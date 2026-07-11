"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { MessageCircleIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { askQuestion } from "@/lib/api";

const EXAMPLE_QUESTIONS = [
  "Show me stories where someone slowly forgives a parent.",
  "What themes usually appear alongside belonging?",
  "How do the stories about isolation and family compare?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");

  const askMutation = useMutation({ mutationFn: (q: string) => askQuestion(q) });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (question.trim()) askMutation.mutate(question.trim());
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ask</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask a question in plain language — the assistant answers by calling the same search, theme, and
          fingerprint tools the rest of this app uses, never by inventing details.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3">
        <Input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What themes usually appear alongside belonging?"
          className="min-w-64 flex-1"
        />
        <Button type="submit" disabled={askMutation.isPending || !question.trim()}>
          {askMutation.isPending ? "Thinking..." : "Ask"}
        </Button>
      </form>

      {!askMutation.data && !askMutation.isPending && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((example) => (
              <Button
                key={example}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setQuestion(example)}
              >
                {example}
              </Button>
            ))}
          </div>
        </div>
      )}

      {askMutation.error && (
        <p className="text-sm text-destructive">Something went wrong asking that — try again.</p>
      )}

      {askMutation.isPending && (
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </CardContent>
        </Card>
      )}

      {askMutation.data && (
        <Card className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          <CardContent className="space-y-3">
            <div className="flex items-start gap-2">
              <MessageCircleIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="space-y-3">
                {!askMutation.data.available && <Badge variant="outline">Not configured</Badge>}
                <p className="text-sm">{askMutation.data.answer}</p>
              </div>
            </div>
            {askMutation.data.tool_calls.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Used: {askMutation.data.tool_calls.map((call) => call.tool).join(", ")}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
