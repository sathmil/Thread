from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db_ok: bool


class StoryOut(BaseModel):
    external_id: str
    title: str | None
    focus: str | None
    word_count: int | None
    preview: str


class SearchRequest(BaseModel):
    query: str
    unit: str = "Passages"
    top_k: int = 5
    embedding_model: str = "Local MiniLM"


class SearchResultOut(BaseModel):
    story_id: str
    unit_type: str
    unit_index: int
    text_unit: str
    preview: str
    score: float
    theme: str | None


class SearchResponse(BaseModel):
    query: str
    unit: str
    results: list[SearchResultOut]


class ClusterStoryOut(BaseModel):
    external_id: str
    title: str | None
    focus: str | None
    word_count: int | None
    preview: str


class ClusterOut(BaseModel):
    cluster_label: int
    theme_name: str | None
    summary: str | None
    summary_source: str
    stories: list[ClusterStoryOut]


class ProjectionPointOut(BaseModel):
    external_id: str
    title: str | None
    preview: str
    x: float
    y: float
    cluster_label: int | None
    theme_name: str | None


class EvaluationResultOut(BaseModel):
    query: str
    expected_story_ids: list[str]
    retrieved_story_ids: list[str]
    hit_at_k: bool
    reciprocal_rank: float
    top_score: float | None


class EvaluationRunOut(BaseModel):
    run_id: str
    embedding_model: str
    unit_type: str
    top_k: int
    recall_at_k: float
    mrr: float
    avg_latency_ms: float | None
    results: list[EvaluationResultOut]
