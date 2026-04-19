import { NewsPipelineList } from "@/components/news-pipeline-list";
import { requireDashboardSession } from "@/lib/auth";
import { getEnabledDomainSummaries } from "@/lib/scraper-service";

export const dynamic = "force-dynamic";

export default async function NewsPipelinePage() {
  await requireDashboardSession();

  let domains: Awaited<ReturnType<typeof getEnabledDomainSummaries>> = [];
  let initialError: string | null = null;

  try {
    domains = await getEnabledDomainSummaries();
  } catch (error) {
    initialError =
      error instanceof Error ? error.message : "Failed to load domains.";
  }

  return (
    <section className="groupbox p-6 md:p-8">
      <span className="groupbox__title">News Pipeline</span>

      {/*<div className="space-y-2">*/}
      {/*  <p className="text-sm uppercase tracking-[0.25em] text-muted">*/}
      {/*    All domains*/}
      {/*  </p>*/}
      {/*  <h2 className="text-2xl font-semibold">Domain table</h2>*/}
      {/*  <p className="text-sm leading-6 text-muted">*/}
      {/*    This table shows every configured domain, its host count, article*/}
      {/*    count, and recent job activity.*/}
      {/*  </p>*/}
      {/*</div>*/}

      {initialError ? (
        <p className="mt-6 border border-[#8f8f8f] bg-[#f7ecec] px-4 py-3 text-sm text-[#7d1717] shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c9b3b3]">
          {initialError}
        </p>
      ) : null}

      {domains.length > 0 ? (
        <div className="mt-6">
          <NewsPipelineList domains={domains} />
        </div>
      ) : (
        <div className="mt-6 border border-dashed border-[#9a9a9a] bg-[#f4f4f4] px-4 py-6 text-sm leading-6 text-muted shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c3c3c3]">
          No domains are available right now.
        </div>
      )}
    </section>
  );
}
