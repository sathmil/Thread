from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Story
from app.schemas import StoryOut
from app.services.dataset_service import get_default_dataset
from app.text import make_preview

router = APIRouter()


@router.get("/stories", response_model=list[StoryOut])
def list_stories(session: Session = Depends(get_db)) -> list[StoryOut]:
    dataset = get_default_dataset(session)
    stories = (
        session.execute(select(Story).where(Story.dataset_id == dataset.id).order_by(Story.external_id))
        .scalars()
        .all()
    )
    return [
        StoryOut(
            external_id=story.external_id,
            title=story.title,
            focus=story.focus,
            word_count=story.word_count,
            preview=make_preview(story.story_text),
        )
        for story in stories
    ]
