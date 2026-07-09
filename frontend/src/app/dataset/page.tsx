"use client";

import { useQuery } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getStories } from "@/lib/api";

export default function DatasetPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["stories"], queryFn: getStories });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Dataset</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The raw stories, enriched with inferred metadata.
        </p>
      </div>

      {isLoading && <Skeleton className="h-64 w-full" />}
      {error && <p className="text-sm text-destructive">Could not load stories.</p>}
      {data?.length === 0 && <p className="text-sm text-muted-foreground">No stories in this dataset yet.</p>}

      {data && data.length > 0 && (
        <Table className="table-fixed">
          <TableHeader>
            <TableRow>
              <TableHead className="w-14">ID</TableHead>
              <TableHead className="w-56">Title</TableHead>
              <TableHead className="w-40">Focus</TableHead>
              <TableHead className="w-16">Words</TableHead>
              <TableHead>Preview</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((story) => (
              <TableRow key={story.external_id}>
                <TableCell>{story.external_id}</TableCell>
                <TableCell className="truncate" title={story.title ?? undefined}>
                  {story.title}
                </TableCell>
                <TableCell className="truncate">{story.focus}</TableCell>
                <TableCell>{story.word_count}</TableCell>
                <TableCell className="truncate text-muted-foreground" title={story.preview}>
                  {story.preview}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
