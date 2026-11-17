# m14-linux-030: K6 busybox 构建接入（静态 musl + 最小 applet 集）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`（K1 启动）/`m14-infra-001`（工具链缺口矩阵）；**运行验收依赖 K5 收口**（syscall 闭环）
**可并行分片**：否（busybox 组件单写者）
**预估**：3–4 h
**档位**：中改（组件接入 + 最小 config；复核 ≥2 路注入）
**状态**：待开始

## 背景（用户 2026-11-17）

`ADR-0052` 已就地修订：M14 出口扩到 **K6（busybox 启动）**。K6 采用**静态 busybox**（不依赖 ldso），最小 applet 集 = `sh` + `ls/cat/echo/mkdir/rm/cp/mv/grep/ps`（`ps` 在无 `/proc` 时退化为打印自身/空表）。首版**不做 `/proc`、不做作业控制**。

## 目标

1. **busybox 源与版本锁定**：按 `docs/Process-01` 以受补丁组件接入（源树 + 补丁集 + `manifests/` 锁 commit），版本号/commit 只认锁文件。
2. **最小 config**：只启用 `sh` 与上述 applet；关闭 `/proc`、作业控制、NFS、PAM 等无关项；输出 `.config` 与 applet 链接表。
3. **静态 musl 构建**：`-static`、无 `PT_INTERP`；工具链缺口（musl 缺函数/syscall 桩）逐条登记到完成区（区分 blocker / 可绕过）。
4. **构建可复现**：一条 `make` 目标（或脚本）产出 `busybox` ELF；build id/哈希记录。

## 验收（逐条贴真实 rc）

1. `busybox` 产出存在、`file`/`readelf` 显示静态（无 `PT_INTERP`、无 `PT_DYNAMIC`）。
2. applet 清单 = 约定集合（逐项 `readelf`/`busybox --list` 核对）。
3. 工具链缺口逐条登记（blocker 0 才可继续；有 blocker 则写明解锁条件并 BLOCKED）。
4. 构建幂等：二次构建产物哈希一致（或给出非确定性归因）。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：busybox 组件目录/补丁集、`manifests/` 锁条目、构建脚本、本任务书。**不动** `spec/`、`.tao/contracts/`、内核补丁。
3. **不改版本号**（用户规则）。
4. 不提交 git；注入还原 `cp`+md5。

## 待裁定

（无）

## 审阅记录

（待填）
