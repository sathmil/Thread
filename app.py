import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.clustering import project_embeddings, summarize_cluster
from src.config import EMBEDDING_BACKENDS, LOCAL_MODEL_NAME, OPENAI_EMBEDDING_MODEL, SEARCH_UNITS
from src.evaluation import evaluate_queries, load_gold
from src.pipeline import build_story_index, build_unit_index
from src.search import search


st.set_page_config(
    page_title="WHO WE ARE Story Explorer",
    page_icon="",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_story_index(cluster_count: int, provider: str):
    return build_story_index(cluster_count, provider)


@st.cache_data(show_spinner=False)
def cached_unit_index(df: pd.DataFrame, unit: str, provider: str):
    return build_unit_index(df, unit, provider)


def render_unit(row: pd.Series, score: float) -> None:
    with st.expander(
        f"Story {row['id']} · {row['unit_type'].title()} {row['unit_id']} · {score:.2f} similarity",
        expanded=score >= 0.42,
    ):
        st.caption(f"Theme {row['cluster']}: {row['theme']}")
        st.write(row["text_unit"])
        st.divider()
        st.caption("Full story")
        st.write(row["story_text"])


def render_story(row: pd.Series, score: float | None = None) -> None:
    label = f"Story {row['id']}"
    if score is not None:
        label += f" · {score:.2f} similarity"
    with st.expander(label, expanded=score is not None and score >= 0.45):
        st.caption(f"{row['title']} · {row['focus']} · Theme {row['cluster']}: {row['theme']}")
        st.write(row["story_text"])


st.title("WHO WE ARE Story Explorer")
st.caption("A semantic retrieval and clustering system for messy personal narratives.")

with st.sidebar:
    st.header("Controls")
    embedding_provider = st.radio(
        "Embedding backend",
        options=EMBEDDING_BACKENDS,
        horizontal=True,
    )
    cluster_count = st.slider("Theme clusters", min_value=2, max_value=6, value=3)
    result_count = st.slider("Search results", min_value=3, max_value=10, value=5)
    search_unit = st.segmented_control(
        "Search unit",
        options=SEARCH_UNITS,
        default="Passages",
    )
    query = st.text_input(
        "Semantic search",
        placeholder="belonging, identity, voice, education...",
    )
    backend_label = LOCAL_MODEL_NAME if embedding_provider == "Local MiniLM" else OPENAI_EMBEDDING_MODEL
    st.caption(f"Embeddings: `{backend_label}`")
    if embedding_provider == "OpenAI API" and not os.getenv("OPENAI_API_KEY"):
        st.warning("OPENAI_API_KEY is not set, so the app will fall back to local embeddings.")
    with st.expander("How the controls work"):
        st.write(
            "Theme clusters changes how many KMeans groups the story embeddings are divided into. "
            "Search results controls how many matches are shown. Search unit switches between sentence, passage, "
            "and full-story retrieval. Embedding backend lets you compare a local pretrained model with an API-backed option."
        )

df, embeddings, cluster_names = cached_story_index(cluster_count, embedding_provider)
unit_df, unit_embeddings = cached_unit_index(df, search_unit, embedding_provider)

tab_search, tab_themes, tab_eval, tab_map, tab_data, tab_demo = st.tabs(
    ["Search", "Themes", "Evaluation", "Map", "Dataset", "Demo"]
)

with tab_search:
    st.subheader("Find Stories By Meaning")
    st.write(
        "Search embeds your query, compares it with sentence, passage, or full-story embeddings, "
        "and ranks the closest matches by cosine similarity."
    )
    if query.strip():
        ranked = search(query.strip(), unit_df, unit_embeddings, result_count, embedding_provider)

        for _, row in ranked.iterrows():
            if search_unit == "Stories":
                story_row = df[df["id"] == row["id"]].iloc[0].copy()
                render_story(story_row, score=float(row["score"]))
            else:
                render_unit(row, score=float(row["score"]))
    else:
        st.info("Type a theme, phrase, or research question to retrieve the closest stories.")
        for _, row in df.head(result_count).iterrows():
            render_story(row)

with tab_themes:
    st.subheader("Theme Clusters")
    for cluster_id in sorted(df["cluster"].unique()):
        cluster_df = df[df["cluster"] == cluster_id]
        st.markdown(f"#### Theme {cluster_id}: {cluster_names[cluster_id]}")
        st.caption(f"{len(cluster_df)} stories")
        st.write(summarize_cluster(cluster_df, cluster_names[cluster_id]))

        for _, row in cluster_df.iterrows():
            st.write(f"**Story {row['id']}**")
            st.caption(f"{row['title']} · {row['focus']} · {row['word_count']} words")
            st.write(row["preview"])

with tab_eval:
    st.subheader("Retrieval Evaluation")
    st.write(
        "Gold queries make the demo repeatable. Each query has expected story IDs and reports "
        "whether the current retrieval settings found one in the top results."
    )
    eval_results, metrics = evaluate_queries(load_gold(), unit_df, unit_embeddings, embedding_provider, top_k=3)
    col1, col2 = st.columns(2)
    col1.metric("Recall@3", f"{metrics['recall@3']:.2f}")
    col2.metric("MRR", f"{metrics['mrr']:.2f}")
    st.dataframe(eval_results, width="stretch", hide_index=True)

with tab_map:
    st.subheader("Embedding Map")
    coords = project_embeddings(embeddings)
    fig, ax = plt.subplots(figsize=(8, 5))

    for cluster_id in sorted(df["cluster"].unique()):
        mask = df["cluster"].to_numpy() == cluster_id
        ax.scatter(coords[mask, 0], coords[mask, 1], label=f"Theme {cluster_id}", s=90, alpha=0.78)

    for idx, row in df.iterrows():
        ax.annotate(row["id"], (coords[idx, 0], coords[idx, 1]), textcoords="offset points", xytext=(6, 4))

    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.set_title("Stories Positioned By Embedding Similarity")
    ax.legend(loc="best")
    ax.grid(alpha=0.18)
    st.pyplot(fig)
    st.caption("Points closer together have more similar sentence-embedding representations.")

with tab_data:
    st.subheader("Structured Output")
    st.write("The raw stories are enriched with inferred metadata, cluster labels, and theme labels.")
    columns = [
        "id",
        "source",
        "title",
        "focus",
        "word_count",
        "sentence_count",
        "passage_count",
        "cluster",
        "theme",
        "preview",
    ]
    st.dataframe(df[columns], width="stretch", hide_index=True)

    csv = df[
        ["id", "source", "title", "focus", "word_count", "sentence_count", "passage_count", "story_text", "cluster", "theme"]
    ].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download clustered stories",
        csv,
        "who_we_are_clustered_stories.csv",
        "text/csv",
    )

with tab_demo:
    st.subheader("Demo Walkthrough")
    st.markdown(
        """
        **One-sentence pitch:** This tool turns a small set of personal narratives into searchable, clustered structure using pretrained embeddings instead of custom training.

        **Suggested demo path:**

        1. Start on `Search` and query `feeling invisible at school`.
        2. Switch `Search unit` from `Passages` to `Sentences` to show finer retrieval.
        3. Open `Themes` and change `Theme clusters` between 3 and 5.
        4. Open `Evaluation` to show Recall@3 and MRR from the gold query set.
        5. Open `Map` to show how story embeddings arrange by similarity.
        6. Open `Dataset` and download the structured CSV.

        **Resume framing:** this is an information retrieval system over unstructured qualitative data, with modular indexing, retrieval, evaluation, and UI layers.
        """
    )
