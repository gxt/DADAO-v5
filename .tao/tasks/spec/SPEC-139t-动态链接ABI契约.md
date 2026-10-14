# SPEC-139t: 动态链接 ABI 契约（`contract-dynlink.md`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`，`D2` 无内核 / `D3` musl 自带 ldso）；`ADR-0019`（`R_DADAO_*` 重定位类型）+ `ADR-0021`；`SPEC-138t`（并列契约，无先后硬依赖）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景 / 依据

- **M8 主线**（`ADR-0025`）：无内核的 Linux 用户态栈；**P2 = 动态链接**（`ADR-0025 D6`）。
- **`ld.so` = musl 自带 ldso**（`ADR-0025 D3`；用户原话「用 musl 自带 ldso（推荐）」）；**无内核目标**（`ADR-0025 D2`）⇒ loader 走**用户态**。
- **既有重定位类型**（`ADR-0019` / `ADR-0021`，归一化于 `contract-elf §2`）：`R_DADAO_ABS48` / `REL26` / `REL20` / `REL14` / `REL12` / `ABS12`——**均为静态链接类型，无动态重定位类型**。
- **`R_DADAO_*` 编号扩展 = 需用户逐条确认**（`AGENTS.md`「ADR decision 逐条确认」）：**就地扩 `ADR-0019`** vs **新 ADR**——本任务内标为**待确认**，**不代decide**。
- **与 `DADAO-0628` 的对照（**内容溯源，非执行必需**；只读 `.cache/refs/**`、不复制代码）**：0628 将「Dynamic linking, TLS」置于「Linux kernel」之后；其 musl `reloc.h` 把 `REL_GOT`/`REL_PLT`/`REL_RELATIVE`/`REL_COPY` **占位**映射到单一 `R_DADAO_64`（无真动态类型）。**v5 差异** = **无内核**（`D2`）⇒ 由 musl `ldso`（`D3`）+ 用户态承担；类型集须**显式定义**，不沿用 0628 的占位方案。

## 接口规范

- **输入**：`ADR-0025`、`ADR-0019` / `ADR-0021` + `contract-elf §2`、musl `ldso`（**外部参照，内容溯源，非执行依赖**）、`spec/DADAO-21-ABI` / `spec/DADAO-22-SBI`。
- **输出**（落点 `.tao/knowledge/contract-dynlink.md`；**新增契约文件**，`check-knowledge-dir` 白名单允许 `contract-*.md`）：
  1. **PIC/PIE 口径**：`-fPIC` / `-pie` 语义与地址无关约定。
  2. **GOT/PLT** 结构与访问约定。
  3. **动态重定位类型集（候选，待定）**：`RELATIVE` / `JUMP_SLOT` / `GLOB_DAT` / `TLS_*`——**待定**，须与第 6 项（编号扩展方案）一并定。
  4. **`PT_INTERP` / `AT_*`**：`PT_INTERP` 指向 musl `ldso` 路径约定；启动时 `AT_*`（`AT_PHDR` / `AT_BASE` / …）注入约定（**无内核** ⇒ 由谁注入**须定**）。
  5. **`ld.so` 路径约定**：musl `ldso` 落点 / 命名（`ADR-0025 D3`）。
  6. **`R_DADAO_*` 编号扩展方案**：**就地扩 `ADR-0019`** vs **新 ADR**——**待用户逐条确认**（本任务标「待确认」，**不代decide**）。
- **约束**：**不代decide** 用户未确认的 `R_DADAO_*` 扩展；**不改** `ADR-0019`（除非用户确认后就地修订）；**不改** `spec/`、`contracts/` 机器数据、组件补丁；与 `contract-elf §2` 既有编号方案**不冲突**。
- **落点迁移接口**：同 `SPEC-138t`（若 `INFRA-071t` 获批，本契约随之整体迁 `contracts/`；引用路径**不写死**）。

## 验收标准

1. `contract-dynlink.md` 落 `.tao/knowledge/`，含上述 6 项；GOT/PLT / `PT_INTERP` / `AT_*` 表述与 `ADR-0025`（`D2` 无内核 / `D3` musl ldso）一致。
2. 动态重定位类型集与 `R_DADAO_*` 扩展方案**逐条有归属**：已定 **或** 标「待用户逐条确认」（含选项：就地扩 `ADR-0019` / 新 ADR），**无臆造**。
3. 与 `ADR-0019` / `contract-elf §2` 既有编号**无冲突**（`grep` 真实输出）。
4. 门控：`make check` / `check-knowledge-dir` / `check-knowledge-refs` / `check-no-residue` / `python3 tools/infra/check_issues.py` 各 rc=0。
5. （若需裁定）用户裁定**原话**原样写入本任务书。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
