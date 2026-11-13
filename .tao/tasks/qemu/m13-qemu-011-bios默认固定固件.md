# m13-qemu-011: `-bios` 收紧为固定固件（删除 legacy trampoline 窗口）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m12-chipyard-019`（五类同步异常已进 hmon，已完成）；与 `m13-testcases-034` **同批合入**
**可并行分片**：否（组件单写者）
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 选 ①「绑 `m12-chipyard-019` 收紧」：019 已完成，迁 44 例 oracle 并删 legacy 窗口。

## 目标

`-bios` 路径**只接受 64 KiB 固定固件**，与 `bootrom-image` 走同一固定固件（`Machine-v5 §6`）；**删除 ≤4096 B 的 raw trampoline 窗口**及其「显式写不可达 hmon 向量」兼容逻辑。

## 范围

- `hw/dadao/dadao-machine.c`（及必要 helper）：删 legacy 分支；`-bios` 接受 64 KiB 固件或**具名报错**；不保留中间尺寸放行。
- 关闭「`-bios` + 短 trampoline ⇒ 机器 fault」这条 `tests/inst` Tiny 依赖的旁路。
- 不改 `spec/`、不改 `contracts/`（§6 原文即目标口径）。

## 验收

1. `-bios` 传 64 KiB 固定固件 ⇒ 正常启动；传 ≤4096 B / 中间尺寸 ⇒ **非零退出 + 具名错误**（两条反例各一）。
2. `check-inst` Tiny 子集在**与 `m13-testcases-034` 同批**下 rc=0；单独本任务时期望红集 == 034 待迁移清单（写出现场清单）。
3. 补丁导出 `make_patch.py qemu`、`check_patch_tree` qemu 段 0 问题；安装根 == 构建树 md5。
4. ≥1 路注入可达 FAIL + `cp`+md5 还原。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree（分支 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；组件补丁走 `make_patch.py`。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需用户语义裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash` 还原注入；用 `cp`+md5。

## 待裁定

（实现中写。）

## 审阅记录

（待填）
