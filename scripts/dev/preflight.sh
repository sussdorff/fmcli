#!/usr/bin/env bash
# Repository preflight, run by the pre-push hook before a push.
# Checks that every toolchain declaration names its latest release.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

python3 scripts/dev/check_toolchain_versions.py
