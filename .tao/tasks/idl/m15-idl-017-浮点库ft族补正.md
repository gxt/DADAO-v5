# m15-idl-017: 浮点库 ft 族补正（tininess 口径 / 两处类型缺陷 / i32·u32→fo）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-015`（ft 族 53 函数）、`m15-idl-016`（fo 族；批 1 已交付）
**可并行分片**：否（与 `m15-idl-007`/`016` 同改 `idl/lib/fp.idl`，串行）
**预估**：3–4 h
**档位**：中改
**状态**：待验收

## 背景（`m15-idl-016` 批 1 交付时发现的 015 遗留缺陷）

1. **tininess 口径缺陷（语义类）**：`softfloat_roundPackToF32` 的「下溢预判」在边界上错——
   精确值 = `min_normal − ulp/2`、按 RUP/RNE/RNA **恰好舍入到 `min_normal`** 时，它**多置 `UF`**。
   `SimRISC-07 §1.3` 要求 tininess **取舍入之后**（IEEE 754-2019 §7.5）⇒ 该情形**不应置 UF**。
   现状：`fo2ft` 已绕开（用 `no_flag` 原语 + 自判 OF/NX/UF），**新写的 f64 原语已正确**；
   但 **ft 算术仍受影响**（`ft_add`/`ft_sub`/`ft_mul`/`ft_div`/`ft_sqrt`/`ft_muladd`）。
2. **两处类型层缺陷（实现类）**：
   - `ft_sqrt` 用 `S`/`E` 作变量名，首字母大写被 idlc 当**常量** ⇒ `Cannot assign to a const`；
   - `round_ft_to_integral` 里 `Bits<8>` 与 `16'sd150` **不可比较**。
   现状：`check_op.rb` 把它们设为「已知例外」（fail-closed），等于**类型检查被绕过**。
3. **缺 `i32_to_fo` / `ui32_to_fo`**：`it2fo`/`ut2fo`（§1.2 三条精确转换）需要它们，库中暂无。
4. **缺 `ft_scale`（`ftsclb` 用）**：`016` 只做了 `fo_scale`（f64）；`007` 的 `ftsclb`（S2D1 缩放）需要 f32 版。与 3. 同批补。

## 要做

1. **修 tininess**：`softfloat_roundPackToF32`（及其 `_no_flag` 变体）改为「**先舍入、后判 tininess**」，与 f64 侧同口径；**不要**为了省事把 ft 算术一律改走 `no_flag` + 手判（那会让 6 个函数重复逻辑）。
2. **修两处类型缺陷**：`ft_sqrt` 的 `S`/`E` 改名（小写或语义名）；`round_ft_to_integral` 的比较改为同宽（`Bits<8>` ↔ `Bits<8>`，或显式类型求解确认）。
3. **补 `i32_to_fo` / `ui32_to_fo`**（与 `i32_to_ft`/`ui32_to_ft` 同构，精确转换、不置标志），供 `it2fo`/`ut2fo` 使用；同批补 **`ft_scale`**（f32 scaleB，语义与 `016` 的 `fo_scale` 同构：指数饱和 ±252 或按 `SimRISC-07` 定值，须核散文）。
4. **撤掉 `check_op.rb` 的两条「已知例外」**，让 107 个函数体**全部**通过 type_check（撤掉后应 0 例外）。

## 验收（逐条贴真实 rc）

1. `idlc compile --root isa` rc=0；**107 个函数体逐条 `type_check` 全 PASS、例外数 0**（现场统计，不写死）；
2. **tininess 定向用例**：构造「舍入后正好 = `min_normal`」的三档（RUP/RNE/RNA）与「舍入后仍 < `min_normal`」三档，各断言 `UF` 的有无；**修前红、修后绿**（给前后对照）；
3. **oracle 回归**：重跑 ft 算术 5 个函数的 oracle（≥1000 例/函数，`Fraction` + IEEE 规则），失配 0；并确认「修 tininess」**没有**改变正常区间的结果（对比修前修后全量输出，差异只应出现在边界档）；
4. `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；合并态（`Process-07 §5a`）再跑一次；
5. 可达 FAIL ≥2 路（① 把 tininess 改回预判 ⇒ 定向用例红；② 把 `i32_to_fo` 的舍入档写死 ⇒ oracle 红），`cp`+md5 还原。

## 待裁定

（无。三项缺陷均有明确真源：IEEE 754-2019 §7.5 + `SimRISC-07 §1.3` + idlc 类型系统报错。）

## 完成区

**范围**：四项缺陷全部落地 —— ① f32 舍入原语的 tininess 改「**舍入后**」检测；② `ft_sqrt`/`round_ft_to_integral` 的类型层缺陷修掉（并撤掉「已知例外」，例外数 0）；③ 补 `i32_to_fo`/`ui32_to_fo`（精确转换）；④ 补 `ft_scale`（scaleB，与 `fo_scale` 同构）。`idl/lib/fp.idl` 函数数 **105 → 108**（现场 `grep -c "^function "`）。

**测试结果**：运行期证据目录内的 `run.sh` **38/38 PASS、`RUNSH_EXIT=0`**（含 3 路注入红→绿）。逐项真实输出：① `idlc compile --root isa`（lib 单文件、§4+lib 拼接）rc=0；**函数体逐条 type_check：`functions=108 failures=0 known=0 unexpected=0`**（现场统计；样例 operation 调 `ft_scale`/`i32_to_fo`/`ui32_to_fo`/`ft_sqrt` 等 **5/5** 编译+type_check）。② tininess 定向 **30 例**：A 组「精确值 = min_normal − ulp/2」RUP/RNE/RNA ⇒ 值 `0x00800000`、标志仅 NX（**无 UF**），RTZ/RDN ⇒ `0x007FFFFF`+UF|NX；B 组「仍 < min_normal」五档全 UF|NX；C（max_subnormal）/E（min_normal）对照组无标志；D 组同一平局点经 `ft_div` 同结论；F 组为负号同点（RDN 等效正号 RUP）。**修前 A/D/F 共九例多置 UF（`0x18` vs `0x10`）**。③ 独立 oracle（`Fraction`+IEEE 规则）`ft_add/sub/mul/div` 各 1408、`ft_sqrt` 1100、`ft_muladd` 1108、`ft_scale` 700、`i32_to_fo`/`ui32_to_fo` 各 607、`round_ft_to_integral` 400 ⇒ **TOTAL=10154 失配 0**（值+标志逐位）；第二 oracle（仓内 spec-exact 模型 `tools/chipyard/fp_ref.py`，`ft_add/sub/mul/div/sqrt`）与期望侧互证 **6732 例失配 0**。④ 修前/修后**全量**输出对比（同一 8240 例）：**11 行差异，全部只有 UF 位、值位型相同、精确幅值 < 2^-126**（ft_mul 10 / ft_div 1）⇒ 正常区间 0 变化（修前失配也正是这 11 例）。⑤ `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` 全 rc=0；**合并态**（已 `git merge master`，FF 到台账提交）复跑 `run.sh` 仍 **38/38**。

**修改文件**：`idl/lib/fp.idl`（tininess 口径 + `ft_sqrt` 改名/移位改法 + `round_ft_to_integral` 同宽比较 + 新增 `ft_scale`/`i32_to_fo`/`ui32_to_fo` + 3 处过时注释）、`idl/README.md`（§4.7 覆盖范围与口径③④、§7 变更记录）、本任务书。库/README 的改动已由 architect 提交在 `2cb3f8e7`；**engineer 未提交 git**，返工 1 的证据脚本与本任务书改动留在工作树（`git status -uall` 只列本任务书）。

**可达 FAIL（3 路；`cp` 备份 + md5 对账还原，三次 md5 均回 `a92bf4d9…`）**：① UF 判据退回「舍入前预判」⇒ 定向用例 **9 例红**；② `i32_to_fo` 的规格化移位写死 `<< 21` ⇒ oracle **605/607 失配**；③ `ft_scale` 打包移位写死 `<< 6` ⇒ oracle **287 失配**。三路均「注入 md5 变（`4c0b5096`/`66f5359f`/`62c06bc5`）⇒ 目标检查红 ⇒ cp 还原 md5 一致 ⇒ 回绿」。

**新发现/坑**：① `ft_sqrt` 其实有**两个**类型缺陷：大写变量名之外，``m `<< twoK`` 的**加宽左移要求移位数是编译期常量**（idlc 报 "Widening shift amount must be constant"），改名后第二个才暴露 ⇒ 改成「零扩展到 64 位 + 普通左移」（m<2^25、twoK≤38 ⇒ 值等价）。② `…_no_flag` 变体**没有** tininess 逻辑（不置任何标志）⇒ 任务书「及其 `_no_flag` 变体」在实现上等价于只改置标志版本，已在 description 写明。③ **f32 roundPack 的被舍入值 = `sig × 2^(exp − 156)`**（sig 31 位、MSB 在 bit30）⇒ scaleB 传 `expZ = (E − 1) + n`（与 `fo_scale` 同构），极易误写成 −150/−157。④ **idlc const-eval 不能当 oracle**：实测 `ft_add(2^23, 1.0)` 得 0、`ft_mul(2^23, 2^23)` 得 0、`ft_div(10.0, 2.0)` 抛 ZeroDivisionError（并伴随 "value was truncated" 告警）⇒ 对拍改为「自写 interp（按 `doc/idl.adoc` 的 `Bits<N>` 语义）+ 两个独立 oracle」，const-eval 只作旁证。⑤ 对拍抓到**我自己 oracle** 两处错：`(+0)+(+0)` 在 RDN 下误判 −0（IEEE §6.3：同号零保留原符号）、roundToIntegral 对负数把 RUP/RDN 套在幅值上（方向反）——分别由第二 oracle 与实现反证后修正。⑥ `/tmp`（16G tmpfs）本任务期间被并行任务打满 3 次（一次 write 失败）；证据脚本已加「可用 < 512 MiB 即中止」守卫，源文件每次注入后 md5 复核。

**返工 1（reviewer Needs Revision 唯一项）**：证据脚本的基线锚点由 `HEAD` 改为**固定引用**（`git show 0be92a40:idl/lib/fp.idl` + 常量 md5 `688862ca…`）——原写法在任务提交后把「修前基线」变成「修后文件」⇒ `baseline_snapshot` 恒红（`PASS=37 FAIL=1`）。改后重跑 **PASS=38 FAIL=0、`RUNSH_EXIT=0`**（当前 HEAD `2cb3f8e7` 已含本任务提交，仍绿）；全库证据脚本再无 `HEAD`/`git log -1` 用法。库代码与判据未动。

**遗留问题**：① 任务书正文写「107 个函数体」，实际为 **108**（105 + `i32_to_fo` + `ui32_to_fo` + `ft_scale`，少算 1 个）；验收按任务书「现场统计」口径执行。② L1 `make -k check` 有 6 项红，**均非本任务引入**：`check-case-ledger` 在 master 主工作树复跑同样红（LLVM lit 台账 `gen-rrii.s` 4 行偏移 `09004`↔`09001`）；`check-components`/`check-width-sizes`/`check-linux-toolchain`/`check-writer-guards` 因本任务 worktree 无 `.dadao/` 交叉工具链与共享安装根；`check-temp-dirs` 报他任务（`m14-linux-*`）陈旧目录。L2 未跑：`check-modules` 前置 `install-host`，并行窗口内禁跑。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19，中改档）

自审方式：自主逐行审查改动 + 三方对拍（自写 interp / Fraction oracle / 仓内 `fp_ref`）+ 定向用例与注入；每条 finding 都有「先红后绿」的真实输出。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `ft_sqrt` 除了大写变量名，``m `<< twoK`` 还违反「加宽左移移位数须为编译期常量」（改名后才暴露） | ✅已修 | 改「`{32'h0, m}` 零扩展到 64 位 + 普通左移」 | type_check 108/108 PASS；`ft_sqrt` 1100 例 oracle 0 失配 |
| 2 | 任务书要求「及 `_no_flag` 变体同改」，而该变体不置任何标志（没有 tininess 逻辑） | ✅确认无需改（写明理由） | 补 description | 与 f64 侧 `…_no_flag` 同构；经 `_no_flag` 的路径由 oracle 覆盖 |
| 3 | 我的 oracle 把 `(+0)+(+0)` 在 RDN 下判成 −0（应保留同号零的符号） | ✅已修 | 和为精确零时同号保留符号 | 第二 oracle 互证 6732 例 0 失配 |
| 4 | 我的 oracle 对 roundToIntegral 的负数把 RUP/RDN 套在幅值上（方向反） | ✅已修 | 按符号映射 RUP/RDN | 新增 `round_ft_to_integral` 400 例 0 失配 |
| 5 | 只改原语的 UF 判据是否会动正常区间？ | ✅已证不动 | — | 修前/修后 8240 例：差异 11 行、全为 UF 位、精确值 < 2^-126 |
| 6 | 三条注入是否可达（防空注入/恒真） | ✅3 路均可达 | — | 9 例红 / 605 失配 / 287 失配；md5 变 → 红 → 还原 → 回绿 |
| 7 | 越界：是否只动任务书范围 | ✅未越界 | — | `git status -uall` = `idl/lib/fp.idl` + `idl/README.md` + 本任务书；`spec/` 未动 |
| 8 | 「首字母大写 = 常量」是否还有残留局部变量 | ✅无 | — | 全库大写局部声明 = 0（20 条均为全局常量） |
| 9 | `i32_to_fo` 的 `-a` 若在 64 位做会得 `2^64 − a` | ✅按 32 位取补后再零扩展 | 先 `Bits<32> absA32` | `i32_to_fo` 607 例（含 `−2^31`/`0xFFFFFFFF`）0 失配 |

判决：全部 finding 已修/已确认并有真实证据 ⇒ 任务完成，状态改 `待验收`，返回主会话。

### 第 2 轮 engineer 自审（2026-11-19，返工：reviewer Needs Revision 唯一项）

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 证据脚本把 `git show HEAD:idl/lib/fp.idl` 当「修前基线」：本任务提交后 HEAD 已是修后文件 ⇒ `baseline_snapshot` 恒红（reviewer 实测 `PASS=37 FAIL=1`、`RUNSH_EXIT=1`；`ISS-475` 同类） | ✅已修 | 锚点改**固定引用**：`BASE_COMMIT=0be92a40`（开工时 master）+ `BASE_MD5=688862ca…`；同时断言快照文件与该提交 blob 的 md5 | 当前 HEAD `2cb3f8e7`（已含本任务提交）下重跑 `run.sh` ⇒ **PASS=38 FAIL=0、`RUNSH_EXIT=0`**；`baseline_snapshot` 实测「快照 / 该提交」两侧 md5 均 `688862ca…` |
| 2 | 同类隐患自查：脚本里是否别处用 `HEAD`/`git log -1` 当基线 | ✅无残留 | — | `grep -n "git \|HEAD" run.sh *.py *.rb` 仅命中注释（`run.sh` 的固定引用段），无其它 git 调用 |
| 3 | 返工是否动了库代码/判据 | ✅未动 | — | `git status -uall` = 仅本任务书；`idl/lib/fp.idl` md5 仍 `a92bf4d9…` |

判决：唯一 finding 已修并复验 ⇒ 状态保持 `待验收`，返回主会话重新 `/complete`。

### 第 1 轮 reviewer 验收（2026-11-19，中改档；判决 = **Needs Revision**）

**重跑（全部本人执行，真实 rc）**
1. 运行期证据目录内 `run.sh` ⇒ `汇总：PASS=37 FAIL=1`、`RUNSH_EXIT=1`：唯一红 = `baseline_snapshot`（修前快照 md5=`688862ca…` vs `git show HEAD:idl/lib/fp.idl`=`a92bf4d9…`；`HEAD^` 版=`688862ca…` ⇒ 快照本身对、比对目标错）。其余 37 项 PASS：`type_check functions=108 failures=0 known=0 unexpected=0`、tininess 30/0、其 oracle `TOTAL=10154 失配=0`、双 oracle `6732/0`、修前修后 `8240 例/11 行/违规=0`、3 路注入红→还原→回绿、4 门控 rc=0。
2. **独立 oracle**（Fraction + IEEE-754-2019 自算，种子 202611192026；不复用其 fporacle/oracle_ft；执行机器只跑实现，`set_fp_flag` 是「把实现请求的枚举值 OR 进标志」的通用机制、无按函数硬编码）：`ft_add/sub/mul/div/sqrt` 各 **320**、`ft_scale` **240**、`i32_to_fo`/`ui32_to_fo` 各 **220**、零符号定向 30 ⇒ **`TOTAL=2280 失配=0`**（值+标志逐位）。
3. **tininess 定向（期望自算）**：平局 `ft_mul(0x00000FFF, 0x45000800)`（精确 = (2²⁴−1)·2⁻¹⁵⁰）RUP/RNE/RNA ⇒ `0x00800000`+仅 NX、**无 UF**；`ft_mul(0x017FFFFD, 0x3E800000)`（= (2²⁴−3)·2⁻¹⁵⁰）与 `ft_div(0x00FFFFFD, 2.0)` 五档全 `UF|NX`；负号平局同构 ⇒ **20/20 PASS**；同批跑修前快照 ⇒ 平局 6 例 `0x18` vs `0x10` **修前红**。
4. **正常区间 0 变化（独立复核）**：我自造 1600 例随机集跑修前快照 ⇒ 失配 1、分类「仅多置 UF」=1、**其它差异=0**（值位型全同）⇒ 与完成区 8240 例 11 行仅 UF 的结论一致。
5. **我的 2 路注入（均不在其 3 路内）**：① `i32_to_fo` 指数偏置去掉 `-1` ⇒ 我的 oracle `i32_to_fo 失配 217`、exit=1；② `round_ft_to_integral` 比较改回 `16'sd150` ⇒ type_check `failures=1`、exit=1；两次均 `cp` 备份 + md5（`a92bf4d9…`→注入变→还原回 `a92bf4d9…`）⇒ 回绿 exit=0。
6. **门控/合并态**：`idl/render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` 独立重跑全 **rc=0**；`check-case-ledger` 在含 `344be697` 的新 master 两次 **PASS、exit=0**（现场 5670 条）。
7. **idlc const-eval 独立抽测 10 例**：可算的 4 例（`ft_add(2²³,1.0)`、`ft_sub(1,1,RDN)`、`i32_to_fo(-2³¹)`、`ui32_to_fo(0xFFFF_FFFF)`）与本 oracle 全一致；另 6 例 `ft_mul`/`ft_scale` 返 0、`ft_div` 抛 `ZeroDivisionError`、`sqrt`/溢出例返 Symbol，`rf0` 恒不可读 ⇒ 复现其坑④，**idlc 不可作执行机**（值侧由解释执行取得，已按上述交叉印证）。

**约束核验**
- 六函数：`ft_add/sub/mul/div/muladd` **函数体逐字节相同**（逐函数提取比对 md5 一致）；`ft_sqrt` 仅类型层三处（`S/E→sigS/expS`；``m `<< twoK`` → `{32'h0,m}` 零扩展+普通左移，`m<2²⁵`、`twoK∈{36,38}` ⇒ `m·2^twoK<2⁶³` **值等价**；`16'sd150→16'd150` 模 2¹⁶ 同值）。UF 判据 `isTiny && roundBits≠0 && z[30:23]==0` **在打包之后**，且相对修前**只可能少置 UF**（z 指数域非 0 即正规）⇒ 正常区间逻辑上不可能变（已实测）。
- 类型两处已修且承重（注入②实证）；三新函数语义经独立 oracle；`check_op.rb` 不带 `--expect-fail`，函数数现场统计 `grep -c "^function "` = **108**、0 例外（本人重跑）。改动 = 3 文件（`idl/lib/fp.idl`、`idl/README.md`、本任务书），`spec/` 未动；验收前后 `git status -uall` 干净、注入 md5 全回 `a92bf4d9…`；主工作树只跑只读门控、状态干净；本人未提交 git。
- **采信边界**：其证据脚本逐条审过（计数现场统计、3 路注入有可达 FAIL 且实证红→绿；`baseline_snapshot` 是唯一缺陷）；仓内既有模型 `tools/chipyard/fp_ref.py` 只重跑其结论（`6732/0`）未审码；8240 例前后对比为其脚本产出，我以自造 1600 例独立复核同结论。

**判决：Needs Revision**
- 失败项（唯一）：运行期证据目录内 `run.sh` 的 `baseline_snapshot` 断言拿 `git show HEAD:<库文件>` 与修前快照比对 ⇒ **提交后恒红**（AGENTS.md「提交后仍须回绿」同类反例），我重跑 `RUNSH_EXIT=1`，完成区「38/38、`RUNSH_EXIT=0`」在交付 HEAD 上不复现。
- 修改建议：该行比对目标改为**固定基线**（任务基线提交 `0be92a40`，或写入基线 md5 常量 `688862ca…`），改后重跑应 `PASS=38`、`RUNSH_EXIT=0`；完成区相应数字按重跑结果对齐。
- 四项交付经我独立 oracle/定向/注入/门控验证**均已达标**；返工仅此一处单行脚本修正 + 数字对齐。

