# SPEC-060t: rf0（FCSR）位域调整与访问规则（ADR-0012 D6）

**模块**：spec（含 `.tao/knowledge/` 与 `contracts/`）
**项目里程碑**：M1→M2
**依赖**：用户逐条确认（2026-09-30，ADR-0012 D6 第 1–7 条全部同意）
**状态**：待开始

## 背景

用户裁定（D6 全文见 `.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` 新增节）：

1. **位域调整**：舍入模式 `[17..16]` → `[33..32]`；SBZ 由 `[50..32]/[21..18]/[15..5]` 合并为 `[50..34]`、`[21..5]`；只读 qNaN 头 `[63..51]`/`[31..22]` 与异常 `[4..0]` 不变。
   → 每个 R/W 字段**独占一个 wyde**（wp0=异常、wp2=舍入、wp1/wp3 完全只读）；`[17:16]` 不再与「指令字 wyde-position 字段」同名。
2. **写入语义（rf0 作目的）**：允许 `rd2rf`（含 `{rf0:rf0+immu6-1}`）、`ld.o`/`ldm.o`、`ld.t`/`ldm.t`、`set.w rf0`；**写只更新 `[33..32]` 与 `[4..0]`，其余位写无效、保持原值**（含 `ld.t`/`ldm.t` 的 `[63:32]` 不变）。
3. **ILLI 边界**：仅「rf0 作**目的**」触发 ILLI —— SimRISC-07 全部浮点运算指令（46 条，含 `ft2ft`/`fo2fo`）、`cs.eq`/`cs.ne`/`cs.n`/`cs.z`/`cs.p`。
4. **读取语义（rf0 作源）**：**合法**（含 `ftsgnj`/`fosgnj` + `rfHD=rf0` 的 `abs()`、`rf2rd`、`st.*`/`stm.*`、`cs.*` 的 rf 源）。
5. **`SimRISC-00:90` 改写**（见下）。
6. **合同修正**：`rf0_as_operand` → `rf0_as_dst`；并修头部计数。
7. **复位值不变**：`0x7FF8_0000_7FC0_0000`。

### 现状缺陷（本任务须修）

- `spec/SimRISC-00:90`「rf0…**不应**采用 rf0 作为普通的浮点寄存器参与运算」——未区分源/目的，与 `SimRISC-07:174–175`（`rfHD=rf0` → `abs()`）冲突。
- `contracts/legality_rules.yaml:70–78` `rf0_as_operand`「目的**或任一源**为 rf0 时触发 ILLI」——**过宽**，与 `SimRISC-07:174–175` 冲突。
- `.tao/knowledge/contract-isa.md:52`、`:812` 同源过宽表述。
- `.tao/knowledge/contract-isa.md` / `legality_rules.yaml` 头部计数漂移：`legality_rules.yaml` L17–19 仍写「254 条：177 条 M1 + 77 条 excluded_m1」，删 `rela.si` 后应为 **253 / 176 / 77**（`SPEC-057t` 遗漏）。

## 修改内容

### A. `spec/`

1. **`spec/SimRISC-00-指令系统设计.md`**
   - §浮点寄存器 第 3 条（现 L90）**改写为**：
     > `rf0` 为浮点状态寄存器（FCSR）。它同时是单精、双精格式的 qNaN，**可作浮点运算的源操作数**；又因其同时是状态寄存器，浮点运算执行后会更新其状态位（异常位），故 **`rf0` 不可作浮点运算的目的操作数**。
   - §浮点状态寄存器 位域**逐行改为**：
     - `[63..51]`: 0111 1111 1111 1（只读，写无效；fo 格式 Quiet NaN，符号位 0、E 全 1、尾数最高位 1）——**不变**
     - `[50..34]`: SBZ（Should Be Zero）
     - `[33..32]`：舍入模式（Rounding Mode）
     - `[31..22]`: 0111 1111 11（只读，写无效；ft 格式 Quiet NaN）——**不变**
     - `[21..5]`：SBZ（Should Be Zero）
     - `[4..0]`：异常状态（Accured exception）——**不变**
   - 舍入模式段（现 L104）括号内改为：`（舍入模式的设置单独放在wp2中，程序可以直接用set.w指令进行设置）`
   - 在异常状态段后**新增**一句写语义：
     > 写 `rf0` 时**只更新** `[33..32]`（舍入模式）与 `[4..0]`（异常状态），其余位（只读 Quiet NaN 位、SBZ）**写无效、保持原值**。

2. **`spec/SimRISC-01-取数存数.md`**（§存取RF寄存器）
   - 更新 L181 注：`rf0` 作**目的**合法（`ld.o`/`ldm.o`/`ld.t`/`ldm.t`），写入按 SimRISC-00 的写语义（`ld.t`/`ldm.t` 的 `[63:32]` 不变）；`rf0` 作**源**（`st.o`/`st.t`/`stm.o`/`stm.t`）读出完整 64 位。

3. **`spec/SimRISC-02-寄存器复制.md`**
   - `cs.eq`/`cs.ne`/`cs.n`/`cs.z`/`cs.p`：**目的**（`rfhc`/`rfhb`）为 `rf0` → ILLI；**源**（`rfhd`/`rfhc`）为 `rf0` 合法。
   - `rd2rf`：`rf0` 可作目的（含 `{rf0:rf0+immu6-1}`，immu6≥2 允许），写入按 SimRISC-00 写语义；`rf2rd`：`rf0` 可作源。

4. **`spec/SimRISC-03-16位立即数操作.md`**
   - `set.w rf0, wpN, immu16` 合法；写入按 SimRISC-00 写语义（`wp2` 命中舍入、`wp0` 命中异常、`wp1`/`wp3` 完全写无效）。

5. **`spec/SimRISC-07-浮点运算.md`**
   - L62、L98：`rf0[17:16]` → `rf0[33:32]`。
   - L231 注更新（rf0 作目的/源的区分 + 指向 SimRISC-00）。
   - **新增**一句：浮点运算指令以 `rf0` 为**目的**操作数 → ILLI；`rf0` 可作**源**操作数（保留 L174–175 的 `abs()` 特例说明）。

### B. `.tao/knowledge/`

6. **`contract-isa.md`**
   - L52：删除/改写「不应作为普通浮点寄存器参与运算」→ 与 SimRISC-00 新表述一致（源合法、目的 ILLI）。
   - §1.3.3 位域表：`[50:32]`→`[50:34]`、`[17:16]`→`[33:32]`、`[21:18]`→`[21:5]`（合并），并补写/读语义。
   - §9（L812）：`（目的或任一源为 rf0 → ILLI）` → `（**目的**为 rf0 → ILLI；作**源**合法）`。
7. **`adr-0012-simrisc-0.5.4-update.md`**：新增 **D6**（上文 7 条）+ `## 状态说明` 追加一行（2026-09-30 新增 D6）。
8. **`adr-0004-test-machine.md`**：D2.1 表（L63 行）与「`rf0` 复位常量推导」表（L55–67）**就地修订**（舍入位 → `[33:32]`、SBZ 区间更新），并按 D2.4 体例在改动处**加注记**（`2026-09-30 就地修订：依据 ADR-0012 D6`）。

### C. `contracts/`

9. **`legality_rules.yaml`**
   - `rf0_as_operand` → **`rf0_as_dst`**；`fault: ILLI`；`status: deferred`（不变）；description 改为「**目的**为 `rf0` 时触发 ILLI」，并注明「`rf0` 作**源**合法」。
     - **精确适用范围（只列禁止者）**：SimRISC-07 全部浮点运算指令 46 条（含 `ft2ft`/`fo2fo`）+ `cs.eq`/`cs.ne`/`cs.n`/`cs.z`/`cs.p`。
     - **不得列入禁止清单（rf0 作目的合法）**：`rd2rf`（含 `{rf0:rf0+immu6-1}`）、`ld.o`/`ldm.o`、`ld.t`/`ldm.t`、`set.w`。
   - 头部 L17–19：`（254 条：177 条 M1 + 77 条 excluded_m1）` → `（253 条：176 条 M1 + 77 条 excluded_m1）`。

## 约束

- **原子同步**：A/B/C 三组必须一次改完（中途态会造成载体间矛盾）。
- **位域三载体逐字一致**：`spec/SimRISC-00 §浮点状态寄存器` ↔ `contract-isa.md §1.3.3` ↔ `adr-0004-test-machine.md §D2.1 推导表`。
- **不改历史**：`spec/SimRISC-0.5.3/`、`.tao/tasks/**`、`.tao/knowledge/deferred.md`（含 `deferred.md:18` 对 `rf0_as_operand` 的历史引用）、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`。
- **不改 QEMU 补丁**（`components/qemu/patches/target/dadao/cpu.c.patch` 的注释同步另开 `QEMU-029t`，本任务不碰）。
- **评估后不改（须在完成区说明理由）**：`docs/02-大道至简.md:114`、`docs/impact-matrix.md:41`。
- 复位值**不变**：`0x7FF8_0000_7FC0_0000`；adr-0004 推导表须**重算核对**（RM 复位 0 ⇒ 值不变）。
- 命令缺失 → **停下报告**，不得换命令。

## 验收标准

1. **位号**：`grep -rn "17..16\|17:16" spec/*.md .tao/knowledge/contract-isa.md .tao/knowledge/adr-0004-test-machine.md` 中**无** rf0 舍入相关命中（**指令字 wyde-position** 的 `[17:16]` 命中须保留并逐条说明）。
2. **过宽表述清除**：`grep -rn "不应采用rf0作为普通的浮点寄存器参与运算\|目的或任一源为 rf0\|目的或任一源操作数为 rf0"` 在 spec/ 与 .tao/knowledge/ 中**无命中**。
3. **三载体位域逐字一致**：给出比对命令与真实输出（3 处 `[50..34]`/`[33..32]`/`[21..5]`/`[4..0]` 完全一致）。
4. **合同**：`rf0_as_dst` 存在且 `fault=ILLI`、`status=deferred`；`rf0_as_operand` 不存在（`grep -c` = 0）；头部为 `253 条：176 条 M1 + 77 条 excluded_m1`。
5. **62 条 rf 指令规则落位**：运行
   ```
   python3 -c "import yaml;d=yaml.safe_load(open('contracts/opcodes.yaml'));r=d if isinstance(d,list) else d['instructions'];\
   [print(e['id'],[f'{\"dst\" if f[\"role\"]==\"dst\" else \"src\"}:{f[\"name\"]}' for f in e.get('fields',[]) if f.get('bank')=='rf']) for e in r if any(f.get('bank')=='rf' for f in e.get('fields',[]))]"
   ```
   逐条标注该指令族在 spec 正文中的**目的/源**规则去向（允许 / ILLI），给出 62 行表 + 逐条结论。
6. **一致性检查可失败（反例门控）**：在 `/tmp/opencode/SPEC-060t/` 副本中注入（任选，须**逐条**给出真实输出）：
   - (a) 把 `contract-isa.md` 的 `[33:32]` 改回 `[17:16]` → 三载体一致性检查 **FAIL**
   - (b) 把 `legality_rules.yaml` 的 `rf0_as_dst` 描述改回「目的或任一源」→ 过宽检查 **FAIL**
   - (c) 把 `SimRISC-00` 的写语义删掉 → 写语义检查 **FAIL**
   复原后全部 PASS，且 `git status` 无残留。
7. **门控**：`make check` **EXIT=0**；`python3 tools/spec/validate_encoding.py` **EXIT=0**；`python3 tools/integ/check_interface_alignment.py` **80/80 EXIT=0**（须贴真实退出码，用 `cmd > log 2>&1; rc=$?` 形式）。
8. **复位值**：`python3 -c "print(hex((0xFFF<<51)|(0x1FF<<22)))"` → `0x7ff800007fc00000`（与 `DADAO_RESET_RF0` 一致；QEMU 补丁值不变）。
9. **未触历史**：`git diff --name-only` 与「修改内容」清单**逐项对齐**，不得多/少。
10. 反例注入**可复原**（`git status --short` + `git diff --stat` 证据）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
