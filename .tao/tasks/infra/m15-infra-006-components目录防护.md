# m15-infra-006: `components/` 目录防护（`.manifests.toml` 第二波）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-005`（guard 脚本与注册表机制已就位）
**可并行分片**：否
**预估**：1–1.5 h
**档位**：小改
**状态**：已验证

## 背景（用户 2026-11-18）

第一波已覆盖 `spec/`、`.tao/`、`.tao/knowledge`。第二波加 `components/`：**新增目录须经用户同意**（机械上 = 清单 diff 即审批点），每个目录的 `owner` 为对应模块，**唯一例外是 `busybox`**。

## 目标

1. 新建 `components/.manifests.toml`：
   - `subdirs` = 现场 `ls -d components/*/` 的 8 个（`busybox`、`chipyard`、`gem5`、`linux`、`llvm-project`、`musl`、`picolibc`、`qemu`），以现场为准；
   - `recursive = false`（子目录内部不受本清单约束，由各组件自己的 `patches/` 结构管）；
   - `files` = 现场直接子文件（若有；无则空 map）。
2. 在 `manifests/dir-guard-roots.toml` 的 `roots` 加 `"components"`。
3. `owner` 归属（写进清单条目，声明性）：
   - `llvm-project` → `llvm`；`qemu` → `qemu`；`gem5` → `gem5`；`linux` → `linux`；`musl` → `llvm`；`picolibc` → `testcases`；`chipyard` → `chipyard`；**`busybox` → `linux`（用户指定例外）**。
4. `components/README.md` 若存在则补一行说明「busybox 由 linux 模块维护」；不存在则不新建（保持现状）。
5. `AGENTS.md` 加一条：**`components/` 新增子目录须经用户同意**（机械判据 = `components/.manifests.toml` 的 `subdirs` 变更）。

## 验收（逐条贴真实 rc）

1. `make check-manifests-guard` rc=0；`grep -c "^\[\[component\]\]\|^name" manifests/components.lock.toml` 与清单无关（lock 是独立数据，不要求一一对应；只核 `components/` 目录）。
2. **新建 `components/zztest/` ⇒ guard rc≠0「多出子目录」**；`cp`/`rmdir` 还原 ⇒ rc=0。
3. **删 `components/busybox` ⇒ rc≠0「缺失子目录」**（用临时树或 `mv` + 还原，勿真删）。
4. 删 `components/.manifests.toml` ⇒ rc≠0（注册表机制生效）。
5. 一并回归：`check-patch-tree`、`manifest-check`、`check-component-changelog`、`check-dirs` 仍 rc=0（新增清单不得干扰它们）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；不改版本号。
2. 只动：`components/.manifests.toml`（新）、`manifests/dir-guard-roots.toml`（一行）、`AGENTS.md`（一条）、`components/README.md`（若存在，一行）、本任务书。
3. **不碰任何组件源/补丁/`series`**（`components/linux` 有在途任务）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

逐行核对：清单 `subdirs` 与现场 `ls -d components/*/` 一致（8 项，现场派生比对）；`files` 仅 `.gitkeep`（A2 双向要求登记直接子文件，漏登会判「多出文件」）；`recursive = false` 与任务书一致（组件内部由各自 `patches/` 结构管）；注册表 `roots` 加 `components` 后 guard 受检目录 3→4，未触碰 `spec/.tao` 三份清单；硬约束核对：未提交 git、未改主工作树、未改版本号、`components/*/` 内 `git status -uall` 仅 1 行（新清单，子目录零改动）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| schema v1 的 `subdirs` 只收字符串、`owner` 仅顶层/`files` 级 ⇒ 每子目录 owner 无法机械承载 | ⏸延后 | 按「声明性」写入条目旁注（`"busybox", # owner = linux`），未改 guard 脚本（不在允许文件内）；证据脚本逐条断言 8 项 owner 非空 + busybox→linux | 证据脚本「每个 subdir 条目都有 owner 声明 期望=0 实际=0」「busybox owner 期望=linux 实际=linux」 |
| 旁注 owner 无门控保护，可能被静默改错 | ✅已修（提升为证据断言） | 证据脚本 §3 断言 owner 存在且 busybox=linux | 注入：改 `busybox` 旁注为 `qemu` ⇒ `[FAIL] busybox owner 期望=linux 实际=qemu`、rc=1；`cp`+md5 还原 `07784b0e…` 前后一致 ⇒ 重跑 18/18 PASS |
| 清单新增后可能与 `check-dirs`/`check-component-changelog`/`manifest-check`/`check-patch-tree` 冲突 | ✅已验证 | 无额外改动 | 四者 rc=0（证据脚本 §7） |

### 第 2 轮 engineer 自审（返工：`[subdir_owners]` 数据化）

返工依据：用户裁定「清单只写数据、不写过程注记」⇒ 旁注 owner 不合格。逐行核对：`ALLOWED_TOP` 加 `subdir_owners`、`load_manifest` 增表/非空字符串/悬空 key 三类校验、`audit` 仅顶层打印 owner（递归层不打印，避免误导）、`BASE_A` 加合法映射使基线成为正例、判据只增不减（未放宽既有任何一条）、三份旧清单不填仍绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| owner 只能写注记，非数据且门控不校验 | ✅已修 | schema 加可选 `[subdir_owners]`（`子目录名 = 模块`）；`components/.manifests.toml` 8 条数据化并删注记；`docs/Process-06` 补 schema 说明 | guard 打印 8 条 `owner components/<dir> = <模块>`；证据 §3 逐条比对任务书映射 + `grep -c '# owner'` = 0 |
| 声明性映射悬空（拼错 / 子目录已删）会静默失效 | ✅已修 | A8：key 不在 `subdirs` ⇒ FAIL；值须非空字符串；`--self-test` +2 例 | 清单注入 `ghost = "x"` ⇒ rc=2「悬空 owner」；self-test 15/15（含两新例） |
| 扩字段可能破坏三份既有清单 | ✅已验证 | 字段可选，三份未改 | 证据 §4：三份 `subdir_owners in doc == False`，guard 仍 rc=0 |
| 证据脚本原 §3 依赖注记解析，返工后失效 | ✅已修 | owner 断言改从 `[subdir_owners]` 读数据（`name=owner` 行比对） | 32/32 PASS；改 `busybox = "qemu"` ⇒ 2 条 FAIL、rc=1、还原后 32/32 |

### 第 1 轮 reviewer 验收（小改；≥3 路注入含 1 路未列）

**自证**：`git rev-parse --show-toplevel` = `/tmp/opencode/m15-infra-006/wt`、分支 `m15-infra-006`、HEAD `6d62e114`（我未新增提交）；`git status --porcelain -uall` 空；主工作树 `master` 且 status 0 行（未触碰）。
**范围**：`git diff --name-status 8400e307..HEAD` = **6 文件**（任务书、`AGENTS.md`、`components/.manifests.toml`(A)、`docs/Process-06`、`manifests/dir-guard-roots.toml`、`tools/infra/check_manifests_guard.py`）；派单提示写「5 文件」实为 6（漏计 `dir-guard-roots.toml`，系任务书目标 2 所需）⇒ **非越界**。`git diff -- spec/ tests/ contracts/` = **0 文件**；diff 内无版本号/`-rc` 变更（`schema = 1` 保持）。
**清单正确性**：`subdirs` 8 项与现场 `ls -d components/*/` **逐项相等**（busybox/chipyard/gem5/linux/llvm-project/musl/picolibc/qemu）；`grep -c '#' components/.manifests.toml` = **0**（无注记）；`[subdir_owners]` 8 条与任务书映射逐条相等（含 `busybox = "linux"`）；`files` 仅 `.gitkeep`。
**重跑（我的真实输出/rc）**：
- `make check-manifests-guard` ⇒ **rc=0**，`清单 4；受检目录 4；文件 32；sha256 22`，打印 8 行 `owner components/<dir> = <模块>`。
- `python3 tools/infra/check_manifests_guard.py --self-test` ⇒ **rc=0、15/15**（含「悬空 key」「值非字符串」两例 + 基线正例）。
- 证据脚本 `./.work/evidence/m15-infra-006/run.sh` ⇒ **rc=0、32/32 PASS**（4 路注入+还原、三份旧清单 `subdir_owners=False`、self-test 计数现场派生非写死）。
- **四路注入（我自跑，`cp`/`mv`+md5 还原）**：① `mkdir components/zztest` ⇒ **rc=2**「多出子目录 zztest」、rmdir ⇒ rc=0；② `mv components/busybox` ⇒ **rc=2**「缺失子目录 busybox」、mv 回 md5 `49c7aabfc1be70ae553034a417468ddf` 前后一致 ⇒ rc=0；③ `rm components/.manifests.toml` ⇒ **rc=2**「缺少清单」、cp 回 md5 `b712c8d47bca11d6a4c6bfa67a0e5c5e` ⇒ rc=0；④ **未列**：`[subdir_owners]` 塞 `ghost = "x"` ⇒ **rc=2**「悬空 owner（不在 subdirs 中）」、cp 回同 md5 ⇒ rc=0。
- **独立反例（改被测产物后重跑同一脚本）**：注入 `ghost` ⇒ `run.sh` **rc=1**、`合计 32 项检查，失败 7 项`（基线/还原A/B/C/D、owner 映射全报 FAIL）；`cp` 还原 md5 一致 ⇒ `make check-manifests-guard` **rc=0 回绿** ⇒ 脚本可达 FAIL、非恒真。
- **向后兼容（关键回归）**：`spec/.manifests.toml`、`.tao/.manifests.toml`、`.tao/knowledge/.manifests.toml` 现读 `subdir_owners=False`、`git diff` 0 行，guard 仍 **rc=0**。
- **回归 7 项（我自跑，非转述）**：`manifest-check` / `check-patch-tree` / `check-component-changelog` / `check-dirs` / `check-tasks` / `check-knowledge-refs` / `check-no-residue` ⇒ 全 **rc=0**。
- **组件源零改动**：`git status --porcelain -uall -- components/` 空；8 个子目录改动计数 **0**；全树 status 空。
**硬约束核验**：① 独立 worktree、未改主工作树、我未提交 git ✓；② 只动上述 6 文件（均在任务书/返工裁定范围内）✓；③ 未碰组件源/补丁/`series` ✓；④ 还原全程 `cp`/`mv`+md5，禁 checkout/restore/stash/show ✓；⑤ 未改版本号 ✓；⑥ 完成区 8 行 ≤30、`**状态**：待验收` ✓。
**记录（不阻断，交 architect 收尾改）**：① 派单提示「5 文件」与实际 6 文件不符（漏计 `dir-guard-roots.toml`）；② `check_manifests_guard.py` docstring 称 `[subdir_owners]`「门控只打印，不判红」，与 A8「悬空 ⇒ FAIL」字面矛盾（后半句已澄清），建议改为「值只打印；键悬空判红」；③ `check-patch-tree` 输出 `libc-test: source worktree absent; skipping …⑦⑧⑨`（rc=0）系 `.work/source/libc-test` 缺失的既有环境跳过，与本任务无关。
**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过，4 路注入（含 1 路未列）均判红并回绿，硬约束无违反；3 条记录均为文档级小错，按规则不阻断。

## 完成区

**测试结果**：一键证据脚本（运行期，未归档）32/32 PASS、rc=0（4 路注入+还原、self-test 15/15、现场派生集合与 owner 数据比对）；脚本自身断言可达 FAIL 实测：把 `[subdir_owners] busybox` 改成 `qemu` ⇒ 2 条 FAIL、rc=1 ⇒ `cp`+md5 还原后 32/32。
**验收逐条（真实 rc）**：① `make check-manifests-guard` rc=0（清单 4；受检目录 4；文件 32；22 sha256）且打印 8 条 `owner components/<dir> = <模块>`；`--self-test` rc=0、15/15（新增「悬空 key」「值非字符串」两例，基线含合法映射仍绿）② 清单塞 `ghost = "x"` ⇒ rc=2 命中「悬空 owner」⇒ `cp` 回（md5 `b712c8d4…` 一致）⇒ rc=0 ③ 新建 `components/zztest/` ⇒ rc=2「多出子目录 zztest」⇒ `rmdir` ⇒ rc=0 ④ `mv components/busybox` 走 ⇒ rc=2「缺失子目录 busybox」⇒ `mv` 回（目录 md5 清单 `49c7aabf…` 一致）⇒ rc=0 ⑤ 删清单 ⇒ rc=2「缺少清单」⇒ `cp` 回 ⇒ rc=0 ⑥ `spec/`、`.tao/`、`.tao/knowledge/` 三份清单未加 `subdir_owners`（现场读出 False）且仍 rc=0 ⑦ 回归 `manifest-check`/`check-patch-tree`/`check-component-changelog`/`check-dirs` rc=0（另 `check-no-residue`/`check-knowledge-refs`/`check-tasks` rc=0）。
**修改文件**：`tools/infra/check_manifests_guard.py`（可选 `[subdir_owners]`：A8 悬空 key/非字符串值判红、打印 owner、self-test +2 例）、`components/.manifests.toml`（新：8 subdirs + `[subdir_owners]` 8 条 + `files.".gitkeep"`，无注记）、`manifests/dir-guard-roots.toml`（roots 加 `components`）、`docs/Process-06`（schema 说明 +1 句）、`AGENTS.md`（+1 条）、本任务书。`components/README.md` 不存在 ⇒ 不新建。
**schema 兼容性**：`[subdir_owners]` **可选**，三份旧清单不填即合法（自检基线覆盖正例）；未知键仍按 A1 判红，未放宽任何既有判据（只增不减）。
**新发现/坑**：① `components/` 直接子文件含 `.gitkeep`，A2 双向集合下必须登记，漏登即「多出文件」；② 声明性字段必须落**数据**并给悬空 key 判红，否则拼错/子目录删除后静默失效（本轮返工原因）；③ `check-temp-dirs` rc=2 系既有其它任务陈旧临时目录（`m14-qemu-001` 等 9 个，非本任务），按规则不代删。
**遗留问题**：无（`check-temp-dirs` 红与本任务无关，见坑③）。
