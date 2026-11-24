# m16-testcases-013: cfx15 timer 中断（R2 捕获缓冲，源 cfxha 15）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-005`（R2 规格）；`m16-chipyard-026`（RTL 捕获缓冲）合入后升三方
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（R2）

`cfx_hart cg9` 是**进入瞬间的捕获缓冲**：每次进入整体覆盖，无"帧活动期"；软件搬走 `cg9`+GPR 后 handoff 到 `cfx_smon`，返回走 smon/umon；`escape imms18=2` **不用于异步返回**（`CFXESC`）。TIMER 源 = `cfx_hart`（15），pending/捕获位 = `1<<15`，掩码在当前模式 monitor 的 `cg8 rc1`。本任务只测 cfx15 单源；多源与 DMA 由 `m16-testcases-014`。

## 要做

1. **放行**：写当前模式 monitor 的 `cg8 rc1` 清 bit15；断言其它位仍 1。
2. **进入**：到期 ⇒ 投 `cfx_hart` supv 单向量（`cg9 rc5 excp_vector`、`rc6=2`）。
3. **捕获快照**：`rc0 prev_run_mode`、`rc1 prev_cfx`、`rc2 cause_ip`（= 提交后的 `rb0`）、`rc3 src_frame = 1<<15`、`rc4 src_pending`（投递后为 0）。
4. **RO**：`rc3`/`rc4` 写忽略、读回不变、不报异常。
5. **覆盖语义**：第一次进入后**不搬走**、再次到期 ⇒ 整体覆盖（`cause_ip`/计数变化）；**断言不是"只置 pending、不进入"**。
6. **屏蔽/pending/ack**：mask bit15=1 时只置 pending；放行后投递；ack（重装 `timer_cmp`）后 pending 落。
7. **无异步返回**：`escape cfx_hart, [async_cause_ip, 8]`（`imms18=2`）⇒ `CFXESC`，`cg9` 不变、cfx/mode 不变；`3`/`[17:2]≠0` ⇒ `ILLI`。
8. **精确点**：补"跳转后到期"用例（`jump` 目标处到期），断言 `cause_ip` = 目标（`SimRISC-06` 的 `jump`）。
9. **H/S/U 三模式**：同一 body，`TMODE=3/2/0`，各写自己 monitor 掩码。
10. **三方**：QEMU + gem5 先跑；`m16-chipyard-026` 合入后升 RTL 三方。

## 不做

- 不做软件 handoff 到 `cfx_smon`（内核任务 `m18-linux-022`）；
- 不做 monitor-first、跨 cfx 仲裁、uart、多核；
- 不做 DMA（014）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 进入/捕获/RO/覆盖/屏蔽→pending→放行/ack/`escape` 拒绝/`ILLI` 逐项；
2. `cause_ip` = 提交后 `rb0`（含跳转后到期）；
3. 三方签名逐槽一致（RTL 未合入时两方并登记）；
4. **可达 FAIL ≥2**：注入"帧门控只置 pending"、"`escape imms18=2` 返回" ⇒ 红；`cp`+md5 还原回绿；
5. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **29/29 PASS、rc=0**（证据日志）；内置注入：A「帧门控只置 pending」（重装 timer 关使能）⇒ rc=1、槽 58/59 红；B「`escape imms18=2` 返回」（8→4）⇒ rc=1、槽 51 红；`cp`+md5 还原后均回绿。gem5 按 DIV-17 预期红（oracle 现场红，非 SKIP）。

**修改文件**：
- 改：`tests/arch/hart/{cfx15.S,check_cfx15.py,README.md}`、`tests/arch.yaml`、`tests/arch/modes.yaml`、`tests/arch/expected-divergences.yaml`、`tests/arch/README.md`、`tests/arch/common/platform.py`、`tests/arch/run_arch.py`、`tests/arch/vast-arch-inventory.md`、本任务书；
- 新增：`tests/arch/hart/{cfx15_qemu.lds,check_hart.py,check_hart_rtl.py,expected.yaml}`。

**验收结果**：
- **QEMU+RTL** 同一 `cfx15.S`：`arch-hart-001` hmon 80 槽、`arch-hart-002` smon/umon 40 槽；归一化签名 640/320 B `qemu==rtl` **逐字节相同**；`run_arch` 三模式 PASS。
- 捕获/RO/覆盖/掩码/ack/escape：`prev_run_mode/prev_cfx/cause_ip/src_frame/src_pending`、`rc3/rc4` 写忽略、屏蔽→pending→放行、ack 后落、第 2/3 次进入覆盖、`escape imms18=2 ⇒ CFXESC` 且 cg9 不变、`3/4 ⇒ ILLI`。
- **精确点**：raw `cause_ip` = ELF `jump_target`（QEMU `0x100894`、RTL `0xffffff010998`；`SimRISC-06` 的 `jump`，非 RISC-V `jal`）。
- 门控：`check-tests-index`/`check-tasks`/`check-knowledge-refs`/`run_arch --self-test` **rc=0**；代表集 umon-smoke 10/10、ptw-001、cache-001 rc=0；Tiny 文件未动。
- gem5：`cg9` 不存在 ⇒ slot 11 读回 `0x4`（CFXREG）、slot 12 为编码；fail-closed，登记 `DIV-17`（`close_when` 必填）。QEMU `cg9 rc6` 写 0 未忽略登记 `DIV-18`。

**新发现/坑**：
- QEMU step5 的 U 页 PTE `HSJU=0xC`（U=0）：`PTW_UMAP` 把镜像所在超页 PTE0 置 `0xF` 并 TLB invalidate，U 模式无需 env 拷贝；RTL 无 PTW，跳过。
- `cfx2rd cycle` 读延迟 QEMU（icount 3/4 cycle）与 RTL（15–21）**不同**；jump 精确点不能写死补偿，改用 `delta=0` 起每 +1 cycle 的有界搜索（QEMU 4 次、RTL 16 次命中）。
- QEMU `-icount shift=0` 是 jump 搜索确定性的前提；**不用 `-d cpu`**（避免 ISS-522 的 GB 级 dump）。
- H 寄存器面含 `cg3`（hypv-only）⇒ H/S/U 拆成 001（H，80 槽）与 002（S/U，40 槽），同一 `cfx15.S`。
- gem5 仍是 R2 前模型（无 `cg9`、旧两级 mask）；QEMU `cg9 rc6` 可写 0（规范固定 supv=2）。

**遗留问题**：
- gem5 `cfx_hart cg9`/R2 迁移（`DIV-17`；尚无 gem5 任务）——本任务的“三方”落地为 QEMU+RTL 两方 + gem5 登记豁免；
- QEMU `cg9 rc6` 写忽略（`DIV-18`）；
- `PTW_UMAP` 依赖 step5 页表 PTE0 布局；step5 改版需同步；
- jump 搜索上限 64 次；后续若接入更慢引擎需复核。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`cfx15.S`（三模式入口、U 页 PTE、jump 搜索、escape/覆盖槽序）、`check_cfx15.py`（期望派生、槽序/自测）、两个驱动（地址覆盖、oracle、归一化签名、selfcheck）、`cfx15_qemu.lds`、`arch.yaml`/`modes.yaml`/`expected.yaml`/`DIV-17/18`、README/inventory、`run_arch.py`/`platform.py`，以及运行期 `run.sh` 的 rc/注入/还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 QEMU 直接链接 0x100000 仍用 RTL 的 `SIG_BUF/EXITB` ⇒ 写 ROM/挂死 | ✅已修 | `cfx15.S` 的 `ENTRY/SIG_BUF/EXITB/HMON_BASE` 加 `.ifndef`，驱动传 `--defsym` | QEMU H/S/U 80/40 槽 rc=0 |
| F2 QEMU U 模式取指 NUPERM（step5 PTE U=0） | ✅已修 | `PTW_UMAP`：PTE0 置 `0xF` + `tlb_control=invalid all` | QEMU umon 40 槽 rc=0 |
| F3 jump 精确点写死 `-2` cycle 补偿在 RTL 偏 8 B | ✅已修 | 改为 `delta` 从 0 每次 +1 的有界搜索（上限 64） | RTL 16 次、QEMU 4 次命中；raw slot = target |
| F4 QEMU `cg9 rc6` 写 0 读回 0（规范 2） | ✅已修（登记） | 槽 17 改为只读回；`DIV-18` | QEMU slot 17=2；差异可追溯 |
| F5 gem5 构建中被重建 ⇒ 证据把 SKIP 误判为 fail-closed PASS | ✅已修 | `run.sh` 等可执行 + 要求 oracle `slot` 行；真实红为 slot 11/12 | 证据日志的 gem5 PASS 依赖真实 `[FAIL] slot` |
| F6 `check_cfx15 --self-test` 假符号缺 `jump_target` | ✅已修 | 假符号表补 `jump_target` | 三模式 self-test rc=0 |
| F7 `run.sh` 日志名含 `/` ⇒ 重定向失败、命令未跑 | ✅已修 | 名称 `tr ' /,' '___'` | 证据脚本三模式均 rc=0 |
| F8 `check_hart.py` 未用的 `signature` 导入；selfcheck 写仓库内目录 | ✅已修 | 删导入；selfcheck 用 `tempfile.mkdtemp` | py_compile/selfcheck rc=0 |
| F9 gem5 三方逐槽 | ⏸延后 | 登记 `DIV-17`；本任务交付 QEMU+RTL 两方 | gem5 oracle 红（slot 11/12），非静默跳过 |

判决：F1–F8 已修并有复验；F9 为已登记的平台缺口（无 gem5 迁移任务），完成区「遗留」明列。状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑（本人执行，不采信完成区）**
- 运行期证据目录内 `run.sh`（干净树）：`SUMMARY: PASS=29 FAIL=0`、`RESULT: PASS`、退出码 0（3 模式 QEMU+RTL、gem5 fail-closed、两路注入红→`cp`+md5 还原→回绿、4 门控、代表集）。
- 独立反例注入（改 `cfx15.S` 的 `MASK_PATTERN`→全 1，非脚本自带两路）后重跑同一 `run.sh`：`RESULT: FAIL`、`PASS=11 FAIL=18`（三 case 的 run_arch/sig/norm/jump 全红）；还原后 15 个变更文件 `md5sum -c` 全 OK，再跑回 `PASS=29 FAIL=0` rc=0。
- `check_cfx15.py --self-test` mode 3/2/0：rc=0，`every slot mutation is rejected`（每槽可达 FAIL）。
- 门控本人重跑：`check-tests-index` rc=0（现场计数 total=500）、`check-tasks` rc=0、`check-knowledge-refs` rc=0（悬空 0、具体运行期目录引用 0）、`run_arch --self-test` rc=0；代表集 umon-smoke/ptw-001/cache-001 rc=0；Tiny 文件未动。
- jump 精确点：ELF `jump_target` = QEMU `0x100894` / RTL `0xffffff010998`，两平台 raw 槽与符号相等；两份 ELF 反汇编均为 `jump [rb2, rd0, 0]`（SimRISC-06 `jump`，非 `jal`）；cycle 搜索 `delta` 0→+1、上限 64（`jump_fail`），无写死补偿，QEMU 侧另加 `-icount shift=0`。

**覆盖核验（槽序取自本人跑出的 oracle 期望，两平台同过）**
- 捕获：槽 2–9 `prev_run_mode`/`prev_cfx`/`cause_ip`/`src_frame=1<<15`/投递后 `src_pending=0`/`rc5` 向量/`rc6` 读回 2/`excp_async_num=1`；槽 45/46 第二次进入的 `src_frame`/`src_pending`。
- RO：槽 14/15 `rc3`/`rc4` 写 PATTERN 忽略、读回不变、无异常（H 寄存器面）。
- 覆盖：槽 58–63 不搬走再到期**整体覆盖**（`cause_ip`=rearm 边界、`excp_async_num`=2），`rearm_fallback` 反证非「只置 pending」。
- 掩码/ack：槽 64–67、73 屏蔽只置 pending → 放行投递 → 重装 `timer_cmp` 后 pending 落；U/S 槽 0/1 同型。
- escape：槽 50–57 `imms18=2 ⇒ CFXESC` 且 `cg9` 不变；槽 33–38 `3`/SBZ ⇒ `ILLI`；同步 `cg5` 返回路径未受影响。
- gem5：oracle 现场红（slot 11 读 `0x4`=CFXREG、slot 12 编码，非 SKIP）；源码核 gem5 无 `cg9` 寄存器面、掩码仍两级 ⇒ DIV-17 描述属实。

**约束**：独立 worktree、未提交（HEAD 仍为派单提交）；变更集 11 改 + 4 新增与完成区「修改文件」逐条一致、无越界、无 Tiny；任务书无运行期路径、无「银行」、新文件无 `-d cpu`。

**DIV-17 判定**：作为差异登记**正确**（用户 2026-11-22 判据 = 有差异必须登记 + 用户裁定；`close_when` 已写需新立 gem5 迁移任务，现无该任务，`m18-gem5-001/002` 只覆盖 escape/CFXESC）。但**登记 ≠ 收口**：M16「三方一致」在用户裁定 DIV-17 前不成立，收口前须用户裁定（豁免或立任务）；本任务按两方交付不因此阻断。

**DIV-18 判定**：**应修 QEMU 而非仅登记**——`§4.7`「固定 supv（2）」与「入口为 supv 单向量」是明文硬要求，而 QEMU 允许写 `cg9 rc6` 且投递时用该值作入口模式（写 0 ⇒ 异步入 user），RTL 为「写接受、忽略」；但同节又写「`rc5`/`rc6` 为软件可读写配置」、未对 rc6 明文写「写忽略」⇒ spec 措辞有张力，建议 spec 补一行澄清。修复归属 QEMU 侧后续任务（承接已验证的异步捕获缓冲任务，编号由 architect 定）；DIV-18 保持 temporary + `close_when` 的登记方式合规。

**Findings（不阻断，交 architect 收尾）**
- F1 `run.sh` 注入 B 注释称「不产生 CFXESC、槽错位」，实测 CFXESC 仍产生、红仅槽 51 `cause_info`（`0x7e3c0001`≠`0x7e3c0002`）：QEMU `helper_cfx_escape` 在 `cfx_hart` 无同步帧（`cause_id==0`）时对 `sel=0/1` 也报 CFXESC，程序级构造不出「`imms18=2` 真返回」反例；该断言的可达 FAIL 由 oracle 自测变异（已重跑）+ 结构判据（真返回则 `esc9_entry` 不执行）覆盖。建议改注释如实描述。
- F2 要做 1「断言其它位仍 1」只在复位值槽 39 断言，三模式写 `MASK_PATTERN` 后均无读回。
- F3 注入 A 注释写「槽 60/61」，实测首红槽 58（完成区 58/59 正确）。
- F4 「归一化签名 qemu==rtl 逐字节相同」按构造成立；实质判据是两平台各自过同一 oracle + raw `cause_ip`==ELF 符号（已具备）。
- F5 完成区「jump 搜索 QEMU 4 次 / RTL 16 次」未落盘，无法独立复核（上限 64 已核）。

**判决：Accepted** —— 验收命令块本人重跑全绿、注入红→还原→回绿、约束无违反；F1–F5 为 finding，由 architect 收尾处置。
