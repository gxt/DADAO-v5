# QEMU-032t: ret rd0 运行期 ILLI 0x88 — imms18 非零时非法

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`SPEC-083t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - QEMU DADAO target 补丁集（`components/qemu/patches/`，当前 `ret` 的 translate 实现在 `target/dadao/translate/ctrl.c.inc` 或类似位置）
  - `contracts/opcodes.yaml`（`ret_riii_ra` 条目，SPEC-083t 完成后含 legality）
  - 已有 harness / min_rom_probe 模式（参考 `QEMU-018t`、`QEMU-014t` 的探针文件）

- **输出**：
  1. QEMU 补丁：在 `ret` 的 translate/执行路径中增加运行期校验——当 `rdha == rd0` 且 `imms18 != 0` 时，触发 **ILLI 0x88**（`0x80 | spec_cause_bit`，ILLI cause bit = 0x08，见 ADR-0004 D5）
  2. `min_rom_probe_ret_rd0`（或类似命名）：反例门控探针
     - **正例**：`ret rd0, 0` 正常执行（不触发 ILLI）
     - **反例**：`ret rd0, 1` 触发 ILLI 0x88，机器 fault 退出码 = `0x88`
     - **非 rd0 正例**：`ret rd1, 42` 正常执行（无此约束）
  3. 探针需注入前后真实输出（注入前后 `git diff` 非空）

- **约束**：
  - 需**增量重建 QEMU**（`JOBS=8`，预计 5–10 分钟），一次只跑一个长构建
  - 不提交 git
  - 全程中文
  - 探针的分支须双向验证（正例路径 + 反例路径）
  - 反例注入须可复原（还原后需重建）

## 验收标准

1. **正例**：`ret rd0, 0` 不触发异常，正常弹栈返回（或 RASUF，取决于 RAS 状态，但不触发 ILLI）。
2. **反例**：`ret rd0, 1` 触发 ILLI，QEMU fault 退出码 = `0x88`。
3. **反例**：`ret rd0, -1` 触发 ILLI，退出码 = `0x88`。
4. **非 rd0 不受影响**：`ret rd1, 42` 正常执行。
5. **探针脚本**：`min_rom_probe_ret_rd0` exit 0（正例 PASS + 反例 FAIL → 综合 PASS）。
6. **反例门控**：将 ILLI 检查逻辑临时回退后，反例用例应不再触发 ILLI（证明检查逻辑确实生效）。
7. **回归**：已有 QEMU 测试/harness 不受影响（`make check-qemu` 或相关测试全绿）。
8. **还原验证**：注入反例 → 确认 FAIL → 还原 → 重建 → 确认 PASS，全流程记录在完成区。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）