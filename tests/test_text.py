import pandas as pd
import pytest

from src.text import infer_focus, make_preview, split_into_units, split_text_units


def test_split_text_units_supports_sentence_passage_and_story_modes():
    text = (
        "First sentence has enough words. Second sentence also has enough words.\n\n"
        "New passage has enough words to survive the passage filter."
    )

    assert len(split_text_units(text, "Sentences")) == 3
    assert len(split_text_units(text, "Passages")) == 2
    assert len(split_text_units(text, "Stories")) == 1


def test_split_text_units_rejects_unknown_unit():
    with pytest.raises(ValueError):
        split_text_units("Some text.", "Paragraphs")


def test_split_into_units_preserves_story_ids():
    df = pd.DataFrame(
        {
            "id": ["001"],
            "story_text": ["This sentence has enough words. This second sentence also has enough words."],
        }
    )

    units = split_into_units(df, "Sentences")

    assert units["id"].tolist() == ["001", "001"]
    assert units["unit_type"].unique().tolist() == ["sentence"]


def test_preview_truncates_without_breaking_words():
    preview = make_preview("one two three four five", limit=13)

    assert preview == "one two..."


def test_infer_focus_detects_voice_language():
    focus = infer_focus("I learned to speak, use my voice, and be heard.")

    assert focus == "Voice & Self-Advocacy"
