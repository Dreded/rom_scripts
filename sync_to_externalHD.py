#!/usr/bin/env python3

import platform
import subprocess
import sys
import re
from pathlib import Path

# ========= USER CONFIGURATION =========
# 🔧 Only modify the section below that matches your OS

# --- Windows Paths ---
SRC_ESDE_WIN = Path("Y:/ES-DE/ES-DE")
DST_ESDE_WIN = Path("D:/ES-DE")

SRC_ROMS_WIN = Path("Y:/ES-DE/ROMs")
DST_ROMS_WIN = Path("D:/ROMs")

# --- Linux Paths ---
SRC_ESDE_LINUX = Path("/mnt/Stuff/ES-DE/ES-DE")
DST_ESDE_LINUX = Path("/mnt/d/ES-DE")

SRC_ROMS_LINUX = Path("/mnt/Stuff/ES-DE/ROMs")
DST_ROMS_LINUX = Path("/mnt/d/ROMs")

# ========= EXCLUSION RULES =========
# Exclude folders or files *relative to each system folder* in ROMs.
EXCLUDE_RULES = {
    "ROMs": {
        "dirs": ["Imgs", "Manuals"],
        "files": ["gamelist.xml"]
    },
    "ES-DE": {
        "dirs": [],
        "files": []
    }
}

# ========= INTERNAL SETUP =========

is_windows = platform.system() == "Windows"
dry_run = "--run" not in sys.argv

# Set up source/destination pairs
FOLDER_PAIRS = [
    (SRC_ESDE_WIN, DST_ESDE_WIN) if is_windows else (SRC_ESDE_LINUX, DST_ESDE_LINUX),
    (SRC_ROMS_WIN, DST_ROMS_WIN) if is_windows else (SRC_ROMS_LINUX, DST_ROMS_LINUX)
]

# ========= SYNC FUNCTIONS =========

def sync_with_robocopy(src: Path, dst: Path, exclude=None):
    cmd = [
        "robocopy",
        str(src),
        str(dst),
        "/MIR",
        "/FFT",
        # "/NJH", "/NJS", "/NP"  # Clean output: No Job Header / No Job Summary / No Progress
    ]
    if exclude:
        for path in exclude.get("dirs", []):
            for sub in src.iterdir():
                if sub.is_dir():
                    cmd.extend(["/XD", str(sub / path)])
        for path in exclude.get("files", []):
            for sub in src.iterdir():
                if sub.is_dir():
                    cmd.extend(["/XF", str(sub / path)])

    if dry_run:
        cmd.append("/L")
        print(f"🔎 Dry run (Windows): {' '.join(cmd)}")

    print(f"▶ Running: {' '.join(cmd)}\n")

    # Let robocopy print normally
    process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    process.wait()

    if process.returncode <= 7:
        print(f"\n✅ {'Simulated' if dry_run else 'Synced'}: {src} → {dst}")
    else:
        print(f"\n❌ Robocopy error (code {process.returncode}) for {src} → {dst}")

def sync_with_rsync(src: Path, dst: Path, exclude=None):
    cmd = [
        "rsync",
        "-a",
        "--delete",
        "--modify-window=2",
        f"{src}/",
        f"{dst}/"
    ]
    if not dry_run:
        cmd.insert(1, "--info=progress2")
    if exclude:
        for path in exclude.get("dirs", []):
            cmd.insert(1, f"--exclude=*/{path}/")
        for path in exclude.get("files", []):
            cmd.insert(1, f"--exclude=*/{path}")
    if dry_run:
        cmd.insert(1, "--dry-run")
        print(f"🔎 Dry run (Linux): {' '.join(cmd)}")

    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"✅ {'Simulated' if dry_run else 'Synced'}: {src} → {dst}")
    else:
        print(f"❌ rsync error (code {result.returncode}) for {src} → {dst}")

# ========= MAIN =========

def main():
    print("🔁 Starting sync " + ("(dry run)" if dry_run else "(real run)") + "...\n")
    for src, dst in FOLDER_PAIRS:
        folder_key = src.name
        exclude = EXCLUDE_RULES.get(folder_key, {})
        if is_windows:
            sync_with_robocopy(src, dst, exclude)
        else:
            sync_with_rsync(src, dst, exclude)

if __name__ == "__main__":
    main()
