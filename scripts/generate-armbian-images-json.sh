#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SOURCE_OF_TRUTH="${SOURCE_OF_TRUTH:-rsync://fi.mirror.armbian.de}"
OS_DIR="${OS_DIR:-./os}"
BOARD_DIR="${BOARD_DIR:-./build/config/boards}"
OUT="${OUT:-armbian-images.json}"

# -----------------------------------------------------------------------------
# Requirements
# -----------------------------------------------------------------------------
need() { command -v "$1" >/dev/null || { echo "ERROR: missing '$1'" >&2; exit 1; }; }
need rsync gh jq jc find grep sed cut awk sort mktemp

[[ -f "${OS_DIR}/exposed.map" ]] || { echo "ERROR: ${OS_DIR}/exposed.map not found" >&2; exit 1; }
[[ -d "${BOARD_DIR}" ]] || { echo "ERROR: board directory not found: ${BOARD_DIR}" >&2; exit 1; }

# -----------------------------------------------------------------------------
# Extract variable from board config
# -----------------------------------------------------------------------------
extract_cfg_var() {
  local file="$1" var="$2"
  awk -v var="$var" '
    {
      line=$0
      sub(/[ \t]*#.*/, "", line)
      if (line ~ var"[ \t]*=") {
        sub(/^.*=/,"",line)
        gsub(/^["'\'']|["'\'']$/,"",line)
        print line; exit
      }
    }' "$file" 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Load board metadata + track incomplete metadata (file-based, set -u safe)
# -----------------------------------------------------------------------------
declare -A BOARD_NAME_MAP
declare -A BOARD_VENDOR_MAP

MISSING_META_FILE="$(mktemp)"
trap 'rm -f "$MISSING_META_FILE"' EXIT

while IFS= read -r cfg; do
  slug="$(basename "${cfg%.*}")"
  slug="${slug,,}"

  name="$(extract_cfg_var "$cfg" BOARD_NAME)"
  vendor="$(extract_cfg_var "$cfg" BOARD_VENDOR)"

  [[ -n "$name" ]]   && BOARD_NAME_MAP["$slug"]="$name"
  [[ -n "$vendor" ]] && BOARD_VENDOR_MAP["$slug"]="$vendor"

  if [[ -z "$name" || -z "$vendor" ]]; then
    printf '%s\n' "$slug" >>"$MISSING_META_FILE"
  fi
done < <(
  find "$BOARD_DIR" -maxdepth 1 -type f \
    \( -name "*.conf" -o -name "*.csc" -o -name "*.wip" -o -name "*.tvb" \) \
  | sort
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
is_version_token() { [[ "$1" =~ ^[0-9]{2}\.[0-9] ]]; }

is_preinstalled_app() {
  case "$1" in kali|homeassistant|openhab|omv) return 0 ;; *) return 1 ;; esac
}

strip_img_ext() {
  sed -E 's/(\.img(\.(xz|zst|gz))?)$//' <<<"$1"
}

extract_file_extension() {
  local n="$1"
  [[ "$n" == *.img.xz ]] && echo "img.xz" && return
  [[ "$n" == *.img.zst ]] && echo "img.zst" && return
  [[ "$n" == *.img.gz ]] && echo "img.gz" && return
  [[ "$n" == *.img ]] && echo "img" && return
  echo "${n##*.}"
}

get_download_repository() {
  local url="$1"
  if [[ "$url" == https://github.com/armbian/* ]]; then
    awk -F/ '{print $5}' <<<"$url"
  elif [[ "$url" == https://dl.armbian.com/* ]]; then
    awk -F/ '{print $5}' <<<"$url"
  else
    echo ""
  fi
}

# -----------------------------------------------------------------------------
# Parse image filename
# -----------------------------------------------------------------------------
parse_image_name() {
  local name="$1"
  IFS="_" read -r -a p <<<"$name"

  local ver="" board="" distro="" branch="" kernel="" tail=""
  local variant="server" app="" storage=""

  if is_version_token "${p[1]:-}"; then
    ver="${p[1]}"; board="${p[2]}"; distro="${p[3]}"
    branch="${p[4]}"; kernel="${p[5]}"; tail="${p[6]:-}"
  else
    ver="${p[2]}"; board="${p[3]}"; distro="${p[4]}"
    branch="${p[5]}"; kernel="${p[6]}"; tail="${p[7]:-}"
  fi

  if [[ "$kernel" == *-* ]]; then
    suffix="$(strip_img_ext "${kernel#*-}")"
    if is_preinstalled_app "$suffix"; then
      app="$suffix"
    else
      [[ "${suffix##*-}" == "ufs" ]] && storage="ufs"
    fi
  fi

  [[ "$tail" == minimal* ]] && variant="minimal"
  [[ "$name" == *_desktop.img.* ]] && variant="$tail"

  printf '%s\n' "$ver" "$board" "$distro" "$branch" "$variant" "$app" "$storage"
}

# -----------------------------------------------------------------------------
# Build feeds (NO .txt files)
# -----------------------------------------------------------------------------
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"; rm -f "$MISSING_META_FILE"' EXIT
feed="$tmpdir/feed.txt"

echo "▶ Building feeds…" >&2

# Mirror feed
rsync --recursive --list-only "${SOURCE_OF_TRUTH}/dl/" |
awk '
{
  size=$2; gsub(/[.,]/,"",size)
  url="https://dl.armbian.com/" $5
  if (url ~ /\/[^\/]+\/archive\/Armbian/ &&
      url !~ /\.txt$/ &&
      url !~ /\.(asc|sha|torrent)$/ &&
      url !~ /(homeassistant|openhab|kali|omv)/) {
    dt=$3 "T" $4 "Z"; gsub("/", "-", dt)
    print size "|" url "|" dt
  }
}' >"$tmpdir/a.txt"

# GitHub feed
: >"$tmpdir/bcd.txt"
for repo in community os distribution; do
  gh release view --json assets --repo "github.com/armbian/$repo" |
  jq -r '.assets[]
    | select(.url | test("\\.txt($|\\?)") | not)
    | select(.url | test("\\.(asc|sha|torrent)($|\\?)") | not)
    | "\(.size)|\(.url)|\(.createdAt)"' >>"$tmpdir/bcd.txt"
done

cat "$tmpdir/a.txt" "$tmpdir/bcd.txt" >"$feed"

# -----------------------------------------------------------------------------
# JSON generation
# -----------------------------------------------------------------------------
{
  echo '"board_slug"|"board_name"|"board_vendor"|"armbian_version"|"file_url"|"file_url_asc"|"file_url_sha"|"file_url_torrent"|"redi_url"|"redi_url_asc"|"redi_url_sha"|"redi_url_torrent"|"file_updated"|"file_size"|"distro_release"|"kernel_branch"|"image_variant"|"preinstalled_application"|"promoted"|"download_repository"|"file_extension"'

  while IFS="|" read -r SIZE URL DATE; do
    IMAGE_SIZE="${SIZE//[.,]/}"
    IMAGE_NAME="${URL##*/}"

    mapfile -t p < <(parse_image_name "$IMAGE_NAME")
    VER="${p[0]}"; BOARD="${p[1]}"; DISTRO="${p[2]}"; BRANCH="${p[3]}"
    VARIANT="${p[4]}"; APP="${p[5]}"; STORAGE="${p[6]}"

    [[ -z "$BOARD" ]] && continue
    BOARD_SLUG="${BOARD,,}"

    REPO="$(get_download_repository "$URL")"
    [[ -z "$REPO" ]] && continue

    PREFIX=""; [[ "$REPO" == "os" ]] && PREFIX="nightly/"

    BASE_EXT="$(extract_file_extension "$IMAGE_NAME")"
    if [[ "$IMAGE_NAME" == *.oowow.img.xz ]]; then
      FILE_EXTENSION="oowow.img.xz"
    elif [[ -n "$STORAGE" ]]; then
      FILE_EXTENSION="${STORAGE}.${BASE_EXT}"
    else
      FILE_EXTENSION="$BASE_EXT"
    fi

    APP_SUFFIX=""; [[ -n "$APP" ]] && APP_SUFFIX="-${APP}"
    REDI_URL="https://dl.armbian.com/${PREFIX}${BOARD_SLUG}/${DISTRO^}_${BRANCH}_${VARIANT}${APP_SUFFIX}"

    if [[ "$URL" == https://github.com/armbian/* ]]; then
      CACHE="https://cache.armbian.com/artifacts/${BOARD_SLUG}/archive/${IMAGE_NAME}"
      ASC="$CACHE.asc"; SHA="$CACHE.sha"; TOR="$CACHE.torrent"
    else
      ASC="$URL.asc"; SHA="$URL.sha"; TOR="$URL.torrent"
    fi

    echo "${BOARD_SLUG}|${BOARD_NAME_MAP[$BOARD_SLUG]:-}|${BOARD_VENDOR_MAP[$BOARD_SLUG]:-}|${VER}|${URL}|${ASC}|${SHA}|${TOR}|${REDI_URL}|${REDI_URL}.asc|${REDI_URL}.sha|${REDI_URL}.torrent|${DATE}|${IMAGE_SIZE}|${DISTRO}|${BRANCH}|${VARIANT}|${APP}|false|${REPO}|${FILE_EXTENSION}"
  done <"$feed"

} | jc --csv | jq '{assets:.}' >"$OUT"

# -----------------------------------------------------------------------------
# Emit warnings for incomplete board metadata (non-fatal)
# -----------------------------------------------------------------------------
if [[ -s "$MISSING_META_FILE" ]]; then
  echo "WARNING: Boards with incomplete metadata detected:" >&2
  sort -u "$MISSING_META_FILE" | while IFS= read -r slug; do
    [[ -z "$slug" ]] && continue
    echo "  - ${slug} (missing BOARD_NAME and/or BOARD_VENDOR)" >&2
  done
fi

echo "✔ Generated $OUT"
echo "✔ Assets: $(jq '.assets | length' "$OUT")"
