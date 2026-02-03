#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SOURCE_OF_TRUTH="${SOURCE_OF_TRUTH:-rsync://fi.mirror.armbian.de}"
OS_DIR="${OS_DIR:-./os}"
BOARD_DIR="${BOARD_DIR:-./build/config/boards}"
REUSABLE_FILE="${REUSABLE_FILE:-./release-targets/reusable.yml}"
OUT="${OUT:-armbian-images.json}"

# -----------------------------------------------------------------------------
# Zoho Bigin configuration (optional enrichment)
# -----------------------------------------------------------------------------
BIGIN_ENABLE="${BIGIN_ENABLE:-true}"
BIGIN_API_BASE="${BIGIN_API_BASE:-https://www.zohoapis.eu/bigin/v2}"
ZOHO_OAUTH_TOKEN_URL="${ZOHO_OAUTH_TOKEN_URL:-https://accounts.zoho.eu/oauth/v2/token}"

# Accounts: custom field that contains company slug (must match board_vendor)
BIGIN_COMPANY_SLUG_FIELD="${BIGIN_COMPANY_SLUG_FIELD:-Company_slug}"
BIGIN_ACCOUNT_FIELDS="Account_Name,Website,${BIGIN_COMPANY_SLUG_FIELD}"

# Pipelines (confirmed keys): Boards, Closing_Date, Stage
BIGIN_PLATINUM_MODULE="${BIGIN_PLATINUM_MODULE:-Pipelines}"
BIGIN_PLATINUM_BOARDS_FIELD="${BIGIN_PLATINUM_BOARDS_FIELD:-Boards}"
BIGIN_PLATINUM_UNTIL_FIELD="${BIGIN_PLATINUM_UNTIL_FIELD:-Closing_Date}"
BIGIN_PLATINUM_STATUS_FIELD="${BIGIN_PLATINUM_STATUS_FIELD:-Stage}"
BIGIN_PLATINUM_FIELDS="${BIGIN_PLATINUM_STATUS_FIELD},${BIGIN_PLATINUM_UNTIL_FIELD},${BIGIN_PLATINUM_BOARDS_FIELD}"

# -----------------------------------------------------------------------------
# Requirements
# -----------------------------------------------------------------------------
need() { command -v "$1" >/dev/null || { echo "ERROR: missing '$1'" >&2; exit 1; }; }
need rsync gh jq jc python3 find grep sed cut awk sort mktemp curl date

[[ -f "${OS_DIR}/exposed.map" ]] || { echo "ERROR: ${OS_DIR}/exposed.map not found" >&2; exit 1; }
[[ -d "${BOARD_DIR}" ]] || { echo "ERROR: board directory not found: ${BOARD_DIR}" >&2; exit 1; }

TODAY_UTC="$(date -u +%F)"

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
declare -A BOARD_SUPPORT_MAP=()

MISSING_META_FILE="$(mktemp)"
trap 'rm -f "$MISSING_META_FILE"' EXIT

while IFS= read -r cfg; do
  slug="$(basename "${cfg%.*}")"
  slug="${slug,,}"

  name="$(extract_cfg_var "$cfg" BOARD_NAME)"
  vendor="$(extract_cfg_var "$cfg" BOARD_VENDOR)"
  support="${cfg##*.}"; support="${support,,}"


  [[ -n "$name" ]]   && BOARD_NAME_MAP["$slug"]="$name"
  [[ -n "$vendor" ]] && BOARD_VENDOR_MAP["$slug"]="$vendor"
  [[ -n "$support" ]] && BOARD_SUPPORT_MAP["$slug"]="$support"

  if [[ -z "$name" || -z "$vendor" ]]; then
    printf '%s\n' "$slug" >>"$MISSING_META_FILE"
  fi
done < <(
  find "$BOARD_DIR" -maxdepth 1 -type f \
    \( -name "*.conf" -o -name "*.csc" -o -name "*.wip" -o -name "*.tvb" \) \
  | sort
)

# -----------------------------------------------------------------------------
# Load virtual boards from reusable.yml
# Boards that reuse artifact sets from other boards but with custom metadata
# -----------------------------------------------------------------------------
declare -A REUSABLE_BOARD_USES=()       # board_slug -> target_board_slug
declare -A REUSABLE_BOARD_BRANCH=()     # board_slug -> branch_filter (optional)
declare -A REUSABLE_BOARD_EXT=()        # board_slug -> file_extension_filter (optional)
declare -A REUSABLE_BOARD_META=()       # board_slug -> "name|vendor|support"

if [[ -f "$REUSABLE_FILE" ]]; then
  echo "▶ Loading reusable board definitions from ${REUSABLE_FILE}…" >&2

  while IFS=$'\t' read -r slug name vendor support uses branch ext; do
    slug="${slug,,}"
    [[ -z "$slug" ]] && continue

    # Store the reusable board mapping
    REUSABLE_BOARD_USES["$slug"]="${uses:-}"
    REUSABLE_BOARD_BRANCH["$slug"]="${branch:-}"
    REUSABLE_BOARD_EXT["$slug"]="${ext:-}"
    REUSABLE_BOARD_META["$slug"]="${name:-}|${vendor:-}|${support:-}"

    # Add to board maps (overwrites if exists)
    [[ -n "$name" ]] && BOARD_NAME_MAP["$slug"]="$name"
    [[ -n "$vendor" ]] && BOARD_VENDOR_MAP["$slug"]="$vendor"
    [[ -n "$support" ]] && BOARD_SUPPORT_MAP["$slug"]="$support"

    ext_msg="${ext:+ (ext: ${ext})}"
    echo "  - ${slug} → ${uses}${branch:+ (branch: ${branch})}${ext_msg}" >&2
  done < <(
    python3 -c "
import yaml, sys
try:
    with open('$REUSABLE_FILE') as f:
        data = yaml.safe_load(f)
    for b in data.get('boards', []):
        print('\t'.join([
            str(b.get('board_slug', '')),
            str(b.get('board_name', '')),
            str(b.get('board_vendor', '')),
            str(b.get('board_support', '')),
            str(b.get('uses', '')),
            str(b.get('branch', '')),
            str(b.get('file_extension', ''))
        ]))
except Exception as e:
    sys.stderr.write(f'Error loading reusable.yml: {e}\n')
    sys.exit(0)
" 2>/dev/null || true
  )

  echo "  - Reusable boards loaded: ${#REUSABLE_BOARD_USES[@]}" >&2
else
  echo "ℹ️  Reusable board file not found: ${REUSABLE_FILE}" >&2
fi

# -----------------------------------------------------------------------------
# Optional: Load company data from Bigin keyed by company_slug (matches board_vendor)
# -----------------------------------------------------------------------------
declare -A COMPANY_NAME_BY_SLUG=()
declare -A COMPANY_WEBSITE_BY_SLUG=()

# Platinum support: store latest until-date per board_slug
declare -A PLATINUM_UNTIL_BY_BOARD=()

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

# Keep the latest ISO date/timestamp string lexicographically
max_date() {
  local a="$1" b="$2"
  [[ -z "$a" ]] && { echo "$b"; return; }
  [[ -z "$b" ]] && { echo "$a"; return; }
  [[ "$a" < "$b" ]] && echo "$b" || echo "$a"
}

# Convert "2025-06-25" or "2025-06-25T..." -> "2025-06-25"
date_only() {
  local s="$1"
  s="${s%%T*}"
  echo "$s"
}

load_bigin_companies() {
  local token="$1"
  [[ -n "$token" ]] || return 0

  echo "▶ Fetching Bigin company data…" >&2
  echo "  - fields: ${BIGIN_ACCOUNT_FIELDS}" >&2
  echo "  - company slug field: ${BIGIN_COMPANY_SLUG_FIELD}" >&2
  echo "  - join key: board_vendor == company_slug" >&2

  local page=1 per_page=200 more="true"
  local loaded=0

  while [[ "$more" == "true" ]]; do
    local resp="/tmp/bigin-accounts-${page}.json"

    curl -s \
      -H "Authorization: Zoho-oauthtoken ${token}" \
      "${BIGIN_API_BASE}/Accounts?fields=${BIGIN_ACCOUNT_FIELDS}&per_page=${per_page}&page=${page}" \
      > "$resp"

    if ! jq -e '.data' "$resp" >/dev/null 2>&1; then
      echo "WARNING: Bigin Accounts response missing .data (page=${page}); skipping company enrichment." >&2
      jq '.' "$resp" >&2 || true
      return 0
    fi

    while IFS=$'\t' read -r slug name website desc; do
      slug="${slug,,}"
      [[ -z "$slug" ]] && continue
      COMPANY_NAME_BY_SLUG["$slug"]="$name"
      COMPANY_WEBSITE_BY_SLUG["$slug"]="$website"
      ((loaded++)) || true
    done < <(
      jq -r --arg f "$BIGIN_COMPANY_SLUG_FIELD" '
        (.data // [])
        | map({
            slug: (.[ $f ] // "" | tostring),
            name: (.Account_Name // "" | tostring),
            website: (.Website // "" | tostring),
          })
        | .[]
        | select(.slug != "")
        | [.slug,.name,.website,.desc] | @tsv
      ' "$resp"
    )

    more="$(jq -r '.info.more_records // false' "$resp")"
    page=$((page + 1))
    [[ "$page" -le 50 ]] || { echo "WARNING: Bigin Accounts pagination safety cap hit; stopping." >&2; break; }
  done

  echo "  - Bigin company slugs loaded: ${#COMPANY_NAME_BY_SLUG[@]} (rows processed: ${loaded})" >&2
}

load_bigin_platinum_support() {
  local token="$1"
  [[ -n "$token" ]] || return 0

  echo "▶ Fetching Bigin platinum support from ${BIGIN_PLATINUM_MODULE}…" >&2
  echo "  - fields: ${BIGIN_PLATINUM_FIELDS}" >&2
  echo "  - rule: map Boards tokens -> board_slug; ignore Stage=Cancelled/Canceled; latest Closing_Date wins" >&2

  local per_page=200
  local page_token=""
  local pages=0
  local rows=0
  local nonnull=0

  while :; do
    pages=$((pages + 1))
    [[ "$pages" -le 200 ]] || { echo "WARNING: pagination safety cap hit; stopping." >&2; break; }

    local resp="/tmp/bigin-platinum-${pages}.json"
    local url="${BIGIN_API_BASE}/${BIGIN_PLATINUM_MODULE}?fields=${BIGIN_PLATINUM_FIELDS}&per_page=${per_page}"
    [[ -n "$page_token" ]] && url="${url}&page_token=${page_token}"

    curl -s -H "Authorization: Zoho-oauthtoken ${token}" "$url" > "$resp"

    if ! jq -e '.data' "$resp" >/dev/null 2>&1; then
      echo "WARNING: Bigin ${BIGIN_PLATINUM_MODULE} response missing .data; skipping platinum extraction." >&2
      jq '.' "$resp" >&2 || true
      return 0
    fi

    # Count non-null Boards on this page (just for your debug summary)
    local page_nonnull
    page_nonnull="$(jq -r --arg bf "$BIGIN_PLATINUM_BOARDS_FIELD" '
      [(.data // [])[] | .[$bf] // empty | tostring | select(. != "" and . != "null")] | length
    ' "$resp" 2>/dev/null || echo 0)"
    nonnull=$((nonnull + page_nonnull))

    # IMPORTANT: no pipe into while; use process substitution to keep map updates
    while IFS=$'\t' read -r b until; do
      b="${b,,}"
      b="$(sed -E 's/^[[:space:]]+|[[:space:]]+$//g' <<<"$b")"
      [[ -z "$b" ]] && continue

      until="$(date_only "$until")"
      [[ -z "$until" || "$until" == "null" ]] && continue

      local cur="${PLATINUM_UNTIL_BY_BOARD[$b]:-}"
      PLATINUM_UNTIL_BY_BOARD["$b"]="$(max_date "$cur" "$until")"
      rows=$((rows + 1))
    done < <(
      jq -r \
        --arg bf "$BIGIN_PLATINUM_BOARDS_FIELD" \
        --arg uf "$BIGIN_PLATINUM_UNTIL_FIELD" \
        --arg sf "$BIGIN_PLATINUM_STATUS_FIELD" '
        (.data // [])
        | map(select(((.[ $sf ] // "") | tostring | ascii_downcase) | IN("cancelled","canceled") | not))
        | .[]
        | (.[ $uf ] // "" | tostring) as $until
        | (.[ $bf ] // "" | tostring) as $boards
        | select($boards != "" and $boards != "null")
        | ($boards
            | gsub("[\r\n\t]"; " ")
            | gsub("[;]+"; ",")
            | split(",")
            | map(gsub("^\\s+|\\s+$"; ""))
            | map(select(length>0))
          )[]
        | [., $until] | @tsv
      ' "$resp"
    )

    page_token="$(jq -r '.info.next_page_token // empty' "$resp")"
    [[ -n "$page_token" ]] || break
  done

  echo "  - pages read: ${pages}" >&2
  echo "  - records with non-empty Boards seen: ${nonnull}" >&2
  echo "  - platinum boards mapped: ${#PLATINUM_UNTIL_BY_BOARD[@]} (rows processed: ${rows})" >&2
}


if [[ "${BIGIN_ENABLE}" == "true" ]]; then
  ZOHO_TOKEN="$(get_zoho_access_token || true)"
  if [[ -n "${ZOHO_TOKEN}" ]]; then
    load_bigin_companies "${ZOHO_TOKEN}" || true
    load_bigin_platinum_support "${ZOHO_TOKEN}" || true
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

  # U-Boot ROM artifacts
  #   ...minimal.u-boot.rom.xz  -> u-boot.rom.xz
  #   ...minimal.u-boot.rom     -> u-boot.rom
  if [[ "$n" == *".u-boot.rom" ]] || [[ "$n" == *".u-boot.rom."* ]]; then
    if [[ "$n" == *".u-boot.rom."* ]]; then
      echo "u-boot.rom.${n##*.u-boot.rom.}"
    else
      echo "u-boot.rom"
    fi
    return
  fi

  # U-Boot BIN artifacts
  #   ...minimal.u-boot.bin.xz  -> u-boot.bin.xz
  #   ...minimal.u-boot.bin     -> u-boot.bin
  if [[ "$n" == *".u-boot.bin" ]] || [[ "$n" == *".u-boot.bin."* ]]; then
    if [[ "$n" == *".u-boot.bin."* ]]; then
      echo "u-boot.bin.${n##*.u-boot.bin.}"
    else
      echo "u-boot.bin"
    fi
    return
  fi

  # rootfs images
  if [[ "$n" == *".rootfs.img."* ]]; then
    echo "rootfs.img.${n##*.rootfs.img.}"
    return
  fi

  # oowow images
  if [[ "$n" == *".oowow.img."* ]]; then
    echo "oowow.img.${n##*.oowow.img.}"
    return
  fi

  # boot payload images:
  #   ...desktop.boot_sm8250-xiaomi-elish-boe.img.xz  -> boe.img.xz
  #   ...desktop.boot_recovery.img.xz                 -> recovery.img.xz
  if [[ "$n" == *".boot_"*".img."* ]]; then
    local after_boot="${n#*.boot_}"          # after ".boot_"
    local boot_stem="${after_boot%%.img.*}"  # before ".img."
    local flavor="$boot_stem"

    # if it's boot_sm8250-...-boe, take last '-' token
    [[ "$boot_stem" == *-* ]] && flavor="${boot_stem##*-}"

    echo "${flavor}.img.${n##*.img.}"
    return
  fi

  # qcow2 (or other img.*) -> canonical img.<rest>
  if [[ "$n" == *".img."* ]]; then
    echo "img.${n##*.img.}"
    return
  fi

  # plain .img
  if [[ "$n" == *.img ]]; then
    echo "img"
    return
  fi

  # hyperv cloud images: minimal.hyperv.zip.xz -> hyperv.zip.xz
  if [[ "$n" == *".hyperv.zip."* ]]; then
    echo "hyperv.zip.${n##*.hyperv.zip.}"
    return
  fi
  if [[ "$n" == *.hyperv.zip ]]; then
    echo "hyperv.zip"
    return
  fi

  # fallback
  echo "${n##*.}"
}

get_download_repository() {
  local url="$1"
  if [[ "$url" == https://github.com/armbian/* ]]; then
    awk -F/ '{print $5}' <<<"$url"
  elif [[ "$url" == https://dl.armbian.com/* ]]; then
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

is_promoted_candidate() {
  local candidate="$1"
  grep -Eq -f "$EXPOSED_MAP_FILE" <<<"$candidate"
}

is_promoted() {
  local image_name="$1" board_slug="$2" url="$3"

  # Never promote trunk builds unless from community
  [[ "$image_name" == *trunk* && "$image_name" != Armbian_community*trunk* ]] && return 1

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
  echo '"board_slug"|"board_name"|"board_vendor"|"board_support"|"company_name"|"company_website"|"company_logo"|"armbian_version"|"file_url"|"file_url_asc"|"file_url_sha"|"file_url_torrent"|"redi_url"|"redi_url_asc"|"redi_url_sha"|"redi_url_torrent"|"file_size"|"file_date"|"distro"|"branch"|"variant"|"file_application"|"promoted"|"download_repository"|"file_extension"|"kernel_version"|"platinum"|"platinum_expired"|"platinum_until"'

  while IFS="|" read -r SIZE URL DATE; do
    IMAGE_SIZE="${SIZE//[.,]/}"
    IMAGE_NAME="${URL##*/}"

    mapfile -t p < <(parse_image_name "$IMAGE_NAME")
    VER="${p[0]:-}"; BOARD="${p[1]:-}"; DISTRO="${p[2]:-}"; BRANCH="${p[3]:-}"
    VARIANT="${p[4]:-server}"; APP="${p[5]:-}"; STORAGE="${p[6]:-}"

    # Extract kernel version by splitting filename and getting the appropriate field
    # Standard: Armbian_24.11.1_Board_Distro_Branch_Kernel_... (kernel at index 5)
    # Community: Armbian_community_Version_Board_Distro_Branch_Kernel_... (kernel at index 6)
    KERNEL_VERSION=""
    IFS='_' read -r -a f <<< "$IMAGE_NAME"
    if [[ "${f[1]:-}" =~ ^[0-9]+\.[0-9] ]]; then
      # Version token at position 1 (standard images)
      KERNEL_VERSION="${f[5]:-}"
    else
      # Version token at position 2 (community images with prefix)
      KERNEL_VERSION="${f[6]:-}"
    fi
    # Strip any suffixes: variants (e.g., "6.6.62-gnome" -> "6.6.62")
    # and file extensions (e.g., "6.6.62.img.xz" -> "6.6.62")
    KERNEL_VERSION="${KERNEL_VERSION%%-*}"
    # Strip .img* suffix only if present (doesn't affect version numbers with dots)
    KERNEL_VERSION="${KERNEL_VERSION%.img*}"

    [[ -z "$BOARD" ]] && continue
    BOARD_SLUG="${BOARD,,}"

    REPO="$(get_download_repository "$URL")"
    [[ -z "$REPO" ]] && continue

    PREFIX=""; [[ "$REPO" == "os" ]] && PREFIX="nightly/"

    BASE_EXT="$(extract_file_extension "$IMAGE_NAME")"
    if [[ -n "$STORAGE" ]]; then
      FILE_EXTENSION="${STORAGE}.${BASE_EXT}"
    else
      FILE_EXTENSION="$BASE_EXT"
    fi

    APP_SUFFIX=""; [[ -n "$APP" ]] && APP_SUFFIX="-${APP}"

    # REDI URL "branch segment" is derived from artifact type (qcow2 => cloud)
    REDI_BRANCH="$BRANCH"
    REDI_VARIANT="$VARIANT${APP_SUFFIX}"

    # Boot "flavor" suffix comes from FILE_EXTENSION like "boe.img.xz"
    BOOT_SUFFIX=""
    case "$FILE_EXTENSION" in
      *.img.*)
        BOOT_SUFFIX="${FILE_EXTENSION%%.img.*}"   # e.g. "boe" from "boe.img.xz"
        ;;
    esac
    # ignore non-boot pseudo prefixes
    case "$BOOT_SUFFIX" in
      ""|img|oowow) BOOT_SUFFIX="";;
    esac

    # U-Boot ROM suffix
    UBOOT_ROM_SUFFIX=""
    [[ "$FILE_EXTENSION" == u-boot.rom* ]] && UBOOT_ROM_SUFFIX="u-boot-rom"

    # U-Boot artifacts should show up as "-boot" in REDI_URL
    UBOOT_SUFFIX=""
    if [[ "$FILE_EXTENSION" == u-boot.bin* ]]; then
      UBOOT_SUFFIX="boot"
    fi

    if [[ "$FILE_EXTENSION" == img.qcow2* ]]; then
      REDI_VARIANT="${VARIANT}-qcow2"
    elif [[ "$FILE_EXTENSION" == hyperv.zip* ]]; then
      REDI_VARIANT="${VARIANT}-hyperv"
    else
      # Append boot flavor for non-cloud images
      [[ -n "$BOOT_SUFFIX" ]] && REDI_VARIANT="${REDI_VARIANT}-${BOOT_SUFFIX}"
      [[ -n "$UBOOT_SUFFIX" ]] && REDI_VARIANT="${REDI_VARIANT}-${UBOOT_SUFFIX}"
      [[ -n "$UBOOT_ROM_SUFFIX" ]] && REDI_VARIANT="${REDI_VARIANT}-${UBOOT_ROM_SUFFIX}"
    fi

    REDI_URL="https://dl.armbian.com/${PREFIX}${BOARD_SLUG}/${DISTRO^}_${REDI_BRANCH}_${REDI_VARIANT}"

    # file_url must remain the original URL (GitHub Releases for community/os/distribution)
    FILE_URL="$URL"

    if [[ "$URL" == https://github.com/armbian/* ]]; then
      CACHE="https://cache.armbian.com/artifacts/${BOARD_SLUG}/archive/${IMAGE_NAME}"
      ASC="${CACHE}.asc"
      SHA="${CACHE}.sha"
      TOR="${CACHE}.torrent"
    else
      ASC="${URL}.asc"
      SHA="${URL}.sha"
      TOR="${URL}.torrent"
    fi
    PROMOTED=false
    if is_promoted "$IMAGE_NAME" "$BOARD_SLUG" "$URL"; then
      PROMOTED=true
    fi

    BOARD_VENDOR="${BOARD_VENDOR_MAP[$BOARD_SLUG]:-}"
    BOARD_SUPPORT="${BOARD_SUPPORT_MAP[$BOARD_SLUG]:-}"
    COMPANY_KEY="${BOARD_VENDOR,,}"
    C_NAME=""
    C_WEB=""
    if [[ -n "$COMPANY_KEY" ]]; then
      C_NAME="${COMPANY_NAME_BY_SLUG[$COMPANY_KEY]:-}"
      C_WEB="${COMPANY_WEBSITE_BY_SLUG[$COMPANY_KEY]:-}"
    fi

    C_LOGO=""
    if [[ -n "$BOARD_VENDOR" ]]; then
      C_LOGO="https://cache.armbian.com/images/vendors/150/${BOARD_VENDOR}.png"
    fi

    PLAT_UNTIL="${PLATINUM_UNTIL_BY_BOARD[$BOARD_SLUG]:-}"

    PLAT="false"
    PLAT_EXPIRED="false"
    if [[ -n "$PLAT_UNTIL" ]]; then
      if [[ "$PLAT_UNTIL" < "$TODAY_UTC" ]]; then
        PLAT="false"
        PLAT_EXPIRED="true"
      else
        PLAT="true"
        PLAT_EXPIRED="false"
      fi
    fi
    echo "${BOARD_SLUG}|${BOARD_NAME_MAP[$BOARD_SLUG]:-}|${BOARD_VENDOR}|${BOARD_SUPPORT}|${C_NAME}|${C_WEB}|${C_LOGO}|${VER}|${FILE_URL}|${ASC}|${SHA}|${TOR}|${REDI_URL}|${REDI_URL}.asc|${REDI_URL}.sha|${REDI_URL}.torrent|${IMAGE_SIZE}|${DATE}|${DISTRO}|${BRANCH}|${VARIANT}|${APP}|${PROMOTED}|${REPO}|${FILE_EXTENSION}|${KERNEL_VERSION}|${PLAT}|${PLAT_EXPIRED}|${PLAT_UNTIL}"

    # Check if this board is used by any reusable boards
    for reusable_slug in "${!REUSABLE_BOARD_USES[@]}"; do
      base_slug="${REUSABLE_BOARD_USES[$reusable_slug]}"

      # Match if this board is the base board
      if [[ "$BOARD_SLUG" == "$base_slug" ]]; then
        branch_filter="${REUSABLE_BOARD_BRANCH[$reusable_slug]:-}"
        ext_filter="${REUSABLE_BOARD_EXT[$reusable_slug]:-}"

        # Apply branch filter if specified
        if [[ -n "$branch_filter" && "$BRANCH" != "$branch_filter" ]]; then
          continue
        fi

        # Apply file extension filter if specified
        if [[ -n "$ext_filter" ]]; then
          # Remove leading dot if present for matching
          ext_filter="${ext_filter#.}"
          current_ext="${FILE_EXTENSION#.}"
          if [[ "$current_ext" != "$ext_filter" ]]; then
            continue
          fi
        fi

        # Get reusable board metadata
        reusable_meta="${REUSABLE_BOARD_META[$reusable_slug]}"
        IFS='|' read -r reusable_name reusable_vendor reusable_support <<< "$reusable_meta"

        # Use reusable board's vendor for company lookup
        reusable_company_key="${reusable_vendor,,}"
        reusable_c_name=""
        reusable_c_web=""
        if [[ -n "$reusable_company_key" ]]; then
          reusable_c_name="${COMPANY_NAME_BY_SLUG[$reusable_company_key]:-}"
          reusable_c_web="${COMPANY_WEBSITE_BY_SLUG[$reusable_company_key]:-}"
        fi

        reusable_c_logo=""
        if [[ -n "$reusable_vendor" ]]; then
          reusable_c_logo="https://cache.armbian.com/images/vendors/150/${reusable_vendor}.png"
        fi

        # Get platinum support for reusable board
        reusable_plat_until="${PLATINUM_UNTIL_BY_BOARD[$reusable_slug]:-}"
        reusable_plat="false"
        reusable_plat_expired="false"
        if [[ -n "$reusable_plat_until" ]]; then
          if [[ "$reusable_plat_until" < "$TODAY_UTC" ]]; then
            reusable_plat="false"
            reusable_plat_expired="true"
          else
            reusable_plat="true"
            reusable_plat_expired="false"
          fi
        fi

        # Update REDI URL with reusable board slug
        reusable_redi_url="https://dl.armbian.com/${PREFIX}${reusable_slug}/${DISTRO^}_${REDI_BRANCH}_${REDI_VARIANT}"

        # Update cache URLs for GitHub releases
        reusable_asc="$ASC"
        reusable_sha="$SHA"
        reusable_tor="$TOR"
        if [[ "$URL" == https://github.com/armbian/* ]]; then
          reusable_cache="https://cache.armbian.com/artifacts/${reusable_slug}/archive/${IMAGE_NAME}"
          reusable_asc="${reusable_cache}.asc"
          reusable_sha="${reusable_cache}.sha"
          reusable_tor="${reusable_cache}.torrent"
        fi

        # Check if reusable board image should be promoted
        reusable_promoted=false
        if is_promoted "$IMAGE_NAME" "$reusable_slug" "$URL"; then
          reusable_promoted=true
        fi

        # Output for reusable board
        echo "${reusable_slug}|${reusable_name}|${reusable_vendor}|${reusable_support}|${reusable_c_name}|${reusable_c_web}|${reusable_c_logo}|${VER}|${FILE_URL}|${reusable_asc}|${reusable_sha}|${reusable_tor}|${reusable_redi_url}|${reusable_redi_url}.asc|${reusable_redi_url}.sha|${reusable_redi_url}.torrent|${IMAGE_SIZE}|${DATE}|${DISTRO}|${BRANCH}|${VARIANT}|${APP}|${reusable_promoted}|${REPO}|${FILE_EXTENSION}|${KERNEL_VERSION}|${reusable_plat}|${reusable_plat_expired}|${reusable_plat_until}"
      fi
    done
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