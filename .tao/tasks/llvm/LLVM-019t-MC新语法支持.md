# LLVM-019t: 更新 LLVM MC 补丁——parser/printer/disassembler 新语法

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（规范已更新）、`LLVM-017t` + `LLVM-018t`（生成器已更新，可生成新语法示例供参考）
**状态**：待开始

## 执行环境
**执行环境**：本地（`.work/source/llvm-project`，补丁在 `components/llvm-project/patches/`）

## 接口规范

- 输入：现有 LLVM MC 补丁（`DADAOAsmParser`/`DADAOMCInstPrinter`/`DADAODisassembler`）、`docs/spec/assembly-language.md` v2
- 输出：更新后的 LLVM MC 补丁，支持新语法
- 约束：只改 parser/printer/disassembler 相关文件，不改 TableGen/CodeEmitter

## 修改内容

### 1. Parser（`DADAOAsmParser.cpp`）

新增语法元素的解析：

**a. 寄存器组 `{...}`**：
- `{rd8}` — 单寄存器组（count=1）
- `{rd8:rd11}` — 范围（`:` 分隔，推导 count=4）
- `{rd8, rd9}` — 双目的寄存器对（恰好 2 个寄存器，无 `:`）
- `{rd8, rd0}?` — 条件寄存器组（`?` 紧跟 `}`）
- `{rd3}?` — 单寄存器条件组

**b. 地址表达式 `[...]`**：
- `[rb2, 1]` — 访存（基址 + 立即数字节偏移）
- `[rb0, 2i]` — iiii 跳转（基址 + 立即数指令字偏移，`i` 后缀）
- `[rb3, rd0, 24i]` — rrii 跳转（基址 + 寄存器偏移 + 立即数指令字偏移）

**c. 单位后缀 `i`**：
- 紧跟立即数之后，表示该立即数以指令字（4 字节）为单位
- 仅在 `[...]` 内的跳转/分支偏移位置接受

**d. 条件标记 `?`**：
- 紧跟 `}` 之后，标记该组为条件寄存器

### 2. Printer（`DADAOMCInstPrinter.cpp`）

**a. 指令格式输出**：
- 双目的 `rrrr`：`add.uo {rd8, rd9}, rd10, rd11`
- 条件赋值 `rrrr`：`cs.n {rd1}?, rd2, rd3, rd4`、`cs.eq {rd8, rd0}?, rd9, rd10`
- 多寄存器 `orri`：`ra2rd {rd8:rd10}, {ra1:ra3}`
- 多寄存器 `rrri`（`ldm`/`stm`）：`ldm.ub {rd8:rd10}, [rb0, rd1]`
- 地址表达式：`ld.ub rd8, [rb2, 1]`、`jump [rb0, 2i]`

**b. 规范化**：
- 花括号内逗号后统一加空格
- 范围 `{rd8:rd11}` 不展开为单寄存器

### 3. Disassembler（`DADAODisassembler.cpp`）

- 输出格式与 printer 一致（往返一致，见 `assembly-language.md` §10）
- 双目的指令：从编码中提取 `rdha` 和 `rdhb`，输出 `{rdha, rdhb}`
- 多寄存器指令：从编码中提取 `rdhb`/`rdhc` 和 `immu6`，输出 `{rdhb:rdhb+immu6-1}, {rdhc:rdhc+immu6-1}`
- 地址表达式：从编码中提取基址/偏移，输出 `[rbN, imm]` 或 `[rb0, immi]`

## M1 指令枚举方法

验收需要覆盖全部 178 条 M1 指令。可执行枚举方法：

```bash
# 从 opcodes.yaml 提取所有 M1 指令（排除 excluded_m1）
python3 -c "
import yaml
entries = yaml.safe_load(open('contracts/opcodes.yaml'))
m1 = [e for e in entries if not e.get('excluded_m1')]
print(f'M1 count: {len(m1)}')
for e in m1:
    print(e['id'])
"
```

该列表用于：
1. 生成全量测试 `.s` 文件（每条指令一个用例）
2. 与 printer/disassembler 输出逐条比对

## 验收标准

1. `make build-mc` 成功（补丁应用 + 编译通过）
2. 全部 178 条 M1 指令可通过新语法汇编——方法：用上述脚本生成包含所有指令的 `.s` 文件，`llvm-mc -show-encoding` 全部成功
3. 全部 178 条 M1 指令的反汇编输出使用新语法——方法：将汇编后的 obj 文件 `llvm-mc -disassemble`，grep 确认无旧语法残留
4. 往返一致：汇编 → 反汇编 → 汇编 得到逐字节相同的编码（`assembly-language.md` §10）
5. 双目的指令：`echo "add.uo {rd8, rd9}, rd10, rd11" | llvm-mc` 正确编码
6. 多寄存器指令：`echo "ra2rd {rd8:rd10}, {ra1:ra3}" | llvm-mc` 正确编码（count=3）
7. 条件指令：`echo "br.eq {rd8, rd0}?, [rb0, 4i]" | llvm-mc` 正确编码
8. 地址表达式：`echo "ld.ub rd8, [rb2, 1]" | llvm-mc` 和 `echo "jump [rb0, 2i]" | llvm-mc` 正确编码
9. 旧语法不再被接受（`add.uo rd8, rd9, rd10, rd11` 报错）
10. 反例验证：故意将 `add.uo` 的 printer 改为旧语法，确认反汇编输出不一致（往返失败）
11. `make check` 通过（无回归）

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
