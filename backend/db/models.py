"""SQLAlchemy models."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


DEFAULT_EDIT_SPEC: dict[str, Any] = {
    "segments": [{"start": 0.0, "end": 60.0}],
    "crop": "9:16",
    "crop_offset_y": 0,
    "audio": {"mute_original": False, "overlay_path": None, "overlay_volume": 1.0, "original_volume": 1.0},
    "captions": {"mode": "none", "srt_path": None, "style": {"font_size": 24}},
    "watermark": {"text": "", "image_path": None, "position": "bottom-right", "opacity": 0.8},
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # meta | google
    account_label: Mapped[Optional[str]] = mapped_column(String(255))
    encrypted_tokens: Mapped[str] = mapped_column(Text, nullable=False)
    permissions_json: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    stage: Mapped[str] = mapped_column(String(32), default="import")
    source_type: Mapped[str] = mapped_column(String(16), default="url")  # url | upload
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    source_platform: Mapped[Optional[str]] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(String(512))
    slug: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(1024))
    source_path: Mapped[Optional[str]] = mapped_column(String(1024))
    proxy_path: Mapped[Optional[str]] = mapped_column(String(1024))
    export_path: Mapped[Optional[str]] = mapped_column(String(1024))
    edit_spec_json: Mapped[str] = mapped_column(Text, default=json.dumps(DEFAULT_EDIT_SPEC))
    caption: Mapped[Optional[str]] = mapped_column(Text)
    publish_targets_json: Mapped[str] = mapped_column(Text, default='["instagram","facebook","youtube"]')
    progress_message: Mapped[Optional[str]] = mapped_column(String(512))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    worker_task: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    publish_results: Mapped[list["PublishResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def edit_spec(self) -> dict[str, Any]:
        return json.loads(self.edit_spec_json)

    def set_edit_spec(self, spec: dict[str, Any]) -> None:
        self.edit_spec_json = json.dumps(spec)

    def publish_targets(self) -> list[str]:
        return json.loads(self.publish_targets_json)

    def set_publish_targets(self, targets: list[str]) -> None:
        self.publish_targets_json = json.dumps(targets)


class PublishResult(Base):
    __tablename__ = "publish_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255))
    platform_post_url: Mapped[Optional[str]] = mapped_column(String(1024))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    job: Mapped["Job"] = relationship(back_populates="publish_results")


class JobEvent(Base):
    """SSE event log for job progress."""

    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(512))
    payload_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
