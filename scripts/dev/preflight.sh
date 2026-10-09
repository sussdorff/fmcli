#!/usr/bin/env bash
# Repository preflight, run by the pre-push hook before a push.
# Checks that every toolchain declaration follows the toolchains standard.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 .agents/standards/toolchains/scripts/check_toolchain_versions.py
