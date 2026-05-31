import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Job } from "../api";

export default function History() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    api.listJobs().then(setJobs);
  }, []);

  return (
    <div>
      <h1>History</h1>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {jobs.map((j) => (
          <div key={j.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <Link to={`/studio/${j.id}`}><strong>{j.title || `Job #${j.id}`}</strong></Link>
                <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {j.source_url || j.source_type} · {new Date(j.created_at as unknown as string).toLocaleString?.() || ""}
                </div>
              </div>
              <span className={`badge badge-${j.status === "completed" ? "success" : j.status === "failed" ? "danger" : "muted"}`}>{j.status}</span>
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
