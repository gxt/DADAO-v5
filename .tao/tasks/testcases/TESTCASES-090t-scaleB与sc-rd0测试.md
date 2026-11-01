# TESTCASES-090t: scaleB C1 与 sc rd0 测试

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
