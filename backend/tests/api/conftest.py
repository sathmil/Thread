"""API tests run against the real seeded dev database (docker compose up -d db
&& python -m scripts.seed), not an isolated test DB — that isolation lands in
M9 alongside CI containers. Until then these assert against the known content
of the 10-story WHO WE ARE seed dataset.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import get_current_user
from app.celery_app import celery_app
from app.db import SessionLocal
from app.main import app
from app.models import User


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _celery_eager_mode():
    """Runs Celery tasks synchronously in-process instead of dispatching to a
    real worker, so job-flow tests are deterministic and don't need Redis +
    a running worker. Toggled at runtime (Celery reads this per task call,
    not just at app start), restored after each test.
    """
    original = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = original


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


@pytest.fixture()
def sign_in_as():
    """Overrides get_current_user (and anything depending on it, like
    require_user) to simulate a signed-in user without a live Clerk
    connection — the standard FastAPI pattern for testing auth.
    """

    def _sign_in(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    return _sign_in
