# SPEC-127t: 聚合传参/HFA/HPA 约定收口 + HFA/HPA 槽位上限 8

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-124t`（调用约定契约收口 `contract-abi §6`，`已验证`）、`SPEC-126t`（返回 `rd8`，`已验证`）；与所有改 `spec/`/锁任务**串行**（同改 `spec/DADAO-21` + `manifests/spec-readonly.lock.toml`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）」**（2026-10-09）。

- 授权范围 = **`spec/DADAO-21 §传参 §聚合类型参数` 的 HFA/HPA 槽位上限 `4 → 8`**（含「计数检查」「示例表」「不是 HFA/HPA」示例）。
- **不立 ADR**（延续用户既定：本族为规范正文口径收口，非跨模块合约决策）。

## 变更边界（授权内 / 待裁定 / 不含）

1. **授权内（本任务落）**：`spec/DADAO-21 §传参 §聚合类型参数`——**HFA/HPA** 的槽位上限由 **4 个寄存器槽位（32 字节）→ 8 个寄存器槽位（64 字节）**；HFA（RF bank）/ HPA（RB bank）各叶子字段仍占 1 槽位、自 `16` 起递增。
2. **待用户裁定（**不擅改**）**：**通用聚合（非 HFA/HPA）** 是否同步由 4 槽位（32 B）改 8 槽位（64 B）——见下「待用户裁定」节。
3. **不含实现**：`components/**`/`tools/**`/`tests/**` 归 `LLVM-062t`（整数聚合）/ `LLVM-066t`（HFA/RF）；本任务 `git diff` 与实现侧交集为空。

## 待用户裁定（通用聚合 4 vs 8，**不擅定**）

> 用户原话只点名 **HFA/HPA → 8 槽位（64 B）**；**通用聚合（非 HFA/HPA）** 是否同步改动**未明说**。HFA/HPA 属 **RF/RB 单 bank**，通用聚合**跨 bank**（RD 块 / 指针间接），两者机制不同。

| 选项 | 口径 | 影响 |
|---|---|---|
| **A（本任务默认落点）** | 仅 **HFA/HPA → 8**（64 B）；**通用聚合仍 4 槽位（32 B）**（`≤32B` 拆 RD 块、`>32B` 走指针间接，**不变**） | 与用户原话**字面一致**；通用聚合行为不变，`LLVM-062t` 整数聚合路径**不受影响** |
| **B** | 通用聚合**也**改 **8 槽位（64 B）**（`≤64B` 拆 8 块、`>64B` 走指针） | 通用聚合同步放宽；`>32B 且 ≤64B` 的聚合由「指针间接」变为「8 个 RD 块」，**`LLVM-062t` 整数聚合传参须按 8 块实现**（否则不一致） |

- **本任务只落 A 的显式部分**（HFA/HPA = 8），**不擅改通用聚合**（保持 4 槽位/32 B）。
- **`待用户裁定`**：请用户就 **A / B** 明确裁定；裁 **B** 时须**另立变更**（同步改通用聚合正文 + `LLVM-062t` 范围），**不并入本轮**。
- **阻塞提示**：`LLVM-062t`（整数完整调用约定）实现的是**通用聚合**传参 ⇒ 该裁定应在 `LLVM-062t` 下发前给出，否则其通用聚合上限口径悬空。

## 接口规范

- **输入**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §传参 §聚合类型参数`（现「最多消耗 4 个寄存器槽位（32 字节）」「计数检查：叶子字段总数 ≤ 4」+ HFA/HPA 示例表与「不是 HFA/HPA」表）。
  - **用户授权原话**（见上「用户裁定」；`DADAO-21` 为**上游只读册**，改册须用户事先授权 + **同一变更**内同步 `sha256` 锁，`Process-06`）。
  - `.tao/knowledge/contract-abi.md`（现 §5 表把 HFA/HPA/聚合传参标 `Excluded from M3`（→ M4）；§6.1 已收口聚合返回/多返回值 M6 口径）。
  - `contracts/abi.yaml`（`deferred_to_m4` 索引含 `hfa`/`hpa`/`aggregate_arguments`；机器可读投影）。
  - `manifests/spec-readonly.lock.toml`（`DADAO-21` 段 `sha256`）。
- **输出**：
  1. `spec/DADAO-21 §传参 §聚合类型参数`：**HFA/HPA 槽位上限** `4 → 8`（64 B）——「计数检查」`≤4 → ≤8`；示例表与「不是 HFA/HPA」表相应更新（补 8 槽位正例、负例阈值改 `>8`）；使「最多消耗 4 个寄存器槽位（32 字节）」的表述在 **HFA/HPA** 与 **通用聚合** 之间**不自相矛盾**（**最小改动**：把 4 槽位限定为「非 HFA/HPA 聚合」，HFA/HPA 明示 8）。
  2. `.tao/knowledge/contract-abi.md`：把 **HFA / HPA / 聚合传参** 由 `Excluded from M3`（→ M4）**提升为 M6 口径**——§5 表状态列 + §6 新增/扩展聚合传参口径（HFA/HPA ≤8 槽位 + 通用聚合取选项 A）+ 头部「`Excluded from M3`」行同步；实现归属标 `LLVM-062t`（整数聚合）/ `LLVM-066t`（HFA/RF）。
  3. **派生投影**：`contracts/abi.yaml`（`deferred_to_m4` 索引中 `hfa`/`hpa`/`aggregate_arguments` 的 M6 口径注记；若存在 ABI 投影生成器则重跑，以实测为准）。
  4. `manifests/spec-readonly.lock.toml`：`DADAO-21` 段 `sha256` **同步**（改毕 `sha256sum` 实测）。
- **约束**：
  - **只动授权范围**：`spec/` 仅允许 `DADAO-21`；其余只读册**一字不改**（`git diff --name-only | grep '^spec/'` 仅 `DADAO-21`）。
  - **不改通用聚合**（选项 A）：不得把「非 HFA/HPA」的 `4 槽位/32 B` 改为 8；除「使表述自洽」所必需的最小限定外，不扩义。任何越出 HFA/HPA 的改动 ⇒ **停下报告、待用户裁定**。
  - 只读册改动**必须同一变更**内同步 `sha256` 锁（`Process-06`）。
  - 与 `SPEC-123t`/`SPEC-124t`/`SPEC-126t` **串行**（同改 `spec/`）。
  - 计数口径**派生自单一真源、不硬编码**（`ISS-148` 教训）。
  - 与 `SPEC-124t §6.1`（聚合返回 K=8）**一致**：HFA/HPA 传参上限 8 与返回上限 8 口径统一。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-127t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-127t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-127t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **HFA/HPA 上限 8**：`DADAO-21 §传参 §聚合类型参数` 中 HFA/HPA 的计数检查 == `≤ 8`、示例含 8 槽位正例、负例阈值 == `> 8`（给 `grep`/摘录真实输出）；HFA（RF）/HPA（RB）仍各占 1 槽位、自 `16` 递增。
2. **通用聚合未改**：非 HFA/HPA 聚合的「`≤32B` 拆 RD 块 / `>32B` 指针间接」**逐条未变**（给 `git diff` 该段 `-`/`+` 对账，证明未改通用语义）。
3. **表意自洽**：不存在「HFA/HPA 8 槽位」与「聚合最多 4 槽位」并存的矛盾表述（给相关句子摘录）。
4. **contract-abi 同步**：`§5` 中 HFA/HPA/聚合传参状态 == M6 口径；`§6` 含聚合传参口径（HFA/HPA ≤8 + 通用聚合选项 A）；实现归属标注 `LLVM-062t`/`LLVM-066t`。
5. **派生投影同步**：`contracts/abi.yaml` 相应注记与 `contract-abi.md` 一致。
6. **锁同步**：`DADAO-21` 段 `sha256` == 实测；`make check-spec-readonly` EXIT=0；**未改册** `sha256` **逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 计数仅 1/1）。
7. **授权范围**：`git diff --name-only | grep '^spec/'` 仅 `spec/DADAO-21-ABI-应用程序二进制接口.md`。
8. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）。
9. **一键证据脚本**：`.work/evidence/SPEC-127t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `≤ 8` 改回 `≤ 4` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
10. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`spec/DADAO-21-ABI-应用程序二进制接口.md` + `manifests/spec-readonly.lock.toml` + `.tao/knowledge/contract-abi.md` + `contracts/abi.yaml` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
