#!/bin/sh
# Build a small, GPL-free, fully static CPython with musl libc.
#
# 1. Prunes unused source (Tools/build/prune-minimal-source.sh) on first run
# 2. Configures with musl-gcc and static linking
# 3. Produces a stripped static `python` binary
#
# Usage:
#   Tools/build/build-minimal-musl.sh [build-dir] [install-prefix]
#
# Environment:
#   MUSL_CC       compiler (default: musl-gcc)
#   MUSL_PREFIX   musl install prefix (default: /usr/local/musl)
#   SKIP_PRUNE=1  skip source pruning (already pruned)
#   PRUNE_DRY_RUN=1  show what would be deleted, then exit
#
# Examples:
#   Tools/build/build-minimal-musl.sh
#   MUSL_CC=x86_64-linux-musl-gcc Tools/build/build-minimal-musl.sh build-musl

set -eu

SRCDIR=$(cd "$(dirname "$0")/../.." && pwd)
BUILDDIR=${1:-${SRCDIR}/build-musl-static}
PREFIX=${2:-${BUILDDIR}/install}
MUSL_PREFIX=${MUSL_PREFIX:-/usr/local/musl}
# Default: gcc with musl specs.  Override with MUSL_CC=musl-gcc if preferred.
MUSL_CC=${MUSL_CC:-gcc -specs ${MUSL_PREFIX}/lib/musl-gcc.specs}
# gcc's libgcc pass-through needs libatomic_asneeded from the host toolchain.
MUSL_HOST_LIBDIR=${MUSL_HOST_LIBDIR:-/usr/lib}

if [ "${PRUNE_DRY_RUN:-0}" = 1 ]; then
    exec "${SRCDIR}/Tools/build/prune-minimal-source.sh" --dry-run
fi

if [ "${SKIP_PRUNE:-0}" != 1 ]; then
    echo "==> Pruning source tree"
    "${SRCDIR}/Tools/build/prune-minimal-source.sh"
    echo "==> Stripping documentation and comments"
    "${SRCDIR}/Tools/build/strip-source.sh"
fi

if ! command -v ${MUSL_CC%% *} >/dev/null 2>&1; then
    echo "error: compiler '${MUSL_CC%% *}' not found; set MUSL_CC" >&2
    exit 1
fi

# Sanity-check musl toolchain (libatomic_asneeded must be visible to the linker).
if ! ${MUSL_CC} -x c - -o /dev/null -L"${MUSL_HOST_LIBDIR}" <<<'int main(void){return 0;}' 2>/dev/null; then
    echo "warning: musl compiler check failed." >&2
    echo "  If the linker cannot find -latomic_asneeded, either:" >&2
    echo "    ln -s ${MUSL_HOST_LIBDIR}/libatomic_asneeded.a ${MUSL_PREFIX}/lib/" >&2
    echo "  or set MUSL_HOST_LIBDIR to the directory containing libatomic_asneeded.a" >&2
fi

mkdir -p "${BUILDDIR}/Modules"
cd "${BUILDDIR}"

cp "${SRCDIR}/Modules/Setup.local.minimal" Modules/Setup.local

# Wrapper used only for ./configure so the linker finds libatomic_asneeded.
# The generated Makefile must NOT retain -L${MUSL_HOST_LIBDIR} or static
# links pull glibc's libc.a instead of musl's.
cat > musl-cc-wrapper.sh <<EOF
#!/bin/sh
exec gcc -specs ${MUSL_PREFIX}/lib/musl-gcc.specs -L${MUSL_HOST_LIBDIR} "\$@"
EOF
chmod +x musl-cc-wrapper.sh

# Copy libatomic into the build dir so the linker can find it without -L/usr/lib
# (which would also expose glibc's libc.a during -static links).
cp "${MUSL_HOST_LIBDIR}/libatomic_asneeded.a" ./libatomic_asneeded.a 2>/dev/null \
    || cp "${MUSL_HOST_LIBDIR}/libatomic.a" ./libatomic.a

: "${CFLAGS:= -Os -g0 -ffunction-sections -fdata-sections}"
: "${CONFIGURE_LDFLAGS:= -Wl,--gc-sections -Wl,-z,stack-size=1048576}"
: "${LINK_LDFLAGS:= -static -L${BUILDDIR} -Wl,--gc-sections -Wl,-z,stack-size=1048576}"
if [ -f "${BUILDDIR}/libatomic_asneeded.a" ]; then
    : "${MUSL_LIBS:= ${BUILDDIR}/libatomic_asneeded.a}"
else
    : "${MUSL_LIBS:= ${BUILDDIR}/libatomic.a}"
fi

export CC="${BUILDDIR}/musl-cc-wrapper.sh"
export MODULE_BUILDTYPE=static
export CONFIG_SITE="${SRCDIR}/Platforms/linux-musl/config.site"
export EXE_LDFLAGS="${LINK_LDFLAGS}"
export LIBS="${LIBS:-} ${MUSL_LIBS}"

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

echo "==> Configuring musl static build in ${BUILDDIR}"
echo "    CC=${CC}"
echo "    prefix=${PREFIX}"
echo "    MUSL_PREFIX=${MUSL_PREFIX}"

# shellcheck disable=SC2086
MODULE_BUILDTYPE=static \
"${SRCDIR}/configure" ${CONFIGURE_ARGS} \
    CC="${BUILDDIR}/musl-cc-wrapper.sh" \
    CFLAGS="${CFLAGS}" \
    LDFLAGS="${CONFIGURE_LDFLAGS}" \
    CPPFLAGS="-I${MUSL_PREFIX}/include"

export MODULE_BUILDTYPE=static
BUILD_CC="gcc -specs ${MUSL_PREFIX}/lib/musl-gcc.specs"

echo "==> Building (static link, interpreter only)"
make python CC="${BUILD_CC}" \
    LDFLAGS="${LINK_LDFLAGS}" \
    EXE_LDFLAGS="${LINK_LDFLAGS}" \
    LIBS="${LIBS}"

echo "==> Stripping"
"${MUSL_CC%%gcc}strip" -s python 2>/dev/null || strip -s python

echo ""
echo "Build complete."
ls -lh "${BUILDDIR}/python"
file "${BUILDDIR}/python" 2>/dev/null || true
echo ""
echo "Verify static musl binary and no GPL modules:"
echo "  ldd ${BUILDDIR}/python 2>&1 || true"
echo "  ${BUILDDIR}/python -c \"import sys; print(sys.version); print('readline' in sys.builtin_module_names)\""
echo ""
du -sh "${SRCDIR}/Modules" "${SRCDIR}/Lib" 2>/dev/null || true
