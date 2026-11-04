# GEM5-017t: FS 同模式 parity 矩阵（QEMU system ↔ gem5 FS：Tiny/Node × inst/arch/embench）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-015t`（gem5 FS Tiny，已验证）、`GEM5-016t`（gem5 FS Node，**当前 `待开始`，必须已验证并入 `master` 后本任务才可开工**）、`QEMU-079t`/`QEMU-080t`（QEMU system Tiny/Node，已验证）、`QEMU-082t`（cfx_power 按 profile，已验证）、`TESTCASES-092t`/`TESTCASES-093t`/`TESTCASES-094t`（Tiny/Node 执行资产、arch 10 例、13 个 L3 探针，已验证）、`SPEC-183t`（`spec/Machine-v5-测试机运行环境.md` 与 `tests/shared/machine-profiles.yaml` 真源，已验证）、`ADR-0048`（QEMU/gem5 同模式一致性，Accepted）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；从含 `GEM5-016t` 的 `master` 建独立 `git worktree` + 分支 `GEM5-017t`；**只改 `tests/**`、`tools/**` 与任务册**，不重建/不改组件；引擎用当前安装根 `qemu-system-dadao` 与 `运行期 gem5 构建树中的 **/gem5.opt`）。开工前必须确认 `GEM5-016t` 已 `已验证` 且已合入 `master`、两引擎二进制存在且可跑；否则本任务 **BLOCKED**，不得用 Tiny 机器/旧日志冒充 Node。

## 用户已定口径（2026-11-04，主会话转达）

- **同模式配对**：QEMU system ↔ gem5 FS；按 `tiny`/`node` **各自配对**；**同一 case ID** 比较「通过/失败 + 退出码 + 架构可见结果」；**不比较时序/性能/主机日志格式**（`ADR-0048 D1/D2`）。
- **覆盖 = FS 全矩阵**：`inst`/`arch`/`embench` × `Tiny`/`Node`；`arch` 仅 Node（Tiny `profile.arch=false`，矩阵记 `N/A` 并给依据，不得静默缺格）。
- **picolibc 仅作 Tiny 旁证**，不纳入硬 subset；`math_test` 的 B7 blocked **不计入 gem5 通过**，不得改写成 PASS。
- **`SYS_TICKFREQ` 基线 = `1e9` ticks/秒（用户裁定 2026-11-04）**：`spec/` 当前未定义具体数值；gem5 现返 `1e12 >> 8 = 3906250000` 不符基线，5 条以 `rd8` 判定的探针记 `BLOCKED` 并移交 `GEM5-018t`；**不得**据此改 `spec/`、不得按 QEMU 实测反推期望值。
- **硬门**：`QEMU 通过集合 ⊆ gem5 通过集合`（同 case 的 exit/架构可见结果一致）；`gem5 通过而 QEMU 不通过` ⇒ 逐条记录并**另立 QEMU 调试任务**，不阻断本任务；`QEMU 通过而 gem5 不通过` ⇒ 本任务不绿（定位到 gem5/测试资产/spec）。
- **spec/contracts 不清 ⇒ 保留现场、提交用户裁定**；不得按 RISC-V/ARM 经验或 QEMU/gem5 实测反推期望值。
- **改动范围（硬）**：只 `tests/**`、`tools/**`、本任务书、`.tao/knowledge/milestones.md`。**不改** `components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`、`docs/**`；**不复制 0628**（只读、仅吸收结论，标「内容溯源，非执行必需」）。
- **不纳入本任务**：cfxha 重编号（独立 spec/资产待办）、M11 收尾待办（里程碑关闭/归档/issue 清理）；二者另册。
- **不可成立 ⇒ BLOCKED**：附 spec 引用、根因、现场日志；不得自行跳过、降级期望、改测试资产或把 QEMU 红算作 gem5 绿。

## 现状与问题根源（2026-11-04 现场核对，只读）

1. **两引擎 FS 已齐，但没有统一的 parity 驱动与矩阵**：`GEM5-015t` 只自证 Tiny（inst 1003/1003、embench 38/38、picolibc 旁证），`GEM5-016t` 只规划 Node；`ADR-0048 D1–D5` 的要求散落在各任务证据里，**没有跨任务、可重跑、逐 case 的对账产物**。
2. **现有驱动只产出聚合文本**：`semantics_gate.py`/`run_qemu_test.py` 只返回 `total/passed/failed/deferred/errors/fail_details`；`run_m5_e2e.py`/`run_embench_e2e.py` 只逐行打印。无 per-case 机器可读记录 ⇒ 无法机械证明「QEMU 通过集合 ⊆ gem5」。
3. **case 身份不统一**：inst 的身份是「文件 + 序号 + `id`」（`id` 可重复，如 `tests/inst/base/misc.yaml` 的 `swym_oiii_imm` 出现两次）；arch 是 `expected.yaml` 的 name；L3 探针是「探针 id + 内部 check」；embench 是「benchmark + 优化级」；picolibc 是 test name。无冻结 ID 规则就会出现「同名不同例/同例不同名」。
4. **计数口径已漂移**：`GEM5-016t` 写 embench「22 × 2」，现场语料 `embench 组件源树中的 src` 为 **19** 个 → **38** 例；`TESTCASES-092t` 基线 Node inst `968 = 963 passed / 5 deferred / skipped_profile=44`。本任务一律**现场统计、不写死**。
5. **Node embench 有机器参数缺口**：`run_embench_e2e.py` 固定 `-M dadao-m1 -kernel <elf>`，不带 Node 的 `profile=node,bootrom-image=…`；直接跑会在 Tiny 机器上执行 Node ELF（假绿）。必须由证据层 wrapper/shim 补齐，且映射逐项入证据。
6. **picolibc `math_test` 是既有 B7 数值差异**：同 ELF 下 QEMU rc=0/0 error、gem5 rc=1/238 error（`GEM5-015t` 遗留①）。它会使「QEMU 通过 ⊆ gem5」在旁证里出现已知例外，必须显式登记为 blocked，不能算通过。
7. **门控环境缺口可预期**：`check-knowledge-refs` 可能因其它任务悬空 `运行期临时目录` 而红；L2 可能停在 `install-host → build-builtins`（`GEM5-015t` 现场）。只允许登记 BLOCKED + 现场，不得伪装 PASS。

## 目标

把 QEMU system 与 gem5 FS 的**同模式一致性**做成一个可重跑、可机械判定的矩阵，作为 M11「FS 覆盖 `inst`/`arch`/裸机 E2E」的验收依据：

1. 一个统一驱动：枚举 case、分别驱动两引擎、归一化结果、产出矩阵（JSON + Markdown）与硬门判定。
2. 覆盖 `inst` / `arch` / `embench` 的 **Tiny/Node 全矩阵**；Tiny arch 记 `N/A`。
3. `QEMU 通过集合 ⊆ gem5 通过集合`，逐 case 比较通过/失败、退出码、架构可见结果；差异逐条归因。
4. picolibc Tiny 旁证：除 `math_test` blocked 外分类一致、无新增 fail。
5. 零退化：SE、B0–B7、现有测试驱动的默认输出/退出码不变。
6. 落一份**入库矩阵快照**（`tests/parity/matrix-M11.md`）+ 可重生成全量矩阵（证据层）。

## 接口规范

### 0. 配对、比较对象与判定（`ADR-0048 D1/D2/D5`）

- **只允许**：gem5 FS ↔ QEMU system（同 profile）。**禁止** gem5 FS ↔ QEMU user、gem5 SE ↔ QEMU system。
- **比较**：同一 `case_id` 的 `status`（PASS/FAIL）、host 退出码、架构可见结果；**不比较**时序、性能、PC/日志格式、主机错误文本。
- **架构可见结果**按 scope 定义（均由资产内 spec 派生断言承载，parity 不另造期望值）：
  - `inst`：guest 按 `build_test_binary` 第 4 段比较 `expected_state`（RD/RB/RA、内存、`expected_pc`、fault）后的判定 + host exit；
  - `arch`（10 smoke）：guest exit + 控制台字节（`run_m5_e2e` 已做 byte-exact）；
  - `arch`（L3 探针）：每个 check 的 PASS/FAIL + exit + 探针内断言的 fault cause/寄存器；
  - `embench`：guest exit（`0` iff benchmark 自校验通过）；
  - `picolibc`：分类 `pass/excluded/blocked/fail`（同 ELF、同 argv）。
- **status 枚举**：`PASS` / `FAIL` / `DEFERRED` / `SKIP_PROFILE` / `BLOCKED` / `ERROR` / `TIMEOUT` / `N/A`。
- **verdict 枚举**：`AGREE_PASS`（双方 PASS 且 exit/架构可见一致）/ `AGREE_FAIL`（双方均非 PASS 且 exit/架构可见一致）/ `GEM5_ONLY_FAIL`（QEMU PASS、gem5 非 PASS）/ `QEMU_ONLY_FAIL`（gem5 PASS、QEMU 非 PASS）/ `DIFF`（其余 status/exit/架构可见不一致，含双方 PASS 但结果不同）/ `BLOCKED_SIDE` / `N/A`。
- **判据**：`QEMU PASS ⇒ gem5 PASS 且 exit/架构可见一致`（违反 = `GEM5_ONLY_FAIL`/`DIFF`，rc=1）；双方均 FAIL 的 `DIFF` 必须归因（资产/spec/gem5/QEMU），未归因 rc=1；覆盖完整。`QEMU_ONLY_FAIL` 不阻断，但必须逐条列出交接。

### 1. case ID（冻结，跨引擎/跨轮稳定）

- `inst/<relpath>#<ordinal>:<id>`：`ordinal` 为文件内 **1 基**列表序号（**不是** `tests/case-ledger.tsv` 的 identity 计数），`id` 取向量 `id`；重复 `id` 靠 ordinal 区分。`<relpath>` 相对 `tests/inst/`。
- `arch/umon/<expected.yaml name>`：`tests/arch/umon/expected.yaml` 的 name。
- `arch/probe/<probe-id>/<check-name>`：`probe-id` 取 `Makefile::ARCH_CFX_PROBES` 的 13 项 + `min_rom_probe_046t`；`check-name` 取探针 `--list`。
- `embench/<bench>-O<level>`：`level ∈ {0,2}`。
- `picolibc/<test>`：picolibc 测试名。
- 另带 `profile ∈ {tiny,node}`、`scope ∈ {inst,arch,embench,picolibc}`。**禁止**用标题/文本/路径顺序等易变内容作 ID。

### 2. 引擎适配（不改判据，只做参数映射）

- **QEMU system**：安装根 `qemu-system-dadao`；`inst`/`arch` 驱动已按 `DADAO_TEST_PROFILE` 生成 `-M dadao-m1[,profile=node,bootrom-image=…]` / `-bios …`，直接复用。
- **Node embench wrapper**：仅在该 scope 为 QEMU 注入 `-machine dadao-m1,profile=node,bootrom-image=<4 MiB>`（Tiny 保持 `-bios`），其余 argv 原样；映射逐项写入证据。**不得**改驱动默认、不得改变「guest exit == 0」判据。
- **gem5 shim**：新增 `tools/testcases/parity/qemu_gem5_shim.py`，只映射下列 QEMU 子集到 `gem5.opt --outdir <work> configs/dadao/fs.py`：
  `-M`/`-machine`（`tiny|node`、`bootrom-image=`）、`-bios`、`-kernel`、`-semihosting-config enable=on,target=native[,arg=…]`、`-chardev file,id=…,path=…`、`-nographic`、`-display none`、`-monitor none`、`-d cpu` + `-D <log>`（输出与 `run_m5_e2e.parse_cpu_log()` 兼容的块）。
  **未知参数/`-qmp`/`-S`/`-s` ⇒ rc=2**，不得静默丢弃；不得改变判据（只看 guest exit/控制台/逐 check）。
- **dump 通道**：arch 探针从 `-d cpu`/`-D` 读取 `RD[NN]`、`PTBR`、`PTW_ENABLE`、`CFXnn …` 等字段。shim 必须把这些字段从 gem5 trace 映射到同一 `-D` 文件；若当前 gem5 `--trace-cpu` 只给 `PC:`/`MODE:`，对应 check 记 **`BLOCKED`**（根因 + 需 gem5 任务），**不得**用 QEMU 结果替代、不得删 check。
- **`-icount shift=`**：QEMU 时序控制，gem5 atomic 无对应 ⇒ shim rc=2；依赖它的 check 记 `N/A`/`BLOCKED`（spec 语义 + 可行性 + 用户裁定），不得静默跳过。
- 引擎来源与身份：QEMU `md5`+`--version`；gem5 `md5`+组件源 `git rev-parse`+`configs/dadao/fs.py` md5；bootrom md5；工具链（clang/lld/mc/objcopy）md5。全部现场采集。
- **绕过 shim 的直跑**：`inst`/`arch-smoke`/`embench` 各至少 1 例直接 `gem5.opt --outdir … configs/dadao/fs.py --profile … --bootrom … --kernel …` 运行（probe 类可用其生成的 ROM 直跑），证明结论不只依赖映射层。

### 3. 矩阵 schema 与产物

- JSON（`--json`）：`{schema:1, generated_at, engines:{qemu,gem5}, toolchain, profiles, counts, cases:[{case_id,profile,scope,qemu:{status,exit,arch_visible},gem5:{…},verdict,note}]}`；行按 `(profile, scope, case_id)` 排序；`counts` 由行现算。
- Markdown（`--markdown`）：① 引擎/工具链身份；② 每 `profile × scope` 计数（total / agree_pass / agree_fail / gem5_only_fail / qemu_only_fail / diff / deferred / skip_profile / blocked / N/A）；③ **全部非 `AGREE_PASS` 行**（逐 case + 归因）；④ 证据指针。全量逐 case 行只在 JSON（证据层）。
- **确定性**：同一输入两次运行的 JSON/Markdown 除 `generated_at` 外逐字节一致（`--repro-check` 自检）。
- 工具默认**不写仓库**；`--markdown` 目标在仓库内时须显式 `--allow-repo-write`。入库快照由证据脚本 `cp` 生成，不手改数字。

### 4. 覆盖矩阵（全量，计数现场派生）

| profile | inst | arch | embench | picolibc |
| --- | --- | --- | --- | --- |
| tiny | 适用全集（`case_applies`，含 universal + explicit tiny） | `N/A`（`machine-profiles.yaml` `tiny.arch=false`） | 全 benchmark × O0/O2 | 旁证（见 §6） |
| node | 适用全集（含 universal + explicit node） | 10 smoke + 13 probes + `046t` | 全 benchmark × O0/O2（Node wrapper） | 不跑 |

- `inst`：`run + deferred + skipped_profile == 现场派生用例总数`（沿用 `semantics_gate` 结构断言）；`deferred` 保留登记、计入覆盖但**不算通过**；`skipped_profile` 同理；不得漏 case/重复 ID。
- `arch`：10 例取 `tests/arch/umon/expected.yaml`；13 探针从 `Makefile::ARCH_CFX_PROBES` 机械解析（缺项/空集 ⇒ 失败），加 `min_rom_probe_046t`；探针子 check 用 `--list` 现场枚举。Tiny 记 `N/A` 并给 profile 依据。
- `embench`：现场枚举 `embench 组件源树中的 src/*`，要求 `executed == discovered`；O0/O2 两档。
- `picolibc`：Tiny 单列旁证，不并入硬 subset。
- 所有计数**不写死**；完成区/REPORT 只贴现场数字。

### 5. 驱动接口（`tools/testcases/parity/run_parity.py`）

```sh
python3 tools/testcases/parity/run_parity.py \
  --profiles tiny,node --scopes inst,arch,embench,picolibc \
  --qemu <安装根二进制> \
  --gem5 <gem5 二进制> \
  --gem5-config configs/dadao/fs.py \
  --bootrom-tiny <tiny bootrom> --bootrom-node tests/shared/bootrom/step5/bootrom_step5.bin \
  --jobs 8 --timeout 600 \
  --work-dir <运行期临时目录> \
  --json <运行期临时目录> --markdown <运行期临时目录>
```

- 选项：`--profiles`/`--scopes`/`--only <case_id>`/`--list`/`--self-test`/`--inject`/`--matrix-only`（对既有 JSON 重判）/`--repro-check`。
- 退出码：`0` 全绿；`1` parity 红（subset 违反/gem5-only fail/未归因 DIFF/覆盖不全）；`2` setup 错或 **BLOCKED**（缺引擎/bootrom/工具、零 case、未知参数）。
- 复用而非重写：`inst` 调 `semantics_gate.py`（新增可选 `--json-out`）；`arch` 调 `run_m5_e2e.py`（新增可选 `--json-out`）+ 探针脚本（`--list`/`--only`）；`embench` 调 `run_embench_e2e.py`（新增可选 `--json-out`）。新增 flag 默认关闭、默认输出与退出码不变。

### 6. picolibc 旁证（仅 Tiny，不算硬门）

- 同一 ELF/argv：QEMU `--stage fast --work-dir <dir> --json <qemu.json>` 产出 ELF，再用 gem5 shim 重跑同一 ELF。
- 分类集合与 QEMU 基线逐项比较：只允许 `math_test` 为 `blocked`（B7 数值差异，`GEM5-015t` 遗留①）；不得出现新增 `fail`；`math_test` **不得**写 PASS、不得计入 gem5 通过数。
- 结果单列 `picolibc` scope，并在矩阵/REPORT 明确「旁证，不参与 `QEMU 通过集合 ⊆ gem5` 硬门」。

### 7. 差异处置与归属（`ADR-0048 D5`）

- `QEMU PASS / gem5 FAIL`：本任务红。归因到 `测试资产 / spec 不清（用户裁定）/ gem5 缺陷`；gem5 缺陷不在本任务改组件 ⇒ 登记 BLOCKED + 另立 gem5 任务。
- `gem5 PASS / QEMU FAIL`：非 gem5 缺陷；逐条列名（case_id + exit + 现场）交主会话另立 **QEMU 调试任务**，不阻断本任务，也不得算进 QEMU 通过集合。
- 双方均 FAIL：比较 exit/架构可见；不一致（`DIFF`）须归因；spec/test asset 不清 ⇒ 用户裁定。
- 不得用跨模式结果、时序或主机日志差异解释不一致。

### 8. 零退化与门控

- 工具侧：`semantics_gate.py`/`run_m5_e2e.py`/`run_embench_e2e.py` 不带新 flag 时，stdout/rc 与改动前一致；各自 `--inject` 仍通过；`run_qemu_test.py` 既有调用方不受影响。
- 实现侧（本任务不改）：`make check-gem5-decode` rc=0；`python3 tools/gem5/check_converge.py` B1–B7 计数不变（`[FAIL] 0`）；`configs/dadao/se.py` 的 `hello`/`fail` rc/stdout 与 `GEM5-014t` 基线一致。
- L1/L2：`make check` rc=0，或「本任务红=0 + 既有红逐条基线复现」；L2 `make check-modules` rc=0，若被共享 `install-host`/`gate.lock` 阻塞则记 BLOCKED + 现场（不得伪装 PASS）。

## 文件范围

**新增**：
- `tools/testcases/parity/run_parity.py`（矩阵驱动与硬门）
- `tools/testcases/parity/qemu_gem5_shim.py`（QEMU→gem5 参数映射，未知参数 rc=2）
- `tools/testcases/parity/README.md`（用法、case ID、退出码、已知限制）
- `tests/parity/README.md`（矩阵口径：**不是新用例/向量体系**，case 全部复用现有清单/驱动派生；`ADR-0048 D3`）
- `tests/parity/matrix-M11.md`（现场生成的入库快照：身份/计数/非 AGREE_PASS 行/证据指针）

**修改（均为可选 flag/钩子，默认行为不变）**：
- `tools/qemu/semantics_gate.py`（`--json-out` per-case 记录）
- `tools/testcases/lib/run_qemu_test.py`（per-case 采集钩子）
- `tools/testcases/arch/run_m5_e2e.py`（`--json-out`）
- `tools/testcases/tset/embench/run_embench_e2e.py`（`--json-out`）
- 本任务书、`.tao/knowledge/milestones.md`

**不改**：`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`Makefile`、`manifests/**`、`docs/**`、现有 `tests/inst|arch|tset|unit|shared` 用例与期望值。证据/临时物只落 `运行期证据（已清理，未归档）`、`运行期日志（已清理，未归档）`、`运行期临时目录`。

## 验收标准

1. **工具契约**：`--list` 逐 profile/scope 枚举 case（现场统计）；`--self-test` rc=0 且输出 `INJECT: PASS`；`--inject` 真实数据注入可达 FAIL；未知选项/零 case/缺引擎 ⇒ rc=2；shim 未知参数 ⇒ rc=2；`--matrix-only` 可对既有 JSON 重判；`--repro-check` 两次运行除 `generated_at` 外逐字节一致；工具未写仓库（无 `--allow-repo-write` 时）。
2. **覆盖完整**：每个 `profile × scope` 的计数现场派生；`inst` 满足 `run + deferred + skipped_profile == 现场派生总数`；无重复/缺失 case ID；`arch` = 10 smoke + 13 probe + `046t`（探针子 check 全覆盖，`N/A`/`BLOCKED` 须逐条给依据）；`embench` `executed == discovered`；Tiny arch 显式 `N/A` 且有 profile 依据。
3. **硬门**：`QEMU PASS ⊆ gem5 PASS` 且同 case 的 exit/架构可见结果一致；`GEM5_ONLY_FAIL == 0`；所有 `DIFF` 有归因（资产/spec/gem5/QEMU）；`QEMU_ONLY_FAIL` 逐条列名并标注「另立 QEMU 任务」；**未比较**时序/性能/日志格式。
4. **Tiny 矩阵**：`inst` 适用全集（计数对齐 `TESTCASES-092t` 口径但以现场为准）、`embench` 现场 benchmark × O0/O2 全量、picolibc 旁证；两引擎逐 case 对照，无 gem5-only fail。
5. **Node 矩阵**：`inst` 适用全集（`skipped_profile` 计数）、`arch` 10 + 13 + `046t`、`embench` Node wrapper 下全量 O0/O2；不得在 Tiny 机器上执行 Node case（wrapper/shim 参数入证据）。
6. **picolibc 旁证**：同 ELF/argv；QEMU 与 gem5 分类逐项一致，唯一允许 `math_test = blocked`；无新增 `fail`；`math_test` 未写 PASS、未计入 gem5 通过；报告明确「B7 blocked（`GEM5-015t` 遗留①）不参与硬门」。
7. **引擎身份**：QEMU md5/`--version`、gem5 md5/源码 commit/配置 md5、bootrom md5、工具链 md5 全部现场采集；无旧二进制/旧日志冒充；`inst`/`arch-smoke`/`embench` 各至少 1 例绕过 shim 直跑 gem5 并记录。
8. **零退化**：三个测试驱动不带新 flag 的默认 stdout/rc 与基线一致、各自 `--inject` 通过；`make check-gem5-decode` rc=0；`check_converge.py` B1–B7 计数不变（`[FAIL] 0`）；SE `hello`/`fail` 与 `GEM5-014t` 基线一致。
9. **L1/L2**：`make check` rc=0，或「本任务红=0」且既有红逐条基线复现；L2 `make check-modules` rc=0，或 BLOCKED（`install-host`/`build-builtins`/`gate.lock`）+ 现场日志。
10. **范围与门控**：`git diff --name-only <base>` 只命中 `tests/**`、`tools/**`、本任务书、`milestones.md`；`check-tests-index`/`check-dirs`/`check-no-residue`/`check-milestones-fresh` rc=0；`check-tasks` 无本任务新增漏收尾项（既有 `TESTCASES-090t` 待验收项复现即可）；无 `*_tmp*`/`*.orig`/`*.rej`/`__pycache__` 残留入库。
11. **证据/注入/快照**：`运行期证据（已清理，未归档）` 一键 `run.sh`（分 phase，逐项 `*_EXIT=<rc>`）+ `REPORT.md`；`run.sh --inject` 覆盖反例（`cp` 备份 + md5 对账还原，先红后绿）；`tests/parity/matrix-M11.md` 的计数/差异与证据 JSON 逐项一致、由脚本生成（不手改）。
12. **状态/BLOCKED**：完成区 ≤30 行，状态 `待验收`；任何无法成立的 case/能力按「spec 引用 + 根因 + 现场日志 + 为何不是实现缺陷」登记 BLOCKED 并经用户裁定；不得自行跳过、改期望、改测试资产或把 QEMU 红算作 gem5 绿。

## 必测反例（每类必须有可达 FAIL，不是上限）

1. **subset 违反**：把一条 `QEMU PASS / gem5 PASS` 改成 gem5 `FAIL` ⇒ 驱动 rc=1 并打印该 `case_id`；还原回绿。
2. **退出码不一致**：改一条 `AGREE_PASS` 的 gem5 exit ⇒ rc=1（`DIFF`/`GEM5_ONLY_FAIL` 命中）；还原回绿。
3. **架构可见结果不一致**：改一条 arch 的 console/verdict（双方均 PASS 但结果不同）⇒ rc=1；还原回绿。
4. **覆盖缺口**：删一行/重复一行/漏一个 vector 文件 ⇒ 覆盖断言 rc=1（不得静默少跑）；还原回绿。
5. **profile 泄漏**：Tiny 跑 Node case，或 Node embench 不加 wrapper（用 Tiny 机器）⇒ 对应用例 FAIL 且驱动记录机器参数；还原回绿。
6. **blocked 冒充 PASS**：把 picolibc `math_test` 的 gem5 blocked 改写成 PASS ⇒ 旁证门 rc=1；还原回绿。
7. **QEMU-only-fail 误判**：把 `QEMU_ONLY_FAIL` 标成 `AGREE_PASS` ⇒ rc=1；还原回绿。
8. **空跑**：scope 为空/`executed != discovered`/零 case ⇒ rc=2（fail-closed），不得绿灯。

## 证据

- `运行期证据（已清理，未归档）`：`run.sh`（phase：工具自检 → 引擎身份 → Tiny inst/embench → Node inst/arch（10+13+`046t`）/embench → picolibc 旁证 → 硬门判定 → 零退化 → L1/L2 → 注入），每 phase 落 `*_EXIT=<rc>`；矩阵 `matrix.json`/`matrix.md`；日志落 `运行期日志（已清理，未归档）` 与 `运行期临时目录`（gem5 `--outdir` 只落后者）。
- `REPORT.md`：所有数字由脚本现场生成（case 数、agree/only-fail/diff/deferred/skip/blocked、引擎 md5、注入表「注入前 md5 / 注入 rc / 还原后 md5 / 回绿 rc」）。
- `tests/parity/matrix-M11.md`：入库快照（现场生成后 `cp`），含身份、计数、全部非 `AGREE_PASS` 行、`N/A` 依据、证据指针；不手改。
- 工具链/依赖缺失（`qemu-system-dadao`、`gem5.opt`、bootrom、`scons`/工具链）⇒ **rc=2 BLOCKED**，不得伪造 PASS。

## 说明（风险 / 非目标 / 溯源 / 待确认）

### 1. 与 GEM5-015/016 的关系

- 本任务**不重复** 015/016 对组件实现的验收，只做**跨引擎、同 case** 的合并对账；015/016 公布的数字仅作输入线索，必须现场重跑。两者计数不一致处（如 embench 19 vs 22）以现场语料为准，并在报告注明差异来源。

### 2. 风险

- **R1 运行时长**：`inst` 约千例 × 2 profile × 2 引擎 ≈ 4k 次 guest 运行；`--jobs 8` 下预计 30–90 分钟，需申报耗时、落 PID/日志/`*_EXIT`，禁 `setsid nohup` 失联。
- **R2 Node embench wrapper 漂移**：wrapper 只补 `profile=node,bootrom-image`，必须逐项记录映射；若 QEMU Node 缺省行为变化，先核 `QEMU-080t` 口径，不按经验改。
- **R3 shim 参数/观测面覆盖**：参数子集外一律 rc=2；新增驱动参数时须显式扩展并有反例。探针依赖 `-d cpu` 的 `RD[NN]`/`PTBR`/`CFXnn` 与 `-icount`，若 gem5 侧 trace 不足或无 atomic 对应，逐 check 记 `N/A`/`BLOCKED`（附 gem5 任务），不得静默通过。
- **R4 工具改动回归**：共享驱动加 `--json-out` 必须默认关闭；L2/L3 的既有调用与 `--inject` 需重跑对照。
- **R5 2 GiB gem5 内存/长跑**：Node 证据阶段注意宿主内存与超时；`--timeout` 的 `124` 判 FAIL，不判 BLOCKED。
- **R6 L1/L2 环境缺口**：`check-knowledge-refs`/`install-host`/`build-builtins` 的既有红按基线登记，不冒充。

### 3. 非目标

- cfxha 重编号；M11 关闭/归档/issue 清理；新增测试向量/期望值；时序/性能/缓存/多核；QEMU/gem5 实现修复；spec/contracts 修订；动态链接/TLS/线程；Linux 启动。

### 4. 参考对照（内容溯源，非执行必需）

- `ADR-0048`（D1–D5）；`GEM5-015t`/`GEM5-016t` 的证据形态；`QEMU-079t`/`QEMU-080t` 的同模式机器；`TESTCASES-092t/093t/094t` 的资产口径；`SPEC-183t` 的 profile 表。
- `DADAO-0628` 的 QEMU/gem5 经验只作**内容溯源，非执行依赖**；不复用其代码/常量/测试。

### 5. 待确认口径（本册已按推荐值写，用户可否决）

- ① `inst` 每 profile 跑「适用全集」（不加 `--only-profile-cases`），`skipped_profile` 计入覆盖但不计通过。
- ② `arch` 仅 Node；Tiny 记 `N/A`（依据 `machine-profiles.yaml`）。
- ③ Node embench 用证据层 wrapper 注入机器参数（不改驱动默认）。
- ④ picolibc 不纳入硬 subset，仅 Tiny 旁证；`math_test` 保持 blocked。
- ⑤ `QEMU_ONLY_FAIL` 不阻断本任务，但必须逐条列名并交主会话另立 QEMU 调试任务。

## 完成区

**测试结果**：全量矩阵（`运行期临时目录`，现场生成）**2658 行**：`AGREE_PASS=2301`、`GEM5_ONLY_FAIL=0`、`QEMU_ONLY_FAIL=0`、`DIFF=0`、`AGREE_FAIL=0`、`BLOCKED_SIDE=28`、`N/A=271`（另有 deferred 10 / skip_profile 48）。逐 scope：tiny inst **1003/1012**（5 deferred / 4 skip）、node inst **963/1012**（5 deferred / 44 skip）、tiny/node embench **38/38 ×2**（19 bench×O0/O2 现场派生）、node arch **242/269 pass + 27 blocked**（20 个 QEMU `-icount` 无 atomic 对应 + 5 条 `SYS_TICKFREQ` 与用户裁定 1e9 基线不符 + 2 条 WRITEC/WRITE0 清 rd8，后 7 条入 gem5 修复任务）、tiny arch **269 N/A**（`tiny.arch=false`）、picolibc 旁证 **17 pass / 1 blocked(`math_test` B7) / 2 excluded**；`QEMU PASS ⊆ gem5 PASS`（除上述 27 条显式 BLOCKED；`svc_readc` 经 input-path→stdin 修复后 PASS）。
**修改文件**：`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py,README.md}`、`tests/parity/{README.md,matrix-M11.md}`；可选钩子：`tools/qemu/semantics_gate.py`、`tools/testcases/lib/run_qemu_test.py`、`tools/testcases/arch/run_m5_e2e.py`、`tools/testcases/tset/embench/run_embench_e2e.py`；本任务书、`.tao/knowledge/milestones.md`。证据/日志在 `运行期证据（已清理，未归档）`、`运行期日志（已清理，未归档）`、`运行期临时目录`（不入 git）。
**验收结果**：`运行期证据脚本（已清理，未归档）` 分 phase：self-test `INJECT: PASS`（10 类反例）、`--list` 逐 scope 现场计数、matrix `rc=0`、matrix-only `rc=0`、direct **inst+arch+embench 各 1 例真实直跑**（arch 用 console-bearing `m5_semi_write0`，`run/direct/m5_semi_write0.console`=`OK\n`、`.cpu.log` 13.3 MB；三项 `exit == matrix`）、repro 两次 Markdown 逐字节同、真实矩阵 `--inject` 全类判出 + 文件注入 `rc=1`→`cp`+md5 还原→回绿 `rc=0`、零退化（三驱动默认路径/`--inject`、decode 264/264+388/388+28/28+2/2、converge `[FAIL] 0`、SE hello `hi\n` rc0 / ret7 rc7）、gates（tests-index/dirs/no-residue/milestones/tasks/range 全 0）。L1 `make -k check` rc=2 唯一红 `check-knowledge-refs`（现场 159 条悬空全属其它任务、本任务 0）；L2 `make check-modules` **BLOCKED**（420s 超时于 `install-host→build-builtins` 的 LLVM 重建，已删半成品 build，未伪 PASS）。
**新发现/坑**：① gem5 semihosting 与用户裁定 1e9 基线/QEMU 不一致共 7 条：5 条 `SYS_TICKFREQ` 返回 `1e12/256`、2 条 `WRITEC/WRITE0` 清 `rd8`（逐条 `KNOWN_GEM5_BLOCKED` + 保留 `raw_status`，另立 gem5 修复任务；`spec/` 不改）；② `-dfilter` 必须按窗口过滤 gem5 trace，直接忽略会改变探针「最后一个 block」观测（曾假绿）；③ `input-path` 必须接到 gem5 stdin，否则 READC 假失败（接上后 `svc_readc` PASS）；④ `build_test_binary` profile 在 import 期固定，parity 直跑须 `set_profile()`；⑤ direct-check 必须显式选 `arch/umon/` console-bearing case，按排序首条 arch 会落到 probe 而被静默跳过（reviewer F1 已修）；⑥ Node inst 用 `bootrom_step5_inst.bin`、arch/embench 用 `bootrom_step5.bin`；⑦ 隔离 worktree 的 picolibc meson 树需软链主仓 `运行期 picolibc 测试构建树`（env，非代码）。
**遗留问题**：① 7 条 gem5 semihosting 缺陷（5×`SYS_TICKFREQ` 按 1e9 + 2×`WRITEC/WRITE0` rd8）需另立 gem5 修复任务；本任务不改 `components/gem5`，记 BLOCKED 且保留 `raw_status`，逐条现场与验收建议见 `运行期证据（已清理，未归档）`；② L2 BLOCKED = 隔离 worktree 无 `运行期 LLVM 构建树`、install-host 触发全量 LLVM 重建（env，非本任务红）；③ L1 `check-knowledge-refs` 159 条悬空均为其它任务/隔离 worktree 基线，本任务 0 条；④ `GEM5-016t` 文本「embench 22×2」与现场 19×2=38 不一致，本任务以现场派生 38 为准；⑤ `_check_picolibc` 未断言 blocked 集合 = `{math_test}`（reviewer 第 2 轮 finding ①）：非 `math_test` 行伪造 `BLOCKED` 仍 rc=0；仅登记、不改已 Accepted 实现语义，建议后续维护任务补断言。
**收尾结论**：engineer 第 2 轮（reviewer Needs Revision）F1/F2/F4 已修：arch direct 真实直跑并留 console/trace 证据、READC 接 input-path 后 PASS、5 条 TICKFREQ 按用户裁定 1e9 归 gem5 修复任务；F3（2 条 WRITEC/WRITE0）仍按 §7 记 BLOCKED。重跑 selftest/rejudge/inject/zero/gates/report 全绿（L2 BLOCKED、L1 基线红）；全矩阵 **2301 AGREE_PASS / 0 gem5-only / 0 DIFF / 0 QEMU-only / 28 BLOCKED**，状态 `待验收`。
**收尾（architect，2026-11-04 13:05）**：reviewer 第 2 轮 **Accepted**（第 1/2 轮原文保留），状态置 `已验证`；文档 findings 1–5 已处置——picolibc blocked 断言缺口登记「遗留⑤」（不改已 Accepted 实现）、handoff 落点订正为 `components/gem5/patches/src/arch/dadao/semihosting.cc.patch`、L1 悬空订正 159、补「第 2 轮 engineer 自审」小节、`SYS_TICKFREQ=1e9` 用户裁定入「用户已定口径」；7 条 semihosting 仍 `BLOCKED`（未写 PASS），移交 `GEM5-018t`。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`run_parity.py`（case 枚举/引擎适配/verdict/覆盖/注入/输出）、`qemu_gem5_shim.py`（argv 映射/trace 过滤/退出码）、三个驱动的 `--json-out` 钩子、`run.sh`/`report.py` 证据链。**方法**：逐文件通读 + 真跑全矩阵/逐 scope 小样 + `--self-test` + 真实矩阵注入；每条 finding 均以重跑输出复核。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `_apply_known_blocked` 成功时返回 reason，judge 误判 stale | ✅已修 | 成功返回 None，stale 仅由「gem5 已 PASS」触发 | arch matrix-only rc=0（241 pass/28 blocked） |
| F2 embench case_id 拼成 `-OO0`，两引擎行全部 join 失配 | ✅已修 | `embench/%s-%s` | tiny/node embench 各 38/38 AGREE_PASS |
| F3 Tiny ELF 被注入 `--bootrom`，fs.py fatal→125 | ✅已修 | `PARITY_GEM5_BOOTROM` 仅 node 设置 | 重跑 tiny/node embench rc=0 |
| F4 `-dfilter` 直接忽略会改变探针最后 block（假绿） | ✅已修 | shim 解析窗口并事后过滤 gem5 trace；不再当 hint | integ046t chain/vectors/ptw/pte 逐项 PASS；7 条真缺陷/基线不符仍 BLOCKED |
| F5 直跑 gem5 复用 import 期 tiny profile，Node case 得 UNDI 137 | ✅已修 | 直跑前 `build_test_binary.set_profile()` | inst 直跑 exit==matrix；arch 直跑当时仍被 F10 静默跳过（见 F10） |
| F10（reviewer F1）`_row_sort` 后在 `direct_check` 取首条 arch 行，恒为 probe 检查而被 `arch/umon/` 条件跳过，arch 从未直跑 | ✅已修 | arch 改选 **console-bearing 的 `arch/umon/` smoke**（`m5_semi_write0`），缺候选/缺 console/trace 证据即报错 | 重跑 direct：inst/arch/embench 三项均 `exit == matrix`；`run/direct/m5_semi_write0.console`=`OK\n`、`.cpu.log` 13.3 MB |
| F11（reviewer F2）shim 用 `stdin=DEVNULL` 丢弃 `input-path`，`svc_readc` 假失败 | ✅已修 | `input-path` 文件接到 gem5 stdin（无输入才 DEVNULL） | `svc_readc` PASS；node/arch blocked 28→27 |
| F12（reviewer F4 + 用户裁定 2026-11-04）`SYS_TICKFREQ` 不写 spec 不清 | ✅已修 | 统一按 1e9 ticks/s 基线；5 条从 spec-pending 移入 `KNOWN_GEM5_BLOCKED`（gem5 修复任务），`spec/` 不改 | arch-only 重跑 node/arch 242 pass / 27 blocked |
| F13（reviewer 建议）icount / tiny-arch 的 N/A 行伪造双 PASS 未被判出 | ✅已修 | 覆盖断言强制 icount 行 gem5=N/A、tiny/arch 双方=N/A | 两条伪造矩阵重判均 rc=1（`must stay N/A`） |
| F6 picolibc QEMU exit=None 致假 DIFF；math_test 超时未归 blocked | ✅已修 | pass→exit0；已知 B7 非零/超时一律 BLOCKED | picolibc 17 pass/1 blocked/2 excluded，rc=0 |
| F7 shim 文档承诺的 input-path 处理缺失、一次编辑造成语法悬空 | ✅已修 | 恢复 console 警告块；input-path 改为接 stdin 并打 NOTE | `py_compile` + `--self-test` + `svc_readc` PASS |
| F8 `run.sh` range 用移动的 `master`，把别处 `discussing.md` 算进来 | ✅已修 | 改用分支基点 `HEAD` + untracked | gates range rc=0 |
| F9 inst 的 deferred/skip 同时计入 N/A，计数重复 | ✅已修 | counts 只在非 deferred/skip 时计 n_a | 快照 node/tiny inst N/A=0，deferred/skip 分列 |

**判决**：无未修 finding；`--self-test` 10 类反例全判出；全量矩阵与证据链可重跑。状态 `待验收`。


#### 第 1 轮 reviewer 验收

**方法**：审 `run.sh`/`run_parity.py`/`qemu_gem5_shim.py`/4 个驱动钩子/`report.py` → 各 phase 独立重跑 → 矩阵独立重算 → 独立注入 → 归因核证（spec/contracts、gem5 与 QEMU 源码、探针实跑）。明细 `运行期日志（已清理，未归档）`。

**重跑 rc（全部我自己的输出）**：`--phase selftest` **0**（`INJECT: PASS` 10 类；`--list` 现场 node 269/38/1012/0、tiny 269/38/1012/20）；`--phase rejudge` **0**（matrix_only 0 / direct 0 / repro 0 / repro_md 0，两次 Markdown 逐字节同）；`--inject` **0**（10 类全判出、文件注入 rc=1、`cp`+md5 `91d91de0…` 还原、回绿 rc=0）；`--phase zero` **0**（decode 264/264+388/388+28/28+2/2、converge `[FAIL] 0`、SE `hi` rc0 / ret7 rc7、三驱动 `--inject` 0、inst tiny 子门 0）；`--phase gates` **0**（tests-index/dirs/no-residue/milestones/tasks 全 0，range 11 文件全在范围）；`--phase l1` **0**（内层 `make -k check` **rc=2**，唯一红 `check-knowledge-refs`，悬空 159 条、本任务 0 条）；`--phase l2` **0**（内层 **rc=124**@420s，卡 `install-host`→ninja LLVM `[556/3573]`，BLOCKED 属实）。契约 rc=2 全复现：未知选项/缺引擎/零 case/`node+picolibc`/shim 未知参数与 `-icount`/`-qmp`/写仓库无 `--allow-repo-write`。

**独立重算**：2658 行 = AGREE_PASS **2300** / BLOCKED_SIDE **29** / N/A **329**（deferred 10、skip 48、n_a 271）；QEMU-only **0**；双方 PASS 而 exit/架构可见不一致 **0**；`raw_status` 改判恰 **8** 行；node arch 269 = 10 smoke + 13 探针 227 + `046t` 32，icount N/A 恰 20；快照 358 条非 AGREE_PASS 与 JSON 集合相同、md5 `4f5b2a4e…`；QEMU/gem5/fs.py/BootROM/工具链 md5 与源码 commit `f86efab6` 现场全对，`components/{qemu,gem5}` 源树 clean。

**独立重生成（新 work-dir、非缓存）**：node/arch、tiny/inst、node/inst、tiny/picolibc、tiny/arch+embench、node/embench 六段 **2658/2658 行全部重跑**，rc=0，`(profile,case_id,qemu.status,exit,gem5.status,exit,verdict)` 与入库矩阵**逐行相同、缺失 0 行**。

**独立注入（异于 engineer 10 类）**：DEFERRED 行伪造 PASS ⇒ `matrix-only` **rc=1**（`expected DEFERRED, got PASS`）⇒ `cp`+md5 还原 ⇒ **rc=0**。另探测两类缺口（**不阻断，建议补**）：icount N/A 行、`tiny/arch` N/A 行伪造双 PASS ⇒ 均 **rc=0**（无 FAIL 路径）；picolibc 非 `math_test` 的机器故障也会归 BLOCKED 且不报错。

**阻断 1（验收 7 + 输出真实性）**：`_row_sort`（`run_parity.py:1538`/`:1694`）先于 `direct_check`，排序后首条 arch 行恒为 `arch/probe/044t/cfx_rw_share`，而代码只处理 `arch/umon/` ⇒ **arch 直跑在任何路径都不会执行**（静默跳过、无报错）。我重跑的 `direct.log` 只有 inst、embench 两行；`run/direct/` 无 `.console`/`.cpu.log`；我新起的**全量** node/arch 跑（非 matrix-only）同样无 arch 行。完成区「direct（inst+arch+embench…）rc=0」与自审 F5「inst/arch/embench 全 exit == matrix」**与真实输出不符**。（`inst` 直跑已核：picked 行是 node 档，命令行 `--profile node --bootrom …_inst.bin`，`GEM5_EXIT_CODE=0` == matrix ⇒ **137 已修**。）

**阻断 2（8 条 semihosting 归因）**：① 5 条 TICKFREQ 写「!= spec 1e9」，但 `spec/Machine-v5 §5.3` 与 `contract-semihosting` 只写「返回 ticks/秒」，全仓 `spec/`、`contracts/`、`.tao/adr/` 无 `1e9`/`0x3b9aca00`/`1 GHz`（QEMU 的 1e9 源自其 `qemu always uses nsec`）⇒ 应按任务书「spec 不清 → 用户裁定」，**不得**登记为 gem5 缺陷另立任务；② 1 条 `svc_readc`「gem5 FS 无控制台输入通道」**不成立**——gem5 `callReadC` 读 `std::cin`（有通道），根因是本任务 shim `stdin=DEVNULL` 且丢弃 `input-path`；我用 `运行期临时目录` 副本仅把 `input-path` 接到 stdin，同一探针 **rc 1→0 PASS**（仓库 shim md5 未变 `48454153…`），属本任务 `tools/` 可修；③ 2 条 `svc_writec`/`svc_write0` 清 `rd8` 归因**成立**（gem5 `retOK(0)` 写 rd8、spec 表「无返回」、QEMU 保留 rd8）。

**判决：Needs Revision**。**「8 条是否应阻断」：是，归因修正前应阻断**——2 条按 §7 登记 BLOCKED + 另立 gem5 任务；5 条转「spec 不清 → 用户裁定」；1 条在本任务内修 shim（修后硬门例外 28 → 27）。另需补 arch 直跑证据并订正完成区/F5 陈述。

**其余约束核验通过**：范围零越界（`git diff` 无 components/spec/contracts/adr/Makefile/manifests/docs，无既有测试资产改动）；SE / B0–B7 / Tiny 零退化全绿；快照由脚本 `cp`（md5 与现场 `matrix.md` 相同）；完成区 6 行、状态 `待验收`；L1/L2 红归因属实（L1 悬空 159 条全属其它任务，L2 真卡 LLVM 重建）。**副作用已还原**：L2 重跑生成的 `运行期 LLVM 构建树`（1.7G，开工时不存在）已删；bootrom 重建 md5 不变；`git status` 与开工快照逐行相同；主仓 `git status` clean；无残留进程。

#### 第 2 轮 engineer 自审

**范围**：reviewer 第 1 轮阻断项（arch 直跑、READC/TICKFREQ 归因）与本轮改动 diff（`run_parity.py` 的 `direct_check`/`KNOWN_GEM5_BLOCKED`、`qemu_gem5_shim.py` 的 `input-path`、`run.sh` phase）。**方法**：先删 `run/direct/` 产物再重跑 `--phase rejudge`；走仓库 shim 逐条重跑三探针；重跑 `--inject`/`--phase zero`/`--phase gates`/`--phase report`。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F10（reviewer 阻断 1）arch 直跑被 `_row_sort` 静默跳过 | ✅已修 | `direct_check` 改选 console-bearing 的 `arch/umon/` 行；缺候选/缺 console/trace 即报错 | 删产物后重跑：`arch m5_semi_write0: exit 65 == matrix`，`console`=`OK\n`、`cpu.log` 13.3 MB |
| F11（reviewer 阻断 2②）shim 丢弃 `input-path` 致 READC 假失败 | ✅已修 | `input-path` 接 gem5 stdin，无输入才 `DEVNULL` | `--only svc_readc` rc=0 `[PASS]`；node/arch blocked 28→27，全矩阵 BLOCKED_SIDE 29→28 |
| F12（reviewer 阻断 2①）TICKFREQ 按 spec 1e9 归因越权 | ✅已修 | 改记「user-ruled 1e9 ticks/s」；5 条移入 `KNOWN_GEM5_BLOCKED` 移交 `GEM5-018t`，`spec/` 不改 | arch-only 重跑 242 pass / 27 blocked；`svc_tickfreq` 仍 rc=1、无 PASS 冒充 |
| F13（reviewer 建议）icount / tiny-arch 的 N/A 行伪造双 PASS 未判出 | ✅已修 | 覆盖断言强制 icount 行、tiny/arch 行双方 `N/A` | 两类伪造矩阵 `matrix-only` 均 rc=1（`must stay N/A`/`must be N/A`） |

**判决**：无未修 finding；全量矩阵 **2301 AGREE_PASS / 0 gem5-only / 0 DIFF / 28 BLOCKED**；`--self-test` 10 类、文件注入 `rc=1`→`cp`+md5 还原→回绿 `rc=0`。状态 `待验收`。

#### 第 2 轮 reviewer 验收（针对第 1 轮 Needs Revision 的增量复验）

**方法**：审返工 diff → 逐 phase 独立重跑 → 关键证据**先删后跑** → 独立注入 → 与我第 1 轮的 2658 行独立重生成结果**逐行比对**。明细 `运行期日志（已清理，未归档）`。

**重跑 rc（我自己的输出）**：`--phase selftest` **0**（`INJECT: PASS` 10 类；`--list` 现场 269/38/1012/0 + 269/38/1012/20）；`--phase rejudge` **0**（matrix_only 0 / **direct 0** / repro 0 / repro_md 0，两次 Markdown 逐字节同）；`--inject` **0**（10 类判出、文件注入 rc=1、`cp`+md5 `8e24c42f…` 还原、回绿 0）；`--phase zero` **0**（decode 264/264+388/388+28/28+2/2、converge `[FAIL] 0`、SE `hi` rc0 / ret7 rc7、三驱动 `--inject` 0、inst tiny 子门 0）；`--phase gates` **0**（tests-index/dirs/no-residue/milestones/tasks 全 0，range 11 文件全在范围）；`--phase report` **0**；契约 rc=2 全复现（未知选项/缺引擎/`node+picolibc`/shim 未知参数与 `-icount`/`-qmp`/写仓库无 `--allow-repo-write`）。

**F10 arch 直跑（先删后跑）**：我先删掉 `run/direct/m5_semi_write0.{console,cpu.log,log}` 再重跑 `--phase rejudge` ⇒ `direct.log` 三行 `inst … exit 0 == matrix`、`arch m5_semi_write0: exit 65 == matrix (console=…, trace=…)`、`embench … exit 0 == matrix`，`direct-check: PASS`；产物 13:01 重建：`console`=`OK\n`(3B)、`cpu.log` 13288062B、`m5_semi_write0.log` 内 `GEM5_EXIT_CODE=65`/`[PARITY_EXIT] rc=65` == 矩阵 `arch/umon/m5_semi_write0` exit 65。选行=排序后首个带 `console_expected` 的 `arch/umon/`（`m5_semi_write0`，`4f4b0a`）；缺候选/缺 console/trace 均报错（fail-closed）。

**F11 READC**：仓库 shim（md5 `cf808f0e…`）直跑 `--only svc_readc` ⇒ **rc=0** `[PASS] … -> ok`；矩阵该行 QEMU PASS/0 + gem5 PASS/0 = **AGREE_PASS**；`KNOWN_GEM5_BLOCKED` 8→**7** 条，node/arch blocked **28→27**，全矩阵 BLOCKED_SIDE **29→28**。

**F12 归因**：7 条仍 BLOCKED、`raw_status=FAIL`、**无一写 PASS**；我现场重跑三探针（走仓库 shim）：`svc_tickfreq` rc=1 `exp=0x3b9aca00 got=0xe8d4a510`、`svc_writec` rc=1 `exp=0xdeadbeef got=0x0`、`svc_write0` rc=1 同上 ⇒ BLOCKED 是真红。登记理由已由「spec 1e9」改为「user-ruled 1e9 ticks/s」；`gem5-fix-handoff.md`（51 行）列全 7 条 + 现场 + 验收建议；`spec/` 未改。

**F13 我第 1 轮两类缺口**：icount N/A 伪造双 PASS ⇒ **rc=1** `-icount check must stay N/A on gem5, got PASS`；`tiny/arch` 伪造双 PASS ⇒ **rc=1** `tiny/arch must be N/A`。

**矩阵与快照**：2658 行 = AGREE_PASS **2301** / BLOCKED_SIDE **28** / N/A **329**；GEM5_ONLY **0**、QEMU_ONLY **0**、DIFF **0**；QEMU PASS 而 gem5 非 PASS **28** = 20 icount + 7 registry + 1 picolibc 旁证；`matrix.md` 与 `tests/parity/matrix-M11.md` **md5 相同** `e9ca31b1…`；非 AGREE_PASS **357** 行集合与 JSON 一致；引擎/BootROM/工具链 md5 与 commit `f86efab6` 现场全对；完成区逐项计数（1003/963/38×2/242+27/269 N/A/17+1+2、deferred 10、skip 48、n_a 271）全部与现场一致。
**与我第 1 轮 2658 行独立重生成逐行比对**：键集相同；**仅 1 行状态变化**（`svc_readc` BLOCKED→AGREE_PASS）+ **5 行 attribution 文本变化**（TICKFREQ 措辞），其余 **2652 行与我自己跑出的结果完全一致**；且本轮矩阵是 11:42→12:46 的全新全量跑（各 scope JSON 时间戳连续）。

**独立注入（异于 engineer 全部 12 类）**：把 registry 内 `svc_tickfreq` 伪造为 gem5 PASS ⇒ `matrix-only` **rc=1** `KNOWN_GEM5_BLOCKED is stale (gem5 now PASS)` ⇒ `cp` 备份还原 md5 `8e24c42f…` ⇒ **rc=0**（顺带复测第 1 轮两类缺口，均 rc=1）。

**L1/L2**：`--phase l1` **0**（内层 `make -k check` **rc=2**，唯一红 `check-knowledge-refs`，悬空 **159** 条、含本任务/`parity` **0** 条）；`--phase l2` **0**（内层 **rc=124**@420s，`install-host` → ninja LLVM `[555/3573]` 被 timeout 终止，BLOCKED 属实）。

**遗留（非阻断，记 finding、由 architect 收尾订正）**：① picolibc 非 `math_test` 行伪造 `BLOCKED` 仍 **rc=0**（`_check_picolibc` 未断言 blocked 集合 = {math_test}；第 1 轮已判非阻断）；② `gem5-fix-handoff.md` 落点路径 `components/gem5/src/arch/dadao/semihosting.cc` **不存在**（实际 `components/gem5/patches/src/arch/dadao/semihosting.cc.patch`，计算在 `gem5 组件源树中的 src/arch/generic/semihosting.cc`）；③ 完成区 L1 悬空「170/160」与现场 **159** 不符（非验收判据）；④ 第 2 轮返工记录并入「第 1 轮 engineer 自审」表（F10–F13），缺「第 2 轮 engineer 自审」小节；⑤ 1e9 用户裁定未落盘到任务书「用户已定口径」节（现仅见 handoff / 完成区 / F12 行）。

**判决：Accepted**。第 1 轮两条阻断项（arch 直跑、READC/TICKFREQ 归因）均已按要求修复并经我独立复验，回归无新增红；上述 5 项为文档级/建议项，按「文档级小错不阻断」记 finding、由 architect 收尾处理，不再开轮。状态仍为 `待验收`，待主会话 `/complete`。**副作用已还原**：L2 重跑生成的 `运行期 LLVM 构建树`（1.7G）已删；`matrix.json`/快照/shim/run_parity md5 与开工相同；`git status` 文件清单与开工快照逐行相同；主仓 clean；无残留进程。
