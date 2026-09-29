# SPEC-046t: SimRISC-06（控制流）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`（尤其 D2 `?`、D3 `i`、D4 `[...]`）、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`045t`
**状态**：已验证

## 修改范围（仅 `spec/SimRISC-06-控制流.md`）

### A. 代码块

| 位置 | 旧 | 新（以生成表为准） |
|---|---|---|
| 42 | `br.eq    rdha, rdhb, imms12` | `br.eq    {rdHA, rdHB}?, [rb0, imms12i]` |
| 43 | `br.ne    rdha, rdhb, imms12` | `br.ne    {rdHA, rdHB}?, [rb0, imms12i]` |
| 53 | `br.n     rdha, imms18` | `br.n     {rdHA}?, [rb0, imms18i]` |
| 54 | `br.nn    rdha, imms18` | `br.nn    {rdHA}?, [rb0, imms18i]` |
| 55 | `br.z     rdha, imms18` | `br.z     {rdHA}?, [rb0, imms18i]` |
| 56 | `br.nz    rdha, imms18` | `br.nz    {rdHA}?, [rb0, imms18i]` |
| 57 | `br.p     rdha, imms18` | `br.p     {rdHA}?, [rb0, imms18i]` |
| 58 | `br.np    rdha, imms18` | `br.np    {rdHA}?, [rb0, imms18i]` |
| 68 | `br.z     rbha, imms18` | `br.z     {rbHA}?, [rb0, imms18i]` |
| 69 | `br.nz    rbha, imms18` | `br.nz    {rbHA}?, [rb0, imms18i]` |
| 81 | `jump    imms24` | `jump    [rb0, imms24i]` |
| 89 | `jump    rbha, rdhb, imms12` | `jump    [rbHA, rdHB, imms12i]` |
| 104 | `call    imms24` | `call    [rb0, imms24i]` |
| 112 | `call    rbha, rdhb, imms12` | `call    [rbHA, rdHB, imms12i]` |
| 131 | `ret     rdha, imms18` | `ret     rdHA, imms18` |

> **要点**：
> - `br.eq`/`br.ne` = **双**寄存器条件组 `{rdHA, rdHB}?`；其余 `br.*` = **单**寄存器条件组 `{rdHA}?`/`{rbHA}?`（`?` 紧跟 `}`）。
> - 跳转/分支目标一律 `[rb0, <imm>i]`（基址恒 `rb0`，立即数**加 `i` 后缀** = 指令字单位）。
> - `jump`/`call` 绝对地址 `rrii` 形式 → `[rbHA, rdHB, imms12i]`（立即数在括号内且加 `i`）。
> - `ret` **不是**跳转：`ret rdHA, imms18`（`rdHA` 为普通目的寄存器，`imms18` **无 `i`**）。

### B. 行 139 `return` 伪指令展开注释

`return                  ; 展开为 ret rd0, 0` —— `ret rd0, 0` 为**具体寄存器**示例，**保持**（`return` 为伪指令，调用写法不改）。

### C. 正文散文引用

- 行 63 `rdha`→`rdHA`（`rd0` 保持）
- 行 65 `rbha`→`rbHA`
- 行 95 / 118 中 `rdhb`→`rdHB`
- 行 93 / 116 中的裸后缀 `ha`/`hb` **保持**（非完整寄存器字段名，最小改动）

## 约束

- **只改 `spec/SimRISC-06-控制流.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–29）
- **语义零变化**：数值（`<<2`、`48`、`16`、`63:48`、`7.4%`、P226 等）、公式、限制条文一字不动
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 15 条代码块行为新格式：
   - 条件组个数正确（`br.eq/ne` 双、其余单）
   - 跳转/分支目标带 `[...]` 且立即数带 `i`；`ret` 为普通形式（**无 `i`、无 `[]`**）
2. B 段 `ret rd0, 0` 未被误改
3. C 段引用大写正确；裸 `ha`/`hb` 未被误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 29）
6. 15 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退（如 `br.eq` 写成单条件组、`jump` 漏 `i` 后缀、`ret` 误加 `[]`）→ 检查可检出；复原后无残留
8. `make check` EXIT=0

## 完成区
**测试结果**：通过 15/15（A 段 15 条代码块逐条与生成表「汇编形式」列相符）；`make check` EXIT=0
**修改文件**：`spec/SimRISC-06-控制流.md`（唯一修改文件）
**验收结果**：
- A 段 15 条代码块逐条核对（行号 → 旧 → 新 → 生成表对照）：
  | # | 行 | 旧 | 新 | 生成表汇编形式 | 符合 |
  |---|---|---|---|---|---|
  | 1 | 42 | `br.eq rdha, rdhb, imms12` | `br.eq {rdHA, rdHB}?, [rb0, imms12i]` | `br.eq {rdHA, rdHB}?, [rb0, imms12i]` | ✓ |
  | 2 | 43 | `br.ne rdha, rdhb, imms12` | `br.ne {rdHA, rdHB}?, [rb0, imms12i]` | `br.ne {rdHA, rdHB}?, [rb0, imms12i]` | ✓ |
  | 3 | 53 | `br.n rdha, imms18` | `br.n {rdHA}?, [rb0, imms18i]` | `br.n {rdHA}?, [rb0, imms18i]` | ✓ |
  | 4 | 54 | `br.nn rdha, imms18` | `br.nn {rdHA}?, [rb0, imms18i]` | `br.nn {rdHA}?, [rb0, imms18i]` | ✓ |
  | 5 | 55 | `br.z rdha, imms18` | `br.z {rdHA}?, [rb0, imms18i]` | `br.z {rdHA}?, [rb0, imms18i]`（rd） | ✓ |
  | 6 | 56 | `br.nz rdha, imms18` | `br.nz {rdHA}?, [rb0, imms18i]` | `br.nz {rdHA}?, [rb0, imms18i]`（rd） | ✓ |
  | 7 | 57 | `br.p rdha, imms18` | `br.p {rdHA}?, [rb0, imms18i]` | `br.p {rdHA}?, [rb0, imms18i]` | ✓ |
  | 8 | 58 | `br.np rdha, imms18` | `br.np {rdHA}?, [rb0, imms18i]` | `br.np {rdHA}?, [rb0, imms18i]` | ✓ |
  | 9 | 68 | `br.z rbha, imms18` | `br.z {rbHA}?, [rb0, imms18i]` | `br.z {rbHA}?, [rb0, imms18i]`（rb） | ✓ |
  | 10 | 69 | `br.nz rbha, imms18` | `br.nz {rbHA}?, [rb0, imms18i]` | `br.nz {rbHA}?, [rb0, imms18i]`（rb） | ✓ |
  | 11 | 81 | `jump imms24` | `jump [rb0, imms24i]` | `jump [rb0, imms24i]` | ✓ |
  | 12 | 89 | `jump rbha, rdhb, imms12` | `jump [rbHA, rdHB, imms12i]` | `jump [rbHA, rdHB, imms12i]` | ✓ |
  | 13 | 104 | `call imms24` | `call [rb0, imms24i]` | `call [rb0, imms24i]` | ✓ |
  | 14 | 112 | `call rbha, rdhb, imms12` | `call [rbHA, rdHB, imms12i]` | `call [rbHA, rdHB, imms12i]` | ✓ |
  | 15 | 131 | `ret rdha, imms18` | `ret rdHA, imms18` | `ret rdHA, imms18` | ✓ |
- B 段：行 139 `return ; 展开为 ret rd0, 0` 未被误改 ✓
- C 段：行 63 `rdha`→`rdHA`、行 65 `rbha`→`rbHA`、行 95/118 `rdhb`→`rdHB` ✓；行 93/116 裸 `ha`/`hb` 保持 ✓
- 语义零变化：数值（`<<2`、`48`、`16`、`63:48`、`7.4%`、P226 等）、公式、限制条文一字不动 ✓
- 不改生成区：diff 仅命中行 ≥39，行 6-29 无变化 ✓
- 反例验证：注入 `br.eq {rdHA}?`（单条件组回退）→ 逐条对照生成表可检出；复原后 `make check` EXIT=0，无残留 ✓
- `make check`：`cmd > log 2>&1; rc=$?` → EXIT=0 ✓

**新发现/坑**：`check-asm-list-consistency` 只校验生成区（`ASSEMBLY_LIST_START/END` 之间），不校验正文代码块——这是设计如此（生成区由生成器写入，正文由人工维护），反例验证需依赖逐条对照生成表完成。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审
**审查方式**：自主逐行审查（subagent_depth=1，无法嵌套子代理）

**审查意见**：

1. **A 段 15 条代码块**：逐条比对生成表「汇编形式」列，全部相符。
   - `br.eq`/`br.ne`（rrii 格式）→ 双条件组 `{rdHA, rdHB}?` ✓
   - `br.n/nn/z/nz/p/np`（riii 格式，rd）→ 单条件组 `{rdHA}?` ✓
   - `br.z/nz`（riii 格式，rb）→ 单条件组 `{rbHA}?` ✓
   - `jump`/`call`（iiii）→ `[rb0, imms24i]` ✓
   - `jump`/`call`（rrii）→ `[rbHA, rdHB, imms12i]` ✓
   - `ret`（riii）→ `rdHA, imms18`（无 `[]`、无 `i`）✓

2. **B 段**：行 139 `return ; 展开为 ret rd0, 0` 未被误改 ✓

3. **C 段散文引用**：
   - 行 63 `rdha`→`rdHA` ✓
   - 行 65 `rbha`→`rbHA` ✓
   - 行 95/118 `rdhb`→`rdHB` ✓
   - 行 93/116 裸 `ha`/`hb` 保持 ✓

4. **语义零变化**：`<<2`、`48`、`16`、`63:48`、`7.4%`、P226、公式、限制条文均未触碰 ✓

5. **生成区未触碰**：diff 仅命中行 ≥39 ✓

6. **反例验证**：注入 `br.eq {rdHA}?`（单条件组回退）→ 逐条对照生成表可检出；复原后 `make check` EXIT=0 ✓

**问题与判决**：无问题，全部通过。

**Finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

**最终判决**：通过，无 finding 需处置。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑，脚本自写：`/tmp/opencode/SPEC-046t/verify.py`、`inject.sh`）
**被审文件**：`spec/SimRISC-06-控制流.md`（`git diff` 版本）、`.tao/tasks/spec/SPEC-046t-SimRISC06正文改新汇编格式.md`
**独立 oracle**：重跑生成器 `python3 tools/llvm/gen_asm_list.py`（输出 `docs/assembly-list.md`，git 无 diff），以生成表「汇编形式」列为准。

##### 1. 重跑记录（真实输出 / 退出码）

- **改动范围**（`git status --short`）：仅
  `M spec/SimRISC-06-控制流.md`、`M .tao/tasks/spec/SPEC-046t-...md`，无其他文件。
- **生成区**：`verify.py` 实测 `START=6 END=29`；`git diff --unified=0` 命中行 =
  `[42,43,53,54,55,56,57,58,63,65,68,69,81,89,95,104,112,118,131]`（min=42）→ **全部 >29**。
- **A 段 15 条独立复算**：逐条 `normalize(代码块行) == 生成表[cells[3]]`，15/15 PASS；
  另加结构正则（`br.eq/ne` 必须 `\{rdHA, rdHB\}\?,`；单条件组 `\{rdHA\}\?`/`\{rbHA\}\?`；`jump/call` 的 `imms24i`/`imms12i`；`ret rdHA, imms18`）全 PASS。
- **B 段**：L139 == `return                  ; 展开为 ret rd0, 0` → PASS。
- **C 段**：L63 含 `rdHA`、L65 `rbHA`、L95/118 `rdHB`（PASS）；L93/116 保留裸 `ha`/`hb`（PASS）；
  变更/代码块行内无残留 `rdha|rdhb|rbha`（PASS）。
  注：L92/115 公式 `Addr = rbha + rdhb + (imms12 << 2)` **有意未改**，符合任务「公式一字不动」约束。
- **语义零变化**：对每个 hunk 提取数字/算子 token `\d+(\.\d+)?|<<|>>|P\d+`（剔除语法性寄存器名 `rb0/rd0/ra63`）逐一比对 old==new，18/18 hunk PASS；
  `verify.py` 整体 **EXIT=0**。
- **`make check`**（`cmd > log 2>&1; rc=$?`）：
  ```
  EXIT=0
  manifest validation: PASS
  spec drift check: PASS
  check-patch-tree: 2 component(s), 67 patches OK
  check-asm-list-consistency: 12 spec files OK
  repository checks: PASS
  ```
  （日志：`/tmp/opencode/SPEC-046t/make_check.log`）

##### 2. 反例注入（每例在 `/tmp` 临时副本操作，仓库零污染；`diff` 确认每例 DIFFERENT）

| # | 注入 | 我的脚本结果 |
|---|------|------|
| 1 | `br.eq {rdHA, rdHB}?` → `{rdHA}?`（单条件组回退） | EXIT=1，`[FAIL] L42 ... [FAIL] L42 double-group rrii` |
| 2 | `jump [rb0, imms24i]` → `[rb0, imms24]`（去 `i`） | EXIT=1，`[FAIL] L81` |
| 3 | `ret rdHA, imms18` → `ret [rdHA, imms18]`（加 `[]`） | EXIT=1，`[FAIL] L131` |
| 4 | `br.z {rbHA}?` → `{rdHA}?`（L68） | EXIT=1，`[FAIL] L68 single rbHA group` |
| 5 | `ret rdHA, imms18` → `...imms18i`（加 `i`） | EXIT=1，`[FAIL] L131` |

注入后 `git status --short` 仍仅 2 个预期文件 → 复原/无残留确认（注入全程在临时副本，未触碰仓库）。

##### 3. 约束逐条核验

| 约束 | 结论 |
|---|---|
| 只改 `spec/SimRISC-06-控制流.md`（+任务文件） | 守住（`git status` 仅 2 文件） |
| 不改生成区（行 6–29），命中行 >29 | 守住（END=29；min hit=42） |
| A 段 15 条条件组个数正确 | 守住（`br.eq/ne` 双；其余单；`?` 紧跟 `}`） |
| 跳转/分支目标 `[rb0, …i]`；`jump/call` rrii = `[rbHA, rdHB, imms12i]` | 守住 |
| `ret` 无 `[]`、无 `i` | 守住 |
| B 段 L139 未误改 | 守住 |
| C 段引用大写；L93/116 裸 `ha/hb` 未误改 | 守住 |
| 语义零变化（`<<2`/`48`/公式等） | 守住（逐 hunk 数字 token 一致） |
| `make check` EXIT=0 | 守住（EXIT=0） |
| 任务文件改动范围 | 仅「状态」+「完成区」+「审阅记录」，未改任务/验收条款 |

##### 4. 判决

**Accepted**。验收命令块在审查者独立重跑下全部通过；5 个反例注入均被自写脚本检出；约束无违反；生成表与生成器重跑一致。
补充（供架构师参考，不构成阻断）：engineer 的「新发现/坑」属实——`check-asm-list-consistency` 只校验生成区，正文代码块回归需靠逐条比对生成表（本审查已用自写脚本补齐该 FAIL 路径）。

**你验证了**：A/B/C 三段 15+ 行、生成区行号、`make check` EXIT=0、反例注入检出。
**你采信的**：`docs/assembly-list.md` 为生成器输出（已重跑核验其与 HEAD 无 diff）。

#### 第 2 轮 reviewer 复核（跨章一致性增补：L92/115 公式字段名大写）

**增补内容**：`Addr = rbha + rdhb + (imms12 << 2)` → `Addr = rbHA + rdHB + (imms12 << 2)`（行 92/115）。

**1. 唯一性（仅这 2 行是追加改动）**
- 当前 `git diff --unified=0` 命中行 = `[42,43,53,54,55,56,57,58,63,65,68,69,81,89,` **`92`** `,95,104,112,` **`115`** `,118,131]`。
- 与第 1 轮命中集之差 = **`{92, 115}`**（无删除、无其它新增）→ 追加改动确为且仅为此 2 行。
- `diff <(git show HEAD:...) <工作树>` 全量比对：其余行与第 1 轮一致。

**2. 语义未变**：仅字段名大小写（`rbha→rbHA`、`rdhb→rdHB`）；该 2 hunk 数字/算子 token `['0','12','2','<<']` 前后一致（`verify.py` 数字 token 比对 PASS）。L92/115 保留裸 `ha`/`hb`（L93/116）符合任务。

**3. 全文无残留小写字段引用**
- `grep -nE '\b(rd|rb|ra|rf)h[a-z]\b'` → **NONE**（覆盖 `rdha/rbha/rdhb/rdhc/rdhd` 等全部小写字段名）。
- `verify.py`「no lowercase field refs anywhere」→ PASS。

**4. 生成区未触碰**：`ASSEMBLY_LIST_END=29`，命中行 min=42（全部 >29）→ PASS。

**5. `make check`**（`cmd > log 2>&1; rc=$?`）：`EXIT=0`；`check-asm-list-consistency: 12 spec files OK` / `repository checks: PASS`（日志 `make_check_round2.log`）。

**6. 反例注入 `rbHA→rbha`**（`/tmp` 副本，仓库零污染）：
| 注入点 | 结果 |
|---|---|
| 行 92 公式（`Addr = rbHA + rdHB`→`rbha + rdhb`，两处同改） | EXIT=1，`[FAIL] no lowercase field refs anywhere (found L92,L115)` |
| 行 89 代码块（`[rbHA, rdHB, imms12i]`→`[rbha, rdhb, imms12i]`） | EXIT=1，`[FAIL] L89 operand form` + `[FAIL] no lowercase field refs anywhere` |

两例均 `diff` 确认 DIFFERENT（注入有效）；注入后 `git status --short` 仍仅任务文件 + spec 文件，无污染。

**判决：Accepted**。追加的 2 行改动经确认唯一、仅大小写、语义未变；全文无残留小写字段；生成区未动；`make check` EXIT=0；反例可检出。原任务书「公式一字不动」与用户规则「正文里的字段名引用也大写」冲突，以用户已确认规则为准——此为**任务书措辞笔误**，不影响本复核结论（架构师知悉）。
