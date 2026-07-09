"""Auth-scoping tests. Rather than requiring a live Clerk connection, these
override the get_current_user dependency directly (FastAPI's documented
pattern for testing auth) — the same approach works before and after real
Clerk keys are configured.
"""
import pytest
from sqlalchemy import select

from app.auth import get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import User


def _get_or_create_test_user(clerk_user_id: str) -> User:
    session = SessionLocal()
    try:
        user = session.execute(select(User).where(User.clerk_user_id == clerk_user_id)).scalar_one_or_none()
        if user is None:
            user = User(clerk_user_id=clerk_user_id)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


@pytest.fixture()
def user_a() -> User:
    return _get_or_create_test_user("test-user-a")


@pytest.fixture()
def user_b() -> User:
    return _get_or_create_test_user("test-user-b")


@pytest.fixture(autouse=True)
def _clear_auth_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _sign_in_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def test_anonymous_sees_only_public_datasets(client):
    response = client.get("/datasets")

    assert response.status_code == 200
    datasets = response.json()
    assert all(d["visibility"] == "public" for d in datasets)
    assert "WHO WE ARE (seed)" in {d["name"] for d in datasets}


def test_create_dataset_requires_auth(client):
    response = client.post("/datasets", json={"name": "Should be rejected"})

    assert response.status_code == 401


def test_user_can_create_and_read_own_dataset(client, user_a):
    _sign_in_as(user_a)

    create_response = client.post("/datasets", json={"name": "User A's dataset"})
    assert create_response.status_code == 201
    dataset = create_response.json()
    assert dataset["visibility"] == "private"
    assert dataset["owner_user_id"] == str(user_a.id)

    read_response = client.get(f"/datasets/{dataset['id']}")
    assert read_response.status_code == 200


def test_other_signed_in_user_gets_403_on_private_dataset(client, user_a, user_b):
    _sign_in_as(user_a)
    dataset_id = client.post("/datasets", json={"name": "User A's private dataset"}).json()["id"]

    _sign_in_as(user_b)
    response = client.get(f"/datasets/{dataset_id}")

    assert response.status_code == 403


def test_anonymous_gets_401_on_private_dataset(client, user_a):
    _sign_in_as(user_a)
    dataset_id = client.post("/datasets", json={"name": "Another private dataset"}).json()["id"]

    app.dependency_overrides.pop(get_current_user, None)
    response = client.get(f"/datasets/{dataset_id}")

    assert response.status_code == 401


def test_dataset_list_is_scoped_per_user(client, user_a, user_b):
    _sign_in_as(user_a)
    client.post("/datasets", json={"name": "A-only dataset"})

    _sign_in_as(user_b)
    names = {d["name"] for d in client.get("/datasets").json()}

    assert "A-only dataset" not in names
    assert "WHO WE ARE (seed)" in names
