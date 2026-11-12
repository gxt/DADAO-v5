#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${1:-${ROOT}/.work/log/rtl/RTL-010t-memory-scala-negative.log}"

source "${ROOT}/20260929report/clab-env.sh" >/dev/null
mkdir -p "$(dirname "${LOG}")"
cd "${ROOT}/rtl/dadao"

set +e
DADAO_MEMORY_NEGATIVE=1 sbt -batch \
  "testOnly dadao.DADAOMemoryNegativeGateSpec" \
  >"${LOG}" 2>&1
rc=$?
set -e

tail -n 80 "${LOG}"
if [[ ${rc} -eq 0 ]]; then
  echo "NEGATIVE_GATE FAIL: forced memory compare returned zero"
  exit 1
fi

echo "NEGATIVE_GATE PASS: forced memory compare returned ${rc}"
