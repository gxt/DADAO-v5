# LLVM-081t: ISA↔后端覆盖矩阵（生成式，两层分列）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`、`LLVM-080t`（矩阵第 2 层需已构建后端；同模块 ⇒ 串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #5`）：**「ISA↔后端覆盖矩阵」立即立项**——生成式；以 **`contracts/opcodes.yaml` 全量**记录为**真源**；**两层分列**：① **汇编器可受理？** ② **ISel 是否用得上？**（**现有 lit 只证第①层**）。
  - 真源：`contracts/opcodes.yaml`（`scope` 分 `m1`/`fp`/`excluded`/`m3`；每指令 mnemonic/format/op/mask/value/fields/legality/spec_cite）。现有工具 `tools/llvm/{gen_asm_list.py,validate_instrinfo.py,check_lit_bytes.py,...}`（复用优先，DRY）。
  - 后端能力来源：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOInstrInfo.td`/ISel）。
- **输出**：
  1. 生成式工具（落 **`tools/llvm/**`**，**入库**、**非易失**）：由 `contracts/opcodes.yaml` **全量**遍历，输出覆盖矩阵（机器可读 + 人类可读，如 TSV/Markdown），**两层分列**：
     - 第①层「汇编器可受理」：逐指令（各合法 shape）喂 `llvm-mc`/`llc`，记录受理/拒绝（**复用现有 lit 能力**）。
     - 第②层「ISel 用得上」：记录该 ISA 指令**是否有 ISel 模式引用**（由 TableGen/ISel 机械提取，**非人工判读**）。
  2. 一页**缺口汇总**（未被 ISel 使用的指令清单 = 候补优化面，供后续里程碑参考）。
- **约束**：
  - **以 `contracts/opcodes.yaml` 全量为真源，禁手工挑拣**（不得只挑已知指令）。
  - **生成式**：矩阵由脚本产出；**计数不写死**（现场统计）；脚本随产物入库（`AGENTS.md`「生成器/脚本随产物保留」）。
  - **不改** `contracts/opcodes.yaml`；**只读**它。
  - 只动任务范围（`tools/llvm/**` + 本文书 + 必要的测试），越界须披露。

## 验收标准

1. **全量覆盖**：矩阵行/指令数 = `contracts/opcodes.yaml` 中指令条数（**现场统计**，脚本从 yaml 数出，不写死）；`grep`/脚本真实输出证明**每条指令都有两层取值**。
2. **两层分列**：输出含独立两列（第①层、第②层），且**第①层与现有 lit 口径一致**（抽查若干指令与 lit 结果一致）。
3. **生成式**：脚本可从真源**幂等重跑**（两次运行结果一致）；`--check` 模式可对「矩阵与真源不一致」报 FAIL（**反例门控**：注入一条虚构指令或篡改 yaml 副本 ⇒ FAIL ⇒ 还原 ⇒ 回绿）。
4. **缺口汇总**：输出「未被 ISel 使用的指令」清单（现场统计条数）。
5. **门控**：`make check`（若新工具纳入门控则全绿）；`check-no-residue` EXIT=0。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
