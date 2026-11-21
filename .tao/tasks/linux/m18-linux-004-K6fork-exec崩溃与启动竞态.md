# m18-linux-004: K6 fork+exec 确定性崩溃与启动竞态修复（ISS-497 / ISS-498）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-001`、`m18-linux-002`
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（用户态进程/异常路径）
**状态**：待开始

## 背景（`m18-linux-002` 实测）

1. **`ISS-497`【P1】**：单次启动跑约 17 条命令后，ash 在 `fork+exec` 处读 NULL ⇒ `die-no-vma`（`va=0x0`），shell 被杀；**5/5 复现**，且 `m18-linux-001` 已合入产物同样复现。`002` 只能拆 3 段短启动。
2. **`ISS-498`【P2】**：间歇启动未进用户态（`Run /init` 后无输出、QEMU rc=124/1），脚本靠 1 次重试。

这两个缺陷不修，`m18-linux-003 check-linux-k6` 只能把它当已知红，收口无意义。

## 目标

1. **定位并修复** `ISS-497`：从 `repro-die-no-vma.txt`（`m18-linux-002` 运行期证据）复现，查 fork/exec 路径（重点：exec 成功后 `current->mm`/用户栈/`task_pt_regs` 交接；fork 预复制与用户缺页在静态 supv 帧上的重入；`+4` 判据只应在 exec 成功时生效）。
2. **定位并修复** `ISS-498`：启动竞态（入口帧/栈顶/调度），修后去掉重试。
3. 不改变既有 K6 口径（无作业控制），不新增 retry/超时来掩盖。

## 验收（真实 rc）

1. **单次启动长脚本**：`repro-die-no-vma.txt`（≥17 条命令，含 `echo/ls/cat/mkdir/rm` 重复多轮）一次跑完，`K6-REGRESSION-DONE` 出现、无 `die-no-vma`、无 panic、退出码符合脚本；
2. **启动稳定性**：同一镜像连续 10 次启动全部进入用户态（无 rc=124/1），脚本里**无重试**；
3. **`m18-linux-002` 回归**：其 `run.sh` 50/50 仍绿；`m18-linux-001` 证据 28/28 仍绿；
4. **不回归**：`check-linux-k5` 280/280、`check-linux-k0` 146/146、`check-config-pins`、`check-patch-tree` linux 段 0 问题；
5. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退你修的关键判据 ⇒ 长脚本再红；② 去掉启动修复 ⇒ 10 次启动出现未进用户态（或按你的判据红）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 约束

独立 worktree；不提交 git；只动 `components/linux/**`、必要证据脚本与任务书；组件补丁经 `make_patch.py` 重导；不改版本号；术语「寄存器组」；`ISS-497/498` 修好后填 `resolved_by`（`closed_in: M18`）。
