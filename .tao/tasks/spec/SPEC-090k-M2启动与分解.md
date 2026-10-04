# SPEC-090k: M2（规范与接口冻结）启动与任务分解

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题根源

M1 已达成（2026-10-03 归档至 `.tao/archive/M1/`）。用户 2026-10-04 裁定：**M2 重定义为「规范与接口冻结（Normative Freeze）」**，原「Basic CodeGen」顺延为 **M3**；**取消「过渡期任务 `M<i>→M<i+1>`」类别**，原 `M1→M2` 任务一律提升为 `M2`（现 **138** 个 M2 任务，其中 **131 已验证 / 5 待开始 / 2 里程碑**）。同期主会话已同步 `milestones.md`、`.tao/README.md`（新 M2/M3 定义、取消过渡期类别）。

M2 的目标是把三层做到**机械一致**：`spec/`（0.5.4，内容层）→ 投影（`contracts/*` 机器数据、`.tao/knowledge/contract-*.md` 叙述合约）→ checker（`make check`），并让 FP **实现侧**收口、偏离台账成型，从而为 M3 codegen 提供稳定契约。

当前 M2 收口只剩零散项，且缺少一份**统一的启动/分解书**把它们纳入同一条依赖链、明确「完成」判据（门槛）。此外，5 个早期创建的 `待开始` 任务其前提多已被 `SPEC-084t`/`085t`、`INFRA-026t`/`027t`、`SPEC-086t`~`089t` 等覆盖或部分覆盖，需逐一核实并处置。

## 目的

1. 冻结 **M2 门槛（5 条）** 为可验收判据（见下）；
2. 把 M2 剩余任务（投影缺口、偏离台账、最小 FP smoke、文档/引用收尾、归档）编成一条依赖链，标清交付物与依赖；
3. 核验 5 个 `待开始` 旧任务，给出处置（关闭 / 改范围 / 保留）及实测依据。

## M2 门槛（完成的 5 条判据；取自 `.tao/knowledge/milestones.md`）

1. **`make check` 全绿**（所有 checker + 反例门控）；
2. **投影表「缺口」清零或显式 deferred**（`spec/README.md` 4 项：`contract-asm` / `contract-sbi` / `contract-exception` / `contract-mmu`）；
3. **`spec_cite` / 引用 / 计数全对齐**；
4. **FP = 执行层 60/60 + `dst_rd0@FP` + 最小 FP smoke**；
5. **偏离台账 6 项**（落点 `.tao/knowledge/MEMORY.md` 新增节）。

> **FP 边界**（用户裁定）：M2 **含**执行层 60/60 + `dst_rd0@FP` + 最小 smoke；**不含** FP 独立 oracle（`GOLDEN-*`）/ FP 向量（`TESTCASES-024t`）/ 完整语义 E2E（→ M3）。
> **偏离台账 6 项**：① exit port（vs 上游 `escape`）；② `fence` SBZ→ILLI；③ 测试机地址映射/复位值；④ `ra0=0`（MemRAS 简化）；⑤ `e_flags` 版本字段；⑥ M1 排除口径（**订正**：浮点已实现、不再 ILLI，余 cfx / LR-SC / fence 仍 ILLI）。

## 对照关系

- **里程碑定义**：`.tao/knowledge/milestones.md`（M2 = 规范与接口冻结；M3 = Basic CodeGen）。
- **候选工作清单**：`docs/m2-spec-planning.md`（N1–N16 映射、三层结构、偏离台账建议）。本 k **不**照单全收：M2 只收口「归一化 + checker + 偏离台账 + FP 实现侧」，其余（新写 ISA 规范等）不在 M2。该文件的 §6/§7-8「不采纳」标记为历史，不改写。
- **参考实现**：`DADAO-0628` 的规范归一（只读溯源，非执行依赖）。
- **经验输入**：`.tao/archive/M1/m1-retrospective.md`（M1 遗留/风险）、`.tao/knowledge/lessons.md`、`.tao/knowledge/issues.yaml`。

## 任务分解

| 编号 | 任务 | 模块 | 交付物 | 依赖 |
|------|------|------|--------|------|
| `SPEC-091t` | `contract-asm.md` 汇编语言叙述合约（清投影缺口①） | spec | `.tao/knowledge/contract-asm.md` + `spec/README.md`/`Process-02` 同步 | 无 |
| `SPEC-092t` | 系统层投影缺口显式 deferred（缺口②③④） | spec | `spec/README.md` 投影表 + `Process-02` 登记 deferred | `SPEC-091t` |
| `SPEC-093t` | 上游↔v5 偏离台账（门槛⑤） | spec | `.tao/knowledge/MEMORY.md` 新增节（6 项 + ADR 指针） | 无 |
| `SPEC-094t` | `check-spec-refs` 历史违规消解（门槛③，**已裁定纳入 M2**） | spec | `contract-*.md` 引用修正 / 排除 / deferred → Check1/Check2 = 0 | `SPEC-091t` |
| `SPEC-030t` | `contract-isa.md` 附录 A 断表空行修复（**改范围**） | spec | `.tao/knowledge/contract-isa.md` | 无 |
| `SPEC-033t` | contract-abi 引用修正（**改范围**：仅 `contract-abi.md`） | spec | `.tao/knowledge/contract-abi.md` | 无 |
| `TESTCASES-014t` | 向量/生成器 `spec_cite` 收尾（**改范围**：仅规则引用） | testcases | `tools/testcases/generate_isa_vectors.py` + 重生成向量 | 无 |
| `INTEG-009t` | 最小 FP E2E smoke（门槛④） | integ | `tests/e2e/smoke_fp.s` + `tests/lit/E2E/smoke_fp.test` + 期望值派生说明 | 无 |
| `INTEG-010t` | M2 归档与回顾（收尾，M2 达成后执行） | integ | `.tao/archive/M2/`（`README.md`/`m2-retrospective.md`/`issues-closed.md`）+ 各台账指针 | 全部 M2 任务 |

- **依赖关系**：
  - `SPEC-091t → SPEC-092t`（两者同改 `spec/README.md` 投影表与 `Process-02` 合约清单，按 `AGENTS.md`「同改共享文件一律串行」串行）。
  - `SPEC-093t`、`SPEC-030t`、`SPEC-033t`、`TESTCASES-014t`、`INTEG-009t` 互不共享文件，可并行（受并行上限约束）。
  - `INTEG-010t` 依赖 **所有 M2 任务均已终态**（`已验证`）。
- **分解理由**：按门槛收口——② 由 `SPEC-091t`（写 asm 合约）+ `SPEC-092t`（三缺口登记 deferred）；③ 由 `SPEC-030t`（`contract-isa` 断表空行）+ `SPEC-033t` + `TESTCASES-014t`（`SPEC-032t` 已由前置消解、`LLVM-016t` 已覆盖）；④ 由 `INTEG-009t`；⑤ 由 `SPEC-093t`；①/归档由 `INTEG-010t`。
- **k↔m**：本 k 对应项目里程碑 **M2**（各模块 M2 `m` 标记在其模块任务收敛时核验；M2 项目里程碑的置「达成」由主会话在依赖的模块 `m` 均达成后执行）。

## 5 个「待开始」旧任务处置（2026-10-04 实测）

| 任务 | 处置 | 实测依据（命令/读文件） |
|------|------|--------------------------|
| `LLVM-016t` | **关闭→删除任务书**（已被 `SPEC-085t`/`INFRA-027t` 覆盖） | `gen_asm_list.py:133/462/643` 已直接用 `entry["id"]`（无重算）；产物已迁 `.tao/knowledge/contract-asm-list.md`（header `227 条 = M1 152 + fp 60 + excluded 15`、id 无重复）；`make check-asm-list-drift` → `PASS (byte-identical)` |
| `SPEC-030t` | **改范围** | `docs/README.md:17` 已完成（现为当前口径 `227`）；**剩余有效项**：`contract-isa.md:1416` 空行使附录 A FP 表 `L1417–L1432` **脱离表格**（表头+分隔在 L1404–1405，markdown 断表）→ 收窄为**仅删该空行** |
| `SPEC-032t` | **关闭→删除任务书**（已消解） | 独立复算 8/16/32/64 位数据运算 rd 形式 `spec_cite` → **0 不匹配**（如 `add.ut_orrr_rd → SimRISC-08 §加减操作`）；`check_qfc_coverage.py` → `差异总数: 0` |
| `SPEC-033t` | **改范围** | `contract-abi.md:209` 仍写 `SimRISC-02 §函数调用`/`§函数返回`（实测 `SimRISC-02` 无此二节、`SimRISC-06` 有）；`docs/README.md:17` 部分已完成 → 收窄为**仅修 `contract-abi.md`** |
| `TESTCASES-014t` | **改范围** | 位宽主引用已对齐（向量用 `SimRISC-08/09/10`）；残留 `generate_isa_vectors.py` 的 `_ILLI_RULES`（L974/976/978）三条规则引用陈旧（`SimRISC-01 §rd0 为目的寄存器约定`/`§加减操作`、`SimRISC-02 §rb0 为目的寄存器约定`），与 `contracts/legality_rules.yaml`（`dst_rd0 → SimRISC-00 §数据寄存器` 等）不一致 → 收窄为**仅修规则引用** |

> 处置已同步写入对应 5 个任务书（改范围项各在头部追加「处置」块）。**关闭项（`LLVM-016t`/`SPEC-032t`）已删除任务书**（用户裁定 2026-10-04；沿用 `LLVM-010t` 先例「删文件、编号留空」），关闭理由记入 `changelog.md`；改范围项按新范围执行。

## 说明

- 本 k 只做规划，不实现；门槛核验在 `INTEG-010t`（M2 归档）前完成。
- **门槛①**（`make check` 全绿）由各任务各自的 `make check` + `INTEG-010t` 终检承担，不单列任务。
- **门槛③的 `check-spec-refs`**（standalone 目标，非 `make check` 成员；当前 76 条历史违规 = `ISS-086`）**已裁定纳入 M2**（用户 2026-10-04），由 **`SPEC-094t`** 消解。
- 涉及新规范正文 / 外部契约的任务（如 `SPEC-091t` 若超出「归一化现有 `spec/`」范围）须按 `spec/Process-03` **主动提醒用户**是否立 ADR，不擅自决定。
- 假设：M2 期间不改 `components/`、`tests/vectors/` 既有语义字段；FP 独立 oracle / FP 向量 / 完整 E2E 明确归 M3。
