# m13-gem5-011: quiet compare 遇 sNaN 置 `NV`（D1）+ `rootn(±0,2) ⇒ +0`

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-007`（口径定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

**预估**：2–3 h

## 用户裁定

- **D1**（2026-11-12）：quiet compare（`ftqcmp`/`foqcmp`）遇 sNaN ⇒ 置 `NV`，「改为置 NV（跟 IEEE）」（落盘 `.tao/knowledge/discussing.md`）。
- **R1**（2026-11-13）：`rootn(±0,2)` 收严为 IEEE `+0`（IEEE 754-2019 §9.2.1；NOTE 明确 `rootn(−0,2) ≠ squareRoot(−0)`）。
- **R2**（2026-11-13）：结果 NaN 统一 canonical qNaN（符号 0、payload 全零；ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）。

审计来源：`docs/TestReports/M13-FP-IEEE对齐审计.md` §D1 / §D2 / §D3。

## 背景（现状现场）

- `components/gem5/patches/src/arch/dadao/exec/b7.cc.patch` 的 `runCompare()`：`case fp::Cmp::Unordered` 里 signaling 才 `flags = fp::NV`，quiet 直接 `result = fp::qnanBits(fmt)` ⇒ **quiet 遇 sNaN 不置 `NV`**（审计实测两方向 `FCSR=0x7FF800007FC00000`，低 5 位 = 0，应为 1）。
- `components/gem5/patches/src/arch/dadao/exec/fp_soft.cc.patch` 的 `sqrt()`：零分支 `if (u.kind == Kind::Zero) return {zeroBits(fmt, u.sign), 0};  // rootn(-0, 2) model: -0` ⇒ `foroot(−0,2) = 0x8000_0000_0000_0000`。
- 模型 `tools/gem5/b7_ref.py` 同现状：`op_sqrt()` 零分支 `zero_bits(fmt, k["sign"])`；`cmp` 分支 quiet 无序不置 `NV`。
- 算术/scaleB/FMA/rnd/minmax 已 canonical（`qnanBits`），**但 `fp_soft::convert()`（`fo2ft`/`ft2fo`）仍保留输入 NaN 的符号与 payload**：`return {(u.sign ? signBit(dst) : 0) | (expAll(dst) << …) | dstFrac, …}`，审计实测 `fo2ft(0xFFF8_0000_0000_0123) = 0xFFC0_0000`。

## 范围

1. **D1（必做）**：`runCompare()` 的 quiet 分支——任一操作数为 **sNaN** ⇒ 置 `NV`（实现可用既有 `fp::isSNaNBits`，`runMinMax` 已在用）；只含 qNaN ⇒ 不置；signaling 分支（任何无序 ⇒ `NV`）保持不变。
2. **R1（必做）**：`fp_soft::sqrt()` 零分支 ⇒ `zeroBits(fmt, false)`（`+0`），不置标志；`±Inf`、负有效数（`NV` + canonical qNaN）、有限正数不变。
3. **R2 缺口（默认纳入，待主会话确认后执行；理由见下）**：`fp_soft::convert()` 的 NaN 分支 ⇒ `qnanBits(dst)`（符号 0、payload 0），sNaN ⇒ `NV`。理由：R2 要求三平台结果 NaN 一致，而 gem5 转换现保留符号/载荷（`fo2ft(0xFFF8…0123)=0xFFC00000`），与 RTL/QEMU 改后不同；`m13-testcases-032` 无法按 spec 期望钉位型。若主会话裁定另立册，则本项移出并在完成区注明「转换 canonical 未做，归属另册」。
4. **模型同步**：`tools/gem5/b7_ref.py` —— `op_sqrt()` 零分支改 `zero_bits(fmt, False)`；`cmp` 分支 quiet + sNaN ⇒ `F_NV`；若纳入第 3 项，`op_convert_ff()` 的 NaN 分支改 `qnan_bits(dst)`。
5. `components/gem5/changelog.md` 记一条；补丁经 `make_patch` 重导出（`series` 不变）。

**非范围**：不改 `tests/inst/**`（归 `m13-testcases-032`）、不改 spec/合约、不改 QEMU/chipyard、不改 B7 之外的执行通路。

## 验收标准（可执行、可失败）

1. **D1 逐例**（B7 探针，打印 `FCSR` 与结果，`rd5`/`rd6` 语义同既有探针）：
   - `ftqcmp(sNaN, 1.0)` ⇒ `FCSR = 0x7FF8_0000_7FC0_0001`（低 5 位 = 1）；`ftqcmp(1.0, sNaN)` ⇒ 同上
   - `foqcmp` 同两方向 ⇒ 同上（`FCSR` 低 5 位 = 1）
   - `ftqcmp(qNaN, 1.0)` ⇒ `FCSR` 低 5 位 = 0（不置）；`ftqcmp(1.0, 2.0)` ⇒ 0
   - `ftscmp(qNaN, 1.0)` ⇒ 低 5 位 = 1（保持 signaling 口径，不回归）
2. **R1 逐例**：`foroot(−0,2)` ⇒ `0x0000_0000_0000_0000`；`ftroot(−0,2)` ⇒ 低 32 位全 0、符号 0；`foroot(+0,2)`/`ftroot(+0,2)` ⇒ `+0` 无标志；`foroot(−4.0,2)` ⇒ `0x7FF8_0000_0000_0000` + `NV`。
3. **R2（含第 3 项时）**：`fo2ft(0xFFF8_0000_0000_0123)` ⇒ `0x7FC0_0000`；`ft2fo(负 qNaN 带 payload)` ⇒ `0x7FF8_0000_0000_0000`；`ftadd(0x7FC1_2345,1.0)` ⇒ `0x7FC0_0000`（回归）。
4. `check_b7` rc=0 且 `[FAIL]`=0、`oracle mismatch=0`、覆盖计数取现场（不得沿用旧数）；`check-gem5-decode` rc=0；`build-gem5` rc=0。
5. **可达 FAIL 注入（≥2 路）**：① 去掉 quiet 分支的 sNaN 条件 ⇒ B7 两方向红（`FCSR` 低位回 0）；② root 零分支改回保号 ⇒ `−0` 例红。均 `cp`+md5+`touch` 还原 ⇒ 回绿（断言注入后源 diff 非空）。
6. 一键证据脚本 `.work/evidence/<任务ID>/run.sh` `rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`JOBS=8`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 待裁定（主会话下发前确认）

- **Q1（已由主会话确认，2026-11-13）**：第 3 项（`fp_soft::convert` 的 NaN canonical 化）**纳入本册**。依据 = 用户 2026-11-13 裁定的 R2「结果 NaN 统一 canonical（符号 0、payload 0）」，三平台必须一致，gem5 转换路径不能例外；不另立册。
- **Q2**：`check_b7` 的覆盖/向量计数在改动后必变（新增 NaN/root 断言），验收只按「现场计数 + `[FAIL]`=0」判，不沿用旧数（本任务已按此写）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

逐行审查范围：`exec/b7.cc`（runCompare）、`exec/fp_soft.cc`（sqrt/convert）、
`exec/b7_test.cc`（新增/改写 15 条断言）、`tools/gem5/b7_ref.py`（模型 + 边界向量）、
`components/gem5/{README,changelog}.md`。结论：逻辑与 spec 逐条对得上（contract-fp
§1/§6/§8、SimRISC-07 §1.4/§2.2/§4），`accrueFlags(0)` 为 no-op ⇒ 只含 qNaN 的
quiet compare 不写 rf0；`sqrt` 的 `NaN → 零 → 负号 → Inf` 分支序未变，`−Inf` 仍走
NV；`convert` 的 `ft2ft`/`fo2fo` 复制路径不经过 `fp::convert`，未被 canonical 化波及。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 探针把 `0x8000_0001` 当「负 f32 sNaN」，实为负次正规数 ⇒ 断言假红 | ✅已修 | 测试改用 `kFtSign|kFtSNaN`（`0xFF80_0001`） | `check_b7` rc=0、`[FAIL]`=0 |
| 证据脚本注入后未重编译探针二进制 ⇒ 「注入后探针不红」与「还原后仍红」 | ✅已修 | 注入/还原后先 `compile_harness` 再跑探针 | 注入后探针 FAIL 5/2 条、还原后 0 条 |
| 原差分向量覆盖 `root −0` 0 条、quiet-compare sNaN 仅 2 条 ⇒ 模型侧难独立发现回归 | ✅已修 | `edge_vectors()` 补 root 11 值 × 2 格式、compare sNaN 四组合、convert 带符号 NaN；4046→4098 | 注入下 `oracle mismatch` 10 / 2（模型独立报警） |
| `b7_test.cc` 旧注释「sNaN is quieted with NV」与相邻断言（纯位拷贝、无 NV）矛盾 | ✅已修 | 改注释为「复制类不改位、不置标志」 | 注释改动后 `check_b7` rc=0 |
| `components/gem5/README.md` 仍写「`rootn(-0,2) = -0`（模型选择）」与旧计数 3980 | ✅已修（越界披露） | 删去该模型项并重编号、计数改现场 4098 | 人工核对；`check-component-changelog` rc=0 |

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑记录**（作业树内现场执行，输出/退出码为本人终端真实值）：
- `python3 tools/gem5/check_b7.py --source .work/source/gem5` ⇒ **rc=0**；`[FAIL]`=0、`[PASS]`=3128、`summary: B7 coverage 55/55, failures 0`、`oracle vectors=4098`（现场值）、`oracle mismatch=0`、`cross-check disagreements=0`。
- `make check-gem5-decode` ⇒ **rc=0**（`positive 264/264, negative 388/388, legality 28/28, legacy 2/2, failures 0`）；`make check-component-changelog` ⇒ **rc=0**（`8 文件 × 4 断言 = 32 项` PASS）。
- `check_patch_tree.py --source-state` ⇒ rc=0，`gem5: OK HEAD=85c525f count=1 clean=True`；`check_patch_tree.py` 全局 rc=1，4 条 problem 全为 qemu/chipyard（他任务在途）、无任何 `gem5:` 行 ⇒ **gem5 段干净**。
- 证据脚本 `.work/evidence/m13-gem5-011/run.sh` ⇒ **rc=0**、`TOTAL failures=0`；两路注入 `[FAIL]` 5/2 条、`oracle mismatch` 10/2、md5 还原、回绿——与完成区数字逐条一致。

**独立语义核对**（自建 14 条向量，期望按 SimRISC-07 §1.4/§2.2/§4 + contract-fp §1/§6/§8 手推，不读 engineer 探针）⇒ **14/14 passed, rc=0**：quiet 两方向 sNaN ⇒ canonical qNaN 且 `FCSR=0x7ff800007fc00001`（全值与验收 item1 相符）、qNaN 对照 f0、signaling qNaN ⇒ sNaN（符号 0）+f1、`foroot(−0)`/`ftroot(±0,2)=+0` 无标志、`foroot(−4.0)` ⇒ canonical+f1、`fo2ft`/`ft2fo` 带符号/带载荷 qNaN ⇒ canonical 无 NV、sNaN ⇒ canonical+NV、`ftadd(qNaN)` 回归 canonical。

**独立注入**（自设计，走 engineer 未覆盖的 convert 路径）：`fp_soft.cc:904` `qnanBits(dst)`→`qnanBits(dst)|1`（锚点唯一、源树 diff 非空）⇒ `check_b7` **rc=1**、`[FAIL]`=4、`oracle mismatch=22`、reviewer 探针 3 点红（rv9/rv10/rv11）；`cp`+md5 还原（`6353b70088f5692f0866e4d360caef14` 前后相等、源树干净，全程未用 checkout/restore/stash）⇒ 回绿 rc=0/`[FAIL]`=0/mismatch=0、探针 14/14。

**模型 vs 实现独立性**：`b7_ref.py` 分类走 `oracle_fma.classify`（Python/Fraction），实现走 `fp::unpack`/`fp::isSNaNBits`（C++ 整数位算法），算术主体两套独立算法——**非同源拷贝**；但本任务三处改动两侧均为「返回 spec 规定常量」的一行式、分支序平行（由 spec 规定），差分对这三处的独立发现力有限 ⇒ 独立性由 b7_test 手写断言 + 本次 reviewer 独立探针承担（已验）。非阻断，记录在案。

**约束核验**：toplevel = 本作业树、未提交 git ✓；计数取现场 4098（未沿用旧数）✓；改动 = 完成区声明 6 文件 + 任务书（commit 7 项对账一致），未碰 spec/contracts/`tests/**`/QEMU/chipyard ✓；README 改动仅限失效模型条目删除+重编号+计数 ✓；完成区 7 行 ≤30、grep 无运行期路径 ✓；注入还原全程 `cp`+md5 ✓；b7_test patch 删 2 条 check 均为 spec 改口径的必然改写（ft2fo payload 传播、`ftroot −0=−0`），无弱化其它断言 ✓。

**Findings（非阻断）**：F1 `components/gem5/README.md:536` 仍写「3980 条 oracle 差分」，与同文件 :102 现场 4098 不一致（漏改一处，文档级）；F2 验收 item6 写 `JOBS=8`、实际证据脚本 `build-gem5 JOBS=32`（与 AGENTS.md 2026-11-13「默认 nproc/2=32」一致、117 GiB 内存充足），建议收尾时把任务书该行口径改为 `JOBS=32`。

**判决：Accepted**——验收命令块在本人重跑下全绿、独立语义 14/14、独立注入 FAIL→还原→回绿，硬约束无违反；F1/F2 交 architect 收尾修正。

## 完成区

**测试结果**：6/6 验收项通过、失败 0。`check_b7` rc=0（`[FAIL]`=0、`oracle mismatch=0`、现场 vectors=4098、harness `[PASS]`=3128、55/55）；`check-gem5-decode` rc=0（positive 264/264、negative 388/388、legality 28/28、legacy 2/2）；`build-gem5 JOBS=32` rc=0（构建期 `free -g` available 117 GiB，未降档）；逐例探针全中：两格式两方向 quiet-sNaN ⇒ canonical qNaN + FCSR 低 5 位=1、qNaN 对照=0、signaling 不回归，`ftroot`/`foroot(±0,2)=+0`（无标志）、`(±)4.0` 负例 ⇒ canonical qNaN+NV，`ft2fo`/`fo2ft` 带符号/带 payload NaN ⇒ canonical（sNaN 另置 NV），`ftadd(qNaN,1.0)` 回归 canonical；注入 2 路（去掉 quiet-sNaN 条件 / root 零分支保号）⇒ `check_b7` rc≠0（FAIL 5 条 / 2 条、oracle mismatch 10 / 2），`cp`+md5 还原后回绿，注入后源 diff 非空、还原后源树干净；`check-component-changelog` rc=0。
**修改文件**：`tools/gem5/b7_ref.py`；`components/gem5/README.md`；`components/gem5/changelog.md`；`components/gem5/patches/src/arch/dadao/exec/{b7.cc,b7_test.cc,fp_soft.cc}.patch`（`make_patch.py` 重导出，`series` 仍 101 份）；组件源树三文件已按 Process-01 收敛为 base+1 本地 commit。`git status -uall` 恰为上述 6 项（任务书除外）。
**验收结果**：一键证据脚本（本任务 ID，运行期证据目录）rc=0、`TOTAL failures=0`，逐项打印 expect/actual/rc，含注入→FAIL→`cp`+md5 还原→回绿自检；`check-source-state` 报 gem5 `OK HEAD=85c525f count=1 clean=True`，`check-patch-tree` 输出无任何 `gem5:` 断言问题（全局 rc=1 仅来自 qemu/chipyard 的断言⑥⑨，属他任务在途改动）。
**新发现/坑**：① 负 f32 sNaN 是 `0xFF80_0001`，`0x8000_0001` 是负次正规数（探针曾因此假红）；② 注入自检必须**先重编译**探针二进制，否则跑旧二进制会「假绿/假红」（证据脚本首版即此问题）；③ 既有差分向量对 `root −0` 覆盖为 0、quiet-sNaN 仅 2 条 ⇒ 只靠随机池无法独立发现这两类回归，须补显式边界向量；④ `accrueFlags(0)` 为 no-op 是「qNaN 不写 rf0」的既有保证，勿在 compare 路径另写 rf0。
**遗留问题**：`components/gem5/README.md` 属任务书未列文件，本次为删去已失效的模型项与旧计数而同批更正（已在自审表披露）；其余无。
