# GEM5-032t: 定位 `math_test` 238→0 的根因（B7 注销前置）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`INTEG-059t`（已验证，记录了「现引擎 0 errors」）
**可并行分片**：否（单引擎重建/对比，单写者）
**状态**：待开始

## 背景（事实）

- `GEM5-015t`（2026-11-04）：`picolibc math_test` 在 gem5 FS 上 **238/76404 errors**（QEMU 0 errors），归因 **B7 浮点数值差异**，登记为已知 BLOCKED（`PICOLIBC_KNOWN_BLOCKED`）。
- `INTEG-058t`（2026-11-06 20:01，`3de11cac`）：**重写 `components/gem5/patches/src/arch/dadao/exec/b7.cc.patch`（137 行）** + `b7.hh`，即 FP 执行单元（含 `convert_f2i` 六档舍入迁移）。
- `INTEG-059t`（2026-11-09）：reviewer 亲跑 `math_test` ⇒ QEMU/gem5 **均 0 errors**（`Tested 76404 functions, 0 errors`），`run_parity` 报 `blocked masquerade`（登记与现状矛盾）。

## 目标

**确认 238→0 的根因**，为「缺陷关闭式重登记」提供依据（不是就地改写 BLOCKED）。

1. **候选根因**：`INTEG-058t` 的 `b7.cc` 重写（FP 执行 / 六档舍入）。请用证据确认或排除。
2. **验证方式（二选一或都做）**：
   - **A. 二进制对比**：分别用 `3de11cac^` 与 `3de11cac` 的 gem5 补丁集构建 gem5（`build-gem5`，两次），用**同一个** `math_test` ELF/argv 各跑一次，比对 errors 数。
   - **B. 单元/语义对比**：跑 `check-b7`（`tools/gem5/check_b7.py`）与 `b7_ref.py` 在 `3de11cac^`/`3de11cac` 两个补丁集下的结果；对 `b7.cc` 的语义 diff 逐处说明「旧实现错在哪、新实现如何修正」。
3. **排除测试条件变化**：确认两次跑的 ELF/argv/镜像/预算一致（若不一致，结论作废）。
4. **给出结论**：
   - 若是真修复 ⇒ 写「可注销 `PICOLIBC_KNOWN_BLOCKED`」的证据与建议（含根因 commit/文件/语义点）
   - 若不是 ⇒ 写明「测试条件变化」或其它原因

## 验收标准

1. 根因明确到 **commit + 文件 + 语义点**（如「`b7.cc` 的 `convert_f2i` 舍入方向」）
2. 至少 **2 个数据点**（修复前 / 修复后）用同一 ELF 跑出的 errors 数对比，命令与输出入完成区
3. 若用 A 方式：两次 `build-gem5` 的二进制 md5 不同、`check-gem5-decode`/`check-b7` 均 rc=0
4. 若用 B 方式：`check-b7` 在两个补丁集下各跑一次，结果差异逐条解释
5. `make check`（L1）rc=0（并发红须核实）
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- **不改** `PICOLIBC_KNOWN_BLOCKED`（注销由后续任务/architect 按结论执行）
- 不改 `math_test` 用例与期望
- 不改 spec/contracts

## 说明

- 重建 gem5 会占用 `.work/source/gem5` 与 `.work/build/gem5`，属**组件单写者**；开工前确认无其它 gem5 任务在跑。
- 长构建先申报耗时，落 PID/日志/`*_EXIT=$rc`。
- 结论必须区分「真修复」与「测试没跑到」——后者不算注销依据。
