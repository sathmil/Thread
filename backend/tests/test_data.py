from app.data import load_stories


def test_load_stories_enriches_dataset():
    df = load_stories()

    assert len(df) == 10
    assert {"id", "source", "title", "focus", "word_count", "sentence_count", "passage_count", "preview"}.issubset(df.columns)
    assert df["id"].str.len().eq(3).all()
    assert df["word_count"].min() > 0
