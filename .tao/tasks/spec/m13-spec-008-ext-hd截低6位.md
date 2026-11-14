# m13-spec-008: `ext.uo`/`ext.so` orrr 形式的 `hd` 取 `rdHD[5:0]`（越界位忽略、不抛 ILLI）

**模块**：spec
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（单册正文 + 契约 + 只读锁同笔，须由单个 engineer 完成）
**状态**：已验证

**预估**：1–2 h

## 用户裁定（2026-11-13）

> 「`ext.*` 的 orrr 形式，`rdHD` 取**低 6 位**作起始位 `hd` 后继续执行，**不抛 ILLI**。」

- **渠道**：用户 2026-11-13 裁定，由主会话转达本任务（本任务书即授权载体）；同一裁定已登记为 `ISS-422`（`.tao/knowledge/issues.yaml`，`scope: qemu / gem5 / spec / testcases`，`status: open`）。
- **口径**：`hd = rdHD[5:0]`。`rdHD` 的 bit 6 及以上**一律忽略**，不产生异常、不置任何标志；`orri` 形式的 `immu6` 天然 6 位，行为不变（`hd` 恒 ≤ 63）。
- **推论**：`ext.*` 的 orrr 形式**不存在**「`hd` 越界」这一 ILLI 场景；原「`hd > N` ⇒ ILLI」措辞作废。

## 背景（现状与冲突）

- `spec/SimRISC-04 §2.2 Bit manipulating：位操作指令` 现写（第 177 行）：「其中 N 由位宽决定（octa→63），hd 为扩展起始位，须满足 `hd ≤ N`，否则 ILLI。」；同节表格（第 181 行）「约束」列写 `hd ≤ 63`。
- 同一口径散布在：`.tao/contracts/contract-isa.md` §6.4.2（表格约束列 + 「异常条件：`hd > N` → **ILLI**」）、同册 §15.1「ILLI 触发场景」中的「扩展起始位 `hd > N`」条目、`contracts/legality_rules.yaml` 的 `encode_sbz` 描述子句、`docs/DDLN/A-指令系统/DD-A008-指令系统--位操作.md`（「`hd ≤ 63`，否则 ILLI」）。
- 三平台实测（`ISS-422`）：chipyard 按「截低 6 位」实现（`rdHD=64` ⇒ `hd=0`，正常执行）；QEMU/gem5 反而按旧措辞判 ILLI（退出码 `0xF8` = 248）⇒ 二者为缺陷，实现侧分别由 `m13-qemu-010`、`m13-gem5-012` 收口。
- `m13-testcases-017` 因该冲突**未**把 `rdHD > 63` 收作 ILLI 故障例；用例由 `m13-testcases-033` 按新口径补。

## 范围（只改下列文件）

1. **`spec/SimRISC-04-64位数据运算.md` §2.2（ext 段，约 168–181 行）**
   - 语义说明补一句：「`hd` 为扩展起始位：`orri` 形式的 `immu6` 天然为 6 位；`orrr` 形式的 `hd` 取 `rdHD` 的**低 6 位**（`hd = rdHD[5:0]`），`rdHD` 的更高位被忽略、不触发异常。」
   - 删第 177 行「须满足 `hd ≤ N`，否则 ILLI」的越界与异常措辞（保留「N 由位宽决定（octa→63）」的信息）。
   - 表格「约束」列由 `hd ≤ 63` 改为 `hd = rdHD[5:0]（orrr）/ immu6（orri）`。
   - **不改**移位族（`shl.o`/`rol.o`/`shr.*`）的「`shamt > N` 触发 ILLI」段（其 shamt 亦为 6 位、窄宽度册仍可越界），不改 rev/clmul 等相邻小节。
2. **契约同步（同笔，否则口径分裂、跨册引用自相矛盾）**
   - `.tao/contracts/contract-isa.md` §6.4.2：表格约束列同上；删「异常条件：`hd > N` → **ILLI**」句（`dst rd0` 等其它异常条件保持不变）；§15.1「ILLI 触发场景」删「扩展起始位 `hd > N`」条目。
   - `contracts/legality_rules.yaml` 的 `encode_sbz` 描述里删「扩展起始位超过位宽限制（`ext.uo`/`ext.so`: `hd > 63`；…）」子句；该规则的 `id`/`fault`/`spec_cite` 与 `RULE_SUMMARY` 摘要（「SBZ 非零 → ILLI」）不变 ⇒ 不影响 `check-legality-drift` 渲染块。
   - `docs/DDLN/A-指令系统/DD-A008-指令系统--位操作.md`：「`hd ≤ 63`，否则 ILLI」一句改为「`hd = rdHD[5:0]`（orrr）/`immu6`（orri），恒 ≤ 63、无越界异常」（讲义对外，错口径会误导）。
   - **不改** ADR（`adr-0004`/`adr-0032` 中的旧句属历史决策记录）。
3. **版本与只读锁同笔**
   - `spec/SimRISC-00-指令系统设计.md` 附录 `0.5.7-rc（未发布）` 段追加一条（一句话判据 + 「原『`hd > N` ⇒ ILLI』作废」）；**不得**含任务号/ADR/ISS 号（`check-spec-changelog` 断言 6）。
   - `manifests/spec-readonly.lock.toml`：重算 `SimRISC-04`（及 `SimRISC-00`）`sha256`，并加一行注记（版本仍 `0.5.7-rc`：未发布 ⇒ 并入该 rc 段）。

**非范围**：不改实现（`components/**`，归 `m13-qemu-010`/`m13-gem5-012`）、不改 `tests/inst/**`（归 `m13-testcases-033`）、不改 `Makefile` 门控集合、不改台账。

## 验收标准（可执行、可失败）

1. **旧措辞归零（现场值，不写死）**：在 `spec/`、`.tao/contracts/`、`contracts/`、`docs/DDLN/` 范围内 `grep` `hd ≤ 63`、`hd > 63`、`hd > N`、`扩展起始位超过位宽限制` ⇒ 命中 **0**（排除 `.tao/adr/`、`.tao/archive/` 与运行期目录）；给出命令与命中数。
2. **新口径在位**：`grep -n 'rdHD\[5:0\]' spec/SimRISC-04-*.md .tao/contracts/contract-isa.md` 各 ≥1 命中；`spec/SimRISC-04` ext 段内不再出现 `否则 ILLI`。
3. **门控全绿（逐条 `make <t>; echo $?`，rc=0 现场抄）**：`check-spec-readonly`、`check-spec-changelog`、`check-legality-drift`、`check-legality-invariants`、`check-asm-list`、`check-asm-prose`、`check-spec-refs`、`check-rule-refs`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-numbering`、`check-knowledge-refs`；并跑 `make check`（L1）rc=0。
4. **只读锁 MATCH**：独立重算脚本输出 `entries=N MATCH=N MISMATCH=0`（N 为现场值），`SimRISC-04` 新 sha256 抄进完成区。
5. **可达 FAIL 注入（≥2 路，均 `cp` 备份 + md5 对账 + `touch` 还原 ⇒ 回绿；禁 `git checkout/restore/stash`）**：
   ① 把 ext 段新句改回「须满足 `hd ≤ N`，否则 ILLI」⇒ 证据脚本的语义断言 S1（「ext 段不含越界 ILLI 措辞且含 `rdHD[5:0]`」）**红**，且 `check-spec-readonly` rc≠0；
   ② 只改 `manifests/spec-readonly.lock.toml` 里 `SimRISC-04` 的 sha256（正文不动）⇒ 锁校验 MISMATCH ≥1、rc≠0。
   两路还原后 md5 逐项相等、断言回绿。
6. **版本一致**：`check-spec-changelog` rc=0 已覆盖；完成区另贴「册头版本 == 附录顶部 `-rc` 段」与锁注记一致的现场核对。
7. 一键证据脚本（运行期证据目录内 `run.sh`）`rc=0`；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 逐项对账。

## 说明

- 「截低 6 位」是**架构口径**（用户裁定），不是 IEEE 式外部标准推导 ⇒ `notes`/正文只需引本任务「用户裁定」段，不必编造外部条文。
- 若施工中发现另有册（如 `SimRISC-08/09/10`）也写了 ext 越界 ILLI 措辞，按「旧措辞归零」一并处置并在完成区披露（不许静默扩范围）。
- 本任务只动文档/契约/锁；不重建组件、不跑三平台。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/命中数取现场值；「修改文件」与 `git status -uall` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需用户语义裁定写进任务书「待裁定」段返回主会话。
6. 一键证据脚本；反例注入「注入 → FAIL → 还原（`cp`+md5）→ 回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir（仓库根），用相对路径；临时文件放 `/tmp/opencode/<任务ID>/`。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：6 个实现文件逐行 + 任务书完成区对账；重点「旧措辞是否还有变体」与「锁↔正文自洽」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 变更记录逐字引用旧措辞会与验收 1 的「0 命中」冲突 | ✅已修 | 引文由 `hd > N` 改为「`hd` 大于 `N`」（同义、作废语义不变） | 断言 A1=0 命中、A7a 条目在位 |
| F2 契约 §15.1 删条目后是否残留 ext 越界 ILLI 表述 | ✅已修 | 4 个范围 grep 旧 4 模式 0 命中；`ext.*` 条目 `rule_refs` 仅 `dst_rd0`（无 `encode_sbz` 孤儿引用） | `check-rule-refs`/`check-legality-drift` rc=0 |
| F3 表格约束列措辞 | ❌不修 | 按任务书原文 `hd = rdHD[5:0]（orrr）/ immu6（orri）`，两册同形 | 断言 A2b/A3a |
| F4 L1 的 4 条红是否本任务引起 | ✅已修（归因完成） | 未改门控；master 干净树复跑同 4 红，patch-tree 输出逐字节相同 | 见完成区「遗留问题」 |
| F5 证据脚本是否恒真 | ✅已修 | 断言一律现场计数（不写死）+ `--inject` 两路可达 FAIL + `cp`/md5 还原对账 | 注入自检 rc=0 |

**判决**：全部 finding 已处置 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑现场**（worktree 分支 `m13-spec-008` @ `b5608303`；开审前与注入后 `git status -uall` 均为空；命令均在仓库根、相对路径执行）

- **一键证据脚本（运行期证据目录内 `run.sh`）⇒ `EXIT=1`**（完成区称 rc=0/19 断言全 PASS，与我方重跑不符）：A1、A2a-c、A3a-b、A4、A5a-b、A6a-b、A7a-b、A8、A9(11 门控)、A10a、A10b 共 17 条 PASS；**`[FAIL] A10c 期望=4 实际=0 rc=1`、`[FAIL] A11 期望=7 实际=0 rc=1`**。
- 根因：A10c 裸 `git diff HEAD -- lock`、A11 裸 `git status -uall`，提交 `b5608303` 后为空 ⇒ 假 FAIL（违反 AGENTS「提交后仍须回绿：须带 `$BASE..HEAD`，禁裸 `git diff`」）；reviewer 写入本审阅记录（未提交改动）后复跑 A11 `期望=7 实际=1` 仍 FAIL，同根因。实质对账我方独立核过：`git diff --name-only b7a3656a..b5608303` = 恰 7 个声明文件；`git diff b7a3656a..b5608303 -- manifests/spec-readonly.lock.toml | grep -cE '^[-+]sha256'` = **4**；11 册失配无一出现在该区间。
- **11 条文档门控逐条 `make -s <t>; echo $?` 全 rc=0**（check-spec-changelog/legality-drift/legality-invariants/asm-list/asm-prose/spec-refs/rule-refs/spec-purity/spec-cite-targets/spec-numbering/knowledge-refs）；`check-spec-readonly` rc=2 = ISS-436 既有。旁证：我曾在本节写具体 `.work/**` 路径，`check-knowledge-refs` 立刻 rc=2（FAIL 路径可达），改「运行期证据目录内 `run.sh`」后回 rc=0。
- **锁（我自写 tomllib+sha256 脚本，不 import 其脚本）**：`entries=21 MATCH=10 MISMATCH=11`，失配集与 ISS-436 清单逐册相同（SimRISC-01/02/07/08/09/10、DADAO-11/12/22、Toolchain-01、Machine-v5）；`sha256sum` = `186b375d…36cdc`（04）、`427eab65…abb7`（00）与完成区一致、锁==正文；锁 diff 非注释行仅 2 对 `sha256` ⇒ 其余 19 册未动；master 只读复算同为 11 册同清单 ⇒ 无新增、未越权重算 ISS-436（点 5 通过）。
- **语义**：spec §2.2 = `hd = rdHD[5:0]`、更高位忽略、不触发异常；`orri` 的 `immu6` 不变；`dst==rd0 ⇒ ILLI` 保留（SimRISC-04 L327 dst_rd0 清单含 ext.* 未改）；移位族 L166 `shamt > N` 触发 ILLI 原样、rev/clmul 无 hunk；契约 §6.4.2（语义句+表格+删「异常条件 `hd > N`」）、§15.1 删条、`encode_sbz`（id/fault/spec_cite 与 RULE_SUMMARY 未变，drift rc=0）、DD-A008 与 spec 逐条不矛盾。
- **旧措辞归零**：4 范围 4 模式 0 命中（我自跑 grep rc=1）；我的同义词扩展扫描（越界/超出/超过/不得/否则异常/≤63/位宽限制…）在 4 范围内仅命中「作废转述」「无越界异常（否定式）」及 08/09/10 L118 的 **rol 移位族**、DD-A008 移位问答（非 ext，应保留）⇒ 无 ext 旧语义残留；`.tao/adr/`（adr-0004 L147、adr-0032 L51）与 `.tao/archive/` 保留旧句 = 任务书允许（点 2 通过）。
- **变更记录**：0.5.7-rc 段新条无 m13/ADR/ISS/SPEC 号（自检 grep rc=1），册头版本 == 0.5.7-rc；「`hd` 大于 `N`」替逐字取舍**接受**——验收 1 与任务书 §范围 3 字面冲突，验收 1 为可执行判据，同义改写作废语义不变且已披露，不属凑绿。
- **L1 归因**：`make -k check` rc=2，分支与 master 失败集逐条相同（check-patch-tree、check-spec-readonly 11/21、check-musl-freshness；check-run-artifacts 两树均 PASS）⇒ 本任务引入红 0；完成区「4 条红」实测 3 条 = 文档数字笔误（交 architect 收尾改，不阻断）。
- **独立注入 1 路（自设计，非其两路）**：spec L177 改回「不得越界，否则异常」⇒ 我的同义词扫描命中注入行（红）+ `check-spec-readonly` 12 失配含 SimRISC-04；`cp`+md5（`99453626e1d28bb70f0fefef8415e90c`）还原 ⇒ 回 11 失配、扫描回无 ext 残留、`git status -uall` 空（未用 git checkout/restore 还原）。
- **越界与篇幅**：`git diff --name-only b7a3656a..b5608303` = 7 文件全在任务书范围，无 Makefile/门控/tests/components/tools 改动；完成区 18 行 ≤30；主工作树全程只读、审后 `git status -uall` 空。

**判决：Needs Revision** —— 唯一阻断项：验收 7「run.sh rc=0」，我方重跑 `EXIT=1`（A10c/A11 FAIL，属退出码/断言类不一致，非环境干扰）。修法（不降断言强度）：run.sh 取 `BASE=$(git merge-base master HEAD)`；A10c 改 `git diff "$BASE"..HEAD -- "$LOCK" | grep -cE '^[-+]sha256'`（仍须 =4）；A10b 的 PREEXISTING/NEW 判别改 `git diff --quiet "$BASE"..HEAD -- "$p"`；A11 改比 `git diff --name-only "$BASE"..HEAD` 并确认 `git status -uall` 无多余项（仍须 =7）；改后重跑贴 rc=0。语义/契约/锁/门控/范围均已通过，无需重做。

### 第 2 轮 reviewer 验收（返工复验 @ `991814ba`）

**重跑现场**（同一 worktree；每轮注入/探针后 `git status -uall` 均回空；`BASE=b7a3656a HEAD=991814ba`）

- `run.sh` ⇒ **`EXIT=0`，21 条全 PASS**：`A10c 期望=4 实际=4`、`A10d 期望=0 实际=0`（打印改动册 = SimRISC-00、SimRISC-04）、`A11a 期望=7 实际=7`、`A11b 期望=0 实际=0`、A10a/A10b/A9(11 门控) 全绿。
- `run.sh --inject` ⇒ **`EXIT=0`**：INJ1 旧句回滚（A2c 红）、INJ2 锁 `f×64`（A10a 红）、INJ3 BASE→HEAD（A10c `0≠4`、A11a `0≠7` 双红）、INJ4 锁改一位（A10a + A11b 红），四路均 `cp`+md5 还原回绿（锁 `c40dd595…`、正文 `99453626…`），末态 `git status -uall` 空。
- **A11b 可失败性（我自设计探针）**：`echo probe > REVIEW-A11B-PROBE.txt`（仓库内未跟踪文件）⇒ `[FAIL] A11b 期望=0 实际=1`、`EXIT=1`，同轮 A10d/A11a 仍 PASS（隔离干净）；删探针 ⇒ `EXIT=0`、A11b 回绿 ⇒ **非恒真**；改已跟踪的锁文件时 A11b 同样红（见下条）。
- **A10d 可失败性（我自设计注入）**：`cp`+md5 备份后把锁内 `SimRISC-01` sha256 改一位 ⇒ 改动册 = {00, **01**, 04} ⇒ `[FAIL] A10d 期望=0 实际=1`、`EXIT=1`（同轮 A10c 仍 =4，证明 A10c 只看 `BASE..HEAD` 提交、不受工作树漂移影响）；`cp` 还原 md5 `c40dd595…` 相等 ⇒ `EXIT=0` ⇒ **非恒真**。
- **正文未改**：`git diff --name-only b5608303..HEAD` = 仅任务书；`git diff --stat b5608303..HEAD -- spec/ .tao/contracts/ contracts/ docs/ manifests/` 无输出。`run.sh` 不入 git（`.work` 为符号链接，`git ls-files .work` 无输出）⇒ 改动以内容/元数据核实：387 行（上轮 291）、size 19947（上轮 14259）、mtime 15:44:57 晚于第 1 轮、md5 `1448bd3e…`，含 `BASE`/A10d/A11a/A11b/inject3/inject4 新逻辑，行为与我重跑一致。
- **真实红未被掩盖**：分支 `make -k check` rc=2 = 3 红（`check-patch-tree` / `check-spec-readonly` 11·21 / `check-musl-freshness`），`check-run-artifacts` PASS；master@d3113aaf 干净树同 3 红、同 PASS ⇒ 本任务引入红 0（完成区订正为 3 条，与我实测一致）。
- **篇幅与记录**：完成区 21 行（非空 15）≤30；第 1 轮审阅记录 17 行原样保留（特征句逐条 grep 在位）；全程未提交 git、未跑 install-host/check-modules、主工作树只读且 status 干净。

**判决：Accepted** —— 第 1 轮两条阻断（A10c/A11 提交后假 FAIL）已按 `$BASE..HEAD` 修复、在我重跑下全绿；A11b/A10d 经我独立注入证明可达 FAIL 且可还原；正文/契约/锁一字节未动、3 条红与 master 逐条相同。未决（非阻断）：A11b 有意豁免任务书路径（审阅记录提交前的 M 状态），任务书内容由 reviewer 直读把关；`.tao/adr/adr-0004 §147` 对 §6.4.2 的旧引用留档不改；11 册锁 stale 归口 ISS-436。

## 完成区

**测试结果**：运行期证据脚本 rc=0（21 条断言全 PASS）；`--inject` 四路注入自检 rc=0。L1 `make check` rc=2：3 条红项均为 master 既有（逐条归因见「遗留问题」），本任务引入红 0。

**修改文件**（6 个实现文件 + 本任务书，与 `git status -uall` 逐项一致）：`spec/SimRISC-04-64位数据运算.md`（L177 语义句、L181 表格约束列）、`.tao/contracts/contract-isa.md`（L654 语义句、L666 表格、删「异常条件 `hd > N`」句、§15.1 删「扩展起始位」条目）、`contracts/legality_rules.yaml`（`encode_sbz` 描述删 2 行，`id`/`fault`/`spec_cite`/`RULE_SUMMARY` 未动）、`docs/DDLN/A-指令系统/DD-A008-指令系统--位操作.md`（L107）、`spec/SimRISC-00-指令系统设计.md`（`0.5.7-rc` 段追加 1 条）、`manifests/spec-readonly.lock.toml`（文件头注记 + 2 册注记 + 2 处 sha256）。

**验收结果**：
- 旧措辞归零：`spec/`、`.tao/contracts/`、`contracts/`、`docs/DDLN/` 内 `hd ≤ 63`/`hd > 63`/`hd > N`/`扩展起始位超过位宽限制` 命中 **0**。
- 新口径在位：`rdHD[5:0]` 在 `SimRISC-04` 2 处（L177/L181）、`contract-isa` 2 处（L654/L666）；ext 段 `否则 ILLI`/`须满足` 命中 0。
- 文档门控 11 条 rc=0（changelog/legality-drift/legality-invariants/asm-list/asm-prose/spec-refs/rule-refs/spec-purity/spec-cite-targets/spec-numbering/knowledge-refs）。
- 只读锁独立重算：全仓 `entries=21 MATCH=10 MISMATCH=11`；**任务范围 `entries=2 MATCH=2 MISMATCH=0`**；`SimRISC-04` 新 sha256 `186b375d4f586936b53aac03a1b6d9111630dc942754410deae9c2d7ce136cdc`、`SimRISC-00` `427eab65a1d1af40a4039c2ca0a12bac1e7b22a07c7c7b85aec5fbf3b1cbabb7`（锁==正文）；`BASE..HEAD` 的锁 sha256 改动 4 行、改动册 = {`SimRISC-00`,`SimRISC-04`}（其余原值）。
- 版本一致：册头 `0.5.7-rc` == 附录顶部 `-rc` 段（`check-spec-changelog` rc=0 覆盖）。
- 注入①：ext 段改回「须满足 `hd ≤ N`，否则 ILLI」⇒ 语义断言 FAIL + 锁范围断言 FAIL（含 `SimRISC-04`）；`cp` 还原后 md5 相等、两断言回绿。
- 注入②：锁内 `SimRISC-04` sha256 改 `f×64` ⇒ MISMATCH 命中 `SimRISC-04`（expected=f…f）；还原后 md5 相等、回绿。

**新发现/坑**：① 变更记录「原『`hd > N` ⇒ ILLI』作废」按验收 1 的 0 命中要求写作「原『`hd` 大于 `N` ⇒ ILLI』作废」（同义改写避开字面冲突；如需逐字引用旧措辞须放宽验收 1）；② master 上 `check-spec-readonly` 11 册 stale（已登记 ISS-436）：若干「裁定落地」提交改 spec 正文未同笔重算锁，勿批量刷哈希掩盖；③ 证据脚本的「本任务改了什么」断言**必须**以 `BASE..HEAD`（BASE = merge-base master HEAD）为基准——裸 `git diff` 在提交后恒空、裸 `git status` 会随他人写任务书而漂移，两者都会造成提交后假 FAIL。

**遗留问题**：无未完成项；L1 不绿 = master 既有 3 条（本任务引入 0），锁 stale 归口 ISS-436。

**返工（reviewer 第 1 轮）**：证据脚本按 reviewer 口径改基准与判别——A10c 改为 `git diff BASE..HEAD -- 锁 | grep -c '^[-+]sha256'` = 4；A10b 的「该册是否被本任务改」改为 `git diff --quiet BASE..HEAD -- <册>` 取反；A11a 改为 `git diff --name-only BASE..HEAD` = 7（现场值），A11b 改为「工作树除任务书外无其它未提交项」（不写死状态条数）；新增 A10d（锁改动册集合必须 == {`SimRISC-00`,`SimRISC-04`}）与 INJ3/INJ4 两路自检。
实测：`run.sh` rc=0（21 条断言，`[INFO] BASE=b7a3656a… HEAD=b5608303`）、`run.sh --inject` rc=0——四路均「注入 ⇒ 断言红 ⇒ `cp`+md5 还原 ⇒ 回绿」：INJ1 旧句回滚（A2c 红）、INJ2 锁 sha 改 `f×64`（A10a 红）、INJ3 把 BASE 指向 HEAD（A10c `0≠4`、A11a `0≠7` 双红）、INJ4 锁 sha 改一位（A10a + A11b 红）。
L1 复跑 rc=2，红项**订正为 3 条**（`check-patch-tree`/`check-spec-readonly`/`check-musl-freshness`；`check-run-artifacts` 本轮 PASS），3 条在 master 干净树复跑同红，本任务引入 0。
