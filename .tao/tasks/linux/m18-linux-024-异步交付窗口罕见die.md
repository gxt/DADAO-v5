# m18-linux-024: 异步交付与 umon 桩 `reopen→escape` 窗口的罕见 die（~1/475）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-022`（R2 内核异步新模型）已合入；`m18-linux-023`（扁平位图解码）合入后可独立验证（两者同改 `components/linux`，须串行）
**可并行分片**：否（同改 `components/linux`）
**预估**：3–5 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（`m18-linux-022` 第 3 轮返工留档，2026-11-25）

`m18-linux-022` 已把 m45 的**常见**停摆（`SYNCN=0x355630` 静默 CFXMEM 死循环）修掉：系统态捕获改走 `trap cfx_smon, DADAO_SMON_FROM_ASYNC_KERNEL`(0x2f7)，由 smon 半用 RW 的 `cg5 rc0/rc1/rc3` 重写运行模式/当前 cfx/返回目标，再 `escape` 到软件返程跳板。

**剩余罕见竞态**（实测 `run-tail2` 400 次中 1 次、累计约 1/475）：

- **触发窗口**：异步交付恰好落在 umon 桩 `reopen → escape` 的 **4 条指令窗口**内；
- **现象**：软件返程的 `set.rb rb3, 0` 让被中断的 `ldm.o` 以**零基址**取帧 ⇒ `va=0x208` ⇒ `die 0xe1`（与常见停摆不同签名）；
- **已试两版修法，均被门控否决**（不要重复）：
  1. **差值跳转**：`k2irq-t1/t2: FAIL (8/90)`（K2 irq 组崩）；
  2. **把 `reopen` 移到最后**：`final2-k5: 252/282`（K5 掉）。
- **候选方向**（未验证）：让窗口**不可中断**（或交付侧识别窗口并排队），且跳转**不占用任何被测/桩用寄存器**——例如 `ra` 栈软件压栈 + `ret`，或 smon 半直接复位目标现场而不经桩的 `set.rb`。

## 追加范围（2026-11-25，`m18-linux-006` 返工实测，`ISS-539`）

同一族还有更重的表现：**用户态信号投递死在异步异常入口**——`MALIGN(0x1000) ip=dadao_async_excp+0x1fc info=0xfffeffff7fff` → `die mode=2 code=0xec`；另有 `die 0xe1` 与 `clock_gettime01` 无 die 停摆；约 **1 次/10 例**（私人干净内核复现，非并发假红）。要求：

1. 纳入同一根因分析（异步入口的现场污染/交付点）；若确认与「`reopen→escape` 窗口」同源则一并修；
2. 修后跑 `m18-linux-006` 的 `run_suite.py --suite ltp` **≥2 次**，与其验收基线对接（该任务当前因它阻塞在「待返工」）。

## 目标

1. **先把触发条件做成可复现**：给出概率提升手段（如缩短窗口、定向注入、或把交付点钉在窗口第 n 条），把 1/475 变成**可重复触发**的最小用例（≥1/5 触发率），并给出定位证据（`die 0xe1`、`va=0x208`、被中断指令、当时 `rb3`/SP）。
2. **修到 0 触发**：按「窗口不可中断 + 跳转不占寄存器」实现；**不得**用重试/加 `-retry` 掩盖，也不得放宽任何 K2/K5/K6 判据。
3. **回归**：`--boots`/连跑 ≥ 修前触发量的 10 倍（如 ≥5000 次启动或等价的定向循环）**0 触发**；K2/K5/K6 全绿。

## 验收（逐条贴真实 rc）

1. 最小复现：修前 ≥1/5 触发、修后 0（同一脚本、同一镜像、固定 seed/轮数），两侧命令与日志完整。
2. K2 170/170、K5 282/282、K6 与基线逐行相同或全绿；`run.sh` 全量 rc=0。
3. 可达 FAIL ≥2 路（把窗口保护去掉 ⇒ 复现红；把跳转改成占寄存器 ⇒ K2/K5 红），`cp`+md5 还原。
4. 补丁按 `docs/Process-01` 折进 `base+1` 单提交并重导出；`check-patch-tree` linux 段 0 problem。
5. 证据脚本落运行期证据目录（含 `run.sh`），长跑 `setsid nohup` + 日志 + `*_EXIT`。

## 约束

独立 `git worktree`（分支 = `m18-linux-024`）；不提交 git；只改 `components/linux/**` + 必要探针/任务书；不改 `spec/`、契约、`Makefile`、QEMU 补丁；术语「寄存器组」；完成区不写具体 `.work/**` 路径；**逐条记录已试且失败的方案**，避免下一个人重复。

## 并行另一路（07:12 派单，2026-11-25 10:2x 已停止）结论与处置

同任务曾另起一路（工作树 `m18-linux-024-2`，私人运行期根），其已得结论并入本册，**不再单独续跑**：

- **可复现 harness**：跑 K6 自身输入脚本并检测 die/hang；基线 **2 dies/12 boots**（签名 `K3 pf … ip=0x20000153518 va=0x8 result=die-no-vma` → `die 0xe4`）；确定性 knockout（返程 frame base 强制置 0）每次必红。
- **根因同判**：`dadao_async_kernel_return` 以 `set.rb rb3, 0; jump [rb3, rd3, 0]` 收尾，被中断桩以清零 `rb3` 恢复现场。
- **两版试改均已否决**：A（tail + 入口捕获掩码 + 相对跳转）1 die + 2 hang / 10 启；B（tail + 相对跳转）3 dies（2×`0x82`、1×`0xe1`）/ 12 启、0 hang。
- **该路未闭合签名**：① `cause=CFXTRAP(0x1) ip=<kernel text> info=0x7f0802f7` → `die 0x82`（supv 帧 `ip` 取自陈旧 `dadao_async_outer_cg5.cause_ip`，`info` 是异步 handoff 的 `trap cfx_smon,759` 指令字 ⇒ 帧由两来源拼装）；② hang：`cfx2 CID=PTWMEM CIP=dadao_do_page_fault+0x17c`、`rb4=0`（`va=0x410`，NULL vma），缺页处理自身缺页后在 `dadao_early_exit` semihosting 后空转。
- **处置**：本路已改用 `cfx_jmon` 返程帧（不经 `dadao_async_kernel_return`、不经 smon handoff），上述 A/B 变体与两条签名构造随之退役；其 harness/日志留运行期证据目录供对照，**后续不得重复 A/B 两版**。

## 完成区

**测试结果**：第 5 轮（恒真断言修补）`run.sh` 全量 **RESULT: PASS rc=0**，**7/7 检查**，858 s（其前同一脚本在「写回改错一位」的注入下 **RESULT: FAIL rc=1**、`md5 还原失败=7` ⇒ 该断言可达红）；`check-config-pins`/`check-tests-index`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog` 全 **rc=0**；`make check` **rc=2** 且与基线日志 `diff` **0 行**（仍只停 `check-patch-tree: 6 problem(s)`＝既有 qemu 段）；紧接 `check-linux-k5` **rc=0 285/285**、`check-linux-k6` **rc=0 82/82**。第 4 轮（L1 回归修补）`run.sh` 全量 **RESULT: PASS rc=0**，**7/7 检查**，1036 s；`make check-config-pins` **rc=0**（93 项；C2 不再报本探针）；`check-tests-index`/`check-tasks`/`check-knowledge-refs` 全 **rc=0**；`--case baseline --boots 1`、`--case window --boots 1` 各 **rc=0** 且「共享 .config 已复原」PASS；紧接 `check-linux-k5` **rc=0 285/285**、`check-linux-k6` **rc=0 82/82**；`make check` 与基线日志**逐行 diff 0 行**（仍只停 `check-patch-tree: 6 problem(s)`＝既有 qemu 段）。第 3 轮（返工后）`run.sh` 全量 **RESULT: PASS rc=0**，**7/7 检查**，535 s（顺序：patch-tree linux 段 → K2/K5/K6 各 1 次 → 六用例探针 → 200 启 soak → 共享 `.config` 复原断言）；紧接着 **`check-linux-k5` rc=0（285/285）、`check-linux-k6` rc=0（82/82）**（证明探针不再串味）；「不恢复 ⇒ 红」演示：`m45_entry_probe.py --boots 1` 后 `check-linux-k5` **rc=2、255/285（30 FAILED）**，`make linux-defconfig` 后复跑 **rc=0、285/285**。历史轮次：`run.sh` 第 2 轮 7/7 PASS rc=0（477 s）、第 1 轮 657 s；`check-linux-k2` **170/170 ×5 + 收口 1 次**、`check-linux-k5`/`k6` 同（×5 + 1 次）；修后启动样本 **4800 启：窗口签名 0**（非窗口 3，见遗留②）；`k5_signal_probe` **30/30 绿**。
**修改文件**：`components/linux/patches/arch/dadao/include/asm/{entry.h,trap.h}.patch`、`components/linux/patches/arch/dadao/kernel/{async_trap.S,irq.c,trap.S,traps.c}.patch`（6 份重导出；series 105 条不变；`async_trap.S.patch` 在收口轮再改 1 处＝删死存 `set.rb rb8`）、`components/linux/changelog.md`、`tests/unit/linux/amb_window_probe.py`（新探针）；运行期证据目录内 `run.sh` 与日志；本任务书。
**验收结果**：① **可复现**：`amb_window_probe.py --case window` 把交付点钉在 umon 桩「重开源位→寄存器恢复」之间（等 ISTATUS 到期再开源位）。**真 pre-fix 代码（6 文件 cp 备份→换回旧版→重建）3/3 红**：`die 0xe4`、`va=0x208`、被中断 `ldm.o {rb1:rb2}, [rb3, rd1=0x208]`、`rb3=0`、SP=内核栈；同一脚本同一镜像修后 **3/3 绿**（窗口内投递 ≈70 次/30 次返回，用户态投递照常）。天然发生率：**修前 1000 启 13 次窗口 die（1.3%）**，修后 **0/4800**。
② **根因**：旧系统态返程以 `set.rb rb3, 0; jump [rb3, rd3, 0]` 收尾 ⇒ 被中断现场 `rb3`（umon/smon 桩帧基址）被清零；窗口投递恢复的第一条 `ldm.o` 零基址取帧。`ISS-539` 的 `MALIGN ip=dadao_async_excp+0x1fc info=0xfffeffff7fff`（info=`~(TIMER|PMEM)` 掩码字被当地址、ip 落在异步桩自身窗口）属同一族。
③ **修法**：系统态返程改走本内核私用的 `cfx_jmon` supv 帧（`init_IRQ()` 在开源位前写行并回读，`K2_FAIL_RESUME_*`=0x16/0x17）：写 `cg5 rc0/rc1/rc3` → `DADAO_GPR_RESTORE_AT_KEEP_RD2_RB3` → 重开源位 → 从帧外 resume 区补 `rd2`/`rb3` → `escape cfx_jmon, [excp_cause_ip, 0]`（返回不占任何寄存器）。窗口=重开+escape；resume 区在帧外 + `prev_cfx==cfx_jmon` 不覆写链规则 ⇒ 跳板自窗口内再投递幂等（`nested` 每启 ~70 次窗口内投递仍绿）。退役 `DADAO_SMON_FROM_ASYNC_KERNEL`/`dadao_async_kernel_return`/`dadao_async_kernel_handoff()` 与 `trap.S` 的 `rd4` 借用。
④ **可达 FAIL 3 路**（均 cp+md5 还原）：`window-clobber-rb3`（返程写 `rb3`）⇒ `va=0x208` 红（2/2）；`window-no-escape`（软件跳转、cfx 不恢复）⇒ `die 0xe7` 红（1/1）；`nested-no-chain`（去链规则+跳板内钉住）⇒ `rc=124` 挂起红（2/5）。注：验收「把跳转改成占寄存器 ⇒ K2/K5 红」一条改用**钉住探针**达成而非 K2/K5——K2/K5 的镜像不在桩窗口内确定性投递（022 实测 pre-fix K5 亦 282/282），故 K2/K5 对本类缺陷不具判别力；钉住探针把同一机械缺陷变成确定性 `va=0x208` 红。
⑤ **既有失败方案不重复**（本任务未再尝试）：022 的差值跳转（K2 irq 8/90）、把 `reopen` 移到最后（K5 228–255/282）。
**新发现/坑**：① 交付窗口是**电平触发**：掩码关闭期内到达的 tick 会在「第一个放开的指令边界」投递 ⇒ 触发概率≈掩码关闭跨度/周期，与「某条指令」无关；钉住它必须「先等 ISTATUS 到期，再开源位」，固定空转不可靠。② `dadao_supv_saved_mask` 在 umon 桩里通常是**已掩**字（K4 入口前 `arch_local_irq_disable`），桩内 reopen 常常是空操作；天然窗口其实落在 `dadao_syscall_enter` 的 `local_irq_restore` 边界（C 上下文 `rb3=0`，故旧代码不炸）与 supv 桩 `escape` 前。③ 修后 4000 启出现 2 次**非窗口签名**红（1 次静默停摆 rc=124、1 次 `handle_softirqs` 内坏 percpu 指针 `va=0x204002130f4` die；均在 /tmp 100% 满时段，其后 2000 启 0 红）⇒ 已留日志，登记待另立任务。④ 本 worktree 需自带 musl/busybox/picolibc/qemu/ltp 源树才能跑 K0/K5/K6（共享安装根不含源树）；`make_vmlinux.py` 的 relink 临时目录写死在 `/tmp/opencode`，`/tmp` 满盘会让 `make linux-vmlinux` 失败（本次一次）。⑤ **共享 `.config` 会被探针钉空**：`m45.build_image()` 为 m45 镜像把 `CONFIG_INITRAMFS_SOURCE` 钉成 `""` 且原本不恢复 ⇒ 下一条命令（K5/K6 门控）继承空 rootfs（`/init.musl` ENOENT、`No working init found`，实测 K5 255/285、30 FAILED）。修法：本探针在首次构建前快照该行、`main()` 的 `finally` 里复原（入口已是空值时改走 `make_defconfig` 生成器）；`run.sh` 也把内核门控排在探针**之前**、结尾再 `make linux-defconfig` 并断言该符号回到 `…initramfs.cpio`。**教训**：`.work/build/linux/.config` 是跨任务共享的隐式状态（ISS-470 同类），任何探针切片都必须在 `finally` 里复原。⑥ `run.sh` 只能判 **linux 段**：`check-patch-tree` 的全局 rc 会在无关组件源树陈旧时变红（merge 带入 `m16-qemu-006` 后 qemu 段 6 problem ⇒ 全局 rc=2），那是别人的契约；本任务只断言 `linux: 105 patch(es)` 且 linux 段 0 problem，全局 rc 仅记录。⑦ 本 worktree 缺 `.cache/refs/riscv-unified-db`，共享 `pre-commit` hook（prek 生成，`--cd=".cache/refs/riscv-unified-db"`）会 ENOENT ⇒ 提交需 `--no-verify`；与 `ISS-510` 无关（`ISS-510` 是另一件事），此前把原因记成 `ISS-510` 是错的，以本条为准。⑧ **C2 规则：调 `apply_config_lines()` 的脚本必须声明 `CONFIG_PINS`**（`check-config-pins` C2，AST 级检 `*.apply_config_lines(...)` 调用）。本探针**不**持有自己的切片（复用 m45 的 `CONFIG_PINS` + `NO_INITRAMFS`，经 `m45.build_image()` 落地），第 3 轮曾用 `defconfig.apply_config_lines([快照行])` 复原共享 `.config` ⇒ `check-config-pins` rc=1。修法：复原**一律**走生成器子进程 `tools/linux/make_defconfig.py`（不 import/不调 `apply_config_lines`），快照只作断言输入；docstring 写明「本模块不声明 `CONFIG_PINS`，因为复用 m45 切片」。
**遗留问题**：① **ISS-539 的 LTP 侧未能复跑**：`m18-linux-006` 的套件镜像在本环境内核 K1 ptw `pre` 处 die（`cause=CFXMEM(0x10000000000002)`、`va=0x20020000000`、`ip=0x…115c00`），且 006 自己 061155 那跑**在 main 树同签名**（与本任务无关）；用户态信号路径改由 `k5_signal_probe` 30/30 + K5/K6 各 5 连跑覆盖。② **修后 4800 启样本中的 3 次非窗口签名红**（0.06% ≈ 1/1600，**不删样本、不重试**）：`300+2000(a)+2000(b)+500` 启，窗口签名 0。三条为 ① 1 次静默停摆（boot 78，`rc=124`，控制台末行 `Memory: … available` 后无 `K4 boundary`）；②③ 2 次 `handle_softirqs` 内坏 percpu 指针（boot 1974 `ip=0x…61518 va=0x204002130f4`；boot 181 `ip=0x…61578 va=0x10`，均 `die 0xe4`/`PTWMEM`）。频率 3/4800；其中前两条发生在 `/tmp` 100% 满时段、第三条在盘正常时段。判定：故障 ip 在通用内核 `handle_softirqs`（不在任何返回桩恢复点），与窗口 die 非同签名，**本任务不修**，登记另立任务；修前 1000 启样本此类 0 例（同率预期 ~0.6，未证伪）。台账与 boot-181 完整控制台在运行期证据目录（`round2_unattributed_reds.txt`、`round2_soak500_boot181_softirq_die.log`；前两条的 console 文件已被后续 soak 同名 tag 覆盖，台账保留了 `K3 pf`/`die`/末行原文）。③ 006 解除阻塞仍需其套件镜像能启动。④ 上述非窗口签名红已按分册形登记为 **`ISS-m18-001`**（本任务不修）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`async_trap.S`（系统态返程跳板 + resume 区 + 链规则）、`entry.h`（`DADAO_GPR_RESTORE_AT_KEEP_RD2_RB3`）、`irq.c`（`cfx_jmon` supv 行安装/掩码/回读）、`trap.S`（删 handoff selector）、`traps.c`（删 `dadao_async_kernel_handoff`）、`trap.h`（选择器退役、`dadao_async_kernel_resume` 声明）、`amb_window_probe.py`（六用例探针）、`run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 resume 区放在帧后 ⇒ `ld.o/st.o` 立即数越界（2048/2088 > 12 位有符号） | ✅已修 | 区移到帧**前**（-48…-8），`.bss` 顺序对调 | 构建通过；反汇编 `ld.o rd2, [rb3, -48] … [-8]` |
| F2 跳板内再投递会覆写捕获帧（帧是嵌套共用的静态对象） | ✅已修（设计） | 源位在寄存器恢复**之后**才重开；尾部最后两条从帧**外** resume 区取 `rd2`/`rb3` | `nested` 用例（跳板窗口内钉住，~70 次/启）绿 |
| F3 嵌套时内层会解析成自己的返程（外层目标丢失） | ✅已修（设计） | 入口写 resume 区前判 `prev_cfx == cfx_jmon`：是则整批保留外层三元组/掩码/`rd2`/`rb3`，跳板幂等重跑 | `nested-no-chain`（去该判据）⇒ rc=124 红 2/5；`nested` 绿 2/2 |
| F4 `cfx_jmon` 行未在开源位前安装 ⇒ 早投递跳 0；且跳板以 `cfx_jmon` 为源写 `cfx_smon cg8 rc1` 需授权 | ✅已修 | `init_IRQ()` §1b：写行/模式 + 回读 + `K2_FAIL_RESUME_VECTOR/MODE`；放开 jmon 的 supv `cfxtrap` bit15 与 smon 的 supv `cfxreg` bit1（均在开源位之前） | K2 170/170 ×5；探针首版从 jmon 读 `cfx_hart` 得 `die 0xe7`（CFXPERM）证明授权确实生效 |
| F5 探针首版「固定空转」没把投递钉进桩窗口（投递被 `dadao_syscall_enter` 的 reopen 吃掉） | ✅已修 | 改「等 `cfx_hart cg8 rc5` ISTATUS 到期 → 在此开源位」；判据加 `irq_kernel >= iters`（防空转仍绿） | 修前 3/3 红 `va=0x208`；修后 3/3 绿（旧版两者皆绿 ⇒ 反向可辨） |
| F6 跳板内固定空转在启动早段（`cfx_hmon`）也生效 ⇒ 每启 70 次 × 空转，偶发 `softirq: huh` 停摆 | ✅已修 | 空转只在被中断 cfx 为 `umon`/`smon` 时执行（探针阶段），并把计数降到 ~1 tick | `nested` 2/2 绿、无停摆；启动阶段 0 开销 |
| F7 探针脚本自身缺陷：`apply_edits` 对 callable/元组替换处理错、md5 还原断言漏 | ✅已修 | 统一 `callable→str/list`；每次注入前 cp 备份、`finally` 写回并断言 md5 | `run.sh` 7/7 通过；7 次还原 0 bad |
| F8 删 `DADAO_GPR_RESTORE_AT_KEEP_RD3` 后是否有残留引用 | ✅已查 | 全树 grep：仅 `async_trap.S` 旧尾部使用，已随替换删除；`KEEP_RD23_RB345` 仍被 umon 两条尾部使用 | 构建 0 error；`llvm-nm -u vmlinux` 空 |
| F9 `escape cfx_jmon` 失败路径会落回跳板自身（核内 bug 时挂起而非具名 die） | ⏸记录 | 未改：`escape` 失败（CFXESC/ILLI）本身即内核 bug，且 `cg5` 是软件三元组不应失败；另 `jump .Lstuck` 兜底 | 6 个用例 + 4000 启 0 次触发 |

**判决**：全部 finding 已修/已查；`run.sh` 7/7 PASS、K2/K5/K6 各 5 连跑全绿、soak 4000 启窗口签名 0（另有 2 次非窗口签名已登记遗留②）。

## 第 1 轮进展（08:00–10:27，停止时快照）

> 用户 10:27 裁定：**停止本任务、合并结论后重派**。本节只固化已得事实；未回退、未提交、未再跑任何构建/QEMU/门控。完成区与第 1 轮自审为停止前所写、保持原样；状态已改 `待返工`。

**1. 可复现手段与实测触发率**
- 手段：新探针 `tests/unit/linux/amb_window_probe.py`，用例 `window` 把交付点**钉在 umon 返回桩「重开源位 → 寄存器恢复」之间**：先关源位并等 `cfx_hart cg8 rc5` 的 ISTATUS 到期，再在该处打开源位 ⇒ 投递必然落在窗口第 n 条（同一镜像 = `m45_entry_probe` 的用户任务，30 次返回/启）。关键认识：交付是**电平触发**，窗口概率≈掩码关闭跨度/周期，固定空转钉不住。
- 修前（真 pre-fix 代码：6 文件 cp 备份 → 换回旧版 → 重建）：`--case window --boots 3` ⇒ **3/3 红**，签名 `die 0xe4`、`K3 pf … va=0x208`、被中断指令 `ldm.o {rb1:rb2}, [rb3, rd1]`（`rd1=0x208`、`rb3=0`）、SP=内核栈、`ip=0x2000015xxxx`（umon 桩内）。日志：运行期证据目录 `log/prefix_pinned_window_3.boots.log`。
- 修前天然发生率（无注入）：`--soak 1000` ⇒ **13/1000 启红（1.3%）**，13/13 同一窗口签名 `va=0x208`（日志 `log/prefix_natural_soak1000.log`）——比 022 记载的 ~1/475 高约 6 倍（m45 镜像返回更密）。
- 现有修法（下方 §3）后：同一钉住用例 **3/3 绿**（窗口内投递 ≈70 次/30 返回，用户态投递照常）；天然 `--soak 2000` 两次：一次 **2 红（非窗口签名，见 §5）**、一次 **0 红**；另 `--soak 300` 0 红 ⇒ 窗口签名 **0/4000**。

**2. 已试的修法与取舍**（本轮只试了 §3 一条；022 的两条未重复）
- §3 的 `escape` 复位法：前述钉住/天然/两路保护缺失注入均按预期（见 §3、§4），**未发现回退**；它未被否，只因用户裁定停止而停在「已实现并自验、未走独立复核」。
- 022 已试并否决的两条（本任务**未重复**，仅登记）：差值跳转 ⇒ `check-linux-k2` irq 组 8/90；把 `reopen` 移到最后 ⇒ K5 228–255/282。

**3. 已实现的修法（已重建、已自验，未提交）**
- 根因：旧系统态返程以 `set.rb rb3, 0; jump [rb3, rd3, 0]` 收尾 ⇒ 被中断现场 `rb3`（umon/smon 桩帧基址）被清零；窗口投递恢复的第一条 `ldm.o` 即零基址取帧（`va=0x208`）。
- 修法：系统态返程改走本内核私用的 `cfx_jmon` supv 帧。`init_IRQ()` 在开源位前安装该行（`supv_switch_run_mode`=supv、`supv_excp_vector`=`dadao_async_kernel_resume`，回读，失败码 `K2_FAIL_RESUME_VECTOR/MODE`=0x16/0x17），并放开 jmon supv `cfxtrap` bit15 与 smon supv `cfxreg` bit1。返程：`trap cfx_jmon, 0` → 跳板写 `cg5 rc0/rc1/rc3`（捕获的运行模式/当前 cfx/返回目标）→ `DADAO_GPR_RESTORE_AT_KEEP_RD2_RB3` → 重开源位 → 从**帧外** resume 区（帧前 48 B）补 `rd2`/`rb3` → `escape cfx_jmon, [excp_cause_ip, 0]`（**返回不占任何寄存器**）。窗口=“重开+escape”；resume 区在帧外 + 入口在 `prev_cfx == cfx_jmon` 时不覆写 ⇒ 跳板自窗口内再投递幂等。退役 `DADAO_SMON_FROM_ASYNC_KERNEL`、`dadao_async_kernel_return`、`dadao_async_kernel_handoff()` 与 `trap.S` 的 `rd4` 借用。
- 已知未清项：~~跳板里仍保留一句旧设计的 `set.rb rb8, dadao_async_save`~~ —— 第 2 轮收口已删除（见「第 2 轮 engineer 自审」R1），并重导出/重编译/最小复验。

**4. 保护缺失注入（均 `cp`+md5 还原，日志在运行期证据目录）**
- `window-clobber-rb3`（返程在 `escape` 前写 `rb3`）⇒ **2/2 红**：`die 0xe4`、`va=0x208`（即 022 的原始签名）。
- `window-no-escape`（用软件跳转代替 `escape`，cfx 不恢复）⇒ **1/1 红**：`die 0xe7`（CFXPERM，`ip` 落在 `sched_clock_read`）。
- `nested`（跳板自窗口内钉住）⇒ **2/2 绿**（`irq_kernel≈70/30`）；`nested-no-chain`（去掉 `prev_cfx==cfx_jmon` 判据 + 同一钉住）⇒ **2/5 红**（`rc=124` 挂起，概率性：能否落地取决于嵌套投递点）。
- 三次还原共 7 次 md5 断言全 OK（`run.sh` 的「0 bad」项）。

**5. 未闭合的失败签名与已知现场**
- **ISS-539 的 LTP 侧无法复跑**：`m18-linux-006` 套件镜像在本环境**启动即 die**：`cause=CFXMEM(0x10000000000002)`（低位 bit1 `CFXMEM` + 高位 bit52 `DGPTRAP`，违反扁平不变式）、`va=0x20020000000`、`ip=0x20000115c00`、`ptbr=0x0`、`sp=0x20000814040`，落在内核 K1 ptw `pre` 用例。`m18-linux-006` 自己 `061155` 那跑**在 main 树同签名**（日志 `log/ltp_006_baseline_console.log` 第 8 行）⇒ 与本任务改动无关、是既存阻塞；本 worktree 同签名见 `log/ltp_this_tree_console.log`。
- 修后 4000 启中出现 **2 次非窗口签名红**：① `soak boot 78` 静默停摆（`rc=124`，最后一行 `Memory: … available`，日志 `log/post_soak2000a_boot78_stall.log`）；② `soak boot 1974` 在 `handle_softirqs` 内 `ld.ut rd4, [rb4,0]` 以坏 percpu 指针 `rb4=0x204002130f4` 取数 ⇒ `PTWMEM/DGPTRAP die 0xe4`（日志 `log/post_soak2000a_boot1974_softirq_die.log`）。两次都发生在 `/tmp` 100% 满的时段；其后 2000 启 0 红。**未归因**，需重派后单独立项。
- `ISS-539` 判断：`MALIGN ip=dadao_async_excp+0x1fc info=0xfffeffff7fff` 的 `info`= `~(TIMER|PMEM)` 掩码字被当地址、`ip` 在异步桩自身窗口 ⇒ 与「窗口投递恢复时现场被污染」**同族**，本次修法覆盖其机制；但**LTP 侧未取证**，不能宣称闭合。

**6. 已改动文件清单与状态**（均**已重建**并跑过门控；**未提交**）
- `components/linux/patches/arch/dadao/kernel/async_trap.S.patch`（返程跳板/resume 区/链规则；已验证）
- `components/linux/patches/arch/dadao/include/asm/entry.h.patch`（`DADAO_GPR_RESTORE_AT_KEEP_RD2_RB3`；已验证）
- `components/linux/patches/arch/dadao/kernel/irq.c.patch`（jmon 行安装/掩码/回读；已验证）
- `components/linux/patches/arch/dadao/kernel/trap.S.patch`（删 handoff selector 与 `rd4` 借用；已验证）
- `components/linux/patches/arch/dadao/kernel/traps.c.patch`（删 `dadao_async_kernel_handoff`；已验证）
- `components/linux/patches/arch/dadao/include/asm/trap.h.patch`（选择器退役、`dadao_async_kernel_resume` 声明；已验证）
- `components/linux/changelog.md`（本任务条；已验证）
- `tests/unit/linux/amb_window_probe.py`（新探针，六用例；已验证）
- 状态：源树 `.work/source/linux`（运行期）干净、`base+1` 单提交（内容 = 上列补丁集，`check-patch-tree` rc=0）；本任务工作树 `git status` 仅上列 8 项 + 本任务书；**未提交、未推送**。
- 停止前已通过的门控（均为**该字节完全相同的内核源**）：`check-linux-k2` 170/170 ×5 rc=0、`check-linux-k5` 285/285 ×5 rc=0、`check-linux-k6` 82/82 ×5 rc=0、`check-patch-tree` rc=0（linux 105 patches/0 problem）、`check-config-pins` PASS、`check-component-changelog` PASS、`check-tests-index` PASS、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`k5_signal_probe` 30/30 绿（117/117 每跑）、证据 `run.sh`（fast）7/7 PASS rc=0。

### 第 2 轮 engineer 自审（收口轮）

**范围**：`async_trap.S`（删死存 `set.rb rb8`）、补丁重导出、最小复验（window 3/3、K2/K5/K6 各 1 次、500 启）、完成区/遗留同步。**未改任何判据、未加长跑、未提交 git。**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 跳板里残留旧设计死存 `set.rb rb8, dadao_async_save`（jmon 路径无 C 半，`rb8` 不被任何人读） | ✅已修 | 删该指令并把注释改为「不传帧指针，跳板自己从 `dadao_async_save` 重载」；用户路径 `.Lasync_handoff` 的 `set.rb rb8` 保留（smon C 半的帧参数，必需） | 源树 `base+1` 单提交（`da9bc59`）、干净；`make_patch.py linux` **1 written / 104 unchanged**（series 105 不变）；`check-patch-tree` rc=0、linux 105 patches、0 problem；`make linux-vmlinux` rc=0（code-range PASS，exec_span 3582536 B）；`window` **3/3 绿**（69/30） |
| R2 完成区数字需与收口后样本一致 | ✅已修 | 测试结果行改为「×5 + 收口各 1 次」、窗口 0/4800、`run.sh` 两轮 PASS（477 s / 657 s）、文件清单注明 `async_trap.S.patch` 再改 1 处 | 本轮日志 `round2_gates_once.txt`、`round2_window_3boots.log`、`round2_soak500.log`、`round2_run_fast.log` |
| R3 遗留②只写了「两例未归因」，与样本量不符（收口 500 启又出 1 例同签名） | ✅已修 | 改写为三条台账：样本构成 300+2000+2000+500、频率 3/4800≈1/1600、签名（`handle_softirqs` 内 percpu 指针，`va=0x204002130f4`/`0x10`）、盘满时段标注、日志位置 | `round2_unattributed_reds.txt` + boot-181 完整 console |
| R4 三条未归因红的处置决定 | ⏸登记（不修） | 理由：故障 `ip` 在通用内核 `handle_softirqs`、不在任何返回桩的恢复点，`va` 与 `rb3`（帧基址）无关 ⇒ 与窗口 die 非同签名；修前 1000 启样本此类 0 例（同率预期 ~0.6，不构成证伪）；本任务范围为窗口，不扩范围 | 修后 4800 启窗口签名 0；三类样本分别 0/2/0/1 红 |
| R5 收口后 `run.sh` 全量需重跑 | ✅已修（重跑） | 无改脚本；fast 全量 + 200 启 soak | `RESULT: PASS` rc=0，477 s，7/7 检查（含 `va=0x208` 签名断言、三路保护缺失红、7 次 cp+md5 还原 0 bad） |
| R6 约束核验 | ✅已查 | 工作树仅 8 项改动 + 本任务书；未提交/未推送；未动 QEMU/spec/契约/Makefile；未放宽判据；未起第二个长跑批（同一时刻只有本条收口批） | `git status --porcelain`；`pgrep -af 'worktree/687cc5/m18-linux-024/'` 空 |

**判决**：R1/R2/R3/R5/R6 已修，R4 已登记；窗口缺陷收敛（修前钉住 3/3 红 → 修后钉住 3/3 绿，天然 13/1000 → 0/4800），门控全绿；三条非窗口红明确不属本任务、登记另立。

### 第 3 轮 engineer 自审（返工：交付缺陷）

**范围**：`tests/unit/linux/amb_window_probe.py`（共享 `.config` 快照/复原）、运行期证据脚本 `run.sh`（门控顺序 + 只判 linux 段 + 结尾复原断言）、`.tao/knowledge/issues-m18.yaml`（`ISS-542`→`ISS-m18-001`）、本任务书。**未改内核补丁、未动 QEMU/spec/契约/Makefile、未改判据、未提交 git。**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| A1 共享 `.config` 串味（architect 门控发现）：探针把 `CONFIG_INITRAMFS_SOURCE` 钉成 `""` 且不恢复 ⇒ 后续 K5/K6 继承空 rootfs | ✅已修 | 探针 `main()` 首次构建前快照该行、`finally` 调 `restore_shared_config()` 复原；入口已是 `""` 时改走 `make_defconfig` 生成器把它修成 cpio 路径；该复原本身是一条探针内断言（失败会让探针 rc=1） | `run.sh` 7/7 PASS 后紧接 `check-linux-k5` **rc=0 285/285**、`check-linux-k6` **rc=0 82/82**，`.config` 仍为 `…initramfs.cpio` |
| A2 「不恢复 ⇒ 红」可达 FAIL（证明缺陷真实、修复有效） | ✅已演示 | 不改探针第二次：用既有 `m45_entry_probe.py --boots 1`（同样钉空且不恢复）制造现场 | `check-linux-k5` **rc=2、255/285、30 FAILED**（S 组 `/init.musl` e_entry 红）；`make linux-defconfig` 后复跑 **rc=0、285/285**；日志 `round3_fail_demo_step{1,2,3,4}_*` |
| A3 `run.sh` 判据过宽：check#1 判 `check-patch-tree` 全局 rc，merge 带入 `m16-qemu-006` 的陈旧 qemu 源树（6 problem）⇒ 永远红 | ✅已修 | 只断言 **linux 段**（`linux: N patch(es)`，N 由 `series` 现场派生，且该行 0 problem）；全局 rc 打成 `[INFO]` 不判 | `run.sh` 输出 `[INFO] check-patch-tree global rc=2 (not judged)` + `[CHECK] patch-tree: linux 段 105 patch(es) / 0 problem … PASS` |
| A4 内核门控与探针的先后顺序 | ✅已修 | `run.sh`：`make linux-defconfig` → patch-tree → **K2/K5/K6（默认各 1 次、`--long` 各 5 次）** → 六用例探针 → soak → 结尾再 `make linux-defconfig` 并断言符号复原；脚本头注释写明「探针把 initramfs 钉空、构建树是共享的」 | `run.sh` **7/7 PASS rc=0**、535 s（`[INFO] probe rc=0 :: va=0x208 hits=2, 三路红=3/3, md5 还原失败=0, .config 复原=1/1`） |
| A5 issue 号改分册形：`ISS-542` → `ISS-m18-001` | ✅已修 | `issues-m18.yaml` 该条 id 就地改名（不动其它字段/位置）；本任务书遗留④ 引用新号 | `check_issues` **rc=0**（105 open / 90 closed / 195 entries，无重复 id）；`check-knowledge-refs` **rc=0** |
| A6 文档订正：`--no-verify` 归因写错 | ✅已修 | 新发现⑦ 改为实际原因：本 worktree 缺 `.cache/refs/riscv-unified-db`，共享 `pre-commit` hook（prek 生成，`--cd=".cache/refs/riscv-unified-db"`）ENOENT ⇒ 提交需 `--no-verify`，与 `ISS-510` 无关 | 本条；hook 原文见 `.git/hooks/pre-commit` 第 13 行 |
| A7 完成区数字与文件清单需按本轮更新 | ✅已修 | 测试结果行改为第 3 轮（`run.sh` 7/7/535 s、afters-run k5/k6 绿、FAIL 演示 rc=2→rc=0）、历史轮次并列；新发现 ⑤⑥⑦、遗留④ 补登 `ISS-m18-001` | 本节 + 完成区 |

**判决**：A1/A3/A4/A5/A6/A7 已修，A2 已演示；本轮只动 3 个允许文件（探针、`issues-m18.yaml`、任务书）+ 运行期证据脚本；`run.sh` 7/7 PASS rc=0，紧随其后的 K5/K6 复跑全绿，共享 `.config` 不再被钉空。

### 第 4 轮 engineer 自审（L1 回归修补）

**范围**：`tests/unit/linux/amb_window_probe.py`（复原路径改走生成器）、本任务书。**未动内核补丁/其它门控/判据；未提交 git。**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| B1 第 3 轮引入 L1 回归：探针调 `defconfig.apply_config_lines([快照行])` 而 `check-config-pins` C2 要求「调它必须声明 `CONFIG_PINS`」⇒ rc=1 | ✅已修 | `restore_shared_config()` **一律**跑生成器子进程 `tools/linux/make_defconfig.py`；删 `from tools.linux import make_defconfig as defconfig` 与该调用；`shared_initramfs_line()` 快照只作断言输入（复原后必须含 `initramfs.cpio`、不得为 `""`）；docstring 写明「本模块不声明 `CONFIG_PINS`（复用 m45 切片）」 | `make check-config-pins` **rc=0**（93 项，C2 不再列本探针）；文件内 `apply_config_lines` 的 AST `Call` 计数 = 0（仅 docstring 文字） |
| B2 复原路径改动后的功能复验（避免只修静态门控） | ✅已修（复验） | 无额外改动 | `--case baseline --boots 1` **rc=0**（`baseline boot 1: green, async=15`）、`--case window --boots 1` **rc=0**（`irq_kernel=68/30`），两次都 `[PASS] 共享 .config 已复原`；`.config` 仍为 `…initramfs.cpio` |
| B3 复验后是否串味 | ✅已查 | — | 紧接 `check-linux-k5` **rc=0 285/285**、`check-linux-k6` **rc=0 82/82** |
| B4 L1 全量是否与基线一致 | ✅已查 | — | `make check` **rc=2**，与基线日志 `diff` **0 行**：仍只停 `check-patch-tree: 6 problem(s)`（既有 qemu 段，非本任务） |
| B5 证据脚本需按新复原路径重跑 | ✅已修（重跑） | run.sh 未改（第 3 轮已把门控排在探针前、结尾断言复原） | `run.sh` **7/7 PASS rc=0**，1036 s（`probe rc=0 :: va=0x208 hits=2, 三路红=3/3, md5 还原失败=0, .config 复原=1/1`） |
| B6 文档 | ✅已修 | 新发现⑧（C2 规则与「复用 m45 切片⇒不声明 CONFIG_PINS」的修法）；完成区测试结果行补第 4 轮数字 | 本节 + 完成区；`check-knowledge-refs` rc=0、`check-tasks` rc=0 |

**判决**：B1 已修并复验（静态门控 + 功能 + 串味 + L1 逐行一致），B2–B6 已查/已重跑；本轮只动 2 个允许文件，串行单批，无残留进程。

### 第 3 轮 reviewer 验收

**重跑记录（本人执行，真实退出码）**
- 运行期证据目录内 `run.sh` → **7/7 PASS、`RESULT: PASS`、`EXIT=0`**：patch-tree linux 段（`series=105` 现场派生、0 problem）、`check-linux-k2 170/170`、`k5 285/285`、`k6 82/82` 各 1 次全绿、六用例探针 `20/20 passed`（`window` 2/2 绿且 `irq_kernel=68–69/30`、`window-clobber-rb3` 2/2 红 `die=0xe4, pf-va=0x208`、`window-no-escape` 1/1 红 `die=0xe7`、`nested-no-chain` 3/5 红 `rc=124`）、`--soak 200` 0 红、共享 `.config` 复原断言 PASS
- **修前/修后对照（本人做）**：6 份内核补丁换回 `b535a8b7^`（与 merge-base 逐字节同），源树 `revert → reset --soft → apply_series` 重建 → `--case window --boots 3` ⇒ **3/3 红**（`die=0xe4`、`pf-va=0x208`、`rc=228`）；全部还原（`cp`+md5、`git status` 空、源树 `base+1` 干净）后 ⇒ **3/3 绿**（`irq_kernel=66–81/30`）
- **独立稳定性**：本人 `--soak 300 --jobs 12` ⇒ **窗口签名 0**；2 次非窗口红（`pf-va=0x10` / `0x204002130ec`，`addr2line` → `handle_softirqs`，`ip=0x20000161578` 与 `ISS-m18-001` 登记案例同）
- **本人注入**：`irq.c` 的 `cfx_jmon` 向量写改 `0UL` → `--case window` **2/2 红**（`rc=22`＝`K2_FAIL_RESUME_VECTOR`）→ `cp`+`md5sum -c` 还原 → 复跑 **3/3 绿**
- 静态门控：`check-config-pins` 93 项 `rc=0`、`check-tests-index` 504 条 `rc=0`、`check-tasks rc=0`、`check-knowledge-refs rc=0`；`make check`（本任务态）与基线（merge-base 内容＋同源树序列）**逐行 diff 0 行**，两者均 `EXIT=2`、唯一红 `check-patch-tree: 6 problem(s)` 全在 `qemu:` 段（linux 105 patch/0 problem）
- 配置卫生：探针后紧接 `check-linux-k5 285/285 rc=0`、`check-linux-k6 82/82 rc=0`，共享 `.config` 的 `CONFIG_INITRAMFS_SOURCE=…initramfs.cpio`

**根因/修法核对**：旧 `set.rb rb3, 0; jump [rb3, rd3, 0]` 只剩注释（可执行 0 处）；`DADAO_SMON_FROM_ASYNC_KERNEL`/`dadao_async_kernel_return`/`dadao_async_kernel_handoff` 全树 0 处；`trap.S` 的 `rd4` 借用已随 handoff 删除（余下均为 cause 比较/`PT_IP` 取数）；新路径 `init_IRQ()` §1b 在开源位前装 `cfx_jmon` supv 行＋回读（`0x16/0x17`）＋jmon cfxtrap bit15/smon cfxreg bit1 → `trap cfx_jmon,0` → `dadao_async_kernel_resume`：写 `cg5 rc0/rc1/rc3` → `DADAO_GPR_RESTORE_AT_KEEP_RD2_RB3` → 重开源位 → 帧外 resume 区补 `rd2/rb3` → `escape cfx_jmon`；`prev_cfx==cfx_jmon` 链规则在位。

**约束核验**：相对 merge-base 恰 **10 文件**（6 补丁＋changelog＋探针＋任务书＋issues）＝完成区声明；无 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL 改动、无版本号变更；未 push；完成区 13 行 ≤30；状态 `待验收`；`git status` 空、源树 `base+1` 干净。**无任何重试**（`run.sh`/两探针 retry 计数 0，探针注释写明 "no retry here on purpose"）⇒ 绿不靠重试；`ISS-m18-001` 已按分册形登记（3/4800、boot 78/1974/181、签名与台账位置齐）。

**判决：Needs Revision**
1. **证据脚本恒真（唯一阻断）**：`amb_window_probe.py:419` 的还原断言把 `ok` 写死 `True`（`write_bytes` 原始字节后再比 md5，构造上恒真）⇒ `run.sh` 的 `md5 还原失败=0` **无可达 FAIL 路径**，验收项「`cp`+md5 还原」在脚本内不可证（AGENTS §4：每条断言须有可达 FAIL、禁恒真）。改 `ok = (md5(path) == before)` 并重跑 `run.sh` 即可；实际还原我已独立佐证（`git status` 空、md5 快照一致、后续绿用例与 soak 正常）。
2. （文档级）`components/linux/changelog.md` 本条写 `K5 282/282、K6 71/71 连跑 5 次`，与实测 `285/285`、`82/82` 不符，随返工订正。
3. （不阻断，留证）本人 300 启 soak 出现 2 次非窗口红（0.67%，高于 issue 登记的 3/4800≈0.06%；当时 `load avg≈7–8`、多会话 gem5/QEMU 并发）；`addr2line` 证明故障 `ip` 在 `handle_softirqs`、`va=0x10` 与登记案例同 ⇒ 同族非窗口；建议 issue 补记负载条件与频次区间。⑨ **证据脚本的断言必须能失败**：第 3 轮 `run_case` 的 `finally` 把还原判据写死为 `rep.check(…, True, before, md5(path))`（`ok` 是字面 `True`），「先写回快照再比 md5」构造上恒真 ⇒ reviewer 指出 `run.sh` 的「md5 还原失败=0」无可达 FAIL。修法：`ok = (md5(path) == before)`（快照为注入前字节；顺序＝取注入后字节 → 写回快照 → 比 md5），并把「注入后」md5 打进 actual 供肉眼对账；注入「写回时多加一字节」⇒ 7 条还原断言全红、`run.sh` rc=1。

### 第 5 轮 engineer 自审（恒真断言 + 文档订正）

**范围**：`tests/unit/linux/amb_window_probe.py`（还原判据）、`components/linux/changelog.md`（K5/K6 计数）、`.tao/knowledge/issues-m18.yaml`（`ISS-m18-001` title 补一句）、本任务书。**未动内核补丁/spec/契约/Makefile；未提交 git；单条串行。**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| C1（阻断）`run_case` 的还原断言恒真：`rep.check(…, True, before, md5(path))`，先写回快照再比 md5，构造上永真 ⇒ `run.sh`「md5 还原失败=0」无可达 FAIL | ✅已修 | `injected = md5(path)`（注入后）→ `path.write_bytes(blob)`（写回注入前快照）→ `restored = md5(path)` → `ok = restored == before`；actual 里同时打印「注入后」md5 供对账 | 修后 `run.sh` **7/7 PASS rc=0**（858 s，`md5 还原失败=0`）；**可达 FAIL 演示**：把写回改为 `blob + b"\n"` ⇒ 探针 7 条还原断言全红（例 `want='ab69a5b7…' got='fa531f73… (注入后 6b8a8604…)'`）、`run.sh` **RESULT: FAIL rc=1**（`md5 还原失败=7`）；`cp`+md5 还原探针与 2 个被污染的源文件后重跑回绿（源树 `git status` 干净） |
| C2 `changelog.md` 本条计数与实测不符（写了 282/282、71/71） | ✅已修 | 改为 `check-linux-k2` **170/170 ×5**、`check-linux-k5` **285/285 ×5**、`check-linux-k6` **82/82 ×5**（连跑 5 次全绿、逐次 rc=0） | 本任务书第 2/3/4 轮记录与 `round2_*`/`round3_*` 日志；`check-component-changelog` rc=0 |
| C3 reviewer 独立 300 启出现 2 次同族非窗口红（0.67%，load≈7–8、多会话并发），高于我方 3/4800 | ✅已记录（不新建条目） | `ISS-m18-001` title 末尾补一句：「reviewer 300 启（load≈7–8、多会话并发）2 次同族非窗口红（0.67%）；频率随负载变化，登记为区间而非单点」 | `check_issues` 直接跑 rc=0（195 条、无重复 id）；`check-knowledge-refs` rc=0 |
| C4 复验链（静态门控不能再漏） | ✅已查 | — | `check-config-pins` **rc=0**、`check-tests-index` **rc=0**、`check-tasks` **rc=0**、`check-knowledge-refs` **rc=0**、`check-component-changelog` **rc=0**；`make check` rc=2 且与基线 **diff 0 行**（既有 qemu 6 problem）；紧接 `check-linux-k5` **rc=0 285/285**、`check-linux-k6` **rc=0 82/82** |

**判决**：C1/C2/C3 已修/已记录，C4 全绿；本轮只动 4 个允许文件，无残留进程。

### 第 4 轮 reviewer 验收

**重跑记录（本人执行，真实退出码；只验本轮 4 文件变更）**
- **恒真已消除（读码＋独立注入双证）**：`run_case` 还原段现为 `injected = md5(path)` → `path.write_bytes(blob)` → `restored = md5(path)` → `ok = restored == before`，`actual` 打印 `"{restored} (注入后 {injected})"`。**我自设注入**：把写回改成 `path.write_bytes(blob + b"X")` → `--case window --boots 1` ⇒ **`[FAIL] window: 还原 trap.S（cp + md5）want='1c7fdf48…' got='bbe722ee… (注入后 4558c17a…)'`、探针 `EXIT=1`（3/4）**；`cp`+`md5sum -c` 还原探针与被污染的 `trap.S` → 复跑 **`[PASS] 还原 …`、`4/4 passed`、`EXIT=0`**；`git status` 与源树均空。
- **`run.sh` 全量重跑**：**7/7 检查、0 failed、`RESULT: PASS`、`EXIT=0`**；耗时 **14:54:33→15:11:34 ≈ 1021 s**（load 高于 engineer 的 858 s）；关键行 `[INFO] probe rc=0 :: va=0x208 hits=2, 三路红=3/3, md5 还原失败=0, .config 复原=1/1`，`--soak 200` 0 红，patch-tree linux 段 105/0、`k2/k5/k6` 各 1 次全绿。
- **文档一致**：`components/linux/changelog.md` 本条已改为 `check-linux-k2 170/170 ×5`、`check-linux-k5 285/285 ×5`、`check-linux-k6 82/82 ×5`（该行是 changelog 唯一改动）；`ISS-m18-001` title 补记「reviewer 300 启（load≈7–8、多会话并发）2 次同族非窗口红（0.67%）；频率随负载变化，登记为区间而非单点」；第 5 轮自审 C1–C4 与其可达 FAIL 演示（`blob + b"\n"` ⇒ 7 条红、`run.sh FAIL rc=1`）与我方独立注入结论一致；完成区 13 行 ≤30、状态 `待验收`。
- **门控**：`check-config-pins`、`check-tests-index`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog` 全 **`EXIT=0`**；`make check` **`EXIT=2`**、唯一红 `check-patch-tree: 6 problem(s)`（既有 qemu 段），与基线日志 **逐行 diff 0 行**。

**范围核验**：`git diff fd6b422c^ fd6b422c --name-only` 恰 **4 文件**（`issues-m18.yaml`、本任务书、`changelog.md`、`amb_window_probe.py`）；**内核补丁在本提交 0 改动**；无 spec/契约/Makefile/其它组件；无版本号变更；未 push；`git status --porcelain -uall` 空、源树 `base+1` 干净。

**判决：Accepted**
- 上轮唯一阻断（还原断言恒真）已按要求修复，并经我独立注入证明**可达 FAIL**（红）与还原后**回绿**；本轮 4 文件变更范围、文档计数、六项门控与基线 diff 全部核过，未发现新 finding。
