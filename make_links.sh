#!/bin/bash

# Configuration - folders can be absolute or relative
LIST_DIR="../ROMs"       # Folder containing .list files
OUTPUT_DIR="../ROMs"     # Where target folders will be created (must exist unless --create-output is passed)

[[ "${LIST_DIR}" != */ ]] && LIST_DIR="${LIST_DIR}/"
[[ "${OUTPUT_DIR}" != */ ]] && OUTPUT_DIR="${OUTPUT_DIR}/"

# Parse optional flags
CREATE_OUTPUT=false
REMOVE_EXTRAS=false
REMOVED_FILES=()

for arg in "$@"; do
    case "$arg" in
        --create-output) CREATE_OUTPUT=true ;;
        --remove) REMOVE_EXTRAS=true ;;
    esac
done

# Check or create OUTPUT_DIR
if [[ ! -d "$OUTPUT_DIR" ]]; then
    if $CREATE_OUTPUT; then
        echo "Creating OUTPUT_DIR '$OUTPUT_DIR'..."
        mkdir -p "$OUTPUT_DIR" || {
            echo "Error: Could not create OUTPUT_DIR '$OUTPUT_DIR'. Aborting."
            exit 1
        }
    else
        echo "Error: OUTPUT_DIR '$OUTPUT_DIR' does not exist. Use --create-output to allow creation."
        exit 1
    fi
fi

# Track if any .list files were processed
found_lists=false

shopt -s nullglob
for FILELIST in "${LIST_DIR}"*.list; do
    found_lists=true
    echo "Processing $FILELIST..."

    if [[ ! -s "$FILELIST" ]]; then
        echo "  Warning: $FILELIST is empty. Skipping."
        continue
    fi

    SOURCE_DIR=$(head -n 1 "$FILELIST")
    TARGET_BASENAME="$(basename "$FILELIST")"
    TARGET_SUBFOLDER="${TARGET_BASENAME%.list}"
    TARGET_DIR="${OUTPUT_DIR}${TARGET_SUBFOLDER}/"

    [[ "${SOURCE_DIR}" != */ ]] && SOURCE_DIR="${SOURCE_DIR}/"

    if [[ ! -d "$SOURCE_DIR" ]]; then
        echo "  Error: Source directory '$SOURCE_DIR' does not exist. Skipping."
        continue
    fi

    any_linked=false
    declare -A valid_files

    while IFS= read -r f; do
        clean_file=$(echo "$f" | tr -d '\r')
        clean_file="${clean_file#"${clean_file%%[![:space:]]*}"}"
        clean_file="${clean_file%"${clean_file##*[![:space:]]}"}"
        [[ -z "$clean_file" ]] && continue
        valid_files["$clean_file"]=1

        if [[ -e "$SOURCE_DIR$clean_file" ]]; then
            if ! $any_linked; then
                if ! mkdir -p "$TARGET_DIR"; then
                    echo "  Error: Failed to create target directory '$TARGET_DIR'. Skipping."
                    continue 2
                fi
                echo "  Linking files into $TARGET_DIR"
                any_linked=true
            fi
            ln -sf "$SOURCE_DIR$clean_file" "$TARGET_DIR"
        else
            echo "  Warning: '$SOURCE_DIR$clean_file' does not exist. Skipping."
        fi
    done < <(tail -n +2 "$FILELIST")

    if $any_linked; then
        echo "  Done linking $SOURCE_DIR to $TARGET_DIR"
    else
        echo "  No valid files to link for $FILELIST — target folder not created."
    fi

    # Remove unlisted extras if --remove was passed
    if $REMOVE_EXTRAS && [[ -d "$TARGET_DIR" ]]; then
        echo "  Checking for unlisted extras to remove..."
        while IFS= read -r filepath; do
            filename="$(basename "$filepath")"
            clean_filename="${filename#"${filename%%[![:space:]]*}"}"
            clean_filename="${clean_filename%"${clean_filename##*[![:space:]]}"}"

            # Skip systeminfo.txt
            if [[ "$clean_filename" == "systeminfo.txt" ]]; then
                continue
            fi

            if [[ -z "${valid_files["$clean_filename"]}" ]]; then
                relative_path="${TARGET_SUBFOLDER}/${clean_filename}"
                echo "    Removing extra: $relative_path"
                rm -f "$filepath"
                REMOVED_FILES+=("$relative_path")
            fi
        done < <(find "$TARGET_DIR" -maxdepth 1 \( -type f -o -type l \))
    fi

    unset valid_files
done
shopt -u nullglob

if $REMOVE_EXTRAS && [[ ${#REMOVED_FILES[@]} -gt 0 ]]; then
    echo ""
    echo "Removed..."
    for f in "${REMOVED_FILES[@]}"; do
        echo "    $f"
    done
fi

if ! $found_lists; then
    echo "No .list files found in '$LIST_DIR'. Nothing to process."
    exit 1
fi

if ! $REMOVE_EXTRAS; then
    echo ""
    echo "Done linking. No files were removed."
    echo "To delete games not in the .list files, re-run this script with --remove:"
    echo "  ./$(basename "$0") --remove"
fi
