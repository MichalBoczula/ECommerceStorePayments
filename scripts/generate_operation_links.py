#!/usr/bin/env python3
"""Project HTTP operations, executed service flows, domain rules and BDD scenarios from source."""

import argparse
import ast
import csv
import inspect
import json
import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.api.routes.payments import router as payments_router
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.payment_policy import PaymentPolicy
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import StripeCheckoutProvider
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/acceptance-matrix.tsv"
FEATURES = ROOT / "tests/acceptance/features"
ROUTERS = (health_router, payments_router)
CLASSES = {
    cls.__name__: cls
    for cls in (
        PaymentService,
        Payment,
        PaymentPolicy,
        Money,
        HttpOrderReader,
        StripeCheckoutProvider,
        PaymentMapper,
        MongoDatabase,
        MongoPaymentRepository,
    )
}
PAYMENT_VARIABLES = {"payment", "existing_payment", "current"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def method_tree(method: Any) -> ast.FunctionDef | ast.AsyncFunctionDef:
    source = textwrap.dedent(inspect.getsource(method))
    return next(node for node in ast.parse(source).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))


def composition_fields() -> dict[str, dict[str, type[Any]]]:
    """Resolve concrete field implementations from create_app and constructor assignments."""
    root = method_tree(create_app)
    assignments = [node for node in ast.walk(root) if isinstance(node, ast.Assign)]
    fields: dict[str, dict[str, type[Any]]] = defaultdict(dict)

    def constructor(expression: ast.expr) -> ast.Call | None:
        if isinstance(expression, ast.Name):
            matches = [
                node.value
                for node in assignments
                if any(isinstance(target, ast.Name) and target.id == expression.id for target in node.targets)
            ]
            require(len(matches) <= 1, f"Ambiguous composition variable: {expression.id}")
            return constructor(matches[0]) if matches else None
        if isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name) and expression.func.id in CLASSES:
            return expression
        return None

    def visit(owner: type[Any], call: ast.Call) -> None:
        parameters = list(inspect.signature(owner).parameters)
        arguments = dict(zip(parameters, call.args, strict=False))
        arguments.update({keyword.arg: keyword.value for keyword in call.keywords if keyword.arg})
        for node in ast.walk(method_tree(owner.__init__)):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Name):
                continue
            for target in node.targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    continue
                argument = arguments.get(node.value.id)
                nested = constructor(argument) if argument is not None else None
                if nested is None:
                    continue
                assert isinstance(nested.func, ast.Name)
                target_owner = CLASSES[nested.func.id]
                fields[owner.__name__][target.attr] = target_owner
                visit(target_owner, nested)

    service_calls = [
        node
        for node in ast.walk(root)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "PaymentService"
    ]
    require(len(service_calls) == 1, "Missing or ambiguous PaymentService composition")
    visit(PaymentService, service_calls[0])
    require(
        fields.get("PaymentService", {}).keys() == {"_payment_repository", "_order_reader", "_checkout_provider"}
        and fields.get("MongoPaymentRepository", {}).keys() == {"_database"},
        "Unresolved payment service composition",
    )
    return fields


FIELDS = composition_fields()


def target_for(owner: type[Any], call: ast.Call) -> tuple[type[Any], str] | None:
    expression = call.func
    if isinstance(expression, ast.Name):
        if owner is Payment and expression.id == "cls":
            return Payment, "__init__"
        if expression.id == "Money":
            return Money, "__post_init__"
        return None
    if not isinstance(expression, ast.Attribute):
        return None

    receiver = expression.value
    resolved: type[Any] | None = None
    if isinstance(receiver, ast.Name):
        if receiver.id in CLASSES:
            resolved = CLASSES[receiver.id]
        elif receiver.id in {"self", "cls"}:
            resolved = owner
        elif owner is PaymentService and receiver.id in PAYMENT_VARIABLES:
            resolved = Payment
        elif owner is PaymentService and receiver.id == "provider":
            resolved = FIELDS["PaymentService"]["_checkout_provider"]
        elif receiver.id == "database" and owner.__name__ == "ApiRoute":
            resolved = MongoDatabase
        elif receiver.id == "payment_service" and owner.__name__ == "ApiRoute":
            resolved = PaymentService
    elif isinstance(receiver, ast.Attribute) and isinstance(receiver.value, ast.Name) and receiver.value.id == "self":
        resolved = FIELDS.get(owner.__name__, {}).get(receiver.attr)
    if resolved is None:
        return None
    require(call.func.attr in vars(resolved), f"Unknown linked call: {resolved.__name__}.{call.func.attr}")
    return resolved, call.func.attr


class Calls(ast.NodeVisitor):
    def __init__(self, owner: type[Any]) -> None:
        self.owner = owner
        self.context: list[str] = []
        self.calls: list[tuple[type[Any], str, str]] = []
        self.raises: list[tuple[str, str]] = []
        self.events: list[tuple[str, Any, str]] = []

    def visit_If(self, node: ast.If) -> None:
        condition = ast.unparse(node.test)
        self.context.append(condition)
        for item in node.body:
            self.visit(item)
        self.context.pop()
        if node.orelse:
            self.context.append(f"otherwise: {condition}")
            for item in node.orelse:
                self.visit(item)
            self.context.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.context.append(f"except {ast.unparse(node.type) if node.type else 'Exception'}")
        for item in node.body:
            self.visit(item)
        self.context.pop()

    def visit_Call(self, node: ast.Call) -> None:
        target = target_for(self.owner, node)
        if target is not None:
            condition = " and ".join(self.context)
            self.calls.append((*target, condition))
            self.events.append(("call", target, condition))
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        if isinstance(node.exc, ast.Call):
            raised = ast.unparse(node.exc.func)
            condition = " and ".join(self.context)
            self.raises.append((raised, condition))
            self.events.append(("raise", raised, condition))
        self.generic_visit(node)


def calls_in(owner: type[Any], name: str) -> Calls:
    method = getattr(owner, name)
    visitor = Calls(owner)
    visitor.visit(method_tree(method))
    return visitor


def source_name(owner: type[Any], name: str) -> str:
    return f"{owner.__module__}.{owner.__name__}.{name}"


def policy_details(owner: type[Any], name: str) -> dict[str, Any]:
    method = getattr(owner, name)
    description = inspect.getdoc(method)
    require(bool(description), f"Missing policy description: {owner.__name__}.{name}")
    conditions = [ast.unparse(node.test) for node in ast.walk(method_tree(method)) if isinstance(node, ast.If)]
    return {"source": source_name(owner, name), "description": description, "conditions": conditions}


def execution(root: tuple[type[Any], str]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    steps: list[dict[str, str]] = []
    reached: set[tuple[type[Any], str]] = set()
    policies: set[tuple[type[Any], str]] = set()

    def walk_policies(owner: type[Any], name: str) -> None:
        identity = (owner, name)
        if identity in reached:
            return
        reached.add(identity)
        if owner is PaymentPolicy or (owner is Money and name == "_validate"):
            policies.add(identity)
        visitor = calls_in(owner, name)
        for target_owner, target_name, _ in visitor.calls:
            walk_policies(target_owner, target_name)

    def walk_flow(
        owner: type[Any], name: str, context: str = "", active: frozenset[tuple[type[Any], str]] = frozenset()
    ) -> None:
        identity = (owner, name)
        require(identity not in active, f"Recursive application flow: {source_name(owner, name)}")
        for kind, value, condition in calls_in(owner, name).events:
            combined = " and ".join(part for part in (context, condition) if part)
            if kind == "raise":
                steps.append({"source": source_name(owner, name), "raise": value, "when": combined})
            else:
                target_owner, target_name = value
                steps.append(
                    {
                        "source": source_name(owner, name),
                        "call": source_name(target_owner, target_name),
                        "when": combined,
                    }
                )
                if target_owner is PaymentService:
                    walk_flow(target_owner, target_name, combined, active | {identity})

    walk_policies(*root)
    walk_flow(*root)
    return steps, [policy_details(owner, name) for owner, name in sorted(policies, key=lambda item: source_name(*item))]


def source_scenarios(feature_dir: Path) -> set[str]:
    scenario_ids: list[str] = []
    step_ids: list[str] = []
    for path in sorted(feature_dir.glob("*.feature")):
        source = path.read_text(encoding="utf-8")
        scenario_ids.extend(re.findall(r"^\s*Scenario:\s+(PAY\d+-\d+)\b", source, re.MULTILINE))
        step_ids.extend(re.findall(r'^\s*Then the response matches case "(PAY\d+-\d+)"', source, re.MULTILINE))
    require(bool(scenario_ids), "No acceptance scenario sources")
    require(len(scenario_ids) == len(set(scenario_ids)), "Duplicate source scenario ID")
    require(Counter(scenario_ids) == Counter(step_ids), "Scenario and result steps differ")
    return set(scenario_ids)


def scenario_links(
    routes: list[APIRoute], matrix: Path, feature_dir: Path
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    with matrix.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require(bool(rows), "Empty acceptance matrix")
    expected_fields = {"id", "operation", "cause", "status", "code", "requirement"}
    require(all(row.keys() == expected_fields for row in rows), "Invalid acceptance matrix columns")
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate matrix scenario ID")
    require(set(ids) == source_scenarios(feature_dir), "Matrix and source scenarios differ")
    requirements = set(
        re.findall(r"\*\*((?:PAY|STRIPE)/\d+)\s+—", (ROOT / "TECHNICAL_TODO.md").read_text(encoding="utf-8"))
    )
    links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched: list[dict[str, Any]] = []
    for row in rows:
        require(row["requirement"] in requirements, f"Unknown requirement: {row['id']}")
        verb, path = row["operation"].removesuffix(" x2").split(" ", 1)
        path_matches = [route for route in routes if route.path == path or route.path_regex.fullmatch(path)]
        match = [route for route in path_matches if verb in route.methods]
        if row["code"] == "route_not_found":
            require(not path_matches, f"Known route marked missing: {row['id']}")
            unmatched.append(row)
            continue
        if row["code"] == "method_not_allowed":
            require(len(path_matches) == 1 and not match, f"Method mismatch stale: {row['id']}")
            match = path_matches
        require(len(match) == 1, f"Orphan or ambiguous scenario route: {row['id']}: {row['operation']}")
        links[match[0].operation_id].append(
            {
                "id": row["id"],
                "requirement": row["requirement"],
                "cause": row["cause"],
                "status": row["status"],
                "code": row["code"],
            }
        )
    return links, unmatched


def generate(matrix: Path = MATRIX, feature_dir: Path = FEATURES, app: Any = None) -> dict[str, Any]:
    app = app or create_app()
    routes = [route for router in ROUTERS for route in router.routes if isinstance(route, APIRoute)]
    ids = [route.operation_id for route in routes]
    require(all(ids) and len(ids) == len(set(ids)), "Missing or duplicate operationId")
    declared = {(route.path, method, route.operation_id) for route in routes for method in route.methods}
    published = {
        (path, method.upper(), operation["operationId"])
        for path, methods in app.openapi()["paths"].items()
        for method, operation in methods.items()
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    require(declared == published, f"Router and generated OpenAPI operations differ: {declared ^ published}")
    links, unmatched = scenario_links(routes, matrix, feature_dir)
    operations = []
    for route in routes:
        assert route.operation_id is not None
        endpoint_tree = method_tree(route.endpoint)
        endpoint_calls = Calls(type("ApiRoute", (), {}))
        endpoint_calls.visit(endpoint_tree)
        services = [(owner, name) for owner, name, _ in endpoint_calls.calls if owner is PaymentService]
        require(len(services) <= 1, f"Ambiguous service flow: {route.operation_id}")
        if route.path.startswith("/payments"):
            require(len(services) == 1, f"Missing executed service flow: {route.operation_id}")
        else:
            require(not services, f"Unexpected service flow in technical route: {route.operation_id}")
        root = services[0] if services else None
        if root:
            description = inspect.getdoc(getattr(*root))
            require(bool(description), f"Missing flow description: {route.operation_id}")
            steps, policies = execution(root)
            require(bool(steps) and bool(policies), f"Unlinked flow or policies: {route.operation_id}")
            flow_source = source_name(*root)
        else:
            description = inspect.getdoc(route.endpoint)
            require(bool(description), f"Missing technical flow description: {route.operation_id}")
            steps = [
                {
                    "source": f"{route.endpoint.__module__}.{route.endpoint.__name__}",
                    "call": source_name(owner, name),
                    "when": condition,
                }
                for owner, name, condition in endpoint_calls.calls
            ]
            policies = []
            flow_source = f"{route.endpoint.__module__}.{route.endpoint.__name__}"
        require(bool(links.get(route.operation_id)), f"Operation without acceptance scenario: {route.operation_id}")
        operations.append(
            {
                "operationId": route.operation_id,
                "method": next(iter(route.methods)),
                "path": route.path,
                "flow": {"source": flow_source, "description": description, "steps": steps},
                "policies": policies,
                "scenarios": links[route.operation_id],
            }
        )
    return {"service": "ECommerceStorePayments", "operations": operations, "unmatchedRouteScenarios": unmatched}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the generated JSON to a file (stdout by default)")
    parser.add_argument("--check", action="store_true", help="Validate links without emitting JSON")
    args = parser.parse_args()
    try:
        result = generate()
        if not args.check:
            output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(output, encoding="utf-8")
            else:
                print(output, end="")
        print(f"Linked {len(result['operations'])} operations to flows, policies and scenarios", file=sys.stderr)
    except (AssertionError, OSError, TypeError, ValueError) as error:
        print(f"Operation link error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
