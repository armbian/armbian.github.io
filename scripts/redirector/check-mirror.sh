#!/usr/bin/env bash
#
# Compare one mirror against the reference MANIFEST and classify it. Writes a
# single status file  status/<id>  whose first line is one of:
#
#   true          - reachable AND matches the reference
#   not_in_sync   - reachable but differs (stale / missing files), or unreachable
#   timeout       - the mirror answered nothing before the time cap
#
# For not_in_sync / timeout a second line carries the server, for the summary.
# For a stale apt mirror a third line lists the stale suites.
#
# Every probe is a plain per-file GET/HEAD. Unlike an lftp directory mirror this
# needs NO directory autoindex on the mirror (a 403 on a directory blocks
# listing, not file serving), so mirrors that disable autoindex are classified
# on their actual content instead of being written off as unreachable.
#
# A fast reachability gate runs first: any HTTP response (even 403/404) means the
# host is up; a host that answers nothing is classified without hammering every
# file, so one unreachable mirror can't run out the job's time budget.
#
# Reference manifest (built by build-reference.sh), TAB-separated:
#   dists    : <suite>   <TAB> <content fingerprint of dists/<suite>/InRelease>
#   torrents : <relpath> <TAB> <size-bytes>
#
# Usage: check-mirror.sh <server> <check-type> <reference-dir> <id>
#   check-type: dists | torrents | noop
set -uo pipefail

# shellcheck source=scripts/redirector/apt-index-fingerprint.sh
source "$(dirname "${BASH_SOURCE[0]}")/apt-index-fingerprint.sh"

server="${1:?server (host/path) required}"
check="${2:?check type required}"
reference_dir="${3:?reference dir required}"
id="${4:?server id required}"

mkdir -p status
manifest="${reference_dir}/manifest.tsv"

# Trim any stray trailing slash so https://<server>/<path> never becomes '//'.
server="${server%/}"
base="https://${server}"

stale=""
classify() { printf '%s\n%s\n%s' "$1" "${server}" "${stale:+${stale}
}" > "status/${id}"; exit 0; }

# Cache: not content-compared, always in sync.
[[ "${check}" == "noop" ]] && { echo "true" > "status/${id}"; exit 0; }

# A missing/empty manifest means the reference job produced nothing; refusing to
# classify is safer than diffing against emptiness and publishing the fleet.
if [[ ! -s "${manifest}" ]]; then
	echo "check-mirror: empty/missing manifest '${manifest}' - refusing to classify ${server}" >&2
	classify not_in_sync
fi

: "${PROBE_PARALLEL:=24}"     # concurrent probes for the torrents check
: "${CONNECT_TIMEOUT:=8}"     # TCP/TLS connect cap (down hosts fail fast)
: "${PROBE_TIMEOUT:=15}"      # per-request total cap
# Overall wall-clock budget for the whole check. It MUST stay well under the
# job's timeout-minutes: a job killed by GitHub's cap is reported "cancelled",
# which poisons the run conclusion and skips the publish. Instead we stop on time
# and record a "timeout" verdict for this one mirror, so its job still succeeds
# and the rest of the run proceeds. A single slow mirror can never break the run.
: "${CHECK_BUDGET:=300}"
: "${TRANSIENT_MAX_PCT:=5}"   # torrents: share of probes allowed to fail transiently
deadline=$(( $(date +%s) + CHECK_BUDGET ))
hit_deadline=0

# Reachability gate: does the host give ANY HTTP response? Returns the curl exit
# code via a global, so a pure timeout can be told from a refusal/DNS failure.
gate_rc=0
reachable() { # <url>
	local code
	code="$(curl -sSL -o /dev/null --connect-timeout "${CONNECT_TIMEOUT}" --max-time "${PROBE_TIMEOUT}" \
		-w '%{http_code}' "$1" 2>/dev/null)"
	gate_rc=$?
	[[ "${code}" =~ ^[0-9]+$ && "${code}" -ge 100 ]]
}

gate="${base}/dists/"
[[ "${check}" == "torrents" ]] && gate="${base}/"
if ! reachable "${gate}"; then
	# No HTTP response at all. Distinguish a slow (timeout) mirror from a dead one.
	[[ "${gate_rc}" -eq 28 ]] && classify timeout
	classify not_in_sync
fi

case "${check}" in
	dists)
		# Compare every manifest suite's content fingerprint. The gate proved the
		# host answers, so a suite without an index is missing: stale.
		bad=0
		while IFS=$'\t' read -r suite refsha; do
			[[ -n "${suite}" ]] || continue
			if (( $(date +%s) > deadline )); then hit_deadline=1; break; fi
			got=""
			for f in InRelease Release; do
				if body="$(curl -fsSL --connect-timeout "${CONNECT_TIMEOUT}" --max-time "${PROBE_TIMEOUT}" \
					"${base}/dists/${suite}/${f}" 2>/dev/null)" && [[ -n "${body}" ]]; then
					got="$(printf '%s' "${body}" | apt_index_fingerprint)"; break
				fi
			done
			if [[ -z "${got}" || "${got}" != "${refsha}" ]]; then
				bad=1; stale+="${stale:+ }${suite}"
			fi
		done < "${manifest}"
		[[ -n "${stale}" ]] && echo "check-mirror: ${server} stale suites: ${stale}" >&2
		;;

	torrents)
		# HEAD each torrent and compare Content-Length to the reference. The files
		# are immutable and versioned, so a matching size on a present file is a
		# strong "has this exact artifact" signal without downloading it. Probe in
		# bounded parallel; one result token per line.
		#
		# A file the mirror does not serve (401/403/404/410) or a size mismatch
		# puts the mirror out of sync. A transient error (timeout, reset, 5xx) is
		# retried once and tolerated up to TRANSIENT_MAX_PCT of the probes; above
		# that the result is unproven, so the mirror is reported as timeout.
		res="$(mktemp -d)"; trap 'rm -rf "${res}"' EXIT
		probe() { # <relpath> <refsize> <slot>
			local rel="$1" refsize="$2" slot="$3" out code size attempt
			for attempt in 1 2; do
				out="$(curl -sSL -I --connect-timeout "${CONNECT_TIMEOUT}" --max-time "${PROBE_TIMEOUT}" \
					-o /dev/null -w '%{http_code} %header{content-length}' "${base}/${rel}" 2>/dev/null)"
				code="${out%% *}"; size="${out#* }"
				case "${code}" in
					200) [[ "${size}" == "${refsize}" ]] && echo ok > "${res}/${slot}" || echo mismatch > "${res}/${slot}"; return ;;
					401|403|404|410) echo missing > "${res}/${slot}"; return ;;
					*)   [[ ${attempt} -lt 2 ]] && sleep 1 ;;   # 000/5xx/timeout -> transient, one retry
				esac
			done
			echo transient > "${res}/${slot}"
		}
		slot=0; running=0
		while IFS=$'\t' read -r rel refsize; do
			[[ -n "${rel}" ]] || continue
			# Stop launching once the budget is spent; in-flight probes drain below.
			if (( $(date +%s) > deadline )); then hit_deadline=1; break; fi
			probe "${rel}" "${refsize}" "${slot}" &
			slot=$((slot + 1)); running=$((running + 1))
			(( running % PROBE_PARALLEL == 0 )) && wait
		done < "${manifest}"
		wait

		bad=0; probes=0; transient=0
		for f in "${res}"/*; do
			[[ -f "${f}" ]] || continue
			probes=$((probes + 1))
			case "$(cat "${f}")" in
				missing|mismatch) bad=1 ;;
				transient)        transient=$((transient + 1)) ;;
			esac
		done
		if (( probes > 0 && transient * 100 > probes * TRANSIENT_MAX_PCT )); then
			echo "check-mirror: ${server} ${transient}/${probes} probes failed transiently" >&2
			hit_deadline=1
		fi
		;;

	*)
		echo "check-mirror: unknown check type '${check}'" >&2
		exit 2
		;;
esac

# The host answered the gate, so it is reachable. A definitive miss/mismatch means
# stale; otherwise, if we ran out of budget before finishing, report timeout (the
# job still succeeds); else in sync.
if [[ "${bad}" -ne 0 ]]; then
	classify not_in_sync
elif [[ "${hit_deadline}" -ne 0 ]]; then
	classify timeout
else
	echo "true" > "status/${id}"
fi
