# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AICoreUtils is a **JSON-first CLI toolkit for LLM agents**, inspired by GNU Coreutils but not a full clone. It exposes 116 commands (111 in the priority catalog + 5 meta-commands: catalog, schema, coreutils, tool-list, hash) via CLI and an MCP server, with deterministic JSON envelopes so agents can parse output reliably. Package name: `aicoreutils` (v1.1.2), requires Python >= 3.11, zero runtime dependencies. Version is single-sourced from pyproject.toml via `importlib.metadata`.

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
uv run pytest tests/test_unit_utils_path.py -v         # Path utilities unit tests
uv run pytest tests/test_concurrency.py -v             # Async + MCP concurrency
uv run pytest tests/test_large_input.py -v             # Large-input behavior (slow, 100 MB)
uv run pytest tests/test_unit_commands_text.py -v      # Text command handlers (direct call)
uv run pytest tests/test_unit_commands_system.py -v    # System command handlers
uv run pytest tests/test_unit_commands_fs.py -v        # FS command handlers
uv run pytest tests/test_error_recovery.py -v          # Disk full, permission, signal tests

# Coverage (threshold: 70%)
uv run pytest tests/ --cov=src/aicoreutils --cov-fail-under=70

# Lint and typecheck (match CI scope)
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/aicoreutils/ --strict

# Run a single test
uv run pytest tests/test_cli_black_box.py::test_ls_basic -v --tb=short

# Run the CLI from source
uv run aicoreutils ls . --limit 20
uv run aicoreutils schema --pretty
uv run aicoreutils catalog --category fs       # Filter catalog by domain
uv run aicoreutils catalog --search "sort"     # Fuzzy-search commands

# Run the MCP server
uv run aicoreutils-mcp --read-only
uv run aicoreutils-mcp --profile workspace-write

# Run pre-commit checks (same as CI lint gate)
uv run pre-commit run --all-files

# Generate shell completions
uv run python scripts/generate_completions.py bash > aicoreutils-complete.bash
uv run python scripts/generate_completions.py zsh > _aicoreutils
uv run python scripts/generate_completions.py fish > aicoreutils.fish
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
docs/               Documentation (reference, guides, architecture, development, status, audits; QUICKSTART.md, COMPATIBILITY.md)
tests/              Test suite (35 test files, stress/, conftest, support, golden/)
examples/           Examples and agent tasks
scripts/            CI audit, release gate, bump version, generate status
.github/scripts/    WSL CI helpers and golden output updater
.github/workflows/  CI (tests, publish) + stress-test.yml (weekly 24h)
vendor/             Local upstream GNU coreutils cache
Dockerfile          Containerized MCP server deployment
```

### JSON envelope contract

Every command outputs:
- **Success** (stdout): `{"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}`
- **Failure** (stderr): `{"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}`

Pass `--raw` to bypass the envelope for pipeline composition.

The `warnings` list may contain deprecation notices (via `deprecation_warning()` in `core/envelope.py`). See `docs/COMPATIBILITY.md` for the deprecation policy and stability commitments.

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

See `docs/reference/SECURITY_MODEL.md` for the full security model.

- All mutating commands (20 total) must pass `require_inside_cwd` before operating.
- Symlink escapes are caught by `resolve_path` resolving real paths before boundary checks.
- Dangerous commands (`shred`, `kill`, `nice`, `nohup`, `stty`, `chcon`, `runcon`, `chroot`) require explicit `--allow-*` flags.
- MCP server supports `--profile readonly`, `--profile workspace-write`, `--allow-command`, `--deny-command` (and the shorthand `--read-only`).

### Plugin system

Third-party packages named `aicoreutils_*` are auto-discovered via `registry/plugins.py`. `PluginRegistry` (in `core/plugin_registry.py`) provides an immutable, thread-safe registry.

### Testing command handlers directly

Command unit tests use the real parser to build proper `argparse.Namespace` objects, then call handlers directly — no subprocess overhead:

```python
from aicoreutils.parser._parser import build_parser
_parser = build_parser()
args = _parser.parse_args(["sort", "--reverse", "file.txt"])
result = args.func(args)  # calls command_sort directly, coverage counts
```

### Recent GNU compatibility additions

- `sort --stable` / `sort --check` — Python sort is already stable; check mode returns `{sorted, disorder_line}`
- `chmod/chown/chgrp --reference` — copy mode/owner/group from a reference file
- `md5sum/sha*sum/b2sum --check` — verify checksums from a checksum file, JSON `{ok, failed, entries}`
- `wc --files0-from` — read NUL-separated file list
- `dd --conv=notrunc,noerror,fsync,sync` — data conversion options

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

CI also runs these audit scripts (all must pass before merge):
- `scripts/audit_command_matrix.py` — risk/test coverage per command
- `scripts/audit_command_specs.py` — spec registry vs parser consistency
- `scripts/audit_supply_chain.py` — pinned actions, dependabot, Dockerfile hardening
- `scripts/release_gate.py` — meta-gate that runs all of the above plus tests

### Release process

1. All CI checks pass (lint, typecheck, tests × 3 platforms × 3 Python versions)
2. `scripts/release_gate.py` passes
3. Bump version with `scripts/bump_version.py <new_version>`
4. Update `CHANGELOG.md`
5. Tag `v<new_version>` and push — CI publishes to PyPI automatically

## Behavioral guidelines

The four behavioral principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) are defined in the user-level `~/.claude/CLAUDE.md` and take precedence. `docs/architecture/` contains project-specific governance and architecture rules.

## Directory governance

- New source modules go under `src/aicoreutils/` following the existing layer stack.
- New command registry entries belong in `registry/catalog.py` (not in top-level files).
- New documentation goes in `docs/` under the appropriate subdirectory. Update `docs/README.md` to link it.
- New tests go in `tests/`. Test files should be named `test_<area>.py`.
- When adding a new mutating command, update the sandbox safety checks in `core/sandbox.py`.
- All tool caches live under `.cache/` (gitignored): `.cache/pytest_cache/`, `.cache/ruff_cache/`, `.cache/mypy_cache/`, `.cache/coverage/`.
