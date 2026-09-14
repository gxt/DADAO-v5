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
  - `contracts/opcodes.yaml`（唯一 `insn` 身份 + op/ha/mask/value）
  - `tests/vectors/isa/*.yaml`（TESTCASES-002t/003t 向量）
- 输出：
  - `tools/testcases/validate_vectors.py`（覆盖率主键改为 opcode 身份 `insn`；新增 `encoding.word` mask/value 校验）
  - `tests/vectors/isa/*.yaml`（补全缺漏的向量与空/缺失的 `encoding.word`）
- 约束：
  - **不改** `contracts/opcodes.yaml`（它是 oracle）
  - **不改** `tests/vectors/schema.md`（除非补字段文档）
  - `make check` 必须通过，覆盖率输出必须列出 M1 scope 全部 `insn`
  - 缺漏身份必须补**真实 active** 向量，不新增 deferred 顶替
  - 完成后不自行 commit

## 背景（完整）

### 目标

1. 修改 `tools/testcases/validate_vectors.py`：以 opcode 身份 `insn` 为覆盖率主键（v5 等价于 0628 的 `(op, ha)`）
2. 补全所有向量的 `encoding.word`（semantic/boundary/legality 中可能有缺漏）
3. 校验 `encoding.word` 符合对应 opcode 的 `mask`/`value` 约束
4. 使 validator 在任一 M1 scope opcode 身份缺向量时报错

### 设计理由

0628 `validate_vectors.py` 以 `(mnemonic, format)` 为覆盖率主键，导致两类误报：

1. **假全覆盖**：`0x47 ldmo`、`0x4D andnw-rb` 与其他 opcode 同 mnemonic+format，被已有向量错误"顶替"，脚本报 `79/79 covered OK`，但这两条指令实际无向量。
2. **`encoding.word` 未验证**：脚本不检查 `encoding.word` 是否符合 `opcodes.yaml` 的 `mask`/`value`，错误字段可静默通过。

v5 的 `opcodes.yaml` 有唯一 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`），比 `(op, ha)` 更直接，故覆盖率主键用 `insn`。

### 关键概念 / 数据

- **主键**：`insn`（唯一标识 opcode 变体）。建立 `insn → record` 索引，并维护 `covered_insns` 集合。
- **encoding.word 校验**：对每条带 word 的 case，找到匹配 `insn` 的 record，断言 `(wval & mask) == value`；不匹配追加 error。
- **覆盖率报告**：遍历 M1 scope 内全部 `insn`，不在 `covered_insns` 的报 `COVERAGE MISSING: <insn>`。
- **M1 scope 限定**：排除浮点 RF、原子 AMO、系统/特权、RA 多存取、`rd2ra`/`ra2rd` 等（以 002t 定义的 scope 为准），避免为 excluded 指令报缺失。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017a-vectors-identity-fix.md`（完整转述：背景两类误报、目标 4 条、`load_opcodes` 建立 `(op, ha)` 索引、`encoding.word` mask/value 校验、覆盖率主键改 `(op, ha)`、补全高优先级向量、约束、验收，以及两轮 Architecture Review）

## 交付物

- `tools/testcases/validate_vectors.py`：
  - `insn` 主键索引与覆盖率统计
  - `encoding.word` 的 `(wval & mask) == value` 校验
  - 覆盖率缺失报 `COVERAGE MISSING: <insn>`
- `tests/vectors/isa/*.yaml`：补全缺漏 `insn` 的 active 向量；补全空/缺失的 `encoding.word`（按 §2.2 公式或 opcodes.yaml 的 `value` 推导）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **覆盖率主键**：0628 用 `(op, ha)`；v5 用唯一 `insn`（更精确，天然区分 `ld.o-rd`/`ld.o-rb`/`or.w-rd`/`or.w-rb` 等变体）。
2. **编码表路径**：`contracts/opcodes.yaml`（0628 `tools/opcodes.yaml`）。
3. **助记符**：0.5.3 命名（`ldmo`→`ldm.o`、`andnw-rb`→`andn.w-rb` 等）。
4. **M1 scope**：v5 需显式 scope 门控（256 条记录中含大量 excluded），0628 仅排除 `rd2ra`/`ra2rd`。
5. **encoding.word 公式**同 0628（§2.2），但字段位置以 v5 `contract-isa.md` 为准。

## 已知坑 / 结论

摘自 DADAO-0628 DL-017a：

1. **假全覆盖**：`(mnemonic, format)` 主键让同组 opcode 互相顶替；v5 用 `insn` 根除。
2. **encoding.word 未验证**：必须显式校验 mask/value，否则错误字段静默通过。
3. **不改 oracle**：`opcodes.yaml` 不动，问题在 validator/数据。
4. **补真实 active 向量**：缺漏身份不得用 deferred 顶替。
5. **边界**：excluded 指令（0628 的 `rd2ra`/`ra2rd`；v5 的 M1 scope 外指令）从覆盖率检查排除，避免 false negative。
6. **主键修复的验收方式**：可临时移除一条变体向量，validator 必须报 `COVERAGE MISSING`（此点在 005t 完整验证）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017a-vectors-identity-fix.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/scripts/validate_vectors.py`
- 本项目：`tools/testcases/validate_vectors.py`、`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md` §2
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `tools/testcases/validate_vectors.py` 覆盖率主键为 `insn`（grep 可确认索引与统计）
2. validator 对 `encoding.word` 执行 `(wval & mask) == value` 校验；故意改错一条 word 时 `make check` 报错
3. M1 scope 内每个 `insn` 均有 ≥1 active 向量，无 `COVERAGE MISSING`
4. `contracts/opcodes.yaml` 未被修改
5. `python3 tools/testcases/validate_vectors.py` 零错误，输出 `N/N opcodes covered OK`
6. `make check` PASS
7. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
