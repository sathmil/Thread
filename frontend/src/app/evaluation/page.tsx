"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getEvaluationRun,
  getEvaluationRunDetail,
  getEvaluationRuns,
  type EvaluationRunOut,
  type SearchUnit,
} from "@/lib/api";

const UNITS: SearchUnit[] = ["Sentences", "Passages", "Stories"];
const EMBEDDING_MODELS = ["Local MiniLM", "OpenAI API"];

const SCORE_BUCKETS = [
  { label: "0.0-0.2", min: 0, max: 0.2 },
  { label: "0.2-0.4", min: 0.2, max: 0.4 },
  { label: "0.4-0.6", min: 0.4, max: 0.6 },
  { label: "0.6-0.8", min: 0.6, max: 0.8 },
  { label: "0.8-1.0", min: 0.8, max: 1.01 },
];

function scoreDistribution(run: EvaluationRunOut) {
  const scores = run.results.map((r) => r.top_score).filter((s): s is number => s != null);
  return SCORE_BUCKETS.map((bucket) => ({
    bucket: bucket.label,
    count: scores.filter((s) => s >= bucket.min && s < bucket.max).length,
  }));
}

export default function EvaluationPage() {
  const [unit, setUnit] = useState<SearchUnit>("Passages");
  const [topK, setTopK] = useState(3);
  const [embeddingModel, setEmbeddingModel] = useState("Local MiniLM");
  const [viewingRunId, setViewingRunId] = useState<string | null>(null);

  const liveRun = useQuery({
    queryKey: ["evaluation", unit, topK, embeddingModel],
    queryFn: () => getEvaluationRun({ unit, top_k: topK, embedding_model: embeddingModel }),
  });

  const history = useQuery({ queryKey: ["evaluation-runs"], queryFn: getEvaluationRuns });

  const historicalDetail = useQuery({
    queryKey: ["evaluation-run-detail", viewingRunId],
    queryFn: () => getEvaluationRunDetail(viewingRunId as string),
    enabled: viewingRunId !== null,
  });

  const displayedRun = viewingRunId ? historicalDetail.data : liveRun.data;
  const isLoading = viewingRunId ? historicalDetail.isLoading : liveRun.isLoading;
  const error = viewingRunId ? historicalDetail.error : liveRun.error;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Retrieval evaluation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Gold queries make the demo repeatable. Each query has expected story IDs and reports whether the current
          retrieval settings found one in the top results. Every run here is saved, so models and settings can be
          compared over time.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Select value={unit} onValueChange={(value) => { setViewingRunId(null); setUnit(value as SearchUnit); }}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {UNITS.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={embeddingModel}
          onValueChange={(value) => { if (value) { setViewingRunId(null); setEmbeddingModel(value); } }}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {EMBEDDING_MODELS.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          type="number"
          min={1}
          max={10}
          value={topK}
          onChange={(event) => { setViewingRunId(null); setTopK(Number(event.target.value) || 1); }}
          className="w-20"
        />
      </div>

      {viewingRunId && (
        <p className="text-xs text-muted-foreground">
          Viewing a saved historical run.{" "}
          <button type="button" className="underline" onClick={() => setViewingRunId(null)}>
            Back to live settings
          </button>
        </p>
      )}

      {isLoading && <Skeleton className="h-32 w-full" />}
      {error && <p className="text-sm text-destructive">Could not run evaluation.</p>}

      {displayedRun && (
        <>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label={`Recall@${displayedRun.top_k}`} value={displayedRun.recall_at_k.toFixed(2)} />
            <MetricCard label="MRR" value={displayedRun.mrr.toFixed(2)} />
            <MetricCard
              label={`Precision@${displayedRun.top_k}`}
              value={displayedRun.precision_at_k != null ? displayedRun.precision_at_k.toFixed(2) : "—"}
            />
            <MetricCard
              label="Avg latency"
              value={displayedRun.avg_latency_ms != null ? `${displayedRun.avg_latency_ms.toFixed(0)}ms` : "—"}
            />
          </div>

          {displayedRun.results.length === 0 ? (
            <p className="text-sm text-muted-foreground">No gold queries for this dataset yet.</p>
          ) : (
            <>
              <div className="space-y-2">
                <p className="text-sm font-medium">Score distribution</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={scoreDistribution(displayedRun)} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#378ADD" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-64">Query</TableHead>
                    <TableHead className="w-28">Expected</TableHead>
                    <TableHead className="w-28">Retrieved</TableHead>
                    <TableHead className="w-16">Hit</TableHead>
                    <TableHead className="w-32">Reciprocal rank</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedRun.results.map((result) => (
                    <TableRow key={result.query}>
                      <TableCell className="truncate">{result.query}</TableCell>
                      <TableCell className="truncate">{result.expected_story_ids.join(", ")}</TableCell>
                      <TableCell className="truncate">{result.retrieved_story_ids.join(", ")}</TableCell>
                      <TableCell>
                        <Badge variant={result.hit_at_k ? "default" : "secondary"}>
                          {result.hit_at_k ? "hit" : "miss"}
                        </Badge>
                      </TableCell>
                      <TableCell>{result.reciprocal_rank.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}
        </>
      )}

      <div className="space-y-2">
        <h2 className="text-lg font-semibold">History</h2>
        <p className="text-sm text-muted-foreground">
          Every past run, across every model — compare Local MiniLM against OpenAI, or a run before and after a
          re-index.
        </p>

        {history.isLoading && <Skeleton className="h-24 w-full" />}
        {history.error && <p className="text-sm text-destructive">Could not load run history.</p>}
        {history.data && history.data.length === 0 && (
          <p className="text-sm text-muted-foreground">No evaluation runs recorded yet — run one above.</p>
        )}

        {history.data && history.data.length > 0 && (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>K</TableHead>
                <TableHead>Recall</TableHead>
                <TableHead>MRR</TableHead>
                <TableHead>Precision</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.data.map((run) => (
                <TableRow key={run.run_id} className="cursor-pointer" onClick={() => setViewingRunId(run.run_id)}>
                  <TableCell className="truncate">{new Date(run.created_at).toLocaleString()}</TableCell>
                  <TableCell>{run.embedding_model}</TableCell>
                  <TableCell>{run.unit_type}</TableCell>
                  <TableCell>{run.top_k}</TableCell>
                  <TableCell>{run.recall_at_k.toFixed(2)}</TableCell>
                  <TableCell>{run.mrr.toFixed(2)}</TableCell>
                  <TableCell>{run.precision_at_k != null ? run.precision_at_k.toFixed(2) : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
