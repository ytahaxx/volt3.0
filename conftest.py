import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    return create_app(TestConfig, {
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "PROGRAMME_PDF": str(tmp_path / "absent.pdf"),
    })


@pytest.fixture()
def client(app):
    return app.test_client()
