# AutoVideo Studio

Open-source video repurpose platform: import from URL or upload, edit with FFmpeg, publish to **Instagram Reels**, **Facebook Reels**, and **YouTube Shorts**.

```
Import → Edit (trim, crop 9:16, captions, watermark, audio) → Preview → Publish
```

## Features

- **Import** — Paste TikTok, Instagram, YouTube, or Facebook URLs, or upload MP4/MOV/WebM
- **Edit studio** — Trim, split segments, 9:16 crop, mute/overlay audio, burn-in captions, watermark
- **Preview** — Platform validation warnings before publish
- **Publish** — Multi-platform dispatch with per-platform status and retry
- **Connected accounts** — Meta and Google OAuth in the dashboard (optional env token fallback)
- **Optional AI** — Caption suggestions via Anthropic-compatible or OpenAI APIs
- **Logging** — Rotating log files under `logs/` for troubleshooting (see [logs/README.md](logs/README.md))

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, SQLite |
| Worker | ARQ + Redis (inline fallback without Redis) |
| Frontend | React 18, Vite, TypeScript |
| Media | FFmpeg, yt-dlp |

## Requirements

- **Python** 3.11+
- **Node.js** 20+
- **FFmpeg** on `PATH`
- **Redis** — optional for local dev; recommended for production

## Quick start

### 1. Clone and configure

```bash
git clone <your-repo-url> autovideo
cd autovideo

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set APP_SECRET_KEY
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Create an admin user

```bash
python scripts/create_user.py you@example.com your-secure-password
```

### 3. Start the API

```bash
export PYTHONPATH=.   # Windows PowerShell: $env:PYTHONPATH=(Get-Location)
uvicorn backend.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and sign in.

### 5. Worker (production or heavy jobs)

With Redis running:

```bash
arq backend.workers.arq_worker.WorkerSettings
```

Without `REDIS_URL` in `.env`, jobs run **inline** in the API process (fine for local testing only).

## Configuration

Copy [`.env.example`](.env.example) to `.env`. Key variables:

| Variable | Purpose |
|----------|---------|
| `APP_SECRET_KEY` | Session signing — **required in production** |
| `META_APP_ID` / `META_APP_SECRET` | Facebook Login for IG + FB publish |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | YouTube OAuth |
| `INSTAGRAM_GRAPH_ACCESS_TOKEN` | Optional publish fallback without OAuth UI |
| `YTDLP_COOKIES_FILE` | Netscape cookies for YouTube/TikTok/Facebook downloads |
| `INSTAGRAM_COOKIES_FILE` | Netscape cookies for Instagram downloads |
| `ANTHROPIC_AUTH_TOKEN` | Optional AI captions (see below) |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Cookie files (downloads only)

Export cookies from your browser while logged in (Netscape format). Place in the project root:

- `cookies-youtube.txt` — YouTube, TikTok, Facebook URL imports
- `cookies-instagram.txt` — Instagram URL imports

These files are **gitignored**. They help yt-dlp bypass login walls; they are **not** used for publishing.

### OAuth redirect URIs

| Provider | Development redirect |
|----------|---------------------|
| Meta | `http://localhost:8000/api/oauth/meta/callback` |
| Google | `http://localhost:8000/api/oauth/google/callback` |

Update to your production domain when deploying.

### Optional AI

Caption suggestions use an Anthropic-compatible Messages API:

```env
ANTHROPIC_AUTH_TOKEN=your-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-20250514
```

OpenAI (`OPENAI_API_KEY`) is used as fallback. Groq (`GROQ_API_KEY`) powers Whisper caption generation.

## Troubleshooting & logs

Logs are written to the `logs/` directory:

| File | Use |
|------|-----|
| `logs/autovideo.log` | General activity |
| `logs/errors.log` | All errors with stack traces |
| `logs/jobs/job_<id>.log` | Per-job failure details |

In the UI, check **Studio** (live progress + `last_error`) and **History** (publish results).

```bash
# Tail errors while reproducing an issue
tail -f logs/errors.log
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose output, then restart the API and worker.

## Docker (production)

```bash
docker compose up -d --build
```

Services: `api`, `worker`, `redis`, `nginx` (serves frontend build + proxies API).

Mount persistent volumes for `storage/` and `data/`. Schedule storage cleanup:

```bash
python scripts/cleanup_storage.py 7   # delete job folders older than 7 days
```

See [deploy/nginx.conf](deploy/nginx.conf).

## Project layout

```
autovideo/
├── backend/          # FastAPI app, workers, publishers, FFmpeg
├── frontend/         # React dashboard
├── logs/             # Runtime logs (gitignored except README)
├── storage/          # Job media files (gitignored)
├── data/             # SQLite database (gitignored)
├── scripts/          # create_user.py, cleanup_storage.py
├── docker-compose.yml
└── .env.example
```

## Legal

Only repurpose content you own or have rights to use. Automated downloading and republishing may violate platform terms of service. You are responsible for compliance with copyright and each platform's policies.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Do **not** commit `.env`, cookie files, `storage/`, `data/`, or `logs/`
4. Open a pull request with a clear description

Issues and pull requests are welcome.
