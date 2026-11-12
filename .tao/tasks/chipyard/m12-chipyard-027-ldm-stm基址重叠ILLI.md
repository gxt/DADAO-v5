# m12-chipyard-027: `ldm`/`stm` 基址/索引重叠 ⇒ ILLI（RTL）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-005`（spec 定稿）
**可并行分片**：否（单组件单写者）
**状态**：待开始

## 用户裁定

`ldm`/`stm` 的基址/索引寄存器**不得**落在被传送的寄存器范围内 ⇒ 违反 ⇒ **ILLI**（原口径「允许重叠、按原始值计算」作废）。

## 范围（只改 QEMU）

1. `WumingDecoder.scala` 的 `ldm`/`stm` 译码加检查（与既有 `mreg_range_overflow` 同位置，`d.ill := true.B`）：
   - **只检查 `ldm`**：RD 形式 `rdHC ∈ [rdHA, rdHA+immu6)` ⇒ 非法；RB 形式 `rbHB ∈ [rbHA, rbHA+immu6)` ⇒ 非法
   - **`stm` 不加检查**（允许重叠：只读传送范围、不写寄存器）
   - **RA/RF 形式：不适用**（范围在 RA/RF bank，基址/索引分别在 RB/RD）
2. 检查必须在**任何元素处理之前**（与既有的 `immu6=0`/范围检查同位置）。
3. 不改其它语义。

## 验收

构造 3 组例：`ldm` RD、`ldm` RB（应 ILLI）；`stm` RD/RB 重叠（应正常执行）：
- 基址落在范围内 ⇒ **ILLI**（且不发访存、不写寄存器）
- 基址在范围外一位（边界）⇒ 正常执行

`check-inst` rc=0；273 例 md5 不变；**可达 FAIL 注入**（去掉检查 ⇒ 该例不再 ILLI）。

## 纪律

- 补丁走 `make_patch`；`JOBS=8`；不占 207/208
- 注入还原 `cp`+md5+`touch`（`cp -p` 假绿坑）
- 不 commit/push、不改台账；状态改 `待验收`
- 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 审阅记录

（待填）
