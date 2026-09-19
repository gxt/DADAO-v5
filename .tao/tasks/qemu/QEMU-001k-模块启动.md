# QEMU-001k: qemu 模块启动

**模块**：qemu
**项目里程碑**：M1
**依赖**：无
**状态**：待开始

## 问题根源

DADAO-v5 基于 SimRISC 0.5.3，需要从零构建 QEMU 的 DADAO CPU target（`target/dadao/`）与裸机测试机器（`hw/dadao/`），使 `qemu-system-dadao` 能在 MMU-off 裸机模式执行 M1 标量程序，并与独立测试向量形成「raw encoding → QEMU 执行 → 结果比对」闭环。当前仓库尚未规划 qemu 模块任务。

DADAO-0628 的 QEMU 任务链基于 SimRISC 0.4.1，其指令命名（`add`/`sub`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`…）、QFC 编码表（opcode 分配）、格式体系（无 MISC-byte/wyde/tetra/octa 子表）、RB 寻址语义（0.4.1 截断到 48 位）与 v5（全 64 位）完全不同，不能照搬其补丁正文、编码数据或 `trans_*` 函数。

因此需要把 0628 的 QEMU 核心任务链（`DL-006a`、`DL-013a`、`DL-014a`、`DL-015a`、`DL-016a`、`DL-016b`、`DL-018a`、`DL-024a`、`DL-025a`、`DL-026a`、`DL-032a`）完整转述并按 0.5.3 重新分解，作为 v5 qemu 模块 M1 的规划基线。

## 目的

规划 v5 qemu 模块 M1 任务链：锁定 QEMU 上游基线 → 创建 target 骨架与裸机测试机器 → decodetree 全量解码 → RD 整数语义 → RD load/store + MALIGN 精确异常 → 控制流 + RB 指令 → rela 基址 / ldmo_rb / div-label / 分支调用 四项修复 → 核心里程碑。使 M1 结束时 `qemu-system-dadao` 能执行 M1 标量程序，语义/合法性/边界向量经「raw encoding → QEMU 执行 → 结果比对」与独立 oracle（`.tao/knowledge/contract-isa.md`、`contracts/opcodes.yaml`）一致，`make build-qemu` 全绿。（注：raw encoding 测试路径不依赖 llvm-mc，由 harness 直接从 `encoding.word` 生成 binary；MC↔QEMU 属 `integ` 模块集成验证。）

## 对照关系

- **借鉴**：DADAO-0628 QEMU 核心任务链——`DL-006a`（组件基线 + ADR-0006 + `build-qemu`）、`DL-013a`（Target Skeleton + `hw/dadao/` 机器）、`DL-014a`（decodetree 全量解码）、`DL-015a`（RD 整数语义）、`DL-016a`（RD load/store）、`DL-016b`（MALIGN 精确异常 + TEMP_EBB 修复）、`DL-018a`（控制流 + RB，TDD 向量先行）、`DL-024a`（rela 基址修复）、`DL-025a`（ldmo_rb 实现）、`DL-026a`（divs/divu TCG label 修复）、`DL-032a`（branch PC 公式 + call RA 修复）；以及其 `components/qemu/patches/series` 的补丁命名与顺序、`docs/adr/0006-qemu-baseline.md` 的 ADR 形态。
- **差异**：
  - 规范版本 0.4.1 → 0.5.3：指令命名使用 `.b/.w/.t/.o` 与 `s`/`u` 后缀（`add.uo`/`add.so`、`div.so`/`div.uo`、`cs.n`、`br.n`/`br.nz`、`set.zw`、`ld.o`、`st.o`、`illi`…）；QFC 主表 opcode 分配完全改变；新增 MISC-byte/wyde/tetra/octa/RF/AMO 子表（op **`0x00`、`0x40`–`0x44`**；**注（2026-09-19 订正）**：原文写 `0x40`–`0x45`，其中 MISC-AMO 实为 `0x00`、其余各少 1）；`add.si`/`rela.si` 为 riii；新增 `br.z-rb`/`br.nz-rb`、LR/SC 原子指令、浮点条件赋值等。补丁正文、`insn.decode`、`trans_*` 与编码数据必须按 0.5.3 重新生成。
  - oracle 不同：v5 语义/合法性期望值来自 `.tao/knowledge/contract-isa.md`（§1 寄存器、§2 编码、§3 标量、§4 地址/内存、§5 控制流、§7 系统、附录 A 编码清单）与 `contracts/opcodes.yaml`（256 条）、`contracts/legality_rules.yaml`，而非 0628 的 `contracts/isa/spec.md`。
  - RB 语义不同：0.5.3 RB 算术为全 64 位运算，bits[63:48] 为运算结果、可用于溢出检测；0.4.1 截断到 48 位。不得沿用 0628 的 `& 0x0000FFFFFFFFFFFF` 掩码写法作为 RB 结果。
  - 测试机权威不同：exit port 协议、内存图、MALIGN/ILLI/UNDI 可观测行为以 v5 `.tao/knowledge/adr-0004-test-machine.md`（`SPEC-006t` 产出）为准，不照抄 0628 `docs/adr/0004-test-machine.md`。
  - 目录/工具不同：v5 任务在 `.tao/tasks/qemu/`；上游 checkout 落在 `.work/source/qemu`（`INFRA-004t` 约定），构建落在 `.work/build/qemu`；参考锁指向 `.work/DADAO-0628`。
  - 不照抄 0628 的 QEMU commit 作为既定基线；版本由 `QEMU-002t` 的 ADR-0008 独立记录并验证。
  - 路线与参考直接指向 DADAO-0628，不使用任何按开发批次命名的目录或字段。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `QEMU-002t` | QEMU 组件基线（commit + ADR-0008 + `build-qemu`） | `.tao/knowledge/adr-0008-qemu-baseline.md`、`manifests/components.lock.toml`（qemu enabled+commit）、`Makefile` 真实 `build-qemu` | `INFRA-006t`、`INFRA-009t`、`INFRA-013t` |
| `QEMU-003t` | Target Skeleton | `components/qemu/patches/0001-dadao-target-skeleton.patch`、`series`、最小冒烟 | `QEMU-002t`、`SPEC-006t` |
| `QEMU-004t` | Decodetree 解码 | `components/qemu/patches/0002-dadao-decodetree.patch` | `QEMU-003t`、`SPEC-003t`、`SPEC-008t` |
| `QEMU-005t` | RD 整数语义（算术/逻辑/移位/比较/条件赋值） | `components/qemu/patches/0003-dadao-rd-arith.patch` | `QEMU-004t` |
| `QEMU-006t` | RD Load/Store | `components/qemu/patches/0004-dadao-load-store.patch` | `QEMU-005t`、`SPEC-006t` |
| `QEMU-007t` | MALIGN 精确异常 + TEMP_EBB 修复 | 修订 `0004-dadao-load-store.patch` | `QEMU-006t`、`SPEC-006t` |
| `QEMU-008t` | 控制流 + RB 指令（不含 ra2rd/rd2ra） | `components/qemu/patches/0005-dadao-ctrl-flow.patch`、向量补充 | `QEMU-007t`、`SPEC-006t` |
| `QEMU-009t` | rela 基址定向回归验证（**验证任务，不改补丁**） | 验证报告 | `QEMU-008t` |
| `QEMU-010t` | ldmo_rb 实现 | 修订 `0005-dadao-ctrl-flow.patch` | `QEMU-009t`、`SPEC-006t` |
| `QEMU-011t` | div/rem label 顺序定向回归验证（**验证任务，不改补丁**） | 验证报告 | `QEMU-010t` |
| `QEMU-012t` | 分支 PC 公式 + call RA 定向回归验证（**验证任务，不改补丁**） | 验证报告 | `QEMU-011t`、`TESTCASES-005t`、`TESTCASES-006t` |
| `QEMU-013t` | RA 指令语义（**拥有 RA 全部指令**：ld.o-ra/st.o-ra/ldm.o-ra/stm.o-ra/rd2ra/ra2rd） | `components/qemu/patches/0008-dadao-ra-semantics.patch`、RA 向量 | `QEMU-008t`、`SPEC-002t`、`SPEC-003t` |
| `QEMU-014t` | QEMU 语义 harness（**并行轨**：骨架+比较逻辑+ADR-0009） | `tests/scripts/build_test_binary.py`、`run_qemu_test.py`、`gen_trampoline.py`、`trampoline.bin`、`README.md`、`.tao/knowledge/adr-0009-qemu-harness-methodology.md` | `QEMU-004t`、`TESTCASES-003t`、`SPEC-006t` |
| `QEMU-015t` | harness 语义验证修复（含 expected_state.ra + encoding.reserved 义务） | `build_test_binary.py`（`emit_state_compare`）、`run_qemu_test.py` | `QEMU-014t` |
| `QEMU-016t` | harness memory 检查（按写入指令推导宽度，不扩 schema.width） | `build_test_binary.py`（memory 比对） | `QEMU-015t`、`TESTCASES-004t` |
| `QEMU-017t` | 分支语义 harness（用 expected_pc，不用 branch_behavior） | `build_test_binary.py`（branch）、`ctrl-br.yaml`/`ctrl-jump.yaml` semantic 激活 | `QEMU-015t`、`TESTCASES-005t` |
| `QEMU-018t` | call/ret 语义 + RA stack（用 expected_pc/expected_state.ra，不用 call_ret） | `build_test_binary.py`（call/ret）、call/ret 测试 | `QEMU-017t`、`QEMU-012t` |
| `QEMU-019t` | QEMU trans lint（含 mnemonic `.`→`_` 归一化对齐） | `tools/qemu/check_qemu_trans.py` | `SPEC-003t`、`QEMU-013t` |
| `QEMU-020m` | QEMU 核心里程碑（**硬性要求：全部 M1 向量经 harness 执行且结果比对一致**） | 里程碑标记 | `QEMU-002t`~`QEMU-019t` |

- **依赖关系**：`002t → 003t → 004t → 005t → 006t → 007t → 008t → {009t（验证）, 013t} → 010t → 011t（验证） → 012t（验证）`；`014t ← 004t`（并行轨，harness 骨架不依赖已实现语义）→ `015t ← 014t` → `{016t ← 015t+TESTCASES-004t, 017t ← 015t+TESTCASES-005t}` → `018t ← 017t+012t`；`002t` 依赖 infra 的 `INFRA-006t`（Makefile 编排）、`INFRA-009t`（多源 schema）、`INFRA-013t`（组件名=原始仓库名）；`003t` 依赖 `SPEC-006t`（Test Machine ADR，提供内存图/复位值/exit 协议）；`004t` 依赖 `SPEC-003t`（编码表）与 `SPEC-008t`（合法性规则）；`008t` 依赖 `SPEC-006t`（fault/exit 可观测）；`012t` 依赖 `TESTCASES-005t`（br.* 向量）、`TESTCASES-006t`（jump/call/ret 向量）；`013t`（RA 指令）依赖 `008t` 与 spec；`014t`~`019t`（QEMU 自测 harness / trans lint）依赖 `014t`（并行轨起点）与 testcases；`020m` 汇总全部。
- **分解理由**：按「基线 → 骨架 → 解码 → RD 语义 → load/store → 精确异常 → 控制流/RB → 修复 → 里程碑」逐层推进，每层可独立 `git am` 一个补丁并独立验收（`make build-qemu` + 向量运行）；补丁命名/顺序以 0628 `series` 前段为参考，但 v5 按 0.5.3 重新生成（0628 的 `0002-dadao-hw-meson-subdir.patch` 独立修复在 v5 应并入 `0001` 骨架，见 `QEMU-003t`）。

## 说明

- 只规划不实现；本模块任务文件由工程师按 `## 交付物` 生成补丁与测试，架构师不写补丁正文。
- M1 范围为标量核心（`contract-isa.md` §3 标量整数、§4 地址/内存中 RD/RB/**RA** 部分、§5 控制流、§7 系统指令中测试机所需 `swym`/`illi`/`fence`）；浮点 RF 全部 与 LR/SC/特权指令按 M1 范围排除（保留 UNDI/ILLI 桩）。
- v5 QEMU M1 补丁序列（指示性，最终编号在实现时定稿，顺序参考 0628）：

  | v5 补丁（参考命名） | 0628 对应 | 任务 |
  | --- | --- | --- |
  | `0001-dadao-target-skeleton.patch` | `0001` + `0002`（hw-meson-subdir） | `QEMU-003t` |
  | `0002-dadao-decodetree.patch` | `0003` | `QEMU-004t` |
  | `0003-dadao-rd-arith.patch` | `0004` | `QEMU-005t` |
  | `0004-dadao-load-store.patch` | `0005` | `QEMU-006t`、`QEMU-007t` |
  | `0005-dadao-ctrl-flow.patch` | `0006` | `QEMU-008t`、`QEMU-009t`（验证）、`QEMU-010t` |
  | `0006-dadao-div-label-fix.patch` | `0007` | `QEMU-011t`（验证） |
  | `0007-dadao-branch-call-fix.patch` | `0008` | `QEMU-012t`（验证） |
  | `0008-dadao-ra-semantics.patch` | — | `QEMU-013t` |

- 参考：`.work/DADAO-0628/components/qemu/patches/series`、`.work/DADAO-0628/components/qemu/README.md`、`.work/DADAO-0628/docs/adr/0006-qemu-baseline.md`。
