# LLVM-123t: `ftfma`/`fofma` 后端（`.td` + `llvm.fma`/`fmuladd` 选择，四操作数零拷贝）

**模块**：llvm
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-157t`（记录已立）、`QEMU-070t`（语义已实现，可端到端验证）；`INFRA-099t`（门控串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 真源

- `spec/SimRISC-07 §4.x` + `contract-fp.md §fma`：`fofma rfHA, rfHB, rfHC, rfHD` = `rfHA ← rfHB × rfHC + rfHD`（**四操作数**），单次舍入。
- 编码：`op = 0x5E`（`ftfma`）/ `0x5F`（`fofma`）、`rrrr`（1 目的 + 3 源）；`scope: excluded`（`SPEC-158t` 翻转）。

### 现场事实（2026-10-21 核，执行前须复核）

- 后端已有 `rrrr` 先例（`mul_uo_rd` 等，但那是 **2 目的**）⇒ `.td` 定为 `(outs RF:$ha), (ins RF:$hb, RF:$hc, RF:$hd)`；**不得**套 `dst_dual_same`。
- **LLVM 侧无需新 intrinsic**：`llvm.fma`（必融合）与 `llvm.fmuladd`（可融合）都是通用 intrinsic；`__builtin_fma` 由 clang 直接发 `llvm.fma` ⇒ **本册只做选择**。
- **四操作数的收益（本册必须如实断言）**：
  - `llvm.fma(a,b,c)` 与 `llvm.fmuladd`（循环 `acc += a*b`）**都是零拷贝**：目的独立，**无需 `rf2rf`**；
  - ⇒ `llc` 输出须为**恰好 1 条** `fofma`，且**不得**出现 `rf2rf`/`fomul`/`foadd`。
- `excluded` 允许有 `.td`（`fence` 先例，`validate_instrinfo.py` 第 34 行）；`gen-excluded.s` 的"UNREC"反例前提需按 `LLVM-122t` 已落地的「`.td` 感知」逻辑处理（若该逻辑尚未落地，本册须先补）。

## 目标

1. `.td` 定义两条（不设 `Pattern`，由伪指令/自定义选择）；
2. `llvm.fma` → 单条 `fofma`/`ftfma`（必要时 +1 搬入）；
3. `llvm.fmuladd` → 同（**零拷贝**）；
4. 不回归既有 `fomul`+`foadd` 序列（无 FMA 的路径仍可用）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfoFP.td`、`DADAOCodeGen.td`、`DADAOISelLowering.cpp`）、`tests/llvm/lit/**`。
- **输出**：`ftfma_rrrr_rf`/`fofma_rrrr_rf` 定义；`llvm.fma`/`llvm.fmuladd` **直接 pattern 选中**（无需伪指令）；lit 用例；证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`（翻转归 `SPEC-158t`）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 选择形态：`fma(a,b,c)` 如何落成 2-address

- 目标：`fofma dst, a, b` 计算 `dst = a*b + dst_old` ⇒ 必须先把 `c` 放进 `dst`。
- 实现方式二选一（完成区写明选择）：
  - 甲：ISel 阶段生成 `COPY c→dst` + `FOFMA dst, a, b`（简单；依赖 RA 合并 COPY）；
  - 乙：自定义 DAG 节点/伪指令，在 `expandPostRAPseudo` 里先 `rf2rf` 再 `fofma`（可控，但代码多）。
- **判据**：循环内 `acc += a*b` 的 `llc` 输出必须**恰好 1 条 `fofma`**（0 拷贝）；独立 `fma(a,b,c)` 允许 1 条 `rf2rf`。

### B. 语义区分（**必须断言，不能用 fmuladd 冒充 fma**）

- `llvm.fma` 要求**单次舍入** ⇒ 只能落 `fofma`（不得展开为 `fomul`+`foadd`）；
- `llvm.fmuladd` 允许融合或分两步 ⇒ 落 `fofma`（优先）；
- 若目标关闭 FMA（未来特性开关），`llvm.fma` 必须**落 libm `fma` 调用**，不得静默展开成两条（语义错）——本册不实现开关，但须在代码注释与 lit 反例中说明该约束。

### C. lit 用例

- 正例 1：`@llvm.fmuladd.f64` 在循环（phi 累加器）⇒ 1 条 `fofma`，`FileCheck` 断言**无** `rf2rf`；
- 正例 2：`@llvm.fma.f64` 独立调用 ⇒ 1 条 `fofma`（允许 1 条 `rf2rf`）；
- 正例 3：`ftfma` 单精度同形；
- 反例：`fofma` 汇编/编码 round-trip（编码 `4422xxxx`/`442Axxxx` 现场派生）；目的 `rf0` ⇒ 汇编拒绝。

## 验收标准

1. `llc -O2`：循环形态 **1 条 `fofma`、0 条 `rf2rf`**；3-address 形态 **1 条 `fofma` + ≤1 条 `rf2rf`**（粘真实输出）。
2. `llvm-mc` 编码 == `op=0x44` + `ha=0x22/0x2A`（与 `validate-encoding` 一致）。
3. 反例：`fofma rf0, rf1, rf2` ⇒ 汇编失败/ILLI（`dst_rf0`）。
4. `check-instrinfo` 0 errors（`excluded` 有 `.td` 合规）；`check-lit` / `check-lit-full` 绿（含 `gen-excluded.s` 前提）。
5. **改 `.td` 后必须 `make install-host`**（随后 `make build-builtins` + `make build-musl-shared`，避免新鲜度门控红）。
6. `make check`（L1）rc=0；`make check-modules`（L2）rc=0。
7. **可达 FAIL ≥ 2**：① 把 `llvm.fma` 误展开成 `fomul`+`foadd` ⇒ lit「1 条 fma」断言红；② 去掉 COPY/伪指令 ⇒ `fma` 3-address 形态选不出或搬错 ⇒ 结果错（语义测试红）。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（FP `.td` 形态、ISel 现有 FP 处理、`gen-excluded.s` 的 `.td` 感知是否已落）。
2. `.td` 两条 + 编码 round-trip lit。
3. `llvm.fma`/`fmuladd` 选择（先甲后乙二选一）。
4. lit 三正例 + 反例；`install-host` + builtins/musl。
5. 反例注入 + L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- `llvm.fma` 改走 `fomul`+`foadd`（临时改 ISel）⇒ lit 断言红；还原 ⇒ 绿。
- 删掉搬入（直接 `fofma dst, a, b` 但 dst 未预置加数）⇒ 语义用例红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不加 clang builtin（`__builtin_fma` 已映射 `llvm.fma`）。
- 不做 Horner 专用 opx（另议）；不做 `fmsub`/`fnmadd`（负号用 `fosgnn`）。
- 不改 `scope`（`SPEC-158t`）；不做集成基准（`TESTCASES-058t`）。

## 完成区

**测试结果**：`.work/evidence/LLVM-123t/run.sh`：default **65/65 rc=0**、`--gates` **67/67 rc=0**（含 L1/L2）、`--inject two-step` **58/58 rc=0**、`--inject rf0` **23/23 rc=0**（各含「注入红 → `cp`+md5 还原 → 重建 → 绿」）
**修改文件**（分支 `LLVM-123t`，未 commit）：组件 **6 改 + 1 新增** —— `DADAOInstrInfoFP.td`（2 def + `GPRF_NoRF0`）、`DADAOCodeGen.td`（2 pattern）、`DADAOISelLowering.{h,cpp}`（`FMA` Legal + `isFMAFasterThanFMulAndFAdd`）、`Disassembler/DADAODisassembler.cpp`（`DecodeGPRF_NoRF0RegisterClass`）、**新增** `clang/lib/Basic/Builtins.cpp.patch`（`isBuiltinConstForTriple` 对 dadao fma/fmaf）；生成物 `gen-rrrr.s`/`gen-fast.s`/`case-ledger.tsv`/`llvm-isa-backend-matrix.{tsv,md}`；工具 `generate_lit_vectors.py`（单目的 rrrr）、`validate_instrinfo.py`（allow-list 2 条）；用例 **新增 4**：`CodeGen/DADAO/fma.ll`、`MC/DADAO/fma-encoding.s`、`tests/e2e/fma_e2e.c`、`tests/e2e/lit/fma_e2e.test`；`ir-lli/manifest.yaml`、`changelog.md`、`series`（90→91）；**用例删除：无**（`gen-excluded.s` 零 diff：fma 现有 `.td` ⇒ 不再作 UNREC 反例，属判据预期而非删例）
**验收结果**：`llc -O2` `llvm.fma.f64` = **1** 条 `fofma rf8, rf16, rf17, rf18`、`.f32` = **1** 条 `ftfma`；循环 phi 累加 `fmuladd` = **1** 条 `fofma rf8, rf16, rf17, rf8`，**0** 条 `rf2rf`/`fomul`/`foadd`；C `fma`/`fmaf` `-O2`（无额外 flag）各 **1** 条、无 `jump [rb0, fma`。**选择路径 = 甲（直接节点）且更简**：`ISD::FMA` `Legal` + `Pat` 直选，四操作数无 2-address tie ⇒ **3-address 也是 0 拷贝**；`fmuladd` 走 `isFMAFasterThanFMulAndFAdd` 在 **SelectionDAGBuilder** 直接成 `ISD::FMA`（**未用** `setTargetDAGCombine`/`ReplaceNodeResults`）。单次舍入反例（QEMU，独立 oracle = 有理数精确值）：f64 `(1+2^-52)^2−(1+2^-51)` 融合 = `0x1p-104`、两步 = `0`；f32 `(1+2^-23)^2−(1+2^-22)` 融合 = `0x1p-46`、两步 = `0` ⇒ guest exit **0**。MC：`fofma rf8,rf9,rf10,rf11`=`5f 20 92 8b`、`ftfma`=`5e 20 92 8b`（由 `opcodes.yaml` 现场派生）；rf0 目的 **rc=1**（`invalid operand`），rf0 源 **rc=0**，rf0 目的编码字反汇编为 `<unknown>`。门控：`check-instrinfo` **0 errors**、`check-isa-coverage` PASS（accept 264/reject 2，ISel yes 177）、`check-scope` **fp 64 / excluded 4**、`check_qemu_trans --strict` **266/266**、`check_lit_gen` **64/64**、`check-lit` **138/138**、L1 rc=0、L2 rc=0（含 picolibc）；`install-host` + `build-builtins` + `build-musl-shared` PASS；`check-patch-tree` **193**。
**新发现/坑**：① 任务书 §A「2-address、须先把 `c` 放进 `dst`」前提不成立——`rrrr` 是 1 目的 + 3 源（`dst=b*c+d`），**3-address 亦零拷贝**；② 任务书「编码 `4422xxxx`/`442Axxxx`」为旧估，真源 `op 0x5E/0x5F` ⇒ `5exxxxxx`/`5fxxxxxx`（以 `opcodes.yaml` 为准，已在 lit/证据中派生）；③ **C 路径前提不成立**：bare-metal triple 非 GNU ⇒ `isBuiltinConstForTriple(fma)` false + `MathErrno` 默认 on ⇒ 前端发 `call fma`。试过 `DADAOToolChain::IsMathErrnoDefault()=false`，但会让 picolibc 的 `atan/exp` 等全部变成未注册 libcall（`no libcall available for fatan`，L2 红）⇒ **回退**，改为 `Builtins.cpp` 只对 dadao 的 fma/fmaf 定向 const；④ **新增寄存器类须同步反汇编器**（否则 TableGen 生成表引用未声明的 `DecodeGPRF_NoRF0RegisterClass`，构建红）；⑤ `.td` 头部 excluded 计数为 SPEC-160t/162t 前旧文（顺手订正）
**遗留问题**：① `scope` 仍 `excluded`（按派单，翻转归 `SPEC-158t`）；② 未做 `fmsub`/`fnmadd`（负号用 `fosgnn`，按派单）；③ 集成验证（点积/GEMM/Horner）归 `TESTCASES-058t`；④ C 层 `fma` 现为 const（不设 errno，与 GNU/Windows 口径一致）；若需 errno 语义须另行裁定（本册未改全局 math-errno）

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-23，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `.td` 头部注释计数过期（64/60/4，实为 66 = 64 fp + 2 excluded） | ✅已修 | `DADAOInstrInfoFP.td` 头注释 | `check-instrinfo` 0 errors（66 defs） |
| F2 `.td` 注释称 `dst_rf0` 由 AsmParser 静态检查给出诊断，实际 MC matcher 先以 `invalid operand` 拒绝（该检查对此二助记符不可达） | ✅已修 | 注释改为 matcher/反汇编器口径 | `--inject rf0`：注入后 rc=0 被接受、还原后 rc=1 |
| F3 新增 `GPRF_NoRF0` 后反汇编表引用未声明的解码函数（构建红） | ✅已修 | `DADAODisassembler.cpp` 加前向声明 + `DecodeGPRF_NoRF0RegisterClass` | `build-mc`/`install-host` rc=0；rf0 编码字 `<unknown>` |
| F4 证据脚本按 `[23:18]` 顺序解析位域（negative shift，oracle 红） | ✅已修 | `reversed(...)` 取 lo/hi | default 61/61 |
| F5 `chk_in` 用 BRE 匹配含 `[` 的 encoding 串（恒不中） | ✅已修 | 改 `grep -F` | `mc-fofma-encoding`/`mc-ftfma-encoding` PASS |
| F6 曾把 toolchain `IsMathErrnoDefault()` 全局关掉（L2 picolibc 红：`no libcall available for fatan/fexp`） | ✅已修（回退） | 撤掉该 override；改 `Builtins.cpp` 定向 const | L2 rc=0；C `fma` 仍 1 条 |
| F7 生成器 `_td_mnemonics()` 读提交补丁；未导出前把 fma 误判为反例（`{rd8,rd9}` 形态） | ✅已修 | 先 `make_patch` 再重生成 | `gen-excluded.s` 零 diff；`gen-rrrr.s` 2 正例 |
| F8 注入模式期望值写反（`chk ... 1 $? 1`） | ✅已修 | 改显式 `accepted`/`nonzero` 观察 | two-step 54/54、rf0 23/23 |

判决：8 条 finding 全部修复；无未修项（遗留 ①–④ 为派单边界/裁定项）。状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**判决：Accepted**（全部验收项本人重跑通过，无阻断；仅记录，不改交付物）

**重跑记录（本人命令 + 真实输出/退出码）**
- 四条路径（自建 IR/C，非工程师文件）：`@llvm.fma.f64`→`fofma rf8,rf16,rf17,rf18`(1 条)；`.f32`→`ftfma`(1)；C `fma`/`fmaf` `-O2`→`fofma`+`ftfma` 各 1、`jump [rb0, fma`=0；`llvm.fmuladd` phi 累加→恰 1 条 `fofma rf8,rf17,rf18,rf8`，`rf2rf/rb2rb/rd2rd/fomul/foadd`=0（零拷贝、无拆开）。
- 自建单次舍入（QEMU，独立有理数 oracle `Fraction` 精算+round-rn-even，自检与 IEEE `float` 一致）：A/f64 `a=1+2^-28,b=1-2^-28,c=-1`→fused `-2^-56`/two-step `0`；B/f32 `a=1+2^-13,b=1-2^-13,c=-1`→`-2^-26`/`0`；C/f64 `a=1+2^-30,b=1+2^-30,c=-1`→`0x1.00000002p-29`/`0x1p-29`。三组 `fused≠two-step`，QEMU guest **exit=0**。
- 编码/约束（`llvm-mc` 现场）：`fofma`=`5f20928b`、`ftfma`=`5e20928b`；由 `opcodes.yaml` 独立派生（op 0x5F/0x5E<<24|ha<<18|hb<<12|hc<<6|hd）一致；目的 `rf0` **rc=1**(invalid operand)、源 `rf0` rc=0。
- 选择路径：`ISD::FMA` `Legal` + `isFMAFasterThanFMulAndFAdd`(f32/f64)=true（未用 `setTargetDAGCombine`），四操作数无 tie，3-address 亦 0 拷贝，未拆 `fmul+fadd`。
- 覆盖核对：`tests/` 新增 **4**(fma.ll/fma-encoding.s/fma_e2e.c/fma_e2e.test)、删除 **0**；`gen-excluded.s` `git diff`=0 行（零 diff 属实）；`check-patch-tree` **193** OK；`Builtins.cpp.patch` 仅对 dadao `fma/fmaf/__builtin_fma/__builtin_fmaf` 返 true，`fmal/fmaf16` 落 break，其它 builtin 不动。
- 门控（本人重跑 rc=0）：`check-instrinfo` 0 errors；`check-scope` PASS（fp **64**/excluded **4**，现场统计）；`check_qemu_trans --strict` **266/266**；`check-isa-coverage` PASS(accept 264/reject 2, yes 177)；`check_lit_gen` **64/64**；`check-lit` **138/138**；**L1 `make check` rc=0**；**L2 `make check-modules` rc=0**；证据脚本 `run.sh` default **65/65 rc=0**。
- 注入 2 次（`cp`+md5 还原，禁 checkout/restore/stash）：① `ISD::FMA`→`Custom`+`FMUL`/`FADD` ⇒ llc `fofma=0,fomul=1,foadd=1`、QEMU guest **exit=1（红）**；还原 md5 一致、回绿。② `.td` `GPRF_NoRF0`→`GPRF`(2 处) ⇒ `fofma rf0` 目的 **rc=0（反例红，原 rc=1）**；还原 md5 一致、rc=1 回绿。还原后源树两文件 md5 复核原值、`git status`/`git diff` 空、install-root 工具未污染。

**约束核验**：不改 spec/contracts（scope 仍 excluded，归 SPEC-158t）✓；`gen-excluded.s` 零 diff 未删例 ✓；`Builtins.cpp` 只定向 fma 族 ✓；未 commit/push ✓（提交权归 architect）。
**判决依据**：路径未拆、计数相符、单次舍入对、编码/约束对、覆盖未删、门控全绿、注入两次均红并回绿 ⇒ **Accepted**。
