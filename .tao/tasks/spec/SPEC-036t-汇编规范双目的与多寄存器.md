# SPEC-036t: 更新汇编规范——双目的语法 + 多寄存器组记法 + `{...}` 速查表

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-035t`（ADR 已立，decision 已确认）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`docs/spec/assembly-language.md`（v1，状态行写「v1」）、用户确认的 ADR-0013 decision
- 输出：`docs/spec/assembly-language.md`（更新后，状态行改为 **v1.1** 并加修订标记，用户已确认 2026-09-28）
- 约束：
  - 改 §4/§5 及新增速查表
  - §1–§3/§6–§10/§12 **不改**
  - §11（实现状态）/附（与上游 spec/ 的关系）/L6（说明行）**允许更新**以反映本次变更
  - 版本号仍为 0.5.4（加表不改版本号）；**状态行**（L3）从「v1」更新为「**v1.1**」并加修订标记（如「修订：双目的/多寄存器语法，2026-09-28」）——用户 2026-09-28 确认
  - `spec/SimRISC-01~12` 内的 ` ```simrisc ` 代码块是**字段级操作数定义**（如 `ld.ub rdha, rbhb, imms12`），非汇编示例——**保留不动**，与嵌入的汇编表格并存（表格是「汇编书写形式」，代码块是「编码字段级语义」，两者分工明确）

## 修改内容

### 1. §4.1 EBNF 更新（覆盖 `{...}` 四种用途）

现有 EBNF：
```
寄存器组   ::= "{" 单寄存器 "}" | "{" 起 ":" 止 "}"
```

更新为：
```
寄存器组       ::= "{" 寄存器列表 "}" | "{" 起 ":" 止 "}"
寄存器列表     ::= 单寄存器 ("," 单寄存器)*
条件寄存器组   ::= 寄存器组 "?"
双目的寄存器对 ::= "{" 单寄存器 "," 单寄存器 "}"   // 恰好 2 个，无 ?
```

说明：`{rd3}` 匹配「单元素寄存器列表」；`{rd8, rd0}` 匹配「双元素寄存器列表」；`{rd8, rd0}?` 匹配「条件寄存器组」。

### 2. §4 之后新增「`{...}` 用途速查表」

| 用途 | 语法 | 示例 | 区分标记 |
|------|------|------|---------|
| 条件寄存器组 | `{reg, …}?` | `{rd3}?`、`{rd8, rd0}?` | `?` 紧跟 `}` |
| 双目的寄存器对 | `{reg, reg}` | `{rd8, rd9}` | 无 `?`，恰好 2 个 |
| 多寄存器组（范围） | `{start:end}` | `{rd8:rd11}` | `:` 分隔 |
| 多寄存器组（单寄存器） | `{reg}` | `{rd8}` | count=1 |

### 3. §4.2 规则补充

**双目的指令规则**（新增段落）：
- `rrrr` 格式中有 6 条指令（`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`）的 `rdha` 和 `rdhb` 均为 dst
- 书写格式：`助记符 {rdHA, rdHB}, rdHC, rdHD`
- 花括号内逗号后加空格（与整体风格一致）

**多寄存器组记法规则**（扩展现有段落）：
- 现有规则仅覆盖 `ldm.*`/`stm.*`（目的/源寄存器组）
- 扩展至：寄存器复制指令（`ra2rd`/`rb2rb`/`rb2rd`/`rd2ra`/`rd2rb`/`rd2rd`/`rd2rf`/`rf2rd`，8 条）和浮点格式转换指令（`ft2fo`/`fo2ft`/…/`ut2fo`，20 条）
- 规则统一表述：「组记法用于指令的寄存器操作数（源或目的），当 `immu6` 表示连续寄存器个数时」
- 示例：`ra2rd {rd8:rd10}, {ra1:ra3}`、`ft2fo {rf4:rf6}, {rf8:rf10}`
- 注意：`ldm` 的组是**目的**（内存→寄存器），`stm` 的组是**源**（寄存器→内存）

### 4. §5 指令语法表更新

`rrrr` 格式拆成 3 行：

| 格式类 | 语法（记法） | 示例 |
|---|---|---|
| `rrrr`（双目的） | `助记符 {dst1, dst2}, src1, src2` | `add.uo {rd8, rd9}, rd10, rd11` |
| `rrrr`（cs.n/z/p） | `助记符 {cond}?, dst, src1, src2` | `cs.n {rd1}?, rd2, rd3, rd4` |
| `rrrr`（cs.eq/ne） | `助记符 {cond1, cond2}?, dst, src` | `cs.eq {rd8, rd0}?, rd9, rd10` |

`orri` 格式的多寄存器指令加注释行：

| 格式类 | 语法（记法） | 示例 |
|---|---|---|
| `orri`（块赋值/格式转换） | `助记符 {dst:…}, {src:…}` | `ra2rd {rd8:rd10}, {ra1:ra3}` |

### 5. §4.3 示例更新

补充双目的和多寄存器组的示例行。

### 6. §11 更新

新增行：「**双目的/多寄存器新记法**（`{rdHA,rdHB}`/`{start:end}`）| ❌ 待实现」。

### 7. 附更新

将「上游 `spec/`（SimRISC 系列）**暂不修改**」改为「上游 `spec/`（SimRISC 系列）可由 spec 模块任务按 ADR-0012 D4 修改」。

### 8. 「spec/ 只读」表述同步

以下文件包含「spec/ 只读」相关表述，需同步更新：

| 文件 | 行 | 当前表述 | 更新为 |
|------|-----|---------|--------|
| `AGENTS.md` | L52 | `spec/ # 原始规范文档（只读）` | `spec/ # 原始规范文档（spec 模块任务可改，见 ADR-0012 D4）` |
| `.tao/knowledge/MEMORY.md` | L24 | `spec/ \| 11 份原始规范文档（只读）` | `spec/ \| 12 份规范文档（spec 模块任务可改）` |
| `.tao/knowledge/MEMORY.md` | L30 | `docs/spec/ \| v5 规范层（…；与只读的上游 spec/ 区分）` | 删除「只读的」定语 |
| `docs/m2-spec-planning.md` | L5 | `spec/（上游规范，只读）` | `spec/（上游规范，spec 模块任务可改）` |
| `docs/m2-spec-planning.md` | L92 | `spec/ 只读，不改上游` | 删除「只读」，改为「spec 模块任务可改」 |
| `docs/m2-spec-planning.md` | L150 | `与只读的 spec/ 区分` | 删除「只读的」 |
| `docs/spec/assembly-language.md` | L6 | `本规范不修改上游 spec/` | 改为「本规范按 ADR-0012 D4 由 spec 模块任务修改」 |
| `docs/spec/assembly-language.md` | §11 | `上游 spec/ 同步：待安排` | 更新为「已由 SPEC-034k 系列任务安排」 |
| `docs/spec/assembly-language.md` | 附 | `上游 spec/ 暂不修改` | 改为「可由 spec 模块任务按 ADR-0012 D4 修改」 |

## 验收标准

1. `docs/spec/assembly-language.md` 的版本号仍为 0.5.4
2. 状态行（L3）为 **v1.1** 且含修订标记（用户 2026-09-28 确认）
3. §4.1 的 EBNF 可推导 4 类示例：
   - `{rd3}` → 寄存器组（单元素列表）
   - `{rd8, rd9}` → 寄存器组（双元素列表，双目的）
   - `{rd8, rd0}?` → 条件寄存器组
   - `{rd8:rd11}` → 寄存器组（范围）
4. §4 包含「`{...}` 用途速查表」（4 行）
5. §4.2 包含双目的指令规则和扩展的多寄存器组记法规则
6. §5 的 `rrrr` 拆成 3 行（双目的 / cs.n/z/p / cs.eq/ne）
7. §5 的 `orri` 包含块赋值/格式转换的组记法说明
8. §11 包含双目的/多寄存器新记法行
9. 附反映 `spec/` 可修改
10. §1–§3/§6–§10/§12 内容未改动（可 `git diff` 比对）
11. 所有新增内容与 ADR-0013 的 decision 一致
12. **「只读」表述已清除**：`grep -rn '只读' AGENTS.md .tao/knowledge/MEMORY.md docs/m2-spec-planning.md docs/spec/assembly-language.md` 返回空（或仅含历史记录/已完成任务的引用）
13. `spec/SimRISC-01~12` 内 ` ```simrisc ` 代码块**未改动**（字段级定义保留）
14. `make check` 通过（无回归）

## 完成区
**测试结果**：`make check` EXIT=0，全 PASS（manifest validation PASS / validate_vectors 178/178 / spec drift PASS / check-patch-tree 67 patches OK / check_issues 0 blocking / repository checks PASS）
**修改文件**：
- `docs/spec/assembly-language.md`：L3 状态行 v1→v1.1 + 修订标记；L6 说明行；§4.1 EBNF 扩展；§4.2 双目的规则 + 多寄存器组记法扩展；§4.3 示例 +3 行；新增 `{...}` 用途速查表（4 行）；§5 rrrr 拆 3 行 + orri 注释行；§11 +1 行 + 上游 spec 同步更新；附更新
- `AGENTS.md`：L52 spec/ 目录注释
- `.tao/knowledge/MEMORY.md`：L24 spec/ 行 + L30 docs/spec/ 行
- `docs/m2-spec-planning.md`：L5 关联行 + L92 小节标题 + L150 落点行
**验收结果**：
- 验收标准 #1：版本号 0.5.4 ✓（README.md 未变）
- 验收标准 #2：状态行 v1.1 + 修订标记 ✓（L3 diff 确认）
- 验收标准 #3：§4.1 EBNF 可推导 4 类示例 ✓（说明段列出）
- 验收标准 #4：速查表 4 行 ✓（§4 后插入）
- 验收标准 #5：§4.2 含双目的规则 + 多寄存器组记法扩展 ✓
- 验收标准 #6：§5 rrrr 拆 3 行 ✓（双目的/cs.n-z-p/cs.eq-ne）
- 验收标准 #7：§5 orri 含块赋值/格式转换行 ✓
- 验收标准 #8：§11 含双目的/多寄存器新记法行 ✓
- 验收标准 #9：附反映 spec/ 可修改 ✓
- 验收标准 #10：§1–§3/§6–§10/§12 未改动 ✓（git diff 确认）
- 验收标准 #11：与 ADR-0013 decision 一致 ✓（D1/D5/D6/D7 均落地）
- 验收标准 #12：只读表述已清除 ✓（grep 仅剩参考仓库引用）
- 验收标准 #13：spec/SimRISC-01~12 未改动 ✓（git diff 不含 spec/）
- 验收标准 #14：make check 通过 ✓（EXIT=0）
**新发现/坑**：
- MEMORY.md L24 原写「11 份」，任务书要求改为「12 份」——但 spec/ 实际仍为 11 份（SimRISC-00~04 + DADAO-11/12/13/21/22/23）；task 书表格写「12 份」可能是笔误，已按任务书执行。建议主会话确认 spec/ 实际文件数。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：4 文件 6 处编辑 + 新增速查表

**逐项审查**：

1. **L3 状态行**：v1→v1.1 + 修订标记「修订：双目的/多寄存器语法，2026-09-28」——与任务书 §接口规范 一致 ✓
2. **L6 说明行**：「不修改」→「按 ADR-0012 D4 由 spec 模块任务修改」——与任务书 §8 表格一致 ✓
3. **§4.1 EBNF**：新增 `寄存器列表`、`条件寄存器组`、`双目的寄存器对` 三条产生式；原 `寄存器组` 改为引用 `寄存器列表`；`单寄存器` 保留——可推导 4 类示例：`{rd3}`(单元素列表) / `{rd8,rd9}`(双元素列表+双目的对) / `{rd8,rd0}?`(条件组) / `{rd8:rd11}`(范围) ✓
4. **§4.2 规则**：新增「双目的指令」段（6 条 rrrr 指令、书写格式、逗号后空格）；新增「多寄存器组记法扩展」段（8+28 条 orri 指令、源+目的都用范围）；原 ldm/stm 段补充「ldm 组=目的、stm 组=源」——与 ADR-0013 D1/D5/D6 一致 ✓
5. **§4.3 示例**：新增 3 行（双目的 add.uo / 多寄存器块赋值 ra2rd / 多寄存器格式转换 ft2fo）——与 §4.2 规则配套 ✓
6. **速查表**：4 行（条件组/双目的/范围/单寄存器），区分标记列完整——与 ADR-0013 D1 一致 ✓
7. **§5 表格**：原 `rrrr` 1 行拆为 3 行（双目的/cs.n-z-p/cs.eq-ne）；新增 `orri`（块赋值/格式转换）1 行——与任务书 §4 表格一致 ✓
8. **§11**：新增「双目的/多寄存器新记法」行；上游 spec/ 同步行从「待安排」改为「已由 SPEC-034k 系列任务安排」——与任务书 §6 一致 ✓
9. **附**：「暂不修改」→「可由 spec 模块任务按 ADR-0012 D4 修改」——与任务书 §7 一致 ✓
10. **AGENTS.md / MEMORY.md / m2-spec-planning.md**：6 处只读表述全部更新——`grep '只读'` 仅剩参考仓库引用（非 spec/）✓

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| MEMORY.md L24 「11 份」→「12 份」可能与实际 spec/ 文件数不符（spec/ 仍为 11 份） | ⏸延后 | 按任务书执行 | `ls spec/` 可核对；建议主会话确认 |
| §1–§3/§6–§10/§12 未改动验证 | ✅已验 | 无 | `git diff` 仅含 §4/§5/§11/附/L3/L6 |
| spec/SimRISC-01~12 未改动验证 | ✅已验 | 无 | `git diff --name-only` 不含 `spec/` |

**判决**：所有 finding 已处置，标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑，未采信完成区转述）

**审查范围**：`docs/spec/assembly-language.md` 全量、`AGENTS.md` / `.tao/knowledge/MEMORY.md` / `docs/m2-spec-planning.md` / `README.md` 的 diff、ADR-0013、`contracts/opcodes.yaml`。

##### 1. 重跑记录（命令 + 真实输出/退出码）

**(a) `make check`（验收标准 #14）**
```
$ make check > /tmp/opencode/SPEC-036t-makecheck.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```
日志尾部（真实）：
```
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
spec drift check: PASS            (contract-abi/elf/isa 全 PASS，错误 0 个；README 版本表 SimRISC=0.5.4)
check-patch-tree: 2 component(s), 67 patches OK
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
```
→ 与完成区「EXIT=0，全 PASS」一致。

**(b) 只读表述清除（验收标准 #12；`AGENTS.md` 验收要点）**
```
$ grep -rn 'spec/.*只读\|只读.*spec/' AGENTS.md .tao/knowledge/MEMORY.md docs/m2-spec-planning.md docs/spec/assembly-language.md
EXIT=1                      # 无任何匹配
$ grep -rn '只读' AGENTS.md .tao/knowledge/MEMORY.md docs/m2-spec-planning.md docs/spec/assembly-language.md
AGENTS.md:9:  ... 只读工作树检出在 .dadao/<id>/ ...
AGENTS.md:28: ... 参考仓库仅作只读溯源/对照 ...
MEMORY.md:31: ... 参考仓库只读工作树 .dadao/<id>/ ...
EXIT=0
```
→ 仅剩 3 处「参考仓库（`.dadao/`）」表述，与 spec/ 无关；符合 #12「或仅含历史记录/已完成任务的引用」。反例门控：该 grep 非恒真——`spec/.*只读` 模式在当前树返回 1，而泛化的 `只读` 模式返回 0，说明匹配逻辑有效。

**(c) spec/ 代码块未改动（验收标准 #13）**
```
$ git status --porcelain spec/ | wc -l
0
```
→ `spec/` 完全未进入本次改动（`git diff --name-only` 也不含 `spec/`）。`spec/SimRISC-01~12` 的 ```simrisc 字段级代码块保留。

**(d) §1–§3/§6–§10/§12 未改动（验收标准 #10）**
```
$ git diff -U0 -- docs/spec/assembly-language.md | grep '^@@'
@@ -3 +3 @@         # 头部 L3 状态行
@@ -6 +6 @@         # 头部 L6 说明行
@@ -87,3 +87,5 @@   # §4.1
@@ -91,0 +94,2 @@   # §4.1
@@ -95,0 +100 @@    # §4.2
@@ -98,0 +104,2 @@   # §4.2
@@ -108,0 +116,12 @@ # §4.3 + 速查表
@@ -118 +137,3 @@   # §5 rrrr
@@ -125,0 +147 @@    # §5 orri
@@ -200,0 +223 @@    # §11
@@ -206 +229 @@      # §11
@@ -223 +246 @@      # 附
```
旧章节行域：§1=11–19、§2=20–49、§3=50–82、§6=143–151、§7=152–167、§8=168–175、§9=176–187、§10=188–194、§12=210–220。
→ 所有 hunk 落点均在第 3/6 行（头部）或 §4/§5/§11/附 内，**无任何 hunk 落入 §1–§3/§6–§10/§12**。

**(e) 指令集独立 oracle 重算（验收要点「6 条双目的 / 28 条多寄存器」）**
用 `contracts/opcodes.yaml`（254 条）独立重算，不采信规范文本：
```
dual-dest (rrrr，rdha 与 rdhb 均 dst) = 6  →  与规范所列 6 条一致
  add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so
寄存器复制 (orri)   = 8   → ra2rd/rb2rb/rb2rd/rd2ra/rd2rb/rd2rd/rd2rf/rf2rd，全部 format=orri ✓
浮点格式转换 (orri) = 20  → ft2fo/ft2ft/fo2ft/.../ut2fo，全部 format=orri ✓
多寄存器合计 = 8 + 20 = 28 ✓
rrrr 格式共 16 条 = 6(双目的) + 6(cs.n/z/p) + 4(cs.eq/ne) → 与 §5 拆 3 行覆盖范围吻合
```

**(f) 份数核查（特别核查项）**
```
$ ls spec/*.md | wc -l
19          # 13(SimRISC-00~12) + 6(DADAO-11/12/13/21/22/23)
$ for f in spec/SimRISC-*.md spec/DADAO-*.md; do ... 版本头 ...; done
SimRISC-00~12 → 0.5.4；DADAO-11/21 → 0.9.2；DADAO-12/22 → 0.7.1；DADAO-13/23 → 0.1.2
```
→ MEMORY.md L24 `19 份规范文档（SimRISC-00~12 + DADAO-11~23）`、README.md L3、m2-spec-planning L69 的 19 份及版本归属**均准确**（19 个 .md 全部带版本头）。工程师原写「12 份」为错，现值 19 正确。

##### 2. 文件内容正确性（逐条阅读）

- **L3 状态行**：`生效（v1.1，2026-09-25，用户审核通过；修订：双目的/多寄存器语法，2026-09-28）`——v1.1 + 修订标记齐备 ✓
- **L6 说明行**：改为「按 ADR-0012 D4 由 spec 模块任务修改上游 spec/」✓
- **§4.1 EBNF**：新增 `寄存器列表`/`条件寄存器组`/`双目的寄存器对` 三产生式；`寄存器组 ::= "{" 寄存器列表 "}" | "{" 起 ":" 止 "}"`；4 类示例（`{rd3}`/`{rd8, rd9}`/`{rd8, rd0}?`/`{rd8:rd11}`）逐条可推导；无遗留旧名 `条件标记 ::=` ✓
- **§4.2**：双目的规则（6 条 rrrr、`助记符 {rdHA, rdHB}, rdHC, rdHD`）；多寄存器组记法扩展（8 条复制 + 20 条格式转换、源+目的都用 `{start:end}`、示例 `ra2rd {rd8:rd10}, {ra1:ra3}`/`ft2fo {rf4:rf6}, {rf8:rf10}`）；补 `ldm` 组=目的 / `stm` 组=源 ✓
- **速查表**：4 行（条件组/双目的/范围/单寄存器），与 ADR-0013 D1 表逐字一致 ✓
- **§5**：`rrrr` 由 1 行拆 3 行（双目的/cs.n/z/p/cs.eq-ne），示例与 §4.3 一致；`orri` 保留原行并新增「块赋值/格式转换」行 ✓
- **§11**：新增「双目的/多寄存器新记法 ❌ 待实现」行；上游 spec/ 同步行改为「已由 SPEC-034k 系列任务安排…可由 spec 模块任务按 ADR-0012 D4 修改」✓
- **附**：「暂不修改」→「可由 spec 模块任务按 ADR-0012 D4 修改」✓
- **ADR-0013 一致性**：D1（4 用途表）、D5（源+目的组记法）、D6（`?` 消歧）、D7（spec/ 可改）均在规范中落地；D2/D3/D4 维持 v1 原状 ✓

##### 3. 约束核验（逐条）

| # | 约束 | 结论 | 证据 |
|---|------|------|------|
| 1 | 版本号仍 0.5.4 | ✓ | `make check` spec drift PASS；README 版本表 SimRISC=0.5.4 未动 |
| 2 | L3 = v1.1 + 修订标记 | ✓ | diff @@ -3；L3 现文 |
| 3 | EBNF 可推导 4 类示例 | ✓ | §4.1 逐条推导 |
| 4 | §4 含 4 行速查表 | ✓ | L120–127 |
| 5 | §4.2 双目的 + 多寄存器组规则 | ✓ | L100、L105 |
| 6 | §5 `rrrr` 拆 3 行 | ✓ | L137–139 |
| 7 | §5 `orri` 含块赋值/格式转换 | ✓ | L147 |
| 8 | §11 含新记法行 | ✓ | L223 |
| 9 | 附反映 spec/ 可修改 | ✓ | L246 |
| 10 | §1–§3/§6–§10/§12 未改 | ✓ | hunk 落点比对（见 1(d)） |
| 11 | 与 ADR-0013 D1–D7 一致 | ✓ | 逐条比对 |
| 12 | 「只读」表述清除 | ✓ | grep（见 1(b)） |
| 13 | `spec/SimRISC-01~12` 代码块未改 | ✓ | `git status spec/` = 0 |
| 14 | `make check` EXIT=0 | ✓ | 独立重跑（见 1(a)） |

##### 4. 非阻断观察（供架构师/主会话定夺，不影响本次判决）

1. **完成区与工作树已不匹配**：完成区「#1 版本号 0.5.4 ✓（**README.md 未变**）」与现状不符——`README.md:3` 已由 11 份改为 19 份（主会话在工程师完成后修正份数）。同时完成区「修改文件」清单未列 `README.md` 与 `m2-spec-planning.md` 的份数修正。属主会话后续编辑所致，非工程师虚假陈述，但完成区文字需按现状更正。
2. `docs/m2-spec-planning.md:96` 仍写「11 份文档 `MUST`/`SHALL` = 0」，与同文 L69 的「19 份」并存；系 2026-09-22 旧分析陈述，**超出 SPEC-036t 范围**，建议后续一并校正或标注时点。
3. `docs/spec/assembly-language.md:4` 仍称本规范语法决策「拟由新 ADR…冻结（**待立**）」，而 ADR-0013 已 Accepted——该行不在本任务 §8 授权改动清单内，属遗留陈旧引用，建议后续任务更新。

##### 5. 判决

**Accepted**

- 验收标准 #1–#14 在我独立重跑/独立重算下**全部通过**，命令的输出与退出码均与完成区一致（`make check` EXIT=0；只读 grep 无 spec/ 残留；spec/ 零改动；§1–§3/§6–§10/§12 零 hunk）。
- 6 条双目的、8 条复制 + 20 条格式转换（=28 多寄存器）经 `contracts/opcodes.yaml` 独立重算确认无误。
- 特别核查项：MEMORY.md 现值为 **19 份且准确**（19 个 .md 与版本头逐一核对通过）；工程师原「12 份」错误已被主会话修正。
- 无契约/spec 被弱化以凑绿，`make check` 为独立门控。
- 上述「非阻断观察」1–3 为完成区文字陈旧与范围外遗留，不构成验收失败，交架构师终审时一并处置。
