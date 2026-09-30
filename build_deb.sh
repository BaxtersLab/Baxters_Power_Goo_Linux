#!/usr/bin/env bash
# baxters-power-goo — A1 contract. DISTRO interpreter lane (PyQt6/SciPy).
# Licence GPL-3.0-only, forced by PyQt6. Builds only; VM harness verifies.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
HERE="$PWD"; PKG=baxters-power-goo
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/opt/baxters/power-goo"
mkdir -p "$DEST" "$STAGE/usr/share/applications" "$STAGE/usr/share/doc"
cp -a packaging/DEBIAN "$STAGE/DEBIAN"
cp -a packaging/usr/share/applications/. "$STAGE/usr/share/applications/"
cp -a packaging/usr/share/doc/. "$STAGE/usr/share/doc/"
cp -a packaging/run.sh "$DEST/run.sh"

for item in main.py src assets; do
    [ -e "$item" ] || { echo "FATAL: required payload item missing: $item" >&2; exit 1; }
    cp -a "$item" "$DEST/"
done
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -name '*.pyc' -delete 2>/dev/null || true
chmod 0755 "$DEST/run.sh"

# Guards, same family as the other packages.
ICON=$(sed -n 's|^Icon=/opt/baxters/power-goo/||p' "$STAGE/usr/share/applications/$PKG.desktop")
[ -n "$ICON" ] && [ ! -f "$DEST/$ICON" ] && { echo "FATAL: Icon= '$ICON' not in payload" >&2; exit 1; }
EXECP=$(sed -n 's|^Exec=||p' "$STAGE/usr/share/applications/$PKG.desktop" | awk '{print $1}')
REL="${EXECP#/opt/baxters/power-goo/}"
[ -x "$DEST/$REL" ] || { echo "FATAL: Exec target '$EXECP' missing or not executable" >&2; exit 1; }
[ -s "$STAGE/usr/share/doc/$PKG/copyright" ] || { echo "FATAL: copyright missing or empty" >&2; exit 1; }
# The entry point must actually import: a payload that cannot start is not a package.
python3 -c "import ast,sys; ast.parse(open('$DEST/main.py').read())" \
  || { echo "FATAL: main.py does not parse" >&2; exit 1; }

mkdir -p "$HERE/dist"

# --- payload hygiene (added 2026-09-24 by the packaging agent) --------------
# Files inherit the BUILD USER's umask. On this box that is 0002, so payload
# arrived group-writable and dpkg installed it that way -- meaning any member
# of the installing group could edit an installed program. An audit of the
# built .deb files found this in ten of the twelve hand-written packagers; none
# of them normalised modes. `go-w` is surgical: it strips group and other write
# and leaves read and EXECUTE alone, so run.sh and binaries keep working (a
# blanket chmod 0644 would break them).
chmod -R go-w "$STAGE"
# Editor history and build-machine bytecode are not product. .bak files put a
# second, older copy of shipped code on a user's machine; __pycache__ carries
# absolute build paths and can be stale against the .py beside it.
find "$STAGE" -name '*.bak' -delete 2>/dev/null || true
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
if [ -n "$(find "$STAGE" \( -type f -o -type d \) -perm -g+w -print -quit 2>/dev/null)" ]; then
    echo "FATAL: group-writable entries remain in the payload" >&2
    exit 1
fi
# Derive the filename from the control, never hardcode it. A hardcoded version
# here produced a .deb whose control said 1.0.0-3 and whose NAME said 1.0.0-2:
# apt reads the control, but every tool that globs the pool reads the name, and
# two artefacts disagreeing about their own version is how "two different files
# claim the same version" starts. Fifth occurrence of this defect in the estate.
DEBVER="$(awk '/^Version: /{sub(/^Version: /,""); print; exit}' "$HERE/packaging/DEBIAN/control")"
[ -n "$DEBVER" ] || { echo "FATAL: no Version: in the control file" >&2; exit 1; }
dpkg-deb --root-owner-group -Zzstd --build "$STAGE" "$HERE/dist/${PKG}_${DEBVER}_all.deb" >/dev/null
echo "built: $HERE/dist/${PKG}_${DEBVER}_all.deb"
