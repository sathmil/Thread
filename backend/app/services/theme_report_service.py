import statistics

import pandas as pd

from app import llm
from app.clustering import summarize_cluster
from app.config import FINGERPRINT_DIMENSIONS


def _fingerprint_averages(fingerprint_dicts: list[dict[str, float]]) -> dict[str, float]:
    if not fingerprint_dicts:
        return {dimension: 0.0 for dimension in FINGERPRINT_DIMENSIONS}
    return {
        dimension: round(statistics.mean(fp[dimension] for fp in fingerprint_dicts), 3)
        for dimension in FINGERPRINT_DIMENSIONS
    }


def generate_report(
    cluster_df: pd.DataFrame, theme_name: str, fingerprint_dicts: list[dict[str, float]]
) -> tuple[str, str]:
    """Returns (summary, summary_source). Tries an LLM-written paragraph
    grounded in a sample of the theme's stories and their fingerprint
    averages; falls back to the existing rule-based summarize_cluster() on
    any failure or missing API key. Both get computed here (the rule-based
    one is never skipped) so the improvement stays auditable rather than
    just assumed, per the roadmap's M7.5 design.
    """
    rule_based_summary = summarize_cluster(cluster_df, theme_name)

    if not llm.is_available():
        return rule_based_summary, "rule_based"

    averages = _fingerprint_averages(fingerprint_dicts)
    top_dimensions = sorted(averages.items(), key=lambda item: item[1], reverse=True)[:3]
    dims_text = ", ".join(f"{dimension} ({value:.1f})" for dimension, value in top_dimensions)
    samples = "\n---\n".join(cluster_df["preview"].tolist()[:5])

    prompt = (
        f"These stories were grouped together under the theme '{theme_name}'. "
        f"Their average scores are highest on: {dims_text}.\n\n"
        f"Sample story previews:\n{samples}\n\n"
        "Write one short paragraph (2-3 sentences) describing what ties these stories together. "
        "Ground your description in the sample text and the listed scores — don't invent details."
    )
    try:
        report = llm.generate_text(prompt, system="You are a thoughtful qualitative researcher.", max_tokens=200)
        return report, "llm"
    except Exception:
        return rule_based_summary, "rule_based"
