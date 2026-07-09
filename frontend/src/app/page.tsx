"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getStories, search, type SearchUnit } from "@/lib/api";

const UNITS: SearchUnit[] = ["Sentences", "Passages", "Stories"];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [unit, setUnit] = useState<SearchUnit>("Passages");
  const [topK, setTopK] = useState(5);

  const searchResult = useQuery({
    queryKey: ["search", submittedQuery, unit, topK],
    queryFn: () => search({ query: submittedQuery, unit, top_k: topK }),
    enabled: submittedQuery.length > 0,
  });

  const fallbackStories = useQuery({
    queryKey: ["stories"],
    queryFn: getStories,
    enabled: submittedQuery.length === 0,
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmittedQuery(query.trim());
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Find stories by meaning</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search embeds your query, compares it with sentence, passage, or full-story embeddings, and ranks the
          closest matches by cosine similarity.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="belonging, identity, voice, education..."
          className="min-w-64 flex-1"
        />
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
          max={20}
          value={topK}
          onChange={(event) => setTopK(Number(event.target.value) || 1)}
          className="w-20"
        />
        <Button type="submit">Search</Button>
      </form>

      {submittedQuery ? (
        <SearchResults
          isLoading={searchResult.isLoading}
          error={searchResult.error}
          data={searchResult.data}
        />
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Type a theme, phrase, or research question to retrieve the closest stories.
          </p>
          {fallbackStories.isLoading && <Skeleton className="h-24 w-full" />}
          {fallbackStories.error && (
            <p className="text-sm text-destructive">Could not load stories.</p>
          )}
          {fallbackStories.data?.length === 0 && (
            <p className="text-sm text-muted-foreground">No stories in this dataset yet.</p>
          )}
          {fallbackStories.data?.slice(0, topK).map((story) => (
            <Card key={story.external_id}>
              <CardHeader>
                <CardTitle className="text-base">
                  <Link href={`/stories/${story.id}`} className="hover:underline">
                    Story {story.external_id}
                  </Link>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <p className="text-sm text-muted-foreground">{story.title}</p>
                {story.focus && <Badge variant="secondary">{story.focus}</Badge>}
                <p className="text-sm">{story.preview}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function SearchResults({
  isLoading,
  error,
  data,
}: {
  isLoading: boolean;
  error: Error | null;
  data: Awaited<ReturnType<typeof search>> | undefined;
}) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">Search failed: {error.message}</p>;
  }

  if (!data || data.results.length === 0) {
    return <p className="text-sm text-muted-foreground">No matches found.</p>;
  }

  return (
    <div className="space-y-3">
      {data.results.map((result) => (
        <Card key={`${result.story_id}-${result.unit_index}`}>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">
              <Link href={`/stories/${result.story_uuid}`} className="hover:underline">
                Story {result.story_id}
              </Link>{" "}
              &middot; {result.unit_type} {result.unit_index}
            </CardTitle>
            <Badge>{result.score.toFixed(2)} similarity</Badge>
          </CardHeader>
          <CardContent className="space-y-1">
            {result.theme && <p className="text-xs text-muted-foreground">Theme: {result.theme}</p>}
            <p className="text-sm">{result.text_unit}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
