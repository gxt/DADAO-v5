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

**测试结果**：LLVM 阶段完成。`.work/evidence/TESTCASES-090t/run.sh` rc=0（12/12 PASS）；`--inject` rc=0（4/4 均可达 FAIL→cp+md5 还原→回绿）。`make check-lit` 161/161、`check-lit-full` 11/11、`check-isa-coverage` PASS（真源 264 == TSV 数据行 264）、`check-tests-index`（239）、`check-case-ledger`（1969）、`check-patch-tree`（205 patches）、`check-source-state`、`check-generator-sync`、`check-milestones-fresh` 均 rc=0。**QEMU/gem5 阶段 BLOCKED：QEMU-078t/GEM5-005t 未实现，未运行/未伪造其结果**。
**修改文件**：`tests/unit/llvm/lit/MC/DADAO/fp-encoding.s`（正例第三操作数改 `rd8`；旧 `rf` 只留 2 条 `OLD-RF` 负例 RUN）；`tests/unit/llvm/lit/CodeGen/DADAO/fp-ldexp.ll`（去 `io2fo/it2ft` 断言，改 `--implicit-check-not` + `rf, rf, rd` 断言）；`tests/unit/llvm/lit/MC/DADAO-gen/gen-orrr.s`（生成器重生成）；`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（生成器重生成）；本任务书；`.tao/knowledge/milestones.md`。证据：`.work/evidence/TESTCASES-090t/{run.sh,run.log,inject.log}`。
**验收结果**：`ftsclb rf4, rf6, rd8` = `44 54 41 88`、`fosclb rf4, rf6, rd63` = `44 74 41 bf`（期望值由 `contracts/opcodes.yaml` 现场派生，objdump 回读含 `rdN`）；旧 `ftsclb/fosclb rf4, rf6, rf8` rc=1 `invalid operand`；`llc` ldexp：f64/f32 为 `ext.so rd4, rd16, 31; fosclb/ftsclb rf8, rf16, rd4`，i64 直用 `rd16`，全程无 `io2fo/it2ft`。矩阵与旧版逐字段比对（去掉行号）仅 `ftsclb/fosclb` 的 `L1_asm` 两格变化，`accept 264/reject 0`、编码 mismatch 0、`L2 yes 202/no 62` 不变。
**新发现/坑**：① lit 资产分两类：`gen-orrr.s`/`gen-fast.s` 是 `generate_lit_vectors.py` 生成物，`fp-encoding.s`/`fp-ldexp.ll` 为手写；`opcodes.yaml` 已被 SPEC-181t 改为 `rdhd`，重生成器只改了 `gen-orrr.s` 4 行（ASM 注释+指令），编码字未变（`rf8`/`rd8` 同位域值 0x88）。② 矩阵重生成的大 diff 主要是 `DADAOCodeGen.td.patch` 行号漂移（LLVM-142t 补丁增行），非语义变化；`check-isa-coverage` 基线实际有 4 项（含多处行号）。③ `%not ... | FileCheck` 可作旧语法负例，但必须同时断言诊断文本，否则“未知助记符”等其它失败会假绿。④ `--implicit-check-not` 对整份 llc 输出生效，比在函数块内摆 `CHECK-NOT` 可靠。
**遗留问题**：① QEMU/gem5 阶段全部 BLOCKED：12 条 `sc rdHB=rd0 ⇒ ILLI` 运行期负例、scaleB C1 运行期语义、QEMU system 与 gem5 FS 一致性对照均待 QEMU-078t/GEM5-005t 实现后补测；② 本次未新增 `tests/inst`/`arch` 运行期向量（依赖同一实现）；③ `sc rd0` 的汇编期拒绝未新增 lit（LLVM-142t 已定向验证，非本 LLVM 资产同步范围，可留测试阶段补）。

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
