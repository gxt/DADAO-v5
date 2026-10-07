# SPEC-114t: SEE/HEE 运行环境 + semihosting 规范正文（`spec/` + 投影）

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-113t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：把 SEE/HEE 运行环境与 semihosting 的**规范正文入 `spec/`**（`INTEG-019k E17`：正文入 `spec/`、**不是 ADR**），并补投影（`.tao/knowledge/contract-*.md`）。`ADR-0020` 只记决策；本任务落正文。
- **输入（自包含）**：
  - `SPEC-113t` 落地的 `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，D1–D14）+ `adr-0004` 修订（R1–R3）。
  - `spec/DADAO-12-SEE-主管系统运行环境.md`（§1 运行模式 + cfxha/cfxname 表；§2.1 核内地址空间/复位向量；§2.2 PTBR 权限 `NUPERM/NJPERM/NSPERM/NHPERM`；§3 cg0–cg7 共有寄存器〔含 `global_cfx_mask`/`cfx2rd|cfx2rc|cfxld|cfxst|trap|escape_cfx_mask`/`switch_run_mode`/`switch_cfx_mask`/`excp_vector`/`excp_cause_mask`〕；§4 专有寄存器；§5 异常进入/退出流程、`escape` 语义、跨 cfx escape 安全约束）。
  - `spec/DADAO-13-HEE-超管系统运行环境.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`（`trap cfxha, immu18`；调用约定；`escape cfxha,[excp_cause_ip,4]` 返回；`:58` CFXREG）、`spec/DADAO-21-ABI-应用程序二进制接口.md`（参数寄存器 `rd16-rd31`/`rb16-rb31`/`rf16-rf31`；返回值 `rd31`；系统调用号 RD15；「与 ABI 传参规范一致」）。
  - `.tao/knowledge/contract-abi.md §4.1/§4.4`（semihosting 复用此约定）。
  - `spec/README.md` 投影表（`DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行现为 `deferred`：`contract-sbi.md`/`contract-mmu.md`/`contract-exception.md`）。
- **输出**：
  1. **规范正文落点（用户裁定 2026-10-07）= 新建 `spec/Machine-01-测试机运行环境.md`**（`Machine` 前缀经用户确认）。承载 SEE/HEE **测试机运行环境与 semihosting** 的 v5 规范正文；章节建议：
     - ① **内存映射/复位**（引 `ADR-0004`；`DADAO-12 §2.1`：复位向量/ROM `0xffff_ffff_0000`、64 KiB；**核内地址空间划分表**：RAM@0〔`0x0000_0000_0000`，cfxha 0 = `umon`，供 bootrom/SEE〕、boot ROM〔cfxha 63 = `power`，64 KiB〕、**旧 RAM 段过渡保留**〔`0xffff_0000_0000`，cfxha 63，16 MiB〕、exit port〔`0xffff_8000_0000`，cfxha 63〕——引 **`ADR-0020 D15`**；**越界访问与越界取指异常语义**：`CFXMEM`〔`DADAO-12 §2.1:73`，`1<<1`〕vs 测试机约定 `unmapped 0x87`〔`ADR-0004 D5.8`〕，**含取指路径**，码表冻结不重排；**RAM@0 双映射现状**〔C1 step1 `QEMU-049t`：RAM@0 与旧 RAM 段并存；step2 另立〕；RAM 基址口径以 **`ADR-0004 R3`（改全 0）** 为准）；
     - ② **运行模式**（`hypv`/`user`；**本版不启用 `supv`**、不涉及 `smon`；引 `ADR-0004 R1`）；
     - ③ **cfx 与权限**（`cfx0/1/2/3/63`；`global_cfx_mask`/指令类型 mask/`switch_run_mode`；**未实现 cfx ⇒ `CFXREG`**〔`DADAO-22 §1`〕；四类 PERM 异常 `NUPERM/NJPERM/NSPERM/NHPERM`〔`DADAO-12 §2.2`〕，讲清其与 cfx 访问权限层〔§5 异常进入流程〕的关系）；
     - ④ **`trap`/`escape` 与异常进入流程**（一般 trap 走 `DADAO-12 §5` 步骤 1–10、**进入 cfx 向量**；`escape` 退出语义与 `imms18` 位宽关系）；
     - ⑤ **semihosting**（判定 `immu18[17:16] == 2'b11`；**`D1` 语义/理由说明**：该 tag 判定 **无 spec 依据、属架构自定义**〔`ADR-0020 D1`，用户裁定「`D1` 的相关说明放到 `Machine-01`」〕，并讲清「semihosting〔`==2'b11`〕 vs 一般 trap〔`≠2'b11`〕」两条路；**服务表 = 完整 25 个（ARM 号值）**；传参 `rd16`/块指针 `rb16`/返回 `rd31`；**无 `escape`、PC 步进返回**；`SYSTEM` 宿主命令执行风险作**已知风险**登记）；
     - ⑥ **加载与 bootrom**（`-bios` 加载、复位向量不变 `0xffff_ffff_0000`；bootrom = 初始权限/向量配置；引 `ADR-0004 R1`）；
     - ⑦ **退出**（`SYS_EXIT` 替代 `exit port`；引 `ADR-0004 R2`）。
  2. **`spec/DADAO-12` 本体补正**（spec 模块任务可改上游，`ADR-0012 D4`）：在 §5 等补齐 M5 落地所需正文——**`switch_run_mode` 语义**（D10）、**两条路**（一般 trap 走 §5 异常进入流程/进入向量；semihosting 的具体承接位置说明）、**权限范围 = `cfx0/1/2/3/63`**、**未实现 cfx ⇒ CFXREG**、**核内地址空间划分 + 越界访问/取指异常（`ADR-0020 D15`：`CFXMEM` vs 测试机约定 `unmapped 0x87`，含取指路径；`ADR-0004 D5.8` 码表冻结不重排）**；如需，同步 `spec/DADAO-13`（HEE，cg3/hmon）与 `spec/DADAO-22`/`spec/DADAO-21` 的相关措辞。**不改动与 M5 无关的语义**。
  3. **semihosting 调用表正文**（入 `spec/`，非 ADR）：**判定**（`trap` 的 `immu18[17:16]==2'b11`）；**传参/返回寄存器**（号→`rd16`、参数块指针→`rb16`、返回值→`rd31`）；**号值 = ARM 号值**；**服务表 = 完整 25 个**（`OPEN 0x01`/`CLOSE 0x02`/`WRITEC 0x03`/`WRITE0 0x04`/`WRITE 0x05`/`READ 0x06`/`READC 0x07`/`ISERROR 0x08`/`ISTTY 0x09`/`SEEK 0x0a`/`FLEN 0x0c`/`TMPNAM 0x0d`/`REMOVE 0x0e`/`RENAME 0x0f`/`CLOCK 0x10`/`TIME 0x11`/`SYSTEM 0x12`/`ERRNO 0x13`/`GET_CMDLINE 0x15`/`HEAPINFO 0x16`/`EXIT 0x18`/`SYNCCACHE 0x19`/`EXIT_EXTENDED 0x20`/`ELAPSED 0x30`/`TICKFREQ 0x31`）；**返回机制**（无 `escape`，PC 步进）；**`SYS_EXIT` 替代 exit port**；**`SYSTEM` 的宿主命令执行风险**作**已知风险**显式登记。**落点**：正文入新建 **`spec/Machine-01-测试机运行环境.md` §⑤**（见 item 1，用户裁定 2026-10-07）；**不臆造与上游不符的册名**。
  4. **投影（叙述合约）**：`contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`（或经 `Process-02` 归一化确定的最小集合）——把上列正文归一化为可精确消费的断言（含 `§` 编号 + `[DADAO-NN §x]` 引用），供 LLVM/QEMU 消费。**投影文件由 spec 模块建立**（`.tao/knowledge/`）。
  5. **`spec/README.md` 登记与投影表同步**：**分册清单登记新建 `Machine-01-测试机运行环境.md`**（新增「测试机」分组或依现有体例并入「环境」分组）；**投影表新增 `Machine-01` 行**（①叙述合约 = `contract-see.md`/`contract-semihosting.md` 等，②/③/④ 据实）；`DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-23` 行的 ①列/②列状态由 `deferred`/`缺口` 更新为本任务落地后的实际落点（`contract-sbi.md` 等；`contract-mmu.md` 若仍 `deferred` 则注明**原因/触发**）。**`check-spec-refs` 须绿**。
- **约束（硬）**：
  - **不接 ADR 正文**（`Process-03`）；**不实现**（实现归 `LLVM-060t`/`QEMU-*`）；**不产向量**（归 `TESTCASES-*`）。
  - **期望值来源**：semihosting 号值/寄存器/服务集以 `ADR-0020`（用户逐条确认后）+ 本任务正文为**唯一来源**，**不得**从 QEMU 实现反推。
  - `spec/` 为共享文件，与 `SPEC-113t`/`115t`/`116t`/`117t` **串行**。
  - `make check`（含 `check-spec-refs`/`check-spec-drift`/`check-asm-prose` 等）EXIT=0。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-114t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **正文入 `spec/`**：**新建 `spec/Machine-01-测试机运行环境.md`** 含 ①内存映射/复位（**核内地址空间划分表** + **越界访问/取指异常**语义，`ADR-0020 D15`）②运行模式 ③cfx/权限 ④`trap`/`escape`/异常进入 ⑤semihosting（判定+**`D1` 语义说明**+25 服务+传参）⑥加载/bootrom ⑦退出；`spec/DADAO-12`（及必要的 `DADAO-13`/`DADAO-21`/`DADAO-22`）含 `switch_run_mode` 语义、两条路、权限范围 `cfx0/1/2/3/63`、未实现 cfx ⇒ CFXREG；给 `grep`/`sed` 真实输出。
2. **semihosting 调用表**：判定（`immu18[17:16]==2'b11`）、传参/返回（`rd16`/`rb16`/`rd31`）、**完整 25 服务**（逐条计数=25）、PC 步进、`SYS_EXIT` 替代、`SYSTEM` 风险登记；给真实输出。
3. **投影落地**：`.tao/knowledge/contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`（或确定的最小集合）存在，含 `§` 编号 + `[DADAO-NN §x]` 引用；`spec/README.md` 投影表对应行更新（`deferred`→实际落点）。
4. **门控**：`make check` EXIT=0（`repository checks: PASS`；`check-spec-refs` 0 violations）；给真实输出。
5. **一键证据脚本**：`.work/evidence/SPEC-114t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（删一条服务号/改一处传参寄存器 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
6. **无残留**：`git status --untracked-files=all` 仅 `spec/**`（含**新建 `spec/Machine-01-测试机运行环境.md`** 及相关册）+ `.tao/knowledge/contract-*.md` + `spec/README.md` + 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 逐条核 25 服务/传参寄存器/投影一致 + 判决）
