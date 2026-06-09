#!/usr/bin/env python3
"""Remove comments and docstrings from C and Python source files in-place."""

import ast
import io
import sys
import tokenize
from pathlib import Path


def strip_c_comments(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    state = 'code'
    while i < n:
        c = text[i]
        if state == 'code':
            if c == '"':
                state = 'str_dq'
                out.append(c)
                i += 1
            elif c == "'":
                state = 'str_sq'
                out.append(c)
                i += 1
            elif c == '/' and i + 1 < n:
                nxt = text[i + 1]
                if nxt == '/':
                    state = 'line_comment'
                    i += 2
                elif nxt == '*':
                    state = 'block_comment'
                    i += 2
                else:
                    out.append(c)
                    i += 1
            else:
                out.append(c)
                i += 1
        elif state == 'str_dq':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
            elif c == '"':
                state = 'code'
                i += 1
            else:
                i += 1
        elif state == 'str_sq':
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
            elif c == "'":
                state = 'code'
                i += 1
            else:
                i += 1
        elif state == 'line_comment':
            if c == '\n':
                state = 'code'
                out.append(c)
            i += 1
        elif state == 'block_comment':
            if c == '*' and i + 1 < n and text[i + 1] == '/':
                state = 'code'
                i += 2
            else:
                i += 1
    return ''.join(out)


class DocstringStripper(ast.NodeTransformer):
    def _strip_doc(self, node):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body.pop(0)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)

    def visit_Module(self, node):
        self.generic_visit(node)
        return self._strip_doc(node)


SKIP_PYTHON = {
    'importlib/_bootstrap.py',
    'importlib/_bootstrap_external.py',
    'encodings/__init__.py',
    'encodings/aliases.py',
    'encodings/utf_8.py',
    'encodings/latin_1.py',
    'encodings/ascii.py',
    'codecs.py',
    'io.py',
    'abc.py',
    'site.py',
    'os.py',
    'stat.py',
    'genericpath.py',
    'posixpath.py',
    'ntpath.py',
    'warnings.py',
    '_py_warnings.py',
    'keyword.py',
    'reprlib.py',
    'copyreg.py',
    '_weakrefset.py',
    'encodings/_win_cp_codecs.py',
}


def strip_python(path: Path) -> None:
    rel = path.as_posix().split('/Lib/', 1)[-1] if '/Lib/' in path.as_posix() else path.name
    if rel in SKIP_PYTHON:
        return
    src = path.read_text(encoding='utf-8')
    tokens = []
    changed = False
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            changed = True
            continue
        tokens.append(tok)
    if not changed:
        return
    stripped = tokenize.untokenize(tokens)
    if stripped != src:
        path.write_text(stripped, encoding='utf-8')


def strip_c(path: Path) -> None:
    src = path.read_text(encoding='utf-8', errors='surrogateescape')
    stripped = strip_c_comments(src)
    lines = [line.rstrip() for line in stripped.splitlines()]
    compact = '\n'.join(line for line in lines if line)
    if not compact.endswith('\n'):
        compact += '\n'
    if compact != src:
        path.write_text(compact, encoding='utf-8', errors='surrogateescape')


def main(argv):
    roots = [Path(p) for p in argv[1:]]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            if path.suffix == '.py':
                strip_python(path)


if __name__ == '__main__':
    main(sys.argv)
