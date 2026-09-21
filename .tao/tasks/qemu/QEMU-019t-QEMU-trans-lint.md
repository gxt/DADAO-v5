# QEMU-019t: QEMU trans lint

**模块**：qemu
**项目里程碑**：M1
**依赖**：`SPEC-003t`、`QEMU-013t`
**状态**：待开始
> **ADR-0010 D2/D3 修订（2026-09-19）**：本任务需适配 `translate.c` 拆分后的路径——grep `insn_trans/trans_*.c.inc`（而非仅 `translate.c`），对齐 D2 的 10 文件结构。

## 执行环境

**执行环境**：本地

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — 命名由 `insn` 派生，复用 `validate_decodetree.py`（DRY）**：
- 真实 `trans_*` 名由 **`insn`** 派生，**非** mnemonic：`add.uo-rd` → `trans_add_uo_rd`、`br.z-rd` → `trans_br_z_rd`、`ld.o-rd` → `trans_ld_o_rd`、`add.sb` → `trans_add_sb`
- 任务书原文举的 `trans_add_uo`/`trans_br_z`/`trans_ld_o` **实测均不存在**（旧文本据此写的算法已废）
- **复用** `tools/qemu/validate_decodetree.py` 的 `sanitize_name()` + `build_unique_func_names()`（insn 派生；同名多条追加 `_{format}` 后缀），**不要**另造 mnemonic 方案

**P2 — 匹配「函数定义」而非子串（避前缀碰撞）**：
- mnemonic 前缀 grep 有 **2 例误匹配**：`br.n` 会命中 `trans_br_nn_rd`/`trans_br_ne_rd`/`trans_br_np_rd`；`cs.n` 会命中 `trans_cs_ne_rd`/`trans_cs_ne_rf` → 可能**掩盖缺失**
- 须按**定义**匹配（如 `trans_<name>\s*\(` 或「`static bool trans_<name>(`」），并对函数名做**精确**（非前缀）比较

**P3 — 计数单位与范围（用户裁定）**：按 **insn**（256 条）统计并报告 **`256/256`**；**同时**额外报告 **M1 子集 `178/178`**（`excluded_m1` 78 条另计）。

**P4 — 实测基线（预期结果）**：源树 `insn_trans/*.c.inc` + `translate.c` 共定义 **256 个** `trans_*`，与 256 条 insn **一一对应**，**0 缺失、0 多余**；`swym`/`illi` **也有** `trans_swym`/`trans_illi`（旧文本「MISC 可能无独立 trans」在 v5 **不成立**）。

**P5 — 反例门控（强制，AGENTS.md）**：真实数据 0 缺失 ⇒ lint 永远只报 `256/256`，**无法证明它能失败**。故：
- 脚本须支持**覆盖输入源路径**（如 `--patches <dir>` / `--src <dir>`），以便在 `/tmp/opencode/QEMU-019t/` 的副本上注入反例
- 必须给出「注入 1 条缺失（如把某 patch 里的 `trans_add_sb` 改名）→ 报 MISSING 且 `--strict` exit 1；还原 → 恢复 `256/256`」的**真实输出**

**P6 — 验收归因过时**：验收 #4 的 BLOCKED 归因「需 `007t` 拆分完成后才有 `insn_trans/`」**已过时**（`007t` 已完成）→ 现在可跑。


## 接口规范

- 输入：
  - `contracts/opcodes.yaml`（M1 mnemonic 列表）
  - `components/qemu/patches/*.patch`（QEMU trans 函数来源）
- 输出：`tools/qemu/check_qemu_trans.py`：每条 insn 是否有 `trans_<insn 派生名>` 的**定义**（lint，默认 exit 0）
- 约束：
  - lint 不是 gate：默认 exit 0；`--strict` 时缺失项致 exit 1
  - **命名由 `insn` 派生**（复用 `validate_decodetree.py` 的 `sanitize_name()`/`build_unique_func_names()`）；**匹配函数定义**（非子串）
  - 计数：报 `256/256`（全部 insn）+ `178/178`（M1 子集）
  - 支持 `--src <dir>` / `--patches <dir>` 覆盖输入源（供反例门控用）
  - 只读 `contracts/opcodes.yaml` 与 patch/源树，**不改**组件源码
  - 脚本放 `tools/qemu/`

## 背景（完整）

### 目标

验证 `components/qemu/patches/` 中每条 M1 opcode 都有 `trans_<mnemonic>` 实现——缺失会走 ILLI stub 导致测试静默失败，目前只能人工逐个检查。

### 设计理由

翻译链里「QEMU trans 覆盖」此前靠人眼检查，容易漏。机械化为 lint，才能让 trans 缺失可见。

### 关键概念 / 数据

**`check_qemu_trans.py` 逻辑**：

1. 读 `contracts/opcodes.yaml`，取全部 256 条记录（并标记 `excluded_m1` 以区分 M1 子集）
2. 用 `validate_decodetree.build_unique_func_names()` 由 **`insn`** 派生每条记录的 `trans_*` 名
3. 在源（`components/qemu/patches/*.patch`，含 `translate.c` 与 `insn_trans/trans_*.c.inc`）中按**函数定义**匹配（精确名 + 词边界）
4. 收集缺失项，输出 MISSING 明细
5. 打印 `check_qemu_trans: 256/256 insns have trans impl (M1 178/178)`
6. 默认 exit 0；`--strict` 且存在缺失时 exit 1

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-023a-issue-registry-trans-lint.md`（trans lint 部分）
- DADAO-0628：`scripts/check_qemu_trans.py`（形态参考，禁止复制正文）

## 交付物

- `tools/qemu/check_qemu_trans.py`：trans 函数**定义**存在性 lint（insn 派生命名，复用 `validate_decodetree.py` 的命名函数）
- 完成区附：真实 stdout（`256/256` + `178/178`）、**反例门控真实输出**（注入缺失 → MISSING + `--strict` exit 1；还原 → 恢复）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **MISC 映射表重建**：0.5.3 没有 `MISC-Norm`，改为主表 + octa/tetra/wyde/byte/RF/AMO 子表体系。
2. **助记符全面变化**：`unimp`→`illi`、`setzw`→`set.zw`、`orw`→`or.w`、`brn`→`br.n`、`muls`→`mul.so` 等；trans 函数命名以 `QEMU-013t` 实际实现为准核对。
3. **trans 源码路径**：v5 以 `components/qemu/patches/*.patch` 为准；拆分后 `trans_*` 函数分布在 `insn_trans/trans_*.c.inc` 中（ADR-0010 D2），lint 须同时覆盖 `translate.c` 和 `insn_trans/trans_*.c.inc`（patch 文件内即含这些新增文件的内容）。
4. **脚本目录**：`scripts/` → `tools/qemu/`。

## 已知坑 / 结论

1. **trans lint 非阻断**：默认 exit 0，仅 lint 警告；`--strict` 才 exit 1。MISC 特殊指令（`swym`/`illi` 等）可能无独立 trans，属预期缺失。
2. ~~**mnemonic 标准化**~~ **【已订正】**：命名由 **`insn`** 派生（非 mnemonic）——`sanitize_name(insn)` 把非字母数字替换为 `_`，同名多条追加 `_{format}` 后缀（见 `validate_decodetree.py` 的 `build_unique_func_names()`）。例：`add.uo-rd`→`add_uo_rd`、`br.z-rd`→`br_z_rd`、`ld.o-rd`→`ld_o_rd`、`add.sb`→`add_sb`。**实测：256/256 一一对应、0 缺失**。
3. **硬编码映射表易漂移**：**已解决**——直接从 `opcodes.yaml` 的 `insn` + 复用 `validate_decodetree.py` 的命名函数推导，**零硬编码**。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-023a-issue-registry-trans-lint.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_qemu_trans.py`
- 本项目：`contracts/opcodes.yaml`、`components/qemu/patches/`、`.tao/knowledge/contract-isa.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `python3 tools/qemu/check_qemu_trans.py` 输出 `256/256`（并附 M1 `178/178`）与 MISSING 明细，默认 exit 0 | 现在可跑 | 实测基线：256/256、0 缺失 |
| 2 | `--strict` 时**存在缺失**则 exit 1；无缺失时 exit 0 | 现在可跑 | 真实数据 0 缺失 → 须靠**注入反例**证明 exit 1 可达 |
| 3 | 脚本只读 `opcodes.yaml` 与 patch/源树，不改组件源码 | 现在可跑 | `git status` 核对 |
| 4 | 脚本适配 `insn_trans/trans_*.c.inc`（拆分后路径） | **现在可跑** | 原归因「需 `007t`」**已过时**（`007t` 已完成，`insn_trans/` 已存在） |
| 5 | 完成区粘贴真实 stdout | 现在可跑 | |
| 6 | **命名由 `insn` 派生并复用 `validate_decodetree.py`**，**匹配函数定义**（精确名/词边界，避 `br.n`↔`br.nn` 类前缀碰撞） | 现在可跑 | 代码审查 + 实测：不得出现「`br.n` 靠 `trans_br_nn_rd` 误判为存在」 |
| 7 | **反例门控（强制）**：在 `/tmp/opencode/QEMU-019t/` 副本上注入 1 条缺失（改名某 `trans_*`）→ 报 MISSING 且 `--strict` **exit 1**；还原 → 恢复 `256/256` 且 exit 0 | 现在可跑 | 须附真实输出 + 还原证据（`git diff`/`git status`） |
| 8 | **前缀碰撞门控**：构造「`br.n` 缺失但 `trans_br_nn_rd` 存在」的副本 → 必须报 `br_n_rd` **MISSING**（不得被 `br.nn` 误判为存在） | 现在可跑 | 证明匹配是精确/词边界而非前缀 |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
