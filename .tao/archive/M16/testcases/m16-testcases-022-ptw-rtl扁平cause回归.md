# m16-testcases-022: PTW 测试的 RTL 面在扁平 cause 对齐后修复/回归

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m17-chipyard-001`（RTL `excp_cause_id` 扁平位图对齐，ADR-0062）合入
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-25 裁定 B）

`m17-spec-002`（ADR-0062）把 `excp_cause_id` 改为**扁平位图**（PTW 故障只置高位、低位 cause 全 0），RTL 仍按 ADR-0056 两级 wyde ⇒ RTL 上凡拿 `CAUSE_*` 做 guest 断言的用例必红（`arch-ptw-009` rc=47、`arch-ptw-011` rc=54、`arch-ptw-013` rc=3）。用户裁定：**保留这些 signature，接受 RTL known-red**，并单独立本任务在 `m17-chipyard-001` 之后修复/回归。

`m16-testcases-019` 已把 `arch-ptw-013` 升为 signature 并保留静态接线；本任务只做 RTL 面收尾，不改 QEMU/gem5 面。

## 要做

1. **前置确认**：`m17-chipyard-001` 已合入且 RTL 的 `excp_cause_id` 为扁平位图（跑一条最小 `CAUSE_*` 探针确认）。
2. **RTL 回归**：`arch-ptw-009/011/013` 在 `run_arch --platforms chipyard`（H/S/U 或声明的模式）下转绿；`arch-ptw-002/007`（DIV-14）不回归；`check_ptw_rtl --selfcheck` 的 signature/guest/gap 集合与本任务后的登记一致。
3. **登记收尾**：删除/收窄 `ISS-m16-006` 的 RTL known-red 说明；若 `m16-testcases-019` 的 BLOCKED/EXPECTED-RED 文案需要更新，一并改为"已闭合"。
4. **不回归**：`tests/arch/ptw/` 的 QEMU/gem5 面不变；`DIV-14` 保持；`check-tests-index`/`check-tasks`/`check-knowledge-refs`（基线悬空见当时状态）。

## 不做

- 不改 RTL/spec（属 `m17-chipyard-001`）；
- 不改 PTW 的 QEMU/gem5 期望；
- 不新增 cfx4 的 S/U RTL 面（仍按 `DIV-09`）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/ptw/**`、`tests/arch.yaml`、`tests/arch/modes.yaml`、`expected-divergences.yaml`、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `arch-ptw-009/011/013` 的 RTL 面转绿（或按声明模式）；`002/007` 不回归；
2. `run_arch --platforms chipyard` 对 cfx4 的 `signature` 集合无 FAIL（gap 只剩 014/015）；
3. **可达 FAIL ≥2**：注入"把 cause 期望改回旧两级编码"、"把 013 退回 gap" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据目录 `run.sh` → **68 PASS / 0 FAIL、rc=0**（`logs/run-default.log`）。要点：S1 最小探针 cause=`0x10000000000000`（`1<<52` DGPTRAP，低位 cause=0、保留位=0），`CFXMEM`=`0x2`（高位=0）；S2 全 15 条 RTL：`009/011/013` rc=0（原 known-red 转绿）、`002/006/007` rc=0 不回归（007 的 DIV-14 两槽仍 0/0）、`014/015` rc=77；S3 `check_ptw_rtl --selfcheck` rc=0（signature=4/guest=9/gap=2，集合由 `arch.yaml`/`expected.yaml`/`rtl-coverage.yaml` 现场派生）；S4 `run_arch --cfx 4 --platforms chipyard --mode hmon` rc=1，15/15 条驱动均为 `unrecognized arguments: --mode`（ISS-m16-010），**无** cause 失配；S5 QEMU `009/011/013` 与 gem5 `013` 全 rc=0，`expected.yaml`/`ptw_carrier_tlb.py`/`check_tlb.py` 相对 HEAD 未改；S6 四门控 rc=0；S7 注入 A（高位 cause 改回旧两级编码）⇒ `010` rc=1、注入 B（013 退回 gap）⇒ `013` rc=77 且 selfcheck rc=1，`cp`+md5 还原（`e17ff953…`/`86e12999…` 相等）⇒ 回绿。
**修改文件**：`tests/arch/ptw/ptw_sig.S`（013 槽 0 记录点前移到回读断言后）、`tests/arch/ptw/rtl-coverage.yaml`（009/010 note 按 ADR-0062 扁平模型）、`tests/arch/ptw/check_ptw_rtl.py`（docstring 的 signature/gap 集合）、`tests/arch/ptw/README.md`（`PTW_CASE=1..13` + 扁平 cause 回归说明）、`.tao/knowledge/issues-m16.yaml`（关闭 `ISS-m16-006`；**超出任务书文件清单，按派单第 3 项执行**）、`.tao/tasks/testcases/m16-testcases-019-ptw-su覆盖与013提升.md`（完成区顶部追加「已闭合」说明，未改审阅记录）、本任务书；证据脚本/日志/探针在运行期证据目录（不入库）。未改 `expected.yaml`、`ptw_carrier_tlb.py`、`check_tlb.py`、`tests/arch.yaml`、`modes.yaml`、`expected-divergences.yaml`（DIV-14 保持 active）。
**验收结果**：probe 构建 `llvm-mc`/`ld.lld` rc=0、guest rc=0；Vast sim md5 `1260b0f0…`（含 028 rc6 + `m17-chipyard-001`）。真实输出：`PASS rtl arch-ptw-009/011/013 rc=0`；`013` 三槽 `0x1122334455667788 / 0x2 / 0x180000000040`；`PASS rtl arch-ptw-007 slots=[14987979561499688941, 11072869122414935808, 0, 0]`；`GAP arch-ptw-014/015` rc=77。门控 rc：`check-tests-index` 0（504 条）、`check-tasks` 0、`check-knowledge-refs` 0（0 具体路径/0 悬空）、`run_arch --self-test` 0、`check_ptw_rtl --selfcheck` 0。
**新发现/坑**：① `ptw_sig.S` 的 `PTW_CASE=13` 槽 0 原先把 `INVAL_ALL` 覆写后的 `rd6`（`CTL_INVALID_ALL`=`0x12`）当回读值记录，而非 cfx_pmem 回读的 M1；因 013 在 RTL 上一直是 known-red（签名流为空），该错误从未被观测到，QEMU/gem5 用另一载体 ⇒ 三方从未逐字节对过该槽。② 只判 rc 绿不够：`009/011` 的 rc=0 只覆盖 guest 断言，签名槽错误必须逐槽比较（本任务 S2 对 013 三槽断言）才抓得到。③ `check_ptw_rtl.py` 缺 `--mode` ⇒ `run_arch --platforms chipyard` 对 cfx4 必 rc=1（15/15 driver rc=2）；直调驱动是当前唯一可用的 RTL 回归路径，S4 的 rc=1 断言随 `ISS-m16-010` 修复需改 rc=0。④ 证据脚本依赖 worktree 内运行期安装根/共享构建软链（gitignored）；换 worktree 需重建。⑤ 旧构建 `d9d613c3…`（缺 023/027/m17）上 013 仍 known-red 或不能 loadmem，不能当对照。
**遗留问题**：① `ISS-m16-010`（缺 `--mode`、单平台假不一致）保持 open（本任务不修），S4 期望届时改 rc=0。② `ISS-m16-011`（cfx15 flake）本任务未触发，PTW 15 条均无超时。③ cfx4 的 RTL 承载仍只跑 hmon（`DIV-09`），S/U 的 RTL 面未覆盖。④ 探针/证据只在运行期目录，未入库。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查了 `ptw_sig.S` 的 013 改动、`rtl-coverage.yaml`/`check_ptw_rtl.py`/`README.md` 的文案、`issues-m16.yaml` 的关闭条目与 019 任务书的追加行，并把每条判据落到 `run.sh` 的真实执行上。发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 013 槽 0 记录的是 `INVAL_ALL` 覆写后的 `rd6`（0x12），不是 cfx_pmem 回读值 M1；RTL 一直红所以从未暴露 | ✅已修 | `ptw_sig.S` 把 `SIGUPD rd6` 移到 `__VERIFY_RD 2, rd6, M1` 之后（槽序不变） | S2 013 三槽 = `0x1122334455667788 / 0x2 / 0x180000000040`；注入 B 仍可达红 |
| 只按驱动 rc 判绿会漏掉签名槽内容错误（009/011 的 rc=0 只证 guest 断言） | ✅已修 | S2 增加 013 三槽逐字节断言、007 DIV-14 槽 2/3 断言 | `run-default.log` S2 两行 PASS |
| `run_arch --platforms chipyard` 的 rc=1 是 `ISS-m16-010` known-red，若当普通绿会掩盖问题 | ✅已修 | S4 显式断言 rc=1 且 15/15 日志为 `--mode` argparse 错误、无 cause 失配；README/遗留写明 010 修复后改 rc=0 | S4 4 行 PASS；`logs/run-arch-chipyard.log` |
| `rtl-coverage.yaml` 010 note 仍写「CFXMEM + DGPTRAP」旧两级口径 | ✅已修 | 改为「只置 DGPTRAP/IGPTRAP，CFXMEM=0（ADR-0062）」 | S3 selfcheck rc=0 |
| `check_ptw_rtl.py` docstring 的 `signature`/`gap` 集合写 002/006/007 与 013/014/015 | ✅已修 | 改为 002/006/007/013 与 014/015 | diff 自查；selfcheck 现场集合同 |
| 改了任务书文件清单外的 `issues-m16.yaml` 与 019 任务书 | ❌不修 | 派单第 3 项明确要求关闭 `ISS-m16-006` 并把 019 的 EXPECTED-RED 文案改为已闭合；只追加「已闭合」说明，未改 019 审阅记录；已在「修改文件」披露 | `git diff` 仅 6 文件；019 审阅记录段字节未变（`git diff` 无该段） |
| 证据脚本依赖 worktree 内运行期软链，换树不可直接跑 | ⏸延后 | 属运行期环境；记录为新发现④，不作为交付物 | 本 worktree 重跑 rc=0 |

判决：全部 finding 已修（越界项为派单明确要求，已披露），任务可转「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（本 reviewer 独立执行，不采信完成区）**

- 仓库根执行运行期证据目录内的 `run.sh` → `checks: 68 PASS / 0 FAIL`、`run.sh: checks.py rc=0`；本次输出与完成区引用的日志逐行 `diff` 一致。
- 扁平 cause 前置（S1 现场）：PTW 故障 cause=`0x10000000000000`（全字相等 ⇒ `[15:0]=0`、保留位全 0）、`cause_info=0x10000`；`ptw_enable=0` 与保留 cfx cause=`0x2`、高位 `[63:32]=0`；探针 guest rc=0。RTL 源侧 `m17-chipyard-001` 已合入（`bec9578a`），`gewu.GewuCauseId`/`WumingPtw`/`WumingTlb` 均为 ADR-0062 扁平位图。
- RTL 回归（S2，15 条 id 由 `tests/arch.yaml` 现场派生）：`arch-ptw-009/011/013` rc=0；`013` 三槽 `0x1122334455667788 / 0x2 / 0x180000000040`；`002/006/007` rc=0，`007` 四槽 `0xd00000006000ffed / 0x99aabbccddeeff00 / 0x0 / 0x0`（DIV-14 仍 `active`、该文件未改）；`014/015` rc=77。`check_ptw_rtl --selfcheck` rc=0，现场 `signature=4 / guest=9 / gap=2`。
- S4 归因：`run_arch --cfx 4 --platforms chipyard --mode hmon` rc=1；15 份驱动日志逐份计数 = `--mode` 未识别 15×1、槽比较/`guest 退出码` 失配 15×0，另有 4 条单平台假「跨平台不一致」⇒ 确为 `ISS-m16-010`（`check_ptw_rtl.py` 缺 `--mode`），**非** cause 失配。
- 测试缺陷修复：`ptw_sig.S` 仅把 `SIGUPD rd6` 移到 `__VERIFY_RD 2, rd6, M1` 之后（`INVAL_ALL` 会覆写 rd6），槽序仍 3 槽、期望未变，改动只落在 `PTW_CASE=13` 分支。
- 门控（S6 现场）：`check-tests-index` rc=0（504 条现场统计）、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 具体路径/0 悬空）、`run_arch --self-test` rc=0。S5：QEMU `009/011/013`、gem5 `013` 全 rc=0，`expected.yaml`/`ptw_carrier_tlb.py`/`check_tlb.py` 相对 HEAD 未改。
- 注入（S7，reviewer 重跑）：A 高位 cause 退回旧两级编码 ⇒ `arch-ptw-010` rc=1；B `013` 退回 gap ⇒ `arch-ptw-013` rc=77、selfcheck rc=1；`cp`+md5 还原（`e17ff953…`/`86e12999…` 相等）⇒ 010/013/selfcheck 回绿 rc=0。
- **独立注入（reviewer 自做）**：把 `ptw_sig.S` 的 `SIGUPD` 退回 `INVAL_ALL` 之后 ⇒ 同一 `run.sh` `64 PASS / 4 FAIL`、rc=1，驱动真红 `[FAIL] 槽 0 期望 0x1122334455667788 实际 0x0000000000000012`；`cp`+md5 还原（`e47b1271…` 相等）⇒ 重跑 `68 PASS / 0 FAIL`、rc=0。
- 登记：`ISS-m16-006` 已 `closed`/`resolved_by: m16-testcases-022` 且写实测闭合（三槽/不回归/gap 集合）；`m16-testcases-019` 完成区仅追加 5 行「已闭合」段、审阅记录段无 diff；`rtl-coverage.yaml` 009/010 note 改扁平口径；`check_ptw_rtl.py` docstring（signature 002/006/007/013、gap 014/015）与 README `PTW_CASE=1..13` 已订正。
- flake：`ISS-m16-011` 本轮未出现（全部日志无超时/挂死命中）。
- 快照对账：验收前后 `git status --porcelain -uall` 逐行相同（7 文件，与完成区「修改文件」一致），注入残留 0（无 `.orig-022` 备份残留）。

**约束核验**：独立 worktree、未提交 git；未改 RTL/spec、QEMU/gem5 期望、`arch.yaml`/`modes.yaml`/`expected-divergences.yaml`；任务书无具体运行期路径；术语「寄存器组」合规。越界项 `issues-m16.yaml` 与 019 任务书系本任务书「要做 3」明确要求，改动仅「关闭」与「追加一段」，已披露 ⇒ 记 finding 不阻断（建议收尾时把「约束」的文件清单与「要做 3」对齐）。

**判决**：Accepted（重跑 68 PASS/rc=0、注入可达红并回绿、登记与文档订正到位、无越界扩大）。
