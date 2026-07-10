import statistics
import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.config import FINGERPRINT_DIMENSIONS, LOCAL_MODEL_NAME
from app.models import Cluster, ClusterAssignment, Dataset, Embedding, InsightFinding, Story, TextUnit
from app.services import fingerprint_service
from app.services.cluster_service import _latest_cluster_run_id, _run_embedding_model
from app.services.embedding_columns import vector_column_for_model_id

# Deliberately explicit, documented thresholds rather than whatever produces
# the most findings — a correlation only surfaces if it clears a real
# effect-size/sample-size bar (roadmap M8.5: "thresholded by effect size and
# sample size ... never invented by an LLM").
MIN_CORRELATION_SAMPLE_SIZE = 4
MIN_CORRELATION_EFFECT_SIZE = 0.5
THEME_BRIDGE_MIN_SCORE = 0.5


@dataclass
class RawFinding:
    finding_type: str
    finding_text: str
    dimension_a: str | None = None
    dimension_b: str | None = None
    effect_size: float | None = None
    sample_size: int | None = None
    subject_story_id: uuid.UUID | None = None


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return 0.0
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom = (sum((x - mean_x) ** 2 for x in xs) ** 0.5) * (sum((y - mean_y) ** 2 for y in ys) ** 0.5)
    return cov / denom if denom else 0.0


def compute_correlations(fingerprints: list[dict[str, float]]) -> list[RawFinding]:
    n = len(fingerprints)
    if n < MIN_CORRELATION_SAMPLE_SIZE:
        return []

    findings = []
    dims = FINGERPRINT_DIMENSIONS
    for i, dim_a in enumerate(dims):
        for dim_b in dims[i + 1 :]:
            xs = [fp[dim_a] for fp in fingerprints]
            ys = [fp[dim_b] for fp in fingerprints]
            r = _pearson(xs, ys)
            if abs(r) < MIN_CORRELATION_EFFECT_SIZE:
                continue
            direction = "also" if r > 0 else "less likely to"
            findings.append(
                RawFinding(
                    finding_type="correlation",
                    dimension_a=dim_a,
                    dimension_b=dim_b,
                    effect_size=round(r, 3),
                    sample_size=n,
                    finding_text=(
                        f"Stories that score high on {dim_a} are {direction} score high on {dim_b} "
                        f"(r={r:.2f} across {n} stories)."
                    ),
                )
            )
    findings.sort(key=lambda f: abs(f.effect_size or 0), reverse=True)
    return findings


def most_representative_per_theme(
    stories: list[Story], vectors: np.ndarray, labels: list[int], theme_names: dict[int, str]
) -> list[RawFinding]:
    findings = []
    for label in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == label]
        if not idx:
            continue
        member_vectors = vectors[idx]
        centroid = member_vectors.mean(axis=0)
        dists = np.linalg.norm(member_vectors - centroid, axis=1)
        best = idx[int(np.argmin(dists))]
        story = stories[best]
        theme = theme_names.get(label, "this theme")
        findings.append(
            RawFinding(
                finding_type="most_representative",
                subject_story_id=story.id,
                effect_size=round(float(dists.min()), 4),
                sample_size=len(idx),
                finding_text=(
                    f'"{story.title or story.external_id}" is the story that best represents the theme '
                    f'"{theme}" — it sits closest to the center of that group.'
                ),
            )
        )
    return findings


def most_unique(stories: list[Story], vectors: np.ndarray, labels: list[int]) -> RawFinding | None:
    if len(stories) < 2:
        return None
    centroids = {}
    for label in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == label]
        centroids[label] = vectors[idx].mean(axis=0)

    best_idx, best_dist = None, -1.0
    for i, vector in enumerate(vectors):
        nearest_centroid_dist = min(float(np.linalg.norm(vector - c)) for c in centroids.values())
        if nearest_centroid_dist > best_dist:
            best_dist, best_idx = nearest_centroid_dist, i

    story = stories[best_idx]
    return RawFinding(
        finding_type="most_unique",
        subject_story_id=story.id,
        effect_size=round(best_dist, 4),
        sample_size=len(stories),
        finding_text=(
            f'"{story.title or story.external_id}" is the most unique story in this dataset — '
            "no theme's center is close to it."
        ),
    )


def most_complex(stories: list[Story], fingerprints: list[dict[str, float]]) -> RawFinding | None:
    if not stories:
        return None
    variances = [statistics.pvariance(fp.values()) for fp in fingerprints]
    best = int(np.argmax(variances))
    story = stories[best]
    return RawFinding(
        finding_type="most_complex",
        subject_story_id=story.id,
        effect_size=round(variances[best], 4),
        sample_size=len(FINGERPRINT_DIMENSIONS),
        finding_text=(
            f'"{story.title or story.external_id}" is the most emotionally complex story — its fingerprint '
            "spans the widest range across all dimensions rather than leaning on just one or two."
        ),
    )


def theme_bridge(
    stories: list[Story], fingerprints: list[dict[str, float]], labels: list[int], theme_names: dict[int, str]
) -> RawFinding | None:
    """A story that scores highly on its own theme's defining dimension
    (the dimension with the highest average fingerprint score among that
    theme's members) *and* on a different theme's defining dimension —
    i.e. it could plausibly belong to either.
    """
    defining_dim: dict[int, str] = {}
    for label in sorted(set(labels)):
        idx = [i for i, l in enumerate(labels) if l == label]
        averages = {dim: statistics.mean(fingerprints[i][dim] for i in idx) for dim in FINGERPRINT_DIMENSIONS}
        defining_dim[label] = max(averages, key=averages.get)

    best_idx, best_score, best_other_label = None, -1.0, None
    for i, label in enumerate(labels):
        own_dim = defining_dim[label]
        own_score = fingerprints[i][own_dim]
        if own_score < THEME_BRIDGE_MIN_SCORE:
            continue
        for other_label, other_dim in defining_dim.items():
            if other_label == label or other_dim == own_dim:
                continue
            other_score = fingerprints[i][other_dim]
            if other_score < THEME_BRIDGE_MIN_SCORE:
                continue
            combined = own_score + other_score
            if combined > best_score:
                best_score, best_idx, best_other_label = combined, i, other_label

    if best_idx is None:
        return None

    story = stories[best_idx]
    own_theme = theme_names.get(labels[best_idx], "its theme")
    other_theme = theme_names.get(best_other_label, "another theme")
    return RawFinding(
        finding_type="theme_bridge",
        subject_story_id=story.id,
        dimension_a=defining_dim[labels[best_idx]],
        dimension_b=defining_dim[best_other_label],
        effect_size=round(best_score / 2, 3),
        sample_size=len(stories),
        finding_text=(
            f'"{story.title or story.external_id}" bridges two themes — it scores highly on both '
            f'"{own_theme}"\'s and "{other_theme}"\'s defining dimensions.'
        ),
    )


def theme_migration(session: Session, dataset: Dataset, embedding_model: str) -> list[RawFinding]:
    """Stories whose theme changed between the two most recent cluster runs
    under the same embedding model (e.g. after a re-index). Empty until a
    dataset has been indexed at least twice under that model.
    """
    rows = session.execute(
        select(Cluster.cluster_run_id, Cluster.created_at)
        .where(Cluster.dataset_id == dataset.id, Cluster.embedding_model == embedding_model)
        .order_by(Cluster.created_at.desc())
    ).all()
    distinct_run_ids = list(dict.fromkeys(row.cluster_run_id for row in rows))
    if len(distinct_run_ids) < 2:
        return []

    latest_run, previous_run = distinct_run_ids[0], distinct_run_ids[1]

    def _theme_by_story(run_id: uuid.UUID) -> dict[uuid.UUID, str | None]:
        theme_rows = session.execute(
            select(Story.id, Cluster.theme_name)
            .select_from(ClusterAssignment)
            .join(Cluster, Cluster.id == ClusterAssignment.cluster_id)
            .join(Story, Story.id == ClusterAssignment.story_id)
            .where(Cluster.cluster_run_id == run_id)
        ).all()
        return {row.id: row.theme_name for row in theme_rows}

    latest_themes = _theme_by_story(latest_run)
    previous_themes = _theme_by_story(previous_run)

    findings = []
    for story_id, new_theme in latest_themes.items():
        old_theme = previous_themes.get(story_id)
        if old_theme is None or old_theme == new_theme:
            continue
        story = session.get(Story, story_id)
        findings.append(
            RawFinding(
                finding_type="theme_migration",
                subject_story_id=story_id,
                finding_text=(
                    f'"{story.title or story.external_id}" moved from the "{old_theme}" theme to '
                    f'"{new_theme}" after re-indexing.'
                ),
                sample_size=2,
            )
        )
    return findings


def _phrase(raw: RawFinding) -> str:
    """The LLM (when available) only rephrases an already-computed, grounded
    finding for readability — it never asserts the statistic itself. Falls
    back to the raw templated text on any failure or missing key.
    """
    if not llm.is_available():
        return raw.finding_text
    prompt = (
        "Rewrite the following data-grounded finding as one crisp, plain-language sentence. "
        "Do not add any new facts, numbers, or names beyond what's given — only rephrase.\n\n"
        f"Finding: {raw.finding_text}"
    )
    try:
        return llm.generate_text(prompt, max_tokens=80, temperature=0.3)
    except Exception:
        return raw.finding_text


def generate_findings(session: Session, dataset: Dataset, embedding_model: str | None = None) -> list[InsightFinding]:
    """Computes and persists every finding type for the dataset's latest
    cluster run under the given (already-resolved, stored) embedding model
    id, defaulting to whichever model produced the most recent cluster run.
    Cached at the (dataset, embedding_model) level by the caller — this
    function always recomputes.
    """
    run_id = _latest_cluster_run_id(session, dataset.id, embedding_model)
    if run_id is None:
        return []
    resolved_model = embedding_model or _run_embedding_model(session, run_id) or LOCAL_MODEL_NAME

    cluster_rows = session.execute(select(Cluster).where(Cluster.cluster_run_id == run_id)).scalars().all()
    theme_names = {c.cluster_label: (c.theme_name or f"Theme {c.cluster_label}") for c in cluster_rows}

    assignment_rows = session.execute(
        select(Story, Cluster.cluster_label)
        .select_from(ClusterAssignment)
        .join(Cluster, Cluster.id == ClusterAssignment.cluster_id)
        .join(Story, Story.id == ClusterAssignment.story_id)
        .where(Cluster.cluster_run_id == run_id)
        .order_by(Story.external_id)
    ).all()
    if not assignment_rows:
        return []

    stories = [row[0] for row in assignment_rows]
    labels = [row[1] for row in assignment_rows]

    column = vector_column_for_model_id(resolved_model)
    vector_rows = session.execute(
        select(Story.id, column)
        .select_from(Story)
        .join(TextUnit, TextUnit.story_id == Story.id)
        .join(Embedding, Embedding.text_unit_id == TextUnit.id)
        .where(
            Story.dataset_id == dataset.id,
            TextUnit.unit_type == "story",
            Embedding.embedding_model == resolved_model,
        )
    ).all()
    vector_by_story = {row[0]: row[1] for row in vector_rows}
    vectors = np.array([vector_by_story[s.id] for s in stories])

    fingerprints = [fingerprint_service.compute_fingerprint(session, s).dimensions for s in stories]

    raw_findings: list[RawFinding] = []
    raw_findings += compute_correlations(fingerprints)
    raw_findings += most_representative_per_theme(stories, vectors, labels, theme_names)
    if (unique_finding := most_unique(stories, vectors, labels)) is not None:
        raw_findings.append(unique_finding)
    if (complex_finding := most_complex(stories, fingerprints)) is not None:
        raw_findings.append(complex_finding)
    if (bridge_finding := theme_bridge(stories, fingerprints, labels, theme_names)) is not None:
        raw_findings.append(bridge_finding)
    raw_findings += theme_migration(session, dataset, resolved_model)

    persisted = []
    for raw in raw_findings:
        finding = InsightFinding(
            dataset_id=dataset.id,
            finding_type=raw.finding_type,
            subject_story_id=raw.subject_story_id,
            dimension_a=raw.dimension_a,
            dimension_b=raw.dimension_b,
            finding_text=_phrase(raw),
            effect_size=raw.effect_size,
            sample_size=raw.sample_size,
            embedding_model=resolved_model,
        )
        session.add(finding)
        persisted.append(finding)
    session.commit()
    for finding in persisted:
        session.refresh(finding)
    return persisted
