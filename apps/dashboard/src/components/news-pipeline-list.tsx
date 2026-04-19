"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import type { DomainAction } from "@/lib/contracts";
import type { DomainSummaryPayload } from "@/lib/contracts";
import { getDomainSummaries } from "@/lib/dashboard-api";
import { startDomainAction } from "@/lib/dashboard-api";

interface NewsPipelineListProps {
  domains: DomainSummaryPayload[];
}

type StageKey = "seed" | "extract" | "import";

type DialogState =
  | { kind: "hosts"; domain: string }
  | { kind: "pipeline"; domain: string }
  | null;

const stageConfig: Record<
  StageKey,
  {
    label: string;
    statusKey: "last_seed_status" | "last_extract_status" | "last_import_status";
    timestampKey: "last_seed" | "last_extract" | "last_import";
  }
> = {
  seed: {
    label: "Seed",
    statusKey: "last_seed_status",
    timestampKey: "last_seed",
  },
  extract: {
    label: "Extract",
    statusKey: "last_extract_status",
    timestampKey: "last_extract",
  },
  import: {
    label: "Import",
    statusKey: "last_import_status",
    timestampKey: "last_import",
  },
};

function isActiveStatus(status: string | null | undefined) {
  return status === "queued" || status === "running";
}

function pendingKey(domain: string, stage: StageKey) {
  return `${domain}:${stage}`;
}

function formatRelativeTime(value: string | null) {
  if (!value) {
    return "Never";
  }

  const date = new Date(value);
  const diffSeconds = Math.floor((date.getTime() - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (absSeconds < 60) {
    return "just now";
  }
  if (absSeconds < 3600) {
    return rtf.format(Math.round(diffSeconds / 60), "minute");
  }
  if (absSeconds < 86400) {
    return rtf.format(Math.round(diffSeconds / 3600), "hour");
  }
  if (absSeconds < 2592000) {
    return rtf.format(Math.round(diffSeconds / 86400), "day");
  }
  if (absSeconds < 31536000) {
    return rtf.format(Math.round(diffSeconds / 2592000), "month");
  }

  return rtf.format(Math.round(diffSeconds / 31536000), "year");
}

export function NewsPipelineList({ domains: initialDomains }: NewsPipelineListProps) {
  const [domains, setDomains] = useState(initialDomains);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [pendingKeys, setPendingKeys] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const refreshDomains = useCallback(async () => {
    try {
      const nextDomains = await getDomainSummaries();
      setDomains(nextDomains);
      setPendingKeys((current) =>
        current.filter((key) => {
          const [domain, stage] = key.split(":") as [string, StageKey];
          const summary = nextDomains.find((item) => item.domain === domain);
          if (!summary) {
            return false;
          }

          return isStageBusy(summary, stage);
        }),
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }, []);

  useEffect(() => {
    const shouldPoll =
      pendingKeys.length > 0 ||
      domains.some((domain) =>
        (["seed", "extract", "import"] as StageKey[]).some((stage) =>
          isStageBusy(domain, stage),
        ),
      );

    if (!shouldPoll) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      void refreshDomains();
    }, 2000);

    return () => window.clearInterval(interval);
  }, [domains, pendingKeys, refreshDomains]);

  const openHostsDialog = useCallback((domain: string) => {
    setDialog({ kind: "hosts", domain });
  }, []);

  const openPipelineDialog = useCallback((domain: string) => {
    setDialog({ kind: "pipeline", domain });
  }, []);

  const handleAction = useCallback(
    async (domain: string, action: DomainAction) => {
      const nextPendingKeys = action === "pipeline" ? [pendingKey(domain, "seed")] : [];

      setMessage(null);
      setDialog(null);

      if (nextPendingKeys.length > 0) {
        setPendingKeys((current) => Array.from(new Set([...current, ...nextPendingKeys])));
      }

      try {
        await startDomainAction(domain, action);
        await refreshDomains();
      } catch (error) {
        if (nextPendingKeys.length > 0) {
          setPendingKeys((current) =>
            current.filter((key) => !nextPendingKeys.includes(key)),
          );
        }
        setMessage(error instanceof Error ? error.message : String(error));
      }
    },
    [refreshDomains],
  );

  const selectedHostDomain =
    dialog?.kind === "hosts"
      ? domains.find((item) => item.domain === dialog.domain) ?? null
      : null;

  return (
    <div className="space-y-3">
      {message ? (
        <p className="border border-[#8f8f8f] bg-[#f7ecec] px-4 py-3 text-sm text-[#7d1717] shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c9b3b3]">
          {message}
        </p>
      ) : null}

      <div className="overflow-hidden border border-[#9a9a9a] bg-[#efefef] shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c3c3c3]">
        <table className="min-w-full border-separate border-spacing-0">
          <thead>
            <tr className="bg-[#e7e7e7] text-left">
              <th className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted">
                Domain
              </th>
              <th className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted">
                Hosts
              </th>
              <th className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted">
                Articles
              </th>
              <th
                className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted"
                colSpan={3}
              >
                Job Status
              </th>
              <th className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted">
                Status
              </th>
              <th className="border-b border-[#b0b0b0] px-2 py-2 text-[11px] uppercase tracking-[0.18em] text-muted">
                Actions
              </th>
            </tr>
            <tr className="bg-[#ececec] text-left">
              <th />
              <th />
              <th />
              <th className="border-b border-[#b0b0b0] px-2 pb-2 text-[11px] uppercase tracking-[0.16em] text-muted">
                Seed
              </th>
              <th className="border-b border-[#b0b0b0] px-2 pb-2 text-[11px] uppercase tracking-[0.16em] text-muted">
                Extract
              </th>
              <th className="border-b border-[#b0b0b0] px-2 pb-2 text-[11px] uppercase tracking-[0.16em] text-muted">
                Import
              </th>
              <th />
              <th />
            </tr>
          </thead>

          <tbody>
            {domains.map((domain) => (
              <Fragment key={domain.domain}>
                <tr className="align-middle">
                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold leading-5">{domain.domain}</p>
                    </div>
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    <span
                      className="cursor-pointer select-text text-sm font-semibold leading-5"
                      onClick={() => openHostsDialog(domain.domain)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          openHostsDialog(domain.domain);
                        }
                      }}
                    >
                      {domain.host_count}
                    </span>
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    <span className="text-sm font-semibold leading-5">
                      {domain.article_count}
                    </span>
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    {renderStageValue(domain, "seed", pendingKeys)}
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    {renderStageValue(domain, "extract", pendingKeys)}
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    {renderStageValue(domain, "import", pendingKeys)}
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    <span
                      className="badge badge-compact"
                      data-tone={domain.enabled ? "success" : "danger"}
                    >
                      {domain.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>

                  <td className="border-b border-[#c5c5c5] px-2 py-2 align-middle">
                    <button
                      className="btn btn-secondary btn-compact"
                      disabled={!domain.enabled}
                      type="button"
                      onClick={() => openPipelineDialog(domain.domain)}
                    >
                      Run pipeline
                    </button>
                  </td>
                </tr>
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {dialog?.kind === "pipeline" ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 px-4 py-6"
          role="presentation"
          onClick={() => setDialog(null)}
        >
          <div
            className="groupbox w-full max-w-md p-4"
            role="dialog"
            aria-modal="true"
            aria-label="Pipeline confirmation"
            onClick={(event) => event.stopPropagation()}
          >
            <span className="groupbox__title">Confirm pipeline</span>

            <p className="text-sm leading-5">
              This will run seed, extract, and import for domain{" "}
              <span className="font-semibold">{dialog.domain}</span>. Please
              confirm.
            </p>
            <div className="mt-3 flex justify-end gap-2">
              <button
                className="btn btn-secondary btn-compact"
                type="button"
                onClick={() => setDialog(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-compact"
                type="button"
                onClick={() => void handleAction(dialog.domain, "pipeline")}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {dialog?.kind === "hosts" ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 px-4 py-6"
          role="presentation"
          onClick={() => setDialog(null)}
        >
          <div
            className="groupbox w-full max-w-lg p-4"
            role="dialog"
            aria-modal="true"
            aria-label={`Hosts for ${dialog.domain}`}
            onClick={(event) => event.stopPropagation()}
          >
            <span className="groupbox__title">Hosts</span>

            {selectedHostDomain?.hosts.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-5">
                {selectedHostDomain.hosts.map((host) => (
                  <li key={host}>{host}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm leading-5 text-muted">
                No hosts are configured for this domain.
              </p>
            )}

            <div className="mt-3 flex justify-end">
              <button
                className="btn btn-primary btn-compact"
                type="button"
                onClick={() => setDialog(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function isStageBusy(summary: DomainSummaryPayload, stage: StageKey) {
  const config = stageConfig[stage];
  const status = summary[config.statusKey];
  return isActiveStatus(status);
}

function renderStageValue(
  summary: DomainSummaryPayload,
  stage: StageKey,
  pendingKeys: string[],
) {
  const key = pendingKey(summary.domain, stage);
  if (pendingKeys.includes(key) || isStageBusy(summary, stage)) {
    return <span className="text-sm font-medium leading-5">running..</span>;
  }

  const status = summary[stageConfig[stage].statusKey];
  if (status === "failed") {
    return <span className="text-sm font-medium leading-5 text-[#7d1717]">failed</span>;
  }

  return (
    <span className="text-sm leading-5">
      {formatRelativeTime(summary[stageConfig[stage].timestampKey])}
    </span>
  );
}
