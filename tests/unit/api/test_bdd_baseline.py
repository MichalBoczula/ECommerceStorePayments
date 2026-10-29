import csv
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.bdd_baseline import (
    BASELINE,
    GAPS,
    check_bdd_results,
    check_runtime_baseline,
    check_source_baseline,
    check_tracked_sources,
    coverage_report,
    load_baseline,
    source_cases,
)
from scripts.generate_operation_links import FEATURES, MATRIX, generate
from scripts.openapi_contract import check_contract, document


def sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    features = tmp_path / "features"
    shutil.copytree(FEATURES, features)
    matrix = tmp_path / "matrix.tsv"
    gaps = tmp_path / "gaps.tsv"
    shutil.copyfile(MATRIX, matrix)
    shutil.copyfile(GAPS, gaps)
    return features, matrix, gaps


def test_original_source_inventory_and_reviewed_coverage() -> None:
    coverage = generate()["coverage"]
    assert coverage == {
        "expandedBddCases": 215,
        "matchedRouteCases": 214,
        "unmatchedRouteCases": 1,
        "declaredOperationStatusPairs": 42,
        "guaranteedScenarioStatusPairs": 27,
        "wrongMethodStatusPairs": 1,
        "gaps": sorted(
            list(csv.DictReader(GAPS.open(encoding="utf-8"), delimiter="\t")),
            key=lambda row: (row["operationId"], int(row["status"])),
        ),
    }
    assert len(coverage["gaps"]) == 15


def test_documented_direct_source_command_checks_the_guard() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_operation_links.py", "--check"],
        cwd=BASELINE.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "27/42" in result.stderr and "15 reviewed gaps" in result.stderr


def test_coordinated_source_and_matrix_removal_cannot_replace_baseline(tmp_path: Path) -> None:
    features, matrix, gaps = sources(tmp_path)
    path = features / "payments.feature"
    text = path.read_text()
    start = text.index("  Scenario: PAY11-01 ")
    stop = text.index("  Scenario: PAY11-02 ")
    path.write_text(text[:start] + text[stop:])
    matrix.write_text(
        "\n".join(row for row in matrix.read_text().splitlines() if not row.startswith("PAY11-01\t")) + "\n"
    )
    with pytest.raises(ValueError, match="Removed baseline BDD case: PAY11-01"):
        generate(matrix=matrix, feature_dir=features, gaps=gaps)


@pytest.mark.parametrize("field", ["cause", "status", "code", "requirement"])
def test_changed_original_cause_or_outcome_is_rejected(field: str, tmp_path: Path) -> None:
    features, matrix, gaps = sources(tmp_path)
    rows = list(csv.DictReader(matrix.open(), delimiter="\t"))
    row = next(row for row in rows if row["id"] == "PAY11-01")
    row[field] = {"cause": "different behavior", "status": "200", "code": "different_code", "requirement": "PAY/8"}[
        field
    ]
    with matrix.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Changed baseline cause or outcome: PAY11-01"):
        generate(matrix=matrix, feature_dir=features, gaps=gaps)


def test_original_title_is_frozen_but_additive_tables_are_allowed(tmp_path: Path) -> None:
    features, matrix, gaps = sources(tmp_path)
    path = features / "payments.feature"
    text = path.read_text().replace(
        "    Given a payable order", "    Given a payable order\n      | Amount | 1299 |", 1
    )
    path.write_text(text)
    assert generate(matrix=matrix, feature_dir=features, gaps=gaps)["coverage"]["expandedBddCases"] == 215
    path.write_text(text.replace("Create a payment from a payable order", "A replacement behavior", 1))
    with pytest.raises(ValueError, match="Changed baseline BDD identity: PAY11-01"):
        generate(matrix=matrix, feature_dir=features, gaps=gaps)


@pytest.mark.parametrize("mutation", ["skip", "duplicate_id", "duplicate_title", "wrong_result", "empty_examples"])
def test_disabled_duplicate_or_unmatched_source_is_rejected(mutation: str, tmp_path: Path) -> None:
    text = (
        'Feature: Guard\n  Scenario: PAY99-01 First\n    When action\n    Then the response matches case "PAY99-01"\n'
    )
    if mutation == "skip":
        text = text.replace("  Scenario:", "  @skip\n  Scenario:")
    elif mutation in {"duplicate_id", "duplicate_title"}:
        text += text[text.index("  Scenario:") :].replace("First", "Second" if mutation == "duplicate_id" else "First")
    elif mutation == "wrong_result":
        text = text.replace('case "PAY99-01"', 'case "PAY99-02"')
    else:
        text = text.replace("Scenario:", "Scenario Outline:") + "    Examples:\n      | value |\n"
    (tmp_path / "guard.feature").write_text(text)
    with pytest.raises(ValueError):
        source_cases(tmp_path)


def test_real_example_values_are_frozen(tmp_path: Path) -> None:
    path = tmp_path / "example.feature"
    text = (
        "Feature: Guard\n  Scenario Outline: PAY99-01 Example\n    When action <quantity>\n"
        '    Then the response matches case "PAY99-01"\n    Examples:\n      | quantity |\n      | 1 |\n'
    )
    path.write_text(text)
    matrix = {"id": "PAY99-01", "cause": "one quantity"}
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "cases": [
                    {
                        "id": "PAY99-01",
                        "feature": path.name,
                        "scenario": "PAY99-01 Example",
                        "example": {"quantity": "1"},
                        "matrix": matrix,
                    }
                ],
            }
        )
    )
    check_source_baseline(source_cases(tmp_path), [matrix], baseline)
    path.write_text(text.replace("| 1 |", "| 2 |"))
    with pytest.raises(ValueError, match="Changed baseline behavioral example"):
        check_source_baseline(source_cases(tmp_path), [matrix], baseline)


def test_new_declared_status_cannot_hide_without_reviewed_gap() -> None:
    spec = deepcopy(document())
    responses = spec["paths"]["/payments/{order_id}/pay"]["post"]["responses"]
    responses["418"] = deepcopy(responses["400"])
    with pytest.raises(ValueError, match=r"unreviewed=.*418"):
        check_contract(spec, generate())


def test_removing_uncovered_status_and_gap_cannot_remove_original_contract(tmp_path: Path) -> None:
    spec = document()
    del spec["paths"]["/payments/{order_id}/pay"]["post"]["responses"]["500"]
    gaps = tmp_path / "gaps.tsv"
    gaps.write_text(
        GAPS.read_text().replace(
            next(row for row in GAPS.read_text().splitlines(True) if row.startswith("payOrder\t500\t")), ""
        )
    )
    with pytest.raises(ValueError, match="baseline operation: payOrder"):
        coverage_report(spec, generate()["operations"], gaps)


def test_new_case_closes_gap_only_when_reviewed_gap_is_removed(tmp_path: Path) -> None:
    features, matrix, gaps = sources(tmp_path)
    with (features / "checkout.feature").open("a") as stream:
        stream.write(
            "\n  Scenario: PAY99-01 Additional checkout validation\n"
            "    An additional checkout validation case closes a reviewed declaration gap through a real result.\n"
            "    Given the health request uses\n      | Field | Value |\n      | Path | /health |\n"
            '    When action\n    Then the response matches case "PAY99-01"\n'
            "      | Field | Value |\n      | HTTPStatuses | 400 |\n"
            "      | ContentType | application/problem+json |\n      | Code | invalid_request |\n"
        )
    with matrix.open("a") as stream:
        stream.write(
            "PAY99-01\tPOST /payments/{order_id}/checkout\tadditional validation\t400\tinvalid_request\tPAY/10\n"
        )
    with pytest.raises(ValueError, match=r"stale=.*createOrderCheckout.*400"):
        generate(matrix=matrix, feature_dir=features, gaps=gaps)
    gaps.write_text(
        "\n".join(row for row in gaps.read_text().splitlines() if not row.startswith("createOrderCheckout\t400\t"))
        + "\n"
    )
    coverage = generate(matrix=matrix, feature_dir=features, gaps=gaps)["coverage"]
    assert coverage["expandedBddCases"] == 216 and coverage["guaranteedScenarioStatusPairs"] == 28
    assert len(coverage["gaps"]) == 14


@pytest.mark.parametrize("mutation", ["duplicate", "unknown_task", "empty_reason"])
def test_invalid_gap_inventory_is_rejected(mutation: str, tmp_path: Path) -> None:
    text = GAPS.read_text()
    if mutation == "duplicate":
        text += text.splitlines(True)[1]
    elif mutation == "unknown_task":
        text = text.replace("PAY-BDD-11", "PAY-BDD-99", 1)
    else:
        text = text.replace(text.splitlines()[1].split("\t")[2], "", 1)
    gaps = tmp_path / "gaps.tsv"
    gaps.write_text(text)
    with pytest.raises(ValueError, match="reviewed acceptance gap"):
        generate(gaps=gaps)


def test_wrong_method_cannot_claim_a_success_outcome() -> None:
    links = generate()
    case = next(case for op in links["operations"] for case in op["scenarios"] if case["id"] == "PAY11-18")
    case["status"] = "200"
    with pytest.raises(ValueError, match="must guarantee 405"):
        coverage_report(document(), links["operations"])


def test_runtime_identity_replacement_fails_even_at_same_total() -> None:
    members = [
        (owner, name) for owner, names in load_baseline()["suites"]["acceptance"]["members"].items() for name in names
    ]
    assert len(members) == 140
    check_runtime_baseline("acceptance", [*members, ("added", "additional_test")])
    members[0] = ("replacement", "different_test")
    with pytest.raises(ValueError, match="Removed baseline suite members"):
        check_runtime_baseline("acceptance", members)


def test_runtime_duplicate_identity_cannot_fill_a_missing_member() -> None:
    members = [
        (owner, name) for owner, names in load_baseline()["suites"]["domain"]["members"].items() for name in names
    ]
    members[0] = members[1]
    with pytest.raises(ValueError, match="duplicate JUnit identity"):
        check_runtime_baseline("domain", members, BASELINE)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "failed", "renamed", "unknown"])
def test_every_current_case_requires_one_passed_allure_result(mutation: str, tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    (features / "case.feature").write_text(
        'Feature: Guard\n  Scenario: PAY99-01 Example\n    When action\n    Then the response matches case "PAY99-01"\n'
    )
    results = tmp_path / "results"
    results.mkdir()
    good = {"name": "PAY99-01 Example", "status": "passed"}
    result_path = results / "one-result.json"
    result_path.write_text(json.dumps(good))
    check_bdd_results(features, results)
    if mutation == "missing":
        result_path.unlink()
    elif mutation == "duplicate":
        (results / "two-result.json").write_text(json.dumps(good))
    else:
        good["status" if mutation == "failed" else "name"] = {
            "failed": "broken",
            "renamed": "PAY99-01 Different",
            "unknown": "PAY99-02 Unknown",
        }[mutation]
        result_path.write_text(json.dumps(good))
    with pytest.raises(ValueError):
        check_bdd_results(features, results)


@pytest.mark.parametrize(
    "generated", ["artifacts/verification/openapi.json", ".venv/package.py", "src/__pycache__/app.pyc"]
)
def test_tracked_generated_output_is_rejected_but_kiota_is_source(generated: str) -> None:
    paths = [
        "uv.lock",
        ".python-version",
        "pyproject.toml",
        "contracts/invoice/source.json",
        "src/clients/generated/model.py",
    ]
    check_tracked_sources(paths)
    with pytest.raises(ValueError, match="Tracked generated verification output"):
        check_tracked_sources([*paths, generated])
