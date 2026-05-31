import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, Job, useJobEvents } from "../api";

const STEPS = ["Import", "Edit", "Preview", "Publish", "Done"];

type Tab = "trim" | "crop" | "audio" | "captions" | "watermark";

export default function Studio() {
  const { id } = useParams();
  const jobId = Number(id);
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [tab, setTab] = useState<Tab>("trim");
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [validationWarnings, setValidationWarnings] = useState<Record<string, string[]>>({});
  const saveTimer = useRef<number>();

  const refresh = useCallback(async () => {
    const j = await api.getJob(jobId);
    setJob(j);
    if (j.stage === "edit" || j.status === "ready") setStep(Math.max(step, 1));
    if (j.export_path || j.stage === "publish") setStep(Math.max(step, 2));
    if (j.status === "publishing" || j.status === "completed") setStep(3);
    if (j.status === "completed") setStep(4);
  }, [jobId, step]);

  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, [refresh]);

  useJobEvents(jobId, (ev) => {
    const e = ev as { message?: string; status?: string };
    if (e.message) setStatusMsg(e.message);
    refresh();
  });

  if (!job) return <p>Loading...</p>;

  const spec = job.edit_spec as {
    segments?: { start: number; end: number }[];
    crop?: string;
    crop_offset_y?: number;
    audio?: { mute_original?: boolean; overlay_volume?: number; original_volume?: number };
    captions?: { mode?: string };
    watermark?: { text?: string; position?: string; opacity?: number };
  };
  const seg = spec.segments?.[0] || { start: 0, end: 60 };

  const patchSpec = (patch: object) => {
    const next = { ...job.edit_spec, ...patch };
    setJob({ ...job, edit_spec: next });
    clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      setSaving(true);
      await api.updateJob(jobId, { edit_spec: next });
      setSaving(false);
    }, 500);
  };

  const updateSegment = (field: "start" | "end", val: number) => {
    const segments = [{ ...seg, [field]: val }];
    patchSpec({ segments });
  };

  const splitAtPlayhead = () => {
    const mid = (seg.start + seg.end) / 2;
    patchSpec({ segments: [{ start: seg.start, end: mid }, { start: mid, end: seg.end }] });
  };

  const applyPreview = async () => {
    setStatusMsg("Rendering preview...");
    await api.exportJob(jobId);
    await refresh();
    try {
      const v = await api.validateJob(jobId);
      setValidationWarnings(v.warnings);
    } catch {
      setValidationWarnings({});
    }
    setStep(2);
  };

  const publish = async () => {
    await api.publishJob(jobId, job.publish_targets, job.caption);
    setStep(3);
    await refresh();
  };

  const videoSrc = job.status !== "queued" && job.status !== "downloading"
    ? api.mediaUrl(jobId, step >= 2 ? "preview" : "proxy")
    : undefined;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h1 style={{ margin: 0 }}>{job.title || `Studio #${job.id}`}</h1>
        <span className="badge badge-muted">{saving ? "Saving..." : job.status}</span>
      </div>

      <div className="stepper">
        {STEPS.map((s, i) => (
          <div key={s} className={`step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>{i + 1}. {s}</div>
        ))}
      </div>

      {statusMsg && <div className="status-bar">{statusMsg}</div>}
      {job.last_error && <div className="status-bar" style={{ color: "var(--danger)" }}>{job.last_error}</div>}

      {step === 0 && job.status === "downloading" && (
        <div className="card"><p>Downloading source video...</p></div>
      )}

      {(step >= 1 || job.status === "ready") && step < 3 && (
        <div className="grid-2">
          <div className="card">
            {videoSrc ? (
              <video key={videoSrc} src={videoSrc} controls playsInline />
            ) : (
              <p style={{ color: "var(--text-muted)" }}>Video processing...</p>
            )}
            <div className="timeline">
              <div
                className="timeline-range"
                style={{
                  left: `${(seg.start / (job.duration_seconds || 60)) * 100}%`,
                  width: `${((seg.end - seg.start) / (job.duration_seconds || 60)) * 100}%`,
                }}
              />
            </div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Trim: {seg.start.toFixed(1)}s – {seg.end.toFixed(1)}s
              {job.duration_seconds ? ` / ${job.duration_seconds.toFixed(0)}s total` : ""}
            </p>
          </div>

          <div className="card">
            <div className="tabs">
              {(["trim", "crop", "audio", "captions", "watermark"] as Tab[]).map((t) => (
                <button key={t} type="button" className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {tab === "trim" && (
              <>
                <label className="label">Start (seconds)</label>
                <input className="input" type="number" step="0.1" value={seg.start} onChange={(e) => updateSegment("start", +e.target.value)} />
                <label className="label" style={{ marginTop: "0.75rem" }}>End (seconds)</label>
                <input className="input" type="number" step="0.1" value={seg.end} onChange={(e) => updateSegment("end", +e.target.value)} />
                <button type="button" className="btn btn-ghost" style={{ marginTop: "0.75rem" }} onClick={splitAtPlayhead}>Split segment at midpoint</button>
              </>
            )}

            {tab === "crop" && (
              <>
                <label className="label">Aspect ratio</label>
                <select className="input" value={spec.crop || "9:16"} onChange={(e) => patchSpec({ crop: e.target.value })}>
                  <option value="9:16">9:16 (Reels / Shorts)</option>
                  <option value="original">Original</option>
                </select>
                <label className="label" style={{ marginTop: "0.75rem" }}>Vertical offset</label>
                <input className="input" type="number" value={spec.crop_offset_y || 0} onChange={(e) => patchSpec({ crop_offset_y: +e.target.value })} />
              </>
            )}

            {tab === "audio" && (
              <>
                <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input type="checkbox" checked={!!spec.audio?.mute_original} onChange={(e) => patchSpec({ audio: { ...spec.audio, mute_original: e.target.checked } })} />
                  Mute original audio
                </label>
                <label className="label" style={{ marginTop: "0.75rem" }}>Original volume</label>
                <input className="input" type="range" min={0} max={2} step={0.1} value={spec.audio?.original_volume ?? 1} onChange={(e) => patchSpec({ audio: { ...spec.audio, original_volume: +e.target.value } })} />
                <label className="label" style={{ marginTop: "0.75rem" }}>Overlay audio (MP3/WAV)</label>
                <input type="file" accept="audio/*" onChange={async (e) => { const f = e.target.files?.[0]; if (f) await api.uploadAudio(jobId, f); refresh(); }} />
              </>
            )}

            {tab === "captions" && (
              <>
                <button type="button" className="btn btn-ghost" onClick={async () => { await api.generateCaptions(jobId); refresh(); }}>Generate captions (AI)</button>
                <label className="label" style={{ marginTop: "0.75rem" }}>Upload SRT</label>
                <input type="file" accept=".srt" onChange={async (e) => { const f = e.target.files?.[0]; if (f) await api.uploadCaptions(jobId, f); refresh(); }} />
              </>
            )}

            {tab === "watermark" && (
              <>
                <label className="label">Watermark text</label>
                <input className="input" value={spec.watermark?.text || ""} onChange={(e) => patchSpec({ watermark: { ...spec.watermark, text: e.target.value } })} placeholder="@YourPage" />
                <label className="label" style={{ marginTop: "0.75rem" }}>Opacity</label>
                <input className="input" type="range" min={0.1} max={1} step={0.1} value={spec.watermark?.opacity ?? 0.8} onChange={(e) => patchSpec({ watermark: { ...spec.watermark, opacity: +e.target.value } })} />
              </>
            )}

            <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.5rem" }}>
              <button type="button" className="btn btn-primary" onClick={applyPreview}>Apply & Preview</button>
            </div>
          </div>
        </div>
      )}

      {step >= 2 && step < 4 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h3>Preview & Publish</h3>
          <video src={api.mediaUrl(jobId, "preview")} controls playsInline style={{ maxWidth: 360, margin: "1rem 0" }} />
          {Object.keys(validationWarnings).length > 0 && (
            <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: "var(--warning)" }}>
              {Object.entries(validationWarnings).map(([platform, msgs]) => (
                <div key={platform}><strong>{platform}</strong>: {msgs.join("; ")}</div>
              ))}
            </div>
          )}
          <label className="label">Caption</label>
          <textarea className="input" rows={3} value={job.caption || ""} onChange={(e) => setJob({ ...job, caption: e.target.value })} onBlur={() => api.updateJob(jobId, { caption: job.caption })} />
          <button type="button" className="btn btn-ghost" style={{ marginTop: "0.5rem" }} onClick={async () => {
            const r = await api.suggestCaption(job.title || "Video", "instagram");
            if (r.caption) setJob({ ...job, caption: r.caption });
          }}>AI suggest caption</button>

          <p className="label" style={{ marginTop: "1rem" }}>Platforms</p>
          <div className="platform-grid">
            {["instagram", "facebook", "youtube"].map((p) => (
              <div
                key={p}
                className={`platform-chip ${job.publish_targets.includes(p) ? "selected" : ""}`}
                onClick={() => {
                  const targets = job.publish_targets.includes(p)
                    ? job.publish_targets.filter((x) => x !== p)
                    : [...job.publish_targets, p];
                  setJob({ ...job, publish_targets: targets });
                  api.updateJob(jobId, { publish_targets: targets });
                }}
              >
                {p === "instagram" && "Instagram Reels"}
                {p === "facebook" && "Facebook Reels"}
                {p === "youtube" && "YouTube Shorts"}
              </div>
            ))}
          </div>

          <button type="button" className="btn btn-primary" style={{ marginTop: "1.5rem" }} onClick={publish} disabled={job.status === "publishing"}>
            Publish to selected platforms
          </button>

          {job.publish_results.map((r) => (
            <div key={r.platform} style={{ marginTop: "0.75rem", fontSize: "0.9rem" }}>
              <strong>{r.platform}</strong>:{" "}
              {r.success ? (
                <a href={r.platform_post_url} target="_blank" rel="noreferrer" style={{ color: "var(--success)" }}>{r.platform_post_url}</a>
              ) : (
                <span style={{ color: "var(--danger)" }}>{r.error_message || "Failed"}</span>
              )}
              {!r.success && (
                <button type="button" className="btn btn-ghost" style={{ marginLeft: "0.5rem", padding: "0.25rem 0.5rem" }} onClick={() => api.retryPlatform(jobId, r.platform).then(refresh)}>Retry</button>
              )}
            </div>
          ))}
        </div>
      )}

      {step >= 4 && (
        <div className="card">
          <h3>Done</h3>
          <p>Job completed. <button type="button" className="btn btn-ghost" onClick={() => navigate("/history")}>View history</button></p>
        </div>
      )}
    </div>
  );
}
