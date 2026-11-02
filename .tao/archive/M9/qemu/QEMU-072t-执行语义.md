# QEMU-072t: `ftrnd`/`fornd` 执行语义（softfloat `round_to_int` + 5 静态模式 + DYN）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-161t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-161t`）：`immu6` one-hot 六档
  `0x01` 取偶 / `0x02` 远离 0 / `0x04` 向 0 / `0x08` 向 +∞ / `0x10` 向 −∞ / `0x20` 动态（读 `rf0[33:32]`，置 NX）。
- 共同边界：sNaN ⇒ NV + qNaN；qNaN 原样；`|x| ≥ 2^p` 原样；`±0` 符号保留；Inf 原样；5 个静态档**不置** NX。

### 现场事实（2026-10-21 核，执行前须复核）

- softfloat 已有 `float32_round_to_int` / `float64_round_to_int`（按 `float_status.float_rounding_mode` 取整，**已处理** ±0/Inf/NaN/大值）；
- 模式枚举含全部 5 种：`float_round_nearest_even`、`float_round_ties_away`(4)、`float_round_to_zero`、`float_round_down`、`float_round_up` ✓ ⇒ **静态档无需自写取整**；
- 现有 helper 范式：读 `rf0[33:32]` 取舍入、把 flags 或回 `rf0[4:0]` ⇒ 复用；
- `check_qemu_trans --strict` 现缺 2 条 ⇒ 本册收口后应全绿。

## 目标

1. 六档语义与 754-2019 一致（**NX 只有 `0x20` 置**）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` 全绿；
3. 探针覆盖"模式敏感"用例（同一输入在 4 种 `rf0` 模式下的 `0x20` 结果）。

## 接口规范

- **输入**：`insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`。
- **输出**：2 条 `insn.decode`；`trans_ftrnd_orri_rf`/`trans_fornd_orri_rf`（共用 `gen_fp_round_to_int(a, isdbl)`）；探针；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不改其它 FP 族；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 静态 5 档：临时 `float_status` + 只合 NV

1. 复制真实 `fp_status` 到临时结构，设 `float_rounding_mode` = 目标模式；
2. 调 `float{32,64}_round_to_int`；
3. **只**把返回的 **NV** 合回真实 `rf0[4:0]`，**丢掉 NX**（静态档不置 inexact）；
4. 结果写 `rfHB`。

> 若直接改真实 status 的 mode，再改回，会**污染**并发/后续指令的 mode 与标志 ⇒ **必须**用副本 + 选择性合并。

### B. DYN（`0x20`）：直接用真实 status

- 直接 `float*_round_to_int(x, &env->fp_status)` ⇒ 内部按 `rf0[33:32]` 取整，**NX/NV 都合回**（= `roundToIntegralExact`）。

### C. 合法性

- `immu6` 非 one-hot ⇒ ILLI（`encode_onehot`，与 `rev.o` 同规则）；目的 `rf0` ⇒ ILLI（`dst_rf0`）。

### D. 探针矩阵

- 输入集：`±0.0`、`±0.4`、`±0.5`、`±1.5`、`±2.5`、`±3.5`、`±1.0`、`2^53`（fo）/`2^24`（ft）、`+Inf`、`−Inf`、qNaN、sNaN、次正规；
- 6 档 × 上述输入，逐例断言**结果位模式**（`±0` 符号、`0.5` 的取偶/远离差异、`2.5`/`3.5` 的取偶结果）；
- **模式敏感专测**：把 `rf0[33:32]` 依次设为 `RNE/RTZ/RDN/RUP`，对同一组输入跑 `0x20`，断言结果随模式变化；
- **NX 专测**：静态档（如 `trunc(1.5)`）后 **NX 不置**；`0x20`（`rint(1.5)`）后 **NX 置位**；qNaN 输入 **NV 不置**；sNaN 输入 **NV 置位**。

## 验收标准

1. `check_qemu_trans --strict` 全绿（现场输出）。
2. 探针全绿（计数现场派生），含 **6 档 × 边界值**、**4 种模式敏感**、**NX/NV 标志**三类断言。
3. ILLI：`immu6=0x03`（非 one-hot）、`immu6=0`、目的 `rf0` ⇒ 真跑观察到非法指令异常（3 例）。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 静态档也走真实 status（NX 被置）⇒ NX 用例红；② `0x20` 写死 RNE 不读 `rf0` ⇒ 模式敏感用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-161t` 登记的 issue。

## 做（阶段）

1. 现场复核（softfloat 模式枚举、`round_to_int` 行为、helper 范式、探针骨架）。
2. decode 2 条 + `gen_fp_round_to_int`（静态副本 / DYN 直连）。
3. 探针（先值矩阵，再模式敏感，再标志）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2**）

- 静态档直接改真实 status ⇒ NX 被置 ⇒ 红；还原 ⇒ 绿。
- DYN 档写死 RNE ⇒ 模式敏感用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- `nearbyint` 无硬件变体（落 DYN，NX 可能置位 —— 已在 `SPEC-161t` 登记）。
- 不做 `*mag`；不改 `fo2io` 转换族（FP→整数另有指令）。
- 不改 `scope`（`SPEC-162t`）；不接后端（`LLVM-125t`）；不做集成（`TESTCASES-060t`）。

## 完成区

**测试结果**：探针 **413/413**（`Main: 413/413 passed, 0 failed`）；oracle PASS（22 ft + 22 fo 样本、26 组模式敏感）；selftest 4/4；`check_qemu_trans --strict` **260/260** rc=0；注入①静态档置 NX ⇒ 278/413（**135 红**）、注入②DYN 写死 RNE ⇒ 379/413（**34 红**），cp+md5 还原后均回绿 413/413；L1 rc=0（38s）/ L2 rc=0（416s，含 `check_interface`）。
**修改文件**：`components/qemu/patches/target/dadao/insn.decode.patch`（2 条 pattern，260 计数）、`helper.c.patch`（`helper_fp_round_to_int`）、`helper.h.patch`（`DEF_HELPER_4`）、`insn_trans/trans_fp.c.inc.patch`（`gen_fp_round_to_int` + 2 条 trans）；`tools/qemu/min_rom_probe_072t.py`；`.work/evidence/QEMU-072t/run.sh`；`.tao/tasks/qemu/QEMU-072t-执行语义.md`、`.tao/knowledge/issues.yaml`（`ISS-322` closed）、`.tao/knowledge/milestones.md`（一行）。
**验收结果**：`check_qemu_trans: 260/260 insns have trans impl (M1 156/156)`；探针 `Main: 413/413 passed, 0 failed`（413 = 220 静态矩阵 + 176 DYN 矩阵 + 10 NX/NV + 4 别名/rf0 源 + 3 ILLI，计数由脚本现场派生）；注入日志 `QEMU-072t-inject-{a,b}-probe.log`（rc=1）+ `...-restore-probe.log`（rc=0）；`run.sh` rc=0（落盘 `.work/evidence/QEMU-072t/run.rc` = 0）。
**新发现/坑**：① `make apply-series` 现报 `KeyError: 'patch_dir'`（enabled `patchless` 组件、既有缺陷）⇒ 改补丁后按 `docs/Process-01 §7` 以单组件重放（`reset --hard base` → 逐 patch `git apply` → commit）落地；证据脚本只依赖「已应用源树」并在首步自检（helper 在、源树 clean）。② NaN 口径：任务书摘要写「qNaN 原样」，`contract-fp.md §18`/spec 写「canonical 化」⇒ 按 Spec-first 取 canonical（`set_default_nan_mode(1)`；sNaN 另置 NV），AL4 固定 `−qNaN→+qNaN`；若要 payload 保留需改任务书口径。③ L2（416s）>5min，证据脚本前台运行并打印 elapsed，未转后台。④ L1 `check-milestones-fresh` A5：未完成任务时间列须为登记时间并带 `（登记）`、表状态须等于册状态（本次已按 `待验收` + `（登记）` 修正）。
**遗留问题**：无（`scope` 翻转归 `SPEC-162t`、LLVM 后端归 `LLVM-125t`、集成归 `TESTCASES-060t`，均非本册）。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-22）

代码级逐行审查（`helper_fp_round_to_int` 四段 / `gen_fp_round_to_int` 四段 / decode 2 行 / patch 生成），findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 静态 5 档是否真独立于 `rf0[33:32]`（易误用真实 status） | ✅已修 | helper 用本地 `float_status` 副本 + 静态模式覆盖；探针静态矩阵刻意用**另一** rf0 模式（`0x08`→RDN、其余→RUP） | 220 个静态例全绿；注入① 135 红 |
| NaN 口径（册摘要「原样」vs 合约 §18「canonical 化」） | ✅已修 | `set_default_nan_mode(1)` ⇒ 统一 canonical qNaN；sNaN 另置 NV | NX5/NX6/NX7/NX10/AL3/AL4 |
| one-hot 判据边界（6 位：0/0x03/0x21…） | ✅已修 | `code == 0 \|\| (code & (code-1)) != 0` ⇒ ILLI；`0x21` 超 6 位不可编码 | IL1/IL2 真跑 exit=0x88 |
| S1D1 别名（src==dst）与源为 `rf0` | ✅已修 | 先 `load_rf` 后 `store_rf`（与 `gen_fp_root` 同范式） | AL1/AL2/AL3 全绿 |
| NX 仅 `0x20`、NV 仅 sNaN | ✅已修 | 静态合 `float_flag_invalid`；DYN 合 `invalid\|inexact` | NX1–NX10；注入① 静态 NX 135 红 |
| 探针断言恒真/计数写死 | ✅已修 | selftest 4 类断言各带可达 FAIL；`run.sh` 以 `probe_meta` 现场派生计数（409→413 自动跟随） | `--selftest` PASS；run.sh 断言全 PASS |
| 注入还原纪律（禁 git 还原） | ✅已修 | `cp` 备份 + md5 前后一致 + 重建后回绿；`trap` 兜底还原 | `inject-*-restore-probe.log` rc=0 |
| patch 手工改 hunk 计数/`index` 易错 | ✅已修 | 由 `/tmp/opencode/QEMU-072t/patchtool.py` 从重建文件重生成（blob 用 `git hash-object`，计数自动）；decode 由 `generate_decodetree.py` 从 yaml 机械派生 | 源树重放 60 patch rc=0，应用后内容与重建文件逐字节一致 |

判决：全部 finding 已处置（✅），无未修项 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-22）

**重跑记录（均 reviewer 亲跑，workdir=仓库根）**：
- `python3 tools/qemu/check_qemu_trans.py --strict` ⇒ `260/260 insns have trans impl (M1 156/156)`，rc=0。
- `python3 tools/qemu/min_rom_probe_072t.py` ⇒ `Main: 413/413 passed, 0 failed`，rc=0（6s）；计数现场派生 cases=413（静态 220 + DYN 176[模式 0/1/2/3] + NX/NV 10 + AL 4 + ILLI 3）。
- `--selftest` ⇒ 4/4 类断言均可 FAIL，rc=0；`--oracle` ⇒ `PASS (22 ft + 22 fo, 26 mode-sensitive groups)`，rc=0。
- `make check`(L1) ⇒ rc=0（39s，`check_issues: resolved_by 约束 OK`）；L2 未重跑（用户约束），读日志：check-interface 83 项 FAIL: 0、`module checks (L2): PASS`。
- ILLI 三例独立真跑（模块内单跑）：`immu6=0x03`/`immu6=0`/目的 rf0 ⇒ 均 `exit=0x88`。
- 独立注入（cp+md5，禁 checkout）：静态合标志改 `& 0x1F`（NX 泄漏）⇒ 重建 6s ⇒ 探针 `278/413, 135 failed` rc=1（`rf0[4:0] expect=0x00 got=0x10 MISMATCH` ×135，NX1 红）；cp 还原 ⇒ md5 `5428370b…` 相等、二进制 md5 复原 `c3d7a6c7…` ⇒ 回绿 `413/413` rc=0。

**约束核验**：静态 5 档用临时 status 副本、只合 `float_flag_invalid`（helper.c.patch 逐行核）✓；DYN 走 rf0 派生 status、合 NV|NX ✓；首读后写（先 `load_rf(hc)` 后 `store_rf(hb)`，AL1/AL2 别名例绿）✓；`spec/**`、`contracts/**` 对 HEAD 零 diff ✓；ISS-322 `closed`+`resolved_by: QEMU-072t` ✓；快照对账 pre/post `git status` 均 0 行一致、`.work/source/qemu` clean、无 `.EXIT` ✓；NaN 口径披露成立：代码 `set_default_nan_mode(1)` ⇒ qNaN→canonical（不置 NV，NX5/AL4 绿）、sNaN→NV+canonical（NX6/NX7 绿），与 `contract-fp.md §18`/spec §4.3「canonical 化」一致（任务书摘要「原样」为过时措辞，已披露，spec-first 取 canonical 正确）。

**不符项（唯一）**：`milestones.md` 一行与 `ISS-322` 关闭注记写「探针 409/409、注入 133/34 红」（`run.sh` 头注释亦写 409），与现场不符：真实 413/413、注入① 135 红（完成区/commit message 正确，工程师日志 inject-a 亦 135）。

**判决：Needs Revision**（仅文档数字更正，无代码/探针改动）：① `milestones.md` QEMU-072t 行改「探针 413/413，注入 135/34 红」；② `issues.yaml` ISS-322 关闭注记同步改 413/413、135/34；③ `run.sh` 头注释 409→413。改后可直接 Accepted（其余验收项全部通过）。

### 第 2 轮 reviewer 验收（2026-10-22，只核第 1 轮唯一打回项）

**重跑记录（reviewer 亲跑，workdir=仓库根）**：
- `git show --stat 77cfe233` ⇒ 仅 2 受跟踪文件：`.tao/knowledge/issues.yaml`、`.tao/knowledge/milestones.md`（各 1 行改）✓；`run.sh` 在 `.work`（gitignore）不入 git ✓。
- `grep "409/409" milestones.md issues.yaml run.sh` ⇒ 零命中（rc=1）；`grep "\b133\b" run.sh` ⇒ 零命中（rc=1）。（全局 `409`/`133` 残留命中均为无关既有内容：`4096`、`SPEC-133t`/`SPEC-135t` 等。）
- `grep "413\|135"` 三处就位：`milestones.md:58`「探针 413/413，注入 135/34 红」；`issues.yaml` ISS-322 关闭注记「探针 413/413、反例注入 135/34 红」；`run.sh:4`「413 cases, live count」✓。
- `make check`(L1) ⇒ rc=0（`repository checks (L1): PASS`；日志 `/tmp/opencode/QEMU-072t-review/l1-round2.log`）。
- `git status --porcelain -uall` ⇒ 唯一 ` M` = 本任务书（即第 1 轮审阅记录本身，reviewer 无提交权、归 architect 入库）；无 untracked 残留、`.work/log` 无 `.EXIT` ✓。未跑长门控（用户约束）。

**判决：Accepted** —— 唯一打回项（文档数字 409/133 → 413/135）三处均已更正且经我亲验；改动集恰为 2 文件、无越界；第 1 轮其余通过项无回归面（本轮仅文档 diff）。

