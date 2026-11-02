# QEMU-079t: Machine-v5-Tiny 系统机

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-183t`（几何/cfx/semihosting 真源）、`TESTCASES-091t`（测试资产与 profile 表）、`QEMU-081t`（页大小 16 位/64 KiB；与 `target/dadao/cpu-param.h` 同文件，须串行并在其之后 rebase）；下游 `QEMU-080t`
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；组件源树 `.work/source/qemu` 为 base+1 单提交、`git status` 干净；实现落任务分支 `QEMU-079t`，不 merge、不 push）

## 用户已定口径（2026-11-02/03，摘要）

- Tiny：地址高 6 位恒 `0x3F`；**不实现任何 cfx（含 `cfx_power`）**；不能进入 `user`；**允许 semihosting**（`trap` 只作陷入宿主的开关，不算 cfx 类）。
- BootROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`；SRAM 8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`。
- raw `-kernel` 基址 `0xffff_ff01_0000`、前 `0x100` 全零、应用入口 `0xffff_ff01_0100`、`SP=0xffff_ff7e_ff00`；ELF 的 crt/stub 在 ROM、应用入口同一；raw/ELF 统一入口与 SP。
- 只跑非 cfx `inst` + `embench` + `picolibc`；不跑 `arch`；无 hmon/PTW。
- 本任务只改 QEMU system（组件补丁 + QEMU 测试驱动），不改 `gem5/`、`spec/`、`tests/**`（测试资产归 `TESTCASES-091t`）。

## 现状与问题根源

1. 现有 `dadao-m1` 是「单一几何」：`target/dadao/cpu.h` 的 `DADAO_RAM_BASE=0xFC00_0000_0000`（16 MiB）、`DADAO_ROM_BASE=0xffff_fffc_0000`（256 KiB），并由 `cpu.c`/`helper.c` **编译期**直接使用；`hw/dadao/dadao-machine.c` 只建一份 RAM/ROM。
2. 该几何已被 `SPEC-183t` 的两 profile 取代；Tiny 的 SRAM 在 cfxha 63 段内，与 Node 的 PA RAM 不可能共用同一组常量。
3. Tiny 的装载、cfx 关闭、fault 直出退出码、`-bios`/`bootrom-image`/raw/ELF 四条路径都不是现实现状；`-kernel` raw 目前固定装到 RAM 基址、入口=RAM 基址。
4. `check_interface_alignment.py` 以 **Node** profile 的 `qemu_*` 字段核对 QEMU 宏，故 Node 常量必须留在 `cpu.h` 的 canonical 宏名上；Tiny 必须走独立常量/运行时 profile，不能覆盖 Node 口径。

## 目标

1. 在 QEMU system 中引入 **运行时 machine profile**（几何 + cfx/PTW 能力 + raw 装载参数），由机器属性选择；现有 `dadao-m1` 在 `QEMU-080t` 前保持 legacy 行为，避免打断 arch 门控。
2. 新增 **Tiny profile**：64 KiB BootROM、8 MiB SRAM、复位/装载/cfx/fault/semihosting 全部按 `spec/Machine-v5` 落地。
3. Tiny 的真实 QEMU 执行闭环：非 cfx inst + embench + picolibc，证据可重跑、可注入失败。
4. 不新增/不改契约；实现与 `spec/Machine-v5 §1/§1.1/§1.2/§2/§3/§4/§5/§6` 逐条对齐。

## 接口规范

### 0. 机器与 profile 选择（规划裁定，待用户确认）

- 机器名保持 **`dadao-m1`**（`check_interface_alignment.py` 的 `MACHINE_TYPE_NAME("dadao-m1")` 不变）。
- 新增机器属性 **`profile`**：本任务取 `legacy`（缺省）与 `tiny`；`QEMU-080t` 再增 `node` 并把缺省改为 `tiny`、移除 `legacy`。
- 选择优先级：显式 `-machine dadao-m1,profile=<name>` > 环境变量 `DADAO_TEST_PROFILE`（与 `tests/shared/machine-profiles.yaml` 同名，供现有驱动零改动接入）> 缺省值。环境变量回退须在 `-machine help`/启动日志中可见，禁止静默。
- Tiny 的 L2/L3 system 目标由 `Makefile` 的该目标环境行设 `DADAO_TEST_PROFILE=tiny`（不改测试脚本/资产）；显式 `profile=` 始终优先。
- 不以“图像大小/地址猜测 profile”。
- 备选（若用户否决属性方案）：新增 `dadao-m1-tiny` 独立 MachineClass，`dadao-m1` 保持 legacy/Node；驱动以机器名选择。两方案验收等价，不得混用。

### 1. 地址空间与复位（Tiny）

| 区域 | 起始 | 大小 | 访问 | 说明 |
| --- | --- | --- | --- | --- |
| BootROM | `0xffff_ffff_0000` | 64 KiB | RX | 复位 = 基址；全部为复位/启动 stub，无 image index table |
| SRAM | `0xffff_ff00_0000` | 8 MiB | RWX | 唯一可写存储器；应用 `.text/.rodata/.data/.bss` 由宿主 loader 装入 |
| 其余 cfxha 63 | — | — | fault | 访存/取指 ⇒ `CFXMEM`（`0x81`），不得 `0x87` |

- `addr[47:42] == 0` 且 `ptw_enable=0` ⇒ `CFXMEM`（`0x81`）；Tiny 无 cfx4，`ptw_enable` 不可写。
- 不建 PA 0 别名、不建 hmon/smon/pmem SRAM；同一存储不设第二地址。
- 复位 `PC=0xffff_ffff_0000`、`rb0` 同值；`ptw_enable=0`、`inner_run_mode=hypv`（名义）、`inner_cfx_code=63`；Tiny 不改变模式、不能进入 `user`。

### 2. 装载路径（Tiny）

- **`-bios`（legacy 64 KiB 窗口）**：flat trampoline 装到 `0xffff_ffff_0000`，复位执行；Tiny 的 raw 测试用此路径（trampoline 设 SP 后跳 `0xffff_ff01_0100`）。不得与 `bootrom-image` 同时给。
- **`bootrom-image`**：必须**恰好 64 KiB**，装到 ROM 基址；长度不符 ⇒ 装载期错误、非零退出。
- **raw `-kernel`（非 ELF）**：装到 `0xffff_ff01_0000`；镜像长度 ≤ `8 MiB - 0x100`；**前 `0x100` 字节必须全零**（保留区），否则装载期错误；入口固定 `0xffff_ff01_0100`。raw 路径要求 `-bios`（无 `-bios` ⇒ 明确错误，不猜入口）。
- **ELF `-kernel`**：`PT_LOAD` 允许落在 **ROM 或 SRAM**（Tiny 的 crt/stub 在 ROM）；仍要求 `p_filesz ≤ p_memsz`、`p_vaddr == p_paddr`、段区间在 profile 内；`e_entry` 在 ROM 时按 ELF 入口执行（crt 设 SP 后跳应用入口）。落在区间外 ⇒ 装载期错误。
- **SP 不由机器设置**：由 ROM stub / `minimal_crt0` / picolibc `__start` 设置；验收以 guest 观测值为准（`rb1`/栈上写入）。

### 3. cfx / 模式 / 异常（Tiny）

- 所有 cfx 寄存器访问（`cfx2rd`/`cfx2rc`，含 `cfx_power`/`cfx4`/`cfx17`/时间类）⇒ `CFXREG`（退出码 `0x84`）。
- `trap`：`immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）**先判 semihosting**，与 `cfxha` 无关，正常服务并 `IP += 4`；其余 `trap` ⇒ `ILLI`（`0x88`），不进入向量、不做模式切换。
- `escape` ⇒ `ILLI`；`switch_run_mode`/`switch_cfx_mask` 写入即 cfx 寄存器 ⇒ `CFXREG`，因此无法进入 `user`。
- 机器 fault **直接映射退出码**（`ADR-0004 D5`）：`CFXMEM=0x81`、`ILLI=0x88`、`MALIGN=0x8C` 等；Tiny 无异常向量、无 hmon/smon 路径。
- `semihosting` 控制台 + `SYS_EXIT`/`SYS_EXIT_EXTENDED` 闭环，服务集与 `spec/Machine-v5 §5.3` 的 25 项一致。

### 4. QEMU 实现落点（profile 化）

- `target/dadao/cpu.h`：新增 profile 描述（几何、`kernel_base`/`kernel_entry`、`cfx_enabled`、`ptw_supported`、power 段 fault 码）；**canonical 宏 `DADAO_RAM_BASE`/`DADAO_RAM_SIZE`/`DADAO_ROM_BASE`/`DADAO_ROM_SIZE`/`DADAO_RESET_PC` 保持 Node 口径**（供 `check_interface` 与 `QEMU-080t`），legacy/tiny 用独立常量。
- `target/dadao/cpu.c`：CPU env 保存 `const DadaoProfile *prof`；machine 在 `qdev_new`/`qdev_realize` **之前**设置（reset 依赖）；reset PC/几何不再读固定宏。
- `target/dadao/helper.c`：`tlb_fill` 的 RAM/ROM/内部空间判定、fault 分类、cfx 存在性判定全部改读 `env->prof`；Tiny 的 power 段越界 ⇒ `CFXMEM`。
- `hw/dadao/dadao-machine.c`：按 profile 建 RAM/ROM（Tiny 不建 alias/mon/pmem）；`-bios`/`bootrom-image`/raw/ELF 四条装载路径按 §2；raw 前缀零校验、入口固定；ELF 允许 ROM 段（用上游 `load_elf`；ROM 写保护仍由 TLB fill 的 store→`ILLI` 保证）。
- 补丁一律经 `python3 tools/infra/make_patch.py qemu` 重导出；源树收敛 base+1 单提交。

## 实施清单

- **A. profile 基础**（`cpu.h`/`cpu.c`/`helper.c`/`dadao-machine.c`）：profile 结构、属性 `profile`、env 指针、canonical 宏保持 Node 值；legacy profile 逐字段等于当前行为（回归基线）。
- **B. Tiny 机器**：RAM/ROM/复位/fault 分类；不建 alias/mon/pmem；`-bios` 64 KiB、`bootrom-image` 精确 64 KiB。
- **C. Tiny 装载**：raw（基址 `0xffff_ff01_0000`、前缀零、入口 `+0x100`）与 ELF（ROM+SRAM 段、`e_entry`）。
- **D. Tiny cfx/异常/semihosting**：cfx 全 `CFXREG`、非 semihosting `trap/escape` `ILLI`、fault 直出、semihosting 25 服务闭环。
- **E. 驱动最小连带**（跨模块，见「未决」）：`Makefile` 的 Tiny system 目标环境行加 `DADAO_TEST_PROFILE=tiny`（不改测试脚本/资产/期望值）；arch 目标保持缺省 legacy，直至 `QEMU-080t`。
- **F. 证据/门控**：`.work/evidence/<任务ID>/run.sh` 一键重跑，逐条取命令自身 rc；注入/还原用 `cp` + `md5sum -c`。

## 验收标准

1. **profile/几何**：
   - `qemu-system-dadao -M dadao-m1,profile=tiny -bios <trampoline> -kernel <raw>` 可启动；不带 `profile` 时行为与开工前 legacy 基线一致。
   - Tiny 常量与 `spec/Machine-v5 §1.1` 逐项相等（BootROM 首尾、SRAM 首尾、复位、raw 基址/入口/SP），由证据脚本从 spec 派生断言。
2. **ROM**：`bootrom-image` 64 KiB 接受；63 KiB/65 KiB ⇒ rc≠0 且报长度错误；guest 写 ROM ⇒ `0x88`。
3. **raw**：镜像装到 `0xffff_ff01_0000`；前 `0x100` 非零 ⇒ rc≠0；入口为 `0xffff_ff01_0100`（guest 观测 IP/PC）；无 `-bios` ⇒ rc≠0。
4. **ELF**：Tiny ELF（crt 在 ROM、应用在 SRAM）装载并执行；`e_entry` 在 ROM；段越界 ⇒ rc≠0；`-bios` 与 `bootrom-image` 同时给 ⇒ rc≠0。
5. **cfx/模式**：`cfx2rd/cfx2rc` 任一 cfxha ⇒ `0x84`；非 semihosting `trap`/`escape` ⇒ `0x88`；`addr[47:42]=0` 访存/取指 ⇒ `0x81`；cfxha 63 越界 ⇒ `0x81`；无路径进入 `user`。
6. **semihosting**：`trap <any cfxha>,0x3FF00` 的 `SYS_WRITE0`/`SYS_EXIT`/`SYS_EXIT_EXTENDED` 实测；服务集覆盖与 `spec/Machine-v5 §5.3` 一致（25 项，按表派生，不写死条数）。
7. **真实执行**：
   - 非 cfx inst：`make check-inst-smoke`（L2 代表集）+ 至少一轮**全量非 cfx inst**（可用 `make check-inst`，L3 单目标；预计 20–40 min，启动前申报耗时）；失败项逐条归因。
   - `embench`：`make check-tset-embench-smoke`（Tiny）rc=0，至少一个完整 benchmark 输出正确。
   - `picolibc`：`make check-picolibc-tests`（Tiny 代表集）rc=0。
   - 不跑 `arch`（Tiny 无 arch）。
8. **L1/L2**：`make check`（L1）rc=0；`make check-modules`（L2）rc=0。arch 相关目标在 `QEMU-080t` 前仍走 legacy，必须保持绿；任一红项给出基线证据/归因。
9. **构建/补丁**：`make build-qemu JOBS=8` rc=0；`make install-host` rc=0；`md5sum .work/build/qemu/qemu-system-dadao .dadao/cross-toolchain/bin/qemu-system-dadao` 两哈希一致；`make check-patch-tree`、`make check-source-state` rc=0；源树 diff 仅本任务文件。
10. **反例可达 FAIL**（`cp` 备份 + `md5sum -c` 还原，禁 `git checkout/restore/stash`）：
    - 把 Tiny SRAM 大小临时改为 4 MiB ⇒ 证据脚本的几何断言/inst smoke 至少一项 FAIL；还原后回绿。
    - 把 raw 入口改回 `kernel_base` ⇒ raw 用例 FAIL；还原后回绿。
11. **体例/台账**：`components/qemu/changelog.md` 在 `## M11` 下追加 `- **2026-11-03 \`QEMU-079t\`**` + 摘要 + `执行者：engineer`；`make check-component-changelog`、`make check-milestones-fresh`、`make check-tasks` rc=0；完成区 ≤30 行；状态 `待验收`。
12. **诚实**：证据落 `.work/evidence/<任务ID>/`（`run.sh`、`run.EXIT`、日志），复杂输出留 `.work/log/qemu/`；失败保留现场并按「失败处置」推进；**不伪造 QEMU 执行**。

## 未决（下发前需用户裁定）

1. **profile 选择机制**：采用「`dadao-m1` + `profile` 属性 + `DADAO_TEST_PROFILE` 回退」，还是「`dadao-m1-tiny` 独立机器名」？本册按前者写；后者需同步改驱动机器名。
2. **跨模块最小连带**：为让 Tiny 的 L2/L3 目标真正跑在新 profile 上，需要在 `Makefile` 的 system 目标环境行加 `DADAO_TEST_PROFILE=tiny`（不改 `tests/**` 资产/期望值、不改测试脚本语义）。是否授权？若不授权，本任务把该项登记 BLOCKED，L2 机器选择由 `TESTCASES` 另立任务解锁。
3. **全量 inst 是否纳入本任务验收**（验收 7 的 L3 单目标），或只要求 L2 代表集 + `/complete` 时跑全量。

## 文件范围

- 允许：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`、`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（及必要的 `hw/dadao/{Kconfig,meson.build}`）、`components/qemu/changelog.md`、`.work/source/qemu/**`（组件工作树，非 v5 跟踪）、`tools/qemu/**`（QEMU 测试驱动）、`Makefile`（仅 Tiny system 目标的 `DADAO_TEST_PROFILE=tiny` 环境行，未决 2 授权时）、本任务书、`.tao/knowledge/milestones.md`、`.work/evidence/<任务ID>/`、`.work/log/qemu/`、`/tmp/opencode/QEMU-079t/`。
- 禁止：`tests/**`、`tools/testcases/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、其它 `components/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`。

## 风险

- **R1 几何 profile 化面大**：`DADAO_RAM_BASE` 等宏在 `cpu.c`/`helper.c` 多处派生；漏改会导致 Tiny 静默走 Node/legacy 地址。缓解：canonical 宏保持 Node 值 + 运行时 `env->prof` 全量替换 + 源扫描断言「运行时路径无直接 `DADAO_RAM_BASE/ROM_BASE` 使用」。
- **R2 reset 时序**：machine 在 CPU realize 前设 profile；若在 reset 后设置，`rb0/PC` 仍是旧值。验收用 guest 观测 `PC/rb0`。
- **R3 ROM ELF 装载**：上游 `load_elf` 对只读 ROM 的写入方式需现场确认；若不可写，用 `rom_add_elf_program`/临时 RAM 后置只读，不得放宽 guest 写权限。
- **R4 与 QEMU-081 同文件**：`cpu-param.h` 页大小改动先合入；本任务 rebase 后再构建。
- **R5 L2 arch 基线**：QEMU-079 期间 arch 仍走 legacy；任何 arch 红项须先证明与开工前基线一致，不得把 legacy 改动算作本任务修复。
- **R6 semihosting 与 cfx 判定顺序**：必须 semihosting 先于 cfx 存在性检查，否则 Tiny 的合法 `trap` 会被误判 `ILLI`。
- **R7 测试驱动跨模块**：未决 2 未授权时不得改 `Makefile`；只可改 `tools/qemu/**`。若 Tiny 目标拿不到 `profile=tiny`，L2 的 inst/embench/picolibc 会在 legacy 上失败，须登记 BLOCKED 而非改测试资产凑绿。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：`DADAO-0628` 的 QEMU 机器是单几何 + RISC-V 血统骨架，reset PC 与本机不同；v5 不复用其机器常量，只借鉴 `hw/dadao` 文件组织。落点 = 本任务的 profile 运行时化，不复制其代码。
- `QEMU-081t` 已记录 0628 的 `TARGET_PAGE_BITS=12` 与 `cfx_tlb_addr_size=65536` 自相矛盾；Tiny 页大小一律 64 KiB，不复用 0628 取值。

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
