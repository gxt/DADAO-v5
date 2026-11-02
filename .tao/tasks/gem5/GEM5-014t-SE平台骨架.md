# GEM5-014t: G1 SE 平台骨架（首条静态 ELF）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-013t`（全 264 执行收敛门控，已验证）、`GEM5-004t`（B0 解码，已验证）、`GEM5-003t`（gem5 版本锁定，已验证）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；起始分支 `master`，实现落任务分支 `GEM5-014t`；不 merge、不 push）

## 用户授权与边界

- **授权原话（`.tao/knowledge/discussing.md` 2026-11-02）**：「**双链并行授权**：同时授权两条独立任务链推进——**G1 SE**（`GEM5-014t` SE 骨架 → ELF/args/stack → syscall/VMA → TLS → 静态 tset）与 **FS Machine-v5**（`SPEC-183t` → `TESTCASES-091t` → `QEMU-079t` Tiny / `QEMU-080t` Node → gem5 FS 映射）。**SE 为优先线，FS 线可并行**；共享文件仍串行；两条链均不需逐任务确认，停止点按 AGENTS。」；同日另一条授权：「不支持 syscall 默认失败报告、**不静默忽略**」。
- **本任务是 G1 SE 链首**：只建**最小可运行 SE 平台骨架**（`SEWorkload` + `Process` 边界、`AtomicSimpleCPU`、静态 ELF 装载、入口、初始栈、最小 `exit` 路径）。**不实现**完整 syscall 表 / `brk` / `mmap` / TLS / 线程 / 动态链接（后续任务）。
- **验收基线（`discussing.md` 2026-11-02，21:40/21:42 两条）**：full tset 以 **QEMU user 的 pass/fail/skip 集合**为基线，gem5 SE **不能少通过**；**若 gem5 通过而 QEMU 未通过，不得直接接受 gem5**，须新增 QEMU 调试任务定位修正；若根因是 spec 解释不清，提交用户裁定。**静态 SE 先做 `ET_EXEC`，不提前做 `ET_DYN`/static PIE**（本册据此拒绝 `ET_DYN`/`PT_INTERP`）。
- **不改**：`tests/**`、`spec/**`、`contracts/**`（含 `.tao/contracts/**`）、`Makefile`、`manifests/**`、`tools/**`、`components/{llvm-project,qemu,musl,picolibc,embench-iot}/**`、`docs/**`。测试资产另立任务（ADR-0048 D3）。
- **不复制 0628 / QEMU 实现代码**：`.cache/refs/DADAO-0628/**` 只读、只吸收**结论**并标「内容溯源，非执行依赖」；QEMU user 只作**同模式对照**（ADR-0048 D1/D2），不得作为期望值来源（ADR-0048 D4）。
- 不提交 git；提交权归 architect。临时目录 `/tmp/opencode/GEM5-014t/`。

## 背景与目标

- B0–B7 已证明 **264 条能解码、能按批执行**（`GEM5-013t`），但 gem5 侧**从未实例化过 CPU、从未装载过 ELF**：`src/arch/dadao/` 只有 decode/exec/isa/decoder/faults/pcstate，没有 `Process`/`SEWorkload`/`MMU`/`TLB`/`Interrupts`，`loader::Arch` 也不认 `EM_DADAO`。因此「指令值级实跑」一直留空。
- 本任务把该能力补到「**一条静态、静态链接、无 TLS、无 mmap 的 musl ELF 能进入 `main`、产出 stdout、经 `exit_group` 退出，且退出码/输出与 `qemu-dadao`（QEMU user）逐字节一致**」。之后的 syscall/VMA/TLS/动态链接任务在此骨架上叠加，不重做平台。
- **为何现在做**：M11 的 SE 交付（ADR-0048 D4）与 gem5 FS 线互不阻塞；SE 先行使 ISA 值语义尽早获得「真实流水线 + 真实 ELF」的第二路证据。

## 事实基线（2026-11-02 现场核对，只读）

- 用户态静态 ELF 现状（现场 `llvm-readelf`）：`ELFCLASS64 / ELFDATA2MSB / ET_EXEC / e_machine=0x0DA0 / e_flags=0x1`，`p_vaddr == p_paddr`，`p_align=0x10000`；lld 默认基址 **0x10000**（首 64 KiB 页留空），`e_entry` 落在第二段（如 `0x20f80`），非 64 KiB 对齐但 **4 字节对齐**。
- 用户态可用工具链：`.dadao/cross-toolchain/bin/{clang,ld.lld,qemu-dadao}`；静态 musl 产物 `.work/source/musl/lib/{crt1.o,libc.a}`。编译/链接配方见 `tools/qemu/user_mode_smoke.py::compile_program/link_static`（v5 自身工具，**只读复用配方，不改该文件**）。
- `qemu-dadao` 现场可跑该配方产物（`write(1,"ok\n",3); return 0;` ⇒ stdout `ok`、rc=0），是本任务的**同模式对照实现**。
- gem5 现状：`loader::Arch` 无 Dadao 成员，`ElfObject::determineArch()` 对 `EM_DADAO` 只 `warn("Unknown architecture")` ⇒ `Process::tryLoaders()` 返回空 ⇒ `fatal("Unknown error creating process object")`；`ISA::inUserMode()` 现为 `panic(...)`，而 `BaseSimpleCPU::countCommitInst()` **每条指令**都会调用它 ⇒ 必须先补。
- `BaseCPU` 要求 `interrupts.size() == numThreads`（`src/cpu/base.cc:497`），且 `BaseCPU` 从 `mmu`/`isa`/`decoder` 参数取对象 ⇒ SE 必须有 `DadaoMMU`/`DadaoTlb`/`DadaoInterrupts`/`DadaoCPU`。
- gem5 的 `SEWorkload`/`Process`/`loader` 接口形态（上游 `src/sim/se_workload.hh`、`src/sim/process.cc`、`src/arch/riscv/{process.cc,linux/se_workload.cc,tlb.cc}`）：`Process::Loader` 全局注册 + `SEWorkload` 子类 + `loader::Arch` + arch `PageBytes` + SE TLB 用 `pTable->translate`。本任务**按接口重写**，不复制 arch 实现。
- 停机：`exitImpl` 尾调用 `exitSimLoop("exiting with last active thread context", status & 0xff)`；配置脚本 `sys.exit(exit_event.getCode())` ⇒ host `$?` = guest status & 0xff。

## 接口规范

### 1. `loader::Arch` 扩展（静态 ELF 识别）

- `src/base/loader/elf_object.hh`：新增两个只读访问器 `uint16_t elfType() const { return ehdr.e_type; }`、`uint32_t elfFlags() const { return ehdr.e_flags; }`（SE 加载期据此拒绝 `ET_DYN`/`e_flags[7:0]!=1`；不改既有成员/语义）。
- `src/base/loader/object_file.hh`：`enum Arch` 增 `Dadao`（**追加在末尾**，不改既有枚举序号）。
- `src/base/loader/object_file.cc`：`archToString()` 增 `case Dadao: return "dadao";`。
- `src/base/loader/elf_object.cc`：`determineArch()` 在 `EM_RISCV` 分支旁增
  `emach == 0x0DA0`（`EM_DADAO`，`#ifndef EM_DADAO #define EM_DADAO 0x0DA0`）⇒ `arch = Dadao`；
  **同分支内**要求 `eclass == ELFCLASS64 && edata == ELFDATA2MSB`，否则 `fatal()`（合约见 `contract-elf.md §1`；不得静默接受 LE/32 位）。
- 只增不删：其它 arch 的识别与 `archToString` 语义不变。

### 2. SE 平台最小构成（新增 `src/arch/dadao/**`）

- **`page_size.hh`**：`PageShift = 16`、`PageBytes = 65536`（DADAO 页 **64 KiB**，`MEMORY.md` 反套用清单）。
- **`tlb.hh/.cc`**（`DadaoISA::TLB : BaseTLB`）：SE 专用直通翻译，唯一规则 = `Process::pTable->translate(vaddr, paddr)`（含 `pageOffset`）；
  - `translateAtomic` / `translateTiming` / `translateFunctional`：查表；失败返回 `std::make_shared<GenericPageTableFault>(vaddr)`；成功 `req->setPaddr(paddr)` 后 `NoFault`。
  - `demapPage`/`flushAll`/`takeOverFrom`/`finalizePhysical`：空实现（SE 无硬件 TLB 语义）。
  - **不**做 PTW / PTBR / `ptw_enable` / TLB 填充：SE 不建模页表硬件（ADR-0039 不适用，见 §7）。
- **`mmu.hh`**（`DadaoISA::MMU : BaseMMU`）：`MMU(const DadaoMMUParams &p) : BaseMMU(p) {}`；`translateFunctional(start,size,...)` 返回 `MMUTranslationGen(PageBytes, ...)`（**必须实现**，否则 `SETranslatingPortProxy` 的读/写路径 `panic("Not implemented")`）。
- **`interrupts.hh`**（`DadaoISA::Interrupts : BaseInterrupts`）：`checkInterrupts() → false`、`getInterrupt() → panic("SE 无中断")`、`updateIntrInfo() {}`、`clearAll() {}`；`post/clear` 保留基类 panic。理由：`BaseCPU` 强制一线程一个中断控制器，SE 无中断源。
- **`process.hh/.cc`**（`DadaoISA::Process : gem5::Process`）：
  - 构造：`Process(params, new EmulationPageTable(params.name, params.pid, PageBytes), objFile)`；`fatal_if(params.useArchPT, ...)`（SE 用宿主页表，不用架构页表）。
  - `MemState` 常量（**SE 平台约定，非 spec 断言**）：`brk_point = roundUp(image.maxAddr(), PageBytes)`、`stack_base = 0x0000_FFFF_FFFF_0000`（48 位空间顶 − 64 KiB）、`max_stack = params.maxStackSize`、`next_thread_stack_base = stack_base − max_stack`、`mmap_end = 0x0000_4000_0000_0000`。
  - `initState()`：先 `gem5::Process::initState()`（装 image、建 `initVirtMem`），再 `argsInit<uint64_t>(PageBytes)`，再对**所有** `contextIds` 设初始架构状态（见 §3）。
  - `argsInit`：在栈上自低向高布置 `argc, argv[0..argc-1], 0, envp[0..n-1], 0, auxv..., AT_NULL/0`，字符串与 16 B `AT_RANDOM` 区在其下方；**所有 64 位字段按大端写**（`ByteOrder::big`），栈指针 `& −16` 对齐（ABI 要求 8 B 对齐，取 16 保证）；auxv 至少含 `AT_PHDR`（`ElfObject::programHeaderTable()`）、`AT_PHNUM`、`AT_PHENT`、`AT_ENTRY`、`AT_PAGESZ=PageBytes`、`AT_RANDOM`、`AT_NULL`。
  - `initState()` 结束时 `tc->pcState(getStartPC())`（`= e_entry`）、`tc->setReg(RegId(intRegClass, 65), sp)`（**SP = rb1**，`int_reg::RbBase + 1`）。
- **`se_workload.hh/.cc`**（`DadaoISA::SEWorkload : gem5::SEWorkload`）：
  - `getArch() → loader::Dadao`；`setSystem` 只用基类（**不建** RemoteGDB：G1 无 gdb 寄存器描述）。
  - 文件内注册匿名 `Process::Loader`：`load()` 接受 `obj->getArch() == loader::Dadao`；`obj->getOpSys()` 为 `UnknownOpSys` 时 `warn` 后按 Linux 处理（现场 ELF `EI_OSABI=0` ⇒ `UnknownOpSys`），其余 op sys 返回 `nullptr`；`new DadaoISA::Process(params, obj)`。
  - `syscall(ThreadContext *tc)` 覆盖：先 `process->gem5::Process::syscall(tc)`（统计），再按 §5 分发。
- **Python SimObject**（每文件一个 SimObject，全部 `tags=['dadao isa']`，`cxx_header`/`cxx_class` 指向本册新增类）：
  `DadaoMMU.py`（`itb = DadaoTlb(entry_type='instruction')`、`dtb = DadaoTlb(entry_type='data')`——`BaseTLB.entry_type` **无默认值，必须显式给**；`DadaoMMU` 的 `cxx_class` 指 `gem5::DadaoISA::MMU`）、`DadaoTlb.py`、`DadaoInterrupts.py`、`DadaoSEWorkload.py`（`type="DadaoSEWorkload"`，`_is_compatible_with` 返回 `obj.get_arch() == "dadao"`）、`DadaoCPU.py`（`class DadaoAtomicSimpleCPU(BaseAtomicSimpleCPU)`，`ArchISA/ArchDecoder/ArchMMU/ArchInterrupts` = DADAO 四件，`mmu = DadaoMMU()`；以 `SimObject('DadaoCPU.py', sim_objects=[])` 注册模块）。
- **`src/cpu/simple/AtomicSimpleCPU.py`**（改）：`arch_vars` 增 `USE_DADAO_ISA`，并增 `elif arch == "USE_DADAO_ISA": from m5.objects.DadaoCPU import DadaoAtomicSimpleCPU as AtomicSimpleCPU`。
- **`src/arch/dadao/SConscript`**（改）：`Source('process.cc'/'se_workload.cc'/'tlb.cc')` + 上述 `SimObject(...)` 行；harness 测试文件仍不进构建。

### 3. 初始架构状态（入口时刻，冻结）

- `PC(rb0) = e_entry`；`rb1 = sp`（栈顶向量低位地址）；`rd0/rb0` 只读语义不变。
- 其余 RD/RB/RA = 0（gem5 寄存器文件已清零，不得再写非零）。
- **`rf0 = 0x7FF8_0000_7FC0_0000`**（FCSR 复位常量，ADR-0004 D2.1 推导；SE 也必须设，否则 FP 标志/只读位从 0 起算）；`rf1–rf63 = 0`。
- `ra0`（MemRAS 指针）语义由 B5 RAS 状态机维护，初值 0（RACNT=0/MRPTR=0 ⇒ 无有效条目）。
- `AT_RANDOM` 的 16 B 取**固定常量**（`0x00..0x0f` 递增），理由：SE 无安全边界，固定值使运行可复现；不是安全模型。
- 除上述外**不得**注入任何寄存器初值（保持「栈/ABI 是唯一入口契约」）。

### 4. 静态 ELF 装载规则（启动期校验，fail-closed）

在 `DadaoISA::Process` 构造（Loader 回调内）做，失败一律 `fatal()` 并打印具体项（**不得**继续跑）：

1. `objFile->getArch() == loader::Dadao`、`getByteOrder() == ByteOrder::big`、`dynamic_cast<loader::ElfObject*>` 成功；`elfType() == ET_EXEC`（`ET_DYN`/static PIE **明确拒绝**，按 2026-11-02 基线不提前做）；`elfFlags() & 0xff == 1`（`contract-elf §1`）。
2. `objFile->getInterpreter() == nullptr`（出现 `PT_INTERP` ⇒ 动态链接不支持，报错而非忽略）。
3. 全部 `objFile->buildImage().segments()`（`PT_LOAD` 与其零填充尾巴）满足：`size > 0`；`base % 8 == 0`（8 B 访问对齐）；`base + size` 不溢出且 `≤ stack_base − max_stack`（不侵占栈区）。0 页**不强制**保留（当前 lld 默认首段 `0x10000`）。
4. `entryPoint() % 4 == 0`；`entryPoint()` 必须落在某个 segment 的 `[base, base+size)` 内（否则取指必 fault，属加载错误）。
5. `getOpSys()` 仅允许 `Linux` / `UnknownOpSys`。

**装载语义**：沿用 gem5 通用机制（`Process::initState` 的 `image.write(*initVirtMem)`，`SETranslatingPortProxy::Always` 自动分配页），**不做** VA=PA 之外的偏置、不做地址重定位；每段 `p_filesz` 取文件、尾巴零填充（`contract-elf §5.2`）。

### 5. 最小 syscall 面（5 个号，其余一律显式失败）

入口：`trap cfx0, 0`（`umon`，`immu18 = 0`）——即 `inst.cc` 的 `Gem5B1Context::trapTo(0, 0)` 在 **SE 模式**下改为 `tc->getSystemPtr()->workload->syscall(tc)` 并返回 `None`（PC 由 gem5 自动 +4，等价 `SyscallFault::invokeSE`；**不**手工 advance）。`trap` 的其它组合（`cfxha != 0`、`immu18 != 0`、semihosting tag 区）仍 `panic`（SE 无 SEE 向量/无 semihosting；ADR-0020 D8 的 `SYS_EXIT` 属 FS 线）。

寄存器约定（`contract-syscall.md §1.1/§3/§4`）：号在 **`rd15`**；返回 **`rd8`**，错误 = **负 `-errno`**；参数按 bank 分：立即数/整型 → `rd16,rd17,…`，指针 → `rb16,rb17,…`（自 16 起独立计数）。

必需集（缺一即「起不到 `main`」或「看不到结果」，逐条有据）：

- `set_tid_address`(96)：musl `__init_tp` 在 `main` 之前**无条件**调用（`.work/source/musl/src/env/__init_tls.c:22`）⇒ 必实现；返回 `tid`（单线程 = `pid`），把 guest 的 `clear_child_tid` 指针记入 `Process::childClearTID`。
- `write`(64)：参数 `fd=int → rd16`、`buf=ptr → rb16`、`count=size_t → rd17`；经 `Process::fds[fd]`（`HBFDEntry::getSimFD()`）落宿主 fd；guest 缓冲用 `SETranslatingPortProxy(tc, Never)` + `tryReadBlob`（**禁 `Always`**：读不得静默分配页）；失败 `-EBADF`/`-EFAULT`。
- `writev`(66)：`fd → rd16`、`iov=ptr → rb16`、`iovcnt → rd17`；每个 `iovec` 为 `{base(8B), len(8B)}`，**大端**解析；逐段复用 `write` 路径；返回累计字节数（musl stdio 走 `writev`，缺它则 `printf` 类用例全灭）。
- `exit`(93) / `exit_group`(94)：`status = int → rd16`；动作 = `tc->halt()` + `exitSimLoop("exiting with last active thread context", status & 0xff)`（与上游 `exitImpl` 尾部同构；单进程 SE 无需 fd 关闭/信号链）；**立即返回不再写 rd8**。

**不支持的号**：`fatal("DADAO SE: syscall %d not implemented (pc=%#x)", nr, pc)` —— 必须**带号与 pc 报错并非零退出**，不得返回 0/`-ENOSYS` 后静默继续（用户 2026-11-02 裁定「不支持 syscall 默认失败报告、不静默忽略」）。完整 syscall 表（含 `-ENOSYS` 语义、`guest_abi` 参数框架）属后续 syscall 任务。

### 6. 配置脚本 `configs/dadao/se.py`（新增，自写经典式 SE 配置）

不用 `gem5.components`（那要改 `src/python/gem5/isas.py`/`SimpleCore` 的 ISA 枚举映射，超出本任务最小面）；改用经典对象组合（形态可对照上游 `configs/deprecated/example/se.py`，**自行编写**）：

- `System(mem_mode='atomic', mem_ranges=[AddrRange(mem_size)], cache_line_size=64)`；`voltage_domain`/`clk_domain`；`membus = SystemXBar()`；`mem = SimpleMemory(range=…)`；`cpu = DadaoAtomicSimpleCPU()`；`cpu.workload = process`；`cpu.createInterruptController()`；`cpu.createThreads()`；端口连接 = `cpu.icache_port`/`cpu.dcache_port`/`system.system_port` → `membus.cpu_side_ports`、`mem.port` → `membus.mem_side_ports`；`system.workload = DadaoSEWorkload()`；`Root(full_system=False, system=system)`；`m5.instantiate()` 后 `m5.simulate()`。
- CLI：`--binary <elf>`（必填）、`--args "a b"`、`--env "K=V…"`、`--mem-size`（默认 `256MiB`）、`--max-stack`（默认 `8MiB`）、`--guest-stdout/--guest-stderr/--guest-stdin <path>`（映射 `process.output/errout/input`；**默认不改**，即 guest fd 1/2 落宿主 stdout/stderr）、`--cwd`、`--max-insts`（防挂死，非通过判据）。
- **argv[0] 规则**：`process.executable = process.cmd[0] = --binary 的原样字符串`（对照时 QEMU 侧必须用**同一字符串**，否则 argv 打印必然不等）。
- 退出：`exit_event = m5.simulate()`；若 `getCause() != "exiting with last active thread context"` ⇒ 打印 cause 并 `sys.exit(125)`（**非 guest 退出**，含 `--max-insts` 命中）；否则 `sys.exit(exit_event.getCode())`。

### 7. SE 与 FS 的隔离（硬约束，门控可判）

- **不引入** BootROM / Machine-v5 段布局 / PTBR / `ptw_enable` / PTW / TLB 填充 / semihosting / exit-port：SE 代码与配置中**不得**出现 `0xFC00_0000_0000`、`bootrom`、`ptbr`、`ptw`、`semihosting`、exit-port 常量（`src/arch/dadao/{process,se_workload,tlb,mmu}.*` + `configs/dadao/se.py` 文本断言，注释剥离后 grep 计数 0）。
- 用户态地址空间从 **0** 起：DRAM 物理基址 **0**（`SimpleMemory` 从 0 起）；guest VA = ELF `p_vaddr`（lld 默认首段 **0x10000**，即 0 页留空）。**SE 不按 Machine-v5 的 `0xFC00_0000_0000` 放 RAM**，也不与 FS 的 42 位内存窗口（ADR-0039）混用。
- guest VA 宽度取 **48 位**（与 `qemu-dadao` 的 `TARGET_VIRT_ADDR_SPACE_BITS=48` 对齐，用于栈顶/`mmap_end` 常量）；这是 **SE 平台约定**，不是 spec 断言，也**不**构成与 FS 的跨模式比较（ADR-0048 D1）。

## 文件范围

**新增补丁**（`components/gem5/patches/`，一文件一补丁）：

- `src/base/loader/object_file.hh.patch`、`src/base/loader/object_file.cc.patch`、`src/base/loader/elf_object.hh.patch`、`src/base/loader/elf_object.cc.patch`（改，见 §1）
- `src/arch/dadao/page_size.hh.patch`、`mmu.hh.patch`、`DadaoMMU.py.patch`、`tlb.hh.patch`、`tlb.cc.patch`、`DadaoTlb.py.patch`、`interrupts.hh.patch`、`DadaoInterrupts.py.patch`、`process.hh.patch`、`process.cc.patch`、`se_workload.hh.patch`、`se_workload.cc.patch`、`DadaoSEWorkload.py.patch`、`DadaoCPU.py.patch`（新）
- `src/arch/dadao/isa.cc.patch`（改：`inUserMode()` → `true` + 注释「G1 SE 只有 user 模式；FS 的 3 轴 mode 模型由 FS 任务替换」）
- `src/arch/dadao/inst.cc.patch`（改：`trapTo` SE syscall 路径，见 §5）
- `src/arch/dadao/SConscript.patch`（改：sources + SimObjects）
- `src/cpu/simple/AtomicSimpleCPU.py.patch`（改：`USE_DADAO_ISA` 分支）
- `configs/dadao/se.py.patch`（新增配置脚本）

**仓库侧文件**：`components/gem5/series`（+N，**字典序**）、`components/gem5/changelog.md`（M11 节追加一条）、`components/gem5/README.md`（补 SE 段：构成/边界/CLI/已知限制）、本任务书、`.tao/knowledge/milestones.md`。

**不改**：`tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`Makefile`、`manifests/**`、`tools/**`、`components/{llvm-project,qemu,musl,picolibc,embench-iot}/**`、`docs/**`。

## 验收标准

1. **补丁集与源树**：`make check-patch-tree` rc=0（补丁数**现场统计**；一文件一补丁、`series` 字典序、可应用到 pinned base、断言⑥/⑨ 内容一致）；`make check-source-state` rc=0（gem5 HEAD = base+1、worktree 干净）。补丁导出必须走 `python3 tools/infra/make_patch.py gem5`（**禁**手改补丁，`docs/Process-01 §6.1.1`）。
2. **构建**：`make build-gem5` rc=0；`gem5.opt --help` rc=0；`gem5.opt --list-sim-objects` 含 `DadaoAtomicSimpleCPU`、`DadaoSEWorkload`、`DadaoMMU`、`DadaoTlb`、`DadaoInterrupts`（注册生效的静态证据）。
3. **静态 ELF 进入并退出**：`hello` 用例（`write(1,"ok\n",3); return 0;`）在 gem5 SE 上 ⇒ guest stdout `ok\n`、gem5 进程 `$? == 0`、`EXIT_CAUSE` 为 `exiting with last active thread context`。
4. **退出码精确传播**：`fail` 用例（`return 7`）⇒ gem5 `$? == 7`（不是 0、不是 1）；`exit_group` 路径生效（`status & 0xff` 语义；另测 `return 300` ⇒ `$? == 44` 作为 `&0xff` 的正向证据）。
5. **初始栈/argv 正确**：`args` 用例（`return argc == 2 ? 0 : 3;`）带 `--args extra` ⇒ `$? == 0`；不带 `--args` ⇒ `$? == 3`（证明 `argc/argv` 向量与 SP/`rb1` 正确，而非「恰好能跑」）。
6. **同模式一致（ADR-0048 D1/D2）**：上列 3 个用例 + 1 条既有静态 ELF（`.dadao/tests/llvm-ts-user/static/**` 中任一 5 s 内结束者，如 `heapsort`）分别在 `qemu-dadao` 与 gem5 SE 上跑，**stdout 字节逐字节相同、退出码相同**；argv[0] 传同一字符串。若出现「gem5 通过而 QEMU 未通过」或反之，**不得直接接受**：按 `discussing.md` 2026-11-02 基线定位（QEMU 调试任务 / spec 裁定），并在完成区写清归属。
7. **不支持 syscall 不静默**：`pidsys` 用例（调 `getpid()`）⇒ gem5 **非零退出**且 stderr 含 `syscall` 号与 `pc`；同一 binary 在 `qemu-dadao` 正常退出（证明这是「明确失败报告」而非「静默忽略」）。
8. **B0–B7 零退化**：`make check-gem5-decode` rc=0（`264/264`、`388/388`、`28/28`、`2/2`、`failures 0`）；`python3 tools/gem5/check_converge.py` rc=0，计数等于 `GEM5-013t` 基线（ids 264/264、boundary 1848/1848、B1–B7 `2102/1160/4248/3696/1215/1362/2979`、`[FAIL]` 0）。
9. **L1**：`make check` rc=0。若失败，须用 `git archive HEAD` 临时树在**同一命令**下复现，证明该失败**既有且非本任务引入**（逐条列出命令、rc、现场），并在完成区登记；**本任务引入的红项一律不得放过**（`check-knowledge-refs` 等对 `.work/**` 悬空敏感，任务书内引用一律用 `**` 通配形）。
10. **隔离门控**：`git diff --name-only <base>`（gem5 补丁集）与仓库改动集对 `tests/ spec/ contracts/ .tao/contracts/ Makefile manifests/ tools/ components/{llvm-project,qemu,musl,picolibc,embench-iot}/ docs/` 命中数 = 0；§7 的禁用 token 文本断言计数 0（注释剥离后）。
11. **反例可达 FAIL**：§必测反例 ≥5 类，每类「注入 → rc≠0 且有 `[FAIL]`/错误行 → `cp` 备份 + md5 对账还原 → 回绿 rc=0」；**禁** `git checkout/restore/stash`。
12. **证据与完成区**：`.work/evidence/GEM5-014t/**` 一键脚本 + `REPORT.md`（数字全部脚本现场生成，不手写）；完成区 ≤30 行；状态 `待验收`。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **ELF 识别缺失**：删 `elf_object.cc` 的 `EM_DADAO` 分支 ⇒ 启动即 `Cannot load object file` / `Unknown error creating process object`，验收 3 失败。
2. **arch 归属错**：`SEWorkload::getArch()` 返回 `loader::Riscv64` ⇒ Loader 不接、进程创建失败。
3. **入口错**：`Process::initState` 把 PC 设为 `0` 或 `image.maxAddr()` ⇒ 取指 fault/不产出 `ok\n`，验收 3 失败。
4. **栈向量错**：`sp` 初值 `+8`（或 `argc` 写错位）⇒ 验收 5 的 `args` 用例失败（`argc` 读成垃圾）。
5. **退出码不传播**：`exit_group` 处理器写成固定 `0`（或漏 `&0xff`）⇒ 验收 4 失败（`7` 读成 `0`/`300` 读成 `300&0xff≠44`）。
6. **syscall 号寄存器错**：分发改用 `rd16` 取号 ⇒ 全部用例变「未实现 syscall」失败。
7. **静默吞未实现 syscall**：把 `fatal` 改成 `return 0` ⇒ 验收 7 失败（应报错却正常退出）。
8. **配置吞码**：`configs/dadao/se.py` 恒 `sys.exit(0)` ⇒ 验收 4/5 失败。

## 证据

- `.work/evidence/GEM5-014t/**` 下的 `run.sh`：编译 4 个 fixture（`hello`/`fail`/`args`/`pidsys`，配方同 `tools/qemu/user_mode_smoke.py`）→ qemu-dadao 基线 → gem5 SE（`--outdir /tmp/opencode/GEM5-014t/gem5-out/`，**禁**在仓库内落 `m5out`）→ 逐项比对 → 跑验收 1/2/8/9/10 → 落 `*_EXIT=<rc>`；日志 `/tmp/opencode/GEM5-014t/` + `logs/`。
- 同目录 `run.sh --inject`：跑 §必测反例，记录「注入前 md5 / 注入后 rc / 还原后 md5 / 回绿 rc」。
- 同目录 `REPORT.md`：补丁数、sim-object 列表、逐用例「qemu stdout/rc vs gem5 stdout/rc」、`EXIT_CAUSE`、B0–B7 计数、构建结果、注入表、`rf0`/SP/PC 实际值证据（可在配置里打印一次寄存器快照，或由 `--debug-flags=Exec` 抓取）。
- 工具链/依赖缺失（`.dadao/cross-toolchain/bin/*`、`.work/source/musl/lib/*`）或 SCons 缺失 ⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明

- **参考来源（内容溯源，非执行依赖）**：0628 `DG-001a`/`DG-002a` 的结论——`Process::Loader` + `SEWorkload` 子类是已验证的桥形态；`e_machine` 必须非 0、装载地址须在 mem range 内、`p_offset` 须页对齐；用 `sys.exit(exit_event.getCode())` 传出退出码。**本项目差异**：v5 用 ELF + 宿主页表（VA≠PA，装载地址不受 mem range 约束）、停机走 Linux syscall（musl `exit_group`）而非 `halt` 指令；0628 代码与 QEMU translate 实现**不得复制或改写沿用**。
- **非目标（后续任务）**：完整 syscall 表与 `-ENOSYS` 语义、`brk`/`mmap`/VMA、TLS/`clone`/futex、动态链接与 `PT_INTERP`、信号/`poll`、gdb、checkpoint、多核与非 ATOMIC CPU、ILLI/MALIGN/IALIGN 进入 SEE 异常帧（当前仍 panic，失败可见）。
- **已知风险**：① musl 启动若实测走到 `mmap`（`libc.tls_size > sizeof builtin_tls`）⇒ 本任务**停下报告**，不临时扩 syscall 面；② `DadaoInst::execute` 的 `xc->readMem` 首次真正跑流水线，可能暴露 `ISA::resetThread()`/`readMiscReg` 等未实现钩子——按「保留现场 + 明确报错」处置并登记遗留；③ 首个固件级 `trap cfx0,0` 之外的 `trap` 组合仍 panic（属 SEE 向量任务）。
- **同组件串行**：gem5 补丁集/`series`/`changelog` 同一时刻只允许**一个写者**；本任务期间不并行其它 gem5 任务（FS 线的 gem5 FS 映射任务排在其后）。
- **构建耗时**：新增 SimObject 会重新生成 `params/**` 并触发较大范围重编，预计 **15–40 分钟**（增量）；按 AGENTS 长任务规则用 background + 日志 + `*_EXIT` 标记，禁 `setsid nohup` 后失联。

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
（审查者独立验证的重跑记录、约束核验、判决）

## 已定 / 下发前确认

1. **任务粒度**：不切分；本册作为一个“SE 平台骨架”能力整体交付，23 份补丁按接口层分批提交；若 engineer 实测规模明显超限，回报后再按 014t/015t 拆分，不预设。
2. **guest VA 宽度**：SE 取 48 位（对齐 qemu-user `TARGET_VIRT_ADDR_SPACE_BITS=48`），**不**用 ADR-0039 的 42 位 FS 内存窗口；属 SE 平台约定、不写 spec。
3. **最小 syscall 面**：包含 `writev`（否则 musl `printf` 类既有 tset 二进制无法参与对照）。
4. **`--max-insts` 判据**：非 guest 退出 ⇒ 配置脚本退出 125，证据侧判 FAIL，与 guest 退出码区分。
