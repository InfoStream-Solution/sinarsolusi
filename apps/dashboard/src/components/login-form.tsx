"use client";

import { useSearchParams } from "next/navigation";
import { normalizeNextPath } from "@/lib/paths";

export function LoginForm() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  const nextValue = normalizeNextPath(searchParams.get("next"));

  return (
    <section className="groupbox w-full max-w-md p-6 md:p-8">
      <span className="groupbox__title">Sign in</span>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
      </div>

      {error === "invalid" ? (
        <p className="mt-5 border border-[#8f8f8f] bg-[#f7ecec] px-4 py-3 text-sm text-[#7d1717] shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c9b3b3]">
          Invalid username or password.
        </p>
      ) : null}

      <form className="mt-6 space-y-4" method="post" action="/api/auth/login">
        <input type="hidden" name="next" value={nextValue} />

        <label className="block space-y-2">
          <span className="text-sm font-medium">Username</span>
          <input
            className="field tk-field"
            autoComplete="username"
            name="username"
            required
            type="text"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium">Password</span>
          <input
            className="field tk-field"
            autoComplete="current-password"
            name="password"
            required
            type="password"
          />
        </label>

        <button className="btn btn-primary w-full" type="submit">
          Sign in
        </button>
      </form>
    </section>
  );
}
