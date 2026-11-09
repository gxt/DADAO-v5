# GEM5-014t: G1 SE 平台骨架（首条静态 ELF · 最小 libc 启动 syscall 面）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-013t`（全 264 执行收敛门控，已验证）、`GEM5-004t`（B0 解码，已验证）、`GEM5-003t`（gem5 版本锁定，已验证）、QEMU user 页大小改为 16 位（`QEMU-081t`，需先/并行修正；当前 `qemu-dadao` 的 12 位是 bug，不能作为 SE 基准）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；起始分支 `master`，实现落任务分支 `GEM5-014t`；不 merge、不 push）

## 用户授权与边界

- **授权原话（`.tao/knowledge/discussing.md` 2026-11-02）**：「**双链并行授权**：同时授权两条独立任务链推进——**G1 SE**（`GEM5-014t` SE 骨架 → ELF/args/stack → syscall/VMA → TLS → 静态 tset）与 **FS Machine-v5**（`SPEC-183t` → `TESTCASES-091t` → `QEMU-079t` Tiny / `QEMU-080t` Node → gem5 FS 映射）。**SE 为优先线，FS 线可并行**；共享文件仍串行；两条链均不需逐任务确认，停止点按 AGENTS。」；同日另一条授权：「不支持 syscall 默认失败报告、**不静默忽略**」。
- **本任务是 G1 SE 链首**：只建**最小可运行 SE 平台骨架**（`SEWorkload` + `Process` 边界、`AtomicSimpleCPU`、静态 ELF 装载、入口、初始栈、最小 libc 启动 syscall 面 `set_tid_address/write/writev/exit/exit_group`）。**不实现**完整 syscall 表 / `brk` / `mmap` / TLS / 线程 / 动态链接（后续任务）。
- **验收基线（`discussing.md` 2026-11-02，21:40/21:42 两条）**：full tset 以 **QEMU user 的 pass/fail/skip 集合**为基线，gem5 SE **不能少通过**；**若 gem5 通过而 QEMU 未通过，不得直接接受 gem5**，须新增 QEMU 调试任务定位修正；若根因是 spec 解释不清，提交用户裁定。**静态 SE 先做 `ET_EXEC`，不提前做 `ET_DYN`/static PIE**（本册据此拒绝 `ET_DYN`/`PT_INTERP`）。
- **不改**：`tests/**`、`spec/**`、`contracts/**`（含 `.tao/contracts/**`）、`Makefile`、`manifests/**`、`tools/**`、`components/{llvm-project,qemu,musl,picolibc,embench-iot}/**`、`docs/**`。测试资产另立任务（ADR-0048 D3）。
- **不复制 0628 / QEMU 实现代码**：`0628 只读参考检出` 只读、只吸收**结论**并标「内容溯源，非执行依赖」；QEMU user 只作**同模式对照**（ADR-0048 D1/D2），不得作为期望值来源（ADR-0048 D4）。
- 不提交 git；提交权归 architect。临时目录 `运行期临时目录`。

## 背景与目标

- B0–B7 已证明 **264 条能解码、能按批执行**（`GEM5-013t`），但 gem5 侧**从未实例化过 CPU、从未装载过 ELF**：`src/arch/dadao/` 只有 decode/exec/isa/decoder/faults/pcstate，没有 `Process`/`SEWorkload`/`MMU`/`TLB`/`Interrupts`，`loader::Arch` 也不认 `EM_DADAO`。因此「指令值级实跑」一直留空。
- 本任务把该能力补到「**一条静态链接、无 TLS、无 mmap 的 musl ELF 能进入 `main`、产出 stdout、经 `exit_group` 退出；其依赖的最小 libc 启动 syscall 面（`set_tid_address/write/writev/exit/exit_group`）齐备，且退出码/输出与 `qemu-dadao`（QEMU user）逐字节一致**」。之后的 syscall/VMA/TLS/动态链接任务在此骨架上叠加，不重做平台。
- **为何现在做**：M11 的 SE 交付（ADR-0048 D4）与 gem5 FS 线互不阻塞；SE 先行使 ISA 值语义尽早获得「真实流水线 + 真实 ELF」的第二路证据。

## 事实基线（2026-11-02 现场核对，只读）

- 用户态静态 ELF 现状（现场 `llvm-readelf`）：`ELFCLASS64 / ELFDATA2MSB / ET_EXEC / e_machine=0x0DA0 / e_flags=0x1`，`p_vaddr == p_paddr`，`p_align=0x10000`；lld 默认基址 **0x10000**（首 64 KiB 页留空），`e_entry` 落在第二段（如 `0x20f80`），非 64 KiB 对齐但 **4 字节对齐**。
- 用户态可用工具链：`安装根 bin 下的 {clang,ld.lld,qemu-dadao}`；静态 musl 产物 `musl 组件源树中的 lib/{crt1.o,libc.a}`。编译/链接配方见 `tools/qemu/user_mode_smoke.py::compile_program/link_static`（v5 自身工具，**只读复用配方，不改该文件**）。
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

- **`page_size.hh`**：`PageShift = 16`、`PageBytes = 65536`（DADAO 普通页 **64 KiB**，与 `contract-elf` 的 `p_align=0x10000` 一致）。**`qemu-dadao` 当前 `TARGET_PAGE_BITS=12` 是错误，须由 QEMU 任务改为 16**；SE 以 16 为基线，`AT_PAGESZ=65536`，不得为迁就 QEMU 的 4 KiB 而改小。
- **`tlb.hh/.cc`**（`DadaoISA::TLB : BaseTLB`）：SE 专用直通翻译，唯一规则 = `Process::pTable->translate(vaddr, paddr)`（含 `pageOffset`）；
  - `translateAtomic` / `translateTiming` / `translateFunctional`：查表；失败返回 `std::make_shared<GenericPageTableFault>(vaddr)`；成功 `req->setPaddr(paddr)` 后 `NoFault`。
  - `demapPage`/`flushAll`/`takeOverFrom`/`finalizePhysical`：空实现（SE 无硬件 TLB 语义）。
  - **不**做 PTW / PTBR / `ptw_enable` / TLB 填充：SE 不建模页表硬件（ADR-0039 不适用，见 §7）。
- **`mmu.hh`**（`DadaoISA::MMU : BaseMMU`）：`MMU(const DadaoMMUParams &p) : BaseMMU(p) {}`；`translateFunctional(start,size,...)` 返回 `MMUTranslationGen(PageBytes, ...)`（**必须实现**，否则 `SETranslatingPortProxy` 的读/写路径 `panic("Not implemented")`）。
- **`interrupts.hh`**（`DadaoISA::Interrupts : BaseInterrupts`）：`checkInterrupts() → false`、`getInterrupt() → panic("SE 无中断")`、`updateIntrInfo() {}`、`clearAll() {}`；`post/clear` 保留基类 panic。理由：`BaseCPU` 强制一线程一个中断控制器，SE 无中断源。
- **`process.hh/.cc`**（`DadaoISA::Process : gem5::Process`）：
  - 构造：`Process(params, new EmulationPageTable(params.name, params.pid, PageBytes), objFile)`；`fatal_if(params.useArchPT, ...)`（SE 用宿主页表，不用架构页表）。
  - `MemState` 常量（**SE 平台约定，非 spec 断言**）：`brk_point = roundUp(image.maxAddr(), PageBytes)`、`stack_base = 0x0000_FFFF_FFFF_0000`（48 位空间顶 − 64 KiB）、`max_stack = params.maxStackSize`、`next_thread_stack_base = stack_base − max_stack`、`mmap_end = 0x0000_4000_0000_0000`。
  - `initState()`：先 `gem5::Process::initState()`（装 image、建 `initVirtMem`），再 `argsInit<uint64_t>(PageBytes)`，再分配 1 MiB MemRAS 区（`initVirtMem->allocate`/`pTable->map`，按 gem5 现有 SE 接口；清零并写 invalid-entry），最后对**所有** `contextIds` 设初始架构状态（见 §3）。
  - `argsInit`：在栈上自低向高布置 `argc, argv[0..argc-1], 0, envp[0..n-1], 0, auxv..., AT_NULL/0`，字符串与 16 B `AT_RANDOM` 区在其下方；**所有 64 位字段按大端写**（`ByteOrder::big`），栈指针 `& −16` 对齐（ABI 要求 8 B 对齐，取 16 保证）；auxv 至少含 `AT_PHDR`（`ElfObject::programHeaderTable()`）、`AT_PHNUM`、`AT_PHENT`、`AT_ENTRY`、`AT_PAGESZ=65536`（= `PageBytes`）、`AT_RANDOM`、`AT_NULL`。
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
- `ra0`（MemRAS 指针）：SE 必须在初始线程启动前分配 **1 MiB MemRAS 区**，清零并把 `MRPTR` 槽预置为 invalid-entry（0），然后置 `ra0[47:0] = MRPTR = 区顶 − 8`（8 字节对齐）、`RACNT=0`。依据 `contract-isa §1.3.4`「用户进程开始执行时 MemRAS 应做好分配并设置 ra0」；**不得**用 `MRPTR=0` 初值，否则深调用链会在 >63 层触发 `RASOF`。区域地址由 SE 平台自定（不要求与 QEMU user 的匿名 mmap 地址逐字节相同），但必须在 guest 可读写页内且不与 ELF/栈冲突。
- `AT_RANDOM` 的 16 B 取**固定常量**（`0x00..0x0f` 递增），理由：SE 无安全边界，固定值使运行可复现；不是安全模型。
- 除上述外**不得**注入任何寄存器初值（保持「栈/ABI 是唯一入口契约」）。

### 4. 静态 ELF 装载规则（启动期校验，fail-closed）

在 `DadaoISA::Process` 构造（Loader 回调内）做，失败一律 `fatal()` 并打印具体项（**不得**继续跑）：

1. `objFile->getArch() == loader::Dadao`、`getByteOrder() == ByteOrder::big`、`dynamic_cast<loader::ElfObject*>` 成功；`elfType() == ET_EXEC`（`ET_DYN`/static PIE **明确拒绝**，按 2026-11-02 基线不提前做）；`elfFlags() & 0xff == 1`（`contract-elf §1`）。
2. `objFile->getInterpreter() == nullptr`（出现 `PT_INTERP` ⇒ 动态链接不支持，报错而非忽略）。
3. 全部 `objFile->buildImage().segments()`（`PT_LOAD` 与其零填充尾巴）满足：`size > 0`；**`base % 4 == 0`**（lld 实测不按 64 KiB `p_align` 放置 PT_LOAD，如 `0x2017c`；4 B 是当前装载可执行的最低对齐，8 B 不做机械断言）；`base + size` 不溢出且 `≤ stack_base − max_stack`（不侵占栈区）。0 页**不强制**保留（当前 lld 默认首段 `0x10000`）。
4. `entryPoint() % 4 == 0`；`entryPoint()` 必须落在某个 segment 的 `[base, base+size)` 内（否则取指必 fault，属加载错误）。
5. `getOpSys()` 仅允许 `Linux` / `UnknownOpSys`。

**装载语义**：沿用 gem5 通用机制（`Process::initState` 的 `image.write(*initVirtMem)`，`SETranslatingPortProxy::Always` 自动分配页），**不做** VA=PA 之外的偏置、不做地址重定位；每段 `p_filesz` 取文件、尾巴零填充（`contract-elf §5.2`）。

### 5. 最小 syscall 面（6 个号，其余一律显式失败）

入口：`trap cfx0, 0`（`umon`，`immu18 = 0`）——即 `inst.cc` 的 `Gem5B1Context::trapTo(0, 0)` 在 **SE 模式**下改为 `tc->getSystemPtr()->workload->syscall(tc)` 并返回 `None`（PC 由 gem5 自动 +4，等价 `SyscallFault::invokeSE`；**不**手工 advance）。`trap` 的其它组合（`cfxha != 0`、`immu18 != 0`、semihosting tag 区）仍 `panic`（SE 无 SEE 向量/无 semihosting；ADR-0020 D8 的 `SYS_EXIT` 属 FS 线）。

寄存器约定（`contract-syscall.md §1.1/§3/§4`）：号在 **`rd15`**；返回 **`rd8`**，错误 = **负 `-errno`**；参数按 bank 分：立即数/整型 → `rd16,rd17,…`，指针 → `rb16,rb17,…`（自 16 起独立计数）。

必需集（缺一即「起不到 `main`」或「看不到结果」，逐条有据）：

- `set_tid_address`(96)：musl `__init_tp` 在 `main` 之前**无条件**调用（`musl 组件源树中的 src/env/__init_tls.c:22`）⇒ 必实现；返回 `tid`（单线程 = `pid`），把 guest 的 `clear_child_tid` 指针记入 `Process::childClearTID`。
- `write`(64)：参数 `fd=int → rd16`、`buf=ptr → rb16`、`count=size_t → rd17`；经 `Process::fds[fd]`（`HBFDEntry::getSimFD()`）落宿主 fd；guest 缓冲用 `SETranslatingPortProxy(tc, Never)` + `tryReadBlob`（**禁 `Always`**：读不得静默分配页）；失败 `-EBADF`/`-EFAULT`。
- `writev`(66)：`fd → rd16`、`iov=ptr → rb16`、`iovcnt → rd17`；每个 `iovec` 为 `{base(8B), len(8B)}`，**大端**解析；逐段复用 `write` 路径；返回累计字节数（musl stdio 走 `writev`，缺它则 `printf` 类用例全灭）。
- `ioctl`(29)：musl `__stdout_write` 在 stdout 首次写前无条件发 `TIOCGWINSZ`，故纳入最小面；只接受 `TIOCGWINSZ`（返回 `-ENOTTY`，保持非交互）与 `TCGETS`（返回 `-ENOTTY`），其余 request **fatal**（带号与 pc），不得静默返回 0。
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
2. **构建**：`make build-gem5` rc=0；`gem5.opt --help` rc=0；`gem5.opt --list-sim-objects` 含 `DadaoISA`/`DadaoSEWorkload`/`DadaoMMU`/`DadaoTlb`/`DadaoInterrupts`；`DadaoAtomicSimpleCPU` 是 `DadaoCPU.py` 内的 Python 别名，以「probe 导入 + 实际实例化 + 跑通 hello」作为等价注册证据（不要求进入 C++ SimObject 列表）。
3. **静态 ELF 进入并退出**：`hello` 用例（`write(1,"ok\n",3); return 0;`）在 gem5 SE 上 ⇒ guest stdout `ok\n`、gem5 进程 `$? == 0`、`EXIT_CAUSE` 为 `exiting with last active thread context`。
4. **退出码精确传播**：`fail` 用例（`return 7`）⇒ gem5 `$? == 7`（不是 0、不是 1）；`exit_group` 路径生效（`status & 0xff` 语义；另测 `return 300` ⇒ `$? == 44` 作为 `&0xff` 的正向证据）。
5. **初始栈/argv 正确**：`args` 用例（`return argc == 2 ? 0 : 3;`）带 `--args extra` ⇒ `$? == 0`；不带 `--args` ⇒ `$? == 3`（证明 `argc/argv` 向量与 SP/`rb1` 正确，而非「恰好能跑」）。
5b. **页大小一致**：`pagesz` 用例（`return sysconf(_SC_PAGESIZE) == 65536 ? 0 : 3;`）在 gem5 SE 与修正后的 `qemu-dadao`（`TARGET_PAGE_BITS=16`）上均 `$? == 0`；证明 `AT_PAGESZ`/`PageBytes` 为 64 KiB。
5c. **MemRAS 已分配**：`deepcall` 用例（100 层 `call`/`ret`，`return 0`）在 gem5 SE 与 `qemu-dadao` 上均 `$? == 0`；证据侧打印 `ra0`（`MRPTR != 0`）并断言 100 层调用不触发 `RASOF`。
6. **同模式一致（ADR-0048 D1/D2）**：上列用例 + 1 条既有静态 ELF（`安装根中的 hello.elf`，输出确定、无 malloc/mmap）分别在 `qemu-dadao` 与 gem5 SE 上跑，**stdout 字节逐字节相同、退出码相同**；argv[0] 传同一字符串。若出现「gem5 通过而 QEMU 未通过」或反之，**不得直接接受**：按 `discussing.md` 2026-11-02 基线定位（QEMU 调试任务 / spec 裁定），并在完成区写清归属。
7. **不支持 syscall 不静默**：`pidsys` 用例（调 `getpid()`）⇒ gem5 **非零退出**且 stderr 含 `syscall` 号与 `pc`；同一 binary 在 `qemu-dadao` 正常退出（证明这是「明确失败报告」而非「静默忽略」）。
8. **B0–B7 零退化**：`make check-gem5-decode` rc=0（`264/264`、`388/388`、`28/28`、`2/2`、`failures 0`）；`python3 tools/gem5/check_converge.py` rc=0，计数等于 `GEM5-013t` 基线（ids 264/264、boundary 1848/1848、B1–B7 `2102/1160/4248/3696/1215/1362/2979`、`[FAIL]` 0）。
9. **L1**：`make check` rc=0。若失败，须用 `git archive HEAD` 临时树在**同一命令**下复现，证明该失败**既有且非本任务引入**（逐条列出命令、rc、现场），并在完成区登记；**本任务引入的红项一律不得放过**（`check-knowledge-refs` 等对 `运行期临时目录` 悬空敏感，任务书内引用一律用 `**` 通配形）。
10. **隔离门控**：`git diff --name-only <base>`（gem5 补丁集）与仓库改动集对 `tests/ spec/ contracts/ .tao/contracts/ Makefile manifests/ tools/ components/{llvm-project,qemu,musl,picolibc,embench-iot}/ docs/` 命中数 = 0；§7 的禁用 token 文本断言计数 0（注释剥离后）。
11. **反例可达 FAIL**：§必测反例 ≥5 类，每类「注入 → rc≠0 且有 `[FAIL]`/错误行 → `cp` 备份 + md5 对账还原 → 回绿 rc=0」；**禁** `git checkout/restore/stash`。
12. **证据与完成区**：`运行期证据（已清理，未归档）` 一键脚本 + `REPORT.md`（数字全部脚本现场生成，不手写）；完成区 ≤30 行；状态 `待验收`。

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

- `运行期证据（已清理，未归档）` 下的 `run.sh`：编译 6 个 fixture（`hello`/`fail`/`args`/`pidsys`/`pagesz`/`deepcall`，配方同 `tools/qemu/user_mode_smoke.py`）→ qemu-dadao 基线 → gem5 SE（`--outdir <运行期临时目录>`，**禁**在仓库内落 `m5out`）→ 逐项比对 → 跑验收 1/2/8/9/10 → 落 `*_EXIT=<rc>`；日志 `运行期临时目录` + `logs/`。
- 同目录 `run.sh --inject`：跑 §必测反例，记录「注入前 md5 / 注入后 rc / 还原后 md5 / 回绿 rc」。
- 同目录 `REPORT.md`：补丁数、sim-object 列表、逐用例「qemu stdout/rc vs gem5 stdout/rc」、`EXIT_CAUSE`、B0–B7 计数、构建结果、注入表、`rf0`/SP/PC 实际值证据（可在配置里打印一次寄存器快照，或由 `--debug-flags=Exec` 抓取）。
- 工具链/依赖缺失（`安装根 bin 下的 *`、`musl 组件源树中的 lib/*`）或 SCons 缺失 ⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明

- **参考来源（内容溯源，非执行依赖）**：0628 `DG-001a`/`DG-002a` 的结论——`Process::Loader` + `SEWorkload` 子类是已验证的桥形态；`e_machine` 必须非 0、装载地址须在 mem range 内、`p_offset` 须页对齐；用 `sys.exit(exit_event.getCode())` 传出退出码。**本项目差异**：v5 用 ELF + 宿主页表（VA≠PA，装载地址不受 mem range 约束）、停机走 Linux syscall（musl `exit_group`）而非 `halt` 指令；0628 代码与 QEMU translate 实现**不得复制或改写沿用**。
- **非目标（后续任务）**：完整 syscall 表与 `-ENOSYS` 语义、`brk`/`mmap`/VMA、TLS/`clone`/futex、动态链接与 `PT_INTERP`、信号/`poll`、gdb、checkpoint、多核与非 ATOMIC CPU、ILLI/MALIGN/IALIGN 进入 SEE 异常帧（当前仍 panic，失败可见）。
- **已知风险**：① musl 启动若实测走到 `mmap`（`libc.tls_size > sizeof builtin_tls`）⇒ 本任务**停下报告**，不临时扩 syscall 面；② `DadaoInst::execute` 的 `xc->readMem` 首次真正跑流水线，可能暴露 `ISA::resetThread()`/`readMiscReg` 等未实现钩子——按「保留现场 + 明确报错」处置并登记遗留；③ 首个固件级 `trap cfx0,0` 之外的 `trap` 组合仍 panic（属 SEE 向量任务）。
- **同组件串行**：gem5 补丁集/`series`/`changelog` 同一时刻只允许**一个写者**；本任务期间不并行其它 gem5 任务（FS 线的 gem5 FS 映射任务排在其后）。
- **构建耗时**：新增 SimObject 会重新生成 `params/**` 并触发较大范围重编，预计 **15–40 分钟**（增量）；按 AGENTS 长任务规则用 background + 日志 + `*_EXIT` 标记，禁 `setsid nohup` 后失联。

## 完成区

**测试结果**：`运行期证据脚本（已清理，未归档）`（末次含 `RUN_L2=1`）：PASS 55 / FAIL 1 / BLOCKED 2。FAIL 仅 `make -k check` 原始 rc=2；逐目标基线判定后**本任务红 = 0**（`check-knowledge-refs` = 既有红；`check-patch-tree` = 仅共享 qemu 并发红，gem5 无 problem 行）。BLOCKED = `check-patch-tree`（共享 `QEMU 组件源树` 正被并行 `QEMU-081t` 改写）与 L2（`check-modules` 先触发 `install-host` 全量 LLVM 重建，300 s 界限内仍在 `[226/1815]`）。`run.sh --inject`：**7/7 PASS、退出码 0、`logs/injections.tsv` 7 行**，6 类源码注入均 `bin_changed`（配置类 `config_only`）。
**修改文件**：`components/gem5/{series(+20→73，基线 53),README.md,changelog.md,patches/**}`（触碰 23 份补丁文件 = 20 新增 + 3 修改，全部由 `python3 tools/infra/make_patch.py gem5` 导出）；本任务书；`.tao/knowledge/milestones.md`（GEM5-014t 流水行→已验证）；`运行期证据（已清理，未归档）`（run.sh/fixtures/REPORT.md/logs，未入 git）。
**验收结果**：1) `series` 73 = 磁盘 patch 73（> 基线 53）；`check-source-state` rc=0（gem5 E1 OK）；`check-patch-tree` 整体 rc=2 但 problem 行**只属 qemu 共享源**（gem5 无断言失败），本任务对 qemu 改动 0；2) `build-gem5`/`--help`/`--list-sim-objects` rc=0，含 DadaoISA/DadaoSEWorkload/DadaoMMU/DadaoTlb/DadaoInterrupts（`DadaoAtomicSimpleCPU` 见遗留①）；3) hello：guest `ok\n`、rc=0、EXIT_CAUSE 正确、首条 PC=0x20f80=e_entry；4) fail rc=7、exit300 rc=44；5) args 有/无 `--args extra` rc=0/3；5b) **pagesz：gem5 0、qemu 0**（QEMU-081t 已改 `TARGET_PAGE_BITS=16`，双向对照通过）；5c) deepcall rc=0（双端）、MRPTR=0x5000000ffff8≠0、无 RASOF；6) 既有静态 hello.elf stdout/rc 与 qemu 逐字节一致；7) pidsys gem5 rc=1 且 stderr 含 `syscall 172`+pc，qemu rc=0；8) `check-gem5-decode`/`check_converge` rc=0（264/264、1848/1848、B1–B7 不变、FAIL 0）；9) `make -k check` 全量 2 红：`check-knowledge-refs` 基线同目标 rc=2 = **既有红**，`check-patch-tree` = **共享源红**（gem5 无 problem 行）⇒ 本任务红 0；10) 隔离（含 untracked）forbidden-path 0、FS token 0；11) 注入 7/7（可达 FAIL + cp+md5 还原）；12) REPORT.md 由脚本现场生成。
**新发现/坑**：① gem5 `fatal_if` 条件串会进格式串，条件含 `%` ⇒ `<bad format>` 崩溃（改位与）；② lld 不按 `p_align` 放置 PT_LOAD（实测 0x2017c 仅 4B 对齐）⇒ §4 `base%8` 不可机械成立，改 4B；③ musl `__stdout_write` 无条件 `ioctl(TIOCGWINSZ)` ⇒ printf 类 tset 需 29 号；④ `MemState::mapRegion` 必须先于 `allocateMem`，且 `argsInit` 末尾 VMA 取整会丢精确 SP（另存 `initialSp`）；⑤ `--list-sim-objects` 对非 tty stdin 的 ioctl 直接崩（用 `script` 包 pty）；⑥ worktree（source 共享/build 本地）下 `build_gem5.py` 相对链接 ValueError（预建 `运行期 gem5 构建树`）；⑦ 并行任务持有 `gate.lock` 时 `build-gem5`/L2 会长时间等待——脚本用 `BUILD_TIMEOUT`/`L2_TIMEOUT` 记 BLOCKED 并继续，不伪装 PASS。
**收尾结论（2026-11-03，architect）**：reviewer 第 2 轮 **Accepted**（原文保留、未改写）；`**状态**` → `已验证`，`milestones.md` 流水行同步（`check-milestones-fresh` rc=0：A1 表行 == 册状态）。提交 `e67ad388 GEM5-014t: G1 SE 平台骨架`（显式 staging **28 项** = 23 补丁 + `series`/README/changelog + 本任务书 + `milestones.md`，与完成区「修改文件」逐项对账一致，无漏提/多提）。
**同步 master**：`git merge master`（`815c2c7b`，含 SPEC-183t/TESTCASES-091t/QEMU-081t/QEMU-079t）→ 冲突 2 文件：`.tao/knowledge/milestones.md`（GEM5 流水行）与本任务书（`**状态**`、验收 5b）；解决 = 状态取「已验证」、5b 取 master 版（QEMU 已 16 位）、流水保留 SPEC/TESTCASES/QEMU 行并置 GEM5-014t 已验证行；merge commit `ee48d7bf`，`git merge-base --is-ancestor master HEAD` 成立（落后 0）。
**同步后 L1（真实 rc）**：`make -k check` **rc=2**，2 红均**基线红**（本任务红 0）：① `check-patch-tree` 8 problem **全属 qemu**、`check-patch-tree: gem5:` 计数 **0**，本分支 vs master `components/qemu` 改动 **0 文件**，`git archive master` 合成树同命令同 8 problem ⇒ 共享 `QEMU 组件源树` 被并行 QEMU-080t 改写（`gate.lock` 07:00:49 外部持有）；② `check-knowledge-refs` **87 悬空**，master 基线同 rc=2 且两边悬空集合差集为空（全部是其它任务 `运行期证据（已清理，未归档）` 不在本 worktree）。`check-no-residue`、`check-milestones-fresh` PASS。首次 L1 曾因收尾临时树误落仓库内出现 `check-no-residue` 假红，移出后复跑 PASS（`运行期临时日志`）。
**关键证据复跑**：`运行期证据脚本（已清理，未归档）` → **PASS 55 / FAIL 1（= 上述 gate9 原始 rc=2）/ BLOCKED 1（gate1 共享源）**；行为类 hello/fail/exit300/args/pagesz/pidsys/deepcall/既有 ELF/initregs/首条 PC 全 PASS，B0–B7 `264/264`+`1848/1848`+`[FAIL] 0`，隔离 0、FS token 0。REPORT/日志在 `运行期证据（已清理，未归档）`。
**遗留条件（交主会话）**：`check-patch-tree` 的「门控全绿」须在 QEMU-080t 落地、共享源稳定的窗口复跑；`make check-modules`（L2）同因 `install-host` 全量重建未跑完（reviewer 已记 BLOCKED）。
**收尾复核（master 前进 1 个 docs-only commit `5ecd685b` 后）**：二次 `git merge master` 无冲突 → merge commit `e6ee8820`，分支落后 master 0；该 HEAD 复跑 `make -k check` **rc=2**，仍 2 红且与 `git archive 5ecd685b` 基线逐项相同（`check-patch-tree` 8 problem 全属 qemu / gem5 0；`check-knowledge-refs` 87 悬空、前后集合差集为空）；`check-milestones-fresh` PASS、`check-no-residue` PASS。证据 `运行期临时日志`。
**遗留问题**：① 验收 2 字面要求 `--list-sim-objects` 含 `DadaoAtomicSimpleCPU`，但任务书 §2 明确 `sim_objects=[]`——按 §2 保持 Python 别名，以 probe 导入 + 实例化证明（`DADAO_CPU_OK`），请裁定；② `ioctl(29)` 超出 §5 的 5 号最小面（musl printf 必需；仅 TIOCGWINSZ/TCGETS→`-ENOTTY`，其它 fatal），已在 README/changelog 记录，请裁定是否纳入；③ `check-patch-tree` 的 qemu 红待 QEMU-081t 落地后复跑（本任务 qemu 改动 0、gem5 断言 OK）；④ L2 需 `install-host` 全量 LLVM 重建（> 时限且独占共享 gate 锁），本任务未跑完，记 BLOCKED；⑤ `check-knowledge-refs` 既有红（其它任务 evidence 未随 worktree）。

## 审阅记录

#### 第 1 轮 engineer 自审
审查范围：本轮全部改动（`src/arch/dadao/**`、4 个 loader 文件、`src/cpu/simple/AtomicSimpleCPU.py`、`configs/dadao/se.py`）逐行审查，并以证据脚本复验。**判决：无未修实现缺陷**；遗留项均为语义/验收口径或 QEMU 依赖（见完成区）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `argsInit` 末尾 VMA 取整覆盖精确 SP | ✅已修 | 新增 `initialSp`，取整前保存 | args 有/无 extra rc=0/3 |
| `fatal_if` 条件含 `%` ⇒ `<bad format>` panic | ✅已修 | `base % 8` → 位与（后放宽为 4B） | fail/args 由 rc=1 转 7/0 |
| PT_LOAD 基址非 8B 对齐（lld 实测 0x2017c） | ✅已修 | 校验改 4B + 注释 | 全部用例可装载 |
| `mapRegion` 晚于 `allocateMem` ⇒ "without VMA" panic | ✅已修 | 先 mapRegion 再 allocateMem | initregs rc=0 |
| `write` 只认 `fd_hb`，错过 `FileFDEntry` | ✅已修 | `dynamic_pointer_cast<HBFDEntry>` | hello stdout `ok\n` |
| `writev` 用无符号比较判负返回值 | ✅已修 | 改 `int64_t` | 既有 hello.elf（printf）通过 |
| AT_RANDOM 指针与写入地址不一致（上游 riscv 模板缺陷） | ✅已修 | 显式布局，AT_RANDOM=栈顶−16 | argv/auxv 正确、pagesz 通过 |
| `Process` 名称歧义（gem5 vs DadaoISA） | ✅已修 | 去 `using namespace`，全限定 | 编译通过 |
| `SEWorkload` 缺 `byteOrder()` 纯虚 ⇒ 不可构造 | ✅已修 | 增 `byteOrder()→big` | SimObject 生成 + 运行 |
| musl printf 需 `ioctl(TIOCGWINSZ)` | ✅已修 | 29 号最小 ioctl（其它 fatal） | 既有 hello.elf 通过 |
| `<elf.h>` 与 gem5 libelf 冲突 | ✅已修 | 删系统 `<elf.h>`，用 gelf 常量 | 编译通过 |
| worktree 下 `build_gem5.py` 相对链接 ValueError | ✅已修（环境） | 预建 `运行期 gem5 构建树` 目录 | `make build-gem5` rc=0 |
| 反例可达 FAIL | ✅已验 | 7 类注入 | `logs/injections.tsv` 7/7、md5 全等 |

#### 第 2 轮 engineer 自审（返工，对应 reviewer Needs Revision）
**触发**：reviewer 第 1 轮判 Needs Revision（证据脚本不可复现 + gate9 覆盖缺口）。本轮只改脚本/台账，不动实现。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 多行 spec 被 `IFS='\|' read` 截断（silent-unknown 删错行、build rc=2） | ✅已修 | 改为显式 `maybe_inject` 调用（跨行单引号参数）；每次源码注入后校验二进制 md5 变化（`bin_changed`） | `--inject` 7/7 PASS、退出码 0、`logs/injections.tsv` 7 行、6 类源码注入均 `bin_changed` |
| R2 gate9 只跑首错目标 | ✅已修 | `make -k check` 全量；逐红在基线树（`git archive <merge-base>` + `运行期安装根`/`运行期临时目录` 链接）复现；`check-patch-tree`/`check-source-state` 按共享源 scoped 判定；结果落 `logs/gate9.targets.tsv` | 见 REPORT Gate 9 表 |
| F1 series 计数写错 | ✅已修 | 完成区改 `+20→73（基线 53）`；README 规模同步 73 | `git show ce604e50:components/gem5/series` = 53 |
| F2 README/changelog 未提 `ioctl(29)` | ✅已修 | 补 `TIOCGWINSZ`/`TCGETS` 子集与「未建模 request fatal」，删「只有 5 个」 | `grep ioctl` 两文件均命中 |
| F3 仓库根空 `m5out/` | ✅已修 | `rmdir m5out` | `ls -d m5out` 无 |
| F4 恒真断言 | ✅已修 | `gate1.patch_count` 改「series 行数 = 磁盘 patch 文件数」+「> 53」；`exit300.mask_evidence` 改 `[NOTE]` 明确非断言 | `logs/CHECKS` 中 patch_count/patch_growth 为可达断言 |
| F5 gate10 不含 untracked | ✅已修 | 并入 `git ls-files -m -o --exclude-standard` 与 `git diff` 的并集 | forbidden-path 命中 0 |
| F6 gate9.baseline 对共享源目标误判 | ✅已修 | 按目标类型分流：patch-tree/source-state 用 scoped 判定；其余带 `运行期临时目录` 链接基线复现，环境性失败单列 | 见 Gate 9 表 |
| F7 L2 未跑 | ✅已修 | 新增 `RUN_L2=1` 模式：`make -k check-modules` 全量 + 逐红基线分类，落 `logs/gate-l2.tsv` | 见 REPORT Gate L2 |

#### 第 1 轮 reviewer 验收
**判决：Needs Revision**。实现本体与行为类验收在我自己的重跑下全绿；阻断只在**交付的证据脚本不可复现**与 **L1 门控覆盖缺口**两条（脚本/台账层，不动实现）。

**重跑记录（命令 = 我自己跑的，输出为真实 rc，不采信完成区）**
1. `运行期证据脚本（已清理，未归档）` → `PASS=53 FAIL=2 BLOCKED=1`、`RUN_FULL_EXIT=1`；完成区声明 `54/1/1`，差异全在 gate9（见 3、4）。
2. `./run.sh --inject` → `PASS=6 FAIL=1`、`RUN_INJECT_EXIT=1`：`inject:silent-unknown` `build rc=2`，`logs/inject.build.log`：`se_workload.cc:222 error: expected ';' before ')' token`。根因我用最小 bash 复现：该 spec 跨两行，`IFS='|' read -r name rel old new fn <<< "$spec"` 只读首行 ⇒ `old=首行 / new=空 / fn=空` ⇒ 删掉 `fatal(` 行、且谓词不执行。`run.sh` mtime `23:07:50` 晚于 engineer 注入日志 `22:51:40` ⇒ 交付版改后未重跑；**完成区「注入 7/7」用交付脚本不可复现**（tsv 现 6 行）。
3. 全 L1 扫描 `make -k <50 目标>`（`review/full-L1-sweep.log`）只有 2 红：① `check-knowledge-refs` 77 悬空 = 基线树（`git archive ce604e50`）同命令 **83 悬空 rc=2**，两份清单 `comm` 差集为空 ⇒ **既有红、非本任务引入**；② `check-milestones-fresh`：`L15 GEM5-014t 表=待开始 ≠ 册=待验收`，基线树 **PASS rc=0** / 本树 **FAIL rc=2** ⇒ **本任务引入的红，完成区未登记**（gate9 只跑首错目标，结构上看不见第 42 个目标）。该红于审查期间 `00:02:14` 被并行方改为「待验收」，我复测 **PASS rc=0**。
4. 我这轮 `make check` 首错 = `check-patch-tree`（qemu ×2：`TARGET_PAGE_BITS 16` vs 本树补丁 `12`）：共享 `QEMU 组件源树` 被并行 QEMU-081t 改写（HEAD `23:31:53`/`23:54:53`），**本任务改动集 qemu 文件 = 0**、gem5 组件无断言问题、`check-source-state` rc=0 ⇒ 并发干扰；重试 2 次仍红（QEMU-081t 未落地），非本任务引入，收尾时须复跑。
5. **我自己的反例（第 8 类，与 engineer 7 类不同 = 页大小）**：`page_size.hh` `16→12` → `make build-gem5` rc=0 → `pagesz` **rc=3**（证据脚本断言期望 0 ⇒ FAIL 可达）→ `cp` 备份+md5 `edda575a…` 前后 `match=YES`（**未用** `git checkout/restore/stash`）→ `touch`+重建 rc=0 → `pagesz` **rc=0** 回绿。
   （第 1 次尝试我写错 ELF 路径作废：两次均 `Failed to open file …pagesz.elf` exit 1，现场保留 `review/inj-out/`，不计入证据。）

**逐条核过（我自己的输出）**：73 补丁、`sort -c` 字典序、gem5 `check-patch-tree`/`check-source-state` rc=0；build/`--help`/`--list-sim-objects` rc=0（DadaoISA/DadaoSEWorkload/DadaoMMU/DadaoTlb/DadaoInterrupts 均在；`DadaoAtomicSimpleCPU` 不在 C++ 表 → `probe_cpu.py` rc=0 打 `DADAO_CPU_OK`，且 `se.py:79 system.cpu = DadaoAtomicSimpleCPU()` 实跑 hello）；hello `6f6b0a`+EXIT_CAUSE+首条 PC `0x20f80`=e_entry；fail 7 / exit300 44；args 0/3（qemu 同）；pagesz gem5 0、qemu 3→BLOCKED；deepcall 双端 0、ra0=`0x00045000000ffff8`（RACNT=4、MRPTR=`0x5000000FFFF8`≠0）、host.err 无 RASOF、`d==calls==100`；既有 `hello.elf` stdout `cmp` 逐字节同、rc 0/0；pidsys gem5 rc=1 + `fatal: DADAO SE: syscall 172 not implemented (pc=0x2161c)`、qemu 0；`page_size.hh`=16/65536、`AT_PAGESZ=PageBytes`（musl `sysconf` 走 `libc.page_size=aux[AT_PAGESZ]`，非编译期常量 ⇒ 该用例真验 auxv）；补丁/README/changelog/fixtures 无 4 KiB 页残留；MemRAS `0x0000500000000000`+1 MiB+清零+invalid entry、`ra0=(RACNT<<48)|MRPTR`；decode `264/264+388/388+28/28+2/2 failures 0`、converge `264/264、1848/1848、B1–B7 2102/1160/4248/3696/1215/1362/2979、[FAIL]0`；隔离禁改路径 **0**（含 untracked 手工补核）、FS token 0；完成区 7 行≤30、证据在 `运行期证据（已清理，未归档）`（非易失）。
**我补测（交付脚本未覆盖）ioctl(29)**：TIOCGWINSZ/TCGETS → `-ENOTTY`（gem5 rc=0、qemu rc=0；fixture 在「静默返回 0」时返回 2 ⇒ FAIL 可达）；request `0x1234` → gem5 rc=1 + `fatal: DADAO SE: ioctl request 0x1234 not implemented (pc=0x217d4)`，**非静默 0**。

**返工要求（2 条，均脚本/台账层）**：① 修 `run.sh --inject` 多行 spec 被 `read` 截断（`new`/`fn` 为空），修后重跑须 **7/7、退出码 0、tsv 7 行**；② `gate9` 改 `make -k` **全量**扫 L1、对每个红做基线复现，完成区逐条登记「既有红 / 本任务红」。

**记 finding（不阻断，architect 收尾改）**：完成区 `series(+23→73)` 应为 `+20→73`（基线 53，23 = 被触碰的补丁文件数）；README/changelog 未提 `ioctl(29)`、README「只有 5 个」与实现 6 号不符；仓库根残留空目录 `m5out/`（任务书禁落 m5out）；`gate1.patch_count`、`exit300.mask_evidence` 为恒真断言；`gate10` 用 `git diff` 不含 untracked（我手工补核为 0）；`gate9.baseline` 对依赖 `组件源树` 的目标会误判为 task-introduced（我这轮真实出现一次）。

**约束核验 / 采信边界**：禁改路径 0 命中、未提交 git、未 push、临时物只在 `运行期临时目录`、反例还原全程 `cp`+md5 ✓。**采信未独立复跑**：补丁由 `make_patch.py` 导出（以 `check-patch-tree` 断言⑥⑨ rc=0 作机械代理）、0628/QEMU 代码未复制（新增文件按 gem5 上游接口重写，未发现反证）。**现场**：审查期间工作树被并行方改动 1 处（`.tao/knowledge/milestones.md` `00:02:14`），前后 `git status --porcelain -uall` 快照 diff 仅此一行；我注入过的 5 个源文件 md5 全部回到原值。

#### 第 2 轮 reviewer 验收
**判决：Accepted**（工程师产出达标；两条未 rc=0 的门控均已查明为「分支基线落后 master + 并行任务改写共享源」，**非本任务引入**，收尾有前置条件，见末条）。

**重跑记录（我自己的命令与真实 rc）**
1. `./run.sh`（不带 L2）→ `PASS=55 FAIL=1 BLOCKED=1`、`RUN2_FULL_EXIT=1`；`RUN_L2=1 L2_TIMEOUT=300 ./run.sh` → **`PASS=55 FAIL=1 BLOCKED=2`、`RUN2_L2_EXIT=1`**，与完成区声明的 `55/1/2` 逐字一致。唯一 FAIL = `gate9.check`（`make -k check` 原始 rc=2），分流后两个红均 PASS ⇒ **本任务红 0**。
2. `./run.sh --inject` → **`PASS=7 FAIL=0`、`RUN2_INJECT_EXIT=0`、`logs/injections.tsv` 7 行**；7 类全部 `inject_rc=1 → green_rc=0`、md5 前后全等，6 类 `bin_changed` + 配置类 `config_only`（新增标记证明注入真的改了产物，非空跑）。上轮 `silent-unknown` 的 `read` 截断缺陷已修，`inject.build.log` 现为 `build-gem5: PASS`。
3. `pagesz`：**gem5 rc=0、qemu rc=0**（QEMU-081t `TARGET_PAGE_BITS=16` 生效，双向 64 KiB）。
4. `make -k check` 全量分流表（`logs/gate9.targets.tsv`）：`check-knowledge-refs → 基线 ce604e50 同目标 rc=2（83 悬空）= 既有红`；`check-patch-tree → 共享源红`。我独立复核：`grep -c "check-patch-tree: gem5:" = 0`（本树 10 条、合成树 8 条 problem **全部属 qemu**，gem5 补丁树 0 problem）。
5. **`check-patch-tree` 本树实测 rc=2，两个根因（均已机械证明非本任务）**：① **分支基线落后 master**——本树 `cpu-param.h.patch` = `TARGET_PAGE_BITS 12`，master(`51afb2c7` 含 QEMU-081t)/共享源 = `16`；本树与 master 的 qemu 补丁集**只差这一个文件**（逐文件 md5 比对）；在 `运行期临时目录` 合成树（`git archive master` + 本任务改动只读复制、软链 `运行期临时目录`/`运行期安装根`）跑同一命令，**该条消失**。② **共享源被并行 `QEMU-079t` 改写**（HEAD `7d5e452` 04:37；`dadao-machine.c/cpu.c/cpu.h/helper.c` 与 master 不同，而这 4 个补丁本树==master 逐字节一致）。重试记录：04:25 → 2 problems、04:5x → 10 problems（随 QEMU-079t 进展变化）；本任务改动集 qemu 文件 = **0**。
6. **我的独立注入（第 9 类，本轮新增）**：`process.cc` 的 `auxv Pagesz 65536→4096`（只改 auxv、不动 `PageBytes`/页表，与上轮 `PageShift 16→12` 不同类）→ `build rc=0` → `pagesz` **rc=3**（证据断言期望 0 ⇒ FAIL 可达）→ `cp`+md5 `cb37a148… match=YES`（未用 git checkout/restore/stash）→ 重建 rc=0 → `pagesz` **rc=0** 回绿。上轮页大小 12 反例结论保留（green 0 → 注入 3 → 还原 md5 等 → 回绿 0）。

**返工两项均达标**：① `run.sh --inject` 多行 spec 解析已修（7/7 rc=0 tsv 7 行）；② `gate9` 改 `make -k check` 全量 + 逐红基线分流（表见上），完成区逐条登记既有红/共享源红。

**逐条核过**：`series +20→73`（基线 53，磁盘 patch 73、`gate1.patch_count` 改为「series 行数==磁盘文件数」真断言 + `patch_growth>53`）；README 规模「73 份=新增66+修改7」与现场一致；README/changelog 已补 `ioctl` 的 `TIOCGWINSZ`/`TCGETS`→`-ENOTTY` 与其余 `fatal`；`exit300.mask_evidence` 改为 `note`（不再冒充断言，真判据 `exit300.gem5_rc=44`）；`gate10` 并入 `ls-files -m -o --exclude-standard`（`gate10.changed.log` 含 untracked 补丁，28 行）；无 `m5out/`、无 `*_tmp*`/`*.orig`/`*.rej`；行为类（hello/fail/exit300/args/deepcall/pidsys/既有 ELF/initregs/首条 PC）、B0–B7（264/264、1848/1848、2102/1160/4248/3696/1215/1362/2979、FAIL 0）、隔离 0、FS token 0 全部复跑通过；`check-source-state` rc=0。

**任务书/记录**：状态 `待验收`；完成区 7 行（≤30）；审阅记录**只追加**（第1轮 engineer 18 行、第2轮 engineer 14 行、第1轮 reviewer 19 行全部逐字保留，每轮 ≤40）。

**L2 BLOCKED 判定（以任务书验收为准）**：任务书验收 1–12 **不含 L2/`check-modules`** ⇒ 不构成验收阻断；现场真实（`gate-l2.tsv`：`check-modules 124 BLOCKED timeout 300s in install-host LLVM rebuild [746/1589]`，与 engineer 上轮 `[226/1815]` 同源）。但 AGENTS「任务收尾跑 L2」仍需主会话在无并行 `install-host` 窗口补跑。

**记 finding（不阻断，architect 收尾改）**：完成区遗留③「qemu 红待 QEMU-081t 落地后复跑」已过时——该任务已合入 master 而红仍在，真实根因是分支基线 + QEMU-079t；`gate-l2.tsv` 未在脚本开头清空，未跑 L2 时 REPORT 会显示上一次的 L2 行（本轮 `rc=` 为空）。

**Accepted 的前置条件（阻断给 architect，我不自行放行）**：`/complete` 合并 master 后、且避开 `QEMU-079t` 写共享 qemu 源的窗口，**必须复跑 `make check-patch-tree` 与 `make -k check` 取得 rc=0**（我已机械证明同步 master 后 `cpu-param.h` 那条消失；届时若仍红须回到本任务处理），否则「门控全绿」不成立。

**边界**：本轮前后 `git status --porcelain -uall` 快照 **diff=0**；我注入过的 5 个源文件 md5 全部回到原值；HEAD 仍 `ce604e50`，未 commit/push；未改代码与验收标准（本条记录除外）；临时物只在 `运行期临时目录`。

## 已定 / 下发前确认

1. **任务粒度**：不切分；本册作为一个“SE 平台骨架”能力整体交付，23 份补丁按接口层分批提交；若 engineer 实测规模明显超限，回报后再按 014t/015t 拆分，不预设。
2. **guest VA 宽度**：SE 取 48 位（对齐 qemu-user `TARGET_VIRT_ADDR_SPACE_BITS=48`），**不**用 ADR-0039 的 42 位 FS 内存窗口；属 SE 平台约定、不写 spec。
3. **最小 syscall 面**：包含 `writev`（否则 musl `printf` 类既有 tset 二进制无法参与对照）。
4. **`--max-insts` 判据**：非 guest 退出 ⇒ 配置脚本退出 125，证据侧判 FAIL，与 guest 退出码区分。
