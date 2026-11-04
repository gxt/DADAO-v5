# GEM5-019t: SYS_ELAPSED 与 SYS_TICKFREQ 时钟基准一致（1e9 ticks/s）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-018t`（已验证；`SYS_TICKFREQ` 已按 1e9 返回、046t 基线）、`QEMU-079t` / `QEMU-080t`（已验证；Machine-v5 system 与 target 时钟基线）、`GEM5-017t`（已验证；FS parity 与 shim 工具链）、`GEM5-015t` / `GEM5-016t`（已验证；FS Tiny/Node 平台）、`TESTCASES-094t`（已验证；`min_rom_probe_046t` 资产，只读复用）；`ADR-0020`（semihosting 调用/返回）、`ADR-0048 D1/D2/D5`（同模式一致、不比较时序数值）
**状态**：待开始

## 执行环境

**执行环境**：本地（仓库根；从含本册的 `master` 建独立 `git worktree` + 分支 `GEM5-019t`；**只改 `components/gem5/**` + 本册 + `.tao/knowledge/milestones.md`**；证据落 `.work/evidence/GEM5-019t/**`、日志 `.work/log/gem5/**`、临时物 `/tmp/opencode/GEM5-019t/**`）。开工前现场确认：

1. `GEM5-018t` 已 `已验证` 且已合入 `master`；`make check-source-state` 报 `gem5: OK HEAD=<commit> count=1 clean=True`（基线以现场为准；2026-11-04 为 `12a4716`）。
2. `.work/source/gem5/build/DADAO/gem5.opt` 存在且 `--help` rc=0；`.work/source/gem5` 是 `manifests/components.lock.toml` 锁定 commit + 恰好 1 个 commit 的干净树。
3. `.dadao/cross-toolchain/bin/qemu-system-dadao`、`.dadao/tests/bootrom/step5/bootrom_step5.bin`、`tools/testcases/arch/min_rom_probe_046t.py`、`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py}` 存在。
4. 任一不成立 ⇒ **rc=2 BLOCKED**（附缺失项与现场），不得用旧日志/旧二进制冒充。

## 用户口径（2026-11-04，主会话转达）

- **用户原话（逐字）**：「时钟信息，QEMU 和 GEM5 保持一致」。
- QEMU 侧：`target/dadao/cpu.h` 的 `DADAO_TIME_FREQ = 1000000000ULL`；`SYS_ELAPSED` 返回 target ticks（`semihosting/arm-compat-semi.c` 的 `get_clock() - clock_start`，`get_clock()` 为 ns ⇒ **1e9 ticks/s**）；`SYS_TICKFREQ` 返回 `1000000000`。
- gem5 侧：`SYS_TICKFREQ` 已按 `1e9` 统一（`GEM5-018t`）；`SYS_ELAPSED` 仍走 gem5 基类 `semiTick(curTick())`，单位与 `TICKFREQ` 不自洽。本任务要求 **`SYS_ELAPSED` 与 `SYS_TICKFREQ` 使用同一 1e9 ticks/s 基准**。
- **不改 spec/契约语义**：`spec/Machine-v5-测试机运行环境.md §5.3` 与 `contract-semihosting §3` 只写「target ticks / ticks per second」，未定义具体频率；M11 的 `1e9` 是用户 2026-11-04 裁定（`discussing.md`），不是 spec 正文。**不改 QEMU**。
- **同模式一致规则（`ADR-0048 D1/D2/D5`）**：只比较 gem5 FS ↔ QEMU system 的同 case 结果（通过/失败、退出码、架构可见结果）；**不比较时序数值**。因此跨引擎不要求 `ELAPSED` 数值相等，只要求同 case 通过 + gem5 内部单位自洽。
- **不改** `tools/**`、`tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`components/qemu/**`、`Makefile`、`manifests/**`、`docs/**`；不复制 `DADAO-0628`（只读溯源，标「内容溯源，非执行必需」）。

## 现场事实（2026-11-04 只读核对；开工后须现场复核）

### F1 当前 gem5 `SYS_ELAPSED` 的单位

- 基类 `src/arch/generic/semihosting.{hh,cc}`：`callElapsed32/64` 写 `semiTick(curTick())`；`tickShift = max(0, findMsbSet(sim_clock::Frequency) - 31)`，`semiTick(t) = t >> tickShift`。
- `sim_clock::Frequency` 默认 `1e12`（`src/sim/core.cc` 的 `_ticksPerSecond = 1e12`；启动横幅 `Global frequency set at 1000000000000 ticks per second`）。`msb(1e12)=39` ⇒ `tickShift=8` ⇒ 单位 = `1e12/256 = 3.90625e9` ticks/s，与 `SYS_TICKFREQ=1e9` **不自洽（差 3.90625×）**。
- 现场样例（2026-11-04 单跑 046t `svc_elapsed`）：gem5 观测 `rd50=0x1076`（=4214），对应 `curTick=1079000`（debug 现场）；同一 tick 按 1e9 应为 `1079`（`1079000/1000`）。**旧值非 0，`svc_elapsed` 仍然 PASS** ⇒ 046t 该 case 只能证明「非零/返回 0」，不能证明单位。

### F2 `SYS_TICKFREQ`（已由 `GEM5-018t` 修复，回归项）

- `DadaoISA::Semihosting::callTickFreq` 覆盖基类，返回 `1000 * 1000 * 1000`；5 条探针断言 `rd8 == 1000000000`（`semihost_tag_path` / `semihost_cfxha_agnostic` / `bank_num_rd16` / `ret_rd8` / `svc_tickfreq`）。

### F3 QEMU 对照（只读，内容溯源）

- `components/qemu/patches/target/dadao/cpu.h.patch`：`#define DADAO_TIME_FREQ 1000000000ULL`。
- `components/qemu/patches` 的 `semihosting/arm-compat-semi.c`：`TARGET_SYS_ELAPSED` 为 `get_clock() - clock_start`；`get_clock()` 是 host `CLOCK_MONOTONIC` 纳秒（`include/qemu/timer.h`），故 ELAPSED 是 **1e9 ticks/s 的 host 时间**；`TARGET_SYS_TICKFREQ` 返回 `1000000000`。
- gem5 只能以**模拟时间**映射同一单位（`curTick()`），两者数值不可跨引擎比较（`ADR-0048 D2`）。

### F4 规范/合约口径

- `spec/Machine-v5-测试机运行环境.md §5.3`（行 `0x30`/`0x31`）与 `contract-semihosting §3`：`SYS_ELAPSED` = 「已流逝的 target ticks」（64 位参数块），`SYS_TICKFREQ` = 「ticks/秒」；**均未固定频率值**。
- `.tao/contracts/contract-see.md` 的 `cfx_time`：`cg10 rc0 = 1_000_000_000`（测试机约定，1 count = 1 ns），`cg10 rc1` 为 64 位时间值；`spec/DADAO-12 §4.10` 只写「计数频率（Hz），硬件设置」。⇒ 「target tick = 1 ns」是 v5 测试机既有约定，1e9 有独立于 gem5 实现的依据。
- gem5 内部同域先例：`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch` 的 `nodeTimeValue()` 用 `(curTick - timeBaseTick) / 1000`（1 count = 1 ns）；**注意**那是 `cfx_time` 的**复位基准**，`SYS_ELAPSED` 的语义是「引擎/进程起点以来」（QEMU `clock_start`），本任务不沿用 `timeBaseTick`。

### F5 046t `svc_elapsed` 现有断言

- `tools/testcases/arch/min_rom_probe_046t.py` 的 `svc_elapsed`：`exit 0x75`、`rd8=0`、`rd50=PRESENT`（仅要求参数块被写入且非零；不校验数值/单位）。

### F6 工具侧既有状态（不在本任务修）

- `tools/testcases/parity/run_parity.py` 的 `KNOWN_GEM5_BLOCKED` 仍登记 7 条 `GEM5-018t` 已修复项（注册表 stale）⇒ 全量 `--profiles node --scopes arch` 的 driver rc=1 属**预期**；`--only` 时 stale 检查只遍历过滤后的行，故 driver rc=0，但 **`--only` 只是“跑完后过滤行”，仍会执行整组 arch**（2026-11-04 实测 >5 min 未完），须按长任务后台跑。
- `tools/gem5/build_gem5.py` 末步 `(source/"build").relative_to(build_link.parent)` 在 fresh worktree 且 `.work/build/gem5` 缺失时抛 `ValueError`（scons 已成功）；本任务沿用 `mkdir -p .work/build/gem5` 绕过，修复另立 INFRA 任务。

## 接口规范

> 目标是**可观测语义 + 判据**；下列「推荐落点」不是唯一实现，engineer 可等价实现，但必须满足全部判据与不变项。

### 1. 统一基准

- 在 `DadaoISA::Semihosting` 内维护**单一**「每秒 target ticks」常量（值 `1e9`，注释引：用户 2026-11-04 裁定 / `discussing.md`、QEMU `DADAO_TIME_FREQ`、`contract-see` 的 `cfx_time` 1 GHz 测试机约定）；`SYS_TICKFREQ` 与 `SYS_ELAPSED` **共用**该常量，不得两处各写魔数。
- `SYS_ELAPSED` 的换算必须是**从引擎频率独立推导**，不是把 `3906250000` 或 `3.90625` 写死：
  `elapsed = floor(curTick() * ticksPerSecond / sim_clock::Frequency)`，结果 64 位。
  基准 = `curTick()`（仿真/引擎起点），**不减** `timeBaseTick`（那是 `cfx_time` 的复位基准，属另一服务）。
- **64 位安全**：中间量不得用 64 位计算 `tick * 10^9`（`Tick` 上限会溢出）；用 128 位中间量或商/余分解。边界：`Tick=(2^63-1)`、`Frequency=10^12` 时结果为 `9223372036854775`（可用 Python 大整数复算）。
- 不改基类 `src/arch/generic/semihosting.*`（上游共用），不改其 `tickShift`/`semiTick`；其它服务继续用基类。

### 2. `SYS_ELAPSED (0x30)`

- 语义不变：64 位参数块写入 64 位 ticks（大端）；返回 `rd8 = 0`；`IP += 4` 由通用返回机制完成。
- 推荐落点：在 `DadaoISA::Semihosting` 覆盖 `callElapsed32` / `callElapsed64`（与基类签名一致），内部共用一个换算 helper，写参数块；`calls` 表 `SYS_ELAPSED` 的成员绑定在派生覆盖后自动指向新实现。**不得**只在 `semiTick`/`calcTickShift` 上打补丁（非虚、且会波及未列入本任务的服务）。
- 32 位入口：DADAO semihosting 恒 64 位（`contract-semihosting §2`），该分支 guest 不可达；若保留，必须与 64 位入口共用同一 helper，**不得**留旧 `semiTick` 路径（否则等价于隐藏的不一致）。

### 3. `SYS_TICKFREQ (0x31)`

- 保持 `GEM5-018t` 行为：`rd8 = 1e9`；只把常量改为「共享常量」，值不变。

### 4. 不变项（回归面）

- 服务集仍为 **25 个**（`--dump-semihost-services` 键与 `spec §5.3` 集合相等）；`SYS_EXIT`/`SYS_EXIT_EXTENDED` 退出码低 8 位传播不变；`SYS_WRITEC`/`SYS_WRITE0` 的 `rd8=0xdeadbeef` 保留标记不变；`ret_rd8` 的 `rd31=0x5A5A` 哨兵不变；SE（`configs/dadao/se.py`）行为逐字节不变。
- `SYS_CLOCK`/`SYS_TIME` **非目标**（基类已按真实仿真时间给 centiseconds/epoch；若用户要求一并统一，另立任务）。

### 5. 补丁/构建流程（`docs/Process-01 §6`）

1. 起点自检 `make check-source-state`（gem5 `HEAD=base+1`、干净）。
2. 在 `.work/source/gem5` 内改源码并收敛为「base + 恰好 1 commit」（amend/重放均可）；**禁止**手改 `components/gem5/patches/**`。
3. `python3 tools/infra/make_patch.py gem5` 导出（一文件一补丁；`series` 行数 = 磁盘 patch 数，字典序）。
4. `make check-patch-tree`、`make check-source-state` rc=0。
5. `make build-gem5`（SCons，`-j8`；增量重编申报耗时；用 background + 日志 + `*_EXIT`，禁 `setsid nohup` 后失联）。

## 文件范围

**修改**（全部在 `components/gem5/` + 两本册）：

- `components/gem5/patches/src/arch/dadao/semihosting.cc.patch`（`SYS_ELAPSED` 换算 + 共享常量；`callTickFreq` 改用共享常量）
- `components/gem5/patches/src/arch/dadao/semihosting.hh.patch`（新增/调整声明与注释；**必须删掉**「`SYS_ELAPSED` 仍走通用 `semiTick`、本任务不动」的过时注释）
- `components/gem5/README.md`（**必须更新** semihosting 段：删除「`SYS_ELAPSED` 仍走通用 `semiTick`」，写明与 `TICKFREQ` 共用 1e9 基准）
- `components/gem5/changelog.md`（`## M11` 节追加 `- **2026-11-04 GEM5-019t**` + `  - 摘要：…` + `  - 执行者：engineer`）
- `.tao/tasks/gem5/GEM5-019t-SYS_ELAPSED与TICKFREQ时钟一致.md`（本册）、`.tao/knowledge/milestones.md`（流水行）

**不改**：`tools/**`（含 `run_parity.py` 的 stale 表、`build_gem5.py`、`min_rom_probe_046t.py`）、`tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`components/qemu/**`、`components/gem5/series`（**不新增**补丁文件）、`Makefile`、`manifests/**`、`docs/**`。证据/临时物只落 `.work/evidence/GEM5-019t/**`、`.work/log/gem5/**`、`/tmp/opencode/GEM5-019t/**`。

## 验收标准

1. **补丁/源树/构建**：`make check-patch-tree` rc=0（gem5 作用域；补丁数现场统计）、`make check-source-state` rc=0（gem5 `count=1 clean=True`）、`make build-gem5` rc=0、`gem5.opt --help` rc=0。
2. **同 case 通过（`ADR-0048 D1/D2`）**：
   - QEMU system：`DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_046t.py --only svc_elapsed --qemu .dadao/cross-toolchain/bin/qemu-system-dadao` ⇒ rc=0（`exit=0x75`、`rd8=0`）。
   - gem5 FS：同上但 `--qemu tools/testcases/parity/qemu_gem5_shim.py`，并设 `PARITY_GEM5=<gem5.opt>`、`PARITY_GEM5_CONFIG=<fs.py>`、`PARITY_GEM5_PROFILE=node`、`PARITY_GEM5_BOOTROM=<step5 bootrom>`、`PARITY_WORK_ROOT=/tmp/opencode/GEM5-019t/shim` ⇒ rc=0，`rd50` 非零。
   - parity（**一次全量运行同时覆盖本条与第 7 条**）：`python3 tools/testcases/parity/run_parity.py --profiles node --scopes arch --qemu <qemu> --gem5 <gem5.opt> --gem5-config <fs.py> --work-dir /tmp/opencode/GEM5-019t/parity --json <json>` ⇒ JSON 中 `arch/probe/min_rom_probe_046t/svc_elapsed` 行 `qemu=PASS`、`gem5=PASS`、`verdict=AGREE_PASS`。注意 `--only` 只是“跑完后过滤行”，仍会执行整组 arch（含 10 个 umon + 全部 probe，实测 >5 min），**必须 background + 充裕 timeout + 日志/`*_EXIT`**；`--only` 下 driver rc=0（stale 检查不参与），全量下 driver rc=1（见第 7 条）。
3. **单位一致性（独立 oracle，必须能失败）**：
   - 证据脚本 `.work/evidence/GEM5-019t/**` 内的 `probe_elapsed.py`（**不入库**，`.work/` 已 ignored）用 046t 的只读 helper（`build_rom`/`sh_call`/`ld_o`/`set_addr`/`exit_seq`）构造一次性 Node ROM：`TICKFREQ` → 存 `rd8`；`ELAPSED` → `E1`；固定长度延迟（`T2-T1 >= 2000` ticks，现场记录指令数）；`ELAPSED` → `E2`；退出前把 `E1/E2/F` 放到 `rd50/51/52`。
   - 直接跑 gem5（保留 outdir 与 debug 日志）：
     `gem5.opt --outdir <O> --debug-flags=Semihosting --debug-file=<D> .work/source/gem5/configs/dadao/fs.py --profile node --bootrom <rom> --semihost on --semihost-system native --trace-cpu <C>`
   - `F`（`rd52`）== `1000000000`。
   - 从 `<D>` 取两条 `DADAO semihosting call64: SYS_ELAPSED` 行首的 tick 前缀 `T1/T2`；从 gem5 启动横幅 `Global frequency set at <N> ticks per second` 取 `N`（并核 `src/sim/core.cc` 的 `_ticksPerSecond`）——**不得**用实现自己算出的值反推 `N`。
   - 断言逐样本恒等：`E1 == T1 * 10^9 // N`、`E2 == T2 * 10^9 // N`（Python 大整数）；`E2 > E1`、`T2 - T1 >= 2000`；由此 `E2-E1 == floor(T2*10^9/N) - floor(T1*10^9/N)`。若实测 `curTick()` 与 debug 前缀差 1 tick（CPU 推进时序），允许在实现中加一行 `DPRINTF` 打印 `curTick()` 及换算输入以取得精确值，**不得**放宽容差到掩盖 3.9× 偏差。
   - 反空转断言：对同一 `T1/T2`，旧映射 `T >> 8` 至少一个与观测 `E` 不等（`N=10^12` 时相差 3.90625×）。
   - **本探针只在 gem5 上跑**（QEMU 的 `ELAPSED` 是 host 时间、gem5 是模拟时间，数值不可跨引擎比较，`ADR-0048 D2`）；QEMU 侧只做第 2 条同 case。
4. **`SYS_TICKFREQ` 回归**：5 条探针（`semihost_tag_path`/`semihost_cfxha_agnostic`/`bank_num_rd16`/`ret_rd8`/`svc_tickfreq`）在 gem5 上全 PASS，`rd8 == 1000000000`；`ret_rd8` 的 `rd31 == 0x5A5A`。
5. **046t 全量回归**：gem5 现场 `--list` 枚举的全部 case（现场计数，`GEM5-018t` 基线 32）全 PASS；`--list` 的服务覆盖行仍为 25。
6. **B0–B7 / SE 零退化**：`make check-gem5-decode` rc=0（`264/264 + 388/388 + 28/28 + 2/2`）；`python3 tools/gem5/check_converge.py` rc=0（264 ids + 1848 边界，`[FAIL] 0`）；SE `hello`（stdout `ok\n`、rc=0）与 `fail`（rc=7）与 `GEM5-014t` 基线逐字节一致。
7. **node/arch parity 无新差异**：全量 `--profiles node --scopes arch` 重跑；矩阵 JSON 中 `DIFF=0`、`GEM5_ONLY_FAIL=0`、`QEMU_ONLY_FAIL=0`，`svc_elapsed` 行为 `AGREE_PASS`，行数与 `AGREE_PASS`/`BLOCKED_SIDE`（icount N/A）计数由现场统计；**driver rc=1 仅由 `KNOWN_GEM5_BLOCKED` 7 条 stale 解释**（`tools/**` 另立任务清理），不得把它算成本任务绿，也不得因此改 tools。
8. **范围与门控**：`git diff --name-only <base>` 只命中「文件范围」列出的文件；`check-component-changelog`、`check-milestones-fresh`、`check-tasks`、`check-no-residue`、`check-dirs`、`check-knowledge-refs` rc=0（或「本任务新增悬空 0 + 既有红逐条基线复现」，`GEM5-018t` 基线：krefs 72 悬空）；无 `*_tmp*`/`*.orig`/`*.rej`/`m5out/`/`__pycache__` 残留入库。
9. **L1/L2**：`make check`（L1）rc=0，或「本任务红=0 + 既有红逐条基线复现」；`make check-modules`（L2）rc=0；若被共享 `install-host`/`build-builtins`/`gate.lock` 阻塞 ⇒ 记 **BLOCKED + 现场日志**（不得伪装 PASS）。
10. **证据/注入/完成区**：`.work/evidence/GEM5-019t/**` 一键 `run.sh`（分 phase，逐项 `*_EXIT=<rc>`）+ `REPORT.md`（数字全部由脚本现场生成）；`run.sh --inject` 对下列反例**可达 FAIL**（`cp` 备份 + md5 对账还原，禁 `git checkout`/`restore`/`stash`），注入后重建、跑红、还原、重建、回绿；完成区 ≤30 行、审阅记录每轮 ≤40 行，状态 `待验收`。
11. **BLOCKED 纪律**：任何无法成立的项按「spec/资产引用 + 根因 + 现场日志 + 为何不是本任务缺陷」登记，并经用户裁定；不得自行跳过、改期望、改 tests/tools/QEMU、把 QEMU 红算 gem5 绿。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **退回旧映射**：不覆盖 `callElapsed32/64`（或让它们返回 `semiTick(curTick())`）⇒ 单位探针 FAIL（`E ≈ 3.90625 × floor(T*10^9/N)`，逐样本恒等不成立）；还原 + 重建 ⇒ 回绿。
2. **只改不可达入口**：只改 32 位 `callElapsed32`（DADAO 恒 64 位、guest 不可达）⇒ 实际调用的 64 位入口仍返回旧值 ⇒ 单位探针 FAIL（证明覆盖必须落在派发路径上）；反过来只改 64 位可接受，但 32 位入口不得留旧 `semiTick` 路径（须共用 helper 或注释说明不可达）。
3. **常量写错**：共享常量 `1e9` 改 `1e8` 或 `1e12`（或 `TICKFREQ` 改回 `semiTick(Frequency)=3906250000`）⇒ 单位探针/5 条 TICKFREQ 探针 FAIL。
4. **64 位溢出**：把换算改成 `((uint64_t)curTick() * 1000000000ULL) / Frequency` ⇒ 证据脚本的静态 64 位乘法断言 + 边界值复算 FAIL（`Tick=2^63-1` 时乘积溢出）。
5. **空跑/少跑**：`--only` 到不存在的 case、或 046t 枚举为空、或 debug 日志缺 `SYS_ELAPSED` 行 ⇒ 驱动/证据脚本 rc=2/rc=1（fail-closed），不得绿灯。
6. **实现自证**：用实现算出的 `E` 反推 `N` 或直接比较 `E` 与 `E` ⇒ 证据门 FAIL（必须用启动横幅 `N` + debug tick 前缀独立复算）。

## 证据

- `.work/evidence/GEM5-019t/**`：`run.sh`（phase：起点自检 → 补丁/门控 → 构建 → 服务表/静态 → 046t 全量 + 5 条 TICKFREQ → 单位探针 → parity 单 case + node/arch 全量 → B0–B7/SE → 协议/范围门控 → L1/L2），每 phase 落 `*_EXIT=<rc>`；日志 `.work/log/gem5/**`、`/tmp/opencode/GEM5-019t/**`。
- `REPORT.md`：数字由脚本现场生成（补丁数、`--dump-semihost-services` 键数、046t case 数、`E1/E2/F/T1/T2/N`、parity 行数与 verdict 计数、注入表「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」）；不得手写数字。
- 引擎身份：gem5 `md5`、组件源 `git rev-parse HEAD`、`configs/dadao/fs.py` md5、启动横幅的频率行；QEMU `md5`/`--version`；bootrom md5；工具链（clang/lld/mc/objcopy）md5 现场采集。
- 依赖缺失（`gem5.opt`、`scons`、parity 工具、bootrom、工具链）⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明（风险 / 非目标 / 溯源 / 待确认）

### 1. 与 `GEM5-018t` 的关系

- `GEM5-018t` 已把 `SYS_TICKFREQ` 改为 1e9，并明确 `SYS_ELAPSED` 不在其范围（R4 遗留）；本任务只收口该遗留，不重做 046t 的其它服务修复，不重跑 017t 的 inst/embench 全矩阵。

### 2. 风险

- **R1 构建成本**：改 `semihosting.{hh,cc}` 触发 gem5 重编（预估增量 2–10 分钟）；注入需 2 轮重建（红/绿），须申报耗时、落日志与 `*_EXIT`，用 background，禁 `setsid nohup` 后失联。
- **R2 单位探针的 tick 对齐**：debug 前缀的 tick 与 `curTick()` 在 AtomicSimpleCPU 同一 `tick()` 内应相同；若现场差 1 tick，按第 3 条以 `DPRINTF` 打印 `curTick()` 取精确值，并在证据中说明；不得用实现的输出充当 oracle。
- **R3 parity stale 注册表**：全量 driver rc=1 是预期（7 条 stale），`--only` 单 case 必须 rc=0；两者都不得记为「本任务失败/成功」的替代证据。
- **R4 fresh worktree 构建**：`.work/build` 为空时 L2 会做全量 LLVM、`build_picolibc.py` 拒绝符号链接 rmtree；沿用 `GEM5-018t` 的复用策略（仅 gem5 本地构建，picolibc 本地重建），不得污染真实仓库。
- **R5 L1 既有红**：`check-knowledge-refs` 在主 worktree 有既有悬空（`GEM5-018t` 评审实测 72 条）；只允许「本任务新增 0 + 既有逐条复现」判 PASS。
- **R6 语义边界**：若 engineer 认为「ELAPSED 起点应减 `timeBaseTick`」与 QEMU 不一致，须**先停**、留现场并交用户裁定（不得自行改语义）；本册按 QEMU `clock_start`（引擎起点）写判据。

### 3. 非目标

- 不改 QEMU / spec / contracts / tests / tools / Makefile / manifests / docs；不删 `run_parity.py` 的 stale `KNOWN_GEM5_BLOCKED`（另立 **tools** 任务）；不修 `tools/gem5/build_gem5.py` 的 `relative_to` 缺陷（另立 **INFRA** 任务）。
- 不改 `SYS_CLOCK`/`SYS_TIME`/`SYS_SYNCCACHE` 等其它服务；不做 cfxha 重编号、M11 收尾、B7 数值差异（`math_test`）、SE 行为变更。
- 不新增 `tools/**` 资产；单位探针是**证据脚本**（`.work/`，不入库）；若需长期保留，另立 `TESTCASES` 任务。

### 4. 参考对照（内容溯源，非执行必需）

- `spec/Machine-v5-测试机运行环境.md §5.3`；`.tao/contracts/contract-semihosting.md §2/§3/§4`；`.tao/contracts/contract-see.md` 的 `cfx_time`；`spec/DADAO-12-SEE-主管系统运行环境.md §4.10`；`ADR-0020 D2/D4`；`ADR-0048 D1/D2/D5`；`discussing.md` 2026-11-04 `SYS_TICKFREQ` 基线。
- QEMU `target/dadao/cpu.h` 的 `DADAO_TIME_FREQ`、`semihosting/arm-compat-semi.c` 的 ELAPSED/TICKFREQ、`include/qemu/timer.h` 的 `get_clock()` 仅作**跨引擎一致性对照**，不是 spec 正文。
- `DADAO-0628` 只读检索（`semihosting`/`SYS_ELAPSED`/`TICKFREQ` 均 0 命中，无 gem5 时钟实现可借鉴）；**内容溯源，非执行必需**，不复制代码/常量/测试。

### 5. 待确认口径（本册已按推荐值写，用户可否决）

1. `SYS_ELAPSED` 基准 = `curTick()`（引擎起点），不减 `timeBaseTick`（`cfx_time` 复位基准）。
2. 共享常量 = `1e9`（不写死 `3.90625e9`，也不用 `semiTick` 的派生单位）。
3. 32 位 `callElapsed32` 入口保留但共用 helper（DADAO 恒 64 位、guest 不可达）。
4. stale parity 表与 `build_gem5.py` 缺陷不在本任务（分别另立 tools / INFRA 任务）。
5. 若用户决定把「1e9 ticks/s」固化进 spec/contract，另立 **SPEC/ADR** 任务；本任务不改 spec/合约。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
