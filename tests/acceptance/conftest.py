import asyncio
import json
import re
from collections.abc import Callable, Generator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs
from uuid import UUID, uuid4

import allure
import pytest
import stripe
from fastapi.testclient import TestClient
from httpx import AsyncClient, ConnectError, MockTransport, ReadTimeout, Request
from httpx import Response as OrdersResponse
from httpx2 import Response
from pydantic import SecretStr
from pymongo import MongoClient
from pymongo.collection import Collection
from pytest_bdd import given, parsers, then, when
from pytest_bdd.parser import Feature, Scenario, Step
from scripts.bdd_evidence import source_evidence
from scripts.captured_contracts import CapturedContracts
from scripts.openapi_contract import document

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_history_document import (
    PaymentHistoryDocument,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.webhook_document import WebhookDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.acceptance.business_validation_checks import BusinessValidationChecks
from tests.acceptance.checkout_checks import CheckoutChecks
from tests.acceptance.checkout_recovery_checks import CheckoutRecoveryChecks
from tests.acceptance.concurrency_checks import ConcurrencyChecks
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence, table_values
from tests.acceptance.framework_checks import FrameworkChecks
from tests.acceptance.fulfillment_checks import FulfillmentChecks
from tests.acceptance.payment_checks import PaymentChecks
from tests.acceptance.retry_checks import RetryChecks
from tests.acceptance.technical_checks import HealthChecks
from tests.acceptance.webhook_lifecycle_checks import WebhookLifecycleChecks
from tests.acceptance.webhook_verification_checks import WebhookVerificationChecks
from tests.unit.external_providers.test_stripe_checkout import StripeTransport
from tests.webhook_fixtures import WEBHOOK_SECRET


@dataclass
class OrdersBoundary:
    order_id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    invoice_id: UUID | None = None
    fulfillment_mode: str = "ok"
    paid_writes: int = 0
    invoice_creates: int = 0
    mode: str = "created"
    status: str = "Created"
    amount: Decimal = Decimal("12.99")
    currency: str = "PLN"
    calls: int = 0
    http_calls: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])
    fulfillment_handler: Callable[[Request], OrdersResponse] | None = None

    def handle(self, request: Request) -> OrdersResponse:
        self.http_calls.append((request.method, request.url.path))
        if self.fulfillment_handler is not None:
            return self.fulfillment_handler(request)
        if request.url.path.startswith("/invoices/"):
            if request.method == "POST":
                self.invoice_creates += 1
                if self.fulfillment_mode == "pdf_failure":
                    self.fulfillment_mode = "ok"
                    return OrdersResponse(500)
                self.invoice_id = self.invoice_id or uuid4()
                if self.fulfillment_mode == "invoice_ack_lost":
                    self.fulfillment_mode = "ok"
                    raise ReadTimeout("private lost response", request=request)
            if self.invoice_id is None:
                return OrdersResponse(404)
            return OrdersResponse(
                200,
                json={
                    "id": str(self.invoice_id),
                    "orderId": str(self.order_id),
                    "clietDataVersionId": str(self.client_id),
                    "storageUrl": "file:///fixture.pdf",
                    "createdAt": "2026-10-01T00:00:00Z",
                },
            )
        if request.method == "PATCH":
            self.paid_writes += 1
            self.status = "Paid"
            if self.fulfillment_mode == "paid_ack_lost":
                self.fulfillment_mode = "ok"
                raise ReadTimeout("private lost response", request=request)
        assert request.url.path in {f"/orders/{self.order_id}", f"/orders/{self.order_id}/status"}
        self.calls += 1
        if self.mode == "missing":
            return OrdersResponse(404)
        if self.mode == "invalid":
            return OrdersResponse(200, json={"id": str(self.order_id), "status": "Created", "totalAmount": "private"})
        if self.mode == "timeout":
            raise ReadTimeout("private Orders timeout", request=request)
        if self.mode == "outage":
            raise ConnectError("private Orders connection", request=request)
        # Keep money as a JSON number token; a float would lose significant digits.
        metadata = json.dumps(
            {
                "id": str(self.order_id),
                "clientId": str(self.client_id),
                "status": self.status,
                "totalCurrency": self.currency,
            }
        )
        assert self.amount.is_finite()
        amount = format(self.amount, "f")
        body = (
            metadata[:-1]
            + ',"totalAmount":'
            + amount
            + ',"lines":[{"lineTotalAmount":'
            + amount
            + ',"productVersion":'
            + json.dumps({"priceCurrency": self.currency})
            + "}]}"
        )
        return OrdersResponse(200, content=body.encode(), headers={"content-type": "application/json"})


@dataclass
class AcceptanceContext:
    client: EvidenceClient
    evidence: ScenarioEvidence
    orders: OrdersBoundary
    settings: Settings
    mongo: MongoClient[PaymentDocument]
    stripe: AcceptanceStripeTransport
    last_operation: str = ""
    responses: list[Response] = field(default_factory=list[Response])
    initial_payment_id: UUID | None = None
    initial_orders_calls: int = 0
    webhook_payload: bytes = b""
    webhook_delivery: str = "valid"
    health_path: str = ""
    request_window: tuple[datetime, datetime] | None = None

    @property
    def payments(self) -> Collection[PaymentDocument]:
        return self.mongo[self.settings.mongodb_database_name]["payments"]

    @property
    def history(self) -> Collection[PaymentHistoryDocument]:
        return cast(
            Collection[PaymentHistoryDocument], self.mongo[self.settings.mongodb_database_name]["payment_history"]
        )

    @property
    def webhooks(self) -> Collection[WebhookDocument]:
        return cast(Collection[WebhookDocument], self.mongo[self.settings.mongodb_database_name]["stripe_webhooks"])

    def send(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        content_type: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        headers = {**(headers or {}), **({"content-type": content_type} if content_type else {})}
        self.last_operation = f"{method} {path.replace(str(self.orders.order_id), '{order_id}')}"
        started = datetime.now(UTC)
        self.responses = [self.client.request(method, path, content=content, headers=headers)]
        self.request_window = (started, datetime.now(UTC))

    def make_terminal(self, status: PaymentStatus) -> None:
        async def update() -> None:
            database = MongoDatabase(self.settings)
            try:
                repository = MongoPaymentRepository(database)
                payment = await repository.get_by_order_id(self.orders.order_id)
                assert payment is not None
                if status is PaymentStatus.FAILED:
                    payment.mark_as_pending("cs_acceptance")
                    payment = await repository.update(payment)
                    payment.mark_as_failed("declined")
                else:
                    payment.cancel()
                await repository.update(payment)
            finally:
                await database.close()

        with self.evidence.action("Prepare terminal payment through repository", {"status": status.value}):
            asyncio.run(update())


class AcceptanceStripeTransport(StripeTransport):
    def __init__(self, evidence: ScenarioEvidence) -> None:
        self.evidence = evidence
        super().__init__(CheckoutRequest(uuid4(), uuid4(), uuid4(), Money(1299, "PLN")))
        self.sessions: dict[str, dict[str, Any]] = {}
        self.exchange_ids: list[str] = []
        self.mode = "ok"
        self.session_template = deepcopy(self.payload)

    async def request_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data: Any = None
    ) -> tuple[bytes, int, Mapping[str, str]]:
        body = post_data.encode() if isinstance(post_data, str) else bytes(post_data or b"")
        captured_headers = {key.lower(): value for key, value in headers.items()}
        exchange = self.evidence.begin(
            method, url, captured_headers, body, target="stripe", role="provider-boundary", controlled=True
        )
        self.exchange_ids.append(json.loads(exchange.metadata)["exchangeId"])
        try:
            response = await self._respond(method, url, headers, post_data)
            payload, status, response_headers = response
            response_headers = {"content-type": "application/json", **response_headers}
            self.evidence.response(exchange, status, response_headers, payload)
            return payload, status, response_headers
        except BaseException as error:
            self.evidence.failure(exchange, error)
            raise

    async def _respond(
        self, method: str, url: str, headers: Mapping[str, str], post_data: Any = None
    ) -> tuple[bytes, int, Mapping[str, str]]:
        # Keep accepted sessions separate from a rejected/malformed response. A later
        # replay must return the accepted session rather than a poisoned shared payload.
        self.calls.append((method, url, dict(headers), post_data))
        if self.mode == "rejection":
            return (
                json.dumps({"error": {"type": "invalid_request_error", "message": "private Stripe detail"}}).encode(),
                400,
                {},
            )
        if self.mode in {"connection", "timeout_before"}:
            error = stripe.APIConnectionError("private Stripe transport detail")
            if self.mode == "timeout_before":
                error.__cause__ = ReadTimeout("private timeout")
            raise error
        if method == "post":
            body = parse_qs(str(post_data))
            key = headers["Idempotency-Key"]
            metadata = {name: body[f"metadata[{name}]"][0] for name in ("payment_id", "order_id", "attempt_id")}
            candidate = {
                **deepcopy(self.session_template),
                "id": f"cs_test_{metadata['attempt_id']}",
                "url": f"https://checkout.stripe.com/c/pay/cs_test_{metadata['attempt_id']}",
                "amount_total": int(body["line_items[0][price_data][unit_amount]"][0]),
                "currency": body["line_items[0][price_data][currency]"][0],
                "client_reference_id": body["client_reference_id"][0],
                "metadata": metadata,
            }
            self.payload = self.sessions.setdefault(key, candidate)
            if self.mode == "timeout_once":
                self.mode = "ok"
                error = stripe.APIConnectionError("private timeout")
                error.__cause__ = ReadTimeout("private timeout")
                raise error
        else:
            self.payload = next(payload for payload in self.sessions.values() if url.endswith(str(payload["id"])))
        payload = deepcopy(self.payload)
        if self.mode == "invalid_money":
            payload["amount_total"] = int(str(payload["amount_total"])) + 1
        return json.dumps(payload).encode(), 200, {"request-id": "req_boundary_test"}


@pytest.fixture
def acceptance(
    mongo_url: str, monkeypatch: pytest.MonkeyPatch, evidence: ScenarioEvidence
) -> Generator[AcceptanceContext]:
    database_name = f"payments_acceptance_{uuid4().hex}"
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=database_name,
        orders_api_base_url="https://orders.example.test",
        stripe_enabled=True,
        stripe_secret_key=SecretStr("sk_test_fixture"),
        stripe_webhook_secret=SecretStr(WEBHOOK_SECRET),
    )
    orders = OrdersBoundary()
    stripe_boundary = AcceptanceStripeTransport(evidence)
    mongo: MongoClient[PaymentDocument] = MongoClient(mongo_url, uuidRepresentation="standard", tz_aware=True)

    def observed_orders(request: Request) -> OrdersResponse:
        exchange = evidence.begin(
            request.method,
            str(request.url),
            request.headers,
            request.read(),
            target="invoices" if request.url.path.startswith("/invoices/") else "orders",
            role="invoices-boundary" if request.url.path.startswith("/invoices/") else "orders-boundary",
            controlled=True,
        )
        try:
            response = orders.handle(request)
            evidence.response(exchange, response.status_code, response.headers, response.read())
            return response
        except BaseException as error:
            evidence.failure(exchange, error)
            raise

    def orders_client(*, base_url: str, timeout: float, trust_env: bool) -> AsyncClient:
        return AsyncClient(
            base_url=base_url, timeout=timeout, trust_env=trust_env, transport=MockTransport(observed_orders)
        )

    monkeypatch.setattr("ecommerce_store_payments.api.app.AsyncClient", orders_client)
    monkeypatch.setattr(
        "ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments.AsyncClient", orders_client
    )

    def checkout_provider(resolved: Settings) -> StripeCheckoutProvider:
        return StripeCheckoutProvider(
            resolved,
            stripe.StripeClient(
                "sk_test_fixture", stripe_version=STRIPE_API_VERSION, http_client=stripe_boundary, max_network_retries=0
            ),
        )

    monkeypatch.setattr("ecommerce_store_payments.api.app.StripeCheckoutProvider", checkout_provider)
    try:
        with TestClient(create_app(settings)) as client:
            yield AcceptanceContext(
                client=EvidenceClient(client, evidence),
                evidence=evidence,
                orders=orders,
                settings=settings,
                mongo=mongo,
                stripe=stripe_boundary,
            )
    finally:
        try:
            mongo.drop_database(database_name)
        finally:
            mongo.close()


EVIDENCE_KEY = pytest.StashKey[ScenarioEvidence]()


@lru_cache
def captured_contracts() -> CapturedContracts:
    return CapturedContracts(document())


def _node(request: pytest.FixtureRequest) -> pytest.Function:
    # pytest exposes FixtureRequest.node without a concrete Item annotation.
    return cast(pytest.Function, cast(Any, request).node)


@pytest.hookimpl(trylast=True)
def pytest_bdd_before_scenario(request: pytest.FixtureRequest, feature: Feature, scenario: Scenario) -> None:
    identity = re.match(r"(PAY\d+-\d+)\b", scenario.name)
    if identity is None or not feature.name or not scenario.description or not scenario.description.strip():
        raise ValueError("A stable scenario ID and readable description are required")
    callspec = getattr(_node(request), "callspec", None)
    parameters = {
        str(key): str(value) for key, value in getattr(callspec, "params", {}).get("_pytest_bdd_example", {}).items()
    }
    captured = ScenarioEvidence(
        identity[1], feature.name, scenario.name, parameters, contract_check=captured_contracts().observe
    )
    _node(request).stash[EVIDENCE_KEY] = captured
    cast(Any, allure.dynamic).description(scenario.description.strip())
    captured.publish_identity()


@pytest.fixture
def evidence(request: pytest.FixtureRequest) -> ScenarioEvidence:
    return _node(request).stash[EVIDENCE_KEY]


@pytest.hookimpl(trylast=True)
def pytest_bdd_before_step(request: pytest.FixtureRequest, step: Step) -> None:
    captured = _node(request).stash[EVIDENCE_KEY]
    captured.phase = step.type.capitalize()
    captured.step = step.name


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_after_step(request: pytest.FixtureRequest) -> None:
    _node(request).stash[EVIDENCE_KEY].flush()


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_step_error(request: pytest.FixtureRequest) -> None:
    _node(request).stash[EVIDENCE_KEY].flush()


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_after_scenario(request: pytest.FixtureRequest) -> None:
    if EVIDENCE_KEY in _node(request).stash:
        _node(request).stash[EVIDENCE_KEY].finish()


@given("the order fixture contains")
def order_inputs(acceptance: AcceptanceContext, datatable: list[list[str]]) -> None:
    values = table_values(datatable)
    assert values.keys() == {"OrderId", "ClientId", "TotalAmount", "TotalCurrency"}
    acceptance.orders.order_id = UUID(values["OrderId"])
    acceptance.orders.client_id = UUID(values["ClientId"])
    acceptance.orders.amount = Decimal(values["TotalAmount"])
    acceptance.orders.currency = values["TotalCurrency"]
    acceptance.evidence.observation("Scenario inputs", values)


@given("the health request uses")
def health_inputs(acceptance: AcceptanceContext, datatable: list[list[str]]) -> None:
    values = table_values(datatable)
    assert values.keys() == {"Path"}
    acceptance.health_path = values["Path"]
    acceptance.evidence.observation("Scenario inputs", values)


@when("I request the health probe")
def request_health(acceptance: AcceptanceContext) -> None:
    assert acceptance.health_path
    acceptance.send("GET", acceptance.health_path)


@pytest.fixture
def payment_checks(acceptance: AcceptanceContext) -> PaymentChecks:
    return PaymentChecks(acceptance)


@given("an unrelated succeeded payment fills all collections")
def unrelated_payment(payment_checks: PaymentChecks, datatable: list[list[str]]) -> None:
    payment_checks.unrelated(table_values(datatable))


@given(parsers.parse('a stored payment is prepared in state "{state}"'))
def stored_payment(payment_checks: PaymentChecks, state: str, datatable: list[list[str]]) -> None:
    payment_checks.prepare(state, table_values(datatable))


@given("I remember the payment and every collection")
def remember_payment(payment_checks: PaymentChecks) -> None:
    payment_checks.remember()


@then("the complete payment response is")
def complete_payment(payment_checks: PaymentChecks, datatable: list[list[str]]) -> None:
    payment_checks.complete(table_values(datatable))


@then("every payment collection and external call count is unchanged")
def unchanged_payment(payment_checks: PaymentChecks) -> None:
    payment_checks.unchanged()


@then("only the requested payment is inserted")
def only_requested_payment(payment_checks: PaymentChecks) -> None:
    payment_checks.only_created()


@pytest.fixture
def retry_checks(payment_checks: PaymentChecks) -> RetryChecks:
    return RetryChecks(payment_checks)


@given(parsers.parse('a historical payment in state "{state}" has no version or checkout fields'))
def historical_payment(retry_checks: RetryChecks, state: str, datatable: list[list[str]]) -> None:
    retry_checks.legacy(state, table_values(datatable))


@given(parsers.parse('Orders currency changes to "{currency}"'))
def changed_currency(acceptance: AcceptanceContext, currency: str) -> None:
    acceptance.orders.currency = currency


@then("the complete retry response is")
def complete_retry(retry_checks: RetryChecks, datatable: list[list[str]]) -> None:
    retry_checks.complete(table_values(datatable))


@then("the retry changes only this version and archive")
def retry_archive(retry_checks: RetryChecks, datatable: list[list[str]]) -> None:
    retry_checks.changed(table_values(datatable))


@then("the rejected retry preserves every document")
def rejected_retry(retry_checks: RetryChecks) -> None:
    retry_checks.rejected()


@then("repeating Pay preserves the completed retry")
def repeat_retry(retry_checks: RetryChecks) -> None:
    retry_checks.repeat()


@then("a later failed attempt is retried without changing older snapshots")
def later_retry(retry_checks: RetryChecks, datatable: list[list[str]]) -> None:
    retry_checks.later_cycle(table_values(datatable))


@pytest.fixture
def checkout_checks(payment_checks: PaymentChecks) -> CheckoutChecks:
    return CheckoutChecks(payment_checks)


@given("I remember checkout state and provider calls")
def remember_checkout(checkout_checks: CheckoutChecks) -> None:
    checkout_checks.remember()


@given("the hosted checkout return URLs are")
def checkout_return_urls(acceptance: AcceptanceContext, datatable: list[list[str]]) -> None:
    values = table_values(datatable)
    assert values.keys() == {"SuccessUrl", "CancelUrl"}
    acceptance.settings.stripe_success_url = values["SuccessUrl"]
    acceptance.settings.stripe_cancel_url = values["CancelUrl"]
    acceptance.evidence.observation("Checkout return URLs", values)


@given("the existing provider session returns")
def provider_session_state(checkout_checks: CheckoutChecks, datatable: list[list[str]]) -> None:
    values = table_values(datatable)
    assert values.keys() == {"Status", "ExpiresAt"}
    assert values["Status"] in {"open", "complete", "expired"}
    provider = checkout_checks.provider()
    provider.update(status=values["Status"], expires_at=int(values["ExpiresAt"]))
    checkout_checks.context.evidence.observation("Controlled provider session", {"inputs": values, "session": provider})


@then("the complete checkout response is")
def complete_checkout(checkout_checks: CheckoutChecks, datatable: list[list[str]]) -> None:
    checkout_checks.complete(table_values(datatable))


@then("only this checkout is created with this provider request")
def created_checkout(checkout_checks: CheckoutChecks, datatable: list[list[str]]) -> None:
    checkout_checks.created(table_values(datatable))


@then("checkout reads only the existing provider session without writes")
def retrieved_checkout(checkout_checks: CheckoutChecks) -> None:
    checkout_checks.retrieved()


@then("repeated checkout keeps the complete response and durable state")
def repeat_checkout(checkout_checks: CheckoutChecks, datatable: list[list[str]]) -> None:
    checkout_checks.repeat(table_values(datatable))


@pytest.fixture
def recovery_checks(payment_checks: PaymentChecks, checkout_checks: CheckoutChecks) -> CheckoutRecoveryChecks:
    return CheckoutRecoveryChecks(payment_checks, checkout_checks)


@given("I remember checkout recovery state")
def remember_recovery(recovery_checks: CheckoutRecoveryChecks) -> None:
    recovery_checks.remember()


@given("the earlier checkout failure matches")
def earlier_checkout_problem(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.earlier_problem(table_values(datatable))


@given("the earlier checkout failure leaves")
@then("checkout failure leaves this complete state")
def failed_checkout_state(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.effect(table_values(datatable))


@given("a reserved checkout fixture contains")
def reserved_checkout(
    recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    recovery_checks.reserve(table_values(datatable), monkeypatch)


@given("a legacy Pending checkout has no attempt identity")
def legacy_pending_checkout(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.legacy_pending(table_values(datatable))


@given(parsers.parse('checkout persistence is interrupted at "{point}"'))
def interrupted_checkout(recovery_checks: CheckoutRecoveryChecks, point: str, monkeypatch: pytest.MonkeyPatch) -> None:
    recovery_checks.interrupt(point, monkeypatch)


@then("the failed provider request is")
def failed_checkout_request(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.failed_request(table_values(datatable))


@then("the complete recovered checkout response is")
def complete_recovered_checkout(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.current_recovery(table_values(datatable))


@then("a fresh application instance recovers checkout with")
def recover_checkout_in_fresh_app(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.fresh_recovery(table_values(datatable))


@then("the recovery provider request is")
def recovered_checkout_request(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.recovery_request(table_values(datatable))


@then("repeated provider rejection preserves the reserved attempt")
def repeated_checkout_failure(recovery_checks: CheckoutRecoveryChecks, datatable: list[list[str]]) -> None:
    recovery_checks.repeat_failure(table_values(datatable))


@pytest.fixture
def verification_checks(payment_checks: PaymentChecks) -> WebhookVerificationChecks:
    return WebhookVerificationChecks(payment_checks)


@given("the webhook verification request is prepared")
def prepared_verification(
    verification_checks: WebhookVerificationChecks, datatable: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    verification_checks.prepare(table_values(datatable), monkeypatch)


@given("I remember webhook verification state")
def remember_verification(verification_checks: WebhookVerificationChecks) -> None:
    verification_checks.remember()


@when("I deliver the prepared verification webhook")
def send_verification(verification_checks: WebhookVerificationChecks) -> None:
    verification_checks.deliver()


@then("the webhook delivery matches this verification evidence")
def verified_wire(verification_checks: WebhookVerificationChecks, datatable: list[list[str]]) -> None:
    verification_checks.wire_evidence(table_values(datatable))


@then("verification rejection preserves this complete state")
def unchanged_verification(verification_checks: WebhookVerificationChecks, datatable: list[list[str]]) -> None:
    verification_checks.rejected(table_values(datatable))


@then("the accepted verification stores this exact ignored receipt")
def unknown_verification_receipt(verification_checks: WebhookVerificationChecks, datatable: list[list[str]]) -> None:
    verification_checks.unknown_receipt(table_values(datatable))


@then("the paid verification digest is")
def paid_verification_digest(verification_checks: WebhookVerificationChecks, datatable: list[list[str]]) -> None:
    verification_checks.paid_control(table_values(datatable))


@pytest.fixture
def lifecycle_checks(payment_checks: PaymentChecks) -> WebhookLifecycleChecks:
    return WebhookLifecycleChecks(payment_checks)


@given("a lifecycle payment starts in")
def lifecycle_start(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.start(table_values(datatable))


@given("the lifecycle event is prepared")
def lifecycle_event(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.prepare(table_values(datatable))


@given("I remember complete webhook lifecycle state")
def lifecycle_before(lifecycle_checks: WebhookLifecycleChecks) -> None:
    lifecycle_checks.remember()


@given("the lifecycle event was delivered")
@when("I deliver the lifecycle event")
def lifecycle_deliver(lifecycle_checks: WebhookLifecycleChecks) -> None:
    lifecycle_checks.deliver()


@then("the complete lifecycle receipt is")
def lifecycle_receipt(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.receipt(table_values(datatable))


@then("webhook processing changes exactly this state")
def lifecycle_delta(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.delta(table_values(datatable))


@then("the complete payment read after webhook is")
def lifecycle_read(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.read(table_values(datatable))


@given("lifecycle completion is interrupted")
def lifecycle_interrupt(
    lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle_checks.interrupt(table_values(datatable), monkeypatch)


@then("durable webhook recovery runs with")
def lifecycle_recover(lifecycle_checks: WebhookLifecycleChecks, datatable: list[list[str]]) -> None:
    lifecycle_checks.recover(table_values(datatable))


@pytest.fixture
def fulfillment_checks(payment_checks: PaymentChecks) -> FulfillmentChecks:
    return FulfillmentChecks(payment_checks)


@given("unrelated fulfillment has completed through the worker")
def settle_unrelated_work(fulfillment_checks: FulfillmentChecks) -> None:
    fulfillment_checks.settle_unrelated()


@given("verified fulfillment work is prepared")
def prepare_fulfillment_work(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.prepare(table_values(datatable))


@given("I remember complete fulfillment state")
def remember_fulfillment_work(fulfillment_checks: FulfillmentChecks) -> None:
    fulfillment_checks.remember()


@then("the complete durable fulfillment record is")
def assert_fulfillment_record(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.state(table_values(datatable))


@then("the worker performs exactly these HTTP operations")
def assert_fulfillment_http(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.http(table_values(datatable))


@then("the complete payment read after fulfillment is")
def assert_fulfillment_payment_read(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.read(table_values(datatable))


@given("local fulfillment persistence is interrupted")
def interrupt_fulfillment_persistence(
    fulfillment_checks: FulfillmentChecks, datatable: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    fulfillment_checks.interrupt(table_values(datatable), monkeypatch)


@then("the controlled downstream state changes to")
def change_fulfillment_boundary(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.change(table_values(datatable))


@then("the operator resumes repaired fulfillment with")
def resume_repaired_fulfillment(fulfillment_checks: FulfillmentChecks, datatable: list[list[str]]) -> None:
    fulfillment_checks.resume(table_values(datatable))


@pytest.fixture
def business_checks(payment_checks: PaymentChecks) -> BusinessValidationChecks:
    return BusinessValidationChecks(payment_checks)


@given("Orders exposes this business contract")
def business_contract(business_checks: BusinessValidationChecks, datatable: list[list[str]]) -> None:
    business_checks.configure(table_values(datatable))


@given("I remember complete business validation state")
def business_before(business_checks: BusinessValidationChecks) -> None:
    business_checks.remember()


@then("business rejection preserves populated state on both requests")
def business_rejection(business_checks: BusinessValidationChecks, datatable: list[list[str]]) -> None:
    case_id = business_checks.context.evidence.identity["scenarioId"]
    assert isinstance(case_id, str)
    expected = _business_profiles()[case_id]["expected"]
    business_checks.rejection(table_values(datatable), expected)


@lru_cache(maxsize=1)
def _business_profiles() -> dict[str, dict[str, Any]]:
    return source_evidence(Path(__file__).parent / "features")


@then("the accepted business boundary remains stable")
def business_repeat(business_checks: BusinessValidationChecks, datatable: list[list[str]]) -> None:
    business_checks.accepted_repeat(table_values(datatable))


@pytest.fixture
def framework_checks(payment_checks: PaymentChecks) -> FrameworkChecks:
    return FrameworkChecks(payment_checks)


@pytest.fixture
def concurrency_checks(payment_checks: PaymentChecks) -> ConcurrencyChecks:
    return ConcurrencyChecks(payment_checks)


@given("the real write schedule is")
def coordinate_writes(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.configure(table_values(datatable))


@then("the coordinated payment responses are")
def coordinated_payments(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.payment_responses(table_values(datatable))


@then("the coordinated database effects are")
def coordinated_effects(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.effects(table_values(datatable))


@then("supporting reads and repeats preserve the coordinated result")
def coordinated_supporting(concurrency_checks: ConcurrencyChecks) -> None:
    concurrency_checks.supporting()


@given("the framework request contains")
def framework_request(framework_checks: FrameworkChecks, datatable: list[list[str]]) -> None:
    framework_checks.prepare(table_values(datatable))


@given("I remember populated framework state")
def framework_remember(framework_checks: FrameworkChecks) -> None:
    framework_checks.remember()


@given("this framework failure is installed")
def framework_fault(
    framework_checks: FrameworkChecks, datatable: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    framework_checks.install_fault(table_values(datatable), monkeypatch)


@when("I submit the prepared framework request")
def framework_send(framework_checks: FrameworkChecks) -> None:
    framework_checks.send()


@then("framework rejection keeps this populated state and protocol")
def framework_rejected(framework_checks: FrameworkChecks, datatable: list[list[str]]) -> None:
    case_id = framework_checks.context.evidence.identity["scenarioId"]
    assert isinstance(case_id, str)
    framework_checks.rejected(_business_profiles()[case_id]["expected"], table_values(datatable))


@then("the accepted framework input has these effects")
def framework_accepted(framework_checks: FrameworkChecks, datatable: list[list[str]]) -> None:
    framework_checks.accepted(table_values(datatable))


@then("the first coordinated receipt is")
def first_coordinated_receipt(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.authored["first"] = table_values(datatable)


@then("the second coordinated receipt is")
def second_coordinated_receipt(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.receipts(concurrency_checks.authored["first"], table_values(datatable))


@pytest.fixture
def health_checks(acceptance: AcceptanceContext) -> HealthChecks:
    return HealthChecks(acceptance)


@given("populated health collections contain")
def populated_health(health_checks: HealthChecks, datatable: list[list[str]]) -> None:
    health_checks.populate(table_values(datatable))


@given("I observe actual health probe calls")
def observe_health(health_checks: HealthChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    health_checks.observe(monkeypatch)


@then("health preserves complete populated state and protocol")
def complete_health(health_checks: HealthChecks, datatable: list[list[str]]) -> None:
    health_checks.verify(table_values(datatable))
