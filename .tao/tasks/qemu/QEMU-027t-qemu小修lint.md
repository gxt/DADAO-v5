# QEMU-027t: qemu 模块小修/lint（deferred 遗留）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（来自 `deferred.md`）

qemu 模块的 3 项遗留：

1. **3 文件缺末尾换行**（`QEMU-003t` 交叉复核 F2）：`target/dadao/helper.c`、`helper.h`、`translate.c` 缺 POSIX 末尾换行（patch 内 3 处 `\ No newline at end of file`）。需重建补丁。
2. **`check_qemu_trans.py` 的 patch 行分类**（`QEMU-019t`/`024t` 观察）：`collect_trans_defs()` 对 `+`/`-`/上下文行**一视同仁**，「后序 patch 删除某 `trans_*` 且未重现」会因前序 `+` 行被误判为存在。建议：只计 `+`/上下文行（忽略 `-` 行）。
3. **harness 硬编码 op 常量 ↔ `opcodes.yaml` 交叉校验**（`QEMU-023t` reviewer）：`tests/scripts/build_test_binary.py` 的 `encode_*` 一律硬编码 op 值（如 `st.b`=0x18），存在漂移风险。建议：加 lint 把 `encode_*` 的 op 常量与 `contracts/opcodes.yaml` 逐条比对。

## 约束

- 只做上述 3 项；不改指令语义
- 末尾换行须重建补丁（`git diff`，一文件一补丁）
- 逐条核对，禁止正则批量替换；命令缺失/构建失败 → 停下报告
- 完成后 `make check` EXIT=0；`make build-qemu` 重跑一致

## 验收标准

1. 3 文件末尾换行修复
2. `check_qemu_trans.py` 只计 `+`/上下文行；反例（构造 deleted-only 名）能 FAIL
3. harness `encode_*` op 常量 ↔ `opcodes.yaml` 校验 lint 就位；反例（改错 op）能 FAIL
4. 补丁格式合规；`make check` EXIT=0

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