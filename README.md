# DADAO for SimRISC 0.5.4

基于 `spec/` 目录下的 19 份上游规范文档（SimRISC-00~12 + DADAO-11~23）与 v5 自定规范（`Toolchain-01`、`Process-0x`，索引见 `spec/README.md`），目标是覆盖 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持（**当前进度见 `.tao/knowledge/milestones.md`**）。

## 当前版本号

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.4 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |
| Toolchain | 1.1 |

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
