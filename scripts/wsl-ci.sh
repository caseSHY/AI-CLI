#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="python3"
VENV_DIR=".venv-wsl"
INSTALL_SYSTEM_DEPS=0
SKIP_INSTALL=0

usage() {
  cat <<'EOF'
Usage: scripts/wsl-ci.sh [options]

Run the GitHub Actions Ubuntu checks locally inside WSL/Linux.

Options:
  --install-system-deps   Run apt-get update/install for coreutils and venv support.
  --python <executable>   Python executable to use (default: python3).
  --venv <path>           Virtual environment path (default: .venv-wsl).
  --skip-install          Reuse existing environment and skip pip install.
  -h, --help              Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-system-deps)
      INSTALL_SYSTEM_DEPS=1
      shift
      ;;
    --python)
      PYTHON_BIN="${2:?missing value for --python}"
      shift 2
      ;;
    --venv)
      VENV_DIR="${2:?missing value for --venv}"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "${REPO_ROOT}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script must run inside WSL/Linux." >&2
  exit 2
fi

if [[ "${INSTALL_SYSTEM_DEPS}" -eq 1 ]]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "--install-system-deps requires an apt-based WSL distribution." >&2
    exit 2
  fi
  sudo apt-get update
  sudo apt-get install -y coreutils python3-venv python3-pip
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

if [[ "${SKIP_INSTALL}" -eq 0 ]]; then
  python -m pip install --upgrade pip
  python -m pip install -e ".[test,dev]"
fi

echo "== Environment =="
python --version
command -v python
command -v sort || true
sort --version | head -n 1 || true

echo "== Ruff =="
ruff check src/ tests/
ruff format --check src/ tests/

echo "== Mypy =="
mypy src/agentutils/ --strict

echo "== Pytest with coverage =="
PYTHONPATH=src python -m pytest tests/ -v --tb=short --cov=src/agentutils --cov-report=term-missing
