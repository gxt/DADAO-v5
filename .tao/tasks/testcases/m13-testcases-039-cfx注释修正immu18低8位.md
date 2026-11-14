# m13-testcases-039: 修正 `11-cfx/trap_ciii_cfx.S` 里「immu18 低 8 位携带服务号」的过时注释

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-009`（已合入：服务号定死 `rd16`）
**可并行分片**：否（单文件注释）
**预估**：0.5–1 h
**状态**：待开始

## 背景

`m13-spec-009` 已把口径定为：`immu18[17:8] == 0x3FF` 是 semihosting 的**固定标记**，`immu18[7:0]` **不携带服务号**（判定只依赖 `[17:8]`），服务号由 `rd16` 给出。

但 `tests/inst/11-cfx/trap_ciii_cfx.S` 里仍有两处**过时注释**（spec-009 的 reviewer 发现，当时因「不改 `tests/**`」的硬约束未动）：

- L23-24：「③ semihosting 服务号按规范取 rd16、编码层同时在 `immu18` 低 8 位携带（`0x3FF00 + op`），本文件令两者相同，不构造二者不一致的用例」；
- L49：「`set.zw rd16, wp0, 0x10   @@ 服务号 = SYS_CLOCK（rd16 与 immu18 低 8 位一致）`」。

## 目标（只改注释，不改指令编码/用例意图）

1. L23-24 改为：「③ semihosting 服务号取 `rd16`（`immu18[17:8] == 0x3FF` 只是标记，`immu18[7:0]` 被忽略）；本文件在 immediate 里保留 `0x10` 只为沿用既有编码字节，**不**表示「低 8 位携带服务号」」。
2. L49 注释改为：「服务号 = `SYS_CLOCK`（`rd16`；immu18 低 8 位被忽略）」。
3. 若该文件还有别处同一误解，一并改（`grep -n "低 8 位\|0x3FF00 + op"`）。

## 验收（逐条贴真实输出）

1. 该文件内 `0x3FF00 + op`、`低 8 位携带`、`与 immu18 低 8 位一致` **0 命中**。
2. **编码字节零改动**：改前/改后 `trap cfx_hmon, 0x3FF10`、`set.zw rd16, wp0, 0x10` 等指令行逐字节相同（贴 `git diff` 证明只有注释行变化，或用 `grep -v '^\s*@@'` 比对）。
3. `make check-inst-asm` **rc=0，264 id / 897 镜像不变**（注释不影响执行，但跑一次证明没碰坏）。
4. `check-tests-index`/`check-case-ledger`/`validate-vectors` 不变；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**。
3. 只改 `tests/inst/11-cfx/trap_ciii_cfx.S`（注释行）+ 本任务书；**不改**指令/期望/宏层/根清单。
4. 禁 `git checkout/restore/stash`；如需注入验证用 `cp`+md5。
5. 测试派节点（`ics170`，jobs 38）；派前 `remote.py status` 查资源；**禁边构建边测试**。

## 待裁定

（实现中写）

## 审阅记录

（待填）
