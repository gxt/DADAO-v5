# m18-gem5-003: `check_tiny_hmon` 的 `CFXESC` oracle 从「旧 monitor 路由」改为「当前 cfx」

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-gem5-002`（CFXESC 投当前 cfx）已合入 `bb937707`；`m18-spec-005`（R2 规格）已验证
**可并行分片**：否（单文件 oracle + 共享签名数据）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（`m18-gem5-002` reviewer 实测，2026-11-25）

`tests/unit/gem5/check_tiny_hmon.py` 当前 **rc=1 / 29 FAIL**，属**基线即红**：该例的 `CFXESC` 记录按**旧 monitor 路由**写 oracle（期望进当前运行模式 monitor），而按 `spec/DADAO-12 §5.1/§5.3` 与 `m18-gem5-002` 的实现，`CFXESC` 应投**当前 cfx**（该例实际以 cfx63 运行：`imms18=1` 走 `tinyEscape`，不经 `inst.cc` fallback）。

已证：`git archive HEAD` 基线树与修复后树的 29 条 FAIL **逐行相同**（md5 同 `bfcd47e6…`）⇒ 与 `m18-gem5-002` 无关，是 oracle 自身陈旧。

## 目标

1. **按 spec 重写 oracle**：`CFXESC`（escape 帧/目标错误）期望改为「投递到**当前 cfx**（本例 cfx63），monitor 不被写」；期望值必须从 `spec/DADAO-12 §5.1/§5.3`（及 `Kaiwu §7.1` 的停机码段规则）**独立派生**，不得从 gem5 实测反推。
2. 若该例还断言了 monitor 侧的记录（cause_ip/cause_info/段），一并改为「monitor 无写入」的**反向断言**。
3. 不得为过门控而放宽其它断言；修改后逐条给证据。

## 验收（逐条贴真实 rc）

1. `python3 tests/unit/gem5/check_tiny_hmon.py` **rc=0**（0 FAIL）；改动前后 FAIL 集对比表（29 → 0）并说明每条的归因。
2. **可达 FAIL ≥2 路**：① 把期望改回「进 monitor」⇒ 红；② 把「monitor 无写入」反向断言删掉 ⇒ 红（或注入一次 monitor 写）；均 `cp`+md5 还原。
3. 期望的 spec 派生链写进任务书（引原文位置），reviewer 可独立复算。
4. 相关门控：`check-gem5-decode`、`check-patch-tree`（gem5 段）、`check-tests-index`、`check-knowledge-refs` 真 rc；若 `check-patch-tree` 总 rc 受他人 linux/musl 基线影响，按「gem5 段 0 problem」口径并披露。
5. 若同步了 `tests/data/inst-signature/**` 或 `case-ledger.tsv`，须由生成器产出（`inst-signature-data` / 对应生成器），禁手改。

## 约束

独立 `git worktree`（分支 = `m18-gem5-003`）；不提交 git；只改 `tests/unit/gem5/**`（及必要生成物）与本任务书；**不改 `components/**`、`spec/`、契约、`Makefile`**；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
