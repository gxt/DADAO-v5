# m14-linux-032: K6 shell 启动（busybox sh + semihosting 控制台 + 前台执行）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-031`、K5 收口（syscall/信号/ABI）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（用户态闭环端到端）
**状态**：待开始

## 背景

K6 首版**只做前台执行**：`busybox sh` 在 QEMU system 下启动，经 semihosting 控制台读写，能执行内建与简单 applet；**不实现作业控制**（无 TTY/job control）。

## 目标

1. **启动路径**：内核 → `/init`（busybox）→ `sh`，控制台走 semihosting（`SYS_WRITE0`/`SYS_READC` 等）。
2. **进程面**：`fork`/`execve`（外部 applet）、`wait4`、退出码；`SIGCHLD` 回收。
3. **信号面**：`SIGINT`/`SIGTERM` 等基本投递与默认动作（与 `027` 衔接）；不实现 `SIGTSTP`/作业控制。
4. **标准 IO**：`stdin`/`stdout`/`stderr` 与 semihosting 的映射；管道（`|`）与重定向（`>`/`<`）按 busybox 实现能力评估，未支持项写明。

## 验收（逐条贴真实 rc）

1. `busybox sh` 启动并输出可识别提示/命令回显。
2. `echo hello` 输出正确、退出码 0；`false` 退出码非 0。
3. 外部 applet（如 `ls`）经 `execve` 运行并返回；`wait4` 收到正确状态。
4. 信号：`kill -TERM` 投递到子进程并触发默认动作（或 busybox 处理）。
5. 不做作业控制的口径写进完成区（哪些命令不支持、原因）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：busybox 配置/补丁（若需）、`/init` 脚本、内核信号/syscall 补丁（若需，逐条披露）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

（待填）
