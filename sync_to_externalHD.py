#!/usr/bin/env python3

import platform
import subprocess
import sys
import re
from pathlib import Path
from argparse import ArgumentParser, Action

# ========= USER CONFIGURATION =========

# Windows
SRC_ESDE_WIN = Path("Y:/ES-DE/ES-DE")
DST_ESDE_WIN = Path("D:/ES-DE")
SRC_ROMS_WIN = Path("Y:/ES-DE/ROMs")
DST_ROMS_WIN = Path("D:/ROMs")

# Linux
SRC_ESDE_LINUX = Path("/mnt/Stuff/ES-DE/ES-DE")
DST_ESDE_LINUX = Path("/mnt/d/ES-DE")
SRC_ROMS_LINUX = Path("/mnt/Stuff/ES-DE/ROMs")
DST_ROMS_LINUX = Path("/mnt/d/ROMs")

# ========= PLATFORM DETECTION =========

is_windows = platform.system() == "Windows"
default_src_esde = SRC_ESDE_WIN if is_windows else SRC_ESDE_LINUX
default_dst_esde = DST_ESDE_WIN if is_windows else DST_ESDE_LINUX
default_src_roms = SRC_ROMS_WIN if is_windows else SRC_ROMS_LINUX
default_dst_roms = DST_ROMS_WIN if is_windows else DST_ROMS_LINUX

# ========= ARGUMENT PARSING =========

class CollectExclude(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, [])
        getattr(namespace, self.dest).append(values)

parser = ArgumentParser(description="Sync subfolders only from ES-DE/ROMs using robocopy or rsync.")
parser.add_argument("--mirror", action="store_true", help="Enable mirroring (delete files at destination that no longer exist in source)")
parser.add_argument("--dry-run", action="store_true", help="Simulate sync without writing files")
parser.add_argument("--verbose", action="store_true", help="Show full robocopy/rsync output")
parser.add_argument("--roms", action="store_true", help="Sync ROMs subfolders")
parser.add_argument("--es-de", action="store_true", help="Sync ES-DE subfolders")
parser.add_argument("--SRC", type=str, help=f"Source override (default: {'Y:/ES-DE/ROMs' if is_windows else '/mnt/Stuff/ES-DE/ROMs'})")
parser.add_argument("--DST", type=str, help=f"Destination override (default: {'D:/ROMs' if is_windows else '/mnt/d/ROMs'})")
parser.add_argument("--exclude", action=CollectExclude, help="Exclude path (e.g., Imgs, *.pdf, psx/BadGame.chd)")
parser.add_argument("--systems", type=str, help="Comma-separated list of subfolders (systems) to sync (e.g., snes,psx,nes)")
parser.add_argument("--create-folders", action="store_true", help="Create destination subfolders if they don't exist")
args = parser.parse_args()

dry_run = args.dry_run
# Force mirroring on during dry-run to collect complete *EXTRA info
if dry_run:
    args.mirror = True
verbose_mode = args.verbose
selected_systems = [s.strip().lower() for s in args.systems.split(',')] if args.systems else None

if not args.roms and not args.es_de:
    parser.print_help()
    print("\n❌ You must specify at least one of: --roms or --es-de\n")
    sys.exit(1)

FOLDER_TARGETS = []
if args.roms:
    src = Path(args.SRC) if args.SRC else default_src_roms
    if not src.exists():
        print(f"❌ Source path does not exist: {src}")
        sys.exit(1)
    dst = Path(args.DST) if args.DST else default_dst_roms
    FOLDER_TARGETS.append(("ROMs", src, dst))
if args.es_de:
    src = Path(args.SRC) if args.SRC else default_src_esde
    if not src.exists():
        print(f"❌ Source path does not exist: {src}")
        sys.exit(1)
    dst = Path(args.DST) if args.DST else default_dst_esde
    FOLDER_TARGETS.append(("ES-DE", src, dst))

# ========= SYNC FUNCTIONS =========

highlight_re = re.compile(r'^\s*(?P<type>\*EXTRA Dir|\*EXTRA File|Newer|New File|Older|New Dir)\s+' r'(?P<size>-?\d+(\.\d+)?\s*[kKmMgG]?)\s+(?P<filename>.+)$|^\s*(?P<count>\d+)\s+(?P<path>[A-Z]:\\.*\\)$')
progress_re = re.compile(r'^\s*(\d{1,3}(\.\d+)?%)\s*$')
INDENT = " " * 8

summary = {"synced": [], "skipped_filtered": [], "skipped_missing_dst": [], "missing_src": [], "extras": {}}

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

def normalize_excludes(excludes):
    normalized = []
    for ex in excludes or []:
        path = Path(ex)
        parts = path.parts
        if len(parts) > 1 and parts[0].lower() in ["roms", "es-de"]:
            ex = Path(*parts[1:])
        normalized.append(str(ex))
    return normalized

def sync_with_robocopy(src: Path, dst: Path, excludes):
    delete_flag = "/MIR" if args.mirror else "/E"
    cmd = ["robocopy", str(src), str(dst), delete_flag, "/FFT", "/NJH", "/NJS"]

    for ex in excludes:
        path = Path(ex)
        if "*" in ex:
            cmd.extend(["/XD", path.name])
            cmd.extend(["/XF", path.name])
        elif path.is_dir() or not path.suffix:
            cmd.extend(["/XD", str(path.name)])
        else:
            cmd.extend(["/XF", str(path.name)])

    if dry_run:
        cmd.append("/L")
        print(f"🔎 [Dry run] robocopy: {src} → {dst}", end="\r")
    elif verbose_mode:
        cmd = [p for p in cmd if p not in ["/NJH", "/NJS", "/NP"]]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last_length = 0
    extra_lines = []

    try:
        for line in process.stdout:
            if verbose_mode:
                print(line, end="")
                continue

            clean_line = line.replace('\t', '    ')
            if "*EXTRA" in clean_line:
                extra_lines.append(clean_line.rstrip())

            match = highlight_re.match(clean_line)
            progress = progress_re.match(clean_line)

            if match:
                output = format_highlight_line(match, INDENT)
                print("\r" + " " * last_length, end="\r")
                print(output, end="\r")
                last_length = len(output)
            elif progress:
                print(f"\r{progress.group(1)}", end="", flush=True)
            else:
                if last_length:
                    print("\r" + " " * last_length, end="\r")
                    last_length = 0
                print(clean_line, end="")

    except KeyboardInterrupt:
        process.terminate()
        print("\n⛔ Interrupted.",end="")
        return

    process.wait()
    summary["extras"][src.name] = extra_lines
    final_status = f"✅ {'Simulated' if dry_run else 'Synced'}: {src} → {dst}"
    print("\r" + " " * last_length, end="\r", flush=True)
    print(final_status, end="")


def sync_with_rsync(src: Path, dst: Path, excludes):
    delete_flag = "--delete" if args.mirror else None
    cmd = ["rsync", "-a", f"{src}/", f"{dst}/"]
    if delete_flag:
        cmd.insert(2, delete_flag)
    if dry_run:
        cmd.insert(1, "--dry-run")
        print(f"🔎 [Dry run] rsync: {src} → {dst}", end="\r")
    else:
        cmd.insert(1, "--info=progress2")

    for ex in excludes:
        cmd.insert(1, f"--exclude={ex}")

    subprocess.run(cmd)

def sync_folder(src: Path, dst: Path, rel_excludes):

    print(f"\n📁 Syncing subfolders of: {src} → {dst}")
    print("🔍 Exclusions (relative to each system folder):")
    for e in rel_excludes:
        print(f"   - system/{e}")
    if selected_systems:
        print(f"📦 Filtering systems: {', '.join(selected_systems)}")

    for sub in sorted(src.iterdir()):
        if not sub.is_dir():
            continue
        if selected_systems and sub.name.lower() not in selected_systems:
            summary["skipped_filtered"].append(sub.name)
            continue

        target_dst = dst / sub.name

        if not target_dst.exists():
            if args.create_folders:
                target_dst.mkdir(parents=True, exist_ok=True)
            else:
                summary["skipped_missing_dst"].append(sub.name)
                print(f"\n⚠️  Skipping '{sub.name}' (destination folder does not exist)",end="")
                continue

        excludes = [e for e in rel_excludes if Path(e).parts[0].lower() in [sub.name.lower(), '*'] or Path(e).name == e]

        if is_windows:
            sync_with_robocopy(sub, target_dst, excludes)
        else:
            sync_with_rsync(sub, target_dst, excludes)

        summary["synced"].append(sub.name)

def print_summary():
    print("\n\n🔄 Sync Summary")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if summary["synced"]:
        print(f"✅ Synced: {', '.join(sorted(summary['synced']))}")
    if summary["skipped_filtered"]:
        print(f"🚫 Filtered: {', '.join(sorted(summary['skipped_filtered']))}")
    if summary["skipped_missing_dst"]:
        print(f"⚠️  Missing DST: {', '.join(sorted(summary['skipped_missing_dst']))}")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    total = sum(len(v) for k, v in summary.items() if k != "extras")
    print(f"{total} attempted / {len(summary['synced'])} synced / {len(summary['missing_src'])} missing / {len(summary['skipped_filtered']) + len(summary['skipped_missing_dst'])} skipped")

    if dry_run:
        print("\n📋 Files/Folders in destination but not in source (from robocopy *EXTRA output):")
        print("   ⚠️  These will NOT be deleted unless you use the --mirror flag.")

        for system, lines in summary["extras"].items():
            if lines:
                print(f"\n📂 {system}:")
                for line in lines:
                    print(f"   {line}")

def main():
    print("🔁 Starting sync " + ("(dry run)" if dry_run else "(real run)") + "...\n")
    normalized_excludes = normalize_excludes(args.exclude)
    for label, src, dst in FOLDER_TARGETS:
        sync_folder(src, dst, normalized_excludes)
    print_summary()
    print("\n⚠️  Only synced subfolders — files in root SRC are ignored.")
    print("⚠️  These will NOT be deleted unless you use the --mirror flag.\n")

if __name__ == "__main__":
    main()
