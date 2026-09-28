# SPEC-034k: 汇编格式实现规划

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题根源

`docs/spec/assembly-language.md`（v1，2026-09-25 用户审核通过）定义了 DADAO 汇编语言的新语法（`{...}`/`?`/`i`/`[]`/`:`），但 LLVM MC 的 parser/printer/disassembler 仍使用旧语法。需要：
1. 补充规范中的双目的指令语法（6 条 `rrrr` 格式，两个 dst）和多寄存器组记法规则（28 条）
2. 将 `assembly-list.md` 的分类表格嵌入对应 `spec/SimRISC-XX-*.md`
3. 更新 LLVM MC 实现为新语法
4. 冻结汇编语法决策为 ADR

## 目的

完成汇编格式从规范到实现的全链路落地：规范补全 → ADR 冻结 → 生成器重构 → LLVM MC 实现 → 测试同步。

## 对照关系

- `docs/spec/assembly-language.md` v1：已定稿的语法规范（§2–§10），需补充 §4/§5 的双目的和多寄存器规则
- `docs/assembly-list.md`：由 `tools/llvm/gen_asm_list.py` 自动生成，当前使用旧语法渲染
- `contracts/opcodes.yaml`：254 条指令编码，权威数据源
- LLVM MC 补丁（`components/llvm-project/patches/`）：当前实现旧语法，需改为新语法
- DADAO-0628：参考实现（旧语法），仅作对照

## 任务分解

- 任务清单：`SPEC-034k`（本任务）、`SPEC-035t`、`SPEC-036t`、`SPEC-037t`、`LLVM-017t`、`LLVM-018t`、`LLVM-019t`、`LLVM-020t`、`TESTCASES-016t`
- 分解理由：按「规范 → 生成器 → MC 实现 → 测试」四阶段拆分，每阶段可独立验收
- 依赖关系：

```
SPEC-034k → SPEC-035t（ADR）→ SPEC-036t（规范更新）
                                    ├──→ TESTCASES-016t（向量同步，只依赖语法定义）
                                    ↓
                              LLVM-017t（双目的渲染）──┐
                              LLVM-018t（多寄存器渲染）──┤→ SPEC-037t（嵌入 spec）
                                                        ↓
                                                  LLVM-019t（MC 补丁，依赖 SPEC-036t + LLVM-017t + LLVM-018t）
                                                        ↓
                                                  LLVM-020t（lit + e2e + oracle + 生成器重跑）
```

| 阶段 | 任务 | 内容 |
|------|------|------|
| 1. 基础 | SPEC-035t | ADR-0013 冻结汇编语法决策（D1–D7） |
| 2. 规范 | SPEC-036t | 更新 `assembly-language.md`：双目的语法 + 多寄存器组记法 + `{...}` 速查表 + §5 拆分 + EBNF |
| 3. 生成器 | LLVM-017t | 更新 `gen_asm_list.py`：6 条双目的指令 `{rdHA, rdHB}` 渲染 |
| 3. 生成器 | LLVM-018t | 更新 `gen_asm_list.py`：28 条多寄存器指令 `{start:end}` 渲染 |
| 3. 生成器 | SPEC-037t | 重构 `gen_asm_list.py` 按类别输出到 12 个 spec 文件 |
| 4. MC | LLVM-019t | 更新 LLVM MC 补丁：parser/printer/disassembler 新语法 |
| 4. MC | LLVM-020t | 更新 lit/e2e/oracle 测试 + 重跑生成器更新 `assembly-list.md` |
| 5. 测试 | TESTCASES-016t | 同步测试向量汇编形式文本 |

### 不变量

- **生成器渲染变更后必须重跑 `--embed-spec`**：`LLVM-017t`/`LLVM-018t` 修改了 `gen_asm_list.py` 的渲染逻辑，`SPEC-037t` 的 `--embed-spec` 输出依赖这些渲染结果。因此 `SPEC-037t` 必须在 `LLVM-017t`+`LLVM-018t` 之后执行；若渲染逻辑再次变更，必须重跑 `--embed-spec` 以保持 spec 文件与生成器一致。

## 说明

- QEMU 模块不直接解析汇编文本（消费二进制编码），不受汇编语法变更影响
- 浮点运算（46 条）和待定（12 条）的汇编/反汇编/模拟器实现仍 deferred，但**汇编格式本次全部定义**
- ADR-0013 的 decision 须逐条与用户确认后方可写为 `Accepted`（主会话职责，交接物：`SPEC-035t` 输出 `Candidate` 状态的 ADR → 主会话逐条与用户确认 → 置 `Accepted`）
- `spec/` 目录**可由 spec 模块任务修改**（ADR-0012 D4：只有 spec 模块的任务才能修改 spec/ 下的文件）
