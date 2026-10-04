# LLVM-022t: llvm 模块小修/lint（deferred 遗留）

**模块**：llvm
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述（来自 `deferred.md`）

llvm 模块的 4 项遗留（均非阻塞）：

1. **4 文件缺末尾换行**（`LLVM-004t` 交叉复核 F1）：`DADAOFrameLowering.{h,cpp}`、`DADAORegisterInfo.cpp`、`DADAOTargetMachine.h` 缺 POSIX 末尾换行（patch 内 4 处 `\ No newline at end of file`），其中 `DADAOTargetMachine.h` 是**回归**（`LLVM-003t` 原版有、被 `0003` 去掉）。
2. **`gen_asm_list.py` 默认输出覆盖已入库文件**（`QEMU-024t` 排查误触）：`--output` 默认 `docs/assembly-list.md`，`--plain` 无显式 `-o` 时**静默覆盖**已提交文件。建议：`--plain` 无 `-o` → stdout，或强制 `-o`。
3. **`check_lit_bytes.py` 两项增强**（`LLVM-012t` reviewer）：(a) 无 CLI（`LIT_DIR` 硬编码），建议加 `--lit-dir`；(b) 独立计数门控**不能捕获整行 `# OBJ:` 被删**（N 与计数同降仍相等），建议加「`# OBJ:` 行数 ≥ 基线下限」或与 `test_encoding_oracle.py` 用例数交叉。
4. **`test_encoding_oracle.py` 用例去重**（`LLVM-008t` reviewer）：`TESTS=57` 去重后仅 50（7 条重复登记）。建议按 `(asm 行, 期望 word)` 去重，并把「oracle 用例数 = lit `OBJ:` 行数」纳入一致性检查（可由 `check_lit_bytes` 承接）。

## 约束

- 只做上述 4 项；不改指令语义/编码
- 末尾换行须重建补丁（`git diff`，一文件一补丁）
- 逐条核对，禁止正则批量替换；命令缺失/构建失败 → 停下报告
- 完成后 `make check` EXIT=0；`make build-mc` 重跑一致

## 验收标准

1. 4 文件末尾换行修复（补丁内无 `\ No newline` 残留）
2. `gen_asm_list.py` 的 `--plain` 不再静默覆盖（无 `-o` 时 stdout 或报错）
3. `check_lit_bytes.py` 有 `--lit-dir` + OBJ 行数下限；反例（删一行 OBJ）能 FAIL
4. `test_encoding_oracle.py` 无重复用例；用例数与 lit OBJ 行数交叉一致
5. 补丁格式合规（每份恰 1 个 `diff --git`）；`make check` EXIT=0

## 完成区
**测试结果**：`make check` EXIT=0（全部通过）
**修改文件**：
- `tools/llvm/gen_asm_list.py`：`-o` 默认改 `None`；`--plain` 无 `-o` 输出 stdout
- `tools/llvm/check_lit_bytes.py`：加 `--lit-dir`（默认 `tests/lit/MC/Dadao`）+ `--min-obj N`（OBJ 行数下限）
- `tools/llvm/test_encoding_oracle.py`：去重7条重复用例（68→61）+ 交叉检查（oracle ≥ lit OBJ）
**验收结果**：
```
# check_lit_bytes.py
$ python3 tools/llvm/check_lit_bytes.py
check_lit_bytes: 53 patterns OK (info: 42/53 masks cover op-field only)

# --min-obj 反例（删1行 OBJ → FAIL）
$ python3 tools/llvm/check_lit_bytes.py --lit-dir /tmp/opencode/lit_test --min-obj 53
  N (52) < min-obj (53) — OBJ lines may have been deleted
EXIT=1

# gen_asm_list.py --plain 无 -o → stdout
$ python3 tools/llvm/gen_asm_list.py --plain --syntax old | head -3
// DADAO 指令清单（旧语法（当前已实现））
// 生成器：tools/llvm/gen_asm_list.py --plain --syntax old
// 来源：contracts/opcodes.yaml（254 条 = M1 177 + excluded_m1 77）

# test_encoding_oracle.py 去重
TESTS count: 61, Unique: 61, Remaining duplicates: 0

# 交叉检查
Oracle unique tests: 61, Lit OBJ lines: 53, Cross-check: PASS (61 >= 53)

# make check
$ make check
repository checks: PASS
```
**新发现/坑**：
- 项 #1（末尾换行）已被 `LLVM-021t`（commit `f791c5d`）修复（36 补丁重生成），无需再改
- `check_lit_bytes.py` 的 `independent_count`（宽松 `# OBJ:` 计数）与 `n_matched`（严格格式匹配）是两个不同维度：前者防格式遗漏，后者防编码不匹配；`--min-obj` 是第三维度防整行删除
- oracle 测试数（61）> lit OBJ 行数（53）是正常的——oracle 覆盖更多操作数组合和边界条件
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：3 个 Python 文件的改动（项 #1 已由 LLVM-021t 完成，无代码改动）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| gen_asm_list.py: `--plain` 无 `-o` 时 `args.output` 为 `None`，`Path(None)` 会报错 | ✅已修 | `--plain` 分支先检查 `args.output is not None`，否则 `sys.stdout.write` | `--plain` 输出到 stdout ✓，`-o /tmp/...` 写文件 ✓ |
| gen_asm_list.py: 非 `--plain` 无 `-o` 时也需默认路径 | ✅已修 | `out = Path(args.output) if args.output is not None else ROOT / "docs/assembly-list.md"` | 默认无参数运行输出到 `docs/assembly-list.md` ✓ |
| check_lit_bytes.py: `--min-obj` 与现有 `independent_count` 检查不冲突 | ✅确认 | 两个检查独立：`independent_count` 防格式遗漏，`--min-obj` 防整行删除 | `--min-obj53` 通过，`--min-obj54` 失败 ✓ |
| test_encoding_oracle.py: 去重后61条仍> lit OBJ 53条，交叉检查用 `>=` 而非 `=` | ✅确认 | oracle 覆盖更多操作数组合（如边界值、多格式变体），是超集关系 | `61 >=53` 通过 ✓ |
| test_encoding_oracle.py: 交叉检查仅在编码测试全通过后执行 | ✅确认 | 编码测试失败时 `sys.exit(1)` 已提前退出 | 逻辑正确 ✓ |

**判决**：所有 finding 已处置，可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查对象**：`tools/llvm/gen_asm_list.py`、`tools/llvm/check_lit_bytes.py`、`tools/llvm/test_encoding_oracle.py`（工作区 diff）+ `components/llvm-project/patches/`（项 #1，LLVM-021t 已提交）。
**审查者环境**：`export PATH="$PWD/.work/build/llvm/bin:$PATH"`；未安装/下载任何东西。

##### 1. 重跑记录（真实输出，照贴）

项 #1 末尾换行（补丁与已应用源树）：
```
$ grep -rlF '\ No newline at end of file' components/llvm-project/patches/        # 全 36 份补丁
（无输出）grep exit=1
$ for f in DADAOFrameLowering.h DADAOFrameLowering.cpp DADAORegisterInfo.cpp DADAOTargetMachine.h; do
    grep -c 'No newline' <patch>; done
0 / 0 / 0 / 0
$ tail -c1 <已应用源树 4 文件> | od -An -c
DADAOFrameLowering.h   -> \n
DADAOFrameLowering.cpp -> \n
DADAORegisterInfo.cpp  -> \n
DADAOTargetMachine.h   -> \n
$ 补丁格式：36 份补丁逐一核对 `grep -c '^diff --git'`，全部恰为 1
```

项 #2 `gen_asm_list.py`：
```
$ python3 tools/llvm/gen_asm_list.py --plain --syntax old > /tmp/.../plain_stdout.txt 2>stderr
EXIT=0
stdout head: // DADAO 指令清单（旧语法（当前已实现）） ...
stderr: gen-asm-list: 254 entries (old syntax) -> stdout
$ md5sum docs/assembly-list.md   # 运行前后
ed95b97bd673343572eba3433ee3fb8e  （前后一致，未被覆盖）
$ python3 tools/llvm/gen_asm_list.py --plain --syntax old -o /tmp/.../out.md   # EXIT=0，写入文件
$ python3 tools/llvm/gen_asm_list.py   # 非 plain 无参数：仍默认写 docs/assembly-list.md，EXIT=0，md5 不变
```

项 #3 `check_lit_bytes.py`：
```
$ python3 tools/llvm/check_lit_bytes.py
check_lit_bytes: 53 patterns OK
  (info: 42/53 masks cover op-field only)
EXIT=0
$ python3 tools/llvm/check_lit_bytes.py --min-obj 53     # 边界通过
EXIT=0
$ python3 tools/llvm/check_lit_bytes.py --min-obj 54     # 反例
  N (53) < min-obj (54) — OBJ lines may have been deleted
EXIT=1
$ # 反例：独立复制 lit 目录、删 1 行 `# OBJ:`（53→52）后加 --min-obj 53
$ python3 tools/llvm/check_lit_bytes.py --lit-dir /tmp/opencode/LLVM-022t/lit_noobj --min-obj 53
  N (52) < min-obj (53) — OBJ lines may have been deleted
EXIT=1
$ # 同一删除、不加 --min-obj（证明该门控正是捕获整行删除的维度）
$ python3 tools/llvm/check_lit_bytes.py --lit-dir /tmp/opencode/LLVM-022t/lit_noobj
check_lit_bytes: 52 patterns OK
EXIT=0
```

项 #4 `test_encoding_oracle.py`：
```
$ python3 tools/llvm/test_encoding_oracle.py
Results: 61 passed, 0 failed out of 61 tests
All encoding tests passed!
Cross-check OK: oracle tests (61) >= lit OBJ lines (53)
EXIT=0
# 独立用 exec 加载 HEAD 与工作区两版 TESTS，Counter 统计：
HEAD(orig): total=68 unique=61 dup_keys=7   （7 个 key 各出现 2 次）
WORK      : total=61 unique=61 dup_keys=0
# 交叉检查 FAIL 路径：把脚本复制到临时树、伪造 62 行 `# OBJ:`
$ python3 /tmp/opencode/LLVM-022t/oracle_cc/tools/llvm/test_encoding_oracle.py
All encoding tests passed!
CROSS-CHECK FAIL: oracle tests (61) < lit OBJ lines (62)
EXIT=1
```

通用：
```
$ make check
...
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 65 open, 9 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
$ make build-mc
ninja -C .work/build/llvm llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen
[8/8] Linking CXX executable bin/llvm-objdump
build-mc: PASS
EXIT=0
# build 后重跑，一致：
check_lit_bytes: 53 patterns OK  (EXIT=0)
Results: 61 passed, 0 failed out of 61 tests / Cross-check OK (61>=53)  (EXIT=0)
```

##### 2. 约束核验（逐条）

- 「只做 4 项；不改指令语义/编码」：diff 仅动 3 个 Python 文件（+98/−28），无 .td/.cpp 指令编码改动；`contracts/opcodes.yaml`、`tests/vectors/` 未改。**守住**。
- 「末尾换行须重建补丁（一文件一补丁）」：36 补丁全部恰 1 个 `^diff --git`；4 文件补丁及已应用源树末尾均为 `\n`，无 `\ No newline` 残留。**守住**（由 LLVM-021t f791c5d 完成）。
- 「逐条核对，禁止正则批量替换」：oracle 去重是逐行删除 7 条与已有项完全重复的登记（key 与 (asm,word) 均一致），非正则替换。**守住**。
- 「命令缺失/构建失败→停下报告」：无缺失，构建成功。**守住**。
- 「完成后 make check EXIT=0；make build-mc 重跑一致」：均已独立复现。**守住**。
- 「未误改其他内容」：`git status` 中 qemu/infra/integ/testcases 的改动分属其它并行任务（QEMU-027t/INFRA-017t/INTEG-006t/TESTCASES-018t），llvm 范围内仅本任务 3 个工具文件 + 任务书自身。**守住**。
- 验收标准逐条：①✗无残留 ②`--plain` 无 `-o`→stdout 且不覆盖 ③`--lit-dir`+`--min-obj` 齐备、反例 EXIT=1 ④无重复（0 dup）+交叉一致 ⑤补丁各 1 `diff --git`、`make check` EXIT=0。**全部满足**。

##### 3. 观察（非阻断）

- 项 #4 交叉检查用 `>=` 而非 `=`：oracle 合法覆盖更多操作数组合（61>53），用 `=` 会恒失败；`>=` 可捕获「oracle 用例被删到低于 lit OBJ 数」，符合 deferred 意图。engineer 已在完成区说明，**不判违规**。
- 真实输出与完成区逐条对齐（53/61/0/EXIT=0），无美化/摘要/估算。

##### 4. 反例与还原

- 反例（删 OBJ 行、`--min-obj` 过大、伪 lit 62 行触发交叉检查）均在 `/tmp/opencode/LLVM-022t/` 临时树操作，**未污染仓库**；操作后 `git status --porcelain -- tools/llvm` 仍仅 3 个任务文件。
- 项 #1 无代码改动，不涉及注入/还原。

##### 5. 判决

**Accepted**。验收命令块在审查者独立重跑下全部通过，硬约束逐条守住，反例均确认 FAIL 且已复原。请主会话将任务状态置为 `已验证`。