# m13-gem5-007: `fo2ft` 溢出按 IEEE 舍入模式（gem5）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-002`（spec 定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 背景（共同，5 个子任务共用）

用户 2026-11-12 定规则（`MEMORY.md`）：**浮点差分一律以 IEEE-754 2019 为准**。

**条款**：`fo2ft` 溢出。现行：恒 ±Inf + `OF|NX`。IEEE 754-2019 §7.4：`RNE`/`RUP` ⇒ ±Inf；`RTZ`/`RDN` ⇒ ±最大有限；均置 `OF|NX`。

## 本任务目标（只改 gem5）

1. gem5 侧 `fo2ft` 实现按 `rf0[33:32]` 舍入模式分派溢出结果；标志保持 `OF|NX`。
2. 与 `m13-spec-002` 定稿逐条对齐。
3. gem5 checker（`tools/gem5/`）若断言了「恒 ±Inf」，同步更新。

## 非范围

- chipyard / QEMU / 向量册

## 验收标准

1. 四档 × 正负溢出逐条给输出（值 + `rf0`）
2. 与 chipyard/QEMU（合入后）逐字节一致；未合入时与 hardfloat 模型对照
3. gem5 侧既有回归（`check_tiny_hmon` 等）rc=0；273 例 md5 不变
4. **可达 FAIL 注入**：改回「恒 ±Inf」⇒ RTZ/RDN 例红 ⇒ `cp`+md5 还原回绿
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- `.work` 必须软链（`ISS-389`）；gem5 重建较慢，先申报耗时。
- 无外网节点不可用于 gem5 构建（依赖 scons/python 包），构建留主控机。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-12）

- **改动逐行**：`b7.cc::runConvertFF` 只删掉 `if (result.flags & fp::OF)` 的 ±Inf 覆盖块（−11 行），改为 `const fp::Val result = fp::convert(...)` 直用 `roundPack→overflowBits` 的方向结果；`raw` 仍被 `value` 使用（无未用变量），`-Wall -Wextra -Werror` 全绿。`b7_test.cc` 新增 18 格表驱动断言（6 档 × 正负 + 动态 4 档 × 正负），每格校验值与 `rf0[4:0]` 双字段；`b7_ref.py` 与 spec 表同步并补 18 格向量。`ft2fo`/f2i/i2f/算术/比较/取整路径零改动（`git -C .work/source/gem5 diff --stat` = 2 文件）。
- **自审发现（均已处置）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `b7_test.cc` 18 格循环把 `w` 整体重置，紧随其后的「tiny+inexact」用例变成依赖残留 `immu6`（实际落到 RDN） | ✅已修 | 该块前显式 `w.immu6 = 0x20`，恢复原意（动态=RNE） | `check_b7` rc=0、`[FAIL]` 0 条；tiny 用例仍 `UF\|NX` |
| F2 `b7_ref.py::_overflow_bits` 用 `return encode(1e400)`：既返回 `(bits,flags)` 元组又自递归，`_encode_rna` 调用点会把元组当真值（RNA 溢出必崩/必错） | ✅已修 | 改为按方向直接构造 ±Inf / ±largest，`op_sclb`/`_pack_significand` 调用点补 `OF\|NX` | 新 RNA 向量由 `TypeError` 转 `0x7f800000/0x14`；`oracle vectors=3998 mismatch=0` |
| F3 `conv_mode` 不认动态码 `0x20`（docstring 已写「0x20 = rf0」但实现缺分支），cvt_ff 首次用动态向量即 `AssertionError` | ✅已修 | `code == 0x20` 直接返回 `rf_mode` | 动态 8 格全 PASS |
| F4 证据脚本 id/列约定不一致：probe 叫 `of-<slug>`、manifest 是 5 列，导致三处比较假红 | ✅已修 | `compare_tsv.py` 加 id 归一 + 3/5 列自适应；`gen_vectors.py` 期望文件按 `of-<slug>` 与 case id 双拼写查找 | `run.sh` 末轮 `PASS=27 FAIL=0`、rc=0 |
| F5 删掉覆盖块后 `sign` 局部变量悬空 | ✅已修 | 随覆盖块一并删除（编译 `-Werror` 印证） | `check_b7` 编译段 rc=0 |

- **可失败性**：注入「恒 ±Inf」→ harness 红 8 断言、probe 红格恰 8 个（RTZ±、RUP−、RDN+、动态 01±/10+/11−）；还原后 19/19 回绿（`cp`+md5+`touch`）。
- **范围/纪律**：只动任务书范围（gem5 源 2 文件 + `tools/gem5/b7_ref.py` + 组件 changelog + 本任务书）；未 commit/push、未动台账；组件源按 E1 收敛为 base+1（HEAD `dc1412a0`）。
- **无未修 finding**，状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-12）

**重跑记录（全部本人执行，退出码现场取）**
- 一键证据脚本连跑 2 次：`PASS=27 FAIL=0`，两次 rc=0（第二次显式落 `RC=0`）。现场值：`B7 coverage 55/55, failures 0`、`oracle vectors=3998`、`oracle mismatch=0`、`cross-check disagreements=0`、fo2ft overflow `19/19`、`[FAIL]` 0 条；probe 18 格全 `0x14`（=OF bit2|NX bit4，UF bit3=0），控制例 `0x3FC00000/0x00`；QEMU 合入版 `Results: 19 total, 19 passed`，钉 gem5 实测值再跑仍 19/19；改前基线 `11 passed, 8 failed`，红格 `4 5 7 8 12 13 14 17`；`check-gem5-decode` rc=0、`check_tiny_hmon` rc=0（`PASS (209 checks, 44 records)`）、273 sweep md5 `2d4d9465…` 不变、L2 `make check-modules` rc=0。
- 18 格逐格对 `SimRISC-07 §1.4` 表（含负数交叉格 RTZ−/RUP−/RDN−/动态四负）：值与标志全对。
- 本人独立注入（与脚本不同点）：`fp_soft.cc::overflowBits` 让 RDN 正向也回 `+Inf` ⇒ 源 md5 `0a25487c…`→`01e86623…`、`check_b7` rc=1、恰 2 条 `[FAIL] fo2ft overflow`（`RDN +`、`dyn=10 RDN +`）、probe `compare_tsv` rc=1 且红格恰 `of-pos-rdn of-pos-dyn-rdn`；`cp`+md5 还原回 `0a25487c…`、标记 0、`check_b7` rc=0、probe 0 mismatch、组件源干净。
- 轻微溢出独立实测（源 `0x47EFFFFFE0000002` = ft_max+2^76，小于中点 k）：gem5 8 格 = 手推 IEEE 期望 —— 正向 RNE/RTZ/RDN 与负向 RNE/RTZ/RUP 给 `±ft_max` 且**只置 NX `0x10`**，RUP 正 / RDN 负给 `±Inf` + `OF|NX 0x14`；同 8 例 QEMU `Results: 8 total, 8 passed` rc=0 ⇒ 两实现逐字节一致。
- 三处「既有缺陷」安全性（旧版取回比对）：3980 条既有向量**零异常、仅 4 条期望变化**（`fo2ft` RTZ±/RDN+ 由 `±Inf`→`±ft_max`，是规范变更本身、非回归）；`_overflow_bits` 在 mode 0–3 旧新 bits/flags 完全相同，仅 RNA(4) 旧返回被再包一层的嵌套元组；`conv_mode(0x20)` 旧抛 `AssertionError` 而既有向量 0 例用到 ⇒ 两处修复对既有结论零影响。
- 门控：`make -k check` + 缺名 14 项逐项补跑共 52 项 ⇒ **48/52 rc=0、4 项 rc=2**：`check-patch-tree`（chipyard 4 / gem5 0）、`check-run-artifacts`（55 命中全他任务）、`check-temp-dirs`（5 条全他任务）、**`check-knowledge-refs` rc=2，唯一命中 = 完成区门控段落里的 `.work/log/*` 具体路径（本记录插入后门控报 line 105，插入前为 line 87）**。
- 纪律：验收前后 `git status --porcelain -uall` 除本任务书（本记录写入）外为空；HEAD 仍 `2a094a40`（architect 的 WIP，engineer 未 commit）；engineer 5 文件 md5 与开审快照逐一相同；组件源 base+1 `dc1412a` 干净；完成区 26 行 ≤30。

**约束核验**：验收 1–4 全过（四档×正负逐条输出、与 QEMU 逐字节、既有回归 rc=0 + 273 md5、注入可达 FAIL 且还原回绿）；验收 5 与硬约束 3「完成区与真实输出逐条对齐」**不达标**；硬约束 1/2/4/6/8 守住，未越界改文件、未 commit。

**判决：Needs Revision**（唯一阻断点 = 任务书 2 处措辞 + 复跑 1 项门控；实现与测试侧全绿）
1. **阻断 A（门控/退出码）**：`make check-knowledge-refs` rc=2，唯一命中是完成区门控段落里的具体 `.work/log/*` 路径（ISS-352、用户 2026-11-08 裁定 A：任务书内具体 `.work/**` 一律 FAIL）。改法：该句改成不含具体 `.work/` 路径的措辞（任务号可留），复跑该门控期望 rc=0。
2. **阻断 B（计数）**：完成区「L1 逐项 49/52 rc=0」与实跑不符（实为 48/52、4 项 rc=2，且漏列 `check-knowledge-refs`）；修 A 后按复跑真实值重写该句。
3. 非阻断 finding：① 18 格全为严重溢出、无「轻微溢出仅置 NX」格 —— IEEE 754-2019 §7.4 原文判该类格**应存在**，但已由 `m13-testcases-011`（待开始，验收含「轻微+严重 ≥ 8 例」三方对照）承接，且两实现 round-then-compare 实测正确，不阻断；② 审阅记录 F2「`_overflow_bits` 自递归」措辞不实：实测无 `RecursionError`（`encode` 委托独立 oracle 模块），真实缺陷是返回元组并在 RNA 调用点被再包一层（`((0x7F800000,0x14),0x14)`）；「须修」结论成立，建议改措辞。

### 第 2 轮 reviewer 验收（2026-11-12）

**重跑（本人执行，退出码现场取）**
- `make -s check-knowledge-refs` ⇒ **rc=0**，`结果: PASS (0 具体 .work/** 引用; 0 悬空小节级互指…)`（阻断 A 解除）。
- `git grep -n`（模式 = `.work/` 后接 `log`）于本任务书 ⇒ **2 命中，不是 0**：两处都在**本人第 1 轮记录**内，且都是**通配形**（路径以 `*` 结尾），属规则豁免形、检查器同判「0 具体引用」。要拿到字面 0 只能改写既有审阅记录，与「不改写既有审阅记录」冲突 ⇒ 留 architect 定夺，**门控判据已绿，不作阻断**。
- L1 现场重数：`Makefile` `_locked-check` 成员 = **52**（现场抽行计数）；`make -k check` + 对日志中未具名的 14 项逐项补跑（全 rc=0）⇒ **49/52 rc=0、3 项 rc=2**（`check-patch-tree` / `check-run-artifacts` / `check-temp-dirs`），与完成区一致；engineer 的逐项 rc 清单（运行期日志目录）52 行 / 3 红，其首轮清单 4 红（含 `check-knowledge-refs`），与我第 1 轮 48/52 吻合。
- 三项红归属复核：patch-tree 4 条全 `chipyard:`、`gem5:` 0；run-artifacts 55 条命中中本任务 0（其中 2 条同目录条目属 `m13-gem5-004` 与 `check.log`）；temp-dirs 5 条 mtime 19.0–50.9 h 全他任务、本任务为活动 worktree 未计入。
- `make -s check-modules`（L2）⇒ **rc=0**（`module checks (L2): PASS`）。
- 一键证据脚本本轮**再跑一次** ⇒ `PASS=27 FAIL=0`、**rc=0**（`B7 coverage 55/55`、`oracle vectors=3998 mismatch=0`、QEMU 双向 19/19、改前基线恰 8 格红、`check_tiny_hmon PASS (209 checks, 44 records)`、273 sweep md5 `2d4d9465…` 不变、注入 8 红→还原回绿）；4 个非任务书交付物 md5 与第 1 轮逐字节相同 ⇒ 第 1 轮的实现侧结论继续成立。
- 范围：`git show --stat 22e8537d` 与 `git diff --stat 2a094a40..22e8537d` **均只含本任务书**（42+/2−）；开审时工作树干净；4 个非任务书交付物 md5 与第 1 轮快照逐一相同；组件源 base+1 `dc1412a` 干净、`b7.cc`/`fp_soft.cc` md5 未变；HEAD `22e8537d`（architect 提交），**engineer 本轮零代码改动** ✓。

**约束核验**：阻断 A（门控 rc）已解；阻断 B（计数）已按现场重写且与我独立重跑逐条吻合；非阻断①已落实（完成区明写「18 格全为严重溢出、无轻微溢出格 ⇒ **不宣称 OF 语义已全覆盖**，由 `m13-testcases-011` 承接」）；非阻断②已落实（`_overflow_bits` 改为「返回 `(bits,flags)` 元组 + RNA 调用点再包一层、无 `RecursionError`」，与我实测 `((0x7F800000,0x14),0x14)` 逐字一致）；既有审阅记录未改写；零代码改动；未 commit/push、未动台账。

**判决：Accepted**（工程师达标；最终接受仍由 architect 终审）。非阻断遗留仅 1 条：本人第 1 轮记录内 2 处通配形 `.work/`+`log/*` 字样（豁免形、门控 rc=0），是否清成字面 0 由 architect 决定。

## 完成区

**测试结果**：一键证据 `run.sh` → `PASS=27 FAIL=0`（rc=0）。18 格实测（gem5 harness probe：`rf2` 低 32 位 = 结果、`rf0[4:0]` = 标志；18/18 全 `0x14` = OF|NX、UF=0；输入 `±0x7FEFFFFFFFFFFFFF`，与 QEMU 侧同一输入位型）：

| 方向 | 正溢出 | 负溢出 |
|---|---|---|
| RNE / RNA | `7f800000` | `ff800000` |
| RTZ | `7f7fffff` | `ff7fffff` |
| RUP（向 +∞） | `7f800000` | `ff7fffff` |
| RDN（向 −∞） | `7f7fffff` | `ff800000` |
| 动态 `00/01/10/11` | 同 RNE/RTZ/RDN/RUP 行 | 同左列 |

控制例 RNE 1.5 → `3fc00000`、flags `0x00`。

18 格输入均为**严重溢出**（`±(ft_max+0.5ulp)` 量级），**无「轻微溢出只置 NX」格** ⇒ 本任务**不宣称 OF 语义已全覆盖**；该覆盖由 `m13-testcases-011`（轻微+严重 ≥8 例三方对照）承接。

**与 QEMU 对齐**：同一 19 例 YAML 跑已合入 QEMU ⇒ `19 total, 19 passed`；把 YAML 期望钉到 gem5 实测值再跑 ⇒ 仍 `19/19`（逐字节）。反向判别：改前 QEMU 基线跑同一 YAML 恰 8 格红（`4 5 7 8 12 13 14 17` = RTZ±、RUP−、RDN+、动态 01±/10+/11−），与定稿差集逐格相同。

**修改文件**（与 `git status` 对账，5 个）：`components/gem5/patches/src/arch/dadao/exec/b7.cc.patch`、`components/gem5/patches/src/arch/dadao/exec/b7_test.cc.patch`、`components/gem5/changelog.md`、`tools/gem5/b7_ref.py`、本任务书；组件源 `.work/source/gem5` 已按 E1 收敛为 base+1 单提交（`dc1412a0`，干净）。

**验收结果**：`check_b7` rc=0（`B7 coverage 55/55`、`oracle vectors=3998`、`oracle mismatch=0`、`cross-check disagreements=0`、fo2ft overflow 断言 19/19）；`check-gem5-decode` rc=0；`check_tiny_hmon` rc=0（`PASS (209 checks, 44 records)`，scons 报 `gem5.opt is up to date` 证明二进制即当前源码）；273 例 sweep `covered=273`、md5 `2d4d9465…` 不变；重建 ≈2 min（`JOBS=8`，1 文件 + 736 MB 链接）≡ `make build-gem5` rc=0。
**门控**：L2 `check-modules` rc=0（四 scope 代表集 PASS）；L1 按 `_locked-check` 成员**逐项**跑（52 项 = 现行 `Makefile` 现场计数）⇒ **49/52 rc=0、3 项 rc=2**（运行期日志落运行期日志目录，未引用具体路径）：`check-patch-tree` rc=2（4 条问题全属 chipyard 并发写者，gem5 命中 0，`--source-state` gem5 `OK HEAD=dc1412a0 count=1 clean=True`）、`check-run-artifacts` rc=2（55 条非法命名命中全属他任务、本任务 0）、`check-temp-dirs` rc=2（5 条陈旧目录 mtime 19–51 h 全属他任务，本任务目录为活动 worktree 未计入）；`check-knowledge-refs` 首轮现场 rc=2（2 处具体运行期路径引用、均本任务书），改写后复跑 **rc=0** 并计入分子。

**注入（可达 FAIL）**：把「恒 ±Inf」覆盖块塞回 ⇒ 源码 md5 `fe662145…`→`40edf2b4…`、`INJECTED` 标记 1 处；harness 红 8 断言、probe 红格恰那 8 个；`cp`+`touch` 还原 md5 回 `fe662145…`、标记 0 处、`check_b7` 与 19/19 回绿。

**新发现/坑**：① `b7_ref.py::_overflow_bits` 原实现 `return encode(1e400, ft, 4)` 返回 `(bits,flags)` **元组**，RNA 调用点又把它再包一层（`old.encode(1e400, ft, 4)` = `((0x7F800000,0x14),0x14)`）；无 `RecursionError`（`encode` 委托的是独立 oracle 模块）。RNA/动态溢出旧无向量故从未暴露，18 格向量一跑即崩（连带 3 个调用点）。② `conv_mode` 文档写了 `0x20 = rf0` 但无实现分支。③ gem5 增量重建（1 文件 + 链接）≈2 min，注入回环只需 g++ 重编 harness（秒级），不必 scons。④ 测试循环重置 `WordSpec` 会连带清掉后续用例依赖的字段，须显式重设。

**遗留问题**：无（`m13-testcases-011` 负责补轻微/严重溢出矩阵与三方对照；本任务只改实现与既有 checker 的 18 格断言）。

## 返工项（reviewer 第 1 轮 Needs Revision，仅文档两处）

**R1（阻断）**：完成区门控段写了具体 `.work/**` 日志路径 ⇒ `check-knowledge-refs` rc=2（父版本该串为 0，本任务引入；本段原文亦含该串，同为命中项）。改成不含具体路径的措辞（任务号可留），复跑期望 rc=0。

**R2（阻断）**：完成区写「L1 逐项 49/52 rc=0」与实跑不符。reviewer 现场核 `Makefile:1114` 共 **52** 项 ⇒ **48/52 rc=0、4 项 rc=2**：`check-patch-tree`（chipyard 4 / gem5 0）、`check-run-artifacts`（55 命中全他任务、本任务 0）、`check-temp-dirs`（5 条全他任务、本任务 0）、`check-knowledge-refs`（即 R1）。按复跑真实值重写。

**非阻断（reviewer 已核实，写进完成区即可）**：
- 18 格全为严重溢出，**无「轻微溢出只置 NX」格**；该覆盖由 `m13-testcases-011` 承接，**不得宣称「OF 语义已全覆盖」**。
- 审阅记录里「`_overflow_bits` 自递归」措辞不实：真实缺陷是**返回元组 + 在 RNA 调用点被再包一层**（`old.encode(1e400, ft, 4)` = `((0x7F800000,0x14),0x14)`），无 `RecursionError`。若完成区沿用此措辞需改。

实现与测试侧 reviewer 已判全绿（18 格 == QEMU 逐字节、三处修复安全、注入可达），**本轮不要改代码**。

## 返工处置（第 2 轮 engineer，2026-11-12）

- **R1 ✅已修**：完成区门控段删去具体 `.work/**` 日志路径，改为「运行期日志落运行期日志目录」；检查器现场报 2 处命中（完成区 line 105 + 返工项 R1 原文 line 115，均为本任务书引入），故 R1 原文中的同一串一并改为通配形。复跑 `make check-knowledge-refs` ⇒ rc=0（`结果: PASS (0 具体 .work/** 引用; 0 悬空小节级互指…)`）。
- **R2 ✅已修**：按现场复跑重写为「52 项中 49 rc=0、3 项 rc=2」。现场计数：`_locked-check` 成员 52 个（脚本现场取行，非抄录）；R1 修前初跑实测 **48/52 rc=0、4 项 rc=2**（`check-patch-tree`、`check-knowledge-refs`、`check-run-artifacts`、`check-temp-dirs`，与 reviewer 记录一致）；R1 修后全量重跑 **49/52 rc=0、3 项 rc=2**。逐项 rc 清单落运行期日志目录。
- **非阻断① ✅**：完成区新增「18 格全为严重溢出、无『轻微溢出只置 NX』格 ⇒ 不宣称 OF 语义已全覆盖，由 `m13-testcases-011` 承接」。
- **非阻断② ✅**：完成区「新发现/坑 ①」改为「返回 `(bits,flags)` 元组 + RNA 调用点再包一层（`((0x7F800000,0x14),0x14)`）、无 `RecursionError`」；审阅记录 F2 为当时原文，按「不改写既有审阅记录」保留，更正以 reviewer 第 1 轮记录 ② 与本条为准。
- **范围**：零代码/测试/checker 改动；`git status --porcelain -uall` 仅本任务书。

#### 收尾（architect，2026-11-12 13:24）

- 第 2 轮 reviewer **Accepted**：两条阻断项（运行期路径、L1 计数）在其重跑下解除；**零代码改动**经 `git diff --stat` + 4 个交付物 md5 逐项核对成立；证据脚本 `PASS=27 FAIL=0`。
- **L1 实测 49/52 rc=0、3 红**（`check-patch-tree` 4 条全 chipyard / gem5 0、`check-run-artifacts` 55 条本任务 0、`check-temp-dirs` 5 条全他任务）；**L2 rc=0**。
- **轻微溢出语义已由 reviewer 用 IEEE §7.4 原文 + 实测确认**：gem5 实测 8 格轻微溢出中「正向 RNE/RTZ/RDN、负向 RNE/RTZ/RUP ⇒ ±ft_max + 仅 NX」「正向 RUP / 负向 RDN ⇒ ±Inf + OF|NX」，**同 8 例 QEMU 也 8/8 一致** ⇒ 两实现本就符合「无界指数舍入后再比较」的判据，**无需改实现**。
- 覆盖缺口（本任务 18 格全严重溢出）由 `m13-testcases-011` 承接，完成区已声明不宣称全覆盖。
- 遗留：reviewer 第 1 轮记录内有 2 处**通配形** `.work/log/*`（检查器豁免、门控 rc=0），按「不改写既有审阅记录」保留。

