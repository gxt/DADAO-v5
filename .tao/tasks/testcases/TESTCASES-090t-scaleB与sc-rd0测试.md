# TESTCASES-090t: scaleB C1 与 sc rd0 测试

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`
**状态**：待验收

## 用户授权

用户 2026-11-01：scaleB C1 与 `sc rdHB=rd0 ⇒ ILLI` 的测试必须随实现独立调整；不新建 `tests/gem5`，复用现有 `tests/inst`/`tests/arch`/`tset` scope。

用户 2026-11-02 裁定：**扩展本任务**，同时接收 LLVM lit 与 `tools/llvm/llvm-isa-backend-matrix.*` 同步；LLVM-142t 只验实现与定向行为，全局 `check-lit`/`check-isa-coverage` 由本任务关绿。

## 目标

1. **scaleB C1**：
   - 新语法 `ftsclb rf,rf,rd`、`fosclb rf,rf,rd` 的正例；
   - 旧 `rf,rf,rf` 负例；
   - `ldexp`/`scalbn` 的 C/IR 运行期与编码检查；
   - QEMU/gem5/LLVM 结果一致性。
2. **sc rd0**：
   - 12 条 `sc` 的 `rdHB=rd0` 负例，期望 ILLI；
   - 正常 rd 目的正例；
   - QEMU system 与 gem5 FS 对照。
3. **LLVM 测试资产同步**：
   - 更新 `tests/unit/llvm/lit/MC/DADAO/fp-encoding.s`、`tests/unit/llvm/lit/CodeGen/DADAO/fp-ldexp.ll`，以及受影响的 `gen-orrr.s`；
   - 重生成 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`；
   - `make check-lit` 与 `make check-isa-coverage` 回绿。
4. 只改 `tests/**`、`tools/llvm/llvm-isa-backend-matrix.*` 和测试驱动；不改实现/spec/contracts；不新建平行测试树。
5. 测试任务独立分支；实现补丁不得夹带测试资产。

## 验收

1. `make check-inst-smoke`/targeted 向量真实 rc=0；负例必须 FAIL/ILLI。
2. `make check-lit` 与 `make check-isa-coverage` 真实 rc=0；旧 `rf` 断言/矩阵必须已更新。
3. `make check-tests-index`、`make check-case-ledger` rc=0。
4. QEMU system 与 gem5 FS 对应 case 结果一致；差异必须定位，不比较时序。
5. 证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。

## 完成区

**测试结果**：QEMU 段本轮完成：`.work/evidence/TESTCASES-090t-qemu/run.sh` rc=0（checks=28 failures=0）——独立 oracle 140 项、targeted `fp/scaleb.yaml` 12/12、`atomics/sc-rd0.yaml` 14/14、`make check-inst-smoke` 90/90、`validate-vectors`、`check-tests-index`（241）、`check-case-ledger`（1995）、`check-spec-cite-targets`、`semantics_gate --check-only`（L3 载体 22 册/1012 例）、`check-dirs`/`check-no-residue`/`check-interface` 全 rc=0；3 组注入（错期望值 / rdHB≠0 / 删 ledger 行）均可达 FAIL→cp+md5 还原→回绿。LLVM 段沿用前轮：`check-lit` 161/161、`check-isa-coverage` PASS。**gem5 FS 段仍 BLOCKED：GEM5-005t 未完成，未运行/未伪造其结论**。
**修改文件**：本轮新增/改：`tests/inst/fp/scaleb.yaml`（新载体，12 例）、`tests/inst/atomics/sc-rd0.yaml`（14 例）、`tests/inst/inventory.md`（L3 载体登记 2 行 + 范围说明）、`tests/inst.yaml`（`inst-fp-001` / `inst-atomics-008`）、`tests/case-ledger.tsv`（`--write` 重生成 +26 行）、`tools/qemu/semantics_gate.py`（`CARRIER_DIRS` 增 `fp`）；本任务书。证据：`.work/evidence/TESTCASES-090t-qemu/{run.sh,run_cases.py,oracle_vectors.py,logs/run.log}`。前轮 LLVM 文件（`fp-encoding.s`/`fp-ldexp.ll`/`gen-orrr.s`/`llvm-isa-backend-matrix.*`）见下，本轮未再改。
**验收结果**：scaleB：`ftsclb rf4,rf1,rd3`=`0x44544043`，1.5f×2^2=6.0f(`0x40C00000`)、rd3=-1→0.75f、rd3=200→+Inf、-200→+0、rd0→1.5f、dst=src→6.0f，f64 同构（6.0/0.75/±Inf/0），rf3=10.0 诱饵在全部用例中不生效。sc：12 条 `sc.* rdHB=rd0` 全部 ILLI；`sc.o.nn rd5,rd0,[rb4]`（先 `lr.o.nn` 持保留）成功：rd5=0、内存=0；`sc.o.nn rd5,rd6,[rb4]` 成功：rd5=0、内存=`0x0123456789ABCDEF`。L2 代表集不变（90 条全绿）。
**新发现/坑**：① `lr` 的 rdHB 固定 rd0（spec SimRISC-12），手写 sequence 用 rdHB≠0 会先 ILLI——本轮实际踩到，由 oracle 的 lr 字段检查拦下；② rf 组无 `input_state` 通道，浮点源/结果须用 `ld.o/st.o rf` 原始编码 sequence；③ `validate_vectors` 只扫 `base/*.yaml` 且 id 必须为 M1 身份 ⇒ 非 M1（fp/m9）向量须放非 base 载体，并同步 inventory 门控表 + `CARRIER_DIRS` + `tests/inst.yaml` + case-ledger（缺一即红）；④ `sc` 的「不写内存/不置结果」在 YAML 不可断言（legality 无 expected_state），只能依赖静态 ILLI 语义；⑤ 旧 `rf,rf,rf` 与新语法同编码，QEMU 侧只能靠 rf 诱饵证明第三源取 rd。
**遗留问题**：① gem5 FS 段 BLOCKED（GEM5-005t 未完成）；QEMU system × gem5 FS 一致性对照未做；② 未跑 L3 全量 `check-inst`（本轮 = targeted + 结构断言 + L2 smoke）；③ `sc rd0` 汇编期拒绝仍只有 LLVM-142t 定向验证（未新增 lit）；④ 前轮 LLVM 遗留项不变。

## 审阅记录

### 第 1 轮 engineer 自审

逐文件审查：
- `fp-encoding.s`：`word=0x44544188` 未变（`rdhd` bits[5:0]=8 与旧 `rf8` 同编码）；OBJ/ASM 同步 `rd8`；两条 `OLD-RF` RUN 用 `%not` + 诊断 `invalid operand`，旧写法若被接受则 `%not` 非零 ⇒ 可达 FAIL（注入 1 实证）。
- `fp-ldexp.ll`：RUN 加 `--implicit-check-not=io2fo/it2ft`（全文件兜底）；三条 sclb 断言 `rf, rf, rd`；i64 加 `CHECK-NOT: ext.so`；注入 2 把断言改回 `rf` ⇒ check-lit rc=2，证可达 FAIL。
- `gen-orrr.s`：仅生成器产出变化（2 例 × 2 行），编码/OBJ 未动；`check-lit-full` 11/11，注入 3 改回旧拼写 ⇒ rc=2。
- `llvm-isa-backend-matrix.{tsv,md}`：重生成后 264 行；独立脚本 strip 行号逐字段比对，非行号差异恰 2 格（`ftsclb/fosclb` 的 `L1_asm`），L1/L2 统计不变；注入 4 改一格 ⇒ check-isa-coverage rc=2。
- `run.sh`：门控取真实 rc；lit 计数/矩阵行数现场解析不写死；无 `tee`；注入一律 cp 备份 + md5 对账（未用 git 还原）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

#### 第 1 轮 architect 提交（WIP）
- 档位：`待验收`（reviewer 未验收）⇒ WIP。
- 提交：`a83a9a7c` `WIP: TESTCASES-090t LLVM 资产同步（QEMU/gem5 阶段待实现）`（7 files, +358/-340）。
- 文件集对账：显式 staging 7 项，与完成区「修改文件」逐项一致（`fp-encoding.s`、`fp-ldexp.ll`、`gen-orrr.s`、`llvm-isa-backend-matrix.{tsv,md}`、本任务书、`milestones.md`）；漏提 0 / 多提 0 / 越界 0；无 `components/`、`spec/`、`contracts/`、QEMU/gem5、`Makefile` 改动；`git status --porcelain -uall` 除本行外干净。

### 第 2 轮 engineer 自审（QEMU 段）

**范围**：逐行审 `tests/inst/fp/scaleb.yaml`、`tests/inst/atomics/sc-rd0.yaml`、`tests/inst/inventory.md`、`tests/inst.yaml`、`tools/qemu/semantics_gate.py`（`CARRIER_DIRS`）、`tests/case-ledger.tsv`（生成物）与证据脚本；实机重跑 `run.sh`。

- 期望值来源：只据 `spec/SimRISC-07 §2.1`（`rfHC × 2^rdHD`，`rdHD∈rd`、`rd0` 为指数 0）、`spec/SimRISC-12`（`sc rdHB` 为结果目的、`=rd0 ⇒ ILLI`；`lr rdHB` 固定 rd0）与 `contracts/opcodes.yaml`（mask/value/fields/rule_refs）；数值用 `math.ldexp`+`ctypes.c_float` 独立重算（`oracle_vectors.py` 140 项），未读 QEMU 实现、未反推。
- 可达 FAIL：三组注入均实跑（错期望值 → scaleb rc=1；rdHB≠0 → sc 用例 rc=1；删 ledger 行 → `check-case-ledger` rc=2），全部 `cp`+`md5sum -c` 还原后回绿；两向量文件为本分支新增（untracked），故注入断言用 md5 变化，另对 tracked `case-ledger.tsv` 断言 `git diff` 非空。
- 脚本纪律：无 `tee`；每检查捕获真实 rc；计数现场统计（12/14/90/241/1995/22 册/1012 例），无写死期望；`trap` 清理注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-1 `lr` 的 rdHB 手写成 5（应固定 rd0），正例实机先 ILLI | ✅已修 | `sc-rd0.yaml` 两条 sequence 的 lr 字 `0x47005004`→`0x47000144` | targeted 14/14；`run.sh` rc=0 |
| F-2 oracle 未校验 lr 字段，F-1 只靠实机才发现 | ✅已修 | oracle 增 `lr.rdhb==0`、`lr.rbhd==sc.rbhd` 检查 | oracle checks=140 failed=0 |
| F-3 rf 诱饵可能恰好同值使断言假绿 | ✅已修 | oracle 增「诱饵指数结果 ≠ 期望」断言 | 12 例全过；错期望值注入 FAIL |
| F-4 非 M1 载体未登记会使 L3/inventory 红 | ✅已修 | `CARRIER_DIRS` 增 `fp` + inventory 2 行 + `tests/inst.yaml` 2 条 + ledger 重生成 | `semantics_gate --check-only` rc=0；`check-tests-index` 241；`check-case-ledger` 1995 |

**判决**：QEMU 段 finding 全部 ✅已修，可标 `待验收`；gem5 FS 段仍 BLOCKED（未声称完成）。
