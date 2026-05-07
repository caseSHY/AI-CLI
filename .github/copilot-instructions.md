# Copilot Instructions

## Project-Specific Rules

Project-specific documentation governance rules live in:

- `docs/status/CURRENT_STATUS.md` — single authoritative status source
- `docs/architecture/DOC_GOVERNANCE_RULES.md` — docs/CI/test governance rules
- `docs/architecture/FACT_PROPAGATION_MATRIX.md` — fact propagation targets

Main test entry: `python -m pytest tests/ -v --tb=short`.
For Ubuntu/GNU CI parity on Windows, use `.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps` after WSL is installed.

## Behavioral Guidelines

See the root `CLAUDE.md` for behavioral guidelines (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution).
