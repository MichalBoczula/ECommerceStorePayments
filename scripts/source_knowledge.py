"""Source-checked semantic graph, separate from observed runtime evidence."""

import ast
import inspect
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from ecommerce_store_payments.api.routes import health
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.domain.aggregates.payments.exceptions import PaymentErrorCode
from ecommerce_store_payments.infrastructure.clients.orders.http_fulfillment import (
    HttpFulfillmentInvoices,
    HttpFulfillmentOrders,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb import fulfill_payments, replay_webhooks
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.webhook_mapper import WebhookMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.fulfillment_repository import (
    MongoFulfillmentRepository,
)
from scripts.source_catalog import CATCHES, FLOW_IDS, GUARDS, HTTP_FAILURES, METHODS, POLICIES, RECEIPTS

EXPAND = {"PaymentService", "WebhookService", "FulfillmentService"}
MODULES = {"health": health, "fulfill_payments": fulfill_payments, "replay_webhooks": replay_webhooks}


def normalize(expression: str) -> str:
    return ast.unparse(ast.parse(expression, mode="eval").body)


class SourceKnowledge:
    def __init__(self, methods: dict[str, Any] | None = None, guards: dict[str, Any] | None = None) -> None:
        from scripts import generate_operation_links as source

        self.source = source
        self.classes = {
            **source.CLASSES,
            **{
                c.__name__: c
                for c in (
                    FulfillmentService,
                    HttpFulfillmentOrders,
                    HttpFulfillmentInvoices,
                    MongoFulfillmentRepository,
                    WebhookMapper,
                )
            },
        }
        self.methods = deepcopy(METHODS if methods is None else methods)
        self.guards = deepcopy(GUARDS if guards is None else guards)
        self.objects: dict[str, Any] = {}
        for key in self.methods.keys() | POLICIES.keys():
            owner, name = key.split(".", 1)
            self.objects[key] = getattr(MODULES.get(owner) or self.classes[owner], name)
        for key, (identity, title) in POLICIES.items():
            self.methods[key] = dict(
                id="payments.method.policy-" + identity,
                title=title,
                effects=inspect.getdoc(self.objects[key]),
                failures=(
                    "Pure domain validation can reject construction/rehydration. Current safe problems "
                    "do not carry per-rule errors; public code mapping is separate."
                ),
            )
        self.source_keys = {self.qualified(value): key for key, value in self.objects.items()}
        self.rule_rows: dict[str, dict[str, Any]] = {}
        self.sites: dict[str, dict[str, Any]] = {}
        self.validate_source()

    @staticmethod
    def qualified(value: Any) -> str:
        return value.__module__ + "." + value.__qualname__

    def validate_source(self) -> None:
        ids = [m["id"] for m in self.methods.values()]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate authored method identity")
        for key, m in self.methods.items():
            if not all(isinstance(m.get(k), str) and m[k].strip() for k in ("id", "title", "effects", "failures")):
                raise ValueError("Missing source method prose: " + key)
        for key, rows in self.guards.items():
            if key not in self.objects:
                raise ValueError("Guard references unknown method: " + key)
            native = {
                ast.unparse(n.test)
                for n in ast.walk(self.source.method_tree(self.objects[key]))
                if isinstance(n, (ast.If, ast.IfExp))
            }
            declared = [normalize(row[1]) for row in rows]
            if len(declared) != len(set(declared)) or set(declared) != native:
                raise ValueError("Authored guards differ from executable source: " + key)
            if len({row[0] for row in rows}) != len(rows) or any(not row[0] or not row[2].strip() for row in rows):
                raise ValueError("Duplicate or unreadable source guard: " + key)
        # Validate the actual command composition, rather than treating port names
        # or test doubles as proof of production adapter wiring.
        native = ast.unparse(self.source.method_tree(fulfill_payments.run))
        expected = (
            "FulfillmentService(repository, payments, HttpFulfillmentOrders(client), HttpFulfillmentInvoices(client))"
        )
        if (
            expected not in native
            or "WebhookService(StripeWebhookVerifier(settings), MongoWebhookRepository(database), payments)"
            not in native
        ):
            raise ValueError("Fulfillment composition changed; review source bindings")
        if (
            "WebhookService(StripeWebhookVerifier(settings), MongoWebhookRepository(database), "
            "MongoPaymentRepository(database))"
        ) not in ast.unparse(self.source.method_tree(replay_webhooks.replay)):
            raise ValueError("Replay composition changed; review source bindings")

    def guard(self, key: str, node: ast.expr, negative: bool = False) -> dict[str, str]:
        expression = ast.unparse(node)
        rows = [row for row in self.guards.get(key, []) if normalize(row[1]) == expression]
        if len(rows) != 1:
            raise ValueError("Missing authored source guard: " + key + " " + expression)
        alias, _, prose = rows[0]
        method_id = self.methods[key]["id"].removeprefix("payments.method.")
        return dict(
            id=method_id + "." + alias + (".otherwise" if negative else ""),
            raw=("otherwise: " if negative else "") + expression,
            description=("The following does not hold: " if negative else "") + prose,
        )

    def resolve(self, key: str, call: ast.Call) -> str | None:
        owner_name = key.split(".")[0]
        if owner_name in self.classes:
            owner = self.classes[owner_name]
            if owner is FulfillmentService:
                if (
                    isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "self"
                    and call.func.attr == "_clock"
                ):
                    return None
                fields = {
                    "_work": MongoFulfillmentRepository,
                    "_payments": self.classes["MongoPaymentRepository"],
                    "_orders": HttpFulfillmentOrders,
                    "_invoices": HttpFulfillmentInvoices,
                }
                expr = call.func
                if (
                    isinstance(expr, ast.Attribute)
                    and isinstance(expr.value, ast.Attribute)
                    and isinstance(expr.value.value, ast.Name)
                    and expr.value.value.id == "self"
                    and expr.value.attr in fields
                ):
                    return fields[expr.value.attr].__name__ + "." + expr.attr
            resolved = self.source.target_for(owner, call)
            return resolved[0].__name__ + "." + resolved[1] if resolved else None
        expr = call.func
        if isinstance(expr, ast.Name):
            return owner_name + "." + expr.id if owner_name + "." + expr.id in self.objects else None
        if isinstance(expr, ast.Attribute):
            if (
                isinstance(expr.value, ast.Call)
                and isinstance(expr.value.func, ast.Name)
                and expr.value.func.id == "FulfillmentService"
            ):
                return "FulfillmentService." + expr.attr
            if isinstance(expr.value, ast.Name):
                fields = {
                    "database": "MongoDatabase",
                    "repository": "MongoFulfillmentRepository",
                    "payments": "MongoPaymentRepository",
                    "webhook_service": "WebhookService",
                    "service": "WebhookService",
                    "WebhookMapper": "WebhookMapper",
                }
                if expr.value.id in fields:
                    return fields[expr.value.id] + "." + expr.attr
        return None

    def events(self, key: str) -> list[dict[str, Any]]:
        graph = self

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.context: list[dict[str, str]] = []
                self.events: list[dict[str, Any]] = []

            def visit_If(self, n: ast.If) -> None:
                self.visit(n.test)
                for negative, body in [(False, n.body), (True, n.orelse)]:
                    if body:
                        self.context.append(graph.guard(key, n.test, negative))
                        for value in body:
                            self.visit(value)
                        self.context.pop()

            def visit_IfExp(self, n: ast.IfExp) -> None:
                self.visit(n.test)
                for negative, value in [(False, n.body), (True, n.orelse)]:
                    self.context.append(graph.guard(key, n.test, negative))
                    self.visit(value)
                    self.context.pop()

            def visit_ExceptHandler(self, n: ast.ExceptHandler) -> None:
                target = ast.unparse(n.type) if n.type else "BaseException"
                if target not in CATCHES:
                    raise ValueError("Unknown source exception guard: " + target)
                alias, prose = CATCHES[target]
                self.context.append(dict(id="caught." + alias, raw="except " + target, description=prose))
                for value in n.body:
                    self.visit(value)
                self.context.pop()

            def emit(self, kind: str, target: str, value: str = "", variant: str = "") -> None:
                meta = graph.methods[key]
                target_id = graph.methods[target]["id"].removeprefix("payments.method.") if kind == "call" else target
                local = ":".join(
                    [meta["id"].removeprefix("payments.method."), kind, target_id, *[c["id"] for c in self.context]]
                )
                if variant:
                    local += ":" + variant
                self.events.append(
                    dict(localId=local, kind=kind, target=target, expression=value, contexts=deepcopy(self.context))
                )

            def visit_Call(self, n: ast.Call) -> None:
                if isinstance(n.func, ast.Attribute):
                    self.visit(n.func.value)
                for value in [*n.args, *[k.value for k in n.keywords]]:
                    self.visit(value)
                target = graph.resolve(key, n)
                if target:
                    if target not in graph.methods:
                        raise ValueError("Missing authored call metadata: " + target)
                    code = n.args[-1] if n.args else None
                    variant = (
                        getattr(PaymentErrorCode, code.attr).value
                        if isinstance(code, ast.Attribute)
                        and isinstance(code.value, ast.Name)
                        and code.value.id == "PaymentErrorCode"
                        else ""
                    )
                    self.emit("call", target, variant=variant)

            def visit_Raise(self, n: ast.Raise) -> None:
                if n.exc:
                    self.visit(n.exc)
                target = ast.unparse(n.exc.func) if isinstance(n.exc, ast.Call) else "reraise"
                self.emit("raise", target, ast.unparse(n.exc) if n.exc else "raise")

            def visit_Return(self, n: ast.Return) -> None:
                if n.value:
                    self.visit(n.value)
                reason = "result"
                if (
                    isinstance(n.value, ast.Tuple)
                    and len(n.value.elts) > 1
                    and isinstance(n.value.elts[1], ast.Constant)
                    and n.value.elts[1].value in RECEIPTS
                ):
                    reason = n.value.elts[1].value
                self.emit("return", reason, ast.unparse(n.value) if n.value else "None")

        visitor = Visitor()
        visitor.visit(self.source.method_tree(self.objects[key]))
        ids = [v["localId"] for v in visitor.events]
        if len(ids) != len(set(ids)):
            raise ValueError("Ambiguous semantic source call/return site: " + key)
        for event in visitor.events:
            meta = self.methods[key]
            identity = "payments.site." + event["localId"]
            self.sites[identity] = dict(
                id=identity,
                methodId=meta["id"],
                source=self.qualified(self.objects[key]),
                kind=event["kind"],
                condition="; ".join(c["description"] for c in event["contexts"])
                or "This declared source site is reached",
                sourceGuards=[c["raw"] for c in event["contexts"]],
                expression=event["expression"],
                targetMethodId=self.methods[event["target"]]["id"] if event["kind"] == "call" else None,
                effects=meta["effects"],
                failures=meta["failures"],
                evidence="declared-source",
            )
        return visitor.events

    def reachable_policies(self, key: str) -> set[str]:
        reached: set[str] = set()
        result: set[str] = set()
        graph = self

        def visit(current: str) -> None:
            if current in reached:
                return
            reached.add(current)
            if current in POLICIES:
                result.add(current)
            owner, name = current.split(".", 1)
            value = getattr(MODULES.get(owner) or graph.classes[owner], name)

            class Visitor(ast.NodeVisitor):
                def visit_Call(self, n: ast.Call) -> None:
                    target = graph.resolve(current, n)
                    if target:
                        visit(target)
                    self.generic_visit(n)

            Visitor().visit(graph.source.method_tree(value))

        visit(key)
        return result

    def flow(self, alias: str, key: str, operation_id: str | None = None) -> dict[str, Any]:
        flow_id = "payments.flow." + alias
        root = self.methods[key]
        steps = []

        def visit(current: str, path: list[str], contexts: list[dict[str, str]], active: set[str]) -> None:
            if current in active:
                raise ValueError("Recursive source flow: " + current)
            for event in self.events(current):
                chain = [*path, event["localId"]]
                combined = contexts + event["contexts"]
                meta = self.methods[event["target"]] if event["kind"] == "call" else self.methods[current]
                step = dict(
                    id="payments.step." + alias + "/" + "/".join(chain),
                    sourceEventId="payments.site." + event["localId"],
                    source=self.qualified(self.objects[current]),
                    kind=event["kind"],
                    when=" and ".join(c["raw"] for c in combined),
                    condition="; ".join(c["description"] for c in combined)
                    or "When this declared source site is reached",
                    description=meta["title"]
                    if event["kind"] == "call"
                    else ("Return: " + meta["title"] if event["kind"] == "return" else "Raise " + event["target"]),
                    effects=meta["effects"],
                    failures=meta["failures"],
                    evidence="declared-source",
                )
                if event["kind"] == "call":
                    step["call"] = self.qualified(self.objects[event["target"]])
                elif event["kind"] == "raise":
                    step["raise"] = event["target"]
                    step["sourceExpression"] = event["expression"]
                else:
                    step["return"] = event["expression"]
                steps.append(step)
                if event["kind"] == "call" and event["target"].split(".")[0] in EXPAND:
                    visit(event["target"], chain, combined, active | {current})

        visit(key, [], [], set())
        if len({s["id"] for s in steps}) != len(steps):
            raise ValueError("Duplicate qualified step identity")
        return dict(
            id=flow_id,
            source=self.qualified(self.objects[key]),
            description=inspect.getdoc(self.objects[key]) or root["title"],
            title=root["title"],
            condition="The entry is selected by its HTTP route or explicit operator command",
            effects=root["effects"],
            failures=root["failures"],
            operationId=operation_id,
            kind="http" if operation_id else "command",
            evidence="declared-source",
            steps=steps,
        )

    def policies(self) -> list[dict[str, Any]]:
        result = []
        for key, (alias, title) in POLICIES.items():
            source = self.objects[key]
            rules = []
            for event in self.events(key):
                if event["kind"] != "raise":
                    continue
                identity = "payments.rule." + event["localId"]
                row = dict(
                    id=identity,
                    source=self.qualified(source),
                    sourceEventId="payments.site." + event["localId"],
                    description=title,
                    condition="; ".join(c["description"] for c in event["contexts"])
                    or "The source validation site rejects its input",
                    sourceGuards=[c["raw"] for c in event["contexts"]],
                    effects="Reject invalid domain construction/rehydration before returning a valid aggregate",
                    failures="Raises "
                    + event["target"]
                    + "; public error signatures remain separate from per-rule execution evidence",
                    sourceFailure=event["expression"],
                    evidence="declared-source",
                    httpObservation=(
                        "Current API problems have no per-rule error entries; "
                        "a public code alone is not execution telemetry"
                    ),
                )
                if identity in self.rule_rows:
                    raise ValueError("Duplicate source rule identity")
                self.rule_rows[identity] = row
                rules.append(identity)
            result.append(
                dict(
                    id="payments.policy." + alias,
                    source=self.qualified(source),
                    description=inspect.getdoc(source),
                    title=title,
                    conditions=[
                        ast.unparse(n.test) for n in ast.walk(self.source.method_tree(source)) if isinstance(n, ast.If)
                    ],
                    condition="The constructor, rehydration or transition invokes this pure validation method",
                    effects=self.methods[key]["effects"],
                    failures=self.methods[key]["failures"],
                    ruleIds=rules,
                    evidence="declared-source",
                )
            )
        return result


def enrich(
    links: dict[str, Any],
    feature_dir: Path | None = None,
    methods: dict[str, Any] | None = None,
    guards: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = SourceKnowledge(methods, guards)
    policies = graph.policies()
    by_source = {p["source"]: p for p in policies}
    flows = []
    outcomes = []
    for operation in links["operations"]:
        key = graph.source_keys[operation["flow"]["source"]]
        alias = FLOW_IDS[operation["operationId"]]
        flow = graph.flow(alias, key, operation["operationId"])
        operation["policies"] = [deepcopy(by_source[p["source"]]) for p in operation["policies"]]
        actual = {graph.qualified(graph.objects[k]) for k in graph.reachable_policies(key)}
        if actual != {p["source"] for p in operation["policies"]}:
            raise ValueError("Policy reachability differs from executable graph")
        flow["policyIds"] = [p["id"] for p in operation["policies"]]
        flow["ruleIds"] = sorted({r for p in operation["policies"] for r in p["ruleIds"]})
        operation["flow"] = flow
        flows.append(flow)
        statuses = sorted({int(s) for case in operation["scenarios"] for s in case["status"].split(",")})
        for status in statuses:
            condition, effects, failures = HTTP_FAILURES.get(
                status,
                (
                    "The selected operation completes with its declared success response",
                    flow["effects"],
                    flow["failures"],
                ),
            )
            if status < 400 and operation["operationId"] == "receiveStripeWebhook":
                effects = (
                    "Acknowledge accepted delivery; inspect the durable receipt state/reason separately from HTTP 200"
                )
            identity = "payments.outcome." + alias + ".http-" + str(status)
            outcomes.append(
                dict(
                    id=identity,
                    flowId=flow["id"],
                    operationId=operation["operationId"],
                    status=status,
                    condition=condition,
                    effects=effects,
                    failures=failures,
                    evidence="declared-outcome-family",
                )
            )
        for case in operation["scenarios"]:
            case["outcomeIds"] = ["payments.outcome." + alias + ".http-" + s for s in case["status"].split(",")]
    commands = []
    for name, root, cli in [
        ("fulfill", "fulfill_payments.run", "fulfill_payments.main"),
        ("replay", "replay_webhooks.replay", "replay_webhooks.main"),
    ]:
        flow = graph.flow(name, root)
        # Both commands rehydrate persisted payments; fulfill also replays receipts.
        reached = {by_source[graph.qualified(graph.objects[k])]["id"] for k in graph.reachable_policies(root)}
        flow.update(
            policyIds=sorted(reached), ruleIds=sorted({r for p in policies if p["id"] in reached for r in p["ruleIds"]})
        )
        flows.append(flow)
        commands.append(
            dict(
                id="payments.command." + name,
                name=name,
                flowId=flow["id"],
                source=graph.qualified(graph.objects[root]),
                cliSource=graph.qualified(graph.objects[cli]),
                condition=graph.methods[root]["title"],
                effects=graph.methods[root]["effects"],
                failures=graph.methods[root]["failures"],
                cliGuards=[
                    dict(
                        id="payments.guard." + graph.methods[cli]["id"].removeprefix("payments.method.") + "." + r[0],
                        sourceExpression=normalize(r[1]),
                        description=r[2],
                    )
                    for r in GUARDS[cli]
                ],
            )
        )
    receipt_rows = []
    native = graph.source.method_tree(graph.objects["WebhookService._apply"])
    reasons = {
        n.value.elts[1].value
        for n in ast.walk(native)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Tuple)
        and len(n.value.elts) > 1
        and isinstance(n.value.elts[1], ast.Constant)
    }
    if reasons != RECEIPTS.keys():
        raise ValueError("Receipt reason catalogue differs from source")
    for reason, (state, condition, effects) in RECEIPTS.items():
        actual_states = {
            ast.unparse(n.value.elts[0]).split(".")[-1].lower()
            for n in ast.walk(native)
            if isinstance(n, ast.Return)
            and isinstance(n.value, ast.Tuple)
            and len(n.value.elts) > 1
            and isinstance(n.value.elts[1], ast.Constant)
            and n.value.elts[1].value == reason
        }
        if actual_states != {state}:
            raise ValueError("Receipt state/reason binding differs from source")
        receipt_rows.append(
            dict(
                id="payments.receipt." + reason,
                reason=reason,
                state=state,
                source=graph.qualified(graph.objects["WebhookService._apply"]),
                condition=condition,
                effects=effects,
                failures=(
                    "A recorded receipt fact does not prove which internal branch ran "
                    "or which request caused an existing snapshot"
                ),
                evidence="declared-receipt-reason",
            )
        )
    for key in graph.guards:
        for event in graph.events(key):
            if event["kind"] != "raise" or key in POLICIES:
                continue
            identity = "payments.rule." + event["localId"]
            graph.rule_rows[identity] = dict(
                id=identity,
                source=graph.qualified(graph.objects[key]),
                sourceEventId="payments.site." + event["localId"],
                description=graph.methods[key]["title"],
                condition="; ".join(c["description"] for c in event["contexts"])
                or "This declared rejection site is reached",
                sourceGuards=[c["raw"] for c in event["contexts"]],
                effects="Raise the declared failure; existing durable progress is determined by state evidence",
                failures=graph.methods[key]["failures"],
                sourceFailure=event["expression"],
                evidence="declared-source",
                httpObservation="Public error codes are signatures, not internal rule-execution telemetry",
            )
    for flow in flows:
        flow["ruleIds"] = sorted(
            set(flow["ruleIds"])
            | {
                "payments.rule." + s["sourceEventId"].removeprefix("payments.site.")
                for s in flow["steps"]
                if s["kind"] == "raise"
            }
        )
        flow["projection"] = "Possible source evaluation order, including alternative branches; not a runtime trace"
    for p in policies:
        key = graph.source_keys[p["source"]]
        p["dependencyPolicyIds"] = sorted(
            "payments.policy." + POLICIES[k][0] for k in graph.reachable_policies(key) if k != key
        )
    outcomes.append(
        dict(
            id="payments.outcome.routing.http-404",
            flowId=None,
            operationId=None,
            status=404,
            condition="No application route matches the decoded request path",
            effects="Return the safe route_not_found problem",
            failures="No named operation execution is claimed",
            evidence="declared-outcome-family",
        )
    )
    for row in links["technicalScenarios"]:
        outcomes.append(
            dict(
                id="payments.outcome.technical." + row["id"].lower(),
                flowId=None,
                operationId=row["operationId"],
                status=int(row["status"]) if row["kind"] == "response" else None,
                condition=row["cause"],
                effects="Observe the explicit technical response, cancellation or action result: " + row["result"],
                failures=(
                    "An exercise can include recovery; an action is not an invented "
                    "HTTP response or single command exit"
                ),
                evidence="declared-technical-family",
            )
        )
    for kind in ["cancelled", "failure"]:
        outcomes.append(
            dict(
                id="payments.outcome.transport." + kind,
                flowId=None,
                operationId=None,
                status=None,
                condition="The actual exchange did not complete"
                + (" because it was cancelled" if kind == "cancelled" else ""),
                effects="Preserve the actual request and safe failure type without a response",
                failures="No HTTP status or downstream nonacceptance is inferred",
                evidence="declared-transport-family",
            )
        )
    for name in ["fulfill", "replay"]:
        outcomes.append(
            dict(
                id="payments.outcome.command." + name,
                flowId="payments.flow." + name,
                operationId=None,
                status=None,
                condition="An explicitly identified command action runs in its recorded scenario phase",
                effects="Keep the actual action result/failure and durable snapshots",
                failures=(
                    "An action can contain several invocations or cancellation followed by recovery; "
                    "no branch or command exit is inferred"
                ),
                evidence="declared-command-family",
            )
        )
    method_rows = [dict(source=graph.qualified(graph.objects[k]), **m) for k, m in graph.methods.items()]
    catalog = dict(
        schemaVersion=1,
        flows=flows,
        policies=policies,
        rules=list(graph.rule_rows.values()),
        outcomes=outcomes,
        commands=commands,
        receiptReasons=receipt_rows,
        methods=method_rows,
        sites=sorted(graph.sites.values(), key=lambda r: r["id"]),
        executionClaim=(
            "Source intent and actual exchange/action facts are distinct; no executed steps/branches/rules are inferred"
        ),
        rag="Prepared source/evidence references only; no ingestion, retrieval or evaluation service",
    )
    links["knowledge"] = catalog
    from scripts.source_links import scenario_bindings

    catalog["scenarioBindings"] = scenario_bindings(links, feature_dir or graph.source.FEATURES)
    validate_catalog(links)
    return links


def validate_catalog(links: dict[str, Any]) -> None:
    catalog = links["knowledge"]
    all_rows = [
        *catalog["flows"],
        *catalog["policies"],
        *catalog["rules"],
        *catalog["outcomes"],
        *catalog["commands"],
        *catalog["receiptReasons"],
        *catalog["methods"],
        *catalog["sites"],
    ]
    all_rows.extend(s for f in catalog["flows"] for s in f["steps"])
    ids = [r["id"] for r in all_rows]
    if len(ids) != len(set(ids)) or any(re.fullmatch(r"payments\.[a-z][A-Za-z0-9_.:/-]*", v) is None for v in ids):
        raise ValueError("Invalid or duplicate global source identity")
    for row in all_rows:
        for field in ["effects", "failures"]:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError("Missing authored source " + field)
        if not (row.get("condition") or row.get("title")):
            raise ValueError("Missing readable source condition/title")
    flows = {f["id"]: f for f in catalog["flows"]}
    policies = {p["id"]: p for p in catalog["policies"]}
    rules = {r["id"]: r for r in catalog["rules"]}
    sites = {s["id"]: s for s in catalog["sites"]}
    methods = {m["id"]: m for m in catalog["methods"]}
    for site in sites.values():
        if site["methodId"] not in methods or site["source"] != methods[site["methodId"]]["source"]:
            raise ValueError("Unknown source site owner")
        if site["targetMethodId"] is not None and site["targetMethodId"] not in methods:
            raise ValueError("Unknown source call target")
    for row in [*rules.values(), *(s for f in flows.values() for s in f["steps"])]:
        if row["sourceEventId"] not in sites or row["source"] != sites[row["sourceEventId"]]["source"]:
            raise ValueError("Unknown source event reference")
    for flow in flows.values():
        if any(p not in policies for p in flow["policyIds"]) or any(r not in rules for r in flow["ruleIds"]):
            raise ValueError("Unknown flow policy/rule reference")
        if any(
            rules[r]["source"]
            not in {policies[p]["source"] for p in flow["policyIds"]} | {s["source"] for s in flow["steps"]}
            for r in flow["ruleIds"]
        ):
            raise ValueError("Unrelated flow rule reference")
    for policy in policies.values():
        if any(r not in rules or rules[r]["source"] != policy["source"] for r in policy["ruleIds"]):
            raise ValueError("Unrelated policy rule membership")
        if any(p not in policies for p in policy["dependencyPolicyIds"]):
            raise ValueError("Unknown policy dependency")
    for op in links["operations"]:
        if op["flow"]["id"] not in flows or op["flow"]["operationId"] != op["operationId"]:
            raise ValueError("HTTP flow ownership drift")
        families = {
            o["status"]
            for o in catalog["outcomes"]
            if o["operationId"] == op["operationId"] and o["flowId"] == op["flow"]["id"]
        }
        if families != {int(s) for c in op["scenarios"] for s in c["status"].split(",")}:
            raise ValueError("Outcome family/status drift")
    for cmd in catalog["commands"]:
        if cmd["flowId"] not in flows or flows[cmd["flowId"]]["kind"] != "command":
            raise ValueError("Unknown command flow")
