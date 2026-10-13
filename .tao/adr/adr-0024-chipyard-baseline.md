# ADR-0024: Chipyard 上游基线（commit + 子模块快照）

**状态**：Candidate（**提案，待用户逐条确认**）
**日期**：2026-10-13
**关联**：`ADR-0005`（组件锁多源；`manifests/components.lock.toml`）、`ADR-0002`（构建编排：`.cache/<name>.git` bare mirror + `.work/source/<name>` 工作树）、`INFRA-073t`（Chipyard `1.14.0` 预研，`已验证`）、`INFRA-074t`（落地准备与 (1) 参考平台，`待开始`）、`manifests/components.lock.toml` / `manifests/chipyard-submodules.lock.toml`（拟新增）

> **本 ADR 为「提案（Candidate）」**：`D1`–`D5` 均为**草案**，**未经用户逐条确认**，**不得**写作 `Accepted`（`AGENTS.md`「ADR decision 逐条确认」）。确认后由主会话置 `Accepted`（`docs/Process-03` 流程）。
> **ADR 不承载规范正文**（`docs/Process-03`）：本文件只记**决策 / 理由 / 被否方案**；锁字段填写由 `INFRA-074t` 执行。

## Context（背景）

- **用途与落法已由用户裁定（2026-10-13）**：Chipyard 用途 = 「**1/2/3**」（(1) 参考平台 / (2) 搬进它家 / (3) 搬它家家具）；落法 = 「**先预研（推荐）**」；**ADR 立 = 「立 ADR（推荐）」**。
- **预研结论已 `已验证`（`INFRA-073t`）**：`1.14.0` **合适**（latest、Chisel 7 主线、lite 构建、fresh-clone 升级路径清晰）；**tag `1.14.0` → commit `0acc1e1…`** 已经**两路交叉核对一致**（`gitclone.com` 与 `ghfast.top`，`git ls-remote` 解引用）。细节/原始探测日志指针 → `INFRA-073t §2 / §4`（**内容溯源，非执行必需**）。
- **上游事实（引用 `INFRA-073t §2`，勿重复查证）**：Chipyard 实际 RTL = **主仓 + 数十个子模块仓**（`ucb-bar/*`、`chipsalliance/*`、`riscv-software-src/*` …，同属 GitHub 域名）；上游明确**跨版本 in-place 升级 not-recommended**（docs §1.4.5，建议 fresh clone）。
- **现有体例（`INFRA-073t §3.1` 现场核对）**：`manifests/components.lock.toml` 的 `[[component]]` = `name`/`repository`/**`commit`（40 hex）**/`shallow`/`shallow_ref`/`role`，多源 = `[[component.source]]`（`ADR-0005`）；文件头明文 **"Tags and branches are not accepted as reproducible baselines"**。
- **命中 ADR 判据（`docs/Process-03`）**：**高代价**（选上游 commit）、**外部依赖/契约**（上游组件基线）、**结论固化**（预研结论落为长期约束）⇒ 立本 ADR。

**承载位置**：本 ADR 只记**决策/理由/被否方案**；`components.lock.toml` 条目新增、子模块锁册生成、`enabled` 翻转**由 `INFRA-074t` 执行**。本 ADR **不改** `manifests/`。

## Decision（决策）— 逐条草案（**待用户逐条确认**）

**D1 — 基线版本与用途定位**
基线 = Chipyard **`1.14.0`**，commit **`0acc1e1de2d3284bcd4d876956932a013ffe1949`**（annotated tag `1.14.0` = `ff2d01f3da2490e7f7216d5bbbe3c8d96a960a03` 的 peeled commit；两路解引用一致）。
**用途定位** = **参考平台优先（1）**；**复用评估次之（3）**；**暂不做（2）**——并入 Chipyard 生态需新写 Chisel core 并重写 TileLink/Diplomacy 与软件栈（BootROM/PK/tests）、工具链、中断/CSR 模型（全部假设 RISC-V），**风险高、代价最高**（依据 `INFRA-073t §6/§7`）。

**D2 — 锁定方式（主仓 commit + 子模块快照）**
(a) **主仓**：在 `manifests/components.lock.toml` 新增 `[[component]] name = "chipyard"`，字段 = `enabled` / `repository = "https://github.com/ucb-bar/chipyard.git"` / `commit = "0acc1e1de2d3284bcd4d876956932a013ffe1949"` / `shallow = true` / `shallow_ref = "1.14.0"` / `role`（RTL SoC 仿真 / Verilator 参考平台）；**并加 `[[component.source]]`**（主 `gitclone.com`、备 `ghfast.top`，遵 `ADR-0005` 多源）。
(b) **子模块快照**：**新增 `manifests/chipyard-submodules.lock.toml`**（`format = 1`，逐条 `path` / `url` / `commit`（40 hex）+ **`lite` 布尔标记**），其内容由**pinned commit 上的 `git submodule status --recursive` 全量导出**（`url` 取 `.gitmodules`）。
**理由**：`tag` 不足 —— ① tag 可 **force-move**（非可复现基线，与 `components.lock.toml` 文件头政策**直接冲突**）；② tag **不含子模块 SHA**（只锁主仓 ⇒ 子模块 commit 随上游漂移）；③ 上游要求 **fresh clone** ⇒ 需**整树（主仓 + 子模块）快照**以便随时重建。

**D3 — lite 子集原则**
只初始化**所需子模块**（**禁** `--recursive` 全量 ✗）；lite 子集清单**由首次成功构建现场导出后固定**（写入 `chipyard-submodules.lock.toml` 的 `lite` 标记），不预先写死。候选清单为**推测**（`INFRA-073t §5.4`）。

**D4 — 工具链隔离（互不替换）**
v5 的 `gcc`/`llvm`/`picolibc` 与 Chipyard 的 **conda 工具链互不替换**（`PATH` 内**不覆盖** v5 既有工具链）；**Verilator 由我们侧装 ≥ `5.022` 并 pin**（apt 仅 `5.020` ✗；版本入锁/入记录）。理由：v5 组件锁（`llvm-project`/`qemu`/`picolibc`）为**精确 commit 基线**，被 Chipyard conda 隐式替换即破坏可复现性。

**D5 — 验收口径（草案）**
M8 以「**参考平台能跑通 `pk`（+ **可选** Linux）并与我们 QEMU 的结果对照**」为达成判据。(1) 冒烟 = `pk` 必达、Linux **可选**（依赖 FireMarshal/内核链，`INFRA-073t §4.4` 其 ref 可取性**未确认** ⇒ 不作必达）。

## Rationale（理由）

- **锁 commit 而非 tag（D1/D2）**：对齐 `ADR-0005` 与 `components.lock.toml` 文件头政策；`shallow_ref` 仍用 **tag `1.14.0`**（不可变引用，类比 `ADR-0023 D3`），`commit` 字段为精确 hash。
- **子模块快照独立成册（D2b）**：主仓 `[[component]]` 体例（`patch_dir`/`patch_series` 等）**不适配**数十条子模块；独立 `format = 1` 锁册更清晰，且与 `spec-readonly.lock.toml` 的「清单型锁册」体例一致。
- **lite 而非全量（D3）**：全量含 BOOM/gemmini/firesim/FPGA/VLSI 等**与本用途无关**的核与工具，量级数十 GB；lite 只保 Verilator flow + bootrom + 外设 + 软件链（`INFRA-073t §5.4`）。
- **工具链隔离（D4）**：v5 的既有可复现性**优先**于 Chipyard 的构建便利；Verilator 版本进锁 ⇒ 与 `ADR-0005` 同口径。
- **先 (1) 后 (3)、(2) 后置（D1）**：先跑通整条链路（代理下载 + conda/sbt/Verilator + lite clone + RocketConfig Verilator 仿真）验证可行性，再评估复用清单落地（`INFRA-073t §8`）。

**被否方案**：
- ✗ **只锁 tag `1.14.0`（不锁 commit / 无子模块快照）**：tag 可 force-move + 不含子模块 SHA ⇒ 不可复现（与文件头政策直接冲突）。
- ✗ **`git submodule update --recursive` 全量**：量级数十 GB、含无关核/工具，成本高且拖慢链路验证。
- ✗ **混用 Chipyard conda 工具链（替换 v5 的 gcc/llvm/picolibc）**：破坏 v5 组件锁基线，跨模块不可复现。
- ✗ **立即做 (2)「搬进它家」**：须新写 DADAO Chisel core + 重写 TL/Diplomacy 与 RISC-V 假设的软件栈/工具链/CSR 模型，代价最高（`INFRA-073t §7`）。
- ✗ **跟随 `main`/分支**：非可复现基线（`ADR-0005`）。

## Consequences（影响）

- **锁条目（拟落地）**：`manifests/components.lock.toml` 新增 `chipyard`（`INFRA-074t`）；**新增** `manifests/chipyard-submodules.lock.toml`（`INFRA-074t` 首次 lite clone 后生成）。
- **下载源（用户已裁定，2026-10-13）**：GitHub 主仓 + 全部子模块 = 主 `gitclone.com` / 备 `ghfast.top`；conda = **TUNA**（conda-forge/defaults）、ucb-bar 通道走 `conda.anaconda.org` 直连（`INFRA-073t §4.5`）。**实际下载须用户授权后开始**（`mirrors.md` 流程第 4 步）。
- **约束**：**不改** `spec/`、`contracts/`、组件补丁；Chipyard **不进入** v5 组件补丁集（`docs/Process-01`）—— 它是**参考平台**，非 v5 交付组件。
- **可复现性**：commit + 子模块快照锁定后，按需 clone；**升级须经新 ADR / 经授权的就地修订**（`docs/Process-03`）。
- **后续**：`INFRA-074t` 落地（P1 环境 / P2 拉取 / P3 最小构建 / P4 (1) 冒烟）；(3) 复用清单落地**另立任务**（依赖本 ADR 与 `INFRA-074t` 结论）。

## 状态说明

**Candidate（提案，2026-10-13）**：`D1`–`D5` 为**草案**，**待用户逐条确认**后方可置 `Accepted`（`docs/Process-03` 流程：先置 `Candidate`；评审通过后由主会话置 `Accepted`）。

- **判定来源**：用户已确认的上游裁定 = ① 用途「**1/2/3**」；② 落法「**先预研（推荐）**」；③ **立 ADR**（「立 ADR（推荐）」）；④ 下载源「按建议定源 + 开工」（主 `gitclone.com` / 备 `ghfast.top` / conda TUNA）。**其余（D2–D5 细则）为架构师草案，不得视为已确认**。
- **变更流程**：决策变更（如升级 commit / 调整 lite 子集）时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认。
