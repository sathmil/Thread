"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  type ScatterPointItem,
} from "recharts";

import { Onboarding } from "@/components/onboarding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getJourney, getProjection, type ProjectionPointOut } from "@/lib/api";

const CLUSTER_COLORS = ["#7F77DD", "#1D9E75", "#D85A30", "#D4537E", "#378ADD", "#EF9F27"];
const ZOOM_FACTOR = 0.75; // multiplies the current domain range when zooming in
const PAN_FRACTION = 0.2; // fraction of the current domain range moved per pan step

type Domain = [number, number];

function colorForCluster(label: number | null) {
  if (label == null) return "#888780";
  return CLUSTER_COLORS[label % CLUSTER_COLORS.length];
}

function extentOf(points: ProjectionPointOut[], key: "x" | "y"): Domain {
  const values = points.map((p) => p[key]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.1 || 1;
  return [min - pad, max + pad];
}

export default function HomePage() {
  const router = useRouter();
  const { data, isLoading, error } = useQuery({ queryKey: ["projection"], queryFn: getProjection });

  const [filter, setFilter] = useState("");
  const [highlighted, setHighlighted] = useState<Set<string> | null>(null);
  const [domain, setDomain] = useState<{ x: Domain; y: Domain } | null>(null);

  const points = useMemo(() => data ?? [], [data]);
  const fullDomain = useMemo(
    () => (points.length > 0 ? { x: extentOf(points, "x"), y: extentOf(points, "y") } : null),
    [points]
  );
  const activeDomain = domain ?? fullDomain;

  const byCluster = new Map<number, ProjectionPointOut[]>();
  for (const point of points) {
    const label = point.cluster_label ?? -1;
    const bucket = byCluster.get(label) ?? [];
    bucket.push(point);
    byCluster.set(label, bucket);
  }

  const normalizedFilter = filter.trim().toLowerCase();
  function matchesFilter(point: ProjectionPointOut) {
    if (!normalizedFilter) return true;
    return (
      Boolean(point.title?.toLowerCase().includes(normalizedFilter)) ||
      point.preview.toLowerCase().includes(normalizedFilter) ||
      Boolean(point.theme_name?.toLowerCase().includes(normalizedFilter))
    );
  }

  function opacityFor(point: ProjectionPointOut) {
    if (highlighted) return highlighted.has(point.external_id) ? 1 : 0.15;
    if (normalizedFilter) return matchesFilter(point) ? 1 : 0.1;
    return 0.85;
  }

  async function handlePointDoubleClick(point: ProjectionPointOut) {
    try {
      const journey = await getJourney(point.story_uuid);
      const ids = new Set(journey.nearest.map((entry) => entry.story_id));
      ids.add(point.external_id);
      setHighlighted(ids);
    } catch {
      // Highlighting nearest neighbors is a bonus interaction, not the
      // critical path — silently ignore if the journey lookup fails.
    }
  }

  function handlePointClick(point: ProjectionPointOut) {
    router.push(`/stories/${point.story_uuid}`);
  }

  function zoom(factor: number) {
    if (!activeDomain) return;
    const { x, y } = activeDomain;
    const cx = (x[0] + x[1]) / 2;
    const cy = (y[0] + y[1]) / 2;
    const halfX = ((x[1] - x[0]) / 2) * factor;
    const halfY = ((y[1] - y[0]) / 2) * factor;
    setDomain({ x: [cx - halfX, cx + halfX], y: [cy - halfY, cy + halfY] });
  }

  function pan(dx: number, dy: number) {
    if (!activeDomain) return;
    const { x, y } = activeDomain;
    const rangeX = x[1] - x[0];
    const rangeY = y[1] - y[0];
    setDomain({
      x: [x[0] + dx * rangeX, x[1] + dx * rangeX],
      y: [y[0] + dy * rangeY, y[1] + dy * rangeY],
    });
  }

  return (
    <div className="space-y-6">
      <Onboarding />
      <div>
        <h1 className="text-2xl font-semibold">Find yourself in someone else&apos;s experience</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every point below is a story, positioned so similar experiences sit close together. Hover to preview,
          click to open, double-click to see what&apos;s nearest to it, or search to find your own.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="belonging, identity, voice, education..."
          className="min-w-64 flex-1"
        />
        {highlighted && (
          <Button type="button" variant="outline" size="sm" onClick={() => setHighlighted(null)}>
            Clear highlight
          </Button>
        )}
        <Button type="button" variant="outline" size="sm" onClick={() => zoom(ZOOM_FACTOR)}>
          Zoom in
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => zoom(1 / ZOOM_FACTOR)}>
          Zoom out
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => setDomain(null)} disabled={!domain}>
          Reset view
        </Button>
      </div>

      {isLoading && <Skeleton className="h-96 w-full" />}
      {error && <p className="text-sm text-destructive">Could not load the story map.</p>}
      {data && data.length === 0 && <p className="text-sm text-muted-foreground">No stories to plot yet.</p>}

      {data && data.length > 0 && activeDomain && (
        <div className="space-y-2">
          <div className="flex justify-end gap-1">
            <Button type="button" variant="ghost" size="icon" onClick={() => pan(-PAN_FRACTION, 0)} aria-label="Pan left">
              ←
            </Button>
            <Button type="button" variant="ghost" size="icon" onClick={() => pan(PAN_FRACTION, 0)} aria-label="Pan right">
              →
            </Button>
            <Button type="button" variant="ghost" size="icon" onClick={() => pan(0, -PAN_FRACTION)} aria-label="Pan up">
              ↑
            </Button>
            <Button type="button" variant="ghost" size="icon" onClick={() => pan(0, PAN_FRACTION)} aria-label="Pan down">
              ↓
            </Button>
          </div>
          <ResponsiveContainer width="100%" height={480}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                type="number"
                dataKey="x"
                name="PCA 1"
                domain={activeDomain.x}
                allowDataOverflow
                tick={{ fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="PCA 2"
                domain={activeDomain.y}
                allowDataOverflow
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3" }} />
              {Array.from(byCluster.entries()).map(([label, clusterPoints]) => (
                <Scatter
                  key={label}
                  name={clusterPoints[0]?.theme_name ?? "Unclustered"}
                  data={clusterPoints}
                  fill={colorForCluster(label)}
                  cursor="pointer"
                  onClick={(item: ScatterPointItem) => handlePointClick(item.payload as ProjectionPointOut)}
                  onDoubleClick={(item: ScatterPointItem) =>
                    handlePointDoubleClick(item.payload as ProjectionPointOut)
                  }
                  shape={(shapeProps: ScatterPointItem) => (
                    <circle
                      cx={shapeProps.cx}
                      cy={shapeProps.cy}
                      r={5}
                      fill={colorForCluster(label)}
                      opacity={opacityFor(shapeProps.payload as ProjectionPointOut)}
                      className="transition-opacity duration-300 ease-out"
                    />
                  )}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
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
