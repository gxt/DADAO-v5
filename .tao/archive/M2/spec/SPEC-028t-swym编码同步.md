# SPEC-028t: swym 编码同步（generate_opcodes.py + opcodes.yaml）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述

commit `7e44520` 将 spec `SimRISC-00` 的 QFC 表中的 `swym` 从主表 `0111-0xxx / xxx-111`（op=0x77）移到 `MISC-AMO 000-xxx / xxx-010`，但**未同步生成器**。

结果：
- spec QFC 表：`swym` 在 `op=0x00, ha=0x02`
- `contracts/opcodes.yaml`：`swym` 在 `op=0x77, ha=0x00`

`tools/spec/check_qfc_coverage.py` 报 **2 条 M1 内差异**：
```
QFC-only  op=0x00 ha=0x02  swym_oiii_imm  → M1 内
YAML-only op=0x77 ha=0x00  swym_oiii_imm  → M1 内
```

## 修改内容

### 1. tools/spec/generate_opcodes.py

找到 swym 的记录生成（约 L466-468）：
```python
# ── swym：格式从 iiii 改为 oiii，immu24 改为 immu18 ──
records.append(rec("swym-oiii", "swym", "oiii", 0x77, ...))
```

改为 MISC-AMO 位置（op=0x00，ha 编码在 rec 中）：
- 需按 MISC-AMO 子表的 `op`/`ha` 定义方式生成
- 参考同表 `illi`（op=0x00, xxx-000）和 `fence`（op=0x00, xxx-001）的生成方式
- swym 应为 `000-010` → `ha=0x02`

### 2. 重生成 contracts/opcodes.yaml

```
python3 tools/spec/generate_opcodes.py
```

### 3. 验证

```
python3 tools/spec/check_qfc_coverage.py
```
应报 **0 条 M1 内差异**。

## 约束

- 只改 swym 的编码位置，不改格式（保持 oiii）和立即数（保持 immu18）
- 不改动其他指令
- 逐条核对 MISC-AMO 表的 op/ha 定义方式

## 验收标准

1. `generate_opcodes.py` 中 swym 生成在 MISC-AMO（ha=0x02）
2. `contracts/opcodes.yaml` 中 swym 的 op/ha 与 spec QFC 表一致
3. `check_qfc_coverage.py` 报 0 条 M1 内差异（贴真实 EXIT）
4. 其他指令未被误改

## 完成区
**测试结果**：check_qfc_coverage.py 通过，EXIT=0，0 条 M1 内差异
**修改文件**：`tools/spec/generate_opcodes.py`（swym 从 build_main_table 移至 build_misc_amo，op=0x77→0x00, ha=0x00→0x02）；`contracts/opcodes.yaml`（自动生成）
**验收结果**：
```
check_qfc_coverage: QFC 表 ↔ contracts/opcodes.yaml 双向覆盖校验
[双向差异]
  QFC-only（QFC 有、yaml 缺）: 0
  YAML-only（yaml 有、QFC 不含）: 0
[汇总]
  差异总数: 0（M1 内: 0，M1 外: 0）
  OK: QFC 表与 opcodes.yaml 双向完全一致
check_qfc_coverage: done (informational, exit 0)
EXIT=0
```
swym 在 opcodes.yaml 中确认：`op: '0x00', ha: '0x02'`，格式 oiii，立即数 immu18。
**新发现/坑**：`check_qfc_coverage.py` 恒 `exit 0`（不阻断），不能以 EXIT 作通过证据；应以 stdout「差异总数: 0（M1 内: 0）」为准。
**遗留问题**：**跨模块影响（待处置）**——swym 编码从 `0x77000000` 迁到 `0x00080000`，`tests/vectors/isa/misc.yaml` 的 2 条 swym case 未同步，导致 `make check` 红。归 **`TESTCASES-013t`**（validate_vectors 恢复 role 逻辑 + swym 向量同步）处理。本任务编码同步本身正确（验收标准 1-4 通过）；`make check` 转绿需 `TESTCASES-013t` 完成后确认。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/spec/generate_opcodes.py` 两处改动（删除 + 添加），`contracts/opcodes.yaml` 自动生成结果。

**审查项**：
1. ✅ swym 从 `build_main_table`（op=0x77, ha=0x00）移除，未留残余
2. ✅ swym 在 `build_misc_amo` 中 fence（ha=0x01）之后添加，ha=0x02，符合 000-010 编码
3. ✅ 格式保持 oiii，立即数保持 immu18，section 保持 S11_SWYM
4. ✅ 其他指令未被修改（仅删除 L466-468 三行注释+记录，添加两行记录）
5. ✅ check_qfc_coverage.py 报 0 M1 内差异，EXIT=0
6. ✅ opcodes.yaml 中 swym 确认 op=0x00, ha=0x02

**判决**：通过，无 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| （无） | | | |

#### 第 1 轮 reviewer 验收

**审查范围**：`tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml` 的 swym 改动；并核验本任务对对下游（`tests/vectors/`）的影响。所有结论均基于我本人重跑。

**重跑记录（真实输出/退出码）**

1. `python3 tools/spec/check_qfc_coverage.py`:
   ```
   [双向差异] QFC-only: 0  YAML-only: 0
   [汇总] 差异总数: 0（M1 内: 0，M1 外: 0）
   OK: QFC 表与 opcodes.yaml 双向完全一致
   check_qfc_coverage: done (informational, exit 0)
   EXIT=0
   ```
   ⚠️ 该脚本设计为 lint「永不阻断，始终 exit 0」（源码 L8/L33/L400 明写 `sys.exit(0)`）。故完成区以「EXIT=0」当通过证据**属无效证据**——反例注入下它仍 exit 0（见下）。真实有效性证据是 stdout 的「差异总数: 0（M1 内: 0）」。

2. `contracts/opcodes.yaml` swym 记录（L1879）：`format: oiii`、`op: '0x00'`、`ha: '0x02'`、`mask: '0xFFFC0000'`、`value: '0x00080000'`、field `immu18 [17:0]`。与 spec `SimRISC-00` L288 表（`000-xxx` 行、`xxx-010` 列 = `swym_oiii_imm`）→ `op=0x00, ha=0x02` **一致**；`SimRISC-11` L19「后18位立即数」与 immu18 一致。

3. `python3 tools/spec/generate_opcodes.py` 重跑：`生成完成：254 条（M1 内 178，excluded_m1 76）`，输出与仓库文件 `diff -q` **IDENTICAL**（生成器可复现）。

4. `make check` → **EXIT=2**：
   ```
   tests/vectors/isa/misc.yaml case[0]: encoding.word 0x77000000 does not match ('swym_oiii_imm','oiii') mask/value (expected (word & 0xFFFC0000) == 0x00080000)
   tests/vectors/isa/misc.yaml case[1]: encoding.word 0x77000000 does not match (...)
   tests/vectors/isa/reg-compare.yaml case[7..31]: rdhb = rd1 not preset...
   tests/vectors/isa/reg-imm-block.yaml case[22..43]: ...
   validate_vectors: FAILED (17 error(s))
   make: *** [Makefile:130: validate-vectors] Error 1
   ```
   分目标独立跑：`manifest-check` EXIT=0、`check-spec-drift` EXIT=0、`check-patch-tree` EXIT=0；唯一失败子目标为 `validate-vectors`。

5. **归因实验（定位为本任务引入）**：临时把 `opcodes.yaml` 的 swym 还原为 `op=0x77/ha=0x00/value=0x77000000` 后重跑 `validate_vectors.py`：错误 **17 → 15**，且 `grep -c swym` = 0。随后从备份还原，`diff -q` **RESTORED_IDENTICAL**，`check_qfc_coverage` 复跑 0 差异。⇒ 上述 2 条 misc.yaml 错误由本任务编码变更**直接引入**；其余 15 条（reg-compare 10 + reg-imm-block 5）与本任务无关（属其它进行中任务，预存在）。

6. **反例验证（检查方法可证伪）**：把 yaml 的 swym `ha` 改为 `0x03`：
   ```
   QFC-only  op=0x00 ha=0x02  swym_oiii_imm  → M1 内
   YAML-only op=0x00 ha=0x03  swym_oiii_imm  → M1 内
   差异总数: 2（M1 内: 2，M1 外: 0）
   ```
   → `check_qfc_coverage` 的 stdout **能**检出不一致（但 exit 仍 0）。已还原。

**约束核验（逐条）**

| 约束/验收 | 结论 | 证据 |
|---|---|---|
| 只改 swym 的编码位置 | ✅ | `git diff` 仅 swym 块移动（opcodes.yaml 26 行、generate_opcodes.py 6 行） |
| swym 格式保持 oiii | ✅ | yaml `format: oiii`；生成器 `f_oiii` |
| swym 立即数保持 immu18 | ✅ | yaml `immu18 [17:0]` |
| 其他指令未被误改 | ✅ | `check_qfc_coverage` 254/254 双向全一致 ⇒ 无其它 op/ha 变动 |
| generate_opcodes 可复现 | ✅ | 重跑输出 IDENTICAL |
| spec QFC ↔ yaml op/ha 一致 | ✅ | op=0x00, ha=0x02 双方一致 |
| **验收点 4：make check 通过** | ❌ | `make check` EXIT=2；`validate-vectors` FAILED，含 2 条本任务引入的错误 |

**判决：Needs Revision**

- 未通过的命令：`make check`（子目标 `validate-vectors`，EXIT=2）。其中 **2 条**由本任务直接引入：
  `tests/vectors/isa/misc.yaml` case[0]/case[1] 的 `encoding.word` 仍为旧值 `0x77000000`，与 swym 新编码（`mask 0xFFFC0000 / value 0x00080000`）不符。
- 本任务把 swym 从 `0x77000000` 迁到 `0x00080000`（跨 spec→testcases 的契约变更），但未同步下游向量，属未处置的跨模块影响；完成区「遗留问题：无」与事实不符。
- 其余 15 条 `validate-vectors` 失败与本任务无关（预存在），不构成本任务的失败归因。

**具体修改建议**

1. 同步 `tests/vectors/isa/misc.yaml` 两条 swym case 的 `encoding.word`：`'0x77000000'` → `'0x00080000'`（mask 已由 opcodes 推导，无需改）。
2. 同步其生成器 `tools/testcases/generate_misc.py`：`SWYM_WORD0`/`VALUE_SWYM` → `0x00080000`，`mask` 注释 → `0xFFFC0000`、头部编码推导注释与两条 case 的 `notes`（当前仍写 `op=0x77`/`mask=0xFF000000`/`value=0x77000000`）一并更正；`fmt` 应为 `oiii`（现仍写 `iiii`，其本身与产物不符）。
3. 若架构师认定向量更新应归 TESTCASES 模块任务，则本任务**至少须在完成区登记该跨模块影响**（不得写「无遗留」），并新增/更新对应任务；但 `make check` 未转绿前不得作为回归通过。
4. 修正后重跑 `make validate-vectors`，确认 `grep swym` 为 0 且错误数回到 15（预存在项）。
5. 完成区不应以 `check_qfc_coverage` 的 `EXIT=0` 作通过证据（该脚本恒 exit 0），应引用 stdout「差异总数: 0（M1 内: 0）」。

（说明：本轮未对 `check_qfc_coverage` 的「M1 外仅 yaml 14」告警作判定，该告警与本任务无关，属预存在。）

#### 第 2 轮 reviewer 验收（返工后）

**审查范围**：工作树中 `tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml` 的 swym 改动（相对 HEAD `694a628` 的**未提交**改动）。以下结论全部基于本人重跑，未采信完成区转述。

**重跑记录（真实输出/退出码）**

1. `python3 tools/spec/check_qfc_coverage.py`（stdout）：
   ```
   [双向差异] QFC-only（QFC 有、yaml 缺）: 0
             YAML-only（yaml 有、QFC 不含）: 0
   [汇总] 差异总数: 0（M1 内: 0，M1 外: 0）
   OK: QFC 表与 opcodes.yaml 双向完全一致
   check_qfc_coverage: done (informational, exit 0)
   EXIT=0
   ```
   ⚠️ 该脚本恒 `exit 0`（informational），故有效证据是 stdout「差异总数: 0（M1 内: 0）」，非退出码。

2. **三方一致**（逐处实读）：
   - `spec/SimRISC-00-指令系统设计.md` L288：行 `000-xxx`、列 `xxx-010` 单元格 = `swym_oiii_imm` → `op=0x00, ha=0x02`。
   - `tools/spec/generate_opcodes.py` L505-507（`build_misc_amo`，该函数 `op = 0x00`）：`rec("swym-oiii","swym","oiii",op,f_oiii("immu18"),[],S11_SWYM,ha=0x02)`；`build_main_table` 区间内 swym 记录计数 = 0（无残余）。
   - `contracts/opcodes.yaml` L2164-2176：`op: '0x00'`、`ha: '0x02'`、`mask: '0xFFFC0000'`、`value: '0x00080000'`、field `immu18 [17:0]`；全表 `id: swym_oiii_imm` 计数 = 1。
   - 编码自洽：`0x00080000 & 0xFFFC0000 == 0x00080000`，`ha=2` 落在 bits[25:18] → `2<<18 = 0x80000` ✓。

3. **生成器可复现**：`python3 tools/spec/generate_opcodes.py` → `生成完成：254 条（M1 内 178，excluded_m1 76）`；对工作树文件 `diff` ⇒ **IDENTICAL**。已从备份还原，`md5sum` 一致（`1afd8fa7…`）。

4. **反例验证（检查可证伪）**：把 opcodes.yaml 的 swym `ha` 由 `0x02` 改 `0x03` 后重跑：
   ```
   QFC-only  op=0x00 ha=0x02  swym_oiii_imm  → M1 内
   YAML-only op=0x00 ha=0x03  swym_oiii_imm  → M1 内
   差异总数: 4（M1 内: 2，M1 外: 2）
   ```
   ⇒ 该检查**能**检出不一致（M1 内差异 0→2）。已还原，`md5sum -c` OK。

**约束核验（逐条）**

| 约束/验收 | 结论 | 证据 |
|---|---|---|
| swym 生成在 MISC-AMO（ha=0x02） | ✅ | generate_opcodes.py L505-507；main_table 无残余 |
| opcodes.yaml op/ha 与 spec QFC 一致 | ✅ | op=0x00, ha=0x02 三方一致 |
| check_qfc_coverage 0 条 M1 内差异 | ✅ | stdout「差异总数: 0（M1 内: 0）」 |
| 其他指令未被误改 | ✅ | `git diff` 范围：opcodes.yaml 仅 swym 块移动（15±）、generate_opcodes.py 仅 swym 记录移动（4−/3+） |
| 格式保持 oiii | ✅ | yaml `format: oiii`；生成器 `f_oiii` |
| 立即数保持 immu18 | ✅ | yaml `immu18 [17:0]` |
| 生成器可复现 | ✅ | 重跑 IDENTICAL |

**观察（非阻塞，供主会话/架构师定夺）**

- 本任务的修复**仅存在于工作树、未提交**。HEAD `694a628` 的 commit message 声称「SPEC-028t: swym 迁至 MISC-AMO (op=0x00, ha=0x02)」，但 `git show 694a628 -- tools/spec/generate_opcodes.py` 中**无任何 swym 行**——该 commit 实际未包含 swym 改动（原因见 SPEC-031t 第 2 轮记录 L80/L101：其返工 `git checkout HEAD` 时把先前未提交的 swym 改动一并还原）。以 HEAD 为准核对会得到错误结论，提交时须在 message 中据实说明。
- 工作树另含与 **SPEC-029t**（旧 spec 文件删除 + `SimRISC-10` 入库）、**SPEC-030t**（`docs/README.md`）相关、与本任务无关的未提交改动——不计入本任务「最小改动」。

**判决：Accepted**（验收标准 1–4 与全部约束在本轮重跑下满足）。