# INFRA-055t: 接入 picolibc 组件（浅克隆 `release-1.8.12` + 锁 + 骨架）

**模块**：infra
**项目里程碑**：M7（规划中；本任务为 M7 前置基础设施，用户 2026-10-11 指示）
**依赖**：无（用户 2026-10-11 直派；与 `INTEG-032t` 登记的 M7 候选主题「libc/OS · test 重心」相关）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户指示原话（2026-10-11）：
    > 「调整 test 重心为 **picolibc 自带的 test**；picolibc 网站 `https://github.com/picolibc/picolibc`，**可以浅克隆到 `.cache` 下**，增加 `components.lock.toml`，版本号 **`release-1.8.12`**。」
  - 已核实上游事实：picolibc 默认分支 = `main`；**`release-1.8.12` 是分支**（`refs/heads/release-1.8.12`），sha = **`2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`**；`release-*` 分支仅此一个。
  - 组件锁体例 `manifests/components.lock.toml`（`llvm-project`/`qemu`/`embench-iot`）；`tools/infra/fetch.py` 支持 `shallow` + `shallow_ref`（浅裸镜像）。
  - 补丁集规范 `spec/Process-01-组件补丁组织与构建编排.md`；上位决策 `ADR-0005`（多源锁）、`ADR-0006`（浅裸镜像）。
- **输出**：
  1. `manifests/components.lock.toml` **追加** picolibc 条目（不动其它条目）：`enabled=true`、`repository=https://github.com/picolibc/picolibc.git`、`commit=2ae376c6…`、`shallow=true`、`shallow_ref="release-1.8.12"`、`patch_dir`/`patch_series`/`role` 照体例。
  2. `components/picolibc/{README.md,patches/**,series,changelog.md}`：**骨架**（**1 个最小占位补丁** `dadao/README.md`，**声明无行为**，真移植归 **M7**）。
  3. 工作树：`make fetch`（**浅**）生成 `.cache/picolibc.git`（浅裸镜像）+ `.work/source/picolibc`。
- **约束**：
  - **不引入任何真实 picolibc 移植补丁**（board/machine 支持、cross file、syscall stub、构建集成归 M7）。
  - 浅克隆已由用户授权；**不用** `--mirror` 全历史。只动任务范围；越界须披露。

## 验收标准

1. **锁条目**：`manifests/components.lock.toml` 追加 picolibc 条目且字段如上（`grep` 真实输出）；其它组件条目零改。
2. **骨架存在**：`components/picolibc/{README.md,changelog.md,series,patches/dadao/README.md.patch}`（`find` 输出）；占位补丁**声明无行为**、未引入真移植。
3. **浅克隆**：`make fetch` EXIT=0；`.cache/picolibc.git` 为**浅**镜像；`.work/source/picolibc` 存在且 `--is-shallow-repository`=`true`；`git apply` 后 `HEAD`=`base+1`（`apply_series` 建本地补丁提交，`check_patch_tree` 断言⑧/⑨要求）。
4. **门控**：`make check`、`make check-patch-tree`、`make check-no-residue` **EXIT=0**；`check_patch_tree.py` 注入反例（清空 `series`）⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿。
5. **test 重心证据**：`.work/source/picolibc/test/` 存在（给 `ls` 摘要）——为 M7「test 重心」留证。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：全绿。
- `make fetch` EXIT=0（`.work/log/infra/INFRA-055t-fetch.log`）：`fetch: mirror picolibc.git shallow-cloned (ref=release-1.8.12)` + `fetch: picolibc -> 2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`；`HEAD is now at 2ae376c Version 1.8.12`。
- `.work/source/picolibc` HEAD=`2ae376c6…`、`--is-shallow-repository`=`true`；`.cache/picolibc.git` `--is-shallow-repository`=`true`。
- `make apply-series` EXIT=0：`picolibc 1 applied, 0 skipped` ⇒ `.work/source/picolibc` HEAD=`3aeb382e…`（base+1）。
- `make check` EXIT=0（`check-patch-tree: 4 component(s), 110 patches OK`、`check-index-blobs: 83 new-file patch(es) OK`、`repository checks: PASS`）；`make check-patch-tree` EXIT=0；`make check-no-residue` EXIT=0（PASS）。
- 注入自检：清空 `series` ⇒ `check-patch-tree: picolibc: series is empty` **RC=1** ⇒ `cp`+md5 还原（md5 `ed734078…` 相等）⇒ **RC=0**。
- picolibc `test/`：存在（54 条目，`test/**/*.c` 342 个），`test/libc-testsuite/`、`test/semihost/`、`test/test-ctype` 等——M7 test 重心证据。

**修改文件**（`git status --porcelain -uall` 仅此 + 本任务书）：
- `manifests/components.lock.toml`（追加 picolibc 条目；其它零改）
- `components/picolibc/README.md`、`changelog.md`、`series`（新）
- `components/picolibc/patches/dadao/README.md.patch`（新；最小占位，声明无行为）
- 本任务书

**验收结果**：① 锁条目字段与用户指示逐字一致（`git diff` 仅 picolibc 条目）✓；② 骨架 4 文件、占位声明无行为 ✓；③ 浅克隆 + base+1 ✓；④ 三门控 EXIT=0 + 注入 FAIL→还原→回绿 ✓；⑤ `test/` 存在 ✓；⑥ 无残留 ✓。

**版本裁定（用户 2026-10-11）**：保持 `1.8.12`（tag；= `release-1.8.12` 同一 commit `2ae376c6…`）；`shallow_ref` 用 tag（不可变）——锁内 `shallow_ref` 由 `"release-1.8.12"` 改为 `"1.8.12"`（`commit` 不变，镜像已含该 commit ⇒ `make fetch` 不重下）。

**新发现/坑**：
- **验收③与「`HEAD==锁定 commit`」同刻不可并存**（同 `INFRA-051t`）：`check_patch_tree` 断言⑧硬要求 `.work/source`=`base+1`（且断言⑥/⑧/⑨在源树存在时生效），故 enabled 组件必须「有 ≥1 补丁且已 `apply-series`」。`make fetch` 后 HEAD=base；`make apply-series` 后 HEAD=base+1。**引用用户此前对 embench 的同款裁定**（2026-10-09「放 1 个最小占位补丁」）。
- **ADR 提醒**：本任务为组件上游选择 + 精确 commit 固化（`ADR-0005`/`ADR-0006` 判据：外部契约/结论固化），**建议（拟）`adr-0023-picolibc-upstream.md`**；本任务未落 ADR（由用户裁定）。指针 `.tao/adr/adr-0022-embench-upstream.md`（同类先例）。
- `make fetch` 首次对 picolibc **联网**浅克隆（GitHub，用户已授权浅克隆）；其余组件均本地镜像、零联网。

**遗留问题**：真移植（cross file / board support / syscall stub / 构建集成 / 以自带 test 为重心接入门控）归 **M7**；本任务仅骨架占位。ADR 待用户裁定。**`adr-0023-picolibc-upstream`（上游 + 精确 commit 固化）待用户裁定——本任务未立**（ADR 提醒已记「新发现/坑」，按 `AGENTS.md`「ADR 提醒」不擅自立）。

## 审阅记录

#### architect 提交与文件集审核（2026-10-11）

本任务无独立 reviewer 轮（用户直派、architect 提交 + 落地）。文件集对账：显式 staging `manifests/components.lock.toml` + `components/picolibc/{README.md,changelog.md,series,patches/dadao/README.md.patch}` + 本任务书；`git diff --cached --name-only` 与「修改文件」声明一致，无漏提/多提/越界（`spec/`/`contracts/`/`Makefile`/其它组件交集为空）。档位：正常提交（无 Needs Revision）。

#### reviewer 独立验收（第 1 轮）

**1. 锁条目**：`git diff cf37d90^ cf37d90 -- manifests/components.lock.toml` → 只增 `[[component]] name="picolibc"` 一条（其它条目零改）；字段完整：`enabled=true` / `repository` / `commit=2ae376c6…` / `shallow=true` / `shallow_ref="release-1.8.12"` / `patch_dir` / `patch_series` / `role`。✓

**2. commit 正确性**：`git ls-remote --tags` → `refs/tags/1.8.12^{}` = `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff` == 锁内 `commit` ✓；`refs/heads/release-1.8.12` = 同一 commit ✓。GitHub Compare API `2ae376c6...main`：`status=ahead`, `ahead_by=156`, `behind_by=0` → `2ae376c6` 是 `main` 的祖先（main 领先 156 commit）。✓

**3. 浅克隆**：`.cache/picolibc.git` exists，`--is-shallow-repository`=**true**，`HEAD`=`2ae376c6`（=锁定 commit）✓；`.work/source/picolibc` exists，`--is-shallow-repository`=**true**，`HEAD`=`3aeb382e…`（=base+1，因 `apply-series` 已执行；`HEAD~1`=`2ae376c6`）。✓

**4. 门控**：`make check` EXIT=**0**；`make check-patch-tree` EXIT=**0**（4 component(s), 110 patches OK）；`make check-no-residue` EXIT=**0**。**独立注入**：`cp components/picolibc/series` → md5=`ed734078…`（备份）；清空 series → `check-patch-tree: picolibc: series is empty` RC=**2**（FAIL）；`cp` 还原 + md5 验证相等 → `check-patch-tree` EXIT=**0**（回绿）。✓

**5. 占位补丁**：`components/picolibc/patches/dadao/README.md.patch` 内容 = 新建 `dadao/README.md`（纯文字说明、"No behaviour is declared here"、"real port belongs to M7"），声明无行为 ✓；`series` = `dadao/README.md.patch` 非空（`check_patch_tree` 硬要求，同 embench 裁定）。✓

**6. test/ 资产**：`ls .work/source/picolibc/test | wc -l` = **54**；`find … -name '*.c' | wc -l` = **342**（含 `libc-testsuite/`、`semihost/`、`test-ctype`、`test-math`、`test-posix` 等）。✓

**7. 边界**：`git status --porcelain -uall` = 空（干净）；无 `_tmp/_orig/_rej` 残留；`git log origin/master..HEAD` = 1 条（`cf37d90`，未 push）。✓（注：commit 额外含 `.tao/knowledge/changelog.md`，不在完成区「修改文件」主列表中，属知识沉淀追加，非功能问题。）

**8. `shallow_ref` 改为 tag `1.8.12` 判定**：**成立且推荐**。依据：`git ls-remote --tags` 显示 `refs/tags/1.8.12^{}` 指向 `2ae376c6`（与锁内 commit 一致）；`git clone --branch` 同时接受分支名和 tag 名；tag 是不可变引用（分支 `release-1.8.12` 可被上游移动），改用 tag 更规范且不改变实际 shallow clone 的 ref（同一 commit、无需重下镜像）。⚠️ 需注意：picolibc 同时有 annotated tag `1.8.12`（tag object `f859fb62`）和 lightweight `1.8.12-1`（不同 commit `ef62ce7b`）——取 `1.8.12`（不是 `1.8.12-1`）即可。建议后续任务跟进此改动。

**判决**：**Accepted** —— 全部 7 条硬约束核验通过，注入→FAIL→还原→回绿闭环完整，无违反。

#### architect 收尾 + 落地（2026-10-11）

**版本裁定（用户 2026-10-11）**：保持 `1.8.12`（tag；= `release-1.8.12` 同一 commit `2ae376c6`）；`shallow_ref` 用 **tag**（不可变）。据此锁内 `shallow_ref` `"release-1.8.12"` → `"1.8.12"`（`commit` 不变）。

- `make fetch` EXIT=0：`fetch: mirror picolibc.git already has 2ae376c6cdf4; skipping fetch` —— **未重下**（日志 `/tmp/opencode/arch-infra055t-close/fetch.log`）。
- `make check` EXIT=0：`check-patch-tree: 4 component(s), 110 patches OK`、`check-no-residue: PASS`、`repository checks: PASS`、lit 89/89。
- `make check-patch-tree` EXIT=0：`4 component(s), 110 patches OK`。
- **落地说明**：本地 `master` 已含 `cf37d90`（与分支 `2b37484` 同内容、树一致之接入 commit）；`merge --squash INFRA-055t` 会因双侧在**同一点新增 picolibc 块且 `shallow_ref` 不同**而冲突/无新内容，故直接在 `master` 单条提交收尾（未 `push`；分支 `INFRA-055t` 保留未删）。
- **登记**：`adr-0023-picolibc-upstream`（上游 + 精确 commit 固化）**待用户裁定**（「遗留问题」+ `changelog`）；lessons §8.52（`shallow_ref` 用 tag）。
- **修改文件**：`manifests/components.lock.toml`、`.tao/tasks/infra/INFRA-055t-*.md`、`.tao/knowledge/changelog.md`、`.tao/knowledge/lessons.md`。
