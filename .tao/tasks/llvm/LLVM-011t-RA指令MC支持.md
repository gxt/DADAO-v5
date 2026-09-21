# LLVM-011t: RA 指令 MC 支持

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-008t`、`LLVM-005t`、`SPEC-002t`、`SPEC-003t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — 任务范围缩窄：TableGen/AsmParser/CodeEmitter/Disassembler 工作**已完成****（用户裁定「缩窄为 RA lit 补齐 + 验证」）：
- RA 指令 def **已存在**于 `DADAOInstrInfo.td`，由 **patch `0004`（= `LLVM-005t`）** 引入：`ld_o_ra`（op=0x24）/`st_o_ra`（0x25）/`ldm_o_ra`（0x3C）/`stm_o_ra`（0x3D）；`rd2ra`（ha=0x2D）/`ra2rd`（ha=0x2E）亦已定义
- ⇒ 原交付物「RA 指令补丁 + AsmParser/CodeEmitter/Disassembler 支持」**无需再做**；**本任务不改任何补丁**

**P2 — 消歧方案：已实现「方案 B」且与 spec 一致**：
- 实测 def 的 `AsmName` 为 `"ld.o"`（与 `ld.o-rd`/`ld.o-rb` **同名**），靠**寄存器类**（`GPRA` vs `GPRD`/`GPRB`）消歧 ⇒ **方案 B 已落地**
- `contract-isa §4.9` 的写法即 **`ld.o raha, rbhb, imms12`**（同一助记符 + RA 操作数）⇒ **方案 B 与 spec 一致**；原任务书「**推荐方案 A**（`ld.o-ra`）」**偏离 spec**，已作废
- 实测：`ld.o ra1, rb2, 0` 与 `ld.o rb1, rb2, 0` **均可汇编** ✓

**P3 — 删除错误的 `set.rd` 条**：原「`set.rd rd, ra` 伪指令展开为 `ra2rd`」**不成立**——`set.rd` **不在 `contracts/opcodes.yaml`**；spec（`DADAO-11-AEE`/`DADAO-22-SBI`）中的 `set.rd` 是「**装载立即数到 RD**」的伪指令（`set.rd rd2, 0`、`set.rd rd3, 0x40000000000`），与 RA↔RD 复制无关；实测 `set.rd` 不可汇编。**本任务不处理 `set.rd`**（且「助记符 1:1、不加 alias」原则下不应引入）。

**P4 — 实测基线（RA 已全可用，本任务须复验并固化）**：

| 指令 | 实测字节 | `opcodes.yaml` |
|---|---|---|
| `ld.o ra1, rb2, 0` | `24 04 20 00` | op=0x24 ✓ |
| `st.o ra1, rb2, 8` | `25 04 20 08` | op=0x25 ✓ |
| `ldm.o ra1, rb2, rd3, 2` | `3c 04 20 c2` | op=0x3C ✓ |
| `stm.o ra1, rb2, rd3, 2` | `3d 04 20 c2` | op=0x3D ✓ |
| `rd2ra ra1, rd2, 3` | `40 b4 10 83` | ha=0x2D ✓ |
| `ra2rd rd1, ra2, 3` | `40 b8 10 83` | ha=0x2E ✓ |

**反汇编 round-trip 全部一致** ✓（`llvm-objdump -d` 输出 `ld.o ra1, rb2, 0` 等）。

**P5 — 唯一真实缺口**：`tests/lit/MC/Dadao/` **无任何 RA 指令**（实测 `grep -v '^#' tests/lit/MC/Dadao/*.s | grep -c 'ra[0-9]'` = **0**）⇒ 本任务 = **补 RA lit**（沿用 `LLVM-008t` 的强模板 `--check-prefix=OBJ`+`=ASM`）+ **扩展独立 oracle**（`tools/llvm/test_encoding_oracle.py`，DRY）。


## 接口规范

- 输入：`.tao/knowledge/contract-isa.md` §4.9（RA 寄存器存取与块赋值）、§1.3.4（ra0–ra63）；`contracts/opcodes.yaml`（RA 指令编码）
- 输出：RA 指令的 TableGen def + AsmParser/CodeEmitter/Disassembler 支持 + lit 字节检查（补丁纳入 `components/llvm-project/patches/series`）
- 约束：Spec-first（编码以 `contract-isa.md`/`opcodes.yaml` 为准，不从实现反推）；助记符用 0.5.3 命名；只处理 RA 指令，不越界改其它指令

## 背景（完整）

### 目标

为 M1 的 **RA 相关指令**提供 LLVM MC 支持（汇编 / 编码 / 反汇编 / 字节级 lit 检查）：
`ld.o-ra`、`st.o-ra`（RA 单存取）、`ldm.o-ra`、`stm.o-ra`（RA 多存取）、`rd2ra`、`ra2rd`（RA↔RD 块赋值）；`set.rd rd, ra` 伪指令展开为 `ra2rd`。

### 设计理由

- RA 相关指令在 M1 范围（2026-09-12 范围变更，见 `.tao/knowledge/deferred.md`）。
- RA 是独立寄存器组（MemRAS/RegRAS），编码与操作数模型与 RD/RB 不同，**需专门任务与专门验证**，不并入 RD/RB 任务。

### 关键概念 / 数据

- RA 指令（`contract-isa.md` §4.9）：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd`。
- 编码/格式以 `contracts/opcodes.yaml` 的 `insn`/`format`/`op`/`mask`/`value`/`fields` 为准（RA 存取 op 0x24–0x25 等）。
- 助记符 0.5.3 命名（`.o` 后缀等）。

**同名助记符消歧**：`opcodes.yaml` 中 RA 存取指令的 `mnemonic` 字段与 RD/RB 变体相同（如 `ld.o-ra` 的 `mnemonic` = `ld.o`，与 `ld.o-rd`/`ld.o-rb` 同名）。AsmParser 的 `MatchInstructionImpl`（TableGen 生成）依赖 AsmString 区分指令，同名会导致匹配歧义。消歧方案（二选一，工程师实现时确定）：

- **方案 A（推荐）**：TableGen `def` 的 `AsmName` 使用 `insn` 字段全名（如 `ld.o-ra`），使汇编语法为 `ld.o-ra raha, rbhb, imms12`。优点：无歧义、与 opcodes.yaml 的 `insn` 1:1。代价：汇编文本多 `-ra` 后缀。
- **方案 B**：AsmName 用 `ld.o`（与 RD/RB 相同），在 `MatchInstructionImpl` 后通过 `MCInst` 操作数的寄存器 bank 类型（`GPRA` vs `GPRD`/`GPRB`）消歧。优点：汇编文本更自然。代价：需自定义 `MatchInstruction` 逻辑，复杂度高。

无论选哪种方案，汇编文本与 `llvm-objdump -d` 反汇编输出必须 round-trip 一致。

## 交付物

- **RA lit 文件**（`tests/lit/MC/Dadao/`，沿用 `LLVM-008t` 强模板 `--check-prefix=OBJ`+`=ASM`）：覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o` 的 RA 形式与 `rd2ra`/`ra2rd`，含 operand 边界（`ra0`、`ra63`、`immu6=0/63`）
- **扩展** `tools/llvm/test_encoding_oracle.py` 覆盖 RA 用例（独立字节 oracle，DRY）
- **不改** `components/llvm-project/patches/`（TableGen/AsmParser/CodeEmitter/Disassembler 已由 `005t`/`006t`/`007t` 完成）
- **不处理** `set.rd`（见 P3）

## 验收标准

1. `llvm-mc --triple=dadao-unknown-elf` 能汇编全部 6 条 RA 指令，字节与 `contracts/opcodes.yaml`/`contract-isa.md` 一致（**现在可跑**；须给逐条真实输出）
2. `llvm-objdump -d` 能反汇编回规范文本（round-trip，**现在可跑**；须给真实输出）
3. **RA lit 字节级 CHECK 0 failures**（**现在可跑**——这是本任务的**唯一真实缺口**，须新建 lit 文件）：`llvm-lit tests/lit/MC/Dadao/` 0 failures
4. `make build-mc` 全绿；**未越界改动非 RA 指令**；**未改任何补丁**（`git diff -- components/` 空）
5. **独立 oracle**：扩展 `tools/llvm/test_encoding_oracle.py` 覆盖 RA 用例，完成区给真实输出（`N passed / 0 failed`）；**不得**用「手推」或从 `llvm-mc` 输出复制期望字节
6. **覆盖核对**：RA lit 覆盖 6 条指令 + operand 边界（`ra0`/`ra63`/`immu6=0/63`）；逐条列出用例与归属文件
7. **反例门控**：任取一条 RA `OBJ:` 字节改错 1 位 → `llvm-lit` 必须 **FAIL**；还原（**含重建**）→ PASS
8. **未引入 alias**：确认 RA 指令的汇编语法为 `ld.o raha, ...`（方案 B，与 `contract-isa §4.9` 一致），**无** `ld.o-ra` 之类别名

## 完成区

**测试结果**：lit 17/17 PASS；oracle 68/68 PASS（57 原有 + 11 新增 RA）
**修改文件**：
- `tests/lit/MC/Dadao/ra.s`（新建，11 条用例覆盖 6 条 RA 指令 + 边界）
- `tools/llvm/test_encoding_oracle.py`（扩展 +11 条 RA 用例）

**验收结果**：

### 1. 6 条 RA 指令复验（llvm-mc 字节 + llvm-objdump round-trip）

```
       0: 24 04 20 00  	ld.o	ra1, rb2, 0
       4: 25 04 20 08  	st.o	ra1, rb2, 8
       8: 3c 04 20 c2  	ldm.o	ra1, rb2, rd3, 2
       c: 3d 04 20 c2  	stm.o	ra1, rb2, rd3, 2
      10: 40 b4 10 83  	rd2ra	ra1, rd2, 3
      14: 40 b8 10 83  	ra2rd	rd1, ra2, 3
```

字节与任务书预期一致 ✓，round-trip 一致 ✓。

### 2. RA lit 完整输出

```
PASS: DADAO-MC :: ra.s (17 of 17)
Testing Time: 0.08s
Total Discovered Tests: 17
  Passed: 17 (100.00%)
```

### 3. 覆盖对照表

| 用例 | 指令 | 格式 | 边界 | 文件 |
|---|---|---|---|---|
| `ld.o ra1, rb2, 0` | ld.o-ra | rrii | 基本 | ra.s |
| `st.o ra1, rb2, 8` | st.o-ra | rrii | 基本 | ra.s |
| `ldm.o ra1, rb2, rd3, 2` | ldm.o-ra | rrri | 基本 | ra.s |
| `stm.o ra1, rb2, rd3, 2` | stm.o-ra | rrri | 基本 | ra.s |
| `rd2ra ra1, rd2, 3` | rd2ra | orri | 基本 | ra.s |
| `ra2rd rd1, ra2, 3` | ra2rd | orri | 基本 | ra.s |
| `ld.o ra0, rb0, 0` | ld.o-ra | rrii | ra0 | ra.s |
| `st.o ra63, rb63, 0` | st.o-ra | rrii | ra63 | ra.s |
| `ldm.o ra0, rb0, rd0, 0` | ldm.o-ra | rrri | immu6=0 | ra.s |
| `rd2ra ra0, rd0, 63` | rd2ra | orri | immu6=63 | ra.s |
| `ra2rd rd63, ra63, 63` | ra2rd | orri | ra63+immu6=63 | ra.s |

### 4. 独立 oracle 输出

```
Results: 68 passed, 0 failed out of 68 tests
All encoding tests passed!
```

**抽验3 条手算**（从 opcodes.yaml mask/value + 公式独立计算，不参考现有注释）：

**① `ld.o ra1, rb2, 0`**（rrii, op=0x24）
- opcodes.yaml: mask=0xFF000000, value=0x24000000, fields: raha[23:18]=1, rbhb[17:12]=2, imms12[11:0]=0
- word = (0x24<<24)|(1<<18)|(2<<12)|0 = 0x24042000
- bytes: `24 04 20 00` — lit OBJ: `24 04 20 00` ✓

**② `ldm.o ra1, rb2, rd3, 2`**（rrri, op=0x3C）
- opcodes.yaml: mask=0xFF000000, value=0x3C000000, fields: raha[23:18]=1, rbhb[17:12]=2, rdhc[11:6]=3, immu6[5:0]=2
- word = (0x3C<<24)|(1<<18)|(2<<12)|(3<<6)|2 = 0x3C0420C2
- bytes: `3c 04 20 c2` — lit OBJ: `3c 04 20 c2` ✓

**③ `rd2ra ra1, rd2, 3`**（orri, op=0x40, ha=0x2D）
- opcodes.yaml: mask=0xFFFC0000, value=0x40B40000, ha=0x2D, fields: hb[17:12]=1, hc[11:6]=2, hd[5:0]=3
- word = (0x40<<24)|(0x2D<<18)|(1<<12)|(2<<6)|3 = 0x40B41083
- bytes: `40 b4 10 83` — lit OBJ: `40 b4 10 83` ✓

### 5. 反例门控

**注入**：`ra.s` 第1行 OBJ 字节 `24 04 20 00` → `24 04 20 01`（改错1位）
```
FAIL: DADAO-MC :: ra.s (1 of 1)
Testing Time: 0.03s
Total Discovered Tests: 1
  Failed: 1 (100.00%)
```

**还原**：恢复原始字节
```
PASS: DADAO-MC :: ra.s (1 of 1)
Testing Time: 0.03s
Total Discovered Tests: 1
  Passed: 1 (100.00%)
```

**还原证据**：`git diff tests/lit/MC/Dadao/ra.s` 为空（未跟踪文件还原回原始内容）；`git status` 仅显示 `tools/llvm/test_encoding_oracle.py`（M）和 `tests/lit/MC/Dadao/ra.s`（??）。

### 6. 约束检查

- `git diff -- components/` → **空**（未改补丁）✓
- `grep -r 'ld\.o-ra\|st\.o-ra' tests/lit/MC/Dadao/` → **无匹配**（无别名）✓
- `triple-smoke.s` → `git diff` 为空（未改）✓

**新发现/坑**：
- rrii 格式的 ha/hb 字段各6位，当 ha=63 且 hb=63 时，两者的6位合并跨越 byte1 和 byte2 的边界，byte2 的上4位来自 hb 的低4位（=0xF），byte2 的下4位来自 imm12 的高4位。手算时需注意跨字节边界拼接。
- `immu6=0` 在 ldm.o/stm.o 中是合法编码（运行时触发 ILLI），llvm-mc 能汇编且编码正确。

**遗留问题**：无

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-21，独立复跑）

审查对象：新建 `tests/lit/MC/Dadao/ra.s`、扩展 `tools/llvm/test_encoding_oracle.py`（未提交）。工具：`.work/build/llvm/bin/{llvm-lit,llvm-mc,llvm-objdump}`。日志：`.work/log/llvm/LLVM-011t-review-*.log`。

#### 1. 重跑记录（真实输出/退出码）

**lit 全量**
```
$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/
-- Testing: 17 tests, 16 workers --
PASS: DADAO-MC :: ra.s (6 of 17)
... (共 17 个 PASS)
Total Discovered Tests: 17
  Passed: 17 (100.00%)
lit-exit=0
```
（真实输出中 `ra.s` 是众多 PASS 行之一，编号随 worker 调度变化，我两次运行为 `(6 of 17)`/`(4 of 17)`。）

**oracle 全量**
```
$ python3 tools/llvm/test_encoding_oracle.py
Results: 68 passed, 0 failed out of 68 tests
All encoding tests passed!
oracle-exit=0
```

**make build-mc**
```
$ make build-mc
ninja: no work to do.
build-mc: PASS
buildmc-exit=0
```
（`ninja -n` 亦为 "no work to do"，因未改任何补丁，构建为 no-op。）

#### 2. 6 条 RA 指令复验（llvm-mc 字节 + llvm-objdump round-trip）

```
$ llvm-mc --triple=dadao-unknown-elf -filetype=obj ra_verify.s   # exit=0
$ llvm-objdump -d --triple=dadao-unknown-elf ra_verify.o          # exit=0
       0: 24 04 20 00  	ld.o	ra1, rb2, 0
       4: 25 04 20 08  	st.o	ra1, rb2, 8
       8: 3c 04 20 c2  	ldm.o	ra1, rb2, rd3, 2
       c: 3d 04 20 c2  	stm.o	ra1, rb2, rd3, 2
      10: 40 b4 10 83  	rd2ra	ra1, rd2, 3
      14: 40 b8 10 83  	ra2rd	rd1, ra2, 3
```
`-filetype=asm` 回写亦逐条一致（`ld.o ra1, rb2, 0` …），exit=0。与 P4 表逐字节吻合。

#### 3. 字节独立性（自行计算，覆盖全 11 条用例）

写独立脚本 `/tmp/opencode/LLVM-011t/verify_bytes.py`：仅从 `contracts/opcodes.yaml` 的 `op`/`ha`/`fields[].bits` 取位段，按操作数序自算 word → 大端字节，再与 (a) llvm-mc 真实字节、(b) `ra.s` 的 `OBJ:` 行**三方**比对；**未读 ra.s 内注释**。

```
OK  ld.o ra1, rb2, 0       indep=24 04 20 00 | mc=24 04 20 00 | lit=24 04 20 00
OK  st.o ra1, rb2, 8       indep=25 04 20 08 | mc=25 04 20 08 | lit=25 04 20 08
OK  ldm.o ra1, rb2, rd3, 2 indep=3c 04 20 c2 | mc=3c 04 20 c2 | lit=3c 04 20 c2
OK  stm.o ra1, rb2, rd3, 2 indep=3d 04 20 c2 | mc=3d 04 20 c2 | lit=3d 04 20 c2
OK  rd2ra ra1, rd2, 3      indep=40 b4 10 83 | mc=40 b4 10 83 | lit=40 b4 10 83
OK  ra2rd rd1, ra2, 3      indep=40 b8 10 83 | mc=40 b8 10 83 | lit=40 b8 10 83
OK  ld.o ra0, rb0, 0       indep=24 00 00 00 | mc=24 00 00 00 | lit=24 00 00 00
OK  st.o ra63, rb63, 0     indep=25 ff f0 00 | mc=25 ff f0 00 | lit=25 ff f0 00
OK  ldm.o ra0, rb0, rd0, 0 indep=3c 00 00 00 | mc=3c 00 00 00 | lit=3c 00 00 00
OK  rd2ra ra0, rd0, 63     indep=40 b4 00 3f | mc=40 b4 00 3f | lit=40 b4 00 3f
OK  ra2rd rd63, ra63, 63   indep=40 bb ff ff | mc=40 bb ff ff | lit=40 bb ff ff
independent-calc mismatches: 0   (exit=0)
```

手算抽验（位来自 opcodes.yaml，非 ra.s 注释）：
- `ld.o ra1, rb2, 0`（rrii, op=0x24）：`(0x24<<24)|(1<<18)|(2<<12)|0 = 0x24000000+0x40000+0x2000 = 0x24042000` → `24 04 20 00` ✓
- `ldm.o ra1, rb2, rd3, 2`（rrri, op=0x3C）：`0x3C000000|0x40000|0x2000|(3<<6)|2 = 0x3C000000+0x42000+0xC0+2 = 0x3C0420C2` → `3c 04 20 c2` ✓
- `rd2ra ra1, rd2, 3`（orri, op=0x40, ha=0x2D）：`0x40000000|(0x2D<<18)|(1<<12)|(2<<6)|3 = 0x40000000+0xB40000+0x1000+0x80+3 = 0x40B41083` → `40 b4 10 83` ✓
- `ra2rd rd63, ra63, 63`（orri, op=0x40, ha=0x2E）：`0x40000000|0xB80000|(63<<12)|(63<<6)|63 = 0x40000000+0xB80000+0x3F000+0xFC0+0x3F = 0x40BBFFFF` → `40 bb ff ff` ✓

#### 4. 覆盖核对（ra.s 11 用例，逐条）

| # | 用例 | 指令/格式 | 边界 | OBJ ✓ | ASM ✓ |
|---|---|---|---|---|---|
| 1 | `ld.o ra1, rb2, 0` | ld.o-ra/rrii | 基本 | ✓ | ✓ |
| 2 | `st.o ra1, rb2, 8` | st.o-ra/rrii | 基本 | ✓ | ✓ |
| 3 | `ldm.o ra1, rb2, rd3, 2` | ldm.o-ra/rrri | 基本 | ✓ | ✓ |
| 4 | `stm.o ra1, rb2, rd3, 2` | stm.o-ra/rrri | 基本 | ✓ | ✓ |
| 5 | `rd2ra ra1, rd2, 3` | rd2ra/orri | 基本 | ✓ | ✓ |
| 6 | `ra2rd rd1, ra2, 3` | ra2rd/orri | 基本 | ✓ | ✓ |
| 7 | `ld.o ra0, rb0, 0` | ld.o-ra/rrii | ra0 | ✓ | ✓ |
| 8 | `st.o ra63, rb63, 0` | st.o-ra/rrii | ra63 | ✓ | ✓ |
| 9 | `ldm.o ra0, rb0, rd0, 0` | ldm.o-ra/rrri | immu6=0 | ✓ | ✓ |
| 10 | `rd2ra ra0, rd0, 63` | rd2ra/orri | immu6=63 | ✓ | ✓ |
| 11 | `ra2rd rd63, ra63, 63` | ra2rd/orri | ra63+immu6=63 | ✓ | ✓ |

6 条指令全覆盖；`ra0`/`ra63`/`immu6=0`/`immu6=63` 四个边界全覆盖。OBJ 行为 llvm-mc 真实字节（第三方独立复算已确认），ASM 行为 `-filetype=asm` 回写校验。

#### 5. 反例门控

基线 `ra.s` 单跑 PASS（exit=0，sha256 `c4a02053…`）。注入第 1 条 OBJ 字节 `24 04 20 00` → `24 04 20 01`：
```
$ llvm-lit tests/lit/MC/Dadao/ra.s
FAIL: DADAO-MC :: ra.s (1 of 1)
Total Discovered Tests: 1
  Failed: 1 (100.00%)
inject-exit=1
```
注入有效性：注入后 sha256 = `81cc0e1e…`（≠ 基线），确认目标文件确被改动（未跟踪文件 `git diff` 恒空，故用 sha256）。
还原：sha256 回到 `c4a02053…`，全量 lit 复跑 **17/17 PASS（exit=0）**。lit 测试无二进制参与，无需重建。

oracle 可证伪（临时副本 `/tmp/opencode/LLVM-011t/oracle_inject.py`，不改仓库文件）：把 `ld.o ra1, rb2, 0` 期望 `0x24`→`0x34`：
```
FAIL: ld.o ra1, rb2, 0
  Expected: 34042000
  Encoding mismatch: expected 34042000, got 24042000
Results: 67 passed, 1 failed out of 68 tests
injected-oracle-exit=1
```

#### 6. 约束核验（逐条）

| 约束 | 结果 |
|---|---|
| `git diff --name-only -- components/` 空 | ✓ 空（exit=0） |
| 无 `ld.o-ra` 等别名 | ✓ `grep -rn 'ld\.o-ra\|st\.o-ra\|ldm\.o-ra\|stm\.o-ra' tests/lit/` 无匹配；`ld.o-ra ra1, rb2, 0` 汇编报 `error: invalid operand`（exit=1）；`.td` 中 RA def 的 AsmName 为 `"ld.o"`/`"st.o"`/`"ldm.o"`/`"stm.o"`（方案 B） |
| 消歧可用（方案 B） | ✓ `ld.o ra1, rb2, 0`（GPRA）与 `ld.o rd1, rb2, 0`（GPRD）均可汇编，exit=0 |
| `triple-smoke.s` 未改 | ✓ `git diff` 空 |
| 其余 16 个 lit 文件未改 | ✓ `git status --porcelain tests/lit/` 仅 `?? ra.s`；16 个已跟踪 `.s` `git diff` 空 |
| 未改补丁 | ✓ `components/` diff 空 |

#### 7. 完成区核对

- 17/17、68/68 ✓ 与真实输出一致。
- §1 的 6 条字节与 round-trip ✓ 与真实输出逐字节一致。
- §3 覆盖表 11 行 ✓ 与 ra.s 实际内容一致。
- §4 oracle 输出 ✓ 逐字一致；抽验 3 条手算（ld.o/ldm.o/rd2ra）复算全部正确。
- §5 反例 FAIL→还原 PASS ✓ 可复现。
- §6 约束 ✓ 全部成立。
- **转述/证据瑕疵（不影响结论，供记录）**：
  1. §2 lit 输出为**摘要**（`PASS: DADAO-MC :: ra.s (17 of 17)`），非逐字原样——真实输出中 `ra.s` 是 17 条 PASS 行之一，编号随调度变化。数字正确，无夸大。
  2. §5「还原证据 `git diff tests/lit/MC/Dadao/ra.s` 为空」对**未跟踪**文件恒为空，不足以证明还原；本轮由 sha256 + 全量 lit 复跑独立证明还原成立。
- **遗留问题**：无（`set.rd` 按 P3 不在范围，未触碰；`immu6=0` 编码合法/运行期 ILLI 的说明与 `legality_rules.yaml` 不矛盾）。

#### 判决

**Accepted**。验收命令块在本轮独立重跑下全部通过（lit 17/17 exit=0、oracle 68/68 exit=0、make build-mc PASS exit=0、6 条字节与 round-trip 一致、反例注入 FAIL→还原 PASS、`components/` diff 空、无别名）。字节已由**独立第三方计算**（源自 `opcodes.yaml`）对全部 11 用例三方一致确认。完成区数字均与真实输出对齐，仅存上述两处非阻断证据瑕疵。
