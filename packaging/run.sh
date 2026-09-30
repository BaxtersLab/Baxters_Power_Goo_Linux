#!/usr/bin/env bash
# Baxters Power Goo — supported entry point (packaging contract A1 §3).
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"

# Prefer the shared scrub when baxters-runtime is installed. It is only a
# Recommends: this app is distro-lane and does not use the vendored interpreter,
# so pulling 33 MB for one shell script would be wrong. The fallback below is the
# same logic, and the duplication is the argument for moving baxters-env.sh into
# a small baxters-common package -- noted in A1, not solved here.
if [ -r /opt/baxters/runtime/baxters-env.sh ]; then
    . /opt/baxters/runtime/baxters-env.sh
else
    for _v in $(env | grep -o '^[A-Za-z_][A-Za-z0-9_]*=/snap/[^:]*' | cut -d= -f1); do
        [ "$_v" = XDG_DATA_DIRS ] && continue
        unset "$_v"
    done
    for _v in GSETTINGS_SCHEMA_DIR GTK_PATH GIO_MODULE_DIR LOCPATH \
              XDG_DATA_HOME XDG_CONFIG_HOME XDG_CACHE_HOME; do
        eval "_val=\${$_v:-}"; case "$_val" in */snap/*) unset "$_v" ;; esac
    done
    unset _v _val ELECTRON_RUN_AS_NODE
    case "${XDG_DATA_DIRS:-}" in */snap/*)
        _c=""; _o="$IFS"; IFS=':'
        for _p in $XDG_DATA_DIRS; do
            [ -z "$_p" ] && continue
            case "$_p" in */snap/*) continue ;; esac
            _c="${_c:+$_c:}$_p"
        done
        IFS="$_o"; export XDG_DATA_DIRS="${_c:-/usr/local/share:/usr/share}"
        unset _c _o _p ;;
    esac
fi

# GDK_BACKEND is deliberately NOT set. This is a Qt application; the GTK
# client-side-decoration hit-offset rule (A1 §3.6) does not apply to it.
cd "$HERE"
exec python3 main.py "$@"
