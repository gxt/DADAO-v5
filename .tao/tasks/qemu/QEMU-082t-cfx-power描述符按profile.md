# QEMU-082t: cfx_power cg7 空间描述符按 profile 分派

**模块**：qemu
**项目里程碑**：M11
**依赖**：`QEMU-079t`（profile 运行时化 / Tiny）、`QEMU-080t`（Node 几何，移除 legacy profile）、`TESTCASES-094t`（`integ049t` 期望已按 `spec/Machine-v5 §1.1` 派生，`space_power` 以 BLOCKED 移交本任务）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；组件源树 `.work/source/qemu` 为 base+1 单提交、`git status` 干净；实现落任务分支 `QEMU-082t`，不 merge、不 push）

## 问题根源（现场核对，2026-11-03）

1. **唯一硬编码**：`components/qemu/patches/target/dadao/helper.c.patch:1576-1581` 的 `power[4] = {0x5, 0x3FFF_FFFC_0000, 0x4_0000, 0x5}`（256 KiB），注释 `:1559-1560` 写「power 256 KiB BootROM」；该常量是 M1–M3「单一几何（ROM 256 KiB）」时代的遗留，`QEMU-079t/080t` 引入运行时 profile 后未同步。
2. **spec 口径**：`spec/Machine-v5 §1.1`（Node 表，`:44`）BootROM = 起始 `0xffff_ffc0_0000`、**4 MiB**（cfx 内偏移 `0x3ff_ffc0_0000`、`size=0x40_0000`，`start+size == 2^42`）；复位窗口 `0xffff_ffff_0000` 是其中**末 64 KiB**。`tests/shared/machine-profiles.yaml` 的 node `bootrom_base/bootrom_size` 同值。
3. **测试期望（不动的对照面）**：`tools/testcases/arch/min_rom_probe_integ049t.py:100-104` `BLOCK0[63] = (0x5, 0x3FF_FFC0_0000, 0x40_0000, 0x5)`，并断言 `(cfxha<<42)|start == FULL_ADDR[63]`、`start+size == 2^42`。
4. **现场差异**：`space_power` 回读 `start=0x3fff_fffc_0000/size=0x4_0000`，即 `(63<<42)|start = 0xffff_fffc_0000 != 0xffff_ffc0_0000`；同册其余 **11 例 PASS**（TESTCASES-094t 完成区：`rc=1/pass=11/fail=1`，唯一 FAIL）。
5. **Tiny 口径**：`spec/Machine-v5 §1.1`（Tiny 表，`:34`）与 `:37` 明确 Tiny **不实现任何 cfx（含 `cfx_power`）**，`power` 只借地址分区。QEMU 现状已在 `helper_cfx2rd`/`helper_cfx2rc` 顶部用 `!DADAO_PROFILE(env)->cfx_enabled` → `dadao_direct_fault(CFXREG)` 挡住（`helper.c.patch:2531-2533`、`:2631-2633`），cg7 分支（`:2599`）对 Tiny 不可达；本任务须**保持**该不可达性并留证，不得为 Tiny 造描述符。
6. **legacy 口径**：`QEMU-080t` 已移除 `legacy` profile（现仅 `tiny|node`，`cpu.h.patch:144-147`）；`-bios` 只是**64 KiB 复位装载窗口**（`DADAO_BIOS_WINDOW_SIZE`），不是 BootROM 区间几何。旧 256 KiB 值**无任何 spec/profile 消费方**。

## 目标

1. cg7 `power` 描述符按**活动 profile**派生：Node `desc=0x5 / start=0x3FF_FFC0_0000 / size=0x40_0000 / attr=0x5`（`start+size=2^42`）；Tiny 不产生可读描述符（保持 `CFXREG`）。
2. 旧 256 KiB 常量与注释**明确退役**（删除，不留死值）；`smon/hmon/pmem` 三个 64 KiB 条目与 `space[1..15]=0` 语义不变。
3. `integ049t` 由 **11 PASS + 1 FAIL** 变为 **12/12 全绿**；`check-interface`、`run_m5_e2e`（含 `check-arch-smoke`）、`check-inst` 不退化。
4. 不改 `spec/`、`contracts/`、`tests/`、`gem5/`；**不得**为凑绿改任何测试期望或放宽断言。

## 接口规范

### 输入

- 活动 profile：`env->prof`，经 `DADAO_PROFILE(env)`（`cpu.h.patch:518-519`；`NULL` ⇒ `dadao_profile_node`，linux-user / 无机器 CPU 同）。
- profile 字段（`cpu.h.patch:145-160` 结构、`:181-194` 两 profile 值）：`rom_base`（Node `0xFFFFFFC00000`、Tiny `0xFFFFFFFF0000`）、`rom_size`（Node 4 MiB、Tiny 64 KiB）、`cfx_enabled`（Tiny `false`）。
- 调用点：`helper.c` 中 `helper_cfx2rd` 的 `cg == 7` 分支（`helper.c.patch:2599-2606`）。

### 输出

1. `.work/source/qemu/target/dadao/helper.c`：`dadao_cg7_space_reg()` 取活动 profile（新增参数或改签名，调用点同步），`power` 四元组由 profile 派生，期望等价式：
   - `start = prof->rom_base & ((1ULL << 42) - 1)`；
   - `size  = prof->rom_size`；
   - `desc = 0x5`（exists|ROM）、`attr = 0x5`（R|X）——Node 值；
   - Node 实测四元组必须逐字等于 `0x5 / 0x3FF_FFC0_0000 / 0x40_0000 / 0x5`，且 `start+size == 2^42`。
   - Tiny：cg7 分支在 `!cfx_enabled` 之后，**不可达**；不为其定义对外可见值（代码里可注释说明，不得回退成 256 KiB 或 64 KiB 的「Tiny 描述符」给 guest 看）。
2. `components/qemu/patches/target/dadao/helper.c.patch`：由 `python3 tools/infra/make_patch.py qemu` 重导出（**禁手工编辑补丁**），源树收敛为 base+1 单提交。
3. 重建并安装 `qemu-system-dadao`（`qemu-dadao` 若因同头文件受影响，同样须 build 树 == 安装根）。
4. `components/qemu/changelog.md` 的 `## M11` 条目（体例同 QEMU-079t/080t/081t）。
5. 证据脚本 + 日志 + 本任务书完成区（状态 `待验收`）。

### 约束

- **只动 cg7 power 派生**：`smon/hmon/pmem` 四元组与 `space[1..15]` 返回 0 不变；cg7 仍为**只读静态表**语义（写任意 cg7 rc ⇒ `CFXREG`，`helper.c.patch:2683` 起）。
- 不改 `tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、其它 `components/**`、`manifests/**`、`.tao/knowledge/discussing.md`。
- `Makefile` **预计零改动**（integ049t 已由 Makefile 以 `DADAO_TEST_PROFILE=node` 选机）；若确实需要改测试选择，只允许环境/选择行，须在完成区逐条给理由，不得改门控语义与期望值。
- 描述符值必须**从 profile 派生**（单一真源），不得在新代码里再写一遍 Node 常量作为「第二真源」；若审计认为必须写死，须给理由并保证 `start+size == 2^42` 由代码/断言守门。
- 还原纪律：任何注入/临时改动一律 `cp` 备份 + `md5sum -c` 还原；**禁** `git checkout`/`restore`/`stash`/`show <commit>:<path>`。
- 临时目录 `/tmp/opencode/QEMU-082t/`；仓库内不留临时/探针文件。

## 实施清单

### A. 源树与补丁

1. 改前自检：`make check-source-state` ⇒ `qemu: OK HEAD=… count=1 clean=True`，记旧 HEAD 与 `helper.c` md5。
2. 改 `.work/source/qemu/target/dadao/helper.c`：`dadao_cg7_space_reg()` 接收 profile，`power` 由 `rom_base/rom_size` 派生；删 256 KiB 常量与「256 KiB」注释，改注释写清「BootROM 区间按 profile（Node 4 MiB；Tiny 无 cfx，不可达）」。
3. 收敛 base+1：`git -C .work/source/qemu add target/dadao/helper.c`；`commit --amend --no-edit`；复跑 `make check-source-state`。
4. 重导出：`python3 tools/infra/make_patch.py qemu`（期望 1 written / N unchanged）。
5. 记录 `git -C .work/source/qemu diff <旧HEAD>..<新HEAD> --stat`：应仅 `target/dadao/helper.c`（行数逐条列出）。

### B. 构建与 Node 描述符

1. `make build-qemu JOBS=8`、`make install-host`；md5 对照 build 树与安装根两二进制。
2. `DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_integ049t.py --qemu .dadao/cross-toolchain/bin/qemu-system-dadao` ⇒ `12/12`、`space_power` PASS；保存四元组现场。

### C. Tiny「不实现 cfx_power」

1. 静态：`grep -n "cfx_enabled\|cg == 7" .work/source/qemu/target/dadao/helper.c` ⇒ `helper_cfx2rd/cfx2rc` 的 `!cfx_enabled` 早于 `cg == 7`（贴行号）。
2. 运行时（**证据**，非门控）：Tiny 64 KiB `bootrom-image`（`-machine dadao-m1,profile=tiny,bootrom-image=…`）首条指令执行 `cfx2rd cfx63, cg7, rc0`（编码可用 `llvm-mc` 汇编或用 `contracts/opcodes.yaml` 直接编码），期望**进程退出码 `0x84`（CFXREG）**、且任何输出/回读中都不出现描述符值。脚本置 `.work/evidence/<任务ID>/`，**不新增 `tests/` 用例**（范围外）。

### D. 回归

1. `make check-interface`；`make check-arch-smoke`（内含 `run_m5_e2e` 10/10 与 25-service 覆盖）；`make check-inst`（Node 全量 + Tiny 44）。
2. L1 `make check` 与 L2 `make check-modules`：开工前记基线、收尾复跑；既有红逐条归因，**不得**新增红、不得改范围外文件。

### E. 证据与收尾

1. `.work/evidence/<任务ID>/run.sh` 一条命令重跑 A–D 与反例；逐条捕命令自身 rc（禁 `| tee` 吞码），落 `run.EXIT`；日志按 `check-run-artifacts` A3 命名落 `.work/log/qemu/`。
2. changelog + 完成区（≤30 行）+ 状态 `待验收`。

## 验收标准

1. **硬件码退役**：`grep -n "0x3FFFFFC0000\|0x40000ULL\|256 KiB" components/qemu/patches/target/dadao/helper.c.patch` ⇒ 0 命中；`grep -n "rom_base\|rom_size" components/qemu/patches/target/dadao/helper.c.patch` ⇒ 命中派生行（贴 5 行代码 + 行号）。
2. **补丁/源树**：`make check-patch-tree` rc=0（若全量因 **gem5** 外部红，须给开工基线同红证据 + qemu 作用域 rc=0）；`make check-source-state` rc=0；`git -C .work/source/qemu diff <旧HEAD>..<新HEAD> --stat` 仅 `target/dadao/helper.c`。
3. **构建/安装**：`make build-qemu JOBS=8` rc=0；`make install-host` rc=0（rc=75 = gate.lock 占用 ⇒ 等待重跑，不作通过）；`md5sum .work/build/qemu/qemu-system-dadao .dadao/cross-toolchain/bin/qemu-system-dadao` 两哈希一致（`qemu-dadao` 同查）。
4. **integ049t 11+1 → 全绿**：`DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_integ049t.py --qemu .dadao/cross-toolchain/bin/qemu-system-dadao` **rc=0、12/12**；`space_power` PASS 且四元组逐字 `0x5 / 0x3ff_ffc0_0000 / 0x40_0000 / 0x5`（贴 `[PASS]` 行 + 汇总行）。
5. **Tiny 不实现 cfx_power**：证据探针退出码 **132（0x84 CFXREG）**，捕获 stderr/stdout 并说明无描述符输出；静态证据：`!cfx_enabled` 门在 `cg == 7` 之前（行号）。
6. **check-interface 不退化**：`make check-interface` rc=0；与开工基线逐项 diff 无新增 FAIL/DEFERRED。
7. **run_m5_e2e 不退化**：`make check-arch-smoke` rc=0（`run_m5_e2e` `10/10` + 25-service）；或按 Makefile 同一命令行直跑并给 `Results: 10/10 passed`。探针集合 `ARCH_CFX_PROBES` 中 `integ049t` 由红转绿，其余不变红。
8. **check-inst 不退化**：`make check-inst` rc=0，Node 全量 `0 failed`（deferred 计数与基线一致）、Tiny `44/44`。
9. **L1/L2**：`make check`（开工基线 + 收尾）与 `make check-modules` rc=0；既有红（已知 `check-knowledge-refs` 等）逐条给归因与基线对照，无本任务新增红。
10. **反例可达 FAIL**：把 `power` 起点临时改回 `0x3FF_FFFC_0000`（或 size 改回 `0x4_0000`）→ `make build-qemu JOBS=8` + `make install-host` → `integ049t` 的 `space_power` **FAIL**（其余 11 例仍 PASS）；`cp` + `md5sum -c` 还原后重建重装 ⇒ **12/12 回绿**。记录两次构建 rc/耗时与注入现场；全程不用 git 还原。
11. **体例/证据**：`.work/evidence/<任务ID>/run.sh` + `run.EXIT` 覆盖 1–10；日志落 `.work/log/qemu/`；`components/qemu/changelog.md` `## M11` 条目；`make check-component-changelog`、`make check-milestones-fresh`、`make check-tasks` 均 rc=0；完成区 ≤30 行；状态 `待验收`。
12. **诚实**：完成区每条与真实输出/退出码逐条对齐（禁转述/估算）；失败保留现场并按「失败处置」推进；**不改任何测试期望**。

## 说明与未决

1. **下发文字与 spec 的 size 冲突（已按 spec 解析）**：下发写「Node 4 MiB `0x3FF_FFC0_0000/0x40000`」，其中 `0x40000`=256 KiB 与「4 MiB」矛盾；按 spec-first 取 `spec/Machine-v5 §1.1` / `machine-profiles.yaml` / `integ049t` 一致的 **`size=0x40_0000`（4 MiB）**，`0x40000` 是本次要退役的旧值。若用户本意确为 256 KiB，须先立 SPEC 任务改 `spec/`，**不在本任务**。
2. **legacy 处置（本任务选「明确退役」）**：`QEMU-080t` 已删除 `legacy` profile；`-bios` 仅为 64 KiB 装载窗口，不构成几何；旧 256 KiB 值无消费方。若坚持「legacy 保持基线」，须指明由哪个 profile / 哪条路径消费该值（当前不存在），否则与 §1.1 冲突。
3. **Tiny 探针归属**：放 `.work/evidence/` 作证据，不进门控、不改 `tests/`；是否升级为常驻门控由主会话/用户裁定。
4. **共用文件**：`helper.c` 与其它 QEMU 任务可能并行 ⇒ 同文件任务串行，后开工者 rebase。

## 文件范围

- 允许：`.work/source/qemu/target/dadao/helper.c`（组件工作树，非 v5 跟踪）、`components/qemu/patches/target/dadao/helper.c.patch`、`components/qemu/changelog.md`、`.work/evidence/<任务ID>/**`、`.work/log/qemu/`、`/tmp/opencode/QEMU-082t/`、本任务书、`.tao/knowledge/milestones.md`；`Makefile` 仅在「测试选择」确有必要时（须给理由）。
- 禁止：其余一切，尤其 `tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、`components/{llvm-project,musl,picolibc,embench-iot,gem5}/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`components/qemu/series`。

## 下发前预检（5 项，现场核）

1. **内部一致**：唯一改动点 = cg7 power 派生；验收 1–12 与「文件范围」逐条对应；编号 `QEMU-082` 未被占用（`.tao/tasks/qemu/` 最大 `QEMU-081t`，`archive/**` 无 082）。
2. **前置可用**：`.work/source/qemu` 在位且 `count=1 clean=True`；`tools/infra/make_patch.py` 可跑；`make build-qemu`/`install-host` 目标存在；`.dadao/cross-toolchain/bin/{llvm-mc,qemu-system-dadao}` 在位；`min_rom_probe_integ049t.py` 开工前可跑（期望现场 `11 PASS + space_power FAIL`，作为转绿基线）。
3. **验收逐条可跑性**：1/2/4/6/7/10 现在可跑；3/8/9 需构建/安装（预计 `build-qemu`/`install-host` 各数分钟，按 QEMU-081t 实测 164 s / 83 s 量级）；`check-inst` 为 L3 单目标（数分钟~十几分钟）。
4. **与 `contracts/`、测试资产一致**：本任务零改 `contracts/`/`tests/`；期望值来源 = `spec/Machine-v5 §1.1` 与 `machine-profiles.yaml`。
5. **拟改文件 × `spec/` 清单**：全部不在 `spec/` ⇒ 无命中、无 BLOCKED。

## 参考对照（内容溯源，非执行必需）

- `DADAO-0628` 的单几何 ROM（256 KiB）是 `QEMU-081t`/`079t`/`080t` 已退役口径；本任务不复用其常量/代码，v5 以 `spec/Machine-v5 §1.1` 为唯一真源。
- `TESTCASES-094t §3` 的裁定：推荐 **A**（立 QEMU 任务修描述符，期望保持 spec 派生），本任务即 A 的落地；不采用 B（改 spec/期望）与 C（退役用例）。

## 风险

- **R1 派生式错位**：`start = rom_base & ((1<<42)-1)` 若取错位宽（如 `& 0x3F_FFFF_FFFF` 少一位）会得到 `0x1FF_FFC0_0000` 之类错值；判据 = 验收 4 的逐字四元组 + `start+size == 2^42`。
- **R2 Tiny 误判**：Tiny 下 `cfx2rd` 期望 `0x84`（CFXREG，`dadao_direct_fault`）；若实测 `0x88`(ILLI)/`0x87`，须先查 `!cfx_enabled` 门是否被改动，不得改期望。
- **R3 同文件并行**：`helper.c` 若被其它任务占用 ⇒ 串行；合并顺序以先验收者为准。
- **R4 构建/安装耗时与 gate.lock**：`install-host` 可能排队（rc=75）；保留现场、等待重跑，不手拷二进制（ISS-300）。
- **R5 基线红**：L1 已知有 gem5/knowledge-refs 类既有红；收尾不得新增，逐条给基线对照。
- **R6 changelog/台账**：漏 changelog 或 `milestones` 行会导致 L1 红；按验收 11 逐门控核对。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
