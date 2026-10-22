# QEMU-071t: `ftmin`/`fomin`/`ftmax`/`fomax` 执行语义（softfloat `minimum_number`）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-159t`）：`min/max` = IEEE 754-2019 §9.6 **`minimumNumber`/`maximumNumber`**。
- 边界：单 NaN（含 sNaN）⇒ 返回数字（sNaN 另置 NV）；双 NaN ⇒ **canonical qNaN**（正号、payload 0）；`−0 < +0`；`x==y` 同号 ⇒ 任一；不涉舍入。

### 现场事实（2026-10-21 核，执行前须复核）

- **QEMU softfloat 已提供** `float32_minimum_number` / `float64_minimum_number`（`include/fpu/softfloat.h` 的 `MINMAX_1(type, minimum_number, float_minmax_isnum)`）⇒ 语义与 754-2019 一致，**直接调用**，不自写比较。
- 现有 helper 范式（`gen_convert_f2i` 等）已处理：从 `rf0[33:32]` 取舍入模式（本族**不需要**，无舍入）、把 softfloat 返回的 `flags` 合回 `rf0[4:0]` ⇒ **复用该范式**（只合 flags）。
- `insn.decode`：`01000100` + opx；新增 4 条（`0x26/0x27/0x2E/0x2F`）。
- `check_qemu_trans --strict` 现为 266-4（`SPEC-159t` 新记录缺 trans）⇒ 本册收口后 **266/266**。

## 目标

1. 4 条按 754-2019 `minimumNumber` 执行（含 sNaN 置 NV、canonical NaN、`−0<+0`）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` 全绿；
3. 探针覆盖语义矩阵（见 §C），并验证**不置** NX（无舍入）。

## 接口规范

- **输入**：`components/qemu/patches/target/dadao/insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`。
- **输出**：4 条 `insn.decode`；`trans_ftmin_orrr_rf`/`trans_ftmax_orrr_rf`/`trans_fomin_orrr_rf`/`trans_fomax_orrr_rf`（或统一 `gen_fp_minmax(a, isdbl, ismax)`）；探针；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（不翻 scope）；不改其它 FP 族；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 调用与标志

- 单精度走 `float32_minimum_number` / `float64_minimum_number`（`float_maximum_number` 对应 max）；传入 `&env->fp_status`（或既有 helper 的 status 入口）；
- 返回后：`rfHB` 写结果；`flags` 按既有方式**或入** `rf0[4:0]`（不得覆盖既有位）；
- 目的 `rf0` ⇒ ILLI（`fp_check_dst_rf0`）；源可为 `rf0`。

### B. 与"分两步实现"的区别（必须能测出）

- 禁止用 `min = (a<b) ? a : b` 的朴素比较实现——它在 **单 NaN** 时返回第二操作数（错）、**双 NaN** 时返回某个 NaN（可能非 canonical）、且 **sNaN 不置 NV**。

### C. 探针矩阵（每格都要断言）

- 有序：`1 vs 2`、`−2 vs 1`（min/max 各一）；
- **`±0` 四组合**：`(+0,−0)`、`(−0,+0)`、`(+0,+0)`、`(−0,−0)`（min(−0,+0)=−0、max=+0）；
- 单 NaN：`qNaN vs 1`、`1 vs qNaN`（两序）、`sNaN vs 1`、`1 vs sNaN` ⇒ 返回数字；sNaN 两序都置 **NV**；
- 双 NaN：`qNaN vs qNaN`、`sNaN vs qNaN` ⇒ **canonical qNaN**（`0x7FC00000`/`0x7FF8000000000000`）+ sNaN 情形置 NV；
- 相等：`1 vs 1`（返回任一即可，但须与实现一致）；
- Inf：`+Inf vs 1`、`−Inf vs +Inf`；
- **标志面**：qNaN 输入 ⇒ NV **不置**；任一有限值比较 ⇒ **NX 不置**（无舍入）。

## 验收标准

1. `check_qemu_trans --strict` ⇒ **266/266**（现场输出）。
2. 探针全绿（计数现场派生），每格含**期望结果 + 期望标志**两列断言。
3. ILLI：目的 `rf0` ⇒ 真跑观察到非法指令异常。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 改用朴素 `(a<b)?a:b`（临时改 trans）⇒ 单 NaN/双 NaN/sNaN 用例红；② sNaN 不置 NV ⇒ 标志用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-159t` 登记的 issue。

## 做（阶段）

1. 现场复核（softfloat 函数签名、helper 范式、`insn.decode` FP 行、探针骨架）。
2. decode 4 条 + `gen_fp_minmax` + helper 调用 → `make build-qemu`。
3. 探针矩阵（先有序/±0，再 NaN/标志）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 朴素比较实现 ⇒ 单 NaN 返回错、sNaN 不置 NV ⇒ 红；还原 ⇒ 绿。
- 双 NaN 返回输入 NaN 而非 canonical ⇒ 红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做 `minimum`/`maximum`（NaN 传播）——CPU 无此指令，由 LLVM 展开。
- 不做 `*mag`（绝对值 min/max）；不做整数 min/max。
- 不改 `scope`（`SPEC-160t`）；不接后端（`LLVM-124t`）；不做集成（`TESTCASES-059t`）。

## 完成区

**测试结果**：探针 **111/111 PASS**（矩阵 96 + 标志 6 + 别名 5 + ILLI 4；计数现场派生；每例断言值 + `rf0[4:0]`（NV/NX 双列）+ `rf0[33:32]` + 只读位）；`--oracle`/`--selftest` PASS；注入①朴素比较 **26 红**、②丢 NV **18 红**，`cp`+md5 还原后 111/111。
**修改文件**：
- `components/qemu/patches/target/dadao/insn.decode.patch`（+4 pattern `0x26/0x27/0x2E/0x2F`，264 条）
- `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（`gen_fp_minmax` + 4 条 `trans_*`）
- `components/qemu/patches/target/dadao/helper.c.patch`（`helper_fp_minmax`：softfloat `minimum/maximum_number` + `set_default_nan_mode(1)`）
- `components/qemu/patches/target/dadao/helper.h.patch`（`DEF_HELPER_5(fp_minmax, ...)`）
- `tools/qemu/min_rom_probe_071t.py`（新增，独立 oracle）
- `.work/evidence/QEMU-071t/run.sh`（新增；`.work/` 不入库）
**验收结果**：
- `check_qemu_trans --strict`：**264/264 rc=0**（任务书 §验收 1 的「266」为立册前旧计数，现场 total 由 yaml 派生 = 264）
- `check_patch_tree` / `--source-state` rc=0；`make build-qemu` rc=0（无新增 warning）
- `make check`(L1) rc=0；`make check-modules`(L2) rc=0（含 `check_interface`）
- 探针 rc=0；`.work/evidence/QEMU-071t/run.sh` rc=0（failures=0；harness self-test a=b=c=1）
- ILLI：4 条目的 `rf0` 真跑均 exit=0x88
**新发现/坑**：
- 双 NaN 必须 `set_default_nan_mode(1)`：softfloat `minimum_number` 的双 NaN 走 `pick_nan()`（按 2-NaN 规则选输入 NaN），单 NaN 分支在其之前返回，故不受默认 NaN 影响（`fpu/softfloat-parts.c.inc` 现场核对）。
- `record_denormals_used` 置 `0x4000`（input-denormal-used），`fp_status_commit` 的 `0x1F` 掩码自然屏蔽 ⇒ 次正规输入不污染 `rf0[4:0]`。
- 注入定位函数体不能取「首次出现的 `set_default_nan_mode`」（先命中 `helper_fp_round_to_int`）；须先 index `helper_fp_minmax(`。
- 探针别名/标志用例手写期望易错（`min(-2,1)` 曾写成 1）⇒ 全部期望改为 oracle 派生。
**遗留问题**：无。`scope` 仍 `excluded`（翻转归 `SPEC-160t`）、后端归 `LLVM-124t`；`ISS-324` 本册关闭。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

范围：4 个 qemu patch + 探针 + 证据脚本；逐行比对 `spec/SimRISC-07 §4.4` 与 `contract-fp.md §19`；真跑日志 `.work/log/qemu/QEMU-071t-*.log`。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 首次注入命中 `helper_fp_round_to_int`（编译 `a/b/ismax undeclared`） | ✅已修 | 注入前先 index `helper_fp_minmax(` 再定位区间 | 两注入 md5 均变化、rebuild rc=0、探针 26/18 红 |
| F2 探针 AL1/AL2 期望手写错（`min(-2,1)` 写成 1）⇒ 2 红 | ✅已修 | AL/FL 期望统一由 oracle `expected()` 派生 | 111/111 PASS |
| F3 `numeric_cmp` 对 `±Inf` 取 `exact_value` 得 None ⇒ TypeError | ✅已修 | 增 Inf 排序分支（`−Inf < 有限 < +Inf`，同号 Inf 相等） | oracle PASS；Inf 用例绿 |
| F4 证据「源树干净」用 rc 判定（脏树 rc 也 0，可能恒真） | ✅已修 | 改 `expect_empty`（rc=0 **且**输出为空） | harness self-test 证明非空输出判 FAIL |
| F5 `expect_red` 可能被「崩溃红」冒充 | ✅已修 | 要求日志匹配 red 用例模式（`NaN`/`zeros`/`sNaN`）并打印 failed 计数 | 26/18 计数与模式双命中 |

判决：F1–F5 全部已修，无未修 finding ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-22）

**重跑记录（均本人执行，rc=真实退出码）**：
- `python3 tools/qemu/check_qemu_trans.py --strict` ⇒ `264/264 insns have trans impl (M1 156/156)`，rc=0。
- `make check`(L1) ⇒ `repository checks (L1): PASS`，rc=0（38 s）。
- 探针直跑 ⇒ `Main: 111/111 passed, 0 failed / Overall: PASS`，rc=0（1.5 s）；`--oracle` rc=0（96 matrix、16 例含 NV，由 exact Fraction 派生）、`--selftest` rc=0（5 类断言均可 FAIL）。
- `check_patch_tree`（192 patches OK）+ `--source-state`（qemu HEAD=e595f06 clean=True）rc=0。
- **独立注入**（`cp` 备份 md5=`c7210edb…`，改 `.work/source/qemu/.../helper.c` 的 `helper_fp_minmax` 为朴素 `(a<b)?a:b`，md5 变 `1b8eff46…`，重建 rc=0）⇒ 探针 **26 红**（`Main: 85/111`，±0/单 NaN/sNaN-NV/双 NaN 用例全红）；`cp` 还原 md5 回 `c7210edb…`、重建 rc=0 ⇒ **111/111 回绿**、源树 clean、工作区快照前后逐行一致。
- **本人另写 16 组手推期望用例**（±0 四组合、qNaN 两序、sNaN 两序、qNaN/qNaN、sNaN/1、有序、Inf、no-NX）真跑核**值 + rf0[4:0]** ⇒ 16/16 PASS（期望由 §4.4 手推、非采信探针 oracle）。
- ILLI：4 条目的 `rf0` 真跑均 `exit=0x88`（fault epilogue，缺检查则 exit=0，FAIL 路径可达）。

**实现核验**：`helper_fp_minmax` 直调 `float{32,64}_{min,max}imum_number`（非自写比较）+ `set_default_nan_mode(1)`（双 NaN ⇒ canonical，单 NaN 分支在 `pick_nan` 之前不受影响，与 `softfloat-parts.c.inc` 现场一致）；flags 经 `fp_status_commit` `|=` 或入 `rf0[4:0]` 不覆盖；decode 4 条 pattern 与 `opcodes.yaml` mask/value 一致（证据脚本由 yaml 派生断言）。

**约束核验**：① `git diff 916fe8a7~1..916fe8a7 -- spec/ contracts/` = 0 行，`scope` 仍 `excluded` ✅；② `ISS-324` closed、`resolved_by: QEMU-071t` ✅；③ `milestones.md` 一行 ✅；④ 完成区 20 行 ✅；⑤ L2 未重跑（按审查指令），采信 `.work/log/qemu/QEMU-071t-L2.log`（`L2_EXIT=0`、`module checks (L2): PASS`、含 check_interface 264/264）——**此为采信日志非本人重跑**。披露：本人一处误用 `tee`（md5sum 输出复制，未吞被检命令码）；`run.sh` 已逐条审读（harness self-test a=b=c=1、注入 md5 非空断言、还原后回绿+源树 clean 齐备）但按指令未重跑整脚本。

**判决：Accepted**（验收命令本人重跑全绿、独立注入红→还原回绿、六条语义与 ILLI 真跑核对无偏差）。
