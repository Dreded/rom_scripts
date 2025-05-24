#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Detect platform
is_windows = platform.system() == "Windows"

# Paths
SRC = Path("Y:/ES-DE/ROMs" if is_windows else "/mnt/Stuff/ES-DE/ROMs")
DST = Path("G:/roms" if is_windows else "/mnt/g/roms")

# System map
system_map = {
    "atari2600": "ATARI", "atari5200": "FIFTYTWOHUNDRED", "atari7800": "SEVENTYEIGHTHUNDRED",
    "cps1": "CPS1", "cps2": "CPS2", "cps3": "CPS3", "fbneo": "ARCADE", "gamegear": "GG",
    "gb": "GB", "gba": "GBA", "gbc": "GBC", "genesis": "MD", "gw": "GW", "lynx": "LYNX", "mastersystem": "MS",
    "nds": "NDS", "neocd": "NEOCD", "neogeo": "NEOGEO", "nes": "FC", "ngp": "NGP", "pcecd": "PCECD",
    "pico": "PICO", "ports": "PORTS", "psx": "PS", "scummvm": "SCUMMVM", "sega32x": "THIRTYTWOX",
    "segacd": "SEGACD", "snes": "SFC", "supergrafx": "SGFX", "tg16": "PCE", "ws": "WS"
}

# Exclusion list
excludes = ["~Filter.miyoocmd", "~Refresh roms.miyoocmd"]

# Determine targets from command-line arguments or default to all
args = sys.argv[1:]
targets = args if args else sorted(system_map.keys())

print(f"\n📂 Starting sync from {SRC} to {DST}\n")

for sys_name in targets:
    if sys_name not in system_map:
        print(f"\n❌ Unknown system: {sys_name} — skipping")
        continue

    src_path = SRC / sys_name
    dst_path = DST / system_map[sys_name]

    print(f"\n🕹️ System: {sys_name} → {system_map[sys_name]}")
    print("──────────────────────────────────────────────")

    if not src_path.is_dir() or not any(f for f in src_path.glob('*') if not f.name.startswith('.')):
        print("⚠️  Skipping: Source is empty or missing")
        continue

    print("🚚 Syncing files...")

    if is_windows:
        robocopy_cmd = ["robocopy", str(src_path), str(dst_path), "/MIR"]
        for pattern in excludes:
            robocopy_cmd.extend(["/XF", pattern])
        subprocess.run(robocopy_cmd, shell=True)
    else:
        rsync_cmd = ["rsync", "-a", "--info=progress2", "--size-only", "--delete"]
        rsync_cmd += [f"--exclude={pattern}" for pattern in excludes]
        rsync_cmd += [f"{src_path}/", str(dst_path)]
        subprocess.run(rsync_cmd)

    print(f"✅ Sync complete: {src_path} → {dst_path}")

    # Rename gamelist.xml to miyoogamelist.xml
    gamelist = dst_path / "gamelist.xml"
    miyoofile = dst_path / "miyoogamelist.xml"
    if gamelist.exists():
        print(f"📄 Renaming: {gamelist} → miyoogamelist.xml")
        gamelist.rename(miyoofile)

    # Clean miyoogamelist.xml
    if miyoofile.exists():
        print(f"🧼 Cleaning: {miyoofile}")
        try:
            tree = ET.parse(miyoofile)
            root = tree.getroot()

            for game in root.findall('game'):
                for child in list(game):
                    if child.tag not in ('path', 'name', 'image'):
                        game.remove(child)

            tree.write(miyoofile, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            print(f"⚠️  Failed to clean XML: {e}")


print("\n✅ All specified systems processed.\n")
