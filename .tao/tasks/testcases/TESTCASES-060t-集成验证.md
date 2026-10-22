# TESTCASES-060t: 取整指令集成验证（6 档矩阵 + 模式敏感 + 标志）

**模块**：testcases
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-162t`、`LLVM-125t`、`QEMU-072t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么要专门验

- 取整指令的坑集中在：**平局方向**（`0.5/1.5/2.5/3.5` 在"取偶"与"远离 0"下结果不同）、**`±0` 符号**、**大值原样**、**NX 只对 DYN 档置**、**DYN 档随 `rf0` 变化**。普通数值用例全部通过也不说明语义对。
- 期望值必须**独立**：由 Python 用整数/有理数运算手算（`struct` 拆位 + 明确的四种平局规则），**不得**从 QEMU/LLVM 反推。

### 现场事实（2026-10-21 核，执行前须复核）

- 6 档 immu6：`0x01` 取偶、`0x02` 远离 0、`0x04` 向 0、`0x08` 向 +∞、`0x10` 向 −∞、`0x20` 动态（`rf0[33:32]`）。
- `rf0[33:32]` 只有 4 档：`RNE/RTZ/RDN/RUP`（无 RMM）⇒ `0x20` 的模式敏感测试只能覆盖这 4 档。
- 已知偏差：`nearbyint`（LLVM）落 `0x20`，**NX 可能被置位** ⇒ 测试**只断言值**，不断言 NX。
- 集成范式：`run_atomics_probe.py` + `oracle_atomics.py`（probe + oracle + 两档）；fast 预算须现场测。

## 目标

1. **6 档 × 值矩阵**：结果位模式逐例相等（含 `±0` 符号、`|x|≥2^p` 原样、Inf/NaN）；
2. **模式敏感**：`rf0` 依次设 4 档，`0x20` 结果随之变化；
3. **标志**：静态 5 档 **不置 NX**；`0x20` 对不精确输入 **置 NX**；qNaN **不置 NV**、sNaN **置 NV**；
4. **C 层映射**：`floor/ceil/trunc/round/nearbyint` 各 1 条且值正确；
5. 用例能失败（≥2 条真实注入）、耗时可控。

## 接口规范

- **输入**：`tests/` C 用例 + `tools/testcases/` probe/oracle；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：`tools/testcases/run_rnd_probe.py`、`tools/testcases/oracle_rnd.py`（整数/有理数手算 + 自证）、C 用例（`rnd_matrix.c`、`rnd_mode.c`、`rnd_flags.c`）、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不引入外部库；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 值矩阵（每格断言完整位模式）

输入：`±0.0`、`±0.4`、`±0.5`、`±1.5`、`±2.5`、`±3.5`、`±1.0`、`2^53`（fo）/`2^24`（ft）、`±Inf`、qNaN、sNaN、最小次正规；
6 档 × 上述输入，逐例比较 64 位模式（`±0` 必须比符号位）。

### B. 模式敏感（`0x20`）

- `rf0[33:32]` 依次设 `RNE/RTZ/RDN/RUP`（用 `set.w` 写 `rf0`），对 `2.5`、`-2.5`、`1.5`、`-0.5` 断言结果；
- 每组跑完恢复 `rf0` 原值（避免污染后续用例）；
- 断言"4 档结果互不相同（在会区分的输入上）"。

### C. 标志

- 静态档：`trunc(1.5)`、`floor(0.5)` 后 **NX 不置**；
- `0x20`：`rint(1.5)` 后 **NX 置位**；对 `1.0`（已整数）**NX 不置**；
- qNaN 输入 **NV 不置**；sNaN 输入 **NV 置位**；
- 读 `rf0[4:0]` 前后各一次（清零由测试自身负责：写 `rf0` 只更新 `[33:32]` 与 `[4:0]`）。

### D. 定层

单跑测耗时；≤ fast 预算 ⇒ 纳入 `check-testcases-suites`；否则按需目标 + 完成区写明实测值。

## 验收标准

1. 值矩阵全绿（位模式比较），两档 `-O0`/`-O2`。
2. 模式敏感 4 档断言成立；每组后 `rf0` 恢复（有断言）。
3. 标志三类断言成立（静态不置 NX / DYN 置 NX / sNaN 置 NV）。
4. C 层 5 个函数各 1 条且值正确（`llc` 或反汇编抽查）。
5. **可达 FAIL ≥ 2**：① 把 `0x02`（远离 0）与 `0x01`（取偶）对调 ⇒ `.5` 用例红；② 静态档改成走真实 status（NX 置位）⇒ 标志用例红。
6. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0。
7. 证据脚本一键复跑、真实 rc 落盘。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（probe 结构、`set.w` 写 `rf0` 的方式、fast 预算）。
2. 写 oracle（手算 + 自证）→ 值矩阵 → 绿。
3. 模式敏感 + 标志。
4. C 层映射抽查；两档跑；耗时定层。
5. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- `0x01`/`0x02` 对调（临时）⇒ `2.5`/`3.5` 用例红；还原 ⇒ 绿。
- 静态档置 NX ⇒ 标志断言红；还原 ⇒ 绿。

## 已知边界（**披露**）

- **不**断言 `nearbyint` 的 NX（已登记偏差，只断言值）。
- 不做 `*mag`；不做 FP→整数转换（`fo2io` 另有覆盖）；不做性能基准。

## 完成区

**测试结果**：两档全绿 **805/805 × 2**（`-O0`/`-O2` 各 805 检查：matrix 360 / mode 120 / flags 192 / cmap 30 + 结构·构建·运行 103）；oracle 自证 **284/284**（手写平局表 + host binary64/binary32 交叉验证 + 可达 FAIL 注入）；注入自检两档 rc=0：`0x01`/`0x02` 对调 ⇒ **16** 条平局格红，5 个静态档改走 `0x20` ⇒ **40** 条 NX 格红，还原回绿且源码 md5 未变。
**修改文件**：`tests/roundint/{rnd_common.h,rnd_matrix.c,rnd_mode.c,rnd_flags.c}`（新）；`tools/testcases/{oracle_rnd.py,run_rnd_probe.py}`（新）；`Makefile`（`check-rnd-probe` 目标 + L2 成员 + help）；本册；`milestones.md` 流水行。`.work/evidence/TESTCASES-060t/run.sh`（`.work/` gitignore，与 056t 同口径不入库）。
**验收结果**（真实输出）：
1. 值矩阵：6 档 × 21 输入 × 2 格式逐例位模式（ft 比低 32 位含符号 / fo 比 64 位）+ 标志 + `rf0[33:32]` 回读 + rf0 只读位不变；静态 5 档在 `rf0[33:32]=RUP` 下跑（证明不受动态方向影响）。
2. 模式敏感：`0x20` × RNE/RTZ/RDN/RUP × {2.5,-2.5,1.5,-0.5} 逐例合 oracle，且「distinct 计数 == oracle 且 >1」；静态不可感性 20 条（4 个 rf0 值结果必须相同）；10 组 `RESTORE` 断言 rf0 复原。
3. 标志：静态 5 档 × 12 输入（1.5/0.5/-0.5/次正规等）NX 恒 0；`0x20` 不精确置 NX=0x10、整数/±0/2^p 不置；qNaN NV=0、sNaN NV=1（6 档全覆盖）；DZ/OF/UF 恒 0。
4. C 层：`floor/ceil/trunc/round/nearbyint`（double+float）值合 oracle；反汇编逐符号 1 条 `fornd`/`ftrnd`、immu6 = 16/8/4/2/32、0 call。`nearbyint` 只断言值（已登记偏差）。
5. 证据：`./run.sh`（含门控）一键 **`TESTCASES-060t evidence: PASS (11 checks)` rc=0**（≈10 min，含 L1+L2）；`./run.sh --no-gates` 快跑 `PASS (9 checks)` rc=0（5.4 s）。
6. 门控：`make check`(L1) `repository checks (L1): PASS` rc=0（38 s）；`make check-modules`(L2) `module checks (L2): PASS` rc=0（含 `check-rnd-probe: PASS (O0 + O2)`；本笔首次 8.5 min，其中 compiler-rt builtins 一次性重建）；`check-run-artifacts` `[PASS] A3 … 0 illegal` rc=0。
7. 定层：driver 单档 0.79 s（O0）/ 0.92 s（O2），证据 5.4 s ⇒ **L2**（Process-07 §3 规则 2）；L2 边际成本 ≈ 6 s（`build-musl` 3.7 s + 2 s）。挂 `_locked-check-modules`。
**新发现/坑**：① 任务书 §B「4 档结果互不相同」不可达——rf0 仅 4 档且 RNE/RTZ/RDN 对 2.5 都给 2，任何输入最多 2 个不同结果；改为「逐档合 oracle + distinct 计数 == oracle(>1)」并另设静态不可感性。② `clang` 4.3 GB / `lld` 2.1 GB 的 md5 每轮 ~13 s ⇒ 工具身份改 size+mtime+path（小文件仍 md5），driver 29.6 s → 0.9 s。③ `set.w rf0, wp2` 写 `[33:32]`、`wp0` 清 `[4:0]`，只读位（`[63:51]`/`[31:22]`/SBZ）实测不变；`nearbyint` 确实落 `0x20` 且 `2.5` 在 RUP 下取 3。④ 本笔 L2 恰好触发 compiler-rt builtins 一次性重建（install-host 前置），非本任务引入。
**遗留问题**：无未修 finding。**披露**：① 新增共享支撑头 `rnd_common.h`（任务书只列 3 个 `.c`）与 Makefile 目标（接口规范已列 Makefile 为输入）；② 负号 NaN 未纳入（canonical 化只验正号 qNaN/sNaN）；③ `nearbyint` NX 不断言（任务书已登记）；④ 不做 `*mag`/FP→整数/性能（任务书边界）；⑤ **分支时序**：实现期误在 `master` 工作树进行，完成时补建 `TESTCASES-060t`（开工时树为净；切换前后 `git status` 清单与 9 个文件 md5 逐一相同，未丢失/未改内容，未 commit）。

## 审阅记录

### 第 1 轮 engineer 自审
逐行审查 `oracle_rnd.py`（解码/编码/四档取整/expect/parse/judge）、`run_rnd_probe.py`（构建/运行/覆盖/反汇编/注入）、4 个 C 文件与 `run.sh`。发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `judge_distinct` 未按 `mode==0x20` 过滤，静态档记录混入 ⇒ 4 档敏感性恒红 | ✅已修 | 加 `int(rec["mode"],0) == DYN_MODE` 过滤 | `mode=120` 全绿；注入 O0/O2 均 PASS |
| F2 覆盖检查对无该组的 probe 也断言（matrix/cmap 在 mode/flags 上） | ✅已修 | `check_coverage(..., expected_groups)` + `if matrix/cmap/flags` | 805/805 全绿（修前 16 红） |
| F3 C 层映射只用「总数 10」判定，错了哪条不可见 | ✅已修 | 逐符号反汇编：1 条正确助记符 + immu6 == oracle 码 + 0 call | 10 条 `cmap … -> fornd/ftrnd immu6=…` 全绿 |
| F4 `_inf_bits`/zero 位模式符号约定不一致（`+0` 与 `-0` 同值） | ✅已修 | `bits_for` zero 用 `spec[1] < 0` 取符号位 | `--dump` 首行 `-0 in=8000…`、`0 in=0000…`；round-trip 全绿 |
| F5 host 交叉验证对「结果为 0」丢负号 ⇒ 17 条假红 | ✅已修 | `ival()` 按输入符号给 `-0.0` | selftest 284/284 |
| F6 注入 ② 只改 `static_modes` 数组 ⇒ 记录 mode 变化，oracle 跟着变 ⇒ 0 红（假注入） | ✅已修 | 改注 `RND_SWITCH` 的指令码（记录仍报静态档） | O0/O2 各 40 条 NX 格红，还原回绿 |
| F7 driver 每轮 md5 4.3 GB `clang`（29.6 s） | ✅已修 | `tool_id()`：>64 MiB 记 size+mtime+path | 29.6 s → 0.92 s |
| F8 `run.sh` 用 `grep "go red"` 读 driver 日志（driver 只打印 FAIL 行 ⇒ 永远无输出） | ✅已修 | 改为从 JSON 取 `N red` 并断言 N>0 | `inject-O0.json: inject 1 -> 16 red cells` |

判决：finding 全修；两档 805/805、`run.sh` 全量（含门控）`PASS (11 checks)` rc=0、`--no-gates` rc=0、L1/L2/`check-run-artifacts` rc=0。

### 第 1 轮 reviewer 验收

**判决：Accepted**（工程师达标；终审归 architect）。按要求未跑 `run.sh` 全量，改以 driver 直跑 + 门控 + 自写注入独立核验。

**重跑记录（本人终端输出 / 退出码）**
1. `python3 tools/testcases/oracle_rnd.py --selftest` → `oracle_rnd selftest: 284 checks, 0 fail` rc=0（0.1 s）。284 由本人独立推导：45 规则/守卫 + 126 host-fo + 70 ft + 40 round-trip + 2 注入守卫 + 1 覆盖 = 284 ✔。35 条手写平局表逐条按 IEEE-754 手验**全对**；期望值由 `Fraction` 精确有理数运算得出，未 import 任何组件（无 QEMU/LLVM/softfloat）⇒ **oracle 独立性成立**。
2. `run_rnd_probe.py --opt O0` → `PASS (-O0): total=805 pass=805 fail=0` rc=0（0.796 s）；`--opt O2` → `PASS (-O2): total=805 ...` rc=0（0.926 s）。805 构成由 JSON **现场派生**：matrix 360 + flags 192 + mode 120 + static 40 + cmap 30 + rf0 27 + 结构/构建/运行 43 = 805 ✔（矩阵 360 = 2 格式 × 20 输入 × (5 静态 + 4 rm)）。
3. 门控：`make check`(L1) `repository checks (L1): PASS` rc=0（37.9 s）；`make check-run-artifacts` `A3 1050 new file(s) checked, 0 illegal` rc=0，`find .work -name "*.EXIT"` 为空；L2 **读日志**（未重跑）：`check-rnd-probe: PASS (O0 + O2)` + `module checks (L2): PASS`。
4. **独立注入（临时树 + cp/md5，未用 checkout/restore/stash，仓库工作树全程 `git status` 干净）**：自行对调 `rnd_common.h` 中 `case 0x01/0x02` 发射的 immu6（非复用 driver 注入）⇒ rc=**1**，`total=805 pass=733 fail=72`，红格 matrix 16（平局格，与完成区声称 16 一致）+ mode 32 + static 16 + flags 8；`cp` 还原 + md5 对账 `7def3ca1…` 与仓库逐字节相同 ⇒ 回绿 `805/805` rc=0。

**约束核验（逐条）**
- 覆盖判定：±0 符号（`-0`→`0x8000…`/`0`→`0x0`）、`2^53`/`2^24` 全档原样且 dyn 不置 NX、Inf/qNaN/sNaN（canonical 化）、±0.5/±1.5/±2.5/±3.5 **均有区分度**（各 2 个不同结果）。
- 模式敏感：`0x20` 真设 rf0 四档，手验 `2.5→2,2,2,3`、`1.5→2,1,1,2`、`-0.5→-0,-0,-1,-0`（RNE/RTZ/RDN/RUP）全对；`static insensitivity` 20 条（去重名）全绿；27 条 `rf0 restored` 断言全绿 ⇒ 恢复有断言。
- 标志三类成立：静态 5 档 × 12 输入 NX **恒 0**（唯一非 0 为 sNaN 的 `0x01`）；`0x20` 不精确输入置 `0x10`、整数/±0/2^p/Inf **不置**；qNaN `0x00`、sNaN `0x01`（6 档全覆盖）。
- C 层 5 函数 × 2 格式：值手验全对（`floor(-2.7)=-3`、`round(±2.5)=∓3`、`nearbyint(2.5)=2`…），逐符号反汇编 **1 条正确助记符 + immu6=16/8/4/2/32 + 0 call**。
- 定层：`_locked-check-modules` → `check-rnd-probe`（前置 `install-host build-musl`）✔；**"边际 ≈6 s" 成立**——`install-host` 本就是 `test-codegen/test-elf/test-semihost` 的前置（L2 已摊销），本人实测 `build-musl` 4.1 s（声称 3.7 s）+ driver 1.7 s；**但单独跑 `make check-rnd-probe` = 71 s**（需自行支付 install-host 67.7 s），后续评估勿按 6 s 读。
- 分支纪律披露属实：`git log master -1` = `6fa884f0` ✔；`git diff master...HEAD` **仅本册 9 文件**、无其它任务内容；`milestones.md` 仅 060t 一行状态变更。
- 零改动面：`git diff master...HEAD -- spec/ contracts/` **为空** ✔。
- 完成区 12 行（≤30）✔；未提交/未 push ✔。

**非阻塞 finding（供 architect 定夺，不改判决）**
- **F-R1 driver 无害重复判定**：`run_rnd_probe.py:check_aggregates` 的 `seen` 集合在 `for fmt` 循环内重置、且 `static` 列表未按 fmt 过滤 ⇒ 20 条静态不可感性检查被判定两次（各名出现 2 次、内容相同）。**不产生假绿**（断言被加强而非削弱），但标题数 805 含 20 条重复，去重后 785。建议把 `static`/`seen` 提到 fmt 循环外。
- **F-R2 完成区叙述偏差（实际更强）**：「10 组 `RESTORE` 断言」实测 **27 组**（matrix 2 / cmap 1 / mode 19 / flags 5）全绿；其余数字均与真实输出逐条对齐。

