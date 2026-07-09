"""Auth-scoping tests. Rather than requiring a live Clerk connection, these
override the get_current_user dependency directly (FastAPI's documented
pattern for testing auth) — the same approach works before and after real
Clerk keys are configured. Shared fixtures (client, user_a, user_b,
sign_in_as) live in conftest.py.
"""
from app.auth import get_current_user
from app.main import app


def test_anonymous_sees_only_public_datasets(client):
    response = client.get("/datasets")

    assert response.status_code == 200
    datasets = response.json()
    assert all(d["visibility"] == "public" for d in datasets)
    assert "WHO WE ARE (seed)" in {d["name"] for d in datasets}


def test_create_dataset_requires_auth(client):
    response = client.post("/datasets", json={"name": "Should be rejected"})

    assert response.status_code == 401


def test_user_can_create_and_read_own_dataset(client, user_a, sign_in_as):
    sign_in_as(user_a)

    create_response = client.post("/datasets", json={"name": "User A's dataset"})
    assert create_response.status_code == 201
    dataset = create_response.json()
    assert dataset["visibility"] == "private"
    assert dataset["owner_user_id"] == str(user_a.id)

    read_response = client.get(f"/datasets/{dataset['id']}")
    assert read_response.status_code == 200


def test_other_signed_in_user_gets_403_on_private_dataset(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    dataset_id = client.post("/datasets", json={"name": "User A's private dataset"}).json()["id"]

    sign_in_as(user_b)
    response = client.get(f"/datasets/{dataset_id}")

    assert response.status_code == 403


def test_anonymous_gets_401_on_private_dataset(client, user_a, sign_in_as):
    sign_in_as(user_a)
    dataset_id = client.post("/datasets", json={"name": "Another private dataset"}).json()["id"]

    app.dependency_overrides.pop(get_current_user, None)
    response = client.get(f"/datasets/{dataset_id}")

    assert response.status_code == 401


def test_dataset_list_is_scoped_per_user(client, user_a, user_b, sign_in_as):
    sign_in_as(user_a)
    client.post("/datasets", json={"name": "A-only dataset"})

    sign_in_as(user_b)
    names = {d["name"] for d in client.get("/datasets").json()}

    assert "A-only dataset" not in names
    assert "WHO WE ARE (seed)" in names
