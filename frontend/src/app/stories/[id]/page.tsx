"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getFingerprint,
  getJourney,
  getStoryDetail,
  type FingerprintOut,
  type JourneyEntryOut,
  type JourneyOut,
  type StoryDetailOut,
} from "@/lib/api";

const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export default function StoryDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  return CLERK_ENABLED ? (
    <AuthedStoryDetail id={id} />
  ) : (
    <StoryDetail id={id} getToken={async () => null} />
  );
}

function AuthedStoryDetail({ id }: { id: string }) {
  const { getToken } = useAuth();
  return <StoryDetail id={id} getToken={getToken} />;
}

function StoryDetail({ id, getToken }: { id: string; getToken: () => Promise<string | null> }) {
  const [showFingerprint, setShowFingerprint] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["story", id],
    queryFn: async () => getStoryDetail(id, await getToken()),
  });

  const journeyQuery = useQuery({
    queryKey: ["journey", id],
    queryFn: async () => getJourney(id, await getToken()),
  });

  const fingerprintQuery = useQuery({
    queryKey: ["fingerprint", id],
    queryFn: async () => getFingerprint(id, await getToken()),
    enabled: showFingerprint,
  });

  if (detailQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (detailQuery.error || !detailQuery.data) {
    return <p className="text-sm text-destructive">Could not load this story.</p>;
  }

  const story = detailQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/dataset" className="text-sm text-muted-foreground hover:text-foreground">
          &larr; Back to dataset
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold">{story.title ?? `Story ${story.external_id}`}</h1>
          {story.theme_name && <Badge variant="secondary">{story.theme_name}</Badge>}
        </div>
        {story.focus && <p className="mt-1 text-sm text-muted-foreground">{story.focus}</p>}
      </div>

      <StoryText story={story} />

      <JourneySection query={journeyQuery} />

      <div>
        <Button variant="outline" size="sm" onClick={() => setShowFingerprint((v) => !v)}>
          {showFingerprint ? "Hide the raw signal" : "Curious? See the raw signal"}
        </Button>
        {showFingerprint && <FingerprintChart query={fingerprintQuery} />}
      </div>
    </div>
  );
}

function StoryText({ story }: { story: StoryDetailOut }) {
  return (
    <Card>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{story.story_text}</p>
      </CardContent>
    </Card>
  );
}

function JourneySection({ query }: { query: UseQueryResult<JourneyOut, Error> }) {
  if (query.isLoading) return <Skeleton className="h-48 w-full" />;
  if (query.error || !query.data) {
    return <p className="text-sm text-destructive">Could not load this story&apos;s journey.</p>;
  }

  const journey = query.data;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Journey</h2>
        <p className="text-sm text-muted-foreground">Stories closest to this one, and why.</p>
      </div>

      {journey.nearest.length === 0 && (
        <p className="text-sm text-muted-foreground">No other stories in this dataset yet.</p>
      )}

      <div className="space-y-3">
        {journey.nearest.map((entry) => (
          <JourneyCard key={entry.story_id} entry={entry} />
        ))}
      </div>

      {journey.contrasting && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">A contrasting story</h3>
          <JourneyCard entry={journey.contrasting} />
        </div>
      )}

      {journey.reflection_questions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Reflection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {journey.reflection_questions.map((question) => (
              <p key={question} className="text-sm">
                {question}
              </p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function JourneyCard({ entry }: { entry: JourneyEntryOut }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{entry.title ?? `Story ${entry.story_id}`}</CardTitle>
        <Badge variant={entry.same_theme ? "default" : "outline"}>
          {entry.same_theme ? "Same theme" : "Different theme"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-1">
        <p className="text-sm">{entry.preview}</p>
        <p className="text-xs text-muted-foreground">{entry.explanation}</p>
      </CardContent>
    </Card>
  );
}

function FingerprintChart({ query }: { query: UseQueryResult<FingerprintOut, Error> }) {
  if (query.isLoading) return <Skeleton className="mt-4 h-48 w-full" />;
  if (query.error || !query.data) {
    return <p className="mt-4 text-sm text-destructive">Could not load the fingerprint.</p>;
  }

  const fingerprint = query.data;
  const data = Object.entries(fingerprint.dimensions).map(([dimension, value]) => ({ dimension, value }));

  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs text-muted-foreground">
        Computed via {fingerprint.model} ({fingerprint.source === "llm" ? "AI-scored" : "keyword heuristic"}).
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="dimension" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#7F77DD" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
