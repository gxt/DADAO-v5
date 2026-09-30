# QEMU-030t: RAS 压/弹栈重写（ADR-0012 D7）+ MemRAS 台账关闭

**模块**：qemu
**项目里程碑**：M2（**本任务推翻 M1 已验收的 RA 行为**）
**依赖**：`ADR-0012 D7`（已固化）；`SPEC-062t`（规范基线，**须先定稿**）
**状态**：待开始（**未下发**）

## 目标

### 1. 按 `ADR-0012 D7` 重写 RAS 压/弹栈实现

文件：`components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`（`gen_ras_push` / `gen_ras_pop`）

| 项 | 要求 |
|---|---|
| **`ra0` 布局** | `[63:54]` SBZ；`[53:48]` = **`RACNT`**（RegRAS 有效条目数 0–63）；`[47:0]` = **`MRPTR`**（MemRAS 下一个待弹出条目的字节地址；0 = 未启用）。**删除**原 `ra0` 高 16 位 MemRAS 计数的一切读写 |
| **有效性判据** | 只用 `RACNT`，**不再**逐条检查 `ra[i]` 高 16 位 |
| **压栈** | D7 §3 的 **C1 / C2（递归折叠优先，含 `< 0xFFFF` 守卫）/ C3a / C3b** 全部实现；C3b = `MRPTR−=8` → 写入**栈底**条目 → 压入新条目 ⇒ `RACNT` 保持 63；`MRPTR == 0` → **RASOF** |
| **弹栈** | D7 §4 的 **D1 / D2 / D3 / D4a / D4b** 全部实现；D4b 读 `MRPTR` 处条目**先判定**（0→RASUF / 1→返回地址 / >1→入栈且计数−1），**判定通过后**才 `MRPTR += 8` |
| **精确异常** | **先完成全部 `RASOF`/`RASUF` 判定**（含 D4b 的读取与内容判定），再作任何 RA 寄存器/内存修改；fault 时 RA 与内存原状 |
| **环形实现（性能）** | 用**隐藏基准索引**（非架构字段，如 `CPUDADAOState.ras_base`）避免压/弹栈的数据搬移；`RACNT` 为唯一有效性依据 |
| **视图一致（关键）** | `ra_i` 为软件可见 ⇒ 下列路径**必须**按基准索引换算：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`（`trans_mem.c.inc`）、`rd2ra`/`ra2rd`（`trans_block.c.inc`）、以及 `cpu_dump_state`（`cpu.c.patch` 的 `RA[%02d]` dump）。否则 `info registers`/`-d cpu` 与架构视图不一致 |

> 补丁的 `index` blob hash 须同步（先例 `QEMU-029t`）。

### 2. 探针更新（覆盖全部分支）

- 更新 `tools/qemu/min_rom_probe_013t.py`（MemRAS 计数相关用例必改），或新增 `tools/qemu/min_rom_probe_030t.py`（推荐新文件，保留 013t 历史）。
- 覆盖：**C1 / C2 / C3a / C3b**、**D1 / D2 / D3 / D4a / D4b**、RASOF/RASUF 的**精确异常**（fault 时 `ra`/内存未变）、**环形跨边界**（`RACNT` 满/空往复）、`RACNT`/`MRPTR` **回读校验**、软件写坏 `ra63`（递归计数=0）→ D1 的 RASUF。

### 3. F4（由 `SPEC-061t` 移入）：关闭 `deferred.md` 过期条目

- 核实条目所述"MemRAS 路径未实现"**已被 `QEMU-013t` 补齐**（给出代码/探针证据）；
- 在该条目**末尾加注关闭**：「**已关闭**（2026-09-30 核实）：`QEMU-013t` 已实现；其"MemRAS 引用计数"语义已由 `ADR-0012 D7` 取代（见 `QEMU-030t`）」；
- **不改写既有正文**（`git diff` 证据）。

## 约束

- **不改** `tests/vectors/**`（另开 `TESTCASES-020t`）；**不改** `spec/`、`contracts/`（另见 `SPEC-062t`）。
- 构建提醒：需 `make prepare` + **`make build-qemu`（预计 5–20 分钟）**——执行前确认。
- **还原须包含重建**（源码还原 ≠ 二进制还原）；反例注入须可复原。
- 命令缺失/失败 → **停下报告**。
- **跨任务影响须登记**：`TESTCASES-020t` 完成前，`ctrl-call.yaml`/`ctrl-ret.yaml` 与实现**不一致**（旧语义期望值），须在完成区明确，不得据此判 PASS。

## 验收标准

1. **分支落位表**：D7 §3/§4 的每个分支 ↔ 代码位置逐条对照（C1–C3b、D1–D4b 共 9 条，无遗漏）。
2. **无残留**：`grep -n "hi16\|0xFFFF" trans_ctrl.c.inc.patch` 中与 MemRAS 计数相关者清零（`RACNT` 的 `0xFFFF` 守卫保留）；`grep` 原始移位循环（`for (i = 2..63)` / `for (i = 62..1)`）**已删除**（环形实现）。
3. **探针**：全部用例 PASS，且**每类断言有可达 FAIL 路径**——对至少 4 类注入（如 C3b 的 `RACNT` 处理、D1 的 RASUF、D4b 的 `MRPTR += 8` 时机、环形基准索引）给出**真实 FAIL 输出** + 复原（含重建）证据。
4. **精确异常**：RASOF/RASUF 触发时 `-d cpu` 实测 `ra`/内存未变。
5. **视图一致**：`info registers`/`-d cpu` 的 RA dump 与软件读（`ra2rd`）一致（给出 README/脚本证据）。
6. **F4**：`deferred.md` 条目加注关闭、既有正文逐字未改。
7. **门控**：`make build-qemu` PASS；`make check` EXIT=0；`python3 tools/qemu/check_qemu_trans.py --strict`（253/253）；`python3 tools/integ/check_interface_alignment.py` 80/80 EXIT=0。均贴真实退出码。
8. `git diff --name-only` 与清单逐项对齐（含 `deferred.md`）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
