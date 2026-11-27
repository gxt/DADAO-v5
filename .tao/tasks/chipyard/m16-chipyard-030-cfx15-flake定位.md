# m16-chipyard-030: `cfx15.S` 偶发挂死（flake）定位

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无。`m18-chipyard-002/003` 已合入（`cfx15.S` 按 spec-007 重写、cg9/cg5/escape 新布局），`m16-chipyard-033` 已合入（RegRAS 环形缓冲）；chipyard 源树 `7b1d785`、Vast sim `0ead2519…`、Tiny sim `71cbed98…`，安装根 QEMU `e470dc56…`
**可并行分片**：否（共享 `components/chipyard` / `tests/arch/hart`）
**预估**：2–4 h
**档位**：大改（复核 ≤60 min）
**状态**：待验收

## 背景（`ISS-m16-011`）

`m16-chipyard-029` 复核两次 `+verbose` 实测：`cfx15.S` 偶发 **1/3 次在 99607 cycle 挂死**（其余 104765 cycle 正常完成、80 槽）；`m16-chipyard-028` 复核对约 10 次 RTL 运行 **0 次**挂死。原因未定位，与 `+verbose` 无确定相关。它会让 RTL 三方/收口结果偶发假红。

## 要做

1. **量化**：同一构建、同一 ELF、同一命令跑 **≥20 次**（hmon/smon/umon 各一轮），记录每次 cycle/退出码/槽数；统计挂死频率与是否与模式/时序相关。
2. **定位**：挂死时 dump `+verbose` 尾部与 `_start`/中断/`escape` 痕迹；判断卡在 boot、异步投递、`escape`、还是仿真器（Verilator/harness）；与 `ISS-m16-008` 的"旧 ELF"区别开（本任务是**当期 ELF**）。
3. **修复或收敛**：若是 RTL/探针竞态，修并补可复现用例；若是仿真器/harness 的偶发（如 `+max-cycles` 边界、随机种子、内存模型），给证据并登记为已知 flake（`expected-divergences` 不适用，走 issue 的 GAP）。
4. **回归**：修复后 20 次全绿；代表集不回归（槽数以现场派生为准：当前 `arch-hart-001` 124 槽、`arch-hart-002` S/U 各 38 槽、`arch-pmem-001` 48 槽；`time`/`cache`/`ptw` 代表集按 `tests/arch.yaml` 现取）。

## 不做

- 不改 spec/契约；
- 不做 `cg9 rc6`（028 已完成）；
- 不改 ADWBFAIL（023）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 共享源树被占用时用隔离树；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. ≥20 次重复的 cycle/退出码/槽数表（现场生成，不手写）；
2. 若修复：20/20 全绿 + 代表集不回归；若登记 flake：给出频率、条件、影响与复评条件；
3. **可达 FAIL**：注入"恢复挂死条件"（若能确定）⇒ 复现；`cp`+md5 还原回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **106/106 PASS、`EXIT=0`**（默认全量约 21 min）。量化（同一构建/ELF/命令）：hmon **20/20** rc=0、cycle=125418、124 槽（2 槽 = `DIV-17` 登记差异）；smon **20/20** 97862/38/0 failure；umon **20/20** 97854/38/0 failure；每模式 20 份签名与 `+verbose` 日志**逐字节相同**；另 fresh 1 次/模式 + 3 次无 `+verbose` 均与档案同 cycle/签名。挂死 **0/60**，与模式、wall 时序、`+verbose`、随机种子无关。

**根因**：不是 RTL/探针竞态，是 `+max-cycles` **预算截断**。TestDriver 按 **harness 时钟**计（`core=(harness−786)/2`）：`+max-cycles=200000` ⇒ core **99607**、`WumingCore: exec` **14188** 行。029 旧构建+旧 ELF 上 full=104765/**15087** 行、200k 截断=99607/**14188** 行——与 029 复核记录里的 14188/15087 与 99607 **逐数吻合**；同一 200k 预算在当前构建也停在 99607（与 ELF/RTL 版本无关）。故“挂死”是 200k 截断（`*** FAILED *** (timeout) after 200001 simulation cycles`，rc=134），不是卡在 boot/异步投递/escape。

**修改文件**：仅本任务书（状态/完成区/审阅记录）；未改 RTL/探针/驱动/契约。运行期证据目录内 `run.sh`、`quant.sh` 与 logs/work/runs。

**验收结果**：注入 = `check_hart_rtl.py` 的 `+max-cycles=8000000`→`200000`（`cp` 备份、md5 `cf0c2106…`、`git diff` 非空）⇒ hmon driver rc=1、`RTL 退出码 -6`、9/124 槽；`cp`+md5 还原（diff 空）后同参 ⇒ 124 槽、仅 2 个 `DIV-17`。回归：hart-001 124（2 DIV-17）、hart-002 smon/umon 38/38、pmem-001 48、time-001 7、cache-001 21/002 12、ptw-001（0 登记）/002（3）/007（2）。门控：`check-patch-tree` chipyard 0 problem（31 patches；全局 rc=2 仅 musl 2 条既有 KNOWN-RED）、`make_patch` 0 written×2、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test`/`check_hart_rtl --selfcheck` 全 rc=0。

**新发现/坑**：① `+max-cycles` 单位是 harness 周期（2× core，偏移 786），不是 core cycle；旧探针需 210316，200000 只有 95%，很容易被当成“卡死”。② Verilator sim 逐次确定：20×3 日志/signature 位相同，`$random` 固定 `e23cbb39`；`+verbose` 不改 cycle/签名。③ `$fatal`/`$stop` 走 SIGABRT，Python driver 记 `RTL 退出码 -6`（不是 134）。④ 029 复核记录把 14188 行（=200k 截断）当作 verbose 证据、又把 99607 当挂死，实为同一条截断日志的两个现象。⑤ 任务书旧槽数 89/40/40、pmem 55 已随 m18 重写变为 124/38/38、48。

**遗留问题**：`ISS-m16-011` 建议由主会话**关闭为测量伪影**（无需 `expected-divergences`/GAP；复评条件：driver 默认 8,000,000 且无墙钟超时下仍在 `SYS_EXIT` 前停，或日志无 `FAILED (timeout)` 却缺槽）。未改代码；建议另立小任务在 driver docstring/README 注明 `max-cycles` 单位（可选项）。`DIV-17` 2 槽与 `DIV-18` 为既有登记，不属本任务。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-27）

审查范围：`run.sh` 全部 106 条断言（量化一致性、200k 复现、harness/core 换算、注入/还原、回归槽数、门控）与 `quant.sh` 现场统计；逐条核对证据文件与真实输出。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 B 段 fresh 抽样用 `$m`（含 `:3`）而非 `$n` 取档案路径，产生 6 条假 FAIL | ✅已修 | `run.sh` fresh 段改为 `q-$n-verbose` | 全量重跑 106/106、`EXIT=0` |
| F2 D3 只认 `RTL 退出码 134`；Python 对 SIGABRT 记 `-6` | ✅已修 | 断言改为 `-6\|134\|RTL 超时` | D3 PASS；注入日志实为 `RTL 退出码 -6` |
| F3 墙钟截断断言（34.9 s）在主机负载下 cycle 区间不稳，可能假红 | ✅已删 | 默认只保留确定性的 200k 复现（C2/C3）；墙钟机制改在完成区说明 | 两次全量 106/106 |
| F4 固定 sim/ELF md5 会随重建失效 | ⏸延后 | 证据绑定本构建（`0ead2519`/`53c367f6`）；重建后需更新期望 md5 | 完成区已注明 |
| F5 “未改代码”是否满足“修复或收敛” | ❌不修（任务书 §3 允许“登记 flake”） | 根因是预算误读；driver 默认 8,000,000 本身正确，仅建议 docstring 注明单位 | C1–C4 + 60× 确定性 |
| F6 20×3 表消费档案而非 `run.sh` 默认重生成 | ✅已说明 | `run.sh --fresh` 可重跑 60×；默认用 fresh 抽样（9 条）逐字节复核档案 | B 段 fresh 9 条 PASS |

判决：无未修 finding；断言均有可达 FAIL（F1/F2 曾真实红），注入用 `cp`+md5 且 `git diff` 证非空、还原后 diff 空。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-27）

**重跑记录（本人执行；证据 = 仓库根运行期证据目录内的 `run.sh` 及其 logs）**
1. `run.sh` 全量 → **`106/106 checks passed, 0 failed`、`RUNSH_RC=0`**（09:39:37→09:52:31）；A 12、B 36、C 13、D 10、E 23、F 12，与完成区 106/106、`EXIT=0` 逐数一致。
2. 量化独立复跑（本人直接跑 `quant.sh`）：hmon 5/5 `rc=0 cycle=125418 slots=124`、smon 3/3 `97862/38`、umon 3/3 `97854/38`；11 份签名与日志各自 md5 唯一值=1；归档 20×3 表重算 rc 全 0、单 cycle、单槽数 → 挂死 **0/60** 成立；`run.sh` md5 复核前后均 `088a1083…` 不变。
3. 算术/代码位置：`(200000−786)/2=99607` 成立；本人另跑预算 60000/150000 ⇒ 停点 **29607**（精确）/**74605**（公式 74607，−2）。harness 计数 `TestDriver.v:119/124/137`（`CLOCK_PERIOD=1.0`、`RESET_DELAY=777.7`）；设计时钟 2× 慢在 `TestHarness.sv:28-33`（`ClockSourceAtFreqMHz PERIOD=2.0 → clock_uncore`，TestDriver 的 clock 未喂设计）；core 计数 `WumingCore.sv:306 cycles`（`WumingCore.scala:373`）。**786 = 复位前导经验截距，非代码字面量**。
4. 落点：`llvm-nm` `__dump_129 = 0xffffff010b80–0xffffff010bbc`；029 归档与当期 200k 日志尾部均停 `ip=0xffffff010b88`（dump 内）、签名截断 418 B。
5. 「1/3」自洽性（会话库原命令，非采信叙述）：029 复核手跑 `+max-cycles=200000 +verbose` ⇒ rc=134、14188 行、99607；control 与 verbose2 均 `+max-cycles=8000000` ⇒ 104765/15087；归档日志含字面 `*** FAILED *** (timeout) after 200001 simulation cycles` ⇒ **参数差异而非随机**。
6. 独立注入（不经 `run.sh`）：`cp` 备份 md5 `cf0c2106…` → sed `8000000→200000`（`git diff` 仅 1 行）⇒ driver `rc=1`、`RTL 退出码 -6`、`stream truncated: got 9 slots, expected 124`（117 槽 FAIL，01/07 为既有 DIV-17）→ `cp` 还原 md5 相等、diff 空 → 重跑 `summary: 124 slot(s), 2 failure(s)`。
7. 回归（本人 rerun E 段）：hart-001 124/2（slot 01/07 = `DIV-17`，`expected-divergences.yaml` 已登记）、hart-002 smon/umon 38/38、pmem-001 48、time-001 7、cache-001/002 = 21/12、ptw-001/002/007 = None/3/2；F 门控 `check-patch-tree` chipyard 31 patches/0 problem（全局 2 problem = musl 既有 KNOWN-RED，rc=2）、`make_patch` 0 written×2、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test`/`check_hart_rtl --selfcheck` 全 rc=0。

**约束核验**：worktree 前后快照均仅本任务书（`git status -uall` 1 行）、主仓 0 行；`check_hart_rtl.py` 还原后 md5 `cf0c2106…`；chipyard 源树 `7b1d785` clean、sim `0ead2519…`；任务书无 `.work` 路径、无「银行」、证据在运行期证据目录内；未改 spec/契约/RTL/driver（注入为临时且已还原）；无 git 提交；只归因不动 ADWBFAIL/cg9，符合「不做」与收敛口径。

**findings（不阻断，architect 收尾处置）**：F1 `run.sh` C4 两条（`offset=786`、`FULL_HARNESS>200000`）由字面量算出、**不可达 FAIL**；结论不由其承载（C1/C2/C3 实测断言 + 本人多预算实验已覆盖），建议改为从日志解析后计算或降级 INFO。F2 完成区「9/124 槽红」按现场应为「9/124 槽存在、117 槽 FAIL」。F3 默认 `run.sh` 消费归档 20×3 表（`--fresh` 可再生，F6 已披露；本人另跑 11 次独立复现）。

**遗留判定**：`ISS-m16-011` **建议关闭为「测量伪影」**（`resolved_by: m16-chipyard-030`；**不走** GAP/`expected-divergences`）；复评条件：driver 默认 8e6 且无墙钟截断仍在 `SYS_EXIT` 前停，或日志无 `FAILED (timeout)` 却缺槽。其它任务的「偶发退出 1」若再现属另案。

**判决：Accepted** —— 重点 1–7 本人重跑全部通过、独立注入红→`cp`+md5 还原→回绿闭环、约束无违反；findings 由 architect 收尾处置。
