#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${1:-${ROOT}/.work/log/rtl/RTL-008t-static-legality-negative.log}"

mkdir -p "$(dirname "${LOG}")"
set +e
python3 "${ROOT}/tools/rtl/check_dadao_static_legality.py" \
  --force-failure \
  >"${LOG}" 2>&1
rc=$?
set -e

cat "${LOG}"
if [[ ${rc} -eq 0 ]]; then
  echo "NEGATIVE_GATE FAIL: forced failure returned zero"
  exit 1
fi

echo "NEGATIVE_GATE PASS: forced failure returned ${rc}"
