# LLVM-125t: `ftrnd`/`fornd` 后端（7 个取整 intrinsic → 6 档 one-hot）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-161t`（记录已立）、`QEMU-072t`（语义已实现）；`INFRA-099t`（门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `SimRISC-07 §4.x`：`ftrnd/fornd rfHB, rfHC, immu6`；`immu6` one-hot：
  `0x01` 取偶、`0x02` 远离 0、`0x04` 向 0、`0x08` 向 +∞、`0x10` 向 −∞、`0x20` 动态（读 `rf0`，置 NX）。
- 偏差（`SPEC-161t` 已登记）：`nearbyint` 落 `0x20`，NX 可能被置位（值正确）。

### 现场事实（2026-10-21 核，执行前须复核）

- 我们后端当前把 `FCEIL/FFLOOR/FTRUNC/FROUND/FROUNDEVEN/FRINT/FNEARBYINT` **全部标为 `Expand`**（`DADAOISelLowering.cpp`）⇒ 现在是 5–10 条软件序列。
- 7 个 ISD 节点 ↔ immu6 的映射：
  - `FROUNDEVEN` → `0x01`；`FROUND` → `0x02`；`FTRUNC` → `0x04`；
  - `FCEIL` → `0x08`；`FFLOOR` → `0x10`；
  - `FRINT` → `0x20`；`FNEARBYINT` → `0x20`（**偏差**，见 §B）。
- `orri` FP 指令的 `.td` 先例：`foroot_orri_rf`（`(outs RF:$hb), (ins RF:$hc, immu6)`）⇒ 直接照抄形态。

## 目标

1. `.td` 两条（`ftrnd_orri_rf`/`fornd_orri_rf`），`op=0x44`、`ha=0x03/0x0B`；
2. 7 个 intrinsic **各 1 条**指令（无比较序列、无 libcall）；
3. `FNEARBYINT` 落 `0x20` 并在代码注释/完成区写明偏差；
4. 不回归既有 `fo2io` 转换与 `fcmp` 路径。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`、`tests/llvm/lit/**`。
- **输出**：2 条 `.td`；7 条选择路径（pattern 或伪指令）；lit（正/反例）；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-162t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 选择方式

- 首选：`Pat` 直接匹配 `fceil`/`ffloor`/`ftrunc`/`fround`/`froundeven`/`frint`/`fnearbyint` → `(FORND $src, <onehot>)`；
- 若某节点带 `flags`（`no-nans` 等）导致不匹配，可用自定义 lowering 兜底（不得落 libcall）。

### B. `FNEARBYINT` 的偏差（**必须注释 + 完成区写明**）

- 落 `0x20`（DYN）⇒ 会置 NX；
- 依据：SimRISC 浮点无异常/陷阱，NX 仅为 `rf0[4:0]` 状态位；LLVM 非严格模式两者均 `IntrNoMem + IntrSpeculatable`（标志不可观察）；值语义完全一致；
- lit 只断言**指令与值**，**不得**断言 NX（避免把偏差固化成契约）。

### C. 边界（由硬件保证，后端不额外处理）

- `±0` 符号、`|x| ≥ 2^p` 原样、NaN/Inf 原样、sNaN 置 NV —— 均在 `QEMU-072t` 验证；后端只负责选择。

## 验收标准

1. lit：7 个 intrinsic **各 1 条** `fornd`（`FileCheck` 断言指令计数 + imm 值），粘真实输出。
2. C 层：`floor/ceil/trunc/round/nearbyint`（`-O2`）各 1 条；C23 `roundeven` 若可用则 1 条。
3. `llvm-mc` 编码 == `44 03/0B` 前缀（现场派生）+ round-trip。
4. 反例：`fornd rf0, rf1, 0x01` ⇒ 汇编失败/ILLI（`dst_rf0`）；`immu6=0x03`（非 one-hot）⇒ 汇编拒绝/ILLI。
5. `check-instrinfo` 0 errors；`check-lit`/`check-lit-full` 绿。
6. 改 `.td` 后 `make install-host` + `make build-builtins` + `make build-musl-shared`。
7. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
8. **可达 FAIL ≥ 2**：① 把 `FFLOOR` 映射成 `0x10` 以外的值（临时）⇒ lit 红；② 把 `FROUND` 与 `FROUNDEVEN` 映射对调 ⇒ `.5` 用例红。
9. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`foroot` 的 `.td` 形态、ISD 节点名、flags 影响）。
2. `.td` 2 条 + 7 条 pattern + 编码 round-trip lit。
3. 7 个 intrinsic 的 lit + C 层 `-O2` 抽查。
4. `install-host` + builtins/musl + L1/L2。
5. 反例注入 + 完成区。

## 可达 FAIL（**≥2**）

- `FFLOOR` 误映 `0x10` 以外 ⇒ lit 红；还原 ⇒ 绿。
- `FROUND`/`FROUNDEVEN` 对调 ⇒ `1.5/2.5` 用例红；还原 ⇒ 绿。

## 已知边界（**披露**）

- 不做 `nearbyint` 的 NX 精确性（偏差已登记）；不做 constrained FP（`llvm.experimental.constrained.*` 仍不支持）。
- 不做 `*mag`；不改转换族；不改 `scope`（`SPEC-162t`）。

## 完成区

**测试结果**：后端 `llc -O2` 七个 f64 intrinsic 各 **1** 条 `fornd rf8, rf16, {16,8,4,2,1,32,32}`（floor/ceil/trunc/round/roundeven/rint/nearbyint），七个 f32 各 1 条 `ftrnd`（同 imm）；带 `afn` 标志仍 1 条/节点、无 libcall、无比较序列。C 层 `-O2` 的 `__builtin_{floor,ceil,trunc,round,nearbyint,roundeven}` 各 1 条 `fornd`（sysroot 尚无 `<math.h>`，故用 builtin 形态）。MC：12 条编码由 `opcodes.yaml` 现场派生（`44 0c …`/`44 2c …`）并与 `llvm-objdump` 逐条一致 + round-trip；`fornd rf0, rf1, 1`、`immu6 ∈ {0,3,5,63,0x40}` 全部 rc=1（`dst_rf0`/`encode_onehot`）。lit（MC+CodeGen+E2E）**132/132**；`check-lit-full` **12/12**；`check_lit_gen` **64/64**；`check-instrinfo` **0 errors**；`check-scope` `excluded` **29** / `fp` **58** 不变；`check_qemu_trans --strict` **260/260**；`check-isa-coverage` accept **258**/reject **2**；`check-patch-tree` **192**（series **90**）。`install-host`/`build-builtins`/`build-musl-shared` 均 PASS（`INSTALL_HOST_EXIT=0`/`BUILTINS_EXIT=0`/`MUSL_EXIT=0`）。
**修改文件**：`DADAOInstrInfoFP.td`（+2 def，形态照抄 `foroot`：`(outs GPRF:$rb),(ins GPRF:$rc, immu6)`）、`DADAOCodeGen.td`（f64/f32 各 7 条 `Pat`）、`DADAOISelLowering.cpp`（7 节点 `Expand`→`Legal`）、`AsmParser/DADAOAsmParser.cpp`（并入 `dst_rf0` + 新 `encode_onehot` 硬错）及其 4 份补丁重导；lit：新增 `p1-fp-rounding-f32.ll`、`fp-round-encoding.s`，`p1-fp-round-libcall.ll`→`p1-fp-rounding.ll`（重写为指令+imm 断言），`p1-fp-libcall-f32.ll`（删取整段）、`fp-legality.s`（计数注释 33→35）；生成物 `MC/DADAO-gen/gen-{orri,excluded}.s`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`、`tools/llvm/gen_isa_coverage.py`（reject 名单改现场派生）；`.tao/knowledge/milestones.md`、`components/llvm-project/changelog.md`。**未改** `spec/`、`contracts/`（`git diff --name-only HEAD -- spec contracts` 为空，证据落盘）。
**验收结果**：`make check`(L1) rc=0、`make check-modules`(L2) rc=0（`module checks (L2): PASS`、`picolibc-tests: PASS (fail=0, blocked=0)`）；证据 `.work/evidence/LLVM-125t/run.sh` default **94/94** rc=0、`--gates` **96/96** rc=0；可达 FAIL 两组各 **7/7**（`--inject ffloor-08`：`FFLOOR→0x08` ⇒ `p1-fp-rounding.ll` 红；`--inject swap-round`：`FROUND`/`FROUNDEVEN` 对调 ⇒ `.5` 用例红；均 `cp`+md5 还原→重建→绿）。
**新发现/坑**：① `validate_instrinfo.py` 默认只重建 `DADAOInstrInfo.td.patch` 的文本，`DADAOInstrInfoFP.td.patch` 不在其扫描面——把 `ftrnd`/`fornd` 加进 `MC_ONLY_EXCLUDED_IDS` 会反而报「allow-list 未在 `.td` 定义」；FP 项实际由 `gen_isa_coverage`（读 FP 补丁）+ `generate_lit_vectors` 覆盖（未改该门控，建议后续统一 TD 补丁集合）。② `generate_lit_vectors.py` 的 excluded 反例判据已按「`.td` def 是否存在」机械判 ⇒ 加 def 后 ftrnd/fornd 自动从 `gen-excluded.s` 转 `gen-orri.s` 正例，生成器零改。③ 矩阵含补丁行号 ⇒ 在 `DADAOCodeGen.td`/`ISelLowering.cpp` 补丁中增行会使 `matrix.{md,tsv}` 大范围位移（86 行，预期）；其 MD 的 reject 名单原为硬编码（已改现场派生，顺带暴露 `clmul.o` 的陈旧文案）。④ 注入必须用 `LLVM_TOOLS_DIR=.work/build/llvm/bin` 让 lit 用重建后的 `llc`（安装根不刷新）；前台注入含 2 次 llc 重链（≈4 min）会被工具 120 s 超时杀掉，须 `setsid nohup`。
**遗留问题**：① `ftrnd`/`fornd` 仍 `scope: excluded` ⇒ 运行期 ILLI，**值域/标志级**验证（6 档×值矩阵、NX/NV、`.5` 位模式）归 `TESTCASES-060t`（`SPEC-162t` 翻转后）。② 因 ①，本任务 lit 的 `.5` 断言是 **模式位 imm** 而非运行值（已用注入② 证明该断言可红）；③ C 层探针用 `__builtin_*`（target sysroot 尚无 `<math.h>`）。④ f32 的 7 条 selection 一并落地（任务验收只点名 `fornd`），f32 lit 已带断言。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

审查面：4 份后端补丁（`.td`/CodeGen/ISelLowering/AsmParser）、2 份新 lit + 2 份改写 lit、`gen_isa_coverage.py` 改动、证据脚本。逐项：

- 映射正确性：7 条 pattern 的 imm 与 `contract-fp.md §roundint` 逐档核对（`FROUNDEVEN=1`、`FROUND=2`、`FTRUNC=4`、`FCEIL=8`、`FFLOOR=16`、`FRINT=32`、`FNEARBYINT=32`），且 `llc` 实测与之一致。
- `Legal` 的副作用：置 `Legal` 后若 pattern 失配会 `Cannot select` 而非静默 libcall；已用 `afn`（fast-math 标志）IR 实测仍 1 条/节点。
- AsmParser：`Flat[]` 下标与既有 `dst_rf0`/`encode_fp_root_n` 一致（0=助记符），符号/重定位立即数（`getImmExpr()!=nullptr`）按不可证明 one-hot 拒绝；对 0x40（超 immu6 范围）报 one-hot 口径错误（仍 rc=1，spec 判据同为 ILLI）。
- lit：每函数 `CHECK-COUNT-1` 断言计数 + `CHECK-NOT: call` 断言无 libcall，`.5` 语义以函数名/注释标注并绑定 imm；`p1-fp-rounding-f32.ll` 与 f64 同构。
- 生成物/门控一致性：矩阵在 `install-host` 之后重生成（否则 `llvm-mc` 旧版会得 accept 256/reject 4 的假红）。
- 证据：`--inject` 两例均在「文件真的改了（md5 变 + marker 在盘）」前提下红，还原用 `cp`+md5 对账（非 `git checkout`），重建后回绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `validate_instrinfo` 的 allow-list 加 ftrnd/fornd 反而 2 errors | ✅已修 | 撤销 `tools/llvm/validate_instrinfo.py` 改动（该门控不扫 FP 补丁） | `check-instrinfo` `=== Result: 0 errors ===`；差异披露于「新发现①」 |
| 矩阵在 install-host 前生成 ⇒ accept 256/reject 4 假红 | ✅已修 | `install-host` 后用现场 `llvm-mc` 重生成 `matrix.{md,tsv}` | `gen_isa_coverage --check: PASS`（accept 258/reject 2） |
| `gen-lit-idempotent` 初版用 `git diff HEAD`（本任务未提交 ⇒ 必红） | ✅已修 | 改为「两次生成 md5 全等」 | `run.sh` default 94/94 |
| 证据脚本在 while 循环里用 `local`（非函数作用域报错） | ✅已修 | 去掉 `local` | 脚本 rc=0 |

### 第 1 轮 reviewer 验收（2026-10-22）

判决 **Accepted**。独立重跑（不采信完成区转述）：`make check`(L1) rc=0；`check-instrinfo` `0 errors` rc=0；`check-scope` PASS（`fp` 58/`excluded` 29/total 260）；`check_qemu_trans.py --strict` `260/260` rc=0；`check-isa-coverage` `accept 258/reject 2` PASS；`check_lit_gen.py` `64/64`。自写最小 `.ll` 跑 `llc -O2 -march=dadao`：`floor`→`fornd rf8,rf16,16`(0x10)、`roundeven`→`fornd rf8,rf16,1`(0x01)，各 1 条无 `call`——映射独立核实为 one-hot（1/2/4/8/16/32/32）。反例：`fornd/ftrnd rf0,rf1,1`→rc=1 `dst_rf0`；`immu6∈{0,3}`→rc=1 `encode_onehot`。编码 `44 2c…`(fornd,ha=0x0B)/`44 0c…`(ftrnd,ha=0x03) 手工核算与 lit 逐条一致（独立手算非读回）。

**独立注入**（`cp`+md5，禁 checkout）：`FFLOOR` imm 16→8 ⇒ md5 `3f0724…`→`99f3a9…`、ninja 重建 llc rc=0、lit `FAIL p1-fp-rounding.ll` **LIT_EXIT=1（红）**；`cp` 还原 md5 相等 `3f0724…`、重建 rc=0、lit **LIT_EXIT=0（绿）**；源树 `git status` 干净、临时已清。断言可达 FAIL 证实。

**`gen_isa_coverage.py` 改动 = 非弱化**：diff 仅 MD 渲染文本（reject 名单硬编码→`l1_reject_mnemonics` 现场派生）；`l1_accept/reject` 计数逻辑（`len(...)`）未动；派生名单只进渲染、不进任何 pass/fail 断言。数值 256/4→258/2 的根因是 `fornd`/`ftrnd` 随新增 `.td` def 由 reject 翻 accept（预期效果）；顺带纠正旧文案错列 `clmul.o`（两版均 accept）。非弱化、属准确性提升。

**约束**：spec/contracts 零 diff（`git diff --name-only 6bb9eb33 HEAD -- spec contracts` 空）；未 commit/push（HEAD=2b3f8803 未变）；证据 default 94/94、`--gates` 96/96、注入各 7/7 与日志一致；偏差 FNEARBYINT 注释/完成区明示、lit 未断言 NX。逐条达标。

