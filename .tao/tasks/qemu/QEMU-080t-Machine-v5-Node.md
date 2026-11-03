# QEMU-080t: Machine-v5-Node 系统机

**模块**：qemu
**项目里程碑**：M11
**依赖**：`QEMU-079t`（profile 运行时化与 Tiny；必须先验收，二者改同一组 `cpu.h`/`cpu.c`/`helper.c`，串行）、`SPEC-183t`、`TESTCASES-091t`、`QEMU-081t`（页 64 KiB）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；组件源树 `.work/source/qemu` 为 base+1 单提交、`git status` 干净；实现落任务分支 `QEMU-080t`，不 merge、不 push）

## 用户已定口径（2026-11-02/03，摘要）

- Node：BootROM 4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`，复位 `0xffff_ffff_0000`；PA RAM 2 GiB。
- hmon/PTW/hypv；L1 **4 × 512 MiB 超页**、`SPF=0xFF`；entry `0x10_0000`、SP `0x7fff_0000`（由本任务实测校准）。
- 完整 `inst` + `arch` + `embench`；**不含 picolibc**；smon 保留但 M11 不覆盖。
- 本任务只改 QEMU system（组件补丁 + QEMU 测试驱动），不改 `gem5/`、`spec/`、`tests/**`（测试资产归 `TESTCASES-091t`）。
- `QEMU-079t` 先于本任务；本任务把 `dadao-m1` 的缺省 profile 从 legacy 切到 tiny，Node 由显式 `profile=node` 选择（见未决 1）。

## 现状与问题根源

1. `QEMU-079t` 后 QEMU 已有运行时 profile（legacy/tiny），但 Node 的几何、启动链、PTW 口径尚未落地；canonical 宏已按 Node 值预留，运行时仍走 legacy/tiny。
2. Node 的 4 MiB BootROM 不是简单放大：image index table、power→hmon→测试本体、hmon 建页表、PTW/超页/`SPF=0xFF`、cfx_pmem DMA 都要在真实执行中闭环。
3. `TESTCASES-091t` 的 Node 资产只做到「静态迁移 + build-only」；`entry=0x10_0000`/`SP=0x7fff_0000`、hmon 的 4 个 PTE、Node ELF 的 VA→PA 装载都需本任务实测校准。
4. **规范/资产冲突（必须处置）**：`spec/Machine-v5 §6` 写「L1 index `0x1000`–`0x1003`、VA `0x0200_0000_0000`–`0x0200_7fff_ffff`」；但测试资产 `tests/shared/bootrom/step5/hmon.S` 把 4 个 PTE 写在 **L1 index 0–3**（VA=PA `[0, 2 GiB)`），且 `entry=0x10_0000`/`SP=0x7fff_0000` 只在 identity 映射下成立。本任务按用户口径（entry/SP）落地 identity，**不改 `spec/`**；冲突登记为跨模块 issue，交 `SPEC` 另立任务订正。

## 目标

1. Node profile：4 MiB BootROM、2 GiB PA RAM、复位 `base+0x3f_0000`、bootrom-image 精确 4 MiB、legacy `-bios` 64 KiB 窗口保留。
2. power → hmon → 测试本体（hypv）真实闭环；hmon 建 L1（4 × 512 MiB、`SPF=0xFF`）、PTBR=0、`ptw_enable=1`、设 hypv 向量并 `trap` 移交。
3. Node ELF 装载：`PT_LOAD` 按 Node VA→PA 落 PA；入口/SP 实测校准并回填测试 profile（授权时）。
4. 完整 `inst` + `arch` + `embench` 在 Node 上真实执行；`smon` 保留但不纳入 M11 验收；`picolibc` 不跑。
5. `check_interface` 的 Node `qemu_*` 等值断言由 DEFERRED 转为 PASS。

## 接口规范

### 0. 机器与 profile 选择

- 机器名保持 **`dadao-m1`**；`QEMU-079t` 的 `profile` 属性扩展为 `legacy|tiny|node`。
- 本任务移除 `legacy`，缺省改为 **`tiny`**（保持 Tiny/lit/inst 资产零改动）；Node 由显式 `-machine dadao-m1,profile=node` 或 `DADAO_TEST_PROFILE=node` 选择。
- Node 的测试驱动以显式 `profile=node` 为准；不得用镜像大小/地址猜测 profile。

### 1. 地址空间与复位（Node）

| 区域 | 起始 | 大小 | 访问 | 说明 |
| --- | --- | --- | --- | --- |
| BootROM | `0xffff_ffc0_0000` | 4 MiB | RX | 偏移 0 image index table；末 64 KiB（`0xffff_ffff_0000`）复位/启动代码 |
| PA RAM | `0` | 2 GiB | RWX | 物理 `[0, 2 GiB)`；CPU 经 PTW 从 VA 访问 |
| hmon SRAM | `0x0fff_0000_0000` | 64 KiB | RWX | H-mode 向量默认起始 |
| smon SRAM | `0x0bff_0000_0000` | 64 KiB | RWX | 保留，M11 不覆盖 |
| cfx_pmem SRAM | `0x47ff_0000_0000` | 64 KiB | RW | `cg15` DMA |

- 复位 `PC=0xffff_ffff_0000`（= ROM base + `0x3f_0000`）、`rb0` 同值；`ptw_enable=0`、`inner_run_mode=hypv`、`inner_cfx_code=63`。
- 不建 PA 0 之外的 RAM 别名；`addr[47:42]==0` 且 `ptw_enable=0` ⇒ `CFXMEM`；PTW 开启后按页表；power 段 BootROM 外未映射 ⇒ `0x87`（legacy 约定）。
- `bootrom-image` 必须**恰好 4 MiB**；`-bios` 仍按 64 KiB 窗口装到 `0xffff_ffff_0000`；两者不得同给。

### 2. 启动链（Node）

1. power（cfx63/hypv）从 BootROM 校验 image index table，装入 hmon 到 `0x0fff_0000_0000`，设 hmon H 向量/`switch_run_mode`，`trap cfx_hmon,0x30001` 移交。
2. hmon：在 hmon SRAM 建 4 个 PTE（L1 index 0–3，PPN 0/`0x2000`/`0x4000`/`0x6000`，`SPF=0xFF`，`P/W/R/X/A/D/G` 按资产），经 cfx_pmem `cg15` DMA 复制到 PA 0；TLB invalidate、`PTBR=0`、`ptw_enable=1`；设 cfx_umon hypv 向量 = `ENTRY`、`switch_run_mode=hypv`、mask=0；`trap cfx_umon,0` 移交测试本体。
3. 测试本体在 hypv 执行；`entry=0x10_0000`、`SP=0x7fff_0000`（首版；实测校准后回填，见未决 2）。
4. `power → hmon → smon` 路径保留（smon SRAM/cfx2 不删）；本任务不做 smon 启动/验收。

### 3. Node ELF 装载

- `-kernel` ELF：`PT_LOAD` 的 `p_vaddr` 按 Node 口径落 PA；首版支持 **identity `[0, 2 GiB)`**（`p_vaddr == p_paddr`，与 `dadao-node.lds`/`entry=0x10_0000` 一致）。
- 若用户裁定必须同时支持 `spec §6` 的 `0x0200_0000_0000`–`0x0200_7fff_ffff` 窗口：按 `PA = VA - 0x0200_0000_0000` 装载，且不得改变 identity 用例；两者不得对同一段重复装载。
- `bootrom-image` + `-kernel` ELF 时，复位仍为 ROM，`e_entry` **不得**覆盖复位 PC（由 power/hmon 移交）。
- 段区间越界、`p_filesz > p_memsz`、段落在非映射区 ⇒ 装载期错误、非零退出。Node `.rom` 段（若测试资产使用）须落在 BootROM 且不得覆盖 image table/复位窗口；否则登记 BLOCKED，不静默覆盖。

### 4. PTW / 异常 / cfx（Node）

- 页表：64 KiB 普通页 / 512 MiB 超页；PTBR=0 的 64 KiB L1 表；HSJU 与 R/W/X 检查；`SPF=0xFF`；A/D 硬件维护；TLB 命中/填充/失效。
- 页异常进入 `cfx_ptw`（cfx4）；`PTWERR`（A/D 回写失败）按现有实现。
- `cfx0/1/2/3/63`、`cfx4`（PTW/TLB）、`cfx17`（pmem SRAM + cg15 DMA）、`cfx15/18` 时间类保留；`cfx5` 未实现 ⇒ `CFXREG`。
- `smon`（cfx2）保留且可被 power/hmon 移交，但 M11 不做验收；不得删除其 SRAM/向量字段。
- semihosting 为唯一停机协议（`SYS_EXIT`/`SYS_EXIT_EXTENDED`）。

### 5. 与测试资产/接口的对齐

- `tests/shared/machine-profiles.yaml` 的 Node `qemu_*` 字段由 null 回填为 QEMU 实际值（`ram_base=0`、`ram_size=2 GiB`、`bootrom_base/size`、`reset_pc`）；只回填数据，不改几何/期望值。
- `check_interface_alignment.py` 的 Node 等值断言从 `DEFERRED (QEMU-079)` 转为 PASS；若 QEMU 常量名调整，只改该检查器的解析正则，不降低断言强度。
- Node 测试驱动（`tools/testcases/**`，非 `tests/**` 资产）通过 `Makefile` 目标环境行 `DADAO_TEST_PROFILE=node` 选择 profile；不改向量/期望值/链接脚本。若个别驱动需要显式 `profile=node` 机器参数，仅改机器选择字符串。

## 实施清单

- **A. Node profile**：几何/复位/ROM 4 MiB/RAM 2 GiB；移除 legacy；缺省 tiny。
- **B. BootROM/启动链**：4 MiB image、reset offset、power→hmon 移交、hmon 页表/PTW/向量/trap、测试本体 hypv。
- **C. Node 装载**：ELF VA→PA（identity 首版）、入口/SP 校准、`.rom` 边界、装载错误。
- **D. PTW/cfx**：超页 `SPF=0xFF`、A/D/TLB、`cfx_ptw` 异常、cfx_pmem DMA、时间类；smon 保留。
- **E. 驱动/接口对齐**：`profile=node` 选择、`qemu_*` 回填、`check-interface` 断言转 PASS。
- **F. 证据/门控**：`.work/evidence/<任务ID>/run.sh` 一键重跑、注入/还原（`cp` + `md5sum -c`）、日志落 `.work/log/qemu/`。

## 验收标准

1. **几何/接口**：
   - Node 常量与 `spec/Machine-v5 §1.1` 逐项相等（BootROM 首尾、复位 `base+0x3f_0000`、PA RAM 2 GiB、hmon/smon/pmem SRAM），证据脚本从 spec 派生断言。
   - `make check-interface` rc=0；Node `qemu_*` 五项均 PASS（无 `DEFERRED`）；`MACHINE_TYPE_NAME("dadao-m1")` 保留。
2. **BootROM**：`bootrom-image` 4 MiB 接受；4 MiB±1 页 ⇒ rc≠0；复位 PC = `0xffff_ffff_0000`（guest 观测）；`-bios`+`bootrom-image` ⇒ rc≠0。
3. **启动链 e2e**：Node bootrom + 测试 ELF 真实执行；guest 观测到 power→hmon→测试本体、`ptw_enable=1`、`PTBR=0`、L1 4 项、`SPF=0xFF`、`entry=0x10_0000`、`SP=0x7fff_0000`；测试 ELF 正常 `SYS_EXIT(0)`。
4. **PTW**：超页命中、普通页命中、越界/权限拒绝进 `cfx_ptw`、A/D 更新、TLB 填充/失效各至少一例；`SPF=0xFF` 生效。
5. **cfx**：cfx0/1/2/3/63、cfx4、cfx17（SRAM+DMA）、cfx15/18 实测可达；`cfx5` ⇒ `0x84`；smon SRAM 存在且不被删除。
6. **Node 装载**：identity ELF（entry `0x10_0000`）装载并执行；越界段 ⇒ rc≠0；`e_entry` 不覆盖 bootrom 复位；`.rom` 段行为按 §3 记录（支持或 BLOCKED，不静默）。
7. **真实执行**：
   - `inst`：`make check-inst-smoke`（Node，L2 代表集）；至少一轮 Node 全量 `inst`（`make check-inst`，L3 单目标，预计 20–40 min，启动前申报耗时）。
   - `arch`：`make check-arch-smoke` + `make check-arch`（全部 cfx 探针）。
   - `embench`：`make check-tset-embench-smoke`（Node）rc=0。
   - **不跑 picolibc**（Node 不覆盖）；不跑 smon 路径（M11 不覆盖）。
8. **L1/L2**：`make check`（L1）rc=0；`make check-modules`（L2）rc=0。任一红项给出基线/归因；不得为凑绿改范围外文件。
9. **构建/补丁**：`make build-qemu JOBS=8` rc=0；`make install-host` rc=0；两 `qemu-system-dadao` 哈希一致；`make check-patch-tree`、`make check-source-state` rc=0；源树 diff 仅本任务文件。
10. **反例可达 FAIL**（`cp` + `md5sum -c` 还原，禁 `git checkout/restore/stash`）：
    - 把 Node RAM 大小临时改为 1 GiB ⇒ PTW/ELF 用例至少一项 FAIL；还原后回绿。
    - 把 hmon 的 `SPF` 改为 `0x1F` 或复位偏移改错 ⇒ boot/PTW 断言 FAIL；还原后回绿。
11. **体例/台账**：`components/qemu/changelog.md` 在 `## M11` 下追加 `- **2026-11-03 \`QEMU-080t\`**` + 摘要 + `执行者：engineer`；`make check-component-changelog`、`make check-milestones-fresh`、`make check-tasks` rc=0；完成区 ≤30 行；状态 `待验收`。
12. **诚实**：证据落 `.work/evidence/<任务ID>/`（`run.sh`、`run.EXIT`、日志）；失败保留现场；不伪造 Node 执行/PTW 结果。

## 未决（下发前需用户裁定）

1. **profile 缺省**：本任务按「缺省 tiny + Node 显式 `profile=node`」写（保持 lit/Tiny 资产零改动）。若用户要求 `dadao-m1` 默认即 Node，则 Tiny/lit 驱动需加 `profile=tiny`，归 `QEMU-079t`/TESTCASES 连带。
2. **Node VA 窗口冲突**：`spec §6` 的 `L1 0x1000–0x1003 / VA 0x0200...` 与测试资产 hmon 的 `L1 0–3 / identity` 不一致。按用户 `entry=0x10_0000`/`SP=0x7fff_0000`，本任务落地 **identity**；`spec` 订正另立 `SPEC` 任务。若用户要求以 spec 为准，则 Node 测试资产（entry/SP/hmon PTE）必须同步改，超出本任务范围。
3. **跨模块最小连带**：`Makefile` 的 Node/arch 目标环境行加 `DADAO_TEST_PROFILE=node`、`tests/shared/machine-profiles.yaml` 回填 Node `qemu_*` 数据；必要时 `tools/testcases/**` 只改机器选择字符串。是否授权？不授权则 L2 的 Node 机器选择/接口断言登记 BLOCKED，交 TESTCASES 另立任务。
4. **全量 inst/arch 是否纳入本任务验收**（验收 7 的 L3 目标），或只要求 L2 代表集 + `/complete` 时跑全量。

## 文件范围

- 允许：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`、`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（及必要的 `hw/dadao/{Kconfig,meson.build}`）、`components/qemu/changelog.md`、`.work/source/qemu/**`（组件工作树）、`tools/qemu/**`、`Makefile`（仅 profile 环境行，未决 3 授权时）、`tests/shared/machine-profiles.yaml` 的 `qemu_*` 数据回填（仅未决 3 授权时）、`tools/infra/check_interface_alignment.py`（仅解析常量名时）、`tools/testcases/**` 的机器选择字符串（仅未决 3 授权时）、本任务书、`.tao/knowledge/milestones.md`、`.work/evidence/<任务ID>/`、`.work/log/qemu/`、`/tmp/opencode/QEMU-080t/`。
- 禁止：`tests/**`（除未决 3 明确授权的 `machine-profiles.yaml` 数据回填）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、其它 `components/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`。

## 风险

- **R1 规范/资产冲突**（上 §现状 4）：identity 与 spec §6 二选一；本任务按用户 entry/SP 口径落地 identity，必须把冲突登记 issue，禁止静默两边都“通过”。
- **R2 PTW PTE 编码**：hmon 的 PTE 字（`0xffef`/`0x2000`…）须与 QEMU 的 PPN/SPF 解析逐位一致；现场以 guest 访存为准，不以“能启动”代替权限/A-D 验证。
- **R3 arch 资产真实执行**：TESTCASES-091 只做 build-only；Node arch 探针可能仍按 `-bios` 直启/PTW-off 写，需逐例归因（QEMU 缺陷 vs 资产缺口），资产缺口登记 BLOCKED 并另立任务。
- **R4 `.rom` 段/4 MiB BootROM 冲突**：测试 ELF 的 ROM 段可能覆盖 image table/复位代码；装载期必须拒绝或明确布局，不得静默覆盖。
- **R5 缺省切换打断 lit**：缺省改 tiny 后，Tiny lit/Tiny 驱动应零改动；任何因缺省切换导致的红项须先证明是资产未迁移，不得改测试期望值。
- **R6 L2 依赖驱动**：未决 3 未授权时，check-inst-smoke/check-arch-smoke 可能仍打 legacy/缺省 profile；须在完成区明确 BLOCKED 与原因，不得伪称 Node 执行。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：`DADAO-0628` 的 hmon/smon 移交与页表布局是历史参考，但其 reset PC/几何与本机不同；v5 以 `spec/Machine-v5` + `ADR-0043` 为准，不复用其常量/代码。
- 0628 时期 QEMU/gem5 的「裸 `-kernel` + host-side syscall 当作启动」是已知坑（见 `SPEC-183t` 参考对照）；Node 必须以 power→hmon→hypv 真实移交验收，不得用宿主代劳。

## 用户授权（2026-11-03，engineer 子会话问答原文）

- 问：Node 启动链实测发现 `tests/shared/bootrom/step5/power.S` 把共享例程调用目标写成 `BOOTROM_BASE + 0x2000/0x2400`（= 0xffff_ffc0_2000），但 `power.lds` 链接在 `RESET_PC + 0x2000/0x2400`（= 0xffff_ffff_2000）——power 在 ROM 偏移 0x2000 执行到全零，启动链死循环。该文件在任务书「禁止：tests/**」内。是否授权做这 2 行最小修复（只改常量，不改测试期望/语义）？
  答：**「授权 2 行修复（推荐）」**。
- 问：其余 TESTCASES 资产缺口（R3）无法在本任务允许范围内修复：① `min_rom_probe_046t.py` 仍按 RAM_BASE 装载/寻址 kernel，未适配 profile 的 `kernel_base`；② 5 个 `tests/arch/umon/m5_perm_*.s` 仍按「user 模式 + cfx_umon escape 向量」写，Node 的 hypv/hmon 模型下必然 0xB7/0xE1。拟登记 BLOCKED 并另立 TESTCASES 任务，本任务不修。是否同意？
  答：**「同意登记 BLOCKED（推荐）」**。
  > 更正（第 2 轮返工，2026-11-03）：上问 ② 的计数有误——`tests/arch/umon/` 只有 **4 个 `m5_perm_*.s`**（reserved_illi / mask_cfxperm / unimpl_cfxreg / badcombo_cfxreg），arch-smoke 第 5 红是 **`m5_trap_escape`**；BLOCKED 清单以「**4 个 `m5_perm_*` + `m5_trap_escape`**」为准（实测见 `.work/log/arch/`，完成区返工更正同）。
- **用户裁定（`check-arch` L3，2026-11-03，原文）：「登记 BLOCKED（推荐）」**——针对 Node 下 `check-arch` 13 探针红（`min_rom_probe_044t` 全 0x81 CFXMEM、`integ039t` 1/37，根因为探针在 PTW off 时按**已移除的 legacy 几何**直写 PA 0）；修复须改 `tests/**`，归 TESTCASES 另立任务，本任务留真实日志（`.work/log/arch/node-*.log`）并如实披露 L3 红。

## 完成区

**测试结果**：证据 `.work/evidence/QEMU-080t/run.sh` **36/36 PASS**（返工后；含 hmon-context 4 项）（rc=0；`run.log`/`run.EXIT`），`run.sh --inject` **1/1 PASS**（RAM 1 GiB：high-ELF 129→1；hmon `SPF=0x00`：boot 64→135；均 `cp`+md5 还原回绿；`inject.log`）。Node 实跑：`check-inst-smoke` **90/90**；`check-tset-embench-smoke` **PASS**（qemu-user，profile 无关）；`check-interface` **90/90 PASS**（Node 5 项无 DEFERRED）；`build-qemu`/`install-host` rc=0，build/install `qemu-system-dadao` md5 同为 `0949cb1f85df0cf04fbd7ec6b441129e`。`check-arch-smoke` rc=2：forward **5/10 PASS**（5 个 semihosting 全绿；4 个 `m5_perm_*` + `m5_trap_escape` 为 user-mode 向量模型，Node hypv/hmon 下必然 0xB7/超时（见返工更正），见遗留）。`check-inst`（Node 全量）rc=2：**1012 total / 945 passed / 62 failed / 5 deferred**（**43 条** `profiles:[tiny]` + **19 条** Node 移交模型：12×0xB7、6×`code 0x01`、1×UNMAPPED/UNDI；逐条归 TESTCASES 资产，见返工更正）。L2 `make check-modules` rc=2（停在 arch-smoke；inst-smoke/embench 绿，unit 见下）；L1 `make check` rc=2 仅 `check-patch-tree` 的 **gem5 26 项**（GEM5-014t 补丁未重导出，非本任务文件）；qemu slice 干净。`check-unit` rc=2：lit **161/162**（唯一 `mcmodel.test` 为 LLD REL26 检查，非 QEMU）；`test-codegen` 未跑到（check-unit 停在 lit），079 已登记其 19 条基线红。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`、`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（`make_patch.py` 重导出，4 份）、`components/qemu/changelog.md`、`Makefile`（inst/arch Node 目标环境行与 4 MiB bootrom 选择）、`tests/shared/machine-profiles.yaml`（Node `qemu_*` 回填）、`tests/shared/bootrom/step5/power.S`（2 行，用户授权）、`tools/infra/check_interface_alignment.py`（Node 解析：`#define` 锚定 + ULL product）、`tools/testcases/lib/run_qemu_test.py`、`tools/testcases/arch/run_m5_e2e.py`（profile→装载路径选择）、`.tao/knowledge/issues.yaml`（ISS-340）、本任务书、`milestones.md`、`.work/source/qemu`（组件提交 `c79f328`）、`.work/evidence/QEMU-080t/`。
**验收结果**：`profile=node` 实跑复位 `0xffff_ffff_0000`→power（`0xffff_ffff_*`）→hmon（`0x0fff_*`）→body `0x10_0000`（hypv），`PTBR=0`/`ptw_enable=1`；PTW body 校验 4 个 L1 PTE（PPN `i*0x2000`、`SPF=0xFF`、flags `0xEF`）、4 个超页访存、L2 64 KiB 普通页 load/store、SP=`0x7fff_0000`。`bootrom-image` 4 MiB rc=0，4 MiB±1 页 rc=1（`expected exactly 4194304`），`-bios`+`bootrom-image` rc=1；Node ELF（entry `0x10_0000`）rc=0x2A 且首 PC 仍为复位，越界段 rc=1（`outside the mapped regions`）。cfx00/02/03/04/15/17/18/63 注册可见、cfx5 不存在、smon（CFX02）保留。
**新发现/坑**：① `step5/power.S` 的共享例程调用目标用 `BOOTROM_BASE+0x2000`，而链接在 `RESET_PC+0x2000`——启动链此前只在 build-only 下"绿"，真实执行必死循环（已授权修）。② `2048 * 1024 * 1024` 在 C 中是 int 溢出（QEMU `mmap` 收到 2^64−…，报 Cannot allocate memory），2 GiB 常量必须 `2048ULL * 1024 * 1024`。③ Node 测试体以 cfx_umon/hypv 运行，per-cfx 掩码只放行 hmon/power：cfx4/17 等跨 cfx 访问被拒，故 `cfx_ptw` TLB invalidate / fault 向量与 A/D 回写无法由测试体编程（A/D 只在本体自身 TLB 淘汰时回写，实测不可达）。④ 移除 `legacy` 后，按 legacy 几何直写 PA 的 L3 探针（integ039/040/042/050 等）与 `min_rom_probe_046t` 均不可在 Node/Tiny 下真实执行。⑥ Node 的 hmon 直接 `trap` 移交，未清零 rd/rb/RAS；`tests/inst` 载体按复位零态编写，27 条 ctrl-* 因遗留寄存器/RAS 而 FAIL（资产缺口，非 QEMU 指令语义）。⑤ 本 worktree 无 `.work/build/llvm`，`install-host` 需 `LLVM_BUILD/COMPILER_RT_BUILD/CFX_ALIAS_TABLE_BUILD` 指到主树；中断过的默认构建会留下半棵树使 `check_install_tools` 要求 build-tree 对照。
**遗留问题**：① **BLOCKED（TESTCASES 资产；依据任务书 R3/R5 预授权 + 本册「登记 BLOCKED（推荐）」原话）**：Node 全量 `inst` 62 FAIL = **43 条** `profiles:[tiny]` 向量（aip-si 1、ctrl-br 10、ctrl-call 1、ctrl-jump 1、mem-ra 4、mem-rb 4、mem-rd 22）+ **19 条** Node 移交模型（12×0xB7、6×`code 0x01`、1×UNMAPPED/UNDI；ctrl-call 7、ctrl-ret 7、misc 4、ctrl-jump 1）；arch-smoke 5 红 = **4 个 `m5_perm_*`（reserved_illi/mask_cfxperm/unimpl_cfxreg/badcombo_cfxreg）+ `m5_trap_escape`**（user-mode/umon-escape 模型与 Node hypv/hmon 不符）；`min_rom_probe_046t.py` 未适配 profile `kernel_base`。② **BLOCKED（资产）**：Node 测试体的 cfx4/cfx17/cfx15/18 可达性与 PTW A/D/TLB-invalidate 需 hmon 移交 cfx3 上下文或预装 cfx_ptw 向量，超出本任务。③ 跨模块：`spec/Machine-v5 §6` 的 `0x0200...`/L1 `0x1000–0x1003` 与 identity 实现冲突，按用户口径落地 identity，交 SPEC 订正（R1）。④ L1 `check-patch-tree` gem5 26 项、`check-unit` 的 mcmodel/codegen 为基线红，归 GEM5/TESTCASES。

**返工更正（第 1 轮 reviewer Needs Revision，2026-11-03）**：
- **arch-smoke 计数更正**：5 红 = 4×`m5_perm_*`（reserved_illi / mask_cfxperm / unimpl_cfxreg / badcombo_cfxreg）+ `m5_trap_escape`（不是 5 个 `m5_perm_*`）。边界 = 这些向量按「user 模式 + cfx_umon escape 向量」写；Node 测试体在 **hypv / cfx_umon**，fault/trap 进入 current-mode monitor `hmon`，故 0xB7/超时。5 个 semihosting 用例全绿。
- **inst 62 条分类更正**：实测 **43 条**向量 `profiles:[tiny]`（aip-si 1、ctrl-br 10、ctrl-call 1、ctrl-jump 1、mem-ra 4、mem-rb 4、mem-rd 22）+ **19 条** Node 移交模型（12×0xB7、6×`code 0x01`、1×`Expected UNMAPPED got UNDI`；ctrl-call 7、ctrl-ret 7、misc 4、ctrl-jump 1）。
- **L1 第二红**：`check-knowledge-refs`（87 悬空 `.work/**` 引用，均为历史 gem5/旧任务，QEMU-080t 条目不在悬空列表）；与 `check-patch-tree` 的 gem5 26 项并列，均非本任务文件。
- **L3 `check-arch`**：Makefile 已把 `check-arch` 探针与 `check-arch-smoke` 第 2 步显式切 `DADAO_TEST_PROFILE=node`；Node 下 044t rc=1（全部 0x81 CFXMEM）、integ039t 1/37（0x81），根因是探针在 PTW off 时直写 PA 0（legacy 几何）；Tiny 下 raw 16 B < 0x100 保留前缀。基线 rc=0 属已按任务书移除的 legacy。现场：`.work/log/arch/node-044t.log`、`node-integ039t.log`。**用户裁定（2026-11-03，原文）：「登记 BLOCKED（推荐）」**——13 个 L3 探针资产另立 TESTCASES，L3 红如实披露。
- **验收 4/5 新增真实证据**：`.work/evidence/QEMU-080t/hmon_probe.py`（自定义 4 MiB BootROM：真实 power/smon + 合成 hmon = 真实 hmon PTW 建立 + 测试体，运行于 cfx3/hypv）四模式全绿：`success` rc=0（cfx17 DMA DONE + cfx15/18 cfx_id + A/D 回写 + TLB invalidate）、`nwperm` rc=0（W=0 store→`NWPERM` 进 cfx_ptw）、`dgtrap` rc=0（缺页→`DGPTRAP` 进 cfx_ptw）、`cfx5` rc=0x84（`cfx2rd cfx5`→CFXREG 投递到 cfx3 向量）。`run.sh` 现 **36/36 PASS**（含 hmon/smon/pmem 几何断言与精确 semihosting 匹配，修复 `PASS m5_semi_write` 前缀误配）。
- **越界文件与授权**：`tests/shared/bootrom/step5/power.S`——用户原话「授权 2 行修复（推荐）」；`tests/shared/machine-profiles.yaml` Node `qemu_*`、`Makefile` Node 环境行、`tools/testcases/**` 机器选择——任务书未决 3/用户 2026-11-02 批次授权；`tools/infra/check_interface_alignment.py`——任务书「仅解析常量名/正则」允许，改动为 `#define` 锚定 + ULL product 解析，未降断言强度。
- **step2 环境行实际执行**：`check-inst-smoke`（日志 `.work/log/qemu/check-inst-smoke-080t.log`，90/90）、`check-inst`（`.work/log/qemu/check-inst.log`，1012/945/62/5）、`check-modules`（`.work/log/qemu/check-modules-080t.log`）均由 Makefile 的 `DADAO_TEST_PROFILE=node` 行实际执行；`check-arch`/`check-arch-smoke` 的 Node 行已落 Makefile，但 **`check-arch-smoke` 第 [2/2] 步（`min_rom_probe_046t`，`DADAO_TEST_PROFILE=node`）因第 [1/2] 步 5 红 `exit $rc` 从未执行**（Makefile 显式 fail-fast），故不声称 step2 已跑；Node arch 证据来自同一 env 的手动 044t/integ039t 执行并留日志，`check-arch` 亦因 arch-smoke 红未进入 13 探针循环。
- **返工复跑 rc（返工后）**：`run.sh` 36/36 rc=0；`--inject` 1/1 rc=0；`check-inst-smoke` rc=0（90/90）；`check-interface` rc=0（90/90）；`check-inst` rc=2（1012/945/62/5）；`check-arch-smoke` rc=2（5/10）；`check-arch` rc=2（停在 arch-smoke）；`check-inst-smoke`/`check-modules` 的 Node 行已实际执行。
- **返工新增文件**：`.work/evidence/QEMU-080t/hmon_probe.py`（4 模式 hmon-context 证据）、`.tao/knowledge/issues.yaml`（ISS-340）。
- **issue 登记**：`ISS-340`（spec §6 Node VA/页表口径 vs identity 实现）已写入 `.tao/knowledge/issues.yaml`（open，`resolved_by: null`）。

**收尾结论（architect，2026-11-03，第 2 轮 reviewer Accepted）**：本任务自身红 **0**；非阻断 finding ①–④ 已处置：① `## 用户授权` 收录 `check-arch` 原话「登记 BLOCKED（推荐）」并把「5 个 `m5_perm_*`」更正为 **4 个 `m5_perm_*` + `m5_trap_escape`**；② 遗留①改按实测 **43 条 `profiles:[tiny]` + 19 条 Node 移交模型**重写，BLOCKED 依据改为任务书 R3/R5 预授权 + 上文原话；③ 明示 `check-arch-smoke` 第 [2/2] 步因第 [1/2] 步 5 红 fail-fast **从未执行**（不声称已跑）；④ `run.sh` 的 smon 断言降级为「cfx02 寄存器文件可见」，smon SRAM 窗口由 `geom_check`（SMON_BASE/SMON_CFX_BASE/MON_SRAM_SIZE）独立断言。状态置 `已验证`，`milestones.md` 流水行同步。本分支不 merge master、不 push。

**同步 master 后 L1（architect，2026-11-03 10:2x）**：`git merge master` rc=0，**无冲突**（`milestones.md` 自动合并；QEMU-080t 行按时间倒序置顶，`check-milestones-fresh` PASS）。`make -k check` **rc=2**，唯一红 `check-knowledge-refs`（**92** 悬空 `.work/**`，**0 条属本任务**；= worktree 缺历史 evidence 87 + master 新入 GEM5-014t 证据路径 5，主树同检查 rc=1/7 ⇒ 基线红）；其余 L1 目标全 PASS：`check-patch-tree` 278 patches、`check-tasks` 241 条、`check-interface` 90/90、`check-milestones-fresh` 30 行、`check-component-changelog`/`check-source-state` 等。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 `cpu.h`/`cpu.c`/`helper.c`/`dadao-machine.c` 与驱动改动，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 2 GiB 常量 `2048*1024*1024` 以 int 求值为负，QEMU mmap 失败（实测 `Cannot allocate memory`，strace size=2^64−…） | ✅已修 | `DADAO_RAM_SIZE`/`DADAO_NODE_RAM_SIZE` 改 `2048ULL * 1024 * 1024`；`check_interface` product 解析支持 ULL 后缀 | `build-qemu` rc=0；`profile=node` 启动/证据 32/32 |
| F2 `check_interface` 的 `RESET_PC` 正则命中注释里的 `DADAO_RESET_PC macros` | ✅已修 | 五个几何正则加 `#define\s+` 锚定（不降断言强度） | `check-interface` 90/90 PASS |
| F3 移除 legacy 后 `DADAO_PROFILE()` 未设 profile 时仍回退 `dadao_profile_legacy`（链接失败/空指针） | ✅已修 | 回退改 `dadao_profile_node`；`extern` 与 profile 表同步 | `build-qemu` rc=0（user-mode 构建同编） |
| F4 Node ELF 的 `.rom` 空段可能被范围检查拒绝 | ✅已修（防御） | `p_memsz == 0` 的 PT_LOAD 跳过范围检查 | Node ELF 证据 rc=0x2A |
| F5 Node 驱动仍走 `-bios` 4 MiB（079 的 arch-smoke 0/10 根因） | ✅已修 | `run_m5_e2e`/`run_qemu_test` 在 node 下用 `bootrom-image=`；Makefile 传 step5 镜像 | arch semihosting 5/5、inst smoke 90/90 |
| F6 证据脚本注入自检曾"两支同结果"（只校验还原后 rc） | ✅已修 | 注入函数显式要求 `normal->injected` 变化（129→1、64→135）且还原回绿 | `run.sh --inject` 1/1 PASS |
| F7 `power.S` 调用目标错（`BOOTROM_BASE` vs `RESET_PC`） | ✅已修（用户授权） | 两处 `LOAD_ADDR` 改 `RESET_PC + 0x2000/0x2400` | 修复前 rc=1/死循环；修复后链 e2e、arch/inst 全跑通 |
| F8 Node 下测试体无法访问 cfx4/cfx17（per-cfx 掩码）——A/D/TLB/fault 不能由本任务证据覆盖 | ⏸延后 | 不修；登记 BLOCKED（需 hmon 移交 cfx3 或预装向量） | 成功证据仅覆盖 PTE/SPF/超页/普通页/SP；其余列遗留 |


#### 第 1 轮 reviewer 验收

**重跑（本人执行，workdir=本任务 worktree；日志 `/tmp/opencode/DADAO-v5/QEMU-080t-review/`，退出码均取 `cmd; echo $?`）**
- `.work/evidence/QEMU-080t/run.sh` → `== 32 checks, 0 failed`，**rc=0**（与完成区 32/32 一致）；`--inject` → `ram 1GiB normal_rc=129 injected_rc=1`、`SPF=0x00 boot rc=135`、还原 `129/64`，`== 1 checks, 0 failed` **rc=0**，`md5sum -c` 全 OK，`git status --porcelain -uall` 审前/审后 13 行逐行一致。
- **独立注入**（非 engineer 自检）：`cp` bootrom→`.preinject`+md5 → 把复位窗口 `0x3f0000` 起 4 KiB 清零 → 同一 `run.sh` **12 FAIL/32、rc=1**（PTW body=137、hmon/entry/PTBR absent、4 MiB accepted=137、5 条 semihosting FAIL）→ `cp` 还原+md5 OK → **0 FAIL、rc=0** 回绿。
- `make check-interface` **rc=0、90/90**（5+36+41+8）、无 `DEFERRED`、Node 5 项 `DADAO_*` PASS；`make check-tasks` **rc=0**；`make check-tset-embench-smoke` **rc=0**。
- `make check-arch-smoke` **rc=2、`Results: 5/10 passed, 5 failed`**（semihosting 5/5 绿；FAIL=`m5_perm_reserved_illi/mask_cfxperm/unimpl_cfxreg/badcombo_cfxreg` + **`m5_trap_escape`**）——与完成区 5/10 一致。
- `make check-inst` **rc=2、`1012 total, 945 passed, 62 failed, 5 deferred`**（与完成区逐字一致；全量明细 `.work/log/qemu/check-inst.log`）。
- `make -k check`（L1 全量，非 -k 会在首个红停止）**rc=2**：红仅 `check-patch-tree`（**gem5 26 项**，本任务未碰 gem5，079 已归 GEM5-014t）与 `check-knowledge-refs`（**87 悬空 `.work/**`**，worktree 缺历史 evidence；主树同检查 rc=1/7 悬空 ⇒ 基线红）；`check-milestones-fresh`/`check-component-changelog`/`check-components`/`check-interface` PASS。
- `make check-modules`（L2）**rc=2** 停在 arch-smoke，之前 `check-inst-smoke` **90/90 PASS**；`make install-host` **rc=0**；`make check-source-state` **rc=0**（`qemu: OK HEAD=c79f328 count=1 clean=True`）；两 `qemu-system-dadao` md5 同 `0949cb1f85df0cf04fbd7ec6b441129e`。
- 边界/几何我自测：bootrom `4 MiB±4 B` 均 rc=1 且 `expected exactly 4194304`（覆盖验收 2「±1 页」）、`-bios`+`bootrom-image` rc=1；`cpu.h` vs spec §1.1（0 / 2 GiB / `0xffffffc00000` / 4 MiB / `0xffffffff0000`）逐项相等；hmon/smon/pmem `0x0fff_0000_0000`/`0x0bff_0000_0000`/`0x47ff_0000_0000` + 64 KiB 我手工核对相等（**但证据脚本未断言**，见阻断 4）。

**约束核验**：改动 13 文件全在允许清单内；`tests/**` 仅 `power.S`（实改 3 行=2 常量+1 行注释，授权原话「2 行修复」）与未决 3 授权的 `machine-profiles.yaml` 数据回填；`spec/contracts/adr/gem5/manifests/discussing.md` 未动；组件树 base+1 `c79f328` 且 `git status` 干净；未决 3 跨模块（Makefile/`tools/testcases`）**任务书无用户原话落盘**（硬约束 9，需 architect 追认；批次授权 2026-11-02 已列本任务）；完成区 8 行 ≤30、状态 `待验收`、changelog `## M11` 条目在位；headline 数字与真实输出全部一致，无伪造。

**阻断项**
1. **验收 7 `make check-arch` 未执行**：我直跑 `min_rom_probe_044t`、`min_rom_probe_integ039t` **全红**（rc=1；根因 `raw kernel …16 bytes, smaller than the reserved prefix of 256 bytes`，缺省已切 tiny；integ039t `0/37`），而基线 `make check-arch` rc=0（INTEG-051t 2026-10-31）⇒ 本任务缺省切换引入的 L3 红：未跑、未逐条归因、未登记 BLOCKED（`新发现④` 仅泛述且根因与实测不同）。
2. **验收 4/5 未达且 BLOCKED 未获批**：PTW 越界/权限→`cfx_ptw`、A/D 更新、TLB 失效、`cfx17` SRAM+DMA、`cfx15/18` 实测可达、`cfx5 ⇒ 0x84` 均无证据（脚本只断言「cfx 注册可见」）；`遗留②` 自开 BLOCKED，任务书用户授权区无对应原话。
3. **arch-smoke 5 红的 BLOCKED 覆盖不实**：实测 FAIL = **4×`m5_perm_*` + `m5_trap_escape`**（`tests/arch/umon/` 只有 4 个 `m5_perm_*.s`），完成区与用户授权原文均按「5 个 m5_perm_*」计 ⇒ `m5_trap_escape` 不在已批清单内。
4. **证据脚本缺陷**：`arch_semihosting` 用 `grep -q "PASS  $c"`，`PASS  m5_semi_writec/write0` 行会命中 `m5_semi_write` 断言（我已复现）⇒ 单例失败可假绿，FAIL 路径不独立可达；且验收 1 明列的 hmon/smon/pmem SRAM 等值断言缺失（值我已核对相等）。

**非阻断 finding**：① 完成区 62 条分类与实测不符（实测 profile 不适用 43 / fault 模型 19；完成区 30/32 把 13 条 profile 不适用算进「hmon 移交」）；② L1 实为 2 红（含 `check-knowledge-refs` 87），「仅 check-patch-tree」因非 `-k` 提前停止未见第二项；③ spec §6 冲突未登记 `issues.yaml`（R1）；④ 完成区「用户同意另立任务」范围超出授权原文；⑤ `check-arch-smoke` step2 的 `DADAO_TEST_PROFILE=tiny` 因 step1 红从未执行；⑥ `smon retained` 与 `cfx02 registered` 用同一条 grep（非独立断言）。

**环境处置（非交付物缺陷，已披露）**：worktree `.work/build/llvm` 半棵树（前次 reviewer 07:30 遗留 + 本人 chain1 续建）使 `check-install-tools` 13/48 红 ⇒ arch-smoke/L2 曾假红；我 `mv` 为 `.work/build/llvm.partial-review-20261103` 并 `make install-cfx-aliases` 后复跑取真值；门控须 `LLVM_BUILD=/mnt/tao/DADAO-v5/.work/build/llvm` 等覆盖（否则在 worktree 本地重建 LLVM，根盘 99%、仅 1.7 G 可用）。审后快照与审前逐行一致，关键文件 md5 全 OK。

**判决：Needs Revision**（阻断 1–4；返工后开第 2 轮复验）

#### 第 2 轮 engineer 自审（返工）

| reviewer finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 1 L3 `check-arch` 红；需显式 Node / 复跑到 rc=0 或请裁定 | ✅部分修复 + 用户裁定 BLOCKED | Makefile 的 `check-arch` 探针与 `check-arch-smoke` 第 2 步加 `DADAO_TEST_PROFILE=node`；044t/integ039t Node 现场保留 | `node-044t.log`（0x81）、`node-integ039t.log`（1/37）；用户原话「登记 BLOCKED（推荐）」；`ISS-340` 另记 spec 冲突 |
| 2 验收 4/5 无证据（cfx_ptw/A-D/TLB/cfx17/cfx15/18/cfx5） | ✅已修 | 新增 `hmon_probe.py`：自定义 BootROM（真实 power/smon + 合成 hmon=真实 PTW 建立+测试体，cfx3/hypv）四模式 | `run.sh` 36/36；`success` rc=0（cfx17 DMA+cfx15/18+A/D+TLB invalidate）、`nwperm`/`dgtrap` rc=0（cfx_ptw）、`cfx5` rc=0x84 |
| 3 arch-smoke 5 红计数不实 | ✅已修 | 完成区返工更正：4×`m5_perm_*` + `m5_trap_escape`；说明 user-mode vs Node hypv 边界 | `check-arch-smoke` 日志 5/10，逐名列出 |
| 4 证据脚本 `grep` 前缀误配；缺 hmon/smon/pmem 几何 | ✅已修 | `grep "  PASS  $c  expected="` 精确匹配；geom 增加 HMON/SMON/PMEM + MON/PMEM SRAM size 断言 | `run.sh` 36/36；`m5_semi_write`/`write0` 均真实 PASS |
| 5 62 分类 43/19；L1 第二红；spec 冲突 issue；越界授权；step2 环境行 | ✅已修 | 完成区返工更正；L1 增报 `check-knowledge-refs` 87 悬空；`issues.yaml` 加 ISS-340；越界逐项列授权原话；环境行执行日志 | `check-inst.log` 1012/945/62/5（43/19）；`make -k check` 两条红；`check_issues` PASS；Makefile 行与运行日志 |
| F9 `hmon_probe.py` 初版把立即数当寄存器（`and.o`/`st.o` 12-bit 溢出） | ✅已修 | 掩码先 `load_rd` 再寄存器 `and.o`；页内偏移 >0xFFF 改用 `add.si` 改基址 | 四模式 rc 0/0/0/0x84 |

#### 第 2 轮 reviewer 验收（增量复验，2026-11-03）

**重跑（本人执行，rc 取 `cmd; echo $?`；日志 `/tmp/opencode/DADAO-v5/QEMU-080t-review/`）**
- `run.sh` **36 checks / 0 failed，rc=0**；`run.sh --inject` **1 check / 0 failed，rc=0**（ram 129→1、SPF 135、还原 129/64）——与完成区一致。
- `hmon_probe.py` 四模式**真实**（我核）：`success` 无 fault handler、4606 条 PC 采样、cfx17 DONE / cfx15=0x0F / cfx18=0x12 / A→D 逐项 `check_eq`（失败码 0xE1–0xE6）；`nwperm`、`dgtrap` 各 **1 次 PC=HMON+0x1900**（cfx_ptw 向量真跑，cause 1<<13 / 1<<20）；`cfx5` **1 次 PC=HMON+0x1800 且 rc=0x84**（cause 1<<2）⇒ 验收 4/5（A/D、TLB invalidate、越界/权限进 `cfx_ptw`、cfx17 DMA、cfx15/18、`cfx5⇒0x84`）为真实执行，非空转。
- `make check-interface` **rc=0（90/90、无 DEFERRED）**；`check-tset-embench-smoke` **rc=0**；`check-inst-smoke` **rc=0（90/90）**；`check-source-state` **rc=0**（`qemu: OK HEAD=c79f328 count=1 clean=True`）；`check-tasks` **rc=0**；`check_issues` **rc=0**（ISS-340 open / `resolved_by: null`）。
- `make check-arch-smoke` **rc=2、5/10**：5 条 semihosting 全绿；FAIL = 4×`m5_perm_*` + `m5_trap_escape` ⇒ **计数准确**。
- `make check-inst` **rc=2、1012 total / 945 passed / 62 failed / 5 deferred**；实测分类 **profile 不适用 43**（aip-si1/ctrl-br10/ctrl-call1/ctrl-jump1/mem-ra4/mem-rb4/mem-rd22）+ **Node 模型 19**（12 行 `0xB7`、6 行 `code 0x01`、1 行 UNMAPPED↔UNDI）⇒ **43/19 与完成区逐项吻合**。
- `make check-arch` **rc=2**（依赖 arch-smoke 红，13 探针未进循环，与披露一致）；现场 `.work/log/arch/node-044t.log` 13 处 `0x81`、`node-integ039t.log` `1/37` 与完成区一致 ⇒ BLOCKED 记录成立（任务书 L3 条目含用户原话「登记 BLOCKED（推荐）」，13 探针归 TESTCASES）。
- `make -k check`(L1) **rc=2，恰两红**：`check-patch-tree` 26（全 gem5）+ `check-knowledge-refs` 87 悬空（**0 条属 QEMU-080t**；主树同检查 rc=1/7 ⇒ 基线）；`check-milestones-fresh`、`check-component-changelog`、`check-interface` PASS。`make check-modules`(L2) **rc=2** 停在 arch-smoke（`check-inst-smoke` 先绿）。另单独跑：`check-unit` **rc=2**（lit **161/162**，唯一 `mcmodel.test` = LLD REL26 空输出，QEMU 步已执行成功，非 QEMU）、`check-tset-libc-smoke`/`check-tset-llvm-smoke`/`check-generator-sync` **rc=0**。
- gem5 红归类：本分支落后 master **3 提交**，`git diff HEAD master -- components/gem5` 含被报全部补丁文件（`inst.cc`/`isa.cc`/`SConscript`/`AtomicSimpleCPU.py`…）⇒ **基线/合成树**（GEM5-014t 补丁未同步到本分支），非本任务红。

**独立注入（与 engineer 的 `cpu.h` RAM / `hmon.S` SPF 均不同）**
- (a) `.dadao/tests/bootrom/step5/power.elf` ← `smon.elf` → `run.sh` **4 FAIL（hmon-context 全中）、rc=1**；`cp`+md5 还原。
- (b) `tests/shared/bootrom/step5/hmon.lds` `ORIGIN +0x1000` → **rc=1**，`success` 模式**行为级**失败（`TimeoutExpired 30s`，body 落错地址挂死）⇒ 新断言非恒真；`cp`+md5 还原 → 复跑 **36/36、rc=0**。

**约束/体例**：完成区 5 字段块 5 行、含返工更正 **17 非空行（≤30）**；越界授权逐项落盘（`power.S` 原话 / 未决3+批次 / `check_interface` 仅正则）；ISS-340 入 `issues.yaml`（R1 闭环）；`grep "  PASS  $c  expected="` 精确（我复现 `writec` 行不再命中）；审前后 `git status` **14 行逐行一致**，`cpu.h`/`hmon.S`/`power.S`/bootrom/`hmon.lds`/`power.elf` md5 全 OK；`hmon_probe.py` 落 `.work/evidence/`（未跟踪，符合证据落点）。

**非阻断 finding**：① `## 用户授权` 区未收录 check-arch 的新裁定原话（仅在完成区 L3 条目），且该区仍写「5 个 `m5_perm_*.s`」（实为 4 + `m5_trap_escape`，完成区已更正）；② `遗留①` 仍写「5 个」「用户同意另立任务」，inst 62 的 BLOCKED 依据实为任务书 R3/R5 预授权而非单独问答；③ `check-arch-smoke` step2 已改 `node` 但因 step1 红从未执行；④ `smon retained` 与 `cfx02 registered` 仍同一条 grep（非独立断言）。

**环境处置（已披露）**：注入(b) 期间 arch-smoke 超时用例遗留的 4.2 GB `-d cpu` 日志 + 注入挂死日志把根盘写满（剩 4 KB），致一次 `run.sh` ENOSPC 假红；我删除这些**临时日志**（`/tmp/opencode/QEMU-080t/m5e2e/*.cpu.log`、`evidence/hmon/*.log`）释放 5 GB 后复跑回绿（现 4.6 G 可用）；`.work/source` 11 组件、qemu `c79f328` 干净未受影响；`.work/build/llvm.partial-review-20261103`（20 G，第 1 轮移开的半棵 LLVM）仍在原处。

**判决：Accepted**——本人重跑下**无假绿、计数全对**，**本任务自身红 0**；剩余红全部为「用户已裁定 BLOCKED」（arch 5 红、inst 62、`check-arch` 13 探针）与「外部红」（分支落后 master 的 gem5 补丁 26、worktree 缺历史 evidence 的 knowledge-refs 87、LLD `mcmodel`、079 基线 lit/codegen）。
