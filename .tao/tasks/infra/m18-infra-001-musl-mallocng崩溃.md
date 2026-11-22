# m18-infra-001: musl mallocng 堆一致性崩溃（ISS-497 / ISS-499）

**模块**：infra
**项目里程碑**：M18
**依赖**：`m18-linux-001`/`002`（K6 启动与回归）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（musl 堆/free 路径或 ash 交互）
**状态**：已验证

## 背景（`m18-linux-004` 定位）

- `ISS-497`：单次启动约 17 条命令后 shell 被杀；内核记 `die-no-vma va=0x0`。定位到 **musl mallocng 内部一致性断言**（`glue.h::assert → a_crash()` 写 NULL，落在 `alloc_slot`/`free`）。
- `ISS-499`：guest `grep` 每次 SIGSEGV，落在同一断言 ⇒ **两个 issue 同一根因**。
- 触发面是**堆布局**：去掉 ash 的 `setvar0("_", lastarg)` 即消失（3/3）；同命令序列经脚本文件/管道喂子 shell 不崩，控制台逐行喂则崩；行缓冲/去回显/非 tty/屏蔽 tick 都不消除。
- 内核侧 `cp` 级探针全绿（fork+exec 12 轮堆校验、64 个 mmap 区间别名+churn、console 逐字节读+堆校验）⇒ 初步判**非内核改写用户内存**。

## 目标

1. **坐实归属**（先做）：最小复现（ash `_` 赋值 + 堆布局）逐层缩小到 musl `mallocng` 的分配/释放路径；给出「内核未改写」的独立证据（或推翻，转回 linux）。
2. **修复**：
   - 若 musl 缺陷 ⇒ 修 `components/musl`（补丁集，`docs/Process-01` 重导）；
   - 若是 ash 触发了 musl 未定义的用法 ⇒ 在 busybox 侧做最小适配并说明为何符合 musl ABI；
   - **不得**只删 `_` 赋值或改堆参数来掩盖。
3. 修后 `ISS-497`/`ISS-499` 填 `resolved_by`（`closed_in: M18`）。

## 验收（真实 rc）

1. **复现与归属**：最小用例（脚本化 stdin）在修前红、修后绿；给出 musl 侧断言的调用栈（`gdb`/`llvm-symbolizer` 或日志）。
2. **K6 回归**：`m18-linux-002` 的 17 条命令**单次启动**跑通（不再拆段）；`m18-linux-001` 28/28；`m18-linux-004` 的 200/200 启动 + 27 条长脚本仍绿。
3. **grep**：guest `grep` 正常（有匹配/无匹配 `-q` 各一例），rc 不再是 139。
4. **可达 FAIL ≥2 路**：回退 musl 修复 ⇒ 复现红；回退 busybox 适配（若走该路）⇒ grep/长脚本红。
5. 门控：`check-musl-freshness`、`check-patch-tree` musl/busybox 段 0 问题、`check-component-changelog`、`check-config-pins`、`check-linux-k5` 280/280、K0 146/146。
6. 完成区 ≤30 行；状态 → `待验收`。

## 约束

独立 worktree；不提交 git；只动 `components/musl/**`、`components/busybox/**`、必要证据脚本与任务书；不改 `spec/`/契约；术语「寄存器组」；组件补丁经 `make_patch.py` 重导。

## 完成区

**范围**：`ISS-497`（K6 长脚本 `die-no-vma`）与 `ISS-499`（guest `grep` rc=139）**同一根因**：musl `mallocng` 的 `a_or(&meta->freed_mask, self)` 未生效（4 字节 `lr.t`/`sc.t` 条件写在参考机器上静默丢写，指令仍报成功），组状态与掩码失配 ⇒ `malloc.c: try_avail` 的 `assert(mask)` → `glue.h::a_crash()` 写 NULL。**非内核**（`qemu-dadao` linux-user、无 DADAO 内核即可 100% 复现）、**非 busybox**（sh/grep 只是受害者）；平台侧窄 `sc` 丢写另登记 `ISS-500`（qemu）。
**测试结果**：`run.sh` 默认 **47/47 PASS、rc=0**；`run.sh --inject` **31/31 PASS、rc=0**（四道注入均「注入红 → 还原 → 回绿」：窄 CAS、丢邻居半字、恒真门反例、guest 死循环超时）。
**修改文件**：`components/musl/patches/arch/dadao/atomic_arch.h.patch`（`make_patch.py musl`：1 written / 25 unchanged）、`components/musl/changelog.md`（M18 追加 1 条）、`.tao/knowledge/issues.yaml`（497/499 关闭 + 新增 `ISS-500`）、本任务书；运行期证据目录内的 `run.sh`（`README.md`、`probe/`、`inject/`、`logs/` 同目录）。未动 busybox、未改版本号、未提交 git。
**验收结果**（真实 rc）：
- **复现与归属**：`probe/narrow_cas_probe.c`（自带窄 CAS，不依赖 musl 版本）实测 `A(load+narrow) freed=0x0 sc.fail=00`（报成功但写丢失）vs `B(noload+narrow) freed=0x2`；`word_cas_probe.c` 同场景 `freed=0x2 avail=0x7f80 sc.fail=00`。修前 `grep` rc=139（`a_crash`）；注入窄 CAS + 真断言时落盘 `Assertion failed: mask (src/malloc/mallocng/malloc.c: try_avail: 164)`（`logs/assert-narrow.log`），与 `logs/mallocng-trace.log` 的 `free → nontrivial_free → a_or(freed_mask 不生效) → try_avail` 状态序列共同构成 musl 侧调用路径。
- **修复**：`a_cas(int)` 改为「含该 `int` 的 8 字节字 CAS」——`a_cas_word()` = `lr.o.an`/`sc.o.ar` + 就地合并 32 位半字；邻居半字变化只会使 CAS 失败并重读（不丢更新）；大端下半字选择 = 字偏移 0 取高半（移位 32）/偏移 4 取低半（移位 0）；`a_cas_p` 不变。
- **grep**：有匹配 `rc=0` 且输出 `hello-k6`、`-q` 有/无匹配 `rc=0/1`（修前 139）。
- **K6**：`long-script.txt` 27 条命令**单次启动**跑通（27 个提示符、`K6-REGRESSION-DONE`、无 `die-no-vma`/panic、qemu rc=0）；`k6-commands.txt`（`m18-linux-002` 形状，含原崩溃点 `ps`）一次跑通；**200/200** 启动进用户态、`die_no_vma=0`；`m18-linux-001` 证据在本 worktree 重跑 **28/28**。
- **门控**：`check-musl-freshness` PASS；`check-patch-tree` 的 **musl/busybox 段 0 问题**；`check-component-changelog` PASS；`check-config-pins` PASS（85/85）；`check-linux-k5` **280/280**；`check-linux-k0` **143/146** —— 3 条失败全为 `K12 apply-series --component linux`（本 worktree 的 linux **源**是未合入的 `m18-linux-004` 树，与其补丁集不匹配；`check-patch-tree` 的 8 条问题同为该 4 个文件），合入 004 后即 146/146 且 patch-tree 全绿；本任务未触碰 linux。
**新发现/坑**：① 归属先切「用户态库 / 内核」：`qemu-dadao` 能复现即与内核无关（比内核探针快一个数量级）；② 窄 `lr/sc` 的丢写是**指令级**的（报成功、内存不变），任何「删 `_` 赋值 / 调堆参数」都只是改布局；③ 字 CAS 后同字邻居并发变化只会多一次重试（不丢更新），但同字两个 `int` 会互相干扰（已写进头注释）；④ 共享 `.dadao` 安装根会让 `check-musl-freshness` 串味——本 worktree 用「私有无敌对 sysroot + 符号链接工具链/测试集」隔离；⑤ `make build-musl`（静态）在源变更后会 `make clean`，把 `lib/libc.so`/`libc_pic.a` 清掉 ⇒ 之后必须先 `make build-musl-shared` 才能过 `check-musl-freshness`。
**遗留问题**：`ISS-500`（qemu 窄 `sc` 丢写）仍开放，交 qemu 模块；本任务只把它降级为「不影响 musl 正确性」。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `a_cas` 的字 CAS 会不会在**同字邻居**被并发改时丢更新 | ✅已修（设计保证）+ 证据 | 循环用「整字 CAS 比较」而非「无条件写」 | `casstress` 1000 轮 × 4 组（邻居 0x7f80/0x8000/0）全对；注入「丢邻居半字」⇒ `STRESS-BAD`（`--inject` inj2） |
| F2 大端下半字选择写反 ⇒ 会改到邻居而不是目标 | ✅已修 | `shift = (p & 4) ? 0 : 32` | `word_cas_probe`：`freed=0x2 avail=0x7f80`（邻居保持） |
| F3 8 字节访问可能跨 64 KiB 页边界 | ❌不修（不存在） | — | 字地址 `p & ~7` 恒 8 对齐，64 KiB 页是 8 的整数倍 ⇒ 8 字节恒在页内；`a_cas_p` 原本就是 `.o` |
| F4 证据脚本里 `casstress.elf` 只在默认路径编译 ⇒ 注入不可见（首轮 `--inject` 的 inj2 假绿） | ✅已修 | 抽出 `build_stress()`，两处注入都重建 | 首轮 `cas-stress-rc-inj2: still green` → 修后 `red as injected (rc=1)` |
| F5 `check-patch-tree`/`check-linux-k0` 的 linux 段红是本 worktree 借用了未合入的 004 源树 | ✅已披露并做成可复核断言 | 断言「musl/busybox 段 0 问题」+「问题行只能是那 4 个 004 文件」+「K0 失败只能是 `K12 `」 | `run.sh` 默认跑 3 条 PASS；K0 `143/146` 的 3 条失败全为 `K12 apply-series` |
| F6 `make build-musl` 在源变更后清掉 `lib/libc.so` ⇒ `check-musl-freshness` 红 | ✅已修 | `build_guest` 改走 `make build-musl-shared`（同时产出静态+共享+pic） | `gate-check-musl-freshness` PASS |

### 第 1 轮 reviewer 验收

**重跑记录**（全部本人执行；命令在仓库根、相对路径）
- **根因探针独立重建并运行**（linux-user `qemu-dadao`，**无 DADAO 内核**）：`narrow_cas_probe` → `A(load+narrow) freed=0x00000000 sc.fail=00` / `B(noload+narrow) freed=0x00000002`；`word_cas_probe` → `A/B freed=0x00000002 avail=0x00007f80`。窄 CAS 丢写、字 CAS 正常，**不依赖内核**，与完成区一致。
- 运行期证据目录内的 `run.sh`：`RESULT: PASS checks=43 failed=0`、`RC=0`（3m7s）。`run.sh --inject`：`RESULT: PASS checks=22 failed=0`、`RC=0`（inj1 `grep` 红 rc=134 + `Assertion failed: mask (src/malloc/mallocng/malloc.c: try_avail`，inj2 `STRESS-BAD` 红，各自 `cp`+md5 还原后回绿）。
- **我自己的独立反例注入**（与 engineer 两道不同：反转 `a_cas` 的半字选择）：`run.sh` → 4 条 `[FAIL] grep-*-rc-accept: want=… got=139`（原 `ISS-499` 症状复现）；`cp` 备份还原 → md5 `e3302868d24a93609e1e4a20b6859c34` 与注入前一致、`git status` 干净、无 `.preinject` 残留 → 重跑 `run.sh` → `PASS checks=43 failed=0`、`RC=0`。
- **门控独立跑**：`check-musl-freshness` PASS；`check-patch-tree` **musl/busybox 段 0 问题**（8 条问题全为 `linux:` 的 4 个 004 文件，带组件前缀过滤后 = 0）；`check-component-changelog` PASS；`check-config-pins` 85/85；`check-linux-k5` **280/280**（FAIL 行 0）；`check-linux-k0` 143/146（3 条 `K12 apply-series --component linux`，004 源树，按派单豁免）；`check_issues` rc=0（497/499 closed + `resolved_by`）。
- **K6 实测**：长脚本 27 提示符 + `K6-REGRESSION-DONE`、`die-no-vma` 0；`k6-commands` 20 提示符含 `ps: can't open '/proc'`；`entered_user_mode=200 die_no_vma=0`；`m18-linux-001 checks=28 failed=0`。

**修复正确性**：`a_cas` 改「含该 int 的 8 字节字 CAS」——偏移 0 → shift 32 / 偏移 4 → shift 0（大端取法正确）；邻居半字变化只使 `a_cas_word` 返回 ≠w 并重读（不丢更新）；`a_cas_p`、`a_barrier` 与修前逐字节相同；mallocng 实际只用 `a_cas`/`a_or`，后者由 `atomic.h` 泛型经 `a_cas` 派生 ⇒ 覆盖全部路径。

**范围**：`git diff fe14a9f7..HEAD` 恰 4 文件（补丁/changelog/issues/任务书），linux/busybox 0 改动；4 文件 md5 与审查前逐个一致；HEAD `2c6903dd`（我未提交 git）。

**判决：Needs Revision**（2 条阻断 + 1 条附带）
1. `make check-knowledge-refs` **rc=2**：`[ISS-352] 具体 .work/** 引用不可复现 → 任务书:44`。完成区「修改文件」段写了运行期证据目录的**具体路径**，违反「任务书不写运行期路径」与 `.work/**` 引用判据；新登记 issue 的 title 里同样有 probe 的具体路径（master 版已改成本地化措辞）。改法：两处改「运行期证据目录内的 `run.sh` / `probe`」措辞后重跑该门控至 rc=0。
2. `run.sh` 的 `gate-patch-tree-problems-are-only-the-004-linux-ones` 是**恒真断言**：其 pattern `check-patch-tree: assertion` 在 `check_patch_tree.py` 输出格式（`check-patch-tree: <组件>: assertion …`）下恒匹配 **0 行** ⇒ `other` 恒 0 ⇒ 恒 PASS，违反 AGENTS.md §4「验证脚本必须能失败」。改法：pattern 补组件段（如 `check-patch-tree: [a-z-]+: assertion`）；修后当前树仍应 PASS（我实测带前缀过滤 = 0 行）。
3. （附带，不阻断）`run.sh` 对 `$GUEST`（grep/stress/probe）**无 timeout**（仅 `boot` 有 `timeout 180`）：我的注入使 `casstress` 死循环、脚本挂死 8 分钟而非判 FAIL。建议给 guest 调用统一加 timeout。

### 第 2 轮 engineer 自审（回应第 1 轮 reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 `check-knowledge-refs` rc=2（任务书:44 写了运行期证据的具体路径；`ISS-500` title 同） | ✅已修 | 完成区改「运行期证据目录内的 `run.sh`（`README.md`、`probe/`、`inject/`、`logs/` 同目录）」；`ISS-500` title 改「运行期证据目录内 `probe/narrow_cas_probe.c`」 | `make check-knowledge-refs` → `结果: PASS (0 具体 .work/** 引用…)`、**rc=0** |
| R2 恒真断言：`check-patch-tree: assertion` 在真实格式 `check-patch-tree: <组件>: assertion …` 下恒匹配 0 行 | ✅已修 | pattern 补组件段 `check-patch-tree: [a-z-]+: assertion`，抽成 `patch_tree_assertion_lines()` / `patch_tree_other_problems()`；补**非空判据**（`gate-patch-tree-assertion-lines-seen >= 1`、`musl: 26 patch(es)`/`busybox: 3 patch(es)` 段已检）与 `gate-check-patch-tree-rc-explained`（rc 必须被允许行数与 `<n> problem(s)` 完全解释） | 默认跑：`assertion-lines-seen: 8`、`problems-are-only-the-004-linux-ones: 8`、`rc-explained: rc=2 problems=8 allowlisted=8`；`--inject`：造 `check-patch-tree: qemu: assertion ⑥: …` ⇒ `red as injected (rc=1)`，再造非允许 mark 的 linux 行 ⇒ `red as injected (rc=1)`，删掉后 `control-green-again: 0` |
| R3 `$GUEST`（grep/stress/probe）无 timeout，guest 死循环会把脚本挂死 | ✅已修 | 新增 `GUEST_TIMEOUT=${GUEST_TIMEOUT:-180}` + `guest_run()`（`timeout "$GUEST_TIMEOUT" qemu-dadao …`），全部 guest 调用改走它（与 `boot` 的 `timeout 180` 一致） | `--inject` 用 `inject/hang.c`（死循环）：`guest-hang-times-out: red as injected (rc=124)`、`guest-hang-bounded: 10s (<= 180s)`；同一 10s 上限下 grep 控制组仍 `rc=0` + 输出 `hello-k6` |

### 第 2 轮 reviewer 复核（窄）
1. **`make check-knowledge-refs` rc=0**（`结果: PASS (0 具体 .work/** 引用; 0 悬空…)`）：完成区改「运行期证据目录内的 `run.sh`」、`ISS-500` title 改「运行期证据目录内 `probe/narrow_cas_probe.c`」，两处具体运行期路径计数 0（我 grep 复核均无匹配）。
2. **恒真门已消除（我独立验，用 `run.sh` 内原函数非重写）**：真实日志 `assertion_lines=8 other=0`；追加 `check-patch-tree: qemu: assertion ⑥: …` ⇒ `other=1`（`problems-are-only…` 与 `rc-explained` 双门皆转 FAIL）；再加非允许 linux 行 ⇒ `other=2`；删掉 ⇒ `other=0`。默认跑非空判据全绿：`assertion-lines-seen: 8`、`musl: 26 patch(es)`、`busybox: 3 patch(es)`、`rc-explained: rc=2 problems=8 allowlisted=8`。
3. **guest timeout 已覆盖**：`$GUEST` 仅剩 `guest_run()` 内一处 `timeout "$GUEST_TIMEOUT"`，grep/stress/probe 全走它；我独立编死循环 guest ⇒ `timeout 5` **rc=124、5s 返回、不挂死**；`--inject` injection 4 ⇒ `guest-hang-times-out: red as injected (rc=124)`、`guest-hang-bounded: 10s (<=180s)`、控制组 grep 仍 `rc=0`+`hello-k6`。
4. **重跑**：`run.sh` **47/47 PASS、rc=0**；`run.sh --inject` **31/31 PASS、rc=0**（inj1 rc=134 + `try_avail` 断言、inj2 rc=1、inj3/3b 红、inj4 rc=124，均 `cp`+md5 还原回绿）。
5. **musl 未动**：补丁 `a3e8c0fddba75d8167c0ad91cb7aeb57`、changelog `9d9aebc013b38f0b61ea9d0715011044`，与第 1 轮审查前逐字节相同；musl 源树 `atomic_arch.h`/`glue.h` 还原（`e3302868…`/`f556544e…`）、源树 status 0 行。
6. **范围**：`git status` 仅 `issues.yaml` + 本任务书（本轮 R1–R3 改动 + 本记录），linux/busybox/musl 0 改动；完成区 15 行 ≤30；我未提交 git。
**判决：Accepted**
