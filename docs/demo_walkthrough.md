# Demo Walkthrough

## One-Sentence Pitch

I built a lightweight semantic explorer that turns personal narratives into searchable, clustered structure with pretrained embeddings instead of custom model training.

## Demo Flow

1. Open the app with `streamlit run app.py`.
2. Start in `Search` and query `feeling invisible at school`.
3. Switch `Search unit` from `Passages` to `Sentences` to show more precise retrieval.
4. Query `finding my voice` and open the top match.
5. Move to `Themes` and change `Theme clusters` from 3 to 5.
6. Open `Evaluation` to show canned queries and top matches.
7. Open `Map` to show how stories arrange by semantic similarity.
8. Open `Dataset` and download the enriched clustered CSV.

## CLI Demo

```bash
python -m src.cli search "finding my voice" --unit Passages --top-k 5
python -m src.cli cluster --clusters 4
python -m src.cli evaluate --unit Passages --top-k 3
```

## Screenshot Checklist

Capture these views for a portfolio page:

- Search results for `feeling invisible at school`
- Sentence-level result for `finding my voice`
- Themes tab with 3 clusters
- Evaluation tab
- Embedding map
- Dataset tab showing enriched metadata

## Portfolio Framing

This project shows a different technique from training a custom model. It uses reusable NLP building blocks: sentence embeddings, cosine similarity, KMeans clustering, TF-IDF labels, and PCA visualization. The throughline is still the same: structuring messy human data into themes, evidence, and navigable patterns.
