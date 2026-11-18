# m14-spec-009: `escape` 恢复 `inner_cfx_code`（补 `excp_prev_cfx_code`，spec + QEMU）

**模块**：spec
**项目里程碑**：M14
**依赖**：无（与 `m14-linux-017` 串行：本任务改 QEMU，017 只读它）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（spec + 组件补丁 + 契约）
**状态**：待开始

## 背景与授权（用户 2026-11-18 裁定 B）

`m14-linux-017` 的 F36 定位：同步帧内到达 tick ⇒ `§5.2 步骤 6` 把 `inner_cfx_code` 改为目标 cfx ⇒ 该帧随后的 `escape cfx_smon` 必然报 `CFXESC`（`§5.3 步骤 0`：`cfxha != inner_cfx_code`）。实测关闭该 tick 后同路径连做 3 次 escape 全成功。

**spec 缺口**：`§5.3` 对 `inner_run_mode` 有保存/恢复（`excp_prev_run_mode`），对 `inner_cfx_code` **只有保存、没有恢复**。

**用户裁定（2026-11-18，逐条）**：

1. **采纳方案 B**（改 spec + QEMU）。
2. `excp_prev_cfx_code` **放 cg5，与 `excp_prev_run_mode` 并列**（即现 `cg5 rc1` 的 reserved 槽）。
3. **版本号不变**（`DADAO-12` 不升版，只加附录变更条目）。
4. QEMU 改完后 017 才继续。

## 目标（spec + QEMU 同笔）

### 1. `spec/DADAO-12-SEE-主管系统运行环境.md`

- **§3.6 cg5 表**：把 `rc1` 从 `reserved` 改为
  `excp prev cfx code` / `cfx_⟨cfxname⟩_excp_prev_cfx_code` / 初始 `0` / `RW` / 「异常前当前核芯功能扩展编号，硬件陷入时保存，软件可写」。
- **§5.2 步骤 5（保存现场）**：增加「`excp_prev_cfx_code` 记录异常前的 `inner_cfx_code`」。
- **§5.2 伪代码**：`cfx_⟨cfxname⟩_excp_prev_cfx_code <= inner_cfx_code`（在 `inner_cfx_code` 被改写**之前**）。
- **§5.3 步骤 2（恢复运行模式）**：改为「恢复运行模式**与当前 cfx**」：`inner_run_mode <= prev_run_mode`、`inner_cfx_code <= prev_cfx_code`。
- **§5.3 伪代码**：加 `inner_cfx_code <= cfx_⟨cfxname⟩_excp_prev_cfx_code`。
- **附录变更记录**：加一条内容条目（**版本号不变**）；说明动机（异常帧被异步事件污染后无法正确返回）与影响（`escape` 后 `inner_cfx_code` 与 `run_mode` 同进退）。
- 同步 `§5.3` 顶部那句「`escape` 恢复 `excp_prev_run_mode`，以及 trap 进入时保存的 `global_cfx_intr_mask`」→ 加「与 `excp_prev_cfx_code`」。

### 2. `components/qemu/patches/target/dadao/**`

- `cpu.h`：`struct` 加 `uint64_t prev_cfx_code;`（注释 `cg5 rc1`）。
- `cpu.c`：复位初始化。
- `helper.c`：
  - trap 进入（保存现场处）：`env->cfx[ci].prev_cfx_code = env->inner_cfx_code;`（**必须在 `inner_cfx_code` 被改写之前**；注意 `ci` 是目标 cfx 的下标，保存的是**进入前**的值）；
  - `escape`（恢复运行模式处）：`env->inner_cfx_code = env->cfx[ci].prev_cfx_code & 0xff;`（位宽按 spec 的 cfx 编号范围）；
  - cg5 rc1 的读写：`helper.c` 的寄存器分发表里把 `case 1` 从 reserved 改为 `&r->prev_cfx_code`。
- **走 `make_patch qemu` 重导出补丁**（禁手改 index）；`--source-state qemu` 必须 `base+1 clean`。

### 3. 契约同步

- `.tao/contracts/contract-see.md` 若含 cg5 寄存器表 ⇒ 同步 rc1 行。
- `spec/.manifests.toml` 的 `DADAO-12` 条目 **sha256 同笔重算**（这是 `check-manifests-guard` 的硬要求）。
- 若 `contracts/` 下有机器可读的 cfx 寄存器投影 ⇒ 同步。

## 验收（逐条贴真实 rc）

1. `make check-manifests-guard` rc=0（`DADAO-12` 新 hash 与清单一致）。
2. `make check-patch-tree` 的 **qemu 段** rc=0（0 problem）；`--source-state qemu` rc=0（`base+1 clean`）；`make_patch qemu` 二次运行 **0 written**（幂等）。
3. **QEMU 行为验证**（最小、可失败）：
   - 构造场景：supv 帧内投递 tick ⇒ 该帧 `escape` 成功后 `inner_cfx_code` 回到进入前的值；
   - 反例：把 `escape` 的恢复那行临时删掉 ⇒ 必须复现 `CFXESC` ⇒ 还原 ⇒ 恢复正常。
   - 用现有 `m14-qemu-*` 探针或最小裸机探针；**不要求跑 Linux**（017 会做端到端）。
4. `check-spec-drift`、`check-spec-purity`、`check-spec-refs`、`check-spec-numbering`、`check-spec-changelog` rc=0（spec 改动不得破坏这些）。
5. `check-syscall-abi`、`check-interface` rc=0（若受影响）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **版本号不变**（用户裁定 3）：`DADAO-12` 的版本行与 `-rc` 段一字不动，只加附录条目。
3. 只动：`spec/DADAO-12`、`spec/.manifests.toml`、`components/qemu/**`（补丁经 `make_patch`）、`.tao/contracts/contract-see.md`（若需）、`docs/Process-06`（若需）、本任务书。
4. **不碰 `components/linux`**（017 在途）。
5. `cp`+md5 还原（禁 checkout/restore/stash/show）。
6. **禁并发构建与门控**（017 踩过）。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
