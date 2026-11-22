# m16-testcases-017: `check-arch-smoke` 代表集重选（三平台分开）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`（运行模式环境）、`m16-testcases-009`/`016`（cfx5/cfx63 用例）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22）

`check-arch-smoke` 用 `cache-model=off`（不测 cache，cfx5 的 on 用例进按需 `check-arch-vast`）。`tests/arch` 成型后，代表集要**重选**：不需要多，但覆盖面稍广；**三个平台分开**；控制测试时间。

## 要做

1. **代表集来源**：从 `tests/arch.yaml` 的 `level: smoke` 现场派生，每平台一份：
   - `qemu`：现有 umon 代表 + 少量 cfx4/5/63 基础用例；目标总时长 **≤5 min**；
   - `gem5`：与 QEMU 同 case 集的代表（能跑的子集）；目标 **≤10 min**；
   - `chipyard`（RTL）：只选少量代表（如 cfx5 寄存器面、cfx4 一个 walk）；**不塞进 L2/L3**，按需跑。
2. **覆盖面**：每平台至少覆盖 cfx0/2/3/4/5/63 各 1 条（cfx15/32/34 若 RTL 未补，按实际登记）；不要求每个 cfx 多例。
3. **Makefile**：`check-arch-smoke` 与 `check-arch` 用 QEMU 代表集（off）；新增按需目标或在 `check-arch-vast` 里跑 gem5/RTL 代表集。
4. **时间控制**：证据脚本记录各平台实测总时长；超过目标的用例降级或移出 smoke。
5. **不回归**：`check-l3-report` 四 scope；`check-arch-smoke` 仍绿。

## 不做

- 不改用例语义/期望；
- 不把 RTL 仿真放进 L2/L3；
- 不新增 cfx 用例（只选代表）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `Makefile`、`tests/arch.yaml`、`tests/arch/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 三平台代表集各自跑通，记录实测总时长（QEMU ≤5 min、gem5 ≤10 min）；
2. 代表集条数现场派生，与 `tests/arch.yaml` 的 smoke 条目一致；缺平台/空集 fail-closed；
3. **可达 FAIL**：删一条代表/改一条期望 ⇒ 红；`cp`+md5 还原回绿；
4. `check-arch-smoke`、`check-l3-report`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
