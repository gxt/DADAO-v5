# LLVM-046t: InstrInfo 生成器/校验器刷新（陈旧、非真源）

**模块**：llvm
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（**无需**组件重建：纯 Python 工具刷新）

## 目标与 resolved_by

处理 1 条无依赖的 LLVM 工具债 issue（纯 Python，改动不参与 LLVM 编译）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-103 | `tools/llvm/generate_instrinfo.py` / `validate_instrinfo.py` 陈旧、非真源（命名漂移 + 基线过期，`EXIT≠0`，均不在 `make check`） |

`resolved_by`：本任务 `LLVM-046t`。

## 接口规范

- **输入**（已核实）：
  - `tools/llvm/validate_instrinfo.py` 头注释：`1. 178 M1 instruction defs exist (no more, no fewer)`；Check 2 命名漂移（`.td` 用 `.` vs `opcodes.yaml` 用 `_`）。
  - 真源变化：`contracts/opcodes.yaml` 现 **228** 条（`scope: m1` = 152；`fp` 60；`excluded` 15；`m3` 1）；`DADAOInstrInfo.td` + `DADAOInstrInfoFP.td` 现状。
  - 两脚本**均不在** `make check`（`Makefile:224`）。
- **输出**：二选一并执行——
  - **(a) 刷新**：修正命名映射、基线数字；脚本运行 `EXIT=0`；并评估是否接入 `make check`（若接入，须满足可失败门控）；或
  - **(b) 退役**：若判定已被 `generate_opcodes.py` / `validate_encoding.py` / lit 取代，**删除或明确标注为历史脚本**（加 deprecation 头、从 `tools/` 移出或加 guard），并给出理由与替代真源。
- **约束**：
  - **不得**用脚本反推真源；脚本以 `contracts/opcodes.yaml` + `.td` 为真源。
  - 若选择刷新，改动须能对**注入的 .td/opcodes 不一致**失败（见验收 3）。
  - 生成器产物（若脚本产出文件被提交）须随产物保留在非易失位置。

## 验收标准

1. **基线一致**：选择 (a) 时，`python3 tools/llvm/validate_instrinfo.py` **EXIT=0**，且其声明的 M1 def 数与 `grep -c '^- id:' contracts/opcodes.yaml` 的 `scope: m1` 子集一致（给出两命令输出，不再出现 178 类的过期硬编码，或明确由 opcodes.yaml 派生）。
2. **命名对齐**：Check 2 的 `.td`（`.`）与 `opcodes.yaml`（`_`）映射显式定义并有测试；对合法输入 EXIT=0。
3. **反例门控**：在临时副本把某条 `.td`/`opcodes.yaml` 的 mnemonic/op 改错 → 校验器 **EXIT≠0**；还原 → EXIT=0。给出真实输出。
4. **选择 (b)** 时：给出「被谁取代」的逐项对照（`validate_encoding.py` / `generate_opcodes.py` / lit 覆盖点），并确认删除/标注后 `make check` 不回归。
5. `make check` EXIT=0（含新增门控则须全绿）。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-046t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/llvm/LLVM-046t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-046t/`，可复用检查器落 `tools/llvm/`。

## 完成区

**结论**：混合处置——**校验器按 (a) 刷新**（它仍提供 lit/oracle 未覆盖的、免构建的 `.td`↔`opcodes.yaml` 静态交叉检查，且验收 §2/§3 要求其存在并失败），**生成器按 (b) 退役**（其无法再生 committed `.td`：def 名是 CodeGen API，由旧手工 `insn` 字段派生，无法由新 `id` 反推；误运行会把真源覆盖为错名，故加 deprecation 头 + guard）。

**测试结果**：
- `python3 tools/llvm/validate_instrinfo.py` → **EXIT=0**；`M1 records=152`（由 `opcodes.yaml` `scope:m1` **派生**，无硬编码 178/152）；`matched 152/152`；`.td instr defs=154`（152 m1 + 1 m3 `sub_o_dbb` + 1 excluded `fence`）；6 项检查全 PASS。
- `python3 tools/llvm/validate_instrinfo.py --self-test` → **EXIT=0**（5 条显式 id→def 映射样本 PASS）。
- `python3 tools/llvm/generate_instrinfo.py` → **EXIT=2**，stderr 打印 DEPRECATED（拒绝运行，不触碰 `.td`）。
- 反例门控（见下）：`.td` mnemonic 漂移 → **EXIT=1**；`opcodes.yaml` op 漂移 → **EXIT=1**；还原 → **EXIT=0**。
- `make check-instrinfo` → **EXIT=0**；`make check` → **EXIT=0**（lit 33/33，`repository checks: PASS`）。
- `.work/evidence/LLVM-046t/run.sh` → **EXIT=0**（12/12 PASS，含注入→FAIL→还原→回绿）。

**修改文件**：
- `tools/llvm/validate_instrinfo.py`（刷新：`(mnemonic,format,op,ha)` 显式 join、派生基线、非 m1 allow-list、`--self-test`/`--dump-map`、默认读 committed patch 免依赖 `.work/source`）
- `tools/llvm/generate_instrinfo.py`（退役：deprecation 头 + `main()` guard，历史实现保留供溯源）
- `Makefile`（新增 `check-instrinfo` target 并并入 `make check` 链）
- 非入库产物：`.work/evidence/LLVM-046t/run.sh`、`.work/log/llvm/LLVM-046t-*.log`

**验收结果**（真实输出摘要，完整日志见 `.work/log/llvm/`）：
```
$ python3 tools/llvm/validate_instrinfo.py ; echo EXIT=$?
=== Validation: DADAOInstrInfo.td vs contracts/opcodes.yaml ===
opcodes.yaml     : /mnt/tao/DADAO-v5/contracts/opcodes.yaml
instruction defs : /mnt/tao/DADAO-v5/components/.../DADAOInstrInfo.td.patch
records total    : 228
M1 records       : 152  (baseline derived from opcodes.yaml)
M3 records       : 1
.td instr defs   : 154
PASS: mapping — join key (mnemonic, format, op, ha) 在两侧均唯一
PASS: baseline — 152/152 条 M1 记录各有唯一 .td def
PASS: coverage — 1/1 条 M3 记录各有唯一 .td def
PASS: orphan — 全部 154 个 .td def 各有唯一 opcodes 记录
PASS: non-m1 — 2 个非 m1 def 均在 allow-list（[('sub_o_dbb', 'm3'), ('fence', 'excluded')]）
PASS: format — m1 def 格式类集合 == M1 记录格式集合: [...]
=== Result: 0 errors ===
EXIT=0

$ grep -c '^- id:' contracts/opcodes.yaml           # 228（全部）
$ python3 -c '...scope==m1...'                        # 152（m1 子集，与上面 M1 records 一致）

$ python3 tools/llvm/generate_instrinfo.py ; echo EXIT=$?
DEPRECATED: tools/llvm/generate_instrinfo.py is retired (ISS-103, LLVM-046t).
...
EXIT=2

$ make check ; echo EXIT=$?
Total Discovered Tests: 33
  Passed: 33 (100.00%)
repository checks: PASS
EXIT=0
```
反例门控（`.work/evidence/LLVM-046t/run.sh`，真实输出）：
```
PASS  5. inject .td mnemonic -> FAIL   expected=diff!=0 & exit!=0  actual=diff=1 exit=1 exit=0
PASS  5b. restore .td -> green         expected=exit 0            actual=exit 0 exit=0
PASS  6. inject opcodes op -> FAIL     expected=diff!=0 & exit!=0  actual=diff=1 exit=1 exit=0
PASS  6b. restore opcodes -> green     expected=exit 0            actual=exit 0 exit=0
ALL CHECKS PASSED
```
注入失败原因（真实 stderr）：`M1 记录 ld.ub_rrii_rd 的 .td def 数 = 0` + `.td def ld_ub_rd 无唯一 opcodes 记录`（`.td` 侧改 `"ld.ub"`→`"ld.ux"`）；opcodes 侧改 `op` `0x10`→`0x1A` 同理。

**(b) 退役项「被谁取代」逐项对照**：
| 原脚本能力 | 取代者（真源/门控） |
|---|---|
| `generate_instrinfo.py` 生成 `DADAOInstrInfo.td` | `.td` 真源 = committed patch `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（人工维护，def 名是 CodeGen API，不可由 id 派生）；端到端正确性由 `make check-lit`（33/33）+ `tools/llvm/test_encoding_oracle.py`（**122** 独立重算）把关 |
| （生成 `opcodes.yaml`） | `tools/spec/generate_opcodes.py`（真源生成器） |
| （`opcodes.yaml` 结构校验） | `tools/spec/validate_encoding.py`（`make validate-encoding`） |
| `.td` ↔ `opcodes.yaml` 交叉校验 | **本任务刷新的** `tools/llvm/validate_instrinfo.py`（`make check-instrinfo`，已并入 `make check`） |

退役后 `make check` **不回归**：`make check` EXIT=0（generator 仅被 `compileall` 编译，不被执行；guard 保证不误写 `.td`）。

**新发现/坑**：
1. **def 名不可由新 `id` 反推**：`.td` 的 legacy def 名（`ld_ub_rd`、`rb2rb`、`add_o_bbd` 等）源自旧 `insn` 字段（`ld.ub-rd`，手工命名），且被 CodeGen 直接引用（`DADAOInstrInfo.cpp`：`DADAO::rb2rb`/`rd2rd`/`rd2rb`/`rb2rd`）。故 SPEC-019t（`insn`→`id`）后生成器/校验器的机械改名（`op["insn"]`→`op["id"]`，commit 0847713）造成命名漂移，且生成器**无法**刷新为再生——改名会破坏 CodeGen（需组件重建）。这直接决定了对生成器选 (b)。
2. **`.td` 现含 2 个非 m1 def**：`sub_o_dbb`（`sub.o_orrr_dbb`，`scope:m3`，ADR-0012 D9.1）、`fence`（`fence_oiii_imm`，`scope:excluded`，SPEC-039t 移出 M1 但 llvm-mc 仍需，见 `tests/lit/MC/Dadao/oiii.s`）。旧校验器的「178 基线」与「no excluded defs」均已过期。故新校验器以 `scope` + 显式 allow-list 表达策略。
3. **另一处陈旧工具（不在本任务范围）**：`tools/llvm/gen_m1_asm.py` + `tools/llvm/test_m1_asm.py` 仍生成旧 `i` 后缀语法（`24i`/`2i`/`4i`，已被 LLVM-026t 去除）→ 实测 `test_m1_asm.py` **148/152**（4 失败：jump/call）。建议另立 issue/任务（与 ISS-103 同族）。
4. `make check` 新门控 `check-instrinfo` 读 **committed patch**（仓库内文件）而非 `.work/source`，故为 hermetic、可在未 `make prepare` 的环境跑（与多数 `make check` 检查一致）。

**遗留问题**：
- **`.td` 头注释与事实不符**：其头部仍写 "Auto-generated from contracts/opcodes.yaml by tools/llvm/generate_instrinfo.py. DO NOT EDIT MANUALLY."，但生成器已退役、`.td` 现为人工维护真源。订正需改 `components/**`（补丁导出，可能触发组件重建），**超出本「纯 Python 工具刷新」任务范围** → 建议后续任务（如 LLVM-0xx）一并订正。
- **`gen_m1_asm.py`/`test_m1_asm.py` 陈旧**（新发现 3），未处理。
- 未提交 git（待用户确认）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/llvm/validate_instrinfo.py`（全文重写）、`tools/llvm/generate_instrinfo.py`（头 + guard）、`Makefile`（+target/链）、`.work/evidence/LLVM-046t/run.sh`（全文）。逐行核对逻辑/边界/防造假。

**核验要点**：
- Join key `(mnemonic,format,op,ha)` 在两侧唯一（228 记录 / 154 def 均无重复）——已由 Check 4 运行输出证实，且**能失败**（注入 mnemonic/op 后 baseline 152→151、orphan 0→1）。
- 基线**派生**自 `opcodes.yaml`（`len(m1)`），全文无数值硬编码（`grep -nE '178|== *152' validate_instrinfo.py` 仅命中 docstring 中「绝无硬编码 178/152」的说明文字，无任何判据常量）。
- 证据脚本注入**真实产物**（committed patch / `opcodes.yaml`）：注入后 `git diff --name-only`=1（非空，防空注入），trap+`git checkout` 还原，末尾 `git status --porcelain` 为空。
- 无 `tee`；所有检查 `cmd > log 2>&1; rc=$?` 捕获退出码。
- 真源方向正确：脚本只**读取** `opcodes.yaml` + patch 做交叉校验，未反推真源。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `DEF_PATTERN` 上方注释误写 "Only the formats…" | ✅已修 | 改为 `# Instruction def: def NAME : DADAO<class><"mnemonic"> { ... }` | 复跑 validator EXIT=0（`.work/log/llvm/LLVM-046t-make-check-instrinfo.log`） |
| F2 `--dump-map` help 写 "and exit" 但实际继续输出 | ✅已修 | help 改为 "print the resolved id -> def-name mapping" | `--dump-map` 与 `--self-test` 均 EXIT=0 |
| F3 证据脚本直接执行 `"$VALIDATOR"` → EXIT=126（无执行位/未走 shebang） | ✅已修 | 统一 `python3 "$VALIDATOR"`/`"$GENERATOR"`（新增 `run_validator()`） | 脚本 12/12 PASS，EXIT=0 |
| F4 Check 6 与 join key 语义部分冗余（key 已含 format） | ❌不修 | 保留为廉价一致性断言，无副作用、增加可读性 | validator EXIT=0 |
| F5 `--td` 指向不存在文件时抛 traceback | ❌不修 | argparse 用户输入错误，非零退出即可（本项目未启用 lint/类型门） | 非默认路径，不触及 make-check 路径 |
| F6 需确认注入确为「被测产物」而非仅 `/tmp` 副本 | ✅核实 | 注入 directly 改 committed patch / `opcodes.yaml`，真实 `git diff`=1，trap 还原 | run.sh 步骤 5/6 + 步骤 8 `no residue` PASS |

**判决**：全部 finding 已修或已说明；validator EXIT=0、generator 拒绝运行、`make check` EXIT=0、证据脚本自注入→FAIL→还原→回绿。无未修 finding，故置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer (mimo-v2.5-pro)
**审查时间**：2026-10-05T08:20+08:00
**审查范围**：`tools/llvm/validate_instrinfo.py`（全文）、`tools/llvm/generate_instrinfo.py`（头+guard）、`Makefile`（check-instrinfo target + check 链）、`.work/evidence/LLVM-046t/run.sh`（全文）

---

### 一、证据脚本审核

**逐条断言可达 FAIL 路径分析**：

| # | 检查名 | FAIL 条件 | 是否可达 FAIL | 结论 |
|---|--------|-----------|--------------|------|
| 1 | validator (legal input) | rc≠0 | ✅ 校验器6项任一失败即非零退出 | 合格 |
| 2 | baseline M1 count (derived) | declared≠derived | ✅ 从 .log 解析 vs opcodes.yaml 实算，硬编码则对不上 | 合格 |
| 2b | grep cross-check | grep_m1≠derived | ✅ 两个独立计算路径 | 合格 |
| 3 | --self-test | st_rc≠0 | ✅5 个样本任一不匹配即 FAIL | 合格 |
| 3b | --dump-map | 4 samples missing | ✅ 任一样本不在映射中即 FAIL | 合格 |
| 4 | generator retired | gen_rc≠2 或无 DEPRECATED | ✅ guard 返回2 且 stderr 含 DEPRECATED | 合格 |
| 5 | inject .td mnemonic → FAIL | diff=0 或 exit=0 | ✅ 改 `ld.ub`→`ld.ux`，join key 变化致 baseline/orphan 失败 | 合格 |
| 5b | restore .td → green | exit≠0 | ✅ git checkout 还原后校验通过 | 合格 |
| 6 | inject opcodes op → FAIL | diff=0 或 exit=0 | ✅ 改 `0x10`→`0x1A`，join key 变化致失败 | 合格 |
| 6b | restore opcodes → green | exit≠0 | ✅ git checkout 还原 | 合格 |
| 7 | make check-instrinfo wired | target 或 chain 缺失 | ✅ Makefile grep ≥4 处 | 合格 |
| 8 | products restored (no residue) | dirty≠0 | ✅ trap+git checkout 清理 | 合格 |

**无恒真断言、无两支写同一结果**。注入直接操作 committed 文件（非 `/tmp` 副本），`git diff --name-only` 非空验证防空注入。末尾无 `tee` 吞退出码。

**脚本判定**：✅ 合格，可重跑。

---

### 二、重跑证据脚本（真实输出）

```
$ cd /mnt/tao/DADAO-v5 && bash .work/evidence/LLVM-046t/run.sh > /tmp/opencode/LLVM-046t-review/evidence-run.log 2>&1; echo "EXIT=$?"
EXIT=0
```

```
=== LLVM-046t evidence: 2026-10-05T08:17:19+08:00 ===
repo: /mnt/tao/DADAO-v5

PASS  1. validator (legal input)                 expected=exit 0 actual=exit 0 exit=0
PASS  2. baseline M1 count (derived)             expected=152 actual=152 exit=0
PASS  2b. grep '^- id:'.m1 cross-check           expected=152 actual=152 exit=0
PASS  3. explicit id->def mapping --self-test    expected=exit 0 (5 samples) actual=exit 0 exit=0
PASS  3b. --dump-map exposes id->def mapping     expected=4 samples present actual=all-present exit=0
PASS  4. generator retired (refuses to run)      expected=exit 2 + DEPRECATED actual=exit 2 exit=0
PASS  5. inject .td mnemonic -> FAIL             expected=diff!=0 & exit!=0 actual=diff=1 exit=1 exit=0
PASS  5b. restore .td -> green                   expected=exit 0 actual=exit 0 exit=0
PASS  6. inject opcodes op -> FAIL               expected=diff!=0 & exit!=0 actual=diff=1 exit=1 exit=0
PASS  6b. restore opcodes -> green               expected=exit 0 actual=exit 0 exit=0
PASS  7. make check-instrinfo wired to check     expected=target + chain present actual=grep=4 exit=0
PASS  8. products restored (no residue)          expected=0 actual=0 exit=0

ALL CHECKS PASSED
```

**12/12 PASS，EXIT=0**。与完成区一致。

---

### 三、独立验证命令（reviewer 自跑）

#### 3.1 `python3 tools/llvm/validate_instrinfo.py`
```
$ python3 tools/llvm/validate_instrinfo.py ; echo "EXIT=$?"
EXIT=0
```
输出：
```
=== Validation: DADAOInstrInfo.td vs contracts/opcodes.yaml ===
opcodes.yaml     : /mnt/tao/DADAO-v5/contracts/opcodes.yaml
instruction defs : /mnt/tao/DADAO-v5/components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch
records total    : 228
M1 records       : 152  (baseline derived from opcodes.yaml)
M3 records       : 1
.td instr defs   : 154

PASS: mapping — join key (mnemonic, format, op, ha) 在两侧均唯一
PASS: baseline — 152/152 条 M1 记录各有唯一 .td def
PASS: coverage — 1/1 条 M3 记录各有唯一 .td def
PASS: orphan — 全部 154 个 .td def 各有唯一 opcodes 记录
PASS: non-m1 — 2 个非 m1 def 均在 allow-list（[('sub_o_dbb', 'm3'), ('fence', 'excluded')]）
PASS: format — m1 def 格式类集合 == M1 记录格式集合: ['iiii', 'oiii', 'orri', 'orrr', 'riii', 'rrii', 'rrri', 'rrrr', 'rwii']

=== Result: 0 errors ===
```

#### 3.2 `python3 tools/llvm/validate_instrinfo.py --self-test`
```
$ python3 tools/llvm/validate_instrinfo.py --self-test ; echo "EXIT=$?"
EXIT=0
```
输出含5条 PASS self-test（ld.ub_rrii_rd→ld_ub_rd、add.si_riii_rd→add_si_rd、sub.o_orrr_dbb→sub_o_dbb、rb2rb_orri_rb→rb2rb、fence_oiii_imm→fence）。

#### 3.3 `python3 tools/llvm/generate_instrinfo.py`
```
$ python3 tools/llvm/generate_instrinfo.py ; echo "EXIT=$?"
EXIT=2
```
stderr: `DEPRECATED: tools/llvm/generate_instrinfo.py is retired (ISS-103, LLVM-046t).`

#### 3.4 `make check-instrinfo`
```
$ make check-instrinfo ; echo "EXIT=$?"
EXIT=0
```

#### 3.5 `make check`
```
$ make check ; echo "EXIT=$?"
EXIT=0
```
末尾：`Total Discovered Tests: 33 / Passed: 33 (100.00%) / repository checks: PASS`

#### 3.6 `make check` 中 `check-instrinfo` 接入确认
```
$ grep -n 'check-instrinfo' Makefile
43:         check-rule-refs check-fp-contract check-instrinfo \
87: 	@echo "  make check-instrinfo  Cross-check DADAOInstrInfo.td against opcodes.yaml (LLVM-046t)"
225: check: manifest-check validate-vectors check-spec-drift check-patch-tree check-asm-list check-asm-list-drift check-asm-prose check-legality-drift check-interface validate-encoding check-scope check-rule-refs check-fp-contract check-instrinfo check-qemu-semantics check-cfx-aliases check-dirs check-no-residue check-lit
317: check-instrinfo:
```
4 处引用：L43（help 列表）、L87（help 文字）、L225（check 依赖链）、L317（target 定义）。✅ 已并入 `make check`。

---

### 四、独立注入反例（reviewer 自选，不同于 engineer 证据脚本的注入点）

**注入点**：`contracts/opcodes.yaml` 的 `rb2rb_orri_rb` 条目，将 `ha: '0x34'` 改为 `ha: '0x35'`。

**注入理由**：engineer 证据脚本改 `.td` 的 `ld.ub` mnemonic 和 opcodes 的 `ld.ub` op；我选不同的字段（`ha`）和不同的记录（`rb2rb`），验证 join key 的 `ha` 维度也能被校验器捕获。

#### 4.1 注入 → FAIL
```
$ python3 -c "
p = 'contracts/opcodes.yaml'
t = open(p).read()
i = t.index('- id: rb2rb_orri_rb\n')
j = t.index('ha: ', i)
k = t.index('\n', j)
open(p, 'w').write(t[:j] + \"ha: '0x35'\" + t[k:])
"
$ git diff --name-only -- contracts/opcodes.yaml
contracts/opcodes.yaml
$ python3 tools/llvm/validate_instrinfo.py ; echo "EXIT=$?"
EXIT=1
```
输出：
```
FAIL: baseline — 151/152 条 M1 记录匹配到 .td def
FAIL: orphan — 1 个 .td def 未匹配到唯一记录
=== Result: 2 errors ===
```
stderr: `M1 记录 rb2rb_orri_rb 的 .td def 数 = 0（期望 1；key=('rb2rb', 'orri', '0x40', '0x35')）` + `.td def rb2rb 无唯一 opcodes 记录（命中 0；key=('rb2rb', 'orri', '0x40', '0x34')）`

**注入有效性**：`git diff --name-only` 非空（1 文件），`EXIT=1`。✅ 注入生效、校验器失败。

#### 4.2 还原 → 回绿
```
$ git checkout -- contracts/opcodes.yaml
$ git diff --name-only -- contracts/opcodes.yaml | wc -l
0
$ python3 tools/llvm/validate_instrinfo.py ; echo "EXIT=$?"
EXIT=0
```
输出6项 PASS、0 errors。✅ 还原干净、校验器回绿。

#### 4.3 工作区清洁确认
```
$ git status --porcelain
 M ".tao/tasks/llvm/LLVM-046t-instrinfo生成器校验器刷新.md"
 M Makefile
 M tools/llvm/generate_instrinfo.py
 M tools/llvm/validate_instrinfo.py
```
仅本任务预期改动的4个文件，无临时残留。✅

---

### 五、(a)/(b) 决策复核

#### 5.1 校验器 (a) 刷新

**join key 唯一性**：opcodes.yaml228条记录的 `(mnemonic, format, op, ha)` 全部唯一（无重复），`.td` 154个 def 的 join key 也全部唯一。✅ 无塌缩。

**基线派生**：`len(m1)` 从 opcodes.yaml 的 `scope:m1` 子集派生（Python 列表推导），全文无 `178` 或 `==152` 硬编码。✅

**显式命名映射**：`build_id_to_def()` 通过 join key 解析 id→def-name，`--self-test` 验证5个样本（含跨格式/跨 scope），`--dump-map` 暴露全量映射。✅

#### 5.2 生成器 (b) 退役

**「def 名不可由 id 反推」验证**：抽样2处：
- `rb2rb_orri_rb` → def 名 `rb2rb`：`id` 按 `{mnemonic}_{format}_{feature}` 规则生成，含 `_orri_rb` 后缀；但 `.td` def 名 `rb2rb` 是 legacy 手工命名，被 `DADAOInstrInfo.cpp` 直接引用（`Opc = DADAO::rb2rb; // RB -> RB`，L66）。无法由 `id` 反推。
- `ld.ub_rrii_rd` → def 名 `ld_ub_rd`：`id` 的 mnemonic `ld.ub` 用 `.`，def 名 `ld_ub_rd` 用 `_` 且省略 format 字段。同样不可反推。

**退役 guard**：`main()` 在 `return 2` 前即返回，历史实现保留在 unreachable code 供溯源。✅ 不会误写 `.td`。

**决策判定**：✅ 合理，理由成立。

---

### 六、披露复核

#### 6.1 `gen_m1_asm.py`/`test_m1_asm.py` 148/152 问题

**reviewer 独立验证**：
```
$ python3 tools/llvm/test_m1_asm.py 2>&1 | tail -5
FAIL: call [rb0, 2i]
FAIL: call [rb3, rd0, 24i]
Results: 148 passed, 4 failed out of 152 instructions
```
失败指令：61: jump [rb0, 2i]、62: jump [rb3, rd0, 24i]、65: call [rb0, 2i]、66: call [rb3, rd0, 24i]。

**是否本次引入**：否。`git log --oneline -3 tools/llvm/gen_m1_asm.py tools/llvm/test_m1_asm.py` 显示最后改动在 `LLVM-019t`（MC 新语法支持），非本任务。✅ 既有问题。

**判定**：应另立 issue/任务处理（与 ISS-103 同族），不阻塞本任务。

#### 6.2 `.td` 头注释「Auto-generated / DO NOT EDIT」

**reviewer 验证**：
```
$ grep -n 'Auto-generated\|DO NOT EDIT' components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch
16:+// Auto-generated from contracts/opcodes.yaml by tools/llvm/generate_instrinfo.py.
17:+// DO NOT EDIT MANUALLY.
```

**判定**：确与退役事实不符，但修改需改 `components/**`（补丁导出），可能触发组件重建，超出本「纯 Python 工具刷新」范围。**非阻塞**，建议后续任务一并订正。

---

### 七、约束核验

| 约束 | 是否守住 | 证据 |
|------|---------|------|
| 临时目录 `/tmp/opencode/LLVM-046t/` | ✅ | 脚本用 `${TMPDIR:-/tmp}/opencode/LLVM-046t`；reviewer 用 `/tmp/opencode/LLVM-046t-review/` |
| 不提交 git | ✅ | `git status` 仅显示本任务预期改动，无暂存区提交 |
| 完成区结论与真实输出逐条对齐 | ✅ | reviewer 全部重跑，输出一致 |
| 只动本任务范围文件 | ✅ | 改动：validate_instrinfo.py、generate_instrinfo.py、Makefile、任务文件 |
| 复杂命令输出留 `.work/log/` | ✅ | 证据脚本输出在 `.work/log/llvm/` |
| 交付一键证据脚本 | ✅ | `.work/evidence/LLVM-046t/run.sh` 12/12 PASS |
| 脚本能失败（反例门控） | ✅ | 注入→FAIL（EXIT=1），还原→回绿（EXIT=0） |

---

### 八、判决

**Accepted**

全部12项证据脚本检查通过（reviewer 重跑 EXIT=0）。校验器6项检查全 PASS（152/152 baseline、0 errors）。`--self-test` EXIT=0（5样本全对）。生成器 EXIT=2（guard 拒绝运行）。`make check` EXIT=0（33/33 lit + repository checks: PASS），`check-instrinfo` 已并入 check 链。reviewer 独立注入 `ha` 反例 → EXIT=1 → 还原 → EXIT=0。join key 两侧唯一（228 记录 / 154 def 无塌缩）。生成器退役理由成立（def 名是 CodeGen API，不可由 id 反推）。两处披露（gen_m1_asm 148/152、.td 头注释）均为既有/超范围问题，非阻塞。
