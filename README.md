# DADAO for SimRISC 0.5.4

基于 `spec/` 目录下的 19 份上游规范文档（SimRISC-00~12 + DADAO-11~23）与 v5 自定技术规范（`Toolchain-01`、`Machine-01`，索引见 `spec/README.md`；工程流程规范 `Process-0x` 见 `docs/`），目标是覆盖 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持（**当前进度见 `.tao/knowledge/milestones.md`**）。

## 当前版本号

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.4 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |
| Toolchain | 0.5.0 |
| Machine | 0.3.0 |

版本号取自 `spec/` 各文档头部的 `> **版本：X.Y.Z**`。同步要求：AEE ↔ ABI、SEE ↔ SBI、HEE ↔ HBI 必须一致，全部基于同一 SimRISC 版本号。

## 项目里程碑

> 已完成里程碑（M1–M6）；当前进度见 `.tao/knowledge/milestones.md`。成就事实取自 `.tao/archive/M*/m*-retrospective.md`。

| 里程碑 | 达成日 | 主题 |
| --- | --- | --- |
| M1 | 2026-09-22 | MC + QEMU 标量核心 + MC↔QEMU 集成 |
| M2 | 2026-10-04 | 规范与接口冻结（Normative Freeze） |
| M3 | 2026-10-05 | Basic CodeGen（纯整数） |
| M4 | 2026-10-07 | ELF 文件支持 + LLD 链接 + 汇编器遗留收口 |
| M5 | 2026-10-08 | SEE/HEE 运行环境 + semihosting |
| M6 | 2026-10-11 | 整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench |

### M1（2026-09-22）MC + QEMU 标量核心 + MC↔QEMU 集成

- `llvm-mc` 可汇编/反汇编全部 M1 指令（L1 编码 oracle 68/68）。
- `qemu-system-dadao` 在 MMU-off 裸机模式执行标量程序（`check_qemu_trans` 256/256）。
- MC→QEMU→结果比对闭环：747 向量，739 passed / 0 failed；覆盖 178/178 + 跨模块接口 80/80。

### M2（2026-10-04）规范与接口冻结（Normative Freeze）

- `spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层机械一致；投影表缺口清零 / 显式 deferred（4 项）。
- FP 实现侧冻结：执行层 60/60 + `dst_rd0@FP` + 最小 FP smoke。
- 上游 ↔ v5 偏离台账成型（6 项）。

### M3（2026-10-05）Basic CodeGen（纯整数）

- `llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编（`test-codegen` 15/15：算术/访存/分支/调用 + 大端窄访存 + `ptr−ptr`）。
- 产出单 TU obj/raw binary（freestanding、无链接器）；bank 只用 `GPRD`（i64 数据）+ `GPRB`（ptr 地址）。
- `qemu-system-dadao` 端到端执行结果正确（MC→obj/raw→QEMU）。

### M4（2026-10-07）ELF 文件支持 + LLD 链接 + 汇编器遗留收口

- 工具链从「raw-bin 单 TU 捷径」升级为「规范 ELF 产出 + `ld.lld` 链接 + QEMU ELF 加载」——`llc→llvm-mc→ld.lld→ET_EXEC→qemu`（`test-elf` 5/5；新增 DADAO LLD target）。
- 汇编器遗留收口（伪指令 / `.dd.*` 指导符 / `-multiple-to-single` / 越界立即数报错 / ABI 寄存器别名）。

### M5（2026-10-08）SEE/HEE 运行环境 + semihosting

- QEMU 从「裸机、无 syscall、`exit port` 停机」升级为 **SEE/HEE 运行环境**：四运行模式 + cfx 权限/掩码/`switch_run_mode`/权限异常 + 新 bootrom。
- semihosting：`trap`（tag `immu18[17:16]==2'b11`）走共享层 `do_common_semihosting`（ARM 号值）；**`SYS_EXIT` 取代 `exit port`**；console 逐字节（LLVM 侧 `trap`/`escape`/`cfx2rc`/`cfx2rd`）。
- 端到端门控 `make test-semihost` 五组成全绿（含 25 服务全覆盖）。

### M6（2026-10-11）整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench

- 三根钉子：DADAO **clang target**（仅 freestanding）+ QEMU 改走 **`load_elf()`** 取代 raw-bin + 接入 **Embench**。
- 整数完整调用约定（返回 `rd8`/`rb8`/`rf8`、聚合 ≤ 64 B、`sret`/变参/间接调用）。
- FP/RF codegen 落地；reloc 体系（`REL12`/`ABS12`）+ ABI 寄存器布局重排。
- 测试资产与门控：opt-in `make test-m6`（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）。
- LLVM 欠账 / 缺口收口（大帧寻址、分支放宽、跳转表、对齐 NOP、clang 小聚合 ABI 等）。

## 上游 ↔ v5 偏离台账

> **归一化登记 7 项**上游 spec 与 v5 决策之间的**规范性偏离**（M2 门槛⑤成型；`SPEC-106t` 增至 7 项）。每项均由**已 `Accepted` 的 ADR**（或 M1→M2 过渡任务 `SPEC-086t`）固化；本节只做**归一化登记 + 指针**，不新增决策，权威决策见 `.tao/adr/`。`scope`、`RACNT`、`MRPTR`、exit 码等写法与 `contracts/opcodes.yaml`、ADR 一致。

| # | 偏离点 | 上游依据 | v5 决策 | ADR / 契约指针 |
|---|--------|----------|---------|----------------|
| 1 | **exit port（程序停机）** | `SimRISC-11 §退出指令`：`escape cfxHA, [excp_cause_ip, imms20]`（**退出特权态**，非停机；编码层 `imms18`） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠 halt） |
| 2 | **`fence` SBZ 非零** | `SimRISC-12 §fence指令`：`immu18 bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1）；`contracts/opcodes.yaml::fence_oiii_imm` |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2.1` 仅给核内地址空间模型，无内存映射 / 复位值全集 / exit 协议） | 采用 spec 核内地址空间模型（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；`rd0`/`rb1`–`rb63`/`ra0`–`ra63`/`rf1`–`rf63` 复位 `0`、`rf0` 复位 `0x7FF8_0000_7FC0_0000`（架构自定义确定性复位） | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`（v5 修订前；对照归档 `.tao/archive/SimRISC-0.5.3/SimRISC-00`）：`ra0` 高 16 位 = **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段）；投影 `contract-elf.md §1.3` |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-07`）、特权 cfx（`SimRISC-11 §特权指令` + `DADAO-12/13`）、LR-SC（`SimRISC-12 §LR-SC指令`）、`fence`（`SimRISC-12 §fence指令`）均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 60 条已实现（不再是 ILLI）**；`excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence excluded）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`） |
| 7 | **汇编伪指令集收缩**（删上游 5 类伪指令） | `SimRISC-0.5.4 §伪指令`：定义 18 条伪指令，含 `nop`/`return`/`not.{b,w,t,o}`/`neg.{b,w,t,o}` 共 10 条 1:1 别名 | v5 只保留「ISA 无法直接表达、需多指令合成」的 **8 条合成型**（`set.rd`×2/`set.rb`×2/`set.ft`×2/`set.fo`×2）；删除 10 条 1:1 别名（`nop`→`swym 0`、`return`→`ret rd0, 0`、`not.*`→`xnor.o`、`neg.*`→`sub.sX`）；`ret` 不加无参形态；反汇编只显真实指令 | **ADR-0013 §D11** |

> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。
>
> **章节订正（实测）**：任务书/`docs/m2-spec-planning.md` 沿用 **SimRISC 0.5.3 编号**；v5 现行规范为 **0.5.4**，章节已重排——上游依据「exit port vs `escape`」现位于 `SimRISC-11 §退出指令`（0.5.3 为 `SimRISC-04`）、`fence` SBZ 位于 `SimRISC-12 §fence指令`（0.5.3 为 `SimRISC-04`）、浮点规范为 `SimRISC-07`（0.5.3 为 `SimRISC-03`）。均以 `contracts/opcodes.yaml` 的 `spec_cite` 实测为准。
