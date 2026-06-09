#!/bin/sh
# Strip documentation and comments from the pruned CPython source tree.
#
# C sources are not comment-stripped (macro continuations break).  Only Lib/*.py
# # comments are removed.  Documentation trees, README files, and unused modules
# are deleted by prune-minimal-source.sh.
#
# Uncompressed source remains ~25 MB (CPython core is irreducible).  The xz
# tarball is ~3 MB — under a 10 MB distribution target.
#
# Usage: Tools/build/strip-source.sh [--dry-run]
# Run after Tools/build/prune-minimal-source.sh

set -eu

SRCDIR=$(cd "$(dirname "$0")/../.." && pwd)
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

rm_path() {
    [ -e "$1" ] || return 0
    if [ "$DRY_RUN" = 1 ]; then
        echo "  would remove: $1"
    else
        rm -rf "$1"
        echo "  removed: $1"
    fi
}

echo "==> Removing documentation trees and metadata"
for path in \
    InternalDocs \
    .github \
    PCbuild \
    README.rst \
    LICENSE \
    Include/README.rst \
    Lib/site-packages \
    Misc/NEWS.d \
    Misc/HISTORY \
    Misc/svnmap.txt \
    Misc/python.man \
    Misc/sbom.spdx.json \
    Misc/externals.spdx.json \
    Misc/ACKS \
    Misc/mypy \
    Misc/rhel7 \
    Misc/valgrind-python.supp \
    Misc/README.valgrind \
    Misc/README.AIX \
    Misc/README \
    Misc/SpecialBuilds.txt \
    Misc/stable_abi.toml \
    Misc/libabigail.abignore
do
    rm_path "${SRCDIR}/${path}"
done

echo "==> Removing orphan / unused source files"
for f in "${SRCDIR}"/Modules/_ssl_data_*.h \
         "${SRCDIR}"/Modules/_test*.c \
         "${SRCDIR}"/Modules/_testclinic*.c \
         "${SRCDIR}"/Modules/xx*.c \
         "${SRCDIR}"/Modules/gc_weakref.txt \
         "${SRCDIR}/Python/bytecodes.c" \
         "${SRCDIR}/Python/optimizer_bytecodes.c"
do
    rm_path "$f"
done

echo "==> Removing __pycache__ and bytecode"
if [ "$DRY_RUN" = 0 ]; then
    find "${SRCDIR}" \( -path "${SRCDIR}/.git" -o -path "${SRCDIR}/build-*" \) -prune \
        -o \( -name '__pycache__' -o -name '*.pyc' -o -name '*.pyo' \) -print -exec rm -rf {} + 2>/dev/null || true
fi

echo "==> Trimming Lib/ to runtime minimum"
for path in zipfile compression pathlib shutil.py pickle.py heapq.py bisect.py \
    queue.py random.py tempfile.py glob.py fnmatch.py sysconfig.py; do
    rm_path "${SRCDIR}/Lib/${path}"
done

echo "==> Removing stray documentation files"
if [ "$DRY_RUN" = 1 ]; then
    find "${SRCDIR}" \
        -path "${SRCDIR}/.git" -prune -o \
        -path "${SRCDIR}/build-*" -prune -o \
        -type f \( -name '*.md' -o -name '*.rst' -o -name '*.man' -o -name 'README*' -o -name 'NEWS*' -o -name 'HISTORY*' -o -name '*.txt' \) \
        -print 2>/dev/null | while read -r f; do
        case "$f" in
            */Misc/platform_triplet.c) continue ;;
            */config.guess|*/config.sub) continue ;;
        esac
        echo "  would remove: $f"
    done
else
    find "${SRCDIR}" \
        -path "${SRCDIR}/.git" -prune -o \
        -path "${SRCDIR}/build-*" -prune -o \
        -type f \( -name '*.md' -o -name '*.rst' -o -name '*.man' -o -name 'README*' -o -name 'NEWS*' -o -name 'HISTORY*' \) \
        -print 2>/dev/null | while read -r f; do
        rm -f "$f" && echo "  removed: $f"
    done
    find "${SRCDIR}" \
        -path "${SRCDIR}/.git" -prune -o \
        -path "${SRCDIR}/build-*" -prune -o \
        -type f -name '*.txt' \
        ! -path '*/Grammar/*' \
        -print 2>/dev/null | while read -r f; do
        rm -f "$f" && echo "  removed: $f"
    done
fi

if [ "$DRY_RUN" = 0 ]; then
    echo "==> Purging orphan extension module sources"
    python3 "${SRCDIR}/Tools/build/purge_orphan_modules.py" "${SRCDIR}"

    echo "==> Removing non-linux Platforms/"
    for d in "${SRCDIR}"/Platforms/*; do
        [ "$(basename "$d")" = "linux-musl" ] && continue
        rm_path "$d"
    done

    echo "==> Stripping # comments from Lib/*.py"
    python3 "${SRCDIR}/Tools/build/strip_comments.py" "${SRCDIR}/Lib"
fi

echo ""
echo "Source size (excluding .git and build-*):"
du -sh --exclude='.git' --exclude='build-*' "${SRCDIR}" 2>/dev/null \
    || du -sh "${SRCDIR}/Modules" "${SRCDIR}/Lib" "${SRCDIR}/Python" "${SRCDIR}/Objects" "${SRCDIR}/Parser" "${SRCDIR}/Include" "${SRCDIR}/Misc" "${SRCDIR}/Tools" "${SRCDIR}/Programs" "${SRCDIR}/Grammar" "${SRCDIR}/Platforms" "${SRCDIR}/configure" "${SRCDIR}/configure.ac" "${SRCDIR}/Makefile.pre.in" 2>/dev/null | awk '{s+=$1} END{print s " (sum of parts)"}'
