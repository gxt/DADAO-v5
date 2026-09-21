# TESTCASES-001k: testcases 模块启动

**模块**：testcases
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

## 问题根源

DADAO-v5 的 TDD 合约要求：在任何 LLVM/QEMU 实现字节被写入之前，M1 scope 内每条指令必须已有独立测试向量，且向量期望值必须**手工派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`**，不得从 LLVM 汇编输出或 QEMU 运行结果反推——否则测试只是实现的自证，无法捕获实现自身的错误。

当前仓库已有 `contracts/opcodes.yaml`（SPEC-003t，256 条记录）作为机器可读编码 oracle，但**没有任何测试向量数据、schema、覆盖矩阵或向量校验器**，后续 llvm/qemu/gem5 模块没有独立 oracle 可比对。DADAO-0628 的 DL-001d 正是为此建立 `tests/vectors/` 与 `validate_vectors.py`，并在随后 DL-017a/017b/020a/022c/027a/028a/034a 中反复修复覆盖率与数据缺陷；这些缺陷与结论是本模块的直接经验来源。

## 目的

建立 testcases 的独立向量层：

- 产出 `tests/vectors/schema.md`、`inventory.md`、`README.md`、`isa/*.yaml`（5 类向量：encoding / legality / semantic / boundary / overlap）与 `tools/testcases/validate_vectors.py`；
- 把向量校验接入 `make check` 作为门控；
- 使 M1 scope 内每条指令身份（`(insn, format)`，等价于编码表的 `(op, ha)`）都有 ≥1 条 active 向量，期望值全部可回溯到合约/spec；
- 使向量层可作为 LLVM/QEMU/gem5 的独立 oracle，并作为后续差分验证的输入。

## 对照关系

- **借鉴**：DADAO-0628 的向量工作流——DL-001d 建 schema/inventory/data/validator；DL-017a/017b 修覆盖率身份与唯一性；DL-020a 补 encoding class；DL-022c 内存地址 ROM→RAM；DL-027a/028a/034a 修数据与 control-flow/load 的 deferred 重设计；以及 `0002-detailed-roadmap.md` 的 TDD Contract / Vector Taxonomy / Ordering Rule。
- **差异**：v5 基于 SimRISC 0.5.3——指令命名带 `.b`/`.w`/`.t`/`.o` 与 `s`/`u` 后缀（`add.uo`/`ld.ub`/`st.o`/`set.zw`/`br.nz`/`illi`）；`contracts/opcodes.yaml` 的 `insn` 字段（如 `ld.o-rd`/`ld.o-rb`）区分 RD/RB/RA 变体，但**并非全局唯一**——`ext.*`/`shr.*`/`shl.*` 的 `orrr`（寄存器移位量/扩展位）与 `orri`（立即数）两条记录共享同一 `insn`（实测 20 组重复；178 条 M1 记录仅 158 个唯一 `insn`）。唯一编码身份是 `(op, ha)`（256/256 唯一，`op`=`value>>24`、`ha`=`(value>>18)&0x3f`），向量侧等价键为 `(insn, format)`（256/256 唯一）。**覆盖率主键须用 `(insn, format)`**，否则这 20 组会重演 0628 的假全覆盖；MISC-byte/wyde/tetra/octa 子表改变向量文件组织；RB 算术为**全 64 位**（0.4.1 的 48-bit 截断/高 16 位保持结论**不适用**）；**M1 scope 以 `contracts/opcodes.yaml` 的 `excluded_m1: true` 为唯一判据**（78 条：浮点 RF 全部、特权 cfx、LR-SC 原子），其余 178 条为 M1——**RA 存取/块赋值（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`ra2rd`/`rd2ra`）与系统指令（`swym`/`illi`/`fence`）属 M1，不得从门控排除**（与 `contract-isa.md` §4.9、§7 及 `legality_rules.yaml` 的 active 规则一致）。
- **拒绝的 legacy 行为**：把 QEMU/LLVM 运行结果当作期望值；用 `(mnemonic, format)` 作覆盖率主键导致 RD/RB 变体假全覆盖；用非唯一的 `insn` 作覆盖率主键导致 `orrr`/`orri` 变体假全覆盖；让 deferred case 静默缺席；把向量校验脚本与编码表混为一套真相；复制 0.4.1 的向量数据/编码正文。

## 任务分解

> **重排说明（2026-09-15 最终裁决，用户逐条确认）**：`TESTCASES-002t` 交付后经 architect 交叉复核 + 主会话独立复验，判决 `Needs Revision`（F1/F10 系统性数据错误 + F2/F3/F5/F6/F7/F9）。任务集据此**二次重排**（覆盖上一次重排）：`002t` 收窄为**向量基础设施返工**（schema 新增 `expected_pc`、inventory、validator；F2/F3/F6/F9）；F1 数据修复归 `003t`（寄存器间传输与运算）；**F10 分摊**到 `003t`~`007t`（各修本任务文件的 encoding 向量，不单列 encoding 任务）；**F7 采用方案 (i)：schema 扩 `expected_pc`**，`jump`/`call` 的 PC 效果与 `br.*` 的 taken 路径均用 `expected_pc` 表达 → **5 条 PC-only 全部改 active，不再有 PC-only deferred**；F5（保留编码 → UNDI）改由 `008t` 承载（原 `011t` 编号**撤销**——不能排在 `010m` 之后）。文件布局采用**方案 A（按运算族分，bank 混在文件内）**。详见各任务文件与 `.tao/knowledge/deferred.md` `## testcases`。

| 编号 | 任务 | 拥有的文件 | 内容 | 依赖 | 状态 |
|------|------|-----------|------|------|------|
| `TESTCASES-002t` | 向量基础设施（**返工**） | `tests/vectors/schema.md`、`inventory.md`、`tools/testcases/validate_vectors.py` | schema（**新增 `expected_pc` 字段**）+ inventory + validator；**F2**（inventory 缺 `format` 列）、**F3**（inventory 无同步校验）、**F6**（encoding 类对恒 fault 指令豁免的澄清）、**F9**（validator 补强） | 无 | 已验证 |
| `TESTCASES-003t` | 寄存器间传输与运算 | `reg-arith` `reg-logic` `reg-shift-extend` `reg-compare` `reg-cond-assign` `reg-imm-block` | 含 **F1**（`orrr` shamt 应为寄存器形式）修复；`rela.si-rb` 改 active；本任务文件 F10 encoding 修复 | `002t` | 待开始 |
| `TESTCASES-004t` | load/store（RD/RB/RA 三 bank） | `mem-rd` `mem-rb` `mem-ra` | 访存 encoding 的地址/base/count 语义（F10）；本任务文件修复 | `003t` | 待开始 |
| `TESTCASES-005t` | 控制转移 `br.*` | `ctrl-br` | taken / not-taken 全测（用 `expected_pc`）；F10 | `002t`（默认串行时排 `004t` 后） | 待开始 |
| `TESTCASES-006t` | `jump`/`call`/`ret` | `ctrl-jump` `ctrl-call` `ctrl-ret` | 用 `expected_pc` 表达 PC 效果；`call` 的 RA 压栈用 `ra` 表达；F7 全 active；F10 | `005t` | 待开始 |
| `TESTCASES-007t` | misc | `misc` | `swym`/`illi`/`fence`（从零生成）；F10 | `006t` | 待开始 |
| `TESTCASES-008t` | 保留编码 → UNDI（**F5**） | 新文件 + `schema.md`/`validate_vectors.py`/`inventory.md` | 保留编码的向量层表达（**方案 A**：复用 `class: legality` + `encoding.reserved: true`；取舍已记录，**不立 ADR**） | `002t` | 待开始 |
| `TESTCASES-009t` | ISA 向量全量再审计（兜底） | 全部 `isa/*.yaml` + `inventory.md` | 残留错误 | `003t`~`008t` | 已验证 |
| `TESTCASES-010t` | 数据级覆盖率缺口消解（154 缺口） | `generate_isa_vectors.py`/`generate_ctrl_br.py`/`generate_ctrl_jump_call_ret.py` + 全部 `isa/*.yaml` + `inventory.md` | 逐条消解 141 legality + 2 boundary + 11 overlap 缺口：补 active case 或降级 ✓ → `deferred` | `009t` | 待开始 |
| `TESTCASES-011m` | 里程碑 | — | 核验门槛含 F1/F5/F6/F7/F10 + 154 缺口消解（gap=0） | 全部 | 待开始 |
| ~~`TESTCASES-004t`~~ | ~~向量覆盖率修复~~（**旧范围已达成**） | — | 范围已由 `002t` validator 覆盖 | — | 已达成 |
| ~~`TESTCASES-005t`~~ | ~~validator 身份唯一性修复~~（**旧范围已达成**） | — | 范围已由 `002t` 覆盖 | — | 已达成 |
| ~~`TESTCASES-006t`~~ | ~~语义向量内存地址 ROM→RAM~~（**旧范围已达成**） | — | 目标已达成 | — | 已达成 |
| ~~`TESTCASES-011t`~~ | ~~保留编码 UNDI 向量表达~~（**编号撤销**） | — | 改由 `008t` 承载（原编号排在 `011m` 之后，违反 `nnn` 递增） | — | 撤销 |

> **旧任务「已达成」理由与证据（单一出处）**：上表末三行是**旧范围**的记录——它们并非「暂缓/不做」，而是**已由 `TESTCASES-002t` 的交付达成**，故不写入 `deferred.md`（`deferred.md` 只记真正未决项）。证据：
> - **旧 `TESTCASES-004t`（覆盖率主键 `(insn, format)` + `encoding.word` mask/value 校验）**：已由 `tools/testcases/validate_vectors.py` 实现——身份存在性 + mask/value 校验（`:174–201`）、覆盖率门控（`:272–281`）。
> - **旧 `TESTCASES-005t`（只标记实际匹配 word 的身份）**：已由 `tools/testcases/validate_vectors.py` 实现——`covered.add(key)` 仅在**精确匹配分支**执行（`:270`）。
> - **旧 `TESTCASES-006t`（semantic 向量地址 ROM→RAM）**：目标已达成——`002t` 交付的全部 semantic memory 地址 **48/48** 落在 ADR-0004 RAM 窗口 `[0xffff_0000_0000, 0xffff_00ff_ffff]`，无以 `rb0` 为 base 的访存，无 ROM 地址。
> - 旧任务文件已删除，内容保留于 git 历史。
>
> **编号复用说明**：`004t`/`005t`/`006t` 三个编号在本次最终重排中被**复用为新任务**（load/store、`br.*`、`jump`/`call`/`ret`），见上表；不再对应旧范围。

- **文件拆分映射（历史：旧 → 新，`tests/vectors/isa/`）**：
  > **注（2026-09-15 交叉复核）**：下表描述的「旧文件」属**上一版已丢弃**的 `002t` 交付，仓库内**已不存在**（`git ls-files tests/` = 0）。`003t`~`007t` 的向量数据改为**从零生成**（见各任务书「输入说明 / 数据来源说明」）；本表仅保留目标文件集的归口关系，**不再表示实际的重组动作**。

  | 旧文件 | 去向 |
  |---|---|
  | `rd-arith.yaml` | `reg-arith.yaml`（保留 add/sub/mul/div/rem + `add.si-rd/rb` + `rela.si-rb`）；`cmp.*` 移入 `reg-compare.yaml` |
  | `rb-ops.yaml` | `add.so-rb`/`sub.so-rb` → `reg-arith.yaml`；`ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb` → `mem-rb.yaml`；**文件消失** |
  | `ra-ops.yaml` | `ra2rd`/`rd2ra` → `reg-imm-block.yaml`；`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` → `mem-ra.yaml`；**文件消失** |
  | `rd-logic.yaml` | `reg-logic.yaml`（改名） |
  | `rd-shift-extend.yaml` | `reg-shift-extend.yaml`（改名） |
  | `rd-compare.yaml` | `reg-compare.yaml`（并入 `rd-arith.yaml` 的 `cmp.*`，去重） |
  | `rd-cond-assign.yaml` | `reg-cond-assign.yaml`（改名） |
  | `rd-imm-block.yaml` | `reg-imm-block.yaml`（并入 `ra-ops.yaml` 的 `ra2rd`/`rd2ra`） |
  | `rd-load-store.yaml` | `mem-rd.yaml`（改名） |
  | `control-flow.yaml` | `br.*` → `ctrl-br.yaml`；`jump-*` → `ctrl-jump.yaml`；`call-*` → `ctrl-call.yaml`；`ret-*` → `ctrl-ret.yaml`；`swym` → `misc.yaml`；**文件消失** |
  | `misc.yaml` | `misc.yaml`（并入 `swym`，与 `fence`/`illi` 合并） |

  目标文件集（14 个）：`reg-arith` `reg-logic` `reg-shift-extend` `reg-compare` `reg-cond-assign` `reg-imm-block` `mem-rd` `mem-rb` `mem-ra` `ctrl-br` `ctrl-jump` `ctrl-call` `ctrl-ret` `misc`。

- **依赖关系与下发建议**：
  - 串行链（共享 **`inventory.md`**，须按序）：数据从零生成后，各任务**不再共享源文件**，但均需手改 `inventory.md` 的 `file` 列（`002t` 未交付 inventory 生成脚本）→ `002t → 003t → 004t → 005t → 006t → 007t` 依次执行，避免 `inventory.md` 冲突。
  - `002t → 003t → 004t → 005t → 006t → 007t → 008t → 009t → 010t → 011m` 为**推荐默认全串行**：`inventory.md`（含 `file` 列）与 `schema.md`/`validate_vectors.py` 为多任务共享，串行最稳。
  - **并行前提不成立**：目标文件集互不相交，但 `inventory.md` 无生成脚本、需手改（`002t` 采用 R2 方案 A，`gen_inventory.py` 仅在 `/tmp` 一次性使用、未进仓库）→ 并行前提不成立；M1 采用默认全串行。`008t` 只碰 `schema.md`/`validate_vectors.py`/新文件，本可与数据链并行，但仍受 `inventory.md` 手改约束，建议串行。
- **分解理由**：`002t` 先冻结 schema（含 `expected_pc`）、inventory、validator（消除 F2/F3/F6/F9 类错误对 `make check` 的不可见性）；随后按运算族**从零生成**数据（F1/F10/F7 为生成时须满足的要求），最后全量再审计（`009t`）兜底残留。

## 说明

- **2026-09-15 二次重排**：本 `k` 文件的历史分解（含上一次重排）保留于 git 历史；当前有效任务集以上表为准。关闭任务（旧 `004t`/`005t`/`006t`）的处置与证据、F5/F6/F7/F9 结论记录在 `.tao/knowledge/deferred.md` `## testcases`。
- 本模块只规划向量层，不实现 LLVM/QEMU/gem5。
- 期望值必须独立派生自 `spec/` 与 `.tao/knowledge/contract-isa.md`（independent oracle 原则）；禁止从 LLVM/QEMU 生成。
- `contracts/opcodes.yaml`（SPEC-003t）是唯一编码真相；向量不得另造编码表。覆盖率主键为 `(insn, format)`（`insn` 非唯一，见「对照关系」）。
- M1 scope 判据为 `contracts/opcodes.yaml` 的 `excluded_m1` 字段（78 条排除，178 条 M1），不另立指令清单。
- `tools/testcases/validate_vectors.py` 置于 `tools/testcases/`（v5 各模块工具目录；`validate_encoding.py` 在 `tools/spec/`）；0628 置于 `scripts/`，差异在各任务注明。
- 测试机相关的地址/exit/fault 语义以 `.tao/knowledge/adr-0004-test-machine.md`（SPEC-006t）为准；向量 schema 的 `expected_fault` 除 6 个 spec fault 外须能表达 ADR-0004 D5.8 的 `0x87`（unmapped，测试机约定）。
- control-flow / load 的 QEMU 运行验收依赖 qemu/integ 模块的 harness（qemu 模块 `QEMU-014t`~`019t`，`verif` 已解散），相关任务以数据不变量 + validator 为主验收，运行验收作为下游集成检查。
- 详细背景与 DADAO-0628 对照见各 `t` 任务文件。
