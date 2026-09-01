#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: bash check.sh <local|github|final>" >&2
  exit 2
fi

exec python3 "$ROOT/public_tests/check_solo.py" "$1"
