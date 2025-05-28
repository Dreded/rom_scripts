#!/usr/bin/env python3

import os
import shutil
import subprocess
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom

roms_dir = r"Y:\ES-DE\ROMs"
media_src_base = r"Y:\ES-DE\ES-DE\downloaded_media"
gamelist_src_base = r"Y:\ES-DE\ES-DE\gamelists"
media_dst_base = r"F:\\"  # Avoid raw string issue

parser = argparse.ArgumentParser(description="Sync images, marquees, videos, and update gamelist.xml for each system.")
parser.add_argument("--run", action="store_true", help="Perform the actual copy. Default is dry run.")
parser.add_argument("--quiet", action="store_true", help="Suppress robocopy output (only effective with --run).")
args = parser.parse_args()

systems = [d for d in os.listdir(roms_dir) if os.path.isdir(os.path.join(roms_dir, d))]

if not systems:
    print("⚠️  No systems found.")
    exit(1)

def update_gamelist(gamelist_path):
    system = os.path.basename(os.path.dirname(gamelist_path))
    if not os.path.isfile(gamelist_path):
        return

    try:
        with open(gamelist_path, "r", encoding="utf-8") as f:
            content = f.read()

        start = content.find("<gameList>")
        end = content.rfind("</gameList>") + len("</gameList>")
        if start == -1 or end == -1:
            print(f"❌ Skipping {system}: <gameList> section not found.")
            return

        xml_snippet = content[start:end]
        root = ET.fromstring(xml_snippet)
        tree = ET.ElementTree(root)
    except ET.ParseError as e:
        print(f"❌ Skipping {system}: invalid XML — {e}")
        return

    # Track missing media files
    missing = {"image": [], "marquee": [], "video": []}

    system_path = os.path.dirname(gamelist_path)

    for game in root.findall("game"):
        path_elem = game.find("path")
        if path_elem is None or not path_elem.text:
            continue

        rom_filename = os.path.basename(path_elem.text.strip())
        rom_basename = os.path.splitext(rom_filename)[0]

        def set_or_replace(tag, value):
            tag_elem = game.find(tag)
            if tag_elem is None:
                tag_elem = ET.SubElement(game, tag)
            tag_elem.text = value

        # Build media paths
        image_rel = f"./images/{rom_basename}.png"
        video_rel = f"./videos/{rom_basename}.mp4"
        marquee_rel = f"./marquees/{rom_basename}.png"

        # Update XML
        set_or_replace("image", image_rel)
        set_or_replace("marquee", marquee_rel)
        set_or_replace("video", video_rel)

        # Check file existence
        if not os.path.isfile(os.path.join(system_path, image_rel[2:])):
            missing["image"].append(image_rel)
        if not os.path.isfile(os.path.join(system_path, marquee_rel[2:])):
            missing["marquee"].append(marquee_rel)
        if not os.path.isfile(os.path.join(system_path, video_rel[2:])):
            missing["video"].append(video_rel)

    # Format and save XML
    rough_string = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")
    cleaned_xml = "\n".join(line for line in pretty_xml.splitlines() if line.strip())

    with open(gamelist_path, "w", encoding="utf-8") as f:
        f.write(cleaned_xml)

    print(f"📝 Updated gamelist.xml for {system}")

    # Report missing files
    total_missing = sum(len(v) for v in missing.values())
    if total_missing > 0:
        print(f"⚠️  Missing media in {system}:")
        for kind, items in missing.items():
            if items:
                print(f"  {kind.capitalize()}:")
                for path in items:
                    print(f"    - {path}")


for system in sorted(systems):
    try:
        print(f"\n🔎 Processing: {system}")
        dest_system_folder = os.path.join(media_dst_base, system)
        if not os.path.isdir(dest_system_folder):
            print(f"⚠️  Skipping '{system}' — destination folder does not exist.")
            continue

        # Define source folders
        miximages_src = os.path.join(media_src_base, system, "miximages")
        videos_src = os.path.join(media_src_base, system, "videos")
        marquees_src = os.path.join(media_src_base, system, "marquees")

        # Define destination folders
        images_dst = os.path.join(dest_system_folder, "images")
        videos_dst = os.path.join(dest_system_folder, "videos")
        marquees_dst = os.path.join(dest_system_folder, "marquees")

        # Copy gamelist.xml
        gamelist_src = os.path.join(gamelist_src_base, system, "gamelist.xml")
        gamelist_dst = os.path.join(dest_system_folder, "gamelist.xml")

        if os.path.isfile(gamelist_src):
            print(f"📄 Copying gamelist.xml for: {system}")
            if args.run:
                shutil.copy2(gamelist_src, gamelist_dst)

        # Robocopy media folders
        for label, src_folder, dst_folder in [
            ("miximages → images", miximages_src, images_dst),
            ("videos", videos_src, videos_dst),
            ("marquees", marquees_src, marquees_dst),
        ]:
            if os.path.isdir(src_folder):
                print(f"📁 {'[DRY RUN] ' if not args.run else ''}Copying {label} for: {system}")
                if args.run:
                    robocopy_cmd = [
                        "robocopy",
                        src_folder,
                        dst_folder,
                        "/E",     # Copy all subdirectories, including empty ones
                        "/NJH",   # No job header
                        "/NP",    # Suppress progress per file
                    ]
                    if args.quiet:
                        subprocess.run(robocopy_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.run(robocopy_cmd, capture_output=False, text=True)


        # Update gamelist.xml with media tags
        if args.run and os.path.isfile(gamelist_dst):
            update_gamelist(gamelist_dst)

    except Exception as e:
        print(f"💥 Exception while processing {system}: {e}")
        import traceback
        traceback.print_exc()

if not args.run:
    print("\nℹ️  Dry run complete. Use `--run` to perform the actual copy.")
