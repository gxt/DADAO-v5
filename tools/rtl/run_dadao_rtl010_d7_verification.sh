#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT}/.work/log/rtl"

mkdir -p "${LOG_DIR}" "${ROOT}/tests/rtl/core"
source "${ROOT}/20260929report/clab-env.sh" >/dev/null

python3 "${ROOT}/tools/rtl/check_dadao_memory_oracle.py" \
  >"${LOG_DIR}/RTL-010t-memory-oracle-check.log" 2>&1

bash "${ROOT}/tools/rtl/check_dadao_vector_hashes.sh" \
  "${LOG_DIR}/RTL-010t-vectors.before.sha256" \
  >"${LOG_DIR}/RTL-010t-vector-hash-before.log"

cd "${ROOT}/rtl/dadao"
timeout 4200 sbt -batch test \
  >"${LOG_DIR}/RTL-010t-final-sbt-test.log" 2>&1

cd "${ROOT}"
bash "${ROOT}/tools/rtl/check_dadao_vector_hashes.sh" \
  "${LOG_DIR}/RTL-010t-vectors.after.sha256" \
  >"${LOG_DIR}/RTL-010t-vector-hash-after.log"
cmp "${LOG_DIR}/RTL-010t-vectors.before.sha256" \
  "${LOG_DIR}/RTL-010t-vectors.after.sha256" \
  >"${LOG_DIR}/RTL-010t-vector-hash-cmp.log"

python3 "${ROOT}/tools/rtl/check_rtl_tree.py" \
  >"${LOG_DIR}/RTL-010t-rtl-tree.log" 2>&1
python3 "${ROOT}/tools/rtl/check_chipyard_patch.py" \
  >"${LOG_DIR}/RTL-010t-chipyard-patch.log" 2>&1

bash "${ROOT}/tools/rtl/check_dadao_memory_oracle_negative.sh" \
  "${LOG_DIR}/RTL-010t-memory-oracle-negative.log" \
  >"${LOG_DIR}/RTL-010t-memory-oracle-negative-wrapper.log"
bash "${ROOT}/tools/rtl/check_dadao_memory_scala_negative.sh" \
  "${LOG_DIR}/RTL-010t-memory-scala-negative.log" \
  >"${LOG_DIR}/RTL-010t-memory-scala-negative-wrapper.log"
bash "${ROOT}/tools/rtl/check_dadao_alu_oracle_negative.sh" \
  "${LOG_DIR}/RTL-009t-alu-oracle-negative.log" \
  >"${LOG_DIR}/RTL-009t-alu-oracle-negative-wrapper.log"
bash "${ROOT}/tools/rtl/check_dadao_exec_coverage_negative.sh" \
  "${LOG_DIR}/RTL-009t-exec-negative.log" \
  >"${LOG_DIR}/RTL-009t-exec-negative-wrapper.log"
bash "${ROOT}/tools/rtl/check_dadao_alu_negative.sh" \
  "${LOG_DIR}/RTL-009t-alu-negative.log" \
  >"${LOG_DIR}/RTL-009t-alu-negative-wrapper.log"
bash "${ROOT}/tools/rtl/check_dadao_vector_hash_negative.sh" \
  >"${LOG_DIR}/RTL-009t-vector-hash-negative.log"

echo "RTL010_D7_VERIFICATION PASS"
