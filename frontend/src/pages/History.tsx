import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";
import { api, Job, jobRef, studioPath } from "../api";

export default function History() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setJobs(await api.listJobs());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (job: Job) => {
    const ref = jobRef(job);
    const label = job.title || job.slug || `Job #${job.id}`;
    if (!window.confirm(`Delete "${label}"? This removes the video and all publish history.`)) return;
    setDeleting(ref);
    try {
      await api.deleteJob(ref);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch {
      await load();
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      <h1>History</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {jobs.map((j) => (
          <div key={j.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link to={studioPath(j)}><strong>{j.title || `Job #${j.id}`}</strong></Link>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {j.source_url || j.source_type} · {new Date(j.created_at as unknown as string).toLocaleString?.() || ""}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
                <span className={`badge badge-${j.status === "completed" ? "success" : j.status === "failed" ? "danger" : "muted"}`}>{j.status}</span>
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ padding: "0.35rem 0.65rem" }}
                  disabled={deleting === jobRef(j)}
                  onClick={() => remove(j)}
                  title="Delete job"
                >
                  <Trash2 size={16} />
                </button>
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
    </div>
  );
}
