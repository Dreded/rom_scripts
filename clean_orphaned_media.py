#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Root folders
ROMS_DIR = Path("D:/ROMs")
MEDIA_DIR = Path("D:/ES-DE/downloaded_media")

# Extensions of media to check (adjust as needed)
MEDIA_EXTENSIONS = [".png", ".jpg", ".jpeg", ".mp4", ".webp"]

deleted = []
kept = 0
skipped_systems = []


def get_rom_basenames(system_path):
    return {rom.stem for rom in system_path.rglob("*") if rom.is_file()}


def clean_orphaned_media(dry_run=True):
    print(f"\n🧹 Scanning for orphaned media... ({'dry run' if dry_run else 'real run'})")
    if dry_run:
        print("ℹ️  No files will be deleted. Run with --run to actually remove orphaned media.")

    for system_folder in MEDIA_DIR.iterdir():
        if not system_folder.is_dir():
            continue

        roms_for_system = ROMS_DIR / system_folder.name
        if not roms_for_system.exists():
            print(f"⚠️  Skipping '{system_folder.name}' — no matching ROM folder found.")
            skipped_systems.append(system_folder.name)
            continue

        print(f"🔍 Checking '{system_folder.name}'...")
        valid_basenames = get_rom_basenames(roms_for_system)
        removed = 0

        for subdir, _, files in os.walk(system_folder):
            for file in files:
                file_path = Path(subdir) / file
                if file_path.suffix.lower() in MEDIA_EXTENSIONS:
                    if file_path.stem not in valid_basenames:
                        try:
                            if not dry_run:
                                file_path.unlink()
                            deleted.append(str(file_path))
                            removed += 1
                        except Exception as e:
                            print(f"❌ Could not delete {file_path}: {e}")
                    else:
                        global kept
                        kept += 1

        if removed:
            print(f"  🗑️ {'Would remove' if dry_run else 'Removed'} {removed} orphaned files")
        else:
            print(f"  ✅ No orphaned media found")

    print("\n✅ Finished cleaning.")
    print(f"🧾 Total deleted: {len(deleted)}")
    print(f"📦 Total kept: {kept}")
    if skipped_systems:
        print(f"⚠️ Skipped systems: {', '.join(skipped_systems)}")
    if deleted:
        print("\n🗂️ Files marked for deletion:" if dry_run else "\n🗂️ Deleted files:")
        for path in deleted:
            print(f"  {path}")
    
    if dry_run:
        print("ℹ️  No files will be deleted. Run with --run to actually remove orphaned media.")


if __name__ == "__main__":
    dry_run = True if "--run" not in sys.argv else False
    clean_orphaned_media(dry_run=dry_run)
