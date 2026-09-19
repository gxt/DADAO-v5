# QEMU-011t: div/rem label 顺序定向回归验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-010t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-010t` 产出的 `translate.c` 中 `div.so`/`div.uo` 及固定位宽 `div.*` 的 `trans_*`
  - `.tao/knowledge/contract-isa.md` §3.1.5（乘除余：除零、`INT_MIN ÷ −1` → ILLI、截断方向、fault 不写目的）
  - `tests/vectors/isa/reg-arith.yaml`（div/rem 向量）
- 输出：验证报告（完成区记录），**不改任何补丁**（不修订 `series`）
- 约束：
  - **验证任务，不改补丁**：只对 `QEMU-010t` 实现中 `div.*`/`rem.*` 的行为做定向回归验证
  - 验证除数为零 → ILLI；`div.s` 的 `INT_MIN ÷ −1` → ILLI
  - 验证 label 顺序正确（无 dead code、正常路径与异常路径分离）
  - 给出可机械判定的命令与期望

## 背景（完整）

### 目标

对 `QEMU-010t` 实现的 `div.so`/`div.uo`（及固定位宽 `div.*`/`rem.*`）做定向回归验证：确认 TCG label 排列顺序正确，除零与 `INT_MIN ÷ −1` 检查正确分支，正常路径结果符合 §3.1.5。本任务**不修改任何补丁**，只验证实现任务已正确的行为。

### 设计理由

- 除法是唯一需要运行时异常检查的算术指令；label 结构必须正确，否则正常路径与异常路径混淆。
- 若 `QEMU-010t` 实现正确，本任务直接 PASS；若发现缺陷，登记为遗留。

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

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-026a-qemu-divs-divu-tcg-label-fix.md`（完整转述：背景、目标、接口说明书、验收、完成区与代码级 Architecture Review）。

## 交付物

- 验证报告（完成区记录）：div/rem label 顺序正确性、ILLI 触发、向量 PASS/FAIL 统计
- **不改补丁、不修订 series**

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **任务性质**：v5 本任务为**验证任务**（不改补丁）；0628 `DL-026a` 为修复任务（改补丁）。
2. **指令**：0628 `divs`/`divu` → v5 `div.so`/`div.uo`（orrr，MISC-octa）；另有固定位宽 `div.ub/sb/uw/sw/ut/st`。
3. **余数**：v5 将 `rem.*` 与 `div.*` 分离；`rem.*` 的除零/溢出检查同样适用。
4. **`INT_MIN` 常量**：按各 size 对应值（§3.1.5），不照抄 0628 的 64 位常量。

## 已知坑 / 结论

1. **label 顺序**：`gen_set_label` 出现在 `return` 之后即 dead code，TCG 报错或死循环。
2. **除零分支**：`brcond divisor==0 → label_div0`；异常路径与正常路径必须显式分隔。
3. **`INT_MIN ÷ −1`**：`div.s` 的唯一溢出情况，需双重 brcond 检测；`div.u` 无需。
4. **正常路径保护**：`div.u` 正常路径后须 `tcg_gen_br(label_ok)` 跳过异常块。
5. **若发现缺陷**：登记为遗留（完成区），由后续修复任务处理；本任务不自行改补丁。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-026a-qemu-divs-divu-tcg-label-fix.md`
- 本项目：`.tao/knowledge/contract-isa.md` §3.1.5；`tests/vectors/isa/reg-arith.yaml`
- 本项目：`.tao/tasks/qemu/QEMU-005t-RD整数语义.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --filter mnemonic:div` 并记录输出
2. div/rem semantic 向量全 PASS（exit=0），含除零与 `INT_MIN ÷ −1` 的 ILLI case（exit=0x88）
3. 正常路径结果符合 §3.1.5（truncate-toward-zero、余数符号 = 被除数符号）
4. 完成区含真实运行输出与 PASS/FAIL 统计
5. 若发现 `div.*`/`rem.*` 行为与 §3.1.5 不一致，在完成区登记为遗留

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
