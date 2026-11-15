# m13-gem5-015: gem5 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（解码表 + exec + 周期表）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`）；`m13-llvm-001`（已合 `75364281`）、`m13-qemu-016`（已合 `ca916300`）可作**交叉检查**（不作期望来源）
**可并行分片**：否（gem5 组件单写者）
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：已验证

## 语义真源

`spec/SimRISC-02`（`rf2rf` 段）+ `contracts/opcodes.yaml::rf2rf_orri_rf`：`opc=OPC-octa(0x40)`、`opx=111-100(ha=0x3C)`、`orri`/`rf`；整 64 位逐位复制、不置标志；`immu6=0`/两端越界/任意重叠 ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**、源 `rf0` 合法。

## 任务

1. `components/gem5` 补丁：`decode_table.inc` / `decode_assertions.inc` / `decode-assertions.tsv` 删两条旧、加 `rf2rf`（**由生成器产出，不手改**）；`inst.cc`/`exec` 实现整 64 位逐元素搬移与六类非法；
2. `b7.cc` / `b7_test.cc` / `fp_soft.cc` 内旧指令引用清理；
3. `wuming_cycles.cc`（周期表）删两条旧、加 `rf2rf` 行（值由 `docs/core-wuming-cycle-model.md` 现场解析；若文档无该行 ⇒ **停下写「待裁定」**，不要自拟拍数）；
4. 补丁导出 + `check-patch-tree` **gem5 段 0 问题** + `--source-state` gem5 OK + `check-component-changelog`。

## 验收（真实 rc）

1. `rf2rf` 语义：`immu6=3` 三元素逐位复制、源寄存器不变；六类非法各 `ILLI`；源 `rf0` 合法（贴实测）；
2. 旧指令编码 ⇒ 非法（UNKNOWN/UNDI 口径按 gem5 现状，与 qemu 的 `0xF9` 对齐说明）；
3. 门控：`check-gem5-decode`、`check-wuming-cycles`、`check-patch-tree`（gem5 段）、`--source-state` gem5、`check-component-changelog`、`check-no-residue`；
4. **≥2 路注入**（`cp`+md5 还原）：① 放行目的 `rf0` ⇒ 负例红；② 重叠判定放宽为"仅完全重合" ⇒ 部分重合负例红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/gem5/**`、`tools/gem5/**`（生成器/周期表侧必要时）、本任务书；**不改** `spec/`、`contracts/`、`tests/inst/**`、其它组件；
- 构建按需（`JOBS=32`，申报耗时）；禁 `install-host`/`check-modules`；**禁 `git reset --hard`**；不 sync/reset 节点；
- 不提交 git；注入还原 `cp`+md5。

## 待裁定

**T1 周期表 `rf2rf` 拍数 —— 已处置（选项 A，主会话裁定 2026-11-15）**

- 原问题：`docs/core-wuming-cycle-model.md` §3 行 71 曾写已删除的 `ft2ft`/`fo2fo`（块复制），全篇无 `rf2rf`；生成器只能匹配到行 70（FP 转换 `*2*` glob，1 拍），直接采用即自拟。
- 处置：行 71 助记符改为 `rf2rf`（**行数 148 不变**，其余被引行号不漂移），拍数与 `D′`/`1+N` 口径**一字未动**；随后重跑生成器，`wuming_cycles.yaml` / `wuming_cycles.{cc,hh}` 由 264 行（含两条已删 id）变为 **263 行**（`rf2rf` = `D′`/`1+N`/`dynamic: N`/引行 71/`实测`）。
- 依据（供 `m16-chipyard-001` 复核）：① `rf2rf` 在 `spec/SimRISC-02 §1` 属**寄存器复制/块复制族**，与 `rd2rd`/`rb2rb` 同族（`m13-testcases-047` 已把载体落 `02-reg-copy`）；② 周期模型对 `rd2rd` 类已实测 `1+N`（`m16-gem5-005`），`rf2rf` 与之同构 ⇒ 沿用 `D′`/`1+N` 是**同族映射**、不是新拍数；③ 本次只是周期模型文档的 **id 对齐**，不改 spec/契约语义。
- **实测拍数仍待 `m16-chipyard-001 周期模型收口复测` 复核**（`1+N` 现属「同族沿用」，非对 `rf2rf` 的独立实测）。
- 附带：模型 §5 行 129 仍列 `ft2ft` / `fo2fo`（同一 `1+N`/`012` 口径行）——本次裁定范围只到 §3 行 71，该行**未动**，建议随 `m16-chipyard-001` 一并改名。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

**结论**：改动 = 生成器（解码表/收敛字/周期表）+ 组件源（b5 加 `rf2rf`、b7 删两条、B1–B4/B6 计数）+ 门控脚本；逐行核对如下。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 周期表生成器「先写盘再报 FAIL」，误跑会落盘自拟拍数 | ✅已修 | `gen_wuming_cycles.py` 写盘改 fail-closed | 误跑前后 md5 三文件不变；`rc=1` 且拒绝写盘 |
| F2 首版 `validate_rf2rf` 禁止任何 `rfhc` legality，误杀合法的源区间检查 | ✅已修 | 收窄为「`rfhc != …` 型禁令」 | `gen rc=1 → 0`，`check-gem5-decode` 转绿 |
| F3 `MATRIX_ABSENT_CONTRACT_REF` 的 `contract-fp §12` 为手写映射 | ❌不修（设计） | 由 `BATCH_COUNTS` 现场计数兜底（误分类必改变批次计数）+ `validate_rf2rf` 钉住 format/ha/rules/legality；注意 `batch_of` 对任意 `contract-fp §…` 一律 B7，单看它拦不住错分类 | 改 `§11`/`§5`/`§13` 三种错映射均被批次计数判死（B1 39 / B2 9 / B2 9）；删 `dst_rf0` 或 `immu6 != 0` 均被 `validate_rf2rf` 判死 |
| F4 `gen_converge_words` 的 `COUNTS` 缺 `0`（基线既存红） | ✅已修 | 末尾追加 `0` | 3 条 unsolved → 263/263；仅 3 行取值变化 |
| F5 `check_converge` b3/b6 PASS 基线过期（既存红） | ✅已修 | 现场重测 4318/1384，注明漂移来源 | `git log` 显示 `m13-gem5-012`/`INTEG-053t` 在冻结点之后改过 `b3_test`/`b6_test` |
| F6 周期表 `rf2rf` 行缺失 | ✅已修（按裁定选项 A） | 行 71 助记符改 `rf2rf`；生成器重跑出 263 行；`REQUIRES_EXACT_DOC_ROW` 保留（现通过，仍拦「回落 glob」） | `make check-wuming-cycles` rc=0（14 PASS）；`rf2rf` 行 = `D′`/`1+N`/`doc: 71` |

**逐行要点**：① `rf2rf` 六类判据全部在**任何寄存器读之前**（`count==0`→目的/源越界→目的 rf0→重叠），与 `Copy` 共用同一分支；② 目的 `rf0` 规则绑定到 op（`CopyNoRf0`）而非 bank，`rd2rf` 仍可写 `rf0`（FCSR 掩码写）；③ 写路径全 64 位（目的非 0 ⇒ `writeFloat64`），源 `rf0` 读 `readFloat(0)` 就是完整 FCSR 字；④ 四条 `kOracles`/`kShapes`/`kIds` 计数同步为 29/53，`T_COPY_NO_RF0` 与 `execOpOf` 对照保持独立 oracle；⑤ 解码负例对两条旧编码同时有「保留槽」与「点名已删除」两行（沿既有重复风格，不改既有计数语义）；⑥ 未改 `spec/`、`contracts/`、`tests/inst/**`、其它组件；未跑 `install-host`/`check-modules`；未 `git reset`。

**状态对账**：F1–F6 全部已修（F6 按主会话裁定走选项 A）；唯一「非本次实测」项是 `rf2rf` 的 `1+N` 属同族沿用、待 `m16-chipyard-001` 复核 ⇒ 状态置「待验收」。

### 第 2 轮 reviewer 验收（2026-11-15）

**重跑（我方真实 rc）**：`check-gem5-decode` rc=0（263/263+391/391+28/28+2/2）；`check-wuming-cycles` rc=0（263 id、D′=9、三份 artifact-up-to-date）；`check_patch_tree.py` rc=0（全仓 401 patch，gem5 段 107）；`--source-state` rc=0（gem5 OK HEAD=fec4fd5 count=1 clean=True）；`check_component_changelog` rc=0；`make check-no-residue` rc=0；证据脚本 plain **42/42**、`--inject` **53/53** 均 rc=0；`check_b1..b7`/`check_converge` 全 rc=0（B5 1292 PASS/0 FAIL、B7 2955 PASS、oracle 3946 向量 mismatch=0、收敛 263/263+1841/1841）；`make build-gem5 JOBS=32` rc=0。
**注入（自设计 2 路 + 生成器 3 例，均 cp+md5 还原，还原后 b5.cc md5=199381d1…、gen md5=8254d6b9…、源树/工作树 `git status` 干净）**：① 把 `CopyNoRf0` 的 rf0 判定挪到元素循环之后 ⇒ check_b5 rc=1，恰 3 条 `zero reads/writes (immu6=1/2/3)` 红；② 上界 `>` 改 `>=` ⇒ rc=1，24 条红（`dst/src+8 == 64 legal` 等）；③ `MATRIX_RETIRED_IDS` 删 `fo2fo` ⇒ 生成器 rc=1 且未写盘；④ `contract_ref` 改 `§11` ⇒ rc=1（B1 39/B5 28 批次计数判死）；⑤ 改 `§12x` 探边界 ⇒ `--check` rc=1（stale），写盘模式不拦（已知设计边界，见 F3）。
**核对**：六类非法判据全在 `b5.cc` 353–369、先于 370 的读写循环（读代码序，非仅测试）；零读写实测覆盖 immu6=0/目的 rf0×3/重叠 3 例，两个越界例仅断言 ILLI（代码序已覆盖，建议补断言）；FCSR：Copy 路径只走 `readReg/writeReg`，`idx==0` 写被 `CopyNoRf0` 判定挡死 ⇒ 不置标志（代码级成立 + 两条实测）；旧编码 `0x44080000/0x44280000` 空槽（negative.tsv 321/325+391/392）、`inst.cc` 解码失败 FS→`FaultUNDI`、`machineFaultExitCode` hypv ⇒ `0xC0|0x30|9=0xF9`（与 QEMU `excp_undi` 同口径，静态链，无 FS 实跑）；负例 388→391、断言 264→263、周期 yaml 264→263 现场复算一致；`check_b7` 仅删两条退役 id 与其 cvt_ff 族下限 128→64（随删除而来，实测 170≥64），双向集合校验仍在。
**`1+N` 判定**：同意「同族沿用」而非新拍数，但行 71 的「实测」标签继承自旧 `ft2ft/fo2fo`，且元素宽 32→64、`per_beat=8` ⇒ **必须由 `m16-chipyard-001` 实测 N=2/3/8/32 才算闭环**，并顺带改 §5 行 129 旧名（本任务已披露为遗留）。
**越界**：`git show 426b75e3 --name-only` 36 项，仅 `components/gem5/**`、`tools/gem5/**`、`docs/core-wuming-cycle-model.md`、本任务书；未动 `spec/`、`contracts/`、`tests/inst/**`；完成区 10 行无运行期路径；未跑 `install-host`、未提交、未 `reset --hard`。
**判决：Accepted**（3 条非阻断 finding：越界两例缺零读写断言、行 71「实测」标签待实测改口径、`§12x` 型 contract_ref 写盘不拦）

## 完成区

**测试结果**：`make build-gem5 JOBS=32` **rc=0** 两次（首轮 2 m 20 s；周期表重生成后增量重建 1 m 57 s，`wuming_cycles.cc` 重编并重链；申报 3 min）；解码 **263/263 + 391/391 + 28/28 + 2/2**（696 `[PASS]` / 0 `[FAIL]`）；B5 **29/29**（1292 PASS，`rf2rf` 六类非法 + 整 64 位复制）；B7 **53/53**（2955 PASS，`oracle mismatch=0`，3946 向量）；B1/B2/B3/B4/B6 = 2156/1160/4318/3696/1384 全 0 FAIL；收敛 263/263 + 边界 1841/1841；周期表 **263/263**（`D′` 8→9、动态行 94→95）。
**修改文件**：`docs/core-wuming-cycle-model.md`（仅 §3 行 71 助记符 `ft2ft`/`fo2fo` → `rf2rf`，行数 148 不变）；`tools/gem5/wuming_cycles.yaml` + 组件源 `wuming_cycles.{cc,hh}`（生成器重跑，263 行）；`components/gem5/{README.md,changelog.md,decode-assertions.tsv,decode-negative.tsv}`；`components/gem5/patches/**` 19 份（decode 4 + exec 测试/b5/b7/fp_soft/converge 13 + `wuming_cycles.{cc,hh}` 2）；`tools/gem5/{gen_decode_table,gen_converge_words,gen_wuming_cycles,check_b3,check_b4,check_b5,check_b6,check_b7,check_converge,b7_ref}.py`；本任务书（`git status -uall` 恰为这 36 项）。
**验收结果**（真实 rc）：`make check-wuming-cycles` **rc=0**（14 PASS，含 `doc-row-exact`/`no-dropped-row`/三份 `artifact-up-to-date`）；`check-gem5-decode` rc=0；`check-patch-tree` **rc=0（全仓，gem5 段 107 patch）**；`--source-state` rc=0（gem5 `OK HEAD=fec4fd5… count=1 clean=True`）；`check-component-changelog` rc=0；`check-no-residue` rc=0。附：`check_b1..b7` rc=0、`check_converge` rc=0。
**周期表口径（T1 选项 A）**：`rf2rf` 行 = `D′` / `1+N`（N=2 ⇒ 3；N=3 ⇒ 4）/ `dynamic: N` / 引文档行 71 / `实测`；依据 = `rf2rf` 与 `rd2rd`/`rb2rb` 同属块复制族（`SimRISC-02 §1`、`m13-testcases-047` 落 `02-reg-copy`）＋ `rd2rd` 类实测 `1+N`（`m16-gem5-005`）⇒ **同族沿用、非新拍数**；**实测拍数待 `m16-chipyard-001 周期模型收口复测`**。表 md5：`yaml 7d5c58f0…`、`cc acb9ff6f…`、`hh dd9df2ed…`。
**旧指令口径**：`0x44080000`/`0x44280000` 现为空子表槽 ⇒ 解码失败 ⇒ FS 走 `FaultUNDI`（cause 9 ⇒ 退出码 `0xF9`），与 QEMU「无 pattern ⇒ `excp_undi`」同口径；SE 仍 panic（现状未改）。
**注入**（cp+md5 还原）：① 删目的 `rf0` 检查 ⇒ 6 条 rf0-目的断言红；② 重叠放宽为「仅完全重合」⇒ `rf2rf` 等 4 组部分重叠负例红；均还原 md5 `199381d1…` 回绿。一键脚本（运行期证据目录）：plain **42/42**、`--inject` **53/53**。
**新发现/坑**：① 周期表生成器原「先写盘再报 FAIL」⇒ 已改 fail-closed（不通过拒绝写盘，md5 实测不变）；② `gen_converge_words.py` 的 `COUNTS` 缺 `0`，三条 `immu6 == 0` 精确转换长期无解（基线既存红）⇒ 补 `0` 到末尾，仅 3 行取值变化；③ `check_converge` 的 b3/b6 基线自 `m13-gem5-012`/`INTEG-053t` 起未刷新（既存红）⇒ 现场重测；④ GEM5-002t 矩阵为快照，新增 `MATRIX_RETIRED_IDS`/`MATRIX_ABSENT_CONTRACT_REF` 显式集合，任一侧未登记即失败；⑤ 文档 `docs/core-wuming-cycle-model.md §5` 行 129 仍列 `ft2ft`/`fo2fo`（不在本次裁定范围，未动）。
**遗留问题**：① `rf2rf` 的 `1+N` 属同族沿用，**实测待 `m16-chipyard-001 周期模型收口复测`**；② 模型 §5 行 129 的旧助记符建议随该任务一并改名。
