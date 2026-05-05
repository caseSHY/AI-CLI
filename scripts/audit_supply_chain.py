#!/usr/bin/env python3
"""Audit supply-chain and release hardening controls."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.failures.append(message)

    def text(self, relative: str) -> str:
        path = ROOT / relative
        if not path.exists():
            self.failures.append(f"Missing required file: {relative}")
            return ""
        return path.read_text(encoding="utf-8")


def _job_block(workflow: str, job_name: str) -> str:
    lines = workflow.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line == f"  {job_name}:":
            start = index
            break
    if start is None:
        return ""
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^  [A-Za-z0-9_-]+:\s*$", line):
            break
        block.append(line)
    return "\n".join(block)


def _uses_refs(workflow: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for match in re.finditer(r"^\s*-\s+uses:\s+([^\s#]+)", workflow, re.MULTILINE):
        spec = match.group(1).strip()
        if spec.startswith("./"):
            continue
        ref = spec.rsplit("@", 1)[1] if "@" in spec else ""
        refs.append((spec, ref))
    return refs


def _dependency_uses_direct_reference(spec: str) -> bool:
    lower = spec.lower()
    return " @ " in lower or lower.startswith(("git+", "http://", "https://", "file:"))


def audit_pyproject(audit: Audit) -> None:
    raw = audit.text("pyproject.toml")
    if not raw:
        return
    data = tomllib.loads(raw)
    project = data.get("project", {})
    audit.require(project.get("requires-python", "").startswith(">=3.11"), "pyproject.toml must require Python >=3.11.")
    for spec in project.get("dependencies", []):
        audit.require(
            not _dependency_uses_direct_reference(spec), f"Runtime dependency uses a direct reference: {spec}"
        )
    optional = project.get("optional-dependencies", {})
    for group, specs in optional.items():
        for spec in specs:
            audit.require(
                not _dependency_uses_direct_reference(spec),
                f"Optional dependency {group} uses a direct reference: {spec}",
            )
    build_system = data.get("build-system", {})
    for spec in build_system.get("requires", []):
        audit.require(not _dependency_uses_direct_reference(spec), f"Build dependency uses a direct reference: {spec}")


def audit_dependabot(audit: Audit) -> None:
    text = audit.text(".github/dependabot.yml")
    for ecosystem in ('"pip"', '"github-actions"', '"docker"'):
        audit.require(f"package-ecosystem: {ecosystem}" in text, f"Dependabot must cover {ecosystem}.")
    audit.require('timezone: "Asia/Shanghai"' in text, "Dependabot schedule must declare Asia/Shanghai timezone.")
    audit.require("open-pull-requests-limit:" in text, "Dependabot must set an open PR limit.")


def audit_workflows(audit: Audit) -> None:
    workflows = {
        ".github/workflows/ci.yml": audit.text(".github/workflows/ci.yml"),
        ".github/workflows/publish.yml": audit.text(".github/workflows/publish.yml"),
    }
    disallowed_refs = {"main", "master", "head", "latest"}
    for relative, text in workflows.items():
        for spec, ref in _uses_refs(text):
            audit.require(ref != "", f"{relative} action reference is not pinned to a ref: {spec}")
            audit.require(ref.lower() not in disallowed_refs, f"{relative} action reference uses mutable ref: {spec}")
        audit.require(
            "| sh" not in text and "| bash" not in text, f"{relative} must not pipe remote scripts into a shell."
        )

    ci = workflows[".github/workflows/ci.yml"]
    audit.require("permissions:\n  contents: read" in ci, "CI workflow must default to read-only contents permission.")
    audit.require("python scripts/audit_supply_chain.py" in ci, "CI workflow must run the supply-chain audit.")
    audit.require("python scripts/release_gate.py" in ci, "CI workflow must run the release gate.")

    publish = workflows[".github/workflows/publish.yml"]
    audit.require("twine check dist/*" in publish, "Publish workflow must verify package metadata with twine.")
    audit.require("actions/upload-artifact@" in publish, "Publish workflow must upload built dist artifacts.")
    audit.require(
        "actions/download-artifact@" in publish, "Publish workflow must download built dist artifacts for publishing."
    )
    audit.require(
        "pypa/gh-action-pypi-publish@release/v1" in publish,
        "Publish workflow must use PyPI trusted publishing action.",
    )
    audit.require("password:" not in publish, "Publish workflow must not use static PyPI passwords.")
    for job_name in ("build", "testpypi", "pypi"):
        block = _job_block(publish, job_name)
        audit.require(block != "", f"Publish workflow missing job: {job_name}")
    audit.require("contents: read" in _job_block(publish, "build"), "Publish build job must use contents: read.")
    for job_name in ("testpypi", "pypi"):
        block = _job_block(publish, job_name)
        audit.require("id-token: write" in block, f"Publish job {job_name} must use trusted publishing id-token.")


def audit_dockerfile(audit: Audit) -> None:
    text = audit.text("Dockerfile")
    from_match = re.search(r"^FROM\s+(\S+)", text, re.MULTILINE)
    audit.require(from_match is not None, "Dockerfile must declare a base image.")
    if from_match is not None:
        base = from_match.group(1)
        audit.require(":latest" not in base, f"Dockerfile base image must not use latest: {base}")
        audit.require(":" in base or "@sha256:" in base, f"Dockerfile base image must include a tag or digest: {base}")
    user_matches = re.findall(r"^USER\s+(\S+)", text, re.MULTILINE)
    audit.require(bool(user_matches), "Dockerfile must switch to a non-root user.")
    if user_matches:
        audit.require(user_matches[-1] not in {"0", "root"}, "Dockerfile final USER must not be root.")
    audit.require("--no-cache-dir" in text, "Dockerfile pip install must use --no-cache-dir.")
    audit.require(
        '"--profile", "readonly"' in text,
        "Dockerfile MCP default command must use --profile readonly.",
    )


def audit_release_gate(audit: Audit) -> None:
    text = audit.text("scripts/release_gate.py")
    audit.require("scripts/audit_supply_chain.py" in text, "Release gate must run the supply-chain audit.")


def run_audit() -> list[str]:
    audit = Audit()
    audit_pyproject(audit)
    audit_dependabot(audit)
    audit_workflows(audit)
    audit_dockerfile(audit)
    audit_release_gate(audit)
    return audit.failures


def main() -> int:
    failures = run_audit()
    if failures:
        print("Supply-chain audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Supply-chain audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
