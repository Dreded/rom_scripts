#!/usr/bin/env python3

import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Detect OS
is_windows = platform.system() == "Windows"

# Base paths
SRC = Path("Y:/ES-DE/ROMs" if is_windows else "/mnt/Stuff/ES-DE/ROMs")
DST = Path("G:/roms" if is_windows else "/mnt/g/roms")

# System mapping
system_map = {
    "atari2600": "ATARI", "atari5200": "FIFTYTWOHUNDRED", "atari7800": "SEVENTYEIGHTHUNDRED",
    "cps1": "CPS1", "cps2": "CPS2", "cps3": "CPS3", "fbneo": "ARCADE", "gamegear": "GG",
    "gb": "GB", "gba": "GBA", "gbc": "GBC", "genesis": "MD", "gw": "GW", "lynx": "LYNX", "mastersystem": "MS",
    "nds": "NDS", "neocd": "NEOCD", "neogeo": "NEOGEO", "nes": "FC", "ngp": "NGP", "pcecd": "PCECD",
    "pico": "PICO", "ports": "PORTS", "psx": "PS", "scummvm": "SCUMMVM", "sega32x": "THIRTYTWOX",
    "segacd": "SEGACD", "snes": "SFC", "supergrafx": "SGFX", "tg16": "PCE", "ws": "WS"
}

# Files to exclude
excludes = ["~Filter.miyoocmd", "~Refresh roms.miyoocmd"]

# Clean XML
def clean_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        for game in root.findall("game"):
            for child in list(game):
                if child.tag not in ("path", "name", "image"):
                    game.remove(child)
        tree.write(xml_file, encoding="utf-8", xml_declaration=True)
        print(f"🧼 Cleaned: {xml_file}")
    except Exception as e:
        print(f"⚠️ XML cleanup failed: {e}")

# Sync for Windows with unfiltered robocopy output
def sync_windows_with_progress(src_path, dst_path):
    robocopy_cmd = ["robocopy", str(src_path), str(dst_path), "/MIR", "/NDL", "/NJH", "/NJS", "/NC"]
    for pattern in excludes:
        robocopy_cmd += ["/XF", pattern]

    print("🚚 Syncing files...")

    proc = subprocess.Popen(
        robocopy_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            if line.endswith('%'):
                print(f"\r{line}  \r", end='', flush=True)
            elif len(line) > 10:
                sys.stdout.write("\r" + " " * 120 + "\r")
                relative = str(line)
                src_str = str(src_path)
                if src_str in line:
                    relative = line.split(src_str, 1)[-1].lstrip("\\/")
                print(f"\r\t{relative}", end='', flush=True)
    except Exception as e:
        print(f"\n❌ Robocopy error: {e}")

    proc.wait()
    sys.stdout.write("\r" + " " * 80 + "\r")
    print(f"✅ Sync complete: {src_path} → {dst_path}")




# Sync for Unix (Linux/macOS)
def sync_unix(src_path, dst_path):
    rsync_cmd = ["rsync", "-a", "--info=progress2", "--size-only", "--delete"]
    rsync_cmd += [f"--exclude={pattern}" for pattern in excludes]
    rsync_cmd += [f"{src_path}/", str(dst_path)]
    subprocess.run(rsync_cmd)
    sys.stdout.write("\033[F\033[K")
    print(f"✅ Sync complete: {src_path} → {dst_path}")

# Main
args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
targets = args if args else sorted(system_map.keys())

print(f"\n📂 Starting sync from {SRC} to {DST}\n")

for sys_name in targets:
    if sys_name not in system_map:
        print(f"\n❌ Unknown system: {sys_name} — skipping")
        continue

    dst_name = system_map[sys_name]
    src_path = SRC / sys_name
    dst_path = DST / dst_name

    print(f"\n🎩 System: {sys_name} → {dst_name}")
    print("─" * 46)

    if not src_path.is_dir() or not any(f for f in src_path.glob("*") if not f.name.startswith(".")):
        print("⚠️  Skipping: Source is empty or missing")
        continue

    if is_windows:
        sync_windows_with_progress(src_path, dst_path)
    else:
        sync_unix(src_path, dst_path)

    # Rename and clean gamelist
    gamelist = dst_path / "gamelist.xml"
    miyoofile = dst_path / "miyoogamelist.xml"
    if gamelist.exists():
        gamelist.rename(miyoofile)
        print(f"📄 Renamed: {gamelist.name} → {miyoofile.name}")
    if miyoofile.exists():
        clean_xml(miyoofile)

print("\n✅ All specified systems processed.\n")
