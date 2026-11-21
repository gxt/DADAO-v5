# m14-linux-009: K2 收口门控 `check-linux-k2`（Vast 端到端；入 L2）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-006`、`m14-linux-007`、`m14-linux-008`、`m14-spec-005`（均已 `已验证`）
**可并行分片**：否（单一端到端门控 + 共享构建树）
**并行组**：K2 串行链**最后一环**，与 `m14-linux-006`/`007`/`008` **必须串行**（同组件 + 同一构建树；门控自身要对它们的产物做注入重建）；唯一可并行的只读动作为 `m14-spec-005` 已完成后的契约静态比对
**预估**：3–4 h（含 4–5 路注入的重复构建）
**档位**：大改（新建 L2 门控 + 注入改组件源码；复核须独立重跑 + 独立注入）
**状态**：已验证

## 背景

K0 有 `make check-linux-k0`（119 项、10 路注入、入 L2，`m14-infra-003`），K1 有 `make check-linux-k1`（102 项、4 路注入、入 L2，`m14-linux-005`）。K2 交付了「同步异常通道 + 时钟/定时器 + IE 屏蔽」，但三者的边界目前只有任务书描述、**没有机械判据** ⇒ 阶段边界无法判定，也无法防止后续（K3）把 K2 的判据改坏。

**K2 出口判据（2026-11-16 用户裁定「可以收窄」⇒ 6 条收窄为 4 条；原 ①⑤ 的断言仍在门控内复用，不丢覆盖）**：

1. **同步异常通道**（原 ②）：一次**预先声明**的 `CFXMEM` 被正确分类（名字 + `ip` + `info`）后恢复继续；**未声明**的同类异常 ⇒ 具名终止、不递归；
2. **时钟**（原 ③）：`cfx_time` 频率 == 契约值、`time` 单调；tick 间隔 == `freq/HZ`（`HZ` 从内核 `.config` **现场解析**），余量按「指令边界投递」推导且有上界；
3. **屏蔽**（原 ④）：屏蔽窗口内 tick 冻结、解除后补投（计数恰增 **1**）；
4. **不回归**（原 ⑥）：`check-linux-k0`、`check-linux-k1` 仍 rc=0。

**复用（不进对外 4 条口径，但门控内仍要断言）**：

- **原 ① 端到端顺序**：`power → hmon → smon → 内核入口 → start_kernel → setup_arch → time_init → 同步向量安装 → `cfx_hart` 异步向量安装 → 两轴 mask 打开 → N 次 tick → 屏蔽窗冻结 → `SYS_EXIT(0)`，顺序正确；
- **原 ⑤ 退出码分段**（用户 2026-11-15 裁定 A′）：自检失败 ∈ guest `0x01–0x7F`；异常终止 ∈ monitor `0xC0–0xFF`（supv ⇒ `0xE0|bit`，`CFXMEM`=`0xE1`）；PASS 恒 `0x00`；两段互不越界。

（①②③④⑤⑥ 分组的对应关系与各断言来源见 `范围` 与 `验收`；用户裁定原话：「可以收窄」＋「可以」。）

## 范围

1. 新增 `tools/linux/check_k2.py` + `make check-linux-k2`：
   - 纳入 **L2**：`Makefile` 的 `_locked-check-modules` 列表（+ 注释）、`GATE_LOCKED_TARGETS`、`PHONY`、`make help` 行；
   - `docs/Process-07-门控分层规范.md` 的「目标-层」表新增一行（层 = L2，说明 = K2 收口）；
   - 检查项分组（现场派生，**不写死总项数**；打印 PASS/FAIL 计数）：
     - **B 构建**：K2 配置（`defconfig` 原样，`CONFIG_DADAO_K1_EARLY_STOP` 未设置 —— 从生成的 `.config` 解析）；构建 rc=0；命令行**无** `-d/-D`；
     - **E 端到端**：guest rc=0；阶段锚点各 1 次且严格递增（锚点以内核自打的唯一行/探针记录为准，不用逐指令日志）；
     - **C 契约一致（静态）**：`contract-see §6` 的 cause 表 ↔ `spec/DADAO-13 §2` + `spec/Kaiwu §4.4` **现场解析比对**；内核 `arch/dadao/kernel/traps.c` 的 cause 名字表与契约表逐项一致（解析源码，不靠注释）；异步入口寄存器口径（`cfx_hart` `cg2 rc10`/`rc8`）与 §6 第 3 条一致（解析源码里的寄存器写点）；
     - **T 时间**：`freq` == 从契约解析的值；`time` 单调不减；相邻 tick 差 ∈ `[period, period + margin]`，`period = freq/HZ`（`HZ` 从 `.config` 解析）、`margin` 按「指令边界投递」推导（`spec/DADAO-12 §5`）并在完成区写清公式；
     - **M 屏蔽**：正例的屏蔽窗口内 tick 计数不变、解除后恰 +1；**两轴**各一次负例（只开 `cfx_smon supv rc4` / 只开 `cfx_smon global`）⇒ 不 tick；
     - **X 退出码分段**：正例 rc=0；负例 rc ∈ `0x01–0x7F`；扫描输出中的自报码，**不得**落在 `0x80–0xFF`（那是「其它 cfx / monitor」段，`§7.1`）；
     - **R 反向断言**：输出无 `CFXESC`/`CFXPERM`/`unknown cause`/`panic`/二次初始化痕迹；tick 行数 == 现场派生的 N；
   - `--selfcheck`：每个检查组至少一次「翻转输入 ⇒ 该组红」，且**证据脚本本身可红**（注入后重跑同一脚本 rc≠0）；
   - 与 K0/K1 **不重叠**：K0 查「能否交接」，K1 查「跑起来并退出」，K2 查「异常通道 + 时间 + 屏蔽」；同样的语义不作二次断言。
2. **可达 FAIL 注入 ≥4 路**（`cp` + md5 还原 + 重建；还原后必须重建再回绿）：
   - ① `cfx_hart` `cg2 rc10` 写成未映射 VA ⇒ 首次 tick 不可恢复（具名、非零、且**不是** 0xC0–0xFF 段）；
   - ② 定时器周期改成 0（`cmp = now`）⇒ 时间差/计数断言红；
   - ③ 只开一轴 mask（清 `rc4` 不清 `global`）⇒ M 组红；
   - ④ 把某**自检**失败码改回 `0xE1`（monitor 段）或把 `dadao_die()` 的码写成 guest 段 ⇒ X 组红；
   - ⑤ 入口少保存一个 bank ⇒ E 或 R 组红（现场挑选稳定可复现的一路并在完成区说明）；
   - 每路贴「注入后真实红色输出（哪条断言、期望 vs 实际）+ 还原 md5 == 注入前 + 还原重建后回绿」。
3. **一键证据脚本**：`tools/linux/` 或运行期证据目录内，一条命令跑完「构建 → 门控 → selfcheck → 注入 → K0/K1 回归」，退出码如实传播（禁 `cmd | tee` 吞码）。

## 验收（逐条贴真实 rc）

1. `make check-linux-k2` **rc=0**，检查项计数现场打印（PASS 数 == 总项数、FAIL 0）；
2. `--selfcheck` 各组可翻转；`--inject` ≥4 路逐条「红 → 还原 → 重建 → 绿」；
3. `make check-linux-k0` rc=0、`make check-linux-k1` rc=0（**不跑 `check-modules`**：会装共享安装根）；
4. `docs/Process-07` 的 L2 组成表含 `check-linux-k2` 一行；`make help` 有对应行；`GATE_LOCKED_TARGETS`/`PHONY`/`_locked-check-modules` 均含之（`grep` 现场取证）；
5. 期望值**全部现场派生**：完成区列出每个期望的来源（契约章节 / `.config` 键 / `llvm-nm` / 现场计数），并说明**没有**从被测输出反推期望（除「阶段锚点出现次数 == 1」这类结构断言）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`spec/`/`contracts/`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp` + md5；注入中途失败也必须 try/finally 还原并重建。
4. 只改 `tools/linux/**`、`Makefile`（目标 + L2 接线）、`docs/Process-07`、本任务书；**不改** `spec/`、`contracts/`、`components/linux/**`（注入时临时改、用完还原）、`tests/`、QEMU。
5. 只在 `qemu-system vast` 上验收；Vast 固件/镜像用共享产物，**不重建 QEMU**。
6. 门控必须**能失败**：每条断言有可达 FAIL 路径；禁恒真断言、禁「两支写同一结果」；计数类期望现场派生（禁钉死总项数，除 `spec` 常量）。
7. 运行时间：整体若 > 15 min，按 `docs/Process-07 §2` 与节点规则处理（可在计算节点跑，但**不得**改变判据）；主控机上同时只允许 1 个长跑批。

## 必须补的两条断言（`ISS-457`，`m14-linux-008` 复核发现）

- **`flags` 宽度**：现 `save` 取整条 64 位，但注入「截低 32 位」时 `k2_irq_probe` 95/95 **全绿** ⇒ 无绝对断言。补：`P1` 断言 `before_smon` == `init_IRQ` 行值（高位参与比较），使截位必红。
- **`enable` 粒度**：注入「`enable` 全清 0」时同样全绿。补：`P5` 断言 `enable` 态 == `disable` 态 `& ~DADAO_IRQ_SOURCE_BITS`（其余位保持），使全清必红。
- 另：`k2_irq_probe` 的 `run.sh --inject` 步骤标签「time 6 路」实为 5 路（文档级，只判 rc），一并订正。

## 待裁定

1. ~~**K2 出口判据需用户确认**~~ **已裁定（2026-11-16 原话「可以收窄」＋「可以」）**：收窄为 **4 条对外口径**（同步异常通道 / 时钟 / 屏蔽 / 不回归），原 ①（端到端顺序）与 ⑤（退出码分段）**仍作为门控内断言复用**，不丢覆盖；`clockevent`/`clocksource`/IPI **不进 K2**。
2. **`margin` 的形状**：建议 `margin = period/2`（且不小于交付时实测最大偏差的 4 倍），依据是 `spec/DADAO-12 §5`「中断在指令边界检查」；若用户要求更严（如 `margin` = 单个 tick 内的实测上界），须在虚拟时钟上验证不 flaky 后再定。
3. **负例镜像的载体**：M 组与 X 组的负例可用「内核 `#ifdef` 探针构建」或「探针镜像 + 参数」两种方式；建议前者（与正例同一条代码路径、只改开关），避免第二套镜像结构漂移。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查，深度 1 不能起嵌套子代理）

审查范围：`tools/linux/check_k2.py` 全文（7 组 B/E/T/M/S/X/R + 4 路注入 + 7 组自检）、`Makefile` 五处接线（`.PHONY`/`GATE_LOCKED_TARGETS`/`help`/`_locked-check-linux-k2`/`_locked-check-modules`）、`docs/Process-07` 一行、一键证据脚本。判决：四条出口口径逐条落在**现场派生**的期望上（`derivations()` 读 `contract-see §3` 的 freq、镜像 `.config` 的 `HZ`、`spec/DADAO-13 §2` 表、`spec/Kaiwu §7.1` 段/位号、ELF 程序头、BootROM 镜像），无硬编码期望；每组都有可达 FAIL（`--selfcheck` 逐组翻转，注入逐路变红）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| S 锚点按语义猜顺序（`smon` 排在 `sync-vector` 前）⇒ S4 恒 FAIL | ✅已修 | 重排 `STAGE_ANCHORS`：`K1 ptw vec`（同步向量安装）先于 `K1 ptw pre`（smon 移交报告） | `[GROUP] S 20/20`；selfcheck「S 缺 armed 锚点」仍可红 |
| B5/B6（无具名终止 / 无 `K2 fail:`）对 trap 镜像误判——该镜像本就以具名终止结束 | ✅已修 | `check_build(terminating=True)`：B5/B6 只对 plain 镜像断言 | `B 27/27`；trap 的终止由 E 组 15 条判 |
| 注入 verdict 的「实际」列写死「有」，与 PASS 并存（日志误导，违反「结论与真实输出对齐」） | ✅已修 | 由同一判据派生 `_tick_state()`/`_exit_state()`/`_in_guest()` | 注入日志 `未产生 tick 行 期望=无 K2 tick 实际=无 K2 tick` |
| `derivations()` 需要 `kernel_size`，初版快照未含（首次运行即缺键） | ✅已修 | `build_image()` 按该镜像 `k1boot.kernel_size_from_elf()` 现场算并快照 | 三轮 gate 运行正常；E5/E12 用它判 ip 落在内核内 |
| `--no-regress` 定义未接线（selfcheck 会白跑 K0/K1 子门控） | ✅已修 | `gate(regress=…)`；selfcheck 传 `False`，main 传 `not args.no_regress` | selfcheck 只跑三镜像 + 合成翻转；注入往返用 `--no-regress` |
| 证据脚本把 `check-patch-tree` 的计数行（`linux: 69 patch(es)`）当问题行 ⇒ 误判 FAIL | ✅已修 | 问题行按 `… linux: .*(assertion\|problem)` 过滤，计数行只打印 | 复盘 `check_patch_tree_linux` rc=0、`linux 段 problem=无` |
| 死代码：`Report.red_groups` + 5 个未用 derivation 键 | ✅已修 | 删除 | `python3 -m compileall -q tools` 通过；`--list` 正常 |
| **任务书「必须补的两条断言（`ISS-457`）」首轮漏做**（只写了门控，没回头补 `k2_irq_probe` 的绝对锚点） | ✅已修 | `P1` 增「save 的整字 == 契约 §3 的复位全 1 只清源位（64 位）」；`P5` 增「`enable` == `disable` 清掉源位（两行）」；配 2 路注入 + 2 个自检翻转；证据脚本标签 6→5 路 | `k2_irq_probe` 97/97、`--selfcheck` 11/11、`--inject` 8/8（`flags-32` 只红 P1、`enable-write-zero` 只红 P5，还原后回绿） |

**复验**：`make check-linux-k2` 104/104、`--selfcheck` 7/7、`--inject` 4/4；`k2_irq_probe` 97/97、`--selfcheck` 11/11、`--inject` 8/8。结论：8 条 finding 全 ✅已修，无 ⏸/❌。

### 第 1 轮 reviewer 验收（2026-11-16）

**判决：Accepted**（大改档＝看 diff + 独立重跑 + 4 路自设计注入；本段为第 1 次重试补写）
**独立重跑（均我自跑、非采信完成区）**：`make check-linux-k2` rc=0 `[GROUP] B 27/27 E 15/15 T 17/17 M 12/12 S 20/20 X 9/9 R 4/4` / `PASS (104/104)`（104 行 `[PASS]`、0 行 `[FAIL]`）；`check_k2.py --selfcheck` rc=0 `7/7 组可翻转`；`check_k2.py --inject --no-regress` rc=0 `4/4 路`（rc=0xe9 / 0x7c / 0x14 / 0x61，还原 md5 == 注入前、重建回绿）；`make check-linux-k0` rc=0 `119/119`、`check-linux-k1` rc=0 `(108/108)`、`k2_trap_probe` rc=0 `(85/85)`、`k2_time_probe` rc=0 `(151/151)`、`k2_irq_probe` rc=0 `(97/97)`、其 `--selfcheck` rc=0 `(11/11)`、其 `--inject` rc=0 `(8/8)`。
**七组抽检的可达 FAIL**：**E** — trap guest 实测 rc=`0xe1`（`die mode=2 code=0xe1`）、E6/E7 `resumed=yes marker=0x5031`，selfcheck「未续跑」「终止码进 guest 段」均可红；**T** — `hz` 取**该镜像 `.config`**（`CONFIG_HZ=100`，T2 期望 100），T11 `4×92120=368480 ≤ 5000000` 真断言，selfcheck 改 hz / 删 tick 行 / rc≠0 三路可红；**M** — `masked ticks=0 window=30000000` 且 `ctrl=0x5`（bit2=ISTATUS 置位 ⇒ 排除「没 arm」），`released ticks=1 elapsed=207381 < 5000000`（恰 +1，不丢不双），selfcheck「窗内投递」「补投两次」可红；**X** — 四段 `pass=0x0 guest=0x1-0x7f other=0x80-0xbf monitor=0xc0-0xff` 由 `spec/Kaiwu §7.1` 现场解析、X1 断言互不重叠，自检码 21 条与我独立 `grep` 全集逐条一致（同 8 文件、清单外无遗漏）；**R** — `subprocess.run` 真跑 `check_k0.py`/`check_k1.py` 取真实 rc（STAT `119/119`、`(108/108)`），非缓存计数。
**期望值派生**：freq 读 `contract-see.md §3`（`1_000_000_000`）、HZ 读镜像 `.config`、N 读 `asm/time.h`（=3）、cause 表读 `DADAO-13 §2`、段/位号读 `Kaiwu §7.1`、`probe_va` 由 boot info + ABI 超页推导、`kernel_size` 读 ELF —— 无一写死。
**4 路自设计注入（`cp`+md5、逐路回绿）**：A `save` 截低 32 位 ⇒ `k2_irq_probe` rc=1 **仅** P1 绝对锚点红（`期望=18446744073709518847 实际=4294934527`）；B `enable` 全清 0 ⇒ **仅** P5 粒度锚点红（`期望=[…7fff,…7fff] 实际=[0,0]`）；C handler 重挂 ×2 ⇒ `check_k2` rc=1 仅 T10/T11 红（`deltas=[20100294,…] margin=5000000`）；D `DADAO_EXIT_MONITOR` 位移 `<<4→<<2` ⇒ rc=1 X6/X8（+E8）红（`code=0xc9`）。四次还原 md5 == 注入前，源树 `git status` 干净。
**ISS-457**：A / B 分别**只红对应那一条**（各 1 行 FAIL，P1、P5 互不串红）⇒ 两条绝对断言确已补且可达，非「都红/都不红」。
**L2 接线**：`check-linux-k2` 由 `GATE_LOCKED_TARGETS` 宏生成（自带锁 + `.PHONY`），仅列 `_locked-check-modules`（L1 `_locked-check` 无此目标）、`make help` 与 `docs/Process-07` L2 表各 1 行；`check-patch-tree` linux 段 0 problem（llvm 段红系并发外因，已核）。
**越界**：`git diff --stat 15f34a2d..66d0186d` 仅 5 文件（本任务书 / `Makefile` / `docs/Process-07` / `tools/linux/check_k2.py` 新 / `tools/linux/k2_irq_probe.py`），`components/linux/**` 0 改动；任务书无运行期路径、完成区 16 行、状态=待验收；证据日志 4 份均钉 `15f34a2d`、`run.sh` 按 `git rev-parse --show-toplevel` 推根且拒绝 master。
**finding（文档级，不阻断，交 architect 收尾改）**：① 完成区遗留②「1 个不合规日志文件名」已失效（`make check-run-artifacts` rc=0）；② 注入①实测 rc=0xE9 落 monitor 段、与任务书①「非 0xC0–0xFF」预期不符，工程按实测改判并已披露，建议在任务书①处补一句实测结论；③ B3「命令行无 -d/-D」自指（cmd 由门控自身 `boot()` 构造，FAIL 路径＝改门控），与 K1 K5 同型；④ 自检码扫描面为硬编码 8 文件清单（当前与全集一致，新增自检文件须同步）。

## 完成区

**测试结果**：`make check-linux-k2` **104/104**（B 27 / E 15 / T 17 / M 12 / S 20 / X 9 / R 4）；`--selfcheck` **7/7 组**可翻转；`--inject` **4/4 路**（红 → `cp`+md5 还原 → 重建 → 回绿）；`check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` **97/97**（原 95 + `ISS-457` 两条绝对锚点）；L1 两项外因红（见「遗留问题」）。
**修改文件**：`tools/linux/check_k2.py`（新：7 组门控 + 4 路注入 + 7 组自检）、`Makefile`（`check-linux-k2` 目标、`GATE_LOCKED_TARGETS`、`.PHONY`、`help`、L2 `_locked-check-modules`、注释）、`tools/linux/k2_irq_probe.py`（`ISS-457`：`P1` 绝对锚点 + `P5` `enable` 粒度断言 + 2 路注入 `flags-32`/`enable-write-zero` + 2 个自检翻转）、`docs/Process-07-门控分层规范.md`（「目标-层」表 L2 一行）、本任务书；运行期证据脚本的步骤标签订正（`k2_time_probe --inject` 6→5 路）。未动 `spec/`、`contracts/`、`tests/`、`components/**`、QEMU。
**验收结果**（真实输出，完整转录见运行期证据目录的 `run.sh` 与其 `log/`）：
- 计数：`[GROUP] B 27/27  E 15/15  T 17/17  M 12/12  S 20/20  X 9/9  R 4/4`；`check-linux-k2: PASS (104/104)`。
- 期望现场派生：`derivations()`（脚本 221–242 行）读 `contract-see §3` 的 `cfx_time_freq`、镜像 `.config` 的 `CONFIG_HZ`、`spec/DADAO-13 §2` 表、`spec/Kaiwu §7.1` 段与位号、`probe_va`；运行值 `T1/T2/T3` 期望==实际 `1000000000 / 100 / 10000000`、`[STAT] tick deltas=… max=… margin=5000000`、`E1 = 0x20080000000`、`[STAT] segments pass=0x0 guest=0x1-0x7f other=0x80-0xbf monitor=0xc0-0xff`。
- 自检 7/7（例 `T hz 被改 ⇒ T2 期望=100 实际=101`、`M 窗内投递 ⇒ M1 期望=0 实际=2`、`X 自检码进 monitor 段 ⇒ X3`、`R k0 失败 ⇒ R1 期望=0 实际=1`）。
- 注入 4 路（每路还原 md5 一致、重建回绿 0 失败）：①`async-vector-unmapped` ⇒ rc=0xE9、无 tick、T/X 红；②`period-zero` ⇒ rc=124、无 tick/done、T/X 红；③`one-axis-only` ⇒ rc=0x14 + `K2 fail: irq test: first TIMER tick`、M/S 红；④`die-code-guest` ⇒ rc=0x61、P7 `cfxmem=0x61`、E/X 红。「证据脚本可红」：注入 ① 后同一门控 rc=1，还原后 rc=0。
- 接线取证：`grep -n check-linux-k2 Makefile` 命中 `.PHONY` / `GATE_LOCKED_TARGETS` / `help` / `_locked-check-linux-k2` / `_locked-check-modules` 五处；`make help` 有该行；`docs/Process-07` L2 表有该行。
- `ISS-457`（任务书「必须补的两条断言」）：`k2_irq_probe` 97/97（+2）、`--selfcheck` 11/11、`--inject` 8/8——`flags-32`（`cfx_smon` 行只读低 32 位）只红 `P1` 绝对锚点、`enable-write-zero` 只红 `P5` 粒度锚点，其余 P1/P2 值自洽（正是复核指出的「无绝对锚点则全绿」），两路还原后回绿 0 失败。
- 补丁纪律：`apply_series --component linux` = already applied、`make_patch linux` `0 written, 69 unchanged`、`check-patch-tree` linux 段 0 problem、`--source-state` `linux: OK count=1 clean=True`、`check-component-changelog` rc=0。
**新发现/坑**：① 异步向量指向未映射 VA 的实测签名是 **rc=0xE9（monitor 段 supv+UNDI 位号）、无 `dadao:` 行、无 tick**——任务书 ① 预期的「具名、且不在 0xC0–0xFF」不成立，门控按实测判据（rc≠0 + 无 tick）断言；② 「周期 0」不是时间差红而是**中断风暴**（每次 `escape` 立即再投递）⇒ rc=124、无 tick，证据脚本用 `K2G_QEMU_TIMEOUT=60` 只缩短挂起判定（`make` 目标仍 180 s）；③ **还原必须刷新 mtime**：`cp -p` 会把源文件 mtime 恢复成旧值、make 判「对象已最新」不重编（一次假回绿），门控统一 `write_bytes` 还原 + md5 对账；④ 端到端顺序里 `K1 ptw vec` 先于 `K1 ptw pre`，按语义猜会恒 FAIL；⑤ 注入 ⑤（入口少存一个 bank）对本门控**不可达**（四组口径不含帧完整性，那是 `k2_trap_probe` C7），故未纳入； ⑥ `ISS-457` 的两个洞只有「契约常量锚点」能堵：低 32 位截断后 P1 的 save/restore/两行比对**全部自洽**，连 `init_IRQ` 行也被同一条 save 写坏（`start_kernel` 更早的 `local_irq_*` 已把寄存器写成 `0xffff7fff`，实测）⇒ 唯一可用锚点是 `contract-see §3` 的「`cfx_intr_mask` 初值全 1」；`enable` 全清 0 同理由 `disable` 行锚。
 ⑦ `R` 以子进程重跑 `check-linux-k0`/`check-linux-k1`（各含增量构建与 QEMU 启动），`make check-modules` 因此会
  把 K0/K1 判定跑两遍、多约 2–4 分钟——这是「不回归」要拿到**真实 rc** 的代价（改为只读计数会失去该判据）。
**遗留问题**：① **L1 未全绿，两项均非本任务引起**：`check-patch-tree` 报 llvm-project 的 `DADAOAsmParser.cpp`「HEAD diff ≠ patch」——共享组件源树已被并发任务（`m15-spec-003` 的 WIP 提交改该 patch 25+/13−）重应用，linux 段 0 problem；修法：该任务合并/重新导出补丁后自然回绿（本任务不动 llvm 组件）。② `check-run-artifacts` 报运行期日志目录下**本次实测 1 个**不合规文件名（他人审查日志 `r2-default.log`；早前一轮为 7 个、已被其所有者清掉 6 个），需其所有者改名或删除（本任务不改他人证据）。③ 本任务内无遗留。
