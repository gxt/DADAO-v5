# m19-chipyard-002: 板上签名流回传（UART）与测试回路

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m19-chipyard-001`（上板骨架）、`m16-testcases-002`（签名机制）
**可并行分片**：否
**预估**：2–3 天
**档位**：中改
**状态**：待开始

## 背景

仿真侧的观测通道是 `+semiout`（`tools/testcases/lib/chipyard_engine.py:14-25`）；**板上没有这层**。签名机制（`tests/shared/asm/signature.inc` + `tests/shared/signature.py`）必须能原样在板上工作，否则 M19 会退化成手工验证，M20 的对比也失去载体。

## 目标

1. 板上通过 **UART** 把签名流回传给宿主，字节格式与仿真**完全一致**（`SIGUPD` 8 字节一条、末尾块写）；
2. 宿主侧复用 `tests/shared/signature.py`，**不另写解析器**；
3. 板上跑 `tests/inst` 代表例 ≥10，与 QEMU 流逐字节比对。

## 验收（逐条贴真实 rc）

1. ≥10 例：板上流与 QEMU 流逐字节相等（非抽样，逐条比）；
2. **漏跑可见**：删一条 `SIGUPD` ⇒ 对应槽为 `0xdeadbeef`，报「槽 N 未写」；
3. **可达 FAIL ≥3 路**：① 波特率配错 ⇒ 流截断/错位被长度断言抓；② 改期望值 ⇒ 报槽号 + 两侧值；③ 中途掉电/复位 ⇒ **BLOCKED** 而不是 PASS；
4. 门控：`check-inst-asm`、`check-tests-index`、`check-knowledge-refs` 真实 rc。

## 约束

独立 `git worktree`；**不提交 git**；不得改 QEMU/gem5 源码；板上回传文件不入库；硬件操作前须用户确认；完成区不写具体 `.work/**` 路径。
