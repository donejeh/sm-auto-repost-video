"""Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class EditSpecUpdate(BaseModel):
    edit_spec: dict[str, Any]


class JobCreateUrl(BaseModel):
    source_url: str


class JobUpdate(BaseModel):
    edit_spec: Optional[dict[str, Any]] = None
    caption: Optional[str] = None
    publish_targets: Optional[list[str]] = None


class PublishRequest(BaseModel):
    platforms: list[str] = Field(default_factory=lambda: ["instagram", "facebook", "youtube"])
    caption: Optional[str] = None


class PublishResultOut(BaseModel):
    platform: str
    success: bool
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    status: str
    stage: str
    source_type: str
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    duration_seconds: Optional[float] = None
    thumbnail_path: Optional[str] = None
    proxy_path: Optional[str] = None
    export_path: Optional[str] = None
    edit_spec: dict[str, Any]
    caption: Optional[str] = None
    publish_targets: list[str]
    progress_message: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    publish_results: list[PublishResultOut] = []

    class Config:
        from_attributes = True


class JobEventOut(BaseModel):
    id: int
    event_type: str
    message: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobLogsOut(BaseModel):
    events: list[JobEventOut]
    file_log: str = ""


class JobListPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int
    pages: int


class AccountStatus(BaseModel):
    provider: str
    connected: bool
    status: str
    account_label: Optional[str] = None
    permissions: Optional[dict[str, Any]] = None
    missing_permissions: list[str] = []
