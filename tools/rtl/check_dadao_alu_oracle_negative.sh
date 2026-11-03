#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${1:-${ROOT}/.work/log/rtl/RTL-009t-alu-oracle-negative.log}"

mkdir -p "$(dirname "${LOG}")"
set +e
python3 "${ROOT}/tools/rtl/check_dadao_alu_oracle.py" \
  --yaml "${ROOT}/tests/rtl/core/RTL-009t-alu-vectors.yaml" \
  --scala "${ROOT}/rtl/dadao/src/test/scala/dadao/DADAOALUOracleTable.scala" \
  --force-failure \
  >"${LOG}" 2>&1
rc=$?
set -e

cat "${LOG}"
if [[ ${rc} -eq 0 ]]; then
  echo "NEGATIVE_GATE FAIL: forced ALU oracle failure returned zero"
  exit 1
fi
echo "NEGATIVE_GATE PASS: forced ALU oracle failure returned ${rc}"
