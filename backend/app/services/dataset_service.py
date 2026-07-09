from sqlalchemy.orm import Session

from app.models import Dataset


def get_default_dataset(session: Session) -> Dataset:
    """M2 operates on a single shared dataset — there's no auth or multi-tenancy
    until M5, and no upload path until M6, so exactly one (the seeded) dataset
    exists. Replaced by proper dataset_id routing once M5/M6 land.
    """
    dataset = session.query(Dataset).order_by(Dataset.created_at).first()
    if dataset is None:
        raise LookupError("No dataset found — run `python -m scripts.seed` first.")
    return dataset
