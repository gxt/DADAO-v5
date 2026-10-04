# SPEC-078t: spec 文档迁移到新汇编格式（131 条）+ 术语 `cfxcode→cfxha`

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-077t`（检测器支持 `[N]`；**最终清单 131**）
**ADR**：`ADR-0013`（新语法 D1–D9）、`ADR-0017`（cfx 别名 D3/D4/D7/D10）
**状态**：已验证

## 目标

把 spec 文档中的旧格式汇编迁移到新语法，使 `SPEC-076t` 检测器**归零**；并统一 `cfxcode→cfxha` 术语。

## 迁移对象（`check_asm_prose.py` 的 131 条）

| 文件 | 条数 |
|---|---|
| `spec/DADAO-22-SBI-…` | **107** |
| `spec/DADAO-11-AEE-…` | **16** |
| `spec/DADAO-23-HBI-…` | **1** |
| `.tao/knowledge/adr-0004-test-machine.md`（示例）| **7** |

## 迁移规则（**已由实现实测确定**，不得改变示例语义 ✗）

1. **访存**：加地址括号 ⇒ `ld.st rd2, [rbN, off]`；
   - **ABI 别名须替换为真实寄存器**：`rbsp` ⇒ **`rb1`**（SP；规范 §2.5「ABI 别名当前 MUST NOT 使用」；实测 `[rbsp, 4]` 报错）。**先查 `contract-abi §1.2` 确认 `rbsp` 别名对应，再做替换**。
   - **符号偏移保留**：`[rb1, x_offset]`（实测 `[rb2, x_offset]` 可汇编 ✓）。
2. **跳转/分支**：`br.*` 条件用 `{…}?`、目标用 `[rb0, …]`；**标签目标保留在括号内**（实测 `br.n {rd0}?, [rb0, L1]` ✓）；`jump`/`call` **立即数加 `i`**（`[rb0, 2i]`）；`jump/call` rrii 形 `[rbN, rdM, 24i]`；`cs.*` 用 `{…}?`。
3. **`escape`**：`escape cfxHA, [excp_cause_ip, Ni]`（`ADR-0013 §cfx`；`escape cfx_smon, 1` ⇒ `escape cfx_smon, [excp_cause_ip, 1i]`）。
4. **双目的**：`add.so rd0, rd4, rd2, rd3` ⇒ `add.so {rd0, rd4}, rd2, rd3`（`R6` 8 条）。
5. **cfx2rd/cfx2rc**：保持**别名形**（`cfx_<name>[N], rdM` 或 `cfx_<name>, rdM`）✓（`SPEC-077t` 后不再是违规）。

## 附带勘误（spec 正文，非新决策）

6. **`docs/spec/assembly-language.md §3.1` 漏写"符号"**：`立即数偏移 ::= 立即数[单位后缀]` **不含符号/标签**，但**实现与 lit 均接受**（`[rb2, x_offset]`、`[rb0, L1]` 实测 rc=0）⇒ 补为 `立即数偏移 ::= 立即数[单位后缀] | 符号`，并在 §3.3 补标签/符号示例。（属**勘误**：文档与既定实现对齐 ✗ 不改语义。）

## 术语清扫 `cfxcode → cfxha`

- **改**：`spec/DADAO-12`(52)、`spec/DADAO-13`(8)、`spec/DADAO-21`(1)、`spec/DADAO-22`(3)、`spec/DADAO-23`(1)、`spec/SimRISC-11`(1)、`.tao/knowledge/contract-isa.md`(2)、`.tao/knowledge/MEMORY.md`(1)、`.tao/knowledge/adr-0004-test-machine.md`(9)。
- **不改** ✗（**记录改名本身，必须保留**）：`adr-0013`、`adr-0017`；以及历史（`SimRISC-0.5.3/`、`m1-retrospective.md`、`testcases-009t-audit.md`、`self-consistency.md`）。

## 验收标准（须真实可失败）

1. **检测器归零**：`python3 tools/spec/check_asm_prose.py` = **0 违规**（全库）✓；`--strict` **EXIT=0**。
2. **术语归零**：`grep -rn cfxcode` 在**生效文件**（排除上述"不改"清单）= **0**（逐条说明豁免）✓。
3. **语义保真**：逐条对照**迁移前/后**，确认示例含义不变（尤其 `rbsp→rb1`、标签/符号偏移不变）✓。
4. **实现抽验**：从迁移后的文档取 ≥5 段汇编（含访存/分支/双目的/escape/cfx），用 `llvm-mc`（`--triple=dadao-unknown-elf -filetype=obj`）汇编通过（若某段含未定义符号/伪指令而无法独立汇编，**说明原因**并改用语义对照 ✓）。
5. **`make check` EXIT=0**；lit **22/22**（本任务**不改 `.s`** ✗）。
6. **不碰** ✗：`tests/vectors/**`、LLVM/QEMU、`adr-0013`/`adr-0017`、历史文件。
7. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败/无法映射的构造 ⇒ **停下报告** ✗。

## 完成区

**测试结果**：make check EXIT=0；lit 22/22（不改 .s）；check_asm_prose.py 0 违规；--strict EXIT=0

**修改文件（含逐文件条数）**：

| 文件 | 汇编迁移条数 | cfxcode→cfxha 条数 | 备注 |
|---|---|---|---|
| `spec/DADAO-22-SBI-…` | **107**（R2×52, R3×50, R6×5） | 3 | +1行内 escape（F5） |
| `spec/DADAO-11-AEE-…` | **16**（R1×11, R2×2, R6×3） | — | |
| `spec/DADAO-23-HBI-…` | **1**（R3×1） | 1 | |
| `.tao/knowledge/adr-0004-test-machine.md` | **7**（R1×5, R2×2） | 9 | |
| `spec/DADAO-12-SEE-…` | 4行内 escape（F5） | 52 | |
| `spec/DADAO-13-HEE-…` | — | 8 | |
| `spec/DADAO-21-ABI-…` | — | 1 | |
| `spec/SimRISC-11-…` | — | 1 | |
| `.tao/knowledge/contract-isa.md` | — | 2 | |
| `.tao/knowledge/MEMORY.md` | — | 1 | |
| `docs/spec/assembly-language.md` | — (errata §3.1/§3.3) | — | |
| `tools/spec/gen_cfx_aliases.py` | — (parser 适配 + docstring F6) | — | |

逐文件/逐规则分解（`git stash` 回原始态实测）：

| 文件 | R1 | R2 | R3 | R6 | 合计 |
|---|---|---|---|---|---|
| DADAO-22 | 0 | 52 | 50 | 5 | 107 |
| DADAO-11 | 11 | 2 | 0 | 3 | 16 |
| DADAO-23 | 0 | 0 | 1 | 0 | 1 |
| adr-0004 | 5 | 2 | 0 | 0 | 7 |
| **全库** | **16** | **56** | **51** | **8** | **131** |

**检测器归零证据（前后）**：
- 迁移前：`check_asm_prose.py` 报 **131** 违规（R1×16, R2×56, R3×51, R6×8）
- 迁移后：`check_asm_prose.py` = **0 违规**；`--strict` EXIT=0

**术语 grep 归零 + 豁免清单**：
- `grep -rn cfxcode` 在9个生效文件 = **0**
- 豁免（保留 cfxcode，逐条说明）：
  - `adr-0013` L125：记录改名本身（`cfxcode→cfxha`）—1 处
  - `adr-0017` L5/L12：引用 cfxcode↔cfxname 表 —2 处
  - `SimRISC-0.5.3/`（历史）—不改
  - `self-consistency.md`（历史）—不改
  - `docs/m1-retrospective.md`（历史）—不改（2处 cfxcode）

**语义保真对照（抽样）**：

| # | 迁移前 | 迁移后 | 语义 |
|---|--------|--------|------|
| 1 | `ld.st rd2, rbsp, x_offset` | `ld.st rd2, [rb1, x_offset]` | rbsp→rb1（ABI别名替换），地址语义不变 |
| 2 | `add.so rd0, rd4, rd2, rd3` | `add.so {rd0, rd4}, rd2, rd3` | 双目的花括号，操作数顺序不变 |
| 3 | `br.nz rd2, overflow_handler` | `br.nz {rd2}?, [rb0, overflow_handler]` | 条件组+标签保留在括号内 |
| 4 | `escape cfx_smon, 1` | `escape cfx_smon, [excp_cause_ip, 1i]` | 1→1i（指令字单位），基址excp_cause_ip |
| 5 | `jump rb3, rd0, 0` | `jump [rb3, rd0, 0i]` | rrii 地址表达式，0→0i |
| 6 | `escape cfx_power, 0` | `escape cfx_power, [excp_cause_ip, 0i]` | 0 表示重试（cause_ip+0），语义不变 |

**`llvm-mc` 抽验输出**：
- 访存：`ld.st rd2, [rb1, x_offset]` / `st.t rd4, [rb1, z_offset]` / `ld.o rd16, [rb17, 1]` / `st.o rd0, [rb16, 0]` → **rc=0** ✓
- 分支：`br.nz {rd18}?, [rb0, 4]` / `br.eq {rd2, rd3}?, [rb0, 8]` / `br.n {rd5}?, [rb0, 12]` → **rc=0** ✓
- 双目的+jump：`add.so {rd0, rd4}, rd2, rd3` / `mul.so {rd0, rd4}, rd2, rd3` / `jump [rb3, rd0, 0]` → **rc=0** ✓
- escape/cfx2rd/cfx2rc：**无法汇编**（Excluded from M1，LLVM MC 未实现该指令）→ 语义对照见上表

**验收结果**：`make check` EXIT=0（含80项接口对齐、227编码验证、146语义门控、cfx-aliases 字节一致）；lit 22/22；detector 0

**新发现/坑**：
- `gen_cfx_aliases.py` 的 `parse_cfxcode_table()` 硬编码了 `cfxcode` 作为表头匹配，术语改名后需同步更新（已修，改为接受 `cfxcode` 或 `cfxha`）
- `escape`/`cfx2rd`/`cfx2rc` 属 Excluded from M1，llvm-mc 不支持其新语法，只能做语义对照
- 迁移脚本会压缩多余空白（`ld.st    rd2` → `ld.st rd2`），属风格归一化，不影响语义
- **检测器能力缺口**：`check_asm_prose.py` 只扫围栏代码块（` ``` `），不覆盖 markdown 表格/散文中的行内 code span（`` `escape cfxha, 1` ``）。DADAO-12 L670-672/L674 和 DADAO-22 L11 各有1处行内 escape 旧格式，本次已人工补迁移。建议 `INFRA-021t` 评估是否扩展检测器覆盖行内 code span。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：全部12个修改文件，131条汇编迁移 + 77条术语替换 +2条勘误

**逐项审查**：

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | R1（访存16条）：`rbsp→rb1` + `[rbN, off]` | ✅ | DADAO-11 全部 rbsp→rb1；adr-0004 用 rb16/rb17（非ABI别名，不替换） |
| 2 | R2（跳转56条）：`{…}?` + `[rb0, label/imm]` | ✅ | br.eq/br.ne → `{rd, rd}?`；br.n/br.nz → `{rd}?`；jump rrii → `[rb, rd, immi]` |
| 3 | R3（escape51条）：`[excp_cause_ip, Ni]` | ✅ | 含 `escape cfx_power,0→[excp_cause_ip, 0i]`（重试语义） |
| 4 | R6（双目的8条）：`{dst1, dst2}, src1, src2` | ✅ | add.so/mul.so 共8条，仅出现在 DADAO-11 |
| 5 | cfx2rd/cfx2rc 保持别名形 | ✅ | 未触碰这些行（SPEC-077t 后不再是违规） |
| 6 | §3.1 补「符号」 | ✅ | `立即数偏移 ::= 立即数[单位后缀] \| 符号` |
| 7 | §3.3 补标签/符号示例 | ✅ | 新增2行：访存符号偏移 + 条件分支标签 |
| 8 | cfxcode→cfxha 生效文件=0 | ✅ | 9文件全部0；adr-0013/0017 保留3处 |
| 9 | gen_cfx_aliases.py 适配 | ✅ | parse 匹配改为接受 cfxcode 或 cfxha |
| 10 | 不碰 files 列表 | ✅ | tests/vectors/**、LLVM/QEMU、adr-0013/0017、SimRISC-0.5.3/ 均未触碰 |

**发现与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| gen_cfx_aliases.py 硬编码 cfxcode 表头 | ✅已修 | 改为 `cells[0] in ("cfxcode", "cfxha")` | `python3 gen_cfx_aliases.py` EXIT=0，`check-cfx-aliases` PASS |
| 空白压缩（ld.st  多空格→单空格） | ✅已确认 | 脚本自动归一化，不影响语义 | diff 逐行核对，操作数内容不变 |

**判决**：全部 finding 已修，可标「待验收」。
#### 第 1 轮 reviewer 验收
（Needs Revision：F1-F6 见下）
#### 第 2 轮 engineer 返工

**F1（DADAO-22 分解数字）**：原写 `R2×56, R3×43, R6×8` ⇒ 实测 `R2×52, R3×50, R6×5`。**✅已修**（`git stash` 回原始态重跑 checker 逐行提取）。

**F2（DADAO-11 分解数字）**：原写 `R1×10, R6×4` ⇒ 实测 `R1×11, R6×3`。**✅已修**。

**F3（adr-0017 行号）**：原写 `L5/L43` ⇒ 实为 `L5/L12`。**✅已修**。

**F4（豁免遗漏）**：原豁免清单漏列 `docs/m1-retrospective.md`（2处 cfxcode）。**✅已补**。

**F5（DADAO-12 行内 escape 未迁移）**：
- DADAO-12 L670-672：markdown 表格中 `` `escape cfxha, 0` `` / `1` / `N` ⇒ 改为 `` `escape cfxha, [excp_cause_ip, 0i]` `` / `1i` / `Ni`。**✅已修**。
- DADAO-12 L674：散文中 `` `escape cfx_A, N` `` ⇒ 改为 `` `escape cfx_A, [excp_cause_ip, Ni]` ``。**✅已修**。
- DADAO-22 L11：散文中 `` `escape cfxha, 1` `` ⇒ 改为 `` `escape cfxha, [excp_cause_ip, 1i]` ``。**✅已修**。
- **结论**：检测器 `check_asm_prose.py` 只扫围栏代码块，不覆盖行内 code span ⇒ 属**能力缺口**，已在完成区「新发现/坑」登记，建议 `INFRA-021t` 评估扩展。

**F6（docstring）**：`gen_cfx_aliases.py` L6 `cfxcode↔cfxname` ⇒ `cfxha↔cfxname`。**✅已修**。

**复验**：
- `check_asm_prose.py --strict` EXIT=0 ✓
- `make check` EXIT=0 ✓
- `llvm-lit` 22/22 ✓
- `git diff --name-only`：12文件（含 DADAO-12 追加3处行内 escape 修复）

> 审查者独立重跑；工作目录 `/mnt/tao/DADAO-v5`；证据 `/tmp/opencode/SPEC-078t-r1/`。**未采信完成区**。

**1. 重跑记录（真实输出 / 退出码）**

| # | 命令 | 真实结果 |
|---|------|---------|
| 1 | `python3 tools/spec/check_asm_prose.py` | `check-asm-prose: PASS (0 violations)`；**EXIT=0** |
| 2 | `python3 tools/spec/check_asm_prose.py --strict` | **EXIT=0** |
| 3 | 检测器反例注入（临时 `spec/zz_reviewer_inject.md`，5 行旧格式） | 报 **5 违规**（R1×1, R2×2, R3×1, R6×1）；`--strict` **EXIT=1**；删除后复跑 **0 / EXIT=0**（检测器**可失败**，非恒 PASS；注入文件已清理） |
| 4 | `git archive HEAD` → `/tmp/…/head` 跑检测器（迁移前） | **131 违规**：R1×16, R2×56, R3×51, R6×8 |
| 5 | `make check` | **EXIT=0**；80/80 接口对齐、`validate_encoding` 227 条 OK、`check-qemu-semantics` 146/146、`check-cfx-aliases: PASS (byte-identical)`、`check-dirs: PASS` |
| 6 | `.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/` | **Passed: 22/22 (100.00%)，EXIT=0** |
| 7 | `python3 tools/spec/gen_cfx_aliases.py --verify` | `check-cfx-aliases: PASS (byte-identical)`，**EXIT=0**；重生成后 `docs/spec/cfx-aliases.md` **无 diff**（**幂等**） |
| 8 | `llvm-mc --triple=dadao-unknown-elf -filetype=obj`（10 段） | 访存 `ld.st rd2,[rb1,x_offset]`／`st.t rd4,[rb1,z_offset]`／`ld.o rd16,[rb17,1]`／`st.o rd0,[rb16,0]`；分支 `br.nz {rd2}?,[rb0,overflow_handler]`／`br.eq {rd2,rd3}?,[rb0,cfx_smon_unknown]`／`br.nz {rd18}?,[rb0,4]`／`br.eq {rd2,rd3}?,[rb0,8]`／`br.n {rd5}?,[rb0,12]`；双目的 `add.so {rd0,rd4},rd2,rd3`／`mul.so {rd0,rd4},rd2,rd3`；`jump [rb3,rd0,0i]` → **全部 rc=0** |
| 9 | `escape cfx_smon,[excp_cause_ip,1i]`／`cfx2rd cfx_smon_excp_cause_id,rd2`／`cfx2rc cfx_ptw_ptbr[0],rd17` | **rc=1**（`expected ',' after base register`／`unrecognized instruction mnemonic`）→ 与完成区「Excluded from M1，llvm-mc 无法汇编」**一致** |
| 10 | 9 个生效文件 `grep -c cfxcode` | 逐个 **0** |
| 11 | `git diff --name-only`（`core.quotepath=false`） | **12 文件**；`tests/**`、`.s`、`components/`、`.work/`、`adr-0013/0017`、历史文件**均未动** |

**2. 语义保真（最关键）——逐项对照 HEAD vs 工作树**

- **访存 `[...]`**：`ld.st rd2, rbsp, x_offset` → `ld.st rd2, [rb1, x_offset]`。`rbsp` 确为 SP——`contracts/abi.yaml` L29 `stack_pointer: rb1`、L30 `stack_pointer_abi_name: rbsp`；`contract-abi.md §2.1` `SP = rb1（rbsp）`。**别名替换正确**；`x_offset/y_offset/z_offset` 等**符号偏移原样保留**。
- **分支/跳转**：`br.ne rd2, rd3, L` → `br.ne {rd2, rd3}?, [rb0, L]`；`br.n/br.nz rdN, L` → `{rdN}?`。**条件寄存器顺序与标签名均原样保留在 `[...]` 内**（逐行核对 DADAO-11/22、adr-0004，无抽样）。
- **`jump`/`call` 偏移**：全部发生处为 `jump rb2/rb3, rd0, 0` → `jump [rb2/rb3, rd0, 0i]`，**偏移量恒为 0**（`0i`=0 指令字）；**无任何非零偏移被改动**。
- **`escape` 立即数**：`escape cfx_smon, 1` → `[excp_cause_ip, 1i]`。`assembly-language.md §3.2` 定义 escape 返回地址 = `excp_cause_ip + imm×4`（指令字）；`1i` = 1 指令字 = 4 字节，与旧 `escape …, 1` **语义一致**（DADAO-12 §5 表：`1 → cause_ip+4`；`0 → cause_ip`）。
- **双目的**：`add.so rd0, rd4, rd2, rd3` → `add.so {rd0, rd4}, rd2, rd3`（`{dst1,dst2}, src1, src2`）：**目的对 `{rd0,rd4}`、源 `rd2,rd3` 顺序与原一致**。
- **结论：未发现任何语义改动。**

**3. 约束核验（逐条）**

- 检测器归零 ✓（0，严格 EXIT=0）；反例可失败 ✓。
- 术语：9 生效文件 cfxcode=0 ✓；`adr-0013`（1 处，**L125**）/`adr-0017`（**L5、L12**，2 处）保留 ✓。
- 勘误 §3.1 `立即数偏移 ::= 立即数[单位后缀] | 符号` + §3.3 两条示例 ✓；`[rb2,x_offset]`/`[rb0,L1]` 实测 rc=0 ✓。
- `make check` EXIT=0 ✓；lit 22/22 ✓；`.s` 未改 ✓。
- 未越界：仅 12 文件；`adr-0013/0017`、`tests/vectors/**`、LLVM/QEMU、历史文件未动 ✓。

**点 2（语义保真）表态：通过——逐行核对后未发现语义改动。**

**点 5（生成器适配）表态：功能通过，非最严，判非阻断。** `parse_cfxcode_table()` L54 由 `cells[0] == "cfxcode"` 改为 `cells[0] in ("cfxcode", "cfxha")`；DADAO-12 表头已改 `cfxha`（L20），生成器不随之更新会解析为空，故改动必要。改后 `make check-cfx-aliases` **PASS（byte-identical）**、生成器**幂等**、漂移门控（重生成 vs 归档逐字节比对）**未被弱化**。唯一松动：若将来把 DADAO-12 表头**回退**为 `cfxcode`，本门控不再因表头报错（严格 `== "cfxha"` 才会）。表头名非本门控职责、术语另有评审 ⇒ **非阻断**。

**4. 发现**

| # | 严重度 | 位置 | 问题 | 真实值（本次重跑） |
|---|--------|------|------|--------------------|
| F1 | **中（阻断）** | 完成区「修改文件」表 DADAO-22 行 | 规则分解 `R2×56, R3×43, R6×8` 与真实 pre-log **不符**，且与全库总计（R2×56/R6×8）**自相矛盾** | **R2×52, R3×50, R6×5**（合计 107 ✓） |
| F2 | **中（阻断）** | 完成区「修改文件」表 DADAO-11 行 | `R1×10, R6×4` 错误（R2×2 正确） | **R1×11, R6×3**（合计 16 ✓） |
| F3 | 低 | 完成区豁免清单 | `adr-0017` 行号写成 `L5/L43` | 实为 **L5 / L12** |
| F4 | 低 | 完成区豁免清单 | 漏列 `docs/m1-retrospective.md`（属任务书"不改"历史文件，仍含 2 处 `cfxcode`） | — |
| F5 | 低（非阻断，建议） | `DADAO-12 §5` L670–672、`DADAO-22` L11 | 术语已改 `cfxha`，但 escape **位置形** `escape cfxha, 0/1/N` 未随语法迁移为 `[excp_cause_ip, Ni]`（散文/表格，**不在检测器 131 内**） | 规范正形见 `assembly-language.md §5`：`escape cfx63, [excp_cause_ip, 1i]` |
| F6 | 低（非阻断） | `tools/spec/gen_cfx_aliases.py` L6 | 模块 docstring 仍写 `cfxcode↔cfxname table`（源表头已改 `cfxha`），与已改的函数 docstring（L41）不一致 | — |

> 说明：完成区术语条数（D12=52、adr-0004=9 等）经核为**按行计**，与 HEAD 的行数一致，**不算错**（按出现次数为 55/12，属口径差异）。pre-log 全量（131；R1×16, R2×56, R3×51, R6×8）与完成区一致。

**5. 判决：Needs Revision**

- 交付物本身（12 个变更文件的汇编迁移 / 术语替换 / 勘误）经独立重跑，**7 条验收标准全部通过，语义保真无问题**；
- 但完成区 **F1/F2 的逐文件规则分解数字与真实输出不符且内部自相矛盾**（`D22 全库 R2×56` 又给 `D11 R2×2`；`R6×8` 全库又给 `D11 R6×4`），F3/F4 豁免清单行号/条目不实 —— 违反「完成区结论须与真实输出逐条对齐」；
- 返工范围**仅限任务书完成区文字**：改正 F1–F4（建议一并处理 F5/F6），**无需改动已迁移的 12 个文件内容**。

#### 第 2 轮 reviewer 复核

> 审查者独立重跑；工作目录 `/mnt/tao/DADAO-v5`；证据 `/tmp/opencode/SPEC-078t-r2/`。**未采信完成区**（F1/F2 独立用 `git archive HEAD` 树重算）。

**1. 重跑记录（真实输出 / 退出码）**

| # | 命令 | 真实结果 |
|---|------|---------|
| 1 | `python3 tools/spec/check_asm_prose.py; echo $?` | `check-asm-prose: PASS (0 violations)`；**EXIT=0** |
| 2 | `python3 tools/spec/check_asm_prose.py --strict; echo $?` | **EXIT=0** |
| 3 | `git archive HEAD` → `/tmp/…/head` 跑检测器并 **awk 按文件×规则聚合** | **131**：D11 `R1×11,R2×2,R6×3`=16；D22 `R2×52,R3×50,R6×5`=107；D23 `R3×1`=1；adr-0004 `R1×5,R2×2`=7；全库 `R1×16,R2×56,R3×51,R6×8` |
| 4 | `make check` | **EXIT=0**；80/80 机械项 PASS；`validate_encoding` 227 OK；`check-qemu-semantics` 146/146；`check-cfx-aliases: PASS (byte-identical)`；`check-dirs: PASS` |
| 5 | `.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/` | **Passed: 22/22 (100.00%)**；**EXIT=0** |
| 6 | `python3 tools/spec/gen_cfx_aliases.py --verify` | `check-cfx-aliases: PASS (byte-identical)`；**EXIT=0** |
| 7 | 9 个生效文件逐个 `grep -c cfxcode` | 全部 **0**；`docs/spec/cfx-aliases.md` **0** |
| 8 | `git diff --name-only` | **12 文件**；`*.s`=0、`tests/`=0、`adr-0013/0017`=0 |

**2. 逐项对应**

- **① F1/F2 数字**：重算（#3）与完成区表**逐条一致**（D22 `R2×52,R3×50,R6×5`；D11 `R1×11,R2×2,R6×3`）且与全库总计 `R1×16/R2×56/R3×51/R6×8=131` 自洽 ⇒ **通过与实跑对齐**。
- **② F3/F4**：`grep -n cfxcode .tao/knowledge/adr-0017*.md` → **L5、L12**（与实跑一致，非 L5/L43）；`docs/m1-retrospective.md` 含 cfxcode **2 处**（L209、L352），已列入豁免 ⇒ **已更正 / 已补**。
- **③ F5 行内 escape**：工作树 diff 确认迁移 **5 行** code span —— D12 `L670/671/672`（`[excp_cause_ip, 0i/1i/Ni]`）+ `L674`（`escape cfx_A, [excp_cause_ip, Ni]`）+ D22 `L11`（`escape cfxha, [excp_cause_ip, 1i]`）。**语义保真**：`assembly-language.md` §157 定义第二参数为「以 `excp_cause_ip` 为基址的指令字偏移」，故 `0i→cause_ip`、`1i→cause_ip+4`、`Ni→cause_ip+N×4`，与旧 `escape …, 0/1/N` **逐值一致**。能力缺口**已登记**于「新发现/坑」（明言检测器只扫围栏码块、不含行内 code span，建议 `INFRA-021t` 评估）⇒ **非静默略过**。
  - **低（非阻断）观察**：完成区「修改文件」表 D12 行写「**3行内 escape**（F5）」，而同段 F5 明细列出 `L670-672` **及 L674**（实为 4 行）；即表汇总比明细少 1 行。F5 明细已完整枚举、无隐藏，且行内迁移不计入 131（不影响任何总计），故**不阻断**；建议一并把该格改为「4 行内 escape」。
- **④ F6**：`tools/spec/gen_cfx_aliases.py` L6 docstring = `cfxha↔cfxname table`，与 D12 源表头 L20 `| cfxha | cfxname | 说明 |` **一致** ⇒ **已更正**。
- **⑤ 无内容回归**：#1/#2 检测器仍 **0 / --strict EXIT=0**（`check_asm_prose.py` 本轮**未改**，第 1 轮可失败性结论仍成立）；`grep cfxcode` 生效文件 **0**；`make check` **EXIT=0**；lit **22/22**；`*.s` **未改** ⇒ **通过**。
- **⑥ 改动范围**：`git diff --name-only` = **12 文件**（含 D14 行内修复）＝D11/D12/D13/D21/D22/D23/SimRISC-11 + 3 knowledge + assembly-language.md + gen_cfx_aliases.py，与任务书「修改文件」清单一致；`tests/**`、`.s`、`adr-0013/0017`、`SimRISC-0.5.3/` 未动 ⇒ **通过**。

**3. 约束核验（逐条）**

- 检测器归零 ✓；术语生效文件归零 ✓；语义保真 ✓；`make check` EXIT=0 ✓；lit 22/22 ✓；不改 `.s` ✓；退出码用 `cmd; echo $?`（未吞码）✓。
- 未见改契约/spec 测试强制通过、未见弱化断言（F5 为**新增**迁移，非规避；能力缺口显式登记并要求后续任务评估）。

**4. 判决：Accepted**

- 第 2 轮确认项①–⑥全部在我自己的重跑下成立；F1/F2/F3/F4 已按实跑更正且自洽，F5 迁移正确且缺口已登记，F6 已更正，无内容回归、无越界改动。
- 唯一遗留为**文档计数 nit**（D12 表汇总「3 行内」vs 明细 4 行，非阻断，F5 明细完整）。
- 支持主会话将该任务置为 `已验证`；最终接受仍由架构师终审。


#### 主会话收尾（2026-10-02）

1. **提交推送**：spec 文档迁移（131→0）+ 术语 `cfxcode→cfxha`（生效文件 0）+ §3.1 勘误 + 生成器 parser 兼容 `cfxcode`/`cfxha` 表头（见 git log）。
2. **过程**：reviewer 第 1 轮 Needs Revision（**内容实质正确、语义保真逐行核过**；仅完成区 F1/F2 数字不实 + F3/F4 小项 + F5/F6 非阻断）→ 返工 → 第 2 轮 **Accepted**（reviewer 用 `git archive HEAD` **独立重算**逐条对齐：D22 R2×52/R3×50/R6×5、D11 R1×11/R2×2/R6×3、全库 16/56/51/8=131）。
3. **F5**：`DADAO-12` 4 行 + `DADAO-22` 1 行**行内** `escape` 已迁移为 `escape cfxHA, [excp_cause_ip, Ni]`（语义保真）。
4. **登记能力缺口**：`check_asm_prose.py` 只扫**围栏代码块**，**不含行内 code span**（本次 F5 为人工补迁移）⇒ 供 `INFRA-021t` 评估扩展。
5. **非阻断观察**：完成区 `DADAO-12` 行「3行内 escape」已更正为 **4**。
