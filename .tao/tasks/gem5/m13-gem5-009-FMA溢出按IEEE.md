# m13-gem5-009: 融合乘加溢出按 IEEE 舍入模式（gem5）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-006`
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-399`）

gem5 的 `fofma` 溢出恒 ±Inf；按 `spec-006` 改为按舍入模式。

## 验收

四档 × 正负实测；与 QEMU 逐字节；`check_b7`/`check-gem5-decode` rc=0；注入可达 FAIL。

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

### 第 1 轮 engineer 自审（2026-11-13）

**审查方式**：逐行读改动（组件源 2 文件 + `tools/gem5/b7_ref.py` + changelog）；48 格期望由 `spec/SimRISC-07 §2.5` 表与三带判据手写，再用 `tools/testcases/oracle_fma.py`（精确 `Fraction`）逐行反算交叉核对；`run.sh` 连跑（`--no-build --no-sweep` 与全量各一轮）+ 两路注入还原。

**实现侧结论（先核实再动手）**：`ftfma`/`fofma` 走 `fp_soft::fma → addFinite → roundPack`，`overflowBits` 的形态表与「`e > emax` 才算溢出」的判据**改动前即符合 §2.5**（含轻微溢出只置 NX）。依据：48 格逐格实测全对 + 6384 条近溢出随机向量对照 `oracle_fma.py` 差分 0（运行期一次性，未归档）。故本次**不改语义**，落点是：把该映射写进代码注释、把 48 格钉成 gem5 自己的断言、给参考模型补 48 向量。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首版把三带（严重/轻微/分界）共用一个「方向表 ⇒ Inf」规则，RNE 轻微带误期望 `+Inf`（ft/fo 各 2 格 FAIL） | ✅已修 | 断言改为「溢出 ⇔ 无界指数舍入后量值 > max」并按带分派：`mild` 只 RUP+/RDN− 溢出，`half` 与方向表同（RNE 在分界进位） | 48/48 PASS；注入①红集与预测逐格相同 |
| F2 fo 结果误用 `ft()`（只取低 32 位） | ✅已修 | `Shape` 加 `isFt`，ft 读低 32、fo 读全 64 | 48/48 PASS |
| F3 `overflows` 未初始化 ⇒ `-Werror=maybe-uninitialized` 编译失败 | ✅已修 | 初始化 `true`，switch 三分支全赋值 | `check_b7` 编译段 rc=0 |
| F4 注入①首版只改 `overflowBits`（恒 ±Inf）：轻微带根本到不了溢出分支 ⇒ 仅 8 格红、mild 0 格，达不到「轻微 6 格红」 | ✅已修 | 注入改在 `roundPack` 顶部恢复 spec-006 前判据（任何 \|精确和\| > max ⇒ 溢出、恒 ±Inf + `OF\|NX`） | 红 28 格（含 mild 12 = 6/格式），harness/probe 红集相同 |
| F5 注入②模式串在 `fp_soft.cc` 出现 2 次（`roundPack` 与另一处同构代码）⇒ 注入器拒绝执行 | ✅已修 | 模式串补 `case Mode::RNE:` 上下文使之唯一；保留「必须命中一次」保护 | rne-tie 注入 4 格红、还原回绿 |

**判决**：F1–F5 已修并复验；无未修 finding，状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑记录（全部本人执行；worktree HEAD `087323b7`，前后快照 `git status -uall` 为空 + 4 文件 md5 逐项相等）**
- `./.work/evidence/m13-gem5-009/run.sh`（全量：gen_vectors + check_b7 + 指令路径 probe + check-gem5-decode + build-gem5 + 273 sweep + 2 次注入还原）⇒ **`REVIEWER_RUN_EXIT=0`、`== summary: PASS=33 FAIL=0 ==`**；`check_b7 rc=0`（`B7 coverage 55/55, failures 0`、`oracle vectors=4046`、`oracle mismatch=0`、`cross-check disagreements=0`、`[PASS] fma overflow`=**48**、`[FAIL]`=0）；`check-gem5-decode rc=0`；`build-gem5 rc=0`；sweep `covered=273` md5 `2d4d94651346ef673c5a855e024c1489`；`compare_tsv: cells=48 mismatch=0` —— 与完成区数字逐条对上（含注入① `31881a2a→518db2ce` 红 28/mild 12、注入② `→f25cb83c` 红 4）。
- **48 格独立重推**（本人现场写：精确 `Fraction` + 无界指数单次舍入 + §2.5 判据/方向表，不借 `gen_vectors.py`/`oracle_fma.py`）⇒ `cells=48 mismatches=0`，值位型与 `rf0[4:0]` 双字段同时比；比对对象 = 手写 `spec.tsv`（期望）与 gem5 指令路径实测 `gem5.tsv`，三方一致。首两版我自己推错 28/16 格（max 位型误当数值、方向镜像写反），修正后归零 ⇒ 格值确有区分力、非恒真。
- **reviewer 独立反例注入**：`cp`+md5 备份（`31881a2a…`）→ 改 `roundPack` 有限分支 `NX`→`OF|NX`（轻微溢出带也置 OF）⇒ `check_b7 rc=1`、`[FAIL] fma overflow` **20 格**（mild **12 格全红** + half 舍回 8 格）、总 FAIL 34（值不变仅 flags 变 ⇒ `rf0[4:0]` 断言可达 FAIL）；`cp`+`touch` 还原 ⇒ md5 回 `31881a2a…`、标记 0、`check_b7 rc=0`、`[FAIL]` 0、`[PASS] fma overflow` 48、`.work/source/gem5` git 干净。
- `make -s check-modules`（L2）⇒ **`CHECK_MODULES_EXIT=0`、`module checks (L2): PASS`**；`make -s check`（L1）⇒ rc=2，仅 `check-patch-tree` **chipyard 2 条**（`WumingDecoder.scala`，并发写者 `m12-chipyard-027`），`check-patch-tree: gem5` **0 条**，与完成区披露一致，非本任务缺陷。

**①「改动前即合规」属实（本任务成立与否的关键）**：`git show HEAD` 对 2 份补丁只增注释（`fp_soft.cc` 1035→1046 行、无逻辑行增删，`b7_test.cc` 纯新增）；亲读 `.work/source/gem5/src/arch/dadao/exec/fp_soft.cc`：`fma → addFinite → roundPack`（`b7.cc` 单点 `fp::fma`），溢出判据 `e > emax`（无界指数舍入后量值 > max），轻微带落有限分支 ⇒ 仅 `NX`；`overflowBits` 的 `toInf = RNE‖RNA‖(RUP∧正)‖(RDN∧负)` = §2.5 表，RNE 分界靠 `kept>>f.p` 进位后 `e=emax+1` 自然达成。`git log -S` 该判据自 `0d81750c`（GEM5-012t）即在，`m13-spec-006` 只改 spec/契约未动 gem5 ⇒ ISS-399 预期的 gem5 语义改动确无必要。

**约束核验**：① 独立 worktree、动手前 `git rev-parse --show-toplevel` 自证、未碰主工作树 ✓；② 本人未 commit/push（HEAD 仍 `087323b7`，WIP 提交属 architect）✓；③ 完成区 21 行 ≤30、第 1 轮自审 15 行 ≤40、完成区数字与我重跑逐条一致 ✓；④ 改动恰为 5 文件 = `git diff --stat HEAD~1`，无 spec/contracts/tests/台账越界，`b7_ref.py` 向量 3998→**4046** 现场复现 ✓；⑥ 注入仅 `cp`+md5+`touch`、未用 checkout/restore/stash，反例非空且还原回绿 ✓；⑧ 一键证据脚本存在并被我重跑，`expect_rc`/红集 diff/`mild=12` 均有可达 FAIL 路径，预测红集由 spec 表推导（`predict_red.py` 不读实现）✓。

**findings（不阻断，交 architect 收尾处置）**：F-a `components/gem5/changelog.md` 摘要「`RNE/RUP ⇒ 正 +Inf、负 −max`」把 **RNE 负向写成 `−max`（应为 `−Inf`）**，同句「6 带 × 2 符号 × 4 方向」应为「6 情形」——文档级措辞，不涉门控/断言；F-b 验收项「与 QEMU 逐字节」本轮未做（`m13-qemu-008` 并行实现中，已披露由 `m13-testcases-013` 三平台复核），收尾时须确认承接任务存在；F-c L1 `check-patch-tree` chipyard 2 条属并发写者，`check-knowledge-refs`/`check-temp-dirs`/`check-milestones-fresh` 归 architect 派单侧。

**判决：Accepted** —— 验收命令块在我本人重跑下全绿、48 格与 oracle 独立可信、硬约束无违反（不替代 architect 终审）。

## 完成区

**测试结果**：一键证据 `.work/evidence/<任务ID>/run.sh` ⇒ **EXIT=0**，`PASS=33 FAIL=0`（含 scons 增量重建 + 273 sweep，4m17s）；`check_b7` rc=0（`B7 coverage 55/55, failures 0`、`fma overflow` 断言 **48/48**、`oracle vectors=4046`、`oracle mismatch=0`、`cross-check disagreements=0`）；`check-gem5-decode` rc=0；`build-gem5` rc=0；L2 `check-modules` rc=0。

**48 格实测**（指令路径 probe：`rf0[33:32]` → `Executor` → 结果寄存器 + `rf0[4:0]`；`14`=`OF|NX`、`10`=仅 `NX`；`sev`=精确和 `2*max`、`mild`=`max+2^102`(ft)/`max+2^969`(fo)、`half`=`max+半个 ulp`）：

- ft（`ft_max=0x7F7FFFFF`）：`sev` 正 `RNE +Inf/14`、`RTZ +max/14`、`RDN +max/14`、`RUP +Inf/14`；负 `RNE −Inf/14`、`RTZ −max/14`、`RDN −Inf/14`、`RUP −max/14`
- ft `mild` 正 `7F7FFFFF/10`（RNE/RTZ/RDN）、`7F800000/14`（RUP）；负 `FF7FFFFF/10`（RNE/RTZ/RUP）、`FF800000/14`（RDN）
- ft `half` 正 `7F800000/14`（RNE/RUP）、`7F7FFFFF/10`（RTZ/RDN）；负 `FF800000/14`（RNE/RDN）、`FF7FFFFF/10`（RTZ/RUP）
- fo（`fo_max=0x7FEFFFFFFFFFFFFF`）：`sev` 正 `7FF0…/14`、`7FEF…/14`、`7FEF…/14`、`7FF0…/14`；负 `FFF0…/14`、`FFEF…/14`、`FFF0…/14`、`FFEF…/14`（顺序 RNE/RTZ/RDN/RUP）
- fo `mild` 正 `7FEF…/10`（RNE/RTZ/RDN）、`7FF0…/14`（RUP）；负 `FFEF…/10`（RNE/RTZ/RUP）、`FFF0…/14`（RDN）
- fo `half` 正 `7FF0…/14`（RNE/RUP）、`7FEF…/10`（RTZ/RDN）；负 `FFF0…/14`（RNE/RDN）、`FFEF…/10`（RTZ/RUP）

**修改文件**（与 `git status -uall` 对账，5 个）：`components/gem5/patches/src/arch/dadao/exec/{b7_test.cc,fp_soft.cc}.patch`、`components/gem5/changelog.md`、`tools/gem5/b7_ref.py`、本任务书；组源码按 E1 收敛为 base+1 单提交（`f98deac`，干净）。

**验收结果**：`check_b7`/`check-gem5-decode`/`build-gem5` rc=0；273 例 sweep `covered=273`、md5 `2d4d94651346ef673c5a855e024c1489` **不变**。**注入①**（恢复 spec-006 前判据：任何 \|精确和\| > max ⇒ 溢出 + 恒 ±Inf + `OF|NX`）⇒ 源 md5 `31881a2a…`→`518db2ce…`、标记 1 处，harness/probe 同步红 **28 格**（其中 mild 带 **12 格 = 6/格式**，与预测逐格相同）；**注入②**（RNE 平局改为向下）⇒ md5→`f25cb83c…`、红 4 格（分界带 RNE 正负 × 2 格式）。两次均 `cp`+md5+`touch` 还原回 `31881a2a…`、标记 0、48 格回绿。

**新发现/坑**：① `ISS-399` 的 gem5 侧表现与实测不符——`fofma`/`ftfma` 早已按方向（共用 `roundPack`/`overflowBits`）且有轻微溢出分档，48 格与 6384 条近溢出差分均 0 差异 ⇒ 本任务落点是覆盖/文档而非语义修复；② `b7_test.cc` 不进 gem5 二进制（`check_b7` 独立编译），改它不触发 scons 重建，须同时动 `fp_soft.cc` 才让 `build-gem5` 有意义；③ 可达 FAIL 必须注入「精确和 > max 即溢出」的**判据**，只改 `overflowBits` 无法让轻微带变红（该带到不了溢出分支）。

**遗留问题**：① 与 QEMU 逐字节对照本轮未做（`m13-qemu-008` 并行实现中）；三平台一致由后续 `m13-testcases-013` 全量复核。② `tools/gem5/b7_ref.py` 向量数由 3998 增至 4046（+48）。③ L3（`check-full`/`test-m6`）未跑，按流程由 `/complete` 执行。④ 门控现场：`check-patch-tree` rc=2（2 条全 chipyard 并发写者、gem5 0 条）、`check-knowledge-refs` rc=2（2 处具体引用分属 `m13-gem5-010` 与 `m13-spec-006` 任务书、本任务书 0）、`check-temp-dirs` rc=2（5 条陈旧目录全他任务）、`check-milestones-fresh` rc=2（台账仍「待开始」未移「进行中」，归 architect 派单更新，子代理不改台账）。

#### 收尾（architect，2026-11-13 10:16）

- reviewer **Accepted**：`run.sh` `PASS=33 FAIL=0`、EXIT=0；`check_b7` rc=0（`coverage 55/55`、`[PASS] fma overflow` **48**、`oracle vectors=4046`、`mismatch=0`）；`check-gem5-decode`/`build-gem5` rc=0；L2 rc=0；273 md5 不变。
- **「改动前即合规」经独立复核成立**：`b7.cc` 单点 `fp::fma → addFinite → roundPack`，判据 `e > emax`；`overflowBits` 的 `toInf` 形态即 §2.5 表；`git log -S` 显示该判据自 `0d81750c`（GEM5-012t）就在 ⇒ `ISS-399` 里「gem5 侧要同步改」的预期与事实不符。
- **48 格三源互证**：engineer 手写表、`oracle_fma.py`（精确 `Fraction`）、reviewer 现场重推（`cells=48 mismatches=0`）——reviewer 自述前两版自己推错 28/16 格，修正后才归零，说明格子有区分力。
- **不改实现、只补覆盖可接受**：语义本就达标；本任务补上两道约束（gem5 的 48 格断言 + 参考模型 48 向量），日后动 `roundPack` 会被 `check_b7` 与 probe 同时拦下。reviewer 自选注入「轻微溢出也置 `OF`」⇒ 20 格红（mild 12 格全红）⇒ 还原回绿。
- **F-a 已修**：`changelog` 摘要把 RNE 负向误写 `−max`（应 `−Inf`），已按四方向重写；「6 带」→「6 情形」。
- **F-b 承接确认**：三平台逐字节对照由 `m13-testcases-013` 承担（其套件已含 `fofma`/`ftfma` 用例与三平台比对）。
\n