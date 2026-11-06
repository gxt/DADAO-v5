# TESTCASES-102t: timing 探针去 icount 化（20 例解 BLOCKED）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-098t`（矩阵重生成）、`GEM5-020t`（CFXREG 对齐）
**状态**：待开始

## 用户裁定（2026-11-06）

> 「去掉 icount，对 qemu 有什么影响」→ 说明影响后选 **A：全部去 icount**。

即：删掉 `-icount`，把 20 个 timing 探针改成**时序模型无关**的轮询/窗口断言，使 QEMU 与 gem5 用同一份探针可比；QEMU 侧精确指令时刻断言不再保留。

## 现状

- 4 个探针文件用 `-icount shift=0`（1 ns/指令）让时间按指令条数确定性推进：
  - `min_rom_probe_integ047t.py` 1 例（`start_busy_returns_busy`）
  - `min_rom_probe_integ050t.py` 9 例（cfx_time/`cfx_hart` timer/cycle/insn）
  - `min_rom_probe_integ051t.py` 10 例（异步中断仲裁/timer/DMA 两源）
  - `node_probe_prelude.py` 负责把 `-icount` 拼进 QEMU 命令行
- parity 驱动 `run_parity.py` 只要发现命令行含 `-icount`，gem5 侧直接标 `BLOCKED`（「QEMU -icount 无 gem5 等价物」）⇒ `node/arch` 20 例 BLOCKED
- 这些用例的期望写成了指令条数（「1 ms BUSY ≈ 1e6 条指令」「10 万条指令内 cycle 至少前进 N」等）
- 事实：gem5 FS 有完整时间模型（tick/事件队列/timer），缺的只是 QEMU 的 `-icount` 开关；因此这是**测试资产耦合**，不是 gem5 能力缺口

## 目标

1. **删除 `-icount` 依赖**：`node_probe_prelude.py` 不再注入 `-icount`；三个探针的 `icount_shift` 参数与相关分支删除。
2. **改写时间等待为模型无关**：
   - 读当前 `cfx_time`/`SBI_TIME_GET`，按「当前值 + Δ」设 deadline；
   - 用**有界轮询**等待（最大迭代数 + 墙钟超时），不得死等；
   - 断言改为**架构可见属性**：到期前不触发、到期后窗口内触发、`ISTATUS` 语义、`IMASK` pending、单次/重触发、单调性、门限行为；
   - 窗口宽度须足够容纳两引擎的节拍差异（建议 ≥ 10× 名义值），并在注释里写明取值依据。
3. **parity 驱动**：删除「含 `-icount` 即 BLOCKED」规则与相关字段/自检；更新 `qemu_gem5_shim.py` 文档（仍拒未知选项即可）。
4. **重新对照**：`node/arch` 20 例从 BLOCKED 转为**实际对照**（AGREE_PASS / GEM5_ONLY_FAIL / QEMU_ONLY_FAIL / DIFF 之一），逐条给结论；不得把新失败写成 BLOCKED 掩盖。
5. 文档同步：`tools/testcases/arch/README.md`、`tools/testcases/parity/README.md`、`run_parity.py` 文档串。

## 范围 / 非范围

**在范围内**：`tools/testcases/arch/{node_probe_prelude.py,min_rom_probe_integ047t.py,min_rom_probe_integ050t.py,min_rom_probe_integ051t.py}`、`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py,README.md}`、`tools/testcases/arch/README.md`、本任务书、`milestones.md`。

**不在范围**：gem5/QEMU 实现语义（若出现真失败，另立任务）、`tests/**` 向量/期望、`spec/**`、`contracts/**`、`tests/parity/matrix-M11.md`（等结果稳定后由矩阵任务重生成）。

## 验收标准

1. 全仓 `-icount` 命中 = 0（活文件；归档/任务书除外）。
2. 20 例在 QEMU 与 gem5 上都实际执行，逐例给出状态与退出码；`BLOCKED` 计数 = 0（除非有真实能力缺口，须给证据并单列）。
3. 稳定性：同一探针对 QEMU 连跑 3 次、gem5 连跑 2 次，结果一致（允许时间窗口差异，不允许 PASS/FAIL 翻转）。
4. `run_parity.py --self-test` rc=0；`node/arch` 全量重跑：`total 269`、`blocked 0`、`diff 0`；`gem5_only_fail`/`qemu_only_fail` 逐条列名。
5. `make check-arch`、`make check`（L1）rc=0。
6. 反例：把任一窗口断言改成恒真（或把 `-icount` 加回）⇒ 对应门控/自检 FAIL；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 取舍已由用户确认：**放弃「恰好第 N 条指令到期」的强断言**，换取两引擎同探针可比。
- 若 gem5 在某例上确实不满足语义（不是节拍差异），按真实失败记录并给最小复现，另立实现任务；不得回填 BLOCKED。
- `-icount` 会关闭寄存器 dump；删除后如 dump 可用，可加强自检，但不得改变用例语义。
