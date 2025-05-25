#!/usr/bin/env python3

import os
import time
from pathlib import Path

# ==== CONFIGURATION ====
# Update this to point to the directory you want to scan
SOURCE_DIR = Path("Y:/ES-DE/ROMs")
FILE_TYPES = [".zip"]  # Extend as needed, e.g. [".zip", ".chd"]
THRESHOLD = 315532800  # Jan 1, 1980 in epoch time

# ==== TIMESTAMP FIXER ====
def fix_invalid_access_times(base_dir: Path):
    now = time.time()
    fixed = 0
    scanned = 0

    for file in base_dir.rglob("*"):
        if file.is_file() and file.suffix.lower() in FILE_TYPES:
            try:
                stat = file.stat()
                scanned += 1
                if stat.st_atime < THRESHOLD:
                    os.utime(file, (now, stat.st_mtime))
                    print(f"✅ Fixed atime: {file}")
                    fixed += 1
            except Exception as e:
                print(f"⚠️ Could not process {file}: {e}")

    print(f"\nFinished. Scanned: {scanned}, Fixed: {fixed}")

if __name__ == "__main__":
    print(f"🔧 Fixing access times in: {SOURCE_DIR}\n")
    fix_invalid_access_times(SOURCE_DIR)
