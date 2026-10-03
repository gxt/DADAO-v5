# INFRA-024t: check_asm_prose 去 `i` 后缀与 `%4` 对齐门控

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：SPEC-082t + TESTCASES-021t（文档 + 测试文件均更新后，prose 检查才不会报假阳性/假阴性）
**状态**：待开始

## 目标

落地 ADR-0013 D3（取消 `i` 后缀）的门控更新：修改 `tools/spec/check_asm_prose.py`，移除 `i` 后缀校验规则（R2、R3），新增**字节偏移 `%4==0` 对齐校验**规则。

## 执行环境

**执行环境**：本地

## 范围

### 文件清单

| 文件 | 改动 |
|---|---|
| `tools/spec/check_asm_prose.py` | 移除 R2（jump/call `i` 后缀校验，~L492–501）与 R3（escape `immi` 模式，~L530–533）；新增 R2'（文档示例中跳转/分支/escape 的字节偏移须 `%4==0`）；更新规则注释 |

### 约束

- `check_asm_prose.py --strict` 是 `make check` 门控的一部分
- 新增的 `%4` 校验只检查**文档示例中的字面数字**（不检查符号/标签偏移）
- 脚本对其余规则（条件标记 `{…}?`、地址表达式 `[...]`、寄存器组等）必须正常工作

### 详细改动

#### 1. 移除 R2：jump/call `i` 后缀校验

当前逻辑（~L492–501）：检查 jump/call/branch 目标中裸数字是否有 `i` 后缀。

改动：**删除**该规则分支。字节化语法中地址立即数为裸数字（无后缀），不应报错。

#### 2. 移除 R3：escape `[excp_cause_ip, immi]` 模式

当前逻辑（~L530–533）：检查 escape 的第二个参数是否有 `i` 后缀。

改动：**删除**该规则分支。

#### 3. 新增 R2'：字节偏移 `%4==0` 对齐校验

新规则：文档示例中，跳转/分支/escape 的**字面数字偏移**须 `%4==0`。

- 匹配 `[rb0, <N>]`、`[excp_cause_ip, <N>]`、以及 **rrii 形 `[rbN, rdN, <N>]`**（`jump`/`call` 的 rrii，如 `jump [rb3, rd0, 96]`）中的 `<N>`
- 校验 `N % 4 == 0`（负数取绝对值后校验）
- **不检查**：符号偏移（如 `[rb0, overflow_handler]`）、访存偏移（`ld.ub rd8, [rb2, 1]`——`imms12` 不要求 `%4`）
- 消歧：通过指令助记符区分（`jump`/`call`/`br.*`/`escape` 的偏移须 `%4`；`ld.*`/`st.*` 的不要求）

#### 4. 更新规则注释

规则列表注释中 R2/R3 描述更新为"已移除（字节化语法无需 `i` 后缀）"；新增 R2' 描述。

#### 5. 补注 `docs/spec/component-patching.md §6.3`（N3，2026-10-03 由 LLVM-026t 复核并入）

- `git diff <base> -- <path>` 对**新增文件**输出为空（2026-10-02 实测）⇒ 补注：**新增文件**用 `git diff --no-index /dev/null <relpath>`（或等价）。
- 补注「补丁可重建源树」的机械核对：应用产物与 `.work/source` 内容一致 + `make check-patch-tree` 断言⑥。
- 点明陷阱：**`git apply --check` 对空补丁恒通过**（2026-10-02 事故根因之一）。

## 验收标准

1. **脚本可运行**：`python3 tools/spec/check_asm_prose.py --strict` 退出码 0（在当前文档上不报假阳性）
2. **`make check-asm-prose` 通过**：`make check-asm-prose` 退出码 0
3. **无 `i` 规则残留**：`grep -n 'suffix.*i\b\|immi\|i.*后缀' tools/spec/check_asm_prose.py` 无匹配（或仅有注释"已移除"）
4. **`%4` 规则存在**：`grep -n '%.*4\|modulo.*4\|对齐\|alignment' tools/spec/check_asm_prose.py` 有输出
5. **反例验证**：在临时文件中故意写 `jump [rb0, 7]`（非 `%4`），运行脚本应报错；写 `jump [rb0, 8]` 不报错

## 下发前预检

1. **任务书内部一致性**：✅ 目标/范围/约束/验收一致；移除旧规则 + 新增 `%4` 对齐规则逻辑自洽
2. **依赖链实际可用性**：⚠️ 依赖 SPEC-082t + TESTCASES-021t（文档和测试文件已去 `i`）；否则脚本移除规则后旧文档不报错但语义已变
3. **验收可执行性**：
   - 验收 1–2（脚本运行 + make 目标）：**BLOCKED**（需 SPEC-082t 完成后文档中不含 `i` 后缀；替代证据：检查 diff 确认规则已移除/新增）
   - 验收 3–4（grep 检查规则内容）：**现在可跑**（检查脚本源码即可）
   - 验收 5（反例验证）：**BLOCKED**（需 SPEC-082t 完成；替代证据：手动审查 `%4` 校验逻辑）
4. **与 spec/vectors 一致**：✅ 不改 `contracts/opcodes.yaml`、不改 `tests/vectors/`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收