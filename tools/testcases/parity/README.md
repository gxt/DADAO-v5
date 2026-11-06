# 跨引擎同模式 parity 驱动（`tools/testcases/parity/`）

把 **QEMU system** 与 **gem5 FS** 的同 profile、同 case 结果做成可重跑、可机械判定的矩阵。
配对**只允许** QEMU system ↔ gem5 FS（同 `tiny`/`node`），见 `ADR-0048 D1/D2`。

本目录**不是**新的测试向量体系：case 全部来自现有清单/驱动（`tests/inst/*.yaml`、
`tests/arch/umon/expected.yaml`、`Makefile::ARCH_CFX_PROBES` + `min_rom_probe_046t`、
`.work/source/embench-iot/src/*`、picolibc Meson 清单）。parity 只做**跨引擎对账**，
不新增期望值、不按 QEMU 实测反推期望。

## 文件

- `run_parity.py`：枚举 case、分别驱动两引擎、归一化、硬门判定、输出 JSON/Markdown。
- `qemu_gem5_shim.py`：把现有驱动发出的 QEMU 系统 argv 子集映射到
  `gem5.opt --outdir … configs/dadao/fs.py`。

## 用法

```sh
python3 tools/testcases/parity/run_parity.py \
  --profiles tiny,node --scopes inst,arch,embench,picolibc \
  --qemu .dadao/cross-toolchain/bin/qemu-system-dadao \
  --gem5 .work/source/gem5/build/DADAO/gem5.opt \
  --gem5-config .work/source/gem5/configs/dadao/fs.py \
  --bootrom-tiny tools/testcases/lib/trampoline.bin \
  --bootrom-node .dadao/tests/bootrom/step5/bootrom_step5.bin \
  --bootrom-node-inst .dadao/tests/bootrom/step5/bootrom_step5_inst.bin \
  --jobs 8 --timeout 600 \
  --work-dir /tmp/opencode/qemu-gem5-parity/run \
  --json /tmp/opencode/qemu-gem5-parity/matrix.json \
  --markdown /tmp/opencode/qemu-gem5-parity/matrix.md
```

选项：

- `--list`：逐 `profile × scope` 现场枚举 case（计数不写死）。
- `--only <case_id>`：只保留一个 case；驱动仍可能跑完其所在 scope（过滤发生在结果层）。
- `--self-test`：合成矩阵 + 全类反例，必须输出 `INJECT: PASS`。
- `--matrix-only <json>`：对既有 JSON 重判（覆盖/机器参数/硬门），可配 `--inject`。
- `--inject`：对**真实矩阵行**逐类注入反例，要求每条都被判出；`--matrix-only` 时使用。
- `--repro-check`：重判 + 重序列化，除 `generated_at` 外必须逐字节一致。
- `--direct-check`：每个 scope 取一个 case 绕过 shim 直跑 `gem5.opt`，与矩阵中的 gem5 退出码比对。
- `--allow-repo-write`：允许把 `--json`/`--markdown` 写进仓库（默认拒绝；入库快照由证据脚本 `cp`）。

退出码：`0` 无红；`1` parity 红（`GEM5_ONLY_FAIL`/未归因 `DIFF`/覆盖缺口/注入未判出）；
`2` setup 错或空矩阵（缺引擎/BootROM/工具、零 case、未知选项）。

## case ID（冻结）

- `inst/<relpath>#<ordinal>:<id>`：`ordinal` 为 YAML 文件内 1 基序号（同一 `id` 可重复）。
- `arch/umon/<expected.yaml name>`；`arch/probe/<probe-id>/<check>`（13 个
  `ARCH_CFX_PROBES` + `min_rom_probe_046t`，子 check 由 `--list` 现场枚举）。
- `embench/<bench>-O{0,2}`。
- `picolibc/<test>`。

另带 `profile ∈ {tiny,node}`、`scope ∈ {inst,arch,embench,picolibc}`。

## 判定

每个 case 比较 **status + host 退出码 + 架构可见结果**（`inst` 的
`expected_fault`/guest 判定、`arch` 的 console/bootrom/probe check、`embench` 的
guest exit、`picolibc` 的分类）；**不比较**时序、性能、PC/日志格式。

- 硬门：`QEMU PASS ⇒ gem5 PASS` 且 exit/可见一致；违反记 `GEM5_ONLY_FAIL`（红）。
- `QEMU_ONLY_FAIL`（gem5 PASS、QEMU 非 PASS）不阻断，逐条列名并交主会话另立
  **QEMU 调试任务**。
- 双方均非 PASS 且 exit/可见一致 ⇒ `AGREE_FAIL`；不一致 ⇒ `DIFF`，必须归因
  （资产/spec/gem5/QEMU），未归因 rc=1。
- `BLOCKED`/`N/A` 逐条带根因；不得静默通过、不得改写成 PASS。

## M11 收口口径（TESTCASES-098t）

- **矩阵范围**：Tiny/Node 的 `inst`/`arch` + Tiny `picolibc`（`math_test` B7 对照）。Embench 不进本矩阵。
- **M11 Node 验收范围**：只验收 `arch`（cfx/arch/PTW/模式）。`node/inst` 行仅作现场参考，不进入 Node 验收通过数。
- **历史归类**：`GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` 结果 = **历史，不计入 M11 Node 验收**；`node/embench` 不再生成。
- **Node 不跑 Embench**：M11 起 Node profile 不跑 Embench。
- **Embench 归属**：Tiny system/bare-metal = `run_embench_e2e.py`（`make test-m6`，guest exit 0）；SE user = `make check-tset-embench-full`（static/dynamic，夜跑成员）。
- **SE tset（TESTCASES-100t 夜跑）**：报告 `2026-11-05-13` 4/4 成员 rc=0、`check-night-report` rc=0。llvm-ts static `discovered 222 - excluded 8 = total 214`，pass 214 / fail 0 / blocked 0；dynamic 同；blocked 不计入通过。
- **math_test**：`picolibc/math_test` 仍 `BLOCKED`（B7 数值差异），现测 QEMU `0 errors / 76404 functions`，gem5 `238 errors / 76404 functions`（exit 1）；BLOCKED 不计入 `AGREE_PASS`。
- **退出码状态**：快照按当前引擎实现生成；`SPEC-187t` 退出码规范已定稿、QEMU/gem5 实现尚未迁移，迁移后须再生成一次。
- **`TESTCASES-102t` 起 arch 探针去 icount 化**：20 个 timing 用例改为读时设 deadline + 有界轮询（窗口 ≥10× 名义值），QEMU 与 gem5 用同一份探针实际对照；下方 2026-11-05 快照里的 20 个 `BLOCKED` 已过时，等矩阵任务重生成 `tests/parity/matrix-M11.md`。
- **本快照（2026-11-05 晚，`GEM5-020t` 后）**：`node/arch` 249 `AGREE_PASS` + 20 `BLOCKED`（icount N/A）、`GEM5_ONLY_FAIL=0`、`DIFF=0`。上一版 14 条 `GEM5_ONLY_FAIL`（`QEMU-083t` 后 gem5 未对齐的历史快照）已由本次替换：14 条逐条转 `AGREE_PASS`，含 `arch/umon/m5_perm_badcombo_cfxreg`（自环已消除）。`GEM5-020t` 将 gem5 的 10 处 CFXREG fault 目标由 `cfxha` 改为当前运行模式 monitor，与 `QEMU-083t` 对齐。
- **引擎冻结**：`GEM5-020t` 评审期间共享 gem5 二进制被反复重建（实测中途 md5 变化导致整轮矩阵失效）；本快照用重建后二进制的**冻结副本**（md5 `d64b0f9…`，源 commit `1ad69d2…`，配置用源树 `fs.py`）生成，矩阵身份即该副本；证据目录保留冻结件与前后两轮作废日志。

## 已知例外（**不**参与硬门的 `AGREE_PASS`）

`run_parity.py` 顶部有两张**显式登记表**，每条都有根因，矩阵里保留
`raw_status`（引擎真实状态）供审计：

- `PICOLIBC_KNOWN_BLOCKED`：仅 `math_test`（B7 数值差异，`GEM5-015t` 遗留①），
  gem5 始终记 `BLOCKED`，不写 PASS、不计入 gem5 通过。
- `KNOWN_GEM5_BLOCKED`：**gem5 侧缺陷**登记表（QEMU 通过、gem5 不通过；修复属
  `components/gem5`）。现为**空表**（既有 semihosting 缺陷已由 `GEM5-018t` 全数
  修复）；后续若发现 gem5 侧缺陷仍登记于此，逐条记 `BLOCKED` + 「另立 gem5
  任务」，`raw_status` 保留；若某条后来变成 PASS，判据会报 stale（必须删登记）。

## shim 参数子集与限制

支持：`-M`/`-machine dadao-m1[,profile=tiny|node][,bootrom-image=]`、`-bios`、
`-kernel`、`-semihosting-config enable=on,target=native[,chardev=][,arg=…]`、
`-chardev file,id=…,path=…`、`-nographic`、`-display none`、`-monitor none`、
`-serial none`、`-d cpu -D <log>`、`-dfilter <base+size,…>`（对 gem5 trace 做
同样的 block 过滤，保证探针「最后一个 block」观测等价）。

`-qmp`/`-S`/`-s`/未知选项 ⇒ rc=2。`-chardev …,input-path=P` 接到
gem5 进程 stdin，`SYS_READC` 读到与 QEMU 相同的字节（不再记 BLOCKED）。

引擎路径通过环境变量传给 shim（由 `run_parity.py` 设置）：
`PARITY_GEM5`、`PARITY_GEM5_CONFIG`、`PARITY_GEM5_PROFILE`、
`PARITY_GEM5_BOOTROM`、`PARITY_WORK_ROOT`。

## Node embench wrapper（历史）

> **Node embench 归历史、不计入 M11 Node 验收**（见上「M11 收口口径」）；M11 起 Node 不跑 Embench，当前矩阵不再生成 `node/embench` 行。本节只说明旧快照时期的 wrapper 机制。

`run_embench_e2e.py` 固定发 `-M dadao-m1`（Tiny 形状）。Node 矩阵的证据层
wrapper 把它改写为 `dadao-m1,profile=node,bootrom-image=…`，其余 argv 原样，
并把每次改写后的 argv 落 JSON 日志；矩阵 `qemu.machine` 从日志回填，判据检查
Node/embench 行必须含 `profile=node` 且有 wrapper 记录。

## 证据与快照

- 全量矩阵 JSON/Markdown 与日志落 `--work-dir`/`--json`/`--markdown`（默认
  `/tmp/opencode/qemu-gem5-parity/**`，gem5 `--outdir` 亦只落临时区）。
- 入库快照 `tests/parity/matrix-M11.md` 由收口任务的证据层从现场 Markdown `cp`，
  不手改数字；证据脚本同时校验计数自洽、引擎身份、Node 历史归类与反例注入。
- 生成矩阵的标题与尾部 `Evidence script` 行不硬编码任务号/证据路径（改为通用标题
  + 指向本 README「证据与快照」）；快照随 M11 收口重生成自动刷新，不手改。
