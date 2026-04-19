import type { ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";
import { DashboardNav } from "@/components/dashboard-nav";
import { requireDashboardSession } from "@/lib/auth";

export default async function DashboardLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  await requireDashboardSession();

  return (
    <div className="tk-page min-h-screen text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="tk-sidebar px-4 py-5">
          <div className="flex h-full flex-col">
            <div className="groupbox p-4">
              <span className="groupbox__title">Application</span>
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">
                  Sinar Solusi
                </p>
                <h1 className="text-lg font-semibold">Dashboard</h1>
              </div>
            </div>

            <DashboardNav />

            <div className="mt-auto pt-6">
              <p className="text-xs leading-6 text-muted">
                Internal operations only.
              </p>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-col">
          <header className="tk-header flex items-center justify-between px-5 py-4 sm:px-6 lg:px-8">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted">
                Ops console
              </p>
              <p className="text-sm text-muted">
                Trigger and monitor scraper seed jobs.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                className="btn btn-secondary px-4 py-2 text-sm"
                type="button"
              >
                Settings
              </button>
              <LogoutButton />
            </div>
          </header>

          <main className="flex-1 px-5 py-6 sm:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
