#!/usr/bin/env python3

import os
import sys
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

# Root folders
ROMS_DIR = Path("D:/ROMs")
GAMELISTS_DIR = Path("D:/ES-DE/gamelists")

missing = {}
skipped_systems = []
removed_entries = {}

def extract_game_list_only(filepath):
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    start = content.find("<gameList>")
    end = content.find("</gameList>") + len("</gameList>")
    if start == -1 or end == -1:
        raise ValueError(f"No <gameList> found in {filepath}")
    cleaned = content[start:end]
    return ET.fromstring(cleaned)

def check_gamelists(dry_run=True, do_backup=True):
    print(f"\n🔍 Scanning gamelists for missing ROMs... ({'dry run' if dry_run else 'modifying files'})")
    for system_folder in GAMELISTS_DIR.iterdir():
        if not system_folder.is_dir():
            continue

        gamelist_path = system_folder / "gamelist.xml"
        roms_path = ROMS_DIR / system_folder.name

        if not gamelist_path.exists():
            continue

        if not roms_path.exists():
            print(f"⚠️  Skipping '{system_folder.name}' — no matching ROM folder found.")
            skipped_systems.append(system_folder.name)
            continue

        print(f"📄 Checking {system_folder.name}\\gamelist.xml...")

        try:
            root = extract_game_list_only(gamelist_path)
        except Exception as e:
            print(f"  ❌ Could not parse XML: {e}")
            continue

        missing_files = []
        games = root.findall("game")

        for game in games[:]:
            path_elem = game.find("path")
            if path_elem is None or not path_elem.text:
                continue

            rom_path = roms_path / path_elem.text.strip().lstrip("./")
            if not rom_path.exists():
                missing_files.append(path_elem.text.strip())
                if not dry_run:
                    root.remove(game)

        if missing_files:
            print(f"  ⚠️  Missing {len(missing_files)} ROM(s):")
            for path in missing_files:
                print(f"    - {path}")
            missing[system_folder.name] = missing_files
            if not dry_run:
                removed_entries[system_folder.name] = missing_files
                if do_backup:
                    backup_path = gamelist_path.with_suffix(".xml.bak")
                    shutil.copy2(gamelist_path, backup_path)
                    print(f"  🛟 Backup created at: {backup_path}")
                with open(gamelist_path, encoding="utf-8") as original:
                    full_content = original.read()
                start = full_content.find("<gameList>")
                end = full_content.find("</gameList>") + len("</gameList>")
                new_game_list = ET.tostring(root, encoding="unicode")
                updated_content = full_content[:start] + new_game_list + full_content[end:]
                with open(gamelist_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
        else:
            print(f"  ✅ All {len(games)} entries found")

    print("\n✅ Gamelist scan complete.")
    if skipped_systems:
        print(f"⚠️ Skipped systems: {', '.join(skipped_systems)}")
    if not missing:
        print("🎉 No missing ROMs found in any gamelists.")

    if not dry_run and removed_entries:
        print("\n🗑️  Removed entries:")
        for system, files in removed_entries.items():
            print(f"  {system}:")
            for path in files:
                print(f"    - {path}")

    if dry_run:
        print("\nℹ️  To actually remove missing entries, run this script with the --run flag:")
        print("    python validate_gamelists.py --run")
        print("\nℹ️  To run without creating .bak backups, use:")
        print("    python validate_gamelists.py --run --no-backup")

if __name__ == "__main__":
    dry_run = "--run" not in sys.argv
    do_backup = "--no-backup" not in sys.argv
    check_gamelists(dry_run=dry_run, do_backup=do_backup)
