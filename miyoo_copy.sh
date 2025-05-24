#!/bin/bash

SRC="/mnt/Stuff/ES-DE/ROMs"
DST="/mnt/g/roms"

# Source-to-destination system map
declare -A map=(
  [atari2600]=ATARI
  [atari5200]=FIFTYTWOHUNDRED
  [atari7800]=SEVENTYEIGHTHUNDRED
  [cps1]=CPS1
  [cps2]=CPS2
  [cps3]=CPS3
  [fbneo]=ARCADE
  [gamegear]=GG
  [gb]=GB
  [gba]=GBA
  [gbc]=GBC
  [genesis]=MD
  [gw]=GW
  [lynx]=LYNX
  [mastersystem]=MS
  [nds]=NDS
  [neocd]=NEOCD
  [neogeo]=NEOGEO
  [nes]=FC
  [ngp]=NGP
  [pcecd]=PCECD
  [pico]=PICO
  [ports]=PORTS
  [psx]=PS
  [scummvm]=SCUMMVM
  [sega32x]=THIRTYTWOX
  [segacd]=SEGACD
  [snes]=SFC
  [supergrafx]=SGFX
  [tg16]=PCE
  [ws]=WS
)

# Files to exclude from deletion
excludes=(
  "~Filter.miyoocmd"
  "~Refresh roms.miyoocmd"
)

# Build rsync exclude options
exclude_args=()
for pattern in "${excludes[@]}"; do
  exclude_args+=(--exclude="$pattern")
done

# Sync logic
for sys in "${!map[@]}"; do
  src_path="$SRC/$sys"
  dst_path="$DST/${map[$sys]}"

  if [[ ! -d "$src_path" ]] || [[ -z "$(find "$src_path" -type f -not -name '.*' -print -quit)" ]]; then
    echo "Skipping $sys (empty or missing)"
    continue
  fi

  echo "Syncing $src_path -> $dst_path"
  rsync -a --info=progress2 --size-only "${exclude_args[@]}" --delete "$src_path/" "$dst_path/"
done

# Rename gamelist.xml to miyoogamelist.xml after sync
echo "Renaming gamelist.xml to miyoogamelist.xml..."
for dst_dir in "$DST"/*; do
  if [[ -f "$dst_dir/gamelist.xml" ]]; then
    echo "Renaming $dst_dir/gamelist.xml -> $dst_dir/miyoogamelist.xml"
    mv -f "$dst_dir/gamelist.xml" "$dst_dir/miyoogamelist.xml"
  fi
done

# Clean up miyoogamelist.xml files
echo "Cleaning XML files in destination..."
for file in "$DST"/*/miyoogamelist.xml; do
  if [[ -f "$file" ]]; then
    echo "Cleaning $file"
    xmlstarlet ed -L -d '//game/*[not(self::path or self::name or self::image)]' "$file"
  fi
done
