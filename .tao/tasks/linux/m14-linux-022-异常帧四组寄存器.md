# m14-linux-022: 异常入口/出口帧扩到四组寄存器（rd/rb/rf/ra）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（K2 `trap.S` 与 K3 已闭合）；**被 `m14-linux-016`/`017` 依赖**（进程切换与 U-mode 帧以本任务为准）
**可并行分片**：否（`arch/dadao` 入口汇编 + 帧结构唯一）
**预估**：4–6 h
**档位**：大改（汇编入口 + 帧结构 + 跨阶段门控回改）
**状态**：待验收

## 背景（用户 2026-11-17 裁定）

> 用户：「ra 和 rf 的保存/恢复不一定需要用 rd 来转存，有直接可用的 ld/st 以及 ldm/stm。在 M14 中，rd/rb/rf/ra 都在异常入口/出口处处理，以后做优化的时候再考虑其它方式。」

现状：`arch/dadao/kernel/trap.S` 的 `DADAO_GPR_SAVE` 只保存 **`rd1–rd63` + `rb1–rb63`**（`arch/dadao/include/asm/entry.h`），帧里没有 `ra`/`rf`。

规范依据：

- `spec/SimRISC-00`：「**进程切换时，操作系统须保存和恢复全部 `ra0–ra63` 寄存器**」；「**异常进入和退出不改变 `ra0–ra63` 的内容**，异常 handler 中可正常使用 `call`/`ret`」——后者要求入口存 ra、出口恢复，否则 handler 的 `call/ret` 会改动用户 RA 状态。
- `spec/SimRISC-00` 指令编码表：`ld.o`/`st.o` 有 **RA/RF 形式**（`ld.o_rrii_ra`/`st.o_rrii_ra`/`ld.o_rrii_rf`/`st.o_rrii_rf`），**无需 rd 转存**；`ra` 的存取按基准索引换算（`RACNT`/`MRPTR`，见 spec 对应条）。
- `ldm/stm` 只支持 `rd` 组（`{rdHA:rdHA+immu6-1}`），**不能**搬 ra/rf。

## 目标

1. **帧结构扩四组**：`struct pt_regs`（`arch/dadao/include/asm/ptrace.h`）增加 `ra[0..63]` 与 `rf[0..63]`，与现有 `rd`/`rb` 并列；所有偏移用 `PT_*` 宏，禁止在探针里硬编码偏移。
2. **入口保存**（同步 `trap.S` 与异步 `async_trap.S` 两条路径都要）：
   - `rd`/`rb` 保持现有方式；
   - `ra0–ra63` 用 **`stm.o {ra0:ra63}`**（`ldm/stm` 的 ra 形式：`SimRISC-01` L102–103 / 编码 `stm.o_rrri_ra`；`immu6` ≤63 ⇒ 64 个寄存器分 2 条）；保存/恢复必须使 `RACNT`/`MRPTR` 与内容一致（spec 的基准索引语义）；
   - `rf0–rf63` 用 **`stm.o {rf0:rf63}`**（`SimRISC-01` L124–127 / 编码 `stm.o_rrri_rf`；`rf0` 作源读完整 64 位、作目的合法）；同样分 2 条。
3. **出口恢复**：反向 `ldm.o {ra…}` / `ldm.o {rf…}`（同分块）；恢复 `ra` 时保证 `RACNT/MRPTR` 与保存时一致。
4. **语义目标**：异常 handler 内正常使用 `call`/`ret` **不得**改变用户可见的 `ra`/`rf`；进程切换后用户四组寄存器原样恢复。
5. **K2/K3 回改**：现有探针/门控若按旧帧偏移/字段数断言，须同步；`check-linux-k2`、`check-linux-k3` 必须回绿（旧断言可在本任务内按「阶段推进即退役」规则改限定语）。
6. **性能登记**：每 trap 增加 **~4 条块传送**（ra/rf 各 2 条 `stm.o`/`ldm.o`）+ 现有 rd/rb 路径；M14 不优化，登记为「后续优化项」（lazy/按需/switch_to 迁移等），**不得**在本任务引入 lazy 机制。

## 验收（逐条贴真实 rc）

1. **帧字段**：`pt_regs` 四组各 64 项 + `ip`/`status`；`sizeof`/偏移自洽（编译期断言）。
2. **同步异常**：探针在 handler 内 `call/ret` 后返回，用户态 `ra`/`rf` 与异常前逐项相等（构造：用户态预置 `ra_i`/`rf_i` 特征值 → 触发异常 → handler 用 `call` → 返回后读回比对）。
3. **异步中断**：同样验证（时钟中断 handler 用 `call/ret` 后 `ra`/`rf` 不丢）。
4. **进程切换**：A/B 两进程分别预置不同的 `ra`/`rf` 特征值，交替切换后各自读回正确（与 `017` 的 U-mode 帧往返配合，但本任务先用内核侧自检）。
5. **≥4 路注入**（`cp`+md5 还原、重建回绿）：① 入口漏存 `ra` ⇒ ② 号断言红；② 入口漏存 `rf` ⇒ 3 号红；③ 出口漏恢复 `ra` ⇒ 2 号红；④ 帧偏移改错一位 ⇒ 编译期/运行期红。
6. **不回归**：`check-linux-k0/-k1/-k2/-k3` 全 rc=0；`check-patch-tree` linux 段 0 problem；`--source-state` linux OK。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 只动：`components/linux/patches/arch/dadao/kernel/{trap.S,async_trap.S}.patch`、`include/asm/{entry.h,ptrace.h}.patch`、相关探针/门控脚本（`tools/linux/check_k2.py`、`check_k3.py` 的帧偏移/字段断言）、`components/linux/changelog.md`、`series`、本任务书。**不动** `spec/`、`.tao/contracts/`、`tests/`、`components/{qemu,gem5,chipyard}`、根 `Makefile`。
3. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md`）。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。
5. 构建 `JOBS=32`；禁边构建边跑批；长命令落运行期日志并记 `*_EXIT`。

## 待裁定

（无；帧范围由用户 2026-11-17 口头裁定：四组都在入口/出口处理，优化后置）

## 审阅记录

### 第 1 轮 reviewer 验收（大改档位：独立重跑 + 8 路独立注入）

**重跑**（workdir=任务 worktree，`>log; echo $?` 取真码，无 `| tee`）：`check-linux-k0` `119/119` rc=0；`-k1` `PASS (112/112)` rc=0；`-k2` `PASS (164/164)` rc=0（`B27 E15 T17 M12 S20 X9 R4 G60/60`）；`-k3` `PASS (263/263)` rc=0；`check-patch-tree` `419 patches OK` rc=0；`--source-state` `linux OK count=1 clean=True` rc=0；证据脚本 `run.sh` rc=0（8 项）、`run.sh --inject` rc=0（9/9 路 + 编译期注入 build rc=1→还原 rc=0）；三探针串行 `k2_trap_probe 85/85`、`k2_irq_probe 99/99`、`k2_time_probe 159/159` 全 rc=0；收尾复跑 `check-linux-k2` `164/164` rc=0。

**语义（我重跑的原始输出）**：P12 四轮 `frame_mm=0 after_mm=0 restore_mm=0`、`call=0x5a69`、`tag0=0xa0220000/1000/2000/3000`、`ra1=rf1=tag0`、`rf0=0x7ff8000{0..3}7fc00011`、`racnt=6 ra0=0x6000000000000`；P6 `ticks=1 frame_mm=0 restore_mm=0 ra1=0xa0230000 rf1=0xa0230000 rf0=0x7ff800037fc00012 racnt=5`；横幅 `frame_bytes=2064 banks=rd,rb,ra,rf`。

**帧/入口**：`pt_regs` = 四组各 64 + `ip`/`status` = (4*64+2)*8 = **2064 B**，6 条 `_Static_assert`（含 `offsetof(status)+8 <= 2048`）；偏移推算 ip=1024/status=1032 ≤2047 可用 `st.o`、ra/rf=1040..2063 超 `imms12` ⇒ 必须块传送，与设计一致；`entry.h` SAVE/RESTORE 各 4 条 `stm/ldm.o {ra0:ra62}+{ra63}+{rf0:rf62}+{rf63}`，逐条 ra/rf `ld/st` 计数 **0**（无 rd 转存、无逐寄存器存取）；`trap.S`/`async_trap.S` 两路均接共用宏；编码合法（`SimRISC-01` L159/162/179/182，`immu6`=63/1；`mreg_range_addr_overlap` 仅 8 条 rb/rd 形式）；`ra0` 整字往返后 `racnt=6 ra0=0x6000000000000` 四轮不变 ⇒ 恢复语义正确。

**独立注入 8 路**（`cp`+md5、禁 `git checkout/restore/stash/show`、还原后 md5 全 OK；含 5 路任务书未列）：
- `ra-save-sync` → rc=1，G1/G11/G13 红（P12 行不出现）；`rf-save-sync` → rc=1，G2/G3/G4 红（`frame_first=64`、`frame_mm=17`）；`ra-restore-sync` → rc=1，G2/G4 红（`after_first=1`）
- `rf-slot-off`（`PT_RF_BASE+8`）→ rc=1，G2/G3 红（`frame_mm=18`）；`async-ra-blank`（异步帧 ra[1] 抹 0）→ rc=1，**仅 G14 红、同步组全绿** ⇒ 两路径隔离成立
- `rf-restore-with-use`（handler 写 rf1 + 出口漏恢复 rf）→ rc=1，G2/G4 红（`after_first=65`）；对照 `rf-handler-use` → 绿 rc=0（证明出口恢复生效）
- 注入后强制重编（`touch`）→ `check_k2 --no-regress` `PASS (160/160)` rc=0、G 组 0 FAIL

**约束核验**：`git rev-parse --show-toplevel`=任务 worktree、branch=`m14-linux-022`、收尾 `status --porcelain -uall` 干净；`$BASE..HEAD`（BASE=30ef63cd）14 文件全在硬约束2 白名单 + 已披露的 F8（4 份内核侧补丁：PT_* 偏移/入口横幅/验收2、3 要求的内核侧自检，必要）与 F10（3 个探针，顺带修）内；禁区（`spec/`、`.tao/contracts/`、`tests/`、`components/{qemu,gem5,chipyard}`、根 `Makefile`）0 命中；版本号 0 命中；`series` 未改；`JOBS=32`、无 `| tee` 吞码。

**findings（不阻断）**：① **G4 的 rf 半边缺独立可达反例**——单删 `ldm.o {rf…}` 不变红（`PASS (160/160)`），因 handler 从不写 rf；复合注入才红 ⇒ 建议 P12 在 handler 内写一次 rf 使该半边可达 FAIL。② `check_k2.py` 的 trap/irq 切片钉了 `K3_PF_SELFTEST=0` 但未钉 `K3_PT_SELFTEST`（F10 只修 3 个探针）：当前顺序不触发，先跑 k3 `pt` 镜像再跑 k2 仍可能继承 `=y`。③ `run.sh` 逐路注入判定 `grep -q` 未过滤 `[FAIL]` 前缀（FAIL 行也命中）；总判定靠 `check-k2 --inject` 的 rc 门控兜底，脚本仍能红，但逐路显示不可信。④ engineer 修订任务书「目标 2/3/6」正文（`st.o` 逐条 → `stm/ldm` 块传送、~128 条 → ~4 条）与用户 2026-11-17 裁定一致、验收段未削弱，属硬约束2 允许范围，建议 architect 复核。⑤ 我方过程事故：两条后台命令并发争用共享构建树，致 trap/time 探针各假红一次（`C1 K2_EARLY_STOP=<unset>`、`config slice rc=1`），串行干净重跑后 85/85、159/159 —— 属 reviewer 工具侧并发，非交付物缺陷。

**判决：Accepted** —— 全部验收命令在我自己的重跑下通过，任务书验收 5 的 4 类注入均可达红，硬约束无违反；上列 findings 供 architect 收尾处置。

### 第 2 轮 engineer 返工（reviewer finding ①②③，判据强度/防护，不扩大范围）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① G4 的 rf 半边缺独立可达反例：单删 `ldm.o {rf…}` 不变红（handler 从不写 rf） | ✅已修 | P12 的 handler 内写一次 FP 组：`rf32 := K2_P12_RF_SENTINEL + pass`；P12 行加 `sent=`；`check_k2` 新增「handler 写过 FP 组」每轮断言；新增固定注入 `no-rf-restore`（第 10 路） | 单删 rf 恢复 ⇒ `after_first=96`（=64+rf32）G2 红；cp+md5 还原后回绿；全程 `10/10 路` |
| ② `check_k2.py` 切片未钉 `K3_PT_SELFTEST`（F10 只修了 3 个探针） | ✅已修 | trap/irq 切片加 `CONFIG_DADAO_K3_PT_SELFTEST=n`，并进 `IMAGE_UNSET`（B1 断言「未设」） | 先在共享构建树植入 `K3_PT_SELFTEST=y` 再跑门控：B1 trap/irq 两条「未设」PASS，`170/170` rc=0 |
| ③ `run.sh` 逐路注入判定用裸 `grep -q`（`[FAIL]` 行也命中） | ✅已修 | 逐路判据改为「`^  \[PASS\] inject:<route> ` 命中 ≥3 且 `^  \[FAIL\] inject:<route> ` 计数为 0」，并打印 `PASS=n FAIL=n`；总判定另要求精确 `check-linux-k2 --inject: PASS (10/10 …)` 行 | `run.sh --inject`：逐路 `PASS=5 FAIL=0`，总判定 `10/10 路` rc=0 |

**判决**：3 条 finding 全修并复验（`check-linux-k2` `170/170`、`-k3` `263/263`、`run.sh` 两模式 rc=0、三探针 85/85·99/99·159/159）；无未修 finding ⇒ `**状态**：待验收`。

### 第 1 轮 engineer 自审（实现后，自主逐行）

**审查范围**：`patches/.../{ptrace.h,entry.h,asm-offsets.c,trap.S,async_trap.S,traps.c,k2_selftest.c,k2_irq_test.c}`、`tools/linux/check_k2.py`、运行期证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `ld.o rf0, [rb19, 0]` 把 FCSR **值**当地址（`register … __asm__("rb19")` 是值寄存器）⇒ 启动即 `MALIGN info=0x11` | ✅已修 | FCSR 字并入 `k2_p12_tags[16]`，用 `[rb18, 128]` 寻址，少一个寄存器 | 重新启动后 P12 四轮 `frame_mm=0` |
| F2 P12 单行超 256 B：早控台 `char buf[256]` 截断，连 `\n` 一起丢（多行粘连） | ✅已修 | 拆为短行 + 仅失配时打明细行；代码注明 256 上限 | 输出四行独立、字段完整 |
| F3 P12 原挂在 `k2_case_p8()` 之后：P8 redirect 路径经 `k2_redirect_landing()` 直接进 `k2_selftest_final()`，P12 永不执行 | ✅已修 | 调用点移到 `k2_case_p5()` 之后，并在末尾复位 `k2_probe.report` | 启动输出出现 4 条 `P12: pass=` |
| F4 P6 结尾 `local_irq_disable()` ⇒ P4 序列拿不到 tick，镜像自报 `K2 fail: … P4 sequence code=0x15` | ✅已修 | 改为 `local_irq_restore(flags)`，并加「还原后 `restore_mm`」自证 | irq 镜像走完 P4 与 `done`，`restore_mm=0` |
| F5 `"i"(K2_P6_SPINS)` 用 `%c0`：`%0` 是操作数 0（指针）⇒ 立即数为空、汇编报错 | ✅已修 | 改 `%1`（常量操作数） | trap/irq 镜像均构建 rc=0 |
| F6 `check_k2._src_define` 正则不接受行尾注释与 `UL` 后缀 ⇒ G13 前 `SystemExit` | ✅已修 | 正则加 `(?:ULL\|UL\|L\|U)?\b`，允许行尾注释 | `check_k2` 160/160 PASS |
| F7 注入 `no-ra-save`／`ra-last-slot-off-by-one` 在**更早**的 K1 预置异常处即以 `RASUF` 终止，P12 行不会出现 | ✅已修 | 判定改为「P12 差异行**或** RASUF/RASOF 具名终止」并打印实际形态 | `--inject` 8/8 路按预期变红 |
| F8 越界披露：任务书白名单未列 `asm-offsets.c`/`traps.c`/`k2_selftest.c`/`k2_irq_test.c`（`PT_RA/RF` 偏移、入口横幅、两处自检必须在内核侧） | ⏸延后（披露） | 只改这 4 份补丁的对应函数，未触其它文件；`series` 无新增文件故未改 | `check-patch-tree` linux 74 补丁 0 problem |
| F10 `k2_trap_probe`／`k2_irq_probe`／`k2_time_probe` 的镜像切片未钉 `CONFIG_DADAO_K3_{PT,PF}_SELFTEST`（K2 之后的符号），在 `check_k3` 之后运行会继承 K3 自检镜像 ⇒ 启动即 `ADWBFAIL` 终止（既有缺陷，非本任务引入） | ✅已修 | 三个探针的切片各加 `K3_PT_SELFTEST=n`／`K3_PF_SELFTEST=0`（与 `check_k0/1/2` 既有做法一致） | 三探针自重跑：trap/irq/time 见下方真实输出 |
| F9 语境核对：`ldm/stm` 的 RA/RF 形式有 `mreg_range_addr_overlap` 禁令吗？——仅 RD/RB 形式适用，RA/RF 形式「不适用」；`rd2` 作索引不落入 RA/RF 传送范围 | ✅无问题 | 未改 | `spec/SimRISC-01 §3/§4` 原文；组装 + 反汇编确认编码 |

**判决**：F1–F7、F10 已修并复验；F8 属披露（范围必要），F9 为规范核对结论；无未修 finding ⇒ 可标「待验收」。

### 第 2 轮 reviewer 验收（3 条 finding 处置 + 不回归；HEAD=21ba637b）

**复核范围**：`114e8491..21ba637b` 4 文件（任务书/changelog/`k2_selftest.c.patch`/`check_k2.py`）+ 未跟踪证据脚本 `run.sh`（逐行读判据）。**① rf 半边可达**：P12 handler 现写 `rf32 := 0xd0220000+pass`、行尾增 `sent=` 字段，`check_k2` 现场派生哨兵并加 4 条 G10 断言；`no-rf-restore` 为第 10 路（判据 `after_first>=64`）。我现场单删出口两条 `ldm.o {rf…}`（md5 `2c8c0fe4`→`778bcf47`，残余 ldm rf 行数=0）⇒ `RED_RC=1 G_FAIL=5`、`after_first=96`（=64+32、`got=0xd022000{0..3}` 即哨兵）、G2+G4 红、`FAIL (161/166)`；`cp`+md5 还原（`2c8c0fe4` 一致）⇒ `GREEN_RC=0 G_FAIL=0`、`PASS (166/166)`。
**② K2 串味**：trap/irq 切片各补 `CONFIG_DADAO_K3_PT_SELFTEST=n` 并入 `IMAGE_UNSET`（B1 +2 条）。机械证据（`EVIDENCE_RC=0`）：(a) 共享 `.config` 植入 `=y` 后跑 `config_image("trap")` rc=0 ⇒ 该符号 `=` 行消失、B1 谓词成立；(b) 把 `=y` 放进送检快照、**真实调用 `check_build`** ⇒ `B1 trap 镜像配置：…未设: 期望=[] 实际=['CONFIG_DADAO_K3_PT_SELFTEST=y']` 红 1 条（可达 FAIL）；随后重配还原 rc=0。
**③ `run.sh` 逐路判据**：已废除裸 `grep -q`，改为 `[PASS] inject:<route> ` 前缀计数 ≥3 **且** `[FAIL] inject:<route> ` 计数=0，总判定 `grep -qx 'check-linux-k2 --inject: PASS (10/10 路注入按预期变红并还原)'`+rc=0。实跑 `run.sh --inject` → `RUN_INJECT_RC=0`，6 条路由逐条 `PASS=5 FAIL=0`、总判定行精确命中、编译期注入 `rc=1`→还原→回绿 `rc=0`，尾行 `evidence: PASS（全部检查 rc=0）`。

**④ 不回归**（我自己的重跑，`>log; echo $?`）：`check-linux-k2` `PASS (170/170)` rc=0（`B 29/29 … G 64/64`，较上轮 +2 B1、+4 G10，与新增断言数吻合）；`check-linux-k3` `PASS (263/263)` rc=0；三探针 `85/85`、`99/99`、`159/159` 全 rc=0；`check-patch-tree` `419 patches OK` rc=0；`--source-state` `linux OK count=1 clean=True` rc=0（收尾复跑同值）。
**约束**：`git rev-parse --show-toplevel`=任务 worktree、branch=`m14-linux-022`、收尾 `git status -uall` 空；注入仅 `cp`+md5（未用 `git checkout/restore/stash/show`、无 `.preinject` 残留）；源树 3 文件 md5 与基线一致；`$BASE..HEAD` 14 文件、禁区 0 命中；`JOBS=32`、无 `| tee`；未提交 git、未碰主工作树。

**判决：Accepted** —— 3 条 finding 均实测闭环（rf 半边由不可观测变为可达红、K3 串味双向验证、逐路判据收紧且实跑 10/10），四项不回归全绿。

## 完成区

**测试结果**：全部通过。`check-linux-k0` 119/119 rc=0；经 K2 门控 R 组 `check-linux-k1` 112/112 rc=0；`check-linux-k2` **170/170** rc=0（`[GROUP] B 29/29 E 15/15 T 17/17 M 12/12 S 20/20 X 9/9 R 4/4 G 64/64`）；`check-linux-k3` 263/263 rc=0；K2 三探针自重跑（默认模式：`k2_trap_probe` 85/85、`k2_irq_probe` 99/99、`k2_time_probe` 159/159）；`check-patch-tree` 419 补丁 0 problem；`--source-state` linux OK（count=1 clean=True）；`check-k2 --selfcheck` 8/8 组可翻转；`check-k2 --inject` **10/10 路**；一键证据脚本（运行期证据目录 `run.sh`）两模式 rc=0。
**修改文件**（14 个）：`patches/.../include/asm/{ptrace.h,entry.h}.patch`（帧扩四组 + 6 条编译期断言；SAVE/RESTORE 各 +4 条块传送）；`patches/.../kernel/{trap.S,async_trap.S}.patch`（帧说明，两入口共用宏）；`patches/.../kernel/{asm-offsets.c,traps.c}.patch`（`PT_RA/RF_BASE/LAST`；入口横幅 `frame_bytes=`/`banks=rd,rb,ra,rf`）；`patches/.../kernel/{k2_selftest.c,k2_irq_test.c}.patch`（P12/P6）；`tools/linux/check_k2.py`（G 组 + selfcheck 8 组 + inject 9 路）；`tools/linux/{k2_trap_probe,k2_irq_probe,k2_time_probe}.py`（镜像切片补钉 K3 自检符号）；`components/linux/changelog.md`、本任务书。`series` 未改（无新增文件）。
**验收结果**（逐条真实输出）：
1. 帧：`K2 trap: entry=… frame_bytes=2064 banks=rd,rb,ra,rf`；G11 期望 2064 实际 2064；G12「≥4 条断言且含 2048 界」True。
2. 同步：`K2 probe P12: pass=0..3 racnt=6 ra0=0x6000000000000 tag0=0xa0220000/1000/2000/3000 ra1=tag0 rf1=tag0 rf0=0x7ff8000{0..3}7fc00011 call=0x5a69 frame_mm=0 after_mm=0 restore_mm=0`。
3. 异步：`K2 irq P6: racnt=5 ra0=0x5000000000000 ra1=0xa0230000 rf1=0xa0230000 rf0=0x7ff800037fc00012 ticks=1 frame_mm=0 at=255 exp=0x0 got=0x0 restore_mm=0`。
4. A/B 交替：P12 四轮特征值互异（`tag0` 每轮 +0x1000），逐轮「入口捕获／出口恢复／自身还原」三项计数全为 0（内核侧自检；真 `switch_to` 归 016/017 用本帧实现）。
5. 注入（`cp`+md5 还原，重建回绿）：`no-ra-save`→G1 红（更早的 K1 预置异常即 `RASUF` 终止）；`no-rf-save`→G2 红（`frame_first=64`）；`no-rf-save-irq`→G14 红（`frame_mm=17`，异步镜像）；`no-ra-restore`→G2 红（`after_first=1`）；`no-rf-restore`→G2 红（`after_first=96` = 64+rf32）；`ra-last-slot-off-by-one`→G1 红；编译期：`ip` 移出立即数窗口 ⇒ build rc=1（ptrace.h:75），cp+md5 还原后 rc=0。
6. 不回归：k0/k1/k2/k3 全 rc=0（上列计数）；patch-tree 0 problem；source-state OK。
**新发现/坑**：① 早控台 `dadao_early_printf` 用 `char buf[256]`，超长单行被截断且**连 `\n` 一起丢**；② `register x __asm__("rbN")` 是**值**寄存器，拿它当 `[rbN, imm]` 基址会把值当地址（实测 `MALIGN info=0x11`）；③ `ldm/stm` 的 RA/RF 形式在 QEMU 侧经 `helper_ra_load/store` 换算基准索引 ⇒ `ra0` 整字回写即恢复 `RACNT`/`MRPTR`，**不需** `rd2ra`；④ 帧 2064 B > `imms12` 的 2048 窗口，字段序（`ip`/`status` 在前）是硬约束，已由 `_Static_assert` 钉住；⑤ RA 组坏了会先在**更早**的异常（K1 预置缺页）以 `RASUF` 终止，P12 行可能不出现（注入判定须接受两种红）；⑥ K2 探针镜像切片未钉 K3 自检符号，`check_k3` 之后跑探针会串味（本任务顺手修）。
**遗留问题**：无功能遗留。复核 3 条 finding 处置：①P12 handler 内写 `rf32 := 每轮哨兵`（`sent=` 证据），并把 `no-rf-restore` 固定成第 10 路注入（单删 `ldm.o {rf…}` ⇒ `after_first=96` 红，cp+md5 还原回绿）；②`check_k2` 的 trap/irq 切片补钉并断言 `CONFIG_DADAO_K3_PT_SELFTEST`（先在共享构建树植入 `=y` 再跑门控：B1 两条「未设」PASS、170/170 绿）；③`run.sh` 逐路判定改为「`[PASS]` 前缀命中 ≥3 且 `[FAIL]` 行为 0」+ 总判定要求精确的 `10/10` 行，不再用裸 `grep -q`。**性能登记**：每 trap 增 **4 条块传送**（ra/rf 各 2 条 `stm.o`/`ldm.o`），**优化后置**（lazy/按需/`switch_to` 迁移），本任务**未**引入 lazy FPU。**待裁定**：无。
