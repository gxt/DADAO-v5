# SPEC-058t: 术语统一 `major-op→opc` / `minor-op→opx` + 修正 wpN 与操作码的混淆

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：用户裁定（2026-09-30）
**状态**：待开始

## 背景与目标

**用户裁定（2026-09-30）**：
1. `major-op` / `major-opcode` 一类描述 → **`opc`**（opcode 的简写）
2. `minor-op` / `minor-opcode` 一类描述 → **`opx`**（opcode-auxiliary 的简写）
3. `wpN`（wyde-position）被当作操作码的一部分是**错误的**，须消除混淆（`SimRISC-00:192–194`）
4. **不改字段名**（`contracts/opcodes.yaml` 的 `op`/`ha` 写法**保持**）；**以改正文/注释为主**

## A. 术语替换（正文/注释）

| 旧 | 新 |
|---|---|
| `major-opcode` / `major opcode` / `major-op` | **`opc`**（首次出现可注「opcode 的简写」） |
| `minor-opcode` / `minor opcode` / `minor-op` | **`opx`**（首次出现可注「opcode-auxiliary 的简写」） |

落点（实测，排除历史不变量）：

| 文件 | 命中 | 说明 |
|---|---|---|
| `spec/SimRISC-00-指令系统设计.md` | 8 | 含 §指令域说明 + 操作数字母表 + MISC 子表段 |
| `spec/SimRISC-11-其它.md` | 1 | |
| `.tao/knowledge/contract-isa.md` | 18 | §2.2/§2.8/附录 A 表头等 |
| `.tao/knowledge/adr-0004-test-machine.md` | 2 | 就地改 + 注记 |
| `.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` | 1 | D2.2 的「（minor-op）」→「（opx）」；就地改 + 注记 |
| `docs/02-大道至简.md` | 1 | |
| `components/llvm-project/patches/.../DADAOInstrFormats.td.patch` | 10 | **注释** |
| `.../DADAO.h.patch` | 3 | **注释** |
| `.../Disassembler/DADAODisassembler.cpp.patch` | 1 | **注释** |
| `tools/llvm/generate_instrinfo.py` | 5 | 注释 4 + **`if role == "minor_op": continue`（死代码，见 §C）** |
| `tools/llvm/gen_asm_list.py` | 1 | docstring |
| `tools/testcases/generate_isa_vectors.py` | 1 | 注释 |
| `tools/qemu/smoke-dadao-m1.sh` | 1 | 注释 |
| `tests/lit/MC/Dadao/{orri,orrr,oiii,rb_ops}.s` | 4 | 注释（**不得**动 `# OBJ:`/`# ASM:` 行） |
| `contracts/legality_rules.yaml` | 1 | 描述文本 |
| `.tao/knowledge/deferred.md` | 1 | **活条目**措辞（历史条目不改） |

## B. 修正 `SimRISC-00:192–194`（opx 只可能是 ha；wyde-position 与操作码无关）

**用户裁定**：**`opx` 只可能是 `ha`（6 位）**；描述操作码时**不涉及 `hb`**，因此**也不涉及 wyde-position**。

**旧**：
```
op是操作码，简称为opcode，或者称之为major-opcode。
某些情况下，ha或ha+hb也可作为opcode，或称为minor-opcode。
特殊情况下（后16位作为立即数时），hb的头两位用来指定wyde在64位数据中的位置。
```

**新**：
```
op 是操作码，简称 opc（opcode 的简写），即头 8 位。
某些情况下，ha（6 位）也参与操作码，称为 opx（opcode-auxiliary 的简写）；opx 只可能是 ha。
```
（**删除**第 3 句——`hb` 头两位的 wyde-position 属**操作数域**，与操作码无关；该用法已在下文「含 wyde-position 的一种特殊格式」中说明）

**同类必须一并修正**：`.tao/knowledge/contract-isa.md:145`
`- 某些情况下 \`ha\` 或 \`ha+hb\` 也可作为 opcode（minor-opcode）。` → `- 某些情况下 \`ha\`（6 位）也参与操作码，称为 \`opx\`（opcode-auxiliary），**只可能是 ha**。`

> 全库核查（实测）：`ha+hb` 作为 **opcode** 的表述**仅此两处**；其余 `ha+hb+hc+hd` 命中均指 `iiii` 的 24 位立即数（合法，**不动**）。
> 相邻的「操作数寻址方式字母」表（`o`/`c`/`r`/`i`/`w`/`z`）**结构不动**，仅 `minor-opcode`→`opx`；如需进一步调整 `w` 的层级，**先问用户**。

## C. 待确认项（**禁止自行处置**）

`tools/llvm/generate_instrinfo.py:99` 的 `if role == "minor_op": continue` —— 经核查 `minor_op` **不是** `contracts/opcodes.yaml` 中的任何 role（已随 `ADR-0012 D2.2` 的「`ha` 并入 `op`」消失），属**死代码**。
**本任务默认不动该行**；若需改名/删除，**先与用户确认**。

## 约束

- **不改字段名**（`opcodes.yaml` 的 `op`/`ha`）
- **不改**历史不变量：`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、已完成 `.tao/tasks/**`、`deferred.md` 历史条目
- ADR（`0004`/`0012`）**就地改 + 注记**，不改写 decision 语义
- LLVM 补丁仅改**注释** ⇒ 需 `make prepare` 重放补丁（`check-patch-tree` 67 OK）；**无需**重编译
- 术语替换**逐条定位**，禁止无脑正则全局替换

## 验收标准

1. 全库（排除历史不变量）再无 `major-op*` / `minor-op*` 字样（`grep` 证据，逐条列出保留项及理由）
2. `SimRISC-00:192–194` 已改写，明确 **wyde-position 属操作数域、不属操作码**；语义与原句一致（逐句对照）
3. **字段名未变**：`contracts/opcodes.yaml` 的 `op`/`ha` 逐字未动（`git diff` 证据）
4. `tests/lit/MC/Dadao/*.s` 的 `# OBJ:`/`# ASM:` 行**未动**；`check_lit_bytes` 计数不变
5. `make prepare`（补丁重放）+ `make check` **EXIT=0**；`check-patch-tree` 67 OK
6. 反例验证：注入（如把某处 `opx` 改回 `minor-opcode`）→ 可检出；复原后无残留

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
