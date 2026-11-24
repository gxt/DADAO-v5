# m16-testcases-009: cfx5 用例三方跑

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-qemu-003`、`m16-chipyard-017`、`m16-gem5-021` 全部合入
**可并行分片**：否（共享 `tests/arch/cache/`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

三个平台的 cfx5 寄存器面/命令已就位后，用同一组用例做三方签名比对。用例落 `tests/arch/cache/`，由 `tests/arch/run_arch.py --cfx 5` 驱动。

> **异步模型说明（更新至 2026-11-24 R2）**：异步投递已按 `ADR-0061` + R2（`m18-spec-004/005`）落定——`cg9` 为捕获缓冲、掩码在当前模式 monitor、`escape imms18=2` 不异步返回。本任务的 cfx5/cache 用例不触达异步，不受影响；若后续用例触达异步，期望值按 R2，不得按旧 target-first/monitor-first 断言。

## 要做

1. **寄存器面用例**：`cache_exist`=0b11、`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 写读回、保留位/非法编码 `CFXREG`。
2. **命令用例**（D 侧）：脏行 `invalidate` 后内存旧值、`clean` 后新值、`flush` 后失效；范围 all/单行/区间；`cache_enable=0` 不维护。
3. **命令用例**（I 侧）：改写代码后 invalidate，取指执行新代码；clean no-op。
4. **使能/异常**：`cache-model=off` 时 cfx5 按 `CFXREG`（QEMU/gem5）；RTL Tiny 无 cfx5。
5. **三方签名**：QEMU/gem5/RTL 同一 ELF 逐槽一致；不一致登记 `expected-divergences.yaml` 并由用户裁。
6. **覆盖点**：每条用例映射到 `m16-spec-001` 条款，写入 `tests/arch/vast-arch-inventory.md` 的 cfx5 行。

## 覆盖范围（用户 2026-11-22 确认）

**必须覆盖（三方）**：

1. 寄存器面：`cache_exist`（on=`0b11`）、`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size`；非法编码 ⇒ `CFXREG`；
2. D 侧：`clean`（写回保留）、`invalidate`（丢弃不写回）、`flush`（写回+删除）；范围 all/PA 单行/PA 区间；选择 I/D/双；
3. 数据可见性：用 DMA 直读内存，验证 clean 后新值、invalidate 后旧值、flush 后新值且行失效；
4. 使能门控：`cache_enable` 对应位为 0 时不维护；编码校验不受使能影响；
5. I 侧：`clean` no-op；`invalidate`/`flush` 后取指重取（**gem5 必须**，022 已证明可行；RTL 017、QEMU 003 补齐）。

**可选 / 差异**（登记 `expected-divergences.yaml`）：QEMU 的 cache 时序/替换策略（功能模型不建模）；gem5 的 I-Cache 命中/缺失（性能，不测）；RTL 的预取/I-D 一致性（未实现）。

**H/S/U 三模式**（用户 2026-11-22）：本任务的用例应经 `tests/arch/common/env/` 在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（`run_arch.py --mode`）；权限不允许的模式必须显式标注 `modes` 排除原因并 fail-closed，不得静默只跑 hmon。

## 不做

- 不改平台实现；不改 cache 几何；
- 不做性能/周期判据。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 用例/期望/驱动脚本集中 `tests/arch/cache/`；不写运行期路径；术语「寄存器组」；
- 仿真不进 L2/L3（`check-arch-vast` 按需）。

## 验证

运行期证据目录内的 `run.sh`：

1. `run_arch.py --cfx 5 --platforms qemu,gem5,chipyard --cache-model on` 三方签名逐槽一致；
2. 覆盖点与 `m16-spec-001` 条款逐条对应，现场统计条数；
3. **可达 FAIL**：改一个期望槽 ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；
5. `--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
