#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
python_bin="${PYTHON_BIN:-python3.12}"
if ! command -v "$python_bin" >/dev/null; then
    echo 'Python 3.12 is required. Set PYTHON_BIN to its path, or use uv venv --python 3.12 .venv.' >&2
    exit 1
fi
"$python_bin" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12"'
"$python_bin" -m venv .venv
.venv/bin/python -m pip install -r requirements-ubuntu.txt
.venv/bin/python scripts/download_models.py
echo 'Ready: ./run-ubuntu.sh'
