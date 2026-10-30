"""Protect the reviewed BDD sources, declared outcomes and executed suite members."""

import csv
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pytest_bdd.gherkin_parser import Child, get_gherkin_document
from pytest_bdd.parser import FeatureParser

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/bdd-baseline.json"
GAPS = ROOT / "docs/acceptance-gaps.tsv"
DISABLED_TAGS = {"skip", "skipif", "xfail", "ignore", "ignored", "pending"}


@dataclass(frozen=True)
class SourceCase:
    feature: str
    scenario: str
    example: dict[str, str]


def load_baseline(path: Path = BASELINE) -> dict[str, Any]:
    baseline = json.loads(path.read_text(encoding="utf-8"))
    if baseline.get("schemaVersion") != 1:
        raise ValueError("Unsupported BDD baseline version")
    return baseline


def _declarations(children: list[Child]) -> int:
    return sum(1 if child.scenario else _declarations(child.rule.children) if child.rule else 0 for child in children)


def source_cases(feature_dir: Path) -> dict[str, SourceCase]:
    """Expand real pytest-bdd sources, including Rules, Backgrounds and Examples."""
    cases: dict[str, SourceCase] = {}
    for path in sorted(feature_dir.rglob("*.feature")):
        document = get_gherkin_document(str(path))
        feature = FeatureParser(str(feature_dir), path.relative_to(feature_dir).as_posix()).parse()
        if _declarations(document.feature.children) != len(feature.scenarios):
            raise ValueError(f"Duplicate source scenario title: {path.name}")
        for template in feature.scenarios.values():
            if template.keyword == "Scenario Outline" and not template.examples:
                raise ValueError(f"Outline without Examples: {template.name}")
            contexts = (
                [(context, example.tags) for example in template.examples for context in example.as_contexts()]
                if template.examples
                else [({}, set[str]())]
            )
            if not contexts:
                raise ValueError(f"Empty Examples: {template.name}")
            for context, tags in contexts:
                inherited = feature.tags | template.tags | (template.rule.tags if template.rule else set()) | tags
                if DISABLED_TAGS & {tag.split("(", 1)[0].lower() for tag in inherited}:
                    raise ValueError(f"Disabled BDD source: {template.name}")
                scenario = template.render(context)
                identity = re.match(r"(PAY\d+-\d+)\b", scenario.name)
                if identity is None:
                    raise ValueError(f"Missing source scenario ID: {scenario.name}")
                case_id = identity[1]
                if case_id in cases:
                    raise ValueError(f"Duplicate source scenario ID: {case_id}")
                result_ids = [
                    match[1]
                    for step in scenario.steps
                    if step.type == "then"
                    and (
                        match := re.fullmatch(
                            r'the (?:response|technical outcome) matches case "(PAY\d+-\d+)"', step.name
                        )
                    )
                ]
                if result_ids != [case_id]:
                    raise ValueError(f"Scenario and result steps differ: {case_id}")
                cases[case_id] = SourceCase(
                    path.relative_to(feature_dir).as_posix(),
                    scenario.name,
                    {key: str(value) for key, value in context.items()},
                )
    if not cases:
        raise ValueError("No acceptance scenario sources")
    return cases


def check_source_baseline(
    cases: dict[str, SourceCase], rows: list[dict[str, str]], baseline_path: Path = BASELINE
) -> None:
    matrix = {row["id"]: row for row in rows}
    for original in load_baseline(baseline_path)["cases"]:
        case_id = original["id"]
        current = cases.get(case_id)
        if current is None:
            raise ValueError(f"Removed baseline BDD case: {case_id}")
        if (current.feature, current.scenario) != (original["feature"], original["scenario"]):
            raise ValueError(f"Changed baseline BDD identity: {case_id}")
        if any(current.example.get(key) != value for key, value in original["example"].items()):
            raise ValueError(f"Changed baseline behavioral example: {case_id}")
        if matrix.get(case_id) != original["matrix"]:
            raise ValueError(f"Changed baseline cause or outcome: {case_id}")


def coverage_report(
    spec: dict[str, Any],
    operations: list[dict[str, Any]],
    gaps_path: Path = GAPS,
    baseline_path: Path = BASELINE,
) -> dict[str, Any]:
    """Require every declaration to have scenario intent or an explicit reviewed gap."""
    profiles = {
        operation["operationId"]: {
            "method": operation["method"],
            "path": operation["path"],
            "statuses": sorted(spec["paths"][operation["path"]][operation["method"].lower()]["responses"], key=int),
        }
        for operation in operations
    }
    for original in load_baseline(baseline_path)["operations"]:
        current = profiles.get(original["operationId"])
        if (
            current is None
            or (current["method"], current["path"]) != (original["method"], original["path"])
            or not set(original["statuses"]) <= set(current["statuses"])
        ):
            raise ValueError(f"Removed or changed baseline operation: {original['operationId']}")
    declared: set[tuple[str, str]] = set()
    covered: set[tuple[str, str]] = set()
    wrong_methods: set[tuple[str, str]] = set()
    for operation in operations:
        operation_id = operation["operationId"]
        declared.update((operation_id, status) for status in profiles[operation_id]["statuses"])
        for case in operation["scenarios"]:
            if not case["cause"].strip() or not case["code"].strip():
                raise ValueError(f"Empty scenario cause/code: {case['id']}")
            statuses = case["status"].split(",")
            if any(re.fullmatch(r"[1-5]\d\d", status) is None for status in statuses):
                raise ValueError(f"Invalid scenario status: {case['id']}")
            pairs = {(operation_id, status) for status in statuses}
            covered.update(pairs)
            if case["code"] == "method_not_allowed":
                if statuses != ["405"]:
                    raise ValueError(f"Wrong-method scenario must guarantee 405: {case['id']}")
                wrong_methods.update(pairs)
    if covered - declared:
        raise ValueError(f"Scenario status is not declared: {sorted(covered - declared)}")
    with gaps_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["operationId", "status", "reason", "task"]:
            raise ValueError("Invalid reviewed acceptance gap columns")
        gaps = list(reader)
    tasks = set(re.findall(r"\*\*(PAY-BDD-\d{2}) —", (ROOT / "docs/bdd-backlog.md").read_text(encoding="utf-8")))
    if any(
        row.keys() != {"operationId", "status", "reason", "task"}
        or not row["reason"].strip()
        or row["task"] not in tasks
        for row in gaps
    ):
        raise ValueError("Invalid reviewed acceptance gap")
    gap_pairs = [(row["operationId"], row["status"]) for row in gaps]
    if len(gap_pairs) != len(set(gap_pairs)):
        raise ValueError("Duplicate reviewed acceptance gap")
    missing = declared - covered
    if missing != set(gap_pairs):
        raise ValueError(
            f"Acceptance gaps differ; unreviewed={sorted(missing - set(gap_pairs))}; "
            f"stale={sorted(set(gap_pairs) - missing)}"
        )
    return {
        "declaredOperationStatusPairs": len(declared),
        "guaranteedScenarioStatusPairs": len(covered),
        "wrongMethodStatusPairs": len(wrong_methods),
        "gaps": sorted(gaps, key=lambda row: (row["operationId"], int(row["status"]))),
    }


def check_runtime_baseline(name: str, members: list[tuple[str, str]], baseline_path: Path = BASELINE) -> None:
    """Check executed identities, not aggregate counts which replacement tests can hide."""
    expected = Counter(
        (owner, member)
        for owner, names in load_baseline(baseline_path)["suites"][name]["members"].items()
        for member in names
    )
    actual = Counter(members)
    if any(not owner or not member for owner, member in members) or len(actual) != len(members):
        raise ValueError(f"Missing or duplicate JUnit identity: {name}")
    if missing := expected - actual:
        raise ValueError(f"Removed baseline suite members in {name}: {list(missing)}")


def check_bdd_results(feature_dir: Path, results_dir: Path) -> None:
    """New source/matrix cases cannot claim coverage without a real BDD result."""
    cases = source_cases(feature_dir)
    observed: list[str] = []
    for path in results_dir.glob("*-result.json"):
        result = json.loads(path.read_text(encoding="utf-8"))
        match = re.match(r"(PAY\d+-\d+)\b", result.get("name", ""))
        case_id = match[1] if match else ""
        if case_id not in cases or result.get("name") != cases[case_id].scenario or result.get("status") != "passed":
            raise ValueError(f"Unknown, renamed or unsuccessful BDD result: {path.name}")
        observed.append(case_id)
    if Counter(observed) != Counter(cases.keys()):
        raise ValueError("Source BDD cases differ from executed Allure cases")


def check_tracked_sources(paths: list[str]) -> None:
    """Generated Kiota source is intentional; generated verification output is not."""
    required = {"uv.lock", ".python-version", "pyproject.toml", "contracts/invoice/source.json"}
    if not required <= set(paths):
        raise ValueError(f"Missing reproducible dependency inputs: {sorted(required - set(paths))}")
    for name in paths:
        path = PurePosixPath(name)
        if (
            path.parts[0] in {".venv", "artifacts", "build", "dist", "allure-results", "allure-report", "htmlcov"}
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
            or name in {"coverage.xml", "junit.xml", ".coverage"}
        ):
            raise ValueError(f"Tracked generated verification output: {name}")


def check_repository_sources() -> None:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True)
    check_tracked_sources(result.stdout.rstrip("\0").split("\0"))
