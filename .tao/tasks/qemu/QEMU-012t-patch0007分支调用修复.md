# QEMU-012t: branch PC 公式 + call RA 修复

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-011t`、`TESTSUITE-008t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-011t` 产出的 `.work/source/qemu` 工作树（控制流实现已在，但分支 PC 公式/返回地址需修正）
  - `.tao/knowledge/contract-isa.md` §5.1（条件跳转地址计算）、§5.2（无条件跳转）、§5.3（函数调用与压栈）、§5.4（函数返回）
  - `tests/vectors/isa/control-flow.yaml`（`TESTSUITE-008t` 产出，独立 oracle）
  - `.tao/knowledge/adr-0004-test-machine.md`（fault/exit 可观测）
- 输出：
  - `.work/source/qemu` 中的修复 commit（branch PC + call 返回地址）
  - `components/qemu/patches/0007-dadao-branch-call-fix.patch`（由该 commit 导出）
  - `components/qemu/patches/series` 加入 `0007`
- 约束：
  - 分支/调用地址公式以 §5 与 `control-flow.yaml` 向量为准，**不得直接照抄 0628 的 `pc_next+4` 基准**
  - not-taken 必须推进到下一指令（不得重复执行同一条）
  - 只导出本任务相关改动，不夹带无关文件
  - 导出后 patch 可干净 `git am`；完成后不自行 commit 主仓库

## 背景（完整）

### 目标

将控制流的 PC 公式修正（条件分支 taken/not-taken、返回地址）固化为可复现补丁 `0007`，并更新 `series`。0628 对应任务 `DL-032a` 把工作树中未提交的 `translate.c` 修复（来自 `DL-028a` 分支 PC + `DL-030a` call 返回地址）提交并导出为 `0007-dadao-branch-call-fix.patch`，经代码级评审 Accepted。

### 设计理由

- 0628 的测试套件依赖这些修复（137/137 PASS），但修复一度不在 patch series 中，导致从干净基线重建后回归。必须固化进补丁序列。
- 分支 PC 公式是控制流正确性的核心：not-taken 不推进会重复执行同一条；taken 基准错误会跳错地址。

### 关键概念 / 数据

**v5 权威公式（§5）**：
- 条件跳转：`if (cond) PC = rb0 + sign_extend(imm << 2)`；`rb0` 为 PC。
- `jump-iiii`：`PC = rb0 + sign_extend(imms24 << 2)`。
- `jump-rrii`/`call-rrii`：`PC = rbha + rdhb + sign_extend(imms12 << 2)`（48 位）。
- `call`：计算返回地址并压入 ra63（按 §5.3 压栈流程），再跳转。
- `ret`：`PC = ra63 低 48 位`，按 §5.4 弹栈。

**QEMU 实现要点**：
- 翻译期 `ctx->base.pc_next` = 下一指令地址；当前指令地址 = `pc_next - 4`。
- **not-taken**：PC = 下一指令（`pc_next`），必须显式推进。
- **taken**：按 §5 的 `rb0 + imm*4` 计算；`rb0` 的取值语义（当前指令地址）须与 `control-flow.yaml` 向量核对。
- **call 返回地址**：返回地址 = `call` 的下一条指令地址（即 `pc_next`），压栈格式按 §5.3（含引用计数）。
- 实现后须经 `control-flow.yaml` 验证；若向量（独立 oracle）与实现不一致，以向量与 §5 为准修正，并在完成区记录推导。

**0628 参考（仅对照，不照抄）**：not-taken `pc_next → pc_next+4`；taken `pc_next-4+imm*4 → pc_next+4+imm*4`（其约定为 PC+4 基准）；`call` `ra[63] = pc_next → pc_next+4`。v5 必须重新推导。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-032a-qemu-patch-0007.md`（完整转述：背景、提交/导出/series 步骤、约束、验收、完成区与代码级 Architecture Review）。
- DADAO-0628：`code-agent/tasks/DL-030a-call-ret-semantic.md`（call/ret 返回地址修正）。
- DADAO-0628：`code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`（分支向量与 PC 公式）。
- 本项目：`TESTSUITE-008t`（控制流向量，v5 独立 oracle）。

## 交付物

- `.work/source/qemu` 的修复 commit（branch PC + call 返回地址），提交信息说明推导依据。
- `components/qemu/patches/0007-dadao-branch-call-fix.patch`：由该 commit 导出（`git format-patch`），含 `From:`/`Subject:`。
- `components/qemu/patches/series`：加入 `0007`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **PC 基准**：0628 经验为 PC+4 基准（`pc_next+4`）；v5 §5 为 `rb0 + imm*4`。v5 须以 §5 与 `TESTSUITE-008t` 向量为准，重新推导并记录。
2. **助记符**：`brz/brnz/brn/brnn/brp/brnp/breq/brne` → `br.z/br.nz/br.n/br.nn/br.p/br.np/br.eq/br.ne`；新增 `br.z-rb`/`br.nz-rb`。
3. **call 返回地址与压栈**：v5 §5.3 要求引用计数与移位压栈（`QEMU-008t`），返回地址为 `call` 下一条指令。
4. **补丁编号**：v5 为 `0007`（0628 的 `0007` 是 div label 修复，`0008` 才是 branch-call fix；v5 序列不同，以本节交付物为准）。
5. **范围**：v5 只固化分支/调用修复；0628 `DL-026a` 夹带的 `helper_exit`/reset PC/tlb_fill/machine 改动在 v5 不属本任务。

## 已知坑 / 结论

摘自 0628 `DL-032a` 完成区与代码级 Architecture Review：

1. **修复必须进 series**：工作树未提交修复会随重建丢失，导致回归。
2. **not-taken 推进**：写 `pc_next`（不推进）会重复执行同一条分支。
3. **taken 基准**：以 §5/向量为准，不照抄 0628 的 `pc_next+4`。
4. **call 返回地址**：返回地址为 `call` 下一条指令；与 §5.3 压栈格式一致。
5. **导出验证**：`patch` 含 `From:`/`Subject:`；`series` 末尾有 `0007`；重建后控制流向量全 PASS。
6. **不夹带无关改动**：导出前 `git status`/`git diff` 确认只含目标文件。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-032a-qemu-patch-0007.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-030a-call-ret-semantic.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-028a-control-flow-yaml-tdd.md`
- 本项目：`.tao/knowledge/contract-isa.md` §5；`tests/vectors/isa/control-flow.yaml`；`.tao/tasks/testsuite/TESTSUITE-008t-控制流向量TDD.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.work/source/qemu` 存在 branch PC + call 返回地址修复 commit，提交信息含推导依据
2. `components/qemu/patches/0007-dadao-branch-call-fix.patch` 由该 commit 导出，含 `From:`/`Subject:`；`series` 末尾加入 `0007`
3. patch 干净 `git am`；不夹带无关文件
4. not-taken 推进到下一指令；taken 公式与 §5 及 `control-flow.yaml` 向量一致
5. `call` 返回地址正确，与 §5.3 一致
6. `make build-qemu` PASS；`control-flow.yaml` 全量 PASS（若 harness 未就绪，记录依赖并保留可复现命令）
7. 完成区含真实构建/运行输出；未自行 commit 主仓库

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
