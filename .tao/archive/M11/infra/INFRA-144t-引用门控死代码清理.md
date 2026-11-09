# INFRA-144t: `check_knowledge_refs.py` 死代码清理（ISS-353）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-135t`（已合入）
**状态**：已验证

## 背景

`INFRA-135t` 把「具体 `.work/**` 引用」改为一律 FAIL 后，`check_knowledge_refs.py` 留下两处死代码：

- `checked` 计数只写不读；
- (A) 面的 `dangling` 分支已不可达（具体路径不再做存在性检查）。

`ISS-353` 记录了这两项。

## 目标

- 删除死代码/死计数，**不得改判据**：具体引用一律 FAIL、四类豁免（占位/前缀/构建源码/删除语境）、`found == 0` 空转、(B) 小节级判定，全部保持原语义。
- 输出里不再出现 `悬空: N`（A 面）这类无意义行；`[ISS-352]` 段落保留。

## 验收

1. `python3 tools/infra/check_knowledge_refs.py` rc=0；fresh 树（`git archive`）`--root` rc=0。
2. 行为等价：注入「本机存在的具体 `.work` 引用」⇒ rc=1；删除全部 `.work` 引用 ⇒ rc=1（vacuous）；两者 `cp`+md5 还原回绿。
3. `make check`（L1）rc=0（并发任务红需核实归属）。
4. 关闭 `ISS-353`；完成区 ≤30 行、无运行期路径。

## 完成区

**测试结果**：一键证据脚本 42/42 通过；当前树 rc=0；fresh 树（`git archive`）`--root` rc=0。L1 仅两处非本改动项红：`check-patch-tree`（并发 `INTEG-060t` 改共享 gem5 源树，`se_workload.cc` 未提交）、`check-milestones-fresh`（本任务台账行仍在「待开始」表）；其余 48 项成员全绿（rc=0），`check_issues` 与 `compileall -q tools` 亦 rc=0。

**修改文件**：`tools/infra/check_knowledge_refs.py`、`.tao/knowledge/issues.yaml`（关闭 `ISS-353`）、本任务书。

**验收结果**：
1. 删除死代码：`checked` 局部计数（含自增）、(A) 面 `dangling` 列表与不可达分支、A 面 `悬空: N` 输出行、`audit_section_refs` 返回字典中只写不读的 `"checked"` 键；判据未改（四类豁免、一律 FAIL、`found==0` 空转、(B) 小节级判定逐项保留）。
2. 行为等价：新旧脚本在同一树上逐标签比对，全部计数一致，唯一差异 = 被移除的 A 面死行；具体引用注入下新旧同 rc=1，删光引用下新旧同 rc=1（vacuous）。
3. 注入①（具体 `.work` 引用，指向本机确实存在的文件）⇒ rc=1 且 `[ISS-352]` 段列出位置；`cp` 还原 + md5 逐字一致后回绿。
4. 注入②（临时树删光全部 `.work` 引用）⇒ rc=1，报 `vacuous: no .work/** refs scanned`，且 (B) 面未空转（排除他因）；还原后回绿。
5. 反例可达：旧版脚本命中死代码 5 处、输出含 A 面死行 1 条；计数比较器对「伪造差异」「新旧对调」均判 FAIL。

**新发现/坑**：`check-patch-tree` 要求共享 gem5 源树工作树干净，任一 gem5 任务并发写该树即红；`git read-tree` 的临时索引写满盘时报 rc=128（非 patch 语义问题），给 `TMPDIR` 换盘即可。

**遗留问题**：① `Makefile` 中 `check-knowledge-refs` 目标上方注释仍写「其余具体路径要求存在」（`INFRA-135t` 遗留的过时描述），本任务范围仅限脚本，未改，建议后续订正。② 台账 `INFRA-144t` 行仍在「待开始」表（派单时应移入「进行中」），按分工由主会话维护、本次未动；移动后 `check-milestones-fresh` 回绿。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

**判决**：可交验收（改动仅删死代码/死计数 + 同步文档措辞；判据与输出计数不变）。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| `checked` 局部计数只写不读 | ✅已修 | 删声明与自增 | 源码死代码探针命中 0；旧版命中 5 |
| (A) 面 `dangling` 列表恒空、分支不可达 | ✅已修 | 删列表、`if dangling` 分支与 A 面 `悬空: N` 打印 | 新旧计数逐标签等价，仅差该死行 |
| 返回字典 `"checked"` 键无消费者 | ✅已修 | 删键 | 全仓 grep 无读取点；门控 rc=0 |
| 注释/文档仍引用已删变量与旧判据 | ✅已修 | 同步判据顺序注释、空转理由措辞、docstring (A) 标题与摘要、PASS 行措辞 | diff 逐行核对；证据脚本 C2/C3 全过 |
| 输出仍打印 A 面 `悬空: N`（恒 0） | ✅已修 | 删该行，(B) 面 4 空格 `悬空` 行保留 | C2a=0 / C2b=1（旧版反例）/ C2c=1 |
| 删除是否改变行为 | ✅已验证 | 未改任何判定表达式 | 注入两种情形新旧 rc 相同；fresh 树 rc=0 |

**未修项**：无（`Makefile` 过时注释属任务范围外，见完成区遗留问题）。

### 第 1 轮 reviewer 验收（2026-11-08）

**判决：Accepted**（判据一行未改；新旧行为等价；两条单独问答见文末）

**重跑记录（本人执行，非采信完成区）**

1. **判据对照**：`git show HEAD:tools/infra/check_knowledge_refs.py` 导旧版，token 级 diff（去注释/文档串）= 6 块，全为删死代码（返回字典 `"checked"` 键、`checked = 0`、`checked += 1`、A 面 `print(悬空: N)`、`if dangling` 分支）+ PASS 行文案；`_classify` / `_PLACEHOLDER_CHARS` / `_DELETION_MARKERS` / `_EXEMPT_PREFIXES` 与 HEAD 逐字 md5 相同；`found == 0`、`vacuous_faces`、`if sec["dangling"]`、`[ISS-352]` 段逐字未动；全仓无 `sec["checked"]` 消费点、无解析该脚本 stdout 的脚本。
2. **基线**：新版 `python3 tools/infra/check_knowledge_refs.py` rc=0；旧版 `old.py --root .` rc=0；两版输出 diff 仅 2 行 = A 面 `  悬空: 0` 删除 + PASS 文案；四类豁免计数（占位 44 / 前缀 2 / 构建 23 / 删除 1）、具体 0、ADR 539 + contract 82 逐标签相同。
3. **注入①**（我自选载体 `.tao/contracts/contract-elf.md` 追加指向本机存在文件的 `.work/…`，`cp -p` 备份）：新 rc=1、旧 rc=1，`[ISS-352]` 段列出 `contract-elf.md:291`，结论 `FAIL (1 具体 …)`；`cp -p` 还原 + `md5sum -c` OK，回绿 rc=0。
4. **注入②**（自建 `git archive` 树，`re.subn` 删光 69 处 `.work` 引用，独立 `grep -rEo` 复核余 0）：新 rc=1、旧 rc=1，同 `FAIL (vacuous: no .work/** refs scanned)`；两版输出 diff 仅 A 面死行 1 条。
5. **fresh 树**：`git archive HEAD` 导出（无 `.work` 目录）+ 新版脚本 `--root` ⇒ rc=0。
6. **证据脚本**：一键证据（`.work/**`，路径不入库）⇒ `汇总: PASS=42 FAIL=0`、exit 0；C3b/C3c 比较器方向性、C7b 旧版死代码命中 5 处均实测可达。
7. **L1**：`make -k check` ⇒ `L1_EXIT=2`，红恰两处：`check-patch-tree`（共享 gem5 树仅 `src/arch/dadao/se_workload.cc` 脏 ⇒ 并发 `INTEG-060t`）、`check-milestones-fresh`（`INFRA-144t` 行仍「待开始」而册=待验收，台账归主会话）；`_locked-check` 50 成员中 48 绿（含 `check-knowledge-refs` rc=0）；`check_issues` rc=0（2 open / 13 closed）、`compileall -q tools` rc=0。

**约束核验**：判据未改 ✅｜四类豁免 / 一律 FAIL / `found==0` 空转 / (B) 小节级判定逐字同 HEAD ✅｜`ISS-353` 已 `closed`（`resolved_by=INFRA-144t`）✅｜完成区 16 行 ≤30、无运行期路径 ✅｜台账行未动，`git status` 仅 3 文件、与完成区「修改文件」声明一致 ✅｜两次注入均 `cp`+`md5` 还原，审查前后工作区快照逐字相同 ✅。

**非阻断发现**：① `Makefile:1208` 注释「其余具体路径要求存在」仍为 INFRA-135t 过时描述（engineer 已披露、范围外）；② 证据脚本 C4c/C5b 属夹具性质断言、无真实 FAIL 路径，其余 40 项均有可达 FAIL，不阻断。

**自纠留痕**：本审阅记录初稿写了具体证据脚本路径 ⇒ 新旧两版同时 rc=1（反向印证「一律 FAIL」判据生效）；已改为占位形并复跑，新旧均 rc=0、输出 diff 仍仅 A 面死行 1 条。

**① 判定逻辑是否真的一行未改**：是——token 级对照仅 5 处死代码删除 + 1 处 PASS 文案改动，判定表达式零改动。
**② 新旧行为是否等价**：是——基线 / 注入① / 注入② 三种情形新旧 rc 与输出逐项一致，唯一差异为被删的 A 面 `  悬空: 0` 死行。

#### 收尾（architect，2026-11-08 16:23）

- 判决 Accepted：reviewer token 级对照确认**判定表达式零改动**（四类豁免、具体引用一律 FAIL、`found==0` 空转、(B) 小节级、`[ISS-352]` 段全同；`_classify` 等与 HEAD md5 相同），仅删 5 处死代码 + 1 处 PASS 文案。
- 行为等价三例（基线 / 注入具体引用 / 删光引用 vacuous）新旧 rc 与输出逐项一致，唯一差异是被删的 A 面 `悬空: 0` 死行。
- F1：`Makefile` 注释已同步为「具体路径一律 FAIL（不可复现）」（master `000b33b2`）。
- F2：证据脚本 C4c/C5b 属夹具断言，记录不阻断。
- `ISS-353` 关闭；台账行由主会话维护（已在本任务合并时置「已验证」）。
