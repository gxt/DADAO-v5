# m14-linux-022: 异常入口/出口帧扩到四组寄存器（rd/rb/rf/ra）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（K2 `trap.S` 与 K3 已闭合）；**被 `m14-linux-016`/`017` 依赖**（进程切换与 U-mode 帧以本任务为准）
**可并行分片**：否（`arch/dadao` 入口汇编 + 帧结构唯一）
**预估**：4–6 h
**档位**：大改（汇编入口 + 帧结构 + 跨阶段门控回改）
**状态**：待开始

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
   - `ra0–ra63` 用 **`stm.o {ra0:ra63}`**（`SimRISC-01` L102–103 / `stm.o_rrri_ra`；`immu6` ≤63 ⇒ 分 2 条）；基准索引语义按 spec；
   - `rf0–rf63` 用 **`stm.o {rf0:rf63}`**（L124–127 / `stm.o_rrri_rf`；`rf0` 作源读完整 64 位）；同样分 2 条。
3. **出口恢复**：反向 `ldm.o {ra…}` / `ldm.o {rf…}`；恢复 `ra` 时保证 `RACNT/MRPTR` 与保存时一致。
4. **语义目标**：异常 handler 内正常使用 `call`/`ret` **不得**改变用户可见的 `ra`/`rf`；进程切换后用户四组寄存器原样恢复。
5. **K2/K3 回改**：现有探针/门控若按旧帧偏移/字段数断言，须同步；`check-linux-k2`、`check-linux-k3` 必须回绿（旧断言可在本任务内按「阶段推进即退役」规则改限定语）。
6. **性能登记**：每 trap 增加 **~4 条块传送**（ra/rf 各 2 条 `stm.o`/`ldm.o`）；M14 不优化，登记为「后续优化项」（lazy/按需/switch_to 迁移等），**不得**在本任务引入 lazy 机制。

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

（待填）
