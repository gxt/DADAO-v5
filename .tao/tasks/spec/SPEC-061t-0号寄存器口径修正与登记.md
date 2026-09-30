# SPEC-061t: 0 号寄存器口径修正（`ra0` 可读写）+ 相关措辞与登记

**模块**：spec（含 `.tao/knowledge/`）
**项目里程碑**：M1→M2
**依赖**：用户裁定（2026-09-30：建任务；**先不执行**）
**状态**：已验证
**前置**：**F2 涉及已 Accepted 的 `ADR-0012 D3.1`，其修订措辞须经用户逐条确认后方可写入**（AGENTS「ADR decision 逐条确认」）

## 背景（`ra0` 读写口径分析结论）

**事实**：`ra0` 的读、写在各层均**合法**，且三层一致——`SimRISC-01:153`「`raHA` 为 `ra0` 时不触发异常（**ra0 可读写**）」；`legality_rules.yaml` **无** `ra_dest_ra0`（对照 `rd0`/`rb0` 有显式 ILLI）；QEMU 六条路径（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd`）均明确允许 `ra0`；`min_rom_probe_013t.py` 的 R1/X1–X3 覆盖 `ra0` 写入（MemRAS 启用/溢出/下溢/精确异常）。这是**有意设计**：`ra0` = MemRAS 指针（低48）+ 引用计数（高16），软件须在进程入口设置、OS 须在进程切换时保存恢复。

但查出 5 处口径问题（F1/F2 为**实质错误**；**F4 已移出至 `QEMU-030t`、F5 已取消**，见下）：

| # | 问题 | 证据 |
|---|---|---|
| **F1** | `spec/SimRISC-02-寄存器复制.md` L64 通用句「**目的寄存器不可为 0 号寄存器**时触发 ILLI（`rdHB` 不可为 `rd0`，`rbHB` 不可为 `rb0`）」与**同节**例外冲突：`rd2ra` 目的 `ra0` 合法、`rd2rf` 目的 `rf0` 合法（`SPEC-060t` 刚加的注） | 本句 + 同段 `rd2rf` 注 |
| **F2** | `ADR-0012 D3.1`「**仅**「**目的**为 **0 号寄存器**」才触发 ILLI」**过度概括**——`ra0`/`rf0` 作目的均**合法**（`rf0` 见 `D6`） | `adr-0012` D3.1；根因是 `ADR-0015` 概括「每组寄存器的 0 号寄存器只读」只对 `rd0`/`rb0` 成立 |
| **F3** | 合同层**缺正向声明**：`legality_rules.yaml` 对 `ra0` 只有多寄存器规则；`contract-isa §1.3.4` 只描述位域，未写「可读写」 | `legality_rules.yaml` L109–130；`contract-isa.md` L87–103 |
| **F4** | ~~`deferred.md` 的「MemRAS 路径未实现」条目无关闭标注~~ → **已移出至 `QEMU-030t`**（用户 2026-09-30 裁定方案 B） | — |
| **F5** | ~~`ra0` 可作多寄存器区间**起点**（`ldm.o {ra0:ra0+immu6-1}`、`rd2ra {ra0:...}`）~~ → **已取消**（用户 2026-09-30：不需要登记） | — |

## 修改内容

### F1 `spec/SimRISC-02-寄存器复制.md`（L64 通用句）

改为（逐字采用）：

```
- 目的寄存器**不可为 `rd0`/`rb0`**时触发 ILLI 异常；`ra0`（`RACNT` + `MRPTR`，见 D7）与 `rf0`（FCSR，见 D6）作目的**合法**（见 SimRISC-01 §存取RA寄存器、SimRISC-00 §浮点状态寄存器）。
```

> 注：**只为消除矛盾**，不改 `rd2rd`/`rb2rb` 等既有规则的语义（`rdHB`/`rbHB` 不可为 0 号的行为不变）。

### F2 `ADR-0012 D3.1` 就地修订（**待用户逐条确认后才能改**）

**拟修订文本（2026-09-30 用户定稿）**，逐字采用：

> **各寄存器组的 0 号寄存器都有专门的用途**：
> - `rd0`（恒 0）、`rb0`（读出当前指令的地址）：**只读**。`rb0` 作**任何显式目的** → ILLI；`rd0` 作**目的** → ILLI，**例外**：① rrrr 双目的 `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 允许其中一个目的为 `rd0`（丢弃对应半结果），但**不能同时为 `rd0`**、也**不能为同一非 `rd0` 寄存器**；② `ret rd0, 0` 允许（无需设置返回值）。`rd0`/`rb0` 作**源**合法（`rd0` 读出 0、`rb0` 读出当前指令的地址）。
> - `ra0`（`RACNT` + `MRPTR`，见 D7）、`rf0`（FCSR，位域与写语义见 D6）：**可读写**。

→ 加**就地修订注记** + `## 状态说明` 追加一行（体例同 `SPEC-058t`：就地措辞修订，decision 语义不变）。

> **engineer 注意**：本项须待用户对上述文本**最终确认**后方可写入；确认前**停下询问**。

### F3 `contract-isa.md §1.3.4`（补正向声明）

在 `ra0` 说明后新增：

```
- `ra0` 作**目的**或**源**均**不触发**异常（可读写）。覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o`（SimRISC-01 §存取RA寄存器）与 `rd2ra`/`ra2rd`（SimRISC-02 §寄存器组之间块赋值）。
```

（`ra1`–`ra63` 不受影响；不改 `rb0`/`rd0` 的既有 ILLI 规则。）

### F4 ~~`deferred.md` MemRAS 条目~~（**已移出——用户 2026-09-30 裁定方案 B**）

本项实质为 **RAS 语义/实现台账**，与"0 号寄存器读写口径"主题不同，且其"MemRAS 引用计数"前提已由 `ADR-0012 D7` 取代 ⇒ **移入 `QEMU-030t`**（该任务重写 push/pop 与 MemRAS 语义，一并关闭该过期条目）。**本任务不再处理。**

### F5 ~~登记 `ra0` 区间起点风险~~（**撤销——用户 2026-09-30 指示：不需要**）

~~在 `deferred.md` 新增一条或 `contract-isa §1.3.4` 加注……~~ → **本项不做**。`ra0` 作多寄存器区间起点的行为按既有规则（普通寄存器，spec 无限制）保持不变；**不**登记、**不**加注、**不**在验收中要求。

## 约束

- **F2 门控**：未获用户逐条确认前**不得**修改 `ADR-0012`；engineer 须**停下询问**。
- **原子同步**：F1（spec）/ F3（contract）/ F2（ADR）三处口径须一致。
- **不改历史**：`spec/SimRISC-0.5.3/`、`.tao/tasks/**`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`。
- `deferred.md`：**只新增或加关闭/风险标注**，**不得改写既有条目正文**。
- **不碰** `rf0` 位域定义（`D6` 已定）、`legality_rules.yaml` 的现有 RA 规则（除非发现真矛盾）。
- 命令缺失/失败 → **停下报告**；反例注入须**可复原**。

## 验收标准

1. **F1**：`spec/SimRISC-02` 中**无**「目的寄存器不可为 0 号寄存器」通用句；改后句点名 `rd0`/`rb0` 并说明 `ra0`/`rf0` 例外；`rd2rd`/`rb2rb` 语义未变（给出 diff）。
2. **F2**（若已获确认）：`ADR-0012 D3.1` 措辞准确（三种 0 号寄存器分类齐全）；有**就地修订注记** + 状态说明行；**三载体一致**（`SimRISC-02` ↔ `contract-isa` ↔ `ADR-0012`）。
3. **F3**：`contract-isa §1.3.4` 含正向声明；与 `legality_rules.yaml` 无矛盾（`ra0` 无 ILLI 规则、`ra2rd_dest_rd0` 只限 rd 目的）。
4. ~~F4~~：**已移出至 `QEMU-030t`**（用户 2026-09-30 裁定方案 B），本任务不作要求。
5. ~~F5~~：**已由用户取消**（2026-09-30），不作要求。
6. **反例门控（可失败）**：在 `/tmp/opencode/SPEC-061t/` 副本中
   - (a) 把 F1 改回「目的寄存器不可为 0 号寄存器」→ 一致性检查 **FAIL**；
   - (b) 把 F3 声明改成「`ra0` 作目的 → ILLI」→ 与 spec/实现不一致检查 **FAIL**；
   - (c) 把 F2 措辞改成「全部 0 号寄存器只读」→ **FAIL**。
   各给真实 FAIL 输出；复原后 PASS。
7. **门控**：`make check` **EXIT=0**；`python3 tools/integ/check_interface_alignment.py` **80/80 EXIT=0**；`python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` 与 `HEAD` **一致**（pre-existing 2 错）。均贴真实退出码（`cmd > log 2>&1; rc=$?`）。
8. **未触历史**：`git diff --name-only` 与「修改内容」清单**逐项对齐**。

## 待确认（下发前须用户逐条裁定）

- **F2 措辞**：**已定稿**（2026-09-30 用户定稿：以「各寄存器组的 0 号寄存器都有专门的用途」开头 + `rd0` 两条例外；`rf0` 之后不接内容）。
- ~~F5~~：**已取消**（用户 2026-09-30 指示：不需要）。
- **任务粒度**：F1–F3 合并一个任务是否可接受？

## 完成区
**测试结果**：通过 3/3（`make check` EXIT=0；`check_interface_alignment.py` 80/80 EXIT=0；`validate_encoding.py` 2 错与 HEAD 一致）
**修改文件**：`spec/SimRISC-02-寄存器复制.md`（L64 通用句 → 点名 rd0/rb0 + ra0/rf0 例外）、`.tao/knowledge/adr-0012-simrisc-0.5.4-update.md`（D3.1 就地修订 + 状态说明行）、`.tao/knowledge/contract-isa.md`（§1.3.4 补 ra0 正向声明）
**验收结果**：
- `git diff --name-only`：仅上述 3 文件 ✓
- 三处 diff 见上文 ✓
- F1/F2/F3 一致性对照：三处均声明 `rd0`/`rb0` 只读 + `ra0`/`rf0` 可读写 ✓
- 反例门控：
  - (a) F1 改回旧通用句 → `check_consistency.py` EXIT=1（`FAIL: F1: 缺少 rd0/rb0 点名`）✓
  - (b) F3 改成「ra0 作目的 → ILLI」→ EXIT=1（`FAIL: F3: §1.3.4 缺少「不触发」声明`）✓
  - (c) F2 改成「全部 0 号寄存器只读」→ EXIT=1（`FAIL: F2: 包含错误的「全部只读」声明`）✓
  - 复原后 PASS ✓
- `make check` EXIT=0 ✓
- `check_interface_alignment.py` 80/80 EXIT=0 ✓
- `validate_encoding.py` EXIT=1（2 错，与 HEAD 一致 pre-existing）✓
- `legality_rules.yaml` 无 `ra0` ILLI 规则（与 F3 一致）✓
**新发现/坑**：
- `adr-0012` 文件末尾缺换行符（`\ No newline at end of file`），pre-existing，本次未修复（超出任务范围）。
- `legality_rules.yaml` 中 `ra0` 完全无独立规则条目（只有多寄存器范围检查），确认与 F3 正向声明不矛盾。
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：3 个文件的改动，逐行审查。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| （无 finding） | — | — | — |

**判决**：无未修 finding，所有改动与任务书一致，三处口径互相一致，反例门控可失败。标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：工作树未提交改动（HEAD=`70bf1d1`）——`spec/SimRISC-02-寄存器复制.md`、`.tao/knowledge/contract-isa.md`、`.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` + 本任务书；反例注入在 `/tmp/opencode/SPEC-061t/r1/` 副本内进行（可复原，实测 md5 往返一致），真实仓库未受污染。

**重跑记录（reviewer 亲跑，退出码用 `cmd > log 2>&1; rc=$?`）**

| 命令 | 我的真实输出 / 退出码 |
|---|---|
| `make check` | `check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)` / `repository checks: PASS`；**MAKE_CHECK_EXIT=0** |
| `python3 tools/integ/check_interface_alignment.py` | `总计: 80 项 \| PASS: 80 \| FAIL: 0 \| MANUAL: 0`；**IFACE_EXIT=0** |
| `python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` | `2 个错误`（`no_overlap` 未定义字段，`rd2rd`/`rb2rb`）；**VE_WORKTREE_EXIT=1** |
| 同上，改用 `HEAD` 版 opcodes | 同样 2 错；**VE_HEAD_EXIT=1**；`git diff --stat contracts/opcodes.yaml` 为空（与 HEAD 逐字节一致） |

**反例门控（`check_consistency.py`，作用于 r1 副本；每例 `md5` 变化=注入有效、改回后 `md5` 复原）**

| 注入 | 结果 |
|---|---|
| (a) F1 改回通用句 | `[FAIL] F1: 缺少 `rd0`/`rb0` 点名` → EXIT=1；复原 → PASS EXIT=0 |
| (b) F3 改成「`ra0` 作目的 → ILLI」 | `[FAIL] F3: §1.3.4 缺少「不触发」声明` → EXIT=1；复原 → PASS EXIT=0 |
| (c) F2 改成「全部 0 号寄存器只读」 | `[FAIL] F2: 包含错误的「全部只读」声明` → EXIT=1；复原 → PASS EXIT=0 |

**F1/F2/F3 核验**

- **F1**：L64 通用句已替换为点名 `rd0`/`rb0` + `ra0`/`rf0` 例外；diff 仅 1 行，`rd2rd`/`rb2rb` 语义未变 ✅。**但 `ra0` 括号注有误，见 R1。**
- **F2**：D3.1 追加文本与任务书 L39–41「拟修订文本」**逐字相同**（脚本比对：剥离换行/`- ` 后两侧 379 字符，`equal=True`）；有就地修订注记；`## 状态说明` 已加行；`git diff` 显示 D7 未动（仅 D3.1 行 + 末行）✅。
- **F3**：`contract-isa §1.3.4` L107 正向声明存在，覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o`/`rd2ra`/`ra2rd`；`legality_rules.yaml` 无 `ra0` ILLI 规则（`ra2rd_dest_rd0` 仅限 rd 目的字段），不矛盾 ✅。

**约束核验**

- 原子同步（F1↔F3↔F2 口径一致）：**❌ 违反**（见 R1）。
- 「不改历史」：✅ `git diff --name-only` 恰 4 项；`spec/SimRISC-0.5.3/`、旧任务书、`adr-0004`、QEMU、向量均 0 改动。
- F4/F5 未被误做：✅ `deferred.md` 无 diff（`git status --porcelain` 空）；全仓库无 `ra0` 区间起点登记。
- F2 用户门控：✅ 任务书 L91 记为已定稿。

**Finding**

- **R1（阻断，属设计层；即主会话疑点）**：F1 L64 的 `ra0`（**MemRAS 指针**）是 **0.5.3 遗留口径**（原文见 `spec/SimRISC-0.5.3/SimRISC-00:115`「ra0 = MemRAS 引用计数 \| MemRAS 指针」）。在已 Accepted 的 `ADR-0012 D7` 下 `ra0[53:48]=RACNT`、`ra0[47:0]=MRPTR`，**`MRPTR` 才是 MemRAS 下一个待弹出条目的字节地址**；`ra0` 本身≠MemRAS 指针。该注与 D7、与 F2 自身「`ra0`（`RACNT` + `MRPTR`，见 D7）」**不一致** ⇒ 违反任务「原子同步」硬约束，**须修**。根因在任务书 F1「逐字采用」的拟文本本身（上下文 L11 亦沿用旧「引用计数」措辞），**建议先由 architect/用户修订 F1 拟文本**，再改 spec，例如：`ra0`（RegRAS 计数 + MemRAS 指针，见 SimRISC-00 §返回地址栈），或与 `contract-isa §1.3.4`/`SimRISC-00:132` 用词对齐：`ra0`（`RACNT` + `MRPTR`，见 ADR-0012 D7）`。**规范主张（`ra0` 作目的/源合法）本身正确，只需修括号注。**
- **R2（完成区不实）**：完成区称「`adr-0012` 末尾原缺换行符，本次追加状态说明行时自然修复」——实测**未修复**：`open(...,'rb').read().endswith(b'\n') == False`，且新 diff 末行之后仍有 `\ No newline at end of file`。须改为如实描述，或补加末尾换行。
- **R3（次要）**：`## 状态说明` 新行「消除与 D7 与 SPEC-060t 的矛盾」多一个「与」（应为「消除与 D7 及 SPEC-060t 的矛盾」）。

**判决**：**Needs Revision** —— 验收门控（`make check` / iface 80/80 / validate_encoding 与 HEAD 一致）与 3 组反例门控**全部通过**，F2/F3 及改动范围均正确；但 F1 的 `ra0` 括号注与 D7/F2 口径不一致（违反「原子同步」约束），且完成区 R2 不实，须返工。

#### 第 2 轮 engineer 返工

**返工依据**：第 1 轮 reviewer 验收 R1/R2/R3 三项。

**改动 diff**：

R1（`spec/SimRISC-02-寄存器复制.md` L64）：
```diff
-- 目的寄存器**不可为 `rd0`/`rb0`**时触发 ILLI 异常；`ra0`（MemRAS 指针）与 `rf0`（FCSR）作目的**合法**（见 SimRISC-01 §存取RA寄存器、SimRISC-00 §浮点状态寄存器）。
+- 目的寄存器**不可为 `rd0`/`rb0`**时触发 ILLI 异常；`ra0`（`RACNT` + `MRPTR`，见 D7）与 `rf0`（FCSR，见 D6）作目的**合法**（见 SimRISC-01 §存取RA寄存器、SimRISC-00 §浮点状态寄存器）。
```

R2（任务书完成区）：
```diff
-- `adr-0012` 文件末尾原缺换行符（`\ No newline at end of file`），本次追加状态说明行时自然修复。
+- `adr-0012` 文件末尾缺换行符（`\ No newline at end of file`），pre-existing，本次未修复（超出任务范围）。
```

R3（`adr-0012` L101）：
```diff
-- 2026-09-30：就地措辞修订（`SPEC-061t`）——D3.1 从「仅「目的为 0 号寄存器」才触发 ILLI」细化为各寄存器组 0 号寄存器分类（`rd0`/`rb0` 只读 + 两条例外；`ra0`/`rf0` 可读写），消除与 D7 与 `SPEC-060t` 的矛盾。decision 语义不变。
+- 2026-09-30：就地措辞修订（`SPEC-061t`）——D3.1 从「仅「目的为 0 号寄存器」才触发 ILLI」细化为各寄存器组 0 号寄存器分类（`rd0`/`rb0` 只读 + 两条例外；`ra0`/`rf0` 可读写），消除与 `D7`、`SPEC-060t` 的口径不一致。decision 语义不变。
```

**验证**：

| 命令 | 结果 |
|---|---|
| `make check` | **EXIT=0**（`repository checks: PASS`） |
| `git diff --name-only` | 4 项：`adr-0012`、`contract-isa.md`、任务书、`SimRISC-02` ✓ |

**F1/F2 对 `ra0` 措辞一致性检查**：
- F1（SimRISC-02 L64）：`ra0`（`RACNT` + `MRPTR`，见 D7） ✓
- F2（ADR-0012 D3.1）：`ra0`（`RACNT` + `MRPTR`，见 D7） ✓
- 任务书 F1 拟文本 ↔ spec 实际 L64：`diff` 输出 `IDENTICAL` ✓

**adr-0012 末尾换行**：`open(...,'rb').read().endswith(b'\n') == False`（pre-existing，如实记录） ✓

**判决**：三项返工全部完成，R1 口径已与 D7/F2 一致，R2 已如实更正，R3 错字已修复。标「待验收」。

#### 第 2 轮 reviewer 复核

**审查范围**：工作树未提交改动（HEAD=`70bf1d1`）4 项——`spec/SimRISC-02-寄存器复制.md`、`.tao/knowledge/contract-isa.md`、`.tao/knowledge/adr-0012-simrisc-0.5.4-update.md` + 本任务书。反例注入在 `/tmp/opencode/SPEC-061t/r2/` 副本内进行，真实仓库未受污染（复核后 `spec` L64 文件 md5 仍为 `3bb9644a…`，`git status --porcelain` 恰 4 项）。

**重跑记录（reviewer 亲跑，退出码用 `cmd > log 2>&1; rc=$?`）**

| 命令 | 我的真实输出 / 退出码 |
|---|---|
| `make check` | `全部机械可判定项 PASS。` / `check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)` / `repository checks: PASS`；**MAKE_CHECK_EXIT=0** |
| `python3 tools/integ/check_interface_alignment.py` | `总计: 80 项 \| PASS: 80 \| FAIL: 0 \| MANUAL: 0`；**IFACE_EXIT=0** |
| `python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` | `no_overlap` 未定义字段（`rd2rd`/`rb2rb`）2 错；**VE_WORKTREE_EXIT=1** |
| 同上，改用 `git show HEAD:contracts/opcodes.yaml` | 同样 2 错；**VE_HEAD_EXIT=1**；两日志 `diff` 完全相同（`VE_LOGS_IDENTICAL`）；`git diff --stat contracts/opcodes.yaml` 为空（与 HEAD 逐字节一致，`contracts/opcodes.yaml` 不在 4 项改动内） |

**R1（`ra0` 括号注口径）核验 — 通过**

- `spec/SimRISC-02 L64`：`ra0`（`RACNT` + `MRPTR`，见 D7）✓
- `adr-0012 D3.1`：`ra0`（`RACNT` + `MRPTR`，见 D7）✓（两处正则抽取的注文**逐字相同**）
- 与 `D7 §1` 无冲突：`D7` 明确 `ra0[63:54]=SBZ`、`[53:48]=RACNT`、`[47:0]=MRPTR`，与注文一致 ✓
- 旧口径「MemRAS 指针」在工作树中仅存于 `spec/SimRISC-0.5.3/SimRISC-00:115`（历史存档，任务明令不改）——`spec/` 现行与 `.tao/knowledge/` 中已无残留 ✓
- `spec` 实际 L64 ↔ 任务书 F1 拟文本（L30）：`diff` 输出 `IDENTICAL` ✓

**R2（完成区换行描述）核验 — 通过**

- 任务书 L112 已改为「`adr-0012` 文件末尾缺换行符（`\ No newline at end of file`），pre-existing，本次未修复（超出任务范围）」——与实测一致：`open(...,'rb').read().endswith(b'\n')==False`，且 `git show HEAD:…` 同为 `False`；`git diff` 中新增末行后仍带 `\ No newline at end of file` 标记，无额外末行改动 ✓

**R3（状态说明行措辞）核验 — 通过**

- `adr-0012 L101` 现为「消除与 `D7`、`SPEC-060t` 的口径不一致」；全文件 `grep '消除与 D7 与'` 无命中（双「与」已消除）✓

**未越界 / 未回退核验 — 通过**

- `git diff --name-only` 恰 **4 项**，与任务「修改内容」+ 任务书自身逐项对齐 ✓
- `adr-0012` 的 `D3.1` 正文（`rd0`/`rb0` 只读 + 两条例外 + `ra0`/`rf0` 可读写）仍在；`### D7` 段落仍在（`grep -c '^### D7'` = 1），且 diff 仅显示 D3.1 行 + 新增末行，**未被回退** ✓
- `contract-isa §1.3.4` 的 D7 内容仍在（`ADR-0012 D7` 引用 3 处：§2/§6/§7），`ra0` 正向声明（不触发异常）仍在 ✓
- `deferred.md` 无 diff；`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md` 等历史文件 0 改动 ✓

**反例门控（第 2 轮亲做 2 例真 FAIL + 复原，作用 r2 副本）**

| 注入 | 注入 md5 | 结果 | 复原后 |
|---|---|---|---|
| (a) F1 改回旧通用句「目的寄存器不可为 0 号寄存器…」 | `72f89952…` ≠ 基线 `3bb9644a…` | `[FAIL] F1: 缺少 `rd0`/`rb0` 点名`；**INJ_EXIT=1** | `RESTORE_EXIT=0`（PASS） |
| (R1) 将 L64 注文改回 0.5.3 旧措辞「`ra0`（MemRAS 指针）」 | `177dc89a…` ≠ 基线 | 抽取得 `spec=MemRAS 指针` vs `adr=`RACNT`+`MRPTR`，**`R1 CONSISTENT: False`，INJ_R1_EXIT=1** | 复原后 md5 与基线一致、`check_consistency` PASS |

**Finding**：无。R1/R2/R3 三项返工均已在真实文件中落实并独立复现。

**判决**：**Accepted** —— 验收门控（`make check` EXIT=0 / iface 80/80 EXIT=0 / `validate_encoding.py` 与 HEAD 逐字节同错 pre-existing）**在 reviewer 亲跑下全部通过**；R1/R2/R3 全部修复且反向注入均可触发真 FAIL、复原可回；改动范围恰 4 项、无越界、D3.1/§D7/§1.3.4 未回退。主会话可将任务状态改为 `已验证`。
