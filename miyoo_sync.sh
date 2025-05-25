#!/bin/bash

SRC="/mnt/Stuff/ES-DE/ROMs"
DST="/mnt/g/roms"

declare -A map=(
  [atari2600]=ATARI [atari5200]=FIFTYTWOHUNDRED [atari7800]=SEVENTYEIGHTHUNDRED
  [cps1]=CPS1 [cps2]=CPS2 [cps3]=CPS3 [fbneo]=ARCADE [gamegear]=GG
  [gb]=GB [gba]=GBA [gbc]=GBC [genesis]=MD [gw]=GW [lynx]=LYNX [mastersystem]=MS
  [nds]=NDS [neocd]=NEOCD [neogeo]=NEOGEO [nes]=FC [ngp]=NGP [pcecd]=PCECD
  [pico]=PICO [ports]=PORTS [psx]=PS [scummvm]=SCUMMVM [sega32x]=THIRTYTWOX
  [segacd]=SEGACD [snes]=SFC [supergrafx]=SGFX [tg16]=PCE [ws]=WS
)

excludes=( "~Filter.miyoocmd" "~Refresh roms.miyoocmd" )
exclude_args=()
for pattern in "${excludes[@]}"; do
  exclude_args+=(--exclude="$pattern")
done

echo -e "\n📂 Starting sync from $SRC to $DST\n"

# Parse command-line args or use sorted default
if [[ $# -gt 0 ]]; then
  targets=("$@")
  echo -e "🎯 Limiting sync to: ${targets[*]}"
else
  targets=($(printf "%s\n" "${!map[@]}" | sort))
fi

for sys in "${targets[@]}"; do
  if [[ -z "${map[$sys]}" ]]; then
    echo -e "\n❌ Unknown system: $sys — skipping"
    continue
  fi

  src_path="$SRC/$sys"
  dst_path="$DST/${map[$sys]}"

  echo -e "\n🕹️ \033[1mSystem:\033[0m $sys → ${map[$sys]}"
  echo "──────────────────────────────────────────────"

  if [[ ! -d "$src_path" ]] || [[ -z "$(find "$src_path" -type f -not -name '.*' -print -quit)" ]]; then
    echo "⚠️  Skipping: Source is empty or missing"
    continue
  fi

  echo -ne "🚚 Syncing files...\r"
  rsync -a --info=progress2 --size-only "${exclude_args[@]}" --delete "$src_path/" "$dst_path/"

  # Clear rsync's final progress line
  tput cuu1 && tput el
  echo "✅ Sync complete: $src_path → $dst_path"

  # Rename gamelist.xml to miyoogamelist.xml
  gamelist="$dst_path/gamelist.xml"
  if [[ -f "$gamelist" ]]; then
    echo "📄 Renaming: $gamelist → miyoogamelist.xml"
    mv -f "$gamelist" "$dst_path/miyoogamelist.xml"
  fi

  # Clean miyoogamelist.xml
  miyoofile="$dst_path/miyoogamelist.xml"
  if [[ -f "$miyoofile" ]]; then
    echo "🧼 Cleaning: $miyoofile"
    xmlstarlet ed -L -d '//game/*[not(self::path or self::name or self::image)]' "$miyoofile"
  fi
done

echo -e "\n✅ All specified systems processed.\n"
