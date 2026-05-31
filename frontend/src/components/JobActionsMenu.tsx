import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, FileText, MoreVertical, RefreshCw, Trash2 } from "lucide-react";
import { Job, studioPath } from "../api";

type Props = {
  job: Job;
  onViewLogs: (job: Job) => void;
  onRetry: (job: Job) => void;
  onDelete: (job: Job) => void;
  retrying?: boolean;
  deleting?: boolean;
};

export function canRetryJob(job: Job): boolean {
  if (job.stage === "import" && ["queued", "failed", "downloading"].includes(job.status)) return true;
  if (job.stage === "publish" && ["queued", "failed"].includes(job.status)) return true;
  if (["preview", "export"].includes(job.stage) && ["queued", "failed"].includes(job.status)) return true;
  return false;
}

export function isJobProcessing(job: Job): boolean {
  return ["downloading", "processing", "exporting", "publishing"].includes(job.status);
}

export function isStaleQueued(job: Job): boolean {
  if (job.status !== "queued") return false;
  const ts = job.updated_at ? new Date(job.updated_at).getTime() : 0;
  return Date.now() - ts > 90_000;
}

export default function JobActionsMenu({ job, onViewLogs, onRetry, onDelete, retrying, deleting }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const showRetry = canRetryJob(job);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div className="job-menu" ref={rootRef}>
      <button
        type="button"
        className="btn btn-ghost job-menu__trigger"
        aria-label="Job actions"
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        <MoreVertical size={18} />
      </button>
      {open && (
        <div className="job-menu__dropdown" role="menu">
          <button
            type="button"
            role="menuitem"
            className="job-menu__item"
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              navigate(studioPath(job));
            }}
          >
            <Eye size={16} /> View in studio
          </button>
          <button
            type="button"
            role="menuitem"
            className="job-menu__item"
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onViewLogs(job);
            }}
          >
            <FileText size={16} /> View logs
          </button>
          {showRetry && (
            <button
              type="button"
              role="menuitem"
              className="job-menu__item"
              disabled={retrying}
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                onRetry(job);
              }}
            >
              <RefreshCw size={16} className={retrying ? "import-progress__icon--spin" : ""} />
              {retrying ? "Retrying…" : "Retry"}
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            className="job-menu__item job-menu__item--danger"
            disabled={deleting}
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              onDelete(job);
            }}
          >
            <Trash2 size={16} /> {deleting ? "Deleting…" : "Clear job"}
          </button>
        </div>
      )}
    </div>
  );
}

export function jobStatusBadgeClass(status: string): string {
  if (status === "completed" || status === "ready") return "success";
  if (status === "failed") return "danger";
  if (["downloading", "processing", "exporting", "publishing"].includes(status)) return "warning";
  return "muted";
}
