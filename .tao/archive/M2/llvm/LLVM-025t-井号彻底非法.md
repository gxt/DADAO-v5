# LLVM-025t: `#` 彻底非法（`AllowAdditionalComments = false`）

**模块**：llvm
**项目里程碑**：M2
**依赖**：`LLVM-024t`（注释符 `#`→`;`，已 `c37b3c7`）
**ADR**：`ADR-0013 D9`（`#` 留给 C 预处理器；不再作注释）
**状态**：已验证

## 背景

`LLVM-024t` 把注释符改为 `;`，但 `DADAOMCAsmInfo` **未设** `AllowAdditionalComments = false`（LLVM 默认 **true**，`AsmLexer.cpp:821-838`）⇒ **行首 `# …` 仍被静默当注释吞掉**（`llvm-mc` EXIT=0），仅行内/操作数位的 `#` 报错。这使 `ADR-0013 D9`「`#` 不作注释」**不彻底**，并令 `assembly-language.md §9`「非法记号（如 `#`）」表述**不自洽**（reviewer 在 `LLVM-024t` 指出）。

## 交付物

1. **LLVM 补丁** `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`：
   - 在 `CommentString = ";";` 附近设 **`AllowAdditionalComments = false;`**（使 `#` 在**任意位置**都不再是注释）。
2. **重建 `llvm-mc`**（`make build-mc`；改 1 个 `.cpp` ⇒ 增量，秒级–1 分钟，`JOBS=8`）。
3. **文档**：`docs/spec/assembly-language.md §9` 的非法记号示例 —— 若 `#` 现已**无条件非法**则示例**正确**（可**加一句**说明：`#` 为 C 预处理器指令符，纯汇编中非法；由 cpp 先行处理）。**不改变 §2.2 的注释规则** ✗。

## 范围外 ✗

- 不改 `spec/` 正文其它内容、`tests/vectors/**`、LLVM 其它补丁；
- 不改历史文件；**不做** 3A/3B（另立任务）。

## 验收标准（须真实可失败）

1. **`#` 无条件非法**：`printf '# foo\nadd.si rd8, 1\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null` ⇒ **非零**（且报错）；`printf '; foo\nadd.si rd8, 1\n' | …` ⇒ **EXIT=0** ✓。
2. **承重反例（含重建）** ⚠️：把 `AllowAdditionalComments` 改回 `true`（或删该行）**并重建** ⇒ 行首 `# foo` **静默通过（EXIT=0）**；复原 **并重建** ⇒ 回非零。**只还原源码不算还原** ✗。
3. **无回归**：lit MC **22/22** + E2E **3/3**；`check_lit_bytes` 53；`make check` **EXIT=0** ✓。
4. **文档一致**：`assembly-language.md §9` 与 §2.2 不再矛盾（`#` 非法 + `;` 为注释）✓。
5. **未越界**：`git diff --name-only` = 该补丁 +（若加）`assembly-language.md` + 任务书；历史文件干净 ✓。
6. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：
**修改文件**：
**`#` 前后行为（真实退出码）**：
**承重反例（含重建）**：
**lit / make check 真实退出码**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收

**结论：Accepted（工程师达标）** —— 验收标准 1–6 在审查者独立重跑下全部通过；第 1 点（`#` 无条件非法）与第 3 点（承重反例含重建）**均 PASS**（见下）。**唯一缺陷为记录缺失**：任务书「完成区」「engineer 自审」「状态（仍为 `待开始`）」均未填写/未更新——属过程记录缺口，非技术缺陷（依 `AGENTS.md`「子代理返回异常处理」：产出已落盘 ⇒ 视为完成）。

**审查范围**：任务书全文、`git diff` 全量、补丁逐行 + hunk 头计数 + 干净 apply、`.work/source` 源码态、二进制 sha、lit MC/E2E、`check_lit_bytes`、`make check`、§2.2/§9 文档、`ADR-0013 D9`；**亲自注入反例 + `make build-mc` 重建 + 复原 + 重建**。证据留档 `/tmp/opencode/LLVM-025t-r1/`。

##### 一、重跑记录（我方真实输出 / 退出码）

| # | 命令 | 真实结果 |
|---|------|---------|
| R1 | `printf '# foo\nadd.si rd8, 1\n' \| llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null; echo $?` | **EXIT=1**（非零）且报错：`<stdin>:1:1: error: unexpected token at start of statement` ✓ |
| R2 | `printf '; foo\nadd.si rd8, 1\n' \| llvm-mc …` | **EXIT=0**（静默）✓ |
| R2b | 位置穷尽：行内 `add.si rd8, 1 # tail` ⇒ **EXIT=1**；操作数位 `add.si rd8, # 1` ⇒ **EXIT=1**；`;` 行首/行内/多行 ⇒ **EXIT=0**；无注释纯汇编 ⇒ **EXIT=0** | ✓ |
| R3 | `grep -n '^@@' <patch>` + 计数 `+` 行 | hunk 头 `@@ -0,0 +1,40 @@`，正文 `+` 行 **40** ⇒ **40=40 一致**（工程师自审曾发现 `37→40`，当前已一致）✓ |
| R3b | 补丁正文逐行 vs `.work/source/.../DADAOMCAsmInfo.cpp` | `diff` 全等（`PATCH_BODY_MATCHES_SOURCE=yes`，40 行）✓ |
| R3c | `git -C .work/source/llvm-project apply --check --reverse <patch>` | **RC=0**（补丁与已应用态一致 ⇒ 可干净 apply）✓；正向 `apply --check` RC=1（`already exists`，符合“已应用”预期）✓ |
| R3d | `grep AllowAdditionalComments`（补丁 + 源码） | 两处均为 `AllowAdditionalComments = false;` ✓ |
| R4 | `make check-lit` | **EXIT=0**，`Total Discovered Tests: 25 / Passed: 25 (100.00%)`；MC **22** + E2E **3**，`FAIL=0` ✓ |
| R5 | `python3 tools/llvm/check_lit_bytes.py` | **EXIT=0**，`check_lit_bytes: 53 patterns OK` ✓ |
| R6 | `JOBS=8 make check` | **EXIT=0**；`总计: 80 项 \| PASS: 80 \| FAIL: 0`、`Results: 146 total, 146 passed, 0 failed`、`repository checks: PASS` ✓ |
| R7 | `git diff --name-only` | 恰两项：`components/.../DADAOMCAsmInfo.cpp.patch` + `docs/spec/assembly-language.md`；任务文件为 untracked（`??`）✓ |
| R8 | `git status --short spec/ tests/vectors/ components/` | 仅该补丁被改；`spec/` 其它正文、`tests/vectors/**`、其余 LLVM 补丁、历史文件**均未动** ✓ |

##### 二、承重反例（reviewer 亲自注入 + 重建 + 复原 + 重建）

- **基线**：源码 `AllowAdditionalComments = false;`，二进制 sha256 = `abfe11a3e31a6ab7a9ccfe920aa1030976582860cd64be0215a91f57f21a5cba`；`# foo` ⇒ EXIT=1（R1）。
- **注入**：`.work/source/.../DADAOMCAsmInfo.cpp` 改 `false` → `true`（`grep` 确认仅此一行变），`JOBS=8 make build-mc` **EXIT=0**（ninja 重建 4 目标，真编译 `.o`）→ 二进制 sha **`fe1113ed688edbcf8d7354608dc723ba8f5d321ba3d266b4807ccdccfc9d6d43`**（证明重编译真实生效）。
  - `printf '# foo\nadd.si rd8, 1\n' | llvm-mc …` ⇒ **EXIT=0，无任何输出（静默吞掉）** ✓ —— 正是本任务要消除的行为。
- **复原**：`cp` 回备份源码（`sha256sum` 与备份逐字节同 = `940c9dc4…8e4d3`）→ `JOBS=8 make build-mc` **EXIT=0** → 二进制 sha 回到 **`abfe11a3…5cba`，与基线 byte-identical** ✓；`# foo` ⇒ **EXIT=1**（报错，回非零）✓。
- 复原后 `.work/source` 源码态与备份一致，`.work` 不入 git ⇒ 未污染工作区。

##### 三、验收标准逐条核验

| 验收项 | 结论 |
|--------|------|
| 1. `#` 无条件非法（行首/行内/操作数）⇒ 非零；`;` ⇒ EXIT=0 | ✓（R1/R2/R2b） |
| 2. 承重反例：改回 `true` + 重建 ⇒ `#` 静默 EXIT=0；复原 + 重建 ⇒ 回非零 | ✓（§二，独立复现，含重建与 byte-identical 复原） |
| 3. 无回归：lit MC 22/22 + E2E 3/3；`check_lit_bytes` 53；`make check` EXIT=0 | ✓（R4/R5/R6） |
| 4. 文档一致：§9 与 §2.2 不矛盾，§2.2 未改 | ✓（见 §四） |
| 5. 未越界：`git diff --name-only` = 补丁 + `assembly-language.md`（+ 任务书） | ✓（R7/R8） |
| 6. 退出码用 `cmd >log 2>&1; rc=$?`；命令失败即停 | ✓（本审查全程照此；无命令缺失） |

##### 四、文档一致性（§9 vs §2.2）

- **§2.2 未改**：`git diff docs/spec/assembly-language.md` 唯一改动在 §9 一行，§2.2 原文未动（`;` 起至行尾为注释 / `#` **不是**注释）。
- **§9 新增说明**：`非法记号（如 `#`、`wp4`）——`#` 为 C 预处理器指令符…纯汇编中**无条件非法**（`AllowAdditionalComments = false`）…`。
- **判定不矛盾**：§2.2 陈述「`#` 不作注释（留给 cpp）」，§9 陈述「作记号的 `#` 非法」；两阶段（预处理器 / 汇编器）分属，可同真。且本次实测**行首 `#` 现已报错**（R1，与 §9「无条件非法」自洽）——这恰是相对 `LLVM-024t` 第 2 轮非阻断观察的收口。
- `ADR-0013 D9.2`（`#` 不再作注释，保留给 C 预处理器）+ D9.5（重建 `llvm-mc`）与本实现一致 ✓。

##### 五、完成区逐条复读

- **完成区为空**：`.tao/tasks/llvm/LLVM-025t-井号彻底非法.md` 的「## 完成区」9 个字段、「#### 第 1 轮 engineer 自审」**均无内容**（`cat -A` / `xxd` 核对，文件止于 `#### 第 1 轮 reviewer 验收`）；任务头 `**状态**` 仍为 `待开始`。工程师**未向任务书写入任何声明/证据**，故无可逐条复读之数字。
- 工程师证据仅存于 `/tmp/opencode/LLVM-025t-*.log`（`hash_after` 报错、`hash_counterexample` 空、`hash_restored` 报错、`lit 25/25`、`make_check` 等），与本审查独立重跑结论**一致**，未见造假或美化。
- **记录缺口须补**：请主会话要求工程师（或代行）补填「完成区 + 第 1 轮 engineer 自审」并将状态置 `待验收`，方与既有 `t` 任务留证规范一致。

##### 六、判据汇总与遗留

- 验收标准 1–6 **全部满足**；补丁 hunk 头计数一致、可干净 apply、源码态与补丁逐字节相符；承重反例经**本人注入 + 重建 + 复原 + 重建**确认（注入 sha `fe1113e…`、复原 sha `abfe11a…` byte-identical）。
- 无越界改动；无凑绿（未改契约/spec 正文/tests/vectors/其它补丁）。
- **遗留（非阻断）**：任务书完成区/自审/状态未填写（§五）。技术交付物正确，仅记录待补；补填后即可置 `已验证`。

**证据留档**：`/tmp/opencode/LLVM-025t-r1/`（`r1-hash.log`、`r1-semi.log`、`r1-extra-*.log`、`r1-patch-body.txt`、`r1-mc.sha256`、`r1-mc-counter.sha256`、`r1-mc-restored.sha256`、`r1-build-counter.log`、`r1-build-restore.log`、`r1-check-lit.log`、`r1-check_lit_bytes.log`、`r1-make-check.log`、`DADAOMCAsmInfo.cpp.patched.bak`）。


## 完成区
**测试结果**：lit **25/25**（MC 22 + E2E 3）；`check_lit_bytes` **53**；`make check` **EXIT=0**。
**修改文件**：
1. `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch` —— 增设 `AllowAdditionalComments = false;`（`@@` 头 `+1,37`→`+1,40`，与实际 `+` 行数一致）。
2. `docs/spec/assembly-language.md §9` —— 非法记号示例加说明（`#` 为 C 预处理器指令符，纯汇编无条件非法）。
**`#` 前后行为（真实退出码）**：`printf '# foo\nadd.si rd8, 1\n' | llvm-mc …`：改前 **EXIT=0**（静默吞）；改后 **EXIT=1**（`unexpected token at start of statement`）。`; foo` 前后均 **EXIT=0**。
**承重反例（含重建）**：`false→true` + `make build-mc` ⇒ `# foo` **EXIT=0**（静默）；复原 `false` + 重建 ⇒ **EXIT=1**；二进制 sha **byte-identical** 复原（`abfe11a3…5cba`）。
**验收结果**：reviewer 第 1 轮 **Accepted**（6 条验收独立重跑通过）。
**新发现/坑**：`AllowAdditionalComments=true` 时 `AsmLexer` 在 `getTok` 阶段就把行首 `#` 当 `Comment` 消费（不看 `CommentString`）；`@@ -0,0 +1,N @@` 的 N 必须与实际 `+` 行数一致。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

| # | finding | 处置 |
|---|---|---|
| 1 | 补丁 `@@` 头行数不一致 | ✅ 已修（37→40）|
| 2 | §9 说明是否与 §2.2 矛盾 | ✅ 无矛盾（§2.2 未改）|
| 3 | 源文件复原 | ✅ `AllowAdditionalComments = false` |
| 4 | 承重反例真实重建 | ✅ 三次 `make build-mc`（日志留 `/tmp/opencode/LLVM-025t-build*.log`）|
| 5 | 退出码捕获规范 | ✅ `cmd >log 2>&1; rc=$?` |

#### 第 1 轮 reviewer 验收
（见任务书「第 1 轮 reviewer 验收」：**Accepted**，6 条独立重跑通过；承重反例含重建、sha byte-identical。）
