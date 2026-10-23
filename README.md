# env-contract

[![tests](https://github.com/maomao-1937/env-contract/actions/workflows/tests.yml/badge.svg)](https://github.com/maomao-1937/env-contract/actions/workflows/tests.yml)

Catch drift between Python environment-variable accesses and a committed `.env.example` without importing the application or consulting the process environment. Python 3.11+; standard library only; no installation or network access needed.

## Quickstart

Run from this repository directory:

```sh
python env_contract.py examples/clean --example examples/clean/.env.example --format json
python env_contract.py examples/drift --example examples/drift/.env.example
python env_contract.py examples/dynamic --example examples/dynamic/.env.example --format json
python env_contract.py --help
```

Expected exits are `0`, `1`, `3`, `0`. The drift example reports missing `SERVICE_ENDPOINT` and example-only `UNUSED_SETTING`. The dynamic example reports an incomplete scan. `checks.json` records these executable checks.

## What it reports

- Literal `os.getenv`, `os.environ.get`, and `os.environ[...]`, including `import os as x` and `from os import getenv/environ as x`.
- `required` for subscript reads, including augmented assignment; `optional` for getters with no default or a literal default; `unknown` for computed defaults. These describe access behavior, not application business requirements. A getter returning `None` may still be required by later code.
- Source-relative file/line, undocumented names (`missing`), unused example names (`example_only`), and detected incompleteness. Missing names include optional accesses because they still need documentation.

Exit `3` takes priority over drift when a dynamic name, unsupported environment method, parse failure, read failure or zero readable Python source files occurs. Exit `2` means invalid CLI/root/example input; `1` means drift; `0` means no detected drift within the supported scan. JSON has `usages`, `missing`, `example_only`, `incomplete` arrays and a `scanned_files` count of successfully parsed Python files. Empty or skipped-only directories are incomplete (exit `3`). Text and JSON contain names and locations, never example values or source excerpts.

The example parser accepts blank lines, comments and single-line `NAME=value` or `export NAME=value` assignments. Names follow `[A-Za-z_][A-Za-z0-9_]*`; duplicate names are rejected. Values are discarded, never expanded. Multiline dotenv syntax is outside scope. Do not pass a live `.env`: this tool needs documentation names only.

## Static-analysis boundaries

The scanner never executes source, reads live environment values, or follows source symlinks/outside-root resolved paths. It skips `.git`, `.hg`, `.svn`, `.venv`, `venv`, `env`, `node_modules`, `build`, `dist`, `__pycache__`, `.tox`, `.mypy_cache`, `.pytest_cache`, `site-packages` trees. Directory read failures are incomplete.

This is an AST pattern checker, not a data-flow analyzer. Name shadowing, reassignment, star imports, `getattr`, aliases assigned after import, custom config wrappers and generated names can evade or confuse it. It visits all branches, including unreachable code. Direct mapping iteration or passing `os.environ` to a wrapper is not inferred. A clean result is not proof that every runtime variable is documented. Source races during a concurrent scan are not isolated; scan a stable checkout.

## 中文快速开始

需要 Python 3.11 或更新版本，无第三方依赖。在仓库目录运行：

```sh
python env_contract.py examples/clean --example examples/clean/.env.example --format json
```

将 `examples/clean` 换成自己的 Python 源码目录，将 `--example` 换成提交到仓库的示例配置文件。程序只比较变量名，不读取真实环境变量，不执行业务代码。退出码：`0` 未发现差异，`1` 有差异，`2` 输入错误，`3` 扫描不完整。不要将 `optional` 理解为业务一定不需要该变量。

## Verification and context

```sh
python -m unittest discover -s tests -v
```

See [TESTING.md](TESTING.md) for the observed run and [RESEARCH.md](RESEARCH.md) for sources, alternatives and evidence boundaries. MIT license.
