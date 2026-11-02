# QEMU-070t: `ftfma`/`fofma` 执行语义（softfloat 单次舍入 + 块/标量）

**模块**：qemu
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立，`scope: excluded`）、`INFRA-099t`（门控互斥；门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 语义真源

- `spec/SimRISC-07 §4.x`（`SPEC-157t` 新增）：`ftfma rfHA, rfHB, rfHC, rfHD` = `rfHA ← rfHB × rfHC + rfHD`（单精度）；`fofma` 同（双精度）。
- **四操作数**：`rfHA ← rfHB × rfHC + rfHD`；目的与源**允许重叠** ⇒ **先读全部源再写**；**单次舍入**。
- 异常：sNaN ⇒ NV + qNaN；OF/UF/NX 按 IEEE，一次运算只置一次；舍入模式由 `rf0[33:32]` 控制。

### 现场事实（2026-10-21 核，执行前须复核）

- QEMU FP 实现分两层：`insn_trans/trans_fp.c.inc.patch`（位级/简单运算，纯 TCG）与 `helper.c.patch`（softfloat）。FMA **必须走 softfloat**（单次舍入无法用 TCG 位运算拼）。
- softfloat 已提供融合乘加入口（名称以现场源码为准，典型为 `float32_muladd` / `float64_muladd`，含 `flags` 与舍入模式参数）；**须现场确认本仓库 qemu 版本的函数名/签名**。
- 现有 helper 调用范式（`gen_convert_f2i` 等）已处理：从 `rf0` 取舍入模式、把 `flags` 合回 `rf0[4:0]` ⇒ **复用该范式**，不自造。
- `insn.decode`：新增 `ftfma`（`0x5E`）/ `fofma`（`0x5F`）两条**整 op 字节** pattern（`rrrr` 四寄存器，**无 opx**）。
- `check_qemu_trans --strict` 现有计数 = 262-1（`SPEC-157t` 新记录缺 trans；issue 已登记）⇒ 本册收口后应为 **262/262**。

## 目标

1. `ftfma`/`fofma` 按 IEEE 单次舍入执行（含 NaN/Inf/溢出/下溢与标志）；
2. `decode` + `trans_*` 齐备 ⇒ `check_qemu_trans --strict` **262/262**；
3. 语义探针覆盖：一般值、单次舍入反例、sNaN/qNaN、±0、溢出/下溢、`rf0` 四种舍入模式。

## 接口规范

- **输入**：`components/qemu/patches/target/dadao/insn.decode.patch`、`insn_trans/trans_fp.c.inc.patch`、`helper.c.patch`、`tools/qemu/*`（探针）。
- **输出**：两条 `insn.decode` pattern；`trans_ftfma_rrrr_rf`/`trans_fofma_rrrr_rf`（或统一 `gen_fp_muladd`，读 3 源写 1 目的）；helper 侧调用 softfloat 的 mulAdd；探针 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（本册不翻 scope）；不改其它 FP 族；不改门控判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 单次舍入的**可判定证据**（本册最关键）

- 必须给一个**经典反例**：选 `a,b,c` 使 `round(a×b) + c ≠ round(a×b + c)`（例如 `a=b=1+2^-23` 附近、`c = -1`），探针断言结果等于 **精确积再舍入** 的那一个；
- 该反例同时用作"实现是否退化为 mul+add"的判据。

### B. 读序与写回

- 三个源（`rfHB`、`rfHC`、`rfHD`）**先全部读出**再写 `rfHA`；目的与源同寄存器时行为确定（规范要求）。
- 目的 `rf0` ⇒ ILLI（`dst_rf0`），沿用 `fp_check_dst_rf0`。

### C. 标志与舍入模式

- 从 `rf0[33:32]` 取舍入模式传给 softfloat；把返回 `flags` 合并进 `rf0[4:0]`（**只置位、清零语义照既有 helper**）。
- 一次运算只更新一次标志（不得拆成两次 mul/add 各置一次）。

### D. 探针覆盖

- 一般值：正/负/混合符号，≥16 组（含 `a×b` 与 `c` 量级相差大的情形）；
- 特殊值：`±0`、`±Inf`、qNaN、sNaN（sNaN ⇒ NV + qNaN 且**不**传播 payload 错误）；
- 边界：最大有限值 × 2 → OF；最小正规 × 2^-1 → UF（含次正规）；
- 舍入模式：四种（RN/RZ/RP/RM）**各 ≥1 例**，只测会被模式影响的值；
- 单次舍入反例 ≥1 例（见 A）。

## 验收标准

1. `check_qemu_trans --strict` ⇒ **262/262**（现场输出）。
2. 探针全绿（计数现场派生）；单次舍入反例**必须**有独立期望值（由 Python 精确有理数/`fractions` + 一次舍入算出，**不得**用 QEMU 自身结果反推）。
3. ILLI：目的 `rf0` ⇒ 真跑观察到非法指令异常。
4. `make build-qemu` rc=0；`make check`（L1）rc=0；`make check-modules`（L2）rc=0。
5. **可达 FAIL ≥ 2**：① 把实现改成 `fomul`+`foadd` ⇒ 单次舍入反例红；② 舍入模式不接 `rf0`（固定 RN）⇒ 四种模式用例红。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行；关闭 `SPEC-157t` 登记的缺 trans issue。

## 做（阶段）

1. 现场复核（softfloat mulAdd 函数名/签名、helper 范式、`insn.decode` FP 行、探针骨架）。
2. `insn.decode` 两条 + `trans_*` + helper 调用 → `make build-qemu`。
3. 探针（先一般值，再单次舍入反例，再标志/模式）。
4. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 实现退化为 `fomul`+`foadd`（临时改 trans）⇒ 单次舍入反例红；还原 ⇒ 绿。
- 舍入模式恒传 RN ⇒ 四种模式用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改 `scope`（`SPEC-158t`）；不接 LLVM（`LLVM-123t`）；不做集成基准（`TESTCASES-058t`）。
- 不做 `fmsub`/`fnmadd`（负号靠 `fosgnn`）。
- 不加新的 softfloat 函数（只用既有 mulAdd；若缺失则**停下报告**，不自行改上游）。

## 完成区

**测试结果**：探针 **122/122**（`Main: 122/122 passed, 0 failed`，新增 122 例、删除 0 例；10 类：GEN=32/FUS=4/NAN=18/ZERO=14/INF=12/BND=8/MODE=24/ALI=6/RF0=2/IL=2）；oracle PASS（17 samples + 16 anchors；fused ft=`0xA8800000`、fo=`0xB970000000000000`，均与 two-step（`+0`）不同；FUS3/FUS4 已改为**真判别**用例：`ft (1+2^-23)^2−(1+2^-22)`、`fo (1+2^-52)^2−(1+2^-51)`，two-step 均得 `+0`）；selftest 4/4；`check_qemu_trans --strict` **266/266** rc=0；注入①two-step **115/122**（**7 红**：GEN5、FUS1–4、BND ft uf、BND fo uf）②去 sNaN 的 NV 106/122（**16 红**：NAN sNaN×6 + twoNaN×2 + zero_x_inf_qnan×2 + INF opp/infxinf/negprod×2），`cp`+md5 还原后均回绿 122/122；L1 rc=0（40s）/L2 rc=0（296s，含 `check_interface`）。
**修改文件**：`components/qemu/patches/target/dadao/{insn.decode,helper.c,helper.h}.patch`、`.../insn_trans/trans_fp.c.inc.patch`（2 条 pattern + `helper_fp_muladd` + `gen_fp_muladd`/2 trans）；`tools/qemu/min_rom_probe_070t.py`；`.work/evidence/QEMU-070t/run.sh`；本任务书、`.tao/knowledge/issues.yaml`（`ISS-330` closed）、`.tao/knowledge/milestones.md`（一行）。
**验收结果**：`check_qemu_trans: 266/266 insns have trans impl (M1 156/156)`；`check_interface` 83/83 PASS；coverage 现场派生 `GEN=32, FUS=4, NAN=18, ZERO=14, INF=12, BND=8, MODE=24, ALI=6, RF0=2, IL=2`；`run.sh` rc=0（`.work/evidence/QEMU-070t/run.rc`=0）；注入日志 `QEMU-070t-inject-{a,b}-probe.log`（rc=1）+ `...-restore-probe.log`（rc=0）。
**新发现/坑**：① 改 patch 后须同步 hunk 行数与 new-file `index` blob，否则 L1 `check-index-blobs` 红（用 `check_index_blobs.py --fix`）；`insn.decode` 与 `generate_decodetree.py` 输出逐字节一致。② softfloat 精确次正规结果**不**置 UF/NX（仅 tiny 且 inexact）；oracle 首版误置 ⇒ BND 4 例红，已按 IEEE 修正。③ `set_default_nan_mode(1)` 同时满足 contract §20 canonical qNaN 与 `0×Inf+qNaN` 的 NV（softfloat 默认 infzero 规则不抑制 invalid）。④ 本仓库 softfloat `float{32,64}_muladd(a,b,c,flags=0,st)` 即融合 `a*b+c`（勿用 `_scalbn` 变体）。⑤ 「单次舍入判别用例」的 `a×b` 本身必须**不可精确表示**：若 `a=b=1` 则乘积精确，无论 `c` 取何值 two-step 都与 fused 相同（FUS3/FUS4 原写法即此坑，已改为 `(1+2^-p)^2+c` 并用 oracle anchor 强制两者不同）。
**遗留问题**：无（`scope → fp` 归 `SPEC-158t`、LLVM 后端归 `LLVM-123t`、集成归 `TESTCASES-058t`，均非本册）。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-23）

代码级逐行审查（`helper_fp_muladd`、`gen_fp_muladd`+2 trans、decode 2 行、oracle/runner），findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 改 patch 后 hunk 行数/new-file `index` 陈旧（`git apply` 静默容忍） | ✅已修 | 重算 hunk 计数、`check_index_blobs.py --fix` 更新 4 个 blob | L1 `check-index-blobs` 回绿；`git apply` 60 patch 全成功 |
| oracle 对**精确**次正规误置 UF\|NX（IEEE 要求 tiny 且 inexact） | ✅已修 | `round_exact` 子正规分支 `flags=UF\|NX if inexact else 0` | BND 4 例回绿；探针 122/122 |
| oracle 样本计数 `len(problems)+11` 为写死假计数 | ✅已修 | 抽 `sample_checks()`/`structural_anchors()`，现场 `len()` | `--oracle` 打印 samples=17 |
| fo 反例常量 `0x3FEFFFFFFFFFFFFF` 实为 `1−2^-53`（非 `1−2^-52`） | ✅已修 | 改 `0x3FEFFFFFFFFFFFFE`（anchor+FUS2） | fo fused anchor `0xB970000000000000` PASS |
| FUS3/FUS4 的 `c` 舍入后恰为 `−1.0` ⇒ 与 two-step 无差（reviewer 指出） | ✅已修 | 改为 `(1+2^-p)^2+c` 真判别式（ft `c=0xBF800002`、fo `c=0xBFF0000000000002`），并加 2 条 oracle anchor | FUS3/FUS4 绿；注入①下二者均红 |
| 证据脚本 `grep "$red_grep"` 对以 `-` 开头的模式报 invalid option | ✅已修 | `grep -c -F -e "$red_grep"` | `--inject` 两例 targeted 检查 PASS |
| 证据脚本查 `=> 0xA8800000` 与探针 `->` 不符 | ✅已修 | 改 `grep -- '-> 0xA8800000'` | 该检查 PASS（actual=1） |
| 别名/读序：三源是否先读后写 | ✅自证 | 三源 load 全部发在 `store_rf(ha)` 前 | ALI 6 例（dst=a/b/c）全绿 |
| 目的 rf0 合法性 | ✅自证 | `fp_check_dst_rf0(ctx, a->ha)` | IL1/IL2 实跑 exit=0x88 |
| 单次舍入是否真融合 | ✅自证 | helper 仅调 `float{32,64}_muladd(...,0,st)`；探针独立 oracle 判别 | FUS1–4 绿；注入① 7 红（含 FUS1–4） |
| 标志是否只置一次 | ✅自证 | 单次 softfloat 调用 + `fp_status_commit` 一次 `\|=` | 所有 120 条 flag 断言绿 |

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**重跑（本人命令 + 真实 rc）**：`check_qemu_trans --strict` ⇒ `266/266 insns have trans impl`（rc=0）；`check_interface` ⇒ `总计: 83 项 | PASS: 83`（rc=0）；`make build-qemu` rc=0（2s）；探针 ⇒ `Main: 122/122 passed, 0 failed`（rc=0）、`--oracle` `Oracle: PASS（17 samples+14 anchors）`（rc=0）、`--selftest` 4/4（rc=0）；`make check`(L1) rc=0（41s）；`make check-modules`(L2) rc=0（297s，含 check_interface）；`.work/evidence/QEMU-070t/run.sh` 整跑 ⇒ `OVERALL: PASS`（rc=0，377s；重跑覆盖 gitignored 的 `.work/log/qemu/QEMU-070t-*.log` 与 `run.rc`，未触碰受跟踪文件）。
**单次舍入（硬要求）**：patch 侧确认 `gen_fp_muladd` 仅一次 `gen_helper_fp_muladd`，helper 内 `float{32,64}_muladd(...,0,st)`（flags=0）、无 mul+add。**自建判别用例**（期望取 glibc `fmaf`/`fma`+fenv，独立于 engineer oracle）：ft `(1+2^-23)²−(1+2^-22)` = `3F800001,3F800001,BF800002` ⇒ QEMU `0x28800000`、flags 0x00（two-step 实测 `+0`、0x10）；fo `(1+2^-52)²−(1+2^-51)` ⇒ `0x3970000000000000`（two-step `+0`）。两例 PASS。
**重叠（先读后写）**：自建 `2×3+0.5=6.5`，dst=a/b/c 各 1 例 + fo dst=c ⇒ QEMU 均 `0x40D00000`/`0x401A000000000000`、flags 0；先写后读则应得 `0x41A00000`/`0x41580000`/`0x41480000`（互异且 ≠ 正确值，判别有效）。
**标志（自建 7 例核 `rf0[4:0]`）**：sNaN⇒`0x7FC00000`+NV 0x01；qNaN⇒qNaN、**0x00**；`0×Inf+1.0`⇒0x01；`Inf+(−Inf)`⇒0x01；`max×2+0`⇒`0x7F800000`+OF\|NX 0x14；tiny∧inexact⇒`0x00400000`+UF\|NX 0x18；`1.5×1.5+0.1`⇒NX 0x10 —— 全 PASS（reviewer 例合计 13/13）。
**探针独立性**：oracle 为纯 `fractions.Fraction` 精确算术（`fma_bits`），期望不经 QEMU/softfloat；NAN 期望来自 spec 规则常量（`qnan_bits,FLAG_NV`）、ZERO 来自 IEEE §6.3 零符号分支、MODE 来自四模式 `round_quantum`；三类均用 glibc fma/fenv 独立复核一致（本机 RNE/RTZ/RDN/RUP=0/3072/1024/2048）。
**注入（本人，`cp`+md5 还原）**：①two-step ⇒ 我的 2 判别例红（`got=0x0`、flags 0x10），探针 `117/122`（5 红：GEN5/FUS1/FUS2/BND ft uf/BND fo uf），还原 md5 `23b785b9…` 相符、回绿 122/122；②`st.float_exception_flags &= ~float_flag_invalid` ⇒ 我的 sNaN/0×Inf/Inf+(−Inf) 三例 flags 红，探针 `106/122`（16 红）、还原回绿。
**约束核验**：`git diff faf29d9b..HEAD` 仅 4 个 qemu patch + probe + 任务书 + issues/milestones；`spec/`、`contracts/`、LLVM 改动 **0 文件**；`check-source-state` qemu `clean=True, count=1`（源=基线+1、与补丁一致）；ILLI（IL1/IL2 实跑 exit 0x88）与探针同绿；`ISS-330` `status: closed` + `resolved_by: QEMU-070t`，关闭判据与我重跑一致 ⇒ 合规。
**非阻断观察**：① 完成区「注入①…5 红，FUS1–4」与真实不符：真实红集为 GEN5/FUS1/FUS2/BND ft uf/BND fo uf（engineer 自身日志 `.work/log/qemu/QEMU-070t-inject-a-probe.log` 亦如此）；FUS3/FUS4 的 `c` 字面量 `-1-2^-24`/`-1-2^-53` 在 ft/fo 中舍入成 `-1.0`，用例退化为 `1×1−1`、two-step 下仍绿 ⇒ **不判别单次舍入**（建议改 `0xBF800002`/`0xBFF0000000000002` 并更正完成区措辞）。
② spec/contract「下溢 ⇒ 次正规数或 ±0 + UF」按 IEEE 作 tiny∧inexact 解读（精确次正规 ⇒ 0 flags），与全 ISA softfloat 行为一致，engineer 已披露。
**判决**：**Accepted**（阻断项——非单次舍入/重叠错/标志错/oracle 循环/门控红/注入不红——均未命中；观察① 由 architect 酌定是否让 engineer 更正完成区措辞与 FUS3/FUS4 常量）。
