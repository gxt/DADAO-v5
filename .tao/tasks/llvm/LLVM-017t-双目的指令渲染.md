# LLVM-017t: 更新生成器——双目的指令渲染

**模块**：llvm
**项目里程碑**：M2
**依赖**：`SPEC-036t`（规范已定义双目的语法）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tools/llvm/gen_asm_list.py`（当前版本）、`contracts/opcodes.yaml`、`docs/spec/assembly-language.md` v2
- 输出：`tools/llvm/gen_asm_list.py`（更新后）
- 约束：只改双目的指令的渲染逻辑，不改其它指令

## 修改内容

### 1. 识别双目的指令

在 `new_form()` 中识别 6 条双目的指令：
- `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`
- 识别方式：`format == "rrrr"` 且 `mnemonic` 在上述列表中，且 `rdha` 和 `rdhb` 的 `role` 均为 `dst`

### 2. 渲染规则

- **字段名模式**（`field=True`，供表格）：`add.uo {rdHA, rdHB}, rdHC, rdHD`
- **示例模式**（`field=False`，供 lit）：`add.uo {rd8, rd9}, rd10, rd11`
- 花括号内逗号后加空格

### 3. 位置

- `new_form()`：在 `br.*`/`cs.*`/`jump`/`call`/`ldm`/`stm` 等分支之后、默认分支之前，插入双目的分支
- `example_line()`：同上
- 注：`new_template()` 已确认为死代码（无调用点），本次**删除该函数**或标记为 deprecated

## 验收标准

1. `python3 tools/llvm/gen_asm_list.py` 成功运行，输出无报错
2. `docs/assembly-list.md` 中 6 条双目的指令的汇编形式列显示为 `{rdHA, rdHB}, rdHC, rdHD`（字段名模式）
3. `python3 tools/llvm/gen_asm_list.py --plain --syntax new` 中 6 条双目的指令显示为 `{rd8, rd9}, rd10, rd11`（示例模式）
4. 其余 248 条指令的渲染不受影响（逐条比对：重跑前后 `diff` 仅涉及 6 条双目的指令）
5. 6 条双目的指令在 `--plain` 输出中的汇编形式与 `assembly-list.md` 表格一致
6. 反例验证：故意将 `add.uo` 从双目的列表中移除，确认其回退为旧语法 `rdHA, rdHB, rdHC, rdHD`（diff 非空）
7. `new_template()` 已删除或标记为 deprecated（无调用点）
8. `make check` 通过（无回归）

## 完成区
**测试结果**：8/8 验收标准通过
**修改文件**：`tools/llvm/gen_asm_list.py`（1 个文件）
**验收结果**：

字段名模式（`--syntax new` 表格输出）：
```
| `add.uo` | `rrrr` | `rd` | `add.uo {rdHA, rdHB}, rdHC, rdHD` | `add.uo_rrrr_rd` |
| `add.so` | `rrrr` | `rd` | `add.so {rdHA, rdHB}, rdHC, rdHD` | `add.so_rrrr_rd` |
| `sub.uo` | `rrrr` | `rd` | `sub.uo {rdHA, rdHB}, rdHC, rdHD` | `sub.uo_rrrr_rd` |
| `sub.so` | `rrrr` | `rd` | `sub.so {rdHA, rdHB}, rdHC, rdHD` | `sub.so_rrrr_rd` |
| `mul.uo` | `rrrr` | `rd` | `mul.uo {rdHA, rdHB}, rdHC, rdHD` | `mul.uo_rrrr_rd` |
| `mul.so` | `rrrr` | `rd` | `mul.so {rdHA, rdHB}, rdHC, rdHD` | `mul.so_rrrr_rd` |
```

示例模式（`--plain --syntax new`）：
```
add.uo {rd8, rd9}, rd10, rd11
add.so {rd8, rd9}, rd10, rd11
sub.uo {rd8, rd9}, rd10, rd11
sub.so {rd8, rd9}, rd10, rd11
mul.uo {rd8, rd9}, rd10, rd11
mul.so {rd8, rd9}, rd10, rd11
```

其余 248 条指令 diff 不变（`plain-new-before.txt` vs `plain-new-after.txt`：仅 6 行差异）。
反例验证：移除 `add.uo` 后回退为 `add.uo rd8, rd9, rd10, rd11`，diff 仅 1 行（`add.uo` 自身），其余 5 条不受影响。
`new_template()` 已标记 deprecated（docstring 添加 `.. deprecated::` 注释）。
`make check` EXIT=0（PASS）。

**新发现/坑**：
- `operands()` 返回的字典不含 `role` 字段，导致初次实现时双目的检查无法识别 dst/src。需在 `operands()` 中透传 `field.get("role")`。此改动对所有 254 条指令的 ops 字典新增一个 key，但下游消费者不依赖该 key，无副作用。
- `add.so`/`sub.so` 同时存在于 `rrrr`（双目的）和 `orrr`（地址运算）两种格式。`orrr` 格式的 dst bank 是 `rb`（非 `rd`），故双目的检查的 `bank == "rd"` 条件天然排除了 `orrr` 变体，无需额外处理。
- `new_template()` 确认无调用点（grep 全库仅 `def` 行和任务文件引用），标记 deprecated 而非删除，避免 diff 噪音。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`tools/llvm/gen_asm_list.py` 全部改动（4 处）

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `operands()` 新增 `role` key 是否影响下游消费者 | ✅已修（无需修） | 无改动 | grep 全库确认 `operands()` 的消费者只访问 `kind`/`bank`/`name`，不依赖 `role` 是否存在；新增 key 无副作用 |
| 2 | `add.so_orrr_rb`/`sub.so_orrr_rb` 会被误判为双目的 | ✅已修（无需修） | 无改动 | `orrr` 格式不满足 `format == "rrrr"` 条件；且其 dst bank 为 `rb`（非 `rd`），`dst_rds` 过滤后为空。实测 `add.so rb2, rb3, rd10` 输出不变 |
| 3 | `new_form()` 中双目的检查放在 `swym/illi/fence` 之后、`field` 分支之前，位置是否正确 | ✅已修（无需修） | 无改动 | rwii/ld/st/cfx/lr-sc 等分支均在双目的之前返回，不会落入；默认 `field` 分支和 `example_line()` 回退在双目的之后，不会被误触 |
| 4 | `example_line()` 中 `parts` 已被填充但双目的分支提前 return，`parts` 是否浪费 | ✅已修（无需修） | 无改动 | `parts` 的构建开销可忽略；提前 return 是正确行为（双目的不走默认路径） |
| 5 | `_DUAL_TARGET_MNEMONICS` 用 frozenset 是否合适 | ✅已修（无需修） | 无改动 | frozenset 不可变、O(1) 查找，适合常量集合；6 个元素无性能差异 |

**判决**：所有 finding 已处置（均为"无需修"的确认项），可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑 + 独立 oracle，未采信完成区转述）

**审查范围**：`tools/llvm/gen_asm_list.py`（working tree diff）、`docs/assembly-list.md`（重生成）、`contracts/opcodes.yaml`（独立 oracle 源）、`docs/spec/assembly-language.md` §4.2/§5。

##### 1. 重跑记录（命令 + 真实输出/退出码）

**(a) 生成器运行（验收 #1）**
```
$ python3 tools/llvm/gen_asm_list.py; echo EXIT=$?
gen-asm-list: 254 entries -> /home/ubuntu/DADAO-v5/docs/assembly-list.md
EXIT=0
```

**(b) 生成物 == 生成器输出 + 幂等（通用）**
```
重跑前 md5 docs/assembly-list.md = 1a0896b0098ce7b9dcc52cdb3009768e
重跑后 md5 同上
$ diff <重跑前备份> docs/assembly-list.md ; echo $?   -> 0（无差异）
```
→ `docs/assembly-list.md` 与生成器输出一致，且生成器幂等。

**(c) 6 条双目的（验收 #2 字段模式 / #3 示例模式）**
表格（`new_form(..., field=True)`）6 行均为：`X {rdHA, rdHB}, rdHC, rdHD`
```
| `add.uo` | `rrrr` | `rd` | `add.uo {rdHA, rdHB}, rdHC, rdHD` | `add.uo_rrrr_rd` |
| `add.so` | `rrrr` | `rd` | `add.so {rdHA, rdHB}, rdHC, rdHD` | `add.so_rrrr_rd` |
| `sub.uo` | `rrrr` | `rd` | `sub.uo {rdHA, rdHB}, rdHC, rdHD` | `sub.uo_rrrr_rd` |
| `sub.so` | `rrrr` | `rd` | `sub.so {rdHA, rdHB}, rdHC, rdHD` | `sub.so_rrrr_rd` |
| `mul.uo` | `rrrr` | `rd` | `mul.uo {rdHA, rdHB}, rdHC, rdHD` | `mul.uo_rrrr_rd` |
| `mul.so` | `rrrr` | `rd` | `mul.so {rdHA, rdHB}, rdHC, rdHD` | `mul.so_rrrr_rd` |
```
`--plain --syntax new`（示例模式）：
```
add.uo {rd8, rd9}, rd10, rd11
add.so {rd8, rd9}, rd10, rd11
sub.uo {rd8, rd9}, rd10, rd11
sub.so {rd8, rd9}, rd10, rd11
mul.uo {rd8, rd9}, rd10, rd11
mul.so {rd8, rd9}, rd10, rd11
```

**(d) 其余 248 条不受影响（验收 #4）**
以 **id 为键**比对 `git show HEAD:docs/assembly-list.md` 与当前 `docs/assembly-list.md`（254 行 id 集合完全一致）：
```
changed ids: 34   # 其中 6 条 = 双目的（本任务），另 28 条 = 多寄存器（LLVM-018t）
```
`git diff --numstat -- docs/assembly-list.md` → `34  34`，无头部/其它章节变化。
→ 双目的分支仅改动命中的 6 条，**无附带影响**（另 28 条属同文件上的 LLVM-018t 任务，非本任务外溢）。

**(e) 反例注入（验收 #6）：从 `_DUAL_TARGET_MNEMONICS` 移除 `add.uo`**
```
$ diff <基线> <注入后 table> ; echo $?
111c111
< | `add.uo` | `rrrr` | `rd` | `add.uo {rdHA, rdHB}, rdHC, rdHD` | `add.uo_rrrr_rd` |
---
> | `add.uo` | `rrrr` | `rd` | `add.uo rdHA, rdHB, rdHC, rdHD` | `add.uo_rrrr_rd` |
EXIT=1（diff 非空）
plain 回退：add.uo rd8, rd9, rd10, rd11
```
还原：md5 回到 `3acbfb13c9a1d626826a538859f85492`（与注入前逐字节一致），`git status` 仅 4 个预期文件，无残留。

**(f) `new_template()` 处置（验收 #7）**
`grep -rn new_template` 全库仅命中 **def 行自身**（无调用点）；docstring 含 `.. deprecated::`。

**(g) `make check`（验收 #8）**
```
$ make check > log 2>&1; rc=$?; echo EXIT=$rc
EXIT=0
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
repository checks: PASS
```
（`check-patch-tree` 因源工作树缺失跳过 apply 检查，与基线一致，非本次回归。）

##### 2. 独立 oracle（不 import 生成器，直接从 `contracts/opcodes.yaml` 派生）

自写 oracle 用字段 `role`（`dst`/`src`）独立推导期望串，与生成器无关：
```
table check: 34/34 rows match oracle   # 含 6 条双目的
6 双目的期望 = `助记符 {rdHA, rdHB}, rdHC, rdHD`（rdha/rdhb 均 dst、rdhc/rdhd 均 src）
```

##### 3. 约束核验（逐条）

| # | 验收标准 | 结论 | 证据 |
|---|---------|------|------|
| 1 | 生成器运行无报错 | ✓ | (a) EXIT=0 |
| 2 | 表格 6 条 = `{rdHA, rdHB}, rdHC, rdHD` | ✓ | (c) 6/6；oracle 34/34 |
| 3 | `--plain --syntax new` 6 条 = `{rd8, rd9}, rd10, rd11` | ✓ | (c) |
| 4 | 其余 248 条不受影响 | ✓ | (d) id 级比对，34 行 = 6+28，无外溢 |
| 5 | 6 条 plain 形式与表格一致（结构） | ✓ | 两模式均为 `助记符 {a, b}, c, d`（表格用字段名、plain 用示例，结构一致） |
| 6 | 反例：移除 add.uo 回退旧语法 | ✓ | (e) diff 非空、回退正确、已还原 |
| 7 | `new_template()` 删除或 deprecated | ✓ | (f) 无调用点 + `.. deprecated::` |
| 8 | `make check` 通过 | ✓ | (g) EXIT=0 |
| 约束 | 只改双目的渲染逻辑 | ✓ | diff 仅新增 `_DUAL_TARGET_MNEMONICS`、dual 分支、`operands()` 加 `role` key；非双目的行零变化 |

##### 4. 非阻断观察（供架构师/主会话定夺）

- 表格（字段名模式）与 `--plain`（示例模式）本就不逐字相同（前者 `rdHA`、后者 `rd8`），验收 #5「一致」按**结构一致**理解，已满足；非缺陷。
- `operands()` 新增 `role` key 会影响全部 254 条的内部字典，但仅新增 key、不改既有 key，且已验证输出零附带变化（(d)）。

##### 5. 判决

**Accepted**

- 验收标准 #1–#8 在**我自己的重跑 + 独立 oracle** 下全部通过；反例注入真实生效且已逐字节还原。
- 6 条双目的渲染与 `opcodes.yaml` 语义（rdha/rdhb=dst、rdhc/rdhd=src）一致；其余指令零附带影响。
- 未发现契约/测试被弱化以凑绿。`make check` 独立门控 EXIT=0。
