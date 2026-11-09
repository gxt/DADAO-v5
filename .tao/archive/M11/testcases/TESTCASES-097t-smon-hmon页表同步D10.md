# TESTCASES-097t: smon/hmon 页表同步到 D10

**模块**：testcases
**项目里程碑**：M11
**依赖**：`SPEC-184t`（已验证；`Machine-v5 §6` D10：`PTBR=0`、L1 `0–3`、4×512 MiB、VA `[0, 2 GiB) → PA [0, 2 GiB)`、`H=1/S=1/U=J=0`、`SPF=0xFF`）
**状态**：已验证

## 执行环境
本地；只改测试 bootrom 资产，不改 spec/QEMU/gem5。

## 问题根源

`SPEC-184t` 已把 Node D10 订正为低地址 4 超页、`U=J=0`；测试资产仍是旧口径：

- `tests/shared/bootrom/step5/smon.S`：L1 index `0x1000` 一个 512 MiB 超页，VA `0x0200_0000_0000` 起，PTE `H=0`；与 D10 的 L1 `0–3`、VA `[0, 2 GiB)`、`H=1` 不一致。
- `tests/shared/bootrom/step5/hmon.S`：已按 L1 `0–3`、4 超页建表，但 PTE `HSJU=0xF`（`U=J=1`），D10 要求 `U=J=0`（`HSJU=0xC`）。

M11 不执行 smon（`machine-profiles.yaml` 的 `smon: reserved`），但测试资产必须与现行 spec 一致，避免后续 smon 任务沿用旧几何。

## 目标

1. `hmon.S`：4 个 PTE 的 `HSJU` 由 `0xF` 改为 `0xC`（`H=1`、`S=1`、`U=0`、`J=0`）；`PPN`、`SPF=0xFF`、`R/W/X/P/SP/A/D/G` 不变；注释同步。
2. `smon.S`：页表模板改为 D10 的 4 个 512 MiB 超页（L1 index `0–3`，`PPN=0/0x2000/0x4000/0x6000`），`HSJU=0xC`、`SPF=0xFF`；DMA 拷贝长度与 PTE 读回断言同步改为 4 项（或至少覆盖 PTE0 + 逐项静态断言）。
3. `smon.S` 中所有旧高地址 VA（`0x0200_...`）改为 D10 覆盖的低地址（如 `0x0000_0001_2000` 等），保持原有测试语义（同一 PA、同一 magic、同一观察寄存器）。
4. 注释/观察寄存器说明与实现一致；不删测试点、不改 magic/退出码。

## 接口规范

### 1. `tests/shared/bootrom/step5/hmon.S`

- 4 个 PTE 的 64 位常量中 `HSJU` 字段由 `0xF` → `0xC`；其余字段逐字不变。
- 顶部 PTE 注释 `HSJU=0xF` → `HSJU=0xC`（`U=J=0`）。
- 不改 PTE 数量、L1 index、PPN、DMA 长度、PTBR/PTW 流程。

### 2. `tests/shared/bootrom/step5/smon.S`

- 页表模板：4 个 PTE 位于 `cfx_pmem` SRAM **偏移 `0`**，L1 `0–3`，PPN `0/0x2000/0x4000/0x6000`；每个 PTE `HSJU=0xC`、`SPF=0xFF`、`P/SP/D/A/G/X/W/R` 与 hmon 一致。
- DMA（2c）：`src = PMEM_BASE (0x83ff_0000_0000) → dst = PA 0`、`size = 64 KiB` 整页拷贝；2a 已清零 ⇒ PA 0 页 = 全零 + 偏移 0 的 4 个 PTE，落点 `PA 0..0x18`（D10）。`cfx_ptw` 的 PTBR/PTW 流程不变。
- PTE 读回（2d）：`src = PA 0 → dst = PMEM SRAM 0x0e00`、`size = 32 字节`（4 项）；`rd14`=PTE0、`rd23-rd25`=PTE1–3，均参与自检；不再用旧的单页读回（`PA 0x8000`）。
- VA 常量：所有 `0x0200_0000_0000` 基址的访问改为 `0x0000_0000_0000` 基址；偏移（`0x12000`、`0x11000`、`0x10000` 等）与 PA 保持一致。逐个核对 `LD64 rb4/rb1/...`，不得只改页表不改访问地址。
- 注释中的「L1 index 0x1000」「VA 0x0200...」全部改为 D10 口径。

### 3. 不变项

- 不改 `tests/shared/machine-profiles.yaml`、链接脚本、`tests/shared/asm/machine-node.inc` 的几何宏。
- 不改 QEMU/gem5、spec、contracts、Makefile、门控脚本。
- 不改 `tests/parity/matrix-M11.md`（M11 收口时另案重生成）。

### 4. 连带同步（范围扩展，2026-11-05）

D10 的 `HSJU=0xC` 会改变“与 hmon.S 逐位一致”的测试资产；以下三处必须同笔同步，否则出现新的口径矛盾：

- `tools/testcases/arch/min_rom_probe_integ046t.py`：`pte_value` 期望常量 `0xF000_0000_0000_FFEF` → `0xC000_0000_0000_FFEF`，注释改 D10；不改探针逻辑。
- `tools/testcases/arch/node_probe_prelude.py`：prelude 自建 PTE 的 `HSJU` `0xF` → `0xC`；顶部“bit-identical to hmon.S”注释保留并改为 D10。（实作例外：L1 `0–2` = `0xC`；L1[3] 覆盖 user/jail 探针的 `FAULT_RECORD`/`EXIT_BLOCK`，显式加 `U+J`，否则 044t/integ048t 退化，见完成区「新发现」）
- `tests/shared/bootrom/step5/README.md`：hmon 段 `HSJU=0xF` → `HSJU=0xC`（`U=J=0`）。

## 文件范围

**修改**（入库文件）：
- `tests/shared/bootrom/step5/hmon.S`
- `tests/shared/bootrom/step5/smon.S`
- `tools/testcases/arch/min_rom_probe_integ046t.py`（期望常量 + 注释）
- `tools/testcases/arch/node_probe_prelude.py`（PTE 常量 + 注释）
- `tests/shared/bootrom/step5/README.md`（HSJU 说明）
- 本任务书
- `.tao/knowledge/milestones.md`（本行）

**不改**：上述清单之外的 `tests/**`、`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`。

## 验收标准

1. **hmon PTE**：源码中 4 个 PTE 的 `HSJU` 均为 `0xC`；`grep -n '0xffef' hmon.S` 的常量与 `PPN` 字段不变；`make build-bootrom` rc=0。
2. **smon PTE**：源码恰有 4 个 PTE，L1 `0–3`、PPN `0/0x2000/0x4000/0x6000`、`HSJU=0xC`、`SPF=0xFF`；`grep -n '0x0200' smon.S` 为 0；`make build-bootrom` rc=0。
3. **构建期断言（可 FAIL）**：证据脚本从 `smon.o`/bootrom 镜像解析 4 个 PTE 常量，断言 L1 `0–3`、PPN、`HSJU=0xC`、`SPF=0xFF`；并断言 DMA 落点（模板 SRAM 偏移 0、`src=PMEM_BASE`、`dst=0`、`size=64 KiB`、PTE 落在 `PA 0..0x18`）。注入 `0xF`/旧 PPN/模板偏移 `0x8000` ⇒ FAIL；还原后回绿（`cp`+`md5sum -c`）。
4. **Node 回归**：`make check-arch` rc=0、`make check-inst` rc=0（Node 965/970、Tiny 44/44 量级）；hmon 改动后 Node arch/inst 不退化。
4b. **连带同步**：`min_rom_probe_integ046t.py` 期望 PTE、`node_probe_prelude.py` PTE、`README.md` 均为 `HSJU=0xC`；`grep -nE '0xF000_0000_0000_FFEF|HSJU=0xF'` 在活文件 0 命中。
5. **smon 执行**：若现场有可执行 smon 的入口，跑一次并断言观察寄存器；若 `smon: reserved` 不可执行，记 **BLOCKED** 并给静态构建期断言证据，不得伪 PASS。
6. **门控**：`make check`（L1）rc=0；`make check-milestones-fresh` rc=0。
7. **范围**：`git status --porcelain -uall` 仅含文件范围清单内的 7 个文件；无临时残留。
8. **体例**：完成区 ≤30 行；证据落运行期临时目录（已清理，未归档）；状态置 `待验收`。

## 证据

- 一键证据脚本：`build-bootrom` + PTE 解析断言 + `check-arch`/`check-inst` + 门控，输出 `RUN_EXIT`。
- 注入脚本：改一处 PTE（`0xC`→`0xF` 或 PPN 旧值）⇒ FAIL ⇒ `cp`+`md5sum -c` 还原 ⇒ 回绿，输出 `INJECT_EXIT`。
- 完成区只写结论 + 命令 rc + “运行期证据已清理，未归档”。

## 说明

- 本任务只同步测试资产到 D10，不新增 smon 执行路径；M11 仍不验收 smon。
- `hmon.S` 的 `U=J=0` 改动可能影响依赖 U/J 访问的 Node 用例；若 `check-arch`/`check-inst` 出现退化，先定位是测试资产错误还是 spec 口径问题，保留现场后报告。
- 不改 `smon` 的退出码/magic/观察寄存器布局。

## 完成区

**测试结果**：`RUN_EXIT=0`（35 项检查 0 失败）。`make build-bootrom` rc=0；PTE 解析 `smon`/`hmon`（含落点）与 prelude 相等性 rc=0；三处注入（PTE0 `HSJU 0xC→0xF`、2b 模板偏移 `0→0x8000`、prelude `0xF` 副本）解析均 rc=1，`cp`+`md5sum -c` 还原后 rc=0；`make check-arch` rc=0（13 探针）、`make check-inst` rc=0（Node 965/970·5 deferred，Tiny 44/44）、`make check` rc=0（L1 90/90）、`make check-milestones-fresh` rc=0。
**修改文件**：`tests/shared/bootrom/step5/hmon.S`、`tests/shared/bootrom/step5/smon.S`、`tests/shared/bootrom/step5/README.md`、`tools/testcases/arch/min_rom_probe_integ046t.py`、`tools/testcases/arch/node_probe_prelude.py`、本任务书、`.tao/knowledge/milestones.md`（共 7 个入库文件，含 §4 范围扩展三处）。
**验收结果**：从 `smon.o`/`hmon.o` 反汇编重建 4 个 PTE：HSJU=0xC、PPN[55:29]=i、SPF=0xFF、flags=0xEF、reserved=0、PPN[28:16]=0，store 偏移 0/8/16/24；**落点**：2b `store base=PMEM_BASE+0`、2c `src=PMEM_BASE`/`dst=0`/`size=64 KiB`，PTE 最终 `PA 0/8/16/24`；prelude 常量 `0xC000_0000_0000_FFEF` == hmon.o PTE0；活文件 `grep -E '0xF000_0000_0000_FFEF|HSJU=0xF'` 0 命中。注入 smon PTE0 `0xC→0xF` ⇒ `[FAIL] PTE0-value` rc=1；注入 2b 偏移 `0→0x8000` ⇒ `[FAIL] land-PTE0-pa: final PA 0x8000, want 0x0` rc=1；prelude `0xF` 副本 ⇒ `[FAIL] prelude-const` rc=1；均还原回绿。证据脚本与日志落在运行期证据目录（未入库）。
**新发现/坑**：(0) **R1（reviewer 阻断，已修）**：2b 模板曾存 `SRAM+0x8000`，而 2c `src=PMEM_BASE` ⇒ PTE 实落 `PA 0x8000`；已把模板改到 `SRAM+0`，并把 DMA 落点纳入断言（只测相对 store 偏移会假绿）。(1) 任务书 §2「8→32 字节」实指 2d 的 PTE 读回；2c 模板整页拷贝按 spec 保持 64 KiB。(2) **prelude 不能全 `0xC`**：实测 4 PTE 全 `0xC` 时 `check-arch` rc=2（044t run_mode_0/1、integ048t user_unaffected 均 exit 0x89），因 user/jail 探针必须写 `FAULT_RECORD`(0x7FFC_0000)/`EXIT_BLOCK`(0x7FFD_0000)（落在 L1[3] 超页）。故 L1 0–2 严格 D10 `0xC`，L1[3] 用显式掩码 `0x3000_0000_0000_0000` 加 U+J（运行期 top nibble = 0xC|U|J），代码/证据双重登记；若要求 4 项全 `0xC`，须另立任务让 user/jail 探针自建页表。
**遗留问题**：smon 执行 **BLOCKED** —— Node `smon: reserved`，无执行入口；未伪 PASS，仅给 `smon.o` 静态断言证据（M11 不验收 smon）。运行期证据已留档（未入库，可清理）。

## 审阅记录

#### 第 1 轮 engineer 自审

审查范围：`hmon.S`（4 PTE 仅 HSJU nibble）、`smon.S`（4 PTE/读回/VA/自检）、step5 `README.md`、integ046t 期望常量、prelude PTE 与 U/J 例外、`run.sh` + `pte_assert.py`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书「8→32 字节」指代不明；smon 8 字节 DMA 实为 PTE 读回 | ✅已修（2c 整页 64 KiB 按 spec 保留） | 2d 长度 8→32 字节、源 `PA 0x8000→0`，rd23-25 读回 PTE1-3 | parser smon PASS；check-inst 965/970 |
| F2 旧读回源 `PA 0x8000` 在 D10 下是空 L1[0x1000] 项 | ✅已修 | 2d 改读 PA 0 | PTE0-3 解析 PASS + 自检常量 |
| F3 integ046t 探针硬编码 0xF 期望致 check-arch FAIL | ✅已修（§4 范围扩展） | 常量与注释改 `0xC000…`/ADR-0043 D10 | check-arch rc=0（13 探针；integ046t 16/16） |
| F4 日志名 `097t-*` 触发 check-run-artifacts A3 | ✅已修 | 改 `TESTCASES-097t-*.log`；脚本日志落运行期证据目录（A3 只管运行期日志目录） | make check rc=0 |
| F5 注入脚本临时目录误落 worktree 根 | ✅已修 | `TMP=运行期临时目录` | `git status -uall` 仅 7 个入库文件 |
| F6 smon 无执行入口 | ⏸登记（任务书允许 BLOCKED） | 无 | profile `smon: reserved` + smon.o 静态断言 |
| F7 prelude/README 仍 `0xF`、注释失实 | ✅已修（§4 范围扩展） | prelude L1 0–2 改 `0xC`、README 改 `0xC`；注释保留 bit-identical | check-arch rc=0；活文件 grep 0 命中 |
| F8 prelude 全 4 项 `0xC` 使 user/jail 探针退化 | ✅已修（最小例外） | L1[3] 显式加 U+J（`0x3000…` 掩码），代码/证据双重登记 | 全 `0xC` 时 check-arch rc=2（044t run_mode_0/1、integ048t user_unaffected exit 0x89）；加例外后 rc=0 |

**自审判决**：无未修的可修 finding，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**（阻断 1 条）。运行期证据目录（未入库）；我注入的两处均已 `cp`+`md5sum -c` 还原，7 个文件 md5 与开审快照逐文件相同，`git status -uall` 恰 7 行。全部命令本人重跑，未采信完成区转述。

**重跑记录（worktree 分支 `TESTCASES-097t` @ b1aa272c，rc 均取 `cmd; echo $?`）**
- 运行期证据脚本 ⇒ **RUN_EXIT=0**，`summary: 28 checks, 0 failed`
- 逐项：`make build-bootrom`=0；`pte_assert smon/hmon/prelude`=0；脚本自带注入 `smon 0xC→0xF` 解析 **rc=1**（`[FAIL] PTE0-value: got 0xf00000000000ffef want 0xc00000000000ffef`）、`cp`+`md5sum -c`=0 后回绿=0；prelude `0xF` 副本 **rc=1**；`make check-arch`=0（13 探针、0 FAIL）；`make check-inst`=0（Node 965/970、Tiny 44/44）；`make check`=0（`总计: 90 项 | PASS: 90 | FAIL: 0`）；`make check-milestones-fresh`=0（`PASS (49 行)`）
- **独立注入①（与任务书不同）**：`hmon.S` PTE1 `PPN 0x2000→0x4000` ⇒ 同一脚本 `SKIP_GATES=1` **rc=1**（`[FAIL] PTE1-value: got 0xc00000004000ffef want 0xc00000002000ffef`；24 checks/2 failed）；还原 md5=OK ⇒ 重跑 **rc=0**（24/0）
- **独立注入②（核 L1[3] U+J 例外依据）**：删 `| (0x3000_0000_0000_0000 if i == 3 else 0)` ⇒ `make check-arch` **rc=2**（`min_rom_probe_044t rc=1`、`integ048t [FAIL] user_unaffected … exit exp=0x0 got=0x89`，与完成区所述一致）；还原 md5=OK ⇒ `make check-arch` **rc=0**

**阻断 finding（语义 / 代码行为）**
- **R1：smon 的 4 个 PTE 运行期仍落在 L1 `0x1000`（PA `0x8000`），D10 要求的 L1 `0–3`（PA `0–0x18`）为全零。** 依据：模板存 `cfx_pmem SRAM+0x8000`（`rb4=rb3+0x8000`）；2c DMA `rc0=src=0x83ff_0000_0000`、`rc1=dst=PA 0`、`size=0x1_0000`、`rc3=0x1`=CFX→PA（spec `DADAO-22 §SBI` 冻结 rc0=src/rc1=dst；`Machine-v5 §6 装载语义` 要求「64 KiB 全零页表页写到 PA 0，在 L1 index 0–3 写 4 个 PTE」）⇒ PTE 落 PA `0x8000–0x8018`=`L1 0x1000–0x1003`，PA `0–0x18`=0。但 VA 已改 `0x0000_0001_2000`（L1 0）、2d 读回已改 PA 0 ⇒ 若执行必：走表空 PTE 故障、`rd14=0≠PTE0` → 0xB9。**与自审 F2「PA 0x8000 在 D10 下是空 L1[0x1000] 项」自相矛盾**——实现恰把 4 个 PTE 放在那里。证据脚本只断言相对 store 偏移 `[0,8,16,24]`，测不到 DMA 落点 ⇒ 假绿；`smon: reserved` 使其无门控可抓，正是任务要防的「沿用旧几何」。
- 修法供定夺：零页整页拷贝**先于**模板写入，再 `src=SRAM+0x8000 → dst=PA 0、size=32`（即本任务书 §2「模板偏移不变 0x8000、拷贝 8→32 字节」的本意）；或模板改存 SRAM+0。**任务书 §2 该行与实现（2c 仍 64 KiB 整页、8→32 实指 2d 读回）歧义，请架构师一并裁定。**

**约束核验**：hmon 4 PTE `HSJU=0xC`、PPN/SPF/flags 逐字不变、注释改 `ADR-0043 D10` ✓；smon 静态 4 PTE/PPN/`HSJU=0xC`/`SPF=0xFF`、`grep -c 0x0200`=0、低地址 VA 偏移与 PA 语义一致 ✓（运行期落点见 R1）；README/integ046t `0xC000…`/prelude L1 `0–2`=`0xC` 且 L1[3] U+J 显式登记（注入②证其有 044t/integ048t 实测依据，未藏）✓；活文件 `grep -nE '0xF000_0000_0000_FFEF|HSJU=0xF'` **rc=1（0 行）** ✓；`smon: reserved` 属实、完成区写 **BLOCKED** 非 PASS ✓；完成区 5 行 ≤30、修改文件 7 个与现场一致 ✓；`components/**`/`spec/**`/`Makefile` 零改动、无临时残留 ✓。
**非阻断 finding**：F-a 自审表 F3「check-arch rc=0（16/16）」与完成区「13 探针」不一致（本人实测 13 探针），文档笔误，收尾改正即可。
**环境说明**：INFRA-122t 并发重建 gem5（scons -j32）期间 gate lock 正常等待，未杀进程、未绕锁。

#### 第 2 轮 engineer 自审（R1 返工）

审查范围：R1 落点修复、2b/2c/2d 注释、`pte_assert.py --landing`、第二轮注入与还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1（reviewer 阻断）模板存 SRAM+0x8000、DMA 从 PMEM_BASE 拷 ⇒ PTE 落 PA 0x8000 | ✅已修 | 2b 模板偏移 `0→0`（去 `0x8000`），2c 保持 `src=PMEM_BASE/dst=0/64 KiB`；2b/2c/2d/文件头注释同步 | 落点断言 PTE0-3 `PA 0/8/16/24`；注入偏移 0x8000 ⇒ `[FAIL] land-PTE0-pa` rc=1 |
| F-b（reviewer）只断言相对 store 偏移，测不到 DMA 落点 ⇒ 假绿 | ✅已修 | 新增 `--landing`：解析 2b store base（`PMEM_BASE+imm`）与 2c `rc0/rc1/rc2`，断言 base==src、src-page delta==off、dst+delta==8i；缺 `--mem-inc` 时 `pmem=None`，落点断言 fail-closed（不回退读取） | 注入 2b 偏移 `0→0x8000`：解析 rc=1（`final PA 0x8000, want 0x0`）；`cp`+`md5sum -c` 还原后 rc=0 |
| F-a（reviewer 非阻断）自审表 F3 探针计数笔误 | ✅已修 | 改为「13 探针；integ046t 16/16」 | 本轮 check-arch 13 探针全过 |

**自审判决**：R1 已修、F-a/F-b 已闭环，无未修 finding，状态置 `待验收`。

#### 第 2 轮 reviewer 验收

**判决：Accepted**（R1 已闭环；2 条非阻断 finding 见末）。运行期证据目录（未入库）；开审快照 9 个文件（7 个入库 + `run.sh`/`pte_assert.py`）在本记录写入前 md5 逐文件与收审相同（`diff` 全同），`git status -uall` 恰 7 行、无临时残留；未 commit、未 push。

**重跑记录（均本人执行，rc 取 `cmd; echo $?`）**
- 运行期证据脚本 ⇒ **RUN_EXIT=0**，`summary: 35 checks, 0 failed`
- 逐项：`make build-bootrom`=0；`pte_assert smon --landing`=0、`hmon --landing`=0、prelude 相等=0；脚本自带三注入均 **rc=1**（HSJU `0xC→0xF`→`[FAIL] PTE0-value`；2b 偏移 `0→0x8000`→`[FAIL] land-PTE0-base/page-offset/pa: final PA 0x8000, want 0x0`；prelude `0xF`→`[FAIL] prelude-const`），每次 `cp`+`md5sum -c`=0 后回绿=0；`make check-arch`=0、`make check-inst`=0、`make check`=0、`make check-milestones-fresh`=0
- **独立重跑（不经 run.sh，逐条单独落 rc）**：`make build-bootrom`=**0**、`make check-arch`=**0**（13 探针、0 FAIL）、`make check-inst`=**0**（Node 970 total/965 passed/5 deferred、Tiny 44/44）、`make check`=**0**（`总计: 90 项 | PASS: 90`）、`make check-milestones-fresh`=**0**（`PASS (49 行)`）
- **独立注入（非工程师注入点）**：2c DMA `src` 立即数 `PMEM_BASE → PMEM_BASE+0x8000`（模板仍在偏移 0）⇒ 同一脚本 `SKIP_GATES=1` **rc=1**（31 checks/2 failed：`[FAIL] dma-src: src=0x83ff00008000 want 0x83ff00000000` + 4×`land-PTE*-candidates: 0 store(s)`）；`cp`+`md5sum -c`=OK ⇒ 重跑 **rc=0**（31/0）

**R1 复核（重点 1/2/3）**
- 2b 模板确在 `cfx_pmem SRAM+0`（`rd6=0`、`rb4=rb3+0`）；2a 清零 64 KiB 算术精确（146×56+16=8192 octas）；2c `src=PMEM_BASE`/`dst=PA 0`/`size=0x10000`/DIR=CFX→PA ⇒ **PTE 落 PA 0/8/0x10/0x18 = L1 0–3**；2d `src=PA 0 → dst=SRAM+0x0e00, size=0x20`。反汇编实测：`dma-src=0x83ff00000000`、`dma-dst=0x0`、`dma-size=0x10000`、`land-PTE0..3-pa = 0/0x8/0x10/0x18`（smon/hmon 均 PASS，hmon 由我单独重跑 rc=0）；3a/3b/3c/3d 均不写 PA 0–0x18 ⇒ 表不再被覆盖。
- 任务书 §2 已消除「8→32」歧义：模板偏移 **0**、2c **64 KiB 整页**、2d **32 字节读回**，与实现逐条一致；验收标准 §3 同步补入落点断言与「模板偏移 `0x8000` ⇒ FAIL」。
- 落点断言审读：store base 由 `set.zw/or.w/add.o` 递推（未知即 `None`）、首个 `cfx_pmem` DMA 的 src/dst/size，断言 `base==src`、`dst+delta==8i`、窗口内 store 恰 1；`--mem-inc` 缺省 ⇒ `pmem=None` ⇒ FAIL（fail-closed）；无恒真、无两支同果；2b 偏移与 2c src 两条独立注入路径均实测 rc=1。

**其余约束**：hmon/README/integ046t/prelude 与第 1 轮 md5 一致（本轮未动）；活文件 `0xF000_0000_0000_FFEF|HSJU=0xF` 0 命中；`smon: reserved` 属实，脚本与完成区均记 **BLOCKED**（`No PASS claimed`）非 PASS；完成区 5 行 ≤30、7 个修改文件与现场一致、`components/**`/`spec/**`/`Makefile` 零改动；完成区与第 2 轮自审数字（35 checks、3 注入 rc=1、13 探针、965/970、44/44、90/90）与我实跑逐项相符。
**非阻断 finding**：N1 自审表「缺 `--mem-inc` 时 `pmem=None`，落点断言 fail-closed（不回退读取）」不准确——缺省为 `None` 并直接 FAIL（fail-closed），无回退读取；N2 hmon 落点明细写入 `pte-hmon.log.dis` 后被随后的 prelude 解析（同名日志）覆盖，明细不留档（失败时仍会先打印到 run.sh stdout），建议两次解析分日志名。均为文档/证据体例级，收尾改即可。
**环境**：INFRA-122t 并发重建 gem5 期间 gate lock 正常等待，未杀进程、未绕锁。

#### 收尾（architect，2026-11-05）

- 按 reviewer N1 改自审表：缺 `--mem-inc` 时 `pmem=None`、落点断言 fail-closed，不是回退读取。
- N2 为证据体例级（hmon 落点明细日志与 prelude 解析同名，后者覆盖前者；失败仍先打印 stdout），记入遗留，不影响判决。
- 判决 Accepted，状态置 `已验证`。
