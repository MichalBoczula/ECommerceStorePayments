from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.acceptance.evidence import table_values
from tests.acceptance.payment_checks import PaymentChecks
from tests.acceptance.technical_mongo import OwnedMongo
from tests.acceptance.technical_scenarios import TechnicalChecks

scenarios("features/technical.feature")


@pytest.fixture
def technical_checks(payment_checks: PaymentChecks) -> TechnicalChecks:
    return TechnicalChecks(payment_checks)


@given("the technical operation uses")
def configure_technical(technical_checks: TechnicalChecks, datatable: list[list[str]]) -> None:
    technical_checks.configure(table_values(datatable))


@given("populated technical collections contain")
def populate_technical(technical_checks: TechnicalChecks, datatable: list[list[str]]) -> None:
    technical_checks.ready(table_values(datatable))


@when("I execute the technical operation")
def run_technical(technical_checks: TechnicalChecks, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if technical_checks.inputs["Mode"] in {"outage", "standalone", "cancel-readiness"}:
        with OwnedMongo(replica=technical_checks.inputs["Mode"] != "standalone") as owned:
            technical_checks.run(monkeypatch, tmp_path, owned)
        technical_checks.context.evidence.observation("Owned Mongo lifecycle complete", owned.events)
    else:
        technical_checks.run(monkeypatch, tmp_path)


@then(parsers.parse('the technical outcome matches case "{case_id}"'))
def expected_technical(technical_checks: TechnicalChecks, case_id: str, datatable: list[list[str]]) -> None:
    assert technical_checks.context.evidence.identity["scenarioId"] == case_id
    technical_checks.expected(table_values(datatable))


@then("technical supporting reads preserve final state")
def support_technical(technical_checks: TechnicalChecks, datatable: list[list[str]]) -> None:
    technical_checks.support(table_values(datatable))
