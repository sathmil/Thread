from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db_ok: bool


class DatasetCreateRequest(BaseModel):
    name: str
    description: str | None = None


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str | None
    visibility: str
    status: str
    owner_user_id: str | None


class StoryOut(BaseModel):
    id: str
    external_id: str
    title: str | None
    focus: str | None
    word_count: int | None
    preview: str


class StoryDetailOut(BaseModel):
    external_id: str
    title: str | None
    focus: str | None
    story_text: str
    word_count: int | None
    theme_name: str | None


class FingerprintOut(BaseModel):
    dimensions: dict[str, float]
    source: str
    model: str


class JourneyEntryOut(BaseModel):
    story_id: str
    title: str | None
    preview: str
    score: float
    same_theme: bool
    explanation: str


class JourneyOut(BaseModel):
    nearest: list[JourneyEntryOut]
    contrasting: JourneyEntryOut | None
    reflection_questions: list[str]


class SearchRequest(BaseModel):
    query: str
    unit: str = "Passages"
    top_k: int = 5
    embedding_model: str = "Local MiniLM"
    dataset_id: str | None = None


class SearchResultOut(BaseModel):
    story_id: str
    story_uuid: str
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
    story_uuid: str
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


class UploadResult(BaseModel):
    stories_created: int


class IndexRequest(BaseModel):
    embedding_model: str = "Local MiniLM"


class ReindexRequest(BaseModel):
    embedding_model: str = "OpenAI API"


class JobOut(BaseModel):
    id: str
    dataset_id: str
    job_type: str
    status: str
    progress_pct: int
    story_count: int | None
    duration_ms: float | None
    embedding_ms: float | None
    avg_embedding_ms_per_story: float | None
    error_message: str | None
    warning_message: str | None
