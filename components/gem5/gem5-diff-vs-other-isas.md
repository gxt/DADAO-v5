# gem5 实现与其它 ISA 的差异盘点（结论索引）

> **性质**：`m16-gem5-019 gem5 实现差异盘点` 的**结论汇总**（只读分析的产出），**不是实现判据**——判据在 `spec/` 与 `.tao/contracts/`。逐条原文（两侧 `文件:行号` + 影响组合 + 优先级）在本任务书「盘点结论」段（`.tao/tasks/gem5/m16-gem5-019-gem5实现差异盘点.md`）。
> **对照物**：其它 ISA 在 gem5 中的实现——主参照 `src/arch/riscv/**`，强参照 `arm/**`，补参照 `x86`/`mips`/`power`/`sparc`。
> **范围**：**2 个 CPU 类型 × 2 个机型 = 4 组**（`--cpu-type {atomic,timing}` × `--profile {tiny,vast}`）。
> **整改权**：由用户逐项决定；本页只做索引与分流。

### 口径与覆盖（现场派生）

- **对照源规模**（`find src/arch/<isa> -type f | wc -l`，harness 数同法现场统计）：dadao 91（含 9 个独立断言 harness `*_test.cc`，不进构建）、riscv 120、arm 339、x86 368、mips 74、power 73、sparc 94。
- **枚举口径 = 12 个机制族**：①异常/故障 ②中断 ③MMU/TLB/PTW ④解码与 StaticInst ⑤ISA 状态与 checkpoint ⑥SE 进程/系统调用 ⑦工作负载与装载 ⑧semihosting ⑨debug/GDB/m5ops ⑩统计 ⑪机型/多核/CPU 模型 ⑫配置脚本。每条差异都归到其中一族、无重复族；**⑧ 无差异**（两侧都复用 `BaseSemihosting`，DADAO 只加 `SYS_SYNCCACHE`），其余 11 族各有差异行。
- **量化对照**：故障类 3（dadao，全为真故障）↔ 14（riscv，含基类 `RiscvFault` 与 `Reset`）/ 28（arm）/ 29（x86）；`DPRINTF` 4 处（全在 semihosting）↔ 67 处 / 10 文件（riscv）；`serialize` 0 ↔ 42 处 / 13 文件（riscv，含 `unserialize`）；SE 系统调用 247 号（argmask 表）/ 81 handler ↔ riscv 359 行号表 + 共享 `syscall_emul`；CLI 选项 34（dadao 自有）↔ 上游 113（同名仅 5）。
- **差异 25 条（D01–D25）：P0 1 / P1 12 / P2 12。**

### 一、缺失实现（9 条）

- D01 [缺失⑨] `src/arch/dadao/semihosting.cc:85` ↔ `src/arch/riscv/tlb.cc:120` ｜ 全树仅 4 处 `DPRINTF`，`--debug-flags TLB/Faults/Exec` 全静默 ｜ 四组 ｜ P1
- D02 [缺失⑨] `src/arch/dadao/se_workload.hh:5`（明写「GDB … deliberately absent」）↔ `src/arch/riscv/bare_metal/fs_workload.hh:65`（`BaseRemoteGDB::build`）+ `src/arch/riscv/remote_gdb.cc:1-623` ｜ 四组 ｜ P2
- D03 [缺失⑨] `src/arch/dadao/decode/decode.hh:26`（batch 仅 1–7，无伪指令）↔ `src/arch/riscv/isa/formats/m5ops.isa:39`、`src/arch/riscv/isa/decoder.isa:6491` ｜ 四组 ｜ P2
- D04 [缺失⑤] `src/arch/dadao/isa.hh:25-167`（无 serialize）↔ `src/arch/riscv/isa.cc:986`、`src/arch/riscv/interrupts.cc:193`、`src/arch/riscv/tlb.cc:693` ｜ 四组 ｜ P1（**DADAO 特有状态（cfx/PTW/TLB 等 misc 侧）未序列化**：GPR+PC 由 `src/cpu/thread_context.cc:194-215` 存取，`BaseISA::serialize` 只写 `isaName`（`src/arch/generic/isa.hh:155`）、`SimObject::serialize` 空实现（`src/sim/sim_object.hh:315`）⇒ 保存/恢复既不报错也不警告，静默丢状态）
- D05 [缺失⑤] `src/arch/dadao/isa.cc:208-233`（misc 读写全 panic）↔ `src/arch/riscv/isa.cc:693-980`（status/satp/sip 副作用）｜ 四组 ｜ P1（cfx 状态只在平台层：`src/arch/dadao/node_cfx.cc:1-1138`、`src/arch/dadao/tiny_cfx.cc:1-499`）
- D06 [缺失⑪] `configs/dadao/se.py:323`/`:325`（只构造一个 CPU SimObject）、`:207-208`+`:262`（`num-threads` 只作上下文池）+ `configs/dadao/fs.py:113-200`（无该项）↔ `configs/common/Options.py:114`（`--num-cpus`）、`:347`（`--smt`）｜ 四组 ｜ P1
- D07 [缺失⑪] `src/arch/dadao/DadaoCPU.py:15` + `configs/dadao/se.py:44`（只有 atomic/timing 两类，且 Timing 类写在配置脚本里而非 arch 目录）↔ `src/arch/riscv/RiscvCPU.py:37-60`（atomic/noncaching/timing/o3/minor 均在 arch 目录）｜ 四组 ｜ P2
- D08 [缺失⑦] `src/arch/dadao/fs_workload.hh:35-118`（只 BootROM+SRAM/PA RAM，机型几何因此在 `configs/dadao/fs.py:70-101` 与 `DadaoFsTlb.py`/`DadaoNodeTlb.py` 的 Param 默认值两处重复）↔ `src/arch/riscv/linux/fs_workload.cc:52`（DTB 由配置单源给出）、`src/arch/riscv/bare_metal/fs_workload.cc`｜ tiny/vast ｜ P2
- D09 [缺失⑩] `src/arch/dadao/isa.hh:129`（2 个 Scalar）+ `src/arch/dadao/node_tlb.cc:36`（2 个 Scalar）↔ `src/arch/riscv/tlb.cc:732`（TlbStats）+ walker/PMP/ISA 计数 ｜ 四组 ｜ P1（全 arch 仅这 4 个计数器；`configs/dadao/se.py` 无 `--dump-stats`，stats 只靠 `src/python/m5/simulate.py:262` 的 atexit 落盘）

### 二、语义不符（6 条）

- D10 [语义①] `src/arch/dadao/fs_machine.cc:117-145`（`invoke()` 内 `tinyCfxRaise` :128 / `nodeSyncEnter` :138 两分支）↔ `src/arch/riscv/faults.cc:61-255`（delegation/status/epc/tval 统一入口）｜ 四组 ｜ P2
- D11 [语义③] `src/arch/dadao/node_tlb.cc:513`（`demapPage` 空）+ `src/arch/dadao/node_tlb.hh:48`（`flushAll` 空）↔ `src/arch/riscv/tlb.cc:187`（按 vaddr/asid 清表）；DADAO 真实失效通道在 `src/arch/dadao/node_cfx.cc:788` ｜ vast ｜ P2
- D12 [语义⑥] `src/arch/dadao/process.cc:142`（ET_DYN 直接 fatal）↔ `src/arch/riscv/process.cc:98-133`（32/64 位 `initState`）；解释器装载在上游走通用 `src/sim/process.cc:506`（`updateBias`），DADAO 也用它但入口只收 ET_EXEC｜ SE 两组 ｜ P2
- D13 [语义⑤] `src/arch/dadao/isa.cc:470-478`（`copyRegsFrom` 只搬 GPR+PC）↔ `src/arch/riscv/isa.cc:334-355`（含 `miscRegFile`）｜ 四组 ｜ P2
- D14 [语义⑤] `src/arch/dadao/inst.cc:68`（自建保留集）+ `src/arch/dadao/isa.hh:84-96` ↔ `src/arch/generic/isa.hh:134-147`（`handleLockedSnoop` 框架钩子，riscv 已覆写）｜ 四组 ｜ P1（一旦开 `--caches`，LR/SC 无 snoop 失效路径）
- D15 [语义②] `src/arch/dadao/interrupts.hh:27`（`checkInterrupts` 恒 false）+ `src/arch/dadao/inst.cc:712`（指令边界自投）↔ `src/arch/riscv/interrupts.hh:89` + `src/arch/riscv/faults.hh:110`（`InterruptFault`）｜ vast（tiny 无异步源）｜ P2

### 三、旁路/折衷（7 条）

- D16 [旁路③] `src/arch/dadao/inst.cc:307-343`（timing 下经 `system.physProxy` 直读直写；= `m16-gem5-006` 约束 1 / 其待裁定 1、`m16-gem5-015` 数据侧折衷，**已知设计、非新缺陷**）↔ `src/cpu/simple/timing.cc:453`（`initiateMemRead`）+ `src/cpu/simple/timing.cc:1061`（`completeAcc`，两段式）｜ timing 三组 ｜ **P0**
- D17 [旁路③] `src/arch/dadao/fs_tlb.cc:84`、`src/arch/dadao/node_tlb.cc:527`（inline `finish` ⇒ 走查 0 周期）↔ `src/arch/riscv/tlb.cc:622` + `src/arch/riscv/pagetable_walker.cc:1-1267`（异步事件）｜ timing×vast（tiny 无 walker，同一 inline 形态但无走查可计时）｜ P1
- D18 [旁路③] `src/arch/dadao/tlb.cc:44-96`（宿主页表直译，无 entry/LRU/ASID）↔ `src/arch/riscv/tlb.cc:116`（lookup）/`:153`（insert）/`:229`（flushAll）｜ SE 两组 ｜ P2
- D19 [旁路⑥] `src/arch/dadao/se_workload.cc:404`（247 号 argmask）、`:5704`（81 handler）↔ `src/arch/riscv/linux/se_workload.cc:95-107` + `SyscallDescTable`（`src/arch/riscv/linux/se_workload.cc:529`/`:896`，64/32 位表 359/331 行）｜ SE 两组 ｜ P1
- D20 [旁路④] `src/arch/dadao/isa/main.isa:24`（`return new DadaoInst(machInst)`）+ `src/arch/dadao/decode/decode.cc:1-131`（手写表驱动）↔ `src/arch/riscv/isa/main.isa:46-60` + `src/arch/riscv/isa/decoder.isa`（6493 行）+ `isa/formats/*`｜ 四组 ｜ P1
- D21 [旁路④] `src/arch/dadao/inst.cc:653-666`（只置 IsInteger/IsFloating/IsInvalid/IsNonSpeculative，opClass 恒 `IntAluOp`）↔ `src/cpu/static_inst.hh:145`（`IsLoad/IsStore/IsAtomic` 由 ISA parser 置位）｜ 四组 ｜ P1
- D22 [旁路③] `src/arch/dadao/fs_tlb.cc:1-110` vs `src/arch/dadao/node_tlb.cc:1-558`、`src/arch/dadao/tiny_cfx.cc:1-499` vs `src/arch/dadao/node_cfx.cc:1-1138`（**两套代码**）↔ `src/arch/arm/mmu.cc:65`（stage1/stage2 TLB 参数化复用）｜ tiny+vast ｜ P1

### 四、配置缺口（3 条）

- D23 [配置⑫] `configs/example/se.py:29`（本版上游脚本已废弃、直接 fatal；`configs/example/fs.py` 同）⇒ 真实参照是 `configs/deprecated/example/{se,fs}.py`(298/449 行)+`configs/common/Options.py`(113 选项)。DADAO 自有 34 项、同名仅 5（`--cpu-type/--env/--interp-dir/--kernel/--mem-size`）、缺 108 项；缺类计数：caches 6、checkpoint/simpoint/dist/work-item 33、`--param` 2、cpu/smt/bp 8、mem 4、gdb 1（`--wait-gdb`）、trace 3、`--stats-root` 1、FS 设备 20、SE in/out/chroot 7、余 23（`--num-cpus`/`--sys-clock`/`--sys-voltage`/`--mem-channels-intlv`/`--maxinsts`/`--maxtime`/`--bench`/`--list-*` 等；合计 108）｜ 四组 ｜ P1
- D24 [配置⑫] `configs/dadao/se.py:285`（SE semihosting 只在 timing 分支生效，且 `:186-205` 在 atomic 下显式拒绝 `--semihost`（入表 `:195`、`parser.error` `:204`））↔ `src/arch/riscv/semihosting.hh:55`（semihosting 对象与 CPU 型号无关，FS/SE 均可挂）｜ atomic×SE ｜ P2
- D25 [配置⑪] `configs/dadao/fs.py:113-200`（无 `--num-threads`，`system.multi_thread` 从不置位）↔ `configs/common/Options.py:114` ｜ FS 两组 ｜ P2

### 五、四组配置逐一说明

- **tiny × atomic**：CPU=`DadaoFsAtomicSimpleCPU`（`src/arch/dadao/DadaoFsCPU.py:7`）+`DadaoFsMMU/FsTLB`。**共用代码+参数**：与 tiny×timing 同一执行核、同一 TLB、同一 Workload，只换 CPU 模型与内存系统。访存：数据走 `xc->readMem/writeMem` 原子包过 `SystemXBar`→`SimpleMemory`（`configs/dadao/fs.py:360`），取指同路；无 cache。机型参数：64 KiB BootROM + 8 MiB SRAM + 64 KiB hmon、页 64 KiB（`src/arch/dadao/page_size.hh:18`），来自 `configs/dadao/fs.py:70-84` 且与 TLB Param 默认值重复（D08）。MMU：identity + ROM/SRAM/hmon 段检查（`src/arch/dadao/fs_tlb.cc:17-72`），**无 entry、无 PTW、`demapPage` 空**。差异：无 stage2/PMP/walker/serialize；故障直入 tiny cfx3 hmon（`src/arch/dadao/fs_machine.cc:113`），不经 gem5 异常框架。
- **tiny × timing**：CPU=`DadaoTimingSimpleCPU`（`configs/dadao/se.py:44`），`system.cpu.mmu = DadaoFsMMU`（`configs/dadao/fs.py:393`）⇒ **共用代码+参数**。访存：**取指**经 `NoncoherentXBar`+`SimpleMemory` 真实计时（`fs.py:355`）；**数据 functional**（`src/arch/dadao/inst.cc:307-343`），ld/st 周期全靠 `contracts/wuming-cycles.yaml`；PTW 本来就没有 walker，0 延迟无意义（D17 只在 vast 侧成立）。
- **vast × atomic**：CPU=`DadaoNodeAtomicSimpleCPU`（`src/arch/dadao/DadaoNodeCPU.py:7`）+`DadaoNodeMMU/NodeTLB`。**两套代码**（相对 tiny）：guest TLB 阵列与两级步进在 `NodeState` 内（`src/arch/dadao/node_tlb.cc:344-500`），命中/缺失/权限/A/D 回写全在此。机型参数：4 MiB BootROM + 2 GiB PA RAM + hmon/smon/pmem 各 64 KiB（`configs/dadao/fs.py:86-101`）、页 64 KiB + 512 MiB 超页（8 个 64 MiB 片段位，`src/arch/dadao/node_cfx.hh:87`）、guest TLB 2 组 × 8 路 + 超级页条目（`src/arch/dadao/node_cfx.hh:95-96`）。访存：取指与数据都过 `SystemXBar` 原子包。差异：无 PMP/PMA，权限是 cfx 两轴（`node_tlb.cc:364`）；TLB 失效走 `cfx_ptw_tlb_control`（`node_cfx.cc:788`），框架 `demapPage`/`flushAll` 空（D11）。
- **vast × timing**：同一个 `DadaoTimingSimpleCPU`，只把 `mmu` 换成 `DadaoNodeMMU`（`configs/dadao/fs.py:387-393`）⇒ **共用代码+参数**。访存：取指计时；数据 functional，但**仍过 `NodeTLB::translateFunctional`**（`src/arch/dadao/inst.cc:314`），段检查/PTW 异常/权限与 atomic 逐项一致，只有时间不进内存系统。关键风险：miss 走查在 `translateTiming` 里 inline（`node_tlb.cc:527`）⇒ **vast×timing 是唯一「有 PTW 语义、无 PTW 时序」的组合**（D17）。

### 六、结论与建议

- 影响**数字可信度**的只有 D16（P0）与 D17（P1）：timing 的 ld/st 与页表走查都不进内存系统，因此「gem5 timing 与 chipyard 的周期差」目前完全由 wuming 周期表承担。**D16 与 `m16-gem5-006` 约束 1（其待裁定 1）、`m16-gem5-015` 的数据侧折衷是同一件事 ⇒ 已知设计、非新缺陷**，仅作为差异最高级保留；D16/D17 若要开任务须用户裁定（不与本次盘点新增缺陷混谈）。其余 23 条是能力/可维护性缺口。
- 建议（未开任务书，待用户裁定优先级）：① 数据面两段式（D16+D17 同批）；② checkpoint（DADAO 特有状态序列化，D04）+ `--param`（D23，可扫 TLB/延迟参数）；③ tiny/vast 合并为参数化 TLB（D22，消除双份语义）。
- 本盘点未比对 chipyard RTL（属 `m16-chipyard-013` 的范围），未重建、未跑仿真。
