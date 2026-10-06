#!/bin/bash
#
# sync_users.sh - mirror GitHub organization members to local SFTP-only accounts
#
# Every member of ORG (minus BLOCKLIST) who has a public SSH key on their
# GitHub profile gets a local account that is jailed via SFTPGROUP into the
# chroot USERPATH and can only authenticate with those keys. No key on
# GitHub, no account, no directory. Existing accounts whose keys disappear
# from GitHub keep their files but cannot log in until a key is back. When
# GitHub cannot be asked (network, rate limit, bad token) the current keys
# stay as they are: the script fails open, never closed.
# Members who left the organization (or got blocklisted) are locked; with
# --delete they are removed together with their files. Logins listed in
# KEEPLIST are treated like members no matter whether they are (still) in
# the organization: account and keys are kept in sync, never pruned.
#
# Which local accounts belong to this script is decided by the account
# database (members of SFTPGROUP), never by directory listings. Therefore
# NEVER add any other account to SFTPGROUP: everything in that group is
# subject to pruning. System accounts (uid below UID_MIN) are ignored as an
# additional safeguard.
#
# Authorized keys live in KEYS_DIR, owned by root, out of the users' reach.
# Keys inside a user-writable home would allow a chrooted user to replace
# ~/.ssh with a symlink and have this script (running as root) write their
# keys anywhere, e.g. into /root/.ssh/authorized_keys.
#
# Token: classic PAT with "read:org", or a fine-grained PAT with organization
# permission "Members: read". Concealed members are only returned when the
# token owner is a member of the organization. Provide the token via the
# environment variable GITHUB_TOKEN or in TOKEN_FILE (owned by root, mode 0600).
# A token with an expiry date is reported TOKEN_WARN_DAYS before it expires.
#
# Requirements: bash >= 4.4, curl >= 7.71, jq, flock, shadow tools.
#
# sshd_config:
#   Match Group sftponly
#       ChrootDirectory /armbianusers
#       ForceCommand internal-sftp
#       AllowTcpForwarding no
#       X11Forwarding no
#       PasswordAuthentication no
#       AuthorizedKeysFile /etc/ssh/authorized_keys.d/%u
#   Add "-d /%u" to internal-sftp to drop users into their own directory.
#
# nginx: serve USERPATH read-only, deny dotfiles:
#   location ~ /\. { deny all; }
#
# Cron example: 17 * * * * root /usr/local/sbin/sync_users.sh --yes --syslog
# Read the log with: journalctl -t sync_users  (or grep sync_users /var/log/syslog)

set -u -o pipefail
# No "set -e": every failure is handled explicitly so that one broken member
# does not abort the whole sync.

# fixed PATH: cron's default lacks /usr/sbin, and nothing relative or odd
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
umask 077

### CONFIG (defaults, override in CONFIG_FILE) ###

# chroot for all members, must be owned by root and not writable by others
USERPATH=/armbianusers

# supplementary group that marks an account as managed by this script and
# is matched by sshd to jail the session
SFTPGROUP=sftponly

# organization to read members from
ORG=armbian

# root-owned directory holding one authorized_keys file per user
KEYS_DIR=/etc/ssh/authorized_keys.d

# token file, used when GITHUB_TOKEN is not set in the environment
TOKEN_FILE=/etc/sync_users.token

# GitHub logins that never get an account. Existing accounts get pruned.
BLOCKLIST=(armbianworker)

# GitHub logins that get an account and key sync regardless of their
# membership in ORG, and are never pruned. Must not overlap with BLOCKLIST.
KEEPLIST=()

# warn when the token expires in less than this many days. 0 = never.
TOKEN_WARN_DAYS=14

# refuse to prune when more than this many accounts qualify. 0 = unlimited.
# Protects against a truncated or wrong member list wiping the server.
MAX_PRUNE=5

# must be in a directory only root can write to (/run/lock is world-writable)
LOCKFILE=/run/sync_users.lock
CONFIG_FILE=/etc/sync_users.conf

### END CONFIG ###


### DO NOT EDIT BELOW ###

DRY_RUN=0
ASSUME_YES=0
DELETE=0
DEBUG=0
SYSLOG=0
OPT_MAX_PRUNE=
CONFIG_EXPLICIT=0

CREATED=0
KEYS_WRITTEN=0
LOCKED=0
DELETED=0
UNCONFIRMED=0
ERRORS=0

# gh_get and friends return their results in globals on purpose: called as
# $(...) they would run in a subshell and lose RATE_LIMITED etc.
GH_BODY=            # body of the last successful gh_get
GH_ERROR=           # why the last gh_get failed, for messages
RATE_LIMITED=0      # GitHub throttled us, further API calls are pointless
TOKEN_CHECKED=0
BODY_TMP=
HEADERS_TMP=
ORG_MEMBERS=        # fetch_org_members: logins, one per line
FETCHED_KEYS=       # fetch_keys: validated key lines, one per line

# GitHub login that is also a valid unix user name (shadow: max 32 chars).
# valid_login() additionally requires a letter: all-digit names are looked
# up as uid by getent/chown/install and could hit a foreign account.
LOGIN_RE='^[A-Za-z0-9][A-Za-z0-9-]{0,31}$'
UID_MIN=1000
# public key types GitHub hands out: "<type> <base64>", no comment
KEY_RE='^(ssh-(rsa|ed25519)|ecdsa-sha2-nistp(256|384|521)|sk-(ssh-ed25519|ecdsa-sha2-nistp256)@openssh\.com) [A-Za-z0-9+/]{32,}={0,2}$'

usage() {
    cat <<EOF
Usage: ${0##*/} [OPTIONS]

  -c, --config FILE   config file to source (default: $CONFIG_FILE)
  -n, --dry-run       report what would be done, change nothing
  -y, --yes           prune without asking (for cron). Without a tty and
                      without --yes prune candidates are only reported and
                      the run ends with status 2.
      --delete        prune = "userdel --remove" instead of locking.
                      Removes all files of the user. CANNOT BE UNDONE.
      --max-prune N   refuse to prune more than N accounts (0 = unlimited)
  -s, --syslog        send all output to syslog (tag "sync_users") instead of
                      stdout/stderr. For cron on hosts without an MTA.
  -d, --debug         verbose output
  -h, --help          this text

Token: environment variable GITHUB_TOKEN or the file configured as TOKEN_FILE.
Exit codes: 0 ok, 1 fatal (aborted, no account touched), 2 finished, but with
            errors or with accounts left to prune.
EOF
}

log()   { printf '%s\n' "$*"; }
warn()  { printf '(!) %s\n' "$*" >&2; }
err()   { printf '(!) %s\n' "$*" >&2; ERRORS=$((ERRORS + 1)); }
die()   { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
debug() { if (( DEBUG )); then printf 'DEBUG: %s\n' "$*"; fi; }

# printable version of an untrusted string, for messages only
safe() { printf '%s' "${1//[^[:print:]]/?}"; }

# name usable as unix user and safe in every place this script uses it
valid_login() {
    [[ $1 =~ $LOGIN_RE && $1 == *[[:alpha:]]* ]]
}

# non-negative decimal integer, printed without leading zeros: bash arithmetic
# would read "010" as octal 8 and choke on "08". Length cap keeps it in 64 bit.
uint() {
    [[ $1 =~ ^[0-9]{1,15}$ ]] || return 1
    printf '%d' "$(( 10#$1 ))"
}

# run a command, or only show it in dry-run mode
run() {
    local shown
    shown=$(printf '%q ' "$@")
    if (( DRY_RUN )); then
        log "    [dry-run] ${shown% }"
        return 0
    fi
    debug "exec: ${shown% }"
    "$@"
}

# ask yes/no. 0 = yes (always in dry-run and with --yes), 1 = no,
# 2 = nobody to ask, no tty.
confirm() {
    local answer
    if (( DRY_RUN || ASSUME_YES )); then
        return 0
    fi
    if [[ ! -t 0 ]]; then
        log "$1 -> skipped, no tty"
        return 2
    fi
    read -r -n 1 -p "$1 [y/N] " answer
    echo
    [[ $answer == [yY] ]]
}


### ARGUMENTS
while (( $# )); do
    case $1 in
        -c|--config)
            [[ $# -ge 2 ]] || die "$1 needs an argument"
            CONFIG_FILE=$2
            CONFIG_EXPLICIT=1
            shift
            ;;
        -n|--dry-run) DRY_RUN=1 ;;
        -y|--yes)     ASSUME_YES=1 ;;
        --delete)     DELETE=1 ;;
        --max-prune)
            [[ $# -ge 2 ]] || die "$1 needs an argument"
            OPT_MAX_PRUNE=$(uint "$2") || die "--max-prune expects a number"
            shift
            ;;
        -s|--syslog)  SYSLOG=1 ;;
        -d|--debug)   DEBUG=1 ;;
        -h|--help)    usage; exit 0 ;;
        *)            usage >&2; die "unknown option: $1" ;;
    esac
    shift
done

# cron has no terminal and often no MTA to mail output to: log to syslog.
# One stream for stdout and stderr keeps the lines in order.
if (( SYSLOG )); then
    command -v logger >/dev/null 2>&1 || die "\"logger\" not found"
    exec > >(logger -t sync_users) 2>&1
fi


### CHECKS
(( EUID == 0 )) || die "run as root"

for tool in curl jq flock getent useradd usermod userdel install stat; do
    command -v "$tool" >/dev/null 2>&1 || die "\"$tool\" not found"
done

if [[ -f $CONFIG_FILE ]]; then
    [[ $(stat -c %u "$CONFIG_FILE") == 0 ]] || die "$CONFIG_FILE must be owned by root"
    [[ $(stat -c %a "$CONFIG_FILE") =~ ^[0-7]?[0-7][0145][0145]$ ]] || die "$CONFIG_FILE must not be writable by others"
    # shellcheck source=/dev/null
    source "$CONFIG_FILE" || die "cannot source $CONFIG_FILE"
    debug "config loaded from $CONFIG_FILE"
elif (( CONFIG_EXPLICIT )); then
    die "config file $CONFIG_FILE not found"
fi
[[ -n $OPT_MAX_PRUNE ]] && MAX_PRUNE=$OPT_MAX_PRUNE
USERPATH=${USERPATH%/}
KEYS_DIR=${KEYS_DIR%/}
[[ $USERPATH == /?* && $USERPATH != *[[:space:]]* ]] || die "USERPATH must be an absolute path below /"
[[ $KEYS_DIR == /?* && $KEYS_DIR != *[[:space:]]* ]] || die "KEYS_DIR must be an absolute path below /"
[[ $ORG =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]] || die "ORG is not a valid GitHub organization name"
[[ $SFTPGROUP =~ ^[a-z_][a-z0-9_-]*$ ]] || die "SFTPGROUP is not a valid group name"
MAX_PRUNE=$(uint "$MAX_PRUNE") || die "MAX_PRUNE must be a number"
TOKEN_WARN_DAYS=$(uint "$TOKEN_WARN_DAYS") || die "TOKEN_WARN_DAYS must be a number"
declare -A IN_BLOCK=()
for u in "${BLOCKLIST[@]}"; do IN_BLOCK[$u]=1; done
for u in "${KEEPLIST[@]}"; do
    valid_login "$u" || die "KEEPLIST entry \"$(safe "$u")\" is not a valid GitHub login"
    [[ -z ${IN_BLOCK[$u]:-} ]] || die "$u is in BLOCKLIST and KEEPLIST"
done
if [[ -r /etc/login.defs ]]; then
    v=$(uint "$(awk '$1 == "UID_MIN" { print $2 }' /etc/login.defs)") && UID_MIN=$v
fi

# token: environment first, file second. Never stored in the script.
if [[ -n ${GITHUB_TOKEN:-} ]]; then
    TOKEN=$GITHUB_TOKEN
elif [[ -r $TOKEN_FILE ]]; then
    [[ -L $TOKEN_FILE ]] && die "$TOKEN_FILE is a symlink"
    [[ $(stat -c %u "$TOKEN_FILE") == 0 ]] || die "$TOKEN_FILE must be owned by root"
    [[ $(stat -c %a "$TOKEN_FILE") =~ ^[0-7]?[0-7]00$ ]] || die "$TOKEN_FILE must not be accessible by group or other users"
    TOKEN=$(<"$TOKEN_FILE")
    TOKEN=${TOKEN//[[:space:]]/}
else
    die "no token. Set GITHUB_TOKEN or put the token into $TOKEN_FILE"
fi
[[ -n $TOKEN ]] || die "token is empty"

# one instance at a time
exec 9>"$LOCKFILE" || die "cannot open $LOCKFILE"
flock -n 9 || die "another instance is running"

# sftp group
if ! getent group "$SFTPGROUP" >/dev/null; then
    cat >&2 <<EOF
Group "$SFTPGROUP" does not exist. Create it with "groupadd $SFTPGROUP" and
add this to sshd_config if not done already:

Match Group $SFTPGROUP
    ChrootDirectory $USERPATH
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no
    PasswordAuthentication no
    AuthorizedKeysFile $KEYS_DIR/%u

EOF
    die "group \"$SFTPGROUP\" missing"
fi

# chroot directory: sshd insists on root ownership and no write access for others
if [[ -d $USERPATH ]]; then
    [[ $(stat -c %u "$USERPATH") == 0 ]] || die "$USERPATH must be owned by root (sshd ChrootDirectory)"
    [[ $(stat -c %a "$USERPATH") =~ ^[0-7]?[0-7][0145][0145]$ ]] || die "$USERPATH must not be writable by group/others (sshd ChrootDirectory)"
else
    log "creating chroot directory $USERPATH"
    run install -d -m 0755 -o root -g root -- "$USERPATH" || die "cannot create $USERPATH"
fi

# key directory: root writes here, so nobody else may
if [[ -L $KEYS_DIR ]]; then
    die "$KEYS_DIR is a symlink"
elif [[ -d $KEYS_DIR ]]; then
    [[ $(stat -c %u "$KEYS_DIR") == 0 ]] || die "$KEYS_DIR must be owned by root"
    [[ $(stat -c %a "$KEYS_DIR") =~ ^[0-7]?[0-7][0145][0145]$ ]] || die "$KEYS_DIR must not be writable by group/others"
else
    log "creating key directory $KEYS_DIR"
    run install -d -m 0755 -o root -g root -- "$KEYS_DIR" || die "cannot create $KEYS_DIR"
fi

NOLOGIN_SHELL=$(command -v nologin || echo /bin/false)

# body and response headers of the last API call go through root-only temp
# files (umask 077). curl truncates the body file before a retry, stdout it
# cannot. The token never touches a file here.
BODY_TMP=$(mktemp) || die "cannot create temporary file"
HEADERS_TMP=$(mktemp) || die "cannot create temporary file"
trap 'rm -f -- "$BODY_TMP" "$HEADERS_TMP"' EXIT
### END CHECKS


### FUNCTIONS

# GET a GitHub API URL into GH_BODY. Fails on network errors and HTTP >= 400
# and leaves the reason in GH_ERROR. Sets RATE_LIMITED when GitHub throttles us.
# The token is passed via curl config on a pipe from the printf builtin, so it
# never shows up in "ps" or in a temp file.
gh_get() {
    local status rc msg
    GH_BODY=
    GH_ERROR=
    status=$(printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" |
        curl -sS -L --retry 2 --connect-timeout 10 --max-time 60 -K - \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            -D "$HEADERS_TMP" -o "$BODY_TMP" -w '%{http_code}' -- "$1")
    rc=$?
    if (( rc != 0 )); then
        GH_ERROR="curl failed with exit code $rc"
        return 1
    fi
    GH_BODY=$(<"$BODY_TMP")
    if [[ $status != 2[0-9][0-9] ]]; then
        msg=$(jq -r 'if type == "object" then .message // empty else empty end' <<<"$GH_BODY" 2>/dev/null)
        GH_ERROR="HTTP $status${msg:+ $(safe "$msg")}"
        if [[ ($status == 403 || $status == 429) && ${msg,,} == *"rate limit"* ]]; then
            RATE_LIMITED=1
        fi
        GH_BODY=
        return 1
    fi
    check_token_expiry
    return 0
}

# warn once when the token is about to expire. GitHub reports the expiry of
# tokens that have one in a response header.
check_token_expiry() {
    local value expires now
    (( TOKEN_CHECKED || TOKEN_WARN_DAYS == 0 )) && return 0
    TOKEN_CHECKED=1
    value=$(awk -F': ' 'tolower($1) == "github-authentication-token-expiration" { v = $2 } END { print v }' "$HEADERS_TMP" | tr -d '\r')
    [[ -n $value ]] || return 0
    expires=$(date -d "$value" +%s 2>/dev/null) || { debug "cannot parse token expiry \"$(safe "$value")\""; return 0; }
    now=$(date +%s)
    if (( expires - now < TOKEN_WARN_DAYS * 86400 )); then
        warn "GitHub token expires $(safe "$value"), less than $TOKEN_WARN_DAYS days left. Replace it."
    else
        debug "token expires $(safe "$value")"
    fi
    return 0
}

# collect all member logins of ORG into ORG_MEMBERS, one per line, following
# pagination. Non-zero = fetch failed, reason in GH_ERROR.
fetch_org_members() {
    local page=1 count logins
    ORG_MEMBERS=
    while :; do
        gh_get "https://api.github.com/orgs/$ORG/members?per_page=100&page=$page" || return 1
        GH_ERROR="unexpected response"
        # every item must be a record with a string login, or nothing is trusted:
        # a silently dropped member would end up as a prune candidate
        count=$(jq 'if type == "array" and all(.[]; type == "object" and (.login | type) == "string")
                    then length else error("member list is not an array of records with a string login") end' <<<"$GH_BODY") || return 1
        [[ $count =~ ^[0-9]+$ ]] || return 1
        (( count == 0 )) && break
        logins=$(jq -r '.[].login' <<<"$GH_BODY") || return 1
        [[ -n $logins ]] && ORG_MEMBERS+=${logins}$'\n'
        (( count < 100 )) && break
        page=$((page + 1))
    done
    ORG_MEMBERS=${ORG_MEMBERS%$'\n'}
    GH_ERROR=
    return 0
}

# print the local accounts managed by this script: members of SFTPGROUP
# (supplementary or primary), one per line. Names this script could never
# have created and system accounts are reported and ignored.
local_members() {
    local gid names u uid
    gid=$(getent group "$SFTPGROUP" | cut -d: -f3) || return 1
    [[ $gid =~ ^[0-9]+$ ]] || return 1
    names=$({
        getent group "$SFTPGROUP" | cut -d: -f4 | tr ',' '\n'
        getent passwd | awk -F: -v g="$gid" '$4 == g { print $1 }'
    } | awk 'NF' | sort -u) || return 1
    while IFS= read -r u; do
        [[ -n $u ]] || continue
        if ! valid_login "$u"; then
            warn "$(safe "$u"): in group $SFTPGROUP but not a name this script manages, ignored"
            continue
        fi
        uid=$(id -u -- "$u") || continue
        if (( uid < UID_MIN )); then
            warn "$u: in group $SFTPGROUP but a system account (uid $uid), ignored"
            continue
        fi
        printf '%s\n' "$u"
    done <<<"$names"
    return 0
}

# collect the user's public keys from GitHub into FETCHED_KEYS, validated,
# one per line. Empty = no keys. Non-zero = fetch failed, reason in GH_ERROR.
# "No keys" is only what GitHub says with an empty JSON array; an empty,
# incomplete or otherwise unexpected body is a failure, never a reason to
# drop keys.
fetch_keys() {
    local count keys rc
    FETCHED_KEYS=
    gh_get "https://api.github.com/users/$1/keys" || return 1
    GH_ERROR="unexpected response"
    # every item must be a record with a string key, or nothing is trusted:
    # a silently dropped key would be removed from the account
    count=$(jq 'if type == "array" and all(.[]; type == "object" and (.key | type) == "string")
                then length else error("key list is not an array of records with a string key") end' <<<"$GH_BODY") || return 1
    [[ $count =~ ^[0-9]+$ ]] || return 1
    keys=$(jq -r '.[].key' <<<"$GH_BODY") || return 1
    # line-wise validation: no options, no comments, nothing but "<type> <base64>"
    FETCHED_KEYS=$(grep -E "$KEY_RE" <<<"$keys")
    rc=$?
    if (( rc == 2 )); then
        GH_ERROR="grep failed"
        return 1
    fi
    if (( count > 0 )) && [[ -z $FETCHED_KEYS ]]; then
        warn "$1: $count key(s) on GitHub, none of a supported type"
    fi
    GH_ERROR=
    return 0
}

# atomically write $2 into root-owned file $1, mode 0644
write_file() {
    local tmp
    tmp=$(mktemp -- "$1.XXXXXX") || return 1
    if printf '%s\n' "$2" >"$tmp" && chmod 0644 -- "$tmp" && mv -f -- "$tmp" "$1"; then
        return 0
    fi
    rm -f -- "$tmp"
    return 1
}

# account expired? That is how this script locks users.
is_expired() {
    local expire today
    expire=$(uint "$(getent shadow -- "$1" | cut -d: -f8)") || return 1
    today=$(( $(date +%s) / 86400 ))
    (( expire <= today ))
}

# make sure the home directory exists and belongs to the user
ensure_home() {
    local u=$1 home=$USERPATH/$1 gid
    if [[ -L $home ]]; then
        err "$u: $home is a symlink, refusing to touch it"
        return 1
    fi
    if (( DRY_RUN )) && ! getent passwd -- "$u" >/dev/null; then
        [[ -d $home ]] || log "    [dry-run] mkdir $home"
        return 0
    fi
    gid=$(id -g -- "$u") || return 1
    if [[ ! -d $home ]]; then
        run install -d -m 0755 -o "$u" -g "$gid" -- "$home" || { err "$u: cannot create $home"; return 1; }
    elif [[ $(stat -c %u -- "$home") != "$(id -u -- "$u")" ]]; then
        warn "$u: adopting pre-existing $home, contents left untouched"
        run chown -- "$u:$gid" "$home" || { err "$u: cannot chown $home"; return 1; }
    fi
    return 0
}

# install validated key lines $2 for user $1 if they changed.
# Empty $2 removes the key file: no key, no login.
install_keys() {
    local u=$1 keys=$2 file=$KEYS_DIR/$1 count
    if [[ -z $keys ]]; then
        if [[ -e $file ]]; then
            warn "$u: no usable SSH key on GitHub any more, login not possible"
            run rm -f -- "$file"
        else
            debug "$u: no usable SSH key on GitHub"
        fi
        return 0
    fi
    count=$(wc -l <<<"$keys")
    if [[ -f $file && $(<"$file") == "$keys" ]]; then
        debug "$u: $count key(s), unchanged"
        return 0
    fi
    log "$u: installing $count key(s)"
    (( DRY_RUN )) && return 0
    write_file "$file" "$keys" || { err "$u: cannot write $file"; return 1; }
    KEYS_WRITTEN=$((KEYS_WRITTEN + 1))
}

# refresh keys of an existing account. Fetch failure keeps current keys.
sync_keys() {
    local u=$1
    if ! fetch_keys "$u"; then
        err "$u: fetching keys from GitHub failed ($GH_ERROR), keeping current keys"
        return 1
    fi
    install_keys "$u" "$FETCHED_KEYS"
}

# create account, but only for members that have a usable key on GitHub:
# no key, no account, no directory. Simple rule to explain.
create_user() {
    local u=$1 keys
    if getent passwd -- "$u" >/dev/null; then
        err "$u: account exists but is not in group $SFTPGROUP, not touching it"
        return 1
    fi
    if ! fetch_keys "$u"; then
        err "$u: fetching keys from GitHub failed ($GH_ERROR), account not created"
        return 1
    fi
    keys=$FETCHED_KEYS
    if [[ -z $keys ]]; then
        log "$u: no usable SSH key on GitHub, no account"
        return 0
    fi
    log "$u: creating account"
    run useradd -M -s "$NOLOGIN_SHELL" -G "$SFTPGROUP" -d "$USERPATH/$u" -c "GitHub $ORG member" -- "$u" \
        || { err "$u: useradd failed"; return 1; }
    CREATED=$((CREATED + 1))
    ensure_home "$u" || return 1
    install_keys "$u" "$keys"
}

update_user() {
    local u=$1
    if is_expired "$u"; then
        log "$u: wanted again, re-enabling account"
        run usermod -e '' -- "$u" || { err "$u: usermod failed"; return 1; }
    fi
    ensure_home "$u" || return 1
    sync_keys "$u"
}

prune_user() {
    local u=$1 rc
    if (( DELETE )); then
        log "$u: deleting account and $USERPATH/$u"
        run userdel --remove -- "$u"
        rc=$?
        if (( rc != 0 )) && getent passwd -- "$u" >/dev/null; then
            err "$u: userdel failed with $rc"
            return 1
        elif (( rc != 0 )); then
            warn "$u: userdel returned $rc (home already gone?), account removed"
        fi
        DELETED=$((DELETED + 1))
    else
        log "$u: locking account"
        run usermod -e 1970-01-02 -- "$u" || { err "$u: usermod failed"; return 1; }
        LOCKED=$((LOCKED + 1))
    fi
    if [[ -e $KEYS_DIR/$u ]]; then
        run rm -f -- "$KEYS_DIR/$u"
    fi
}

### END FUNCTIONS


### MAIN

(( DRY_RUN )) && log "dry run, nothing will be changed"

# remote state
log "fetching members of \"$ORG\""
fetch_org_members || die "could not fetch the member list of \"$ORG\": $GH_ERROR"
[[ -n $ORG_MEMBERS ]] || die "member list of \"$ORG\" is empty, refusing to continue"
mapfile -t ORG_LIST <<<"$ORG_MEMBERS"
debug "org members: ${ORG_LIST[*]}"

declare -A IS_WANTED=() IS_LOCAL=()

# wanted = org members that are neither unusable as user name nor blocklisted,
# plus the keeplist regardless of membership.
# Logins are untrusted input: validate before they are used anywhere,
# including as array subscripts.
WANTED=()
for u in "${ORG_LIST[@]}"; do
    if ! valid_login "$u"; then
        warn "$(safe "$u"): not usable as unix user name, skipped"
        continue
    fi
    if [[ -n ${IN_BLOCK[$u]:-} ]]; then
        debug "$u: blocklisted"
        continue
    fi
    IS_WANTED[$u]=1
    WANTED+=("$u")
done
for u in "${KEEPLIST[@]}"; do
    [[ -n ${IS_WANTED[$u]:-} ]] && continue
    debug "$u: keeplisted, wanted regardless of membership"
    IS_WANTED[$u]=1
    WANTED+=("$u")
done
log "${#ORG_LIST[@]} members, ${#WANTED[@]} wanted after blocklist (${BLOCKLIST[*]:-none}) and keeplist (${KEEPLIST[*]:-none})"

# local state
LOCAL_MEMBERS=$(local_members) || die "cannot read members of group \"$SFTPGROUP\""
LOCAL_LIST=()
[[ -n $LOCAL_MEMBERS ]] && mapfile -t LOCAL_LIST <<<"$LOCAL_MEMBERS"
for u in "${LOCAL_LIST[@]}"; do IS_LOCAL[$u]=1; done
log "${#LOCAL_LIST[@]} local accounts in group \"$SFTPGROUP\""
debug "local accounts: ${LOCAL_LIST[*]}"

# create or refresh
log ""
log "syncing accounts and keys"
for (( i = 0; i < ${#WANTED[@]}; i++ )); do
    u=${WANTED[i]}
    if (( RATE_LIMITED )); then
        err "GitHub rate limit hit, not synced this run: ${WANTED[*]:i}"
        break
    fi
    if [[ -n ${IS_LOCAL[$u]:-} ]]; then
        update_user "$u"
    else
        create_user "$u"
    fi
done

# prune
log ""
log "checking for accounts to prune"
CANDIDATES=()
for u in "${LOCAL_LIST[@]}"; do
    [[ -n ${IS_WANTED[$u]:-} ]] && continue
    if (( ! DELETE )) && is_expired "$u" && [[ ! -e $KEYS_DIR/$u ]]; then
        debug "$u: already locked"
        continue
    fi
    CANDIDATES+=("$u")
done

if (( DELETE )); then
    ACTION="delete account and files (CANNOT BE UNDONE)"
else
    ACTION="lock account"
fi

if (( ${#CANDIDATES[@]} == 0 )); then
    log "nothing to prune"
elif (( MAX_PRUNE > 0 && ${#CANDIDATES[@]} > MAX_PRUNE )); then
    err "${#CANDIDATES[@]} accounts qualify for pruning, more than MAX_PRUNE=$MAX_PRUNE. Refusing."
    err "candidates: ${CANDIDATES[*]}"
    err "verify the member list, then raise --max-prune if this is expected"
else
    for u in "${CANDIDATES[@]}"; do
        confirm "$u: no longer member of \"$ORG\" or blocklisted. ${ACTION}?"
        case $? in
            0) prune_user "$u" ;;
            1) log "$u: kept" ;;
            *) UNCONFIRMED=$((UNCONFIRMED + 1)) ;;
        esac
    done
    # an operator saying no is a decision; nobody being asked is not
    if (( UNCONFIRMED )); then
        err "$UNCONFIRMED account(s) left to prune, run with --yes to apply"
    fi
fi

log ""
log "done: created $CREATED, keys written $KEYS_WRITTEN, locked $LOCKED, deleted $DELETED, errors $ERRORS"
(( ERRORS == 0 )) && exit 0
exit 2

