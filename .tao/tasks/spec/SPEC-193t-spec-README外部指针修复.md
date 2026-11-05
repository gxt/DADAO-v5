# SPEC-193t: spec/README 精简后的外部指针修复

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-185t`（已验证；spec/README 已删除投影表/缺口表等非 spec 内容）
**状态**：已验证

## 执行环境
本地；只修文档指针，不改 spec 规范语义。

## 背景

`SPEC-185t` 删除了 `spec/README.md` 的投影表/缺口表等非 spec 内容，导致外部文档仍有指针指向已不存在的节/表。reviewer 现场确认仍悬空 5 处：

- `docs/Process-02-合约编写规范.md:20`：`spec/README.md`「登记缺口（显式 deferred）」表 / 投影表
- `docs/Process-06-spec目录保护规范.md:61`：`spec/README.md` 的历史版本表
- `.tao/knowledge/MEMORY.md:50`：`spec/README.md`（分册索引、投影/缺口表）
- `.tao/contracts/contract-asm.md:260`：`spec/README.md` 投影表 `Toolchain-01` 行 ③ 机械门控列
- `docs/README.md:26`：`spec/README.md` 投影表

已消解、无需改：根 `README.md:16`（册维护约定+版本号语义）、`docs/Process-02:34`（规范修订流程）、`MEMORY.md:17`。

## 目标

1. 逐处改为指向**现存**的 `spec/README.md` 节（如「分册清单」「册维护约定」「规范修订流程」），或删除指针并保留句子。
2. 不再引用已删除的「投影表」「登记缺口表」「历史版本表」。
3. 不新增 spec 内容，不把投影/缺口表搬回 spec/README。
4. 不改 spec 语义、ADR decision、contracts 数据、QEMU/gem5/tests。

## 范围 / 非范围

**在范围内**：`README.md`（若仍有悬空）、`docs/Process-02-合约编写规范.md`、`docs/Process-06-spec目录保护规范.md`、`docs/README.md`、`.tao/contracts/contract-asm.md`、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`。

**不在范围内**：`spec/**`、`.tao/adr/**`、`contracts/**`、QEMU/gem5/tests、门控脚本。

## 验收标准

1. **悬空清零**：上述文件不再引用 `spec/README.md` 的「投影表」「登记缺口表」「历史版本表」；改为现存节或删除指针。
2. **句子保留**：只删/改指针，不删整段技术结论；不新增内容。
3. **引用一致**：`check-knowledge-refs`、`check-spec-refs`（若扫到）rc=0；`make check`（L1）rc=0。
4. **反例可达 FAIL**：写回一处 `spec/README.md 投影表` ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原回绿。
5. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是 `SPEC-185t` 的收尾清理，不重新引入非 spec 投影表。
- 若某指针所在句子需要说明“投影已迁实现层”，用不带路径的描述，不再指向 spec/README 的已删表。
- 与 `SPEC-192t` 并行时只改不同文件；不改 `contract-see`/`Machine-v5`/ADR。

## 完成区

**测试结果**：运行期证据脚本 最终 rc=0，checks=13 / FAILS=0；审计（5 文件 534 行）禁用词命中 0；`make check-knowledge-refs` rc=0（ADR 533 + contract 79 已校验）、`make check-spec-refs` rc=0（0 violations）、`make check`（L1）rc=0（`repository checks (L1): PASS`）。
**修改文件**：`docs/Process-02-合约编写规范.md`、`docs/Process-06-spec目录保护规范.md`、`docs/README.md`、`.tao/contracts/contract-asm.md`、`.tao/knowledge/MEMORY.md`（5 文件 +6/-6，无新增内容）；`.tao/knowledge/milestones.md`（状态行）；本任务书（完成区/自审/状态）。`spec/**`、ADR、`contracts/**`、QEMU/gem5/tests 零触碰。
**验收结果**：① Process-02:20 两指针删除（改指"上表 `deferred` 各行"）；② Process-06:61 改指 `spec/SimRISC-00`「附录：版本与变更记录」（0.4.1/0.5.3 段实存）；③ docs/README:26 删 `spec/README.md` 投影表引用（保留另两引用）；④ contract-asm:260 删指针，三个门控名与 `[Toolchain-01 §12]` 原样保留；⑤ MEMORY:50 改指"分册清单、册维护约定、规范修订流程"（另将 :17 标签"投影表"改为"分册清单"）。反例：真树写回 `spec/README.md 投影表` ⇒ rc=1 并命中该行；`cp`+`md5sum -c` 还原 ⇒ rc=0、审计回绿；临时树逐 token（投影表/登记缺口/历史版本表/缺口表）各 rc=1，基线 rc=0。
**新发现/坑**：① `check-run-artifacts` 拒非 ASCII 日志名：首轮用 token 命名的日志致二轮 `make check` rc=2（A3 4 illegal），已改 ASCII 序号并清理旧日志 ⇒ rc=0（教训：证据日志名只用 `<TASK-ID>-<purpose>`）。② `spec/README.md` 的 `## 投影表` 节仍在（仅一句"投影落点属实现层"），故"悬空"是内容层而非节不存在层。③ 四类型投影规则（①叙述②机器数据③机械门控④可执行）在 SPEC-185t 后活文档仅剩 `.tao/archive/`，Process-02 该指针子句按"删指针"处理、未搬回。
**遗留问题**：范围外未改——`.tao/adr/adr-0013-assembly-syntax.md:217` 与 `tools/infra/check_spec_refs.py:41-42` 仍写"`spec/README.md` 投影表"（任务书禁改 ADR / 门控脚本）；根 `README.md:43`"投影表缺口清零"为 M2 史实陈述、非路径指针，未改。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据日志用中文 token 命名，违反 `check-run-artifacts` A3 | ✅已修 | `run.sh` 改用 ASCII 序号 `pattern-$i`，删除 4 个非法旧日志 | 重跑 `make check` rc=0（日志 `SPEC-193t-make-check.log`）；失败原因 A3 已直接列出 |
| F2 审计中 docs/README 的保留断言只查文件名，偏弱 | ✅已修 | anchor 改为整句"**FP 独立 oracle 方案**（被 `contract-fp.md`…）" | `audit.py` rc=0（18 项 0 FAIL） |
| F3 MEMORY:17 仍含"投影表"标签（任务书列"已消解"） | ✅已修（披露） | 同批改为"分册清单"，使该文件对禁用词清零 | 审计命中 0 |
| F4 删除"四类型投影落点"子句是否算删结论 | ❌不修 | 该子句仅为指针；四类型定义已随 SPEC-185t 删除，按任务"删指针"处理、不新增内容 | diff 仅删指针，其余结论原样 |

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲跑，workdir=任务 worktree，均取真实 rc；未用 `cmd | tail` 取码）**

- `make check-knowledge-refs` ⇒ rc=0（`小节级: ADR 533 + contract 79 已校验`、悬空 0）
- `make check-spec-refs` ⇒ rc=0（`结果: PASS (0 violations)`，总引用 1084 / 失败 0）
- `timeout 2400 make check` ⇒ rc=0（`repository checks (L1): PASS`）
- 运行期证据脚本 ⇒ rc=0，`checks=13 FAILS=0`（三次：初跑 / 还原后 / 终跑均同）；审计日志 `行 534，命中 0（期望 0）、检查项 18、FAIL 0` —— 与完成区 13/13、534 行、+6/-6（`git diff --stat`：5 文件 content 6+/6-）、ADR 533+contract 79、0 violations 逐条一致，无美化
- **独立反例注入①（真树、非 engineer 自检）**：`cp MEMORY.md .bak`+`md5sum` ⇒ 追加 `见 spec/README.md 投影表`（md5 变）⇒ 重跑 `run.sh` ⇒ **rc=1，FAILS=3**，`[A] 命中 1`：`.tao/knowledge/MEMORY.md:80: 「投影表」`；`cp` 还原 ⇒ `md5sum -c` OK（`179b2f53…` 与注入前快照相同）⇒ 重跑 `run.sh` ⇒ rc=0 / 13-13
- **独立反例注入②（anchor 可达 FAIL）**：删 §12 行 `[Toolchain-01 §12]` ⇒ audit rc=0（文件内第 7 行仍有同名 tag）；**全删两处** ⇒ rc=1 `FAIL anchor not found`；`cp`+`md5` 还原 ⇒ OK
- **快照对账**：`git status --porcelain -uall` 7 个 ` M`（与任务书「修改文件」声明逐行一致）、无未跟踪残留；7 文件 `md5sum -c` 前后快照全 OK（注入已还原）；HEAD 仍 `e43828e4`，reviewer 未 commit/push

**约束核验**：① 5 处悬空清零 ✅ —— 5 文件 `grep 投影表|登记缺口|历史版本表` rc=1（0 命中）；Process-02:20 改「上表 `deferred` 各行」（表内确含理由/触发）；Process-06:61 改 `spec/SimRISC-00`「附录：版本与变更记录」（节 395 行实存，0.4.1/0.5.3 段 440/471 行实存）；docs/README:26 保留另两引用且二者确实引用 fp-oracle-design ✅；contract-asm:260 三门控名+issues.yaml+`[Toolchain-01 §12]` 原样（**只改指针、技术结论未动**）✅；MEMORY:50 改三节且三节实存 ✅。② MEMORY:17「投影表→分册清单」合理 ✅ —— `spec/README.md` 有 `## 分册清单`(12)，`## 投影表`(60) 仅存一句锚点，标签不再指空表、无悬空语义。③ 范围 ✅ —— `git diff --stat` 仅 7 文件，无 `spec/**`、`.tao/adr/**`、`contracts/**`、QEMU/gem5/tests。④ 体例 ✅ —— 完成区 5 行（≤30）、状态/里程碑均 `待验收`、无绝对运行期路径（grep rc=1）。

**范围外残留（实测真残留，未清零，须另立任务/收尾处置）**：
- `.tao/adr/adr-0013-assembly-syntax.md:217` 仍写「`spec/README.md` 投影表 `Toolchain-01` 行 ③」——该列已随 SPEC-185t 删除，**内容层悬空**；ADR 改动须用户逐条确认 ⇒ 建议 architect 立任务。
- `tools/infra/check_spec_refs.py:41-42` 注释仍写「见 spec/README.md 投影表」——悬空注释，门控脚本禁改本任务范围 ⇒ 建议随上项一并处置。
- 根 `README.md:43` 位于 `### M2（2026-10-04）…` 里程碑史实段、不带 `spec/README` 路径 ⇒ 判为史实陈述、**不改正确**（与 engineer 判断一致）。
- 另：`spec/README.md:60 ## 投影表` 仍为一句空锚点（SPEC-185t 裁定保留），与根 README「投影表缺口清零」的口径关系归 architect 收尾统一（`spec/**` 本任务禁改）。

**Finding（均不阻断）**：R1 上述 3 处范围外残留须另立任务；R2 证据脚本 anchor 断言为**文件级包含**，行级漂移不红（实测删 §12 行 tag 仍 rc=0，全删才 FAIL）——建议后续改行级断言；R3 Process-06 新指针不含旧表「提交/归档目录/同号冲突」列，但同 bullet 的 `gen_spec_archive.py --list` 清单列含「来源仓库」，来源口径仍闭环（文档级精度提示）；R4 任务书完成区/自审数字经重跑逐条对齐，无笔误。

**判决：Accepted** —— 验收标准 1-5 在 reviewer 自己的重跑下全部通过（门控 rc=0、证据 13/13、反例 注入→FAIL→还原→回绿 均有真实输出），硬约束无违反；范围外残留已如实登记、不掩盖。

#### 收尾（architect，2026-11-05）

- R1：范围外残留 `adr-0013:217` 与 `check_spec_refs.py:41-42` 另立/并入 `SPEC-191t`（ADR 改动须用户逐条确认）；根 `README.md:43` 为 M2 史实，不改。
- R2：证据脚本 anchor 断言为文件级包含，行级漂移不红；记入遗留，后续改行级。
- R3：Process-06 指针精度提示记入遗留，不阻断。
- 判决 Accepted，状态置 `已验证`。
