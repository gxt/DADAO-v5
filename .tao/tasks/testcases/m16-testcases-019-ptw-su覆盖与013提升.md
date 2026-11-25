# m16-testcases-019: PTW S/U 覆盖 + `arch-ptw-013` 提升为 signature

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-018`、`m16-chipyard-020`（U/S 路由）已合入；`m16-chipyard-027`（cfx5/PTW 模式面）按需
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

- `ISS-528`：`tests/arch` 的 cfx4 PTW/TLB 用例只跑 `[hmon]`，S/U 运行模式与 PTE 的 S/U 轴未覆盖（QEMU/gem5 载体固定 `cfx_hmon`/hypv、RTL step5 只交付 hmon）；对应用户 2026-11-22"每个 cfx 三模式各跑一次"。
- `ISS-532`：`arch-ptw-013` 的 RTL GAP 理由（pmem SRAM 不可达）已被 `m16-chipyard-022` 消除，可提升为 signature 用例。

## 要做

1. **S/U 运行模式**：把 cfx4 的 15 条用例迁到 `common/env-{smon,umon}` 可跑（按需最小改动，不改 PTW 实现）；H/S/U 各跑一次，不允许的模式显式 `modes` 排除并给原因（排除理由必须实测，不得沿用旧措辞）。
2. **PTE 的 S/U 轴**：补 `H`/`S`/`U` 与 `R/W/X` 组合的 S/U 向量（H 轴已由 case 011 覆盖；J 不测）。
3. **`arch-ptw-013` 提升**：`tests/arch/ptw/ptw_sig.S` 的 `PTW_CASE=13` 改为 signature 用例（用 `cfx_pmem` SRAM 窗口），更新 `rtl-coverage.yaml` 与 `tests/arch.yaml` 状态，删对应 GAP 条目（`expected-divergences.yaml`/`rtl-coverage.yaml`）。
4. **不回归**：`arch-ptw-012` 等既有 12 signature + 2 GAP 不回归；`DIV-14` 保持；QEMU/gem5/RTL 三方逐槽。

## 不做

- 不改 PTW/TLB 实现语义；
- 不改 `m16-chipyard-027` 的 RTL 面（若需要，先等它合入）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/ptw/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx4 15 条在 H/S/U 的模式覆盖（或显式排除原因）与三方逐槽；
2. `PTW_CASE=13` 变为 signature 且三方一致，GAP 条目删除；
3. **可达 FAIL ≥2**：注入"把 013 退回 GAP"、"S/U 掩码错行" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

> ⚠ **RTL 侧为已知红（用户 2026-11-25 裁定 B，`ISS-539`）**：`arch-ptw-013`
> **保留 signature**、接受 RTL known-red。根因：RTL 的 `excp_cause_id` 仍是
> **ADR-0056 的两级 wyde**，`m17-spec-002`（ADR-0062）已改扁平位图 ⇒ 用例的
> `CAUSE_*` guest 断言在 RTL 上必红（隔离树实测：013 `SYS_EXIT code=0x3`、
> 009 rc=47、011 rc=54，同因）。修复/回归由 **`m16-testcases-022`** 在
> **`m17-chipyard-001`（RTL 对齐扁平位图）** 合入后进行；本任务**不主张**该项
> 已在 RTL 上通过。

**测试结果**：QEMU+gem5 全绿：`run_arch --cfx 4 --platforms qemu,gem5 --mode {hmon,smon,umon}` 各 15/15，逐 case QEMU==gem5 签名流逐字节相同（三模式各 30 次比对）；`arch-ptw-013` 的三槽 = `0x1122334455667788 / 0x2 / 0x180000000040`（与 `expected.yaml`、RTL 生成器一致）。`arch-ptw-011` 各模式检查数 hmon=5 / smon=7 / umon=7（S/U 轴）。静态：`check_tlb --selfcheck`、`gen_ptw_sig_tables --selfcheck`（4 签名 case / 13 槽）、`check_ptw_rtl --selfcheck`（signature=4、guest=9、gap=2）全 PASS。**RTL 侧 known-red（裁定 B / `ISS-539`）**：RTL 的 cause 仍是 ADR-0056 口径，`m16-testcases-022` 在 `m17-chipyard-001` 后修复/回归，见遗留 1。
**修改文件**：`tests/arch/ptw/{ptw_carrier_tlb.py,check_tlb.py,expected.yaml,gen_ptw_sig_tables.py,ptw_sig.S,rtl-coverage.yaml,README.md}`、`tests/arch/modes.yaml`、`tests/arch/README.md`、`tests/arch/PLAN.md`、`tests/arch/vast-arch-inventory.md`、`tests/arch/common/{env-umon/env.S,env/cfx_perm.inc,env-README.md,env-MIGRATION.md}`、`tools/testcases/arch/node_probe_prelude.py`；证据脚本与日志放运行期证据目录（`run.sh` / `logs/`，不入库）。
**验收结果**：运行期证据目录内的 `run.sh` → `31 PASS / 0 FAIL / 1 EXPECTED-RED`，退出码 3（known-red 不计 PASS，不算通过）。门控：`check-tests-index` rc=0（504 条）、`check-tasks` rc=0、`check-index-blobs` rc=0、`run_arch --self-test` rc=0；`make check-knowledge-refs` rc=1，但**失败集与基线（`git archive HEAD` 导出树现场跑）逐行相同**（`FAIL (1 悬空小节级互指)`、15 条明细、`item diff: []`；基线 = `milestones-m17.md:36 ADR-0063`），本任务文档不含具体 `.work/**` 路径（`具体路径 (不可复现): 0`）。注入（每条真红 + `cp`+md5 还原回绿）：①`rtl-coverage.yaml` 013 退回 gap ⇒ `check_ptw_rtl --selfcheck` 红；②`ENV_PERM_ALLOW` 只清 hmon 行 ⇒ `arch-ptw-011 --mode smon` 红；③任务书塞一条具体 `.work/**` 路径 ⇒ knowledge-refs 失败集 != 基线（`item diff` 命中该行、判定 `1 具体 .work/** 引用不可复现`）。
**新发现/坑**：① 环境「打开」只清源 cfx_hmon(3) 位，而以**监视器 cfx**（cfx_smon/cfx_umon）身份运行的故障处理程序访问声明的 cfx 会 `CFXPERM` ⇒ 新增 `ENV_PERM_ALLOW`；处理程序应留在**触发模式**（非 hypv），掩码即与 body 相同。② umon 的 U 页拷贝是 do-while（0 会下溢死循环）⇒ 加 0 计数前置判断；进 user 的向量要用 body 真实地址（新增 `ENV_UENTRY`）。③ 改 L1[3] 的 U 位后必须 `invalid|all`（hypv 阶段可能已按 0xC 填过条目）⇒ `ENV_TLB_INVALIDATE`。④ 签名流要与运行模式无关 ⇒ 测试页 PTE 取 `HSJU=H|S|U`（0xD），否则 `expected.yaml` 的槽值要按模式分叉。⑤ `/tmp` 是 16G **共享** tmpfs：4 MiB 镜像/长 `-d cpu` 日志必须落 `.work/`（本次曾写满 /tmp）。⑥ 共享源树里的 Vast 仿真器是**别人的构建产物**（md5 随时被重建改掉），在它上面多段 `loadmem` 镜像会停在 init、连 `[WumingLoadMem]` 行都不打印（`m17-chipyard-001` 的 `ptw_walk` 同现象）⇒ 不能拿它判断 RTL 行为；隔离树重建后镜像能正常加载（`5 PT_LOAD … 4191/4191` 回读校验通过），RTL 的真实红是 cause 口径（ADR-0056 vs ADR-0062），不是仿真器。
**遗留问题**：① **RTL 侧 known-red（用户 2026-11-25 裁定 B：`arch-ptw-013` 保留 signature、接受 RTL known-red，`ISS-539`）**：RTL 的 `excp_cause_id` 仍是 ADR-0056（两级 wyde），`m17-spec-002`/ADR-0062 已改扁平位图 ⇒ `CAUSE_*` guest 断言在 RTL 上必红（**隔离树实测**：`[WumingLoadMem] 5 PT_LOAD … 4191/4191` 回读校验通过、`arch-ptw-013` `SYS_EXIT code=0x3`、`arch-ptw-009 rc=47`、`011 rc=54`，同一根因；不是仿真器问题）。**闭合路径 = `m16-testcases-022`「PTW 测试的 RTL 面在扁平 cause 对齐后修复/回归」，在 `m17-chipyard-001` 合入后修复/回归**（届时跑运行期证据目录内的 `run.sh --rtl`：行为断言、无产物 md5 依赖）。② `014`/`015` 仍为 RTL gap（本任务不做）。③ cfx4 的 RTL 承载仍只跑 hmon（`DIV-09`：cfx4 无 `<mode>` 行），S/U 的 RTL 面未覆盖。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查了本任务的改动（载体镜像构建/模式感知/故障处理、生成器、`ptw_sig.S` 013、
两处共享 env 的按需开关、`expected.yaml`/`modes.yaml` 与文档）。发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 环境「打开」只清 cfx_hmon(3) 源位；故障处理程序以监视器 cfx（smon=2/umon=0）为源访问声明的 cfx ⇒ `CFXPERM`（smon 的 009/010/011/013/015 全红、循环） | ✅已修 | `cfx_perm.inc` 加 `ENV_PERM_ALLOW`（缺省不变）；驱动按模式传 `…F3`/`…F6`；`set_handler` 让处理程序留在**触发模式** | `logs/run-smon.log`、`logs/run-umon.log`（15/15） |
| umon 的 U 页拷贝是 do-while：`ENV_COPY_OCTAS=0` 会下溢成死循环 | ✅已修 | `env-umon/env.S` 加 0 计数前置 `br.z` 跳过 | umon 32/32 checks |
| umon 进 user 的向量写死 `ENV_UCOPY`（拷贝目标）：body 在 ROM 时跳到 0x7000_0000 取指 ⇒ `UNDI` | ✅已修 | 新增 `ENV_UENTRY`（缺省 = `ENV_UCOPY`） | umon 32/32 checks |
| 改 L1[3] 的 U 位后旧 TLB 条目仍按 0xC 判 ⇒ user 命中 `[32] NUPERM`（umon 全红 0xE0） | ✅已修 | 新增 `ENV_TLB_INVALIDATE`（`invalid|all`） | umon 32/32 checks |
| 013 的 `SIGUPD` 落在全零页表生效期 ⇒ `DGPTRAP`（"no exception expected"） | ✅已修 | 先 `set_ptbr(PT_L1)` + 失效，再 `sig_obs` | `arch-ptw-013` 3/3 checks、3 槽 |
| 007b 的 `st64(0x40)` 在 user 下走 L1[0] 超页（HSJU=0xC）⇒ `NUPERM` | ✅已修 | 该检查先把 L1[0] 写成 H|S|U 超页并失效 | umon 32/32 checks |
| case 007 的 ROM 叶 PTE 用 body 相对偏移（0xEFF8）；body 基址移到 env 段后越界（61440 B > 窗口） | ✅已修 | `Check.rom_at`（绝对镜像偏移）+ 与 prelude/env/body/image_at 的重叠校验 | hmon 30/30 |
| `expected.yaml` 的签名槽仍按 HSJU=0x8（与运行模式相关，三模式无法共用一份期望） | ✅已修 | 测试页 PTE 取 `H|S|U`(0xD)，`expected.yaml`/RTL 生成器同步 | `gen --selfcheck`（4 case/13 槽）、`check_ptw_rtl --selfcheck` |
| RTL（chipyard）承载的 013 三方逐槽：RTL 的 cause 编码仍 ADR-0056（wyde），用例按 ADR-0062 扁平位图断言 ⇒ RTL 必红 | ⏸延后 | 未改 RTL（任务「不做」）；证据脚本 `--rtl` 只做行为断言（不绑产物 md5），默认模式记 BLOCKED | 隔离树实测（`SYS_EXIT code=0x3`、009 rc=47、011 rc=54）+ `logs/run-default.log`（BLOCKED 行）+ 遗留 1 |

判决：除第 9 条（RTL 口径滞后，待 `m17-chipyard-001` 合入后复跑）外全部已修并
复验；本任务**不主张** 013 的 RTL 三方逐槽已通过。

### 第 1 轮 reviewer 验收

**重跑（reviewer 亲自执行；以下均为真实输出/退出码）**
1. 仓库根执行运行期证据目录内的 `run.sh` → `26 PASS / 0 FAIL / 1 BLOCKED`、**rc=3**（与完成区一致）；注入 A `check_ptw_rtl --selfcheck` 真红（`FAIL（1 项）`，signature 集 4 vs 3）、注入 B `6/7 checks passed` 真红；`cp`+md5 还原后回绿。
2. 独立 `cmp` 45 对 signature.bin（3 模式 × 15 case，qemu vs gem5）**mismatch=0**；013 三槽 = `0x1122334455667788 / 0x2 / 0x180000000040`（两方 md5 同 `6cd8e919…`、inode 不同 ⇒ 真两方执行）；011 = `5/5`、`7/7`、`7/7`。
3. 门控：`check-tests-index` rc=0（504 条）、`check-tasks` rc=0、`check-index-blobs` rc=0（357 new-file OK）、`run_arch --self-test` rc=0。
4. 覆盖/接线：`modes.yaml` 15 条 = `[hmon,smon,umon]` + `cfx_access` 全声明、无 reasons（现场 `BAD []`）；`rtl-coverage.yaml` signature=4 / guest=9 / gap=2；`ptw_sig.S` 的 `PTW_CASE==13` 分支在；`expected.yaml` 013 三槽齐。
5. env 改动缺省等价（`ENV_PERM_ALLOW`/`ENV_UCOPY`/`ENV_UTAIL`/`ENV_UENTRY`/`ENV_UPAGE_PTE_PA`(0x18−24=0)/`ENV_TLB_INVALIDATE` 未定义则不发射；`node_probe_prelude.entry=None` 回 `BODY_OFF`）。回归 fence(0)/power(63)/pmem(32)/time(34)/cache(5)/hart(15) × 三模式：QEMU 全 rc=0；gem5 红全是已登记缺面（`DIV-17`、asm 未接 gem5、`arch-umon-011` 只接 QEMU），非本任务改动。
6. reviewer 自注入：`modes.yaml` 的 013 退回 `[hmon,smon]` ⇒ `run.sh` **rc=1 / 5 FAIL**；`cp`+md5 还原（`0d20abde…` 相等）⇒ **rc=3 / 26 PASS / 0 FAIL / 1 BLOCKED**。工作区前后 `git status` 与 17 文件 md5 逐行相同；与完成区「修改文件」16 项 + 任务书自身对账一致。

**RTL 013（隔离树，根因已定位）**
1. 共享源树不可用：`m17-chipyard-001` 未提交的 6 个补丁目标文件已就地落进共享源树（从 master 跑 `check-patch-tree` 出 chipyard 12 条 ⑥⑨ 红）。
2. 隔离副本按 master 补丁集收敛：`head_matches_patches=True`（31 补丁 + testchipip gitlink）；`make verilog && make CONFIG=WumingVastConfig -j32` **rc=0**（5m12s，md5 `1daf1a77…`）。
3. `DADAO_REPO=<隔离副本> run.sh --rtl` → **rc=1 / 3 FAIL**：md5 断言 `8b3f221d…` ≠ `1daf1a77…`、`check_ptw_rtl --only arch-ptw-013` **rc=1**、槽空。
4. **不挂死**：`[WumingLoadMem] 5 PT_LOAD segment(s) … 4191/4191 word(s) byte-identical`；guest `SYS_EXIT code=0x3` = `__VERIFY_RD 3, rd5, CAUSE_NONPTW` 失败（断言 2 的 cfx_pmem 旁路回读**通过**）；复跑同结果。
5. 同因红：`arch-ptw-009` rc=47、`arch-ptw-011` rc=54，均卡在 `CAUSE_*` 比对；`arch-ptw-002`（槽 `0xd00000006100ffe1`，本任务 HSJU 改动）与 `arch-ptw-007`（DIV-14）**PASS**。
6. **根因**：`m17-spec-002`（ADR-0062 扁平位图，11-24 20:21）把 `CAUSE_NONPTW/CAUSE_NWPERM…` 改为扁平模型（`1<<sub`、低位 cause=0），RTL 仍按 ADR-0056 ⇒ `m17-chipyard-001`（待开始）合入前，RTL 上凡比 `CAUSE_*` 的 guest 断言必红。**不是 sim 状态、不是多段 loadmem**。

**约束核验**：独立 worktree ✓；不提交 git ✓（前后 md5 相等）；用例/期望集中 `tests/arch/ptw/` ✓；无「银行」✓；失败路径短 timeout ✓；**「不写运行期路径」✗（F1）**。

**发现**
- **F1（阻断·约束/门控）** 任务书 51/53 行写了 2 条具体 `.work/` 证据路径：`check-knowledge-refs` 实测 `具体路径 (不可复现): 2`（基线 0），失败理由由基线 `FAIL (1 悬空小节级互指)` 变为 `FAIL (2 具体 .work/** 引用不可复现)` ⇒ 违反任务书「不写运行期路径」与 AGENTS §5「一律 FAIL」；完成区「与基线逐行相同」不成立。
- **F2（阻断·断言）** `run.sh` 的 knowledge-refs 断言只比 `悬空:` 子集 ⇒ F1 打不红（实测该断言 PASS 而门控失败集已变），未实现判据「与基线逐行相同」。
- **F3（阻断·语义）** 遗留① 的根因与闭合路径错误：「恢复 027 那版 sim 后跑 `run.sh --rtl` 即可闭合」已被隔离树实测**证伪**；真实闭合条件 = `m17-chipyard-001` 合入（或在 `expected-divergences.yaml` 登记该 RTL 滞后）。
- **F4（设计层·供架构师定夺）** 013 由 gap 升 signature 后、`m17-chipyard-001` 合入前，`run_arch --platforms chipyard` 由 `GAP` 变 `FAIL`（009/011 已红）：保留 signature + 登记 RTL 滞后 DIV，或退回 gap 且 `close_when` 改「`m17-chipyard-001` 合入」。
- **F5（脚本）** `run.sh --rtl` 的 `SIM_MD5_EXPECTED=8b3f221d…` 是不可复现的构建产物 md5（换构建路径即变），使 `--rtl` 实际无可达 PASS 路径。

**判决：Needs Revision**（F1–F3 必改并复跑；F4 由架构师裁定；F5 建议改）。其余（26 PASS/rc=3、三模式 15/15 逐字节、S/U 轴 5/7/7、013 静态接线、env 缺省等价与六组代表集回归、四项门控、两处注入红→还原→回绿）全部达标。

### 第 2 轮 engineer 返工（回应第 1 轮 reviewer 的 F1/F2/F3/F5；F4 按架构师指示不动）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书写了 2 条具体 `.work/` 证据路径 ⇒ `check-knowledge-refs` 多 2 条「具体路径（不可复现）」 | ✅已修 | 完成区的 `修改文件`/`验收结果`/遗留① 三处改为「运行期证据目录内的 `run.sh` / `logs/`」措辞 | `make check-knowledge-refs` → `具体路径 (不可复现): 0`、`结果: FAIL (1 悬空小节级互指)`（= 基线） |
| F2 `run.sh` 只比 `悬空:` 子集，F1 打不红 | ✅已修 | 新增 `knowledge_compare`/`knowledge_checks`：基线 = `git archive HEAD` 导出树现场跑同一工具；判据 = **明细项集合 + 结果行类别/计数**全等；新增注入 C（任务书塞具体 `.work` 路径）复用它证明可达 FAIL | `logs/knowledge-diff.log`（`baseline-identical: True`、`item diff: []`）；`logs/injC-red.log`（`item diff` 命中注入行、`False`）；`logs/run-default.log` 的注入 C 三行 |
| F3 遗留① 根因/闭合路径错误（错归因 sim 状态） | ✅已修 | 改为：RTL 仍 ADR-0056 两级 wyde，`m17-spec-002`/ADR-0062 已扁平化 ⇒ `CAUSE_*` guest 断言必红；闭合 = `m17-chipyard-001` 合入后复跑；并写入隔离树实测证据（`5 PT_LOAD … 4191/4191`、013 `SYS_EXIT code=0x3`、009 rc=47、011 rc=54） | 同上三处（完成区顶部警示、新发现⑥、遗留①、自审第 9 行） |
| F5 `--rtl` 绑死构建产物 md5 ⇒ 无可达 PASS | ✅已修 | 删 `SIM_MD5_EXPECTED` 与 md5 断言，改为 `[INFO]` 记录；`--rtl` 只剩行为断言（`check_ptw_rtl --only arch-ptw-013` + 3 槽） | `grep -c SIM_MD5_EXPECTED run.sh` = 0；`run.sh --rtl` 在 RTL 对齐后可达 PASS（当前预期红，见遗留①） |
| F4 013 的 signature/gap 归属 | ➡按裁定 | 用户 2026-11-25 裁定 **B**：**保留 signature**、接受 RTL known-red（`ISS-539`），由 `m16-testcases-022` 在 `m17-chipyard-001` 后修复/回归；`rtl-coverage.yaml`/`expected.yaml` 的 013 不回退 | `rtl-coverage.yaml` 013 = `status: signature` / `rtl_case: 13`；`expected.yaml` 013 三槽在 |

返工后 `run.sh`：`31 PASS / 0 FAIL / 1 BLOCKED`（rc=3，BLOCKED = RTL 口径滞后）。

### 第 3 轮 engineer 收尾（用户裁定 F4=B）

- **归属不变**：`arch-ptw-013` 保持 `signature`（`rtl-coverage.yaml` 未改；
  `expected.yaml` 的 013 三槽未改）。
- **标签**：证据脚本里 013 的 RTL 项由 `[BLOCKED]` 改为
  `[EXPECTED-RED (ISS-539)]`（仍是「不计 PASS」，退出码仍非 0），并先打印一行
  根因：`ADR-0062 扁平 cause vs RTL ADR-0056，待 m17-chipyard-001`；汇总行由
  `BLOCKED` 改为 `NOT-PASS (… expected-red=1 …)`，退出码 3。`--rtl` 仍为**行为
  硬断言**（供 `m16-testcases-022` 闭合后转绿，不绑产物 md5）。
- **文档**：完成区顶部警示、测试结果末句、遗留① 均写入裁定 B + `ISS-539` +
  `m16-testcases-022`（在 `m17-chipyard-001` 后修复/回归）；遗留①不再出现
  「恢复 sim 即可闭合」的措辞。
- **复核**：任务书不含具体运行期路径（`grep -nE '\.work/[A-Za-z0-9]' ` 命中 0）；
  `make check-knowledge-refs` 失败集 = 基线；`run.sh` → `31 PASS / 0 FAIL /
  1 EXPECTED-RED`、rc=3。

### 第 2 轮 reviewer 验收

**重跑（reviewer 亲自执行，以下均为真实输出/退出码）**
1. 仓库根执行运行期证据目录内的 `run.sh` → **rc=3**、`31 PASS / 0 FAIL / 1 EXPECTED-RED / 0 BLOCKED`（与完成区一致；013 的 RTL 项为 `[EXPECTED-RED (ISS-539)]`，不计 PASS、退出码非 0）。
2. QEMU+gem5：三模式各 `PASS（15 case × 2 平台）`、`checked 15 cases; mismatches: []` ×3；013 三槽 `0x1122334455667788 0x2 0x180000000040`；011 = `5/5`、`7/7`、`7/7`。
3. 门控独立重跑：`check-tests-index` rc=0（504 条）、`check-tasks` rc=0、`check-index-blobs` rc=0（357 new-file OK）、`run_arch --self-test` rc=0。
4. **F1**：任务书 `grep -nE '\.work/[A-Za-z0-9]'` **0 命中**；`check-knowledge-refs` 当前 `具体路径 (不可复现): 0`、`结果: FAIL (1 悬空小节级互指)` = 本树 `git archive HEAD` 基线（本树基线仍含 `milestones-m17.md:36 ADR-0063`，master 是否已补 ADR 与本判据无关——按「本树 vs 本树 HEAD」判一致）。
5. **F2**：`knowledge_compare` 现比**明细项集合 + 结果行类别/计数**；绿侧 `baseline-identical: True`、`item diff: []`、两侧同为 `FAIL (1 悬空小节级互指)`/15 items。**reviewer 独立注入 C2**（任务书追加一条具体运行期证据路径）⇒ `run.sh` **rc=1、2 FAIL**（门控断言与注入 C 回绿两处均红），红侧 `item diff` 命中 `:137`、`baseline-identical: False`；`cp`+md5 还原（`5f99bd07…` 相等）⇒ 回 **rc=3 / 31 PASS / 0 FAIL / 1 EXPECTED-RED**。
6. **F3**：遗留① 根因 = `excp_cause_id` 仍 ADR-0056 两级 wyde vs `m17-spec-002`/ADR-0062 扁平位图；闭合 = **`m16-testcases-022` 在 `m17-chipyard-001` 合入后修复/回归**；完成区顶部警示、测试结果、新发现⑥ 三处口径一致，已无「恢复 sim 即可闭合」措辞。
7. **F5**：`grep -rn SIM_MD5_EXPECTED` 于证据脚本/`tests/`/`tools/` **0 命中**；`--rtl` 只剩行为断言（md5 降为 `[INFO]` 记录），且 `expected_red` 仅在 `MODE=default` 分支 ⇒ `--rtl` 仍是硬断言、无洗绿路径。
8. **F4=B**：`rtl-coverage.yaml` 013 = `status: signature` / `rtl_case: 13`；`expected.yaml` 013 三槽未改；16 个代码/文档文件 md5 与本轮审前**逐行相同**，`git status` 审前/审后一致、无 `??` 残留。

**未复跑**：`run.sh --rtl`（隔离树已按上轮收尾清理、共享仿真器属他会话；本轮 F5 判据只需静态 grep + 分支确认）。

**判决：Accepted** —— F1/F2/F3/F5 全部修复并经 reviewer 独立反例验证，F4=B 按裁定落地且未洗绿；第 1 轮其余判据复跑维持全绿。本判决为「工程师达标」证据，架构师仍需终审。
