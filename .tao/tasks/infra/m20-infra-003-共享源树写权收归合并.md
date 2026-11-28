# m20-infra-003: 共享源树写权收归合并（强规则）——任务一律用私有源树

**模块**：infra
**项目里程碑**：M20
**依赖**：无（与 `m20-infra-001` 并行）
**可并行分片**：否（动 `Makefile`/`tools/infra`，全局串行）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-28 裁定「按第三条强规则进行」）

仓库频繁出现「**二进制对、源码树错**」：`check-patch-tree` 的 ⑥（patch 复现不出 worktree）与 ⑨（源树 HEAD 与补丁集不一致）反复红。根因不是并发（同组件单写者规则一直存在），而是**共享源树 `.work/source/<c>` 的写权谁都能拿**：

- `merge --squash` 只改 `components/<c>/patches`，不碰 `.work/source` ⇒ 合并后树落后；
- 任务 engineer 在共享树上 `apply_series` 自己的分支 ⇒ 树超前于 master（2026-11-28 实测：qemu 源树 HEAD `10:14` vs master 补丁 `08:51`）；
- 改了树忘了 `make_patch.py` ⇒ 补丁复现不出树。

**强规则（用户裁定）**：**共享源树的写权只归「合并」这一动作（主会话）**；任务一律在自己的**私有源树**里 apply/导出/构建。这样「共享树 == master 补丁集」成为不变量，⑥⑨ 不再因任务而漂。

## 目标

1. **统一源树根**：引入 `DADAO_SOURCE_ROOT`（默认 `.work/source`），所有构建/导出路径从它派生：
   - `Makefile` 的 `QEMU_SRC`/`GEM5_SRC`/`LLVM_SRC` 改为由 `$(DADAO_SOURCE_ROOT)` 派生（保持默认值不变）；
   - 其余组件（`musl`/`picolibc`/`linux`/`busybox`/`chipyard`/`llvm-project`）逐个核对：路径硬编码的脚本必须支持 `--source/--build` 或同名 env 覆盖（已有 `DADAO_LINUX_SOURCE`/`DADAO_LINUX_BUILD` 的沿用，不重复造）。
2. **私有树工具** `tools/infra/private_source.sh <component> <task-id>`：
   - 在 `.work/private/<task-id>/source/<component>` 建私有树：从 `.cache/<component>.git`（`git clone --shared` 或 `worktree`）检出 manifest 的 base，再 `apply_series.py --component <component> --source <path>`；
   - 打印要 export 的变量与 `make ... <VAR>=...` 建议（不替用户改环境）。
3. **主会话重放工具** `tools/infra/replay_source.sh <component>`：
   - `git -C .work/source/<c> reset --hard <manifest base>` → `apply_series.py --component <c>` → `check_patch_tree.py --source-state <c>` 校验；
   - 设 `DADAO_SHARED_SOURCE_OWNER=main-session` 作为写共享树的唯一凭据。
4. **共享树写守卫**：`apply_series.py` / `make_patch.py` 在目标路径位于共享根（`DADAO_SOURCE_ROOT` 默认值）且 `DADAO_SHARED_SOURCE_OWNER != main-session` 时 **rc=2 拒绝**，提示改用 `private_source.sh`。
5. **文档**：`AGENTS.md §3` 加不变量一句；`docs/Process-01` 补「合并即重放 + 任务用私有树」；`.opencode/commands/complete.md` 收尾段补「合并后 `replay_source.sh <c>`」；`.tao/knowledge/nodes.md §8` 注明节点单写者场景可继续用共享树。

## 验收（逐条贴真实 rc）

1. **守卫可失败**：任务 worktree 内对共享树跑 `apply_series.py --component qemu` ⇒ **rc=2** 且提示 `private_source.sh`；设 `DADAO_SHARED_SOURCE_OWNER=main-session` ⇒ 通过。
2. **私有树端到端（qemu 示例）**：`private_source.sh qemu <task>` → apply → `make_patch.py qemu`（`written files 0`）→ 用私有 build 目录构建 → 跑一个 qemu 相关门控；**全程共享树 md5/mtime 不变**（脚本化对账，不能只看 `git status`）。
3. **主会话重放**：`replay_source.sh qemu` 后 `python3 tools/infra/check_patch_tree.py --source-state qemu` 通过、qemu 段 0 problem。
4. **默认行为不回归**：未设新变量时 `make build-qemu`/`make fetch`/`check-patch-tree` 与改前**逐字节相同的失败集**（给 `diff`）。
5. 文档四处更新；`check-knowledge-refs`、`check-manifests-guard`、`check-tests-index` rc=0。

## 约束

独立 `git worktree`；不提交 git；只改 `Makefile`、`tools/infra/{apply_series,make_patch,private_source,replay_source,check_patch_tree}.*`、上述文档与本任务书；**不改门控判据语义**（⑥⑨ 的红绿结论不变）；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-28）

- **F1 真实共享树的自测风险**：owner 凭据的“放行”分支若在真共享树上跑会写共享树。处置：✅已修——配对测试放到由 `.cache` 克隆的一次性 sandbox（代码相同、共享根为副本），真共享树只跑 rc=2 的拒绝分支；证据全程 md5+mtime 对账。
- **F2 证据脚本相对日志路径**：子 shell 切到 sandbox 后相对日志丢失，若干断言变成空值假 FAIL。处置：✅已修——`EVID/LOGS/TMP` 统一绝对路径。
- **F3 基线路径归一化**：`git archive` 基线经 `.work` 软链后 realpath 与替换串不一致，`make -n` 出现假 diff。处置：✅已修——同时替换 `BASEWT` 与 `BASEWT_REAL`。
- **F4 子模块错误被吞**：`replay_source.sh` 的 process substitution 在 `set -e` 下不传播 python 失败。处置：✅已修——改为命令替换 + `|| exit`。
- **F5 并发写者导致证据假红**：首轮证据运行期间另一任务在真共享 qemu 上做注入，快照对账捕获到（正是本任务要消除的漂移）。处置：✅已修——等其退出后重跑；证据脚本的共享快照断言保留（有可达 FAIL）。
- **F6 仍硬编码共享路径的构建脚本**（musl/picolibc/busybox/chipyard）：任务书范围只允许改 Makefile/五个 tools 文件，未改这些脚本。处置：⏸延后（见「待裁定」）；同时在 Makefile 给四个构建目标加 `$(error)` 显式失败，避免 `DADAO_SOURCE_ROOT` 覆盖时静默读共享树。
- **F7 节点引导回归（用户 2026-11-28 补报）**：守卫会让 `bootstrap_node.sh` step 5 的 `apply_series` 在节点上 rc=2。处置：✅已修——守卫放宽为「非空 token 放行、空/空白拒绝」；bootstrap step 5 显式 `env DADAO_SHARED_SOURCE_OWNER=node-single-writer`（可用同名环境变量覆盖；**纯空白 die，空串走默认 node token**）；`--dry-run` 打印同一命令；Process-01/nodes.md 写明 token = 单写者自证，非身份认证。
- 判决：F1–F5、F7 已修并复验；F6 显式失败 + 待裁定，无其它未决项。

### 第 1 轮 reviewer 验收（2026-11-28，全部我本人重跑，rc 取被检命令自身、不 `| tee`）

**重跑记录**
1. **守卫两态**（本树，`env -u`/`env` 显式控制）：无 token `apply_series.py --component qemu` **rc=2**、`make_patch.py qemu --dry-run` **rc=2**（提示均含 `private_source.sh` 与 token 语义）；空串 **rc=2**、纯空白 **rc=2**；`DADAO_SOURCE_ROOT` 为相对 / 绝对 / 经软链 / 带 `..` 逃逸且指向共享根一律 **rc=2**；`--source <私有树>` 与 `DADAO_SOURCE_ROOT=<私有根>` 在无 token 下均 **rc=0**。
2. **节点回归**：`bootstrap_node.sh --dry-run --repo-dir <本树>` **rc=0**，step 4 `fetch` 不带 token、step 5 打印 `env DADAO_SHARED_SOURCE_OWNER=node-single-writer make … apply-series`；纯空白 token **rc=2**（`source-owner token must not be empty`）；空串走默认 node token **rc=0**。
3. **默认零回归**（窗口 12:00:31–12:03:06）：证据脚本第 5 段 `make -n fetch`（2 行）、`make -n build-qemu`（33 行）与改前基线 `diff` **空**；`check_patch_tree.py` 双侧 **rc=1**、91 行**逐行相同**（67 problem）。另在 master（旧代码，`grep DADAO_SHARED_SOURCE_OWNER` 计数 0）与本树背靠背各跑全量：差 4 行 + 概要 63→67，4 行全对应 base 落后 master 的 `trans_ctrl.c.inc.patch`/`wuming_cycles.cc.patch`（`git diff --name-only 2e1064f59..4484c1d18 -- components/` 恰这 2 个补丁 + 2 changelog）⇒ 属基线差，非判据变化。
4. **私有树端到端**（我自建共享 qemu 源树 md5+mtime 快照 24222 行）：`private_source.sh qemu <task>` **rc=0** → `make_patch.py qemu --source <私有树>` **rc=0**（`0 written, 69 unchanged`）→ `DADAO_SOURCE_ROOT=<私有根> make build-qemu QEMU_BUILD=<私有build>` **rc=0**（`build-qemu: PASS`，产物 `--version` `-g113e580` = 私有树 HEAD）→ `make -s check-qemu-forms` **rc=0**；全程共享树 `cmp` **相同**。
5. **replay**（一次性沙箱克隆，未碰真共享树）：`replay_source.sh qemu` **rc=0**（69 applied）→ 注入额外 commit ⇒ `--source-state qemu` **rc=1** → 再 replay **rc=0** → `--source-state` **rc=0**、全量 `check_patch_tree.py` **rc=0**（`12 patch set(s), 464 patches OK`）；`DADAO_SOURCE_ROOT` 指私有时 replay 拒绝 **rc=1**、多余参数 **rc=2**。
6. **门控**：本树 `check-tests-index`/`check-tasks`/`check-dirs`/`check-no-residue`/`check-writer-guards` **rc=0**；**master 侧 `check-manifests-guard` rc=0 PASS**；本树 rc=2 且仅缺 `issues-m16.yaml`/`milestones-m16.md` 两条 = 分支落后 master 的既有 KNOWN-RED（与完成区一致）。
7. **证据脚本审核 + 注入**：30 条断言逐条有可达 FAIL（捕自身 rc、两态配对、共享快照独立断言、注入红链）；我重跑第 1 次 **FAIL**（基线侧 `git status` rc=128 崩溃，共享 chipyard 树正被在途任务写 = 环境干扰，非交付物）、第 2 次 **30/30 rc=0**；独立注入「token 分支恒 False」⇒ **rc=1、7 条 FAIL**，`cp`+md5 还原（`925ac7ae…` 双侧相等、grep 无残留）后重跑 **30/30 rc=0**。

**约束核验**：变更集 9 改 + 3 新（`Makefile`、`tools/infra/{apply_series,make_patch,check_patch_tree,bootstrap_node}` + 新增 `private_source.sh`/`replay_source.sh`、4 处文档、本任务书）；`git diff --name-only -- spec/ .tao/contracts/` **空**；`check_patch_tree.py` 仅加 `--source-state <组件>` 与 `DADAO_SOURCE_ROOT` 覆盖，断言 ①–⑩ 判定函数未动 ⇒ ⑥⑨ 红绿结论不变；未提交 git；注入还原只用 `cp`+md5（未用 checkout/restore/stash）。

**发现（不阻断，交 architect）**：F-a 守卫比对的是「共享根/<本组件>」，`--source <共享根>/<另一组件>` 与 `<共享根本身>` 被判为非共享而放行（实测 `refuse_shared_write('qemu', <共享>/gem5, <共享>)` = 放行）；建议改为 `source == shared_root or shared_root in source.resolve().parents`。F-b `AGENTS.md §4`「组件补丁重建」仍写裸 `apply_series.py --component <c>`，新守卫下必 rc=2，需补 token 或改指 `replay_source.sh`。F-c `check-tset-*` 已改用 `$(DADAO_SOURCE_ROOT)` 却未加 `guard_private_source_root`，私有 root 下报「not found」而非「not supported」。F-d F7 的「空值 die」与实现不符：空串走默认 node token（rc=0），仅纯空白 die（rc=2）。

**待裁定**：① **立项必要**——`build-musl`/`build-musl-shared`/`build-picolibc`/`build-busybox` 是**树内**构建（会写共享树）、chipyard harness 同理，规则对这四项目前只靠 `$(error)` 兜底（实测 `make -n build-musl` 默认 rc=0、带私有 root rc=2）；不阻塞默认路径，建议排后续任务。② **节点凭据已闭环**：bootstrap step 5 自动带 token，手工 `make apply-series` 须自证（`nodes.md` §8 已写），无需操作者额外动作。

**判决：Accepted** —— 验收命令在我自己的重跑下全部通过、硬约束无违反；F-a~F-d 记为遗留，由 architect 在收尾提交或后续任务处理。

## 完成区

**测试结果**：证据脚本 30/30 PASS（`run.sh` rc=0；含注入→红→replay→绿的还原自检、`node-single-writer`/空白 token 配对、bootstrap `--dry-run` 带凭据）。`check-knowledge-refs` rc=0、`check-tests-index` rc=0、`check-tasks` rc=0；`check-manifests-guard` rc=2 与基线失败集相同（KNOWN-RED：缺 m16 两个知识文件，非本任务引入；仅 `make` 报错行号随新增行位移）。
**修改文件**：`Makefile`；`tools/infra/apply_series.py`、`make_patch.py`、`check_patch_tree.py`、`bootstrap_node.sh`；新增 `tools/infra/private_source.sh`、`replay_source.sh`；`AGENTS.md`、`docs/Process-01-组件补丁组织与构建编排.md`、`.opencode/commands/complete.md`、`.tao/knowledge/nodes.md`；本任务书；运行期证据脚本与日志（证据目录）。
**验收结果**（逐条真实 rc）：
1. 任务 worktree 内 `apply_series.py --component qemu`（未设凭据）⇒ **rc=2** 且提示 `private_source.sh`；`make_patch.py qemu --dry-run` 同 **rc=2**。同代码 sandbox 内未设凭据 **rc=2**、设 `DADAO_SHARED_SOURCE_OWNER=main-session` **rc=0**（唯一差异为该变量）。
2. `private_source.sh qemu m20-infra-003` **rc=0**（clone→base→apply 69 patches）；`make_patch.py qemu --source <私有树>` **rc=0** 且 `0 written`；私有 build 目录 `make build-qemu` **rc=0**（PASS），产物 `--version` 含私有 HEAD `g113e580`；`make check-qemu-forms` **rc=0**。全程共享 qemu 非 `.git` 文件 md5+mtime 快照 `cmp` 相同（见证据 `shared-qemu.before/after`）。
3. 主会话 replay 未在真共享树上执行（遵守“不得写共享树”硬约束）；在同源 sandbox：注入额外 commit ⇒ `--source-state qemu` **rc=1**，`replay_source.sh qemu` **rc=0**，随后 `--source-state qemu` **rc=0**、全量 `check_patch_tree.py` **rc=0**（`qemu` 段 0 problem）。
4. `make -n fetch`、`make -n build-qemu` 与改前代码逐字节相同（归一化根路径后 `diff` 空）；`check_patch_tree.py` **rc=1** 且失败消息集与改前逐行相同（共享树既有 ⑥⑨ 漂移为基线红，非本任务引入；证据脚本已做归一化 `diff`）。
5. 文档四处已更新；`check-knowledge-refs` rc=0、`check-tests-index` rc=0；`check-manifests-guard` rc=2 基线同红。`check-writer-guards`/`check-dirs`/`check-no-residue` rc=0。
6. 节点引导回归：`bootstrap_node.sh --dry-run` **rc=0** 且 step 5 打印 `env DADAO_SHARED_SOURCE_OWNER=node-single-writer make … apply-series`；空白 token ⇒ bootstrap **rc=2**；sandbox 内 `node-single-writer` ⇒ apply **rc=0**、空白 token ⇒ **rc=2**；任务侧无 token 仍 **rc=2**。
**新发现/坑**：① 证据首轮运行期间确有一并发任务在共享 qemu 上注入 `trans_ctrl.c.inc`（快照捕获、内容其后被其恢复），正说明本规则的必要性——共享树 md5/mtime 断言必须区分“本任务操作”和“外部写者”；最终绿跑窗口内快照一致，跨窗口 mtime 会随外部写者变化。② `make -n build-qemu` 会打印 `gate-lock:` 运行态行，比较默认行为时须过滤，否则随并发假红。③ musl/picolibc/busybox/chipyard 的构建脚本仍写死共享路径，`DADAO_SOURCE_ROOT` 对它们不生效（已用 `$(error)` 显式失败）。④ 守卫若只认固定 token 会把节点引导打红：现改为「非空 token 即单写者自证」，bootstrap step 5 自动带 `node-single-writer`。
**遗留问题**：`musl/picolibc/busybox/chipyard` 私有构建覆盖未实现（任务书文件范围外，见「待裁定」）；`check-manifests-guard` 既有 KNOWN-RED（缺 `issues-m16.yaml`/`milestones-m16.md`）。

## 待裁定

1. 是否新立任务把 `DADAO_SOURCE_ROOT`/`--source` 覆盖补到 `tools/infra/build_musl.py`、`build_picolibc.py`、`tools/linux/build_busybox.py`、chipyard harness（`tools/testcases/lib/chipyard_engine.py`、`tests/ee-tiny/run_inst_tiny.py`）？本任务书允许改动的文件不含它们，故只做了 `$(error)` 显式失败。
2. （已按用户 2026-11-28 指示落地）`tools/infra/bootstrap_node.sh` step 5 已自动 `DADAO_SHARED_SOURCE_OWNER=node-single-writer`，无需操作者手工 export；token 语义 = 单写者自证。
