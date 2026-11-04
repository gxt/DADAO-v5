# GEM5-015t: FS Machine-v5-Tiny（gem5 FS Tiny 平台：BootROM/ELF/semihosting/机器 fault→退出码）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-014t`（SE 平台骨架：`loader::Dadao`、`DadaoISA::{TLB,MMU,Interrupts}`、`DadaoAtomicSimpleCPU`、`configs/dadao/se.py`，已验证）、`GEM5-013t`（B0–B7 全 264 收敛门控，已验证）、`GEM5-003t`（gem5 v25.1.0.1 / `c8222cc6` 锁定，已验证）、`QEMU-079t`（Machine-v5-Tiny 系统机，同模式参考，已验证）、`QEMU-082t`（Tiny cfx_power 不可达，已验证）、`SPEC-183t`（`spec/Machine-v5-测试机运行环境.md` 几何/装载/cfx/semihosting 真源，已验证）、`TESTCASES-091t`/`TESTCASES-092t`/`TESTCASES-093t`（测试资产与 profile 表，已验证）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；独立 `git worktree` + 分支 `GEM5-015t`，从 `master` 建；gem5 组件源树内部收敛 base+1 提交；不 merge、不 push）

## 用户已定口径（2026-11-03，主会话转达 + `spec/Machine-v5-测试机运行环境.md` 真源）

- **只做 gem5 FS `Machine-v5-Tiny`**：64 KiB BootROM `0xffff_ffff_0000`；8 MiB SRAM `0xffff_ff00_0000`；raw 镜像基址 `0xffff_ff01_0000`、前 `0x100` 字节全零、应用入口 `0xffff_ff01_0100`、`SP = 0xffff_ff7e_ff00`；ELF 的 crt/启动 stub 在 BootROM（`e_entry` 同址）、应用段在 SRAM。
- **Tiny 能力边界**：`addr[47:42]` 恒 `0x3F`；**无任何 cfx**（含 `cfx_power`）、**无 PTW/页表**、**不能进入 `user`**、无 hmon/smon 与异常向量；**允许 semihosting**（`trap` 只作陷入宿主开关）；`AtomicSimpleCPU`，**无时序/无 cache**。
- **同模式对照**：gem5 FS **只对 QEMU system**（`qemu-system-dadao -M dadao-m1`，profile tiny），不对 QEMU user（ADR-0048 D1/D2）。**gem5 通过而 QEMU 未通过 ⇒ 不得直接接受 gem5**，记录并另立 QEMU 调试任务；**spec/contracts 不清 ⇒ 停下提交用户裁定**，不得按 RISC-V/ARM 经验补全。
- **测试资产复用**（只读，不改）：`tests/shared/machine-profiles.yaml`（`tiny` 几何）、`tests/shared/crt0/minimal_crt0.s`、`tests/shared/linker/dadao-tiny.lds`、`tools/testcases/lib/{build_test_binary.py,run_qemu_test.py,machine_profile.py,gen_trampoline.py,trampoline.bin}`、`tools/testcases/inst/run_qemu_smoke.py`、`tools/testcases/tset/embench/run_embench_e2e.py`、`tools/testcases/picolibc_tests.py`。
- **改动范围（硬）**：只 `components/gem5/**`（补丁/`series`/`changelog.md`/`README.md`）+ 本任务书 + `.tao/knowledge/milestones.md`。**不改** `spec/**`、`tests/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`、`tools/**`、`components/{qemu,llvm-project,musl,picolibc,embench-iot}/**`、`docs/**`；**不复制 0628/QEMU 代码**（0628 只读、只吸收结论并标「内容溯源，非执行必需」）。

## 现状与问题根源（2026-11-03 现场核对，只读）

1. **gem5 侧只有 SE 平台，没有 FS 机器模型**：`src/arch/dadao/` 现含 `process.{hh,cc}`、`se_workload.{hh,cc}`、`tlb.{hh,cc}`（SE 直通 `Process::pTable`）、`mmu.hh`、`interrupts.hh`、`page_size.hh`、`DadaoSEWorkload.py`/`DadaoCPU.py`/`configs/dadao/se.py`；**没有** FS `Workload`、boot ROM、内存映射、semihosting、机器 fault→退出码，也没有 `System`/`AtomicSimpleCPU` 的 FS 配置。
2. **fault 路径全部 panic，且不分模式**：`faults.hh` 的 `IllegalInstruction`/`MalignInstruction`/`UnimplementedInstruction` 均 `panic`；`inst.cc::mapExecFault` 对 `RasOverflow/RasUnderflow/CfxReg/CfxEsc` 也 `panic`；`Gem5B1Context::trapTo` 只接 `trap cfx0,0`（SE syscall），其余（含 semihosting tag `0x3FF00–0x3FFFF`）`panic`；`escapeFrom` 恒 `false`。Tiny 要求「机器 fault 直接映射退出码、无异常向量」（`spec/Machine-v5 §1.2/§3/§4`），且这些 panic 在 SE 下必须保持原样（不得借 FS 改写 SE 语义）。
3. **UNDI/ILLI 未区分**：`decode::DecodedInst::ok()` 为假（空白 opcode 字节/空子表槽）与「已分配 id 的静态合法性违反」目前都落到 `IllegalInstruction`（`0x88`）；Tiny 的 `inst` 向量要求前者为 **UNDI `0x89`**（`tests/inst/schema.md`：`encoding.reserved ⇒ UNDI`）。
4. **无 semihosting**：SE/Tiny 的停机与控制台协议都是 semihosting（`spec/Machine-v5 §5`、`contract-semihosting §1/§2/§5`；`ADR-0020 D8`）；gem5 侧现无任何服务实现。gem5 上游已有可复用的通用骨架 `src/arch/generic/semihosting.hh`（`BaseSemihosting`，24 个服务 + 文件/时间基础设施；RISC-V 用 `src/arch/riscv/semihosting.*` 做 ISA 适配），本任务**按接口重写 DADAO 适配**，只缺 `SYS_SYNCCACHE (0x19)`。
5. **QEMU 侧已有同模式参考且已验证**：`QEMU-079t` 实现 `profile=tiny`（`-bios` 64 KiB 复位窗口 + raw/ELF 两条装载、fault 直出、semihosting 25 服务）；测试资产 `tests/shared/**` + `tools/testcases/**` 已按 Tiny 落地（`TESTCASES-091t/092t/093t`）。本任务**不改 QEMU**，只在 gem5 侧重做同模式机器。
6. **可构建基线**：`gem5 组件源树` = `c8222cc6` + 1 个 dadao 补丁提交（现场 `4c08f32`，干净）；`build/DADAO/gem5.opt` 已存在（2026-11-03 05:02，可增量）。新增 SimObject 会重生成 `params/**`，预计增量重编 **15–40 分钟**。

## 目标

在 gem5 上补齐 **Machine-v5-Tiny 的 FS 平台**，使 `tests/inst`、Embench（system 模式 E2E）、picolibc 测试集能在 gem5 FS 上真实执行，并与 QEMU system（`profile=tiny`）在**同一 case ID 上通过/失败与退出码一致**：

1. FS 机器模型：BootROM/SRAM 两段物理内存、复位与初值、raw/ELF 两条装载路径。
2. Tiny 地址检查与机器 fault→退出码（无异常向量、无 PTW、无 cfx、不能进 user）。
3. semihosting（25 服务、64 位大端、`rd16`/`rb16`→`rd8`、`IP+=4`）与控制台/停机闭环。
4. 与 QEMU 的同模式对照矩阵（inst 代表集 + 全量非 cfx、embench、picolibc）与逐条归因。
5. SE 线零退化（`GEM5-014t`）与 B0–B7 零退化（`GEM5-013t`）。

## 接口规范

### 0. 机器几何与复位（Tiny，冻结；`spec/Machine-v5 §1/§1.1`）

| 区域 | 基址 | 大小 | 访问 | 说明 |
| --- | --- | --- | --- | --- |
| BootROM | `0xffff_ffff_0000` | 64 KiB | 取指/读；**写 ⇒ ILLI `0x88`** | 复位向量 = 基址；内容为复位/启动 stub |
| SRAM | `0xffff_ff00_0000` | 8 MiB | 取指/读/写 | 唯一可写存储；末尾 `0xffff_ff7f_ffff` |
| 其余 | — | — | **CFXMEM `0x81`** | `addr[47:42]==0`、gap `0xffff_ff80_0000–0xffff_fffe_ffff`、cfxha 63 段内越界；**取指与数据同等对待** |

- **复位**：`PC = rb0 = 0xffff_ffff_0000`；`rb1–rb63 = 0`（SP 由启动 stub/crt 设置，平台**不得**代设）；`rd* = 0`；`ra* = 0`；`rf0 = 0x7FF8_0000_7FC0_0000`（FCSR 复位常量，同 `GEM5-014t §3`）；`rf1–rf63 = 0`。**不得**注入其它初值。
- **物理内存零初值**：两段 `SimpleMemory` 由 gem5 匿名映射（零），与 QEMU RAM 一致；**不得**用非零填充或镜像外的旧内容。
- **运行模式**：名义 hypv / cfxha 63，**无模式切换路径**（`switch_run_mode` 等属 cfx 写 ⇒ `0x84`），`ISA::inUserMode()` 在 FS 返回 `false`（SE 仍 `true`）。
- **配置常量来源**：`configs/dadao/fs.py` 的几何常量与 `tests/shared/machine-profiles.yaml` 的 `tiny` **逐项相等**（ROM/SRAM/复位/`kernel_base`/`kernel_reserved`/`entry`/`sp`）；配置须提供 `--dump-geometry` 打印实际生效值（供证据机械比对，禁止手写副本漂移）。

### 1. 装载路径（`spec/Machine-v5 §6`；对照 `QEMU-079t §2`）

- **`--bootrom <flat>`（可选）**：flat 镜像 ≤ 64 KiB，装在 ROM 基址，其余 ROM 保持零；机器 PC = ROM 基址。**raw `--kernel` 必须给 `--bootrom`**（否则 `fatal` 非零退出，不猜入口）。
- **`--kernel <file>`**：自动识别。
  - **ELF**：`loader::Dadao` 识别（`GEM5-014t §1` 已建）且 `ELFCLASS64`/`ELFDATA2MSB`/`ET_EXEC`/`e_flags&0xff==1`/无 `PT_INTERP`；全部 `PT_LOAD`：`p_vaddr == p_paddr`、`p_filesz ≤ p_memsz`、`[p_vaddr, p_vaddr+p_memsz)` ⊆ ROM ∪ SRAM；`e_entry` ∈ ROM ∪ SRAM（Tiny 实测 = ROM 基址）；BSS 尾巴由 `MemoryImage` 零填充（`contract-elf §5.2`）。**ELF 与 `--bootrom` 同给 ⇒ `fatal`**（ELF 自带 ROM crt，二者会重叠；见「待确认口径」3）。
  - **raw**：长度 ≤ `8 MiB − 0x100`；**前 `0x100` 字节必须全零**；装到 `0xffff_ff01_0000`；应用入口固定 `0xffff_ff01_0100`（由 BootROM trampoline 以普通跳转移交，`SP` 由 trampoline 设为 `0xffff_ff7e_ff00`）。
- **入口规则**：`entry = bootrom ? 0xffff_ffff_0000 : elf.e_entry`；平台**不设 SP**。
- 任一校验失败 ⇒ `fatal()` 打印具体项（文件/段/字段/值）+ 非零退出；**不得**跳过、裁剪或静默重定位。

### 2. FS 翻译与地址检查（新文件，SE 路径不动）

- 新增 **`DadaoFsTlb`**（`BaseTLB` 子类）：identity `VA == PA`，**无** PTW/PTBR/TLB 填充/A-D/页表；实现 `translateAtomic`/`translateTiming`/`translateFunctional`/`finalizePhysical`/`demapPage`/`flushAll`/`takeOverFrom`。
- 检查顺序（每条都有可达 FAIL 证据）：
  1) **取指** `vaddr % 4 != 0` ⇒ IALIGN `0x8D`；
  2) 访问区间 `[addr, addr+size)` 必须完整落在 ROM 或 SRAM（跨界算越界）；
  3) ROM 上的 **store** ⇒ ILLI `0x88`（只读区）；取指/load 允许；
  4) 其余 ⇒ CFXMEM `0x81`。
- **SE 隔离**：`DadaoISA::TLB`/`Process`/`SEWorkload` 的现有语义与文件**不改**；`GEM5-014t §7` 的 SE 文本门控须继续成立（`src/arch/dadao/{process,se_workload,tlb,mmu}.*` 与 `configs/dadao/se.py` 注释剥离后不含 `bootrom`/`ptbr`/`ptw`/`semihosting`/exit-port token，计数 0）——因此 FS 逻辑一律放**新文件**。

### 3. 机器 fault → 退出码（`ADR-0004 D5.8`；`spec/Machine-v5 §1.2/§3/§4`）

| 情形 | 退出码 |
| --- | --- |
| CFXMEM（越界访存/取指、`addr[47:42]==0`、gap、cfxha63 段内越界） | `0x81` |
| CFXREG（`cfx2rd`/`cfx2rc` 任一 cfxha；Tiny 无 cfx） | `0x84` |
| ILLI（已分配 id 的静态合法性违反；ROM 写；非 semihosting `trap`/`escape`；`escape`） | `0x88` |
| UNDI（opcode 表空白/子表空槽，**无 id**） | `0x89` |
| RASOF / RASUF | `0x8A` / `0x8B` |
| MALIGN（数据访问未对齐，含 `lr`/`sc`/`ldm`/`stm`） | `0x8C` |
| IALIGN（取指 `PC % 4 != 0`） | `0x8D` |

- 实现方式：新增 `MachineFault(code, name)`（`FaultBase`），`invoke()` 记录并 `exitSimLoop(name, code)`（**首个 fault 锁定退出码**，不再执行后续 guest 指令）；非 guest 停机（panic/超时）不得映射为 guest 码。
- **仅在 Tiny FS 生效**：SE 保持现有 panic 行为（`GEM5-014t` 验收不变）；用 workload/系统类型判定，不得用全局开关波及 SE。
- UNDI/ILLI 区分：`!decoded.ok()`（无 id）⇒ UNDI；B1–B7 的 `exec::Fault::Illegal`（有 id、违反 `legality`）⇒ ILLI。若某具体编码的归类在 spec/contracts 中不可机械判定 ⇒ **停下问用户**，不得按 QEMU 实测反推期望值。
- **无异常向量、无 hmon/smon**：fault 不得「进入向量」或恢复执行；`rb0` 等现场不留可观测异常帧（Tiny 语义）。

### 4. semihosting（`spec/Machine-v5 §5`；`contract-semihosting §1/§2/§3/§4/§5`；`ADR-0038 D1`、`ADR-0020 D2/D4/D8`）

- **入口判定**：`trap <any cfxha>, immu18` 且 `immu18[17:8] == 0x3FF` ⇒ semihosting（**与 cfxha 无关**）；服务号 = `immu18 & 0xFF`；非该区间 ⇒ 一般 trap（Tiny ⇒ ILLI `0x88`）。
- **调用约定**：操作号 `rd16`、参数块指针 `rb16`、返回 `rd8`；参数块字段 **64 位大端**；完成后 **`IP += 4`**（`ADR-0020 D4`，不进入向量）。
- **服务集 = 完整 25 个**（`spec §5.3` 表，按表派生、不写死条数）：`0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0C,0x0D,0x0E,0x0F,0x10,0x11,0x12,0x13,0x15,0x16,0x18,0x19,0x20,0x30,0x31`。实现基于 gem5 `src/arch/generic/semihosting.hh` 的 `BaseSemihosting`（24 服务 + 文件/时间基础设施）**按接口写 DADAO ISA 适配**（`Abi64::State` 读 `rb16`、大端；`Result` 写 `rd8`），并补 `SYS_SYNCCACHE (0x19)` 为空操作。
- **控制台/停机**：`SYS_WRITEC`/`SYS_WRITE0` → 宿主 console（默认 stdout，可 `--console-out <path>`）；`SYS_EXIT`/`SYS_EXIT_EXTENDED` → `exitSimLoop`，**退出码取低 8 位并忠实传播到 host `$?`**（如 `300 ⇒ 44`）。
- **`SYS_GET_CMDLINE`**：由 `--semihost-argv a b …`（或 QEMU `-semihosting-config ...,arg=…` 映射）提供，空格连接，与 QEMU 侧同字符串。
- **`SYS_SYSTEM`**：按 `ADR-0020 D7` 默认**不执行**（返回确定错误并记日志），`--semihost-system=native` 显式开启；不得静默执行宿主命令。
- **未知服务号**：`fatal("DADAO FS: semihosting op %#x not implemented (pc=%#x)")` —— 带号与 pc、非零退出，**不得返回 0/`-ENOSYS` 后静默继续**。

### 5. CPU / System 构成（无时序）

- 复用 `GEM5-014t` 的 `DadaoISA`/`DadaoDecoder`/`DadaoInterrupts`；新增 `DadaoFsTlb`（`BaseTLB` 子类，见 §2）、`DadaoFsMMU`（**独立 SimObject**：新 C++ `DadaoISA::FsMMU : BaseMMU`，`itb`/`dtb` 为 `Param.BaseTLB` 且默认 `DadaoFsTlb`；`translateFunctional` 同 SE 返回 `MMUTranslationGen(PageBytes, …)`）、`DadaoFsAtomicSimpleCPU`（`DadaoAtomicSimpleCPU` 的 Python 子类，`mmu = DadaoFsMMU()`——`BaseCPU.mmu` 已是 `Param.BaseMMU`）。**不**改 `DadaoMMU.py`/`DadaoTlb.py`（SE 文件保持原样）。
- `System(mem_mode='atomic')`、`SystemXBar`、**两个** `SimpleMemory`（ROM 64 KiB、SRAM 8 MiB，`range` 精确；`system.mem_ranges` 同步为这两段），`system.system_port` → `membus.cpu_side_ports`，`system.workload = DadaoFsWorkload(...)`；`cpu.createInterruptController()`、`cpu.createThreads()`；`Root(full_system=True, system=system)`。
- **无** cache、无平台设备（UART/RTC/CLINT/PCI）、无 GDB、无 checkpoint、无 multi-core、无 KVM；`mem_mode=atomic` 为唯一模式。
- `DadaoFsWorkload`（`Workload` 子类）：`bootrom`/`kernel`/几何参数/`semihosting`；构造期完成 §1 校验；`initState()` 用 `system->physProxy` 写镜像（ROM 段与 SRAM 段分别落位）后对 `system->threads` 逐线程 `resetThread()` + `activate()`；`getArch()→loader::Dadao`、`byteOrder()→big`、`getEntry()` 按 §1、`symtab()` 返回镜像符号表。
- `ISA::resetThread()`（FS）：按 §0 复位寄存器并置 `PC = workload->getEntry()`；SE 的 `Process::initState` 路径不变。

### 6. 配置脚本 `configs/dadao/fs.py`（新增）

- CLI：`--kernel <file>`（必填）、`--bootrom <file>`、`--semihost {on,off}`（默认 on）、`--semihost-argv <a,b,…>` 或重复 `--semihost-arg`、`--semihost-system {deny,native}`（默认 deny）、`--console-out <path>`、`--max-ticks <n>`（安全上限，命中 ⇒ 非 guest 退出 125）、`--dump-geometry`、`--dump-semihost-services`、`--outdir`（gem5 既有）。
- 退出：`exit_event = m5.simulate()`；`getCause() == "exiting with last active thread context"` ⇒ `sys.exit(exit_event.getCode() & 0xff)`；否则打印 cause 并 `sys.exit(125)`。
- `--dump-geometry` 输出 `GEM5_GEOMETRY key=value` 行（ROM/SRAM/复位/`kernel_base`/`kernel_reserved`/`entry`/`sp`）；`--dump-semihost-services` 输出 C++ 服务表实际键（供 §4 的 25 项机械比对）。
- **禁**在仓库内落 `m5out/`：证据统一 `--outdir <运行期临时目录>`。

### 7. 同模式对照驱动（证据层，不入 git）

- 证据层提供 **QEMU→gem5 参数映射 shim**（`运行期临时目录` 或 `运行期证据（已清理，未归档）` 下，**不进仓库**），接受并只映射：`-M dadao-m1[,profile=tiny]`、`-bios <file>`、`-kernel <file>`、`-semihosting-config enable=on,target=native[,arg=…]`、`-nographic`、`-display none`、`-monitor none`；转调 `gem5.opt --outdir … configs/dadao/fs.py …`。**未知参数必须报错退出（rc=2）**，不得静默丢弃；不得改变判据（只看 guest 退出码/控制台）。
- 复用现有驱动（只读，不改）：`run_qemu_test.py`/`run_qemu_smoke.py`/`run_embench_e2e.py` 的 `--qemu <shim>`；picolibc（`tools/testcases/picolibc_tests.py` 硬编码 QEMU，无 `--qemu`）用「QEMU 基线产物复用」：`--stage fast --work-dir <dir> --json <qemu.json>` 产出 `<dir>/<name>.elf`，再用 gem5 逐个重跑并与 `qemu.json` 分类逐项比对。
- 至少 **1 条** 用例必须**绕过 shim**、直接 `gem5.opt configs/dadao/fs.py …` 运行，证明结论不只依赖映射层。

## 文件范围

**新增补丁**（`components/gem5/patches/`，一文件一补丁；由 `python3 tools/infra/make_patch.py gem5` 导出，禁手改）：

- `src/arch/dadao/fs_workload.hh/.cc`、`fs_tlb.hh/.cc`、`fs_mmu.hh`、`fs_machine.hh`、`semihosting.hh/.cc`（FS 专用，命名可调但须独立于 SE 文件）
- `src/arch/dadao/DadaoFsTlb.py`、`DadaoFsMMU.py`、`DadaoFsWorkload.py`、`DadaoSemihosting.py`、`DadaoFsCPU.py`
- `configs/dadao/fs.py`

**修改补丁**：`src/arch/dadao/SConscript`（`Source()` + `SimObject()`）、`isa.hh`/`isa.cc`（`resetThread()`、FS 的 `inUserMode()`）、`faults.hh`（`MachineFault`/UNDI）、`inst.cc`（`trapTo`/`escapeFrom`/`mapExecFault` 的 FS 分支；SE 分支语义逐字保留）。

**仓库侧**：`components/gem5/series`（+N，字典序）、`components/gem5/changelog.md`（`## M11` 节追加一条 `- **<日期> GEM5-015t**` + 摘要缩进行 + `  - 执行者：engineer`）、`components/gem5/README.md`（FS 段：构成/CLI/边界/已知限制）、本任务书、`.tao/knowledge/milestones.md`。

**不改**：见「用户已定口径」的硬范围；证据/临时物只落 `运行期证据（已清理，未归档）`、`运行期日志（已清理，未归档）`、`运行期临时目录`（均不入 git）。

## 验收标准

1. **补丁/源树/构建/对象注册**：`make check-patch-tree` rc=0（gem5 作用域；补丁数现场统计，`series` 行数 = 磁盘 patch 数且字典序）；`make check-source-state` rc=0（gem5 HEAD = base+1、worktree 干净）；`make build-gem5` rc=0；`gem5.opt --help` rc=0；`gem5.opt --list-sim-objects` 含 `DadaoFsWorkload`/`DadaoSemihosting`/`DadaoFsTlb`/`DadaoFsMMU`（`DadaoFsAtomicSimpleCPU` 是 Python 别名，以 probe 导入 + 实跑为等价证据）。
2. **几何/复位/零初值**：`--dump-geometry` 与 `tests/shared/machine-profiles.yaml` `tiny` 逐项相等（BootROM 首址/大小、SRAM 首址/大小、复位 PC、`kernel_base`、`kernel_reserved`、`entry`、`sp`）；guest 侧 fixture 观测复位后 `rb0 == 0xffff_ffff_0000`、`rb1 == 0`、`rf0 == 0x7FF8_0000_7FC0_0000`、其余 GPR/RA = 0；未写内存读回零。
3. **BootROM/raw**：flat bootrom ≤ 64 KiB 装 ROM 基址并从基址执行；raw 镜像实际落在 `0xffff_ff01_0000`（fixture 以链接地址自证 / 取指 PC 证据）、入口 `0xffff_ff01_0100`、trampoline 后 `SP == 0xffff_ff7e_ff00`；**前 `0x100` 非零 ⇒ rc≠0**；**raw 无 `--bootrom` ⇒ rc≠0**；`--bootrom` 超 64 KiB ⇒ rc≠0。
4. **ELF 路径**：Tiny ELF（crt 在 ROM、应用在 SRAM）装载执行，`readelf` 实测 `e_entry = 0xffff_ffff_0000` 且 `PT_LOAD` 落 ROM/SRAM；退出码经 `SYS_EXIT` 传播（含 `300 ⇒ 44`）；段越界 / `ET_DYN` / 非大端 / `PT_INTERP` / `--bootrom` 同给 ⇒ 均 rc≠0 且报具体项。
5. **地址检查与 fault 码**：逐项实测退出码——ROM 写 `0x88`；`addr[47:42]==0` 数据/取指 `0x81`；gap `0x81`；cfxha63 段内越界 `0x81`；MALIGN `0x8C`；IALIGN `0x8D`；静态 ILLI `0x88`；UNDI `0x89`；RASOF/RASUF `0x8A/0x8B`；`cfx2rd`/`cfx2rc` 任一 cfxha `0x84`；非 semihosting `trap`/`escape` `0x88`；**无路径进入 user/PTW**（无相关寄存器/状态可写）。
6. **semihosting**：`--dump-semihost-services` 的服务号集合 == `spec/Machine-v5 §5.3` 表（机械派生，不写死条数）；动态：`SYS_WRITEC`/`SYS_WRITE0` 控制台字节逐字节正确、`SYS_EXIT`/`SYS_EXIT_EXTENDED` 退出码正确且**首个退出即锁定**、`SYS_GET_CMDLINE` 返回 `--semihost-argv`、未知服务号 ⇒ fatal 带号与 pc、完成后 `IP += 4` 且 `rd8` 为返回值；`SYS_SYSTEM` 默认 deny（不执行）、`native` 显式开启后才执行。
7. **inst 同模式一致**：`run_qemu_smoke.py`（Tiny 代表集，`--qemu <shim>`）与 QEMU 基线**逐例 PASS/FAIL 与退出码一致**；全量 Tiny 子集按 `make check-inst` 的同一形态直接调用 `tools/qemu/semantics_gate.py --vectors tests/inst --qemu <shim> --trampoline tools/testcases/lib/trampoline.bin --only-profile-cases`（`DADAO_TEST_PROFILE=tiny`，递归覆盖 `tests/inst/**`；QEMU 侧同命令换 `--qemu` 为 `qemu-system-dadao`），产出逐 case 对照表：**QEMU 通过集合 ⊆ gem5 通过集合**、无 gem5-only 失败；差异逐条归因到「测试资产 / spec 不清（提交用户）/ 实现缺陷（本任务修）」。**gem5 通过而 QEMU 未通过**的 case 记录并另立 QEMU 调试任务（不阻断本任务）。
8. **Embench（system E2E）**：`run_embench_e2e.py --qemu <shim> --opt O0,O2` rc=0（**19** benchmark × 2 档 = **38** case，全部 ELF 经 gem5 执行、guest 退出码 0；语料 `embench-iot/src/` 实为 19 个，QEMU-079t 基线同为 38/38，`executed == discovered` 有断言）；其 `--inject` 自检的**工具契约**是「检出注入的错值 ⇒ rc=0、未检出 ⇒ rc=1、setup 错 ⇒ rc=2」，即本验收要求 **rc=0 且输出 `INJECT: PASS`**（判据可失败）。（收尾修正，finding 2：原文「22 benchmark」「必须返回 1」与现场/工具相反。）
9. **picolibc**：`--stage fast` 的 QEMU 基线 JSON 与 gem5 重跑分类逐项一致（`pass`/`excluded`/`blocked` 集合相同、无新增 `fail`）；同 argv（`SEMIHOST_ARGS_TESTS`）与同 ELF（QEMU work-dir 产物）比较。
10. **SE 与 B0–B7 零退化**：`configs/dadao/se.py` 的 `hello`/`fail` fixture rc/stdout 与 `GEM5-014t` 基线一致（SE 的 panic/fault 行为不变）；`make check-gem5-decode` rc=0（`264/264`、`388/388`、`28/28`、`2/2`、`failures 0`）；`python3 tools/gem5/check_converge.py` rc=0 且 ids/boundary/B1–B7 计数不变（`[FAIL] 0`）。
11. **L1/L2/隔离/台账**：`make check`（L1）rc=0 或「本任务红 = 0」且逐条基线复现；L2（`make check-modules`）rc=0，若被共享 `install-host`/gate.lock 阻塞则记 BLOCKED + 现场（不得伪装 PASS）；`git diff --name-only <base>` 只命中 `components/gem5/**` + 两本册；`check-component-changelog`/`check-milestones-fresh`/`check-tasks`/`check-no-residue` rc=0；无 `m5out/`、无 `*_tmp*`/`*.orig`/`*.rej`。
12. **证据/注入/完成区**：`运行期证据（已清理，未归档）` 一键脚本（`run.sh`、`run.EXIT`、`REPORT.md`、日志）+ `run.sh --inject` 覆盖 §必测反例、每类「注入 → FAIL（rc≠0/错误行）→ `cp` 备份 + md5 对账还原 → 回绿」；完成区 ≤30 行；状态 `待验收`。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **SRAM 大小**：临时改 8 MiB→4 MiB ⇒ 几何断言/trampoline 后 SP 落点或某个 inst case FAIL；还原回绿。
2. **复位向量**：PC 改为 SRAM 基址（或 `getEntry()` 返回 0）⇒ 启动即越界/无输出，验收 2/3 FAIL。
3. **raw 前缀零校验**：关闭 `0x100` 校验 ⇒ 前缀非零镜像被接受，验收 3 FAIL。
4. **ROM 写保护**：允许 store 到 ROM ⇒ 验收 5 的 ROM 写用例返回 0 而非 `0x88`。
5. **越界检查**：TLB 去掉区间检查（恒 identity）⇒ `CFXMEM` 用例返回 0/UNDI 而非 `0x81`，验收 5 FAIL。
6. **UNDI/ILLI**：把 `!decoded.ok()` 改回 ILLI ⇒ UNDI 用例得 `0x88`，验收 5/7 FAIL。
7. **退出码传播**：`SYS_EXIT` 丢弃子码或不取低 8 位 ⇒ `300` 读成 `300`/`0`，验收 4/6 FAIL。
8. **semihosting 返回寄存器**：返回写 `rd16` 而非 `rd8` ⇒ 控制台/停机用例 FAIL（验收 6）。
9. **semihosting 入口 tag**：改成旧 `immu18[17:16]==0b11` ⇒ `0x3FF00+op` 之外的 tag 误判，验收 6 FAIL。
10. **SE 回归**：让 `MachineFault` 在 SE 生效（或 `inUserMode()` 恒 false）⇒ 验收 10 的 SE 基线/decoder 断言 FAIL。

## 证据

- `运行期证据（已清理，未归档）`：`run.sh`（构建 → 几何/semihosting 静态比对 → 本册自带 fixtures → inst 代表集 + 全量对照 → embench e2e + `--inject` → picolibc fast 对照 → SE/B0–B7 回归 → L1/L2 → 隔离），逐项落 `*_EXIT=<rc>`；日志 `运行期日志（已清理，未归档）` 与 `运行期临时目录`（gem5 `--outdir` 只落此处）。
- `REPORT.md`：**数字全部脚本现场生成**（补丁数、sim-object 列表、几何 dump、25 服务表比对、逐 case 对照统计、embench/picolibc 分类、B0–B7 计数、注入表「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」）。
- 工具链/依赖缺失（`安装根 bin 下的 {clang,ld.lld,llvm-mc,qemu-system-dadao}`、`组件源树 {gem5,embench-iot,picolibc}`、`scons`）⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明（风险 / 非目标 / 溯源）

- **参考来源（内容溯源，非执行依赖）**：gem5 上游 `src/arch/riscv/bare_metal/fs_workload.*`（`Workload` 子类 + `physProxy` 写镜像 + `resetThread()` + `activate()` 形态）、`src/arch/riscv/semihosting.*` 与 `src/arch/generic/semihosting.hh`（`BaseSemihosting` + 每 ISA 的 `Abi64::State`/`Result`/`InPlaceArg` 适配）。**本项目差异**：Tiny 无页表/PTW（identity + 段检查），fault 直接映射退出码（无向量），`SP` 不由平台设置，semihosting 返回 `rd8`、参数块 **大端 64 位**、补 `SYS_SYNCCACHE`；**不复制**代码，也不复制 0628 实现。
- **风险**：R1 高位地址（ROM 末地址 = `0x1_0000_0000_0000`）与 `AddrRange`/`SimpleMemory` 边界语义（先做最小 probe）；R2 `system->physProxy` 依赖 `system_port` 已连接（`initState` 时序）；R3 Atomic fetch 走 `translateTiming`/`translateAtomic` 双路径，fault 传播需实测；R4 `BaseSemihosting` 的 ABI 适配（`Abi64::State` 读 `rb16`、大端、`rd8`）与 `SYS_GET_CMDLINE` 的 argv 连接语义；R5 全量 inst 的 UNDI/ILLI 归类若有 spec 不清 ⇒ 用户裁定；R6 gem5 atomic 下 embench/picolibc 耗时（picolibc `test-memmem` 等慢例已有 1200 s 预算，gem5 可能更慢，必要时提高 `--timeout` 并记录）；R7 gem5 组件串行（同一时刻只一个写者；构建 15–40 min，用 background + 日志 + `*_EXIT`）。
- **非目标**：Machine-v5-Node、hmon/smon、PTW/TLB 页表、A/D、cfx（含 `cfx_power`）、`user`/`supv` 模式、中断/定时器、cache/时序、多核、checkpoint、GDB、动态链接/TLS/线程（SE 线后续）、`tests/arch`（Tiny `arch=false`）。
- **待确认口径（本册已按推荐值写，用户可否决）**：① `SYS_SYSTEM` 默认 deny、`native` 显式开启（`ADR-0020 D7`）；② ELF 与 `--bootrom` 同给 ⇒ `fatal`（避免 ROM 重叠，QEMU ELF 路径也不传 `-bios`）；③ picolibc 对照走「复用 QEMU work-dir 的 ELF 重跑」，因 `tools/testcases/picolibc_tests.py` 硬编码 QEMU 路径且 `tools/**` 禁改；④ 全量 inst 以「QEMU 通过集合 ⊆ gem5 通过集合」为硬门（而非仅 L2 代表集）。
- **失败处置**：保留现场（命令/完整输出/退出码/日志）后继续推进；自行处置（修/绕行/有据重试并记次数/登记后跳过）；**只在需要用户语义裁定（spec/契约不清、新增决策）时留问**。

## 完成区

**测试结果**：`运行期证据脚本（已清理，未归档）`（分 phase 亲跑，日志在 `运行期日志（已清理，未归档）` 与 `运行期临时目录`）：meta+fixtures **76 CHECK / 0 FAIL**；inst smoke 90/90（QEMU 与 gem5 同）；inst 全量 **1003/1003 双引擎逐例 PASS**、QEMU 通过集合 ⊆ gem5、无 gem5-only 失败；Embench **38/38**（O0/O2，`--timeout 600`）+ `--inject` 判据可达（检测到错误期望）；picolibc QEMU 基线 18 pass/2 excluded/0 fail，gem5 17 pass/2 excluded/**1 blocked（`math_test`，既有 B7 数值差异，非 FS 路径）**、无新增 fail；SE hello/exit42/exit300 全过；decode 264/264+388/388+28/28+2/2、converge 264/264+1848/1848+B1–B7 全零退化；注入 **10/10**（注入红、`cp`+md5 还原、回绿）。
**修改文件**：`components/gem5/patches/**`（15 新增 + 6 修改；`series` 89）、`components/gem5/changelog.md`、`components/gem5/README.md`、`.tao/tasks/gem5/GEM5-015t-FS-Machine-v5-Tiny.md`、`.tao/knowledge/milestones.md`、`运行期证据（已清理，未归档）`（不入 git）。
**验收结果**：`--dump-geometry` 9 项与 profile tiny 逐项相等；复位 fixture 观测 `PC=rb0=BASE/ROM`、`rb1=0`、`rf0=0x7FF800007FC00000`、其余 GPR/RA=0、未写 SRAM 读回 0；rawcheck 观测入口 `0xffffff010100` 与 `SP=0xffffff7eff00`；ELF `e_entry=0xffffffff0000`、PT_LOAD 落 ROM/SRAM、`return42→42`、`return300→44`；fault 实测 ROM 写 0x88、`addr[47:42]=0`/gap/cfx63 越界 0x81、MALIGN 0x8C、IALIGN 0x8D、静态 ILLI 0x88、UNDI 0x89、cfx2rd/cfx2rc 0x84、非 semihosting trap/escape 0x88；semihosting 25 服务（C++ 表实际键）与 spec §5.3 集合相等，WRITEC/WRITE0 字节、`SYS_EXIT` 300→44/首退出锁定、GET_CMDLINE=`alpha beta`、未知号 fatal 带 `0x7f`+pc、`--console-out` 文件逐字节、`SYS_SYSTEM` deny 不执行/native 执行均实测；`make check-patch-tree` rc=0（294 patches）、`check-source-state` gem5 HEAD=`5b2bc85` base+1 clean；L1 `make -k check` rc=2、**2 红均 env 缺口（本任务红=0）**：`check-knowledge-refs`（150 条其它任务 `运行期临时目录` 悬空，0 条属本任务；隔离 worktree 缺其产物）+ `check-builtins-freshness`（`expected=present actual=absent`，隔离 worktree 无 builtins 产物）；L2 `check-inst-smoke` PASS 后停在 `install-host → build-builtins`（`ERROR: no configured compiler-rt build tree at 运行期 compiler-rt 构建树 -- configure it once (INFRA-079t) first`）⇒ BLOCKED；**不是** `check-arch-smoke` Node 基线（主仓该目标 10/10 + 25 svc PASS，QEMU-080t 已验证）。（收尾修正，finding 1/5。）`git diff` 仅 `components/gem5/**` + 两本册。
**新发现/坑**：① 服务号按 contract/spec 取 **rd16**（任务书 §4「immu18 低 8 位」与 §5.2/资产冲突；按 spec + 现有 harness 实现并在证据中验证）；② gem5 fetch 在 TLB 前把 PC 掩到 4 字节，IALIGN 必须用 `req->PC` 判；③ `BaseSemihosting` 原只在 ARM/RISC-V 构建注册，需在 generic SConscript 为 DADAO 启用；④ `Param.SimObject(NULL)` 不能传 Python `None`，用 gem5 `NULL`；⑤ 对照 shim 必须接受 `-machine`（驱动用 `-machine` 非 `-M`）；⑥ raw 装载不得覆盖 BootROM 复位 PC；⑦ `math_test` 暴露既有 B7 低位数值差异（238/76404，疑 fma），与 FS 无关；⑧ `运行期 LLVM 构建树` 在隔离 worktree 缺失时 `check-modules` 会触发全量 LLVM 重建（本任务按基线停在该目标前）。
**遗留问题**：① picolibc `math_test` BLOCKED = 既有 B7 数值差异（QEMU 0 error / gem5 238 error；建议另立 B7 差分任务，本任务未改 B7）；② L1 `check-knowledge-refs` 150 条其它任务悬空引用 = 隔离 worktree 无其 `运行期证据（已清理，未归档）`（基线，非本任务）；③ L2 `check-arch-smoke` 在隔离 worktree 停于 `install-host → build-builtins`（缺 `运行期 compiler-rt 构建树`，env 缺口；主仓同目标 10/10 PASS）——**非** Node 基线问题（收尾修正，finding 1）；④ 空目录 `m5out/` 已 `rmdir`，`check.py` 增 git 不可见的空目录检查（收尾修正，finding 5）。
**收尾结论**：reviewer 第 1 轮判决 **Accepted**（不另开轮）；findings 1–5 均文档/口径级，由 architect 收尾直接处置（见「第 1 轮 architect 收尾」）；状态 `待验收`→`已验证`。**picolibc `math_test` 仍记 blocked，未写 PASS。**

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 `fs_machine.*`/`fs_tlb.*`/`fs_mmu.hh`/`fs_workload.*`/`semihosting.*`/`fs.py`/`isa.*`/`inst.cc`/`faults.hh` 与 patch/series；findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书 §4 写「服务号 = immu18 低 8 位」，但 contract §2/spec §5.2 与现有 harness 用 `rd16` | ✅已修（按 spec/资产） | `inst.cc`/`semihosting` 取 `rd16`，tag 只判 `immu18[17:8]==0x3FF` | console/exit300/getcmdline 实测 + 完成区① |
| F2 gem5 fetch 先按 4 字节掩码，IALIGN 看 TLB vaddr 恒过 | ✅已修 | `fs_tlb.cc` 用 `req->hasPC()?req->getPC()` 判 `PC%4` | `fault-ialign` rc=0x8D；注入 ialign 未单列但 fixture 真红 |
| F3 raw 装载覆盖 BootROM 复位 PC（`entry` 被改写） | ✅已修 | `fs_workload.cc` 仅无 bootrom 时设 raw entry | reset fixture rc0；注入 reset-vector rc=137 |
| F4 `--semihost off` 传 Python `None` 触发 SimObject 转换错误 | ✅已修 | `fs.py` 用 gem5 `NULL` | `--semihost off` → ILLI 0x88 实测 |
| F5 system/getcmdline fixture 漏 raw `0x100` 前缀 | ✅已修 | `gen_fixtures.py` 统一 `finish(prefix=0x100)` | system deny/native rc0 + marker 断言 |
| F6 `--dump-semihost-services` 在 SimObject 构造前调用 | ✅已修 | `fs.py` 移到 `m5.instantiate()` 后 | 25 服务集合 == spec §5.3 |
| F7 `BaseSemihosting` 仅 ARM/RISC-V 注册/编译 | ✅已修 | `src/arch/generic/SConscript` 条件加 `USE_DADAO_ISA` | 构建 rc0 + 25 服务动态执行 |
| F8 `math_test` gem5 238/76404 errors（B7 低位数值） | ⏸延后 | 未改 B7（本任务未触碰 `exec/b7*`/`fp_soft*`） | QEMU 0 error vs gem5 238；完成区遗留① |
| F9 L1 `check-knowledge-refs` 150 悬空、L2 停 `build-builtins` | ✅已核（基线非本任务） | 无（隔离 worktree 缺其它任务 `运行期临时目录` / 缺 `compiler-rt-builtins` 树）；**收尾修正**：原写「L2 = arch-smoke Node 基线」「L1 仅 1 红」有误，改为 env 缺口 + L1 2 红 | L1 本任务红=0；L2 inst-smoke PASS、BLOCKED 于 `install-host`（finding 1/5） |
| F10 SE 隔离 | ✅已核 | FS 判定 = `dynamic_cast<FsWorkload*>`，无全局开关；`faults.hh` SE 分支逐字保留 panic | SE hello/42/300 全过；注入 `se-cleared-by-fs` 使 SE 红（rc=125），还原回绿 |

代码级复核：区间检查用 `addr-base < size` 且 `len <= size-off`（无溢出）；ROM 写仅 `Write`；首个 `MachineFault` 用 `faultRaised` 锁定并 `exitSimLoopNow`；semihosting 仅在 FS 且 tag 命中时短路，SE `trap cfx0,0` 原路径不变；`resetThread` 仅 FS 调用并拒绝 SE；`--max-ticks`/panic 等非 guest 退出固定 125。注入 10/10（`cp`+md5，未用 git 还原）。

#### 第 1 轮 reviewer 验收

**重跑（reviewer 亲跑，rc 为本人终端实测，不采信完成区）**
- `RUN_INJECT=0 运行期证据脚本（已清理，未归档）` → **rc=0**（`run.EXIT=0`）：**109 CHECK / 0 FAIL**，其中 meta+fixtures=**76**；inst smoke 90/90 双引擎；全量 **1003/1003**（`both_fail=0`、`qemu_only_fail=0`、双引擎 PASS 集逐条 diff 为空、4 条 `profiles:[node]` skip、5 deferred）；embench **38/38** 且 `--inject` 检出；picolibc qemu 18 pass / gem5 17 pass+**1 blocked** / `new_fail=0`；SE `0/42/44`；`check-patch-tree` rc=0（`6 component(s), 294 patches OK`）、`check-source-state` rc=0（`5b2bc85` = `c8222cc`+1、clean）、decode `264/388/28/2` failures 0、converge `264/264`+`1848/1848`+B1–B7 `2102/1160/4248/3696/1215/1362/2979` 全 `[FAIL]0`、L1 rc=2、L2 rc=2、隔离 2 项 rc=0。
- `./run-inject.sh` → **rc=0**（`inject.EXIT=0`）：10/10 注入红、10/10 `md5 same=True`、`REBUILD restore-green rc=0`、10/10 回绿。
- **独立注入 2 类**（不在 engineer 的 10 类内）：① `configs/dadao/fs.py` 把 SYS_SYSTEM 恒 `native` ⇒ `sys-system-deny-not-executed` **rc=1**（expected=absent actual=present），`cp`+md5 还原（`md5sum -c OK`）后回绿 69/69 rc=0；② `fs_workload.cc` 关 `ET_EXEC` 校验（`scons` rc=0）⇒ `neg-elf-etdyn-msg` **rc=1**（ET_DYN 被接受、跑到 exit 42），md5 还原 + 重建 rc=0、回绿 69/69 rc=0。
- 字面验收命令 `semantics_gate.py --vectors tests/inst --only-profile-cases`：gem5 shim **rc=0 44/44**、`qemu-system-dadao` **rc=0 44/44**；44 例由我从 yaml 独立派生，全部包含在 1003 PASS 集内。
- `math_test` 同 ELF 对照：QEMU **rc=0 / 0 errors**；gem5 **rc=1 / 238 errors**、`GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit`、`GEM5_EXIT_CODE=1` ⇒ 76404 项跑完、装载与退出路径正常，差异为 `pow` 等 libm 低位 ULP；补丁级 diff（vs `b3c1f12b`）仅涉 `fs_*`/`semihosting`/`isa`/`inst` FS 分支/`faults`/两处 SConscript，**未触碰 FP/B7** ⇒ 归因成立，且**记为 blocked 未写 PASS**。
- `run_embench_e2e.py --inject` 实测 **rc=0**（`INJECT: PASS`，见 finding 2）。
- 全量 L1 `make -k check` **rc=2，仅 2 红**：`check-knowledge-refs`（150 悬空、**0 条属本任务**）+ `check-builtins-freshness`（`build product ... expected=present actual=absent`）；L2 `check-inst-smoke: PASS` 后停在 `install-host → build-builtins` 同一 env 缺口 ⇒ **本任务红 0**。
- 快照对账：`git status --porcelain -uall` 与开工快照**逐行相同**；5 个声明文件 md5 前后相同；源树 `5b2bc85` clean；`run.EXIT=0`/`inject.EXIT=0`；完成区 8 行、状态 `待验收`。

**约束核验**：改动仅 `components/gem5/**` + 两本册（`git diff` + untracked 双查，无 QEMU/spec/tests/contracts/Makefile/tools 改动）；`series` 89 行 = 磁盘 89 patch 且 `sort -c` 通过；SE 文件无 `fs_`/`machinefault`、SE panic 分支逐字保留；25 服务集合 == spec §5.3（现场派生）；几何 9 项 == `machine-profiles.yaml` tiny；shim 未知参数 rc=2 实测；无 `*_tmp*/*.orig/*.rej`、仓库无 `m5out/` 内容。采信项：仅 `REPORT.md` 聚合数字不采信（见 finding 3），其余全部亲跑。

**findings（不阻断，architect 收尾处置）**
1. **L2 归因与现场不符**：完成区/遗留③/F9 写「arch-smoke 0/10 = Node 未实现基线」，实际停点是 `install-host → build-builtins: ERROR: no configured compiler-rt build tree at 运行期 compiler-rt 构建树`（隔离 worktree 缺该树）；主仓基线 `check-arch-smoke` **10/10 PASS + 25 svc PASS**、QEMU-080t 状态「已验证」。请改写完成区/审阅记录的现场与 `check.py` 硬编码标签。
2. **验收 8 字面口径与现场不符**：语料 `embench-iot/src/` 实为 **19** 个 benchmark（非 22；QEMU-079t 基线同为 38/38，`executed==discovered` 有断言）；`--inject` 工具契约是「检出⇒rc=0、未检出⇒rc=1」，任务书「必须返回 1」方向相反（实测 rc=0）。实质判据「判据可失败」已证 ⇒ 请更正任务书验收 8 措辞。
3. **REPORT.md 计数掺入旧分相日志**：`report.py` 合并 `运行期临时日志`，本轮单次全量 109 CHECK 被报成 213（smoke/embench/picolibc 各重复一次），`geometry keys:` 为空 ⇒ 报告器改为只读单次 run 或先清理旧日志。
4. **`math_test` 豁免需落地为任务**：`check.py` 的 `known_blocked={math_test}` 是唯一会把 gem5 `fail` 改判 `blocked` 的点（QEMU 分类器同输入判 `fail`）；归因已独立证实（见上），请按遗留①**另立 B7 数值差分任务**，落地前保留登记。
5. 仓库根残留**空目录 `m5out/`**（git 不可见，任务书要求「无 m5out/」）；L1 实有 2 红（完成区只写了 knowledge-refs 一项），同属 env 缺口 ⇒ 收尾 `rmdir m5out` 并补记。

**判决：Accepted** —— 上述 rc 全部为 reviewer 亲跑实测；验收实质项全绿、本任务红 0、无越界改动、无凑绿/弱化断言；findings 1–5 为文档/口径级，按 6.5 由 architect 收尾直接改，不另开一轮。

#### 第 1 轮 architect 收尾（findings 1–5 处置）

reviewer 判决 **Accepted**，不另开轮；findings 1–5 全为文档/口径级，由 architect 直接改（任务书 + 证据脚本）：

| finding | 处置 | 证据 |
|---|---|---|
| 1 L2 归因错 | 改写完成区/遗留③/F9 为「停于 `install-host → build-builtins`（隔离 worktree 缺 `运行期 compiler-rt 构建树`）」；`check.py` 的 L2 判据改为 `check-inst-smoke: PASS` + 该错误串，标签不再写 Node 基线 | 主仓 `make check-arch-smoke` 末「Results: 10/10 passed」+「RESULT: PASS」（含 25 服务；QEMU-080t 已验证）；隔离 worktree 的门控日志 L2 段显示 BLOCKED 于 build-builtins |
| 2 验收 8 口径 | 「22 benchmark」→**19**（现场 `ls -d embench 组件源树中的 src/*` = 19；38 = 19×2，工具 line 360 断言 `executed == discovered`）；`--inject` 契约改为「检出 ⇒ rc=0（`INJECT: PASS`）/ 未检出 ⇒ rc=1 / setup ⇒ rc=2」 | `run_embench_e2e.py` line 299/360/378–400；现场 19 目录 |
| 3 REPORT 计数 | `report.py` 改为**只读单次 run log**（删掉合并 `check-*.log` 旧分相日志），geometry keys 改由 `CHECK geometry-*` 派生并剔除 `dump`/`keys` 伪键；重生成 REPORT.md | 重生成后：**109 CHECK / 0 FAIL**、geometry 9 项、注入 10 行（原 213 消失） |
| 4 `math_test` 豁免 | 归因已由 reviewer 独立证实（同 ELF：QEMU 0 error / gem5 238 error；补丁不触 FP/B7）⇒ **保留 blocked 登记（未写 PASS）**；「另立 B7 数值差分任务」留在遗留①，**本次不建册**（新任务属批次外停止点，需主会话确认后立） | 完成区遗留①；REPORT `picolibc` 段 `gem5 pass=17 blocked=1 new_fail=0` |
| 5 残留 + L1 红数 | 仓库根空目录 `m5out/` 已 `rmdir`（rc=0，复核 `ls` 无该目录）；`check.py` 增「git 不可见的空目录 `m5out/`」residue 检查；完成区补记 L1 **2 红**（`check-knowledge-refs` 150 悬空 + `check-builtins-freshness` 缺产物），均 env 缺口、本任务红=0；L1 判决改为 `make -k check` 全跑 + 红目标 ⊆ 两项 env 缺口 | `check-gates3.log`：`L1-check … reds=['check-builtins-freshness','check-knowledge-refs'] rc=0`、`isolation-no-residue … rc=0` |

**提交前门控（architect 亲跑）**：`check.py --phases gates,isolation --no-build` ⇒ `SUMMARY: all checks passed`，12 条 CHECK 全 rc=0（`check-patch-tree`/`check-source-state`/`check-gem5-decode`/`check-converge`/四本册门控/两条 isolation）；L1 红目标 `['check-builtins-freshness','check-knowledge-refs']`（均 env 缺口、本任务悬空 0），L2 BLOCKED 于 build-builtins（env 缺口，如实记、不伪装 PASS）。日志（同一证据目录）：`运行期证据（已清理，未归档）`（提交前全绿）、`运行期证据（已清理，未归档）`（post-merge 首跑，红）、`运行期证据（已清理，未归档）`（修复后全绿，`GATES_EXIT=0`）。
**门控可达 FAIL 的现场证据（本次收尾真实发生）**：首次 post-merge 跑出 L1 rc=1 —— 本册 finding 1 行引用了主仓工作树里的 arch-smoke 日志路径（隔离 worktree 无该文件）⇒ `check-knowledge-refs` 悬空 151、`ours=True` 判红；改引用、并把门控日志复制到 `运行期证据（已清理，未归档）` 后重跑全绿。
**同步**：`git merge master` 实为**有冲突**——`master` 已从 `b3c1f12b` 前进到 `464028f9`（新增 `GEM5-016t` 立册），冲突文件仅 `.tao/knowledge/milestones.md`（新增 GEM5-016t 行 vs 本行改写）；解决 = 两行都保留，按 `check-milestones-fresh` A4「同一时间按编号升序」排为 GEM5-015t → GEM5-016t；merge commit `be430216`（无其它文件冲突）。
**同步后门控**：`check.py --phases gates,isolation --no-build` ⇒ **12/12 CHECK rc=0、`SUMMARY: all checks passed`、`GATES_EXIT=0`**（L1 红仅 2 项 env 缺口、本任务悬空 0；L2 BLOCKED 于 build-builtins）。日志 `运行期证据（已清理，未归档）`（含首跑红 `check-gates-merged.log`：A4 次序错 1 项，已修）。
**提交**：`GEM5-015t: FS Machine-v5-Tiny`（`a3809976`）—— 显式 staging 26 文件（21 补丁 + `series` + `README.md` + `changelog.md` + 本册 + `milestones.md`），`git diff --cached --name-only` 与完成区「修改文件」逐项对账**空差**（无漏提/多提/越界）；未 `push`、未合入 `master`（合并由主会话执行）。
