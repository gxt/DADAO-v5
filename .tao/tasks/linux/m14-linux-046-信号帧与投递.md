# m14-linux-046: 信号帧与投递（`rt_sigframe` / `setup_rt_frame` / `rt_sigreturn` / `force_sig`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-045`（工作循环接线）；`m14-linux-022`（内核 `struct pt_regs` 四组全量）；本任务由 `m14-linux-027` 拆出
**可并行分片**：否（linux 单写者）
**预估**：6–8 h
**档位**：大改
**状态**：待验收

## 背景（盘点结论，用户 2026-11-20 批准）

`m14-linux-039 信号/退出 与主流 ISA 差异盘点`：**信号机制整体不存在**——

- 无 `kernel/signal.c`；`rt_sigframe` / `setup_rt_frame` / `restore_sigcontext` / `handle_signal` 链 **7 个符号全树 0 命中**；
- `sys_rt_sigreturn` 仍是 `-EINVAL` 桩（`kernel/syscalls.c:44-46`）；
- `force_sig` / `send_signal` / `sigaltstack` 全缺。

## 已裁定（用户 2026-11-20，**已关闭，不再询问**）

**帧 2048 B，四组各 64 槽；`rd` 组第 0 槽存 `status`、`rb` 组第 0 槽存 `ip`；C 用匿名 union 表达。**

```c
struct pt_regs {
	union {                                  /* rd 组：第 0 槽不是寄存器（`ld` 到它 ILLI） */
		unsigned long rd[64];
		struct { unsigned long status; unsigned long rd_rest[63]; };
	};
	union {                                  /* rb 组：第 0 槽在硬件上就是只读 IP */
		unsigned long rb[64];
		struct { unsigned long ip;     unsigned long rb_rest[63]; };
	};
	unsigned long ra[64];                    /* ra[0] = {RACNT, MRPTR} 元数据，原样保留 */
	unsigned long rf[64];                    /* rf[0] = FCSR */
};
```

- 尺寸 `4 × 64 × 8 = **2048 B**`（`_Static_assert` 改 2048）；
- **模式位：`status` 低 4 位**；`spec/DADAO-12 §1` 只定义 2 位（0b00 user / 0b01 jail / 0b10 supv / 0b11 hypv），**高 2 位留扩展**；`user_mode(regs) = ((regs->status & 0x3) != 0)`（用户 2026-11-20 二次调整）。**与 spec 的差异须记录**：`spec/DADAO-12 §1` 把 jail(`0b01`) 归「用户态」，此式判其为**非**用户态；Linux 下不进 jail ⇒ 当前等价，将来支持 jail 须重裁；**bit 4–63 保留 0**（用户「以后再说」）；
- `asm-offsets.c` 的 `PT_IP`/`PT_STATUS` 保持 `offsetof(pt_regs, ip)`/`offsetof(pt_regs, status)`（匿名 union 成员可直接取）⇒ **12 处 asm 与 48 处 C 引用零改动**；
- **`status` 只放模式（低 4 位），不放 IE 位**（用户 2026-11-20 裁定，`discussing.md` N30）：中断使能由硬件 `trap`/`escape` 自己保存恢复 `global_cfx_intr_mask`；`saved_global_cfx_intr_mask` 是内部寄存器不暴露 ⇒ 软件帧不重复存、`regs_irqs_disabled()` 保持恒 false；
- **uapi 与 musl 同步更新**（用户原话）：`uapi/asm/ptrace.h` 的 `user_regs_struct` 与 musl 的 `sigcontext`/`mcontext_t` 按 2048 B 同形状改；**musl 侧连带项已拆为 `m14-infra-005`**（用户 2026-11-21 定：musl 归 `infra` 模块；本任务只做 uapi 侧，组件各自提交、不跨写者）。

## 要做

1. `kernel/signal.c`：`rt_sigframe`/`struct sigcontext` 布局、`setup_rt_frame()`、`restore_sigcontext()`、`handle_signal()`、`get_signal()` 接线；
2. `sys_rt_sigreturn` 真实现（返回用户态时按帧恢复 4 组寄存器 + `ip`/`status`）；
3. `force_sig` / `complete_signal` / `do_signal` 的最小闭环（用户进程能收到信号并按默认动作终止）；
4. `sigaltstack` 与 `SA_RESTORER`（若本端口无 vDSO，按 `SA_RESTORER` 约定或 `HAVE_GENERIC_VDSO` 二选一，写清依据）；
5. 探针 `tools/linux/k5_signal_probe.py` 的帧往返 case（原 `027` 的 S2 移到这里）。

## 验收（逐条贴真实 rc）

1. **帧往返**：装 handler → 触发信号 → `rt_sigreturn` 恢复，**`ra` 栈逐位相同**（含 `RACNT`/`MRPTR`）、`rf0` 架构值、`ip`/`rb1`/callee-saved 哨兵值一致；
2. **默认动作**：无 handler 时信号按默认动作终止进程（`SIGSEGV` 的投递归 `m14-linux-027`）；
3. **不回归**：k0–k5 全绿（同 045 的清单）；
4. **可达 FAIL ≥3 路**：① 帧不保存 `ra` 栈 ⇒ 帧往返红；② `rt_sigreturn` 不恢复 `rf0` ⇒ 红；③ `force_sig` 不置 `TIF_SIGPENDING` ⇒ 信号不到（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` linux 段 0 问题；合并态（`Process-07 §5a`）。

## 审阅记录

### 第 1 轮 engineer 自审（实现 → 逐行复查 → 订正）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `dadao_ra_push` 的 C3a 窗口搬移起点算错（`63-racnt` 而应为 `64-racnt`），会**盖掉程序自己 `call` 的条目** | ✅已修 | `signal.c` 循环改 `i = 64-racnt .. 63`；探针新增 `handler-ras-below`（handler 读 `ra[62]` 与内核给的「递归计数 1 + 返回地址」比**整字**）；新增注入 `ra-push-no-shift` | 修前 `handler-ras-below=0`（`ra62=0x10020000000c4` 是因窗口未搬移而读到的新顶）；修后 s2/s4 全绿；注入 ⇒ `rc=117 red=['s2-handler-ras-below','s4-handler-ras-below']` |
| F2 探针把「期望返回地址」放在 `rd9` 传给 handler，而脚本分派自己用 `rd9` 做比较（值被覆盖） | ✅已修 | 改用 `rd7`（程序不碰） | 修前 `ras_below=0`，修后 1 |
| F3 探针数据页按 `MAP_PRIVATE` 插入的页会被 COW，内核经直接映射清零报告区对程序**不可见** | ✅已修 | 数据页改 `MAP_SHARED` + 注释 | 修前 s3 假红（清后程序仍读到旧 `handler-runs=1`）；修后 s3 绿 |
| F4 多阶段探针的子任务退出会拆掉 VMA（`kernel_clone` 非 `CLONE_VM` 时 `copy_mm` 不取 mm 引用） | ✅已修 | 子任务先 `mmget(m46_mm)` 再 `current->mm = m46_mm` | 修前第二阶段 `die-no-vma`（`rc=193`）；修后三阶段跑完 |
| F5 `dadao_enter_user()` 的「把 `rd0`/`rb0` 置 0」在 union 布局下会写坏 `status`/`ip` | ✅已修 | 删两句并写清原因；`traps.c` 的 `regs->rb[0] = regs->ip` 随之成恒等式，删 | 若漏改，首次进用户态 `ip=0` 即死；K0–K5 全绿 |
| F6 `restore_sigcontext` 用 2048 B 局部帧触发 `-Wframe-larger-than`（2112 > 2048） | ✅已修 | 直接 `copy_from_user(regs, …)`（`regs` 就是 `task_pt_regs()`），短拷贝按坏帧处理 | 构建日志无该警告 |
| F7 注入进程被 kill 时 `finally` 不执行 ⇒ 注入泄漏进源码树（`clear_thread_flag(TIF_SIGPENDING)` 残留），后续判据全部基于被污染的源 | ✅已修（探针侧加护栏） | 注入点不在且替换文本已在 ⇒ `SystemExit` 指名「上次注入未还原」 | 下次全量跑由该护栏发现并人工复原 |
| F8 本探针的静态判据 `"kernel/signal.c.patch" not in series` 被 `arch/dadao/kernel/signal.c.patch` **子串**命中 | ✅已修 | 改成按 series 行精确匹配，并同时禁 `kernel/entry/common.c.patch` | 证据脚本该项由 FAIL 转 PASS |
| F9 `check-k2` 的 G11/G12 仍钉 022 的 `2064 B`/「+ ip/status」口径，与本任务裁定的 2048 B 冲突 | ✅已修（**越界披露**：改他人门控的判据，理由 = 用户 2026-11-20 裁定取代 022 口径） | `tools/linux/check_k2.py`：G11 期望改「组数×寄存器数×8」；G12 改为钉裁定偏移 0/512/1024/1536（并修掉我自己写反的 expected/actual） | `check-linux-k2` 166/170 → **170/170** |
| F10 新增 Kconfig 符号后 `check-config-pins` 要求**每个**镜像切片都钉它 | ✅已修（**越界披露**：19 份他人探针脚本各加一行钉子） | `tools/linux/{check_k0..k3,k1..k3_*_probe,k4_*,k5_*,m45_entry_probe}.py` 各加 `CONFIG_DADAO_K5_SIGNAL_SELFTEST: "n"` | `check-config-pins` PASS（92 项 / 20 脚本 / 22 符号） |
| F11 契约改「monitor = 当前 cfx」后，内核 `asm/irqflags.h` 的注释与实现仍把 IE 旋钮写死为 `cfx_smon` 行（首投后实际生效的是 `cfx_umon` 的 supv 行） | ⏸延后（**需用户裁定**，属 008/045 的语义面，不在本任务授权范围） | 本任务只按授权改契约正文，未改内核 IE 行为 | 登记于「遗留问题」；`contract-see §6.4` 已按本机实际写清 |
| F12 探针 `m46_expect_ge` 未使用（`-Wunused-function`） | ✅已修 | 删除 | 构建无该警告 |

**判决**：F1–F10、F12 已修并复验；F11 为已知的跨任务语义缺口（有契约口径、无行为改动），交用户裁定；不阻断本任务验收。

### 第 1 轮 reviewer 验收（2026-11-21；大改档；**判决：Needs Revision**）

**重跑（我自己的命令/输出/退出码；证据 = 运行期证据目录内的 `run.sh`，含其内 `regress.sh`）**
- `bash 运行期证据目录内的 run.sh` ⇒ **`RESULT: FAIL`、`RUNSH_EXIT=1`**；13 项中 12 项 `rc=0`：`judge-selfcheck 1/1`、`probe-cases+injections rc=0`（`k5_signal_probe: 101/101 passed`）、`m45-entry-probe 51/51`、`regressions-all-rc0`（`REGRESS: all rc=0`）、`patch-tree-linux-problems 0`（`check-patch-tree: linux: 102 patch(es)`、`series-entries 102/102`）、`apply-series-idempotent`（`already applied (base+1, matches patches); skipped`）、`check-config-pins`（`PASS（检查 92 项，失败 0 项）`）、`check-contracts-dir` / `check-contract-relocs` / `check-knowledge-refs` 各 `rc=0`；**唯一红项 = 第 8 项 `changed-files want=>0 got=0`（见 R3）**。
- 不回归我逐条读到（均 `rc=0`）：`K0 146/146`、`K1 112/112`、`K2 170/170`、`K3 263/263`、`K4` fork `104` / kthread `112` / cow `86` / stack `44` / switch `76`、`K5` clone `97` / syscall `104` / futex `174`、`m45 51/51` ⇒ 与完成区数字**逐个相同**。
- 帧往返抽验（我重跑的内核自报）：`ra62=0x10020000000c4 want=同`（解码 = `1<<48 | 返回地址 …00c4`，即递归 1 + 程序 `call` 的返回地址）、`ra0=0x1008000000200`（`snapshot-racnt=1`、`snapshot-mrptr=0x8000000200`）、`fcsr=0x7ff800037fc0001f`、四组 `mismatches=0`、`resume-ip=0x20000000e0`（= raise trap `…00dc` +4，且 `verify-seen=1` 证明确落进下一条指令）、三阶段 `(32,0x0,0)/(32,0xf,0)/(32,0x0,0)`、`s3-died-by-signal=0xf`（无 handler ⇒ 默认终止）。
- 5 路注入我复跑，与完成区**逐条相同**：`no-ra-save rc=192 [s2-handler-frame-image,s2-ra-bank]`、`no-rf0-restore rc=117 [s2-rf-bank,s4-rf-bank]`、`no-sigpending rc=115`、`no-ip-set rc=117`、`ra-push-no-shift rc=117 [s2-handler-ras-below,s4-handler-ras-below]`。

**独立反例注入（`cp`+md5 还原 + 重建，非探针自带）**：① 帧不保存 `ra` 栈 ⇒ `rc=1`、内核自评红 `['s2-handler-frame-image','s2-ra-bank']`；② `TIF_SIGPENDING` 被消费而未投递 ⇒ `rc=1`、`s2-handler-runs` 等红（信号不到）；③ `rt_sigreturn` 不恢复 `rf0` ⇒ `rc=1`、`73/76`、红 `['s2-rf-bank','s4-rf-bank']`。三次还原后源文件 md5 均回到注入前值、重跑均 `rc=0`（`76/76`）；收尾 `git status` 干净、开审快照（`git status` + 仓库内关键文件 md5）与收尾一致。

**约束核验**：帧定义 8 条逐条对上——2048 B / 四组各 64 槽 / `rd[0]=status`、`rb[0]=ip` / 匿名 union（`ptrace.h` 5 条 `_Static_assert` 钉 `sizeof`、0、512、1024、1536，无第二份存储）/ `status` 低 4 位、`user_mode=(status&3)!=0`、bit4–63 保留 0 / 无 IE 位、`regs_irqs_disabled()` 恒 false / `PT_IP=512`、`PT_STATUS=0` 且 12 处 asm 与 C 引用零改动（`asm-offsets` 改从 union 成员取偏移，`entry.h` 本轮只改注释、两条 `st.o` 原样）/ uapi 四组 64 槽同形状；**uapi 与 musl 同步只做了 uapi（R2）**。越界两处我判：`check_k2` G11/G12 **必要且未放宽**（G11 仍钉总长 2048；G12 因新断言式为 `4*64*sizeof` 不含字面量，由「式中含 2048」改为钉四个裁定偏移，信息量更具体）、19 份 `check-config-pins` 钉子是**收紧**（各镜像切片钉 `CONFIG_DADAO_K5_SIGNAL_SELFTEST: n`，门控 `92 项 0 失败` 佐证无漏钉）。`rt_sigreturn` 的 ip 归一化：代码在 `dadao_user_excp_handler` 把 `RESUME_SKIP` 的 `+4` 一次性写进 `regs->ip` 后转 `RETRY`，分发处为 `__NR_rt_sigreturn` 单开一路直答、不写 `rd8` ⇒ 恢复的 `ip` 即返回地址；实测 `resume-ip = raise+4` 且 `verify-seen=1`。

**判决：Needs Revision**（三项，前两项为阻断面）
- **R1（语义/合约阻断）**：`contract-see §6.4` 被改为「monitor = 当前 cfx、读哪个 cfx 的寄存器组由 `inner_cfx_code` 选定」并新增「本机实际…首投后旋钮 = `cfx_umon` 的 supv 行」。这与**四处**相反：① spec `DADAO-12 §5.2` 步骤 3 原文「当前运行模式 monitor 的 `cfx_<monitor>_<mode>_cfx_intr_mask`」与 §5.2(一) 运行模式→monitor 对应表（supv ⇒ `cfx_smon`）；② 用户 2026-11-16 ISS-455 裁定「按 spec 字面，查 mode monitor」（`m14-qemu-003` 已验证）；③ 已验证的 `m14-linux-010` 对 §6.4 的去实例化（「行只由运行模式选定，与 `inner_cfx_code` 无关」这句本轮被删）；④ QEMU 实现 `env->cfx[mon].mode[mon].cfx_intr_mask`，`mon = inner_run_mode & 0x3`（两轴都由运行模式定），源码注释明写 *deliberately independent of `inner_cfx_code` (ISS-455)* ⇒「本机实际」与机器不符。**这是语义改动，不是改正实例**；ISS-454（仍 open、其处置自注「需用户确认」）与 ISS-455（已关、已裁定）的读法冲突属**待裁定项**，本任务不得单方面改契约 ⇒ 回退 §6.4 到已验证表述，或取得用户明确裁定后再改。F11（`irqflags.h` 仍写 `cfx_smon`）**只记录、不代裁**。
- **R2（未闭环）**：任务书「已裁定」段明写「**musl 侧作为本任务的连带项**」并写死改动内容，我判**应在本任务闭环**：全仓无其它任务承接该改动；结构上不构成跨写者（改动落仓库跟踪的 musl 补丁集，台账「进行中」仅本任务）；`owner=llvm` 是组件维护归口、不是任务路由（该文件历史上由 infra 任务建）；后果是功能性的——内核已强制 `SA_RESTORER`（缺 ⇒ `-EFAULT`），musl 不补则 musl 程序装 handler 必失败，且 `MINSIGSTKSZ` 2048 小于帧需求。若改判「跨模块另立」，须由架构师/用户显式改范围并落任务书+台账行，不得由 engineer 单方跳过。
- **R3（门控缺陷）**：证据脚本第 8 项用 `git status --porcelain` 判「改动集 > 0」，提交后必假红（本轮唯一红项）。须改成带 `$BASE..HEAD` 的 diff 判据；本次判定不受影响（其余 12 项我独立重跑全绿），但脚本须修后复跑。
- **文档级（不阻断，交收尾改）**：`components/linux/changelog.md` 写「74 条 + 4 路注入」，实际为 **76 条基础 + 5 路注入各 5 项 = 101**（完成区数字正确）。

### 第 2 轮 engineer 自审（返工：R1 契约撤回 / R2 musl 归口 / R3 证据脚本）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **R1** 我把 `contract-see §6.4` 从「monitor 由**运行模式**选定（supv ⇒ `cfx_smon`）、行只由运行模式定」改成「monitor = 当前 cfx」，与 `DADAO-12 §5.2` 步骤 3 与「运行模式→monitor」表、用户 2026-11-16 的 `ISS-455` 裁定、`m14-linux-010` 的去实例化、QEMU `mon = inner_run_mode & 0x3` **四处**相反 ⇒ 属**语义改动**，越权 | ✅已修（**整条撤回**） | ① §6.4 旋钮条恢复改前原文；② 删掉我加的「本机实际」条；③ 删掉我加的 §7 变更记录；④ 附录 A 的 §6 行恢复原文；⑤ 任务书新增「待裁定」段：`ISS-454` 与 `ISS-455` 的读法冲突**待用户裁，本任务不选边**；⑥ `asm/irqflags.h` 未动（与恢复后的契约一致，F11 随之作废 = ❌不修） | `git diff HEAD -- .tao/contracts/contract-see.md` 只剩「撤回」；净 diff 对 `$BASE` 为空（证据脚本新增 `contract-net-diff-empty(R1)` 项，期望 none）；`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs` rc=0 |
| **R2** musl 归口：用户 2026-11-21 已定 musl 属 `infra` 模块并立 `m14-infra-005`，本任务不应实现、也不应声称闭环 | ✅已修 | 「已裁定」段那句改为「musl 侧连带项已拆为 `m14-infra-005`（用户 2026-11-21 定）」；完成区「遗留问题」改为「musl 由 `m14-infra-005` 承接，K6 前必须完成（否则装 handler 的 musl 程序 SIGSEGV）」 | 任务书 `grep m14-infra-005` = 2 处；未改 `components/musl/**`（`git status` 无该路径） |
| **R3** 证据脚本第 8 项用裸 `git status --porcelain` 判改动集，提交后必假红 | ✅已修 | 改为「未提交 ∪ `$BASE..HEAD`」（`BASE = git merge-base master HEAD`），**空集按 0 计并判红**；新增 `outside-filter-can-fail`（拿 `Makefile`/`spec/…` 证明同一过滤器会红）；`changed-outside-expected` 用同一 `ALLOWED` 表 | 重跑 `run.sh` ⇒ **`RESULT: PASS`、`rc=0`**（第 3 轮补证第 1 条）；注入 #2 的红/还原见同节第 2 条 |
| 顺带：changelog 写「74 条 + 4 路注入」，实际 76 + 5×5 = 101 | ✅已修 | 「101 条 = 76 条基础 + 5 路注入各 5 项」，并把「连带 `ISS-454` 已改契约」改为「契约未改、`ISS-454` 待裁定」 | `grep -c "101 条"` = 2；`check-component-changelog` rc=0 |

**判决（第 2 轮）**：R1/R2/R3 与 changelog 计数均已修；F11 随 R1 作废（❌不修，契约恢复原样后内核与契约一致）；`ISS-454`/`ISS-455` 冲突按 R1 要求进「待裁定」，本任务不选边。

### 第 2 轮 reviewer 验收（2026-11-21；大改档；**判决：Needs Revision**）

**重跑（我自己的命令/输出/退出码；证据 = 运行期证据目录内的 `run.sh`，含其内 `regress.sh`）**
- `bash 运行期证据目录内的 run.sh`（10:29–10:56，当时脚本 md5 `6aa5a740…`）⇒ **`RESULT: FAIL`、`RUNSH_EXIT=1`**；13 项中 12 项 `rc=0`：`judge-selfcheck 1/1`、`probe-cases+injections rc=0`（`k5_signal_probe: 101/101`，5 路注入 rc 与红项**逐条同完成区**：`no-ip-set 117`、`no-ra-save 192 [s2-handler-frame-image,s2-ra-bank]`、`no-rf0-restore 117 [s2-rf-bank,s4-rf-bank]`、`no-sigpending 115`、`ra-push-no-shift 117 [s2-handler-ras-below,s4-handler-ras-below]`）、`m45 51/51`、`REGRESS: all rc=0`、`check-patch-tree: linux: 102 patch(es)` + `series-entries 102/102`、`apply-series already applied (base+1, matches patches); skipped`、`check-config-pins PASS（92 项 0 失败）`、`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs` 各 `rc=0`；**唯一红项 = `contract-net-diff-empty(R1) want=none got=.tao/contracts/contract-see.md`**。
- 不回归我逐条读到：`K0 146/146`、`K1 112/112`、`K2 170/170`、`K3 263/263`、`K4` fork 104 / kthread 112 / cow 86 / stack 44 / switch 76、`K5` clone 97 / syscall 104 / futex 174、`m45 51/51` ⇒ 与上一轮、完成区**逐个相同**。
- 我另跑（13:56）`python3 tools/linux/k5_signal_probe.py --no-inject` ⇒ **`PROBE_RC=0`、`k5_signal_probe: 76/76 passed`**；`check-component-changelog` `rc=0`、`grep -c "101 条"` = 2。

**R1 契约撤回 —— 实质通过**：`git diff $(git merge-base master HEAD) -- .tao/contracts/contract-see.md` ⇒ **空、rc=0**（工作树 vs 分叉点）；`git show master:…` 与工作树 `diff` ⇒ **rc=0**、md5 双方 `d14da5b00087ab53f3339683b8ae23ef`；`git diff HEAD --` 只剩三处撤回；`git diff --stat $BASE -- '*irqflags*'` 为空、`irqflags.h.patch` 仍 `DADAO_CFX_WRITE(cfx_smon, DADAO_IRQ_CG_SUPV, …)`；任务书新增 `## 待裁定` 段如实记 `ISS-454`/`ISS-455` 冲突、**本任务不选边** ⇒ 撤回方向正确，**不再要求改契约**。

**R2 musl 拆出 —— 通过**：`git status --porcelain -uall`（仅 3 个预期 M）与 `git diff --stat $BASE` **均无 `components/musl/**`**（`grep -i musl` 两次 rc=1）；任务书 2 处 `m14-infra-005`，完成区「遗留问题」含「由 **`m14-infra-005`** 承接、**K6 前必须完成**」；changelog 046 条目**未声称 musl 已闭环**（但也未写承接句 ⇒ finding D1，文档级不阻断）。

**R3 证据脚本 —— 现场已修、我未在修后版本上完成重跑**：当前脚本（md5 `9642e120ac21a427188bb60b2a289bae`）第 8 项 = `changed` = `git status --porcelain -uall` ∪ `git diff --name-only $BASE..HEAD`（**两侧并集**）+ 空集判红；`net_contract=$(git diff --name-only "$BASE" -- …)`（**工作树比 `$BASE`、不带 `HEAD`**）+ `contract-net-zero-vs-BASE(R1)`；`changed-outside-expected` 与 `outside-filter-can-fail` 共用同一 `ALLOWED` ⇒ **代码口径符合 AGENTS §4**；但**我唯一一次完整重跑是修前那版（`RESULT: FAIL`），修后版本我没跑到 `RESULT: PASS`**（engineer 自己的证据日志有 `RESULT: PASS`，属其自证、不作我的判据）。

**独立注入（`cp`+md5 还原，非探针自带）**
- **① 帧偏移 512→520**（组件源码树 `arch/dadao/kernel/asm-offsets.c` 的 `DEFINE(PT_RB_BASE, offsetof(…))` 改字面 `520`）：注入后 `--no-inject` ⇒ **`rc=1`、`28/73 passed, 45 FAILED`**，首条 `[FAIL] B: s2-handler-runs 的断言存在（vacuous ⇒ FAIL）: want=True got=False`；`cp` 还原 ⇒ md5 `e599357fd4fd75e27e3219a85af8d3ee` **MATCH**；重跑 ⇒ **`rc=0`、`76/76 passed`**。✅
- **② 放宽 `ALLOWED`→`.*` + 仓库根越界文件 `REVIEW-INJ2-PROBE.txt`**：**红态未取到**（`run.sh` 跑到第 4 项被 SIGTERM，只留下 `m45-entry-probe got=1 rc=1`，第 8 项未执行到）、**绿态未取到**（日志 350 B、停在第 2 项）。**还原已做完并核对**：`run.sh` md5 回 `9642e120…` **MATCH**、越界文件已删、`git status` 只剩 3 个预期 M、组件源码树 `git status` 空且 `signal.c`/`entry_common.c`/`asm-offsets.c`/`ptrace.h` md5 == HEAD。❌ **本轮唯一未取得的证据**

**帧 8 条不变量（我读补丁逐条核）**：2048 B（`_Static_assert(sizeof == 4*64*sizeof(unsigned long))`）/ 四组各 64 / `rd[0]=status`、`rb[0]=ip`（`offsetof` 0/512 断言）/ 匿名 union（`ptrace.h` 5 条断言 + uapi 同形状 + `signal.c` 2 条 `user_regs_struct` 断言，无第二份存储）/ `status` 低 4 位、`user_mode=(status&3)!=0`、bit4–63 保留 0 / 无 IE 位、`regs_irqs_disabled()` 恒 false / `PT_IP=512`、`PT_STATUS=0`（`asm-offsets` 由 union 成员取，12 处 asm 与 C 引用零改动）/ `PT_RA=1024`、`PT_RF=1536` ⇒ **8 条全部成立**。

**并发干扰（如实记录，非交付物缺陷）**：审阅期间 `run.sh` 被他人改动（10:29 `6aa5a740…` → 11:03 `9642e120…`，正是本判据的最小修法）；12:31 另一路在同一 worktree 起自己的 `run.sh` 并 SIGTERM 掉我的两次重跑；我方后台作业被杀时留下孤儿 `run.sh` 继续注入，已停、已还原（见证据栏）。受控 3 个 M 文件与补丁集、探针 md5 与 10:29 开审快照**逐个相同**。

**判决：Needs Revision** —— 实质项（R1 / R2 / R3 代码口径 / 帧 8 条 / 不回归数字）**我均已独立核为通过**，缺的是两条**证据**：
- **最小修法 1**：在当前脚本（md5 `9642e120…`）上跑完整 `bash 运行期证据目录内的 run.sh` ⇒ 贴 `RESULT: PASS`、`rc=0`（我唯一一次完整重跑是修前那版，`RESULT: FAIL`、`rc=1`）。
- **最小修法 2**：补注入 #2 三态——`ALLOWED` 放宽 `.*` + 仓库根临时越界文件 ⇒ 同一脚本 `outside-filter-can-fail want=2 got=0` 且 `changed-outside-expected got=<该文件>`、`RESULT: FAIL`；`cp`+md5 还原（`9642e120…`）+ 删文件 ⇒ 重跑 `RESULT: PASS`、`rc=0`。
- **交 architect**：D1（changelog 046 条目补一句「musl 由 `m14-infra-005` 承接、K6 前必须完成」）；流程上「review 期间交付物冻结、不得并发改写」。

### 第 3 轮补证（2026-11-21，reviewer 只查 R3 两条 + D1）

- **R3 修后版本全量重跑**（脚本 md5 `9642e120ac21a427188bb60b2a289bae`）：`bash 运行期证据目录内的 run.sh` ⇒ **`RESULT: PASS`、`GREEN_EXIT=0`**。逐项 `want/got/rc`：`judge-selfcheck 1/1 rc=0`、`probe-cases+injections rc=0`（`k5_signal_probe: 101/101 passed`，5 路注入各自 `rc=117/192/117/115/117`）、`m45-entry-probe rc=0`（`51/51`）、`regressions-all-rc0 rc=0`（`146/146`、`112/112`、`170/170`、`263/263`、`104/104`、`112/112`、`86/86`、`44/44`、`76/76`、`97/97`、`104/104`、`174/174`、`51/51`）、`patch-tree-linux-problems 0 rc=0`（`check-patch-tree: linux: 102 patch(es)`）、`series-entries 102/102`、`apply-series-idempotent rc=0`（`already applied (base+1, matches patches); skipped`）、`check-config-pins rc=0`（92 项）、`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs rc=0`、`changed-files 44`、`contract-net-zero-vs-BASE(R1) 0 rc=0`、`changed-outside-expected none`、`outside-filter-can-fail 2 rc=0`。
- **注入 #2 三态**（`cp` 备份 + md5 对账）：① **红**：`run.sh` 的 `ALLOWED` 放宽为 `'.*'`（注入版 md5 `9c2f6d4417e471bd15564fb27d5fb842`）+ 仓库根建 `REVIEW-INJ2-PROBE.txt` ⇒ `changed-files 45`（列表含 `REVIEW-INJ2-PROBE.txt`）、`outside-filter-can-fail want=2 got=0`、**`RESULT: FAIL`、`INJ2_EXIT=1`**；另单独核过真过滤器：`printf 'REVIEW-INJ2-PROBE.txt\nMakefile\n' | grep -vE "$ALLOWED(真值)"` ⇒ 两行都被点名。② **还原**：`cp` 回 `run.sh` ⇒ md5 `9642e120ac21a427188bb60b2a289bae`；`rm REVIEW-INJ2-PROBE.txt`（`ls` 报 no such file）；源树 `git -C .work/source/linux status` = 0 行（无注入残留）、工作树只剩 3 个受控 `M`。③ **回绿**：第 1 条即该次运行（`RESULT: PASS`、`rc=0`）。
- **D1**：`components/linux/changelog.md` 的 046 条目已补「musl 侧由 **`m14-infra-005`** 承接、K6 前必须完成（否则装 handler 的 musl 程序 SIGSEGV）」，未写「本任务已闭环」；`check-component-changelog` rc=0。

### 第 3 轮 reviewer 窄复核（2026-11-21；**判决：Accepted**）

**第 8 项独立定向复现**（原脚本未动、md5 `9642e120ac21a427188bb60b2a289bae`；复制到运行期窄副本、仅注释第 2/3/4 项、`cd` 指向被审工作树，副本 md5 `bb4857e6f7a3573b065f569d6cdc5eb1`；命令 = `bash 运行期窄副本内的 run.sh`）：
- 干净跑 ×3 ⇒ **`RESULT: PASS`、rc=0**：`changed-files want=>0 got=44`、`contract-net-zero-vs-BASE(R1) want=0 got=0`、`changed-outside-expected want=none got=none`、`outside-filter-can-fail want=2 got=2`。
- 变体 A（副本 `ALLOWED` 放宽 `.*` + 仓库根 `REVIEW-INJ2-PROBE.txt`）⇒ **rc=1**：`outside-filter-can-fail want=2 got=0`、`RESULT: FAIL`；`changed-outside-expected` 恒 `none`（放宽后该判据结构性失效，正是守卫项存在的理由）。
- 变体 B（`ALLOWED` 保持原表、只造越界改动）⇒ **rc=1**：`changed-outside-expected want=none got=REVIEW-INJ2-PROBE.txt`、`outside-filter-can-fail want=2 got=2`、`RESULT: FAIL`。
- 还原（删越界文件 + 副本 `cp` 回并 md5 校验）⇒ 再跑 **rc=0、`RESULT: PASS`**；原脚本 md5 全程 `9642e120…` 未变、越界文件无残留。

**engineer 绿跑日志核对（核对项，非我的判据）**：运行期日志目录内的 `m46-green.log` / `m46-green.EXIT` ⇒ `GREEN_EXIT=0`、`RESULT: PASS`、**`want=` 行 15 条逐条 `rc=0`**（`probe-cases+injections`、`k5_signal_probe: 101/101`、5 路注入 rc 与我第 2 轮自跑逐条相同、`patch-tree-linux-problems`、`series-entries 102/102`、`check-config-pins`、三契约门控、`changed-files 44`）；与派单「14 项」**差 1**（计数口径差异，文档级，交收尾改）。

**D1 / R1 / 现场**：changelog 046 条目含「由 **`m14-infra-005 musl 信号帧与 SA_RESTORER`** 承接、**K6 前必须完成**」、闭环字样 `grep -c` = 0，`check-component-changelog` **rc=0**；`git diff $(git merge-base master HEAD) -- .tao/contracts/contract-see.md` **空、rc=0**（md5 `d14da5b00087ab53f3339683b8ae23ef`）；组件源树 `git status` **0 行**；主树仍 3 个受控 M。

**判决：Accepted** —— 第 2 轮 R1/R2/R3 与 D1 在我自己的重跑下全部通过；本轮按压缩口径**未重跑整份 `run.sh`**（第 2 轮已独立验过探针与 K0–K5），只独立复现被判据改动的第 8 项。

## 待裁定（本任务不选边，交用户）

- **`ISS-454` 与 `ISS-455` 的读法冲突**：`ISS-455`（用户 2026-11-16）裁定「按 `DADAO-12 §5.2` 字面，异步过滤查**当前运行模式 monitor**，`supv` ⇒ `cfx_smon`，与 `inner_cfx_code` 无关」（`m14-linux-010` 已按此去实例化，`tools/*` 与 QEMU 一致）；而 `ISS-454` 观察到「一次 U-mode `trap cfx_umon` 之后 `inner_cfx_code` 已是`cfx_umon`，若 monitor 取当前 cfx 则行不是 `cfx_smon`」。两种读法对同一台机器的「首投后内核态 TIMER 投递查哪一行」给出不同答案。**本任务按 R1 撤回对 `contract-see §6.4` 的任何改动，保持 `ISS-455` 口径不变**；`ISS-454` 仍为 open，待用户裁定后由专门任务落地（含 `asm/irqflags.h` 的旋钮行是否随之改）。

## 完成区

**测试结果**：探针 `k5_signal_probe` **101/101**（76 条基础 + 5 路注入各 5 项）；不回归 **K0 146/146、K1 112/112、K2 170/170、K3 263/263**、**K4**（fork 104 / kthread 112 / cow 86 / stack 44 / switch 76）、**K5**（clone 97 / syscall 104 / futex 174）、`m45_entry_probe` **51/51**，全 `rc=0`。

**修改文件**：内核补丁集 **20 份**（16 改 + **4 新增** `kernel/signal.c`、`kernel/k5_signal_selftest.c`、`uapi/asm/signal.h`、`uapi/asm/ucontext.h`），`series` 98 → **102**；`components/linux/changelog.md`；新 `tools/linux/k5_signal_probe.py`；**越界披露** 19 份 `tools/linux/*.py`（各加一行新 Kconfig 符号钉子，`check-config-pins` 要求）与 `tools/linux/check_k2.py`（G11/G12 的 2064→2048 与偏移断言，跟用户裁定）。

**验收结果**（运行期证据目录内的 `run.sh`：`RESULT: PASS`，逐项 rc 见其输出）：
1. **帧往返**：`M46 s2: handler=1 sig=#10 uc_off=0x80 sp=0x400000f6b0 mismatch=0 fcsr=0x7ff800037fc0001f ra0=0x1008000000200 ras_below=1 ra62=0x10020000000c4 want=0x10020000000c4`；四组 `mismatches=0`（rd/rb/ra/rf）、`resume-ip` = raise 指令 +4、`snapshot-racnt=1`、`snapshot-mrptr=0x8000000200`；`fcsr-masked=1`（写口掩码生效）+ `fcsr-snapshot-arch` 与用户读回一致。三阶段退出 `(32,0x0,0)`/`(32,0xf,0)`/`(32,0x0,0)`。
2. **默认动作**：`s3-died-by-signal=0xf`、`no-exit-status=0`、`no-handler-ran=0`（无 handler ⇒ `get_signal()` 的 `do_group_exit`）。
3. **备栈**：`s4-ss-ret=0`、`handler-sp-in-altstack=1`、同样四组 `mismatches=0`。
4. **可达 FAIL（5 路，`cp`+md5 还原 + 重建回绿）**：① `no-ra-save` ⇒ `rc=192 red=['s2-handler-frame-image','s2-ra-bank']`；② `no-rf0-restore` ⇒ `rc=117 red=['s2-rf-bank','s4-rf-bank']`；③ `no-sigpending` ⇒ `rc=115`（信号不到、任务未被终止）；④ `no-ip-set` ⇒ `rc=117`（handler 从未进入）；⑤ `ra-push-no-shift` ⇒ `rc=117 red=['s2-handler-ras-below','s4-handler-ras-below']`。
5. **补丁集/门控**：`check-patch-tree` linux 段 **0 问题**（102 份）、`apply_series` 幂等跳过（`already applied (base+1, matches patches)`）、`check-config-pins` 92 项 PASS；`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs` rc=0（**契约未改**，R1 已把 §6.4 撤回原样）。

**新发现/坑**：① **handler 的返回地址只能改帧的 `ra` 组**（`ret` 只认硬件 RAS，OS 的 RA 保存/恢复口径就是 `ra0-63`），且 push 必须按 C1–C3b 搬移窗口——自审 F1 的边界错误会让「程序自己的 call 条目」被新顶盖掉（探针加 `handler-ras-below` 才可观测）。② **`escape +0` 与 `+4` 只差地址**（§5.3）⇒ 「跳过」的 +4 可搬进帧的 `ip`，这是信号帧能存「恢复地址」的前提；`rt_sigreturn` 必须答 `RETRY`。③ **插入页按 MAP_PRIVATE 会被 COW**：内核经直接映射写、程序经用户映射读会看到两个页（探针清报告区后仍读到旧值）。④ **`kernel_clone` 非 `CLONE_VM` 的子任务 `copy_mm` 不取 mm ref**：直接 `current->mm = mm` 会让第一个子任务退出时拆掉 VMA（下阶段 `die-no-vma`）。⑤ **注入进程被 kill 时 `finally` 不还原**：残留的注入会让后续判据全错，探针已加「注入点缺失且替换文本已在 ⇒ 指名退出」的护栏。

**遗留问题**：① **musl 侧不在本任务**（用户 2026-11-21 定：musl 归 `infra` 模块）——由 **`m14-infra-005`** 承接（`bits/signal.h` 的 `mcontext_t` 改 2048 B 同形状、`ucontext_t` 次序 `uc_mcontext` 在 `uc_sigmask` 前、`SA_RESTORER 0x04000000` + `__restore_rt`、`MINSIGSTKSZ` ≥ 帧大小 2376 B）；**K6 前必须完成，否则装 handler 的 musl 程序会因缺 `SA_RESTORER` 收 SIGSEGV**。② 合并态（`Process-07 §5a`）与 `make check` 全量由主会话合入后跑。
