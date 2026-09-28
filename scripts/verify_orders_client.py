#!/usr/bin/env python3
"""Regenerate the pinned Invoice GET /orders/{orderId} Kiota client."""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/invoice/openapi.json"
OUTPUT = ROOT / "src/ecommerce_store_payments/infrastructure/clients/orders/generated"
CONTRACT_SHA256 = "d708b5b186de6264d6530fd0cbff69f673802725007e20972e562fbf7b9ebc73"
KIOTA_VERSION = "1.34.1"


def check_contract() -> None:
    if hashlib.sha256(CONTRACT.read_bytes()).hexdigest() != CONTRACT_SHA256:
        raise ValueError("Invoice OpenAPI snapshot changed; review and pin the new upstream contract.")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    operation = contract["paths"]["/orders/{orderId}"]["get"]
    if operation["operationId"] != "GetOrderById":
        raise ValueError("Invoice Orders operation changed.")
    for schema, property_name in (
        ("OrderResponseDto", "totalAmount"),
        ("OrderLineResponseDto", "lineTotalAmount"),
    ):
        amount = contract["components"]["schemas"][schema]["properties"][property_name]
        if amount != {"type": "number", "format": "double"}:
            raise ValueError("Invoice money representation changed; revisit the exact-decimal adapter.")


def files(directory: Path, *, normalize: bool = False) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): (
            (
                "\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()).rstrip() + "\n"
            ).encode()
            if normalize and path.suffix == ".py"
            else path.read_bytes()
        )
        for path in directory.rglob("*")
        if path.is_file() and path.name != ".kiota.log" and "__pycache__" not in path.parts
    }


def run(kiota: Path, check: bool) -> None:
    check_contract()
    version = subprocess.check_output([str(kiota), "--version"], text=True).strip()
    if not version.startswith(KIOTA_VERSION + "+") and version != KIOTA_VERSION:
        raise ValueError(f"Expected Kiota {KIOTA_VERSION}, found {version}")
    with tempfile.TemporaryDirectory(prefix=".kiota-check-", dir=OUTPUT.parent) as temporary:
        generated = Path(temporary)
        subprocess.run(
            [
                str(kiota),
                "generate",
                "--language",
                "Python",
                "--class-name",
                "OrdersClient",
                "--namespace-name",
                "ecommerce_store_payments.infrastructure.clients.orders.generated",
                "--openapi",
                str(CONTRACT),
                "--output",
                str(generated),
                "--include-path",
                "/orders/{orderId}#GET",
            ],
            cwd=ROOT,
            check=True,
        )
        produced = files(generated, normalize=True)
        if check:
            committed = files(OUTPUT)
            if produced != committed:
                missing = sorted(produced.keys() ^ committed.keys())
                changed = sorted(
                    name for name in produced.keys() & committed.keys() if produced[name] != committed[name]
                )
                raise ValueError(f"Generated Invoice client drift: missing/extra={missing}, changed={changed}")
            print("Pinned Invoice OpenAPI and Kiota-generated client verified.")
        else:
            OUTPUT.mkdir(parents=True, exist_ok=True)
            for previous in OUTPUT.rglob("*"):
                if previous.is_file() and previous.name != ".kiota.log":
                    previous.unlink()
            for name, content in produced.items():
                target = OUTPUT / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kiota", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.kiota, args.check)


if __name__ == "__main__":
    main()
