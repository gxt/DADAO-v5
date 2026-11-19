# m15-idl-016: 浮点语义库 fo 族 + remainder（binary64）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-015`（库骨架 `idl/lib/fp.idl`、ft 族 53 函数已落地）
**可并行分片**：否（与 `m15-idl-007` 同改 `idl/lib/fp.idl`，串行）
**预估**：2–3 天（分 2 批）
**档位**：大改
**状态**：已验证

## 背景（`m15-idl-007` 批 2 的阻塞）

`m15-idl-007` 批 2 剩 8 条写不出来，根因是**库缺口**（不是散文问题）：

- **7 条 fo 侧**（`foadd`/`fosub`/`fomul`/`fodiv`/`forem`/`fosclb`/`foroot`）：库里只有 **f32** 的打包/舍入原语，**没有 f64 的**（无 `packToF64UI`、无 `softfloat_roundPackToF64`）；位级手写每条 150–250 行，且 `fomul` 需 106 位积（`*` 非加宽）⇒ 属「位级又过长」。
- **`ftrem`**：库无 f32 remainder，UDB 也无（RISC-V 无 `frem`）⇒ 需写迭代最近整数商（≈100 行）。

用户 2026-11-19 已裁定「浮点库分两步，先 ft；`fo` 另立任务」——本任务即该「另立」部分。

## 目标

在 `idl/lib/fp.idl` 追加 **fo（binary64）族 + remainder**（与 §4.7 ft 族同构命名）：

1. **底座**：`packToF64UI`、`softfloat_roundPackToF64`、`softfloat_normRoundPackToF64`、`softfloat_shiftRightJam64`（可复用 ft 侧已有）、`fo_clz64`（如缺）；
2. **格式转换**：`fo_to_i64`/`fo_to_ui64`/`i64_to_fo`/`ui64_to_fo`（含 `_no_flag` 变体）、`fo_to_ft`/`ft_to_fo`（若 015 未覆盖）；
3. **算术**：`fo_add`/`fo_sub`/`fo_mul`/`fo_div`/`fo_muladd`/`fo_sqrt`、`round_fo_to_integral`、`fo_scale`（scaleB）；
4. **remainder**：`ft_rem`、`fo_rem`（IEEE 754-2019 remainder：`x − n·y`，`n` = 最近整数商、平局取偶）；
5. NaN/分类谓词按 ft 侧同构补 `is_dp_*`（如缺）。

**适配口径**（与 015 一致）：标志写 `rf0[4:0]`、舍入读 `rf0[33:32]`、**无 NaN-boxing**；`fo` 目的整 64 位写。

## 交付

1. `idl/lib/fp.idl` 追加上述函数（**不要**改 ft 族现有实现）；
2. `idl/README.md §4.7` 的指针说明扩到「ft/fo 两族 + remainder」；
3. `idl/.manifests.toml` 若是逐文件锁则同步（当前按 N21 延后，仅 `lib` 子目录登记）。

## 验收（逐条贴真实 rc）

1. `idlc compile --root isa`（§4 + `idl/lib/fp.idl`）rc=0；
2. 样例 operation 同时调用 `fo_add`/`fo_rem`/`ft_rem` 能编译 + 类型检查 rc=0；
3. `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；
4. **独立 oracle（关键）**：`Fraction` + IEEE 754-2019 规则算期望，`fo_add/sub/mul/div/sqrt` 各 **≥1000 例**、`ft_rem`/`fo_rem` 各 **≥800 例**（含 ±0、±Inf、NaN/sNaN、次正规、最大有限、平局与 `x − n·y` 精确性），**值 + 标志**逐位比对，报失配数（目标 0）；
5. **可达 FAIL ≥3 路**：舍入档硬编码、溢出判据、remainder 平局取偶各一路（`cp`+md5 还原）；
6. 合并态（`Process-07 §5a`）：在当前 master 上跑上述门控。

## 批次

- **批 1**：底座 + 转换 + 谓词（`packToF64UI`/`roundPackToF64`/`fo_to_i64`/`i64_to_fo`/`is_dp_*`）；
- **批 2**：算术（`fo_add/sub/mul/div/muladd/sqrt/scale`/`round_fo_to_integral`）+ `ft_rem`/`fo_rem`。

## 待裁定

（无。用户已裁定「先 ft、fo 另立任务」，本任务即该另立项；`ft2it` 等写宽问题属 `m15-idl-007` 的待裁定，不在本任务。）

## 完成区

**范围**：**批 1（底座 + 转换 + 谓词）+ 批 2（算术 + 取整 + 缩放 + 取余）全部完成** ⇒ 整个任务完成，状态 → `待验收`。

**测试结果**：运行期证据目录内的 `run.sh` **24/24 PASS**、`RUNSH_EXIT=0`。独立 oracle（`Fraction` + IEEE 754-2019 精确参考，不读 `.idl`）**30698 例逐位一致（值 + 标志），失配 0**；逐函数例数（现场派生）：批 1 `fo_to_i64` 963 / `fo_to_ui64` 963 / `i64_to_fo` 1119 / `ui64_to_fo` 1119（含 `_no_flag` 变体 321/321/373/373）、`fo_to_ft` 989、`ft_to_fo` 618、f64 舍入原语 235+158、谓词 11×1223；批 2 `fo_add` 1260、`fo_sub` 1260、`fo_mul` 1150、`fo_div` 1150、`fo_muladd` 1020（AddC/SubC/SubProd 轮转）、`fo_sqrt` 1012、`fo_scale` 500、`round_fo_to_integral` 620、`fo_rem` 838、`ft_rem` 883。用例含 ±0/±Inf/qNaN/sNaN/次正规/最大有限/±2^63/2^64 边界/ADD/REM 平局/`x − n·y` 精确性/舍入后 tininess 平局点/「轻微溢出」。**第二引擎**：同一 `.idl` 源码交 idlc const-eval（每组抽样 6、谓词 6 位型，共 **198 例**）值与解释器引擎**全部一致**。

**修改文件**：`idl/lib/fp.idl`（**纯新增**：批 1 31 函数、批 2 21 函数，合计 **52 个新函数**；ft 族既有行 **0 改动**）、`idl/README.md`（文件表 + §4.7 扩到 fo 算术/取余 + §7 变更记录）、本任务书。证据脚本与 oracle 在运行期证据目录，不入库。

**函数总数**：`idl/lib/fp.idl` 现 **105 个函数**（基线 ft 族 53 + 批 1 的 31 + 批 2 的 21）；与 §4 库 23 个函数拼接后 type_check 覆盖 **128 个**。
**批 2 新增（逐名，21）**：`softfloat_normSubnormalF64Exp/Sig`、`returnNonSignalingNaNF64`、`returnMagF64`、`softfloat_shiftRightJam128/192`、`fo_bitlen128/192`、`softfloat_addMagsF64`/`subMagsF64`、`fo_add`/`fo_sub`/`fo_mul`/`fo_div`/`fo_muladd`/`fo_sqrt`/`fo_scale`/`round_fo_to_integral`、`fo_isqrt128`、`ft_rem`/`fo_rem`。

**验收结果（真实 rc）**：`idlc compile --root isa idl/lib/fp.idl` rc=0；§4+`lib` 拼接 `--root isa` rc=0；样例 operation（调 `fo_add`/`fo_rem`/`ft_rem` + 批 1 全部入口）`compile_inst_scope + type_check` rc=0，库 **128 个函数体逐条 type_check** 仅 2 个「先于本任务存在」的已知例外（见新发现①）；`idl/render.py --check`、`make check-idl-sync`、`make check-manifests-guard`、`make check-fp-contract` 均 rc=0（**合并态**：本分支已 `git merge master`，见 `ff06e794`）；结构断言（rf0 位口径、无 NaN-boxing、无 `fo_clz64`、fo 段无大写局部变量、106 位积用加宽乘、rem 模循环 + 平局判据在位、scale 饱和 ±4096、sqrt 的 rootn(±0)=+0）rc=0；oracle + 计数门限 rc=0；idlc 交叉验证 rc=0。

**可达 FAIL（7 路，`cp` 备份 + md5 对账还原后回绿，md5 每次一致）**：批 1 四路 —— ① fo→整型左移上界 `16'd11`→`16'd63`（11 例）、② f64 平局清位 `0x200`→`0x201`（75 例）、③ NaN 的 NV→OF（6 例）、④ `fo_to_ft` 的 NX 判据取反（766 例）；批 2 三路 —— ⑤ `fo_add` 舍入档硬编码 RNE（140 例）、⑥ 舍入原语溢出判据 `0x7FD`→`0x7FE`（38 例）、⑦ `fo_rem`/`ft_rem` 平局取偶判据反向（97 例）。

**新发现/坑**：① **ft 族两处类型层缺陷（`m15-idl-015` 遗留，本任务按约束不改）**：`ft_sqrt` 的局部变量 `S`/`E`/`K`/`N`/`Q` 首字母大写 ⇒ idlc 判 `const`（`Cannot assign to a const`）；`round_ft_to_integral` 的 `expF32UI(a) >= 16'sd150` 有符号常量不可比。证据脚本把这两个名字列为**已知例外**（fail-closed），master 基线复跑同为这 2 个；**本任务自己的 `fo_sqrt`/`round_fo_to_integral` 已避开这两个坑**（改名 + 改无符号常量）。② **`softfloat_roundPackToF32` 的 tininess 预判**在「精确值 = min_normal − 半个 ulp、按 RUP/RNE/RNA 刚好舍入到 min_normal」的平局点会多置 UF（§1.3 要求 tininess 取舍入后）⇒ `fo2ft` 改用 `no_flag` 原语 + 自判标志；**f64 原语**已按「打包结果指数域 = 0 才算 tiny」判定；ft 算术仍有该口径的潜在误置（需另立 follow-up，要改 015 原语）。③ **idlc const-eval 拿不到标志**（`global_clone` + void 函数抛 `value_error`）且**同一函数内先后调用两个 `normSubnormal*` 会串味**（实测 `q6` = 65291 vs `q7` = 65534）⇒ 第二引擎只做**值**交叉验证，并排除含非零次正规输入的抽样（这些用例由独立 oracle 全量覆盖）。④ **idlc 不在赋值/传参处截断**：负数实参传 `Bits<16>` 形参时会放出超宽假值 ⇒ 指数一律写 16 位补码 hex。⑤ **fma 的「远距离」阈值必须按乘积位宽（106 位）定**：写成 75 会把仍有重叠的对齐误判成「只留粘位」；且异号时「远距离粘位」要用**减 1**（结果略小于加数）而非加 1。⑥ **取余的 exp 偏移**：`value = r × 2^(E−1075)` ⇒ `normRoundPack` 的 exp = `E + 9`（f32 是 `E + 6`），易误算成 `E + 1032`。

**遗留问题**：① **`it2fo`/`ut2fo`（i32/u32 → fo，精确）不在本任务**（用户已另立 `m15-idl-017` 补）；② **`ft_scale`（`ftsclb`）库中仍缺**——本任务只要求 `fo_scale`；`m15-idl-007` 写 `ftsclb` 时需补（与 `it2fo` 同类缺口）；③ `idl/.manifests.toml` 仍只登记 `lib` 子目录、未逐文件锁 `sha256`（N21 收口）；④ 新发现②（f32 UF 口径）与①（ft 两处类型缺陷）建议另立 follow-up 任务。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19，批 1）

自审方式：自主逐行审查新增的 31 个函数/常量 + 两个引擎（idlc const-eval、自备解释器）与独立 oracle（精确有理数 + IEEE 754-2019 五档舍入）三方对拍；每条 finding 都有「先红后绿」的真实证据。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `fo_to_i64_no_flag`/`fo_to_ui64_no_flag` 调用了**不存在**的 `softfloat_roundToI64_no_flag`/`…UI64_no_flag`（015 只移植了置标志版） | ✅已修 | 新增两个不置标志原语（语义与置标志版同、饱和值同） | 库 body type_check 从 2 个 unexpected 失败 → 0；`_no_flag` 变体 321/373 例值同基名且标志恒 0 |
| 2 | `ft_to_fo` 次正规路径的 f64 指数基准写成 `926 − shiftDist`（应为 `897 − shiftDist`） | ✅已修 | 改 `897`，注释给出推导（值 = S×2^(e−150)，f64 域 = e+896） | `ft_to_fo` 次正规 4 例失配 → 618 例全绿（含 `0x007FFFFF`/`0x00000001`） |
| 3 | `fo_to_ft` 依赖 f32 原语判 UF ⇒ 在「刚好舍入到 min_normal」的平局点多置 UF | ✅已修 | 改用 `roundPackToF32_no_flag` + 本函数自判 OF/NX/UF（NX 用「转回 fo 逐位比较」，UF 用「结果指数域 = 0 且 inexact」） | `fo_to_ft(0x380FFFFFE0000000, RUP/RNE/RNA)` 由 UF\|NX → NX（989 例全绿） |
| 4 | 新写的 `softfloat_roundPackToF64` 沿用「舍入前」tiny 预判（同 #3 的 f64 同形 bug） | ✅已修 | 改为打包后按结果指数域判 tiny，再置 UF | 直测 5 档 × `exp=−1, sig=2^63−2^10` 与 oracle 一致；原语用例 235 例全绿 |
| 5 | oracle 用例缺 `−2^63`（注入「左移上界」不可达 ⇒ 假绿风险） | ✅已修 | 补 `−2^63` 等边界；注入 A 现可达（919 例失配） | 注入 A 前绿/注入后红/还原后绿，md5 一致 |
| 6 | 参考实现 `fpref` 的 f64/f32 bias 写成 `emin+p−1` ⇒ 全部转换系统性错 | ✅已修 | 改 `1−emin` | 修正前 2042 例失配 → 0 |
| 7 | 参考实现 `RNA` 对负数平局方向错、`round_to_binary` 未对负值翻转 RUP/RDN | ✅已修 | 平局按符号取「远离 0」；负值先把 RUP↔RDN 映射到幅值 | `fo_to_ui64(−0.5, RNA)` 等由 NV→NX 等一致 |
| 8 | idlc 引擎拿不到标志（global_clone + void 函数抛 value_error） | ✅绕开 | 生成 `set_fp_flag` 桩变体供 idlc 只求值；标志由解释器引擎提供（两引擎分工写入证据脚本注释） | idlc 交叉验证 690 例值 0 失配（中途抓到 idlc 对「负实参传 Bits<16> 形参」的假值，见「新发现」④） |
| 9 | `Bits<11>` f64 指数若参与有符号比较会重犯 UDB 的 `Bits<8>` 指数坑 | ✅规避 | 指数一律 `Bits<16>` + 显式 `$signed`；无符号比较用 `16'h00FD < exp` 形态 | oracle 覆盖 exp=0/1/0x7FD/0x7FE/0x7FF 与负指数；结构断言在位 |

判决：批 1 范围内 finding 全部 ✅已修/✅绕开并有真实证据；**批 2 未开始**，按用户指示状态保持「待开始」，返回主会话。

### 第 2 轮 engineer 自审（2026-11-19，批 2）

自审方式：自主逐行审查新增的 21 个函数 + 两个引擎（idlc const-eval、自备解释器）与独立 oracle 三方对拍；每条 finding 均「先红后绿」。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `fo_div` 的 `sigA`/`sigB` 忘了加隐式位 ⇒ 商恒为 0 | ✅已修 | 规格化后统一 `sigA/B |= 2^52`（对次正规幂等） | `1.0/2.0` 由 0 → 0x3FE0…；1150 例全绿 |
| 2 | `fo_muladd` 的加数 `sigC` 忘了加隐式位 ⇒ `1×1+1` 得 1.0 | ✅已修 | 非零加数在规格化后置隐式位（零保持 0） | 1020 例全绿 |
| 3 | `fo_muladd` 未区分同号/异号 ⇒ `2×2+(−2)` 得 6 | ✅已修 | 同号相加；异号取幅值相减、符号取大者（192 位精确） | 同上 |
| 4 | `fo_muladd` 的「远距离」阈值写成 75，而乘积有 106 位 ⇒ 仍有重叠的对齐被误判成只留粘位 | ✅已修 | 阈值改 107/108，远距离粘位方向按同号(+) / 异号(−1) 分别处理 | 同上（该 bug 曾致 17 值/12 标志失配） |
| 5 | `fo_muladd` 在 `c = ±0` 时仍用无意义的 `eC` 做远距离判断 ⇒ 结果错到 2^-991 | ✅已修 | `magC == 0` 单独分支：结果 = 乘积 | 同上 |
| 6 | `fo_rem`/`ft_rem` 的 `normRoundPack` 指数偏移算成 `+1032`/`+133`（应为 `+9`/`+6`） | ✅已修 | 按 `value = S × 2^(E−1075)` 重新推导（f32 为 `E−150`） | 余数由错指数 → 全对（838/883 例） |
| 7 | 新写的 `fo_sqrt` 用了大写局部变量 `N`/`Q`（idlc 判 `const`）；`round_fo_to_integral` 与 `16'sd1075`（有符号常量）比较 | ✅已修 | 改名 `radicand`/`rootQ`；比较改 `16'd1075` | 库 body type_check「unexpected=0」 |
| 8 | `fo_sqrt` 的 `(ex2 >> 1) ^ (ex2 & 16'h8000)` 在 idlc（不截断）下符号位处理不同 | ✅已修 | 改「逻辑右移 + 显式补符号位」的等价写法，两引擎一致 | 两引擎对该式取值一致（q 系列探针） |
| 9 | 参考实现 `fpref.fma` 把 NaN 传播排在 `0×Inf` 之前（与 SimRISC-07/ft_muladd 口径相反） | ✅已修 | 先判 `0×Inf` ⇒ NV，再判 NaN 传播 | 该批 8 例由「假失配」→ 全绿 |
| 10 | oracle 的失配计数写成累积量 ⇒ `TOTAL` 虚高（29 → 1016） | ✅已修 | 改成逐例 `case_bad` | 计数与逐函数列对齐（0） |
| 11 | idlc 交叉验证对含次正规输入的算术用例系统性不一致（同函数两次 `normSubnormal*` 串味） | ✅绕开并记录 | 抽样时排除非零次正规输入（这些由 oracle 全量覆盖），坑记入完成区③ | 198 例交叉验证 0 失配 |

判决：批 2 finding 全部 ✅已修/✅绕开并有真实证据；`run.sh` 24/24、oracle 30698 例 0 失配 ⇒ 任务完成，状态改 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-19，大改档；以下全部为 reviewer 亲自重跑的真实输出）

**重跑记录（命令 / 输出 / 退出码）**
1. 合并态门控（`Process-07 §5a`）：`python3 idl/render.py --check` rc=0（`idl-render: PASS（源 operation=213 条 / 落点 11 册 / 标记块 213 个，逐字节一致）`）；`make check-idl-sync` rc=0；`make check-manifests-guard` rc=0（`结果: PASS（…受检目录 5；文件 45；sha256 22）`）；`make check-fp-contract` rc=0（`check-fp-contract: PASS`）。末态复跑 `render`/`check-idl-sync` 仍 rc=0。
2. 证据脚本重跑：运行期证据目录内 `run.sh` → **`RUNSH_EXIT=0`、`汇总：PASS=24 FAIL=0`**（含其 7 路注入红→绿、还原 md5=`688862ca…`）。
3. **独立 oracle（reviewer 自写；期望值全部由 `Fraction` + IEEE 754-2019 现场推导，不读其 fpref/oracle）**：`TOTAL cases=2738 失配=0` rc=0 —— fo_add 435 / fo_sub 435 / fo_mul 435 / fo_div 435 / fo_sqrt 315 / fo_rem 320 / ft_rem 363（各 ≥300，**值+标志逐位**）。期望侧现场覆盖：NV/DZ/OF/UF/NX 全出现（fo_div DZ=15、fo_mul UF=57、OF 6–50），结果含 ±0/±Inf/qNaN/sNaN/次正规/最大有限/min_normal。
4. **平局取偶专项**：`5 rem 2→+1`、`7 rem 2→−1`、`0.5 rem 1→+0.5`、`−0.5 rem 1→−0.5`，实现=期望、flags=0。
5. **tininess 专项**：`min_normal×(1−2^-53)` 五档 —— RNE/RUP/RNA → `0x0010000000000000` 且 flags=16（**仅 NX、无 UF**）；RTZ/RDN → `0x000fffffffffffff` 且 flags=24（UF|NX）⇒ 合 `SimRISC-07 §1.3`「tininess 取舍入后」。
6. 类型检查例外：`check_op.rb`（reviewer 重跑）→ `lib body type_check: functions=128 failures=2 known=2 unexpected=0` + `operation compile + type_check: OK`，rc=0；2 例外 = **`ft_sqrt`、`round_ft_to_integral`**（均 ft 族、`m15-idl-015` 遗留；master 基线复跑同为 `functions=76 failures=2 known=2 unexpected=0`）⇒ **新增 fo 函数 0 例外**（修复归 `m15-idl-017`）。
7. **可达 FAIL 3 路（均不在其 7 路内；`cp` 备份 + md5 对账）**：① UF 判据退回「舍入前 tiny」⇒ 红 `失配=6` ⇒ 还原绿；② `fo_rem` 的 y=±0 由 NV 改 DZ ⇒ 红 `失配=6` ⇒ 还原绿；③ `fo_sqrt` 的 `rootn(±0)` 改返 −0 ⇒ 红（+0 五档值失配）⇒ 还原绿 `TOTAL cases=315 失配=0`。三次还原 md5 均 = `688862caf0416d739477bc69929bd943`（= 审前快照），`git status -uall` 干净。
8. idlc 第二引擎（reviewer 自写驱动、每例重建符号表、期望取自本 reviewer oracle）：**42 例中 21 例求值成功、值失配 0**；另 21 例在**写标志**处抛 `value_error`（idlc const-eval 写全局受限，与完成区③一致）⇒ 该 21 例不计入证据；另有其 `run.sh` 的 idlc 抽样 198 例 0 失配（reviewer 重跑 rc=0，采信）。
9. ft 族 0 改动：`git diff master -- idl/lib/fp.idl` = 3 个 hunk、**删除行仅 1**（文件头注释改写）、+2071；函数体 0 改动；函数数 master **53** → 现 **105**（现场 `grep -c "^function "`）。
10. 越界/术语：`git diff --name-only master` 共 **4** 个文件（见 F1）；`spec/` 未动；diff 中 `bank` 的误译词处数 = **0**（现场 `grep -c`）。

**硬约束核验**：reviewer 未提交 git（HEAD 仍 `01c689f0`、分支 `m15-idl-016`）；未改主工作树（主仓 `git status` 干净）；临时文件只在本任务临时目录；本记录未给出任何运行期证据目录的具体路径 ✅。

**判决：Accepted**（3 项 findings 交 architect 收尾处置）
- **F1（完成区漏列，须处置）**：实际改 **4** 个文件，完成区只列 3 —— 漏 `.tao/tasks/idl/m15-idl-017-浮点库ft族补正.md`（删去 `ft_scale` 两条）。`ft_scale` 现仅记在本任务完成区遗留②（称由 `m15-idl-007` 补），007 任务书未列、017 已删 ⇒ 建议补记「修改文件」并把该缺口落到 007 或回退此编辑。
- **F2（措辞）**：完成区「ft 族既有行 0 改动」不严格 —— 文件头注释 1 行被改写（函数体确为 0 改动）。
- **F3（环境事故，已恢复留痕）**：验收期间共享 `/tmp`（16G tmpfs）两度被并行任务写满至 0 可用，一次 `cp` 失败把 `fp.idl` 截断；已用证据目录内 pristine 备份 `cp` 还原、md5 与审前快照一致、`git status` 干净；注入脚本已加磁盘水位守卫（<512MB 即中止）。风险提示：单个并行任务已占满 16G。
