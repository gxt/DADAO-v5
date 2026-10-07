# SPEC-113t: ADR 决策落地（`ADR-0020` 新建 + `ADR-0004` 修订 + `ADR-0016` 范围）

**模块**：spec
**项目里程碑**：M5
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：本任务是 M5 的**决策先行**任务（`spec/Process-03`：决策先行）。把 `INTEG-019k` §说明「ADR 清单（决策提案）」的提案**逐条经用户判定**后落为 ADR。**决策入 ADR、规范正文入 `spec/`**（`INTEG-019k E17`）；本任务**只写 ADR**，规范正文归 `SPEC-114t`/`115t`/`116t`，实现归 LLVM/QEMU 任务。
- **输入（自包含）**：
  - `.tao/tasks/integ/INTEG-019k-m5启动与分解.md`——§ADR 清单（`ADR-0020` D1–D14、`ADR-0004` R1–R3、`ADR-0016` S1）、§第 2 轮用户裁定（2026-10-07，A2/A3/A5/A8/B9/B12 的定案值）。
  - `spec/Process-03-ADR编写规范.md`（模板与流程：`Candidate` → `Accepted`；决策变更**新增 ADR 或标 `Superseded`**，不直接改写已 `Accepted` 的决策；ADR **不承载规范正文**）。
  - `.tao/adr/adr-0004-test-machine.md`（**Accepted**，rev. 2026-10-06）、`.tao/adr/adr-0016-dadao-install-layout.md`（**Accepted**，D1–D11）、`.tao/adr/adr-0003-object-abi.md`、`.tao/adr/adr-0019-dadao-relocation-types.md`（背景）。
  - `spec/DADAO-12-SEE-主管系统运行环境.md`（§1/§2.1/§3/§5）、`spec/DADAO-22-SBI-主管系统二进制接口.md`（§1 调用约定；`:58` CFXREG）、`spec/SimRISC-11-其它.md`（§其它、L80/L81 措辞）、`.tao/knowledge/contract-abi.md §4.1/§4.4`（传参/返回寄存器）。
- **输出（本任务交付物）**：
  1. **`.tao/adr/adr-0020-see-semihosting.md`（新建）**：含 `Context`/`Decision`（D1–D14）/`Rationale`/`Consequences`/`状态说明`。**先置 `Candidate`**；**逐条经用户判定（保留/修改/否决）后**方可置 `Accepted`。
     - **`ADR-0020` 决策提案（D1–D14，来源 `INTEG-019k` §ADR 清单）**：
       - **D1** 入口判定：`trap cfxHA, immu18` 中 `immu18[17:16]==2'b11` ⇒ semihosting（与 `cfxha` 无关）。
       - **D2** 传参/返回寄存器（**用户 2026-10-07 裁定**）：号（标量）→`rd16`（=`rda0`）、参数块指针（地址）→`rb16`、返回值→`rd31`（`.tao/knowledge/contract-abi.md §4.1/§4.4`；指针返回才用 `rb31`，semihosting 不用）；共享层 `nr = common_semi_arg(cs,0)`、参数块指针 = `common_semi_arg(cs,1)`。
       - **D3** 号值 = **ARM 号值**（`OPEN 0x01`…`EXIT 0x18`/`EXIT_EXTENDED 0x20`…）；**服务集 = 完整 25 个**（含 D2 文件档；`SYSTEM`、`HEAPINFO` 都做——`SYSTEM` 的"执行宿主命令"风险保留在 ADR/spec 作**已知风险**）。
       - **D4** 返回机制：无 `escape` 指令——服务后 **PC 步进**（`env->pc += 4`）+ 写回返回寄存器。
       - **D5** 复用范式：复用 QEMU 共享入口 `do_common_semihosting(cs)`；DADAO 只提供 `common-semi-target.c` 式钩子；接入 = trap 译码后抛 semihost 内部异常（类比 `RISCV_EXCP_SEMIHOST`）。
       - **D6** 位宽/端序：由 `is_64bit_semihosting()` 决定；v5 恒 64 位；参数块 = 64 位字段 + target 端序（v5 大端）。
       - **D7** host 侧安全：默认值由 harness/Makefile 的 `-semihosting-config` 给；`auto` = 有 GDB⇒gdb、无 GDB⇒native；**建议默认 `gdb`/沙箱**，`native` 显式开。
       - **D8** `SYS_EXIT` **替代** `exit port`（`ADR-0004 D3`）⇒ 既有 M1–M4 依赖 exit-port 的向量/harness **迁移范围 = 全部**。
       - **D9** QEMU 权限实现粒度 = 完整：cfx 掩码 + 指令类型 mask + `switch_run_mode` + 权限异常（`NUPERM/NJPERM/NSPERM/NHPERM`）；**运行模式与 cfx 正交**。**权限范围 = 只做 `cfx0/1/2/3/63`**；**访问未实现 cfx ⇒ `CFXREG` 异常**（出处 `spec/DADAO-22-SBI-主管系统二进制接口.md:58`）。
       - **D10** 流程（两条路）：(a) **一般 `trap cfxHA, immu18`**（`immu18[17:16]≠2'b11`）：先过权限，允许则**走 spec 异常进入流程**（`spec/DADAO-12-SEE-主管系统运行环境.md §5`，含步骤 10「跳转至异常向量」）——**进入该 cfx 的向量**；(b) **semihosting**（`immu18[17:16]==2'b11`）：**QEMU 译码层短路**（与 `RISCV_EXCP_SEMIHOST` 同构）——**不进入向量**、直接服务并按 PC 步进返回（见 D4）。`switch_run_mode` 语义须在 spec/ADR 讲清。
       - **D11** `cfxha` 不设白名单：是否允许调用由权限控制。
       - **D12** 新 bootrom：M5 的 QEMU 提供新 bootrom（固件），用于初始权限/向量配置；bootrom 用自有工具链编。**（用户 2026-10-07 裁定：`-bios` 加载、复位向量不变 `0xffff_ffff_0000`；bootrom hypv→user 直跳、本版不启用 supv）**。
       - **D13** 承载位置：测试机/SEE 规范正文入 `spec/`（非 ADR）；ADR 只记决策。
       - **D14** 共享层适配点：共享层 `common_semi_arg(cs,n)` 假定"同一组 `a0+n`"（RISC-V 实测 `gpr[xA0+argno]`），v5 **三组分离** ⇒ DADAO 钩子**按 `n` 选 bank**（`n=0`→`rd16`、`n=1`→`rb16`）、`common_semi_set_ret`→`rd31`；**小适配（非重写）**。
  2. **`.tao/adr/adr-0004-test-machine.md`（就地修订）**：按 `Process-03` 补充「新 bootrom 与加载模型」的口径修订（`## 修订` 追加条目，标 rev 日期；**不改** D1/D2.1/D3/D4/D5/D6 决策正文，除非用户逐条确认）。
     - **`ADR-0004` 决策提案（R1–R3）**：
       - **R1** 现「路径 A ELF 不用 `-bios`」与「路径 B 双镜像用 `-bios`」须随 M5 新 bootrom 调整——新增/明确「**SEE 启动 = bootrom 固件（初始权限/向量配置）→ 跳应用**」的加载/入口模型（**用户 2026-10-07 裁定**：**用 `-bios`**、**复位向量不变** `0xffff_ffff_0000`；bootrom **hypv→user 直跳、本版不启用 supv**）。**须明确与 M4 ELF 路径（当前不用 `-bios`）的并存/替代关系**（由用户判定）。
       - **R2** `ADR-0004 D3` 的 exit port 与 semihosting `SYS_EXIT` 的关系（**用户 2026-10-07 裁定**）：`SYS_EXIT` **替代** exit-port；**迁移范围 = 全部**。
       - **R3** 段布局/RAM 基址（`0xffff_0000_0000`）/ROM（`0xffff_ffff_0000` 64 KiB）是否因 bootrom 调整。**用户裁定复位向量/ROM 起点不变**；**RAM 基址是否随 bootrom 调整仍属本 ADR 逐条判定项**。
         - **⚠️ R3 显式判定项（`INTEG-019k` 第 2 轮裁定 / `/plan` 关注 5）**：本任务**必须显式向用户提出「RAM 基址是否随 bootrom 调整」并记录判定结论**。**归属：仅判定/记录**——**本 M5 任务清单不承接 RAM 基址调整的实现**；若 R3 判需调整，由本任务**记录结论**并注明**后续另立任务**（不得在本任务内改实现/改链接脚本）。
  3. **`.tao/adr/adr-0016-dadao-install-layout.md`（范围判定，`S1`）**：判定 M5 落地（`INFRA-047t`）是否**沿用** D1–D11，或需调整范围（是否纳入 `manifests/` 定位机制的全部改名点）。**`S1`**：`D1–D11` 已 `Accepted`；`INFRA-047t` **沿用** D1–D11，除非用户裁定调整范围。属**逐条 ADR 判定项**。若仅「沿用、无改动」，记判定结论即可（无需改 ADR 正文）；若有改动，按 `Process-03`（新增/`Superseded`/经授权就地修订）。
- **约束（硬）**：
  - **每个 decision 逐条经用户确认**（`AGENTS.md`「ADR decision 逐条确认」；`spec/Process-03`）：**任务书里列的 decision 只是提案**；**不得**因 `INTEG-019k` 或本任务书写有该决策就默认通过；主会话/子代理**均不得**把未经用户逐条确认的 decision 写为 `Accepted`。用户原话/问答摘要**原样落盘于任务书完成区**（`lessons §7.3`）。
  - **`ADR-0020` 先置 `Candidate`**；仅当 D1–D14 全部经用户判定（保留/修改/否决）、且**无否决未处置**时，方置 `Accepted`。
  - **ADR 不承载规范正文**：ADR 只记决策/理由/被否方案/指向规范章节；SEE/semihosting 调用表等**正文归 `SPEC-114t`**。
  - **R3 判定/记录 + 归属声明**（见上）；**不得**在本任务内改实现或链接脚本。
  - `spec/`/`.tao/adr/` 为共享文件，与其它改 `spec/`/`adr` 的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-113t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **ADR 落位**：`.tao/adr/adr-0020-see-semihosting.md` 存在，含 `Context`/`Decision`（D1–D14）/`Rationale`/`Consequences`/`状态说明`；`**状态**` 为 `Candidate` 或（全部确认后）`Accepted`。
2. **逐条确认记录**：完成区含**用户对 D1–D14 的逐条判定原话/摘要**（保留/修改/否决），无「未确认即 Accepted」；对**被否决/修改**项已处置。
3. **`ADR-0004` 修订**：`adr-0004` 含 `## 修订` rev. 条目（R1/R2 口径），且**未擅自改写已 `Accepted` 的 D1/D2.1/D3/D4/D5/D6**（`git diff` 证据）；用户逐条确认记录落盘。
4. **`ADR-0016` 范围判定**：`S1` 判定结论有据（沿用/调整及其范围），用户确认落盘。
5. **R3 判定/记录**：完成区显式给出「RAM 基址是否随 bootrom 调整」的用户裁定结论，并注明**归属 = 仅判定/记录、实现另立任务**。
6. **门控**：`make check` EXIT=0；给真实输出。
7. **一键证据脚本**：`.work/evidence/SPEC-113t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（删 `## 修订` R1 段/把某 D 项改回旧值 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
8. **无残留**：`git status --untracked-files=all` 仅 `.tao/adr/adr-0004-test-machine.md`（若改）、`.tao/adr/adr-0016-*.md`（若改/新建判定）、`.tao/adr/adr-0020-see-semihosting.md`（新建）+ 本任务书。

## 完成区

**用户逐条确认记录（原话/摘要，2026-10-07+）**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 逐条核 D1–D14/用户确认记录/R3 归属 + 判决）
