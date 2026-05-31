# AutoVideo log files (generated at runtime — not committed)

This directory is created automatically when the API or worker starts.

| File | Contents |
|------|----------|
| `autovideo.log` | General application and worker activity (INFO and above) |
| `errors.log` | Errors only — API failures, job failures, stack traces |
| `jobs/job_<id>.log` | Per-job error history with full tracebacks |

## Where else to look

- **Dashboard / Studio** — job `last_error` and live SSE progress
- **History page** — failed publish results per platform
- **SQLite** — `job_events` table stores the event timeline for each job

## Tips

- Increase verbosity: set `LOG_LEVEL=DEBUG` in `.env` and restart the API/worker
- Rotate logs automatically (5 MB × 5 for app log, 10 for errors)
- Safe to delete old files; they are recreated on next run
