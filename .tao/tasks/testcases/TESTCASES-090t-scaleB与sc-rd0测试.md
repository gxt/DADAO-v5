# TESTCASES-090t: scaleB C1 与 sc rd0 测试

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-181t`、`LLVM-142t`、`QEMU-078t`、`GEM5-005t`
**状态**：待开始

## 用户授权

用户 2026-11-01：scaleB C1 与 `sc rdHB=rd0 ⇒ ILLI` 的测试必须随实现独立调整；不新建 `tests/gem5`，复用现有 `tests/inst`/`tests/arch`/`tset` scope。

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
3. 只改 `tests/**` 和测试驱动；不改实现/spec/contracts；不新建平行测试树。
4. 测试任务独立分支；实现补丁不得夹带测试资产。

## 验收

1. `make check-inst-smoke`/targeted 向量真实 rc=0；负例必须 FAIL/ILLI。
2. `make check-tests-index`、`make check-case-ledger` rc=0。
3. QEMU system 与 gem5 FS 对应 case 结果一致；差异必须定位，不比较时序。
4. 证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
