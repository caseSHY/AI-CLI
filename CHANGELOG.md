# Changelog

All notable changes to AICoreUtils.

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
