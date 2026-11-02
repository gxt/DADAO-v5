# TESTCASES-091t: Machine-v5 Tiny/Node 测试资产迁移

**模块**：testcases
**项目里程碑**：M11
**依赖**：无（真实机器执行依赖后续 `QEMU-079t`/`QEMU-080t` 建册落地；本任务不依赖其代码）
**状态**：待开始

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

- 旧几何硬编码散落：`tests/inst/base/*.yaml` 8 册约 160 处、`tests/arch/umon/*.s` 12 册、`tools/testcases/**` 约 51 个文件，以及 `tests/shared/linker/dadao.lds`、`tests/shared/bootrom/**`、`tests/shared/crt0/codegen_crt0.s`、`tests/unit/llvm/e2e/**`。
- 两个 profile 的 RAM 位于不同地址空间（Tiny 在 cfxha 63 内部空间且无 PTW；Node 在内存窗口 `addr[47:42]=0` 且 PTW 开启），**同一个绝对地址无法通用于两者**。
- 若按 profile 复制用例，会破坏 `case-ledger.tsv` 身份、`tests/*.yaml` 唯一性与覆盖率；因此必须"**同一 case ID 一份，profile 只决定地址/装载方式**"。
- 现有 `validate_vectors.py`、`build_test_binary.py`、`check_interface_alignment.py` 均把旧 RAM 基址/容量当常量。

## 目标

1. 建立**单一 profile 真源**（Tiny/Node 的 BootROM/RAM/入口/SP/装载/PTW 参数），测试资产与驱动只读取它，不各写一份。
2. `tests/inst`、`tests/arch`、`tests/shared/{bootrom,linker,crt0,runtime}`、ELF loader 与 `tools/testcases` 驱动按 profile 参数化；同一 case 只有一份。
3. 测试资产中**不再出现旧 0xFC00 高 RAM / 16 MiB / 256 KiB BootROM 字面量**；地址静态扫描可失败、可注入。
4. 静态门控（schema/validate/index/ledger/生成器同步/地址扫描/`check-no-residue`）全绿；真实 QEMU 执行明确 BLOCKED，交 QEMU 任务。
5. 不改 QEMU/gem5 实现、`spec/`、`contracts/`、`Makefile`；不新建平行测试树。

## 接口规范

### 1. profile 真源与读取

- 新增 `tests/shared/machine-profiles.yaml`（`tests/` 根下不得新增 `*.yaml`，故放 `shared/`），是测试侧**唯一**几何真源；`tools/testcases/lib/machine_profile.py` 提供 `load(name)`、`resolve(token)`、`all_profiles()`。
- 字段（两 profile 同构，缺一即错误）：
  - `bootrom_base` / `bootrom_size` / `reset_pc` / `bootrom_load`
  - `ram_base` / `ram_size` / `ram_end`
  - `entry` / `sp` / `host_loader` / `image_window`
  - `ptw` / `hmon` / `smon` / `default_run_mode`
  - `exit_block` / `dump_base`（harness 私有区，由 `sp`/`ram_base` 派生）
- 选择方式：驱动统一接受 `--profile {tiny,node}`，环境变量 `DADAO_TEST_PROFILE` 可替代；**缺省 `tiny`**（不改 `Makefile`）。真实执行 Node 用 `DADAO_TEST_PROFILE=node make ...` 或显式参数。

### 2. 两个 profile 的取值（本任务约定；集中一处，变更只改 profile 表）

**Tiny**
- `bootrom_base=0xFFFF_FFFF_0000`，`bootrom_size=0x1_0000`（64 KiB），`reset_pc=0xFFFF_FFFF_0000`，`bootrom_load=bios-flat@base`
- `ram_base=0xFFFF_FF00_0000`，`ram_size=0x80_0000`（8 MiB），`ram_end=0xFFFF_FF7F_FFFF`
- `entry=0xFFFF_FF00_0000`（ELF `e_entry` 必须等于它），`sp=0xFFFF_FF7F_0000`（RAM 顶 − 64 KiB）
- `host_loader=elf-ptload`（宿主按 PT_LOAD 装入 SRAM），`image_window=0x1_0000`
- `ptw=false`，`hmon=false`，`smon=false`，`default_run_mode=user`（bootrom：power → 配置 cfx_umon 用户向量 → `trap cfx_umon`）
- `exit_block=0xFFFF_FF7D_0000`，`dump_base=0xFFFF_FF7E_0000`

**Node**
- `bootrom_base=0xFFFF_FFC0_0000`，`bootrom_size=0x40_0000`（4 MiB），`reset_pc=0xFFFF_FFFF_0000`（= base + `0x3F_0000`），`bootrom_load=bios-flat@base`
- `ram_base=0x0000_0000_0000`，`ram_size=0x8000_0000`（2 GiB），`ram_end=0x7FFF_FFFF`
- `entry=0x0000_0000_0010_0000`（**本任务初值，1 MiB**），`sp=0x0000_0000_7FFF_0000`（2 GiB − 64 KiB）
- `host_loader=elf-ptload`（VA=PA 恒等，PTW 开启），`image_window=0x1_0000`
- `ptw=true`，`hmon=true`（hmon 建立一级页表：4 × 512 MiB 超页覆盖 `[0, 2 GiB)`，`SPF=0xFF`），`smon=reserved`，`default_run_mode=user`
- `exit_block=0x7FFD_0000`，`dump_base=0x7FFE_0000`
- **已定**：Node 测试本体在 hypv 执行；`entry=1 MiB`、`SP=2 GiB−64 KiB` 为首版初值，由 QEMU-080t 实测校准，不改 case 的 ISA 期望值。Tiny 由宿主 loader 设置入口/栈，无 hmon/PTW/异常路径。要求 U-mode 特权语义的 case 若无法在 Node 的 hypv 模式成立，登记 BLOCKED，不伪造期望值。

### 3. 向量与 harness 的参数化语法

- `tests/inst` 向量的几何敏感字段允许**符号 token**：`@RAM_BASE`、`@RAM_END`、`@SP`、`@BOOTROM_BASE`、`@ENTRY`，可带单个 `+0x…`/`-0x…` 偏移；适用于 `input_state.rd/rb/ra`、`input_state.memory[].address`、`expected_state` 的寄存器/内存值、`expected_pc`。
- `validate_vectors.py` 与 `build_test_binary.py` **用同一解析函数**按选中 profile 解析；未解析 token、越 48 位、或 semantic 内存地址落在所选 profile RAM 外 ⇒ 报错（不得静默取 0）。
- 仅当某 case 语义只对一个 profile 成立时，才允许新增可选 `profiles: [tiny|node]` 字段；**禁止**把一个 case 拆成两册/两 ID。使用该字段的 case 数量须在完成区报告。
- `expected_pc` 沿用字符串十六进制或 token；`schema.md` 同步说明 token 与 `profiles` 字段。

### 4. 加载模型（BootROM / 入口 / SP）

- **Tiny**：`bootrom.bin`（64 KiB 平铺）经 `-bios` 装到 `0xFFFF_FFFF_0000`，复位 PC=base；宿主 loader 按 ELF PT_LOAD 把 `.text/.rodata/.data/.bss` 装入 SRAM（**不复制进 BootROM**）；bootrom 配置后 `trap` 到 `entry`，**无 hmon/PTW**。
- **Node**：4 MiB BootROM 镜像装到 `0xFFFF_FFC0_0000`，复位入口在镜像内偏移 `0x3F_0000`；power 把 hmon 复制到 hmon SRAM，hmon 建页表、开 PTW 后移交测试；测试镜像按 ELF PT_LOAD 装入 PA=VA 恒等区，`entry` 与 `sp` 取 profile；smon 路径保留但本任务测试不使用。
- 两个 BootROM 的地址立即数由 profile 生成的汇编头/`--defsym` 注入；**BootROM 源与链接脚本不得散落字面量**。
- 链接脚本：`tests/shared/linker/dadao.lds` 改为 **Tiny** 几何（保持文件名，`Makefile` 不动）；新增 `dadao-node.lds`（Node 2 GiB / 入口 1 MiB）。两者共享 sections 片段，`MEMORY` 的 ORIGIN/LENGTH 由静态门控与 profile 表逐项核对。

### 5. 静态地址扫描与门控挂载

- 在 `tools/testcases/check_tests_index.py` 内新增地址扫描（或由它调用新脚本），使 `make check-tests-index`（L1）覆盖，**不改 Makefile**。
- 扫描范围：`tests/**`、`tools/testcases/**` 的文本文件。禁止出现的旧几何字面量：`0xFC00`/`fc00`（任意写法）、`0xFFFF_FFFC_0000`、`0x00FF_0000`（旧 16 MiB 顶部偏移）、`0xFFFF_0000_1000`（旧 BINARY_BASE 别名）。允许清单缺省为空；唯一预登记例外 = `min_rom_probe_049t.py` 中作为**负例目标**的 `0xFFFF_0000_0000`（语义就是"旧别名未映射"），须逐处说明；其它注释/溯源需求逐文件列理由并经 reviewer 同意。
- 交叉核对：每个 lds 的 RAM/ROM `ORIGIN`/`LENGTH` 必须精确匹配 profile 表某一项；bootrom 链接入口/复位偏移一致；`build_test_binary.py` 的基址不再取字面量。
- `--self-test` 至少含：注入旧字面量 ⇒ FAIL；篡改 lds ORIGIN ⇒ FAIL；干净树 ⇒ PASS。
- `tools/infra/check_interface_alignment.py` 只保留/改写**测试侧**断言（profile 表 ↔ lds ↔ harness）；QEMU↔profile 的等值断言以 profile 表中的 `qemu_*` 字段为准：字段未填时打印 `DEFERRED (QEMU-079)` 且不静默；填入后必须与 QEMU 补丁一致。不得把任何断言改成无条件 PASS。
- 生成器（`generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py` 及其它含地址字面量者）改为输出 token，`make check-generator-sync` 必须逐字节一致。

## 范围

**在范围内**
- `tests/shared/machine-profiles.yaml`（新）、`tests/shared/linker/**`、`tests/shared/bootrom/**`、`tests/shared/crt0/codegen_crt0.s`、`tests/shared/runtime/**`（仅地址相关）。
- `tests/inst/**`（向量 + `schema.md`）、`tests/arch/umon/**`（`.s` + `expected.yaml`）。
- `tools/testcases/lib/**`、`tools/testcases/inst/**`、`tools/testcases/arch/**`、`validate_vectors.py`、`check_tests_index.py`、`generate_*.py`、`oracle_*.py`（仅地址）。
- `tools/infra/check_interface_alignment.py`（仅测试侧断言改写）。
- **必要连带**：`tests/unit/llvm/e2e/smoke_*.s`、`mcmodel_far.lds`、`lit/weak_undef.test` 中因 `dadao.lds` 改几何而失效的地址/断言；只改地址与注释，不改测试意图，并在完成区单列。
- `tests/case-ledger.tsv`、`tests/{inst,arch}.yaml` 仅在现场需要重生成时改（预期不变；不变则须 `git diff --exit-code` 证明）。

**不在范围内**
- QEMU/gem5 实现与补丁、`spec/`、`contracts/`、`Makefile`、ADR 正文（归 `QEMU-079t`/`QEMU-080t` 链）。
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
10. `run_m5_e2e.py --profile {tiny,node} --build-only`（或等价 build-only 模式）逐个汇编 `tests/arch/umon/*.s` 并 objcopy 成功；不启动 QEMU。
11. 每个 profile 的 lds 链接一个最小 ELF，`e_entry`/最小 PT_LOAD 落在 profile 规定地址。

**S3 证据**
12. `.work/evidence/TESTCASES-091t/` 有 `run.sh`（一条命令重跑全部静态检查、逐项取真实 rc、无 `tee` 吞码）、日志、注入/还原记录（`cp`+`md5`）、profile 参数核对输出。完成区只写结论 + 证据路径。

**BLOCKED（不得声称通过，交后续任务）**
- 真实 QEMU 执行类：`check-inst-smoke`、`check-arch-smoke`、`check-unit`、`check-tset-*-smoke`、`test-elf`、`test-codegen` 及所有 `min_rom_probe_*` 实跑——依赖 `QEMU-079t`/`QEMU-080t` 的机器实现。
- `check-interface` 的 QEMU↔profile 等值断言——同上，待 QEMU 任务填入 `qemu_*` 字段后转为强制。
- tset/llvm-ts 的 user/SE 地址常量与语义——非 Machine-v5 FS profile，登记不处理。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
