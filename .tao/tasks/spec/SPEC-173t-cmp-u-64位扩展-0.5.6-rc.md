# SPEC-173t: `cmp.{ut,uw,ub}` 的 -1 改为 64 位全 1（0.5.6-rc）

**模块**：spec
**项目里程碑**：M10
**依赖**：ADR-0037（已 Accepted）
**状态**：已验证

## 执行环境
**执行环境**：本地（纯文档，无构建）

## 接口规范

### 背景（ADR-0037，用户原话）
- 原文 `SimRISC-08/09/10 §1.2` 写「`.ut/.uw/.ub ⇒ 结果零扩展」⇒ `cmp.ut(-1)` = `0x00000000FFFFFFFF`，`br.n`（看 bit63）判负失效。
- 用户裁定：**-1 结果按 64 位扩展（全 1）**；版本 `0.5.6-rc`，`-rc` 不归档。
- 用户另指出：`SimRISC-00` 第 255 行「SimRISC 0.5.4版本的指令 opc 布局如下」**不应带版本号**。

### 输出（逐条）
1. `spec/SimRISC-08 §1.2`、`SimRISC-09 §1.2`、`SimRISC-10 §1.2`：
   - 高位规则改为：**-1 ⇒ 64 位全 1（符号扩展）；0 ⇒ 0；+1 ⇒ 1**；源操作数仍按 width 截断；`.st/.sw/.sb` 不变。
   - 同步修正该段的例子文字。
2. `spec/SimRISC-00` 第 255 行：删去「0.5.4」，改为不带版本号的表述。
3. **13 册**版本头 `**版本：0.5.5**` → `**版本：0.5.6-rc**`（含 `SimRISC-00`）。
4. `spec/SimRISC-00` 变更记录：新增 `### 0.5.6-rc（2026-10-25）` 段（在 `### 0.5.5` 之前），记「修正 `cmp.{ut,uw,ub}` 的 -1 扩展（原文零扩展为错误）」。
5. `.tao/contracts/contract-isa.md` 的 `cmp.*` 行补「-1 = 64 位全 1」口径（若其版本头需同步，按门控提示）。
6. `manifests/spec-readonly.lock.toml`：按 `tools/infra/check_spec_readonly.py` 提示更新被改文件的 sha（**用户已授权本次 spec 修改**）。
7. **不建** `.tao/archive/SimRISC-0.5.6-rc/`（`-rc` 不归档）。

### 约束
- 只改上述文件；不改其它 spec 册正文。
- 若 `check-spec-drift` / `check-spec-changelog` 要求额外同步（如契约头版本），按提示处理并记完成区。

## 验收标准
1. `make check`（L1：`check-spec-numbering` / `check-spec-changelog` / `check-spec-purity` / `check-spec-cite-targets` / `check-spec-drift` / `check-spec-readonly`）rc=0。
2. `python3 tools/spec/gen_spec_archive.py --verify` rc=0（0.5.6-rc 应 `SKIP`）；`check_spec_archive.py` rc=0。
3. 13 册版本头一致为 `0.5.6-rc`；`SimRISC-00` 第 255 行无版本号（贴改后行）。
4. 08/09/10 三处 §1.2 文字与 ADR-0037 一致（贴 diff）。
5. 完成区贴真实命令、输出、退出码。

## 完成区
**测试结果**：pass（`make check` rc=0；`gen_spec_archive.py --verify` rc=0；`check_spec_archive.py` rc=0；spec 七门控 rc=0；一键证据 ALL PASS/rc=0，6/6 注入「基线 PASS→注入 FAIL」）。
**修改文件**：`spec/SimRISC-00`…`-12`（13 册册头 `0.5.5 → 0.5.6-rc`；00 另改第 255 行 + 新增 0.5.6-rc 段）；`spec/SimRISC-08/09/10` §1.2；`.tao/contracts/contract-isa.md` §10.2/§11.2/§12.2；`manifests/spec-readonly.lock.toml`（13 册 sha256 + 授权注释）；`.tao/tasks/spec/SPEC-173t-*.md`（状态/完成区/自审）；`.tao/knowledge/milestones.md`（流水状态同步，`check-milestones-fresh` 要求）。
**验收结果**：
- 13 册版本头：`grep -h '版本：' spec/SimRISC-*.md | sed 's/（与 SimRISC-00 一致）//' | sort | uniq -c` → `13 > **版本：0.5.6-rc**`；`check-spec-changelog` rc=0，`simrisc_header_versions=['0.5.6-rc']`。
- `SimRISC-00` 第 255 行（改后）：`SimRISC 的指令 opc 布局如下。空白单元格表示 reserved（保留未分配）。`（无 `0.5.4`）。
- 三处 §1.2（改后规则行）：08 =「比较结果（−1/0/+1）**按 64 位扩展**写满目的寄存器——−1 ⇒ `0xFFFF_FFFF_FFFF_FFFF`（64 位全 1）、0 ⇒ `0`、+1 ⇒ `1`；`.st`/`.ut` 结果相同…源操作数仍按上述位宽截断后比较」；09 `.sw`/`.uw`、10 `.sb`/`.ub` 同式；三册例子同步为「…rd1 = 0xFFFF_FFFF_FFFF_FFFF / 0 / 1」。完整 diff：`.work/log/spec/SPEC-173t-diff.log`。
- `make check`（L1）：末行 `repository checks (L1): PASS`，rc=0（`.work/log/spec/SPEC-173t-make-check.log`）。
- `python3 tools/spec/gen_spec_archive.py --verify`：`OK SimRISC-0.5.5`、`SKIP SimRISC-0.5.5-rc`、`SKIP SimRISC-0.5.6-rc`，rc=0（0.5.6-rc 按 `-rc` 跳过；无归档目录）。
- `python3 tools/spec/check_spec_archive.py`：`PASS（声明 7 个版本目录，磁盘 8 个，A3/A4 启用）` rc=0；未建 `.tao/archive/SimRISC-0.5.6-rc/`。
- 一键证据：`bash .work/evidence/SPEC-173t/run.sh` → `SPEC-173t evidence: ALL PASS` rc=0（`.work/log/spec/SPEC-173t-evidence-full.log`）。
**新发现/坑**：
- rc 段标题：任务书写 `### 0.5.6-rc（2026-10-25）`，但 `spec/README.md`「册维护约定」与既有 6 个 rc 段一律 `### <ver>-rc（未发布）`（发布时去 `-rc` 并补发布日期），故取 `（未发布）`；发布动作不受影响。
- `tools/spec/check_spec_purity.py --self-test` 锚点仍写 `> **版本：0.5.5-rc**`，自 0.5.5 发布起即 `AssertionError`（HEAD 复现，非本次引入；不在 `make check` 内，改工具属越界）。
- 合约头保持 `0.5.5`：`check-spec-drift` 以根 README「已发布版本」比对，升 `0.5.6-rc` 会红（Process-06 口径：正式发布再升）。
- 任务书状态改 `待验收` 后 `check-milestones-fresh` 会红（流水表状态须一致）；已把 `milestones.md` SPEC-173t 行改为 `待验收`、时间列保留登记时间。
**遗留问题**：
- 根 `README.md`「在研版本」列仍 `0.5.5`（未授权改 README，越界未动）——建议收尾/发布时同步。
- 跨任务：QEMU-074t（去三条零扩展）、TESTCASES-065t（向量期望值改全 1 + `cmp.ut→br.n` 用例）、LLVM-133t（补断言）按本口径跟进；本次只改 spec + 合约 + 锁。

## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**：13 册册头、`SimRISC-00` 第 255 行 + 附录、08/09/10 §1.2、合约三行、lock 13 sha、证据脚本三件。
**逐行要点**：① §1.2 与 ADR-0037 D1 逐项对齐（−1 全 1 / 0 / +1 / 源按 width 截断 / `.s<size>` 不变）；② 例子 `0xFFFF_FFFF_FFFF_FFFF` 与规则一致，§1.2 内无「零扩展」残留；③ changelog rc 数值 = 下一段 z+1（0.5.6 vs 0.5.5），无任务号/表格；④ lock 仅 13 册 sha 变动，其余 8 册条目未动；⑤ 证据脚本每条断言可达 FAIL（6 例注入逐一命中）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| rc 段标题与 `spec/README`「册维护约定」冲突（任务书给日期） | ✅已修 | 取 `（未发布）` | `check-spec-changelog` rc=0；既有 6 段同式 |
| 合约头是否随 0.5.6-rc 升版 | ❌不修（有据） | 保持 `0.5.5` | `check-spec-drift` 以 README 已发布版比对；升则红 |
| 根 README「在研版本」未同步 | ⏸延后（越界） | 未改 | `git status` 无 README 条目 |
| `gen --verify` 未列 0.5.6-rc（git 派生、未提交） | ✅已核 | 无代码改 | 0.5.5-rc 的 `SKIP` 行证明 -rc 分支生效 |
| `check_spec_purity --self-test` 锚点失效 | ⏸延后（pre-existing/越界） | 未改 | `git show HEAD:…` 版本为 `0.5.5`，anchor 为 `0.5.5-rc` ⇒ HEAD 即失败 |
| 证据脚本注入是否假绿 | ✅已验 | `inject.py` 空注入即非零 | 6/6 例 `[FAIL]` 命中，各例基线全 PASS |

**判决**：与本次改动相关的 finding 全部处置（修复 / 有据不修）；延后两项非本任务引入且越界（README、tools）。状态 → `待验收`。

#### 第 1 轮 reviewer 验收

**核验方式**：本 reviewer 会话无 shell（`execute` 无 shell/run/exec；嵌套子代理超深度上限），5 条验收命令与独立反例由**主会话代行执行**（环境限制，非交付物缺陷）；我**逐行读取 6 个真实日志**核对 rc 与关键行（非采信完成区转述），并叠加我自带 `grep`/`read` 完成的**文件级独立核验**。

**① 主会话代行的 5 命令（我读日志核 rc/关键行）**：
- `make check`（L1）→ `.work/log/spec/SPEC-173t-main-L1.log` 末行 `repository checks (L1): PASS`；内含 `spec drift check: PASS`、`check-spec-readonly: 21 volume(s) OK`、`check-spec-changelog: PASS … simrisc_header_versions=['0.5.6-rc']`、`check-spec-archive: PASS`、`check-spec-purity: hits=0`、`check-milestones-fresh: PASS` ⇒ rc=0 ✓
- `gen_spec_archive.py --verify` → `OK SimRISC-0.5.5` / `SKIP 0.5.5-rc` / **`SKIP 0.5.6-rc`**（`-rc` 不纳入校验；无 0.5.6-rc 归档目录）rc=0 ✓
- `check_spec_archive.py` → `PASS（声明 7，磁盘 8，A3/A4 启用）` rc=0 ✓
- `tools/infra/check_spec_readonly.py` → `21 read-only spec volume(s) OK`（**13 册 sha256 与 lock 实测一致**）rc=0 ✓
- `evidence run.sh` → C1-C6 = 8/8 PASS；7 spec 门控 + gen-verify + make-check-full 全 rc=0；**6/6 注入例**均「注入后 rc=1（1 项命中）」= 基线 PASS→注入 FAIL；末行 `SPEC-173t evidence: ALL PASS` rc=0 ✓

**② 我的独立反例 `/tmp/opencode/SPEC-173t-review/inject.py`（主会话代跑，我读日志）**：
- 场景1（08 §1.2 改回零扩展）：注入后 `check_spec_readonly` **rc=1**（MISMATCH 捕获）→ 还原后 `21 volume(s) OK` rc=0，`md5.restored==md5.before` `RESTORE-OK` ✓
- 场景2（12 册头 0.5.6-rc→0.5.5）：注入后 `check_spec_changelog` **rc=1**（`互锁组 …册头版本不一致: ['0.5.5','0.5.6-rc']`）+ readonly rc=1 → 还原后 changelog rc=0（`['0.5.6-rc']`）+ readonly `21 OK` rc=0，md5 一致 ✓
- 两场景均**红→绿→md5一致**，非恒真；日志顶部 1-4 行 MISMATCH 系注入期 stderr/stdout 交错缓冲，非残留（各场景还原后 readonly 均 `21 OK`）。

**③ 我自带工具的文件级独立核验（非采信完成区）**：13 册头 `0.5.6-rc`（grep 13/13）；`SimRISC-00` L255 无 `0.5.4`；08/09/10 §1.2 =「−1 ⇒ 全 1 / 0 / +1，源仍按位宽截断，.st/.sw/.sb 同值」与 ADR-0037 D1 逐项一致、cmp 段无「零扩展」残留；合约 L963/1040/1117 三行一致；无 `SimRISC-0.5.6-rc/` 归档；purity 全量 grep 禁用词 0 命中。**两处判断有据**：① rc 段「未发布」= `spec/README.md` L135 册维护约定；② 合约头 `0.5.5` = `check_spec_drift.py` 比对 README 已发布列（L9=0.5.5），升 `0.5.6-rc` 即红。

**次要发现（文档级，不阻断）**：完成区 L48 预测 `--verify` 暂不列 0.5.6-rc，实际出现 `SKIP SimRISC-0.5.6-rc`（`-rc` 处理正确、rc=0、无归档目录，仅措辞预判不准）；任务书 readonly 路径 `tools/spec/` 有误（实为 `tools/infra/`），主会话收尾改。

**判决：Accepted**。验收命令块在真实日志下全绿（rc=0）、独立反例红→绿→md5一致、文件级核验与 ADR-0037 逐项吻合、无任何交付物缺陷；命令由主会话代行系环境限制，我已核真实日志非转述。架构师可终审收尾。
