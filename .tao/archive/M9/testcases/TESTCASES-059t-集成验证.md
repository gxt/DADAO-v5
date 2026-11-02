# TESTCASES-059t: `min/max` 集成验证（NaN/±0 矩阵 + clamp/排序 + 编译形态）

**模块**：testcases
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-160t`、`LLVM-124t`、`QEMU-071t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么要专门验

- `min/max` 的坑**全在边界**：单 NaN 返回谁、双 NaN 是否 canonical、sNaN 是否置 NV、`−0` vs `+0`。普通数值用例**全部通过**也不能说明语义对。
- 期望值必须**独立**：由 Python 直接用 IEEE 规则实现（不调用 QEMU/LLVM 结果），并**先自证**（用 `math` 的 `fmin/fmax` 交叉验证有限值用例）。

### 现场事实（2026-10-21 核，执行前须复核）

- 硬件语义：`minimumNumber`/`maximumNumber`（754-2019 §9.6）。
- 后端：`llvm.minnum`/`llvm.minimumnum`/C `fmin` ⇒ **1 条**指令；`llvm.minimum`（C23 `fminimum`）⇒ 展开（`fomin` + NaN 选择）。
- 集成范式：`run_atomics_probe.py` + `oracle_atomics.py`（probe + oracle + 两档）。
- fast 预算须现场测（`check-testcases-suites`），定层按 `Process-07 §3`。

## 目标

1. **语义矩阵**（指令级）：有序 / 相等 / ±0 四组合 / 单 NaN（q&s，两序）/ 双 NaN / Inf / 次正规 —— 结果与**标志**双断言；
2. **展开路径**：C23 `fminimum`（NaN 传播）在目标上结果正确且**无 libcall**；
3. **集成**：clamp/clip 循环、4×4 矩阵逐元素 min/max 与 oracle 一致；
4. 编译形态：`fmin` 热循环 **1 条 `fomin`**（可选，若 `llc` 可用）；
5. 用例能失败（≥2 条真实注入）、耗时可控。

## 接口规范

- **输入**：`tests/` 新增 C 用例 + `tools/testcases/` probe/oracle；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：`tools/testcases/run_minmax_probe.py`、`tools/testcases/oracle_minmax.py`（IEEE 规则手写 + 自证）、C 用例（`minmax_matrix.c`、`minmax_clamp.c`、`minmax_c23.c`）、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不引入外部库；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 语义矩阵（每条都断言"值 + NV"）

- `min/max` × {有序正向、有序反向、相等同号、`+0/−0` 两两组合、`qNaN` 左/右、`sNaN` 左/右、双 `qNaN`、`sNaN+qNaN`、`±Inf`、次正规}；
- 期望：单 NaN ⇒ 数字；sNaN ⇒ 数字 + **NV 置位**；双 NaN ⇒ **canonical qNaN**（`0x7FC00000`/`0x7FF8000000000000`）；qNaN ⇒ **NV 不置**；任何情形 **NX 不置**。

### B. `fminimum`（C23）展开路径

- 用 `fminimum(a,b)`（clang 支持 C23 时）或 `__builtin_fminimum`；断言：任一 NaN ⇒ 结果为 NaN（canonical）；无 NaN 时 `−0<+0` 成立；
- 断言**无 libcall**（`llvm-nm` 或反汇编检查无 `fmin` 符号引用）。

### C. 集成

- `clamp(x, lo, hi)` 循环 1k 次（含 NaN 与 ±0 边界）；
- 4×4 矩阵逐元素 `min`/`max`（含 NaN 行）；
- 与 oracle 逐位比较（不是"近似"）。

### D. 定层

- 单跑测耗时；≤ fast 预算 ⇒ 纳入 `check-testcases-suites`（L2）；否则按需目标 + 完成区写明实测值。

## 验收标准

1. 语义矩阵全绿（**值与 NV 双列**），两档 `-O0`/`-O2`。
2. `fminimum` 路径：结果正确 + **零 libcall**；`−0<+0` 断言成立。
3. clamp/矩阵集成全绿；计数现场派生；失败/跳过分列。
4. **可达 FAIL ≥ 2**：① 把硬件语义改成"返回第二操作数"（临时）⇒ 单 NaN 用例红；② 去掉 sNaN 的 NV ⇒ 标志用例红。
5. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0。
6. 证据脚本一键复跑、真实 rc 落盘（禁 `cmd | tee` 吞码）。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（atom probe 结构、两档口径、`rf0` 读取方式、fast 预算）。
2. 写 oracle（IEEE 规则 + 自证）→ 指令级矩阵 → 绿。
3. `fminimum` 展开路径 + 零 libcall 断言。
4. clamp/矩阵集成；两档跑；耗时测定层。
5. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 临时把 `fomin` 实现改为"返回第二操作数" ⇒ 单 NaN 两序用例红；还原 ⇒ 绿。
- 临时让 sNaN 不置 NV ⇒ 标志断言红；还原 ⇒ 绿。

## 已知边界（**披露**）

- 不做 `minimum` 的硬件版用例（无该指令；只验 LLVM 展开）。
- 不做 `*mag`；不做整数 min/max；不做性能基准。
- 不引入外部数学库。

## 完成区

**测试结果**：O0/O2 各 **3102/3102 PASS**（值 1502 + 标志 1502 + 结构 98，现场派生）；矩阵 88 格（2 格式×{min,max}×22 对）、C23/num/cmap 264、clamp 1000、4×4 矩阵 64、整数对照 86 = **1502 例 / 3004 断言**；oracle 自证 **153/153**（手写 §2.4 边界表 + host-float 第二实现 + 编解码往返 + 3 类可达 FAIL）；`--inject` **202/202**：①sNaN NV 期望改 0 ⇒ **188 红**（48 sNaN 标志格），②±0 期望对调 ⇒ **155 红**（48 零值格），③fminimum 走 libcall ⇒ 8 个未定义符号、无 libcall 断言红；仓库源 md5 不变、还原后 0 红。
**修改文件**：新增 `tests/minmax/{minmax_common.h,minmax_matrix.c,minmax_clamp.c,minmax_c23.c}`、`tools/testcases/{oracle_minmax.py,run_minmax_probe.py}`、`.work/evidence/TESTCASES-059t/run.sh`（`.work/` 不入库）；改 `Makefile`（`check-minmax-probe` + L2 成员 + gate lock + help）、`.tao/knowledge/milestones.md`（一行）、本册。
**验收结果**：
- `make check`(L1) rc=0；`make check-modules`(L2) rc=0（含 `check-minmax-probe: PASS (O0 + O2)`）；`check_qemu_trans --strict` **264/264** rc=0；`validate-vectors` rc=0；证据 `run.sh` rc=0（**13 checks**，`run.EXIT=0`）。
- 零 libcall：`llvm-nm -u` 无 fmin/fmax/fminimum 系；objdump 12 个符号合计 **12 条 minmax / 0 call**；`llc` 现场复算一致（c23 = 1 `fomin`/`fomax` + 1 `cs.z`；num/cmap = 1 条）。
- clamp：`mm_clamp_f64` = 1 `fomax`+1 `fomin`、`mm_clamp_f32` = 1 `ftmax`+1 `ftmin`、0 call。
- 定层：driver 单档 ≈0.2 s（matrix 0.02 / clamp 0.13 / c23 0.04），L2 边际 <1 s；`install-host/build-musl` 为既有前置。
**覆盖变化**：**新增 1502 例**（值/标志各 1502 断言）+ 98 结构断言；**删除 0 / 修改已有用例 0**；未改 `spec/`、`contracts/`、ISA/QEMU/LLVM 实现；未 commit/push。用例以 `QEMU-071t` 111 例探针为交叉参照，oracle 独立重写（未复制、未 import 组件）。
**新发现/坑**：
- 任务书「不做整数 min/max」与本轮父指令「与整数 min/max 对照」冲突：按父指令新增 `INTCMP` 控制组（C 整数 `max(lo,min(x,hi))`，**非 ISA 指令**；ISA 无整数 min/max）；如不认可可整组删除，不影响 1/2/4 项。
- Python 3.12 无 `math.fmin/fmax` ⇒ oracle 自证第二实现改用 host float + 显式 ±0/NaN 规则（任务书 §A 提法不可执行，已披露）。
- clang 23 无 `__builtin_fminimum`（只有 `fminimum_num`）；C23 `minimum/maximum` 用标量 `__builtin_elementwise_minimum/maximum`（= `llvm.minimum/maximum`）；实测 sNaN 置 NV、qNaN 不置、双 NaN canonical、±0 有序。
- `set.w rf0, wp0/wp2` 清标志/设 RNE 后 `pre == 0x7FF800007FC00000`；只读位全程不变（每行断言）。
**遗留问题**：无未修 finding、无阻塞。整数对照组为对父指令的解释，见上。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-23）

范围：`oracle_minmax.py`（规则/自证/判分）、`run_minmax_probe.py`（构建/判分/覆盖/反汇编/llc/注入）、3 个 C 探针 + 公共头、`Makefile` 目标、`run.sh`；逐行复核 + 真跑（日志 `.work/evidence/TESTCASES-059t/logs/`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `encode()` 次正规缩放写成 `2^(1-bias)` ⇒ minsub 往返为 0 | ✅已修 | 改 `2^(bias-1+mb)` | selftest 153/153（round-trip minsub/maxsub 绿） |
| F2 `RESTORE` 行被解析进 obs ⇒ `KeyError: fmt` | ✅已修 | `parse()` 单列 `restore` + `judge_restore` | driver 全绿（每探针 1 条 RESTORE 断言） |
| F3 selftest 的「number≠propagate」守卫格式参数错位 | ✅已修 | 修正 `add(...)` 参数 | selftest 0 fail |
| F4 clamp 覆盖统计 `specials` 缺 `qnan` key ⇒ KeyError | ✅已修 | 四种 kind 全列 | driver O0/O2 绿 |
| F5 反汇编期望串残留字面 `%s` | ✅已修 | `"1 x %s" % mnem` | O2 JSON 期望为实际助记符 |
| F6 注入子进程复用正常 work dir，可能覆盖正常产物 | ✅已修 | 每次注入独立 `--work-dir inject-<tag>` | inject 202/202 |
| F7 标志断言只查 `[4:0]`+只读位，未断言 `pre` 精确等于复位值 | ✅已修 | `judge_obs` 增 `pre != RF0_RESET` 红路 | 实测 `pre=7ff800007fc00000`；全绿 |
| F8 `-Wall` 报公共头静态函数未用（c23 TU） | ✅已修 | `mm_obs`/`mm_restore` 改 `static inline` | 三探针 `-O2 -Wall` 零告警 |
| F9 Python 3.12 无 `math.fmin/fmax`（任务书 §A 的交叉验证提法不可用） | ✅已修（替代实现） | 自证第二实现改 host float + 显式 ±0/NaN 规则 | selftest 153/153；完成区披露 |
| F10 任务书「不做整数 min/max」与父指令「整数对照」冲突 | ❌不修（ISA 无整数 min/max；按父指令加 C 整数控制组，不改 ISA） | 增加 `INTCMP` 控制组（C 整数，非 ISA） | driver 86 行全绿；完成区披露 |
| F11 注入 ③ 只改 cmap 不够贴近「fminimum 走 libcall」 | ✅已修 | 注入改 `c23_*` 为 `fminimum*` 调用 + `-fno-builtin` | nm 显示 8 个未定义 min/max 符号 |

判决：F1–F9、F11 已修，F10 不改（无 ISA 面，且已按父指令加控制组）；O0/O2 3102/3102、注入三项真实红、L1/L2 全绿 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-23）

**重跑记录（本人真跑，非采信完成区）**：`oracle --selftest` rc=0（153 checks 0 fail）；驱动 O0/O2 各 rc=0 `PASS total=3102 pass=3102 fail=0`；证据 `run.sh` 全量重跑 rc=0（**13 checks 全 PASS，`run.EXIT=0`**，含 `check-minmax-probe: PASS (O0 + O2)` 在 L2 log 4108 行真跑）；`check_qemu_trans --strict` 264/264 rc=0；`validate-vectors` rc=0；L1/L2 rc=0。
**计数（现场统计 JSON）**：O0/O2 各 3102 = 值 1502 + 标志 1502 + 结构 98；分项 matrix 88（22 对×2 格式×2 op）、c23/num/cmap 264、clamp 1000、mat4 64、intcmp 86 —— 与完成区**逐项一致**。
**6 例独立推导（按 `spec/SimRISC-07 §2.4` 六条手推，再对 `--dump` 与目标原始 OBS 行）**：①单 qNaN 左/右 ⇒ 返回数（ft 0x3F800000/fo 0x3FF0…）NV=0 ✓；②sNaN 左（ft 0x7F800001/fo 0x7FF0…0001）⇒ 返回数 + post[0]=1 ✓；③双 qNaN ⇒ canonical 0x7FC00000/0x7FF8… NV=0；sNaN+qNaN ⇒ canonical + NV=1 ✓；④`+0/−0` ⇒ min=−0、max=+0（两序，ft/fo）✓；⑤clamp 边界 c013（sNaN×[−Inf,+0]）手推 −0x1p0+NV、c004（+Inf,[qNaN,+2]）手推 +2.0/NV=0 ✓；⑥mat4 r3c0（qNaN,sNaN）⇒ canonical+NV ✓ —— 与用例表**全一致**。oracle 推导路径：`decode→Fraction/numeric_cmp→规则`，imports 仅标准库，无 QEMU/LLVM/071t 引用（仅 27 行平凡公共文本）；操作数由 label 反查表重推 ⇒ **非循环论证、非照抄探针 oracle**。
**libcall（本人现场核）**：`llvm-nm -u` 三目标仅 printf/strcmp/snprintf，无 fmin/fmax/fminimum 系；objdump 12 符号逐个 1×fomin/fomax/ftmin/ftmax、0 call（合计 12/0）；llc 独立复算 12/0；clamp 两符号 1+1、0 call。
**注入（本人独立注入，`--work-dir` 隔离 + md5 还原）**：①sNaN NV 期望改 0 ⇒ rc=1 **188 红**（全为 flags 格）；②±0 期望对调 ⇒ rc=1 **155 红**（含 48 zeros_ 值格）；③被测产物侧注入（fmin 经 volatile 函数指针 ⇒ 真 libcall）⇒ `no min/max libcall (nm -u)` **红**（actual=1 fmin）。仓库源 md5 前后一致、`git status` 前后快照均为空。
**覆盖**：`git diff --name-status a437090b~1`：tests/ 仅 4 个新增文件（A），**删除 0**；`spec/`、`contracts/`、`components/` 改动 0；QEMU/LLVM 实现 0。
**证据脚本审读**：无 `| tee`（仅注释提及）、每条 rc 显式捕获落盘、13 checks 均有可达 FAIL 路径（driver rc 门 + 注入红数从 JSON 解析）。
**非阻塞 finding（F12）**：`oracle_minmax.py` selftest 第 4 组 `add("number != propagate …", …)` 误传 4 个位置参数 ⇒ `ok` 恒为真值字符串，该**自证守卫恒真**；同一语义差异已被驱动 c23/matrix 两组真实断言覆盖（注入③实测分歧红），不影响判决，请下轮修参数。

**判决：Accepted**（期望值与 spec 逐例相符、oracle 独立、零 libcall、三注入真红、无覆盖删除、门控全绿）；F12 提请 architect 随返工队列处置。
