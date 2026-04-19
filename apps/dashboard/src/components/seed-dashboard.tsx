"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { createSeedJob } from "@/lib/dashboard-api";
import { getSeedJob } from "@/lib/dashboard-api";
import type { JobStatus } from "@/lib/contracts";
import type { ScrapeJobPayload } from "@/lib/contracts";
import { isTerminalStatus } from "@/lib/contracts";

interface SeedDashboardProps {
  domains: string[];
  initialError?: string | null;
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Pending";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function statusTone(status: JobStatus) {
  switch (status) {
    case "succeeded":
      return "success";
    case "failed":
      return "danger";
    default:
      return "accent";
  }
}

function statusLabel(status: JobStatus) {
  return status.replace("_", " ");
}

export function SeedDashboard({
  domains,
  initialError,
}: SeedDashboardProps) {
  const [selectedDomain, setSelectedDomain] = useState(domains[0] ?? "");
  const [currentJob, setCurrentJob] = useState<ScrapeJobPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(initialError ?? null);
  const timerRef = useRef<number | null>(null);
  const activeJobIdRef = useRef<number | null>(null);

  const hasDomains = domains.length > 0;

  const progressLabel = useMemo(() => {
    if (!currentJob) {
      return "Ready";
    }
    if (currentJob.status === "queued") {
      return "Queued for Celery";
    }
    if (currentJob.status === "running") {
      return "Running in Celery";
    }
    if (currentJob.status === "succeeded") {
      return "Completed";
    }
    return "Failed";
  }, [currentJob]);

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function stopPolling() {
    clearTimer();
    activeJobIdRef.current = null;
  }

  async function pollJob(jobId: number) {
    const nextJob = await getSeedJob(jobId);
    if (activeJobIdRef.current !== jobId) {
      return;
    }
    setCurrentJob(nextJob);

    if (isTerminalStatus(nextJob.status)) {
      setLoading(false);
      stopPolling();
      return;
    }

    timerRef.current = window.setTimeout(() => {
      void pollJob(jobId).catch((error: unknown) => {
        setLoading(false);
        setMessage(error instanceof Error ? error.message : String(error));
        stopPolling();
      });
    }, 1500);
  }

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      activeJobIdRef.current = null;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);

    if (!selectedDomain) {
      setMessage("Pick an enabled domain first.");
      return;
    }

    stopPolling();
    setLoading(true);

    try {
      const job = await createSeedJob(selectedDomain);
      setCurrentJob(job);
      activeJobIdRef.current = job.job_id;

      if (isTerminalStatus(job.status)) {
        setLoading(false);
        stopPolling();
        return;
      }

      timerRef.current = window.setTimeout(() => {
        void pollJob(job.job_id).catch((error: unknown) => {
          setLoading(false);
          setMessage(error instanceof Error ? error.message : String(error));
          stopPolling();
        });
      }, 1200);
    } catch (error) {
      setLoading(false);
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-3 md:grid-cols-3">
        <div className="groupbox px-4 py-3">
          <span className="groupbox__title">Domains</span>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted">
                Enabled
              </p>
              <p className="mt-2 text-2xl font-semibold">{domains.length}</p>
            </div>
            <p className="text-sm text-muted">From scraper contract</p>
          </div>
        </div>

        <div className="groupbox px-4 py-3">
          <span className="groupbox__title">Transport</span>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted">
                Live updates
              </p>
              <p className="mt-2 text-2xl font-semibold">Polling</p>
            </div>
            <p className="text-sm text-muted">SSE / WS later</p>
          </div>
        </div>

        <div className="groupbox px-4 py-3">
          <span className="groupbox__title">State</span>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted">
                Current
              </p>
              <p className="mt-2 text-2xl font-semibold">{progressLabel}</p>
            </div>
            {currentJob ? (
              <span className="badge" data-tone={statusTone(currentJob.status)}>
                {statusLabel(currentJob.status)}
              </span>
            ) : (
              <span className="badge">Ready</span>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.94fr_1.06fr]">
        <div className="groupbox p-5">
          <span className="groupbox__title">Seed job</span>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold">Trigger a scraper run</h2>
            <p className="text-sm leading-6 text-muted">
              Choose an enabled source domain and start a seed job.
            </p>
          </div>

          <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium">Domain</span>
              <select
                className="field tk-field"
                disabled={!hasDomains || loading}
                onChange={(event) => setSelectedDomain(event.target.value)}
                value={selectedDomain}
              >
                {domains.map((domain) => (
                  <option key={domain} value={domain}>
                    {domain}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <button
                className="btn btn-primary"
                disabled={!hasDomains || loading}
                type="submit"
              >
                {loading ? "Seeding..." : "Seed domain"}
              </button>
              <span className="text-sm text-muted">
                {hasDomains
                  ? "Polling starts immediately after job creation."
                  : "No enabled domains are available."}
              </span>
            </div>
          </form>

          {message ? (
            <p className="mt-6 border border-[#8f8f8f] bg-[#f7ecec] px-4 py-3 text-sm text-[#7d1717] shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c9b3b3]">
              {message}
            </p>
          ) : null}

          <div className="mt-6 grid gap-3">
            <div className="groupbox px-4 py-3">
              <span className="groupbox__title">Contract</span>
              <p className="text-sm leading-6 text-muted">
                The dashboard only creates a seed job and polls until terminal
                state.
              </p>
            </div>
            <div className="groupbox px-4 py-3">
              <span className="groupbox__title">Scope</span>
              <p className="text-sm leading-6 text-muted">
                No business logic lives here beyond orchestration and display.
              </p>
            </div>
          </div>
        </div>

        <div className="groupbox p-5" aria-live="polite">
          <span className="groupbox__title">Live result</span>
          <div className="flex flex-col gap-4 border-b border-[#b0b0b0] pb-5 md:flex-row md:items-start md:justify-between">
            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Job completion view</h2>
              <p className="text-sm leading-6 text-muted">
                This panel stays reactive until the scraper job resolves.
              </p>
            </div>

            {currentJob ? (
              <span className="badge" data-tone={statusTone(currentJob.status)}>
                {statusLabel(currentJob.status)}
              </span>
            ) : (
              <span className="badge">Waiting</span>
            )}
          </div>

          {currentJob ? (
            <div className="mt-5 space-y-5">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="metric">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted">
                    Job ID
                  </p>
                  <p className="mt-2 text-2xl font-semibold">#{currentJob.job_id}</p>
                </div>
                <div className="metric">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted">
                    Domain
                  </p>
                  <p className="mt-2 text-lg font-semibold break-all">
                    {currentJob.domain}
                  </p>
                </div>
              </div>

              <div className="groupbox px-4 py-4">
                <span className="groupbox__title">Timeline</span>
                <div className="progress-track h-1.5" />
                <div className="grid gap-4 pt-4 md:grid-cols-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-muted">
                      Created
                    </p>
                    <p className="mt-2 text-sm">{formatTimestamp(currentJob.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-muted">
                      Started
                    </p>
                    <p className="mt-2 text-sm">{formatTimestamp(currentJob.started_at)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-muted">
                      Finished
                    </p>
                    <p className="mt-2 text-sm">
                      {formatTimestamp(currentJob.finished_at)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="groupbox px-4 py-4">
                  <span className="groupbox__title">Result summary</span>
                  {Object.keys(currentJob.result_summary ?? {}).length > 0 ? (
                    <dl className="mt-3 space-y-3">
                      {Object.entries(currentJob.result_summary).map(
                        ([key, value]) => (
                          <div
                            key={key}
                            className="flex items-start justify-between gap-4 border-b border-[#d2d2d2] pb-3 last:border-b-0 last:pb-0"
                          >
                            <dt className="text-sm text-muted">{key}</dt>
                            <dd className="text-right text-sm font-medium">
                              {typeof value === "object"
                                ? JSON.stringify(value)
                                : String(value)}
                            </dd>
                          </div>
                        ),
                      )}
                    </dl>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-muted">
                      The job has not produced a result summary yet.
                    </p>
                  )}
                </div>

                <div className="groupbox px-4 py-4">
                  <span className="groupbox__title">Error</span>
                  {currentJob.error_message ? (
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[#7d1717]">
                      {currentJob.error_message}
                    </p>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-muted">
                      No error reported for this job.
                    </p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5 border border-dashed border-[#9a9a9a] bg-[#f4f4f4] px-6 py-8 text-sm leading-6 text-muted shadow-[inset_1px_1px_0_#ffffff,inset_-1px_-1px_0_#c3c3c3]">
              No job yet. Seed a domain to populate this panel.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
