# INTEG-019k: M5（SEE/HEE 运行环境 + semihosting）启动与分解

**模块**：integ
**项目里程碑**：M5
**依赖**：无
**状态**：已验证

> **本 `k` 定位**：M5 的**规划/启动**任务书（谋事有因）。按 `spec/Process-04 §1`（用户 2026-10-06 裁定），**M5 起里程碑由 INTEG 模块开启**（开启 = INTEG 规划 `k`）——故本文件落 `integ` 模块（**非** `SPEC-*k`，M1–M4 的历史做法不沿用）。本 `k` 只做规划、**不执行**、**不创建 `t`/`m` 任务文件**；任务清单以「草案」形式载于 §任务分解；**本轮用户裁定已落盘（见 §第 2 轮用户裁定）**，按 `/plan` 流程交叉审查后再落 **21 份**任务书。

---

## 问题根源

M4（ELF 文件支持 + LLD 链接 + 汇编器遗留收口）已达成（2026-10-07，见 `milestones.md`）。当前 v5 工具链是「**裸机、无 OS、无 syscall**」的：

- **QEMU** 只实现「M1 标量核心 + FP 执行层 + ELF 加载」；**无 SEE**（无四运行模式、无 cfx 寄存器、无 cfx 掩码/权限、无 `switch_run_mode`、无异常进入/退出流程）；**无 semihosting**。
- **停机协议**依赖 `exit port`（`ADR-0004 D3`，MMIO `0xffff_8000_0000` 8B 只写）——这是 v5 自定、非 spec 语义（`MEMORY.md` 偏离台账第 1 项）。
- **LLVM** 不实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`SimRISC-11 §其它`）；4 条均在 `contracts/*` 中 `scope: excluded` ⇒ **decode ILLI**（`ISS-110`）。因此任何依赖 cfx 的代码（含 bootrom/固件）都编不出、跑不了。
- **install**（`ADR-0016 D1–D11`）尚未落地：门控/执行器**就地**从 `.work/build/{llvm,qemu}` 取可执行，无 `--prefix`/sysroot；**生成物落点**未按新规则（`.dadao/tests/`）迁移。
- **规范层缺口**：`contract-sbi.md`/`contract-mmu.md`/`contract-exception.md` 均 `deferred`（`spec/README.md` 投影表）；SEE/SBI 的规范正文**未激活**。

结果：v5 无法承载真实（C/OS/多模式）程序——**没有系统调用/字符输出/退出机制**，也没有「核芯功能扩展」这一 spec 核心机制的任何实现。

---

## 目的

把 QEMU 从「**裸机、无 syscall、exit-port 停机**」升级为「**SEE/HEE 运行环境 + semihosting**」：

```
自有工具链编 bootrom（LLVM 新指令首个真实用户）
  → QEMU 启动 bootrom（初始权限/向量配置）
  → guest 经 trap（semihosting tag = immu18[17:16]==2'b11）
  → QEMU 共享层 do_common_semihosting（ARM 号值）
  → SYS_EXIT / 控制台输出替代 exit-port
```

同时清掉基础设施欠账（`ADR-0016` install + 生成物落点）、把 `trap`/`escape`/`cfx2rc`/`cfx2rd` 从 `excluded` **re-scope 为已实现**、把 SEE/semihosting 规范**正文入 `spec/`**。

**门槛（用户 2026-10-07 第 2 轮裁定，见 §第 2 轮用户裁定）**：门槛名 = **`make test-semihost`**（**不是** `test-see`——用户指出"没有 SEE"）。组成：① **正向**（bootrom + 单/多 TU ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码）；② **权限反例**（未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`）；③ **服务表各条至少 1 例**；④ **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）；⑤ **`INTEG` 开闭**。

**边界声明**：**M6 = 完整调用约定（整数）+ 欠账收口**（已定，**不在本 `k` 的任务清单内**）。FP/RF codegen、clang 前端、libc/OS、golden model 不在 M5。

---

## 已锁定边界（用户裁定 2026-10-07，**原样落盘**，作为设计依据）

> 以下 A–E 为用户本轮讨论已定口径；各条编号为用户原编号。凡涉未定取值者，见 §待用户裁定项（**已由 §第 2 轮用户裁定逐条定案**）。

### A. semihosting（QEMU 侧「直接复用、不重写」）

1. **判定**：`trap cfxHA, immu18` 中 **`immu18[17:16]==2'b11`** ⇒ semihosting（与 `cfxha` 无关）。
2. **号/参数**：**用 ABI 传参寄存器**——因共享层 `nr = common_semi_arg(cs,0)` **自取寄存器**；**返回值**写回同一「a0 等价物」。**（第 2 轮裁定具体号：号→`rd16`、参数块指针→`rb16`、返回值→`rd31`；见 §第 2 轮用户裁定 2）**
3. **采用 ARM 号值**（`OPEN 0x01`…`EXIT 0x18`/`EXIT_EXTENDED 0x20`…）；服务集**倾向完整 25 个**，但分档：**D1 必做**（console `WRITEC/WRITE0/WRITE/READC` + 退出 `EXIT/EXIT_EXTENDED` + 错误 `ISERROR/ERRNO` + 系统信息 `CLOCK/TIME/ELAPSED/TICKFREQ/GET_CMDLINE` + `ISTTY/SYNCCACHE`）；**D2 文件档**（`OPEN/CLOSE/READ/SEEK/FLEN/TMPNAM/REMOVE/RENAME`，需 host FS 通道）；**D3 `SYSTEM 0x12` 建议拒（ENOSYS）**。**（第 2 轮裁定：服务集 = 完整 25 个；`SYSTEM`、`HEAPINFO` 都做——`SYSTEM` 风险保留在 ADR/spec 作已知风险；见 §第 2 轮用户裁定 1）**
4. **返回**：**无 `escape` 指令**——服务后 **PC 步进**（RISC-V `env->pc += 4`）+ 写回返回寄存器（用户原话：「**退出的 escape 无需指令，直接执行**」）。
5. **复用范式（实测锁定 QEMU）**：共享入口 `do_common_semihosting(cs)`（`semihosting/arm-compat-semi.c`，声明于 `include/semihosting/common-semi.h`）；每 target 只提供 **`common-semi-target.c` 式钩子**（照 `target/riscv/common-semi-target.c`：`common_semi_arg`/`common_semi_set_ret`/`is_64bit_semihosting`/`common_semi_sys_exit_is_extended`/`common_semi_stack_bottom`/`common_semi_has_synccache`）；接入方式 = **trap 译码后抛 semihost 内部异常**（RISC-V：`RISCV_EXCP_SEMIHOST` → `do_common_semihosting(cs)` → `pc += 4`）。**（第 2 轮补充：v5 三组分离 ⇒ 钩子须按 `n` 选 bank——`n=0`→`rd16`、`n=1`→`rb16`、`set_ret`→`rd31`；小适配、非重写；见 §第 2 轮用户裁定 3）**
6. **32/64**：由 `is_64bit_semihosting()` 一概决定；**v5 恒 64 位**；参数块 = **64 位字段 + target 端序**（v5 大端，共享层走 `cpu_ld*_data` ⇒ 自动正确）。
7. **host 侧安全**：机制照搬；**默认值由 harness/Makefile 的命令行 `-semihosting-config` 给**（`target=native|gdb|auto`、`chardev=`、`arg=`）；QEMU **`auto` 的实际语义 = 有 GDB⇒gdb、无 GDB⇒native（首次调用判定并记住）** ⇒ **建议默认 `gdb`/沙箱**，`native` 显式开。
8. **`SYS_EXIT` 替代现有 `exit port`**（`ADR-0004 D3`）⇒ 既有 M1–M4 依赖 exit-port 的向量/harness **迁移**是任务的一部分。**（第 2 轮裁定：迁移范围 = 全部；见 §第 2 轮用户裁定 7）**

### B. SEE/HEE 运行环境（QEMU + 新 bootrom）

9. **QEMU 权限实现粒度 = 完整**：cfx 掩码（`cfx_<name>_<mode>_perm` + 指令类型 mask）、`cfx_<name>_<mode>_switch_run_mode`、权限异常（`NUPERM/NJPERM/NSPERM/NHPERM`，见 `DADAO-12 §5 异常进入流程`）；**运行模式与 cfx 正交**（`SimRISC-11 L80`：trap/escape 可在**任意模式**执行，由 cfx mask 控制）。**（第 2 轮裁定 cfx 范围：只做 `cfx0/1/2/3/63`；未实现 cfx ⇒ `CFXREG` 异常；见 §第 2 轮用户裁定 4）**
10. **流程**：**先过权限，允许则直接服务**（不进入该 cfx 的向量；`switch_run_mode` 语义须在 spec/ADR 里讲清）。
11. **`cfxha` 不设白名单**——是否允许调用**由权限控制**。
12. **新 bootrom**：M5 的 QEMU 提供**新 bootrom**（固件），用于**初始权限/向量配置**；bootrom **用我们自己的工具链编**（⇒ 是 LLVM 新指令的第一个真实用户）；`ADR-0004` 的加载/入口模型（现「路径 A 不用 `-bios`」）**须随之调整**。**（第 2 轮裁定：用 `-bios`、复位向量不变 `0xffff_ffff_0000`；bootrom hypv→user 直跳、本版不启用 supv；见 §第 2 轮用户裁定 5/6）**

### C. LLVM

13. 实现 **`trap`/`escape`/`cfx2rc`/`cfx2rd`**（`SimRISC-11 §其它`）；**`SimRISC-12 §待定`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred**。⇒ spec 侧要把这 4 条从 **`scope: excluded` → 已实现**（re-scope）。
14. `escape` 位宽：**编码 18 位**（字节偏移、必为 4 的倍数）⇒ **汇编里写 20 位**，无冲突（用户确认；但请在 spec 里写清这层关系）。
    - 规范实测映射（`Toolchain-01 §3.2`）：汇编层 **`imms20`（字节，须 `%4==0`）⇔ 编码层 `imms18`（`field = bytes >> 2`）**，`Addr = excp_cause_ip + (imms18 << 2)`。

### D. 基础设施

15. **install 落地**（`ADR-0016 D1–D11`）+ **生成物落点迁移**（`test-codegen`/`test-elf`/lit `test_exec_root` → `.dadao/tests/`；`.work/log`/`.work/evidence` 不动）+ `Process-05 §6` 补正。
16. **大小写**：`spec/Toolchain-01 §2.1` + `contract-asm §2.1` 改为**大小写敏感**（撤销「不敏感」条款）⇒ `ISS-157` 以「条款撤销」结案。

### E. 承载位置

17. 测试机/SEE 的**规范正文入 `spec/`**（**不是 ADR**——用户明确）；**ADR 只记决策**。

> **更新（2026-10-07 第 2 轮）**：A2/A3/A5/A8、B9/B12 等的**待定取值**已由用户裁定，见 §第 2 轮用户裁定；**凡与本节冲突者，以 §第 2 轮用户裁定为准**。

---

## 第 2 轮用户裁定（2026-10-07，**原话落盘**）

> 本节汇总用户本轮逐条裁定，**原话/要点原样保留**（`AGENTS.md`「ADR decision 逐条确认」；`lessons §7.3`）。凡与上文 A–E 口径冲突者，**以本节为准**。**本节裁定 = 任务内容定论**（`k` 的规划依据）；`ADR-0020`/`ADR-0004` 的 decision 仍须由用户**逐条**判定后才可写入（承载任务 `SPEC-113t`）。

1. **服务集 = 完整 25 个**（原话要点：「**复用、ARM/RISC-V 有就做**」）⇒ 含 **D2 文件档**；**`SYSTEM`、`HEAPINFO` 都做**（`SYSTEM` 的"执行宿主命令"风险**保留在 ADR/spec 作已知风险**，不因此拒服务）。
2. **传参/返回寄存器 = 用 ABI 定义**（`.tao/knowledge/contract-abi.md §4`）：
   - **号（标量）→ `rd16`（=`rda0`）**（`.tao/knowledge/contract-abi.md §4.1`：`rd16–rd31` 数据参数寄存器）；
   - **参数块指针（地址）→ `rb16`**（`.tao/knowledge/contract-abi.md §4.1`：`rb16–rb31` 地址参数寄存器）；
   - **返回值 → `rd31`**（`.tao/knowledge/contract-abi.md §4.4`；**指针返回才用 `rb31`，semihosting 不用**）。
   - ⇒「a0 等价物」= **`rd16`**（对齐共享层 `common_semi_arg(cs,0)` = 号、`(cs,1)` = 参数块指针）；**不另设 `rd15`**（`DADAO-22 §2` 的 `rd15` 是 umon/jmon syscall 号，semihosting 不用）。
3. **⚠️ 共享层适配点（新增，必须写进任务）**：QEMU 共享层 `common_semi_arg(cs,n)` 假定"**同一组 `a0+n`**"（实测 `target/riscv/common-semi-target.c:19` = `gpr[xA0 + argno]`；共享层 `semihosting/arm-compat-semi.c:395-396` 取 `nr`/`args`），而 v5 **三组分离**（`rd`/`rb`/`rf` 各自独立计数）⇒ v5 的 target 钩子须**按 `n` 选 bank**（`n=0`→`rd16`、`n=1`→`rb16`）、`common_semi_set_ret`→`rd31`。**属小适配（非重写）**：仅写 `target/dadao/common-semi-target.c`。
4. **权限范围**：只做 **`cfx0/1/2/3/63`**（按 `DADAO-12 §1` 表 = `umon/jmon/smon/hmon/power`）；**访问未实现 cfx ⇒ 依 spec 触发 `CFXREG` 异常**。
   - **spec 出处（已核实）**：`spec/DADAO-22-SBI-主管系统二进制接口.md:58`（`SBI_SMON_PROBE_CFX` 行：「**若 cfx 硬件不存在则触发 CFXREG 异常**」）。相关佐证：`spec/DADAO-12-SEE-主管系统运行环境.md:373`（读写不存在/超出数量的 cfx 暂存寄存器，`rc ≥ N` ⇒ CFXREG）、`spec/SimRISC-11-其它.md:121`（读写不存在的 `cfx_<cfxname>_cgHB_rcHC` 组合 ⇒ CFXREG）。
5. **模式**：bootrom **hypv → user 直跳、本版不启用 supv**（**落纸说明**；`smon` 不参与）。
6. **bootrom 加载**：**用 `-bios`**、**复位向量不变**（`0xffff_ffff_0000`，`DADAO-12 §2.1`）。
7. **exit-port 迁移范围 = 全部**（M1–M4 所有依赖 exit-port 的向量/harness 全迁到 `SYS_EXIT`）。
8. **`ADR-0020` 新建** ✓（decision 提案**待用户逐条判定**）。
9. **M5 门槛名 = `make test-semihost`**（**不是** `test-see`——用户指出"**没有 SEE**"）；门槛组成 = **正向**（bootrom + 单/多 TU ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码）/ **权限反例**（未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`）/ **服务表各条至少 1 例** / **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）/ **`INTEG` 开闭**。
10. **执行顺序**：**先 `/plan` 交叉审查本 `k`，再建 21 份任务书**（本 `k` 仍只出草案、**不建 `t`/`m` 文件**）。

---

## 对照关系

- **QEMU 上游 RISC-V semihosting（实测锁定，只读对照，非执行依赖）**：
  - 共享入口：`do_common_semihosting(CPUState *cs)`（`semihosting/arm-compat-semi.c:385`）；target 钩子声明于 `include/semihosting/common-semi.h`。
  - 钩子实现范式：`target/riscv/common-semi-target.c`（`common_semi_arg` 取 `gpr[xA0+argno]`、`common_semi_set_ret` 写 `gpr[xA0]`）。共享层：`nr = common_semi_arg(cs,0)`、`args = common_semi_arg(cs,1)`；`GET_ARG/SET_ARG` 按 `is_64bit_semihosting` 走 `get/put_user_u64`（⇒ 端序随之正确）。
  - 接入点：`target/riscv/tcg/insn_trans/trans_privileged.c.inc` 抛 `RISCV_EXCP_SEMIHOST` → `target/riscv/tcg/cpu_helper.c`：`case RISCV_EXCP_SEMIHOST: do_common_semihosting(cs); env->pc += 4;`。
  - **v5 照搬此范式**：复用共享层（不重写）、只写 DADAO `common-semi-target.c` 钩子、异常后 `pc += 4`。
- **ARM 号值（共享层 `semihosting/arm-compat-semi.c:54-78` 实测）**：`OPEN 0x01 / CLOSE 0x02 / WRITEC 0x03 / WRITE0 0x04 / WRITE 0x05 / READ 0x06 / READC 0x07 / ISERROR 0x08 / ISTTY 0x09 / SEEK 0x0a / FLEN 0x0c / TMPNAM 0x0d / REMOVE 0x0e / RENAME 0x0f / CLOCK 0x10 / TIME 0x11 / SYSTEM 0x12 / ERRNO 0x13 / GET_CMDLINE 0x15 / HEAPINFO 0x16 / EXIT 0x18 / SYNCCACHE 0x19 / EXIT_EXTENDED 0x20 / ELAPSED 0x30 / TICKFREQ 0x31`。
- **0628 路线对照（只读、不复制、非执行依赖）**：DADAO-0628 = `trap cfx_smon` → CFXTRAP → **cfx_smon responder 应答 Linux syscall 号**（`SYS_write=64`/`SYS_writev=66`/`SYS_read=63`；见 `.cache/refs/DADAO-0628/components/qemu/patches/{0014,0021,0022}`，cfxcode/func 经 env scratch 传递）。**与 v5 选定路线不同**：v5 用 **ARM 号值** + **tag 在 `immu18[17:16]==2'b11`**（与 `cfxha` 无关），走 QEMU **共享层 `do_common_semihosting`**；0628 的 syscall 号 + 自建 responder 仅作**方法论对照**（responder 如何取参/返回/推进 PC）。
- **v5 合约分两层（引用约定）**：`contracts/*.yaml` = 机器可读数据（**无 `§` 章节号**）；`.tao/knowledge/contract-*.md` = 合约正文（**含 `§` 章节号**）。本文件及 `milestones.md` 的 `§4.1/§4.4` 等引用**属后者**，完整路径 = `.tao/knowledge/contract-abi.md`（如其 `§4.1 参数寄存器`、`§4.4 返回值`）。
- **spec 依据（v5 自身知识，执行依据）**：
  - `spec/DADAO-12 §1`（四运行模式 + cfxha/cfxname 表 + 作用域）、`§2.2`（PTBR 权限异常 `NUPERM/NJPERM/NSPERM/NHPERM`）、`§3`（cg0–cg7 共有寄存器：`global_cfx_mask`/`cfx2rd|cfx2rc|cfxld|cfxst|trap|escape_cfx_mask`/`switch_run_mode`/`switch_cfx_mask`/`excp_vector`/`excp_cause_mask`）、`§5`（异常进入/退出流程；`escape` 语义；「trap/escape/cfxld/cfxst/cfx2rd/cfx2rc **可在任意运行模式执行**」；跨 cfx escape 安全约束）。
  - `spec/DADAO-22`（`trap cfxha, immu18`；调用约定；参数「与 ABI 传参规范一致」；`escape cfxha,[excp_cause_ip,4]` 返回）。
  - `spec/SimRISC-11 §其它`（`trap`/`escape`/`cfx2rc`/`cfx2rd` 编码与汇编形式；`cfx<ha>`/`cfx_<name>` 两种写法；cfx2rd/cfx2rc 简化 regname 写法）。
  - `spec/SimRISC-12 §待定`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` —— **保持 deferred**）。
  - `spec/DADAO-21`（参数寄存器 `rd16-rd31`/`rb16-rb31`/`rf16-rf31`；返回值 `rd31`；系统调用号 `RD15`；「与 ABI 传参规范一致」⇒ semihosting 复用此约定）。
  - `spec/Process-05`（TDD 三层向量 + 反例门控）、`spec/Process-04 §1`（INTEG 开启/结束闭环）。

---

## 任务分解（草案）

> 编号规则：`<PREFIX>-nnn<suffix>`，模块内递增、跨后缀共享。各模块起始号 = 该模块 M4 归档后最大号 + 1。
> **本 `k` 只出草案，不建 `t`/`m` 文件**；建立时机已裁定：**先 `/plan` 交叉审查本 `k`，再建 21 份**（见 §待用户裁定项 9 / §第 2 轮用户裁定 10）。**（2026-10-07 追加：按 `ADR-0004 R3`/`ADR-0020 D15` 裁定，新增 C1 step1 `QEMU-049t`（RAM@0 双映射）⇒ 21 → **22 份**。）**

| 编号 | 任务 | 模块 | 交付物（一句话范围） | 依赖 |
|------|------|------|----------------------|------|
| `INTEG-019k` | **M5 启动与分解**（本文件） | integ | 本 `k` + `milestones.md` M5 定义 | 无 |
| `INFRA-047t` | **install 落地**（`ADR-0016 D1–D11`） | infra | Makefile 定位机制（`manifests/` 单一真源）+ `tools/infra/` + `.dadao/{cross-toolchain,dadao-unknown-elf}` 布局；门控/执行器改从 **install 根**取可执行；`.work/` 仅 build 区；保留「从源码可重建」 | 无 |
| `INFRA-048t` | **生成物落点迁移**（→ `.dadao/tests/`） | infra | `Makefile`（`CODEGEN_E2E_WORK` + `test-elf` 目标 + lit `test_exec_root`）+ `tools/integ/run_{codegen,elf}_e2e.py` + `.gitignore`；`.work/log`/`.work/evidence` **不动** | `INFRA-047t` |
| `SPEC-113t` | **ADR 决策落地**（`ADR-0020` 新建 + `ADR-0004` 修订 + `ADR-0016` 范围） | spec | `.tao/adr/adr-0020-*.md` + `adr-0004` 就地修订 + `adr-0016` 修订/沿用；**每个 decision 逐条经用户确认**（**用户 2026-10-07 逐条裁定**：**新增 `ADR-0020 D15`**〔核内地址空间划分 + 越界访问/取指异常〕；**`D1`** 决策保留、语义说明移 `spec/Machine-01-*`；**`R1`** = `-bios` bootrom 与 M4 ELF **并存**；**`R2`** = `SYS_EXIT` 取代 exit-port；**`R3`** = **RAM 基址改全 0 + C1 双映射两步**〔step1 = `QEMU-049t`；step2 = 另立〕；`D2–D14`/`S1` 按「未特别指出=保留」**推定**，待用户复核）。**本任务只落 ADR 决策/口径，不改实现/链接脚本** | 无（决策先行） |
| `SPEC-114t` | **SEE/HEE 运行环境 + semihosting 规范正文** | spec | **新建 `spec/Machine-01-测试机运行环境.md`**（正文落点，用户裁定 2026-10-07）+ `spec/DADAO-12`（§1/§5 等，+`DADAO-13`/`DADAO-22`/`DADAO-21` 相关）+ 投影 `contract-sbi.md`/`contract-see.md`/`contract-semihosting.md` + `spec/README` 登记与投影表 | `SPEC-113t` |
| `SPEC-115t` | **re-scope：`trap`/`escape`/`cfx2rc`/`cfx2rd` `excluded`→已实现** | spec | `spec/SimRISC-11` + `contracts/opcodes.yaml`/`legality_rules.yaml` + `contract-isa`/`contract-asm`/`contract-asm-list` 投影 + `check_scope.py` 对齐；**`SimRISC-12` 保持 deferred** | `SPEC-114t`、`SPEC-113t` |
| `SPEC-116t` | **大小写敏感修订**（`Toolchain-01 §2.1` + `contract-asm §2.1`） | spec | 上述两处（撤销「不敏感」条款）+ `check-asm-*`/`check-spec-refs` 绿；**`ISS-157` 以「条款撤销」结案** | 无（与 113–115 同改 `spec/` ⇒ 串行） |
| `SPEC-117t` | **`Process-05 §6` 落点规则补正** | spec | `spec/Process-05-里程碑TDD规范.md §6`（`.dadao/tests/` 规则正文） | `INFRA-048t` |
| `LLVM-060t` | **`trap`/`escape`/`cfx2rc`/`cfx2rd`**（MC + 必要 CodeGen/内建） | llvm | `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（parser/printer/disassembler/编码）+ lit L1 + 编码 oracle；`escape` 位宽关系落实 | `SPEC-115t`、`INFRA-047t` |
| `QEMU-044t` | **SEE/HEE 运行模式 + cfx 寄存器/掩码/权限/异常** | qemu | `components/qemu/patches/target/dadao/**` + `hw/dadao/**`：四运行模式、cg0–cg7 共有 + 专有寄存器、`global_cfx_mask`/指令类型 mask、`switch_run_mode`、权限异常（`NU/J/SP/HPERM`）、**异常进入流程**（`DADAO-12 §5`）+ 探针。**权限范围 = 只做 `cfx0/1/2/3/63`**（`umon/jmon/smon/hmon/power`）；**未实现 cfx ⇒ `CFXREG` 异常**（`DADAO-22:58`） | `SPEC-114t` |
| `QEMU-045t` | **`trap`/`escape` 语义 + `cfx2rd`/`cfx2rc` 执行** | qemu | trap 译码 → CFXTRAP 路由 → **走 spec 异常进入流程（`DADAO-12 §5`）并进入该 cfx 的向量**（**一般 trap**，`immu18[17:16] ≠ 2'b11`）；`escape` 退出（恢复 `prev_run_mode`/`prev_cfx_mask`、`escape_num`++、按 `imms18` 跳转）；cfx2rd/cfx2rc 读写 cfx 寄存器 + 探针；**semihosting 短路（`immu18[17:16] == 2'b11`，译码层直接服务、不进入向量）不在本任务，见 `QEMU-046t`** | `SPEC-115t`、`SPEC-114t`、`QEMU-044t` |
| `QEMU-046t` | **semihosting** | qemu | `immu18[17:16]==2'b11` 判定（**QEMU 译码层短路，与 RISC-V `RISCV_EXCP_SEMIHOST` 同构**：**不进入 cfx 向量**、直接服务并按 PC 步进返回；对照「一般 trap 走 spec 异常进入流程并进入向量」，见 `QEMU-045t`）；`DADAO common-semi-target.c` 钩子（**按 `n` 选 bank**：`n=0`→`rd16`、`n=1`→`rb16`；`set_ret`→`rd31`——**共享层小适配，非重写**）+ 复用 `do_common_semihosting`；**服务表 = 完整 25 个**（含 **D2 文件档**；**`SYSTEM`、`HEAPINFO` 都做**）；`SYS_EXIT` **替代 exit port**；探针 | `QEMU-045t`、`SPEC-114t` |
| `QEMU-047t` | **新 bootrom**（构建 + 链接 + 测试） | qemu | bootrom 固件源码（初始权限/向量配置；**hypv → user 直跳、本版不启用 supv**）+ 自有工具链构建/链接接入（`Makefile`；**含 bootrom 链接脚本**——地址布局对齐 `0xffff_ffff_0000` 的 64 KiB ROM 区、段序/对齐依 `ADR-0004`/`contract-elf`）+ **`-bios` 加载、复位向量不变（`0xffff_ffff_0000`）** + 端到端启动证据（LLVM 新指令首个真实用户） | `LLVM-060t`、`QEMU-044t`、`QEMU-049t`（RAM@0 双映射）、`INFRA-047t` |
| `QEMU-049t` | **RAM@0 双映射**（C1 step1；`ADR-0004 R3`/`ADR-0020 D15`） | qemu | `components/qemu/patches/target/dadao/**` + `hw/dadao/**`：QEMU 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段（`0xffff_0000_0000`，供既有测试）** + **RAM@0 链接基址（供 bootrom/SEE 的链接脚本片段）**；**`check-interface` 断言新增 RAM@0 段（旧断言保留）** ⇒ 每任务门控保持全绿；**越界（访问/取指）异常语义**（`CFXMEM` vs 测试机约定 `unmapped 0x87`，含取指路径）见 `ADR-0020 D15` | `QEMU-044t`（同改 `hw/dadao/**` ⇒ 串行） |
| `RAM@0-migrate`（**另立，M5 之外**） | **旧向量/harness 迁移到 RAM@0**（C1 step2）；**不建本 M5 任务书** | （跨 testcases/integ/infra/qemu） | 既有向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段（`0xffff_0000_0000`）+ 收紧 `check-interface` 断言；**登记为另立任务**（编号待 M6 规划/另立时确定；**不阻塞 M5 门槛**——M5 门控经 step1 双映射保持全绿） | `QEMU-049t`、`TESTCASES-034t`、`INTEG-020t` |
| `TESTCASES-033t` | **SEE/HEE + semihosting 向量**（L1 MC + L3 执行） | testcases | `tests/llvm/lit/MC/DADAO/`（trap/escape/cfx2*；**分阶段**：`LLVM-060t` 就绪前 L1 MC 向量以 `UNSUPPORTED:` 暂缓，`LLVM-060t` 完成后去除 `UNSUPPORTED:`）+ `tests/llvm/codegen/m5/`（semihosting 服务/权限异常）+ 独立 oracle（**禁从 LLVM/QEMU 反填**） | `SPEC-114t`、`SPEC-115t`、`LLVM-060t`、`INFRA-048t` |
| `TESTCASES-034t` | **exit-port → `SYS_EXIT` 迁移**（范围 = **全部**） | testcases | M1–M4 **所有**依赖 exit-port 的向量/harness + oracle 更新；`ISS-147`（exit 码与 fault 区重叠）随迁处置 | `QEMU-046t`、`TESTCASES-033t` |
| `INTEG-020t` | **SEE/semihosting E2E + harness stdio 捕获 + 门控收口** | integ | `tools/integ/` 驱动 + `Makefile`（新目标 **`test-semihost`**）+ `tests/e2e/lit/`；harness stdio 捕获（**细节展开**：`-semihosting-config` 的 `chardev=`/`target=` 由 Makefile 传参还是 harness 脚本包装；console 输出捕获到 stdout/stderr 的落点与比对）；`make check` 收口 | `QEMU-046t`、`QEMU-047t`、`TESTCASES-033t`、`TESTCASES-034t` |
| `INFRA-049m` | M5 infra 里程碑 | infra | `m` 文件 | `INFRA-047t`/`048t` |
| `SPEC-118m` | M5 spec 里程碑 | spec | `m` 文件 | `SPEC-113t`~`117t` |
| `LLVM-061m` | M5 llvm 里程碑 | llvm | `m` 文件 | `LLVM-060t` |
| `QEMU-048m` | M5 qemu 里程碑 | qemu | `m` 文件 | `QEMU-044t`~`047t`、`QEMU-049t` |
| `TESTCASES-035m` | M5 testcases 里程碑 | testcases | `m` 文件 | `TESTCASES-033t`/`034t` |
| `INTEG-021m` | M5 integ 里程碑（**整体收敛点**） | integ | `m` 文件 | `INTEG-020t` |

> 合计：**16 `t` + 6 `m` = 22 份任务书**（含 2026-10-07 追加的 C1 step1 `QEMU-049t`；**step2 为「另立、M5 之外」，不计入本 M5 任务书**）。（原为 15 `t` + 6 `m` = 21 份。）

### 依赖关系与串行链（分波）

- **Wave 0 — 基础设施**（无前置，最先；同改 `Makefile` ⇒ **串行**）：
  `INFRA-047t`（install）→ `INFRA-048t`（落点迁移）→ `SPEC-117t`（`Process-05 §6` 补正，依 `INFRA-048t`）。
- **Wave 1 — 决策与规范（spec-first）**：
  `SPEC-113t`（ADR，**用户逐条确认**）→ `SPEC-114t`（规范正文）→ `SPEC-115t`（re-scope）；`SPEC-116t`（大小写）与 113–115 **同改 `spec/` ⇒ 串行**（可置于 114 前后）。
  ⇒ **ADR 未 `Accepted` 前不进入 Wave 2/3**（`Process-03`：决策先行）。
- **Wave 2 — LLVM 指令**：`LLVM-060t` ← `SPEC-115t`（编码/re-scope 定后）+ `INFRA-047t`（从 install 根取工具）。**只 1 条，无链内并发**。
- **Wave 3 — QEMU（与 Wave 2 不同仓库，可并行；但 QEMU 内串行）**：
  `QEMU-044t`（模式/cfx/权限/异常）→ `QEMU-045t`（trap/escape/cfx2*）→ `QEMU-046t`（semihosting）；
  `QEMU-049t`（RAM@0 双映射，C1 step1；← `QEMU-044t`，同改 `hw/dadao/**` ⇒ 串行）→ `QEMU-047t`（新 bootrom）← `LLVM-060t` + `QEMU-044t` + `QEMU-049t` + `INFRA-047t`（**须 LLVM 指令 + 权限配置 + RAM@0 就绪**）。
  - **step1/step2 关系（C1，`ADR-0004 R3`/`ADR-0020 D15`）**：`QEMU-049t` = step1（M5，机器模型双映射 + `check-interface` 新断言 ⇒ 门控全绿）；**step2**（旧向量/harness 迁到 `0` + 删旧 RAM 段 + 收紧断言）= **另立、M5 之外**，**不阻塞 M5 门槛**（M5 门控经双映射保持全绿）。
- **Wave 4 — 向量**：`TESTCASES-033t` ← `SPEC-114t`/`115t` + `LLVM-060t`（L1 MC 编码；`UNSUPPORTED:` 分阶段）+ `INFRA-048t`（落点）；`TESTCASES-034t` ← `QEMU-046t` + `TESTCASES-033t`（**迁移须在 semihosting 落地后**）。
- **Wave 5 — E2E + 门控收口**：`INTEG-020t` 最后（依赖 QEMU-046t/047t + 033t/034t）；**`make test-semihost`**（**不是** `test-see`）与既有 `make test-codegen`/`make test-elf` 并存或迁移后等价。
- **共享文件串行**：`Makefile`/`contracts/`/`spec/`/`tests/` 改动一律串行（`AGENTS.md`）。
- `k ↔ m`：本 `k` 对应 M5；各模块 `m` 在模块任务收敛时就近核验，M5 由主会话在依赖模块 `m` 均置 `里程碑` 后置 `达成`（`Process-04 §1`）。
- **反向依赖（实现 ← 契约）**：`LLVM-060t`←`SPEC-115t`；`QEMU-044t`←`SPEC-114t`；`QEMU-045t`←`SPEC-114t`/`115t`；`QEMU-046t`←`SPEC-114t`；`QEMU-049t`←`SPEC-113t`（`R3`/`D15` 决策）；`QEMU-047t`←`QEMU-049t`（RAM@0 双映射）；`TESTCASES-*`←`SPEC-114t`/`115t`；`TESTCASES-033t`←`LLVM-060t`（L1 MC 编码支持）。

### 分解理由

- **决策先行**（Wave 1 的 `SPEC-113t`）：本千行涉「跨组件合约 + 多方案 + 固定结论」，命中 `Process-03` ADR 判据（`ADR-0020`/`ADR-0004` 修订），故先落 ADR、经用户逐条确认，再落正文与实现。
- **基础设施前置**（Wave 0）：`ADR-0016` install + 落点迁移是 M5 起步待办（`milestones.md` §M5 起步待办），且改动波及门控/执行器——先做可避免后续任务反复改 `Makefile`。
- **spec 正文 ⇄ 实现分离**（`SPEC-114t`/`115t` vs `LLVM-060t`/`QEMU-*`）：`E17` 明确规范正文入 `spec/`；`Spec-first` 要求编码/语义期望值来自 `contracts/*`，不倒推。
- **bootrom 依赖链最紧**（`QEMU-047t` 四重依赖）：bootrom 是「LLVM 新指令首个真实用户」——只有在 `LLVM-060t` 能编 `trap`/`escape`/`cfx2*`、`QEMU-044t` 能配置初始权限、且 `QEMU-049t` 提供 RAM@0 双映射（供 bootrom/SEE）后方可构建/启动。
- **RAM@0 过渡分两步**（`ADR-0004 R3`/`ADR-0020 D15`，C1）：`QEMU-049t`（step1）先把机器模型改为**双映射**并**追加** `check-interface` 断言 —— 既有测试仍走旧 RAM 段 ⇒ **每任务门控保持全绿**；向量/harness 迁移（step2）**另立、M5 之外**，避免 M5 期间大面积改动既有向量/`crt0`。
- **向量与 E2E 分离**（`TESTCASES-*` vs `INTEG-020t`）：满足 **Independent oracle**；`Process-05` TDD ⇒ 向量先立。
- **`SimRISC-12` 保持 deferred**（`C13`）：不纳入本 M5，避免范围蔓延。

---

## 说明

### ADR 清单（**决策提案，逐条待用户判定，不得预先标 `Accepted`**）

> 依 `AGENTS.md`「ADR decision 逐条确认」：以下每个 decision 均须由用户逐条判定（保留/修改/否决），确认后方可写入 ADR。承载任务 = `SPEC-113t`。

**① `ADR-0020`（拟定**新建**）：SEE/HEE 运行环境与 semihosting**

| 提案 | decision |
|------|----------|
| D1 | **入口判定**：`trap cfxHA, immu18` 中 `immu18[17:16]==2'b11` ⇒ semihosting（与 `cfxha` 无关）。 |
| D2 | **传参/返回寄存器**（**用户 2026-10-07 裁定**）：**号（标量）→ `rd16`（=`rda0`）**、**参数块指针（地址）→ `rb16`**、**返回值 → `rd31`**（`.tao/knowledge/contract-abi.md §4.1/§4.4`；指针返回才用 `rb31`，semihosting 不用）。共享层 `nr = common_semi_arg(cs,0)`、参数块指针 = `common_semi_arg(cs,1)`。 |
| D3 | **号值 = ARM 号值**（`OPEN 0x01`…`EXIT 0x18`/`EXIT_EXTENDED 0x20`…）；**服务集 = 完整 25 个**（**用户 2026-10-07 裁定**：含 **D2 文件档**；**`SYSTEM`、`HEAPINFO` 都做**——`SYSTEM` 的"执行宿主命令"风险**保留在 ADR/spec 作已知风险**）。 |
| D4 | **返回机制**：无 `escape` 指令——服务后 **PC 步进**（`env->pc += 4`）+ 写回返回寄存器。 |
| D5 | **复用范式**：复用 QEMU 共享入口 `do_common_semihosting(cs)`；DADAO 只提供 `common-semi-target.c` 式钩子；接入 = trap 译码后抛 semihost 内部异常（类比 `RISCV_EXCP_SEMIHOST`）。 |
| D6 | **位宽/端序**：由 `is_64bit_semihosting()` 决定；v5 恒 64 位；参数块 = 64 位字段 + target 端序（v5 大端）。 |
| D7 | **host 侧安全**：默认值由 harness/Makefile 的 `-semihosting-config` 给；`auto` = 有 GDB⇒gdb、无 GDB⇒native；**建议默认 `gdb`/沙箱**，`native` 显式开。 |
| D8 | **`SYS_EXIT` 替代 `exit port`**（`ADR-0004 D3`）⇒ 既有 M1–M4 依赖 exit-port 的向量/harness **迁移**。 |
| D9 | **QEMU 权限实现粒度 = 完整**：cfx 掩码 + 指令类型 mask + `switch_run_mode` + 权限异常（`NUPERM/NJPERM/NSPERM/NHPERM`）；**运行模式与 cfx 正交**。 |
| D10 | **流程（两条路，2026-10-07 `/plan` 审查修订）**：(a) **一般 `trap cfxHA, immu18`**（`immu18[17:16] ≠ 2'b11`）：先过权限，允许则**走 spec 的异常进入流程**（`DADAO-12 §5`，含步骤 10「跳转至异常向量」）——**进入该 cfx 的向量**；(b) **semihosting**（`immu18[17:16] == 2'b11`）：**QEMU 译码层短路**（与 RISC-V `RISCV_EXCP_SEMIHOST` 同构）——**不进入向量**、直接服务并按 PC 步进返回（见 D4）。`switch_run_mode` 语义须在 spec/ADR 讲清。 |
| D11 | **`cfxha` 不设白名单**：是否允许调用由权限控制。 |
| D12 | **新 bootrom**：M5 的 QEMU 提供新 bootrom（固件），用于初始权限/向量配置；bootrom 用自有工具链编。**（用户 2026-10-07 裁定：`-bios` 加载、复位向量不变 `0xffff_ffff_0000`；bootrom hypv→user 直跳、本版不启用 supv）** |
| D13 | **承载位置**：测试机/SEE 规范正文入 `spec/`（非 ADR）；ADR 只记决策。 |
| D14 | **共享层适配点**（**用户 2026-10-07 裁定**）：共享层 `common_semi_arg(cs,n)` 假定"同一组 `a0+n`"（RISC-V 实测 `gpr[xA0+argno]`），v5 **三组分离** ⇒ DADAO 钩子**按 `n` 选 bank**（`n=0`→`rd16`、`n=1`→`rb16`）、`common_semi_set_ret`→`rd31`；**小适配（非重写）**。 |
| D15 | **核内地址空间划分 + 越界（访问/取指）报异常**（**用户 2026-10-07 裁定新增**）：M5 测试机使用的 cfxha 段/地址区间划分（**RAM@0**〔`0x0000_0000_0000`，cfxha 0 = `umon`，供 bootrom/SEE〕、**boot ROM**〔`0xffff_ffff_0000`，cfxha 63 = `power`，64 KiB，`-bios`〕、**旧 RAM 段过渡保留**〔`0xffff_0000_0000`，cfxha 63，16 MiB〕、exit port〔`0xffff_8000_0000`，cfxha 63〕）；**越界访问与越界取指均须报异常**（含取指路径）。异常语义：**`CFXMEM`**（spec：核内地址空间非法访问，`DADAO-12 §2.1:73`、异常原因表 `1<<1`）vs 测试机约定 **`unmapped 0x87`**（`ADR-0004 D5.8`）。**注**：`ADR-0004 D5.8` 码表**已冻结、不得重排**；`CFXMEM`（`1<<1`）⇒ `0x81`，落在表内已保留的 `0x81`–`0x86` 区间，**无需新码**。 |

**② `ADR-0004`（就地**修订**口径）：新 bootrom 与加载模型**

| 提案 | decision |
|------|----------|
| R1 | 现「路径 A ELF **不用 `-bios`**」与「路径 B 双镜像 **用 `-bios`**」须随 M5 **新 bootrom** 调整——新增/明确「SEE 启动 = bootrom 固件（初始权限/向量配置）→ 跳应用」的**加载/入口模型**（**用户 2026-10-07 裁定**：**用 `-bios`**、**复位向量不变** `0xffff_ffff_0000`；bootrom **hypv → user 直跳、本版不启用 supv**；**`-bios` bootrom 与 M4 ELF 路径【并存】、非替代**）。 |
| R2 | `ADR-0004 D3` 的 **exit port 与 semihosting `SYS_EXIT` 的关系**（**用户 2026-10-07 裁定**：**「R2：是的」**）：`SYS_EXIT` **替代** exit-port；**迁移范围 = 全部**（M1–M4 所有依赖 exit-port 的向量/harness 全迁）。 |
| R3 | 段布局/RAM 基址/ROM 是否因 bootrom 调整。**用户 2026-10-07 裁定**：复位向量/ROM 起点不变（`0xffff_ffff_0000`，64 KiB）；**RAM 基址改为全 0**（`0x0000_0000_0000`）；**C1 双映射两步**——**step1（M5）**：机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段（`0xffff_0000_0000`，供既有测试）** + `-bios` bootrom，`check-interface` 断言**新增 RAM@0 段（旧断言保留）** ⇒ **每任务门控保持全绿**；**step2（另立，M5 之外）**：既有向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言。 |

**③ `ADR-0016`（落地范围）**

| 提案 | decision |
|------|----------|
| S1 | `D1–D11` 已 `Accepted`；M5 落地（`INFRA-047t`）**沿用** D1–D11，除非用户裁定调整范围（是否纳入 `manifests/` 定位机制的全部改名点）。**（属 `SPEC-113t` 逐条 ADR 判定项，见 §待用户裁定项 10）** |

### 待用户裁定项清单（**2026-10-07 第 2 轮已逐条裁定**）

> **裁定原话见 §第 2 轮用户裁定**（`lessons §7.3`）。**裁定 = 任务内容定论**；`ADR-0020`/`ADR-0004` 的 decision 仍须由用户**逐条**判定后才可写入 ADR。

1. **semihosting `D2` 文件档**（`OPEN/CLOSE/READ/SEEK/FLEN/TMPNAM/REMOVE/RENAME`，需 host FS 通道）是否纳入本 M5？
   → **已裁定：纳入**（服务集 = 完整 25 个；「复用、ARM/RISC-V 有就做」）。
2. **semihosting `D3`**：`SYSTEM 0x12` 是否拒（`ENOSYS`）？`HEAPINFO 0x16` 是否纳入？
   → **已裁定：`SYSTEM`、`HEAPINFO` 都做**；`SYSTEM` 的"执行宿主命令"风险**保留在 ADR/spec 作已知风险**（不拒服务）。
3. **`rd` 传参寄存器具体号**：「a0 等价物」= `rd16`？号寄存器是否另设 = `rd15`（对齐 `DADAO-21` 系统调用号）？返回值写回哪个号？（按 `DADAO-21` 定）
   → **已裁定：号（标量）→ `rd16`（=`rda0`）；参数块指针 → `rb16`；返回值 → `rd31`**（`.tao/knowledge/contract-abi.md §4.1/§4.4`）。**不另设 `rd15`**（`rd15` 是 umon/jmon syscall 号，semihosting 不用）。
4. **QEMU 权限实现的具体 cfx/寄存器范围**：64 个 cfx 全实现还是子集？cg0–cg7 授权哪些？是否含 `§2.2` PTBR 权限/MMU/页表步进（**MMU 是否属 M5**）？
   → **已裁定：只做 `cfx0/1/2/3/63`**（`DADAO-12 §1` = `umon/jmon/smon/hmon/power`）；**访问未实现 cfx ⇒ `CFXREG` 异常**（出处 `spec/DADAO-22-SBI-主管系统二进制接口.md:58`，已核实）。`cfx_ptw`(=cfx4)/MMU/页表步进**不在本 M5 实现范围**。
5. **SEE 与 HEE 是否都做**：还是仅 SEE？HEE（`DADAO-13`/cg3/`hmon`）范围？
   → **已裁定：bootrom hypv → user 直跳、本版不启用 supv**（落纸说明；`smon` 不参与）。
6. **bootrom 的加载模型**：`-bios` 提供 bootrom vs QEMU 内建 vs `-kernel`；`ADR-0004` 路径 A/B 如何调整？
   → **已裁定：用 `-bios`**、**复位向量不变**（`0xffff_ffff_0000`）。
7. **exit-port 迁移范围**：哪些 M1–M4 向量/harness 迁到 `SYS_EXIT`？是否保留 exit-port 兼容？`ISS-147` 是否随迁处置？
   → **已裁定：迁移范围 = 全部**（M1–M4 所有依赖 exit-port 的向量/harness 全迁 `SYS_EXIT`）。
8. **M5 门槛**：提案「`make test-see` 绿 + `make check` 绿 + bootrom 端到端 + 既有门槛不回归」——待确认（及新目标命名）。
   → **已裁定：门槛名 = `make test-semihost`**（**不是** `test-see`；用户指出"没有 SEE"）；组成见 §第 2 轮用户裁定 9。
9. **`t`/`m` 任务文件的建立时机**：待上述裁定后按 `/plan` 流程创建（本 `k` 只出草案）。
   → **已裁定：先 `/plan` 交叉审查本 `k`，再建 21 份任务书**。
10. **`ADR-0020` 是否新建**（vs 并入现有 ADR）；及 D1–D13/R1–R3/S1 逐条判定。
    → **已裁定：新建 ✓**；`ADR-0020` D1–D13（+ D14 新提案）/`ADR-0004` R1–R3/`ADR-0016` S1 的**逐条 ADR 判定**仍待用户在 `SPEC-113t` 时执行。

**剩余未定项**：无（原 10 项已全部裁定）。**残留提醒（不改变裁定）**：`NUPERM/NJPERM/NSPERM/NHPERM` 在 `DADAO-12 §2.2` 属 **PTBR 权限**异常，与本轮"cfx 访问权限"（`§5` 异常进入流程）的关系，须在 `QEMU-044t`/`SPEC-114t` 落实时讲清；`ADR-0004` R3 的 RAM 基址是否随 bootrom 调整仍属 ADR 逐条判定项。


### 关联 issue（收口目标）

- `ISS-110`（cfx 指令/别名实现）—— 部分由 `SPEC-115t` + `LLVM-060t` 收口（`SPEC-075t` 的 uart2..30 别名缺口另计）。
- `ISS-157`（大小写不敏感未实现）—— `SPEC-116t` 以「条款撤销」结案。
- `ISS-147`（exit 码与 fault 区重叠）—— 随 `TESTCASES-034t`（exit-port 迁移）处置。
- `ISS-003`（M1 范围外：FP/特权 cfx/LR-SC）—— 特权 cfx 部分由本 M5 收口；FP/LR-SC 仍留。
- `ISS-160`（投影层残留）—— 可随 `SPEC-115t` 或另立 spec 任务刷新（待定）。

### 假设 / 边界

- 本 `k` 只做规划，不实现、不建 `t`/`m` 文件；门槛核验在 `INTEG-021m`（及 M5 项目里程碑）前完成。
- **`k` 的模块/编号**：已由用户裁定 = **`INTEG-019k`**（依 `spec/Process-04 §1`，M5 起 INTEG 开启）；`Process-04 §1` **无需修订**。
- 外部仓库（`DADAO-0628` / QEMU 上游 RISC-V）仅作**只读对照**（内容溯源，**非执行依赖**）。
- 任务书自包含：执行所需事实写入各任务书或引用 v5 自身知识（`spec/`/`contracts/`/`.tao/adr/`）。
- `F16` 大小写修订**撤销**（非新增）现有条款——须在 `SPEC-116t` 明确「条款撤销」措辞并更新投影/门控。

---

## 完成区

**测试结果**：N/A（`k` 规划任务，不实现代码）。门控影响：仅新增 `.tao/tasks/integ/INTEG-019k-*.md` 与追加 `.tao/knowledge/milestones.md`（纯文档，不在 `make check` 门控覆盖内，`AGENTS.md` 收尾检查 1 豁免）。

**本 `k` 产出**：

1. 本任务书 `.tao/tasks/integ/INTEG-019k-m5启动与分解.md`（自包含：问题根源/目的/已锁定边界 A–E/对照关系/任务分解/说明）。
2. `.tao/knowledge/milestones.md` 追加 **M5 行**（roadmap 表）+ **M5 说明**（目的/范围/门槛提案/范围外边界/前置 ADR 指针）。
3. **任务清单草案**：**15 `t` + 6 `m` = 21 份**（见 §任务分解表）。
4. **ADR 清单（决策提案）**：`ADR-0020`（新建，D1–D14）、`ADR-0004`（修订，R1–R3）、`ADR-0016`（范围，S1）——**逐条待用户判定**。
5. **待用户裁定项**：10 项，**已于 2026-10-07 第 2 轮逐条裁定**（见 §待用户裁定项清单 / §第 2 轮用户裁定）。

**修改文件**：

- `.tao/tasks/integ/INTEG-019k-m5启动与分解.md`（新增）
- `.tao/knowledge/milestones.md`（追加 M5 行 + M5 说明）

**验收结果**：待主会话 `/plan` 级交叉审查。

**新发现/坑（规划阶段实测）**：

1. **模块/编号冲突已裁定**：本指令原写「`SPEC-1xxk`」，与 `Process-04 §1`（M5 起 INTEG 开启）冲突；用户裁定采纳 **`INTEG-019k`**。
2. **共享层位置澄清**：共享**入口**在 `semihosting/arm-compat-semi.c`（`do_common_semihosting`），`include/semihosting/common-semi.h` 只**声明**之 + 声明 target 钩子；issue 描述「共享入口 `common-semi.h`」应理解为「共享层（声明在 `common-semi.h`、实现在 `arm-compat-semi.c`）」。
3. **`escape` 位宽口径**：`C14` 表述「编码 18 位（字节偏移）」与 `Toolchain-01 §3.2`（汇编 `imms20` 字节 ⇔ 编码 `imms18` 字偏移）措辞略异；`SPEC-115t` 须在 spec 写清「汇编层 `imms20`（字节，`%4==0`）⇔ 编码层 `imms18`（`>>2`）」。
4. **MMU 边界**（**第 2 轮已裁定**）：`D9` 的「权限异常 `NU/J/SP/HPERM`」来自 `§2.2` PTBR 权限，但 `§5` 的异常进入流程也含 cfx mask；**用户裁定权限范围 = 只做 `cfx0/1/2/3/63`**，`cfx_ptw`(=cfx4)/MMU/页表步进**不在本 M5** ⇒ 原「未定」消解（见 §待用户裁定项 4）。
5. **共享层 bank 假设（第 2 轮新增）**：共享层 `common_semi_arg(cs,n)` 假定同一组 `a0+n`（`target/riscv/common-semi-target.c:19` = `gpr[xA0 + argno]`），v5 三组分离 ⇒ 钩子须**按 `n` 选 bank**（`n=0`→`rd16`、`n=1`→`rb16`）、`set_ret`→`rd31`；落地 `QEMU-046t`、小适配非重写。

**遗留问题**：

- 原 §待用户裁定项清单 1–10 已全部裁定（2026-10-07 第 2 轮）；**`t`/`m` 任务书待 `/plan` 交叉审查本 `k` 后创建**。ADR decision（D1–D14/R1–R3/S1）逐条判定待 `SPEC-113t` 时由用户执行。

---

## 审阅记录

#### 第 1 轮 architect 规划自审

**自审范围**：本 `k` 的自包含性（问题根源/目的/已锁定边界/对照关系/任务分解）；任务草案编号规范（模块内递增、跨后缀共享）；依赖/串行链无环；ADR 判据（`Process-03`）与决策「不得预先 Accepted」；待裁定项完整覆盖用户所列 6 项。

**要点**：

- **编号**：`INTEG-019k`；各模块起始号 = M4 归档后最大号 +1（infra 047 / spec 113 / llvm 060 / qemu 044 / testcases 033 / integ 019），**跨后缀共享**（如 spec 117t 后 118m）。
- **用户口径**：A–E（1–17 条）**原样落盘**；`D1`–`D3` 分档、`exit port` 替代、`escape` 返回无指令、ARM 号值、复用共享层等关键措辞保留原话（含「退出的 escape 无需指令，直接执行」）。
- **对照关系**：含 0628 路线对照（`trap cfx_smon` + Linux syscall 号）与 QEMU RISC-V 共享层范式对照；均标「只读、非执行依赖」。
- **ADR 清单**：`ADR-0020`（D1–D13）/`ADR-0004`（R1–R3）/`ADR-0016`（S1）——**逐条待用户判定，未标 `Accepted`**。
- **覆盖核对**（用户要求「至少覆盖」）：install+落点（`INFRA-047t`/`048t`、`SPEC-117t`）✓；SEE/HEE QEMU（`QEMU-044t`）✓；新 bootrom 构建+链接+测试（`QEMU-047t`）✓；LLVM 4 条（`LLVM-060t`）✓；semihosting（`QEMU-046t` + `INTEG-020t`）✓；spec 正文（`SPEC-114t`/`115t`/`116t`）✓；门控收口（`INTEG-020t`）✓。
- **依赖无环**：`INTEG-019k`→Wave0→Wave1→Wave2→Wave3→Wave4→Wave5；反向依赖（实现←契约）单向。

**判决**：规划草案完成，交主会话 `/plan` 级交叉审查（含 reviewer）；**用户裁定项未定前不推进实现**。

#### 第 1 轮 reviewer 规划审查（2026-10-07，`/plan` 级交叉审查）

**审查范围**：对照 7 项审查清单，逐条核验 INTEG-019k + milestones.md M5 段。

**审查方法**：独立打开 spec/contracts 文件核实引用准确性；比对任务表/ADR 表/边界/裁定记录之间一致性；检查依赖图无环性与共享文件串行声明。

---

##### 1. 内部一致性

**结论：基本一致，2 处引用格式问题，1 处 D10 措辞与 spec §5 矛盾。**

- `test-see` 旧名：全文已统一为 `test-semihost`（目的段 L40、裁定 9 L104、任务表 L150、Wave5 L172）。✓
- `cfx` 范围：全文一致"只做 `cfx0/1/2/3/63`"（B9 L63、裁定 4 L98、任务表 `QEMU-044t` L144）。✓
- 服务集分档：全文一致"完整 25 个"（A3 L54、裁定 1 L91、ADR D3 L200、任务表 `QEMU-046t` L146）。✓
- 传参寄存器：全文一致 `rd16`/`rb16`/`rd31`（A2 L53、裁定 2 L92-96、ADR D2 L199、milestones.md L109）。✓
- **⚠️ D10（L207）措辞与 spec §5 矛盾**：D10 写「先过权限，允许则**直接服务**（不进入该 cfx 的向量）」。但 `DADAO-12 §5`（L698-720）异常进入流程明确规定 trap 指令**总是**经过步骤 1-10（含步骤 10「跳转至异常向量」）。spec 中 trap 的正常路径是：权限检查 → 模式切换 → **进入 cfx 向量** → handler 处理。semihosting 的"不进入向量"是 QEMU 实现层的特殊短路（trap 译码时识别 tag 后直接调 `do_common_semihosting`，类似 RISC-V 的 `RISCV_EXCP_SEMIHOST`），**不是 spec §5 定义的标准 trap 流程**。D10 需区分：(a) 一般 trap = 权限检查 → 进入 cfx 向量 → handler；(b) semihosting trap = QEMU 译码层短路 → 直接服务。当前措辞会让实现者误以为所有 trap 都"不进入向量"。
- **⚠️ `ADR-0004 R3`（L219）残留未分配**：R3 提到"RAM 基址是否调整仍属本 ADR 逐条判定项"，但任务表中**无任何 `t` 任务**承接 RAM 基址调整的实现。若 R3 判定需调整，当前分解无落点。

##### 2. 裁定落盘完整性

**结论：10 条裁定全部落到可执行位置，但 1 处引用格式错误。**

逐条核对：

| # | 裁定 | 任务表/ADR 表/边界落点 | 状态 |
|---|------|----------------------|------|
| 1 | 服务集=完整 25 + SYSTEM/HEAPINFO 都做 | `QEMU-046t`(L146) + ADR D3(L200) + A3(L54) | ✓ |
| 2 | 传参 rd16/rb16/返回 rd31 | ADR D2(L199) + A2(L53) + milestones L109 | ✓（但引用格式见下） |
| 3 | 共享层按 n 选 bank 适配 | ADR D14(L211) + `QEMU-046t`(L146) + A5(L56) | ✓ |
| 4 | 只做 cfx0/1/2/3/63 + CFXREG | `QEMU-044t`(L144) + B9(L63) + 裁定 4(L98) | ✓ |
| 5 | hypv→user 忽略 supv | `QEMU-047t`(L147) + B12(L66) + 裁定 5(L100) | ✓ |
| 6 | `-bios` + 复位向量不变 | `QEMU-047t`(L147) + B12(L66) + 裁定 6(L101) | ✓ |
| 7 | exit-port 全部迁移 | `TESTCASES-034t`(L149) + A8(L59) + 裁定 7(L102) | ✓ |
| 8 | ADR-0020 新建 | ADR ①(L194) + 裁定 8(L103) | ✓ |
| 9 | 门槛名 test-semihost | 目的段(L40) + 裁定 9(L104) + `INTEG-020t`(L150) | ✓ |
| 10 | 先 /plan 再建 21 份 | 裁定 10(L105) + L8/L131 | ✓ |

**⚠️ 引用格式错误**：裁定 2（L93）引用 `contract-abi §4.1` 和 `§4.4`——**`contract-abi.md` 文件不存在**（`contracts/` 下只有 `abi.yaml`，无 `§4.1`/`§4.4` 章节号）。`abi.yaml` 中 `rd16-rd31` 数据参数（L63）、`rb16-rb31` 地址参数（L75）、`rd31` 标量返回（L150）、`rb31` 指针返回（L151）的**数据内容正确**，但引用路径/章节号须修正（改为 `contracts/abi.yaml` + 对应行号或字段路径）。同样的问题出现在 ADR D2（L199）、L236、L343。

##### 3. 分解可执行性与依赖

**结论：无环、依赖真实可用；1 处遗漏依赖。**

- **无环验证**：Wave 0→1→2→3→4→5 严格分层，反向依赖（实现←契约）单向。✓
- **依赖真实可用**：所有依赖指向的任务均在任务表中存在。✓
- **共享文件串行**：L141（`SPEC-116t` 与 113-115 同改 `spec/` ⇒ 串行）、L162-173（Wave 描述）。✓
- **粒度**：15 `t` + 6 `m`，每个 `t` 可被单个 subagent 独立验收。✓
- **⚠️ `TESTCASES-033t`（L148）遗漏 `LLVM-060t` 依赖**：该任务产 MC 向量（`trap`/`escape`/`cfx2*`），编译这些向量需要 `LLVM-060t` 提供的 MC 编码支持。当前依赖只列 `SPEC-114t`、`SPEC-115t`、`INFRA-048t`，缺 `LLVM-060t`。若 `TESTCASES-033t` 的 L1 MC 向量用 `UNSUPPORTED:` 标记（L148 注释），则依赖可降级为"LLVM-060t 完成后去除 UNSUPPORTED"——但需在任务书里明确此分阶段策略。

##### 4. 与 spec/合同一致

**结论：核心断言有据；2 处引用需修正，1 处行号偏差。**

- **`DADAO-22:58`（CFXREG）**：✓ 已核实。原文「若 cfx 硬件不存在则触发 CFXREG 异常」（L58）。佐证 `DADAO-12:373`（`rc ≥ N` ⇒ CFXREG）和 `SimRISC-11:121`（不存在组合 ⇒ CFXREG）均正确。
- **`SimRISC-11 L80`（运行模式与 cfx 正交）**：⚠️ **行号偏差**。实际文本在 **L81**（`trap/escape/cfx2rd/cfx2rc/cfxld/cfxst 指令可以在任意运行模式下执行`），L80 为汇编器两种写法等价的说明。应修正为 `SimRISC-11 L81`。
- **`DADAO-12 §5`（异常进入流程）**：✓ 已核实。L648 起，步骤 1-10 完整。NUPERM/NJPERM/NSPERM/NHPERM 在 `§2.2`（L92，PTBR 权限检查第一步）定义，与 `§5` 的 cfx mask 权限检查是**两个不同层次**——文档 L252 残留提醒已标注此关系，足够。
- **`contract-abi §4.1/§4.4`**：❌ **文件不存在**。`contracts/` 下无 `contract-abi.md`。实际文件为 `contracts/abi.yaml`，无 `§4.1`/`§4.4` 章节。数据内容正确（见上），引用须修正。
- **`DADAO-12 §2.1`（复位向量）**：✓ L68 确认 `cfx_power_hypv_excp_vector` = `0xffff_ffff_0000`，64KiB。

##### 5. ADR/spec 分工

**结论：分工正确。**

- `SPEC-113t`（L138）：ADR 决策落地（`ADR-0020` 新建 + `ADR-0004` 修订 + `ADR-0016` 范围）。✓
- `SPEC-114t`（L139）：规范正文（`DADAO-12`/`DADAO-13`/`DADAO-22`/`DADAO-21` 相关 + 投影）。✓
- `SPEC-115t`（L140）：re-scope（`excluded`→已实现）。✓
- 用户明确"决策入 ADR、正文入 `spec/`"（E17 L81），任务表体现。✓

##### 6. 门槛可执行性

**结论：五部分可机器判定；exit-port 迁移与不回归的关系需在任务书里明确机制。**

- **正向**：bootrom + ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码 → 可机器判定（比对 stdout/stderr 内容 + exit code）。✓
- **权限反例**：未授权模式 ⇒ `NUPERM` 等 → 可机器判定（比对 QEMU 异常输出/退出码）。✓
- **服务表各条至少 1 例**：25 个服务各 1 例 → 可机器判定（计数）。✓
- **不回归**：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` → 可机器判定。✓
- **INTEG 开闭**：可机器判定。✓
- **⚠️ exit-port 迁移与不回归的关系**：`TESTCASES-034t`（L149）将 M1–M4 向量从 exit-port 迁到 `SYS_EXIT`。迁移后旧向量的"不回归"依赖**迁移正确性**——即 `SYS_EXIT` 的退出码/行为必须与原 exit-port 语义兼容（或向量期望值同步更新）。任务表未明确此保障机制。建议在 `TESTCASES-034t` 任务书里写明：迁移 = 改退出机制 + 同步更新期望值 + 迁移后全量重跑确认绿。

##### 7. 风险/遗漏

**结论：3 项需关注。**

1. **`bootrom` 构建/链接脚本归属**：`QEMU-047t`（L147）写"bootrom 固件源码 + 自有工具链构建/链接接入（`Makefile`）"，但未明确链接脚本（`bootrom.lds` 或类似）的地址布局。bootrom 加载到 `0xffff_ffff_0000`（64KiB ROM 区），链接脚本须与此对齐。建议在 `QEMU-047t` 任务书里明确链接脚本需求。
2. **harness stdio 捕获实现归属**：`INTEG-020t`（L150）写"harness stdio 捕获（`-semihosting-config` 默认值）"，但未说明具体实现方式。QEMU 的 `-semihosting-config` 需要 `chardev=` 指定 stdio 捕获目标。建议在任务书里明确：是通过 Makefile 传参、还是 QEMU 默认配置、还是 harness 脚本包装。
3. **`ADR-0004 R3` RAM 基址未分配**：R3（L219）提到"RAM 基址是否调整仍属本 ADR 逐条判定项"，但任务表无对应 `t` 任务。若 R3 判定需调整 RAM 基址（`0xffff_0000_0000`），当前分解无实现落点。建议：要么在 `SPEC-113t` 里明确 R3 的判定范围（仅讨论、不改实现），要么增加对应任务。

---

**判决：需修订**

**最小必改清单（3 项）**：

1. **修正 `contract-abi` 引用**：将所有 `contract-abi §4.1`/`§4.4` 引用改为 `contracts/abi.yaml` + 对应字段路径/行号（影响：裁定 2 L93、ADR D2 L199、L236、L343）。
2. **修正 `SimRISC-11` 行号**：`L80` → `L81`（影响：B9 L63 附近的引用）。
3. **澄清 D10 措辞**：D10（L207）"先过权限，允许则直接服务（不进入该 cfx 的向量）"与 spec §5（trap 总是进入 cfx 向量）矛盾。建议改为：「先过权限检查（mask 过滤）；对于 semihosting（`immu18[17:16]==2'b11`），QEMU 实现层在 trap 译码时短路，直接调 `do_common_semihosting` 服务（不走完整异常进入流程）；其它 trap 正常进入 cfx 向量。」

#### 第 2 轮 architect 更新（2026-10-07，第 2 轮用户裁定落盘）

**范围**：把用户本轮 10 条裁定（原话要点）与新事实写入本 `k` + `milestones.md` M5 段；**不建 `t`/`m` 任务书**（用户裁定：先 `/plan` 交叉审查本 `k`，再建 21 份）。

**改动**：

- 新增 §第 2 轮用户裁定（原话落盘，1–10 条）+ §已锁定边界 顶部指针；A2/A3/A5/A8、B9/B12 就地追加裁定标注。
- §待用户裁定项清单 10 项**逐条标注已裁定**（保留原问 + 裁定）；剩余未定项 = 无（残留提醒 2 条见该节）。
- ADR 表：D2/D3/D12 更新为新裁定值，**新增 D14 提案**（共享层适配点）；R1/R2/R3 更新为已裁定。
- 任务表：`QEMU-044t`（cfx 范围）/`QEMU-046t`（完整 25 + 适配点）/`QEMU-047t`（`-bios`、hypv→user）/`TESTCASES-034t`（迁移=全部）/`INTEG-020t` + Wave5（门控名 `test-semihost`）。
- 门槛名统一：`make test-see` → **`make test-semihost`**（目的段 / 待裁定项 8 / 任务表 / Wave5）。

**实测核实（证据）**：

- `spec/DADAO-22-SBI-主管系统二进制接口.md:58`：`SBI_SMON_PROBE_CFX` 行含「**若 cfx 硬件不存在则触发 CFXREG 异常**」（用户所指出处，已核实）。
- 佐证：`spec/DADAO-12-SEE-主管系统运行环境.md:373`（`rc ≥ N` ⇒ CFXREG）、`spec/SimRISC-11-其它.md:121`（不存在 `cfx_<name>_cgHB_rcHC` 组合 ⇒ CFXREG）。
- `contract-abi.md §4.1`（`rd16–rd31` 数据参数 / `rb16–rb31` 地址参数）、`§4.4`（标量返回 `rd31`、指针返回 `rb31`）——与裁定 2 一致。
- `.work/source/qemu/target/riscv/common-semi-target.c:19`（`common_semi_arg` = `gpr[xA0 + argno]`）、`semihosting/arm-compat-semi.c:395-396`（`nr = common_semi_arg(cs,0)`、`args = common_semi_arg(cs,1)`）——佐证裁定 3 的适配点。

**判决**：更新完成，待主会话 `/plan` 级交叉审查；**审查通过后再建 21 份任务书**。

#### 第 3 轮 architect 修订（2026-10-07，`/plan` 判决「需修订」处置）

**依据**：`/plan` 级交叉审查（第 1 轮 reviewer 规划审查，见上）判决 = **需修订**；用户逐条裁定处置口径。**范围**：就地修订本 `k`（+ `milestones.md` M5 段同源引用），**不建 `t`/`m` 任务书**，**不提交 git**。

**逐条处置**：

1. **② `SimRISC-11` 行号（必改）**：`L80` → **`L81`**。已核实：`spec/SimRISC-11-其它.md:81` = 「trap/escape/cfx2rd/cfx2rc/cfxld/cfxst 指令可以在任意运行模式下执行…」，`L80` 为汇编器两种写法等价的说明。影响：B9（L63）。
2. **③ `D10` 措辞（必改）**：改为**分清两条路**——(a) **一般 `trap cfxHA, immu18`**（`immu18[17:16] ≠ 2'b11`）：**走 spec 的异常进入流程**（`DADAO-12 §5`，含步骤 10「跳转至异常向量」）、**进入该 cfx 的向量**；(b) **semihosting**（`immu18[17:16] == 2'b11`）：**QEMU 译码层短路**（与 `RISCV_EXCP_SEMIHOST` 同构）、**不进入向量**、直接服务并按 PC 步进返回。已同步落点：ADR `D10`、`QEMU-045t` 范围、`QEMU-046t` 范围。
3. **① `contract-abi` 引用（采納但改正，reviewer 误判）**：reviewer 把「`contract-abi §4.1` 章节号」误当成「`contracts/` 下的文件」而判「文件不存在」；**实际 `.tao/knowledge/contract-abi.md` 存在（25394 B，含 `§4.1 参数寄存器` / `§4.4 返回值`）**。⇒ **保留引用目标**，正文引用补全为完整路径 `.tao/knowledge/contract-abi.md §4.x`；并在 §对照关系新增「v5 合约分两层」说明。**reviewer 记录中「文件不存在」的结论不成立**（本修订**不改写**其原文，仅在此登记）。
4. **`TESTCASES-033t` 依赖（关注项）**：依赖 += **`LLVM-060t`**；并写明 L1 MC 向量**分阶段**（`LLVM-060t` 就绪前以 `UNSUPPORTED:` 暂缓，完成后去除）。同步 Wave 4 / 反向依赖。
5. **`ADR-0004 R3`（关注项）**：在 `SPEC-113t` 的 ADR 逐条判定项中**显式列出**（RAM 基址是否随 bootrom 调整）并**注明归属**（仅判定/记录；本 M5 任务清单不承接实现，若判调整则后续另立任务）。
6. **细节归属（关注项）**：bootrom **链接脚本** → `QEMU-047t` 范围；harness **stdio 捕获细节** → `INTEG-020t` 范围（各一句话）。

**改动文件**：`.tao/tasks/integ/INTEG-019k-m5启动与分解.md`、`.tao/knowledge/milestones.md`（M5 段同源引用）。

**判决**：修订完成，待主会话 `/plan` 级复核；通过后再建 21 份任务书。

#### 第 2 轮 reviewer 复审（2026-10-07，第 3 轮修订后复审）

**复审范围**：仅核 `/plan` 判决「需修订」的 3 必改 + 3 关注，共 6 项。

**复审方法**：独立打开 spec 文件核实引用准确性；逐项 grep 任务文件确认改动落地。

---

##### ② 行号（`SimRISC-11` L80/L81）：**❌ 仍需修订**

**独立核实**：打开 `spec/SimRISC-11-其它.md`，逐行确认：

```
L78: 汇编器对两种写法等价处理，均编码为 6 位的 cfxha。
L79: (空行)
L80: trap/escape/cfx2rd/cfx2rc/cfxld/cfxst 指令可以在任意运行模式下执行，
     具体是否允许由各核芯功能扩展的 cfx mask 寄存器和指令类型 cfx mask 寄存器控制。
     详细异常路由规则见 SEE §5 异常进入流程。
L81: (空行)
L82: ### 陷入指令
```

**结论**：目标文本在 **L80**，不是 L81。第 1 轮 reviewer 的行号分析本身有误——其称「L80 为汇编器两种写法等价的说明」，实际那是 **L78**。architect 据此将 L80→L81 的修改**方向反了**。

**当前文件状态**：
- L63（B9）：写 `SimRISC-11 L81` → **应为 L80**
- 审阅记录 L379、L449 仍写 L81 → 但属历史引文，本轮不改审阅记录原文

**必改**：L63 的 `SimRISC-11 L81` → `SimRISC-11 L80`。

---

##### ③ D10 措辞：**✓ 通过**

L208 当前内容：

> D10：**(a) 一般 `trap cfxHA, immu18`**（`immu18[17:16] ≠ 2'b11`）：先过权限，允许则**走 spec 的异常进入流程**（`DADAO-12 §5`，含步骤 10「跳转至异常向量」）——**进入该 cfx 的向量**；(b) **semihosting**（`immu18[17:16] == 2'b11`）：**QEMU 译码层短路**（与 RISC-V `RISCV_EXCP_SEMIHOST` 同构）——**不进入向量**、直接服务并按 PC 步进返回（见 D4）。

**独立核实 `DADAO-12 §5`**：
- L676-703：异常进入流程步骤 1-10 完整
- L703（步骤 10）：「**跳转至异常向量**：跳转到 `cfx_⟨cfxname⟩_<mode>_excp_vector` 寄存器指示的异常处理程序地址」

**`QEMU-045t`/`QEMU-046t` 一致性**：
- `QEMU-045t`（L146）：「走 spec 异常进入流程（`DADAO-12 §5`）并进入该 cfx 的向量（**一般 trap**，`immu18[17:16] ≠ 2'b11`）」✓
- `QEMU-046t`（L147）：「**QEMU 译码层短路**：不进入 cfx 向量、直接服务并按 PC 步进返回」✓
- 两任务范围互斥且互补，与 D10 两条路一致。

---

##### ① 引用（`contract-abi`）：**✓ 通过**

**当前文件状态**（grep 全文 `contract-abi`）：
- L92：`.tao/knowledge/contract-abi.md §4` ✓
- L93：`.tao/knowledge/contract-abi.md §4.1` ✓
- L94：`.tao/knowledge/contract-abi.md §4.1` ✓
- L95：`.tao/knowledge/contract-abi.md §4.4` ✓
- L200（ADR D2）：`.tao/knowledge/contract-abi.md §4.1/§4.4` ✓
- L237（裁定 3）：`.tao/knowledge/contract-abi.md §4.1/§4.4` ✓

**引用目标未改**：仍是 `.tao/knowledge/contract-abi.md`（非 `contracts/abi.yaml`）。✓

**独立核实文件存在性**：`.tao/knowledge/contract-abi.md` 确实存在，含 `§4.1 参数寄存器`（L164：`rd16–rd31` 数据参数 / `rb16–rb31` 地址参数）和 `§4.4 返回值`（L192：标量返回 `rd31`、指针返回 `rb31`）。✓

**「两层合约」说明**：L118 新增说明：「`contracts/*.yaml` = 机器可读数据（无 `§` 章节号）；`.tao/knowledge/contract-*.md` = 合约正文（含 `§` 章节号）」。✓

---

##### 关注 4（`TESTCASES-033t` 依赖 + 分阶段）：**✓ 通过**

L149 当前依赖列：`SPEC-114t`、`SPEC-115t`、**`LLVM-060t`**、`INFRA-048t` ✓

交付物描述：「**分阶段**：`LLVM-060t` 就绪前 L1 MC 向量以 `UNSUPPORTED:` 暂缓，`LLVM-060t` 完成后去除 `UNSUPPORTED:`」✓

Wave 4（L172）：`TESTCASES-033t` ← `SPEC-114t`/`115t` + **`LLVM-060t`**（L1 MC 编码；`UNSUPPORTED:` 分阶段）✓

反向依赖（L176）：`TESTCASES-033t`←**`LLVM-060t`**（L1 MC 编码支持）✓

---

##### 关注 5（`SPEC-113t` + `ADR-0004 R3`）：**✓ 通过**

L139 `SPEC-113t` 交付物描述：

> **判定项显式含 `ADR-0004 R3`「RAM 基址是否随 bootrom 调整」**——**归属**：仅作 ADR 判定/记录；本 M5 任务清单**不承接** RAM 基址调整实现，若 R3 判需调整，由 `SPEC-113t` 记录结论并**后续另立任务**

归属明确：仅判定/记录，不承接实现，若需调整另立任务。✓

---

##### 关注 6（bootrom 链接脚本 + harness stdio 捕获）：**✓ 通过**

`QEMU-047t`（L148）已写入：

> `Makefile`；**含 bootrom 链接脚本**——地址布局对齐 `0xffff_ffff_0000` 的 64 KiB ROM 区、段序/对齐依 `ADR-0004`/`contract-elf`

`INTEG-020t`（L151）已写入：

> harness stdio 捕获（**细节展开**：`-semihosting-config` 的 `chardev=`/`target=` 由 Makefile 传参还是 harness 脚本包装；console 输出捕获到 stdout/stderr 的落点与比对）

两项均已在任务书范围中明确。✓

---

**判决：仍需修订**

**最小必改清单（1 项）**：

1. **L63 行号修正**：`SimRISC-11 L81` → `SimRISC-11 L80`。spec 文件中目标文本在 L80（非 L81），第 1 轮 reviewer 的行号分析有误（把 L78 的内容误归到 L80），architect 据此反向修改导致新错误。

**内部自洽性评估**：除行号这一处事实性错误外，INTEG-019k 在 D10 两条路区分、contract-abi 引用补全、TESTCASES-033t 依赖补全、SPEC-113t R3 归属、QEMU-047t 链接脚本、INTEG-020t stdio 捕获等 5 项均已正确修订，**内部自洽**。修正行号后即可据此建 21 份任务书。

#### 第 4 轮 architect 落点裁定与收尾（2026-10-07）

**范围**：把用户 2026-10-07 确认的两处落点写进任务书；同步 `milestones.md`；置状态 `已验证`。**（`/plan` 级交叉审查已通过。）**

**落点裁定（用户确认，原话要点）**：

1. **`QEMU-047t`（新 bootrom）**：**固件源码放 `tests/scripts/`**；**生成物放 `.dadao/` 下**（按落点规则：运行产物默认 `.dadao/tests/`；能靠配置解决的不算"难"）。已写入 `QEMU-047t` 的「输出」（item 1 源码落点、item 2 生成物落点）与「约束」（新增「落点」条 + 修正「补丁纪律」条原歧义表述 `tests/scripts/` 或 `hw/dadao/` 旁）；「验收标准」item 9 补「无残留/落点」核对。
2. **`SPEC-114t`（SEE/semihosting 规范正文）**：**正文落 `spec/Machine-01-测试机运行环境.md`（新建）**（用户确认前缀 `Machine`）；章节 ①内存映射/复位（引 `ADR-0004`）②运行模式（hypv/user，本版不启用 supv）③cfx 与权限（掩码/`switch_run_mode`/`CFXREG` 与四类 PERM 异常）④`trap`/`escape` 与异常进入流程 ⑤semihosting（`immu18[17:16]=11` 判定、25 服务表〔ARM 号值〕、传参 `rd16`/块指针 `rb16`/返回 `rd31`、PC 步进返回）⑥加载与 bootrom ⑦退出（`SYS_EXIT` 替代 exit-port）；并**登记 `spec/README.md`**。已写入 `SPEC-114t` 的「输出」（新增 item 1「规范正文落点」+ item 3 落点 + item 5「`spec/README.md` 登记与投影表同步」）；「验收标准」item 1/item 6 补落点核对。

**同步改动**：`milestones.md` M5 段追加「落点裁定」+「`/plan` 通过」两条；本 `k` §任务分解表 `SPEC-114t` 行「交付物」补入新建 `spec/Machine-01-测试机运行环境.md`。

**状态落实**：`/plan` 级交叉审查通过；第 2 轮 reviewer 复审的唯一最小必改项（`SimRISC-11` 行号）**已落实**——本 `k` B9（L63）现为 `SimRISC-11 L80`，经核实与 `spec/SimRISC-11-其它.md:80` 一致（L78 为「汇编器两种写法等价」说明，L80 才是「可在任意运行模式下执行」；第 2 轮 reviewer 复审已核实）。⇒ 本 `k` `**状态**` 置 **`已验证`**。

**判决**：规划落定；21 份任务书（15 `t` + 6 `m`）就绪，可进入 Wave 0（`INFRA-047t`）。

#### 第 4 轮 architect 提交留痕（2026-10-07）

- **档位**：**正常提交**（非 `WIP:`）——`INTEG-019k` 已置 `已验证`（`/plan` 级交叉审查通过）。
- **提交号**：`5e37de1`　`M5 规划：INTEG-019k（已验证）+ 21 份任务书（15t+6m）`（**仅本地 `commit`、未 `push`**）。
- **文件集对账**：显式 staging（逐个路径 `git add --`，**未用 `git add -A`**）；`git diff --cached --name-only`（`core.quotepath=false`）= **23** 条 = **22 任务书**（15 `t` + 6 `m` + `INTEG-019k`）+ **`.tao/knowledge/milestones.md`**；**漏提 0 / 多提 0 / 越界 0**（`.tao/` 之外 0 条；无 `spec/` 改动卷入；无并行会话改动）。`git diff --cached --stat` = `23 files changed, 1650 insertions(+)`。

#### 第 5 轮 architect 规划更新（2026-10-07，ADR 逐条裁定落盘）

**依据**：用户对 `SPEC-113t` ADR 判定清单**逐条裁定**（原话见 `SPEC-113t` §待用户逐条判定清单「四、用户逐条裁定结果」）。**范围**：本 `k` 的 ADR 表 / 任务表 / 依赖链同步 + `SPEC-113t`/`114t`/`QEMU-047t`/`QEMU-048m`/`TESTCASES-034t`/`INTEG-020t` 范围增补 + **新建 C1 step1 `QEMU-049t`** + `milestones.md` M5 段同步；**不写 ADR 正本**（归 `SPEC-113t`）、**不改 `spec/` 正文**（归 `SPEC-113t`/`114t`）、**不改 `QEMU-044t`**（D15 的机器模型部分归 `QEMU-049t`，异常进入流程引用 `QEMU-044t`）。

**裁定落点（要点，原话见 `SPEC-113t`）**：

1. **新增 `ADR-0020 D15`**：核内地址空间划分（RAM@0 / boot ROM / 旧 RAM 段 / exit port）+ **越界访问/取指报异常**（`CFXMEM`〔`DADAO-12 §2.1:73`，`1<<1`〕vs 测试机约定 `unmapped 0x87`；`ADR-0004 D5.8` 码表**冻结不重排**，`CFXMEM` ⇒ `0x81`，无需新码）⇒ 已写入 §ADR 清单 ① 表 D15 行。
2. **`D1`**：决策保留；**语义/理由说明**（`immu18[17:16]==2'b11`、无 spec 依据属架构自定义）落 `spec/Machine-01-*`（`SPEC-114t`），ADR 只留决策 ⇒ 已在 `SPEC-114t` 范围增补。
3. **`R1`**：`ADR-0004` 修订口径 = **`-bios` bootrom 与 M4 ELF 路径【并存】（非替代）** ⇒ 已更新 §ADR 清单 ② 表 R1 行。
4. **`R2`**：`SYS_EXIT` 取代 exit-port（`ADR-0004 D3`）⇒ R2 行确认。
5. **`R3`**：**RAM 基址改为全 0**（`0x0000_0000_0000`）；**C1 双映射两步**（step1 = M5 机器模型+bootrom；step2 = 另立、M5 之外）⇒ 已更新 R3 行 + 任务表新增 `QEMU-049t` + 登记 step2。
6. **`D2–D14`、`S1`**：按「**未特别指出 = 保留**」**推定**（**待用户复核**）⇒ 在原样写入 ADR 时按此推定。

**任务表新增（C1 step1）**：**`QEMU-049t`（RAM@0 双映射）** —— 机器模型**同时映射 RAM@0（新，供 bootrom/SEE）+ 保留旧 RAM 段** + RAM@0 链接基址 + **`check-interface` 断言新增 RAM@0 段（旧断言保留）**；依赖 `QEMU-044t`（同改 `hw/dadao/**` ⇒ 串行）；`QEMU-047t` 依赖 += `QEMU-049t`。**`QEMU-048m` 关联任务 += `QEMU-049t`**。**合计 21 → 22 份**（16 `t` + 6 `m`）。

**step1 与 `QEMU-047t` 的关系（架构师判断）**：**另立 `QEMU-049t`、串在 `QEMU-047t` 之前**（**非合并**）。理由：① **可独立验收**——RAM@0 双映射 + `check-interface` 断言可脱离 `LLVM-060t`/bootrom 独立门控（`QEMU-047t` 依赖链含 `LLVM-060t`，合并则受其阻塞）；② **Do One Thing**——「内存映射」与「固件构建」分属两类交付物；③ `QEMU-047t` 已较重，另立可降低其风险。**编号**：`QEMU-049t`（按模块现状顺延，`QEMU-048m` 之后；`QEMU-048m` 关联任务已同步含之）。**（备选/被否：并入 `QEMU-047t` —— 因耦合与阻塞，未采纳。）**

**step2 是否阻塞 M5 门槛（架构师判断）**：**不阻塞**。M5 门槛 = `make test-semihost` + 不回归（`test-elf`/`test-codegen`/`check`/`check-lit`）；step1 双映射**保留旧 RAM 段** ⇒ 既有测试仍绿；semihosting/SEE 正向路径走 RAM@0（step1 提供）。step2（迁移 + 删旧段 + 收紧断言）登记为**另立、M5 之外**（编号待 M6 规划/另立时确定）。**M5 里程碑须记明双映射为过渡态。**

**残留提醒（不改变裁定）**：`D2–D14`/`S1` 的「保留」为**推定**，待用户复核；`ADR-0004 D5.8` 码表若未来确需新增 fault 码，须说明依据（本轮 D15 未用新码）。

**判决**：本轮规划更新完成；`SPEC-113t` 据此写 ADR 正本（D1–D15 + R1–R3 + S1 落纸）。
