# m18-qemu-004: QEMU hart-first 异步仲裁（cfx_hart cg9）

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-002`（spec/契约 hart-first）合入；`m16-qemu-003` 已合入；`m18-llvm-001`（汇编器支持 `escape ..., 8`/cg9）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

`ADR-0060` 取代 `ADR-0059`：异步投递统一 **hart-first**——所有异步源（TIMER=`1<<17`、PMEM_DMA=`1<<18`）投 **`cfx_hart`（cfxha 15）** 的 supv 单向量；现场/mask/pending 在新增 **`cfx_hart cg9`**（16 rc）。`m18-qemu-002`（monitor-first）**不合入**、留参考分支；本任务对照它的仲裁/补投骨架，改目标为 `cfx_hart cg9`。

## 要做

1. **仲裁目标**：`dadao_async_arbitrate()` 投递目标 = `cfx_hart`（cfxha 15），入口 = supv 单向量（`cg9 rc6 async_excp_vector`、`rc7=2`）；不再按当前模式 monitor。
2. **cg9 现场**：进入时写 `async_prev_run_mode`/`prev_cfx_code`/`cause_ip`/`cause_id`；保存 `async_global_intr_mask` 到 `saved_global_intr_mask` 并置全 1。
3. **mask/pending**：五个 mask 在 `cg9 rc8–rc12`（位=源 cfxha 15/32）；`async_pending` 在 `rc5`（位=**cause id** `1<<17`/`1<<18`）；屏蔽时置 pending、不进入；同源 OR；写 0 清位。
4. **无嵌套/释放/重建**：`async_cause_id != 0` 时新事件只置 pending；软件写 0 释放帧、清 pending；可快照/重建。
5. **escape frame selector**：`imms18` 合法集 `{0,1,2}`（0/1=cg5 0/+4，2=cg9 0，3⇒ILLI）；`imms18[17:2]` SBZ；`cfxha`=当前 cfx；cg9 恢复 `prev_*` 与 `saved_global_intr_mask`。
6. **cause 常量**：`DADAO_CAUSE_TIMER=1<<17`、`DADAO_CAUSE_PMEM_DMA=1<<18`；`dadao_cause_check` 的 `[31:16]` 放行 17/18。
7. **探针/归档**：`min_rom_probe_integ051t`、K2/K5 异步探针、`tests/arch/vast-arch-inventory.md` 改 hart-first（cause 17/18、pending cg9、mask 位源 cfxha）。
8. **不回归**：M16 cfx5/cache 代表集；`check-patch-tree` qemu 段 0 problem。

## 不做

- 不改 `spec/`/契约（由 `m18-spec-002`）；
- 不做 monitor-first（ADR-0059 作废）；
- 不改 kernel/RTL/gem5；
- 不改版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. TIMER/PMEM_DMA 都投 `cfx_hart` supv；`cg9 rc0–rc4` 现场逐项；mask 位 15/32；pending 位 `1<<17`/`1<<18`；
2. 屏蔽→pending 保留→解除补投；`cause_id != 0` 不嵌套；写 0 释放后不再进入；
3. `escape imms18=2` 恢复 cg9；`3` ⇒ `ILLI`；`imms18[17:2]≠0` ⇒ `ILLI`；
4. **可达 FAIL ≥3 路**（`cp`+md5 还原 + 重建）：① 投 monitor；② pending 记 cfxha 位；③ escape 选错帧；
5. 不回归：M16 cfx5/cache 代表集、`check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs`；
6. `--inject` ≥3 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **16/16 PASS rc=0**；`run.sh --inject` **12/12 PASS rc=0**（3 路注入：投 monitor / pending 记 cfxha 位 / escape 选错帧；均 `cp`+md5 还原→重建→回绿）。`min_rom_probe_integ051t.py` **13/13**（doc 12 + structure 15 子项归并计 2 项、runtime 11 例）；cg9 现场、mask 位 15/32 vs pending 位 17/18、无嵌套/释放补投、escape 2/3/SBZ 全覆盖。
**修改文件**（9）：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/changelog.md`、`tests/arch/vast-arch-inventory.md`、`tests/unit/linux/{k2_irq_probe,k2_time_probe}.py`（仅 cause 语义/文档）、`tools/testcases/arch/min_rom_probe_integ051t.py`、本任务书。未改 `spec/`/`.tao/contracts/`/`Makefile`/`components/{linux,musl,busybox}`；未升版本号；未提交 git。
**验收结果**（真实 rc）：`make build-qemu JOBS=32` **0**；`make_patch.py qemu` **0**，二次运行 3 份补丁 md5 不变；`check-patch-tree` **qemu 69 patch / 0 problem、整跑 0**；`check-component-changelog` 0、`check-knowledge-refs` 0；M16 代表集：`run_arch --level smoke` **10/10**、`min_rom_probe_046t` **25/25**、`carrier_tlb` **29/29**、`min_rom_probe_integ042t --only cfx5_cache_noop` PASS、`check_cfx5_regs --self-test` PASS；`make check` rc=2，首个失败目标 = 基线 `check-milestones-fresh`（共享台账并发编辑，非本任务文件；基线/本树同目标），其余门控均绿。
**新发现/坑**：① `cfx2rc` 的 cg9 分支早退会跳过通用写尾的 `dadao_async_kick` ⇒ 放宽 mask/写 0 释放帧后不补投（探针 4 例红后才暴露），已在分支内显式重踢。② `ld_o` 的 imm12 有符号且只 12 位，状态块偏移靠 `& 0xFFF` 落到低地址（沿用旧探针口径，所有状态偏移 <0x80）。③ 同一向量既收 PMEM 又收后续 TIMER 时，frame handler 会把自己当首帧再 arm 一次 ⇒ 释放帧前软件须把 `cg9 rc6` 指回普通 handler（探针按此模拟）。④ 基线 `make check` 在共享台账文件上随其它会话变化（本次先后出现 `m16-chipyard-021`/`m16-testcases-012` 两条），证据按「首个失败目标相同」比对并注明。
**遗留问题**：① **K2 irq/time 内核镜像仍是 monitor-first**（`cfx_smon cg2 rc4` 旋钮、monitor 向量），本任务只按范围订正 TIMER cause 文档；QEMU 改 hart-first 后两门控将红，待 kernel hart-first 任务（`components/linux` 不在本任务范围）。② `min_rom_probe_integ042t` 的 `pmem_dma_irq_delivered`/`pmem_dma_masked_pending` 仍断言 target-first（`cfx_pmem cg5 rc5 1<<8`）⇒ KNOWN-RED，路径不在本任务允许集，需 testcases 迁 hart-first。③ RTL/gem5（`m18-chipyard-001` 等）与 `m18-testcases-002` 的 escape 向量待后续。④ `m16-testcases-012` 台账「待开始但有 worktree」为并发会话状态，非本任务改动。⑤ `tools/testcases/arch/README.md` 的 integ051t 摘要仍是旧 target-first 口径（该路径不在任务允许集，未改，建议随 testcases 迁移任务同步）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（深度 1，无嵌套子代理）：`dadao_async_enter` 的 mask/帧/pending/现场/切换顺序与 §5.2(四) 逐步对照；`dadao_async_arbitrate` 单层/升序/失败保留 pending；TIMER/DMA 事件与 cmp/ctrl 写；cg9 寄存器宽度与 4B 对齐落盘、rc13–15 CFXREG；escape 编码/帧/恢复三支；宏 cause 校验；user 构建的 `#ifndef` 边界；探针每条断言的 FAIL 可达性与注入锚点唯一性。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 cg9 写分支早退跳过 `dadao_async_kick` ⇒ mask 放宽/释放帧后不补投 | ✅已修 | `helper_cfx2rc` cg9 分支内加 `dadao_async_kick` | 4 例由红转绿；13/13 |
| F2 frame 探针把后续 TIMER 也送进 frame handler ⇒ 0x71 自嵌套假红 | ✅已修 | 释放帧前写 `cg9 rc6` 回主 handler | `no_nest_frame` PASS |
| F3 探针 mask 相位把「位=1 屏蔽」写成反义 ⇒ phase1 假红 | ✅已修 | phase1 用 bit15 开放/bit17 屏蔽，phase2 反之 | `mask_index_source` PASS |
| F4 ILLI/CFXREG 用例缺 smon supv 向量与 deleg | ✅已修 | bootstrap 写 smon `cg2 rc10`、hart/smon `cg3 rc12=0x8` | `escape_ill`/`cg9_reserved` PASS |
| F5 证据脚本把 `[PASS]` 全部计入 runtime 数（40≠13） | ✅已修 | 只数 `^PASS `（11）+ 汇总行 13/13 | `run.sh` 16/16 |
| F6 `make check` 逐行比对受共享台账并发编辑影响 | ✅已修 | 改比「首个失败目标」+ baseline 说明；全绿时直接判绿 | 基线/本树均 `check-milestones-fresh` |
| F7 `cause_ip` 落盘未显式 48 位掩码 | ✅已修 | `& 0x0000FFFFFFFFFFFF & ~3` | 重建 + 13/13 |

**约束核验**：`git status` = 8 文件 + 本任务书；组件源树干净且 `base..HEAD` 恰 1 commit；未改 `spec/`/契约/Makefile/linux|musl|busybox；未升版本号；注入全程 `cp`+md5（无 `git checkout/restore/stash`）；临时目录 `~/.local/share/opencode/worktree/...` 与 `/tmp/opencode/m18-qemu-004/`；构建 `JOBS=32`；术语「寄存器组」。
**判决**：**待验收**（F1–F7 已修；遗留 ①–④ 登记）。

### 第 1 轮 reviewer 验收（独立重跑，非采信完成区）

**重跑记录**（仓库根执行；证据 = 运行期证据目录内 `run.sh`）
1. `./run.sh` → `16 passed, 0 failed`、退出码 **0**（审查前一次、注入还原后一次，输出一致）。
2. `./run.sh --inject` → `12 passed, 0 failed`、退出码 **0**；三路逐条 `applied → red rc=1 → cp+md5 还原 → green rc=0`（inj1 投 monitor / inj2 pending 记 cfxha 位 / inj3 escape 选错帧）。
3. **自设第 4 路注入（未列）**：cg9 入口 `switch_run_mode` 改恒 hypv（锚点 1 处）→ `make build-qemu JOBS=32` rc=0 → `./run.sh` **9 passed / 7 failed、退出码 1**（`integ051t runtime 9/11`，红例 `escape_ill`、`cg9_reserved` exit=126=0x7E poison；summary/E1/patch export/check-patch-tree/首红目标一并红）→ `cp` 还原 + md5 `1f26d82d…` 相等 → 重建 rc=0 → `./run.sh` **16/16、退出码 0**。
4. 环境插曲：首跑构建因系统临时分区（tmpfs 16 G）被并发会话打满报 `No space left on device`，空间恢复后重跑成功（第 1/3 次）——环境干扰，非交付物缺陷。
5. `make check` 本树 vs 基线日志**逐行 diff**：仅台账行数与 VIOLATION（`m16-testcases-012`、`m16-testcases-018`、`m16-chipyard-021`）及 make 目录行不同，首红同为 `check-milestones-fresh`；**主仓 master（无本任务改动）单跑 `make check-milestones-fresh` rc=2、同样 5 条 VIOLATION** ⇒ 同因、不属本任务。
6. `integ051t --doc`：doc 0 failed、structure 0 failed（子项 **16 + 13**）。快照：审查前后 `git status --porcelain -uall` 均空、9 文件 md5 与派单快照逐一相同、`master...HEAD` 恰 9 路径。

**约束核验（逐条）**
1. **投递**：`timer_frame_hart`/`pmem_frame_hart` 断 cause `1<<17`/`1<<18`、prev hypv/hmon、源 cfx 与 monitor `excp_async_num=0`、入口 = cg9 rc6、`cg9_reset_defaults` 断 rc7=2；与 spec §3.9/§5.2(三)(四)/§5.3 逐条对齐（escape 不清 cause_id、释放须在 escape 之前均一致）。
2. **mask/pending**：rc8–rc12 复位全 1、位 = 源 cfxha（`mask_index_source` 三相、`mode_mask_row`、`pending_or_order` 只认 17/18 不认 15、`dedup_same_source` 同源 OR）；`release_reenter` 写 0 释放→静默→再入；`no_nest_frame` 无嵌套且释放后补投。
3. **escape**：`escape_ill`（imms18=3 与 `[17:2]`≠0 ⇒ ILLI×2）、`cg9_reserved`（rc13/rc15 ⇒ CFXREG×2）、恢复 prev_*/cause_ip/saved mask 均有断言。
4. **证据**：16/16、12/12、三路可达 FAIL、`cp`+md5 还原重建回绿（上列为本人真实输出与退出码）。
5. **M16 回归**：smoke 10、046t 25、carrier 29、integ042t `--only cfx5_cache_noop`、`check_cfx5_regs --self-test` 全 PASS；`check-patch-tree` qemu 69 patch / 0 problem、整跑 0。
6. **范围**：9 路径与完成区一致；无 `spec/`/`.tao/contracts/`/`Makefile`/`components/{linux,musl,busybox}` 改动；`make_patch.py qemu` 幂等（md5 不变）；完成区 7 行 ≤30；状态 `待验收`；未提交 git。
7. **门控**：`make check` 首红 = 基线同目标，且 master 单跑同红（见 5）。
8. **遗留承接**：①K2/K5 旧镜像→`m18-linux-021`（其验收 6 明写「旧镜像必红、由红转绿」）；②integ042t pmem 两断言→`m18-testcases-001`（明列）；③RTL/gem5→`m18-chipyard-001`/`m18-gem5-001`；④escape 向量→`m18-testcases-002`；⑤README 旧摘要→`m18-testcases-001`。完成区均已披露。

**finding（文档/覆盖级，不阻断，交 architect 收尾处理）**
- F1 完成区「doc 12 + structure 15 子项」实测为 **16 + 13**（数字笔误，非门控读数）。
- F2 本任务书「约束核验」句写了家目录与临时目录绝对路径，违反「任务书不写运行期路径」；`check-knowledge-refs` 只拦「被引运行期材料悬空」故未拦 ⇒ 收尾删改措辞。
- F3 `cg9 rc9/rc10`（user/jail 行）只有复位读断言，缺写入/行为用例（rc8/rc11/rc12 已覆盖）。
- F4 按复位语义推断（未实测 L2，需内核构建、超 60 min 档）：五 mask 复位全 1、rc6 复位 0 而旧内核不写 cg9 ⇒ 异步根本不投递，`check-linux-k2`/K5 时钟例**将红**，与完成区披露一致；`/complete` 前必须先落 `m18-linux-021`。

**判决：Accepted**（8 项核验在本人重跑下全部通过；F1–F4 记档不阻断，由 architect 收尾处理）。
