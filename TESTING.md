# Verification record

Observed locally on 2026-10-23 (Asia/Singapore, UTC+08:00), as catch-up for the requested 2026-10-22 batch. Runtime: Python 3.11.15 on Windows. These are synthetic local checks, not evidence of production adoption or universal correctness.

Run from this repository directory:

```sh
python -m unittest discover -s tests -v
```

Result: 21 tests discovered; 20 passed, 1 skipped, 0 failures/errors; exit 0. The skipped `test_symlink_not_followed` could not create a symlink under the current Windows privileges, so symlink behavior was not empirically exercised here. It remains runnable on a host with symlink support.

Coverage includes alias imports, literal/dynamic defaults, required reads including augmented assignments, write-only exclusions, missing/unused names, sanitized errors, duplicate example names, invalid input, skip directories, static source handling, counted scans, and incomplete empty/skipped-only roots. The zero-file regressions failed before the completeness fix, then passed after it. A new side-effect fixture verifies that scanning does not execute or modify the source file.

Every top-level `checks.json` entry was run using `[sys.executable, *check["args"]]` with this repository as the working directory; actual return codes matched `exit`:

| Command | Expected / observed exit |
| --- | --- |
| `python env_contract.py --help` | 0 / 0 |
| `python env_contract.py examples/clean --example examples/clean/.env.example --format json` | 0 / 0 |
| `python env_contract.py examples/drift --example examples/drift/.env.example` | 1 / 1 |
| `python env_contract.py examples/dynamic --example examples/dynamic/.env.example --format json` | 3 / 3 |
| `python env_contract.py examples/does-not-exist --example examples/clean/.env.example` | 2 / 2 |

No live application, runtime configuration, business requirement inference, or full data-flow analysis was tested. See README for static-analysis limits.
