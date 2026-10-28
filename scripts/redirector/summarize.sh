#!/usr/bin/env bash
#
# Aggregate the per-server status files for one variant:
#   - append "Not in sync" / "Timeouts" lists to the job step summary
#   - export failoverserver (space-joined ids of in-sync mirrors) and a fresh
#     reloadKey to GITHUB_ENV for the redirector-config step
#
# Usage: summarize.sh [status-dir]   (default: status)
set -uo pipefail

status_dir="${1:-status}"
summary="${GITHUB_STEP_SUMMARY:-/dev/stdout}"

# status files whose first line is exactly this state; print their 2nd line (server)
list_state() {
	local state="$1"
	local f
	for f in "${status_dir}"/*; do
		[[ -f "${f}" ]] || continue
		[[ "$(sed -n '1p' "${f}")" == "${state}" ]] && sed -n '2p' "${f}"
	done
}

{
	echo "# Not in sync"
	list_state "not_in_sync"
	echo "# Timeouts"
	list_state "timeout"
} >> "${summary}"

# Failover pool = ids of mirrors reported in sync (first line == "true").
failover=""
for f in "${status_dir}"/*; do
	[[ -f "${f}" ]] || continue
	[[ "$(sed -n '1p' "${f}")" == "true" ]] && failover+="$(basename "${f}") "
done
failover="${failover% }"

# An empty pool would generate a redirector config with nowhere to send traffic.
# Fail the step instead: the previously published config stays live.
if [[ -z "${failover}" ]]; then
	echo "summarize: no in-sync mirrors found in '${status_dir}' - refusing to publish an empty failover pool" >&2
	exit 1
fi

{
	echo "failoverserver=${failover}"
	echo "reloadKey=$(openssl rand -hex 16)"
} >> "${GITHUB_ENV:-/dev/stdout}"
