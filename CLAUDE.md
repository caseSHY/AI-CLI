# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AICoreUtils is a **JSON-first CLI toolkit for LLM agents**, inspired by GNU Coreutils but not a full clone. It exposes 114 commands via CLI and an MCP server, with deterministic JSON envelopes so agents can parse output reliably. Package name: `aicoreutils` (v1.1.2), requires Python >= 3.11, zero runtime dependencies.

## Commands

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run all tests (primary entry)
python -m pytest project/tests/ -v --tb=short

# Run a single test file
python -m pytest project/tests/test_cli_black_box.py -v --tb=short

# Run specific test subsets
python -m pytest project/tests/test_property_based_cli.py -v      # Hypothesis property-based
python -m pytest project/tests/test_gnu_differential.py -v        # GNU differential (needs GNU coreutils)
python -m pytest project/tests/test_sandbox_escape_hardening.py -v # Sandbox escape hardening
python -m pytest project/tests/test_docs_governance.py -v         # Docs governance checks
python -m pytest project/tests/test_docs_bilingual.py -v          # Bilingual docs check
python -m pytest tests/test_version_consistency.py -v             # Version consistency

# Coverage (threshold: 45%)
python -m pytest project/tests/ --cov=src/aicoreutils --cov-fail-under=45

# Lint and typecheck
ruff check src/ project/tests/
ruff format --check src/ project/tests/
mypy src/aicoreutils/ --strict

# Run a single test
python -m pytest project/tests/test_cli_black_box.py::test_ls_basic -v --tb=short

# Run the CLI from source
PYTHONPATH=src python -m aicoreutils ls . --limit 20
PYTHONPATH=src python -m aicoreutils schema --pretty
```

## Architecture

### Layer stack (bottom → top)

```
core/          Foundation: exit codes, exceptions, JSON envelope, path utils, sandbox, streaming, constants
protocol/      Domain utilities: argparse wrapper, I/O, hashing, text processing, ranges, printf, numfmt, system, path
commands/      Command handlers organized by category: fs/, system/, text/
parser/        CLI entry point: builds argparse tree, dispatches to handlers
catalog.py     Authoritative priority catalog of all 114 commands (P0-P3)
mcp_server.py  MCP server: JSON-RPC 2.0 over stdio, no external deps
```

### JSON envelope contract

Every command outputs:
- **Success** (stdout): `{"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}`
- **Failure** (stderr): `{"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}`

Pass `--raw` to bypass the envelope for pipeline composition.

### Semantic exit codes

`src/aicoreutils/core/exit_codes.py` — `EXIT` dict maps semantic codes to POSIX codes. `8` is reserved for sandbox safety rejections (`unsafe_operation`).

### Command handler contract

Every command in `commands/fs/_core.py`, `commands/system/_core.py`, `commands/text/_core.py` follows:
1. Path resolution + sandbox validation (`resolve_path` + `require_inside_cwd`)
2. Safety checks (`dangerous_delete_target` + `refuse_overwrite`)
3. `dry_run` early return (`if args.dry_run: return {...}`)
4. Execute and collect results
5. Return JSON-compatible dict or `bytes` (raw mode)

### Sandbox safety

- All mutating commands (20 total) must pass `require_inside_cwd` before operating.
- Symlink escapes are caught by `resolve_path` resolving real paths before boundary checks.
- Dangerous commands (`shred`, `kill`, `nice`, `nohup`, `stty`, `chcon`, `runcon`, `chroot`) require explicit `--allow-*` flags.
- MCP server supports `--profile readonly`, `--profile workspace-write`, `--allow-command`, `--deny-command`.

### Plugin system

Third-party packages named `aicoreutils_*` are auto-discovered via `plugins.py`. Shared mutable global state between `catalog.py` and `plugins.py` is known tech debt — `PluginRegistry` (in `core/plugin_registry.py`) is the replacement.

## Governance rules (mandatory)

Before changing docs, CI, tests, security status, command counts, or governance reports, read these three files first:

1. `project/docs/status/CURRENT_STATUS.md` — single authoritative status source
2. `project/docs/agent-guides/DOC_GOVERNANCE_RULES.md` — docs/CI/test governance
3. `project/docs/agent-guides/FACT_PROPAGATION_MATRIX.md` — fact propagation targets

Key rules:
- Do not mark work as "verified" unless a command was actually run or CI completed.
- Chinese and English doc sections must be updated in the same change.
- After changing CI, test counts, security status, or command counts, update `CURRENT_STATUS.md` and check the fact propagation matrix for other docs that need updating.
- Run `scripts/generate_status.py` after modifying any status-tracked metric.
- New behavior must have focused tests before status docs are updated.

## Behavioral guidelines

See `project/docs/agent-guides/CLAUDE.md` for the canonical behavioral principles: Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution.
