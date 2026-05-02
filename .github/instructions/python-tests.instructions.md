---
name: "Python Test Rules"
description: "Rules for Python code, tests, and documented verification"
applyTo: "**/*.py"
---

# Python Test Rules

- Use `python -m pytest project/tests/ -v --tb=short` as the main verification command.
- Set `PYTHONPATH=src` when running tests from a source checkout without an
  editable install.
- Do not update documented test counts unless the relevant test command was
  actually run.
- Preserve sandbox and dry-run safety behavior unless the user explicitly asks
  to change it.
- New behavior should have focused tests before the documented status is
  changed.
