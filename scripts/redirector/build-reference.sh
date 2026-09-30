#!/usr/bin/env bash
#
# Build the reference MANIFEST for one platform from the source of truth.
#
# The manifest is a small fingerprint, not a mirrored tree, so check-mirror.sh
# can compare a mirror with plain per-file GET/HEAD instead of an lftp directory
# mirror. That matters because a large share of the fleet disables directory
# autoindex (403 on a directory but serves the files fine) — those mirrors could
# never be listed and so were always mis-reported as "not in sync".
#
# Manifest formats (TAB-separated), written to  ref/manifest.tsv :
#   dists    (apt|beta)   : <suite>   <TAB> <content fingerprint of dists/<suite>/InRelease>
#   torrents (dl|archive) : <relpath> <TAB> <size-bytes>
#   noop     (cache)      : a single "noop" line (never read)
#
# APT sync compares every suite's content fingerprint (apt-index-fingerprint.sh):
# the package index checksums, not the file hash. A publish that changes nothing
# does not flag mirrors, and a change in one suite (say jammy-desktop) is caught
# even when the other suites are unchanged. $APT_REF_SUITE pins a single suite.
#
# Usage: build-reference.sh <platform> <source_of_truth_base_url>
#   platform: beta | apt | dl | archive | cache
set -euo pipefail

# shellcheck source=scripts/redirector/apt-index-fingerprint.sh
source "$(dirname "${BASH_SOURCE[0]}")/apt-index-fingerprint.sh"

platform="${1:?platform (beta|apt|dl|archive|cache) required}"
src="${2:?source-of-truth base URL required}"
src="${src%/}"

out="ref"
mkdir -p "${out}"
: > "${out}/manifest.tsv"

CURL=(curl -fsSL --connect-timeout 15 --max-time 90 --retry 3 --retry-delay 5 --retry-connrefused)
retry() { local n=0; until "$@"; do n=$((n+1)); ((n >= 3)) && return 1; sleep $((n * 5)); done; }

# GET a suite's index body: InRelease (signed) preferred, else Release. Empty on miss.
fetch_index() { # <base> <suite>
	local f body
	for f in InRelease Release; do
		if body="$("${CURL[@]}" "${1}/${2}/${f}" 2>/dev/null)" && [[ -n "${body}" ]]; then
			printf '%s' "${body}"; return 0
		fi
	done
	return 1
}

case "${platform}" in
	beta|apt)
		base="${src}/${platform}/dists"
		listing="$("${CURL[@]}" "${base}/")" \
			|| { echo "build-reference: cannot list ${base}/" >&2; exit 1; }
		# suite dirs only: href="./bookworm/" etc. Drop by-hash and parent links.
		suites="$(grep -oiE 'href="\./[^"/]+/"' <<<"${listing}" \
			| sed -E 's#.*href="\./([^"/]+)/".*#\1#' \
			| grep -viE '^(by-hash)$' | LC_ALL=C sort -u)"
		[[ -n "${suites}" ]] || { echo "build-reference: no suites under ${base}/" >&2; exit 1; }

		# Fetch each suite's index once; keep its content fingerprint.
		declare -A SHA
		while read -r s; do
			[[ -n "${s}" ]] || continue
			body="$(fetch_index "${base}" "${s}")" || { echo "build-reference: ${platform}/${s} has no InRelease/Release — skipped" >&2; continue; }
			SHA["${s}"]="$(printf '%s' "${body}" | apt_index_fingerprint)"
		done <<<"${suites}"
		[[ "${#SHA[@]}" -gt 0 ]] || { echo "build-reference: no suite has a readable index under ${base}/" >&2; exit 1; }

		# Every suite, unless APT_REF_SUITE pins one.
		want="${APT_REF_SUITE:-all}"
		selected=()
		if [[ "${want}" == "all" ]]; then
			mapfile -t selected < <(printf '%s\n' "${!SHA[@]}" | LC_ALL=C sort)
		else
			[[ -n "${SHA[${want}]:-}" ]] || { echo "build-reference: pinned APT_REF_SUITE='${want}' not found / no index" >&2; exit 1; }
			selected=("${want}")
		fi

		for s in "${selected[@]}"; do
			printf '%s\t%s\n' "${s}" "${SHA[${s}]}" >> "${out}/manifest.tsv"
		done
		echo "build-reference: ${platform} suites: ${selected[*]}" >&2
		;;

	dl|archive)
		# Images: no single fingerprint file, but the .torrent files are small and
		# their image filenames are immutable + versioned. Mirror just the torrents
		# from the (listable) source and record each one's relative path + byte size;
		# the mirror check HEAD-compares Content-Length — no download, no listing.
		mkdir -p src_tree
		( cd src_tree && retry lftp -e "mirror --include-glob=*/archive/*.torrent --parallel=64; quit" "${src}/${platform}" )
		( cd src_tree && find . -type f -name '*.torrent' -printf '%P\t%s\n' | LC_ALL=C sort ) > "${out}/manifest.tsv"
		[[ -s "${out}/manifest.tsv" ]] \
			|| { echo "build-reference: no torrents mirrored from ${src}/${platform}" >&2; exit 1; }
		;;

	cache)
		echo "noop" > "${out}/manifest.tsv"
		;;

	*)
		echo "build-reference: unknown platform '${platform}'" >&2
		exit 2
		;;
esac

echo "build-reference: ${platform} -> $(wc -l < "${out}/manifest.tsv") manifest entries"
