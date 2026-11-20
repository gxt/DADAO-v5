# m18-linux-003: K6 收口门控 `check-linux-k6`

**模块**：linux
**项目里程碑**：M18
**依赖**：`m14-linux-030`–`031`、`m18-linux-001`–`002`（全部）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（新门控 + 退役 + L2 接线）
**状态**：待开始

> **迁移说明**：本任务原为 `m14-linux-034`（M14），用户 2026-11-20 裁定 K6 移入 M18 ⇒ 改号 `m18-linux-003`，任务范围不变。

## 背景

K6（busybox 启动）是 M14 修订后的最终阶段。本任务把 K6 出口固化为 L2 门控，并沿用 `m14-linux-015`/`029` 的口径：**门控只跑代表例**，全量由回归脚本单独跑。

## 目标

1. **新增 `tools/linux/check_k6.py` + `make check-linux-k6`**：代表例 = `busybox sh` 启动 + 5 条命令 + 退出码。
2. **接线**：`Makefile`（`PHONY`、`GATE_LOCKED_TARGETS`、`_locked-check-modules`、`help`、块注释）、`docs/Process-07` 目标-层表一行（L2）。
3. **§4a 退役**：K5 及以前里「用户态应用尚未跑通 / busybox 未支持」类过时断言逐条处置（保留附理由 / 改限定语 / 删除并指向替代），门控内加机械断言（新文案在 / 旧文案不在 / 替代指向 / `Process-07 §4a` 有记录）。
4. **一键证据脚本**：构建 → 门控 → selfcheck → 注入 → 回归（K0–K5）退出码如实传播。

## 验收（逐条贴真实 rc）

1. `make check-linux-k6` rc=0，项数现场打印。
2. `--selfcheck` 每组可翻转；`--inject` ≥4 路（含至少 1 路任务书未列）均可达 FAIL，`cp`+md5 还原。
3. 不回归：`check-linux-k0`–`k5` rc=0。
4. `docs/Process-07` 与 `make help` 含新门控；`check-patch-tree` linux 段 0 problem。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：新门控脚本、`Makefile`、`docs/Process-07`、退役的旧断言（逐条披露）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

（待填）
