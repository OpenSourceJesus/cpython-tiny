#!/bin/sh
# Permanently remove unused CPython source for minimal musl static builds.
#
# Deletes directories and files from the source tree.  Run once before building
# with Tools/build/build-minimal-musl.sh.
#
# Restore original tree (if using git):
#   git checkout -- Lib/ Modules/ Doc/ PC/ Tools/ Mac/ Android/ iOS/ Platforms/
#   mv Modules/Setup.stdlib.in.full Modules/Setup.stdlib.in  # if backup exists
#
# Usage: Tools/build/prune-minimal-source.sh [--dry-run]

set -eu

SRCDIR=$(cd "$(dirname "$0")/../.." && pwd)
DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    echo "==> dry run (no files removed)"
fi

rm_path() {
    if [ ! -e "$1" ]; then
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  would remove: $1"
    else
        rm -rf "$1"
        echo "  removed: $1"
    fi
}

echo "==> Pruning CPython source tree at ${SRCDIR}"

# --- Replace Setup.stdlib.in with minimal module list ---
if [ ! -f "${SRCDIR}/Modules/Setup.stdlib.in.full" ]; then
    if [ "$DRY_RUN" = 0 ]; then
        cp "${SRCDIR}/Modules/Setup.stdlib.in" \
           "${SRCDIR}/Modules/Setup.stdlib.in.full"
    fi
    echo "==> Saved Modules/Setup.stdlib.in.full backup"
fi
if [ "$DRY_RUN" = 0 ]; then
    cp "${SRCDIR}/Modules/Setup.stdlib.minimal.in" \
       "${SRCDIR}/Modules/Setup.stdlib.in"
fi
echo "==> Using Modules/Setup.stdlib.minimal.in"

# --- Modules/ extension directories ---
echo "==> Removing Modules/ extension directories"
for dir in \
    _ctypes _decimal expat cjkcodecs _zstd _remote_debugging \
    _testcapi _testinternalcapi _testlimitedcapi _xxtestfuzz \
    _hacl _sqlite _multiprocessing
do
    rm_path "${SRCDIR}/Modules/${dir}"
done

# --- Individual Modules/*.c files ---
echo "==> Removing unused Modules/*.c sources"
for f in \
    readline.c _gdbmmodule.c _dbmmodule.c _cursesmodule.c _curses_panel.c \
    zlibmodule.c _lzmamodule.c _bz2module.c binascii.c \
    md5module.c sha1module.c sha2module.c sha3module.c blake2module.c hmacmodule.c \
    cmathmodule.c _statisticsmodule.c _uuidmodule.c _zoneinfo.c \
    _lsprof.c rotatingtree.c syslogmodule.c _scproxy.c \
    _tkinter.c tkappinit.c pyexpat.c _elementtree.c \
    _hashopenssl.c _ssl.c \
    _interpchannelsmodule.c _interpqueuesmodule.c _interpretersmodule.c \
    _asynciomodule.c unicodedata.c unicodedata_db.h unicodename_db.h \
    xxsubtype.c xxmodule.c xxlimited.c xxlimited_35.c xxlimited_3_13.c \
    _testbuffer.c _testclinic.c _testclinic_limited.c _testclinic_depr.c \
    _testimportmultiple.c _testmultiphase.c _testsinglephase.c overlapped.c
do
    rm_path "${SRCDIR}/Modules/${f}"
done

# --- Documentation, tests, platform-specific trees ---
echo "==> Removing Doc/, PC/, and test-only trees"
rm_path "${SRCDIR}/Doc"
rm_path "${SRCDIR}/PC"
rm_path "${SRCDIR}/Lib/test"
rm_path "${SRCDIR}/Lib/idlelib"
rm_path "${SRCDIR}/Lib/tkinter"
rm_path "${SRCDIR}/Lib/turtledemo"
rm_path "${SRCDIR}/Lib/unittest"
rm_path "${SRCDIR}/Lib/ensurepip"
rm_path "${SRCDIR}/Lib/venv"
rm_path "${SRCDIR}/Lib/pydoc_data"
rm_path "${SRCDIR}/Lib/profiling"

# --- Lib/ packages tied to removed extensions ---
echo "==> Removing unused Lib/ packages"
for dir in \
    asyncio concurrent ctypes curses dbm sqlite3 multiprocessing \
    xml xmlrpc email html http urllib wsgiref zoneinfo tomllib lib2to3 \
    imaplib nntplib smtplib poplib ftplib telnetlib mailbox msilib \
    pydoc zipapp _pyrepl logging
do
    rm_path "${SRCDIR}/Lib/${dir}"
done

# --- Lib/ whitelist: delete everything else at top level not in this list ---
echo "==> Pruning Lib/*.py to minimal whitelist"
KEEP_LIB="
    abc.py
    codecs.py
    io.py
    os.py
    runpy.py
    stat.py
    site.py
    linecache.py
    _collections_abc.py
    _sitebuiltins.py
    genericpath.py
    ntpath.py
    posixpath.py
    zipimport.py
    subprocess.py
    socket.py
    threading.py
    functools.py
    operator.py
    copy.py
    copyreg.py
    datetime.py
    warnings.py
    traceback.py
    types.py
    typing.py
    struct.py
    random.py
    pickle.py
    heapq.py
    bisect.py
    queue.py
    contextlib.py
    enum.py
    textwrap.py
    tempfile.py
    shutil.py
    glob.py
    fnmatch.py
    pathlib.py
    locale.py
    signal.py
    selectors.py
    string.py
    weakref.py
    keyword.py
    numbers.py
    reprlib.py
    copyreg.py
    _weakrefset.py
    _py_warnings.py
    __hello__.py
"
for f in "${SRCDIR}"/Lib/*.py; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    keep=0
    for k in $KEEP_LIB; do
        if [ "$base" = "$k" ]; then
            keep=1
            break
        fi
    done
    if [ "$keep" = 0 ]; then
        rm_path "$f"
    fi
done

# Keep Lib/importlib/, Lib/json/, Lib/re/, Lib/collections/, Lib/__phello__/
for dir in collections; do
    if [ ! -d "${SRCDIR}/Lib/${dir}" ]; then
        echo "  note: Lib/${dir}/ not present"
    fi
done

# --- Trim encodings/ ---
echo "==> Trimming Lib/encodings/"
KEEP_ENCODINGS="
    __init__.py aliases.py ascii.py latin_1.py
    utf_8.py utf_8_sig.py idna.py punycode.py _win_cp_codecs.py
"
if [ -d "${SRCDIR}/Lib/encodings" ]; then
    for f in "${SRCDIR}"/Lib/encodings/*.py; do
        [ -e "$f" ] || continue
        base=$(basename "$f")
        keep=0
        for k in $KEEP_ENCODINGS; do
            if [ "$base" = "$k" ]; then
                keep=1
                break
            fi
        done
        if [ "$keep" = 0 ]; then
            rm_path "$f"
        fi
    done
fi

# --- Non-essential Tools/ (keep Tools/build, Tools/freeze, Tools/gdb) ---
echo "==> Removing non-essential Tools/"
for dir in \
    msi peg_generator jit pixi-packages buildbot nuget \
    c-analyzer unicode wasm stringbench i18n ssl \
    cases_generator clinic importbench scripts \
    picklebench patchcheck inspection ftscalingbench \
    check-c-api-docs lockbench unittestgui ubsan tsan
do
    rm_path "${SRCDIR}/Tools/${dir}"
done

# --- Platform-specific source ---
echo "==> Removing platform-specific trees"
for path in \
    Mac Android iOS \
    Platforms/WASI Platforms/emscripten
do
    rm_path "${SRCDIR}/${path}"
done

echo ""
echo "Prune complete."
du -sh "${SRCDIR}/Modules" "${SRCDIR}/Lib" "${SRCDIR}/Tools" 2>/dev/null || true
echo ""
echo "Next: Tools/build/build-minimal-musl.sh"
