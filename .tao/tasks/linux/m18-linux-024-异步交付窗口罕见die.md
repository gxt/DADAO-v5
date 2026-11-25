# m18-linux-024: 异步交付与 umon 桩 `reopen→escape` 窗口的罕见 die（~1/475）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-022`（R2 内核异步新模型）已合入；`m18-linux-023`（扁平位图解码）合入后可独立验证（两者同改 `components/linux`，须串行）
**可并行分片**：否（同改 `components/linux`）
**预估**：3–5 h
**档位**：中改（复核 ≤40 min）
**状态**：待返工

## 第 1 轮进展（2026-11-25 08:3x，无代码改动；可复现与两版否决已实测）

- **复现已做成**：私人重放树 + 启动 harness（跑 K6 自身输入脚本，检测 die/hang，`setsid nohup` + `*_EXIT`）。基线 flaky 实测 **2 dies/12 boots**（另一样本 2/2），签名 `K3 pf … ip=0x20000153518 va=0x8 result=die-no-vma` → `die 0xe4`。**确定性 knockout**（把返程 frame base 强制置 0）每次启动都复现 ⇒ harness 有可达 FAIL 路径。
- **原签名根因确认**：`dadao_async_kernel_return` 以 `set.rb rb3, 0; jump [rb3, rd3, 0]` 结尾，被中断桩以**清零的 rb3** 恢复现场。改「相对转移（`jump [rb0, delta, 0]` 经只读 IP）+ 忠实恢复 rb3」后该签名 **0/12**（对照 2/12）。
- **两版实现已建、已测、已否**（脚本/diff 留档在运行期证据目录）：
  - **A**（tail + 入口捕获掩码 + 相对跳转）：1 个 `0x82` die + 2 hang / 10 boots ⇒ 更差，已回退；
  - **B**（仅 tail + 相对跳转）：3 dies（2×`0x82`、1×`die 0xe1`）/ 12 boots、0 hang ⇒ 仍不可接受。
- **剩余失败已定位但未闭合**：
  1. `cause=CFXTRAP(0x1) ip=<kernel text> info=0x7f0802f7` → `die 0x82`：supv 帧的 `ip` 来自**陈旧的** `dadao_async_outer_cg5.cause_ip`，而 `info` 是异步 handoff 的 `trap cfx_smon,759` 指令字 ⇒ **帧由两个来源拼装**；
  2. **hang**：`cfx2 CID=PTWMEM CIP=dadao_do_page_fault+0x17c`、`rb4=0`（`va=0x410`，NULL vma）——缺页处理自身缺页，随后 guest 在 `dadao_early_exit` 的 semihosting 后 `jump [rb0,0]` 空转；monitor dump 已抓（`MODE=2`/`PTBR`/`cfx2 GIM`/`CID/CIP`）。

## 下一轮做法（第 1 轮结论，2026-11-25）

返回路径按「**恢复全部寄存器 + 用 `escape` 转移（不经 GPR）**」重做：要求 supv 桩保留自己 `cg5 rc0/rc1/rc3` 的软件副本，并在 escape 前重写；掩码策略字用 `xnor.o`+`andn.w` 构造（已验证）；关闭捕获窗口时**不得**在 handoff selector 之前新增 `cfx_smon` 访问。完成后跑 12 boots；若 NULL-vma hang 仍在，用 monitor dump 追被污染的寄存器（可能需**拆成独立任务**）。


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
