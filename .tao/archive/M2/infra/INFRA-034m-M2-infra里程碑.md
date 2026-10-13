# INFRA-034m: M2 infra 里程碑

**模块**：infra
**项目里程碑**：M2
**状态**：里程碑
**目标**：infra 在 M2（规范与接口冻结）期间完成构建/门控/台账基础设施收口——fetch 浅取、doctor 依赖检查、产物路径定位、组件补丁幂等与内容断言、门控收口（`check-patch-tree`/`check-asm-prose --strict`/`check-lit`/`check-no-residue`/`check-tasks`）、文档分层改造 T2/T3、组件源文件规模约定、一键证据脚本规程、台账合并（`issues.yaml` + `lessons.md`）与 M2 归档前置清理；`make check` 全绿。
**关联任务**：`INFRA-015t`、`INFRA-016t`、`INFRA-017t`、`INFRA-018t`、`INFRA-019t`、`INFRA-020t`、`INFRA-021t`、`INFRA-023t`、`INFRA-024t`、`INFRA-025t`、`INFRA-026t`、`INFRA-027t`、`INFRA-028t`、`INFRA-029t`、`INFRA-030t`、`INFRA-031t`、`INFRA-032t`、`INFRA-033t`（18 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`Makefile`（`check` 门控集）、`tools/infra/{check_patch_tree,check_tasks,check_dirs,size_report}.py`、`.tao/knowledge/{issues.yaml,lessons.md}`、`spec/Process-01/03` 相关节
- `make check` 全绿（M2 门槛①）；`make check-no-residue` PASS
- 归档前置：`issues.yaml`/`lessons.md` 梳理已完成（`INFRA-033t`，`Process-04 §2`）

## 核验记录（2026-10-04，architect 核验）

**关联任务**：`INFRA-015t`~`INFRA-033t`（18/18）全部 `已验证`。

**命令核验（真实输出，2026-10-04）**：
```
$ make check ; echo EXIT=$?
...
check_issues: 72 open, 41 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0

$ make check-no-residue   → PASS（`make check` 成员）
```
（`check-patch-tree`/`check-asm-prose --strict`/`check-lit`/`check-no-residue` 均已在 `check:` 目标内；`check-tasks` 为报告型、不入阻断路径。完整输出见 `.work/log/integ/M2-milestone-make-check.log`。）

**归档前置**：`INFRA-032t`（`deferred.md`→`issues.yaml` 53 条 + 新建 `lessons.md`）与 `INFRA-033t`（`issues.yaml` 内容清理与校正、头部 M2 状态同步）均 `已验证` ⇒ 满足 `Process-04 §2` 归档前置（关闭已消解项 / 校正 scope / 移出教训类 / 判定 moot / 头部同步）。

**跨模块影响**：无未处置项——`issues.yaml` 中 open 项**无一 `scope: M2`**（实测 `scope` 含 `M2` 的 open issue = 0）。

**结论**：核验通过，置 `里程碑`。
