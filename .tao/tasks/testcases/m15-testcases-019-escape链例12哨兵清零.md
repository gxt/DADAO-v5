# m15-testcases-019: 11-cfx `escape` 链例 12 的 SRAM 哨兵显式清零

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-017`（两载体已按新 escape 语义重写）
**可并行分片**：否
**预估**：1–1.5 h
**档位**：小改
**状态**：待开始

## 背景（`m16-chipyard-005` 复核实测）

`tests/inst/11-cfx/escape_ciii_cfx.S` 的**链例 12** 用 hmon SRAM 的 `+0xC0` / `+0xC8` 两个槽当「未调用 / 到达计数」哨兵，**默认它们上电为 0**：

- **QEMU**：SRAM 上电为 0 ⇒ 用例成立；
- **chipyard**：TLRAM 上电**随机**（实测 `+0xC8` = `0xad3555700e50e7e2`）⇒ 哨兵读到随机值 ⇒ **该例在本 profile 结构性红**。

同一份副本在**显式清零两槽**后，chipyard 与 QEMU **96 B 逐字节全绿** ⇒ escape 语义本身已对齐，问题只在 SRAM 上电口径。

## 目标

1. `escape_ciii_cfx.S` 的链例 12（以及任何依赖「SRAM 上电为 0」的用例）在**执行前显式清零**所用哨兵槽（`+0xC0`/`+0xC8`）；
2. 全册扫描同类假设：`tests/inst/11-cfx/**` 里凡读未初始化 SRAM/内存槽当哨兵的地方，逐条列出并处置（清零或改用显式初值）；
3. **不改启动时序、不改 RTL**（chipyard 上电随机的口径不动）。

## 验收（逐条贴真实 rc）

1. `make check-inst-asm` **272/272** rc=0（chipyard profile 的 11-cfx 不再因上电随机而红）。
2. `escape_ciii_cfx` 单载体：QEMU 与 chipyard **字节流逐字节相同**（给出两侧长度与 md5）。
3. **可达 FAIL**：把清零那两行临时去掉 ⇒ 在 chipyard lane 必须复现红（或超时）；还原 ⇒ 绿（`cp`+md5）。
4. `check-case-ledger`（`--write` 后幂等）、`check-asm-list`、`check-tests-index`、`check-dirs`、`check-no-residue` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `tests/inst/11-cfx/**` 与本任务书；不改 `components/`、`spec/`。
3. 单文件用例 ≤127。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

（待填）
