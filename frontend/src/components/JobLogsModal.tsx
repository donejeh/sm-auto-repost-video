import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, Job, jobRef, JobLogEvent } from "../api";

type Props = {
  job: Job;
  onClose: () => void;
};

export default function JobLogsModal({ job, onClose }: Props) {
  const [events, setEvents] = useState<JobLogEvent[]>([]);
  const [fileLog, setFileLog] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const logs = await api.getJobLogs(jobRef(job));
        if (!cancelled) {
          setEvents(logs.events);
          setFileLog(logs.file_log);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load logs");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [job]);

  const label = job.title || job.slug || `Job #${job.id}`;

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="job-logs-title">
        <div className="modal-header">
          <h3 id="job-logs-title" style={{ margin: 0 }}>Logs — {label}</h3>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {loading && <p style={{ color: "var(--text-muted)" }}>Loading logs…</p>}
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

        {!loading && !error && (
          <>
            {events.length > 0 ? (
              <ul className="job-log-events">
                {events.map((ev) => (
                  <li key={ev.id}>
                    <span className="job-log-events__time">
                      {new Date(ev.created_at).toLocaleString()}
                    </span>
                    <span className="job-log-events__type">{ev.event_type}</span>
                    <span>{ev.message || "—"}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No events recorded yet.</p>
            )}

            {fileLog && (
              <>
                <h4 style={{ marginTop: "1.25rem", marginBottom: "0.5rem" }}>Error log file</h4>
                <pre className="job-log-file">{fileLog}</pre>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
