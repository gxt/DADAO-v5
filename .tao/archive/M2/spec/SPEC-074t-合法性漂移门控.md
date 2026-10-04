# SPEC-074t: `check-legality-drift` 漂移门控 + 接入 `make check`

**模块**：spec（`tools/spec/` + `Makefile`）
**项目里程碑**：M2
**依赖**：`SPEC-073t`（生成器 + 12 章生成区已定稿，`fe190e2`）；`SPEC-071t`（`check_rule_refs.py` 已有）
**状态**：已验证

## 目标

新增 `tools/spec/check_legality_drift.py`：把 `spec/SimRISC-01`~`SimRISC-12` 的 `<!-- LEGALITY_START/END -->` 生成区与**从 `contracts/` 实时重算的期望内容**逐字比对；不一致即**非零退出** ✓。并接入 `make check` 新增 `check-legality-drift` target。

## 判据（必须真实可失败）

1. **内容漂移**：对每章，用 `gen_legality_list.py` 的渲染逻辑（**复用**，勿重复实现 ✗）从 `contracts/legality_rules.yaml` + `contracts/opcodes.yaml`（`rule_refs`）+ `classify()` 计算期望区，与 spec 实际区**整段精确比对**；任一章不一致 ⇒ **EXIT=1** 并打印「章 + 首个不同行」✓。
2. **标记存在性**：`SimRISC-01`~`12` 各含**恰一份** `LEGALITY_START/END` ✓；**`SimRISC-00` 不得有** ✗。
3. **落点**：`LEGALITY_START` 必须紧跟对应章的 `<!-- ASSEMBLY_LIST_END -->` 之后 ✓。
4. **退出码必须携带信号** ⚠️：**不得**沿用 `gen_legality_list.py --verify` 的缺陷（其检出 MISMATCH 仍 `return 0` ✗）—— 本门控**任何**不一致都须 **EXIT=1** ✓；亦**不得**用子串判定（须整段精确比对 ✓）。
5. **不弱化既有门控** ✗：接入后 `make check` 各既有 target 判定逻辑不变 ✓。

## 接线

- `Makefile` 新增 `check-legality-drift` target，纳入 `check` 依赖链（建议紧随 `check-asm-list` 或 `check-rule-refs` 之后 ✓）。
- 与 `check_asm_list_consistency.py`（只管 `ASSEMBLY_LIST`）**隔离** ✓；不改其行为 ✗。

## 验收标准

1. 新脚本存在；正常仓库运行 **EXIT=0** ✓；`make check` **EXIT=0**（`check-asm-list`/`check-rule-refs`/`check-qemu-semantics` 146 例等全 PASS）✓。
2. **反例（须真实失败，逐条贴输出 + 退出码）** ⚠️：
   - A：手改某章 `LEGALITY` 区一行（如改规则 id 或删一行）⇒ **EXIT=1** ✓；
   - B：删除某章一个 `LEGALITY` 标记 ⇒ **EXIT=1** ✓；
   - C：给 `SimRISC-00` 加 `LEGALITY` 标记 ⇒ **EXIT=1** ✓；
   - D：把 `LEGALITY_START` 挪到 `ASSEMBLY_LIST_END` 之前（或远离）⇒ **EXIT=1** ✓。
   - 复原须 **byte-identical**（`git status`/`git diff` 核对 ✓），并给还原后 **EXIT=0** 证据 ✓。
3. **捕获退出码须正确** ⚠️：用 `cmd > log 2>&1; rc=$?`（**不得** `cmd | tail -1; echo $?` ✗）。
4. **未越界**：`git diff --name-only` = `Makefile` + `tools/spec/check_legality_drift.py`（新增，untracked）+ 任务书；**不改** 12 章生成区内容、不改 `gen_legality_list.py` 判定行为 ✗、不改历史文件 ✓。
5. 命令缺失/失败 ⇒ 停下报告 ✗。

## 完成区

**测试结果**：通过 12/12；`make check` 全部 146 例语义 + 80 项接口 + 编码/向量/规则引用/补丁/漂移/合法性全 PASS

**修改文件**：
- `Makefile`（新增 `check-legality-drift` target + `check` 依赖链接入）
- `tools/spec/check_legality_drift.py`（新增）

**反例 A/B/C/D 真实输出与退出码**：
- **A（内容漂移）**：`sed -i '/^\* \`dst_rd0\`/s/14 条/99 条/' spec/SimRISC-01-取数存数.md`
  ```
  FAIL: 取数存数 (SimRISC-01-取数存数.md): LEGALITY content drift (first diff at line 4, expected 19 lines, got 19 lines)
  1 violation(s) found, 11 OK
  EXIT=1
  ```
- **B（删除标记）**：`sed -i '/^<!-- LEGALITY_END -->$/d' spec/SimRISC-02-寄存器复制.md`
  ```
  FAIL: 寄存器复制 (SimRISC-02-寄存器复制.md): expected exactly 1 LEGALITY START+END pair, found START=1 END=0
  1 violation(s) found, 11 OK
  EXIT=1
  ```
- **C（SimRISC-00 加标记）**：`sed -i '1a<!-- LEGALITY_START -->\n<!-- LEGALITY_END -->' spec/SimRISC-00-指令系统设计.md`
  ```
  FAIL: SimRISC-00: forbidden LEGALITY markers found (START=1, END=1)
  1 violation(s) found, 12 OK
  EXIT=1
  ```
- **D（LEGALITY_START 挪到 ASSEMBLY_LIST_END 之前）**：把 LEGALITY 块移到 ASSEMBLY_LIST_END 之前
  ```
  FAIL: 16位立即数操作 (SimRISC-03-16位立即数操作.md): LEGALITY_START at line 23 is -10 lines after ASSEMBLY_LIST_END (line 33); expected 1-3
  1 violation(s) found, 12 OK
  EXIT=1
  ```

**复原证据**：`git checkout spec/SimRISC-01-取数存数.md && git checkout spec/SimRISC-02-寄存器复制.md && git checkout spec/SimRISC-00-指令系统设计.md && git checkout spec/SimRISC-03-16位立即数操作.md` 后 `git diff --name-only` = 仅 `Makefile`（已修改）；复原后 `make check-legality-drift` EXIT=0 ✓

**验收结果**：
- `python3 tools/spec/check_legality_drift.py` EXIT=0 ✓
- `make check-legality-drift` EXIT=0 ✓
- `make check` EXIT=0（146 例语义 PASS、80 项接口 PASS、编码 227 条 OK、向量 152 覆盖 OK、规则引用 PASS、补丁 67 条 OK、合法性 12 章 OK）✓
- `git diff --name-only` = `Makefile`（修改）+ `tools/spec/check_legality_drift.py`（新增 untracked）+ 任务书（untracked）✓

**新发现/坑**：
1. `gen_legality_list.py --verify` 的 `verify_legality()` 用 `expected_block in content`（子串匹配），且 MISMATCH 时仍 `return 0`。本门控用整段精确比对 + 强制 EXIT=1 来修正这两处缺陷。
2. `check_proximity` 需去掉 `break`，否则当 LEGALITY_START 在 ASSEMBLY_LIST_END 之前时，`asm_end_idx` 未赋值导致跳过检查。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审
- 自主逐行审查 `tools/spec/check_legality_drift.py`：
  - 逻辑正确性：`extract_block` 用精确 marker 行匹配 + 行拼接；`check_proximity` 已去掉 `break` 确保两个 index 都能找到；内容比对用 `==` 整段精确比较。
  - 设计/惯用法：复用 `gen_legality_list.py` 的渲染函数，不重复实现。
  - 防造假：反例 A/B/C/D 均真实执行并贴出完整输出+退出码。
  - 发现 1 个 bug（`check_proximity` 的 `break`）并已修复，修复后反例 D 通过。
  - 判决：全部 finding 已修，可标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| check_proximity 有 break 导致 LEGALITY_START 在 ASSEMBLY_LIST_END 之前时跳过检查 | ✅已修 | 去掉 for 循环中的 break | 反例 D 修复后 EXIT=1 ✓ |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，未采信完成区）
**证据目录**：`/tmp/opencode/SPEC-074t-r1/`

**审查的文件**：`tools/spec/check_legality_drift.py`（新）、`tools/spec/gen_legality_list.py`（对照）、`Makefile` diff、`spec/SimRISC-00..12`。

##### 重跑记录（均为我自己的真实输出/退出码）

基线（未注入）：
```
$ python3 tools/spec/check_legality_drift.py
check-legality-drift: 12 chapters OK
EXIT=0
$ make check-legality-drift
check-legality-drift: 12 chapters OK
EXIT=0
```

反例 A（手改 SimRISC-01 `dst_rd0` 行 `14 条`→`99 条`）：
```
FAIL: 取数存数 (SimRISC-01-取数存数.md): LEGALITY content drift (first diff at line 4, expected 19 lines, got 19 lines)

1 violation(s) found, 11 OK
EXIT=1
```
与完成区 A 逐字一致 ✓。`git checkout` 后 `sha256sum` = OK（byte-identical）。

反例 B（删 SimRISC-02 `LEGALITY_END`）：
```
FAIL: 寄存器复制 (SimRISC-02-寄存器复制.md): expected exactly 1 LEGALITY START+END pair, found START=1 END=0

1 violation(s) found, 11 OK
EXIT=1
```
与完成区 B 逐字一致 ✓。复原 sha OK。

反例 C（SimRISC-00 加 `LEGALITY_START/END`）：
```
FAIL: SimRISC-00: forbidden LEGALITY markers found (START=1, END=1)

1 violation(s) found, 12 OK
EXIT=1
```
与完成区 C 逐字一致 ✓。复原 sha OK。

反例 D（把 LEGALITY 块移到 `ASSEMBLY_LIST_END` 之前，SimRISC-03）：
```
FAIL: 16位立即数操作 (SimRISC-03-16位立即数操作.md): LEGALITY_START at line 23 is -9 lines after ASSEMBLY_LIST_END (line 32); expected 1-3

1 violation(s) found, 12 OK
EXIT=1
```
⚠️ 完成区 D 记的是 `-10 lines ... (line 33)`。差异来源：完成区未给出 D 的精确注入命令，其排布在块与 `ASM_END` 间多留了一空行，故偏移 -10/行 33；我的排布为 -9/行 32。**违反类型（LEGALITY_START 在 ASM_END 之前）与 EXIT=1 完全一致**，该输出可由合法注入自然产生，非美化/虚构，判为可复现。
补充 D' 变体（LEGALITY_START 远离 5 行，SimRISC-05）：
```
FAIL: 64位地址运算 (SimRISC-05-64位地址运算.md): LEGALITY_START at line 25 is 7 lines after ASSEMBLY_LIST_END (line 18); expected 1-3

1 violation(s) found, 12 OK
EXIT=1
```
「远离」同样被抓 ✓。

退出码捕获方式：全部用 `cmd >log 2>&1; rc=$?`，未用管道吞码 ✓。

##### 第 2 点（不复现 `--verify` 缺陷）——明确表态：**PASS**

1. 代码核对：`check_legality_drift.py` 的 MISMATCH 分支为
   `if actual_block != expected_block: errors.append(...)`，最终 `if errors: ... return 1`（第 168–175 行），**非** print 后 `return 0` ✓。
2. **整段精确比对**证明：在 SimRISC-04 的 `LEGALITY_END` 前插入一行（期望块仍为文件中一段连续子串），若为子串判定（`expected in content`）必漏报；实测：
   ```
   FAIL: 64位数据运算 (SimRISC-04-64位数据运算.md): LEGALITY content drift (first diff at line 7, expected 7 lines, got 8 lines)
   EXIT=1
   ```
   证明用的是整段精确 `!=` ✓。
3. 对照缺陷确实存在：`gen_legality_list.py --verify` 对同一漂移打印 `MISMATCH` 却 `EXIT=0`（`verify_legality` 用 `expected_block in content`，`main` 恒 `return 0`）：
   ```
   gen-legality: spec/SimRISC-01-取数存数.md MISMATCH
   EXIT=0
   ```
   同一漂移下新门控 `check_legality_drift EXIT=1` ✓。新门控未复现该缺陷。

##### 第 3 点（复用渲染逻辑）——PASS
`check_legality_drift.py` 直接 `from tools.spec.gen_legality_list import render_chapter_legality, build_chapter_entries, build_rule_to_chapters, build_rule_entries, classify, load_data, SECTION_ORDER, CLASS_TO_SPEC`，期望区由 `render_chapter_legality()` 生成，**未重复实现分类**（分类仍在 `tools/llvm/gen_asm_list.classify`，经 gen_legality_list 传递）✓。
（次要：`classify` 被 import 但本文件未直接调用，属无害未用导入，不影响 DRY/行为。）

##### 第 4 点（接线 + `make check`）——PASS
- `Makefile` 新增 target 并纳入 `check` 依赖链：`check: ... check-asm-list check-legality-drift check-interface validate-encoding check-rule-refs check-qemu-semantics`；`.PHONY` 与 `help` 同步 ✓。
- **既有 target 判定逻辑未弱化**：diff 仅 8+/2-，`check-asm-list`/`check-rule-refs`/`check-interface` 等 target 体与对应脚本**零改动**（`git status` 中无这些文件）✓。
- `make check` 亲自重跑：
  ```
  validate_vectors: 152/152 M1 identities covered OK
  check-patch-tree: 2 component(s), 67 patches OK
  check-asm-list-consistency: 12 spec files OK
  check-legality-drift: 12 chapters OK
  ...
  总计: 80 项 | PASS: 80 | FAIL: 0
  validate_encoding: 227 条记录 OK
  check-rule-refs: PASS
  Results: 146 total, 146 passed, 0 failed
  check-qemu-semantics: PASS
  check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)
  repository checks: PASS
  EXIT=0
  ```
  新门控确实在依赖链中执行（日志含 `check-legality-drift: 12 chapters OK`）✓。

##### 第 5 点（未越界）——PASS
`git status --short`：
```
 M Makefile
?? .tao/tasks/spec/SPEC-074t-合法性漂移门控.md
?? tools/spec/check_legality_drift.py
```
`git diff --name-only` = `Makefile`；`spec/` 无任何修改（13 个文件 `sha256sum -c` 全部 OK）；`gen_legality_list.py` 未改；无历史文件改动 ✓。

##### 第 6 点（完成区逐条复读）
A/B/C 与真实逐字一致；`make check` 各项计数（146/80/227/152/67/12 章）与我的日志一致；D 存在上述 off-by-one 说明（非功能性不符）。全部反例复原后 `sha256sum` 全部 OK，最终门控 `EXIT=0`。

##### 约束核验

| 约束 | 结果 |
|------|------|
| 门控真实可失败（我亲自注入 A/B/C/D） | ✓ 全部 EXIT=1 |
| 每例亲自确认退出码非 0（`cmd >log 2>&1; rc=$?`） | ✓ 未用管道吞码 |
| 复原 byte-identical（sha256） | ✓ 13 文件全 OK |
| MISMATCH 分支返回非零、非 print-then-0 | ✓ 明确 PASS |
| 整段精确比对、非子串 | ✓ 子串探针证明 |
| 复用 `gen_legality_list.py` 渲染、勿重实现分类 | ✓ PASS |
| `Makefile` 接线纳入 `check`、既有判定不弱化 | ✓ PASS |
| `make check` EXIT=0 | ✓ |
| 未越界（diff 范围） | ✓ |
| 完成区 A/B/C/D 与真实一致 | A/B/C ✓；D 类型一致、行号 off-by-one（已说明） |

##### 判决：**Accepted**

第 1 点（门控真实可失败）与第 2 点（不复现 `--verify` 缺陷）均明确 **PASS**。验收命令块在我独立重跑下全部通过，约束无违反。唯一附注为完成区反例 D 的行号 off-by-one（因注入排布留白差异，非功能不符、非虚构），不影响达标。

**阻断项**：无。可提交架构师终审。


#### 主会话收尾（2026-10-02）

1. **提交推送**：`check_legality_drift.py` + `check-legality-drift` 接入 `make check`（见 git log）。
2. **非阻断遗留**（登记）：
   - `gen_legality_list.py --verify` 检出 MISMATCH 仍 `return 0`（旧缺陷）⇒ 现由 `check-legality-drift`（真失败）承担；`--verify` 本身是否顺带修，留后续（可选）。
   - 完成区反例 D 的行号 `-10/line 33` 与 reviewer 复现 `-9/line 32` 差 1（完成区未列精确注入命令）⇒ 非虚构，属留白差异。
3. **M2 合法性清单线收口**：`SPEC-070t`(规则整合) → `071t`(rule_refs+双向门控) → `073t`(生成器+注入) → `074t`(drift 门控) 全部 Accepted。
