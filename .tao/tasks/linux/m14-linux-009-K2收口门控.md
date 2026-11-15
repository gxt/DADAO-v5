# m14-linux-009: K2 收口门控 `check-linux-k2`（Vast 端到端；入 L2）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-006`、`m14-linux-007`、`m14-linux-008`、`m14-spec-005`（均已 `已验证`）
**可并行分片**：否（单一端到端门控 + 共享构建树）
**并行组**：K2 串行链**最后一环**，与 `m14-linux-006`/`007`/`008` **必须串行**（同组件 + 同一构建树；门控自身要对它们的产物做注入重建）；唯一可并行的只读动作为 `m14-spec-005` 已完成后的契约静态比对
**预估**：3–4 h（含 4–5 路注入的重复构建）
**档位**：大改（新建 L2 门控 + 注入改组件源码；复核须独立重跑 + 独立注入）
**状态**：待开始

## 背景

K0 有 `make check-linux-k0`（119 项、10 路注入、入 L2，`m14-infra-003`），K1 有 `make check-linux-k1`（102 项、4 路注入、入 L2，`m14-linux-005`）。K2 交付了「同步异常通道 + 时钟/定时器 + IE 屏蔽」，但三者的边界目前只有任务书描述、**没有机械判据** ⇒ 阶段边界无法判定，也无法防止后续（K3）把 K2 的判据改坏。

**K2 出口判据**（本任务把它变成门控；判据本身待用户确认，见待裁定 1）：

1. Vast 上端到端：`power → hmon → smon → 内核入口 → start_kernel → setup_arch → time_init → 同步异常向量安装 → `cfx_hart` 异步向量安装 → 两轴 mask 打开 → 连续 N 次 `TIMER` tick → 屏蔽窗口内冻结 → `SYS_EXIT(0)`**，顺序正确、各阶段出现 1 次；
2. **同步异常通道可用**：一次**预先声明**的 `CFXMEM` 被正确分类（名字 + `ip` + `info`）后恢复继续；未声明的同类异常 ⇒ 具名终止（不递归）；
3. **时钟**：`cfx_time` 频率 == 契约值、`time` 单调；tick 间隔 == `freq/HZ`（`HZ` 从内核 `.config` 现场解析），余量按「指令边界投递」推导且有上界；
4. **屏蔽**：屏蔽窗口内 tick 冻结、解除后补投（计数恰增 1）；**两轴 mask 都必须起作用**（只开一轴 ⇒ 不 tick）；
5. **退出码合规**（`spec/Machine-v5 §7.1`；用户 2026-11-15 裁定「同意A'」）：**按事件性质分段**——自检失败码 ∈ guest 段 `0x01–0x7F`；异常终止码 ∈ monitor 段 `0xD0–0xDF`（supv：`0xD0|bit索引`，如 `CFXMEM`=`0xD1`）；PASS 恒 `0x00`；两段互不越界；
6. **不回归**：`check-linux-k0`、`check-linux-k1` 仍 rc=0。

## 范围

1. 新增 `tools/linux/check_k2.py` + `make check-linux-k2`：
   - 纳入 **L2**：`Makefile` 的 `_locked-check-modules` 列表（+ 注释）、`GATE_LOCKED_TARGETS`、`PHONY`、`make help` 行；
   - `docs/Process-07-门控分层规范.md` 的「目标-层」表新增一行（层 = L2，说明 = K2 收口）；
   - 检查项分组（现场派生，**不写死总项数**；打印 PASS/FAIL 计数）：
     - **B 构建**：K2 配置（`defconfig` 原样，`CONFIG_DADAO_K1_EARLY_STOP` 未设置 —— 从生成的 `.config` 解析）；构建 rc=0；命令行**无** `-d/-D`；
     - **E 端到端**：guest rc=0；阶段锚点各 1 次且严格递增（锚点以内核自打的唯一行/探针记录为准，不用逐指令日志）；
     - **C 契约一致（静态）**：`contract-see §6` 的 cause 表 ↔ `spec/DADAO-13 §2` + `spec/Machine-v5 §4.4` **现场解析比对**；内核 `arch/dadao/kernel/traps.c` 的 cause 名字表与契约表逐项一致（解析源码，不靠注释）；异步入口寄存器口径（`cfx_hart` `cg2 rc10`/`rc8`）与 §6 第 3 条一致（解析源码里的寄存器写点）；
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

## 待裁定

1. **K2 出口判据需用户确认**：上「背景」6 条是 architect 拟定的边界（用户 2026-11-15 原话「4、同意，是否并行根据依赖关系来定」只批准立册，未指定出口）。若用户要收窄（如「只要时钟中断 + jiffies」）或扩充（如「要 `clockevent`/`clocksource` 框架」「要 IPI 接口」），门控组随之调整。
2. **`margin` 的形状**：建议 `margin = period/2`（且不小于交付时实测最大偏差的 4 倍），依据是 `spec/DADAO-12 §5`「中断在指令边界检查」；若用户要求更严（如 `margin` = 单个 tick 内的实测上界），须在虚拟时钟上验证不 flaky 后再定。
3. **负例镜像的载体**：M 组与 X 组的负例可用「内核 `#ifdef` 探针构建」或「探针镜像 + 参数」两种方式；建议前者（与正例同一条代码路径、只改开关），避免第二套镜像结构漂移。

## 审阅记录

（待填）
