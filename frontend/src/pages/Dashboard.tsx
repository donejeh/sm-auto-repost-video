import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Link2 } from "lucide-react";
import { api, Job } from "../api";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setJobs(await api.listJobs());
  }, []);

  useEffect(() => { load(); }, [load]);

  const importUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const job = await api.createFromUrl(url.trim());
      window.location.href = `/studio/${job.id}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const job = await api.upload(file);
      window.location.href = `/studio/${job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>
      <p style={{ color: "var(--text-muted)" }}>Import a video, edit it, and publish to Reels & Shorts.</p>

      <div className="card" style={{ marginBottom: "2rem" }}>
        <h3 style={{ marginTop: 0 }}>New project</h3>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <input
            className="input"
            style={{ flex: 1, minWidth: 280 }}
            placeholder="Paste TikTok, Instagram, YouTube, or Facebook URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && importUrl()}
          />
          <button type="button" className="btn btn-primary" onClick={importUrl} disabled={loading}>
            <Link2 size={16} /> Import URL
          </button>
          <label className="btn btn-ghost" style={{ cursor: "pointer" }}>
            <Upload size={16} /> Upload file
            <input type="file" accept="video/*" hidden onChange={onFile} />
          </label>
        </div>
        {error && <p style={{ color: "var(--danger)", marginBottom: 0 }}>{error}</p>}
      </div>

      <h2>Recent jobs</h2>
      {jobs.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No jobs yet. Import a video to get started.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {jobs.map((j) => (
            <Link key={j.id} to={`/studio/${j.id}`} className="card" style={{ display: "block" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>{j.title || `Job #${j.id}`}</strong>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {j.source_platform} · {j.stage} · {j.status}
                  </div>
                </div>
                <span className={`badge badge-${j.status === "completed" ? "success" : j.status === "failed" ? "danger" : "muted"}`}>
                  {j.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
