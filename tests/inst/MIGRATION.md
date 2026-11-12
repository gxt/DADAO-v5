# `tests/inst/` 重构台账（YAML → 汇编 + 宏）

> **目标**：让每条**操作码**的测试可读、可审、可三方差分。YAML 退出，改为 `.S` + 宏，期望值内联。
> **判据**：一个 id 一个文件；一个文件一个 ELF；失败点号 = 用例序号（退出码 `0x01`–`0x7F`，见 `spec/Machine-v5 §7.1`）。

## 1. 大类（= SimRISC 册）

| 目录 | SimRISC 册 | id 数（初估，待按各册附录 A 校准） |
|---|---|---|
| `01-load-store/` | 01 取数存数 | 38 |
| `02-reg-copy/` | 02 寄存器复制 | 16 |
| `03-wyde-imm/` | 03 16 位立即数操作 | 8 |
| `04-arith-logic-octa/` | 04 64 位数据运算 | 60 |
| `05-arith-addr/` | 05 64 位地址运算 | 5 |
| `06-control-flow/` | 06 控制流 | 15 |
| `07-floating-point/` | 07 浮点运算 | 44 |
| `08-arith-logic-tetra/` | 08 32 位数据运算 | 16 |
| `09-arith-logic-wyde/` | 09 16 位数据运算 | 16 |
| `10-arith-logic-byte/` | 10 8 位数据运算 | 16 |
| `11-cfx/` | 11 核芯功能扩展 | 29 |
| `12-misc/` | 12 其它指令 | 1（待校准） |

> id 总数应恰为 **264**（`contracts/opcodes.yaml`）。校准任务：建「id → 册」映射表并机械校验（每个 id 恰好属一册、12 册合计 264）。

## 2. 小类（= 一个 opcode id）

- 文件名 = **`<id>.S`**（id 里已含 format 与 bank，不重复写，如 `ld.o_rrii_rd.S`）
- 目录内不再按 bank 分层

## 3. 每个 id 的用例设计模板（5 类）

| 类 | 写什么 | 每 id 条数 |
|---|---|---|
| encoding | 该 id 的唯一编码（mask/value 校验） | 1–2 |
| legality | 该 id 适用的合法性规则（rd0/rb0、双目的、保留编码…） | 2–4 |
| semantic | 正常路径：宽度 × 符号 × 形式 | 4–8 |
| boundary | 该族特有边界（进位/借位/最值/次正规/对齐/窗口…） | 4–8 |
| overlap | 源=目、部分重叠、块复制重叠 | 1–3 |

合计每 id 约 15–25 条；一文件一个 ELF，检查点 ≤127。

## 4. 任务拆分（18 个）

| # | 任务 | 覆盖 | id 数 |
|---|---|---|---|
| 1 | 01-a | `ld.*` + `st.*`（单元素） | 19 |
| 2 | 01-b | `ldm.*` + `stm.*`（多元素） | 19 |
| 3 | 02 | 复制 + 条件选择 | 16 |
| 4 | 03 | 16 位立即数 | 8 |
| 5 | 04-a | 算术（add/sub/mul/div/rem/cmp） | ~20 |
| 6 | 04-b | 逻辑/移位/扩展 | ~20 |
| 7 | 04-c | 位操作（rev/rol/clmul/ct*） | ~20 |
| 8 | 05 | 地址运算 | 5 |
| 9 | 06 | 控制流 | 15 |
| 10 | 07-a | FP 算术（加/乘/FMA/除/开方/取余） | ~14 |
| 11 | 07-b | FP 转换/比较/分类 | ~16 |
| 12 | 07-c | FP 取整/缩放/符号 | ~14 |
| 13 | 08 | 32 位 | 16 |
| 14 | 09 | 16 位 | 16 |
| 15 | 10 | 8 位 | 16 |
| 16 | 11-a | 原子（`lr`/`sc`/`fence`/`swym`） | ~25 |
| 17 | 11-b | cfx/system（`trap`/`escape`/`cfx2rd`/`cfx2rc`） | ~4 |
| 18 | 12 | 其余 | ~1–20 |

## 5. YAML 台账（迁移与删除）

现状：**30 个 YAML 文件、1586 条用例、覆盖 229 个 id**；`opcodes.yaml` 有 **264** 个 id ⇒ **36 个 id 无 YAML 载体**；另有 16 个 id 出现在多个文件里。

**删除规则**：一个 YAML 文件里的**所有 id** 都迁完后，才 `git rm` 该文件，并在本表勾掉。

| YAML 文件 | 用例 | 涉及 id 数 | 状态 |
|---|---|---|---|
| `atomics/atomics-fence.yaml` | 17 | 1 | 待迁 |
| `atomics/atomics-lrsc.yaml` | 108 | 24 | 待迁 |
| `atomics/sc-rd0.yaml` | 14 | 24 | 待迁 |
| `base/aip-si.yaml` | 12 | 1 | 待迁 |
| `base/bitcnt.yaml` | — | — | 待迁 |
| `base/reg-arith.yaml` | 224 | — | 待迁 |
| `base/reg-compare.yaml` | — | — | 待迁 |
| `base/reg-cond-assign.yaml` | — | — | 待迁 |
| `base/reg-imm-block.yaml` | — | — | 待迁 |
| `base/reg-logic.yaml` | — | — | 待迁 |
| `base/reg-shift-extend.yaml` | 112 | — | 待迁 |
| `base/mem-rd.yaml` | 122 | — | 待迁 |
| `base/mem-ra.yaml` / `mem-rb.yaml` / `mem-rf.yaml` | — | — | 待迁 |
| `base/misc.yaml` | — | — | 待迁 |
| `base/reserved.yaml` | — | — | 待迁 |
| `fp/*.yaml`（`arith`/`convert`/`divrem`/`cond-assign`） | — | — | 待迁 |
| `bitcnt/`、`clmul/`、`fma/`、`minmax/`、`rev/`、`rol/`、`roundint/` 各自 | 414/81/… | — | 待迁 |

> 精确「文件 → id」清单由 `tools/testcases/` 现场导出（不写死在本表，避免漂移）。

## 6. 已完成

（空）
