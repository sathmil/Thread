import re

import pandas as pd

from app.config import FOCUS_SIGNALS


def make_preview(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", str(text)).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0] + "..."


def infer_title(row: pd.Series) -> str:
    text = re.sub(r"\s+", " ", str(row["story_text"])).strip()
    first_sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    title = first_sentence[:72].strip("\"'")
    if len(first_sentence) > 72:
        title = title.rsplit(" ", 1)[0] + "..."
    return title or f"Story {row['id']}"


def infer_focus(text: str) -> str:
    lowered = str(text).lower()
    scores = {
        label: sum(lowered.count(needle) for needle in needles)
        for label, needles in FOCUS_SIGNALS.items()
    }
    best_label, best_score = max(scores.items(), key=lambda item: item[1])
    return best_label if best_score else "Open Narrative"


def split_text_units(text: str, unit: str) -> list[str]:
    if unit == "Stories":
        raw_parts = [text]
    elif unit == "Sentences":
        raw_parts = re.split(r"(?<=[.!?])\s+", str(text))
    elif unit == "Passages":
        raw_parts = re.split(r"\n\s*\n+", str(text))
    else:
        raise ValueError(f"Unsupported search unit: {unit}")

    parts = [re.sub(r"\s+", " ", part).strip() for part in raw_parts]
    min_words = 5 if unit == "Sentences" else 8
    parts = [part for part in parts if len(part.split()) >= min_words]
    return parts or [str(text)]


def split_into_units(df: pd.DataFrame, unit: str) -> pd.DataFrame:
    rows = []
    unit_names = {"Sentences": "sentence", "Passages": "passage", "Stories": "story"}
    if unit not in unit_names:
        raise ValueError(f"Unsupported search unit: {unit}")

    for _, row in df.iterrows():
        parts = split_text_units(row["story_text"], unit)
        for unit_number, text_unit in enumerate(parts, start=1):
            rows.append(
                {
                    "id": row["id"],
                    "unit_id": f"{row['id']}.{unit_number}",
                    "unit_type": unit_names[unit],
                    "story_text": row["story_text"],
                    "text_unit": text_unit,
                    "preview": make_preview(text_unit, limit=260),
                }
            )

    return pd.DataFrame(rows)
