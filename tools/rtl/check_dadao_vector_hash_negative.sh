#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

bash "${ROOT}/tools/rtl/check_dadao_vector_hashes.sh" \
  "${TMP_DIR}/before.sha256" >/dev/null
cp "${TMP_DIR}/before.sha256" "${TMP_DIR}/after.sha256"
printf '0  changed-vector.yaml\n' >>"${TMP_DIR}/after.sha256"

set +e
cmp "${TMP_DIR}/before.sha256" "${TMP_DIR}/after.sha256" \
  >/dev/null 2>&1
rc=$?
set -e

if [[ ${rc} -eq 0 ]]; then
  echo "NEGATIVE_GATE FAIL: changed hash list compared equal"
  exit 1
fi
echo "NEGATIVE_GATE PASS: changed hash list detected"
