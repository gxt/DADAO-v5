# TESTCASES-103t: gem5 SE 基线预算与分类重跑（120s → 600s）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`GEM5-023t`（文件 I/O 与时钟；基线需在当前引擎上重跑）
**状态**：待开始

## 背景与事实

- `GEM5-021t` 基线使用 **120 s/例**；其中大量 `blocked` 实为 `timeout after 120s (SE, not a verdict)`，不是能力缺口
- 超预算重测（600 s）显示：7 例转 PASS、22 例仍 blocked（纯计算量）、1 例转 fail（`Misc/pi`，后由 `INTEG-058t` 修复）
- 当前基线把 `time budget` 与真实能力缺口混在同一张 `blocked` 表里，后续任务判断（例如「文件 I/O 还差几例」）会被超时干扰
- 驱动 `run_gem5_se_baseline.py` 已有 `--timeout`，但默认值与报告口径未按套件区分

## 目标

1. 把 gem5 SE 基线的默认预算改为**按套件可配**（建议 `libc-test` 300 s、`llvm-ts` 600 s、`embench` 300 s，命令写入任务书），并在报告里把 `timeout` 单列，不算能力缺口。
2. 重跑 static 基线（`GEM5-021t` 驱动），产出新的 JSON + 摘要（覆盖 `gap_inventory` 与 `timeout_recheck`），库内快照更新到 `.tao/knowledge/refs/`。
3. 对每个 `timeout` 案例做「预算倍数」实验（600 s / 1200 s）并记录：转 PASS / 仍超时 / 真失败，给出每例结论。
4. 不改 `tests/tset/**` 用例与期望，不改 gem5/QEMU 实现。

## 范围 / 非范围

**在范围内**：`tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`、`tools/testcases/lib/gem5_se_engine.py`（仅预算/分类）、`.tao/knowledge/refs/GEM5-021t-baseline-*`（更新快照）、本任务书、`milestones.md`。

**不在范围**：gem5/QEMU 实现、测试用例与期望、`tests/parity/matrix-M11.md`（G3 统一重生成）。

## 验收标准

1. 新基线报告：`blocked` 只含真实能力缺口；`timeout` 单列并标注「非能力」。
2. 每例 `timeout` 有 600 s 结果；仍超时的给「需要 >1200 s / 纯计算量」结论。
3. `qemu_only_fail` 0；`gem5_only_fail` 与前一版差异逐条解释（不得把超时改写成 PASS）。
4. `make check`（L1）rc=0；驱动 `--self-test`（如有）rc=0。
5. 反例：把预算改回 120 s ⇒ 报告里 timeout 数回升，验证分类不受手写影响；`cp`+`md5sum -c` 还原。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 该任务**不实现任何能力**，只校准口径；它必须在一个没有 gem5 构建在跑的窗口执行，否则结果不可复现。
- 全量 589 例在 600 s 预算下耗时较长（小时级），按套件分批跑并落日志/PID/EXIT。
