**追加（m18-spec-009）**：保持 `当前模式 ≤ cg15 rc14` 的进入上限（继承自 002）。

# m18-chipyard-003: RTL 每源 pending/mask/ack（cg15/cg16）

**模块**：chipyard
**项目里程碑**：M18
**依赖**：`m18-spec-008`、`m18-testcases-005`；等 M16 chipyard 写者窗口
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（RTL 异步源）
**状态**：已验证

## 目标

按 `m18-spec-008`：异步捕获 `cg9`→`cg15`；monitor mask `cg8 rc1`→`cg15 rc3`；timer `cfx_hart cg16 rc0/rc1/rc16/17/18`；DMA `cfx_pmem cg16 rc16/17/18`、删除 `IRQ_EN`；pending ack 才清；进入判定按源 + monitor mask + ENABLE；`cg15 rc4/rc5` 聚合；`escape rc11` 写 `cg15 rc3`。

## 验收

1. `make verilog` + sim rc=0；`m18-testcases-005` 可跑项在 Vast 上通过；与 QEMU 同 ELF 签名一致（不一致登记 `expected-divergences.yaml`）。
2. 可达 FAIL ≥2（恢复 cg9 / pending 进入即清），`cp`+md5 还原重建回绿。
3. 不回归 M16 cfx/cache 代表集；`check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
4. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

独立 worktree；不提交 git；只动 `components/chipyard/**`、`tests/arch/**`、`expected-divergences.yaml`、本任务书；不改其它实现/spec/契约/Makefile；`make_patch.py chipyard`；`cp`+md5。

## 完成区

**测试结果**：运行期证据目录 `run.sh --base` = 38/38、EXIT=0（门控 + Vast/Tiny 构建 + 四组向量 + escalation 探针 + Tiny 基线 + 寄存器面自检）；`run.sh --inject` = 14/14、EXIT=0（注入 A/B 真重建后红、`cp`+md5 还原重建回绿）。
**修改文件**：`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`、`.../dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingParams,WumingPmem}.scala.patch`、`components/chipyard/changelog.md`；`tests/arch/{hart/{README.md,escape_escalation.S},pmem/{pmem.S,check_pmem.py,README.md},vast-arch-inventory.md,expected-divergences.yaml}`；本任务书。
**验收结果**：
- Vast/Tiny `make verilog` + Verilator rc=0、`%Error`=0；sim md5 Vast `e46730f9…`（基准构建）/`b5b2dae0…`（注入还原后重建，Verilator 不逐位复现）、Tiny `265181f1…`。
- Vast 向量：`arch-hart-002` smon/umon 各 38 槽 PASS；`arch-hart-001` hmon 124 槽仅 `DIV-17` 的槽 1/7（actual 63 vs expected 3）；`arch-pmem-001` hmon 48 槽、`arch-pmem-002` smon/umon 各 10 槽 PASS（同 ELF、同一独立 oracle；0.8.1 QEMU 二进制不在本 worktree，QEMU 侧同 oracle 由 `m18-testcases-005` 验收）。
- 寄存器面/语义：`check_hart_rtl --selfcheck`、`check_pmem --self-test`（mode 3/2/0）、`check_escape_rtl`（SYS_EXIT 0）、`run_arch --self-test` rc=0。
- 注入 A（进入即清 pending）⇒ `arch-hart-002/smon` 槽 07/20 红（expected 0x8000 actual 0）；注入 B（删 `runMode <= cg15 rc14`）⇒ `arch-hart-001` 命中 `rc14_bad_entry` 哨兵 `0xBAD0C14`（槽 101/102）；还原后源码 md5 `ec9d2205…`、重建回绿。
- Tiny 不回归：`11-cfx` 4/5（`escape_ciii` = `DIV-18`）、`01-load-store` 38/38。
- 门控：`check-patch-tree` chipyard 段 **0 problem**、`--source-state` chipyard OK；`check-component-changelog`/`check-knowledge-refs`/`check-tests-index`/`check-index-blobs`/`check-arch-self-test` rc=0。
- `make -k check` = EXIT 2，红项 6：`check-patch-tree`（qemu/gem5/musl 既有漂移，chipyard 0）/`check-interface`（294≠309）/`check-milestones-fresh`（台账待主会话）/`check-musl-freshness`/`check-run-artifacts`（运行期日志目录既有命名）/`check-temp-dirs`（W2），均基线与本任务无关。
- `DIV-17` 保留（Vast BootROM 仍以 cfx_power 交付测试体，本任务不改交付链）；`DIV-18` 保留（Tiny 无异步模型/`cg15`，且硬约束不含 `tests/inst`）。
**新发现/坑**：源 pending 粘滞后若无 kick，会在 handler ack 前每个边界重入 ⇒ RTL 必须与 QEMU/gem5 同加一次性 `asyncKick`（进入清除，源事件/可放行写置位）；`intr.valid` 不得由 `wEn`/`escape.valid` 组合驱动（FIRRTL 组合环，`pmemEvent`/`kickWrite`/`escapeKick` 各寄存一拍）。`cfx0`–`cfx3` 与 `cfx_hart` 的 `cg15 rc3` 同 rc，按 cfxha 区分。`cg15 rc5` 是实时汇总、不能做成寄存器（进入不清）。
**遗留问题**：`pmem.S` 运行期逐槽未跑（多 KiB DMA 经 DRAMSim，>15 min/模式），证据只含三分支编译 + `check_pmem --self-test`，语义面由索引载体 `arch-pmem-001/002` 承担。共享源树现为 003 状态（base+1、干净）；`m18-chipyard-002` reviewer 重跑前须先重放 002 的 patch 集。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `GewuFile`（`cg15`/`cg16` 行解码与读写集、monitor `cg15 rc3`、timer 边沿/使能即检、DMA 事件与 ack、`asyncKick`/组合环、`cg15 rc4/rc5`）、`WumingCore/WumingParams/WumingPmem`（仅注释同步）、`pmem.S`/`check_pmem.py`（槽序与期望）与 patch 导出。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 每次进入后 `hartKickWrite` 仍高，同拍把 kick 重新置位 ⇒ handler ack 前二次进入（prev_cfx=hart、async_num 翻倍） | ✅已修 | 进入同拍只由 `timerEvent`/`pmemEvent` 重 arm，不让致因写重 arm | smon/umon 38/38 PASS |
| F2 `intr.valid` 组合依赖 `io.wEn`/`escape.valid` ⇒ FIRRTL 组合环 | ✅已修 | `pmemEvent`、`hartKickWrite`、`escapeKick` 各 `RegNext` 一拍 | `make verilog` rc=0、无 CheckCombLoops 错误 |
| F3 旧 `asyncSrcPending` 寄存器成为死代码 | ✅已修 | 删除，`cg15 rc5` 改为实时 `pendingSummary` | 编译 + 槽 07/20 断言 |
| F4 `pmem.S` 仍是 pre-R3（旧 `escape cfx, [ip,4]`/`cg3 rc8`/`cg9`/`IRQ_EN`） | ✅已修（运行期未跑） | 迁到 `cg15`/`cg16`/`cg15 rc3`/`ESCAPE_SKIP4`，槽 87/9 与 `check_pmem` 同步 | 三分支编译 rc=0；`check_pmem --self-test` 3/3 PASS；长仿真未跑（遗留） |
| F5 QEMU 0.8.1 原始签名不可得 | ⏸延后 | 不改判据；RTL 过同一独立 oracle + 登记 expected 比较 | `run_arch --self-test`、四组向量 |
| F6 `make_patch` 后 patch 是否自洽 | ✅已修 | 源树 amend 为 base+1 后导出 4 份 patch | `make_patch` 幂等（md5 不变）、chipyard 0 problem |

判决：所有可修 finding 已修；状态对账为「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（仓库根执行运行期证据目录内的 `run.sh`）**
- `--base` ⇒ `summary: 32/32 checks passed, 0 failed`、EXIT=0；`--inject` ⇒ `summary: 14/14 checks passed, 0 failed`、EXIT=0。
- 注入 A（进入即清 pending）真红：`slot 07 async src_pending after entry ... expected 0x8000 actual 0`（slot 20 同）；注入 B（删 `runMode <= cg15 rc14`）真红 rc=1：`slot 101 async rc14=0 ... actual 0xbad0c14`；两路均 `cp`+md5 还原（`ec9d2205…`）重建回绿、共享源树 `git status` 空、HEAD `564fbcd`。
- 审查者自设注入 C（把 `escape` 的 `rc11` 整字写改成写当前 monitor mask）⇒ `arch-hart-002/smon` rc=1：`slot 11 escape rc11 whole word ... expected 0x0123456789abcdef actual 0xffffffffffff7fff`；`cp`+md5 还原（与备份逐字节相等）重建 ⇒ `PASS arch-hart-002/smon（38 槽）` rc=0、Vast sim md5 `e46730f9…` 与完成区一致、源树干净。
- 向量：`arch-hart-001` 124 槽仅 `DIV-17` 槽 1/7=63、`arch-hart-002` 38×2、`arch-pmem-001` 48、`arch-pmem-002` 10×2 全 PASS；我另跑 Tiny `01-load-store` 38/38、`11-cfx` 4/5（`escape_ciii` 签名 0 字节 = `DIV-18`）；cache 代表集 `001/002/003` PASS、`004` 登记 GAP；`arch-time-001/002` PASS。
- 语义核对（patch 逐行）：`cg15`/`cg15 rc3`/`cg16` 齐；pending 只由 `cg16 rc18` W1C 清（进入不清、写 0 幂等、同拍事件优先）；上限 `runMode <= cg15 rc14`；`cg15 rc4`=本次源集合、`rc5`=实时汇总不进寄存器；timer `ENABLE` 即检、写 `cmp` 只 re-arm；`asyncKick` 由事件/可放行写置位、进入清除；`cg9`、`cg8 rc1`、`cg8 rc4/rc5`、`IRQ_EN` 均无译码 ⇒ `CFXREG`；002 的 `cg5 rc0–rc3` 只读、出口 `rc8–rc11`、六判据未回退。
- 约束：本任务 12 文件（`milestones-m18.md` 一行属派单提交）✓；无其它组件/spec/契约/Makefile ✓；未 push ✓；状态 `待验收` ✓；完成区 16 行 ✓。
- 采信：QEMU 同 oracle 腿由 `m18-testcases-005` 承担（本 worktree 无 0.8.1 QEMU 二进制，完成区已披露）。
- 范围外观察：`run_arch --platforms chipyard` 的 `arch-power-001/002` 因 `check_power_rtl.py` 不接受 `--signature-out/--mode` 而 rc=2——两任务未碰 `run_arch.py`/`check_power_rtl.py`，host 侧 argparse 即失败、不进 RTL，判基线既有，供 architect 立 issue。

**Needs Revision finding**
- **F1（阻断，退出码类）**：`tests/arch/hart/escape_escalation.S` 仍读 `cfx_smon cg8 rc1`（002 布局），003 已把该 monitor mask 迁到 `cg15 rc3` ⇒ 读它触发 `CFXREG`，探针 `SYS_EXIT 1`、`check_escape_rtl` rc=1（异常 `info=0x7a088045` = `cfx2rd cfx=2 cg=8 rc=1 rd=5`，落点 `esc_land`，`s_phase0` 判 cause≠1 ⇒ `EXIT 1`）。002 交付的探针在 003 下打红，且 003 改写的 `hart/README.md` 声称该探针覆盖 `cg15 rc3`，与实测不符。改法：`.S` 的读点与头部注释迁到 `cg15 rc3`（`tests/arch/**` 在硬约束内），重跑 `check_escape_rtl` 回 `SYS_EXIT 0`，README 以实测为准。
- **F2（文档级）**：`components/chipyard/changelog.md` 的 003 条目写 `arch-pmem-001` 55 槽，实测 48 槽（完成区与 `pmem/README.md` 均为 48）；`tests/arch/vast-arch-inventory.md` 亦仍写 55 槽 ⇒ architect 收尾改。
- **F3（文档级）**：`run.sh` 不含 Tiny 基线与残留门断言（Tiny 结果只落日志）、`check-patch-tree chipyard problems` 零输出时恒过，且未留 `--inject` 的 EXIT/stdout 记录（本轮由审查者重跑补齐）。

**判决**：Needs Revision（F1 指名返工；F2/F3 随返工一并处理）

### 第 2 轮 engineer 自审（返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `escape_escalation.S` 仍读 `cfx_smon cg8 rc1`（CFXREG 落 esc_land） | ✅已修 | `.S` 读点/头注/节点注释迁到 `cg15 rc3`；README 口径与实测一致 | `check_escape_rtl` → `PASS escape_escalation（SYS_EXIT 0）`、rc=0；已纳入 `run.sh` |
| F2 changelog/inventory 写 `arch-pmem-001` 55 槽 | ✅已修 | 两处改 48（changelog 同步把注入 B 措辞改成「删模式上限」） | `grep '55 槽'` 两文件 0 命中；doc 与实测 48 槽一致 |
| F3 `run.sh` 缺 Tiny 基线/残留门，且无 `--inject` 的 EXIT/stdout | ✅已修 | 加 `check-no-residue`、Tiny `01-load-store` 38/38 与 `11-cfx` 4/5（含 DIV-18 负例）、escalation 探针；产出 `run-inject.stdout`/`run-inject.EXIT` | `run.sh --base` 38/38、EXIT=0；`--inject` 结果见运行期证据目录 |

判决：3 条 finding 全部修复；状态保持「待验收」。

### 第 2 轮 reviewer 验收

**重跑记录（仓库根执行运行期证据目录内的 `run.sh`，均本轮亲跑）**
- `--base` ⇒ `summary: 38/38 checks passed, 0 failed`、EXIT=0（0 条 `[FAIL]`）；`--inject` ⇒ `summary: 14/14`、EXIT=0。
- **F1 闭环**：base 内 `escape_escalation probe rc | expected=0 actual=0`；我另在 worktree 单独重跑 `check_escape_rtl` ⇒ `PASS escape_escalation（SYS_EXIT 0）`、rc=0；`escape_escalation.S` 读点 = `cfx2rd cfx_smon, cg15, rc3, rd5`，头注与节点注释同步 `cg15 rc3`，全文件 0 处 `cg8`。
- 向量：`arch-hart-002` 38×2、`arch-hart-001` 124 槽仅 `DIV-17`(1/7)=63、`arch-pmem-001` 48、`arch-pmem-002` 10×2；`check-no-residue` rc=0；Tiny `01-load-store` 38/38、`11-cfx` 4/5（`escape_ciii` 负例断言在 base 内）。
- 脚本注入 A/B：A 真红（`arch-hart-002/smon red actual=1`、`slot 07/20 ... expected 0x8000 actual 0`）、B 真红（`slot 101 ... actual 0xbad0c14`）；两路 `cp`+md5 还原（`ec9d2205…`）重建回绿、源树 `git status` 空、HEAD `564fbcd`。
- **审查者自设注入 D**（换角度：`cg16 rc18` W1C ack 改 no-op）：首版只关掉事件环里的重复清除 ⇒ 向量仍绿（写块内另有同条件清除）；补齐写块+事件环 4 处后重建 ⇒ `arch-hart-002/smon` rc=1，`slot 24 ack (cg16 rc18 W1C): pending = 0 expected 0x0 actual 0x8000`、slot 31 同；`cp`+md5 还原（与备份逐字节相等、`grep INJ-D` = 0）重建 ⇒ `PASS arch-hart-002/smon（38 槽）` rc=0、Vast sim md5 回 `e46730f9…`。
- **F2**：`changelog.md`、`vast-arch-inventory.md` 中 `55 槽` **0 命中**，`48 槽` 各 1 命中。
- **F3**：`run.sh` 含 `check-no-residue`、step 4 escalation 探针、step 5b Tiny 基线（38/38、4/5、DIV-18 负例）三处断言；运行期证据目录有 `run-base.EXIT=0`（38/38）与 `run-inject.EXIT=0`（14/14）+ stdout。
- 范围：`8896b84b` = 4 文件（任务书/changelog/`escape_escalation.S`/inventory），与完成区声明一致；无 spec/契约/Makefile/其它组件/`tests/inst` 改动；未 push；状态 `待验收`；交接记录在批次册「chipyard 写者交接」+ M16 台账 033 行。

**finding（不阻断）**：① `run.sh` 的 `check-patch-tree chipyard problems` 在工具零输出时仍恒过（同脚本 `source-state` 兜底）；② `timerPending`/`dmaPending` 的 ack 清除在写块与事件环各写一份（同条件、幂等，建议合并）；③ 本轮重建后 Tiny sim md5 为 `a0bfcb5e…`（完成区记 `265181f1…`），与 002 已登记的「Verilator 不逐位复现」一致，判据以源码 md5 `ec9d2205…` + 载体回绿为准；④ 任务书/030 台账行未写交接语（记录在批次册与 M16 台账）。均沿第 1 轮口径，不阻断。

**判决**：Accepted
