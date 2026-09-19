import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.store import reset_store  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture()
def store(tmp_path):
    """A store with a writable data directory and the real sample datasets."""
    return reset_store(data_dir=tmp_path, samples_dir=SAMPLES)


@pytest.fixture()
def bracket(store):
    return store.get_simulation("brk-114")


@pytest.fixture()
def aero(store):
    return store.get_simulation("aer-207")


@pytest.fixture()
def plate(store):
    return store.get_simulation("thm-088")


@pytest.fixture()
def suspension(store):
    return store.get_simulation("mbd-052")


@pytest.fixture()
def client(store):
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
