"use client";

import { useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const STORAGE_KEY = "thread_onboarding_seen";

function subscribe() {
  return () => {};
}

function getSeenSnapshot(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== null;
  } catch {
    // Private browsing / disabled storage — treat as "seen" so the modal
    // doesn't show on every single visit with no way to dismiss it for good.
    return true;
  }
}

function getServerSnapshot(): boolean {
  // SSR-safe default: nothing renders open in the server-rendered HTML;
  // useSyncExternalStore re-checks the real value right after hydration.
  return true;
}

export function Onboarding() {
  const seen = useSyncExternalStore(subscribe, getSeenSnapshot, getServerSnapshot);
  const [dismissed, setDismissed] = useState(false);
  const open = !seen && !dismissed;

  function dismiss() {
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Ignore — the worst case is the modal reappears next visit.
    }
    setDismissed(true);
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && dismiss()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Find yourself in someone else&apos;s experience</DialogTitle>
          <DialogDescription>
            Every point on this map is a real person&apos;s story. Explore for a few minutes — you might recognize a
            piece of your own.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-3 text-sm">
          <li>
            <strong>Hover, click, explore.</strong> Points close together felt similar things — hover to preview,
            click to read, double-click a point to see what&apos;s nearest to it.
          </li>
          <li>
            <strong>Mirror your own story.</strong> Paste a few sentences of your own and see who else has been
            there — no account needed.
          </li>
          <li>
            <strong>Nothing here is invented.</strong> Themes, journeys, and insights are grounded in real computed
            patterns — an AI may phrase them for readability, it never makes them up.
          </li>
        </ul>
        <DialogFooter>
          <Button type="button" onClick={dismiss}>
            Start exploring
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
