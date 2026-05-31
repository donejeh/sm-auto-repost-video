"""Caption generation helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def audio_to_srt(audio_path: Path, srt_path: Path) -> None:
    """Generate SRT via Groq Whisper if key available, else placeholder."""
    from backend.config import get_settings

    settings = get_settings()
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    if settings.groq_api_key:
        import httpx

        with open(audio_path, "rb") as f:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": f},
                data={"model": "whisper-large-v3", "response_format": "srt"},
                timeout=120,
            )
        if resp.status_code == 200:
            srt_path.write_text(resp.text, encoding="utf-8")
            return

    # Fallback: extract audio and write minimal srt placeholder
    _extract_audio_wav(audio_path.with_suffix(".wav") if audio_path.suffix != ".wav" else audio_path)
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:05,000\n(Caption generation requires GROQ_API_KEY)\n",
        encoding="utf-8",
    )


def extract_audio_from_video(video: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-acodec", "pcm_s16le", str(output)],
        check=True,
        capture_output=True,
    )


def _extract_audio_wav(path: Path) -> None:
    if path.exists():
        return
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc", "-t", "1", str(path)],
        capture_output=True,
    )
