const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SearchUnit = "Sentences" | "Passages" | "Stories";

export type StoryOut = {
  id: string;
  external_id: string;
  title: string | null;
  focus: string | null;
  word_count: number | null;
  preview: string;
};

export type StoryDetailOut = {
  external_id: string;
  title: string | null;
  focus: string | null;
  story_text: string;
  word_count: number | null;
  theme_name: string | null;
};

export type FingerprintOut = {
  dimensions: Record<string, number>;
  source: string;
  model: string;
};

export type JourneyEntryOut = {
  story_id: string;
  title: string | null;
  preview: string;
  score: number;
  same_theme: boolean;
  explanation: string;
};

export type JourneyOut = {
  nearest: JourneyEntryOut[];
  contrasting: JourneyEntryOut | null;
  reflection_questions: string[];
};

export type SearchResultOut = {
  story_id: string;
  story_uuid: string;
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
  story_uuid: string;
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
  story_uuid: string;
  title: string | null;
  preview: string;
  x: number;
  y: number;
  cluster_label: number | null;
  theme_name: string | null;
};

export type InsightFindingOut = {
  finding_type: string;
  finding_text: string;
  dimension_a: string | null;
  dimension_b: string | null;
  effect_size: number | null;
  sample_size: number | null;
  subject_story_external_id: string | null;
  subject_story_uuid: string | null;
  subject_story_title: string | null;
};

export type DatasetOut = {
  id: string;
  name: string;
  description: string | null;
  visibility: string;
  status: string;
  owner_user_id: string | null;
};

export type UploadResult = {
  stories_created: number;
};

export type JobOut = {
  id: string;
  dataset_id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress_pct: number;
  story_count: number | null;
  duration_ms: number | null;
  embedding_ms: number | null;
  avg_embedding_ms_per_story: number | null;
  error_message: string | null;
  warning_message: string | null;
};

async function fetchJson<T>(path: string, init?: RequestInit & { token?: string | null }): Promise<T> {
  const { token, headers, ...rest } = init ?? {};
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...rest,
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

export function getStoryDetail(storyId: string, token?: string | null): Promise<StoryDetailOut> {
  return fetchJson<StoryDetailOut>(`/stories/${storyId}`, { token });
}

export function getFingerprint(storyId: string, token?: string | null): Promise<FingerprintOut> {
  return fetchJson<FingerprintOut>(`/stories/${storyId}/fingerprint`, { token });
}

export function getJourney(storyId: string, token?: string | null): Promise<JourneyOut> {
  return fetchJson<JourneyOut>(`/stories/${storyId}/journey`, { token });
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

export function getInsights(datasetId: string, token?: string | null): Promise<InsightFindingOut[]> {
  return fetchJson<InsightFindingOut[]>(`/datasets/${datasetId}/insights`, { token });
}

export function getDatasets(token?: string | null): Promise<DatasetOut[]> {
  return fetchJson<DatasetOut[]>("/datasets", { token });
}

export function createDataset(
  payload: { name: string; description?: string },
  token: string
): Promise<DatasetOut> {
  return fetchJson<DatasetOut>("/datasets", {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export async function uploadStories(
  datasetId: string,
  file: File,
  token: string
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${API_URL}/datasets/${datasetId}/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Upload failed (${response.status}): ${detail}`);
  }
  return response.json() as Promise<UploadResult>;
}

export function indexDataset(
  datasetId: string,
  token: string,
  embeddingModel: string = "Local MiniLM"
): Promise<JobOut> {
  return fetchJson<JobOut>(`/datasets/${datasetId}/index`, {
    method: "POST",
    body: JSON.stringify({ embedding_model: embeddingModel }),
    token,
  });
}

export function getJob(jobId: string, token?: string | null): Promise<JobOut> {
  return fetchJson<JobOut>(`/jobs/${jobId}`, { token });
}

export function reindexDataset(
  datasetId: string,
  token: string,
  embeddingModel: string = "OpenAI API"
): Promise<JobOut> {
  return fetchJson<JobOut>(`/datasets/${datasetId}/reindex`, {
    method: "POST",
    body: JSON.stringify({ embedding_model: embeddingModel }),
    token,
  });
}
