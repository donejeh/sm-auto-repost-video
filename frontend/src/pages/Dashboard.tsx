import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Link2, Loader2 } from "lucide-react";
import { api, Job, jobRef, studioPath } from "../api";
import ImportProgress from "../components/ImportProgress";
import JobActionsMenu, {
  isJobProcessing,
  isStaleQueued,
  jobStatusBadgeClass,
} from "../components/JobActionsMenu";
import JobLogsModal from "../components/JobLogsModal";
import JobPagination from "../components/JobPagination";

type ActiveImport = {
  jobRef: string;
  sourceLabel: string;
  platform?: string;
};

const PAGE_SIZE = 10;

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [activeImport, setActiveImport] = useState<ActiveImport | null>(null);
  const [logsJob, setLogsJob] = useState<Job | null>(null);
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    const res = await api.listJobs(page, PAGE_SIZE);
    setJobs(res.items);
    setTotal(res.total);
    setPages(res.pages);
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const needsPoll = jobs.some(
      (j) => isJobProcessing(j) || j.status === "queued",
    );
    if (!needsPoll) return;
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, [jobs, load]);

  const importUrl = async () => {
    if (!url.trim() || submitting || activeImport) return;
    setSubmitting(true);
    setError("");
    try {
      const job = await api.createFromUrl(url.trim());
      setActiveImport({
        jobRef: jobRef(job),
        sourceLabel: url.trim(),
        platform: job.source_platform,
      });
      setUrl("");
      setPage(1);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start import");
    } finally {
      setSubmitting(false);
    }
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || submitting || activeImport) return;
    setSubmitting(true);
    setError("");
    try {
      const job = await api.upload(file);
      setActiveImport({
        jobRef: jobRef(job),
        sourceLabel: file.name,
        platform: "upload",
      });
      setPage(1);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
      e.target.value = "";
    }
  };

  const retryJob = async (job: Job) => {
    setRetryingId(job.id);
    try {
      await api.retryJob(jobRef(job));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetryingId(null);
    }
  };

  const deleteJob = async (job: Job) => {
    const label = job.title || job.slug || `Job #${job.id}`;
    if (!window.confirm(`Clear "${label}"? This removes the video and all files.`)) return;
    setDeletingId(job.id);
    try {
      await api.deleteJob(jobRef(job));
      if (jobs.length === 1 && page > 1) {
        setPage((p) => p - 1);
      } else {
        await load();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
      await load();
    } finally {
      setDeletingId(null);
    }
  };

  const busy = submitting || !!activeImport;

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <p style={{ color: "var(--text-muted)" }}>Import a video, edit it, and publish to Reels & Shorts.</p>

      {activeImport && (
        <ImportProgress
          jobRef={activeImport.jobRef}
          sourceLabel={activeImport.sourceLabel}
          platform={activeImport.platform}
          onDismiss={() => setActiveImport(null)}
        />
      )}

      <div className="card" style={{ marginBottom: "2rem", marginTop: activeImport ? "1.5rem" : 0 }}>
        <h3 style={{ marginTop: 0 }}>New project</h3>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            className="input"
            style={{ flex: 1, minWidth: 280 }}
            placeholder="Paste TikTok, Instagram, YouTube, or Facebook URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !busy && importUrl()}
            disabled={busy}
          />
          <button type="button" className="btn btn-primary" onClick={importUrl} disabled={busy || !url.trim()}>
            {submitting ? (
              <>
                <Loader2 size={16} className="import-progress__icon--spin" /> Starting…
              </>
            ) : (
              <>
                <Link2 size={16} /> Import URL
              </>
            )}
          </button>
          <label className={`btn btn-ghost ${busy ? "btn-disabled" : ""}`} style={{ cursor: busy ? "not-allowed" : "pointer" }}>
            <Upload size={16} /> Upload file
            <input type="file" accept="video/*" hidden onChange={onFile} disabled={busy} />
          </label>
        </div>
        {error && <p style={{ color: "var(--danger)", marginBottom: 0, marginTop: "0.75rem" }}>{error}</p>}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>Recent jobs</h2>
        <JobPagination
          page={page}
          pages={pages}
          total={total}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      </div>

      {jobs.length === 0 ? (
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>No jobs yet. Import a video to get started.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
          {jobs.map((j) => (
            <div key={j.id} className="card job-row">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                <Link to={studioPath(j)} className="job-row__link" style={{ flex: 1, minWidth: 0 }}>
                  <strong>{j.title || `Job #${j.id}`}</strong>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {j.source_platform} · {j.stage} · {j.status}
                    {j.progress_message ? ` · ${j.progress_message}` : ""}
                  </div>
                  {isJobProcessing(j) && (
                    <div className="job-row-progress">
                      <div className="job-row-progress__bar" />
                    </div>
                  )}
                  {isStaleQueued(j) && (
                    <div className="job-row-stale">
                      Stuck in queue — open menu and choose Retry
                    </div>
                  )}
                  {j.status === "failed" && j.last_error && (
                    <div className="job-row-error">{j.last_error}</div>
                  )}
                </Link>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
                  <span className={`badge badge-${jobStatusBadgeClass(j.status)}`}>{j.status}</span>
                  <JobActionsMenu
                    job={j}
                    onViewLogs={setLogsJob}
                    onRetry={retryJob}
                    onDelete={deleteJob}
                    retrying={retryingId === j.id}
                    deleting={deletingId === j.id}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {total > 0 && (
        <JobPagination
          page={page}
          pages={pages}
          total={total}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}

      {logsJob && <JobLogsModal job={logsJob} onClose={() => setLogsJob(null)} />}
    </div>
  );
}
