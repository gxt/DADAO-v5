# LLVM-022t: llvm 模块小修/lint（deferred 遗留）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

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