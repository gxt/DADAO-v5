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

- `llvm-mc` 可汇编/反汇编全部 M1 指令；`qemu-system-dadao` 在 MMU-off 裸机模式执行标量程序。
- MC→QEMU→结果比对闭环：向量 harness 747 total / 739 passed / 0 failed / 8 deferred。
- 向量覆盖 `validate_vectors.py`：178/178 identities、15 数据文件、gaps 0。
- 跨模块接口零不一致（`check_interface_alignment.py` 80/80/0）。
- `make check` EXIT 0；lit 25/25（MC 22 + E2E 3）；`check_qemu_trans` 256/256。
- 组件锁 `manifests/components.lock.toml`：LLVM/QEMU 以精确 commit 锁定（不用 tag/branch）。

### M2（2026-10-04）规范与接口冻结（Normative Freeze）

- `spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层机械一致。
- 投影表「缺口」清零或显式 deferred（4 项）。
- `check-spec-refs` EXIT=0（Check1 680 引用 / 0 失败）。
- FP 实现侧收口：执行层 60/60 + `dst_rd0@FP` + 最小 FP smoke。
- 偏离台账成型（6 项，`.tao/knowledge/MEMORY.md`）。
- `make check` EXIT=0；lit 31/31。

### M3（2026-10-05）Basic CodeGen（纯整数）

- `llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编。
- `make test-codegen` EXIT=0；15/15（算术/访存/分支/调用 + 大端窄访存 + `ptr−ptr`）。
- 端到端：单 TU obj/raw binary → `qemu-system-dadao` 执行结果正确（freestanding、无链接器）。
- 寄存器 bank 只用 `GPRD`（i64 数据）+ `GPRB`（ptr 地址）；`RA`/`RF` 仅「保留不分配」。
- `make check` EXIT=0；lit 34/34。
- 补丁集一致 `check-patch-tree` 80 patches OK（llvm 48 + qemu 32）。

### M4（2026-10-07）ELF 文件支持 + LLD 链接 + 汇编器遗留收口

- 工具链从「raw-bin 单 TU 捷径」升级为「规范 ELF 产出 + `ld.lld` 链接 + QEMU ELF 加载」（`llc→llvm-mc→ld.lld→ET_EXEC→qemu`）。
- `make test-elf` EXIT=0（5/5：多 TU + 多段 + 跨 TU call/全局地址/loop/`ptr−ptr`）。
- 汇编器遗留收口（伪指令 / `.dd.*` 指导符 / `-multiple-to-single` / 越界立即数报错 / ABI 寄存器别名）。
- 新增 DADAO LLD target（`lld/ELF/Arch/DADAO.cpp` + `EM_DADAO`/reloc，产 `ET_EXEC`）。
- M3 链不回归（`test-codegen` 15/15）；M3 15 向量经新 ELF 链 vs raw-bin **0 分歧**。
- lit 60/60；补丁集 89 patches OK；负例（畸形 ELF / reloc 溢出）非零退出。
- 自 M4 起 TDD：先立测试向量/门控、再实现（`spec/Process-05`）。

### M5（2026-10-08）SEE/HEE 运行环境 + semihosting

- QEMU 从「裸机、无 syscall、`exit port` 停机」升级为「SEE/HEE 运行环境 + semihosting」。
- 实现四运行模式与 cfx 寄存器的权限/掩码/`switch_run_mode`/权限异常；新 bootrom（自有工具链编、`-bios` + bin）。
- semihosting：`trap`（tag = `immu18[17:16]==2'b11`）走 QEMU 共享层 `do_common_semihosting`（ARM 号值）。
- **`SYS_EXIT` 取代 `exit port`** 作停机协议；LLVM 实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`。
- 端到端门控 `make test-semihost` 五组成全绿（console 逐字节 + 4 cfx 级权限反例）；25 服务全覆盖。
- `make check` EXIT=0；补丁集 92 patches OK；接口对齐 85 项 PASS。
- `SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred。

### M6（2026-10-11）整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench

- 整数完整调用约定（返回 `rd8`/`rb8`/`rf8`、聚合 ≤ 64 B、`sret`/变参/间接调用）。
- FP/RF codegen 落地；reloc 体系（`REL12`/`ABS12`）+ ABI 寄存器布局重排。
- 打通 DADAO **clang target**（仅 freestanding）；QEMU 改走 **`load_elf()`** 取代 raw-bin。
- 接入 **Embench**：19 基准 `-O0`/`-O2` 双 **19/19**（判据 guest exit 0，0 FAIL）。
- 新增 opt-in `make test-m6`：`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench **38/38**。
- `make check` EXIT=0（lit 89/89）；补丁集 109 patches OK。
- `embench-iot` 新增组件锁（commit `09c2ed8c…`、`enabled=true`，`ADR-0022 D2`）。
