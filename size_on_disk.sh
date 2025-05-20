#!/bin/bash

# === USER VARIABLES ===
ROMS_DIR="/mnt/user/Stuff/ES-DE/ROMs"
MEDIA_DIR="/mnt/user/Stuff/ES-DE/ES-DE/downloaded_media"

format_bytes_align() {
  local bytes=$1
  if (( bytes >= 1073741824  )); then
    awk -v b="$bytes" 'BEGIN { printf "%7.2f G", b / (1024*1024*1024) }'
  elif (( bytes >= 1048576 )); then
    awk -v b="$bytes" 'BEGIN { printf "%7.0f M", b / (1024*1024) }'
  else
    awk -v b="$bytes" 'BEGIN { printf "%7.0f K", b / 1024 }'
  fi
}

# Set up total counters (in bytes)
rom_total=0
media_total=0
sort_field="none"
basic_output=0
declare -a system_filters=()

# Argument parsing
# Support short sort aliases: --sort-r, --sort-m, --sort-t
# Also allow overriding ROM and media root paths
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sort=rom|--sort=r)   sort_field="rom" ;;
    --sort=media|--sort=m) sort_field="media" ;;
    --sort=total|--sort=t) sort_field="total" ;;
    --sort)       sort_field="total" ;;
    --basic)      basic_output=1 ;;
    --system)
      shift
      IFS=',' read -ra system_filters <<< "$1"
      ;;
    --system=*)
      IFS=',' read -ra system_filters <<< "${1#*=}"
      ;;
    --rom-folder)
      shift
      ROMS_DIR="$1"
      ;;
    --rom-folder=*)
      ROMS_DIR="${1#*=}"
      ;;
    --media-folder)
      shift
      MEDIA_DIR="$1"
      ;;
    --media-folder=*)
      MEDIA_DIR="${1#*=}"
      ;;

    --help|-h)
      echo "Usage: $0 [--sort[=rom|media|total]] [--basic] [-s <system1,system2>] [--system=nes,snes] [--rom-folder path] [--media-folder path]"
      echo "  --rom-folder     Path to ROM root directory"
      echo "  --media-folder   Path to media root directory"
      echo "  --sort           Default to sorting by total size"
      echo "  --sort=rom       Sort by ROM size (also --sort=r)"
      echo "  --sort=media     Sort by media size (also --sort=m)"
      echo "  --sort=total     Sort by total size (also --sort=t)"
      echo "  --basic          Output basic colon-separated data (suitable for piping to a file)"
      echo "  --system         Comma-separated list of systems to process"
      echo "  --help           Show this message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Try '$0 --help' for usage."
      exit 1
      ;;
  esac
  shift
done

# Create a temporary file to collect sortable data
tempfile=$(mktemp)

# Initial status message
[[ $basic_output -eq 0 ]] && echo -ne "Processing...\r"

# Build directory list
if [[ ${#system_filters[@]} -gt 0 ]]; then
  rom_dirs=()
  for sys in "${system_filters[@]}"; do
    rom_dirs+=("$ROMS_DIR/$sys/")
  done
else
  rom_dirs=("$ROMS_DIR"/*/)
fi

# Loop through each ROM system directory
for d in "${rom_dirs[@]}"; do
  if [[ ! -d "$d" ]]; then
    echo -e "[31mWarning:[0m Directory not found: $d" >&2
    continue
  fi

  dirname=$(basename "$d")
  media_dir="$MEDIA_DIR/$dirname"

  [[ $basic_output -eq 0 ]] && echo -ne "Processing: $dirname         \r"

  rom_kb=$(du -sL "$d" 2>/dev/null | awk '{print $1}')
  media_kb=$(du -sL "$media_dir" 2>/dev/null | awk '{print $1}')
  media_kb=${media_kb:-0}

  # Only skip small folders (≤ 4KB) if not manually specified
  if [[ $rom_kb -le 4 && ${#system_filters[@]} -eq 0 ]]; then
    continue
  fi

  if [[ $rom_kb -le 4 && ${#system_filters[@]} -gt 0 ]]; then
    rom_bytes=0
  else
    rom_bytes=$((rom_kb * 1024))
  fi

  media_bytes=$((media_kb * 1024))
  total_bytes=$((rom_bytes + media_bytes))

  rom_total=$((rom_total + rom_bytes))
  media_total=$((media_total + media_bytes))

  rom_human=$(format_bytes_align "$rom_bytes")
  media_human=$(format_bytes_align "$media_bytes")
  total_human=$(format_bytes_align "$total_bytes")

  printf "%d\t%d\t%d\t%s\t%s\t%s\t%s\n" "$rom_bytes" "$media_bytes" "$total_bytes" "$dirname" "$rom_human" "$media_human" "$total_human" >> "$tempfile"
done

[[ $basic_output -eq 0 ]] && echo -ne "                                         \r"

# Output
if [[ $basic_output -eq 1 ]]; then
  awk -F'\t' '{ printf "%s:%d:%d:%d\n", $4, $1 / 1024, $2 / 1024, $3 / 1024 }' "$tempfile"
  if [[ ${#system_filters[@]} -ne 1 ]]; then
    rom_kb_total=$((rom_total / 1024))
    media_kb_total=$((media_total / 1024))
    total_kb_combined=$(((rom_total + media_total) / 1024))
    echo "TOTAL:$rom_kb_total:$media_kb_total:$total_kb_combined"
  fi
else
  echo
  printf "%-15s %-12s %-12s %-12s\n" "System" "Rom Size" "Media Size" "Total Size"
  printf "%-15s %-12s %-12s %-12s\n" "--------------" "----------" "----------" "----------"

  case "$sort_field" in
    rom|r)
      sort -nr -k1 "$tempfile"
      ;;
    media|m)
      sort -nr -k2 "$tempfile"
      ;;
    total|t)
      sort -nr -k3 "$tempfile"
      ;;
    *)
      cat "$tempfile"
      ;;
  esac | awk -F'\t' '{ printf "%-15s %-12s %-12s %-12s\n", $4, $5, $6, $7 }'

  if [[ ${#system_filters[@]} -ne 1 ]]; then
    echo
    printf "%-15s %s\n" "Total ROMs:"     "$(format_bytes_align "$rom_total")"
    printf "%-15s %s\n" "Total Media:"    "$(format_bytes_align "$media_total")"
    printf "%-15s %s\n" "Combined Total:" "$(format_bytes_align "$((rom_total + media_total))")"
  fi
  echo
fi

# Clean up
rm -f "$tempfile"
