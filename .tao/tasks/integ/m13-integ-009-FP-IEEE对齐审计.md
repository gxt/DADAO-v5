# m13-integ-009: FP-IEEE 对齐审计（47 条指令，等 `015` 收齐后执行）

**模块**：integ
**项目里程碑**：M13
**依赖**：`m12-chipyard-015`（FP 取整/缩放/符号收齐 47 条）+ `m13-integ-004`（riscv-tests，已合入）
**可并行分片**：否（跨模块审计，单写者）
**状态**：已验证

## 背景

用户 2026-11-12 定规则（`.tao/knowledge/MEMORY.md`「DADAO 反套用清单」末条）：

> 浮点设计与实现过程中出现的差分问题，都以 **IEEE-754 2019** 规定的行为为准；`SimRISC` 指令系统与各模拟器都应以此更新和修订。

已知的第一处冲突是 `fo2ft` 溢出（`ISS-397`），已拆成 5 个子任务（`m13-spec-002` / `m12-chipyard-025` / `m13-qemu-005` / `m13-gem5-007` / `m13-testcases-011`）。但**这条规则适用于全部 FP 语义**，需要一次系统审计。

## 目标

对 **66 条 `scope: fp` 指令**（`contracts/fp_semantics.yaml`，与 `contract-fp` 一致）逐条产出审计表；**按 spec 附录 A 的 52 行排版呈现**（其余 14 行填「IEEE 未规定」）；「47」不复用（任何机器可读源都复现不出，`ISS-409`），每行给出：

| 列 | 内容 |
|---|---|
| 指令 | 助记符 |
| IEEE 条文 | 754-2019 的具体章节（如 §5.4.1 舍入方向、§7.4 溢出、§7.5 下溢、§5.11 谓词） |
| 当前实现 | chipyard / QEMU / gem5 各自行为（三列或合并） |
| 结论 | 一致 / 偏离 / IEEE 未规定（实现自由） |
| 动作 | 不改 / 改 spec 措辞 / 改实现 / 立子任务 |
| 影响面 | 涉及模块与既有任务号 |

至少覆盖这几类高风险点（已知候选见 `ISS-397`）：

1. 舍入方向与溢出/下溢结果（`fo2ft` 已确认冲突）
2. 谓词（quiet vs signaling）遇 NaN/Inf 的 `NV` 语义（`qemu-004`/`chipyard-024` 已处理一部分）
3. sNaN 结果 payload 与 NaN 符号位（IEEE 未强制 ⇒ 需在 spec 写明取值）
4. 取整/缩放类（`rnd`/`sclb`）的舍入模式与边界
5. 转换类（`f2i`/`i2f`）的饱和与 `NV`/`NX` 组合
6. `rf0` 只读位（`ld.t rf0`）这类**测试机约定**，需标为架构附加而非 IEEE 行为

## 验收标准

1. 审计表**逐条覆盖 66 条**（现场统计 == `contracts/fp_semantics.yaml` 的 `scope: fp` 集合，漏一条即 FAIL，不得抽样）；呈现按 52 行分组
2. 每行的「IEEE 条文」可核对（章节号 + 一句话结论），不接受「大致符合」
3. 偏离项**全部**有后续动作：已立册的写任务号，未立册的写「需立册 + 建议归属（模块/里程碑）」，由 architect 转立
4. 审计表落 `docs/TestReports/M13-FP-IEEE对齐审计.md`（人读结论）+ 原始表落运行期目录
5. 一键证据脚本（含可达 FAIL：漏一条指令 ⇒ 必须 FAIL）
6. 完成区 ≤30 行、无运行期路径

## 说明

- **等 `015` 完成后再派**：47 条 FP 指令全部落地后审一次，避免审两遍。
- 本任务**只审计 + 立册建议**，不直接改实现；改实现按子任务走。
- `.work` 必须软链（`ISS-389`）。
- 若审计中发现 IEEE 与 `spec/` 冲突且**需要用户裁定**（例如「保留偏离 vs 改实现」），写进任务书「待裁定」段返回主会话，不自行决定。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 待裁定（`m13-integ-009`）

**R1 `rootn(±0,2)` 取向**（审计 D2）：三实现均返回 `−0`（= `squareRoot(−0)`），IEEE 754-2019 §9.2.1 规定偶数 `n>0` 时 `rootn(±0,n) = +0`；`spec §2.2` 明文「不做具体要求」但未标注为有意偏离、未给理由。

- 选项：① 收严为 IEEE `+0`（改 RTL/QEMU/gem5 + 向量）；② 保留 `−0`，在 spec 明文写「有意偏离 + 理由」。
- 建议：①（用户规则是「一律以 IEEE 裁决」，且改动面仅 3 处 + 1 组向量）；若倾向保留，则必须补理由（例如「沿用 sqrt 实现，避免为 n=2 单开特例」）。
- 临时处置：审计表 `foroot`/`ftroot` 记「偏离」，动作记「改 spec 措辞 + 需立册（待裁定）」，未改任何实现。

**R2 NaN 结果 payload / 符号位统一取值**（审计 D3）：IEEE §6.2.3 未规定，三实现互不一致（RTL 传首 NaN payload、符号清 0；QEMU 传首 NaN payload+符号；gem5 一律 canonical）。属 `contract-fp` 语义冻结段落的变更。

- 选项：① 统一为 canonical qNaN（符号 0、payload 全零；改动最小，gem5 不动，收 RTL/QEMU）；② 统一为「传播首个 NaN 的 payload 与符号」（改动 gem5 + RTL 两处）。
- 建议：①（与 `§18/§19/§20` 已采用的 canonical 口径一致，且与 `rf0` 的只读 qNaN 位同源）。
- 临时处置：审计表记「NaN 见 D3」+ 建议立册，未改任何实现/契约。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

范围：`tools/spec/check_fp_ieee_audit.py`、`run.sh`（运行期证据脚本）、审计册、`docs/README.md` 索引行。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 4b 校验把表 B「IEEE 无对应」判红（规则过严） | ✅已修 | 仅当 `结论=IEEE 未规定` 时允许「无对应」，其余仍强制 `§<数字>` | 门控 4b PASS |
| 反例 B 只被摘要计数抓到，行级「一致却要改实现」未被判红 | ✅已修 | 新增 5b：一致/未规定 ⇒ 不得含「改实现」；偏离 ⇒ 须有改实现/改 spec 措辞 | 注入 B 现同时触发 5b+6a |
| `--raw` 首次输出 0 行（表内首列带反引号，键不匹配） | ✅已修 | `by_id` 键做 `strip("`")` | `--raw` 现 66 行（== 合同条数，现场比对） |
| 审计册含具体 `.work/**` 路径 + 册头缺「机器指纹」 | ✅已修 | 改 `run.sh` 占位形；册头补「机器指纹」 | `check-test-reports.py` PASS |
| D3 对 QEMU 转换类 payload 的描述不准确（softfloat 是右移丢弃，非 OR） | ✅已修 | 按 `parts_uncanon` 实读改「右移丢失（移空置 quiet 位）」 | 复读 softfloat 代码 |
| P13 把 RTL FMA 溢出写成「实现待 029」，实际 029 是实测确认任务 | ✅已修 | 改「待 `m12-chipyard-029` 实测，不据他平台推定」 | 册内 3 处一致 |
| 证据脚本 `record` 期望写成「非 0」与实际「非0」比较 ⇒ 首轮假红 rc=1 | ✅已修 | 统一为「非0」 | 脚本 `ALL PASS`，rc=0 |
| 完成区写「门控 18/18」而现场为 19 项（写死计数漂移） | ✅已修 | 改为现场统计 `${n}/${n}` 的实跑值 19/19 | `grep -c '^\[PASS\]'` = 19 |
| 「一致」列主要依据静态读码（QEMU/chipyard 无 FP 运行时差分） | ⏸延后 | 册头「证据强度」+ §8 已披露；待 `m13-integ-002` 恢复后复核 | 无（依赖外部任务状态） |

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑（worktree 内，全部本人实跑，不信完成区转述）**：
- `python3 tools/spec/check_fp_ieee_audit.py` → **rc=0**，19 项 `[PASS]`；`summary: 合同 66 条 / 附录 A 52 行 / 表 A 52 + 表 B 14；一致 48、IEEE 未规定 14、偏离 4；failures 0`。
- `bash .work/evidence/<任务ID>/run.sh` → **rc=0，`ALL PASS`**：反例 A（删 `ut2ft` 行）⇒ `[FAIL] 2b 期望 52 / 实际 51`（2b/2c/3c/6a 红）、反例 B（`ftqcmp` 偏离→一致）⇒ `[FAIL] 5b ['ftqcmp'(一致 却要改实现)]`（5b/6a 红）；两例 `cp` 还原 md5 `6c35dc2632832961…` 相等、回绿 rc=0。
- **独立覆盖统计（现场数，不采信 66）**：`fp_semantics.yaml`（顶层 `scope: fp`）66 条无重复；`opcodes.yaml` scope 含 fp 66 个，双向差=[]；表 A 52 行与 `SimRISC-07` 附录 A **同序同集**；表 B 14 条 id == 合同−附录A（集合相等）；A∪B 覆盖 **66/66**（缺=[] 多=[]）；偏离 4 行 = `foqcmp/foroot/ftqcmp/ftroot`；结论 48/14/4。
- **IEEE 条文抽检 16 处**（下载 754-2019 官方 PDF 84 页，`pdftotext` 逐条比对原文）：§4.3、§5.3.1（remainder 平局取偶/恒精确/r=0 取 x 符号）、§5.3.3（scaleB 精确积单次舍入）、§5.4.1、§5.4.2（NOTE：同格式 convertFormat canonical 化 vs copy）、§5.5.1、§5.6.1、§5.7.2（10 类逐字吻合）、§5.8、§5.9、§5.11（quiet 仅 sNaN ⇒ invalid，原文逐字）、§6.2/§6.2.3、§6.3（RDN ⇒ −0 逐字吻合）、§7.2f、§7.3、§7.4（方向 a–d + OF|NX 逐字吻合）、§7.5、§9.2.1（`rootn(±0, 偶数 n>0) = +0` + NOTE `rootn(−0,2)≠squareRoot(−0)`）、§9.6 —— 章节号真实、一句话结论与原文一致。
- **D1**：读码三边核实 —— RTL `Mux(io.signaling, unordered, isSigNaN(a) || isSigNaN(b))`、QEMU `nv_rule==FP_CMP_NV_SNAN ? is_snan(a)||is_snan(b) : unord`、gem5 `runCompare` quiet 分支不置 flags；探针复跑 `b7test --vectors`：`qcmp_snan_vs_num`/`qcmp_num_vs_snan` FCSR=`0x7ff800007fc00000`（低 5 位 0）、`scmp_qnan`=`…0001`；`arith.yaml` 4 例期望 `rd6=…0001`；裁定原文在 `discussing.md` 2026-11-12「改为置 NV（跟 IEEE）」；`SimRISC-07 §4`/`contract-fp §8` 确无 NV 条款。
- **D2**：`SimRISC-07 §2.2`「不做具体要求」逐字在；RTL 注释 `-0 is returned`、QEMU `helper_fp_root = float64_sqrt`、gem5 `rootn(-0,2) model: -0`，探针 `foroot_negzero = 0x8000000000000000` —— 三实现 `−0`、IEEE `+0` 属实。
- **D3**：§6.2.3 payload 为 should（多 NaN「does not specify which」）、§6.3「does not specify the sign bit of a NaN result」支撑「未规定」；探针 `ftadd/ftsclb(0x7FC12345,…)→0x7FC00000`、`fo2ft(0xFFF8…0123)→0xFFC00000`；QEMU `float_2nan_prop_ab`、RTL「First NaN wins…OR-ed into last payload bit」读码相符。
- **门控**：`check-test-reports` rc=0、`check-fp-contract` rc=0、`check_asm_list_consistency.py` rc=0（12 spec OK）、`make check-tasks` rc=0；`check-knowledge-refs` rc=2（5 条全是 `m13-testcases-013`）、`check-run-artifacts` rc=2（17 problems，0 条涉及本任务）⇒ 既有基线，与完成区声明相符。
- **独立反例注入（自设计，非 engineer 两例）**：表 B `ld.t_rrii_rf`→`ld.t_rrii_xf` ⇒ `[FAIL] 3b 缺=['ld.t_rrii_rf'] 多=['ld.t_rrii_xf']` **rc=1**；`cp` 备份还原、md5 `6c35dc26…` 前后相等 ⇒ **rc=0 回绿**（未用 checkout/restore/stash）。
- **快照对账**：验收前后 `git status --porcelain -uall` 均为空、审计册 md5 `6c35dc26…` 前后相等；`git show --stat 9e838503` 4 文件 == 完成区「修改文件」。

**约束核验**：未动 `tests/inst/`、组件源树（commit 仅任务书/审计册/门控脚本/`docs/README.md`）；完成区 18 行 ≤30；无绝对运行期路径（仅 `<任务ID>`/`<>` 占位）；R1/R2 待裁定已落盘、未改实现/契约；证据脚本逐条有可达 FAIL（脚本审读 + 双反例复跑 + 独立注入三重证实）。

**findings（文档级，按 §6.5 不阻断，architect 收尾改）**：F1 完成区所贴 run.sh md5 `808db48b…` 取自 13:37 旧版运行，最终产物为 `6c35dc26…`（13:39 `evidence-final.log` 与我重跑一致，FAIL/PASS 行逐字相符）；F2 完成区「check-run-artifacts 18 条 node-bootstrap」实跑为 17（15 node-bootstrap + 2 `reviewer-check-*`）；F3 册头「`check_b7.py --vectors`」参数名有误（`--vectors` 属其编译出的 harness）；F4 立册建议 `m13-gem5-010` 与**已验证**的 `m13-gem5-010-hmon测试fixture迁移` 冲突，转立时须换号（`m13-integ-010`/`m13-spec-007` 空闲）；F5 §6 索引「轻微溢出只置 NX」是 §7.4 iff 判据的推论（标准无此原文，与 spec §1.4 同口径），建议标「推论」；F6 建议册内补注 §6.2/§6.2.3 的「shall be canonical」句（binary 格式按 §3.4 不构成 payload 强制，D3 结论不变）。

**判决：Accepted** —— 验收命令块在本人重跑下全部通过、66/66 覆盖与三偏离独立复核属实、约束无违反。状态保持 `待验收`，由主会话置 `已验证`。

## 完成区

**测试结果**：审计册门控 19/19 通过（rc=0）；覆盖 **66/66**（表 A 52 + 表 B 14，计数全部现场统计，未写死）；注入 2 例（漏一条指令 / 偏离改一致）均 rc≠0，`cp`+md5 还原后回绿。
**修改文件**：`docs/TestReports/M13-FP-IEEE对齐审计.md`（新）、`tools/spec/check_fp_ieee_audit.py`（新）、`docs/README.md`（索引 +1 行）、本任务书（待裁定/审阅记录/完成区/状态）；运行期不入库：证据脚本 `.work/evidence/<任务ID>/run.sh`、逐条表 `.work/log/integ/<任务ID>-audit-raw.txt`。
**验收结果**：
```
$ python3 tools/spec/check_fp_ieee_audit.py
summary: 合同 66 条 / 附录 A 52 行 / 表 A 52 + 表 B 14；一致 48、IEEE 未规定 14、偏离 4；failures 0   (rc=0)
$ bash .work/evidence/<任务ID>/run.sh
[FAIL] 2b 表 A 行数 == 附录 A: 期望 52 / 实际 51        ← 注入 A（删 ut2ft 行）
[PASS] 反例 A 还原 md5: 期望 808db48b810fbf94… / 实际 808db48b810fbf94…
[FAIL] 5b 结论↔动作自洽: ['`ftqcmp`(一致 却要改实现)']  ← 注入 B（偏离→一致）
[PASS] 反例 B 还原 md5: 期望 808db48b810fbf94… / 实际 808db48b810fbf94…
==== 总结：ALL PASS ====    (rc=0)
```
门控：`check-test-reports` PASS、`check-tasks` rc=0、`check-fp-contract` PASS、`check-asm-list-consistency` PASS；`check-knowledge-refs`（5 处 `m13-testcases-013` 的具体 `.work` 引用）与 `check-run-artifacts`（18 条 `node-bootstrap` 日志命名）**在 master 上同样红**（已实跑复现）⇒ 既有基线，非本任务引入。
**git status**：`?? docs/TestReports/M13-FP-IEEE对齐审计.md`、`?? tools/spec/check_fp_ieee_audit.py`、`M docs/README.md`、`M` 本册 == 上「修改文件」（无其它残留）。
**新发现/坑**：① gem5 quiet compare 遇 sNaN **不置 NV**（运行期实测，IEEE §5.11/用户在 2026-11-12 裁定均要求置）；② `rootn(−0,2)` 三实现均 `−0`，IEEE §9.2.1 为 `+0`；③ NaN payload/符号三实现三种口径（IEEE 未规定 ⇒ 差分恒红）；④ 计数注释漂移（`fp_semantics.yaml` 写 `cs_rf(5)` 实为 3；QEMU 头注释写 60/cs(5) 实为 66/3）；⑤ RTL 注释把 scaleB 记为 §9.2，实为 §5.3.3。建议沉淀：静态读码得结论须标「证据强度」；三平台 NaN 口径不统一会让 FP 差分永红。
**遗留问题**：R1（`rootn(±0,2)` 取向）、R2（NaN 口径）见「待裁定」，未改实现/契约；`m13-integ-002` 停摆 ⇒ FP 三平台运行时差分仍缺，本册「一致」列待其复核；F2/F3 注释漂移未修（建议随子任务顺手改）。
