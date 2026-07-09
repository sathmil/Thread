"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

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
import { getEvaluationRun, type SearchUnit } from "@/lib/api";

const UNITS: SearchUnit[] = ["Sentences", "Passages", "Stories"];

export default function EvaluationPage() {
  const [unit, setUnit] = useState<SearchUnit>("Passages");
  const [topK, setTopK] = useState(3);

  const { data, isLoading, error } = useQuery({
    queryKey: ["evaluation", unit, topK],
    queryFn: () => getEvaluationRun({ unit, top_k: topK }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Retrieval evaluation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Gold queries make the demo repeatable. Each query has expected story IDs and reports whether the current
          retrieval settings found one in the top results.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Select value={unit} onValueChange={(value) => setUnit(value as SearchUnit)}>
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
        <Input
          type="number"
          min={1}
          max={10}
          value={topK}
          onChange={(event) => setTopK(Number(event.target.value) || 1)}
          className="w-20"
        />
      </div>

      {isLoading && <Skeleton className="h-32 w-full" />}
      {error && <p className="text-sm text-destructive">Could not run evaluation.</p>}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label={`Recall@${data.top_k}`} value={data.recall_at_k.toFixed(2)} />
            <MetricCard label="MRR" value={data.mrr.toFixed(2)} />
            <MetricCard
              label="Avg latency"
              value={data.avg_latency_ms != null ? `${data.avg_latency_ms.toFixed(0)}ms` : "—"}
            />
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
              {data.results.map((result) => (
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
