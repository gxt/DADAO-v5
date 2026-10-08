# QEMU-045t: `trap`/`escape` 语义 + `cfx2rd`/`cfx2rc` 执行

**模块**：qemu
**项目里程碑**：M5
**依赖**：`SPEC-115t`、`SPEC-114t`、`QEMU-044t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-115t`（4 条 re-scope）+ `SPEC-114t`（SEE §5 正文）+ `QEMU-044t`（cfx 寄存器文件 + 异常进入流程 + 权限/mask）。
  - `spec/SimRISC-11-其它.md`（`trap cfxHA, immu18`；`escape cfxHA, [excp_cause_ip, imms20]`；`cfx2rc`/`cfx2rd cfxHA, cgHB, rcHC, rdHD`；简化 regname 写法；L80 任意模式执行；L121 reserved/不存在组合）。
  - `spec/DADAO-22-SBI §1`（调用约定：`trap` 陷入目标 cfx；被调方 `escape cfxha, [excp_cause_ip, 4]` 返回下一条；参数与 ABI 一致）；`spec/DADAO-12 §5`（异常进入流程步骤 1–10；**异常退出流程** §5 伪代码——步骤 0 `escape` cfx mask 检查 + 1 恢复 `prev_cfx_mask` + 2 恢复 `prev_run_mode` + 3 `escape_num`++ + 4 计算返回地址 `excp_cause_ip + (imms18<<2)`）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D10 两条路**）。
  - `contracts/opcodes.yaml`（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx` 编码）。
- **输出**（组件源码改在 `.work/source/qemu`；**导出补丁**）：
  0. **范围调整（见「审阅记录 · 044t/045t 边界处置说明」）**：`QEMU-044t` 已把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 **decode→流程接线与基础执行** 落地（`trans_*_cfx` 由 ILLI 桩改为 `gen_helper_cfx_*` + `exit_tb`；`helper_cfx_trap`/`helper_cfx_escape`/`helper_cfx2rd`/`helper_cfx2rc`，见 044t 完成区实测）。本任务**不再重复实现**这些触发路径，只在其**基线**上**深化并验证完整语义 + 交付独立专探针/向量**。
  1. **在 044t 基线上深化/验证完整语义**（以读写 + **回读校验**为主；发现 044t 基线缺口时补齐）：
     - **`trap` 完整语义（一般 trap）**：`trap cfxHA, immu18`（`immu18[17:16] ≠ 2'b11`）→ `cause = CFXTRAP`（`1<<0`）→ **进入该 cfx 的向量**（`cfx_⟨cfxname⟩_<mode>_excp_vector`）；核对 `cause_id`/`cause_ip`/`cause_info`；reserved cfxha（7–14、19–61）⇒ **ILLI**（重定向到当前 mode monitor）；指令类型 `trap_cfx_mask` 禁止 ⇒ **ILLI**。
     - **`escape` 完整语义（异常退出流程）**：步骤 0 `escape_cfx_mask`（**跨 cfx**：非自身 cfxha 且禁止 ⇒ ILLI）；1 恢复 `inner_cfx_mask`←`excp_prev_cfx_mask`；2 恢复 `inner_run_mode`←`excp_prev_run_mode`；3 `escape_num`++；4 `PC ← excp_cause_ip + (imms18 << 2)`（**含负偏移回退**：`imms18` 18 位**有符号**展开、字节偏移 `%4==0`，与 `Toolchain-01 §3.2` 一致）。
     - **`cfx2rd`/`cfx2rc` 全寄存器面深化**：`cfx2rd cfxHA, cgHB, rcHC, rdHD`（读 cfx 寄存器 → `rdHD`）；`cfx2rc`（写 `rdHD` → cfx 寄存器）；读写覆盖 cfx 的 cg0–cg7 **全集**（含 RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv）；**reserved cfxha ⇒ ILLI**；读写不存在/超出数量的寄存器组合 ⇒ **CFXREG**（`DADAO-12:373`/`SimRISC-11:121`）；经 `set.zw`/`or.w` 构造并**回读校验**。**简化 regname 写法**在汇编期已展开（`LLVM-060t`），QEMU 侧只见标准三操作数编码。
  2. **专探针/向量**：`tools/qemu/min_rom_probe_045t.py`（或 `.work/evidence/QEMU-045t/`）——一般 trap 进入向量并可由 `escape` 返回；`escape` 恢复模式/掩码、`escape_num` 递增、**负偏移回退**、**跨 cfx escape**；`cfx2rd`/`cfx2rc` **全寄存器面**读写正确；reserved ⇒ ILLI；不存在组合 ⇒ CFXREG。
- **边界（硬）**：
  - **semihosting 短路（`immu18[17:16] == 2'b11`）不在本任务**：其“QEMU 译码层短路、不进入向量、直接服务并按 PC 步进返回”归 **`QEMU-046t`**。本任务只做**一般 trap**（进入向量）。
  - **触发路径已由 `QEMU-044t` 落地**：本任务**不重复实现** `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 decode→流程接线（见「审阅记录 · 044t/045t 边界处置说明」），只在其基线上**深化/验证 + 专探针**；**不改** `QEMU-044t` 已交付的 cfx 寄存器文件/异常进入流程语义；**不改** M1–M4 标量语义/exit port。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS` 限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-045t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；`cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **一般 trap 进入向量**：`trap cfx0, immu18`（`immu18[17:16]≠2'b11`）→ `cause=CFXTRAP`、进入 `cfx_umon`（或对应 cfx）的 `excp_vector`（探针观测 PC/`cause_id`；真实输出）。
3. **`escape` 返回**：handler 内 `escape cfx0, [excp_cause_ip, 4]` → 返回到 trap 下一条指令；`escape_num` 递增；`prev_run_mode`/`prev_cfx_mask` 恢复（真实探针）。
4. **`escape` 偏移**：`imms20` 字节偏移（`%4==0`）正确反映到 `PC = cause_ip + (imms18<<2)`；含**负偏移回退**用例（真实输出）。
5. **`cfx2rd`/`cfx2rc`**：读写 `cfx_umon`/`cfx_power` 某寄存器值正确（含经 `set.zw`/`or.w` 构造并回读校验）；给真实输出。
6. **reserved / 不存在组合**：reserved cfxha ⇒ **ILLI**（`0x88`）；读写不存在/超出数量寄存器组合 ⇒ **CFXREG**（≥2 类，真实输出）。
7. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（15/15）/`make test-elf`（5/5）EXIT=0；`check-patch-tree` EXIT=0。
8. **一键证据脚本**：`.work/evidence/QEMU-045t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（把 `escape` 偏移 `imms18<<2` 改成固定值/关掉 reserved 判定 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
9. **无残留**：`git status --untracked-files=all` 仅组件补丁 + 探针 + 本任务书；`.work/source/qemu` worktree clean。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改 escape 偏移/关 reserved 判定 → 重建 → FAIL → 还原+重建 → 回绿）+ 约束核验（semihosting 未越界/不改标量语义）+ 判决）

#### 044t/045t 边界处置说明（architect，2026-10-08，**只追加**）

**背景**：engineer 为使 `QEMU-044t` 验收 2–7 可观测，把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 **decode→异常流程接线** 一并实现（044t 完成区「新发现 4」已登记，供 architect 判定）。经核 `QEMU-045t` 任务书与该实现的**实际交叉面**，二者输出重叠。

**依据（044t 实测交付，非转述）**：
- `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`：`trans_trap_ciii_cfx`/`trans_escape_ciii_cfx`/`trans_cfx2rd_crrr_cfx`/`trans_cfx2rc_crrr_cfx` 由 `gen_exception_illegal`（ILLI 桩）改为 `gen_helper_cfx_*` + `tcg_gen_exit_tb`（`cfxld`/`cfxst` 仍 ILLI）。
- `components/qemu/patches/target/dadao/helper.c.patch`：新增 `helper_cfx_trap`（一般 trap ⇒ `CFXTRAP` 进入向量；**reserved ⇒ ILLI**；`trap_mask` 禁止 ⇒ ILLI；未实现 cfx ⇒ CFXREG；semihosting tag ⇒ 显式 ILLI）、`helper_cfx_escape`（`DADAO-12 §5` 退出流程步骤 0–4，含 **18 位有符号展开** 与 **跨 cfx escape mask** 检查）、`helper_cfx2rd`/`helper_cfx2rc`（经 `cfx_reg_ptr` 覆盖 cg0–cg7 全寄存器面 + RO/RW + `scratch_regs_num` 边界 + cg3 仅 hypv，异常组合 ⇒ CFXREG）。
- 044t 完成区实测：探针 13/13 PASS、`make check` EXIT=0 等（见 044t 完成区）。

**调整决定（最小化收缩 045t 范围）**：045t 依赖 044t 之上，**044t 已落地的触发路径与基础执行不再重复实现**；045t 收敛为「**在 044t 基线上深化并验证完整语义 + 交付独立专探针/向量**」，保留其**独有内容**：
- `escape` **负偏移回退**（`imms18` 有符号展开、`%4==0`）与 **跨 cfx** escape mask（步骤 0）；
- `trap` **完整语义**（一般 trap 进入向量 + `cause_id`/`cause_ip`/`cause_info` 回读；reserved/`trap_mask` ⇒ ILLI）；
- `cfx2rd`/`cfx2rc` **全寄存器面深化**（cg0–cg7、RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv、CFXREG 组合）；
- **专探针/向量** `tools/qemu/min_rom_probe_045t.py`（一般 trap 向量往返、负偏移、跨 cfx、全寄存器面）。

**边界与影响**：
- **M5 总范围不变**：045t 的语义能力仍在 M5 内（044t 落地 + 045t 验证/深化），**未扩大或缩小** M5 覆盖；仅调整两任务之间的实现/验证分工。
- **未改 `spec/`**；semihosting（`immu18[17:16] == 2'b11`）仍归 `QEMU-046t`。
- 045t **状态**保持 `待开始`（尚未下发）。
- 本说明**只追加**，不改写 045t 既有内容。
