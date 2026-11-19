# m15-idl-015: 浮点语义库移植（ft / binary32 族，移植 UDB `fp.idl`）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-013`（语义库 v1）；参考源 `.cache/refs/riscv-unified-db/spec/std/isa/isa/fp.idl`（只读）
**可并行分片**：否（新建库文件 + 改共享 `render.py`）
**预估**：2–4 天（分 2 批）
**档位**：大改
**状态**：待开始

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

（待填）
