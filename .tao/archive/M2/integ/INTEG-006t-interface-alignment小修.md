# INTEG-006t: check_interface_alignment 两处缺陷

**模块**：integ
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述（来自 `deferred.md`）

1. **第三处调用的 `isdir` 守卫不一致**（`INTEG-005t` reviewer N3/C1）：`check_opcodes_cross()` 内为 `if os.path.isdir(qemu_patches_dir): for pf in iter_patch_files(...)`，而前两处（`check_elf_fields()`/`check_adr_alignment()`）**无守卫**、直接调用。后果：若 `components/qemu/patches/` 不存在，第三处**不**触发空集硬错误，而静默产出「期望 256 trans_*，实际 0」的误导 FAIL。建议：删 `isdir` 判断，交由 `iter_patch_files()` 统一处理（三处一致）。
2. **`_is_comment()` 只识别全行注释**（`LLVM-014t` reviewer 第 3 轮）：`_is_comment()` 只识别 `//`/`/*`/`*`/`*/` 开头的**全行**注释；**行尾注释 / 块注释中间行**内的误导文本仍可先于真实 call 命中 ⇒ **假绿**。建议：改读**真实产物**（`llvm-mc` + `llvm-readobj` 解析 `Flags`），或至少收紧 token 匹配（要求独占行/真实 call 形态）。

## 约束

- 只做上述 2 项；不改其他检查逻辑
- 逐条核对，禁止正则批量替换；命令缺失 → 停下报告
- 完成后 `make check` EXIT=0；`check_interface_alignment` 80/80

## 验收标准

1. 三处 `iter_patch_files()` 调用一致（无 `isdir` 守卫差异）；目录缺失时**统一硬错误**
2. `_is_comment` 假绿消除（行尾/块注释内的误导文本不再致假绿）；**反例**（构造行尾注释内含 `setELFHeaderEFlags(` 但无真实 call）→ 检查 FAIL
3. `check_interface_alignment` 80/80 EXIT=0；`make check` EXIT=0
4. 反例验证（两处各自可达 FAIL）

## 完成区

**测试结果**：check_interface_alignment 80/80 PASS，EXIT=0；make check EXIT=0

**修改文件**：`tools/integ/check_interface_alignment.py`（1 个文件，2 处改动）

**验收结果**：

```
$ python3 tools/integ/check_interface_alignment.py 2>&1; echo "EXIT=$?"
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
EXIT=0

$ make check 2>&1; echo "EXIT=$?"
repository checks: PASS
EXIT=0
```

**反例验证**：

- **反例 1（isdir 守卫）**：构造临时树缺少 `components/qemu/patches/`，`iter_patch_files()` 直接抛 `SystemExit` 硬错误（与前两处行为一致）。修复前 `isdir` 守卫会静默跳过，产出误导 FAIL。
- **反例 2a（行尾注释误命中）**：构造 patch 含 `+ int dummy = 0; // setELFHeaderEFlags(0x99)` + 真实调用。旧方法 `_is_comment()` 只判行首，regex 误命中注释中的 `0x99`（2 处命中）；新方法 `_strip_inline_comment()` 剥离行尾注释后仅命中真实调用（1 处命中）。
- **反例 2b（纯注释无真实调用）**：构造 patch 仅有 `+ int dummy = 0; // setELFHeaderEFlags(0x99)` 无真实调用。旧方法会误认为 `e_flags=153`（错值，FAIL 原因不准确）；新方法正确报告「未找到 getEFlags() 或 setELFHeaderEFlags()」。

**新发现/坑**：
- `_is_comment()` 的设计缺陷模式：只检查行首前缀无法处理行尾注释，这是 C/C++ source filter 的常见坑。`_strip_inline_comment()` 的字符级状态机是正确的通用解法，可复用于其他需要过滤注释的场景。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查内容**：逐行审查 `check_interface_alignment.py` 的两处改动。

**Finding 1**：`_strip_inline_comment()` 中转义字符处理——`c == "\\"` 在 Python 源码中是单个 `\` 字符，逻辑正确（匹配字符串字面量中的 `\` 转义）。复验：构造含 `\"` 的字符串测试，确认不误截断。

**Finding 2**：`_is_comment_line()` 重命名自 `_is_comment()`，函数体不变（行首去空白后以 `//`/`/*`/`*`/`*/` 开头），仅改名以区分职责（判纯注释行 vs 去行尾注释）。

**Finding 3**：`check_opcodes_cross()` 删除 `isdir` 守卫后，`iter_patch_files()` 的 `SystemExit` 会直接终止脚本，与 `check_elf_fields()`/`check_adr_alignment()` 行为一致。确认：`main()` 中四类检查依次调用，任一抛出 SystemExit 则整体终止（不会被静默吞掉）。

**判决**：全部 finding 无问题，实现与反例验证均通过。

#### 第 1 轮 reviewer 验收

**审查者独立重跑，未采信完成区转述。**

**1. 验收命令重跑（真实输出/退出码）**

```
$ python3 tools/integ/check_interface_alignment.py; echo EXIT=$?
...
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
  1.ELF: 5  2.ADR: 26  3.Schema: 41  4.Opcodes: 8
全部机械可判定项 PASS。
EXIT=0

$ make check; echo EXIT=$?
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 65 open, 9 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

（退出码用 `cmd > log 2>&1; rc=$?; echo EXIT=$rc` 捕获，非管道末端 `$?`。）

**2. 改动范围核对（`git diff`）**

- `tools/integ/check_interface_alignment.py`：**2 个 hunk**，只落在 `check_elf_fields()`（`_strip_inline_comment`/`_is_comment_line` 与 `code_lines` 构造）和 `check_opcodes_cross()`（删 `isdir` 守卫）——与任务「只做 2 项、不改其他检查」一致。
- 全文件无残留 `_is_comment(` 旧引用（`grep` 退出 1）。
- hunk 头均限于 `check_elf_fields`/`check_opcodes_cross`，未触及 `check_adr_alignment`/`check_schema_harness`。

**3. 反例 1（`isdir` 守卫一致性）——含新旧对照**

隔离树 `/tmp/opencode/INTEG-006t/`（脚本置于 `tools/integ/` 使 `REPO_ROOT` 指向临时树），直接调用 `check_opcodes_cross()`，`components/qemu/patches/` 缺失：

```
[NEW] SystemExit: ERROR: .../components/qemu/patches 下未找到任何 .patch 文件（空补丁集，无法校验）
[OLD] NO ERROR (静默返回)
      OLD: QEMU trans_* 定义数 FAIL — 期望 254 trans_*，实际 0
```

- `check_adr_alignment()` 同一条件下亦 `SystemExit`（同一 `iter_patch_files` 硬错误）。
- `check_elf_fields()`（llvm patches 空）亦 `SystemExit`。
- 三处调用（行 78 / 266 / 710）经 `grep` 确认**均无 `isdir` 守卫**，统一交由 `iter_patch_files()` 抛 `SystemExit`。行 690 的 `isdir(lit_dir)` 属另一 check，非本次三处调用，未改。

**4. 反例 2（`_is_comment` 假绿消除）——含新旧对照**

构造 patch（`components/llvm-project/patches/test.patch`），行尾注释含 `setELFHeaderEFlags(` token：

- **2a 假绿**：行尾注释 `// setELFHeaderEFlags(0x1)`（恰为期望值）+ 真实 call `setELFHeaderEFlags(0x2)`（错值）

  ```
  [OLD] e_flags PASS — setELFHeaderEFlags(0x1)          ← 假绿（命中注释，放过错值）
  [NEW] e_flags FAIL — setELFHeaderEFlags(0x2)，期望 0x1  ← 正确命中唯一真实 call
  ```
- **2b 纯注释无真实 call**：仅 `// setELFHeaderEFlags(0x99)`

  ```
  [OLD] FAIL — setELFHeaderEFlags(0x99)，期望 0x1（错值，FAIL 原因不准确）
  [NEW] FAIL — 未找到 getEFlags() 或 setELFHeaderEFlags()，默认为 0（原因准确）
  ```
- **边缘**：字符串字面量含 `//`（`"http://example.com/x"`）+ 真实 call → 未被误截断，仍命中 `EF_DADAO_ABIV1=0x1`。

**5. 约束逐条核验**

| 约束 | 结果 | 证据 |
|---|---|---|
| 只做 2 项、不改其他检查 | 通过 | diff 仅 2 hunk，落在两函数内 |
| 三处 `iter_patch_files()` 调用一致 | 通过 | grep 行 78/266/710 均无守卫 |
| 目录缺失统一硬错误 | 通过 | 三处直接调用均 `SystemExit` |
| 行尾注释 token 不再致假绿 | 通过 | 2a NEW FAIL / OLD PASS |
| 反例各自可达 FAIL | 通过 | 反例 1 SystemExit；反例 2 NEW FAIL |
| `check_interface_alignment` 80/80 EXIT=0 | 通过 | 真实重跑 80/80 EXIT=0 |
| `make check` EXIT=0 | 通过 | 真实重跑 EXIT=0 |
| 未凑绿/未弱化断言 | 通过 | 未改期望值、未改契约/spec |

**判决：Accepted**

理由：两条验收命令在审查者独立重跑下全部通过；两处缺陷的修复经反例（含旧代码对照）证明真实消除——旧代码确实存在「静默误导 FAIL」与「行尾注释致假绿」，新代码分别在两处转化为硬错误与准确 FAIL；改动范围严格限于 2 处，无越界、无凑绿。可交架构师终审。

**说明**：工作区另有 `tools/infra/`、`tools/llvm/`、`tools/qemu/`、`tools/testcases/` 等文件处于 M 状态，属其它并行小修任务，非本任务产出；INTEG-006t 对应 diff 仅为上述 1 文件 2 hunk。