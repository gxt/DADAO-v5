# m16-testcases-014: cfx32 pmem DMA 完成中断 + 同界多源（R2 捕获缓冲）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m18-spec-005`（R2）；`m16-chipyard-022` 合入后升三方；同源用例 `013` 可并行复核
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（R2）

PMEM_DMA 源 = `cfx_pmem`（32）：pending/捕获位 = `1<<32`，掩码在当前模式 monitor `cg8 rc1` 的 bit32；DMA 细节回 `cfx_pmem cg15 rc4 dma_status`（W1C），无 `cause_info`。`cg9` 是捕获缓冲（每次进入覆盖、无帧活动期），软件搬走后 handoff `cfx_smon`；`escape imms18=2` ⇒ `CFXESC`（不异步返回）。同一界面 timer(15)+DMA(32) 都放行时**一次进入、一份捕获**（`src_frame` 位图并集）。

## 要做

1. **DMA**：配置/搬运/完成状态；数据逐字节回读；`DONE`/`ERROR` + `ERR_CODE`。
2. **放行**：写当前模式 monitor `cg8 rc1` 清 bit32（与 bit15）。
3. **捕获**：完成 ⇒ `src_frame = 1<<32`、`src_pending` 投递后清；细节读源 cfx。
4. **屏蔽/pending/ack**：mask bit32=1 只置 pending；放行后投递；W1C `dma_status` 后 pending 落。
5. **同界多源**：timer+DMA 同时 pending 且放行 ⇒ **一次进入**、`src_frame = (1<<15)|(1<<32)`、两位都清、`excp_async_num` +1；对照"拆成两次进入"应 FAIL。
6. **覆盖语义**：不搬走再到期 ⇒ 整体覆盖（不是只置 pending）。
7. **无异步返回**：`escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/SBZ 非零 ⇒ `ILLI`。
8. **H/S/U 三模式**各跑一次，各写自己 monitor 掩码。
9. **三方**：QEMU + gem5 先跑；`m16-chipyard-022` 合入后升 RTL 三方。

## 不做

- 不做软件 handoff 到 `cfx_smon`（`m18-linux-022`）；
- 不做 cfx15 单源基础项（013 已覆盖）；
- 不做 monitor-first、嵌套帧、uart、多核。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/期望集中 `tests/arch/`；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 搬运逐字节、DMA 状态/错误码；
2. 捕获 `src_frame=1<<32`、mask 位 32、ack 后 pending 落；
3. **同界多源**：一次进入、两位并集、计数 +1（与"串行两帧"可达 FAIL 对照）；
4. **覆盖语义**：不搬走再到期整体覆盖；
5. `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；
6. 三方签名逐槽一致（RTL 未合入时两方并登记）；
7. **可达 FAIL ≥2**：注入"多源串行开两帧"、"`escape` 返回" ⇒ 红；`cp`+md5 还原回绿；
8. `check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **41/41 PASS、rc=0**。内置注入：A「同界多源拆成单源帧」（`MASK_ALLOW_BOTH` 只放行 TIMER）⇒ rc=1，命中 `multi capture src_frame = union bitmap` 与 `multi capture src_pending = 0`；B「`escape imms18=2` 按旧语义返回」⇒ rc=1，命中 `CFXESC: cg5 cause` 缺槽与后续 ack 槽错位；两路 `cp` 备份 + md5 对账（`752ce691…`）还原后回绿。

**修改文件**：
- 新增：`tests/arch/pmem/{pmem_dma.S,pmem_dma.lds,pmem_dma_qemu.lds,pmem_oracle.py,check_pmem_dma.py,check_pmem_rtl.py,expected.yaml}`；
- 改：`tests/arch.yaml`、`tests/arch/modes.yaml`、`tests/arch/expected-divergences.yaml`、`tests/arch/README.md`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、`tests/arch/pmem/README.md`、`tests/arch/vast-arch-inventory.md`、本任务书。

**验收结果**：
- **QEMU+RTL 两方逐槽**：`run_arch --cfx 32 --platforms qemu,chipyard` 的 hmon/smon/umon 三次 rc=0，归一化签名 `signature_equal=true`（55/10 槽）。DMA 8 B 往返与 3 B 部分拍（邻居字节保留）、`DONE`/`ERROR`+`ERR_CODE`（SIZE=`0xC`、PA_FAULT=`0x44`、读 ROM 合法）；**一致性 A**：先脏行 → CFX→PA 后 `D|invalidate` 读到 DMA 值，CPU 脏行 → `D|clean` 后 DMA 读到 CPU 值；`imms18=3/4 ⇒ ILLI`。
- **捕获/多源/覆盖**：屏蔽期 `pending=1<<32`、`src_frame=0`；投递后 `src_frame=1<<32`、`pending=0`、`excp_async_num=1`、细节回 `cg15 rc4=DONE`；`escape imms18=2 ⇒ CFXESC` 且 `cg9` 四槽不变；同界 TIMER(15)+DMA(32) ⇒ **一次进入**、`src_frame=0x100008000`、`pending=0`、计数 2；W1C 后 pending 落、放行无遗留投递；第 3 次进入整体覆盖。
- **H/S/U**：三模式各跑一次，S/U 各写自己 monitor 的 `cg8 rc1`（回读全 1）→ pending → 放行 → 投递（DMA 在 hypv 启动、完成落在目标模式）。
- **三方**：gem5 仍 R2 前模型（无 `cfx_hart cg9`）⇒ `arch-pmem-001` 从槽 16 起读回指令字、rc=1（fail-closed、非 timeout）；`DIV-17` 已扩展覆盖本 case，逐槽为 **QEMU+RTL 两方**。
- 门控：`check-tests-index` rc=0（504 条）、`check-tasks` rc=0、`run_arch --self-test` rc=0；`check-knowledge-refs` **rc=2 基线 KNOWN-RED**（唯一条 `.tao/knowledge/milestones-m17.md:36 ADR-0063` 在 HEAD 已存在，属在跑任务 `m17-spec-004`；按「错误集与基线逐行相同」判）。
- 不回归（QEMU）：`arch-hart-001/hmon`、`arch-hart-002/smon|umon`、`arch-cache-001/hmon`、`arch-ptw-001/hmon` 全 rc=0；变更集不含 Tiny/`spec/`/`contracts/`。

**新发现/坑**：
- **RTL 固定 BootROM 不建页表**（power→hmon→jump）；QEMU/gem5 的 step5 BootROM 建。三方同一 case 要 CPU 访问 PA，必须由探针自建：RTL 用 `+loadmem` 把首张页表装到 PA 0，`_start` 写 PTBR/`ptw_enable`/invalidate；U 模式再改 PTE0 的 HSJU=0xF。
- `cfx_cache_ctrl` 的 `PA 区间` = `[3:2]=10`（`0x4000|0x8|op`）；漏 `0x8` 变成「PA 单行」，clean 打不中目标行、DMA 读到 0（QEMU 判据当场抓到）。
- QEMU 的 DMA 完成延迟 1 ms 虚拟时间（`-icount shift=0` ⇒ ~1e6 指令）：「屏蔽期同时置两位」必须先 `POLL_BUSY` 再 BURN；RTL 的 DMA 延迟小，旧 RTL 探针只 BURN 即可。
- gem5 pre-R2 的 `cfx_hart cg9` 读回**指令字**（`0x7a3c9105`）而非 `CFXREG`，用例据此从槽 16 起红、rc=1 且不挂死 ⇒ fail-closed 证据可用。
- 注入是否落到工作树不能看 `git diff`（新增文件是 untracked）；用 md5 变化 + `grep -P` 精确替换判。

**遗留问题**：
- gem5 R2 迁移（`cfx_hart cg9` + monitor 掩码）无任务 ⇒ 按两方交付（`DIV-17`）；
- QEMU/gem5 cfx_pmem 缺 `cg8/12/13/14`（`ISS-533`、`DIV-06`）⇒ 寄存器面仍只有 RTL 探针 `pmem.S`；
- 注入 A 的语义是「同界拆成单源帧」（只放行 TIMER），即串行投递的第一帧；字面两帧需改 handler 流程，未做；
- `POLL_BUSY` 无内建上限，坏 DMA 由驱动 timeout（240/600 s）兜底；
- L2 `check-modules` 未跑（共享安装根 + 并行窗口禁跑），以代表集 QEMU 用例 + 门控代替。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`pmem_dma.S`（三模式入口/PTW/页表、DMA+一致性、捕获/多源/覆盖/escape 槽序、注入点）、`pmem_oracle.py`（期望派生、槽序、self-test）、两个驱动（地址覆盖、oracle、归一化签名、selfcheck、超时/cwd）、两个 lds、`arch.yaml`/`modes.yaml`/`expected.yaml`/`DIV-06`/`DIV-17`、README/inventory、`run_arch.py`/`platform.py`，以及运行期 `run.sh` 的 rc/注入/还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 RTL 上 CPU 访问 PA 报 `CFXMEM[57]`（RTL 固定 BootROM 不建页表，首版假设错） | ✅已修 | `_start` 写 PTBR/TLB invalid/`ptw_enable`；`pmem_dma.lds` 增 `.pt_l1`（PA 0，4 超页）并 `RTL_PTW_TABLE=1` | RTL hmon/smon/umon 全 PASS |
| F2 `D|clean` 只清单行（`0x4005`），DMA 读到 0 | ✅已修 | 区间编码改 `0x4009`（`[3:2]=10`） | QEMU slot 9 回绿；RTL PASS |
| F3 部分拍目的预置值首 3 字节与 DMA 数据相同 ⇒ 断言恒真 | ✅已修 | 预置 `0xDEADBE5A…`、期望 `0xAABBCC5A…` | QEMU/RTL slot 2 PASS |
| F4 RTL 驱动用相对 `--work-dir` 且 sim 以 work 为 cwd ⇒ semiout/ELF 路径错、0 槽 | ✅已修 | `work` 统一 `resolve()` | RTL 三模式 55/10 槽 |
| F5 注入「落到工作树」用 `git diff`（新增文件 untracked 恒空）、B 用 BRE `	` | ✅已修 | 改 md5 前后比对 + `grep -P` | 证据 41/41 |
| F6 注入 B 的「后续槽」断言选错槽（slot 25 是 DMA 细读、注入后仍过） | ✅已修 | 改判后续 ack 槽 | 证据 41/41 |
| F7 两个驱动未捕 `SetupError`（会 traceback 而非 rc=2） | ❌不修 | 与既有 `check_hart.py`/`check_time_rtl.py` 同型；rc=1 fail-closed 可接受 | — |
| F8 `expected.yaml` 槽数靠手写 | ✅已核 | selfcheck/self-test 现场派生 55/10 + `run_arch --self-test` 结构校验 | 全绿 |

判决：F1–F6、F8 已修并有复验；F7 为与既有驱动一致的风格选择，非缺陷。状态置「待验收」。

### 第 1 轮 reviewer 验收

**重跑（独立执行，不采信完成区）**：仓库根跑运行期证据目录内的 `run.sh` ⇒ `SUMMARY: checks=41 fails=0 / RESULT: PASS`，**rc=0**（41/41）。分项：QEMU hmon 55 槽、smon/umon 各 10 槽 rc=0；`run_arch --cfx 32 --platforms qemu,chipyard` 三模式 rc=0，`run.json` 为 `signature_equal=true`、`signature_slots={qemu:55,chipyard:55}`（S/U 各 10/10）；gem5 `rc=1`，驱动 problems 首条「模拟器退出码 1」（**非超时**）、失败自槽 16 起、读回 `0x4`/`0x7a3c9105`/`0x7a3c90c5` 指令字 ⇒ fail-closed 属实、未挂死；门控 `check-tests-index` rc=0（**504 条**）、`check-tasks` rc=0、`run_arch --self-test` rc=0；`check-knowledge-refs`（make）rc=2、悬空 1 条。
**基线 diff**：`git archive HEAD` 导出树跑同一脚本 **rc=1**，与当前树输出 `diff` **rc=0（逐行相同）**；唯一条 `.tao/knowledge/milestones-m17.md:36 ADR-0063`（`adr-0063-*` 不存在，`m17-spec-004` 承接），HEAD 已含该行 ⇒ KNOWN-RED 成立。
**DMA/一致性 A**：原始 55 槽逐条核 = `0x2`(DONE) / `P1` / `0xaabbcc5a11223344`（邻居 `0x5A` 保留）/ `0xC`=ERROR|bit3 SIZE / `0x0`(W1C 清 ERR_CODE) / `0x44`=ERROR|bit6 PA_FAULT / `0x0` / 读 ROM `0x2` / `0xaaaabbbbccccdddd`（invalidate 后 CPU 读到 DMA 值）/ `0x5555666677778888`（clean 后 DMA 读到 CPU 值）；顺序 = `START` 前 `D|clean` 源、`POLL_BUSY`(BUSY=0) 后 `D|invalidate` 目标，两侧均为值断言、不依赖硬件一致；`CACHE_D_CLEAN_SPAN=0x4009` = bit14|[3:2]=10|[1:0]=01，合 `DADAO-12 §4.6` 与 `contract-cache` CACHE-09/17。
**捕获/多源/覆盖**：16/17/18 = `1<<32`/0/0（屏蔽只置 pending）；22/23/24 = `1<<32`/0/1，25 = `cfx_pmem cg15 rc4` DONE；26–33 = CFXESC + `cg9` 四槽 == 槽 19–22；36 = `0x1_0000_8000`、42 = 并集、43 = 0、44 = 2（计数只 +1）、45/47 = 0（W1C 后 pending 落）；49–54 第 3 次进入 `cause_ip=overwrite_fallback`（整体覆盖）、计数 3；`imms18=3/4` ⇒ ILLI（槽 10–15）。三模式：H 55 / S·U 10，S/U 槽 0 回读全 1、槽 4/5 = supv/smon 与 user/umon ⇒ DMA 在 hypv 启动、完成落目标模式。
**注入**：run.sh 内 A「只放行 TIMER」rc=1 命中 `multi capture src_frame = union bitmap` + `src_pending = 0`；B「escape→jump」rc=1 命中 `CFXESC: cg5 cause`；**reviewer 独立注入 C**（`CACHE_D_CLEAN_SPAN 0x4009→0x4005`）rc=1 命中 `slot 09 coherence PA->CFX … actual 0x0`；三路均 `cp` 备份 + md5（`752ce691…`）还原后回绿 rc=0。
**不回归**：`arch-hart-001/hmon`、`arch-hart-002/smon|umon`、`arch-cache-001/hmon`、`arch-ptw-001/hmon` 全 rc=0；变更集 9 改 + 7 新增与完成区「修改文件」逐项一致，`changeset.py` 对 Tiny/`spec/`/`.tao/contracts/` 命中 0，HEAD 无提交；验收前后 `git status -uall` + 目标文件 md5 快照逐行相同 ⇒ 注入零残留。
**遗留判**：gem5 R2 无任务（`DIV-17` + `ISS-m16-004` 待裁定）、`ISS-533`、注入 A 非字面两帧、`POLL_BUSY` 由驱动 timeout 兜底、L2 `check-modules` 未跑 —— 前 4 条成立且已披露；L2 因 gate 锁/并行窗口未跑可接受，但**须在窗口空时补跑**（AGENTS §4 任务收尾 L2）；「证据双份」未见于本任务书遗留段（实为 5 条）。
**finding（均文档级，不阻断）**：① `pmem/README.md:13`「三方承载同一份 case」与同文件 45–47「逐槽 QEMU+RTL 两方」易读成三方；② `DIV-06` 的 `scope: [chipyard]` 与收窄后 impact（QEMU/gem5 寄存器面）不符（无 `slots`，门控不消费其 impact，纯元数据）；③ 完成区称「在跑任务 `m17-spec-004`」，`check-tasks` 实为「待开始」；④ `DIV-17` reason「槽 16 起读回指令字」，实测槽 16 = `0x4`、指令字自槽 17 起（失败确自槽 16 起）；⑤ run.sh E5 未断言 gem5「非超时/槽 16 起指令字」，该两条靠人工核 `run.json`；⑥ 任务书遗留缺第 6 条「证据双份」。以上由 architect 收尾时顺手订正。
**判决：Accepted** —— 验收命令块在本人重跑下全绿（41/41，rc=0）、基线逐行相同、注入红→还原→回绿；约束（独立 worktree、不提交 git、不写运行期路径、术语「寄存器组」、失败路径短 timeout、用例/期望集中 `tests/arch/`）逐条无违反。
