# m12-chipyard-027: `ldm`/`stm` 基址/索引重叠 ⇒ ILLI（RTL）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-005`（spec 定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 用户裁定

**`ldm`** 的基址/索引寄存器**不得**落在被传送的寄存器范围内 ⇒ 违反 ⇒ **ILLI**；**`stm` 允许**（只读传送范围、不写寄存器）；RA/RF 不适用（用户 2026-11-13 三轮收敛口径，见 `m13-spec-005`）。

## 范围（只改 chipyard RTL）

1. `components/chipyard/patches/.../WumingDecoder.scala.patch` 的 `ldm`/`stm` 译码加检查（与既有 `mreg_range_overflow` 同位置，`d.ill := true.B`）：
   - **只检查 `ldm`**：RD 形式 `rdHC ∈ [rdHA, rdHA+immu6)` ⇒ 非法；RB 形式 `rbHB ∈ [rbHA, rbHA+immu6)` ⇒ 非法
   - **`stm` 不加检查**（允许重叠：只读传送范围、不写寄存器）
   - **RA/RF 形式：不适用**（范围在 RA/RF bank，基址/索引分别在 RB/RD）
2. 检查必须在**任何元素处理之前**（与既有的 `immu6=0`/范围检查同位置）。
3. 不改其它语义。

## 验收

构造 3 组例：`ldm` RD（7 条中至少 1 条）、`ldm` RB（应 ILLI）；`stm` RD/RB 重叠（应正常执行）：
- 地址寄存器落在范围内 ⇒ **ILLI**（且不发访存、不写任何寄存器）
- 地址寄存器在范围外一位（边界）⇒ 正常执行且元素值正确
- `stm` 重叠 ⇒ 正常执行、数据正确、地址取指令开始时的原始值
- RA/RF 形式（数值落在块内）⇒ 正常执行（结构上不适用）

门控：`check-patch-tree`（chipyard 子集）rc=0、`check-source-state` rc=0、`apply-series` 幂等、elab + Verilator 构建 rc=0 且 `%Error`=0、`check_b6`/解码断言（若涉及）rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；**可达 FAIL 注入**（去掉检查 ⇒ 该例不再 ILLI）。

## 纪律

- 补丁走 `make_patch`；`JOBS=8`；不占 207/208
- 注入还原 `cp`+md5+`touch`（`cp -p` 假绿坑）
- 不 commit/push、不改台账；状态改 `待验收`
- 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 审阅记录

### 第 1 轮 engineer 自审

改动：`WumingDecoder.scala` 的 `multiMem` 在既有 `mreg_zero`/`mreg_range_overflow` 之后加 `when(isLoad)` 分支，RD 形式判 `hc ∈ [ha, ha+hd)`、RB 形式判 `hb ∈ [ha, ha+hd)`；`stm` 由 `isLoad` 豁免，RA/RF 由 bank 条件豁免。逐行对照 spec §1/§2 与 `contracts/legality_rules.yaml`：边界 `ha` 含、`ha+immu6` 不含；`ha+hd>64` 已被前一条规则判 ILLI，此条用 `+&` 不会引入错误环绕；`hd=0` 时范围为空不触发（与前条一致）。`execFault` 已把 `d.ill` 挡在访存与写回之前（core 侧已核）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 探针镜像缺 print/exit 尾巴，程序跑出镜像（trace 连续 `cause=0x200`） | ✅已修 | `gen_probe` 统一追加 `tail(len(expect))` | 14/14 探针 rc=0 且字节比对通过 |
| 传送范围首版用 rd10–rd13，被 hmon 处理器改写（实测 dump 出 1/3） | ✅已修 | 范围改到 rd18–rd21 / rb18–rb21 / rf18–rf21（`tools/chipyard/excp/app.S`：hmon 污染 rd6–rd14） | 6 个 ILLI 探针 dump 全等于预期原值 |
| `ldm.t` RF 探针的内存播种按 `zip(tetra, tetra[1:])` 配对，元素错位 | ✅已修 | 改为按 8 字节字装两个 tetra（步长 4） | E2 探针字节比对通过 |
| `run.sh` 段选择把 `ONLY=ac` 当逗号列表、缺日志目录、worktree 无工具链软链 | ✅已修 | 改子串匹配、`mkdir -p`、补 `.dadao` 软链（gitignore 内） | 各段 rc=0、37 PASS / 0 FAIL |
| 只按 md5 判"已还原"不足以排除"空注入" | ✅已修 | 追加"注入后组件源树 diff 非空"与"还原后 blob == base+1 commit blob"两条 | 注入段 2 条 PASS、还原段 blob 相等 |

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑记录**（worktree HEAD `526a6e04`、组件源树 `06dcf16`；以下全部本人亲跑）
- `bash .work/evidence/m12-chipyard-027/run.sh` ⇒ **RC=0，PASS=21 FAIL=0**：`check-patch-tree: 9 patch set(s), 333 patches OK`；`check-source-state: chipyard: OK HEAD=06dcf16 count=1 clean=True`；`apply-series` 幂等且 commit 仍 `06dcf16`；`check-component-changelog: PASS`；补丁含 `hc >= ha && hc < (ha +& hd)`、`hb >= ha && hb < (ha +& hd)`、`when(isLoad)` 守卫计数=1；源树 0 行；elab/Verilator rc=0 `%Error`=0；`probes=14 failed=0`；273 例三处 md5 均 `2d4d94651346ef673c5a855e024c1489` 且 `cmp` 字节相等。
- 探针日志亲读：A1–A4、B1×2 → `excp cause=0x100`（`cause_ip`=该 ldm、`info`=指令字 `0x28483484`/`0x28483504`）、`kind=2|3`=0、`cfxmem=0`；A3/B1-unmapped 仅 `0x1`(CFXTRAP)、**无** `0x2`；C/D/E 各 1 条 `kind=2/3 count=4`（D1 `addr=0xffffff012100` = ENTRY+0x2000 = 原 rd20），14 例字节比对全过。
- `bash run.sh --inject` ⇒ **RC=0，PASS=16 FAIL=0**：6/6 红（mapped `memop=1` 无 ILLI、unmapped 转 `0x2`）；还原 md5 `37444f17…`==注入前、blob `36ff5500…`==HEAD blob、源树 0 行、14/14 回绿；inject/restore 均真编译（elab 94KB / verilator 199KB、`%Error`=0，非 "Nothing to be done"）。
- **reviewer 独立注入**（与 engineer 不同）：`hc >= ha`→`hc > ha`（开下界）⇒ `ONLY=bc bash run.sh` ⇒ **RC=1，PASS=6 FAIL=1**，仅 `A1-ldm.ub-rd-index-at-start` 红（无 ILLI、`memop=1`、字节不符）⇒ `cp`+md5+`touch` 还原（md5 `37444f17…` 相等、blob==HEAD blob、源树 0 行）⇒ 重建 **RC=0，PASS=7 FAIL=0**（14/14 回绿）。
- `make -s check-modules` ⇒ **RC=0**，`module checks (L2): PASS`（inst/arch/unit/tset×3/generator-sync 全 PASS，日志 `failed=0`）。

**约束核验**：① 只改 RTL+补丁：HEAD 仅 2 文件（任务书+补丁）、master（`23796159`）无本改动、三处工作树均 0 行、未 commit/push/改台账；② 检查位于 `multiMem` 静态译码段（`mreg_zero`/`mreg_range_overflow` 之后、`when(isLoad)` 内），消费侧 `execFault` 在 `sExec` 的 when 链优先于 `state := sMreq`、`memop` printf 由 `!execFault` 门控 ⇒ 静态、先于任何元素处理；③ 字段未反：RD 用 `hc`、RB 用 `hb`，`isLoad && bank∈{RD,RB}` 恰 8 条（opc 0x28–0x2D、0x38、0x3A）与 `legality_rules.yaml`「共 8 条」一致；④ `stm` 豁免、RA/RF 豁免、三边界（`rdhc==rdha`、`rdhc==rdha+immu6`、`rdhc==rdha-1`，另 `rbhb==rbha+immu6`）实测成立；⑤ 补丁可复现：apply-series 幂等、源树==base+1+补丁；⑥ 注入可达 FAIL：engineer 与 reviewer 各一次、均还原回绿；⑦ 完成区 14 行（≤30）、无运行期绝对路径。

**跨平台口径（逐条对照，无不一致）**：QEMU `mreg_addr_in_range = addr>=start && addr<start+len`，8 个调用点全在 `trans_ldm_*`（7×`hc` + 1×`hb`），`trans_stm_*` 无；gem5 `decode-assertions.tsv` 恰 8 行 `rdhc<rdha || rdhc>=rdha+immu6` / `rbhb<rbha || rbhb>=rbha+immu6`（stm/ra/rf 行均无），`b1_test.cc` 组 1a/1b/2a/2b/3a 与本任务探针同构；chipyard `hc>=ha && hc<(ha+&hd)`。三家同为**半开区间、仅 ldm、8 条、字段一致、静态判**；`immu6=0`/`ha=0`/`ha+hd>64` 三家同判 ILLI（`+&` 与 unsigned 均不环绕）。

**Finding（文档级，不阻断）**：① 完成区括注「门控9+构建4+探针3+14例+273回归5」与 `PASS=21` 不自洽（14 例是探针段内逐条输出，实为 9+4+3+5=21）；② 「ldm.o RA / ldm.t RF：`hb=hc=20`」对 E1 不准——E1 是 `hb=20,hc=2`，E2 才 `hb=hc=20`；RA 形式未测「hc 数值落块内」组合（读码 `bank===RD/RB` 可证豁免）；③ `components/chipyard/{README,changelog}.md` 未列新规则（engineer 已披露为遗留）。建议 architect 收尾改措辞/补文档。

**判决：Accepted**（验收命令块本人重跑全绿、硬约束无违反、两次反例注入均证可达 FAIL 并已还原；architect 终审）

## 完成区

**测试结果**：证据脚本 `run.sh` PASS=21 FAIL=0（门控 9 + 构建 4 + 探针段 3 + 273 回归 5；14 例是探针段内逐条输出，不另计）；`run.sh --inject` PASS=16 FAIL=0（注入 6/6 变红、还原 14/14 回绿）；L2 `make check-modules` rc=0
**修改文件**：
- `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingDecoder.scala.patch`（`make_patch chipyard` 导出，唯一入库改动；组件源树内同文件的 `multiMem` 加范围检查 + 头注释补 `mreg_range_addr_overlap`）
**验收结果**：
- ldm RD：`rdhc==rdha`（下边界）与 `rdhc=rdha+2`（范围内，`ldm.ub`/`ldm.o`）⇒ ILLI；dump 的 rd18..rd21 与 EA 处 8 字节均为原值，trace **无** `memop kind=2`；EA 未映射例只报 ILLI、不报 CFXMEM
- ldm RB：`rbhb=rbha+2` ⇒ ILLI（mapped/unmapped 同证），rb18..rb21 与内存不变、无 `memop kind=3`
- 边界正常：`rdhc==rdha+immu6`、`rdhc==rdha-1`、`rbhb==rbha+immu6` ⇒ 正常；元素值 0x7F/0x80/0x00/0xFF（ldm.ub）与符号扩展 0xFFFF…80 / 0xFFFF…FF（ldm.sb）逐字节相等
- stm 重叠正常：`stm.b` 存 11 22 00 44（rd20 低位 0x00；EA 取原值 D=ENTRY+0x2000）、`stm.o` 四个 octa 落位，寄存器全不变
- ldm.o RA / ldm.t RF：`hb=hc=20` 数值落在 [18,22) 但分属 RB/RD 组 ⇒ 正常执行（数值落入也不误判）
- 门控：elab rc=0 `%Error`=0；Verilator rc=0 `%Error`=0；`check-patch-tree` / `check-source-state` / `apply-series`（未新增 commit）/ `check-component-changelog` 全 rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
- 注入：`when(isLoad)`→`when(false.B)` 后 6/6 ILLI 例 RED（mapped 例 `memop=1` 且无 ILLI；unmapped 例转 CFXMEM）⇒ `cp`+md5+`touch` 还原（blob 与 base+1 commit 相等）⇒ 重建后 14/14 回绿
- 构建耗时：elab ≈2 min；Verilator（仅 decoder 变更）≈1 min（`-j32` 增量）
**新发现/坑**：hmon 处理器污染 rd6–rd14（`tools/chipyard/excp/app.S`），探针可观察寄存器必须 ≥rd15；Tiny 的 hmon 对 ILLI 是可跳过类（`escape … +4`），故零副作用可在同一镜像内 dump；`excp cause`/`memop` 行只在 `+verbose` 下输出
**遗留问题**：`components/chipyard/README.md` / `changelog.md` 的 ldm/stm 合法性条目未列新规则（任务范围限定 RTL+补丁，未越界改文档）

#### 收尾（architect，2026-11-13 11:43）

- reviewer **Accepted**：`run.sh` RC=0 PASS=21；`--inject` RC=0 PASS=16（6/6 变红、还原 14/14 回绿）；**L2 `check-modules` RC=0**；`check-patch-tree` 9 组 333 补丁 OK、`check-source-state` chipyard clean。
- **检查位置与字段**：`multiMem` 静态段、`isLoad` 门限；RD 用 `hc` 对 `[ha, ha+hd)`、RB 用 `hb`；`stm` 与 RA/RF 结构豁免。reviewer 独立注入「开下界（`hc > ha`）」⇒ 恰 `A1-ldm.ub-rd-index-at-start` 红。
- **零副作用**：ILLI 例 dump 的寄存器与内存均为原值、trace 无 `memop kind=2|3`；EA 未映射例只报 ILLI（`0x100`）不报 CFXMEM —— 证检查在任何元素之前。
- **跨平台口径一致**：QEMU `mreg_addr_in_range`（8 个调用点：7×`hc` + 1×`hb`、`stm` 无）、gem5 静态段（`offValue`/`base`）、本任务 RTL 三者半开区间与 `stm` 豁免相同。
- **补丁可复现**：`make_patch chipyard` 仅 1 文件 1 改写/20 未变；`apply-series` 幂等、源树 clean。
- Finding ① 已订正（完成区计数括注与 `PASS=21` 对齐）；② 属测量口径，已在审阅记录保留。
- 遗留：`components/chipyard/{README,changelog}.md` 的 ldm/stm 合法性条目未列新规则（任务范围限 RTL+补丁）——登记 `ISS-421`。
\n