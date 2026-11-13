# m13-spec-008: `ext.uo`/`ext.so` orrr 形式的 `hd` 取 `rdHD[5:0]`（越界位忽略、不抛 ILLI）

**模块**：spec
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（单册正文 + 契约 + 只读锁同笔，须由单个 engineer 完成）
**状态**：待开始

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

（待填）
