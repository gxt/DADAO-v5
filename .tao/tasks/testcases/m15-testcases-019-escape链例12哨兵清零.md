# m15-testcases-019: 11-cfx `escape` 链例 12 的 SRAM 哨兵显式清零

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-017`（两载体已按新 escape 语义重写）
**可并行分片**：否
**预估**：1–1.5 h
**档位**：小改
**状态**：已验证

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

### 第 1 轮 engineer 自审（2026-11-19）

- **逐行审查改动**（`escape_ciii_cfx.S` §`__c12`）：+2 行注释 + `set.rd rd7, 0` + 两条 `st.o rd7, [rb20, 0xC0/0xC8]`。`rb20` 在 setup 装载后仅作 hmon 基址使用（c8/c9 只写 0xF8），到 `__c12` 未被改写 ⇒ 基址有效；`rd7` 在 case 12 执行前无活跃值（首次使用在 0x1E00 的 `ld.o`）；两槽 8 字节对齐；0xC0/0xC8 在固件固定布局（0xD8–0xFF）之外，不覆盖 cause 三槽/返回槽。
- **检查点计数不变**：清零指令不匹配链例行/`__REC` 正则；`check-tests-index` 现场 272 载体/最大 id 34 不变，`check-case-ledger` 现场身份 5670 条不变（`--write` md5 幂等）。
- **可达 FAIL 实测**：去掉两条 store ⇒ chipyard rc=**12**（无字节流）、QEMU rc=0/96 B；`cp`+md5 还原 ⇒ chipyard/QEMU 96 B、md5 相同。
- **结论**：无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| （无） | — | — | — |

### 第 1 轮 reviewer 验收（2026-11-19，独立重跑）

- **工作树自证**：`git rev-parse --show-toplevel` = `/tmp/opencode/m15-testcases-019/wt`、分支 `m15-testcases-019`、`git status --porcelain -uall` 空；`git diff master...HEAD --stat` = **2 文件**（本任务书 + `tests/inst/11-cfx/escape_ciii_cfx.S`，+24/−2）；`-- components/ spec/` 输出为空，无版本号/manifest 改动。
- **清零正确性（读源）**：`__c12` 增 `set.rd rd7, 0` + `st.o rd7, [rb20, 0xC0]` / `[rb20, 0xC8]`。`rb20` 仅在 `__TEST_BEGIN` 后第 78 行 `LOAD_ADDR rb20, HMON_BASE` 装载，全文件再无对 `rb20` 本体的写（只作基址用于 0xF8/0xC0/0xC8 三次 store）⇒ `__c12` 时有效；消费侧 0x1E00 块用 `rb21=HMON_BASE`、probe 入口用 `rb22=HMON_BASE`，三者同一基址。清零位于 `__MON_ENTER` 之前，其间 handler 只写 0xE0，不覆盖 C0/C8；`rd7` 在 case 12 前无活跃值（上次写在 case 6 落点块且已消费）；两槽 8 B 对齐。
- **布局核对**：`tests/ee-tiny/hmon_tiny.S` 固件布局 = 代码区 0x00–0xD7（实际代码 44 B，0x00–0x2B）、`0xD8 rd63 / 0xE0 / 0xE8 / 0xF0 / 0xF8` ⇒ 0xC0/0xC8 既在固定布局 0xD8–0xFF 之外、也不在实际代码之内，不覆盖 cause 三槽与返回槽。
- **重跑①**：`make check-inst-asm` → **rc=0**，日志实录 `run_asm_suite: 272/272 镜像通过（272 个 id；链例 + 故障链 632 例）` + `check-inst-asm: PASS`。
- **重跑②（证据脚本，用新 RTL 快照）**：`CHIPYARD_SIM=$PWD/.work/evidence/m15-testcases-019/sim-chipyard-prevcfx bash .work/evidence/m15-testcases-019/run.sh` → **rc=0 / `evidence: PASS`**；头部 `sim md5=9b6928e035c321835d81cef03542c6f7`（共享 `.work` 默认 sim `eb5220f9…` 为 Nov 17 旧基线，**未使用**）。S1=2/S2=1；N1–N6 全 PASS：双 lane rc=0、各 **96 B**（`wc -c` = 96/96）、md5 均 `1fb42c10c7c1bdce824fd3e8bd8a8be7`、`cmp` 逐字节相同；脚本 I 段（去掉两条清零 store）chipyard **rc=12**、QEMU rc=0/96 B，`cp`+md5 还原 `977cbb08…` 后 I7 rc=0、I8 identical；G1–G7 全 PASS（ledger md5 `9d9d8c55…` 幂等）。
- **重跑③（五门控单独直跑，真实 rc）**：`check_case_ledger.py --write`=0、`check_case_ledger.py`=0、`check_asm_list_consistency.py`=0、`check_tests_index.py`=0（现场 272 载体 / 最大 id 34 / PASS）、`check_dirs.py`=0、`check_dirs.py --residue`=0。
- **独立注入（reviewer 自做，非 engineer 自检）**：注入① 改 case12 `ld.o rd7, [rb21, 0xC0]`→`0xC4`（读未写槽，S1/S2 仍 2/1 绿）⇒ 脚本报 `[FAIL] N1`，单跑 qemu `--timeout-qemu 40` 实测 **rc=-2 / 0 B**；注入② 改 `__CHECK_RD 12, rd7, 0x8`→`0x9`（快速失败）⇒ `bash run.sh` **rc=1 / `evidence: FAIL（4 项）`**（N1/I5/I7/G2 红）。两次均 `cp`+md5 还原至 `977cbb08…`，ledger 经 `--write` 回 `9d9d8c55…`、`git status` 干净；回绿复跑 `bash run.sh` **rc=0 / `evidence: PASS`**、双 lane md5 与交付态一致。
- **注入留痕**：注入① 因链例 12 分支挂死（双 lane 超时）拖过我 30 min 时限，首条命令被 SIGTERM（exit 143）；改用注入② 取得脚本完整退出码，重试 1 次，未以重试掩盖根因。
- **全册扫描核实**：`tests/inst/11-cfx/` 平坦 5 个 `.S`；`ld.o` 计数 `cfx2rc=0 / cfx2rd=0 / fence=0 / trap=1 / escape=6`。`cfx2rc`/`cfx2rd`/`fence` 各仅 1 条 `st.o [rb20, 0xF8]`、不读 hmon SRAM；`trap` 唯一 `ld.o` 读 0xE8（本次 trap 已由固件写）；`escape` 的 0xE0/0xE8/0xF0 读均在固件/handler 写之后 ⇒ 全册只有链例 12「首读先于首写」，与完成区结论一致。
- **约束逐条**：① 独立 worktree、未改主工作树、未提交（`git log -1` 仍 `a861a322`）✓；② 只动 `tests/inst/11-cfx/**` + 本任务书，`components/`/`spec/` 零 diff ✓；③ 单文件 ≤127（本文件 12 链 + 8 故障；index 现场最大 id 34）✓；④ 还原全程 `cp`+md5，未用 checkout/restore/stash/show ✓；版本号未动 ✓；完成区 5 行、本节 ≤40 行 ✓。
- **非阻断观察（供 architect 定夺）**：链例 12 注释称「到达次数上限 2 ⇒ 第 3 次到达判红（**不挂死**）」，而注入①（cause_id 恒读 0）实测双 lane 挂死至超时（qemu `rc=-2`），该「不挂死」口径未被证实；不影响交付态与本任务验收，属既有 fail 路径的注释/行为差异，建议另立 issue。
- **判决：Accepted** —— 验收命令块在本人重跑下全部 rc=0 通过、硬约束无违反；另有 1 条非阻断观察留 architect 处置。

## 完成区

**测试结果**：`make check-inst-asm` **272/272** rc=0（链例+故障链 632 例）；证据脚本（运行期证据目录 `run.sh`）全段 rc=0；五个 L1 门控 rc=0。
**修改文件**：`tests/inst/11-cfx/escape_ciii_cfx.S`（+5 行：`__c12` 执行前清零 hmon SRAM `+0xC0`/`+0xC8`；附带同区扫描结论见「新发现」）。
**验收结果**：① QEMU 单载体 rc=0 / **96 B** / md5 `1fb42c10c7c1bdce824fd3e8bd8a8be7`。② chipyard（含 `m16-chipyard-005` prevCfx 的交付构建，sim md5 `9b6928e0…`，证据目录内留有该快照）rc=0 / **96 B** / 同一 md5，`cmp` 逐字节相同。③ 可达 FAIL：去掉两条清零 store ⇒ chipyard rc=**12**（0 B）、QEMU 仍 rc=0/96 B ⇒ `cp`+md5 还原（`977cbb08…` 复现）⇒ 双绿且字节流与交付态相同。④ `check-case-ledger --write` 幂等（tsv md5 前后同）、`check-asm-list`/`check-tests-index`/`check-dirs`/`check-no-residue` rc=0。
**新发现/坑**：① **全册扫描**（`tests/inst/11-cfx/**`）：只有本文件链例 12 读「未写过的 SRAM 槽」当哨兵；其余 hmon SRAM 读（0xE0/0xE8/0xF0）都在固件/本文件 handler 写之后，`cfx2rc`/`cfx2rd`/`fence` 不读 hmon SRAM（只写 0xF8），结果缓冲在 PT_LOAD 之外但只打印已写槽 ⇒ 无需处置。② **chipyard 判据必须用新 escape 语义的构建**：master `.work` 基线（Nov 17）在**链例 9** 就红，与本任务哨兵无关；本次用 `m16-chipyard-005` 交付构建的快照取证（clean 重建 md5 会变、行为不变，`ISS-453`）。③ **并行坑**：`m16-chipyard-005` 复核的注入/还原会替换其 worktree 里的 sim（实测 `9b6928e0`→`e7337774`（注入态→链例 9 红）→`9b6928e0`）；故证据跑用**快照**，`run.sh` 支持 `CHIPYARD_SIM` 覆盖。
**遗留问题**：`m16-chipyard-005` 合入并重建共享 `.work/source/chipyard` 后，reviewer 可用默认 sim 路径复跑本证据脚本（默认路径 = 共享 `.work`，当前仍是旧构建，直跑会在链例 9 红，属既有 RTL 差异、非本任务引入）。
