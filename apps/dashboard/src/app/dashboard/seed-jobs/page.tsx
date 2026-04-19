import { getEnabledDomains } from "@/lib/scraper-service";
import { SeedDashboard } from "@/components/seed-dashboard";
import { requireDashboardSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function SeedJobsPage() {
  await requireDashboardSession();

  let domains: string[] = [];
  let initialError: string | null = null;

  try {
    domains = await getEnabledDomains();
  } catch (error) {
    initialError =
      error instanceof Error ? error.message : "Failed to load domains.";
  }

  return <SeedDashboard domains={domains} initialError={initialError} />;
}
