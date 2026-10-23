import pytest

import app.store as store_module
from app.store import InMemoryStore


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    """No test may touch the real Supabase project: every test starts with a fresh in-memory store."""
    monkeypatch.setattr(store_module, "_store", InMemoryStore())
