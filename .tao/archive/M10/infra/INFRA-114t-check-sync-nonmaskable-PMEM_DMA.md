# INFRA-114t: check-sync-nonmaskable 白名单补 PMEM_DMA（M10 收尾门控）

**模块**：infra
**项目里程碑**：M10
**依赖**：`INTEG-042t`（`spec/DADAO-12` 异常原因表引入 `PMEM_DMA` 行）、`INTEG-047t`（`cfx_pmem` DMA 的 SBI 契约）——均为已 `已验证`，仅作溯源，非阻塞
**状态**：已验证

## 执行环境

**执行环境**：本地

## 背景（现场事实）

- `make check-milestone` 现 **rc=2**：`check-spec-archive` / `check-spec-archive-verify` 通过后停在
  `check-sync-nonmaskable`，报
  `DADAO-12-SEE-主管系统运行环境.md:662: 同步异常原因 PMEM_DMA 被标为可屏蔽（仅异步源可屏蔽）`。
- 事实两面：`spec/DADAO-12` 的 `PMEM_DMA`（`1 << 8`）**确实是异步源**（`dma_ctrl.IRQ_EN=1` 时 DONE/ERROR 置位；
  被掩码时置 `cfx_pmem_excp_pending`），标「可」**语义正确**；而 `tools/spec/check_sync_nonmaskable.py`
  的异步白名单 `ASYNC_NAME_RE = ^(?:IPI|TIMER|UART\d*|\.\.\.)$` **漏了 `PMEM_DMA`**。
- 该缺口自 `INTEG-042t` 引入（`git log -S` 命中 `145b07c3`），此前门控无此 cause 故未暴露。
- 连带：`--self-test` 的第 1 步「基线副本必须 PASS」现在也**必然 FAIL**（基线含 `PMEM_DMA`），
  即 self-test 目前整体非零 —— 修白名单后两者同时回绿。
- 已登记于 `INTEG-052m`（M10 核验册）「遗留」与「核验」两节。

## 接口规范

- 输入：`spec/DADAO-12-SEE-主管系统运行环境.md` / `DADAO-22` / `DADAO-23` 的「异常原因表」（列 `是否可屏蔽`）。
- 输出：`check_sync_nonmaskable.py` 的退出码（0 = PASS / 1 = 有同步 cause 被标可屏蔽 / 2 = 源缺失或空跑）。
- 约束：
  - **只放宽已知异步源**：白名单加入 `PMEM_DMA`（与 `IPI`/`TIMER`/`UART<n>` 同类），
    **不得**退化为「任意 cause 均放行」（如删掉 `ASYNC_NAME_RE` 判定、改成 `.*`、加 `\S+` 之类通配）；
  - **不改** `spec/DADAO-12`（`PMEM_DMA` 仍「可」）、不改 `TARGETS`、不改其它门控脚本；
  - 改后同步 **docstring 规则描述**（现文「`IPI`、`TIMER`、`UART<n>` 或占位行 `...`」）与
    **成功文案**（现 `check-sync-nonmaskable: PASS（仅异步源（IPI/TIMER/UART*/…）可屏蔽）`），三处口径一致。

## 验收标准

1. `python3 tools/spec/check_sync_nonmaskable.py` **rc=0**，且 stdout 含现场计数
   （`files=3 tables=… rows=… maskable_rows=…`）与 PASS 文案，PASS 文案列出 `PMEM_DMA`；
2. `python3 tools/spec/check_sync_nonmaskable.py --self-test` **rc=0**（基线 PASS / 注入同步 cause=可 → FAIL /
   还原 PASS / 异步源 PASS / 最终 PASS 全成立）；
3. **self-test 新增可达断言**：`PMEM_DMA=可` 明确验为「白名单命中 ⇒ 不报错」——不得**只**改正则而不加断言
   （现行第 1 步「基线副本必须 PASS」已隐式覆盖，须额外给出**显式**断言或独立注入步，
   且证明该断言**能失败**：把 `PMEM_DMA` 从白名单临时移除 ⇒ 该步必须 RED，`cp` 还原 + md5 对账后回绿）；
4. `make check-milestone` **rc=0**；若仍有其它门控红，**分开报告**（逐项 rc / 首行错误），不合并成一条；
5. L1 `make check` **rc=0**；
6. 无残留：`git status --untracked-files=all` 干净（自检临时树落 `/tmp/opencode/INFRA-114t/`，用完即清）；
7. 完成区贴真实命令输出与退出码（禁转述），并逐条对齐本清单。

## 完成区

**测试结果**：一键证据 `.work/evidence/INFRA-114t/run.sh` **9/9 全绿（SCRIPT_RC=0）**：gate rc=0（`files=3 tables=9 rows=70 maskable_rows=8`）；`--self-test` rc=0（`[OK]=7 / [BAD]=0`）；白名单静态锚点 rc=0（`mismatch=[]`）；注入 RED（rc=1 + `[BAD] PMEM_DMA=可 必须白名单命中且不报错`）；`cp` 还原 md5 相等（`50af8c1e972db8d09c2e2db2f212d27f`）后自检 rc=0；`make check` rc=0；`check-milestone` 分项 sub_rc=0 + m册_rc=0；`check_tasks --strict` rc=1 但漏收尾唯一项为本任务；翻转临时树（状态→已验证）后该严格检查 rc=0。
**修改文件**：
- `tools/spec/check_sync_nonmaskable.py`：`ASYNC_NAME_RE` 白名单加 `PMEM_DMA`（锚定枚举，非通配）；docstring 规则/自检描述与 PASS 文案三处同步；`--self-test` 新增步 5（独立小表 `PMEM_DMA=可` 走真实 `run()`，断言 `rc=0`、`errors=∅`、`maskable_rows==1`，并现场统计基线 PMEM_DMA 行数 ≥1）+ 步 5b（`CFXMEM=可` 必须仍 FAIL，防退化通配）。
- `.work/evidence/INFRA-114t/run.sh`（新增证据脚本）+ `.work/evidence/INFRA-114t/logs/`（真实日志）。
- 本任务书（完成区/状态/审阅记录）、`.tao/knowledge/milestones.md`（流水行）。
**验收结果**（逐条对任务书）：
1. gate **rc=0**，stdout 含 `files=3 tables=9 rows=70 maskable_rows=8` 与 `PASS（仅异步源（IPI/TIMER/UART*/PMEM_DMA/…）可屏蔽）` ✅
2. `--self-test` **rc=0**（基线 PASS / 注入 SOFT_RESET=可 → FAIL / 还原 PASS / TIMER=可 PASS / 最终 PASS 全成立）✅
3. 显式断言**可达 FAIL**：临时移除白名单 `PMEM_DMA` ⇒ 步 5 `[BAD]`、self-test rc=1、`git diff --name-only` 非空（防空注入）；`cp` 还原 + md5 对账（相等）后 rc=0 ✅
4. `make check-milestone`：**状态翻转前**（任务书仍 `待开始`）实跑 **rc=0**（`check-milestone: PASS (…)`）；改为 `待验收` 后**整目标 rc=2，唯一失败源 = `check_tasks --strict` 的 ① 漏收尾=1（即本任务自身，`/complete` 翻 `已验证` 即转绿）**。分项实跑：`make check-spec-archive check-spec-archive-verify check-sync-nonmaskable check-night-report check-l3-report` rc=0、`check_milestone_tasks.py` rc=0；临时树翻转本任务状态后 `check_tasks --strict` rc=0（`logs/check-tasks-flip.log`）✅（如实分项，未冒充整目标绿）
5. L1 `make check` **rc=0**（尾行 `repository checks (L1): PASS`）✅
6. `git status --untracked-files=all`：本任务改动 = `tools/spec/check_sync_nonmaskable.py` + 任务书 + `milestones.md`（`.work/` 已忽略）；另见 `spec/SimRISC-00-指令系统设计.md` 与 `manifests/spec-readonly.lock.toml` 两项**非本任务**改动（09:57 出现，内容为 escape 立即数变更记录补记，**非我所写、未触碰/未还原**，如实披露）；`/tmp/opencode/INFRA-114t/` 用完即清 ✅
7. 完成区数值取自 `logs/` 真实输出与退出码，未转述 ✅
**新发现/坑**：① `check-milestone` 含 `check_tasks --strict`，任务处于「完成区已填 + 待验收」时**必然 rc=2**——本类任务验收不能以整目标 rc 作绿判据，须分项 + 状态翻转临时树证明（同 `INFRA-112t` 先例）；② `check-milestones-fresh` L11：非 `已验证` 行时间**必须保留** `HH:MM（登记）`，改状态时勿删；③ `Makefile` 两处文案（207 行 help echo、1125 行注释）仍作 `IPI / TIMER / UART* / 占位行 …`，未改（任务限定单文件，`…` 可涵盖）；④ 自检小表用 `maskable_rows==1` 证明行**确被扫描**（防空扫假绿，lessons §2.20/§2.21）；⑤ 注入/还原全程 `cp`+md5（lessons §3.2）；⑥ **并发写入**：`spec/SimRISC-00` + `manifests/spec-readonly.lock.toml` 于 09:57 被其它会话改动（escape 立即数变更记录补记），本任务未触碰——同工作树并发写者存在，`git status` 判「干净」须按文件归属甄别。
**遗留问题**：无（`Makefile` 帮助文案欠同步属可选打磨，不阻塞收尾）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-01）

自查项：白名单是否退化为通配（否：`^(?:IPI|TIMER|UART\d*|PMEM_DMA|\.\.\.)$` 锚定枚举，见步 3 静态锚点 `mismatch=[]`）；新增断言是否有可达 FAIL（是：移除白名单项 ⇒ 步 5 `[BAD]`，实跑 rc=1）；合成小表是否为空扫（否：`maskable_rows=1` 且基线行数现场统计 =1）；是否误改语义/TARGETS/其它门控（否：`git diff` 仅本脚本 55+/6-）；临时树是否残留（`--self-test` 的 tmp 子目录 finally 清理，`/tmp/opencode/INFRA-114t/` 已清）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 只改正则而无显式断言（任务书第 3 条） | ✅已修 | `--self-test` 步 5/5b | `logs/selftest.log` `[OK] PMEM_DMA=可 必须白名单命中且不报错` |
| 白名单可能被放宽成通配 | ✅已修（加反向守卫） | 步 5b `CFXMEM=可` 必须 FAIL | `logs/selftest.log` 步 `pmem-dma-neg` rc=1 |
| 断言恒真 / 空扫风险 | ✅已修 | 断言 `maskable_rows==1` + 现场行数 | `logs/selftest.log` prints `PMEM_DMA 行数 = 1` |
| 改状态后 `check-milestones-fresh` L11 报「时间须带（登记）」 | ✅已修 | milestones 行时间恢复 `2026-11-01 09:52（登记）` | `python3 tools/infra/check_milestones_fresh.py` ⇒ `结果: PASS` rc=0 |
| `make check-milestone` 整目标在 `待验收` 窗口 rc=2 | ✅处置（非缺陷，非冒充绿） | 证据脚本改为分项 + 临时树翻转状态证明 | `logs/check-tasks-flip.log` rc=0；`logs/milestone-sub.log` rc=0 |

判决：全部 finding 已修 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-01）

**重跑记录**（均 reviewer 亲跑，workdir=仓库根，非采信完成区）：
- 门控本体：`python3 tools/spec/check_sync_nonmaskable.py` ⇒ `rc=0`，stdout `files=3 tables=9 rows=70 maskable_rows=8` + `PASS（仅异步源（IPI/TIMER/UART*/PMEM_DMA/…）可屏蔽）` ✅
- `--self-test` ⇒ `rc=0`（`[OK]=7/[BAD]=0`，含 `[OK] PMEM_DMA=可 必须白名单命中且不报错` + 反向 `[OK] CFXMEM=可 必须仍 FAIL`；小表 `maskable_rows=1` 非空扫、基线行数现场统计=1）✅
- 证据脚本 `bash .work/evidence/INFRA-114t/run.sh` ⇒ **9/9，SCRIPT_RC=0**（含 L1 `make check` rc=0 尾行 `repository checks (L1): PASS`；`check-milestone` 分项 sub_rc=0 + mbook_rc=0；`check_tasks --strict` rc=1 且 ①漏收尾唯一项=本任务；临时树翻转状态后 rc=0）✅
- **独立反例注入**（reviewer 自做，非采信脚本内置步）：cp 备份后移除白名单 `PMEM_DMA` ⇒ 门控 `rc=1`（报 `DADAO-12-…md:662: 同步异常原因 PMEM_DMA 被标为可屏蔽`）、`--self-test` `rc=1`（`[BAD] PMEM_DMA=可` 显式步 RED）、重跑同一 run.sh ⇒ **6/9 FAIL，SCRIPT_RC=1**；`cp` 还原 + md5 对账（`50af8c1e972db8d09c2e2db2f212d27f` 相等）⇒ 门控/self-test/run.sh 全回绿 ✅
- `make check-milestone` 独立整跑 ⇒ `rc=2`：全部子门控 PASS，唯一红源 = `check_tasks --strict` ①漏收尾=1（恰为本任务自身，`/complete` 翻 `已验证` 即消，翻转测试已证）——按裁定分项报告、不改状态 ✅

**约束核验**：① 白名单为锚定枚举 `^(?:IPI|TIMER|UART\d*|PMEM_DMA|\.\.\.)$`，非通配（静态锚点 allow/deny 全对 + 注入下 deny 项报错可证）；② 提交 74f26dfc 仅 3 文件（脚本/任务书/milestones），未改 `spec/DADAO-12`（PMEM_DMA 仍「可」，662 行亲验）、未改 TARGETS、未改其它门控；③ docstring/白名单/PASS 文案三处口径一致；④ `INTEG-052m` 仍 `待验收`（亲验）；⑤ milestones 仅本任务行 待开始→待验收，`(登记)` 时间保留；⑥ 快照对账：验收前后 `git status --porcelain -uall` 均空、`diff SNAPSHOT_MATCH=yes`，注入全还原。

**判决：Accepted**（工程师达标证据，终审归 architect；`make check-milestone` 整目标红为「本任务待验收」窗口效应，`/complete` 后自消）。

### 第 1 轮 architect 交叉复核（2026-11-01，`/complete`）

**独立抽核**（architect 亲跑，不采信前两轮叙述）：`check_sync_nonmaskable.py` rc=0（`files=3 tables=9 rows=70 maskable_rows=8` + PASS 文案含 `PMEM_DMA`）；`--self-test` rc=0（`[OK]`×7、`[BAD]`×0，含 `PMEM_DMA` 显式步与其 `CFXMEM` 反向步）；L1 `make check` rc=0（尾行 `repository checks (L1): PASS`）。

**状态翻转前** `make check-milestone` rc=2 的分项核对：`check-spec-archive` / `check-spec-archive-verify` / `check-sync-nonmaskable` / `check-night-report` / `check-l3-report` / `check_milestone_tasks`（`M10 有 m 册；所列任务号全部真实存在`）**全 PASS**，唯一红项 = `check_tasks --strict` ①漏收尾=1 且命中项恰为本任务（`待验收` + 完成区已填）⇒ 窗口效应，非缺陷。翻转后 `make check-milestone` **rc=0**。

**结论**：与 reviewer 判决一致 ⇒ **Accepted**；M10 收尾门控缺口（`INTEG-052m` 遗留）已消除，`INTEG-052m` 置回 `里程碑`。
