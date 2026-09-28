"""Validate pytest JUnit and Cobertura reports and enforce line coverage gates."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class SuiteReport:
    name: str
    total: int
    passed: int
    failed: int
    skipped: int
    lines_covered: int
    lines_valid: int
    minimum: int | None

    @property
    def line_percentage(self) -> Decimal:
        return Decimal(self.lines_covered) * 100 / Decimal(self.lines_valid)

    def markdown(self) -> str:
        gate = f"{self.minimum}%" if self.minimum is not None else "report only"
        return (
            "| Suite | Total | Passed | Failed | Skipped | Line coverage | Gate |\n"
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |\n"
            f"| {self.name} | {self.total} | {self.passed} | {self.failed} | {self.skipped} "
            f"| {self.line_percentage:.2f}% | {gate} |\n"
        )


def verify(name: str, directory: Path, expected_sources: tuple[Path, ...], minimum: int | None) -> SuiteReport:
    junit = directory / "junit.xml"
    coverage = directory / "coverage.xml"
    for file in (junit, coverage):
        if not file.is_file() or file.stat().st_size == 0:
            raise ValueError(f"Missing report for {name}: {file}")
    try:
        result = ElementTree.parse(junit).getroot()
        report = ElementTree.parse(coverage).getroot()
    except ElementTree.ParseError as error:
        raise ValueError(f"Invalid XML report for {name}: {error}") from error
    suites = [result] if result.tag == "testsuite" else result.findall("testsuite")
    if not suites:
        raise ValueError(f"Missing JUnit suites for {name}")
    total = sum(int(suite.get("tests", "0")) for suite in suites)
    failed = sum(int(suite.get("failures", "0")) + int(suite.get("errors", "0")) for suite in suites)
    skipped = sum(int(suite.get("skipped", "0")) for suite in suites)
    passed = total - failed - skipped
    if total <= 0 or passed <= 0 or failed != 0:
        raise ValueError(f"Invalid JUnit results for {name}: total={total}, passed={passed}, failed={failed}")

    if report.tag != "coverage":
        raise ValueError(f"Invalid coverage report for {name}")
    actual_sources = {Path(item.text).resolve() for item in report.findall("./sources/source") if item.text}
    expected = {path.resolve() for path in expected_sources}
    if actual_sources != expected:
        raise ValueError(f"Wrong coverage sources for {name}: {actual_sources} != {expected}")
    valid = int(report.get("lines-valid", "0"))
    covered = int(report.get("lines-covered", "0"))
    if valid <= 0 or not 0 <= covered <= valid:
        raise ValueError(f"Invalid coverage counters for {name}: {covered}/{valid}")
    if minimum is not None and covered * 100 < minimum * valid:
        raise ValueError(f"{name} line coverage {Decimal(covered) * 100 / Decimal(valid):.2f}% is below {minimum}%")
    return SuiteReport(name, total, passed, failed, skipped, covered, valid, minimum)
