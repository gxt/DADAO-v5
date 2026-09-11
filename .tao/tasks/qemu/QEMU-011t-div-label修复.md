# QEMU-011t: div.so/div.uo TCG label 修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-010t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-010t` 产出的 `translate.c` 中 `div.so`/`div.uo`（0628 名 `divs`/`divu`）及固定位宽 `div.*` 的 `trans_*`
  - `.tao/knowledge/contract-isa.md` §3.1.5（乘除余：除零、`INT_MIN ÷ −1` → ILLI、截断方向、fault 不写目的）
  - `tests/vectors/isa/rd-arith.yaml`（div/rem 向量）
- 输出：`components/qemu/patches/0006-dadao-div-label-fix.patch`、`components/qemu/patches/series`、向量状态更新
- 约束：
  - 不改变 ISA 语义：除数为零 → ILLI；结果按 §3.1.5 写目标
  - `gen_set_label` 必须在 `gen_exception_illegal` 之后、`return true` 之前；不得出现在 `return` 之后（dead code）
  - 正常路径须用 `tcg_gen_br` 跳过异常路径
  - 只改本任务涉及的 `div.*`（及必要 helper）；不夹带无关改动
  - 完成后不自行 commit

## 背景（完整）

### 目标

修复 `div.so`/`div.uo`（0628 `trans_divs`/`trans_divu`）的 TCG label 排列顺序，使除零与 `INT_MIN ÷ −1` 检查正确分支；同步修复固定位宽 `div.*`。0628 对应任务 `DL-026a` 修复 label 顺序并经代码级评审 Accepted。

### 设计理由

- 0628 的 `gen_set_label(l1)` 被放在 `return true` 之后（dead code），导致 TCG SIGABRT（label 未使用）或 brcond 跳到未定义位置 → 无限循环 → 5 秒 timeout。
- 除法是唯一需要运行时异常检查的算术指令；label 结构必须正确，否则正常路径与异常路径混淆。

### 关键概念 / 数据

**正确控制流结构**（以 `div` 为例）：
```
check 目的/双目标 ILLI
load dividend, divisor, 常量
brcond divisor==0 → label_div0
（div.s 时）brcond dividend!=INT_MIN → label_ok
（div.s 时）brcond divisor!=-1 → label_ok
   正常除法路径：
       div/rem（或 divu/remu）
       store 结果
       br label_ok
label_div0:
   gen_exception_illegal
label_ok:
   return true
```
- `gen_set_label(label_ok)` 必须在 `gen_exception_illegal` 之后、`return true` 之前；`gen_set_label(label_div0)` 紧跟 `brcond`（不在 `return` 后）。
- `div.uo`（无符号）仅需除零检查；`div.so`（有符号）还需 `INT_MIN ÷ −1`。
- 固定位宽 `div.ub/sb/uw/sw/ut/st` 的 `INT_MIN` 与位宽对应，按 §3.1.5。

**向量**：`rd-arith.yaml` 中 div/rem 的 semantic/encoding 向量从 `deferred` 改回 `active`，运行全通。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-026a-qemu-divs-divu-tcg-label-fix.md`（完整转述：背景、目标、接口说明书、验收、完成区与代码级 Architecture Review）。

## 交付物

- `components/qemu/patches/0006-dadao-div-label-fix.patch`：`target/dadao/translate.c` 中 `div.*` 的 label 修复。
- `tests/vectors/isa/rd-arith.yaml`：div/rem 向量 `deferred` → `active`。
- `components/qemu/patches/series`：加入 `0006`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **指令**：0628 `divs`/`divu` → v5 `div.so`/`div.uo`（orrr，MISC-octa）；另有固定位宽 `div.ub/sb/uw/sw/ut/st`（MISC-byte/wyde/tetra），须一并检查。
2. **余数**：v5 将 `rem.*` 与 `div.*` 分离；`rem.*` 的除零/溢出检查同样适用。
3. **`INT_MIN` 常量**：按各 size 对应值（§3.1.5），不照抄 0628 的 64 位常量。
4. **补丁编号**：v5 为 `0006`（0628 的对应修复在其 `0007`，因前置补丁序列不同）。
5. **范围收窄**：0628 `DL-026a` 实际超出范围地修改了 `insn.decode`/`helper_exit`/`EXCP_EXIT`/reset PC/`tlb_fill`/machine 等；v5 本任务只做 div label 修复，其余归 `QEMU-003t`/`QEMU-008t`。

## 已知坑 / 结论

摘自 0628 `DL-026a` 完成区与代码级 Architecture Review：

1. **label 顺序**：`gen_set_label` 出现在 `return` 之后即 dead code，TCD 报错或死循环。
2. **除零分支**：`brcond divisor==0 → label_div0`；异常路径与正常路径必须显式分隔。
3. **`INT_MIN ÷ −1`**：`div.s` 的唯一溢出情况，需双重 brcond 检测；`div.u` 无需。
4. **正常路径保护**：`div.u` 正常路径后须 `tcg_gen_br(label_ok)` 跳过异常块。
5. **死标签**：0628 遗留 `l_overflow` 死标签（无害）；v5 应避免。
6. **范围蔓延教训**：0628 该任务实际改动 7 个文件（约束为 1），v5 应严格限定范围。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-026a-qemu-divs-divu-tcg-label-fix.md`
- DADAO-0628：`.work/DADAO-0628/components/qemu/patches/0007-target-dadao-DL-026a-divs-divu-TCG-label-fix-machine.patch`（仅参考结构）
- 本项目：`.tao/knowledge/contract-isa.md` §3.1.5；`tests/vectors/isa/rd-arith.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-005t-RD整数语义.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `components/qemu/patches/0006-dadao-div-label-fix.patch` 存在且干净 apply；`series` 已加入
2. `div.so`/`div.uo`（及固定位宽 `div.*`）label 顺序正确，无 dead code；除零与 `INT_MIN ÷ −1` → ILLI
3. 正常路径结果符合 §3.1.5；fault 时目的不写
4. `rd-arith.yaml` 相关向量 `active` 且运行 PASS，不引入其他回退
5. `make build-qemu` PASS
6. 完成区含真实构建/运行输出；未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
