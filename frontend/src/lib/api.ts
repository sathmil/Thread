const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SearchUnit = "Sentences" | "Passages" | "Stories";

export type StoryOut = {
  external_id: string;
  title: string | null;
  focus: string | null;
  word_count: number | null;
  preview: string;
};

export type SearchResultOut = {
  story_id: string;
  unit_type: string;
  unit_index: number;
  text_unit: string;
  preview: string;
  score: number;
  theme: string | null;
};

export type SearchResponse = {
  query: string;
  unit: string;
  results: SearchResultOut[];
};

export type ClusterStoryOut = {
  external_id: string;
  title: string | null;
  focus: string | null;
  word_count: number | null;
  preview: string;
};

export type ClusterOut = {
  cluster_label: number;
  theme_name: string | null;
  summary: string | null;
  summary_source: string;
  stories: ClusterStoryOut[];
};

export type EvaluationResultOut = {
  query: string;
  expected_story_ids: string[];
  retrieved_story_ids: string[];
  hit_at_k: boolean;
  reciprocal_rank: number;
  top_score: number | null;
};

export type EvaluationRunOut = {
  run_id: string;
  embedding_model: string;
  unit_type: string;
  top_k: number;
  recall_at_k: number;
  mrr: number;
  avg_latency_ms: number | null;
  results: EvaluationResultOut[];
};

export type ProjectionPointOut = {
  external_id: string;
  title: string | null;
  preview: string;
  x: number;
  y: number;
  cluster_label: number | null;
  theme_name: string | null;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function getStories(): Promise<StoryOut[]> {
  return fetchJson<StoryOut[]>("/stories");
}

export function getClusters(): Promise<ClusterOut[]> {
  return fetchJson<ClusterOut[]>("/clusters");
}

export function search(payload: { query: string; unit: SearchUnit; top_k: number }): Promise<SearchResponse> {
  return fetchJson<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getEvaluationRun(params: { unit: SearchUnit; top_k: number }): Promise<EvaluationRunOut> {
  const query = new URLSearchParams({ unit: params.unit, top_k: String(params.top_k) });
  return fetchJson<EvaluationRunOut>(`/evaluation/run?${query.toString()}`);
}

export function getProjection(): Promise<ProjectionPointOut[]> {
  return fetchJson<ProjectionPointOut[]>("/clusters/projection");
}
