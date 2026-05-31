"""URL-friendly job slugs."""

from __future__ import annotations

import re
import secrets


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return (text[:60] or "video")


def make_initial_slug() -> str:
    return f"video-{secrets.token_hex(4)}"


def refresh_slug_from_title(title: str, current_slug: str) -> str:
    suffix = current_slug.rsplit("-", 1)[-1] if current_slug else secrets.token_hex(4)
    return f"{slugify(title)}-{suffix}"[:128]
