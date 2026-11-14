# Linux 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M14

- **2026-11-13 `m14-linux-001`**
  - 摘要：**组件转正：去 `patchless`、建空补丁集首态**。锁条目新增 `patch_dir = "components/linux/patches"` / `patch_series = "components/linux/series"`，`role` 改为「Linux 内核移植目标（`arch/dadao`）+ syscall 号表参考」；基线（`7.2.10` / `7b20d05f…` / `shallow_ref = v7.2.10`）与 `source[]` 不变。新增本目录 `README.md`/`changelog.md`/`series`（零条目）/`patches/.gitkeep`；**首个补丁由 `m14-linux-002` 落地**。空补丁集成为合法首态由 `docs/Process-01 §2/§8` 登记（`series` 零条目 + `patches/` 无 `.patch` + `.gitkeep` 至多一个 且仅空 `series` 时合法），E1 期望条数随之为 `base+0`；非空补丁集的 `base+1` 口径不放宽。

- **2026-11-14 `m14-linux-002`**
  - 摘要：**`arch/dadao` K0 最小骨架，`make ARCH=dadao … vmlinux` 出镜像（不启动）**。56 份树形补丁（全部 `arch/dadao/**`；上游文件零改动）：`Kconfig`/`Kconfig.debug`/`Makefile`/`configs/defconfig`、`kernel/{head.S,vmlinux.lds.S,setup.c,traps.c,syscalls.c,syscall_table.c,early_console.c,asm-offsets.c,Makefile}`、`mm/init.c`、`lib/delay.c`、`include/{asm,uapi/asm}/**`。链接地址/入口 = `0x0200_0010_0000`、`p_vaddr = p_paddr + 2 TiB`、64 KiB 页两级页表（`spec/DADAO-12 §2.2`）；产物断言与代码跨度护栏进 `tools/linux/make_vmlinux.py`。K0 关：SMP/DTB/UART/PCI/模块/`CONFIG_KALLSYMS`（kallsyms 发射用 GAS `.long/.short`，DADAO 汇编器不受理）。

- **2026-11-14 `m14-linux-003`**
  - 摘要：**K1：在 Vast 上进入 `start_kernel` 并按 2026-11-14 裁定在开时钟前退出**。`arch/dadao/kernel/head.S` 在首次压栈前自建 16 KiB early stack、把 §5 的 `rb16`/`rb17` 存进 `dadao_entry_va`/`dadao_bootinfo_va`、按 `contract-linux-boot §4` 校验 boot info 的 `magic`/`version`/`size`（失败交 `dadao_bootinfo_reject()` 具名打印后 `SYS_EXIT`，码 `0xE1`/`0xE2`/`0xE3`）；随后进 C 的 `dadao_start_kernel()`：解析并打印全部 15 字段 + 运行时 SP，交 `start_kernel()`。`init/main.c` 在 `start_kernel()` 首句插入 `dadao_k1_early_stop()`（新 `CONFIG_DADAO_K1_EARLY_STOP`，默认 y，K2 起关掉即恢复上游语义），打印 `start_kernel` 标记、RAS 返回地址（落在 `start_kernel` 内）与 SP 后 `SYS_EXIT(0)`；此时无任何子系统/时钟/中断被初始化。early console = semihosting（服务号 `rd16`、参数块 `rb16`、指针为 **PA**；`SYS_WRITEC` 逐字节输出）。另修 K0 遗留：`br.eq {rb2,rb3}`（`br.eq` 只比较 rd 寄存器）、semihosting 服务号误放 immu18、失败码 `0x100+` 会回绕成宿主 0。新增 `tools/linux/k1_boot_probe.py`（P1–P7 + `--neg magic|size`）；`tools/qemu/k0_boot_probe.py::build_firmware` 增加 K1 变体参数（`hmon_src`/`hmon_defs`/`smon_defs`/`name`）。
