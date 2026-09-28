# LLVM-020t: 更新 lit/e2e/oracle 测试 + 重跑生成器更新 assembly-list

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`LLVM-019t`（MC 已支持新语法）、`LLVM-017t` + `LLVM-018t`（生成器已更新）
**状态**：待开始

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
2. **E2E lit 测试通过**：`.work/build/llvm/bin/llvm-lit tests/lit/E2E/` 全绿
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
   # 字节 oracle
   grep -En '"(ld\.|st\.|ldm\.|stm\.|br\.|jump|add\.(uo|so)|sub\.(uo|so)|mul\.(uo|so)|[a-z]+2(rd|rb|ra|rf)) ' tools/llvm/test_encoding_oracle.py | grep -v '\['
   ```
4. **字节 oracle 通过**：`python3 tools/llvm/test_encoding_oracle.py` exit 0
5. **生成器一致**：`docs/assembly-list.md` 与 `python3 tools/llvm/gen_asm_list.py` 输出逐字节一致
6. **lit 字节 oracle 通过**：`python3 tools/llvm/check_lit_bytes.py` exit 0
7. **接口对齐通过**：`python3 tools/integ/check_interface_alignment.py` exit 0
8. **双前缀测试**：`OBJ` 前缀检查编码字节、`ASM` 前缀检查新语法汇编输出
9. **反例验证**：将 `rrrr.s` 的 `add.uo {rd8, rd9}, rd10, rd11` 改为旧语法 `add.uo rd8, rd9, rd10, rd11`，确认 `llvm-lit tests/lit/MC/Dadao/rrrr.s` 失败（`--check-prefix=ASM` 前缀不匹配）
10. **`make check`** 通过（无回归）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
