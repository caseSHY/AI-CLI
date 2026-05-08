# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AICoreUtils is a **JSON-first CLI toolkit for LLM agents**, inspired by GNU Coreutils but not a full clone. It exposes 114 commands (111 in the priority catalog + 3 meta-commands) via CLI and an MCP server, with deterministic JSON envelopes so agents can parse output reliably. Package name: `aicoreutils` (v1.1.2), requires Python >= 3.11, zero runtime dependencies.

## Commands

```bash
# Install dev environment
uv sync --extra dev

# Run all tests
uv run pytest tests/ -v --tb=short

# Run a single test file
uv run pytest tests/test_cli_black_box.py -v --tb=short

# Run specific test subsets
uv run pytest tests/test_property_based_cli.py -v      # Hypothesis property-based
uv run pytest tests/test_gnu_differential.py -v        # GNU differential (needs GNU coreutils)
uv run pytest tests/test_sandbox_escape_hardening.py -v # Sandbox escape hardening
uv run pytest tests/test_docs_governance.py -v         # Docs governance checks
uv run pytest tests/test_docs_bilingual.py -v          # Bilingual docs check
uv run pytest tests/test_version_consistency.py -v     # Version consistency
uv run pytest tests/test_project_consistency.py -v     # Project consistency

# Coverage (threshold: 45%)
uv run pytest tests/ --cov=src/aicoreutils --cov-fail-under=45

# Lint and typecheck (match CI scope)
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/aicoreutils/ --strict

# Run a single test
uv run pytest tests/test_cli_black_box.py::test_ls_basic -v --tb=short

# Run the CLI from source
uv run aicoreutils ls . --limit 20
uv run aicoreutils schema --pretty
```

## Architecture

### Layer stack (bottom -> top)

```
core/          Foundation: exit codes, exceptions, JSON envelope, path utils, sandbox, streaming, config, constants
utils/         Domain utilities: argparse wrapper, I/O, hashing, text processing, ranges, printf, numfmt, system, path
commands/      Command handlers (fs/_core.py, system/_core.py, text/_core.py — one file per category)
parser/        CLI entry point: single _parser.py builds argparse tree, dispatches to handlers
registry/      Command registry: catalog (111 commands P0-P3), plugins, command_specs, tool_schema
mcp_server.py  MCP server: JSON-RPC 2.0 over stdio, no external deps
async_interface.py  Async wrapper: asyncio subprocess pool for concurrent command execution
```

### Project layout

```
src/aicoreutils/    Python package (core -> utils -> commands -> parser, with registry/)
docs/               Documentation (reference, guides, architecture, development, status, audits, reports)
tests/              Test suite (27 test files, conftest, support, golden/)
examples/           Examples and agent tasks
scripts/            CI audit, release gate, bump version, generate status
vendor/             Local upstream GNU coreutils cache
```

### JSON envelope contract

Every command outputs:
- **Success** (stdout): `{"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}`
- **Failure** (stderr): `{"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}`

Pass `--raw` to bypass the envelope for pipeline composition.

### Semantic exit codes

`src/aicoreutils/core/exit_codes.py` -- `EXIT` dict maps semantic codes to POSIX codes. `8` is reserved for sandbox safety rejections (`unsafe_operation`).

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

Third-party packages named `aicoreutils_*` are auto-discovered via `registry/plugins.py`. `PluginRegistry` (in `core/plugin_registry.py`) provides an immutable, thread-safe registry.

## Governance rules (mandatory)

Before changing docs, CI, tests, security status, command counts, or governance reports, read these three files first:

1. `docs/status/CURRENT_STATUS.md` -- single authoritative status source
2. `docs/architecture/DOC_GOVERNANCE_RULES.md` -- docs/CI/test governance
3. `docs/architecture/FACT_PROPAGATION_MATRIX.md` -- fact propagation targets

Key rules:
- Do not mark work as "verified" unless a command was actually run or CI completed.
- Chinese and English doc sections must be updated in the same change.
- After changing CI, test counts, security status, or command counts, update `CURRENT_STATUS.md` and check the fact propagation matrix for other docs that need updating.
- Run `scripts/generate_status.py` after modifying any status-tracked metric.
- New behavior must have focused tests before status docs are updated.

## Behavioral guidelines

The four behavioral principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) are defined in the user-level `~/.claude/CLAUDE.md` and take precedence. The project root `AGENTS.md` and `docs/architecture/` contain project-specific governance and architecture rules.

## Directory governance

- New source modules go under `src/aicoreutils/` following the existing layer stack.
- New command registry entries belong in `registry/catalog.py` (not in top-level files).
- New documentation goes in `docs/` under the appropriate subdirectory. Update `docs/README.md` to link it.
- New tests go in `tests/`. Test files should be named `test_<area>.py`.
- When adding a new mutating command, update the sandbox safety checks in `core/sandbox.py`.
