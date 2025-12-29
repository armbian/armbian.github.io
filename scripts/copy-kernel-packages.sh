#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# copy-armbian-kernel-and-uboot-debs.sh
#
# Copy a minimal, de-duplicated set of Armbian kernel and U-Boot .deb packages
# from SRC_DIR to DST_DIR based on image-info.json.
#
# Kernel packages are unique per (linuxfamily, branch).
# U-Boot packages are unique per (board, branch).
#
# SELECT syntax:
#   SELECT='linuxfamily_glob[:branch_glob] ...'
#   Examples:
#     SELECT='meson64:current imx6:current'
#     SELECT='meson64:* imx6:current'
#     SELECT='meson64*'        # shorthand for meson64*:*
#
# UBOOT_SELECT syntax:
#   UBOOT_SELECT='board_glob[:branch_glob] ...'
#   Examples:
#     UBOOT_SELECT='odroidm1:current'
#     UBOOT_SELECT='bananapim64:*'
#
# Other flags:
#   DRY_RUN=true
#   INCLUDE_LIBC_DEV=true
#   COPY_UBOOT=false
# =============================================================================

# Default URL for image-info.json
DEFAULT_JSON_URL="https://github.armbian.com/image-info.json"
JSON_FILE="${1:-image-info.json}"

SRC_DIR="${SRC_DIR:-./in}"
DST_DIR="${DST_DIR:-./out}"

SELECT="${SELECT:-}"
INCLUDE_LIBC_DEV="${INCLUDE_LIBC_DEV:-false}"
DRY_RUN="${DRY_RUN:-false}"

COPY_UBOOT="${COPY_UBOOT:-true}"
UBOOT_SELECT="${UBOOT_SELECT:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

# Fetch JSON from URL if file doesn't exist
if [[ ! -f "$JSON_FILE" ]]; then
  if [[ "$JSON_FILE" == "http://"* ]] || [[ "$JSON_FILE" == "https://"* ]]; then
    # JSON parameter is a URL, download it
    echo "Downloading JSON from: $JSON_FILE"
    curl -fsSL "$JSON_FILE" -o image-info.json || die "Failed to download JSON from $JSON_FILE"
    JSON_FILE="image-info.json"
  else
    # Try to download from default URL
    echo "JSON file not found: $JSON_FILE"
    echo "Attempting to download from: $DEFAULT_JSON_URL"
    # Ensure target directory exists
    JSON_DIR=$(dirname "$JSON_FILE")
    [[ -n "$JSON_DIR" ]] && mkdir -p "$JSON_DIR"
    curl -fsSL "$DEFAULT_JSON_URL" -o "$JSON_FILE" || die "Failed to download JSON from $DEFAULT_JSON_URL"
    echo "Downloaded successfully to: $JSON_FILE"
  fi
fi

[[ -f "$JSON_FILE" ]] || die "JSON not found: $JSON_FILE"
[[ -d "$SRC_DIR" ]] || die "SRC_DIR not found: $SRC_DIR"
mkdir -p "$DST_DIR"

# -----------------------------------------------------------------------------
# Expand JSON to triplets (board, linuxfamily, branch)
# -----------------------------------------------------------------------------
JQ_EXPAND='
  def norm_branches:
    if . == null then []
    elif (type=="string") then ( gsub("[,\\s]+";" ") | split(" ") | map(select(length>0)) )
    elif (type=="array")  then ( map(tostring) | map(select(length>0)) )
    else [] end;

  [
    .[]
    | {
        board:       (.out.HOST // .in.inventory.BOARD // ""),
        linuxfamily: (.out.LINUXFAMILY // .in.inventory.BOARDFAMILY // ""),
        branches:    ((.in.inventory.BOARD_POSSIBLE_BRANCHES
                      // .in.inventory.BOARD_TOP_LEVEL_VARS.BOARD_POSSIBLE_BRANCHES)
                      | norm_branches)
      }
    | select((.board|length>0) and (.linuxfamily|length>0) and (.branches|length>0))
    | . as $o
    | $o.branches[]
    | { board: $o.board, linuxfamily: $o.linuxfamily, branch: . }
  ]
  | unique_by([.linuxfamily,.branch,.board])
  | sort_by(.board, .branch, .linuxfamily)
  | group_by([.board,.branch]) | map(.[0])
'

# Kernel pairs: dedupe boards for same (linuxfamily,branch)
JQ_KERNEL_PAIRS="$JQ_EXPAND"'
  | sort_by(.linuxfamily, .branch, .board)
  | group_by([.linuxfamily,.branch]) | map(.[0])
  | map([.linuxfamily, .branch] | @tsv)
  | .[]
'

# U-Boot triplets: keep all boards
JQ_UBOOT_TRIPLETS="$JQ_EXPAND"'
  | map([.board, .branch] | @tsv)
  | .[]
'

mapfile -t KERNEL_PAIRS < <(jq -r "$JQ_KERNEL_PAIRS" "$JSON_FILE" | sort -u)
mapfile -t UBOOT_TRIPLETS < <(jq -r "$JQ_UBOOT_TRIPLETS" "$JSON_FILE" | sort -u)

[[ ${#KERNEL_PAIRS[@]} -gt 0 ]] || die "No kernel pairs found"

# -----------------------------------------------------------------------------
# Selection helpers (IMPORTANT: local IFS includes space)
# -----------------------------------------------------------------------------
pair_selected() {
  local fam="$1" br="$2"
  local token sf sb
  local -a tokens=()

  [[ -z "${SELECT:-}" ]] && return 0

  # Split SELECT on spaces/newlines/tabs regardless of global IFS
  IFS=$' \n\t' read -r -a tokens <<< "${SELECT}"

  for token in "${tokens[@]}"; do
    [[ -z "$token" ]] && continue

    if [[ "$token" == *:* ]]; then
      sf="${token%%:*}"
      sb="${token#*:}"
      [[ -z "$sf" ]] && sf="*"
      [[ -z "$sb" ]] && sb="*"
    else
      sf="$token"
      sb="*"
    fi

    # IMPORTANT: pattern side must be unquoted to enable glob matching (*)
    if [[ $fam == $sf && $br == $sb ]]; then
      return 0
    fi
  done
  return 1
}

uboot_selected() {
  local board="$1" br="$2"
  local token sb sbr
  local -a tokens=()

  [[ -z "${UBOOT_SELECT:-}" ]] && return 0
  [[ "${UBOOT_SELECT}" == "*" ]] && return 0

  # Split on spaces/newlines/tabs regardless of global IFS
  IFS=$' \n\t' read -r -a tokens <<< "${UBOOT_SELECT}"

  for token in "${tokens[@]}"; do
    [[ -z "$token" ]] && continue

    if [[ "$token" == *:* ]]; then
      sb="${token%%:*}"
      sbr="${token#*:}"
      [[ -z "$sb" ]] && sb="*"
      [[ -z "$sbr" ]] && sbr="*"
    else
      sb="$token"
      sbr="*"
    fi

    # IMPORTANT: unquoted to enable glob matching
    if [[ $board == $sb && $br == $sbr ]]; then
      return 0
    fi
  done

  return 1
}


# -----------------------------------------------------------------------------
# Copy helpers
# -----------------------------------------------------------------------------
shopt -s nullglob

copy_flat() {
  local glob="$1"
  local files=( $glob )

  [[ ${#files[@]} -eq 0 ]] && { echo "  MISSING: $(basename "$glob")"; return 1; }

  for f in "${files[@]}"; do
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "  WOULD COPY: $(basename "$f")"
    else
      cp -a "$f" "$DST_DIR/"
      echo "  COPIED:     $(basename "$f")"
    fi
  done
}

copy_recursive() {
  local pat="$1"
  local files=()

  while IFS= read -r -d '' f; do files+=("$f"); done < <(
    find "$SRC_DIR" -type f -name "$pat" -print0 2>/dev/null || true
  )

  [[ ${#files[@]} -eq 0 ]] && { echo "  MISSING: $pat"; return 1; }

  for f in "${files[@]}"; do
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "  WOULD COPY: $(basename "$f")"
    else
      cp -a "$f" "$DST_DIR/"
      echo "  COPIED:     $(basename "$f")"
    fi
  done
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
copied=0
missing=0
selected_pairs=0

declare -A selected_pairs_set=()

echo "JSON:         $JSON_FILE"
echo "SRC_DIR:      $SRC_DIR"
echo "DST_DIR:      $DST_DIR"
echo "SELECT:       ${SELECT:-<all>}"
echo "COPY_UBOOT:   $COPY_UBOOT"
echo "UBOOT_SELECT: ${UBOOT_SELECT:-<from kernels>}"
echo "DRY_RUN:      $DRY_RUN"
echo

# Kernels
for line in "${KERNEL_PAIRS[@]}"; do
  fam="${line%%$'\t'*}"
  br="${line#*$'\t'}"

  pair_selected "$fam" "$br" || continue

  selected_pairs=$((selected_pairs+1))
  selected_pairs_set["$fam:$br"]=1

  echo "== Pair: linuxfamily=$fam branch=$br =="

  for p in linux-image linux-dtb linux-headers; do
    copy_flat "$SRC_DIR/${p}-${br}-${fam}_*.deb" && copied=$((copied+1)) || missing=$((missing+1))
  done

  if [[ "$INCLUDE_LIBC_DEV" == "true" ]]; then
    copy_flat "$SRC_DIR/linux-libc-dev-${br}-${fam}_*.deb" && copied=$((copied+1)) || missing=$((missing+1))
  fi

  echo
done

[[ $selected_pairs -gt 0 ]] || die "No kernel pairs selected"

# U-Boot
if [[ "$COPY_UBOOT" == "true" ]]; then
  echo "== U-Boot packages =="

  for line in "${UBOOT_TRIPLETS[@]}"; do
    board="${line%%$'\t'*}"
    br="${line#*$'\t'}"

    uboot_selected "$board" "$br" || continue

    echo "-- board=$board branch=$br --"
    copy_recursive "linux-u-boot-${board}-${br}_*.deb" \
      && copied=$((copied+1)) || missing=$((missing+1))
  done
  echo
fi

echo "Done."
echo "Selected (linuxfamily,branch) pairs: $selected_pairs"
echo "Matched file groups:                $copied"
echo "Missing patterns:                  $missing"
