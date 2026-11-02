# QEMU-080t: Machine-v5-Node 系统机

**模块**：qemu
**项目里程碑**：M11
**依赖**：`QEMU-079t`（profile 运行时化与 Tiny；必须先验收，二者改同一组 `cpu.h`/`cpu.c`/`helper.c`，串行）、`SPEC-183t`、`TESTCASES-091t`、`QEMU-081t`（页 64 KiB）
**状态**：待开始

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
