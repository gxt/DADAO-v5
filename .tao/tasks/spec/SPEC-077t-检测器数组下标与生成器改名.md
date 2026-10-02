# SPEC-077t: 检测器接受数组寄存器单下标 + 生成器 `cfxcode→cfxha`

**模块**：spec（tools 侧）
**项目里程碑**：M2
**依赖**：`SPEC-075t`（别名表生成器）、`SPEC-076t`（检测器）
**ADR**：`ADR-0017 D10`（数组 cfx 寄存器单下标 `cfx_<name>[N]` ⇔ `(cfxha,cg,rc=rc_base+N)`）、`ADR-0013 D8.4`（字段改名 `cfxcode→cfxha`）
**状态**：已验证

## 目标（tools 侧两件事，**不迁移 spec 正文**）

1. **检测器 `tools/spec/check_asm_prose.py` 接受单下标**：`cfx_<cfxname>_<regname>[N]` 视为**合法**（`ADR-0017 D10`），当 `N` 落在 `docs/spec/cfx-aliases.md` 该寄存器 `rc` 列范围内时**不报违规**；**越界**（如 `[64]` 超出 `0-63`）或**未知基名**仍报。
2. **生成器 `tools/spec/gen_cfx_aliases.py` 把 `cfxcode` 改 `cfxha`**（`ADR-0013 D8.4`），并**重生成** `docs/spec/cfx-aliases.md`（其表头/第 8 行/第 18 行表列 `cfxcode` ⇒ `cfxha`）。

## 范围外 ✗

- **不迁移** `spec/DADAO-*`/`SimRISC-11`/`contract-isa`/`MEMORY`/`adr-0004` 正文（属 `SPEC-078t`）；
- **不改** `adr-0013`/`adr-0017`（它们**记录改名本身**，必须保留 `cfxcode` 字样 ✗）；
- 不改 LLVM/QEMU、历史文件。

## 验收标准（须真实可失败）

1. **检测器接受 `[N]`**：`python3 tools/spec/check_asm_prose.py` 中 `R3(cfx操作数形)` 由 **16 → 0**；**总数 147 → 131**（`DADAO-22` 123→107?）——以实跑为准，**贴前后对照**；`SimRISC-00..12` 仍 **0** ✓。
2. **越界仍报（反例）** ⚠️：构造 `cfx_ptw_ptbr[64]`（超 `0-63`）⇒ 仍报 R3；`cfx_nosuch_x[0]`（未知基名）⇒ 仍报。复原 byte-identical。
3. **生成器改名**：`grep -c cfxcode docs/spec/cfx-aliases.md` = **0**（且表头列名/来源行均为 `cfxha`）；`make check-cfx-aliases` **PASS**（重生成与产物一致）✓。
4. **幂等**：生成器连跑两次 sha 一致。
5. **`make check` EXIT=0**；检测器仍**未接入** `make check`（接线属 `INFRA-021t`）✓。
6. **未越界**：`git diff --name-only` = `tools/spec/check_asm_prose.py`、`tools/spec/gen_cfx_aliases.py`、`docs/spec/cfx-aliases.md`、任务书；`spec/` 正文未改 ✗。
7. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：全部通过
**修改文件**：`tools/spec/check_asm_prose.py`、`tools/spec/gen_cfx_aliases.py`、`docs/spec/cfx-aliases.md`

**检测器前后对照（R3cfx 16→0；总数 147→131）**：

| 规则 | 改前 | 改后 |
|------|------|------|
| R1(访存缺[]) | 16 | 16 |
| R2(跳转缺[]) | 56 | 56 |
| R3(cfx操作数形) | **16** | **0** |
| R3(escape缺[]) | 51 | 51 |
| R6(rrrr缺{}) | 8 | 8 |
| **total** | **147** | **131** |

逐文件分布（reviewer 亲验实跑）：
- `DADAO-22`：R3(cfx操作数形) **16→0**，total **123→107**（全部 16 条 R3(cfx) 均在此文件）
  - `cfx_ptw_ptbr[0/1/63]`：6 条（`cfx2rc`×3 + `cfx2rd`×3）
  - `cfx_ptw_pthi[0/1/63]`：3 条（仅 `cfx2rc`，无 `cfx2rd` 形）
  - `cfx_ptw_pahi[0/1/63]`：3 条（仅 `cfx2rc`，无 `cfx2rd` 形）
  - `cfx_timer_regs[0]`：2 条（`cfx2rc`×1 + `cfx2rd`×1）
  - `cfx_uart_uart0_regs[0/1]`：2 条（`cfx2rc`×1 + `cfx2rd`×1）
  - 合计 6+3+3+2+2 = **16** ✓
- `DADAO-11`：16→16（不变，无 cfx 操作数形）
- `adr-0004`：7→7（不变）
- `DADAO-23`：1→1（不变）
- `SimRISC-00..12`：0（前后一致）

**越界/未知基名反例证据**：
- `cfx_ptw_ptbr[64]`（超 `0-63`）→ R3 报出 ✓（真实退出码 0，但 2 violations found）
- `cfx_nosuch_x[0]`（未知基名）→ R3 报出 ✓
- 测试文件 `docs/test-counter-spec077t.md` 已复原删除，`git diff --name-only` 无残留

**生成器改名与幂等证据**：
- `grep -c cfxcode docs/spec/cfx-aliases.md` = **0** ✓
- 表头列名 `cfxha`（第 18 行）、来源行 `cfxha↔cfxname`（第 8 行）✓
- `make check-cfx-aliases` EXIT=0 ✓
- 幂等：生成器连跑两次，`sha256 = a489688812939f742548a842ef20d396085fc7363cb10ee0dcd2efcbad5222e0`，一致 ✓

**验收结果**：
- `make check` EXIT=0 ✓
- 检测器未接入 `make check`（`check` target 不含 `check-asm-prose`）✓
- `git diff --name-only` = `docs/spec/cfx-aliases.md`、`tools/spec/check_asm_prose.py`、`tools/spec/gen_cfx_aliases.py`（+ 任务书）✓
- `spec/` 正文未改 ✓

**新发现/坑**：
1. cfx-aliases.md 中的 `[0..7]` 表示**数组下标范围**（N=0..7），而 rc 列的 `8-15` 表示**实际 rc 值**。两者不等价：`cfx_timer_regs[N]` 的 N 是 0-7，rc = 8+N。检测器必须从名称列解析 `[lo..hi]`，不能从 rc 列取。
2. `_CFX_ALIAS_PATTERN` 需要匹配 Unicode 字符 `⟨⟩` 和 `−`（U+2212 MINUS SIGN），正则字符类 `[\w⟨⟩\[\].−\d]` 中 `−` 在 `.` 和 `\d` 之间被解析为字面量（非范围操作符），实测正确。
3. 展开后的模板别名（如 `cfx_ptw_scratch_regs[0..N−1]`）需同时保留完整名（含 `[0..N−1]`）和基础名（不含括号），否则 `[N]` 查找基础名会失败。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/spec/check_asm_prose.py`（+85/-17）、`tools/spec/gen_cfx_aliases.py`（+2/-2）、`docs/spec/cfx-aliases.md`（+2/-2）

**逐行审查发现**：

| # | 文件 | 行 | finding | 判决 |
|---|------|-----|---------|------|
| 1 | check_asm_prose.py | 119 | `_CFX_ALIAS_PATTERN` 正则新增 `⟨⟩\[\].−\d`，Unicode `−` (U+2212) 在字符类中 `.` 和 `\d` 之间是否被当范围操作符？ | ✅已修：Python re 对非 ASCII 字符不识别范围，`−` 为字面量；实测匹配 `cfx_⟨cfxname⟩_scratch_regs[0..N−1]` ✓ |
| 2 | check_asm_prose.py | 149,155 | `re.sub(r"\[\d+\.\.\d+(?:−\d+)?\]$", ...)` 的 `−` 是否需要转义？ | ✅已修：正则中 `−` 为字面量（非 ASCII 连字符），无需转义；实测 base name 提取正确 ✓ |
| 3 | check_asm_prose.py | 165 | range 解析 `bracket_match` 用 `\[(\d+)\.\.(\d+)\]`，不含 `−` 模式——对 `scratch_regs[0..N−1]` 行会 miss | ⏸延后：该行 rc 为 `0−(N−1)`（非数字），`int()` 会抛异常。但当前代码用 `\[(\d+)\.\.(\d+)\]` 只匹配纯数字范围，`N−1` 不匹配→跳过→ranges 不含 scratch_regs→不影响运行。变量大小数组不在本次范围内。 |
| 4 | check_asm_prose.py | 398 | `_is_cfx_alias_form` 默认参数 `cfx_ranges: dict = {}`——可变默认参数风险 | ⏸延后：Python 对默认参数 `{}` 只创建一次，但此处只读不写，无副作用。现有代码风格一致，不改。 |
| 5 | check_asm_prose.py | 411-428 | `[N]` 分支：`first.index("[")` 取第一个 `[`——若别名本身含 `[`（如 `cfx_ptw_ptbr[0..63]`）会错误切割 | ✅已修：`cfx_ptw_ptbr[0..63]` 先命中 `first in cfx_aliases`（exact match）分支，不进入 `[N]` 分支。只有 `cfx_ptw_ptbr[0]`（不在 aliases 中）才会走 `[N]` 分支。逻辑正确 ✓ |
| 6 | gen_cfx_aliases.py | 205,217 | 输出中 `cfxcode`→`cfxha` 改动：只改了 render 函数的两行，docstring 第 6 行的 `cfxcode` 保留 | ✅确认：第 6 行是模块 docstring（描述 spec 源表结构），spec 源表仍叫 `cfxcode`，docstring 如实记录不改。任务要求改「输出里的 cfxcode」，docstring 非输出 ✓ |
| 7 | check_asm_prose.py | scan() | scan 函数新增 `cfx_ranges` 参数但签名中默认 `{}`——所有调用方需传参 | ✅已修：main() 已更新调用 `scan(opcode_formats, cfx_aliases, cfx_ranges)` ✓ |

**判决**：所有 finding 已处置（3 条 ✅已修，2 条 ⏸延后有充分理由），无阻塞项。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查方式**：自建 HEAD 基线 worktree（`git worktree add --detach`，已清理），自跑全部命令；未采信完成区转述。证据留 `/tmp/opencode/SPEC-077t-r1/`。

##### 一、重跑记录（真实输出/退出码）

**1. 检测器前后对照（基线 = HEAD，实跑）**

```
# 基线 worktree（HEAD）
$ python3 tools/spec/check_asm_prose.py   → EXIT=0
--- rule hit statistics ---
  R1(访存缺[]): 16
  R2(跳转缺[]): 56
  R3(cfx操作数形): 16
  R3(escape缺[]): 51
  R6(rrrr缺{}): 8
  total: 147

# 当前工作区
$ python3 tools/spec/check_asm_prose.py   → EXIT=0
  R1(访存缺[]): 16
  R2(跳转缺[]): 56
  R3(escape缺[]): 51
  R6(rrrr缺{}): 8
  total: 131

# 逐文件（violation 条数）
before: DADAO-22=123  DADAO-11=16  adr-0004=7  DADAO-23=1   (合计 147)
after : DADAO-22=107  DADAO-11=16  adr-0004=7  DADAO-23=1   (合计 131)
# DADAO-22 内 R3(cfx操作数形)：before=16 → after=0（清掉的 16 条 = 123−107）
# SimRISC-00..12：before/after 均 0 ✓
```

**2. 单下标接受/越界/未知基名（reviewer 亲自构造反例）**

构造 `docs/test-counter-spec077t-rev.md`（已删除，复原无残留），`--files` 实跑：

```
$ python3 tools/spec/check_asm_prose.py --files docs/test-counter-spec077t-rev.md → EXIT=0
L6: [R3(cfx操作数形)] cfx2rc  cfx_ptw_ptbr[64], rd16
L7: [R3(cfx操作数形)] cfx2rc  cfx_nosuch_x[0], rd16
L10:[R3(cfx操作数形)] cfx2rc  cfx_timer_regs[8], rd16
L12:[R3(cfx操作数形)] cfx2rc  cfx_uart_uart0_regs[64], rd16
```
- `cfx_ptw_ptbr[0]` / `[63]` → **不报** ✓
- `cfx_ptw_ptbr[64]`（超 0-63）→ **报** ✓
- `cfx_nosuch_x[0]`（未知基名）→ **报** ✓
- `cfx_timer_regs[0]` / `[7]` → 不报；`cfx_timer_regs[8]` → 报（见第三点）
- `cfx_uart_uart0_regs[63]` → 不报；`[64]` → 报
- `--strict` 反例：`EXIT=1`，`2 violation(s)`（证明脚本有可达 FAIL 路径，非恒 PASS）✓

**3. 生成器改名 / 幂等**

```
$ grep -c cfxcode docs/spec/cfx-aliases.md   → 0（rc=1）
  第 8 行来源行、第 18 行表头列名均含 cfxha ✓
$ make check-cfx-aliases                      → EXIT=0  check-cfx-aliases: PASS (byte-identical)
$ python3 tools/spec/gen_cfx_aliases.py  (连跑两次) → rc=0, rc=0
  before sha256 = a489688812939f742548a842ef20d396085fc7363cb10ee0dcd2efcbad5222e0
  after1  sha256 = a489688812939f742548a842ef20d396085fc7363cb10ee0dcd2efcbad5222e0
  after2  sha256 = 同                                         → 幂等 ✓
```

**4. `make check`**

```
$ make check   → EXIT=0（real 59s）
  ... 总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  repository checks: PASS
$ sed -n '211p' Makefile | grep -o check-asm-prose  → 空（NOT PRESENT）
  `check:` target = … check-cfx-aliases check-dirs，**不含** check-asm-prose ✓
```

**5. 未越界**

```
$ git diff --name-only
docs/spec/cfx-aliases.md
tools/spec/check_asm_prose.py
tools/spec/gen_cfx_aliases.py
$ git diff --name-only -- spec/            → 空（spec/ 正文未改 ✓）
$ git diff --name-only -- .tao/knowledge/adr-0013-*.md .tao/knowledge/adr-0017-*.md → 空
  grep -c cfxcode adr-0013=1、adr-0017=2（保留 cfxcode，未被动 ✓）
```
（+ 任务书为 untracked 文件；测试文件已删，`git status` 无残留 ✓）

##### 二、逐点结论

1. **检测器接受 `[N]` 且越界仍报** —— **通过**。`[0]/[63]` 不报、`[64]` 报、未知基名报、`--strict` 可失败，均我亲测。
2. **总量 16→0、147→131** —— **通过**（我实跑一致）；逐文件分布见上（`SimRISC-00..12` 仍 0 ✓）。
3. **⚠️ 范围取值来源（判据）** —— **工程师「按名称列」正确**。回 `docs/spec/cfx-aliases.md` 核实：第 145 行 `cfx_timer_regs[0..7]`，其 **rc 列为 `8-15`**，二者确实不等价（名称列 `[0..7]` 是数组下标 N，rc 列 `8-15` 是实际 rc，`rc = rc_base + N`，`rc_base=8`）；源 spec `DADAO-12:591` 同（cg=10, rc=8-15, regname=`cfx_timer_regs[0..7]`）。ADR-0017 D10 亦言「别名表以 `cfx_<…>[lo..hi]` 记整数组，**单下标是其具体化**」⇒ 下标 N 取自名称列 `[lo..hi]`。**若按 rc 列**，则 `cfx_timer_regs[0]`（DADAO-22 实有 2 处）会被判违规、`cfx_timer_regs[8]` 反而放行，另 2 条无法清零，总数将停在 133 而非 131 ⇒ 与验收标准 1 冲突。故**必须按名称列**，工程师实现正确。
   > 设计层备注（非本任务实现缺陷，供架构师定夺）：任务书第 11 行与 `ADR-0017 D10` 文字均写作「N 落在 … **rc 列**的范围」，与 D10 的 `rc=rc_base+N`、「单下标是 `[lo..hi]` 具体化」相矛盾；本任务产出的正确行为是「按名称列 `[lo..hi]`」。建议后续任务修正表述（ADR 属范围外，本任务不得改）。
4. **生成器改名 / 幂等 / 未接线** —— **通过**（grep=0、表头=cfxha、check-cfx-aliases PASS、两次 sha 一致、`check:` 无 check-asm-prose）。
5. **`make check` EXIT=0** —— **通过**。
6. **未越界** —— **通过**（3 个文件 + 任务书；`spec/` 正文未改；adr-0013/0017 保留 cfxcode）。
7. **完成区逐条复读** —— **不通过**（见下）。

##### 三、完成区与真实输出不一致（打回项）

完成区主对照表正确（R1/R2/R3cfx/R3escape/R6 与 total 147→131 全部与实跑一致），但**逐文件分布段落有错且自相矛盾**：

| 完成区表述 | reviewer 实跑 | 差异 |
|-----------|--------------|------|
| `DADAO-22`：R3(cfx操作数形) **14→0** | **16→0** | 差 2 |
| `DADAO-22`：total **123→109** | **123→107** | 差 2（与主表 16→0 也不自洽） |
| `cfx_ptw_pthi[0/1/63]`（**6 处**） | violation **3 条**（该文档仅 `cfx2rc` 形，无 `cfx2rd` 形） | 差 3 |
| `cfx_ptw_pahi[0/1/63]`（**6 处**） | violation **3 条** | 差 3 |
| `cfx_ptw_ptbr[0/1/63]`（6 处） | violation **6 条** | 一致 |
| `cfx_timer_regs[0]`（2 处）、`cfx_uart_uart0_regs[0/1]`（2 处） | 各 2 条 | 一致 |

即：完成区逐文件段落自身「14→0 / 123→109」与其主表「16→0 / 147→131」互相矛盾；且 6+6+6+2+2=22≠16。任务书验收标准 1 已给出提示「`DADAO-22` 123→**107**?」，工程师写成 109，与提示及实跑均不符。违反 AGENTS.md「完成区结论须与真实输出逐条对齐：不得转述、概括或与输出矛盾」，触发复审规则「工程师说 N、你跑出 M ⇒ 打回」。

> 代码/产物本身行为已全部验证正确；**返工范围仅限完成区文字的数值更正**（改写逐文件分布为实测值，或删除该不准确补充；无需改任何代码）。

##### 四、判决

**Needs Revision**。失败约束：完成区逐文件分布数字与真实输出不一致（`14→0`/`123→109` 应为 `16→0`/`123→107`；pthi/pahi 「6 处」应为 3 条），且与完成区自身主表矛盾。验收标准 1–6 与约束 6/7 在我的重跑下全部通过，实现无缺陷；仅需更正完成区数值后复验。

#### 第 2 轮 engineer 返工

**返工原因**：reviewer 判 Needs Revision——完成区逐文件数字与实跑矛盾。

**处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| DADAO-22 R3(cfx) 写 14→0，实为 16→0 | ✅已修 | 完成区逐文件段改为「R3(cfx操作数形) **16→0**，total **123→107**」 | reviewer 实跑与主表一致 |
| DADAO-22 total 写 123→109，实为 123→107 | ✅已修 | 同上 | 123−16=107 ✓ |
| cfx_ptw_pthi 写「6 处」，实为 3 条 | ✅已修 | 改为「3 条（仅 cfx2rc，无 cfx2rd 形）」 | reviewer 实跑 DADAO-22 无 cfx2rd pthi 违规 |
| cfx_ptw_pahi 写「6 处」，实为 3 条 | ✅已修 | 改为「3 条（仅 cfx2rc，无 cfx2rd 形）」 | 同上 |
| 合计 6+3+3+2+2=16 与主表 16→0 自洽 | ✅已修 | 加注「合计 6+3+3+2+2 = **16** ✓」 | 自洽 ✓ |
| 残留文件 docs/test-counter-spec077t-rev.md | ✅已修 | 确认不存在（`find` 无结果，`git status` 无残留） | `git status --short` 仅 3 个 M + 1 个 ??(任务书) |

**不改代码**：`check_asm_prose.py`、`gen_cfx_aliases.py`、`cfx-aliases.md` 均未动，仅改完成区文字。

**`git status` 证据**：
```
 M docs/spec/cfx-aliases.md
 M tools/spec/check_asm_prose.py
 M tools/spec/gen_cfx_aliases.py
?? .tao/tasks/spec/SPEC-077t-*.md
```
无其它残留 ✓

#### 第 2 轮 reviewer 复核（最小确认）

**范围**：仅复核第 1 轮唯一打回项（完成区逐文件数字），并抽验已过项未回归。所有命令为本 session 亲自重跑，证据留 `/tmp/opencode/SPEC-077t-r2/`。

##### 一、重跑记录（真实输出 / 退出码）

**1. 检测器前后对照（基线 = HEAD worktree，非采信）**

```
# 基线：git worktree add --detach /tmp/opencode/SPEC-077t-r2/baseline HEAD（66d8494，已 remove）
$ (baseline) python3 tools/spec/check_asm_prose.py      → EXIT=0
  R1(访存缺[]): 16   R2(跳转缺[]): 56
  R3(cfx操作数形): 16  R3(escape缺[]): 51  R6(rrrr缺{}): 8
  total: 147
  逐文件：adr-0004=7  DADAO-11=16  DADAO-22=123  DADAO-23=1  SimRISC-00..12=0

# 当前工作区
$ python3 tools/spec/check_asm_prose.py                  → EXIT=0
  R1(访存缺[]): 16   R2(跳转缺[]): 56
  R3(cfx操作数形): 0（该行不再出现）  R3(escape缺[]): 51  R6(rrrr缺{}): 8
  total: 131
  逐文件：adr-0004=7  DADAO-11=16  DADAO-22=107  DADAO-23=1  SimRISC-00..12=0
```

**2. R3(cfx) 逐条来源（基线实跑 16 条明细，验证 6+3+3+2+2）**

```
L193 cfx2rc cfx_ptw_ptbr[0]     L195 cfx2rc cfx_ptw_ptbr[1]
L198 cfx2rc cfx_ptw_ptbr[63]    L209/L211/L214 cfx2rd cfx_ptw_ptbr[0/1/63]  → 6
L259/L261/L264 cfx2rc cfx_ptw_pthi[0/1/63]（无 cfx2rd 形）               → 3
L276/L278/L281 cfx2rc cfx_ptw_pahi[0/1/63]（无 cfx2rd 形）               → 3
L563 cfx2rc cfx_timer_regs[0]  L569 cfx2rd cfx_timer_regs[0]             → 2
L655 cfx2rc cfx_uart_uart0_regs[0]  L660 cfx2rd cfx_uart_uart0_regs[1]   → 2
合计 6+3+3+2+2 = 16 ✓（全部在 DADAO-22；123−16=107 ✓）
```

**3. 改名 / 幂等产物 / 接线 / 回归**

```
$ grep -c cfxcode docs/spec/cfx-aliases.md   → 0（grep rc=1，无匹配）
$ grep -n cfxha   docs/spec/cfx-aliases.md   → 第 8/18/34/115 行均含 cfxha
$ make check-cfx-aliases                      → EXIT=0  check-cfx-aliases: PASS (byte-identical)
$ make check                                  → EXIT=0
  Results: 146 total, 146 passed, 0 failed …  repository checks: PASS
$ awk '/^check:/…' Makefile | grep check-    → check: … check-cfx-aliases check-dirs（不含 check-asm-prose）
$ grep -n check-asm-prose Makefile           → 仅 77/249 行（独立 target/help），未接入 check:
```

**4. `git status` 无残留**

```
$ git status --short
 M docs/spec/cfx-aliases.md   M tools/spec/check_asm_prose.py
 M tools/spec/gen_cfx_aliases.py
?? ".tao/tasks/spec/SPEC-077t-检测器数组下标与生成器改名.md"
$ find . -name '*spec077t*' | grep -v .tao/tasks/spec   → 空
$ git diff --name-only -- spec/                          → 空
$ git worktree list                                      → 仅主工作树（baseline 已 remove）
```

##### 二、约束核验

| # | 约束 | 结果 |
|---|------|------|
| 1 | 完成区实跑数字逐条对齐（`DADAO-22` 16→0 / 123→107；total 147→131；pthi·pahi 各 3 条；合计 6+3+3+2+2=16） | **✓ 逐条与我的实跑一致** |
| 2 | 本轮无代码改动（3 个受追踪文件与本轮前一致） | **✓**：mtime `check_asm_prose.py`=13:41:08、`gen_cfx_aliases.py`=13:41:33、`cfx-aliases.md`=13:48:30，均**早于**任务书本轮编辑 13:52:22（也早于/等于 r1 复核窗口）；`git diff --stat` 仍为 `check_asm_prose.py 85 / gen_cfx_aliases.py 4 / cfx-aliases.md 4`，未变 |
| 3 | 已过项未回归（total=131、SimRISC-*=0、check-cfx-aliases PASS） | **✓** 均我亲测 |
| 4 | `git status` 无残留 | **✓** |
| 5 | 无其它返工项 | **✓**（第 1 轮打回项仅「完成区数字」一项，已处置） |

> 说明：第 1 轮已亲验的越界/未知基名反例（`cfx_ptw_ptbr[64]`、`cfx_nosuch_x[0]` 报 R3；`--strict` 可达 FAIL）属完成区未改段落，本轮不涉及改动，未重复构造；其真实性与 `make check`/检测器行为一致。

##### 三、判决

**Accepted**。第 1 轮唯一打回项（完成区逐文件数字）已按实跑更正，且更正后的每个数字（`DADAO-22` **16→0**、total **123→107**、全局 **147→131**、pthi/pahi 各 **3 条**、合计 **16**）在我的独立重跑下**逐条吻合**；无代码改动；4 项已过约束抽验无回归；无残留。实现与产出无缺陷。

> 设计层备注（承第 1 轮，非本任务实现缺陷，供架构师定夺）：任务书第 11 行与 `ADR-0017 D10` 文字将下标范围表述为「**rc 列**」的范围，而实现/正确行为是「按名称列 `[lo..hi]`」（rc 列 `8-15` 是实际 rc，rc=rc_base+N）。建议后续任务修正表述（ADR 属范围外）。


#### 主会话收尾（2026-10-02）

1. **提交推送**：`check_asm_prose.py`（接受 `[N]`）+ `gen_cfx_aliases.py`（`cfxcode→cfxha`）+ `docs/spec/cfx-aliases.md`（重生成）（见 git log）。
2. **过程**：reviewer 第 1 轮 Needs Revision（**仅完成区逐文件数字错**：写 `DADAO-22 14→0`/`total 123→109`/`pthi·pahi 6 处`，实为 `16→0`/`123→107`/各 **3**）→ 返工（只改文字）→ 第 2 轮 **Accepted**（reviewer 亲跑：147→131、DADAO-22 123→107、16 条 R3 明细 6+3+3+2+2 自洽）。
3. **功能**：`[N]` 越界（`[64]`）/未知基名仍报；生成器 `cfxcode`=0；幂等；`make check` EXIT=0；检测器**未接线** `make check`。
4. **设计层备注（待用户授权）**：`ADR-0017 D10` 措辞「`N` 落在 `rc` 列范围」与「`rc=rc_base+N`」自相矛盾；正确为 `N` 落在**名称列 `[lo..hi]`**、`rc=rc_base+N`（`rc_base`=该行 rc 列下界）。**待授权后就地修订 D10 措辞**。
