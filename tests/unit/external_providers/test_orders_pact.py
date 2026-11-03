"""Consumer-owned examples execute the production Orders boundary over Pact HTTP."""

import asyncio
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider
from pact import Pact

from ecommerce_store_payments.application.payments.exceptions import OrderNotFoundError
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter


@dataclass(frozen=True)
class OrderExample:
    order_id: UUID
    currency: str
    total: int | float
    lines: tuple[int | float, ...]
    expected_minor: int


# Independent consumer fixtures: no provider OpenAPI, provider DTOs or generated test data.
EXAMPLES = (
    OrderExample(UUID("10000000-0000-4000-8000-000000000001"), "PLN", 0.29, (0.10, 0.19), 29),
    OrderExample(UUID("10000000-0000-4000-8000-000000000002"), "JPY", 500, (200, 300), 500),
    OrderExample(UUID("10000000-0000-4000-8000-000000000003"), "KWD", 1.234, (1, 0.234), 1234),
    OrderExample(UUID("10000000-0000-4000-8000-000000000004"), "USD", 12345.67, (12300, 45.67), 1234567),
)
MISSING_ID = UUID("10000000-0000-4000-8000-000000000099")
PACT_NAME = "payments-invoice.json"


def _order_body(example: OrderExample) -> dict[str, object]:
    # These are exactly the fields read by HttpOrderReader. Provider-only fields
    # (client/date/product metadata) do not become consumer requirements.
    return {
        "id": str(example.order_id),
        "status": "Created",
        "totalAmount": example.total,
        "totalCurrency": example.currency,
        "lines": [
            {"lineTotalAmount": amount, "productVersion": {"priceCurrency": example.currency}}
            for amount in example.lines
        ],
    }


async def _exercise_consumer(directory: Path) -> Path:
    pact = Pact("payments", "invoice").with_specification("V4")
    for example in EXAMPLES:
        (
            pact.upon_receiving(f"read a Created order in {example.currency}")
            .given(
                "a Created order exists for payment",
                orderId=str(example.order_id),
                currency=example.currency,
                totalAmount=str(example.total),
                lineAmounts=[str(amount) for amount in example.lines],
            )
            .with_request("GET", f"/orders/{example.order_id}")
            .with_header("Accept", "application/json")
            .will_respond_with(200)
            .with_body(_order_body(example), content_type="application/json")
        )
    (
        pact.upon_receiving("read an order that does not exist")
        .given("the order does not exist", orderId=str(MISSING_ID))
        .with_request("GET", f"/orders/{MISSING_ID}")
        .with_header("Accept", "application/json")
        .will_respond_with(404)
        .with_body({"status": 404}, content_type="application/problem+json")
    )

    # No MockTransport, replacement parser or direct DTO construction: the real
    # generated GET and response deserialization use the production HTTP stack.
    with pact.serve(addr="127.0.0.1") as server:
        base_url = str(server.url)
        async with AsyncClient(base_url=base_url, timeout=5, trust_env=False) as client:
            reader = HttpOrderReader(
                OrdersClient(
                    OrdersRequestAdapter(
                        AnonymousAuthenticationProvider(),
                        parse_node_factory=PreciseOrderJsonFactory(),
                        http_client=client,
                        base_url=base_url,
                    )
                )
            )
            for example in EXAMPLES:
                result = await reader.get_by_id(example.order_id)
                assert result == OrderPaymentDetails(
                    order_id=example.order_id,
                    money=Money(amount_minor=example.expected_minor, currency=example.currency),
                    status="Created",
                )
            with pytest.raises(OrderNotFoundError) as error:
                await reader.get_by_id(MISSING_ID)
            assert str(MISSING_ID) in str(error.value)
    # The default server context rejects unmatched/missing requests. Write only
    # after that verification and every application-model assertion succeeds.
    pact.write_file(directory, overwrite=True)
    return directory / PACT_NAME


async def test_orders_consumer_pact_is_reproducible_and_maps_application_results(tmp_path: Path) -> None:
    first = await _exercise_consumer(tmp_path / "first")
    second = await _exercise_consumer(tmp_path / "second")
    content = first.read_bytes()
    assert content == second.read_bytes(), "Identical source/toolchain must produce identical Pact bytes."
    document = json.loads(content)
    assert document["consumer"]["name"] == "payments"
    assert document["provider"]["name"] == "invoice"
    assert document["metadata"]["pactSpecification"]["version"] == "4.0"
    assert len(document["interactions"]) == 5

    await asyncio.to_thread(_publish_contract, first, content)


def _publish_contract(first: Path, content: bytes) -> None:
    output = Path(os.environ.get("PAYMENTS_PACT_DIR", "artifacts/verification/pact/pacts"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(first, output / PACT_NAME)  # preserve the official writer's exact bytes
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "consumer": "payments",
                "provider": "invoice",
                "pactSpecification": "4.0",
                "pactPython": version("pact-python"),
                "pactPythonFfi": version("pact-python-ffi"),
                "file": PACT_NAME,
                "sha256": hashlib.sha256(content).hexdigest(),
                "interactionCount": 5,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
