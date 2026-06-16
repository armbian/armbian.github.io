#!/usr/bin/env bash
set -euo pipefail

# Validate images:
# - board-images/: 16:9 AND either 1920x1080 or 3840x2160, TRANSPARENT background,
#   and (optional) object not larger than MAX_OBJECT_PCT of the frame
# - board-vendor-logos/: must be square (WxH equal)
#
# On a PR only the changed assets are checked; on schedule/workflow_dispatch the
# WHOLE set is checked. Requires ImageMagick's `identify`/`convert`.
#
# env: MAX_OBJECT_PCT (int) — if set, fail a board image whose opaque-pixel fill
#      exceeds this %. Unset = report only (board images currently fill 5–48%).

BASE_REF="${BASE_REF:-origin/${GITHUB_BASE_REF:-main}}"
HEAD_REF="${HEAD_REF:-HEAD}"

# Fetch base ref if needed (useful on CI with shallow clones)
git fetch --no-tags --prune --depth=50 origin "+refs/heads/*:refs/remotes/origin/*" >/dev/null 2>&1 || true

# On a PR, validate only the changed assets. On schedule / workflow_dispatch /
# local (no PR base ref) validate EVERY asset, so the monthly run actually checks
# the whole set instead of an empty diff.
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  mapfile -t CHANGED < <(git diff --name-only "${BASE_REF}...${HEAD_REF}" -- \
    'board-images/**' 'board-vendor-logos/**' || true)
  echo "Mode: changed files (PR vs ${GITHUB_BASE_REF})"
else
  mapfile -t CHANGED < <(find board-images board-vendor-logos -type f | sort)
  echo "Mode: all assets"
fi

if [[ ${#CHANGED[@]} -eq 0 ]]; then
  echo "No board-images/ or board-vendor-logos/ files to validate. ✅"
  exit 0
fi

# Filter to image files we can validate
VALID_EXT_RE='\.(png|jpg|jpeg|webp)$'
FILES=()
for f in "${CHANGED[@]}"; do
  [[ "$f" =~ $VALID_EXT_RE ]] || continue
  [[ -f "$f" ]] || continue
  FILES+=("$f")
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No supported image files changed (png/jpg/jpeg/webp). ✅"
  exit 0
fi

if ! command -v identify >/dev/null 2>&1; then
  echo "ERROR: 'identify' not found. Install ImageMagick."
  exit 2
fi

# Background is transparent iff there's an alpha channel AND all four corners are
# (near) fully transparent. Returns 0 when transparent.
bg_transparent() {
  local f="$1" a tl tr bl br
  a="$(identify -format '%A' "$f" 2>/dev/null || echo None)"
  case "$a" in True|Blend|true|blend) : ;; *) return 1 ;; esac
  tl=$(convert "$f" -format '%[fx:p{0,0}.a]'     info: 2>/dev/null || echo 1)
  tr=$(convert "$f" -format '%[fx:p{w-1,0}.a]'   info: 2>/dev/null || echo 1)
  bl=$(convert "$f" -format '%[fx:p{0,h-1}.a]'   info: 2>/dev/null || echo 1)
  br=$(convert "$f" -format '%[fx:p{w-1,h-1}.a]' info: 2>/dev/null || echo 1)
  awk -v a="$tl" -v b="$tr" -v c="$bl" -v d="$br" \
    'BEGIN{exit !(a<0.04 && b<0.04 && c<0.04 && d<0.04)}'
}

# Object fill = % of the canvas that is opaque (non-transparent) pixels.
object_fill_pct() {
  convert "$1" -alpha extract -format '%[fx:round(mean*100)]' info: 2>/dev/null || echo 100
}

fail=0

check_board_image() {
  local file="$1"
  local w h
  read -r w h < <(identify -format '%w %h' "$file" 2>/dev/null || echo "0 0")

  if [[ "$w" -le 0 || "$h" -le 0 ]]; then
    echo "❌ $file: could not read dimensions"
    return 1
  fi

  # Must be exact 16:9 -> w*9 == h*16
  if [[ $(( w * 9 )) -ne $(( h * 16 )) ]]; then
    echo "❌ $file: must be 16:9 (got ${w}x${h})"
    return 1
  fi

  if ! { [[ "$w" -eq 1920 && "$h" -eq 1080 ]] || [[ "$w" -eq 3840 && "$h" -eq 2160 ]]; }; then
    echo "❌ $file: must be 1920x1080 or 3840x2160 (got ${w}x${h})"
    return 1
  fi

  # Background must be transparent (board photo cut out, not a flat backdrop).
  if ! bg_transparent "$file"; then
    echo "❌ $file: background must be transparent (no alpha channel or opaque corners)"
    return 1
  fi

  # Object size: report the opaque-pixel fill %, and fail only if a limit is set.
  local fill
  fill=$(object_fill_pct "$file")
  if [[ -n "${MAX_OBJECT_PCT:-}" && "$fill" -gt "${MAX_OBJECT_PCT}" ]]; then
    echo "❌ $file: object too large — fills ${fill}% of the frame (max ${MAX_OBJECT_PCT}%)"
    return 1
  fi

  echo "✅ $file: OK (${w}x${h}, transparent, object ${fill}%)"
  return 0
}

check_vendor_logo() {
  local file="$1"
  local w h
  read -r w h < <(identify -format '%w %h' "$file" 2>/dev/null || echo "0 0")

  if [[ "$w" -le 0 || "$h" -le 0 ]]; then
    echo "❌ $file: could not read dimensions"
    return 1
  fi

  if [[ "$w" -ne "$h" ]]; then
    echo "❌ $file: vendor logos must be square (got ${w}x${h})"
    return 1
  fi

  echo "✅ $file: OK (${w}x${h})"
  return 0
}

echo "Validating ${#FILES[@]} image(s)..."
for f in "${FILES[@]}"; do
  if [[ "$f" == board-images/* ]]; then
    check_board_image "$f" || fail=1
  elif [[ "$f" == board-vendor-logos/* ]]; then
    check_vendor_logo "$f" || fail=1
  else
    # Shouldn't happen because of the diff filter, but keep it safe.
    echo "Skipping unrelated file: $f"
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo ""
  echo "Image validation failed. Please resize/crop the files to match the rules above."
  exit 1
fi

echo "All image validations passed. ✅"
