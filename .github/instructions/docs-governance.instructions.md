---
name: "Documentation Governance"
description: "Rules for docs, CI status, test numbers, and governance reports"
applyTo: "**"
---

# Documentation Governance Rules

When changing CI, tests, test counts, security status, command counts, or
governance status:

- Read `docs/status/CURRENT_STATUS.md` first.
- Read `docs/architecture/DOC_GOVERNANCE_RULES.md`.
- Read `docs/architecture/FACT_PROPAGATION_MATRIX.md`.
- Update Chinese and English mirror sections together.
- Search stale facts with numeric and natural-language forms:
  - `99`, `120`, `126`, `132`, `54 skipped`
  - `passed`, `skipped`, `failed`, `not installed`, `No Windows runner`
  - `通过`, `跳过`, `失败`, `未安装`, `无 Windows CI`, `现有`
- Distinguish status levels:
  - Configured: configuration was changed.
  - Runnable: dependencies are present.
  - Locally verified: local command completed.
  - CI verified: GitHub Actions completed.
- Never mark CI-only behavior as verified until CI has actually run.
- If `.github/workflows/ci.yml` changes, check `CURRENT_STATUS.md`,
  `docs/development/TESTING.md`, and governance reports.
