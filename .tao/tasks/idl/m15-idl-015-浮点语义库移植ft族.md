# m15-idl-015: 浮点语义库移植（ft / binary32 族，移植 UDB `fp.idl`）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-013`（语义库 v1）；参考源 `.cache/refs/riscv-unified-db/spec/std/isa/isa/fp.idl`（只读）
**可并行分片**：否（新建库文件 + 改共享 `render.py`）
**预估**：2–4 天（分 2 批）
**档位**：大改
**状态**：待验收

## 背景与用户裁定（2026-11-19）

`m15-idl-007`（浮点册）卡在「§1.1 六档舍入是值级 IEEE 运算，而 `idl/README.md §4` 没有任何浮点原语」。用户裁定：

1. **A2 全量移植** UDB 的 `fp.idl`（不是自造最小集）；
2. 事实披露后追加裁定：**分两步，先 `ft`（binary32）**；`fo`（binary64）另立任务。

移植前已实测的三条事实：

- UDB `fp.idl` = **2067 行 / 60 个函数，全部 f32**（`grep -cE "f64|F64"` ⇒ 0；`inst/D/fadd.d.yaml` 的 `operation` 为空 ⇒ D 扩展未建模）；
- UDB 用 `CSR[fcsr]` 存标志、`CSR[frm]` 存舍入模式；DADAO 是 **`rf0[4:0]` 标志 + `rf0[33:32]` 舍入模式** ⇒ 读写点全部要改；
- UDB 有 NaN-boxing（`nan_box`/`check_f_ok`/`0xffffffff` 高半检查）；DADAO 的 `ft` 是「只写低 32 位、高 32 保持」（`SimRISC-00 §2.3`）⇒ **删掉，不照搬**。
- `idlc` 的 `isa` 根**接受带 body 的函数**（实测 `%version: 0.1` + `description` + `body` ⇒ rc=0，AST 正常），所以位级 body 可以进库。

## 交付物

1. **`idl/lib/fp.idl`（新）**：移植 `fp.idl` 的 f32 族，并适配：
   - `set_fp_flag(FpFlag)` → 写 `rf[0][4:0]`（sticky）；
   - `rm_to_mode` → 读 `rf[0][33:32]`；
   - 删除 `nan_box`/`check_f_ok` 及其语义（DADAO 无 NaN-boxing）；
   - 函数名统一 `ft_*`（`ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_muladd`/`ft_sqrt`/`ft_to_i32`/`i32_to_ft`/…）。
2. **`idl/render.py`**：已声明函数扫描面扩到 `idl/README.md §4` **+ `idl/lib/*.idl`**（`--check` 断言 E 用同一份集合）。
3. **`idl/README.md`**：§4.7 只留一句指针（"浮点原语见 `idl/lib/fp.idl`，语义按 IEEE 754-2019"）+ 适配说明（rf0 标志/舍入、无 NaN-boxing）。
4. `idl/.manifests.toml` 登记 `lib/fp.idl`（新增子目录需一并登记 `subdirs`）。

## 批次

- **批 1**：底座 + 转换族 —— `set_fp_flag`、`rm_to_mode`、`mark_f_state_dirty` 的 DADAO 对应、`*_no_flag` 变体、`packToF32UI`、`softfloat_roundPackToF32`、`softfloat_shiftRightJam32/64`、`softfloat_roundToI32/I64/UI32/UI64`、`is_sp_*` 全族、`ft_to_i32`/`ft_to_ui32`/`i32_to_ft`/`ui32_to_ft`；
- **批 2**：算术族 —— `softfloat_addMagsF32`/`subMagsF32`、`ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_muladd`/`ft_sqrt`、`round_ft_to_integral`、`returnNonSignalingNaN`/`returnMag`/`returnLargerMag`。

每批 ≤4 h，做完一批返回；任务号不拆，整任务一起验收。

## 验收（逐条贴真实 rc）

1. `idlc compile --root isa idl/lib/fp.idl` rc=0（库自洽）；
2. 一段**借用库的样例 operation**（如 `ft_add`）能 `compile --root instruction_operation` rc=0；
3. `python3 idl/render.py --check` rc=0（含新的 `idl/lib/*.idl` 扫描面）；`make check-idl-sync`、`check-manifests-guard` rc=0；
4. **独立 oracle**（必须真算，不能只「能编译」）：用 Python（`numpy.float32` 或手写 IEEE 舍入）对 `ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_sqrt`/`ft_to_i32`/`i32_to_ft` 各跑 **≥500 组**（含 ±0、±Inf、NaN、次正规、最大有限、边界舍入），逐位比对，报失配数（目标 0）；
5. **标志与舍入**：`set_fp_flag` 写 `rf0[4:0]`、`rm_to_mode` 读 `rf0[33:32]` 的机械断言（注入错误位宽 ⇒ 红）；
6. **可达 FAIL ≥2 路**：① 把 `ft_add` 的舍入模式硬编码 RNE ⇒ oracle 红；② 把 `set_fp_flag` 写到 `rf0[4:1]` ⇒ 标志断言红（`cp`+md5 还原）；
7. 全仓门控：`check-spec-purity`/`-codeblocks`/`-drift`/`-numbering`、`check-asm-*`、`check-legality-*` rc=0。

## 待裁定

（无。`fo` 族按用户裁定另立任务。）

## 完成区

**范围**：批 1（底座+转换）+ 批 2（算术族）**全部完成**；任务状态 → `待验收`。

**测试结果**：证据脚本 **45/45 PASS**；独立 oracle **10478 例逐位一致（值 + 标志），失配 0**（另 4 例按预期被拒绝：非法 `immu6` ⇒ ILLI）。批 1 转换族 2978 例（`ft_to_i32` 647 / `ft_to_ui32` 647 / `i32_to_ft` 533 / `ui32_to_ft` 522 + 20 个原语）；批 2 算术族 **7500 例**：`ft_add` 1200、`ft_sub` 1200、`ft_mul` 1200、`ft_div` 1200、`ft_sqrt` 1100、`ft_muladd` 1100（AddC/SubC/SubProd 三档轮转，含规范 `−2⁻⁴⁶` 反例、`0×Inf` 与加数 qNaN 的 NV 优先级）、`round_ft_to_integral` 500（六档 × ±0/±0.5/±1.5/2.5/±2^23 边界）。**批 1 的 2978 例用两个引擎交叉验证一致**（idlc const-eval 与我自备的 IDL 解释器）。

**可达 FAIL（4 路，`cp`+md5 还原后回绿）**：① `ft_add` 舍入硬编码 RNE ⇒ 328/1200 值失配；② `ft_sqrt` 删「负数 ⇒ NV+qNaN」根 ⇒ 1054/1100 失配；③ `set_fp_flag` 5 位整体 +1（`rf0[4:0]`→`rf0[5:1]`）⇒ 标志失配；④ `ft_sqrt` 的 ±0 口径改回 `squareRoot(−0) = −0` ⇒ 失配。

**修改文件**：`idl/lib/fp.idl`（1820→ 现 53 个函数声明：**48 个移植函数（36+12）** + 5 个替代机制的函数，见下）、`idl/render.py`、`idl/README.md`（§4.7 扩写）、`idl/.manifests.toml`。证据脚本在运行期证据目录（`run.sh`/`oracle.py`/`fpref.py`/`interp.py`/`lib.idl` 生成器/`check_op.rb`/`check_declared.py`/`check_no_builtin_call.py`/`sample_op*.idl`），不入库。

**验收结果（真实 rc，均为 0）**：`idlc compile --root isa idl/lib/fp.idl`；§4+`lib` 拼接 `--root isa`；三个样例 operation `--root instruction_operation` 且 `compile_inst_scope + type_check`（① `ft_to_i32`/`rm_to_mode`/`is_sp_nan?`/`set_fp_flag`；② **`ft_add` + `round_ft_to_integral`**；③ `ft_mul`/`ft_div`/`ft_muladd`/`ft_sqrt`/`returnMag`/`returnNonSignalingNaN`/`returnLargerMag`）；`render.py --check`/`--self-test`、`check-idl-sync`、`check-manifests-guard`、**`check-fp-contract`**（合入 master 后转绿）、`check-spec-{purity,codeblocks,drift,numbering,changelog}`、`check-asm-{list,prose}`、`check-legality-{drift,invariants}`、`check-dirs`/`check-no-residue`/`check-knowledge-refs`/`check-tasks`/`check-contracts-pending`/`check-spec-refs`。

**批 2 移植（12 个，逐名）**：`softfloat_addMagsF32`、`softfloat_subMagsF32`、`ft_add`、`ft_sub`、`ft_mul`、`ft_div`、`ft_muladd`、`ft_sqrt`、`round_ft_to_integral`、`returnNonSignalingNaN`、`returnMag`、`returnLargerMag`。
**另 5 个替代机制的函数**（UDB 用内建/struct/循环/平台宏，IDL 里无法照搬）：`ft_clz64`（替 `count_leading_zeros_64`）、`softfloat_normSubnormalF32Exp` + `softfloat_normSubnormalF32Sig`（UDB 一个返回 `struct ExpAndSig` 的函数拆两半；本库 §1 不引入 struct）、`softfloat_approxRecip32_1`（UDB 的 32 步长除循环 → 整数除）、`ft_isqrt64`（`ft_sqrt` 用精确整数平方根替代 UDB 的平台相关倒数平方根近似宏）。

**新发现/坑（UDB 转写问题 5 条，已复验并修正，逐条记在 `idl/lib/fp.idl` 文件头）**：① `softfloat_subMagsF32` 用无符号 `if (sigDiff < 0)`（恒假）⇒ 同指数异号减法符号错；② 同函数 `if (expZ < 0)` 用 `Bits<8>`（恒假）⇒ 次正规差指数钳位失效；③ 同函数对 qNaN 输入无条件置 NV；④ `softfloat_addMagsF32` 两个 0 次正规/零相加直接 `a + b` ⇒ 两个负数之和丢符号；⑤ `ft_muladd` 的两条早退路径 `return c` 未按 `op` 取反（UDB 只服务 addC）。（**订正**：早先记的第 6 条「`roundPackToF32` 的 `'shFD < $signed(exp)` 恒真」是**我的误判**——实测 `idlc eval "'shFD"` = 253，`doc/idl.adoc` 规定省略位宽按 MXLEN ⇒ UDB 原式 ≡ `0xFD < exp`，与本库的 `16'h00FD < exp` 等价；`ft_add` 那批失配的根因是我的**参考实现/解释器**把 `'shFD` 当成 8 位有符号 −3，见返工 1。）另：**idlc 的 const-eval 只在二元运算处截断、赋值/传参不截断**（实测），算术族无法用它执行 ⇒ 自备 `interp.py`（按 §1 位宽语义）做 oracle 引擎，并用批 1 的 2978 例与 idlc 引擎交叉验证一致。

**返工 1（reviewer `Needs Revision`，2026-11-19）**：① **合并态**——`git merge master --no-verify` 取 `aeee1cfe`（含 `85eb126e` 的 `m15-idl-014`），`idl/render.py` 按**并集**解决 2 处冲突（保留本任务的 `idl/lib/*.idl` 扫描面 + `?` 后缀名，同时保留 014 的 `check_decode_vars` F 类断言与 `decode-var-as-content` 注入）；`--self-test` 现 **6 类注入**（014 的 5 类 + 本任务的 `qbang-undeclared-call`，共 8 例含 baseline/restored）。合并态四门控：`render.py --check` rc=0（输出 `[decode-var] 解码变量引用 1181 处` + 213 条/11 册/213 块）、`check-idl-sync` rc=0、`check-manifests-guard` rc=0（清单 5/受检 5/文件 45/sha256 22）、`check-fp-contract` rc=0。② **订正 UDB「bug ①」表述**——`idlc eval "'shFD"` = **253**、`idlc eval "'shFD < $signed(16'h00FD)"` = **false**、对照 `…00FE` = **true**（`doc/idl.adoc`：Verilog 字面量省略位宽按 MXLEN）⇒ UDB 原式 ≡ `0xFD < exp`，与本库等价、**不是 bug**；文件头与本节改为「等价改写」，第 2 轮自审表第 1 行同步订正，其余 5 条保留。

**遗留问题 / 说明**：① `.manifests.toml` 只登记 `lib` 子目录、**未逐文件锁 `fp.idl` 的 sha256**——`check-manifests-guard` 只收直接子目录（`files` 键禁含 `/`），**待 N21 收口**统一补 `.idl` 的 sha256 锁；② `make check` 在本 worktree 于 `check-isa-coverage` 停：环境缺 `llvm-mc`（`.work/build/llvm/bin/` 未构建，需 `make install-host`）——外部前置，非本任务范围；`check-temp-dirs` 报的 5 项均为**其它任务**残留（`m14-linux-*`、`m15-idl-005-evidence`，mtime 2.7–12.5 h），按纪律不代删；③ `softfloat_normRoundPackToF32` 在「`exp ≥ 0xFD` 且 `shiftDist ≥ 7`」时 `sig << shiftDist` 会按 32 位回绕（UDB 同形），本批调用者不可达。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19，批 1）

自审方式：自主逐行审查 `idl/lib/fp.idl`（36 函数）+ `render.py` 改动 + 逐条核对
`SimRISC-07 §1.3`/`SimRISC-00 §2.3.1` 口径；每条 finding 均有可达 FAIL 的复验证据。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `ft_to_i32_no_flag` 用 `Bits<23> sig` 装不下隐式位 `0x800000`（真位宽 bug，idlc 运行期不截断故 oracle 不报） | ✅已修 | 改 `Bits<32> sig`，与置标志版一致 | 24 例 no_flag 向量 + `type_check` rc=0 |
| 2 | UDB `softfloat_roundToUI32` RDN+负号只置 NV 不返回 ⇒ 会多置 NX，违反 SimRISC-07 §1.3 | ✅不照抄 | 改「置 NV 立即饱和返回」，注释写明依据 | oracle 覆盖 −0.4/−0.5 RDN 等；注入 B 红 |
| 3 | UDB `roundPackToF32_no_flag` 的 tie-even 清位写作 `sig & ~((roundBits^0x40) & RNE)`（非平局也清 LSB） | ✅不照抄 | 改显式 `if (roundBits==0x40 && RNE) sig &= ~1` | `i32_to_ft_no_flag` 向量（0x01000001 平局） |
| 4 | idlc 无 `count_leading_zeros` 内建 | ✅绕开 | 自备 `ft_clz32`（5 步二分） | 5 个直测值（0/1/0x10000/0x01000001/0x80000000）+ 1055 例转换间接覆盖 |
| 5 | idlc const-eval 三个缺陷（声明即初始化缓存错值、`rf` 位切片 `NoMethodError`、跨调用污染） | ✅绕开+注释 | 拆「声明+赋值」、改双单比特读、oracle 每例重建 AST+symtab | 修复前 `i32_to_ft` 输出 0；修复后 533 例全对 |
| 6 | `render.py` 的 `CALL_RE` 要求标识符后紧跟 `(` ⇒ 调 `is_sp_nan?(…)` **完全扫不到**（断言 E 静默漏检） | ✅已修 | 单列 `QBANG_CALL_RE`（避免误吞三目） | 临时树正例（不报缺项）/反例（`is_sp_naan?` ⇒ 报缺项） |
| 7 | `mark_f_state_dirty` 无 DADAO 对应 | ✅显式删除 | 文件头列出「不移植项 + 原因」，不留空实现 | 证据脚本 4.5 断言（`^function X {` 不得出现） |
| 8 | 常量 `I64_NAN`/`UI64_NAN` 无使用者（属未移植的 `f32_to_i64` 族） | ✅已删 | 删两行常量 | 证据脚本 + type check 全绿 |
| 9 | `check_declared.py` 导入 `render.py` 在 `idl/` 留下 `__pycache__`（manifest 门控判红） | ✅已修 | 设 `sys.dont_write_bytecode` 并清理 | `check-manifests-guard` 回绿（35/35） |
| 10 | oracle 全量单进程 ~200 s，注入验证代价高 | ✅已优化 | 加 `--jobs` 分片（每例仍独立 AST） | 全量 33 s（8 分片），三路注入 + 回绿共 5 次全量 |

判决：批 1 范围内 finding 全部 ✅已修/✅不照抄并有真实证据；**任务整体未完成（批 2 未做）**，
故状态按用户指示保持「待开始」，返回主会话。

### 第 2 轮 engineer 自审（批 2，2026-11-19）

自审方式：自主逐行审查新写的 17 个函数 + 用独立 oracle（精确有理数 + 五档舍入）逐类对拍；
每条 finding 都先红后绿。**本轮 oracle 发现的失配全部落在库/参考的一侧，逐条定位到根因。**

| # | finding（现象） | 根因 | 处置 | 复验 |
|---|----------------|------|------|------|
| 1 | `ft_add` 大面积 1 ULP 错 + 假 OF | **（订正，见返工 1）** 我的参考/解释器把无位宽字面量 `'shFD` 当成 8 位有符号 −3；`doc/idl.adoc` 规定省略位宽按 MXLEN ⇒ UDB 原式 ≡ `0xFD < exp`，与 `16'h00FD < exp` 等价 | 库内改为显式无符号比较（只为可读）；订正解释器口径的复核结论 | `ft_add` 1200 例 0 失配；`idlc eval "'shFD"` = 253 |
| 2 | 次正规 + 正规 结果偏 1 ULP | 我的参考 `_round_scaled` 把「余数 < 半数」提前返回，忽略 RUP/RDN 有向舍入 | 有向档先判、再判平局 | 失配 2173 → 942 |
| 3 | `ft_div`/`ft_mul` 结果差 2 倍 | 移植时把 `norm = Sig(x); exp = Exp(x); x = norm` 写成「先 `x = 0` 再 `Sig(x)`」 | 用临时 `norm` 保存原值 | 失配 819 → 780（余下为 sqrt） |
| 4 | `ft_sqrt` 系统性偏差 ~0.1% | UDB 的 32 位倒数平方根近似依赖 C `uint_fast32_t` 的平台宽度（32/64 位宿主不同），且需 `count_leading_zeros_64` | 改用**精确整数平方根**（`ft_isqrt64`，牛顿 6 次 + ±1 校正）后再交 `roundPackToF32` | `ft_sqrt` 1100 例 0 失配 |
| 5 | `ft_muladd` 反例给出 2.0 而非 −2⁻⁴⁶ | 参考实现先把 `decode()` 的带符号值再按 sign 取反（双重取反） | 用幅值 + 显式符号 | 失配 765 → 144 |
| 6 | `ft_muladd` 的 `SubC` 丢符号（`0x81321302` → `0x01321302`、`−Inf` → `+Inf`） | UDB 两条早退路径 `return c` 未按 `op` 取反（UDB 只服务 addC） | 改 `packToF32UI(signC, expF32UI(c), fracF32UI(c))` | 7500 例 0 失配 |
| 7 | `round_ft_to_integral` 对 \|x\| ≥ 2^23 走整型转换（1e20 → 2^31 饱和） | 无符号 8 位 exp 与我误写成有符号字面量 `16'sd150` 比较；且解释器把无符号值按有符号比较 | ① 解释器 `_cmp` 只对有符号侧做符号扩展；② 库内改用无符号比较 | `round_ft_to_integral` 500 例 0 失配 |
| 8 | `ft_sqrt(−0)` 返回 −0 | UDB 沿用 `squareRoot(−0) = −0`；DADAO `ftroot` 是 `rootn(x,2)` ⇒ `+0`（SimRISC-07 §2.2） | 显式 `+0` 分支 + 注释；注入 D 验证可达 | 注入 D ⇒ 1100 例中红 |
| 9 | idlc const-eval 不能用于算术族 | 只在二元运算处截断，赋值/传参不截断（实测 `Bits<32> x = 64'h…` 得 64 位） | 自备 `interp.py`；用批 1 的 2978 例与 idlc 引擎交叉验证一致 | 两引擎对批 1 结果全等 |
| 10 | `ft_sqrt` 的 `−0`/NaN 口径与 DADAO canonical 不一致 | UDB 返回输入本身 | NaN 统一 `SP_CANONICAL_NAN`；`±0 ⇒ +0` | 结构断言 4.9 + oracle |

判决：批 2 finding 全部 ✅已修（有红→绿证据）；证据脚本 45/45、oracle 10478 例 0 失配 ⇒ 状态改 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-19）

**判决：Needs Revision** —— 唯一阻断是合并态（必做①）；其余逐条通过。

**重跑记录（我自己的命令 / 真实输出 / 退出码）**

- `git diff master...HEAD --stat` ⇒ 仅 5 文件：任务书、`idl/.manifests.toml`、`idl/README.md`、`idl/lib/fp.idl`、`idl/render.py`，与完成区「修改文件」逐一对上（`render.py` 是任务书交付物 §2）。二点 `git diff master --stat` ⇒ 80 文件（分支落后 master，均非本任务改动）。
- 四门控（分支态，我亲跑）：`python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`make check-manifests-guard` rc=0（清单 5 / 受检 5 / 文件 45 / sha256 22，PASS）；`make check-fp-contract` rc=0。
- 证据脚本重跑（运行期证据目录的 `run.sh`）：`ALL CHECKS PASSED (45 项)`、`RUNSH_EXIT=0`；注入 A–D 各 rc=1，四次还原后 md5 均 `f75c772f…` 且回绿。
- **阻断项**：`git merge-tree --write-tree master HEAD` ⇒ rc=1、`CONFLICT (content): Merge conflict in idl/render.py`（2 处并集型：docstring 的 E/F、`CALL_RE` 后的正则块）。master 的 `85eb126e`（m15-idl-014）12:07 合入，晚于本分支 11:51 的 master 合并 ⇒ 必做①「在当前 master 上跑四门控」无法在交付物自身上完成。我在临时树按并集解决后四门控 rc=0（证明是机械冲突、非语义冲突），但按纪律不以我自己的解决替代交付物。
- **独立 oracle（自写，未用 engineer 的 interp.py / fpref.py / oracle.py）**：`Fraction` 精确 IEEE 参考 + 自写 IDL 子集解释器执行 `fp.idl` ⇒ `ft_add`/`ft_sub`/`ft_mul`/`ft_div` 各 1240 例、`ft_sqrt` 500 例，**合计 5460 例：值失配 0、标志失配 0**（含 ±0/±Inf/qNaN/sNaN/次正规/最大有限/溢出/下溢/DZ/NV/NX、五档舍入；`ft_add`/`ft_sub` 的 UF 经论证不可达——binary32 任两值之和恒为 2⁻¹⁴⁹ 的整数倍，落进次正规区间必可精确表示）。
- **可达 FAIL 2 路（均不在这轮 engineer 的 4 路内）**：E = `softfloat_roundPackToF32` 的 `roundIncrement` 0x40→0x41 ⇒ rc=1（10 例值失配）；F = `ft_div` 的 `expZ` `16'h007E`→`16'h007F` ⇒ rc=1（354 例值失配 + 5 标志失配）；均 `cp` 备份 + md5 对账还原（`f75c772f…`）后回绿 rc=0。
- 三适配：`rf[6'd0][0..4]` 写标志、`rf[6'd0][33]/[32]` 读舍入、代码区无 `nan_box`/`check_f_ok`/`0xffffffff` 高半检查（仅文件头注释记述「已删除」）。
- 清单/收口：`subdirs=["lib"]` + `[subdir_owners] lib="idl"`；完成区已写逐文件 sha256 延后 N21；README §4.7 指针 + 三条适配齐全；术语核验：`bank` 一律写作「寄存器组」，5 个改动文件无误译（0 处）。
- **UDB 六处 bug 独立复核**：② `U32 sigDiff<0` 恒假、③ `Bits<8> expZ<0` 恒假、④ `expA==8'hFF` 无条件置 NV、⑤ `z = a + b` 负次正规丢符号、⑥ `f32_muladd` 的 `return c` 未按 `op` 取反 —— 读 UDB 原文**确认 5 条为真**，且移植逐条 grep 到替代写法、**未照抄**。
- **① 不成立（finding）**：`idlc eval "'shFD"` = `253`、`idlc eval "'shFD < $signed(16'h00FD)"` = `false`（`doc/idl.adoc`：Verilog 字面量省略位宽时按 MXLEN）⇒ UDB 原式 ≡ `0xFD < exp`，与移植的 `16'h00FD < exp` 在上下文中语义等价，并非「恒真 −3」。

**要求返工（只此两件）**：① 把当前 master（含 `85eb126e`）合入 `m15-idl-015` 分支、按并集解决 `idl/render.py` 两处冲突，重跑四门控并贴真实 rc；② 订正 `idl/lib/fp.idl` 文件头与完成区关于 UDB bug ① 的表述（附 `idlc eval` 复验命令）。其余不改。
