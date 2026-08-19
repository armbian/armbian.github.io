#!/usr/bin/env bash
#
# Compare one mirror server against the reference index and classify it.
# Writes a single status file  status/<id>  whose first line is one of:
#
#   true          - reachable AND identical to the reference
#   not_in_sync   - reachable but differs, or unreachable / no index
#   timeout       - the mirror pull hit the 3-minute cap
#
# For not_in_sync / timeout a second line carries the server, so the summary
# step can list it.
#
# Usage: check-mirror.sh <server> <check-type> <reference-dir> <id>
#   check-type: dists | torrents | noop
#
# This replaces five copy-pasted inline blocks and fixes their shared bug:
# `exit_status` was used uninitialised and only some variants set it (debs-beta
# used `|| true`), so out-of-sync / timeout servers were silently dropped.
set -uo pipefail

server="${1:?server (host/path) required}"
check="${2:?check type required}"
reference_dir="${3:?reference dir required}"
id="${4:?server id required}"

mkdir -p status compare

# 0 = pull ok, 124 = timeout, anything else = pull error. Initialised so the
# classification is well-defined even when the mirror is unreachable.
exit_status=0
# Whether the mirror answered at all. An unreachable mirror leaves compare/
# empty, which would diff clean against an empty reference and be published as
# healthy - so reachability is tracked explicitly rather than inferred.
reached=0

case "${check}" in
	noop)
		# Cache mirrors aren't index-compared; they're always considered in sync.
		echo "true" > "status/${id}"
		exit 0
		;;

	dists)
		# APT repositories: mirror the dists/ tree and diff it.
		if curl -o /dev/null -sfI "https://${server}/dists/"; then
			reached=1
			( cd compare && timeout 3m lftp -e "mirror --parallel=16; exit" "https://${server}/dists/" ) \
				|| exit_status=$?
		fi
		;;

	torrents)
		# Image repositories: mirror only the archive/*.torrent files.
		mkdir -p source
		if curl -o /dev/null -sfI "https://${server}"; then
			reached=1
			( cd source && timeout 3m lftp -e "mirror --include-glob=*/archive/*.torrent --parallel=64; exit" "https://${server}" ) \
				|| exit_status=$?
			# -f, not -i: with no tty an interactive prompt reads EOF and silently
			# declines the move. Errors stay on stderr so a real failure is visible.
			find source/*/archive/ -mindepth 1 -maxdepth 1 -exec mv -f -- {} compare/ \; || true
		fi
		;;

	*)
		echo "check-mirror: unknown check type '${check}'" >&2
		exit 2
		;;
esac

# An empty reference means the index job produced nothing: every mirror would
# then diff clean and the whole fleet would be published as in sync. Refuse.
if [[ -z "$(find "${reference_dir}" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
	echo "check-mirror: reference dir '${reference_dir}' is empty - refusing to classify ${server}" >&2
	printf '%s\n%s\n' "not_in_sync" "${server}" > "status/${id}"
	exit 0
fi

# In sync only when the mirror answered AND its content matches the reference.
if [[ "${reached}" -eq 1 && -z "$(diff -rq compare "${reference_dir}" 2>/dev/null || true)" ]]; then
	echo "true" > "status/${id}"
elif [[ "${exit_status}" -eq 124 ]]; then
	printf '%s\n%s\n' "timeout" "${server}" > "status/${id}"
else
	printf '%s\n%s\n' "not_in_sync" "${server}" > "status/${id}"
fi
