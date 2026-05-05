# Changelog

All notable changes to AICoreUtils.
## [1.1.1] - 2026-05-05

### Security (Critical)
- Fix csplit/split bypass: commands were in both _READ_ONLY_TOOLS and _DESTRUCTIVE_TOOLS,
  allowing file writes under MCP --read-only mode

### Added
- 5 cwd boundary escape tests (mkfifo, mknod, csplit, split, nohup)
- 4 overwrite protection tests (cp, mv, ln, link)
- test_project_consistency.py: classification overlap, catalog duplicates, all-classified checks
- scripts/bump_version.py: semi-automated version bump for all 5 version files + CHANGELOG

### Changed
- scripts/generate_status.py: robust --write mode with auto-update for CURRENT_STATUS.md
- CONTRIBUTING.md: updated release process with bump_version.py + generate_status.py

### Fixed
- README production pin: 1.0.1 → 1.1.0
- CURRENT_STATUS.md: commit hash, macOS Python matrix (3.12/3.13 → 3.11/3.12/3.13)
- CURRENT_STATUS.md: self-contradiction (version consistency "CI未纳入" while in CI cmd)
- SECURITY_MODEL.md: add csplit/split/nohup to CN+EN cwd coverage list
- catalog.py: remove duplicate mknod from P3 group; fix stale comment
- Pre-commit hooks: check-yaml, check-toml, check-json, detect-private-key, end-of-file-fixer, trailing-whitespace

### CI
- New status-check job verifies CURRENT_STATUS.md consistency
- publish.yml: automatic GitHub Release creation from CHANGELOG on tag push

### Testing
- test_version_consistency.py: +3 tests (CURRENT_STATUS version, README pin, CI pipeline claim)
- test_project_consistency.py: 4 classification integrity tests
- Sandbox escape tests: 46 → 58 (+12 new tests)


## [1.1.0] - 2026-05-05

### Added
- MCP server: `--read-only`, `--allow-command`, `--deny-command` three-tier access control
- CWD sandbox: `require_inside_cwd()` now enforced on all 20 mutating commands (was 5)
- PRODUCTION_SECURITY.md: deployment security guide
- `scripts/generate_status.py`: auto-sync tool for CURRENT_STATUS.md
- 33 new tests (10 MCP security integration + 13 cwd escape + 10 security unit)
- Pre-commit hooks: check-yaml, check-toml, check-json, detect-private-key, end-of-file-fixer, trailing-whitespace
- CI: concurrency group, pip cache on all 3 platforms, Windows choco coreutils
- Dependabot: Docker ecosystem monitoring
- Dockerfile: non-root user

### Changed
- `_READ_ONLY_TOOLS`: sync, sleep, timeout, stdbuf, stty, nice, csplit, split reclassified to destructive
- `.gitignore`: added *.log, *.tmp, .python-version

### Security
- MCP server: deny list takes priority over allow list; allow list overrides read-only mode
- SECURITY_MODEL.md: MCP security controls section with recommended production configs
- All security denials return structured JSON `{"error":{"code":"SECURITY_DENIED",...}}`

## [1.0.3] - 2026-05-05

### Fixed
- CURRENT_STATUS.md: synced version from 0.4.4 to 1.0.2, CI job count 10/10→11/11, coverage threshold 25%→45%
- CONTRIBUTING.md: coverage threshold 35%→45%
- README.md: replaced static "CI 12/12" with GitHub Actions badge
- CHANGELOG.md: fixed outdated CI job count
- COMMUNITY_LAUNCH_COPY.md: fixed job count 12→11

### Changed
- test_docs_governance.py: version assertion now dynamic (reads `__version__`), test count assertions use regex — prevents future doc staleness

### Removed
- Closed resolved known issues K-004 (version consistency in CI) and K-005 (mcp_server 0% coverage)

## [1.0.2] - 2026-05-05

### Added
- CHANGELOG.md

### Changed
- Development Status classifier: Alpha → Beta
- README: added SemVer stability notice

## [1.0.1] - 2026-05-04

### Fixed
- `date` command: non-ASCII timezone names replaced with UTC offset format (fixes garbled output on Windows with CJK locales)

### Removed
- Obsolete planning documents (`PROJECT_ITERATION_PLAN_v2.md`, `TDQS_DEVELOPMENT_PLAN.md`)

## [1.0.0] - 2026-05-04

Milestone release. 114 tools all A-grade TDQS (avg 4.6), Glama 92%, CI all platforms passing.

### Added
- AI IDE integration guide (Cursor, Windsurf, Continue.dev)
- Agent task examples
- LangChain tool wrapper
- Community launch copy (HN / Reddit / Chinese platforms)

### Changed
- All 114 tool descriptions rewritten using paper-backed 5-segment best-practices template

### Fixed
- CI: GitHub Actions upgraded to Node.js 24 (`checkout@v6`, `setup-python@v6`, `upload-artifact@v7`, `download-artifact@v8`)

## [0.5.1] - 2026-05-04

### Changed
- CI: GitHub Actions versions bumped (Node.js 24 migration)
- Code review: `os.path` already fully migrated to `pathlib` — no changes needed

## [0.5.0] - 2026-05-04

### Added
- 8 new `async_interface` execution tests

### Changed
- CI coverage gate raised 35% → 45%

## [0.4.9] - 2026-05-04

### Changed
- All 114 tool descriptions rewritten with 5-segment best-practices template (Purpose + Behavior + Output + Usage + Alternatives), based on arXiv papers 2602.14878 and 2602.18914

## [0.4.8] - 2026-05-04

### Fixed
- TDQS: `mkfifo` description improved (B 3.3 → A ~4.0)

## [0.4.7] - 2026-05-04

### Added
- 26 unit tests for `mcp_server.py` (`_call_tool`, protocol parsing, server loop, entry point) — 覆盖率 0% → 90%

### Changed
- CI: 覆盖率门禁 25% → 35%
- CI: macOS 矩阵新增 Python 3.11
- CI: 上传 coverage.xml artifact 用于历史趋势追踪

### Fixed
- TDQS: `basenc` 工具描述 — 补充 `--base`/`--decode`/`--raw` 使用说明，明确与 `base64`/`base32` 的区别

## [0.4.6] - 2026-05-04

### Fixed
- TDQS: `nice` 工具描述 — 说明子进程执行、输出捕获、超时、与 stdbuf/nohup/timeout 的区别
- TDQS: `stdbuf` 工具描述 — 补充缓冲模式默认行为、子进程执行、与 nice/timeout 的区别
- TDQS: `dir` 工具描述 — 补充输出格式、参数、与 ls/vdir 的区别
- TDQS: `ginstall`/`install` 工具描述 — 补充副作用、典型用法、与 cp 的区别

## [0.4.5] - 2026-05-04

### Fixed
- CI: 修复 8 个 GitHub Actions 版本号 (v6/v7/v8 → v4/v5)
- CI: Ubuntu job 添加 `apt-get update` 防止包索引过期
- CI: `tests/test_version_consistency.py` 纳入 CI pipeline
- 文档: `CURRENT_STATUS.md` 同步到 v0.4.4 真实状态
- 文档: `TDQS_DEVELOPMENT_PLAN.md` 添加中英双语标记
- `.gitignore` 损坏修复，补充 `.coverage`/`coverage.xml`/`.opencode/` 规则
- pre-commit: hook id `ruff-check` → `ruff`

## [0.4.4] - 2026-05-01

### Added
- 插件测试隔离 API: `reset_plugins()`
- 114 工具完整 TDQS 评分体系

### Fixed
- mypy no-redef 和 operator 错误
- 插件命令测试隔离问题

## [0.4.3] - 2026-04-30

### Fixed
- CI 测试隔离 — 插件命令测试不再相互影响

## [0.4.2] - 2026-04-30

### Fixed
- CI 失败 — 放松插件工具数量断言、新增双语标记

## [0.4.1] - 2026-04-30

### Fixed
- coreutils 描述与 schema 对齐

## [0.4.0] - 2026-04-29

### Added
- 114 个命令全部可用
- MCP JSON-RPC server (stdlib 实现，零外部依赖)
- 插件系统 (命名空间包自动发现)
- 异步接口 (`run_async`/`run_async_many`)
- 流式 JSON 输出 (NDJSON)
- 沙箱安全模型 (路径校验、dry-run、符号链接防护)
- GNU Coreutils 兼容层 (109 个命令名)
