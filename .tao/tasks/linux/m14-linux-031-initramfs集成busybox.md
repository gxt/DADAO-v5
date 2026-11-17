# m14-linux-031: K6 initramfs 集成（busybox + applet 链接 + /init 切换）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-030`（busybox 构建）、`m14-infra-002`（initramfs）、**K5 收口**
**可并行分片**：否（initramfs 单写者）
**预估**：2–3 h
**档位**：中改（镜像内容 + 确定性；复核 ≥2 路注入）
**状态**：待开始

## 背景

K6 出口：QEMU system 下的 initramfs 内含 `/bin/busybox` 与 applet 链接，`/init` 切到 busybox `sh`（或由 busybox 提供 `/init`）。

## 目标

1. **initramfs 内容**：`/bin/busybox` + applet 符号链接（`/bin/sh`、`/bin/ls` 等）；`/init` 指到 busybox（链接或脚本）。
2. **确定性**：沿用 `m14-infra-002` 的确定性 newc（时间戳/uid/gid/顺序固定），新增条目后仍可复现（同输入同哈希）。
3. **大小上限**：按 `contract-linux-boot §2` 的 initramfs 上限检查。
4. **内核装载路径**：确认内核从 initramfs 读 `/init` 并 `execve` 到 busybox（与 `017` 的 init 真跑衔接）。

## 验收（逐条贴真实 rc）

1. initramfs 清单含 `/bin/busybox`、`/init`、约定 applet；逐项存在性断言。
2. newc 两次生成哈希一致；大小 ≤ 契约上限。
3. `/init` 解析到 busybox（`readlink`/内容断言）。
4. QEMU system 启动：日志显示 `/init` 被 execve 且 busybox 开始执行（shell 提示或首条命令输出）。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：initramfs 生成脚本/清单、内核 initramfs 相关补丁（若需）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

（待填）
