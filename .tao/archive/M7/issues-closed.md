# M7 阶段已关闭 Issue（2026-10-11 ~ 2026-10-13）

> **来源**：`INTEG-035m`（2026-10-13）从 `.tao/knowledge/issues.yaml` 提取——**M7 期阶段已 `closed` 的 issue**（`Process-04 §4.4/§7`）。
>
> **判据（如实说明）**：**项目里程碑 M7 尚未标记「达成」**（待 `ISS-201` 用户裁定）⇒ 本归档以「**M7 期 = 2026-10-11（`INTEG-033k` 开启）~ 2026-10-13（归档日）**」为范围；提取集合 = 该范围内所有 `closed` 项（**12** 条）。**无 ≤ 达成日的机械界**（里程碑未达成）——此为本归档相对 `Process-04 §4.4` 的**已披露偏离**。
>
> **未提取（活动台账保留）**：M1（≤ 2026-09-22）8 条见 `.tao/archive/M1/issues-closed.md`；M2 41 条见 `.tao/archive/M2/issues-closed.md`；M3 56 条见 `.tao/archive/M3/issues-closed.md`；M4 12 条见 `.tao/archive/M4/issues-closed.md`；M5 5 条见 `.tao/archive/M5/issues-closed.md`；M6 18 条见 `.tao/archive/M6/issues-closed.md`。本次提取后活台账 `.tao/knowledge/issues.yaml` **仅保留 open 项**（**25** 条）。
>
> **更正注（2026-10-13）**：上「判据（如实说明）」之「**项目里程碑 M7 尚未标记「达成」**」**随口径纠正失效** ⇒ **更正为「项目里程碑 M7 = 达成（2026-10-13）」**。**理由**：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**；`ISS-201`（规范是否补记未定义弱符号**防御分支**）属 **spec 模块内 backlog**、**不阻断**。**用户指正原话**（2026-10-13）：「M7都已经归档了，你留着ISS-201是有什么意义？」。**原述保留不改写**（归档时快照）；本归档范围（M7 期 = 开启日 2026-10-11 ~ 归档日 2026-10-13）与提取集合（**12** 条）**不变**。

**共 12 条**（按原 `issues.yaml` 顺序）：M7 期关闭 **5** 条 + M6 遗留台账收敛 **7** 条。

## 1. M7 期关闭（5 条，`resolved_by` 指向 M7 任务）

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-189` | 其它 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double` 等）仍被 `llvm-mc` 受理（裁定口径 4 名外的剩余面） | [llvm] | LLVM-082t |
| `ISS-191` | `tests/scripts/dadao.lds` 缺 `__heap_start`/`__heap_end` PROVIDE ⇒ `malloc`/`sbrk` 程序链接失败 | [infra, testcases] | TESTCASES-042t |
| `ISS-194` | LLD 不为指向未定义弱函数的 `R_DADAO_REL26` 生成 veneer/弱桩 ⇒ 相对 `call` 链接失败 | [llvm] | LLVM-085t |
| `ISS-195` | DADAO QEMU `float_status` 未设 2-NaN 传播规则 ⇒ 恒等断言中止模拟器（`test-remquo-quo` rc=-6） | [qemu] | QEMU-058t |
| `ISS-196` | DADAO 工具链未构建/安装 compiler-rt builtins ⇒ `__muldc3`/`__mulsc3` 未定义（6 条复数 test 链接失败） | [llvm, infra] | INFRA-067t |

## 2. M6 遗留台账收敛（7 条，`INTEG-028t`，M7 期回填关闭）

> M6 任务完成区**声称已修/已收口**但 `resolved_by` 未回填的 7 条（M6 归档时如实登记为「待收敛」，见 `.tao/archive/M6/issues-closed.md` 末注）；M7 期由 `INTEG-028t`（M6 范围收尾任务，提交于 M7 期 2026-10-11）逐条独立核实后回填 `closed`。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-043` | 越界立即数静默截断（分支/跳转 fixup 越界无诊断） | [llvm] | LLVM-062t |
| `ISS-045` | `getFixupKindForInstr` 的 default 分支未白名单化（非分支符号操作数按 `PCRel_18` 处理） | [llvm] | LLVM-062t |
| `ISS-138` | >128K 帧（C7 D4 方案1：rd 存偏移 + `ldm`/`stm`）未实现，当前显式失败 | [llvm] | LLVM-064t |
| `ISS-148` | `tools/llvm/gen_m1_asm.py`/`test_m1_asm.py` docstring 仍写「177 条」（实 152） | [llvm] | LLVM-062t |
| `ISS-156` | `set.fo rf,0` 的 `rd2rf` 特例与 `Toolchain-01 §6.1`「4×set.w」口径不一 | [llvm, spec] | SPEC-123t |
| `ISS-159` | M4 后端 lower IR `not`/`neg` 未走 `xnor.o`/`sub.sX` 路径 | [llvm] | LLVM-062t |
| `ISS-162` | `DADAOAsmParser` 诊断枚举缺 `FIRST_TARGET_MATCH_RESULT_TY` 偏移 | [llvm] | LLVM-062t |

## 判定表（逐条：`resolved_by` → 提交 / 关闭日，落于 M7 期 2026-10-11 ~ 2026-10-13）

| id | resolved_by（提交） | 关闭提交日（`git log --grep`） | 判定 |
| --- | --- | --- | --- |
| `ISS-189` | LLVM-082t（`8050ce2`） | 2026-10-12 08:08 | ✅ 提取（M7 期） |
| `ISS-191` | TESTCASES-042t（`b653df5`） | 2026-10-12 03:29 | ✅ 提取（M7 期） |
| `ISS-194` | LLVM-085t（`a55c922`） | 2026-10-12 12:00 | ✅ 提取（M7 期） |
| `ISS-195` | QEMU-058t（`6b4c77c`） | 2026-10-12 21:26 | ✅ 提取（M7 期） |
| `ISS-196` | INFRA-067t（`bc362cb`） | 2026-10-12 18:01 | ✅ 提取（M7 期） |
| `ISS-043` | LLVM-062t（`d367bf6`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-045` | LLVM-062t（`d367bf6`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-138` | LLVM-064t（`98334d9`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-148` | LLVM-062t（`d367bf6`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-156` | SPEC-123t（`a8f21d7`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-159` | LLVM-062t（`d367bf6`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
| `ISS-162` | LLVM-062t（`d367bf6`，2026-10-09） | 关闭于 `INTEG-028t`（`f68e5a3`，2026-10-11 07:11） | ✅ 提取（M6 遗留收敛） |
