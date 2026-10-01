#!/usr/bin/env python3
"""Run one isolated Payments test suite with JUnit and scoped coverage reports."""

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.verify_suite import verify

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "artifacts" / "verification"
SOURCE = ROOT / "src" / "ecommerce_store_payments"


@dataclass(frozen=True)
class Suite:
    tests: tuple[str, ...]
    sources: tuple[str, ...]
    minimum: int | None = None


SUITES = {
    "domain": Suite(("tests/unit/domain",), ("domain",), 70),
    "application": Suite(("tests/unit/application", "tests/integration/application"), ("application",), 70),
    "infrastructure": Suite(
        ("tests/unit/infrastructure", "tests/unit/external_providers", "tests/integration/infrastructure"),
        ("infrastructure",),
        70,
    ),
    "externalproviders": Suite(("tests/unit/external_providers",), ("infrastructure/clients",)),
    "acceptance": Suite(
        (
            "tests/unit/api",
            "tests/unit/test_architecture.py",
            "tests/unit/test_suite_reports.py",
            "tests/integration/api",
            "tests/acceptance",
        ),
        ("api",),
    ),
}


def run(name: str) -> int:
    suite = SUITES[name]
    if name == "infrastructure":
        subprocess.run(["bash", "scripts/prepare_fulfillment_image.sh"], cwd=ROOT, check=True)
    destination = RESULTS / name
    if destination.exists():
        shutil.rmtree(destination)  # stale reports cannot satisfy a failed run
    destination.mkdir(parents=True)
    sources = tuple(SOURCE / path for path in suite.sources)
    command = [
        sys.executable,
        "-m",
        "pytest",
        *(str(ROOT / path) for path in suite.tests),
        f"--junitxml={destination / 'junit.xml'}",
        *(f"--cov={path}" for path in sources),
        f"--cov-report=xml:{destination / 'coverage.xml'}",
        f"--cov-report=html:{destination / 'htmlcov'}",
        "--cov-report=term-missing",
    ]
    environment = {**os.environ, "COVERAGE_FILE": str(destination / ".coverage")}
    outcome = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    try:
        report = verify(name, destination, sources, suite.minimum)
    except (OSError, ValueError) as error:
        print(f"Suite report error: {error}", file=sys.stderr)
        return outcome.returncode or 1
    summary = report.markdown()
    (destination / "summary.md").write_text(summary, encoding="utf-8")
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(summary)
    print(summary)
    return outcome.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=sorted(SUITES))
    args = parser.parse_args()
    sys.exit(run(args.suite))


if __name__ == "__main__":
    main()
