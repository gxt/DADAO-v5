# INFRA-125t: embench-iot/libc-test 补丁集迁入 tests/tset

**模块**：infra
**项目里程碑**：M11
**依赖**：`TESTCASES-100t`（已验证；libc-test 补丁集）、`INFRA-123t`（已验证；DDLN 规则）
**状态**：已验证

## 执行环境
本地；移动测试集补丁资产与 manifest 路径，不改上游 commit、不改测试语义。

## 用户裁定（2026-11-05）

> 「我要把 components/embench-iot 目录和 components/libc-test 目录清理掉，这些内容应该放在 tests/tset 下面，并且已经有这两个测试集的对应目录了」

## 现状

`components/` 下有两个测试集的补丁资产：

- `components/embench-iot/`
  - `patches/examples/dadao/{README,boardsupport.c,boardsupport.h}.patch`
  - `patches/src/md5sum/md5.c.patch`
  - `series`、`README.md`、`changelog.md`
- `components/libc-test/`
  - `patches/src/regression/malloc-brk-fail.c.patch`
  - `series`、`README.md`、`changelog.md`

`tests/tset/embench` 与 `tests/tset/libc-test` 已存在，前者是 Embench 用户态驱动/板级 shim，后者目前只有 README。

## 目标

1. 把两个补丁集整体迁到现有 tset 目录：
   - `components/embench-iot/patches/**` → `tests/tset/embench/patches/**`
   - `components/embench-iot/series` → `tests/tset/embench/series`
   - `components/embench-iot/changelog.md` → `tests/tset/embench/changelog.md`
   - `components/embench-iot/README.md` → 合并进 `tests/tset/embench/README.md`
   - `components/libc-test/patches/**` → `tests/tset/libc-test/patches/**`
   - `components/libc-test/series` → `tests/tset/libc-test/series`
   - `components/libc-test/changelog.md` → tset libc-test changelog
   - `components/libc-test/README.md` → 合并进 `tests/tset/libc-test/README.md`
2. 删除 `components/embench-iot/` 与 `components/libc-test/` 目录。
3. `manifests/components.lock.toml`：
   - 两个 component 的 upstream `commit`/`repository` 不变；
   - `patch_dir`/`patch_series` 改为 `tests/tset/{embench,libc-test}/...`；
   - 注释/role 同步，不再说“components 下”。
4. 更新依赖这些路径的活文件：
   - `tools/testcases/tset/embench/run_embench_user_suite.py`
   - `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
   - `tests/tset/embench/embench_user_boardsupport.c` 注释
   - `tools/infra/check_patch_tree.py` 文档字符串中 `components/<name>/series` 的旧措辞
   - `ADR-0022` 的历史位置指针加 `rev. 2026-11-05` 注记（不改决策）
5. `check-component-changelog.py`：
   - 扫描面从仅 `components/*/changelog.md` 扩为 `components/*/changelog.md` + `tests/tset/*/changelog.md`；
   - 保持 5 条形态断言；不得 vacuous PASS；
   - self-test 覆盖新扫描面。
6. 不改上游源树内容、不改补丁语义、不改测试判据。

## 范围 / 非范围

**在范围内**：`components/embench-iot/**`、`components/libc-test/**`（删除）、`tests/tset/embench/**`、`tests/tset/libc-test/**`、`manifests/components.lock.toml`、`tools/infra/check_component_changelog.py`、`tools/infra/check_patch_tree.py`（仅注释）、`tools/testcases/tset/{embench,libc-test}/*.py`（仅路径/文案）、`.tao/adr/adr-0022-embench-upstream.md`（仅指针/rev）、`docs/Process-01-组件补丁组织与构建编排.md`（§1/§2/§9/§10 + 修订）、`docs/repository-layout.md`、`Makefile`（门控帮助注释）、本任务书、`milestones.md`。

**不在范围内**：`components/qemu/**`、`components/gem5/**`、其它 `components/**`、`spec/**`、`contracts/**`、QEMU/gem5 实现、测试期望值。

## 验收标准

1. `components/embench-iot`、`components/libc-test` 不存在；对应 `tests/tset/{embench,libc-test}` 含 patches/series/changelog/README。
2. `manifests/components.lock.toml` 的 patch_dir/series 指向新路径；`manifest_check` rc=0。
3. `check-patch-tree`/`check-index-blobs` rc=0；源树 base+1 不变；`apply-series`/`check-source-state` rc=0。
4. `check-component-changelog` 扫描面含 `tests/tset/*/changelog.md`，5 条断言全绿，非 vacuous。
5. `make check-tset-embench-smoke`、`make check-tset-libc-smoke`（或现场可用等价）rc=0；L1 rc=0。
6. 活文件对 `components/embench-iot`/`components/libc-test` 的引用 0 命中（历史归档/任务书除外）。
7. 反例：把 manifest patch_dir 改回旧路径或删除一个 tset changelog ⇒ 门控 FAIL；`cp`+`md5sum -c` 还原回绿。
8. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是资产位置迁移，不是组件删除：upstream commit lock 保留，只是补丁集归 `tests/tset`。
- `check-component-changelog` 扩展扫描面时，不能把 `tests/tset/*/changelog.md` 排除；否则新位置无人校验。
- 先移动、改 manifest，再改生成/门控；最后删除空 components 目录。
- 与 `INTEG-054t` 并行时只改不同文件；若 `make check` 因并发构建红，区分环境红并重试。

## 完成区

**测试结果**：`make check`（L1；`-k` 全量）唯一红 = `check-patch-tree` 的**环境红**（并行 `INTEG-054t` 改共享 共享源树：8 条 assertion ⑥/⑦，与本任务开工基线同数同路径，迁移两组件 0 条）；`make -k check` 其余目标全绿；补文档后复跑：`make manifest-check` rc=0、`make check-component-changelog` rc=0、`make check` rc=2（仍止于同一环境红）。迁移两组件 scoped patch-tree 0 problem；source-state：embench-iot `80e50848`、libc-test `fc50a4d8`，均 clean + base+1。`check-index-blobs`（226 new-file OK / 77 skipped）、`check-component-changelog`（7 文件 × 4 = 28 项）+ `--self-test`、`check-milestones-fresh` 全 rc=0。`make check-tset-libc-smoke` rc=0（5/5 类代表集）、`make check-tset-embench-smoke` rc=0（38 benchmark × `-O0/-O2` PASS）。
**修改文件**：`git mv` 迁移 `components/{embench-iot,libc-test}/{patches/**,series,changelog.md}` → `tests/tset/{embench,libc-test}/`（内容原样）；删两 components 目录（两份 README 合并进 tset README）；`manifests/components.lock.toml`（patch_dir/patch_series + 注释/role，upstream commit 不变）；`tools/infra/check_component_changelog.py`（扫描面扩为 `components/*` + `tests/tset/*`，⑤ 覆盖加「带 `series` 的套件必须有 changelog」）；`tools/infra/check_patch_tree.py`（docstring）；`tools/testcases/tset/{embench,libc-test}/*.py`（docstring）；`tests/tset/embench/embench_user_boardsupport.c`（注释）；`tests/tset/{embench,libc-test}/README.md`；`.tao/adr/adr-0022-embench-upstream.md`（`rev. 2026-11-05` 注记，不改决策）；**活文档指针（补本轮）**：`docs/Process-01-组件补丁组织与构建编排.md`（§1/§2/§9/§10 + 修订行）、`docs/repository-layout.md`、`Makefile`（`check-component-changelog` 帮助注释）；`.tao/knowledge/milestones.md`、本任务书。
**验收结果**：运行期证据脚本 全量 PASS（rc=0；逐项打印期望/实际/rc；补文档后 `SMOKE=0` 复跑再 PASS，含新增「活文档指针」检查）；`--inject` 三条反例均可达 FAIL、`cp`+md5 还原回绿：manifest 改回旧路径 ⇒ `manifest-check` + scoped patch-tree 红；删 tset libc-test changelog ⇒ ⑤ 覆盖红；tset changelog 插表格行 ⇒ ① 红。全仓 grep（排除 `.tao/archive`/`.tao/tasks`/`.work`/`.cache`）旧路径命中仅剩 tset changelog 历史条目、补丁 payload 与被补丁的上游文件内容、ADR-0022 历史句/rev 注记。
**新发现/坑**：① ⑤ 覆盖若以 `tests/tset/*/patches/` 当「带补丁集」标记会误伤 `tests/tset/llvm-ts/patches/`（那是逐例 glue、语料 patchless），改用 `series` 标记。② 运行期日志目录 下 `*.rc` 触发 `check-run-artifacts` A3 命名红（自身造成），改 `INFRA-125t-*-rc.txt` 后回绿。③ 补丁 payload `examples/dadao/README.md.patch` 正文含旧路径——那是被补丁的上游文件内容，改它会改上游树/commit，故不动。④ tset changelog 按「原样迁入」未追加本轮条目，迁移记录见 README/ADR rev/milestones。⑤ 文档侧不止 §10：Process-01 §1（术语）/§2（目录形态）/§9（参考值）也有通用路径表述，同文件一并同步（仍属 `docs/Process-01` 一个文件）。
**遗留问题**：ADR-0022 正文历史句与 tset changelog 历史条目保留旧路径（历史记录，仅加 rev 注记/原样迁入）；补丁 payload `examples/dadao/README.md.patch` 正文的旧路径属被补丁的上游文件内容，不改。环境红（qemu/gem5 共享源树脏）随 `INTEG-054t` 结束复跑 L1 应消失。

## 审阅记录

#### 第 1 轮 engineer 自审

审查范围：`check_component_changelog.py`（⑤ 覆盖 / 枚举 / self-test 还原）、manifest 字段、README 合并、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ⑤ 以 `patches/` 作「带补丁集」标记，误伤 `tests/tset/llvm-ts/patches/`（glue、语料 patchless） | ✅已修 | 改用 `series` 标记 | 修前 `[FAIL] ⑤ ... tests/tset/llvm-ts/changelog.md`；修后 7 文件全 PASS |
| manifest 注释写「pin below」，实际 pin 在字段上方 | ✅已修 | 改「above」 | `grep -n "upstream pin"` → `above` ×2 |
| 运行期日志目录 下 `*.rc` 触发 check-run-artifacts A3 非法命名（自身环境红） | ✅已修 | 改名 `INFRA-125t-*-rc.txt` | `check_run_artifacts.py`：`0 illegal` rc=0；run2 L1 绿 |
| 证据脚本 `CH= tests/...` 赋值带空格（shell 会把路径当命令） | ✅已修 | 去空格 | `bash -n` rc=0；`--inject` 全 PASS |
| README/manifest 迁移注记含旧路径，可能违反验收 6「0 命中」 | ✅已修 | 改为「归位到本目录」 | 全仓 grep 仅剩 changelog / patch payload / ADR 历史句 |

判决：全部 finding 已修，状态 → `待验收`。

#### 第 2 轮 engineer 自审（活文档指针补齐）

审查范围：`docs/Process-01`（§1/§2/§9/§10 + 修订）、`docs/repository-layout.md`、`Makefile` 帮助注释、证据脚本新增检查。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 三处活文档仍把补丁台账写成仅 `components/<name>/changelog.md` | ✅已修 | 改为两处扫描面（`components/*` + `tests/tset/*`，测试集台账在 tset） | `doc_pointers` 检查 PASS；`grep -c 'tests/tset/*/changelog.md'` = Makefile 1 / repository-layout 1 / Process-01 3 |
| Process-01 §1/§2/§9 同类表述（同一文件内）未同步 | ✅已修 | 术语/目录形态/参考值三处同步 + 修订行 | 修后 §2 含 `tests/tset/<suite>/` 表述；docs 旧任务路径 grep 0 命中 |
| 文档改动是否影响门控语义 | ✅未改 | 仅位置/文档表述；5 条断言与门控逻辑不变 | `check-component-changelog` rc=0、self-test PASS；L1 仍仅环境红 |

判决：全部 finding 已修，状态保持 `待验收`（未 commit/push）。

#### 第 1 轮 reviewer 验收

**判决：Accepted**（HEAD=`77a41b82`，`git status --porcelain -uall` 前/后均空，md5 前后对账 OK；本轮未 commit/push）

**重跑记录（reviewer 亲自执行，worktree=任务 worktree，rc 皆取 `echo $?`）**
- 证据脚本全量 运行期证据脚本 ⇒ 15 项全 PASS，`RUN_EXIT=0`；`--inject` 三条反例全 PASS，`INJECT_MODE_rc=0`（脚本 md5 `ce8b8988…` 前后未变）。
- 自跑门控（`own-gates.log`）：`make manifest-check`=0、`make check-patch-tree`=0（`7 component(s), 303 patches OK`）、`make check-index-blobs`=0（`226 new-file OK; 77 skipped`）、`make check-source-state`=0（`embench-iot HEAD=80e50848 clean count=1`、`libc-test HEAD=fc50a4d8 clean count=1`）、**`make check`(L1)=0**（`repository checks (L1): PASS`，0 条 make 错误）、`make apply-series`=0（两组件 `already applied (base+1, matches patches)`）、复跑 `check-source-state`=0。
- `check_component_changelog` ⇒ rc=0，`7 个 changelog.md（components/* + tests/tset/*，现场 glob）`、`7 文件 × 4 = 28 项`，两 tset 文件逐项 ①–④ PASS（非 vacuous）；`--self-test` ⇒ rc=0，含 ①b tset 插表格、⑤b 删 tset changelog 两条新面反例（均 `rc=1` 命中后 cp+md5 还原回绿）。
- smoke：`check-tset-libc-smoke` `pass=5 fail=0`（`run_libc_test_user_suite: PASS`）、`check-tset-embench-smoke` `total=38 pass=38 fail=0`（`run_embench_user_suite: PASS`），均 rc=0。
- **独立注入（reviewer 自做，非脚本自检）**：① manifest `patch_dir/patch_series` 改回 `components/embench-iot/*` ⇒ `make manifest-check rc=2`（`missing patch directory`）+ `make check-patch-tree rc=2`（`missing series`），`cp`+`md5sum -c` 还原 rc=0、回绿 rc=0；② `rm tests/tset/libc-test/changelog.md` ⇒ 门控 `rc=1`（`⑤ …缺 changelog.md`），还原回绿；③ 顶格 `## M` 行前插 `|---|---|` ⇒ 门控 `rc=1`（`[FAIL] ① … 行 [5]`，命中 tset 新扫描面），还原回绿。全程 `cp`+md5，未用 git 还原；终态 `git status` 空、7 个关键文件 md5 与开工前一致。

**约束核验**：① 两 components 目录不存在、tset 两目录含 patches/series/changelog/README ✅；补丁/series/changelog 与 master 逐文件 md5 相同（4+3 个文件 SAME）；② patch_dir/series 指向 tset、`repository`/`commit`（`09c2ed8c…`/`b7ec4679…`）与 master 逐字相同、`manifest-check rc=0` ✅；③ 见上，apply-series/check-source-state 真实 rc=0，源树 base+1 且 base=manifest commit ✅；④ 扫描面含两 tset changelog、5 断言全绿非 vacuous、self-test 覆盖新面 ✅；⑤ 两 smoke + L1 rc=0 ✅；⑥ 活文件旧路径 0 命中（grep `docs/ tools/ Makefile manifests/ tests/` 仅剩 tset changelog 历史条目、补丁 payload 上游内容、ADR-0022 历史句/rev 注记；Process-01 §10/§1/§2/§9、repository-layout、Makefile 帮助、两驱动 docstring、boardsupport 注释、ADR-0022 rev 均已同步）✅；⑦ 反例三连可达 FAIL + cp/md5 回绿 ✅；⑧ 完成区 9 行 ≤30、无运行期绝对路径、状态 `待验收` ✅；范围无 spec/contracts/tests 期望值/QEMU/gem5 改动（`git diff --name-only master...` 25 文件全在范围内）✅。

**非阻断 finding（供 architect 收尾处置）**
- F1（证据脚本）：`run.sh` 的 `l1()` 在「失败目标全是 `check-patch-tree` 且非迁移两组件」时判 PASS 且不打印 `make check` 真实 rc，存在掩盖他组件 patch-tree 真红的可能；本轮我独立 `make check`=0，未触发该路径。建议打印 rc 并收紧容忍条件。
- F2（证据脚本覆盖）：脚本未覆盖验收 3 的 `make apply-series`/`make check-source-state`（我已单独重跑，均 rc=0）。
- F3（文档级小错，不阻断）：`.tao/knowledge/discussing.md:28` 仍写 `INFRA-125t（待开始）`+旧路径描述（该文件仅主会话可改）；`.tao/knowledge/refs/DADAO-0628-对照分析.md:165` 仍把组件侧写成 `components/*/changelog.md`（参考文档，未列本任务活文件清单）。
- F4（记录差异）：完成区称 `make check rc=2`（INTEG-054t 并行环境红），我重跑为 rc=0（该任务已合入、共享源树已复位）；以我的重跑为准，判定不受影响。
- F5（reviewer 自身记录）：反例③ 前两次注入锚到正文里的 `## M<k>` 字样、分隔行未独立成行 ⇒ rc=0，根因是我自己的注入锚点错误；第 3 次锚到顶格 `## M` 行 ⇒ rc=1，非门控缺陷，如实记录重试 3 次。

#### 收尾（architect，2026-11-05）

- F1/F2：证据脚本 `l1()` 容忍条件与 apply-series/source-state 覆盖不足记入遗留；reviewer 已独立重跑 L1/apply-series rc=0。
- F3：`discussing.md` 的 INFRA-125t 旧状态在合并后更新；`refs/DADAO-0628-对照分析.md` 为参考文档，旧路径保留。
- F4：完成区当时 `make check rc=2` 为并发环境红；reviewer 重跑 rc=0，以重跑为准。
- F5：reviewer 注入锚点重试 3 次，非门控缺陷。
- 判决 Accepted，状态置 `已验证`。
