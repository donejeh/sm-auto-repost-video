"""Video download via yt-dlp."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from backend.config import ROOT_DIR, get_settings

settings = get_settings()


def _cookies_for_platform(platform: str) -> str | None:
    if platform == "instagram":
        path = ROOT_DIR / settings.instagram_cookies_file
    else:
        path = ROOT_DIR / settings.ytdlp_cookies_file
    return str(path) if path.exists() else None


def download_from_url(url: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    platform = url  # detect below
    from backend.services.platform_detect import detect_platform

    platform = detect_platform(url)
    out_template = str(output_dir / "source.%(ext)s")

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        out_template,
        "--write-info-json",
        "--no-playlist",
        url,
    ]
    cookies = _cookies_for_platform(platform)
    if cookies:
        cmd.extend(["--cookies", cookies])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "yt-dlp download failed")

    source = output_dir / "source.mp4"
    if not source.exists():
        candidates = list(output_dir.glob("source.*"))
        video_candidates = [p for p in candidates if p.suffix.lower() in {".mp4", ".webm", ".mkv"}]
        if not video_candidates:
            raise RuntimeError("Download completed but no video file found")
        source = video_candidates[0]
        if source.suffix.lower() != ".mp4":
            target = output_dir / "source.mp4"
            source.rename(target)
            source = target

    info_path = output_dir / "source.info.json"
    metadata: dict[str, Any] = {"platform": platform, "url": url}
    if info_path.exists():
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
        metadata.update(
            {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            }
        )

    return {
        "source_path": str(source),
        "platform": platform,
        "title": metadata.get("title") or f"{platform.title()} Video",
        "duration": metadata.get("duration"),
        "thumbnail_url": metadata.get("thumbnail"),
    }
