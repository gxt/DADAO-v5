# QEMU 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M1

- **2026-09-23 —**
  - 摘要：**M1 补丁集重整**：由「16 份编号补丁 + `git am`」改为「树形补丁集 + `git apply`」（本组件 8 → **31** 份 = 新增 25 + 修改 6）。应用后最终 tree hash = `4a14d56ce4ecfc6f5edd2f2d181ec6628844233b`（与重整前一致，语义未变）。决策见 `ADR-0002 D4`（rev. 2026-09-23）。

## M2

- **2026-09-29 `QEMU-025t`**
  - 摘要：**`trans_*` 命名同步到 0.5.4 id**（QEMU 侧函数名与 `contracts/opcodes.yaml` 的 id 对齐）。

- **2026-09-29 `QEMU-026t`**
  - 摘要：**QEMU 11.1.1 / GCC 15 构建修复**。

- **2026-09-29 `QEMU-027t`**
  - 摘要：**模块小修 / lint**（deferred 遗留项）。

- **2026-09-30 `QEMU-028t`**
  - 摘要：**`st.*` 源为 0 号寄存器被误判 ILLI 的修复**（0 号寄存器作源合法）。

- **2026-09-30 `QEMU-029t`**
  - 摘要：**`cpu.c.patch` 的 `rf0` 位布局注释同步**（`ADR-0012 D6`）。

- **2026-09-30 `QEMU-030t`**
  - 摘要：**RAS 压/弹栈重写**（`ADR-0012 D7`）+ MemRAS 台账关闭。

- **2026-10-02 `QEMU-031t`**
  - 摘要：**`ADR-0012 D8` 地址语义实现**：`cmp.uo-rb` 取 48 位地址；控制流 64 位地址写回 `rb0`。

- **2026-10-03 `QEMU-032t`**
  - 摘要：**`ret rd0` 运行期 ILLI**（`imms18` 非零时非法）。

- **2026-10-03 `QEMU-033t`**
  - 摘要：**`mreg_range_overlap` 运行期实现**（translate 期判定 ILLI）。

- **2026-10-03 `QEMU-034t`**
  - 摘要：**FP 执行层基础设施 + RF 数据搬运族（16 条）从 ILLI 桩换为真实 TCG**。新建 `target/dadao/insn_trans/trans_fp.c.inc`（60 条 `scope:fp` trans：16 真实 + 44 保留 ILLI 桩），并从 `trans_arith`（42 个）/`trans_compare`（2）/`trans_block`（2）/`trans_mem`（8）/`trans_cond_assign`（5）/`trans_imm`（1）删除对应 FP 桩；`translate.c` 新增 `RF0_WRITE_MASK`/`load_rf`/`store_rf`（rf0=FCSR，写掩码 `[33:32]+[4:0]`）并 include 新文件。实现家族：`rf_mem`（`ld.t/st.t/ld.o/st.o/ldm.t/stm.t/ldm.o/stm.o` 的 `-rf`）、`rf_move`（`rd2rf`/`rf2rd`）、`set.w-rf`、`cs.n/z/p/eq/ne-rf`；translate 期合法性 `dst_rf0`/`mreg_zero`/`mreg_range_overflow`。补丁 **31 → 32**（qemu），全仓 **68 → 69**；`check_qemu_trans` **227/227 (M1 152/152)** 不变。
  - 执行者：engineer

- **2026-10-03 `QEMU-035t`**
  - 摘要：**FP 位级语义族（10 条）从 ILLI 桩换为真实 TCG（纯位运算，无 softfloat）**：`sign` 4（`ftsgnj/ftsgnn/fosgnj/fosgnn`，`rfHD=rf0`→`abs`/`-abs`、`rfHC==rfHD`→`copy`/`negate` 自然成立；`ft` 用 bit31、`fo` 用 bit63，按完整 64 位注入并保持非符号位）、`classify` 2（`ftcls`/`focls`，10 类位 `[9:0]`、`[63:10]` 清零，orri 块形式 `immu6` 1–63 先读后写）、`compare` 4（`ftqcmp/ftscmp/foqcmp/foscmp`，结果 `1/0/-1` 写 rd；unordered 静默返回 qNaN / 信令返回 sNaN，符号位 0）。合法性：sign `dst_rf0`、classify `mreg_zero`/`mreg_range_overflow`（源/目的双侧）。仅改 `trans_fp.c.inc`；补丁**无新增**（仍 32/69）。`check_qemu_trans` **227/227 (M1 152/152)** 不变。
  - 执行者：engineer

- **2026-10-03 `QEMU-036t`**
  - 摘要：**FP 转换族（20 条）从 ILLI 桩换为真实 TCG，首次接入上游 softfloat**：`convert_ff` 4（`ft2ft`/`fo2fo` 全 64 位寄存器搬移；`ft2fo`/`fo2ft` 经 `float32_to_float64`/`float64_to_float32`，含溢出→±Inf+OF、下溢→UF、NaN payload 传播、sNaN⇒NV+qNaN）、`convert_f2i` 8（`floatXX_to_intYY_round_to_zero`，向零截断、NaN/Inf/超范围饱和最大/最小+NV；spec 未明 NX，按裁定不置）、`convert_i2f` 8（`intXX_to_floatYY`/`uintXX_to_floatYY`，rf0 舍入、inexact 置 NX）。`helper.c`/`helper.h` 新增 `fp_cvt_ff`/`fp_cvt_f2i`/`fp_cvt_i2f` 三个 helper：局部 `float_status`（**不新增 cpu.h 字段**）、`rf0[33:32]`→softfloat 舍入模式映射、softfloat 标志 `&0x1F` 合并入 `rf0[4:0]`；`trans_fp.c.inc` 新增 `convert_ff` 的 `mreg_range_overlap` 检查与三族通用块处理。补丁**无新增**（仍 32/69）。`check_qemu_trans` **227/227 (M1 152/152)** 不变。
  - 执行者：engineer

- **2026-10-03 `QEMU-037t`**
  - 摘要：**FP softfloat 算术族 + root（14 条）从 ILLI 桩换为真实 TCG，`scope:fp` 60 条全部落地**：`arith` 12（`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb` + `foadd/fosub/fomul/fodiv/forem/fosclb`）经 `float32_*`/`float64_*`（`div`/`rem`/`scalbn`），`root` 2（`ftroot`/`foroot` = `rootn(x,2)` == `sqrt`，`immu6 != 2` ⇒ ILLI）。`helper.c` 新增统一 `helper_fp_arith`（kind 0..5 ft / 6..11 fo；`scalb` 的 n 取 `floatXX_to_int32(rfHD)`）与 `helper_fp_root`；`fp_status_init` 补 `set_float_default_nan_pattern(0b01000000)`（memset 后 0 会让 `parts64_default_nan` 断言失败/产生畸形 NaN）。`trans_fp.c.inc` 新增 `gen_fp_arith`/`gen_fp_root`（先读全源再写目的；`dst_rf0` ⇒ ILLI）。补丁**无新增**（仍 32/69）。`check_qemu_trans` **227/227 (M1 152/152)** 不变。
  - 执行者：engineer

- **2026-10-04 `QEMU-038t`**
  - 摘要：**FP `dst_rd0` 运行期 ILLI 落地（15 条 rd-目的）**：新增 `fp_check_dst_rd0(ctx, rdstart)`（`rdstart == 0 ⇒ gen_exception_illegal`），并在 **8 个调用点**覆盖 15 条 rd-目的指令——`gen_convert_f2i`（8 条 convert_f2i 共用）、`trans_ftcls_orri_rf`/`trans_focls_orri_rf`（classify 2）、4 个 `trans_{ftqcmp,ftscmp,foqcmp,foscmp}_orrr_rf` 包装（compare 4；`gen_fp_cmp` 签名不变）、`trans_rf2rd_orri_rf`（rf_move 1）；目的字段统一 `a->hb`，检查置于各族既有 `fp_check_mreg` 之前（`dst_rd0` 优先，无相互抵消）。依据 `contracts/legality_rules.yaml` `dst_rd0`(active) + `contracts/fp_semantics.yaml` 15 条 `legality_refs`（Spec-first）。**只改既有补丁，不新增**（qemu 32、全仓 69）；`check_qemu_trans` **227/227 (M1 152/152)** 不变；新建探针 `tools/qemu/min_rom_probe_038t.py`（42/42）。
  - 执行者：engineer

## M3

- **2026-10-05 `QEMU-040t`**
  - 摘要：**新增指令 `sub.o_orrr_dbb`（RB − RB → RD）的 decode + trans**：`insn.decode` 在 `@misc` 子表新增 pattern `sub_o_orrr_dbb 01000000110011..................`（14 位 = op `0x40` + ha `0x33`；value `0x40CC0000`/mask `0xFFFC0000`）；`trans_arith.c.inc` 新增 `trans_sub_o_orrr_dbb`（`a->hb == 0` ⇒ 运行期 ILLI，否则 `load_rb(a->hc) − load_rb(a->hd)` 全 64 位补码 → `store_rd(a->hb)`）。依据 `ADR-0012 D9.1`（`scope:m3`）；与 `SPEC-100t` 同集原子落地。**补丁无新增**（qemu 32、全仓 69）。`check_qemu_trans` **228/228 (M1 152/152)**；`check-interface` 228；探针 `tools/qemu/min_rom_probe_040t.py` 6/6。
  - 执行者：engineer

## M4

- **2026-10-06 `QEMU-042t`**
  - 摘要：**QEMU ELF 加载器（`Ehdr`/`Phdr`/装载/`e_entry`；raw-bin 兼容；加载期 over-size 守卫；M4）**。`hw/dadao/dadao-machine.c`：按 kernel 前 4 字节 magic 判别路径 A/B；路径 A 解析**大端** `Elf64_Ehdr`/`Elf64_Phdr`、校验 `EI_CLASS=2`/`EI_DATA=2`/`e_type=ET_EXEC`/`e_machine=0x0DA0`/`e_flags[7:0]=1`，按 **VA=PA** 装载 `PT_LOAD`（`.bss` 零填充；**按 `p_offset` 通用处理、不假设 0**），装载后 **`cpu_set_pc(e_entry)`**；路径 B raw-bin 双镜像**保留** + 新增装载期尺寸守卫（ROM>64 KiB / RAM>16 MiB 报错含实际尺寸与上限）。**未动** `target/dadao/**`（guest 语义）。**验证**：探针 `tools/qemu/min_rom_probe_042t.py` 22/22；`make check`/`check-qemu-semantics`(149/149)/`check-patch-tree`(89)/`test-codegen`(15/15) EXIT=0；证据 4/4 注入 + reviewer 独立注入（`cpu_set_pc(e_entry)→RAM 基址`）→FAIL→还原+重建→回绿。**遗留**：`EI_OSABI` 未校验、`PT_LOAD` 重叠未显式拒绝（非阻塞）。
  - 执行者：engineer + reviewer

## M5

- **2026-10-08 `QEMU-044t`**
  - 摘要：**SEE/HEE 运行模式 + cfx 寄存器文件/掩码/权限 + `DADAO-12 §5` 异常进入/退出流程**。`cpu.h`：新增 `inner_run_mode`/`inner_cfx_code`/`inner_cfx_mask`、`cfx_global_version[4]`/`global_cfx_mask[4]`（cg0-3 rc0/rc1，全局共享）、`DADAOCfxRegs cfx[5]`（实现范围 `cfx0/1/2/3/63`，cg0-cg7）。`cpu.c`：复位值依 `DADAO-12 §3`+`DADAO-13 §1`（hypv：mask 全0、`switch_run_mode=3`、`excp_vector=cfxha<<42\|0x3ff_ffff_0000`；user/jail/supv：mask 全1、`switch_run_mode=2`、`excp_vector=0`；`cfx_id`/`version`/`scratch_regs_num`/`cause_nonmaskable`）；`dump_state` 打印 cfx/mode 状态供 `-d cpu` 观测。`helper.c`/`helper.h`：`helper_cfx_trap`/`cfx_escape`/`cfx2rd`/`cfx2rc` 实现 `§5` 步骤 1–10（reserved⇒ILLI 重定向当前 monitor、指令类型 mask⇒ILLI、未实现 cfx⇒CFXREG、`inner/global/cause` mask、计数、现场保存、`switch_run_mode`/`switch_cfx_mask`、`cause_ip/id/info`、跳向量）与 cfx 寄存器读写（cg/rc 有效性、RO 写⇒CFXREG、rc≥N⇒CFXREG、cg3 仅 hypv）。`trans_ctrl.c.inc`：`trap`/`escape`/`cfx2rd`/`cfx2rc` 由 ILLI 桩改为路由到流程（`cfxld`/`cfxst` 保持 ILLI，`scope:excluded`）。探针 `tools/qemu/min_rom_probe_044t.py`（13 用例）。补丁**无新增**（qemu 32）。**边界**：本任务提供流程机制并接线 `trap`/`escape`/`cfx2rd`/`cfx2rc`（验收 2–7 需要可观测触发路径）；`QEMU-045t` 在其上补 refine+专探针。
  - 执行者：engineer

- **2026-10-08 `QEMU-049t`**
  - 摘要：**RAM@0 双映射（C1 step1）+ 越界访问/取指异常语义（`ADR-0004 R3` / `ADR-0020 D15`）**。`cpu.h`：新增 `DADAO_RAM0_BASE=0x0000_0000_0000`/`DADAO_RAM0_SIZE=16 MiB`、`DADAO_EXIT_CFXMEM=0x81`、`DADAO_EXCP_CFXMEM` 内部异常、cfxha 宏（`DADAO_CFXHA_SHIFT=42`/`MASK=0x3F`/`UMON=0`/`DADAO_ADDR_CFXHA`）。`hw/dadao/dadao-machine.c`：新增 RAM@0 `memory_region_init_ram("dadao-ram0")` + `add_subregion(system_memory, DADAO_RAM0_BASE, ram0)`，**旧 RAM 段（`0xffff_0000_0000`，16 MiB）保留**（两段并存、互不重叠）。`helper.c`：`dadao_excp_to_exit_code` 增 `CFXMEM→0x81`；`dadao_cpu_tlb_fill` 增 RAM@0 映射分支，并把越界故障按 cfxha 分类——**umon 段（`addr[47:42]==0`）越界访问/取指 ⇒ `CFXMEM`（0x81）**，其余（含旧 power 段 63）**保留测试机约定 `unmapped`（0x87）**；取指路径与数据路径同等对待（经 `get_page_addr_code`/`MMU_INST_FETCH` 到同一 `tlb_fill`）。探针 `tools/qemu/min_rom_probe_049t.py`（9 用例：RAM@0 读写/执行、旧 RAM 读写、同偏移互不干扰、cfxha0 越界数据/取指⇒0x81、cfxha63 越界数据/取指⇒0x87）。`check-interface` 增 RAM@0（基址/大小/`hw/dadao` 注册点）与 `CFXMEM=0x81`/`CFXHA_UMON=0` 断言，**旧 RAM 断言保留**。补丁**无新增**（qemu 32）。**step2**（旧向量/harness 迁 `0` + 删旧 RAM 段 + 收紧断言）另立、M5 之外。
  - 执行者：engineer

- **2026-10-08 `QEMU-046t`**
  - 摘要：**semihosting（译码层短路 + 共享层复用 + 完整 25 服务 + `SYS_EXIT`）**。`target/dadao/common-semi-target.c`（**新增**）：共享层 `do_common_semihosting` 的 v5 钩子——`common_semi_arg(cs,0)=rd16`（号）、`(cs,1)=rb16`（参数块指针）、`common_semi_set_ret=rd31`、`is_64bit_semihosting` 恒真、`common_semi_stack_bottom=rb1`（`rbsp`）、`common_semi_has_synccache` 真（`ADR-0020 D2/D14`；共享层**不重写**）。`insn_trans/trans_ctrl.c.inc`：`trap cfx*, immu18` 当 `immu18[17:16]==2'b11` 时**译码层短路**，抛内部 `DADAO_EXCP_SEMIHOST`（与 `RISCV_EXCP_SEMIHOST` 同构），不进入 cfx 向量。`cpu.h`：新增 `DADAO_EXCP_SEMIHOST`。`helper.c`：`dadao_cpu_do_interrupt` 短路处理——`do_common_semihosting(cs)` + `env->pc += 4`（写回 `rb0`），返回 `rd31`；`helper_cfx_trap` 的 tag 分支改为**防御性显式失败**（译码层已短路）。`cpu.c`：新增 `dadao_cpu_translate_for_debug`（无 MMU，VA=PA，仅暴露已映射区）接入 `SysemuCPUOps`——共享层经 `cpu_memory_rw_debug` 读写 guest 内存必需，否则空指针崩溃。`Kconfig`：`select ARM_COMPATIBLE_SEMIHOSTING if TCG`；`meson.build`：条件编译 `common-semi-target.c`；`qemu-options.hx`：`-semihosting`/`-semihosting-config` 的 arch mask 增 `QEMU_ARCH_DADAO`（默认 `auto`，harness 侧 `native` 显式开，`ADR-0020 D7`）。探针 `tools/qemu/min_rom_probe_046t.py`（**新增，随产物入库**）：32 用例覆盖判定两条路、钩子 bank（`n=0→rd16`/`n=1→rb16`/返回 `rd31`）、**25 服务各 ≥1 例**、`SYS_EXIT`/`EXIT_EXTENDED` 码传播到 host `$?`、`SYSTEM`/D2 文件档、64 位大端参数块。补丁 **32 → 34**（+`qemu-options.hx.patch`+`common-semi-target.c.patch`）。`exit port` 机制**保留**（迁移归 `TESTCASES-034t`）。
  - 执行者：engineer

## M6

- **2026-10-09 `QEMU-052t`**
  - 摘要：**ELF 直载改走上游 loader（钉子②）：删自建白名单 + 调用方薄校验 + 仅允许 RAM 落段（用户裁定 D）**。`hw/dadao/dadao-machine.c`：删自建 ELF loader（`dadao_load_elf`/`DadaoLoadRegion`/`dadao_load_regions[]`/`dadao_elf_rd*`/`dadao_region_contains`/`dadao_fill_zero`）；path A 改调上游 `load_elf(...)`（多段 `PT_LOAD`/`.bss` 零填充/`e_entry` 其提供），**调前自校验**——`dadao_elf_check_header`（`e_type==ET_EXEC` + `e_flags` 版本 1/保留位 0）与 `dadao_elf_check_segments`（逐 `PT_LOAD`：`p_filesz<=p_memsz`、`p_vaddr==p_paddr`、区间 `[p_vaddr,p_vaddr+p_memsz)` 在该窗内、无算术溢出）。**用户裁定 D（2026-10-09）：`-kernel` ELF 是 RAM 镜像，只允许落 RAM** ⇒ `dadao_mapped_regions[]` 由 `RAM ∪ ROM` 收窄为**仅 RAM**（`0xffff_0000_0000`+16 MiB），落 boot ROM 窗口（`0xffff_ffff_0000`/64 KiB）的 `PT_LOAD` ⇒ 加载阶段报错并 `exit(1)`（工具/加载错误层，与 guest fault 分层）。**不恢复白名单**（装载仍由上游做）；内存图与 raw-bin path B 未改。合约 `contract-elf §6.1.2`：装载语义改为**仅 RAM**、落 ROM 窗口 ⇒ 加载期错误并非零退出（并追加「只约束非零退出+分层、不约束文案」；§6.1.2/§6.2 两处 over-size 文案同步删 ROM）。探针 `tools/qemu/min_rom_probe_042t.py`：`elf_fill_rom_exact` 由「可运行」改为「**被拒**」（非零退出）；`neg_seg_out_of_range` 为**真越界**；`elf_fill_ram_exact` 保持恰好填满 RAM 可运行。**验证**：042t 探针 **21/21 PASS**（5 负例全 `exit=1`；`elf_fill_rom_exact` 被拒、`elf_fill_ram_exact` 仍 exit=0）；`.work/evidence/QEMU-052t/run.sh` **RUN_EXIT=0**（注入：允许集合加回 ROM + 禁用两处校验 callsite ⇒ `elf_fill_rom_exact`/`neg_bad_type`/`oversize_elf_seg` 不再被拒 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；注入时 ROM ELF 运行 exit=0 ⇒ 上游 ROM 装载路径仍可用，B′ 回归已消除）；`test-elf` EXIT=0（5/5）、`check-qemu-semantics` EXIT=0（149/149）、`check-patch-tree` EXIT=0（92 patches）、`make check` EXIT=0。补丁**无新增**（qemu 34）。
  - 执行者：engineer

- **2026-10-09 `QEMU-053t`**
  - 摘要：**RAM@0 收口（C1 step2）+ 删 exit port（`ISS-165`/`ISS-169`）**。`cpu.h`：删 `DADAO_RAM0_*` 与 `DADAO_EXIT_PORT_*`，`DADAO_RAM_BASE` 改 `0x0000_0000_0000`（**RAM@0 为唯一 RAM 段**）。`hw/dadao/dadao-machine.c`：删 RAM@0 与旧 RAM 双映射 → **单一 RAM@0**；**删整个 exit-port MMIO 设备**（struct/ops/init/type 注册）。`helper.c`：`dadao_cpu_tlb_fill` 删旧 RAM 与 exit-port 分支，单 RAM@0 映射；越界分类不变（umon 段 ⇒ `0x81`，其余含 power 段 ⇒ `0x87`）。`cpu.c`：`translate_for_debug` 单 RAM@0。`translate.c`/`trans_mem.c.inc`：删 `gen_check_exit_port_illi`（exit port 已无）。**测试侧迁 `0`**：`build_test_binary.py`(`BINARY_BASE=0`/`EXIT_BLOCK`/`DUMP_BASE`)、`codegen_crt0.s`、`gen_trampoline.py`(+`trampoline.bin`)、`dadao.lds`、`bootrom.S`/`bootrom_app.S`、`tests/e2e/*.s`、`tests/llvm/codegen/m5/*`、`tests/vectors/isa/{ctrl-*,mem-*}.yaml`、`tools/testcases/{validate_vectors,009t-audit,generate_*}`、`tools/integ/run_m5_e2e.py`、各 `tools/qemu/min_rom_probe_*`（SEMI_BLOCK/栈/数据地址迁 `0`；`049t` 旧 RAM 用例改为断言 **UNMAPPED**）。`check-interface` **收紧**：断言 `RAM_BASE=0`/`RAM_SIZE`、**新增**「旧 RAM 段已删」「exit-port 设备已删」负断言，删旧 RAM/exit-port 断言。`spec/Machine-01 §1/§5.5/§7` 同步（RAM@0 唯一 + exit-port 已删）+ `sha256` 锁同步。补丁**无新增**（qemu 34）。**验证**：`make check`/`check-interface`(83)/`check-qemu-semantics`(149/149)/`check-patch-tree`(105) EXIT=0；`test-codegen`(19/19)/`test-elf`(5/5)/`test-semihost` PASS。
  - 执行者：engineer

- **2026-10-09 `QEMU-055t`**
  - 摘要：**半托管/SEE 服务返回寄存器 `rd31 → rd8`（用户裁定「统一为 rd8」；不立 ADR）——实现侧**。`target/dadao/common-semi-target.c`：`DADAO_SEMI_RET_REG` `31 → 8`（`common_semi_set_ret()` 写 `rd8`），头注释同步返回寄存器措辞（引 `Machine-01 §5.2/§5.4`、`contract-semihosting §2/§4`）；**入参映射 `DADAO_SEMI_NUM_REG`(`rd16`)/`DADAO_SEMI_ARG_REG`(`rb16`)/`DADAO_SEMI_SP_REG`(`rb1`) 逐条未变**，`rd31` 仍为通用暂存（**不涉**函数返回域 `rd8/K=8`，属 `LLVM-062t`）。`tools/qemu/min_rom_probe_046t.py`：服务返回期望值**全部重派生为 `rd8`**（`ret_rd31` → `ret_rd8`：断言 `rd8` 得 `TICKFREQ=1e9` 且 `rd31` 哨兵 `0x5A5A` 不被改）。**逐条分类**：`034t/035t/036t/037t/038t`（`load_rf` 用 `rd31` 作暂存）+ `045t`（`rd31` 作 cfx 寄存器观测）**均为非服务返回 ⇒ 不改**；仅 `046t` 改。**域 B 收口**（用户裁定 2026-10-09「域B 并入 QEMU-055t」）：`tests/llvm/codegen/m5/m5_semi_write.s` 的服务返回读 `rd31 → rd8`（`SYS_OPEN` 句柄 + `SYS_WRITE` 未写计数），`tests/llvm/codegen/m5/expected.yaml` 约定行 + derivation 同步（引 `contract-semihosting §2/§4`、`Machine-01 §5.2`）。**验证**：`min_rom_probe_046t.py` PASS（rc=0）；6 个未改探针 rc=0 无回归；`make check`/`check-qemu-semantics`/`check-patch-tree` EXIT=0；**`test-semihost` EXIT=0**（`run_m5_e2e` 全绿）；证据 `.work/evidence/QEMU-055t/run.sh` `RUN_EXIT=0`（注入① `RET_REG 8→31`；注入② `m5_semi_write.s` 返回读 `rd8→rd31` ⇒ `test-semihost`/断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。补丁**无新增**（qemu 34）。
  - 执行者：engineer

## M7

- **2026-10-11 `QEMU-056t`**
  - 摘要：**RAM 基址由全 0 改为 `0xFC00_0000_0000`（cfxha 63 段；用户裁定 `INTEG-033k #10`）**。`cpu.h`：`DADAO_RAM_BASE` 由 `0x000000000000ULL` 改为 `0xFC0000000000ULL`（**唯一 RAM 段**，cfxha 63 / `power`；容量 16 MiB 不变）；`helper.c`/`dadao-machine.c` 以宏为真源的引用随之生效，注释同步（umon 段现无 RAM ⇒ 越界即 CFXMEM）。**测试侧随改**：`tests/scripts/{dadao.lds(RAM ORIGIN),codegen_crt0.s,bootrom.S,bootrom_app.S,gen_trampoline.py(+trampoline.bin),build_test_binary.py(BINARY_BASE/EXIT_BLOCK/DUMP_BASE),run_qemu_test.py(FAULT_NAMES 增 CFXMEM)}`、`tests/e2e/smoke_*.s`、`tests/llvm/codegen/m5/*.s`、`tests/vectors/isa/{ctrl-*,mem-*}.yaml`（生成器 base 常量更新后**重派生**：地址迁新基址；addr=0 越界用例按不变路由改判 **CFXMEM 0x81**）、`tools/testcases/{validate_vectors(RAM_BASE/END/RB0_PC/ALLOWED_FAULTS+CFXMEM),009t-audit,generate_*}`、各 `tools/qemu/min_rom_probe_*`（SEMI_BLOCK/栈/数据/MRPTR 地址；`046t` svc_heapinfo 输出指针改为 RAM 内）、`tools/integ/{run_m5_e2e.py,check_interface_alignment.py：RAM_BASE 断言改为从 `dadao.lds` ORIGIN 派生并与 QEMU 宏交叉核对（不写死）}`。`spec/Machine-01 §1` 地址图改 `0xFC00_0000_0000` + 册头 `0.2.1→0.3.0` + changelog + `sha256` 锁同步（用户授权 #10）。`components/qemu/README.md` 补丁规模刷新（31→**34** = 新增 27 + 修改 7）。补丁**无新增**（qemu 34）。**验证**：`make check`/`check-modules`(L2)/`check-interface`(83)/`check-qemu-semantics`(149/149)/`check-patch-tree`(110) EXIT=0；`test-codegen`(15/15)/`test-elf`(5/5)/`test-semihost`(m5 10/10 + 046t 25 服务) PASS。
  - 执行者：engineer

- **2026-10-12 `QEMU-058t`**
  - 摘要：**NaN 2-NaN 传播规则按宿主实测设为 `float_2nan_prop_ab`（`ISS-195` 收口）**。`target/dadao/helper.c`：`fp_status_init()` 在 `memset`+舍入+tininess+`set_float_default_nan_pattern(0b01000000)` 之后新增 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`（`float_status` **唯一**初始化点 ⇒ 覆盖 `cvt_ff`/`cvt_f2i`/`cvt_i2f`/`arith`/`root` 全族）；此前未设 ⇒ 默认 `float_2nan_prop_none` ⇒ 任一 NaN 操作数进入 add/sub/mul/div/rem 触发 softfloat 断言（`fpu/softfloat-parts.c.inc` `parts64_pick_nan` `g_assert_not_reached`）而中止模拟器。依据 = **宿主（x86_64 标量 SSE，`addss/subss/mulss/divss`）实测**：`(qNaN_a,sNaN_b)` 返回**第一操作数 a** 的 NaN（sNaN 则 quiet）⇒ 等价 `ab`、**排除** IEEE 754-2019 §6.2.3 推荐的 `s_ab`（用户 2026-10-12 裁定「参照宿主机实现」）。**验证**：`make check-picolibc-tests-full`（total 235）**pass 205 → 213 / fail 0 / excluded 22 / blocked 8 → 0**（解锁 8、`newly_blocked=∅`）；门控 `make check`/`check-patch-tree`(4 comp/127)/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests`(fast) EXIT=0；证据 `.work/evidence/QEMU-058t/run.sh`（默认 22 检查 rc=0；`--inject` 回退规则 ⇒ `test-remquo-quo` blocked/`signal 6` 可达 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。补丁**无新增**（qemu 34）。
  - 执行者：engineer

## M8

- **2026-10-15 `SPEC-142t`**
  - 摘要：**新增指令 `rev.o/rev.t/rev.w/rev.b`（逐块反转）的 decode + trans（QEMU 侧，`ADR-0012 D10`）**。`insn.decode`：`@misc` 子表新增 4 条 pattern（`rev_o/rev_t/rev_w/rev_b_orri_rd` = `01000000/01/10/11` + `001100`，即 op `0x40/0x41/0x42/0x43` + ha `0x0C`；value `0x40300000`/`0x41300000`/`0x42300000`/`0x43300000`，mask `0xFFFC0000`），头部计数 227→231。新建 `target/dadao/insn_trans/trans_rev.c.inc`：4 条 `trans_rev_{o,t,w,b}_orri_rd` + `gen_rev_units`（编译期展开的单元序反转：S∈{64,32,16,8} 块 × 块内 `S/k` 个 `k` 位单元倒序、单元内位序不变）与 `rev_legal`（`rdhb==rd0` ⇒ `ILLI`/`dst_rd0`；`k` 非 one-hot 或 `k>=S` ⇒ `ILLI`/`encode_onehot`；`immu6` 为立即数 ⇒ 翻译期静态判定，照既有 `trans_*_orri_rd` 惯例 `gen_exception_illegal`）。`translate.c` 增 `#include "insn_trans/trans_rev.c.inc"`（485→486 行）。依据 `ADR-0012 D10` + `contracts/opcodes.yaml` + `contracts/legality_rules.yaml`（`encode_onehot`）。补丁 **34 → 35**（qemu = 新增 28 + 修改 7）；`check_qemu_trans` **231/231 (M1 155/155)**、`check-interface` 83/83、`check-patch-tree`(128)/`check-index-blobs` EXIT=0。
  - 执行者：engineer

- **2026-10-15 `SPEC-143t`**
  - 摘要：**新增指令 `ctlz`/`cttz`/`ctpop`（前导零 / 末尾零 / 置位数）的 decode + trans（QEMU 侧，`ADR-0012 D11`）**。`insn.decode`：`@misc` 子表新增 3 条 pattern（`ctpop/ctlz/cttz_orri_rd` = `01000000` + `011101/011110/011111`，即 op `0x40` + ha `0x1D/0x1E/0x1F`；value `0x40740000`/`0x40780000`/`0x407C0000`，mask `0xFFFC0000`），头部计数 231→234。新建 `target/dadao/insn_trans/trans_bitcnt.c.inc`：3 条 `trans_{ctpop,ctlz,cttz}_orri_rd` + `bitcnt_mask`（有效位掩码，`>> (63-hd)` 避开 `1ULL<<64` 的 UB）与 `bitcnt_legal`（`rdhb==rd0` ⇒ `ILLI`/`dst_rd0`，照既有 `orri` 先例 `gen_exception_illegal`）。语义（`hd` = **有效位上界**，`rdHC[hd:0]` 共 `hd+1` 位）：`ctlz` = 左移 `63-hd` 后 `tcg_gen_clzi_i64(..., hd+1)`、`cttz` = 掩码后 `tcg_gen_ctzi_i64(..., hd+1)`、`ctpop` = 掩码后 `tcg_gen_ctpop_i64` ⇒ 全 0 时 `ctlz`/`cttz` 得定值 `hd+1`（`hd=63` ⇒ 64）、`ctpop` = 0；结果写满 64 位。**`hd ∈ 0..63` 全部合法**（无 `hd` 相关 ILLI 分支）。`translate.c` 增 `#include "insn_trans/trans_bitcnt.c.inc"`（486→487 行）。依据 `ADR-0012 D11` + `contracts/opcodes.yaml` + `contracts/legality_rules.yaml`（`dst_rd0`）。补丁 **35 → 36**（qemu = 新增 29 + 修改 7）；`check_qemu_trans` **234/234 (M1 155/155)**、`check-interface` 83/83、`check-patch-tree`(129)/`check-index-blobs` EXIT=0。
  - 执行者：engineer

- **2026-10-15 `INFRA-082t`**
  - 摘要：**在 `dadao-m1` 上新增 `umon` syscall 服务（识别条件含 user 模式）**：`write`/`writev`/`exit`/`exit_group`/`set_tid_address` 五服务（未实现者 ⇒ `-ENOSYS`）；`helper.c.patch` 于 `helper_cfx_trap` 内接管 user `trap cfx0,0`；`check-qemu-semantics` **149/149** 不回归。
  - 执行者：engineer

- **2026-10-15 `QEMU-060t`**
  - 摘要：**按用户 2026-10-15 裁定撤回上述 `umon` syscall 服务**（`helper.c.patch` 还原 `761dfa3` 基线；删 2 个专用探针/测试；`check-qemu-semantics` **149/149** 不回归）⇒ `dadao-m1` 回到 semihosting-only 两条路由。
  - 执行者：engineer

- **2026-10-16 `QEMU-061t`**
  - 摘要：**恢复 `aip.si`（IP 相对寻址，`ADR-0029` `D1`/`D7③`；原 `rela.si`，用户 2026-10-16 裁定改名）的解码 + 语义**。`insn.decode`：`@main` 的 `0x5A` 由手写注释「`rela.si` deleted (`ADR-0012 D5`) → reserved → UNDI」改为**合法 pattern** `aip_si_riii_rb  01011010........................  @main`（= `contracts/opcodes.yaml` 的 `aip.si_riii_rb`：op `0x5A` + `rbha[23:18]` + `imms18[17:0]`；头部计数 **234 → 235**，现由 `tools/qemu/generate_decodetree.py` **从记录数派生**（原硬编码 `256 patterns` 属长期漂移，本任务一并订正、**不再手改生成物**）；生成路线 = 生成器重跑 → `.work/source/qemu` 收敛为 base+1 → `make_patch`。`trans_arith.c.inc` 新增 `trans_aip_si_riii_rb`：`rbha = IP + (sign_extend(imms18) << 12)`，其中 **`IP` = 该指令自身地址**（`load_rb(ctx, 0)` = 既有 `rb0` 口径；**无 `±4` 流水偏移**、**低位不清零**）、`imms18` **有符号**且单位为 **4 KiB 块**（`<<12`、无 `<<2`）、结果**全 64 位**写 `store_rb`；目的 `ha == 0` ⇒ `gen_exception_illegal`（`dst_rb0`）⇒ **「`0x5A` ⇒ UNDI」路径消失**。向量：`tests/vectors/isa/aip-si.yaml` 增 **6 条 L3**（4 semantic + 2 boundary；**独立 oracle** = `IP = BINARY_BASE + 4*loader_words`（harness 布局现场派生）+ SimRISC-05 §1.4 公式，含 IP = 自身地址 / `<<12` / 有符号 / 上下界；另既有目的 `rb0` ⇒ ILLI 例随之转绿）；**顺带订正**该文件 2 条 L1 word（`0x5A04FFFF` → `0x5A07FFFF`、`0x5AFCFFFF` → `0x5AFDFFFF`：原 word 的 `bits[17:0]` 与 notes 声明的 `imms18`（∓1 块 / ±131071）不符，field 派生见证据脚本 oracle）；`tests/vectors/inventory.md` 的 `aip.si_riii_rb` 行 semantic/boundary `deferred QEMU-061t` → **✓**。新探针 `tools/qemu/min_rom_probe_061t.py`（ROM 侧期望值由 `ROM_BASE + 4*idx` 独立派生）**8/8 PASS**。**验证**：`check_qemu_trans --strict` **235/235 (M1 156/156)**、`validate_decodetree` **235/235**、`make check`(L1) EXIT=0、`check-patch-tree`(5 comp/147)/`check-index-blobs` EXIT=0、`validate-vectors`(156/156, 712 cases) EXIT=0；L3：`run_qemu_test` aip-si **12/12** + reserved（UNDI 不回归）**3/3** + 门控向量集 **149/149**；L2 等价：`run_qemu_smoke` **86/86**（均用 `.work/build/qemu` 增量自检二进制）。补丁**无新增**（qemu 36 = 2 份修改）。
  - 执行者：engineer

- **2026-10-17 `QEMU-062t`**
  - 摘要：**新增 `linux-user`（qemu-user）DADAO 后端（P3，ADR-0025 D2/D6）：静态档 + 动态档都能真跑起来**。新目标 `configs/targets/dadao-linux-user.mak`（`TARGET_ARCH=dadao`、`TARGET_LONG_BITS=64`、`TARGET_BIG_ENDIAN=y`；号表 `linux-user/dadao/syscall.tbl` 与 `linux-user/riscv/syscall.tbl` 逐字节相同，sha256 与 `contract-syscall.md §1.2` 锁定快照一致）。新 `linux-user/dadao/**`：`cpu_loop.c`（`trap cfx0,0` ⇒ 号读 `rd15`、按 musl `__dadao_argmask`/`syscall_cp.s` 同一张路由表把 rd16+/rb16+ 还原为位置参数、宿主 `do_syscall` 转发、返回与 `-errno` 写 `rd8`、未实现号 ⇒ `-ENOSYS`）；`elfload.c`（ELF 机器型号）；`signal.c`（[OPEN] 暂定帧 + 信号 tramp 页）；`target_elf.h`（`EM_DADAO`/`ELFCLASS64`/`e_flags[7:0]=1`）；`target_syscall.h`（`AUDIT_ARCH_DADAO = EM_DADAO|AUDIT_ARCH_64BIT`，不带 `LE`）；其余为 asm-generic 头。`target/dadao/**` 按 `CONFIG_USER_ONLY` 切分：`cpu.h` 去掉「不支持 user」硬失败、加 `MMU_USER_IDX`/`DADAO_EXCP_SYSCALL`；`cpu.c`/`helper.c` 把 sysemu ops/`tlb_fill`/`do_interrupt`/对齐异常留在系统档；`trans_ctrl.c.inc` 在 user 档把 `trap cfx0,0` 解为 `DADAO_EXCP_SYSCALL`、其余 trap/`escape`/`cfx2rd`/`cfx2rc` ⇒ ILLI（无 monitor 上下文，且不混 semihosting 停机协议）；`dadao_cpu_class_by_name` 支持短名 `any`。`linux-user/syscall.c` 的 `riscv_hwprobe` 实现改为仅 `TARGET_RISCV`，DADAO 显式 `-ENOSYS`；`syscall_defs.h` 增 `TARGET_DADAO` 的 asm-generic stat/ioctl/statfs 分支。**运行验证**（`.work/evidence/QEMU-062t/run.sh`）：静态 musl（`crt1.o`+`libc.a`）与动态（`libc.so` 作 `PT_INTERP`，`-L` guest root）全绿 45/45；`AT_BASE`/`AT_PHDR`/`AT_ENTRY`/`AT_PHNUM`/`AT_PHENT` 与文件独立对照；`writev`/`fstat` 的结构双向大端；`rd8 = -EBADF`；未实现号 `-ENOSYS`；`ioctl` 的 rb16 路由；`--inject`（路由表 0x02→0x00）与 `--inject-be`（`TARGET_BIG_ENDIAN`→0）均先 FAIL、`cp`+md5 还原后回绿。补丁 **36 → 59**（qemu = 新增 49 + 修改 10）。
  - 执行者：engineer

- **2026-10-17 `ISS-249`（`TESTCASES-047t` 静态档重跑收口）**
  - 摘要：**`linux-user/dadao/cpu_loop.c:dadao_argmask()` 与 musl 端口逐号对齐（12 → 245 条）**。宿主侧按同一张表把 `rd16+/rb16+` 还原为位置参数表；表项/掩码派生口径写在 musl `arch/dadao/syscall_arch.h` 头部注释（内核 `SYSCALL_DEFINE` 原型 + 18 处地址-as-整数例外）。漂移门控 = `tools/qemu/check_syscall_abi.py`（`make check-syscall-abi`，L1）：三载体逐项对账 + 完整性（musl 能发出的名全覆盖）+ `.Lm<mask>` 块的搬运条数 = 掩码位值。补丁**无新增**（qemu 59）。
  - 执行者：engineer

- **2026-10-19 `QEMU-063t`**
  - 摘要：**linux-user 启动时启用 MemRAS 溢出区（`contract-isa.md §5.4-§5.6`、`contract-abi.md §2.2`）**：`init_main_thread` 为初始线程 `target_mmap` 1 MiB 专用区，将 `ra0[47:0]`（MRPTR）指向区顶并预置 invalid-entry 哨兵（0），使 `call` 深度超过 RegRAS 63 项时按契约落到 MemRAS 而非 RASOF；此前 MRPTR 恒 0，任何用户程序调用链 >63 层即 `SIGSEGV/ACCERR`。修后 `dbms` 静态+动态两档 **PASS**（oracle 逐字节一致）且 048t 抽样（`sqlite3`/`treecc`/`15-trie`/`fixoutput`/`IntMM`）两档 10/10 不回归；`check-qemu-semantics` **161/161**、`check-qemu-smoke` **90/90**。补丁**无新增**（qemu 59 = 修改 `linux-user/dadao/cpu_loop.c.patch`）。
  - 执行者：engineer

## M9

- **2026-10-19 `QEMU-064t`**
  - 摘要：**`ext` 迁 `100/101`、`shl` 迁 `010/011-000` 并去 `u`；新增 `rol.o/t/w/b`（逻辑循环左移，`orrr`/`orri`）的 decode + trans（`ADR-0032 D1/D2/D3/D4`）**。`insn.decode` 由 `tools/qemu/generate_decodetree.py` 从 `contracts/opcodes.yaml` 重生成（pattern **235 → 243**，计数从记录派生）：`ext.uo/so` orrr `100-000/001`、orri `101-000/001`；`shl.{o,t,w,b}` orrr `010-000`、orri `011-000`；`rol.{o,t,w,b}` orrr `010-001`、orri `011-001`；既有格（`swym` `0x77880000`、`aip.si` `0x5A` 等）未动。`trans_shift.c.inc`：`trans_shl_u{otwb}_{orrr,orri}_rd` → `trans_shl_{otwb}_{orrr,orri}_rd`（8 条改名，语义不变）；新增 8 条 `trans_rol_{o,t,w,b}_{orrr,orri}_rd`——`rol.o` 全 64 位（`tcg_gen_rotl_i64` / `tcg_gen_rotli_i64`）；`rol.t/w/b` 取源低 `W` 位、旋转量 `rdhd & (W-1)`（orrr，mod W）、`W-k` 双移位合成环移后按值语义零扩展写满 64 位；`orri` 的 `immu6 > W-1` ⇒ ILLI（`encode_sbz`）；目的 `rdhb == rd0` ⇒ ILLI（`dst_rd0`）。诊断工具机械同步（`min_rom_probe_005t.py` 的 `shl`/`ext` 编码、`check_005t_coverage.py` 的 id 清单）。L3 语义向量新增 `tests/vectors/rol/rol.yaml`（**64 条**，独立 oracle = Python 按 `rol(x,n,W)=((x<<(n%W))|(x>>(W-n%W)))&(2^W-1)` 重算；覆盖 4 宽度 × orrr/orri × `n=0/1/W-1`、`rol.o` 的 31/32/63、`mod W`、orri 越界 ILLI、每宽度 `rd0` ILLI），并挂入 `check-qemu-semantics` 载体清单（`isa/*.yaml` 之外的 `rol/` 目录，因 `validate_vectors` 要求 `tests/vectors/isa/*.yaml` 的 id 必须是 M1）。L3 `check-qemu-semantics` **224/224**（新增 64）、L2 `check-qemu-smoke` **90/90** 不回归。补丁**无新增**（qemu 59 = 2 份修改：`insn.decode.patch` + `insn_trans/trans_shift.c.inc.patch`）。
  - 执行者：engineer

- **2026-10-20 `QEMU-065t`**
  - 摘要：**qemu-user 线程语义（线程链 T2）**：`clone`/TLS/futex/`exit`/信号路径打通；并发互斥出现丢更新时归因到 musl `a_cas` 的假原子实现（另立 `ISS-294`）。
  - 执行者：engineer

- **2026-10-20 `QEMU-066t`**
  - 摘要：**qemu-user 线程缺口三条（`ISS-296`/`ISS-297`/`ISS-298`）**。① `ISS-296`（PI futex）：`do_futex` 把 guest 地址直接交给宿主内核，而 PI futex 字**存的就是 owner TID**；DADAO 大端 + 宿主小端 ⇒ 内核查到的 tid 被字节颠倒、找不到任务 ⇒ `FUTEX_LOCK_PI` 恒 `ESRCH`（musl 落到 100 ms `__timedwait` 兜底，`pthread_mutex_pi` 报 "got deadlock"）。修法 = 对 `LOCK_PI`/`LOCK_PI2`/`TRYLOCK_PI`/`UNLOCK_PI` 四个 op 在宿主调用前后做**保值的字节序转换**（`pi_futex_word_to_host`/`pi_futex_word_to_target`；整字转换使 `FUTEX_WAITERS`/`OWNER_DIED`/`TID_MASK` 数值位不变）。`WAIT_REQUEUE_PI`/`CMP_REQUEUE_PI` 不动（musl `src/` 0 处使用，PI 条件变量不存在消费者；requeue 需 PI 字在**阻塞等待**期间保持宿主序，会破坏 owner 视角）。已知边界已在注释显式登记：真正阻塞在 `LOCK_PI` 期间字面处于宿主序。② `ISS-297`（robust list）：`set_robust_list`/`get_robust_list` 由恒 `ENOSYS` 改为**注册/查询一致**（`TaskState.robust_list_head`；`len != 3*sizeof(long)` ⇒ `EINVAL`、`head==0` 注销、`pid ∉ {0, 自身 tid}` ⇒ `ESRCH` 的显式口径）——musl 在用户态自己遍历 robust 链表（`pthread_create.c:119-137`），平台侧只需 ABI 形状一致。③ `ISS-298`（取消被重启）：根因**不是** `SA_RESTART` 传播，而是 DADAO 的 `struct target_ucontext` 把 `uc_mcontext` 加了 `QEMU_ALIGNED(16)` ⇒ 帧内 `uc_mcontext` 落在 176 而 musl `ucontext_t` 期望 168 ⇒ handler 读到的 `MC_PC` 是 8 字节对齐填充（恒 `0`）⇒ `[__cp_begin,__cp_end)` 判定永假、`cancel_handler` 只能 `tkill` 重投，取消被吞。修法 = 去掉该对齐属性（帧与 guest `ucontext_t` 逐字节一致）。验证：`functional/pthread_mutex_pi`、`functional/pthread_robust`、`regression/pthread-robust-detach`、`regression/pthread_cond_wait-cancel_ignored` 两档全 pass；T3 的 19 例两档 **19/19**；`check-qemu-semantics` **224/224**、`check-qemu-smoke` **90/90** 不回归。补丁 **59 → 60**（+`linux-user/qemu.h.patch`，改 `linux-user/syscall.c.patch`/`linux-user/dadao/signal.c.patch`）。
  - 执行者：engineer

- **2026-10-20 ADR-0034**
  - 摘要：**`lr`/`sc` 重排为 24 条（`<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>`）的 decode + 桩同步**（`ADR-0034 D3`/`D4`/`D5`/`D7` 执行前置 2；语义仍 `scope: excluded` ⇒ ILLI，本笔不实现语义）：`insn.decode` 由 `tools/qemu/generate_decodetree.py` 从 `contracts/opcodes.yaml` 重生成（pattern **243 → 259**，计数从记录派生）；`trans_mem.c.inc` 的 `lr`/`sc` 桩 **8 → 24** 并改名（`trans_lr_nn_o_orrr_rd` → `trans_lr_o_nn_orrr_rd` 等；**删除** `lr.*.nr`/`sc.*.an` 四条旧桩，新增 `.t/.w/.b` 与 `an/nr/ar` 组合 16 条），全部沿用 ILLI 桩写法；`fence_oiii_imm` 模式随真源变 `01110111100000`。补丁 **2 份改**（`series` 仍 **60**、`check-patch-tree` **185 不变**）。**真值**：`validate_decodetree` 259/259 错误 0；`check_qemu_trans` **259/259（M1 156/156）**；桩数 **24/24** 且与 decode 名字集合双向一致（无多余/缺失）。**未跑**：`build-qemu`/L2/L3（按派单；源码/补丁树自洽已由 `check-patch-tree` 断言⑥⑨ 与 `--source-state` 保证）。
  - 执行者：engineer

- **2026-10-21 `QEMU-067t`**
  - 摘要：**原子指令语义（`fence` + 24 条 `lr/sc`）由 ILLI 桩换为真实实现**（`SimRISC-11 §4.1/§4.2`、`ADR-0034 D1/D2/D6`、用户裁定 2026-10-21「甲」）。`fence`：`fm ≠ 0`（含 TSO 预留 `fm=8`）或 `pred[11:10]`/`succ[5:4]` SBZ 非零 ⇒ ILLI；`pred = succ = 0` ⇒ **no-op（不发任何屏障）**；其余按 `(pred, succ)` 的 R/W/I/O 类映射到 `TCG_MO_{LD,ST}_{LD,ST}` 并附 `TCG_BAR_SC`（I/O 类无设备模型 ⇒ 各自贡献两个内存类，只强不弱），宿主线程间可见。`lr`：`hb ≠ 0` ⇒ ILLI；读含该地址的整 8 B 字（`MO_BEUQ`），按 `k = addr & 7` 与宽度大端抽取并零扩展写 `rdHC`，置本 hart 保留（`lock_addr`/`lock_val`/`lock_valid`，精确 8 B 字）。`sc`：先按**数据宽度**判自然对齐（`.b`=1/`.w`=2/`.t`=4/`.o`=8，不满足 ⇒ 显式 MALIGN，且**与是否持有保留无关**）；保留在**且地址匹配** ⇒ 以单条 8 B 宿主 CAS（`tcg_gen_atomic_cmpxchg_i64`，`MO_BEUQ|MO_ALIGN_8`）合并写入、`rdHB = 0`，否则不写、`rdHB = 1`；**成败皆清本 hart 全部保留**。保留清除还挂在三处入口：异常/中断进入（`dadao_cpu_do_interrupt`）、user-mode 信号帧建立（`setup_rt_frame`）、新 guest 线程（`cpu_clone_regs_child`）与复位。L3 向量新增 `tests/vectors/atomics/{atomics-lrsc,atomics-fence}.yaml`（**127 例**，独立 oracle = Python 按 §3 手算大端抽取/掩码合并；`sequence:` 可选字段表达「`lr` 后接 `sc`」与「失败清保留」），载体进 `check-qemu-semantics`。`tests/scripts/build_test_binary.py`：新增可选 `sequence:`（缺省行为逐字节不变）+ `derive_width_from_mnemonic` 认识 `lr/sc` 的宽度段。**真值**：`check-qemu-semantics` **224 → 351（351/351）**、`check-qemu-smoke` **90/90** 不回归、`build-qemu` rc=0、`check_qemu_trans --strict` **259/259（M1 156/156）**、端到端两线程 `__atomic_add_fetch` CAS 环 5 轮 **40000/40000** 精确（`nm -u` 无 `__atomic_*`）；补丁 **8 份改**（`series` 仍 **60**、`check-patch-tree` **185 不变**）。限制：保留粒度 = 精确 8 B 字值比对（另一 hart 写**同值**检不出，即 ABA）；设备/非一致内存语义不在本机范围。
  - 执行者：engineer

- **2026-10-22 SPEC-164t**
  - 摘要：**`OPC-MISC` 编码迁 `op 0x47`（原 `0x77`）；`ctpop`/`ctlz`/`cttz` 并入 MISC**（用户 2026-10-22 裁定「OPC-MISC的编码改为：0100-0111」「ctpop_orri_rd ctlz_orri_rd cttz_orri_rd 从 OPC-octa 改为 OPC-MISC，opx：100-101/100-110/100-111」；`ADR-0034`/`ADR-0012` 的 `## 修订`）。`insn.decode` 由 `tools/qemu/generate_decodetree.py` 从 `contracts/opcodes.yaml` 重生成（pattern 仍 **264**，计数从记录派生）：26 条 MISC pattern 前缀 `01110111 → 01000111`；`ctpop/ctlz/cttz` 由 `0100000001110x/1x` 改为 `01000111100101/10/11`（即 `op 0x47`、`ha 0x25/0x26/0x27`）；trans 函数名与语义不变。附带注释同步（`trans_ctrl.c.inc` 的 `op=0x47`、`trans_bitcnt.c.inc` 的 `OPC-MISC 100-101/110/111`）。`check_qemu_trans --strict` **264/264（M1 156/156）**；`validate_decodetree` 264/264 错误 0。补丁 **3 份改**（`series` 仍 **60**、`check-patch-tree` **192 不变**）。
  - 执行者：engineer

- **2026-10-22 `QEMU-069t`**
  - 摘要：**`fcls`（FP classify）位序重排**（`SPEC-156t`：位序改为 754/LLVM 顺序）：`trans_fp.c.inc` 的 `fp_classify_one` 10 个位号同步；`min_rom_probe_035t.py` 改为**按 `spec §7` 现场解析**（独立 oracle）并补 7 个边界例，84/84。
  - 执行者：engineer

- **2026-10-22 `QEMU-068t`**
  - 摘要：**`clmul.o` 执行语义**（64×64 无进位乘 → 128 位，`rdHB` 高 / `rdHA` 低；`rd0` 单侧丢弃、双侧或同非 `rd0` 寄存器 ⇒ ILLI）：`insn.decode` + `trans_clmul_o_rrrr_rd`；L3 向量 `tests/vectors/clmul/clmul.yaml`（81 例，独立逐位 oracle）；`check_qemu_trans --strict` **260/260**。
  - 执行者：engineer

- **2026-10-22 `QEMU-072t`**
  - 摘要：**`ftrnd`/`fornd` 执行语义**（softfloat `round_to_int`；静态 5 档用临时 `float_status` 只合 NV，DYN 走真实 `rf0` 合 NV|NX）：2 条 `insn.decode` pattern + `helper_fp_round_to_int` + `gen_fp_round_to_int` + 2 条 `trans_*`；探针 413/413；`check_qemu_trans --strict` **260/260**。
  - 执行者：engineer

- **2026-10-22 `QEMU-071t`**
  - 摘要：**`ftmin`/`fomin`/`ftmax`/`fomax` 执行语义**（softfloat `minimum_number`/`maximum_number`：sNaN ⇒ NV，结果 canonical qNaN）：4 条 `insn.decode` pattern（`0x26/0x27/0x2E/0x2F`）+ `helper_fp_minmax` + `gen_fp_minmax` + 4 条 `trans_*`；`check_qemu_trans --strict` **264/264**。
  - 执行者：engineer

- **2026-10-23 `QEMU-070t`**
  - 摘要：**`ftfma`/`fofma` 执行语义**（softfloat `float{32,64}_muladd` 单次舍入；canonical qNaN；`0×Inf + qNaN` 仍置 NV）：2 条 `insn.decode` pattern + `helper_fp_muladd` + `gen_fp_muladd` + 2 条 `trans_*`；探针 122/122；`check_qemu_trans --strict` **266/266**。
  - 执行者：engineer

- **2026-10-24 `QEMU-073t`**
  - 摘要：**`cpu_loop_exit` longjmp 泄漏 MMIO 重入守卫（`ISS-064`）结构化复位**：`system/memory.c` 在 `access_with_adjusted_size` 置位 `engaged_in_io` 时把该守卫压入**线程级链**（栈上节点，正常路径出栈），新增 `mem_reentrancy_guard_abort()`（声明在 `include/system/memory.h`）；`accel/tcg/cpu-exec-common.c::cpu_loop_exit` 在**唯一** `siglongjmp(cpu->jmp_env)` 之前调用它——跳转时被放弃的访问帧仍在栈上，可安全遍历整条链复位（两个 `sigsetjmp` 落点共用此唯一 longjmp 产生点）。现场：`dadao_cpu_tlb_fill` 只映射 RAM/ROM，非 RAM/ROM 一律 UNMAPPED（0x87）⇒ 现机无 MMIO 可达路径，原载体 exit-port 已删（ADR-0020 D8），用户裁定「**不做复现，只修**」；本地临时实验（设备 + tlb_fill 放行，均未入交付物、cp+md5 还原）给出修复前 `rc=2` + `Blocked re-entrant IO on MemoryRegion: dadao-testio`、修复后 `rc=0` 无告警。补丁 **60 → 63**（新增 `accel/tcg/cpu-exec-common.c.patch`、`include/system/memory.h.patch`、`system/memory.c.patch`）；`check_patch_tree` **198** 绿、`check_qemu_trans --strict` **266/266**、L1/L2 rc=0。
  - 执行者：engineer

## M10

- **2026-10-25 `QEMU-074t`**
  - 摘要：**`cmp.{ut,uw,ub}` 结果去掉零扩展（ADR-0037：-1 = 64 位全 1）**：`trans_cmp_{ut,uw,ub}` 删除 `ext32u/ext16u/ext8u`（`gen_cmp_three_way` 的 i64 -1/0/1 与源截断保留）；`tests/vectors/isa/reg-compare.yaml` 3 条 -1 期望改 `0xFFFF_FFFF_FFFF_FFFF`（0/+1 未动）；新增 `tools/qemu/min_rom_probe_074t.py`（21 例：-1/0/+1、源截断、`cmp.{ut,uw,ub}→br.n`、控制组）；`min_rom_probe_005t.py` 的 V3 旧零扩展断言同步。真值：L1/L2 绿、`check-qemu-smoke` 90/90、L3 967/978（11 deferred）、注入 16/16 红→绿。
  - 执行者：engineer

- **2026-10-26 `QEMU-076t`**
  - 摘要：**semihosting 判定迁至 `0x3FF00–0x3FFFF`（ADR-0038 D1/D4）**：`insn_trans/trans_ctrl.c.inc` 译码条件 `((immu18 >> 16) & 0x3) == 0x3` → `immu18 >= 0x3FF00`；`helper.c` 的同判据防御分支与两处注释同步；调用点 `0x30000` → `0x3FF00`（bootrom_app/`codegen_crt0`/`build_test_binary`/M5 向量/e2e/`min_rom_probe_*`）。**语义/服务号不变**（`0x30001` HBI INIT、指令编码字、`0x3FFFF` 掩码常量未动）。
  - 执行者：engineer

- **2026-10-29 `INTEG-039t`**
  - 摘要：**地址空间 Step 2（ADR-0040）**：`ptw_enable=1` 由显式失败改为两级页表步进——从 PA 读 64 位大端 PTE（`HSJU[63:60]`、`PPN[55:16]`/超页 `[55:29]`、`SPF/GPF[15:8]`、flags `[7:0]`），L1 next-level / L1 512 MiB 超页 / L2 64 KiB 普通页，`VA[41:29]`/`[28:16]` 选索引，形成 PA56；按 `P=0`/超页缺失 → SPF/GPF → HSJU → R/W/X 顺序判错，页表异常经 §5 流程进入 `cfx_ptw`（新 `DADAO_EXCP_PTW_FAULT` + `ptw_fault_cause/info`，cfx4 的 `cause_nonmaskable` 补齐页级 cause）；保留位忽略、超页 PPN 低位强制清零；A/D 只定义不更新（无 TLB）。新增探针 `tools/testcases/arch/min_rom_probe_integ039t.py`（37 例）。
  - 执行者：engineer

- **2026-10-29 `INTEG-038t`**
  - 摘要：**地址空间 Step 1（ADR-0039 §8.5）**：CPU 地址按 48 位处理（`addr[47:42]` 分区）；`addr[47:42] = 0` 为内存窗口，`ptw_enable=0` 时数据/取指均 ⇒ CFXMEM（不再按 umon 段特判，也不直通 pmem）；`ptw_enable=1` 的页表步进尚未实现 ⇒ 显式失败（不静默成功）。新增单 PTBR `cfx_ptw_ptbr`（cg9 rc0，写掩码 `PPN[55:16]`）与 `cfx_ptw_enable`（cg8 rc8，1 位）；复位均为 0；写 PTBR/使能不隐含 TLB 失效。保留 cfx（7–14、19–61）普通 ld/st ⇒ CFXMEM。`cfx4` 加入测试机实现集（仅 Step 1 寄存器子集）；`cfxreg_unimpl` 测试改用 `cfx5`。新增 `tools/testcases/arch/min_rom_probe_integ038t.py`（16 例）。
  - 执行者：engineer

- **2026-10-29 `INTEG-040t`**
  - 摘要：**地址空间 Step 3（ADR-0041）**：TLB 并入 `cfx_ptw`——条目按「虚拟页 + 16 位 ASID（`cfx_ptw_tlb_asid`）」匹配、`G=1`（PTE bit4，原保留）跨 ASID；`ptw_enable=1` 即参与查找、`0` 时旁路，无 `tlb_enable`/`tlb_exist`；命中不重读 PTE（按 `SPF/GPF → HSJU → R/W/X` 同序检查，异常直接进 `cfx_ptw`），miss 走页表步进且成功才填充（替换 dirty 条目先回写）。A/D 在条目中维护（fill 不产生回写、读/取指置 A、写置 A/D、缺页/权限失败不更新），`CLEAN`/`FLUSH`/替换以原子 OR 回写 PTE，`INVALID` 不写回；回写失败报 `PTWERR`（`1<<7`，`cause_info` = PTE PA）并保留条目。新增 `cfx_ptw` cg12 接口（rc0 control：op/scope/ASID_ANY 正交，rc1 ASID，rc2 start，rc3 size；`scope=11` 或 `range` 且 `size=0` ⇒ `CFXREG`（仅 clean/invalid/flush；op=00 优先 no-op））。QEMU 自有 translation cache 在 PTBR/ptw_enable/ASID 写、条目删除与 run-mode 切换时丢弃（guest TLB 条目保留，不构成隐含失效）。新增探针 `tools/testcases/arch/min_rom_probe_integ040t.py`（34 例）。
  - 执行者：engineer

- **2026-10-29 INTEG-041t**
  - 摘要：**`fence` 解码/语义迁到 `ciii`（`opc 0x79`）**（`ADR-0044 D1`–`D8`）：`insn.decode` 由 `contracts/opcodes.yaml` 重生成（266 patterns），`trans_ctrl.c.inc` 的 `trans_fence_oiii_imm` 改为 `trans_fence_ciii_cfx(arg_main)`：`ha = cfxha`（0 = all cfx；保留 7–14/19–61 ⇒ ILLI），`hb != 0` ⇒ ILLI；`pred/succ` 六位 `cr/cw/ci/co/mr/mw` 映射到 `TCG_MO_*`，零掩码 no-op。qemu-user 为平坦内存模型，cfx 选择器不额外削弱屏障。**真值**：`check-patch-tree` 205 OK；`semantics_gate` 结构派生 0 差异；`atomics-fence.yaml` **17/17 PASS**（含 hb≠0、reserved cfx、零掩码 no-op）；`build-qemu` rc=0。补丁 **2 份改**（`series` 63）。
  - 执行者：engineer

- **2026-10-30 INTEG-042t**
  - 摘要：**Step 4：`cfx_pmem` 64 KiB SRAM + SRAM↔PA DMA（ADR-0042）**。测试机把 SRAM 映射为独立 RAM 区（`0x0100_0000_0000_0000`，56 位 PA 之外，guest PA 无法别名），`tlb_fill` 把 cfx17 内部偏移 `0..0xFFFF` 映射过去（越界 ⇒ CFXMEM）；`cfx_reg_ptr` 的测试机 cfx 集合加 `17`，保留 cfx 改 `6`–`14`/`19`–`61`（`cfx5` = cache，未实现 ⇒ CFXREG）。`cg15` rc0–4 = `dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`：方向位、CFX 低42/PA 低56、size 30 位 `1..2^29`，START 自清并在虚拟时钟定时器上异步完成（BUSY 可观测），setup 错误置 `ERROR|ERR_CODE`（SIZE/CFX_RANGE/PA_RANGE/PA_FAULT），`BUSY` 期间 cg15 写与 DONE/ERROR W1C 被忽略；`PMEM_DMA`（`1<<8`，可屏蔽）经 `cpu_exec_interrupt` 投递到 `cfx_pmem`（被屏蔽只置 pending），`cfx_pmem` 的 `cause_nonmaskable` 按 §4.9 只保留 CFXTRAP/CFXMEM/CFXREG。新增探针 `tools/testcases/arch/min_rom_probe_integ042t.py`（23 例）。
  - 执行者：engineer

- **2026-10-30 INTEG-044t**
  - 摘要：**cfx 两轴权限模型（ADR-0045）**：cg0–3 的 rc0–3 改为 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类 64 位同步来源 mask、rc4 = `cfx_intr_mask`，删除 `global_version`/旧 `global_cfx_mask`，cfx0–3 增加 `cg8/rc1 global_cfx_intr_mask`；初值 power/普通 cfx `0xFFFF_FFFF_FFFF_FFF7`、hmon `0x7FFF_FFFF_FFFF_FFF7`、中断 mask 全 1。权限判定先判 reserved→ILLI，再以「当前模式行 + 源 cfx 位」判四类 mask（self 只绕 cfx 轴），拒绝 ⇒ `CFXPERM`（`1<<7`）进当前模式 monitor；escape `cfxha` 固定当前 cfx，目标/帧错误 ⇒ `CFXESC`（`1<<3`）进当前 cfx。直接 ld/st/取指在 `tlb_fill` 按 cfxmem/cfxexe 检查；异步按当前 cfx `cfx_intr_mask` 与当前 mode monitor 的 `global_cfx_intr_mask` 两级过滤后置 pending。trap 进入时保存并置全 1 `global_cfx_intr_mask`，escape 恢复；mask 写触发 translation cache 丢弃。`-d cpu` dump 改输出新 mask 字段。新增探针 `min_rom_probe_integ044t.py`（6 例），并迁移 044/045/046/039/040/042 探针与 bootrom 到 hmon 引导。
  - 执行者：engineer

- **2026-10-30 INTEG-045t**
  - 摘要：**cfx 指令清理同步**：`insn.decode` 由 `contracts/opcodes.yaml` 重生成（266 → **264** patterns，计数从记录派生）；删除 `trans_cfxld_crii_cfx`/`trans_cfxst_crii_cfx` 两个 ILLI 桩（两条指令已从 ISA 删除、其两格转为空白保留 ⇒ decode UNDI），`check_qemu_trans --strict` 264/264、orphan 0；`fence_cfx_reserved` 的保留集由 `7–14` 改为 **`6–14`/`19–61`**（与 `DADAO_CFX_IS_RESERVED` 及 `encode_cfx_reserved` 统一）。补丁 **2 份改**（`series` 63、`check-patch-tree` 205 不变）；`build-qemu` rc=0，`check-arch` 全绿（7 个 cfx 探针）。
  - 执行者：engineer

- **2026-10-30 `INTEG-046t`**
  - 摘要：**Step5 启动链 QEMU 侧（ADR-0043 D1/D2/D4/D5/D10/D14）**：BootROM 几何改为 256 KiB（`0xffff_fffc_0000`–`0xffff_ffff_ffff`），复位向量独立为 `DADAO_BIOS_LOAD_BASE`（`0xffff_ffff_0000`，既有 `-bios` 仍按 64 KiB 窗口装载，语义不变）；新增机器属性 `bootrom-image=<path>`（`-machine dadao-m1,bootrom-image=...`，要求恰 256 KiB，与 `-bios` 互斥，`-kernel` 可选且不改复位 PC）；新增 hmon/smon SRAM（cfx3 `0x0fff_0000_0000` / cfx2 `0x0bff_0000_0000`，各 64 KiB，宿主地址在 56 位 PA 之外，`tlb_fill` 按内部偏移 `0x3ff_0000_0000` 路由、越界 ⇒ CFXMEM）；RAM 在 PA 0 增加 16 MiB 别名（PTE 读取与 `cfx_pmem` DMA 同时接受 `[0,16 MiB)` 与 `[RAM_BASE,+16 MiB)`），供 smon 的 PTBR=0 页表；`translate_for_debug` 覆盖 hmon/smon SRAM（半托管参数块）。新增探针 `min_rom_probe_integ046t.py`（15 例）与 builder `build_step5_bootrom.py`。
  - 执行者：engineer

- **2026-10-31 `INTEG-048t`**
  - 摘要：**`cfx_<cfxname>_hypv_cg_reg_deleg` 强制检查（DADAO-13 §1；R1–R6）**：新增静态门 `cfx_deleg_denied()`（数据源固定 `mode[DADAO_MODE_HYPV].cg_reg_deleg`，仅 `supv` 生效、位索引 = cg 编号 0–63、`1 ⇒ CFXPERM`），在 `helper_cfx2rd`/`helper_cfx2rc` 的 `cfxreg` 轴之后、`cfx_pmem cg15` 特例与 `cfx_reg_ptr()` 之前调用 ⇒ **cg3 无例外**（supv 访问任何 cfx 的 cg3 由恒 1 的 bit3 拒绝为 `CFXPERM`，不再落到 `CFXREG`），hypv/user/jail 不受本检查约束；`helper_cfx2rc` 对 `cg3 rc12` 的写强制 `value | (1<<3)`（软件写 0 无效、读回恒 1）；复位值 `~0` 与 `cpu.h` 布局不变。新增探针 `min_rom_probe_integ048t.py`（23 例）。
  - 执行者：engineer

- **2026-10-31 `INTEG-049t`**
  - 摘要：**cg7 内部空间描述在 QEMU 落地（DADAO-12 §3.8）**：删除 `DADAOCfxRegs.sram_block_sel`/`sram_addr`（旧「块选择 + 块内地址」RW 语义作废），改为编译期常量 16×4 只读表 `dadao_cg7_space_reg()`（smon/hmon `desc=0x3 start=0x3ff_0000_0000 size=0x1_0000 attr=R|W|X`、pmem 同 start/size 而 `attr=R|W`、power `desc=0x5 start=0x3ff_fffc_0000 size=0x4_0000 attr=R|X`，其余块/其余 cfx 读 0）；`cfx_reg_ptr()` 删除 `case 7`，`helper_cfx2rd`/`helper_cfx2rc` 在权限与 deleg 门之后插入 cg7 分支（读任意 rc 回表值、写任意 cg7 rc ⇒ `CFXREG`）；未实现 cfx（`cfx5` 等）仍 `CFXREG`，`exists=0` 只对已实现 cfx 可见。新增探针 `min_rom_probe_integ049t.py`（12 例），`044t`/`045t`（13→14 例）/`integ048t` 旧 cg7 用例按新语义改造（不删用例、不放宽断言）。
  - 执行者：engineer

- **2026-10-31 `INTEG-050t`**
  - 摘要：**`cfx_time`（cfxha 18）+ 单 hart `cfx_hart` 定时器（DADAO-12 §4.7/§4.10）**：测试机 cfx 集合加 15/18（`DADAO_NUM_CFX` 7→9，map `{0,1,2,3,4,15,17,18,63}`）；`cfx_time` `cg10 rc0 = 1 GHz`、`rc1` = 虚拟时钟 64 位（1 count=1 ns）、`SBI_TIME_GET`；`cfx_hart` `cg8 rc0 = hart_id 0`、`rc2 cycle`/`rc3 insn` 均 64 位（cycle 由时钟派生、insn 在 `insn_start` 每指令累加，不依赖 `-icount`）、`rc4 timer_cmp`/`rc5 timer_ctrl`（ENABLE/IMASK/ISTATUS）、`rc1/rc6/rc7` 保留；TIMER（`1<<10`，可屏蔽，`cause_info=0`）为 one-shot，IMASK 时置既有 `cg5 rc5` bit10、解除 IMASK 后经异步路径投递。异步只复用既有单源路径（per-source bool + `CPU_INTERRUPT_HARD` + `cfx_enter(async)`），不做跨源统一仲裁。新增探针 `min_rom_probe_integ050t.py`（17 例）；m5 `unimplemented cfx` 样本改 `cfx_llc`。
  - 执行者：engineer

- **2026-10-31 `INTEG-051t`**
  - 摘要：**统一异步中断仲裁（pending 归目标 cfx；DADAO-12 §5；ADR-0045 D3）**：删 050 的 `pmem_dma_irq`/`hart_irq` 两个 per-source `bool`，异步 pending 只记在**目标 cfx** 的 `cg5 rc5`（`PMEM_DMA` `1<<8`→`cfx_pmem`、`TIMER` `1<<10`→`cfx_hart`；不建跨 cfx 聚合位图/不新增 `async_enable`）；源事件只置位 + 重踢 `CPU_INTERRUPT_HARD`，`dadao_cpu_exec_interrupt()` 收成单一入口 `dadao_async_arbitrate()`：按**目标 cfxha 升序**（15→17）选第一个可投源、一次调用至多一次 `cfx_enter(async)`（单层、不嵌套），掩码判定仍只在 `cfx_enter` step 3/4/5（不复制公式），`entered=false` 时保留 pending；投递成功清该位。补投踢点四类：`helper_cfx2rc` 通用写尾、`cfx_hart cg8 rc4/rc5` 写、`helper_cfx_escape` step 1 之后、源事件（DMA 完成/定时器到期）。D9 帧屏蔽抽成 `cfx_frame_block_async()` 供同步 trap 与异步仲裁共用（否则 async 帧内不挡第二源、escape 会恢复陈旧 mask）。新增探针 `min_rom_probe_integ051t.py`（14 例：目标 cfx pending / S-H 不混 / 两级 mask 与 cause mask 补投 / IMASK / 低 cfxha 优先 / escape 补投 / 直接目标 poison / 去重 / ERROR info + 两项离线契约与结构断言）。
  - 执行者：engineer

## M11

- **2026-11-02 `QEMU-078t`**
  - 摘要：**scaleB C1 与 sc rd0（SPEC-181t F5.2/F8.2）**。`ftsclb`/`fosclb` 的第三源由 `rfHD` 改为 `rdHD`（同 `orrr` 编码）：`gen_fp_arith` 对 scaleB 用 `load_rd(a->hd)` 取 64 位有符号整数指数，`helper_fp_arith` 删除 `floatXX_to_int32` 路径、改为 `fp_scaleb_exp()`（超出 int 范围按 IEEE 754 饱和到溢出/下溢）。`gen_sc` 在搬运地址前判 `a->hb == 0` ⇒ 静态 ILLI（不写内存、不置成功/失败），12 条 `sc.*` 编码未动；`rdHC=rd0` 仍合法。`insn.decode` 由 `opcodes.yaml` 重生成后逐字节不变（bank 不在 decodetree 里）。补丁 **3 份改**（`helper.c` / `insn_trans/trans_fp.c.inc` / `translate.c`）；证据 `.work/evidence/QEMU-078t/run.sh` rc=0（17 例行为 + 两次注入→FAIL→`cp`+md5 还原→回绿；`atomics-lrsc` 125/125 回归）。
  - 执行者：engineer

- **2026-11-02 `QEMU-081t`**
  - 摘要：**用户态/系统态页大小由 4 KiB 改为 64 KiB（DADAO-12 §2.2.2：`VA[15:00]` 页内偏移）**。`target/dadao/cpu-param.h` 的 `TARGET_PAGE_BITS` 12→16（唯一源码改动，`TARGET_VIRT_ADDR_SPACE_BITS` 保持 48），补丁由 `make_patch.py` 重导出（**1 份改**，`series` 63）；`TARGET_PAGE_SIZE/MASK/ALIGN` 派生面随之更新：linux-user 的 `AT_PAGESZ`/`getpagesize`/ELF 装载/`target_mmap`(`mmap_h_lt_g`)/`do_brk`/`setup_arg_pages`(guard 64 KiB)/sigtramp/`probe_guest_base`(`MAX(SHMLBA,TARGET_PAGE_SIZE)`)，softmmu 的 `tlb_set_page(...,TARGET_PAGE_SIZE)`/`translate_for_debug.lg_page_size`/subpage 容器。审计确认补丁集无第二处 4 KiB 假设；系统态各区（RAM 16 MiB、ROM 256 KiB、pmem/hmon/smon 各 64 KiB）均 64 KiB 对齐、无 <64 KiB MMIO 设备。测试驱动 `tools/qemu/user_mode_smoke.py` 的 `% 4096` 改 `% 65536` 并新增静态/动态 `getpagesize`/`sysconf(_SC_PAGESIZE)`/`getauxval(AT_PAGESZ)`=65536 断言。证据 `.work/evidence/QEMU-081t/run.sh`（静态+运行时注入→FAIL→`cp`+md5→回绿）。
  - 执行者：engineer

- **2026-11-03 `QEMU-079t`**
  - 摘要：**Kaiwu-Tiny 系统机（spec/Kaiwu §1–§7）**：`dadao-m1` 新增运行时 `profile` 属性（`legacy` 缺省 / `tiny`），选择优先级 `-machine ...,profile=` > `DADAO_TEST_PROFILE`（回退在启动日志可见）> 缺省；CPU env 保存 `env->prof`，reset/`tlb_fill`/semihosting 调试翻译/装载全部改读 profile，canonical `DADAO_RAM_*`/`DADAO_ROM_*`/`DADAO_RESET_PC` 保持 legacy 口径。Tiny：BootROM 64 KiB `0xffff_ffff_0000`、SRAM 8 MiB `0xffff_ff00_0000`、无 alias/hmon/smon/pmem、无 cfx/PTW/user；raw `-kernel` 装 `0xffff_ff01_0000`（前 `0x100` 零、入口 `0xffff_ff01_0100`、无 `-bios` 显式报错）、`bootrom-image` 精确 64 KiB、ELF 允许 ROM+SRAM 段且 `e_entry` 在映射区；任意 cfx2rd/cfx2rc ⇒ `CFXREG`（0x84，新增直接 fault 通道）、非 semihosting `trap`/`escape` ⇒ `ILLI`（0x88）、`addr[47:42]=0`/cfxha 63 越界 ⇒ `CFXMEM`（0x81）；semihosting 与 cfxha 无关、IP+=4。补丁 **4 份改**（`cpu.h`/`cpu.c`/`helper.c`/`dadao-machine.c`），`make_patch.py` 重导出；驱动侧最小连带：Makefile Tiny 目标环境行 + `machine-profiles.yaml` tiny `qemu_*` 回填 + trampoline 跳 profile entry + `check_interface` 按 profile 前缀核对。证据 （运行期证据已清理，未归档；结果见该任务完成区）（几何由 spec 派生、raw/ELF/ROM/cfx/semihosting、inst smoke/embench/picolibc、注入→FAIL→`cp`+md5→回绿）。
  - 执行者：engineer

- **2026-11-03 `QEMU-080t`**
  - 摘要：**Kaiwu-Node 系统机（spec/Kaiwu §1.1/§6）**：`dadao-m1` 的运行时 profile 由 `legacy|tiny` 改为 `tiny|node`（缺省 `tiny`，移除 `legacy`；`DADAO_TEST_PROFILE` 回退保留）。Node：BootROM 4 MiB `0xffff_ffc0_0000`（`bootrom-image` 精确 4 MiB；`-bios` 仍为 64 KiB 复位窗口）、复位 `0xffff_ffff_0000`、PA RAM 2 GiB `[0, 2 GiB)`、hmon/smon/pmem SRAM 与完整 cfx/PTW；canonical `DADAO_*` 宏改为 Node 口径（2 GiB 用 `2048ULL * 1024 * 1024` 避免 int 溢出）。power→hmon→测试本体（hypv）真实闭环：hmon 建 4×512 MiB identity 超页（`SPF=0xFF`、PPN `i`）、`PTBR=0`、`ptw_enable=1`，`-kernel` raw 装 `0x10_0000`；ELF `PT_LOAD` 按 VA=PA 落 PA RAM（越界装载期拒绝），`e_entry` 不覆盖复位。补丁 **4 份改**（`cpu.h`/`cpu.c`/`helper.c`/`dadao-machine.c`），`make_patch.py` 重导出。驱动侧最小连带：Makefile inst/arch 目标改用 `profile=node` + 4 MiB `bootrom-image`、`machine-profiles.yaml` Node `qemu_*` 回填、`check_interface` Node 断言转 PASS；`tests/shared/bootrom/step5/power.S` 两处共享例程调用目标修正为 `RESET_PC + 0x2000/0x2400`（用户 2026-11-03 授权，启动链此前无法真实执行）。证据 （运行期证据已清理，未归档；结果见该任务完成区）（32 检查：几何/接口、BootROM 尺寸、boot 链/PTW、ELF、arch semihosting）+ `--inject`（RAM 1 GiB / hmon `SPF=0x00` → FAIL → `cp`+md5 还原 → 回绿）。
  - 执行者：engineer

- **2026-11-03 `QEMU-082t`**
  - 摘要：**cg7 `power` 空间描述符按活动 profile 派生（spec/Kaiwu §1.1）**：`dadao_cg7_space_reg()` 新增 `const DadaoProfile *` 参数（调用点传 `DADAO_PROFILE(env)`），`power[1] = rom_base & ((1<<42)-1)`、`power[2] = rom_size`，`desc=0x5`/`attr=0x5` 不变；退役 M1–M3 遗留的 256 KiB 常量（`0x3FFFFFC0000`/`0x40000`）与「power 256 KiB」注释。Node 实测 `0x5 / 0x3ff_ffc0_0000 / 0x40_0000 / 0x5`（`start+size == 2^42`）；Tiny 由 `!cfx_enabled` 前置门挡在 `cg == 7` 之前，cg7 不可达（探针退出码 `0x84` CFXREG）。`smon/hmon/pmem` 常量与 `space[1..15]=0` 不变。补丁 **1 份改**（`helper.c`），`make_patch.py` 重导出（1 written / 62 unchanged）。证据 （运行期证据已清理，未归档；结果见该任务完成区）（integ049t 12/12、Tiny cfx_power 探针、check-interface/arch-smoke/inst/L1/L2）+ 注入（`power[1]`↔`power[2]` 旧值 → `space_power` FAIL → `cp`+md5 还原 → 12/12 回绿）。
  - 执行者：engineer

- **2026-11-05 `QEMU-083t`**
  - 摘要：**`CFXREG` 异常目标改为当前运行模式 monitor（DADAO-12 §5.2；ISS-342）**：`helper_cfx2rd`/`helper_cfx2rc` 的 10 处 `cfx_raise(..., DADAO_CAUSE_CFXREG, cfxha, ...)` 改为 `env->inner_run_mode`（U/J/S/H ⇒ `cfx_umon`/`cfx_jmon`/`cfx_smon`/`cfx_hmon`），覆盖 cg/rc 越界、`rc >= scratch_regs_num`、只读寄存器写、cg7 写与 cg15 保留 rc；合法路径与其它异常（`CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`）目标不变。补丁 **1 份改**（`helper.c`），`make_patch.py` 重导出（1 written / 62 unchanged）。随语义迁移的最少测试资产修正：`tests/arch/umon/m5_perm_badcombo_cfxreg.s` 删除自装 `cfx_umon` 向量规避、改读 hmon fault-record（退出码/原因期望不变）；`tools/testcases/arch/{min_rom_probe_044t,045t,integ040t,integ042t,integ050t}` 的 CFXREG 用例改从 `cfx_hmon` 取 cause 帧（`integ042t` 的 pmem 入口改用非屏蔽 `trap cfx_pmem` 并在 trap 帧内恢复 hmon 全局源掩码），断言强度不放宽。
  - 执行者：engineer

- **2026-11-05 `INTEG-054t`**
  - 摘要：**删除 5 个无效屏蔽寄存器的实现（SPEC-188t）**：`cpu.h` 移除 `DADAOCfxModeRegs.{switch_cfx_mask,excp_cause_mask}`、`DADAOCfxRegs.{prev_cfx_mask,cause_nonmaskable}` 与 `inner_cfx_mask`；`cpu.c` 复位值与 `dump_state` 同步移除（不再打印 `CFXMASK`/`PREVMASK`/`NONMASK`/`SWMASK`/`CAUSEMASK`）；`helper.c` 的 `cfx_mode_reg`/`cfx_reg_ptr` 不再解析 `cg0-3 rc9/rc11`、`cg5 rc1/rc63`（访问 ⇒ `CFXREG`），`cfx_enter` 删除 inner/cause 掩码层（同步异常不可屏蔽，异步只按 `cfx_intr_mask`+`global_cfx_intr_mask` 两级来源过滤），`escape` 不再恢复 cfx 屏蔽状态、保留 trap 保存的 `global_cfx_intr_mask` 恢复。补丁 3 份改（`cpu.h`/`cpu.c`/`helper.c`），`make_patch.py` 重导出（3 written / 60 unchanged）。验收：`build-qemu`/`install-host`、`check-inst`、`check-arch`、`check-source-state`/`check-patch-tree`、L1；`matrix-M11` node/arch 无回归。
  - 执行者：engineer

- **2026-11-05 `INTEG-055t`**
  - 摘要：**退出码实现迁移到 `spec/Kaiwu §7.1` 三段式（QEMU 侧）**：删除 `DADAO_EXIT_CFXMEM/CFXREG/UNMAPPED/ILLI/...` 旧码与 `0x80 | cause_bit` 派生，新增 `DADAO_EXIT_CFX(cfxHA)` 与 `DADAO_EXIT_MONITOR(mode,index)`；`dadao_excp_to_exit_code()` 改按 `env->inner_run_mode` 编 monitor 段（`UNMAPPED` 归 `CFXMEM` index 1），guest SYS_EXIT 传播不变；`cpu.h` 加 §7.1 公式编译期自检。**页表异常改投当前 monitor（DADAO-12 §2.2.6/§5.2）**：`dadao_tlb_check`/`dadao_ptw_walk` 的缺页/碎片/A-D 回写失败统一编 `CFXMEM`、HSJU/R/W/X 编 `CFXPERM`，删除 `PTWERR` 与页级 one-hot cause；`DADAO_EXCP_PTW_FAULT` 由 `cfx_enter(...cfx_ptw...)` 改为进入 `env->inner_run_mode` 的 monitor，A/D 回写失败的 `cause_info` 仍为 PTE PA。补丁 3 份改（`cpu.h`/`cpu.c`/`helper.c`），`make_patch.py` 重导出。
  - 执行者：engineer

- **2026-11-06 `QEMU-084t`**
  - 摘要：**guest `RLIMIT_AS`/`RLIMIT_DATA`/`RLIMIT_STACK` 记账（ISS-343）**：此前 `setrlimit`/`prlimit64` 对这三项直接返回成功而不记录（透传给宿主会限制 QEMU 自身分配），guest 永远读回 `RLIM_INFINITY` 且 `mmap`/`brk` 不受限。新增 `linux-user/mmap.c` 内的 guest 限额存储（仅 `TARGET_DADAO`）+ `guest_rlimit_check_mmap()`：`target_mmap()` 在 mmap 锁内按 `walk_memory_regions()` 现读页表现算总量，`RLIMIT_AS` 管总 VA、`RLIMIT_DATA` 管可写私有映射（含 `do_brk()` 经 `target_mmap()` 的堆增长，并按内核 `may_expand_vm()` 的 cur=0/max 未动「Valgrind workaround」放行），`MAP_GROWSDOWN` 映射按 `RLIMIT_STACK` 限长，超限 ⇒ `ENOMEM`；`syscall.c` 的 `prlimit64`/`setrlimit`/`getrlimit` 对这三项改读写 guest 值（`getrlimit` 返回所设值，`prlimit64` 只支持 self，其它 pid ⇒ `ESRCH`），其余资源与既有语义不变。`user-mmap.h` 增三接口声明。未设限的 `RLIMIT_STACK` 报告 loader 实际映射的主栈大小（`max(guest_stack_size, 32 页)`，默认 8 MiB）而非 `RLIM_INFINITY`，使报告值与真实约束一致（宿主 `RLIMIT_STACK` 不参与：宿主 unlimited 时区域仍是 8 MiB，宿主更小时区域也不缩）。补丁 3 份：2 新增（`linux-user/mmap.c.patch`、`linux-user/user-mmap.h.patch`）+ 1 改（`linux-user/syscall.c.patch`），`make_patch.py` 重导出（65 份）。
  - 执行者：engineer

- **2026-11-06 `INTEG-058t`**
  - 摘要：**转换指令舍入编码三分（ADR-0050 / SPEC-194t）落地**：8 条 `f2i`、6 条不精确 `i2f` 与 `fo2ft` 的 immu6 改为六档 one-hot（`0x01`/`0x02`/`0x04`/`0x08`/`0x10`/`0x20`），`0x20` 读 `rf0[33:32]`、静态档不受 rf0 影响；`ft2fo`/`it2fo`/`ut2fo` 校验 SBZ=0；18 条转换改单寄存器、去掉旧计数循环与 `mreg_*` 校验；复制类 `ft2ft`/`fo2fo` 仍按 1–63 计数与重叠规则。`helper_fp_cvt_f2i` 改用按方向舍入的 softfloat 入口并按 D5 合并 NX（有限不精确）与 NV（NaN/Inf/越界饱和、不置 NX）；`fo2ft` 溢出按契约恒返 ±Inf + OF|NX。补丁 2 份改（`helper.c`/`trans_fp.c.inc`），`make_patch.py` 重导出。
  - 执行者：engineer

- **2026-11-07 `GEM5-029t`**
  - 摘要：**`sigaltstack(2)` 的 `SS_AUTODISARM` 支持（用户裁定 2026-11-07：gem5 按 Linux 实现，同时给 QEMU 补 patch）**。`linux-user/signal.c`：`on_sig_stack()` 在 `sas_ss_flags` 带 `SS_AUTODISARM` 时按 Linux 返回 0；`target_save_altstack()` 回写 `sas_ss_flags(sp) | (ss_flags & SS_FLAG_BITS)`；`target_restore_altstack()` 改为按 `ss_flags & ~SS_FLAG_BITS` 判模式（接受 `SS_AUTODISARM`，仅未知位 `EINVAL`）并记录 `ss_flags`。`linux-user/dadao/signal.c`：`setup_ucontext()` 保存 `uc_stack` 后按 `sas_ss_reset` 语义禁用自动拆除的备用栈，由 sigreturn 从帧恢复。此前 QEMU 对 `SS_AUTODISARM` 返回 `EINVAL`，与 Linux 不符，使双引擎探针无法以 QEMU 为 oracle。
  - 执行者：engineer

- **2026-11-08 `QEMU-085t`**
  - 摘要：**`target_mremap()` 的增长按 guest `RLIMIT_AS` 记账（ISS-351，对齐 Linux `may_expand_vm`）**。`QEMU-084t` 只在 `target_mmap()` 检查限额，`mremap` 增长（GEM5-030t 实测 4 MiB→100 MiB）在 QEMU 上仍成功，而内核在 `check_prep_vma()` 对 `MREMAP_FIXED`、搬移与原地三种路径都调 `may_expand_vm()` 收费。`linux-user/mmap.c` 新增 `guest_rlimit_check_remap_grow()`（复用同一 `guest_rlim[]` 存储与 `walk_memory_regions()` 现读页表总量，不另立状态），`target_mremap()` 在 mmap 锁内对 `new_size > old_size` 只计增长量（两长度按页对齐后相减）并检查 `RLIMIT_AS`，超限 ⇒ `TARGET_ENOMEM`；收缩、等长与 `MREMAP_DONTUNMAP` 语义不变，目标与源重叠的 `MREMAP_FIXED` 仍交宿主回 `EINVAL`（不让限额检查抢错误的优先级）。RLIMIT_DATA 半边未重复：页表只记可写性、`target_mremap` 拿不到私有/共享请求，属既有近似；`old_size==0` 的复制形态内核按整段 `new_len` 收费，但 qemu-user 无从判共享与否，保持原样——两处均写进补丁注释。补丁 **1 份改**，`make_patch.py` 重导出（1 written / 65 unchanged，共 66 份）。双引擎探针（限内增长成功 / 超限 `ENOMEM` / 非增长完好 / `MREMAP_FIXED` 同两态）43 条断言 QEMU 与 gem5 SE 逐行一致；反例去掉新增检查 ⇒ 两组增长断言 4 条 FAIL，`cp`+md5 还原重建回绿。
  - 执行者：engineer

## M12

- **2026-11-08 `m12-qemu-001`**
  - 摘要：**拆两台机器 `kaiwu-tiny` / `kaiwu-vast`（M12；`spec/Kaiwu §1`）**：`hw/dadao/dadao-machine.c` 由「单机型 + 运行期 `profile=`」改为按机器类型固定 `DadaoProfile`，注册 `kaiwu-tiny-machine` / `kaiwu-vast-machine` / `dadao-m1-machine` 三个 QOM 类型（同一 `DadaoMachineState`/`DadaoMachineClass`，`class_data` 携带 profile）；`profile` 属性只挂在过渡别名 `dadao-m1` 上，`kaiwu-tiny`/`kaiwu-vast` 传 `profile=` 直接报 property not found（双入口移除）。`cpu.{h,c}` 的 `dadao_profile_node` → `dadao_profile_vast`（`.name = "vast"`）、`DADAO_NODE_*` 几何宏 → `DADAO_VAST_*`；canonical `DADAO_RAM_*`/`DADAO_ROM_*`/`DADAO_RESET_PC` 口径不变（仍是 Vast 值）。兼容别名（`deprecated since M12`，仅到 `m12-integ-001`）：`dadao-m1` == tiny，`profile=tiny|vast` 与旧值 `node`→vast，`DADAO_TEST_PROFILE` 回退保留；`-M help` 的描述文本标 `(deprecated)`；**未**使用 `mc->deprecation_reason`（启动警告会污染 stderr，被 `diff_ir_lli` 误判为装载拒绝）。补丁 3 份改，`git apply` 重生成（hunk 计数与 index 由 `git diff --cached` 产出）。文档：`README.md` 增「机器（machine）」节。
  - 执行者：engineer

- **2026-11-09 `m12-integ-001`**
  - 摘要：**移除过渡别名 `dadao-m1` 与 `profile=node`**。`hw/dadao/dadao-machine.c` 删除 `dadao-m1` 机器类型、`profile` 属性、`profile=node`→vast 映射与 `DADAO_TEST_PROFILE` 回退；`DadaoMachineState`/`DadaoMachineDesc`/`DadaoMachineClass` 去掉 `profile`/`legacy_alias` 字段，`dadao_machine_select_profile()` 删除，profile 直接取 `class_data`；错误信息前缀 `dadao-m1:` 改为 `dadao:`，`-M dadao-m1` 现报 machine not found（不再静默映射）。`cpu.{h,c}` 注释同步。补丁 3 份改（hunk 计数由 `git diff <base>` 产出）。`README.md` 记录别名移除。
  - 执行者：engineer

## M13

- **2026-11-11 `m13-qemu-003`**
  - 摘要：**比较族标志对齐 IEEE 754-2019 §5.6.1（用户裁定「任何无序都置」）**。`target/dadao/insn_trans/trans_fp.c.inc` 的 `gen_fp_cmp()` 增 `signal_nv` 参数：`ftscmp`/`foscmp` 在结果为 unordered（任一操作数为 qNaN 或 sNaN）时把 `unord`（1/0）OR 进 `rf0` 的 NV 位（经 `store_rf()` 写入，只读 qNaN/SBZ 位保持）；`ftqcmp`/`foqcmp` 仍不置任何标志；比较结果（quiet→qNaN、signaling→sNaN、有→`-1/0/1`）与其它 FP 标志路径不变。补丁 1 份改。
  - 执行者：engineer

- **2026-11-10 `m13-qemu-002`**
  - 摘要：**Tiny 对齐 hmon 装载契约（`spec/Kaiwu` 0.4.4-rc §6/§6.1/§6.2、`DADAO-13` rc10、`Kaiwu §2` switch_run_mode）**。`hw/dadao/dadao-machine.c`：Tiny 的契约路径改为 `bootrom-image` 固定 64 KiB 固件 + 应用（真实执行 power → hmon → escape → `0xffff_ff01_0100`）；ELF PT_LOAD 只允许 SRAM（BootROM/hmon SRAM 下发即具名报错）、Tiny `e_entry` 必须等于固定入口；`-bios` 的 64 KiB 文件按同一固定固件走契约路径，≤4096 B 保留为 pre-contract 的平坦 trampoline 窗口（raw `-kernel`），中间尺寸具名报错。`cpu.{h,c}`：Tiny 关闭 `rom_elf_segments`/`mon_elf_segments`、增 `bootrom_required`/`fixed_kernel_entry`/`switch_run_mode_write_ignored`；`cg3 rc10` 初值改为该 cfx 内部 SRAM 起始（hmon `0x0fff_0000_0000`）。`helper.c`：`rc10` 写入掩掉低 2 位；Tiny `switch_run_mode` 写入忽略、保存值保持 3。测试侧：`tools/testcases/lib/gen_trampoline.py` 的 legacy trampoline 先把 hmon 向量指到不可达地址，保持 44/44 的机器 fault 退出码口径；lit/test-elf/picolibc/embench 的 Tiny ELF 应用改用 SRAM 应用链接脚本 + `bootrom-image`。
  - 执行者：engineer

- **2026-11-10 `m13-qemu-001`**
  - 摘要：**Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`（`spec/Kaiwu` 0.4.2-rc §1.1/§2/§4.4/§6）**。`cpu.{h,c}`：profile 由 `cfx_enabled` 改为 `cfx_impl_mask`（Tiny `{3,63}`、Vast 原 9 项）+ `hmon_sram`/`smon_sram` 拆分 + `mon_elf_segments` + `unimpl_cfx_trap_illi` + `sync_exc_monitor_entry`；`cfx_idx()` 按 profile 过滤（未实现的 cfx 无寄存器行/掩码/向量）。`hw/dadao/dadao-machine.c`：Tiny 增 64 KiB hmon SRAM（`0x0fff_0000_0000`，cfxha 3；CPU 仍经 `tlb_fill` 的 host 基址访问）与**装载别名**（ELF PT_LOAD 直装 hmon SRAM，R13-A），`dadao_mapped_regions()` 增第三区。`helper.c`：同步异常统一走 `dadao_sync_enter()`（cause id/info 表：`ILLI`/`UNDI`/`CFXMEM`/`CFXREG`/`CFXPERM`/`MALIGN`/`IALIGN`/`RASOF`/`RASUF`），**向量不可达时回退机器 fault 退出码**（`Kaiwu §7.1`，防 CFXMEM 递归）；Tiny `cfx2rd`/`cfx2rc`/`trap` 到未实现 cfx ⇒ `ILLI`、寄存器访问 ⇒ `CFXREG`；`escape` 仅在有 `trap` 保存的 `global_cfx_intr_mask` 时恢复；Tiny 运行模式锁 `hypv`。`raise_exception` helper 增 `cause_info` 参数（指令编码/访存地址）。`translate.c`：**IALIGN 在取指前检测**（`IP[1:0] != 00`），IP 停留非法地址、不写回 nextIp；`tlb_fill` 对取指同检（未映射且非对齐时 IALIGN 优先于 CFXMEM）。Vast 的 `ILLI`/`UNDI`/`CFXMEM`/`MALIGN`/`IALIGN`/`RAS*` 仍按 staged 机器 fault 映射（旧探针 oracle 依赖，规格偏差已登记任务书）。补丁 **7 份改**，`make_patch.py` 重导出（7 written / 59 unchanged，共 66 份）。
  - 执行者：engineer

- **2026-11-12 `m13-qemu-005`**
  - 摘要：**`fo2ft` 溢出按 IEEE 754-2019 §7.4 / `SimRISC-07 §1.4` 定稿按舍入方向分派**。`target/dadao/helper.c`：`conv_select_mode()` 改为返回解析后的 `FloatRoundMode`（`0x20` 动态档已按 `rf0[33:32]` 展开），`helper_fp_cvt_ff()` 的 `fo2ft` 溢出路径改用新增 `fo2ft_overflow_result(mode, neg)`——RNE/RNA、RUP 正溢出、RDN 负溢出 ⇒ `±Inf`；RTZ 双向、RUP 负溢出、RDN 正溢出 ⇒ `±ft_max`（`0x7F7F_FFFF`/`0xFF7F_FFFF`），符号取精确结果（有限源）的符号。`OF|NX` 仍由 softfloat 溢出路径置位并经 `fp_status_commit()` 累积；`ft2fo` 精确转换与其它 FP 路径不变。补丁 1 份改。
  - 执行者：engineer

- **2026-11-12 `m13-qemu-004`**
  - 摘要：**quiet compare 遇 sNaN 置 `NV`（IEEE 754-2019 §5.11；用户裁定 2026-11-12「改为置 NV（跟 IEEE）」）**。`target/dadao/insn_trans/trans_fp.c.inc`：新增 `fp_is_snan()`（NaN 且尾数静默位为 0）；`gen_fp_cmp()` 的 `signal_nv` 改为 `nv_rule` 二档——`FP_CMP_NV_UNORDERED`（signaling compare，任何无序置，口径不变）/ `FP_CMP_NV_SNAN`（quiet compare，**仅任一操作数为 sNaN 时置**，qNaN 不置）；`ftqcmp`/`foqcmp` 改传后者，NV 仍经 `store_rf()` 写 `rf0` 的 bit0（只读 qNaN/SBZ 位保持）。比较结果值（quiet→qNaN、signaling→sNaN、有序→`−1/0/1`）与其它 FP 标志路径不变。补丁 1 份改。
  - 执行者：engineer

- **2026-11-13 `m13-qemu-006`**
  - 摘要：**`ldm` 地址寄存器落入传送范围 ⇒ ILLI（`mreg_range_addr_overlap`；用户裁定「不允许重叠，改spec」+ 补充「stm 应该是允许这种重叠的」）**。`target/dadao/insn_trans/trans_mem.c.inc`：新增静态判定 `mreg_addr_in_range()`（`addr ∈ [start, start+immu6)`）；RD 形式 7 条 `ldm`（`ldm.ub/uw/ut/sb/sw/st/o` 的 rd 变体）在既有 `immu6=0`/范围检查同处增 `rdhc` 判定，RB 形式 `ldm.o` 增 `rbhb` 判定；命中即 `gen_exception_illegal()`，任何元素都不产生效果（不发访存、不写寄存器）。`stm` 不加检查（只读传送范围、不写寄存器 ⇒ 允许重叠）；RA/RF 形式结构上不可能重叠，不适用。补丁 1 份改。
  - 执行者：engineer

- **2026-11-13 `m13-qemu-009`**
  - 摘要：**`rootn(±0, 2) = +0` 与「结果 NaN 一律 canonical」**（`SimRISC-07 §2.2` / `§异常与标志`、`contract-fp.md §1`；用户裁定 R1/R2）。`target/dadao/helper.c` 两处：① `fp_status_init()` 增 `set_default_nan_mode(1, &st)`——softfloat 的 `partsN(return_nan)` / `pick_nan` / `pick_nan_muladd` 在任何 payload 传播规则**之前**短路返回 `default_nan`，故算术、开方、取余、scaleB 与 f2f 转换一次覆盖，结果统一为 FCSR 的 qNaN 位型 `0x7FC0_0000` / `0x7FF8_0000_0000_0000`（符号 0、payload 0），sNaN 仍置 NV（早于短路）；原 `float_2nan_prop_ab`（为对齐 x86_64 主机而设）降级为**仅在 default-NaN 关闭时**防 `g_assert_not_reached` 的兜底（ISS-195），不再定义 ISA 结果；`set_float_default_nan_pattern(0b01000000)` 不变。② `helper_fp_root()` 零量值（`±0`）短路返回 `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`），不置标志、不进 softfloat；其余输入仍为 squareRoot 语义（负数 ⇒ NV + canonical qNaN）。`roundint`/`minmax`/`fma` 三处 per-op `set_default_nan_mode(1,&st)` 变冗余，保留（最小改动）。`tests/inst` 的既有非 canonical qNaN pin（`divrem.yaml[23]`）随之转红，由 `m13-testcases-032` 收口。补丁 1 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-007`**
  - 摘要：**`ld.t`/`ldm.t` 写 `rf0` 不再改写只读位（争议 6 裁定 A）**。`target/dadao/insn_trans/trans_fp.c.inc` 删掉 `ld.t`/`ldm.t` 目的写的 rf0 专用旁路 `store_rf_tetra_dst()`（原实现把装入值的低 32 位整体写入，覆盖只读 `[31:22]` ft qNaN 与 SBZ `[21:5]`；去掉旁路后该包装与非零 rf 无差别，一并删除，两个调用点直接走 `store_rf()`）：`RF0_WRITE_MASK` 只放行 `[33:32]`/`[4:0]`，`[63:51]`/`[31:22]` 只读 qNaN 与 SBZ 写无效、保持原值（`spec/SimRISC-00 §2.3.1`、`SimRISC-01 §存取RF寄存器` 注、`contract-fp §1`）。tetra 装入仍按既有语义符号扩展到 64 位（与 chipyard `memLdElem` 一致），故 `ld.t rf0 ← 0xFFFF_FFFF` 读回 `0x7FF8_0003_7FC0_001F`。`ld.o`/`ldm.o`/`rd2rf`/`set.w`/FP helper 路径不变（原本就经 `store_rf()`/掩码 OR）。补丁 1 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-010`**
  - 摘要：**`ext.uo`/`ext.so` orrr 的 `hd` 取 `rdHD[5:0]`，删运行时 ILLI 路径**（用户裁定 2026-11-13，`ISS-422`：`rdHD` 高位忽略、不抛 ILLI）。`target/dadao/insn_trans/trans_extend.c.inc`：`trans_ext_{uo,so}_orrr_rd` 删除 `gen_runtime_illi_check(ctx, rdhd, 63)` 及其注释，保留既有 `tcg_gen_andi_i64(pos, rdhd, 0x3F)`，头注释改述 `hd = rdHD[5:0]`（chipyard `WumingDecoder.orrrShift` 即把该值送 6 位 `shamt` 端口）。`target/dadao/translate.c`：`gen_runtime_illi_check()` 随之无调用者、删除；其唯一被调用者 `gen_raise_exception_illi()` 亦无调用者，同步删除（避免新增 `-Wunused-function`）。orri 分支的 `a->hd > 63` 检查保留（`immu6` 为 6 位字段 ⇒ 不可达，留作防御、最小改动）。语义：`rdHD=64 ≡ 0`、`67 ≡ 3`、`2^64−1 ≡ 63`、`63 ≡ 63`；`ext.so` 仍按 `rdhc[hd]` 符号扩展。补丁 2 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-012`**
  - 摘要：**`ra0` 写口丢弃 SBZ `[63:54]`（`ISS-426` 的 QEMU 侧）**。`target/dadao/helper.c` 的 `helper_ra_store()`：逻辑寄存器 0（`ra0`，物理 0）的写入按 `RA0_WRITE_MASK = 0x003FFFFFFFFFFFFF` 掩码，只落 `RACNT[53:48]`/`MRPTR[47:0]`，`[63:54]` 写无效、读回恒 0（`spec/SimRISC-00 §2.4`）；`ra1`–`ra63` 的 `[63:48]` 是 16 位递归计数，不掩码。`helper_ras_push`/`helper_ras_pop` 的 RACNT/MRPTR 头更新路径未改动（逐字节不变）。补丁 1 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-013`**
  - 摘要：**单精写入宽度：`ld.t`/`ldm.t` 不扩展 + 以 ft 寄存器为目的的指令只写低 32 位**（用户 2026-11-14 裁定；`spec/SimRISC-01 §4` 注、`SimRISC-07 §1.3`、`contract-fp §1`）。`target/dadao/translate.c` 新增 `store_rf_tetra()`（低 32 位合并、高 32 位保持；rf0 仍经 `RF0_WRITE_MASK`，只有 `[4:0]` 生效）；`target/dadao/insn_trans/trans_fp.c.inc`：`ld.t`/`ldm.t` 改 `MO_BEUL` 无符号 32 位装载 + tetra 写；ft 算术（`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb`）、`ftroot`、`ftrnd`、`ftmin`/`ftmax`、`ftfma`、`fo2ft`、`it2ft/io2ft/ut2ft/uo2ft`、`ft2ft`（含连续搬移）、`ftsgnj`/`ftsgnn`（ft 窄写，追加裁定 `9cff1daa`）全部改 `store_rf_tetra()`；`fo2fo`、跨组复制 `rd2rf`/`rf2rd`、`ld.o`/`ldm.o`、`st.*`、`cs.*-rf` 与 `fosgnj`/`fosgnn`（fo，整 64 位）仍 64 位。`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`（原 `0x7FF8_0003_7FC0_001F`）；`ft2ft` 目的高半保持写前值。补丁 2 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-014`**
  - 摘要：**`sc` 保留粒度改为「精确地址 + 访问宽度」，删整字值比较（`ISS-435` 用户裁定「严格按spec来」；`spec/SimRISC-12 §1`「保留机制」、`contract-isa §14.2`）**。`target/dadao/cpu.h`：保留记录由 `{lock_addr(8 B 对齐字), lock_val(整字观测值)}` 改为 `{lock_addr(精确地址), lock_width(1/2/4/8)}`，删 `lock_val`；`target/dadao/translate.c`：`gen_lr` 按宽度大端装载（`lrsc_memop()`）并记 `(addr, width)` 键，`gen_sc` 仅当 `lock_valid && lock_addr == addr && lock_width == width` 时按宽度写入并 `rdHB=0`，否则不写并 `rdHB=1`；删 `gen_be_shift`/`be_width_mask` 与整字 CAS 值比较；成败都清 `lock_valid`。`cpu.c` 复位删 `lock_val` 初始化、`helper.c` 的异常/中断清除点注释同步。同 hart 普通 store、同字异址、同址不同宽度均不再使 `sc` 失败；`rdHB` 方向与 MALIGN 检查不变。补丁 4 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-011`**
  - 摘要：**Tiny 的 `-bios` 收紧为固定固件，删除 ≤4096 B 的 raw trampoline 窗口**（`spec/Kaiwu §6`；用户裁定 2026-11-13「绑 `m12-chipyard-019` 收紧」）。`hw/dadao/dadao-machine.c`：新增 `dadao_check_bios_firmware_size()`——`bootrom_required`（Tiny）profile 下 `-bios` 镜像必须**恰好** `rom_size`（64 KiB，与 `bootrom-image` 同一固定固件），任意其它尺寸（含空文件、4 KiB/8 KiB 与中间尺寸）在写入 BootROM 窗口**之前**按名拒绝并 `exit(1)`，报出实际字节数、64 KiB 规则与 `spec/Kaiwu §6` 出处，不做截断/降级；`dadao_machine_init()` 的 Tiny 分支删掉「`-bios` 小文件 ⇒ flat trampoline + raw `-kernel`」旁路，`-bios` 一律走「固定固件 + 应用（ELF 或 raw）」契约路径，无固件的应用 ⇒ 具名报错；Path B（flat `-bios` + raw `-kernel`）只剩 Vast 的 64 KiB reset window。文件头与函数注释同步改述。补丁 1 份改。
  - 执行者：engineer

- **2026-11-14 `m13-qemu-015`**
  - 摘要：**tetra 写入 `rf0` 保持 `[33:32]`（零扩展后再整掩码的缺陷）**。`target/dadao/translate.c`：新增 `RF0_WRITE_MASK_TETRA = 0x1F`（32 位写入宽度内只有 `[4:0]` 可达）与 `store_rf_masked(n, val, mask)`（`store_rf()` 的 rf0 分支改为调用它，行为不变）；`store_rf_tetra()` 的 rf0 分支由「零扩展低 32 位交给 `RF0_WRITE_MASK`」改为 `store_rf_masked(0, low, RF0_WRITE_MASK_TETRA)`——原实现把 `[33:32]` 一并清零（用户 2026-11-14 裁定：`ld.t`/`ldm.t` 只写低 32 位，`[33:32]` 在写入宽度之外 ⇒ 保持；`spec/SimRISC-01 §4` 注、`contract-fp §1`）。`ld.t rf0 ← 0xFFFF_FFFF` 由 `0x7FF8_0000_7FC0_0000` 改为 `0x7FF8_0000_7FC0_001F`；`ld.o`/`ldm.o`（octa，`[33:32]` 由值给出）、`set.w`、`rd2rf`、`ld.t rf5` 高半与其它 ft 结果族（本来就是低 32 位值）逐字节不变。`trans_fp.c.inc` 头注释同步改述（tetra 只 `[4:0]`；octa `[33:32]`+`[4:0]`）。补丁 2 份改。
  - 执行者：engineer

- **2026-11-15 `m13-qemu-016`**
  - 摘要：**rf 组块复制改为 `rf2rf`、删 `ft2ft`/`fo2fo`（编码不兼容，`m13-spec-010`）**。`target/dadao/insn.decode` 由 `contracts/opcodes.yaml` 重生成（263 条）：删 `ft2ft_orri_rf`（`01000100000010`）与 `fo2fo_orri_rf`（`01000100001010`）⇒ 两者成为保留编码（执行 ⇒ UNDI），新增 `rf2rf_orri_rf`（`OPC-octa` `111-100`、`mask 0xFFFC0000`/`value 0x40F00000`）。`target/dadao/insn_trans/trans_fp.c.inc`：删 `trans_ft2ft_orri_rf`/`trans_fo2fo_orri_rf` 与 `gen_convert_ff()` 的同格式复制分支（`move`/`move_ft` 参数随之删除，`convert_ff` 只剩 `ft2fo`/`fo2ft`）；新增 `trans_rf2rf_orri_rf`——`fp_check_dst_rf0`（目的范围含 `rf0` ⇒ ILLI，`hb == 0` 即覆盖任意 `immu6`）、`fp_check_mreg` 两侧起止（`immu6` = 0 / 起始 + `immu6` > 64 ⇒ ILLI）、`fp_check_mreg_overlap`（任意重叠含完全重合 ⇒ ILLI，全部在处理任何元素之前判定），逐元素 `load_rf` → `store_rf` 整 64 位逐位搬移（源 `rf0` 合法、读完整 64 位；不换算、不舍入、不置标志）。`translate.c` 仅改 `store_rf_tetra()` 注释（无功能改动：`trans_fp.c.inc` 已是整文件 include）。运行期实测（`kaiwu-tiny`，`run_asm_suite`）：链例 7 检查点全过（`immu6=3` 三元素 64 位、窗口顶端 60+4、最高号 rf63、最大可行个数 31、相邻窗口、源 `rf0` 读出 `0x7FF8_0000_7FC0_0000`），7 条 ILLI 全中（`immu6=0`/目的越界/源越界/完全重合/部分重合/目的含 `rf0`（`{rf0}` 与 `{rf0:rf1}`）），旧 `ft2ft`/`fo2fo` 编码实测 UNDI（0xF9）。补丁 3 份改。
  - 执行者：engineer

## M14

- **2026-11-14 `m14-qemu-001`**
  - 摘要：**Vast K1 启动链：宿主 K1 装载 + boot info，hmon→smon 建首张页表并以 VA 入口进 `supv`（`spec/Kaiwu §6.3`、`ADR-0051 D2/D4/D5/D6`）**。`hw/dadao/dadao-machine.c` 新增 K1 装载路径（仅 `kaiwu-vast` 的 `bootrom-image + -kernel`）：ELF 按 §6.3.2 的 7 条规则逐条具名拒绝（`ELF-FORMAT`/`ELF-PT-LOAD`/`ELF-VA-TO-PA`（`p_paddr = p_vaddr - 2 TiB`，装载仍交上游 `load_elf` 按 `p_paddr` 放置）/`ELF-ALIGN`/`ELF-NO-OVERLAP`（先于 `ELF-RANGE` 判定，便于具名归因）/`ELF-RANGE`/`ELF-ENTRY`），raw 按 4 条规则（`RAW-BASE`/`RAW-ENTRY`/`RAW-LENGTH` 63 MiB 上限/`RAW-BSS` 由内核自清）整体装入 `kernel_base` 的 PA；通过后在 VA `0x0200_0001_0000`（PA `0x1_0000`）写 15 字段大端 boot info（`kernel_size` 现场计算，K1 无 initramfs），复位 PC 不变、不写页表页。补丁 1 份改。
  - 执行者：engineer

- **2026-11-16 `m14-infra-004`**
  - 摘要：**测试机整机名 `Kaiwu`（`ADR-0055`）随全仓改名**：补丁里 `Machine-v5*` → `Kaiwu*`、QEMU 机器串 `dadao-tiny`/`dadao-vast` → `kaiwu-tiny`/`kaiwu-vast`（无旧名别名）、`spec/Kaiwu §…` 注记同步；**只改名不改语义**（编码/几何/契约值零改动）。
  - 执行者：engineer

- **2026-11-16 `m14-qemu-006`**
  - 摘要：**Vast 同步异常路由对齐 `DADAO-12 §5.2`（删 staged 直映射，两 profile 统一进 monitor）**。`target/dadao/cpu.c`：`dadao_profile_vast.sync_exc_monitor_entry` 由 `false` 改 `true`（Tiny 原为 `true`）。`target/dadao/helper.c`：`dadao_cpu_do_interrupt` 删去 staged 分支（`dadao_excp_to_exit_code()` + `qemu_system_shutdown_request_with_code(GUEST_PANIC)` 的一路，以及 CFXPERM 的 `cfx_raise` 旁路），ILLI/UNDI/CFXMEM/CFXREG/CFXPERM/MALIGN/IALIGN/RASOF/RASUF 一律经 `dadao_sync_enter()`（存帧 → 跳 `<mode>_excp_vector`）；`CFXPERM` 的 `cause_info = cfx_perm_info` 由 `dadao_sync_cause()` 继续传递，「已在关停流程中不再进 monitor/覆盖退出码」短路保留；向量不可达仍按 `spec/Kaiwu §7.1` 落 monitor 段机器 fault；profile 关掉该开关 ⇒ 具名报错并 `exit(1)`（不再有第二条路由）。`target/dadao/cpu.h` 注释同步改述。Vast 探针 oracle 同步改为帧级期望（`cause_id`/`cause_ip`/`cause_info`/`prev_run_mode`）。补丁 3 份改。
  - 执行者：engineer

- **2026-11-16 `m14-qemu-003`**
  - 摘要：**异步源轴 mask 改按「当前运行模式 monitor」的行查询（`ISS-455` 用户裁定「按 spec 字面」；`spec/DADAO-12 §5.2` 步骤 3）**。`target/dadao/helper.c` 的 `cfx_enter()` 步骤 3：源轴由「当前 cfx（`inner_cfx_code`）的 `<mode>_cfx_intr_mask`」改为「**当前运行模式 monitor 的** `mode[monitor].cfx_intr_mask`」（supv ⇒ `cfx_smon cg2 rc4`；monitor 取 `inner_run_mode` = cfx0–3），与 `inner_cfx_code` 无关；全局轴 `cfx_<monitor>_global_cfx_intr_mask`（`cg8 rc1`）读法不变；两轴位索引仍为**来源 cfxha**。理由：`escape` 只恢复运行模式、不恢复 `inner_cfx_code`（`§5.3`），首投后当前 cfx 停在目标 cfx，「按当前 cfx 的行」会去读内核并不拥有的行（`m14-linux-007` 实测只 1 个 tick）。补丁 1 份改。
  - 执行者：engineer

- **2026-11-16 `m14-qemu-004`**
  - 摘要：**`SYS_READC`/`SYS_FLEN` 的内部取字缓冲由 VA/SP 派生改为按 PA（`ISS-452`，用户裁定「现在修，用 PA」）**。`semihosting/arm-compat-semi.c`：新增 target 钩子 `common_semi_scratch_addr(cs, size, &addr)`（弱默认 = 上游原式 `common_semi_stack_bottom(cs) - size`，逐字节不变；成功才写 `*addr`），`TARGET_SYS_READC` 的取字槽（1 B）、`common_semi_readc_cb` 的读回、`TARGET_SYS_FLEN` 的 `common_semi_flen_buf`（64 B gdb_stat 块）与 `common_semi_flen_fstat_cb` 的读回一律改经该钩子；READC 钩子失败 ⇒ `EFAULT`，FLEN 在钩子失败时交 `UINT64_MAX` 占位（宿主/静态文件由自身 `fstat` 定长、不读该块；需要该块的是 gdb 路径，回调再次取名并按 `EFAULT` 拒绝，故不会写到 PA 0 之类的位置）。`target/dadao/common-semi-target.c`：强定义——槽位 = `rb1 - size`；按机器地址空间模型选区（`DADAO-12 §2.2`）：`cfxha != MEM` 或 `ptw_enable == 0` 时槽位本就在物理口径（`kaiwu-tiny` 的 RAM/ROM 在 `0xffff_ff00_0000`、Vast 开 PTW 之前）⇒ 原值直用；`cfxha == MEM` 且 PTW 开时槽位是 VA ⇒ 走页表反查取**同一槽位的 PA**；既非物理口径又不可映射/不可写 ⇒ 返回 `-1`（服务显式 `EFAULT`，不写到别处）。`target/dadao/helper.c` + `cpu.h`：新增 `dadao_cpu_va_to_pa(env, va, &pa)`，复用既有 `dadao_ptw_walk()`（单 PTBR 两级走，不填 guest TLB、不改 A/D，权限要求可写）。`include/semihosting/common-semi.h`：钩子声明与取值纪律。门控：`tools/linux/check_k1.py` 新增 K15 与 `tools/linux/semihosting_readc_probe.S`（Vast+PTW 下自设内核窗口 VA 作 `rb1`，喂一个字符、要求 `rd8` 与回显都与喂入字节逐字节相等；探针自检 0xE3 槽位 VA 未映射 / 0xE5 槽位数值仍像 PA）；`check_k1 --selfcheck` 组数 15→18。补丁 5 份改。
  - 执行者：engineer

- **2026-11-17 `m14-qemu-005`**
  - 摘要：**页表异常填 `excp_cause_id` 子原因 wyde + TLB 维护按契约对齐（`contract-see §6.1/§6.1.1`、`contract-tlb` TLB-16/17/35/37/40/41/43、`ADR-0056 D3/D4`、`ADR-0041 D3.2`）**。`target/dadao/cpu.h`：新增 18 个子原因位（wyde2 `[32..39]` 专供 `CFXPERM`、wyde3 `[48..57]` 专供 `CFXMEM`）与三个字段掩码（`WYDE2`/`WYDE3`/`RESERVED16`）。`target/dadao/helper.c`：① 命中路径 `dadao_tlb_check()` 与步进路径 `dadao_ptw_walk()` **同一张表**——缺失类按「L1 P=0 SP=0→GP trap / SP=1→SP trap / L2 P=0→GP trap / SPF 或 GPF 小页位=0→PF trap」并按取指(`I`)/数据(`D`)分列，HSJU 不符按当前运行模式给 `N{U,J,S,H}PERM`，R/W/X 不符给 `NRPERM`/`NWPERM`/`NXPERM`（命中不重读 PTE，但检查项相同 ⇒ 子原因相同；原 `if (super) … else …` 两支写同一结果的死分支消除）；② `CFXMEM` 非页表类统一 `[57] NONPTW`（`dadao_sync_cause()` 的 `DADAO_EXCP_CFXMEM`/`UNMAPPED`，覆盖 ptw_enable=0 访存/取指、cfx 空间非法访问、保留 cfx、存储块故障）；③ A/D 回写失败（`clean`/`flush`/条目替换）统一 `CFXMEM + [56] ADWBFAIL` 且 `cause_info` = 该 PTE 物理地址；④ 两轴 cfx 权限拒绝（`dadao_sync_cause()` 的 `DADAO_EXCP_CFXPERM` 与 `cfx_raise_perm()`）统一 `[39] NCFXPERM`；⑤ `cfx_enter()` 存帧前新增 `dadao_cause_check()`——大类与子原因 wyde 必须配对、wyde 内恰一位、另一 wyde 与 `[31:16]` 必须为 0，违规即 `error_report` + `exit(1)`（不静默掩盖）；⑥ `dadao_tlb_control_exec()` 的「不得部分完成」落实为**条目级 + 遇错即停**（用户 2026-11-16 裁定、`contract-tlb` TLB-37）：首个失败条目保持原状并立即停止，其后条目一律不处理，一条指令最多报一处失败。既有 5 个 oracle（`049t`/`integ039t`/`integ040t`/`integ042t`/`integ048t`）的 `cause_id` 全宽相等断言改为「低 16 位掩码 + 期望子原因位 + 另一 wyde 与 `[31:16]` 为 0」的分字段断言。补丁 2 份改（`target/dadao/{cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-17 `m14-qemu-007`**
  - 摘要：**semihosting 字符串取参按 PA：补 K14 的长串（多分块）覆盖 + 收掉最后一处过时注释（`ISS-450` 收尾）**。**前提订正**：`SYS_WRITE0`/`SYS_OPEN` 的串长探测已由 `m14-qemu-002` 改为 target 钩子 `common_semi_strlen()`（dadao 强定义按 PA 逐块读，复用 `cpu_memory_rw_debug` → `dadao_cpu_translate_for_debug`），`translate_for_debug` 注释亦已于彼时订正；基线实测 `check-linux-k1` 111/111、K14 的 `SYS_WRITE0` 断言已绿 ⇒ 本任务**不重复实现**，只补覆盖与注释：`tools/linux/semihost_pa_probe.S` 增第二个 `SYS_WRITE0`（640 B 长串，起点在 256 B 块内 48 字节处、跨 3 个块；`sp_long` = `ENTRY_VA+0x1030`）；`tools/linux/check_k1.py` 的 K14 oracle 改为「前 5 段 `.ascii` 固定 + 其余拼接为长串（现场要求 > 2×256 B）」，新增断言「长串经 PA 完整取出」，逐字节全等断言纳入长串，`--selfcheck` 的 K14 翻转 3 → 4 路（总组数 18 → 19，`check-linux-k1` 断言 111 → 112）；`target/dadao/cpu.c` 的 `dadao_cpu_mmu_index()` 注释由「M1: no MMU, single index」改为与 Vast+PTW 一致的口径（单一 index 的判据 = 单地址空间 + 窗口两级走在 `dadao_cpu_tlb_fill()` 内查询 + PTBR/ptw_enable/ASID/两轴 mask/TLB 命令同笔丢弃派生翻译缓存）。补丁 1 份改（`target/dadao/cpu.c`）。
  - 执行者：engineer

## M15

- **2026-11-19 `m15-qemu-001`**
  - 摘要：**`ftscmp`/`foscmp` 无序结果由 sNaN 位型改为 canonical quiet NaN（`spec/SimRISC-07 §4`，IEEE 754-2019 §6.2.1 的 `shall`；用户 2026-11-19 授权，版本号不变）**。`target/dadao/insn_trans/trans_fp.c.inc`：两条 signaling compare 的 `nan_const` 由 `FP_FT_SNAN`/`FP_FO_SNAN` 改为 `FP_FT_QNAN`(`0x7FC0_0000`)/`FP_FO_QNAN`(`0x7FF8_0000_0000_0000`)，删除两个 sNaN 常量与相应注释；`NV` 置位规则不变（`FP_CMP_NV_UNORDERED` 仍取 `unord` 谓词、`FP_CMP_NV_SNAN` 仍取 sNaN 谓词）⇒ quiet 与 signaling 的差别只剩 `NV`。补丁 1 份改。
  - 执行者：engineer

- **2026-11-20 `m15-qemu-002`**
  - 摘要：**窄 `lr`（`lr.{t,w,b}.{nn,an,ar}` 共 9 条）写回改为「只写目的低 W 位、高位保持原值」**（`spec/SimRISC-12 §1.1`；用户 2026-11-19 裁定，依据 `m15-idl-020 D3`）：`target/dadao/translate.c` 新增 `store_rd_narrow()`（`new = (old & ~mask) | (val & mask)`，`mask = 2^(8W) − 1`），`gen_lr()` 对 `width == 8`（`lr.o`）保持整 64 位写、窄宽度改走切片写（既不零扩展也不符号扩展）。`tests/inst/12-misc` 的 9 个 `lr` 载体期望值按新语义订正（`tests/case-ledger.tsv` 同步重生成；`check-inst-asm` 272/272）。补丁 1 份改。
  - 执行者：engineer

## M16

- **2026-11-21 `m16-testcases-003`**
  - 摘要：**`sc` 保留标记的清除点收敛到「异常/中断进入向量」这一处（`ISS-443`；`spec/SimRISC-12 §1`「保留机制」）**。`target/dadao/helper.c`：`cfx_enter()` 第 7 步真正进入向量时置 `env->lock_valid = 0`（覆盖同步异常、`trap` 与异步投递；被 mask 而未投递的异步源不经过此处）；`dadao_cpu_do_interrupt()` 顶部的原清除删除——该钩子也服务 semihosting 短接（只推进 PC、不进入任何处理器），按 spec 不属清除事件。修复 `trap cfx_hmon` 后 `sc` 仍成功的问题（原只有经 `cpu_do_interrupt` 的同步异常清）。补丁 1 份改（`target/dadao/helper.c`）。
  - 执行者：engineer

- **2026-11-22 `m16-qemu-001`**
  - 摘要：**`-machine kaiwu-vast,cache-model=off|on` 属性 + cfx5（`cfx_cache`）寄存器面（`contract-cache` CACHE-03/04/06/07/09/11/12/13/14/18/27/28；`spec/Kaiwu §3.2`；用户 2026-11-22 裁定「模型只决定有没有效果，不决定 cfx5 是否存在」）**。`hw/dadao/dadao-machine.c`：新增 QOM 属性 `cache-model`（`off` 默认 / `on`；非法值与 `kaiwu-tiny,cache-model=on` 均在启动期 `error_setg` ⇒ 非零退出，不静默降级），`on/off` 只置 `cpu->env.cache_model_on`。`target/dadao/cpu.h`：`DadaoProfile.cache_cfx`（Vast 有 cfx5、Tiny 无）、`cfxha 5` 进 `dadao_cfxha_map`（`DADAO_NUM_CFX` 9 → 10，获得常规两轴 mask/向量行）、cfx5 位域常量、`dadao_cache_exist()`（`on` ⇒ `0b11`、`off` ⇒ 0）与 `cache_enable`/`cache_addr_start`/`cache_addr_size` 状态（`cache_ctrl` 为 WO，无存储）。`target/dadao/helper.c`：`cfx_idx()` 让 cfx5 在 Vast 的**两种** `cache-model` 下都存在（不再走「未实现 cfx ⇒ `CFXREG`」）；cfx5 **只实现 cg8 寄存器面**，其余 cg（含共享 cg0-cg6 与 cg7）仍 `CFXREG`（CACHE-04）。`cfx2rd`/`cfx2rc` 的 cg8 分支按契约：rc0 exist（RO，`on` 读 `0b11`、`off` 读 0）、rc8 enable（RW，位效果随 exist，复位值 = exist）、rc9 ctrl（WO，写即执行）、rc10 addr_start（RW，`PA[55:0]`、`[63:56]` 读 0）、rc11 addr_size（RW）；其余 rc ⇒ `CFXREG`。`cache_ctrl` 按 CACHE-11 判序（选择 → 操作 → 范围/操作数）：`sel=00`/`op=none` 无条件 no-op 且不查范围与 `size`；合法编码**接受但无效果**（影子 D-Cache 与维护效果留后续任务）；`[3:2]=11` 或 `PA 区间` 且 `size=0` 在**两种模型下**都 ⇒ `CFXREG`（`cause_info` = 指令编码）。`target/dadao/cpu.c`：复位 `cache_enable = cache_exist`。`tools/testcases/arch/min_rom_probe_integ042t.py`：`cfx5_cache_cfxreg`（期望 `CFXREG`）改为 `cfx5_cache_noop`——off 下 `cache_exist` 读 0、36 种合法 `cache_ctrl` 编码被接受且无异常（合法阶段用「任何异常即 exit 0x19」的处理器，避免假绿），非法编码仍 `CFXREG` 且 `cause_info` = 该指令字（CACHE-08/14）。补丁 4 份改（`hw/dadao/dadao-machine.c`、`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-22 `m16-qemu-004`**
  - 摘要：**`fence` 的保留 cfx 集对齐 spec（`ISS-432`）**：`target/dadao/insn_trans/trans_ctrl.c.inc` 的 `fence_cfx_reserved()` 由局部口径 `6–14, 19–61` 改为复用 `DADAO_CFX_IS_RESERVED()`（`target/dadao/cpu.h`，`6–14, 16–31, 35–61`；`spec/Kaiwu §1.2` + `spec/DADAO-12 §1` + `contracts/legality_rules.yaml` 的 `encode_cfx_reserved`），消除与 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的口径漂移；`hb ≠ 0 ⇒ ILLI` 与六位 pred/succ 屏障实现不变。探针（Tiny 三方）：cfx16/17/18 与边界 14/31/35/61 ⇒ `ILLI`，cfx0/15/32/33/34/62/63 ⇒ 放行，QEMU/gem5/chipyard 逐字节一致。补丁 1 份改（`target/dadao/insn_trans/trans_ctrl.c.inc`）。
  - 执行者：engineer

- **2026-11-22 `m16-qemu-002`**
  - 摘要：**影子 D-Cache 数据通路（`cache-model=on`；`contract-cache` CACHE-05/27/29/30；几何与 Wuming RTL 一致）**。`target/dadao/cpu.h`：D-Cache 几何常量与 per-hart 存储（8 路 × 128 组 × 64 B = 64 KiB；每行 `tag`/`valid`/`dirty`/64 B 数据；每组件替换游标；`off` 时指针为 NULL）、`dadao_dcache_redirect()`（RAM 窗口 PA → 代理窗口主机地址，其余原样）。`target/dadao/helper.c`：`MemoryRegionOps` 代理（`128` 组 × `8` 路查找、读缺失整行填充、写缺失写分配、脏行淘汰整行写回底层 RAM、`DEVICE_BIG_ENDIAN` 字节序）；`tlb_fill` 只对**数据访问**做重定向（取指仍走原路径）；页表读取与 A/D 回写经 `dadao_dcache_read()/write()`，使脏 PTE 行对走页表可见、A/D 更新与后续访存一致；退出时打印一行 `dadao-dcache:` 命中/缺失/写回统计（仅 `on`）。`target/dadao/cpu.c`：semihosting/调试的 PA 视图对 RAM 半区同样重定向（脏行未写回时退出码块仍可见）。`hw/dadao/dadao-machine.c`：仅 `cache-model=on` 时创建并映射代理 `MemoryRegion`（主机地址在 56 位 PA 空间之外），`off` 不建代理、全部走原直通路径；`cfx_pmem` DMA 与镜像装载继续用 `address_space_memory` 的真实 PA，天然绕过影子。cfx5 维护命令（clean/invalidate/flush、I 侧）仍为合法 no-op，留 `m16-qemu-003`。补丁 4 份改（`hw/dadao/dadao-machine.c`、`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-22 `m16-qemu-003`**
  - 摘要：**cfx5 `cache_ctrl` 维护命令接线（`contract-cache` CACHE-08/09/11…CACHE-24/CACHE-27；`spec/DADAO-12 §4.6`）**。`target/dadao/helper.c`：`cache_ctrl` 继续按 CACHE-11 判序（选择 → 操作 → 范围/操作数），校验与模型/使能无关；合法命令按 `[15:14]` 分侧（bit15=I、bit14=D），`cache_enable` 对应位门控（`off` 时 `cache_enable`=0 ⇒ 自然 no-op，CACHE-27）。**D 侧**：遍历影子阵列按 56 位 PA 做三档匹配（`all` / 含 `addr_start` 的 64 B 行 / 与 `[start, start+size)` 相交，64 位加法饱和不绕回），`clean` 把脏行经 `address_space_write` 写回真实 PA 并清 dirty（保留行），`invalidate` 直接丢弃（不写回、不报异常），`flush` 写回后删除；只有 RAM 窗口内存在行 ⇒ MMIO/不可缓存 PA 天然无效果（CACHE-22）。**I 侧**：`clean` no-op；`invalidate`/`flush` 对选中范围（`all` 折叠到影子 RAM 窗口）经 `address_space_translate` 取 RAMBlock 偏移后调 `tb_invalidate_phys_range()`（复用 ARM `IC IVAU` 写法）使后续取指重取，不建 I 阵列；两侧全选先 I 后 D（CACHE-21）。`target/dadao/cpu.h`：订正 cfx5 行注释（off 下存在且 `cache_exist` 读 0，不再写「CFXREG」）。补丁 2 份改（`target/dadao/{cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-23 `m16-qemu-005`**
  - 摘要：**cfx5 的 `cg0`–`cg7` 走 `cfx_reg_ptr` 通用共有寄存器表（`contract-see §3`；`spec/DADAO-12 §3`）**。`target/dadao/helper.c`：删除 `cfx2rd`/`cfx2rc` 对 cfx5 的「非 `cg8` ⇒ `CFXREG`」特判（两条对称路径），使 cfx5 的 `cg0`–`cg2`（四类同步 mask/`cfx_intr_mask`/`switch_run_mode`/`excp_vector`）、`cg3`（hypv 行 + `rc12` `hypv_cg_reg_deleg`，复位全 1、RW、bit3 硬连线 1）、`cg4`（`cfx_id`/`version`/计数/`scratch_regs_num`，只读）、`cg5`（异常现场）、`cg6`（scratch，`rc >= scratch_regs_num ⇒ CFXREG`）、`cg7`（只读空间描述，cfx5 无内部空间 ⇒ 全 0、写 ⇒ `CFXREG`）由通用路径应答；`cg8` 的 CACHE-03/04/27 专属语义不变（off/on 两模型都存在）。`cg3 rc12` 的既有通用实现（写或 bit3、`supv` 按目标 cfx 位图判定、未开放 ⇒ `CFXPERM`）即满足 cfx5 的 deleg 要求，未改语义。订正 cfx5 cg8 注释中「只实现 cg8」的过时表述。补丁 1 份改（`target/dadao/helper.c`）。
  - 执行者：engineer

- **2026-11-25 `m16-qemu-006`**
  - 摘要：**`cfx_pmem` 寄存器面 + `cfx_power_ctrl` 写侧 + `cfx_hart cg9 rc6` 写忽略（`ISS-533/525/536`；`spec/DADAO-12 §4.9/§4.12/§4.7`）**。`target/dadao/{cpu.h,cpu.c}`：`CPUDADAOState` 增 `pmem_start/size/attr[64]`（`DADAO_PMEM_REGIONS=64`，复位 0）；`DadaoHartAsync` 删 `switch_run_mode` 存储。`target/dadao/helper.c`：新增 `dadao_pmem_reg_{read,write}()`——`cg8 rc0 pmem_exist` 读全 1（测试机约定 64 区域全存在）、写 ⇒ `CFXREG`；`cg12/13/14 rc0..63` 为 64 位 RW 存储，其余 cg8 rc ⇒ `CFXREG`；`cfx2rd/rc` 在 cg15 前接线该面；`cfx_power cg8 rc1` 写被接受（按 `§4.12` bit0 关机 / bit1 硬复位 / bit2 软复位落 QEMU run state；写 0 无动作），读仍 ⇒ `CFXREG`；**写分支按 profile 门控**：`DadaoProfile.power_ctrl`（Vast true / Tiny false），Tiny 按 `spec/Kaiwu §3` 落回通用路径 ⇒ `CFXREG`（不设静默桩）；`cg9 rc6` 读回恒 supv(2)、写被接受且不生效，`dadao_async_enter()` 固定投递 supv。`tests/arch/{pmem,power}` 与 `expected-divergences.yaml DIV-06` 同步 QEMU 侧现状（gem5 仍未补齐，close_when 收窄不删除）。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-25 `m16-qemu-007`**
  - 摘要：**`cfx_hart cg9 rc6`（`async_switch_run_mode`）回归 `m18-spec-006`：RW、复位 2、异步进入取该值**。`target/dadao/cpu.h`：`DadaoHartAsync` 恢复 `switch_run_mode` 存储（2 位，复位 2 = supv）。`target/dadao/cpu.c`：复位置 `switch_run_mode = supv`。`target/dadao/helper.c`：`cg9 rc6` 读回存储值、写 `val & 0x3` 落地（不再是「写接受、忽略、恒 2」）；`dadao_async_enter()` 的进入模式改为 `switch_run_mode & 0x3`（删除硬编码 supv 与 Tiny 的 hypv 覆盖——Tiny 无 cfx_hart，不可达）。`tests/arch/hart/cfx15.S`：`arch-hart-001` 增加 rc6 复位 2、写 0/1/3 读回、supv 下 rc6=0/2 连续投递并以 `prev_run_mode` 证明进入模式（89 槽）；`check_cfx15.py`/`check_hart.py`/`check_hart_rtl.py`/`expected.yaml`/README 同步。`tests/arch/expected-divergences.yaml`：`DIV-18` 收窄为 RTL/gem5（QEMU 已对齐）。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

## M17

- **2026-11-24 `m17-qemu-001`**
  - 摘要：**异常原因编码扁平化（`ADR-0062`；`contract-see §6.1/§6.1.1` 已由 `m17-spec-002` 落扁平位图）**。`target/dadao/cpu.h`：删 `DADAO_SUB_NCFXPERM`（`[39]`）与 `DADAO_SUB_NONPTW`（`[57]`），`DADAO_CAUSE_WYDE2/WYDE3` 改为扁平位图掩码 `DADAO_CAUSE_PERM_BITS`（`[38:32]`）/`DADAO_CAUSE_MEM_BITS`（`[56:48]`）+ `DADAO_CAUSE_RESERVED`（`[31:16]`/`[39]`/`[47:40]`/`[57]`/`[63:58]` 恒 0）；`CFXMEM`/`CFXPERM` 注释收窄为「非 PTW 核内访存」/「cfx 来源掩码拒绝」。`target/dadao/helper.c`：`CFXPERM` 不再带 `[39]`，`cause_info` = **触发指令地址**（`cfx_raise_perm()` 收为 `(env, pc)`，`trap`/`cfx2rd`/`cfx2rc` 五处统一传 `pc`；`ISS-469`）；`CFXMEM` 不再带 `[57]`；PTW 权限/缺失/`ADWBFAIL` 只置高位位图之一（`[38:32]`/`[56:48]`/`[56]`）且父 `CFXPERM`/`CFXMEM` = 0，`cause_info` 按 `ADR-0062 D4`（权限/缺失 = VA、`[56]` = PTE PA）；`dadao_cause_check()` 改判扁平不变式（64 位恰一位、低位 cause 时 `[63:32]` 全 0、位图位时 `[15:0]` 全 0、保留位恒 0）。路由不变（PTW 故障进当前运行模式 monitor，`ADR-0062 D6`；Tiny 退出码不变）。测试载体：`tests/arch/umon/m5_perm_mask_cfxperm.S` 断言整字 `cause_id == 0x80` 且 `cause_info == excp_cause_ip`；`tests/arch/ptw/ptw_carrier_tlb.py` 的合约解析与断言改扁平位图（整字相等、父位为 0），`expected.yaml` 同步。补丁 2 份改（`target/dadao/{cpu.h,helper.c}`）。
  - 执行者：engineer

## M18

- **2026-11-23 `m18-qemu-004`**
  - 摘要：**异步投递改 hart-first（`ADR-0060` 取代 `ADR-0059`）**。`target/dadao/cpu.h`：新增 `cfx_hart cg9` 异步现场寄存器组（`DadaoHartAsync`：`rc0` prev_run_mode、`rc1` prev_cfx_code、`rc2` cause_ip、`rc3` cause_id、`rc4` saved_global_intr_mask、`rc5` pending、`rc6` async_excp_vector、`rc7` switch_run_mode、`rc8` global_intr_mask、`rc9`–`rc12` user/jail/supv/hypv 五个来源掩码）；`DADAO_CAUSE_TIMER`/`DADAO_CAUSE_PMEM_DMA` 改为宏 cause `1<<17`/`1<<18`，`DADAO_CAUSE_RESERVED16` → `DADAO_CAUSE_MACRO16`。`target/dadao/helper.c`：新增 `dadao_async_enter()`（目标固定 `cfx_hart`，mask 位索引 = 源 cfxha 15/32、mode 行按事件到达模式选、`rc8` 全局轴；被 mask 或 `cause_id != 0` 时只置 `async_pending`（位 = 源 cause id）；进入时写 `rc0`–`rc4` 并把 `rc8` 置全 1，切 `rc7`（supv）跳 `rc6`）；`dadao_async_arbitrate()` 只从 `cfx_hart cg9 rc5` 取 pending、按源 cfxha 升序单层投递；源事件（TIMER/PMEM_DMA）与 cmp/ctrl 写均改记 `cfx_hart cg9 rc5`；`cfx2rd/rc` 增加 cg9 寄存器面（仅 `cfx_hart`；宽度/4B 对齐落盘；`rc13`–`rc15` ⇒ `CFXREG`；写后重踢），`cfx_reg_ptr` 不再承担 cg9；`escape imms18` 增帧选择位（`{0,1,2}` 合法、`3` 与 `[17:2]` 非零 ⇒ `ILLI`、选 `cg9` 时恢复 `async_prev_run_mode`/`async_prev_cfx_code`/`async_saved_global_intr_mask` 并以 `async_cause_ip` 返回）；`dadao_cause_check` 放行 `[31:16]` 单宏 cause；同步 `cfx_enter` 收敛为 sync-only（异步不再走错误地写 cg5）。`target/dadao/cpu.c`：中断入口注释改 hart-first，复位给 cg9 五 mask 全 1、`rc7=supv`。探针/文档：`tools/testcases/arch/min_rom_probe_integ051t.py` 重写为 hart-first（cg9 现场、mask 位 15/32 vs pending 位 17/18、无嵌套、释放补投、escape 2/3/SBZ）、`tests/arch/vast-arch-inventory.md` 与 `tools/testcases/arch/README.md` 同步；K2 探针文档的 TIMER cause 订正为 `1<<17`。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-23 `m18-qemu-005`**
  - 摘要：**异步模型修订（`ADR-0061` 取代 `ADR-0060` D2/D3/D5/D6/D7 口径）**。`target/dadao/cpu.h`：`DadaoHartAsync` 精简为 7 槽（`rc0` prev_run_mode、`rc1` prev_cfx_code、`rc2` cause_ip、`rc3` `async_src_frame`（HW/RO）、`rc4` `async_src_pending`（HW/RO）、`rc5` 向量、`rc6` 固定 supv；`rc7`–`rc15` ⇒ `CFXREG`）；删除 `cg9` 五个掩码与 `saved_global_intr_mask`、`cg0`–`cg3 rc4`（`cfx_intr_mask`），异步来源掩码改为 `cfx0`–`cfx3 cg8 rc1`（`async_intr_mask`，位 = 源 cfxha，复位全 1）；删除 `DADAO_CAUSE_TIMER=1<<17`/`DADAO_CAUSE_PMEM_DMA=1<<18`，源身份 = 源 cfxha（15/32）。`target/dadao/helper.c`：`dadao_async_allowed()` 按当前运行模式取 monitor 掩码并应用源本地 TIMER IMASK gate；同一指令边界把 `pending && !masked` 的源合并成一帧（`src_frame` 并集、`src_pending` 扣除、`excp_async_num` 每帧 +1），帧活动期只置 pending；`escape` 以 `src_frame != 0` 判帧有效并在合法返回时清 0 释放，不再保存/恢复掩码；`trap` 删除掩码保存/恢复；`dadao_cause_check` 拒绝 `[31:16]` 非零（异步不占 `excp_cause_id`）；`cfx2rc cg9 rc3/rc4` 写忽略、读不变、不产生异常；`dma_status` W1C 在源事件清空后落 pending。`target/dadao/cpu.c`：复位只初始化 monitor `cg8 rc1` 与 `cg9 rc6`，dump 去掉 `INTRMASK`。探针：`min_rom_probe_integ051t.py` 重写为 7 槽/两图/一帧多源/监控掩码/ack 语义，K2 探针期望改源位与 `cfx_smon cg8 rc1`。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-23 `m18-qemu-006`**
  - 摘要：**异步捕获缓冲修订（`ADR-0061` R2）**。`target/dadao/helper.c`：`dadao_async_allowed()` 删除 `src_frame != 0` 门控——`cg9` 只是进入瞬间的捕获缓冲，每次异步进入都覆盖，是否投递只由当前运行模式 monitor 的 `cg8 rc1` 掩码决定（屏蔽只置 pending、解除后进入）；`dadao_async_enter()` 注释改为「覆盖 `prev_*`/`cause_ip`/`src_frame`」；`helper_cfx_escape()` 删除 cg9 异步返回分支——`imms18[1] = 1`（`imms18 = 2`）不再返回异步帧，按所选帧无效处理 ⇒ 当前 cfx 的 `CFXESC`，且不改变 cfx/运行模式/`cg9`（不清 `src_frame`、不计数），sync `cg5` 路径与 `imms18 = 3` ⇒ `ILLI` 不变。`target/dadao/{cpu.c,cpu.h}`：注释同步为捕获缓冲语义（无 `frame_valid`、无「帧活动期」）。探针 `tools/testcases/arch/min_rom_probe_integ051t.py`：异步 handler 改为「读 `cg9` 捕获 → 软件搬运 → `trap cfx_smon` 交接返回」（不再 `escape` 异步帧），新增 `overwrite_two_entries`（连续两次进入、第二次覆盖）、`nested_capture`（handler 内再进入，`prev_mode` = supv / `prev_cfx` = `cfx_hart`）、`escape_no_async_return`（`escape imms18 = 2` ⇒ `CFXESC`、`cg9` 不变）；去掉释放帧/防重入断言，改为捕获保持。K2/K5 探针 P4 期望与 `tests/arch/vast-arch-inventory.md` 同步。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-24 `m18-qemu-001`**
  - 摘要：**`ISS-501` 复核（`lr`/`sc` 窄宽度条件写）+ 新回归向量；本组件无补丁变更**。复核对象 `target/dadao/translate.c` 的 `gen_sc`/`lr`（`lrsc_memop`，M15 `m15-qemu-002` 起未改动）：当前参考机（`qemu-dadao`/`qemu-system-dadao`，QEMU 11.1.1 + 本补丁集）在 180 组用户态形状矩阵（前置 `st.o`/`st.t` × 同址/邻址 `ld.ut`/`ld.o` × 宽度 `.b/.w/.t/.o` 与偏移 × CAS 环形状）与 11 个 system 形状探针（`ld.ut` 在 `lr` 前/后、`ld.o`、1/2/8 B 宽、保留被抢的失败路径）上行为全部符合 `spec/SimRISC-12 §1` + `contract-isa §14.2`：`sc` 成功时窄写必然落地、同字邻居半字不变，失败时不写。原 mallocng 症状的其他成因在 musl 侧（`m18-infra-001` 已把 `a_cas` 换成 8 字节字 CAS）。补丁集 **0 份改动**（`check-patch-tree` qemu 段 0 assertion）；回归覆盖为新向量 `tests/inst/00-isa-design/atomic_rmw.S` 第 14/15 点。
  - 执行者：engineer

- **2026-11-26 `m18-qemu-008`**
  - 摘要：**异步 escape 出口（`ADR-0061` R3；`DADAO-12` 0.8.0）**。`target/dadao/cpu.h`：`DADAOCfxModeRegs` 的 `switch_run_mode`/`excp_vector` 迁到 `rc14`/`rc15`；`DadaoHartAsync` 重排为 `rc0`–`rc3` 入口记录（prev run mode / prev cfx / prev ip / prev intr mask）、`rc4` 源集合、`rc5` pending、`rc14` switch、`rc15` vector；`DADAOCfxRegs` 的 `cg5` 改为入口记录 `rc0`–`rc3`（只读）+ 原因 `rc4`/`rc5` + 出口意图 `rc8`–`rc11`（`rc11` 复位全 1），删除 `pending`。`target/dadao/helper.c`：`cfx_reg_ptr` 按新槽位表（`cg0`–`cg2` 仅 rc0–3/14/15、`cg3` 加 rc12、`cg5` 只读 rc0–5 + RW rc8–11、`cg9` 读 rc0–5/14/15 且 rc0–5 写忽略）；`cfx_enter()` 同步进入写目标 cfx `cg5 rc0`–`rc5` + `rc8`–`rc11`（`rc11` = 进入前运行模式 monitor 的 `cg8 rc1` 快照）；`dadao_async_enter()` 只写 `cg9 rc0`–`rc4` 与 hart 自己的 `cg5 rc8`–`rc11`，不写 hart `cg5 rc0`–`rc3`；`helper_cfx_escape()` 重写为 `escape cfxHA`：`imms18` 必须 0（非 0 ⇒ `ILLI`）、`cfxha` 非当前 cfx / 目标 cfx 未实现 / 目标模式无 monitor / 升权 ⇒ `CFXESC`（全部在切换前判定）、跳 `rc10`、`rc11` 整字写入目标模式 monitor 的 `cg8 rc1`（与切模式/切 cfx/跳转同一转换）、`escape_num` +1，删除 `cause_id != 0` 帧有效性检查；`cfx2rc` 写侧对 `rc14`（Tiny 忽略）/`rc15`（低 2 位忽略）/`cg5 rc8`–`rc11`（2/6/48/64 位掩码）分工。`target/dadao/cpu.c`：复位初始化入口记录、出口意图（`rc11` 全 1）与 `cg9 rc14=2`/`rc15=0`；`-d cpu` 的 `PREVM` 行把 `PEND` 换成 `PIM` 并新增 `ESCOM/ESCIC/ESCIP/ESCIM` 行。探针：`tools/testcases/arch/node_probe_prelude.py` 的 hypv 向量写 `rc10` → `rc15`；新增自包含单测 `tools/testcases/arch/min_rom_probe_m18qemu008.py`（21 例 / 150 断言：cg5 布局与访问、cg0–cg3 四行各自 rc14/rc15 与旧 rc8/rc10、cg9 新布局、同步与异步进入写入集合、escape 六类判据；槽位/复位值/低 2 位规则现场取自 `DADAO-12 §3.1–§3.4`/`§4.7`）。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-26 `m18-qemu-009`**
  - 摘要：**每源 pending/mask/ack 迁移（`ADR-0064`；`DADAO-12` 0.8.1-rc）**。`target/dadao/cpu.h`：`DadaoHartAsync` 的捕获组迁到 `cg15`（删除 `src_pending` 存储，`rc5` 改为原始 pending 汇总视图）；monitor `async_intr_mask` 改由 `cg15 rc3` 解析（旧 `cg8 rc1` 归 reserved）；`cfx_hart`/`cfx_pmem` 新增 `cg16 rc16/17/18` 源接口（mask 复位全 1、pending ack-only、ack W1C）；`cfx_hart cg16 rc0/rc1` 为 timer ctrl（仅 bit0 ENABLE）/cmp；删除 `dma_ctrl.IRQ_EN` 与 `pmem_dma_irq_en`，新增 `hart_timer_{mask,pending}`/`pmem_dma_{mask,pending}`。`target/dadao/helper.c`：`cfx_reg_ptr` 只把 `cg15 rc3` 给 cfx0–3、`cg8 rc1` 不再解析；`cfx_hart cg8 rc4/rc5` 归 reserved；`cfx2rd/rc` 的 hart 捕获组由 `cg9` 改 `cg15`，新增 hart/pmem `cg16` 分发；定时器事件改为置 `cg16 rc17` bit0（ENABLE 门控、使能即检、写 cmp 不清 pending、ack 幂等）；DMA 完成（`DONE|ERROR`，含 START 时 ERROR）置 `cg16 rc17` bit0，`cg16 rc18` 只清 pending，`dma_status` 仍自行 W1C；`dadao_async_allowed()` 逐源判 `pending & ~源mask` + monitor `cg15 rc3`（timer 还要 ENABLE），`dadao_async_enter()` 合并多源、**不清源 pending**，`cg15 rc5` 始终由源 pending 派生；`escape` 的 `rc11` 整字恢复到目标 monitor `cg15 rc3`。`target/dadao/cpu.c`：复位置新 mask/pending 字段与 `cg15` 捕获组。测试：新增 `tools/testcases/arch/min_rom_probe_m18qemu009.py`（10 例 / 91 断言，`--self-test` 全断言可达 FAIL）；`tests/arch/hart/check_cfx15.py`、`tests/arch/pmem/{check_pmem,pmem_oracle}.py` 的静态布局解析同步 0.8.1-rc；`tests/arch/vast-arch-inventory.md` 与 `tools/testcases/arch/README.md` 登记新探针与 KNOWN-RED（旧 `cg9`/`cg8 rc1`/`IRQ_EN` 向量归 `m18-testcases-005`）。补丁 3 份改（`target/dadao/{cpu.c,cpu.h,helper.c}`）。
  - 执行者：engineer

- **2026-11-26 `m18-qemu-010`**
  - 摘要：**异步进入的运行模式上限（`DADAO-12` §5.4(一)，`cg15 rc14`）**。`target/dadao/helper.c`：`dadao_async_allowed()` 在逐源 pending/mask 判定之外增加 `inner_run_mode <= cfx_hart cg15 rc14`（`async_switch_run_mode`，复位 2）；当前模式高于上限时返回 0（不进入），源 `cg16 rc17` pending 与 `cg15 rc5` 汇总保留、不报错、不丢事件，条件满足后在后续指令边界重判。默认 `rc14 = 2` ⇒ `hypv` 不被异步打断；配成 3 时可从 `hypv` 进入，入口 `cg15 rc0` 记录 `hypv`，`escape cfx_hart` 返回同级、不触发升权。探针 `tools/testcases/arch/min_rom_probe_m18qemu009.py` 增 2 例（`async_mode_cap_hypv_block_supv_enter`：hypv 下 pending 保留、回到 supv 后正常进入且 `rc0=supv`；`async_mode_cap_hypv_open`：rc14=3 时 hypv 进入并 escape 返回 hypv），共 19 例 / 157 断言；`tests/arch/vast-arch-inventory.md` 与 `tools/testcases/arch/README.md` 同步。补丁 1 份改（`target/dadao/helper.c`）。
  - 执行者：engineer

- **2026-11-27 `m18-qemu-007`**
  - 摘要：**移除 `cfx_jmon`（cfx1）实现（用户 2026-11-25 裁定；与 RTL 口径一致，RTL 无 cfx1）**。`target/dadao/cpu.c`：`DADAO_CFX_IMPL_VAST` 去掉 `1ULL << 1`（`jmon` 无 cg/rc 面、无 jail 模式语义、无 SBI 入口，设计未定义）。`target/dadao/{cpu.h,helper.c}`：`DADAO_NUM_CFX` 10→9、`dadao_cfxha_map` 去掉 cfx1（`{0,2,3,4,5,15,32,34,63}`）；`trap cfx1` 与 cfx1 寄存器访问按「allocated-but-unimplemented」既有规则 ⇒ `CFXREG`（进入当前运行模式 monitor；不静默、不落别的 monitor）；`trap cfx0/2/3` 行为不变。清理 `umon/jmon/smon/hmon`、`umon/jmon/ptw: 16 blocks` 等「jmon 已实现」表述；`jail→jmon` 的 escape 注释改为「jail 无 monitor（cfx1 未实现）⇒ `CFXESC`」。`target/dadao/insn_trans/trans_ctrl.c.inc`：linux-user `trap cfx1` 注释改为「spec 分配但本机/测试机均未实现」。测试：`tools/testcases/arch/min_rom_probe_m18qemu009.py` 的 hmon 掩码复位用例改为断言 `cfx_jmon cg15 rc3` 读 ⇒ `CFXREG`（保留 `cg9` 保留 rc 的 `CFXREG` 断言）；`tests/arch/README.md` 与 `pmem*.S` 注释登记 cfx1 未实现。补丁 4 份改（`target/dadao/{cpu.c,cpu.h,helper.c,insn_trans/trans_ctrl.c.inc}`）。
  - 执行者：engineer


- **2026-11-28 `m18-linux-016`**
  - 摘要：**linux-user `dadao_argmask` 补 `TARGET_NR_futex_waitv`(449) = 0x09**，与 musl C stub / 内核入口 / gem5 SE 表逐项一致（`check-syscall-abi` 86/86）。`series` 69 不变。
  - 执行者：engineer
