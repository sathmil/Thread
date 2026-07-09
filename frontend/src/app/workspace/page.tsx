"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createDataset, getDatasets } from "@/lib/api";

export default function WorkspacePage() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!clerkEnabled) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="text-sm text-muted-foreground">
          Sign-in isn&apos;t configured in this environment yet. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and
          CLERK_SECRET_KEY to enable private datasets.
        </p>
      </div>
    );
  }

  return <WorkspaceContent />;
}

function WorkspaceContent() {
  const { isSignedIn, getToken } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const datasetsQuery = useQuery({
    queryKey: ["datasets", isSignedIn],
    queryFn: async () => getDatasets(isSignedIn ? await getToken() : undefined),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Sign in required.");
      return createDataset({ name, description: description || undefined }, token);
    },
    onSuccess: () => {
      setName("");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Public datasets are visible to everyone; private datasets are visible only to you.
        </p>
      </div>

      {isSignedIn ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
          className="flex flex-wrap gap-3"
        >
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Dataset name"
            className="min-w-64 flex-1"
            required
          />
          <Input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description (optional)"
            className="min-w-64 flex-1"
          />
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create dataset"}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-muted-foreground">Sign in to create your own private datasets.</p>
      )}

      {createMutation.error && (
        <p className="text-sm text-destructive">{(createMutation.error as Error).message}</p>
      )}

      {datasetsQuery.isLoading && <Skeleton className="h-24 w-full" />}
      {datasetsQuery.error && <p className="text-sm text-destructive">Could not load datasets.</p>}

      <div className="space-y-2">
        {datasetsQuery.data?.map((dataset) => (
          <Card key={dataset.id}>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">{dataset.name}</CardTitle>
              <Badge variant={dataset.visibility === "public" ? "default" : "secondary"}>
                {dataset.visibility}
              </Badge>
            </CardHeader>
            <CardContent>
              {dataset.description && <p className="text-sm text-muted-foreground">{dataset.description}</p>}
              <p className="mt-1 text-xs text-muted-foreground">Status: {dataset.status}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
