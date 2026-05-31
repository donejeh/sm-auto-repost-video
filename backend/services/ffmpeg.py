"""FFmpeg video processing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

EXPORT_WIDTH = 1080
EXPORT_HEIGHT = 1920


def _run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "ffmpeg failed")


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return 0.0
    data = json.loads(proc.stdout)
    return float(data.get("format", {}).get("duration", 0))


def probe_has_audio(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def generate_proxy(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-i",
        str(source),
        "-vf",
        "scale=720:-2",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "28",
    ]
    if probe_has_audio(source):
        args.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        args.append("-an")
    args.append(str(output))
    _run_ffmpeg(args)


def generate_thumbnail(source: Path, output: Path, at_seconds: float = 1.0) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "-ss",
            str(at_seconds),
            "-i",
            str(source),
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(output),
        ]
    )


def _build_filter_complex(edit_spec: dict[str, Any], job_dir: Path, *, has_audio: bool = True) -> tuple[str, list[str], list[str]]:
    """Build filter_complex and extra inputs for export."""
    segments = edit_spec.get("segments") or [{"start": 0, "end": 60}]
    crop = edit_spec.get("crop", "9:16")
    offset_y = int(edit_spec.get("crop_offset_y", 0))
    audio_cfg = edit_spec.get("audio") or {}
    captions = edit_spec.get("captions") or {}
    watermark = edit_spec.get("watermark") or {}

    extra_inputs: list[str] = []
    filter_parts: list[str] = []

    # Concat segments from same input
    seg_filters = []
    for i, seg in enumerate(segments):
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 60))
        seg_filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
        if not audio_cfg.get("mute_original") and has_audio:
            vol = float(audio_cfg.get("original_volume", 1.0))
            seg_filters.append(
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,volume={vol}[a{i}]"
            )
        else:
            seg_filters.append(
                f"anullsrc=r=44100:cl=stereo,atrim=end={end - start},asetpts=PTS-STARTPTS[a{i}]"
            )

    n = len(segments)
    if n == 1:
        v_in, a_in = "[v0]", "[a0]"
    else:
        v_concat = "".join(f"[v{i}]" for i in range(n))
        a_concat = "".join(f"[a{i}]" for i in range(n))
        seg_filters.append(f"{v_concat}concat=n={n}:v=1:a=0[vcat]")
        seg_filters.append(f"{a_concat}concat=n={n}:v=0:a=1[acat]")
        v_in, a_in = "[vcat]", "[acat]"

    if crop == "9:16":
        # Center crop to 9:16 then scale to export size
        crop_expr = (
            f"{v_in}crop=ih*9/16:ih:(iw-ih*9/16)/2:{offset_y},"
            f"scale={EXPORT_WIDTH}:{EXPORT_HEIGHT}[vcrop]"
        )
    else:
        crop_expr = f"{v_in}scale={EXPORT_WIDTH}:{EXPORT_HEIGHT}[vcrop]"

    seg_filters.append(crop_expr)
    v_out = "[vcrop]"

    # Watermark text
    if watermark.get("text"):
        pos = watermark.get("position", "bottom-right")
        opacity = float(watermark.get("opacity", 0.8))
        if pos == "bottom-right":
            x, y = "w-tw-40", "h-th-40"
        elif pos == "top-left":
            x, y = "40", "40"
        else:
            x, y = "(w-tw)/2", "h-th-80"
        text = watermark["text"].replace(":", "\\:").replace("'", "\\'")
        seg_filters.append(
            f"{v_out}drawtext=text='{text}':fontsize=36:fontcolor=white@{opacity}:x={x}:y={y}[vwm]"
        )
        v_out = "[vwm]"

    # Burn-in captions
    if captions.get("mode") == "burn_in" and captions.get("srt_path"):
        srt = Path(captions["srt_path"])
        if srt.exists():
            srt_escaped = str(srt).replace("\\", "/").replace(":", "\\:")
            font_size = captions.get("style", {}).get("font_size", 24)
            seg_filters.append(
                f"{v_out}subtitles='{srt_escaped}':force_style='FontSize={font_size},PrimaryColour=&HFFFFFF&'[vfinal]"
            )
            v_out = "[vfinal]"

    # Audio overlay
    overlay_path = audio_cfg.get("overlay_path")
    a_out = a_in
    if overlay_path and Path(overlay_path).exists():
        extra_inputs.extend(["-i", overlay_path])
        ov_vol = float(audio_cfg.get("overlay_volume", 1.0))
        input_idx = 1
        seg_filters.append(f"[{input_idx}:a]volume={ov_vol}[aov]")
        seg_filters.append(f"{a_in}[aov]amix=inputs=2:duration=first[aout]")
        a_out = "[aout]"

    filter_parts.extend(seg_filters)
    return ";".join(filter_parts), extra_inputs, [v_out.strip("[]"), a_out.strip("[]")]


def export_final(source: Path, output: Path, edit_spec: dict[str, Any], job_dir: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    has_audio = probe_has_audio(source)
    fc, extra_inputs, maps = _build_filter_complex(edit_spec, job_dir, has_audio=has_audio)
    args = ["-i", str(source), *extra_inputs, "-filter_complex", fc, "-map", f"[{maps[0]}]", "-map", f"[{maps[1]}]"]
    args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            "90",
            str(output),
        ]
    )
    _run_ffmpeg(args)


def export_preview(source: Path, output: Path, edit_spec: dict[str, Any], job_dir: Path) -> None:
    """Lower quality preview export."""
    output.parent.mkdir(parents=True, exist_ok=True)
    has_audio = probe_has_audio(source)
    fc, extra_inputs, maps = _build_filter_complex(edit_spec, job_dir, has_audio=has_audio)
    args = ["-i", str(source), *extra_inputs, "-filter_complex", fc, "-map", f"[{maps[0]}]", "-map", f"[{maps[1]}]"]
    args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-t",
            "90",
            str(output),
        ]
    )
    _run_ffmpeg(args)
