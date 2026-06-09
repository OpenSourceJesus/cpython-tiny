#!/bin/sh
# Build a small, GPL-free, mostly-static CPython interpreter.
#
# Usage:
#   Tools/build/build-minimal-static.sh [build-dir] [install-prefix]
#
# Examples:
#   Tools/build/build-minimal-static.sh
#   Tools/build/build-minimal-static.sh build-min /opt/python-minimal
#   FULL_STATIC=1 Tools/build/build-minimal-static.sh build-static
#
# The resulting `python` binary statically links libpython and stdlib C
# extensions (MODULE_BUILDTYPE=static).  Pure-Python stdlib files under
# Lib/ are still required at runtime unless you use Tools/freeze or a
# custom layout.
#
# GPL note: CPython itself is PSF-licensed.  This script avoids optional
# modules that link GNU Readline or GNU GDBM at runtime.  Build-time-only
# GPLv3 files (config.guess, config.sub) are not linked into the binary.

set -eu

SRCDIR=$(cd "$(dirname "$0")/../.." && pwd)
BUILDDIR=${1:-${SRCDIR}/build-minimal-static}
PREFIX=${2:-${BUILDDIR}/install}

mkdir -p "$BUILDDIR/Modules"
cd "$BUILDDIR"

# Out-of-tree Setup.local from the minimal template.
cp "${SRCDIR}/Modules/Setup.local.minimal" Modules/Setup.local

# Size-oriented compiler defaults (override via environment).
# -g0 avoids configure's default -g, which bloats the binary before strip.
: "${CFLAGS:= -Os -g0 -ffunction-sections -fdata-sections}"
: "${LDFLAGS:= -Wl,--gc-sections}"

CONFIGURE_ARGS="
  --prefix=${PREFIX}
  --disable-shared
  --disable-test-modules
  --without-doc-strings
  --without-readline
  --with-dbmliborder=ndbm:bdb
  --with-ensurepip=no
  --with-builtin-hashlib-hashes=no
  --without-remote-debug
"

# Statically link extension modules into libpython / the interpreter binary.
export MODULE_BUILDTYPE=static

# Optional: fully static executable (requires static libc and deps; musl
# toolchains work best).  Set FULL_STATIC=1 to enable.
if [ "${FULL_STATIC:-0}" = 1 ]; then
  export LDFLAGS="-static ${LDFLAGS}"
  export EXE_LDFLAGS="-static"
  export LIBS="${LIBS:-} -static"
fi

echo "==> Configuring in ${BUILDDIR}"
echo "    prefix: ${PREFIX}"
echo "    MODULE_BUILDTYPE=${MODULE_BUILDTYPE}"
echo "    CFLAGS=${CFLAGS}"
echo "    LDFLAGS=${LDFLAGS}"

# shellcheck disable=SC2086
"${SRCDIR}/configure" ${CONFIGURE_ARGS} CFLAGS="${CFLAGS}" LDFLAGS="${LDFLAGS}"

echo "==> Building"
make -j"$(nproc 2>/dev/null || echo 2)"

echo "==> Stripping debug symbols"
strip -s python

echo ""
echo "Build complete."
echo "  Binary:  ${BUILDDIR}/python"
echo "  Install: make -C ${BUILDDIR} install  (prefix=${PREFIX})"
echo ""
echo "Verify GPL-free optional modules are absent:"
echo "  ${BUILDDIR}/python -c \"import sys; bad=('readline','_gdbm'); print([m for m in bad if m in sys.builtin_module_names])\""
echo ""
echo "Check binary size:"
echo "  ls -lh ${BUILDDIR}/python"
echo ""
echo "Note: Lib/ is still required at runtime.  For a single-file app, use"
echo "Tools/freeze after installing this build with MODULE_BUILDTYPE=static."
