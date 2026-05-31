import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Job, jobRef, studioPath } from "../api";
import JobActionsMenu, { jobStatusBadgeClass } from "../components/JobActionsMenu";
import JobLogsModal from "../components/JobLogsModal";
import JobPagination from "../components/JobPagination";

const PAGE_SIZE = 15;

export default function History() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
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

  const retryJob = async (job: Job) => {
    setRetryingId(job.id);
    try {
      await api.retryJob(jobRef(job));
      await load();
    } finally {
      setRetryingId(null);
    }
  };

  const remove = async (job: Job) => {
    const label = job.title || job.slug || `Job #${job.id}`;
    if (!window.confirm(`Delete "${label}"? This removes the video and all publish history.`)) return;
    setDeletingId(job.id);
    try {
      await api.deleteJob(jobRef(job));
      if (jobs.length === 1 && page > 1) {
        setPage((p) => p - 1);
      } else {
        await load();
      }
    } catch {
      await load();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
        <h1 style={{ margin: 0 }}>History</h1>
        <JobPagination page={page} pages={pages} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
        {jobs.map((j) => (
          <div key={j.id} className="card job-row">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link to={studioPath(j)}><strong>{j.title || `Job #${j.id}`}</strong></Link>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {j.source_url || j.source_type} · {new Date(j.created_at as unknown as string).toLocaleString?.() || ""}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
                <span className={`badge badge-${jobStatusBadgeClass(j.status)}`}>{j.status}</span>
                <JobActionsMenu
                  job={j}
                  onViewLogs={setLogsJob}
                  onRetry={retryJob}
                  onDelete={remove}
                  retrying={retryingId === j.id}
                  deleting={deletingId === j.id}
                />
              </div>
            </div>
            {j.publish_results.length > 0 && (
              <ul style={{ margin: "0.75rem 0 0", paddingLeft: "1.2rem", fontSize: "0.85rem" }}>
                {j.publish_results.map((r) => (
                  <li key={r.platform}>
                    {r.platform}: {r.success ? (
                      <a href={r.platform_post_url} target="_blank" rel="noreferrer">{r.platform_post_url}</a>
                    ) : r.error_message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {total > 0 && (
        <JobPagination page={page} pages={pages} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      {logsJob && <JobLogsModal job={logsJob} onClose={() => setLogsJob(null)} />}
    </div>
  );
}
