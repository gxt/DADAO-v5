# SPEC-107t: `ADR-0004` 调整（ELF `e_entry`/段布局/加载约定）〔若需〕

**模块**：spec
**项目里程碑**：M4
**依赖**：`SPEC-105t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/adr/adr-0004-test-machine.md`（**Accepted**；D2.2/D2.3 冻结「flat binary、不做 ELF 解析、不读 `e_entry`、双镜像 `-bios`+`-kernel`、RAM 基址 `0xffff_0000_0000`」）。
  - `SPEC-104k` §已锁定边界：`dadao.lds` 地址布局依 `ADR-0004`（RAM 基址 `0xffff_0000_0000` 作 `.text`/entry；段序 `.text→.rodata→.data→.bss`）；对齐依 `contract-elf §5`；`FILEHDR PHDRS` 使 `.text` file-offset 0；**可能需调整 `ADR-0004`**（ELF `e_entry`/段布局/加载约定）。
  - `.tao/knowledge/contract-elf.md` §5（段对齐/VA=PA）/§6（pipeline，`SPEC-105t` 完成后的版本）。
  - `spec/Process-03-ADR编写规范.md`（就地修订/`Superseded`/新增 ADR 三种途径）。
- **输出**（**先判定、后落地**）：
  - **判定步**：核对 M4 引入 ELF（`ET_EXEC` + `e_entry` + LLD 链接脚本）后，`ADR-0004` D2.2/D2.3（「不做 ELF 解析/不读 `e_entry`/flat binary」）与 M4 目标是否冲突、需不需要扩展。
  - **若需调整**（大概率）：对 `adr-0004` **就地修订**（追加 `## 修订` 段，说明 rev 日期 + 变更范围 + 用户逐条确认），把加载约定扩展为「ELF（读 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`）**并保留 raw-bin 双镜像路径**（M3 `make test-codegen` 不回归）」；同步 `contract-elf.md §5/§6`（段布局/对齐/加载语义）与文件头 M1 范围说明。
  - **若判定不需调整**：在完成区记录**判定理由**（逐条对照 D2.2/D2.3），并说明 LLD/loader 如何在**不改 ADR**的前提下实现——仍需用户确认该判定。
  - **凡改动 `ADR-0004` 的任一 decision，必须逐条经用户确认**；把用户确认的原话（问答摘要）**原样记入完成区**。
- **约束（硬）**：
  - **本任务只做「ADR-0004 调整 + 合约同步」，不实现 LLD/loader**（分别归 `LLVM-056t`/`QEMU-042t`）。
  - **不得把未经用户逐条确认的 decision 写为 `Accepted`/就地定稿**（`AGENTS.md`「ADR decision 逐条确认」）。
  - 地址布局基线：RAM 基址 `0xffff_0000_0000` 作 `.text`/entry，段序 `.text→.rodata→.data→.bss`（`SPEC-104k` 已锁定，不重议）。
  - `ADR`/`contract` 为共享文件，**串行**；临时目录 `/tmp/opencode/SPEC-107t/`；**不提交 git**。

## 验收标准

1. **判定有据**：完成区给出「ADR-0004 需/不需调整」的判定与逐条依据（对照 D2.2/D2.3 原文），无悬空结论。
2. **用户确认记录**：若调整，`adr-0004` 的每个被改 decision 均有用户逐条确认的原话/摘要（原样落盘于任务书完成区）；`## 修订` 段含 rev 日期与变更范围。
3. **合约同步**：若调整，`contract-elf.md §5/§6` 与 `adr-0004` 一致（无相互矛盾）；`grep` 显示 §6 已描述 ELF 加载路径且保留 raw-bin 路径。
4. **门控**：`make check` EXIT=0；`git status` 仅本任务应有改动。
5. **反例门控**：`.work/evidence/SPEC-107t/run.sh` 对注入反例（删掉修订段、把 §6 改回「不读 `e_entry`」）**必须 FAIL**，还原后回绿。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
