# m13-qemu-009: `rootn(±0,2) ⇒ +0` 与结果 NaN 统一 canonical

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-007`（口径定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

**预估**：2–3 h

## 用户裁定（2026-11-13，落盘 `.tao/knowledge/discussing.md`）

1. **R1**：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
2. **R2**：结果 NaN 统一 **canonical quiet NaN**（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。审计依据见 `docs/TestReports/M13-FP-IEEE对齐审计.md` §D2 / §D3。

## 背景（现状现场）

- `components/qemu/patches/target/dadao/helper.c.patch` 的 `helper_fp_root()`（`foroot`/`ftroot`，`immu6 = 2`）直接调 `float64_sqrt` / `float32_sqrt`：`sqrt(−0) = −0` ⇒ `foroot(−0,2) = 0x8000_0000_0000_0000`（应为 `+0`）。
- 同文件 `fp_status_init()` 现设 `set_float_2nan_prop_rule(float_2nan_prop_ab, st)`，注释自陈「We match the current host（x86_64 SSE）」⇒ 算术/scaleB/取余/开方把**首个 NaN 的 payload 与其符号**传播出去（例：`forem(qNaN=0x7FF8_0000_0000_0123, 2.0) = 0x7FF8_0000_0000_0123`；`ftadd(0x7FC12345,1.0)` 得 `0x7FC12345`）。
- 对比：`roundint` / `minmax` / `fma` 三个 helper 已各自 `set_default_nan_mode(1, &st)`（canonical）。
- softfloat 侧事实（`fpu/softfloat-parts.c.inc`）：`partsN(pick_nan)` 与 `partsN(return_nan)` 在 `get_default_nan_mode(s)` 为真时**短路**返回 `default_nan`（早于 2-NaN 规则分派）；`set_float_default_nan_pattern(0b01000000, st)` 已把默认 NaN 设为 canonical ⇒ **在 `fp_status_init()` 置 `set_default_nan_mode(1, &st)` 即可让全部软浮点路径产出 canonical qNaN**，且不再依赖 2-NaN 规则（原 `g_assert_not_reached` 路径不会到达）。

## 范围（只改 QEMU 组件）

1. **R1**：`helper_fp_root()`（sqrt 分支）——源为 `+0`/`−0` 时结果 `+0`（符号位清 0），不置任何标志；`±Inf`、负有效数（`NV` + canonical qNaN）、有限正数行为不变。
2. **R2**：在 `fp_status_init()` 置 `set_default_nan_mode(1, &st)`，使全部 qNaN 结果为 canonical；随之 `float_2nan_prop_ab` 的规则与其「match host」注释的前提作废——保留或删除规则由 engineer 实测决定（**判据**：删后不得出现 `g_assert_not_reached` / softfloat abort；保持 `set_float_default_nan_pattern` 不变）。`roundint`/`minmax`/`fma` 中既有的 per-op `set_default_nan_mode(1,&st)` 变冗余，最小改动可保留，须在完成区披露。
3. `components/qemu/changelog.md` 记一条。
4. 不得顺带改其它标志路径（`NV`/`DZ`/`OF`/`UF`/`NX`）与舍入逻辑。

**非范围**：不改 `tests/inst/**`（既有 pin「传播 payload」的期望由 `m13-testcases-032` 改）、不改 spec/合约、不改 chipyard/gem5。

## 验收标准（可执行、可失败）

1. **R1 逐例**（改后安装根，`rd5` = `rf2rd` 读回、`rd6` = FCSR）：
   - `foroot(−0, 2)` ⇒ `0x0000_0000_0000_0000`、`rd6[4:0] = 0`
   - `ftroot(−0, 2)` ⇒ 低 32 位 `0x0000_0000`（符号 0；高 32 位按该例装载值）
   - `foroot(+0, 2)` / `ftroot(+0, 2)` ⇒ `+0`、无标志（回归）
   - `foroot(−4.0, 2)` ⇒ canonical qNaN `0x7FF8_0000_0000_0000` + `NV`（回归，值不变）
2. **R2 逐例**（改后安装根）：
   - `ftadd(0x7FC1_2345, 1.0)` ⇒ `0x7FC0_0000`；`foadd(fo qNaN 带 payload 且**负号**, 1.0)` ⇒ `0x7FF8_0000_0000_0000`（符号清 0）
   - `ftsclb(qNaN 带 payload, 3)` ⇒ `0x7FC0_0000`
   - `fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`（符号 0、payload 0）；`ft2fo(qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`
   - `forem(0x7FF8_0000_0000_0123, 2.0)` ⇒ `0x7FF8_0000_0000_0000`、无标志
   - `ftadd(sNaN, 1.0)` ⇒ canonical qNaN + `NV`（回归）
   - **排除项对照（必须保持不变）**：`ft2ft`/`fo2fo` 复制带 payload NaN ⇒ 位型原样搬移；`foscmp(qNaN,1.0)` ⇒ `0x7F80_0001` 且 `NV=1`
3. **`make check-inst` 的红集必须是「既有 pin 非 canonical NaN 的期望」且可穷举**：施工前用 `grep` 现场枚举 `tests/inst/fp/*.yaml` 中结果为非 canonical qNaN（payload≠0 或符号 1）的期望项（例：`divrem.yaml` 的 `forem` qNaN 传播 case `rd5=0x7FF8_0000_0000_0123`），逐条列在完成区；改后 `check-inst` 的 FAIL 集**必须恰等于该清单**（不得有其它红），并注明由 `m13-testcases-032` 收口回绿。若出现清单外红 ⇒ 判本任务缺陷。
4. `check-patch-tree`（qemu 子集 problem=0）、`check-component-changelog` rc=0；`check-source-state` rc=0。
5. **可达 FAIL 注入（≥2 路）**：① 去掉 `set_default_nan_mode(1,&st)` ⇒ canonical 例红（且 `check-inst` 红集扩大）；② 去掉 root 的零符号修正 ⇒ `foroot(−0,2)` 回 `0x8000…` 红。均 `cp`+md5+`touch` 还原 ⇒ 回绿。
6. **安装根一致性**（`ISS-373` 并发坑）：测量前后各断言 `md5(构建树二进制) == md5(安装根二进制)`，末尾必须再跑一次 `make install-host` 收口；注入整段建议用 gate lock 包住。
7. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`.work` 须软链（`ISS-389`）、`JOBS=8`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数从脚本现场输出直接抄（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）；补丁改动走 `make_patch` 导出。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 待裁定（交主会话）

1. **任务书 #5① 的括号预期与实测相反**：括号写「去掉 `set_default_nan_mode(1,&st)` ⇒ canonical 例红（且 `check-inst` 红集扩大）」；实测 canonical 例确实红（20 例），但 `check-inst` 红集从 `{divrem.yaml[23]}` 缩为**空**——该唯一既有 pin 期望的正是旧「payload 传播」行为，关掉 canonical 后它回绿。硬判据 #3（红集 == 现场枚举清单）仍成立。
   - 方案 A（本任务自决、已实现）：按实测记录，硬判据不变；`#5①` 的括号视为任务书笔误——`m13-testcases-032` 把 pin 改成 canonical 之后，同样的注入自然会「红集扩大」。
   - 方案 B：本任务补一种「注入后红集扩大」的构造（先把某条 `tests/inst` 期望改 canonical 再注入）——会动 `tests/inst`，越出本任务范围。
   - 建议：A；只需在任务书层面确认该括号为笔误，不改实现。
   - **主会话裁定（2026-11-13）：采方案 A**（`#5①` 括号为笔误，硬判据不变，不返工）。

## 完成区

**测试结果**：一键证据脚本 `run.sh` → **PASS=80 FAIL=0**、rc=0（含两次注入自检）；验收逐条如下。
**修改文件**：`components/qemu/patches/target/dadao/helper.c.patch`（源树改 → `make_patch.py qemu`：1 written / 65 unchanged）、`components/qemu/changelog.md`（M13 一条）、本任务书；与 `git status --porcelain -uall` 三条**逐条一致**。组件源树 `target/dadao/helper.c` 已收敛为 base+1 且干净（不入本仓库）。
**验收结果**：
1. **R1 逐例（改后安装根）**：`foroot(−0,2)`=`0x0000_0000_0000_0000`、rd6[4:0]=`0x00`；`ftroot(−0,2)` 低 32 位 `0x0000_0000`、`0x00`；`foroot/ftroot(+0,2)`=`+0` 且无标志（回归）；`foroot(−4.0,2)`=`0x7FF8_0000_0000_0000`+NV（回归）；另加 `foroot/ftroot(4.0,2)`=2.0/无标志。
2. **R2 逐例（改后安装根）**：`ftadd(0x7FC1_2345,1.0)`=`0x7FC0_0000`；`foadd(0xFFF8…0123,1.0)`=`0x7FF8_0000_0000_0000`（符号清 0）；`ftsclb`/`fosclb`/`fo2ft(0xFFF8…0123)`/`ft2fo`/`forem`/`fodiv`/`foroot` 均 canonical；`ftadd`/`foadd`/`ftroot`/`forem`(sNaN)=canonical+NV；`forem(qNaN,+0.0)`、`fodiv(负 qNaN,+0.0)` canonical 且不置 NV/DZ。**排除项不变**：`ft2ft`/`fo2fo` 带 payload NaN 位型原样、`foscmp(qNaN,1.0)`=`0x7FF0_0000_0000_0001`+NV、单 NaN `fomin` 返回数（sNaN 仍 NV）。命令：向量批跑 rc=0（`38 total, 38 passed`）；逐例 dump 对比 `total=38 bad=0`。
3. **`check-inst` 红集 == 既有非 canonical 期望清单**：现场穷举 `tests/inst/**/*.yaml` 的 `rd5` 非 canonical qNaN ⇒ **命中 1 条 = `divrem.yaml[23]`（`forem`，`0x7FF8_0000_0000_0123`）**；`make check-inst` **rc=2**，Vast `1141 total / 1135 passed / 1 failed / 5 deferred / 0 errors`（Tiny 段因 Vast 先失败未跑），红集 = `divrem.yaml[23]`，**与清单逐条相等、无清单外红**；由 `m13-testcases-032` 收口。`check-inst-smoke` rc=0。
4. **门控**：`check-patch-tree` **qemu 子集 problem=0**（整树现场 9 条全在 gem5(6)/chipyard(3)，系其并行任务的在飞未导出改动/脏树，与本任务无关）；`check-component-changelog` rc=0；`check-source-state` 的 **qemu OK**（HEAD `f2d3eb2`、base+1、clean），整树 rc=1 仅因 chipyard 脏树（非本任务）。
5. **可达 FAIL（2 路）**：① 去 `set_default_nan_mode(1,&st)` ⇒ 20 例 canonical 红（`8–23 27–30`）、`check-inst` 红集变空；② 去 root 零短路 ⇒ 恰 `0 1` 两例红、`check-inst` 红集不变。均 `cp`+md5+`touch` 还原 ⇒ 二进制 md5 回 `389ffb96…`、38/38 回绿。
6. **安装根一致性（ISS-373）**：首、末两次 `make install-host` rc=0，各断言 md5(构建树)==md5(安装根)==`389ffb96…`；旧二进制以 md5 `b366e491…` 钉住作前置对照（红集恰为声明的 22 例 `0 1 8–23 27–30`）。
7. **脚本与对账**：`run.sh` rc=0；完成区 ≤30 行、无运行期路径；`JOBS=32`（`free -g` 可用 119 GiB，未降档）。
**新发现/坑**：① 任务书 #5① 括号「（且 `check-inst` 红集扩大）」实测**相反**：既有唯一非 canonical pin 就是旧行为，关掉 canonical 反而让它回绿、红集缩空（红集扩大只在 `m13-testcases-032` 改 pin 后成立，见「待裁定」）。② `fo2ft` 的 sNaN 只有**负号或高位 payload** 才暴露旧行为（softfloat 转换截掉低位 payload）⇒ 反例用例须用 `0xFFF0_0000_0000_0123`。③ 2-NaN 传播规则保留为兜底：删掉后一旦 default-NaN 被关（注入 A 即如此）会命中 `partsN(pick_nan)` 的 `g_assert_not_reached`，反例变成 abort 而非可判读红集。④ `rd6` 是整条 FCSR（高位形似 fo qNaN），枚举非 canonical pin 只能扫 `rd5`，否则误报 100+ 条。⑤ 整树门控的红随并行任务的在飞改动漂移（本轮 `check-patch-tree` 由 8 变 9 条、`check-source-state` 由 rc=0 变 rc=1），判据须取 qemu 子集而非整树 rc。
**遗留问题**：`check-inst` 余 1 红（`divrem.yaml[23]`，既有 payload 传播 pin）由 `m13-testcases-032` 收口；整树 `check-source-state`/`check-patch-tree` 的红属 gem5/chipyard 并行任务在飞，待其收尾后转绿；其余无。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`target/dadao/helper.c` 两处改动全 diff、导出补丁、changelog 条目、证据脚本（`run.sh` + 向量生成/枚举/编码读回三支脚本）。

- R1 零判定：fo 用 `x & 0x7FFF_FFFF_FFFF_FFFF`、ft 用 `(uint32_t)x & 0x7FFF_FFFF` —— 覆盖 ±0，不误伤最小次正规（其量值非 0）；提前返回 `0` 与既有 `(uint64_t)(uint32_t)` 的零扩展形状一致；±0 本不置标志（IEEE 754-2019 §9.2），故跳过 `fp_status_init/commit` 不改变 rf0。
- R2 摆放：`set_default_nan_mode(1, st)` 放在 `set_float_default_nan_pattern(0b01000000)` **之后**（default_nan 取该 pattern ⇒ canonical）；sNaN 的 NV 在 `return_nan`/`pick_nan`/`pick_nan_muladd` 短路**之前** raise ⇒ sNaN 仍置 NV（4 例实测）。
- 排除项不经该路径：`ft2ft`/`fo2fo` 是 TCG 位搬移、比较族是 TCG 内联常量、`min/max` 单 NaN 返回数 —— 3 例实测不变。
- 未改：舍入模式、`NV/DZ/OF/UF/NX` 路径、`set_float_default_nan_pattern`；`roundint/minmax/fma` 的 per-op `set_default_nan_mode(1,&st)` 变冗余但保留（最小改动，已在完成区披露）。
- 证据脚本：无 `| tee` 吞码（逐条捕 rc）；注入还原用 `cp`+md5+`touch`（未用 git 还原）；向量/名单/计数现场派生（不写死）；红集与逐例断言均有可达 FAIL 路径（两次注入各走一条不同失败路径）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 初版删掉 2-NaN 规则 ⇒ 注入 A 会 abort 而非产出可判读红集 | ✅已修 | 保留规则，注释改述为「default-NaN 关闭时的兜底（ISS-195）」 | 注入 A 得 20 例红，无 abort |
| F2 初版 `fo2ft` sNaN 用正号/低位 payload ⇒ 旧二进制同样是 canonical，该例不可失败 | ✅已修 | 输入改 `0xFFF0_0000_0000_0123` | 旧二进制该例红（红集含 30） |
| F3 初版 `fomin` 单 NaN 期望「返回该 NaN」，与 spec「返回那个数」相反 | ✅已修 | 期望改 `1.0`；sNaN 例补 NV | 38/38 绿（`[36]`/`[37]`） |
| F4 初版比较类用例的结果被随后 `rf2rd rd5` 回读覆盖（rd5 恒 0） | ✅已修 | 比较类标 `direct`，不回读 rf4 | `[24]`/`[35]` 绿 |
| F5 `rd6` 被当成 fo qNaN 分类（初版枚举 115 条噪声） | ✅已修 | 只扫 `rd5`；signaling-compare 的 sNaN 结果按 spec 排除 | 枚举 = 1 条，与 `check-inst` 红集逐条相等 |

判决：无未修 finding ⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-13，全部由 reviewer 亲自重跑；轮次与 engineer 自审连续编号）

**重跑记录（真实输出/退出码）**
- `bash <运行期证据目录>/run.sh` ×3：基线 `PASS=80 FAIL=0, RUN1_EXIT=0`；注入 run `PASS=45 FAIL=35, RUN2_EXIT=1`；还原后回绿 `PASS=80 FAIL=0, RUN3_EXIT=0`。
- 向量批跑（安装根 38 例）`rc=0`：`38 total, 38 passed`；改前二进制（md5 `b366e491…`）`rc=1`：`16 passed, 22 failed`，红集=声明的 `0 1 8–23 27–30`（run.sh 内 `PASS pre-change red set == declared`）。
- `JOBS=32 make check-inst`：`rc=2`，Vast `1141 total / 1135 passed / 1 failed / 5 deferred`，红集恰 `divrem.yaml[23]`（Tiny 段未跑）；`make check-inst-smoke` `rc=0` PASS。
- **独立红集枚举**（reviewer 自写扫描：tests/inst 全 yaml 的 `expected_state.rd5`、fp 结果族白名单、排除位搬移/信号比较/符号注入、rd6=FCSR 不扫）：**恰 1 条 = `divrem.yaml:714`（0-based 23）**，与 check-inst 红集逐条相等、无清单外红；该红由 `m13-testcases-032` 收口，不判本任务失败。
- `python3 tools/infra/check_patch_tree.py --source-state` `rc=0`（`qemu: OK HEAD=f2d3eb2 count=1 clean=True`）；`check_patch_tree.py` `rc=1`、8 problems 全在 gem5(6)/chipyard(2)、**qemu 段 0**（并行任务在飞，非本任务）；`make check-component-changelog` `rc=0`（`PASS, 32 项`）。
- **独立语义探针（自建 8 例，不用 engineer 向量）**：payload 自选 `0xFFD23456`/`0xFFF8ABCDEF012345`，指令字现场 `llvm-mc --show-encoding` 编码。改后安装根 **8/8 `rc=0`**；改前二进制 **6 红 = P0–P5**（`foroot/ftroot(−0,2)` 符号位 0、`ftadd/fo2ft/forem/ftsclb` 负号+payload qNaN ⇒ canonical）且 **P6 `ft2ft` 位搬移 / P7 `foscmp`（sNaN+NV）两支绿** ⇒ 排除项不受影响、探针可达 FAIL。
- **独立注入（自设计，非 run.sh 内部 A/B）**：`set_float_default_nan_pattern(0b01000000→0b01111111)`（锚点与 A/B 不重叠）⇒ `run.sh rc=1`、35 FAIL：spec 表红集 `4 5 8–23 25–30`、`check-inst` 红集扩为 15 条、`check-patch-tree qemu-subset=2`、`source-state rc=1`、E1 脏树；`cp`+md5 还原（`ad0a66d1…` 相等、marker 消失、源树干净）⇒ 回绿 `rc=0`。全程未用 `git checkout/restore/stash`。
- 安装根一致性：基线/回绿 run 首末 `make install-host rc=0`，`md5(构建树)==md5(安装根)==389ffb969e503f291f8e1b7c718392d8`。
- **终态复核（本轮落盘前再跑一遍）**：38 例批跑 `rc=0`（`38 total, 38 passed`）；`make check-inst` `rc=2`、红集仍恰 `divrem.yaml[23]`（独立枚举 `divrem.yaml:714` count=1，逐条相等）；`--source-state` `rc=0`（qemu OK）；`check-component-changelog` `PASS rc=0`；探针改后 `8/8 rc=0`、改前二进制 `6 红 rc=1`；安装根==构建树 `389ffb96…`。

**约束核验**：① 改动仅 3 文件（补丁/changelog/任务书，`git diff HEAD~1 HEAD --name-only` 三行），未碰 chipyard/gem5/tests/spec/contracts；② 验收前后 `git status -uall` 均空、三文件 md5 与快照逐一相等；组件源树 base+1 clean；③ 完成区 12 行 ≤30、无具体 `.work/**`/宿主运行期路径（仅 `<>` 模板形）；④ changelog 一条、证据脚本可达 FAIL（run.sh 两路内部注入 + 我的独立注入均真红）；⑤ spec 语义逐条对过 `SimRISC-07 §1.4/§2.2/§4`、`contract-fp.md §1`（rootn ±0=+0、结果 NaN canonical、位搬移/信号比较/单 NaN 三类排除），实现与 spec 一致。

**发现（非阻断，记档）**：① `run.sh` 头注释写「34 vectors / 18 canonical」，实际 38/20（断言全取现场值，仅注释过期）；② 任务书 #5① 括号「（且 check-inst 红集扩大）」与实测相反——我复跑确认注入 A 后红集**缩为空**（`inject-A check-inst red set: []`），engineer 已按实测落「待裁定」且硬判据 #3 未变 ⇒ **建议采方案 A（括号为笔误）**，由用户/架构师裁定，不作返工理由。

**判决：Accepted** —— 验收标准 1–7 在 reviewer 自己的重跑下全部通过；唯一红 `divrem.yaml[23]` 是既有 payload 传播 pin（任务书明示由 `m13-testcases-032` 收口），不判本任务失败。
