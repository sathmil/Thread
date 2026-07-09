from pathlib import Path

import pandas as pd

from src.config import DATA_PATH
from src.text import infer_focus, infer_title, make_preview, split_text_units


def load_stories(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["id"] = df["id"].astype(str).str.zfill(3)
    df["story_text"] = df["story_text"].fillna("")
    return enrich_stories(df)


def enrich_stories(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["source"] = "WHO WE ARE story dataset"
    enriched["title"] = enriched.apply(infer_title, axis=1)
    enriched["focus"] = enriched["story_text"].apply(infer_focus)
    enriched["word_count"] = enriched["story_text"].apply(lambda text: len(str(text).split()))
    enriched["sentence_count"] = enriched["story_text"].apply(lambda text: len(split_text_units(text, "Sentences")))
    enriched["passage_count"] = enriched["story_text"].apply(lambda text: len(split_text_units(text, "Passages")))
    enriched["preview"] = enriched["story_text"].apply(make_preview)
    return enriched
