# TESTCASES-091t: Machine-v5 Tiny/Node 测试资产迁移

**模块**：testcases
**项目里程碑**：M11
**依赖**：无（真实机器执行依赖后续 `QEMU-079t`/`QEMU-080t` 建册落地；本任务不依赖其代码）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（2026-11-02，测试机 RAM 映射）

以下为本任务自包含的参数真源（逐字记录见 `.tao/knowledge/discussing.md` 同日条目）：

- **Tiny**：BootROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`；SRAM 8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`；ELF/rodata 由宿主 loader 装入 SRAM，不塞 BootROM；无 hmon/PTW；覆盖 Embench 与完整 picolibc 测试集。
- **Node**：BootROM 4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`，复位向量仍 `0xffff_ffff_0000`；PA RAM 2 GiB `[0, 2 GiB)`；hmon 直接驱动 cfx_pmem、建立一级页表（4 个 512 MiB 超页，`SPF=0xFF`）并在 hypv 平台下跑测试；`power → hmon → smon` 路径保留给内核/smon 测试。
- **不做双映射**：旧高地址 RAM 测试直接迁移，不保留并行的旧 profile；不新立 ADR（修改 ADR-0004/0039/0040/0043 与 `spec/Machine-v5-测试机运行环境.md`，属 QEMU 任务链）。
- **运行模式**：用户 2026-11-02 明确 Node 在 hypv 下测试，测试本体按 H 模式执行；Tiny 是宿主装载的精简 FS 平台，不建立用户态异常路径。若某 case 明确要求 U-mode 特权语义，标 BLOCKED，不伪造期望值。
- **本轮边界（协调者下发）**：先改测试资产与 harness，不实现 QEMU/gem5；`llvm-ts`/tset 属 QEMU user/gem5 SE，不强行并入本任务。

## 现状与问题

- 旧几何硬编码散落：`tests/inst/base/*.yaml` 8 册约 160 处、`tests/arch/umon/*.s` 12 册、`tools/testcases/**` 约 51 个文件，以及 `tests/shared/linker/dadao-tiny.lds`、`tests/shared/bootrom/**`、`tests/shared/crt0/minimal_crt0.s`、`tests/unit/llvm/e2e/**`。
- 两个 profile 的 RAM 位于不同地址空间（Tiny 在 cfxha 63 内部空间且无 PTW；Node 在内存窗口 `addr[47:42]=0` 且 PTW 开启），**同一个绝对地址无法通用于两者**。
- 若按 profile 复制用例，会破坏 `case-ledger.tsv` 身份、`tests/*.yaml` 唯一性与覆盖率；因此必须"**同一 case ID 一份，profile 只决定地址/装载方式**"。
- 现有 `validate_vectors.py`、`build_test_binary.py`、`check_interface_alignment.py` 均把旧 RAM 基址/容量当常量。

## 目标

1. 建立**单一 profile 真源**（Tiny/Node 的 BootROM/RAM/入口/SP/装载/PTW 参数），测试资产与驱动只读取它，不各写一份。
2. `tests/inst`、`tests/arch`、`tests/shared/{bootrom,linker,crt0,runtime}`、ELF loader 与 `tools/testcases` 驱动按 profile 参数化；同一 case 只有一份。
3. 测试资产中**不再出现旧 0xFC00 高 RAM / 16 MiB / 256 KiB BootROM 字面量**；地址静态扫描可失败、可注入。
4. 静态门控（schema/validate/index/ledger/生成器同步/地址扫描/`check-no-residue`）全绿；真实 QEMU 执行明确 BLOCKED，交 QEMU 任务。
5. 不改 QEMU/gem5 实现、`spec/`、`contracts/`；`Makefile` 仅允许活跃路径/Node arch bootrom 同步，不改构建/测试语义；不新建平行测试树。

## 接口规范

### 1. profile 真源与读取

- 新增 `tests/shared/machine-profiles.yaml`（`tests/` 根下不得新增 `*.yaml`，故放 `shared/`），是测试侧**唯一**几何真源；`tools/testcases/lib/machine_profile.py` 提供 `load(name)`、`resolve(token)`、`all_profiles()`。
- 字段（两 profile 同构，缺一即错误）：
  - `bootrom_base` / `bootrom_size` / `reset_pc` / `bootrom_load`
  - `ram_base` / `ram_size` / `ram_end`
  - `entry` / `sp` / `host_loader` / `image_window`
  - `kernel_base` / `kernel_reserved`（raw `-kernel` 装载基址与前置零字节）
  - `ptw` / `hmon` / `smon` / `cfx` / `semihosting` / `arch` / `embench` / `picolibc` / `default_run_mode`
  - `exit_block` / `dump_base`（harness 私有区，由 `sp`/`ram_base` 派生）
- 选择方式：驱动统一接受 `--profile {tiny,node}`，环境变量 `DADAO_TEST_PROFILE` 可替代；**缺省 `tiny`**（不改 `Makefile`）。真实执行 Node 用 `DADAO_TEST_PROFILE=node make ...` 或显式参数。

### 2. 两个 profile 的取值（本任务约定；集中一处，变更只改 profile 表）

**Tiny（用户 2026-11-02 最终）**
- `bootrom_base=0xFFFF_FFFF_0000`，`bootrom_size=0x1_0000`（64 KiB），`reset_pc=0xFFFF_FFFF_0000`，`bootrom_load=bios-flat@base`
- `ram_base=0xFFFF_FF00_0000`，`ram_size=0x80_0000`（8 MiB），`ram_end=0xFFFF_FF7F_FFFF`
- raw `kernel_base=0xFFFF_FF01_0000`，`kernel_reserved=0x100`（前 0x100 全零），`entry=0xFFFF_FF01_0100`
- `sp=0xFFFF_FF7E_FF00`（与 raw/ELF 统一）；ELF 的 `minimal_crt0` 在 `0xFFFF_FFFF_0000`，`e_entry` 同址，设 SP 后跳 `entry`
- `host_loader=raw-kernel+elf-ptload`，`image_window=0x1_0000`
- **无任何 cfx（含 cfx_power）**、不能 user 模式；`cfx=false`、`semihosting=true`（trap 不算 cfx）、`default_run_mode=machine`
- `ptw=false`，`hmon=false`，`smon=false`；只跑非 cfx inst + embench + picolibc，不跑 arch
- `exit_block=0xFFFF_FF7E_0000`，`dump_base=0xFFFF_FF7E_8000`

**Node**
- `bootrom_base=0xFFFF_FFC0_0000`，`bootrom_size=0x40_0000`（4 MiB），`reset_pc=0xFFFF_FFFF_0000`（= base + `0x3F_0000`），`bootrom_load=bios-flat@base`
- `ram_base=0x0000_0000_0000`，`ram_size=0x8000_0000`（2 GiB），`ram_end=0x7FFF_FFFF`
- `entry=0x0000_0000_0010_0000`（**本任务初值，1 MiB**），`sp=0x0000_0000_7FFF_0000`（2 GiB − 64 KiB）
- `host_loader=elf-ptload`（VA=PA 恒等，PTW 开启），`image_window=0x1_0000`
- `ptw=true`，`hmon=true`（hmon 建立一级页表：4 × 512 MiB 超页覆盖 `[0, 2 GiB)`，`SPF=0xFF`），`smon=reserved`，`default_run_mode=hypv`
- `cfx=true`、`semihosting=true`；跑完整 inst + arch + embench，**不跑 picolibc**；`arch=true`、`picolibc=false`
- `exit_block=0x7FFD_0000`，`dump_base=0x7FFE_0000`
- **已定**：Node 测试本体在 hypv 执行；`entry=1 MiB`、`SP=2 GiB−64 KiB` 为首版初值，由 QEMU-080t 实测校准，不改 case 的 ISA 期望值。要求 U-mode 特权语义的 case 若无法在 Node 的 hypv 模式成立，登记 BLOCKED，不伪造期望值。

### 3. 向量与 harness 的参数化语法

- `tests/inst` 向量的几何敏感字段允许**符号 token**：`@RAM_BASE`、`@RAM_END`、`@SP`、`@BOOTROM_BASE`、`@ENTRY`，可带单个 `+0x…`/`-0x…` 偏移；适用于 `input_state.rd/rb/ra`、`input_state.memory[].address`、`expected_state` 的寄存器/内存值、`expected_pc`。
- `validate_vectors.py` 与 `build_test_binary.py` **用同一解析函数**按选中 profile 解析；未解析 token、越 48 位、或 semantic 内存地址落在所选 profile RAM 外 ⇒ 报错（不得静默取 0）。
- 仅当某 case 语义只对一个 profile 成立时，才允许新增可选 `profiles: [tiny|node]` 字段；**禁止**把一个 case 拆成两册/两 ID。使用该字段的 case 数量须在完成区报告。
- `expected_pc` 沿用字符串十六进制或 token；`schema.md` 同步说明 token 与 `profiles` 字段。

### 4. 加载模型（BootROM / 入口 / SP）

- **Tiny**：BootROM/trampoline 在 `0xFFFF_FFFF_0000`，只设 SP 并跳 `entry`，**无 cfx/hmon/PTW/user 模式**。raw 由 `-kernel` 装到 `kernel_base=0xFFFF_FF01_0000`，前 `0x100` 全零，应用入口 `0xFFFF_FF01_0100`；ELF 由 `minimal_crt0` 在 ROM `0xFFFF_FFFF_0000` 设 SP（`0xFFFF_FF7E_FF00`）后跳应用入口，`minimal_crt0` **自己清 BSS**（loader 不清）。
- **Node**：4 MiB BootROM 镜像装到 `0xFFFF_FFC0_0000`，复位入口在镜像内偏移 `0x3F_0000`；power 把 hmon 复制到 hmon SRAM，hmon 建页表、开 PTW 后移交测试；测试镜像按 ELF PT_LOAD 装入 PA=VA 恒等区，`entry` 与 `sp` 取 profile；smon 路径保留但本任务测试不使用。
- 两个 BootROM 的地址立即数由 profile 生成的汇编头/`--defsym` 注入；**BootROM 源与链接脚本不得散落字面量**。
- 链接脚本：`tests/shared/linker/dadao-tiny.lds`（Tiny；不再保留泛名 `dadao.lds`）与 `dadao-node.lds`（Node 2 GiB / 入口 1 MiB）；公共 `.rodata/.data/.bss` 与 `__bss_start/__bss_end/__heap_*` 抽到 `dadao-common.lds`，两份 wrapper 用 `INCLUDE dadao-common.lds`，驱动传 `-L tests/shared/linker`。`MEMORY` 的 ORIGIN/LENGTH 由静态门控与 profile 表逐项核对。picolibc 使用 `picolibc-tiny.ld`（Tiny 专用：`_start`/crt 在 ROM `0xffff_ffff_0000`，应用 `.text/.rodata/.data/.bss` 在 SRAM `0xffff_ff01_0100`，`e_entry` 在 ROM，SP `0xffff_ff7e_ff00`；Node 不跑 picolibc）。

### 5. 静态地址扫描与门控挂载

- 在 `tools/testcases/check_tests_index.py` 内新增地址扫描（或由它调用新脚本），使 `make check-tests-index`（L1）覆盖，**不改 Makefile 门控结构**。
- 扫描范围：`tests/**`、`tools/testcases/**` 的文本文件。禁止出现的旧几何字面量：`0xFC00`/`fc00`（任意写法）、`0xFFFF_FFFC_0000`、`0x00FF_0000`（旧 16 MiB 顶部偏移）、`0xFFFF_0000_1000`（旧 BINARY_BASE 别名）。允许清单缺省为空；唯一预登记例外 = `min_rom_probe_049t.py` 中作为**负例目标**的 `0xFFFF_0000_0000`（语义就是"旧别名未映射"），须逐处说明；其它注释/溯源需求逐文件列理由并经 reviewer 同意。
- 交叉核对：每个 lds 的 RAM/ROM `ORIGIN`/`LENGTH` 必须精确匹配 profile 表某一项；bootrom 链接入口/复位偏移一致；`build_test_binary.py` 的基址不再取字面量。
- `--self-test` 至少含：注入旧字面量 ⇒ FAIL；篡改 lds ORIGIN ⇒ FAIL；干净树 ⇒ PASS。
- `tools/infra/check_interface_alignment.py` 只保留/改写**测试侧**断言（profile 表 ↔ lds ↔ harness）；QEMU↔profile 的等值断言以 profile 表中的 `qemu_*` 字段为准：字段未填时打印 `DEFERRED (QEMU-079)` 且不静默；填入后必须与 QEMU 补丁一致。不得把任何断言改成无条件 PASS。
- 生成器（`generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py` 及其它含地址字面量者）改为输出 token，`make check-generator-sync` 必须逐字节一致。

## 范围

**在范围内**
- `tests/shared/machine-profiles.yaml`（新）、`tests/shared/linker/**`（含 `dadao-common.lds`、`dadao-tiny.lds`、`dadao-node.lds`、`picolibc-tiny.ld`）、`tests/shared/bootrom/**`、`tests/shared/crt0/minimal_crt0.s`、`tests/shared/runtime/**`（仅地址相关）。
- `tests/inst/**`（向量 + `schema.md`）、`tests/arch/umon/**`（`.s` + `expected.yaml`）。
- `tools/testcases/lib/**`、`tools/testcases/inst/**`、`tools/testcases/arch/**`、`validate_vectors.py`、`check_tests_index.py`、`generate_*.py`、`oracle_*.py`（仅地址）。
- `tools/infra/check_interface_alignment.py`（仅测试侧断言改写）、`tools/testcases/picolibc_tests.py` 与 `tools/infra/test_picolibc_smoke.py`（Tiny picolibc 链接配置/profile 拒绝）。
- **必要连带**：`tests/unit/llvm/e2e/smoke_*.s`、`mcmodel_far.lds`、`lit/weak_undef.test` 中因 `dadao-tiny.lds` 改几何而失效的地址/断言；只改地址与注释，不改测试意图，并在完成区单列。
- `tests/case-ledger.tsv`、`tests/{inst,arch}.yaml` 仅在现场需要重生成时改（预期不变；不变则须 `git diff --exit-code` 证明）。

**不在范围内**
- QEMU/gem5 实现与补丁、`spec/`、`contracts/`、ADR 正文（归 `QEMU-079t`/`QEMU-080t` 链）；`Makefile` 只做活跃路径同步（不改语义）。
- tset/llvm-ts 的 user/SE 语义迁移；若因共享 lds 改动导致常量过期，只允许同步引用常量并登记，不调整套件语义。
- 新增测试能力/新 case；本任务只迁移既有资产。

## 任务分解（同一任务内阶段，按序执行）

- **P0 profile 与读取层**：建 `machine-profiles.yaml` + `machine_profile.py`；`validate_vectors.py`/`build_test_binary.py` 接 profile 与 token；`schema.md` 更新。
- **P1 inst 资产**：`tests/inst/base/*.yaml` 及带地址的其它册改 token；生成器改输出 token；case ID/条数不变。
- **P2 arch/bootrom/crt0**：Tiny/Node 两套 bootrom 源与 lds、`build_step5_bootrom.py`、`run_m5_e2e.py --profile`、`expected.yaml`、12 册 `.s`、40 余个 `min_rom_probe_*.py` 去字面量。约 15 个 `min_rom_probe_*` 以 `-bios` 在 `0xFFFF_FFFF_0000` 直接执行（隐含 64 KiB 窗口），Node 下须改为装入 4 MiB BootROM 容器/附加段，**不得沿用 64 KiB 假设**；无法静态改造的探针登记 BLOCKED 并给出原因，不得伪造通过。
- **P3 门控与连带**：`check_tests_index.py` 地址扫描 + 自测；`check_interface_alignment.py` 测试侧断言；e2e 连带文件；全量静态复跑。
- 每阶段单独 `cp`+`md5` 留存证据，阶段结束即跑该阶段可跑门控，不积压。

## 验收标准

**S1 结构/静态（必须全绿）**
1. `python3 tools/testcases/validate_vectors.py --profile tiny` 与 `--profile node` 均 rc=0；M1 向量条数与迁移前一致（现场统计，不写死）。
2. `make validate-vectors` rc=0（缺省 Tiny）。
3. `make check-tests-index` rc=0（含新地址扫描）；扫描 `--self-test` 通过，且真实注入一次旧字面量 ⇒ FAIL、`cp`+`md5sum -c` 还原后回绿。
4. `make check-case-ledger` rc=0；`git diff --exit-code tests/case-ledger.tsv` rc=0（无身份漂移）。
5. `make check-generator-sync` rc=0（生成器输出与落盘逐字节一致）。
6. `make check-no-residue` rc=0；`git status --porcelain -uall` 除本任务文件外干净。
7. `python3 -m compileall -q tools` rc=0。
8. `make check`（L1）rc=0；其中 `check-interface` 的 QEMU↔profile 等值按 `qemu_*` 字段缺省打印 `DEFERRED`，测试侧断言必须保留可达 FAIL。

**S2 构建/装配（静态，不需要 QEMU）**
9. Tiny/Node BootROM 均可构建（`llvm-mc`/`lld`/`objcopy`），`llvm-readobj` 证据：Tiny 镜像 ≤64 KiB、入口/复位 `0xFFFF_FFFF_0000`；Node 镜像 ≤4 MiB、复位入口偏移 `0x3F_0000`、`.text` 起点符合 profile。
10. `run_m5_e2e.py --profile node --build-only`（arch 仅 Node）逐个汇编 `tests/arch/umon/*.s` 并 objcopy 成功；`--profile tiny` 必须显式拒绝；不启动 QEMU。`run_codegen_e2e.py --build-only` 全量通过（raw 入口前缀/`.text.start` 顺序）。
11. Tiny `dadao-tiny.lds` 链接最小 ELF：`e_entry=0xffff_ffff_0000`，应用 `.text` 在 `0xffff_ff01_0100`；Node `dadao-node.lds` `e_entry=0x100000`。Tiny picolibc 用 `picolibc-tiny.ld` 静态链接成功（`_start`/`__bss_*`/`__stack` 布局），raw C BSS 测试 `bss_zero_e2e.c` 静态链接成功且 `minimal_crt0` 含 `bss_clear`。

**S3 证据**
12. `.work/evidence/TESTCASES-091t/*` 有 `run.sh`（一条命令重跑全部静态检查、逐项取真实 rc、无 `tee` 吞码）、日志、注入/还原记录（`cp`+`md5`）、profile 参数核对输出。完成区只写结论 + 证据路径。

**BLOCKED（不得声称通过，交后续任务）**
- 真实 QEMU 执行类：`check-inst-smoke`、`check-arch-smoke`、`check-unit`、`check-tset-*-smoke`、`test-elf`、`test-codegen`、`picolibc-tests` 实跑及所有 `min_rom_probe_*` 实跑——依赖 `QEMU-079t`/`QEMU-080t` 的机器实现。
- `check-interface` 的 QEMU↔profile 等值断言——同上，待 QEMU 任务填入 `qemu_*` 字段后转为强制。
- tset/llvm-ts 的 user/SE 地址常量与语义——非 Machine-v5 FS profile，登记不处理。

## 完成区

**测试结果**：证据脚本 `.work/evidence/TESTCASES-091t/run.sh` **50/50 PASS, 0 FAIL**（真实输出 `run.log`；含注入/还原与 L1）。`validate_vectors --profile {tiny,node}` rc=0（validate 输出 16 data files / 716 cases；`tests/inst/**` 全量 1488 与迁移前一致；Tiny 构建 1484 / 跳过 4 条 node-only，Node 1445 / 跳过 43 条 tiny-only）；`validate_m5_vectors` **140 checks PASS**（`m5_perm_mask_cfxperm` 归 `target_cfxtrap_denied`）；`make check` rc=0；`check-tests-index` rc=0 且旧几何残留 0；`check-case-ledger` rc=0 且 `case-ledger.tsv` diff=0；`check-generator-sync` rc=0；`check-no-residue` rc=0；`compileall tools` rc=0；`check-interface` 80 PASS / 5 MANUAL（QEMU `qemu_*` 全为 `DEFERRED (QEMU-079)`）。
**修改文件**：新增 `tests/shared/machine-profiles.yaml`、`tests/shared/asm/{machine,machine-tiny,machine-node}.inc`、`tests/shared/linker/{dadao-common,dadao-tiny,dadao-node}.lds`、`tests/shared/linker/picolibc-tiny.ld`、`tools/testcases/lib/machine_profile.py`、`tools/testcases/arch/gen_machine_inc.py`、`tests/unit/llvm/e2e/bss_zero_e2e.c`+`lit/bss_zero_e2e.test`；改 `tests/{arch/umon,arch.yaml,inst,shared,unit/llvm/e2e}` 地址/token/lds 引用、`tools/testcases/{lib,arch,unit,picolibc_tests,run_suite}`、`tools/infra/{check_interface_alignment,test_picolibc_smoke,build_musl}`、向量生成器（ctrl/mem/misc/atomics）与 `Makefile` 活跃路径。另改 `.tao/knowledge/milestones.md`（流水状态→待验收，L1 一致性连带）；完整清单见 `git status`。
**验收结果**：Tiny BootROM 40 B（entry `0xffffffff0000`）；Node BootROM 4194304 B、复位窗口 `0x3f0000` 与 power flat 首字一致；`dadao-tiny.lds` 最小 ELF entry=`0xffffffff0000`、应用 `.text`=`0xffffff010100`，`dadao-node.lds` entry=`0x100000`；`run_m5_e2e --profile node --build-only` 10/10、`--profile tiny` 显式 rc=2；`run_codegen_e2e --build-only` 19/19；picolibc Tiny 静态链接成功且 `e_entry=0xffffffff0000`（`_start` ROM、`_picolibc_start` SRAM），`--profile node` rc=2；BSS C 静态链接并确认 `bss_clear`。证据：`.work/evidence/TESTCASES-091t/{run.sh,run.log,check_node_bootrom.py}`。
**新发现/坑**：① profile 限定 case 共 47 条（Tiny 跳过 4 条 escape-node-only；Node 跳过 43 条 tiny-only）；② `min_rom_probe_*` 只做几何常量化+编译级迁移，真实字节序列仍需 QEMU-079/080 校准，未伪称通过；③ tset/llvm-ts 三个 `SCRIPTED_BASE` 在扫描白名单（qemu-user/SE，非 Machine-v5）；049t 仅白名单 `0xFFFF_0000_0000` 负例目标；④ 隔离 worktree 跑 L1 需把 `.work/{evidence,log}` 指到主工作树（`check-knowledge-refs` 历史引用），本次已用符号链接完成；⑤ `inner_cfx_mask_denied` 暂无可执行向量，已在 validator/任务书登记待后续向量；⑥ Tiny `dadao-tiny.lds` 对 legacy musl crt1 保留“_start 可在应用入口”的兼容分支（musl crt1 未迁移）。
**合入前返工（reviewer F1–F3）**：F1 `bss_probe` 改 `volatile __attribute__((used))`，新增 `check_bss.py` 断言 `.bss` 非空且 probe 落在区间；F2 Node `__heap_end` 修正为 `0x7ffef000`，`check-tests-index` 新增 `__heap_end == sp-0x1000` 门控（tiny `0xffffff7eef00` 同构）；F3 `components/{picolibc,musl}/README.md` 路径改 `minimal_crt0.s`/`dadao-tiny.lds`。证据 `run.sh` **50/50 PASS**。
**遗留问题**：**BLOCKED**：`check-inst-smoke`/`check-arch-smoke`/`check-unit`/`check-tset-*-smoke`/`test-elf`/`test-codegen`/`picolibc-tests` 与全部 `min_rom_probe_*` 实跑依赖 QEMU-079t/080t；Node `entry=1 MiB`、`SP=2 GiB−64 KiB` 待 QEMU-080t 校准；tset/llvm-ts user/SE 地址常量不迁移；`inner_cfx_mask_denied` 向量待后续；legacy musl crt1 布局未迁移。
**收尾结论**：reviewer 两轮均 `Accepted`（第 1 轮 25 行、第 2 轮 10 行原文保留，第 2 轮为 F1–F3 返工增量复核）；architect 显式 staging 提交本任务分支，未 merge/push。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `build_branch_test_binary`/`build_ret_binary` 对已解析的 int `expected_pc` 再 `int(x,16)` ⇒ TypeError | ✅已修 | 新增 `_as_int()` 并用于两处 | 1488/1445 cases 全量构建脚本通过 |
| F2 `build_test_binary` 对 `profiles: [tiny]` 的 case 在 node 下仍尝试解析 token | ✅已修 | 先判 `profiles`，不适用即显式 `ValueError`（不静默） | node 构建 1445 built / 43 skipped，无异常 |
| F3 `generate_misc` 硬编码 preamble=3 字，Tiny 新 entry 需 4 字 ⇒ assert 失败 | ✅已修 | 改为 handler_start 不动点求解 | `generate_misc.py --check` PASS |
| F4 `machine_profile` 仓库根路径少一层；缺 profile 自洽校验 | ✅已修 | 4 层 dirname；校验 `ram_end`/复位窗口/entry/sp/exit 落在 RAM | `machine_profile.py` 正常打印两 profile |
| F5 地址扫描会扫到自身 forbidden 表；asm 头漂移无门控 | ✅已修 | 排除扫描器自身；`check_profile_lds` 增 asm header 逐项核对；self-test 增注入⑭⑮⑯ | `--self-test` 17 case PASS |
| F6 evidence 内联 heredoc 取 Python rc 方式错误（`reset_word` 为空） | ✅已修 | 抽出 `check_node_bootrom.py`，直接取 `$?` | Node 镜像断言 PASS |
| F7 隔离 worktree 中 `make check` 因历史 `.work` 引用与 `.dadao` 工具链缺失失败 | ✅已处置 | 仅在 worktree 建 `.work/{evidence,log}`、`.dadao/*` 符号链接（不入库）；证据 run.sh 支持 `TC_BIN` | `make check` rc=0 |
| F8 `check-milestones-fresh` 要求流水状态与任务书一致 | ✅已修 | `.tao/knowledge/milestones.md` 行改 `待验收`（连带、已在完成区披露） | 该门控 PASS |
| F9 `validate_m5_vectors` 3 条 `m5_perm_mask_illi` 失败（rule→ILLI vs cause=CFXPERM） | ✅已修 | 向量改名 `m5_perm_mask_cfxperm`；规则拆 `target_cfxtrap_denied`⇒CFXPERM / `inner_cfx_mask_denied`⇒ILLI；coverage 改 `perm.cfxperm.mask` | `validate_m5_vectors` 140 checks PASS |
| F12 lds 泛名 `dadao.lds` 与两份脚本漂移风险 | ✅已修 | 改 `dadao-tiny.lds`，公共段抽 `dadao-common.lds` + `INCLUDE`，驱动加 `-L` | `check-tests-index` common/lds 核对 PASS；min ELF entry 正确 |
| F13 picolibc 仍用 `picolibc_noflash.ld` 默认旧基址 | ✅已修 | 新增 Tiny 专用 `picolibc-tiny.ld`（A 方案：`_start`/crt 在 ROM、应用 SRAM、e_entry ROM、SP 0x7eff00）；`picolibc_tests` 按 profile，Node rc=2 | Tiny 静态链接 e_entry=0xffffffff0000；Node 拒绝 rc=2 |
| F14 `minimal_crt0` 不清 BSS / raw 前缀缺失 | ✅已修 | 加 `__bss_start/__bss_end`、`bss_clear` 循环；`build_test_binary`/`run_codegen_e2e` 加 Tiny raw 0x100 前缀与 `.text.start` 顺序 | BSS C 链接含 `bss_clear`；`run_codegen_e2e --build-only` 19/19 |
| F10 `min_rom_probe_*` 只做几何常量化，未验证新字节序列 | ⏸延后 | 动态执行依赖 QEMU-079/080；不伪造通过 | 全部登记 BLOCKED；compileall/扫描 PASS |
| F11 `misc.yaml` 的 escape 非法序列曾把 Tiny 绝对 handler 地址写进 `sequence`，Node 构建会指向错误地址 | ✅已修 | 改为 `rb2rd rd22,rb0,1` + `add.si rd22,16` 的 IP 相对 handler，两 profile 共用同一序列 | misc tiny/node 均构建；`generate_misc --check` PASS |

### 第 1 轮 reviewer 验收（2026-11-02，独立重跑；worktree=`/tmp/opencode/DADAO-v5/TESTCASES-091t`）

**重跑记录（全部由 reviewer 自己执行，输出留 `/tmp/opencode/TESTCASES-091t-review/`）**
- `bash .work/evidence/TESTCASES-091t/run.sh` → **rc=0**，`== RESULT: 49/49 PASS, 0 FAIL ==`（`run_stdout.txt` / `run.log:1045`）。
- 逐项独立复跑 rc：`validate_vectors --profile tiny`=0、`--profile node`=0、`make validate-vectors`=0、`validate_m5_vectors`=0（`PASS (140 checks)`）、`check_tests_index`=0、`--self-test`=0、`gen_machine_inc --check`=0、`make check-case-ledger`=0、`git diff --exit-code tests/case-ledger.tsv`=0、`make check-generator-sync`=0、`make check-no-residue`=0、`python3 -m compileall -q tools`=0、`check_interface_alignment`=0（run.log：85 项 = 80 PASS / 0 FAIL / 5 MANUAL，QEMU 项全 `DEFERRED (QEMU-079)`）。
- 条数现场统计：`tests/inst/**/*.yaml` 在 HEAD 与工作树均为 **1488**（逐文件零差异）；`profiles` 限定共 **47** 条（`[tiny]`=43、`[node]`=4 个 `escape_ciii_cfx`）。
- **独立注入①**（与 engineer 不同）：`tests/shared/asm/machine-tiny.inc` SP 改 `0xffffff7ef000` → `check_tests_index`=**1**（`ASM HEADER DRIFT`）、`gen_machine_inc --check`=**1** → `cp`+`md5` 还原（`94dab35a…` `md5sum -c OK`）→ 两者回 **0**。
- **独立注入②**（与 engineer 不同）：`tests/shared/crt0/minimal_crt0.s` `bss_clear`→`bss_wipe` → 同一 `run.sh` **rc=1、47/49**（`[FAIL] minimal_crt0 BSS clear`；同轮 `make check` 因并发写入 `.work/log/qemu/QEMU-081t-*.EXIT` 触发 `check-run-artifacts` A3 红，属环境干扰）→ `cp`+`md5` 还原（`87ab3360…` `md5sum -c OK`）→ 全量 `run.sh` 回 **rc=0 / 49/49**。
- 现场实测：Tiny raw 镜像前 `0x100` 全零、代码起于 `0x100`（`build_test_binary --profile tiny`）；`node` 案例在 tiny 下 `ValueError: applies only to profiles ['node']`；Tiny 链接 `e_entry=0xffffffff0000` 且应用 `.text=0xffffff010100`、Node `e_entry=0x100000`；picolibc 链接 `_start=0xffffffff0000`(ROM)/`_picolibc_start=0xffffff010100`(SRAM)/`__stack=0xffffff7eff00`；`bss.elf` 反汇编含 `bss_clear` 循环（rb2/rb3 取 `__bss_start/__bss_end`，不依赖 loader）。
- 边界核：`run_m5_e2e --profile tiny`=**2**、`picolibc_tests`/`test_picolibc_smoke --profile node`=**2**（均显式 ERROR 文案，非静默跳过）；`validate_m5_vectors` 规则拆分 `target_cfxtrap_denied→CFXPERM`（源常量 `0x0080` 与 `spec/DADAO-12 §4` 的 `1<<7` 一致）、`inner_cfx_mask_denied→ILLI` 未入 `REQUIRED_COVERAGE`（无伪造）；活跃树无 `m5_perm_mask_illi` / `dadao.lds` / `codegen_crt0` 残留。
- 快照对账：验收前/后 `git status --porcelain -uall` 均 **151 行**、`diff` 无差异；`spec/`、`contracts/`、`.tao/adr` 未改；无 `*_tmp*`/`*.orig`/`*.rej`；完成区 5 行（≤30）。
- BLOCKED 属实：`.dadao/host-tools/bin/qemu-system-dadao` **不存在**（仅有 `lli`）⇒ `check-inst-smoke`/`check-arch-smoke`/`check-unit`/`check-tset-*-smoke`/`test-elf`/`test-codegen`/`picolibc-tests`/`min_rom_probe_*` 实跑不可执行；run.log 中 build-only 行标 `(build-only (no QEMU))`、`actual=?`，未伪称执行通过。

**约束核验**：S1.1–S1.8、S2.9–S2.12 全部在我自己的重跑下 rc=0；Makefile diff 仅路径同步 + Node arch bootrom（`step5/bootrom_step5.bin`）；case ID/`case-ledger.tsv` 无漂移；未新建平行测试树、`tests/` 根未新增 yaml；`.tao/archive/**` 历史引用未动。

**Findings（非阻断，交 architect 处置）**
- F1 `tests/unit/llvm/e2e/bss_zero_e2e.c` 被 `-Oz` 常量折叠：`llvm-nm bss.o` 无 `bss_probe`、链接后 `__bss_start==__bss_end`、`main` 恒返回 0 ⇒ 该用例将来开 runtime 行也恒真；建议改 `volatile`/`extern`（本轮 S2.11 字面判据已满足，未伪造）。
- F2 `dadao-node.lds __heap_end=0x7fef000` 疑少一位（tiny 同构为 `sp-0x1000` ⇒ `0x7ffef000`），且无门控核对该值；`__heap_end` 未按任务书 §4 抽入 `dadao-common.lds`。
- F3 `components/picolibc/README.md:36`、`components/musl/README.md:36` 仍引用已删除的 `tests/shared/{crt0/codegen_crt0.s,linker/dadao.lds}`（`.tao/contracts/contract-elf.md`、changelog 属历史/范围外）。
- F4 完成区把「1488 cases」归给 `validate_vectors` 输出，该脚本实印 `16 data files, 716 cases`（1488 = 全 `tests/inst/**` 条数，已现场核）。
- F5 `gen_machine_inc.py` 硬编码 `HMON_BASE/SMON_BASE/PMEM_BASE`（不在 profile 表）；`check-tests-index` 未核 `EXIT_BLOCK/DUMP_BASE` 与 profile 一致。
- F6 `docs/Process-09-测试组织规范.md`、`tests/{README,INVENTORY}.md`、`tools/qemu/generate_atomics_vectors.py` 等改动未逐项进「修改文件」（该区已声明“完整清单见 `git status`”）。
- 环境提示：`.work/log` 符号链接主工作树，并发会话（QEMU-081t）写 `.work/log/qemu/*.EXIT` 会使本 worktree `make check` 的 `check-run-artifacts` 间歇红（我实测到 1 次），非本任务缺陷。

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全部通过、两次反例注入均 FAIL 且 `cp`+`md5` 还原后回绿；上列 findings 由 architect 终审时裁定是否随收尾修）

### 合入前返工（reviewer finding F1–F3，2026-11-02）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `bss_probe` 被 `-Oz` 折叠，`.bss` 可能为空 | ✅已修 | `bss_probe` 改 `static volatile ... __attribute__((used))`；新增 `.work/evidence/TESTCASES-091t/check_bss.py` 断言 `bss_probe` 存在、`__bss_start < __bss_end` 且 probe 落在区间 | `llvm-nm` 见 `bss_probe=0xffffff010158`、`__bss_start=0xffffff010158`、`__bss_end=0xffffff0101d8`；`check_bss.py` rc=0；证据 `[PASS] bss probe non-empty (nm)` |
| F2 Node `__heap_end = 0x7fef000` 少一位 | ✅已修 | Node 改 `0x7ffef000`（SP `0x7fff0000` − `0x1000`）；`check_tests_index` 新增 `__heap_end == sp-0x1000` 门控，Tiny 同构核对 `0xffffff7eef00` | 篡改 Node 回 `0x7fef000` ⇒ `check-tests-index` rc=1（`__heap_end ... != sp-0x1000`），`cp`+`md5` 还原后 rc=0；证据 50/50 |
| F3 components README 旧路径 | ✅已修 | `components/picolibc/README.md` 改 `minimal_crt0.s`/`dadao-tiny.lds`；`components/musl/README.md` 改 `dadao-tiny.lds` | 活跃树无 `codegen_crt0.s`/`dadao.lds` 旧引用（archive 除外） |

**返工后门控（真实 rc）**
- `run.sh` → **50/50 PASS, 0 FAIL**（含新增 `check_bss.py`）。
- `bss_zero_e2e` 静态：`clang -Oz`+`llvm-mc`+`ld.lld` rc=0，`llvm-nm` 三符号齐全、`.bss` 0x80 字节；`check_bss.py` rc=0。
- `check_tests_index` rc=0；`--self-test` rc=0；`gen_machine_inc --check` rc=0。
- `validate_m5_vectors` rc=0（`PASS (140 checks)`）。
- `make check` rc=0（L1）。
- 未改 reviewer 原文；未 commit。

### 第 2 轮 reviewer 验收（F1–F3 返工增量复核，2026-11-02，reviewer 自己重跑）

- **F1**：`bss_zero_e2e.c` 现为 `static volatile unsigned long bss_probe[16] __attribute__((used))`；我自己 `clang -Oz`+`llvm-mc`+`ld.lld`（dadao-tiny.lds）→ rc=0/0/0，`llvm-nm`：`bss_probe=0xffffff010158`、`__bss_start=0xffffff010158`、`__bss_end=0xffffff0101d8` ⇒ `.bss` 0x80 非空、`start<end`、探针在区间内；`main` 反汇编确有 `ld.o` 读探针 + `ret` 分支（非恒真）；新增 `check_bss.py` 我实测**负例 rc=1**（用无 `bss_probe` 的旧 ELF：`missing symbols ['bss_probe']`）、**正例 rc=0**。
- **F2**：`dadao-node.lds __heap_end=0x7ffef000` = SP `0x7fff0000`−`0x1000` ✓；`dadao-tiny.lds 0xffffff7eef00` = SP `0xffffff7eff00`−`0x1000` ✓（同构）；`check_tests_index` 新增校验（`expected_heap = prof.sp - 0x1000`）。**独立注入③**（本轮新反例）：Node 改回 `0x7fef000` ⇒ `check_tests_index` **rc=1**（`LDS: … __heap_end 0x7fef000 != sp-0x1000 0x7ffef000`，`结果: FAIL (1 项)`）⇒ `cp`+`md5`（`f3dd95f8…` `md5sum -c OK`）⇒ **rc=0**（`结果: PASS（241 条…）`）。`--self-test` rc=0（17 case；未新增 heap 专用注入用例，规则实证靠本注入，记为观察项）。
- **F3**：`components/picolibc/README.md:36` → `tests/shared/{crt0/minimal_crt0.s,linker/dadao-tiny.lds}`、`components/musl/README.md:36` → `dadao-tiny.lds`；全活跃树（排除 `.tao/archive`、changelog）`codegen_crt0|dadao.lds` 命中 0。
- **重跑（全部 reviewer 执行）**：`bash .work/evidence/TESTCASES-091t/run.sh` → **rc=0，`== RESULT: 50/50 PASS, 0 FAIL ==`**（23:56:40–23:58:43）；`make check` → **rc=0**（`repository checks (L1): PASS`，`check-interface` 85 项 = 80 PASS / 0 FAIL / 5 MANUAL）；`validate_m5_vectors` → **rc=0**（`PASS (140 checks)`）；`check_tests_index` → **rc=0**（`473 个文本文件，旧几何残留 0`、`241 条`）；`check_tests_index --self-test` → **rc=0**；`gen_machine_inc --check` → **rc=0**（两头 `OK`）；`make check-no-residue` → **rc=0**（`PASS`）。
- **记录完整性**：第 1 轮 reviewer 验收节 **25 行原文逐段未改**（标题/两次注入 md5/判决均在）；`第 1 轮 engineer 自审`节 19 行未改；本轮结论为**追加**。完成区：`修改文件`/`验收结果`/`新发现/坑`/`遗留问题` 四行原文未动，`测试结果` 行被就地更新（`49/49→50/50`、1488/716 口径按 F4 修正），新增 `合入前返工` 一行 ⇒ 与真实输出一致，记 F4 已闭环；完成区仍 6 行（≤30）。
- **快照对账**：本轮前/后 `git status --porcelain -uall` 均 **153 行**、`diff` 无差异（仅比上轮多 `components/{picolibc,musl}/README.md`）；注入文件 md5 还原校验通过；无 `*_tmp*`/`*.orig`/`*.rej`/`.bak` 残留；**未 commit**。

**判决：Accepted**（F1–F3 三条返工在我自己的重跑下全部证实；注入③ FAIL→还原→回绿；`run.sh` 50/50 与 `make check` rc=0 由 reviewer 亲自取得）
