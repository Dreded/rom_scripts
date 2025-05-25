#!/usr/bin/env python3

import os
import shutil
import argparse
import re
from xml.etree import ElementTree as ET

PSX_DIR = "/mnt/Stuff/ES-DE/ROMs/psx"
GAMELIST = os.path.join(PSX_DIR, "gamelist.xml")
IMGS_DIR = os.path.join(PSX_DIR, "Imgs")


def restore_backups():
    print("🧪 Test mode: Restoring backups and removing .m3u files...")
    if os.path.exists(GAMELIST + ".bak"):
        print("🛠️  Restoring gamelist.xml from backup...")
        shutil.copyfile(GAMELIST + ".bak", GAMELIST)

    imgs_backup = IMGS_DIR + ".bak"
    if os.path.exists(imgs_backup):
        print("🛠️  Restoring Imgs/ from Imgs.bak...")
        shutil.rmtree(IMGS_DIR)
        shutil.copytree(imgs_backup, IMGS_DIR)

    print("🧼 Removing existing .m3u files for testing...")
    for file in os.listdir(PSX_DIR):
        if file.endswith(".m3u"):
            os.remove(os.path.join(PSX_DIR, file))


def load_gamelist():
    tree = ET.parse(GAMELIST)
    root = tree.getroot()
    return tree, root


def find_game_by_path(root, path):
    for game in root.findall("game"):
        if game.findtext("path") == path:
            return game
    return None


def remove_game_by_path(root, path):
    for game in root.findall("game"):
        if game.findtext("path") == path:
            root.remove(game)
            return True
    return False


def update_image_path(game, new_path):
    image = game.find("image")
    if image is not None:
        image.text = new_path
    else:
        image = ET.SubElement(game, "image")
        image.text = new_path


def main(test_mode=False):
    os.chdir(PSX_DIR)
    print("\n🎮 Converting multi-disc games to .m3u in gamelist.xml...\n")

    shutil.copyfile(GAMELIST, GAMELIST + ".bak")
    print(f"📝 Backup created: {GAMELIST}.bak")

    tree, root = load_gamelist()
    updated = False

    for filename in os.listdir("."):
        if not re.search(r"\(Disc 1\).*\.chd$", filename, re.IGNORECASE):
            continue

        base_name = re.sub(r" \(Disc 1\)( \(Rev \d+\))?\.chd$", "", filename, flags=re.IGNORECASE)
        m3u_file = f"{base_name}.m3u"
        m3u_path = f"./{m3u_file}"
        disc1_path = f"./{filename}"

        print(f"\n🕹️  Processing: \033[1m{base_name}\033[0m")
        print("──────────────────────────────────────────────")

        m3u_in_gamelist = find_game_by_path(root, m3u_path) is not None
        m3u_file_exists = os.path.exists(m3u_file)

        if m3u_in_gamelist and m3u_file_exists:
            print("⏩ .m3u already in gamelist and file exists — skipping")
        else:
            if not m3u_file_exists:
                chds = sorted([f for f in os.listdir(".") if re.match(re.escape(base_name) + r" \(Disc [1-9]\).*\.chd", f)])
                print(f"📦 Creating {m3u_file} with:")
                with open(m3u_file, "w") as f:
                    for chd in chds:
                        print(f"   • {chd}")
                        f.write(f"{chd}\n")
            else:
                print(f"📁 {m3u_file} already exists — skipping creation")

            if not m3u_in_gamelist:
                game = find_game_by_path(root, disc1_path)
                if game:
                    game.find("path").text = m3u_path
                    updated = True
                    print("🛠️  Updated <path> in gamelist.xml")

        game = find_game_by_path(root, m3u_path)
        if game and game.find("image") is not None:
            image_path = game.find("image").text.strip()
            old_image = os.path.normpath(os.path.join(PSX_DIR, image_path.strip("./")))
            new_image_rel = f"./Imgs/{base_name}.png"
            new_image_abs = os.path.normpath(os.path.join(PSX_DIR, new_image_rel.strip("./")))

            if os.path.exists(old_image) and old_image != new_image_abs:
                print(f"🖼️  Renaming image: {image_path} → {new_image_rel}")
                os.rename(old_image, new_image_abs)
                update_image_path(game, new_image_rel)
                updated = True
            elif os.path.exists(old_image):
                print(f"ℹ️  Image already correctly named: {new_image_rel}")

        if remove_game_by_path(root, disc1_path):
            print(f"❌ Removing duplicate Disc 1 entry: {disc1_path}")
            updated = True
        else:
            print(f"ℹ️  No <game> entry found for: {disc1_path} — skipping")

        current_image = None
        game = find_game_by_path(root, m3u_path)
        if game and game.find("image") is not None:
            current_image = game.find("image").text

        for f in os.listdir("."):
            if re.match(re.escape(base_name) + r" \(Disc [2-9]\).*\.chd", f):
                disc_path = f"./{f}"
                if remove_game_by_path(root, disc_path):
                    print(f"❌ Removing extra disc entry: {f}")
                    updated = True
                else:
                    print(f"ℹ️  No <game> entry found for: {f} — skipping")

                img_path = f"./Imgs/{f[:-4]}.png"
                if os.path.exists(img_path):
                    if img_path == current_image:
                        print(f"🛑 Not deleting image (used by .m3u): {img_path}")
                    else:
                        print(f"🗑️  Deleting image: {img_path}")
                        os.remove(img_path)

    if updated:
        tree.write(GAMELIST, encoding="utf-8", xml_declaration=True)
    print("\n✅ All multi-disc conversions complete.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Restore backups and remove .m3u files for testing")
    args = parser.parse_args()

    if args.test:
        restore_backups()
    main(test_mode=args.test)
