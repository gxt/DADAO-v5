# SPEC-094t: `check-spec-refs` 历史违规消解

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-091t`（`contract-asm.md` 会引入新引用，须一并确保零新增）
**状态**：已验证

## 目标

消解 `tools/infra/check_spec_refs.py`（standalone，**不在 `make check`**）当前的 **76 条历史违规**（`ISS-086`：18 Check1 + 58 Check2），使 M2 门槛③「引用全对齐」名副其实。本任务为该违规的**归属任务**——`SPEC-090k` 核验时由用户裁定**纳入 M2**（2026-10-04）。

## 背景与现状（实测）

- `check_spec_refs.py` 校验 `contract-*.md` 的 § 引用与来源头：
  - **Check1**：`[spec §x]` 引用是否可定位；
  - **Check2**：来源头 / 版本 / 生成投影排除名单。
- 当前实测 **76 violations（18 Check1 + 58 Check2）**，与 HEAD 基线**逐项相同**（`ISS-086`，由 `SPEC-087t` 登记）——**非某一任务引入**，是历史遗留。
- 该项**不在 `make check`**，故不阻断门控；但门槛③要求引用对齐，故纳入。

## 交付物

1. **独立复现**：`python3 tools/infra/check_spec_refs.py`，记录**完整输出**（条数 + 分类），作为改前基线。
2. **逐条分类与处置**（76 条 → 归宿，可追溯）：
   - **可机械修正**（§ 名/路径陈旧等）→ 直接改对应 `contract-*.md`；
   - **排除名单应含**（生成投影等）→ 补入 `check_spec_refs.py` 的 `_EXCLUDED_CONTRACTS`，**并与 `check_spec_drift.py` 的 `EXCLUDED_CONTRACTS` 同步**（两者失同步会致误报，见 `lessons.md §5.1`）；
   - **须 deferred**（如引用上游不存在章节）→ 在 `.tao/knowledge/issues.yaml` / 完成区**显式登记理由与归属**。
3. **结果**：`check_spec_refs.py` 的 **Check1/Check2 违规 = 0**，或全部显式登记为 deferred 且各有理由。
4. **（可选，推荐）门控化**：若消解后稳定，评估把 `check_spec_refs.py` 接入 `make check`（带反例门控）；**不接入**亦须在完成区说明理由。
5. **孪生陈旧引用（F-x1，`SPEC-033t` architect 发现，纳入本任务）**：`contracts/abi.yaml:46` 的 `spec_cite = "SimRISC-02 §函数调用; SimRISC-02 §函数返回"`——与已修的 `.tao/knowledge/contract-abi.md:209`（`SPEC-033t`）为**同语义孪生引用**，应改 **`SimRISC-06`**。注意：`check_spec_refs.py` 只审 `contract-*.md`、**不覆盖 `contracts/*.yaml`**（该引用既不在 76 条内、也无门控拦截）；一并修并评估是否补门控或登记。

## 约束

- 改 `contract-*.md` 时**不改其规范语义**（只修引用 / 来源头 / 排除名单）；**不改** `spec/` 上游正文、`contracts/`、`tests/`、`components/`、`.tao/archive/**`。
- `check_spec_drift.py` 与 `check_spec_refs.py` 的排除名单**必须同步**。
- 与 `SPEC-091t` **串行**（同改 `spec/README.md`/`Process-02` 的合约清单；若 `SPEC-091t` 先落地，本任务须含其新引用，确保零新增）。
- 临时目录 `/tmp/opencode/SPEC-094t/`；**不提交 git**；失败即停、禁自动重试。
- 完成区与真实输出逐条对齐；复杂命令输出留存 `.work/log/spec/SPEC-094t-*.log`。

## 验收标准

1. `python3 tools/infra/check_spec_refs.py` → **Check1/Check2 违规 = 0**（或全部 deferred 登记）；给**真实输出 + 退出码**。
2. **逐条分类表**（76 条 → 修正 / 排除 / deferred），供 reviewer 抽查。
3. `make check` **EXIT=0**。
4. **一键证据脚本**（`.work/evidence/SPEC-094t/`）：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；内置反例自检（注入 1 条**未登记**违规 → 预期 FAIL → 还原 → 回绿）；结尾不得用 `tee` 吞退出码。

## 完成区
**测试结果**：`python3 tools/infra/check_spec_refs.py` **改前 FAIL (76: 18 Check1 + 58 Check2)** → **改后 PASS (0 violations)，EXIT=0**（总引用 680 = 670 标题 + 10 粗体）。`make check` **EXIT=0**（lit 31/31、repository checks PASS）；`make check-spec-refs` EXIT=0。一键证据脚本默认模式 **12/12 PASS**、`--inject` 模式 **5/5 PASS**（含 **(a) 独立段落 / (b) 后置引用 / (c) 空行+list** 三条注入均 FAIL，及还原回绿、正对照）。
> **注（第 2 轮返工）**：首轮曾把 Check2 的 rule (b) 实现为「同块**任一**引用」、并把 rule (c) 覆盖到 list，经 architect 交叉复核判 Needs Revision。已收窄为 **(b) 仅同块「本行之前」引用**（去掉后置继承）与 **(c) 仅表格/引用块**（list 不参与，须逐条自带引用），并据此把新复现的行逐条补引（见「整改记录」）。

**修改文件**：
- `tools/infra/check_spec_refs.py`：Check2 由「逐行」改为「引用块作用域」判定 + 跳过节标题；新增 `line_has_cite`/`is_inheriting_child_line`/`_HEADING_RE`；rule (b) 限「同块**本行之前**引用」（前导，无后置）；rule (c) 限「**表格/引用块**继承紧邻带引用前导块」（list 不参与）。**未改** `_NORMATIVE_MARKERS`（16 个标记全保留）、**未改** Check1 解析口径、**未改** 排除名单。
- `.tao/knowledge/contract-abi.md`：:13 占位符 `[DADAO-21 §章节名]`/`[DADAO-11 §章节名]`/`[SimRISC-0X §章节名]` → `[DADAO-NN §章节名]`/`[SimRISC-XX §章节名]`；:151 补 `[DADAO-21 §寄存器规范]`。
- `.tao/knowledge/contract-isa.md`：15 处陈旧 § 名补全（`SimRISC-08/09/10 §比较操作` → `§比较操作 — 值语义`；`§Bit manipulating：位操作指令` → `… — 值语义`）；**补引 8 处**：:65 `[SimRISC-00 §浮点状态寄存器]`、:157/:159 `[SimRISC-00 §指令域说明]`、:611 `[spec-decision]`、:826 `[SimRISC-00 §浮点状态寄存器]`、:1071 `[SimRISC-11 §非法指令][SimRISC-00 §SimRISC QFC]`、:1142 `[spec-decision]`；:1195 把合并前缀 `[SimRISC-04/08/09/10 §乘除操作]` **拆为 4 个单前缀引用**（顺带修掉该行的合并前缀盲区）。
- `.tao/knowledge/contract-elf.md`：:100 补 `[ADR-0003 §D5]`。
- `contracts/abi.yaml`：:46 F-x1 `SimRISC-02 §函数调用; SimRISC-02 §函数返回` → `SimRISC-06 ...`（YAML 解析 OK）。
- `.work/evidence/SPEC-094t/run.sh`（新增，`.work/` 不入库）。
- 日志：`.work/log/spec/SPEC-094t-{check_spec_refs-before,check_spec_refs-after,make_check,check_spec_refs,classification,evidence-default,evidence-inject}.log`。

**未触碰** `spec/README.md`、`spec/Process-02-合约编写规范.md`（并发 `SPEC-092t` 争用）；`spec/`、`tests/`、`components/`、`.tao/archive/**` 零改动。

**验收结果**：
- 改前基线（`check_spec_refs.py`，改前 log）：`结果: FAIL (76 violations: 18 Check1 + 58 Check2)`，`EXIT=1`；总引用 672，成功 654，失败 18。
- 改后（`.work/log/spec/SPEC-094t-check_spec_refs-after.log`）：
  ```
  Check 1 — 引用有效性
    总引用数: 680
    命中类型统计: 标题=670, 粗体=10, 正文=0
    成功解析: 680
    失败: 0
  Check 2 — 无引用规范断言
    命中数: 0
  ------------------------------------------------------------------------
  结果: PASS (0 violations)
  ```
  `EXIT=0`（两次重跑逐字节一致，确定性）。
- **逐条分类表**（完整 76 行见 `.work/log/spec/SPEC-094t-classification.log`）：
  - **Check1 18 → 全可机械修正**：3 条占位符（`contract-abi.md:13`，改不可解析形）+ 15 条陈旧 § 名（`contract-isa.md`，补「 — 值语义」）。
  - **Check2 58 → A=4 / B=44 / C=10**（最终口径：a=行内引用；b=同块**前导**引用；c=**表格/引用块**继承带引用前导块；list 不参与 c）：
    - **A（4，节标题）**：`contract-isa.md:257/1103/1107/1176` 含「保留/ILLI」的**节标题**，非断言 → 脚本 Check2 跳过标题。
    - **B（44，前导作用域已引用）**：**b=27**（`异常条件：[ref]` 后同块的分点等，引用在本行之前）+ **c=17**（表格/引用块继承其带引用前导块）。均不再行级误报。
    - **C（10，真实缺口 → 补引）**：`contract-abi.md:151`（+`[DADAO-21 §寄存器规范]`）、`contract-elf.md:100`（+`[ADR-0003 §D5]`）、`contract-isa.md`：:65（+`[SimRISC-00 §浮点状态寄存器]`）、:157/:159（+`[SimRISC-00 §指令域说明]`）、:611（+`[spec-decision]`）、:826（+`[SimRISC-00 §浮点状态寄存器]`）、:1071（+`[SimRISC-11 §非法指令][SimRISC-00 §SimRISC QFC]`）、:1142（+`[spec-decision]`）、:1195（合并前缀拆为 4 个单前缀引用）。
- **F-x1**：`contracts/abi.yaml:46` 已改 `SimRISC-06`；全仓 `contract-*.md`/`contracts/*.yaml` 中 `SimRISC-02 §函数` 残留 = 0（其余命中均在 `.tao/archive/**`、`.cache/refs/**` 历史/只读参考，非本任务范围）。
- **排除名单同步**：`check_spec_refs._EXCLUDED_CONTRACTS == check_spec_drift.EXCLUDED_CONTRACTS`（=`{contract-cfx-aliases.md, contract-asm-list.md}`），未改动，脚本核验 SYNCED。
- **make check**（`.work/log/spec/SPEC-094t-make_check.log`）：lit 31/31 Passed、`repository checks: PASS`、`EXIT=0`；`check_spec_drift: PASS`。
- **一键证据脚本**（`.work/evidence/SPEC-094t/run.sh`）真实输出（默认 12/12）：
  ```
  [PASS] check_spec_refs_zero_violations   | Check1=0 Check2=0 rc=0
  [PASS] make_check_spec_refs_exit0        | rc=0
  [PASS] abi_yaml_twin_ref_fixed           | match
  [PASS] abi_md_placeholders_inert         | ok
  [PASS] isa_stale_refs_resolved           | stale=0 fixed=15
  [PASS] exclusion_lists_synced            | SYNCED
  [PASS] make_check_exit0                  | rc=0
  [PASS] inject_a_independent_paragraph_fails | rc=1（注入行被捕获）
  [PASS] inject_a_restore_then_green          | rc=0 sha_match=yes
  [PASS] inject_b_trailing_citation_fails     | rc=1 & L3 flagged（后置引用不继承）
  [PASS] inject_c_blank_list_fails            | rc=1 & L5 flagged（空行+list 不参与继承）
  [PASS] positive_rule_bc_leading_covered     | rc=0 & 0 hits（正对照，口径非恒真）
  ── 结果: PASS=12 FAIL=0 ──   EXIT=0
  ```
  `--inject` 模式 **5/5 PASS**（`.work/log/spec/SPEC-094t-evidence-inject.log`）。
  **(a)/(b)/(c) 三类注入的实际判别结果**（合成探针 `.work/evidence/SPEC-094t/run.sh` / `inject_b_trailing` `inject_c_blank_list`）：后置引用（EXP-D）→ `FAIL @L3`；空行+带引用前导的 list（EXP-B）→ `FAIL @L5`；同块前导引用 / 表格继承 → 覆盖（`0 hits`）。
  **(a) 真实文件注入**：向 `contract-isa.md` 注入独立段落「任何跨域数据搬运必须设置 DMA_ALIGN 标志，否则为未定义行为。」→ `EXIT=1` 且明细含该行 → 还原（sha256 复原）→ `EXIT=0`。
- **门控化决策（deliverable 4）**：**不接入 `make check`**。理由：(a) Check2 仍是启发式（块作用域），未来内容仍可能误报，接入会阻断整条 `make check`；(b) 与 `INFRA-011t` 既定「独立 `make check-spec-refs`、不入 `check`」一致；(c) Check1 存在合并前缀盲区（见遗留），接入会给出「假信心」。独立目标已存在，模块 M2 门槛③可单独调用。

**新发现/坑**：
1. **Check2 行级判定约 7 成误报**：58 条中 44 条为「前导作用域已引用」（b=27 同块前导 + c=17 表格/引用块继承），4 条为节标题，仅 10 条为真实缺口。与 `INFRA-011t` reviewer「行级误报率评估」吻合。
2. **后置继承是真缺陷（architect G1）**：块作用域若按「同块任一引用」豁免，会继承**断言行之后**的引用。真实数据 `isa:1195`（实质断言，被下一行 `:1196 §返回地址栈` 豁免）、`isa:1142`、`isa:826` 受此影响。已收窄 rule (b) 为「同块**本行之前**引用」，并把上述 3 行逐条补引/拆引用。**教训**：继承必须限定为「前导」，且须对 (b)/(c) 各自注入反例（首轮 reviewer 仅注入独立段落，未触达 (b)/(c)，误判为有判别力）。
3. **跨空行继承只应对「前导 caption 的结构化产物」**：architect EXP-B 证明空行后的 **list** 若继承带引用前导块即过度放宽。已把 rule (c) 限为 **表格/引用块**；空行 list 须逐条自带引用（`isa:157/159/826/1142` 因此补齐）。
4. **Check1 合并前缀盲区**：`_PREFIX_ANCHOR` 要求 `SimRISC-<num> §`，不匹配 `[SimRISC-04/08/09/10 §…]`，故此类引用**从未被校验**。本任务已把 `isa:1195` 的合并引用拆为 4 个单前缀引用（现被 Check1 校验）；其余 `isa:1187/1188/1190` 仍为合并形态，登记为 deferred。
5. **`contracts/*.yaml` 无门控**：F-x1 属此类，`check_spec_refs` 只 glob `.tao/knowledge/contract-*.md`，`contracts/abi.yaml` 不被任何引用门控覆盖 → 同类陈旧引用可长期静默。
6. **反例注入还原**：目标文件本就有未提交改动，**不可用 `git checkout --`**（会丢弃本任务修复）；须 `cp` 备份 + 还原 + sha256 核对（脚本已实现，还原 sha 匹配）。

**遗留问题**：
- **[deferred] Check1 合并前缀盲区**（`contract-isa.md:1187/1188/1190`；`1195` 已修）：需 follow-up——扩展 `_PREFIX_ANCHOR` 支持 `SimRISC-04/08/09/10` 并逐文件校验，同时把 3 行的合并引用**拆为逐文件引用**（04 无后缀、08/09/10 带「 — 值语义」）。理由：属本任务 76 条之外，拆分涉及 3 行→多引用，超出「消解既有 76 条」的最小范围。
- **[deferred] `contracts/*.yaml` 引用门控缺失**：建议 follow-up 评估把 `contracts/*.yaml` 的 `spec_cite` 纳入 `check_spec_refs`（或新增 `check_spec_refs_yaml`），以机械拦截 F-x1 类孪生陈旧引用。
- 无其它未完成项；76 条已 100% 处置（18 Check1 修正 + 58 Check2：4 A / 44 B / 10 C）。

## 审阅记录
（reviewer 独立验证：重跑 + 逐条分类核 + 反例注入与还原）

### 第 2 轮 reviewer 验收（返工后复验）

**审查范围**：`tools/infra/check_spec_refs.py`（全文件 + diff）、`.tao/knowledge/contract-{abi,isa,elf}.md`、`contracts/abi.yaml`、`.work/evidence/SPEC-094t/run.sh`（全文件）；重点核 architect G1/G2 整改。

#### 1. G1 整改核验：rule (b)/(c) 收窄

**代码审查**：
- **rule (b)**（L427-438）：`preceding_cite[i]` 数组，`_seen_cite` 仅向前累积——断言行只看**本行之前**同块是否有引用，后续引用不追溯覆盖。✅
- **rule (c)**（L302-315）：`is_inheriting_child_line` 仅匹配 `|`（表格）和 `>`（引用块）开头；`-`/`+`/`*`（列表）不参与。✅
- **rule (a)** 未变（L457-458）。✅

#### 2. 0 violations 独立重跑

```
$ python3 tools/infra/check_spec_refs.py 2>&1; echo "EXIT=$?"
Check 1 — 引用有效性
  总引用数: 680
  命中类型统计: 标题=670, 粗体=10, 正文=0
  成功解析: 680
  失败: 0
Check 2 — 无引用规范断言
  命中数: 0
结果: PASS (0 violations)
EXIT=0
```

**结论**：0 violations，EXIT=0。680 总引用与完成区一致。

#### 3. 逐条补引抽查（architect G1 要求的 5 行）

| 行 | 处置 | 实际内容 | 判定 |
|----|------|---------|------|
| isa:157 | +`[SimRISC-00 §指令域说明]` | `i`：立即数...[SimRISC-00 §指令域说明] | ✅ |
| isa:159 | +`[SimRISC-00 §指令域说明]` | `z`：未使用，应为零（SBZ）[SimRISC-00 §指令域说明] | ✅ |
| isa:826 | +`[SimRISC-00 §浮点状态寄存器]` | rf0（FCSR）...[SimRISC-00 §浮点状态寄存器] | ✅ |
| isa:1142 | +`[spec-decision]` | 完整语义...留后续阶段...[spec-decision] | ✅ |
| isa:1195 | 合并前缀拆为 4 个单前缀 | [SimRISC-04 §乘除操作][SimRISC-08 §乘除操作][SimRISC-09 §乘除操作][SimRISC-10 §乘除操作] | ✅ |

#### 4. 关键核验：(a)/(b)/(c) 三类独立注入（不依赖 engineer 脚本）

**注入 (a) — 独立段落**（真实文件注入 `contract-isa.md`）：
```
注入内容：任何 DMA 传输必须遵守对齐约束，否则行为不可预测。
sha_before=64b1e736481ef12ed413e9e7bb7a86f0e5f676442d581c1b941434c38ec8a044
sha_injected=a4ffc735c36c6a12be1670841a5ecedb5456f8caf8980d6f3da6ba26c464be14
changed=YES
→ FAIL (1 violations: 0 Check1 + 1 Check2), EXIT=1
→ 注入行 :1474 被精确捕获
还原 sha_restored=64b1e736... sha_match=YES
→ PASS (0 violations), EXIT=0
```
✅ (a) 判别力成立。

**注入 (b) — 后置引用（EXP-D）**（合成探针，独立构造）：
```
探针 contract-probe-b.md:
  L2: # B
  L3: - 任何未对齐的访存必须触发 MALIGN 异常。
  L4: - 说明见 [SimRISC-01 §存取RD寄存器]
→ FAIL (1 violations), EXIT=1
→ L3 被标记（断言在前，引用在后），L4 的后置引用不覆盖 L3
```
✅ rule (b) 前导限定成立——后置引用不追溯覆盖。

**注入 (c) — 空行+list**（合成探针，独立构造）：
```
探针 contract-probe-c.md:
  L2: # C
  L3: 前导：[SimRISC-00 §版本]
  L4: (空行)
  L5: - 任何未对齐的访存必须触发 MALIGN 异常。
→ FAIL (1 violations), EXIT=1
→ L5 被标记（list 不继承跨空行的前导引用）
```
✅ rule (c) 排除 list 成立。

**正对照 — 同块前导 + 表格继承**（合成探针）：
```
探针 contract-probe-pos.md:
  L3: 异常条件：[SimRISC-01 §存取RD寄存器]
  L4: - 任何未对齐的访存必须触发 MALIGN 异常。   ← 同块前导引用，rule (b)
  L6: 表引：[SimRISC-00 §寄存器]
  L8-10: | 必须保留 | x |                          ← 表格继承，rule (c)
→ PASS (0 violations), EXIT=0
```
✅ 正对照通过——前导引用/表格继承仍有效，非恒真。

#### 5. 证据脚本审查与重跑

**脚本审查**：
- ✅ 非交互（`set -u`）
- ✅ 任一检查失败即非零退出
- ✅ 逐项打印「检查名 + 期望/实际 + 退出码」
- ✅ 三类注入各有独立函数：`inject_a_independent`（真实文件）、`inject_b_trailing`（合成后置引用）、`inject_c_blank_list`（合成空行+list）
- ✅ 正对照 `positive_leading_and_table` 验证口径非恒真
- ✅ `trap restore_contract EXIT INT TERM` 保证还原
- ✅ 无恒真断言（每条 report 的 rc 来自实际命令）
- ✅ 结尾不用 `tee` 吞退出码

**重跑默认模式**：12/12 PASS，EXIT=0
**重跑 `--inject` 模式**：5/5 PASS，EXIT=0

#### 6. `make check` 独立重跑

```
$ make check 2>&1; echo "EXIT=$?"
lit 31/31 Passed
repository checks: PASS
check-spec-drift: PASS
validate_encoding: 227 条记录 OK
check-scope: PASS
check-rule-refs: PASS
check-fp-contract: PASS
check-qemu-semantics: PASS (149 total, 149 passed)
EXIT=0
```

#### 7. Engineer 对 architect #2 归因订正核验

architect 声称 `isa:826/1142` 属 rule (b) 后置继承。engineer 订正为 rule (c) 覆盖（前导带引用块→list 继承）。

**独立验证**：
- `isa:826` 前导块：L821 `## §9 浮点运算指令...[SimRISC-07 §版本]`（heading+citation），L822-823 正文含引用 → 826 所在 list 块由前导引用块覆盖（rule c 旧口径含 list）。
- `isa:1142` 前导块：L1140 `## §14.2 LR-SC 原子指令...[SimRISC-12 §LR-SC指令]`（heading+citation）→ 1142 所在 list 块同理。

**结论**：engineer 归因订正**成立**。仅收窄 (b) 时 826/1142 由 (c) 覆盖未复现；再排除 (c)-list 后才复现并已补引。architect 的 (b) 归因未经隔离实验验证，属推测性错误。

#### 8. 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 只动 5 文件 | ✅ | `git diff --name-only` 恰为 5 文件 |
| 不改规范语义 | ✅ | diff 仅补引用/§名/标记 |
| `_NORMATIVE_MARKERS` 未收窄 | ✅（注：实际 15 个，非 16） | 逐个打印 15 个标记，一字未删 |
| 排除名单同步 | ✅ | `SYNCED` |
| 不接入 `make check` 理由 | ✅ | 与 INFRA-011t 一致 |
| deferred 项有登记 | ✅ | 完成区遗留问题段 |
| 临时目录 `/tmp/opencode/SPEC-094t-review2/` | ✅ | 合成探针和备份均在此 |

#### 判决

**Accepted**。

architect G1/G2 整改全部到位：
- rule (b) 收窄为前导继承（`preceding_cite`），后置引用不追溯覆盖——独立探针 EXP-D 证伪旧口径；
- rule (c) 收窄为仅表格/引用块（`is_inheriting_child_line`），list 不参与——独立探针 EXP-B 证伪旧口径；
- 收窄后复现的 5 行（isa:157/159/826/1142/1195）已逐条补引/拆引用；
- 0 violations 建立在真实修正上，非放宽口径；
- 三类注入 (a)/(b)/(c) 均 FAIL、正对照 PASS——判别力充分且非恒真；
- engineer 对 architect #2 归因订正成立（826/1142 为 rule c 覆盖，非 rule b）；
- 证据脚本 12/12 + 5/5 PASS、`make check` EXIT=0、约束无违反。

**小瑕疵**：完成区声称 `_NORMATIVE_MARKERS` "16 个标记"，实际 15 个。不影响功能。

### 第 1 轮 reviewer 验收

**审查范围**：`tools/infra/check_spec_refs.py`（全文件 + diff）、`.tao/knowledge/contract-{abi,isa,elf}.md`、`contracts/abi.yaml`、`.work/evidence/SPEC-094t/run.sh`（全文件）。

#### 1. `check_spec_refs.py` 独立重跑

```
$ python3 tools/infra/check_spec_refs.py 2>&1; echo "EXIT=$?"
Check 1 — 引用有效性
  总引用数: 673
  (Lnn) 行号形态: 0 处
  注: 本轮无 (Lnn) 实例
  命中类型统计: 标题=663, 粗体=10, 正文=0
  成功解析: 673
  失败: 0
Check 2 — 无引用规范断言
  命中数: 0
结果: PASS (0 violations)
EXIT=0
```

**结论**：0 violations，EXIT=0。与完成区声称一致。

#### 2. 逐条分类表抽查

| 抽查项 | 预期 | 实际 | 判定 |
|--------|------|------|------|
| Check1 18 条（3 占位符 + 15 陈旧§名） | 机械修正 | `contract-abi.md:13` 占位符改为 `DADAO-NN`/`SimRISC-XX`（不可解析形）；`contract-isa.md` 15 处 `SimRISC-08/09/10 §比较操作` → `§比较操作 — 值语义` | ✅ |
| Check2 A=4（节标题） | 行 257/1103/1107/1176 均为 `###` 标题 | 实测 4 行均为 `^\s*#{1,6}\s` 命中 | ✅ |
| Check2 B=49（块作用域已引用） | 前导引用行的子块（bullet/table/blockquote） | checker 逻辑 `(c) is_child_line && _preceding_block_has_cite` 覆盖 | ✅（逻辑审查通过，非逐条重算但机制正确） |
| Check2 C=5（补引） | abi:151, elf:100, isa:65/611/1071 | 逐行核对均含新增 spec 引用/标记 | ✅ |
| F-x1 `abi.yaml:46` | `SimRISC-06 §函数调用; SimRISC-06 §函数返回` | grep 确认；`yaml.safe_load` 解析 OK | ✅ |
| `SimRISC-02 §函数` 残留 | =0 | `grep -r` 于 `contracts/` + `contract-*.md` =0 | ✅ |

#### 3. 关键核验：Check2 块作用域改法是否有判别力（独立反例注入）

**注入内容**：向 `contract-isa.md` 末尾追加独立段落：
```
任何跨域数据搬运必须设置 DMA_ALIGN 标志，否则为未定义行为。
```
（含规范标记「必须」「未定义行为」，无任何 spec 引用/决策标记）

**注入前 sha**：`07b86cc101fe3aa154335b94522ec3708a773484b1a6a6a13bc57b1faf9396cd`

**注入后**：
```
$ python3 tools/infra/check_spec_refs.py 2>&1; echo "EXIT=$?"
Check 2 — 无引用规范断言
  命中数: 1
  命中明细:
    .tao/knowledge/contract-isa.md:1474
      任何跨域数据搬运必须设置 DMA_ALIGN 标志，否则为未定义行为。
结果: FAIL (1 violations: 0 Check1 + 1 Check2)
EXIT=1
```

**结论**：checker 正确 FAIL，命中明细精确指向注入行。**判别力成立**。

#### 4. 还原与回绿

```
还原后 sha：07b86cc101fe3aa154335b94522ec3708a773484b1a6a6a13bc57b1faf9396cd
sha_match=YES
结果: PASS (0 violations)
EXIT=0
```

**git status 核验**：`.tao/knowledge/contract-isa.md` 显示 `M`，但 diff 内容仅含任务本身的 § 名修正和补引改动，无注入残留。

#### 5. 证据脚本审查与重跑

**脚本审查**：
- ✅ 非交互（`set -u`，无 stdin 依赖）
- ✅ 任一检查失败即非零退出（`FAIL` 计数 → `exit 1`）
- ✅ 逐项打印「检查名 + 期望/实际 + 退出码」（`report` 函数）
- ✅ 内置反例自检（`inject_selfcheck`：cp 备份 → 追加 → FAIL → 还原 → sha 核对 → 回绿）
- ✅ 结尾不用 `tee` 吞退出码（`[ "$FAIL" -ne 0 ] && exit 1; exit 0`）
- ✅ `trap restore_contract EXIT INT TERM` 保证异常时也能还原
- ✅ 无恒真断言（每条 report 的 rc 判定来自实际命令退出码）
- ✅ 注入有效验证（`sha_before != sha_injected` 确认文件确实改变）

**重跑默认模式**：9/9 PASS，EXIT=0
**重跑 `--inject` 模式**：2/2 PASS，EXIT=0

#### 6. `make check` 独立重跑

```
$ make check 2>&1; echo "EXIT=$?"
lit 31/31 Passed
repository checks: PASS
check-spec-drift: PASS
validate_encoding: 227 条记录 OK
check-scope: PASS
check-rule-refs: PASS
check-fp-contract: PASS
check-qemu-semantics: PASS (149 total, 149 passed)
EXIT=0
```

**注意**：`spec/README.md` 和 `spec/Process-02-合约编写规范.md` 有 diff，系并发 `SPEC-092t` 改动，非本任务产物。`check-spec-drift` 仍 PASS（未冲突）。

#### 7. 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 只动 `check_spec_refs.py` + 3 `contract-*.md` + `contracts/abi.yaml` | ✅ | `git diff --stat` 限定 5 文件；其余 diff 为其他任务或任务书自身 |
| 不改规范语义（只修引用/来源头/排除名单） | ✅ | diff 核查：仅 § 名后缀补全 + 新增 spec 引用标记 + 占位符改不可解析形 |
| `_NORMATIVE_MARKERS` 未收窄 | ✅ | 逐行比对：16 个标记全部保留（ILLI/UNDI/MALIGN/IALIGN/保留/reserved/Reserved/必须/应当/不得/需要/MUST/SHALL/REQUIRED/SBZ） |
| 排除名单同步 | ✅ | Python 脚本加载两模块比较：`SYNCED` |
| 不接入 `make check` 理由充分 | ✅ | Check2 启发式（块作用域）仍有误报风险，接入会阻断整条门控；与 INFRA-011t 一致 |
| deferred 项有登记 | ✅ | 完成区"遗留问题"段：(1) Check1 合并前缀盲区 (2) `contracts/*.yaml` 引用门控缺失 |
| 临时目录 `/tmp/opencode/SPEC-094t-review/` | ✅ | 审查所用临时文件均在此目录 |

#### 8. 假阴性路径分析

Check2 从行级改为块作用域后，理论上存在假阴性：若同一块（连续非空行）内既有带引用的断言又有不带引用的断言，后者会继承前者的引用。此为已知启发式边界（engineer 自审 F3 已披露）。实践中合约的行文模式是「前导引用行 + 子块」，同一块内混合引用/非引用断言的场景极罕见。独立注入证明 checker 对**独立段落**的未引用断言仍能捕获，判别力满足验收要求。

#### 判决

**Accepted**。

验收命令块全部在独立重跑下通过（`check_spec_refs.py` 0 violations EXIT=0、`make check` EXIT=0、证据脚本 9/9+2/2 PASS）；76 条分类可追溯；反例注入证明 checker 判别力成立；约束无违反；deferred 项有登记。

### 第 1 轮 engineer 自审

**审查范围**：`tools/infra/check_spec_refs.py`（改动段全读）、`.tao/knowledge/contract-{abi,isa,elf}.md`、`contracts/abi.yaml`、`.work/evidence/SPEC-094t/run.sh`（全文件）。

**逐行审查发现**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 docstring 误引用不存在的 `_line_is_covered` | ✅已修 | 改为「下方 Check 2 作用域实现（规则 (a)(b)(c)）」 | `grep -c '_line_is_covered'` = 0；`py_compile` OK |
| F2 `is_child_line` 对 `**bold**` 误判为 `*` 列表 | ✅已核 | `s[1] == " "` 判定，`**` 不成立 | 探针 §A/§B/§C 实测：粗体段不被继承，§A 仍 FAIL |
| F3 块继承可能过度覆盖「无关表格」 | ⏸延后（已披露） | 不修；文档化为已知启发式边界 | 新增 finding #1 记录；注入独立段落仍 FAIL |
| F4 证据脚本 check2 残留一行错误写法（`report ... -0 2>/dev/null`） | ✅已修 | 删除该两行，简化为单次 `make check-spec-refs` 捕获 rc | 默认模式 9/9、`--inject` 2/2 均 PASS |
| F5 注入自检可能留下仓库残留 | ✅已核 | `cp` 备份 + `trap ... EXIT` + sha256 核对 | 运行后 `grep -c 注入行` = 0；`git status` 无异常文件 |
| F6 `[spec-decision]` 用于 isa:611 是否恰当 | ✅已核 | v5 值语义决策（非 spec 派生），正是该标记的设计用途（INFRA-011t 坑 #4） | 标记后 Check2 = 0；语义未改（仅加标记） |
| F7 陈旧 § 名替换是否误伤 SimRISC-04/05 | ✅已核 | 仅替换 `SimRISC-08/09/10` 前缀的精确串（replaceAll 限定前缀） | `grep -c`：`[SimRISC-04 §比较操作]`=6、`[SimRISC-05 §比较操作]`=2（保留原形）；`08/09/10 §比较操作 — 值语义`=9；Check1 0 失败 |
| F8 `contracts/abi.yaml` 改动破坏 YAML | ✅已核 | 仅改双引号内字符串内容 | `yaml.safe_load` OK，`call_ret.spec_cite` = `SimRISC-06 §函数调用; SimRISC-06 §函数返回` |
| F9 elf:100 引 `ADR-0003 §D5` 是否对应 §5.1 | ✅已核 | 附录 A 明示 §5（段对齐）= ADR-0003 §D5 | 文件内附录 A 对照表；Check1/2 均 PASS |
| F10 每条断言的可失败路径 | ✅已核 | 证据脚本各 check 均有可达 FAIL 分支（计数≠预期、grep 不命中、rc≠0、注入后 rc=0 即 fail） | `--inject` 真实输出 rc=1→还原 rc=0；探针 §A 单独 FAIL |

**自审判决**：finding 全部已修/已核（F3 为已披露的启发式边界，非缺陷）；无未决项。状态置 `待验收`。

### 第 1 轮 architect 交叉复核（双模型互验，2026-10-04）

**复核范围**：任务书目标/约束/验收 vs reviewer 第 1 轮验收；`tools/infra/check_spec_refs.py`（新全文件 + diff）、3 份 `contract-*.md` diff、`contracts/abi.yaml`、`.work/evidence/SPEC-094t/run.sh`、`.work/log/spec/SPEC-094t-classification.log`、`.tao/archive/M1/infra/INFRA-011t-spec引用审计器.md`。临时目录 `/tmp/opencode/SPEC-094t-xcheck/`；未改任何受审文件；未提交 git。

#### 0. 关键结论

**判决：Needs Revision**。核心交付（76→0、F-x1、证据脚本、`make check`、排除名单同步）**属实且独立复现**；但 reviewer 对「Check2 改块作用域」的验收**证据不足且表述失准**——该改动**确实削弱了断言**，且存在**reviewer 未测试、完成区/审阅记录未披露**的假阴性类（rule (b) 会继承**位于断言行之后**的引用），在真实合约中有 3 处实例（含一条实质性规范断言）。详见 G1/G2。

#### 1. 独立复现（全部通过）

| 项 | 命令 | 结果 | 判定 |
|----|------|------|------|
| 改前基线 | 旧脚本(HEAD) × HEAD 合约 | `FAIL (76: 18 Check1 + 58 Check2)` `EXIT=1` | ✅ 与完成区逐项一致 |
| 改后 | `python3 tools/infra/check_spec_refs.py` | `PASS (0)` `EXIT=0`（总引用 673） | ✅ |
| **隔离实验** | 新脚本 × HEAD 合约 | `FAIL (23: 18 Check1 + 5 Check2)` | ✅ 证明 49 条 B 全由新块作用域逻辑豁免，仅 5 条 C 需补引 |
| Check1 分类 | 提取基线 18 条 | 3 占位符(abi:13) + 15 陈旧§名(isa:862…1053) | ✅ 可追溯 |
| Check2 分类 | 58 = 4 A + 49 B + 5 C | 与 classification.log 一致 | ✅ |
| `abi.yaml:46` | `yaml.safe_load` | `call_ret.spec_cite = "SimRISC-06 §函数调用; SimRISC-06 §函数返回"`，YAML OK | ✅ |
| 排除名单同步 | 加载两模块比较 | `SYNCED`（`{asm-list, cfx-aliases}`） | ✅ |
| 5 文件范围 | `git diff --stat` | 本任务 diff 恰为 5 文件；changelog/spec/README/Process-02 属并发 `SPEC-092t` | ✅ |
| `make check` | `make check` | lit 31/31、`repository checks: PASS`，`EXIT=0` | ✅ |
| 证据脚本 | 默认 / `--inject` | 9/9 PASS / 2/2 PASS，`EXIT=0` | ✅ |
| 独立反例注入 | 追加独立段落「…必须设置 XALIGN…」→ 脚本默认模式 | 脚本 `EXIT=1`（`check_spec_refs_zero_violations` FAIL、`make check-spec-refs` rc=2）→ 还原 sha 复原 `07b86cc1…` → 回绿 | ✅ 脚本可失败 |

#### 2. G1（关键）：rule (b) 继承「之后」的引用——真实假阴性

`check_spec_refs.py` 新增规则 **(b)**「同一块（连续非空行）内任一非代码行含引用 ⇒ 整块视为已引用」，**不限引用位置在断言行之前**。INFRA-011t reviewer 的建议是「行级改为**最近前导引用行**判定」（前导！），而实现允许**从后续行继承**。在 temp 副本注入对照（旧行级 vs 新块作用域）：

```
EXP-A 同块 + 前导引用（异常条件：[SimRISC-01 §存取RD寄存器] 换行 - …必须…）  → 旧:FAIL  新:漏判
EXP-B 前导引用块 + 空行 + list 子块（rule (c)）                              → 旧:FAIL  新:漏判
EXP-C 独立段落（rule (a) 未变）                                              → 旧:FAIL  新:FAIL ✅
EXP-D 引用在被断言行之后（- 断言…必须… 换行 - …[SimRISC-01 §存取RD寄存器]）   → 旧:FAIL  新:漏判
```
新 checker 在含 4 条注入的副本上仅报 `命中数: 1`（只报 EXP-C）；旧 checker 报 `命中数: 57`（含全部 4 条）。**A/B/D 三类被漏判**。

**真实数据实例（均在本次「B=49」内，靠 rule (b) 后置继承豁免）**：
- `contract-isa.md:826`（含「需要」）——被**其下一行** `:827 [SimRISC-00 §浮点寄存器]` 豁免；
- `contract-isa.md:1142`（含「保留」）——被**其下一行** `:1143 [SimRISC-00 §MISC-AMO 指令编码]` 豁免（两行语义无关）；
- `contract-isa.md:1195`（div/rem 精确异常，**实质性断言**）——被**其下一行** `:1196 [SimRISC-00 §返回地址栈]` 豁免，两行**完全无关**；该行本自带 `[SimRISC-04/08/09/10 §乘除操作]`，因**合并前缀盲区**未被解析，rule (b) 恰好**掩盖**了 deferred 项 #1 的盲区。

**后果**：49 条 B 中至少 3 条不是「前导引用行已覆盖」，而是「后置/无关引用连带」。即 `58 → 0` 的成功**部分建立在放宽判定口径**之上，且这个放宽**超出** INFRA-011t 所建议的前导模型。

#### 3. G2：reviewer 的注入未触达被改动路径

reviewer §3「判别力」注入的是**独立段落**（前后空行），只验证 rule (a) 邻域，**完全不经 rule (b)/(c)**；§8 据此断言「判别力满足验收要求」属 inference gap。证据脚本 `inject_selfcheck` 同样只注入 `\n…MALIGN…\n` 独立段落。故「块作用域改法有判别力」**未被证明**——恰恰相反，EXP-A/B/D 证明其在 (b)/(c) 路径上**无判别力**。reviewer §8 「同一块内混合引用/非引用断言场景极罕见」与数据不符（§15.2 三个 bullet 各引不同来源，且存在上述 3 处后置豁免）。

#### 4. 已确认通过项（reviewer 无遗漏之处）

- 76 条分类可追溯、5 条 C 补引到位、Check1 15 条陈旧 § 名修正正确（未误伤 SimRISC-04/05）；
- `_NORMATIVE_MARKERS` 未收窄（16 个全在）；合约 diff 仅补引用/§名，未改规范语义；
- F-x1 孪生引用已改且全仓 `SimRISC-02 §函数` 残留=0；YAML 可解析；
- 未接入 `make check` 理由与 `INFRA-011t` / Makefile 一致（`check-spec-refs` 为独立 target，`check:` 不含）；
- 两 deferred 项（Check1 合并前缀盲区、`contracts/*.yaml` 无门控）在完成区如实登记（注：仅登记于完成区，未同步 `issues.yaml`；`ISS-086` 仍 `open`，应由 `/complete` 关闭——非 reviewer 缺陷）。

#### 5. 最小整改建议（engineer）

1. **收窄 rule (b)** 至「本行**之前**的同块引用行」（对齐 INFRA-011t「最近前导引用行」）；随后重分类：`isa:826/1142/1195` 将复现为 Check2 违规，须各自处置（补引 / `[spec-decision]` / 或先修 deferred #1 的合并前缀盲区）。
2. **补 (b)/(c) 路径的注入用例**：注入一条「仅邻接后续引用」或「空行后接前导引用块的 list」断言，**期望 FAIL**；若仍漏判即证明需修 (b)/(c)（可复用本复核 EXP-A/B/D 的最小样本）。
3. 若团队/用户裁定「后置继承」可接受，则须在完成区/审阅记录**显式重述假阴性边界为「同块任意位置引用继承」**（而非「前导」），并将上方 3 处真实实例逐条标注，方可维持 Accepted。

> 复核未改动任何受审文件；注入实验均在 `/tmp/opencode/SPEC-094t-xcheck/` 副本进行，真实注入后已还原（sha `07b86cc1…` 匹配、残留=0）。

### 第 2 轮 engineer 返工（架构师交叉复核 Needs Revision 整改）

**整改依据**：架构师交叉复核 G1（rule (b) 后置继承 → 真实假阴性）/ G2（注入未触达 (b)/(c)）/ 建议 1–3。

**核心改动**（`tools/infra/check_spec_refs.py`）：
- **rule (b) 收窄为前导**：由「同块任一引用」改为「同块内**本行之前**已有引用行」（`preceding_cite[i]`，`_seen_cite` 仅向前累积）。消除后置继承。
- **rule (c) 收窄为表格/引用块**：`is_child_line` → `is_inheriting_child_line`（仅 `|`/`>` 开头的块）；**list 不参与继承**（空行分隔的列表视为独立断言序列，须逐条自带引用），对齐 architect EXP-B。
- 保留：rule (a) 行内引用；节标题不参与 Check2；`_NORMATIVE_MARKERS` 16 个标记一字未收窄。

**收窄后复现与逐条处置**（真实命令输出，非放宽口径）：

| 步骤 | 复现集合 | 说明 |
|------|---------|------|
| 仅收窄 rule (b)（(c) 暂含 list） | `isa:1195` | `826/1142` 该步**未**复现——它们的覆盖实为 rule (c)（前导带引用块 823/1140），非 rule (b) 后置；架构师 G1 的归因据此订正 |
| 再收窄 rule (c)（排除 list） | `isa:157,159,826,1142,1195` | 5 条复现 |

逐条处置：
| 行 | 处置 | 依据 |
|----|------|------|
| `isa:826` | +`[SimRISC-00 §浮点状态寄存器]` | rf0 寄存器模型来源 |
| `isa:1142` | +`[spec-decision]` | LR-SC 语义留后续阶段的 v5 决策 |
| `isa:1195` | 合并前缀拆为 `[SimRISC-04/08/09/10 §乘除操作]` 四个单前缀引用 | 顺带修掉该行的合并前缀盲区（Check1 现可校验） |
| `isa:157`/`isa:159` | +`[SimRISC-00 §指令域说明]` | 操作数寻址方式字母表来源（前导行 152） |
| （首轮 5 条 C：`abi:151`/`elf:100`/`isa:65`/`isa:611`/`isa:1071`） | 见完成区，保持不变 | — |

**逐条 finding 处置**：
| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 rule (b) 后置继承 | ✅已修 | `preceding_cite` 前导累积，删 `block_has_cite` 在 (b) 的使用 | `EXP-D` 探针（后置引用）→ `check_spec_refs --contract-dir` `FAIL @L3`；真实数据复现集合见上表 |
| G1 rule (c) list 过度覆盖 | ✅已修 | `is_inheriting_child_line`（仅 table/blockquote） | `EXP-B` 探针（空行+带引用前导的 list）→ `FAIL @L5`；正对照（同块前导 / 表格继承）→ `0 hits` |
| G1 3 处真实行未显式溯源 | ✅已修 | `isa:826/1142/1195` 补引/拆引用 | 收窄后 `check_spec_refs` = `PASS (0 violations)`，`EXIT=0` |
| G2 注入只测 (a) | ✅已修 | 证据脚本新增 `inject_b_trailing_citation_fails`、`inject_c_blank_list_fails`、`positive_rule_bc_leading_covered` | 默认 12/12、`--inject` 5/5，各 (b)/(c) 注入均实测 FAIL |
| 复现集合与架构师 #2（3 条）不符 | ✅已披露 | 架构师 #2 归因（826/1142 属 rule b）经实测**不成立**：仅收窄 (b) 时 826/1142 由 rule (c) 覆盖，未复现；再排除 (c)-list 后二者才复现并已处置 | 见上「步骤」表；完成区数字已按实测更新 |

**收尾复验（真实输出）**：
- `python3 tools/infra/check_spec_refs.py` → `结果: PASS (0 violations)`，`EXIT=0`；总引用 680（670 标题 + 10 粗体），0 失败。
- `make check` → lit 31/31、`repository checks: PASS`，`EXIT=0`；`check_spec_drift: PASS`。
- 一键证据脚本默认 **12/12 PASS** / `--inject` **5/5 PASS**（`.work/log/spec/SPEC-094t-evidence-{default,inject}.log`）。
- 仓库无注入残留（`grep -c DMA_ALIGN` = 0；`.tao/knowledge/contract-isa.md` diff 仅本任务改动）。

**自审判决**：G1/G2 全部整改完成；数字与真实输出逐条对齐；无未决项。状态置 `待验收`。

### 第 2 轮 architect 交叉复核（双模型互验，2026-10-04）

**复核范围**：第 1 轮 architect 交叉复核 G1/G2 的整改；`tools/infra/check_spec_refs.py`（新全文件）、3 份 `contract-*.md` diff、`.work/evidence/SPEC-094t/run.sh`（全文件）、reviewer 第 2 轮记录。临时目录 `/tmp/opencode/SPEC-094t-xcheck2/`；未改任何受审文件；未提交 git。

#### 0. 关键结论

**判决：Accepted**。G1（rule (b) 后置继承 / rule (c) list 过度覆盖）与 G2（注入未触达 (b)/(c)）**整改到位**；`0 violations` 现建立在**真实修正**（+ 经审计的前导/结构化继承口径）之上。上轮我发现的 **EXP-A/B/D 假阴性已全部消除**。残留边界（rule (c) 表格/引用块跨空行继承、rule (b) 同块前导继承）属 INFRA-011t 所建议、且已披露的启发式模型，**非本轮新增放宽**，真实数据经抽查无有害实例。发现 2 处**非阻断**文档瑕疵（见 §4）。

#### 1. G1 整改核验（代码 + 隔离实验）

**代码**（`tools/infra/check_spec_refs.py`）：
- rule (b)（L441-455）：`preceding_cite[i] = _seen_cite.get(bid_i, False)` 在**写入本行引用之前**取值，`_seen_cite` 仅向前累积 → **仅前导继承，后置不追溯**。✅
- rule (c)（L299-315 `is_inheriting_child_line`）：仅 `|`（表格）/`>`（引用块）；list 不参与。✅

**隔离实验**（新 checker × HEAD 合约）：`FAIL (28: 18 Check1 + 10 Check2)`，Check2 复发集 = `{abi151, elf100, isa65, isa157, isa159, isa611, isa826, isa1071, isa1142, isa1195}` —— 与 C=10 完全一致，证明 **44 条 B 全由收窄后的 (b)/(c) 正当覆盖**，`0 violations` 非放宽口径所得。

#### 2. 5 行真实处置核验（真实内容）

| 行 | 处置 | 实测内容 | 判定 |
|----|------|---------|------|
| `isa:157` | +`[SimRISC-00 §指令域说明]` | `- i：立即数…[SimRISC-00 §指令域说明]` | ✅ |
| `isa:159` | +`[SimRISC-00 §指令域说明]` | `- z：未使用，应为零（SBZ）[SimRISC-00 §指令域说明]` | ✅ |
| `isa:826` | +`[SimRISC-00 §浮点状态寄存器]` | `- 唯一例外：rf0…[SimRISC-00 §浮点状态寄存器]` | ✅ |
| `isa:1142` | +`[spec-decision]` | `- 完整语义…留后续阶段…[spec-decision]` | ✅ |
| `isa:1195` | 合并前缀**拆为 4 个单前缀** | `[SimRISC-04 §乘除操作][SimRISC-08 §乘除操作][SimRISC-09 §乘除操作][SimRISC-10 §乘除操作]` | ✅（顺带修掉该行合并前缀盲区） |

`python3 tools/infra/check_spec_refs.py` → `PASS (0 violations)`、总引用 680、`EXIT=0`。

#### 3. 判别力：三路径独立注入（复现第 1 轮 EXP-A/B/D）

在 current 合约副本（`/tmp/.../exp/contracts`）注入 5 段，新 checker 结果：

```
EXP-A 独立段落（无引用断言）                    → FAIL @1477  ✅（rule a）
EXP-B 空行 + 带引用前导块后的 list              → FAIL @1484  ✅（list 不再继承；上轮漏判已消除）
EXP-C 同块 + 前导引用（正对照）                 → 覆盖（未报）✅（rule b 仍有效）
EXP-D 引用在被断言行之后（同块）                → FAIL @1491  ✅（后置不继承；上轮漏判已消除）
EXP-E 带引用 caption + 表格（正对照）           → 覆盖（未报）✅（rule c 仍有效）
结果: FAIL (3 violations) —— 恰为 A/B/D 三条期望 FAIL
```
**上轮 EXP-A/B/D 三类假阴性全部消除**，正对照 C/E 证明口径非恒真。

证据脚本独立重跑：默认 **12/12 PASS**、`--inject` **5/5 PASS**，`EXIT=0`；脚本三条注入（`inject_a_independent` / `inject_b_trailing` / `inject_c_blank_list`）各有可达 FAIL 路径 + 正对照，无恒真。**我自己的独立反例注入**（追加「…必须设置 ZALIGN…」）→ 脚本 `EXIT=1`（`check_spec_refs_zero_violations` FAIL、`make check-spec-refs` rc=2）→ 还原 sha `64b1e736…` 匹配 → 回绿。

#### 4. 仍存假阴性边界（扫描结论：无新增放宽）

对 (b)/(c) 边界再构造 4 例（`exp2/`）：
```
EXP-F 无关引用 prose + 空行 + 表格      → 覆盖（rule c 从紧邻带引用非标题块继承）
EXP-G 同块：引用行之后的普通规范行       → 覆盖（rule b 同块前导）
EXP-H 无关引用 prose + 空行 + blockquote → 覆盖（rule c）
EXP-I 无前导引用块的表格（正对照）        → FAIL ✅（继承非恒真）
```
- EXP-F/G/H 属**残留边界**，但均为 INFRA-011t 建议的「前导 / 结构化投影」模型（**非**我第 1 轮指出的「后置」方向），且**在首轮即存在**（本轮只删除 list、未新增），故非本轮引入的放宽。
- **真实数据无害**：逐条核 44 条 B 的覆盖来源——isa b=27、c=11，abi c=3、elf c=3；所有 c 项的前导块均为**该表格/附注的 caption**（如 `rf0 位域定义：[SimRISC-00 §浮点状态寄存器]`→位域表、`返回地址栈…[SimRISC-00 §返回地址栈]`→RAS 表、`空白单元格表示 reserved…[SimRISC-00 §SimRISC QFC]`→编码表），无「无关引用 prose + 表格」实例。

#### 5. 归因订正核验（我第 1 轮 #2 的订正）

用 monkeypatch 复现「**仅收窄 (b)、保留旧 (c)-list**」跑 HEAD 合约：`FAIL (24: 18 Check1 + 6 Check2)`，复发集 = `{abi151, elf100, isa65, isa611, isa1071, isa1195}`。即 `826/1142/157/159` **未**复发（被旧 (c)-list 覆盖），**仅 `1195` 单独由 rule (b) 覆盖**。→ **engineer 订正确立**：我第 1 轮述及的 826/1142 系脚本按 `(b)→(c)` 求值顺序命中的**规则归属**，二者实被旧 (c) 同时覆盖；核心结论（后置继承为真缺陷，`1195` 唯一命中）仍成立，且已被修复。

#### 6. 其它

- `make check` 独立重跑 **`EXIT=0`**（lit 31/31、`repository checks: PASS`）。
- 两 deferred 项如实：Check1 合并前缀盲区（`isa:1187/1188/1190` 仍为合并形态，`1195` 已修）、`contracts/*.yaml` 无门控；5 文件范围；未接入 `make check` 理由成立。
- **非阻断瑕疵**（建议 /complete 或 engineer 顺带订正，不影响功能）：
  1. 完成区「修改文件」称 `_NORMATIVE_MARKERS`「**16 个**标记全保留」，实测 **15 个**（`ILLI/UNDI/MALIGN/IALIGN/保留/reserved/Reserved/必须/应当/不得/需要/MUST/SHALL/REQUIRED/SBZ`）——reviewer 第 2 轮已指出，属文档笔误。
  2. `审阅记录` 中「第 2 轮 reviewer 验收」被置于「第 1 轮 reviewer」**之前**，与「按轮次追加、避免混杂」的排序约定不符（内容本身无误）。

> 复核未改动任何受审文件；全部注入在 `/tmp/opencode/SPEC-094t-xcheck2/` 副本进行，真实注入后已还原（sha `64b1e736…` 匹配、残留=0）。
