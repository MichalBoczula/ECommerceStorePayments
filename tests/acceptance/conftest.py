import asyncio
import json
import re
from collections.abc import Generator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
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
from tests.acceptance.checkout_checks import CheckoutChecks
from tests.acceptance.checkout_recovery_checks import CheckoutRecoveryChecks
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence, table_values
from tests.acceptance.payment_checks import PaymentChecks
from tests.acceptance.retry_checks import RetryChecks
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

    def handle(self, request: Request) -> OrdersResponse:
        self.http_calls.append((request.method, request.url.path))
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
    captured = ScenarioEvidence(identity[1], feature.name, scenario.name, parameters)
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
