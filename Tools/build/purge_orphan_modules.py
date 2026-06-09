#!/usr/bin/env python3
"""Delete C module sources and clinic headers not in the minimal build set."""

import sys
from pathlib import Path

KEEP_ROOT = {
    'arraymodule.c', 'atexitmodule.c', 'errnomodule.c', 'faulthandler.c',
    'fcntlmodule.c', 'gcmodule.c', 'getaddrinfo.c', 'getbuildinfo.c',
    'getnameinfo.c', 'getpath.c', 'getpath_noop.c', 'itertoolsmodule.c',
    'main.c', 'mathintegermodule.c', 'mathmodule.c', 'posixmodule.c',
    'selectmodule.c', 'signalmodule.c', 'socketmodule.c', 'symtablemodule.c',
    'timemodule.c', '_abc.c', '_bisectmodule.c', '_codecsmodule.c',
    '_collectionsmodule.c', '_csv.c', '_datetimemodule.c', '_functoolsmodule.c',
    '_heapqmodule.c', '_json.c', '_localemodule.c', '_opcode.c', '_operator.c',
    '_pickle.c', '_posixsubprocess.c', '_queuemodule.c', '_randommodule.c',
    '_stat.c', '_struct.c', '_suggestions.c', '_sysconfig.c', '_threadmodule.c',
    '_tracemalloc.c', '_typesmodule.c', '_typingmodule.c', '_weakref.c',
}

KEEP_SUB = {
    '_io/_iomodule.c', '_io/iobase.c', '_io/fileio.c', '_io/bytesio.c',
    '_io/bufferedio.c', '_io/textio.c', '_io/stringio.c',
    '_sre/sre.c',
}

KEEP_CLINIC = set()
for name in KEEP_ROOT:
    KEEP_CLINIC.add(name.replace('.c', '.c.h'))
for sub in KEEP_SUB:
    KEEP_CLINIC.add(Path(sub).name.replace('.c', '.c.h'))
KEEP_CLINIC.update({
    'sre.c.h', 'bytesio.c.h', 'fileio.c.h', 'iobase.c.h', 'bufferedio.c.h',
    'textio.c.h', 'stringio.c.h', '_iomodule.c.h', 'gcmodule.c.h',
})


def purge_modules(modules: Path) -> None:
    for path in modules.glob('*.c'):
        if path.name not in KEEP_ROOT:
            print(f'  removed: {path}')
            path.unlink()
    for path in modules.rglob('*.c'):
        if path.parent == modules:
            continue
        rel = str(path.relative_to(modules))
        if rel not in KEEP_SUB:
            print(f'  removed: {path}')
            path.unlink()
    clinic = modules / 'clinic'
    if clinic.is_dir():
        for path in clinic.glob('*.h'):
            if path.name not in KEEP_CLINIC:
                print(f'  removed: {path}')
                path.unlink()


def main():
    root = Path(sys.argv[1])
    print('==> Purging orphan Modules/*.c and clinic headers')
    purge_modules(root / 'Modules')


if __name__ == '__main__':
    main()
