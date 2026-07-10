"use client";

import { SignInButton, UserButton, useUser } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Explore" },
  { href: "/search", label: "Search" },
  { href: "/clusters", label: "Themes" },
  { href: "/insights", label: "Insights" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/dataset", label: "Dataset" },
  { href: "/workspace", label: "Workspace" },
];

const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
        <span className="text-sm font-semibold">WHO WE ARE Story Explorer</span>
        <nav className="flex gap-4">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "text-sm text-muted-foreground hover:text-foreground",
                pathname === link.href && "font-medium text-foreground"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto">{CLERK_ENABLED ? <AuthControls /> : <AuthNotConfigured />}</div>
      </div>
    </header>
  );
}

function AuthControls() {
  const { isSignedIn } = useUser();
  return isSignedIn ? <UserButton /> : <SignInButton mode="modal" />;
}

function AuthNotConfigured() {
  return (
    <span
      className="text-xs text-muted-foreground"
      title="Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY to enable sign-in"
    >
      Sign in (not configured)
    </span>
  );
}
