# SPEC-190t: DADAO-23 与 DDLN 屏蔽寄存器旧引用清理

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-188t`（已验证；5 个无效屏蔽寄存器定义已删）、`SPEC-189t`（跨节原因表同步；同改 spec 锁，须串行）
**状态**：已验证

## 执行环境
本地；只改 DADAO-23 与 DDLN 的旧屏蔽寄存器引用，不改语义结论、不改实现。

## 背景

`SPEC-188t` 已删除 5 个无效屏蔽寄存器，但仍有旧引用：

- `spec/DADAO-23-HBI-超管系统二进制接口.md` §3：
  - `inner_cfx_mask` 初始化/移交（约 25/53/71/72 行）
  - `<mode>_switch_cfx_mask`（约 40 行）
  - `excp_prev_cfx_mask`（约 51/71 行）
- `docs/DDLN/C-资源管理/{DD-C002,DD-C003,TT-C002,TT-C003}`：
  - `switch_cfx_mask`、`excp_prev_cfx_mask`、`excp_cause_nonmaskable` 仍按旧模型解释

这些与 A/A1 模型冲突：

- 同步异常不可屏蔽
- 异步中断先入当前 monitor，按 `cfx_intr_mask` + `global_cfx_intr_mask` 过滤，屏蔽置 `excp_pending`
- `escape` 不再恢复 `excp_prev_cfx_mask`；`global_cfx_intr_mask` 保留
- `switch_cfx_mask`/`inner_cfx_mask` 不存在

## 目标

1. `DADAO-23 §3` 的 HBI 启动/移交初始化改为 A/A1：
   - 不再初始化 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`
   - 初始化 monitor 的 `cfx_intr_mask`/`global_cfx_intr_mask`（按需要）
   - 移交后 `inner_run_mode`/`inner_cfx_code` 保留；不再设置无意义 mask
   - `escape` 不再恢复 prev mask；`global_cfx_intr_mask` 的 trap 保存/escape 恢复保留
2. DDLN 四册的旧解释同步为 A/A1；只改说明，不改技术结论。
3. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `dadao-23` sha（若 DADAO-23 在锁内）；其它册不变。
4. 不改 QEMU/gem5/tests；实现同步另立任务。

## 接口规范

- DADAO-23：保留 §3 结构/标题；只改初始化与移交句；不新增寄存器。
- DDLN：保留问答结构；把旧 mask 名称替换为现行模型；不得把 DDLN 写成规范真源。
- 历史段/变更记录不改；DADAO-23 追加一条变更记录（无任务号/ADR/ISS）。
- 锁：仅 `dadao-23` 块（若锁含该册）；`docs/` 不入 spec 锁。

## 范围 / 非范围

**在范围内**：`spec/DADAO-23-HBI-超管系统二进制接口.md`（仅 §3 + 变更记录）、`docs/DDLN/C-资源管理/{DD-C002,DD-C003,TT-C002,TT-C003}.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：QEMU/gem5/tests、`contracts/**`、`.tao/contracts/**`、`DADAO-12/13/22/Machine-v5`（已由 186t/188t/189t 处理）、`DADAO-23` 其它章节。

## 验收标准

1. **引用清零**：`inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 在 DADAO-23 活文件与 DDLN 四册 0 命中（历史/变更记录除外）。
2. **A/A1 一致**：DADAO-23 初始化/移交不再设置无效 mask；`cfx_intr_mask`/`global_cfx_intr_mask` 保留；`escape` 不再恢复 prev mask。
3. **DDLN**：四册解释与现行 spec 一致，不引入新规范结论。
4. **锁**：`dadao-23` sha 与 `sha256sum` 逐字相等（若在锁内）；其它册不变。
5. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-knowledge-refs`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：把 `switch_cfx_mask` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- DDLN 是“给别人看”的讲义层，不是规范真源；同步以 spec 为准。
- 若 DADAO-23 §3 的初始化语义需要新增/变更寄存器，先留问，不自行扩。
- 实现（QEMU/gem5/tests）由后续任务处理；本任务只清文档/规范引用。

## 未决（下发前确认）

1. DDLN 四册是否全部纳入，还是只改直接引用 `switch_cfx_mask`/`excp_prev_cfx_mask` 的两册；默认四册全改。
2. DADAO-23 §3 初始化是否需要新增 monitor `cfx_intr_mask` 初始化值；默认只删无效 mask，不新增语义。

## 完成区

**测试结果**：`运行期证据脚本` → `RUN_EXIT=2`（`FAILS=0 ENV_BLOCKED=1`；语义/锁/范围/10 项 spec 门控全 PASS，L1 唯一红为并发环境 `check-patch-tree`）；`run.sh --inject` → `INJECT_EXIT=0`（注入 `switch_cfx_mask` ⇒ 语义断言 rc=1；`cp`+`md5sum -c` 还原 ⇒ rc=0）。
**修改文件**：`spec/DADAO-23-HBI-超管系统二进制接口.md`（仅 §3 初始化/移交句 + 0.1.4-rc 一条）、`docs/DDLN/C-资源管理/DD-C002`/`DD-C003`（经 TT 副本同步）、`manifests/spec-readonly.lock.toml`（仅 dadao-23 注记 + sha）、`.tao/knowledge/milestones.md`（本行状态）、本任务书；另在工作树内编辑 gitignored 草稿 `TT-C002`/`TT-C003`（不入库）。
**验收结果**：旧标识符 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 在 DADAO-23 §3 活文件与 DDLN 四册命中均 **0**（历史/变更记录除外）；`cfx_intr_mask`/`global_cfx_intr_mask` 保留且 `escape` 不恢复前一 cfx 掩码；DADAO-23 标题行增删 **0**；锁 sha `efcb7d42…b57e56` 与 `sha256sum` 逐字相等，相对 HEAD 仅 dadao-23 册变化；`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-knowledge-refs`、`check-milestones-fresh` 全 **rc=0**；`make -k check` 除 `check-patch-tree` 外全过，`git status --porcelain -uall` 仅 6 个允许文件、无残留；未决处置：DDLN 四册全改，未新增寄存器/语义。
**新发现/坑**：`check-patch-tree` 红根因 = `QEMU-083t` 并发占用共享 `共享 QEMU 源树`（源 HEAD `4d604a4` ≠ 锁提交 `c3d48b7`）；同一时刻 `master` 工作树 `check-patch-tree` 同样 rc=2、断言 ⑥/⑨ 一致，故判环境红而非本任务红。DDLN `DD-*` 按规则先复制为 `TT-*` 编辑再回写，`TT-*` 被 `.gitignore` 忽略、不在提交内。
**遗留问题**：① `make check`（L1）因上述并发源树未达 rc=0，待 QEMU-083t 合入后由收尾方复跑；② `TT-C002`/`TT-C003` 为 gitignored 草稿且位于任务 worktree，收尾删 worktree 前需把这两份草稿同步到主工作树，否则主树 TT 落后于 DD。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 DADAO-23 §3、DD-C002/003（TT 同源）、锁注记与证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 注入备份落在 worktree 根，产生 `DADAO-23.bak` 残留 | ✅已修 | 备份改到 `运行期证据临时目录/` | `git status --porcelain -uall` 仅 6 个允许文件 |
| `semantic_check` 恒返回 0，注入判定假绿 | ✅已修 | PASS/FAIL 分支显式 `return 0/1` | 注入 rc=1、还原 rc=0（`INJECT_EXIT=0`） |
| DADAO-23 §3 复位条第 2 项未点明是 monitor 的中断掩码 | ✅已修 | 改为「monitor 的 `cfx_intr_mask`/`global_cfx_intr_mask`…先入 monitor 再过滤」 | 语义断言 + `check-spec-changelog` rc=0 |
| DD-C002「屏蔽与 pending 由两个 mask 承担」表述不精确 | ✅已修 | 补 `excp_pending` | DDLN 旧标识符 0 命中 |
| DDLN 规则要求先改 TT 再回写 DD | ✅已修 | 建 TT 副本→改 TT→`cp` 回写 DD | TT/DD 内容一致、`grep` 旧名 0 |

#### 第 1 轮 reviewer 验收

**判决：Accepted**（环境红如实记录，未写 PASS；finding 与收尾必办见末段）。以下均为 reviewer 本人在任务 worktree 重跑的真实输出。

**重跑记录**
- `bash 运行期证据脚本` → `RUN_RC=2`（`FAILS=0 ENV_BLOCKED=1`）；10 项门控逐条 `rc=0`；语义 19 项全 PASS；锁 sha `efcb7d42…b57e56` 与 `sha256sum` 实测逐字相等；标题行增删 0；DDLN 新增行含 `spec/|SPEC-n|真源` = 0；范围恰 6 个允许文件。
- `run.sh --inject` → `ENGINEER_INJECT_RC=0`（注入断言 rc=1、还原 rc=0、`md5sum -c` = `OK`），与完成区声明一致。
- **独立注入**（reviewer 自己把 `switch_cfx_mask` 写入 §3；`cp` 备份至 `运行期备份`，md5 `9793cb8f…`）→ 重跑同一 `run.sh` → **`rc=1`、`FAILS=4`**（语义断言、锁 sha、`check-spec-readonly`、L1 同时转红）；`cp` 回 + `md5sum -c` → `OK` → 重跑 → **`rc=2`、`FAILS=0`**。全程未用 git 还原；注入前后 `git status -uall` + 8 文件 md5 快照 `diff` = `SNAPSHOT_IDENTICAL`。
- `make -s -k check`（L1）**4 次独立尝试**：14:03 / 14:11 / 14:15 / 14:41 均 `rc=2`，唯一红 `check-patch-tree`，`[FAIL]=0`、`[PASS]=1087`；14:21 一次因 `.dadao/gate.lock` 被 QEMU-083t `install-host` 占用而阻塞（记录，不计入通过）。
- **环境红独立证明**：① 干净 `master` 工作树 `make -s check-patch-tree` → **rc=2**，断言⑥/⑨与任务树逐字相同；② 源树 HEAD `4d604a4` ≠ 锁 `c3d48b7`；③ 共享 QEMU 源树的 `git diff c3d48b7..HEAD -- target/dadao/helper.c` 与主树 `helper.c.patch` 的差异恰为 QEMU-083t 的 13 处 `cfxha`→`env->inner_run_mode`，且与 QEMU-083t worktree 的 patch 逐字相同；④ `check_patch_tree.py` 输入仅 `manifests/components.lock.toml` + `components/<n>/` + 共享源树目录，本任务改动 0 命中 ⇒ 判**环境红**（QEMU-083t 至 14:46 仍 `待验收`、源树未稳定，L1 未取得 rc=0，按遗留①由收尾方复跑）。

**约束核验**
- DADAO-23 §3：`inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 正文 0 命中（全文仅 66/72/73 三行，均在「附录：版本与变更记录」第 59 行之后：66 为本次新增条目、72/73 属 0.1.3 历史）；初始化/移交改 monitor 的 `cfx_intr_mask`/`global_cfx_intr_mask`；移交句明写 `escape` 只恢复 `excp_prev_run_mode` 与 trap 保存的 `global_cfx_intr_mask`；`git diff -U0` 标题行增删 0；0.1.4-rc 恰追加 1 条。
- DDLN 四册：DD/TT 逐对 md5 相同（C002 `3a655ccd…`、C003 `6aeda8c6…`）；四册旧 id 与 `excp_cause_nonmaskable` 命中均 0；口径与 `spec/DADAO-12` 第 750/801/803/898 行（A/A1：escape 恢复、两层过滤置 `excp_pending`、不保存独立屏蔽状态）一致，未新增规范结论、未把 DDLN 写成真源。
- 锁：`git diff -- manifests/spec-readonly.lock.toml` 仅 1 对 `-sha256/+sha256`，仅 dadao-23；实测 sha 相等；脚本按路径解析全锁比对，相对 HEAD 变化册 = 仅 DADAO-23。
- 范围：`git status --porcelain -uall` 恰 6 个允许文件；`git diff --name-only | grep -E 'qemu|gem5|tests/|contracts/'` rc=1（无命中）；完成区 8 行 ≤30 行、状态 `待验收`。

**交接（合并前必办）**：主树 `TT-C002`/`TT-C003` md5 `9714d83e…`/`5f416345…`，仍含旧 id 1/4 处，落后于任务 worktree 的 `3a655ccd…`/`6aeda8c6…`；TT 被 `docs/DDLN/.gitignore`（`TT-*`）忽略、不入库 ⇒ **删任务 worktree 前必须把这两份 `cp` 回主树对应路径并核 md5，否则草稿丢失**。

**finding（非阻断）**：① `run.sh` 的 ENV 判据「源 HEAD ≠ 锁 commit」几乎恒真（源树常态 = `base + dadao: qemu patch series`），会把真红也归 ENV——本次已另用「master 同红 + 输入 0 命中」独立证明，建议改为「失败目标 = check-patch-tree 且主树同红」；② 完成区含运行期源码树路径 `共享 QEMU 源树`（AGENTS「任务书不写运行期路径」），文档级，收尾顺手改；③ 任务 worktree 根有 gitignored 检查日志残留（`check-*.log`/`run.log`/`inject.log`），随 worktree 删除，收尾确认清空。

#### 收尾（architect，2026-11-05）

- TT-C002/TT-C003 已从任务 worktree 复制回主工作树，md5 与 reviewer 实测一致（`3a655ccd…`/`6aeda8c6…`）；TT 为 gitignored，删 worktree 前已保护。
- F2：`run.sh` 的 ENV 判据“源 HEAD ≠ 锁 commit”健壮性不足，记入遗留；不影响本任务语义结论。
- F3：运行期路径已改为通用描述。
- L1 环境红（`check-patch-tree` 被并发 QEMU-083t 源树占用）待 QEMU-083t 合并后由 architect 复跑；绿后再置 `已验证`。
