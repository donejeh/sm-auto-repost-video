import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, Link2, Loader2 } from "lucide-react";
import { api, Job, jobRef, studioPath } from "../api";
import ImportProgress from "../components/ImportProgress";

type ActiveImport = {
  jobRef: string;
  sourceLabel: string;
  platform?: string;
};

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [activeImport, setActiveImport] = useState<ActiveImport | null>(null);

  const load = useCallback(async () => {
    setJobs(await api.listJobs());
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
      e.target.value = "";
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

      <h2>Recent jobs</h2>
      {jobs.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No jobs yet. Import a video to get started.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {jobs.map((j) => (
            <Link key={j.id} to={studioPath(j)} className="card card-link">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong>{j.title || `Job #${j.id}`}</strong>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {j.source_platform} · {j.stage} · {j.status}
                  </div>
                  {(j.status === "downloading" || j.status === "queued") && (
                    <div className="job-row-progress">
                      <div className="job-row-progress__bar" />
                    </div>
                  )}
                </div>
                <span className={`badge badge-${j.status === "completed" ? "success" : j.status === "failed" ? "danger" : j.status === "downloading" ? "warning" : "muted"}`}>
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
