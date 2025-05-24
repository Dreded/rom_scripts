#!/bin/bash

PSX_DIR="/mnt/Stuff/ES-DE/ROMs/psx"
GAMELIST="$PSX_DIR/gamelist.xml"
IMGS_DIR="$PSX_DIR/Imgs"

# Parse --test flag
if [[ "$1" == "--test" ]]; then
  echo "🧪 Test mode: Restoring backups and removing .m3u files..."

  if [[ -f "$GAMELIST.bak" ]]; then
    echo "🛠️  Restoring gamelist.xml from backup..."
    cp -f "$GAMELIST.bak" "$GAMELIST"
  fi

  if [[ -d "$PSX_DIR/Imgs.bak" ]]; then
    echo "🛠️  Restoring Imgs/ from Imgs.bak..."
    rsync -a --delete "$PSX_DIR/Imgs.bak/" "$IMGS_DIR/"
  fi

  echo "🧼 Removing existing .m3u files for testing..."
  rm -f "$PSX_DIR"/*.m3u
fi

cd "$PSX_DIR" || { echo "❌ Cannot access $PSX_DIR"; exit 1; }

echo -e "\n🎮 Converting multi-disc games to .m3u in gamelist.xml...\n"

# Backup current gamelist
cp "$GAMELIST" "$GAMELIST.bak"
echo "📝 Backup created: $GAMELIST.bak"

# Process all Disc 1 .chd files
find . -maxdepth 1 -type f -iname "*\(Disc 1\)*.chd" | while read -r disc1_path; do
  disc1_file="${disc1_path#./}"
  base_name=$(echo "$disc1_file" | sed -E 's/ \(Disc 1\)( \(Rev [0-9]+\))?\.chd$//')
  m3u_file="$base_name.m3u"
  m3u_path="./$m3u_file"

  echo -e "\n🕹️  Processing: \033[1m$base_name\033[0m"
  echo "──────────────────────────────────────────────"

  if grep -Fq "$m3u_path" "$GAMELIST"; then
    echo "⏩ .m3u already in gamelist — skipping update/creation"

    # Make sure the image exists for the .m3u entry
    base_img="./Imgs/$base_name.png"
    if [[ ! -f "$base_img" ]]; then
      echo "🔍 .m3u image $base_img is missing — searching for a disc image to rename..."
      for f in "$IMGS_DIR"/"$base_name (Disc "[1-9]")"*.png; do
        if [[ -f "$f" ]]; then
          echo "🖼️  Renaming fallback disc image: $(basename "$f") → $(basename "$base_img")"
          mv -f "$f" "$base_img"
          xmlstarlet ed -L -u "//game[path=\"$m3u_path\"]/image" -v "$base_img" "$GAMELIST"
          break
        fi
      done
    fi
  else
    if [[ ! -f "$m3u_file" ]]; then
      echo "📦 Creating $m3u_file with:"
      find . -maxdepth 1 -type f -iname "$base_name (Disc [1-9])*\.chd" | sort -V | sed 's|^\./||' | tee "$m3u_file" | sed 's/^/   • /'
    else
      echo "📁 $m3u_file already exists — skipping creation"
    fi

    xmlstarlet ed -L -u "//game[path=\"./$disc1_file\"]/path" -v "$m3u_path" "$GAMELIST"
    echo "🛠️  Updated <path> in gamelist.xml"

    image_path=$(xmlstarlet sel -t -v "//game[path=\"$m3u_path\"]/image" "$GAMELIST")
    old_image="$PSX_DIR/${image_path#./}"
    new_image="./Imgs/$base_name.png"

    if [[ -f "$old_image" ]]; then
      echo "🖼️  Renaming image: $image_path → $new_image"
      mv -f "$old_image" "$PSX_DIR/${new_image#./}"
      xmlstarlet ed -L -u "//game[path=\"$m3u_path\"]/image" -v "$new_image" "$GAMELIST"
      echo "🛠️  Updated <image> in gamelist.xml"
    fi
  fi

  # Remove Disc 1 entry if still present
  if xmlstarlet sel -t -v "//game[path=\"./$disc1_file\"]" "$GAMELIST" | grep -q .; then
    echo "❌ Removing duplicate Disc 1 entry: $disc1_file"
    xmlstarlet ed -L -d "//game[path=\"./$disc1_file\"]" "$GAMELIST"
  else
    echo "ℹ️  No <game> entry found for: $disc1_file — skipping"
  fi

  current_image=$(xmlstarlet sel -t -v "//game[path=\"$m3u_path\"]/image" "$GAMELIST")

  find . -maxdepth 1 -type f -iname "$base_name (Disc [2-9])*\.chd" | while read -r extra_disc; do
    disc_file="${extra_disc#./}"

    if xmlstarlet sel -t -v "//game[path=\"./$disc_file\"]" "$GAMELIST" | grep -q .; then
      echo "❌ Removing extra disc entry: $disc_file"
      xmlstarlet ed -L -d "//game[path=\"./$disc_file\"]" "$GAMELIST"
    else
      echo "ℹ️  No <game> entry found for: $disc_file — skipping"
    fi

    img="./Imgs/${disc_file%.chd}.png"
    if [[ -f "$img" ]]; then
      if [[ "$img" == "$current_image" ]]; then
        echo "🛑 Not deleting image (used by .m3u): $img"
      else
        echo "🗑️  Deleting image: $img"
        rm -f "$img"
      fi
    fi
  done
done

echo -e "\n✅ All multi-disc conversions complete.\n"
