#!/bin/bash
#
# sync_users.sh - mirror GitHub organization members to local SFTP-only accounts
#
# Every member of ORG (minus BLOCKLIST) who has a public SSH key on their
# GitHub profile gets a local account that is jailed via SFTPGROUP into the
# chroot USERPATH and can only authenticate with those keys. No key on
# GitHub, no account, no directory. Existing accounts whose keys disappear
# from GitHub keep their files but cannot log in until a key is back.
# Members who left the organization (or got blocklisted) are locked; with
# --delete they are removed together with their files. Accounts listed in
# KEEPLIST are never pruned.
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
#
# Requirements: bash >= 4.4, curl >= 7.55, jq, flock, shadow tools.
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
# Cron example: 17 * * * * root /usr/local/sbin/sync_users.sh --yes

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

# local accounts (members of SFTPGROUP) that are never pruned
KEEPLIST=()

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
OPT_MAX_PRUNE=
CONFIG_EXPLICIT=0

CREATED=0
KEYS_WRITTEN=0
LOCKED=0
DELETED=0
ERRORS=0

# GitHub login that is also a valid unix user name (shadow: max 32 chars).
# valid_login() additionally requires a letter: all-digit names are looked
# up as uid by getent/chown/install and could hit a foreign account.
LOGIN_RE='^[A-Za-z0-9][A-Za-z0-9-]{0,31}$'
UID_MIN=1000
# public key types GitHub hands out: "<type> <base64>", no comment
KEY_RE='^(ssh-(rsa|dss|ed25519)|ecdsa-sha2-nistp(256|384|521)|sk-(ssh-ed25519|ecdsa-sha2-nistp256)@openssh\.com) [A-Za-z0-9+/]{32,}={0,2}$'

usage() {
    cat <<EOF
Usage: ${0##*/} [OPTIONS]

  -c, --config FILE   config file to source (default: $CONFIG_FILE)
  -n, --dry-run       report what would be done, change nothing
  -y, --yes           prune without asking (for cron). Without a tty and
                      without --yes prune candidates are only reported.
      --delete        prune = "userdel --remove" instead of locking.
                      Removes all files of the user. CANNOT BE UNDONE.
      --max-prune N   refuse to prune more than N accounts (0 = unlimited)
  -d, --debug         verbose output
  -h, --help          this text

Token: environment variable GITHUB_TOKEN or the file configured as TOKEN_FILE.
Exit codes: 0 ok, 1 fatal (nothing or not everything done), 2 finished with errors.
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

# ask yes/no. Yes in dry-run and with --yes, no without a tty.
confirm() {
    local answer
    if (( DRY_RUN || ASSUME_YES )); then
        return 0
    fi
    if [[ ! -t 0 ]]; then
        log "$1 -> skipped, no tty. Run with --yes to apply."
        return 1
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
            [[ $2 =~ ^[0-9]+$ ]] || die "--max-prune expects a number"
            OPT_MAX_PRUNE=$2
            shift
            ;;
        -d|--debug)   DEBUG=1 ;;
        -h|--help)    usage; exit 0 ;;
        *)            usage >&2; die "unknown option: $1" ;;
    esac
    shift
done


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
[[ $MAX_PRUNE =~ ^[0-9]+$ ]] || die "MAX_PRUNE must be a number"
if [[ -r /etc/login.defs ]]; then
    v=$(awk '$1 == "UID_MIN" { print $2 }' /etc/login.defs)
    [[ $v =~ ^[0-9]+$ ]] && UID_MIN=$v
fi

# token: environment first, file second. Never stored in the script.
if [[ -n ${GITHUB_TOKEN:-} ]]; then
    TOKEN=$GITHUB_TOKEN
elif [[ -r $TOKEN_FILE ]]; then
    [[ $(stat -c %a "$TOKEN_FILE") =~ ^[0-7]?[0-7]00$ ]] || warn "$TOKEN_FILE is readable by others, chmod 0600 it"
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
### END CHECKS


### FUNCTIONS

# GET a GitHub API URL. Prints the body. Fails on network errors and HTTP >= 400.
# The token is passed via curl config on a pipe from the printf builtin, so it
# never shows up in "ps" or in a temp file.
gh_get() {
    printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" |
    curl -sS -f -L --retry 2 --connect-timeout 10 --max-time 60 -K - \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -- "$1"
}

# print all member logins of ORG, one per line, following pagination
fetch_org_members() {
    local page=1 body count
    while :; do
        body=$(gh_get "https://api.github.com/orgs/$ORG/members?per_page=100&page=$page") || return 1
        count=$(jq 'if type == "array" then length else error("unexpected response") end' <<<"$body") || return 1
        [[ $count =~ ^[0-9]+$ ]] || return 1
        (( count == 0 )) && break
        jq -r '.[] | objects | .login | strings' <<<"$body" || return 1
        (( count < 100 )) && break
        page=$((page + 1))
    done
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

# print the user's public keys from GitHub, validated, one per line.
# Empty output = no keys. Non-zero = fetch failed.
fetch_keys() {
    local body keys
    body=$(gh_get "https://api.github.com/users/$1/keys") || return 1
    keys=$(jq -r 'if type == "array" then .[] | objects | .key | strings else error("unexpected response") end' <<<"$body") || return 1
    # line-wise validation: no options, no comments, nothing but "<type> <base64>"
    grep -E "$KEY_RE" <<<"$keys" || true
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
    expire=$(getent shadow -- "$1" | cut -d: -f8)
    [[ $expire =~ ^[0-9]+$ ]] || return 1
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
    local u=$1 keys
    if ! keys=$(fetch_keys "$u"); then
        err "$u: fetching keys from GitHub failed, keeping current keys"
        return 1
    fi
    install_keys "$u" "$keys"
}

# create account, but only for members that have a usable key on GitHub:
# no key, no account, no directory. Simple rule to explain.
create_user() {
    local u=$1 keys
    if getent passwd -- "$u" >/dev/null; then
        err "$u: account exists but is not in group $SFTPGROUP, not touching it"
        return 1
    fi
    if ! keys=$(fetch_keys "$u"); then
        err "$u: fetching keys from GitHub failed, account not created"
        return 1
    fi
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
        log "$u: back in \"$ORG\", re-enabling account"
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
ORG_MEMBERS=$(fetch_org_members) || die "could not fetch the member list of \"$ORG\" (token, permissions, network?)"
[[ -n $ORG_MEMBERS ]] || die "member list of \"$ORG\" is empty, refusing to continue"
mapfile -t ORG_LIST <<<"$ORG_MEMBERS"
debug "org members: ${ORG_LIST[*]}"

declare -A IN_ORG=() IN_BLOCK=() IN_KEEP=() IS_LOCAL=()
for u in "${BLOCKLIST[@]}"; do IN_BLOCK[$u]=1; done
for u in "${KEEPLIST[@]}";  do IN_KEEP[$u]=1;  done

# wanted = org members that are neither unusable as user name nor blocklisted.
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
    IN_ORG[$u]=1
    WANTED+=("$u")
done
log "${#ORG_LIST[@]} members, ${#WANTED[@]} wanted after blocklist (${BLOCKLIST[*]:-none})"

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
for u in "${WANTED[@]}"; do
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
    [[ -n ${IN_ORG[$u]:-} ]] && continue
    if [[ -n ${IN_KEEP[$u]:-} ]]; then
        debug "$u: keeplisted"
        continue
    fi
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
        if confirm "$u: no longer member of \"$ORG\" or blocklisted. ${ACTION}?"; then
            prune_user "$u"
        else
            log "$u: kept"
        fi
    done
fi

log ""
log "done: created $CREATED, keys written $KEYS_WRITTEN, locked $LOCKED, deleted $DELETED, errors $ERRORS"
(( ERRORS == 0 )) && exit 0
exit 2

