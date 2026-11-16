# m14-linux-008: K2 中断使能与屏蔽（`local_irq_*` → 两级 mask 的软件旋钮）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-007`（有真实 `TIMER` 才能观测「屏蔽窗口内不推进」）、`m14-spec-005`（§6 内核侧 IE 口径）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：与 `m14-linux-006`/`007`/`009` **必须串行**（同组件单写者；本任务改 `irqflags.h` 与 007 的 tick 路径相交）；`m14-spec-005` 必须先完成（§6 第 4 条即本任务的判据来源）
**预估**：2–3 h
**档位**：大改（组件改，代码量小；复核按大改取证、≥4 路注入）
**状态**：待验收

## 背景

K1 交付的 `arch/dadao/include/asm/irqflags.h` 是**恒 disabled 桩**（`arch_local_irq_save()` 返回 0、`arch_irqs_disabled()` 恒 1），注释写明「等 trap 入口落地再补」。K2 起有真实异步源，内核必须能进出临界区——否则 `timer_cmp` 的「读-改-写」、tick 计数更新、退出序列都可能被 `TIMER` 打断在半途。

硬件事实（`spec/DADAO-12 §3.1`/`§3.3`、`spec/DADAO-13 §1`、`contract-see §3`）：本机**没有状态寄存器 IE 位**，只有两级来源 mask——当前 cfx 的 `<mode>_cfx_intr_mask`（位索引 = **目标 cfxha**）与当前 mode monitor 的 `global_cfx_intr_mask`。因此软件 IE 必须映射到一个寄存器，且**不能**用 `global_cfx_intr_mask`：

- 异步帧建立时硬件把**当前 mode monitor** 的 `global_cfx_intr_mask` 置全 1、`escape` 时恢复并重踢 pending（`contract-see §3`「统一异步中断仲裁」）。若软件也把它当旋钮，`restore` 会与帧的保存/恢复互相覆盖；
- 用 `cfx_smon` 的 `supv` 行 `cfx_intr_mask`（`cg2 rc4`）则互不干扰：帧内软件「开中断」也不会真的嵌套（global 仍挡着），`escape` 后硬件恢复 global 并补投——这正是单核阶段想要的行为。

## 范围

1. **`arch/dadao/include/asm/irqflags.h` 真实现**（替换恒 disabled 桩）
   - 软件旋钮 = **按「当前 cfx」选行**的 `supv` 行 `cfx_intr_mask`（`cg2 rc4`）：正常运行期当前 cfx = `cfx_smon`（2）；**一旦有 cfx 投递过异常，当前 cfx 变成该 cfx**（`escape` 不恢复 `inner_cfx_code`，见 `ISS-454`；`m14-linux-007` 已按「两行都开」实现） ⇒ `save`/`restore` 必须同时覆盖 `cfx_smon` 与**投递过的 cfx**（如 `cfx_hart`）两行；`arch_local_irq_save()` = 读回当前值（作 `flags` 返回）后**置位**所有「内核关心的源位」；`arch_local_irq_restore(flags)` = 写回；**注意**：`ISS-455` 记录了一处未定口径（`spec/DADAO-12 §5.2` 步骤 3 写「源轴查 mode monitor 的行」，与 `ADR-0045 D3`/`contract-see §6.4`/QEMU「查当前 cfx 的行」不一致）。本任务按**两行都开**实现（对两读法皆成立、无副作用），并在完成区显式披露该未定项；
   - `arch_local_irq_disable()` = `save()` 丢弃返回值；`arch_local_irq_enable()` = 清掉「内核关心的源位」；
   - `arch_local_save_flags()` = 读回；`arch_irqs_disabled_flags(flags)` = 「`flags` 是否把内核关心的源位挡住」；`arch_irqs_disabled()` 同上；
   - 「内核关心的源位」= 运行期由 `m14-linux-007` 使能的源集合（当前只有 `TIMER` = `1 << 15`，位索引 = 目标 cfxha `15`）。**不得**把 `1 << 15` 硬编码散落在多处：集中为一个 `#define`/常量并注明来源（`spec/DADAO-12 §4.7` 的 `cfxha` + `contract-see §3` 的「位索引 = 目标 cfxha」）；
   - 语义边界写进注释：mask 只**阻止投递**，事件仍记在**目标 cfx** 的 `cg5 rc5` pending；解除后由硬件补投（`contract-see §3`），软件**不自建** pending 位图。
2. **首批消费者**：把 `m14-linux-007` 的「读 `cmp`/`rc5` → 改 → 写 `cmp`/`rc5`」与 tick 计数更新包进 `local_irq_save/restore`；退出序列（`stop` + `SYS_EXIT`）在屏蔽下完成。
3. **探针**（`tools/linux/k2_irq_probe.py`）
   - P1 往返：`save` 后物理寄存器（现场 `cfx2rd` 读 `cg2 rc4`）确实置位、`restore` 后逐位等于保存值（不是「看起来对」）；
   - P2 窗口冻结：屏蔽后等 ≥3 个 tick 周期，tick 计数**不变**且 `ISTATUS` 置位；解除后计数**恰增 1**（合并补投，不丢不多）；
   - P3 嵌套两层：`save` → `save` → `restore` → `restore`，最终 mask 与最初逐位相同，且中间层 `restore` 后仍屏蔽（最外层未恢复）；
   - P4 handler 内「开中断」不嵌套：在 tick handler 里 `restore` 到「允许」状态，观察同一帧内不再进第二次 tick（global 仍挡），`escape` 后补投；
   - P5 `irqs_disabled()` 与物理值一致：在 3 个不同 mask 状态下各断言一次（现场读寄存器比对，不用记录的影子变量）。
4. **文档**：`components/linux/changelog.md` 一条；`irqflags.h` 注释改写（去掉「K0 无中断源」的过时说明，写清单旋钮与两级 mask 的关系）。

## 验收（逐条贴真实 rc 与输出）

1. `make build-linux JOBS=32` rc=0；Vast 端到端 guest **rc=0**，且 `m14-linux-007` 的 tick 断言仍成立（屏蔽只包住临界区，不改变总 tick 数）；
2. 探针 P1–P5 全 PASS（计数现场打印）；P2 的「冻结窗口」与「补投 +1」各贴真实 tick 计数与 `ISTATUS` 读回值；
3. **可达 FAIL 注入 ≥4 路**（`cp` + md5 还原 + 重建）：① `arch_local_irq_restore` 写死 0（全开）⇒ P3 红（嵌套语义丢）；② 用 `global_cfx_intr_mask`（`cg8 rc1`）当旋钮 ⇒ P4 红（帧恢复与软件相互覆盖，出现异常 tick 数）；③ `irqs_disabled_flags` 的判据从「位与」改成 `flags == 0` ⇒ P5 红；④ 去掉临界区包裹 ⇒ P2 的窗口内计数出现漂移（贴真实漂移次数；若单核下偶发不漂，改用「在 `cmp` 写入前后人为拉长窗口」的变体并在完成区说明）；
4. `make check-linux-k0` rc=0、`make check-linux-k1` rc=0；
5. 补丁纪律：`make apply-series` 幂等、`make_patch.py linux` 重导出无 diff、`check-patch-tree` linux 段 0 问题、`--source-state` linux OK、`check-component-changelog` rc=0；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`spec/`/`contracts/`/`Makefile`/`tests/`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp` + md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁 + `changelog.md`）、`tools/linux/**`、本任务书；**不改** 固件（`tests/shared/bootrom/**` 归 `m14-linux-007`）、`spec/`、`contracts/`、QEMU。
5. 只在 `qemu-system vast` 上验收；不实现 IPI/SMP、不引入「每源独立使能位图」等超出 spec 的结构（`ADR-0052 D2`）。
6. `irqflags.h` 的语义必须能由 `cfx2rd` 现场核对；不得引入「影子变量缓存 mask」而让物理值不可观测。

## 待裁定

> **派单口径（2026-11-16）**：以下三条按各自的建议执行，不再等裁定 —— 1 = `flags` 取整条 `cg2 rc4`（注释写明假设）；2 = `enable` 只清内核关心的源位、保留各行其它位；3 = 临界区不覆盖 `escape` 前的帧改写（注释写明边界与理由）。

1. **`flags` 的宽度口径**：Linux 约定 `flags` 为 `unsigned long`；本机可直接放整条 mask 寄存器（64 位）。若将来 mask 语义扩展到多寄存器，`flags` 需重新定义 ⇒ 本任务按「整条 `cg2 rc4` 值」实现并在注释里写明该假设。
2. **`local_irq_enable()` 的粒度**：建议「清掉内核关心的源位」（保留其它位原值，不做全清 0），以免把固件/后续阶段的其它源策略一并抹掉；若用户要求「`enable` = 全开」需明确（会与 K4 的源管理冲突）。
3. **临界区是否要覆盖 `escape` 前的帧改写**：建议不要（`escape` 是控制转移，不是可中断点），本任务只在注释里写明该边界。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查，深度 1 不能起嵌套子代理）

审查范围：`irqflags.h`（全部内联函数）、`time.c` 的 tick/退出/边界钩子、`k2_irq_test.c` 全文、`Kconfig.debug`/`kernel/Makefile` 改动、`k2_irq_probe.py` 全文、`k2_time_probe.py` 的两处改动（C8 判据、`done` 行格式与新增断言）。判决：实现与探针逐条对齐「物理值现场读 + 探针独立判」，无影子变量；语义边界（mask 只阻止投递、`escape` 前帧改写不进临界区）在注释中写明。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `local_irq_save(flags)` 是语句宏（取左值），`flags = local_irq_save()` 编不过 | ✅已修 | 语句形式 + 需要返回值处用 `arch_local_irq_save()` | 5 个镜像全部编译通过（k0/k1/trap/time/irq） |
| P2「释放延迟」测量把已发生的补投误判成「等下一次 tick 超时」（假 5.1 ms） | ✅已修 | `k2_irq_wait_tick(绝对目标)` + 从 restore 之前计时 | `elapsed≈6.6e4 ns` ≪ `period/2=5e6` |
| 反例①预期过宽（认为 P1 也红）：`restore` 写 0 后基线塌成「全开」，P1 往返自洽 | ✅已修 | 收窄为 `("P3",)` 并在完成区说明原因 | `--inject` ① PASS |
| 反例②用运行期值无法判别：两行默认值相同且 `init_IRQ` 同位置位，旋钮接到 global 行后所有现场值仍自洽 | ✅已修 | 新增 C0 静态断言（`cg/rc == contract-see §6.4`、写入覆盖两行） | ② 变红 C0；另加 ②b 给出 P4 红 |
| 反例②b `want_rc=None` 触发 `hex(None)`，检查项被异常吞掉 | ✅已修 | 检查项按 `want_rc is not None` 构造 | `--only global-row-unmask` PASS |
| 反例⑤的 C0 判定被替换注释里的 `cfx_hart` 字样骗过（未变红） | ✅已修 | 匹配 `DADAO_CFX_WRITE(cfx_hart,` 而非裸名字 | ⑤ C0 变红 |
| `run.sh` 的 REPO 解析经 `.work` 软链落到主工作树（误写 6 个文件） | ✅已修 | 按 cwd 解析 + `master` 拒跑 | 主工作树 `git status` 干净、文件 md5 == HEAD blob；复跑 10/10 |
| 探针 P5 状态排序比较写错（tuple vs list） | ✅已修 | 两侧都 `sorted()` | 95/95 |
| `k2_time_probe` 的镜像切片没钉 `CONFIG_DADAO_K2_IRQ_TEST`，共享构建树把本任务 probe 镜像的 `=y` 泄漏进去（`--selfcheck` 首跑 6 个 C1/C3 问题） | ✅已修 | 其 `IMAGES` 增 `CONFIG_DADAO_K2_IRQ_TEST=n`；本任务 probe 与 k0/k1/trap 的切片已各自钉全 | `run.sh --selfcheck` 复跑 PASS |

### 第 1 轮 reviewer 验收（独立重跑，2026-11-16）

**重跑记录**（判决全部取自本人终端输出，未采信完成区）：证据脚本 `run.sh --gates` ⇒ **10/10、rc=0**（`check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` 95/95；apply-series `already applied`、`make_patch linux` `0 written, 69 unchanged`（补丁树 md5 前后同）、`check-patch-tree` 414 patches OK、`--source-state` linux OK count=1 clean=True、`check-component-changelog` rc=0）；`--selfcheck` ⇒ 2/2 rc=0；`--inject` ⇒ irq **6/6** + time **5/5** rc=0（逐路 cp+md5 还原、还原后回绿 0 失败）。
**真数（guest 原行，本人所跑）**：P1 `0xffffffffffff7fff → 0xffffffffffffffff → 0xffffffffffff7fff`（两行一致）；P2 屏蔽窗 `ticks=0 ctrl=0x5 window=30000000`、释放 `ticks=1 elapsed=91894 ns`；P3 `inner=0xffffffffffffffff`、内层 restore 后两行仍全屏蔽；P4 帧内 `waited_ticks=0 ctrl=0x5 elapsed=5034849`、帧后 `tick+1 gap=47019 ns`；P5 四态 disabled/flags_disabled 与现场寄存器逐条一致；退出 `done ticks=4 mask=0xffffffffffffffff`。
**约束核验**：① 两行真改 —— `save`/`restore` 走 `dadao_irq_mask_row_write()`（同时 `DADAO_CFX_WRITE(cfx_smon,…)` 与 `(cfx_hart,…)`），`disable`=save，`enable` 两行各自 RMW `& ~DADAO_IRQ_SOURCE_BITS`（非全清 0）；`flags` = 整条 64 位（`unsigned long`，注释写明假设）；`irqs_disabled_flags()` = 位与。② `1UL << 15` 来源正确：`contract-see §6.4`「mask 位索引 = 目标 cfxha（`cfx_hart` ⇒ bit 15）」+ `contracts/cfx-aliases.txt` `scalar cfx_hart 15`；cause `TIMER=1<<10` 是另一套编号（探针 C0 现场断言两者不同），头文件集中单点并注明来源。③ 旋钮路径无 `cg8/rc1`/`global_cfx_intr_mask` 写（全局搜仅命中注释；global 只在 `irq.c::init_IRQ` 一次性放行，本任务未改该文件）。④ `time.c` 读数-记账-`cmp`/`ctrl` 重挂整段在 `local_irq_save/restore` 内，退出序列 `local_irq_disable()` 在 stop+exit 之前，`escape` 前帧改写按派单口径 3 不包（注释写明边界与理由）。⑤ 越界 0：11 个文件全在 `components/linux/**`+`tools/linux/**`+本任务书，`tests/`/`spec/`/`contracts/`/`.tao/contracts/`/`Makefile` 改动为空。⑥ 安全：run.sh 按 cwd 推仓库根且拒 master（已核源码），主工作树审前审后 `git status --porcelain -uall` 均为空。
**≥4 路自设计注入**（cp+md5+重建+回绿，不复用它那 6 路）：m1 `save` 只读不写 ⇒ **P1/P2 红**（窗内 `ticks=3`）；m3 `restore` 永不放开 ⇒ **P2 红** + 客户机 rc=0x15；m5 退出序列去掉屏蔽 ⇒ **`k2_time_probe` 新断言红（2/151）**；m6 `arch_irqs_disabled()` 恒 0 ⇒ **P5 红** —— 4 路均有可达 FAIL，还原后回绿 0 失败。
**Finding（不阻断，交 architect 处置）**：① m2 把 `flags` 截成低 32 位 ⇒ **95/95 全绿**（现场 `before_smon=0xffff7fff`、`done mask=0xffffffff` 仍全过）——「`flags` = 整条 64 位」只有同轮相对比对、缺绝对锚点；建议 P1 增「`before_smon` == C1 init 行读到的 smon 值」（现场派生、不写死）。② m4 `enable` 全清 0 ⇒ **全绿**——派单口径 2「保留各行其它位」无可达 FAIL；建议 P5 增「enable 态 == disable 态 & ~源位」。③ `run.sh --inject` 步骤标签写「`k2_time_probe --inject (6 路)`」实为 5 路（步骤只判 rc，标签过时）。④ P2 只断言 ISTATUS、未断言 ENABLE（ENABLE 由 spec「ISTATUS 由 ENABLE 门控」间接成立）；P4 的 `gap < period/2` 阈值本身不充分（周期重挂那次 ≈ `period/2−ε` 也过线），真正排除靠帧内 `arm(1)` 写 `cmp` 取消旧 deadline + 序列超时 rc=0x15 兜底 —— 证据链够、阈值偏松。
**判决：Accepted** —— 验收 1–6 与硬约束 1–6 在本人重跑下全部成立；ISS-454 已由「两行」落实，ISS-455（spec §5.2 步骤 3「按运行模式 monitor 选行」vs §3.3/ADR-0045 D3/契约 §6.4「按当前 cfx」）经核属实、披露充分，属未决项不阻断。

## 完成区

**测试结果**：全绿。`check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` **151/151**（原 149 + 两条新增「退出序列在屏蔽下完成」；C8 首次触碰点随真实 `irqflags` 前移到 `start_kernel`，判据仍是「权限来自固件」）、`k2_irq_probe` **95/95**；`k2_irq_probe --inject` **6/6**、`--selfcheck` 9/9；`k2_time_probe --inject` 5/5（原 6 路，`only-smon-row` 退役）；`run.sh --gates` 10/10 步、`--selfcheck` 2/2 步。
**修改文件**：`components/linux/patches/arch/dadao/{include/asm/irqflags.h,kernel/time.c,kernel/Makefile,Kconfig.debug,kernel/k2_irq_test.c}.patch`、`components/linux/{series,changelog.md,README.md}`、`tools/linux/k2_irq_probe.py`（新）、`tools/linux/k2_time_probe.py`（镜像切片补钉 `K2_IRQ_TEST=n`、`done` 行加 `mask=`、C8 判据前移、`only-smon-row` 反例退役 6→5）、本任务书；未改固件/`spec/`/`contracts/`/QEMU/`tests/`。
**验收结果**（真实输出）：
- 补丁纪律：`make_patch linux` 重导出 `0 written, 69 unchanged`、`apply_series --component linux` = `already applied`、`check-patch-tree` `linux: 69 patch(es) … 414 patches OK`、`--source-state` `linux: OK count=1 clean=True`、`check-component-changelog` rc=0。
- P1 往返（两行现场值）：`0xffffffffffff7fff → 0xffffffffffffffff → 0xffffffffffff7fff`，`restored_{smon,hart} == flags`。
- P2：屏蔽窗 `window=30000000`（3 period）`ticks=0 ctrl=0x5`（ISTATUS=1）；释放 `ticks=1 elapsed=81335 ns`（≪ `period/2=5000000`）。
- P3：`inner=0xffffffffffffffff`，内层 restore 后两行仍全屏蔽，外层 restore 后回 `0xffffffffffff7fff`。
- P4：帧内 `waited_ticks=0 ctrl=0x5 elapsed=5033140`；`afterframe tick=frame+1 gap=44184 ns`（< period/2 ⇒ 是 `escape` 后补投，不是周期重挂）。
- P5：`disable(1,1) enable(0,0) save(1,0) restore(0,0)`，各态 `disabled` 与现场 `smon/hart` 一致、`flags_disabled` == `flags` 位与结果。
- 退出：`done ticks=4 mask=0xffffffffffffffff`（`stop` + `SYS_EXIT` 在屏蔽下完成）。
- 注入 6 路（`cp`+md5 还原+重建+回绿）：①`restore` 写 0 ⇒ **P3** 红（基线塌成「全开」后 P1 自洽，实测只 P3 红）；②旋钮接 `cfx_smon cg8 rc1` ⇒ **C0** 红（`(8,1)≠(2,4)`；运行期值自洽，故 P1/P2/P4 仍绿）；②b 帧内 restore 顺手清 global 行 ⇒ **P4** 红（同帧内第二次 tick、帧证据消失、`rc=0xEA` 异常终止）；③`flags == 0` 判据 ⇒ **P5** 红；④去掉 P2 临界区 ⇒ **P2** 红（窗内 `ticks=3`）；⑤只写 `cfx_smon` 一行 ⇒ **C0/P1/P2** 红（窗内 `ticks=3 ctrl=0x1`，`ISS-454` 直接判据）。
**新发现/坑**：⓪ 旋钮每次 save/restore 写两行 ⇒ `init_IRQ` 只开一行不再是单点故障，007 的 `only-smon-row` 反例失去可达 FAIL 路径（已退役，判据移入本任务反例⑤）；① `local_irq_save(flags)` 是语句宏（取左值），`flags = local_irq_save()` 编不过；② **寄存器身份只能静态判**——两行旋钮默认值相同、`init_IRQ` 同位置位，把旋钮接到 global 行后现场值仍自洽（动态检查全绿）⇒ 必须静态断言「`cg/rc` == 契约 §6.4」+「写入覆盖两行」；③ 量补投延迟须用**绝对 tick 目标**，否则补投已发生时会误测成「等下一次 tick」超时（假 5.1 ms）；④ 反例②b 复现契约点名的危害：帧内软件碰 `global_cfx_intr_mask` ⇒ 同帧内嵌套投递。
**ISS-455 披露（口径未定）**：`spec/DADAO-12 §5.2` 步骤 3 写「源轴查 **mode monitor 行**（按运行模式选行）」，`ADR-0045 D3`/`contract-see §6.4`/QEMU 实现查**当前 cfx 的行**；首投后两者不同（当前 cfx = 15）。本实现**同时写 `cfx_smon` 与 `cfx_hart` 两行**——前者即 supv 的 monitor 行、后者即首投后的当前 cfx 行 ⇒ 对两种读法皆成立、无副作用（多一次 `cfx2rc`）。口径本身仍未定，须 `m14-spec-005` 与契约 §6.4 同笔裁定后才能收敛为一行；`ISS-454`（首投后当前 cfx = 15）已由「两行」落实。
**遗留问题**：仅 `ISS-455` 口径未定（非本任务可裁）；另：任务书预期的「反例② ⇒ P4 红」实测只红 C0，P4 侧的红由 ②b 给出（见上）。
