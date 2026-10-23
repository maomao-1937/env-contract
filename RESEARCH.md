# Research and scope

Sources checked on 2026-10-22; links document context, not an endorsement or adoption claim.

## Observed facts

- Python documents `getenv` with an optional default and `environ` as the process environment mapping: [Python os documentation](https://docs.python.org/3/library/os.html#os.getenv).
- [dotenv-linter](https://github.com/dotenv-linter/dotenv-linter) checks/fixes dotenv files and compares keys between dotenv files. It already addresses dotenv hygiene and file-to-file drift.

## Design inference

A small code-to-example check may help reviewers notice a newly introduced literal environment access that never reached configuration documentation. This implementation compares Python AST patterns to example-file names; it does not replace dotenv-linter or claim better coverage/performance. The code and examples are independently authored.

## Alternatives and unknowns

Use dotenv-linter for dotenv formatting, duplicate keys and file-to-file comparison. A typed configuration library plus runtime tests can cover application-specific requirements that static getter classification cannot infer. Which approach fits an existing team's workflow, real-world false-negative rate, and demand are unvalidated. No benchmark, user-adoption, first-of-kind, or universal secret-safety claim is made.
