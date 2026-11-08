# m12-infra-001: M12 任务编号与独立台账脚手架

**模块**：infra
**项目里程碑**：M12
**类型**：task
**状态**：待开始

## 用户裁定（原话）

> 「从M12开始，任务书都带上里程碑，例如 chipyard-m12-001t-***；这样在合并的时候不会出现冲突，且milestones.md也改为milestones-m12.md」
> 「m12是不是放在前面更好，m12-infra-001t，你觉得呢」
> 「从M12开始，任务书的后缀k/t/m，我觉得也可以取消了，就是<NNNN>」

最终口径（architect 归并，已经用户确认方向）：**`<mNN>-<module>-<NNNN>`**，无后缀。

## 目标

### 1. 任务编号与文件名

- 任务号：`m12-<module>-<NNN[N]>`（模块小写；序号 **3–4 位**均可，本仓库沿用 3 位：`m12-chipyard-001`）
- 任务书文件名：`.tao/tasks/<module>/m12-<module>-<NNNN>-<描述>.md`
- 任务书头部新增 `**类型**：task | kickoff | verify`（默认 `task`；`verify` 供里程碑核验用）
- **旧编号（M11 及之前，如 `GEM5-031t`）保持不变**，不做迁移

### 2. 独立台账

- 新增 `.tao/knowledge/milestones-m12.md`：与 `milestones.md` 同结构（`项目里程碑 = M12` 断言 + 待开始 / 进行中 / 已验证 三表，进行中带派单时间）
- `milestones.md` 继续作为 M11 台账，直至 M11 收口
- 两文件**互不影响**；M12 任务的派单/完成只改 `milestones-m12.md`

### 3. 门控与工具

- `tools/infra/check_milestones_fresh.py`：支持 `--file PATH`（默认仍为 `milestones.md`）；任务号正则同时接受旧格式（`PREFIX-nnn[suffix]`）与新格式（`mNN-module-NNNN`）
- `Makefile`：`check-milestones-fresh` 依次校验存在的台账（M11 必有；M12 存在则校验），任一红即红
- 覆盖性：`.tao/tasks/**` 的任务书须在其**所属里程碑**的台账中出现（按任务书 `**项目里程碑**` 字段分派）
- `docs/Process-07`：登记新编号与双台账规则
- `AGENTS.md`：任务编号段补一行新格式

## 范围 / 非范围

**在范围内**：`tools/infra/check_milestones_fresh.py`、`Makefile`（仅该目标）、`.tao/knowledge/milestones-m12.md`（新建）、`docs/Process-07`、`AGENTS.md`、本任务书。

**不在范围**：`check-milestone`（m 册门控，由 `m12-infra-002` 取消）、旧任务书改名、其它门控。

## 验收标准

1. `make check-milestones-fresh` rc=0（M11 台账 + M12 空台账都通过）
2. **可达 FAIL**：临时树放一份 `m12-test-0001` 任务书但 M12 台账未列 ⇒ FAIL 并指名；补行后回绿
3. 旧格式任务书（如 `GEM5-031t`）仍被正确覆盖，M11 台账不受影响
4. **跨台账隔离**：把 M12 任务写进 `milestones.md` ⇒ 应判「不在其所属里程碑台账」FAIL（或明确被 M11 校验拒绝）
5. `--file` 参数可用；缺文件时行为明确（M12 文件不存在 ⇒ 跳过，不 vacuous）
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 说明

- 本任务是**自举**：它自己用新编号命名。architect 已先做**最小自举**——`check_milestones_fresh.py` 的 `TASK_ID_RE`/`ROW_ID_RE`/`TASK_FILE_RE` 已接受 `m\d{2}-[a-z][a-z0-9]*-\d{3,4}`（旧格式并存），因此本任务书与台账行已可被门控识别；**剩余的台账路由/双文件/文档由本任务完成**。
- 本任务行暂时放在 `milestones.md`（M11 台账）；任务结束前须创建 `milestones-m12.md` 并把 M12 行迁入，同时把门控改为按任务书 `**项目里程碑**` 路由。
- 不改任何 M11 任务的状态与台账行
