# INFRA-109t: 归档门控移到里程碑收尾（`check-spec-archive` + `--verify`）

**模块**：infra
**项目里程碑**：M10
**依赖**：INFRA-107t（`--verify` 已能跳过 `-rc`）
**状态**：已验证

## 执行环境
**执行环境**：本地（纯 Makefile/文档，无构建）

## 接口规范

### 背景（用户 2026-10-25 裁定）
- 归档是**只读历史快照**，只在发布/里程碑边界变化；用户要求：**结构与 sha 校验都只在里程碑收尾做一次**，不进每任务 L1。
- 现状：`check-spec-archive`（结构）在 L1 `_locked-check`；`gen_spec_archive.py --verify`（内容 sha）未接线、靠手动。

### 输出
1. `Makefile`：
   - 从 L1 `_locked-check` **移除** `check-spec-archive`；
   - 新增 `check-spec-archive-verify`：`$(PYTHON) tools/spec/gen_spec_archive.py --verify`；
   - `check-milestone` 依赖/步骤加入 `check-spec-archive` 与 `check-spec-archive-verify`；
   - help / phony 同步（标注「里程碑收尾」）。
2. `docs/Process-07-门控分层规范.md`：门控表把 `check-spec-archive` 从 L1 行移到「里程碑收尾」行，登记 `--verify`。
3. 不改 `check-milestones-fresh` 的 archive 回退（任务号解析，非归档校验）。

### 约束
- 不改变 `check-spec-archive` / `--verify` 的判据本身（只改触发层）。
- 不引入新依赖。

## 验收标准
1. `make check`（L1）不再包含 `check-spec-archive`（`make -n` 不含该目标），且 rc=0。
2. `make check-milestone` 实际跑 `check-spec-archive` 与 `--verify`，rc=0（贴输出）。
3. `docs/Process-07` 与 Makefile 实际分层一致（贴对照）。
4. 反例注入（临时让 `--verify` 红）⇒ `check-milestone` 红 ⇒ 还原 ⇒ 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：通过 **20/20**（default 6/6 rc=0、`--inject` 14/14 rc=0，`.work/evidence/INFRA-109t/run.sh`）。关键真值：`make -n check` rc=0 且 `grep check_spec_archive\|gen_spec_archive` = **0 命中**；`make -n check-milestone` 两命令齐（结构行 1 < verify 行 2）；`make check`(L1) **rc=0**（改后 `INFRA-109t-make-check.log`、状态置 `待验收` 后 `INFRA-109t-make-check-final.log`、写完成区后 `INFRA-109t-post-completion-check.log`，末行均 `repository checks (L1): PASS`，日志内 0 处归档命令）；`make check-milestone` **rc=0**（填完成区**前**：`INFRA-109t-make-milestone.log` / `-restore-milestone.log`——`check-spec-archive: PASS（声明 7 个版本目录，磁盘 8 个）` + 8 版 `OK`/2 版 `SKIP -rc` + `check-milestone: PASS (归档结构 + 内容 sha + …)`）；**填完成区后** `make check-milestone` **rc=2**，唯一红 = `check_tasks.py --strict` 的「① 漏收尾 = 1」（即本册 `待验收`，设计语义；归档两段同日志仍 PASS，`-post-completion-milestone.log`）。反例：`SimRISC-0.5.5/PROVENANCE.md` 组合 sha 首字符 `c038…→d038…`（`git diff` 非空=1）⇒ `--verify` **rc=2**（`FAIL SimRISC-0.5.5 … 声明 d038… 重算 c038…`）、`check-milestone` **rc=2**（停在 `check-spec-archive-verify] Error`）、L1 **rc=0**；`cp` 还原后 md5 `acb41fadc385488b0d457b836f6bdd0d` 一致、`git diff` 0 行 ⇒ `--verify` **rc=0**、`check-milestone` **rc=0**。
**修改文件**：`Makefile`（L1 `_locked-check` 移除 `check-spec-archive`；新增 `check-spec-archive-verify` 目标；`check-milestone` 前置两归档门控；phony + help 同步）；`docs/Process-07-门控分层规范.md`（§1.1 新增 archive/verify 两行 + `check-milestone` 行；§1.1 收尾专项说明；§2 触发点）；本册（状态/完成区/自审）；`.tao/knowledge/milestones.md`（**仅** INFRA-109t 行 `待开始`→`待验收`，L1 `check-milestones-fresh` 硬要求）；新增 `.work/evidence/INFRA-109t/run.sh`（`.work/` 忽略区）与 `.work/log/infra/INFRA-109t-*.log`。
**验收结果**：① L1 不含归档门控 ✓（`make -n` 0 命中 + 真跑日志 0 命中，rc=0）。② `check-milestone` 实跑两门控 ✓（输出见上，`.work/log/infra/INFRA-109t-make-milestone.log`/`-restore-milestone.log`）。③ Process-07 与 Makefile 一致 ✓：`check-spec-archive` 行改标「里程碑收尾专项（随 `check-milestone`；不入 L1）」，新增 `check-spec-archive-verify` 行，`check-milestone` 行注明「先跑结构 + 内容 sha」；`_locked-check:` 行现场 `grep` 无 archive。④ 反例红→还原绿 ✓，且注入下 L1 仍绿（隔离性）；另证判定器可达 FAIL：摘除 `check-milestone` 的 verify 依赖 ⇒ `milestone_verdict`= **1（真实红）**，`cp` 还原 md5 一致。⑤ 真实命令/输出/退出码均留 `.work/log/infra/`。
**新发现/坑**：① `docs/Process-06-spec目录保护规范.md §8` 仍写 `check-spec-archive`（**L1**），与本任务分层相反；**不在任务书范围内未改**，建议 architect 后续一笔改成「里程碑收尾」。② **`check-milestone` 含 `check_tasks.py --strict`** ⇒ 任何任务在「完成区已填 + 状态=待验收」态下必然使它红（`① 漏收尾 = 1` = 该册自身，`/complete` 置 `已验证` 后自解）；这是**设计语义**，审阅者不得据 rc=2 判实现失败——须看红是否只落在 `--strict` 且归档两段仍 PASS。③ `make -n check` 会真执行 `+` 前缀的 gate_lock 重入行（内层仍继承 `-n`）= 输出仍是布线清单，可作「L1 是否含某门控」证据；Process-07 §1「`make -n` 不适用」指耗时/依赖，不冲突。④ 依赖式接线在 `-jN` 下两归档步骤可能并行（均只读，安全），recipe 仍串行失败即停。⑤ 证据脚本首版 `REPO_ROOT` 少一级（`../..` 落到 `.work`）⇒ 6 项全 FAIL；改 `../../..` 后全绿——正是脚本「能失败」的旁证。
**遗留问题**：① 上述 Process-06 §8 的 L1 标注未清理（越界，待裁定/后续任务）。② `make check-milestone` 在**写完成区后**必红（`check_tasks --strict` 把「完成区已填 + 待验收」计为漏收尾=1 = 本册自身，设计语义，`/complete` 置 `已验证` 后自解）；归档两段在该红态下仍 PASS，绿证据见填完成区前日志。③ 未跑 L2/L3（本册只改 Makefile 触发层 + 文档；L1 已真跑）。④ 工作树 `docs/DDLN/README.md` 有**开工前已存在**的非本任务改动（7 行），未触碰。⑤ 未 commit（提交权归 architect）。

## 审阅记录

#### 第 1 轮 engineer 自审
**审查方式**：自主逐行审查（engineer 深度 1，不起嵌套子代理）；改动面 = `Makefile`（diff 22±）、`docs/Process-07`（+7/−2）、本册、`milestones.md` 单格、`run.sh` 全文。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `run.sh` 的 `REPO_ROOT=$(dirname/../..)` 解析到 `.work`（非仓库根）⇒ 首跑 C1–C6 全 FAIL（`grep: Makefile: No such file`） | ✅已修 | `../../..`（evidence 深三层） | `INFRA-109t-evidence-default.log` 6/6 PASS rc=0 |
| F2 归档两步骤用「依赖」还是「recipe 两行」：recipe 两行会复制脚本命令（DRY 违背）且与独立目标双份真源 | ✅保留依赖式 | `check-milestone: check-spec-archive check-spec-archive-verify` | `make -n check-milestone` 顺序正确；真跑两段输出在场；失败即停（注入 rc=2 停在 verify） |
| F3 `check-milestone` 原先不在 `.PHONY`（同名文件可劫持目标） | ✅已修 | `.PHONY` 加 `check-milestone`（连同新目标 `check-spec-archive-verify`） | `make help`/真跑均正常；无同名文件 |
| F4 改 `Makefile` 后 `help` 两行仍标 `(L1)` ⇒ 文档与实现反向 | ✅已修 | 两行改 `milestone closure`，`check-milestone` 行列出归档两段 | `make help` 输出 `check-spec-archive` / `-verify` 各 1 行，均无 `(L1` 字样 |
| F5 `make check` 日志为「无归档命令」之证据是否被 `grep` 自身 rc 污染 | ✅已修/已核 | 每次 `grep` 后单列 `grep_rc`；证据脚本用 `grep -c` 取计数并与 rc=0 联合判定 | `archive_grep_rc=1`（0 命中）与 `MAKE_CHECK_EXIT=0` 同时成立 |
| F6 反例是否「空注入」假红 | ✅已核 | 注入后先断言 `git diff --name-only` = 1 行、md5 变化再跑门控 | 注入 md5 `ce07f38b…` ≠ 基线 `acb41fad…`；`FAIL SimRISC-0.5.5` 由声明/重算差直接给出 |
| F7 `check-milestone` 依赖在 `-j` 下与 `check_tasks --strict` 并行是否可能读到半写状态 | ⏸延后（非本册引入） | 未改 | 两归档门控只读 `spec/`+`.tao/archive/`+git 历史；本册及验收均单进程运行 |
| F8 证据脚本 C6 只断言 `rc==0` ⇒ 写完成区后必红，审阅者重跑会误判为回归 | ✅已修 | 新增 `milestone_verdict()`：绿 / **设计性红**（必须归档两段 PASS + m 册 PASS + `漏收尾=1` + 单一 make 错误）/ 真实红 | 写完成区后 default 6/6 rc=0（C6 = `rc=2 leaked=1`）；`--inject` 14/14 rc=0（I7 同规则） |
| F9 「设计性红」白名单是否有恒真风险（掩盖真实回归） | ✅已实证 | 临时删 `check-milestone` 的 `check-spec-archive-verify` 依赖（`cp` 备份 Makefile，md5 `8b59cb92…`） | `milestone_verdict` 返回 **1=真实红**，日志中 `gen_spec_archive.py --verify` 出现 **0** 次；`cp` 还原后 md5 一致、`make -n` 两命令复原 |
| F10 两轮反例注入是否残留工作树污染 | ✅已核 | 每轮 `cp` + md5 + `git diff` 对账 | PROVENANCE md5 `acb41fadc385488b0d457b836f6bdd0d` 与备份一致；`git diff --name-only -- .tao/archive` = 0 行；Makefile 注入亦 md5 还原 |

**判决**：finding 全处置（F1/F3/F4/F8 修，F2 为设计选择，F6/F9/F10 已实证，F7 记录）；证据脚本 default 6/6 + `--inject` 14/14 双模 rc=0；任务书状态与 `milestones.md` 同步 `待验收` ⇒ 置 `待验收`。

#### 第 1 轮 reviewer 验收
**独立重跑（命令 + rc）**：① `make -n check` rc=0、`grep -cE 'check_spec_archive|gen_spec_archive'`=**0**（grep_rc=1）；② `make -n check-milestone` rc=0，两条齐且有序：行1 `tools/spec/check_spec_archive.py`、行2 `gen_spec_archive.py --verify`；③ `python3 tools/spec/check_spec_archive.py` rc=0（`PASS（声明 7 个版本目录，磁盘 8 个，A3/A4 启用）`）；④ `gen_spec_archive.py --verify` rc=0（8 版 `OK` + 2 版 `SKIP -rc`）；⑤ `bash .work/evidence/INFRA-109t/run.sh` rc=0（**default 6/6 PASS**）、`--inject` rc=0（**14/14 PASS**）——日志 `.work/log/infra/INFRA-109t-reviewer-evidence-{default,inject}.log`。脚本审核：各断言均有可达 FAIL 路径（C1/C5 计数+rc 联合判定；C6 `milestone_verdict` 的设计性红白名单经 engineer F9 注入实证可判真实红，非恒真）。
**预期红拆分核验**：`make check-milestone` rc=2——归档两段 PASS（结构 1 行 PASS + verify 8 OK/2 SKIP 在场）、`check_milestone_tasks.py` rc=0（`结果: PASS (M9…)`）；单独跑 `tools/infra/check_tasks.py --strict` rc=1，红项①「漏收尾」计数= **1 且仅本册**（`INFRA-109t-归档门控移到里程碑.md | 待验收`）⇒ 自指设计语义，非实现缺陷。
**独立反例（reviewer 自做，`cp`+md5 还原、未用 git checkout）**：`.tao/archive/SimRISC-0.5.5/PROVENANCE.md` 组合 sha 首字符 `c038…→d038…`（`git diff` 1 行、md5 `ce07f38bc8a4b…`）⇒ `--verify` **rc=1 红**（`FAIL SimRISC-0.5.5：声明 d038d40f… 重算 c038d40f…`）；注入下 `make check` **rc=0 仍绿**（L1 隔离性 ✓）；`cp` 还原 md5 `acb41fadc385488b0d457b836f6bdd0d` 一致、残留 diff 0 行 ⇒ `--verify` rc=0 回绿。
**约束核验**：① 判据未改——`git diff 8eec0cc5..6068b31a -- tools/spec/check_spec_archive.py tools/spec/gen_spec_archive.py` **为空**（只动 Makefile 触发层 + 文档）；② `_locked-check:` 行 grep `check-spec-archive` = **0**；`check-milestone:`（Makefile:910）前置依赖两归档门控；③ Process-07 §1.1 两行均标「里程碑收尾专项（不入 L1）」、`check-milestone` 行注明先跑两段，§2 触发点登记，与 Makefile 一致；④ 无新依赖；⑤ 提交 6068b31a 仅动完成区声明的 4 文件，`milestones.md` 仅 INFRA-109t 单格 `待开始→待验收`。完成区数字（20/20、0 命中、行1<行2、md5、各 rc）与我方重跑**逐项一致**。
**快照对账**：验收前后 `git status --porcelain -uall` 均仅 ` M docs/DDLN/README.md`（用户开工前改动，未触碰），前后 diff 0 行；`.work/` 为忽略区，无仓库残留。
**非阻塞 finding（供 architect）**：`docs/Process-06-spec目录保护规范.md §8` 仍标 `check-spec-archive`（**L1**），与新分层相反——任务书范围仅 Makefile + Process-07，engineer 已披露，建议收尾提交一笔修订。
**判决：Accepted**——验收命令块在我方重跑下全绿、预期红仅自指项（`check_tasks --strict` 漏收尾=1=本册，`/complete` 置 `已验证` 后自解）、约束无违反。
