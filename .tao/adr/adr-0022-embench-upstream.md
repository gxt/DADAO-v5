# ADR-0022: Embench-iot 上游选择与 commit 锁定

**状态**：Accepted
**日期**：2026-10-08
**决策者**：用户（逐条确认，见 `INTEG-023k §C/§D`；`SPEC-122t` 完成区 Q4 ③ + 「直接最新版本」裁定）
**关联**：`ADR-0005`（组件锁多源；`manifests/components.lock.toml`）、`ADR-0002`（构建编排：`.cache/<name>.git` bare mirror + `.work/source/<name>` 工作树）、`INTEG-023k §C`（`INFRA-051t`/`TESTCASES-039t`）、`INFRA-051t`（翻 `enabled=true`）、`TESTCASES-039t`（Embench 接入）、`manifests/components.lock.toml`（`[[component]] name = "embench-iot"`）

## Context（背景）

- M6 引入 **Embench-iot** 作为编译正确性/性能基准（`INTEG-023k §C` `TESTCASES-039t`；由 `INFRA-051t` 接入组件）。
- `manifests/components.lock.toml` 的 `[[component]] name = "embench-iot"` 现为模板占位：`enabled = false`、`commit = ""`，注释明示「**批量/精确 commit 待 M6 的 ADR 记录上游选择后填写并翻 `enabled = true`**」，并记「当前 master HEAD = `09c2ed8c…`（仅作记录，不作基线）」。
- v5 组件锁原则（`ADR-0005`）：**以精确 commit hash 锁定（不用 tag/branch）**；`ADR-0002`：bare mirror 落 `.cache/embench-iot.git`、工作树落 `.work/source/embench-iot`。
- 用户裁定（`INTEG-023k §C` + 本任务 Q4 ③）：「Embench 上游选择 + commit，pin master `09c2ed8c…`」；更早裁定原话：**「按正式镜像走，直接最新版本即可」**。

**承载位置**：本 ADR 只记**决策/理由**；`manifests/components.lock.toml` 的字段填写与 `enabled` 翻转由 `INFRA-051t` 执行，组件补丁骨架（`components/embench-iot/{patches,series,changelog}`）与 `make fetch` 亦归 `INFRA-051t`（本 ADR 不改 `manifests`）。

## Decision（决策）

**D1 — 上游仓库**
Embench 上游 = **`https://github.com/embench/embench-iot.git`**（正式上游镜像；不使用第三方 fork/镜像地址）。

**D2 — 精确 commit 锁定**
基线 commit = **`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`**（裸镜像 `.cache/embench-iot.git` 的 master HEAD，提交日期 2026-02-13；`git describe` = `embench-0.5-100-g09c2ed8`）。供 `INFRA-051t` 写入 `manifests/components.lock.toml` 并翻 `enabled = true`。

**D3 — 用 commit、不用 tag/branch**
以**精确 commit hash** 锁定（`ADR-0005` 组件锁原则）；镜像内存在 tag（`embench-0.5`/`embench-1.0`/`embench-2.0rc1`/`embench-2.0rc2`）**仅作溯源**，**不作基线**（用户裁定「直接最新版本即可」，落到锁定 commit）。

## Rationale（理由）

- **选上游正式仓库（D1）**：`embench-iot` 是 Embench 的官方仓库；使用正式上游 + commit 锁定符合 `ADR-0005`「外部依赖以精确 commit 锁定」与 `ADR-0002` 的 bare mirror 流程，可 `make fetch` 幂等重建。
- **pin master HEAD（D2/D3）**：用户裁定「按正式镜像走，**直接最新版本即可**」——直接 pin 镜像 master HEAD；用 commit 而非 tag，与全仓组件锁惯例一致（tag 可移动/被重新指向，commit 不可）。

## Consequences（影响）

- **`INFRA-051t`**：把 `commit = "09c2ed8c3b7008c95d08b038de4a3f6dc103ed70"` 写入 `manifests/components.lock.toml` 的 `[[component]] name = "embench-iot"`，并翻 `enabled = true`；建 `components/embench-iot/{patches,series,changelog}` 骨架；`make fetch` 落 `.work/source/embench-iot`（对应 bare mirror `.cache/embench-iot.git`）。
- **`TESTCASES-039t`**：以该 commit 的 Embench 基准做板级 shim（`initialise_board`/`start_trigger`/`stop_trigger`）+ 最小运行时；首验收 = 最小基准 QEMU 正确退出码。
- **可复现性**：commit 锁定后，组件不入库、按需 fetch；升级须经新 ADR / 授权就地修订。
- **不变**：不引入 `embench-iot` 之外的基准套件；M6 只做编译正确性（`INTEG-023k §A #3`：M6 不引 libc）。

## 状态说明

**Accepted（2026-10-08）**：`D1`–`D3` 已由用户逐条判定，无否决未处置。

- **判定来源**：`INTEG-023k §C/§D`（`INFRA-051t` 前置 ADR「Embench 上游选择 + commit」）与主会话 2026-10-08 夜 Q4 ③ 复述确认——用户对「③ Embench ADR（上游选择 + commit，pin master `09c2ed8c…`）」答**「全部确认（推荐）」**；更早裁定原话：**「按正式镜像走，直接最新版本即可」**（⇒ pin 镜像 master HEAD `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`）。用户原话落 `.tao/tasks/spec/SPEC-122t-ADR决策落地.md` 完成区（`lessons §7.3`）。
- **变更流程**：决策变更（如升级 commit）时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`spec/Process-03-ADR编写规范.md`）。
