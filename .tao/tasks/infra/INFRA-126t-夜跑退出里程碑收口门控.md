# INFRA-126t: 夜跑退出里程碑收口门控（改为观测口径）

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `TESTCASES-101t` 独立；只改门控与文档，不改测试）
**状态**：待开始

## 用户裁定（2026-11-06）

> 「我觉得，对于夜跑，你有些误解；Dadao并不是完整、成型的系统，夜跑是需要随时调整的，其目的也并非是为了里程碑」
>
> 选 **A：夜跑只做观测，不阻断收口** —— 「本轮照常跑一次夜跑，红项逐条分诊/登记；M11 收口不要求报告全绿（需调整 check-night-report/check-milestone 依赖或用例口径）」。

## 现状

`make check-milestone` 的依赖里含 `check-night-report`，而 `check-night-report` 要求**最近一次夜跑报告存在且全部 rc=0**。效果：夜跑被当成里程碑验收动作，任何用例红都会阻断收口；而 DADAO 仍在演进，夜跑成员/期望/known-fail 本就需要随时调整。

`check-l3-report` 保持现状（L3 是可重复的全量验证，不属本次调整范围）。

## 目标

1. `Makefile`：`check-milestone` **去掉** `check-night-report` 依赖；保留 `check-l3-report`、`check-spec-archive`、`check-spec-archive-verify`、`check-sync-nonmaskable`、`check_milestone_tasks.py`、`check_tasks.py --strict`。
2. `check-night-report` 目标**保留可用**（仍是「报告存在性 + 结构 + 结果」检查），但改为**按需诊断**，不再被里程碑门控调用；其自身判据与 `--self-test` 不改。
3. 同步文档与帮助文本：
   - `Makefile` 中 `check-milestone` / `check-night-report` 的注释与 `make help` 文案（夜跑 = 观测，按需消费；不再列入里程碑依赖）。
   - `docs/Process-07-门控分层规范.md`：§ 表格中 `check-milestone` 依赖与「夜跑（非三层之一）」行的口径；触发点描述。
   - `docs/Process-09-测试组织规范.md`：里程碑门控组成与夜跑定位（两处）。
4. 记录口径：夜跑红项按「真缺陷 / 语料假设过时 / 环境」分诊，真缺陷立任务或 issue；不以「一次全绿」为里程碑条件。
5. 不改夜跑成员集合、不改 `night_run.py` 行为、不改任何测试用例与期望。

## 范围 / 非范围

**在范围内**：`Makefile`、`docs/Process-07-门控分层规范.md`、`docs/Process-09-测试组织规范.md`、`tools/testcases/check_night_report.py`（仅文档字符串措辞，如提及里程碑层）、本任务书、`milestones.md`、`discussing.md`。

**不在范围**：`check-l3-report` 及 L3 口径、`check-night-report` 判据逻辑、`night_run.py`、测试用例/期望、QEMU/gem5/LLVM 组件。

## 验收标准

1. `make -n check-milestone` 不再包含 `check-night-report`；仍包含 `check-l3-report` 等其余依赖。
2. `make check-night-report` 仍可用：对现有报告按原判据给出 rc（红报告仍 rc=1，`--self-test` rc=0）。
3. `make check`（L1）rc=0；`make check-milestone` 在本任务改动后可达（m 册存在时）或至少不再因夜跑缺失而失败。
4. 文档三处口径一致：夜跑 = 观测/按需消费，不阻断收口；L3 仍为收口门控。
5. 反例：临时把 `check-night-report` 依赖加回 ⇒ `make -n check-milestone` 断言 FAIL；还原后回绿（`cp`+`md5sum -c`，禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**门控口径**调整，不是降低测试覆盖：夜跑照常跑、结果照常落报告，只是不再作为收口硬条件。
- 若后续希望恢复硬门控，可另立任务改回（本任务把口径写清即可）。
