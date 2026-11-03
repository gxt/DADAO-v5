#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${1:-${ROOT}/.work/log/rtl/RTL-010t-memory-oracle-negative.log}"
ORACLE="${ROOT}/tools/rtl/check_dadao_memory_oracle.py"
VECTOR="${ROOT}/tests/rtl/core/RTL-010t-memory-vectors.yaml"
SCALA="${ROOT}/rtl/dadao/src/test/scala/dadao/DADAOMemoryOracleTable.scala"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

mkdir -p "$(dirname "${LOG}")"
sha256sum "${VECTOR}" "${SCALA}" >"${TMP_DIR}/before.sha256"

modes=(
  endianness
  wstrb
  extension
  priority
  partial-commit
  block-stride
)

: >"${LOG}"
for mode in "${modes[@]}"; do
  set +e
  python3 "${ORACLE}" \
    --failure-mode "${mode}" \
    --yaml "${TMP_DIR}/${mode}.yaml" \
    --scala "${TMP_DIR}/${mode}.scala" \
    >>"${LOG}" 2>&1
  rc=$?
  set -e
  if [[ ${rc} -eq 0 ]]; then
    echo "NEGATIVE_GATE FAIL: ${mode} returned zero"
    exit 1
  fi
  echo "NEGATIVE_GATE PASS: ${mode} returned ${rc}" | tee -a "${LOG}"
done

set +e
python3 "${ORACLE}" \
  --force-failure \
  --yaml "${TMP_DIR}/forced.yaml" \
  --scala "${TMP_DIR}/forced.scala" \
  >>"${LOG}" 2>&1
rc=$?
set -e
if [[ ${rc} -eq 0 ]]; then
  echo "NEGATIVE_GATE FAIL: forced memory oracle failure returned zero"
  exit 1
fi
echo "NEGATIVE_GATE PASS: forced memory oracle failure returned ${rc}" \
  | tee -a "${LOG}"

sha256sum "${VECTOR}" "${SCALA}" >"${TMP_DIR}/after.sha256"
cmp "${TMP_DIR}/before.sha256" "${TMP_DIR}/after.sha256"
echo "VECTORS_UNCHANGED_DURING_NEGATIVE_GATE=1" | tee -a "${LOG}"
