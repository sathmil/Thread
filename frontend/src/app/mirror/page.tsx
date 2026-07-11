"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { mirrorStory } from "@/lib/api";

export default function MirrorPage() {
  const [storyText, setStoryText] = useState("");

  const mirrorMutation = useMutation({ mutationFn: (text: string) => mirrorStory(text) });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (storyText.trim()) mirrorMutation.mutate(storyText.trim());
  }

  const result = mirrorMutation.data;
  const chartData = result ? Object.entries(result.fingerprint).map(([dimension, value]) => ({ dimension, value })) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Mirror my story</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste a short story of your own — nothing is saved — and see which stories in this collection feel
          closest to it, and why.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={storyText}
          onChange={(event) => setStoryText(event.target.value)}
          placeholder="Write a few sentences about something you've been through..."
          rows={6}
          className={cn(
            "w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none transition-colors",
            "placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          )}
        />
        <Button type="submit" disabled={mirrorMutation.isPending || !storyText.trim()}>
          {mirrorMutation.isPending ? "Finding matches..." : "Find my matches"}
        </Button>
      </form>

      {mirrorMutation.error && (
        <p className="text-sm text-destructive">Something went wrong finding matches — try again.</p>
      )}

      {mirrorMutation.isPending && (
        <div className="space-y-3">
          <Skeleton className="h-6 w-56" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="space-y-3">
            <h2 className="animate-in fade-in duration-500 text-lg font-semibold">
              You&apos;re closest to {result.matches.length} {result.matches.length === 1 ? "story" : "stories"}
              {result.matches[0]?.theme ? ` about ${result.matches[0].theme}` : ""}
            </h2>
            {result.matches.map((match, index) => (
              <Card
                key={match.story_id}
                className="animate-in fade-in slide-in-from-bottom-2 fill-mode-both duration-500"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <CardHeader className="flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-base">{match.title ?? `Story ${match.story_id}`}</CardTitle>
                  <Badge>{match.score.toFixed(2)} similarity</Badge>
                </CardHeader>
                <CardContent className="space-y-1">
                  {match.theme && <p className="text-xs text-muted-foreground">Theme: {match.theme}</p>}
                  <p className="text-sm">{match.preview}</p>
                  <p className="text-xs text-muted-foreground">{match.explanation}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              Your story&apos;s signal ({result.fingerprint_source === "llm" ? "AI-scored" : "keyword heuristic"}).
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="dimension" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#1D9E75" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
