# m12-chipyard-029: 融合乘加溢出按 IEEE 舍入模式（RTL + 模型）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-spec-006`（spec 定稿）
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-399`）

`fofma`/`ftfma` 溢出当前恒 ±Inf；`spec-006` 定稿后须按舍入模式分派，并区分严重/轻微溢出（后者只置 `NX`）。

## 验收

四档 × 正负（含轻微溢出）实测；与 QEMU/gem5 逐字节；`fo2ft ovf` 那套 40 例的判据可复用；注入可达 FAIL；L2 rc=0。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：逐行读 6 个改动文件的 `git diff`；改前先用**未改动**的 RTL 做 96 格预探（确认前提），改后重建单元台与整核各跑一轮；3 路注入。核心事实：RTL 与模型**本已合规** —— 溢出由共享舍入原语按 `rf0[33:32]` 分派，本族从未有 `forceInfOnOverflow`（该覆写只存在于 `fo2ft`，`m12-chipyard-026` 已删）；`ISS-399` 的 chipyard 侧「未知」实测为**无需改行为**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务前提「溢出恒 ±Inf」与实测不符：未改动 RTL 的 96 格预探即与条款一致 | ❌不修（实测本就合规） | 只在 `WumingMulAddRecFN` 补条款注释（分派 + 轻微只置 `NX` + 禁止再添 Inf 覆写），舍入逻辑一行未动 | 改后重建：`fma ovf` 96 格 table/hf-value/hf-flag/oracle=0；注入① 可达 FAIL（table-diff=16） |
| F2 单元台首版按 `zip(names, row)` 解 3 元组 ⇒ `ValueError` | ✅已修 | 打印行改为逐项解 `(mode, value, flags)` | `unit_run --n 20` rc=0；`fma ovf: 96 vectors | table-diff=0` |
| F3 期望表写在 `check()` 内，证据脚本无法独立复用（模型核对不该读 RTL） | ✅已修 | 常量与 24 行表移到模块级，`check()` 只留检查逻辑 | 证据 B 段 `import unit_run.FMA_OVF_ROWS` 核模型，192 格 mismatch=0 |
| F4 `check-patch-tree` 断言数到 `chipyard: 21 patch(es)` 汇总行 ⇒ 干净也 FAIL | ✅已修（只收窄） | 断言改为「chipyard 的 `assertion` 行数 = 0」，patch 数单列 | 现场 `assertion=0`、`21 patch(es)` |
| F5 README 插入时误把 030 节标题与其首条 bullet 拼成一行 | ✅已修 | 恢复 030 标题 + 首条 bullet | `check-component-changelog` rc=0 |
| F6 证据脚本「sweep triples」断言实际数的是 case 数（92），标签不符 | ✅已修 | 改为现场 `grep -c '^    ("ovf_'`（12） | A 段 PASS 12 |
| F7 整仓 `check-patch-tree` rc=1：gem5 源树被并行任务改脏（`isa.hh`/`timing.cc` 与补丁不一致） | ⏸范围外 | 未动 gem5 | 证据 E：chipyard `assertion`=0、`--source-state` chipyard(+testchipip) OK |

**判决**：F2–F6 已修并复验；F1 为「按实测不改行为」的结论项（附防回退注释）；F7 属并行任务/范围外登记。状态 → `待验收`。

### 第 2 轮 engineer 自审（组件树污染 → 恢复后复跑）

**背景**：首轮全绿后（A–E 段 68/68 ⇒ EXIT=0），共享 `.work/source/chipyard` 于 00:21 被并行任务 `m12-chipyard-028` 改写 `bootrom.tiny.hex`（同组件双写者），使 E 段两项对该**非本任务文件**报红；主会话已把该文件恢复（md5 `797fe3f6…`）、组件 commit `amend` 为 `b7c72e6`（只含本任务 `WumingFP.scala` 改动）并重导出补丁集。本轮据此复跑。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 E 段两项红（chipyard assertion 2 条 / apply-series 树不一致）全部来自 `bootrom.tiny.hex`（028 在途改写，非本任务文件） | ✅已闭环 | 未改判据；组件树恢复后整核强制重建复跑 | 全量 `run.sh` ⇒ **EXIT=0（74/74 PASS）**；`chipyard assertion lines: total=0 own=0`；`this task's changed RTL reproduces`=0、`inherited-path drift: 0`、21 补丁二次 0 应用 |
| R2 E 段判据把「本任务责任」收到本次改动的 RTL，其余 20 条继承补丁的漂移只披露、不判分（同组件并行任务不得把整段拖红） | ✅已修（收窄，非放宽） | `check-patch-tree` 断言改为「命中 `WumingFP.scala` 的 assertion 行 = 0」；`apply-series` 逐路径核对并单列 `[INHERITED-DRIFT]` | 污染态下能直接定位到外部文件；恢复后 `total=0` |

**判决**：R1 闭环（失败项已转绿）、R2 为诊断性收窄；RTL 实测表与完成区数字不受影响（FMA 语义与 bootrom 无关）。状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**重跑（全部本人执行，退出码为实测）**：① `bash .work/evidence/m12-chipyard-029/run.sh`（整核强制重建）⇒ `summary: PASS=74 FAIL=0`、**EXIT=0**，A18/B5/C11/D20/E15/F5 与完成区逐条同数；`fma ovf` 96 例 table/hf-value/hf-flag/oracle 全 0，`fma ft`/`fma fo` 各 5370 例 `TOTAL failed=0`，核上溢出 48+48 mismatch=0，273 例 md5 `2d4d9465…`，`L2 rc=0`。② `run.sh --inject` ⇒ **EXIT=0**：RTL「恒 ±Inf」table-diff=16、「轻微也置 OF」table-diff=32、模型注入 oracle-diff=16，三路 `cp`+md5 还原回绿（源码 md5 `f6fc716a…`，`.inj-bak` 0 残留）。③ 独立门控：`check-component-changelog` rc=0、`check-index-blobs` rc=0、`check-patch-tree` rc=2（36 条 assertion 全在 gem/linux/llvm-project/qemu，**chipyard 0 条**）、`make_patch chipyard` = `0 written, 21 unchanged`（补丁 md5 前后零差异）。
**独立实测（自写 `indep.py`：`Fraction` 按 §2.5 推导期望，不 import `fp_ref`/`FMA_OVF_ROWS`，先断言 24 个操作数形状成立）**：216 格 mismatch=**0**、EXIT=0 —— 单元台用**我自己的向量文件**驱动同一 Verilator 二进制 96 格（ft/fo × 严重/轻微/中点/中点下/恰 max/精确 2^128·2^1024 × 双符号 × RNE/RTZ/RDN/RUP）+ 整核 dump 48+48 格（`rd` 全等、`rf0[4:0]` 全等、`rf0[33:32]` 逐例 == 所选档）。
**独立注入（自设计 2 路，`cp`+md5 还原）**：① 改期望表 `ft/pos_sev` RTZ 期望 `max→Inf` ⇒ `unit_run` **EXIT=1**、`table-diff=1`、`TOTAL failed=1`、只红该格（hf/oracle 差仍 0）；还原 md5 `af0ab45a…` ⇒ EXIT=0。② 改 `fp_ref.fma_exact` 溢出恒 `±Inf` ⇒ `ONLY=D SKIP_CORE_BUILD=1` **EXIT=1**（`arith_fma_ft/fo bytes=diff`、溢出格 8+8 mismatch、6 FAIL）；还原 md5 `3ddc73e3…` ⇒ EXIT=0（50/50 组绿）。
**非同源自比**：期望表 = 条款逐格抄写（我按 §2.5 表逐格手算复核 24×4 全对）；`fp_ref` 为 Python 精确有理数模型（与 hardfloat/RTL 不同语言不同推导）；hardfloat 与 RTL 同源，仅作第三参照。
**「RTL 本就合规」成立**：结构上 `WumingMulAddRecFN` 只把 `sExp/sig/roundingMode` 交给共享原语，溢出由 `common_overflow`/`overflow_roundMagUp`/`pegMaxFiniteMagOut` 按 `rf0[33:32]` 分派（无 Inf 覆写）；史上 `forceInfOnOverflow` 只在转换族（`git log -S` 仅 012 引入 / 026 删除，命中 `WumingF2F`/`INToRecFN`/`FPConvert`，未触及本族；HEAD~1 与 HEAD 补丁各 0 处）；实测 216 格独立推导全同 ⇒ 交付 = 证据 + 防回退注释 + 可复跑用例，不需改 RTL。
**约束核验**：worktree 根自证 ✓；我与 engineer 均未 commit（HEAD 仍 `045ea55e` WIP）✓；改动 7 文件 == 完成区「修改文件」+任务书，无越界（未碰 spec/contracts/tests/QEMU/gem5/Makefile）✓；完成区 23 行、两轮审阅记录各 ≤40 行 ✓；任务书无违规运行期路径（仅豁免形 `.work/source`）✓；前后 `git status` 快照逐行相同、目标文件 md5 一致 ✓。
**非阻断 finding（交 architect）**：① E 段断言 `grep -qE '^check-patch-tree: [a-z]'` 会命中 chipyard 自身行 ⇒ 该条实际恒真，建议改为「chipyard assertion total=0」/「红组件集合不含 chipyard」；本任务责任已由 `own=0` 覆盖（我独立跑实测 36 条红全在他组件）。② 本分支 L1 `make check` rc=2 = `check-spec-drift`（contract-syscall 0.10.0 ≠ README 0.9.2）：基线 `72006e53` 早于 master 修复 `48a7016e`/`1e40da19`（非 HEAD 祖先，master 同检查 rc=0），本任务 diff 不含 contracts/spec ⇒ 合入后复跑 L1。③ 验收词「与 gem5 逐字节」：QEMU 两图已逐字节（F 段复跑 PASS）；本任务镜像 gem5 无 runner（已披露），我补跑 `tools/gem5/check_b7.py` rc=0（fma 240 向量、0 disagreement）作侧面证据，措辞取舍归 architect。
**判决**：**Accepted**（验收命令块在本人重跑下全绿、无约束违反、注入可达 FAIL 且已还原回绿）。

## 完成区

**测试结果**：一键证据脚本（整核强制重建）⇒ **EXIT=0**（74/74 PASS：A 18、B 5、C 11、D 20、E 15、F 5）；`--inject` ⇒ **EXIT=0**：RTL「溢出恒 ±Inf」⇒ `fma ovf` table-diff=16、RTL「轻微溢出也置 `OF`」⇒ table-diff=32、模型「溢出恒 ±Inf」⇒ oracle-diff=16；三路 `cp`+md5 还原（源码 md5 `f6fc716a…`）后重建回绿。组件树污染已恢复（`b7c72e6`），两处原红项已转绿（`chipyard assertion total=0`；`apply-series` 21 路径逐字节 + 二次 0 应用）。

**RTL 实测（`ftfma`/`fofma` 各 96 格 = 12 形状 × 双符号 × 四档；单元台与整核逐字节一致，`max`/`Inf` 按格式取）**：
- 严重溢出（`max×2`、精确 `2^128`/`2^1024`）：RNE `±Inf`、RTZ `±max`、RDN 正 `+max`/负 `−Inf`、RUP 正 `+Inf`/负 `−max`，均 `OF|NX`（`0x14`）
- 轻微溢出（`max` 上方 1/4 ulp、中点下方）：RNE/RTZ/正向 RDN/负向 RUP ⇒ `±max` **仅 `NX`**（`0x10`）；正向 RUP / 负向 RDN ⇒ `±Inf`+`OF|NX`
- RNE 中点（`max+ulp/2`，ft `2^103`/fo `2^970`）：RNE/RUP ⇒ `±Inf`+`OF|NX`；RTZ、正向 RDN、负向 RUP ⇒ `±max` 仅 `NX`
- 恰为 `max`：四档 `±max`/`0x00`；整核 `rf0[33:32]` = 00/01/10/11 与所选档逐例对应
- 模型 `fp_ref.fma_exact` 与上述 96 格逐格相同（B 段 192 条断言 mismatch=0），核上 `rd`+`rf0` 与模型逐字节（48+48 格）

**修改文件**（`git status -uall` = 6 modified / 0 untracked，另本任务书）：
- `components/chipyard/patches/.../WumingFP.scala.patch`：源树 `WumingMulAddRecFN` 增 §2.5 溢出条款注释（**行为未改**，实测本就合规）
- `tools/chipyard/fp_unit/unit_run.py`：模块级 `FMA_OVF_ROWS`（24 行，期望值逐格抄条款）+ `fma ovf` 检查组 96 例（表/hardfloat/模型四方对照）
- `tools/chipyard/fp_sweep.py`：`FMA_OVF_TRIPLES`（12 形状），`arith_fma_ft`/`arith_fma_fo` 各增 48 例（92/格式）
- `tools/chipyard/fp_ref.py`：`fma_exact` 文档注明方向规则与轻微溢出口径（无行为改动）
- `components/chipyard/{README.md,changelog.md}`：新增本节与条目

**验收结果**：单元台 `fma ovf` 96 例四差 0、`fma ft`/`fma fo` 各 **5370** 例 oracle/hf 0 差、`TOTAL failed=0`；整核 `arith_fma_*` 92 例/格式逐字节、溢出 48+48 格 mismatch 0；QEMU 同镜像逐字节（两图，仅补充、不用于推定 RTL）；elab/Verilator rc=0 且 `%Error`=0、镜像晚于 FP 源；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-source-state` chipyard(+testchipip) OK、`check-component-changelog`/`check-index-blobs`/L2 rc=0、`check-patch-tree` chipyard `assertion` 0 条、apply-series 21 补丁幂等（二次 0 应用、树不变）、`make_patch` 复跑 `0 written, 21 unchanged`。

**新发现/坑**：① 本任务前提不成立 —— 融加溢出一直由共享舍入原语按 `rf0[33:32]` 决定，`forceInfOnOverflow` 从未出现在本族；`ISS-399` chipyard 侧「未知」实测为无需改动，交付物 = 证据 + 防回退注释 + 可复跑用例；② 轻微溢出必须是「无界指数按方向舍入后再比 `max`」，与「精确值 > `max`」不等价（后者会把 RTZ 的 `NX`-only 格误判为 `OF`）；③ 期望表须放模块级，模型核对才不依赖 RTL；④ 同组件并行任务会改写共享源树（本任务期间 `bootrom.tiny.hex` 曾被他任务改写）⇒ 证据脚本把 E 段判据收到「本任务改动文件」，其余继承路径漂移只披露并逐条打印。

**遗留问题**：整仓 `check-patch-tree` 在其它组件被并行任务改脏时仍 rc≠0（本任务范围外；chipyard 段 0 assertion）；QEMU 仅作同镜像逐字节补充、gem5 无本族 runner 未参与，均未用于推定 RTL。
