from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import ValidationError
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError
from scripts.generate_operation_links import generate
from scripts.openapi_contract import check_case, check_contract, document, export

from ecommerce_store_payments.infrastructure.config.settings import Settings


def test_export_lints_generated_openapi_without_mongodb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_database(_: Settings) -> None:
        raise AssertionError("Export must not connect to MongoDB")

    monkeypatch.setattr("ecommerce_store_payments.api.app.MongoDatabase", fail_database)
    output = tmp_path / "openapi.json"
    assert export(output) == (7, 52)
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert "422" not in document()["paths"]["/payments/{order_id}/pay"]["post"]["responses"]


@pytest.mark.parametrize("drift", ["missing_status", "wrong_media", "missing_schema", "phantom_422", "duplicate_id"])
def test_contract_drift_fails(drift: str) -> None:
    spec = deepcopy(document())
    pay = spec["paths"]["/payments/{order_id}/pay"]["post"]
    if drift == "missing_status":
        del pay["responses"]["504"]
    elif drift == "wrong_media":
        pay["responses"]["502"]["content"]["application/json"] = pay["responses"]["502"]["content"].pop(
            "application/problem+json"
        )
    elif drift == "missing_schema":
        del pay["responses"]["201"]["content"]["application/json"]["schema"]
    elif drift == "phantom_422":
        pay["responses"]["422"] = deepcopy(pay["responses"]["400"])
    else:
        pay["operationId"] = "getPaymentByOrderId"
    with pytest.raises((ValueError, KeyError, OpenAPIValidationError)):
        check_contract(spec, generate())


def test_actual_health_and_error_bodies_match_generated_schemas(client: TestClient) -> None:
    spec = cast(FastAPI, client.app).openapi()
    links = generate()
    live = client.get("/health/live")
    check_case(spec, links, "PAY11-19", live.status_code, live.headers["content-type"], live.json())
    invalid = client.post("/payments/invalid-uuid/pay")
    check_case(spec, links, "PAY11-14", invalid.status_code, invalid.headers["content-type"], invalid.json())
    unknown = client.get("/unknown-route")
    check_case(spec, links, "PAY11-17", unknown.status_code, unknown.headers["content-type"], unknown.json())

    with pytest.raises(ValidationError):
        check_case(spec, links, "PAY11-19", live.status_code, live.headers["content-type"], {"wrong": "shape"})
    with pytest.raises(ValueError, match="HTTP media differs"):
        check_case(spec, links, "PAY11-17", unknown.status_code, "application/json", unknown.json())
