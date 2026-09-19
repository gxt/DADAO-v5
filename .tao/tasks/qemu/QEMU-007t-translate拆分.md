# QEMU-007t: translate.c 拆分重构

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-006t`
**状态**：待开始
**补丁**：`0005-dadao-translate-split.patch`（纯重构，ADR-0010 D2/D3）

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-006t` 产出的 `components/qemu/patches/0004-dadao-load-store.patch`（apply 后 `target/dadao/translate.c` 约 2500–3000 行）
  - `.tao/knowledge/adr-0010-qemu-task-restructure.md` D2（10 个 `.c.inc` 文件方案）
  - 上游参考：v11.1.1 riscv 的 `target/riscv/tcg/` 子目录 + `insn_trans/trans_*.c.inc` 模式
- 输出：`components/qemu/patches/0005-dadao-translate-split.patch`、`components/qemu/patches/series`
- 约束：
  - **纯重构，不改变语义**：`make build-qemu` 必须 PASS，`grep -c trans_` 总数不变
  - 不改 `insn.decode`（decodetree 不变）
  - 不改任何 `trans_*` 函数的实现逻辑（只移动物理位置）
  - 各 `.c.inc` 不含 `#include` 保护符（非独立编译单元）
  - 完成后不自行 commit

## 背景（完整）

### 目标

将 `translate.c`（约 2500–3000 行）按指令类别拆分为 10 个 `.c.inc` 文件，放入 `insn_trans/` 子目录，对齐 v11.1.1 riscv 的官方模式。纯重构，不改变任何语义。

### 设计理由

- `translate.c` 在 `006t` 后已膨胀到约 2500–3000 行，后续 `008t`（控制流+RB）+ `013t`（RA）将继续膨胀
- 10 文件按 spec 章节分类，每个文件对应一个指令类别，review 边界清晰
- 纯重构风险低，但能显著降低后续任务的 review 难度与冲突风险

### 关键概念 / 数据

**10 个 `.c.inc` 文件分类**（ADR-0010 D2）：

| 文件 | spec 章节 | 内容 |
|------|----------|------|
| `trans_arith.c.inc` | §3.1 | add/sub/mul/div/rem 及固定位宽变体 |
| `trans_compare.c.inc` | §3.2 | cmp.* |
| `trans_logic.c.inc` | §3.3 | and/or/xor/xnor/andn 及固定位宽变体 |
| `trans_shift.c.inc` | §3.4.1 | shr/shl 及固定位宽变体 |
| `trans_extend.c.inc` | §3.4.2 | ext.* |
| `trans_cond_assign.c.inc` | §3.5 | cs.* |
| `trans_imm.c.inc` | §3.6 | set.zw/or.w/andn.w 及 RB 变体 |
| `trans_block.c.inc` | §3.7/§4 | 块赋值（rd2rd/rd2rb/rb2rd/rb2rb/rd2ra/ra2rd） |
| `trans_mem.c.inc` | §3.8/§4/§4.9 | 存取（ld/st/ldm/stm 含 RD/RB/RA 变体） |
| `trans_ctrl.c.inc` | §5/§2.8 | 控制流（br/jump/call/ret/rela/swym/illi/fence） |

**`translate.c` 保留内容**：
- decodetree `#include`（`#include "decode-insn.c.inc"`）
- helper 函数（`store_rd`/`load_rd`/`gen_exception_illegal`/`gen_raise_exception_illi` 等）
- 寄存器访问宏（`cpu_rd`/`cpu_rb`/`cpu_ra` 等）
- `gen_intermediate_code` 入口函数
- 末尾 10 个 `#include "insn_trans/trans_*.c.inc"`

**文件格式**：
- 每个 `.c.inc` 以 `/* SPDX-License-Identifier: GPL-2.0-or-later */` 开头
- 不含 `#ifndef`/`#define` include 保护符
- 不含 `#include`（依赖 `translate.c` 中已引入的头文件）

### 上游引用

- v11.1.1 riscv：`target/riscv/tcg/translate.c` + `insn_trans/trans_rvi.c.inc` 等（官方推荐模式）

## 交付物

- `components/qemu/patches/0005-dadao-translate-split.patch`：创建 `insn_trans/` 目录 + 10 个 `.c.inc` 文件 + 修改 `translate.c`（删除移出的 `trans_*` 函数，末尾添加 10 个 `#include`）
- `components/qemu/patches/series`：加入 `0005`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **0628 无此任务**：0628 未做 translate.c 拆分（其文件规模更小）；v5 因任务更细、指令更多而需要拆分。
2. **文件数量**：v5 采用 10 文件方案（用户否决了 4 文件方案，要求更细粒度）。
3. **分类依据**：按 spec 章节（§3.1–§3.8 + §4 + §5）分类，而非按格式或位宽。

## 已知坑 / 结论

1. **`trans_*` 函数数量必须一致**：拆分前后 `grep -c 'trans_' translate.c` 加上所有 `.c.inc` 的总和必须相等。
2. **`#include` 顺序**：`.c.inc` 文件在 `translate.c` 中的引入顺序不影响编译，但建议按章节排列。
3. **git am 冲突**：本补丁必须在 `0004` 之上 apply；若有 `trans_*` 函数同时被 `0004` 和 `0005` 修改，需确保 hunk 对齐。
4. **后续补丁适配**：`0006`（008t 控制流）和 `0007`（013t RA）须在新的 `trans_ctrl.c.inc`/`trans_mem.c.inc`/`trans_block.c.inc` 中添加 `trans_*`。

## 参考

- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md` D2
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `components/qemu/patches/0005-dadao-translate-split.patch` 存在且干净 apply（在 `0004` 之上）；`series` 已加入 | 现在可跑 | `git am` 系列 |
| 2 | `target/dadao/insn_trans/` 目录下存在 10 个 `.c.inc` 文件，每个以 SPDX 开头 | 现在可跑 | `ls` + head 检查 |
| 3 | `translate.c` 末尾包含 10 个 `#include "insn_trans/trans_*.c.inc"` | 现在可跑 | grep |
| 4 | `make build-qemu` PASS（纯重构，不改变语义） | 现在可跑 | 构建 |
| 5 | `grep -c 'trans_'` 总数拆分前后一致 | 现在可跑 | 计数比对 |
| 6 | `insn.decode` 未被修改（diff 确认） | 现在可跑 | diff |
| 7 | 完成区含真实构建输出；未自行 commit | 现在可跑 | |

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录