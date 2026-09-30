# SPEC-062t: RA 语义修订落地（ADR-0012 D7：`RACNT` / `MRPTR` / 压弹栈流程）

**模块**：spec（含 `.tao/knowledge/`）
**项目里程碑**：M1→M2
**依赖**：`ADR-0012 D7`（2026-09-30 用户逐条确认，已写入）；本任务为**规范基线**，QEMU/向量/探针由其后续任务实现
**状态**：待验收

## 背景

`ADR-0012 D7` 已固化 RA 语义修订（见 `.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` §D7）。核心变化：

- `ra0[63:54]` = SBZ（**MemRAS 引用计数取消**）；`ra0[53:48]` = **`RACNT`**（RegRAS 有效条目数 0–63）；`ra0[47:0]` = **`MRPTR`**（MemRAS 下一个待弹出条目的字节地址；0 = 未启用）。
- `ra1`–`ra63`：`[63:48]` = **递归计数**、`[47:0]` = 返回地址；`ra63` 恒为栈顶；**有效性判据 = `RACNT`**（不看条目自身值）：有效条目 = 自 `ra63` 起向下连续 `RACNT` 个。
- 压栈 C1/C2/C3（C2 递归折叠优先；C3b 满栈时溢出栈底到 MemRAS，`RACNT` 保持 63）；弹栈 D1–D4（D4b 读 MemRAS 条目并按其递归计数判定）。
- **精确异常**：先完成全部 `RASOF`/`RASUF` 判定，再作任何修改。
- 实现可用**环形缓冲 + 隐藏基准索引**避免数据搬移（非架构语义）。

**现状与 D7 冲突处**（本任务须改）：

| 文件 | 现状 | D7 |
|---|---|---|
| `spec/SimRISC-00 §返回地址栈` L127–174 | 位域表（`ra0` 高16 = MemRAS 计数）+ 压栈三情况/弹栈三情况（"高16 位为引用计数"） | 全表 + 全流程重写 |
| `spec/SimRISC-06-控制流.md` L99（call） | 「压入 `ra63`…**高 16 位为引用计数**（首次压栈设为 1，递归调用递增）」 | 改为「**递归计数**」+ 指向 §返回地址栈 |
| `spec/SimRISC-06-控制流.md` L122（ret） | 「从 `ra63`（栈顶）弹出…**高 16 位为引用计数**」 | 同上 |
| `.tao/knowledge/contract-isa.md §1.3.4` | 表（`ra0` 高16 = MemRAS 引用计数）+ 有效性描述 | 全表 + 判据改写 |

## 修改内容

### 1. `spec/SimRISC-00-指令系统设计.md` §返回地址栈（L127–174）

- **位域表**改为：

| 寄存器 | `[63:48]` | `[47:0]` |
|---|---|---|
| `ra0` | `[63:54]` = **SBZ**；`[53:48]` = **`RACNT`**（RegRAS 有效条目数，0–63，初始 0） | **`MRPTR`**：MemRAS 下一个待弹出条目（栈顶）的字节地址（8 字节对齐）；**0 = 未启用 MemRAS** |
| `ra1`–`ra63` | **递归计数** | **返回地址**（`ra63` 恒为 RegRAS 栈顶） |

- 新增/改写说明段：**有效性判据 = `RACNT`**（不条目自身值）：有效条目 = 自 `ra63` 起向下连续 `RACNT` 个（第 k 新 = `ra[64−k]`，栈底 = `ra[64−RACNT]`）；有效区之外 `ra_i` 内容未定义（复位后全 0）。
- **压栈流程**：按 D7 §3 的 **C1/C2/C3a/C3b** 逐条改写（含 C3b 的 `MRPTR −= 8`、写入栈底条目、`RACNT` 保持 63、`MRPTR == 0 → RASOF`）。
- **弹栈流程**：按 D7 §4 的 **D1/D2/D3/D4a/D4b** 逐条改写（含 D4b 的读取与递归计数判定、`MRPTR += 8` 时机）。
- **精确异常**：加「先判定、后修改」表述（D7 §6）。
- **实现注**：环形缓冲 + 隐藏基准索引（D7 §5），标注为**非架构语义**。
- **保留不改**：进程入口/进程切换/异常进入退出/fork 等既有段落（其中「RegRAS 全部初始化为全零」仍成立，`ra[63:48]=0` 的描述按新语义表述为「`RACNT = 0`、条目内容全 0」）。
- **删除**：`ra0` 高 16 位为 MemRAS 计数的相关语义（含「高16位为 16 位无符号计数…0xFFFF 溢出触发 RASOF」）。

### 2. `spec/SimRISC-06-控制流.md`（L99 call / L122 ret）

- 把「**高 16 位为引用计数**（首次压栈设为 1，递归调用递增）」→「**`[63:48]` 为递归计数**（首次压栈设为 1，递归调用递增）」；
- 补充：压/弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 **SimRISC-00 §返回地址栈**（不在本文件展开）。

### 3. `.tao/knowledge/contract-isa.md §1.3.4`

- 位域表按 D7 §1/§2 改写；
- 有效性判据改为 `RACNT`；
- 「`ra0` 低 48 位为 0 时只有一个 RAS」→「**`MRPTR == 0`** 时只有一个 RAS（RegRAS）」；
- 新增：**RASOF 仅由「需溢出且 `MRPTR == 0`」触发**；**MemRAS 越界不由硬件检测（交 OS）**；精确异常承诺按 D7 §6。

### 4. 评估项（**预期不改**，如判断需改须在完成区说明理由）

- `adr-0004-test-machine.md §D2.1`（复位值 `ra0=0` 不变；若需可加一句就地修订注记，注明有效性判据见 D7）
- `spec/DADAO-21-ABI-应用程序二进制接口.md:59`（`ra0` = RAS control；`[47:0]` 语义不变）
- `docs/impact-matrix.md`（§1.3.4 行的下游标注）

## 约束

- **仅 ASCII/中文措辞与语义改动**；**不改** `adr-0012`（D7 已固化）、**不改** QEMU/向量/探针（另开任务）。
- **不改历史**：`spec/SimRISC-0.5.3/`、`.tao/tasks/**`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`。
- 术语：一律用「**压栈/弹栈**」，**不得**出现「上移/下移」；「**递归计数**」写全；符号用 `RACNT`/`MRPTR`。
- **载体一致**：`spec/SimRISC-00` ↔ `spec/SimRISC-06` ↔ `contract-isa §1.3.4` ↔ `ADR-0012 D7` 逐条对齐。
- 命令缺失/失败 → **停下报告**；反例注入须**可复原**。

## 验收标准

1. `spec/SimRISC-00 §返回地址栈`：位域表 = D7 §1/§2；**无**「MemRAS 引用计数」「0xFFFF 溢出」残留（`grep` 证据）；压/弹栈流程含 **C1–C3b** 与 **D1–D4b** 全部情形（**逐条对照 D7 列表**，给出对照表）。
2. `spec/SimRISC-06`：L99/L122 改为「递归计数」并指向 §返回地址栈。
3. `contract-isa §1.3.4`：表 + 判据 + RASOF/RASUF 判据与 D7 一致。
4. **载体一致**：四载体逐条对照表（D7 的 §1–§7 ↔ 三文件），无遗漏、无矛盾。
5. **术语**：`grep -n "上移\|下移" spec/SimRISC-00*.md spec/SimRISC-06*.md` → 0 命中（本次新增文本内）。
6. **反例门控（可失败）**：/tmp 副本中注入 (a) 把有效性判据改回「条目自身高16」 (b) 把 C3b 的 `RACNT` 改为「−1」 (c) 删 D1（`RACNT>0` 且递归计数==0 → RASUF） —— 各使「与 D7 对照」检查 **FAIL**；复原后 PASS。
7. **门控**：`make check` **EXIT=0**；`check_interface_alignment.py` **80/80 EXIT=0**；`validate_encoding.py contracts/opcodes.yaml` 与 `HEAD` **一致**。均贴真实退出码。
8. **未触历史 + 未触 QEMU/向量**：`git diff --name-only` 与清单逐项对齐。

## 完成区

> ### ⚠️ 提交归属更正（主会话，2026-09-30，**可审计性说明**）
> 本任务的三文件改动（`spec/SimRISC-00` / `spec/SimRISC-06` / `.tao/knowledge/contract-isa.md`）**实际落在提交 `dff2381`**，但该提交的 message 是「SPEC-061t: F2 措辞定稿」——**message 与内容不符**。
> **原因（主会话操作错误）**：主会话在本任务**后台运行期间**用 `git add -A` 提交 SPEC-061t 任务书，把在飞的本任务产物一并扫入。该提交**已推送**（不可重写历史）⇒ 以本注记更正。
> **教训**：**不得在后台子代理运行期间使用 `git add -A`**（应只 `git add <明确路径>`）。已报用户。

**测试结果**：全部验收项通过（详见下方逐条对照表与证据；反例门控3 注入均 FAIL、复原后 PASS，真实退出码见验收 6）

**修改文件**：三载体（`spec/SimRISC-00`、`spec/SimRISC-06`、`.tao/knowledge/contract-isa.md`）的 RA 语义修订（位域表/压弹栈 C1–C3b、D1–D4b/判据/异常表 RASOF/RASUF 补充）+ 反例对照器（`tools/spec/check_d7_consistency.py`）。三载体改动实际落在 commit `dff2381`（message 误标为 SPEC-061t，系主会话 `git add -A` 误扫入，已由 `2e9ded4` 更正）；对照器为本轮新增。

**验收结果**：

### 验收 1：`spec/SimRISC-00 §返回地址栈` 位域表 = D7 §1/§2

| D7 条目 | D7 原文 | SimRISC-00 对应行 | 一致？ |
|---------|---------|-------------------|--------|
| §1 ra0[63:54] | SBZ（写无效） | L132 `[63:54]` = **SBZ**（写无效） | ✅ |
| §1 ra0[53:48] | RACNT（RegRAS 有效条目数，0–63，初始 0） | L132 `[53:48]` = **RACNT** | ✅ |
| §1 ra0[47:0] | MRPTR（MemRAS 下一个待弹出条目字节地址；0=未启用） | L132 **MRPTR** | ✅ |
| §1 ra1–ra63[63:48] | 递归计数 | L133–134 **递归计数** | ✅ |
| §1 ra1–ra63[47:0] | 返回地址；ra63 恒为栈顶 | L133–134 | ✅ |
| §2 有效性判据 | RACNT（不看条目自身值） | L137 有效性判据 = RACNT | ✅ |
| §2 有效条目定义 | 自 ra63 起向下连续 RACNT 个 | L137 | ✅ |
| §2 有效区外 | 未定义（复位后全 0） | L137 | ✅ |
| §7 RASOF 仅由 | 需溢出且 MRPTR==0 | L142 | ✅ |
| §7 MemRAS 越界 | 不由硬件检测（交 OS） | L142 | ✅ |
| §6 精确异常 | 先完成全部判定，再修改 | L143 | ✅ |
| §5 实现注 | 环形缓冲+隐藏基准索引（非架构语义） | L174–176 | ✅ |

**grep 残留检查**：
- `grep -n "上移\|下移" spec/SimRISC-00*.md spec/SimRISC-06*.md .tao/knowledge/contract-isa.md` → **0 命中**
- `grep -n "引用计数" spec/SimRISC-00*.md spec/SimRISC-06*.md .tao/knowledge/contract-isa.md` → **0 命中**
- `grep -n "MemRAS 引用计数" spec/SimRISC-00*.md` → **0 命中**

**压栈流程逐条对照（D7 §3）**：

| D7 分支 | 条件 | SimRISC-00 行 | 一致？ |
|---------|------|---------------|--------|
| C1 | RACNT==0 → 压入新条目（递归计数=1），RACNT=1 | L157 | ✅ |
| C2 | RACNT>0 且返回地址==ra63[47:0] 且 ra63[63:48]<0xFFFF → 递归折叠，RACNT 不变 | L158 | ✅ |
| C3a | RACNT<63 → 压入新条目（递归计数=1），RACNT+=1 | L160 | ✅ |
| C3b | RACNT==63 → ①MRPTR==0→RASOF ②MRPTR−=8 写栈底 ③压入新条目，RACNT 保持 63 | L161 | ✅ |

**弹栈流程逐条对照（D7 §4）**：

| D7 分支 | 条件 | SimRISC-00 行 | 一致？ |
|---------|------|---------------|--------|
| D1 | RACNT>0 且 ra63[63:48]==0 → RASUF | L167 | ✅ |
| D2 | RACNT>0 且 ra63[63:48]>1 → 计数−1，RACNT 不变 | L168 | ✅ |
| D3 | RACNT>0 且 ra63[63:48]==1 → 弹出栈顶，RACNT−1 | L169 | ✅ |
| D4a | RACNT==0 且 MRPTR==0 → RASUF | L171 | ✅ |
| D4b | RACNT==0 读 MRPTR 处条目：递归计数=0→RASUF；=1→返回且 MRPTR+=8；>1→压入栈顶（计数−1）且 MRPTR+=8、RACNT=1 | L172 | ✅ |

### 验收 2：`spec/SimRISC-06` L99/L122

- L99（call）：已改为「`[63:48]` 为递归计数（首次压栈设为 1，递归调用递增），`[47:0]` 为返回地址。压/弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。」✅
- L122（ret）：已改为「`[47:0]` 为返回地址，`[63:48]` 为递归计数。弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。」✅

### 验收 3：`contract-isa §1.3.4`

- 位域表：ra0[63:54]=SBZ、[53:48]=RACNT、[47:0]=MRPTR ✅
- 有效性判据=RACNT（不看条目自身值）✅
- MRPTR==0 时只有一个 RAS ✅
- RASOF 仅由「需溢出且 MRPTR==0」触发 ✅
- MemRAS 越界不由硬件检测 ✅
- 精确异常按 D7 §6 ✅
- §8.4 函数调用：递归计数 ✅
- §8.5 函数返回：递归计数 ✅
- §8.6 压栈/弹栈流程：C1/C2/C3a/C3b + D1/D2/D3/D4a/D4b ✅
- 异常表 RASOF/RASUF 描述已更新 ✅

### 验收 4：四载体逐条对照（D7 §1–§7 ↔ 三文件）

| D7 章节 | 内容 | SimRISC-00 | SimRISC-06 | contract-isa | 一致？ |
|---------|------|------------|------------|--------------|--------|
| §1 ra0 位域 | SBZ/RACNT/MRPTR | L132 | — | L92–94 | ✅ |
| §1 ra1–ra63 | 递归计数+返回地址 | L133–134 | — | L95–96 | ✅ |
| §2 有效性判据 | RACNT | L137 | — | L98 | ✅ |
| §3 压栈 C1–C3b | 4 分支 | L157–161 | L99（指向） | L777–780 | ✅ |
| §4 弹栈 D1–D4b | 5 分支 | L167–172 | L122（指向） | L786–789 | ✅ |
| §5 实现注 | 环形缓冲 | L174–176 | — | — | ✅ |
| §6 精确异常 | 先判定后修改 | L143 | — | L103 | ✅ |
| §7 影响 | RASOF 条件+MemRAS 交 OS | L142 | — | L102 | ✅ |

### 验收 5：术语检查

```
$ grep -n "上移\|下移" spec/SimRISC-00*.md spec/SimRISC-06*.md .tao/knowledge/contract-isa.md
(0 hits)
```

### 验收 6：反例门控（可复现）

对照器：`tools/spec/check_d7_consistency.py`（提交到仓库，可复用/可审计）。校验 D7 §1–§7 ↔ 三载体（`SimRISC-00`/`06`、`contract-isa.md`）的 9 分支与位域/判据，共静态 35 条 needle 断言（运行时展开 65 项）。

**基线（仓库干净副本）**：
```
$ python3 tools/spec/check_d7_consistency.py .
PASS: 全部 D7 对照项通过
EXIT=0
```

**(a) 注入：有效性判据改回「条目自身高16位」**（副本 `/tmp/opencode/SPEC-062t/r2/injA/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injA
FAIL: 4 项不符
  - [s00] 缺少/不符: §2 判据=RACNT  (needle='有效性判据 = RACNT（不看条目自身的值）')
  - [cis] 缺少/不符: §2 判据=RACNT  (needle='有效性判据 = RACNT（不看条目自身的值）')
  - [s00] 残留旧语义: 条目自身高16  (found='条目自身高16')
  - [cis] 残留旧语义: 条目自身高16  (found='条目自身高16')
EXIT=1
```

**(b) 注入：C3b 的 `RACNT 保持 63` → `RACNT −= 1`**（副本 `/tmp/opencode/SPEC-062t/r2/injB/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injB
FAIL: 2 项不符
  - [s00] 缺少/不符: C3b RACNT 保持 63  (needle='RACNT 保持 63')
  - [cis] 缺少/不符: C3b RACNT 保持 63  (needle='RACNT 保持 63')
EXIT=1
```

**(c) 注入：删除 D1 行（`RACNT>0` 且 `ra63[63:48]==0 → RASUF`）**（副本 `/tmp/opencode/SPEC-062t/r2/injC/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injC
FAIL: 2 项不符
  - [s00] 缺少/不符: D1  (needle='D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF')
  - [cis] 缺少/不符: D1  (needle='D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF')
EXIT=1
```

**复原后 PASS**（干净副本 `/tmp/opencode/SPEC-062t/r2/restored/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/restored
PASS: 全部 D7 对照项通过
EXIT=0
```

**注入方式**：三例均在 `/tmp/opencode/SPEC-062t/r2/inj{A,B,C}/` 的隔离副本上操作，仓库零污染（`git status --porcelain` 无三载体改动）。

### 验收 7：门控退出码

```
$ make check
EXIT=0
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/integ/check_interface_alignment.py
EXIT=0
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml
EXIT=1（2 errors: no_overlap — 与 HEAD 一致，pre-existing）
```

### 验收 8：未触历史 + 未触 QEMU/向量

```
$ git status --porcelain
 M ".tao/tasks/spec/SPEC-062t-RA语义修订落地.md"    ← 本任务书（本轮返工修改）
?? tools/spec/check_d7_consistency.py               ← 本轮新增对照器

$ git diff --name-only
.tao/tasks/spec/SPEC-062t-RA语义修订落地.md          ← 本任务书
```

- 三载体（`SimRISC-00`/`06`、`contract-isa.md`）在工作树中**无 diff**（自 `dff2381` 起未变），符合预期。
- `git diff --name-only dff2381^..HEAD` 包含 **7 项**：三载体（`contract-isa.md`、`SimRISC-00`、`SimRISC-06`）+ 本任务书 + `SPEC-061t` 任务书 + `INTEG-008t` 任务书 + `tools/spec/check_d7_consistency.py`。其中 `SPEC-061t`/`INTEG-008t` 任务书属独立提交（`dff2381` 自身、`8930aa5`），非本任务越界。**（2026-09-30 更正：原写「6 项」，漏计本任务新增的对照器；依据 reviewer 第 2 轮复核）**
- 禁止项（`spec/SimRISC-0.5.3/`、`adr-0004`、`adr-0012`、QEMU、向量、`contracts/opcodes.yaml`、ABI、`docs/`）**0 改动**。

**新发现/坑**：
- 三载体的 RA 语义修订（D7 全部落地）实际是本任务（SPEC-062t）的产物，被主会话 `git add -A` 在后台运行期间误扫入 message 为「SPEC-061t: F2 措辞定稿」的 commit `dff2381`；该提交已推送，不可重写历史，已由 `2e9ded4` 加更正注记。**教训**：不得在后台子代理运行期间使用 `git add -A`。
- 本任务产物包含两部分：(1) 三载体 RA 语义修订（位域表/流程/判据/异常表 RASOF/RASUF 补充），落在 `dff2381`；(2) 反例对照器 `tools/spec/check_d7_consistency.py`，本轮新增。
- `validate_encoding.py` 的 2 个 `no_overlap` 错误是 pre-existing（opcodes.yaml 中 `rd2rd`/`rb2rb` 引用了未实现的 `no_overlap` legality），与本次任务无关。
- `check_interface_alignment.py` 位于 `tools/integ/`（非 `tools/infra/`）。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：三文件（SimRISC-00 §返回地址栈、SimRISC-06 L99/L122、contract-isa §1.3.4+§8.4–§8.6+异常表）vs ADR-0012 D7 §1–§7。

**逐项审查**：

| # | 检查项 | 判定 | 说明 |
|---|--------|------|------|
| 1 | ra0 位域表 = D7 §1 | ✅ | SBZ[63:54]、RACNT[53:48]、MRPTR[47:0] 三处一致 |
| 2 | ra1–ra63 位域 = D7 §2 | ✅ | 递归计数[63:48]、返回地址[47:0]、ra63 恒为栈顶 |
| 3 | 有效性判据 = RACNT = D7 §2 | ✅ | 「不看条目自身的值」+ 有效条目定义 + 有效区外未定义 |
| 4 | 压栈 C1 = D7 §3 | ✅ | RACNT==0 → 压入（递归计数=1），RACNT=1 |
| 5 | 压栈 C2 = D7 §3 | ✅ | 递归折叠条件三要素（RACNT>0 + 地址匹配 + 计数<0xFFFF）完整 |
| 6 | 压栈 C3a = D7 §3 | ✅ | RACNT<63 → 压入（递归计数=1），RACNT+=1 |
| 7 | 压栈 C3b = D7 §3 | ✅ | 三步（①MRPTR==0→RASOF ②MRPTR−=8 写栈底 ③压入，RACNT 保持 63） |
| 8 | 弹栈 D1 = D7 §4 | ✅ | RACNT>0 且递归计数==0 → RASUF（递归计数耗尽场景） |
| 9 | 弹栈 D2 = D7 §4 | ✅ | 递归计数>1 → 计数−1，RACNT 不变 |
| 10 | 弹栈 D3 = D7 §4 | ✅ | 递归计数==1 → 弹出栈顶，RACNT−1 |
| 11 | 弹栈 D4a = D7 §4 | ✅ | RACNT==0 且 MRPTR==0 → RASUF |
| 12 | 弹栈 D4b = D7 §4 | ✅ | 三分支（=0→RASUF、=1→返回且MRPTR+=8、>1→压入栈顶（计数−1）且MRPTR+=8/RACNT=1）完整 |
| 13 | 精确异常 = D7 §6 | ✅ | 「先完成全部判定，再修改」表述存在 |
| 14 | RASOF 条件 = D7 §7 | ✅ | 「仅由需溢出且 MRPTR==0 触发」+ MemRAS 越界交 OS |
| 15 | 实现注 = D7 §5 | ✅ | 环形缓冲+隐藏基准索引，标注非架构语义 |
| 16 | SimRISC-06 call = D7 | ✅ | 递归计数 + 指向 §返回地址栈 |
| 17 | SimRISC-06 ret = D7 | ✅ | 递归计数 + 指向 §返回地址栈 |
| 18 | contract-isa §1.3.4 表 | ✅ | 位域表与 D7 §1/§2 一致 |
| 19 | contract-isa §1.3.4 判据 | ✅ | RACNT 有效性 + MRPTR==0 判据 |
| 20 | contract-isa §8.6 流程 | ✅ | C1–C3b + D1–D4b 概要与 SimRISC-00 一致 |
| 21 | contract-isa 异常表 | ✅ | RASOF/RASUF 描述已更新为 D7 语义 |
| 22 | 术语合规 | ✅ | 无「上移/下移」，无「引用计数」，「递归计数」写全 |
| 23 | 无 QEMU/向量/探针改动 | ✅ | `git diff --name-only` 仅含任务书 + 对照器，三载体无 diff（自 `dff2381` 起未变） |
| 24 | 无历史文件改动 | ✅ | 未触 SimRISC-0.5.3/tasks/docs |

**发现**：无阻塞性问题。三载体的 D7 全部落地是本任务（SPEC-062t）产物，被误扫入 commit `dff2381`（message 误标 SPEC-061t，已由 `2e9ded4` 更正）。本轮新增反例对照器 `tools/spec/check_d7_consistency.py`。

**判决**：通过 → 待验收。
#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，不采信 engineer 完成区）
**审查时间**：2026-09-30

##### 0. 前置：提交归属核验（工程师报告不可信）

工程师完成区称「D7 内容已由 `SPEC-061t` 在 commit `dff2381` 落地」——**该归属表述错误，已独立证实**：

- `git show --stat dff2381` 的实际 message 为「SPEC-061t: F2 措辞定稿」，但其 diff **含本任务三载体**。
- 工作树三载体 blob 与 `dff2381` **逐字节相同**（即内容自 `dff2381` 起未变）：
  - `SimRISC-00`：`e586132d9b82d366524246973e899eeb28f3fc3d`
  - `SimRISC-06`：`619eb93a7506a6979b82bb8e1f3cd14230c8d7f2`
  - `contract-isa`：`0d37dfdb589be78621ae724984d067346206a5fd`
- `dff2381` 的 diff 明确把三载体的 RA 语义（位域表/压弹栈 C1–C3b、D1–D4b/判据/异常表）改写为 D7 版本（见 `git diff dff2381^ dff2381`）。
- ⇒ 三载体内容确为**本任务（SPEC-062t）的产物**，被主会话 `git add -A` 在后台运行期间误扫入 `dff2381`；**并非 SPEC-061t 的成果**。工程师把它记成「SPEC-061t 落地」是**归因错误**（详见 §8）。

##### 1. 重跑记录（真实命令 + 真实退出码，均为本次亲自执行）

```
$ git status --porcelain
（空 → 工作树干净）

$ grep -n "上移\|下移" spec/SimRISC-00-指令系统设计.md spec/SimRISC-06-控制流.md .tao/knowledge/contract-isa.md
（无输出）; rc=1         ← 0 命中

$ grep -n "MemRAS 引用计数\|高 16 位为引用计数\|高16位为引用计数" <三载体>
（无输出）; rc=1         ← 0 命中

$ grep -n "引用计数" <三载体>
（无输出）; rc=1         ← 0 命中

$ grep -n "0xFFFF" <三载体>
spec/SimRISC-00-指令系统设计.md:158: ... `ra63[63:48] < 0xFFFF` → 递归折叠优先 ...
contract-isa.md:779: ... `ra63[63:48] < 0xFFFF` → 递归折叠优先 ...
   ← 仅出现在 D7 §3 C2 正确的计数上界语境，属合法表述

$ make check ; EXIT=0
  ...
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  全部机械可判定项 PASS。
  check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)
  repository checks: PASS

$ python3 tools/integ/check_interface_alignment.py ; EXIT=0
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml ; EXIT=1
  ERROR: rd2rd_orri_rd: legality 'no_overlap(...)' 引用了不存在的字段/标识符 'no_overlap'
  ERROR: rb2rb_orri_rb: legality 'no_overlap(...)' 引用了不存在的字段/标识符 'no_overlap'
  验证失败: 2 个错误
```

pre-existing 判定成立：`contracts/opcodes.yaml` 最后改动于 `b0866c8`（SPEC-057t），`git diff HEAD -- contracts/opcodes.yaml` 为空；该 2 错由未实现的 `no_overlap` legality 引起，与本次任务无关（另有 `INTEG-008t` 修复任务）。

##### 2. 载体正确性（逐条对照 D7 §1–§7）

| D7 章节 | 要求 | SimRISC-00 | SimRISC-06 | contract-isa | 判定 |
|---|---|---|---|---|---|
| §1 | `ra0[63:54]`=SBZ / `[53:48]`=`RACNT`(0–63,初始0) / `[47:0]`=`MRPTR`(0=未启用) | L132 | —（不承载 ra0 位域，指向 00） | L94 | ✅ |
| §1 | `ra1`–`ra63[63:48]`=递归计数 / `[47:0]`=返回地址，`ra63` 恒栈顶 | L133–134 | L99/L122（ra63） | L95–96 | ✅ |
| §2 | 有效性判据=`RACNT`（不看条目自身值）；有效条目=自 `ra63` 向下连续 `RACNT` 个；有效区外未定义 | L137 | — | L99 | ✅ |
| §3 | C1 / C2 / C3a / C3b（含 `MRPTR −= 8`、写栈底、`RACNT 保持 63`、`MRPTR==0→RASOF`） | L157–161 | —（L99 指向） | L778–780 | ✅ 4/4 |
| §4 | D1 / D2 / D3 / D4a / D4b（含 D4b 读取+内容判定、`MRPTR += 8` 时机） | L167–172 | —（L122 指向） | L786–789 | ✅ 5/5 |
| §5 | 实现注（环形缓冲+隐藏基准索引，非架构语义） | L174–176 | — | — | ✅ |
| §6 | 精确异常「先完成全部判定，再修改」（含 D4b 读取与内容判定） | L143 | — | L103 | ✅ |
| §7 | RASOF 仅由「需溢出且 `MRPTR==0`」触发；MemRAS 越界交 OS | L142 | — | L102；异常表 L1146–1147 | ✅ |

**D7 §3/§4 全部分支（9 条）在各载体完整性**：SimRISC-00 与 contract-isa **各自完整含 C1/C2/C3a/C3b + D1/D2/D3/D4a/D4b 全部 9 条**（由我的对照器逐条断言，见 §3）。SimRISC-06 仅指向 00，不再展开（符合任务 §2 要求）。

**`ra0` 位域三载体一致性**：承载 `ra0` 位域者为 `SimRISC-00`(L132) 与 `contract-isa`(L94)；两者语义逐字一致，仅 Markdown 加粗标记差异（00 用 `**SBZ**`/`**0 = 未启用 MemRAS**`，contract 未加粗）——**无语义差异**。`SimRISC-06` 不承载 `ra0` 位域（合规，非缺漏）。

##### 3. 反例门控（我自行编写对照器 + 自行注入，≥3 例）

- 对照器：`/tmp/opencode/SPEC-062t/check_d7.py`（reviewer 独立编写，非工程师产出；把 D7 §1–§7 编码为约 40 条 needle 断言）。
- 基线：`python3 check_d7.py /home/ubuntu/DADAO-v5` → `PASS: 全部 D7 对照项通过`，**EXIT=0**。
- 注入均在 `/tmp/opencode/SPEC-062t/inj{A,B,C}/` 的**副本**上进行，逐例隔离（首轮曾因并发共用目录产生串扰，已作废重跑），**仓库零污染**（注入后 `git status --porcelain` 仍为空）。

| 例 | 注入 | 结果 | 复原 |
|---|---|---|---|
| (a) | `有效性判据 = RACNT（不看条目自身的值）` → `有效性判据 = 条目自身高16位（>0 为有效）` | **FAIL EXIT=1**（`§2 判据=RACNT` 缺 + `残留旧语义 '条目自身高16'`） | PASS EXIT=0 |
| (b) | C3b `RACNT 保持 63` → `RACNT −= 1` | **FAIL EXIT=1**（`C3b RACNT 保持 63` 不符） | PASS EXIT=0 |
| (c) | 删除 D1 行 | **FAIL EXIT=1**（`D1 RACNT>0 且 ra63[63:48]==0 → RASUF` 缺失） | PASS EXIT=0 |

⇒ 该门控**可失败**，非恒真。

##### 4. 未触历史/越界（vs `dff2381^`）

```
$ git diff --name-only dff2381^..HEAD
.tao/knowledge/contract-isa.md
.tao/tasks/integ/INTEG-008t-…-validate_encoding…no_overlap….md   ← 另任务（8930aa5）
.tao/tasks/spec/SPEC-061t-…0号寄存器口径修正与登记.md             ← 另任务（dff2381 自身）
.tao/tasks/spec/SPEC-062t-RA语义修订落地.md                       ← 本任务
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-06-控制流.md

$ git diff --name-only dff2381^..HEAD -- spec/SimRISC-0.5.3 <adr-0004/adr-0012> tests/vectors \
      contracts/opcodes.yaml spec/DADAO-21-ABI-应用程序二进制接口.md docs/m1-retrospective.md docs/testcases-009t-audit.md
（无输出）; QEMU 路径亦为 0 命中
```

- 三载体 + 本任务书 = 清单 4 项，均在列；**另多出 2 个「他任务任务书」**（`SPEC-061t`、`INTEG-008t`）。这两项分别来自 `dff2381` 自身（061 任务书）与 `8930aa5`（008t），**属独立提交，不是本任务的越界**。任务书 §验收 8 措辞为「与清单逐项对齐」——实际为「清单 ⊆ 实际」且**禁止项（历史/QEMU/向量/ADR/opcodes）0 改动**，故**判定为合规**（但与 reviewer 预判的「应恰为 4 项」不符，如实记录）。
- `adr-0012`、`adr-0004`、`spec/SimRISC-0.5.3/`、QEMU、向量、旧任务书**均未改动**，约束守住。

##### 5. 约束核验（逐条）

| 约束 | 结果 |
|---|---|
| 仅 ASCII/中文措辞与语义改动 | ✅ 仅 md 文本，无代码/二进制 |
| 不改 `adr-0012` / QEMU / 向量 / 探针 | ✅ 0 改动（`git diff` 证实） |
| 不改历史（`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`） | ✅ 0 改动 |
| 术语：不得出现「上移/下移」 | ✅ `grep` rc=1，0 命中 |
| 「递归计数」写全；符号用 `RACNT`/`MRPTR` | ✅ 三载体一致 |
| 四载体逐条对齐、无遗漏无矛盾 | ✅ §2 对照表逐条通过 |
| 命令缺失/失败 → 停下报告；反例可复原 | ⚠️ 见 §7/§8（反例证据无留存脚本；命令均已完成） |

##### 6. 门控退出口径

`make check` **EXIT=0**、`check_interface_alignment.py` **80/80 EXIT=0**、`validate_encoding.py` **EXIT=1（pre-existing 2 错，与 HEAD 一致）**——与工程师完成区数字**一致**。

##### 7. 发现的问题（阻断项）

**B1（证据层，须修）——反例门控无可复现产物**：完成区「验收 6」仅给出叙述式三例（`注入:`/`D7 §2:`/`结果:`），**无脚本路径、无命令行、无退出码**，属「摘要/叙述」而非可重跑的原始输出——违反「验证脚本必须能失败 + 留证须捕获被检命令自身退出码」。我已自建对照器证实该门控**可**失败，但**工程侧未留存任何可运行产物**（`tools/`、`.work/` 均无该检查器）。

**B2（真实性，须修）——完成区归因错误 + 自相矛盾**：
1. 完成区 L92/L224/L265 反复称「D7 内容**已由 `SPEC-061t`** 在 `dff2381` 落地」。事实：该内容是**本任务（SPEC-062t）产物**，只因主会话 `git add -A` 误扫入 message 为 SPEC-061t 的提交（§0 已证）。此表述与任务书顶部主会话更正注记**直接矛盾**。
2. 同句自相矛盾：既称「**无新增修改**」，又称「本次确认其正确性并**补充异常表 RASOF/RASUF 描述**」——后者是修改动作，二者不能同时为真（经查异常表改动确实包含在 `dff2381` 的 `contract-isa` diff 内）。

**B3（跨文档，供架构师定夺，非本任务范围）——`adr-0004 §D5.5` 残留旧语义**：`.tao/knowledge/adr-0004-test-machine.md` L162–163 仍写「RASOF…**或 MemRAS 引用计数溢出**」「RASUF…**或 MemRAS 引用计数/内容无效**」。D7 §7 明确「**无 MemRAS 引用计数**」，故该 Accepted ADR 的描述已因 D7 落地而过时。任务书 §修改内容 4 仅评估 `adr-0004 §D2.1`，未覆盖 `§D5.5`；且改 Accepted ADR 须经用户确认。**标注为跨文档阻断线索，交架构师决定是否开专门任务**，不据此判本任务内容不合格。

##### 8. engineer 完成区逐条复读（重点：归因）

- **归因不实（须改）**：见 B2.1。工程师把本任务成果记给 `SPEC-061t`；与主会话更正注记冲突。
- **自相矛盾（须改）**：见 B2.2「无新增修改」vs「补充异常表描述」。
- 其余逐条**与我的重跑一致**，无不实：验收 1 对照表行号（L132/L137/L157–161/L167–172/L174–176、contract L94/L99/L778–780/L786–789）我逐行核对**全部准确**；验收 2/3/5/7/8 的结论与真实一致；「`check_interface_alignment.py` 在 `tools/integ/`」「validate_encoding 2 错 pre-existing」属实。
- **唯一证据缺口**：验收 6 无留存脚本/退出码（B1）。

##### 9. 判决

**Needs Revision（Needs Revision 仅限「报告与证据」层；三载体内容本身已由本审查独立核实为正确，无需改内容）**

- **内容层**：D7 §1–§7 已完整、无矛盾地落入三载体；C1–C3b + D1–D4b 共 9 分支在 `SimRISC-00` 与 `contract-isa` 各自完整；残留归零；门控（make check / align）真实通过。**我未发现任何内容性错误。**
- **须返工项**：
  1. **B2**：修正完成区 L92/L224/L265 的归因（三载体内容是 **SPEC-062t** 产物，误入 message=SPEC-061t 的 `dff2381`），删除「已由 SPEC-061t 落地」；消除「无新增修改」与「补充异常表描述」的矛盾（二者择一或说明）。
  2. **B1**：留存可运行的「与 D7 对照」检查器（建议提交至 `tools/spec/` 或至少 `.work/SPEC-062t/`），并在完成区贴**真实命令行 + `cmd > log 2>&1; rc=$?` 的退出码**：基线 PASS、三例注入 FAIL、复原 PASS。可直接复用本审查留在 `/tmp/opencode/SPEC-062t/check_d7.py` 的思路（或自建等价物）。
  3. **清单对齐**：完成区 §验收 8 应如实列出 vs `dff2381^` 的 6 项并说明多出的 `SPEC-061t`/`INTEG-008t` 任务书属他任务提交（非本任务越界）。
- **交架构师定夺（不阻碍本任务内容）**：B3（`adr-0004 §D5.5` 旧语义）是否另开任务 / 就地修订（须用户确认）。

**证据留存**：`/tmp/opencode/SPEC-062t/{make_check.log, align.log, valenc.log, check_d7.py}`；注入副本 `/tmp/opencode/SPEC-062t/inj{A,B,C}/`；仓库 `git status` 干净、三载体 blob 与 `dff2381` 相同。

#### 第 2 轮 engineer 返工

**返工范围**：仅报告/证据层（B1 反例门控可复现 + B2 归因与矛盾修正），三载体实质内容不动。

##### B1：反例门控可复现

**新增对照器**：`tools/spec/check_d7_consistency.py`（提交到仓库，约 120 行 Python，校验 D7 §1–§7 ↔ 三载体的 40 条 needle 断言）。

**基线**：
```
$ python3 tools/spec/check_d7_consistency.py .
PASS: 全部 D7 对照项通过
EXIT=0
```

**注入 (a)：有效性判据改回「条目自身高16位」**（副本 `/tmp/opencode/SPEC-062t/r2/injA/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injA
FAIL: 4 项不符
  - [s00] 缺少/不符: §2 判据=RACNT
  - [cis] 缺少/不符: §2 判据=RACNT
  - [s00] 残留旧语义: 条目自身高16
  - [cis] 残留旧语义: 条目自身高16
EXIT=1
```

**注入 (b)：C3b `RACNT 保持 63` → `RACNT −= 1`**（副本 `/tmp/opencode/SPEC-062t/r2/injB/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injB
FAIL: 2 项不符
  - [s00] 缺少/不符: C3b RACNT 保持 63
  - [cis] 缺少/不符: C3b RACNT 保持 63
EXIT=1
```

**注入 (c)：删除 D1 行**（副本 `/tmp/opencode/SPEC-062t/r2/injC/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/injC
FAIL: 2 项不符
  - [s00] 缺少/不符: D1
  - [cis] 缺少/不符: D1
EXIT=1
```

**复原后 PASS**（干净副本 `/tmp/opencode/SPEC-062t/r2/restored/`）：
```
$ python3 tools/spec/check_d7_consistency.py /tmp/opencode/SPEC-062t/r2/restored
PASS: 全部 D7 对照项通过
EXIT=0
```

##### B2：归因与矛盾修正

**修改内容**（diff 摘要）：
- L92「修改文件」：删除「无新增修改（D7 内容已由 SPEC-061t 落地）」→ 改为如实列出产物（三载体改动 + 对照器），说明三载体改动被误扫入 `dff2381` 的事实。
- L224「新发现/坑」：删除「已由 SPEC-061t 落地」→ 改为「本任务产物，误入 `dff2381`」。
- L265/L297 engineer 自审「发现」：同上归因修正。
- L294「git diff 为空（无新增修改）」→ 改为如实列出 diff 内容。
- 验收 8：补充 `git status --name-only` 真实输出 + 6 项清单对齐说明。
- 消除「无新增修改」与「补充异常表 RASOF/RASUF 描述」的矛盾：本任务确有产物（三载体 + 异常表补充 + 对照器），三载体改动被误提交到 `dff2381`，对照器本轮新增。

##### 门控退出码（本轮重跑）

```
$ make check ; echo "EXIT=$?"
EXIT=0
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/integ/check_interface_alignment.py ; echo "EXIT=$?"
EXIT=0
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml ; echo "EXIT=$?"
EXIT=1（2 errors: no_overlap — pre-existing，与 HEAD 一致）

$ git diff --name-only
.tao/tasks/spec/SPEC-062t-RA语义修订落地.md

$ git status --porcelain
 M ".tao/tasks/spec/SPEC-062t-RA语义修订落地.md"
?? tools/spec/check_d7_consistency.py
```

**遗留问题**：B3（`adr-0004 §D5.5` 旧语义）不在本轮范围，已上报用户待确认。

#### 第 2 轮 reviewer 复核

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**审查时间**：2026-09-30
**范围**：仅 B1/B2 + 三载体未变 + 门控 + 未触其它（B3 不在本轮）

##### 1. B1 可复现（我亲自跑，非转述）

**基线**（仓库根）：
```
$ python3 tools/spec/check_d7_consistency.py . ; echo "EXIT=$?"
PASS: 全部 D7 对照项通过
EXIT=0
```

**我自行做的 3 例注入**（各在 `/tmp/opencode/SPEC-062t/r2verify/inj{A,B,C}/` 隔离副本，仅复制三载体）：
```
=== injA（判据改回条目自身高16）===
FAIL: 4 项不符
  - [s00] 缺少/不符: §2 判据=RACNT  (needle='有效性判据 = RACNT（不看条目自身的值）')
  - [cis] 缺少/不符: §2 判据=RACNT  (needle='有效性判据 = RACNT（不看条目自身的值）')
  - [s00] 残留旧语义: 条目自身高16  (found='条目自身高16')
  - [cis] 残留旧语义: 条目自身高16  (found='条目自身高16')
EXIT=1
=== injB（C3b `RACNT 保持 63` → `RACNT -= 1`）===
FAIL: 2 项不符
  - [s00] 缺少/不符: C3b RACNT 保持 63  (needle='RACNT 保持 63')
  - [cis] 缺少/不符: C3b RACNT 保持 63  (needle='RACNT 保持 63')
EXIT=1
=== injC（删 D1 行）===
FAIL: 2 项不符
  - [s00] 缺少/不符: D1  (needle='D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF')
  - [cis] 缺少/不符: D1  (needle='D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF')
EXIT=1
=== restored（未注入副本）===
PASS: 全部 D7 对照项通过
EXIT=0
```

**零污染**：全部注入仅在 `/tmp` 副本；注入期间与之后 `git status --porcelain` 均为空。

**判别力判定：非恒真，有真实断言。** `need()` 实际断言 `needle ∈ norm(文件文本)`。抽查：needle `'D1 RACNT > 0 且 ra63[63:48] == 0 → RASUF'` 对应 `SimRISC-00` L167 / `contract-isa` L786（我逐字核对原文）；删该行后即 FAIL（例 c 证明 FAIL 路径可达）。故对照器非空断言。**弱项提示（非阻断）**：`need('cis','RASUF',…)` 仅查子串存在，判别力弱（任何含 `RASUF` 的文本都过）；但整体门控可失败。

##### 2. B2 归因与矛盾

- **归因已更正**：完成区 L92/L255/L297 已改为「三载体是 **SPEC-062t** 产物，被 `git add -A` 误扫入 message=SPEC-061t 的 `dff2381`」；不再出现「已由 SPEC-061t 落地」（残留字样仅在「第 1 轮 reviewer」引用旧错误时出现，属正常留档）。✅
- **「无新增修改」矛盾已消除**：完成区不再声称「无新增修改」，改为如实列出产物（三载体 + 异常表补充 + 对照器）。✅
- **残留不实（须修）**：完成区 §验收 8（L251）称「`git diff --name-only dff2381^..HEAD` 包含 6 项：三载体 + 本任务书 + SPEC-061t 任务书 + INTEG-008t 任务书」。**我实跑为 7 项**：
```
$ git diff --name-only dff2381^..HEAD | wc -l
7
（.tao/knowledge/contract-isa.md；INTEG-008t 任务书；SPEC-061t 任务书；SPEC-062t 任务书；
 spec/SimRISC-00…；spec/SimRISC-06…；tools/spec/check_d7_consistency.py）
```
  即遗漏了本 commit `fd51651` **自身新增**的 `tools/spec/check_d7_consistency.py`。该表述与真实输出矛盾（此命令是 HEAD 相对范围，`fd51651` 提交后项数由 6 变 7）。
- **次要（不作阻断）**：验收 6 称对照器「共静态 35 条 needle 断言（运行时展开 65 项）」；静态调用点实为 35（`need` 32 + `forbid` 3），含 `for` 循环展开的运行时断言为 65。建议可直接写实际条数。

##### 3. 三载体未变

```
$ git diff --stat fd51651^..fd51651 -- spec/ .tao/knowledge/contract-isa.md
（空）; RC=0
```
三载体在返工 commit 内**零改动**，返工未动三载体。✅

##### 4. 门控（我重跑，真实退出码）

```
$ make check ; EXIT=0
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  全部机械可判定项 PASS。

$ python3 tools/integ/check_interface_alignment.py ; EXIT=0
  总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0

$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml ; EXIT=1
  ERROR: rd2rd_orri_rd: legality 'no_overlap(rdhb, rdhc, immu6)' 引用了不存在的字段/标识符 'no_overlap'
  ERROR: rb2rb_orri_rb: legality 'no_overlap(rbhb, rbhc, immu6)' 引用了不存在的字段/标识符 'no_overlap'
  验证失败: 2 个错误

$ git diff --stat HEAD -- contracts/opcodes.yaml
（空）; RC=0   ← opcodes.yaml 未改，EXIT=1 为 pre-existing
```
✅ 与完成区数字一致。

##### 5. 未触其它

```
$ git diff --name-only fd51651^..fd51651
".tao/tasks/spec/SPEC-062t-RA语义修订落地.md"
tools/spec/check_d7_consistency.py
```
恰为 2 项（任务书 + 对照器），与要求一致。禁止项（`spec/SimRISC-0.5.3/`、`adr-0004`、`adr-0012`、QEMU、向量、`docs/`、`contracts/opcodes.yaml`、ABI）`git diff` **0 改动**。✅

##### 6. 判决

**Needs Revision**（**仅报告层一处数字不准；三载体内容与 B1 门控均已核实无误**）

- **通过项**：B1 对照器**存在、可运行、非恒真**——基线 PASS EXIT=0，我自行 3 例注入均 FAIL EXIT≠0，复原 PASS EXIT=0，仓库零污染；B2 归因更正与「无新增修改」矛盾消除**均已落实**；三载体未变；门控 `make check`/`align` EXIT=0、`validate_encoding` pre-existing EXIT=1；未触 QEMU/向量/ADR/历史。
- **须返工项（仅 1 处）**：完成区 §验收 8（L251）「`dff2381^..HEAD` 包含 **6 项**」→ 实为 **7 项**，须补入 `tools/spec/check_d7_consistency.py`（或改写为不含本 commit 的行数并注明口径）。属报告与真实输出不一致，按「完成区结论须与真实输出逐条对齐」须修。
- **建议（不阻断）**：验收 6 的「约 40 条」宜写实际条数（静态 35 / 运行时 65）。
- **不在本轮**：B3（`adr-0004 §D5.5`）仍待用户/架构师定夺。

**证据留存**：`/tmp/opencode/SPEC-062t/r2verify/{make_check.log, align.log, valenc.log, injA, injB, injC, restored}`；复核时仓库 `git status --porcelain` 为空。

#### 第 3 轮 reviewer 复核（最小确认）

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**审查时间**：2026-09-30
**范围**：仅第 2 轮唯一阻断项（L251 计数）+ 非阻断建议（L177 条数）+ 三载体未变 + 门控。

##### (i) L251/L177 与真实一致 —— 通过

```
$ git diff --name-only dff2381^..HEAD | wc -l
7
$ git diff --name-only dff2381^..HEAD
.tao/knowledge/contract-isa.md
.tao/tasks/integ/INTEG-008t-....md
.tao/tasks/spec/SPEC-061t-....md
.tao/tasks/spec/SPEC-062t-RA语义修订落地.md
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-06-控制流.md
tools/spec/check_d7_consistency.py
```
7 项与 L251 所列（三载体 + 本任务书 + SPEC-061t + INTEG-008t + 对照器）**逐项吻合**。✅

L177 条数：脚本静态调用点 `need` 32 + `forbid` 3 = **35**（`grep -c` 得 33/4，各含 1 处 `def`，故实为 32/3）；`for` 循环运行时展开 10+9+16+16+2+6+4+2 = **65 项**。与 L177「静态 35 条（运行时展开 65 项）」一致。✅

##### (ii) 三载体未被本轮改动 —— 通过

```
$ git diff 90d3b84^..90d3b84 -- spec/ .tao/knowledge/contract-isa.md
（空）
$ git diff --name-only 90d3b84^..90d3b84
".tao/tasks/spec/SPEC-062t-RA语义修订落地.md"
```
`90d3b84` 仅改任务书 1 文件（107+/2-），`spec/` 与 `contract-isa.md` **零改动**。✅

##### (iii) 门控 —— 通过

```
$ make check > /tmp/opencode/SPEC-062t/review3-makecheck.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)
repository checks: PASS
$ python3 tools/spec/check_d7_consistency.py . ; echo "EXIT=$?"
PASS: 全部 D7 对照项通过
EXIT=0
```
（退出码直接取自命令，未经管道。）

##### (iv) 无其它返工项 —— 通过

- 第 2 轮唯一阻断项（L251 6→7）已按实修正并注明口径；非阻断建议（约 40 条 → 静态 35/运行时 65）亦已落实。
- 三载体工作树无 diff，禁止项（`SimRISC-0.5.3`/`adr-0004`/`adr-0012`/QEMU/向量/`contracts/opcodes.yaml`/ABI/`docs/`）0 改动。
- **非阻断观察**：完成区 §验收 8 的 `git status --porcelain` 快照（L242–244，显示 `M 任务书` + `?? 对照器`）是 `fd51651` 提交前的返工现场留档，HEAD 现为 clean（我实跑 `git status --porcelain` 0 行）。该块已由「本轮返工修改/本轮新增对照器」注明时点，且最终态结论由 L251/L252 承载，**不构成矛盾，不作返工**。

##### 判决

**Accepted**（第 2 轮阻断项已修复；三载体、门控、条数均经独立重跑核实一致）

- 通过：L251 计数 7（实跑吻合）、L177 静态 35/运行时 65（枚举吻合）、三载体零改动、`make check` EXIT=0、对照器基线 PASS EXIT=0。
- 未发现其它返工项。
- 不在本轮：B3（`adr-0004 §D5.5` 旧语义）仍待用户/架构师定夺。

**证据留存**：`/tmp/opencode/SPEC-062t/review3-makecheck.log`。
