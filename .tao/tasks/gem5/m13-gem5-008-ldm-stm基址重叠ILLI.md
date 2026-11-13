# m13-gem5-008: `ldm`/`stm` 基址/索引重叠 ⇒ ILLI（gem5）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-005`（spec 定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 用户裁定

**`ldm`** 的基址/索引寄存器**不得**落在被传送的寄存器范围内 ⇒ 违反 ⇒ **ILLI**；**`stm` 允许**（只读、不写寄存器）；RA/RF 不适用（用户 2026-11-13 三轮收敛口径）。

## 范围（只改 gem5）

1. `src/arch/dadao/exec/` 的 `ldm`/`stm` 执行路径（`b1.cc` 一族）加检查：
   - **只检查 `ldm`**：RD 形式 `rdHC ∈ [rdHA, rdHA+immu6)` ⇒ 非法；RB 形式 `rbHB ∈ [rbHA, rbHA+immu6)` ⇒ 非法
   - **`stm` 不加检查**（允许重叠：只读传送范围、不写寄存器）
   - **RA/RF 形式：不适用**（范围在 RA/RF bank，基址/索引分别在 RB/RD）
2. 检查必须在**任何元素处理之前**（与既有的 `immu6=0`/范围检查同位置）。
3. 不改其它语义。

## 验收

构造 3 组例：`ldm` RD、`ldm` RB（应 ILLI）；`stm` RD/RB 重叠（应正常执行）：
- 基址落在范围内 ⇒ **ILLI**（且不发访存、不写寄存器）
- 基址在范围外一位（边界）⇒ 正常执行

`check_b1`/`check-gem5-decode` rc=0；273 例 md5 不变；**可达 FAIL 注入**（去掉检查 ⇒ 该例不再 ILLI）。

## 纪律

- 重建 QEMU 前申报耗时；`JOBS=8`；不占 207/208
- 注入还原 `cp`+md5+`touch`（`cp -p` 假绿坑）
- 不 commit/push、不改台账；状态改 `待验收`
- 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查对象：`exec/b1.cc` 静态检查段、`exec/b1_test.cc` 新增/改写用例、`check_converge.py` 冻结基线。

- **位置**：新检查在 `count == 0` / `dst + count > 64` 之后、EA 计算与任何 `readInt/readMem` 之前；实测用例断言“无访存、无寄存器写”，即 ILLI 先于 MALIGN/访存。
- **同组性**：RD 形式比较索引 `offValue`（`rdhc`，RD 组）、RB 形式比较基址 `base`（`rbhb`，RB 组）；RA/RF 形式不比较（结构性不适用），有用例正证。
- **`stm` 不加检查**：实现只在 `Access::Load` 下生效；用例证明 `stm` RD/RB 重叠正常且三元素地址全取原始 `rdhc`。
- **边界**：`rdhc == dst+count-1` 属块内、`== dst+count` 合法；逐 id 规则消费覆盖 8 条 `ldm`（7 RD + 1 RB）。
- **防恒真**：初稿 group 2a 的 `ctx.rb[20] == before` 是自证恒真 ⇒ 改成显式期望值。
- **既有用例冲突**：`1+63 == 64 合法` 在新规则下地址寄存器必落块内 ⇒ 改块 `[1..62]` + 地址寄存器 `= 63`；`ldm 重叠按原值` 语义已反转 ⇒ 换成 `stm` 同型用例。
- **注入核对**：`Load→Store` 后 18 条红（8 条规则 + RD/RB 块内外 + 被误拒的 stm 用例），还原 md5 一致后回绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 初稿 group 2a 断言恒真 | ✅已修 | 改显式期望 rb19/20/21 | `ldm RB rbhb in block: no register written` PASS |
| 既有 `1+63` 边界用例被连带判红 | ✅已修 | 块 `[1..62]`、地址寄存器 63 | `check_b1` 2156 PASS / 0 FAIL |
| 既有 `ldm 重叠按原值` 用例与裁定冲突 | ✅已修 | 改 `stm` RD/RB 重叠 + `ldm` RA/RF 不适用 | 三组例全绿 |
| 解码表相对 `contracts/` 已 stale | ✅已修 | 重生成 `decode_table.inc`/`decode_assertions.inc`/`decode-assertions.tsv` | `gen_decode_table --check` rc=0 |

### 第 1 轮 reviewer 验收（独立重跑）

**判决：Accepted**（三项单独答复见末尾）

**重跑记录（全部本人执行，退出码如注，原始输出落 `/tmp/opencode/m13-gem5-008-review/`）**
- `./.work/evidence/m13-gem5-008/run.sh --inject` → `RUNSH_EXIT=0`、`PASS=28 FAIL=0`：`check_b1` rc=0（`[PASS] 2156 / [FAIL] 0`、`B1 coverage 38/38, cases 38, failures 0`）、`check-gem5-decode` rc=0（264/264、388/388、28/28、2/2、failures 0）、`check_b7` rc=0、sweep `covered=273 md5=2d4d94651346ef673c5a855e024c1489`；注入 `Load→Store` ⇒ rc=1、`[FAIL] 18`（ldm 组例 4 条）⇒ `cp`+`touch` 还原 md5 `6ab38737…` 一致、组件树干净、回绿 rc=0。
- 单跑复核：`make check-gem5-decode` rc=0；`make build-gem5` rc=0（scons `gem5.opt is up to date`，内容判据未触发重建 ⇒ 产物即当前源）；`make check-source-state` rc=0（gem5 `OK HEAD=a9990227d057 count=1 clean=True`）；`make check-component-changelog` rc=0；`make check-patch-tree` rc=2（2 条全属 qemu，gem5 0）；`check_converge.py` rc=1（红 3 项 = `gen_converge_words` 3 id + b6 1384/1362 + b7 3066/2979；本任务只改 b1 基线键 ⇒ 先于本任务，与完成区披露一致）。
- 三组例亲见 `[PASS]`：ldm RD `Illegal`+`no memory read`+`no register written`、`rdhc==22 → None` 且 rd19/20/21=0x8081…；ldm RB 同型；`stm RD/RB overlap → None`（地址全取原始 rdhc、大端正确、寄存器不变）；`ldm RA/RF → None`；规则由解码表驱动：`rule mreg_range_addr_overlap` 8 id ×3 = 24 条全 `[PASS]`。
- **reviewer 独立探针**（`probe008.cc`，24 项全 PASS、rc=0）：`rdhc==rdHA`⇒Illegal（0 访存/0 写）、`rdhc==21`（末元素）⇒Illegal、`rdhc==rdHA+immu6`⇒None 且 3 元素大端正确、`rbhb==rbHA`⇒Illegal / `==+immu6`⇒None、`stm` RD/RB `==dst` 重叠⇒None+地址与数据正确、`ldm` RA/RF `rdhc==19`⇒None。**探针反例**：临时副本注入 `Load→Store` ⇒ 探针 9 项 FAIL（rc=1），交付树未动。
- **我方注入（RD/RB 检查对调）**：`check_b1` rc=1、`[FAIL] 15` ⇒ `cp`+md5+`touch` 还原（md5 `6ab38737…` 一致、组件 `git status` 0 行）⇒ rc=0、2156 PASS。

**约束核验**：检查在 `b1.cc` 静态段（`count==0`/`dst+count>64` 之后、EA 计算与首个 `ctx.readInt`/`readMem`/`writeDestination` 之前，不在元素循环内）✅；RD 查 `offValue=rdhc`、RB 查 `base=rbhb`（与 `kSpecs` 字段、spec §1/§2 同组口径一致，两向未搞反）✅；`stm` 由 `Access::Load` 门限、RA/RF 无分支 ✅；解码表 8 条 ldm（7 RD+1 RB）rule+legality、`stm` 0 条、`ldm.t_rrri_rf`/RA/RF 未动 ✅；基线 2102→2156 为上调（覆盖只增不减；`1+63`→`1+62` 的等价边界仍由 `62+2==64` 用例覆盖）✅；8 文件对账（7 实现文件 + 任务书）✅；完成区 7 行、本轮 40 行内 ✅；未 commit、未改台账，验收前后 `git status -uall` 与 6 个目标文件 md5 逐项一致 ✅。

**findings（文档级，不阻断，交 architect 收尾改）**：① 完成区写「与 `git status -uall` 7 项对上」，实际 8 项（含任务书自身）；② 完成区 `check-source-state` gem5 记 `HEAD=f5e3a00c`，实测 `HEAD=a9990227d057`；③ `check-patch-tree` 记 rc=1，`make` 实测 rc=2；④ 任务书「范围（只改 QEMU）」与验收「`check-inst`」是 QEMU 孪生任务（m13-qemu-006）的模板文案 —— 本任务为 gem5 侧，**我未跑 `check-inst`**（QEMU 侧 L3 全量门控，且与并行 qemu 任务共用构建树），建议改文后再定其归属。

**① 检查位置与 RD/RB 字段**：正确 —— 静态段、先于任何访存/写寄存器；RD=`rdhc` 对 `rdha`、RB=`rbhb` 对 `rbha`，与 spec §1/§2 同组口径一致，独立探针双向验证。
**② `stm` 允许、RA/RF 不适用**：实测成立 —— engineer 三组例 + 我方探针各自跑通（`stm` RD/RB `==dst` 重叠 ⇒ None 且地址取原始值、数据正确；`ldm` RA/RF `rdhc` 数值落块内 ⇒ None 且元素正确）。
**③ 解码表与基线**：合理 —— 规则/合法性文本源自 `contracts/legality_rules.yaml`+`opcodes.yaml`（m13-spec-005 已合入），`gen_decode_table --check` rc=0，8 ldm/0 stm 与 spec 附录逐条一致；基线为覆盖增加后的只增上调，非凑绿。

## 完成区

**测试结果**：`run.sh --inject` PASS=28 FAIL=0（`RUNSH_EXIT=0`）。三组例：`ldm` RD `rdhc=20∈[19,22)` ⇒ ILLI（0 访存、0 写寄存器）、`rdhc=22` 边界 ⇒ None 且 3 元素正确；`ldm` RB `rbhb=20` ⇒ ILLI、`rbhb=22` ⇒ None；`stm` RD/RB 重叠 ⇒ None 且地址全取原始 `rdhc`；`ldm` RA/RF ⇒ None（不适用）。`check_b1` 38/38、cases 38、failures 0（[PASS] 2156，基线 2102→2156）；`check_b7` rc=0；`make check-gem5-decode` rc=0（264/264、388/388、28/28、2/2、failures 0）；`make build-gem5` rc=0；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489` 不变。
**修改文件**：`components/gem5/patches/src/arch/dadao/exec/b1.cc.patch`、`.../exec/b1_test.cc.patch`、`.../decode/decode_table.inc.patch`、`.../decode/decode_assertions.inc.patch`、`components/gem5/decode-assertions.tsv`、`components/gem5/changelog.md`、`tools/gem5/check_converge.py`（b1 冻结基线上调）——与 `git status -uall` 7 项逐一对上。
**验收结果**：注入 `Access::Load → Access::Store` ⇒ `git diff --name-only` 非空、`check_b1` rc=1 且 18 条 `[FAIL]`（4 条属 ldm 组例）；`cp` 还原 + `touch` 后 md5 `6ab387371ad9e9a768219a2184674372` 一致、组件工作树干净、`check_b1` 回绿（rc=0）。`check-source-state` gem5 `OK HEAD=f5e3a00c count=1 clean=True`；`check-component-changelog` PASS。
**新发现/坑**：① `m13-spec-005` 合入契约后 gem5 解码表即 stale（`gen_decode_table --check` 原本红），本任务必须重生成，否则 `check_b1` 的 rule/legality “known” 断言 16 红；② 任务书「用户裁定」段写作「`ldm`/`stm` … 不得落入」，与 spec 定稿（`stm` 不加检查）及本任务「范围」第 1 条冲突，实现按 spec 与派单口径（只查 `ldm`），建议 architect 修文；③ 既有 `ldm` 重叠用例（“按原始值计算”）与 `1+63` 边界用例在新口径下必红，需同步改写。
**遗留问题**：`check_converge` 仍红 3 项、均先于本任务且与本任务无关：`gen_converge_words` 有 3 个 `*2fo` id 无合法字（INTEG-058t 后）、b6 冻结基线 1384/1362、b7 3066/2979（两测试在 GEM5-013t 冻结后分别被 INTEG-058t / m13-gem5-007 增补）；未改其基线以免掩盖他任务。`check-patch-tree` rc=1 的 2 条全属 qemu（`trans_mem.c.inc` 并发写者），gem5 命中 0。

#### 收尾（architect，2026-11-13 08:31）

- reviewer **Accepted**：`run.sh --inject` 28/0；`check_b1` **2156 PASS / 0 FAIL**（B1 coverage 38/38）；`check-gem5-decode` rc=0（264/264、388/388）；`build-gem5` rc=0；273 md5 不变。
- **检查位置**：在 `b1.cc` 静态段（`count==0`/`dst+count>64` 之后、EA 计算与首个 `readInt`/`readMem`/`writeDestination` 之前）；RD 查 `offValue`(rdhc)、RB 查 `base`(rbhb)，未搞反（对调注入必红 15 条）。
- **reviewer 独立探针 24 项全 PASS**：`rdhc==rdHA`⇒Illegal（0 访存/0 写）、`==dst+immu6`⇒None 且大端正确；`stm` 重叠⇒None 且地址取原始值；`ldm` RA/RF⇒None。
- **解码表**：`decode-assertions.tsv` 恰 8 条 `ldm`（7 RD + 1 RB）带 rule+legality、`stm` 0 条；`check_converge` 基线 2102→2156 是**只增覆盖**的上调。
- 文档订正：完成区「7 项」实为 8；`check-source-state` 记的 HEAD 与实测不符（实测 `a9990227d057`）；`check-patch-tree` 记 rc=1 实为 rc=2；**任务书原模板文案「范围（只改 QEMU）」与验收里的 `check-inst` 属 QEMU 孪生任务**，已改为 gem5 侧（`check_b1`/`check-gem5-decode`）。

