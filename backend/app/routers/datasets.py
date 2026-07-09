import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_user
from app.deps import get_db
from app.models import Dataset, User
from app.schemas import DatasetCreateRequest, DatasetOut
from app.services import dataset_service

router = APIRouter()


def _to_out(dataset: Dataset) -> DatasetOut:
    return DatasetOut(
        id=str(dataset.id),
        name=dataset.name,
        description=dataset.description,
        visibility=dataset.visibility,
        status=dataset.status,
        owner_user_id=str(dataset.owner_user_id) if dataset.owner_user_id else None,
    )


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[DatasetOut]:
    datasets = dataset_service.list_datasets_for_user(session, user)
    return [_to_out(d) for d in datasets]


@router.post("/datasets", response_model=DatasetOut, status_code=201)
def create_dataset(
    payload: DatasetCreateRequest,
    user: User = Depends(require_user),
    session: Session = Depends(get_db),
) -> DatasetOut:
    dataset = dataset_service.create_dataset(session, user, payload.name, payload.description)
    return _to_out(dataset)


@router.get("/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: uuid.UUID,
    user: User | None = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DatasetOut:
    dataset = dataset_service.get_dataset_scoped(session, dataset_id, user)
    return _to_out(dataset)
