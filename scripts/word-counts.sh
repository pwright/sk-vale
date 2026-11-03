#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Show word count distribution across generated assemblies and modules.
Includes abstract word counts extracted from [role="_abstract"] blocks.

Options:
  --list        Show per-file word counts (sorted descending)
  -h, --help    Show this help message
EOF
    exit 0
}

SHOW_LIST=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --list)    SHOW_LIST=true; shift ;;
        -h|--help) usage ;;
        *)         echo "Unknown option: $1"; usage ;;
    esac
done

abstract_words() {
    local file="$1"
    local in_abstract=false
    local words=0
    while IFS= read -r line; do
        if [[ "$line" == *'role="_abstract"'* ]]; then
            in_abstract=true
            continue
        fi
        if $in_abstract; then
            if [[ -z "${line// /}" ]]; then
                break
            fi
            words=$((words + $(echo "$line" | wc -w)))
        fi
    done < "$file"
    echo "$words"
}

count_dir() {
    local dir="$1"
    local label="$2"
    local files=("$dir"/*.adoc)

    if [[ ! -e "${files[0]}" ]]; then
        echo "$label: no .adoc files found"
        return
    fi

    local n=0 total=0 min=999999 max=0
    local abs_total=0 abs_min=999999 abs_max=0 abs_count=0 abs_missing=0
    local -a counts=()
    local -a abs_counts=()
    local -a file_data=()

    for f in "${files[@]}"; do
        local w aw
        w=$(wc -w < "$f")
        aw=$(abstract_words "$f")
        counts+=("$w")
        abs_counts+=("$aw")
        file_data+=("$w:$aw:$(basename "$f")")
        total=$((total + w))
        n=$((n + 1))
        if (( w < min )); then min=$w; fi
        if (( w > max )); then max=$w; fi
        if (( aw > 0 )); then
            abs_total=$((abs_total + aw))
            abs_count=$((abs_count + 1))
            if (( aw < abs_min )); then abs_min=$aw; fi
            if (( aw > abs_max )); then abs_max=$aw; fi
        else
            abs_missing=$((abs_missing + 1))
        fi
    done

    IFS=$'\n' sorted=($(printf '%s\n' "${counts[@]}" | sort -n)); unset IFS
    local median
    if (( n % 2 == 1 )); then
        median=${sorted[n/2]}
    else
        median=$(( (sorted[n/2 - 1] + sorted[n/2]) / 2 ))
    fi
    local mean=$(( total / n ))

    local b1=0 b2=0 b3=0 b4=0 b5=0
    for w in "${counts[@]}"; do
        if   (( w < 50 ));  then b1=$((b1 + 1))
        elif (( w < 100 )); then b2=$((b2 + 1))
        elif (( w < 200 )); then b3=$((b3 + 1))
        elif (( w < 500 )); then b4=$((b4 + 1))
        else                     b5=$((b5 + 1))
        fi
    done

    echo "$label ($n files, $total words)"
    echo "  Total — min: $min  max: $max  mean: $mean  median: $median"
    echo "  Total — <50: $b1 | 50-99: $b2 | 100-199: $b3 | 200-499: $b4 | 500+: $b5"

    if (( abs_count > 0 )); then
        IFS=$'\n' abs_sorted=($(printf '%s\n' "${abs_counts[@]}" | sort -n | grep -v '^0$')); unset IFS
        local abs_median
        if (( abs_count % 2 == 1 )); then
            abs_median=${abs_sorted[abs_count/2]}
        else
            abs_median=$(( (abs_sorted[abs_count/2 - 1] + abs_sorted[abs_count/2]) / 2 ))
        fi
        local abs_mean=$(( abs_total / abs_count ))

        local ab1=0 ab2=0 ab3=0 ab4=0 ab5=0
        for w in "${abs_counts[@]}"; do
            if (( w == 0 )); then continue; fi
            if   (( w < 10 )); then ab1=$((ab1 + 1))
            elif (( w < 20 )); then ab2=$((ab2 + 1))
            elif (( w < 30 )); then ab3=$((ab3 + 1))
            elif (( w < 40 )); then ab4=$((ab4 + 1))
            else                    ab5=$((ab5 + 1))
            fi
        done

        echo "  Abstract — found: $abs_count  missing: $abs_missing"
        echo "  Abstract — min: $abs_min  max: $abs_max  mean: $abs_mean  median: $abs_median"
        echo "  Abstract — <10w: $ab1 | 10-19w: $ab2 | 20-29w: $ab3 | 30-39w: $ab4 | 40+w: $ab5"
    else
        echo "  Abstract — none found"
    fi

    if [[ "$SHOW_LIST" == "true" ]]; then
        echo ""
        printf "%6s  %6s  %s\n" "Total" "Abstr" "File"
        printf "%6s  %6s  %s\n" "-----" "-----" "----"
        for entry in "${file_data[@]}"; do
            IFS=: read -r tw aw fname <<< "$entry"
            local abs_col
            if (( aw > 0 )); then
                abs_col="$aw"
            else
                abs_col="---"
            fi
            printf "%6d  %6s  %s\n" "$tw" "$abs_col" "$fname"
        done | sort -rn
    fi
}

echo ""
count_dir "$REPO_ROOT/assemblies" "Assemblies"
echo ""
count_dir "$REPO_ROOT/modules" "Modules"
echo ""
