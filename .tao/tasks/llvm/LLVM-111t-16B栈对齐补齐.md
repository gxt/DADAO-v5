# LLVM-111t: `ADR-0031 D7` 的 16 B 栈对齐补齐（caller / callee / `va_arg` 三处一致）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-102t`（D4 整组分配与栈偏移的现实现；其完成区坑②③ + 执行期偏差② = 本册现场）、`LLVM-106t`（`long double` = binary128 的取值/搬运）、`ADR-0031 D7`（**`Accepted`**，16 B 栈对齐的依据；本册**不改 ADR**）、`ISS-275`（登记源；本册 = 落点）、`TESTCASES-047t`（5 个 `long double` 回归）、`TESTCASES-048t`（抽样回归）
**状态**：待开始

> **立册口径（2026-10-19，architect）**：这是 `Accepted` 的 `ADR-0031 D7` 的**实现补齐**，不是新决策、不改 ADR、不放宽 `D7`。`ISS-275` 的 ①（9–15 B 寄存器「偶号起」）是既有实现约束（后端只见 `[2 x i64]`，分不清 12/16 B），**本册不改**；本册只补齐 16 B 值的**栈**布局，且三处（caller / callee / `va_arg`）必须同一套规则。

## 执行环境
**执行环境**：本地

## 问题根源

**契约要求（`ADR-0031 D7`，逐字）**：「栈槽：标量 8 B；`long double` / binary128 / 16 B 值 = **16 B 占两槽、16 B 对齐**（必要时跳过一个 8 B 槽）」；「栈上 16 B 值同样高半在前」。

**现状（`LLVM-102t` D4 实现，工程师已在完成区如实披露并登记 `ISS-275`）**：
- `DADAOISelLowering.cpp` 的 `reassignDADAOArgLocs` 把 f128 与 2 块聚合的栈偏移按 **8 B 单位**推进：`StackOff += 16` 前**不做** 16 B 取整 ⇒ 紧跟在 8 B 栈参数之后时，16 B 值落在 `offset == 8 (mod 16)`；caller 的 `[rb1, 8]` / `[rb1, 16]` 两块、callee 的 `CreateFixedObject(8, offset)` 同样错位。
- `clang/lib/CodeGen/Targets/DADAO.cpp` 的 `EmitVAArg` 栈路径把 `va.stack` 直接当源地址、按 `StackBytes` 前进：**不跳过奇 8 B 槽**。
- `va_start` 的 `stack_next = incoming_sp + VarArgStackOffset`，而 `VarArgStackOffset = ArgStackSize`（同由 `reassignDADAOArgLocs` 返回）⇒ 补齐后**自动**跟随；但必须在探针中核对它确实含补位，不能另行硬编码。
- 后果：与 `D7` 字面不符；若用 `ldm.o`/`stm.o` 直通搬 16 B 会在奇数 8 B 槽上触发 `MALIGN`（`SimRISC-01` 对齐规则），`va_arg` 也会从错位处读半字。

**三处必须一致（本册核心）**：
1. **caller 传参**：`reassignDADAOArgLocs<ISD::OutputArg>` 的栈分支（`LowerCall` 用其 `LocMemOffset` + `CALLSEQ_START(NumBytes)`）。
2. **callee 退栈参数**：同一函数 `reassignDADAOArgLocs<ISD::InputArg>`（`LowerFormalArguments`）+ `CreateFixedObject(8, LocMemOffset)`；以及变参 `VarArgStackOffset`。
3. **`va_arg` 取栈**：clang `EmitVAArg` 的 `OnStackBB`（`va.stack` 的取整与前进量）。

## 判据（写死）

- **取整规则**：仅当该值在栈上占 **16 B** 时，放值**之前**把 `StackOff`（caller/callee）或 `va.stack`（`va_arg`）向上取整到 16 B（`(x + 15) & ~15`），再放高半/低半两块；若已对齐**不补位**（不得无条件加 16）。
- **覆盖集合**（前后端能对齐的唯一集合）：`f128` 与 **2 块 RD 组**（`Count == 2 && Bank == 0`；同时被 `va_arg` 的 `C.Is16`〔= 通用聚合 `Slots == 2` 或 `long double`〕选中）。后端只见 `[2 x i64]`、**无法区分 12 B 与 16 B** ⇒ 9–15 B 的两块聚合在栈上**同样**按 16 B 起（与 `ISS-275 ①` 的寄存器约定同源）；这是「**多耗 1 槽、不错值**」，须在完成区如实记录，**不得**据此改寄存器奇偶规则。
- **不覆盖**（本册零改动，写清以免误伤）：8 B 标量/指针（基线布局**不得变**）、HFA/HPA（栈上按叶逐 8 B 存取，不组 16 B 搬运）、`> 16 B` 聚合（仍按 `size` 取整 8 B、`max(8, align)`）。
- **不在本册**：不改 `spec/`、不改 `.tao/contracts/`、不改 `ADR-0031`（D7 已 `Accepted`）；不改 9–15 B 的寄存器「偶号起」；不改返回路径。
- **补丁树**：只改既有两份 patch 的终态（`series` 条目数不变、`check-patch-tree` 计数不变），编辑必须在 `.work/source/llvm-project` 进行后用 `python3 tools/infra/make_patch.py llvm-project` 导出（禁手工编辑 `.patch`，`Process-01 §6.1.1`）。

## 改动清单

### A. 后端 `DADAOISelLowering.cpp`（`reassignDADAOArgLocs`）
- f128 分支的「不 fit ⇒ 栈」：`StackOff = alignTo(StackOff, 16)` 后再 `convertToMem(StackOff)` / `convertToMem(StackOff + 8)`、`StackOff += 16`。
- 聚合分支的 `Fits == false` 且 `Pair`（`Count == 2 && Bank == 0`）：同上取整；非 `Pair`（3 块以上 / HFA / HPA）**保持** `StackOff + 8 * K`、`+= 8 * Count`（不取整）。
- 注释同步到 `ADR-0031 D7`（16 B 两槽、必要时跳过 8 B 槽）；**不得**改变 `NextSlot` / bank 游标 / 寄存器分支的任何行为。
- 保证返回的 `ArgStackSize` 含补位（`va_start` 与 `CALLSEQ` 都依赖它）。

### B. clang `DADAO.cpp`（`EmitVAArg` 栈路径）
- `OnStackBB`：当 `C.Is16` 为真时，对 `va.stack` 先做 16 B 取整再构造 `Src`；前进量仍为 `StackBytes`（= 2 槽 = 16 B）。
- 注释同步：`D7` 栈上 16 B 对齐 + 与 caller 取整同一规则；`C.Is16` 的定义（`long double` / 通用聚合 `Slots == 2`）保持不变。
- 若发现 `va_start`/`VarArgStackOffset` 之外的硬编码偏移：一并核对，但**不得**改动 `va_list` 七字段布局（`ADR-0031 D1`）。

### C. lit（结构性回归）
- 新增 `tests/llvm/lit/CodeGen/DADAO/m8-varargs-stack-align.ll`（llc）：构造「16 RD + 16 RF 已满」的调用/定义，断言
  - caller：8 B 栈参数在 `[rb1, 0]`，其后的 `f128` / 2 块值在 `[rb1, 16]`/`[rb1, 24]`（**不是** 8/16）；
  - callee：对应 `ld.o` 自 `[rbsp, 16]`/`[rbsp, 24]`；
  - 已对齐（`offset == 0`）的 16 B 值**不额外补位**（`CHECK-NOT` 相邻空槽）。
- 既有 `m6-varargs.ll` / `f128-codegen.ll` 不得回归。

## 探针（必做；独立 oracle；证据落 `.work/evidence/LLVM-111t/*`）

1. **P1 栈上地址 % 16 == 0（f128）**：变参函数 `p(int i0..i15, double d0..d15, ...)`（RD 16 槽、RF 16 槽被命名参数占满），调用时依次传 `int x`（RD 满 ⇒ 栈 offset 0）、`long double ld`（RF 满 ⇒ 栈，必须 16 对齐）、`int y`（栈 offset 32）。callee 用 `va_start` 后按 **原始 `va_list` 第 7 字段（`va.stack`）**记录三个取值点的指针值并断言：`p0 % 16 == 0`、`p1 % 16 == 0`、`p1 == p0 + 16`、`p2 == p0 + 32`；`va_arg` 读出的 `ld`/`x`/`y` 与**手算常量**逐位一致（`long double` 用可精确表示的常量，如 `1.5L`、`-3.25L`）。
2. **P2 前后布局 + 16 B 聚合**：`struct S16 { long a, b; }` 与 `struct S12 { long a; int b; }` 各一例：16 B 组在 8 B 栈参数之后必须落在 `16 (mod 32)` 边界（`% 16 == 0`），其后的 8 B 参数在 `+16`；两例的字段值/后续参数值均与手算一致（12 B 例同时记录「栈上也按 16 B 起」这一已知后果）。
3. **P3 基线对照（不引入额外对齐）**：只用 8 B 值（20 个 `int`、17 个 `double`、16 个指针）迫使溢出，改前在 `/tmp/opencode/LLVM-111t/baseline/` 用**旧安装根**保存程序输出与 `-O2 -S` 汇编；改后同参数重编 ⇒ `va_arg` 读值、`va.stack` 偏移**逐项相同**，汇编**逐字节相同**（差异应为空）。
4. **可达 FAIL**：`run.sh --inject` 至少三处（各自先 `cp` 备份 + md5）：
   - 把 P1 期望 `p1 % 16` 改成 `== 8` ⇒ 探针 FAIL；
   - 篡改一份**生成的汇编副本**（`[rb1, 16]` → `[rb1, 8]`）⇒ lit/grep 断言 FAIL；
   - 篡改 P3 基线副本一个字节 ⇒ `cmp` FAIL；
   每处还原后 md5 回到原值、默认模式回绿。**禁** `git checkout/restore/stash` 还原。

## 回归 / 门控

- `install-host` **单跑**（改后端后必须；`ISS-210`；串行、不并发），随后：
  - `make check-lit`（含新 lit 文件）；
  - `TESTCASES-047t` 5 个 `long double` **两档**：`math/(acoshl|asinhl|erfcl|lgammal|tgammal)$`，`--link-mode static` 与 `dynamic` 各一次（`--json-out` + `--work-dir` 显式，`INFRA-093t`）；
  - `TESTCASES-048t` 抽样两档：`--only 'Shootout/hello$' --only 'Olden/bh$' --only 'SingleSource/Benchmarks/Misc/mandel$' --only 'SingleSource/Benchmarks/Misc/evalloop$'`，逐例判据与改前一致（`--json-out` 必填）。
- L1：`make check`（含 `check-patch-tree` / `check-instrinfo` / `check-lit` 之外的静态门控）；另跑 `make check-tasks`、`make check-knowledge-refs`、`make check-no-residue`、`make check-milestones-fresh`、`python3 tools/infra/check_issues.py`。
- 全部 rc 须为 0；命令输出留 `.work/log/llvm/LLVM-111t-*.log`（门控日志按 `check-<name>.log` 名；一次运行一个目录，`INFRA-093t`）。
- 运行期判据须带 `timeout`（`124` = FAIL）；不得用 `cmd | tee` 吞退出码。

## 接口规范

- **输入**：本册判据 + `ADR-0031 D7`（`Accepted`）+ `LLVM-102t` 现实现（`reassignDADAOArgLocs` / `EmitVAArg`）。
- **输出**：A/B 两份 patch 的终态改动；新增 lit；`.work/evidence/LLVM-111t/*`（`run.sh` 默认 + `--inject`）；探针源码与日志；完成区。
- **约束**：
  - 临时目录仅 `/tmp/opencode/LLVM-111t/`；证据脚本与产物留仓库内证据目录（非易失）。
  - 只动本册列出的文件；越界须在完成区披露。
  - 不提交 git（提交权归 architect）；不改 `**状态**`；不改 `ADR` / `spec` / 契约。
  - 失败保留现场并继续推进；需用户语义裁定才留问（`AGENTS.md`）。

## 验收标准

1. 三处取整规则实现一致（caller / callee / `va_arg`），且 `ArgStackSize` / `VarArgStackOffset` 含补位；`f128` 与 2 块 RD 组在**奇 8 B 槽**起时补到 16 B，已对齐时不补；8 B / HFA / HPA / `>16 B` 布局不变。
2. 探针 ①②③ 全绿：地址 `% 16 == 0`、前后参数值正确、8 B 基线逐字节不变；`--inject` 三处均真实 FAIL 且还原后回绿（md5 对账）。
3. `047t` 5 个 `long double` 两档全 `pass`；`048t` 4 例两档判据与改前一致；`make check-lit` 全绿（含新 lit）。
4. L1 + 台账门控全 rc=0；`check-patch-tree` 计数不变；`install-host` 已单跑。
5. 完成区贴真实命令/退出码/关键输出（不转述），写清 12 B 栈上同补位的已知后果与 `ISS-275` 落点。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
