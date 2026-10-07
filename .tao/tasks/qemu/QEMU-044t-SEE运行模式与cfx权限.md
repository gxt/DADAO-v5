# QEMU-044t: SEE/HEE 运行模式 + cfx 寄存器/掩码/权限/异常进入流程

**模块**：qemu
**项目里程碑**：M5
**依赖**：`SPEC-114t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t` 后的 `spec/DADAO-12-SEE-主管系统运行环境.md`（§1 四运行模式 + cfxha/cfxname 表；§3 cg0–cg7 共有寄存器〔`global_cfx_mask`/`cfx2rd|cfx2rc|cfxld|cfxst|trap|escape_cfx_mask`/`switch_run_mode`/`switch_cfx_mask`/`excp_vector`/`excp_cause_mask`；§3 cg4/5/6/7 `cfx_id`/`version`/`trap_num`/`excp_sync_num`/`excp_async_num`/`escape_num`/`scratch_regs_num`、`excp_prev_run_mode`/`prev_cfx_mask`/`cause_id`/`cause_ip`/`cause_info`/`pending`/`cause_nonmaskable`、`scratch_regs`、`sram_*`〕；§4 专有寄存器〔本 M5 只做 cfx0/1/2/3/63〕；§5 异常进入/退出流程伪代码【**权威依据**】）；`spec/DADAO-13`（cg3/hmon）；`spec/SimRISC-11-其它.md`（L80：`trap/escape/cfx2rd/cfx2rc` 可在任意运行模式执行，由 cfx mask 控制；L121：reserved cfxha ⇒ ILLI、不存在寄存器组合 ⇒ CFXREG）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，D9/D10/D11）+ `adr-0004` 修订。
  - `.tao/knowledge/contract-sbi.md`/`contract-see.md`（`SPEC-114t` 投影）。
  - 现有 `.work/source/qemu/target/dadao/**`（decode/translate/helper 结构，`ADR-0010` 的 `.c.inc` 拆分）与 `hw/dadao/dadao-machine.c`（复位值、exit port、fault→退出码映射，`ADR-0004` M1 冻结）。
- **输出**（组件源码改在 `.work/source/qemu`；**导出补丁**）：
  1. **四运行模式 `inner_run_mode`（2 位）**：user/jail/supv/hypv（编码 0/1/2/3，`DADAO-12 §1`）；**运行模式与 cfx 正交**（`SimRISC-11 L80`）。
  2. **cfx 寄存器文件（`cfx0/1/2/3/63` = umon/jmon/smon/hmon/power）**：
     - cg0–cg3（user/jail/supv/hypv）：每 mode 12 个共有寄存器（version / `global_cfx_mask` / 6 个指令类型 mask / `switch_run_mode` / `switch_cfx_mask` / `excp_vector` / `excp_cause_mask`）；复位值依 `DADAO-12 §3` 表（version `0x00090002`/`0x00070001` 等、mask 全 1、`switch_run_mode` 初值）。
     - cg4/5/6/7：`cfx_id`/`version`/`trap_num`/`excp_sync_num`/`excp_async_num`/`escape_num`/`scratch_regs_num`；异常现场寄存器（`excp_prev_*`/`cause_*`/`pending`/`cause_nonmaskable`）；暂存寄存器 `scratch_regs[0..N-1]`；SRAM 控制 regs。
     - `global_cfx_mask` 为**全局共享**（所有 cfx 同值，`DADAO-12 §3` 注）。
  3. **`inner_cfx_mask` / `inner_cfx_code`**（per-hart）内部寄存器与判断逻辑。
  4. **异常进入流程（`DADAO-12 §5` 伪代码，权威）**：步骤 1–10——确定 cfx（含 reserved ⇒ ILLI 重定向到当前 mode monitor；指令类型 mask 禁止 ⇒ ILLI；trap/cfx2* 按 cfxha 路由）→ 不可屏蔽判定 → `inner_cfx_mask`/`global_cfx_mask` 屏蔽判定（同步屏蔽 ⇒ ILLI 重定向）→ 异常原因 mask → 陷入计数递增 → 保存现场 → 模式/掩码切换（`switch_run_mode`/`switch_cfx_mask`）→ 保存 `cause_ip`/`cause_id`/`cause_info` → 跳异常向量。
     - **`switch_run_mode` 语义**须落地并在 spec/ADR 已讲清（`ADR-0020 D10`）。
  5. **权限异常**：cfx 访问权限（由 mask 控制）与 `DADAO-12 §2.2` 的 `NUPERM/NJPERM/NSPERM/NHPERM`（**PTBR 权限**层）的**关系须在实现与探针中讲清**（`INTEG-019k` 残留提醒：二者是不同层次；本 M5 权限范围 = `cfx0/1/2/3/63`，`cfx_ptw`(=cfx4)/MMU/页表步进**不在 M5**）。
  6. **未实现 cfx ⇒ `CFXREG` 异常**（出处 `spec/DADAO-22-SBI-主管系统二进制接口.md:58`；佐证 `DADAO-12:373`、`SimRISC-11:121`）：访问 `cfxha ∈ {7..14,19..61}`（reserved）⇒ **ILLI**（`SimRISC-11 L121`）；访问**未实现但已分配的 cfx**（如 cfx4/cfx5…超出本 M5 集合）⇒ **`CFXREG`**（依契约实现对不存在/超出数量的寄存器组合）。
  7. **探针**：`tools/qemu/min_rom_probe_044t.py`（或 `.work/evidence/QEMU-044t/`）——四模式切换、mask 屏蔽（同步 ⇒ ILLI 重定向）、`switch_run_mode`、权限反例（未授权 ⇒ `NU/J/SP/HPERM` 或 CFXREG）、异常进入流程步骤 1–10 的可观测子集。
- **约束（硬）**：
  - **权限范围 = 只做 `cfx0/1/2/3/63`**（`INTEG-019k` 裁定 4）；**`cfx_ptw`(=cfx4)/MMU/页表步进不在本 M5**。`smon`(cfx2) 相关寄存器按范围实现，但 M5 流程 hypv→user 直跳、**不启用 supv**（`INTEG-019k` 裁定 5），bootrom/流程面不使用 smon。
  - **不改 guest 标量指令执行语义**（`target/dadao` 现有 decode/trans 不动，除本任务新增 cfx/模式相关）；**不改 exit port/fault→退出码映射**（`ADR-0004`/`ADR-0011`）。
  - **`trap`/`escape` 执行语义、`cfx2rd`/`cfx2rc` 执行、semihosting 不在本任务**（分别归 `QEMU-045t`/`QEMU-046t`）；本任务提供其依赖的寄存器文件与异常进入流程。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS`（默认 8）限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-044t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；用 `cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **四运行模式**：探针可设置/读取 `inner_run_mode`（经 `switch_run_mode` + 异常进入流程），四模式编码正确（真实输出）。
3. **cfx 寄存器**：`cfx0/1/2/3/63` 的 cg0–cg7 寄存器读写正确（含 `global_cfx_mask` 共享、`trap_num`/`escape_num` 递增、`scratch_regs` 数量）；复位值依 `DADAO-12 §3`。
4. **mask 屏蔽**：`global_cfx_mask`（及指令类型 mask）置位 ⇒ 目标非自身 cfx 的同步访问**触发 ILLI 并重定向到当前 mode monitor**（真实探针）。
5. **`switch_run_mode`**：异常进入后运行模式切换为该 cfx 的 `switch_run_mode` 值（真实输出）。
6. **权限反例**：未授权模式/未实现 cfx 访问 ⇒ 依契约触发 `NU/J/SP/HPERM` 或 **`CFXREG`**；reserved cfxha ⇒ **ILLI**（≥3 类，真实输出）。
7. **异常进入流程**：探针覆盖步骤 1–10 的可观测子集（确定 cfx / 不可屏蔽 / mask / 原因 mask / 计数 / 现场 / 模式切换 / cause_ip/id/info / 跳向量）。
8. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（15/15）/`make test-elf`（5/5）EXIT=0（说明 M1–M4 路径未回归）；`check-patch-tree` EXIT=0。
9. **一键证据脚本**：`.work/evidence/QEMU-044t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（关 mask 判定/改 `switch_run_mode` 初值/放宽 reserved 判定 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
10. **无残留**：`git status --untracked-files=all` 仅组件补丁 + 探针 + 本任务书；`.work/source/qemu` worktree clean。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改 mask/权限判定 → 重建 → FAIL → 还原+重建 → 回绿）+ 约束核验（不改标量语义/exit-port）+ 判决）
