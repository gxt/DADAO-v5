# 项目里程碑路线图

项目级里程碑（跨模块），由各模块的里程碑支撑（模块里程碑见 `.tao/tasks/<module>/` 的 `m` 文件）。主会话在依赖的模块里程碑均达成为 `里程碑` 后，将本项目里程碑置为 `达成`。路线参考 DADAO-0628（`.work/DADAO-0628`）。

| 项目里程碑 | infra | spec | testcases | golden | llvm | qemu | integ | gem5 | sail | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | `INFRA-014m` | `SPEC-011m` | `TESTCASES-010m` | — | `LLVM-013m` | `QEMU-021m` | `INTEG-004m` | — | — | 待开始 |
| M2 | — | — | — | 待规划 | 待规划 | — | 待规划 | — | — | 待开始 |

## 里程碑说明

**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**

目的：`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。门槛：`make build-mc` / `build-qemu` / `test-interface` 全绿。

**M2 — Basic CodeGen**

目的：`llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → obj → 链接 → QEMU 执行结果正确（freestanding、same-TU，不含变参/聚合）。门槛：`make test-codegen` 全绿，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。

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
- `testcases`（2026-09-15 最终重排）：`TESTCASES-002t`（**返工**：schema 新增 `expected_pc` + inventory + validator；F2/F3/F6/F9）→ `003t`（寄存器间传输与运算，含 F1）→ `004t`（load/store 三 bank）→ `005t`（`br.*` taken/not-taken）→ `006t`（`jump`/`call`/`ret`）→ `007t`（misc）→ `008t`（保留编码 → UNDI，F5）→ `009t`（全量再审计兜底）→ `010m`。F10 分摊到 `003t`~`007t`（各修本任务文件 encoding，不单列任务）；F7 用 `expected_pc` 方案全部转 active。**共享源文件**（`rb-ops`/`ra-ops` 被 `003t`/`004t`；`control-flow` 被 `005t`/`006t`/`007t`）与 `inventory.md` 决定以串行最稳；`{003t→004t}` 与 `{005t→006t→007t}` 目标文件集不相交，**若** inventory 由生成器统一重生成则可并行。旧 `004t`/`005t`/`006t`（覆盖率修复/身份唯一性/地址迁移）已关闭，编号已复用为新任务（见 `deferred.md`）
- `llvm`：`LLVM-002t` → `003t`（Triple + 最小 build）
- `qemu`：`QEMU-002t` → `003t`（骨架 + `hw/dadao/`）
- 说明：向量层尽早建立，供第 3 层验证；`llvm`/`qemu` 各自先打通「能 build」。

**第 3 层 — MC 后端 + QEMU 核心（+ 各自自测）**（依赖第 2 层，两条线并行）
- `llvm`：`LLVM-004t` → `005t` → `006t` → `007t`（反汇编器）→ `008t`（全量 lit）→ `010t` → `011t` → `012t`（lit 字节 oracle）
- `qemu`：`QEMU-004t` → `005t` → `006t`(合并) → `007t`(拆分) → `008t` → `009t` → `010t` → `011t` → `012t` → `013t` → {`014t`~`020t` 自测/trans lint/dumper改造}

**第 4 层 — 集成验证**（依赖第 3 层）
- `integ`：`INTEG-002t`（E2E 套件与回归）、`INTEG-003t`（接口对齐）→ `INTEG-004m`

**第 5 层 — 里程碑收敛**
- 各模块 `m` 核验通过后置 `里程碑` → `M1` 置 `达成`

> 建议：第 1、2 层先行（打通构建与向量），第 3 层的 `llvm` 与 `qemu` 并行推进，第 4 层紧随其后。
