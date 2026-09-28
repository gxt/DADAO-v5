# TESTCASES-013t: validate_vectors 恢复 role 逻辑 + swym 向量同步

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：`SPEC-031t`
**状态**：已验证

## 问题描述

1. **validate_vectors 的 src 检测错误**：SPEC-024t 删除 opcodes.yaml 的 `role` 字段后，validator 被改为按 format 推导 src，但**语义错误**（把 orrr/orri 的 `hb` 误判为 src，实际 `hb` 是目的寄存器），导致 **15 条误报**
2. **swym 向量未同步**：SPEC-028t 将 swym 编码从 `op=0x77` 迁到 MISC-AMO `op=0x00, ha=0x02`（word 从 `0x77000000` 变为 `0x00080000`），`tests/vectors/isa/misc.yaml` 的 2 条 swym case 未更新

## 前置

`SPEC-031t` 恢复 `role` 字段后，validator 可恢复用 role 判断 src。

## 修改内容

### 1. tools/testcases/validate_vectors.py

将 SPEC-024t 引入的 format 推导逻辑**恢复为 role 判断**：
```python
for fld in fields:
    if fld.get("role") != "src":
        continue
    bank = fld.get("bank")
    ...
```

### 2. tests/vectors/isa/misc.yaml

更新 2 条 swym case 的 `encoding.word`：
- 旧：`0x77000000`
- 新：`0x00080000`

### 3. tools/testcases/generate_misc.py

同步 swym 的编码常量（`SWYM_WORD0` 等）、注释、notes（format 应为 oiii），并重生成 misc.yaml。

## 约束

- validator 恢复 role 逻辑后，15 条误报应消失
- 不改动其他测试向量
- 逐条核对，禁止正则批量替换

## 验收标准

1. `validate_vectors.py` 用 `role` 判断 src
2. `misc.yaml` 的 swym case word 为 `0x00080000`
3. `python3 tools/testcases/validate_vectors.py` EXIT=0（15 条误报消失）
4. `make check` EXIT=0
5. 其他向量未被误改

## 完成区
**测试结果**：validate_vectors EXIT=0（178/178 M1 identities covered,15 data files, 747 cases, 0 data coverage gaps）；make check EXIT=0
**修改文件**：
- `tools/testcases/validate_vectors.py`（L461-493 format 推导 → role 判断，删除32行，替换为6行）
- `tests/vectors/isa/misc.yaml`（swym case[0]/case[1] word `0x77000000` → `0x00080000`，notes 同步）
- `tools/testcases/generate_misc.py`（`SWYM_WORD0`/`MASK_SWYM`/`VALUE_SWYM` 常量更新，fmt `iiii` → `oiii`，头部注释/notes 同步）
- `contracts/opcodes.yaml`（swym entry: `op: '0x77' → '0x00'`, `ha: '0x00' → '0x02'`, `value: '0x77000000' → '0x00080000'`——SPEC-028t 遗留，opcodes.yaml 实际未同步，本任务一并修正）
**验收结果**：
```
$ python3 tools/testcases/validate_vectors.py 2>&1; echo "EXIT=$?"
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
EXIT=0

$ make check 2>&1; echo "EXIT=$?"
enabled components: llvm-project, qemu
references: 2
manifest validation: PASS
validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
── spec drift check ──
[PASS] contract-abi.md
[PASS] contract-elf.md
[PASS] contract-isa.md
── 结果: 检查 3 个合约，排除 1 个，错误 0 个 ──
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```
**新发现/坑**：
- SPEC-028t 任务文件声称已完成 opcodes.yaml swym 编码同步（`待验收`），但实际 `contracts/opcodes.yaml` 仍为旧值 `op=0x77, value=0x77000000`，`tools/spec/generate_opcodes.py` 也未更新。本任务须一并修正 opcodes.yaml，否则 validate_vectors 会因 mask/value 不匹配报错。
- generate_misc.py 的 swym fmt 写为 `iiii`（应为 `oiii`），与产物 misc.yaml 不一致，属 SPEC-028t 遗留。
**遗留问题**：
- `tools/spec/generate_opcodes.py` 中 swym 仍在 `build_main_table`（op=0x77），未迁至 `build_misc_amo`（op=0x00, ha=0x02）。本任务只改了 opcodes.yaml（生成产物），未改生成器脚本。需后续任务（或 SPEC-028t 返工）同步生成器。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：4 个文件的改动，逐行核对。

**审查项**：

1. **validate_vectors.py L461-467**：format 推导（32行）→ role 判断（6行）。确认：
   - `fld.get("role") != "src"` 正确跳过非 src 字段（dst/imm/cfxcode 等）
   - `bank not in ("rd", "rb", "ra")` 保留原有 bank 过滤
   - 下游逻辑（字段提取、寄存器预置检查）未改动
   - **验证**：`add.sb_orrr_rd` 的 `rdhb(role=dst)` 被跳过，`rdhc/rdhd(role=src)` 被处理 ✓

2. **misc.yaml case[0]/case[1]**：word `0x77000000` → `0x00080000`，notes 同步。确认：
   - `(0x00080000 & 0xFFFC0000) == 0x00080000` ✓
   - 其他 case（illi、fence）未被误改 ✓

3. **generate_misc.py**：`SWYM_WORD0`/`MASK_SWYM`/`VALUE_SWYM` 常量更新，fmt `iiii`→`oiii`，注释/notes 同步。确认：
   - `_verify(SWYM_WORD0, MASK_SWYM, VALUE_SWYM)` 通过 ✓
   - 重生成 misc.yaml 与手工修改一致 ✓

4. **opcodes.yaml swym entry**：`op: '0x77'→'0x00'`, `ha: '0x00'→'0x02'`, `value: '0x77000000'→'0x00080000'`。确认：
   - 与 SPEC-028t 任务描述一致（MISC-AMO op=0x00, ha=0x02）
   - mask `0xFFFC0000` 未变（格式仍为 oiii）

**判决**：通过，无 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| （无） | | | |

#### 第 1 轮 reviewer 验收

**审查范围**：工作树中 `tools/testcases/validate_vectors.py`、`tests/vectors/isa/misc.yaml`、`tools/testcases/generate_misc.py` 的未提交改动。以下结论全部基于本人重跑与注入反例，未采信完成区转述。

**重跑记录（真实输出/退出码）**

1. `python3 tools/testcases/validate_vectors.py`：
   ```
   validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)
   EXIT=0
   ```

2. **role 逻辑**（逐行实读）：`validate_vectors.py` L461-467 = `for fld in fields: if fld.get("role") != "src": continue`（其后按 `bank` 过滤并校验预设）；`grep -n "is_src|fname.endswith"` **无匹配** ⇒ SPEC-024t 引入的 32 行 format 推导逻辑已删除。

3. **承重证明（反例 A：证明修复确为 15 误报消失之因）**：将 validator 临时换回 `HEAD:tools/testcases/validate_vectors.py`（format 推导版）后重跑：
   ```
   validate_vectors: FAILED (15 error(s))
   EXIT=1
   ```
   15 条全部为 `hb` 字段被误判为 src（如 `case[31]: active semantic src field rdhb = rd1 not preset`、`rahb`、`rbhb`）。换回修复版后 0 错误（见上）。⇒ 完成区「15 条误报消失」属实且由该修复达成。已还原（`diff` RESTORED_IDENTICAL）。

4. **非空转证明（反例 B：证明修复后仍能捕获真实缺失 src）**：删去 `tests/vectors/isa/reg-arith.yaml` 中 `add.so_orrr_rb` semantic case 的 `rb2` 预设后重跑：
   ```
   tests/vectors/isa/reg-arith.yaml case[44]: active semantic src field rbhc = rb2 not preset in input_state.rb
   validate_vectors: FAILED (1 error(s))
   EXIT=1
   ```
   已还原（该文件 `git diff` 为空，干净）。⇒ 该检查非恒 PASS。

5. **swym 向量同步**：`tests/vectors/isa/misc.yaml` case[0]/case[1]（L12/L27）`word: '0x00080000'`；`0x00080000 & 0xFFFC0000 == 0x00080000` ✓。其余 case 未变（illi `0x00000000`、fence `0x00040000`/`0x00050000`）；`git status` 中向量文件仅 `misc.yaml` 一个被改。

6. **生成器可复现**：`python3 tools/testcases/generate_misc.py` → `Generated 6 cases … [0] swym_oiii_imm oiii encoding …`，对工作树 `misc.yaml` `diff` ⇒ **MISC_IDENTICAL**；`_verify(SWYM_WORD0, MASK_SWYM, VALUE_SWYM)` 通过；swym `fmt="oiii"`（原 `iiii` 已改）。已还原，`md5sum` 一致（`a3c1c74b…`）。

7. `make check`：
   ```
   manifest validation: PASS
   validate_vectors: 178/178 M1 identities covered OK (… 15 data files, 747 cases; data coverage gaps: 0)
   spec drift check: PASS
   check-patch-tree: 2 component(s), 67 patches OK
   check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)
   repository checks: PASS
   EXIT=0
   ```

8. **反例 C（make check 可失败）**：注入 misc.yaml swym word `0x77000000` 后 `make check` ⇒ `EXIT=2`（`validate_vectors: FAILED (1 error(s))`；`make: *** [Makefile:130: validate-vectors] Error 1`）。已还原，`md5sum -c` OK。

**约束核验（逐条）**

| 约束/验收 | 结论 | 证据 |
|---|---|---|
| validator 用 role 判断 src | ✅ | L463 `role != "src"`；format 推导（is_src/fname.endswith）无残留 |
| 15 条误报消失 | ✅ | 换回 HEAD 版 = 15 errors；修复版 = 0 |
| misc.yaml swym word = 0x00080000 | ✅ | case[0]/case[1] |
| validate_vectors EXIT=0 | ✅ | 本人重跑 |
| make check EXIT=0 | ✅ | 本人重跑 |
| 其他向量未被误改 | ✅ | 向量文件仅 misc.yaml 改动；文件内仅 swym word + 生成器驱动之 notes 折行（语义不变） |
| generate_misc 重生成一致 | ✅ | MISC_IDENTICAL |

**观察（非阻塞，供主会话/架构师定夺）**

- **引用陈旧（预存在，非本任务引入）**：`misc.yaml` / `generate_misc.py` 的 swym `spec_cite` 仍为 `SimRISC-04 §占位指令`，fence 为 `SimRISC-04 §fence指令`；但现规范「占位指令」已迁至 `spec/SimRISC-11-其它.md §占位指令`（`opcodes.yaml` 已正确引用 `SimRISC-11 §占位指令`）。`HEAD:misc.yaml` 同值 ⇒ 预存在，且不在本任务验收标准内。建议另立任务统一修正 swym/fence 的 `spec_cite`。
- **未提交**：本任务改动同样仅在**工作树**、未入 commit（与 SPEC-028t 修复同批待提交）。

**判决：Accepted**（验收标准 1–5 与全部约束在本轮重跑下满足）。