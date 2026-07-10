import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm
from app.config import FINGERPRINT_DIMENSIONS
from app.models import Dataset, Story
from app.services import cluster_service, fingerprint_service, search_service

MAX_TOOL_ROUNDS = 4

UNAVAILABLE_MESSAGE = "Conversational exploration needs an OpenAI key configured — try Search or Themes instead."

SYSTEM_PROMPT = (
    "You help people explore a collection of personal narratives by calling the tools available to you. "
    "Never invent details about a story, theme, or statistic — only report what the tools return. "
    "Answer in two or three warm, plain-language sentences once you have what you need."
)

# Deliberately tight tool surface (roadmap M8.7): every tool is a thin
# wrapper over an existing service (SearchService/ClusterService/
# fingerprint_service) — the agent is a natural-language UI over
# capabilities the rest of the app already has, not a new retrieval path.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_stories",
            "description": (
                "Semantic search over the dataset's stories for a natural-language description of an "
                "experience, feeling, or theme."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for, in plain language."},
                    "unit": {
                        "type": "string",
                        "enum": ["Sentences", "Passages", "Stories"],
                        "description": "Granularity to search at. Defaults to Passages.",
                    },
                    "top_k": {"type": "integer", "description": "How many results to return. Defaults to 5."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_dimension",
            "description": (
                "Find stories that score highly on one narrative-fingerprint dimension: "
                f"{', '.join(FINGERPRINT_DIMENSIONS)}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string", "enum": list(FINGERPRINT_DIMENSIONS)},
                    "min_score": {"type": "number", "description": "Minimum score 0-1. Defaults to 0.6."},
                    "top_k": {"type": "integer", "description": "How many results to return. Defaults to 5."},
                },
                "required": ["dimension"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_theme",
            "description": "Get the summary and sample stories for a theme, by its name or numeric cluster label.",
            "parameters": {
                "type": "object",
                "properties": {"theme": {"type": "string", "description": "Theme name or cluster label."}},
                "required": ["theme"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_stories",
            "description": "Explain how two stories relate, grounded in their narrative fingerprints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_id_a": {"type": "string", "description": "external_id of the first story"},
                    "story_id_b": {"type": "string", "description": "external_id of the second story"},
                },
                "required": ["story_id_a", "story_id_b"],
            },
        },
    },
]


def _tool_search_stories(session: Session, dataset: Dataset, args: dict) -> dict:
    unit = args.get("unit") or "Passages"
    top_k = int(args.get("top_k") or 5)
    try:
        results, _ = search_service.search(session, dataset, args["query"], unit, top_k)
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "results": [
            {"story_id": r.story_id, "preview": r.preview, "score": round(r.score, 3), "theme": r.theme}
            for r in results
        ]
    }


def _tool_filter_by_dimension(session: Session, dataset: Dataset, args: dict) -> dict:
    dimension = args.get("dimension")
    if dimension not in FINGERPRINT_DIMENSIONS:
        return {"error": f"Unknown dimension {dimension!r}. Valid dimensions: {list(FINGERPRINT_DIMENSIONS)}"}
    min_score = float(args.get("min_score") or 0.6)
    top_k = int(args.get("top_k") or 5)

    stories = session.execute(select(Story).where(Story.dataset_id == dataset.id)).scalars().all()
    scored = []
    for story in stories:
        fingerprint = fingerprint_service.compute_fingerprint(session, story)
        score = fingerprint.dimensions.get(dimension, 0.0)
        if score >= min_score:
            scored.append((story, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return {
        "dimension": dimension,
        "matches": [
            {"story_id": story.external_id, "title": story.title, "score": round(score, 3)}
            for story, score in scored[:top_k]
        ],
    }


def _tool_describe_theme(session: Session, dataset: Dataset, args: dict) -> dict:
    theme_query = str(args.get("theme", "")).strip().lower()
    clusters = cluster_service.get_clusters(session, dataset)

    match = None
    for cluster in clusters:
        if theme_query == str(cluster.cluster_label):
            match = cluster
            break
        if cluster.theme_name and theme_query in cluster.theme_name.lower():
            match = cluster
            break
    if match is None:
        return {"error": f"No theme found matching {args.get('theme')!r}."}

    return {
        "theme_name": match.theme_name,
        "summary": match.summary,
        "story_count": len(match.stories),
        "sample_story_ids": [s.external_id for s in match.stories[:5]],
    }


def _tool_compare_stories(session: Session, dataset: Dataset, args: dict) -> dict:
    story_a = session.execute(
        select(Story).where(Story.dataset_id == dataset.id, Story.external_id == args.get("story_id_a"))
    ).scalars().first()
    story_b = session.execute(
        select(Story).where(Story.dataset_id == dataset.id, Story.external_id == args.get("story_id_b"))
    ).scalars().first()
    if story_a is None or story_b is None:
        return {"error": "One or both story ids weren't found in this dataset."}

    fingerprint_a = fingerprint_service.compute_fingerprint(session, story_a)
    fingerprint_b = fingerprint_service.compute_fingerprint(session, story_b)
    explanation = fingerprint_service.explain_similarity(fingerprint_a.dimensions, fingerprint_b.dimensions)
    return {"story_id_a": story_a.external_id, "story_id_b": story_b.external_id, "explanation": explanation}


_TOOL_DISPATCH = {
    "search_stories": _tool_search_stories,
    "filter_by_dimension": _tool_filter_by_dimension,
    "describe_theme": _tool_describe_theme,
    "compare_stories": _tool_compare_stories,
}


def dispatch_tool(session: Session, dataset: Dataset, name: str, args: dict) -> dict:
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool {name!r}"}
    return handler(session, dataset, args)


@dataclass
class QueryResult:
    available: bool
    answer: str
    tool_calls: list[dict] = field(default_factory=list)


def answer_query(session: Session, dataset: Dataset, question: str) -> QueryResult:
    """Runs the tool-calling loop: the LLM picks tools from TOOLS, we
    dispatch them against existing services, and feed results back until
    it has enough to answer in plain language. Falls back to a graceful
    "not configured" message when no OpenAI key is set (roadmap M8.7 was
    built to the "build fully, verify the fallback path" pattern used for
    Clerk/M5 and OpenAI/M7 in environments without live credentials).
    """
    if not llm.is_available():
        return QueryResult(available=False, answer=UNAVAILABLE_MESSAGE, tool_calls=[])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls_made: list[dict] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = llm.chat_completion_raw(messages, tools=TOOLS)
        message = response["choices"][0]["message"]
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return QueryResult(available=True, answer=(message.get("content") or "").strip(), tool_calls=tool_calls_made)

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result = dispatch_tool(session, dataset, name, args)
            tool_calls_made.append({"tool": name, "arguments": args})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                }
            )

    return QueryResult(
        available=True,
        answer="I wasn't able to find a good answer in time — try rephrasing your question.",
        tool_calls=tool_calls_made,
    )
