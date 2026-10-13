# INFRA-004t: 组件获取与打补丁工具

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-003t`
**状态**：已验证

> **注（2026-09-14 模块重划）**：脚本目录由 `scripts/` 迁至 `tools/infra/`；下方完成区/审阅记录中的 `scripts/` 为当时的历史路径。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml` 与 `manifests/references.lock.toml`（`INFRA-003t` 产出）、`components/<name>/patches/series` 与补丁本体
- 输出：`tools/infra/fetch.py`、`tools/infra/apply_series.py`、`tools/infra/make_patch.py`、`tools/infra/fetch_refs.py`
- 约束：上游**对象库（bare mirror）**落在仓库内 gitignored 的 `.cache/<name>.git`（持久，只增量 `fetch`）；工作树落在 `.work/source/<name>/`（可随 `.work` 重建，无需重新下载）；补丁只从 `components/<name>/patches/` 读取；不复制 0.4.1 的补丁正文

## 背景（完整）

### 目标

按 manifest 精确 commit 获取上游组件源码，并将 DADAO 的有序补丁序列应用到 checkout 上；同时提供把本地开发工作树导出为补丁序列的工具。

### 设计理由

- ADR-0002（v5：`.tao/knowledge/adr-0002-build-orchestration.md`）：每个组件按完整 commit 获取并应用**单一有序补丁序列**；`git am` 是唯一打补丁路径。
- 可复现性：`.work/source/<name>` 完全可由 `components.lock.toml` + 补丁序列重建，不把上游源码树或产物纳入仓库。
- **避免重下大仓库**：LLVM/QEMU/gem5 与参考仓库体量大。用**持久 bare mirror**（组件 `.cache/<name>.git`、参考 `.cache/refs/<id>.git`）作本地对象库，工作树从 mirror 建（本地硬链接，不额外占盘）；`clean_work` 只清 `.work/`、不动 `.cache/` → 清空 `.work` 后重建工作树无需网络。

### 关键概念 / 数据

- `fetch.py`（v5：mirror + worktree 两层；逻辑基于 0628 并增加持久对象库）：
  - 读取 `components.lock.toml`，取 `enabled` 组件；无 enabled 组件时打印提示并退出 0。
  - `mirror_dir = .cache`（仓库内、gitignored）；`source_root = .work/source`。
  - **对象库（mirror）** `.cache/<name>.git`：不存在则 `git clone --mirror <repo> .cache/<name>.git`（首次下载）；已存在则 `git -C .cache/<name>.git fetch --prune`（增量，不重下）。
  - **工作树** `.work/source/<name>`，从本地 mirror 建：不存在则 `git clone --no-checkout .cache/<name>.git .work/source/<name>`（本地硬链接），随后 `git fetch --no-tags origin <commit>` + `git checkout --detach <commit>`。
  - **已存在工作树**：先 `git status --porcelain`，脏则报错拒覆盖；若 `HEAD == commit` 跳过；若 commit 是 HEAD 的祖先（已打过补丁）则**保持不动**；否则 `git checkout --detach <commit>`。
  - **恢复**：`.work/source/<name>` 丢失时，从 `.cache/<name>.git` 重建，无需网络。
- `apply_series.py`（0628 逻辑，完整转述）：
  - 对每个 enabled 组件，要求 `source/.git` 存在（否则提示先 `make fetch`）；要求 `HEAD == component["commit"]`（否则报错）。
  - 读取 `components/<name>/patches/series`，逐行（跳过空行与 `#` 注释）用 `git -C <source> am <patch>` 应用；空序列打印提示。
- `make_patch.py`（v5 新增，0628 无此脚本）：从 `.work/source/<name>` 的工作树相对 base commit 生成有序补丁，输出到 `components/<name>/patches/` 并维护 `series`。0628 的补丁靠手动 `git format-patch` 产出，v5 将其工具化（参考 0628 的补丁序列**格式**，不复制其脚本或补丁正文）。

### 上游引用

- DADAO-0628 `scripts/fetch.py`（完整转述见上；含其对 `--no-checkout` clone 与"已打补丁祖先"两处关键修复的注释）。
- DADAO-0628 `scripts/apply_series.py`（完整转述见上）。
- DADAO-0628 `components/llvm/README.md` 与 `components/llvm/patches/series`：补丁序列的组织方式（`series` 有序清单 + 编号 `.patch` 文件；补丁名带任务号）。
- DADAO-0628 `docs/development-roadmap.md`（`scripts/fetch.py silently discarded applied patches` 段）：fetch 曾静默丢弃已应用补丁的事故记录。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：获取与补丁编排。

## 交付物

- `scripts/fetch.py`：维护 `.cache/<name>.git` 持久 mirror（增量 fetch），并从 mirror 建/刷新 `.work/source/<name>` 工作树到 pin commit。
- `scripts/apply_series.py`：将有序补丁序列 `git am` 到 checkout。
- `scripts/make_patch.py`：从工作树生成/维护补丁序列（v5 新增）。
- `scripts/fetch_refs.py`：按 `references.lock.toml` 维护参考仓库的**持久 mirror**（`.cache/refs/<id>.git`，首次 `git clone --mirror`、以后增量 `fetch`），并从中建/刷新只读工作树到其 `path`（`.dadao/DADAO-0628`、`.dadao/DADAO`），供任务 `## 参考` 定位；已存在且 commit 匹配则跳过；`.work` 清空后可从 mirror 重建、无需重下。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- `make_patch.py` 为 v5 新增：0628 `scripts/` 下无此脚本，补丁靠手工 `git format-patch`。本任务只参考 0628 的补丁序列格式，不复制其补丁正文。
- 组件 commit 待定：`fetch.py` 在组件 `enabled = false` 时应与 0628 一样打印"no components enabled"并正常退出。

## 已知坑 / 结论

- **`--no-checkout` clone 的 HEAD 指向远端默认分支 tip，而非 pin commit**：新 clone 必须直接 `fetch <commit>` + `checkout --detach <commit>`，否则工作树为空、HEAD 停在错误 commit（0628 在启用 musl 时发现）。
- **重跑 `make fetch` 会静默丢弃已应用补丁**：当 HEAD 已含 pin commit 作为祖先（即补丁已 `git am` 在顶部）且工作树干净时，`checkout --detach <pin>` 会破坏性地丢弃全部补丁 commit。0628 在 2026-07-15/16 真实发生（重跑 fetch 抹掉 `.work/source/qemu` 的补丁，靠 reflog 恢复）。必须检测"已打补丁"并跳过。
- 脏工作树必须拒绝覆盖，避免丢失未提交改动。
- `apply_series.py` 严格要求 `HEAD == base commit`，防止在错误基线上叠补丁。
- 补丁应用统一用 `git am`（保留作者/提交信息），不用 `patch`/`git apply`。
- **避免重下大仓库**：`.work/` 可被 `clean_work` 清空，但 `.cache/`（组件 `.cache/<name>.git`、参考 `.cache/refs/<id>.git`）持久保留；工作树从本地 mirror 重建（硬链接），不触发网络。对已存在 mirror 只做增量 `git fetch --prune`。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/scripts/fetch.py`
- DADAO-0628：`.dadao/DADAO-0628/scripts/apply_series.py`
- DADAO-0628：`.dadao/DADAO-0628/components/llvm/README.md`
- DADAO-0628：`.dadao/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.dadao/DADAO-0628/docs/development-roadmap.md`
- DADAO-0628：`.dadao/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `fetch.py` 能按 manifest commit 获取组件；对已打补丁的 checkout 重跑不丢补丁；脏树拒绝覆盖
2. `apply_series.py` 能按 `series` 顺序 `git am` 应用补丁，并在 HEAD 非 base commit 时明确报错
3. `make_patch.py` 能从工作树生成补丁并维护 `series`（新工具，含基本自测）
4. 三脚本通过 `python3 -m compileall scripts`（`make fetch`/`make apply-series` 的集成由 `INFRA-006t` 验收）
5. `fetch_refs.py` 维护 `.cache/refs/<id>.git` 持久 mirror 并从中建参考工作树到 `path`；已存在且 commit 匹配时跳过；删除 `path` 后能从 mirror 重建、不联网
6. `.cache/<name>.git` 为持久 mirror；删除 `.work/source/<name>` 后 `fetch.py` 能从 mirror 重建工作树且不联网；`clean_work.py` 不删除 `.cache/`

## 完成区

**测试结果**：全部通过。合成自测（fake 上游 + 临时树）覆盖 fetch/apply/make_patch 的正常与错误路径；真实参考仓库幂等与离线重建测试通过。日志：
- `.tao/logs/INFRA-004t-compileall.log`（compileall，exit=0）
- `.tao/logs/INFRA-004t-fetch-no-enabled.log`（fetch 无 enabled，exit=0）
- `.tao/logs/INFRA-004t-apply-no-enabled.log`（apply 无 enabled，exit=0）
- `.tao/logs/INFRA-004t-fetch-refs-idempotent.log`（真实 refs 幂等跳过，exit=0）
- `.tao/logs/INFRA-004t-fetch-refs-rebuild.log`（真实 refs 离线重建，exit=0）
- `.tao/logs/INFRA-004t-selftest.log`（合成自测全流程，exit=0）
- `.tao/logs/INFRA-004t-manifest-check.log`（回归，exit=0）

**返工 F1 复验**（2026-09-12）：
- `.tao/logs/INFRA-004t-rework-selftest.log`（隔离合成上游 dry-run 零副作用 + 非 dry-run 不回归，PIPE_EXIT=0）
- `.tao/logs/INFRA-004t-rework-compileall.log`（compileall，COMPILE_EXIT=0）

**修改文件**（本任务均为新增；F1 返工仅改 `scripts/make_patch.py`）：
- `scripts/fetch.py`（新增）
- `scripts/apply_series.py`（新增）
- `scripts/make_patch.py`（新增；F1 返工修改）
- `scripts/fetch_refs.py`（新增）

**验收结果**（真实终端输出，日志见上）：

1) 无 enabled 组件（当前锁文件状态）——退出 0：
```
$ python3 scripts/fetch.py
fetch: no components enabled; accept baseline ADRs first
exit=0
$ python3 scripts/apply_series.py
apply-series: no components enabled
exit=0
```

2) 真实参考仓库幂等（主会话已落实的 mirror + 工作树）——退出 0、不联网：
```
$ python3 scripts/fetch_refs.py
fetch-refs: dadao-0628 already at 2d270604b778; skipping
fetch-refs: dadao already at f9bde0481668; skipping
exit=0
```

3) 真实参考仓库离线重建（删除 `.dadao/DADAO-0628`，`GIT_ALLOW_PROTOCOL=file` 禁用网络协议）——退出 0，origin 指向本地 mirror：
```
$ GIT_ALLOW_PROTOCOL=file python3 scripts/fetch_refs.py
Cloning into '/mnt/tao/DADAO-v5/.dadao/DADAO-0628'...
done.
From /mnt/tao/DADAO-v5/.cache/refs/dadao-0628
 * branch            2d270604b778d609e1a09b4047271b5309005ffc -> FETCH_HEAD
HEAD is now at 2d27060 KL-157a: bypass VFS root-mount wall via minimal built-in initramfs /init
fetch-refs: mirror dadao-0628.git already has 2d270604b778; skipping fetch
fetch-refs: dadao-0628 -> 2d270604b778d609e1a09b4047271b5309005ffc
fetch-refs: dadao already at f9bde0481668; skipping
exit=0
rebuilt HEAD: 2d270604b778d609e1a09b4047271b5309005ffc
rebuilt origin: /mnt/tao/DADAO-v5/.cache/refs/dadao-0628.git
rebuilt clean: []
```

4) 合成自测关键输出（`.tao/logs/INFRA-004t-selftest.log`）：
```
=== C. apply_series.py (replay series) ===
Applying: first change
Applying: second change
apply-series: foo applied 2 patches
exit=0
=== D. fetch.py rerun must NOT discard applied patches ===
fetch: foo HEAD (8987520a1461) already has 4fe576ace881 as an ancestor (patches applied on top) -- leaving it alone
exit=0
PATCHES PRESERVED
=== E. dirty worktree must be refused ===
fetch: .../.work/source/foo is dirty; refusing to overwrite
exit=1
=== F. apply_series.py on patched HEAD must error ===
apply-series: foo HEAD (8987520a1461) is not its base commit (4fe576ace881); refusing to apply patches
exit=1
=== J. offline rebuild of foo worktree from mirror ===  # 上游已移走，仍成功
rebuilt HEAD=4fe576ace881...
worktree origin=.../.cache/foo.git
exit=0
```

5) 回归：`python3 scripts/manifest_check.py` → `manifest validation: PASS`，exit=0。

6) **F1 返工复验**（隔离合成上游；`/tmp/opencode/INFRA-004t-rework/tree`，未改仓库 tracked 文件；完整日志 `.tao/logs/INFRA-004t-rework-selftest.log`）：
```
=== T1. dry-run with no components/foo present ===
ls: cannot access 'components/foo': No such file or directory
(components/foo does not exist BEFORE)
make-patch: would write 0001-first-change.patch
make-patch: would write 0002-second-change.patch
exit=0
PASS: components/foo still absent after dry-run

=== T2. non-dry-run regression: writes patches + series ===
make-patch: foo wrote 2 patches to .../components/foo/patches
make-patch: series .../components/foo/patches/series
exit=0
--- components/foo/patches ---
0001-first-change.patch
0002-second-change.patch
series
--- series ---
0001-first-change.patch
0002-second-change.patch

=== T3. dry-run on existing dir must leave it byte-identical ===
make-patch: would write 0001-first-change.patch
make-patch: would write 0002-second-change.patch
exit=0
--- before ---            --- after ---
patches/0001-first-change.patch 345   patches/0001-first-change.patch 345
patches/0002-second-change.patch 353  patches/0002-second-change.patch 353
patches/series 49                     patches/series 49
PASS: components/foo/patches unchanged (names+sizes+sha1)
```
真实仓库 `components/` 仍仅 `components/.gitkeep`，无 patches 目录被创建（见下）。`python3 -m compileall -q scripts` → COMPILE_EXIT=0（`.tao/logs/INFRA-004t-rework-compileall.log`）。

**验收标准逐条自审**：
1. `fetch.py` 按 manifest commit 获取组件；重跑不丢补丁；脏树拒绝覆盖 —— ✅ 通过（合成自测 A/B/D/E；offline 重建 J）
2. `apply_series.py` 按 series 顺序 `git am`；HEAD 非 base 时明确报错 —— ✅ 通过（合成自测 C/F；空序列 L；缺 source M）
3. `make_patch.py` 从工作树生成补丁并维护 series（含基本自测）—— ✅ 通过（合成自测 G/H；unknown component K；unpinned commit N）
4. 三脚本通过 `python3 -m compileall scripts` —— ✅ 通过（实际四个脚本全部编译通过，exit=0）
5. `fetch_refs.py` 维护 `.cache/refs/<id>.git` 持久 mirror 并从 mirror 建工作树到 `path`；已存在且 commit 匹配时跳过；删除 `path` 后离线重建 —— ✅ 通过（真实 refs 测试 2/3）
6. `.cache/<name>.git` 为持久 mirror；删除 `.work/source/<name>` 后 `fetch.py` 从 mirror 重建且不联网；`clean_work.py` 不删 `.cache/` —— ✅ 通过（fetch 部分：合成自测 J；`clean_work.py` 属 `INFRA-005t` 交付物，见遗留问题）

**新发现/坑**：
- **「已存在 mirror → 无条件 `fetch --prune`」与「重建不联网」冲突**：任务书 line 35/57 写"已存在则增量 fetch"，但验收标准 5/6 要求"删除工作树后从 mirror 重建、不联网"。若对已存在 mirror 无条件 `git fetch`（origin=GitHub），离线重建会失败。实现取二者交集：**mirror 已含 pin commit 时跳过 fetch（打印跳过），缺 commit 时才 `fetch --prune`**。语义上 pin 已在本对象库即无需下载；pin 变更时仍会增量 fetch。已在 `fetch.py`/`fetch_refs.py` 统一采用。
- **`git clone --no-checkout` 的 HEAD 指向 mirror 默认分支 tip**（非 pin），故新建工作树后必须 `git fetch <commit>` + `checkout --detach <commit>`；沿用 0628 的修复注释。
- **`git fetch --no-tags origin <sha>` 对本地 mirror origin 可用**：合成自测中从 `.cache/<name>.git` clone 后按 SHA fetch 成功（本地 file 传输），无需 `uploadpack.allowAnySHA1InWant`。
- **`git format-patch -o` 会覆盖同名补丁文件**，可安全重跑；`make_patch.py` 以 `format-patch` 的 stdout 为权威有序清单写 `series`。
- 补丁应用路径由 manifest `patch_series` 的父目录推导（`components/<name>/patches/`），与 0628 硬编码 `components/<name>/patches/` 等价但更贴合锁文件。
- **`git format-patch -o <dir>` 是 dry-run 副作用的来源**：只要指定 `-o`，git 就落盘补丁文件；即便调用方随后只读 stdout 取文件名，文件也已写出。若调用方声称 "dry-run 不写盘"，必须改为 `--stdout`（解析正文，脆弱）或输出到 `tempfile.TemporaryDirectory()`（本次采用），并把 `out_dir.mkdir` 放入非 dry-run 分支。

**遗留问题**：
- **F1（`make_patch.py --dry-run` 写盘副作用）——✅已修**：dry-run 改为在 `tempfile.TemporaryDirectory()` 中渲染补丁、仅取其文件名，`out_dir.mkdir(...)` 移入非 dry-run 分支；非 dry-run 的 `git format-patch --no-signature -o <out_dir> <commit>..HEAD` 与 series 写入保持不变。复验：dry-run 在 `components/foo` 不存在时不创建目录（T1）、在已存在时文件 names+sizes+sha1 完全不变（T3）；非 dry-run 仍生成 2 补丁 + series（T2）；`compileall` exit=0。证据见上「F1 返工复验」与 `.tao/logs/INFRA-004t-rework-selftest.log`。
- 验收标准 6 的 `clean_work.py` 不删 `.cache/` 部分**不在本任务交付物内**（`INFRA-005t` 交付 `scripts/clean_work.py`）。本任务已验证 `.cache/` 为持久对象库、删 `.work/source/<name>` 后可从 mirror 离线重建；`clean_work.py` 的 `.cache/` 保护由 `INFRA-005t` 验收。
- `make fetch` / `make apply-series` / `make fetch-refs` 的 Makefile 集成由 `INFRA-006t` 验收（本任务只交付脚本）。
- 组件锁三组件仍 `enabled=false`，`fetch.py`/`apply_series.py` 的**真实组件**路径未跑（无可用 commit），已用本地合成上游等价验证；待 llvm/qemu/gem5 模块锁定 commit 后回归。

## 审阅记录

### 第 1 轮 reviewer 验收

**审查者**：reviewer subagent
**审查时间**：2026-09-12
**审查方法**：独立重跑全部验收命令 + 源码分析 + 合成自测

#### 重跑记录

##### 1. compileall
```
$ python3 -m compileall -q scripts; echo "EXIT=$?"
EXIT=0
```

##### 2. fetch.py（无 enabled 组件）
```
$ python3 scripts/fetch.py; echo "EXIT=$?"
fetch: no components enabled; accept baseline ADRs first
EXIT=0
```

##### 3. apply_series.py（无 enabled 组件）
```
$ python3 scripts/apply_series.py; echo "EXIT=$?"
apply-series: no components enabled
EXIT=0
```

##### 4. fetch_refs.py（幂等跳过）
```
$ python3 scripts/fetch_refs.py; echo "EXIT=$?"
fetch-refs: dadao-0628 already at 2d270604b778; skipping
fetch-refs: dadao already at f9bde0481668; skipping
EXIT=0
```

##### 5. fetch_refs.py 离线重建（删除 `.dadao/DADAO-0628` 后，`GIT_ALLOW_PROTOCOL=file`）
```
$ rm -rf .dadao/DADAO-0628
$ GIT_ALLOW_PROTOCOL=file python3 scripts/fetch_refs.py; echo "EXIT=$?"
Cloning into '/mnt/tao/DADAO-v5/.dadao/DADAO-0628'...
done.
From /mnt/tao/DADAO-v5/.cache/refs/dadao-0628
 * branch            2d270604b778d609e1a09b4047271b5309005ffc -> FETCH_HEAD
HEAD is now at 2d27060 KL-157a: bypass VFS root-mount wall via minimal built-in initramfs /init
fetch-refs: mirror dadao-0628.git already has 2d270604b778; skipping fetch
fetch-refs: dadao-0628 -> 2d270604b778d609e1a09b4047271b5309005ffc
fetch-refs: dadao already at f9bde0481668; skipping
EXIT=0
```
验证：`rebuilt HEAD=2d270604b778d609e1a09b4047271b5309005ffc`，`rebuilt origin=/mnt/tao/DADAO-v5/.cache/refs/dadao-0628.git`，`rebuilt clean=[]`

##### 6. 合成 fake 上游全流程自测（reviewer 独立构造）

**环境**：本地 bare repo `/tmp/tmp.8JIAUy1gQO`，3 commits（base + 2 patches），临时替换 `components.lock.toml` 启用 `foo` 组件。

**B. fetch.py 首次运行（clone + checkout）**：
```
$ python3 scripts/fetch.py; echo "exit=$?"
Cloning into bare repository '/mnt/tao/DADAO-v5/.cache/foo.git'...
done.
Cloning into '/mnt/tao/DADAO-v5/.work/source/foo'...
done.
From /mnt/tao/DADAO-v5/.cache/foo
 * branch            a7a6a743c52bbcec924c7d8b16643da40636cd91 -> FETCH_HEAD
HEAD is now at a7a6a74 base commit
fetch: mirror foo.git cloned
fetch: foo -> a7a6a743c52bbcec924c7d8b16643da40636cd91
exit=0
```

**C. apply_series.py（应用 2 个补丁）**：
```
$ python3 scripts/apply_series.py; echo "exit=$?"
Applying: first change
Applying: second change
apply-series: foo applied 2 patches
exit=0
```

**D. fetch.py 重跑不丢补丁**：
```
$ python3 scripts/fetch.py; echo "exit=$?"
From /mnt/tao/DADAO-v5/.cache/foo
 * branch            a7a6a743c52bbcec924c7d8b16643da40636cd91 -> FETCH_HEAD
fetch: mirror foo.git already has a7a6a743c52b; skipping fetch
fetch: foo HEAD (a3489f09bbc3) already has a7a6a743c52b as an ancestor (patches applied on top) -- leaving it alone
exit=0
PATCHES PRESERVED
```

**E. 脏工作树拒绝覆盖**：
```
$ python3 scripts/fetch.py; echo "exit=$?"
fetch: mirror foo.git already has a7a6a743c52b; skipping fetch
fetch: /mnt/tao/DADAO-v5/.work/source/foo is dirty; refusing to overwrite
exit=1
```

**F. apply_series.py 在已打补丁的 HEAD 上报错**：
```
$ python3 scripts/apply_series.py; echo "exit=$?"
apply-series: foo HEAD (a3489f09bbc3) is not its base commit (a7a6a743c52b); refusing to apply patches
exit=1
```

**G. make_patch.py 生成补丁并维护 series**：
```
$ python3 scripts/make_patch.py foo; echo "exit=$?"
make-patch: foo wrote 2 patches to /mnt/tao/DADAO-v5/components/foo/patches
make-patch: series /mnt/tao/DADAO-v5/components/foo/patches/series
exit=0
--- series content ---
0001-first-change.patch
0002-second-change.patch
```

**H. make_patch.py dry-run**：
```
$ python3 scripts/make_patch.py foo --dry-run; echo "exit=$?"
make-patch: would write 0001-first-change.patch
make-patch: would write 0002-second-change.patch
exit=0
```

**I. 离线重建 foo 工作树（从本地 mirror）**：
```
$ rm -rf .work/source/foo
$ GIT_ALLOW_PROTOCOL=file python3 scripts/fetch.py; echo "exit=$?"
Cloning into '/mnt/tao/DADAO-v5/.work/source/foo'...
done.
From /mnt/tao/DADAO-v5/.cache/foo
 * branch            a7a6a743c52bbcec924c7d8b16643da40636cd91 -> FETCH_HEAD
HEAD is now at a7a6a74 base commit
fetch: mirror foo.git already has a7a6a743c52b; skipping fetch
fetch: foo -> a7a6a743c52bbcec924c7d8b16643da40636cd91
exit=0
rebuilt HEAD=a7a6a743c52bbcec924c7d8b16643da40636cd91
worktree origin=/mnt/tao/DADAO-v5/.cache/foo.git
rebuilt clean=
```

**J. make_patch.py 未知组件**：
```
$ python3 scripts/make_patch.py nonexistent; echo "exit=$?"
make-patch: unknown component 'nonexistent' (known: foo)
exit=1
```

**K. fetch.py 拒绝非 git 目录**：
```
$ python3 scripts/fetch.py; echo "exit=$?"
fetch: mirror foo.git already has a7a6a743c52b; skipping fetch
fetch: /mnt/tao/DADAO-v5/.work/source/foo exists but is not a git worktree; refusing to touch it
exit=1
```

**L. apply_series.py 缺失 source**：
```
$ python3 scripts/apply_series.py; echo "exit=$?"
apply-series: missing source /mnt/tao/DADAO-v5/.work/source/foo; run make fetch
exit=1
```

##### 7. manifest_check.py 回归
```
$ python3 scripts/manifest_check.py; echo "exit=$?"
enabled components: none
references: 2
manifest validation: PASS
exit=0
```

#### 约束核验

| 约束 | 状态 | 证据 |
|------|------|------|
| 不复制 0.4.1 补丁正文 | ✅ | 源码中仅在 docstring 提及 0628 设计背景（`make_patch.py` line 4/9、`fetch_refs.py` line 5），无补丁内容复制 |
| `.cache/` 持久（gitignored） | ✅ | `.gitignore` line 5: `.cache/`；`.work/` line 2: `.work/` |
| `clean_work` 不删 `.cache/` 属 INFRA-005t | ✅ | 任务书 line 188 已标注，本任务不涉及 |
| 修改文件仅为新增 | ✅ | `git status --short scripts/` 仅显示 4 个 `??`（untracked），无 `M` |
| mirror + worktree 两层设计 | ✅ | `fetch.py`: `.cache/<name>.git` mirror + `.work/source/<name>` worktree；`fetch_refs.py`: `.cache/refs/<id>.git` mirror + `path` worktree |
| 已打补丁重跑不丢补丁 | ✅ | 合成自测 D：HEAD 未变，输出 "already has ... as an ancestor (patches applied on top) -- leaving it alone" |
| 脏树拒绝覆盖 | ✅ | 合成自测 E：exit=1，"is dirty; refusing to overwrite" |
| HEAD 非 base 时 apply 报错 | ✅ | 合成自测 F：exit=1，"HEAD (...) is not its base commit (...); refusing to apply patches" |
| 离线重建不联网 | ✅ | 真实 refs 重建 + 合成 foo 重建，均用 `GIT_ALLOW_PROTOCOL=file` 成功，origin 指向本地 mirror |
| 幂等跳过 | ✅ | 真实 refs 幂等 + 合成 foo 幂等（"already at ...; skipping"） |

#### 验收标准逐条核验

1. `fetch.py` 按 manifest commit 获取组件；重跑不丢补丁；脏树拒绝覆盖 —— ✅ 通过（合成自测 B/D/E/I）
2. `apply_series.py` 按 series 顺序 `git am`；HEAD 非 base 时明确报错 —— ✅ 通过（合成自测 C/F/L）
3. `make_patch.py` 从工作树生成补丁并维护 series（含基本自测）—— ✅ 通过（合成自测 G/H/J）
4. 三脚本通过 `python3 -m compileall scripts` —— ✅ 通过（exit=0）
5. `fetch_refs.py` 维护 `.cache/refs/<id>.git` 持久 mirror 并从 mirror 建工作树到 `path`；已存在且 commit 匹配时跳过；删除 `path` 后离线重建 —— ✅ 通过（真实 refs 测试 4/5）
6. `.cache/<name>.git` 为持久 mirror；删除 `.work/source/<name>` 后 `fetch.py` 从 mirror 重建且不联网 —— ✅ 通过（合成自测 I）；`clean_work.py` 不删 `.cache/` 属 INFRA-005t

#### 源码分析

- **fetch.py**（140 行）：mirror + worktree 两层，正确处理 `--no-checkout` clone 后 HEAD 指向问题（line 90-98 注释），已打补丁祖先检测（line 117-132），脏树拒绝（line 102-106），commit 已在 mirror 时跳过 fetch（line 52-57）
- **apply_series.py**（58 行）：HEAD == base commit 校验（line 35-39），`git am` 应用路径，空序列处理
- **make_patch.py**（107 行）：SHA1 校验、祖先检查、`format-patch` 生成、series 维护、dry-run 支持
- **fetch_refs.py**（95 行）：与 fetch.py 同构但读 `references.lock.toml`，mirror 在 `.cache/refs/<id>.git`，worktree 在 manifest `path`

#### 与完成区自审结论的差异

工程师完成区自审结论全部通过，与 reviewer 独立重跑结果一致。但需指出：**工程师的自审子代理会话被中断**（嵌套自审的 LLM 流挂起），故「审阅记录」中无 engineer 自审轮次。这不影响验收结论，因 reviewer 已独立重跑全部验收命令。

#### 判决

**Accepted**

全部 6 条验收标准通过，约束无违反。4 个脚本语法正确、逻辑完整、边界处理充分。合成自测覆盖了 fetch/apply/make_patch 的正常路径与错误路径（共 12 个测试场景）。`manifest_check.py` 回归通过。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**（6/6 独立复现）；但提出 1 项 reviewer 遗漏的真实缺陷。

**独立核对**：自建 fake 上游复现全部核心路径（fetch / apply / 重跑不丢补丁 / 脏树拒绝 / 已打补丁 HEAD 报错 / 离线重建等），与 reviewer 记录一致；脚本读取字段与 `manifests/*.lock.toml` schema 吻合，`Path(__file__).resolve().parents[1]` 定位 ROOT 与 cwd 无关，可被 `INFRA-006t` 复用；`.cache/` 在 `.work/` 之外，`INFRA-005t` 的 `clean_work` 天然不碰；组件锁仍 `enabled=false`。

**补充发现**：

- **F1（中低，真实缺陷）`make_patch.py --dry-run` 有写盘副作用**：`git format-patch -o <out_dir>` 与 `out_dir.mkdir(...)` 在 `if args.dry_run:` 之前/之外执行，导致 `--dry-run` 实际写出补丁文件（仅不写 `series`），与 `--help` 的 "without writing anything" 矛盾。reviewer 未抓到（其自测先 dry-run 后正式写、只核对 stdout/退出码，未检查目录副作用）。
  - **处置**：判定 **Needs Revision**，本任务回退 `待返工` 做最小修复（使 `--dry-run` 零副作用）。
- N1（低，可审计性）：reviewer 自测日志未落盘（`.tao/logs/INFRA-004t-review-selftest.log` 为 0 字节）；建议后续要求 reviewer 将自测输出落盘。

**统一判决**：**Needs Revision**（以交叉复核意见为准），返工项 = F1。

### 第 2 轮 engineer 自审

**自审者**：engineer（返工）
**时间**：2026-09-12
**方式**：**自主自审（嵌套受限）** —— 尝试开 `general` subagent 做代码级 review 时返回 `Subagent depth limit reached (1)`，按规则降级为自主逐行审查。

#### 改动内容

仅改 `scripts/make_patch.py`（本任务新增文件）：
1. 新增 `import tempfile`。
2. 抽出辅助函数 `format_patch(source, commit, out_dir) -> list[str]`，封装原 `git format-patch --no-signature -o <out_dir> <commit>..HEAD` 调用与文件名解析（逻辑与原内联代码逐字一致）。
3. `out_dir.mkdir(parents=True, exist_ok=True)` 从无条件执行移入**非 dry-run 分支**。
4. dry-run 分支：在 `tempfile.TemporaryDirectory()` 中调用 `format_patch` 取文件名，打印 `would write`，不触碰 `out_dir`；临时目录退出上下文即删除。

#### 逐条 finding

| # | finding | 严重度 | 结论与证据 |
|---|---------|--------|-----------|
| E2-1 | dry-run 是否仍写补丁文件？ | 高 | ❌不存在：dry-run 只写 `tempfile.TemporaryDirectory()`，退出即删。T1 后 `components/foo` 不存在；T3 后文件 names+sizes+sha1 不变。 |
| E2-2 | dry-run 是否仍创建 `components/<name>/patches/`？ | 高 | ❌不存在：`out_dir.mkdir` 已移入非 dry-run 分支（line 107），dry-run 分支（line 95-105）无任何 `out_dir` 写操作。T1 PASS。 |
| E2-3 | 非 dry-run 行为是否回归？ | 高 | ❌无回归：同一 `format_patch` 辅助函数、同一参数 `--no-signature -o <out_dir> <commit>..HEAD`、同一 series 写入与 stdout 文案。T2 复现旧版输出：2 补丁 + series 内容一致。 |
| E2-4 | 命令行接口是否改变？ | 中 | ❌未改：argparse 参数与 `--help` 文案原样（`--help` 实测输出与旧版一致）。 |
| E2-5 | 空补丁序列边界？ | 中 | ✅保留：dry-run 与非 dry-run 两分支均在 `generated` 为空时打印 `produced no patches` 并 return 0。 |
| E2-6 | `git` 失败时临时目录是否残留？ | 低 | ✅安全：`git(...)` 用 `check=True`，异常在 `with tempfile.TemporaryDirectory()` 内抛出，上下文管理器仍执行清理。 |
| E2-7 | 是否引入新外部依赖？ | 中 | ❌无：`tempfile` 为 Python 标准库。 |
| E2-8 | dry-run 打印的文件名是否与非 dry-run 落盘文件名一致？ | 中 | ✅一致：T1/T2 均打印 `0001-first-change.patch`/`0002-second-change.patch`；命名只取决于 commit 序列与 subject，与输出目录无关。 |
| E2-9 | 真实仓库是否被测试污染？ | 中 | ❌无：`git status --short` 仅显示本任务 4 个新增脚本（`??`）与既有 `.tao`/`AGENTS.md` 改动；`components/` 仍仅 `.gitkeep`；合成测试全在 `/tmp/opencode/INFRA-004t-rework/tree`。 |
| E2-10 | 是否存在"静默成功"兼容桩？ | 低 | ❌无：前置校验（unknown component / no pinned commit / missing source / HEAD 祖先）均在分支前，行为不变。 |

#### 防造假核对

- 所有 T1/T2/T3 输出为 `bash selftest.sh 2>&1 | tee .tao/logs/INFRA-004t-rework-selftest.log` 的真实终端输出，日志落盘。
- `compileall` 真实执行，`COMPILE_EXIT=0`，日志 `.tao/logs/INFRA-004t-rework-compileall.log`。
- 未执行 `git commit`；未修改仓库 tracked 文件（除任务文件本身）。

#### 判决

**自主自审通过**：F1 已按最小改动修复，dry-run 零副作用，非 dry-run 与 CLI 无回归；无未修 finding。任务状态置 `待验收`，交主会话 `/complete` 由 reviewer 独立验收。

### 第 2 轮 reviewer 验收

**审查者**：reviewer subagent
**审查时间**：2026-09-12
**审查方法**：独立构造隔离合成上游 + 重跑全部验收命令 + 源码分析

#### 重跑记录

##### 1. compileall
```
$ python3 -m compileall -q scripts 2>&1; echo "EXIT=$?"
EXIT=0
```

##### 2. fetch.py（无 enabled 组件）
```
$ python3 scripts/fetch.py 2>&1; echo "EXIT=$?"
fetch: no components enabled; accept baseline ADRs first
EXIT=0
```

##### 3. apply_series.py（无 enabled 组件）
```
$ python3 scripts/apply_series.py 2>&1; echo "EXIT=$?"
apply-series: no components enabled
EXIT=0
```

##### 4. fetch_refs.py（幂等跳过）
```
$ python3 scripts/fetch_refs.py 2>&1; echo "EXIT=$?"
fetch-refs: dadao-0628 already at 2d270604b778; skipping
fetch-refs: dadao already at f9bde0481668; skipping
EXIT=0
```

##### 5. fetch_refs.py 离线重建（删除 `.dadao/DADAO-0628`，`GIT_ALLOW_PROTOCOL=file`）
```
$ rm -rf .dadao/DADAO-0628
$ GIT_ALLOW_PROTOCOL=file python3 scripts/fetch_refs.py 2>&1; echo "EXIT=$?"
Cloning into '/mnt/tao/DADAO-v5/.dadao/DADAO-0628'...
done.
From /mnt/tao/DADAO-v5/.cache/refs/dadao-0628
 * branch            2d270604b778d609e1a09b4047271b5309005ffc -> FETCH_HEAD
HEAD is now at 2d27060 KL-157a: bypass VFS root-mount wall via minimal built-in initramfs /init
fetch-refs: mirror dadao-0628.git already has 2d270604b778; skipping fetch
fetch-refs: dadao-0628 -> 2d270604b778d609e1a09b4047271b5309005ffc
fetch-refs: dadao already at f9bde0481668; skipping
EXIT=0
rebuilt HEAD=2d270604b778d609e1a09b4047271b5309005ffc
rebuilt origin=/mnt/tao/DADAO-v5/.cache/refs/dadao-0628.git
```

##### 6. manifest_check.py 回归
```
$ python3 scripts/manifest_check.py 2>&1; echo "EXIT=$?"
enabled components: none
references: 2
manifest validation: PASS
EXIT=0
```

##### 7. F1 dry-run 零副作用（reviewer 独立构造隔离合成上游）

**环境**：`/tmp/infra004t-r2/`，synthetic bare repo 3 commits（base + 2 patches），临时 manifest 启用 `foo` 组件。测试结束后已清理。

**T1. dry-run 目录不存在时零副作用**：
```
$ ls components/foo 2>&1 || true
ls: cannot access 'components/foo': No such file or directory
(components/foo does not exist BEFORE)
$ python3 scripts/make_patch.py foo --dry-run 2>&1; echo "exit=$?"
make-patch: would write 0001-first-change.patch
make-patch: would write 0002-second-change.patch
exit=0
$ ls components/foo 2>&1 || echo "PASS: components/foo still absent after dry-run"
ls: cannot access 'components/foo': No such file or directory
PASS: components/foo still absent after dry-run
```

**T2. 非 dry-run 无回归**：
```
$ python3 scripts/make_patch.py foo 2>&1; echo "exit=$?"
make-patch: foo wrote 2 patches to /tmp/infra004t-r2/components/foo/patches
make-patch: series /tmp/infra004t-r2/components/foo/patches/series
exit=0
--- components/foo/patches ---
0001-first-change.patch
0002-second-change.patch
series
--- series ---
0001-first-change.patch
0002-second-change.patch
--- file sizes ---
359 components/foo/patches/0001-first-change.patch
377 components/foo/patches/0002-second-change.patch
 49 components/foo/patches/series
785 total
```

**T3. dry-run 已存在目录时文件不变（sha1 核对）**：
```
=== Snapshot BEFORE dry-run ===
0001: sha1=e518ad8670dd87f93f10a9aa7760923f914d9df9 size=359
0002: sha1=bb370d3661f8d0853301e1e9efd9c39203b906b7 size=377
series: sha1=354b9d12977f34fcf3b5dcc940231e9f382d9877 size=49

$ python3 scripts/make_patch.py foo --dry-run 2>&1; echo "exit=$?"
make-patch: would write 0001-first-change.patch
make-patch: would write 0002-second-change.patch
exit=0

=== Snapshot AFTER dry-run ===
0001: sha1=e518ad8670dd87f93f10a9aa7760923f914d9df9 size=359
0002: sha1=bb370d3661f8d0853301e1e9efd9c39203b906b7 size=377
series: sha1=354b9d12977f34fcf3b5dcc940231e9f382d9877 size=49
PASS: components/foo/patches unchanged (names+sizes+sha1)
```

**真实仓库污染检查**：
```
$ git status --short scripts/
?? scripts/apply_series.py
?? scripts/fetch.py
?? scripts/fetch_refs.py
?? scripts/make_patch.py
$ ls -la components/
total 8
drwxr-xr-x  2 ubuntu ubuntu 4096 Sep 12 02:13 .
drwxr-xr-x 13 ubuntu ubuntu 4096 Sep 12 01:07 ..
-rw-rw-r--  1 ubuntu ubuntu    0 Sep 11 13:43 .gitkeep
```
真实仓库 `components/` 仍仅 `.gitkeep`，无补丁目录被创建。

##### 8. make_patch.py --help 语义核对
```
$ python3 scripts/make_patch.py --help
usage: make_patch.py [-h] [--dry-run] component

Generate a component's ordered patch series from its worktree.

positional arguments:
  component   component name from components.lock.toml

options:
  -h, --help  show this help message and exit
  --dry-run   list the patches that would be generated without writing
              anything
```
`--help` 声明 "without writing anything"，与实现一致（dry-run 用 `tempfile.TemporaryDirectory()` 渲染后只取文件名）。

#### 约束核验

| 约束 | 状态 | 证据 |
|------|------|------|
| F1：`--dry-run` 零副作用 | ✅已修 | T1 目录不存在时不创建；T3 sha1 完全不变；源码 line 95-105 使用 tempfile |
| 不复制 0.4.1 补丁正文 | ✅ | 源码无补丁内容复制 |
| `.cache/` 持久（gitignored） | ✅ | `.gitignore` 已配置 |
| 修改文件仅为新增 | ✅ | `git status --short scripts/` 仅 4 个 `??` |
| mirror + worktree 两层设计 | ✅ | fetch.py / fetch_refs.py 实现正确 |
| 已打补丁重跑不丢补丁 | ✅ | fetch.py ancestor 检测（line 117-132） |
| 脏树拒绝覆盖 | ✅ | fetch.py line 102-106 |
| HEAD 非 base 时报错 | ✅ | apply_series.py line 35-39 |
| 离线重建不联网 | ✅ | 真实 refs 重建 + `GIT_ALLOW_PROTOCOL=file` 成功 |
| 幂等跳过 | ✅ | 真实 refs 幂等 + mirror 已含 commit 时 skip |

#### 源码分析（F1 修复）

`scripts/make_patch.py` F1 修复的三个关键改动：

1. **`import tempfile`**（line 17）：新增标准库导入。

2. **抽出 `format_patch()` 辅助函数**（line 39-47）：封装 `git format-patch --no-signature -o <out_dir> <commit>..HEAD` 调用与文件名解析。逻辑与原内联代码一致，仅将 `out_dir` 参数化。

3. **dry-run 分支使用 tempfile**（line 95-105）：
   - `with tempfile.TemporaryDirectory() as scratch:` 创建临时目录
   - `format_patch(source, commit, Path(scratch))` 将补丁写入临时目录
   - 仅取文件名打印 `would write <name>`
   - `with` 块结束时临时目录自动删除
   - **不触碰 `out_dir`**（`components/<name>/patches/`）

4. **`out_dir.mkdir` 移入非 dry-run 分支**（line 107）：原代码在分支前无条件执行 `out_dir.mkdir(...)`，现在仅在非 dry-run 路径执行。

修复正确：dry-run 的唯一副作用是临时目录中的 `git format-patch` 输出，退出即清理；真实 `out_dir` 完全不被触碰。

#### 与工程师自审的差异

工程师自审结论全部通过，与 reviewer 独立重跑结果一致。工程师的自测日志（`.tao/logs/INFRA-004t-rework-selftest.log`）内容与 reviewer 独立构造的测试结果吻合。

#### 判决

**Accepted**

F1 返工修复正确：`--dry-run` 零副作用（目录不存在时不创建、已存在时 sha1 不变），非 dry-run 无回归，CLI/`--help` 语义与实现一致。全部 6 条验收标准通过，约束无违反。4 个脚本语法正确、逻辑完整。`manifest_check.py` 回归通过。返工未引入新问题。

### 交叉复核（architect）F1

**复核者**：architect
**时间**：2026-09-12
**结论**：**确认 Accepted**。F1 已真正修复，返工未引入回归，reviewer 第 2 轮判决无过严/过松。

**独立核对（自建隔离合成上游 `/tmp/opencode/arch-recheck`，未触碰仓库 tracked 文件）**：

- **F1 零副作用（复现 reviewer T1/T2/T3）**：
  - T1 `components/foo` 不存在时 `--dry-run`：打印 `would write 0001/0002`，exit=0，目录仍未创建（`find` 无 stray `.patch`）。
  - T2 非 dry-run：生成 `0001-first-change.patch`/`0002-second-change.patch` + `series`，文件名与顺序与 dry-run 打印一致。
  - T3 已存在目录再 dry-run：`sha1sum` before/after `diff` 为空，PASS。
- **reviewer 遗漏边界补测（E1–E4，均通过）**：
  - E1 `components/foo` 存在但 `patches/` 缺失：dry-run 不创建 `patches/`（确认 `out_dir.mkdir` 确已移入非 dry-run 分支）。
  - E2 `HEAD == pin`（无顶部提交）：dry-run/非 dry-run 均打印 `has no commits on top` 且不落盘，exit=0。
  - E3 `HEAD` 不派生自 pin：exit=1 报错，且发生在任何写操作之前。
  - E4 多次 dry-run 后 source worktree `git status --porcelain` 为空（git 本身无残留副作用）。
- **非 dry-run / CLI 无回归**：`format_patch()` 与旧内联逻辑逐字等价（同 `--no-signature -o <out_dir> <commit>..HEAD`），series 写入与 stdout 文案一致；`--help` 文案未变。
- **真实仓库无污染**：`components/` 仅 `.gitkeep`；`.cache/` 仅 `refs/`（无测试遗留 `foo.git`）；`.work/source/` 为空；`git status` 仅 4 个新增脚本 `??`；`__pycache__` 已被 `.gitignore` 忽略。
- **日志真实性**：`.tao/logs/INFRA-004t-rework-selftest.log`（1198B）与 `-rework-compileall.log`（`EXIT=0`）内容与独立复现一致；`python3 -m compileall -q scripts` 现跑 `EXIT=0`。

**残留（非阻塞，可审计性）**：N1 未完全闭环——reviewer 第 2 轮的 F1 合成自测输出仅内联于任务文件，未落盘为独立日志（`.tao/logs/` 下无 R2 selftest 日志）。因工程师 `rework-selftest.log` 已落盘且与本轮独立复现吻合，不影响判决；建议后续 reviewer 自测一律落盘。

**状态提示**：任务文件仍为 `**状态**：待验收`；本交叉复核确认后，由主会话置 `已验证`。
