# m16-testcases-016: cfx63 power 基础用例（三方）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`（运行模式环境）合入（同改 `tests/arch`，串行）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 选 A）

9 个 cfx 里 cfx63 是唯一“三方都有实现、但用例覆盖不均”的：QEMU 有 step5 启动链（`integ046t`），gem5 Vast 无用例，RTL 只有 `prevcfx.S`/`causeid.S` 手工探针。本任务补一件 cfx63 **基础用例**，把三方签名对齐。

## 要做

1. **寄存器面**：`cfx_power` 的 cg7 BootROM 块（start/size）、power ctrl、复位 `inner_cfx_code=63`；位域/读写属性按 `contract-see`/`Kaiwu §3` 现场解析。
2. **移交语义**：power→hmon 的 `trap cfx_hmon`；hmon 收到的 `prev_cfx`/`inner_cfx_code` 与 `cg5 rc1` 一致（复用 `prevcfx.S` 的检查点）。
3. **载体**：复用 step5 启动链（`tests/ee-vast/power_vast.S` + hmon），QEMU/gem5/RTL 各后端；RTL 侧把现有 `tools/chipyard/excp/prevcfx.S` 的检查点纳入统一 case。
4. **三方**：QEMU + gem5 先跑；RTL 侧可直接接（power 已实现），签名逐槽一致；不一致登记 `expected-divergences.yaml`。
5. **不回归**：step5 启动链（`integ046t`）、Tiny 的 power/hmon、cfx3/4/5 现有用例不变。

## 不做

- 不做 cfx63 的电源域/时钟等平台功能（只做 cfx 寄存器 + 移交）；
- 不改 QEMU/gem5/RTL 实现；
- 不做 cfx0/2/15/32/34（各自任务）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语「寄存器组」；
- 仿真不进 L2/L3（按需 `check-arch-vast`）。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx63 寄存器面：cg7 BootROM 块、power ctrl、复位 `inner_cfx_code=63` 逐项；
2. power→hmon 移交：`prev_cfx`/`inner_cfx_code`/`cg5 rc1` 与期望一致；
3. 三方同一 ELF 签名逐槽一致（RTL 侧可直接接；若暂不可用，显式 fail-closed 并登记）；
4. **可达 FAIL**：注入「移交后 `prev_cfx` 错」/「cg7 块错」⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
