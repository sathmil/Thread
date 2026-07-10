"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDatasets, getInsights, type InsightFindingOut } from "@/lib/api";

const FINDING_TYPE_LABELS: Record<string, string> = {
  most_representative: "Most representative",
  most_unique: "Most unique",
  most_complex: "Most emotionally complex",
  theme_bridge: "Bridges two themes",
  theme_migration: "Changed themes",
};

export default function InsightsPage() {
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: () => getDatasets() });
  const datasetId = datasetsQuery.data?.[0]?.id;

  const insightsQuery = useQuery({
    queryKey: ["insights", datasetId],
    queryFn: () => getInsights(datasetId as string),
    enabled: Boolean(datasetId),
  });

  const isLoading = datasetsQuery.isLoading || insightsQuery.isLoading;
  const error = datasetsQuery.error || insightsQuery.error;
  const findings = insightsQuery.data;

  const correlations = findings?.filter((f) => f.finding_type === "correlation") ?? [];
  const superlatives = findings?.filter((f) => f.finding_type !== "correlation") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Insights</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Real, reproducible patterns computed from the current corpus — statistical correlations across narrative
          dimensions, plus standout stories. Nothing here is invented; an AI may only rephrase a finding for
          readability, never assert it.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {error && <p className="text-sm text-destructive">Could not load insights.</p>}

      {findings && findings.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Not enough data yet to surface reproducible findings — index a larger dataset first.
        </p>
      )}

      {correlations.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Patterns across dimensions</h2>
          <div className="space-y-2">
            {correlations.map((finding) => (
              <Card key={`${finding.dimension_a}-${finding.dimension_b}`}>
                <CardContent className="flex items-center justify-between gap-3">
                  <p className="text-sm">{finding.finding_text}</p>
                  {finding.effect_size !== null && (
                    <Badge variant="outline">r = {finding.effect_size.toFixed(2)}</Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {superlatives.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Notable stories</h2>
          <div className="space-y-2">
            {superlatives.map((finding, index) => (
              <SuperlativeCard key={`${finding.finding_type}-${finding.subject_story_uuid}-${index}`} finding={finding} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function SuperlativeCard({ finding }: { finding: InsightFindingOut }) {
  const label = FINDING_TYPE_LABELS[finding.finding_type] ?? finding.finding_type;

  const body = (
    <CardContent className="space-y-1">
      <p className="text-sm">{finding.finding_text}</p>
    </CardContent>
  );

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{finding.subject_story_title ?? `Story ${finding.subject_story_external_id}`}</CardTitle>
        <Badge variant="secondary">{label}</Badge>
      </CardHeader>
      {finding.subject_story_uuid ? (
        <Link href={`/stories/${finding.subject_story_uuid}`} className="block hover:bg-muted/50">
          {body}
        </Link>
      ) : (
        body
      )}
    </Card>
  );
}
