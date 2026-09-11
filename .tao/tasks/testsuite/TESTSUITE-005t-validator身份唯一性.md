# TESTSUITE-005t: validate_vectors.py 身份唯一性修复

**模块**：testsuite
**项目里程碑**：M1
**依赖**：`TESTSUITE-004t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `verif/validate_vectors.py`（TESTSUITE-004t：已改 `insn` 主键、已加 `encoding.word` mask/value 校验）
  - `verif/opcodes.yaml`（`insn` 分组与 mask/value 来源）
  - `tests/vectors/isa/*.yaml`（含共享 mnemonic+format 的变体，如 `ld.o-rd`/`ld.o-rb`）
- 输出：`verif/validate_vectors.py`（覆盖率标记逻辑修复：只标记**实际匹配 encoding.word** 的那条 opcode 记录）
- 约束：
  - 只改 validator，不改向量数据、不改 opcodes.yaml
  - 修复后覆盖率数值不得虚降（真实覆盖应保持）
  - 完成后不自行 commit

## 背景（完整）

### 目标

修复 `validate_file()`：只将**实际匹配 `encoding.word` 的那条 opcode 记录**标为 covered，不允许同组的兄弟 opcode 身份互相顶替。

### 设计理由

0628 `validate_vectors.py` 的覆盖率标记逻辑中，当发现某向量的 `(mnemonic, format)` 存在于 `opcodes.yaml` 时，会将该组内**所有** `(op, ha)` 身份全部标为 covered：

```python
elif status == "active":
    for rec in opcodes_by_mnem_fmt[key]:   # 遍历整组
        opid = (rec["op"], str(rec.get("ha")))
        covered_opids.add(opid)            # 全组标为 covered ← BUG
```

**影响举例**：`ldo rrii`（v5：`ld.o-rb`/`ld.o-rd`）在 opcodes 中同 mnemonic+format 有多条记录。当只测了 RD 变体时，RB 变体的身份也被标为 covered，即使其向量不存在。当前数据恰好都有向量，故覆盖数看似真实——但若去掉某条变体向量，validator 不会发现。v5 的 `opcodes.yaml` 有 18 组重复 `(mnemonic, format)`，该缺陷影响面更大。

### 关键概念 / 数据

**修复规格**（把 mask/value 校验与覆盖率标记合并为一次遍历，只标记匹配的 record）：

```
if word and mnem != "?" and fmt != "?":
    recs = opcodes_by_insn / 按 insn 分组
    if recs:
        wval = int(word, 16)
        matched_rec = None
        for rec in recs:
            if (wval & mask) == value:
                matched_rec = rec
                break
        if matched_rec is None:
            errors.append(f"{tag}: encoding.word {word} does not match ...")
        elif status == "active":
            covered_insns.add(matched_rec["insn"])   # 只标记匹配的那条
```

- 原有的 mnemonic+format 存在性检查（无 word 时）保留，但**删除**其中的整组 covered 标记。
- 覆盖率现在**仅由 mask/value 精确匹配驱动**。
- v5 以 `insn` 为身份，`matched_rec` 直接取其 `insn`。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017b-validator-identity-uniqueness.md`（完整转述：背景缺陷、目标、修复规格前后对比、验收步骤，以及代码级 Architecture Review）

## 交付物

- `verif/validate_vectors.py`：覆盖率标记逻辑重构，`covered_*` 的填充只发生在精确匹配分支，且仅 1 处调用

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **身份键**：0628 的 bug 在 `(op, ha)` 分组上；v5 用唯一 `insn`，修复后只标记匹配的 `insn`。v5 重复 `(mnemonic, format)` 组有 18 组（0628 为 7 对），故该修复更重要。
2. **助记符**：示例 `ldo rrii` 在 v5 为 `ld.o-rd`/`ld.o-rb`。
3. **编码表路径**：`verif/opcodes.yaml`。
4. 其余修复逻辑与 0628 一致（合并遍历、精确匹配、单点标记）。

## 已知坑 / 结论

摘自 DADAO-0628 DL-017b 代码级 Architecture Review：

1. **根因**：覆盖率标记对整组 opcode 身份生效，导致兄弟身份互相顶替。
2. **修复**：mask/value 校验与覆盖率标记合并；`covered.add()` 只应出现 **1 处**，且仅当 `matched_rec` 非 None 且 `status=active`。
3. **无 word 分支**：只校验身份存在性，**不**做覆盖率标记。
4. **验收方式**：临时移除一条 RB 变体向量，validator 必须报该身份 `COVERAGE MISSING`；恢复后 `make check` 再次 PASS。
5. **grep 验证**：`grep -n "covered.*add" verif/validate_vectors.py` 应只有 1 处。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-017b-validator-identity-uniqueness.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/scripts/validate_vectors.py`
- 本项目：`verif/validate_vectors.py`、`verif/opcodes.yaml`、`tests/vectors/isa/`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `make check` PASS，覆盖率数值不低于修复前（真实覆盖不变）
2. 手动移除一条共享 `(mnemonic, format)` 的变体向量后，validator 报该 `insn` 的 `COVERAGE MISSING`；恢复后 PASS
3. `grep -n` 确认覆盖率标记只发生在精确匹配分支、且只有 1 处
4. 未改向量数据、未改 `verif/opcodes.yaml`
5. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
