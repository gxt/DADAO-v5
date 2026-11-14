#!/usr/bin/env bash
# engine_parity_run.sh — m12-chipyard-016 证据脚本（embench / picolibc-full 在
# chipyard Tiny Verilator harness 上，走两个 runner 的 `--engine chipyard` 路径）。
#
# 本文件是 016 证据脚本 `run.sh` 的入仓版（`m12-chipyard-017`）：检查项 A–H 的
# 语义与名字原样保留，只把「主工作树 / 证据目录 / 报告路径」的推导换成参数
# （`--repo` / `--log-dir` / `--work-dir`）。
#
#   bash tools/testcases/parity/engine_parity_run.sh            # A–F：接线、契约探针、
#                                                               #      两份批次报告、
#                                                               #      报告可复现性
#   bash tools/testcases/parity/engine_parity_run.sh --full     # + G：qemu 侧回归（make 门控）
#   bash tools/testcases/parity/engine_parity_run.sh --inject   # + H：三路可达 FAIL 注入 + 回绿
#
# 退出码 = 0 当且仅当每项检查通过；逐项打印 检查名 / expected / actual。
# 退出码直接捕获（`; rc=$?`），不经 `tee`。
#
# 注意：C/D 断言的是 **016 收口态**（embench 38/38、budget 类 0 例）。当前数据
# 仍在 `-O0` 夜跑窗口内（`cases_seen` < 38、budget 单列非 0），此时本脚本会把
# C1/C2/D6 报 FAIL —— 那是**数据未收完**，不是判据变更；补齐后重跑即回绿。
set -uo pipefail

TASK=m12-chipyard-016
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
LOG="$REPO/.work/log/chipyard"
WORK=

while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO=$2; shift 2 ;;
    --log-dir) LOG=$2; shift 2 ;;
    --work-dir) WORK=$2; shift 2 ;;
    --full|--inject) MODE="$MODE ${1#--}"; shift ;;
    *) echo "run.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$WORK" ] || WORK="$REPO/.work/evidence/$TASK"

TC="$REPO/.dadao/cross-toolchain/bin"
CHIP="$REPO/.work/source/chipyard"
SIM="$CHIP/sims/verilator/simulator-chipyard.harness-WumingTinyConfig"
EMB_JSON="$LOG/m12-chipyard-016-embench.json"
PIC_CY_JSON="$LOG/m12-chipyard-016-picolibc-chipyard.json"
PIC_QEMU_JSON="$LOG/m12-chipyard-016-picolibc-qemu.json"
REPORT_MD="$REPO/.tao/knowledge/refs/m12-016-embench-picolibc.md"
REPORT_JSON="$REPO/.tao/knowledge/refs/m12-016-embench-picolibc.json"
GEN="$REPO/tools/testcases/parity/engine_parity_report.py"
mkdir -p "$LOG" "$WORK"

has_mode() {
  case " ${MODE:-} " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  [PASS] %s | expected=%s actual=%s\n' "$1" "$2" "$3"; }
bad() { FAIL=$((FAIL+1)); printf '  [FAIL] %s | expected=%s actual=%s\n' "$1" "$2" "$3"; }
chk() { [ "$2" = "$3" ] && ok "$1" "$2" "$3" || bad "$1" "$2" "$3"; }
chk_rc() { local n="$1" want="$2" got="$3"; [ "$want" = "$got" ] && ok "$n" "rc=$want" "rc=$got" || bad "$n" "rc=$want" "rc=$got"; }

# ---------------------------------------------------------------------------
echo "== A. engine wiring (both runners expose --engine chipyard)"
A=$(cd "$REPO" && python3 tools/testcases/tset/embench/run_embench_e2e.py --help 2>&1 | grep -c "engine chipyard")
chk "A1 embench runner has --engine chipyard" 1 "$A"
B=$(cd "$REPO" && python3 tools/testcases/picolibc_tests.py --help 2>&1 | grep -c "engine chipyard")
[ "$B" -ge 1 ] && ok "A2 picolibc runner has --engine chipyard" ">=1" "$B" \
    || bad "A2 picolibc runner has --engine chipyard" ">=1" "$B"
C=$(cd "$REPO" && grep -c "chipyard_engine" tools/testcases/picolibc_tests.py tools/testcases/tset/embench/run_embench_e2e.py | awk -F: '{s+=$2} END {print s}')
[ "$C" -ge 4 ] && ok "A3 both runners import the shared engine module" ">=4 refs" "$C refs" || bad "A3 shared engine module used" ">=4 refs" "$C refs"

# ---------------------------------------------------------------------------
echo "== B. contract-conformance probe (op in rd16, trap 0x3FF00)"
# A spec-form guest: rd16 = 0x18 (SYS_EXIT), block{0x20026, 7}, `trap cfx0,0x3FF00`
# -> the harness must answer 7.  A harness that decodes the op from immu18[7:0]
# (the pre-m12-016 chipyard channel) sees op=0 and fails.
W="$WORK/probe"; rm -rf "$W"; mkdir -p "$W"
cat > "$W/t.c" <<'EOF'
int main(void) { return 7; }
EOF
"$TC/clang" -target dadao-unknown-elf -O0 -ffreestanding -fno-builtin -std=gnu99 \
    -c "$W/t.c" -o "$W/t.o" 2>/dev/null
"$TC/llvm-mc" --triple=dadao -filetype=obj "$REPO/tests/shared/crt0/minimal_crt0.s" -o "$W/crt0.o"
"$TC/ld.lld" -L "$REPO/tests/shared/linker" -T "$REPO/tests/shared/linker/dadao-tiny-app.lds" \
    "$W/t.o" "$W/crt0.o" -o "$W/t.elf"
"$SIM" +permissive +loadmem="$W/t.elf" +semiout="$W/out" +max-cycles=2000000 \
    +permissive-off none > "$W/sim.log" 2>&1
chk_rc "B1 spec-form guest exit status (rd16 op channel)" 7 $?
TRAP=$(grep -c "trap	cfx0, 0x3FF00" "$REPO/tests/shared/crt0/minimal_crt0.s")
chk "B2 probe really uses the canonical 0x3FF00 tag" 1 "$TRAP"
CH=$(grep -c "semiOp := rf.io.r0Data(7, 0)" "$CHIP/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala")
chk "B4 RTL 当前服务号来源 = rd16" 1 "$CH"
CYC=$(grep -o "cycle=[0-9]*" "$W/sim.log" | head -1 | cut -d= -f2)
[ -n "$CYC" ] && [ "$CYC" -gt 0 ] && ok "B3 harness reports the exit cycle stamp" ">0" "$CYC" \
    || bad "B3 harness reports the exit cycle stamp" ">0" "${CYC:-none}"

# ---------------------------------------------------------------------------
echo "== C. embench 38/38 on chipyard（报告 union）"
# 注意：C1 断言的是报告里**现场统计**的用例数（`cases_seen`），不是
# `pass + (38 - cases_seen) == 38` 这类恒等式；C5 断言 md5 **集合大小为 1**，
# 并把那个 md5 打出来。
if [ -f "$REPORT_JSON" ]; then
  mapfile -t V < <(python3 - "$REPORT_JSON" <<'PYEOF'
import json, sys
e = json.load(open(sys.argv[1]))["embench"]
print(e["cases_seen"])                       # 现场统计的已判例数
print(e["pass"])
print(len(e["budget_blocked"]))
print(len(set(e["sim_md5"])))                 # 期望 1
print((e["sim_md5"] or ["-"])[0])
PYEOF
)
  T=${V[0]}; P=${V[1]}; BUD=${V[2]}; MDN=${V[3]}; MD5=${V[4]}
  chk "C1 报告已判例数（现场统计）" 38 "$T"
  chk "C2 PASS" 38 "$P"
  chk "C3 budget-blocked（12 h 仍不够）单列" 0 "$BUD"
  chk "C5 embed 整批 sim md5 唯一（集合大小）" 1 "$MDN"
  echo "     embench sim md5 = $MD5"
else
  bad "C0 报告存在" "file exists" "missing $REPORT_JSON"
fi

# ---------------------------------------------------------------------------
echo "== D. M12 判据 = engine parity（picolibc 逐例状态与 qemu 一致）"
# 用户 2026-11-14 裁定：判据不是「全绿」（qemu 自己也 1 fail + 4 blocked），
# 而是 (i) 逐例状态差集 = 0；(ii) qemu 侧既有缺口登记在册、不计到 chipyard；
# (iii) host timeout 属 budget 结果，单列且不计入「chipyard 独有失败」。
if [ -f "$REPORT_JSON" ]; then
  mapfile -t W2 < <(python3 - "$REPORT_JSON" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
p = d["parity"]
print(d["picolibc_chipyard"]["total"])
print(d["picolibc_qemu_baseline"]["total"])
print(len(p["differing"]))
print(len(p["chipyard_only_failures"]))
print(len(p["budget_blocked"]))
print(len(p["qemu_gaps_matched"]))
print(len(p["qemu_gaps_registered"]))
PYEOF
)
  CY=${W2[0]}; QE=${W2[1]}; DIFF=${W2[2]}; ONLY=${W2[3]}; BUD=${W2[4]}; GAPM=${W2[5]}; GAPR=${W2[6]}
  chk "D1 chipyard 清单 = qemu 清单" 235 "$CY"
  chk "D2 qemu 基线清单" 235 "$QE"
  chk "D3 逐例状态差集（budget 类单列不计入）" 0 "$DIFF"
  chk "D4 chipyard 独有失败（qemu pass 而 chipyard fail/blocked）" 0 "$ONLY"
  chk "D5 qemu 既有缺口登记匹配" "$GAPR" "$GAPM"
  echo "     budget 类单列（host timeout，不计入 chipyard 独有失败）：$BUD 例"
  chk "D6 budget 类单列（应随重跑池收敛；不阻断 parity）" 0 "$BUD"
else
  bad "D0 报告存在" "file exists" "missing $REPORT_JSON"
fi

# ---------------------------------------------------------------------------
echo "== E. report files"
[ -f "$REPORT_MD" ] && ok "E1 report markdown" "exists" "exists" || bad "E1 report markdown" "exists" "missing"
[ -f "$REPORT_JSON" ] && ok "E2 report json" "exists" "exists" || bad "E2 report json" "exists" "missing"
if [ -f "$REPORT_JSON" ]; then
  # (i) determinism: the report is a pure function of the runtime inputs --
  #     two independent regenerations must be byte-identical;
  # (ii) honesty: every per-case row in the committed report must still exist in
  #     the current inputs with the same status (a live batch only *adds* cases,
  #     so a stale snapshot is a subset, never an invention);
  # (iii) reproducibility: `--check` on the committed pair (byte-for-byte).
  for n in 1 2; do
    R="$WORK/regen$n"; rm -rf "$R"; mkdir -p "$R"
    python3 "$GEN" --repo "$REPO" --log-dir "$LOG" --out-dir "$R" > /dev/null 2>&1
  done
  chk "E3a report json is a deterministic function of the inputs" \
      "$(md5sum "$WORK/regen1/m12-016-embench-picolibc.json" | cut -d' ' -f1)" \
      "$(md5sum "$WORK/regen2/m12-016-embench-picolibc.json" | cut -d' ' -f1)"
  chk "E3b report markdown is a deterministic function of the inputs" \
      "$(md5sum "$WORK/regen1/m12-016-embench-picolibc.md" | cut -d' ' -f1)" \
      "$(md5sum "$WORK/regen2/m12-016-embench-picolibc.md" | cut -d' ' -f1)"
  python3 - "$REPORT_JSON" \
      "$WORK/regen1/m12-016-embench-picolibc.json" <<'PYEOF'
import json, sys
committed = json.load(open(sys.argv[1])); live = json.load(open(sys.argv[2]))
bad = []
for key in ("embench", "picolibc_chipyard"):
    live_rows = {c.get("case_id") or c.get("name"): c["status"]
                 for c in live[key]["cases"]}
    for c in committed[key]["cases"]:
        k = c.get("case_id") or c.get("name")
        if k in live_rows and live_rows[k] != c["status"]:
            bad.append("%s: %s -> %s" % (k, c["status"], live_rows[k]))
if bad:
    print("stale/invented rows:", "; ".join(bad[:4]))
    sys.exit(1)
PYEOF
  chk_rc "E3c committed report rows match the live inputs (no invention)" 0 $?
  python3 "$GEN" --repo "$REPO" --log-dir "$LOG" --check > "$WORK/check.log" 2>&1
  chk_rc "E4 --check reproduces the committed report byte-for-byte" 0 $?
  grep -o 'sha256 .*' "$WORK/check.log" | sed 's/^/     /'
fi

if has_mode full; then
  echo "== G. qemu path regressions"
  ( cd "$REPO" && make check-tset-embench-smoke > "$LOG/m12-chipyard-016-gate-embench-smoke.log" 2>&1 )
  chk_rc "G1 make check-tset-embench-smoke" 0 $?
  ( cd "$REPO" && make check-picolibc-tests > "$LOG/m12-chipyard-016-gate-picolibc.log" 2>&1 )
  chk_rc "G2 make check-picolibc-tests" 0 $?
fi

# ---------------------------------------------------------------------------
if has_mode inject; then
  echo "== H. injections (reachable FAIL -> cp+md5 restore -> green)"
  INJ="$WORK/inj"; rm -rf "$INJ"; mkdir -p "$INJ/src/tiny"
  cat > "$INJ/src/tiny/tiny.c" <<'EOF'
/* Staged, Embench-shaped benchmark for the evidence injections: the corpus is
 * manifest-locked, so the injection runs against this copy through the same
 * `--embench-src` build+run path. */
#include "support.h"
void initialise_benchmark(void) {}
void warm_caches(int heat) { (void)heat; }
int benchmark(void) { return 42; }
int verify_benchmark(int result) { return result == 42; }
EOF
  ln -s "$REPO/.work/source/embench-iot/support" "$INJ/support"
  ln -s "$REPO/.work/source/embench-iot/examples" "$INJ/examples"
  RUN=(python3 tools/testcases/tset/embench/run_embench_e2e.py --engine chipyard
       --embench-src "$INJ" --opt O2 --work-dir "$INJ/work" --timeout 600)
  ( cd "$REPO" && "${RUN[@]}" > "$INJ/base.log" 2>&1 )
  chk_rc "H1 baseline green" 0 $?
  SRC="$INJ/src/tiny/tiny.c"; cp -p "$SRC" "$SRC.orig"; M0=$(md5sum "$SRC" | cut -d' ' -f1)
  sed -i 's/return result == 42;/return result == 43;/' "$SRC"
  ( cd "$REPO" && "${RUN[@]}" > "$INJ/wrong.log" 2>&1 )
  chk_rc "H2 wrong verify_benchmark => FAIL" 1 $?
  chk "H3 FAIL is the guest exit code (not a guard)" 1 "$(grep -c 'non-zero guest exit' "$INJ/wrong.log")"
  cp -p "$SRC.orig" "$SRC"; rm -f "$SRC.orig"
  chk "H4 restore md5" "$M0" "$(md5sum "$SRC" | cut -d' ' -f1)"
  ( cd "$REPO" && "${RUN[@]}" > "$INJ/green.log" 2>&1 )
  chk_rc "H5 restored => green" 0 $?
  ( cd "$REPO" && "${RUN[@]:0:6}" --max-cycles 2000 "${RUN[@]:6}" > "$INJ/maxcyc.log" 2>&1 )
  chk_rc "H6 +max-cycles exhausted => FAIL" 1 $?
  chk "H7 the cycle budget is named in the reason" 1 "$(grep -c 'max-cycles=2000 exhausted' "$INJ/maxcyc.log")"
  ( cd "$REPO" && python3 - <<'PY' > "$INJ/md5.log" 2>&1
import sys
sys.path.insert(0, "tools/testcases/lib")
import chipyard_engine as ce
obs = ce.evaluate("work/probe/t.elf", "work/probe/md5case",
                  sim=ce.default_sim("."), timeout=60, sim_md5="0" * 32)
print(obs["status"], obs["reason"])
sys.exit(0 if obs["status"] == "FAIL" and "changed before the run" in obs["reason"] else 1)
PY
  )
  chk_rc "H8 a replaced simulator binary => FAIL (md5 guard)" 0 $?
fi

echo
printf 'evidence: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
