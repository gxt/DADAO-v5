# 项目里程碑路线图

项目级里程碑（跨模块），由各模块的里程碑支撑（模块里程碑见 `.tao/tasks/<module>/` 的 `m` 文件）。主会话在依赖的模块里程碑均达成为 `里程碑` 后，将本项目里程碑置为 `达成`。路线参考 DADAO-0628（`.cache/refs/DADAO-0628`）。

| 项目里程碑 | infra | spec | testcases | golden | llvm | qemu | integ | gem5 | sail | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | **`INFRA-014m` ✅ 里程碑** | **`SPEC-011m` ✅ 里程碑** | **`TESTCASES-012m` ✅ 里程碑** | — | **`LLVM-015m` ✅ 里程碑** | **`QEMU-021m` ✅ 里程碑** | **`INTEG-004m` ✅ 里程碑** | — | — | **✅ 达成** |
| M2 | **`INFRA-034m` ✅ 里程碑** | **`SPEC-095m` ✅ 里程碑** | **`TESTCASES-025m` ✅ 里程碑** | — | **`LLVM-032m` ✅ 里程碑** | **`QEMU-039m` ✅ 里程碑** | **`INTEG-011m` ✅ 里程碑** | — | — | **✅ 达成** |
| M3 | `INFRA-036m` | `SPEC-099m` | `TESTCASES-027m` | — | `LLVM-042m` | — | `INTEG-013m` | — | — | 待开始 |

> **归档（2026-10-03）**：M1 的 76 个任务书已归档至 `.tao/archive/M1/`（按模块子目录）；M1 时期 changelog/MEMORY 内容见 `.tao/archive/M1/README.md`；**M1 回顾见 `.tao/archive/M1/m1-retrospective.md`**（由 `docs/` 移入）。
>
> **M2 重定义（2026-10-04，用户裁定）**：M2 定为「**规范与接口冻结（Normative Freeze）**」，原「Basic CodeGen」顺延为 **M3**；并**取消「过渡期任务 `M<i>→M<i+1>`」类别**——原 `M1→M2` 任务一律提升为 `M2`（**推翻** 2026-09-25 决议；不立 ADR）。
>
> **归档前置（MUST）**：任何里程碑达成后、**归档前**，须先按 `spec/Process-04 §2` 对遗留台账（`.tao/knowledge/issues.yaml` / `lessons.md`）做一次**梳理**（关闭已消解项、校正 `scope`、移出教训类、判定 moot 项、头部同步）；未完成不得归档。
>
> **状态口径**：本表 `状态` 列只有 **`待开始`/`达成`** 两态（模块 `m` 未置则显 `待开始`）；`issues.yaml` 头部的「M2=进行中」是**进度叙述**，二者不矛盾。
>
> **M2 达成（2026-10-04，architect 实测核验）**：M2 门槛 5 条全部满足、各模块 M2 任务均终态 ⇒ 6 个模块 `m` 置 `里程碑`、M2 置 `达成`。核验记录见下「M2 达成核验记录」。
>
> **归档（2026-10-04）**：M2 的 149 个任务书已归档至 `.tao/archive/M2/`（按模块子目录）；M2 时期 changelog（60 条）/MEMORY（45 行 + 2 段落）内容见 `.tao/archive/M2/README.md`；**M2 回顾见 `.tao/archive/M2/m2-retrospective.md`**；`issues.yaml` 的 41 条 M2 阶段 closed 项见 `.tao/archive/M2/issues-closed.md`。
>
> **M3 重定义（2026-10-04，用户裁定）**：M3 定为 **「Basic CodeGen（纯整数）」**——`llc` 编译标量整数/指针函数 → MC → 单 TU obj/raw binary → QEMU 执行正确；门槛 `make test-codegen` 全绿。bank 只 `GPRD`+`GPRB`；`RA`/`RF` 仅「保留不分配」；无需链接器（ADR-0003 §D5 单 TU + 最小重定位）。**M4（后续，未规划）**顺延：FP/RF codegen、完整调用约定（`ISS-005`，含变参/聚合/多返回/sret）、完整重定位（`ISS-008`）、clang targetinfo/driver。M3 任务分解见 `.tao/tasks/spec/SPEC-096k-M3启动与分解.md`；M3 的 `qemu` 无实现任务（执行层已由 M1 冻结）故本表填 `—`。

## M2 达成核验记录

**日期**：2026-10-04　**执行**：architect 实测（命令原样 + 退出码；完整输出见 `.work/log/integ/M2-milestone-make-check.log`、`.work/log/spec/M2-milestone-check-spec-refs.log`、`.work/log/qemu/M2-milestone-probe-03{4..8}t.log`）

| # | 门槛 | 命令 / 证据 | 结果 |
|---|------|-------------|------|
| ① | `make check` 全绿（所有 checker + 反例门控） | `make check` | **EXIT=0**；`repository checks: PASS`；lit 31/31 |
| ② | 投影表「缺口」清零或显式 deferred | `contract-asm.md` 已补齐（`SPEC-091t`）；`DADAO-12/13/22/23` ①列 = `deferred`（`SPEC-092t`）；`Process-02` 三者 = `deferred` | **满足**（4 项） |
| ③ | `spec_cite` / 引用 / 计数全对齐 | `make check-spec-refs` | **EXIT=0**；Check1 680 引用 / 0 失败、Check2 0（76→0，`SPEC-094t`） |
| ④ | FP = 执行层 60/60 + `dst_rd0@FP` + 最小 smoke | `min_rom_probe_03{4..7}t` = 59/77/113/91 全 PASS；`_038t` = 42/42；`smoke_fp.test` PASS | **满足** |
| ⑤ | 偏离台账 6 项 | `.tao/knowledge/MEMORY.md` `## 上游 ↔ v5 偏离台账` | **恰好 6 行**（`SPEC-093t`） |

**各模块 M2 `m`**：`INFRA-034m`、`SPEC-095m`、`TESTCASES-025m`、`LLVM-032m`、`QEMU-039m`、`INTEG-011m`。

**M2 任务终态**：wave 1/2 全部 `已验证`；唯一非终态 M2 任务 = `INTEG-010t`（M2 达成**后**执行的归档收尾，非达成分解）。

**归档前置**：`INFRA-033t`（`Process-04 §2` 台账梳理）`已验证`；M2 任务书归档由 `INTEG-010t` 在 M2 达成后执行。

> **caveat（非阻断，交主会话复核）**：投影表仍存 3 处字面 `缺口`——`SimRISC-07` 行 ④列 `缺口`（FP oracle/向量待建，2026-10-04 M3 重定义后属 **M4**，未加 `deferred` 字样）、`DADAO-12` 行 ②④列 `缺口（据实）`（据实、无需独立投影）。按 `SPEC-090k` 对门槛②的 4 项界定为满足；若要字面清零，建议将 `SimRISC-07 ④` 改标 `deferred（M3）`（需改 `spec/README.md`，超出本次核验写范围）。

## 里程碑说明

**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**

目的：`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。门槛：`make build-mc` / `build-qemu` / `test-interface` 全绿。

**M2 — 规范与接口冻结（Normative Freeze）**

目的：`spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层**机械一致**；FP **实现侧**收口（执行层 + 合法性）；偏离台账成型。为 M3 codegen 提供稳定契约。

门槛：① `make check` 全绿（所有 checker + 反例门控）；② 投影表「缺口」清零或显式 deferred；③ `spec_cite`/引用/计数全对齐；④ FP = 执行层 60/60 + `dst_rd0@FP` + **最小 FP smoke**；⑤ 偏离台账（6 项，见 `MEMORY.md`）。

**范围外（2026-10-04 M3 重定义后改归 M4）**：FP 独立 oracle（`GOLDEN`）、FP 向量（`TESTCASES-024t`）、完整语义 E2E。

**M3 — Basic CodeGen（纯整数）**

目的：`llc` 将**标量整数/指针**函数（LLVM IR）编译为 DADAO 汇编，经 MC → **单 TU** obj/raw binary → `qemu-system-dadao` 执行结果正确（freestanding、same-TU、无链接器）。门槛：**`make test-codegen` 全绿**，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。**范围**（用户裁定 2026-10-04）：bank 只用 `GPRD`+`GPRB`；`RA`/`RF` 仅「保留不分配」；无需链接器（单 TU 自包含 + 最小重定位）。分解见 `.tao/tasks/spec/SPEC-096k-M3启动与分解.md`。

> **M3 CodeGen 取舍点（C1–C17）已定（2026-10-04，用户逐条判定，32 条 decision 经逐一审核通过）**：判定结果见 `.tao/knowledge/project_M3-codegen-choices.md §5`；架构决策固化于单一 **`ADR-0018`**（分组：C1 硬双类、C2 指针 i64 通吃、C4 栈溢出区全局声明序、C5 返回 rb31 + callee 扩展、C7 帧策略条件式/SP-only 默认、C9 DataLayout、C11 SelectionDAG 为主、C13 无 subreg + 大端窄访存、C14 RB 算术落 GPRB、C16 call Defs/RegMask）；C17（无标志位 compare-branch）只落 `LLVM-037t` 任务书约束，不立 ADR。C6（CSR）归 ABI（`SPEC-097t`）。

> **M2 定义变更留下的旧文本已在 2026-10-04 M3 重定义时移除**：M2 曾把「FP 独立 oracle / FP 向量 / 完整语义 E2E」顺延至 M3；用户 2026-10-04 重划边界后，FP/RF 及完整调用约定/完整重定位归 **M4**（见下「M3 重定义」）。

## M1 模块依赖关系

```
infra ───────────────┐
                     ├──→ llvm ───┐
spec ──→ testcases ──┤           ├──→ integ ──→ M1
                     └──→ qemu ───┘
```

| 依赖边 | 内容 |
| --- | --- |
| `infra` → `llvm`、`qemu` | `build-mc` / `build-qemu` 依赖 infra 的 Makefile、fetch/apply、组件锁、容器 |
| `spec` → `testcases`、`llvm`、`qemu` | ISA 合约、编码表、ABI/ELF 合约、ADR-0003/0004（Test Machine） |
| `testcases` → `llvm`、`qemu`、`integ` | 独立测试向量（encoding/legality/semantic/boundary/overlap）供 MC/QEMU/集成验证 |
| `llvm` ∥ `qemu` | 两者仅依赖 `infra`+`spec`，**可并行**（MC 与 CPU 核心无相互依赖） |
| `llvm` + `qemu` + `testcases` → `integ` | 集成验证（E2E 套件与回归 + 跨模块接口对齐） |
| `integ` → `M1` | 集成闭环达成，M1 置为 `达成` |

关键路径：`infra` + `spec` → `qemu`（或 `llvm`）→ `integ` → M1。

## M1 建议执行顺序

按依赖分层，同层可并行：

**第 1 层 — 基础设施 + 规范基线**（无前置或已部分完成）
- `infra`：`INFRA-002t` → `003t` → {`004t`、`005t`} → `006t` → `007t` → {`010t`、`011t`、`012t`}
- `spec`：`SPEC-002t` → `003t` → `SPEC-004t` → {`005t`、`006t`} → `007t` → {`008t`、`009t`} → `010t`
- 说明：先建 `Makefile`/fetch/锁（infra）与 `ADR-0004`/ELF 合约（spec），解除对下游的阻塞。

**第 2 层 — 测试向量 + 组件基线/骨架**（依赖第 1 层）
- `testcases`（2026-09-15 最终重排）：`TESTCASES-002t`（**返工**：schema 新增 `expected_pc` + inventory + validator；F2/F3/F6/F9）→ `003t`（寄存器间传输与运算，含 F1）→ `004t`（load/store 三 bank）→ `005t`（`br.*` taken/not-taken）→ `006t`（`jump`/`call`/`ret`）→ `007t`（misc）→ `008t`（保留编码 → UNDI，F5）→ `009t`（全量再审计兜底）→ `010t`（缺口消解第一批：reg-arith/logic/shift-extend/compare）→ `011t`（缺口消解第二批：cond-assign/imm-block/ctrl + 门控转严）→ `012m`。F10 分摊到 `003t`~`007t`（各修本任务文件 encoding，不单列任务）；F7 用 `expected_pc` 方案全部转 active。**共享源文件**（`rb-ops`/`ra-ops` 被 `003t`/`004t`；`control-flow` 被 `005t`/`006t`/`007t`）与 `inventory.md` 决定以串行最稳；`{003t→004t}` 与 `{005t→006t→007t}` 目标文件集不相交，**若** inventory 由生成器统一重生成则可并行。旧 `004t`/`005t`/`006t`（覆盖率修复/身份唯一性/地址迁移）已关闭，编号已复用为新任务（见 `.tao/knowledge/issues.yaml`）
- `llvm`：`LLVM-002t` → `003t`（Triple + 最小 build）
- `qemu`：`QEMU-002t` → `003t`（骨架 + `hw/dadao/`）
- 说明：向量层尽早建立，供第 3 层验证；`llvm`/`qemu` 各自先打通「能 build」。

**第 3 层 — MC 后端 + QEMU 核心（+ 各自自测）**（依赖第 2 层，两条线并行）
- `llvm`：`LLVM-004t` → `005t` → `006t` → `007t`（反汇编器）→ `008t`（全量 lit）→ `011t` → `012t`（lit 字节 oracle）（`010t` 已于 2026-09-21 关闭）
- `qemu`：`QEMU-004t` → `005t` → `006t`(合并) → `007t`(拆分) → `008t` → `009t` → `010t` → `011t` → `012t` → `013t` → {`014t`~`019t` 自测/trans lint}（`020t` 已于 2026-09-21 关闭）；`022t`（TB 缺陷修复，依赖 `007t`，可与 `008t`~`020t` 并行）；`023t`（harness `input_state.memory` 按宽度写入，依赖 `016t`）

**第 4 层 — 集成验证**（依赖第 3 层）
- `integ`：`INTEG-002t`（E2E 套件与回归）、`INTEG-003t`（接口对齐）→ `INTEG-004m`

**第 5 层 — 里程碑收敛**
- 各模块 `m` 核验通过后置 `里程碑` → `M1` 置 `达成`

> 建议：第 1、2 层先行（打通构建与向量），第 3 层的 `llvm` 与 `qemu` 并行推进，第 4 层紧随其后。
