# m14-linux-008: K2 中断使能与屏蔽（`local_irq_*` → 两级 mask 的软件旋钮）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-007`（有真实 `TIMER` 才能观测「屏蔽窗口内不推进」）、`m14-spec-005`（§6 内核侧 IE 口径）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：与 `m14-linux-006`/`007`/`009` **必须串行**（同组件单写者；本任务改 `irqflags.h` 与 007 的 tick 路径相交）；`m14-spec-005` 必须先完成（§6 第 4 条即本任务的判据来源）
**预估**：2–3 h
**档位**：大改（组件改，代码量小；复核按大改取证、≥4 路注入）
**状态**：待开始

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

1. **`flags` 的宽度口径**：Linux 约定 `flags` 为 `unsigned long`；本机可直接放整条 mask 寄存器（64 位）。若将来 mask 语义扩展到多寄存器，`flags` 需重新定义 ⇒ 本任务按「整条 `cg2 rc4` 值」实现并在注释里写明该假设。
2. **`local_irq_enable()` 的粒度**：建议「清掉内核关心的源位」（保留其它位原值，不做全清 0），以免把固件/后续阶段的其它源策略一并抹掉；若用户要求「`enable` = 全开」需明确（会与 K4 的源管理冲突）。
3. **临界区是否要覆盖 `escape` 前的帧改写**：建议不要（`escape` 是控制转移，不是可中断点），本任务只在注释里写明该边界。

## 审阅记录

（待填）
