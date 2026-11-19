# m15-idl-016: 浮点语义库 fo 族 + remainder（binary64）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-015`（库骨架 `idl/lib/fp.idl`、ft 族 53 函数已落地）
**可并行分片**：否（与 `m15-idl-007` 同改 `idl/lib/fp.idl`，串行）
**预估**：2–3 天（分 2 批）
**档位**：大改
**状态**：待开始

## 背景（`m15-idl-007` 批 2 的阻塞）

`m15-idl-007` 批 2 剩 8 条写不出来，根因是**库缺口**（不是散文问题）：

- **7 条 fo 侧**（`foadd`/`fosub`/`fomul`/`fodiv`/`forem`/`fosclb`/`foroot`）：库里只有 **f32** 的打包/舍入原语，**没有 f64 的**（无 `packToF64UI`、无 `softfloat_roundPackToF64`）；位级手写每条 150–250 行，且 `fomul` 需 106 位积（`*` 非加宽）⇒ 属「位级又过长」。
- **`ftrem`**：库无 f32 remainder，UDB 也无（RISC-V 无 `frem`）⇒ 需写迭代最近整数商（≈100 行）。

用户 2026-11-19 已裁定「浮点库分两步，先 ft；`fo` 另立任务」——本任务即该「另立」部分。

## 目标

在 `idl/lib/fp.idl` 追加 **fo（binary64）族 + remainder**（与 §4.7 ft 族同构命名）：

1. **底座**：`packToF64UI`、`softfloat_roundPackToF64`、`softfloat_normRoundPackToF64`、`softfloat_shiftRightJam64`（可复用 ft 侧已有）、`fo_clz64`（如缺）；
2. **格式转换**：`fo_to_i64`/`fo_to_ui64`/`i64_to_fo`/`ui64_to_fo`（含 `_no_flag` 变体）、`fo_to_ft`/`ft_to_fo`（若 015 未覆盖）；
3. **算术**：`fo_add`/`fo_sub`/`fo_mul`/`fo_div`/`fo_muladd`/`fo_sqrt`、`round_fo_to_integral`、`fo_scale`（scaleB）；
4. **remainder**：`ft_rem`、`fo_rem`（IEEE 754-2019 remainder：`x − n·y`，`n` = 最近整数商、平局取偶）；
5. NaN/分类谓词按 ft 侧同构补 `is_dp_*`（如缺）。

**适配口径**（与 015 一致）：标志写 `rf0[4:0]`、舍入读 `rf0[33:32]`、**无 NaN-boxing**；`fo` 目的整 64 位写。

## 交付

1. `idl/lib/fp.idl` 追加上述函数（**不要**改 ft 族现有实现）；
2. `idl/README.md §4.7` 的指针说明扩到「ft/fo 两族 + remainder」；
3. `idl/.manifests.toml` 若是逐文件锁则同步（当前按 N21 延后，仅 `lib` 子目录登记）。

## 验收（逐条贴真实 rc）

1. `idlc compile --root isa`（§4 + `idl/lib/fp.idl`）rc=0；
2. 样例 operation 同时调用 `fo_add`/`fo_rem`/`ft_rem` 能编译 + 类型检查 rc=0；
3. `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；
4. **独立 oracle（关键）**：`Fraction` + IEEE 754-2019 规则算期望，`fo_add/sub/mul/div/sqrt` 各 **≥1000 例**、`ft_rem`/`fo_rem` 各 **≥800 例**（含 ±0、±Inf、NaN/sNaN、次正规、最大有限、平局与 `x − n·y` 精确性），**值 + 标志**逐位比对，报失配数（目标 0）；
5. **可达 FAIL ≥3 路**：舍入档硬编码、溢出判据、remainder 平局取偶各一路（`cp`+md5 还原）；
6. 合并态（`Process-07 §5a`）：在当前 master 上跑上述门控。

## 批次

- **批 1**：底座 + 转换 + 谓词（`packToF64UI`/`roundPackToF64`/`fo_to_i64`/`i64_to_fo`/`is_dp_*`）；
- **批 2**：算术（`fo_add/sub/mul/div/muladd/sqrt/scale`/`round_fo_to_integral`）+ `ft_rem`/`fo_rem`。

## 待裁定

（无。用户已裁定「先 ft、fo 另立任务」，本任务即该另立项；`ft2it` 等写宽问题属 `m15-idl-007` 的待裁定，不在本任务。）

## 完成区

（待填）
