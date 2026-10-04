# SPEC-093t: 上游 ↔ v5 偏离台账（MEMORY.md 新增节）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 目标

在 `.tao/knowledge/MEMORY.md` 新增一节 **「上游 ↔ v5 偏离台账」**，收录 **6 项**上游 spec 与 v5 决策之间的**规范性偏离**，每项给出：偏离点、上游依据、v5 决策、**ADR 指针**、影响/状态。作为 M2 门槛⑤的交付物，使 M3 codegen 的实现者能一眼看到「哪些地方 v5 ≠ 上游」。

## 背景与现状（实测）

- 该台账来源与建议清单见 `docs/m2-spec-planning.md §3 第 3 层` 与 `§4.2`（讨论稿）。
- v5 的偏离均已由 **已 Accepted 的 ADR** 固化，本任务只做**归一化登记 + 指针**，**不新增决策**。
- `.tao/knowledge/MEMORY.md` 现状：`## 当前进度`（大表）+ `## 关键目录速查` + `## 重要决策` + `## 如何参考…` 等节。新增节须不破坏既有表格。

## 交付物

`.tao/knowledge/MEMORY.md` 新增节 **`## 上游 ↔ v5 偏离台账`**（建议置于 `## 关键目录速查` 之前或 `## 重要决策` 之后，择一不影响既有表格），含 6 项（表格或列表，逐项）：

| # | 偏离点 | 上游依据 | v5 决策 | ADR 指针 |
|---|--------|----------|---------|----------|
| 1 | **exit port（程序停机）** | `SimRISC-04 §退出指令`：`escape cfx_<name>, imms18`（退出特权态，非停机） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠性补全） |
| 2 | **`fence` SBZ 非零** | `SimRISC-04 §fence`：`bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1） |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2` 仅给地址空间模型，无内存映射/复位值全集/exit 协议） | 采用 spec **核内地址空间模型**（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；确定复位 `rd0`/`rf0`/RF 全 0 | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`：`ra0` 高 16 位含 **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段） |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-03`）、特权 cfx（`DADAO-12/13`）、LR-SC（`SimRISC-12`）、`fence` 均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 60 条已实现（不再是 ILLI）**；`excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence excluded）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`） |

> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。

## 约束

- **不臆造**：第 1–6 项的 ADR 指针、decision 编号、spec 章节**必须逐一实测核对**（`grep` ADR 文件确认 `D1`/`D3`/`D7`/`D5.3` 等真实存在，且 ADR 状态 `Accepted`）；表述与 ADR 原文一致，不新增/改写决策。
- **纯登记**：不新增 ADR、不改任何 `spec/`/`contracts/`/`tools/`；只往 `MEMORY.md` **追加**一节（不改写既有行/表）。
- 格式：新增节不得破坏 `MEMORY.md` 既有 markdown 表格（表内无空行、无连续空行、文件尾无空行）。
- 术语一致：`scope`、`RACNT`、`MRPTR`、exit 码等用与 `contracts/opcodes.yaml`/ADR 一致的写法。
- ADR 提醒：本任务为**登记已 Accepted 决策**，**不立新 ADR**。

## 验收标准

1. `MEMORY.md` 含新节 `## 上游 ↔ v5 偏离台账`，**恰好 6 项**，覆盖：exit port / fence SBZ / 测试机地址映射+复位值 / `ra0`(MemRAS) / `e_flags` / M1-M2 排除口径。
2. 每项含：偏离点、上游依据、v5 决策、**ADR 指针**（文件 + decision 编号）；6 项的 ADR 指针经实测**全部可定位**（独立复算：`grep` 到对应 decision 且 ADR `Accepted`）。
3. 第 6 项**已订正**为「浮点已实现、不再 ILLI；余 cfx/LR-SC/fence 仍 ILLI」，与 `contracts/opcodes.yaml`（`scope` 分区 152/60/15）一致。
4. `MEMORY.md` 既有表格未被破坏（`git diff` 只新增节；表格行/列完好；无表内空行、无文件尾空行）。
5. 纯文档改动：以 `git status`（仅 `MEMORY.md`）目视 +（如适用）`make check-no-residue` 为准。
6. **反例门控**：一键证据脚本内置「注入反例→预期 FAIL→还原→预期回绿」（如把某项 ADR 指针改成不存在的编号 → 自检 FAIL），并在完成区给出真实输出与退出码。

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
