# INFRA-110t: semihosting 旧口径文档清理（ISS-337）

**模块**：infra
**项目里程碑**：M10
**依赖**：ADR-0038 / SPEC-176t
**状态**：待验收

## 背景
semihosting 判定已迁至 `0x3FF00–0x3FFFF`（`ADR-0038`），但以下文档仍是旧口径 `immu18[17:16]==2'b11` / `0x30000`：
- `README.md:60`（M5 历史段）；
- `docs/DDLN/D-运行平台/DD-D002`、`TT-D002`（现行/教学口径，含 §8「为什么用 tag」）；
- `docs/Machine-00-执行环境分层-Draft.md:12`；
- `.tao/knowledge/audits/cfx-audit-2026-10-26.md`（审计快照）。

## 改动
1. `README.md` M5 历史段：**不改写历史**，在句末加注「（M10 已迁 `0x3FF00–0x3FFFF`，见 `ADR-0038`）」。
2. `docs/DDLN/D-运行平台/DD-D002` 与 `TT-D002`：判定改为 `immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）；一般 trap 为 `< 0x3FF00`；示例 `0x30000` → `0x3FF00`；§8 的「为什么用 tag」按新范围改写（保留历史动机说明，不删对比内容）。
3. `docs/Machine-00-执行环境分层-Draft.md:12`：同判定更新；Draft 仍标 Draft。
4. `audits/cfx-audit-2026-10-26.md`：**不改快照正文**，在文件头加一行「审计时 semihosting 为旧 tag；M10 已迁 `0x3FF00–0x3FFFF`（ADR-0038）」。
5. `issues.yaml`：ISS-337 `closed`，`resolved_by: INFRA-110t`。

## 验收
- `make check` rc=0。
- grep：`README.md`/`docs/Machine-00*`/`docs/DDLN` 中**现行口径**的 `2'b11`/`0x30000` = 0（历史注记/对比说明允许保留，须明确标「历史」）。
- 快照正文未改（仅头注）。

## 约束
- 只改上述 4 份文档 + `issues.yaml` + 任务书/`milestones.md`；不改 spec 正文/ADR/contracts。
- 临时目录 `/tmp/opencode/INFRA-110t/`；不提交。

## 完成区

**状态**：待验收

**测试结果**：`make check` **rc=0**（尾行 `repository checks (L1): PASS`）；证据 `bash .work/evidence/INFRA-110t/run.sh` → **checks=25 failures=0，rc=0**（10 断言 + `make check` + 3 组「注入→FAIL→`cp`+md5 还原→回绿」）。

**修改文件**：`README.md`（M5 段加历史注记）、`docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md` + `TT-D002-…`（§7/§8/对照改新判据；`TT-*` 被 `.gitignore` 忽略、随 DD 同步）、`docs/DDLN/Z-发展历程/DD-Z003-…` + `TT-Z003-…`（M5 段同 README 加注）、`docs/DDLN/README.md`（D002 索引行）、`docs/Machine-00-执行环境分层-Draft.md`（L2 示例 `0x3FF00`）、`.tao/knowledge/audits/cfx-audit-2026-10-26.md`（仅头注）、`.tao/knowledge/issues.yaml`（ISS-337）、`.tao/knowledge/milestones.md`（行状态）、本任务书；证据 `.work/evidence/INFRA-110t/{run.sh,checks.py}`（`.work/**` 不入 git）。

**验收结果**：
- 现行口径 grep：`README.md`/`docs/Machine-00*`/`docs/DDLN`（现场 77 文件）中旧口径行 = **5 行，全部标「历史」且带新口径指针**（README M5、Z003/TT-Z003 M5、DD002 §8 历史动机）；未标「历史」= **0**。
- 判定：DD/TT-D002 均 `immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）、一般 trap `immu18 < 0x3FF00`；§8 标题/正文新判据 + 历史动机保留；DD ≡ TT 逐字一致。
- 快照：audits 去头注后与 `git show HEAD:` **逐字相同**（仅加 1 行时间注记）。
- 台账：ISS-337 `closed` / `resolved_by: INFRA-110t`；`milestones.md` 行 `待验收` = 任务书 `**状态**`（`check-milestones-fresh` 在 `make check` 内 rc=0）。
- 反例：① D002 §7 回填旧 tag ⇒ c02/c07 FAIL；② audit 正文改字 ⇒ c05 FAIL；③ ISS-337 改回 open ⇒ c06 FAIL；三次 `cp` 还原 md5 全等（`MD5-RESTORE-OK`）后回绿。

**新发现/坑**：
- `TT-*` 讲义被 `docs/DDLN/.gitignore` 忽略（本地衍生副本）⇒ 改后不入 git；一致性靠 `DD ≡ TT` 断言（c03）守。
- 「历史」二字本身可掩盖现行残留 ⇒ 证据按 `is_hist()` 双判据（`历史` + `0x3FF`/`ADR-0038`/`0x30001` 之一）。
- **越界披露**：任务只列 4 份文档，但验收要求 `docs/DDLN` 现行口径旧 token = 0；故另改 `docs/DDLN/README.md` D002 索引行 + Z003/TT-Z003 历史段注记（同 README 口径），未动 spec/ADR/contracts。

**遗留问题**：无（`Machine-00` 仅 L2 行含 semihosting 口径，grep 已覆盖；`ADR-0020`/`QEMU-076t` 等历史文献按设计保留旧文）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-26）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务约束只列 4 份文档，但验收要求 `docs/DDLN` 现行口径旧 token=0；`DDLN/README.md:40`（索引摘要）与 `Z003/TT-Z003:51`（M5 历史副本）不在列 | ✅已修（越界已披露） | 更新 DDLN 索引 D002 行；Z003/TT-Z003 加同 README 的历史注记 | c07（77 文件、未标历史=0）/c08 PASS |
| F2 c02 初版把 D002 §8「历史动机」行判红（该行按任务要求保留旧 2 位写法） | ✅已修 | 旧 token 判定改用 `is_hist()` | c02 PASS；注入① 仍 FAIL |
| F3 任意行加「历史」即可放过（掩盖现行残留） | ✅已修 | `is_hist()` 追加新口径指针要求；c07 同步 | 注入①（无指针旧行）⇒ c02/c07 均 FAIL |
| F4 c10 初版用 `git diff --name-only`，漏「未跟踪残留」 | ✅已修 | 改 `git status --porcelain -uall`；rename 取新名 | c10 现场 9 项 ⊆ 允许集 |
| F5 c05 初版「去头注」有冗余赋值、仅比子串 | ✅已修 | 重写 `drop` 计算；改与 `git show HEAD:` 全文逐字比较 | c05 PASS；注入② ⇒ FAIL |
| F6 历史行全被删时 c07 会 0 命中空转 | ✅已修 | 增 `marked=0 ⇒ FAIL` | 注入① 下 unmarked=1 ⇒ FAIL |

**自审判决**：改动逐行核对（`0x3FF00`/`0x3FF` 等价、§7 两路分界、§8 保留历史动机、审计正文未改、台账/milestones 状态对账）；无未修 finding；三组注入均可达 FAIL 且 `cp`+md5 还原回绿。**可标「待验收」**。

