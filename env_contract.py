#!/usr/bin/env python3
"""Compare static Python environment accesses with names in an example file."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import sys
import tokenize

SKIP = {'.git', '.hg', '.svn', '.venv', 'venv', 'env', 'node_modules', 'build', 'dist', '__pycache__', '.tox', '.mypy_cache', '.pytest_cache', 'site-packages'}
NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'error: invalid command arguments; see --help\n')


def example_names(path):
    names = set()
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        name, sep, _ = line.partition('=')
        name = name.strip()
        if not sep or not NAME.fullmatch(name):
            raise ValueError('invalid example assignment')
        if name in names:
            raise ValueError('duplicate example name')
        names.add(name)
    return names


def accesses(tree, relative):
    modules, getters, environs = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.asname or 'os' for a in node.names if a.name == 'os')
        elif isinstance(node, ast.ImportFrom) and node.module == 'os':
            getters.update(a.asname or a.name for a in node.names if a.name == 'getenv')
            environs.update(a.asname or a.name for a in node.names if a.name == 'environ')

    def attr(node, name):
        return isinstance(node, ast.Attribute) and node.attr == name and isinstance(node.value, ast.Name) and node.value.id in modules

    def environ(node):
        return (isinstance(node, ast.Name) and node.id in environs) or attr(node, 'environ')

    usages, incomplete = [], []
    augmented = {id(node.target) for node in ast.walk(tree) if isinstance(node, ast.AugAssign)}
    for node in ast.walk(tree):
        key = default = None
        indexed = False
        recognized = False
        if isinstance(node, ast.Subscript) and environ(node.value):
            if not isinstance(node.ctx, ast.Load) and id(node) not in augmented:
                continue
            key, indexed, recognized = node.slice, True, True
        elif isinstance(node, ast.Call):
            f = node.func
            if attr(f, 'getenv') or (isinstance(f, ast.Name) and f.id in getters) or (isinstance(f, ast.Attribute) and f.attr == 'get' and environ(f.value)):
                recognized = True
                key = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == 'key'), None)
                default = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == 'default'), None)
                if any(k.arg is None for k in node.keywords) or any(isinstance(a, ast.Starred) for a in node.args):
                    incomplete.append({'path': relative, 'line': node.lineno, 'reason': 'expanded environment arguments'})
            elif isinstance(f, ast.Attribute) and environ(f.value):
                incomplete.append({'path': relative, 'line': node.lineno, 'reason': 'unsupported environment method'})
        if recognized:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                incomplete.append({'path': relative, 'line': node.lineno, 'reason': 'dynamic environment name'})
                continue
            classification = 'required' if indexed else ('optional' if default is None or isinstance(default, ast.Constant) else 'unknown')
            usages.append({'name': key.value, 'classification': classification, 'path': relative, 'line': node.lineno})
    return usages, incomplete


def scan(root, documented):
    usages, incomplete = [], []
    scanned_files = 0

    def walk_error(_):
        incomplete.append({'path': '.', 'reason': 'directory read failure'})

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (base / d).is_symlink() and (base / d).resolve().is_relative_to(root))
        for name in sorted(files):
            path = base / name
            if path.suffix != '.py' or path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            relative = path.relative_to(root).as_posix()
            try:
                with tokenize.open(path) as stream:
                    tree = ast.parse(stream.read())
                scanned_files += 1
                found, issues = accesses(tree, relative)
                usages.extend(found)
                incomplete.extend(issues)
            except (OSError, UnicodeError, SyntaxError, ValueError, RecursionError):
                incomplete.append({'path': relative, 'reason': 'source parse or read failure'})
    if scanned_files == 0:
        incomplete.append({'path': '.', 'reason': 'no readable Python source files'})
    used = {row['name'] for row in usages}
    return {'usages': sorted(usages, key=lambda r: (r['path'], r['line'], r['name'])),
            'missing': sorted(used - documented), 'example_only': sorted(documented - used),
            'incomplete': incomplete, 'scanned_files': scanned_files}


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('root', type=Path, help='Python source directory')
    parser.add_argument('--example', required=True, type=Path, help='example file; names only are parsed')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('root must be a directory')
        report = scan(root, example_names(args.example))
    except (OSError, UnicodeError, ValueError, RecursionError):
        print('error: cannot read root or parse example file', file=sys.stderr)
        return 2
    if args.format == 'json':
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        for row in report['usages']:
            print(f"{row['path']}:{row['line']} {row['name']} ({row['classification']})")
        print('Missing: ' + ', '.join(report['missing']))
        print('Example only: ' + ', '.join(report['example_only']))
        print(f"Scanned files: {report['scanned_files']}")
        print(f"Incomplete checks: {len(report['incomplete'])}")
    return 3 if report['incomplete'] else (1 if report['missing'] or report['example_only'] else 0)


if __name__ == '__main__':
    sys.exit(main())
