#!/usr/bin/env bash
# Example: bash install.sh --target claude --scope user
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$script_dir/scripts/install.py" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$script_dir/scripts/install.py" "$@"
else
  echo 'Python 3.10+ is needed for this installer. Manual copy instructions are in docs/setup.md.' >&2
  exit 1
fi
