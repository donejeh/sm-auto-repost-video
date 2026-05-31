"""AutoVideo FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.api import accounts, auth_routes, editor, jobs, oauth_google, oauth_meta
from backend.config import get_settings
from backend.db.session import init_db
from backend.logging_config import setup_logging

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="AutoVideo", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(jobs.router)
app.include_router(editor.router)
app.include_router(oauth_meta.router)
app.include_router(oauth_google.router)
app.include_router(accounts.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "redis": settings.use_redis}


class SuggestCaptionBody(BaseModel):
    title: str
    platform: str = "instagram"
    context: str = ""


@app.post("/api/ai/suggest-caption")
async def suggest_caption_endpoint(body: SuggestCaptionBody):
    from backend.services.ai import suggest_caption

    text = await suggest_caption(body.title, body.platform, body.context)
    if not text:
        return {"available": False, "caption": None}
    return {"available": True, "caption": text}
