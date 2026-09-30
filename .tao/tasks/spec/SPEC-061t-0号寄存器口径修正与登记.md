# SPEC-061t: 0 号寄存器口径修正（`ra0` 可读写）+ 相关措辞与登记

**模块**：spec（含 `.tao/knowledge/`）
**项目里程碑**：M1→M2
**依赖**：用户裁定（2026-09-30：建任务；**先不执行**）
**状态**：待开始（**未下发**）
**前置**：**F2 涉及已 Accepted 的 `ADR-0012 D3.1`，其修订措辞须经用户逐条确认后方可写入**（AGENTS「ADR decision 逐条确认」）

## 背景（`ra0` 读写口径分析结论）

**事实**：`ra0` 的读、写在各层均**合法**，且三层一致——`SimRISC-01:153`「`raHA` 为 `ra0` 时不触发异常（**ra0 可读写**）」；`legality_rules.yaml` **无** `ra_dest_ra0`（对照 `rd0`/`rb0` 有显式 ILLI）；QEMU 六条路径（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd`）均明确允许 `ra0`；`min_rom_probe_013t.py` 的 R1/X1–X3 覆盖 `ra0` 写入（MemRAS 启用/溢出/下溢/精确异常）。这是**有意设计**：`ra0` = MemRAS 指针（低48）+ 引用计数（高16），软件须在进程入口设置、OS 须在进程切换时保存恢复。

但查出 **5 处口径问题**（F1/F2 为**实质错误**）：

| # | 问题 | 证据 |
|---|---|---|
| **F1** | `spec/SimRISC-02-寄存器复制.md` L64 通用句「**目的寄存器不可为 0 号寄存器**时触发 ILLI（`rdHB` 不可为 `rd0`，`rbHB` 不可为 `rb0`）」与**同节**例外冲突：`rd2ra` 目的 `ra0` 合法、`rd2rf` 目的 `rf0` 合法（`SPEC-060t` 刚加的注） | 本句 + 同段 `rd2rf` 注 |
| **F2** | `ADR-0012 D3.1`「**仅**「**目的**为 **0 号寄存器**」才触发 ILLI」**过度概括**——`ra0`/`rf0` 作目的均**合法**（`rf0` 见 `D6`） | `adr-0012` D3.1；根因是 `ADR-0015` 概括「每组寄存器的 0 号寄存器只读」只对 `rd0`/`rb0` 成立 |
| **F3** | 合同层**缺正向声明**：`legality_rules.yaml` 对 `ra0` 只有多寄存器规则；`contract-isa §1.3.4` 只描述位域，未写「可读写」 | `legality_rules.yaml` L109–130；`contract-isa.md` L87–103 |
| **F4** | `deferred.md` 的「MemRAS 路径未实现……归属 `QEMU-013t`」条目**无关闭标注**，但 `QEMU-013t` 已补全 MemRAS | `trans_ctrl.c.inc.patch`（`ra0 low48 != 0` spill/restore 分支）+ 探针 R1/X1–X3 + changelog 2026-09-21 |
| **F5** | `ra0` 可作多寄存器区间**起点**（`ldm.o {ra0:ra0+immu6-1}`、`rd2ra {ra0:...}`）——会连带改写 MemRAS 指针与 RegRAS 条目（合法但危险，spec 未限制） | `spec/SimRISC-01 §存取RA寄存器`、`SimRISC-02 §寄存器组之间块赋值` |

## 修改内容

### F1 `spec/SimRISC-02-寄存器复制.md`（L64 通用句）

改为（逐字采用）：

```
- 目的寄存器**不可为 `rd0`/`rb0`**时触发 ILLI 异常；`ra0`（MemRAS 指针）与 `rf0`（FCSR）作目的**合法**（见 SimRISC-01 §存取RA寄存器、SimRISC-00 §浮点状态寄存器）。
```

> 注：**只为消除矛盾**，不改 `rd2rd`/`rb2rb` 等既有规则的语义（`rdHB`/`rbHB` 不可为 0 号的行为不变）。

### F2 `ADR-0012 D3.1` 就地修订（**待用户逐条确认后才能改**）

拟修订为：明确「**0 号寄存器并非统一只读**：`rd0`（恒 0）/`rb0`（当前指令地址）**只读**，作**目的** → ILLI；`ra0`（MemRAS 指针，低48/高16）与 `rf0`（FCSR，见 D6）**可读写**，各有专属语义」。→ 加**就地修订注记** + `## 状态说明` 追加一行（体例同 `SPEC-058t`）。

> **engineer 注意**：未经用户逐条确认**不得**动本项；先停下询问。确认后由主会话把最终措辞写死进本任务书（见「待确认」节）。

### F3 `contract-isa.md §1.3.4`（补正向声明）

在 `ra0` 说明后新增：

```
- `ra0` 作**目的**或**源**均**不触发**异常（可读写）。覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o`（SimRISC-01 §存取RA寄存器）与 `rd2ra`/`ra2rd`（SimRISC-02 §寄存器组之间块赋值）。
```

（`ra1`–`ra63` 不受影响；不改 `rb0`/`rd0` 的既有 ILLI 规则。）

### F4 `deferred.md` MemRAS 条目

**先核实**（读取 `trans_ctrl.c.inc.patch` 的 `gen_ras_push`/`gen_ras_pop` 是否含 `ra0 low48 != 0` 的 spill/restore + 计数溢出/下溢分支，并对照探针 R1/X1–X3）；核实为**已实现**后，在该条目**末尾加关闭标注**（如「**已关闭**（2026-09-30 核实）：`QEMU-013t` 已实现……依据：……」，**不改写既有正文**）。

### F5 登记 `ra0` 区间起点风险

在 `deferred.md` **新增一条**（不改既有条目）或 `contract-isa §1.3.4` 加注：说明「`ra0` 作多寄存器区间起点**被允许**（语义即普通寄存器）」，并登记潜在风险（M2 若需保护另议）。

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
4. **F4**：**核实证据**（QEMU 代码片段 + 探针用例）已贴；条目加关闭标注且**既有正文逐字未改**（`git diff` 证据）。
5. **F5**：风险已登记（新条目，不改既有）。
6. **反例门控（可失败）**：在 `/tmp/opencode/SPEC-061t/` 副本中
   - (a) 把 F1 改回「目的寄存器不可为 0 号寄存器」→ 一致性检查 **FAIL**；
   - (b) 把 F3 声明改成「`ra0` 作目的 → ILLI」→ 与 spec/实现不一致检查 **FAIL**；
   - (c) 把 F2 措辞改成「全部 0 号寄存器只读」→ **FAIL**。
   各给真实 FAIL 输出；复原后 PASS。
7. **门控**：`make check` **EXIT=0**；`python3 tools/integ/check_interface_alignment.py` **80/80 EXIT=0**；`python3 tools/spec/validate_encoding.py contracts/opcodes.yaml` 与 `HEAD` **一致**（pre-existing 2 错）。均贴真实退出码（`cmd > log 2>&1; rc=$?`）。
8. **未触历史**：`git diff --name-only` 与「修改内容」清单**逐项对齐**。

## 待确认（下发前须用户逐条裁定）

- **F2 措辞**：上文拟修订文本是否可行？（这是已 Accepted 的 `ADR-0012 D3.1` 的措辞修订，须逐条确认）
- **F5 落点**：登记到 `deferred.md`（新增条目）还是 `contract-isa §1.3.4`（加注）？
- **任务粒度**：F1–F5 合并一个任务是否可接受？（若你希望 F2 单列，可拆分）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
