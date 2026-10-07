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
  1. **`trap` 译码 + 路由（一般 trap）**：`trap cfxHA, immu18`（`immu18[17:16] ≠ 2'b11`）→ 按 cfxha 路由到目标 cfx，`cause = CFXTRAP`（`1<<0`）→ **走 spec 的异常进入流程（`DADAO-12 §5`，含步骤 10「跳转至异常向量」）**——**进入该 cfx 的向量**（`cfx_⟨cfxname⟩_<mode>_excp_vector`）。
     - 特例：reserved cfxha（7–14、19–61）⇒ **ILLI**（重定向到当前 mode monitor）；指令类型 `trap_cfx_mask` 禁止 ⇒ **ILLI**。
  2. **`escape` 执行（异常退出流程）**：步骤 0 检查 `escape_cfx_mask`（非自身 cfxha 且禁止 ⇒ ILLI）；1 恢复 `inner_cfx_mask`←`excp_prev_cfx_mask`；2 恢复 `inner_run_mode`←`excp_prev_run_mode`；3 `escape_num`++；4 `PC ← excp_cause_ip + (imms18 << 2)`（**字节偏移 = imms18×4**，与 `Toolchain-01 §3.2` 一致）。
  3. **`cfx2rd`/`cfx2rc` 执行**：`cfx2rd cfxHA, cgHB, rcHC, rdHD`（读 cfx 寄存器 → `rdHD`）；`cfx2rc`（写 `rdHD` → cfx 寄存器）。**reserved cfxha ⇒ ILLI**；**读写不存在/超出数量的寄存器组合 ⇒ CFXREG**（`DADAO-12:373`/`SimRISC-11:121`）；**简化 regname 写法**在汇编期已展开（`LLVM-060t`），QEMU 侧只见标准三操作数编码。
  4. **与 `QEMU-044t` 的异常进入流程复用**：`trap`/`cfx2rd`/`cfx2rc` 的路由与 mask/权限判定**复用** `QEMU-044t` 的流程实现，本任务补 cause 与向量跳转的**触发路径**。
  5. **探针**：`tools/qemu/min_rom_probe_045t.py`（或 `.work/evidence/QEMU-045t/`）——一般 trap 进入向量并可由 `escape` 返回；`escape` 恢复模式/掩码、`escape_num` 递增、按 `imms20`/`imms18` 跳转（含负偏移回退）；`cfx2rd`/`cfx2rc` 读写正确；reserved ⇒ ILLI；不存在组合 ⇒ CFXREG。
- **边界（硬）**：
  - **semihosting 短路（`immu18[17:16] == 2'b11`）不在本任务**：其“QEMU 译码层短路、不进入向量、直接服务并按 PC 步进返回”归 **`QEMU-046t`**。本任务只做**一般 trap**（进入向量）。
  - **不改** `QEMU-044t` 已交付的 cfx 寄存器文件/异常进入流程语义（在其之上补 trap/escape/cfx2* 触发路径）；**不改** M1–M4 标量语义/exit port。
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
