# INFRA-021t: 门控收口（asm-prose strict + MC/E2E lit 接入 + 行内 span 评估）

**模块**：infra
**项目里程碑**：M2
**依赖**：`SPEC-076t`/`077t`/`078t`（检测器 + 文档迁移 0 基线）、`LLVM-024t`（注释符）
**ADR**：`ADR-0013`（D9 注释符）、`ADR-0017`
**状态**：已验证

## 目标

把新汇编格式相关工作**收口为永久门控**，补上此前的覆盖盲区。

## 交付物

1. **`check-asm-prose` 转严并接入 `make check`**：
   - 现 `check-asm-prose`（`SPEC-076t`）为 **report 模式**（exit 0）；基线已 = **0 违规** ⇒ 改为 **`--strict`**（有违规即非零），并加入 `check:` 依赖链 ✓。
2. **MC + E2E lit 接入 `make check`**（**新增覆盖**；当前 `make check` **完全不含 lit**）：
   - 新 target `check-lit`：`llvm-lit`（`.work/build/llvm/bin/llvm-lit`）跑 `tests/lit/MC/Dadao`（**22/22**）+ `tests/lit/E2E`（**3/3**）；
   - 依赖：MC 需 `llvm-mc`/`llvm-objdump`/`FileCheck`（`build-mc-lite` 足）；**E2E 需 `llvm-objcopy`（full `build-mc`）+ `qemu-system-dadao`（`build-qemu`）+ trampoline**（见 `tests/lit/E2E/lit.cfg.py` 的 `%qemu`/`%trampoline`/`%e2e_dir` 取法）；
   - 加入 `check:` 依赖链；**`llvm-lit` 缺失 ⇒ 明确报错**（不得静默跳过 ✗）。
3. **行内 code span 检测（评估）**：`SPEC-078t` F5 登记「检测器只扫围栏代码块、**不含行内 code span**」。
   - **评估**：是否可行/值得扩展 `check_asm_prose.py` 覆盖行内 span（注意误报风险：`rd8`/`cfx` 等词的普通提及）。
   - **二选一**并给依据：**(a)** 实现**保守版**（仅对能唯一识别为汇编的行内 span 检测；须反例证明可失败且不误报）；**(b)** 登记 `deferred.md`（说明风险/成本）。
4. **`deferred.md` 收口**：登记本工作流的遗留（如行内 span 若选 (b)、LLVM MC cfx 实现 M2、`#` 行首 `AllowAdditionalComments` 等）。

## 验收标准（须真实可失败）

1. **`make check` EXIT=0**，含新 `check-asm-prose`（strict）与 `check-lit`；且**既有 target 判定未弱化** ✗。
2. **承重反例（你亲自注入 + 复原）** ⚠️：
   - A：向 `docs/spec/assembly-language.md` 或某 spec prose 注入一行旧格式 ⇒ `check-asm-prose` **非零**；
   - B：向 `tests/lit/MC/Dadao/*.s` 或 `tests/lit/E2E/*.s` 注入错误（如改一条期望字节 / 把新格式改旧）⇒ `check-lit` **非零**；
   - 复原 byte-identical；退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）。
3. **lit 真实通过**：`check-lit` 跑出 MC **22/22** + E2E **3/3** ✓（贴输出）。
4. **行内 span 处置**：选 (a) ⇒ 实现 + 反例（可失败、无误报）；选 (b) ⇒ `deferred.md` 有明确条目 + 依据 ✓。
5. **未越界**：`git diff --name-only` = `Makefile`（+ `tools/spec/check_asm_prose.py` 若选 3(a)）+ `tests/lit/**`/`tests/e2e/**`（若需）+ `.tao/knowledge/deferred.md` + 任务书；不改 `spec/` 正文、LLVM/QEMU、历史文件 ✓。
6. 命令缺失/失败 ⇒ 停下报告 ✗。

## 完成区

**测试结果**：通过 25/25（MC 22/22 + E2E 3/3）；`make check` 全绿（含新 `check-asm-prose` strict + `check-lit`）；既有 target 判定未弱化。
**修改文件**：`Makefile`、`.tao/knowledge/deferred.md`（+ 任务书自身）
**`make check` 真实退出码（含新 target）**：EXIT=0（repository checks: PASS）
**反例 A/B 真实输出与退出码 + 复原**：
- **反例 A**（`spec/SimRISC-05-64位地址运算.md` 注入 `# old comment format`）：
  ```
  check-asm-prose: 1 violation(s) found
  spec/SimRISC-05-64位地址运算.md:
    L39: [R4(#注释)] # old comment format
  EXIT=1
  ```
  复原：md5 `5acc785826e7b85ff1cddee55f486d2a`，注入前后一致；复原后 EXIT=0。
- **反例 B**（`tests/lit/MC/Dadao/basic-encoding.s` 改期望字节 `59 20 00 01` → `59 20 00 02`）：
  ```
  FAIL: DADAO-MC :: basic-encoding.s (1 of 1)
  basic-encoding.s:10:8: error: OBJ: expected string not found in input
  EXIT=1
  ```
  复原：md5 `6f6be7b35d95d2a2105f7093defc0b21`，注入前后一致；复原后 EXIT=0。
**lit MC/E2E 输出**：`-- Testing: 25 tests, 16 workers --`，25/25 Passed（100.00%），Testing Time: 0.08s。
**行内 span 处置（a/b）与依据**：选 **(b)** 登记 `deferred.md`。依据：(1) 行内 span 大量是寄存器名/格式名普通提及（`rd0`–`rd63`、`rrrr`、`add.uo`），不构成可检测的旧格式行；(2) 真正的行内汇编片段极少见且形态多样，误报率高；(3) 保守版匹配规则复杂脆弱；(4) 围栏块已覆盖绝大部分汇编示例。
**验收结果**：6 项验收标准全部满足——(1) `make check` EXIT=0 含新 target ✓；(2) 反例 A/B 注入→非零→复原 byte-identical ✓；(3) lit 25/25 ✓；(4) 行内 span 方案 b + deferred.md 条目 ✓；(5) `git diff --name-only` = `Makefile` + `deferred.md` + 任务书，未越界 ✓；(6) 无命令缺失/失败。
**新发现/坑**：无。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`Makefile` 改动（4 处）、`deferred.md` 新增 3 条、任务书完成区。

**逐行审查**：

1. **`.PHONY` 列表**：`check-asm-prose` 和 `check-lit` 已加入。✅
2. **Help 文本**：`check-asm-prose` 从 "report mode" 改为 "strict mode"；`check-lit` 新增一行。✅
3. **`check:` 依赖链**：`check-asm-prose` 插入在 `check-asm-list` 之后、`check-legality-drift` 之前；`check-lit` 追加在末尾（`check-dirs` 之后）。位置合理（lit 耗时最长放末尾，prose 检查快放前面）。✅
4. **`check-asm-prose` target**：加 `--strict`，注释更新。✅
5. **`check-lit` target**：
   - `LIT_BIN = $(LLVM_BUILD)/bin/llvm-lit`——复用既有 `LLVM_BUILD` 变量，不硬编码路径。✅
   - `@test -x $(LIT_BIN) || { echo "..."; exit 1; }`——缺失时报明确错误、非静默跳过。✅
   - `$(LIT_BIN) tests/lit/MC/Dadao tests/lit/E2E -v`——`-v` 提供详细输出。✅
   - 无 `@` 前缀（lit 输出直接显示）。✅
6. **`deferred.md` 新增条目**：行内 span（方案 b + 依据）、check-lit 接入、check-asm-prose 转严。格式与既有条目一致。✅
7. **未越界**：`git diff --name-only` = `Makefile` + `deferred.md`，未改 `spec/`、LLVM/QEMU、历史文件。✅

**finding 清单**：无。

**判决**：全部通过，可标「待验收」。
#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立验收，不采信完成区）
**证据目录**：`/tmp/opencode/INFRA-021t-r1/`
**审查基线**：`Makefile` md5 `2b17d8b62028aaeff2fafb327713d319`、`deferred.md` `69e27cd2c46741ff120621b33c55fd0c`；`git status --porcelain` = ` M Makefile` + ` M deferred.md` + `?? 任务书`。

##### 1. 重跑记录（真实命令 / 输出 / 退出码）

**(1) `make check` 全链**（`JOBS=8`）：
```
$ make check > make_check.log 2>&1; rc=$?; echo EXIT=$rc
EXIT=0
```
日志关键行（`/tmp/opencode/INFRA-021t-r1/make_check.log`）：
```
manifest validation: PASS
validate_vectors: 152/152 M1 identities covered OK
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check-asm-prose: PASS (0 violations)
check-legality-drift: 12 chapters OK
... INTEG-003t 总计: 80 项 | PASS: 80 | FAIL: 0
validate_encoding: 227 条记录 OK
check-rule-refs: PASS (规则 15 条: ...)
check-qemu-semantics: PASS  (Results: 146 total, 146 passed, 0 failed)
check-cfx-aliases: PASS (byte-identical)
check-dirs: PASS
-- Testing: 25 tests, 16 workers --
Total Discovered Tests: 25
  Passed: 25 (100.00%)
check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)
repository checks: PASS
```
MC `PASS: DADAO-MC` 计数 = **22**，E2E `PASS: DADAO-E2E` 计数 = **3**（`grep -c`），即 **25/25**。

**(2) 反例 A（注入 → 非零）**：向 `spec/SimRISC-05-64位地址运算.md` 第 38 行后（` ```simrisc ` 围栏内）插入旧格式 `ld.ub rd8, rb0, 4`：
```
$ python3 tools/spec/check_asm_prose.py --strict; echo EXIT=$?
check-asm-prose: 1 violation(s) found
spec/SimRISC-05-64位地址运算.md:
  L39: [R1(访存缺[])] ld.ub rd8, rb0, 4
EXIT=1
$ make check-asm-prose; echo EXIT=$?
EXIT=2        # make 将子进程 exit 1 报为 Error 1 → 非零
```
复原：md5 恢复 `5acc785826e7b85ff1cddee55f486d2a`、`diff -q` IDENTICAL、`git status --porcelain spec/` 空；复原后 `--strict` EXIT=0。

**(3) 反例 B（注入 → 非零）**：`tests/lit/MC/Dadao/basic-encoding.s` 期望字节 `59 20 00 01` → `59 20 00 02`（注入有效：`diff` 显示 L10 变更）：
```
$ make check-lit; echo EXIT=$?
Failed Tests (1):
  DADAO-MC :: basic-encoding.s
  Passed: 24 (96.00%)  Failed: 1 (4.00%)
EXIT=2
```
复原：md5 恢复 `6f6be7b35d95d2a2105f7093defc0b21`、`diff -q` IDENTICAL、`git status --porcelain tests/lit/` 空；复原后 `make check-lit` EXIT=0、25/25。

**(4) `llvm-lit` 守卫可失败**（不改仓库，用变量覆盖）：
```
$ make check-lit LLVM_BUILD=/tmp/.../no-such-llvm; echo EXIT=$?
check-lit: ERROR: /tmp/.../no-such-llvm/bin/llvm-lit not found — run 'make build-mc' first
EXIT=2
```
依赖（工具目录）缺失：`LLVM_TOOLS_DIR=<空目录> make check-lit` → 25 条 `command not found`（exit 127）→ `Failed: 25 (100.00%)`，EXIT=2——**明确失败、非静默跳过**。

##### 2. 约束核验（逐条）

| 任务约束 | 核验结果 |
|---|---|
| `check-asm-prose` 用 `--strict` | Makefile:251 `@$(PYTHON) tools/spec/check_asm_prose.py --strict` ✓ |
| 基线 0 违规 ⇒ `make check` 不因它失败 | `--strict` 直跑 EXIT=0；`make check` 中 `check-asm-prose: PASS (0 violations)` ✓ |
| `check-lit` 接入 `make check` | `check:` 依赖链含 `check-lit`（Makefile:212）✓ |
| MC 22/22 + E2E 3/3 = 25/25 | 实测 25/25（grep 计数 22+3）✓ |
| `llvm-lit` 缺失明确报错、不静默跳过 | 守卫 EXIT=2 + 明确 ERROR；依赖缺失 25 failed ✓ |
| 反例 A/B 可失败、复原 byte-identical、退出码非管道吞码 | 见上，均 EXIT=1/2；md5/diff 复原验证 ✓ |
| 行内 span 处置 (b) + `deferred.md` 条目 + 依据 | 条目存在；依据经抽查佐证 ✓（见下） |
| `make check` EXIT=0 | EXIT=0 ✓ |
| 既有 target 判定未弱化 | `git diff Makefile` 仅 5 处 hunk（`.PHONY`/help/`check:`/`check-asm-prose`/新增 `check-lit`），**未改任何既有 target 逻辑**；`check:` 旧 12 项全部保留、新增 2 项 ✓ |

##### 3. 行内 span（方案 b）依据佐证

`deferred.md` 新增条目存在（`行内 code span 检测（INFRA-021t 评估…方案 b）` 等）。理由抽查成立：
- spec/docs 行内 span 以**裸助记符/格式名**为主：`` `add.sb` ``(28+)`` `set.zw` ``(28)`` `st.o` ``(24)`` `ld.o` ``(24)`` `add.so` ``(11) 等（`grep -rhoE` 统计）。
- 若强行把这些 span 当行送入现有规则，会**大量误报**——实测把 span 内容喂给 `_check_line`：`` `ld.o`/`st.o`/`add.uo`/`cs.eq`/`set.zw`/`or.w`/`add.so` `` → `R6(操作数形态不符)`，`` `stm.o` `` → `R5(多寄存器缺{})`。即方案 (b)「误报率高、收益有限」结论有实证支撑。

##### 4. 完成区复读

- 25/25（MC 22 + E2E 3）、`-- Testing: 25 tests, 16 workers --`、Testing Time 0.08s：与实测一致 ✓
- `make check` EXIT=0（含新 target）、既有未弱化：一致 ✓
- 反例 A：文件 `spec/SimRISC-05-64位地址运算.md`、基线 md5 `5acc7858…`、EXIT=1：md5 与基线一致，非零结论可复现 ✓
- 反例 B：`basic-encoding.s`、`59 20 00 01→…02`、EXIT=1、md5 `6f6be7b3…`：一致 ✓
- 修改文件 = `Makefile` + `deferred.md` + 任务书（任务书为 untracked，故不出现在 `git diff --name-only`）：一致，`spec/` 正文/`components/`/历史文件无改动 ✓
- 「无命令缺失/失败」：本次验收环境下确实无缺失 ✓

##### 5. 判决

- **Accepted**。第 2 项（`check-asm-prose` strict 接入 + 基线 0 违规）与第 3 项（反例 A/B 承重）均经**本审查者独立注入 + 自取退出码 + byte-identical 复原**验证通过；`make check` EXIT=0、25/25、既有门控链完整未弱化、改动范围未越界。
- 说明：反例 B 仅做了 MC 侧（任务书中 E2E 侧为「亦可」可选项），MC 反例已证明 `check-lit` 门控承重。
- 未发现设计层/路线层阻断问题。

**建议主会话**：将任务状态置为 `已验证`。


#### 主会话收尾（2026-10-02）

1. **提交推送**：`Makefile`（`check-asm-prose --strict` + 新 `check-lit` 接入 `check:`）+ `deferred.md`（行内 span 等 3 条）（见 git log）。
2. **reviewer 第 1 轮 Accepted**：亲跑 `make check` EXIT=0、lit **25/25**；**独立注入**反例 A（prose 旧格式 ⇒ `check-asm-prose` EXIT=2）/ B（MC 期望字节改错 ⇒ `check-lit` EXIT=2）均承重 + byte-identical 复原；`llvm-lit` 缺失守卫可失败（无静默跳过）；行内 span 选 **(b)** 的依据经抽查成立；既有 12 门控**零修改**。
3. **收口**：新汇编格式工作流（`ADR-0013 D9` + `ADR-0017` + `LLVM-024t`/`SPEC-075t`/`076t`/`077t`/`078t`/`INFRA-021t`）**全部完成**。
