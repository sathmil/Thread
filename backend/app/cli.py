import argparse

import pandas as pd

from app.clustering import summarize_cluster
from app.config import SEARCH_UNITS
from app.evaluation import evaluate_queries, load_gold
from app.pipeline import build_story_index, build_unit_index
from app.search import search


def cmd_search(args: argparse.Namespace) -> None:
    df, _, _ = build_story_index(args.clusters, args.backend)
    unit_df, unit_embeddings = build_unit_index(df, args.unit, args.backend)
    results = search(args.query, unit_df, unit_embeddings, args.top_k, args.backend)
    columns = ["id", "unit_id", "unit_type", "theme", "score", "preview"]
    print(results[columns].to_string(index=False))


def cmd_cluster(args: argparse.Namespace) -> None:
    df, _, cluster_names = build_story_index(args.clusters, args.backend)
    rows = []
    for cluster_id in sorted(df["cluster"].unique()):
        cluster_df = df[df["cluster"] == cluster_id]
        rows.append(
            {
                "cluster": cluster_id,
                "theme": cluster_names[cluster_id],
                "stories": len(cluster_df),
                "summary": summarize_cluster(cluster_df, cluster_names[cluster_id]),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))


def cmd_evaluate(args: argparse.Namespace) -> None:
    df, _, _ = build_story_index(args.clusters, args.backend)
    unit_df, unit_embeddings = build_unit_index(df, args.unit, args.backend)
    results, metrics = evaluate_queries(load_gold(), unit_df, unit_embeddings, args.backend, args.top_k)
    print(results[["query", "expected_story_ids", "top_story", "score", "hit_at_k", "reciprocal_rank"]].to_string(index=False))
    print()
    for name, value in metrics.items():
        print(f"{name}: {value:.3f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semantic retrieval over the WHO WE ARE story dataset.")
    parser.add_argument("--backend", choices=["Local MiniLM", "OpenAI API"], default="Local MiniLM")
    parser.add_argument("--clusters", type=int, default=3)

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search stories by semantic similarity.")
    search_parser.add_argument("query")
    search_parser.add_argument("--unit", choices=SEARCH_UNITS, default="Passages")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--clusters", type=int, default=3)
    search_parser.set_defaults(func=cmd_search)

    cluster_parser = subparsers.add_parser("cluster", help="Print cluster summaries.")
    cluster_parser.add_argument("--clusters", type=int, default=3)
    cluster_parser.set_defaults(func=cmd_cluster)

    eval_parser = subparsers.add_parser("evaluate", help="Run gold-query retrieval evaluation.")
    eval_parser.add_argument("--unit", choices=SEARCH_UNITS, default="Passages")
    eval_parser.add_argument("--top-k", type=int, default=3)
    eval_parser.add_argument("--clusters", type=int, default=3)
    eval_parser.set_defaults(func=cmd_evaluate)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
