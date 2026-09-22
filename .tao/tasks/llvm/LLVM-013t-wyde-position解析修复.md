# LLVM-013t: wyde-position 操作数解析修复（`wpN` 静默误编码）

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-005t`（rwii 指令格式 TableGen）、`LLVM-006t`（AsmParser 与 CodeEmitter）、`LLVM-014m`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.work/build/llvm/bin/llvm-mc`（DADAO target）
  - `contracts/opcodes.yaml`（rwii 编码）、`.tao/knowledge/contract-isa.md` §2.3/§2.4（wyde-position）
  - `.work/source/llvm-project/llvm/lib/Target/DADAO/`（TableGen + AsmParser 源码）
- 输出：
  - 新补丁 `components/llvm-project/patches/0007-*.patch` + `components/llvm-project/patches/series` 更新
  - 新增 lit 用例（`tests/lit/MC/Dadao/`）
  - 完成区附真实输出
- 约束：
  - **不改指令编码语义**（`wp` 字段仍为 2 位，`hb{5:4}`）
  - **不改 `llvm-mc -filetype=asm` 的打印形态**（仍打印数字）——既有 17 个 lit 的 `ASM:` 前缀依赖数字打印，改动会大面积回归
  - 不改 `tests/vectors/isa/*.yaml`

## 背景（完整）

### 问题（`INTEG-002t` 发现，2026-09-22）

`llvm-mc` 对 rwii 的 `wydepos` 操作数**只接受数字**；把 `wp0`/`wp1`/`wp2`/`wp3` 这类 token 传进去时**不报错**，而是当作未定义符号**静默取 0**，导致一律编码为 `wp0`：

```
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj wpn.s -o wpn.o
$ .work/build/llvm/bin/llvm-objdump -d --triple=dadao-unknown-elf wpn.o
       0: 4e 04 ff ff  	set.zw	rb1, 0, 65535    # 源: set.zw rb1, wp2, 0xffff  ← 错！应为 4e 06 ff ff
       4: 4e 06 ff ff  	set.zw	rb1, 2, 65535    # 源: set.zw rb1, 2,   0xffff  ← 正确
       8: 4e 04 00 ff  	set.zw	rb1, 0, 255      # 源: set.zw rb1, wp1, 0x00ff  ← 错！应为 4e 05 00 ff
       c: 4e 05 00 ff  	set.zw	rb1, 1, 255      # 源: set.zw rb1, 1,   0x00ff  ← 正确
```

**静默误编译**属危险类别：无任何诊断，错误编码进入产物。当前影响面为零（现有 lit/生成器/脚本全用数字，`wpN` 仅出现在注释），但须修复。

### 设计（用户已于 2026-09-22 逐条确认，D1–D4 生效）

1. **接受** `wp0`/`wp1`/`wp2`/`wp3`（小写）作为数字 `0`–`3` 的等价写法；
2. **拒绝**其它非数字 token（如 `wp4`、`foo`）——**报错**，不得静默取 0；
3. 数字越界（如 `4`、`-1`）仍须报错；
4. **打印形态不变**（`llvm-mc -filetype=asm` / `llvm-objdump` 仍输出数字），故既有 `ASM:`/`OBJ:` lit 前缀不受影响。

> 方案备选（供参考，未采用）：仅做「非法 token 报错」而不接受 `wpN`（更小改动，但文档/注释里的 `wpN` 记法仍不可直接汇编）。

**确认记录（2026-09-22，用户）**：D1–D4 **逐条确认**。**ADR 判定**：D1 虽引入新的汇编器操作数语法（属工具链对外契约），但为**语法细节、可逆、非跨模块架构决策**，用户裁定**不生成 ADR**；理由记于此（对齐 `adr-authoring.md` 的判据）。

### 关键概念 / 数据

- rwii 格式：`hb{5:4}` = wyde-position（2 位）；`hb{3:0}:hc:hd` = immu16（`.tao/knowledge/contract-isa.md` §2.3/§2.4）
- 涉及指令（rwii 共 8 条）：`set.zw`/`set.ow`/`or.w`/`andn.w` × `-rd`/`-rb`
- 实现位置：
  - `llvm/lib/Target/DADAO/DADAOInstrInfo.td` 的 `def wydepos : Operand<i64>`（`ParserMatchClass = DADAOImmAsmOperand`）
  - AsmParser（`DADAOAsmParser.cpp`，`LLVM-006t` 产出）中的操作数解析路径
- **CodeEmitter 不受影响**：`getMachineOpValue()` 处理的是**已解析的整数**，本任务只改 **parser**

## 交付物

- 新补丁 `components/llvm-project/patches/0007-wyde-position-operand-parser.patch` + `series` 追加
- 新增 lit 用例（`tests/lit/MC/Dadao/`，例如 `wpn_operand.s`）：
  - `wp0`–`wp3` 各编码正确（`OBJ:` 字节级断言）
  - 数字 `0`–`3` 仍正确（不回归）
  - 非法 token（`wp4`/`foo`）→ **报错**（用 `not %llvm_mc ...` 断言失败）
- 完成区附全链路真实输出

## 已知坑 / 结论

1. **不要改打印形态**：现有 17 个 lit 用例的 `ASM:` 前缀依赖数字打印（如 `set.zw rb1, 2, 65535`）；若改为打印 `wp2` 会大面积回归。
2. **CodeEmitter 不动**：只改 parser。
3. **反例门控**：新增 lit 必须能对「`wpN` 回归为静默 0」失败——即**回退修复后新增 lit 必须 FAIL**。
4. **补丁生成流程**：`.work/source/llvm-project` 树 amend 提交 → `git format-patch` 覆盖 `components/llvm-project/patches/NNNN-*.patch`；**不得手工追加 hunk**；校验：临时 worktree 依序 apply（`0001`→`0007`）干净 + 落地 tree 与源树 HEAD tree 一致。
5. **`make build-mc` 需重编**：改 TableGen/AsmParser 后须重建（`make build-mc`）。

## 参考

- `.tao/tasks/integ/INTEG-002t-MC-QEMU-E2E冒烟.md`（发现现场与完成区）
- `contracts/opcodes.yaml`（rwii 编码）、`.tao/knowledge/contract-isa.md` §2.3/§2.4
- `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td`（`wydepos` 定义）
- `.tao/knowledge/adr-0006-llvm-baseline.md`

## 验收标准

1. `set.zw rb1, wp2, 0xffff` → 编码 `4e06ffff`（`wp0`–`wp3` 全部正确）
2. 数字 `0`–`3` 的编码与修复前**一致**（不回归）
3. 非法 token（`wp4`/`foo`）→ `llvm-mc` **报错**且**不产生**输出文件
4. `make build-mc` PASS
5. `llvm-lit tests/lit/MC/Dadao/` 0 failures（原 17 个 + 新增）
6. `python3 tools/llvm/check_lit_bytes.py` exit 0（N > 0）
7. `python3 tools/llvm/test_encoding_oracle.py` 全 PASS
8. `python3 tools/llvm/validate_instrinfo.py`（若适用于本改动）PASS
9. **反例门控**：回退修复后新增 lit 必须 FAIL（给出真实输出 + 还原证据；还原须含**重建**）
10. 未修改 `tests/vectors/isa/*.yaml`；未改动既有 lit 用例的 `ASM:`/`OBJ:` 期望

## 完成区

**测试结果**：通过 21/21；失败 0

**修改文件**：
- `.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`：新增 `isWydePosImm()` 谓词（`DADAOOperand`）+ `parseWydePosToken()` 方法 + 修改 `parseOperand()` 调用链
- `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td`：新增 `DADAOWydePosAsmOperand`（`PredicateMethod = "isWydePosImm"`）；`wydepos` 改用此类
- `Makefile`：第 86 行 build-mc 目标追加 `not`（修复可复现性缺口）
- `components/llvm-project/patches/0007-wyde-position-operand-parser.patch`（新）
- `components/llvm-project/patches/series`（追加 `0007`）
- `tests/lit/MC/Dadao/lit.cfg.py`（追加 `%not` 替换）
- `tests/lit/MC/Dadao/wpn_operand.s`（新，12 条 OBJ/ASM 断言）
- `tests/lit/MC/Dadao/wpn_err_wp4.s`（新，wp4 报错验证）
- `tests/lit/MC/Dadao/wpn_err_foo.s`（新，foo 报错验证）
- `tests/lit/MC/Dadao/wpn_err_range.s`（新，数值越界报错验证）

**验收结果**：

1. **修复后编码**（wpN 与数字逐条一致）：
```
set.zw rb1, wp0, 0xffff → 4e 04 ff ff  (= set.zw rb1, 0, 0xffff)
set.zw rb1, wp1, 0xffff → 4e 05 ff ff  (= set.zw rb1, 1, 0xffff)
set.zw rb1, wp2, 0xffff → 4e 06 ff ff  (= set.zw rb1, 2, 0xffff)
set.zw rb1, wp3, 0xffff → 4e 07 ff ff  (= set.zw rb1, 3, 0xffff)
set.zw rb1, wp0, 0x00ff → 4e 04 00 ff  (= set.zw rb1, 0, 0x00ff)
set.zw rb1, wp1, 0x00ff → 4e 05 00 ff  (= set.zw rb1, 1, 0x00ff)
set.zw rb1, wp2, 0x00ff → 4e 06 00 ff  (= set.zw rb1, 2, 0x00ff)
set.zw rb1, wp3, 0x00ff → 4e 07 00 ff  (= set.zw rb1, 3, 0x00ff)
```

2. **数字 0-3 不回归**：修复前后编码逐条一致（见上）。

3. **非法 token 报错**：
```
# wp4:
/tmp/opencode/LLVM-013t/test_wp4.s:1:13: error: invalid wyde-position; expected wp0, wp1, wp2, or wp3
set.zw rb1, wp4, 0xffff
            ^
EXIT: 1
ls: cannot access '/tmp/opencode/LLVM-013t/test_wp4.o': No such file or directory

# foo:
/tmp/opencode/LLVM-013t/test_foo.s:1:13: error: invalid operand for instruction
set.zw rb1, foo, 0xffff
            ^
EXIT: 1
ls: cannot access '/tmp/opencode/LLVM-013t/test_foo.o': No such file or directory

# numeric 4:
/tmp/opencode/LLVM-013t/test_num4.s:1:13: error: invalid operand for instruction
set.zw rb1, 4, 0xffff
            ^
EXIT: 1
ls: cannot access '/tmp/opencode/LLVM-013t/test_num4.o': No such file or directory
```

4. **`make build-mc` PASS**：移走 `not` 后执行 ninja（同 Makefile 第 86 行命令），`[255/325] Linking CXX executable bin/not` 重建成功，最终 `[325/325]` 全部完成。
```
=== not removed ===
ls: cannot access '/mnt/tao/DADAO-v5/.work/build/llvm/bin/not': No such file or directory
=== ninja (same command as Makefile) ===
[255/325] Linking CXX executable bin/not
...
[325/325] Linking CXX static library lib/libLLVMDADAOCodeGen.a
=== not exists ===
-rwxrwxr-x 1 ubuntu ubuntu 19051944 Sep 22 07:37 /mnt/tao/DADAO-v5/.work/build/llvm/bin/not
```

5. **`llvm-lit` 0 failures**：
```
Testing Time: 0.08s
Total Discovered Tests: 21
  Passed: 21 (100.00%)
```

6. **`check_lit_bytes.py` exit 0**：
```
check_lit_bytes: 53 patterns OK
  (info: 44/53 masks cover op-field only)
```
注：此脚本是**结构门**（mask 仅覆盖 op 字段），对操作数位注入（如 `4e06`→`4e01`）仍 exit 0。wpN 语义正确性由独立推导 + FileCheck 字节断言承担，不依赖此脚本。

7. **`test_encoding_oracle.py` 全 PASS**：
```
Results: 68 passed, 0 failed out of 68 tests
All encoding tests passed!
```

8. **`validate_instrinfo.py` PASS**：
```
=== Result: 0 errors, 0 warnings ===
```

9. **`make check` PASS**：
```
spec drift check: PASS
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

10. **反例门控**（返工后重新确认）：
- **注入**：`sed` 将 `parseWydePosToken()` 函数体首行追加 `return false;`，`git diff --name-only` 非空（确认注入有效）。
- **FAIL 输出**（21 tests, 19 passed, 2 failed）：
```
FAIL: DADAO-MC :: wpn_operand.s (1 of 21)
  set.zw rb1, wp0, 0xffff → error: invalid operand for instruction
  set.zw rb1, wp1, 0xffff → error: invalid operand for instruction
  set.zw rb1, wp2, 0xffff → error: invalid operand for instruction
  set.zw rb1, wp3, 0xffff → error: invalid operand for instruction
  (同样 wp0-wp3 + 0x00ff 也报错，共 8 条)
FAIL: DADAO-MC :: wpn_err_wp4.s (20 of 21)
  wp4 不再走 wydepos 专有报错路径，FileCheck 匹配 "invalid wyde-position" 失败
Passed: 19 (90.48%)  Failed: 2 (9.52%)
```
- **还原**：`git checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp` + `ninja` 重建。
- **还原后 PASS**：21/21 tests passed (100.00%)。
- **还原证据**：源树 `git diff --stat` 为空，HEAD 仍为 `e23e76dfe`。

11. **未修改**：`tests/vectors/isa/*.yaml`（`git diff --stat` 为空）；既有 lit 的 `ASM:`/`OBJ:` 期望未改动（`rwii.s` 无 diff）。

**补丁生成验证**：
```
# 源树 commit:
e23e76dfe DADAO: Fix wyde-position operand parsing (wpN tokens)

# 临时 worktree apply（tree hash 一致）:
Current HEAD tree: a88a1a85b412d911b9a814edea743a9bfd1b99f2
After apply tree:  a88a1a85b412d911b9a814edea743a9bfd1b99f2
PASS: tree hashes match
```

**series 内容**：
```
0001-dadao-triple-registration.patch
0002-dadao-target-skeleton.patch
0003-dadao-register-info.patch
0004-dadao-instrinfo.patch
0005-dadao-asmparser.patch
0006-dadao-disassembler.patch
0007-wyde-position-operand-parser.patch
```

**新发现/坑**：
1. `DADAOWydePosAsmOperand` 的 `PredicateMethod` 调用在 `DADAOOperand` 实例上（非 `DADAOAsmParser`），故 `isWydePosImm()` 必须放在 `DADAOOperand` 类内。
2. `DiagnosticPredicate` 只有 `isMatch()` / `isNearMatch()` 两态，无显式 "reject" 路径——`isNearMatch()` → `Match_InvalidImmediate`（带 `DiagnosticType`），`!isMatch() && !isNearMatch()` → `Match_InvalidOperand`（通用错误）。
3. `foo` 作为非 `wp` 前缀标识符，走 `parseImmediate()` → `MCExpr`（未定义符号）→ `isWydePosImm()` 拒绝 → `Match_InvalidOperand`（通用错误，非 wydepos 专有消息）。这是 LLVM 标准行为。
4. `not` 工具**必须**纳入 `make build-mc` 构建目标（已修复：`Makefile` 第 86 行追加 `not`）。此前靠手动 `cmake --build . --target not` 规避，干净构建下 `wpn_err_*.s` 必失败（Exit 127）。
5. `git apply --check` 对已 apply 的 patch 会报错（预期），正确验证方法是 reset → apply → 比较 tree hash。
6. `check_lit_bytes.py` 是**结构门**（mask 仅覆盖 op 字段），对操作数位注入仍 exit 0。wpN 语义正确性由独立推导 + `FileCheck` 字节断言承担。

**遗留问题**：无（`not` 构建缺口已在本轮修复）

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-22）

**判决：Needs Revision**（功能实现正确，但存在**可复现性阻断缺口**：`not` 未入 `make build-mc` 构建目标，干净构建下 2/21 lit 失败）

#### 1. 独立重跑记录（全部为 reviewer 亲自执行）

| 命令 | 退出码 | 真实输出（摘要） |
|---|---|---|
| `make build-mc` | **0** | 首次 `[1141/1141]` 全量重建 + `build-mc: PASS`；二次 `ninja: no work to do.` + `build-mc: PASS` |
| `llvm-lit tests/lit/MC/Dadao/ -v` | **0** | `Passed: 21 (100.00%)` |
| `python3 tools/llvm/check_lit_bytes.py` | **0** | `check_lit_bytes: 53 patterns OK` / `(info: 44/53 masks cover op-field only)` |
| `python3 tools/llvm/test_encoding_oracle.py` | **0** | `Results: 68 passed, 0 failed out of 68 tests` |
| `python3 tools/llvm/validate_instrinfo.py` | **0** | `=== Result: 0 errors, 0 warnings ===` |
| `make check` | **0** | `repository checks: PASS` |

#### 2. 独立推导编码（不采信 engineer / lit 期望）

按 `contracts/opcodes.yaml` `set.zw-rb`（op=0x4E, mask=0xFF000000；`rbha[23:18]`、`wpN[17:16]`、`immu16_hi[15:12]`、`mid[11:6]`、`lo[5:0]`）+ `contract-isa.md §2.3/§2.4` 手算
`word=(0x4E<<24)|(rbha<<18)|(wp<<16)|(hi<<12)|(mid<<6)|lo`：

```
wp0/num0 0xffff -> 0x4E04FFFF  4e 04 ff ff
wp1/num1 0xffff -> 0x4E05FFFF  4e 05 ff ff
wp2/num2 0xffff -> 0x4E06FFFF  4e 06 ff ff   ← 任务验收 #1
wp3/num3 0xffff -> 0x4E07FFFF  4e 07 ff ff
wp0/num0 0x00ff -> 0x4E0400FF  4e 04 00 ff
wp1/num1 0x00ff -> 0x4E0500FF  4e 05 00 ff
wp2/num2 0x00ff -> 0x4E0600FF  4e 06 00 ff
wp3/num3 0x00ff -> 0x4E0700FF  4e 07 00 ff
```

- 与 `llvm-mc`+`llvm-objdump` **实测 16/16 字节逐条一致**（`.work/log/llvm/LLVM-013t-review-r1-derive.log`）。
- 与 `wpn_operand.s` 内 **12 条 `# OBJ:` 期望逐条一致**（`.work/log/llvm/LLVM-013t-review-r1-lit-expect.log`）→ 非「lit 期望与实现同源同错」。
- 额外核验全部 rwii 形式（`set.zw rd/rb`、`set.ow rd`、`or.w rd/rb`、`andn.w rd/rb`）：`wpN` 与数字 `N` 字节**完全相同**（见 `rwii_all.s` 实测）。

#### 3. D4 打印形态未变

`llvm-mc -filetype=asm` 对 wpN 源码仍打印**数字**（`set.zw rb1, 2, 65535`），无一处 `wp`。`git diff --stat` 显示 `tests/lit/MC/Dadao/` 仅 `lit.cfg.py` 被改；既有 17 个 `.s` **逐字未动**（`.work/log/llvm/LLVM-013t-review-r1-asm-print.log`）。

#### 4. 反例门控（reviewer 亲自注入，均给出真实 FAIL + 还原证据）

| 注入 | 改动 | FAIL 证据（真实） | 还原证据 |
|---|---|---|---|
| 1 禁用 wpN 解析 | `parseWydePosToken` 首行 `return false` | `wpn_operand.s` FAIL（8 条 wpN 报 `invalid operand for instruction`）+ `wpn_err_wp4.s` FAIL | `git diff --name-only` 空 → `ninja` 重建 → **21/21** |
| 2 映射改错 wp2→1 | `createImm(N==2?1:N,...)` | `wpn_operand.s` FAIL（objdump 实出 `4e 05` 而期望 `4e 06`；Exit Code 1） | 同上 → 21/21 |
| 3 非法 token 静默取 0 | 删 `Error(...)`，改 `N=0` | `wpn_err_wp4.s` FAIL（Exit Code 2，`not llvm-mc` 成功→FileCheck 空输入）；直接复现：wp4 → `4e04ffff`、mc 退出 0、**产出文件** | 同上 → 21/21 |

- 还原均为「源码 `git checkout` + ninja 重建」，源树 `git status --porcelain` 空、HEAD 仍为 `e23e76dfe`；还原后 lit 复现 21/21（`.work/log/llvm/LLVM-013t-review-r1-lit-restored.log`）。
- ⚠️ 注入 3 仅触发 `wpn_err_wp4.s`（`foo`/数字 4 走另一路径）；`wpn_err_range.s`/`wpn_err_foo.s` 在该注入下仍 PASS——其 FAIL 路径存在但由不同注入触发（说明见 §7 备注）。

#### 5. 补丁流程校验

- `0007` diff 正文与 `git diff 928089dd0..e23e76dfe` **逐字一致**（剥签名后 `diff` 为空）→ **无手工追加 hunk**。
- `series` 顺序 `0001…0007` 正确。
- 全新临时 worktree（base `6dfe1677a`）依序 `git am` 7 个补丁**全部 clean**；落地 tree = **`a88a1a85b412d911b9a814edea743a9bfd1b99f2`** = `.work/source/llvm-project` HEAD tree（**PASS: tree hashes match**，与 engineer 报告值一致）。
- 补丁内容与我重新 `git format-patch` 的结果仅**元数据行**有别（`From` 哈希因历史改动、`[PATCH n/6]` vs `[PATCH n/7]` 编号、签名），hunk 完全相同。

#### 6. ⚠️ `not` 缺口核实结论（**必须修**）

- `tests/lit/MC/Dadao/lit.cfg.py` 新增 `%not` → `<build>/bin/not`（绝对路径，不依赖 PATH）。
- `wpn_err_wp4.s`/`wpn_err_foo.s` 用 `%not` → **需要真实 `not` 二进制**；`wpn_err_range.s` 用**裸 `not`** → 由 lit 内建取反（`TestRunner.py` L314-328）处理，**不需要二进制**。
- `Makefile` 第 86 行 ninja 目标为 `llvm-mc llvm-objdump llvm-objcopy FileCheck LLVMDADAOCodeGen`，**未含 `not`**；全仓库无其它目标构建 `not`。
- **实测证据**：临时把 `.work/build/llvm/bin/not` 改名后
  - `wpn_err_foo.s` FAIL、`wpn_err_wp4.s` FAIL：`'/…/bin/not': command not found`（**Exit Code 127**）；
  - `wpn_err_range.s` 仍 PASS；
  - 结果 **19/21**（`.work/log/llvm/LLVM-013t-review-r1-lit-notmissing.log`）。
  - 还原：md5 `38e04c27e2…` 校验 OK + lit 复现 21/21。
- **结论**：此为**必须修**的可复现性缺陷。task 验收 #4（`make build-mc`）+ #5（lit 0 failures）合起来要求在**文档化构建流程**下绿；干净机器上 `make build-mc` 不产 `not` → 2/21 必失败。engineer 靠手动 `cmake --build . --target not` 拿到 21/21，属**规避**。先例：commit `539bb88`（INTEG-001k）正是把 `llvm-objcopy` 加进**同一行** ninja 目标，本任务应循此例。
- **修复建议**：`Makefile` 第 86 行改为
  `ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump llvm-objcopy FileCheck not LLVMDADAOCodeGen`
  并验证干净构建下 21/21。

#### 7. 逐条验收（1–10）

1. ✅ `wp2` → `4e 06 ff ff`，`wp0`–`wp3` 全对（独立推导一致）。
2. ✅ 数字 0–3 不回归，且与 wpN 字节相同。
3. ✅ `wp4`/`foo`/`4`/`-1` → 报错 exit 1 且**无输出文件**。
4. ✅ `make build-mc` PASS（EXIT=0）。
5. ❌/⚠️ **未达标**：engineer 环境下 21/21，但**干净 `make build-mc`** 下 `not` 缺失 → `wpn_err_wp4.s`/`wpn_err_foo.s` **FAIL（127）**，实为 19/21。
6. ✅ `check_lit_bytes` exit 0（53 patterns）。
7. ✅ `test_encoding_oracle` 68/68。
8. ✅ `validate_instrinfo` 0 errors。
9. ✅ 3 组注入均 FAIL + 还原重建后 21/21（见 §4）。
10. ✅ `tests/vectors/isa/*.yaml` 未改；既有 17 lit 期望逐字未改。

#### 8. 附加发现（非阻断，供参考）

- **验证脚本可失败性**：`check_lit_bytes.py` 对 opcode 注入（`4e`→`5e`）**能** exit 1；但对**操作数位**注入（`4e 06`→`4e 01`）**仍 exit 0**——因其 mask `0xFF000000` 仅盖 op 字段（脚本自身亦标注 `44/53 masks cover op-field only`）。故 #6 只是**结构门**，**不能**作为 wpN 语义证据；wpN 正确性由 §2 独立推导 + `wpn_operand.s` 的 FileCheck 字节断言承担。
- **lit 断言锚定偏弱**：`wpn_operand.s` 的 `# OBJ:` 未带地址锚，FileCheck 会向后搜索，注入 2 的失配在**下一处同模式**才暴露（最终仍 FAIL，但定位不直观）。可考虑给 OBJ 行加地址/顺序锚，非必须。
- `wpn_err_range.s` 用裸 `not`，与另两错误用例的 `%not` 不一致；修 #1 后建议统一为 `%not`。

#### 9. 完成区一致性核对

- 与真实输出**基本一致**：wpN/数字编码、错误消息、lit 21/21、53 patterns、68/68、0 errors 均可复现。
- **不一致/需订正**：
  - 「**遗留问题**：无」不实——`not` 构建缺口（其自身「新发现/坑 #4」已承认）是真实遗留项。
  - 「`make build-mc` PASS：ninja 增量构建 **13/13** targets OK」不可复现：reviewer 首跑 1141/1141、次跑 `ninja: no work to do`。应改为可复现表述。
  - 「新发现/坑 #4」把 `not` 描述为「需单独编译」并只做 `%not` 替换，**未把它纳入构建目标**，正是本次打回的根因。

#### 10. 精确修复清单（返工）

1. **【必须】** `Makefile` 第 86 行 ninja 目标追加 `not`（见 §6 建议命令）。
2. **【必须】** 用**干净构建**验证：`make build-mc` 后 `<build>/bin/not` 存在，`llvm-lit tests/lit/MC/Dadao/` = **21/21**；把该真实输出与命令写入完成区。
3. **【建议】** `wpn_err_range.s` 改用 `%not`，三错误用例一致。
4. **【必须】** 订正完成区：删除「遗留问题：无」，如实登记 `not` 构建依赖及其修复；把「13/13」改为可复现表述。
5. 返工后需重建并复跑本文件 §1 全部命令 + §4 注入门控（至少注入 1/3）。

### 第 2 轮 reviewer 验收（2026-09-22）

**判决：Accepted**

第 1 轮阻断项（`not` 未入 `make build-mc`）已修复并**独立复现因果链**；功能实现、全部验收命令、反例门控、补丁流程、无回归均复核通过。返工清单 5 项全部落实。

#### 1. Makefile 改动核实

- `git diff Makefile` 仅一行：第 86 行追加 `not` → `ninja -C $(LLVM_BUILD) llvm-mc llvm-objdump llvm-objcopy FileCheck not LLVMDADAOCodeGen`，**无其它副作用**。
- 3 个错误用例 `wpn_err_wp4.s`/`wpn_err_foo.s`/`wpn_err_range.s` 现均用 `%not`；`lit.cfg.py` 的 `%not` 仍指向 `<tools_dir>/not`（绝对路径）。

#### 2. 干净构建因果链（reviewer 亲自复现，未用 `--target not`）

```
$ md5sum .work/build/llvm/bin/not          # 38e04c27e2063d9a1acc22dbf72594e3
$ mv .work/build/llvm/bin/not /tmp/opencode/LLVM-013t/not.hidden
$ ls .work/build/llvm/bin/not
ls: cannot access .../bin/not: No such file or directory
$ make build-mc
[272/1539] Linking CXX executable bin/not
...
[1539/1539] Linking CXX executable bin/llvm-objdump
build-mc: PASS                              # EXIT=0
$ ls -la .work/build/llvm/bin/not
-rwxrwxr-x 1 ubuntu ubuntu 19051336 ... bin/not
$ llvm-lit tests/lit/MC/Dadao/ -v
Total Discovered Tests: 21
  Passed: 21 (100.00%)                      # EXIT=0
$ .work/build/llvm/bin/not true; echo $?   # 1
$ .work/build/llvm/bin/not false; echo $?  # 0
```

- **还原/清理**：隐藏副本 `not.hidden` 已删除；`bin/` 下仅 `not`（无备份残留）；重建后的 `not` 功能正常、lit 21/21。
- 说明：reviewer 经 `make build-mc` 触发 `not` 重建（`[272/1539]`，因 cmake 重配触发较多重建）；engineer 完成区记的是直接跑同款 ninja 的 `[255/325]`。**数量随环境不同**，但**关键事实一致：`not` 现由 `make build-mc` 构建**。

#### 3. 复跑命令（真实输出）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `llvm-lit tests/lit/MC/Dadao/ -v` | **0** | `Passed: 21 (100.00%)` |
| `check_lit_bytes.py` | **0** | `53 patterns OK` / `(info: 44/53 masks cover op-field only)` |
| `test_encoding_oracle.py` | **0** | `68 passed, 0 failed` |
| `validate_instrinfo.py` | **0** | `0 errors, 0 warnings` |
| `make check` | **0** | `spec drift check: PASS` / `66 open, 8 closed (0 blocking M1-gate: 0)` / `repository checks: PASS` |

（日志在 `.work/log/llvm/LLVM-013t-review2-*.log`）

#### 4. 反例门控（禁用 `wpN` 解析，第 2 轮复验）

- 注入：`parseWydePosToken` 首行 `return false;`；`git diff --name-only` = `.../DADAOAsmParser.cpp`（**非空，注入有效**）。
- 重建 `ninja llvm-mc` → `llvm-lit` **EXIT=1**：
  - `FAIL: wpn_operand.s`（8 条 wpN 报 `error: invalid operand for instruction`）
  - `FAIL: wpn_err_wp4.s`
  - `Passed: 19 (90.48%)  Failed: 2 (9.52%)`
- 还原：`git checkout -- .../DADAOAsmParser.cpp`（`git diff --name-only` 空）+ `ninja` 重建 → **21/21**；源树 `status` 空、HEAD 仍 `e23e76dfe`。
- 真实日志：`.work/log/llvm/LLVM-013t-review2-inject1.log` / `...-lit-restored.log`。

#### 5. 完成区一致性核对（逐条）

| 完成区条目 | 核对结果 |
|---|---|
| 修改文件含 `Makefile` 第 86 行追加 `not` | ✅ 属实（diff 一致） |
| 「4. `make build-mc` PASS」改为干净构建证据（`[255/325]`→`[325/325]`，`not` 重建） | ✅ 「13/13」已删除，改为体现 `not` 重建；⚠️ 其证据是**直接 ninja** 而非 `make build-mc`（reviewer 已用 `make build-mc` 补证，实质成立） |
| 「9. `make check` PASS」 | ✅ 新增，与实测一致 |
| `check_lit_bytes` 结构门说明 | ✅ 新增（正文 #6 注 + 坑 #6），与 reviewer 实测一致 |
| 坑 #4 `not` 缺口如实记录 | ✅ 改写为「必须纳入构建目标，已修复」 |
| 「遗留问题：无（`not` 构建缺口已在本轮修复）」 | ✅ 属实 |
| 「10. 反例门控」返工后确认 | ✅ 与 reviewer 复验一致（19/21 → 21/21） |

#### 6. 补丁流程 + 无回归

- `0007` diff 正文剥签名后与 `git diff 928089dd0..e23e76dfe` **逐字一致** → **无手工 hunk**；`series` `0001…0007` 正确。
- 全新 worktree（base `6dfe1677a`）依序 `git am` 7 补丁**全 clean**；落地 tree = **`a88a1a85b412d911b9a814edea743a9bfd1b99f2`** = 源树 HEAD tree（**PASS**, 第 2 轮重验一致）。
- `tests/vectors/` 无改动；`tests/lit/` 仅 `lit.cfg.py` 改动，既有 17 个 `.s`（含 `rwii.s` 的 `ASM:`/`OBJ:`）逐字未动（21 个 `.s` = 17+4）。

#### 7. 清理核实

- `.tao/logs/`（废弃目录）中 **LLVM-013t 第 1 轮日志（reviewer）已迁至 `.work/log/llvm/LLVM-013t-review-r1-*.log`**，本文件第 1 轮记录的引用路径已同步更新。
- `.tao/logs/` 仍余 2 个**非本任务**文件：`INTEG-002t-review-lit-e2e.log`、`INTEG-002t-review2-lit-e2e.log`（他任务 reviewer 产物，未擅动，供主会话处置）。
- `bin/not*` 无备份残留；`/tmp/opencode/LLVM-013t/` 无 `not.hidden` 残留。

#### 8. 残留缺陷 / 观察（均不阻断）

1. 完成区「4.」的干净构建证据用的是**直接 ninja**（同款命令），未用 `make build-mc`；reviewer 已用 `make build-mc` 独立补齐，因果成立。建议今后直接贴 `make build-mc` 输出。
2. 添加 `not` 后 `make build-mc` 的目标数量随构建环境浮动（reviewer `[272/1539]`/engineer `[255/325]`），完成区给出的是环境相关数字，非固定值。
3. 第 1 轮已登记的非阻断项（`check_lit_bytes` 结构门、`wpn_operand.s` OBJ 无地址锚）在完成区已如实说明，本任务不要求修。

---

## 验收结论（2026-09-22，主会话；reviewer 两轮独立验收）

**判决**：**Accepted**（第 1 轮 Needs Revision → 返工 → 第 2 轮 Accepted）。

**功能（reviewer 独立推导验证）**：`wp0`–`wp3` → `4e04ffff`/`4e05ffff`/`4e06ffff`/`4e07ffff`，与 `opcodes.yaml` + ISA §2.3/2.4 手算 **16/16 一致**；数字 `0`–`3` 不回归；非法 token（`wp4`/`foo`/`4`/`-1`）报错且不产出文件。**D1–D4 全部落实**（D4：打印形态未变，既有 17 个 lit 的 `ASM:`/`OBJ:` 期望逐字未动）。

**反例门控（reviewer 亲自注入）**：3 组（禁用 `wpN` 解析 / 映射改错 / 非法 token 复静默取 0）均产生真实 FAIL；还原（含**重建**）后 21/21。

**第 1 轮阻断项（已修复）**：`%not` 指向 `<build>/bin/not`，但 `Makefile` 第 86 行 ninja 目标未含 `not` ⇒ 干净构建下 **19/21** ✗。返工：第 86 行追加 `not`；reviewer **亲自复现**「移走 `not` → `make build-mc` → `[272/1539] Linking bin/not` → lit 21/21」因果链 ✓。

**命令核验（真实输出）**：`make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` **21/21**；`check_lit_bytes.py` **53 patterns OK**（44/53 mask 仅盖 op 字段 ⇒ 属**结构门**，不作语义证据）；`test_encoding_oracle.py` **68/68**；`validate_instrinfo.py` 0 errors；`make check` PASS。

**补丁流程**：`0007` 正文与源树 diff 逐字一致（无手工 hunk）；`series` `0001`…`0007`；临时 worktree `git am` 全 clean，落地 tree = `a88a1a85b412d911b9a814edea743a9bfd1b99f2` = 源树 HEAD tree ✓。

**结论**：置 `已验证`。
