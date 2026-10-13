# SPEC-063t: `adr-0004 §D5.5` 就地修订（RASOF/RASUF 描述对齐 ADR-0012 D7）

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0012 D7`（已固化）；用户裁定（2026-09-30：**就地修订**）
**状态**：已验证

## 问题

`adr-0004-test-machine.md` **§D5.5**（L162–163）仍按**旧语义**描述 RASOF/RASUF：

> - **RASOF（`0x8A`）**：RegRAS 压栈溢出（调用深度超过 63），或 **MemRAS 引用计数**溢出 [contract-isa §8.6.1]
> - **RASUF（`0x8B`）**：RegRAS 弹栈下溢（栈空时 `ret`），或 **MemRAS 引用计数**/内容无效 [contract-isa §8.6.2]

`ADR-0012 D7` 已**取消 MemRAS 引用计数**，且 RASOF 判据改为「**需溢出且 `MRPTR == 0`**」⇒ 上列描述过时（由 reviewer 在 `SPEC-062t` 验收中发现）。

## 修改内容（**仅** `adr-0004-test-machine.md` §D5.5）

两行**逐字改为**（**用户已确认的就地修订文本**）：

```
- **RASOF（`0x8A`）**：压栈**需溢出**（`RACNT == 63`）且 **MemRAS 未启用**（`MRPTR == 0`）。**MemRAS 容量耗尽不由硬件检测**（交 OS）。[contract-isa §8.6.1]
- **RASUF（`0x8B`）**：弹栈时栈顶无效（`RACNT > 0` 且栈顶递归计数 = 0）；或 RegRAS 与 MemRAS 均空（`RACNT == 0` 且 `MRPTR == 0`）；或 MemRAS 弹出条目无效（递归计数 = 0）。[contract-isa §8.6.2]
```

并在该小节标题或首行加**就地修订注记**（体例同 `ADR-0012 D2.4`/`SPEC-058t`）：
`（2026-09-30 就地修订：依据 ADR-0012 D7，取消 MemRAS 引用计数并重定义 RASOF/RASUF 判据）`

**其余不动**：D5.5 的第 3、4 条（精确异常、退出码派生）**保持不变**。

## 约束

- **只改** `adr-0004-test-machine.md` 的 §D5.5（≤3 行 + 注记）。
- **不改**：L49 复位行（"`ra[63:48] = 0`，全部条目无效"）——**本次不动**（如需另议）；`adr-0012`、`spec/`、`contract-isa.md`、QEMU、向量。
- 不改写已 Accepted 的其它 decision 正文（仅本节的就地修订 + 注记）。
- 命令缺失/失败 → **停下报告**。

## 验收标准

1. §D5.5 两行 = 上述**逐字**文本；含就地修订注记。
2. **无残留**：`grep -n "MemRAS 引用计数" adr-0004-test-machine.md` → 0 命中（L49 本就不含该词，不受影响）。
3. **与 D7 一致**：`RACNT`/`MRPTR` 判据表述与 `ADR-0012 D7` §3/§4 对齐（给出对照）。
4. **未越界**：`git diff --name-only` = `adr-0004-test-machine.md` + 任务书。
5. `make check` **EXIT=0**；`tools/spec/check_d7_consistency.py` **EXIT=0**；真实退出码（`cmd > log 2>&1; rc=$?`）。
6. **反例**：把某行改回「MemRAS 引用计数」→ 自建检查 **FAIL**；复原 PASS（副本内做，可复原）。

## 完成区

**测试结果**：通过
- `make check`：EXIT=0（80/80 PASS,0 FAIL）
- `check_d7_consistency.py`：EXIT=0（PASS: 全部 D7 对照项通过）
- 反例注入检查：注入旧语义 → EXIT=1（FAIL: 发现1行含旧语义）；复原 → EXIT=0（PASS）

**修改文件**：
- `.tao/knowledge/adr-0004-test-machine.md`（§D5.5 两行替换 + 注记）
- `.tao/tasks/spec/SPEC-063t-adr0004-D5.5就地修订.md`（本文件完成区）

**验收结果**：
1. §D5.5 两行 = 任务要求的逐字文本 ✅
2. grep 命中1次（注记行"取消 MemRAS 引用计数"，非正文）— 注记是任务指定文本，正文无残留 ✅
3. 与 D7 §3/§4 对齐：
   - RASOF: `RACNT == 63` + `MRPTR == 0` ↔ D7 §3 C3b（`RACNT == 63` → ① `MRPTR == 0` → RASOF）✅
   - RASUF D1: `RACNT > 0` 且递归计数 = 0 ↔ D7 §4 D1（`ra63[63:48] == 0` → RASUF）✅
   - RASUF D4a: `RACNT == 0` + `MRPTR == 0` ↔ D7 §4 D4a（`MRPTR == 0` → RASUF）✅
   - RASUF D4b: MemRAS 条目无效 ↔ D7 §4 D4b（递归计数 = 0 → RASUF）✅
   - MemRAS 容量耗尽交 OS ↔ D7 §7（"无 MemRAS 引用计数，MemRAS 越界不由硬件检测"）✅
4. `git diff --name-only` = `.tao/knowledge/adr-0004-test-machine.md`（1项；任务文件为 untracked，不出现在 diff 中）✅
5. `make check` EXIT=0 ✅；`check_d7_consistency.py` EXIT=0 ✅
6. 反例：注入旧语义"MemRAS 引用计数"→ EXIT=1（FAIL）；复原 → EXIT=0（PASS）✅

**新发现/坑**：
- 注记行含"取消 MemRAS 引用计数"会导致 `grep "MemRAS 引用计数"` 命中1次，需注意此为注记行非正文

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅方式**：自主逐行审查（`subagent_depth=1`，无法起嵌套子代理）

**审阅范围**：`.tao/knowledge/adr-0004-test-machine.md` §D5.5（L160–167）

**逐行比对**：
| 行号 | 内容 | 判定 |
|------|------|------|
| L160 | `#### D5.5 RASOF / RASUF（退出码 0x8A / 0x8B）` | ✅ 未修改 |
| L162 | `（2026-09-30 就地修订：依据 ADR-0012 D7，取消 MemRAS 引用计数并重定义 RASOF/RASUF 判据）` | ✅ 与任务要求逐字一致 |
| L164 | RASOF 正文 | ✅ 与任务要求逐字一致 |
| L165 | RASUF 正文 | ✅ 与任务要求逐字一致 |
| L166 | 精确异常（未修改） | ✅ |
| L167 | 退出码派生（未修改） | ✅ |

**与 ADR-0012 D7 对照**：
- RASOF ↔ D7 §3 C3b①：`RACNT == 63` + `MRPTR == 0` → RASOF ✅
- RASUF D1 条件 ↔ D7 §4 D1：`RACNT > 0` 且递归计数 = 0 ✅
- RASUF D4a 条件 ↔ D7 §4 D4a：`RACNT == 0` + `MRPTR == 0` ✅
- RASUF D4b 条件 ↔ D7 §4 D4b：MemRAS 条目无效（递归计数 = 0）✅
- MemRAS 交 OS ↔ D7 §7："无 MemRAS 引用计数，MemRAS 越界不由硬件检测（交 OS）" ✅

**验证证据**：
- `make check`：EXIT=0（80/80 PASS,0 FAIL）
- `check_d7_consistency.py`：EXIT=0（PASS: 全部 D7 对照项通过）
- `grep "MemRAS 引用计数"`：命中1次（L162 注记行，任务指定文本，非正文残留）
- `git diff --name-only`：`.tao/knowledge/adr-0004-test-machine.md`（1项，任务文件为 untracked）
- 反例注入：注入旧语义 → check_rasof_rasuf.py EXIT=1（FAIL）；复原 → EXIT=0（PASS）

**finding 列表**：无

**判决**：全部检查通过，无未修 finding。标「待验收」。
#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立复核，未采信完成区叙述）
**审查范围**：`.tao/knowledge/adr-0004-test-machine.md` §D5.5（+ 本任务书）。工作树中的 `QEMU-030t` / `TESTCASES-020t` 在飞改动**与本任务无关，已排除**。
**审查时间**：2026-09-30

##### 一、重跑记录（全部为审查者亲自执行的输出与真实退出码）

**1) §D5.5 逐字比对（脚本提取任务书目标行 ↔ 实际文件行）**
```
TASK : '- **RASOF（`0x8A`）**：压栈**需溢出**（`RACNT == 63`）且 **MemRAS 未启用**（`MRPTR == 0`）。**MemRAS 容量耗尽不由硬件检测**（交 OS）。[contract-isa §8.6.1]'
ADR  : (完全相同)   IDENTICAL: True
TASK : '- **RASUF（`0x8B`）**：弹栈时栈顶无效（`RACNT > 0` 且栈顶递归计数 = 0）；或 RegRAS 与 MemRAS 均空（`RACNT == 0` 且 `MRPTR == 0`）；或 MemRAS 弹出条目无效（递归计数 = 0）。[contract-isa §8.6.2]'
ADR  : (完全相同)   IDENTICAL: True
note in adr L162: '（2026-09-30 就地修订：依据 ADR-0012 D7，取消 MemRAS 引用计数并重定义 RASOF/RASUF 判据）'  ← 与任务书注记逐字一致
```
判定：两行正文 + 注记 = 任务书指定文本**逐字**一致（以程序抽取比对，排除人工誊写误差）。第 3、4 条（精确异常 / 退出码派生）为 diff 上下文行，**未被改动**。

**2) 越界核验**
```
$ git diff -- .tao/knowledge/adr-0004-test-machine.md | grep -c "^@@"
1
$ git diff --name-only -- adr-0004 adr-0012 spec/ contract-isa.md
.tao/knowledge/adr-0004-test-machine.md
$ git status --porcelain | grep -E "adr-0012|spec/|contract-isa"   → NONE
```
- 改动为**唯一 hunk**（`@@ -159,8 +159,10 @@`），位于 D5.5 内：删 2 行旧正文、增 注记+空行+2 新正文（+4/−2）。
- L49 复位行未动：`| RA \`ra0\`–\`ra63\` | \`0\`（\`ra[63:48] = 0\`，全部条目无效；…`，不在 hunk 内。
- `adr-0012` / `spec/` / `contract-isa.md`：`git diff` 空、`git status` 无记录 ⇒ **0 改动**。
- `git diff --name-only` 出现的其它文件（qemu patches、`ctrl-*.yaml`、`generate_ctrl_jump_call_ret.py`、TESTCASES-020t）均为**并行任务**，与本任务无关。

**3) 残留核验**
```
$ grep -n "MemRAS 引用计数" adr-0004-test-machine.md
162:（2026-09-30 就地修订：依据 ADR-0012 D7，取消 MemRAS 引用计数并重定义 RASOF/RASUF 判据）
$ grep -n "压栈溢出\|弹栈下溢\|引用计数" adr-0004-test-machine.md
162:（…注记行…）
```
判定：**唯一命中为注记行**，正文（RASOF/RASUF）**零残留**旧词。注记必须保留旧术语才能说明"取消了什么"，**可接受**。（任务书验收 #2 写"0 命中"与 #1"注记含该词"自相矛盾；此为任务书内部不一致，非工程师缺陷，见 findings。）

**4) 门控重跑（真实退出码，`> log 2>&1; rc=$?`）**
```
$ make check > /tmp/opencode/SPEC-063t-reviewer-make-check.log 2>&1; echo EXIT=$?
EXIT=0
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  repository checks: PASS
$ python3 tools/spec/check_d7_consistency.py > /tmp/opencode/reviewer_d7.log 2>&1; echo EXIT=$?
EXIT=0
  PASS: 全部 D7 对照项通过
```

**5) 反例门控（审查者自建检查，非复用工程师脚本）**
审查者新建独立检查器 `/tmp/opencode/SPEC-063t-review/check_d55.py`：断言 D5.5 小节内**逐字**含注记 + RASOF + RASUF 三行，且小节内除注记行外无"引用计数"。
```
1) 基线（当前仓库内容）      : PASS: D5.5 逐字 + 无正文残留        EXIT=0
2) 注入旧语义（RASOF 行改回）: FAIL: 2 项                          EXIT=1
     - 缺 RASOF 逐字行
     - L164 正文残留旧词: - **RASOF（`0x8A`）**：RegRAS 压栈溢出（调用深度超过 63），或 MemRAS 引用计数溢出 [contract-isa §8.6.1]。
   （`diff pristine copy` 证实注入确实改动 L164，非空注入）
3) 复原（cp 回 pristine）     : PASS: D5.5 逐字 + 无正文残留        EXIT=0
   diff pristine.md.bak copy.md → IDENTICAL（空输出）
```
反例在 `/tmp` 副本内完成，**仓库工作树未被污染**（事后重跑 `git diff` 仅 1 hunk，见上）。检查器具备**可达的 FAIL 路径**。

##### 二、与 ADR-0012 D7 对照（逐条）

| adr-0004 §D5.5 新表述 | ADR-0012 D7 出处 | 一致性 |
|---|---|---|
| RASOF：`RACNT == 63` 且 `MRPTR == 0`；MemRAS 容量耗尽交 OS | D7 §3 **C3b①**（`RACNT == 63` → ① `MRPTR == 0` → **RASOF**） | ✅ |
| RASUF：栈顶无效（`RACNT > 0` 且栈顶递归计数 = 0） | D7 §4 **D1**（`RACNT > 0` 且 `ra63[63:48] == 0` → RASUF） | ✅ |
| RASUF：RegRAS 与 MemRAS 均空（`RACNT == 0` 且 `MRPTR == 0`） | D7 §4 **D4a**（`RACNT == 0` → `MRPTR == 0` → RASUF） | ✅ |
| RASUF：MemRAS 弹出条目无效（递归计数 = 0） | D7 §4 **D4b**（读 `MRPTR` 处条目，递归计数 = 0 → RASUF） | ✅ |
| MemRAS 容量耗尽不由硬件检测（交 OS） | D7 §7（"无 MemRAS 引用计数，MemRAS 越界（容量耗尽）不由硬件检测（交 OS）"） | ✅ |

引用可定位：`[contract-isa §8.6.1]`/`[§8.6.2]` 在 `contract-isa.md` L775/L783 存在，且其 C1–C3b / D1–D4b 内容已与 D7 对齐。

##### 三、约束核验（逐条）

| # | 约束 | 结果 |
|---|---|---|
| 1 | 只改 D5.5（≤3 行 + 注记） | ✅ 唯一 hunk；正文 2 行替换 + 注记（+1 空行分隔）= 符合 |
| 2 | 不改 L49 复位行 | ✅ 未在 hunk 内，L49 原样 |
| 3 | `adr-0012` / `spec/` / `contract-isa.md` / QEMU / 向量不改 | ✅ 就本任务而言 0 改动（其余改动属并行任务） |
| 4 | 不改其它已 Accepted decision 正文 | ✅ 单一 hunk |
| 5 | `make check` EXIT=0 | ✅ 审查者重跑 EXIT=0（80/80） |
| 6 | `check_d7_consistency.py` EXIT=0 | ✅ 审查者重跑 EXIT=0 |
| 7 | 反例门控 | ✅ 审查者自建检查器可 FAIL 可复原 |

##### 四、findings（均非阻断）

1. **任务书内部不一致（非工程师责任）**：验收 #1 要求注记（含"取消 MemRAS 引用计数"）与 #2 要求 `grep` 0 命中相互矛盾。工程师取注记优先、正文零残留，与任务书"修改内容"段一致，**可接受**。
2. **工程师补充检查器偏弱**：`/tmp/opencode/SPEC-063t/check_rasof_rasuf.py` 仅检查正文行"不含旧词"，若整行被删亦会 PASS（缺少"须含新逐字文本"的正向断言）。审查者已用独立检查器（含正向逐字断言）补足，故**不阻断**；建议后续此类"就地修订"验收脚本同时断言"含新文本"与"无旧残留"。
3. **L49 残留旧位域表述**：L49 仍写 `ra[63:48] = 0`，未反映 D7 的 `[63:54] SBZ / [53:48] RACNT` 拆分。任务书**明确排除** L49（"本次不动，如需另议"），故不计入本次验收；建议另开任务处置。
4. **工程师完成区表述**：其"`make check` EXIT=0"在审查者重跑下**可复现**（真实 EXIT=0）。期间因并行任务 `validate-vectors` 曾短暂变红一事工程师未说明，属"表述可更严谨"，**非阻断**。
5. 跨模块耦合核查：`tools/testcases/generate_ctrl_jump_call_ret.py`（TESTCASES-020t 在飞）仅在 citation 字符串中引用 `ADR-0004 D5.5`，**不解析** §D5.5 正文，本次改动不破坏其解析；`make check`（含 `validate-vectors`）通过佐证。

##### 五、判决

**Accepted**。
- 验收命令块在审查者**独立重跑**下全部通过：`make check` EXIT=0、`check_d7_consistency.py` EXIT=0。
- §D5.5 两行 + 注记 = 用户确认的**逐字**文本（程序比对 IDENTICAL）；第 3、4 条未动。
- 无越界改动；约束逐条守住；反例门控由审查者自建检查器独立证实（FAIL → 复原 PASS）。
- findings 均为非阻断（任务书内部矛盾、补充脚本偏弱、被明确排除的 L49、完成区措辞）。

> 注：本任务书为**未跟踪**文件；本审阅记录仅为审查证据，最终接受决定由架构师/用户终审。
