import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Download, Film, Loader2, AlertCircle } from "lucide-react";
import { api, Job, JobRef, studioPath, useJobEvents } from "../api";

const PLATFORM_LABEL: Record<string, string> = {
  instagram: "Instagram",
  youtube: "YouTube",
  tiktok: "TikTok",
  facebook: "Facebook",
  upload: "Upload",
};

type StepState = "pending" | "active" | "done" | "error";

function stepState(current: number, index: number, failed: boolean): StepState {
  if (failed && index === current) return "error";
  if (index < current) return "done";
  if (index === current) return "active";
  return "pending";
}

interface ImportProgressProps {
  jobRef: JobRef;
  sourceLabel?: string;
  platform?: string;
  onDismiss?: () => void;
  /** When false, stay on current page when import completes (e.g. Studio). Default: true */
  autoNavigate?: boolean;
}

export default function ImportProgress({
  jobRef,
  sourceLabel,
  platform,
  onDismiss,
  autoNavigate = true,
}: ImportProgressProps) {
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [message, setMessage] = useState("Starting import…");
  const [percent, setPercent] = useState(8);
  const [failed, setFailed] = useState(false);
  const navigated = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const j = await api.getJob(jobRef);
      setJob(j);
      if (j.progress_message) setMessage(j.progress_message);

      if (j.status === "failed") {
        setFailed(true);
        setMessage(j.last_error || "Import failed");
        setPercent(0);
        return;
      }
      if (j.status === "ready") {
        setPercent(100);
        setMessage(autoNavigate ? "Ready — opening editor…" : "Ready — loading editor…");
        if (!navigated.current) {
          navigated.current = true;
          if (autoNavigate) {
            setTimeout(() => navigate(studioPath(j)), 600);
          }
        }
        return;
      }
      if (j.status === "downloading") {
        setPercent((p) => Math.max(p, 25));
      }
      if (j.status === "processing") {
        setPercent((p) => Math.max(p, 92));
        setMessage(j.progress_message || "Preparing preview…");
      }
    } catch {
      /* ignore poll errors */
    }
  }, [jobRef, navigate, autoNavigate]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [refresh]);

  useJobEvents(jobRef, (ev) => {
    const e = ev as {
      type?: string;
      message?: string;
      status?: string;
      payload?: { percent?: number };
    };
    if (e.message) setMessage(e.message);
    if (e.type === "download_progress" && typeof e.payload?.percent === "number") {
      setPercent(Math.min(90, Math.max(20, e.payload.percent)));
    }
    if (e.type === "download_started") setPercent(20);
    if (e.type === "download_complete") setPercent(95);
    if (e.status === "failed" || e.type === "error") {
      setFailed(true);
      if (e.message) setMessage(e.message);
    }
    refresh();
  });

  const currentStep = failed ? 1 : job?.status === "ready" ? 3 : job?.status === "processing" ? 2 : 1;
  const steps = [
    { label: "Job created", icon: CheckCircle2 },
    { label: "Download video", icon: Download },
    { label: "Prepare editor", icon: Film },
  ];

  const platformName = platform ? PLATFORM_LABEL[platform] || platform : "Video";

  return (
    <div className={`import-progress ${failed ? "import-progress--failed" : ""}`}>
      <div className="import-progress__header">
        <div className="import-progress__icon-wrap">
          {failed ? (
            <AlertCircle size={28} className="import-progress__icon import-progress__icon--error" />
          ) : percent >= 100 ? (
            <CheckCircle2 size={28} className="import-progress__icon import-progress__icon--success" />
          ) : (
            <Loader2 size={28} className="import-progress__icon import-progress__icon--spin" />
          )}
        </div>
        <div>
          <h3 className="import-progress__title">
            {failed ? "Import failed" : `Importing from ${platformName}`}
          </h3>
          {sourceLabel && (
            <p className="import-progress__source" title={sourceLabel}>
              {sourceLabel.length > 72 ? `${sourceLabel.slice(0, 72)}…` : sourceLabel}
            </p>
          )}
        </div>
      </div>

      <div className="import-progress__bar-track">
        <div
          className={`import-progress__bar-fill ${percent < 90 && !failed ? "import-progress__bar-fill--pulse" : ""}`}
          style={{ width: `${failed ? 100 : percent}%` }}
        />
      </div>
      <p className="import-progress__message">{message}</p>
      {!failed && percent < 100 && (
        <p className="import-progress__hint">This can take a minute for long reels. Keep this tab open.</p>
      )}

      <ol className="import-progress__steps">
        {steps.map((s, i) => {
          const state = stepState(currentStep, i, failed);
          const Icon = s.icon;
          return (
            <li key={s.label} className={`import-progress__step import-progress__step--${state}`}>
              <Icon size={16} />
              <span>{s.label}</span>
            </li>
          );
        })}
      </ol>

      {failed && (
        <div className="import-progress__actions">
          <button type="button" className="btn btn-ghost" onClick={onDismiss}>
            Try again
          </button>
          <button type="button" className="btn btn-primary" onClick={() => navigate(job ? studioPath(job) : `/studio/${jobRef}`)}>
            View details
          </button>
        </div>
      )}
    </div>
  );
}
