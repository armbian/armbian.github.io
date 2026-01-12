#!/bin/bash
set -e
set -o pipefail

# Sync repository script
# Usage: sync-repository.sh <sync_type>
# sync_type: "files" (sync packages only) or "index" (sync everything with cleanup)

SYNC_TYPE="${1:-files}"

# Validate sync type
case "$SYNC_TYPE" in
  files|index)
    ;;
  *)
    echo "::error::Invalid sync type: $SYNC_TYPE (must be 'files' or 'index')"
    exit 1
    ;;
esac

# Use server configuration from matrix (fetched and validated in Prepare job)
HOSTNAME="${MATRIX_NODE_NAME}"
SERVER_PATH="${MATRIX_NODE_PATH}"
SERVER_PORT="${MATRIX_NODE_PORT}"
SERVER_USERNAME="${MATRIX_NODE_USERNAME}"

echo "### Server: $HOSTNAME ($SYNC_TYPE)" | tee -a "$GITHUB_STEP_SUMMARY"
echo "  Path: $SERVER_PATH" | tee -a "$GITHUB_STEP_SUMMARY"
echo "  Port: $SERVER_PORT" | tee -a "$GITHUB_STEP_SUMMARY"
echo "  Username: $SERVER_USERNAME" | tee -a "$GITHUB_STEP_SUMMARY"
echo ""

# Fetch targets from NetBox API (need tags for determining sync targets)
API_URL="${NETBOX_API}/virtualization/virtual-machines/?limit=500&name__empty=false&name=${HOSTNAME}"

response=$(curl -fsSL \
  --max-time 30 \
  --connect-timeout 10 \
  -H "Authorization: Token ${NETBOX_TOKEN}" \
  -H "Accept: application/json" \
  "$API_URL" 2>&1) || exit 1

# Extract targets from tags
TARGETS=($(echo "$response" | jq -r '.results[] | .tags[] | .name' 2>/dev/null | grep -v "Push" || echo ""))

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "::warning::No targets found for $HOSTNAME"
  exit 0
fi

# Filter to only valid targets
VALID_TARGETS=()
for target in "${TARGETS[@]}"; do
  case "$target" in
    debs|debs-beta)
      VALID_TARGETS+=("$target")
      ;;
    *)
      echo "::warning::Invalid target '$target' for $HOSTNAME - must be 'debs' or 'debs-beta', skipping"
      ;;
  esac
done

if [[ ${#VALID_TARGETS[@]} -eq 0 ]]; then
  echo "::warning::No valid targets found for $HOSTNAME"
  exit 0
fi

TARGETS=("${VALID_TARGETS[@]}")
echo "Sync targets: ${TARGETS[*]}" | tee -a "$GITHUB_STEP_SUMMARY"
echo ""

# Set base path using global variable
PUBLISHING_PATH="${PUBLISHING_PATH}"

# Validate publishing path
case "$PUBLISHING_PATH" in
  *"/publishing/repository"*)
    ;;
  *)
    echo "::error::Invalid publishing path: $PUBLISHING_PATH"
    exit 1
    ;;
esac

# Build rsync options - add --dry-run if DRY_RUN_SYNC is enabled
RSYNC_OPTIONS="-av --omit-dir-times"
if [[ "${DRY_RUN_SYNC}" == "true" ]]; then
  RSYNC_OPTIONS="$RSYNC_OPTIONS --dry-run"
  echo "::notice::DRY_RUN_SYNC is enabled - rsync will only show what would be transferred" | tee -a "$GITHUB_STEP_SUMMARY"
  echo "" | tee -a "$GITHUB_STEP_SUMMARY"
fi

# Sync to each target
for target in "${TARGETS[@]}"; do
  if [[ "$SYNC_TYPE" == "files" ]]; then
    echo "→ Syncing $target" | tee -a "$GITHUB_STEP_SUMMARY"
  else
    echo "→ Finalizing $target" | tee -a "$GITHUB_STEP_SUMMARY"
  fi

  REPO_PATH="${PUBLISHING_PATH}-${target}"
  if [[ ! -d "$REPO_PATH/public" ]]; then
    if [[ "$target" == "debs" ]]; then
      echo "::error::Source repository path does not exist: $REPO_PATH/public"
      exit 1
    else
      echo "::warning::Repository path does not exist: $REPO_PATH/public, skipping"
      continue
    fi
  fi

  DEST_PATH="${SERVER_PATH}/$(echo "$target" | sed 's/debs-beta$/beta/;s/^debs$/apt/')"

  if [[ "$SYNC_TYPE" == "files" ]]; then
    # First sync: packages only, exclude dists and control
    rsync $RSYNC_OPTIONS -e "ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30" \
      --exclude "dists" --exclude "control" \
      "$REPO_PATH/public/" \
      ${SERVER_USERNAME}@${HOSTNAME}:"${DEST_PATH}"
  else
    # Second sync: everything including indices, with cleanup
    rsync $RSYNC_OPTIONS -e "ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30" \
      "$REPO_PATH/public/" \
      ${SERVER_USERNAME}@${HOSTNAME}:"${DEST_PATH}"

    # Cleanup sync with --delete
    rsync $RSYNC_OPTIONS --delete -e "ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30" \
      "$REPO_PATH/public/" \
      ${SERVER_USERNAME}@${HOSTNAME}:"${DEST_PATH}"
  fi
done

echo "" | tee -a "$GITHUB_STEP_SUMMARY"
if [[ "$SYNC_TYPE" == "files" ]]; then
  echo "✓ Sync completed for $HOSTNAME" | tee -a "$GITHUB_STEP_SUMMARY"
else
  echo "✓ Final sync completed for $HOSTNAME" | tee -a "$GITHUB_STEP_SUMMARY"
fi
