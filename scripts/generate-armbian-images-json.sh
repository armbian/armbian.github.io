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

# Bigin / Zoho enrichment (optional)
BIGIN_ENABLE="${BIGIN_ENABLE:-true}"
BIGIN_API_BASE="${BIGIN_API_BASE:-https://www.zohoapis.eu/bigin/v2}"
ZOHO_OAUTH_TOKEN_URL="${ZOHO_OAUTH_TOKEN_URL:-https://accounts.zoho.eu/oauth/v2/token}"

# Custom field API name in Bigin Accounts holding the Company slug (matches board_vendor)
BIGIN_COMPANY_SLUG_FIELD="${BIGIN_COMPANY_SLUG_FIELD:-Company_slug}"

# Fields we fetch from Bigin Accounts (Logo is NOT fetched; logo is computed from board_vendor)
BIGIN_FIELDS="Account_Name,Website,Description,${BIGIN_COMPANY_SLUG_FIELD}"

# -----------------------------------------------------------------------------
# Requirements
# -----------------------------------------------------------------------------
need() { command -v "$1" >/dev/null || { echo "ERROR: missing '$1'" >&2; exit 1; }; }
need rsync gh jq jc find grep sed cut awk sort mktemp curl

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
declare -A BOARD_NAME_MAP=()
declare -A BOARD_VENDOR_MAP=()

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
# Optional: Load company data from Bigin keyed by company_slug (matches board_vendor)
# -----------------------------------------------------------------------------
declare -A COMPANY_NAME_BY_SLUG=()
declare -A COMPANY_WEBSITE_BY_SLUG=()
declare -A COMPANY_DESC_BY_SLUG=()

get_zoho_access_token() {
  local client_id="${ZOHO_CLIENT_ID:-}"
  local client_secret="${ZOHO_CLIENT_SECRET:-}"
  local refresh_token="${ZOHO_REFRESH_TOKEN:-}"

  if [[ -z "$client_id" || -z "$client_secret" || -z "$refresh_token" ]]; then
    echo ""
    return 0
  fi

  curl -sH "Content-type: multipart/form-data" \
    -F refresh_token="$refresh_token" \
    -F client_id="$client_id" \
    -F client_secret="$client_secret" \
    -F grant_type=refresh_token \
    -X POST "$ZOHO_OAUTH_TOKEN_URL" \
  | jq -r '.access_token // empty'
}

load_bigin_companies() {
  local token="$1"
  [[ -n "$token" ]] || return 0

  echo "▶ Fetching Bigin company data…" >&2
  echo "  - fields: ${BIGIN_FIELDS}" >&2
  echo "  - company slug field: ${BIGIN_COMPANY_SLUG_FIELD}" >&2
  echo "  - join key: board_vendor == company_slug" >&2

  local page=1 per_page=200 more="true"
  local loaded=0

  while [[ "$more" == "true" ]]; do
    local resp="/tmp/bigin-accounts-${page}.json"

    curl -s \
      -H "Authorization: Zoho-oauthtoken ${token}" \
      "${BIGIN_API_BASE}/Accounts?fields=${BIGIN_FIELDS}&per_page=${per_page}&page=${page}" \
      > "$resp"

    if ! jq -e '.data' "$resp" >/dev/null 2>&1; then
      echo "WARNING: Bigin Accounts response missing .data (page=${page}); skipping enrichment." >&2
      jq '.' "$resp" >&2 || true
      return 0
    fi

    while IFS=$'\t' read -r slug name website desc; do
      slug="${slug,,}"
      [[ -z "$slug" ]] && continue
      COMPANY_NAME_BY_SLUG["$slug"]="$name"
      COMPANY_WEBSITE_BY_SLUG["$slug"]="$website"
      COMPANY_DESC_BY_SLUG["$slug"]="$desc"
      ((loaded++)) || true
    done < <(
      jq -r --arg f "$BIGIN_COMPANY_SLUG_FIELD" '
        (.data // [])
        | map({
            slug: (.[ $f ] // "" | tostring),
            name: (.Account_Name // "" | tostring),
            website: (.Website // "" | tostring),
            desc: (.Description // "" | tostring)
          })
        | .[]
        | select(.slug != "")
        | [.slug,.name,.website,.desc] | @tsv
      ' "$resp"
    )

    more="$(jq -r '.info.more_records // false' "$resp")"
    page=$((page + 1))
    [[ "$page" -le 50 ]] || { echo "WARNING: Bigin pagination safety cap hit; stopping." >&2; break; }
  done

  echo "  - Bigin company slugs loaded: ${#COMPANY_NAME_BY_SLUG[@]} (rows processed: ${loaded})" >&2
}

if [[ "${BIGIN_ENABLE}" == "true" ]]; then
  ZOHO_TOKEN="$(get_zoho_access_token || true)"
  if [[ -n "${ZOHO_TOKEN}" ]]; then
    load_bigin_companies "${ZOHO_TOKEN}" || true
  else
    echo "ℹ️  Bigin enrichment disabled (missing Zoho secrets or token could not be obtained)." >&2
  fi
fi

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
# Load exposed patterns once (skip blanks/comments)
# -----------------------------------------------------------------------------
EXPOSED_MAP_FILE="${OS_DIR}/exposed.map"

# Return 0 if given candidate matches any exposed pattern
is_promoted_candidate() {
  local candidate="$1"
  grep -Eq -f "$EXPOSED_MAP_FILE" <<<"$candidate"
}

is_promoted() {
  # args: image_name board_slug url
  local image_name="$1" board_slug="$2" url="$3"

  # Candidates to match: filename, board/archive/filename, and relative URL paths
  local rel_dl="${url#https://dl.armbian.com/}"
  local rel_cache="${url#https://cache.armbian.com/artifacts/}"
  local rel_github="${url#https://github.com/armbian/}"

  local c
  for c in \
    "$image_name" \
    "${board_slug}/archive/${image_name}" \
    "$rel_dl" \
    "$rel_cache" \
    "$rel_github"
  do
    [[ "$c" == "$url" ]] && continue
    if is_promoted_candidate "$c"; then
      return 0
    fi
  done

  return 1
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
  echo '"board_slug"|"board_name"|"board_vendor"|"company_name"|"company_website"|"company_logo"|"company_description"|"armbian_version"|"file_url"|"file_url_asc"|"file_url_sha"|"file_url_torrent"|"redi_url"|"redi_url_asc"|"redi_url_sha"|"redi_url_torrent"|"file_updated"|"file_size"|"distro_release"|"kernel_branch"|"image_variant"|"preinstalled_application"|"promoted"|"download_repository"|"file_extension"'

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

    PROMOTED=false
    if is_promoted "$IMAGE_NAME" "$BOARD_SLUG" "$URL"; then
      PROMOTED=true
    fi

    # Join key: board_vendor == Bigin company_slug
    BOARD_VENDOR="${BOARD_VENDOR_MAP[$BOARD_SLUG]:-}"
    COMPANY_KEY="${BOARD_VENDOR,,}"

    C_NAME="${COMPANY_NAME_BY_SLUG[$COMPANY_KEY]:-}"
    C_WEB="${COMPANY_WEBSITE_BY_SLUG[$COMPANY_KEY]:-}"
    C_DESC="${COMPANY_DESC_BY_SLUG[$COMPANY_KEY]:-}"

    # company_logo is computed (not fetched from Bigin)
    C_LOGO=""
    if [[ -n "$BOARD_VENDOR" ]]; then
      C_LOGO="https://cache.armbian.com/images/vendors/150/${BOARD_VENDOR}.png"
    fi

    echo "${BOARD_SLUG}|${BOARD_NAME_MAP[$BOARD_SLUG]:-}|${BOARD_VENDOR}|${C_NAME}|${C_WEB}|${C_LOGO}|${C_DESC}|${VER}|${URL}|${ASC}|${SHA}|${TOR}|${REDI_URL}|${REDI_URL}.asc|${REDI_URL}.sha|${REDI_URL}.torrent|${DATE}|${IMAGE_SIZE}|${DISTRO}|${BRANCH}|${VARIANT}|${APP}|${PROMOTED}|${REPO}|${FILE_EXTENSION}"
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
