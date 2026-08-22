#!/usr/bin/env bash
#
# Query NetBox for the active mirror servers behind each redirector variant and
# emit a single GitHub Actions matrix: a JSON array of node objects, one per
# mirror server, each carrying everything the check job needs.
#
#   { "key": "images", "reference": "dl", "check": "torrents",
#     "server": "mirror.example.com/dl", "id": "123" }
#
# "key"       - short, collision-free artifact prefix for this variant
# "reference" - which build-job reference artifact to diff against
# "check"     - how the mirror is compared (dists | torrents | noop)
# "server"    - host + download path; the check hits https://<server>/...
# "id"        - NetBox VM id, used as the status filename
#
# Replaces five near-identical inline jq/sed/xargs pipelines. Requires
# NETBOX_API and NETBOX_TOKEN in the environment.
set -euo pipefail

: "${NETBOX_API:?NETBOX_API is required}"
: "${NETBOX_TOKEN:?NETBOX_TOKEN is required}"

# The single source of truth for the redirector variants.
# key | netbox tag | download-path custom field | fallback path | reference artifact | check type
variants=$(
	cat <<-'TSV'
		debsbeta	debs-beta	download_path_debs	beta	beta	dists
		debs	debs	download_path_debs	apt	apt	dists
		images	images	download_path_images	dl	dl	torrents
		archive	archive	download_path_archive	archive	archive	torrents
		cache	cache	download_path_cache	cache	cache	noop
	TSV
)

nodes='[]'
while IFS=$'\t' read -r key tag field fallback reference check; do
	[[ -z "${key}" ]] && continue

	resp=$(curl -fsS --retry 3 --retry-delay 5 --retry-connrefused \
		-H "Authorization: Token ${NETBOX_TOKEN}" \
		-H "Accept: application/json" \
		"${NETBOX_API}/virtualization/virtual-machines/?limit=500&name__empty=false&status=active&tag=${tag}")

	# limit=500 is a cap, not a promise. If NetBox ever pages the response the
	# tail would vanish from the matrix silently and those mirrors would drop
	# out of the failover pool - so fail loudly instead.
	if [[ "$(jq -r '.next // "null"' <<<"${resp}")" != "null" ]]; then
		echo "netbox-mirrors: paginated response for tag '${tag}' ($(jq -r '.count' <<<"${resp}") results); raise the limit or follow .next" >&2
		exit 1
	fi

	# One clean jq pass per variant: server = name + "/" + download path (the
	# custom field, or the fallback when it's null/absent).
	part=$(jq -c \
		--arg key "${key}" --arg ref "${reference}" --arg check "${check}" \
		--arg field "${field}" --arg fb "${fallback}" '
		[ .results[]
		  | { key:       $key,
		      reference: $ref,
		      check:     $check,
		      server:    (.name + "/" + (.custom_fields[$field] // $fb)),
		      id:        (.id | tostring) } ]' <<<"${resp}")

	nodes=$(jq -cn --argjson a "${nodes}" --argjson b "${part}" '$a + $b')
done <<<"${variants}"

echo "${nodes}"
