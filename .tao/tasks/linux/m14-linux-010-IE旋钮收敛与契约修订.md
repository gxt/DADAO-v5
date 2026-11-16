# m14-linux-010: IE 旋钮收敛为「当前运行模式 monitor」单行 + 契约 §6.4 口径修订（`ISS-455`/`ISS-454`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-qemu-003`（**已验证**：源轴按 mode monitor）、`m14-linux-008`（已验证：两行旋钮）
**可并行分片**：否（linux 组件单写者）
**预估**：2–3 h
**档位**：中改（实现收敛 + 契约文字 + 探针断言；复核 ≥2 路注入）
**状态**：已验证

## 背景

用户 2026-11-16 裁定：

- **`ISS-455`**：「查 mode monitor」—— 异步源轴 mask 按 `spec/DADAO-12 §5.2（三）步骤 3`，查**当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`（supv ⇒ `cfx_smon` 的 `cg2 rc4`），**与 `inner_cfx_code` 无关**；
- **`ISS-454`**（解释）：`escape` 不恢复 `inner_cfx_code`，所以"当前 cfx = `cfx_smon`"这个**理由**在首投后不成立；但**寄存器选择本来就该由"运行模式 → monitor"决定**，所以按 455 的口径，`cfx_smon cg2 rc4` 依然正确，只是**理由**要改。两条一次改完。

现状：`m14-linux-008` 为兼容两种读法，**每次写两行**（`cfx_smon` + `cfx_hart`）。按 455 裁定，`cfx_hart` 那一行**不再需要**（多余的写会让"源轴按 monitor"读法更难看清），应收敛为单行。

## 目标

1. **实现收敛**：`arch/dadao/include/asm/irqflags.h` 的 `save/restore/disable/enable` 由"两行"改为**只写 `cfx_smon` 的 supv 行（`cg2 rc4`）**；注释写明依据 = 运行模式 → monitor（`cfx_smon`），并引用 `ISS-454` 说明"当前 cfx"不是选择依据；
2. **契约修订**：`.tao/contracts/contract-see.md §6.4` 改为「IE 旋钮 = **当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`（supv ⇒ `cfx_smon cg2 rc4`）；`global_cfx_intr_mask` 只作模式级放行（被异步帧借用）」——**删掉**「当前 cfx = `cfx_smon`」的实例表述（`ISS-454`）；接口版本按 `docs/Process-02` 处理（`contract-see` 为 ADR-sourced，版本头保持 `0.7.3-rc`）；
3. **探针**：`k2_irq_probe` 的"两行"断言改为**单行**断言（`save` 后只 `cfx_smon cg2 rc4` 的源位置位、`restore` 后逐位复原），并保留**首投后仍能 tick**这类跨阶段证据（若 QEMU 侧已由 `m14-qemu-003` 覆盖，则此处只核内核侧读写）。

## 增补要求（`m14-qemu-003` 复核 finding 1，2026-11-16）

**本任务删掉 `cfx_hart` 行写入后，`tools/linux/k2_time_probe.py` 的 `SINGLE_ROW_PATCHES` 注入点会消失**（三处 old 串 count=0 ⇒ 现有代码 `SystemExit("注入点不唯一 (0 处)")` 会把整个探针跑红）。

必须在**本任务内**同步改，判据不得因此变弱：

- `SINGLE_ROW_PATCHES` 退化为**空表**，`single_row_run()` 直接用**未注入的内核**跑 C10（此时内核天然只写 `cfx_smon` 行，C10 由"注入式先红后绿"转为**常驻断言**）；
- **保留可失败性**：另加一路反向注入——临时**加回** `cfx_hart` 行写入 ⇒ C10 **必红**（证明判据仍能抓"写了两行"）；
- 验收里写明这两条（常驻断言 + 反向注入）的实测输出。

## 验收（真实 rc + 输出）

1. `k2_irq_probe` 全绿（条数现场统计，不低于改前 95）、`--selfcheck`/`--inject` 可跑；`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`check-linux-k0` 119/119、`check-linux-k1` 108/108；
2. **≥2 路注入**（`cp`+md5+重建）：① `restore` 只写低 32 位 ⇒ 逐位复原断言红；② `enable` 全清 0 ⇒ 粒度断言红（若原判据抓不到，先补断言再注入，见 `ISS-457`）；
3. 契约门控：`check-contracts-dir`、`check-contracts-pending`、`check-contract-relocs`、`check-rule-refs`、`check-spec-refs`、`check-interface` 全 rc=0；
4. 补丁纪律：`apply_series --component linux`、`check-source-state`、`check-patch-tree`（linux 0 problem）、`make_patch linux` 幂等；
5. L1 `make check` rc=0；完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/linux/**`、`tools/linux/**`、`.tao/contracts/contract-see.md`、本任务书；不改 `spec/`（spec 已是 mode-monitor 口径，无需改）、不改 QEMU；
- 语义不变：`flags` 仍整条 64 位、`enable` 仍只清内核关心源位；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-17）

自主逐行审查 `irqflags.h`/`irq.c` 两处写入点、两个探针的断言与注入表、契约 §6.4 条文；下列 finding 全部 **✅已修**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ⑴ C8「首次触碰在 `start_kernel` 内」前提失效：旋钮收敛后不再触碰被固件关闭的目标 cfx，首个被拒访问前移到 `time_init` 的 `cfx_time` 读 ⇒ 断言无依据地红 | ✅已修 | `check_permission` 的跨度改为 `time_init ≤ ip < init_IRQ`，注释写明「权限按目标 cfx 分开」 | 注入前实测 ip == `time_init` 起始、`info=0x7a88a008`；修后 158/158 |
| ⑵ `cfx_hart` 行「已放开」的两处 C7 断言（`check_vector_and_masks` + `check_axis`）仍按两行写 | ✅已修 | 两处都改为「该行未被写＝复位值、该位仍屏蔽」，并补 source/global 镜像的 monitor 行单独断言 | 修前 3 条红（158/158 → 逐条消失） |
| ⑶ `.config`/`vmlinux` 在**共享**构建树上于校验时才读取 ⇒ 并发写者（`m14-qemu-005` 的 `check-linux-k2`）换掉后 4 条 C1 假红 | ✅已修 | 新增 `image_config()`/`freeze_image()`：构建完立刻取 `.config` 并把 ELF 拷出，boot 用副本、断言用快照 | 早先一轮 98 条中 4 红全为配置项；修后 99/99，且 boot 不再受并发重建影响 |
| ⑷ 注入「`restore` 只写低 32」只红到 save 锚点，「逐位复原」断言仍绿（截位后 save/restore 自洽，`ISS-457` 现象） | ✅已修 | `P1` 增绝对锚点「restore 后整字 == 复位全 1 只清源位」；新增注入 `restore-32`（只截 restore） | 注入实测两条 P1 红（期望 18446744073709518847、实际 4294934527），`cp`+md5 还原后回绿 |
| ⑸ 增补要求的反向注入**打不中** C10：加回第二行写入时该行此刻本就读到同一字（`escape` 只在帧后改变它），运行期读数无差别 | ✅已修 | C10 增「写路径只写 monitor 行（源码）」常驻断言，读取器 `knob_rows_written()` 下沉到 `k2_time_probe` 并由 `k2_irq_probe` 复用 | 手工注入现源文件实测 `(True, False) → (True, True)`，`cp`+md5 还原后 `(True, False)`；整套由 `--inject --only two-row` 复验 |
| ⑹ 证据脚本的 TERM trap 只杀子进程不退出 ⇒ SIGTERM 无法停止长跑 | ✅已修 | `trap 'cleanup; exit 130' INT TERM` | 二次运行以 SIGKILL 终止后被中断的注入残留在源树（`irqflags.h` md5 c7d363c5），按 `cp`+md5 还原回 bf9350f6 并核对组件树干净 |
| ⑺ 文案笔误「cfx_hart 行未被内核算过」 | ✅已修 | 改为「未被内核写过」 | 同文件同断言 |
| ⑻ `only-smon-row` 注入随两行写法消失，注入数会 −1 | ✅已修 | 删除该路（其正向），新增 `restore-32` 补齐；反向由 `k2_time_probe` 的 `two-row` 承担 | `k2_irq_probe --list` 仍 8 路 |
| ⑼ 全 8 路注入重跑暴露 `knob-on-global` 的旧观测失效：旋钮改指 `cg8` 后固件 `supv_cfxreg` 未放行该 cg，内核在 `init_IRQ` 即报具名 `CFXREG`（rc `0xe2`），原「仍启动到 done」的期望不成立 | ✅已修 | 该路期望改为「§7.1 `supv+CFXREG` 码 + 具名行 + 禁止 `done` 行」，`want_rc` 支持 `("monitor", mode, cause)` 元组（与 `k2_time_probe` 同形）；C0 仍是主判据 | 单路重跑 6 条全 PASS（`期望=0xe2 实际=0xe2`、`C0` 红 `(2,4)→(8,1)`、还原 `bf9350f6` 后回绿） |

**判决**：无未修 finding；任务判据净变化 = `k2_irq_probe` 97→99、`k2_time_probe` 151→159（C7 +2、C10 +1），无删弱。


### 第 1 轮 reviewer 验收（2026-11-17）

**重跑**（`run.sh` 复跑 + 独立注入，真实输出/退出码）：`k2_irq_probe` 99/99、selfcheck 11/11、`--inject` 8/8；`k2_time_probe` 159/159、selfcheck 16/16；`k2_trap_probe` 85/85、k0 119/119、k1 111/111、k2 104/104；契约 6 门 rc=0；`make_patch` 0 written/71 unchanged、`apply_series` noop（HEAD 94647cfb0）、source-state linux clean=True、patch-tree linux 0 problem；L1 红成员全外因（4 项、0 行指本任务）。`汇总: FAILS=0`。

**写点 grep**：`grep CFX_WRITE(cfx_hart` 全树仅 timer(time.c) 与 vector rc10(irq.c)，**无一处写 `cg2 rc4`**；`cfx_hart` 的 intr-mask 仅现于 READ（`dadao_irq_mask_row_hart()`、init_IRQ printf 回读、async_trap.S `cfx2rd cfx_hart cg5 rc4`=excp_cause_info 非 mask）。

**C10/反向注入**：`SINGLE_ROW_PATCHES=()` 空表、非空即 `SystemExit`；未注入 C10 常驻绿（`写路径只写 monitor 行=(True,False)`、`cfx_hart 行仍复位=True`）；`--inject --only two-row` ⇒ C10 红 `(True,False)→(True,True)`，还原 bf9350f6。

**2 路自设计注入**（`cp`+md5+重建，均红→还原→回绿）：① `arch_local_irq_enable` 加 `cfx_hart` 写 ⇒ 源级 C10 红 `(True,True)`；② `init_IRQ` 加 `cfx_hart` 源轴写 ⇒ 运行期 C10「cfx_hart 行仍复位」红（`期望=True 实际=False`，源级 `knob_rows_written` 抓不到，证明两级断言各有可达 FAIL）。还原后源树 md5 复原（bf9350f6/8b84e927）、`git status` 干净、重建回绿。

**契约 diff**：§6.4 已改「当前运行模式 monitor 的 `<mode>_cfx_intr_mask`」、删净「当前 cfx = `cfx_smon`」、`global_cfx_intr_mask` 明确「模式级放行」；版本号仍 0.7.3-rc（上游册未变，依据成立）。

**越界**：仅 7 文件（components/linux/** ×4、tools/linux/*.py ×2、contract-see.md、本任务书），无 spec/tests-inst/qemu/gem5/chipyard。

**未决项（供架构师定夺，非本任务阻断）**：contract-see **§3** L52/L61 仍写「当前 cfx 的 `inner_run_mode` 行」作源轴（旧读法，`INTEG-051t` 带入、`m14-qemu-003` 未改），与 §6.4 新「运行模式 monitor」读法冲突；本任务范围仅 §6.4，需另立任务或裁定是否同步 §3。

**判决：Accepted**（本任务验收命令全绿、约束无违反；§3/§6.4 交叉项待架构师裁决）。


## 完成区

**测试结果**：`k2_irq_probe` **99/99**（改前 97）、`--selfcheck` 11/11、`--inject` **8/8 路**（含验收①②）；`k2_time_probe` **159/159**（改前 151；C7 +2/C10 +1）、`--selfcheck` 16/16；`k2_trap_probe` 85/85、`check-linux-k0` 119/119、`check-linux-k1` 111/111、`check-linux-k2` 104/104；契约 6 门全 rc=0。
**修改文件**：`components/linux/patches/arch/dadao/include/asm/irqflags.h.patch`、`components/linux/patches/arch/dadao/kernel/irq.c.patch`、`components/linux/changelog.md`、`tools/linux/k2_irq_probe.py`、`tools/linux/k2_time_probe.py`、`.tao/contracts/contract-see.md`（§6.4 + §7 + 附录 A）、本任务书。
**验收结果**（一键证据脚本，末行 `汇总: FAILS=0`、`EXIT=0`）：① 注入「`restore` 只写低 32」⇒ **P1 两条绝对锚点红**（期望 `18446744073709518847` 实际 `4294934527`），`cp`+md5 还原（`bf9350f6`）+ 重建回绿；② 注入「`enable` 全清 0」⇒ **仅 P5 粒度锚点红**（期望 `18446744073709518847` 实际 `0`），还原回绿；③ 常驻断言：C10 六条全绿（`写路径只写 monitor 行=(True,False)`、`cfx_hart 行仍复位`、tick 3==声明 3、退出 tick 3、rc=0）；④ **反向注入** `two-row`（加回 `cfx_hart` 行）⇒ C10 红（`(True,False)` 变 `(True,True)`），还原回绿。
**补丁纪律**：`make_patch` `0 written / 71 unchanged`（补丁集 md5 不变）；`apply-series` 幂等（`already applied`，HEAD 不变 `94647cfb0`）；`--source-state` linux `count=1 clean=True`；`check-patch-tree` **linux 段 0 problem**。
**新发现/坑**：① 依赖「首投后当前 cfx」的断言在收敛后会**说反**——C8 的跨度与 C7 的两行断言必须改按「权限/过滤按运行模式 monitor、权限按目标 cfx 分开」重写，spec `§5.2(三)` 步骤 3 是唯一真源；② **共享构建树 + 多 worktree 并发**：`.config`/`vmlinux` 必须在构建成功后立刻快照（取 `.config` 文本 + 拷出 ELF 再 boot），否则并发写者换掉后同一份源码会「假红」（本轮实测 4 条 C1 红即此故），建议固化为 K2 探针通例；③ **反向注入的可打中点**：`cfx_hart` 行在 `init_IRQ` 时刻本就读到与原值相同的字（第二行写入在该点上不改变值），运行期读数**无法**区分写一行/两行 ⇒ 只有**源码级**「只写一行」断言能抓住，注入前必须先把注入点证实能失败；④ `check-run-artifacts` 要求日志名 `check-*.log` 或 `<任务号>-<purpose>.log`，证据脚本日志须带任务号；⑤ 证据脚本 trap 必须 `exit`，否则 SIGTERM 被吞、长跑停不下来（中断的注入残留按 `cp`+md5 复原并留证）。
**遗留问题**：① L1 `make -k check` 5 项外因红，**逐项归因、0 行指向本任务**：`check-patch-tree`＝共享 qemu 树带 `m14-qemu-005` 在途补丁（linux 段 0 problem）；`check-knowledge-refs`＝4 处他任务书里的 `.work/**`（`m14-qemu-003`/`m14-qemu-004`/`m15-testcases-006`，均 `已验证` 提交带入）；`check-run-artifacts`＝7 个 `review-*.log`（qemu 复核者）；`check-temp-dirs`＝5 个他任务临时目录（`m14-linux-005/006/007/008`、`qemu-gem5-parity`）；`check-milestones-fresh` R1＝`m16-gem5-009` 有 worktree 但台账在「待开始」（主会话台账动作）。② `apply-series` 首次按 E5 流程需 `reset --hard <base>` 重放（本任务已做，源树内容 md5 逐文件复原）；③ 全部 8 路 `k2_irq_probe` 注入 + 1 路反向注入均已逐路重跑（每路：红 → `cp`+md5 还原 → 重建 → 回绿）；`knob-on-global` 的观测随收敛由「启动到 done」变为具名 `CFXREG`（rc `0xe2`），已按新观测钉死。
