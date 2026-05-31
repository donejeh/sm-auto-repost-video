"""Platform validation before publish."""

from __future__ import annotations

from pathlib import Path

from backend.services.ffmpeg import probe_duration

LIMITS = {
    "instagram": {"max_duration": 90, "warn_duration": 60},
    "facebook": {"max_duration": 90, "warn_duration": 60},
    "youtube": {"max_duration": 60, "warn_duration": 55},
}


def validate_export(platform: str, video_path: Path) -> list[str]:
    warnings: list[str] = []
    if not video_path.exists():
        return [f"Export file missing: {video_path}"]

    duration = probe_duration(video_path)
    limits = LIMITS.get(platform, LIMITS["instagram"])
    if duration > limits["max_duration"]:
        warnings.append(
            f"{platform}: duration {duration:.0f}s exceeds max {limits['max_duration']}s"
        )
    elif duration > limits.get("warn_duration", limits["max_duration"]):
        warnings.append(f"{platform}: duration {duration:.0f}s is near the limit")

    return warnings
