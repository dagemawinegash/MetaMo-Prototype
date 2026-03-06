#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${1:-.venv}"
PY_BIN="${PYTHON:-python3}"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR"
    "$PY_BIN" -m venv "$VENV_DIR"
else
    echo "Reusing existing virtual environment in $VENV_DIR"
fi

PIP="$VENV_DIR/bin/pip"
PYTHON_EXEC="$VENV_DIR/bin/python"

if [ ! -x "$PIP" ]; then
    echo "Could not find pip inside $VENV_DIR. Did venv creation succeed?" >&2
    exit 1
fi

"$PYTHON_EXEC" -m pip install --upgrade pip
"$PIP" install \
    langgraph \
    langchain-core \
    langchain-openai \
    langchain-google-genai \
    langchain \
    langchain-community \
    python-dotenv

echo "Virtual environment ready. Activate it with: source $VENV_DIR/bin/activate"
