# m12-chipyard-028: 用新 builder 重生成 chipyard `bootrom.tiny.hex`

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-integ-007`（新 hmon 算法已合入）
**可并行分片**：否
**状态**：待开始

## 背景（`ISS-410`，P1）

chipyard 签入的 BootROM hex 仍是**旧 hmon**（`escape +4`、120 B），而 QEMU/gem5 用的共享镜像已是新算法（槽 `0xF8`、48 B）。`m13-testcases-012/013` 只能靠「测试运行期自装 hmon handler」绕过，三方固件行为实际不一致。

## 目标

1. 用 `tools/testcases/arch/build_tiny_bootrom.py` 重生成 `bootrom.tiny.hex`（目标解码镜像 md5 `514300876ea66ec108396334f3ef2b0f`）
2. 改源树 hex → `tools/infra/make_patch.py chipyard` 重导出 → `check-patch-tree` rc=0
3. 回归：`make build-bootrom`、chipyard 构建/Verilator、TestDriver

## 验收

1. 签入 hex 与共享镜像一致（解码后 md5 相同；**hex 文本 md5 另行记录**，两者不是一回事）
2. `check-patch-tree` chipyard 0 问题；`check-source-state` rc=0
3. `m13-testcases-012/013` 撤掉自装 handler 的 workaround 后**仍三方一致**
4. 完成区 ≤30 行；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

（待填）
