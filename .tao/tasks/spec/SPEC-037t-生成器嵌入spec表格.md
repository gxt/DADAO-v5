# SPEC-037t: 重构生成器——按类别输出汇编表格到 spec 文件

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`LLVM-017t` + `LLVM-018t`（生成器渲染逻辑已更新，表格内容由渲染决定）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tools/llvm/gen_asm_list.py`（已支持双目的/多寄存器渲染）、`contracts/opcodes.yaml`、`spec/SimRISC-XX-*.md`（12 个文件）
- 输出：12 个 `spec/SimRISC-XX-*.md` 文件（嵌入汇编表格）、`docs/assembly-list.md`（保持不变）
- 约束：
  - 生成器按类别自动输出到对应 spec 文件，不手动复制
  - `spec/` 目录可由 spec 模块任务修改（ADR-0012 D4）
  - 依赖 `LLVM-017t`+`LLVM-018t` 的理由：表格的「汇编形式」列由渲染逻辑决定（双目的 `{...}`、多寄存器 `{start:end}`），渲染变更后必须重跑 `--embed-spec`

## 修改内容

### 1. `tools/llvm/gen_asm_list.py` 新增功能

- 新增 `--embed-spec` 模式：按分类（12 个类别）将表格输出到对应的 `spec/SimRISC-XX-*.md` 文件
- 分类到文件的映射（**12 个文件，01–12**）：

| 分类 | 文件 |
|------|------|
| 取数存数 | `spec/SimRISC-01-取数存数.md` |
| 寄存器复制 | `spec/SimRISC-02-寄存器复制.md` |
| 16位立即数操作 | `spec/SimRISC-03-16位立即数操作.md` |
| 64位数据运算 | `spec/SimRISC-04-64位数据运算.md` |
| 64位地址运算 | `spec/SimRISC-05-64位地址运算.md` |
| 控制流 | `spec/SimRISC-06-控制流.md` |
| 浮点运算 | `spec/SimRISC-07-浮点运算.md` |
| 32位数据运算 | `spec/SimRISC-08-32位数据运算.md` |
| 16位数据运算 | `spec/SimRISC-09-16位数据运算.md` |
| 8位数据运算 | `spec/SimRISC-10-8位数据运算.md` |
| 其它 | `spec/SimRISC-11-其它.md` |
| 待定 | `spec/SimRISC-12-待定.md` |

- 表格插入位置：紧接在 spec 文件的 `> **版本/分类**` 头部之后、正文之前
- 表格节标题：`## 汇编指令速查`
- 表格格式：保留全部列（助记符 | format | feature | 汇编形式 | id），与 `assembly-list.md` 一致
- 使用标记注释（`<!-- ASSEMBLY_LIST_START -->` / `<!-- ASSEMBLY_LIST_END -->`）界定生成区域，便于幂等更新
- 幂等性：重跑不改变非生成区域的内容
- 生成区域包含 `### <类>（N 条）` 标题行（与 `assembly-list.md` 章节标题一致）

### 2. deferred 章节处理

浮点运算（SimRISC-07）和待定（SimRISC-12）的表格仍嵌入（格式已定义），但加 `**deferred**` 标注。

### 3. 新增一致性 checker（建议）

新增 `tools/spec/check_asm_list_consistency.py`：
- 比对 `spec/SimRISC-XX-*.md` 中 `<!-- ASSEMBLY_LIST_START/END -->` 区域的内容与 `gen_asm_list.py --embed-spec` 的输出
- 不一致则 exit 1
- 接入 `make check`

## 验收标准

1. 运行 `python3 tools/llvm/gen_asm_list.py --embed-spec` 后，**12 个** spec 文件（01–12）各包含对应类别的汇编表格
2. 表格位于 `> **版本/分类**` 头部之后、正文之前，节标题为 `## 汇编指令速查`
3. 表格前后有 `<!-- ASSEMBLY_LIST_START -->` / `<!-- ASSEMBLY_LIST_END -->` 标记
4. 表格内容与 `docs/assembly-list.md` 对应章节逐字节一致（含 `### <类>（N 条）` 标题行）
5. 重跑 `--embed-spec` 不改变非生成区域（幂等性验证：重跑前后 `git diff` 仅含时间戳变化）
6. `docs/assembly-list.md` 的默认输出不受影响（`-o` 行为不变）
7. deferred 章节（07/12）的表格有 `**deferred**` 标注
8. 生成器无 `--embed-spec` 时行为与修改前完全一致（向后兼容）
9. `make check` 通过（无回归）
10. 若实现了一致性 checker：`python3 tools/spec/check_asm_list_consistency.py` exit 0

## 完成区
**测试结果**：12/12 spec 文件嵌入正确；幂等验证通过；`make check` EXIT=0
**修改文件**：
- `tools/llvm/gen_asm_list.py`：新增 `--embed-spec` 模式、`CLASS_TO_SPEC` 映射、`_section_content()`、`embed_spec()`
- `tools/spec/check_asm_list_consistency.py`（新建）：一致性 checker
- `Makefile`：新增 `check-asm-list` target，接入 `make check`
- `spec/SimRISC-01-取数存数.md` ~ `spec/SimRISC-12-待定.md`（12 个文件）：嵌入汇编表格
**验收结果**：
- 12 个 spec 文件嵌入结果：
  | 文件 | 类别 | 表格行数 |
  |------|------|---------|
  | SimRISC-01 | 取数存数 | 38 |
  | SimRISC-02 | 寄存器复制 | 18 |
  | SimRISC-03 | 16位立即数操作 | 8 |
  | SimRISC-04 | 64位数据运算 | 29 |
  | SimRISC-05 | 64位地址运算 | 4 |
  | SimRISC-06 | 控制流 | 15 |
  | SimRISC-07 | 浮点运算 | 46（deferred） |
  | SimRISC-08 | 32位数据运算 | 26 |
  | SimRISC-09 | 16位数据运算 | 26 |
  | SimRISC-10 | 8位数据运算 | 26 |
  | SimRISC-11 | 其它 | 6 |
  | SimRISC-12 | 待定 | 12（deferred） |
- 幂等验证：重跑 `--embed-spec` 无 diff ✓
- `docs/assembly-list.md` 默认输出不受影响 ✓
- deferred 章节（07/12）有 `**deferred**` 标注 ✓
- 默认模式（无 `--embed-spec`）行为与修改前完全一致 ✓
- `make check` 真实输出：`repository checks: PASS`（EXIT=0）✓
- 一致性 checker 反例验证：注入错值 → exit 1；移除标记 → exit 1 ✓
**新发现/坑**：
- 头部检测逻辑需注意：spec 文件 `#` 标题行在 `>` 头部之前，循环必须用 `in_header` 标志追踪「已进入 `>` 块」状态，否则会因标题行不以 `>` 开头而立即 break，导致 `header_end=0`（初次实现的 bug）
- 嵌入内容与 `docs/assembly-list.md` 逐字节一致，但多了 `## 汇编指令速查` 节标题（spec 文件需要此标题作为正文前的导航锚点）
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 头部检测 `else: break` 导致 `header_end=0`（标题行不以 `>` 开头） | ✅已修 | 改为 `in_header` 标志：`elif in_header: break` | 重跑后 spec 文件头部保留，`head -6` 输出正确 |
| 12 个文件表格内容逐字节比对 | ✅已验 | — | Python 脚本比对12个分类全部 MATCH |
| 幂等性 | ✅已验 | — | 重跑前后 `git diff --stat` 内容一致 |
| 反例门控：checker 能检测错值 | ✅已验 | — | 注入 `ra→XX` → exit 1；移除标记 → exit 1 |
| `make check` 无回归 | ✅已验 | — | `make check` EXIT=0 |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，未采信完成区转述）
**审查基线**：工作树 `7e05aa5` + 未提交改动（15 个文件）。审查过程未修改真实仓库任何文件。

##### 重跑记录（均为审查者本人执行，退出码为命令自身退出码）

**R1. `make check`**
```
$ make check > /tmp/opencode/SPEC-037t-makecheck.log 2>&1; echo "EXIT=$?"
EXIT=0
$ grep -n asm-list /tmp/opencode/SPEC-037t-makecheck.log
29:check-asm-list-consistency: 12 spec files OK
$ tail -1 /tmp/opencode/SPEC-037t-makecheck.log
repository checks: PASS
```

**R2. 一致性 checker（repo root）**
```
$ python3 tools/spec/check_asm_list_consistency.py; echo "EXIT=$?"
check-asm-list-consistency: 12 spec files OK
EXIT=0
```
从其它 cwd 调用同样通过（ROOT 由 `__file__` 解析）：
```
$ cd /tmp && python3 /home/ubuntu/DADAO-v5/tools/spec/check_asm_list_consistency.py; echo $?
check-asm-list-consistency: 12 spec files OK
EXIT_FROM_TMP=0
```

**R3. 幂等（md5 before/after，12 个文件全量）**
```
$ find spec -name 'SimRISC-0*.md' -o -name 'SimRISC-1*.md' | sort | xargs md5sum > before.md5
$ python3 tools/llvm/gen_asm_list.py --embed-spec; echo "GEN_EXIT=$?"
GEN_EXIT=0   （打印 12 行 embedded …（N 条）-> …）
$ find spec -name 'SimRISC-0*.md' -o -name 'SimRISC-1*.md' | sort | xargs md5sum > after.md5
$ diff before.md5 after.md5 && echo "IDEMPOTENT: no diff"
IDEMPOTENT: no diff
```

**R4. 与 `docs/assembly-list.md` 逐字节比对（12/12）**
独立解析 `docs/assembly-list.md` 的 `### <类>（N 条）` 章节，与 spec 嵌入区（去掉 `## 汇编指令速查` 节标题后）逐行比对：
```
取数存数: header=True table=True rows=40/40
寄存器复制: header=True table=True rows=20/20
16位立即数操作: header=True table=True rows=10/10
64位数据运算: header=True table=True rows=31/31
64位地址运算: header=True table=True rows=6/6
控制流: header=True table=True rows=17/17
浮点运算: header=True table=True rows=48/48
32位数据运算: header=True table=True rows=28/28
16位数据运算: header=True table=True rows=28/28
8位数据运算: header=True table=True rows=28/28
其它: header=True table=True rows=8/8
待定: header=True table=True rows=14/14
```
（行数 = `### 标题` + 表头 + 分隔 + N 行；`### 标题` 与全部数据行逐字节相同。）

**R5. 反例注入（在 `/tmp/opencode/SPEC-037t-copy/` 的隔离副本上执行，真实仓库未触碰）**
```
=== baseline ===
check-asm-list-consistency: 12 spec files OK          BASELINE=0
=== T1: 改错「汇编形式」值（spec 05，add.si rbHA→XXHA）===
FAIL: 64位地址运算: content mismatch in SimRISC-05-64位地址运算.md
1 inconsistency(ies) found, 11 OK                      T1_EXIT=1
=== T2: 删除 START 标记（spec 02）===
FAIL: 寄存器复制: no ASSEMBLY_LIST markers in SimRISC-02-寄存器复制.md
1 inconsistency(ies) found, 11 OK                      T2_EXIT=1
=== T3: 改错 format 单元格（spec 04，rrrr→orrr）===
FAIL: 64位数据运算: content mismatch in SimRISC-04-64位数据运算.md
1 inconsistency(ies) found, 11 OK                      T3_EXIT=1
=== T4: 删除一行数据行（spec 01，ld.ub 行）===
FAIL: 取数存数: content mismatch in SimRISC-01-取数存数.md
  expected 44 lines, got 43 lines
1 inconsistency(ies) found, 11 OK                      T4_EXIT=1
```
T1–T4 全部 exit=1，checker 具备可达的 FAIL 路径，非「只会报 PASS」。

**R6. 默认模式（无 `--embed-spec`）向后兼容**
```
$ python3 tools/llvm/gen_asm_list.py -o /tmp/opencode/SPEC-037t-default.md
gen-asm-list: 254 entries -> /tmp/opencode/SPEC-037t-default.md
$ diff -q /tmp/opencode/SPEC-037t-default.md docs/assembly-list.md
DEFAULT OUTPUT == docs/assembly-list.md
```
`docs/assembly-list.md` 在本次未改动（`git status` 未列出），且默认输出与其逐字节相同。

**R7. 12 个文件标记界定与位置（独立脚本核对）**
```
SimRISC-01: START@5 after last '>'@3 -> True; END@51; title=True; sec_hdr=True
SimRISC-02: START@5 after last '>'@3 -> True; END@31; title=True; sec_hdr=True
SimRISC-03: START@5 after last '>'@3 -> True; END@21; title=True; sec_hdr=True
SimRISC-04: START@5 after last '>'@3 -> True; END@42; title=True; sec_hdr=True
SimRISC-05: START@5 after last '>'@3 -> True; END@17; title=True; sec_hdr=True
SimRISC-06: START@5 after last '>'@3 -> True; END@28; title=True; sec_hdr=True
SimRISC-07: START@5 after last '>'@3 -> True; END@59; title=True; sec_hdr=True
SimRISC-08: START@5 after last '>'@3 -> True; END@39; title=True; sec_hdr=True
SimRISC-09: START@5 after last '>'@3 -> True; END@39; title=True; sec_hdr=True
SimRISC-10: START@5 after last '>'@3 -> True; END@39; title=True; sec_hdr=True
SimRISC-11: START@5 after last '>'@3 -> True; END@19; title=True; sec_hdr=True
SimRISC-12: START@5 after last '>'@3 -> True; END@25; title=True; sec_hdr=True
```
`ASSEMBLY_LIST_START/END` 各出现 1 次（12 文件），块内含 `## 汇编指令速查` 与正确的 `### <类>（N 条）`；SimRISC-00 计数为 0（正确不嵌入）。
表行数合计 38+18+8+29+4+15+46+26+26+26+6+12 = **254**，与 `contracts/opcodes.yaml` 条目总数一致。
`SimRISC-01~12` 的 `# 标题` / `> **版本` / `> **分类` 均保留（各 1 处），` ```simrisc ` 代码块仍在（01=5, 03=9, 06=9 … 未被删除）。

##### 约束核验（逐条）

| # | 约束/验收标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | 12 个文件（01–12）嵌入对应类别表格 | ✅ | R4/R7 |
| 2 | 表格位于 `> 版本/分类` 之后、正文之前，节标题 `## 汇编指令速查` | ✅ | R7（START 在最后一个 `>` 行之后） |
| 3 | 前后有 `<!-- ASSEMBLY_LIST_START/END -->` | ✅ | R7 |
| 4 | 内容与 `docs/assembly-list.md` 对应章节逐字节一致（含 `### 标题行`） | ✅ | R4（header=True, table=True） |
| 5 | 幂等（重跑无 diff） | ✅ | R3 |
| 6 | `docs/assembly-list.md` 默认输出不受影响 | ✅ | R6 |
| 7 | deferred 章节（07/12）有 `**deferred**` 标注 | ✅ | 嵌入区标题为 `### 浮点运算（46 条）｜ **deferred** — 待浮点专门任务` / `### 待定（12 条）｜ **deferred** — 暂不归类，待必须启用时`；与 docs 一致 |
| 8 | 无 `--embed-spec` 时行为与修改前一致 | ✅ | R6；`git diff gen_asm_list.py` 为纯新增（121/0，无删/改行） |
| 9 | `make check` 通过（无回归） | ✅ | R1 |
| 10 | checker exit 0 | ✅ | R2 |
| 11 | checker「能失败」（反例注入） | ✅ | R5（T1–T4 全 exit 1） |
| 12 | `git diff` 范围：仅 12 spec + gen_asm_list.py + Makefile + checker | ✅ | 见下 |

**改动范围核对**（`git status --porcelain` / `git diff --numstat`）：
- 修改：`Makefile`(7/2)、`tools/llvm/gen_asm_list.py`(121/0)、`spec/SimRISC-01~12`（均为纯新增：48/0、28/0、18/0、39/0、14/0、25/0、56/0、36/0、36/0、36/0、16/0、22/0）
- 新增：`tools/spec/check_asm_list_consistency.py`（untracked）
- 未改动：`docs/assembly-list.md`、`spec/SimRISC-00`、`contracts/` 等
- spec 文件 diff 无删除行（`git diff -- spec | grep '^-'` 为空）→ 标记外正文/代码块未被触碰

##### 非阻断观察（不影响判决）

1. checker 的失败信息在「行数相同但内容不同」时只报 `expected N lines, got N lines`（T1/T3 可见），定位价值有限——属 UX 瑕疵，非正确性缺陷。
2. checker 按任务定义比对的是 `gen_asm_list.py --embed-spec` 的（同源代码路径）输出，而非直接读 `docs/assembly-list.md`；这符合任务书对 checker 的定义，且嵌入内容已由 R4 独立证明与 docs 一致。

##### 判决

**Accepted**

验收命令块在本审查者独立重跑下全部通过（R1–R7），12 条约束无违反，反例注入（T1–T4）证明 checker 具备可达 FAIL 路径，改动范围与任务约束一致且 spec 文件为纯新增（未改契约/未弱化检查）。可提交架构师终审。

#### 第 2 轮 reviewer 验收
（如需返工，在此记录；当前无返工）
