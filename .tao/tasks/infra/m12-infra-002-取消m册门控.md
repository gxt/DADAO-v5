# m12-infra-002: 取消 m 册门控（M12 起）

**模块**：infra
**项目里程碑**：M12
**状态**：待开始

## 用户裁定（原话）

「m11 收口→仍然是立一个 integ 的任务，M11里程碑核验，只是没有 m 后缀，该检查任务状态检查任务状态，该归档归档即可」（用户 2026-11-08；此前对「m 册门控去留」选 B = 取消）

## 背景

- `tools/infra/check_milestone_tasks.py`（`make check-milestone` 的一环）当前**强制要求**当前里程碑存在 `m` 册，无册即非零退出。
- M11 已裁定不建 `m` 册、改由 `INTEG-061t` 核验；M12 起编号为 `m12-<module>-<NNN[N]>`（无 k/t/m 后缀），也不会有 `m` 册。
- 结果：`make check-milestone` 在当前里程碑上必然红——是**假的失败信号**，会掩盖其余真实检查。
- `make check-milestone` **不在 L1**（`.PHONY` 列表中有，但 `_locked-check` 不含）。

## 目标

1. `check_milestone_tasks.py`：把「必须有 m 册」改为**可选**——
   - 有 `m` 册：按原规则校验（册自报里程碑一致、册内任务号真实存在、至少列一个任务号）
   - 无 `m` 册：**不再判失败**，打印「本里程碑按用户裁定不建 m 册，跳过」（非静默：明确输出分支名）
   - `--self-test` 覆盖两分支（有册缺→FAIL；无册→PASS 且打印跳过；册内号不存在→FAIL）
2. `Makefile` 的 `check-milestone` 目标：移除对 m 册的硬依赖，保留 SIMRISC archive / sha / sync-nonmaskable / L3 report / `check-tasks --strict` 各项。
3. `docs/Process-07` 的 `check-milestone` 行同步（取消 m 册要求，说明 M12 起口径）。
4. 确认 `Makefile` help 文本与 `AGENTS.md` 若有「m 册」表述同步（只改规则表述，不改历史任务书）。

## 验收标准

1. `python3 tools/infra/check_milestone_tasks.py` rc=0 且输出含「不建 m 册，跳过」分支
2. `--self-test` rc=0；新增两分支的自检项各有可达 FAIL
3. `make check-milestone` 在有/无 m 册两种状态下都不因 m 册而红（其余项失败仍红）
4. `make check`（L1）rc=0
5. 不改 `INTEG-061t`、不改历史任务书、不改已归档册
6. 完成区 ≤30 行、无运行期路径

## 说明

- 这是**门控语义变更**（不是放宽判据）：m 册从「必需」变为「可选」，其余校验项保持。
- 若将来恢复 m 册（例如某里程碑需要专门核验册），本改动仍兼容（有册即校验）。
