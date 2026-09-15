# TESTCASES-004t: 向量覆盖率修复（opcode identity + encoding.word 补全）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tools/testcases/validate_vectors.py`（TESTCASES-002t，当前实现）
  - `contracts/opcodes.yaml`（唯一编码身份 `(op, ha)`；`op = value>>24`、`ha = (value>>18)&0x3f`；`insn` 单独不唯一）+ `mask`/`value`
  - `tests/vectors/isa/*.yaml`（TESTCASES-002t/003t 向量）
- 输出：
  - `tools/testcases/validate_vectors.py`（覆盖率主键改为 `(insn, format)`；新增 `encoding.word` mask/value 校验）
  - `tests/vectors/isa/*.yaml`（补全缺漏的向量与空/缺失的 `encoding.word`）
- 约束：
  - **不改** `contracts/opcodes.yaml`（它是 oracle）
  - **不改** `tests/vectors/schema.md`（除非补字段文档）
  - `make check` 必须通过，覆盖率输出必须列出 M1 scope 全部 `(insn, format)`
  - 缺漏身份必须补**真实 active** 向量，不新增 deferred 顶替
  - 完成后不自行 commit

## 背景（完整）

### 目标

1. 修改 `tools/testcases/validate_vectors.py`：以指令身份 `(insn, format)` 为覆盖率主键（v5 等价于 0628 的 `(op, ha)`）
2. 补全所有向量的 `encoding.word`（semantic/boundary/legality 中可能有缺漏）
3. 校验 `encoding.word` 符合对应 opcode 的 `mask`/`value` 约束
4. 使 validator 在任一 M1 scope 指令身份缺向量时报错

### 设计理由

0628 `validate_vectors.py` 以 `(mnemonic, format)` 为覆盖率主键，导致两类误报：

1. **假全覆盖**：`0x47 ldmo`、`0x4D andnw-rb` 与其他 opcode 同 mnemonic+format，被已有向量错误"顶替"，脚本报 `79/79 covered OK`，但这两条指令实际无向量。
2. **`encoding.word` 未验证**：脚本不检查 `encoding.word` 是否符合 `opcodes.yaml` 的 `mask`/`value`，错误字段可静默通过。

v5 的 `opcodes.yaml` 用 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`）区分 RD/RB/RA 变体，比 `(op, ha)` 更直观；但 **`insn` 单独并不唯一**——`ext.*`/`shr.*`/`shl.*` 的 `orrr` 与 `orri` 记录共享同一 `insn`（实测 20 组重复），故覆盖率主键必须用 `(insn, format)`（256/256 唯一），否则这 20 组会重演同类假全覆盖。

### 关键概念 / 数据

- **主键**：`(insn, format)`（唯一标识编码身份）。建立 `(insn, format) → record` 索引，并维护 `covered_ids` 集合。
- **encoding.word 校验**：对每条带 word 的 case，找到匹配 `(insn, format)` 的 record，断言 `(wval & mask) == value`；不匹配追加 error。
- **覆盖率报告**：遍历 M1 scope 内全部 `(insn, format)`，不在 `covered_ids` 的报 `COVERAGE MISSING: <insn> <format>`。
- **M1 scope 限定**：以 `contracts/opcodes.yaml` 的 `excluded_m1 != true` 为唯一判据（78 条排除：浮点 RF 全部、特权 cfx、LR-SC 原子），**不得**排除 RA 存取/块赋值（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`ra2rd`/`rd2ra`）或系统指令（`swym`/`illi`/`fence`）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017a-vectors-identity-fix.md`（完整转述：背景两类误报、目标 4 条、`load_opcodes` 建立 `(op, ha)` 索引、`encoding.word` mask/value 校验、覆盖率主键改 `(op, ha)`、补全高优先级向量、约束、验收，以及两轮 Architecture Review）

## 交付物

- `tools/testcases/validate_vectors.py`：
  - `(insn, format)` 主键索引与覆盖率统计
  - `encoding.word` 的 `(wval & mask) == value` 校验
  - 覆盖率缺失报 `COVERAGE MISSING: <insn> <format>`
- `tests/vectors/isa/*.yaml`：补全缺漏 `(insn, format)` 的 active 向量；补全空/缺失的 `encoding.word`（按 §2.2 公式或 opcodes.yaml 的 `value` 推导）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **覆盖率主键**：0628 用 `(op, ha)`；v5 用 `(insn, format)`（`insn` 单独非唯一——20 组 `orrr`/`orri` 共享 `insn`；`(insn, format)` 天然区分 `ld.o-rd`/`ld.o-rb`/`or.w-rd`/`or.w-rb` 等变体，且 256/256 唯一）。
2. **编码表路径**：`contracts/opcodes.yaml`（0628 `tools/opcodes.yaml`）。
3. **助记符**：0.5.3 命名（`ldmo`→`ldm.o`、`andnw-rb`→`andn.w-rb` 等）。
4. **M1 scope**：v5 以 `excluded_m1` 字段为唯一判据（78 条 RF/cfx/LR-SC 排除，178 条 M1）；0628 仅排除 `rd2ra`/`ra2rd`，而 **v5 的 `rd2ra`/`ra2rd` 属 M1**，不得排除。
5. **encoding.word 公式**同 0628（§2.2），但字段位置以 v5 `contract-isa.md` 为准；`ha` 由 `(value>>18)&0x3f` 推导（`opcodes.yaml` 无独立 `ha` 字段）。

## 已知坑 / 结论

摘自 DADAO-0628 DL-017a：

1. **假全覆盖**：`(mnemonic, format)` 主键让同组 opcode 互相顶替；v5 用 `(insn, format)` 根除（`insn` 单独仍会因 `orrr`/`orri` 碰撞而假覆盖，必须带 `format`）。
2. **encoding.word 未验证**：必须显式校验 mask/value，否则错误字段静默通过。
3. **不改 oracle**：`opcodes.yaml` 不动，问题在 validator/数据。
4. **补真实 active 向量**：缺漏身份不得用 deferred 顶替。
5. **边界**：`excluded_m1` 条目从覆盖率检查排除，避免 false negative；**M1 内的 `rd2ra`/`ra2rd` 不得排除**（0628 曾排除，v5 不同）。
6. **主键修复的验收方式**：可临时移除一条变体向量，validator 必须报 `COVERAGE MISSING`（此点在 005t 完整验证）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017a-vectors-identity-fix.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/scripts/validate_vectors.py`
- 本项目：`tools/testcases/validate_vectors.py`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md` §2
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `tools/testcases/validate_vectors.py` 覆盖率主键为 `(insn, format)`（grep 可确认索引与统计）
2. validator 对 `encoding.word` 执行 `(wval & mask) == value` 校验；故意改错一条 word 时 `make check` 报错
3. M1 scope（`excluded_m1 != true`）内每个 `(insn, format)` 均有 ≥1 active 向量，无 `COVERAGE MISSING`
4. `contracts/opcodes.yaml` 未被修改
5. `python3 tools/testcases/validate_vectors.py` 零错误，输出 `N/N opcodes covered OK`（N = 178）
6. `make check` PASS
7. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
