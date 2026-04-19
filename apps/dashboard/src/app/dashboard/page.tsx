import { requireDashboardSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  await requireDashboardSession();

  return (
    <section className="groupbox p-6 md:p-8">
      <span className="groupbox__title">Home</span>
      <p className="text-sm uppercase tracking-[0.25em] text-muted">
        Home
      </p>
      <h2 className="mt-2 text-2xl font-semibold">
        Welcome to the dashboard
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
        Use the Seed jobs section to start and monitor scraper runs.
      </p>
    </section>
  );
}
