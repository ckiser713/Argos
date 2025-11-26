#!/usr/bin/env bash
set -euo pipefail

# Guardrail: prevent running project commands outside the Nix dev shell.
# Usage: source or invoke from other scripts, e.g.,
#   tools/require-nix.sh pnpm install

if [[ "${IN_NIX_SHELL:-}" != "impure" && "${IN_NIX_SHELL:-}" != "pure" ]]; then
  echo "Error: This command must be run inside the Nix dev shell (nix develop or nix-shell nix/rocm-shell.nix)." >&2
  exit 1
fi

if [[ "$#" -gt 0 ]]; then
  exec "$@"
fi
