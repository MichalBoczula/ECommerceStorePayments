import subprocess
import sys
from pathlib import Path

import pytest
from scripts.check_architecture import PACKAGE, ROOT, check


def _source(tmp_path: Path, layer: str, relative: str, code: str) -> Path:
    source = tmp_path / "src" / PACKAGE
    for name in ("domain", "application", "infrastructure", "api"):
        (source / name).mkdir(parents=True, exist_ok=True)
    file = source / layer / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(code, encoding="utf-8")
    return source


def test_current_source_respects_architecture() -> None:
    assert check() == []


@pytest.mark.parametrize(
    ("layer", "relative", "code", "message"),
    [
        (
            "domain",
            "bad.py",
            "from ecommerce_store_payments.infrastructure.persistence.mongodb import mongo_database\n",
            "forbidden domain -> infrastructure",
        ),
        ("application", "bad.py", "import ecommerce_store_payments.api.app\n", "forbidden application -> api"),
        (
            "application",
            "bad.py",
            "from ecommerce_store_payments import infrastructure\n",
            "forbidden application -> infrastructure",
        ),
        (
            "infrastructure",
            "bad.py",
            "from ecommerce_store_payments.api import dependencies\n",
            "forbidden infrastructure -> api",
        ),
        (
            "api",
            "routes/bad.py",
            "from ecommerce_store_payments.infrastructure.config import settings\n",
            "forbidden api -> infrastructure",
        ),
        (
            "api",
            "app.py",
            "from ecommerce_store_payments.infrastructure.persistence.mongodb.documents import payment_document\n",
            "MongoDB document outside infrastructure",
        ),
        ("domain", "bad.py", "from pydantic import BaseModel\n", "framework outside adapters"),
        ("application", "bad.py", "from pymongo import MongoClient\n", "MongoDB driver outside persistence"),
        ("infrastructure", "clients/bad.py", "from pymongo import MongoClient\n", "MongoDB driver outside persistence"),
        ("domain", "payments/bad.py", "from ...infrastructure import config\n", "forbidden domain -> infrastructure"),
        ("domain", "bad.py", "__import__('ecommerce_store_payments.api.app')\n", "forbidden domain -> api"),
    ],
)
def test_forbidden_source_import_fails(layer: str, relative: str, code: str, message: str, tmp_path: Path) -> None:
    source = _source(tmp_path, layer, relative, code)
    assert any(message in violation for violation in check(source))


def test_architecture_command_rejects_a_negative_fixture(tmp_path: Path) -> None:
    source = _source(tmp_path, "domain", "bad.py", "from ecommerce_store_payments.api import routes\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_architecture.py"), "--source-root", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "forbidden domain -> api" in result.stderr


def test_explicit_readiness_and_composition_exceptions_are_narrow(tmp_path: Path) -> None:
    source = _source(tmp_path, "api", "app.py", "from ecommerce_store_payments.infrastructure.config import settings\n")
    _source(tmp_path, "api", "routes/health.py", "from pymongo.errors import PyMongoError\n")
    assert check(source) == []
    _source(tmp_path, "api", "routes/health.py", "from pymongo import MongoClient\n")
    assert any("MongoDB driver outside persistence" in violation for violation in check(source))


def test_import_text_in_a_string_is_not_a_dependency(tmp_path: Path) -> None:
    source = _source(tmp_path, "domain", "bad.py", 'note = "from ecommerce_store_payments.api import routes"\n')
    assert check(source) == []
