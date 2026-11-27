# m17-infra-002: `check-spec-refs` 扩展非 SimRISC 前缀（ISS-521）

**模块**：infra
**项目里程碑**：M17
**依赖**：`m17-infra-001`（标题型引用校章号）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`ISS-521`（P3，`m17-infra-001` 复核发现）：`check-spec-refs` 的 `_PREFIX_ANCHOR` 只覆盖 `SimRISC-*` 等在册前缀；`[Kaiwu §…]` 等非 SimRISC 册的**标题型引用**仍不校章号（HEAD 即如此）。`m17-infra-001` 只收紧了在册前缀。

## 要做

1. 扩展前缀集：至少 `Kaiwu`、`DADAO-12`/`13`/`22` 等实际出现的前缀（以现场 `grep` 为准，不写死猜测）；
2. 处理 `§` 与中文节名混排、范围/字母附录等形态：可判定的同时校章号与标题；不可判定的显式打印跳过原因（不静默）；
3. `--self-test` 增两路：`[Kaiwu §9.9 正确标题]` ⇒ FAIL；正确章号 ⇒ PASS；
4. 收紧后跑全量：若暴露存量错误，逐条列清单（含文件/行/实际节号），本任务**不批量改正文**，交主会话另立任务。

## 不做

- 不改 spec 正文；不改 `m17-infra-001` 的在册前缀行为。

## 约束

- 独立 `git worktree`；不提交 git；只动 `tools/infra/check_spec_refs.py`、`docs/Process-07`、本任务书；完成区 ≤30 行。

## 验证

1. `make check-spec-refs` rc=0（或暴露存量错误时给逐条清单）；
2. `--self-test` 全过；
3. **可达 FAIL**：构造 `[Kaiwu §9.9 …]` 注入 ⇒ 红；`cp`+md5 还原回绿；
4. 扫描面/跳过项计数现场派生。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` 37/37 通过（rc=0）；`make check-spec-refs` rc=0（引用 1416 / 失败 0）；`--self-test` 9/9；`check_spec_refs_selftest.py` 8/8。
**修改文件**：`tools/infra/check_spec_refs.py`、`docs/Process-07-门控分层规范.md`（`check-spec-refs` 行）、本任务书。
**验收结果**：
- 前缀集：`Kaiwu` 入册（`SPEC_PREFIX_MAP` + `_PREFIX_ANCHOR`），与 `Machine-01` 同指 `spec/Kaiwu-测试机运行环境.md`；`DADAO-12/13/22` 经现场 `grep` 确认本就在册（`DADAO-\d+`），无缺口。
- 混排/不可判定：`§1.2 越界访问与越界取指异常` 仍命中 `### 1.2 …（含取指路径）`（中文节名+章号同校）；占位/范围/纯字母附录/空节名改为逐条打印「原因」的跳过明细，计数现场派生（当前 3 处占位，明细指名文件:行）。
- 真注入（`contract-syscall.md:121` `[Kaiwu §1.2 …]`→`§9.9`）：`make check-spec-refs` rc=2（工具 rc=1），报「章号与标题不匹配: 引用 §9.9，标题「越界访问与越界取指异常」实际位于 §1.2」并指名 `contract-syscall.md:121`；HEAD 版工具同一注入 rc=0（证明为新增能力）；`cp -p`+md5（`bd7ee17f…`）还原后 rc=0。
- 非 SimRISC 在册前缀复核：临时契约副本把 `[DADAO-22 §1 调用约定]`→`§9.9` ⇒ rc=1 并指名实际节号。
- 存量错误：无（收紧前后 Check1 失败均 0；引用 1415→1416 恰为新增的 Kaiwu 引用 1 条）⇒ 无需另立改正文任务。
**新发现/坑**：① 现场只有 1 条 `[Kaiwu §…]`（`contract-syscall.md:121`），本任务实际缺口即该册前缀；② 契约另有 `[ADR-*]`/`[contract-*]` 引用（非 spec 册，本门控不校，已写入 Process-07 缺口列）；③ `make` 对失败 recipe 返回 2（非工具 rc=1），证据按「rc≠0」断言；④ 纯字母附录 `§附录A` 由 HEAD 的 FAIL 改为「跳过+打印原因」（带标题形态仍走标题校验），已在缺口列披露。
**遗留问题**：`tools/infra/check_spec_drift.py` 的 `RE_SPEC_REF` 仍不认 `[Kaiwu §…]`（该门控只核「引用文件存在」，本轮无影响；不在本任务文件集）。

## 审阅记录

### 第 1 轮 reviewer 复核

**重跑**（worktree 根、相对路径）：
- `bash <运行期证据目录>/run.sh` → `PASS（37 项断言全部成立）`，rc=0（37 OK / 0 FAIL，逐项输出见对话）。
- `make check-spec-refs` → rc=0，`总引用数: 1416`、`失败: 0`、`PASS (0 violations)`；`--self-test` rc=0（9/9 OK）；`check_spec_refs_selftest.py` rc=0（8/8 OK）；`make check-spec-drift` rc=0（错误 0）。
- **独立注入**（改 `contract-semihosting.md` 追加新引用行，非工程注入点）：`[Kaiwu §9.9 越界访问与越界取指异常]` → `make` rc=2，报「章号与标题不匹配…实际位于 §1.2」并指名 `contract-semihosting.md:102`；**同一注入**跑 `git show HEAD:` 版工具 → rc=0（漏检）⇒ 新增能力成立；换回 `§1.2` 同标题 → rc=0（总引用 1417/失败 0）；`cp -p` 还原后 md5 `e8c8d922…` 与注入前相等、rc=0。
- 脚本可达 FAIL：注入态重跑 `run.sh` → rc=1（**14 项 FAIL**）；还原后重跑 → rc=0（37/37）。
- self-test 可达 FAIL（只在副本注入，原件 md5 `beefb40a…` 未变）：删「跳过明细原因打印」→ rc=1（1 FAIL）；摘 `Kaiwu` 前缀 → rc=1（3 FAIL）。

**约束核验**：
1. 前缀：`SPEC_PREFIX_MAP["Kaiwu"]="Kaiwu-测试机运行环境.md"`（:82）、`_PREFIX_ANCHOR` 含 `|Kaiwu`（:91）；`DADAO-12/13/22` 在 map（:72-75）、anchor 为 `DADAO-\d+` ⇒ 现场 grep 确认在册。
2. 标题型双校：错章号 → 「章号与标题不匹配」；错标题 → 「节标题未找到」rc=1（副本实测）。
3. 不可判定形态：占位/范围/纯字母附录/空节名 4 形态实测 → 摘要分类计数 + 明细逐条「原因: …」4/4，非静默。
4. 越界：`git status -uall` 改动集恰 = 完成区 3 文件；`git diff --name-only -- spec/ .tao/contracts/` = 0 行，未改正文。
5. 数字：1416/0、9/9、8/8、37/37 与完成区一致；HEAD 基线总引用 1415 vs 现 1416（+1 = 现场唯一 `[Kaiwu §…]`）。
6. 脚本审核：断言均有可达 FAIL（注入态实证 14 FAIL），无恒真/两支同结果（C5 新旧工具 rc=2 vs 0）。
7. 写入本记录后重跑 `make check-knowledge-refs` → rc=0 `PASS (0 具体 .work/** 引用; 0 悬空…)`（首次带重定向执行得 rc=2 且日志 0 字节，直接重跑即绿，疑为瞬时/锁，非记录内容问题）。

**遗留**：`check_spec_drift.py:87` `RE_SPEC_REF` 不含 `Kaiwu`，仅用于版本头行（:161）核「spec 文件存在」（:189-193）；现场版本头 0 处含 `[Kaiwu §…]`、门控 rc=0 ⇒ 本轮无影响；失效方向为「误红」非漏检 ⇒ **不需登记 issue**（留观察项）。

**判决：Accepted** —— 全部验收命令在我自己的重跑下通过，无阻断项；`**状态**` 未改。

### 第 1 轮 engineer 自审

**判决**：通过（无未修 finding）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只扩展前缀但「不可判定形态」仍只报模板占位，范围/字母附录无打印 | ✅已修 | 新增 `skip_reason()` 与四类原因常量，摘要按类计数 + 「跳过明细」逐条打印文件:行与原因 | `run.sh` C2 断言明细条数 = 现场派生跳过数；self-test 第 8 路断言 `跳过: 2 处` 且两类原因可辨 |
| F2 字母附录正则过宽，会连带跳过可判定的 `§附录 A：…` / `§A.1 标题` | ✅已修 | 正则收紧为「整段只有纯编号」（`^(?:[A-Z](?:\.\d+)+|附录\s*[A-Z])\s*$`），带标题形态仍按标题型引用校验 | self-test 第 8 路 + 现场 `Check1` 0 失败；`spec/SimRISC-01` 的 `## 附录 A：…` 未被误伤 |
| F3 self-test 绿路可能恒真（前缀缺席时 rc 仍 0，无区分度） | ✅已修 | 绿路增加「总引用数: 1」+「标题=1」断言，前缀缺席时计数为 0 即 FAIL | `--self-test` 第 6 路 `[OK]`；红路（§9.9）同时证明该前缀被扫描 |
| F4 任务书要求 `DADAO-12`/`13`/`22`，现场是否真缺？ | ✅已核验 | 现场 grep：`DADAO-\d+` 已在 `_PREFIX_ANCHOR`，`12/13/22` 在 `SPEC_PREFIX_MAP`；缺口仅 `Kaiwu` | `run.sh` C6：`DADAO-22 §1→§9.9` 注入 rc=1 并指名实际节号 |
| F5 还原须 `cp`+md5，禁 `git checkout/restore` | ✅已核验 | `run.sh` 用 `cp -p` 备份/还原 + md5 对账；`git diff` 仅作「注入生效/已还原」辅助判据 | `run.sh` C5：注入后 `git diff` 非空、还原 md5 一致（`bd7ee17f…`）、目标不在改动集 |
| F6 Process-07 行须与实际行为对账（扫描面/缺口） | ✅已修 | 该行补前缀集（ISS-521）与缺口（只校 spec 册；占位/范围/纯字母附录显式跳过） | `run.sh` C7：改动集 ⊆ 允许集（3 文件） |

