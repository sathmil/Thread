import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Dataset, User


def get_default_dataset(session: Session) -> Dataset:
    """The single shared public dataset used by the M2/M3/M4 routes
    (/stories, /search, /clusters, /evaluation/run). Those stay dataset-
    agnostic until M6 gives users real per-dataset content to search.
    """
    dataset = session.query(Dataset).order_by(Dataset.created_at).first()
    if dataset is None:
        raise LookupError("No dataset found — run `python -m scripts.seed` first.")
    return dataset


def create_dataset(session: Session, owner: User, name: str, description: str | None) -> Dataset:
    dataset = Dataset(
        owner_user_id=owner.id,
        name=name,
        description=description,
        visibility="private",
        status="draft",
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def list_datasets_for_user(session: Session, user: User | None) -> list[Dataset]:
    """Public datasets, plus the caller's own private datasets if signed in."""
    conditions = [Dataset.visibility == "public"]
    if user is not None:
        conditions.append(Dataset.owner_user_id == user.id)
    return (
        session.execute(select(Dataset).where(or_(*conditions)).order_by(Dataset.created_at))
        .scalars()
        .all()
    )


def get_dataset_scoped(session: Session, dataset_id: uuid.UUID, user: User | None) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.visibility == "public":
        return dataset
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required to view this dataset.")
    if dataset.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this dataset.")
    return dataset
