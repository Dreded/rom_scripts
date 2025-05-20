#!/bin/bash

# === USER VARIABLES ===
ROMS_DIR="/mnt/user/Stuff/ES-DE/ROMs"
MEDIA_DIR="/mnt/user/Stuff/ES-DE/ES-DE/downloaded_media"

format_bytes_align() {
  local bytes=$1
  if (( bytes >= 1073741824 )); then
    awk -v b="$bytes" 'BEGIN { printf "%.2f G", b / (1024*1024*1024) }'
  elif (( bytes >= 1048576 )); then
    awk -v b="$bytes" 'BEGIN { printf "%.0f M", b / (1024*1024) }'
  else
    awk -v b="$bytes" 'BEGIN { printf "%.0f K", b / 1024 }'
  fi
}

# Set up total counters (in bytes)
rom_total=0
media_total=0
image_total=0
video_total=0
manual_total=0
sort_field="none"
basic_output=0
declare -a system_filters=()

# Argument parsing
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sort=rom|--sort=r)   sort_field="rom" ;;
    --sort=media|--sort=m) sort_field="media" ;;
    --sort=total|--sort=t) sort_field="total" ;;
    --sort)                sort_field="total" ;;
    --basic)               basic_output=1 ;;
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
      echo "Usage: $0 [options]"
      echo "  --rom-folder              Path to ROM root directory"
      echo "  --media-folder            Path to media root directory"
      echo "  --sort[=rom|media|total]  Sort output by size field"
      echo "  --basic                   Output colon-separated values for scripting"
      echo "  --system=nes,snes         Comma-separated list of systems"
      echo "  --help                    Show this help message"
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
  media_kb_full=$(du -sL "$media_dir" 2>/dev/null | awk '{print $1}')
  manuals_kb=$(du -sL "$media_dir/manuals" 2>/dev/null | awk '{print $1}')
  videos_kb=$(du -sL "$media_dir/videos" 2>/dev/null | awk '{print $1}')
  media_kb_images=$((media_kb_full - manuals_kb - videos_kb))

  rom_kb=${rom_kb:-0}
  media_kb_full=${media_kb_full:-0}
  manuals_kb=${manuals_kb:-0}
  videos_kb=${videos_kb:-0}
  media_kb_images=$(( media_kb_images >= 0 ? media_kb_images : 0 ))

  if [[ $rom_kb -le 4 && ${#system_filters[@]} -eq 0 ]]; then
    continue
  fi

  if [[ $rom_kb -le 4 && ${#system_filters[@]} -gt 0 ]]; then
    rom_bytes=0
  else
    rom_bytes=$((rom_kb * 1024))
  fi

  media_bytes=$((media_kb_full * 1024))
  image_bytes=$((media_kb_images * 1024))
  video_bytes=$((videos_kb * 1024))
  manual_bytes=$((manuals_kb * 1024))
  total_bytes=$((rom_bytes + media_bytes))

  rom_total=$((rom_total + rom_bytes))
  media_total=$((media_total + media_bytes))
  image_total=$((image_total + image_bytes))
  video_total=$((video_total + video_bytes))
  manual_total=$((manual_total + manual_bytes))

  rom_human=$(format_bytes_align "$rom_bytes")
  image_human=$(format_bytes_align "$image_bytes")
  video_human=$(format_bytes_align "$video_bytes")
  manual_human=$(format_bytes_align "$manual_bytes")
  total_human=$(format_bytes_align "$total_bytes")

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$dirname" "$rom_human" "$image_human" "$video_human" "$manual_human" "$total_human" >> "$tempfile"
done

[[ $basic_output -eq 0 ]] && echo -ne "                                         \r"

# Output
if [[ $basic_output -eq 1 ]]; then
  awk -F'\t' '{ printf "%s:%s:%s:%s:%s:%s\n", $1, $2, $3, $4, $5, $6 }' "$tempfile"
else
  echo
  printf "%-15s %-10s %-10s %-10s %-10s %-12s\n" "System" "Roms" "Images" "Videos" "Manuals" "Total Size"
  printf "%-15s %-10s %-10s %-10s %-10s %-12s\n" "--------------" "--------" "--------" "--------" "--------" "------------"

  cat "$tempfile" | awk -F'\t' '{ printf "%-15s %8s   %8s   %8s   %8s   %12s\n", $1, $2, $3, $4, $5, $6 }'

  if [[ ${#system_filters[@]} -ne 1 ]]; then
    echo
    printf "%-20s %s\n" "Roms:"              "$(format_bytes_align "$rom_total")"
    printf "%-20s %s\n" "Images:"            "$(format_bytes_align "$image_total")"
    printf "%-20s %s\n" "Videos:"            "$(format_bytes_align "$video_total")"
    printf "%-20s %s\n" "Manuals:"           "$(format_bytes_align "$manual_total")"
    printf "%-20s %s\n" "All Media:"         "$(format_bytes_align "$media_total")"
    printf "%-20s %s\n" "Roms + Images:"     "$(format_bytes_align "$((rom_total + image_total))")"
    printf "%-20s %s\n" "Roms + All Media:"  "$(format_bytes_align "$((rom_total + media_total))")"
    echo
  fi

fi

# Clean up
rm -f "$tempfile"
