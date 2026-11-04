# GEM5-018t: FS semihosting 修复（WRITEC/WRITE0 rd8 保留标记 + SYS_TICKFREQ=1e9）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-017t`（FS 同模式 parity，**必须已验证**并给出本任务 4 项服务（`SYS_TICKFREQ`/`SYS_WRITEC`/`SYS_WRITE0`/`SYS_READC`）的逐 case 差异证据；未验证或缺少该证据 ⇒ 本任务 BLOCKED，禁止凭推测开工）、`GEM5-015t`（FS Tiny + 25 服务 semihosting，已验证）、`GEM5-016t`（FS Node / cfx / PTW，已验证）、`SPEC-183t`（`spec/Machine-v5-测试机运行环境.md` 真源，已验证）、`TESTCASES-094t`（L3 探针与 `min_rom_probe_046t` 资产，已验证，只读复用）、`ADR-0020`（semihosting 调用/返回）、`ADR-0048`（QEMU/gem5 同模式一致性）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；从含 `GEM5-017t` 的 `master` 建独立 `git worktree` + 分支 `GEM5-018t`；**只改 `components/gem5/**` + 本任务书 + `.tao/knowledge/milestones.md`**；证据落 `.work/evidence/GEM5-018t/**`、`.work/log/gem5/**`、`/tmp/opencode/GEM5-018t/**`）。开工前必须确认：① `GEM5-017t` 已 `已验证` 且已合入 `master`；② `tools/testcases/parity/run_parity.py` 与 `qemu_gem5_shim.py` 存在且能跑 046t（`-chardev ...,input-path=` 被接受）；③ `.work/build/gem5/**/gem5.opt`（或 `.work/source/gem5/build/DADAO/gem5.opt`）存在可跑；任一项不成立 ⇒ **rc=2 BLOCKED**，不得用旧日志/旧二进制冒充。

## 用户已定口径（2026-11-04，主会话转达）

- **只修 2 条真缺陷**（均由 `GEM5-017t` 的 parity 发现）：① `SYS_WRITEC`/`SYS_WRITE0` 的 `rd8`；② `SYS_TICKFREQ` 的返回值（含 5 条以 `rd8` 判定的探针）。
- **`SYS_TICKFREQ` 基线 = `1e9` ticks/秒**（`discussing.md` 2026-11-04：「统一按 1e9；QEMU/gem5 同模式一致；spec 当前未定义具体值」）。当前 gem5 返回 `1e12 >> 8 = 3906250000`，不符合基线。
- **`SYS_READC` 的 shim `input-path` 归 `GEM5-017t` 修，不在本任务**：本任务**只做回归**；`GEM5-017t` 若已修好则 `svc_readc` 必须 PASS；未修好则登记 **BLOCKED + 根因**，不得在本任务改 `tools/**`、不得把 BLOCKED 记成 PASS。
- **不改** `components/qemu/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`tests/**`、`tools/**`、`Makefile`、`manifests/**`、`docs/**`；**不复制** `DADAO-0628`（只读溯源，标「内容溯源，非执行必需」）。
- **同模式一致规则**（`ADR-0048 D1/D2/D5`）：只比较 gem5 FS ↔ QEMU system 的同 case 结果（通过/失败、退出码、架构可见结果）；不比较时序/性能/日志格式；spec/契约不清 ⇒ 保留现场、提交用户裁定，不得按经验反推。

## 现场事实与缺陷判定（2026-11-04 只读核对；开工后须以 `GEM5-017t` 现场证据复核）

### F1 `SYS_WRITEC` / `SYS_WRITE0` 的 `rd8`

- **规范口径**：`contract-semihosting §3` 与 `spec/Machine-v5-测试机运行环境.md §5.3` 均记两者「无返回」；`§4` 的返回机制写 `rd8`，但这两项无定义返回值。
- **QEMU 现状**：共享层用 `0xdeadbeef` 作为「无返回」保留标记 —— `semihosting/arm-compat-semi.c` 的 `common_semi_dead_cb()` 写 `0xdeadbeef`（该文件注释原文「Use 0xdeadbeef as the return value when there isn't a defined return value for the call.」），`TARGET_SYS_WRITEC`/`TARGET_SYS_WRITE0` 均走该回调；`QEMU-055t` 归档亦记「0xdeadbeef（无返回标记），随返回寄存器移至 rd8」。
- **gem5 现状**：`callConsoleWriteC`/`callConsoleWrite0` 返回 `retOK(0)`，`Result<Abi, RetErrno>::store` 无条件写 `rd8` ⇒ guest 观测 `rd8 = 0`（与 QEMU 的 `0xdeadbeef` 不同）。
- **parity 资产期望**：`tools/testcases/arch/min_rom_probe_046t.py` 的 `svc_writec`（exit `0x62`、`out=b"Y"`、`rd8=0xdeadbeef`）与 `svc_write0`（exit `0x63`、`out=b"hi046"`、`rd8=0xdeadbeef`）。
- **本任务判定**：`rd8` 取「无返回保留标记 `0xdeadbeef`」（与 QEMU/046t 一致）；**不是**写业务返回值 `0`。控制台字节、`IP += 4`、其余寄存器（含 `rd31`）均不变。

### F2 `SYS_TICKFREQ`

- **规范口径**：`contract-semihosting §3` / `spec §5.3` 为「无参数；返回 ticks/秒 / `-1`」；**具体值**由用户 2026-11-04 定为 **`1e9`**（`discussing.md`）。
- **gem5 现状**：`src/arch/generic/semihosting.cc` 的 `BaseSemihosting::callTickFreq()` 返回 `semiTick(sim_clock::Frequency)`；`semiTick(t) = t >> tickShift`，`tickShift = max(0, msb(Frequency) - 31)`。`sim_clock::Frequency = 1e12` ⇒ `msb = 39`、`tickShift = 8` ⇒ 返回 **`3906250000`**（=`1e12/256`）。
- **5 条受影响探针**（均在 `min_rom_probe_046t`，均断言 `rd8 = 1000000000`）：
  `semihost_tag_path`（exit `0x5A`）、`semihost_cfxha_agnostic`（`0x5E`）、`bank_num_rd16`（`0x5B`）、`ret_rd8`（`0x5D`，另断言 `rd31=0x5A5A`）、`svc_tickfreq`（`0x76`）。
- **本任务判定**：这 5 条必须 PASS；`rd8` 恰为 `1000000000`。

### F3 `SYS_READC`（只回归，不改）

- `min_rom_probe_046t.svc_readc` 用 `rb1-1` 作 1 字节缓冲，期望 `rd8=0x51`、exit `0x66`，输入由 `-chardev file,id=semi,path=<out>,input-path=<in>` 提供。
- gem5 侧无输入通道映射，归 `GEM5-017t` 的 shim；本任务**不实现** `input-path`，只在 017t 完成后回归该 case。

## 接口规范

### 1. `SYS_WRITEC (0x03)` / `SYS_WRITE0 (0x04)`

- 行为不变：`WRITEC` 写 `rb16` 指向的单字节；`WRITE0` 写以 NUL 结尾字符串（`portProxy(...).readString`）；二者写 `--console-out`（默认 stdout）后 `fflush`；`IP` 由正常顺序步进 `+4`（`contract-semihosting §4`）。
- **返回值**：写 `rd8 = 0xdeadbeef`（「无返回」保留标记）。实现上定义一个具名常量（如 `Semihosting::noReturnMark`）并在两处复用，附注释说明「QEMU 共享层 `common_semi_dead_cb` + `QEMU-055t` 归档 + 046t 期望」，**不得**把它写成 spec 正文断言（spec 只写「无返回」）。
- **不得**改 `Result::store` 的通用写 `rd8` 机制，**不得**改 `src/arch/generic/semihosting.*`（上游共用文件）。

### 2. `SYS_TICKFREQ (0x31)`

- 返回 `rd8 = 1000000000`（常量 `1000 * 1000 * 1000`，注释引 `discussing.md` 2026-11-04 基线）。
- 实现方式（最小改动）：在 `DadaoISA::Semihosting` **新增** `callTickFreq(ThreadContext *)` 覆盖/hide 基类同名方法，并把 `calls` 表中 `SYS_TICKFREQ` 指向它；**不改** `BaseSemihosting::callTickFreq`、**不改** `calcTickShift`/`semiTick`（`SYS_ELAPSED` 仍走原 `semiTick`，本任务不动）。
- 无参数服务：`rb16` 内容不读；不写除 `rd8` 外的寄存器（`ret_rd8` 断言 `rd31` 哨兵不变）。

### 3. `SYS_READC (0x07)`（回归项）

- 与 QEMU 同 case 比较（`rd8`=读到的字节、exit）；若 `GEM5-017t` shim 尚未支持 `input-path` ⇒ 该 case 记 **BLOCKED**（根因：shim 缺输入通道，属 017t），不计 PASS/FAIL，不影响本任务对 F1/F2 的判决。

### 4. 不变项（回归面）

- 服务集仍为 **25 个**（`--dump-semihost-services` 的键与 `spec §5.3` 集合相等）；`SYS_EXIT`/`SYS_EXIT_EXTENDED` 退出码低 8 位传播（`300 ⇒ 44`）；`SYS_WRITE`/`SYS_READ`/`SYS_OPEN` 等其余服务行为不变；`IP += 4` 与「不进入 cfx 向量」的入口判定不变（`immu18[17:8]==0x3FF`，与 `cfxha` 无关）。
- SE（`configs/dadao/se.py`）不走 semihosting，行为必须逐字节保持。

### 5. 补丁/构建流程（`docs/Process-01 §6`）

1. 起点自检：`make check-source-state`（gem5 HEAD = base+1、worktree 干净）；不满足先收敛，不得带脏树开改。
2. 在 `.work/source/gem5` 内改源码（**禁止**手改 `components/gem5/patches/**`），提交并收敛为「base + 恰好 1 commit」。
3. `python3 tools/infra/make_patch.py gem5` 导出补丁（一文件一补丁；`series` 行数 = 磁盘 patch 数、字典序）。
4. `make check-patch-tree`、`make check-source-state` 均 rc=0。
5. `make build-gem5`（SCons；`-j8`；增量重编申报耗时，用 background + 日志 + `*_EXIT`，禁 `setsid nohup` 后失联）。

## 文件范围

**修改**（全部在 `components/gem5/` 内，另加两本册）：
- `components/gem5/patches/src/arch/dadao/semihosting.cc.patch`（`calls` 表 `0x31` 指向新方法；`WRITEC`/`WRITE0` 返回保留标记；新增 `callTickFreq` 实现；常量/注释）
- `components/gem5/patches/src/arch/dadao/semihosting.hh.patch`（`callTickFreq` 声明、`noReturnMark` 常量）
- `components/gem5/changelog.md`（`## M11` 节内追加一条 `- **2026-11-04 GEM5-018t**` + `  - 摘要：…` + `  - 执行者：engineer`）
- `components/gem5/README.md`（若「当前状态」段列任务覆盖，则补一条；无则不强制）
- `.tao/tasks/gem5/GEM5-018t-FS-semihosting修复.md`（本册）、`.tao/knowledge/milestones.md`（流水行）

**不改**：`components/qemu/**`、`components/gem5/series`（**不新增补丁文件**）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`tests/**`（含 `tools/testcases/arch/min_rom_probe_046t.py`）、`tools/**`、`Makefile`、`manifests/**`、`docs/**`。证据/临时物只落 `.work/evidence/GEM5-018t/**`、`.work/log/gem5/**`、`/tmp/opencode/GEM5-018t/**`。

## 验收标准

1. **补丁/源树/构建**：`make check-patch-tree` rc=0（gem5 作用域；补丁数现场统计）、`make check-source-state` rc=0（`count=1`、`clean=True`）、`make build-gem5` rc=0、`gem5.opt --help` rc=0。
2. **F1 `WRITEC`/`WRITE0`**：`min_rom_probe_046t` 的 `svc_writec` / `svc_write0` 在 gem5（Node profile，经 017t shim）PASS：exit/控制台字节与用例一致，**`rd8 == 0xdeadbeef`**；`tests/arch/umon/m5_semi_writec.s` / `m5_semi_write0.s` 的 10 smoke 仍全 PASS（控制台字节不变）。
3. **F2 `TICKFREQ`**：上述 5 条探针（`semihost_tag_path`/`semihost_cfxha_agnostic`/`bank_num_rd16`/`ret_rd8`/`svc_tickfreq`）在 gem5 上全 PASS，`rd8 == 1000000000`；其中 `ret_rd8` 的 `rd31 == 0x5A5A` 不变。
4. **F3 `READC` 回归**：`svc_readc` 在 gem5 上 PASS（`rd8=0x51`、exit `0x66`）；若 `GEM5-017t` shim 未支持 `input-path` ⇒ 记 **BLOCKED**（附 shim rc/错误串 + 017t 归属），**不得**算 PASS、**不得**在本任务改 shim。
5. **parity 复跑**：`python3 tools/testcases/parity/run_parity.py --profiles node --scopes arch --only <上述 case_id>` 对 4 项服务重跑，`GEM5_ONLY_FAIL == 0`、无未归因 `DIFF`；`--markdown` 输出与证据 JSON 逐项一致（case ID 取 `GEM5-017t §1`；接口有偏差以 017t 实测为准并记录，不改 017t 工具）。
6. **全探针回归**：`min_rom_probe_046t` 现场 `--list` 枚举的**全部 case** 在 gem5 上重跑（除 `svc_readc` 可能 BLOCKED 外）全 PASS；不得少跑/跳过用例。
7. **B0–B7 零退化**：`make check-gem5-decode` rc=0（`264/264` + `388/388` + `28/28` + `2/2`）；`python3 tools/gem5/check_converge.py` rc=0（264 ids + 1848 边界，B1–B7 计数与基线一致，`[FAIL] 0`）。
8. **SE 零退化**：`configs/dadao/se.py` 的 `hello`（stdout `ok\n`、rc=0）与 `fail`（rc=7）与 `GEM5-014t` 基线逐字节一致；SE 不受 semihosting 改动影响。
9. **L1/L2**：`make check`（L1）rc=0，或「本任务红=0 + 既有红逐条基线复现」；`make check-modules`（L2）rc=0，若被共享 `install-host`/`build-builtins`/`gate.lock` 阻塞 ⇒ 记 **BLOCKED + 现场日志**（不得伪装 PASS）。
10. **范围与门控**：`git diff --name-only <base>` 只命中 `components/gem5/**` + 本册 + `milestones.md`；`check-component-changelog`/`check-milestones-fresh`/`check-tasks`/`check-no-residue`/`check-dirs`/`check-knowledge-refs` rc=0（或本任务悬空 0 + 既有红逐条基线）；无 `*_tmp*`/`*.orig`/`*.rej`/`m5out/`/`__pycache__` 残留入库。
11. **证据/注入/完成区**：`.work/evidence/GEM5-018t/**` 一键 `run.sh`（分 phase，逐项 `*_EXIT=<rc>`）+ `REPORT.md`；`run.sh --inject` 对 F1/F2 **各至少 1 类**可达 FAIL（`cp` 备份 + md5 对账还原，禁 `git checkout`/`restore`/`stash`），注入后重建、跑红、还原、重建、回绿；完成区 ≤30 行，状态 `待验收`。
12. **状态/BLOCKED**：任何无法成立的项按「spec/资产引用 + 根因 + 现场日志 + 为何不是本任务缺陷」登记 BLOCKED 并经用户裁定；不得自行跳过、改期望、改 tests/QEMU、把 QEMU 红算 gem5 绿。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **`WRITEC`/`WRITE0` 退回 0**：把两处返回值改回 `retOK(0)` ⇒ 重建后 `svc_writec`/`svc_write0` FAIL（`rd8 exp=0xdeadbeef got=0x0`）；还原 + 重建 ⇒ 回绿。
2. **`TICKFREQ` 退回 `semiTick(Frequency)`**（或硬编码 `3906250000`）⇒ 5 条探针 FAIL（`rd8 exp=1000000000`）；还原 + 重建 ⇒ 回绿。
3. **只修 `svc_tickfreq` 不修其余 4 条**（例如只对 `svc_tickfreq` 特判）⇒ 其余 4 条仍 FAIL（证明 5 条由同一服务路径覆盖，不是按用例特判）。
4. **`rd8` 写错位置**（改成写 `rd16`/`rd31`）⇒ 对应 case FAIL，且 `ret_rd8` 的 `rd31` 哨兵被破坏 ⇒ FAIL；还原回绿。
5. **空跑/少跑**：`--only` 到不存在的 case、或 046t 枚举为空 ⇒ 驱动 rc=2/rc=1（fail-closed），不得绿灯。
6. **`READC` 冒充 PASS**：shim 不支持 `input-path` 时把该 case 记 PASS ⇒ 证据门 FAIL（必须为 BLOCKED 并带 shim 现场）；还原回绿。
7. **补丁手改**：直接改 `components/gem5/patches/**` 而不改源树 ⇒ `check-patch-tree` 断言⑥/⑨ FAIL（`cp` 还原后回绿）。

## 证据

- `.work/evidence/GEM5-018t/**`：`run.sh`（phase：起点自检 → 补丁导出/门控 → 构建 → 服务表/静态比对 → 046t 4 项 + 全量探针 → parity 复跑 → B0–B7 → SE → L1/L2 → 注入），每 phase 落 `*_EXIT=<rc>`；日志 `.work/log/gem5/**` 与 `/tmp/opencode/GEM5-018t/**`（gem5 `--outdir` 只落后者）。
- `REPORT.md`：所有数字由脚本现场生成（补丁数、`--dump-semihost-services` 键数、case 计数、`rd8` 观测、注入表「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」）；不得手写数字。
- 引擎身份：gem5 `md5` + 组件源 `git rev-parse` + `configs/dadao/fs.py` md5；QEMU `md5`/`--version`（parity 对照侧）；bootrom md5；工具链（clang/lld/mc/objcopy）md5 现场采集。
- 依赖缺失（`gem5.opt`、`scons`、017t parity 工具、bootrom、工具链）⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明（风险 / 非目标 / 溯源 / 待确认）

### 1. 与 GEM5-015/016/017 的关系
- 本任务**不重做** 015/016 的 FS 平台验收，只修 017t 发现的 2 条 semihosting 行为差异；017t 的矩阵/REPORT 是本任务的输入（`.work/evidence/GEM5-017t/**`），必须现场复核，不直接引用旧数字。
- 017t 的 `RUN_PARITY` 若对 `arch` 探针全量跑，本任务只重跑受影响 case + 046t 全量；**不重复** 017t 的 inst/embench 全矩阵。

### 2. 风险
- **R1 构建成本**：改 `semihosting.{hh,cc}` 触发 gem5 重编（预估 5–20 分钟）；注入需 2 轮重建（红/绿），须申报耗时、落日志与 `*_EXIT`。
- **R2 `rd8` 语义歧义**：用户原话「`WRITEC`/`WRITE0` 不写 `rd8`（按 spec/QEMU 保留）」有两种解读：(a) 写 QEMU/046t 的 `0xdeadbeef` 保留标记（**本册按此落验收**，理由：QEMU 实测 + 046t 期望 + 无返回标记惯例）；(b) 完全不动 `rd8`（保持调用前值）——该解读与 046t `svc_writec`/`svc_write0` 的 `rd8=0xdeadbeef` 及 QEMU 实现直接冲突，且需改通用 `Result::store`，属新语义决策。若用户确认是 (b)，本任务 **BLOCKED + 另立 spec/contracts/tests 任务**，不得自行改资产。
- **R3 017t 接口漂移**：`run_parity.py`/`qemu_gem5_shim.py` 的 CLI、case ID、trace 字段以 017t 实测为准；若 017t 的 shim 不支持 `-chardev input-path`，046t 整体 rc=2 ⇒ 本任务 BLOCKED（归 017t），不得绕过。
- **R4 `SYS_ELAPSED` 口径**：`semiTick` 仍按 `1e12>>8` 产出 ticks，与 `TICKFREQ=1e9` 不自洽；本任务**不改** `ELAPSED`（非 2 条缺陷之一，046t `svc_elapsed` 只断言字段存在）；登记为遗留，建议另立任务由用户裁定。
- **R5 L1/L2 环境缺口**：`check-knowledge-refs` 可能因其它任务 `.work/**` 悬空而红；L2 可能停在 `install-host → build-builtins`。只允许登记 BLOCKED/基线红 + 现场，不得伪装 PASS。

### 3. 非目标
- 不改 QEMU/spec/contracts/tests/Makefile/manifests/docs；不改 `SYS_ELAPSED`/`SYS_CLOCK`/`SYS_TIME` 口径；不修 `READC` 的 shim；不做 cfxha 重编号、M11 收尾、B7 数值差异（`math_test`）；不动 SE。

### 4. 参考对照（内容溯源，非执行必需）
- `contract-semihosting §2/§3/§4`；`spec/Machine-v5-测试机运行环境.md §5.2/§5.3/§5.4`；`ADR-0020 D2/D4/D8`；`ADR-0048 D1/D2/D5`；`discussing.md` 2026-11-04 `SYS_TICKFREQ` 基线。
- QEMU 共享层 `semihosting/arm-compat-semi.c` 的 `common_semi_dead_cb` / `TARGET_SYS_TICKFREQ` 仅作**跨引擎一致性对照**，不作为 spec 正文；`DADAO-0628` 只读、仅吸收结论，**不复制代码/常量/测试**。

### 5. 待确认口径（本册已按推荐值写，用户可否决）
- ① `WRITEC`/`WRITE0` 采用 `rd8=0xdeadbeef` 保留标记（见 R2）；② `TICKFREQ` 用 DADAO 覆盖方法返回常量 `1e9`（不改 `ELAPSED`）；③ `READC` 只回归、BLOCKED 时不计 PASS；④ `check-source-state` 的 base 取 `manifests/components.lock.toml` 锁定 commit。

## 完成区

**测试结果**：046t `--list` 32 case 全 PASS（含 `svc_readc` 回归）；rd8 观测：`svc_writec`/`svc_write0`=0xdeadbeef，5 条 TICKFREQ=0x3b9aca00（`ret_rd8` 另验 rd31=0x5A5A）；node/arch parity 269 行 = AGREE_PASS 249 + icount N/A 20，7 条 GEM5-017t 缺陷行转 `gem5 PASS`/`AGREE_PASS`（无 `raw_status`），GEM5_ONLY_FAIL=0、DIFF=0、QEMU_ONLY_FAIL=0；decode 264/264+388/388+28/28+2/2、converge 264 ids+1848 边界 `[FAIL] 0`；SE hello stdout `ok\n` rc=0、fail rc=7；L2 rc=0；L1 rc=2 仅 `check-knowledge-refs` 既有红（本任务悬空 0，master 基线 72）。
**修改文件**：`components/gem5/patches/src/arch/dadao/semihosting.cc.patch`、`components/gem5/patches/src/arch/dadao/semihosting.hh.patch`（`noReturnMark=0xdeadbeef`、`callTickFreq()` 返回 1e9；`calls` 0x31 绑定原已指向 `callTickFreq`）、`components/gem5/changelog.md`、`components/gem5/README.md`、本册、`.tao/knowledge/milestones.md`；gem5 源树 base+1 = `12a4716`（仅 `semihosting.{cc,hh}`，其余 95 补丁不变）。
**验收结果**：`./.work/evidence/GEM5-018t/run.sh` rc=0（p0–p9 全绿；L1/krefs 既有红以「本任务 0 + master 基线复现」判 PASS）、`run.sh --inject` rc=0；`REPORT.md` + `logs/EXITS` 逐项留痕；`check-patch-tree` 302 补丁 OK、`check-source-state` gem5 `count=1 clean=True`、`build-gem5` rc=0、`--dump-semihost-services` 25 项与 `spec/Machine-v5 §5.3` 集合相等（现场派生）；注入表见 `logs/INJECT_TABLE.tsv`。
**新发现/坑**：① `tools/gem5/build_gem5.py` 末步 `(source/"build").relative_to(build_link.parent)` 在 `.work/build/gem5` 缺失（fresh worktree）时 ValueError ⇒ `make build-gem5` rc=2（scons 实已成功）；本任务按既有形态 `mkdir .work/build/gem5` 绕过，建议另立 INFRA 任务修。② fresh worktree 的 `.work/build` 为空 ⇒ L2 触发全量 LLVM（3573 目标）且 `build_picolibc.py` 拒绝对符号链接 rmtree；证据脚本改用主 worktree 的 llvm/qemu 构建树（picolibc 本地重建）。③ `run_parity.py` 的 `KNOWN_GEM5_BLOCKED` 令修复后 driver rc=1（7 条 stale），绿灯断言须读 matrix 行 + 日志分类。④ 046t `general_trap_path` 的 `services=` 为空，按 `services=0x` 计数会漏 1 例（31 vs 32）。⑤ 并发 L2 满载时 `integ042t/dma_busy_w1c_ignored` 的 QEMU 侧曾超时一次（3/3 重跑 PASS），重跑 parity 为 0 QEMU_ONLY_FAIL。
**遗留问题**：① 移除 `tools/testcases/parity/run_parity.py` 中 7 条 `KNOWN_GEM5_BLOCKED`（本任务禁改 `tools/**`，需另立 tools 任务；移除后 parity 才能 rc=0）。② 修 `build_gem5.py` 上述 relative_to 缺陷（INFRA）。③ `SYS_ELAPSED` 仍 `1e12>>8`，与 `TICKFREQ=1e9` 不自洽（本任务非目标 R4，需用户裁定另立任务）。④ `check-knowledge-refs` 既有红（worktree 缺其它任务 `.work/**` 证据；master 基线 72 悬空，本任务 0）。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：可验收（改动 2 源文件/2 补丁；逐行核对 `semihosting.{hh,cc}` diff、服务表与 `ret_rd8` 哨兵）。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 只改 `WRITEC` 漏 `WRITE0` | ✅已修（实现即两处同改） | 两处 `retOK(noReturnMark)` | `svc_writec`/`svc_write0` 均 rc=0、rd8=0xdeadbeef |
| 覆盖 `callTickFreq` 是否波及 `SYS_ELAPSED` | ❌不修（核后无影响） | 仅新增派生同名方法 + `calls` 0x31 指向它；`ELAPSED` 仍走基类 `semiTick` | `svc_elapsed` PASS；`src/arch/generic/**` 零改动 |
| `0xdeadbeef`/1e9 被写成 spec 断言的风险 | ❌不修（按任务口径） | 注释标明「QEMU 同模式对照 / 用户裁定，非 spec 正文」 | `spec/**`、`contracts/**` 零改动（p9 越界 0） |
| 046t 用例计数写死风险 | ✅已修 | 现场 `grep -cE 'services='`（32） | `p4-case-count expected=32 actual=32` |
| rd8 观测受 16 位前导零影响 | ✅已修 | 新增 `expect_hex` 归一化 | 5 条 `expected=0x3b9aca00 actual=0x3b9aca00` |
| 证据门可能恒真 | ✅已修 | `check_matrix.py --self-test` 篡改一行必 FAIL；另以 017t 修复前矩阵反证 | `p5-matrix-selftest rc=0`、`p5-prefix-negative rc=1`（22 issue） |
| F1 注入锚点断言写错（`retOK(0)` 计数含 `callSyncCache`） | ✅已修 | 改为断言注入前 `noReturnMark` 恰 2 次 | `run.sh --inject` F1 RED→回绿 |

**自审补充**：`retOK(0xdeadbeef)` 只经 `Result<Abi,RetErrno>::store` 写 rd8；控制台字节与 `IP+=4` 未动（046t 出口字节 + umon 10 smoke 全 PASS）。

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**（下列输出全部来自我本人的重跑/注入，不采信 engineer 转述）

**重跑记录**
- `./.work/evidence/GEM5-018t/run.sh` ⇒ **`RUN_EXIT=0`**，本轮 `logs/EXITS`：`p0..p4=0 p5=0 p6=0 p7=0 p8=0 p9=0`（`p8-L1=2`、`p9-check-knowledge-refs=2` = 既有红，见遗留④）
- p4 真实输出：`p4-case-count expected=32 actual=32`、`p4-fail-count 0`、`svc_writec`/`svc_write0` `rd8=0xdeadbeef`、5 条 TICKFREQ `0x3b9aca00`、`ret_rd8 rd31=0x5a5a`、`svc_readc rc=0 rd8=0x51`（shim 已接 `input-path`，非冒充 PASS）
- `run.sh --inject` ⇒ **`INJECT_EXIT=0`**：F1/F2 各 `build-red=0 / probe-red=1 / md5还原相等 / build-green=0 / probe-green=0 / tree-clean=0`；空跑 `no case named` rc=1
- parity：driver `rc=1`（7 条 stale，预期值）、`p5-matrix=0`、`p5-matrix-selftest=0`、017t 旧矩阵 negative `rc=1`
- 我独立解析 `matrix-node-arch.json`：269 行 = `AGREE_PASS 249 + BLOCKED_SIDE 20`（20 行均带 `icount` note）；7 缺陷行 `gem5=PASS / qemu=PASS / AGREE_PASS / 无 raw_status`；`gem5_only_fail=0 qemu_only_fail=0 diff=0`；md 行 `269|249|0|0|0|0|0|0|20|0` 与 JSON 一致
- p6 `positive 264/264, negative 388/388, legality 28/28, legacy 2/2, failures 0`、converge `ids 264/264, boundary 1848/1848 [FAIL] 0`；p7 SE `hello 6f6b0a rc=0`、`fail rc=7`；p9 五门控 rc=0、`changed files: 6`、residue 0
- L2 `p8-L2 rc=0`：`check-arch-smoke: PASS` + umon 10 例 `PASS`（console 字节逐字节一致）+ 046t `RESULT: PASS`
- L1 `rc=2` 仅 krefs；我在主 worktree 实测 `make check-knowledge-refs` ⇒ `结果: FAIL (72 悬空)` **rc=2**（既有红复现）；本树 155 悬空中 `GEM5-018t` 命中 **0**

**本人独立注入（非 engineer 自检）**
- ① 源树 `semihosting.hh` `noReturnMark 0xdeadbeef→0xdeadbeee`（md5 `a43ac6b5→d100534f`）→ `build-gem5 rc=0` → 同一脚本 `run.sh --phase p4` ⇒ **rc=1**（`p4-svc_writec-rd8 expected=0xdeadbeef actual=0xdeadbeee`、`p4-fail-count 0→2`）→ `cp` 还原 md5 `a43ac6b5` 相等 → 重建 `rc=0` → `--phase p4` ⇒ **rc=0**（FAIL 0）、源树 0 改动
- ② 手改 `semihosting.cc.patch` 追加一行 → `make check-patch-tree` ⇒ **rc=2**（`assertion ⑨ … local commit does not match the patch set`）→ `cp` 还原 md5 `61482fe4` 相等 → **rc=0**（`6 component(s), 302 patches OK`）

**约束核验**：改动恰 6 文件 = `components/gem5/{2 patch, changelog, README}` + 本册 + `milestones.md`；`tools/Makefile/spec/contracts/tests/qemu/manifests/docs` 零改动（审查前后 `git status` 快照逐行一致）；源树 `HEAD=12a4716 count=1 clean=True`；97 补丁 / 97 series、`check-patch-tree 302 OK`、25 服务 == `spec §5.3`；完成区 7 行（≤30）、自审 13 行（≤40）；状态 `待验收`；`run.sh` md5 `06166ea1` 未被改动；stale 未写成 PASS。

**遗留核验**：① `KNOWN_GEM5_BLOCKED` 7 条仍在 `tools/testcases/parity/run_parity.py`（本任务禁改 `tools/**`，移除后 driver 才 rc=0）⇒ driver `rc=1` 按预期登记，非绿灯；② `tools/gem5/build_gem5.py:95` `(source/"build").relative_to(build_link.parent)` 缺陷代码在场（fresh worktree 触发）；③ `SYS_ELAPSED` 仍走 `callElapsed32 → semiTick(curTick())`（`1e12>>8`），与 `TICKFREQ=1e9` 不自洽，遗留③待用户裁定、未洗成 PASS；④ krefs 既有红、本任务 0。

**Findings（文档级，不阻断，交 architect 收尾改）**：F1 `components/gem5/changelog.md` 写「046t 全 **27** 探针」，现场 `--list` = **32**；F2 `run.sh` 提示与完成区写「master 基线 **66** 悬空」，我实测主 worktree **72**（本树 155），结论「既有红 + 本任务 0」成立、仅数字过期。
