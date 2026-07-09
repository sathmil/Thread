"""API tests run against the real seeded dev database (docker compose up -d db
&& python -m scripts.seed), not an isolated test DB — that isolation lands in
M9 alongside CI containers. Until then these assert against the known content
of the 10-story WHO WE ARE seed dataset.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)
