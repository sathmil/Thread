import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const clerkConfigured = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY
);

// No routes require sign-in yet (the public seed dataset is meant to work
// unauthenticated) — this just makes req.auth() available app-wide. Falls
// back to a no-op so `npm run dev` doesn't crash before real keys exist.
export default clerkConfigured ? clerkMiddleware() : () => NextResponse.next();

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
