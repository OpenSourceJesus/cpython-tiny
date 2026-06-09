#!/bin/sh
# Export a minimal source tree (only files needed to rebuild python) as a tarball.
#
# Usage: Tools/build/export-minimal-source.sh [output.tar.xz] [build-dir]

set -eu

SRCDIR=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-${SRCDIR}/cpython-minimal-source.tar.xz}
BUILDDIR=${2:-${SRCDIR}/build-musl-static}
STAGE=$(mktemp -d)

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

if [ ! -f "${BUILDDIR}/Makefile" ]; then
    echo "error: ${BUILDDIR}/Makefile not found; configure first" >&2
    exit 1
fi

python3 "${SRCDIR}/Tools/build/compute_minimal_sources.py" \
    "${SRCDIR}" "${BUILDDIR}" --list > "${STAGE}/files.lst"

DEST="${STAGE}/cpython"
mkdir -p "${DEST}"

while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    src="${SRCDIR}/${rel}"
    [ -f "$src" ] || continue
    mkdir -p "${DEST}/$(dirname "$rel")"
    cp -p "$src" "${DEST}/${rel}"
done < "${STAGE}/files.lst"

mkdir -p "${DEST}/build-musl-static/Modules"
cp "${BUILDDIR}/Makefile" "${DEST}/build-musl-static/"
cp "${BUILDDIR}/pyconfig.h" "${DEST}/build-musl-static/"
cp "${BUILDDIR}/Modules/Setup.local" "${DEST}/build-musl-static/Modules/" 2>/dev/null || true
cp "${BUILDDIR}/Modules/Setup.stdlib" "${DEST}/build-musl-static/Modules/" 2>/dev/null || true

mkdir -p "${DEST}/Tools/build"
for f in build-minimal-musl.sh strip-source.sh prune-minimal-source.sh \
    export-minimal-source.sh strip_comments.py purge_orphan_modules.py \
    compute_minimal_sources.py purge_nonessential_tree.py; do
    [ -f "${SRCDIR}/Tools/build/${f}" ] && cp "${SRCDIR}/Tools/build/${f}" "${DEST}/Tools/build/"
done

echo "==> Creating ${OUT}"
tar -cJf "$OUT" -C "$STAGE" cpython
ls -lh "$OUT"
du -sh "${DEST}"
