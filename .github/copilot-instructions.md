# Copilot Instructions

## Project-Specific Rules

Project-specific documentation governance rules live in:

- `project/docs/status/CURRENT_STATUS.md` — single authoritative status source
- `project/docs/agent-guides/DOC_GOVERNANCE_RULES.md` — docs/CI/test governance rules
- `project/docs/agent-guides/FACT_PROPAGATION_MATRIX.md` — fact propagation targets

Main test entry: `python -m pytest project/tests/ -v --tb=short`.
For Ubuntu/GNU CI parity on Windows, use `.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps` after WSL is installed.

## Behavioral Guidelines

See `project/docs/agent-guides/CLAUDE.md` for the canonical behavioral guidelines (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution). This project's `CLAUDE.md` is the single authoritative source for those principles.
