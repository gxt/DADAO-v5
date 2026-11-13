# m14-linux-002: `arch/dadao` 最小骨架出 vmlinux

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-spec-001`（装载/入口/boot info 契约）、`m14-infra-001`（工具链选择与规避法）、`m14-linux-001`（补丁集组件形态）
**可并行分片**：否（同一补丁集、同一构建树；`arch/dadao` 单写者）
**预估**：6–7 h
**状态**：待开始

## 背景

`linux` 已成为受补丁组件（`m14-linux-001`），但补丁集为空。K0 的入口判据之一是「`arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux」。本任务只要求**链接出可解析的 vmlinux**，**不要求能启动**：不声称 console/memblock/trap/initramfs/userspace 可用。

入口/内存/装载规则以 `m14-spec-001` 冻结的契约为唯一依据，**但内核 VA 窗口已由用户 2026-11-13 修订为 `[2 TiB, 3 TiB)`**（`m14-spec-003` 负责改 spec）：内核链接/入口 = **`0x0000_0200_0010_0000`**、boot info = `0x0000_0200_0001_0000`、initramfs = `0x0000_0200_0400_0000`；用户空间 `[0, 2 TiB)`；映射为 `VA = PA + 2 TiB`；工具选择以 `m14-infra-001` 的矩阵为唯一依据。**不得**从 0628 的 `arch/dadao` 复制代码/补丁。

## 目标

1. 以**树形补丁集**落地最小 `arch/dadao/**`（一文件一补丁、series 字典序），至少含：
   - `arch/dadao/Kconfig`（最小 `config DADAO`，供 `ARCH=dadao` 选择）；
   - `arch/dadao/Makefile`（`KBUILD` 钩子 + `core-y`/`libs-y` 最小集）；
   - `arch/dadao/configs/defconfig`（最小配置：单核、无 SMP、无 MMU 高级特性、无设备树/DTB、semihosting 控制台 stub 开）；
   - `arch/dadao/kernel/head.S`（入口 `_start`/`dadao_start`：自建 early stack、清零 `__bss_start..__bss_stop`（raw 路径需要）、校验 boot info magic/version/size（失败走 semihosting `SYS_EXIT` 的固定失败码）、随后进入最小 C 入口）；
   - `arch/dadao/kernel/vmlinux.lds.S`（链接地址/入口 = `0x0000_0200_0010_0000`，`PT_LOAD` 规则按 spec-001；`__bss_start/_end` 等符号）；
   - `arch/dadao/kernel/setup.c` + early console stub（semihosting `SYS_WRITE0`，仅编译链接，K0 不执行）；
   - 链接所需的最小 arch 头/符号（按真实链接错误逐项补齐，**不得**批量塞「永不调用的空 stub」掩盖缺口）。
2. 构建包装：`tools/linux/make_defconfig.py` / `tools/linux/make_vmlinux.py`（目标 `make linux-defconfig` / `make linux-vmlinux` 已由 `m14-linux-001` 声明）；使用 `tools/linux/paths.py` 解析源树/构建树，工具来自 `m14-infra-001` 矩阵。
3. 产物断言：`vmlinux` 为 ELF64 大端、`e_machine = 0x0DA0`、`e_entry = 0x0000_0200_0010_0000`、仅 `PT_LOAD`、`p_vaddr = p_paddr + 2 TiB`（VA 与 PA 差固定偏置）、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、段落在 `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`；`llvm-nm -u vmlinux` 为空。
4. 补丁集可重建：`make apply-series` 在干净 base 上得到 `base+1`，`make check-patch-tree` / `make check-source-state` 绿。

## 接口规范

- **构建命令（仓库级，不写运行期路径）**：`make linux-defconfig` → `make linux-vmlinux`；两者均为写者目标（已在 `GATE_LOCKED_TARGETS`），失败须非零退出并打印下一步（`make install-host` / `make fetch apply-series`）。`linux-vmlinux` 内部必须真实执行 `make ARCH=dadao … vmlinux`（构建日志贴出该命令行与退出码），不得用宿主对象伪造产物。
- **工具选择**：`CC=clang --target=dadao-unknown-elf`、`LD=ld.lld`、`NM/OBJCOPY/OBJDUMP` 用安装根对应工具；`AR/RANLIB/STRIP` 按 `m14-infra-001` 矩阵的 present/absent + workaround 选择（矩阵未覆盖的不得自选）。
- **补丁集文件名**：严格 `<上游相对路径>.patch`（如 `arch/dadao/kernel/head.S.patch`），`new file mode` + 全文 `+` 行；`series` 按路径字典序；一文件一补丁。
- **入口符号**：`arch/dadao/kernel/head.S` 的 `_start`（或 `dadao_start`）必须与链接脚本 `ENTRY()`、ELF `e_entry` 一致；`m14-infra-003` 的门控会从契约投影取期望值核对。
- **boot info 校验**：`magic == 0x4442_494E`、`version == 1`、`size >= 0x60`；字段按 spec-001；失败码自定但须在完成区记录（K1 再统一）。
- **代码跨度护栏（用户 2026-11-13 确认，ADR-0036 `D1` 打包预算）**：链接后用现有 `make check-code-range`（或等价脚本）测「最远 REL26 调用边」与「可执行区跨度」；**跨度 ≥ 30 MiB 或 REL26 余量 < 2 MiB ⇒ 停下报告主会话**，由用户裁定是否切 `-mcmodel=large`；**不得**自行改代码模型。
- **early stack**：在 `.bss`/链接脚本保留区中定义（大小自定，≥ 16 KiB、16 B 对齐）；**不得**依赖 boot info 提供 SP。
- **不执行**：K0 的 `head.S` 只需能链接；若实现走到 C 入口，C 入口可以是最小 `dadao_start_kernel()`（打印一条 stub 消息后自旋/退出），**不得**声称进入 `start_kernel` 或任何 Linux 子系统已工作。

## 汇编/编译口径（用户 2026-11-13 裁定）

- 汇编数据伪指令**只用** `.dd.o64`/`.dd.t32`/`.dd.w16`/`.dd.b08`；**不用** `.quad/.long/.short/.byte`（DADAO MC 明确不支持）。
- 对齐**只用** `.p2align`/`.balign`，**不用** `.align`。
- 代码模型用 `default`（= `-mcmodel=small`）；**不用** `-mcmodel=kernel`（ADR-0036 只有 `default` 与 `large`）。
- 栈保护：本任务不依赖 `-fstack-protector`（后端支持见 `m14-llvm-002`），K0 Kconfig 先关。

## 范围（改哪些文件）

- `components/linux/series`、`components/linux/patches/arch/dadao/**`（新建补丁；`patches/.gitkeep` 在有首个补丁后删除）
- `components/linux/README.md`、`components/linux/changelog.md`（补丁集概况 + 本任务条目）
- `tools/linux/make_defconfig.py`、`tools/linux/make_vmlinux.py`（新建）
- 本任务书

**不改**：`Makefile`（目标已声明）、`manifests/`（除非 `apply-series` 需要，不得改）、`spec/`、`contracts/`、`tests/`、安装根/LLVM 源码。

## 验收标准

1. 补丁集：`components/linux/series` 非空且字典序；每份补丁仅一个 `diff --git`、一个目标路径、`new file mode` 有有效 hunk；`patches/` 无 `.gitkeep`、无非 `.patch` 文件；`make check-patch-tree` 对本任务补丁集 rc=0（输出补丁数 = 现场统计；其它组件既存红项逐条归属）。
2. 源树可重建：在 `base` 干净树上 `make apply-series` rc=0 得到 `base+1`；再次 `make apply-series` 幂等 rc=0；`make check-source-state` rc=0（linux 行 `count=1 clean=True`）。
3. `make linux-defconfig` rc=0；`make linux-vmlinux` rc=0，产物 `vmlinux` 存在且通过：
   - `llvm-readelf -h`：ELF64、`Data: 2's complement, big endian`、`Machine: DADAO (0x0da0)`、`Type: EXEC`；
   - `e_entry = 0x0000_0000_0010_0000`；
   - `llvm-readelf -l`：仅 `PT_LOAD`（+ 允许 `PT_GNU_STACK` 等非装载段，须在完成区列出并说明）；每段 `p_vaddr = p_paddr + 2 TiB`（VA 与 PA 差固定偏置）、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、落在 `[0x0010_0000, 0x0400_0000)`；
   - `llvm-nm -u vmlinux` 输出为空（**无未定义符号**）。
4. **不批量造假 stub**：完成区列出所有为链接补齐的 arch 符号/文件，逐条给依据（`spec/`/`contract`/`DADAO-21` 或「K0 最小链接所需、K1 替换」）；不得出现「永不调用且无注释」的整批符号。
5. **不复制 0628**：补丁按 `m14-spec-001`/`DADAO-21` 独立推导；reviewer 抽查 `arch/dadao` 与 `.cache/refs/DADAO-0628/components/linux/patches` 的同名文件（**内容溯源，非执行依赖**），如结构/命名相似须在完成区说明「按 v5 契约重写，非复制」。
6. 工具链：构建命令中 `CC/LD/AR/...` 与 `m14-infra-001` 矩阵一致；矩阵 `absent` 项使用了其 workaround；构建日志贴出工具解析结果（现场）。
7. 可失败路径（各自可达 FAIL + 还原）：
   - 把链接脚本入口改为 `0x0011_0000`（不重链的临时副本或临时树）⇒ 产物断言 FAIL；
   - 在某个 patched 文件临时引入一个未定义外部符号并重链 ⇒ `llvm-nm -u` 非空 ⇒ FAIL；
   - `series` 漏列一份补丁 ⇒ `check-patch-tree` FAIL。
   还原用 `cp`+md5（源码/补丁）或 Process-01 §7 的源树恢复；**禁**在任务 worktree 上 `reset --hard`。
8. `make check`/L1 rc=0（外部红逐条归属）；一键证据脚本；完成区 ≤30 行、无运行期路径。

## 说明

- **K0 的成功判据只有「链接出可解析 vmlinux」**；不跑 QEMU、不要求 boot info 校验通过、不要求 early console 输出。若实现顺带跑通最小执行，须明确标「超出 K0 要求、非本任务验收项」。
- **链接地址**：`0x0010_0000` 与既有 Vast raw loader 的 `kernel_base` 一致（`spec/Machine-v5 §6.3`，`m14-spec-001` 冻结）；若评估认为必须改链接地址，**不得自改**，登记「待裁定」。
- **`-O2` vs `-O0`**：本任务不强制优化级；以能链接为准。若某优化级链接失败，记录实际使用值，不在本任务修 LLVM。
- 参考实现只读：`.cache/refs/DADAO-0628/code-agent/tasks/KL-149a-k3-linux-linked-image-reset-handoff.md` 的阶段划分/踩坑可对照（**内容溯源，非执行必需**），其地址 `0x80000000`、flat Image、ROM handoff 均**不采用**。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/补丁数/符号数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）；Linux 构建日志单独落盘。
10. 证据脚本基线钉**派单前 commit 常量**，不得取 `HEAD`。
11. 同一构建树/同一组件同一时刻只允许一个写者（`docs/Process-07 §2`）；本任务独占 linux 构建树。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`；如实现中必须改，先停并登记「待裁定」。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
