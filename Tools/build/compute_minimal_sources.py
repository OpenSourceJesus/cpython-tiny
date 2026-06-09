#!/usr/bin/env python3
"""Compute source files required to rebuild `python` from an existing build dir."""

import re
import sys
from pathlib import Path

SOURCE_PREFIXES = (
    'Modules/', 'Python/', 'Objects/', 'Parser/', 'Programs/', 'Include/',
    'Lib/', 'Grammar/', 'Tools/build/', 'Tools/gdb/', 'Platforms/linux-musl/',
)

BUILD_ARTIFACTS = (
    'Modules/Setup', 'Modules/Setup.local', 'Modules/Setup.bootstrap',
    'Modules/Setup.stdlib', 'Modules/Setup.bootstrap.in', 'Modules/Setup.stdlib.in',
    'pyconfig.h.in', 'Modules/config.c.in',
)


def object_sources(makefile_text: str) -> set[str]:
    objs = set(re.findall(r'(?:^|\s)([\w./-]+\.o)\s*(?:\\|$)', makefile_text, re.M))
    sources = set()
    for obj in objs:
        if not any(obj.startswith(p.rstrip('/')) for p in SOURCE_PREFIXES[:5]):
            continue
        sources.add(obj[:-2] + '.c')
    return sources


def scan_includes(root: Path, paths: set[str]) -> set[str]:
    include_re = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]', re.M)
    seen = set(paths)
    queue = list(paths)
    while queue:
        rel = queue.pop()
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors='replace')
        except OSError:
            continue
        for inc in include_re.findall(text):
            if inc.startswith('Python/') or inc.startswith('internal/'):
                candidates = [inc, f'Include/{inc}', f'Include/cpython/{Path(inc).name}',
                              f'Include/internal/{Path(inc).name}']
            elif '/' in inc:
                candidates = [f'Include/{inc}', inc]
            else:
                candidates = [
                    f'Include/{inc}',
                    f'Include/cpython/{inc}',
                    f'Include/internal/{inc}',
                    inc,
                ]
            for cand in candidates:
                if cand in seen:
                    continue
                if (root / cand).is_file():
                    seen.add(cand)
                    queue.append(cand)
                    break
    return seen


def generated_headers(sources: set[str]) -> set[str]:
    extra = set()
    for src in sources:
        base = Path(src)
        for suffix in ('.c.h', '.h'):
            cand = str(base.with_suffix(base.suffix + '.h' if suffix == '.c.h' else '.h'))
            if cand.endswith('.c.h'):
                extra.add(cand)
        clinic = f'Modules/clinic/{base.name}.h'
        extra.add(clinic)
    extra.update({
        'Python/generated_cases.c.h',
        'Python/executor_cases.c.h',
        'Python/optimizer_cases.c.h',
        'Include/internal/pycore_opcode_metadata.h',
        'Include/internal/pycore_uop_metadata.h',
        'Include/internal/pycore_unicodeobject_generated.h',
        'Include/internal/pycore_global_objects_fini_generated.h',
        'Objects/unicodetype_db.h',
        'Parser/parser.c',
        'Python/Python-ast.c',
    })
    return extra


def lib_runtime(root: Path) -> set[str]:
    keep = set()
    for path in (root / 'Lib').rglob('*'):
        if path.is_file():
            keep.add(str(path.relative_to(root)))
    return keep


def main():
    root = Path(sys.argv[1])
    build = Path(sys.argv[2])
    makefile = (build / 'Makefile').read_text()
    sources = object_sources(makefile)
    sources.update(generated_headers(sources))
    sources.update(BUILD_ARTIFACTS)
    sources.update(scan_includes(root, sources))
    sources.update(lib_runtime(root))
    sources = {p for p in sources if (root / p).exists()}
    total = sum((root / p).stat().st_size for p in sources)
    print(f'{len(sources)} files, {total / 1024 / 1024:.2f} MB')
    if len(sys.argv) > 3 and sys.argv[3] == '--list':
        for p in sorted(sources):
            print(p)


if __name__ == '__main__':
    main()
