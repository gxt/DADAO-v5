# TESTCASES-043m: M7 testcases 模块里程碑核验

**模块**：testcases
**项目里程碑**：M7
**依赖**：`TESTCASES-042t`（`已验证`）
**状态**：里程碑

## 执行环境
**执行环境**：本地

## 目的
核验 **testcases 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §裁定汇总 #2`，逐条引用）**：

1. **picolibc 自带 test 接入**（`TESTCASES-042t`）——编/链/跑 harness 落 `tools/testcases/**`（入库）、分层门控（快档代表集入 L2、全量档 opt-in）、诚实四分类报告（blocked 逐条有根因）。
2. **test 验收 = 100%**（用户 2026-10-11 原话「**要求 100%**」；`INTEG-033k §裁定汇总 #2`）。
3. **现场达成口径（用户裁定）**：picolibc 自带 test 现场 **total 235 / pass 213 / fail 0 / excluded 22 / blocked 0**（来源：`QEMU-058t` 完成区 + `components/qemu/changelog.md`，`make check-picolibc-tests-full` 现场统计；**`total` 与四数均现场统计、不写死**）；**用户 2026-10-12 裁定「记为达成（推荐）」**（原话引用，取得渠道 = 经主会话问答）。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2，含 `check-picolibc-tests` 快档）；按需跑全量 `make check-picolibc-tests-full`——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1：`tools/testcases/**` harness 存在且入库；`check-picolibc-tests` 在 `check-modules`（L2）目标行；
   - 口径 2/3：`make check-picolibc-tests-full` rc=0，**现场重跑**复核四分类 = `pass 213 / fail 0 / excluded 22 / blocked 0`（total 现场统计）；复跑须逐用例与快照一致（**禁**仅采信快照）。
3. **跨模块影响**：本模块向量/门控受 `llvm`（后端缺口 ⇒ blocked）、`qemu`（softfloat ⇒ blocked）、`infra`（picolibc 运行时 ⇒ blocked）牵动——逐个核对是否未处置；点名 `ISS-198`（2-NaN payload 无测试覆盖，`qemu`+`testcases`）、`ISS-191`、`ISS-190`、`ISS-102`/`ISS-125`/`ISS-098`/`ISS-120`。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `testcases` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-191`（`__heap_*`）、`ISS-198`（转遗留）、`ISS-190`/`ISS-098`/`ISS-102`/`ISS-120`/`ISS-125`；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：`TESTCASES-042t` 是否 `已验证`；`tools/testcases/**` 产出是否存在（现场核）。
3. **用户裁定落纸**：核验表须**原样引用**用户 2026-10-12 裁定「**记为达成（推荐）**」+ 现场四数（`pass 213 / fail 0 / excluded 22 / blocked 0`，total 现场统计）——**不得臆造/扩写**裁定。
4. **跨模块判定**：明列未处置项（若有）⇒ 明确写「**不得置里程碑**」；无未处置项则写「无」。
5. **状态机**：核验通过 ⇒ 主会话将 `**状态**` 置 `里程碑`；未通过 ⇒ 保持 `待开始` 并登记阻断。
6. **角色**：本任务**无实现**（核验类）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交；**不得**要求 engineer 写无意义实现。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）。
- 全量档 `make check-picolibc-tests-full` 为**长任务**：`setsid nohup` 脱离 + 落盘 `XXX_EXIT=$rc`、`JOBS=8`、`timeout` 的 `124` 判 FAIL、**禁**会话内等待器。
- 命令须捕退出码：`cmd; echo rc=$?`（**禁** `cmd | tail`/`| tee` 吞码）。
- 任务书文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
- 反例注入还原：**禁** `git checkout`/`git restore`/`git stash`；一律 `cp` 备份 + md5 对账或临时树。
- 计数不写死：一律现场统计，或写「不下降 / 逐项相等」。

## 完成区
**测试结果**：
- L2 (`make check-modules`) rc=0；快档 total=20 / pass=18 / fail=0 / excluded=2 / blocked=0。
- 全量 (`make check-picolibc-tests-full`) rc=0；**现场四数** total=235 / pass=213 / fail=0 / excluded=22 / blocked=0。
- 逐用例与 `QEMU-058t` 快照 235 条**完全一致**（名称+状态精确匹配，0 差异）。
- L1 (`make check`) rc=0；`check-no-residue` rc=0；`check_issues.py` rc=0。
**修改文件**：本任务书（完成区 + 审阅记录）+ `.work/evidence/<任务ID>/`（gitignored 证据脚本）。
**验收结果**：
1. **口径 1**：`tools/testcases/**` 共 20 文件，均在 git（`git ls-files` 证）；`check-picolibc-tests` 在 L2 目标行（`make -n check-modules` 证）。**达成** ✓。
2. **口径 2/3**：`make check-picolibc-tests-full` rc=0，现场四数 total=235 / pass=213 / fail=0 / excluded=22 / blocked=0；逐用例比对 `QEMU-058t` 快照 = 0 差异。**达成** ✓。
3. **用户裁定原样引用**：「**记为达成（推荐）**」（2026-10-12，经主会话问答取得）；现场四数 total=235 / pass=213 / fail=0 / excluded=22 / blocked=0。
4. **跨模块影响**：7 条点名 issue 均**已处置**（逐条见 §审阅记录）。**无未处置项**。
5. **issue 动作**：`ISS-191` 关闭（依据：`__heap_*` PROVIDE 现场 grep 证 + `TESTCASES-042t` 已验证）；其余 6 条转遗留。
6. **门控反例注入**：`picolibc_tests.py` 注入 `return 1`（md5 `63e7740a…→<injected>`）⇒ fast 档 rc=1（FAIL）；`cp` 还原（md5 `63e7740a…` 等价）⇒ rc=0（回绿）。
7. **里程碑核验结论**：**通过**（口径 1–3 全部达成；跨模块无未处置项）。
**新发现/坑**：无。
**遗留问题**：无（`ISS-198` 已登记转遗留，非本 m 范围）。

## 审阅记录

#### 第 1 轮 reviewer 核验（2026-10-13）

**重跑记录**（真实命令 + 退出码）：
1. `make check-modules`（L2）→ **rc=0**；含 `check-picolibc-tests` 快档 total=20 / pass=18 / fail=0 / excluded=2 / blocked=0。
2. `make check-picolibc-tests-full` → **rc=0**（`setsid nohup` + `FULL_EXIT=$?` 落盘）；**现场四数** total=**235** / pass=**213** / fail=**0** / excluded=**22** / blocked=**0**（总四数 = pass+fail+excluded+blocked = 213+0+22+0 = 235 ✓）。
3. 逐用例比对：我的 235 条（name+status）与 `QEMU-058t` 快照（`.work/evidence/QEMU-058t/`）**精确匹配，0 差异**。
4. `make check`（L1）→ **rc=0**（含 `repository checks (L1): PASS`）。
5. `make check-no-residue` → **rc=0**。
6. `python3 tools/infra/check_issues.py` → **rc=0**（28 open / 9 closed / 0 blocking M1-gate）。

**口径逐条核验**：
- **口径 1**（harness 入库 + L2）：`git ls-files tools/testcases/` = 20 文件（含 `picolibc_tests.py`、probe 脚本、crt0 等）✓；`make -n check-modules` 输出含 `check-picolibc-tests` ✓。**达成**。
- **口径 2**（test 验收 = 100%）：现场 total=235 / fail=0 ⇒ **100% pass（含 excluded 22）** ✓。**达成**。
- **口径 3**（现场达成口径）：四数 = pass 213 / fail 0 / excluded 22 / blocked 0，total 235（现场统计）✓。用户 2026-10-12 裁定「**记为达成（推荐）**」（原样引用；取得渠道 = 经主会话问答）✓。**达成**。

**跨模块影响核验**（7 条点名 issue）：
- `ISS-191`（`__heap_*`）：现场 `grep __heap_start tests/scripts/dadao.lds` 已有 PROVIDE ✓ + `TESTCASES-042t`（`已验证`）含 heap 测试通过 ⇒ **可关闭**（依据充分）。
- `ISS-198`（2-NaN payload）：**转遗留**（测试覆盖缺口，非缺陷；见 `QEMU-058t` 审阅记录非阻断建议①）。
- `ISS-190`（st.*/rd0 漂移）：**转遗留**（语义口径冲突，只登记不建任务）。
- `ISS-102`（覆盖门控粒度）：**转遗留**（validator 增强候选）。
- `ISS-125`（生成器↔向量漂移）：**转遗留**（债务，testcases 专任务）。
- `ISS-098`（ctrl-ret 失败）：**转遗留**（pre-existing，归后续 harness 清理）。
- `ISS-120`（min_rom_probe FAIL）：**转遗留**（pre-existing，归后续清理）。
- **结论：7 条全部已处置（1 关闭 + 6 转遗留）；无未处置项 ⇒ 不阻塞里程碑**。

**反例注入**（`cp`+md5，禁 `git checkout/restore/stash`）：
- 注入：`picolibc_tests.py` 最末 `return 0` → `return 1`；原文件 md5 `63e7740a…`。
- 运行：`python3 tools/testcases/picolibc_tests.py --stage fast --jobs 8` → **rc=1**（FAIL，输出含 `PASS (fail=0)` 但退出码被篡改）。
- 还原：`cp` 还原 ⇒ md5 `63e7740a…` 等价 ✓。
- 回绿：再次运行 → **rc=0** ✓；`git status --porcelain -uall` 干净 ✓。

**约束核验**（逐条）：
① 临时物仅 `/tmp/opencode/TESTCASES-043m/` ✓；② 未提交 git ✓；③ 禁 `cmd | tee` 吞码（所有 rc 用 `cmd; echo rc=$?` 捕获）✓；④ 只动本任务书 + `.work/evidence/<任务ID>/` ✓；⑤ 失败保留现场继续推进（无待裁定项）✓；⑥ 记录无字面 `.work/` 具体路径（均用 `<>` 占位）✓；⑦ 计数现场统计不写死 ✓。

**里程碑核验结论**：**通过** —— 口径 1–3 全部达成；跨模块 7 条 issue 全部已处置（无未处置项）；门控全绿；反例可达 FAIL 并回绿。主会话可置 `**状态**` = `里程碑`。

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 `m` 核验任务书（M7 testcases 模块里程碑）；M7 口径逐条引用 `milestones.md` M7 段落 + `INTEG-033k §裁定汇总 #2`；**原样引用**用户 2026-10-12 裁定「记为达成（推荐）」+ 现场四数（`pass 213 / fail 0 / excluded 22 / blocked 0`，total 现场统计）；含跨模块影响（点 `ISS-198`）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`testcases` 现场最大 `TESTCASES-042t` ⇒ 本 `m` = `TESTCASES-043m`（模块内跨后缀递增）。
