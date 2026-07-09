"""Manual scale-test: creates a demo user + private dataset, uploads N
synthetic stories (see generate_synthetic_dataset.py), triggers indexing
through the real (non-eager) Celery pipeline, and polls job status until
it completes. Requires a live Celery worker running against the same
Redis/Postgres:

    celery -A app.celery_app worker --loglevel=info

Usage: python -m scripts.demo_large_upload [story_count]
"""
import csv
import io
import sys
import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import get_current_user
from app.db import SessionLocal
from app.main import app
from app.models import User
from scripts.generate_synthetic_dataset import generate_synthetic_stories


def _get_or_create_demo_user() -> User:
    session = SessionLocal()
    try:
        user = session.execute(
            select(User).where(User.clerk_user_id == "demo-scale-test-user")
        ).scalar_one_or_none()
        if user is None:
            user = User(clerk_user_id="demo-scale-test-user")
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "story_text"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def main(story_count: int) -> None:
    user = _get_or_create_demo_user()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    dataset = client.post("/datasets", json={"name": f"Scale demo ({story_count} stories)"}).json()
    print(f"Created dataset {dataset['id']}")

    rows = generate_synthetic_stories(story_count)
    upload = client.post(
        f"/datasets/{dataset['id']}/upload",
        files={"file": ("stories.csv", _csv_bytes(rows), "text/csv")},
    ).json()
    print(f"Uploaded {upload['stories_created']} stories")

    job = client.post(f"/datasets/{dataset['id']}/index", json={}).json()
    print(f"Job {job['id']} started, status={job['status']}")

    while job["status"] in ("queued", "running"):
        time.sleep(1)
        job = client.get(f"/jobs/{job['id']}").json()
        print(f"  status={job['status']} progress={job['progress_pct']}%")

    print(f"Final status: {job['status']}")
    if job["status"] == "succeeded":
        print(
            f"  story_count={job['story_count']} embedding_ms={job['embedding_ms']:.0f} "
            f"avg_per_story={job['avg_embedding_ms_per_story']:.1f}ms duration_ms={job['duration_ms']:.0f}"
        )
    else:
        print(f"  error: {job['error_message']}")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    main(count)
