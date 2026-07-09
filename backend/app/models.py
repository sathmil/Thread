import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    clerk_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("visibility in ('private','public')", name="ck_datasets_visibility"),
        CheckConstraint("status in ('draft','indexing','ready','failed')", name="ck_datasets_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String, nullable=False, server_default="private")
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="draft")
    default_cluster_k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    stories: Mapped[list["Story"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = (UniqueConstraint("dataset_id", "external_id", name="uq_stories_dataset_external_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    focus: Mapped[str | None] = mapped_column(String)
    story_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="stories")
    text_units: Mapped[list["TextUnit"]] = relationship(back_populates="story", cascade="all, delete-orphan")


class TextUnit(Base):
    __tablename__ = "text_units"
    __table_args__ = (
        CheckConstraint("unit_type in ('sentence','passage','story')", name="ck_text_units_unit_type"),
        UniqueConstraint("story_id", "unit_type", "unit_index", name="uq_text_units_story_type_index"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    unit_type: Mapped[str] = mapped_column(String, nullable=False)
    unit_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_unit: Mapped[str] = mapped_column(Text, nullable=False)
    preview: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    story: Mapped["Story"] = relationship(back_populates="text_units")
    embeddings: Mapped[list["Embedding"]] = relationship(back_populates="text_unit", cascade="all, delete-orphan")


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "text_unit_id", "embedding_model", "embedding_version", name="uq_embeddings_unit_model_version"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    text_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("text_units.id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String, nullable=False, server_default="v1")
    # Two nullable, dimension-specific columns rather than one fixed-width vector(N):
    # MiniLM is 384-dim and OpenAI text-embedding-3-small is 1536-dim, and only one
    # is populated per row. See docs/database_schema.md (M10) for the rationale.
    vector_384: Mapped[list[float] | None] = mapped_column(Vector(384))
    vector_1536: Mapped[list[float] | None] = mapped_column(Vector(1536))
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    text_unit: Mapped["TextUnit"] = relationship(back_populates="embeddings")


class Cluster(Base):
    __tablename__ = "clusters"
    __table_args__ = (
        CheckConstraint("summary_source in ('rule_based','llm')", name="ck_clusters_summary_source"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    cluster_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cluster_label: Mapped[int] = mapped_column(Integer, nullable=False)
    theme_name: Mapped[str | None] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_source: Mapped[str] = mapped_column(String, nullable=False, server_default="rule_based")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClusterAssignment(Base):
    __tablename__ = "cluster_assignments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    cluster_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    story_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stories.id", ondelete="CASCADE"))
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationQuery(Base):
    __tablename__ = "evaluation_queries"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationQueryExpectedStory(Base):
    __tablename__ = "evaluation_query_expected_stories"

    evaluation_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_queries.id", ondelete="CASCADE"), primary_key=True
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String)
    top_k: Mapped[int | None] = mapped_column(Integer)
    recall_at_k: Mapped[float | None] = mapped_column(Float)
    mrr: Mapped[float | None] = mapped_column(Float)
    precision_at_k: Mapped[float | None] = mapped_column(Float)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_queries.id", ondelete="CASCADE"), nullable=False
    )
    retrieved_story_ids: Mapped[list | None] = mapped_column(JSON)
    hit_at_k: Mapped[bool | None] = mapped_column()
    reciprocal_rank: Mapped[float | None] = mapped_column(Float)
    top_score: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    query_text: Mapped[str | None] = mapped_column(Text)
    unit_type: Mapped[str | None] = mapped_column(String)
    embedding_model: Mapped[str | None] = mapped_column(String)
    top_k: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    embedding_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("job_type in ('index','reindex','cluster','evaluate')", name="ck_jobs_job_type"),
        CheckConstraint("status in ('queued','running','succeeded','failed')", name="ck_jobs_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="queued")
    celery_task_id: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    warning_message: Mapped[str | None] = mapped_column(Text)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    story_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    embedding_ms: Mapped[float | None] = mapped_column(Float)
    avg_embedding_ms_per_story: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
