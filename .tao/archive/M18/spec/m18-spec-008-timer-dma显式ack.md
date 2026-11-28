# m18-spec-008: timer/DMA 显式中断 ack（讨论稿）

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-spec-007`（0.8.0 出口帧）、`ADR-0061 R3`
**可并行分片**：否
**预估**：待定（讨论完成后再标定）
**档位**：中改（异步源 ack 语义 + 三实现）
**状态**：已验证
**执行环境**：本地

## 背景

现行 `contract-see §3`/`DADAO-12 §4.7`/`§4.9` 把“中断 ack”定义成两个**副作用**：`TIMER` = 重写 `timer_cmp`；`PMEM_DMA` = `dma_status` 的 `DONE/ERROR` W1C。没有第一类的“ack 操作”，导致：

- 投递即清 `pending`，漏 ack 不留下可检测状态（timer tick 静默停摆）；
- `ISTATUS` 是派生条件（`cmp<=now && ENABLE`），ack 与 re-arm 绑死；`ENABLE=0` 时前置检查失败（内核 `die`）；
- DMA 的 ack 与状态清除、`ERR_CODE` 读取耦合；`BUSY=1` 时 W1C 被忽略；
- ack 没有幂等定义。

用户 2026-11-26 裁定：**A（显式 ack）**。

## 已确定（用户拍板）

1. **走 A：显式 ack**。
2. **当前只有两个异步源**：`TIMER`（源 cfxha 15）、`PMEM_DMA`（源 cfxha 32）。`IPI` 是 `cfx_hart` 的**同步** cause（`1<<8`、单 hart 无发送方，未接异步投递）；`UART`（cfxha 62）无异步路径。
3. **A1：ack 放在源侧，每位 W1C**：
   - `TIMER`：`ISTATUS` 改**粘滞锁存**，W1C 即 ack；`timer_cmp` 只负责 re-arm，不再兼作 ack；
   - `PMEM_DMA`：`DONE`/`ERROR` 的 W1C 定义为 ack；明确 ack 前再次 DONE 的语义；`ERR_CODE` 只在 `ERROR` ack 时清；
   - 内核按 `cg9 rc4`（本次源集合）逐源 ack；不新增 hart 的集中 ack 寄存器。

4. **用户 2026-11-26 追加方向**：**每个中断源都有自己的 `pending`/`mask`/`ack` 寄存器**（源侧自洽，不再把 pending 集中在 `cfx_hart cg9 rc5`、mask 集中在每模式 monitor `cg8 rc1`）。待讨论：mask 是否**取代** monitor 掩码、pending 是否改为 ack 才清、`cg9 rc4 src_frame` 是否随之删除、源侧寄存器如何统一。

5. **用户 2026-11-26 明确 timer 布局**：`TIMER` 移到 **`cfx_hart cg10`**：`rc0` = timer ctrl、`rc1` = timer cmp、`rc13` = ack（W1C）、`rc14` = mask、`rc15` = pending。三个独立寄存器（ack/mask/pending），不再与 `cg8` 混放；`cg9` 的集中 pending/src_frame 与 monitor `cg8 rc1` 掩码的最终去留待定。DMA 的对应布局待定。

6. **用户 2026-11-26 澄清**：
   - `cg9 rc4`（本次源集合）与 `rc5`（pending 汇总）**保留**，作为聚合视图，避免 handler 逐个读源；不是冗余。
   - **源 mask 与 `*mon` 的 mask 不冲突、互不替代**：源 mask 是设备自己的 gate，monitor `cg8 rc1` 是运行模式 gate，两者独立（投递同时受两者约束）。
   - **`escape` 语义不变**：`rc11` 仍整字写目标运行模式 monitor 的 `cg8 rc1`；与源 mask 无关。

7. **用户 2026-11-26 再澄清**：
   - `pending` 语义：**事件置位、ack（源 `rc13` W1C）才清、投递不清**；handler 必须在 `escape` 前 ack 已投递源，想延后就保持该源 mask 关闭。
   - **monitor mask 是每个 monitor cfx（cfx0–3）各自的 64 位寄存器**，位 = 源 cfxha（15/32）。
   - **源 mask 是源自己的事件位图**：不是“一个源一位”，而是“该源的子事件位”——`TIMER` 现在只有一个 `cmp`，所以只有 bit0 有效；将来扩展成两个 `cmp`，就低 2 位有效。源 `pending`/`ack` 同构（按子事件位）。

8. **用户 2026-11-26 定布局**：
   - 中断源统一接口在 **`cg16`**：`rc16` = **mask**、`rc17` = **pending**、`rc18` = **ack（W1C）**（2026-11-26 用户订正顺序）；三个独立寄存器，位 = 该源子事件（当前均只有 bit0 有效）。
   - `TIMER`（`cfx_hart`）：`cg16 rc0` = timer ctrl（**只留 bit0 `ENABLE`**；`IMASK` 由 `rc16` 取代、`ISTATUS` 由 `rc17` 取代）、`rc1` = timer cmp；中断面 `rc16/17/18`（原拟 `cg10` 作废）。
   - `PMEM_DMA`（`cfx_pmem`）：中断面也搬到 `cg16 rc16/17/18`；DMA 引擎寄存器仍留 `cg15`。**子事件合并为一位**（B：`DONE|ERROR` 合并成 bit0“传输结束”），ERR_CODE/DONE/ERROR 细节仍由 cg15 `dma_status` 区分；对外接口与 timer 一致，内部各自解释。
   - `PMEM_DMA` 的 `cg15 dma_ctrl.IRQ_EN`（bit2）**删除**：中断屏蔽统一由 `cg16 rc16` 的 bit0 控制，`dma_ctrl` 只剩 `START`（自清）与 `DIR`（用户 2026-11-26 选 A）。
   - `cg9 rc4/rc5` 仍为 hart 级聚合（bit = 源 cfxha）；monitor mask 仍为每 cfx 64 位（`cg8 rc1`）；`escape` 不变。

9. **DMA ack 范围（用户 2026-11-26 选 B）**：`cg16 rc18` 的 ack 只清**中断 pending**；`dma_status` 的 `DONE/ERROR/ERR_CODE` 仍由 `dma_status` 自己的 W1C 清。**澄清**：这不是“两条中断 ack”——`rc18` 是唯一的中断 ack；`dma_status` 的 W1C 只是**引擎状态清理**，两者对象不同，软件可以先 `rc18` ack 中断、再按需清 status。

10. **timer `ENABLE` 门控事件产生（用户 2026-11-26 选 A）**：`ENABLE=0` 时到期不置 pending；写 `cmp` 只改 deadline、不清 pending（清只靠 `rc18`）。
11. **术语（用户 2026-11-26）**：“投递（delivery）”概念模糊、无实际意义，**取消该提法**；统一称 **“异步进入（async entry）”**——在指令边界上，若存在任一源 `pending & ~源mask` 且 monitor mask 放行（timer 还要求 `ENABLE=1`），硬件执行一次“异步进入”：写 `cg9` 捕获/`hart cg5` 出口意图、切到 `cfx_hart`、跳 `cg9 rc15`。spec/契约/ADR 的 `投递` 措辞随之清理。

12. **源 mask/ack 的写权限（用户 2026-11-26 选 B）**：按各 cfx 的 `<mode>_cfxreg` 两轴矩阵放行；**默认只 supv/hypv**，平台可按需把某个源开放给 user/jail；user 读 pending 不受限（RO）。

13. **源 mask 极性与复位（用户 2026-11-26 选 A）**：`1` = 屏蔽、**复位全 1**；`pending` 复位 0；`ack` 读 0、写 1 清位。内核 init 时按需放开源 mask。

14. **异步进入判定（用户 2026-11-26 选 A）**：逐源判定 `(pending & ~源mask) != 0` 且 monitor mask 的 `[源 cfxha] == 0` 且（timer 还要求 `ENABLE=1`）；同一边界所有可进入源**合并成一次进入**；`cg9 rc4` 的位 = **源 cfxha**（不含子事件），源内细节回源读 `pending`。
15. **timer 使能即检（用户选 A）**：`ENABLE` 0→1 时若 `cfx_time >= cmp`，立即置一次 `pending` bit0（之后不写新 `cmp` 不再置）。

16. **ack 容错（用户选 A）**：对 `pending=0` 的位写 ack = no-op；对保留位写 1 被忽略、不报错；访问不存在的 `rc` 才是 `CFXREG`。ack 可按位图整体写。

17. **版本（用户 2026-11-26 选 B）**：`DADAO-12`/`DADAO-22` 升 **`0.8.1-rc`**（`0.8.0` 已发布保持不动）；`contract-see` 同步 `0.8.1-rc`；`SimRISC` 不变（ISA 编码未动）。

18. **ADR（用户 2026-11-26 选 A）**：新立 **ADR-0064**「中断源 pending/mask/ack 归源、显式 W1C ack」，取代 `ADR-0061 D5`（mask 唯一归 monitor）与 `D6`（投递即清）；`ADR-0061 R3` 的出口帧继续有效。

19. **时序（用户 2026-11-26 选 A）**：`m18-linux-026` 先按 `0.8.0` 收口（出口帧/去 jmon）；本任务随后落地，再由 `m18-linux-027` 只改 ack/timer 寄存器。
20. **默认口径（用户 2026-11-26 部分订正）**：
   - DMA ack 前多次完成合并为 bit0（不计数）；
   - `cg16` 只在 `cfx_hart`/`cfx_pmem` 实现，其它 cfx 访问 ⇒ `CFXREG`；
   - **DMA `dma_ctrl.IRQ_EN` 位不保留**（从定义中删除；该位按保留位读 0/写忽略）；
   - **旧 timer `cg8 rc4/rc5` 归 reserved（访问 ⇒ `CFXREG`）**；
   - **`cfx_hart` 的异步捕获组由 `cg9` 改为 `cg15`**（`rc0`–`rc4`、`rc14`/`rc15` 编号不变）；
   - **monitor 的 `async_intr_mask` 由 `cg8 rc1` 改为 `cg15 rc3`**（umon/jmon/smon/hmon 四个模式行；`cg8 rc1` 归 reserved）；
   - `cg15 rc3` 位 = 源 cfxha；`cg9` 不再用于异步；
   - `cg9 rc4/rc5` 的“聚合”含义随之移到 `cg15 rc4/rc5`；`rc3 prev intr mask` 含义不变；
   - `escape` 语义不变，但 `rc11` 的写入目标改为目标模式 monitor 的 **`cg15 rc3`**。

## 待裁定（逐条讨论）

1. `ISTATUS` 置位条件：**到期边沿置位**（每个 armed deadline 只置一次，之后不重复）还是 `cmp<=now` 的持续电平？前者才使 ack 有意义。
2. `ENABLE=0` 是否清 `ISTATUS`，还是只 gate 投递？
3. ack 后未 re-arm（`cmp` 仍在过去）时，`ISTATUS` 是否立即重置（防风暴规则）。
4. DMA：ack 前再次 `DONE` 的合并/计数语义；`DONE` 与 `ERROR` 同时置位时的 ack 顺序；`BUSY=1` 时 ack 的处理。
5. ack 幂等：条件已消失/已 ack 时 W1C 是否 no-op（建议是，内核不得 die）。
6. ack 与 `pending` 的关系：投递仍清 pending；ack 只清源事件（或 ack 也清 pending 残留？）。
7. 内核侧改动面（`time.c` 的 ack 路径、`dadao_async_ack_sources`、K2 探针）。
8. QEMU/RTL/gem5/IDL 的同步任务与顺序；版本是否随 0.8.0（已定版）另起。

## 目标

1. **`DADAO-12`**
   - `cfx_hart`：异步捕获组由 `cg9` 移到 **`cg15`**（`rc0` prev mode / `rc1` prev cfx / `rc2` prev ip / `rc3` prev intr mask / `rc4` 本次源集合 / `rc5` 原始 pending 汇总 / `rc14` switch / `rc15` vector；`rc6`–`rc13` reserved）；删除 `cg9` 的异步用途（`cg9` 归 reserved/其它用途）。
   - 四个 monitor（umon/jmon/smon/hmon）：`async_intr_mask` 由 `cg8 rc1` 移到 **`cg15 rc3`**（64 位、位 = 源 cfxha、1 = 屏蔽、复位全 1）；`cg8 rc1` 归 reserved。
   - **`cfx_hart cg16`**：`rc0` timer ctrl（仅 bit0 `ENABLE`）、`rc1` timer cmp、`rc16` mask、`rc17` pending、`rc18` ack（W1C）；删除 `cg8 rc4/rc5` 的 timer 定义（归 reserved ⇒ `CFXREG`）。
   - **`cfx_pmem cg16`**：`rc16` mask、`rc17` pending、`rc18` ack；子事件合并 bit0（“传输结束”= `DONE|ERROR`）；`cg15` DMA 引擎寄存器中 **删除 `dma_ctrl.IRQ_EN`**（位按保留读 0/写忽略）。
   - **语义**：pending 事件置位、**ack 才清**、进入不清；mask 1=屏蔽、复位全 1；ack 幂等、保留位忽略；异步进入判定 = 逐源 `(pending & ~源mask) != 0` 且 monitor `cg15 rc3[源cfxha]==0` 且（timer `ENABLE=1`），多源合并一次进入；`cg15 rc4` = 源 cfxha 位集合，`rc5` = 原始 pending 汇总。
   - `escape` 语义不变，`rc11` 写入目标改为目标模式 monitor 的 **`cg15 rc3`**；`cg5 rc3`（prev intr mask）快照同一行。
   - **术语**：删除“投递/delivery pending/投递即清”提法，统一“事件 / 异步进入 / ack”。
   - `cg16` 仅在 `cfx_hart`/`cfx_pmem` 实现，其它 cfx 访问 ⇒ `CFXREG`。
2. **`DADAO-22`**：相关 SBI/示例（DMA、timer）按新寄存器与新 ack 口径同步。
3. **`contract-see`/`contract-syscall`/`contract-cfx-aliases`**：同步 `cg15`/`cg16` 布局、ack/mask/pending、术语；别名表/opcodes/legality 重生成（ISA 编码不变）。
4. **`ADR-0064`**：新立，取代 `ADR-0061 D5/D6`（mask 唯一归 monitor、投递即清）；`ADR-0061 R3` 出口帧继续有效。
5. **版本**：`DADAO-12`/`DADAO-22` → **`0.8.1-rc`**；`contract-see` 同步；`SimRISC` 不变。

## 验收

1. spec/契约门控：`check-spec-*`、`check-contracts-*`、`check-manifests-guard`、`check-cfx-aliases`/`-alias-table`、`check-opcodes-repro`、`check-legality-*`、`check-knowledge-refs` rc=0。
2. 全文一致性：`cg9` 无异步用途、`cg8 rc1` 无 mask 用途、`cg8 rc4/rc5` 无 timer 用途、`dma_ctrl.IRQ_EN` 0 处；“投递”措辞现行正文 0 处（历史变更记录可留）；`cg15 rc3`/`cg16 rc16-18` 在 `DADAO-12`/契约/别名表一致。
3. `escape rc11` 目标行改为 `cg15 rc3` 且 `cg5 rc3` 快照同步；`cg15 rc4/rc5` 聚合语义写清。
4. ADR-0064 落地并显式 supersede；版本三处一致（`0.8.1-rc`）。
5. 可达 FAIL ≥2 路（如把 `cg15 rc3` 写回 `cg8 rc1`、把 pending 改回“进入即清”）⇒ 一致性扫描红，`cp`+md5 还原。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动 spec/契约/ADR/索引 + 本任务书；不改实现组件/`tests/**`/`idl/**`。
3. 语义严格按「已确定」1–20，不自行扩展；`cp`+md5 还原。
4. **派发时机**：`m18-linux-026` 收口后再派（用户裁定 A）。
5. 术语「bank = 寄存器组」；完成区不写具体运行期路径。

## 完成区

**测试结果**：证据脚本 22/22（17 门控 + 38 文件扫描 + 4 路注入）；`check-arch-self-test` 恢复基线 `self-test: FAIL（2 项）`（`check_hart`/`check_pmem_dma`，两侧同因缺 llvm-mc）
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`、`spec/Kaiwu-测试机运行环境.md`、`spec/DADAO-23-HBI-超管系统二进制接口.md`、`spec/.manifests.toml`、`README.md`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`、`contracts/cfx-aliases.txt`、`.tao/adr/adr-0064-…md`（新增）、`.tao/adr/adr-0061-…md`（取代指针）、`tests/arch/common/check_mode_env.py`
**验收结果**：
- F1：`check_mode_env.py` L145 正则改为接受 `(?:cg8 rc1|cg15 rc3)`，**探针已随规范同步**、断言未删；注入 `cg16 rc3` ⇒ probe FAIL、`cp`+md5 还原 PASS；`check-arch-self-test` 由 3 项恢复 **2 项基线**（无新增 KNOWN-RED）。
- F2：Kaiwu L92（mask→`cg15 rc3`+`cg16`）、L108（删 `IRQ_EN`，改 `cg16` 中断面）、L148/L152（escape 目标→`cg15 rc3`）；DADAO-23 L25（`cg15`）、L26（`cg15 rc3`+`cg16`）、L53（`cg15`/`cg15 rc3`）；两册活正文 `cg8 rc1`/`cg9` 异步/`投递`/`IRQ_EN` 清零，manifests 重算。
- F3：扫描面扩至 38 文件（`spec/*.md` 23 + `.tao/contracts/*.md` 15，逐文件在变更记录截断），断言 **132** 条；补「`cg15 rc3` 复位全 1」「`cg16 rc18` W1C」断言；注入 ② 复位改 0、③ W1C→W0C 均转 FAIL，`cp`+md5 还原回绿。
- 门控：`check-spec-*`、`check-contracts-*`、`check-manifests-guard`、`check-cfx-aliases`/`-alias-table`、`check-opcodes-repro`、`check-legality-*`、`check-knowledge-refs` 全 rc=0；别名 1336 regs、opcodes 263 不变、三处 `0.8.1-rc`。
**新发现/坑**：`contract-see` 版本头含 `-rc` 时 `check_spec_drift` 走 ADR-sourced 分支；`cg8 rc1` 文本扫描须用 `(?!\d)` 排除 `cg8 rc10/rc11`；IDL-ISA/SimRISC-11 的旧口径由 `m18-idl-004` 覆盖，扫描以显式 known-red 名单排除。
**遗留问题**：KNOWN-RED（归波2）：QEMU/RTL/gem5/IDL 执行器、Linux 内核补丁、`check_hart`/`check_pmem_dma` 探针仍按 0.8.0 寄存器面；`check-arch-self-test` 的 2 项红为基线既有（缺 llvm-mc），非本任务引入。spec/契约活正文无遗留。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `cg5` 退出伪码仍写 `temp_monitor.cg8_rc1` | ✅已修 | 改为 `temp_monitor.cg15_rc3` | 全文 `cg8_rc1` 0 命中；证据脚本 rc=0 |
| 一致性扫描只查文本 `cg8 rc1`，表行 `\| 8 \| 1 \|` 注入假绿 | ✅已修 | 增加表行判据（`cg8 rc1` mask 行 / `cg8 rc4/5` timer 行 / `cg9` async 行） | 注入 1 转 FAIL、cp+md5 还原回绿 |
| `IRQ_EN` 在历史变更记录与新说明中残留 | ✅已修 | 两册全文清零（保留“bit2 保留”表述） | `grep -c IRQ_EN` 两册 = 0；扫描 rc=0 |
| `dma_ctrl` bit2 读回/写忽略口径未写全 | ✅已修 | §4.9 表与段补“读 0/写忽略” | 门控 + 扫描 rc=0 |
| DADAO-22 `SBI_HART_SET_TIMER` 未体现 `cg16 rc0/rc1/mask` | ✅已修 | 说明补 `ENABLE`/cmp/mask 口径；示例注释同步 | 门控 + 扫描 rc=0 |
| `timer_mask` 复位全 1 与“SBI 示例直接可用”存在易误读 | ⏸延后 | 不改语义（用户已定复位全 1）；由内核 init 清 mask | 任务书「已确定 13」；§4.7/§5.4 已写清 |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 本人执行，workdir = 任务 worktree，提交 `c342c3f0`）**
- 仓库根执行运行期证据目录内的 `run.sh`（默认注入）：17 项门控（`check-spec-{drift,numbering,changelog,refs,purity,cite-targets,codeblocks}`、`check-contracts-{dir,pending}`、`check-contract-relocs`、`check-manifests-guard`、`check-cfx-aliases`、`check-cfx-alias-table`、`check-opcodes-repro`、`check-legality-{drift,invariants}`、`check-knowledge-refs`）逐项 `rc=0` + `PASS consistency scan rc=0` + 2 路注入「红→cp+md5 回绿」⇒ `── summary: pass=20 fail=0 ──`、`EXIT=0`。
- `make -k check` @ `c342c3f0` 与 @ 基线 `a362345b`（干净检出）逐段 diff：失败集 = isa-coverage / arch-self-test / syscall-abi / milestones-fresh / width-sizes / components / interface / linux-toolchain / writer-guards / temp-dirs；**除 `check-arch-self-test` 外逐段相同**（isa-coverage 两侧同为缺 llvm-mc；syscall-abi/width-sizes/components/linux-toolchain 同为缺工具链；milestones-fresh 9 项、writer-guards `W5b`、temp-dirs 6 项、interface `294≠309` 两侧一致）；`check-knowledge-refs` 基线红（`ADR-0064` 悬空 2）→ 本任务转绿。
- `check-arch-self-test`：基线 `self-test: FAIL（2 项）` → 现 `FAIL（3 项）`；新增 `tests/arch/common/check_mode_env.py`，其 L145 正则要求 `contract-see §3` 含「`cfx0`–`cfx3` 的 `cg8 rc1`（异步来源掩码）初值全 1」，本任务把该句改成 `cg15 rc3` ⇒ 失配；另 2 项（`check_hart`/`check_pmem_dma`）两侧同为缺 llvm-mc。
- 独立注入 3 路（各 `cp` 备份 + md5 前后校验、恢复后 md5 相等、回绿）：① `escape rc11` 目标句 `cg15 rc3`→`cg8 rc1` ⇒ `SKIP_GATES=1 INJECT=0` 跑 `run.sh` **EXIT=1**（marker 缺失）；② `cg15 rc3` 复位 `全1`→`0` ⇒ **EXIT=0 不红**；③ `cg16 rc18` ack `W1C`→`W0C` ⇒ **EXIT=0 不红**。
- 38 文件现场枚举（`spec/*.md` ∪ `.tao/contracts/*.md`、逐文件在变更记录处截断）：`IRQ_EN` 1 = `spec/Kaiwu` L108；现行正文「投递」4 = Kaiwu L108、`DADAO-23` L25/L26、`IDL-ISA` L354；`cg8 rc1` 掩码/escape 目标 7 = Kaiwu L92/L148/L152、DADAO-23 L26/L53、IDL-ISA L312/L354、`SimRISC-11` L86；`cg9` 异步 5 = DADAO-23 L25/L53、IDL-ISA L350/L353/L357（`Toolchain-01`/`contract-asm`/`contract-isa` 的 `cg9` 帧选择位属 `m18-spec-007` 已披露的旧 escape 语法，不计）。
- 范围：`git show --name-only c342c3f0` 与完成区声明 10 文件逐字一致；`components/**`/`tests/**`/`idl/**` 命中 0；`git ls-remote --heads origin m18-spec-008` 空（未 push）；开工/收尾 `git status --porcelain -uall` 均空，9 个交付文件 md5 与开工值逐个相等（仅本任务书因本记录改动）；状态 `待验收`；完成区 11 行 ≤30。
- 版本/别名/编码：三处 `0.8.1-rc`；`git diff a362345b..HEAD -- spec/SimRISC*` 空、`contracts/opcodes.yaml` 未动（263 条）；别名表 1336 regs（专有 52）与 `gen_cfx_alias_table` 现场输出一致。

**约束核验**：硬约束 1–5 全守（独立 worktree、未提交未推送、只动 spec/契约/ADR/索引+本任务书、`cp`+md5 还原、无运行期路径入文、术语「寄存器组」）。验收 1/3/4/5/6 我方重跑通过：`cg15 rc0–rc5/rc14/rc15` + `rc6–rc13` reserved、`cg9` 正文无异步用途；四 monitor `cg15 rc3` 64 位/位=源 cfxha/1=屏蔽/复位全 1、`cg8 rc1` 归 reserved、`escape rc11`→`cg15 rc3`、`cg5 rc3` 快照同步、§5.4 逐源求值；`cfx_hart cg16` rc0 仅 ENABLE/rc1 cmp/rc16/17/18、`cfx_pmem cg16` bit0 = `DONE|ERROR`、两册 `IRQ_EN` 0 处、`cg8 rc4/rc5` reserved；pending 事件置位/ack 才清/进入不清、ack 幂等保留位忽略、多源合并、`cg15 rc4/rc5` 聚合、使能即检、DMA ack 只清 pending；ADR-0064 D1–D8 逐条对应已确定 1–20 并显式 supersede `ADR-0061` D5/D6、`ADR-0061` 状态行有指针；`contract-syscall` 无旧口径残留。

**判决：Needs Revision**
- **F1（阻断·门控/退出码）**：`make check` 与基线**不逐行相同**且新增红未登记——`check-arch-self-test` 2→3 项（`check_mode_env`，根因本任务改 `contract-see`），完成区「遗留问题」未点名、`issues-m18.yaml` 中 `grep -c "ADR-0064\|m18-spec-008"` = 0 ⇒ 违反 AGENTS.md §4「失败须登记 KNOWN-RED + issue」（同模块 `m18-spec-005` 验收 5 即「`make check` 与基线逐行相同」）。改法：完成区补该 KNOWN-RED（基线 2→现 3、探针名、根因、归 `m18-testcases-005`）+ 登记 issue 或写明由 architect 收尾登记；`tests/**` 超本任务硬约束，不要求本任务改探针。
- **F2（阻断·语义）**：验收 2「全文一致性」按 `m18-spec-004` 复审确立的 38 文件口径不成立——`spec/Kaiwu` 4 行（含指导软件使用**已删除**的 `IRQ_EN`、把掩码写到**已 reserved** 的 `cg8 rc1`）与 `spec/DADAO-23` 3 行（`cg9` 捕获、`cg8 rc1` 掩码与 escape 目标、投递）现行正文与 `DADAO-12` 新口径直接矛盾；**两册无任何后续任务覆盖、完成区零披露、issue 零登记**（IDL-ISA/SimRISC-11 已由 `m18-idl-004` 覆盖，须写明）。改法二选一：本任务内改两册活正文并重算 manifests（硬约束 2 允许面内），或完成区逐条枚举行号 + 登记 issue/后续任务（`m18-spec-004` F3 模式）。
- **F3（随修·证据脚本）**：`run.sh` 扫描面仅 5 文件（先例 38 文件、断言 ≥30），且验收 4 的「`cg15 rc3` 复位全 1」「`rc18` W1C」两维度无断言（注入 ②③ 不红）⇒ 扩扫描面 + 补两条可达 FAIL 断言并注入回绿。

### 第 2 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `check_mode_env` 仍断言 `cg8 rc1` 位置 | ✅已修 | L145 正则接受 `(?:cg8 rc1|cg15 rc3)`，断言保留 | 注入 `cg16 rc3` ⇒ probe FAIL、cp+md5 还原 PASS；`check-arch-self-test` 2 项基线 |
| F2 Kaiwu/DADAO-23 活正文旧口径 | ✅已修 | Kaiwu L92/108/148/152；DADAO-23 L25/26/53 改 `cg15`/`cg15 rc3`/`cg16`，删 `IRQ_EN` | 38 文件扫描 0 残留（IDL-ISA/SimRISC-11 按 known-red 排除）；manifests 重算 |
| F3 扫描面/断言不足 | ✅已修 | 扫描 38 文件、断言 132；补复位全 1 与 W1C 断言 | 注入 ②复位 0、③W1C→W0C 均 FAIL，cp+md5 还原回绿；证据 22/22 |

### 第 2 轮 reviewer 验收

**重跑记录（reviewer 本人执行，workdir = 任务 worktree，提交 `43dfc3fe`）**
- **F1**：`python3 tests/arch/common/check_mode_env.py --selfcheck` ⇒ `selfcheck PASS`、EXIT=0；`make check-arch-self-test` ⇒ `self-test: FAIL（2 项）`（`arch/hart/check_hart.py`、`arch/pmem/check_pmem_dma.py`，与基线同因缺 llvm-mc）= 基线。断言未删、非恒真：独立注入（`contract-see` 初值句 `全1`→`全0`）⇒ probe **EXIT=1**「缺 cg15 rc3 异步来源掩码初值句」，`cp`+md5 还原 ⇒ EXIT=0。**判定：改探针可替代上轮「登记 KNOWN-RED + issue」**——根因（探针钉旧位置）被消除、`tests/arch/common/check_mode_env.py` 为已授权扩围的单点文件、断言保留且可达 FAIL；登记仅在无法改根因时才必要。
- **F2**：`git show 43dfc3fe` 逐行核：Kaiwu L92（mask→`cg15 rc3` + 源侧 `cg16 rc16/17/18`）、L108（删 `IRQ_EN` 指导→`cg16` 中断面、删「投递」）、L148/L152（escape 目标→`cg15 rc3`）；DADAO-23 L25/L26/L53（`cg9`→`cg15`、`cg8 rc1`→`cg15 rc3`、补 `cg16` 复位口径、删「投递」）。reviewer 独立 38 文件正文统计：`IRQ_EN`=0；`投递` 仅 `IDL-ISA` L354（known-red）；两册正文 `投递/IRQ_EN/cg8 rc1/cg9` 命中全 0。`sha256sum` 我方重算 Kaiwu/DADAO-23 = 清单登记值，`check-manifests-guard` rc=0。
- **F3**：`run.sh` 打印 `scan files=38 (spec=23, contracts=15) assertions=131` + 计数断言 ⇒ `CONSISTENCY: PASS (assertions=132)` ≥30；`summary: pass=22 fail=0`、`EXIT=0`（17 门控逐项 rc=0，含 `check-cfx-alias-table`/`check-opcodes-repro`/`check-knowledge-refs`）；4 路内置注入均红→`cp`+md5 回绿。**注入 ②（复位 `全1`→`0`）③（`W1C`→`W0C`）reviewer 单独重跑**：均 `EXIT=1`（上轮同两路为 EXIT=0），还原 md5 相等、回绿 `EXIT=0`。
- **自设注入（新角度）**：Kaiwu L92 回写 `cg15 rc3`→`cg8 rc1` ⇒ `SKIP_GATES=1 INJECT=0` 跑 `run.sh` **EXIT=1**（`cg8 rc1 still used as mask`）⇒ `cp`+md5 还原 ⇒ EXIT=0（`assertions=132`）。
- **范围**：`git show --name-only 43dfc3fe` = 5 文件（任务书、`spec/Kaiwu-测试机运行环境.md`、`spec/DADAO-23-HBI-超管系统二进制接口.md`、`spec/.manifests.toml`、`tests/arch/common/check_mode_env.py`），与完成区声明一致（任务书为隐含项，同第 1 轮口径）；无 `components/**`/`idl/**`/内核/其它 `tests/**`；`git ls-remote --heads origin m18-spec-008` 空（未 push）；注入前后 `git status --porcelain -uall` 均空；状态 `待验收`。
- **`make -k check` @`43dfc3fe` vs 基线失败集**：`diff` ⇒ **IDENTICAL（10 项：isa-coverage / arch-self-test / syscall-abi / milestones-fresh / width-sizes / components / interface / linux-toolchain / writer-guards / temp-dirs）**，无新增红；`check-arch-self-test` 段 = 基线 2 项；`check-knowledge-refs` PASS（0 悬空、0 具体 `.work/**` 引用）。

**约束核验**：硬约束 1–5 守（本轮扩围 `tests/arch/common/check_mode_env.py` 已由主会话授权、单点、断言未弱化、未动实现/IDL/内核）；`cp`+md5 还原全绿；完成区 ≤30 行、无运行期路径入文；第 1 轮审阅记录未被改写。

**观察（不阻断）**：① `check_mode_env.py` L145 用 `(?:cg8 rc1|cg15 rc3)` 容忍旧写法，单看可放过「回退到 `cg8 rc1`」，但 `run.sh` §2.5 另有钉死 `cg15 rc3` 的专句断言（可达 FAIL），整体仍守；② 完成区「修改文件」未列任务书本身（与第 1 轮一致，属隐含项）。

**判决：Accepted**
