from __future__ import annotations
import pytest

@pytest.fixture(autouse=True)
def _force_offline(monkeypatch):
    """Make every prax-brain test offline-safe by default.

    Researcher scanners short-circuit when PRAX_OFFLINE is set; tests that
    explicitly need to exercise the network can monkeypatch this fixture
    away or set PRAX_OFFLINE=0 in the test body.
    """
    monkeypatch.setenv("PRAX_OFFLINE", "1")
    yield


@pytest.fixture
def mock_prax_dir(tmp_path):
    d = tmp_path / "prax"
    d.mkdir(parents=True)
    for sub in ["proposals/pending", "proposals/approved", "proposals/rejected", "projects", "logs"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d
