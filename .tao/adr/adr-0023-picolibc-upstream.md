# ADR-0023: picolibc 上游选择与 commit 锁定

**状态**：Accepted
**日期**：2026-10-11
**关联**：`ADR-0005`（组件锁多源；`manifests/components.lock.toml`）、`ADR-0002`（构建编排：`.cache/<name>.git` bare mirror + `.work/source/<name>` 工作树）、`INFRA-055t`（组件接入，`已验证`）、`INTEG-033k`（M7 启动）、`manifests/components.lock.toml`（`[[component]] name = "picolibc"`）

## Context（背景）

- M6 之后 **M7 的 test 重心调整为 picolibc 自带 test**（用户 2026-10-11 指示；`INFRA-055t` 已据指示接入组件）。
- 用户给定上游地址：`https://github.com/picolibc/picolibc`，并要求**锁定精确 commit**（`ADR-0005` 组件锁原则：以精确 commit hash 锁定，不用 tag/branch）。
- `INFRA-055t` 已把 picolibc 条目写入 `manifests/components.lock.toml`（`enabled = true`、`commit = 2ae376c6…`、`shallow = true`、`shallow_ref = "1.8.12"`），并完成浅裸镜像与工作树 fetch；**上游选择 + 精确 commit 的固化仍待本条 ADR 记录**（`INFRA-055t`「遗留问题」）。
- 上游事实（`INFRA-055t` reviewer 独立核验，实测）：默认分支 = `main`；**annotated tag `1.8.12`** 的 tag 对象 = `f859fb62…`，其 **peeled commit = `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`**；`refs/heads/release-1.8.12` 指向**同一 commit**；另存在 **lightweight tag `1.8.12-1`**（不同 commit）。GitHub Compare API：`2ae376c6…main` = `status=ahead`、`ahead_by=156`、`behind_by=0`（`2ae376c6` 是 `main` 的祖先）。

**承载位置**：本 ADR 只记**决策/理由/被否方案**；锁字段填写与 `enabled` 翻转已由 `INFRA-055t` 执行，组件补丁集（真移植）与构建集成归 M7（`INFRA-057t`）。本 ADR **不改** `manifests/components.lock.toml`。

## Decision（决策）

**D1 — 上游仓库**
picolibc 上游 = **`https://github.com/picolibc/picolibc`**（用户 2026-10-11 给定；上游官方仓库，不使用第三方 fork/镜像地址）。

**D2 — 精确 commit 锁定**
基线 commit = **`2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`**（= annotated tag **`1.8.12`** 所指向的 commit；用户 2026-10-11 裁定「**保持 1.8.12**」）。供 `manifests/components.lock.toml` 的 `[[component]] name = "picolibc"` 的 `commit` 字段使用。

**D3 — `shallow_ref` 用 tag（不可变）**
浅克隆引用 `shallow_ref` 取 **tag `1.8.12`**（用户 2026-10-11 澄清：其所说「tag」指 tag `1.8.12`）——tag 为**不可变引用**，优于可被上游移动的分支名 `release-1.8.12`（二者指向同一 commit `2ae376c6`）。`commit` 字段仍为精确 hash。

## Rationale（理由）

- **选上游正式仓库（D1）**：使用官方上游 + 精确 commit 锁定符合 `ADR-0005`「外部依赖以精确 commit 锁定」与 `ADR-0002` 的 bare mirror 流程，可 `make fetch` 幂等重建。
- **锁定 `1.8.12` 而非 `main`（D2）**：用户裁定「保持 1.8.12」。**被否方案 `main`**：相对 `2ae376c6` 领先 **156** commit（GitHub Compare API 实测），多为 **math/stdlib/stdio 修复 + 脚本/CI 现代化**，且 `main` 为开发分支、**无 release 保证**（用户 2026-10-11）。
- **锁定 `1.8.12` 而非 `1.8.12-1`（D2）**：**被否方案 lightweight tag `1.8.12-1`**（不同 commit）——其相对 `1.8.12` 的差异**绝大多数为 Debian 打包内容 + 2018 年老历史**，非上游 release 语义（用户 2026-10-11）。
- **`shallow_ref` 用 tag（D3）**：tag 不可变（分支可被上游移动），改用 tag 更稳且不改实际浅克隆的 ref（同一 commit、无需重下镜像）。对齐 `lessons §8.52`（`shallow_ref` 用 tag）。

## Consequences（影响）

- **锁条目（已落地）**：`manifests/components.lock.toml` 的 `[[component]] name = "picolibc"`：`enabled = true` / `repository = "https://github.com/picolibc/picolibc.git"` / `commit = "2ae376c6cdf4fef90ca2388ecf7a07457fa63cff"` / `shallow = true` / `shallow_ref = "1.8.12"`（`INFRA-055t` 落地）。
- **M7 移植**：真移植（cross file / machine-board dir / syscall stub / 构建集成）归 `INFRA-057t`；以**自带 test 为重心**接入门控（100% 验收）归 `TESTCASES-042t`。
- **可复现性**：commit 锁定后，组件不入库、按需 fetch；**升级须经新 ADR / 经授权的就地修订**。
- **不变**：不引入 picolibc 之外的 libc；M7 **不引入**动态链接 / linux-user / pk（见 `INTEG-033k §排除项`）。

## 状态说明

**Accepted（2026-10-11）**：`D1`–`D3` 已由用户逐条判定，无否决未处置。

- **判定来源与用户原话（2026-10-11，`lessons §7.3`）**：① 上游 —— 用户给 `https://github.com/picolibc/picolibc`；② commit —— 用户「**保持 1.8.12**」（= tag `1.8.12` 的 commit `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`）；③ `shallow_ref` —— 用户澄清其所说「tag」指 **tag `1.8.12`**（不可变）。原话落 `.tao/tasks/infra/INFRA-055t-picolibc组件接入.md` 完成区「版本裁定」与 `INTEG-033k §裁定汇总`。
- **变更流程**：决策变更（如升级 commit）时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`docs/Process-03-ADR编写规范.md`）。
