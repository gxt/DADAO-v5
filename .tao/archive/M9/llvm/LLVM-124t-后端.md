# LLVM-124t: `ftmin`/`fomin`/`ftmax`/`fomax` 后端（`.td` + `FMINNUM_IEEE`/`FMINIMUMNUM` Legal）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-159t`（记录已立）、`QEMU-071t`（语义已实现）；`INFRA-099t`（门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `spec/SimRISC-07 §4.x` + `contract-fp.md §minmax`：4 条 `orrr`，`op=0x44`，`ha` 分别为 `0x26/0x27/0x2E/0x2F`；语义 = 754-2019 `minimumNumber`/`maximumNumber`。
- 硬件保证：单 NaN（含 sNaN）⇒ 数字（sNaN 置 NV）；双 NaN ⇒ canonical qNaN；`−0 < +0`；无舍入。

### 现场事实（2026-10-21 核，执行前须复核）

- LLVM 有 **4 个** 相关 ISD 节点：`FMINNUM`（遗留）、`FMINNUM_IEEE`（定义良好的 number 语义）、`FMINIMUM`（NaN 传播 = 754-2019 `minimum`）、`FMINIMUMNUM`（2019 `minimumNumber`）。
- 现有后端把这些**全部**标为 `Expand`（`DADAOISelLowering.cpp` 的 `setOperationAction` 列表含 `FMINNUM/FMAXNUM/FMINIMUM/FMAXIMUM`）⇒ 现在 C `fmin/fmax` 是 4–6 条比较序列。
- LLVM 的降级链（源码已核）：`expandFMINNUM_FMAXNUM`（`FMINNUM`→`FMINNUM_IEEE` + `FCANONICALIZE`）、`expandFMINIMUMNUM_FMAXIMUMNUM`（→`FMINNUM_IEEE` + canonicalize）、`expandFMINIMUM_FMAXIMUM`（`FMINNUM_IEEE` + `SETUO` 选 NaN；若底层不保证 ordered zero 再加 `SETOEQ` ±0 修正）。
- **结论**：目标只需让 **`FMINNUM_IEEE`/`FMAXNUM_IEEE` 与 `FMINIMUMNUM`/`FMAXIMUMNUM` Legal**（映射到本组指令），`FMINIMUM/FMAXIMUM` 继续 `Expand` 即可覆盖 C23。

## 目标

1. `.td` 定义 4 条（`orrr`，`(outs RF:$hb), (ins RF:$hc, RF:$hd)`）；
2. `@llvm.minnum`、`@llvm.minimumnum`、C `fmin/fmax` ⇒ **1 条** `fomin`/`fomax`（无比较序列）；
3. `@llvm.minimum`（C23 `fminimum`）⇒ 展开为 `fomin` + NaN 选择（**无 libcall**、不落 `fmin` 库函数）；
4. 不回归既有 `fcmp`/`cs.*-rf` 路径。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`）、`tests/llvm/lit/**`。
- **输出**：4 条 `.td` def + 2 组 pattern（`fminnum_ieee`/`fmaxnum_ieee`、`fminimumnum`/`fmaximumnum`）；lit（正/反例）；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-160t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 节点映射（**关键，别只映射 `FMINNUM`**）

- `FMINNUM_IEEE`/`FMAXNUM_IEEE` → `fomin`/`fomax`（`ft` 同理，按 `VT` 选）；
- `FMINIMUMNUM`/`FMAXIMUMNUM` → 同一条（语义与硬件完全一致）；
- `FMINNUM`/`FMAXNUM`（遗留）**保持 Expand**，由 LLVM 转成 `FMINNUM_IEEE`（其 `FCANONICALIZE` 在无 x87 扩展精度的目标上应为恒等；须现场确认 `FCANONICALIZE` 的 lower 结果不引入额外指令）；
- `FMINIMUM`/`FMAXIMUM` **保持 Expand**。

### B. 语义断言（用 lit）

- `@llvm.minnum.f64(x,y)` ⇒ **恰好 1 条 `fomin`**；
- `@llvm.minimumnum.f64` ⇒ 同上；
- `@llvm.minimum.f64` ⇒ `fomin` + `SETUO` 选择（**数字符**：无 `call fmin`、无 `call fminf`）；
- C `fmin(a,b)`（`-O2`）⇒ 1 条；
- `-0`/`+0` 语义：`llc` 不得额外插入 ±0 修正（硬件保证 ordered zero ⇒ `MinMaxMustRespectOrderedZero` 成立）；
- 反例：`fomin rf0, rf1, rf2` ⇒ 汇编失败/ILLI（`dst_rf0`）。

### C. 已知陷阱

- `FMINNUM` 若被误标 Legal 而不做 canonicalize，会让 **sNaN 不置 NV**、与 `minimumnum` 混淆 ⇒ 必须走 Expand 路径；
- `nsz` 标志：LLVM 会传 `hasNoSignedZeros`；我们的硬件仍按 `−0<+0` 执行，结果**仍是合法**的（`nsz` 允许非确定）✓ 但不得因此删掉硬件语义。

## 验收标准

1. 三条 lit 正例各断言**指令计数**（`minnum`/`minimumnum` = 1；`minimum` ≤ 4 且无 libcall），粘真实输出。
2. `llvm-mc` 编码 == `44 26/27/2E/2F`（现场派生）+ round-trip。
3. 反例 `dst_rf0` 汇编拒绝。
4. `check-instrinfo` 0 errors（`excluded` 有 `.td` 合规）；`check-lit`/`check-lit-full` 绿。
5. 改 `.td` 后 `make install-host` + `make build-builtins` + `make build-musl-shared`（新鲜度门控）。
6. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
7. **可达 FAIL ≥ 2**：① 把 `FMINNUM_IEEE` 改回 Expand ⇒ 指令计数断言红；② 去掉 `FMINIMUM` 的 NaN 选择（临时）⇒ `minimum` 语义用例红。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（FP `.td` 形态、`FCANONICALIZE` 的 lower、ISD 节点名）。
2. `.td` 4 条 + 两组 pattern + 编码 round-trip。
3. lit：`minnum`/`minimumnum` 各 1 条；`minimum` 展开；`fmin` C 层 1 条。
4. `install-host` + builtins/musl + L1/L2。
5. 反例注入 + 完成区。

## 可达 FAIL（**≥2**）

- `FMINNUM_IEEE` 保持 Expand ⇒ lit「1 条 fomin」红；还原 ⇒ 绿。
- 删 `FMINIMUM` 展开里的 NaN select（临时）⇒ `@llvm.minimum` 用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做 `minimum` 的硬件版（无此指令）；不做 `*mag`；不改 `fcmp` 路径。
- 不改 `scope`（`SPEC-160t`）；不做集成（`TESTCASES-059t`）。

## 完成区

**测试结果**：`.work/evidence/LLVM-124t/run.sh` **118/118 PASS**（`--gates` 120/120 含 L1/L2）；`llc`：`minnum`/`maxnum`/`minimumnum`/`maximumnum` f64+f32 各 **1 条**（`fomin`/`fomax`/`ftmin`/`ftmax`，无 libcall、无比较序列）；C `fmin/fmax/fminf/fmaxf`（`-O2`）各 **1 条**；`llvm.minimum/maximum` = **9 条**（`fomin`+`foqcmp`+`cmp.si`+`cs.p`+`cs.z`+NaN 常量 2 条+`ret`），**无 libcall**、**无 SETOEQ ±0 修正**（无 `andn.w`/`set.ow`）。`llvm-mc` 编码 == `44 98/9c/b8/bc 82 4a`（现场由 `opcodes.yaml` 派生 + objdump 往返）；`dst_rf0` 4 条全拒（rc=1）。lit 131/131、`check-lit-full` 12/12。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOInstrInfoFP.td,DADAOCodeGen.td,DADAOISelLowering.cpp,DADAOISelLowering.h,AsmParser/DADAOAsmParser.cpp}.patch`（.td 4 条 + 8 pattern + 节点动作 + `dst_rf0` 名单）；`tests/llvm/lit/CodeGen/DADAO/p1-fp-minmax.ll`（新）、`p1-fp-minmax-libcall.ll`/`p1-fp-libcall-f32.ll`（删，内容已由新册覆盖）、`tests/llvm/ir-lli/manifest.yaml`、`tests/llvm/lit/MC/DADAO/fp-legality.s`、`MC/DADAO-gen/{gen-orrr,gen-excluded}.s`（重生成）、`tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（重生成）、`components/llvm-project/changelog.md`（一条）、`.tao/knowledge/milestones.md`（一行）、`.work/evidence/LLVM-124t/`。
**验收结果**：`make install-host` PASS（2 次）、`build-musl-shared` PASS；`check-instrinfo` 0 errors、`check-scope` PASS（excluded **31**/fp 60/264）、`check_qemu_trans --strict` **264/264**、`check_isa_coverage --check` PASS、`check_lit_gen` 64/64、`check-lit` 131/131；**L1 rc=0、L2 rc=0**（现场 805/805）。可达 FAIL 3 条（各含还原后回绿）：① `--inject a`（`FMINNUM_IEEE`→Expand）⇒ `minimum/maximum` 重新出现 ±0 `SETOEQ` 修正（10→20 行、5 个 `cs.z`）红；② `--inject a2`（`FMINNUM/FMAXNUM`→Expand）⇒ `minnum` 由 2 行变 6 行、「1 条」断言红；③ `--inject b`（删 `expandFMINIMUM_FMAXIMUM` 的 NaN select）⇒ `minimum` 只剩 1 条、`cs.*` 计数与语义断言红。
**新发现/坑**：**任务书 A/B 冲突（须裁定）**：`FMINNUM` 保持 `Expand` ⇒ LLVM 的 `expandFMINNUM_FMAXNUM` 给每个操作数插 `FCANONICALIZE`，而本目标 `FCANONICALIZE` 展开成 `x*1.0`（实测 `llvm.canonicalize.f64` = `set.zw;rd2rf;fomul`，3 条）⇒ `minnum` 为 7 条，与验收「1 条」冲突（任务书假设它是恒等，实测不是）。故 `FMINNUM/FMAXNUM` 改 `Custom`→直落 `FMINNUM_IEEE/FMAXNUM_IEEE`（1 条）：LangRef 明确 minnum 的 sNaN 结果**非确定**（「任一 NaN 或另一操作数」）且允许把 NaN 当 qNaN，而 canonicalize 会先安静 sNaN 反而**丢掉** `contract-fp.md §minmax` 要求的 NV；因此本实现 sNaN 仍置 NV。`minimum` 为 **9 条**而非任务书估的 ≤4（`SETUO` 选择需 3 条 + NaN 常量 2 条）。另：`.tao/knowledge/{MEMORY.md,issues.yaml}` 在工作期间被**他方**并发改写（非本任务改动、未触碰）。
**遗留问题**：① `FMINNUM/FMAXNUM` 的 `Custom`（而非 `Expand`）为对任务书 A 点的**有意偏离**，请 architect/reviewer 裁定（若坚持 Expand，则 `minnum` 只能是 7 条，验收「1 条」须改）；② `minimum` 指令数 9 > 任务书「≤4」，如需更小须把 `FMINIMUM` 也改 Custom（用 `rf0` 的 qNaN 省掉常量 2 条），属设计外；③ 预存在缺陷（非本任务）：`tests/llvm/ir-lli/manifest.yaml` 有 11 个未分类 `*.ll` + 1 条悬空项（`p1-fp-round-libcall.ll`，LLVM-121t/122t/125t 遗留）⇒ `test-m6`(L3) 结构性红；本任务只把自己两册的条目对齐，未代为修全表。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-22 20:30，自主逐行审查）

改动逐文件复核：`.td` 4 条（`op`/`ha`/`GPRF` 形态由证据脚本**从 `opcodes.yaml` 重新派生比对**，非抄实现）；`DADAOCodeGen.td` 8 条 pattern（`fminnum_ieee`/`fmaxnum_ieee`/`fminimumnum`/`fmaximumnum` × f64/f32，复用 `DADAOOrrr` 格式类，未另造 `RF` 类）；`DADAOISelLowering.cpp`（动作表 + `LowerMinMaxNum` + `LowerOperation` 两 case；`Op->getFlags()` 透传 `nsz`）；`.h` 声明；`AsmParser` `dst_rf0` 名单 20 条（与 spec 的 4 条排除项一致）。逻辑边界复核：`nsz`（硬件仍 `−0<+0`，LLVM 允许非确定）、sNaN（硬件置 NV）、双 NaN（canonical qNaN）、`minimum` 的 ±0 分支（`MinMaxMustRespectOrderedZero` 抑制 `SETOEQ` 修正，反向注入 a 证明该断言可红）。防造假：所有数字取自 `.work/evidence/LLVM-124t/out/`（`counts.log`/`lit.log`/`make_check*.log`），未估算。证据脚本自身的首次红色（`mc-roundtrip` 位域取错、`total-instruction-count` 漏 `ret`、`chk_in` 用 BRE 匹配方括号）已当场修正并回绿——即脚本自身也有真实 FAIL 路径。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `FMINNUM/FMAXNUM` 由 `Expand` 改 `Custom`（偏离任务书 A 点） | ⏸延后（需 architect/用户裁定；理由已具证据） | `DADAOISelLowering.cpp` 动作表 + `LowerMinMaxNum` | `counts.log`（1 条）vs 注入 a2（6 行）；LangRef 引文见代码注释 |
| `minimum` 实测 9 条 > 任务书「≤4」 | ❌不修（LLVM 通用展开；缩小须改 `FMINIMUM` 为 Custom 用 `rf0` 的 qNaN，属设计外） | 无 | `minimum_f64.body`（9 条 + `ret`） |
| `Custom` 的 `LowerOperation` 产物**不再过 legalizer**（LLVM 契约：须返回已合法节点）⇒ `FMINNUM_IEEE`/`FMAXNUM_IEEE` 必须保持 Legal | ❌不修（当前满足契约；已在注入 a 的注释与任务书记录） | 无 | 注入 a：`FMINNUM_IEEE→Expand` 后 `minnum` 仍 1 条（`inject_a.run.log`） |
| 删 `p1-fp-minmax-libcall.ll`/`p1-fp-libcall-f32.ll`、新增 `p1-fp-minmax.ll`（旧册只断言已消失的 libcall） | ✅已修 | 见「修改文件」；`ir-lli/manifest.yaml` 同步 | `lit.log` 131/131；`chk_in lit-p1-fp-minmax-pass` |
| 生成物需重生成（`gen-orrr`/`gen-excluded`/`isa-coverage` 矩阵） | ✅已修 | 三个生成器重跑 | `gen-lit-idempotent`、`check_lit_gen` 64/64、`check-isa-coverage PASS` |
| 预存在：`ir-lli/manifest.yaml` 11 个未分类 `*.ll` + 1 条悬空项（他任务遗留） | ⏸延后（非本任务范围，范围外修复须授权） | 未动 | 自审实测 `structural_check` 输出（`inject_*` 前的现场） |

判决：finding 1、6 需裁定/他人处置，其余已修；实现与验收证据一致，状态置 `待验收`（finding 1 已在「遗留问题 ①」标出，请 reviewer 一并裁定）。

### 第 1 轮 reviewer 验收（2026-10-22，独立重跑）

**指令计数（安装根 `llc`/`clang` 现场生成，非采信完成区）**：`minnum/maxnum/minimumnum/maximumnum` f64 → `fomin/fomax/fomin/fomax`、f32 → `ftmin/ftmax/ftmin/ftmax`，各 **1 条**（llc rc=0）；`minimum/maximum` = **9 条+ret**（foqcmp+cmp.si+2×set.zw+cs.p+fomin+set.zw+rd2rf+cs.z），**无 call/jump、无 andn.w/set.ow**（无 SETOEQ ±0 修正）；C `fmin/fmax/fminf/fmaxf`（-O2）各 **1 条**（clang rc=0，无 libcall）。与完成区数字逐条一致。

**两处披露偏差**：① `FMINNUM/FMAXNUM`→`Custom` **成立**——`llvm.canonicalize.f64` 实测 = `set.zw;rd2rf;fomul`（x*1.0，3 条，非恒等；源码 `FCANONICALIZE` 在 Expand 列表），保持 Expand 则 minnum=7 条，与验收「1 条」冲突；LangRef.md:17248「For signaling NaNs, non-deterministically returns NaN or the other operand」⇒ 直落 `FMINNUM_IEEE`（sNaN 仍置 NV）合规。② `minimum` **9 条 > 任务书 ≤4 成立**：9 条为 LLVM 通用 `expandFMINIMUM_FMAXIMUM` 的必要构成（NaN 检测 2 + SETUO 标志路径 3 + minmax 1 + qNaN 常量 2 + select 1），再缩须改 `FMINIMUM`=Custom（用 rf0 qNaN），属设计外。

**门控重跑（reviewer 本机 rc）**：`validate_instrinfo.py` rc=0「=== Result: 0 errors ===」；`check_scope.py` rc=0 PASS（excluded=**31**、fp=60，现场统计）；`check_qemu_trans --strict` rc=0「**264/264**」；`make check-lit` rc=0「**131/131**」；`make check`(L1) rc=0「repository checks (L1): PASS」。按指示未重跑 install-host/重建。

**独立注入（与 engineer 三种均不同：`FMINIMUMNUM/FMAXIMUMNUM`→Expand）**：`cp` 备份 md5=`8d165f94…` → 注入后 `090ddb5d…` → `ninja -j8 llc` rc=0 → **同一脚本**（shim 仅覆盖 ROOT/LLC/OUT 三行环境变量，断言逐字未动，diff 仅 3 行）rc=**1**，16 FAIL（`FAIL llc[minimumnum_f64]-instruction-count expected=2 actual=6` 等）→ `cp` 还原 md5=`8d165f94…` **相等** → 重建 rc=0（build llc md5=`17d4264d…`==安装根）→ 同脚本 rc=**0**（118/118）。全程 cp 备份还原，未用 git checkout/restore/stash。

**证据脚本审读**：无 `| tee`（仅注释提及）；逐命令 `rc=$?` 捕获、trap 落盘 `run.{default,gates,inject-a,a2,b}.EXIT`（5 个均 EXIT=0 实核）；断言有可达 FAIL 路径（本注入即证，非恒真）；注入还原用 cp+md5。弱项（不阻断）：`chk "baseline-inventory"` 仅断言 inventory 命令 rc=0。

**改动面**：`git diff --stat 40b4bff4~1..40b4bff4` = 16 文件；`-- spec contracts` = **0 行**；`git status --porcelain -uall` 空 rc=0（注入前/后各核一次）。

**非阻断 finding**：① 完成区「check-lit-full 12/12」等未逐项重跑，采信 out/ 留档 + shim 全流程复跑佐证；② 任务书验收「≤4」与实测 9 的偏差建议 architect 收尾时在任务书侧标注裁定；③ engineer 披露的 manifest.yaml 预存在缺陷（遗留③）确认非本任务引入。

**判决：Accepted**（两处披露偏差均成立且有据；5 项门控、全部指令计数、MC 往返与反例在 reviewer 独立重跑下复现；独立注入红/还原回绿真实）。
