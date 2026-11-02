# QEMU-078t: scaleB C1 与 sc rd0

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-181t`
**状态**：已验证

## 用户授权

用户 2026-11-01：scaleB C1 `ftsclb/fosclb` 第三源 `rfHD → rdHD`（同编码）；`sc rdHB=rd0 ⇒ ILLI`；授权 QEMU 独立任务。

## 目标

1. **scaleB C1**：
   - `insn.decode` 第三字段 bank 改为 `rdhd`；语法 `ftsclb rf,rf,rd`；
   - `trans_fp`/`helper_fp_arith` 的 scaleB 直接读 RD 指数（64 位有符号），不再 `floatXX_to_int32(rfHD)`；
   - 旧 `rf,rf,rf` 编码/汇编路径拒绝。
2. **sc rd0**：
   - `sc rdHB, rdHC, [rbHD]` 且 `rdHB=rd0` 静态 ILLI；
   - 不写内存、不置成功/失败状态；
   - 编码不变。
3. 不改 `tests/**`/`spec/**`/`contracts/**`/LLVM/gem5/Makefile；测试另任务。

## 文件范围

- `components/qemu/**`（补丁、series、changelog）
- 本任务书、`milestones.md`

## 验收

1. `make check-patch-tree`、`make check-source-state` rc=0。
2. 重新构建 QEMU 后：scaleB 新/旧语法、`sc rd0` ILLI 反例真实 rc；`check_qemu_trans` 相关项 rc=0。
3. 不跑全量 L3；证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。
4. 失败保留现场；不猜 spec；不复制 LLVM/gem5 实现。

## 完成区

**测试结果**：`.work/evidence/QEMU-078t/run.sh` rc=0（checks=31 failures=0；行为 17/17：scaleB 新路径 + 极端 64 位指数 + `rdHC=rd0` + 12 条 `sc rd0` ILLI）。两次注入均可达 FAIL：恢复旧 `load_rf(a->hd)` ⇒ scaleB 2/2 FAIL；删除 sc 守卫 ⇒ 12 条 rd0 全 FAIL；`cp`+md5 还原后均回绿。回归 `atomics-lrsc` 125/125 PASS。增量重建 `make build-qemu JOBS=8` rc=0（约 1 min/次）。
**修改文件**：`components/qemu/patches/target/dadao/{helper.c,translate.c,insn_trans/trans_fp.c.inc}.patch`；`components/qemu/changelog.md`；本任务书；`.tao/knowledge/milestones.md`。组件源树（非 v5 跟踪）同三文件；证据 `.work/evidence/QEMU-078t/`（gitignored）。`insn.decode` 未改。
**验收结果**：`check-patch-tree` rc=0（5 comp/205 patches）；`check-source-state` rc=0（qemu OK HEAD=f98216a count=1 clean=True）；`check_qemu_trans --strict` 264/264、orphan 0；`validate_decodetree` PASS；`check-qemu-forms` rc=0；`insn.decode` 重生成逐字节相同。llvm-mc：新语法编出 `0x44544043/0x44744043`，objdump 反汇编为 `rd3`；旧语法 rc=1 拒绝（LLVM-142t）。
**新发现/坑**：① QEMU 只吃编码，新旧写法共享同一 `orrr` 位模式，无法也不应在 QEMU 侧区分；旧路径的证明是「rf3=10.0 诱饵仍在、rd3=2 生效 ⇒ 6.0 而非 1536.0」。② 任务书说“改 insn.decode 第三字段 bank”，但 decodetree 不表达 bank；bank 只在 `contracts/opcodes.yaml`，故重生成逐字节不变，改的是 trans/helper 的 `load_rd`。③ `fp_scaleb_exp` 对超 int 的 64 位指数按 IEEE 754 饱和，已用 `2^63-1`/`-2^63` 例验证。
**遗留问题**：① `tests/` 向量归 `TESTCASES-090t`（本任务按边界未动）；② 按任务要求未跑全量 L3；③ 旧语法拒绝由 LLVM-142t 承担，QEMU 侧无独立可测面。④ `make check` rc=2，唯一 FAIL=`check-isa-coverage`（`gen-orrr.s` 缺 `ftsclb/fosclb rf,rf,rd` 行 + `tools/llvm/llvm-isa-backend-matrix.*` patch 行号漂移）；属 LLVM-142t/TESTCASES-090t 范围，未重试、未越界修改；其余 L1 门控（patch-tree/source-state/qemu_trans/forms/interface/changelog/milestones）均 rc=0。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：逐行审 `trans_fp.c.inc`/`helper.c`/`translate.c` 改动与 3 份导出补丁；重跑证据脚本与 atomics 回归。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 64 位指数超 int 时截断会错 | ✅已修 | `fp_scaleb_exp()` 饱和到 `INT_MAX/INT_MIN` | `ftsclb_exp_max/min` 2 例 PASS |
| F-2 `sc rd0` 必须在任何内存/状态操作前 ILLI | ✅已修 | `gen_sc` 首部静态 `gen_exception_illegal` | 删除守卫注入 ⇒ 12 条 FAIL；还原回绿 |
| F-3 scaleB 仍可能走旧 `rfHD` | ✅已修 | `is_sclb ? load_rd : load_rf` 分支 | 恢复旧路径注入 ⇒ scaleB 2/2 FAIL |
| F-4 `insn.decode` 未改是否漏同步 | ❌不修 | decodetree 无 bank 字段，重生成逐字节相同 | 生成器 diff rc=0；`validate_decodetree` PASS |
| F-5 `sc` 非 rd0 路径回归 | ✅已修 | 未改非 rd0 逻辑，仅加前置 ILLI | `atomics-lrsc` 125/125 PASS |

### 第 1 轮 reviewer 验收

**快照/范围**：分支 `QEMU-078t` @4ef0a81b；前/后 `git status --porcelain -uall` 均空；`git diff HEAD~1..HEAD` 仅 6 文件（helper.c/translate.c/trans_fp.c.inc 三补丁 + changelog + 任务书 + milestones），无 tests/spec/contracts/LLVM/gem5/Makefile 越界；QEMU 源树 `git diff` 空，md5 与注入前一致（trans_fp `5452c695…` / translate `eb7496fc…`）。
**重跑（本人执行，真实 rc）**：`make build-qemu JOBS=8` rc=0（增量 real 2.5s；注入/还原后重建各 rc=0，约 8s）；`.work/evidence/QEMU-078t/run.sh` rc=0（checks=31 failures=0，89s）；`check-patch-tree` rc=0（5 comp/205 patches）；`check-source-state` rc=0（qemu OK HEAD=f98216a count=1 clean=True）；`check_qemu_trans --strict` rc=0（264/264、orphan 0）；`validate_decodetree` rc=0 PASS；`check-qemu-forms` rc=0；`check-interface` rc=0（49/49）；`check-component-changelog` rc=0（20 项）；回归 `run_qemu_test --batch tests/inst/atomics` rc=0（125 total/125 passed）。
**独立注入（cp+md5，未用 git checkout/restore）**：① scaleB 改回 `load_rf(a->hd)` → 重建 rc=0，engineer 4 条 scaleB 中 3 条 FAIL、我方 5 条中 4 条 FAIL，整体 rc=1；`cp` 还原 + `md5sum -c` OK + 重建 rc=0 → 全绿。② 删除 `gen_sc` rd0 守卫 → 12 条 `sc.* rdHB=rd0` 全部 `FAIL Expected ILLI, got FAIL(0x01)`（rc=1），我方「先 lr 持保留再 sc rd0」同 FAIL、rdHC=rd0 仍 PASS；还原回绿 13/13。
**独立行为核验（我方向量 `/tmp/opencode/QEMU-078t-review/rev_vectors.yaml`，6/6 PASS）**：rd3=-1 → 0.75（有符号 64 位指数）；rd3=2^31 → +Inf（超 int32 不回绕）；rd3=rd0 → 1.5（rf 诱饵 10.0 不生效，旧路径应为 1536）；fosclb 同；`sc.o.nn` 持保留 + rdHB=rd0 → 0x88。llvm-mc 独立复跑：新语法 rc=0 → `0x44544043 0x44744043`/objdump `rd3`，旧 `rf,rf,rf` rc=1 `invalid operand`；`insn.decode` 重生成逐字节相同、opcodes 未改 ⇒ 编码未改。
**make check**：`make -k check` rc=2，失败仅 3 项且均非本任务引入——`check-isa-coverage`（允许，TESTCASES-090t）、`check-musl-freshness`（clang/lld 07:23–07:30 被他任务安装、stamp 停在 11-01）、`check-run-artifacts`（18 条非法名全在 `.work/log/testcases/TESTCASES-090t/`，mtime 07:39–07:46 早于本轮审查）；其余 L1 全 PASS，无失败被掩盖。
**findings（不阻断）**：F-a 完成区「scaleB 2/2 FAIL」实为 3/4——`ftsclb_exp_max` 注入下仍 PASS（rf 诱饵 0x41200000 被当指数饱和到 +Inf，恰好等于期望值），门控整体仍 FAIL，属文档数字不准；F-b「atomics-lrsc 125/125」实为 atomics 目录 108 lrsc + 17 fence = 125；F-c「make check 唯一 FAIL」在本轮已不成立（另 2 红为他任务残留）；F-d 12 条 sc 为 legality 类、harness 不比对 expected_state，「不写内存/状态」依据是守卫位于 gen_sc 任何访存/状态操作之前的静态次序 + 持保留反例。
**判决：Accepted**（验收命令全部在本人重跑下通过；F-a~F-d 交 architect 收尾处置）
