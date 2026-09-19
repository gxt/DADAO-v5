# QEMU-012t: 分支 PC 公式 + call RA 定向回归验证

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-011t`、`TESTCASES-005t`、`TESTCASES-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-011t` 产出的 `.work/source/qemu` 工作树（控制流实现已在，含分支 PC 公式与 call RA）
  - `.tao/knowledge/contract-isa.md` §5.2（条件跳转）、§5.3（无条件跳转）、§5.4（函数调用）、§5.5（函数返回）
  - `tests/vectors/isa/ctrl-br.yaml`、`tests/vectors/isa/ctrl-jump.yaml`、`tests/vectors/isa/ctrl-call.yaml`、`tests/vectors/isa/ctrl-ret.yaml`（`TESTCASES-005t`/`TESTCASES-006t` 产出，独立 oracle）
  - `.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测）
- 输出：验证报告（完成区记录），**不改任何补丁**（不修订 `series`）
- 约束：
  - **验证任务，不改补丁**：只对实现中分支 PC 公式与 call RA 的行为做定向回归验证
  - 验证 taken 公式与 §5 及向量一致
  - 验证 not-taken 推进到下一指令
  - 验证 `call` 返回地址正确（压入 ra63）
  - 给出可机械判定的命令与期望

## 背景（完整）

### 目标

对实现的控制流做定向回归验证：确认分支 taken/not-taken PC 公式、call 返回地址与 §5 及独立向量一致。本任务**不修改任何补丁**，只验证实现任务已正确的行为。

### 设计理由

- 分支 PC 公式是控制流正确性的核心：not-taken 不推进会重复执行同一条；taken 基准错误会跳错地址。
- call 返回地址正确性由 `call→ret→landing` 往返隐式验证。
- 若实现正确，本任务直接 PASS；若发现缺陷，登记为遗留。

### 关键概念 / 数据

**v5 权威公式（§5）**：
- 条件跳转：`if (cond) PC = rb0 + sign_extend(imm << 2)`；`rb0` 为 PC。
- `jump-iiii`：`PC = rb0 + sign_extend(imms24 << 2)`。
- `jump-rrii`/`call-rrii`：`PC = rbha + rdhb + sign_extend(imms12 << 2)`（48 位）。
- `call`：计算返回地址并压入 ra63（按 §5.3 压栈流程），再跳转。
- `ret`：`PC = ra63 低 48 位`，按 §5.4 弹栈。

**验证方法**：
- `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-br.yaml tests/vectors/isa/ctrl-jump.yaml tests/vectors/isa/ctrl-call.yaml tests/vectors/isa/ctrl-ret.yaml` 全量 PASS。
- taken case：验证 PC 跳到 `expected_pc`（poison pattern 中跳过 `illi`）。
- not-taken case：验证 PC 推进到下一指令（不踩 poison `illi`）。
- call/ret case：验证 `call→ret→landing` 完整往返 PASS。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-032a-qemu-patch-0007.md`（完整转述：背景、提交/导出/series 步骤、约束、验收、完成区与代码级 Architecture Review）。
- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（call/ret 返回地址修正）。

## 交付物

- 验证报告（完成区记录）：分支 PC 公式正确性、call RA 正确性、向量 PASS/FAIL 统计
- **不改补丁、不修订 series**

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **任务性质**：v5 本任务为**验证任务**（不改补丁）；0628 `DL-032a` 为修复任务（改补丁+导出）。
2. **PC 基准**：0628 经验为 PC+4 基准（`pc_next+4`）；v5 §5 为 `rb0 + imm*4`，以 §5 与向量为准。
3. **助记符**：`brz/brnz/…` → `br.z/br.nz/…`；新增 `br.z-rb`/`br.nz-rb`。
4. **call 返回地址与压栈**：v5 §5.3 要求引用计数与移位压栈，返回地址为 `call` 下一条指令。

## 已知坑 / 结论

1. **not-taken 推进**：写 `pc_next`（不推进）会重复执行同一条分支。
2. **taken 基准**：以 §5/向量为准，不照抄 0628 的 `pc_next+4`。
3. **call 返回地址**：返回地址为 `call` 下一条指令；与 §5.3 压栈格式一致。
4. **若发现缺陷**：登记为遗留（完成区），由后续修复任务处理；本任务不自行改补丁。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-032a-qemu-patch-0007.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- 本项目：`.tao/knowledge/contract-isa.md` §5；`tests/vectors/isa/ctrl-br.yaml`；`tests/vectors/isa/ctrl-jump.yaml`；`tests/vectors/isa/ctrl-call.yaml`；`tests/vectors/isa/ctrl-ret.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 运行 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-br.yaml tests/vectors/isa/ctrl-jump.yaml tests/vectors/isa/ctrl-call.yaml tests/vectors/isa/ctrl-ret.yaml` 并记录输出
2. 全量 PASS（encoding + semantic + legality），0 FAIL
3. taken case 的 `expected_pc` 与 §5 公式一致
4. not-taken case PC 推进到下一指令（不踩 poison `illi`）
5. `call→ret→landing` 往返 PASS（证明 RA 压栈/弹栈正确）
6. 完成区含真实运行输出与 PASS/FAIL 统计
7. 若发现分支/call 行为与 §5 不一致，在完成区登记为遗留

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
