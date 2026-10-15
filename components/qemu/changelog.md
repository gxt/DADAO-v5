# QEMU 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M1

- **2026-09-23 —**
  - 摘要：**M1 补丁集重整**：由「16 份编号补丁 + `git am`」改为「树形补丁集 + `git apply`」（本组件 8 → **31** 份 = 新增 25 + 修改 6）。应用后最终 tree hash = `4a14d56ce4ecfc6f5edd2f2d181ec6628844233b`（与重整前一致，语义未变）。决策见 `ADR-0002 D4`（rev. 2026-09-23）。

## M2

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
