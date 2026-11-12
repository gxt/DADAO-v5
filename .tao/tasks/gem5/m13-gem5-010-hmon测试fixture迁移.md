# m13-gem5-010: gem5 的 hmon 测试 fixture 迁到最小 handler

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-integ-007`（新 hmon 已合入，共享镜像 md5 `514300876…`）
**可并行分片**：否
**状态**：待开始

## 背景

`m13-integ-007` 把 hmon 改成「最小保存-跳转」（11 条 / 44 B，代码 `0x00`、数据 `0xD8–0xFF`），共享镜像已更新，QEMU 在用。

但 **gem5 的测试分派 fixture 仍是旧版**：

- `tests/arch/hmon/tiny_hmon_handler.S` / `.lds`：**旧 18 条 / 248 B**，仍记录 frame、重写 IALIGN/+4
- 因此 `tests/arch/hmon/expected.yaml` 的 records 0 / 17–31 仍按旧 fixture 推导
- `expected.yaml` 的 `pending_followups` 已列此条，但一直没派单

## 目标

1. 把 `tests/arch/hmon/{tiny_hmon.S,tiny_hmon_handler.S,tiny_hmon_min.S}` 统一到**最小 handler**（与 `tests/shared/bootrom/tiny/hmon.S` 同一算法）
2. `expected.yaml` 的 cause 记录改为读 hmon SRAM `0xE0/0xE8/0xF0/0xF8`（code@0x00、data@0xD8），**重派生** records 0/17–31
3. 删除 `require_layout=False` 之类的旧布局 opt-out
4. 更新 `tests/arch/hmon/README.md` 说明

## 验收

1. `check_tiny_hmon` 全绿，且 **不再有 `[PENDING]` 行**
2. hmon 段长度 44 B（表项对齐 48 B）、数据区不在镜像段内
3. 五类异常（CFXMEM/ILLI/UNDI/MALIGN/IALIGN）的 cause_id/ip/info 与 QEMU 探针逐值一致
4. `expected.yaml` 的 `pending_followups` 清空或只剩 chipyard 那条
5. 完成区 ≤30 行；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），动手前 `git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

（待填）
