from copy import deepcopy
from functools import lru_cache
from typing import Any

import pytest
from scripts.generate_operation_links import FEATURES, generate
from scripts.openapi_contract import document
from scripts.source_catalog import GUARDS, METHODS
from scripts.source_knowledge import SourceKnowledge, validate_catalog
from scripts.source_links import SourceLinks


@lru_cache
def knowledge() -> dict[str, Any]:
    return generate()


def test_semantic_source_graph_covers_http_commands_policies_rejections_and_receipt_meanings() -> None:
    links = knowledge()
    catalog = links["knowledge"]
    assert len(catalog["scenarioBindings"]) == links["coverage"]["expandedBddCases"] == 391
    assert len(catalog["flows"]) == 9 and len(catalog["policies"]) == 8
    assert len(catalog["rules"]) == 49 and len(catalog["receiptReasons"]) == 11
    assert {r["id"] for r in catalog["commands"]} == {"payments.command.fulfill", "payments.command.replay"}
    for flow in catalog["flows"]:
        assert flow["projection"].startswith("Possible")
        assert all(step["evidence"] == "declared-source" for step in flow["steps"])
    receipts = {r["reason"]: r for r in catalog["receiptReasons"]}
    assert receipts["awaiting_payment"]["state"] == "ignored"
    assert receipts["payment_succeeded"]["state"] == "applied"
    assert receipts["payment_mismatch"]["state"] == "rejected"
    # The same public status family does not claim any particular domain rule ran.
    assert all(r["httpObservation"] for r in catalog["rules"])
    assert "no executed" in catalog["executionClaim"]
    assert "no ingestion" in catalog["rag"]


def test_call_order_evaluates_nested_arguments_before_outer_call_and_workers_use_real_adapters() -> None:
    graph = SourceKnowledge()
    calls = [e["target"] for e in graph.events("WebhookService.receive") if e["kind"] == "call"]
    assert calls.index("MongoWebhookRepository.receive") < calls.index("WebhookService.process_received")
    fulfill = next(f for f in knowledge()["knowledge"]["flows"] if f["id"] == "payments.flow.fulfill")
    calls = [s.get("call", "") for s in fulfill["steps"]]
    for target in (
        "HttpFulfillmentOrders.get",
        "HttpFulfillmentInvoices.create",
        "MongoFulfillmentRepository.complete",
    ):
        assert any(c.endswith(target) for c in calls)
    assert all("test" not in s["source"] for s in fulfill["steps"])


def test_source_ids_ignore_registry_order_and_keep_shared_steps_qualified_by_flow() -> None:
    graph = SourceKnowledge(methods=dict(reversed(list(METHODS.items()))))
    actual = graph.flow("pay", "PaymentService.pay", "payOrder")
    expected = next(f for f in knowledge()["knowledge"]["flows"] if f["id"] == "payments.flow.pay")
    assert [r["id"] for r in actual["steps"]] == [r["id"] for r in expected["steps"]]
    assert all(r["id"].startswith("payments.step.pay/") for r in actual["steps"])
    assert all("sha256" not in r["id"] for r in actual["steps"])


@pytest.mark.parametrize("drift", ["predicate", "guard-id", "method-id", "prose", "missing-call"])
def test_source_changes_require_reviewed_metadata(drift: str) -> None:
    guards, methods = deepcopy(GUARDS), deepcopy(METHODS)
    if drift == "predicate":
        row = guards["PaymentService.pay"][0]
        guards["PaymentService.pay"][0] = (row[0], "False", row[2])
    elif drift == "guard-id":
        rows = guards["PaymentService.pay"]
        rows[1] = (rows[0][0], rows[1][1], rows[1][2])
    elif drift == "method-id":
        methods["PaymentService.pay"]["id"] = methods["PaymentService.checkout"]["id"]
    elif drift == "prose":
        methods["PaymentService.pay"]["effects"] = ""
    else:
        del methods["PaymentService._retry"]
    with pytest.raises(ValueError):
        graph = SourceKnowledge(methods, guards)
        graph.flow("pay", "PaymentService.pay", "payOrder")


@pytest.mark.parametrize(
    "drift",
    [
        "duplicate",
        "prose",
        "site-owner",
        "call-target",
        "step-site",
        "rule-site",
        "policy-rule",
        "policy-dependency",
        "flow-policy",
        "flow-rule",
        "command-flow",
        "http-family",
        "scenario-binding",
    ],
)
def test_broken_or_unrelated_source_references_fail(drift: str) -> None:
    links = deepcopy(knowledge())
    c = links["knowledge"]
    if drift == "duplicate":
        c["methods"][0]["id"] = c["flows"][0]["id"]
    elif drift == "prose":
        c["flows"][0]["failures"] = ""
    elif drift == "site-owner":
        c["sites"][0]["methodId"] = "payments.method.missing"
    elif drift == "call-target":
        c["sites"][0]["targetMethodId"] = "payments.method.missing"
    elif drift == "step-site":
        c["flows"][0]["steps"][0]["sourceEventId"] = "payments.site.missing"
    elif drift == "rule-site":
        c["rules"][0]["sourceEventId"] = "payments.site.missing"
    elif drift == "policy-rule":
        c["policies"][0]["ruleIds"] = [r["id"] for r in c["rules"] if r["source"] != c["policies"][0]["source"]][:1]
    elif drift == "policy-dependency":
        c["policies"][0]["dependencyPolicyIds"] = ["payments.policy.missing"]
    elif drift == "flow-policy":
        c["flows"][0]["policyIds"] = ["payments.policy.missing"]
    elif drift == "flow-rule":
        c["flows"][0]["ruleIds"] = [c["rules"][0]["id"]]
    elif drift == "command-flow":
        c["commands"][0]["flowId"] = "payments.flow.missing"
    elif drift == "http-family":
        next(r for r in c["outcomes"] if r["status"] == 201)["status"] = 499
    else:
        c["scenarioBindings"][0]["kind"] = "action"
    with pytest.raises(ValueError):
        if drift == "scenario-binding":
            SourceLinks(links, document(), FEATURES)
        else:
            validate_catalog(links)
