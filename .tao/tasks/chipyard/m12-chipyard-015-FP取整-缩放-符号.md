# m12-chipyard-015: FP 取整/缩放/符号

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-014`（已合入）+ `026`（补丁落盘修复，已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

012 已完成除/开方/余；剩余 FP 零碎指令。

## 目标

1. **取整**：`fornd`（roundToIntegral，六档舍入）。
2. **缩放**：`fosclb`/`ftsclb`（第三操作数为 `rd` 组的有符号 64 位整数指数，`rdHD=rd0` 表示指数 0）。
3. **符号操作**：`fosgnj`（及同族）。
4. 至此 **FP 47 条指令**全部落地（`spec/SimRISC-07`）。

## 验收标准

1. FP 47 条指令在 `tests/inst` 中全部有覆盖且与 QEMU 一致
2. `fosclb` 的 `rd` 第三操作数（含 `rd0`）有专门断言
3. `fornd` 六档舍入全覆盖
4. Verilator 构建 rc=0（主控机）；门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

T0/T1 冒烟（`014`/`015`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-013/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

## 完成区

**测试结果**：一键证据 `PASS=190 FAIL=0`（`FINAL_EXIT=0`；A 结构/B 模型自检+双 oracle 互证/C 构建/D 单元台/E 273 回归/F 新 YAML 核上+QEMU/G 11 组 sweep 核上+QEMU/H 周期/I 门控）；注入自检 `INJECT_EXIT=0`（① `roundUp:=false` ⇒ D 的 rnd ft 734 / fo 713 差；② 去 scaleB 指数偏移 ⇒ sclb hf-value-diff 12203/14644；③ 模型静态档恒置 NX ⇒ G 的 rnd_ft/fo 红；三次 `cp`+md5 还原（`25a8fb93…`/`d4e80c60…`）复跑回绿）。
**修改文件**（== 任务 worktree `git status -uall`，15 项 = 13 改 + 2 新）：4 个 `components/chipyard/patches/.../{WumingFP,WumingCore,WumingDecoder,WumingFPUnitHarness}.scala.patch`（`make_patch` 重导出，`series` 不变）、`components/chipyard/{README.md,changelog.md}`、`tools/chipyard/{fp_ref.py,fp_sweep.py,fp_unit/unit_run.py}`、`tests/inst/fp/{roundint.yaml(新 46 例),sign.yaml(新 28 例),scaleb.yaml(+fosclb rd0)}`、`tests/inst/inventory.md`（门控表 +2 行）、`tests/case-ledger.tsv`（`--write`，2170 条）、本任务书。
**验收结果**：
1. **六档舍入**（46+115+128 例，核==QEMU）：`+0.5`⇒RNE`+0`/RNA`1`/RTZ`+0`/RUP`1`/RDN`+0`；`−0.5`⇒RNE`−0`/RNA`−1`/RTZ`−0`/RUP`−0`/RDN`−1`（`±0` 保留输入符号）；`±1.5`⇒就近`±2`、RTZ`±1`、RUP(−)`−1`、RDN(+)`1`；`−2.5`⇒RNE`−2`/RNA·RDN`−3`；次正规（`minsub/maxsub`）⇒`±0`（RUP 正/RDN 负⇒`1`）；`±Inf` 与 `|x|≥2^p` 原样；NaN⇒canonical qNaN（sNaN 另置 `NV`）；静态档 flags **恒 0**（`static-rf0-sensitive=0`，`rf0[33:32]` 四种取值不变），`0x20` 仅结果≠输入置 `NX`；不置 `OF/UF/DZ`。
2. **`scalB` 三类**（exact 112 例 / ovf 96（`OF` 60）/ unf 88（`UF` 60）/ rd0 18 / nan 64）：**精确** `1.5×2^2=6.0`、`1.5×2^-1=0.75`、`3×2^10`、`minsub×2^24=2^-125`、`maxf×2^-1`、`±0/±Inf/qNaN` 原样 ⇒ flags 0；**溢出** `maxf×2^1` ⇒ RNE/RNA/RUP(+)`±Inf`、RTZ/RDN(+)`±maxf`，均 `OF|NX`（含 `n=2000`、`INT64_MAX`）；**下溢** `minsub×2^-1` ⇒ RNE/RTZ`±0`、RUP(+)/RDN(−)`±minsub`，均 `UF|NX`（含 `n=-2000`、`INT64_MIN`）。**无「轻微溢出」格**：只搬指数 ⇒ 值要么可表示、要么 ≥`2^(emax+1)`（模型已写成可达 FAIL 的断言，16000 例未触发）。
3. **符号类无标志**：`sign_flags` 20 例（4 指令 × sNaN/带 payload qNaN/−Inf/−0 等 5 形状）核上 `rf0` 逐字节==`0x7FF800007FC00000`；`sign.yaml` 28 例的 `rd6` 同；RTL 走 ALU 位操作（`WumingRecFN.signInject`），不经任何 FP 单元。
4. **三方一致**：单元台 rnd ft/fo 各 **5304** 例（精确 oracle；`roundToIntegral` 无 hardfloat 模块）、sclb 各 **24752** 例（oracle 0 差；其中 **14144/16796** 例对 hardfloat `MulRecFN` 值与标志全等）；核上 11 组 **core==model==QEMU** 逐字节；87 例 YAML **core==YAML==QEMU**；58/58 合法性镜像按预期异常；双 oracle（`fp_ref` vs `oracle_rnd.py`）**360 对 0 差**。
5. **周期实测**（同镜像 `exec` 行相邻拍差）：标尺 `foadd=1`/`shl_t=2`/`fodiv=57`，`ftrnd/fornd/ftsclb/fosclb` 各 2 例 **全 1 拍**。
6. **273 md5** `2d4d94651346ef673c5a855e024c1489`（期望侧=核上侧）。
7. **门控**：elab/Verilator rc=0 且 `%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree`/`validate-vectors`/`check-case-ledger` rc=0；`make check-inst`（L3）**rc=0**（tiny 44/44、vast full、载体 28 册）；**L2 rc=0**；L1 红仅 `check-knowledge-refs`/`check-run-artifacts`/`check-temp-dirs` 三项（他任务），本任务 offender **0**。
8. 完成区 ≤30 行、无运行期路径；构建/运行均主控机（未使用节点）。

**本任务新增的 8 条指令（`m13-integ-009` 对表用）**：`ftrnd`/`fornd`（`ftrnd_orri_rf`/`fornd_orri_rf` → `WumingFpRound`）、`ftsclb`/`fosclb`（`ftsclb_orrr_rf`/`fosclb_orrr_rf` → `WumingFpScale`）、`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`（`*_orrr_rf` → ALU 位操作 `WumingRecFN.signInject`）。证据：`roundint.yaml`/`sign.yaml`/`scaleb.yaml`（含两格式 `rd0`）+ sweep `rnd_*`/`sclb_*`/`sign_flags` + 单元台 op10–13/47–50。计数口径：spec 附录 A 实列 **52** 行、`opcodes.yaml` 的 `scope: fp` 共 **66** 个 id；`discussing.md` 的「47」未展开（见遗留①）——至此 **FP ALU 语义全部有 RTL 实现**（`opc 0x44` 无「已定义未实现」格）。

**新发现/坑**：①`roundToIntegral` 的 `NX` 放错 `Cat` 端会**变成 `NV`**（bit4=NX、bit0=NV）——「值对标志错」要按位读；②scaleB 不存在「轻微溢出」格（只搬指数）；③`rf0[33:32]` 只有 4 档，驱动侧别喂 `RNA`；④模型指数饱和下界须按有效数口径（`emin-2p`），否则夹住最小次正规；⑤sNaN payload / 负号 qNaN 的符号是本核与 softfloat 的已声明差异（sweep 放 model-only）；⑥任务 worktree 缺 `.dadao` 安装根会让 `check-inst`/L2 假红（软链主树即回绿）。

**遗留问题**：①「47 条」口径与 spec 附录 A 的 52 行 / 66 个 `scope:fp` id 不一致，请裁审计口径（未改 spec/台账）；②**26 个 `scope:fp` id 仍无 YAML 载体**（属 011–014：`ftadd/ftsub/fosub/ftmin/ftmax`、`ftcls/focls`、`ft2ft/fo2fo`、12 条转换、`set.w rf`/`rd2rf`/`rf2rd`/`ld.t rf`/`ldm.t rf`），其语义覆盖在 sweep（QEMU 同镜像）与 L3 探针，若要「tests/inst 全覆盖」需另立任务；③sNaN payload / 负号 qNaN 的已声明差异；④未 commit（提交权归 architect）；⑤任务书硬约束 1 的临时目录写了他任务号，按本任务号执行（同 `ISS-390`）。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = `WumingFP.scala` 的 `WumingFpRound`/`WumingFpScale`/`WumingFpMisc`、`WumingDecoder` 的 4 条解码与 `encode_onehot`、`WumingCore` 的下发/写回/标志、`WumingFPUnitHarness` 的 op 47–50、`tools/chipyard/{fp_ref,fp_sweep,fp_unit}`、两个新 YAML 与 `scaleb.yaml` 增补、证据脚本。缺陷均以「单元台 vs 精确 oracle / vs hardfloat」「核上字节级对比」「QEMU 同镜像」「273 回归」「门控」的真实输出暴露后逐条修复。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `WumingFpRound` 的 `NX` 写在 `Cat` 末位（= `NV` 位） | ✅已修 | `Cat(nx, false, false, false, nv)` | D 段 rnd ft/fo oracle-diff 488/500 → **0**；G 段 `rnd_dyn` core==model==QEMU |
| F2 单元台把 `RNA` 当 scaleB 的方向驱动（`rf0[33:32]` 不可编码） | ✅已修 | sclb 用 `MODES4`（RNE/RTZ/RDN/RUP）+ 注释 | sclb oracle-diff 224/格式 → **0** |
| F3 模型 `sclb_exact` 的指数饱和下界按值指数推 ⇒ 夹住最小次正规 | ✅已修 | `lo = emin - 2*sw`（e2 口径） | `fp_ref rndsclb` 16000 例 0 mismatch；`minsub×2^0` 正确 |
| F4 harness 的 `powFo` 用 `SInt.zext` 触发 Chisel 类型错误 | ✅已修 | 整型位移 + `.pad` | `wuming/compile` rc=0 |
| F5 decoder 新字段无默认值 ⇒ `sink ... not fully initialized` | ✅已修 | 三行默认赋值 | elab rc=0、`%Error`=0 |
| F6 `cases_sclb_rd0` 期望 `rf0` 写死为复位值（sNaN 行漏 `NV`） | ✅已修 | 期望 = `FCSR_BASE | 模型 flags` | G 段 `sclb_rd0` core==model |
| F7 sNaN payload / 负号 qNaN 的符号与模型不一致 | ✅已修 | 模型比较用 `fn_val` 折叠 NaN 值；sNaN 行移至 model-only 组 `sclb_nan_*` | D 段 0 差；`sclb_nan_*` 核上==模型；QEMU 组不含 sNaN |
| F8 证据脚本手算锚点错 1 处（`minsub×2^24` 写成 `0x0C800000`） | ✅已修 | 改 `0x01000000` | B 段 `anchors_bad=0` |
| F9 证据脚本组计数正则 `[ft]+` 不匹配 `_fo` | ✅已修 | 改 `(ft|fo)` | 6 == 6 |
| F10 首轮把 13 项改动写进**主工作树**（`ISS-368`/`ISS-402`） | ✅已修 | 逐项 `cp` 进任务 worktree 后主树 `git checkout -- <7 文件>` + `rm <2 新文件>`；`case-ledger.tsv` 在 worktree 重生成 | 主树 `git status -uall` **空**；worktree 15 项（附于回复） |
| F11 本任务的构建完成标记文件命名不合 `check-run-artifacts` | ✅已修 | 改名 `*-build-exit.txt`（`build.sh` 同步） | 本任务 offender **0** |
| F12 任务 worktree 缺 `.dadao` 安装根 ⇒ `check-inst`/L2 假红 | ✅已修 | 软链主树 `.dadao`（gitignored） | `check-inst` rc=0、L2 rc=0 |

**判决**：finding 全部已修/已决；证据脚本 190/190 全绿 + 注入 3 例先红后绿（`cp`+md5）；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（均本人在任务 worktree 执行，HEAD `2186281d`；长输出留运行期日志目录）
1. 全量运行期证据脚本 → `== summary: PASS=190 FAIL=0 ==`、退出码 **0**：B `anchors_bad=0`、双 oracle `pairs=360 bad=0`；C elab/Verilator rc=0 且 `%Error`=0；D `rnd ft/fo 5304`（`oracle-diff=0`、`static-rf0-sensitive=0`）、`sclb ft/fo 24752`（`hf-cases 14144/16796`，值/标志/oracle 全 0 差）；E 273 md5 `2d4d94651346ef673c5a855e024c1489`；F `semantic=87 fault=0`、`core ok=87 qemu ok=87`；G 13 组 core==model、其中 11 组再==QEMU、`sclb_rd0=18`、`sign_noflag=20`。
2. 门控（均 rc=0）：`apply-series`、`check-source-state`、`check-patch-tree`、`validate-vectors`、`check-case-ledger`、`check-inst`（tiny 44/44、vast full、载体 28 册）、L2；L1 红仅 `check-knowledge-refs`/`check-run-artifacts`/`check-temp-dirs`，offender 全属他任务，本任务 0 条。
3. 周期实测（11 个 mark 全测得）：`ftrnd/ftrnd2/fornd/fornd2/ftsclb/ftsclb2/fosclb/fosclb2` 全 **1 拍**；标尺 `foadd=1`、`shl_t=2`、`fodiv=57`；每个被测 mark 之后仍有后续指令（末位 `fodiv` → 存/退），无「多拍藏进末次」。
4. engineer 注入自检 `--self-test-inject` → 退出码 **0**：① `roundUp:=false` ⇒ `rnd ft 734 / fo 713` 红；② 去 scaleB 指数偏移 ⇒ `sclb hf 12203/14644` 红；③ 模型静态档恒置 NX ⇒ `rnd_ft/rnd_fo` 红；三次 `cp`+md5 还原 `25a8fb93…`/`d4e80c60…` 均 matched 且复跑回绿。
5. **我自选注入**：仅把 `WumingFpScale` 内 `rounder.io.roundingMode := io.mode` 改为强制 `RNE`（同名的除法/开方接线未动）⇒ 退出码 **1**、`PASS=41 FAIL=6`：`sclb ft hf 1214 / oracle 4660`、`sclb fo hf 1224 / oracle 3364` 全红而 `rnd ft/fo oracle-diff=0` 仍绿 ⇒ 红点唯一定位 scaleB 方向（含「下溢 RUP/RDN 回 ±0 而非 ±minsub」被抓住）；`cp` 还原 md5 `25a8fb93…` 相等、无 `.inj-bak/.preinject` 残留，复跑 `PASS=47 FAIL=0`、退出码 0。
6. **独立 oracle**（reviewer 自写，仅据 IEEE 754-2019 与 spec §2.1/§2.3/§3，不 import 工程师模型）：三份 YAML 期望全中 `roundint 44/44`、`sign 24/24`、`scaleb 11/11`（bad=0）；自选 3440 例 RTL 探针 `mismatches=0`、静态档置 `NX/OF/UF` 0 例、动态档「结果==输入仍置 NX」0 例；与工程师模型交叉 `33600+179200=212800` 对 **0 差**；「单次舍入 vs `×fl(2^n)` 双舍入」9 格 RTL 全等单舍入、7 格与双舍入值不同（`1.5×2^-150 ⇒ minsub` vs `0`；`1.5×2^1023 RTZ ⇒ maxf` vs `+Inf`）。
7. **NX 语义（派单质疑不成立）**：IEEE 754-2019 §5.9（Details of operations to round a floating-point datum to integral value）对五个固定方向 op 原文「**These operations shall not signal any exception except for signaling NaN input**」，只有 `roundToIntegralExact` 原文写「signals the inexact exception **if the result does not have the same numerical value as x**」。⇒ `ftrnd RNE 2.5 → 2` 在静态档 `0x01` 下**不该**也**没有**置 NX，`0x20` 才按「结果≠输入」置 NX——派单「静/动两档两句互相矛盾」的判断**不成立**（二者是 IEEE 中两个不同操作）；实测（探针 `static_with_NX_OF_UF=0`、YAML `+0.5 RNE ⇒ 0x0/flags 0`）与 spec §2.3、`contract-fp §18`、QEMU 四方一致。
8. **六档边界与 scalB 三类（我逐格自算）**：`+0.5`⇒RNE`+0`/RNA`1`/RTZ`+0`/RUP`1`/RDN`+0`；`−0.5`⇒`−0`/`−1`/`−0`/`−0`/`−1`（±0 保号）；`±1.5` 就近`±2`、RTZ`±1`；`−2.5`⇒RNE`−2`、RNA·RDN`−3`；`minsub/maxsub`⇒`±0`（RUP 正/RDN 负⇒`1`）；`±Inf`、`|x|≥2^p` 原样；qNaN→canonical、sNaN→canonical+NV。scalB：精确 112（不置标志 104）/溢出 96（`OF` 60：RNE·RUP(+)`±Inf`、RTZ·RDN(+)`±maxf`，恒 `OF|NX`）/下溢 88（`UF` 60：RNE·RTZ`±0`、RUP(+)/RDN(−)`±minsub`，恒 `UF|NX`）；`n=INT64_MAX/MIN`、`±2000` 探针 9 格全中；无「轻微溢出」格（只搬指数 ⇒ 可表示或 ≥`2^(emax+1)`）。符号族 20（sweep `rf0==FCSR_BASE`）+28（YAML `rd6`）例零标志，含 sNaN/带 payload qNaN/`−Inf`/`−0`。
9. 文件对账：`git show --stat HEAD` 恰 15 项 == 完成区清单；分支对 master **无** `spec/`、`contracts/`、`Makefile`、台账改动；审前/审后 `git status -uall` 均 0 行、组件源 md5 与审前一致、无注入残留；完成区 15 行 ≤30、无运行期路径；未 commit/push（HEAD 为 architect 的 WIP），未占 207/208。

**非阻断 finding**（文档级，交 architect 收尾一并订正）：① 完成区「46+115+128 例」漏 `rnd_fo` 的 115（现场 `rnd_ft=115 / rnd_fo=115 / rnd_dyn=128`＝358）；② 遗留②「26 个 `scope:fp` 无 YAML 载体」现场 **32**（`ftmin_orrr_rf` 实有载体、转换缺 13 条非 12、另漏 `ld.o/ldm.o/st.o/st.t/stm.o/stm.t`）；③ README/证据脚本注释引「IEEE 754-2019 §5.3.1」应作 §5.3（列举）/§5.9（细则），§5.3.1 属 2008 编号；④「静态档 flags 恒 0」应作「静态档除 sNaN→NV 外不置标志」；⑤ 答遗留①口径：`m13-integ-009` 审计集合取 **66**（`contracts/fp_semantics.yaml`＝`contract-fp` 声明的 `scope: fp` 全集，含 `ld.t rf0` 等 rf0 约定项），按 **52**（spec 附录 A＝11 个 IEEE-able 族）排版需给 IEEE 条文的行、其余 14 行标「IEEE 未规定」，「47」无机器可读来源建议退役为别名。

**判决：Accepted**（验收命令块在我本人重跑下全部通过；9 项硬约束无违反；上列 finding 属文档级，不阻断）。

#### 收尾（architect，2026-11-12 21:49）

- reviewer **Accepted**：全量 190/0；三份 YAML 由**自写 IEEE oracle** 复核（`roundint 44/44、sign 24/24、scaleb 11/11`）；3440 例 RTL 探针 `mismatches=0`；与模型交叉 212,800 对 0 差。
- **我在派单里的质疑被推翻**：IEEE 754-2019 §5.9 把 `roundToIntegral`（五档固定方向，**不置 NX**，仅 sNaN 置 NV）与 `roundToIntegralExact`（结果≠输入置 NX）分成**两个操作**；静态档恒不置 NX **是对的**，动态 `0x20` 走 Exact。四方（实测/spec §2.3/`contract-fp §18`/QEMU）一致。
- **只舍入一次**有实证：9 格 RTL 全等单舍入，7 格与「×fl(2^n)」双舍入**值不同**（`1.5×2^-150 ⇒ minsub` vs `0`）。
- 周期：四条新指令各 2 例全 **1 拍**（标尺 `foadd=1`/`shl_t=2`/`fodiv=57`），无「藏进末次」。
- 计数订正（finding ①–④）：`rnd_fo` 的 115 漏计（实为 115/115/128=358）；「26 个 scope:fp 无载体」实为 **32**；引用 §5.3.1 应为 §5.3/§5.9；「静态档 flags 恒 0」应作「除 sNaN→NV 外不置标志」。
- **`m13-integ-009` 审计口径已定（reviewer 与我一致）**：审 **66**（`contract-fp` 的 `scope: fp` 全集，可做「漏一条 ⇒ FAIL」门控）、按 **52**（spec 附录 A）排版、**47 退役**（任何机器可读源都复现不出）。

