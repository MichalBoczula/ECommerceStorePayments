"""Join declared source intent to actual immutable scenario evidence, without tracing branches."""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import ValidationError
from pytest_bdd.parser import FeatureParser

from scripts.bdd_evidence import attachments, instance_id, source_evidence
from scripts.captured_contracts import CapturedContracts
from scripts.source_knowledge import validate_catalog
from scripts.technical_scenarios import check_technical_result

ATTACHMENT = "Scenario source links"
WORKER_WHENS = {
    "the durable fulfillment command runs",
    "the invoice retry becomes due and the durable fulfillment command runs",
    "real claim and worker commands follow the schedule",
}
REPOSITORY_WHEN = "two stale repository commands follow the schedule"
CLAIM = "Declared source context and observed facts only; no executed steps, branches or rules are inferred"


def scenario_bindings(links: dict[str, Any], feature_dir: Path) -> list[dict[str, Any]]:
    """Bind authored When steps, never a case-ID prefix or a setup response masquerading as work."""
    technical = {r["id"]: r for r in links["technicalScenarios"]}
    http = {c["id"]: (op, c) for op in links["operations"] for c in op["scenarios"]}
    missing = {r["id"] for r in links["unmatchedRouteScenarios"]}
    rows = []
    for path in sorted(feature_dir.rglob("*.feature")):
        feature = FeatureParser(str(feature_dir), path.relative_to(feature_dir).as_posix()).parse()
        for template in feature.scenarios.values():
            contexts = [c for examples in template.examples for c in examples.as_contexts()] or [{}]
            for context in contexts:
                scenario = template.render(context)
                case = scenario.name.split()[0]
                whens = [s.name for s in scenario.steps if s.type == "when"]
                source_id = flow_id = None
                if case in technical:
                    kind = "technical"
                    source_id = technical[case]["source"]
                elif any(s in WORKER_WHENS for s in whens):
                    kind, source_id, flow_id = "action", "payments.command.fulfill", "payments.flow.fulfill"
                elif REPOSITORY_WHEN in whens:
                    kind, source_id = "action", "payments.method.payment-update"
                elif case in http or case in missing:
                    kind = "http"
                    if case in http:
                        source_id = http[case][0]["operationId"]
                        flow_id = http[case][0]["flow"]["id"]
                else:
                    raise ValueError("Unbound source scenario: " + case)
                rows.append(
                    dict(
                        scenarioId=case,
                        kind=kind,
                        sourceId=source_id,
                        flowId=flow_id,
                        whenSteps=whens,
                        httpOperationId=http[case][0]["operationId"] if case in http else None,
                    )
                )
    return sorted(rows, key=lambda r: r["scenarioId"])


def receipt_facts(value: Any, pointer: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Select canonical recorded BSON receipts, excluding authored expected tables/tokens."""
    rows = []
    if isinstance(value, dict):
        if (
            isinstance(value.get("_id"), str)
            and value["_id"].startswith("evt_")
            and isinstance(value.get("state"), str)
            and value.get("state") in {"pending", "applied", "ignored", "rejected"}
            and isinstance(value.get("received_at"), dict)
            and set(value["received_at"]) == {"$date"}
            and re.fullmatch(r"[0-9a-f]{64}", str(value.get("payload_digest", "")))
            and "event_type" in value
            and "reason" in value
        ):
            rows.append((pointer, value))
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            rows.extend(receipt_facts(child, pointer + "/" + escaped))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(receipt_facts(child, pointer + "/" + str(index)))
    return rows


class SourceLinks:
    def __init__(self, links: dict[str, Any], spec: dict[str, Any], feature_dir: Path) -> None:
        validate_catalog(links)
        self.links, self.contracts = links, CapturedContracts(spec)
        self.catalog = links["knowledge"]
        self.profiles = source_evidence(feature_dir)
        self.bindings = {r["scenarioId"]: r for r in self.catalog["scenarioBindings"]}
        if list(self.bindings.values()) != scenario_bindings(links, feature_dir):
            raise ValueError("Source scenario bindings differ from actual When steps")
        if self.bindings.keys() != self.profiles.keys():
            raise ValueError("Source scenario binding coverage differs")
        self.flows = {f["id"]: f for f in self.catalog["flows"]}
        self.operations = {o["operationId"]: o for o in links["operations"]}
        self.sources = {r["id"]: r for key in ("commands", "methods") for r in self.catalog[key]}
        self.outcomes = {r["id"]: r for r in self.catalog["outcomes"]}
        self.reasons = {r["reason"]: r for r in self.catalog["receiptReasons"]}

    def context(self, flow_id: str | None) -> dict[str, Any]:
        flow = self.flows.get(flow_id or "")
        return dict(
            flowId=flow_id,
            declaredStepIds=[s["id"] for s in flow["steps"]] if flow else [],
            declaredPolicyIds=flow["policyIds"] if flow else [],
            declaredRuleIds=flow["ruleIds"] if flow else [],
            executedStepIds=[],
            executedRuleIds=[],
        )

    def observe(self, identity: dict[str, Any], records: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"valid": True, **self.check(identity, records)}
        except (ValidationError, ValueError, KeyError, TypeError) as error:
            return {"valid": False, "errorType": type(error).__name__}

    def check(self, identity: dict[str, Any], records: dict[str, Any]) -> dict[str, Any]:
        case = identity["scenarioId"]
        profile, binding = self.profiles[case], self.bindings[case]
        wanted = dict(
            service="payments",
            scenarioId=case,
            instanceId=instance_id(case, profile["parameters"]),
            feature=profile["feature"],
            scenario=profile["scenario"],
            parameters=profile["parameters"],
        )
        if identity != wanted:
            raise ValueError("Foreign source evidence identity")
        pairs: dict[str, dict[str, tuple[str, dict[str, Any]]]] = defaultdict(dict)
        actions: dict[str, dict[str, tuple[str, dict[str, Any]]]] = defaultdict(dict)
        for name, record in records.items():
            if name == ATTACHMENT:
                continue
            if any(record.get(k) != v for k, v in identity.items()):
                raise ValueError("Foreign source evidence record")
            kind = record.get("kind")
            if kind in {"request", "response", "failure"}:
                group = pairs[record["exchangeId"]]
                if kind in group:
                    raise ValueError("Duplicate actual exchange record")
                group[kind] = name, record
            elif kind in {"action-start", "action-result", "action-failure"}:
                group = actions[record["actionId"]]
                if kind in group:
                    raise ValueError("Duplicate actual action record")
                group[kind] = name, record
        action_rows = []
        for action_id, group in sorted(actions.items()):
            if set(group) not in ({"action-start", "action-result"}, {"action-start", "action-failure"}):
                raise ValueError("Source action lacks actual paired records")
            start_name, start = group["action-start"]
            end_name, end = group.get("action-result") or group["action-failure"]
            metadata = {k: v for k, v in start.items() if k not in {"kind", "inputs"}}
            if metadata != {k: v for k, v in end.items() if k not in {"kind", "output", "exceptionType"}}:
                raise ValueError("Action source association changed")
            source_id = start.get("sourceId")
            source = self.sources.get(source_id)
            if source_id is not None and source is None:
                raise ValueError("Unknown explicit action source")
            flow_id = source.get("flowId") if source else None
            outcome_id = "payments.outcome.command." + source["name"] if source and "name" in source else None
            action_rows.append(
                dict(
                    actionId=action_id,
                    sourceId=source_id,
                    startAttachment=start_name,
                    outcomeAttachment=end_name,
                    phase=start["stepPhase"],
                    step=start["step"],
                    observation=end["kind"],
                    outcomeId=outcome_id,
                    **self.context(flow_id),
                )
            )
        action_by_id = {r["actionId"]: r for r in action_rows}
        exchanges = []
        for exchange_id, group in sorted(pairs.items()):
            if set(group) not in ({"request", "response"}, {"request", "failure"}):
                raise ValueError("Source exchange lacks actual paired records")
            request_name, request = group["request"]
            outcome_name, outcome = group.get("response") or group["failure"]
            excluded = {"kind", "headers", "headerItems", "content", "status", "exceptionType", "cancelled"}
            if {k: v for k, v in request.items() if k not in excluded} != {
                k: v for k, v in outcome.items() if k not in excluded
            } or exchange_id != f"{identity['instanceId']}/{request['sequence']}":
                raise ValueError("Changed source request/outcome association")
            classification = self.contracts.check(request, outcome)
            operation_id = classification.get("operationId")
            op = self.operations.get(operation_id)
            flow_id = op["flow"]["id"] if op else None
            if request["actionId"] is not None and request["actionId"] not in action_by_id:
                raise ValueError("Source exchange has no actual owning action")
            outcome_id = None
            if outcome["kind"] == "failure":
                outcome_id = "payments.outcome.transport." + ("cancelled" if outcome["cancelled"] else "failure")
            elif op:
                outcome_id = (
                    "payments.outcome." + flow_id.removeprefix("payments.flow.") + ".http-" + str(outcome["status"])
                )
            elif classification["classification"] == "unmatched-route":
                outcome_id = "payments.outcome.routing.http-404"
            if outcome_id is not None and outcome_id not in self.outcomes:
                raise ValueError("Unknown observed outcome family")
            body = request["content"]["body"]
            event_id = body.get("id") if operation_id == "receiveStripeWebhook" and isinstance(body, dict) else None
            public = outcome.get("content", {}).get("body")
            exchanges.append(
                dict(
                    exchangeId=exchange_id,
                    requestAttachment=request_name,
                    outcomeAttachment=outcome_name,
                    phase=request["stepPhase"],
                    step=request["step"],
                    targetService=request["targetService"],
                    exchangeRole=request["exchangeRole"],
                    controlledBoundary=request["controlledBoundary"],
                    requestAttempt=request["requestAttempt"],
                    actionId=request["actionId"],
                    ownerSourceId=action_by_id[request["actionId"]]["sourceId"] if request["actionId"] else None,
                    classification=classification["classification"],
                    operationId=operation_id,
                    outcomeId=outcome_id,
                    observation=outcome["kind"],
                    status=outcome.get("status"),
                    publicCode=public.get("code") if isinstance(public, dict) else None,
                    exceptionType=outcome.get("exceptionType"),
                    eventId=event_id,
                    **self.context(flow_id),
                )
            )
        facts = []
        for name, record in sorted(records.items()):
            if name == ATTACHMENT:
                continue
            for pointer, receipt in receipt_facts(record.get("value"), "/value"):
                reason = receipt["reason"]
                declared = self.reasons.get(reason)
                if (receipt["state"] == "pending" and reason is not None) or (
                    receipt["state"] != "pending" and (declared is None or declared["state"] != receipt["state"])
                ):
                    raise ValueError("Unknown or mismatched actual receipt state/reason")
                facts.append(
                    dict(
                        attachment=name,
                        jsonPointer=pointer,
                        phase=record["stepPhase"],
                        eventId=receipt["_id"],
                        state=receipt["state"],
                        reason=reason,
                        reasonId=declared["id"] if declared else None,
                        fulfillmentStatus=receipt.get("fulfillment_status"),
                        fulfillmentError=receipt.get("fulfillment_error"),
                        matchingExchangeIds=[e["exchangeId"] for e in exchanges if e["eventId"] == receipt["_id"]],
                        causalityClaim="Recorded snapshot only; matching event IDs do not establish causality",
                    )
                )
        primary = self.primary(profile, binding, records, pairs, exchanges, action_rows)
        return dict(
            schemaVersion=1,
            executionClaim=CLAIM,
            binding=binding,
            primaryWitnesses=primary,
            exchanges=exchanges,
            actions=action_rows,
            receiptFacts=facts,
            rag="Source/evidence references prepared; no ingestion, retrieval or evaluation claimed",
        )

    def primary(
        self,
        profile: dict[str, Any],
        binding: dict[str, Any],
        records: dict[str, Any],
        pairs: dict[str, Any],
        exchanges: list[dict[str, Any]],
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        technical = profile.get("technical", False)
        expectation = records["Expected technical outcome" if technical else "Expected response"]
        if expectation["value"] != profile["expected"]:
            raise ValueError("Source witness expectation differs from authored table")
        selected = expectation.get("exchangeIds", [])
        if len(selected) != len(set(selected)):
            raise ValueError("Duplicate selected source witness")
        by_exchange = {r["exchangeId"]: r for r in exchanges}
        by_action = {r["actionId"]: r for r in actions}
        if any(e not in by_exchange for e in selected):
            raise ValueError("Foreign selected source witness")
        if not technical:
            responses = [pairs[e].get("response", (None, {}))[1] for e in selected]
            expected = profile["expected"]
            if sorted(r.get("status", -1) for r in responses) != sorted(map(int, expected["HTTPStatuses"].split(","))):
                raise ValueError("Source outcome differs from authored statuses")
            for response in responses:
                body = response["content"]["body"]
                if (
                    response["targetService"] != "payments"
                    or response["content"]["contentType"] != expected["ContentType"]
                    or body.get("code", "-") != expected["Code"]
                ):
                    raise ValueError("Source outcome differs from authored public signature")
                for key, value in expected.items():
                    if key.startswith("JSON."):
                        actual = body
                        for part in key[5:].split("."):
                            actual = actual[part]
                        if type(actual) is not type(json.loads(value)) or actual != json.loads(value):
                            raise ValueError("Source outcome differs from authored JSON")
        witnesses = []
        for exchange_id in selected:
            row = by_exchange[exchange_id]
            role = (
                "setup-http"
                if row["phase"] in {"Setup", "Given"}
                else "supporting-http"
                if binding["kind"] == "action"
                else "primary-http"
            )
            if role == "setup-http" and binding["kind"] != "action":
                raise ValueError("Setup HTTP cannot replace a primary When witness")
            if not technical and row["operationId"] != binding["httpOperationId"]:
                raise ValueError("Selected witness belongs to an unrelated operation")
            witnesses.append(dict(kind=role, exchangeId=exchange_id, outcomeId=row["outcomeId"]))
        if technical:
            if any(by_exchange[e]["phase"] != "When" for e in selected):
                raise ValueError("Technical HTTP witness must come from When")
            check_technical_result(
                expectation,
                profile["expected"],
                {k: [v[1] for v in group.values()] for k, group in pairs.items()},
                records,
            )
            for action_id in expectation.get("actionIds", []):
                if action_id not in by_action or by_action[action_id]["phase"] != "When":
                    raise ValueError("Technical primary action is missing or not When")
                witnesses.append(dict(kind="primary-action", actionId=action_id))
            for witness in witnesses:
                witness["technicalOutcomeId"] = "payments.outcome.technical." + binding["scenarioId"].lower()
        elif binding["kind"] == "action":
            actual = [a for a in actions if a["sourceId"] == binding["sourceId"] and a["phase"] == "When"]
            if not actual:
                raise ValueError("Primary worker/repository When action is missing")
            witnesses.extend(
                dict(kind="primary-action", actionId=a["actionId"], sourceId=a["sourceId"], outcomeId=a["outcomeId"])
                for a in actual
            )
        elif not witnesses or any(by_exchange[e]["phase"] != "When" for e in selected):
            raise ValueError("Primary HTTP witness must come from the actual When")
        return witnesses


def check_source_links(
    links: dict[str, Any], spec: dict[str, Any], feature_dir: Path, results_dir: Path
) -> dict[str, int]:
    checks = SourceLinks(links, spec, feature_dir)
    totals = dict(scenarios=0, exchanges=0, actions=0, receiptFacts=0, primaryActions=0, setupHttp=0)
    seen = set()
    for path in results_dir.glob("*-result.json"):
        records = {}
        for attachment in attachments(json.loads(path.read_text())):
            if attachment["type"] != "application/json":
                continue
            name = attachment["name"]
            if name in records:
                raise ValueError("Duplicate source evidence attachment")
            records[name] = json.loads((results_dir / attachment["source"]).read_text())
        if "Scenario identity" not in records:
            raise ValueError("Missing source scenario identity")
        identity = records["Scenario identity"]
        case = identity["scenarioId"]
        if case in seen:
            raise ValueError("Duplicate source scenario")
        seen.add(case)
        actual = records.get(ATTACHMENT)
        expected = {**identity, "value": {"valid": True, **checks.check(identity, records)}}
        if actual != expected:
            raise ValueError("Source links differ from actual evidence: " + case)
        value = expected["value"]
        totals["scenarios"] += 1
        for field in ("exchanges", "actions", "receiptFacts"):
            totals[field] += len(value[field])
        totals["primaryActions"] += sum(w["kind"] == "primary-action" for w in value["primaryWitnesses"])
        totals["setupHttp"] += sum(w["kind"] == "setup-http" for w in value["primaryWitnesses"])
    if seen != checks.profiles.keys():
        raise ValueError("Source links do not cover all authored BDD cases")
    return totals
