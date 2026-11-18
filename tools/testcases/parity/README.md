# 跨引擎同模式 parity 驱动（`tools/testcases/parity/`）

把 **QEMU system** 与 **gem5 FS** 的同 profile、同 case 结果做成可重跑、可机械判定的矩阵。
配对**只允许** QEMU system ↔ gem5 FS（同 `tiny`/`vast`），见 `ADR-0048 D1/D2`。

本目录**不是**新的测试向量体系：case 全部来自现有清单/驱动（`tests/inst/*.yaml`、
`tests/arch/umon/expected.yaml`、`Makefile::ARCH_CFX_PROBES` + `min_rom_probe_046t`、
`.work/source/embench-iot/src/*`、picolibc Meson 清单）。parity 只做**跨引擎对账**，
不新增期望值、不按 QEMU 实测反推期望。

## 文件

- `run_parity.py`：枚举 case、分别驱动两引擎、归一化、硬门判定、输出 JSON/Markdown。
- `qemu_gem5_shim.py`：把现有驱动发出的 QEMU 系统 argv 子集映射到
  `gem5.opt --outdir … configs/dadao/fs.py`。
- `three_platform_matrix.py`：三平台（qemu / gem5 / chipyard）逐例矩阵汇总入口
  （只读已入库 JSON，见「三平台矩阵（m13-integ-001）」）。
- `fp_diff.py`：FP `scope: fp` 三平台逐例差分报告生成器
  （见「FP 三平台差分（m13-integ-002）」）。
- `int_diff.py`：非 cfx、非 FP 的 `.S` 载体三平台逐例差分报告生成器
  （见「整数与访存三平台差分（m13-integ-003）」）。
- `acceptance_report.py`：M13 收口入口（复用 `int_diff`/`fp_diff` 的 `build()`，
  出矩阵册 + 收口报告，见「M13 收口与矩阵冻结（`m13-integ-005`）」）。
- `engine_parity_*.{py,sh}`：M12 engine-parity 报告生成器/核对器/收集器/证据脚本
  （见「engine parity 报告（`m12-chipyard-016`，生成器入仓 `m12-chipyard-017`）」）。

## 用法

```sh
python3 tools/testcases/parity/run_parity.py \
  --profiles tiny,vast --scopes inst,arch,embench,picolibc \
  --qemu .dadao/cross-toolchain/bin/qemu-system-dadao \
  --gem5 .work/source/gem5/build/DADAO/gem5.opt \
  --gem5-config .work/source/gem5/configs/dadao/fs.py \
  --bootrom-tiny .dadao/tests/bootrom/tiny/bootrom_tiny.bin \
  --bootrom-vast .dadao/tests/bootrom/step5/bootrom_step5.bin \
  --bootrom-vast-inst .dadao/tests/bootrom/step5/bootrom_step5_inst.bin \
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

另带 `profile ∈ {tiny,vast}`、`scope ∈ {inst,arch,embench,picolibc}`。

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

## SE tset 双向一致性（INTEG-059t，G3 收口）

`run_parity.py` 只做 **QEMU system ↔ gem5 FS**；SE user 模式的完整 tset 对账由
`tests/ee-user/tset_matrix_user.py` 汇总（`m15-testcases-012` 从本目录迁出；不跑 guest，只读两份已入库的 per-case 基线）：

```sh
python3 tests/ee-user/tset_matrix_user.py \
  --json-out <运行期目录>/se-parity.json \
  --markdown-out <运行期目录>/se-parity.md \
  --matrix-section-out <运行期目录>/matrix-section.md
python3 tests/ee-user/tset_matrix_user.py --self-test   # 逐条反例注入
```

- 中间产物（per-case JSON、SE 段）落**运行期目录**；入库的人读快照是
  `docs/TestReports/M11-三平台一致矩阵.md`（目录规则见
  `docs/TestReports/README.md`），由证据脚本从运行期 `cp`，不手改。

- 输入：static = `tests/data/GEM5-021t-baseline-summary.json`（`TESTCASES-103t` 预算）、
  dynamic = `tests/data/TESTCASES-104t-dynamic-summary.json`（`GEM5-027t` 动态装载）。
- **不信任已声明计数**：per-suite counts / cross 列表 / totals / gap 桶全部从
  per-case 行重算并与声明值对账；不一致 rc=1。
- **每个非 pass 行必须有 owner**：`timeout` ⇒ budget；`blocked` ⇒ 证据文本必须
  归到 `implementation`/`environment`（`SE syscall table`、`ldso`、`SE loader`、
  guest root 缺 DADAO 工具）；`gem5_only_fail` ⇒ 显式登记表（`ISS-357` / 环境缺口）；
  `qemu_only_fail` ⇒ 登记表为空（`ADR-0048 D5`：不得当作 gem5 胜利）；两引擎同
  verdict 的 `known-fail`（`ISS-251`）才允许进 `both_non_pass`。
- 输出 SE 段片段（`--matrix-section-out`）与完整快照
  （`--compose-out --fs-matrix <run_parity 输出> --picolibc-json <tiny/picolibc
  JSON>`；旧的 `--carry-from` 只在 B7 登记未裁定时期承接上一版行）；数字一律
  现场统计，不手改。

## 三平台矩阵（qemu / gem5 / chipyard，`m13-integ-001`）

`three_platform_matrix.py` 是**三平台汇总入口**：不跑 guest，只读**已入库**的逐例
JSON，复算计数/判定/归因并渲染 `docs/TestReports/<M>-<主题>.md` 形态的册
（chipyard 列在 M12 核未就绪时记 `N/A` + 依据，不是伪值）。

```sh
# 从已入库基线重建（默认输入 = m13 长尾 static/dynamic 两份 refs）
python3 tools/testcases/parity/three_platform_matrix.py \
  --markdown-out <运行期目录>/m13-三平台差分矩阵.md
# 入库册与重建结果逐字节比对（册不得手改）
python3 tools/testcases/parity/three_platform_matrix.py \
  --check docs/TestReports/M13-三平台差分矩阵.md
# 追加来源 / 单独挂 chipyard 证据（`m13-integ-002`/`003` 用）
python3 tools/testcases/parity/three_platform_matrix.py \
  --source <canonical.json> --chipyard <chipyard.json>
python3 tools/testcases/parity/three_platform_matrix.py --self-test
```

- **输入两种形态**（自动识别）：已入库长尾基线（`rows[]` + `qemu_klass`/
  `gem5_klass`/`gem5_gap`）或 canonical `{"schema": "three-platform-cases/1",
  "link_mode": …, "cases": [{case, suite, qemu/gem5/chipyard}]}`。同名
  `(档, suite, case)` 跨输入按**平台列**合并，同一平台两值不同即 FAIL。
- **复用不复制**：状态词表与 `qemu ↔ gem5` 判定 = `run_parity.py`（`STATUSES`、
  `_verdict`）；owner 词表与「预算耗尽 ≠ 判定」= `se_tset_matrix.py`（`OWNERS`、
  `TIMEOUT_CAPABILITY`）。
- **fail-closed**：非 `AGREE_PASS` 行必须命中归因登记表（`BLOCKED_OWNERS` /
  `GEM5_ONLY_FAIL` / `BOTH_NON_PASS`），未登记即 rc=1；legacy 基线须
  `ok=true`/`missing=[]` 且 `selection.total`/`by_suite` 与行一致；chipyard 非
  `N/A` 行必须带 `owner` + `basis`。
- **可重建**：册内容只来自已入库 JSON（不写重建时刻、不写运行期路径），故
  `--check` 在 fresh clone 上也能逐字节复现；写入仓库须显式 `--allow-repo-write`。

## FP 三平台差分（`m13-integ-002`）

`fp_diff.py` **不跑 guest**：输入是 `run_asm_suite.py` 的三平台逐镜像 JSON
（同 ELF、status/exit/结果字节流）+ 每镜像 `.out` 结果流（按 8 字节检查点切分），
加上 `contracts/opcodes.yaml`、`spec/SimRISC-07` 附录 A、`tests/inst.yaml` 三个
静态真源，输出 `tests/data/m13-002-fp-diff.{json,md}`（入库基线的落点）。

```sh
python3 tools/testcases/parity/fp_diff.py \
  --run fp-book=<run.json> --work fp-book=<work-dir> \
  --run fp-extras=<run2.json> --work fp-extras=<work-dir2> \
  --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \
  --json-out <运行期>/m13-002-fp-diff.json \
  --markdown-out <运行期>/m13-002-fp-diff.md
python3 tools/testcases/parity/fp_diff.py --check <已入库 .md 或 .json>
python3 tools/testcases/parity/fp_diff.py --self-test    # 8 类反例逐条判出
```

- **计数口径**：`scope: fp` = 66（机器可读全集）；附录 A = 52（`SimRISC-07` 的
  运算/转换/比较族）；历史别名「47 条」在任何机器可读源都复现不出（`issues.yaml`
  已登记，退役）。历史口径只写进报告，不作判据。
- **判据**：三平台缺一 / 未知 id / 重复镜像 / 点号与载体不符 / `ok` 与平台记录
  矛盾 / 未归因的平台差异 ⇒ 非零退出；覆盖缺口逐条列出（`not_indexed` 不阻断，
  载体存在且由 L2 `check-inst-asm` 执行）。
- **矩阵**：4 档 `rf0[33:32]` × {NONE,NV,DZ,OF,UF,NX} 的链例点计数与三平台一致数；
  只统计 `AGREE_PASS` 链例镜像的点，空白格给出「现有向量无此组合」的逐格原因。
- **已知项单列**：`ISS-357`（SE 双 fd 输出顺序）与 picolibc `math_test` 不参与
  FP 语义差异计数；单通道 semihosting 字节流比较不经过该路径。
- 复用：载体点数/点号 = `run_asm_suite.scan_source`；owner 词表 =
  `se_tset_matrix.OWNERS`；平台状态词表 = `run_parity.STATUSES`。

## 整数与访存三平台差分（`m13-integ-003`）

`int_diff.py` 与 `fp_diff.py` 同形：**不跑 guest**，输入是 `run_asm_suite.py` 的
三平台逐镜像 JSON + 每镜像 `.out` 结果流；范围 = `tests/inst/**/*.S` 中**非 cfx**
（册 `11-cfx`）且**非 FP**（`scope: fp`）的载体（现场枚举，计数不写死）。
输出 `tests/data/m13-003-int-diff.{json,md}`（入库基线的落点）。

```sh
python3 tools/testcases/parity/int_diff.py \
    --run int-book=<run.json> --work int-book=<work-dir> \
    --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \
    --json-out <运行期>/m13-003-int-diff.json --markdown-out <运行期>/m13-003-int-diff.md
python3 tools/testcases/parity/int_diff.py --check <已入库 .md 或 .json>
python3 tools/testcases/parity/int_diff.py --self-test   # 10 类反例逐条判出
```

- **分母**：`.S` 载体总数 → 排除 `scope: fp` 与册 `11-cfx` → 本报告载体数/镜像数
  （链例 + 故障例），三平台完成数按记录现场统计；未跑项按 id 归集并给原因。
- **语义出处**：逐 id 的 `spec_cite`（`contracts/opcodes.yaml`）解析到
  `spec/SimRISC-NN-*` 章节，并在章内核对助记符（表格首列优先、行内代码次之）；
  解析不到 ⇒ 记 **spec 歧义** 并逐条列出（不臆造期望）。非 id 载体
  （`00-isa-design/undi_reserved`）取自身文件头的 spec 出处。
- **判据**：缺平台 / 未知 id / 重复记录 / `ok` 与平台记录矛盾 / 点号不连续 /
  未归因差异 ⇒ 非零退出。归因表可代码内（`ATTRIBUTIONS`）或 `--attribution`
  外部 JSON 逐条申报；每条 owner 必须 ∈ `OWNERS`、`spec_cite` 必须解析到现存
  章节，**未列出的差异仍 rc=1**（表只许逐条申报，不是放行开关）。
- 复用：逐镜像装载/判定 = `fp_diff.py`（`load_run`/`merge_runs`/`classify`）；
  载体统计 = `run_asm_suite.scan_source`。

## M13 收口与矩阵冻结（`m13-integ-005`）

`acceptance_report.py` 是**收口入口**：不跑 guest、**不新增第二套口径**，输入与
`int_diff.py`/`fp_diff.py` 相同（同一批 `run_asm_suite.py` 三平台逐镜像 JSON +
每镜像 `.out` 结果流），并**复用**这两个生成器的 `build()`：

```sh
python3 tools/testcases/parity/acceptance_report.py \
    --run book=<run.json> --work book=<work-dir> \
    --engine qemu=<md5> --engine gem5=<md5> --engine chipyard=<md5> \
    --tool llvm-mc=<md5> --tool bootrom=<md5> \
    --json-out <运行期>/m13-005-acceptance.json \
    --markdown-out <运行期>/m13-005-acceptance.md \
    --matrix-out <运行期>/M13-三平台差分-矩阵.md
python3 tools/testcases/parity/acceptance_report.py --check <任一产物>
python3 tools/testcases/parity/acceptance_report.py --self-test   # 9 类反例
```

- **输入切分**：`run_asm_suite --books-root tests/inst` 的一批输入含 int / fp / cfx
  三段；两个生成器都只接受自己的 scope（fail-closed），故本脚本按段切分后再分别
  `build()`。落不进三段的记录、重复记录、段内记录数 ≠ 现场枚举镜像数 ⇒ rc=1。
- **向量面对账**：逐册统计载体 / 链例点 / 故障例 / 镜像，并断言
  「int + fp + cfx = `tests/inst` 全量」与「两份报告的 `coverage`/`results` 分母
  逐项相符」——对不上即 rc=1，不静默。
- **差异归因合并**：002/003 的差异由**同一批输入重算**（不读旧报告），按
  `spec` / `implementation` / `test asset` 分类；未知 owner 或未知缺口 kind ⇒ rc=1。
  004（riscv-tests）语料已退役，只保留任务书结论作指针。
- **冻结产物**：矩阵册 `docs/TestReports/M13-三平台差分-矩阵.md` + 收口报告
  （`tests/data/m13-005-acceptance.{json,md}`）。三者都是输入的确定性
  函数：不写墙钟、不写运行期路径，**记输入 commit**（`--input-commit`，缺省
  `git rev-parse HEAD`）；换 commit 复算须显式传同一 sha，否则 `--check` 会如实报
  不一致（陈旧可见）。

## engine parity 报告（`m12-chipyard-016`，生成器入仓 `m12-chipyard-017`）

M12 判据 = **engine parity**（chipyard 与 qemu 同代码同 ELF、只换引擎，picolibc
逐例状态必须一致；qemu 侧既有缺口登记在册、不计到 chipyard）。报告对
（`tests/data/m12-016-embench-picolibc.{json,md}`）是**运行期批次输入的
确定性函数**，本目录的四个脚本即其生成器（此前只在 016 证据树里，fresh clone
复现不了）：

- `engine_parity_report.py`：合并两套批次输入 ⇒ 报告对；`--check` 与入库报告
  **逐字节**比对（打印两处 sha256，不符 rc=1 并指出首个差异行）。
- `engine_parity_pending.py`：列出 picolibc 侧仍缺终态判决的用例（budget
  `blocked (host timeout)` 不算终态；embench 侧 pending = 语料
  `benchmark × opt` − `cases_seen`，语料规模由用例名现场派生）。
- **超时口径**（`m12-chipyard-031`，用户 2026-11-15 裁定「blocked 容易让人误解，
  timeout（12h）如何？」）：预算耗尽的用例记 `timeout(<预算>)`（显示形
  `timeout(12h)`，机读值 `TIMEOUT`；预算由 `--timeout` 现场换算，`3600→1h`、
  `5400→90m`），**`blocked` 只留给构建/环境缺口**（ISS-193 long-double、CFX6 缺
  载体、harness 服务未实现）。`timeout` 属**无判决**：不参与逐例状态一致比较、
  不计入 chipyard 独有失败 —— 报告 §0/§2 逐条写明；生成器把标签经
  `parse_budget` 回读校验，换算写错即 rc=1（不打印悄悄错的标签）。
- `engine_parity_collect.sh`：从节点拉回报告引用的逐例 `semi.out`/`sim.log`
  （供抽查，不重跑批次）。落点 = `.work/evidence/<TASK>/cases/<node>/<suite>/<case>/`
  （`--dest` 可覆盖）：逐例嵌套结构属证据树，不放 `.work/log/` —— 那里受 L1
  `check-run-artifacts` 的平铺命名约束（`check-<name>.log` 或
  `<TASK-ID>-<purpose>.(log|json|txt)`）。
- `engine_parity_run.sh`：016 的端到端证据脚本（接线/契约探针/报告一致性/可选
  `--full` qemu 回归与 `--inject` 注入）。

```sh
python3 tools/testcases/parity/engine_parity_report.py --check   # 复现校核（rc=0 即逐字节一致）
python3 tools/testcases/parity/engine_parity_pending.py          # 现场 pending
bash tools/testcases/parity/engine_parity_run.sh                 # A–F
```

接口：`--repo`（默认脚本上溯三层）；报告生成器/`pending` 另有 `--log-dir`
（默认仓库内 chipyard 运行期日志目录），collect 用 `--dest`；`--node-map
<日志名>=<节点>` 覆盖分片节点（默认见脚本内 `SHARD_NODE`）。输入全部运行期、
永不入库；`--check` 需要与生成报告时相同的批次输入，否则 rc≠0。

## M11 收口口径（TESTCASES-098t）

- **矩阵范围**：Tiny/Vast 的 `inst`/`arch` + Tiny `picolibc`（旁证；`math_test` PASS，B7 已关闭）。Embench 不进本矩阵。
- **M11 Vast 验收范围**：只验收 `arch`（cfx/arch/PTW/模式）。`vast/inst` 行仅作现场参考，不进入 Vast 验收通过数。
- **历史归类**：`GEM5-016t`/`QEMU-080t` 的 Vast `inst`/`embench` 结果 = **历史，不计入 M11 Vast 验收**；`vast/embench` 不再生成。
- **Vast 不跑 Embench**：M11 起 Vast profile 不跑 Embench。
- **Embench 归属**：Tiny system/bare-metal = `run_embench_e2e.py`（`make test-m6`，guest exit 0）；SE user = `make check-tset-embench-full`（static/dynamic，回归运行成员）。
- **SE tset（TESTCASES-100t 回归运行）**：报告 `2026-11-05-13` 4/4 成员 rc=0、`check-night-report` rc=0。llvm-ts static `discovered 222 - excluded 8 = total 214`，pass 214 / fail 0 / blocked 0；dynamic 同；blocked 不计入通过。
- **math_test**：`picolibc/math_test` **PASS**（双引擎 `Tested 76404 functions, 0 errors`；QEMU/gem5 exit 0）。B7 数值差异由 `INTEG-058t`（f2i 舍入方向修正）修复、`GEM5-032t` 定位，`GEM5-033t` 注销 `PICOLIBC_KNOWN_BLOCKED`；picolibc 段由现场 `run_parity --profiles tiny --scopes picolibc` JSON 重生成。
- **退出码状态**：快照按当前引擎实现生成；`SPEC-187t` 退出码规范已定稿、QEMU/gem5 实现尚未迁移，迁移后须再生成一次。
- **`TESTCASES-102t` 起 arch 探针去 icount 化**：20 个 timing 用例改为读时设 deadline + 有界轮询（窗口 ≥10× 名义值），QEMU 与 gem5 用同一份探针实际对照；下方 2026-11-05 快照里的 20 个 `BLOCKED` 已过时，等矩阵任务重生成 `docs/TestReports/M11-三平台一致矩阵.md`。
- **本快照（2026-11-05 晚，`GEM5-020t` 后）**：`vast/arch` 249 `AGREE_PASS` + 20 `BLOCKED`（icount N/A）、`GEM5_ONLY_FAIL=0`、`DIFF=0`。上一版 14 条 `GEM5_ONLY_FAIL`（`QEMU-083t` 后 gem5 未对齐的历史快照）已由本次替换：14 条逐条转 `AGREE_PASS`，含 `arch/umon/m5_perm_badcombo_cfxreg`（自环已消除）。`GEM5-020t` 将 gem5 的 10 处 CFXREG fault 目标由 `cfxha` 改为当前运行模式 monitor，与 `QEMU-083t` 对齐。
- **profile 命名**：`m12-testcases-001` 起矩阵 profile 为 `tiny` / `vast`（旧快照里的 `node` = 现 `vast`）；重生成的快照按新名输出，`node` 行不再出现。
- **SE 段**：`docs/TestReports/M11-三平台一致矩阵.md` 末尾的「SE tset matrix」段由 `se_tset_matrix.py` 生成（static + dynamic 两档，见上节）。
- **引擎冻结**：`GEM5-020t` 评审期间共享 gem5 二进制被反复重建（实测中途 md5 变化导致整轮矩阵失效）；本快照用重建后二进制的**冻结副本**（md5 `d64b0f9…`，源 commit `1ad69d2…`，配置用源树 `fs.py`）生成，矩阵身份即该副本；证据目录保留冻结件与前后两轮作废日志。

## 已知例外（**不**参与硬门的 `AGREE_PASS`）

`run_parity.py` 顶部只有一张显式登记表，每条都有根因，矩阵里保留
`raw_status`（引擎真实状态）供审计：

- `KNOWN_GEM5_BLOCKED`：**gem5 侧缺陷**登记表（QEMU 通过、gem5 不通过；修复属
  `components/gem5`）。现为**空表**（既有 semihosting 缺陷已由 `GEM5-018t` 全数
  修复）；后续若发现 gem5 侧缺陷仍登记于此，逐条记 `BLOCKED` + 「另立 gem5
  任务」，`raw_status` 保留；若某条后来变成 PASS，判据会报 stale（必须删登记）。

`PICOLIBC_KNOWN_BLOCKED`（`math_test` / B7）已删除：根因为 `INTEG-058t` 的
f2i 舍入方向修正（`GEM5-032t` 定位），现双引擎 `Tested 76404 functions, 0 errors`，
`math_test` 按普通 case 参与判定（`GEM5-033t`）。

## shim 参数子集与限制

支持：`-M`/`-machine {kaiwu-tiny,kaiwu-vast}[,bootrom-image=]`、`-bios`、
`-kernel`、`-semihosting-config enable=on,target=native[,chardev=][,arg=…]`、
`-chardev file,id=…,path=…`、`-nographic`、`-display none`、`-monitor none`、
`-serial none`、`-d cpu -D <log>`、`-dfilter <base+size,…>`（对 gem5 trace 做
同样的 block 过滤，保证探针「最后一个 block」观测等价）。

`-qmp`/`-S`/`-s`/未知选项 ⇒ rc=2。`-chardev …,input-path=P` 接到
gem5 进程 stdin，`SYS_READC` 读到与 QEMU 相同的字节（不再记 BLOCKED）。

引擎路径通过环境变量传给 shim（由 `run_parity.py` 设置）：
`PARITY_GEM5`、`PARITY_GEM5_CONFIG`、`PARITY_GEM5_PROFILE`、
`PARITY_GEM5_BOOTROM`、`PARITY_WORK_ROOT`。

## Vast embench wrapper（历史）

> **Vast embench 归历史、不计入 M11 Vast 验收**（见上「M11 收口口径」）；M11 起 Vast 不跑 Embench，当前矩阵不再生成 `vast/embench` 行。本节只说明旧快照时期的 wrapper 机制。

`run_embench_e2e.py` 固定发 `-M kaiwu-tiny`（Tiny 形状）。Vast 矩阵的证据层
wrapper 把它改写为 `kaiwu-vast,bootrom-image=…`，其余 argv 原样，
并把每次改写后的 argv 落 JSON 日志；矩阵 `qemu.machine` 从日志回填，判据检查
Vast/embench 行必须含 `kaiwu-vast` 且有 wrapper 记录。

## 证据与快照

- 全量矩阵 JSON/Markdown 与日志落 `--work-dir`/`--json`/`--markdown`（默认
  `/tmp/opencode/qemu-gem5-parity/**`，gem5 `--outdir` 亦只落临时区）。
- 入库快照 `docs/TestReports/M11-三平台一致矩阵.md` 由收口任务的证据层从现场 Markdown `cp`，
  不手改数字；证据脚本同时校验计数自洽、引擎身份、Vast 历史归类与反例注入。
- 生成矩阵的标题与尾部 `Evidence script` 行不硬编码任务号/证据路径（改为通用标题
  + 指向本 README「证据与快照」）；快照随 M11 收口重生成自动刷新，不手改。
