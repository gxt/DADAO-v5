#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-${ROOT}/.work/log/rtl/RTL-009t-vectors.sha256}"

mkdir -p "$(dirname "${OUT}")"
cd "${ROOT}"
find tests -type f -name '*.yaml' -print0 \
  | sort -z \
  | xargs -0 sha256sum >"${OUT}"

count=$(wc -l <"${OUT}")
echo "VECTOR_HASH_COUNT=${count}"
echo "VECTOR_HASH_FILE=${OUT}"
