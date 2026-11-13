# m12-chipyard-030: `rootn(±0,2) ⇒ +0` 与自写 FP 的结果 NaN 统一 canonical（RTL + 模型）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-007`（口径定稿；本任务不据 QEMU/gem5 结论推定 RTL 行为）
**可并行分片**：否（单组件单写者）
**状态**：已验证

**预估**：3–4 h（含 elab + Verilator 重建）

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 **canonical quiet NaN**（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。依据：IEEE §6.2.3 payload 传播只是 *should*、§6.3 不规定符号；**Berkeley hardfloat 即 canonical**（`RoundAnyRawFNToRecFN.scala`：`signOut = Mux(isNaNOut, false.B, …)`、NaN 时有效位只置 quiet 位）。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D2 / §D3。

## 背景（RTL 现状现场）

`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch`：

- 取整/转换包装（`invalidExc` / `isNaNOut` 那一段）已把 **符号清 0**（`signOut = Mux(isNaNOut, false.B, io.in.sign)`），但注释自陈「DADAO: a quiet NaN input keeps its payload（窄化截断位 OR 进 payload 末位、加宽左移）」⇒ qNaN 输入的 payload 被传播、窄化还额外 OR 截断位。
- `WumingDivSqrtRecFN` 另有独立的一处 NaN 传播：`nanSrc`/`nanSig = (nanSrc.sig << 2)(sw+2,0)` → `nanSigZ` → 送进 rounder 的 `io.in.sig`（`Mux(nanInZ, nanSigZ, …)`）⇒ 除法/开方同样传播首 NaN payload。
- `WumingDivSqrtRecFN` 注释：「`rootn(-0, 2)` is unspecified by spec §2.2; -0 is returned」⇒ `foroot(−0,2) = −0`；实现上零结果走 `zeroOut = Mux(io.sqrtOp, rawA.isZero, …)`，符号取 `sign = Mux(io.sqrtOp, rawA.sign, rawA.sign ^ rawB.sign)`，rounder 对非 NaN 结果保号 ⇒ 零结果继承 `−0`。
- 模型 `tools/chipyard/fp_ref.py`：`round_bits(...)` 的 `nan_fract` 传播 payload；`sqrt_exact(...)` 零分支返回 `ra["sign"] << (...) `（保号）⇒ 与 RTL 同现状。

## 范围（RTL + 模型 + 单元/扫描覆盖；不含向量文件）

1. **R1**：`WumingDivSqrtRecFN` 的 sqrt 路径——源为 `+0`/`−0` 时结果 `+0`（符号位 0），不置标志；`±Inf`、负有效数（`NV` + canonical qNaN）、有限正数行为不变。
2. **R2**：结果 qNaN 一律 canonical（符号 0、payload 只置 quiet 位）：
   - 取整/转换包装：删除 qNaN 输入的 payload 传播与窄化截断位 OR（`nanFract` 恒为 `quietBit`）；
   - 除法/开方：删除 `nanSig`/`nanSigZ` 通路对 rounder 的 payload 注入（NaN 时只由 rounder 置 quiet 位）；
   - 适用面：算术 add/sub/mul/div、scaleB、root、remainder、FMA、rnd、minmax（双 NaN 已 canonical）、`fo2ft`/`ft2fo` 转换；
   - **不适用**（须保持）：`ft2ft`/`fo2fo` 复制（纯位搬移）；`ftscmp`/`foscmp` 的 sNaN 结果（signaling 位型、符号 0）；`minmax` 单 NaN 返回数字。
3. **模型同步**：`tools/chipyard/fp_ref.py` 按 **spec 派生**改（`round_bits` 的 NaN payload、`sqrt_exact` 的零分支），**不是**按 RTL 现状反推；`tools/chipyard/fp_sweep.py` / `tools/chipyard/fp_unit/unit_run.py` 补覆盖点（root ±0、带 payload/负号 qNaN、`fo2ft` NaN），计数取现场。
4. `components/chipyard/changelog.md` 记一条；补丁经 `make_patch` 重导出（`series` 不变，一文件一补丁）。

**非范围**：不改 `tests/inst/**`（YAML 向量归 `m13-testcases-032`）、不改 `tests/case-ledger.tsv`、不改 QEMU/gem5/spec、不改 `WumingFPUnitHarness` 之外的公共接口（若 harness 需加断言可改，须披露）。

## 角色边界（用户 2026-11-13 裁定：节点只作评测用）

- **主控机 = 唯一仓库写者 + 构建调试 + L1 静态门控**：改 `components/chipyard/patches/**`、`tools/chipyard/**`、changelog；`make_patch` 导出补丁；跑 `check-patch-tree` / `check-source-state` / L1；elab + Verilator 构建亦在主控机（调试迭代不得外包）。
- **节点 = 评测执行机**：主控机 `make sync-node-repo` 后，节点 `make apply-series` → 节点**自行重建** chipyard（Verilator 产物与机器相关，**禁止跨机复制**）→ 节点跑 FP 评测（`fp_sweep` / `fp_unit`）。节点**不做**仓库修改、补丁导出、调试迭代、L1 静态门控。
- 评测就近判据（用户 2026-11-13）：单套件墙钟 `< 15 min` ⇒ 主控机就近跑（构建时间不计入）；`> 15 min` ⇒ 分片到节点并行。
- **不得用 QEMU/gem5 结论推定 RTL 行为**：RTL 结论只认 RTL 自身仿真（单元 harness 或 Verilator 探针）；QEMU/gem5 仅作对照，三方对照由 `m13-testcases-032` 汇总。

## 验收标准（可执行、可失败）

1. **逐点实测**（改后 RTL：单元 harness 或 Verilator 探针，给出装载值/读回路径）：
   - `foroot(−0,2)` ⇒ `0x0000_0000_0000_0000`；`ftroot(−0,2)` ⇒ 低 32 位全 0、符号 0；`foroot(+0,2)`/`ftroot(+0,2)` ⇒ `+0`、无标志；`foroot(−4.0,2)` ⇒ canonical qNaN + `NV`
   - `ftadd(0x7FC1_2345, 1.0)` ⇒ `0x7FC0_0000`；fo 侧带 payload 且负号 qNaN 的 `foadd` ⇒ `0x7FF8_0000_0000_0000`
   - `fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - 排除项：`ft2ft` 复制带 payload NaN ⇒ 原样；`foscmp(qNaN,1.0)` ⇒ `0x7F80_0001` + `NV=1`
2. **模型 == RTL 逐字节**：`fp_sweep`/`fp_unit` 全绿（`mismatch=0`），受影响格数/向量数取现场输出；`fp_ref.py` 改动须能追到 spec 条款（完成区写清「哪句 spec → 哪行模型」）。
3. **可达 FAIL 注入（≥2 路）**：① 把 `nanFract` 改回「传播首 NaN payload」⇒ 对应格红；② 把 root 零分支改回保号 ⇒ `−0` 例红。均 `cp`+md5+`touch` 还原（注意 `cp -p` 假绿坑）⇒ 回绿；注入期须断言组件源树 diff 非空、还原后 blob == `base+1` commit blob。
4. **门控**：`check-patch-tree`（chipyard problem=0）、`check-source-state` rc=0、`apply-series` 幂等（HEAD 不变）、`check-component-changelog` rc=0；elab + Verilator 构建 rc=0、`%Error`=0。
5. **整数套件不受影响**：整数 273 例 emit md5 与基线一致（现场值；FP 改动不应触及）。
6. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`JOBS=8`，禁全核。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树（`ISS-368`）。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

逐行审查 `WumingFP.scala` 改动、`fp_ref.py`/`fp_sweep.py`/`unit_run.py` 的改动与证据脚本；判决：**可标「待验收」**（findings 全部已修，复验见右列）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `fp_ref.sclb_exact` 对 qNaN 输入仍返回原 payload（`return x & mask`），与 R1/R2 矛盾 | ✅已修 | 改为 `_canon_qnan`，docstring 与 `selfcheck_rndsclb` 的 NaN 锚点同改 | `fp_ref rndsclb 200` mismatches=0；核上 `sclb_nan_ft/fo`、`sclb_exact_ft/fo`、`sclb_ovf_*`、`sclb_unf_*` byte-exact（修前这 7 组红） |
| F2 `round_exact` 的 NaN 分支一度写成 `_canon_qnan`（那是**IEEE** 字），而该函数契约是**recoded** 字 | ✅已修 | 改为 recfn 形式（NaN 指数 `7 <<(oe-2)` 置在 `oe+1` 位上，再接 quiet 位），并注明「本函数所有返回值都是 recoded」 | 新增 `selfcheck` NaN 位级锚点：修前 240 mismatches，修后 0（10560 组） |
| F3 故障镜像判据沿用 `m12-005` 的「rc≠0 / 无 POST」——自 `m12-019` 起同步故障进 cfx 处理机、继续执行 | ✅已修 | 改判 hmon 的 `excp cause=0x…`（one-hot 逐镜像比对）；证据脚本注释说明判据来源 | 58/58 镜像命中期望 cause |
| F4 `unit_run` 的 sqrt 组对 hardfloat 逐值比较会在 `sqrt(±0)` 变红（hardfloat 是 `squareRoot(−0)=−0`） | ✅已修 | 新增 `fn_val_root`（只折叠零的两种写法）并注明这是与 hardfloat 唯一有意的值差异；oracle 侧仍逐字节 | `sqrt ft/fo` hf-value-diff=0、oracle-diff=0 |
| F5 `_quieted` 变成死代码、多处 `src = …` 赋值无用 | ✅已修 | 删除 helper 与 4 处 `src` 局部 | `grep _quieted` 无命中；三个自检 rc=0 |
| F6 `QEMU_GROUPS` 的注释在 qNaN 结果改为 canonical 后不再准确 | ✅已修 | 补一段：哪些组带 qNaN 结果格、与 softfloat 的 payload/符号差异、QEMU 侧归 `m13-integ-010`、汇总归 `m13-testcases-032` | 注释与 `cases_*_nan` 组的归属一致；组数 50（现场） |

证据脚本自身的三个坑（已修，留作知识沉淀）：① 不能把 chipyard conda 环境放进全局 `PATH`（其 python 3.10 无 `tomllib`，仓库 `make` 全红）；② Verilator harness 会读 stdin，循环读文件时每条 sim 必须 `</dev/null`（否则键名被吃掉前 9 字节）；③ 汇总表格式是 `vectors= N failed=N`（无冒号/竖线），与明细行不同，解析助手须分开。

### 第 2 轮 reviewer 验收（2026-11-13）

**重跑（我自己的命令 → 真实输出/退出码；长输出落运行期临时目录 `/tmp/opencode/<任务ID>/`）**

1. `JOBS=32 bash .work/evidence/m12-chipyard-030/run.sh`（注入前后各一次）⇒ 两次均 `== summary: PASS=84 FAIL=0 ==`、`EXIT=0`：elab rc=0/%Error=0、Verilator rc=0、50/50 组 2118 例逐字节、58/58 镜像 cause、273 例 md5 `2d4d94651346ef673c5a855e024c1489`==基线、单元台 `TOTAL failed=0`（45 组）与 `spec points: 20 vectors table-diff=0`、`apply-series` 21 补丁+二次 0+树 hash `462516e6…` 不变、L2 rc=0。
2. `run.sh --self-test-inject` ⇒ `EXIT=0`：3 路注入均达 FAIL（table-diff=1/4、模型 oracle-diff=5）→ 还原 md5 `eb0ab6665d7b0e86036fb168843f4ab6` → 回绿。
3. `make check-patch-tree` ⇒ rc=2，8 problem 全为 qemu/gem5 并行脏树、**chipyard 段 0 条**；`make check-source-state` ⇒ rc=0 `chipyard: OK HEAD=c5d592c clean=True`（testchipip 同 OK）；`check-component-changelog`/`check-index-blobs` ⇒ rc=0；`make apply-series` ⇒ rc=1（拒绝 qemu HEAD、未动任何树），chipyard 幂等以脚本隔离实测为准。
4. `python3 tools/chipyard/fp_ref.py selfcheck 400` / `divrem 200` / `rndsclb 200` ⇒ 三次 rc=0、mismatches=0（8560 对）。
5. **我自设计的反例注入**（改本轮未动的 `WumingCompareRecFN.quietNan |= 1`）：`ONLY=C run.sh` ⇒ `EXIT=1`（`qcmp fo(qNaN,1.0)` 实测 `0x7ff8000000000001` vs 条款 `0x7ff8000000000000`、`total failed=107`、`spec-point failures=1`；root 各格仍绿，证明逐格独立）→ `cp`+md5 还原（md5 相等、源树 `git status` 0 行、HEAD 仍 `c5d592c`）→ 同一脚本重跑 ⇒ `EXIT=0`、`PASS=25 FAIL=0`。
6. **独立语义核验**（期望值我按 spec 条款手写，不经模型/oracle）：44 点 0 差错 = 单元台 20 个 spec point（RTL 实测 `outLo/outHi/flags`）+ 核上 24 个 `.out` dump：`ft2ft/fo2fo` 复制原样、`ftrnd/ftsclb/fo2ft/ft2fo` 的 qNaN ⇒ canonical 且无标志、root `±0` 四档 ⇒ `+0`、`forem/fodiv/foroot` 的 qNaN ⇒ canonical 且不置 NV、`fomin` 单 NaN 返数/双 NaN canonical；模型侧另 15 点同表全对。
7. **同源判断**：`fp_ref.round_bits` 自述「mirroring WumingRoundAnyRawFNToRecFN」⇒ 舍入原语的特殊值装配两边**同源、该条差分发现力有限**；但 `round_exact` 是独立精确有理数路径（`selfcheck` 把两者钉齐 0 mismatch）、数值路径两套算法、单元台另有 hardfloat 第三方，加上 SPEC_POINTS 抄条款 + 本次独立推导 ⇒ 本任务新规则不靠同源自比。

**约束核验**：改动恰 7 文件（`git show --name-only` 与完成区逐项一致，未触 tests/spec/contracts/Makefile）；双树 `git status -uall` 0 行、HEAD 未变（`289492d7` / `c5d592c`）；完成区 19 行、第 1 轮审阅 15 行；无运行期绝对路径；计数全部现场对上（84 / 45 / 50 / 2118 / 58 / 21 / 20）；注入全程 `cp`+md5，未用 `git checkout/restore/stash`；`JOBS=32 < nproc`，未全核。

**Findings（不阻断，交 architect 收尾处置）**：① 任务书验收 1「`foscmp(qNaN,1.0)` ⇒ `0x7F80_0001`」是笔误——`0x7F80_0001` 是 ft 位型，fo 应为 `0x7FF0_0000_0000_0001`（RTL/条款/SPEC_POINTS 三处都对）；② 任务书验收 6「`JOBS=8`」与 AGENTS 2026-11-13「`JOBS = nproc/2`」冲突，实际按脚本默认 32（未全核）；③ 跨册陈旧表述待同步（均非本任务范围）：`docs/DDLN/…/DD-A009:102`、`docs/fp-oracle-design.md:45/49/65`、`components/gem5/README.md:75`、`tools/gem5/b7_ref.py:351`、`tests/inst/fp/divrem.yaml:727`；④ `divrem_nan` 新增 6 个 qNaN case 沿用 `divrem_snan_*` 重名（识别须靠操作数）；⑤ `fn_val_root` 只放宽对 hardfloat 的零符号对照，oracle 侧仍逐字节严格（已核 `unit_run.py` 的 `r["out"] != want` 分支）。

**判决：Accepted**——终态复核：全量 `run.sh` `PASS=84 FAIL=0` `EXIT=0`、独立语义 44/0、双树干净、组件源 `c5d592c` 未变。

## 完成区

**测试结果**：通过 84/84（`run.sh` → `PASS=84 FAIL=0`，rc=0；默认 `FORCE_BUILD=1` 抹掉 generated 树后**真** elab+Verilator 重建）；注入自检 3/3 路可达 FAIL 并还原回绿（`run.sh --self-test-inject` rc=0）。失败原因：无。

**修改文件**（与 `git status -uall` 逐项一致，7 项）：① `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch`（`make_patch chipyard` 重导出：1 written / 20 unchanged，`series` 未变）；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④ `tools/chipyard/fp_ref.py`；⑤ `tools/chipyard/fp_sweep.py`；⑥ `tools/chipyard/fp_unit/unit_run.py`；⑦ 本任务书。`WumingFPUnitHarness` **未改**（无需新断言；hardfloat 参考照旧）。组件源树 HEAD=`c5d592c`（base+1、clean），未提交本仓 git。

**验收结果**（RTL 实测：单元台 Verilator，装载值 → 读回 `outLo/outHi`+`flags`；期望值逐条抄条款，不取自 oracle）：
- `foroot(0x8000…0,2)`/`ftroot(0x8000_0000,2)` ⇒ `0x0`/`0x0`、rf0=0；`±0` 双格式、`RNE/RUP/RDN` 各档同（方向不敏感）
- `ftroot(0xC080_0000)` ⇒ `0x7FC0_0000`+NV；`foroot(0xC010_…0)` ⇒ `0x7FF8_…_0000`+NV
- `ftadd(0x7FC1_2345,1.0)` ⇒ `0x7FC0_0000`；`ftsub(1.0,0xFFC1_2345)` ⇒ 同；`foadd(0xFFF8_…_0123,1.0)`、`fomul(1.0,0x7FF8_…_0123)` ⇒ `0x7FF8_…_0000`；均 rf0=0
- `fo2ft(0xFFF8_…_0123)` ⇒ `0x7FC0_0000`；`ft2fo(0x7FC1_2345)` ⇒ `0x7FF8_…_0000`
- 排除项：`ftscmp(qNaN,1.0)` ⇒ `0x7F80_0001`+NV、`foscmp` ⇒ `0x7FF0_…_0001`+NV；`foqcmp` 无序 ⇒ `0x7FF8_…_0000`、rf0=0；`fomin` 单 NaN ⇒ `0x3FF0_…0`（数）、双 NaN ⇒ `0x7FF8_…_0000`；`ft2ft`/`fo2fo` 带 payload NaN 复制 ⇒ 原样（核上 `cvt_ff` 逐字节）
- 单元台：`TOTAL failed=0`（45 组；sqrt ft/fo 各 3100 向量 hf/oracle-diff=0，sclb 71792×2，rnd 15384×2，`spec points` 20/20 table-diff=0）
- 核上 `fp_sweep`：50/50 组逐字节一致（2118 例；新增 `cvt_nan` 18、扩 `arith_nan`→23、`divrem_nan`→32）；58/58 合法性镜像 cause 命中；273 整数例 md5 `2d4d9465…` == 基线
- 门控：`check-patch-tree` chipyard problem=0（全局 8 条系并行任务 qemu/gem5 脏树）、`check-source-state` chipyard+子模块 OK、`apply-series` 幂等（21 补丁 / 二次无写入 / 树 hash 不变）、`check-component-changelog`·`check-index-blobs`·L2 rc=0；elab+Verilator 重建（抹树后）rc=0、`%Error`=0，镜像新于源码

**新发现/坑**：① `fp_ref.round_exact`/`f2f_exact` 返回 **recoded** 字（比较前须 `fn_from_recfn`），把 canonical NaN 写成 IEEE 字会让 `selfcheck` 立红（本轮实踩 240 处）；② `faults.json` 的判据自 `m12-019` 起不再是「rc≠0/无 POST」（同步故障进 cfx 处理机后继续执行），只能看 hmon `excp cause=0x…`（48 位零填充）；③ Verilator harness 会读 **stdin**，循环读文件时每条 sim 须 `</dev/null`，否则键名被吃掉 9 字节；④ chipyard conda 的 `python3` 是 3.10（无 `tomllib`），不能进全局 `PATH`，否则仓库 `make` 门控全红（只包住 sbt/verilator/make verilog）；⑤ hardfloat `DivSqrtRecFN_small` 实为 `squareRoot`（`sqrt(−0)=−0`），`rootn(±0,2)=+0` 是与 hardfloat 唯一有意的值差异；⑥ `fp_ref.sclb_exact` 原对 qNaN 返回原 payload（与 §1.4 矛盾），本轮一并收口。

**遗留问题**：无。QEMU/gem5 与 `tests/inst` 向量的同步按任务书非范围，归 `m13-integ-010`/`m13-testcases-032`（`QEMU_GROUPS` 注释已写明差异面）。
