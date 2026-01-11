#!/usr/bin/env bash
set -euo pipefail

# Validate images in PRs:
# - board-images/: must be 16:9 AND either 1920x1080 or 3840x2160
# - board-vendor-logos/: must be square (WxH equal)
#
# Requires ImageMagick's `identify`.

BASE_REF="${BASE_REF:-origin/${GITHUB_BASE_REF:-main}}"
HEAD_REF="${HEAD_REF:-HEAD}"

# Fetch base ref if needed (useful on CI with shallow clones)
git fetch --no-tags --prune --depth=50 origin "+refs/heads/*:refs/remotes/origin/*" >/dev/null 2>&1 || true

mapfile -t CHANGED < <(git diff --name-only "${BASE_REF}...${HEAD_REF}" -- \
  'board-images/**' 'board-vendor-logos/**' || true)

if [[ ${#CHANGED[@]} -eq 0 ]]; then
  echo "No changes in board-images/ or board-vendor-logos/. ✅"
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

  echo "✅ $file: OK (${w}x${h})"
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
