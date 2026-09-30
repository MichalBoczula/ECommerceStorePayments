from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from scripts.generate_operation_links import MATRIX, generate

from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.api.routes.payments import router as payments_router
from ecommerce_store_payments.domain.aggregates.payments.payment_policy import PaymentPolicy


def test_generated_links_follow_executed_flows_and_domain_policies() -> None:
    result = generate()
    operations = {item["operationId"]: item for item in result["operations"]}
    assert set(operations) == {
        "payOrder",
        "getPaymentByOrderId",
        "createOrderCheckout",
        "receiveStripeWebhook",
        "get_health",
        "get_liveness",
        "get_readiness",
    }
    webhook = operations["receiveStripeWebhook"]
    assert webhook["flow"]["source"].endswith("WebhookService.receive")
    assert any(
        policy["source"].endswith("PaymentPolicy.require_checkout_confirmation") for policy in webhook["policies"]
    )
    pay = operations["payOrder"]
    assert pay["flow"]["source"].endswith("PaymentService.pay")
    assert any(step.get("call", "").endswith("PaymentService._retry") for step in pay["flow"]["steps"])
    assert any(policy["source"].endswith("PaymentPolicy.require_transition") for policy in pay["policies"])
    assert not any(
        policy["source"].endswith("PaymentPolicy.require_transition")
        for policy in operations["getPaymentByOrderId"]["policies"]
    )
    assert any(
        policy["source"].endswith("PaymentPolicy.validate_snapshot")
        for policy in operations["getPaymentByOrderId"]["policies"]
    )
    assert {scenario["id"] for scenario in operations["get_health"]["scenarios"]} == {"PAY11-22"}
    assert [row["id"] for row in result["unmatchedRouteScenarios"]] == ["PAY11-17"]


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("PAY11-01\t", "Matrix and source scenarios differ"),
        ("POST /payments/{order_id}/pay", "Orphan or ambiguous scenario route"),
        ("PAY/9", "Unknown requirement"),
    ],
)
def test_stale_matrix_links_fail(replacement: str, message: str, tmp_path: Path) -> None:
    source = MATRIX.read_text(encoding="utf-8")
    if replacement.startswith("PAY11"):
        changed = "\n".join(row for row in source.splitlines() if not row.startswith(replacement)) + "\n"
    elif replacement.startswith("POST"):
        changed = source.replace(replacement, "POST /unknown-payment-route", 1)
    else:
        changed = source.replace(replacement, "PAY/999", 1)
    matrix = tmp_path / "matrix.tsv"
    matrix.write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        generate(matrix=matrix)


def test_duplicate_scenario_id_fails(tmp_path: Path) -> None:
    source = MATRIX.read_text(encoding="utf-8")
    matrix = tmp_path / "matrix.tsv"
    matrix.write_text(source + source.splitlines()[1] + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate matrix scenario ID"):
        generate(matrix=matrix)


def test_missing_executed_service_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    route = next(
        route for route in payments_router.routes if isinstance(route, APIRoute) and route.operation_id == "payOrder"
    )

    async def no_service_call() -> None:
        pass

    monkeypatch.setattr(route, "endpoint", no_service_call)
    with pytest.raises(ValueError, match="Missing executed service flow"):
        generate()


def test_missing_called_policy_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(PaymentPolicy, "require_transition")
    with pytest.raises(ValueError, match=r"Unknown linked call: PaymentPolicy\.require_transition"):
        generate()


def test_duplicate_operation_id_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    routes = [route for route in health_router.routes if isinstance(route, APIRoute)]
    monkeypatch.setattr(routes[1], "operation_id", routes[0].operation_id)
    with pytest.raises(ValueError, match="duplicate operationId"):
        generate()
