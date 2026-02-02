#!/bin/bash

# Start x402 Facilitator
# This script starts the facilitator service

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Starting x402 Facilitator"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f "../../../.env" ]; then
    echo "Error: .env file not found in project root"
    echo "Please create .env file with required variables:"
    echo "  FACILITATOR_PRIVATE_KEY=<your_private_key>"
    echo "  TRON_NETWORK=<network>"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../../../.venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run: python -m venv .venv"
    echo ""
    exit 1
fi

# Activate virtual environment
source "../../../.venv/bin/activate"

PIP_CMD=(python -m pip)

# Install dependencies if needed
if ! python -c "import x402" 2>/dev/null; then
    echo "Installing dependencies..."
    # Some environments don't expose a `pip` executable even after venv activation.
    # Ensure pip exists, then always invoke it via the interpreter.
    python -m ensurepip --upgrade >/dev/null 2>&1 || true
    "${PIP_CMD[@]}" --version >/dev/null 2>&1 || {
        echo "Error: pip is not available in the virtual environment." >&2
        echo "Try recreating the venv: python -m venv .venv" >&2
        exit 1
    }

    "${PIP_CMD[@]}" install -e ../../../python/x402
    "${PIP_CMD[@]}" install -r requirements.txt
fi

# Start the facilitator
python main.py
