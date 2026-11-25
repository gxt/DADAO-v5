# m18-llvm-002: LLVM/opcodes 支持 `escape cfxHA` 与新槽位（任务链第 1 环）

**模块**：llvm
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入：`escape cfxHA`、`imms18` 恒 0、cg5/cg9 新槽位、opcodes/legality/别名表已重生成）；**LLVM 写者**须等 `m20-llvm-003` 释放（同 `components/llvm-project`，串行）
**可并行分片**：否
**预估**：2–3 h（标定：同档 llvm-001 汇编/反汇编支持约 2 h；本任务另含 legality/别名重生成，取 1–1.5×）
**档位**：中改（MC/AsmParser/Disassembler）
**状态**：待开始
**执行环境**：本地

## 背景

`m18-spec-007` 已把 `escape` 汇编格式改为 **`escape cfxHA`**（无 `imms18` 操作数；机器码字段保留但必须为 0，非 0 ⇒ `ILLI`），并改了 `cg5`/`cg9`/`cg0–cg3` 的槽位。`contracts/opcodes.yaml`、`legality_rules.yaml`、`cfx-aliases.txt` 已按新规范重生成，但 LLVM 侧仍：接受 `escape cfxha, imms` 形式、按旧操作数打印、未拒绝非 0 `imms18`。

所有后续任务（QEMU/RTL/gem5 探针、内核汇编、测试向量）都要用汇编器生成新编码/新槽位，因此本任务必须排在最前。

## 目标

1. **AsmParser**：`escape cfxHA` 合法；带第二个立即数（旧 `escape cfxha, 0/4/8`）⇒ 汇编错误（提示改用 `escape cfxHA` + 写 `cg5 rc10`）。
2. **编码**：生成的机器码 `imms18 = 0`；`imms18[17:2]` 与非 0 的 `imms18[1:0]` 由 legality 判 `ILLI`（与 `legality_rules.yaml` 一致）。
3. **反汇编**：统一打印 `escape cfxHA`；不得再打印偏移或帧选择位。
4. **生成物**：`opcodes`、`instrinfo`、别名/`.set` 表、asm-list 由仓库生成器重跑（`make generate-*` / `tools/llvm/gen_asm_list.py`），`check-opcodes-repro`/`check-asm-list-drift` rc=0。
5. **测试**：`tests/unit/llvm/lit/**` 更新（含 `cfx2-trap-escape.s` 的 `excp_cause_ip` 槽位 rc3→rc2、`escape` 新语法）；补一条“带立即数 ⇒ 汇编失败”和一条“`imms18 != 0` ⇒ ILLI 合法性”用例。
6. **不做**：不改 `tests/inst/**` 向量（`m18-testcases-004`）、不改 QEMU/RTL/gem5/IDL/内核。

## 验收（逐条贴真实 rc）

1. `lit` 全绿（记录总数）；`llvm-mc -show-encoding` 对 `escape cfx0` 输出 `imms18 = 0`；带立即数报错。
2. `llvm-objdump` 往返：`escape cfxHA` 汇编→反汇编→汇编，字节一致。
3. `check-opcodes-repro`、`check-asm-prose`、`check-asm-list`、`check-asm-list-drift`、`check-legality-drift`、`check-legality-invariants`、`check-cfx-aliases`、`check-instrinfo`、`check-decodetree-repro` rc=0。
4. 可达 FAIL ≥2 路（改回旧语法/允许非 0 imms18），`cp`+md5 还原回绿。
5. 组件补丁经 `make_patch.py llvm` 重导；`check-patch-tree` llvm 段 0 problem；不改版本号。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/llvm-project/patches/**`、`components/llvm-project/changelog.md`、`tests/unit/llvm/**`、`tools/llvm/gen_asm_list.py`（如需）、本任务书。
3. 不改 spec/契约/Makefile/QEMU/RTL/gem5/IDL/内核；不改版本号；`cp`+md5 还原。
4. LLVM 写者互斥：等 `m20-llvm-003` 合入后再动同一组件。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
