#!/usr/bin/env python3
"""Check source imports against Payments layer and persistence boundaries."""

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "ecommerce_store_payments"
LAYERS = {"domain", "application", "infrastructure", "api"}
ALLOWED = {
    "domain": {"domain"},
    "application": {"application", "domain"},
    "infrastructure": {"infrastructure", "application", "domain"},
    "api": {"api", "application", "domain"},
}
CORE_FRAMEWORKS = {
    "stripe",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "pymongo",
    "bson",
    "motor",
    "httpx",
    "httpx2",
}
MONGO_DRIVERS = {"pymongo", "bson", "motor"}
HEALTH_FILE = Path("api/routes/health.py")
COMPOSITION_FILE = Path("api/app.py")
HEALTH_DATABASE = f"{PACKAGE}.infrastructure.persistence.mongodb.mongo_database"
HEALTH_DRIVER = "pymongo.errors.PyMongoError"


def imports(tree: ast.AST, package_name: str) -> list[tuple[int, str]]:
    """Return absolute names for imports, including relative and literal dynamic imports."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = (
                importlib.util.resolve_name("." * node.level + (node.module or ""), package_name)
                if node.level
                else node.module
            )
            if base:
                found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names)
        elif (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "__import__":
                found.append((node.lineno, node.args[0].value))
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == "import_module"
                and isinstance(func.value, ast.Name)
                and func.value.id == "importlib"
            ):
                found.append((node.lineno, node.args[0].value))
    return found


def check(source_root: Path = ROOT / "src" / PACKAGE) -> list[str]:
    errors: list[str] = []
    for layer in sorted(LAYERS):
        if not (source_root / layer).is_dir():
            errors.append(f"missing layer: {layer}")
    for file in sorted(source_root.rglob("*.py")):
        relative = file.relative_to(source_root)
        layer = relative.parts[0]
        if layer not in LAYERS:
            continue  # package entry point is allowed to assemble the API
        module_parts = (PACKAGE, *relative.with_suffix("").parts)
        package_name = ".".join(module_parts[:-1])
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except SyntaxError as error:
            errors.append(f"{relative}:{error.lineno}: invalid Python source: {error.msg}")
            continue
        for line, name in imports(tree, package_name):
            location = f"{relative}:{line}"
            if name.endswith(".*"):
                errors.append(f"{location}: wildcard import hides architecture dependencies: {name}")
                continue
            parts = name.split(".")
            target = parts[1] if parts[0] == PACKAGE and len(parts) > 1 else None
            if target in LAYERS and target not in ALLOWED[layer]:
                allowed_health = relative == HEALTH_FILE and name in {
                    HEALTH_DATABASE,
                    f"{HEALTH_DATABASE}.MongoDatabase",
                }
                if not (layer == "api" and (relative == COMPOSITION_FILE or allowed_health)):
                    errors.append(f"{location}: forbidden {layer} -> {target}: {name}")
            if layer in {"domain", "application"} and parts[0] in CORE_FRAMEWORKS:
                errors.append(f"{location}: framework outside adapters: {name}")
            if parts[0] in MONGO_DRIVERS and not relative.parts[:3] == ("infrastructure", "persistence", "mongodb"):
                if not (relative == HEALTH_FILE and name == HEALTH_DRIVER):
                    errors.append(f"{location}: MongoDB driver outside persistence: {name}")
            if target == "infrastructure" and "documents" in parts and layer != "infrastructure":
                errors.append(f"{location}: MongoDB document outside infrastructure: {name}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "src" / PACKAGE)
    args = parser.parse_args()
    violations = check(args.source_root)
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        sys.exit(1)
    print("Architecture boundaries verified.")


if __name__ == "__main__":
    main()
