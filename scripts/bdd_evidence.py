"""Verify authored tables and actual immutable BDD attachments before publication."""

import base64
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from pytest_bdd.parser import FeatureParser

from scripts.bdd_baseline import source_cases


def instance_id(scenario_id: str, parameters: Mapping[str, str]) -> str:
    canonical = json.dumps(
        {"scenarioId": scenario_id, "parameters": dict(sorted(parameters.items()))},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def source_evidence(feature_dir: Path) -> dict[str, dict[str, Any]]:
    cases = source_cases(feature_dir)
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(feature_dir.rglob("*.feature")):
        feature = FeatureParser(str(feature_dir), path.relative_to(feature_dir).as_posix()).parse()
        for template in feature.scenarios.values():
            contexts = [context for examples in template.examples for context in examples.as_contexts()] or [{}]
            for context in contexts:
                scenario = template.render(context)
                case_id = scenario.name.split()[0]
                tables: dict[str, dict[str, str]] = {}
                for step in scenario.steps:
                    if step.datatable is None:
                        continue
                    table = [[cell.value for cell in row.cells] for row in step.datatable.rows]
                    if table[0] != ["Field", "Value"] or any(len(row) != 2 for row in table[1:]):
                        raise ValueError(f"Invalid evidence table: {case_id}")
                    values = dict(table[1:])
                    if len(values) != len(table) - 1 or not values or any(not k or not v for k, v in values.items()):
                        raise ValueError(f"Empty or duplicate evidence table: {case_id}")
                    if step.name in {"the order fixture contains", "the health request uses"}:
                        if "inputs" in tables:
                            raise ValueError(f"Duplicate input table: {case_id}")
                        tables["inputs"] = values
                    if step.name == f'the response matches case "{case_id}"':
                        tables["expected"] = values
                description = (scenario.description or "").strip()
                if len(description.split()) < 10 or "inputs" not in tables or "expected" not in tables:
                    raise ValueError(f"Readable description and executable input/expected tables required: {case_id}")
                if not {"HTTPStatuses", "ContentType", "Code"} <= tables["expected"].keys():
                    raise ValueError(f"Incomplete expected HTTP table: {case_id}")
                profiles[case_id] = {
                    "description": description,
                    "feature": feature.name,
                    "scenario": scenario.name,
                    "parameters": cases[case_id].example,
                    **tables,
                }
    return profiles


def check_source_evidence(feature_dir: Path, matrix: Path) -> None:
    profiles = source_evidence(feature_dir)
    with matrix.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            expected = profiles[row["id"]]["expected"]
            media = "application/problem+json" if int(row["status"].split(",")[0]) >= 400 else "application/json"
            if (
                expected["HTTPStatuses"] != row["status"]
                or expected["Code"] != row["code"]
                or expected["ContentType"] != media
            ):
                raise ValueError(f"Authored HTTP table and matrix differ: {row['id']}")


def attachments(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield from value.get("attachments", [])
        for key, child in value.items():
            if key != "attachments":
                yield from attachments(child)
    elif isinstance(value, list):
        for child in value:
            yield from attachments(child)


def check_content(content: dict[str, Any]) -> None:
    body = base64.b64decode(content["bodyBytesBase64"], validate=True)
    if len(body) != content["byteLength"] or hashlib.sha256(body).hexdigest() != content["sha256"]:
        raise ValueError("Captured HTTP bytes differ from digest or length")
    if content["rawBody"] is not None and content["rawBody"].encode() != body:
        raise ValueError("Captured HTTP raw text differs from bytes")
    if content["bodyFormat"] == "json" and json.loads(body) != content["body"]:
        raise ValueError("Captured parsed JSON differs from bytes")


def check_result_evidence(result: dict[str, Any], profile: dict[str, Any], results_dir: Path) -> None:
    case_id = result["name"].split()[0]
    identity = {
        "service": "payments",
        "scenarioId": case_id,
        "instanceId": instance_id(case_id, profile["parameters"]),
        "feature": profile["feature"],
        "scenario": profile["scenario"],
        "parameters": profile["parameters"],
    }
    for name in ("service", "scenarioId", "instanceId"):
        if [label["value"] for label in result.get("labels", []) if label["name"] == name] != [identity[name]]:
            raise ValueError(f"Missing or duplicate evidence label: {case_id} {name}")
    if result.get("description") != profile["description"]:
        raise ValueError(f"Missing or changed authored description: {case_id}")
    records: dict[str, Any] = {}
    tables: list[dict[str, str]] = []
    for attachment in attachments(result):
        source = attachment["source"]
        if Path(source).name != source or not (results_dir / source).is_file():
            raise ValueError(f"Missing or unsafe attachment: {source}")
        if attachment["type"] == "text/csv":
            rows = list(csv.reader(io.StringIO((results_dir / source).read_text())))
            if not rows or rows[0] != ["Field", "Value"] or any(len(row) != 2 for row in rows[1:]):
                raise ValueError(f"Invalid rendered Gherkin table: {case_id}")
            tables.append(dict(rows[1:]))
        if attachment["type"] != "application/json":
            continue
        if attachment["name"] in records:
            raise ValueError(f"Duplicate evidence attachment: {case_id} {attachment['name']}")
        record = json.loads((results_dir / source).read_text())
        if any(record.get(key) != value for key, value in identity.items()):
            raise ValueError(f"Foreign evidence identity: {case_id}")
        records[attachment["name"]] = record
    if (
        profile["inputs"] not in tables
        or profile["expected"] not in tables
        or records.get("Scenario identity") != identity
    ):
        raise ValueError(f"Missing identity or rendered tables: {case_id}")
    if records.get("Scenario inputs", {}).get("value") != profile["inputs"]:
        raise ValueError(f"Missing or changed executed inputs: {case_id}")
    expectation = records.get("Expected response", {})
    if expectation.get("value") != profile["expected"]:
        raise ValueError(f"Missing or changed executed expectations: {case_id}")
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actions: dict[str, list[str]] = defaultdict(list)
    for name, record in records.items():
        kind = record.get("kind", "")
        if kind in {"request", "response", "failure"}:
            sequence = record["sequence"]
            if name != f"HTTP {sequence:03} {kind}" or record["exchangeId"] != f"{identity['instanceId']}/{sequence}":
                raise ValueError(f"Invalid HTTP sequence: {case_id}")
            if record["stepPhase"] not in {"Setup", "Given", "When", "Then"}:
                raise ValueError(f"Invalid HTTP phase: {case_id}")
            if kind != "failure":
                check_content(record["content"])
            pairs[record["exchangeId"]].append(record)
        if kind.startswith("action-"):
            actions[record["actionId"]].append(kind)
    for pair in pairs.values():
        kinds = Counter(record["kind"] for record in pair)
        if kinds not in (Counter(request=1, response=1), Counter(request=1, failure=1)):
            raise ValueError(f"Unpaired captured HTTP exchange: {case_id}")
        metadata = [
            {
                key: value
                for key, value in record.items()
                if key not in {"kind", "headers", "content", "status", "exceptionType", "cancelled"}
            }
            for record in pair
        ]
        if metadata[0] != metadata[1]:
            raise ValueError(f"Changed HTTP request/outcome association: {case_id}")
    index = records.get("Scenario evidence index", {}).get("exchanges", [])
    if len(index) != len(pairs) or {item["exchangeId"] for item in index} != pairs.keys():
        raise ValueError(f"Incomplete HTTP evidence index: {case_id}")
    for item in index:
        request = next(record for record in pairs[item["exchangeId"]] if record["kind"] == "request")
        if item != {key: value for key, value in request.items() if key not in {"kind", "headers", "content"}}:
            raise ValueError(f"Changed HTTP evidence index metadata: {case_id}")
        if item["actionId"] is not None and item["actionId"] not in actions:
            raise ValueError(f"HTTP exchange has no owning action: {case_id}")
    for states in actions.values():
        if sorted(states) not in (["action-result", "action-start"], ["action-failure", "action-start"]):
            raise ValueError(f"Unpaired action evidence: {case_id}")
    selected = expectation.get("exchangeIds", [])
    if len(selected) != len(set(selected)) or any(key not in pairs for key in selected):
        raise ValueError(f"Invalid asserted response witnesses: {case_id}")
    outcomes = [record for key in selected for record in pairs[key] if record["kind"] == "response"]
    expected = profile["expected"]
    if sorted(record["status"] for record in outcomes) != sorted(map(int, expected["HTTPStatuses"].split(","))):
        raise ValueError(f"Missing asserted HTTP status witnesses: {case_id}")
    if any(
        record["targetService"] != "payments"
        or record["content"]["contentType"] != expected["ContentType"]
        or record["content"]["body"].get("code", "-") != expected["Code"]
        for record in outcomes
    ):
        raise ValueError(f"Asserted HTTP witnesses differ from expected table: {case_id}")
    for record in outcomes:
        for key, value in expected.items():
            if key.startswith("JSON."):
                actual = record["content"]["body"]
                for part in key.removeprefix("JSON.").split("."):
                    actual = actual[part]
                if actual != json.loads(value):
                    raise ValueError(f"Asserted JSON witness differs from expected table: {case_id} {key}")
    if len(outcomes) > 1 and (
        any(not record["requestAttempt"] for record in outcomes)
        or len({record["requestAttempt"] for record in outcomes}) != len(outcomes)
    ):
        raise ValueError(f"Concurrent responses need distinct attempt identities: {case_id}")


def check_evidence_results(feature_dir: Path, results_dir: Path) -> None:
    profiles = source_evidence(feature_dir)
    for path in results_dir.glob("*-result.json"):
        result = json.loads(path.read_text())
        match = re.match(r"(PAY\d+-\d+)\b", result.get("name", ""))
        if match is None or match[1] not in profiles:
            raise ValueError(f"Unknown evidence scenario: {path.name}")
        check_result_evidence(result, profiles[match[1]], results_dir)
