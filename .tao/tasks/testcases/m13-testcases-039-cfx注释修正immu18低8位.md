# m13-testcases-039: 修正 `11-cfx/trap_ciii_cfx.S` 里「immu18 低 8 位携带服务号」的过时注释

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-009`（已合入：服务号定死 `rd16`）
**可并行分片**：否（单文件注释）
**预估**：0.5–1 h
**状态**：已验证

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

无。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

审查范围：`tests/inst/11-cfx/trap_ciii_cfx.S` 两处注释改动 + 一键证据脚本（逐行核断言与还原逻辑）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务原文的新注释含子串「低 8 位携带」，与验收①「`低 8 位携带` 0 命中」自相矛盾 | ✅已修 | 改写为「**不**表示低 8 位承载服务号」（保义避串） | C1 命中 0；I2 注入旧串后命中 1（判据可红） |
| F2 初版把 L23-24 拆成 3 行注释 ⇒ `grep -v '^\s*@@'` 过滤后多一空行、diff 不空 | ✅已修 | 压回 2 行（行数不变） | C2 rc=0（注释剥离后逐字节相同） |
| F3 证据脚本 C2 比较 `git diff` 行时未剥 `+`/`-` 前缀 ⇒ 恒假红 | ✅已修 | 两侧 `sed -e 's/^[-+]//'` 后再 md5 比对 | 脚本 rc=0；I1 注入仍红（可达 FAIL） |
| F4 本任务 worktree 基线落后 master 两提交（任务书文件不在树内） | ✅已修 | `git merge --ff-only master` 补齐（未改主工作树） | 任务书已在本树；`git status` 仅 `.S` |

**判决**：finding 全部已修，无未修项 → 可交付 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**重跑记录（本人执行，输出/退出码如下）**
1. **编码零改动**：`diff <(git show b79e816e^:tests/inst/11-cfx/trap_ciii_cfx.S | sed 's/@@.*$//') <(sed 's/@@.*$//' tests/inst/11-cfx/trap_ciii_cfx.S)` ⇒ **rc=0**，两侧 md5 同为 `fb3a9fdb949383103e500fa5e56c6647`；`git diff --stat b79e816e^ b79e816e` = 3+/3−（仅 `@@` 注释行）；`trap cfx_hmon, 0x3FF10`、`set.zw rd16, wp0, 0x10` 原样未动。
2. **过时串**：`grep -c '0x3FF00 + op\|低 8 位携带\|与 immu18 低 8 位一致'` ⇒ **0**（逐项各 0，grep rc=1）；全文件 `低 8 位` 仅 L24/L49 两处，均为否定式（不承载 / 被忽略）。
3. **门控**：`make check-tests-index` rc=0（**486 条**）；`make check-case-ledger` rc=0（**2033** = vector 1510 + lit 523）；`make validate-vectors` rc=0（**156/156、264 `.S` 载体、gaps 0**）；`inst_sweep emit` covered=**273**、`sweep_expect.bin` md5 **`2d4d94651346ef673c5a855e024c1489`**。
4. **证据脚本**：`bash .work/evidence/<任务ID>/run.sh` ⇒ **rc=0**，C1–C6 + I1/I1′/I2/I2′ 全 PASS，两次 `cp` 还原 md5 `7b7db92a…` 与基线一致。
5. **节点 `ics170` 复跑**：派前 `remote.py status` rc=0（40 核、loadavg 20.0、disk 26%、他任务 21 路 verilator 在跑）；在由 `b79e816e` 建的临时 worktree 跑 `make check-inst-asm TEST_JOBS=18` ⇒ **rc=0**、`264 个 id / 897 个镜像`、`897/897 镜像通过`、`check-inst-asm: PASS`（16.2 s）；本文件 **1 链例（检查点 9）+ 6 故障例全 PASS**。
6. **独立注入（自设计）**：`trap cfx_hmon, 0x3FF10 → 0x3FE10`（`cp` 备份 md5 `7b7db92a…`）⇒ 重跑 **`check-inst-asm: FAIL (rc=1)`、make rc=2、896/897**；`cp` 还原 md5 一致 ⇒ 回绿 `897/897`、rc=0。
7. **节点还原对账**：`git worktree list` 仅主树、临时分支/bundle 已删、主树 HEAD `8a4098ce` 与 4 项他任务脏项原样、该 `.S` md5 复原 `4773420012afec055687d8e963cd8e06`。

**约束核验**
- 只改该 `.S`（注释）+ 任务书：`git diff --stat master...HEAD` 仅 2 文件（`.S` 3+/3−、任务书 32+/6−）；`tests/inst.yaml`、宏层、根清单未动 ✓
- 未跑 `install-host`/`check-modules`/`build-*`；未提交 git；未动主工作树（主树固定 `master` 且 `git status` 干净；其 HEAD 由主会话另行推进，与本任务无关）✓
- 完成区 14 行 ≤30、无运行期路径；任务书 `**状态**：待验收`；`discussing.md`/台账未改 ✓
- 快照对账：验收前 `git status -uall` 空 = 验收后空；该 `.S` md5 `7b7db92a…` 前后一致 ✓

**发现（不阻断）**
- F1 证据脚本 C2 在提交后退化为同源自比：实测 `old_code_md5=d41d8cd9 new_code_md5=d41d8cd9`（两侧皆空 md5），对「提交本身是否改了编码」不敏感；验收②已由我用 `b79e816e^` 独立复核 rc=0。建议把 C2 基准改为 `HEAD^`（architect 收尾时处理）。
- F2 「低 8 位**承载**」避串可接受：同句已写明 `immu18[7:0]` 被忽略、且整句为否定式（「**不**表示…」），不会被读成旧口径；任务目标 1 原句含「低 8 位携带」、与验收①字面串自相矛盾，engineer 取舍合理。
- F3 任务书写 jobs 38、实跑 18（节点被他任务占约 20 并行，按「总并行 ≤ 核数−2」下调）；计数判据与 jobs 无关。
- F4 engineer 的 delta bundle 落在任务临时目录（节点交互中转件按规则应放 `.work/`），且未见被实际使用；过程小节。

**判决：Accepted** —— 验收命令在我自己的重跑下全部通过、约束无违反；F1–F4 仅记录，不需返工。

## 完成区

**测试结果**：通过（一键证据脚本 rc=0，C1–C6 + I1/I1′/I2/I2′ 全 PASS）；节点 `make check-inst-asm TEST_JOBS=38` **rc=0**（14.7 s，现场统计 **264 id / 897 镜像** = 链例 264 + 故障例 633；本文件 9 个链例检查点 + 6 个故障例全 PASS）。长日志留运行期日志目录。
**修改文件**：`tests/inst/11-cfx/trap_ciii_cfx.S`（仅注释）、本任务书（`git status -uall` 仅 `M` 该 `.S`）。
**验收结果**：
① 改前 L23-24：「③ semihosting 服务号按规范取 rd16、编码层同时在 `immu18` 低 8 位携带（`0x3FF00 + op`），本文件令两者相同，不构造二者不一致的用例」⇒ 改后：「③ semihosting 服务号取 `rd16`（`immu18[17:8] == 0x3FF` 只是标记、`immu18[7:0]` 被忽略）；本文件在 immediate 里保留 `0x10` 只为沿用既有编码字节，**不**表示低 8 位承载服务号」。
② 改前 L49：「`set.zw rd16, wp0, 0x10   @@ 服务号 = SYS_CLOCK（rd16 与 immu18 低 8 位一致）`」⇒ 改后：「… @@ 服务号 = SYS_CLOCK（`rd16`；immu18 低 8 位被忽略）」。
③ 过时串 0 命中：`grep -c '0x3FF00 + op\|低 8 位携带\|与 immu18 低 8 位一致'` = **0**（改前该文件 2 处）。
④ 编码零改动：`diff <(git show HEAD:<file> | sed 's/@@.*$//') <(sed 's/@@.*$//' <file>)` **rc=0**（剥掉 `@@` 注释后逐字节相同）；`git diff -U0` 的 3 `-`/3 `+` 行剥注释后 md5 相同；`git diff --stat` = 3+/3−；指令行 `trap cfx_hmon, 0x3FF10`、`set.zw rd16, wp0, 0x10` 原样未动。
⑤ 门控：`check-tests-index` rc=0（**486 条**）、`check-case-ledger` rc=0（**2033** = vector 1510 + lit 523）、`validate-vectors` rc=0（156/156、264 `.S` 载体、gaps 0）；`inst_sweep emit` rc=0 `covered=273`、`sweep_expect.bin` md5 **`2d4d94651346ef673c5a855e024c1489`** 不变。
⑥ 节点 `ics170`：派前 `remote.py status` rc=0（loadavg 0.00 / disk 26% / running=none）+ `sync_node_artifacts.sh ics170` rc=0（三件 same、工具链 synced、verify OK）；跑后节点仓该文件 md5 复原为原值、`git diff` 空、`git worktree list` 仅主树、临时 worktree/bundle 已删、原有 4 个他任务脏项未被触碰。
⑦ 反例可达 FAIL（`cp`+md5 还原）：I1 注入 `0x3FF10→0x3FF11` ⇒ C2 **rc=1**；I2 注入旧口径注释 ⇒ C1 **命中=1**；两次还原后 md5 `7b7d…` 与备份一致、C1/C2 回绿。
**新发现/坑**：① 任务原文新注释含「低 8 位携带」子串，与验收①0 命中冲突 ⇒ 改写为「低 8 位承载」保义避串（见自审 F1）。② 注释块行数须保持不变，否则「过滤 `^\s*@@` 行后 diff 为空」不成立（多一空行，见 F2）。③ 「编码零改动」的判据应剥 `@@` 起至行尾（含行尾注释），仅过滤整行注释不够——`set.zw` 行是行尾注释改动。
**遗留问题**：无。
