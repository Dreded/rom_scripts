#!/bin/bash

# Configuration
LIST_DIR="../ROMs"        # Folder with .list files
DEST_DIR="../ROMs"        # Folder with destination subfolders containing symlinks

[[ "${LIST_DIR}" != */ ]] && LIST_DIR="${LIST_DIR}/"
[[ "${DEST_DIR}" != */ ]] && DEST_DIR="${DEST_DIR}/"

# Parse flags
REMOVE=false
for arg in "$@"; do
    if [[ "$arg" == "--remove" ]]; then
        REMOVE=true
    fi
done

shopt -s nullglob
for LISTFILE in "${LIST_DIR}"*.list; do
    BASENAME="$(basename "$LISTFILE")"
    SYSTEM_NAME="${BASENAME%.list}"
    TARGET_DIR="${DEST_DIR}${SYSTEM_NAME}/"

    if [[ ! -d "$TARGET_DIR" ]]; then
        echo "Skipping '$SYSTEM_NAME': target directory '$TARGET_DIR' does not exist."
        continue
    fi

    echo "Checking $SYSTEM_NAME..."

    # Build a set of expected filenames from the .list (skip first line)
    declare -A expected_files
    while IFS= read -r line || [[ -n "$line" ]]; do
        clean_file=$(echo "$line" | tr -d '\r')
        clean_file="${clean_file#"${clean_file%%[![:space:]]*}"}"
        clean_file="${clean_file%"${clean_file##*[![:space:]]}"}"
        [[ -z "$clean_file" ]] && continue
        expected_files["$clean_file"]=1
    done < <(tail -n +2 "$LISTFILE")

    # Find all symlinks or regular files in the destination folder
    while IFS= read -r filepath; do
        filename="$(basename "$filepath")"
        clean_filename="${filename#"${filename%%[![:space:]]*}"}"
        clean_filename="${clean_filename%"${clean_filename##*[![:space:]]}"}"

        # Ignore systeminfo.txt
        if [[ "$clean_filename" == "systeminfo.txt" ]]; then
            continue
        fi

        if [[ -z "${expected_files["$clean_filename"]}" ]]; then
            if $REMOVE; then
                echo "  Removing extra file: $filename"
                rm -f "$filepath"
            else
                echo "  Extra file in '$SYSTEM_NAME': $filename"
            fi
        fi
    done < <(find "$TARGET_DIR" -maxdepth 1 \( -type f -o -type l \))

    unset expected_files
done
shopt -u nullglob

if ! $REMOVE; then
    echo ""
    echo "Done checking. No files were removed."
    echo "To delete extra files, re-run this script with the --remove flag:"
    echo "  ./$(basename "$0") --remove"
fi
