#!/usr/bin/env bash
set -euo pipefail

# Ensure Python 3.11 is used by Poetry virtualenv for this project
# - Detect python3.11 on PATH
# - If found, instruct poetry to use it
# - Install dependencies (backend) using that environment

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

PYTHON_BIN=$(command -v python3.11 || true)
if [ -z "$PYTHON_BIN" ]; then
  echo "python3.11 not found on PATH. Please install Python 3.11 and retry."
  exit 1
fi

echo "Using Python: $($PYTHON_BIN -V) at $PYTHON_BIN"

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry not found; installing from official installer..."
  curl -sSL https://install.python-poetry.org | python3.11 -
  export PATH="$HOME/.local/bin:$PATH"
fi

POETRY_BIN=$(command -v poetry)
echo "Using Poetry: $POETRY_BIN"

cd "$ROOT_DIR/backend"

CURRENT_PY=$(poetry env info -p 2>/dev/null || true)
if [ -n "$CURRENT_PY" ]; then
  echo "Existing poetry virtualenv path: $CURRENT_PY"
fi

echo "Setting Poetry virtualenv to Python 3.11"
poetry env use "$PYTHON_BIN" || {
  echo "Failed to set poetry env to python3.11; try running: poetry env use $PYTHON_BIN" >&2
}

echo "Installing backend dependencies with Poetry using Python 3.11"
if ! poetry install -v; then
  echo "poetry install failed, attempting to install dependencies without installing the project (--no-root)"
  poetry install --no-root -v
fi

echo "Poetry environment info:"
poetry env info

echo "Check python version inside poetry venv:"
poetry run python -V

echo "Done. Backend Poetry environment configured to use Python 3.11"

exit 0
