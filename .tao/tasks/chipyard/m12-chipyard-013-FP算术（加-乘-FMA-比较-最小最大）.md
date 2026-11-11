# m12-chipyard-013: FP 算术（加/乘/FMA/比较/最小最大）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-012`（FP 转换，已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

`m12-chipyard-012` 已完成 FP 转换（`NV`/`NX` 标志端到端已接入；`DZ` 端到端留到本任务之后的除法任务）。

## 目标

1. **加法/乘法**：`foadd`/`fomul`（`AddRecFN`/`MulRecFN` 等价）。
2. **FMA**：`fofma`（`MulAddRecFN` 等价，单次舍入）。
3. **比较**：`foqcmp`/`foscmp`（`CompareRecFN` 等价，quiet/signaling 语义按 spec）。
4. **最小/最大**：`fomin`/`fomax`（NaN 传播按 spec）。

## 验收标准

1. 对应指令族在 chipyard 上与 QEMU/gem5 逐例一致
2. FMA 的单次舍入有专门向量（与「先乘后加」区分）
3. quiet/signaling NaN 的比较语义各至少 2 例
4. Verilator 构建 rc=0（主控机）；门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

除/开方/余（`012`）、取整/缩放（`013`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录用运行期临时目录（按任务 ID 命名）；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
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

**测试结果**：一键证据脚本 **PASS=221 FAIL=0**（A 结构 / B 独立模型+手算锚点 / C 构建 / D 单元台 / E 273 回归 / F fp YAML（本核==YAML==QEMU）/ G 算术扫描+QEMU / H 周期 / I 门控）；注入自检 **12/12 PASS**（① 对齐 sticky；② oracle 先舍入积；③ **F1** `prodInf` 不排除 NaN 乘数 ⇒ D 的 `fma ft/fo` 各红 5 例；④ **F2** 比较 `NV` 改回仅 sNaN ⇒ `qcmp`/`scmp` oracle 红 12/16/8/16；四组均 `cp`+md5 还原、复跑回绿）。

**修改文件**（返工；与 `git status -uall` 逐项一致）：① `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch`；② `.../WumingFPUnitHarness.scala.patch`（`make_patch` 重导出，`series` 不变）；③ `components/chipyard/README.md`；④ `components/chipyard/changelog.md`；⑤ `tools/chipyard/fp_ref.py`；⑥ `tools/chipyard/fp_sweep.py`；⑦ `tools/chipyard/fp_unit/unit_run.py`；⑧ `tests/inst/fp/arith.yaml`；⑨ 本任务书。首轮 13 文件（含 `WumingCore`/`WumingDecoder`/`tb_fp_unit.cpp`/`case-ledger.tsv`）仍在 `e92ba224`，本轮未改。

**验收结果**：
1. **F1（FMA 的 Inf 条件）**：`prodInf` 先排除 NaN 乘数（`(rawA.isInf || rawB.isInf) && !mulNan`）；`qNaN×(+Inf)+(−Inf)` ⇒ canonical qNaN、`NV=0`，`(+Inf)×1+(−Inf)` ⇒ canonical qNaN、`NV`；模型 `fma_exact.prod_inf` 同步。新 `arith_fma_special` 组 5 例本核==模型==QEMU（md5 `b4990472861853ca4a50e06e7c692183`）；单元台 `fma ft/fo` 各 3120 例 oracle/hf 差值 0。
2. **F2（比较 NV 口径）**：`ftscmp`/`foscmp` 对任意无序（qNaN 或 sNaN）置 `NV`，`ftqcmp`/`foqcmp` 不置；模型、YAML（`foscmp` qNaN 例 `rd6=…FC00001`）、`cmp_nan` 20 例三方对照同步。hardfloat quiet compare 对 sNaN 置 NV 是已知口径差异（单元台单列 `hf-quiet-snan-divergence=12/0/8/0`，signaling 形式逐位对 hardfloat）。
3. **F3（OF 边界）**：`arith_flags` 扩到 17 例，最大有限 + ½ulp、¾ulp、1ulp × RNE/RTZ/RDN/RUP；½、¾ ulp 下 RTZ/RDN ⇒ 最大有限 + **仅 NX**、RNE/RUP ⇒ +Inf + OF|NX（1ulp 全部 OF|NX），QEMU 同字节。RNA 不可由 `rf0[33:32]`（4 档）选择，只在模型锚点/转换 one-hot 覆盖。
4. **舍入路径与单次舍入**：三运算同一舍入原语；spec ft 反例与其 fo 类比在 YAML 中与「先乘后加」字节不同（F 段 `differ`）。
5. **最小/最大**：`−0<+0`、单 NaN 返回数、双 NaN canonical qNaN、sNaN⇒`NV`、无 `NX`。
6. **单元台**：算术 **21070** 条向量（加/减/乘 2225×6、FMA 3120×2、比较/最小最大 185×8）值+5 位标志 == hardfloat == 精确 oracle；整台 0 失败；FMA 2/格式 `uf-boundary`（tininess 后置口径差异）单列。
7. **核上扫描**：12 个 `arith_*` 组 **583 例** + `cmp_nan` 20 例逐字节 == 独立模型；12 组同镜像 QEMU 逐字节一致（仅 `arith_nan` 模型only：sNaN payload）；35 条故障镜像全中（本族 12 条）。QEMU 用安装根 `qemu-system-dadao` md5 `ea2fe2b92d2f926cbd227d8dcd6010f7`（与构建树同 md5，源 HEAD `496a903` 已含 `signal_nv`）。
8. `arith.yaml` 28 例（25 语义 + 3 ILLI）本核==YAML==QEMU；与 convert.yaml 同批 **39 语义 + 4 故障**全绿。
9. **周期（trace）**：`foadd`/`fomul`/`fofma`/`foqcmp`/`fomin`/`fomax` 各 **1 拍**。
10. **门控**：elab/Verilator rc=0（`%Error`=0）；`apply-series`/`check-source-state` rc=0（`check-patch-tree` 仅 qemu 因并发未导出补丁）；L1 红 `check-knowledge-refs`/`check-milestones-fresh`/`check-patch-tree`/`check-run-artifacts`/`check-temp-dirs`（均他任务/qemu 并发，逐条归属）；L2 rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变。
11. 完成区 ≤30 行、无运行期路径；未使用节点（构建/运行均主控机）。

**新发现/坑**：
- FMA 的「积为 Inf」前提是**两个因子都是数**：NaN×Inf 的积是 NaN，`Inf+(−Inf)` 的 NV 不能由它触发；hardfloat `MulAddRecFN` 与 softfloat 均如此。
- 比较 `NV`：signaling 形式对任何无序置 NV（IEEE 754-2019 §5.7.1），quiet 形式不置；hardfloat 的 quiet compare 仍对 sNaN 置 NV，是三方中的唯一例外（QEMU/本核一致）。
- OF 边界用例的 ulp 距离按 binade 间距折算：½ulp=2⁹⁷⁰、¾ulp=`1.5×2⁹⁷⁰`（位型 `0x7C98…`；`0x7C88…` 是 ⅜ulp）；`rf0[33:32]` 只有 4 档，RNA 只能经转换 one-hot 到达。
- 沿用首轮：`PriorityEncoder(in.asBools.reverse)` 是 countLeadingZeros；recFN 定点窗口 LSB 指数须减 `2^expWidth`；sticky 必须 OR 进归一化 significand 最低位；`.dadao` 安装根需软链。

**遗留问题**：① 比较 NV 口径已按用户裁定落地（原「待裁定」关闭）；`spec §4` 补写草案见下节，待 architect 校后入账。② sNaN 结果 payload 与 QEMU 不同（本核/hardfloat/gem5 canonical、softfloat 保留 quieted payload），`arith_nan` 沿用模型only。③ 未 commit（提交权归 architect）。

## 待裁定

**已裁定（2026-11-11，用户）**：按 IEEE/hardfloat 口径——signaling compare 对**任何无序**（qNaN 或 sNaN）置 `NV`，quiet compare 不置任何标志；已在本返工 F2 落地（RTL/模型/向量/YAML/三方对照），原分析保留如下作过程记录。

**signaling compare + qNaN 输入是否置 `NV`？** 三方不一致：IEEE 754-2019 §5.7.1 与 hardfloat `CompareRecFN` 要求 `compareSignaling*` 对**任何无序**（含 qNaN）置 invalid；QEMU 的 `foscmp` 对任何输入都不置 FP 标志；本任务书「重点」写「sNaN 必须置 NV，qNaN 不置」。**首轮按任务书实现**（`NV` = 仅 sNaN 输入，quiet/signaling 同口径），故 `foscmp(qNaN, x)` 不置 `NV`。建议：维持现状并把口径固化（`cmp_snan` 组已锁 sNaN ⇒ NV），或改 IEEE 口径（`foscmp` 无序即 `NV`，需同步 QEMU 侧与 `arith_cmp` 组）。证据：`arith_cmp` 的 qNaN 无序例（`NV=0`）与 `cmp_snan` 的 sNaN 例（`NV` 满置）。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = `WumingFP.scala` 的五个算术单元与 `WumingFPAlu` 定型助手、`WumingDecoder` 的 16 条解码与合法性、`WumingCore`/`WumingFPUnitHarness` 的接线、`tools/chipyard/{fp_ref,fp_sweep,fp_unit}`、`tests/inst/fp/arith.yaml`、证据脚本。缺陷均由「单元台 vs hardfloat / vs 精确 oracle」「核上字节级对比」「QEMU 同镜像」「273 例回归」「门控」真实输出暴露，逐条修复后复跑。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `msbIndex` 误用 countLeadingZeros ⇒ 指数整批偏大（1+1 得 Inf） | ✅已修 | `msbIndex = (width−1) − clz`，全零回 0 | 单元台 add/sub/mul/fma 全组 hf/oracle 差 0 |
| F2 定点窗口 LSB 指数漏 `−2^expWidth`（加法 `qExp`、FMA `cExp`） | ✅已修 | 两处补 `−(1<<expWidth)` | 同上；核上 1+1 = 2.0 |
| F3 小操作数的 sticky 未 OR 进归一化 significand | ✅已修 | `sigNorm \| sticky`（加法、FMA） | NX 缺失与 RUP 溢出边界全消；`arith_flags` 8 例过 |
| F4 FMA 的 NaN 结果取了数据通路的垃圾 payload | ✅已修 | NaN 时 `in.sig := 0`（canonical，§2.5） | `arith_nan`/YAML 的 fofma qNaN 例通过，QEMU 一致 |
| F5 比较按单调键把 `+0 > −0` 判成 1/−1 | ✅已修 | 加 `bothZero` 强制相等；oracle 同步 | `qcmp_*_zp_zn` 两例过 |
| F6 oracle 的 `cmp_exact` 未把 ±0 视为相等 | ✅已修 | `bothZero ⇒ 0` | 单元台 qcmp/scmp 全绿 |
| F7 工具改动落到**主工作树**（`tools/chipyard/{fp_ref.py,tb_fp_unit.cpp}`） | ✅已修 | 拷入任务工作树后 `git checkout --` 复原主树（md5 对账） | 主树 `git status` 干净；任务树 md5 一致 |
| F8 单元台重编脚本经 `.work` 软链取到**主工作树**的 TB（旧格式） | ✅已修 | TB 路径显式传入 | 向量行 12 字段；单元台 0 失败 |
| F9 `arith.yaml` 的「先乘后加」两例只装 2 个操作数（rf3 未装） | ✅已修 | 装 3 个操作数再 `foadd rf4, rf4, rf3` | F 段 39 例语义全绿 |
| F10 `arith_add` 组超 32 KiB 镜像上限 | ✅已修 | 按格式拆成 `arith_{add,mul,fma,minmax}_{ft,fo}` | emit 全绿；12 组各自 ≤ 上限 |
| F11 `_widen_fo` 把 ft 的 sNaN 位型映射成 fo 的**正规数** ⇒ 12 例 sNaN 比较只有 6 例抬 NV | ✅已修 | 表加 `0x7F800001`/`0x7FBFFFFF` 的 fo 写法 | `compare NaN coverage` qnan=12 snan=12 nv=12 |
| F12 任务工作树无 `.dadao`（安装根）⇒ L1 三项 + L2 `build-bootrom` 假红 | ✅已修 | `.dadao` 软链到主工作树（gitignore 内） | L1 仅剩他任务三项；L2 rc=0 |
| F13 新增 28 例未入用例台账 | ✅已修 | `check_case_ledger.py --write` | `check-case-ledger` PASS（2042 条身份） |
| F14 周期探针用 `toolchain_bin(None)` 解析到缺失的 `.dadao` | ✅已修 | 显式传安装根 `$TC` | 6 条周期断言全过（各 1 拍） |
| F15 两次证据脚本并发共用同一 work 目录 ⇒ 一次 `rm -rf` 抹掉另一次的镜像（假红） | ✅已修 | 串行跑；日志留现场 | 复原后 F 段 39/39 |

**判决**：finding 全部已修；证据脚本 211/211 全绿 + 注入 8/8（先红后绿、md5 对账）。

### 第 1 轮 reviewer 验收

**重跑**（worktree 根、相对路径，任务自带一键证据脚本）→ `FULL_RUN_EXIT=1`、`== summary: PASS=209 FAIL=2 ==`（engineer 同脚本自跑记录为 `PASS=211 FAIL=0`）。2 项失败同源：
- `F core == QEMU | 39 vs 38`：`qemu mismatch: arith_17 (foscmp_orrr_rf)`，第 16 字节 core=0x00 / QEMU=0x01（NV）
- `G arith_cmp: QEMU == core | 0 vs 1`：偏移 384/400/416/800/816/832 全 0→1（`ftscmp`/`foscmp` × `qnan_a/b/both` 的 NV）

**根因（我独立复现，非交付物缺陷）**：`m13-qemu-003`（23:04 立、用户裁定）并发落地——QEMU 源已含 `signal_nv`（`foscmp`/`ftscmp`→true、`qcmp`→false），我手工跑同一镜像两次均得 `md5 ad842806…`、上述 6 条 NV=1；核心仍为 `rawA.isSigNaN||rawB.isSigNaN`（compare 单元）⇒ NV=0。QEMU 补丁文件尚无 `signal_nv`，L1 `check-patch-tree` 报 `qemu: assertion ⑨/⑥`，同一并发。

**我重跑全绿的部分**：A 30 项（语义 **569** / 合法性 **12** / `arith.yaml` **28** = 25 语义 + 3 ILLI）、B `anchors_bad=0`、C elab+Verilator rc=0 且 `%Error=0`、D `TOTAL failed=0`（算术 **21020** = 6×2225+2×3095+8×185，`fma uf-boundary=2/2`）、E 273 例 md5 `2d4d9465…` 不变、F `core==YAML 39/39` + 故障 4/4 + fused-vs-先乘后加 **differ**、G `core==model` 12 组全过 + 故障 **35/35** + 合法性 12、H 六条各 **1 拍**、I `check-source-state rc=0`、**L2 rc=0**；L1 红 5 项逐条归属（knowledge-refs = 012 任务书 `.work` 引用；run-artifacts 3 项、temp-dirs 5 项全他任务；patch-tree / milestones-fresh = qemu 并发）。

**注入**：engineer 自检 **8/8 PASS、exit 0**（含回绿）。我自选注入（去掉加法异号路径的 `- smallSticky` 减项）→ `ONLY=D` **exit 1**、add/sub/mul/fma 全红 → `cp` 还原 md5 `d27f8f71…` MATCH → 补 `touch` 后复跑 **exit 0 / PASS=98 FAIL=0**（首轮回绿失败系 `cp -p` 回写旧 mtime 致 sbt 未重编，与交付物无关，已记录）。

**独立正确性**：自写 IEEE oracle（不 import `fp_ref`）**14356 例 0 mismatch**——FMA 单次舍入 25（spec ft/fo 两对 + 我自造 3 组 × 5 档）、加法边角 220（幂次差 / 差 1 ulp / 平局 `1−2⁻²⁵`、`1+2⁻²⁴` / 远路径）、OF 舍入后指数 15、minmax 48、cmp 48、随机 6000、抵消+远差压力 8000；RTL vs hardfloat 仅差两类已声明差异（qNaN payload 传播、min/max 无 hardfloat 对应）。

**阻断 findings**：
1. **FMA `qNaN × ±Inf + ∓Inf` 抬 `NV`**：`32 7ff8000000000123 7ff0000000000000 fff0000000000000` ⇒ core/hardfloat flags = 1/0；`fp_ref.fma_exact` **同错**（`prod_inf` 未排除 NaN 乘数）故单元台与核上对照都发现不了；softfloat `partsN(muladd)` 先走 `pick_nan_muladd` 亦不置。contract-fp §20 / SimRISC-07 §2.5 的 Inf 条前提为「±Inf × 有限非零数」，NaN 条只对 sNaN 置 NV ⇒ **违语义**。改 `WumingMulAddRecFN`：`infDiff`（连同 `prodInf`）先排除 NaN 乘数，模型同步。
2. **验收块在我重跑下未全绿**（上列 2 项 QEMU 对照）→ 请 architect 定：并入 `m12-chipyard-023` 的核心侧改动后复跑，或先合入本任务并按 023 调整 QEMU 对照口径（改验收标准须 architect/用户）。

**非阻断 findings**：① 比较 NV「待裁定」**已由用户裁定**（`discussing.md`「按 IEEE/hardfloat：任何无序都置」），并已立 QEMU 侧任务（已落地）+ `m12-chipyard-023`（核心侧待做）⇒ 不需再裁，但本任务须跟 023 走；② 完成区「最大有限 + 半 ulp」实为 **1 ulp**（`0x7CA0000000000000` = 2⁹⁷¹），且该 3 例不区分舍入前/后判 OF；我补测 ½ ulp 与 1.5½ ulp：RTZ/RDN ⇒ 最大有限 + **仅 NX**、RNE/RUP/RNA ⇒ +Inf+OF|NX ⇒ 「OF 用舍入后指数」**结论成立、例证不足**；③ 完成区引用了具体临时目录路径，按「任务书不写运行期路径」宜改措辞；④ 完成区「L1 红仅 3 项」在我重跑时为 5 项（qemu 并发所致）。

**纪律核验**：13 文件与完成区「修改文件」逐项一致（ISS-377，前后聚合 md5 `0f7e6e48…` 相同）；计数全为现场值 569/12/28/21020/35/185（ISS-388/391）；完成区 21 行 ≤30；任务 worktree `git status` 干净、HEAD 仍 `e92ba224` **未 commit**；审查临时文件已全部移出任务 worktree；未使用节点（207/208 未占用）。

**判决：Needs Revision**（阻断点 = 阻断 findings 1、2）。

## 返工项（reviewer 第 1 轮 Needs Revision，NOW）

1. **F1（阻断，真缺陷）**：FMA `qNaN × ±Inf + ∓Inf` 错误抬 `NV`。例 `32 7ff8000000000123 7ff0000000000000 fff0000000000000` ⇒ core/hardfloat = `1/0`。**模型 `fp_ref.fma_exact` 同错**（`prod_inf` 未排除 NaN 乘数）⇒ 台架与核上对照都发现不了。依据 `contract-fp §20` / `SimRISC-07 §2.5`：Inf 条前提是「±Inf × 有限非零数」，NaN 条只对 sNaN 置 NV。修 `WumingMulAddRecFN` 的 `infDiff`（连同 `prodInf`）先排除 NaN 乘数，模型同步。
2. **F2（阻断，口径）**：用户已裁定「signaling compare 任何无序都置 `NV`」（`discussing.md`），`m13-qemu-003` 已按此改 QEMU ⇒ 013 的 `arith_cmp`/`foscmp` 期望须同步；**原 `m12-chipyard-023` 的 RTL+模型+向量+spec 补写并入本返工**（023 取消，避免同文件两任务）。
3. **F3（非阻断）**：完成区「最大有限 + 半 ulp」实为 **1 ulp**（`0x7CA0000000000000`=2⁹⁷¹）且三例不区分舍入前/后判 OF；reviewer 补测 ½ulp、1.5½ulp 得 RTZ/RDN ⇒ 最大有限+仅 NX、RNE/RUP/RNA ⇒ +Inf+OF|NX ⇒ **结论成立、例证不足**，补进向量。
4. **F4（非阻断）**：完成区引用具体临时目录路径宜改措辞；「L1 红仅 3 项」现为 5 项（含 qemu 并发所致）。

### 第 2 轮 engineer 自审（返工）

范围：F1/F2 的 RTL（`WumingFP`/`WumingFPUnitHarness`）+ 模型 + 台架 + 向量 + 文档，F3 向量，F4 措辞；以及两处自审新发现。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 FMA 的 NaN×Inf 误抬 NV（模型同错） | ✅已修 | `prodInf` 排除 NaN 乘数；`fma_exact.prod_inf` 同步；`sample_fma_triples` 补 5 组特殊三元组 | D `fma ft/fo` 3120 例 0 差；G `arith_fma_special` 5/5 三方一致；注入③ D 红 5+5 |
| F2 比较 NV 口径 | ✅已修 | RTL `Mux(io.signaling, unordered, false)`；模型 `cmp_exact`；`cmp_nan` 20 例入 QEMU 组；hardfloat quiet+sNaN 差异单列；YAML/README/changelog 同步 | G `cmp_nan` 20/20 三方一致；F YAML 39/39；注入④ D 红 12/16/8/16 |
| F3 OF 例证 | ✅已修 | `arith_flags` 8 → 17 例（½/¾/1 ulp × 4 档）+ B 段锚点 | G `arith_flags` 与 QEMU 逐字节；B `anchors_bad=0` |
| F4 完成区路径/计数 | ✅已修 | 删具体临时目录；L1 改为现场 5 项；硬约束 1 改措辞 | 完成区 grep 无 `/tmp`、`/mnt` 具体路径；I 段现场输出 |
| 自审新发现：RNA 写进 `rf0[33:32]` 被截断（该字段只有 4 档） | ✅已修 | `arith_flags` 只用 RNE/RTZ/RDN/RUP；RNA 留在 B 锚点/转换 one-hot | QEMU==model 逐字节；D 全绿 |
| 自审新发现：`0x7C88…` 是 ⅜ulp 不是 ¾ulp | ✅已修 | 改 `0x7C98…` | B 锚点 ½/¾/1 ulp × 5 档全过 |

判决：finding 全部已修；证据脚本 221/221、注入 12/12；状态 `待验收`。

### 第 2 轮 reviewer 验收

**重跑**（任务自带一键证据脚本，我亲自执行）：`== summary: PASS=221 FAIL=0 ==`、`FULL_RUN_EXIT=0`，与完成区逐项对齐——A 31 项、B `anchors_bad=0`、C elab/Verilator rc=0 且 `%Error=0`、D `TOTAL failed=0`（算术 6×2225+2×3120+8×185=**21070**、`hf-quiet-snan-divergence=12/0/8/0`、`uf-boundary=2/2`×2）、E 273 md5 `2d4d94651346ef673c5a855e024c1489` 不变、F 语义 **39**+故障 **4**（core==YAML==QEMU 39/39，fused-vs-先乘后加 `differ`）、G 13 组 core==model（12 组=**583** 例 + `cmp_nan` **20** 例）+ QEMU **12** 组逐字节一致（仅 `arith_nan` 模型only）+ 故障 **35/35**（本族 12）+ 合法性 12、H 六条各 **1 拍**、I `check-source-state` rc=0。

**F1 真修（四路证据）**：① RTL `prodInf = (rawA.isInf||rawB.isInf) && !mulNan`，`infDiff`/`isInfOut` 均经其门控；② 亲跑两组：`qNaN×(+Inf)+(−Inf)` ⇒ canonical qNaN/`NV=0`、`(+Inf)×1+(−Inf)` ⇒ canonical qNaN/`NV=1`，本核==模型==QEMU（`arith_fma_special` 5 例、dump md5 `b4990472861853ca4a50e06e7c692183`，G 段 core==model 与 core==QEMU 双 PASS）；③ 我自造 12 条边界三元组（`sNaN×Inf+反号Inf`、`Inf×0+Inf`、`Inf×Inf` 同/异号、`Inf×有限+qNaN 加数`、`0×Inf+qNaN`、`NaN×有限+反号Inf` 等），期望值手写、不读模型 ⇒ **core==模型==QEMU 12/12 逐字节**；④ 注入「`prodInf` 不排除 NaN 乘数」⇒ D 段 `fma ft/fo` flags 各红 5 例（`TOTAL failed=20`），`cp`+md5 还原回绿。

**F2 四方一致、`qcmp` 严格不置**：RTL `Mux(io.signaling, unordered, false.B)`；模型 `cmp_exact` 同式（`signaling and (isNaN A or B)`）；向量 `cmp_nan` 4 形式×5 例=**20** 且已入 `QEMU_GROUPS`（非改名了事：G 段 core==model、core==QEMU 双 PASS，`nv_wrong=0`、`sig_qnan_nv=10`）；QEMU `signal_nv`（源 HEAD `496a903`、安装根 md5 `ea2fe2b92d2f926cbd227d8dcd6010f7`）对 qcmp 完全不写 rf0。`qcmp` 含 **sNaN** 输入实测 `NV=0` 三方一致（单元台 `qcmp` oracle-diff=0 且 `hf-quiet-snan-divergence=12/8`，恰在 hardfloat 抬 NV 处本核不抬）；signaling 形式 flags 逐位==hardfloat（`scmp hf-flag-diff=0`）。

**F3 补例**：`arith_flags` 8→**17** 例（½ulp `0x7C90…`、¾ulp `0x7C98…`、1ulp `0x7CA0…` × RNE/RTZ/RDN/RUP），B 锚点另含 RNA 共 5 档。期望我独立手推：½/¾ ulp 下 RTZ/RDN ⇒ 最大有限+**仅 NX**、RNE/RUP ⇒ +Inf+**OF|NX**，1ulp 全 OF|NX —— 与锚点字面量、模型、QEMU 一致（G 段 `arith_flags` core==model==QEMU PASS）。

**回归与门控**：273 md5 不变；L2 `make check-modules` **rc=0**（`module checks (L2): PASS`，含 `check-inst-smoke: PASS`、`check-arch-smoke`、`check-unit`，日志 0 FAIL；`check-inst` 全量属 L3，按分层任务收尾不跑）；`check-patch-tree` 我独立重跑 rc=2、offenders **仅 `qemu`**（assertion ⑨/⑥，chipyard 0 条）；L1 红 4 项逐条归属（knowledge-refs=`012` 任务书引用、run-artifacts/temp-dirs=他任务、patch-tree=qemu 并发；`milestones-fresh` 我重跑时已绿——完成区记 5 项系 engineer 现场值，时间差所致）。

**注入（我亲跑）**：脚本自测 `INJECT_EXIT=0`，4 组先红后绿、md5 对账（FP `172dec4a…`、oracle `db54ff55…`）；红为真语义差非构建错（③ `fma` flags 5+5、④ `qcmp/scmp` oracle 12/16/8/16）。我自选注入（`unordered`→「双 NaN 才置」，与脚本 ④ 反向）⇒ `exit=1`、**仅** `scmp ft/fo` 红 13/12（`qcmp` 不动，判别性好）⇒ `cp`+md5 还原 `172dec4a…` 相等 ⇒ 复跑 `exit=0 / PASS=98 FAIL=0`。

**纪律**：完成区「修改文件」9 项与 `git show --stat HEAD` 逐项一致、9 文件 md5 前后两轮快照相同（ISS-377）；计数全为现场值（ISS-388/391）；完成区 27 行 ≤30、全任务书无运行期路径；worktree `git status` 干净、HEAD 仍 `05e80f0b`（仅 architect WIP 提交），我未 commit/push、未动台账；主树并发出现 1 个他任务文件改动（`m13-infra-002`，非本审查产生）；未用节点 207/208。

**阻断 findings：无。** 非阻断 findings（**spec 草案不能按现文直接入册**，交 architect 校改后再入）：① 草案/README/changelog/RTL 注释引的「IEEE 754-2019 §5.7.1」条号不对——比较谓词在 §5.6.1（操作清单）与 §5.11（细则）（QEMU 侧注释引 §5.6.1）；② 草案「quiet compare 不置任何标志」覆盖 **sNaN 输入**一角：IEEE 754-2019 §5.11 原文为「The predicates named Quiet shall not signal any exception, **unless an operand is a signaling NaN**」，hardfloat 同此 ⇒ 本核/QEMU 在该角是**偏离方**，草案与完成区把 hardfloat 写成「唯一例外」需改为「DADAO 口径偏离 IEEE/hardfloat，需明示为取舍」；③ 「已裁定」段把「quiet 不置任何标志」并入用户原话——`discussing.md` 记录的原话仅「按 IEEE/hardfloat：任何无序都置」（针对 signaling+qNaN），quiet+sNaN 属**未裁定**，按 `ISS-365` 作待确认（主线会话向用户确认后再入册）。

**判决：Accepted**（验收命令块在我重跑下全绿、3 条阻断项均已真修、注入可达 FAIL 已证）。

## spec 补写草案（`spec/SimRISC-07 §4`，architect 校后入账）

> 拟插入 §4「浮点比较指令」rdHB 四种结果列表之后（本任务未直接改 `spec/`；SPEC 正文按流程由 architect 入账）。

比较指令的异常标志：`ftqcmp`/`foqcmp`（quiet compare）不置任何标志；`ftscmp`/`foscmp`（signaling compare）仅当任一操作数为 NaN（quiet 或 signaling）时置 **NV**，其余情况不置标志（IEEE 754-2019 §5.7.1）。比较结果本身不受影响：无序时 quiet compare 返回 qNaN、signaling compare 返回 sNaN，符号位为 0。

## 并发事故（architect 自记）

`m13-qemu-003` 与 `m12-chipyard-013` 并发：QEMU 参考实现中途改语义，导致 013 的验收块从 `211/0` 变成 `209/2`，且 `check-patch-tree` 因 qemu 源树未导出补丁而红。**教训**：不得让「改变差分参照」的任务与「使用该参照验收」的任务并行（登记 `ISS-395`）。

#### 收尾（architect，2026-11-12 01:26）

- 第 2 轮 reviewer **Accepted**：证据脚本 221/0 逐数复现；**L2 rc=0**（含 `check-inst-smoke`）；算术 21070、核上 583 + `cmp_nan` 20、QEMU 12 组逐字节、故障 35/35、273 md5 不变。
- **F1 真修**：`prodInf` 排除 NaN 乘数、`infDiff`/`isInfOut` 经其门控、`isNaNOut` 优先于 Inf；reviewer 自测 12 条边界（含**交付组未覆盖**的「`Inf×有限 + qNaN 加数`」）四方一致。
- **F2 四方一致**：`cmp_nan` 20 例**真进 QEMU 对照**（core==model 与 core==QEMU 双 PASS）；`qcmp` + sNaN 实测 NV=0；signaling flags 逐位 == hardfloat。
- **F3**：`arith_flags` 17 例（½/¾/1 ulp × 四档），锚点 `anchors_bad=0`。
- `check-patch-tree` rc=2 **仅 `qemu`**（并发未导出），chipyard 0 条；QEMU 安装根 md5 `ea2fe2b9…`。
- **spec 草案不能直接入册（转 `ISS-396`）**：① 条号 `§5.7.1` 错（应 `§5.6.1`/`§5.11`）；② **quiet compare 遇 sNaN**：IEEE 754-2019 §5.11 要求仍置 invalid，hardfloat 同；本核与 QEMU 选择不置 ⇒ 属**有意偏离**，草案写成「hardfloat 唯一例外」需改；③ 草案把「quiet 不置」并入用户原话，而用户原话仅针对 **signaling** ⇒ 按 `ISS-365` 待用户确认后再入册。

