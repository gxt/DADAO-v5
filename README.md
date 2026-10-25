# DADAO for SimRISC 0.5.5

基于 `spec/` 目录下的 19 份上游规范文档（SimRISC-00~12 + DADAO-11~23）与 v5 自定技术规范（`Toolchain-01`、`Machine-01`，索引见 `spec/README.md`；工程流程规范 `Process-0x` 见 `docs/`），目标是覆盖 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持（**当前进度见 `.tao/knowledge/milestones.md`**；**上游↔v5 偏离台账见 `.tao/knowledge/MEMORY.md`**）。

## 当前版本号

| 组件 | 已发布版本 | 在研版本（`-rc`） |
|------|-----------|------------------|
| SimRISC | 0.5.5 | 0.5.6-rc |
| AEE / ABI | 0.9.2 | 0.9.3-rc |
| SEE / SBI | 0.7.1 | 0.7.2-rc |
| HEE / HBI | 0.1.2 | 0.1.3-rc |
| Toolchain | 0.5.3 | 0.5.3 |
| Machine | 0.3.0 | 0.3.0 |

「**已发布版本**」＝ `spec/` 各册**最近一次正式发布版本**（见各册文末「附录：版本与变更记录」，注意**非**册头在研版本），也是合约（`.tao/contracts/contract-*.md`）投影的版本（`check-spec-drift` 以此列比对）；「**在研版本**」＝ 各册文末「附录：版本与变更记录」顶部累积段（自上次发布后**确有内容改动**者为 `<z+1>-rc`，否则与已发布版本相同；口径见 `spec/README.md`「册维护约定」）。同步要求：AEE ↔ ABI、SEE ↔ SBI、HEE ↔ HBI 组内版本必须一致，全部基于同一 SimRISC 版本号。

## 项目里程碑

> 已完成里程碑（M1–M9）；当前进度见 `.tao/knowledge/milestones.md`。成就事实取自 `.tao/archive/M*/m*-retrospective.md`。

| 里程碑 | 达成日 | 主题 |
| --- | --- | --- |
| M1 | 2026-09-22 | MC + QEMU 标量核心 + MC↔QEMU 集成 |
| M2 | 2026-10-04 | 规范与接口冻结（Normative Freeze） |
| M3 | 2026-10-05 | Basic CodeGen（纯整数） |
| M4 | 2026-10-07 | ELF 文件支持 + LLD 链接 + 汇编器遗留收口 |
| M5 | 2026-10-08 | SEE/HEE 运行环境 + semihosting |
| M6 | 2026-10-11 | 整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench |
| M7 | 2026-10-13 | picolibc 移植（自带 test）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle |
| M8 | 2026-10-19 | 无内核 Linux 用户态栈：musl 静态→动态 + QEMU user-mode（`ADR-0025`） |
| M9 | 2026-10-24 | FP 完备性 + 线程支持 + ISA 收口（发布 SimRISC 0.5.5） |

### M1（2026-09-22）MC + QEMU 标量核心 + MC↔QEMU 集成

- `llvm-mc` 可汇编/反汇编全部 M1 指令（L1 编码 oracle 68/68）。
- `qemu-system-dadao` 在 MMU-off 裸机模式执行标量程序（`check_qemu_trans` 256/256）。
- MC→QEMU→结果比对闭环：747 向量，739 passed / 0 failed；覆盖 178/178 + 跨模块接口 80/80。

### M2（2026-10-04）规范与接口冻结（Normative Freeze）

- `spec/`（0.5.5）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层机械一致；投影表缺口清零 / 显式 deferred（4 项）。
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

### M7（2026-10-13）picolibc 移植（自带 test）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle

- picolibc 全量移植并集成（`build-picolibc`）；自带 test 达成 **`total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`**（用户 2026-10-12 裁定「记为达成（推荐）」）。
- FP 后端 P0/P1 补齐（`f32→f64` 载入 / `setcc` / `bitcast` / `select_cc` / `cttz`；取整六项 / `fmin-fmax` / `fabs-copysign`）+ 谓词 / `"r"` 内联汇编 / f32 libcall / 截断存储分批收口。
- 生成式 **ISA↔后端覆盖矩阵**（227 条：①受理 217 / ②ISel yes 86）。
- **门控分层 L1/L2/L3**（`docs/Process-07`）+ **过渡 oracle**（宿主机参照，登记「非判据真源」）。
- 归档与回顾见 `.tao/archive/M7/`（`README.md` / `m7-retrospective.md`）。

### M8（2026-10-19）无内核 Linux 用户态栈：musl 静态→动态 + QEMU user-mode

- musl 1.2.6 **静态 + 动态**两档可编可跑：`libc.so` / `ld-musl-dadao.so.1` / `PT_INTERP` / GOT·PLT / PIC（`QEMU-062t` 两档 E2E）。
- `qemu-dadao`（user-mode）承接 syscall 直通与动态装载；`P4`（RISC-V 交叉对照）由用户 2026-10-18 裁定**不作**。
- ABI/后端收口：`long double` = **binary128**（`ADR-0030`）、变参三游标（`ADR-0031`）、**SP 16 B 对齐**、`rb2` 帧指针、`@@` 注释符、`brind`/f128 libcall/i32 窄返回。
- 三套大型测试两档如实分类（权威跑）：`embench-iot` 38/38 + 38/38；`libc-test` 静态 `309/0/4/24`、动态 `312/0/4/21`；`llvm-test-suite` 两档同 `201/3/0/16/2`；失败逐条归因（`ISS-265` 等）。
- 门控 L1/L2/L3 全绿；归档与回顾见 `.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。

### M9（2026-10-24）FP 完备性 + 线程支持 + ISA 收口（发布 SimRISC 0.5.5）

- **浮点能力补齐（前端可直接用）**：融合乘加 `fma`（单次舍入）、最小/最大值、取整六档、分类（`is.fpclass`）、`remainder`、`ldexp`、舍入模式读写、饱和转换；`fma`/`fmin`/`fmax`/`fabs`/`copysign`/`rint` 等 C 库函数调用**各 1 条指令、无 libcall**。
- **线程与 TLS 可用**：musl 端口补齐 `clone`，`pthread_create`/`pthread_join`/`posix_spawn` 可用；`__thread` 静态 TLS 与动态 TLS（含 `dlopen`）打通；`libc-test` 中原被阻塞的 20 例线程用例全部通过（仅 `pthread_create-oom` 这类 OOM 边界用例仍受限）。
- **整数与位操作**：8/16/32 位窄指令启用（`add.st/sw/sb` 等各 1 条，不再一律按 64 位算）；`clz`/`ctz`/`popcount`/`bswap` 各 1 条（原来分别要 10 条、7 条）；结构体/小数组拷贝用多寄存器 `ldm`/`stm` 合并。
- **原子与内存序**：`fence` 与 `lr`/`sc` 全部实现（核芯功能扩展 `cfxld`/`cfxst` 仍保留未实现）。
- **发布与验收**：SimRISC **0.5.5**；三套大型测试两档复跑 **0 fail**（`embench-iot` 38/38；`libc-test` 静态 331 / 动态 338 pass；`llvm-test-suite` 静态 204 / 动态 203 pass）。
- 归档与回顾见 `.tao/archive/M9/`（`README.md` / `m9-retrospective.md` / `issues-closed.md`）。
