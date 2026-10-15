# musl 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M8

- **2026-10-15 `INFRA-082t`（阶段 A2+A3）**
  - 摘要：**建 DADAO 移植补丁集 + 锁条目补丁化 + 静态最小程序可编出**。新增 `components/musl/{README.md,changelog.md,patches/**,series}`（树形补丁、一文件一补丁）；补丁 = `arch/dadao/**`（12：`syscall_arch.h`/`crt_arch.h`/`reloc.h`/`pthread_arch.h`/`atomic_arch.h`/`kstat.h`/`arch.mak` + `bits/{alltypes.h.in,float.h,setjmp.h,signal.h,syscall.h.in}`）+ `src/setjmp/dadao/{setjmp.S,longjmp.S}` + `src/thread/dadao/__set_thread_area.s` + `configure`（加 `dadao*) ARCH=dadao`）；锁条目**去掉 `patchless`**、补 `patch_dir`/`patch_series`、`role` 同步（同一提交）。**移植口径**：号表沿用 RISC-V（号在 `rd15`、返回 `rd8`、errno 负值，`contract-syscall.md`）、参数按类型分 bank（整数 `rd16+` / 指针 `rb16+`，按号恢复指针槽位）、`TP = rb3`（`TLS_ABOVE_TP`、无偏置）、crt 静态构造 `argc/argv/auxv` 帧、`setjmp` 真保存 RegRAS + callee-saved 161 octa。**A3 出口**：`tools/infra/build_musl.py` 构出 `libc.a`+`crt1.o` 并链出静态 `ET_EXEC`——`ELF 64-bit MSB, machine 0xDA0 (DADAO), statically linked`，入口 `0xfc0000000000`。**已登记边界**：原子（LR-SC/`fence` 未实现 ⇒ 单线程语义）、`GETFUNCSYM`（内存操作数 inline asm 后端崩）、`arch.mak` 后端受阻源过滤（`rotl/rotr`/`bswap`/`dynamic_stackalloc`）、`bits/signal.h` 信号帧 `[OPEN]`、无 `AT_PHDR` ⇒ 静态 `__thread` 未打通；运行（`dadao-m1` E2E）属阶段 B。
  - 执行者：engineer
