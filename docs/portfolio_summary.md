# Portfolio Summary

## Title

WHO WE ARE Story Explorer

## Short Description

An embedding-based search and clustering tool for personal narratives. It helps researchers move from raw stories to themes, representative passages, and structured metadata without training a custom model.

## Why It Matters

Human stories are hard to analyze because the signal is often thematic rather than keyword-based. This prototype uses semantic embeddings to retrieve passages by meaning, cluster stories into themes, and generate an enriched dataset that can support qualitative analysis.

## Technical Highlights

- Local pretrained sentence embeddings with `all-MiniLM-L6-v2`
- Optional API-backed embeddings via `OPENAI_API_KEY`
- Sentence, passage, and full-story retrieval modes
- KMeans theme clustering
- TF-IDF cluster labels and rule-based summaries
- PCA embedding map
- Gold-query evaluation with Recall@K and MRR
- CLI commands for search, clustering, and evaluation
- Modular pipeline split across data, text, embeddings, search, clustering, and evaluation modules
- Downloadable enriched CSV

## Interview Framing

This is intentionally not a model-training project. The point is to show range: when the task is small, qualitative, and messy, a fast embedding pipeline can produce useful structure with less complexity, less data, and faster iteration.
