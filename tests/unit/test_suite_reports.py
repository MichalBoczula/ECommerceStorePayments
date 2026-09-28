from pathlib import Path

import pytest
from scripts import run_suite
from scripts.run_suite import SUITES
from scripts.verify_suite import verify


def _reports(tmp_path: Path, *, total: int = 2, failures: int = 0, covered: int = 7, valid: int = 10) -> Path:
    directory = tmp_path / "domain"
    directory.mkdir(exist_ok=True)
    (directory / "junit.xml").write_text(
        f'<testsuites><testsuite tests="{total}" failures="{failures}" errors="0" skipped="0"/></testsuites>',
        encoding="utf-8",
    )
    (directory / "coverage.xml").write_text(
        f'<coverage lines-covered="{covered}" lines-valid="{valid}">'
        f"<sources><source>{tmp_path / 'domain'}</source></sources></coverage>",
        encoding="utf-8",
    )
    return directory


def test_suite_paths_cover_every_test_with_only_external_boundary_overlap() -> None:
    root = Path(__file__).resolve().parents[2]
    assigned: list[Path] = []
    for suite in SUITES.values():
        for target in suite.tests:
            path = root / target
            assigned.extend(path.rglob("test_*.py") if path.is_dir() else [path])
    assert set(assigned) == set((root / "tests").rglob("test_*.py"))
    repeated = {path for path in assigned if assigned.count(path) > 1}
    assert repeated == set((root / "tests/unit/external_providers").rglob("test_*.py"))


def test_valid_report_passes_at_exact_line_threshold(tmp_path: Path) -> None:
    directory = _reports(tmp_path)
    report = verify("domain", directory, (tmp_path / "domain",), 70)
    assert report.passed == 2
    assert "70.00%" in report.markdown()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing_junit", "Missing report"),
        ("missing_coverage", "Missing report"),
        ("invalid_xml", "Invalid XML report"),
        ("failed_test", "Invalid JUnit results"),
        ("no_tests", "Invalid JUnit results"),
        ("low_coverage", "below 70%"),
        ("wrong_scope", "Wrong coverage sources"),
    ],
)
def test_missing_or_failed_reports_reject_suite(change: str, message: str, tmp_path: Path) -> None:
    directory = _reports(
        tmp_path,
        failures=1 if change == "failed_test" else 0,
        total=0 if change == "no_tests" else 2,
        covered=6 if change == "low_coverage" else 7,
    )
    if change == "missing_junit":
        (directory / "junit.xml").unlink()
    if change == "missing_coverage":
        (directory / "coverage.xml").unlink()
    if change == "invalid_xml":
        (directory / "coverage.xml").write_text("<coverage", encoding="utf-8")
    sources = (tmp_path / "other",) if change == "wrong_scope" else (tmp_path / "domain",)
    with pytest.raises(ValueError, match=message):
        verify("domain", directory, sources, 70)


def test_runner_preserves_test_failure_even_with_valid_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(run_suite, "RESULTS", tmp_path)
    monkeypatch.setattr(run_suite, "SOURCE", tmp_path)

    def failed_test_command(*_args: object, **_kwargs: object) -> object:
        _reports(tmp_path)

        class Result:
            returncode = 7

        return Result()

    monkeypatch.setattr(run_suite.subprocess, "run", failed_test_command)
    assert run_suite.run("domain") == 7


def test_runner_does_not_accept_stale_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reports(tmp_path)
    monkeypatch.setattr(run_suite, "RESULTS", tmp_path)
    monkeypatch.setattr(run_suite, "SOURCE", tmp_path)

    class Result:
        returncode = 0

    def no_reports(*_args: object, **_kwargs: object) -> Result:
        return Result()

    monkeypatch.setattr(run_suite.subprocess, "run", no_reports)
    assert run_suite.run("domain") == 1
