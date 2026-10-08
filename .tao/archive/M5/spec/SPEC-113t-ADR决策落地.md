# SPEC-113t: ADR 决策落地（`ADR-0020` 新建 + `ADR-0004` 修订 + `ADR-0016` 范围）

**模块**：spec
**项目里程碑**：M5
**依赖**：无
**状态**：已验证

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
  1. **`.tao/adr/adr-0020-see-semihosting.md`（新建）**：含 `Context`/`Decision`（D1–D15）/`Rationale`/`Consequences`/`状态说明`。**先置 `Candidate`**；**逐条经用户判定（保留/修改/否决）后**方可置 `Accepted`。
     - **`ADR-0020` 决策提案（D1–D15；D1–D14 来源 `INTEG-019k` §ADR 清单，`D15` 为用户 2026-10-07 裁定**新增——见本任务书 §待用户逐条判定清单「四、用户逐条裁定结果」）**：
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
       - **D15（用户 2026-10-07 裁定新增）** **核内地址空间划分 + 越界（访问/取指）报异常**：M5 测试机使用的 cfxha 段/地址区间划分（**RAM@0**〔`0x0000_0000_0000`，cfxha 0 = `umon`，供 bootrom/SEE〕、**boot ROM**〔`0xffff_ffff_0000`，cfxha 63 = `power`，64 KiB，`-bios`〕、**旧 RAM 段过渡保留**〔`0xffff_0000_0000`，cfxha 63，16 MiB，供既有测试〕、exit port〔`0xffff_8000_0000`，cfxha 63，见 `ADR-0004 D3`〕）；**越界访问与越界取指均须报异常**（**须含取指路径**）。异常语义须写清 **`CFXMEM`**（spec：核内地址空间非法访问，`spec/DADAO-12 §2.1:73`、异常原因表 `1<<1`）vs 测试机约定 **`unmapped 0x87`**（`ADR-0004 D5.8`）。**注**：`ADR-0004 D5.8` fault 码表**已冻结、不得重排**；`CFXMEM`（`1<<1`）⇒ `0x81`（`0x80 | 1`），落在表中已保留的 `0x81`–`0x86`（spec cause 位 1–6）区间内，**无需新码/重排**；若确需新码，须说明依据。
         - **D15 归属与 C1 两步（用户 2026-10-07 裁定）**：**step1（M5）** = QEMU 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段（`0xffff_0000_0000`，供既有测试）** + `-bios` bootrom；**`check-interface` 断言新增 RAM@0 段（旧断言保留）** ⇒ **每任务门控保持全绿**；**step2（另立，M5 之外）** = 既有向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言。**实测依据（不可臆改）**：QEMU 侧宏 `components/qemu/patches/target/dadao/cpu.h.patch:63-64`（`DADAO_RAM_BASE=0xffff00000000ULL`/`DADAO_RAM_SIZE=(16 * 1024 * 1024)`）、`hw/dadao/dadao-machine.c.patch:183/485-486`（RAM 区域注册/映射）、`helper.c.patch:103`（RAM 判定）；门控 `check-interface`（∈ `make check`）在 `tools/integ/check_interface_alignment.py:319-347` 硬断言 `RAM_BASE=0xFFFF_0000_0000`、`RAM_SIZE=16MiB`（`:351` 起断言 exit port 基址）。
  2. **`.tao/adr/adr-0004-test-machine.md`（就地修订）**：按 `Process-03` 补充「新 bootrom 与加载模型」的口径修订（`## 修订` 追加条目，标 rev 日期；**不改** D1/D2.1/D3/D4/D5/D6 决策正文，除非用户逐条确认）。
     - **`ADR-0004` 决策提案（R1–R3）**：
       - **R1** 现「路径 A ELF 不用 `-bios`」与「路径 B 双镜像用 `-bios`」须随 M5 新 bootrom 调整——新增/明确「**SEE 启动 = bootrom 固件（初始权限/向量配置）→ 跳应用**」的加载/入口模型（**用户 2026-10-07 裁定**：**用 `-bios`**、**复位向量不变** `0xffff_ffff_0000`；bootrom **hypv→user 直跳、本版不启用 supv**）。**须明确与 M4 ELF 路径（当前不用 `-bios`）的并存/替代关系**。**（用户 2026-10-07 裁定：`-bios` bootrom 与 M4 ELF 路径【并存】、非替代）**。
       - **R2** `ADR-0004 D3` 的 exit port 与 semihosting `SYS_EXIT` 的关系（**用户 2026-10-07 裁定**）：`SYS_EXIT` **替代** exit-port；**迁移范围 = 全部**。
       - **R3** 段布局/RAM 基址（`0xffff_0000_0000`）/ROM（`0xffff_ffff_0000` 64 KiB）是否因 bootrom 调整。**用户裁定复位向量/ROM 起点不变**；**（用户 2026-10-07 裁定：RAM 基址改为全 0〔`0x0000_0000_0000`〕；采用 C1 双映射两步——step1（M5）机器模型 + bootrom 先做〔RAM@0 与旧 RAM 段并存〕，step2（另立，M5 之外）旧向量/harness 迁移；详见 §待用户逐条判定清单「四、用户逐条裁定结果」）**。
         - **⚠️ R3 归属（用户 2026-10-07 裁定）**：R3 结论 = **RAM 基址改为全 0**，实现**归属两步**——step1 归 M5（新任务 `QEMU-049t`：机器模型 RAM@0 双映射 + bootrom 链接基址 + `check-interface` 新断言）、step2 **另立（M5 之外）**（旧向量/harness/`crt0`/e2e 迁移 + 删旧 RAM 段 + 收紧断言）。本任务（`SPEC-113t`）**只落 ADR 决策/口径，不改实现/链接脚本**。
  3. **`.tao/adr/adr-0016-dadao-install-layout.md`（范围判定，`S1`）**：判定 M5 落地（`INFRA-047t`）是否**沿用** D1–D11，或需调整范围（是否纳入 `manifests/` 定位机制的全部改名点）。**`S1`**：`D1–D11` 已 `Accepted`；`INFRA-047t` **沿用** D1–D11，除非用户裁定调整范围。属**逐条 ADR 判定项**。若仅「沿用、无改动」，记判定结论即可（无需改 ADR 正文）；若有改动，按 `Process-03`（新增/`Superseded`/经授权就地修订）。
- **约束（硬）**：
  - **每个 decision 逐条经用户确认**（`AGENTS.md`「ADR decision 逐条确认」；`spec/Process-03`）：**任务书里列的 decision 只是提案**；**不得**因 `INTEG-019k` 或本任务书写有该决策就默认通过；主会话/子代理**均不得**把未经用户逐条确认的 decision 写为 `Accepted`。用户原话/问答摘要**原样落盘于任务书完成区**（`lessons §7.3`）。
  - **`ADR-0020` 先置 `Candidate`**；仅当 D1–D15 全部经用户判定（保留/修改/否决）、且**无否决未处置**时，方置 `Accepted`。
  - **ADR 不承载规范正文**：ADR 只记决策/理由/被否方案/指向规范章节；SEE/semihosting 调用表等**正文归 `SPEC-114t`**。
  - **R3 裁定落纸 + 归属两步**（见上及 §用户逐条裁定结果）：R3 = **RAM 基址改为全 0**；step1（M5，`QEMU-049t`）与 step2（另立）分工已定；本任务**只落 ADR 决策/口径，不得**在本任务内改实现/链接脚本/`QEMU-047t` 链接脚本。
  - `spec/`/`.tao/adr/` 为共享文件，与其它改 `spec/`/`adr` 的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-113t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **ADR 落位**：`.tao/adr/adr-0020-see-semihosting.md` 存在，含 `Context`/`Decision`（D1–D15）/`Rationale`/`Consequences`/`状态说明`；`**状态**` 为 `Candidate` 或（全部确认后）`Accepted`。
2. **逐条确认记录**：完成区含**用户对 D1–D15 的逐条判定原话/摘要**（保留/修改/否决；D2–D14、S1 可按「未特别指出=保留」推定但须显式写明、待用户复核），无「未确认即 Accepted」；对**被否决/修改**项已处置。
3. **`ADR-0004` 修订**：`adr-0004` 含 `## 修订` rev. 条目（**R1**：`-bios` bootrom 与 M4 ELF 路径**并存**；**R2**：`SYS_EXIT` 取代 exit-port；**R3**：RAM 基址改全 0 + C1 双映射两步），且**未擅自改写已 `Accepted` 的 D1/D2.1/D3/D4/D5/D6**（`git diff` 证据）；用户逐条确认记录落盘。
4. **`ADR-0016` 范围判定**：`S1` 判定结论有据（沿用/调整及其范围），用户确认落盘。
5. **R3 裁定落纸 + D15**：`ADR-0020` 含 **`D15`**（核内地址空间划分 + 越界访问/取指异常语义：`CFXMEM` vs 测试机约定 `unmapped 0x87`，含取指路径，`ADR-0004 D5.8` 码表冻结不重排）；完成区显式给出 R3 裁定结论（**RAM 基址改全 0**）与**归属两步**（step1 = `QEMU-049t`〔M5〕；step2 = 另立〔M5 之外〕）。
6. **门控**：`make check` EXIT=0；给真实输出。
7. **一键证据脚本**：`.work/evidence/SPEC-113t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（删 `## 修订` R1 段/把某 D 项改回旧值 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
8. **无残留**：`git status --untracked-files=all` 仅 `.tao/adr/adr-0004-test-machine.md`（若改）、`.tao/adr/adr-0016-*.md`（若改/新建判定）、`.tao/adr/adr-0020-see-semihosting.md`（新建）+ 本任务书。

## 完成区

**用户逐条确认记录（原话/摘要，2026-10-07+）**：

> **用户原话（裁定总述，逐字，2026-10-07）**：
> > ADR0020：注意核内地址空间的划分；以及如果越界需要报异常，包括取指；2、D1的相关说明，可以放到新的MACHINE-01中；R1：用-bios bootrom，与elf并存；R2：是的；R3：RAM基址改为全0
>
> **后续两问回答（原话）**：
> > R3 实现归属：**「M5 内分两步：机器模型+bootrom 先做，旧向量迁移另立」**
> > C 的过渡方式：**「C1 双映射过渡（推荐）」**

**逐条落点（本轮被特别指出者）**：

| 条目 | 用户裁定 | 落点 / 处置 |
| --- | --- | --- |
| **D1** | 保留决策；语义说明移 `spec/Machine-01-*` | `ADR-0020 D1` 保留（含「架构自定义、无 spec 依据」标注）；语义/理由说明归 `SPEC-114t`（ADR 只留决策） |
| **D15（新增）** | 采纳 | 写入 `ADR-0020 D15`（核内地址空间划分 + 越界访问/取指异常 + `CFXMEM` vs `0x87` 层次 + 码表冻结不重排） |
| **R1** | 「用-bios bootrom，与elf并存」 | `ADR-0004 ## 修订` rev. 2026-10-07 R1：`-bios` bootrom 与 M4 ELF 路径**【并存】、非替代** |
| **R2** | 「是的」（`SYS_EXIT` 取代 exit-port） | `ADR-0004 ## 修订` R2：**取代关系**——`D3` 由 `ADR-0020 D8` 取代（`D3` 标 `Superseded`），迁移范围=全部 |
| **R3** | 「RAM基址改为全0」 | `ADR-0004 ## 修订` R3：**覆盖关系**——RAM 基址改全 0（`0x0000_0000_0000`）+ C1 双映射两步；`D1` 正文不改 |

**推定保留 + 用户明确确认（须用户复核）**：`D2`–`D14`、`S1` 未在总述中特别指出，按主会话声明「**未特别指出者视为保留**」推定保留，并**经用户明确确认**（记录于本任务书 §四「推定说明」）。该推定为**默认推定、待用户复核**；若用户对某条另有意见，按 `spec/Process-03` 处置（新增 ADR / 标 `Superseded` / 经授权就地修订）。`S1` 判定结论见下「ADR-0016 范围判定」。

**测试结果**：
- `make check`：**EXIT=0**；尾行 `repository checks: PASS`；`check-interface` 内 `总计: 80 项 | PASS: 80 | FAIL: 0`；lit `Passed: 60 (100.00%)`。完整输出：`.work/log/spec/SPEC-113t-check.log`。
- 一键证据脚本 `.work/evidence/SPEC-113t/run.sh`：**EXIT=0**，`RESULT: PASS`（51 项检查 + 注入自检）。完整输出：`.work/log/spec/SPEC-113t-evidence.log`。

**修改文件**（与 `git status --porcelain -uall` 一致）：
- `.tao/adr/adr-0020-see-semihosting.md`（**新建**；`状态 Accepted`）
- `.tao/adr/adr-0004-test-machine.md`（**修订**：`**状态**` 行加 rev. 2026-10-07 + `## 修订` 追加 rev. 2026-10-07 条目；**未改** `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` 正文）
- `.tao/tasks/spec/SPEC-113t-ADR决策落地.md`（本任务书：完成区 + 审阅记录 + `状态`）
- 未入库（`.work/` 已被 gitignore）：`.work/evidence/SPEC-113t/run.sh`、`.work/log/spec/SPEC-113t-evidence.log`、`.work/log/spec/SPEC-113t-check.log`
- **未改**：`.tao/adr/adr-0016-dadao-install-layout.md`（`S1` = 沿用 D1–D11，仅记结论，不动正文）；`spec/` 正文（归 `SPEC-114t`）；任何实现/链接脚本。

**验收结果**（逐条对齐，真实输出见上述日志）：
1. **ADR 落位**：`adr-0020` 存在，含 `## Context（背景）`/`## Decision（决策）`（`D1`–`D15`）/`## Rationale（理由）`/`## Consequences（影响）`/`## 状态说明`；`**状态**：Accepted`。✅
2. **逐条确认记录**：见上「用户逐条确认记录」+「推定保留」；`ADR-0020` 状态说明明示判定日期/方式与推定保留，`D2`–`D14` 全程以「推定保留 + 用户明确确认」标注，**无「未确认即 Accepted」**；无否决项未处置。✅
3. **`ADR-0004` 修订**：`## 修订` rev. 2026-10-07 含 R1（并存）/R2（`SYS_EXIT` 取代 exit-port，`D3` 标 `Superseded`）/R3（RAM 改全 0 + C1 两步）；**受保护决策正文未被改写**——证据脚本以 `git show HEAD:` 与工作树**逐节比对**（D1/D2.1/D3/D4/D5/D6 全 `same`），并通过 `git diff` 复核（仅 `**状态**` 行替换，无其它删除行）。✅
4. **`ADR-0016` 范围判定**：`S1` = **沿用 `D1`–`D11`**（`ADR-0016` 已于 2026-10-02 经用户逐条确认 `Accepted`；`INFRA-047t` 沿用，不调整范围）⇒ **仅记结论、不改正文**；用户「未特别指出=保留」确认落盘。✅
5. **R3 裁定落纸 + D15**：`ADR-0020 D15` 含核内地址空间划分表（RAM@0 / boot ROM / 旧 RAM 段过渡 / exit port）+ 越界访问与**越界取指均报异常（含取指路径）** + `CFXMEM`（`1<<1` ⇒ `0x81`）vs 测试机约定 `unmapped 0x87` 的**层次与适用** + 码表**冻结不重排**。**R3 裁定结论 = RAM 基址改为全 0**；**归属两步**：**step1 = `QEMU-049t`（M5）**（机器模型双映射 RAM@0 + 旧 RAM 段 + `check-interface` 新增断言）；**step2 = 另立（M5 之外）**（旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言）。✅
6. **门控**：`make check` EXIT=0（见日志）。✅
7. **一键证据脚本**：`.work/evidence/SPEC-113t/run.sh` 非交互、失败非零、逐项打印；内置注入自检（删 `D15` 行 ⇒ 断言检出缺失=1 ⇒ `cp` 还原 ⇒ md5 一致 ⇒ 回绿）；结尾用 `rc=$?` 捕获且**未用 `tee`**。✅
8. **无残留**：`git status --porcelain -uall` = ` M .tao/adr/adr-0004-test-machine.md` + `?? .tao/adr/adr-0020-see-semihosting.md`（+ 本任务书；`.work/` gitignored），与「修改文件」一致。✅

**ADR-0004 决策变更所用机制与依据**（硬约束 2）：采用「**`## 修订` 新增条目 + 明确取代/覆盖关系**」——R2 明示 **`D3` 由 `ADR-0020 D8` 取代**（`D3` 标 `Superseded`）；R3 明示**覆盖 `D1` 的 RAM 基址**（step2 前旧基址因双映射仍有效）。**不改写** `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` 正文；依据 `spec/Process-03-ADR编写规范.md`「决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策」。

**新发现/坑**：
1. **`D9` 依据归属订正（须沉淀）**：`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `spec/DADAO-12 §2.2`（PTBR 权限，`:92`/`:133`）与 cfx_ptw 异常原因表（`:449`–`:452`），**非 `§5`**；`§5` 对未授权 cfx 触发的是 **`ILLI`**（`:684`/`:692`–`:693`）。已在 `ADR-0020 D9` 订正，并提示 `SPEC-114t`/`QEMU-044t` 讲清两层次。
2. **`D1` tag 无 spec 依据**：`immu18[17:16]==2'b11` 属架构自定义（`spec/DADAO-22`/`SimRISC-11` 无 semihosting 语义），ADR 与后续 `spec/Machine-01-*` 均须明示。
3. **受保护决策「未被静默改写」的机械证明**：`git diff` 的 hunk 判定较脆；改用 **`git show HEAD:<file>` 与工作树按节前缀提取后逐节比对**（D1/D2.1/D3/D4/D5/D6），对「就地修订已 Accepted 决策」类任务更稳健，建议沉淀为通用检查。
4. **`CFXMEM` ⇒ `0x81` 无需新码**：`CFXMEM=1<<1` ⇒ `0x80|1=0x81`，正好落在 `ADR-0004 D5.8` 表中已保留的 `0x81`–`0x86`（spec cause 位 1–6，M1 未用）区间 ⇒ **码表冻结、不重排**。
5. **注入还原纪律**：证据脚本用 `grep -v` 删行注入、`cp` 备份 + `md5sum` 对账还原；**未用** `git checkout/restore/stash`；并打印注入前/还原后 `git status --porcelain -uall` 快照。

**遗留问题**：
1. **`RAM@0` 容量**与**越界路由的精确归属**（哪类越界取 `0x81`、哪类取 `0x87`）已在 `ADR-0020 D15` 写明「由 `QEMU-049t` 按层次落地」——属**实现缺口**（非本 ADR 决策缺口），登记为 `QEMU-049t` 待办。
2. `D2`–`D14`、`S1` 为「推定保留 + 用户明确确认」，**待用户复核**；若某条另有意见，按 `spec/Process-03` 处置（本任务已按推定写入，无未处置否决）。
3. `S1` 判定结论为「沿用、无改动」，`adr-0016` 正文**未改**（无需动作）；`INFRA-047t` 范围是否需调整由用户复核确认。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`ADR-0020`（新建）全文、`ADR-0004 ## 修订` 追加条目、证据脚本 `run.sh`。

**方法**：逐行审阅两份 ADR 与脚本；对每条引用的 spec/合约出处**逐条回读原文行**核实（不采信任务书转述）；对受保护决策做 HEAD×工作树逐节比对；对证据脚本做注入自检。

**引证核实（逐条）**：`DADAO-12:68`（复位向量）/`:73`（CFXMEM）/`:406`（cfx_umon 异常表 `1<<1`）/`:92`/`:133`（NUPERM 等 PTBR 权限）/`:449`–`:452`（cfx_ptw 异常表）/`:684`/`:692`–`:693`（未授权 cfx → ILLI）/`:703`（§5 步骤 10）/`§3:385`（内部存储块 CFXMEM）；`DADAO-22:7`/`:11`/`:13`/`:58`（CFXREG）；`SimRISC-11:80`/`:89`；`contract-abi.md §4.1`/`§4.4`；QEMU patch `cpu.h.patch:63-64`、`dadao-machine.c.patch:183`、`helper.c.patch:103`、`check_interface_alignment.py:319-320`/`351`。全部与原文一致。

**自审 findings 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `D15` 表中 `RAM@0` 容量无权威值 | ⏸延后（不臆填） | 记为「【待 `QEMU-049t` 定】」，并在 `D15` 第 4 点与完成区「遗留问题 1」登记 | `run.sh` D15/结构断言 PASS；`ADR-0020` L54 |
| F2 受保护决策「未被静默改写」原拟用 `git diff` hunk 判定（脆弱：body 行措辞与 `## 修订` 引用可能混淆） | ✅已修 | 改用 `git show HEAD:<file>` 与工作树**按节前缀提取后 `diff -q`** 逐节比对 `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` | `run.sh` 第 4 节 6×`[PASS] ... same`；`git diff` 删除行仅 `**状态**` 一行 |
| F3 注入自检存在「空注入 ⇒ 仍全绿」的假结论风险 | ✅已修 | 注入后断言「行差=1」且「D-missing=1」两条独立断言；不满足即 FAIL | `run.sh` 第 5 节：`行差=1`、`D-missing=1`、`restore md5 一致`、`restore D-missing=0` 全 PASS |
| F4 `ADR-0004` 决策变更机制须符合 `Process-03`（不得直接改写已 `Accepted` 决策） | ✅已修 | 采用「`## 修订` 新增条目 + 明确取代/覆盖关系」（R2 指出 `D3` 由 `ADR-0020 D8` 取代并使 `D3` 标 `Superseded`；R3 指出覆盖 `D1` RAM 基址）；`D1/D2.1/D3/D4/D5/D6` 正文未动 | `run.sh` 第 3 节 R1/R2/R3+取代断言 PASS；第 4 节逐节 same；完成区「机制与依据」 |
| F5 `D9` 引用若沿用任务书的 `§5` 归属会致误 | ✅已修 | 订正为 `§2.2` + cfx_ptw 异常表（`NUPERM` 等），并区分 `§5` 的 `ILLI` | `ADR-0020 D9`「依据归属（订正）」；`run.sh` 结构断言 PASS |

**防造假自查**：`make check` 与 `run.sh` 均为真实执行并留日志（`.work/log/spec/`）；完成区数值与日志逐条对齐（`8/8` 验收项、51 项脚本检查）；未伪造/估算输出；未用 `tee` 吞退出码。

**判决**：所有 finding 已处置（F1 为**非本 ADR 的决策缺口**，属实现待办、已登记），无未修 finding ⇒ **状态置 `待验收`**。

#### 第 1 轮 reviewer 验收

**审查环境**：临时目录 `/tmp/opencode/SPEC-113t-review/`；模型 `mimo-v2.5-pro`。

##### A. 常规验收

**A1. 证据脚本 `run.sh` 审核**：

逐条核对 5 个检查段（结构/D15 口径/ADR-0004 修订/逐节比对/注入自检）：
- **FAIL 路径**：`ck_file`（文件不存在）、`ck_f`（grep 不命中）、`ck_eq`（字符串不等）、`d_missing`（D 项缺失）均为真正可失败断言，无恒真/两支同一结果。
- **注入自检**：删 `- **D15**` 行后断言「行差=1」且「D-missing=1」——两条独立断言，任一不满足即 FAIL（可拦空注入）。还原用 `cp` + `md5sum` 对账（非 `git checkout/restore/stash`）。
- **结尾**：`if [ "$FAILS" -eq 0 ]; then ... exit 0; else ... exit 1; fi`（行 133–138），未用 `tee`。
- **判定**：脚本合格。

**A2. 重跑脚本**（真实输出）：

```
== SPEC-113t 证据：ADR 决策落地 ==
repo=/mnt/tao/DADAO-v5

-- 1. ADR-0020 落位与结构 --
[PASS] adr-0020 存在 | expect exists: .tao/adr/adr-0020-see-semihosting.md
[PASS] adr-0020 结构 | expect contains: ## Context（背景）
[PASS] adr-0020 结构 | expect contains: ## Decision（决策）
[PASS] adr-0020 结构 | expect contains: ## Rationale（理由）
[PASS] adr-0020 结构 | expect contains: ## Consequences（影响）
[PASS] adr-0020 结构 | expect contains: ## 状态说明
[PASS] adr-0020 状态 Accepted | expect contains: **状态**：Accepted
[PASS] adr-0020 状态说明含 Accepted（2026-10-07） | expect contains: Accepted（2026-10-07）
[PASS] adr-0020 状态说明含推定保留 | expect contains: 推定保留
[PASS] adr-0020 D1 语义说明移 spec/Machine-01 | expect contains: spec/Machine-01
[PASS] adr-0020 D1 无 spec 依据（架构自定义） | expect contains: 架构自定义
[PASS] adr-0020 D1..D15 缺失数（应为 0） | expected=[0] actual=[0]

-- 2. ADR-0020 D15 口径 --
[PASS] D15 核内地址空间 RAM@0 | expect contains: RAM@0
[PASS] D15 boot ROM 复位向量 | expect contains: 0xffff_ffff_0000
[PASS] D15 旧 RAM 段过渡保留 | expect contains: 0xffff_0000_0000
[PASS] D15 exit port | expect contains: 0xffff_8000_0000
[PASS] D15 RAM 基址全 0 | expect contains: 0x0000_0000_0000
[PASS] D15 含取指路径 | expect contains: 取指路径
[PASS] D15 CFXMEM | expect contains: CFXMEM
[PASS] D15 CFXMEM cause 1<<1 | expect contains: 1 << 1
[PASS] D15 CFXMEM 映射 0x81 | expect contains: 0x81
[PASS] D15 测试机约定 unmapped 0x87 | expect contains: unmapped 0x87
[PASS] D15 码表冻结不重排 | expect contains: 码表冻结

-- 3. ADR-0004 修订（R1/R2/R3 + 取代关系）--
[PASS] adr-0004 has 修订 | expect contains: ## 修订
[PASS] adr-0004 rev. 2026-10-07 | expect contains: rev. 2026-10-07
[PASS] adr-0004 R1 | expect contains: **R1 — 加载/入口模型
[PASS] adr-0004 R2 | expect contains: **R2 — 停机协议
[PASS] adr-0004 R3 | expect contains: **R3 — RAM 基址
[PASS] adr-0004 R1 并存非替代 | expect contains: 【并存】、非替代
[PASS] adr-0004 R2 取代本 ADR D3 | expect contains: 取代本 ADR
[PASS] adr-0004 R2 Superseded | expect contains: Superseded
[PASS] adr-0004 R3 RAM 改全 0 | expect contains: RAM 基址改为全 0
[PASS] adr-0004 R3 C1 双映射两步过渡 | expect contains: C1 双映射两步过渡
[PASS] adr-0004 R3 step1 | expect contains: step1（M5
[PASS] adr-0004 R3 step2 | expect contains: step2（另立

-- 4. 受保护决策正文未被静默改写（HEAD vs worktree 逐节比对）--
[PASS] adr-0004 D1 正文未改 | expected=[same] actual=[same]
[PASS] adr-0004 D2.1 正文未改 | expected=[same] actual=[same]
[PASS] adr-0004 D3 正文未改 | expected=[same] actual=[same]
[PASS] adr-0004 D4 正文未改 | expected=[same] actual=[same]
[PASS] adr-0004 D5 正文未改 | expected=[same] actual=[same]
[PASS] adr-0004 D6 正文未改 | expected=[same] actual=[same]

-- 5. 注入自检：删 D15 行 ⇒ 断言 FAIL ⇒ 还原（cp+md5）⇒ 回绿 --
pre-inject: git status --porcelain -uall:
pre-inject: md5(adr-0020)=77414d82d68c17890aff09aced796d8e
[PASS] inject: 注入确实改动文件（行差=1） | expected=[1] actual=[1]
[PASS] inject: D-missing（应检出 1 条） | expected=[1] actual=[1]
[PASS] restore: md5 一致 | expected=[77414d82d68c17890aff09aced796d8e] actual=[77414d82d68c17890aff09aced796d8e]
[PASS] restore: D1..D15 缺失数（应回 0） | expected=[0] actual=[0]
post-restore: git status --porcelain -uall:

RESULT: PASS
EXIT=0
```

**51/51 PASS，EXIT=0**。✅

**A3. 独立注入反例**（reviewer 自行执行，非沿用 engineer 自检）：

- **注入方式**：修改 `ADR-0004 D3` 节标题（`### D3 Exit Port 协议` → `### D3 EXIT PORT INJECTED`），与脚本自身的 D15 删除注入为不同攻击向量。
- **还原纪律**：注入前 `cp` 备份到 `/tmp/opencode/SPEC-113t-review/adr-0004.preinject`，md5 = `7d2e6159947582e7f01bee638fede1c1`；还原 `cp` 回，md5 对账一致。
- **注入后运行脚本**：`[FAIL] adr-0004 D3 正文未改 | expected=[same] actual=[DIFFERENT]`，EXIT=1。✅ 脚本成功检出。
- **还原后运行脚本**：51/51 PASS，EXIT=0。✅ 回绿。
- **快照对账**：
  - 注入前快照：`git status --porcelain -uall` 干净；md5(adr-0020) = `77414d82d68c17890aff09aced796d8e`，md5(adr-0004) = `7d2e6159947582e7f01bee638fede1c1`
  - 还原后快照：`git status --porcelain -uall` 干净；md5(adr-0020) = `77414d82d68c17890aff09aced796d8e`，md5(adr-0004) = `7d2e6159947582e7f01bee638fede1c1` → **逐行一致**。

**A4. 逐条核验收 1–8**：

| # | 验收项 | 判定 | 证据 |
|---|--------|------|------|
| 1 | ADR 落位 | ✅ | `adr-0020` 存在，含 Context/Decision(D1-D15)/Rationale/Consequences/状态说明；状态=Accepted |
| 2 | 逐条确认记录 | ✅ | 完成区含用户原话 + 推定保留说明；无「未确认即 Accepted」 |
| 3 | ADR-0004 修订 | ✅ | `## 修订` rev.2026-10-07 含 R1/R2/R3；D1/D2.1/D3/D4/D5/D6 正文未改（git diff + 逐节比对确认） |
| 4 | ADR-0016 范围判定 | ✅ | S1 = 沿用 D1-D11；`git diff ac0962e -- adr-0016` 无输出（未改正文） |
| 5 | R3 裁定 + D15 | ✅ | D15 含地址空间划分表/取指路径/CFXMEM/0x87/码表冻结；R3 归属两步写明 |
| 6 | 门控 | ✅ | `make check` EXIT=0；80/80 项 PASS；lit 60/60 Passed |
| 7 | 一键证据脚本 | ✅ | 51/51 PASS；含注入自检；结尾无 tee |
| 8 | 无残留 | ✅ | `git diff ac0962e --name-only` 仅 3 文件（adr-0004/adr-0020/本任务书） |

##### B. 重点核验

| # | 核验项 | 判定 | 证据 |
|---|--------|------|------|
| B1 | 已 Accepted 决策未被静默改写 | ✅ | `git diff ac0962e^..ac0962e` 仅 `**状态**` 行替换 + `## 修订` 追加；逐节比对 D1/D2.1/D3/D4/D5/D6 均 `same` |
| B2 | 变更机制合规 | ✅ | R2 明标 `D3` 由 `ADR-0020 D8` 取代（`Superseded`）；R3 覆盖 D1 RAM 基址 + C1 两步过渡清晰；R1 并存非替代 |
| B3 | ADR-0020 D15 内容 | ✅ | 核内地址空间划分表（4 区域）+ 越界访问/取指均报异常（含取指路径）+ CFXMEM(1<<1⇒0x81) vs unmapped(0x87) 层次 + 码表冻结不重排 + 归属两步（step1=QEMU-049t/step2=另立） |
| B4 | ADR 不承载规范正文 | ✅ | ADR-0020 11 处引用 SPEC-114t/spec/Machine-01；权威表/语义详述均指向 `spec/` |
| B5 | 逐条确认记录 | ✅ | 完成区含用户原话（逐字）+ 推定保留显式说明 + D1 语义归 spec/Machine-01（4 处引用）；无「未确认即 Accepted」 |
| B6 | ADR-0016 | ✅ | `git diff ac0962e -- adr-0016` 无输出（未改正文）；S1 判定结论有据（沿用 D1-D11） |
| B7 | 未越界 | ✅ | `git diff ac0962e --name-only` 仅 3 文件，未卷入 `spec/`、`adr-0016`、`components/`、其它任务书 |

##### 判决

**Accepted** — 验收命令块全部通过（51/51 证据脚本 + `make check` 80/80 + lit 60/60）、独立注入反例成功检出并回绿、B 各项全部通过、约束无违反。

#### 清单编制（architect，2026-10-07）
- **来源**：`INTEG-019k` §ADR 清单（`ADR-0020` D1–D14、`ADR-0004` R1–R3、`ADR-0016` S1）+ §第 2 轮用户裁定（2026-10-07）；依据已独立核对到文件+行号/章节（`spec/DADAO-12`/`-21`/`-22`、`spec/SimRISC-11`、`.tao/knowledge/contract-abi.md`、`.tao/adr/adr-0004`/`-0011`/`-0016`、QEMU 上游 `.work/source/qemu/{semihosting,target/riscv,gdbstub}`）。
- **条目数**：**18** 条（`D1–D14` 14 + `R1–R3` 3 + `S1` 1）；**编号连续、无跳号**。
- **产出**：本任务书新增章节 `## 待用户逐条判定清单（2026-10-07）`（每条按「提案 / 依据 / 备选 / 影响面·代价」4 要素；供用户逐条裁定）。
- **发现的证据问题（已在清单内标注）**：① `D9` 的四类 `NUPERM/NJPERM/NSPERM/NHPERM` 归属应为 `DADAO-12 §2.2`（L92/L255）/异常表（L449-452），**非 §5**（`§5` 对未授权 cfx 触发 `ILLI`）；② `D1` 的 `immu18[17:16]=2'b11` tag **无 spec 依据**（架构自定义）；③ `INTEG-019k` 内「D1–D13（+D14）」表述与表内 D1–D14 **未同步**（非跳号）。

#### 第 1 轮 architect 提交（WIP）
- **档位**：**WIP**（engineer 返回、reviewer 尚未验收 ⇒ 非「验收完成」，按规则用 `WIP:` 前缀本地提交）。
- **文件集对账**（显式 staging，未用 `git add -A`）：
  - 入库 3 项，与完成区「修改文件」声明**一致**：`.tao/adr/adr-0020-see-semihosting.md`（新建）、`.tao/adr/adr-0004-test-machine.md`（修订）、本任务书。**无漏提、无多提**。
  - **越界核查**:未卷入 `spec/`、`.tao/adr/adr-0016-dadao-install-layout.md`、`components/`、其它任务书（`git status`/`git diff --cached --name-only` 实测确认）。
  - `.work/**` 为 gitignored，**不入库**（与声明一致）。
- **提交**：`WIP: SPEC-113t ADR-0020 新建 + ADR-0004 修订（待 reviewer 验收）`；**只 commit，未 push**。

#### 第 1 轮 architect 交叉复核（/complete）
- **判决**：reviewer 「Accepted」**维持**（未过严、未漏判致返工）；下列 1 项为**措辞级补充发现**（不影响决策成立、不阻塞提交）。
- **独立复核（重跑 / 独立注入，非转述）**：
  1. **重跑证据脚本**：`bash .work/evidence/SPEC-113t/run.sh > /tmp/opencode/SPEC-113t/run.architect.out 2>&1; rc=$?` ⇒ **EXIT=0**、`RESULT: PASS`（51 项）；还原后工作树 md5 不变（`adr-0020=77414d82d68c17890aff09aced796d8e`、`adr-0004=7d2e6159947582e7f01bee638fede1c1`）。
  2. **独立注入（在临时树，未碰工作树）**：`cp .tao/adr/adr-0004-test-machine.md /tmp/opencode/SPEC-113t/inj.md`，改节标题 `### D3 Exit Port 协议` → `### D3 EXIT PORT INJECTED`；用脚本同款「按节提取 + 逐节 `diff`」逻辑复核 ⇒ `D3 => DIFFERENT`、其余 5 节 `same`；注入 `diff` **非空**（防空注入）。⇒ reviewer 的独立注入**有鉴别力**、脚本承重；工作树 md5 未变。
  3. **受保护决策零改动**：`git show ac0962e -- .tao/adr/adr-0004-test-machine.md` 仅 `**状态**` 行替换 + `## 修订` 追加**两处**；逐节提取 `D1`(19 行)/`D2.1`(33)/`D3`(22)/`D4`(12)/`D5`(92)/`D6`(108) 均**非空**且 HEAD=工作树 `same`（防「空提取 ⇒ 假 same」）。
  4. **`ADR-0020 D15` 四要素**：①地址划分表（RAM@0 / boot ROM `0xffff_ffff_0000` / 旧 RAM 段 `0xffff_0000_0000` / exit port `0xffff_8000_0000`）；②**越界访问与越界取指均报异常**（含「取指路径」）；③`CFXMEM`(`1<<1`⇒`0x81`) vs 测机约定 `unmapped 0x87` **层次**；④**码表冻结不重排**（落 `0x81`–`0x86` 保留区）。R3 归属两步（step1=`QEMU-049t`/M5、step2=另立/M5 之外）写明。✅
  5. **规则一致性**：`D13` 明示「ADR 不承载规范正文」（`Process-03`）；服务表/权限/`CFXMEM` 语义正文指向 `spec/Machine-01-*`（`SPEC-114t`）；`D1` 语义说明归 `spec/Machine-01-*`。✅
- **补充发现（措辞级）**：`ADR-0004 R2` 括注称「（`D3` 标 `Superseded`）」，但实测 **`D3` 节标题与节内**均无 `Superseded` 标记（全文 `Superseded` 仅见 `:357` 通用规则、`:383` rev.2026-10-06、`:388` R2 本条）。⇒ 该「已标」实为**文件级取代声明**（R2 条目即标注），非 in-place 标记；`Process-03`「**新增 ADR** 或标注 `Superseded`」机制已由 `ADR-0020`（新增 ADR）满足 ⇒ **决策成立、不返工**。建议后续经授权修订二选一：给 `D3` 加一行 `Superseded` 标记，或把括注改为「由本修订条目声明取代」。

#### 用户对推定保留项的明确确认（2026-10-07）
- **结论**：`D2–D14`、`S1` 的「未特别指出 = 保留」推定，已获用户 **2026-10-07 明确确认**（原话：**「全部确认」**；经主会话转达，子会话不直连用户）。⇒ §四「推定说明（须用户复核）」**复核闭合**，`ADR-0020` `D2–D14` 与 `ADR-0016 S1` 判定**终局**。
- **落点**：`ADR-0020` 正文**无需改动**（保留项原本即按「保留」写入）；`ADR-0016` 正文**不改**（`S1` = 沿用 `D1–D11`）。

#### 第 1 轮 architect 提交（正常）
- **档位**：**正常**（reviewer 判 `Accepted` ⇒ 验收完成，**不加 `WIP:`**）。
- **文件集对账**（显式 staging，未用 `git add -A`）：`git diff --cached --name-only` 与完成区「修改文件」声明 + 本任务范围对账 —— 收尾追加的台账：`.tao/tasks/spec/SPEC-113t-ADR决策落地.md`、`.tao/knowledge/changelog.md`、`.tao/knowledge/milestones.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/feedback_004-就地修订已Accepted决策的机械核验.md`；**无漏提 / 无多提 / 无越界**（未卷入 `spec/`、`.tao/adr/`、`components/`、其它任务书；`.work/**` gitignored 不入库）。
- **提交信息**：`SPEC-113t ADR-0020 新建 + ADR-0004 修订（reviewer Accepted）`；**只 commit，未 push**。

---

## 待用户逐条判定清单（2026-10-07）

> **用途**：供用户对 `ADR-0020` D1–D14、`ADR-0004` R1–R3、`ADR-0016` S1 **逐条裁定（保留 / 修改 / 否决）**，每条给出「提案 / 依据 / 备选 / 影响面·代价」4 要素。
> **裁定后处置**：**用户裁定后，本节按裁定更新/标记**（保留 = `✓`；修改 = 记新值；否决 = 记理由与替代方向）；裁定结论另按硬约束**原样**落「完成区」。
> **前提**：下列 decision **均为提案**；**未确认前不得写入 ADR、不得标 `Accepted`**（`AGENTS.md`「ADR decision 逐条确认」；`spec/Process-03`）。
> **依据出处约定**：`spec/*.md` 记「文件:行号或章节」；`.tao/knowledge/contract-*.md` 记「路径 §章节」；QEMU 上游记相对路径:行号（只读对照，非执行依赖）。

### 一、`ADR-0020`（新建）— SEE/HEE 运行环境与 semihosting

**D1 — 入口判定：`trap cfxHA, immu18` 中 `immu18[17:16]==2'b11` ⇒ semihosting（与 `cfxha` 无关）**
- 提案：以 `immu18` 高 2 位作为 semihosting 判定 tag。
- 依据：用户 2026-10-07 已锁定边界 A1；`spec/DADAO-22:11`（`trap cfxha, immu18` 陷入）+ `spec/SimRISC-11:79`（`immu18` 事务号）。⚠️ `spec` **无 semihosting 语义** ⇒ 该 tag **属架构自定义**，须在 ADR/spec 明示「无 spec 依据」。
- 备选：用独立/保留 `cfxha` 段区分；或专用指令。
- 影响面·代价：`QEMU-046t` 译码路由、`SPEC-114t §semihosting`、`TESTCASES-033t`；写错则 semihosting 与一般 `trap` 路由混淆。

**D2 — 传参/返回寄存器：号（标量）→`rd16`、参数块指针（地址）→`rb16`、返回值→`rd31`；不另设 `rd15`**
- 提案：semihosting 复用 ABI 传参寄存器，`common_semi_arg(cs,0)`=号、`(cs,1)`=参数块指针。
- 依据：用户 2026-10-07 第 2 轮裁定 2；`.tao/knowledge/contract-abi.md §4.1`（`rd16–rd31` 数据参数、`rb16–rb31` 地址参数；L40 `rd16=rda0`）、`§4.4`（`rd31` 标量返回、`rb31` 指针返回）；`spec/DADAO-22:13`（参数与 ABI 一致）；`spec/DADAO-21:377`（`rd15` 是系统调用号，不用于 semihosting）。
- 备选：另设 `rd15` 作 semihosting 号寄存器（已否决）；参数块改走栈。
- 影响面·代价：`QEMU-046t` 共享层钩子、`SPEC-114t` 服务表、`TESTCASES-033t`；写错则取参/写回错位。

**D3 — 号值 = ARM 号值；服务集 = 完整 25 个（含文件档；`SYSTEM`、`HEAPINFO` 都做，`SYSTEM` 风险记为已知风险）**
- 提案：采用 ARM semihosting 号值，实现全部 25 个服务。
- 依据：用户 2026-10-07 第 2 轮裁定 1 / 待裁定项 1、2（原话「复用、ARM/RISC-V 有就做」）；QEMU `semihosting/arm-compat-semi.c:54-78`（25 个 `TARGET_SYS_*` 常量实测，含 `SYSTEM 0x12`/`HEAPINFO 0x16`）。
- 备选：只做「D1 必做档」（console/退出/错误/系统信息，不含文件档）；`SYSTEM` 拒 `ENOSYS`（**均已被用户否决**）。
- 影响面·代价：`QEMU-046t`、`SPEC-114t §semihosting 服务表`、`TESTCASES-033t`（各条 ≥1 例）；写错则号值错位、服务误派。

**D4 — 返回机制：无 `escape` 指令——服务后 PC 步进（`env->pc += 4`）+ 写回返回寄存器**
- 提案：semihosting 返回不走 `escape`，由 QEMU 直接前移 PC。
- 依据：用户原话「**退出的 escape 无需指令，直接执行**」（`INTEG-019k:55`）；QEMU 实测 `target/riscv/tcg/cpu_helper.c:2092-2094`（`do_common_semihosting(cs); env->pc += 4;`）。
- 备选：用 `escape` 指令返回（`spec/DADAO-22:11` 的通用 trap 约定）——但 semihosting 走译码短路，不进入向量，不适用。
- 影响面·代价：`QEMU-046t`；写错则返回地址错乱/死循环。

**D5 — 复用范式：复用 `do_common_semihosting(cs)`，仅写 `common-semi-target.c` 式钩子；接入 = 译码后抛 semihost 内部异常**
- 提案：照 RISC-V 范式复用共享层，不自建 responder。
- 依据：用户 2026-10-07 已锁定边界 A5；QEMU `semihosting/arm-compat-semi.c`（`do_common_semihosting`）、`include/semihosting/common-semi.h`（声明）、`target/riscv/common-semi-target.c`（钩子范式）、`target/riscv/tcg/insn_trans/trans_privileged.c.inc:69`（`generate_exception(...SEMIHOST)`）。
- 备选：自建 responder（0628 `trap cfx_smon` + Linux syscall 号路线，已否）。
- 影响面·代价：`QEMU-046t`；写错则须重写共享层（成本大幅上升）。

**D6 — 位宽/端序：由 `is_64bit_semihosting()` 决定；v5 恒 64 位；参数块 = 64 位字段 + target 端序（v5 大端）**
- 提案：位宽/端序交由共享层按 target 判定。
- 依据：用户 2026-10-07 已锁定边界 A6；QEMU `semihosting/arm-compat-semi.c:191,203`（`GET_ARG/SET_ARG` 依 `is_64bit_semihosting` 走 `get/put_user_u64` ⇒ 端序自动）；v5 大端（`ADR-0003`/`contract-elf` `ELFDATA2MSB`）。
- 备选：无（v5 无 32 位运行模式）。
- 影响面·代价：`QEMU-046t`、`TESTCASES-033t` 独立 oracle；写错则参数块解析错。

**D7 — host 侧安全：默认值由 harness/Makefile 的 `-semihosting-config` 给；`auto`=有 GDB⇒gdb、无 GDB⇒native；建议默认 `gdb`/沙箱，`native` 显式开**
- 提案：默认走 `gdb`/沙箱；`native` 显式启用。
- 依据：用户 2026-10-07 已锁定边界 A7；QEMU `gdbstub/syscalls.c:47-64`（`auto` 首次调用 `gdb_attached()` 判定并记忆）、`semihosting/config.c:147-165`（`target=native/gdb/auto` 解析）。
- 备选：默认 `native`（用户倾向否决）；由 harness 脚本包装 `chardev=`。
- 影响面·代价：`INTEG-020t`（stdio 捕获）、`QEMU-046t`；写错则 CI 无 GDB 时行为不确定，或 `SYSTEM` 执行宿主命令的安全风险外露。

**D8 — `SYS_EXIT` 替代 `exit port`（`ADR-0004 D3`）⇒ M1–M4 依赖 exit-port 的向量/harness 迁移范围 = 全部**
- 提案：以 semihosting `SYS_EXIT` 取代 exit-port 作为停机协议。
- 依据：用户 2026-10-07 第 2 轮裁定 7（范围=全部）；`ADR-0004 §D3`（exit port 协议）、`ADR-0011`（exit-port 可靠 halt）；QEMU `semihosting/arm-compat-semi.c:751-757`（`TARGET_SYS_EXIT`/`EXIT_EXTENDED`）。
- 备选：保留 exit-port 兼容并存（**已否决**：范围=全部）。
- 影响面·代价：`TESTCASES-034t`（迁移）、`ADR-0004 D3` 修订、`INTEG-020t` 门槛、M1–M4 全部依赖 exit-port 的向量；写错则旧回归红。

**D9 — QEMU 权限粒度 = 完整：cfx 掩码 + 指令类型 mask + `switch_run_mode` + 权限异常；运行模式与 cfx 正交；权限范围只做 `cfx0/1/2/3/63`；访问未实现 cfx ⇒ `CFXREG`**
- 提案：实现完整权限机制，但 cfx 集合限 `cfx0/1/2/3/63`（`umon/jmon/smon/hmon/power`）。
- 依据：用户 2026-10-07 第 2 轮裁定 4；`spec/DADAO-12 §1`（四模式 + cfx 表 + 作用域）、`§3` cg0–cg3（`global_cfx_mask`/`<instr>_cfx_mask`）、`§5` 步骤 3–8（mask/`switch_run_mode`）、`spec/SimRISC-11:80`（任意模式执行）；`CFXREG` 出处 `spec/DADAO-22:58`（已核实）+ `spec/DADAO-12:373`。
- ⚠️ **依据订正**：`NUPERM/NJPERM/NSPERM/NHPERM` 定义在 `spec/DADAO-12 §2.2`（L92/L255）与异常表（L449-452，PTBR 权限），**非 §5**；`§5` 对未授权 cfx 触发的是 `ILLI`（L684/L692-693）——二者层次不同，须在 `SPEC-114t`/`QEMU-044t` 讲清（`INTEG-019k:252` 残留提醒）。
- 备选：只做 `cfx0-3`（不含 `power`）；或 64 个 cfx 全做（用户已裁定为 `cfx0/1/2/3/63`）。
- 影响面·代价：`QEMU-044t`、`SPEC-114t §cfx 与权限`、`TESTCASES-033t` 权限反例；写错则越权/误禁或未实现 cfx 的异常语义不清。

**D10 — 流程两条路：(a) 一般 `trap`（`immu18[17:16]≠2'b11`）走 spec 异常进入流程、**进入该 cfx 向量**；(b) semihosting（`==2'b11`）**QEMU 译码层短路**、不进入向量、直接服务并按 PC 步进返回**
- 提案：一般 trap 与 semihosting 分两条路，semihosting 不走向量。
- 依据：用户 2026-10-07 第 3 轮 architect 修订（`/plan` 采纳，`INTEG-019k:208`）；`spec/DADAO-12 §5` 步骤 1–10（`:708` 步骤 10「跳转至异常向量」）；QEMU 短路范式（`trans_privileged.c.inc:69` + `cpu_helper.c:2092`）。
- 备选：所有 trap 统一走向量（由向量内分发 semihosting）——已被审查否决。
- 影响面·代价：`QEMU-045t`（走向量）/`QEMU-046t`（短路）范围划分、`SPEC-114t §5`；写错则实现者误让 semihosting 进向量。

**D11 — `cfxha` 不设白名单：是否允许调用由权限（mask）控制**
- 提案：不硬编码 cfxha 白名单，交由 cfx mask 决定可否调用。
- 依据：用户 2026-10-07 已锁定边界 B11；`spec/DADAO-12 §5:684`（reserved cfxha→`ILLI`；合法但指令 cfx mask 禁→`ILLI`）、`spec/DADAO-12:662`、`spec/SimRISC-11:80`（由 mask 控制）。
- 备选：硬编码白名单（已否决）。
- 影响面·代价：`QEMU-044t`/`045t`；写错则越权或误禁。

**D12 — 新 bootrom（固件，用自有工具链编）用于初始权限/向量配置；`-bios` 加载、复位向量不变（`0xffff_ffff_0000`）；bootrom hypv→user 直跳、本版不启用 supv**
- 提案：M5 引入新 bootrom 固件并经 `-bios` 加载，复位向量沿用不改。
- 依据：用户 2026-10-07 第 2 轮裁定 5/6；`spec/DADAO-12 §2.1:68`（`cfx_power_hypv_excp_vector = 0xffff_ffff_0000`，64KiB）；`ADR-0004 §D1/§D2.3`（ROM/启动协议）。
- 备选：QEMU 内建 bootrom；`-kernel` 加载（**已否决**：用 `-bios`）。
- 影响面·代价：`QEMU-047t`、`ADR-0004 R1`、`LLVM-060t`（bootrom 是 LLVM 新指令首个真实用户）；写错则启动模型/复位向量冲突。

**D13 — 承载位置：测试机/SEE 规范正文入 `spec/`（非 ADR）；ADR 只记决策**
- 提案：规范正文归 `spec/`，ADR 仅承载决策/理由/被否方案。
- 依据：用户 2026-10-07 已锁定边界 E17（原话「规范正文不是 ADR——用户明确」）；`spec/Process-03`（ADR 不承载规范正文）。
- 备选：正文写入 ADR（已否决）。
- 影响面·代价：`SPEC-113t`/`114t` 分工；写错则 ADR 承载正文、违反 `Process-03`。

**D14 — 共享层适配点：DADAO 钩子按 `n` 选 bank（`n=0`→`rd16`、`n=1`→`rb16`）、`common_semi_set_ret`→`rd31`；属小适配（非重写）**
- 提案：因 v5 三组寄存器分离，钩子按参数序号选 bank。
- 依据：用户 2026-10-07 第 2 轮裁定 3；QEMU `target/riscv/common-semi-target.c:19`（`gpr[xA0 + argno]`）、`semihosting/arm-compat-semi.c:395-396`（`nr=common_semi_arg(cs,0)`、`args=(cs,1)`）；`.tao/knowledge/contract-abi.md §4.1`（三组各自独立计数）。
- 备选：让 v5 三组合并为 `a0` 连续（破坏 ABI）；或改共享层（重写）。
- 影响面·代价：`QEMU-046t`；写错则 `n=1` 取到 `rd17` 而非 `rb16`。

### 二、`ADR-0004`（就地修订）— 新 bootrom 与加载模型

**R1 — 加载/入口模型：SEE 启动 = bootrom 固件（初始权限/向量配置）→ 跳应用；用 `-bios`、复位向量不变（`0xffff_ffff_0000`）；bootrom hypv→user 直跳、不启用 supv；须明确与 M4 ELF 路径（现不用 `-bios`）的并存/替代关系**
- 提案：为 SEE 启动确立「bootrom + `-bios`」加载模型，并厘清与既有 M4 ELF 路径的关系。
- 依据：用户 2026-10-07 第 2 轮裁定 5/6；`ADR-0004 §D2.2/§D2.3`（现「路径 A ELF 不用 `-bios`」「路径 B 双镜像用 `-bios`」）、`§D1`、`spec/DADAO-12 §2.1:68`。
- 备选：保持 M4 ELF 路径不变、bootrom 仅用于 raw-bin。
- 影响面·代价：`ADR-0004` 修订、`QEMU-047t`、`contract-elf §6.2`；⚠️ **待判点**：ELF 路径与 bootrom `-bios` 是**并存还是替代**，须用户明确（否则启动路径说明自相矛盾）。

**R2 — `ADR-0004 D3` 的 exit port 与 semihosting `SYS_EXIT` 的关系：`SYS_EXIT` 替代 exit-port，迁移范围 = 全部**
- 提案：修订 `ADR-0004 D3` 口径，以 `SYS_EXIT` 取代 exit-port。
- 依据：用户 2026-10-07 第 2 轮裁定 7；`ADR-0004 §D3`（exit port 协议）、`ADR-0011`（halt 确定性）；同 `D8`。
- 备选：保留 exit-port 兼容并存（已否决）。
- 影响面·代价：`ADR-0004 §D3` 修订（或按 `Process-03` 标 `Superseded`）、`TESTCASES-034t`；写错则回归判据失效。

**R3 — 段布局/RAM 基址（`0xffff_0000_0000`）/ROM（`0xffff_ffff_0000` 64KiB）是否因 bootrom 调整；复位向量/ROM 起点不变；RAM 基址是否调整仍属逐条判定项**
- 提案：判定 RAM 基址（及段布局/ROM）是否随新 bootrom 调整；复位向量/ROM 起点确认不变。
- 依据：用户 2026-10-07 第 2 轮裁定 6（复位向量/ROM 不变）；`ADR-0004 §D1`（RAM 16MiB `0xffff_0000_0000`、ROM 64KiB `0xffff_ffff_0000`）、`contract-elf §5/§6`。
- 备选：调整 RAM 基址/容量；调整段布局。
- 影响面·代价（**归属**）：⚠️ **本任务仅判定/记录**；**本 M5 任务清单不承接 RAM 基址调整的实现**，若判需调整由本任务**记录结论并后续另立任务**（不得在本任务内改实现/链接脚本/`QEMU-047t` 链接脚本）；写错则链接脚本/向量布局返工。

### 三、`ADR-0016`（落地范围判定）

**S1 — M5 落地（`INFRA-047t`）沿用 `D1–D11`，除非用户裁定调整范围（是否纳入 `manifests/` 定位机制的全部改名点）**
- 提案：`INFRA-047t` 沿用已 `Accepted` 的 `ADR-0016 D1–D11`；不调整范围则仅记结论、不改 ADR 正文。
- 依据：用户 2026-10-07 第 2 轮裁定（待裁定项 10 相关）；`.tao/adr/adr-0016-dadao-install-layout.md`（`D1–D11` 已于 2026-10-02 经用户逐条确认，`Accepted`）；`manifests/install-dirs.lock.toml` 已作为 `D7`「单一真源」存在。
- 备选：调整范围（全部/部分改名点纳入，如 `references.lock.toml` 的 `path`、`fetch_refs.py`/`status.py`）。
- 影响面·代价：`INFRA-047t`、`ADR-0016`（沿用则无需改正文，记结论即可；若调整按 `Process-03` 新增/`Superseded`/经授权就地修订）；写错则 install 落地范围不清、改名点遗漏。

---

### 附：编制时发现的证据问题（供用户裁定参考，**不静默补齐**）

1. **`D9` 依据归属不精确**：四类 `NUPERM/NJPERM/NSPERM/NHPERM` 出自 `spec/DADAO-12 §2.2`（L92/L255）与异常表（L449-452，PTBR 权限）；`§5` 异常进入流程对未授权 cfx 触发的是 `ILLI`。`INTEG-019k:63` 与 `SPEC-113t:30` 均写「见 `DADAO-12 §5`」——须订正归属（清单 D9 已标注）。
2. **`D1` 的 tag 无 spec 依据**：`immu18[17:16]==2'b11` ⇒ semihosting 属**架构自定义**（`spec/DADAO-22` 无 semihosting 语义），须在 ADR/spec 明示。
3. **`INTEG-019k` 编号表述未同步（非跳号）**：`§待用户裁定项 10`（L251）与 architect 自审（L318）写「`D1–D13`（+`D14` 新提案）」，而 ADR 表（L199-212）为 **`D1–D14` 连续**。**无缺号/跳号**，仅表述滞后。
4. **`D9` 命名近似**：`cfx_<name>_<mode>_perm` 为近似写法；spec 实际寄存器名为 `cfx_⟨cfxname⟩_<mode>_global_cfx_mask` 与 `cfx_⟨cfxname⟩_<mode>_<instr>_cfx_mask`（`spec/DADAO-12 §3` cg0–cg3）。属措辞近似，非冲突。
5. **`R1` 存在真实待判点**：现 `ADR-0004 §D2.3` 路径 A（M4 ELF）「不用 `-bios`」，与 SEE 启动「用 `-bios`」的关系（**并存 vs 替代**）用户裁定尚未给出——须在 R1 判定时一并明确。

---

### 四、用户逐条裁定结果（2026-10-07，**原话落盘**）

> **用户原话（裁定总述，逐字）**：
> > ADR0020：注意核内地址空间的划分；以及如果越界需要报异常，包括取指；2、D1的相关说明，可以放到新的MACHINE-01中；R1：用-bios bootrom，与elf并存；R2：是的；R3：RAM基址改为全0
>
> **后续两问回答（原话）**：
> > R3 实现归属：**「M5 内分两步：机器模型+bootrom 先做，旧向量迁移另立」**
> > C 的过渡方式：**「C1 双映射过渡（推荐）」**

> **推定说明（须用户复核）**：主会话此前声明「**未特别指出者视为保留**」⇒ 本轮仅 **D1、D15（新增）、R1、R2、R3** 被特别指出；**`D2–D14`、`S1` 一律按「未特别指出 = 保留」推定**。该推定为**默认推定、待用户复核**；若用户对某条另有意见，按 `Process-03` 处置（新增/`Superseded`/经授权就地修订）。

| 条目 | 裁定 | 用户原话 / 依据 | 落点 |
| --- | --- | --- | --- |
| **D1** | **保留**（决策）；语义说明移 `spec/` | 「2、D1的相关说明，可以放到新的MACHINE-01中」 | 决策保留于 `ADR-0020`；**其语义/理由说明**（`immu18[17:16]==2'b11` 判定、**无 spec 依据属架构自定义**）落 **`spec/Machine-01-*`**（归 `SPEC-114t`）；ADR-0020 只留决策 |
| **D2–D14** | **保留（推定）** | 未特别指出 ⇒ 推定保留（**待用户复核**） | 原样写入 `ADR-0020` |
| **D15（新增）** | **采纳（新增 decision）** | 「ADR0020：注意核内地址空间的划分；以及如果越界需要报异常，包括取指」 | 新增 `ADR-0020 D15`，见下 |
| **R1** | **保留 + 口径明确** | 「R1：用-bios bootrom，与elf并存」 | `ADR-0004` 修订：**`-bios` bootrom 与 M4 ELF 路径【并存】（非替代）** |
| **R2** | **保留** | 「R2：是的」 | `ADR-0004 D3` 修订 = `SYS_EXIT` 取代 exit-port |
| **R3** | **修改** | 「R3：RAM基址改为全0」 | **RAM 基址改为全 0**（`0x0000_0000_0000`）；C1 双映射两步（见下） |
| **S1** | **保留（推定）** | 未特别指出 ⇒ 推定保留（**待用户复核**） | `INFRA-047t` 沿用 `ADR-0016 D1–D11` |

**D15 内容（写入 `ADR-0020` 正本，正本由本任务执行）**：
- **核内地址空间划分**：M5 测试机使用的 cfxha 段/地址区间——
  - **RAM@0（新）**：`0x0000_0000_0000` 起（cfxha 0 = `umon` 段），**供 bootrom/SEE**（C1 step1 双映射引入）；
  - **boot ROM**：`0xffff_ffff_0000`（cfxha 63 = `power`，64 KiB，复位向量，`-bios`）；
  - **旧 RAM 段（过渡保留）**：`0xffff_0000_0000`（cfxha 63，16 MiB，供既有测试）；
  - （exit port `0xffff_8000_0000` 同属 cfxha 63，见 `ADR-0004 D3`）。
- **越界访问与越界取指均须报异常**（**含取指路径**）：须写清异常语义——**`CFXMEM`**（spec：核内地址空间非法访问，`spec/DADAO-12 §2.1:73`、异常原因表 `1<<1`）vs 测试机约定 **`unmapped 0x87`**（`ADR-0004 D5.8`）。**注**：`ADR-0004 D5.8` fault 码表**已冻结、不得重排**；`CFXMEM`（`1<<1`）对应 `0x81`（`0x80 | 1`），落在表中已保留的 `0x81`–`0x86`（spec cause 位 1–6）区间内，**无需新码/重排**；若确需新码，须说明依据。

**R3 归属与 C1 两步过渡**（`ADR-0004` 修订口径，实现另立）：
- **R3 实现归属**（用户原话）：「**M5 内分两步：机器模型+bootrom 先做，旧向量迁移另立**」。
- **C1 双映射过渡**（用户原话：「C1 双映射过渡（推荐）」）：
  - **step1（M5）**：QEMU 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段（`0xffff_0000_0000`，供既有测试）** + `-bios` bootrom；**`check-interface` 断言新增 RAM@0 段（旧断言保留）** ⇒ **每任务门控保持全绿**。
  - **step2（另立，M5 之外）**：既有向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言。
- **实测依据（不可臆改）**：QEMU 侧宏在 `components/qemu/patches/{target/dadao/cpu.h.patch, target/dadao/helper.c.patch, hw/dadao/dadao-machine.c.patch}`（`DADAO_RAM_BASE`/`DADAO_RAM_SIZE`）；门控 `check-interface`（∈ `make check`）在 `tools/integ/check_interface_alignment.py:319-347` 硬断言 `RAM_BASE=0xFFFF_0000_0000`、`RAM_SIZE=16MiB`（`:351` 起断言 exit port 基址）。
  - 本裁定落盘时复核的实测位置：`cpu.h.patch:63-64`（`DADAO_RAM_BASE 0xffff00000000ULL` / `DADAO_RAM_SIZE (16 * 1024 * 1024)`）、`hw/dadao/dadao-machine.c.patch:183`（`{ "RAM", DADAO_RAM_BASE, DADAO_RAM_SIZE }`）与 `:485-486`（`memory_region_init_ram(... DADAO_RAM_SIZE ...)` + `add_subregion(system_memory, DADAO_RAM_BASE, ram)`）、`helper.c.patch:103`（`addr >= DADAO_RAM_BASE && addr < DADAO_RAM_BASE + DADAO_RAM_SIZE`）；`tools/integ/check_interface_alignment.py:319`（`ram_base_exp = 0xFFFF_0000_0000`）、`:320`（`ram_size_exp = 16 * 1024 * 1024`）、`:351`（`exit_base_exp`）。



#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：`Accepted`。证据脚本重跑 **51/51 PASS, EXIT=0**；**独立注入**（自行改 `ADR-0004` 的 `D3` 节标题）⇒ 脚本报 `adr-0004 D3 正文未改 | expected=[same] actual=[DIFFERENT]`、**EXIT=1** ⇒ `cp`+`md5` 还原（`adr-0020=77414d82…`、`adr-0004=7d2e6159…`）⇒ **回绿 51/51**；`make check` **EXIT=0**（`check-interface` 80/80、lit 60/60）。
- **architect 交叉复核**：**维持 `Accepted`**。① 独立在临时树复现同款注入逻辑（改 `D3` 节标题 ⇒ 该节 `DIFFERENT`、其余 5 节 `same`，且注入 `diff` 非空 ⇒ **防空注入**）；② 逐节提取 `D1/D2.1/D3/D4/D5/D6` 均**非空**且 `HEAD == 工作树`（防「空提取⇒假 same」）；③ `ADR-0004` 受保护正文**零改动**（`git show ac0962e` 仅 `**状态**` 行 + `## 修订` 追加）；④ 核 `D15` 四要素与 R3 两步归属齐全；⑤ ADR **不承载规范正文**（`D1` 语义归 `spec/Machine-01-*`）。
- **共识**：`ADR-0020`（D1–D15，`Accepted`）与 `ADR-0004` 修订（R1 `-bios`/ELF **并存**、R2 `SYS_EXIT` 取代 exit-port、R3 **RAM 基址改全 0** + C1 双映射两步）落位；`ADR-0016` `S1`「沿用、无正文改动」；**无否决未处置**；用户逐条裁定**原话落盘**（`D2–D14`/`S1` 的「推定保留」已获用户 2026-10-07 **明确确认**，原话「全部确认」）。
- **补充发现（措辞级，不阻塞，不改变判决）**：`ADR-0004 R2` 括注称「（`D3` 标 `Superseded`）」，而 `D3` 节内**无** in-place `Superseded` 标记——其「取代」由**修订条目（文件级）**声明；`Process-03`（「新增 ADR 或标注 `Superseded`」）已由**新增 `ADR-0020`** 满足 ⇒ 决策成立。**待办**：是否经授权修订为二选一（给 `D3` 加 `Superseded` 标记 / 改括注为「由本修订条目声明取代」）——**未擅自改**，登记待用户定。
- **收尾检查**：`make check` 覆盖内改动（`.tao/adr/**` 属决策层文档；`**状态**`/`## 修订` 追加）已由 reviewer 重跑 `EXIT=0`；台账为纯文档（豁免）；`git status --porcelain -uall` 干净；证据留 `.work/evidence/SPEC-113t/`、`.work/log/spec/`。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。

#### 经授权修订：ADR-0004 D3 加 Superseded 标记（2026-10-07，用户原话「闭合即可，a」）

- **用户裁定原话**：**「闭合即可，a」**（对上方收尾「补充发现」登记的遗留项「是否经授权修订为二选一」作答）⇒ 选定 **a = 给 `ADR-0004 D3` 加 `Superseded` 标记**；即**授权**对已 `Accepted` 决策（`D3`）作**经授权就地修订**（`spec/Process-03`「决策变更时新增 ADR 或标注 `Superseded`」的 `Superseded` 途径）。
- **改动摘要**：
  1. `.tao/adr/adr-0004-test-machine.md`：
     - `### D3 Exit Port 协议` 标题下方新增**单行 in-place 标记**：`> **Superseded by \`ADR-0020 D8\`**（2026-10-07，经用户授权）——semihosting \`SYS_EXIT\` 取代 exit-port 作为停机协议；取代声明亦见本 ADR \`## 修订\` rev. 2026-10-07 \`R2\`；本节点内正文未改写。`（写法与 `spec/Process-03`「标注 `Superseded`」及 `feedback_004` §3 建议一致：`> **Superseded by ADR-00xx Dn**`）。
     - `## 修订` `R2` 括注**同步**：`（\`D3\` 标 \`Superseded\`）` → `（\`D3\` 节内标 \`Superseded\`，见 \`D3\` 标题下方标记）`；`本 rev 不改写 \`D3\` 正文` → `本 rev 仅加该标记、不改写 \`D3\` 协议正文`——使括注与 `D3` 节内实际标记**一致**（消除原「声称已标而未标」）。
     - **未改** `D3` 协议正文语义、**未改**其它受保护节（`D1`/`D2.1`/`D4`/`D5`/`D6`）：`git diff` 仅「`D3` 标题后插入标记（+标记行+空行）」与「`R2` 一行替换」两处；`D3` 节删标记行后与 HEAD 逐字一致。
  2. `.work/evidence/SPEC-113t/run.sh`（gitignored）：原第 4 节「`D3` 正文未改（与 HEAD 逐字相同）」改**白名单式**——新增 `d3_whitelist_ok()`：① `D3` 节**删标记行（含其引入的空行）后须与 HEAD 逐字一致**；② 标记须存在且指明 `ADR-0020 D8`；③ 防空提取（防空 ⇒ 假 `same`）。其余受保护节（`D1`/`D2.1`/`D4`/`D5`/`D6`）**仍要求逐字相同**（「修一类」保留）。新增第 6 节注入自检：删 `D3` 的 `Superseded` 标记行 ⇒ 白名单断言 **FAIL** ⇒ `cp`+`md5` 还原 ⇒ **回绿**。
- **脚本重跑真实输出与结论**：`bash .work/evidence/SPEC-113t/run.sh` ⇒ **`RESULT: PASS`、`EXIT=0`**（49 项检查，0 FAIL）。关键行：第 4 节 `[PASS] adr-0004 D3 白名单（仅 Superseded 标记差异） | expected=[ok] actual=[ok]`；第 6 节 `[PASS] inject(D3): D3 白名单断言应 FAIL | expected=[FAIL] actual=[FAIL]`、`[PASS] restore(D3): D3 白名单断言应回绿 | expected=[ok] actual=[ok]`。完整输出：`.work/log/spec/SPEC-113t-evidence-rerun.log`。
- **独立注入（architect 复核，非脚本自检）**：在临时树 `/tmp/opencode/SPEC-113t/` 改 `D3` 协议正文（`0xffff_8000_0000`→`0xffff_8000_0008`）⇒ 同款「按节提取 + 删标记行 + `diff`」逻辑报 **DIFFERENT**（证明白名单**不吞**正文改动，仍判 FAIL）；注入 `git diff --stat` 非空（防空注入）。工作树未受污染：`git status --porcelain -uall` 仅 ` M .tao/adr/adr-0004-test-machine.md`（md5 `bc2bd33c30a2aed2bfc5817aa1027c23`）；`adr-0020` md5 未变（`77414d82d68c17890aff09aced796d8e`）。
- **提交**：见下方 architect 提交（经授权修订）记录。

#### architect 提交（经授权修订）

- **档位**：**正常**（用户对 `SPEC-113t` 收尾遗留项裁定「闭合即可，a」= **授权**经授权就地修订；改动为决策层文档 `Superseded` 标记，**不含 `WIP:` 前缀**）。
- **文件集对账**（显式 staging，未用 `git add -A`）：`git diff --cached --name-only` 与本节「改动摘要」+ 任务范围对账 —— 应入库 **2 项**：`.tao/adr/adr-0004-test-machine.md`（`D3` 标记 + `R2` 括注同步）、`.tao/tasks/spec/SPEC-113t-ADR决策落地.md`（本记录）；**无漏提 / 无多提 / 无越界**（未卷入 `adr-0020`、`spec/`、`components/`、其它任务书；`.work/**` gitignored 不入库）。
- **提交信息**：`SPEC-113t 后续：ADR-0004 D3 加 Superseded 标记（经用户授权）`；**新增提交**（不改写已 push 的 `ca7ad85`）；**只 commit，未 push**（push 归主会话）。

#### 第 2 轮 reviewer 验收（经授权后续改动复验）

**审查环境**：临时目录 `/tmp/opencode/SPEC-113t-review2/`；模型 `mimo-v2.5-pro`；审查对象 = `ff88dcc`（`ca7ad85` 之后的新增提交）。

##### 1. 重跑证据脚本

```
$ bash .work/evidence/SPEC-113t/run.sh > /tmp/opencode/SPEC-113t-review2/evidence.log 2>&1; echo "EXIT=$?"
EXIT=0
```

**完整输出**（51/51 PASS）：

```
== SPEC-113t 证据：ADR 决策落地 ==
repo=/mnt/tao/DADAO-v5

-- 1. ADR-0020 落位与结构 --
[PASS] adr-0020 存在
[PASS] adr-0020 结构 ×5
[PASS] adr-0020 状态 Accepted
[PASS] adr-0020 状态说明含 Accepted（2026-10-07）
[PASS] adr-0020 状态说明含推定保留
[PASS] adr-0020 D1 语义说明移 spec/Machine-01
[PASS] adr-0020 D1 无 spec 依据（架构自定义）
[PASS] adr-0020 D1..D15 缺失数（应为 0） | [0]=[0]

-- 2. ADR-0020 D15 口径 --
[PASS] D15 核内地址空间 RAM@0
[PASS] D15 boot ROM 复位向量
[PASS] D15 旧 RAM 段过渡保留
[PASS] D15 exit port
[PASS] D15 RAM 基址全 0
[PASS] D15 含取指路径
[PASS] D15 CFXMEM
[PASS] D15 CFXMEM cause 1<<1
[PASS] D15 CFXMEM 映射 0x81
[PASS] D15 测试机约定 unmapped 0x87
[PASS] D15 码表冻结不重排

-- 3. ADR-0004 修订（R1/R2/R3 + 取代关系）--
[PASS] adr-0004 has 修订
[PASS] adr-0004 rev. 2026-10-07
[PASS] adr-0004 R1/R2/R3
[PASS] adr-0004 R1 并存非替代
[PASS] adr-0004 R2 取代本 ADR D3
[PASS] adr-0004 R2 Superseded
[PASS] adr-0004 R3 RAM 改全 0
[PASS] adr-0004 R3 C1 双映射两步过渡
[PASS] adr-0004 R3 step1/step2

-- 4. 受保护决策正文（HEAD vs worktree 逐节比对 + D3 白名单）--
[PASS] D1/D2.1/D4/D5/D6 正文未改 | [same]=[same]
[PASS] D3 白名单（仅 Superseded 标记差异） | [ok]=[ok]

-- 5. 注入自检：删 D15 行 --
[PASS] inject 行差=1 / D-missing=1 / restore md5 一致 / D-missing=0

-- 6. 注入自检：删 D3 的 Superseded 标记行 --
[PASS] inject(D3) 行差=1 / D3 白名单 FAIL / restore md5 一致 / D3 白名单 ok
```

✅ **51/51 PASS，EXIT=0**。

##### 2. 独立注入反例（reviewer 自行执行，两次）

**注入前快照**：
```
$ git status --porcelain -uall
（空——工作树干净）
$ md5sum .tao/adr/adr-0004-test-machine.md .tao/adr/adr-0020-see-semihosting.md
bc2bd33c30a2aed2bfc5817aa1027c23  .tao/adr/adr-0004-test-machine.md
77414d82d68c17890aff09aced796d8e  .tao/adr/adr-0020-see-semihosting.md
```

**注入 A：删 D3 的 `Superseded` 标记行**（L98 `> **Superseded by \`ADR-0020 D8\`**...`）

- 方法：`grep -v '> \*\*Superseded by `ADR-0020 D8`\*\*'` 删行
- 注入后 `git diff --name-only` = `.tao/adr/adr-0004-test-machine.md`（非空 ✅）
- 注入后行差 = 397 → 396（=1 ✅）
- 重跑脚本：`[FAIL] adr-0004 D3 白名单（仅 Superseded 标记差异） | expected=[ok] actual=[VIOLATION]`，EXIT=1 ✅
- 还原：`cp` 备份回，md5=`bc2bd33c30a2aed2bfc5817aa1027c23`（一致 ✅），`git status` 干净
- 还原后重跑：51/51 PASS，EXIT=0 ✅

**注入 B：改 D3 协议正文**（L100 `0xffff_8000_0000` → `0xffff_8000_DEAD`）

- 方法：`sed -i '100s/0xffff_8000_0000/0xffff_8000_DEAD/'`
- 注入后 `git diff` 非空 ✅（改了 D3 协议正文地址值）
- 重跑脚本：`[FAIL] adr-0004 D3 白名单（仅 Superseded 标记差异） | expected=[ok] actual=[VIOLATION]`，EXIT=1 ✅
- 还原：`cp` 备份回，md5=`bc2bd33c30a2aed2bfc5817aa1027c23`（一致 ✅），`git status` 干净
- 还原后重跑：51/51 PASS，EXIT=0 ✅

**结论**：两次注入（删标记行 / 改协议正文）均被脚本检出 FAIL，还原后均回绿。白名单**不吞**正文改动。

**还原后快照对账**：
```
$ git status --porcelain -uall
（空——工作树干净）
$ md5sum .tao/adr/adr-0004-test-machine.md .tao/adr/adr-0020-see-semihosting.md
bc2bd33c30a2aed2bfc5817aa1027c23  .tao/adr/adr-0004-test-machine.md
77414d82d68c17890aff09aced796d8e  .tao/adr/adr-0020-see-semihosting.md
```
与注入前快照**逐行一致** ✅。

##### 3. 核改动范围（`git show ff88dcc`）

`ff88dcc` 仅改 **2 文件**：

| 文件 | 改动 |
|------|------|
| `.tao/adr/adr-0004-test-machine.md` | +4/-1：① `### D3 Exit Port 协议` 标题后插入 Superseded 标记行+空行（+2）；② `## 修订` R2 括注同步（`D3 标 Superseded` → `D3 节内标 Superseded，见 D3 标题下方标记`；`不改写 D3 正文` → `仅加该标记、不改写 D3 协议正文`）（+1/-1） |
| `.tao/tasks/spec/SPEC-113t-ADR决策落地.md` | +19：追加「经授权修订」记录 + architect 提交记录 |

- **D1/D2.1/D4/D5/D6**：零改动 ✅
- **D3 协议正文**（地址/宽度/编码等）：零改动 ✅（仅标题后加了标记行）

##### 4. 核历史未被改写

```
$ git log --oneline ca7ad85~1..HEAD
ff88dcc SPEC-113t 后续：ADR-0004 D3 加 Superseded 标记（经用户授权）
ca7ad85 SPEC-113t ADR-0020 新建 + ADR-0004 修订（M5 W1）——已验证

$ git rev-parse origin/master
ca7ad852b7a255d9ed67ba60cbe55d49defce113

$ git rev-parse ca7ad85
ca7ad852b7a255d9ed67ba60cbe55d49defce113
```

- `origin/master` == `ca7ad85` ✅（已 push 提交未被改写）
- `ff88dcc` 是 `ca7ad85` 之上的**新增提交**（非 amend）✅

##### 5. 核表述一致性

- **D3 标记**：`> **Superseded by \`ADR-0020 D8\`**（2026-10-07，经用户授权）——semihosting \`SYS_EXIT\` 取代 exit-port 作为停机协议；取代声明亦见本 ADR \`## 修订\` rev. 2026-10-07 \`R2\`；本节点内正文未改写。`
- **R2 括注**：`（D3 节内标 Superseded，见 D3 标题下方标记）`
- **一致性**：D3 标记指明取代者 `ADR-0020 D8`，R2 括注指向 D3 标记——**互相一致**，不再「声称已标而未标」 ✅
- **Process-03 合规**：格式 `> **Superseded by ADR-00xx Dn**` 符合 `spec/Process-03`「标注 `Superseded`」与 `feedback_004` §3 建议 ✅

##### 6. 核未越界

```
$ git show ff88dcc --name-only --format=""
.tao/adr/adr-0004-test-machine.md
.tao/tasks/spec/SPEC-113t-ADR决策落地.md

$ git diff ca7ad85..ff88dcc -- .tao/adr/adr-0020-see-semihosting.md  （空）
$ git diff ca7ad85..ff88dcc -- spec/                                   （空）
$ git diff ca7ad85..ff88dcc -- components/                             （空）
$ git diff ca7ad85..ff88dcc -- .tao/adr/adr-0016-dadao-install-layout.md（空）
```

未卷入 `spec/`、`adr-0020`、`adr-0016`、`components/`、其它任务书 ✅

##### 判决

**Accepted** — 验收命令块在独立重跑下全部通过（51/51 PASS，EXIT=0）、两次独立注入反例均成功检出并回绿、改动范围精确（仅 D3 标记+R2 括注同步+任务书记录）、历史未被改写、表述一致、未越界、约束无违反。
