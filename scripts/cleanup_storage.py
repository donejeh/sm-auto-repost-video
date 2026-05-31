#!/usr/bin/env python3
"""Remove job storage older than N days."""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings

settings = get_settings()
days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
cutoff = time.time() - days * 86400
jobs_root = settings.storage_path / "jobs"
removed = 0

if jobs_root.exists():
    for d in jobs_root.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            removed += 1

print(f"Removed {removed} job folders older than {days} days")
