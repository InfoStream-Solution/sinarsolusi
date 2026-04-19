"use client";

export function LogoutButton() {
  return (
    <form action="/api/auth/logout" method="post">
      <button className="btn btn-secondary px-4 py-2 text-sm" type="submit">
        Sign out
      </button>
    </form>
  );
}
