"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createDataset,
  getDatasets,
  getJob,
  indexDataset,
  reindexDataset,
  uploadStories,
  type DatasetOut,
} from "@/lib/api";

type GetToken = () => Promise<string | null>;

export default function WorkspacePage() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!clerkEnabled) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="text-sm text-muted-foreground">
          Sign-in isn&apos;t configured in this environment yet. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and
          CLERK_SECRET_KEY to enable private datasets.
        </p>
      </div>
    );
  }

  return <WorkspaceContent />;
}

function WorkspaceContent() {
  const { isSignedIn, getToken } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const datasetsQuery = useQuery({
    queryKey: ["datasets", isSignedIn],
    queryFn: async () => getDatasets(isSignedIn ? await getToken() : undefined),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Sign in required.");
      return createDataset({ name, description: description || undefined }, token);
    },
    onSuccess: () => {
      setName("");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Public datasets are visible to everyone; private datasets are visible only to you. Upload a CSV with a
          story_text column, then index it to make it searchable and clustered.
        </p>
      </div>

      {isSignedIn ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
          className="flex flex-wrap gap-3"
        >
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Dataset name"
            className="min-w-64 flex-1"
            required
          />
          <Input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description (optional)"
            className="min-w-64 flex-1"
          />
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create dataset"}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-muted-foreground">Sign in to create your own private datasets.</p>
      )}

      {createMutation.error && (
        <p className="text-sm text-destructive">{(createMutation.error as Error).message}</p>
      )}

      {datasetsQuery.isLoading && <Skeleton className="h-24 w-full" />}
      {datasetsQuery.error && <p className="text-sm text-destructive">Could not load datasets.</p>}

      <div className="space-y-2">
        {datasetsQuery.data?.map((dataset) => (
          <DatasetCard key={dataset.id} dataset={dataset} getToken={getToken} />
        ))}
      </div>
    </div>
  );
}

function DatasetCard({ dataset, getToken }: { dataset: DatasetOut; getToken: GetToken }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // GET /datasets only ever returns public datasets plus the caller's own
  // private ones (see dataset_service.list_datasets_for_user), so any
  // private dataset showing up here is one this user owns and can manage.
  const isMine = dataset.visibility === "private";

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = await getToken();
      if (!token) throw new Error("Sign in required.");
      return uploadStories(dataset.id, file, token);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });

  const indexMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Sign in required.");
      return indexDataset(dataset.id, token);
    },
    onSuccess: (job) => setActiveJobId(job.id),
  });

  const reindexMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Sign in required.");
      return reindexDataset(dataset.id, token, "OpenAI API");
    },
    onSuccess: (job) => setActiveJobId(job.id),
  });

  const jobQuery = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: async () => getJob(activeJobId as string, await getToken()),
    enabled: activeJobId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 1500 : false;
    },
  });

  const job = jobQuery.data;
  const isIndexing = job ? job.status === "queued" || job.status === "running" : false;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{dataset.name}</CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant={dataset.visibility === "public" ? "default" : "secondary"}>{dataset.visibility}</Badge>
          <Badge variant="outline">{job?.status ?? dataset.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {dataset.description && <p className="text-sm text-muted-foreground">{dataset.description}</p>}

        {isMine && (
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="text-sm text-muted-foreground file:mr-2 file:rounded-md file:border file:bg-transparent file:px-2 file:py-1 file:text-sm"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadMutation.mutate(file);
              }}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => indexMutation.mutate()}
              disabled={indexMutation.isPending || isIndexing}
            >
              {isIndexing ? `Indexing... ${job?.progress_pct ?? 0}%` : "Index"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => reindexMutation.mutate()}
              disabled={reindexMutation.isPending || isIndexing}
              title="Recompute embeddings under OpenAI's model, without deleting the existing ones"
            >
              Re-index (OpenAI)
            </Button>
          </div>
        )}

        {uploadMutation.data && (
          <p className="text-xs text-muted-foreground">Uploaded {uploadMutation.data.stories_created} stories.</p>
        )}
        {uploadMutation.error && (
          <p className="text-xs text-destructive">{(uploadMutation.error as Error).message}</p>
        )}
        {indexMutation.error && (
          <p className="text-xs text-destructive">{(indexMutation.error as Error).message}</p>
        )}
        {reindexMutation.error && (
          <p className="text-xs text-destructive">{(reindexMutation.error as Error).message}</p>
        )}

        {job && job.status === "succeeded" && (
          <p className="text-xs text-muted-foreground">
            Indexed {job.story_count} stories in {job.duration_ms?.toFixed(0)}ms
            {job.avg_embedding_ms_per_story
              ? ` (${job.avg_embedding_ms_per_story.toFixed(1)}ms/story embedding)`
              : ""}
            .
          </p>
        )}
        {job && job.warning_message && (
          <p className="text-xs text-amber-600">{job.warning_message}</p>
        )}
        {job && job.status === "failed" && (
          <p className="text-xs text-destructive">Indexing failed: {job.error_message}</p>
        )}
      </CardContent>
    </Card>
  );
}
