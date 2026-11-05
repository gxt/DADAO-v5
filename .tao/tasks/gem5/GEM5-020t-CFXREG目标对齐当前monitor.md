# GEM5-020t: gem5 CFXREG 目标对齐当前 monitor

**模块**：gem5
**项目里程碑**：M11
**依赖**：`QEMU-083t`（已验证；QEMU 已把 CFXREG 目标改为当前 monitor）、`SPEC-186t`（DADAO-12 §5.2 A/A1）
**状态**：待开始

## 执行环境
本地；只改 gem5 实现/补丁，不改 spec/QEMU/tests 期望。

## 背景

`QEMU-083t` 已把 `cfx2rd`/`cfx2rc` 的 `CFXREG` 目标从“被访问 cfx”改为“当前运行模式 monitor”，并同步了 arch 探针期望。gem5 仍为旧语义，导致：

- `TESTCASES-098t` 现场矩阵 14 条 `GEM5_ONLY_FAIL`，全在 `node/arch`
- `m5_perm_badcombo_cfxreg` gem5 自环超时
- 13 个 cfx/PTW/模式探针目标不符

## 目标

1. 在 gem5 的 `cfx2rd`/`cfx2rc` 非法寄存器组合路径，把 `CFXREG` 目标从 `cfxha` 改为当前运行模式 monitor（`inner_run_mode` 对应 umon/jmon/smon/hmon），与 QEMU-083t / §5.2 一致。
2. 对齐 QEMU-083t 已同步的 arch 探针语义；不改测试期望值。
3. 源树 base+1 干净；按 `docs/Process-01` 重导出 gem5 补丁；不改 QEMU/LLVM/spec。
4. 重跑 gem5 Node/Tiny 代表测试，验证 14 条 node/arch 红行转 `AGREE_PASS`。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/**`（cfx/isa/异常路径）、`components/gem5/changelog.md`、`components/gem5/README.md`（若需）、本任务书、`milestones.md`、`ISS-342` 关闭。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/qemu/**`、`components/llvm/**`、`tests/**` 期望值、`tools/testcases/parity/**`（矩阵由 TESTCASES-098t 重生成）。

## 验收标准

1. **目标正确**：gem5 非法 `cfx2rd/cfx2rc` 组合 ⇒ `CFXREG` 进当前 monitor；`m5_perm_badcombo_cfxreg` 不再自环/超时。
2. **矩阵转绿**：`TESTCASES-098t` 重跑后 `node/arch` 14 条 `GEM5_ONLY_FAIL` → `AGREE_PASS`；`GEM5_ONLY_FAIL=0`、`DIFF=0`、`QEMU_ONLY_FAIL=0`。
3. **构建/回归**：`make build-gem5`、`check-gem5-decode`、`check_b6.py`、`make check-arch`、`make check-inst`、`make check`（L1）rc=0；源树 base+1 干净。
4. **反例可达 FAIL**：把目标改回 `cfxha` ⇒ `m5_perm_badcombo` timeout/FAIL；`cp`+`md5sum -c` 还原后回绿。
5. **范围**：无 spec/QEMU/tests 改动；完成区 ≤30 行；状态 `待验收`。

## 说明

- 以 QEMU-083t 的 10 处 `cfxha`→`env->inner_run_mode` 为参照，逐处核对 gem5 对应路径；不要只改一处。
- `CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`、合法读写、Tiny 直通 fault 不要动。
- 不改 `tests/arch/umon/expected.yaml` 等期望；QEMU-083t 已同步，gem5 只对齐实现。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
