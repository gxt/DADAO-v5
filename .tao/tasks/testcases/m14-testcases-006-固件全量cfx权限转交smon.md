# m14-testcases-006: 固件把全部 cfx 的 supv 权限转交 smon（除 hmon 自身）

**模块**：testcases
**项目里程碑**：M14
**依赖**：无（`tests/shared/bootrom/k0/hmon.S` 现状）
**可并行分片**：否（单一 bootrom 镜像）
**预估**：1–1.5 h
**档位**：小改（固件宏 + 负例 + 门控重跑）
**状态**：待开始

## 背景（用户 2026-11-17 裁定）

> 用户：「hmon 应该把所有 cfx 权限转交给 smon，除了 hmon 自己。」

起因：`m14-linux-016` 的 F5（U-mode 帧往返）卡在测试固件权限——启动 SEE 只给源 cfx 2（smon）放行 `cfx_pmem/ptw/smon/hart/time` 的 `cfxreg` 轴，内核首次 `cfx2rd cfx_umon` 即 `CFXPERM(0x80) info=0x7a000208`。

现状（`tests/shared/bootrom/k0/hmon.S` 的 `OPEN_SUPV_REGS`）：

- 只清目标 cfx 的 `cg2 rc2`（supv `cfxreg` mask）的源位 bit2（smon）与 bit15（hart 约定），并设 `cg3 rc12`（`cg_reg_deleg`）= `0x8`（打开除 cg3 外所有 cg）。
- **没有清** `cg2 rc0`（`cfxtrap`）、`rc1`（`cfxmem`）、`rc3`（`cfxexe`）的 smon 位 ⇒ smon 只能通过 `cfx2rd/cfx2rc` 访问，不能 `trap`/`escape`/`ld/st`/直接跳转进入其它 cfx。

## 目标

1. **新增/改造宏**：对**除 hmon (`cfx3`) 外的全部已定义 cfx**，把 supv 行的四类同步 mask（`cg2 rc0–rc3`）中的**源 smon 位（bit2）清 0**：
   - `cfx_umon(0)`、`cfx_jmon(1)`、`cfx_smon(2)`、`cfx_ptw(4)`、`cfx_cache(5)`、`cfx_hart(15)`、`cfx_pmem(32)`、`cfx_llc(33)`、`cfx_time(34)`、`cfx_uart(62)`、`cfx_power(63)`；
   - **排除 `cfx_hmon(3)`**（hmon 自身不向 smon 开放）；
   - 每个目标 cfx 同时保持现有 `cg3 rc12 = 0x8`（打开除 cg3 外的 cg 访问）。
2. **保留现有特例**：`cfx_pmem` 的 supv `cfxmem` 需要 smon 访问（页表暂存区）——由「rc1 清 bit2」覆盖，无需额外宏；如与既有 `OPEN_SUPV_REGS cfx_pmem` 重复，合并为一条。
3. **负例机制**：沿用现有 `K2_TIME_PERM=0` 的做法，新增一个可汇编的负例开关（例如 `OPEN_SUPV_ALL=0`），使固件**不放行**这些位；用它证明「权限来自固件而不是硬件默认」：不放行时内核首次 `cfx2rd cfx_umon` 必须 `CFXPERM`，放行后成功。
4. **K0 固件镜像变化**：bootrom 镜像会变 ⇒ 记录新 md5；所有依赖 bootrom 的探针/门控（`check-linux-k0/-k1/-k2/-k3`、`check-arch` 中的 bootrom magic/镜像断言）必须重跑并回绿。

## 验收（逐条贴真实 rc）

1. **正向**：内核/探针在 supv 下对 `cfx_umon` 的 `cfx2rd`（cg0/cg5 等）成功；对 `cfx_umon` 的 `trap`/`escape`/`ld/st` 按 `OPEN_SUPV_ALL` 放行后不再 `CFXPERM`（按任务书构造的最小探针，内核侧或固件侧均可）。
2. **负例**：`OPEN_SUPV_ALL=0` 时同一访问 ⇒ `CFXPERM`，且 `cause_info` 为目标地址/指令地址（按 `contract-see §6.1`）；证明权限来自固件。
3. **不开放 hmon**：对 `cfx_hmon` 的 supv 访问仍 `CFXPERM`（至少一条断言）。
4. **镜像与门控**：bootrom 新 md5 记录；`check-linux-k0/-k1/-k2/-k3` 全 rc=0；`check-arch` 中 bootrom 相关断言回绿（若断言写死旧 md5，按 `Process-07 §4a` 改现场派生并说明）。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 只动：`tests/shared/bootrom/k0/hmon.S`（+ 若 bootrom 镜像断言在 `tools/`/`tests/` 需同步则一并，逐条披露）、本任务书。**不动** `spec/`、`contracts/`、`components/`、根 `Makefile`。
3. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md`）。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。
5. 固件是只读基线的一部分：改后必须重建并记录新镜像 md5，门控不得写死旧值。

## 待裁定

（无；用户 2026-11-17 已明确「全部 cfx 转交 smon，除 hmon 自身」）

## 审阅记录

（待填）
