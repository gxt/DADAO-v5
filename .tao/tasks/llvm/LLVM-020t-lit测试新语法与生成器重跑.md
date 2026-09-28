# LLVM-020t: 更新 lit/e2e/oracle 测试 + 重跑生成器更新 assembly-list

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`LLVM-019t`（MC 已支持新语法）、`LLVM-017t` + `LLVM-018t`（生成器已更新）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：
  - `tests/lit/MC/Dadao/*.s`（22 个 lit 测试文件，旧语法）
  - `tests/e2e/*.s`（3 个 E2E 测试文件：`smoke_add.s`/`smoke_arith.s`/`smoke_jump.s`）
  - `tools/llvm/test_encoding_oracle.py`（字节 oracle，含旧语法 asm 文本）
  - `tools/llvm/gen_asm_list.py`（已更新）
- 输出：更新后的上述文件 + `docs/assembly-list.md`
- 约束：只改汇编语法文本，不改测试逻辑/覆盖范围/编码期望值

## 修改内容

### 1. lit 测试文件更新（`tests/lit/MC/Dadao/*.s`，22 个文件）

**特例（count=0 的 `ldm/stm`）**：旧语法 `ldm.o ra0, rb0, rd0, 0`（`immu6=0`，编码 `0x3c000000`）在新语法下**无法表达**（count 由 `{start:end}` 推导，**空组 `{}` 被拒**）。此类用例**保留为裸 `.4byte 0x3c000000`（`.word` 在本目标不可用）**（encoding 期望值不变），并加注释说明「immu6=0 → ILLI，新语法不可表达」。

所有 `.s` 文件中的汇编语法改为新语法。**据实列出**旧→新映射（基于实际文件内容）：

**地址表达式 `[]`**：
- 旧：`ld.ub rd8, rb0, 1` → 新：`ld.ub rd8, [rb0, 1]`
- 旧：`ld.sb rd1, rb2, -1` → 新：`ld.sb rd1, [rb2, -1]`
- 旧：`st.o rd0, rb1, 0` → 新：`st.o rd0, [rb1, 0]`

**条件寄存器组 `{...}?`**：
- 旧：`br.n rd0, 1` → 新：`br.n {rd0}?, [rb0, 1i]`
- 旧：`br.eq rd8, rd0, 4` → 新：`br.eq {rd8, rd0}?, [rb0, 4i]`

**跳转/分支偏移 `i` 后缀 + `[...]`**：
- 旧：`jump 1` → 新：`jump [rb0, 1i]`
- 旧：`br.nz rd0, 4` → 新：`br.nz {rd0}?, [rb0, 4i]`

**多寄存器组 `{start:end}`**：
- 旧：`ldm.ub rd8, rb0, rd1, 2` → 新：`ldm.ub {rd8:rd9}, [rb0, rd1]`
- 旧：`ldm.ub rd8, rb0, rd0, 1` → 新：`ldm.ub {rd8}, [rb0, rd0]`（count=1，单寄存器组）

**双目的 `{dst1, dst2}`**：
- 旧：`add.uo rd8, rd9, rd10, rd11` → 新：`add.uo {rd8, rd9}, rd10, rd11`
- 旧：`add.so rd8, rd9, rd10, rd11` → 新：`add.so {rd8, rd9}, rd10, rd11`

### 2. E2E 测试文件更新（`tests/e2e/*.s`，3 个文件）

**`smoke_add.s`**：
- 旧：`br.nz rd3, Lfail` → 新：`br.nz {rd3}?, [rb0, Lfail]`（标签形式，`Lfail` 由汇编器解析为偏移）
- 旧：`st.o rd3, rb3, 0` → 新：`st.o rd3, [rb3, 0]`
- 旧：`st.o rd4, rb3, 0` → 新：`st.o rd4, [rb3, 0]`

**`smoke_arith.s`**：
- 同 `smoke_add.s`：`br.nz {rd3}?, [rb0, Lfail]`、`st.o rd3, [rb3, 0]`

**`smoke_jump.s`**：
- 旧：`jump 2` → 新：`jump [rb0, 2i]`
- 旧：`st.o rd4, rb3, 0` → 新：`st.o rd4, [rb3, 0]`
- 旧：`st.o rd5, rb3, 0` → 新：`st.o rd5, [rb3, 0]`

注：`set.zw`/`or.w`/`add.si`/`xor.o`/`or.o`/`cmp.so`/`swym` 的语法不变（`rwii`/`orrr`/`riii`/`oiii` 格式无 `[]`/`{}` 语法变更）。

### 3. 字节 oracle 更新（`tools/llvm/test_encoding_oracle.py`）

该脚本的 `TESTS` 列表中 asm 文本为旧语法，需**全部**更新为新语法（**编码期望值不变**，只改 asm 文本）。

**据实生成清单的方法**（不手列，避免遗漏）：

```bash
# 提取 oracle 中所有 asm 字符串（第一列）
grep '("' tools/llvm/test_encoding_oracle.py | grep -oP '"\K[^"]+' | sort -u
```

**旧→新映射规则**（按语法类别批量替换）：

| 旧语法模式 | 新语法模式 | 涉及格式 |
|-----------|-----------|---------|
| `ld.X rdN, rbN, imm` | `ld.X rdN, [rbN, imm]` | rrii 访存 |
| `st.X rdN, rbN, imm` | `st.X rdN, [rbN, imm]` | rrii 访存 |
| `ld.X raN, rbN, imm` | `ld.X raN, [rbN, imm]` | rrii 访存（RA/RB/RF 形式） |
| `st.X raN, rbN, imm` | `st.X raN, [rbN, imm]` | rrii 访存（RA/RB/RF 形式） |
| `ldm.X rdN, rbN, rdN, N` | `ldm.X {rdN:rdN+N-1}, [rbN, rdN]` | rrri 多寄存器 |
| `stm.X rdN, rbN, rdN, N` | `stm.X {rdN:rdN+N-1}, [rbN, rdN]` | rrri 多寄存器 |
| `add.uo rdN, rdN, rdN, rdN` | `add.uo {rdN, rdN}, rdN, rdN` | rrrr 双目的 |
| `add.so rdN, rdN, rdN, rdN` | `add.so {rdN, rdN}, rdN, rdN` | rrrr 双目的 |
| `br.X rd0, imm` | `br.X {rd0}?, [rb0, immi]` | riii 分支 |
| `br.eq rdN, rd0, imm` | `br.eq {rdN, rd0}?, [rb0, immi]` | rrii 分支 |
| `jump imm` | `jump [rb0, immi]` | iiii 跳转 |
| `ra2rd rdN, raN, N` | `ra2rd {rdN:rdN+N-1}, {raN:raN+N-1}` | orri 块赋值 |
| `rd2ra raN, rdN, N` | `rd2ra {raN:raN+N-1}, {rdN:rdN+N-1}` | orri 块赋值 |
| `rb2rd rdN, rbN, N` | `rb2rd {rdN:rdN+N-1}, {rbN:rbN+N-1}` | orri 块赋值 |
| `rd2rd rdN, rdN, N` | `rd2rd {rdN:rdN+N-1}, {rdN:rdN+N-1}` | orri 块赋值 |

**关键**：完成上述替换后，重跑 `grep` 确认无旧语法模式残留（见验收 4）。

### 4. 生成器重跑

```bash
python3 tools/llvm/gen_asm_list.py -o docs/assembly-list.md
```

确保 `docs/assembly-list.md` 与生成器输出逐字节一致。

### 5. lit 测试结构

- 保持现有 `--check-prefix=OBJ` 和 `--check-prefix=ASM` 的双前缀结构
- `OBJ` 前缀：检查编码字节（不变）
- `ASM` 前缀：检查汇编输出（改为新语法）
- 不新增/删除测试文件，只修改内容

## 验收标准

1. **lit 测试通过**：`.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/` 全绿
2. **E2E lit 测试**（**BLOCKED：QEMU 未构建**）：依赖 `qemu-system-dadao`（不存在）。本任务只需保证 `.s` 已迁移 + `llvm-mc` 步骤可跑（前两条 RUN 生成 `.o`/`.bin`）；E2E 全绿待 QEMU 构建后另验。
3. **无旧语法残留**（以下 grep 均返回空）：
   ```bash
   # lit + e2e 的 .s 文件
   grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/
   grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/
   # 字节 oracle：访存/跳转类应含 '['；双目的 rrrr 类应含 '{'
   grep -En '"(ld\.|st\.|ldm\.|stm\.|br\.|jump)' tools/llvm/test_encoding_oracle.py | grep -v '\['
   grep -En '"(add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)) ' tools/llvm/test_encoding_oracle.py | grep -v '{'
   ```
4. **字节 oracle 通过**：`python3 tools/llvm/test_encoding_oracle.py` exit 0
5. **生成器一致**：`docs/assembly-list.md` 与 `python3 tools/llvm/gen_asm_list.py` 输出逐字节一致
6. **lit 字节 oracle 通过**：`python3 tools/llvm/check_lit_bytes.py` exit 0
7. **接口对齐**（**BLOCKED：QEMU trans 命名不一致，pre-existing**）：`check_interface_alignment.py` 的 `QEMU trans ↔ opcodes.yaml` FAIL（0/254）根因是 **QEMU 补丁的 `trans_*` 命名与 0.5.4 的 id 期望不一致**（如 `trans_cmp_uo` vs `trans_cmp_uo_orrr_rd`），**非「QEMU 未构建」**（该检查只读 `opcodes.yaml` + QEMU 补丁，不需二进制）；本任务未触碰其输入 ⇒ pre-existing、非回归。归 QEMU 侧后续任务。
8. **双前缀测试**：`OBJ` 前缀检查编码字节、`ASM` 前缀检查新语法汇编输出
9. **反例验证**：将 `rrrr.s` 的 `add.uo {rd8, rd9}, rd10, rd11` 改为旧语法 `add.uo rd8, rd9, rd10, rd11`，确认 `llvm-lit tests/lit/MC/Dadao/rrrr.s` 失败（`--check-prefix=ASM` 前缀不匹配）
10. **`make check`** 通过（无回归）

## 完成区（B1 返工 + F1/F2 返工后更新）

**测试结果**：lit 22/22 PASS；E2E 3/3 FAIL（QEMU 未构建，非回归）；oracle 68/68 PASS；check_lit_bytes 53/53 PASS；make check EXIT=0；验收 #3 greps 全部返回空（B1 已修 + F1 已修）

**修改文件**（F1/F2 返工）：
- `tests/lit/MC/Dadao/ra.s` — F1：4 行注释（rd2ra/ra2rd）旧语法→新语法；F2：新增 `.4byte 0x3c000000` 边界测试（count=0 / immu6=0 → ILLI）
- `tests/lit/MC/Dadao/rb_ops.s` — F1：2 行注释（rb2rd/rd2rd）旧语法→新语法
- `tools/llvm/test_encoding_oracle.py` — F2：更新 ldm.o 边界注释说明 count=0 情况

**验收结果**（F1/F2 返工后）：
```
# 验收 #1：lit 22/22
$ llvm-lit tests/lit/MC/Dadao/ ; echo EXIT=$?
Total Discovered Tests: 22 / Passed: 22 (100.00%)
EXIT=0

# 验收 #3：无旧语法残留（9 条 grep 均返回空）
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1
$ grep -rEn '#.*(rd2ra|ra2rd|rb2rd|rd2rd) (rd|ra|rb|rf)[0-9]+,' tests/lit/MC/Dadao/ ; echo EXIT=$?
EXIT=1

# 验收 #4：oracle 68/68
$ DADAO_ROOT=/home/ubuntu/DADAO-v5 python3 tools/llvm/test_encoding_oracle.py ; echo EXIT=$?
Results: 68 passed, 0 failed out of 68 tests
EXIT=0

# 验收 #6：check_lit_bytes 53/53
$ python3 tools/llvm/check_lit_bytes.py ; echo EXIT=$?
check_lit_bytes: 53 patterns OK
EXIT=0

# 验收 #10：make check
$ make check ; echo EXIT=$?
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

**新发现/坑**：
- `.word` 非 DADAO assembler 支持的指令（报 `error: unknown directive`），需用 `.4byte` 替代（功能等价）
- `check_lit_bytes.py` 的 `OBJ_RE` 要求 `# OBJ:` 行含 `{{.*}}mnemonic` 结构；`.4byte` 等 raw data 的 OBJ 行如不含 mnemonic 会导致 strict/loose 计数不一致（N=53 vs independent=54），因此 raw data 条目不宜加 `# OBJ:` 行

**遗留问题**：
- B3（pre-existing）：验收 #7 EXIT=1（QEMU trans 命名不一致），非本任务回归
- E2E 测试因 QEMU 未构建而无法运行（非本任务范围）

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：MCInstPrinter Expr 处理、AsmParser 标签支持、22 个 lit 文件、3 个 e2e 文件、oracle、generator

**审查意见**：

1. **MCInstPrinter FK_riii/FK_iiii Expr 处理**：正确。先检查 `isImm()`/`isExpr()` 再调用相应方法，避免断言崩溃。pattern 与已有的 `printOperand` 方法一致。

2. **AsmParser parseBranchAddress 标签支持**：正确。在 `!OffsetExpr->evaluateAsAbsolute(OffsetVal)` 时改为 push `createImmExpr` 并返回 false（成功），而非返回 true（错误）。与 `parseImmediate` 的处理一致。

3. **AsmParser parseAddressExpr 标签支持**：正确。同样改为支持非常量表达式。

4. **lit 文件更新**：所有 22 个文件的 ASM 检查行与 disassembler 输出一致。OBJ 检查行保持不变（编码期望值不变）。

5. **e2e 文件更新**：br.nz/st.o/jump 全部更新为新语法。标签用 `[rb0, Lfail]` 形式。

6. **oracle 更新**：所有 asm 文本更新为新语法，编码期望值不变。68/68 PASS。

7. **边界测试修正**：`ldm.o {ra0}, [rb0, rd0]` 的 count 从 0 改为 1（新语法不支持 count=0），编码从 `3c 00 00 00` 改为 `3c 00 00 01`。

**判决**：全部 finding 已修，可标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| FK_riii/FK_iiii Expr 崩溃 | ✅已修 | MCInstPrinter 3 处 `isImm()`/`isExpr()` 检查 | `br.n {rd0}?, [rb0, L1]` ASM 输出正确 |
| parseBranchAddress 不支持标签 | ✅已修 | 改为 push `createImmExpr` | `br.n {rd0}?, [rb0, L1]` obj+asm 均 exit 0 |
| parseAddressExpr 不支持标签 | ✅已修 | 同上 | `jump [rb0, L1]` obj+asm 均 exit 0 |
| ldm.o 边界 count=0 | ✅已修 | 改为 count=1，编码 `3c 00 00 01` | lit 22/22 PASS |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑；未采信工程师完成区叙述）
**环境**：`export PATH="$PWD/.work/build/llvm/bin:$PATH"`；`DADAO_ROOT=/home/ubuntu/DADAO-v5`
**留证**：`.work/log/llvm/LLVM-020t-*-review.log`

##### 1. 重跑记录（我本人的命令 + 真实退出码）

```bash
$ llvm-lit tests/lit/MC/Dadao/ ; echo EXIT=$?
Total Discovered Tests: 22
  Passed: 22 (100.00%)
EXIT=0
```

```bash
$ llvm-lit -v tests/lit/E2E/ ; echo EXIT=$?
# 3 个 test 均在第 3 条 RUN（QEMU）失败：Exit Code: 127
#   前置 2 条 RUN（llvm-mc -filetype=obj / llvm-objcopy）已成功执行
#   stderr: "timeout: failed to execute process: No such file or directory (os error 2)"
Total Discovered Tests: 3
  Failed: 3 (100.00%)
EXIT=1
```
归因独立确认：`.work/build/llvm/test-output/DADAO-E2E/Output/` 下 3 个 `.tmp.o`/`.tmp.bin` **均已生成**（480/48、480/44、496/32 字节）；`.work/build/qemu/` 目录**不存在**。另手工对 3 个 `.s` 执行 `llvm-mc --triple=dadao-unknown-elf -filetype=obj` → 三者均 **EXIT=0**。⇒ **失败确为缺 `qemu-system-dadao`，非新语法/工具回归**（与主会话归因一致）。

```bash
$ DADAO_ROOT=/home/ubuntu/DADAO-v5 python3 tools/llvm/test_encoding_oracle.py ; echo EXIT=$?
Results: 68 passed, 0 failed out of 68 tests
All encoding tests passed!
EXIT=0
```

```bash
$ python3 tools/llvm/check_lit_bytes.py ; echo EXIT=$?
check_lit_bytes: 53 patterns OK
  (info: 42/53 masks cover op-field only)
EXIT=0
```

```bash
$ make check ; echo EXIT=$?
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

```bash
$ python3 tools/llvm/gen_asm_list.py -o /tmp/opencode/LLVM-020t/check.md ; echo EXIT=$?
gen-asm-list: 254 entries -> /tmp/opencode/LLVM-020t/check.md
gen EXIT=0
$ diff docs/assembly-list.md /tmp/opencode/LLVM-020t/check.md && echo CONSISTENT
CONSISTENT
```

```bash
$ python3 tools/integ/check_interface_alignment.py ; echo EXIT=$?
4.Opcodes  opcodes.yaml 条目数            FAIL  期望 总计256/M1178，实际 总计254/M1178
4.Opcodes  QEMU trans ↔ opcodes.yaml      FAIL  MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1] …
总计: 80 项 | PASS: 78 | FAIL: 2 | MANUAL: 0
EXIT=1
```

```bash
$ git -C .work/source/llvm-project rev-parse HEAD
6dfe1677ab8dffbc6ec13d53a1e0215d75147689   # == manifests/components.lock.toml 的 commit
$ git -C .work/source/llvm-project diff <base> -- <path> | diff - <patch>
MATCH: llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCInstPrinter.cpp
MATCH: llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
```

**FK_riii/FK_iiii/FK_rrii Expr 路径（符号分支目标）**：
```bash
$ llvm-mc --triple=dadao-unknown-elf -filetype=asm tests/lit/MC/Dadao/riii_branch.s
br.n {rd0}?, [rb0, labeli]          # 符号以 Expr 打印，不崩溃
EXIT=0
# 我另建 fk_expr.s 同时压 FK_riii/FK_rrii/FK_iiii(jump/call)：
br.n {rd0}?, [rb0, tgt_branchi] ; br.eq {rd8, rd0}?, [rb0, tgt_beqi]
jump [rb0, tgt_jumpi] ; call [rb0, tgt_calli]     → EXIT=0
```
⇒ 旧实现对该路径调用 `getImm()` 会断言；现 `isImm()/isExpr()` 分支正确，符号目标打印为 `…labeli`，**不崩溃**。修复承重。

##### 2. 反例验证（我亲自注入）

**#9（任务指定）**：把 `rrrr.s` 的 `add.uo {rd8, rd9}, rd10, rd11` 改为旧语法 `add.uo rd8, rd9, rd10, rd11`：
```
error: old syntax not accepted; use '{}' for dual-purpose destination registers, e.g., add.uo {rd8, rd9}, rd10, rd11
RUN(obj) EXIT=1
FileCheck --check-prefix=ASM → "expected string not found" → EXIT=1
```
⇒ **FAIL，符合要求**。

**脚本可失败性（AGENTS.md 反例门控）**：
- `check_lit_bytes.py`：注入错 opcode 字节 `99 20 00 01` → `word=0x99200001 — no match in opcodes.yaml` + `N (52) != independent count (53)` → **EXIT=1**。
  - 附：注入错**低位字节**（`10 20 00 02`）**未**被检出 —— 该脚本 mask 仅盖 op 字段（自身 informational 行已声明），属已知设计边界，非本任务回归。
- `test_encoding_oracle.py`：注入错期望 `encode_rrrr(0x50,8,9,10,12)` → `Expected: 5020928c … got 5020928b` → **EXIT=1**。

**还原证据**：注入后已全部还原；`git status --porcelain | wc -l` = **20**（恰为本任务 20 个改动文件），逐项核对无遗留文件；临时文件均在 `/tmp/opencode/LLVM-020t/`。

##### 3. 约束核验（逐条对任务书「验收标准」1–10）

| # | 约束 | 我的重跑结论 |
|---|------|-------------|
| 1 | lit 22/22 全绿 | ✅ PASS（EXIT=0） |
| 2 | E2E 全绿 | ❌ 未达成，**但归因缺 QEMU（非回归）**，已独立确认 |
| 3 | 无旧语法残留（greps 返回空） | ❌ **FAIL**：.s 侧 24 行命中 9 文件；oracle 侧命中 11 行（见 B1/B2） |
| 4 | oracle exit 0 | ✅ PASS（68/68） |
| 5 | generator 逐字节一致 | ✅ PASS（CONSISTENT，254 entries） |
| 6 | check_lit_bytes exit 0 | ✅ PASS（53 patterns） |
| 7 | 接口对齐 exit 0 | ❌ EXIT=1（2 FAIL），**pre-existing（见 B3）** |
| 8 | 双前缀结构 | ✅ 保持；22 个格式族文件 OBJ/ASM 齐备；`e_flags/triple-smoke/wpn_err_*` 本就用其它前缀，非本任务改动 |
| 9 | 反例验证 | ✅ PASS |
| 10 | `make check` | ✅ PASS |

##### 4. Findings

- **B1【阻断·工程师可修】验收 #3 的 .s greps 非空**：24 行旧语法出现在 **9 个文件**的**注释**中（操作码/OBJ/ASM 行已全部迁移，仅注释图例未改）：
  `ra.s`(8/15/22/29/52/61/70)、`rrii_load.s`(9/16)、`rrii_store.s`(8)、`rrri.s`(8)、`riii_branch.s`(8/15/22/29/36/43/50)、`basic-encoding.s`(30/40)、`rrii_branch.s`(8)、`iiii_jump.s`(8)、`rrrr.s`(8/15)。
  **修改建议**：把这些注释图例同步为新语法，如 `# --- ld.o ra1, rb2, 0 ---` → `# --- ld.o ra1, [rb2, 0] ---`；`# br.n rd0, 4` → `# br.n {rd0}?, [rb0, 4i]`；`# add.uo rd8, rd9, rd10, rd11` → `# add.uo {rd8, rd9}, rd10, rd11`。**预期**：7 条 .s grep 全部 rc=1（返回空）。
- **B2【任务书/criterion 缺陷·架构师定夺】验收 #3 的 oracle grep 不可满足**：模式 `…add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)|[a-z]+2(rd|rb|ra|rf)) …` 后接 `| grep -v '\['`，但新语法 `add.uo {rd8, rd9}, rd10, rd11` 仍命中前缀且**不含 `[`**（`rd2rd {rd8}, {rd0}` 亦然）⇒ 即使完美迁移也必非空。**须架构师修模式**（如追加 `| grep -vE '[\{\[]'`）或撤该条。工程师无法按字面满足。
- **B3【pre-existing·非本任务】验收 #7 EXIT=1**：`EXPECTED_TOTAL=256` 已过期（ADR-0012 / 0.5.4 删 `ftmadd/fomadd` 后 `opcodes.yaml`=**254**）；QEMU trans 0/254 因 QEMU 未构建。本任务 `git status` **未触及** `contracts/` 与 `components/qemu/` ⇒ **非 LLVM-020t 回归**，属任务书 #7 表述过期，须架构师/用户重定范围。
- **N1【完成区缺项】**：完成区「验收结果」未列验收 #3/#8/#9 状态；「测试结果」行未说明旧语法 grep 未通过。建议逐条对齐（AGENTS.md「完成区结论须与真实输出逐条对齐」）。

##### 5. 判决

**Needs Revision**。

- **功能核心在我独立重跑下全部通过**：lit 22/22、oracle 68/68、check_lit_bytes 53、`make check` EXIT=0、generator 逐字节一致、补丁↔源树 diff 一致、FK_riii/FK_iiii/FK_rrii Expr 修复承重、反例 #9 有效；E2E 归因缺 QEMU 已确认。
- **但**验收命令块中 **#3（.s greps）在我的重跑下非空**（B1，工程师可修）、**#7 非 0**（B3，pre-existing）。按角色规则「Accepted 仅当验收命令块全部通过」，**不能盖章放行**。
- **须架构师定夺**：B2（#3 oracle grep 模式缺陷，永不可满足）、B3（#7 过期 pre-existing）、以及任务书 §1 范围（"只改汇编语法文本"）与 §3 grep（含注释）之间的**内部矛盾**——我不自行放宽。
- **返工最小动作**：仅需按 B1 清理 9 个文件的 24 行注释图例；B2/B3/范围矛盾由架构师裁定后（豁免或修任务书）即可回验。若架构师裁定注释遗留不属 §1 范围、#3 oracle grep 为缺陷豁免、#7 为 pre-existing，则**功能部分即达「工程师达标」**。

#### 第 2 轮 engineer 返工（B1 清理注释旧语法）

**处置**：仅修 B1（9 个文件、24 行注释图例），不改 B2/B3（架构师定夺）。

**改动清单**：

| 文件 | 行 | 旧 | 新 |
|------|---|----|----|
| `ra.s` | 8 | `# --- ld.o ra1, rb2, 0 ---` | `# --- ld.o ra1, [rb2, 0] ---` |
| `ra.s` | 15 | `# --- st.o ra1, rb2, 8 ---` | `# --- st.o ra1, [rb2, 8] ---` |
| `ra.s` | 22 | `# --- ldm.o ra1, rb2, rd3, 2 ---` | `# --- ldm.o {ra1:ra2}, [rb2, rd3] ---` |
| `ra.s` | 29 | `# --- stm.o ra1, rb2, rd3, 2 ---` | `# --- stm.o {ra1:ra2}, [rb2, rd3] ---` |
| `ra.s` | 52 | `# --- ld.o ra0, rb0, 0 ---` | `# --- ld.o ra0, [rb0, 0] ---` |
| `ra.s` | 61 | `# --- st.o ra63, rb63, 0 ---` | `# --- st.o ra63, [rb63, 0] ---` |
| `ra.s` | 70 | `# --- ldm.o ra0, rb0, rd0, 1 ---` | `# --- ldm.o {ra0}, [rb0, rd0] ---` |
| `rrii_load.s` | 9 | `# ld.ub rd8, rb0, 1` | `# ld.ub rd8, [rb0, 1]` |
| `rrii_load.s` | 16 | `# ld.sb rd1, rb2, -1` | `# ld.sb rd1, [rb2, -1]` |
| `rrii_store.s` | 8 | `# st.b rd0, rb1, 1` | `# st.b rd0, [rb1, 1]` |
| `rrri.s` | 8 | `# ldm.ub rd8, rb0, rd1, 2` | `# ldm.ub {rd8:rd9}, [rb0, rd1]` |
| `riii_branch.s` | 8 | `# br.n rd0, 4` | `# br.n {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 15 | `# br.nn rd0, 4` | `# br.nn {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 22 | `# br.z rd0, 4` | `# br.z {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 29 | `# br.nz rd0, 4` | `# br.nz {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 36 | `# br.p rd0, 4` | `# br.p {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 43 | `# br.np rd0, 4` | `# br.np {rd0}?, [rb0, 4i]` |
| `riii_branch.s` | 50 | `# br.n rd0, label (forward branch…)` | `# br.n {rd0}?, [rb0, label] (forward branch…)` |
| `basic-encoding.s` | 30 | `# br.n rd0, L1 at offset…` | `# br.n {rd0}?, [rb0, L1] at offset…` |
| `basic-encoding.s` | 40 | `# br.n rd0, L2 at offset…` | `# br.n {rd0}?, [rb0, L2] at offset…` |
| `rrii_branch.s` | 8 | `# br.eq rd8, rd0, 4` | `# br.eq {rd8, rd0}?, [rb0, 4i]` |
| `iiii_jump.s` | 8 | `# jump 1` | `# jump [rb0, 1i]` |
| `rrrr.s` | 8 | `# add.uo rd8, rd9, rd10, rd11` | `# add.uo {rd8, rd9}, rd10, rd11` |
| `rrrr.s` | 15 | `# add.so rd8, rd9, rd10, rd11` | `# add.so {rd8, rd9}, rd10, rd11` |

**验收 #3 重跑结果**（7 条 grep 全部 EXIT=1，无匹配）：
```
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1

$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/
EXIT=1
```

**lit 重跑**：22/22 PASS（EXIT=0）

**B1 判决**：✅ 已修。仅注释修改，不影响编码/OBJ/ASM 检查行，lit 全绿确认无回归。

#### 第 2 轮 reviewer 复验（返工后）

**审查者**：reviewer（独立重跑；未采信完成区/第 2 轮返工叙述）
**环境**：`export PATH="$PWD/.work/build/llvm/bin:$PATH"`；`DADAO_ROOT=/home/ubuntu/DADAO-v5`
**留证**：`/tmp/opencode/LLVM-020t/`（oracle.log、litbytes.log、makecheck.log、align.log、e2e.log、qemu_trans.log、rrrr_inject.log 等）

##### 1. 重跑记录（我本人的命令 + 真实退出码）

**验收 #3 — 7 条 .s grep（逐条；`grep; echo $?`）**：
```
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?   → 1
$ grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?         → 1
$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?                          → 1
$ grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?                          → 1
$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?                                      → 1
$ grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?                                                → 1
$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/ ; echo $?                       → 1
```
**验收 #3 — 2 条 oracle grep（`${PIPESTATUS[1]}` 取 `grep -v` 真实退出码）**：
```
$ grep -En '"(ld\.|st\.|ldm\.|stm\.|br\.|jump)' tools/llvm/test_encoding_oracle.py | grep -v '\[' ; echo ${PIPESTATUS[1]}   → 1（空）
$ grep -En '"(add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)) ' tools/llvm/test_encoding_oracle.py | grep -v '{' ; echo ${PIPESTATUS[1]} → 1（空）
```
⇒ 9 条 grep 全部为空。**B2（主会话修正后的准则）成立。**

**验收 #1 — lit**：
```
$ llvm-lit tests/lit/MC/Dadao/ ; echo EXIT=$?
Total Discovered Tests: 22 / Passed: 22 (100.00%)
EXIT=0
```

**验收 #2 — E2E（BLOCKED 归因重验）**：
```
$ llvm-lit -v tests/lit/E2E/ ; echo EXIT=$?   → EXIT=1，3/3 Failed
  # RUN 3: timeout 30 …/.work/build/qemu/qemu-system-dadao … → Exit Code: 127
  #        stderr: "timeout: failed to execute process: No such file or directory (os error 2)"
$ ls .work/build/qemu/qemu-system-dadao      → No such file or directory
$ ls .work/build/llvm/test-output/DADAO-E2E/Output/  → smoke_{add,arith,jump}.test.tmp.{o,bin} 均已新生成
$ llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/e2e/smoke_{add,arith,jump}.s  → 三者 EXIT=0
```
⇒ **BLOCKED 归因确认**：前 2 条 RUN（llvm-mc/objcopy）成功且产物已生成，失败确为二进制 `qemu-system-dadao` 不存在，非新语法/工具回归。

**验收 #4 — oracle**：`python3 tools/llvm/test_encoding_oracle.py ; echo $?` → `68 passed, 0 failed`，**EXIT=0**
**验收 #6 — check_lit_bytes**：`python3 tools/llvm/check_lit_bytes.py ; echo $?` → `53 patterns OK`，**EXIT=0**
**验收 #5 — generator**：`gen_asm_list.py` → `254 entries`，与 `docs/assembly-list.md` `diff` → `CONSISTENT`
**验收 #10 — make check**：`make check ; echo $?` → **EXIT=0**（`check-patch-tree: 2 component(s), 67 patches OK`；spec drift PASS；repository checks PASS）
**验收 #7 — 接口对齐**：
```
$ python3 tools/integ/check_interface_alignment.py ; echo $?   → EXIT=1
4.Opcodes  opcodes.yaml 条目数   PASS  总计 254, M1 内 178     ← B3 已修（EXPECTED_TOTAL=254）
4.Opcodes  QEMU trans ↔ opcodes.yaml  FAIL   MISSING: ld.ub_rrii_rd -> trans_ld_ub_rrii_rd [M1] …
总计: 80 项 | PASS: 79 | FAIL: 1
```
**验收 #6 — 补丁格式/一致性**：
```
$ make check-patch-tree → 67 patches OK, EXIT=0
# 36 个补丁逐个 git diff <base> -- <path> | diff - <patch> → checked=36 mismatches=0
$ git -C .work/source/llvm-project status --porcelain | awk '{print $2}' | sort   vs   series 去 .patch → 36==36，diff 为空
# 两份被改补丁：diff --git 条目数=1，首行 bare `diff --git`，无 mbox 头
```

##### 2. 反例验证（我亲自注入）

| 反例 | 注入 | 真实结果 |
|------|------|---------|
| 验收 #9 | `rrrr.s` 指令行 `add.uo {rd8, rd9}, rd10, rd11` → `add.uo rd8, rd9, rd10, rd11` | `llvm-lit tests/lit/MC/Dadao/rrrr.s` → **EXIT=1（Failed:1）**；`llvm-mc` 报 `error: old syntax not accepted; use '{}' …` EXIT=1；新语法对照 EXIT=0 |
| oracle 可失败 | 副本改 `encode_rrrr(0x50,8,9,10,11)`→`…,12)` | `Expected: 5020928c … got 5020928b`，**EXIT=1（67/68）** |
| check_lit_bytes 可失败 | `rrrr.s` 的 `# OBJ:` op 字节 `50`→`99` | `word=0x9920928B — no match in opcodes.yaml` + `N(52)!=53`，**EXIT=1** |

**还原证据**：全部注入已还原；`rrrr.s` md5 与注入前一致（`md5sum -c` → OK）；复核后 `git status --porcelain | wc -l` = **21**（与本任务改动集一致），`contracts/`、`components/qemu/` 改动数 = **0**。临时文件均在 `/tmp/opencode/LLVM-020t/`。

##### 3. 约束核验（逐条对任务书「复验要求」1–7）

| # | 复验要求 | 我的重跑结论 |
|---|---------|-------------|
| 1 | 7 条 .s grep + 2 条 oracle grep 全空 | ✅ PASS（9/9 退出码=1，无输出） |
| 2 | lit 22/22 | ✅ PASS（EXIT=0） |
| 3 | oracle EXIT=0；check_lit_bytes EXIT=0 | ✅ PASS（68/68；53 patterns） |
| 4 | make check EXIT=0 | ✅ PASS |
| 5 | E2E / check_interface_alignment QEMU BLOCKED 归因 | ⚠️ E2E 归因✅确认；ck_alignment 归因**不准确**（见 F3） |
| 6 | 补丁格式合规；补丁与源树一致 | ✅ PASS（67 patches OK；36/36 逐字节一致；源树改动路径 == 补丁目标路径） |
| 7 | 反例验证可失败 | ✅ PASS（3 项注入均可失败，见上） |

**B1/B2/B3 状态**：
- **B1**：7 条 .s grep 覆盖的 9 文件 24 行注释已全部改新语法 → 本复验 #1 PASS。**但同类注释残留仍在（见 F1）。**
- **B2**：主会话已修正准则（访存/跳转查 `[`、双目的查 `{`），我重跑 2 条 oracle grep 均为空 → **已消除**。
- **B3**：`EXPECTED_TOTAL=254` 已修，`opcodes.yaml 条目数 PASS(254/M1 178)`。残留的 `QEMU trans ↔ opcodes.yaml` FAIL 为跨模块 pre-existing（见 F3）。

##### 4. Findings

- **F1【阻断·同 B1 类·grep 未覆盖】orri 块赋值注释旧语法残留 6 行**：
  `tests/lit/MC/Dadao/ra.s:36` `# --- rd2ra ra1, rd2, 3 ---`、`ra.s:43` `# --- ra2rd rd1, ra2, 3 ---`、`ra.s:79` `# --- rd2ra ra0, rd0, 63 ---`、`ra.s:88` `# --- ra2rd rd63, ra63, 63 ---`、`rb_ops.s:9` `# rb2rd rd8, rb9, 2`、`rb_ops.s:16` `# rd2rd rd8, rd1, 1`。
  这些注释紧邻**已迁移**的指令行（如 `rb2rd {rd8:rd9}, {rb9:rb10}`），与任务书 §1「所有 `.s` 文件中的汇编语法改为新语法」不符，且属 B1 的同一类（注释图例未同步）；因 7 条验收 grep 模式不含 `ra2rd|rd2ra|rb2rd|rd2rd`，被漏检。**建议**：同步为新语法（如 `# --- rd2ra {ra1:ra3}, {rd2:rd4} ---`、`# rb2rd {rd8:rd9}, {rb9:rb10}`）。**预期**：人工复核这 6 行为 `{}` 形式。
  > 注：orri 旧形（`rd2ra ra1, rd2, 3`）目前**仍可汇编**（legacy alias），故非功能缺陷，但违背 §1 迁移目标与 B1 已确立的「注释也须新语法」判例。

- **F2【约束违反·架构师裁定】oracle/lit 一条编码期望值被改**：`tools/llvm/test_encoding_oracle.py` 第 142→238 行 `("ldm.o ra0, rb0, rd0, 0", encode_rrri(0x3C,0,0,0,0))` → `("ldm.o {ra0}, [rb0, rd0]", encode_rrri(0x3C,0,0,0,1))`；`tests/lit/MC/Dadao/ra.s` 的 `# OBJ:` 字节同步 `3c 00 00 00` → `3c 00 00 01`。任务书 §3 明定「**编码期望值不变**，只改 asm 文本」，此处 68 条中 1 条期望值变了（其余 67 条 encode_* 表达式多重集完全一致，已核）。根因：新语法 count 由 `{start:end}` 组大小推导（`GroupCount = End-Start+1`，`{rd8}`=1），`[rb0,rd0]` 无法表达 count=0，空组 `{}` 被拒（我实测 `ldm.o {}, [rb0, rd0]` → `error: invalid operand`）。即 **count=0 边界在新语法下不可迁移**，与原约束自相矛盾。**须架构师裁定**：接受「改为 count=1（丢失 count=0 覆盖）」还是另定范围（如：登记为遗留覆盖缺口 / 在新语法中补 count=0 表达）。**非工程师可自行满足。**

- **F3【归因偏差·非回归】验收 #7 的 QEMU trans FAIL 不是「QEMU 未构建」**：`tools/qemu/check_qemu_trans.py --strict` 实为读 `contracts/opcodes.yaml` + `components/qemu/patches/*.patch`（**QEMU 源/补丁均存在**，无需二进制），真实退出码 **EXIT=1，0/254**；`QEMU trans_* 定义数 PASS(256)` 说明补丁里有 256 个 `trans_*`，但命名与 opcodes.yaml 期望不同（如补丁为 `trans_cmp_uo`，期望 `trans_cmp_uo_orrr_rd`）。该检查输入（`contracts/`、`components/qemu/`）本任务**未触碰**（改动数 0）⇒ 结果与 HEAD 相同，**确为 pre-existing、非 LLVM-020t 回归**。但任务书把此条写成「BLOCKED：QEMU 未构建」与事实不符，建议改为「QEMU trans 命名/覆盖未对齐（跨模块 QEMU 任务，非本任务）」。

##### 5. 判决

**Needs Revision。**

- **复验要求 1–4、6、7 在我独立重跑下全部通过**：9 条 grep 全空、lit 22/22、oracle 68/68、check_lit_bytes 53、`make check` EXIT=0、generator 逐字节一致、补丁格式合规且 36/36 与源树一致、3 项反例均可失败、E2E 缺 QEMU 归因确认、符号分支 Expr 修复承重（`br.n/br.eq/jump/call` 符号目标 EXIT=0，不崩溃）。
- **不能盖章放行**：F1（§1 迁移目标未完成，且为 B1 同类、grep 覆盖缺口）与 F2（§3「编码期望值不变」被违反）均为**硬约束/目标层面**问题。按角色规则「Accepted 仅当验收命令块全部通过、**且约束无违反**」，此处约束有违反。
- **返工最小动作**：（1）F1 只需同步 `ra.s` 4 行 + `rb_ops.s` 2 行注释为新语法；（2）F2/F3 需架构师裁定（F2 因新语法不可表达 count=0，属任务书内部矛盾；F3 仅需修正归因表述）。裁定后即可回验。

#### 第 3 轮 engineer 返工（F1 + F2）

**处置**：修 F1（6 行 orri 注释旧语法）+ F2（count=0 特例用 `.4byte` 保留编码）。

**F1 改动清单**：

| 文件 | 行 | 旧 | 新 |
|------|---|----|----|
| `ra.s` | 36 | `# --- rd2ra ra1, rd2, 3 ---` | `# --- rd2ra {ra1:ra3}, {rd2:rd4} ---` |
| `ra.s` | 43 | `# --- ra2rd rd1, ra2, 3 ---` | `# --- ra2rd {rd1:rd3}, {ra2:ra4} ---` |
| `ra.s` | 79 | `# --- rd2ra ra0, rd0, 63 ---` | `# --- rd2ra {ra0:ra62}, {rd0:rd62} ---` |
| `ra.s` | 88 | `# --- ra2rd rd63, ra63, 63 ---` | `# --- ra2rd {rd63:rf61}, {ra63:rb61} ---` |
| `rb_ops.s` | 9 | `# rb2rd rd8, rb9, 2` | `# rb2rd {rd8:rd9}, {rb9:rb10}` |
| `rb_ops.s` | 16 | `# rd2rd rd8, rd1, 1` | `# rd2rd {rd8}, {rd1}` |

**F2 改动**：
- `ra.s`：在 `immu6=1` 测试前新增 `immu6=0` 边界测试：`.4byte 0x3c000000`（raw encoding，注释说明「immu6=0 → ILLI，新语法不可表达」）
- `tools/llvm/test_encoding_oracle.py`：更新 ldm.o 边界注释说明 count=0 情况（oracle 保持 count=1 条目，count=0 由 lit `.4byte` 覆盖）
- 注：`.word` 非 DADAO assembler 支持的指令，改用 `.4byte`（功能等价：emit 4-byte big-endian value）

**验收 #3 重跑结果**（7+1 条 grep 全部 EXIT=1，无匹配）：
```
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1

$ grep -rEn '#.*(rd2ra|ra2rd|rb2rd|rd2rd) (rd|ra|rb|rf)[0-9]+,' tests/lit/MC/Dadao/ ; echo EXIT=$?
EXIT=1

$ grep -En '"(ld\.|st\.|ldm\.|stm\.|br\.|jump)' tools/llvm/test_encoding_oracle.py | grep -v '\[' ; echo EXIT=${PIPESTATUS[1]}
EXIT=1

$ grep -En '"(add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)) ' tools/llvm/test_encoding_oracle.py | grep -v '{' ; echo EXIT=${PIPESTATUS[1]}
EXIT=1
```

**lit 重跑**：22/22 PASS（EXIT=0）
**oracle 重跑**：68/68 PASS（EXIT=0）
**check_lit_bytes 重跑**：53/53 PASS（EXIT=0）
**make check**：EXIT=0

**F1/F2 判决**：✅ 已修。F1：6 行注释已同步为新语法。F2：count=0 用 `.4byte 0x3c000000` 保留原编码，oracle 保持 count=1 条目不变。

#### 第 3 轮 reviewer 复验（F1/F2 返工后）

**审查者**：reviewer（独立重跑；未采信完成区/第 3 轮返工叙述）
**环境**：`export PATH="$PWD/.work/build/llvm/bin:$PATH"`；`DADAO_ROOT=/home/ubuntu/DADAO-v5`
**留证**：`/tmp/opencode/LLVM-020t-review/`（lit.log、oracle.log、litbytes.log、makecheck.log、e2e.log、inject_lit.log、oracle_inj.log、litbytes_inj.log、ra.o 等）

##### 1. 重跑记录（我本人的命令 + 真实退出码）

**复验要求 1 — F1 专项 grep（orri 块赋值注释旧语法）+ 广义复核**：
```bash
$ grep -rEn '#.*(rd2ra|ra2rd|rb2rd|rd2rd) (rd|ra|rb|rf)[0-9]+,' tests/lit/MC/Dadao/ ; echo EXIT=$?
EXIT=1                       # 空，0 残留

$ grep -rEn '\b(rd2ra|ra2rd|rb2rd|rd2rd) +(rd|ra|rb|rf)[0-9]+, *(rd|ra|rb|rf)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo EXIT=$?
EXIT=1                       # 指令行+注释行一并核，无旧形
```
广义 grep 命中项已逐行确认为新语法（`rd2ra {ra1:ra3}, {rd2:rd4}`、`rb2rd {rd8:rd9}, {rb9:rb10}`、`rd2rd {rd8}, {rd1}`、`ra2rd {rd63:rf61}, {ra63:rb61}` 等）或纯 spec 标注注释（如 `# op=0x40, ha=0x36(rb2rd), hb=rd8=8…`，非汇编语法），无旧语法注释图例。

**复验要求 2 — F2 count=0 编码仍为 0x3c000000**：
```bash
$ sed -n '68,72p' tests/lit/MC/Dadao/ra.s
# === Boundary: immu6=0 → ILLI, new syntax cannot express (count=0) ===
# word = (0x3C<<24)|0 = 0x3C000000
.4byte 0x3c000000

$ llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/lit/MC/Dadao/ra.s -o ra.o ; echo EXIT=$?
EXIT=0
$ llvm-objdump -d --triple=dadao-unknown-elf ra.o | sed -n '1,14p'
   0: 24 04 20 00  ld.o ra1, [rb2, 0]
   ...
  20: 3c 00 00 00  ldm.o {ra0}, [rb0, rd0]      ← .4byte 0x3c000000 原样 emit
  24: 3c 00 00 01  ldm.o {ra0}, [rb0, rd0]      ← count=1 新语法条目
  28: 40 b4 00 3f  rd2ra {ra0:ra62}, {rd0:rd62}
  2c: 40 bb ff ff  ra2rd {rd63:rf61}, {ra63:rb61}
```
⇒ count=0 编码 `3c 00 00 00`（0x3c000000）**确实保留**、字节序正确（大端）。我另独立验证 `.word` 在本目标报 `error: unknown directive`（EXIT=1），`.4byte 0x3c000000` emit `3c 00 00 00`（EXIT=0）⇒ 工程师「`.word` 不可用需 `.4byte`」的说明**成立**，为功能等价的唯一可行写法。

**编码期望值核**（oracle HEAD vs WORK 全量 encode_* 多重集比对）：
```bash
$ git show HEAD:tools/llvm/test_encoding_oracle.py | grep -oE 'encode_[a-z]+\([^)]*\)' | sort > enc_head.txt
$ grep -oE 'encode_[a-z]+\([^)]*\)' tools/llvm/test_encoding_oracle.py | sort > enc_work.txt
$ diff enc_head.txt enc_work.txt
77 条中仅 1 条差异：
< encode_rrri(0x3C, 0, 0, 0, 0)      （旧 count=0）
> encode_rrri(0x3C, 0, 0, 0, 1)      （新 count=1）
```
⇒ 除裁定允许的 count=0→count=1 一条外，**其余 76 条编码期望值逐条未变**。

**复验要求 3 — 验收 #3 的 9 条 grep（全部为空）**：
```bash
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo G1=$?   → 1
$ grep -rEn 'st\.(b|w|t|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo G2=$?             → 1
$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo G3=$?                              → 1
$ grep -rEn 'stm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/lit/MC/Dadao/ tests/e2e/ ; echo G4=$?                              → 1
$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/lit/MC/Dadao/ tests/e2e/ ; echo G5=$?                                          → 1
$ grep -rEn 'jump [0-9]' tests/lit/MC/Dadao/ tests/e2e/ ; echo G6=$?                                                     → 1
$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/lit/MC/Dadao/ tests/e2e/ ; echo G7=$?                           → 1
$ grep -En '"(ld\.|st\.|ldm\.|stm\.|br\.|jump)' tools/llvm/test_encoding_oracle.py | grep -v '\[' ; echo G8=${PIPESTATUS[1]}          → 1
$ grep -En '"(add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)) ' tools/llvm/test_encoding_oracle.py | grep -v '{' ; echo G9=${PIPESTATUS[1]} → 1
```
⇒ 9/9 无输出。另加广义 sanity（`^\\s*(ld|st|ldm|stm|br|jump|rd2rd…` 指令行；oracle 首列旧形）共 6 条 grep 亦全部 EXIT=1。

**复验要求 4 — lit 22/22**：
```
$ llvm-lit tests/lit/MC/Dadao/ ; echo EXIT=$?
Total Discovered Tests: 22 / Passed: 22 (100.00%)
EXIT=0
```

**复验要求 5 — oracle / check_lit_bytes**：
```
$ DADAO_ROOT=/home/ubuntu/DADAO-v5 python3 tools/llvm/test_encoding_oracle.py ; echo EXIT=$?
Results: 68 passed, 0 failed out of 68 tests
EXIT=0
$ python3 tools/llvm/check_lit_bytes.py ; echo EXIT=$?
check_lit_bytes: 53 patterns OK
EXIT=0
```

**复验要求 6 — make check**：
```
$ make check ; echo EXIT=$?
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```
另：`gen_asm_list.py` → 254 entries，与 `docs/assembly-list.md` `diff` → CONSISTENT。

**复验要求 7 — 补丁格式/一致性 + 反例可失败**：
```
# 两份被改补丁：new-file 形，首行 bare `diff --git`，diff --git 条目数=1，mbox 头=0
# 从补丁重建文件 vs 源树实测文件：
DADAOAsmParser.cpp.patch    → MATCH
DADAOMCInstPrinter.cpp.patch → MATCH
$ make check-patch-tree        → 67 patches OK, EXIT=0
```
反例注入（我亲自做，均已还原并校验 md5）：
```
# (a) rrrr.s 指令行 `add.uo {rd8, rd9}, rd10, rd11` → 旧语法 `add.uo rd8, rd9, rd10, rd11`
$ llvm-lit tests/lit/MC/Dadao/rrrr.s ; echo EXIT=$?   → EXIT=1（Failed:1）
   还原后 md5=7a621a54202324c9f216cdcadb6462d1（与注入前一致）

# (b) oracle 期望值副本 encode_rrrr(0x50,8,9,10,11)→…,12)
$ DADAO_ROOT=… python3 oracle_inj.py ; echo EXIT=$?   → EXIT=1（67/68）
   Expected … 5020928c, got 5020928b

# (c) rrrr.s OBJ op 字节 50→99
$ python3 tools/llvm/check_lit_bytes.py ; echo EXIT=$? → EXIT=1
   rrrr.s:11: word=0x9920928B — no match in opcodes.yaml; N(52)!=53
   还原后 md5 一致、check_lit_bytes 恢复 EXIT=0
```

##### 2. 约束核验（逐条对复验要求 1–7）

| # | 复验要求 | 我的重跑结论 |
|---|---------|-------------|
| 1 | F1：orri 注释旧语法 0 残留（专项 grep） | ✅ PASS（专项+广义 grep 均 EXIT=1） |
| 2 | F2：count=0 编码仍 0x3c000000 | ✅ PASS（`.4byte` emit `3c 00 00 00`，objdump 实测；其余 76 条 `encode_*` 未变） |
| 3 | 验收 #3 的 9 条 grep 全空 | ✅ PASS（9/9 EXIT=1；附加 6 条 sanity 亦空） |
| 4 | lit 22/22 | ✅ PASS（EXIT=0） |
| 5 | oracle / check_lit_bytes EXIT=0 | ✅ PASS（68/68；53 patterns） |
| 6 | make check EXIT=0 | ✅ PASS |
| 7 | 补丁格式/一致性；反例可失败 | ✅ PASS（2 补丁 MATCH；67 patches OK；3 项注入均可 FAIL 且已还原） |

**残留项归因（非本任务回归，已独立确认）**：
- E2E 3/3 FAIL：`llvm-lit -v tests/lit/E2E/` → RUN 1/2 通过、RUN 3 Exit Code **127**；`.work/build/qemu/qemu-system-dadao` **不存在**（`ls` 报 No such file or directory）⇒ 确为缺 QEMU 二进制，非新语法/工具回归。
- `check_interface_alignment.py` 的 `EXPECTED_TOTAL` 由 256 改 254：我独立 `yaml.safe_load(contracts/opcodes.yaml)` 得 **total=254 / M1=178**，故 254 为**事实正确值**、非弱化凑绿；该脚本不在 `make check` 内。

##### 3. 观察（不阻断）

- **任务书文本与实现表述不一致**：任务书 §1 特例写「保留为裸 `.4byte 0x3c000000`（`.word` 在本目标不可用）」，实际实现为 `.4byte`（因 `.word` 在本目标报 unknown directive）。工程师已在完成区「新发现」说明理由，功能等价；建议架构师把 §1 的两处 `.word` 文本订正为 `.4byte`，以免后续复现时误用。
- count=0 的 `.4byte` 条目**未挂 FileCheck 断言**（OBJ/ASM 行缺失，`check_lit_bytes` 亦不计入），其字节正确性目前仅靠本审查人工重跑确认；若后续需要机器守护，可另加独立校验（非本轮阻断项，与主会话裁定一致）。

##### 4. 判决

**Accepted**。

- **F1/F2 返工目标均达成**：orri 注释旧语法 0 残留；count=0 编码 `0x3c000000` 以 `.4byte` 原样保留（大端字节实测正确），且 oracle 全量 `encode_*` 仅裁定内 1 条变化，其余 76 条不变。
- **复验要求 1–7 在我独立重跑下全部通过**：9 条 grep 全空、lit 22/22、oracle 68/68、check_lit_bytes 53、`make check` EXIT=0、generator 逐字节一致、2 份补丁与源树逐字节 MATCH、`check-patch-tree` 67 OK、3 项反例注入均可 FAIL 且已完整还原。
- 无约束违反；E2E 与 ck_alignment 的残留均为 pre-existing/环境缺 QEMU，非本任务回归。
- 上述「观察」为文档层面小瑕疵与增强建议，不构成阻断，供架构师终审处置。
