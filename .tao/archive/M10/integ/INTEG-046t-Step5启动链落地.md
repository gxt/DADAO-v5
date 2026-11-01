# INTEG-046t: Step5 启动链落地（BootROM image table / hmon / smon / 第一张页表）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-044t（两轴权限）、INTEG-042t（cfx_pmem SRAM + DMA）、INTEG-041t（TLB/A-D）、INTEG-040t（页表步进）、INTEG-038t（PTBR/PTW）；决策源 **ADR-0043 D1–D15**（另见 ADR-0045、ADR-0046）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景

1. 现行 `tests/shared/bootrom/bootrom.S` 是**单级**启动：power → hmon 桩 → 直接 `trap cfx_umon` 进 user app（`-bios` 64 KiB 平铺镜像 + `-kernel` 平铺 app）。ADR-0043 要求的 **power → hmon → smon** 分层链、唯一 256 KiB BootROM、image index table + ELF 装载、smon 第一张页表/PTW 均未落地。
2. QEMU 侧现状（已调查）：ROM 仅 64 KiB（`target/dadao/cpu.h.patch` 的 `DADAO_ROM_BASE/DADAO_ROM_SIZE`，`DADAO_RESET_PC == DADAO_ROM_BASE`）；**hmon/smon 无 SRAM**（`tlb_fill` 只特判 cfx17 pmem SRAM，cfxha 2/3 落在 cfx 内部空间 ⇒ CFXMEM）；**PA 0 无物理存储器**（RAM 只有 `0xFC00_0000_0000` 16 MiB，`dadao_pmem_dma_pa_ok` 与 PTW 页表读都只认这段）。
3. 承载 `-kernel` ELF 的现有路径（`contract-elf.md §5.2/§6`）与 30+ `min_rom_probe_*`、`run_m5_e2e.py` 都以 **`-bios` = 64 KiB 复位窗口 `0xffff_ffff_0000`** 为前提；本任务不得让它们回退。
4. spec 正文与 ADR-0043 存在**已知缺口**（见「约束」末条与「验收」BLOCKED 项）：`DADAO-12 §2.1` 表无 smon SRAM 行、BootROM 仍记 64 KiB；`Machine-01 §2` 仍写「不启用 supv、不涉及 smon」。**本任务不改 `spec/`**。

## 目标（范围）

1. **BootROM 几何（ADR-0043 D1/D2）**：ROM 区改为 `0xffff_fffc_0000`–`0xffff_ffff_ffff`（256 KiB，RO+X）；**复位向量不变** `0xffff_ffff_0000`（= 镜像内偏移 `0x3_0000`）。既有 `-bios` 语义**保持不变**（仍按 64 KiB 复位窗口装载），新 BootROM 镜像经**新机器属性**装载（接口见 §接口规范 4）。
2. **image index table**（格式真源 = 本文 §接口规范 1）：偏移 0 起的表头 + 定长表项（type/flags/offset/size/reserved）。
3. **power 阶段**（ROM 偏移 `0x3_0000`，hypv/cfx63）：读表 → 校验表项 → 装载 hmon ELF 到 hmon SRAM → 设 hmon H-mode 向量/陷入模式 → `trap cfx_hmon, <boot_magic>`。
4. **hmon 阶段**（hmon SRAM `0x0fff_0000_0000`，hypv/cfx3）：校验 `CFXTRAP + magic` → 设 rbsp → 复用 ROM 里的同一装载例程装载 smon ELF 到 smon SRAM → 设 smon S-mode 向量/陷入模式与运行期 cfx 权限（§接口规范 3）→ `trap cfx_smon, <boot_magic>` → park。
5. **smon 阶段**（smon SRAM `0x0bff_0000_0000`，supv/cfx2）：校验 magic → 设 rbsp → 用 **cfx_pmem cg15 DMA** 建立第一张页表（PTBR=0、单 512 MiB 超页、`VA 0x0200_0000_0000 → PA 0`）→ 开 PTW → 自检 → `SYS_EXIT(0)`。
6. **ELF 基本校验（不做签名）**（清单见 §接口规范 2），失败**报码退出**（码表见 §接口规范 5），不静默继续。
7. **构建期尺寸检查**：hmon/smon 镜像（文件与装载足迹 `Σp_memsz`）均 ≤ 64 KiB；power 平铺段 ≤ 64 KiB；整镜像恰 256 KiB。
8. **park + poison**：power/hmon 在 `trap` 后紧跟「poison 写 + 自环」，正常路径不可达；探针以 poison 未写 + 无对应 PC 断言「未被恢复执行」。
9. **测试/证据**：新探针 + builder 自检 + `run.sh` 可达 FAIL 注入 + cp+md5 还原；门控按改动类型跑（见「验收」）。

## 接口规范

**1. BootROM image index table（本任务真源；表项与镜像一律大端、8/16 字节对齐）**

表头 16 字节：

| 偏移 | 类型 | 字段 | 值/约束 |
| --- | --- | --- | --- |
| 0 | u32 | `magic` | `0x4442_4F54`（ASCII `DBOT`） |
| 4 | u16 | `version` | `1` |
| 6 | u16 | `count` | 表项数（本任务 = 2） |
| 8 | u32 | `boot_magic` | handoff magic，须 = `0x30001`（= `HBI_<name>_INIT`，`DADAO-23 §3` 既有编码；本任务不新造 magic 值） |
| 12 | u32 | `reserved` | SBZ = 0 |

表项 32 字节（自偏移 16 起连续，`count` 个）：

| 偏移 | 类型 | 字段 | 含义 |
| --- | --- | --- | --- |
| +0 | u32 | `type` | `1`=hmon(cfx3)、`2`=smon(cfx2)；其余保留 |
| +4 | u32 | `flags` | bit0 `REQUIRED`、bit1 `LOAD`、bit2 `VERIFY`、bit3–31 **SBZ=0** |
| +8 | u64 | `offset` | ELF 起点相对 ROM 基址的偏移 |
| +16 | u64 | `size` | ELF 文件字节数（≤ 64 KiB） |
| +24 | u64 | `reserved` | SBZ = 0 |

flags 语义（本任务定义）：
- `REQUIRED=1`：该项装载失败 ⇒ 启动链**报码退出**；`=0`：失败时**跳过转载**继续（后续必然由链路自身暴露，不得静默成功）。
- `LOAD=1`：引导方须把镜像从 ROM 装到目标 SRAM；`=0`：不装载（本任务全部 = 1）。
- `VERIFY=1`：装载前执行 §2 全部校验；`=0`：只做 magic + 长度/SRAM 边界的最小校验。
- bit3–31 任一非 0 ⇒ 表项非法 ⇒ 报码退出。

镜像布局：`[表头+表项][hmon.elf][smon.elf][pad 0x00][power 平铺段 @0x3_0000..0x3_FFFF]`，总长恰 `0x4_0000`。

**2. ELF 基本校验清单（LOAD/VERIFY 生效时逐条；任一条不符 ⇒ 报码）**

- `EI_MAG` = `0x7f 'E' 'L' 'F'`；`EI_CLASS` = 2（ELF64）；`EI_DATA` = 2（大端）；`EI_VERSION` = 1。
- `e_type` = 2（`ET_EXEC`）；`e_machine` = `0x0DA0`（`EM_DADAO`，`contract-elf.md §1.3`）。
- `e_flags[7:0]` = 1（ABI 版本）、`e_flags[31:8]` = 0；`e_ehsize` = 64；`e_phentsize` = 56；`e_phnum` ≥ 1；`e_phoff + e_phnum*56 ≤ size`（全程 64 位无溢出）。
- 每个 `PT_LOAD`（`p_type` = 1）：`p_filesz ≤ p_memsz`；`p_vaddr == p_paddr`；`p_offset + p_filesz ≤ size`；`p_vaddr % 4 == 0`；`p_memsz` 非 0。
- 装载窗口：`p_paddr ≥ 目标 SRAM 基址` 且 `p_paddr + p_memsz ≤ 基址 + 64 KiB`（hmon `0x0fff_0000_0000`、smon `0x0bff_0000_0000`）。
- `e_entry` 落在某个 `PT_LOAD` 的 `[p_paddr, p_paddr+p_memsz)` 内且 `%4 == 0`。
- 装载动作：拷 `p_filesz` 字节到 `p_paddr`，`(p_memsz − p_filesz)` 尾部清零。
- **不做签名/摘要校验**。

**3. 启动链寄存器写入表（初始值见 ADR-0045 D4 / DADAO-13 §1）**

power（hypv/cfx63）：
- `cfx_hmon` cg3 rc10（hypv excp vector）← hmon `e_entry`；`cfx_hmon` cg3 rc8（switch_run_mode）← `3`（hypv）。
- 不写 `cfx_power`/`cfx_smon` 的任何 mask（默认已允许 hmon 取指/读 ROM：`0xFFFF_FFFF_FFFF_FFF7` 的 bit3 = 0）。

hmon（hypv/cfx3）：
- `cfx_smon` cg2 rc10（supv excp vector）← smon `e_entry`；`cfx_smon` cg3 rc8 ← `2`（supv）。
- 运行期开放（`0xFFFF_FFFF_FFFF_FFF3` = 默认值清 bit2/smon，只对**已实现**的 cfx 写）：`cfx_ptw`(4)、`cfx_pmem`(17) 的 cg2 rc0–rc3（cfxtrap/cfxmem/cfxreg/cfxexe）、cg3 rc12（`hypv_cg_reg_deleg`）清 bit2。
- `cfx_hmon` cg2 rc0（supv cfxtrap）清 bit2（允许 smon 后续 `trap` 入 hmon 做 poweroff/reset，ADR-0043 D13）。
- 撤销 hmon 自身对 `cfx_pmem` 的运行期访问（D13「hmon 不保留 DMA 启动权」）：`cfx_pmem` cg3 rc0–rc3 置 bit3=1（`0xFFFF_FFFF_FFFF_FFFF`）；**最后**写，写完即失去访问。
- **不写** `cfx_hmon`/`cfx_power` 的运行期开放项（D9「不开放 hmon/power」）；`cfx_cache`(5)/`cfx_uart`/`cfx_time`/`cfx_hart`/`cfx_llc` 在测试机**未实现**（写其寄存器 ⇒ `CFXREG`）⇒ 不得写，登记为遗留。

smon（supv/cfx2）：
- rbsp（`rb1`）= `0x0bff_0000_0000 + 0x1_0000 − 16`；hmon rbsp = `0x0fff_0000_0000 + 0x1_0000 − 16`；power rbsp = `0xFC00_0000_0000 + 16 MiB − 16`。
- 页表：`cfx_pmem` SRAM（`0x47ff_0000_0000`，核内偏移 `0x3ff_0000_0000`）整 64 KiB 清零 → SRAM 偏移 `0x8000` 写 L1 PTE（值见下）→ cg15 rc0=SRAM 基址、rc1=`0`、rc2=`0x1_0000`、rc3=`START|DIR=0`（CFX→PA）→ 轮询 rc4 至 `BUSY=0`，须 `DONE=1`、`ERROR=0`。
- `cfx_ptw` cg9 rc0（`cfx_ptw_ptbr`）← `0`；再 `cfx_ptw` cg8 rc8（`cfx_ptw_enable`）← `1`（不隐含 TLB 失效；复位 TLB 为空）。
- L1 PTE = `0x4000_0000_0000_FFE3`：HSJU=`S`（bit62）、PPN=0、SPF=`0xFF`、R/W/X=1、G=0、A/D=0（硬件维护）、SP=1、P=1；索引 `VA[41:29] = 0x1000` ⇒ PTE 字节偏移 `0x1000*8 = 0x8000`。
- 自检：`VA 0x0200_0000_2000`（PA `0x2000`，**避开 PTE 所在 `0x8000`**）写模式 → VA 读回 → 再 DMA PA→SRAM 读回比对；反向 DMA 写 PA `0x1000` → VA `0x0200_0000_1000` 读回比对；`cfx_ptw` cg9 rc0 读回 `0`、cg8 rc8 读回 `1`。观测值放 `rd5`–`rd12`（供 `-d cpu` 比对）。
- 完成 ⇒ `SYS_EXIT(0)`（ADR-0020 D8）。

**4. QEMU 接口（待实现时确认落法，推荐方案如下）**

- 新机器属性 `bootrom-image=<path>`：装载 256 KiB BootROM 到 `0xffff_fffc_0000`；给出该属性时 `-kernel` 不再必需、且**不得**同时给 `-bios`（给了即 `error_report` + 非零退出）。
- `-bios` 语义不变：装载到复位窗口 `0xffff_ffff_0000`，上限 64 KiB（既有探针/e2e 零改动）。
- 复位 PC 与 `rb0` = `0xffff_ffff_0000`（独立常量，不再等于 ROM 基址）。
- hmon/smon SRAM：各 64 KiB，仿 cfx_pmem SRAM（RAM region 落在 **56 位 PA 之外**的 host 地址 + `tlb_fill` 按 cfxha 3/2 且内部偏移 `0x3ff_0000_0000` 路由；偏移越界 ⇒ `CFXMEM`）。
- PA 0 物理存储器：**待实现时确认** 落法（推荐「把现有 16 MiB DRAM 在 PA 0 别名」，即 `dadao_pmem_dma_pa_ok` 与 PTW 页表读同时接受 `PA [0, 16 MiB)` 与 `[RAM_BASE, +16 MiB)`；ROM 仍只可读）。选此方案须核 `min_rom_probe_integ042t` 的 `PA_FAULT` 期望（现仅「写 ROM」一例，别名不破坏它）。

**5. 失败码（semihosting `SYS_EXIT`，host `$?` 取值；避开 ADR-0004 D5.8 冻结的 `0x80`–`0x8D`）**

`0xB1` 表头 magic/version/count/SBZ · `0xB2` 表项 flags SBZ 非 0 · `0xB3` 镜像超 64 KiB · `0xB4` ELF 头不合规 · `0xB5` ELF 段不合规 · `0xB6` 表项 REQUIRED 失败且不可跳过 · `0xB7` hmon 收到非预期 magic · `0xB8` smon 收到非预期 magic · `0xB9` 页表/DMA/PTW 自检失败。
（失败一律**报码退出**；正常路径的 park 自环不参与报码。）

## 修改文件范围（已按现状核对存在性）

- QEMU 组件补丁（4 份）：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`、`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（ROM 几何/`bootrom-image`/hmon+smon SRAM/PA 0 别名/ROM 窗口校验上限）。
- `components/qemu/changelog.md`：1 条（M10）。
- 新固件（6+1 文件）：`tests/shared/bootrom/step5/{power.S,hmon.S,smon.S,power.lds,hmon.lds,smon.lds,README.md}`（三份 lds 各带 `ASSERT` 尺寸上限；power 段 ORIGIN `0xffffffff0000`/64 KiB）。
- 新工具：`tools/testcases/arch/build_step5_bootrom.py`（打包 + 尺寸/表项自检 + `--self-test`，含超限注入开关供证据用）。
- 新探针：`tools/testcases/arch/min_rom_probe_integ046t.py`（用例见「验收」；`--qemu/--bootrom-image/--only/--list`，默认产物读 `.dadao/tests/bootrom/step5/`）。
- `tools/testcases/arch/README.md`（登记两新文件）；`Makefile`（`build-bootrom` 增 step5 产物 + builder 调用；`ARCH_CFX_PROBES += integ046t`）。
- 契约投影（跟随 ADR-0043，逐条标 `[ADR-0043 §D1/§D2]`）：`.tao/contracts/contract-see.md`（启动段）、`.tao/contracts/contract-elf.md`（§5.2/§6.1.2/§6.2 的 boot ROM 窗口几何 `0xffff_ffff_0000/64 KiB` → 新 ROM 区 + 复位窗口语义）。
- 台账/文档：`tests/INVENTORY.md`、`tests/README.md`（固件资产行；计数现场派生）。
- **不动**：`spec/**`、`manifests/spec-readonly.lock.toml`、`tests/shared/bootrom/bootrom.S`（legacy 应用路径保留）、`contracts/opcodes.yaml`、`tests/inst/**`。

## 验收

1. `make build-bootrom` rc=0，产出 `bootrom_step5.bin`（**恰 262144 字节**）+ 三份 ELF/平铺件；builder 摘要打印 offset/size/flags；`builder --self-test` rc=0。
2. 探针 `min_rom_probe_integ046t.py --qemu <安装根 qemu>` 全用例 PASS，至少覆盖：
   - `chain_basic`：power→hmon→smon 三段均执行（`-d cpu` 中分别出现 ROM 内 PC（`CFXCODE: 63`/`MODE: 3`）、hmon SRAM 内 PC（`CFXCODE: 3`/`MODE: 3`）、smon SRAM 内 PC（`CFXCODE: 2`/`MODE: 2`））；三层 marker（RAM/hmon SRAM/smon SRAM 各一字）全部命中；host rc=0。
   - `vectors`：`cfx_hmon` cg3 rc10 == hmon `e_entry`、`cfx_smon` cg2 rc10 == smon `e_entry`、`cfx_smon` cg3 rc8 == 2。
   - `ptw_state`：`cfx_ptw_ptbr` = 0、`cfx_ptw_enable` = 1（dump `PTBR:`/`PTW_ENABLE:` 逐条）。
   - `pte_value`：DMA 从 PA `0x8000` 读回 `0x4000_0000_0000_FFE3`。
   - `va_pa_both_ways`：VA 写→DMA 读 PA 相等；DMA 写 PA→VA 读相等（两个方向各一例）。
   - `no_resume_poison`：power/hmon 的 poison 字均保持 0（未被恢复执行）。
   - 反例（各例可达 FAIL，期望码见 §接口规范 5）：`bad_table_magic`(0xB1)、`flags_sbz`(0xB2)、`image_oversize`(0xB3)、`bad_elf_header`(0xB4)、`bad_elf_segment`(0xB5)、`smon_not_required_bad_elf`(hmon 跳过且 smon 未运行)、`hmon_magic_mismatch`(0xB7)、`flags_verify_off`（正向：仍装载成功）。
3. 反例的可达 FAIL 由**本探针自身**证明（每例断言 `期望码 != 实测码` ⇒ FAIL）；不写恒真断言。
4. 尺寸检查的双向证明：builder 默认拒绝超 64 KiB 镜像（`--max-image-size` 注入 ⇒ 非零退出，见证据脚本）。
5. 门控（按改动类型）：
   - **L1** `make check` rc=0（含 `check-patch-tree`/`check-source-state`/`check-component-changelog`/`check-spec-readonly`/`check-contracts-dir`/`check-tests-index`/`check-no-residue`）。
   - **L2** `make check-modules` rc=0（含 `check-arch-smoke`：**legacy** forward 10/10 + permission 10/10 + 25 服务；证明旧引导路径不回退）。
   - **L3** `make check-arch` rc=0（新增 `integ046t` + 既有 `044t/045t/049t/integ039t/integ040t/integ042t/integ044t` 全 PASS）；改 QEMU 组件补丁 ⇒ 先 `make build-qemu`（自动装到安装根）并披露重建耗时。`make check-full` 若时间允许建议跑（非硬性）。
6. 证据 `.work/evidence/<任务号>/{run.sh,check.py}`：默认全绿；`--inject` ≥2 处（如「builder 尺寸上限」「探针期望 PTE 值」）→ FAIL → `cp` 备份 + `md5sum` 对账还原 → 回绿，输出 `EVIDENCE INJECT: PASS`。
7. 完成区 ≤30 行、审阅记录每轮 ≤40 行；任务书 `**状态**` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-046t/`。

**BLOCKED（本任务不解决，须如实登记）**
- **spec 正文对齐**：`DADAO-12 §2.1`（补 smon SRAM 行、BootROM 256 KiB）、`Machine-01 §1.1/§2/§3`（启用 supv/smon、RAM 口径）**无用户授权改 `spec/`** ⇒ BLOCKED；替代证据 = ADR-0043 D1–D15 + 本文 §接口规范 + 探针实测 + 契约投影。
- **`cfx_*_cg_reg_deleg` 强制**：QEMU 现仅存储不检查（`helper.c.patch` 无消费点）⇒ 本任务只写值并断言 dump 值，**权限强制**另立任务。
- **PA 0 物理存储器落法**：待实现时确认（推荐别名），确认结论须落任务书并披露。
- **多 hart / jmon / umon 代码 / 用户态** 不在本任务。

## 参考对照（`DADAO-0628` 只读检索；**内容溯源，非执行必需**，不作为执行依赖、不复制代码）

- **0628 做法**：启动只有「flat trampoline」一级——64 KB ROM（`0x0010_0000`）+ flat 测试 bin（`0x8000_0000`）+ exit port MMIO，复位直接跳应用（`.cache/refs/DADAO-0628/code-agent/knowledge/06-machine-memory-map.md §6.1/§6.5`）。
- **本项目差异**：v5 要分层（power→hmon→smon）、唯一 256 KiB BootROM、ELF 镜像 + 索引表、smon 首张页表/PTW；停机上早已由 semihosting `SYS_EXIT` 取代 exit port（ADR-0020 D8）。
- **建议落点**：本任务书 §接口规范 1/2/5 为唯一真源；0628 的 trampoline 仅证明「ROM 平铺 + `-bios` 装载」可行，不参与本任务设计。

## 约束

- 只做本任务；**不提交、不 push**（提交权归 architect）；不跑 `check-full` 夜跑；重建前先申报预计耗时。
- **不改 `spec/`**（含 `manifests/spec-readonly.lock.toml`）；`spec` 与 ADR 的缺口按上面 BLOCKED 登记，不得顺手改。
- **`-bios` 语义与既有 30+ `min_rom_probe_*`、`run_m5_e2e.py` 必须零改动保持绿**；如某项必须改，先停下报告（可能意味着方案需重选）。
- 旧 `bootrom.S`（power→hmon→user）**保留**：smon 尚无应用装载能力（umon/用户态在本任务范围外），legacy 应用路径由其继续承担。
- 单 hart、固定 hart0；不实现 frame_active/异步重入；不实现 SBI DMA 封装（smon **直接**用 `cfx_pmem` cg15）。
- 反例注入还原一律 `cp` + md5（禁 `git checkout/restore/stash`）。
- 失败保留现场并继续推进（自行处置/有据重试并记次数）；**只有需用户语义裁定**时留问。

## 用户授权原话

本轮无用户逐字原话；以下为**主会话派单原话（原样落纸）**，spec/契约外的实现细节按 ADR-0043 已确认决策（该 ADR「状态说明」列明：唯一 BootROM、power 无 SRAM、hmon/smon 64 KiB、镜像复制链、trap magic、页表/PTW、超高区映射、park 均已确认）：

> 任务：创建 `INTEG-046t: Step5 启动链落地` 任务书（文件放 `.tao/tasks/integ/`，任务号按现有序列顺延）。
>
> 任务书必须自包含，至少包含：背景、依赖、目标、验收、约束、用户授权原话（可引用本轮对话结论，但不能编造原话；没有原话就写"本轮架构讨论确认"并列出确认点）；明确的修改文件范围；启动链范围：BootROM image index table、ELF 基本校验（不做签名）、image flags（bit0 REQUIRED、bit1 LOAD、bit2 VERIFY，其余 SBZ）、hmon/smon 镜像 ≤64 KiB 构建期检查、power→hmon→smon、hmon/smon 的 SRAM/向量、smon 第一张页表（PTBR=0、单 512 MiB 超页、VA 0x0200_0000_0000→PA 0）、PTW 开启、handoff magic、park；不包含：SBI DMA 封装（另立任务；本任务只允许 smon 直接访问 cfx_pmem cg15）、多 hart、jmon/umon 代码、用户态测试、签名/安全启动、per-hart 异常栈；测试/证据：新增或更新 boot 探针、`run.sh` 可达 FAIL 注入、cp+md5 还原、L1/L2/L3 门控按改动类型；下发前预检 5 项结论；若某验收前置不可用，标 BLOCKED 并给替代证据。
>
> 按已确认的 ADR-0043 决策和本轮讨论落纸；不确定的写成"待实现时确认"，不要猜。

**本轮架构讨论确认点（无逐字原话，均为本文自定细则，实现时按此执行）**：表头/表项格式与 magic `DBOT`、`boot_magic` = `0x30001`、flags 三位的语义、失败码 `0xB1`–`0xB9`、park = 「poison 写 + 自环」、PTE 常量 `0x4000_0000_0000_FFE3`、`bootrom-image` 机器属性方案、PA 0 别名推荐方案。

## 下发前预检（5 项）

1. **任务书内部一致**：PASS——§接口规范 1–5 与「目标」「验收」逐项对应（表格式↔builder、flags↔反例、寄存器表↔`vectors`/`ptw_state`、PTE 常量↔`pte_value`、失败码↔反例期望、尺寸检查↔builder 注入）；`-bios` 兼容约束与「验收 5」L2 对应。
2. **验证手段前置实际可用**（本轮实测）：`.dadao/cross-toolchain/bin/{llvm-mc,ld.lld,llvm-objcopy,qemu-system-dadao}` 存在；`make build-bootrom` rc=0（PASS）；`min_rom_probe_integ044t.py --qemu .dadao/cross-toolchain/bin/qemu-system-dadao` rc=0（`RESULT: PASS`，探针框架可用）。**前置缺口**：新机器属性/新 SRAM/PA 0 需 QEMU 重建后才存在（属任务自身交付物，非外部阻塞）。
3. **验收逐条可跑性**：验收 1/2/3/4/6 **现在可跑**（依赖本任务产物，同任务内闭环）；验收 5 的 L3 `check-arch`（含新探针）**现在可跑**；`check-full` 标**可选**（耗时）；BLOCKED 三项见「验收」末段（spec 对齐 / cg_reg_deleg 强制 / PA 0 落法），已给替代证据。
4. **与 `contracts/`、`tests/inst/` 一致**：PASS——本任务只用 `trap/escape/cfx2rd/cfx2rc` 与 `ld/st`（`contracts/opcodes.yaml` 现行条目，`INTEG-045t` 后无 `cfxld/cfxst`）；不新增指令/编码；`tests/inst/**` 不改；`contract-elf.md §1.3` 的 `EM_DADAO/e_flags` 规则被 §接口规范 2 直接复用。
5. **拟改文件 × `spec/` 清单**：**无 `spec/` 命中**（见「修改文件范围」末行「不动」清单）⇒ 不触发「须用户授权原话」阻断；但 **spec 正文与 ADR-0043 的 3 处缺口**（`DADAO-12 §2.1` 无 smon 行/BootROM 64 KiB、`Machine-01 §2` 不启用 supv/smon、`Machine-01 §1.1` RAM 口径）**必须在主会话收尾时登记并另立 spec 任务**，不得在本任务内静默改。

## 完成区

**测试结果**：`make check` rc=0；`make check-modules` rc=0；`make check-arch` rc=0（smoke + 8 探针，`integ046t` 15/15）；`build_step5_bootrom.py --self-test` rc=0；证据 `run.sh --inject` 0 failed（`EVIDENCE INJECT: PASS`）。
**修改文件**：`components/qemu/patches/{target/dadao/{cpu.h,cpu.c,helper.c}.patch,hw/dadao/dadao-machine.c.patch}`、`components/qemu/changelog.md`；`tests/shared/bootrom/step5/{power,hmon,smon}.{S,lds}` + `README.md`；`tools/testcases/arch/{build_step5_bootrom.py,min_rom_probe_integ046t.py,README.md}`；`Makefile`；`.tao/contracts/{contract-see,contract-elf}.md`；`tests/{INVENTORY.md,README.md}`；**越界披露**：`tools/infra/check_interface_alignment.py`（ROM 几何断言随 ADR-0043 更新，否则 L1 红）。
**验收结果**：`bootrom_step5.bin` = 262144 B（header magic/version/count/boot_magic 逐项打印）；`chain_basic/vectors/ptw_state/pte_value/va_pa_both_ways/no_resume_poison/deleg_dump` 全 PASS；反例 `0xB1/0xB2/0xB3/0xB4/0xB5/0xB7` + `smon_not_required_bad_elf`（rc=0x89、三 marker 均 0）+ `flags_verify_off`（正向 rc=0）全 PASS；legacy `integ042t` 25/25、`integ044t` PASS、`run_m5_e2e` PASS（`-bios` 语义未回退）。QEMU 增量重建约 1 min；`install-host` 通过。
**规范核对**：`0x30001` 为 `DADAO-23 §3` 既有 `HBI_<name>_INIT`；PTE `0x4000_0000_0000_FFE3` 与 `contract-see §2` 的 HSJU/PPN/SPF/RWX/SP/P 位布局一致；表格式（大端 16+32B）为本任务接口真源，与 `contracts/` 无冲突。
**新发现/坑**：① `ret rd,imm` 只把**常量**写 rd、返回地址从 RAS 弹出 ⇒ 状态返回必须 `ret rd0,0`（用 `ret rd6,0` 会把状态清 0）；② 共享例程在 **power 平铺段** `0xffff_ffff_2000/2400`，不是 256 KiB ROM 基址；③ `stm.o {rd8:rd63}` 一次写 448 B，避免 64 KiB 清零循环产生海量 `-d cpu` TB 日志；④ builder 的 `--self-test` 必须写临时目录，否则污染真实 `step5/`；⑤ `-d cpu` 的 RD 一行有 4 个寄存器，解析须 `finditer`。
**遗留问题**：spec 正文对齐（`DADAO-12 §2.1`、`Machine-01 §1.1/§2/§3`）仍 BLOCKED（无授权改 `spec/`；替代证据 = ADR-0043 D1–D15 + 本任务接口规范 + 15 例探针）；`cfx_*_cg_reg_deleg` 仅存储不检查，本任务只写值并断言 dump（`rd17=0xFFFF_FFFF_FFFF_FFF3`），权限强制另立任务；PA 0 采用「现有 16 MiB DRAM 别名」落法（已核 `integ042t` PA_FAULT 不回退）；`check-full` 未跑（任务标可选）。
**新发现/坑（门控）**：`check_interface_alignment.py` 的 ROM 几何/复位断言必须随 ADR-0043 同步，否则 L1 必红。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `ret rd6,0` 把 DMA 状态清 0 | ✅已修 | `smon_dma_wait` 改 `ret rd0,0`，状态留在 rd6 | `deleg_dump`/`pte_value` PASS |
| 共享例程地址误用 256 KiB ROM 基址 | ✅已修 | 改为 power 段 `0xffff_ffff_2000/2400` | `chain_basic` 三段 PC 均命中 |
| `e_phoff` 被比较指令覆盖 | ✅已修 | 先存 `rd11` 再用 | `0xB4/0xB5` 反例仍按期望触发 |
| 入口区间检查用 `rd7` 被 VERIFY 标志覆盖 | ✅已修 | 改用 `rd6` 保存 VERIFY | 链路 rc=0，15/15 |
| `phnum*56` 误算成 57n | ✅已修 | `rb9` 从 0 起累加 8/16/32 | 链路 rc=0 |
| flags `LOAD=0` 未生效 | ✅已修 | `rb14` 记录 LOAD，装载段前判零跳 copy | `flags_verify_off` 正常；代码审查 |
| `p_memsz` 64 位回绕未检查 | ✅已修 | 窗口检查前加 `p_memsz <= 64 KiB` | 15/15 + 代码审查 |
| builder `--self-test` 写真实产物目录 | ✅已修 | 临时 `out_dir` | `step5/` 无 `self-test.bin` |
| 探针 RD 只匹配行首 | ✅已修 | `finditer` 一行 4 个 RD | 6 个观测用例全 PASS |

判决：全部 finding 已修，标 `待验收`。

#### 第 1 轮 architect 提交（文件集审核）

档位：`待验收`（reviewer 未验收）——按主会话派单原话用 `feat(integ): INTEG-046t Step5 启动链落地` 提交（非 `WIP:`；偏差已在本轮声明，未 push）。提交号见下轮 reviewer 前 `git log`。

文件集对账（23 项，全部显式 staging，未用 `git add -A`）：
- 与完成区「修改文件」一致（21 项）：qemu 补丁 4 + changelog、step5 7 文件、tools/testcases/arch 3、Makefile、contracts 2、tests 2 文档、`check_interface_alignment.py`（已披露越界）。
- **多提（完成区声明遗漏，判为状态机机械同步，接受）**：`.tao/knowledge/milestones.md`（仅 `待开始`→`待验收` 一行，L1 `check-milestones-fresh` 要求与任务书一致）、本任务书自身（状态/完成区）。
- 漏提/越界：无。`spec/**`、`manifests/spec-readonly.lock.toml`、`contracts/opcodes.yaml`、`tests/inst/**`、`tests/shared/bootrom/bootrom.S` 均未改（`git status --porcelain -- spec/ manifests/` 空）。
- 临时残留：`git status -uall` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`*.bak`；产物在 `.dadao/`、证据在 `.work/`（均 ignore）。
- `check_interface_alignment.py` 越界**接受**：断言改为 `ROM_BASE=0xFFFF_FFFC_0000`/`256KiB`、`RESET_PC=DADAO_BIOS_LOAD_BASE`，与 `cpu.h.patch` 实际常量逐条对齐（ADR-0043 D1 的机械投影；不改则 L1 红）。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，均在 workdir 内）**：
- `git branch --show-current` = `INTEG-046t`；`git status --porcelain -uall` 空（验收前后快照逐行对账一致，`/tmp/opencode/INTEG-046t-review/{pre,post}-status.txt` 均 0 行）；`git diff master...HEAD --stat` 23 文件，与提交 `ef799558` 完成区清单对齐。
- `make check` **rc=0**（`repository checks (L1): PASS`；check-patch-tree 205 patches OK、check-no-residue PASS、check-spec-readonly 21 卷 OK、check-component-changelog PASS）。
- `make check-modules` **rc=0**（`module checks (L2): PASS`，含 run_m5_e2e PASS）。
- `make check-arch` **rc=0**（`check-arch: PASS`；check-arch-smoke forward+permission **10/10** + 25-service PASS；integ042t **25/25**、integ044t PASS、`run_m5_e2e: PASS`、`integ046t` **15/15**）。
- `make build-bootrom` rc=0（`bootrom_step5.bin` = **262144 B**，header magic=0x44424f54/version=1/count=2/boot_magic=0x30001、entry flags=0x7 逐项打印）；builder `--self-test` rc=0（含 `injected --max-image-size=4096 rejected PASS`）。
- 证据 `.work/evidence/INTEG-046t/run.sh` **rc=0**（5 项全 PASS）；`run.sh --inject` **rc=0**（`inject_builder_size_guard` rc=1、`inject_probe_expected_pte` rc=1、`inject_probe_restored_md5` md5 相等、`EVIDENCE INJECT: PASS`）。脚本逐条审过：断言均有可达 FAIL 路径、无恒真、注入非空、cp+md5 还原。
- **reviewer 独立注入 ×2（非 engineer 注入点）**：① `check_interface_alignment.py` 的 `rom_size_exp` 改回 64 KiB ⇒ `make check-interface` **rc=2**（`ROM_SIZE=256KiB FAIL 期望 65536, 实際 262144`）⇒ cp 还原 + md5 相等 ⇒ rc=0 回绿；② **被测产物**注入：`step5/power.S` 的 marker 立即数 `0x504f→0x414f` ⇒ 重建后同一探针 `--only chain_basic` **rc=1**（`mismatch {'rc': (185,0), 'rd10': (1095718725, 1347376965)}` = 0xB9 + marker 0x414F5745 实测被抓）⇒ cp 还原 + md5 相等、重建后回绿 rc=0。
- **真实 dump 复核**（手动 QEMU，1517 个 dump 块）：末块 `PC=0xbff000000318 MODE:2 CFXCODE:2`；`RD10=504f5745/RD11=484d4f4e/RD12=534d4f4e/RD13=0/RD14=400000000000ffe3/RD17=fffffffffffffff3`、`RD5=RD6=1122334455667788`、`RD7=99aabbccddeeff00`、`PTBR:0 PTW_ENABLE:1`；三段 PC 首现 `0xffffffff0000`(cfx63/mode3)、`0xfff00000000`(cfx3/mode3)、`0xbff00000000`(cfx2/mode2)——与探针断言逐项一致。
- **QEMU 安装根**：补丁 mtime 23:53 < 安装根二进制 23:54，安装根与 `.work/build/qemu` md5 相同（72d6c653…），安装根 `-M dadao-m1,help` 实测含 `bootrom-image` 属性 ⇒ 非旧安装根假绿；`check-source-state` rc=0。

**约束核验**：`spec/**`、`manifests/`、`contracts/opcodes.yaml`、`tests/inst/**`、`tests/shared/bootrom/bootrom.S` 的 `git diff master...HEAD` 均为空、md5 与验收前一致 ✅；`check_interface_alignment.py` 越界 diff 仅为 ADR-0043 D1 机械投影（ROM 256 KiB / RESET_PC=DADAO_BIOS_LOAD_BASE），断言仍 fail-closed（注入实证 rc=2），未放宽判据 ✅；`bootrom.S`/legacy 路径零回退（integ042t 25/25、integ044t、run_m5_e2e、check-arch-smoke 10/10）✅；反例码 0xB1/0xB2/0xB3/0xB4/0xB5/0xB7、`smon_not_required_bad_elf` 实测 rc=**137=0x89** 三 marker 均 0、`flags_verify_off` rc=0，与任务书 §5 一致 ✅；探针 15 例每例可达 FAIL、无恒真 ✅；完成区 7 行（≤30）、审阅记录每轮 ≤40 行 ✅；milestones `待验收` ✅；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`.bak` 残留 ✅。

**finding（非阻断，文档级）**：`.work/evidence/INTEG-046t/check.py` 文档字符串写「min_rom_probe_integ046t.py (14 cases)」，实际探针 15 例（`--list` 实测 15 条、check-arch 15/15）——纯注释笔误，请 architect 收尾时顺手改。

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全部 rc=0、两处独立注入均实证可达 FAIL 并还原回绿、约束无违反）。可进入 `/complete`。

#### 第 1 轮 architect 交叉复核（`/complete`）

**独立重跑（workdir 内，不采信叙述）**：`make check` **rc=0**（L1 PASS）；`make check-arch` **rc=0**（`check-arch: PASS`；arch-smoke forward+permission+25-service PASS、`run_m5_e2e: PASS`、integ042t 25/25、044t/045t/049t/integ039t/integ040t PASS、**integ046t 15/15**）；证据 `.work/evidence/INTEG-046t/run.sh` **rc=0**（5 项 PASS）。日志：`/tmp/opencode/INTEG-046t/arch/{L1,L3,evidence}.log`。`git show --stat ef799558` 23 文件，与完成区「修改文件」+ 已披露越界逐项对齐。

**逐项复核**：
1. `-bios` 零回退：`DADAO_BIOS_LOAD_BASE`/`DADAO_BIOS_WINDOW_SIZE` 已与 ROM 几何解耦；覆盖 = L2 `check-arch-smoke`→`run_m5_e2e.py`（`-bios`+`--bootrom`）10/10 + L3 七个 `-bios` 探针（042/044/045/049/integ039/040/044），本次重跑全绿 ✅。
2. 安装根（ISS-210）：`md5sum` 安装根 == `.work/build/qemu/qemu-system-dadao`（`72d6c653…`），mtime 23:54 > 补丁 23:53；`-M dadao-m1,help` 含 `bootrom-image` ⇒ 非旧根假绿 ✅。
3. `check_interface_alignment.py`：diff 仅 4 处（`rom_base_exp`/`rom_size_exp`/`RESET_PC=DADAO_BIOS_LOAD_BASE` 的取值与文案），仍 fail-closed，未放宽判据 ✅。
4. PA 0 别名 = `memory_region_init_alias(ram)` + `dadao_pmem_dma_pa_ok` 低区接受；`cg_reg_deleg` 仅 `cpu.c` 复位、`helper.c:1501` 返回指针，**无消费点**（与披露一致）；spec 缺口已在「验收·BLOCKED」与「遗留问题」如实登记 ✅。
5. 15 例逐条审：每例先 patch 镜像再断言特定码，无反例恒真 ✅。**建议（非阻断）**：① 0xB6/0xB8/0xB9 无正例（验收为「至少覆盖」，不构成缺口）；② `no_resume_poison` 断言 poison==0 + rc==0，未显式断言「park PC 不出现」（park 为自环 ⇒ 执行必超时且毒字非 0，实际仍可捕获）——留后续强化。
6. 长度：完成区 7 行（≤30）、审阅记录每轮 ≤40 行 ✅；`git status -uall` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`.bak` ✅。

**reviewer finding 处置**：`.work/evidence/INTEG-046t/check.py` 文档字符串 `14 cases`→`15 cases` 已改，`python3 -m py_compile` **rc=0**；该文件位于 `.gitignore` 的 `.work/` 下（`git check-ignore` 命中），**不随提交落地**，仅作本地证据保留。

**判决**：确认 reviewer 的 **Accepted**，无阻断 finding。可进入主会话 `/complete`：置 `**状态**`=`已验证` 并同步 `milestones.md` 对应行为 `已验证`，然后 `merge --squash` + `push`（均归主会话）。

#### 主会话统一收尾

reviewer 与 architect 两份独立复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`。收尾仅同步状态/流水，不改完成区与既有审阅记录。剩余非阻断项：spec 正文缺口（`DADAO-12 §2.1`、`Machine-01`）另立 SPEC 任务；`cg_reg_deleg` 权限强制另立任务；`no_resume_poison` 后续强化。`ADR-0043` 仍为 `Proposed`，不在本任务擅自改状态。
