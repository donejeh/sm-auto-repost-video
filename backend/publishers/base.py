"""Publisher base types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PublishOutcome:
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PlatformCredentials:
    access_token: str
    account_id: str
    page_id: Optional[str] = None
