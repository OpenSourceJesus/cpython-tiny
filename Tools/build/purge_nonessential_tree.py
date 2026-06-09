#!/usr/bin/env python3
"""Delete source files not required to rebuild python from an existing build dir."""

import subprocess
import sys
from pathlib import Path

KEEP_TOP = {
    'Modules', 'Python', 'Objects', 'Parser', 'Programs', 'Include', 'Lib',
    'Grammar', 'Tools', 'Platforms', 'Misc',
}
KEEP_FILES = {
    'Makefile.pre.in', 'pyconfig.h.in', 'Modules/config.c.in',
    'Modules/Setup.bootstrap.in', 'Modules/Setup.stdlib.in',
    'Modules/Setup.local.minimal', 'Modules/Setup.stdlib.minimal.in',
    'configure', 'configure.ac', 'config.guess', 'config.sub', 'install-sh',
}


def minimal_files(root: Path, build: Path) -> set[str]:
    out = subprocess.check_output(
        [sys.executable, str(root / 'Tools/build/compute_minimal_sources.py'),
         str(root), str(build), '--list'],
        text=True,
    )
    return {line.strip() for line in out.splitlines() if line.strip()}


def main():
    root = Path(sys.argv[1])
    build = Path(sys.argv[2])
    keep = minimal_files(root, build)
    keep.update(KEEP_FILES)
    keep.add('Tools/build/export-minimal-source.sh')
    for path in (root / 'Tools/build').glob('*'):
        if path.is_file():
            keep.add(str(path.relative_to(root)))
    keep.add('Tools/gdb/libpython.py')
    keep.add('Platforms/linux-musl/config.site')

    removed = 0
    for path in sorted(root.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if '.git' in path.parts or any(p.startswith('build-') for p in path.parts):
            continue
        rel = str(path.relative_to(root))
        if path.is_dir():
            if path.name in KEEP_TOP and path.parent == root:
                continue
            if not any(k.startswith(rel + '/') or k == rel for k in keep):
                if path.exists():
                    print(f'  removed dir: {rel}')
                    import shutil
                    shutil.rmtree(path)
                    removed += 1
            continue
        if rel not in keep:
            print(f'  removed: {rel}')
            path.unlink(missing_ok=True)
            removed += 1

    total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file()
                and '.git' not in p.parts
                and not any(part.startswith('build-') for part in p.parts))
    print(f'==> Removed {removed} paths; tree now {total / 1024 / 1024:.2f} MB')


if __name__ == '__main__':
    main()
