# QEMU-025t: QEMU trans_* 命名同步到 0.5.4 id

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

`tools/integ/check_interface_alignment.py` 的 `QEMU trans ↔ opcodes.yaml` 检查报 **FAIL（0/254）**：

```
MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1]
MISSING: cmp.uo_orrr_rd -> trans_cmp_uo_orrr_rd
...
```

根因：**QEMU 补丁的 `trans_*` 函数命名与 0.5.4 的 `opcodes.yaml` id 期望不一致**：

- QEMU 侧实际命名（旧风格）：`trans_cmp_uo`、`trans_ld_ub` 等（`mnemonic` 级）
- 检查器期望（新 id 风格）：`trans_cmp_uo_orrr_rd`（`id` 级，含 format/feature）

即 `check_qemu_trans.py` 按 `opcodes.yaml` 的 `id`（`mnemonic_format_feature`）拼期望函数名，而 QEMU 补丁的 trans 函数未随之更新。

**注**：此检查只读 `opcodes.yaml` + QEMU 补丁（**不需 QEMU 二进制**），属 pre-existing 跨模块缺口（0.5.4 id 化后的遗留）。

## 目标

使 QEMU 的 `trans_*` 命名与 0.5.4 的 `id` 一致，`check_qemu_trans.py` 与 `check_interface_alignment.py` 的该项通过。

## 待确认（执行前与用户确认）

1. **命名方案**：QEMU 的 `trans_*` 是否改为 `trans_<id>`（如 `trans_ld_ub_rrii_rd`）？还是**检查器侧**放宽匹配（如按 `mnemonic` 匹配，容忍多格式）？
2. **改动范围**：QEMU 补丁中有多少 `trans_*` 函数需改名？（`decode` 表由 `generate_decodetree.py` 生成？）
3. **是否影响 QEMU 解码逻辑**（函数名 vs 语义）

## 修改内容（待确认后细化）

- QEMU `target/dadao/*.c.inc` / `translate.c` 的 `trans_*` 函数命名
- `tools/qemu/check_qemu_trans.py` 的期望函数名构造
- `tools/qemu/generate_decodetree.py`（若其生成 `trans_*` 引用）
- 重生成/重建补丁（按 `docs/spec/component-patching.md`：裸 `git diff`，一文件一补丁）

## 约束

- **命令缺失/构建失败 → 停下报告，禁止自行安装/下载**
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `python3 tools/qemu/check_qemu_trans.py`：**254/254**（M1 178/178）
2. `python3 tools/integ/check_interface_alignment.py` 的 `QEMU trans ↔ opcodes.yaml` **PASS**
3. 补丁格式合规（每份恰 1 个 `diff --git`）
4. `make check` EXIT=0
5. 反例验证（注入缺失/错名 trans → 检查失败）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）