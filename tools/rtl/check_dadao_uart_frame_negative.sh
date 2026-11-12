#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${1:-${ROOT}/.work/log/rtl/RTL-008t-uart-frame-negative.log}"

mkdir -p "$(dirname "${LOG}")"
set +e
python3 "${ROOT}/tools/rtl/dadao_uart_frame.py" \
  selftest \
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
