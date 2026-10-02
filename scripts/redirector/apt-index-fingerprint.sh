# shellcheck shell=bash
# Content fingerprint of an APT suite, for build-reference.sh and check-mirror.sh.
#
# A publish rewrites every suite's InRelease: new Date, new signature, new file
# hash, even when no package changed. So compare the index list inside it
# instead: the SHA256 section lists the checksum of every Packages/Sources file.
# It changes only when the content of that suite changes.
#
# Reads an InRelease or Release body on stdin. Prints one sha256. Falls back to
# the whole body when the index has no SHA256 section.
apt_index_fingerprint() {
	local body entries
	body="$(cat)"
	entries="$(awk '/^SHA256:/ { s = 1; next } s && /^ / { print; next } { s = 0 }' <<<"${body}" | LC_ALL=C sort)"
	[[ -n "${entries}" ]] || entries="${body}"
	printf '%s' "${entries}" | sha256sum | awk '{print $1}'
}
