#!/usr/bin/env python3

import platform
import subprocess
import sys
import re
from pathlib import Path

# ========= USER CONFIGURATION =========
# 🛠️ Only modify the section below that matches your OS

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
verbose_mode = "--verbose" in sys.argv

# Set up source/destination pairs
FOLDER_PAIRS = [
    (SRC_ESDE_WIN, DST_ESDE_WIN) if is_windows else (SRC_ESDE_LINUX, DST_ESDE_LINUX),
    (SRC_ROMS_WIN, DST_ROMS_WIN) if is_windows else (SRC_ROMS_LINUX, DST_ROMS_LINUX)
]

# ========= REGEX FOR ROBUST LINE MATCHING =========
# Matches:
# 1. Robocopy operation lines like "New File 123456 File.png"
# 2. Folder summary lines like "48    Y:\Path\To\Folder\"
# 3. Progress lines like " 42.8%  "
highlight_re = re.compile(
    r'^\s*(?P<type>\*EXTRA Dir|\*EXTRA File|Newer|New File|Older|New Dir)\s+'
    r'(?P<size>-?\d+(\.\d+)?\s*[kKmMgG]?)\s+(?P<filename>.+)$|'
    r'^\s*(?P<count>\d+)\s+(?P<path>[A-Z]:\\.*\\)$'
)
progress_re = re.compile(r'^\s*(\d{1,3}(\.\d+)?%)\s*$')

INDENT = " " * 8  # aligns output away from robocopy progress updates

# ========= FORMATTER =========

def format_highlight_line(match: re.Match, prefix: str) -> str:
    if match.group('type'):
        type_ = match.group('type')
        size = match.group('size').strip()
        filename = match.group('filename')
        return f"{prefix}{type_:<12} {size:>8}  {filename}"
    else:
        count = match.group('count')
        path = match.group('path')
        return f"{prefix}Folder       {count:>6}  {path}"

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

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last_length = 0

    try:
        for line in process.stdout:
            if verbose_mode:
                sys.stdout.write(line)
                sys.stdout.flush()
                continue

            clean_line = line.replace('\t', '    ')  # Preserve \r for progress updates
            match = highlight_re.match(clean_line)
            progress = progress_re.match(clean_line)

            if match:
                output = format_highlight_line(match, INDENT)
                print("\r" + " " * last_length, end="\r", flush=True)
                print(output, end="\r", flush=True)
                last_length = len(output)
            elif progress:
                print(f"\r{progress.group(1)}", end="", flush=True)
            else:
                if last_length:
                    print("\r" + " " * last_length, end="\r", flush=True)
                    last_length = 0
                print(clean_line, end='', flush=True)

    except KeyboardInterrupt:
        process.terminate()
        print("\n⛔ Sync interrupted by user.")
        return

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
