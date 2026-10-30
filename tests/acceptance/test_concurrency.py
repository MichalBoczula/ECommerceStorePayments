"""Native BDD inputs, complete contracts and explicit coordination/rollback actions."""

from functools import lru_cache
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from scripts.bdd_evidence import source_evidence
from scripts.generate_operation_links import FEATURES

from tests.acceptance.atomicity_checks import AtomicityChecks
from tests.acceptance.concurrency_checks import ConcurrencyChecks
from tests.acceptance.conftest import AcceptanceContext
from tests.acceptance.evidence import table_values
from tests.acceptance.fulfillment_checks import FulfillmentChecks
from tests.acceptance.payment_checks import PaymentChecks
from tests.acceptance.test_api import matches_matrix
from tests.acceptance.worker_concurrency_checks import WorkerConcurrencyChecks

scenarios("features/concurrency_atomicity.feature")


@lru_cache(maxsize=1)
def profiles() -> dict[str, Any]:
    return source_evidence(FEATURES)


@then(parsers.parse('the response matches case "{case_id}"'))
def matches_concurrent_case(acceptance: AcceptanceContext, case_id: str, datatable: list[list[str]]) -> None:
    matches_matrix(acceptance, case_id, datatable)


@given(parsers.parse('the coordinated target starts "{state}"'))
def target_state(payment_checks: PaymentChecks, state: str) -> None:
    context = payment_checks.context
    assert state in {"absent", "created", "pending", "failed", "canceled"}
    if state == "absent":
        assert payment_checks.target(payment_checks.snapshot()) is None
    elif state in {"created", "pending"}:
        response = context.client.post(
            f"/payments/{context.orders.order_id}/{'pay' if state == 'created' else 'checkout'}"
        )
        assert response.status_code == (201 if state == "created" else 200)
    else:
        payment_checks.prepare(
            state,
            {
                "provider_session_id": '"cs_coordinated_retry"',
                "provider_payment_id": "null",
                "failure_code": '"declined"' if state == "failed" else "null",
            },
        )


@when("two real Pay requests follow the schedule")
def coordinated_pay(concurrency_checks: ConcurrencyChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    concurrency_checks.pay(monkeypatch)


@when("two real Checkout requests follow the schedule")
def coordinated_checkout(concurrency_checks: ConcurrencyChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    concurrency_checks.checkout(monkeypatch)


@when("two stale repository commands follow the schedule")
def coordinated_repository(concurrency_checks: ConcurrencyChecks) -> None:
    concurrency_checks.repository()


@when("two signed webhook requests follow the schedule")
def coordinated_webhook(concurrency_checks: ConcurrencyChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    concurrency_checks.webhook(monkeypatch)


@then("the coordinated checkout responses are")
def checkout_response_table(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.authored["checkout"] = table_values(datatable)


@then("the coordinated provider requests are")
def checkout_form_table(concurrency_checks: ConcurrencyChecks, datatable: list[list[str]]) -> None:
    concurrency_checks.checkout_responses(concurrency_checks.authored["checkout"], table_values(datatable))


@pytest.fixture
def atomicity_checks(payment_checks: PaymentChecks) -> AtomicityChecks:
    return AtomicityChecks(payment_checks)


@given("the post-write rollback boundary is")
def rollback_inputs(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    atomicity_checks.configure(table_values(datatable))


@when("the public request reaches the real post-write fault")
def real_post_write(atomicity_checks: AtomicityChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    atomicity_checks.fail_after_write(monkeypatch)


@then("the real abort preserves this populated state")
def real_rollback(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    cid = atomicity_checks.context.evidence.identity["scenarioId"]
    assert isinstance(cid, str)
    atomicity_checks.rollback(profiles()[cid]["expected"], table_values(datatable))


@when("the fault is removed and the public request is retried")
def retry_after_abort(atomicity_checks: AtomicityChecks) -> None:
    atomicity_checks.retry()


@then("the recovered checkout response is")
def recovered_checkout(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    atomicity_checks.authored["checkout"] = table_values(datatable)


@then("the recovered checkout provider request is")
def recovered_provider(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    atomicity_checks.checkout_recovery(atomicity_checks.authored["checkout"], table_values(datatable))


@then("the recovered webhook receipt is")
def recovered_receipt(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    atomicity_checks.authored["receipt"] = table_values(datatable)


@then("the complete payment after webhook rollback recovery is")
def recovered_payment(atomicity_checks: AtomicityChecks, datatable: list[list[str]]) -> None:
    atomicity_checks.webhook_recovery(atomicity_checks.authored["receipt"], table_values(datatable))


@then("supporting requests preserve the post-abort recovery")
def stable_recovery(atomicity_checks: AtomicityChecks) -> None:
    atomicity_checks.unchanged_repeat()


@pytest.fixture
def worker_concurrency_checks(fulfillment_checks: FulfillmentChecks) -> WorkerConcurrencyChecks:
    return WorkerConcurrencyChecks(fulfillment_checks)


@given("the worker coordination schedule is")
def worker_inputs(worker_concurrency_checks: WorkerConcurrencyChecks, datatable: list[list[str]]) -> None:
    worker_concurrency_checks.configure(table_values(datatable))


@when("real claim and worker commands follow the schedule")
def worker_commands(worker_concurrency_checks: WorkerConcurrencyChecks, monkeypatch: pytest.MonkeyPatch) -> None:
    worker_concurrency_checks.execute(monkeypatch)


@then("the complete coordinated worker receipt is")
def worker_receipt(worker_concurrency_checks: WorkerConcurrencyChecks, datatable: list[list[str]]) -> None:
    worker_concurrency_checks.record(table_values(datatable))


@then("the coordinated worker effects are")
def worker_effects(worker_concurrency_checks: WorkerConcurrencyChecks, datatable: list[list[str]]) -> None:
    worker_concurrency_checks.effects(table_values(datatable))


@then("the complete payment after worker coordination is")
def worker_payment(worker_concurrency_checks: WorkerConcurrencyChecks, datatable: list[list[str]]) -> None:
    worker_concurrency_checks.supporting(table_values(datatable))
