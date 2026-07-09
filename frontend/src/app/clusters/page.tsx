"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getClusters } from "@/lib/api";

export default function ClustersPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Theme clusters</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Stories grouped by KMeans over their embeddings, labeled with TF-IDF terms and a rule-based summary.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {error && <p className="text-sm text-destructive">Could not load clusters.</p>}
      {data?.length === 0 && (
        <p className="text-sm text-muted-foreground">No themes yet — index a dataset to generate clusters.</p>
      )}

      {data?.map((cluster) => (
        <Card key={cluster.cluster_label}>
          <CardHeader>
            <CardTitle className="text-base">
              Theme {cluster.cluster_label}: {cluster.theme_name}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{cluster.stories.length} stories</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm">{cluster.summary}</p>
            <div className="space-y-2">
              {cluster.stories.map((story) => (
                <div key={story.external_id} className="rounded-md border p-3">
                  <p className="text-sm font-medium">Story {story.external_id}</p>
                  <p className="text-xs text-muted-foreground">
                    {story.title} &middot; {story.focus} &middot; {story.word_count} words
                  </p>
                  <p className="mt-1 text-sm">{story.preview}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
