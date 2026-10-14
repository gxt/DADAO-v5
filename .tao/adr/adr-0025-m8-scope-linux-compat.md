# ADR-0025: M8 范围与 Linux 兼容路线（无内核的 Linux 用户态栈）

**状态**：Accepted
**日期**：2026-10-14
**关联**：`ADR-0003`（Object ABI；M1 范围界定段「无动态链接、无 TLS、无 LLD」+ `## 修订`① 保留 LLD `FILEHDR PHDRS` 能力）、`ADR-0019`（DADAO 重定位类型 `R_DADAO_*`）、`ADR-0021`（`ld/st` 符号偏移重定位）、`ADR-0023`（picolibc 上游基线）、`ADR-0024`（Chipyard 基线；`§D5` `pk` 判据）、`spec/DADAO-21-ABI §4`（syscall 寄存器约定）、`spec/DADAO-22-SBI §2`（`umon`/`jmon`）、任务 `SPEC-138t` / `SPEC-139t`

> **本 ADR 已 `Accepted`（2026-10-14）**：`D1`–`D7` 逐条 = 用户对议题 **A–G** 的选择，经**主会话问答**取得并**逐条确认**（`AGENTS.md`「ADR decision 逐条确认」；`docs/Process-03` 流程）。
> **ADR 不承载规范正文**（`docs/Process-03`）：本文件只记**决策 / 理由 / 被否方案**；syscall 映射与动态链接 ABI 的规范正文由 P0 任务（`SPEC-138t` / `SPEC-139t`）落笔。

## Context（背景）

- **M8 主线（用户 2026-10-13/14 经主会话问答裁定）**：「**无内核的 Linux 用户态栈**：musl（静态→动态）+ QEMU user-mode + 与 RISC-V musl 的 **golden 对照**」。
- **上游已有 syscall 模型（勿重复发明）**：`spec/DADAO-21-ABI §4` 已定以 `trap cfxha, immu18` 发起、号在 `rd15`、参数 `rd16–31`/`rb16–31`/`rf16–31`、返回 `rd8`；`spec/DADAO-22-SBI §2` 已定 `umon(cfx0)`/`jmon(cfx1)` 的 `SBI_*_SYSCALL`（`immu18=0`）。**缺的不是 syscall ABI，而是 Linux 语义映射**（号表 / errno / 参数与返回值语义）。
- **M1 范围不是永久禁令**：`ADR-0003` 首段「单 TU / freestanding / 无动态链接 / 无 TLS / 无 LLD」为 **M1 范围界定**；其 `## 修订`① 已**原样保留** LLD 的 `FILEHDR PHDRS` 能力 ⇒ 动态链接不与之冲突。
- **QEMU 现状**：仅 **system 模式**（`qemu-system-dadao -M dadao-m1`）；`components/qemu/patches/` 已含 `target/` 结构 ⇒ user-mode（`linux-user`）为新增工作，非改造既有。
- **未闭环项**：`ADR-0024 §D5` 的 Chipyard `pk` 冒烟**未达**（`PK_EXIT=2`）⇒ `pk` 排障仍未处置。
- **命中 ADR 判据（`docs/Process-03`）**：**定位/方向**（阶段方向选择）、**跨模块/需一致**（spec / llvm / qemu / infra / testcases）、**多方案且需记录取舍**、**外部依赖/契约**（与 RISC-V musl golden 对照）⇒ 立本 ADR。

**承载位置**：本 ADR 只记**决策/理由/被否方案**；syscall 映射契约、动态链接 ABI 契约的规范正文由 P0（`SPEC-138t` / `SPEC-139t`）落笔。

## Decision（决策）— 逐条（**用户已逐条确认，2026-10-14，经主会话问答**）

**D1（议题 A）— Linux syscall 号表：沿用 RISC-V 编号**
**用户选择**：「**沿用 RISC-V 编号（推荐）**」。
**理由**：与 golden 对照（`D7`：RISC-V + musl 跑同程序）同口径，便于跨目标直接比较；避免自造号表、避免与对照面脱节。**被否**：自定号表（与对照目标脱节，无收益，且需额外映射层）。

**D2（议题 B）— 是否有内核目标：无内核目标**
**用户选择**：「**无内核目标（推荐）**」。
**理由**：M8 只做 Linux **用户态**栈（musl + QEMU user-mode），不引入内核（VFS / MM / 调度 / 信号）。**被否**：引入内核目标（超出 M8 范围、代价最高）。

**D3（议题 C）— 动态链接器 `ld.so`：用 musl 自带 ldso**
**用户选择**：「**用 musl 自带 ldso（推荐）**」。
**理由**：与 `D4`（musl 并存）一致，复用 musl 生态、免自写 loader。**被否**：自写 `ld.so`（无必要的新组件、无额外收益）。

**D4（议题 D）— musl 与 picolibc：并存**
**用户选择**：「**并存（推荐）**」。
**理由**：picolibc（M7 已交付、自带 test 100%）继续服务 freestanding / 小 libc 场景；musl 承载 Linux 用户态栈。**被否**：以 musl 取代 picolibc（丢弃 M7 既有交付与测试面）。

**D5（议题 E）— TLS/线程：先查证再定**
**用户选择**：「**先查证再定（推荐）**」（⇒ 若 musl **硬依赖** TLS 则**自动纳入** M8）。
**理由**：先以查证消除不确定性（musl 是否硬依赖 TLS/线程），再定归属，避免过早纳入或遗漏。**被否**：立即纳入（未查证即扩大范围）；立即排除（可能与 musl 硬依赖冲突）。

**D6（议题 F）— 顺序/判据：契约 → musl → 动态 → linux-user**
**用户选择**：「**契约→musl→动态→linux-user（推荐）**」。
**理由**：先冻结契约（P0）再实现；依赖自下而上（契约 → 静态 musl → 动态链接 → user-mode 宿主）。**被否**：并行无序（缺契约时实现漂移）。

**D7（议题 G）— golden 对照：要 golden 对照**
**用户选择**：「**要 golden 对照（推荐）**」（**RISC-V + musl 跑同程序**作对照）。
**理由**：以既有 RISC-V musl 生态作**独立参照**，检验 DADAO 用户态栈语义（含 syscall 号表口径 `D1`）。**被否**：不要对照（缺独立 oracle 面，回归不可辨）。

## Rationale（理由）

- **不重复发明规范正文（`D1`/`D2`）**：syscall ABI 已在上游 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2` 定义，本 ADR 只定 **Linux 语义映射路线**，正文归 P0 契约。
- **路线自下而上（`D6`）**：契约（P0）→ musl 静态（P1）→ 动态（P2）→ linux-user（P3）→ 对照/回归（P4），与「Spec-first」一致（期望值来自契约，不从实现反推）。
- **与 `DADAO-0628` 的对照（**内容溯源，非执行必需**；只读 `.cache/refs/**`、不复制代码）**：0628 的 roadmap 将「**Dynamic linking, TLS**」置于「**Linux kernel**」之后；其 musl 以 `trap cfx_smon` + `rd16` 传号 + **Linux asm-generic** 编号起步（其 `adr-0014`）。**v5 差异**：**无内核目标**（`D2`）⇒ 动态链接与 TLS 改由 **musl 自带 `ldso`（`D3`）+ 用户态**承担；**号表挂 `rd15`、沿用 RISC-V 编号**（`D1`；与 0628 的 `rd16`/asm-generic 不同）。

## Consequences（影响）

- **任务分解（P0–P4 路线指针）**：
  - **P0 契约**：`SPEC-138t`（Linux syscall 映射契约 → `.tao/knowledge/contract-syscall.md`）、`SPEC-139t`（动态链接 ABI 契约）。
  - **P1 musl 静态**：musl 静态最小集移植（crt/loader 骨架 + syscall stub ⇒ 静态可运行）。
  - **P2 动态链接**：`.so` / `ld.so` / `GOT`/`PLT` / `-fPIC`/`-shared` + `PT_INTERP`/`.dynamic`。
  - **P3 qemu-linux-user**：QEMU user-mode（`linux-user`）宿主 syscall 转发。
  - **P4 对照/回归**：RISC-V + musl golden 对照（`D7`）+ 回归门控。
  - （P1–P4 任务在 P0 契约落地后按 `D6` 顺序**另立**；本 ADR 只给路线指针，不预建任务。）
- **P0 契约落点**：`contract-syscall.md` 暂落 `.tao/knowledge/`（`check-knowledge-dir` 白名单允许 `contract-*.md`）；若 `INFRA-071t`（`contract-*.md` → `contracts/`，**待用户授权**）获批，则 P0 契约**随之整体迁移** `contracts/`——`SPEC-138t`/`SPEC-139t` 须为此留**可切换**的路径引用（不写死）。
- **`R_DADAO_*` 扩展（动态重定位类型）**：若 P0 动态链接 ABI 契约需新增重定位类型（如 `RELATIVE` / `JUMP_SLOT` / `GLOB_DAT` / `TLS_*`），是否**就地扩 `ADR-0019`** 还是**新 ADR**，**须用户逐条确认**（`AGENTS.md`「ADR decision 逐条确认」）——`SPEC-139t` 内标为**待确认**，本 ADR **不代decide**。
- **与既有基线的关系**：`ADR-0003` 的 M1 范围**不被本 ADR 推翻**（其为范围界定，非永久禁令）；`ADR-0024 §D5` 的 `pk` 判据维持，`pk` 未闭环项见「风险 / 未决项」。
- **约束**：**不改** `spec/`（上游只读册）、`contracts/` 机器数据、组件补丁；实现阶段由后续 `t` 任务落。

## 风险 / 未决项

- **`E`（TLS/线程）= 待查证**：musl 是否**硬依赖** TLS/线程**尚未查证**；查证结论决定 TLS 是否**自动纳入 M8**（`D5`）。登记于 `.tao/knowledge/milestones.md`「M8 规划区」待办。
- **`pk` 未闭环**：`ADR-0024 §D5` 的 `pk` 冒烟 `PK_EXIT=2` 未达 ⇒ 排障**待办**；未处置前不得据此判 `ADR-0024` 闭环。
- **动态重定位类型集**：`RELATIVE`/`JUMP_SLOT`/`GLOB_DAT`/`TLS_*` 候选**待 P0 契约定**（并与 `R_DADAO_*` 编号扩展方案一并待用户确认）。
- **errno 约定**：`rderrno`（`rd1`，`spec/DADAO-21-ABI §1`）与 musl 的关系**待 P0 契约定**。

## 状态说明

**Accepted（2026-10-14）**：`D1`–`D7` = 用户对议题 **A–G** 的逐条选择，已成立、无否决未处置。

**逐条确认记录**（2026-10-14，**经主会话问答**取得；取得渠道 = 主会话问答，2026-10-13/14）：

| 议题 | 用户选择（**原话 / 选项标签，原样**） | 落为 |
|---|---|---|
| A | 「沿用 RISC-V 编号（推荐）」 | `D1` |
| B | 「无内核目标（推荐）」 | `D2` |
| C | 「用 musl 自带 ldso（推荐）」 | `D3` |
| D | 「并存（推荐）」 | `D4` |
| E | 「先查证再定（推荐）」 | `D5` |
| F | 「契约→musl→动态→linux-user（推荐）」 | `D6` |
| G | 「要 golden 对照（推荐）」 | `D7` |

**变更流程**：决策变更时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`docs/Process-03`）。
