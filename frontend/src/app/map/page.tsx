"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Skeleton } from "@/components/ui/skeleton";
import { getProjection, type ProjectionPointOut } from "@/lib/api";

const CLUSTER_COLORS = ["#7F77DD", "#1D9E75", "#D85A30", "#D4537E", "#378ADD", "#EF9F27"];

function colorForCluster(label: number | null) {
  if (label == null) return "#888780";
  return CLUSTER_COLORS[label % CLUSTER_COLORS.length];
}

export default function MapPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["projection"], queryFn: getProjection });

  const byCluster = new Map<number, ProjectionPointOut[]>();
  for (const point of data ?? []) {
    const label = point.cluster_label ?? -1;
    const bucket = byCluster.get(label) ?? [];
    bucket.push(point);
    byCluster.set(label, bucket);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Embedding map</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Stories positioned by a 2D PCA projection of their embeddings. Points closer together have more similar
          sentence-embedding representations; color shows theme membership.
        </p>
      </div>

      {isLoading && <Skeleton className="h-96 w-full" />}
      {error && <p className="text-sm text-destructive">Could not load the embedding map.</p>}
      {data && data.length === 0 && <p className="text-sm text-muted-foreground">No stories to plot yet.</p>}

      {data && data.length > 0 && (
        <ResponsiveContainer width="100%" height={480}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis type="number" dataKey="x" name="PCA 1" tick={{ fontSize: 12 }} />
            <YAxis type="number" dataKey="y" name="PCA 2" tick={{ fontSize: 12 }} />
            <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            {Array.from(byCluster.entries()).map(([label, points]) => (
              <Scatter
                key={label}
                name={points[0]?.theme_name ?? "Unclustered"}
                data={points}
                fill={colorForCluster(label)}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function PointTooltip({ active, payload }: { active?: boolean; payload?: { payload: ProjectionPointOut }[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;

  return (
    <div className="max-w-64 rounded-lg border bg-popover p-3 text-sm shadow-md">
      <p className="font-medium">
        Story {point.external_id} &middot; {point.theme_name}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{point.preview}</p>
    </div>
  );
}
