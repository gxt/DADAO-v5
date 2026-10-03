# TESTCASES-021t: lit 与 e2e 汇编语法字节化

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：LLVM-026t（需要新 llvm-mc 才能跑 `make check-lit`）
**状态**：已验证

## 目标

**（2026-10-03 调整：本任务的迁移工作已由 `LLVM-026t` 实际完成并经其 reviewer 验证 ⇒ 本任务缩窄为「复核-only」，不再重复改动。）**

对 `LLVM-026t` 已执行的迁移做**独立复核**：
- `tests/lit/MC/Dadao/{riii_branch,iiii_jump,rrii_branch,e_flags}.s`、`tests/e2e/smoke_jump.s` 的 `<数字>i` → 字节值是否正确（值 ×4、**OBJ 编码不变**、ASM/注释同步）；
- `grep -rn '[0-9]+i[][ ,;)]' tests/lit/MC/Dadao/*.s tests/e2e/*.s` 无残留；
- `make check-lit` 绿（`LLVM-026t` 报告 25/25）。
- **仅当发现遗漏/错误时**才修改，并在完成区记录；否则只出复核结论（含真实命令与输出）。

## 执行环境

**执行环境**：本地

## 范围

### 文件清单

| 文件 | 类型 | `i` 出现次数 | 改动 |
|---|---|---|---|
| `tests/lit/MC/Dadao/riii_branch.s` | lit MC | 25 | `4i`→`16`、`3i`→`12`；OBJ/ASM CHECK + 注释同步 |
| `tests/lit/MC/Dadao/iiii_jump.s` | lit MC | 7 | `1i`→`4` |
| `tests/lit/MC/Dadao/rrii_branch.s` | lit MC | 4 | `4i`→`16` |
| `tests/lit/MC/Dadao/e_flags.s` | lit MC | 1 | `0i`→`0` |
| `tests/e2e/smoke_jump.s` | e2e | 3 | `2i`→`8`（含注释） |

**合计**：40 行含 `i`，需改动 40 行。

### 不改的文件

| 文件 | 理由 |
|---|---|
| `tests/vectors/isa/*.yaml` | 只含 raw encoding（`word` 字段），不含汇编文本 |
| `tests/lit/MC/Dadao/basic-encoding.s` | 不含跳转/分支/escape 指令 |
| 其他 `.s` 文件 | 不含 `i` 后缀（已核实全部 22 个 lit `.s` 文件 + 3 个 e2e `.s` 文件） |

### 约束

- OBJ 行的**字节编码不变**（ISA 编码语义不变；汇编器内部 `>>2` 后产出相同编码）
- OBJ 行中的**汇编文本模式需更新**（`{rd0}?, [rb0, 4i]` → `{rd0}?, [rb0, 16]`）
- ASM 行的汇编文本**需更新**（反汇编器改为打印字节值）
- 注释中的 `i` 后缀也需更新

### 精确行分类计数

下表为逐行分类（SRC=源码行、OBJ=OBJ CHECK 行、ASM=ASM CHECK 行、CMT=纯注释行）：

| 文件 | SRC | OBJ | ASM | CMT | 合计 |
|---|---|---|---|---|---|
| `riii_branch.s` | 6 | 7 | 6 | 6 | 25 |
| `iiii_jump.s` | 3 | 2 | 2 | 1 | 7 |
| `rrii_branch.s` | 2 | 1 | 1 | 1 | 4 |
| `e_flags.s` | 1 | 0 | 0 | 0 | 1 |
| `smoke_jump.s` | 1 | 0 | 0 | 2 | 3 |
| **合计** | **13** | **10** | **9** | **10** | **40** |

> 说明：riii_branch.s 含 7 个 OBJ 行（6 个 `4i` + 1 个 `3i`，L54 的 label fixup 用例）；L56 的 ASM 行用 `{{.*}}` 通配符，不含 `i]`，不需改。

### 转换规则

`<N>i` → `<N×4>`（字节值）。逐指令编码验证：

| 原写法 | 新写法 | 字节值 | field = bytes>>2 | OBJ 编码 | 验证 |
|---|---|---|---|---|---|
| `0i` | `0` | 0 | 0 | 不变 | 0×4=0 ✓ |
| `1i` | `4` | 4 | 1 | 不变 | 1×4=4 ✓ |
| `2i` | `8` | 8 | 2 | 不变 | 2×4=8 ✓ |
| `3i` | `12` | 12 | 3 | 不变 | 3×4=12 ✓ |
| `4i` | `16` | 16 | 4 | 不变 | 4×4=16 ✓ |
| `24i` | `96` | 96 | 24 | 不变 | 24×4=96 ✓ |

> **注**：`1i` 对应 **4 字节**（不是 8）。实测 `jump [rb0, 1i]` 的 encoding = `70 00 00 01`（field=1，1×4=4 字节）。

### 详细改动

#### 1. 每个 `i` 出现的改动

- **SRC 行**（源码指令）：`br.n {rd0}?, [rb0, 4i]` → `br.n {rd0}?, [rb0, 16]`
- **OBJ 行**（CHECK 模式）：`{{[0-9a-f]+:}} 68 00 00 04{{.*}}br.n{{.*}}{rd0}?, [rb0, 4i]` → `{rd0}?, [rb0, 16]`（编码字节 `68 00 00 04` **不变**）
- **ASM 行**（CHECK 模式）：`; ASM: br.n {rd0}?, [rb0, 4i]` → `{rd0}?, [rb0, 16]`
- **CMT 行**（注释）：`; br.n {rd0}?, [rb0, 4i]` → `{rd0}?, [rb0, 16]`

#### 2. OBJ 行编码不变的原理

汇编器收到 `br.n {rd0}?, [rb0, 16]` → 解析字节偏移=16 → `%4==0` ✓ → `field = 16>>2 = 4` → encoding `68 00 00 04` → 与旧 `4i` 相同。OBJ CHECK 模式中的字节部分**无需修改**，只需更新尾部的汇编文本模式。

## 验收标准

1. **全量无 `i` 残留**：`grep -rn '[0-9]i\]' tests/lit/MC/Dadao/*.s tests/e2e/*.s` 退出码 1
2. **字节值正确**（手动抽验 3 处）：
   - `jump [rb0, 4]` → OBJ 行应含 `70 00 00 01`（4>>2=1，与旧 `1i` 编码相同）
   - `br.n {rd0}?, [rb0, 16]` → OBJ 行应含 `68 00 00 04`（16>>2=4）
   - `br.n {rd0}?, [rb0, 12]` → OBJ 行应含 `68 00 00 03`（12>>2=3，L54 label fixup）
3. **`make check-lit` 全通过**（BLOCKED，见预检）：`make check-lit` 退出码 0（MC 22/22 + E2E 3/3）
4. **文件计数**：改动文件 = 5

## 下发前预检

1. **任务书内部一致性**：✅ D3 覆盖；40 行精确计数；转换表逐指令验证；OBJ 不变 / ASM 更新的逻辑自洽
2. **依赖链实际可用性**：✅ 依赖 LLVM-026t（新 llvm-mc）；本任务只改 `.s` 文本
3. **验收可执行性**：
   - 验收 1（grep 无残留）：**现在可跑**
   - 验收 2（手动抽验 OBJ 编码）：**现在可跑**（对比文件内容即可）
   - 验收 3（`make check-lit`）：**BLOCKED**（需 LLVM-026t 完成 + `make build-mc` + `make build-qemu`；替代证据：验收 1–2 的手动比对 + 验收 4 的文件计数）
4. **与 spec/vectors 一致**：✅ 不改 `contracts/opcodes.yaml`、不改 `tests/vectors/`

## 完成区

**测试结果**：复核-only，未做任何改动。全部 4 项复核通过。

**修改文件**：无（LLVM-026t 已完成全部迁移，本任务仅复核）

**验收结果**：

1. **grep 无 `i` 残留**：`grep -rnE '[0-9]+i[][ ,;)]' tests/lit/MC/Dadao/*.s tests/e2e/*.s` → 退出码 1（无匹配）。✅
2. **字节值正确性（逐文件逐行校验）**：
   - `riii_branch.s`：7 个 `[rb0, 16]`（原 `4i`，16÷4=4）+ 1 个 `[rb0, 12]`（原 `3i`，12÷4=3），OBJ 编码 `68–6d 00 00 04` / `68 00 00 03` 均正确，注释/ASM 同步。✅
   - `iiii_jump.s`：2 个 `[rb0, 4]`（原 `1i`，4÷4=1），OBJ `70 00 00 01` / `74 00 00 01`。✅
   - `rrii_branch.s`：1 个 `[rb0, 16]`（原 `4i`），OBJ `6e 20 00 04`。✅
   - `e_flags.s`：`jump [rb0, 0]`（原 `0i`）。✅
   - `smoke_jump.s`：`jump [rb0, 8]`（原 `2i`，8÷4=2），指令行+注释行均已同步。✅
3. **抽验编码一致性**（验收标准 3 条）：
   - `jump [rb0, 4]` → `70 00 00 01`（`iiii_jump.s` L11）✅
   - `br.n {rd0}?, [rb0, 16]` → `68 00 00 04`（`riii_branch.s` L11）✅
   - `br.n {rd0}?, [rb0, 12]` → `68 00 00 03`（`riii_branch.s` L53）✅
4. **`make check-lit`**：25/25 PASS，退出码 0（MC 22/22 + E2E 3/3）。✅
5. **文件变动**：`git status --short tests/lit/MC/Dadao/*.s tests/e2e/*.s` → 无输出（确认复核-only 未引入改动）。✅

**新发现/坑**：无。

**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 5 个文件的所有偏移量字节值：
- 所有 `<N>i` → `<N×4>` 转换正确（0→0, 1→4, 2→8, 3→12, 4→16）
- OBJ 编码字节与 `field = bytes>>2` 计算一致（6 个分支指令 op + 2 个 jump/call op + 1 个 rrii 分支）
- ASM/注释行同步更新
- 无遗漏、无错误
- 判决：通过，无需修改

#### 第 1 轮 reviewer 验收