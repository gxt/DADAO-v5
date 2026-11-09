# TESTCASES-100t: libc-test malloc-brk-fail 64K 页可移植性修正

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-099t`（已验证；根因 = musl dynamic 启动堆/64K 页 LOAD 空洞）、`TESTCASES-076t`（夜跑）、`TESTCASES-083t`（libc-test 驱动）
**状态**：已验证

## 执行环境
本地；改 libc-test 语料 + 组件补丁策略，不改 spec/QEMU/gem5。

## 背景

`regression/malloc-brk-fail` dynamic 在 DADAO 64K 页上失败：

- libc.so LOAD 段之间有 54880 B 的 64K 对齐空洞
- musl dynamic loader `reclaim_gaps` 把空洞捐给 mallocng
- `malloc(10000)` 直接落在该空洞，无 brk/mmap 系统调用
- 测试假设“填满 VA + RLIMIT_DATA=0 后 malloc 必失败”不成立

4K 页 ISA 的空洞 <4K，`malloc(10000)` 放不进去，测试通过；64K 页系统会失败。属测试可移植性问题。

## 目标（C 方案）

在 libc-test 语料侧修正，使测试对 64K 页也成立：

1. 把 `libc-test` 从 `patchless = true` 转为受补丁组件：
   - `manifests/components.lock.toml`：`patchless = false`、`patch_dir`、`patch_series`、role 注记
   - `components/libc-test/series`、`components/libc-test/patches/src/regression/malloc-brk-fail.c.patch`
2. 补丁在测试开始、`t_vmfill` 之前**消耗 dynamic loader 捐赠的启动堆**：
   - 申请并保留若干块，确保 64K 空洞被占用（例如先 `malloc(50000)`，再 `malloc(10000)`；按 64K 页/4K 页都成立）
   - 不改变测试断言、magic、退出码、`t_vmfill`/`t_setrlim` 逻辑
   - 注释写明“64K 页 dynamic loader gap”原因
3. 源树 base+1 干净；补丁由 `make apply-series` 应用；`check-source-state`/`check-patch-tree` 通过。
4. 重跑 libc-test static/dynamic full、`make check`（L1）、`make check-night`（或至少 `tset:libc-test` + `check-night-report`），确认夜跑转绿。

## 接口规范

- 补丁只改 `src/regression/malloc-brk-fail.c`；一文件一补丁，符合 `docs/Process-01`。
- 不修改测试的 `t_error`/`t_status` 语义；不跳过测试；不降低覆盖。
- `components/libc-test/changelog.md`（若存在）记录补丁原因与 commit。
- 不改 `tests/tset` 驱动的 judge 逻辑；不改 spec/QEMU/gem5/musl。

## 范围 / 非范围

**在范围内**：`manifests/components.lock.toml`（仅 libc-test 条目）、`components/libc-test/**`、本任务书、`milestones.md`、运行期证据。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/qemu/**`、`components/gem5/**`、`components/musl/**`、`tests/**` 其它文件、`tools/testcases/tset/**` 判据。

## 验收标准

1. **补丁生效**：`libc-test 源树` 为 base+1；`git diff` 仅 `malloc-brk-fail.c`；`make apply-series`/`check-source-state`/`check-patch-tree` rc=0。
2. **64K 页通过**：`make check-tset-libc-full` static+dynamic rc=0；`malloc-brk-fail` dynamic 不再报“malloc succeeded after memory is filled”。
3. **4K 页不退化**：补丁在 4K 页布局下仍保持原测试语义（prime 只消耗堆，不改变断言）；无法现场跑 4K 页时，用静态推理 + 代码审查说明。
4. **夜跑转绿**：`make check-night`（或等价 libc-test full + 其它三项）后 `check-night-report` rc=0；若只跑 libc-test，须说明其余三项沿用上一轮结果，不得伪称 full green。
5. **门控**：`make check`（L1）rc=0；`check-components`/`check-source-state`/`check-patch-tree` rc=0；`check-run-artifacts` rc=0。
6. **反例可达 FAIL**：删补丁中的 prime/回退原语义 ⇒ dynamic 用例 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **范围**：无 spec/QEMU/gem5/musl 改动；完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**测试输入侧**的可移植性修正，不是放宽判据；static 仍覆盖原行为，dynamic 仍执行同一用例。
- 若 prime 方案在 4K/64K 页上无法同时成立，保留现场并留问；不改成“dynamic 排除”或 known-fail。
- 修改 `patchless` 属组件策略变更，须在完成区明确记录；不改 libc-test 的 lock commit。

## 未决（下发前确认）

1. prime 大小/数量：默认 `malloc(50000)` + `malloc(10000)` 保留；若 64K 空洞 class 不同，按现场调整并记录。
2. 是否要求本任务直接跑完整 `check-night`（小时级）；默认先跑 libc-test full，再按 M11 收口跑 night。
3. `components/libc-test/changelog.md` 是否存在；不存在则在任务书完成区记录。

## 完成区

**测试结果**：`make check-tset-libc-full` rc=0（static：discovered 367/excluded 30/total 337/pass 335/fail 0/known-fail 2/blocked 0；dynamic：367/27/340/pass 338/fail 0/known-fail 2/blocked 0）；`regression/malloc-brk-fail` 两档均 PASS。`make check`（L1）rc=0；`check-components`/`check-source-state`/`check-patch-tree`/`check-run-artifacts`/`check-component-changelog` 单项 rc=0。完整夜跑 `make check-night` 4/4 成员 rc=0（tset:libc-test/llvm-ts/embench + arch:cfx，报告 `2026-11-05-13`），`make check-night-report` rc=0。证据脚本 `运行期证据脚本`：normal 18/18 PASS（rc=0），`--inject` 25/25 PASS（rc=0）。
**修改文件**：`manifests/components.lock.toml`（仅 libc-test 条目与相邻注释）、`components/libc-test/{README.md,changelog.md,series,patches/src/regression/malloc-brk-fail.c.patch}`、本任务书；运行期证据在 `运行期证据目录/`（未入库）。
**验收结果**：
1) 补丁生效：`libc-test 源树` base+1（`fc50a4d`），`git diff b7ec467..HEAD` 仅 `src/regression/malloc-brk-fail.c`；一文件一补丁、series 字典序；`make apply-series`/`check-source-state`/`check-patch-tree` rc=0。
2) 64K 通过：dynamic 首个 `malloc(10000)` 在 `RLIMIT_DATA=0` 后 `mmap(65536)` 返回 ENOMEM（无 brk/成功 mmap），munmap 64K 后同一 `mmap(65536)` 成功；strace 见证据目录。
3) 4K 不退化（无法现场跑：guest 页固定 64K）：`size_classes` 与页大小无关，32736 在 4K 仍是 class 39；4K 下可写 LOAD 空洞均 <32768（无 class-39 捐赠组），6 块在 dynamic 各自独立 mmap 32K 且满槽；4K 推理下 static lite_malloc 6×32736 后余 4480 B（<10000），首个 malloc 仍需 brk/mmap 而失败，64K 洞放得下 32K/12K mmap。
4) 反例可达 FAIL：回退 pristine 源 ⇒ dynamic rc=1 且报旧消息 `malloc(10000) succeeded after memory is filled`；`cp` 回填后 md5 相等、git 干净、复跑 PASS。
**新发现/坑**：① 默认 `malloc(50000)+malloc(10000)` 实测 dynamic 仍失败：50000→class 42（无捐赠组），10000 仍命中捐赠 class-39 槽；故改为 6×32736（class 39、16 B 对齐）。该 6 是锁语料/驱动布局下的经验值（4 个捐赠 class-39 组 + class-40 组 2 槽；DADAO 64K 实测 static 余 192 B brk），语料/驱动/LOAD 布局变化需重核。② 共用 `共享 QEMU 源树` 被其它分支 patch set 收敛导致 `check-patch-tree` 先红，已按 Process-01 复原到锁 base 后 `make apply-series`（未改仓库文件）。③ 运行期临时盘被已验证任务临时物占满；清理已验证任务的 093t/094t/096t/119t 临时目录后恢复，本轮实验与证据改落 `运行期证据目录/`。
**遗留问题**：驱动 `run_libc_test_user_suite.py` 顶部仍称 libc-test 为 "patchless corpus"（本任务不改驱动判据/注释，交 architect 决定订正）；`milestones.md` 流水行状态归主会话收尾；4K 页为静态推理（QEMU guest 页固定 64K，无法现场跑）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查改动（补丁源、manifest、README/changelog、证据脚本），finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务默认 prime `50000+10000` 不解问题 | ✅已修 | 改为 6×`malloc(32736)`（class 39、16 B 对齐），保留不释放 | dynamic 由 FAIL→PASS；`--inject` 回退仍 FAIL、回填回绿 |
| F2 prime 数量依赖锁语料/驱动布局，可能脆 | ✅已处置 | 按 donate 分区现场核对：4 个 class-39 捐赠组 + class-40 组 2 槽=6；static lite_malloc 余 192 B；写入补丁注释与完成区 | full suite static/dynamic rc=0；strace 显示首个 malloc 走 `mmap(65536)` 失败、munmap 后成功 |
| F3 4K 页无法现场跑 | ✅已处置 | 给出静态推导：`size_classes` 页无关、4K 空洞均 <32768 无 class-39 组、static 6 块后余 4480 B、64K 洞容得下 32K/12K mmap | 完成区第 3 条；未伪称现场运行 |
| F4 注入还原纪律 | ✅已修 | 脚本仅 `cp` 备份/回填 + md5 比对；反例用运行期保存的 pristine 副本，不用 git 还原 | 注入后 `git status` 非空；回填 md5 相等、git 干净；复跑 PASS |
| F5 共用 `共享 QEMU 源树` 被其它分支收敛，`check-patch-tree` 先红 | ✅已修 | `reset --hard` 到锁 base 后 `make apply-series`（未改仓库文件） | `check-patch-tree` 7 组件/303 补丁 rc=0 |
| F6 新建 README/changelog 是否越界 | ✅已处置 | Process-01 §2/§10 要求组件 README/changelog；`changelog.md` 按 M11 列表体例 | `check-component-changelog` 7 文件×4 断言 PASS |
| F7 证据脚本可能恒真 | ✅已修 | 每条断言有可达 FAIL；`--inject` 独立反例路径；计数现场累加 | normal 18/18、inject 25/25，均 rc=0 |

判决：finding 全部处置，证据脚本 `--inject` 通过；状态置 `待验收`。范围外观察（驱动 docstring 仍称 patchless）记入「遗留问题」交 architect，不作为本任务 finding。

#### 第 1 轮 reviewer 验收

**重跑（reviewer 本人执行，2026-11-05 13:45–14:04，workdir = 任务 worktree，真实 rc）**
- `运行期证据脚本`(normal)：**rc=1，`pass=17 fail=1`** —— 唯一红项 `check-patch-tree`（见 F1），其余 17 条 PASS（manifest/补丁/series/base+1/两档用例）。
- `make check-tset-libc-full`：**rc=0**（154s）；static `discovered 367/excluded 30/total 337/pass 335/fail 0/known-fail 2/blocked 0`、dynamic `367/27/340/338/0/2/0`，`regression/malloc-brk-fail` 两档均 `exit=0 PASS` —— 与完成区数字逐字一致。
- 修复前同口径基线（`.dadao/tests/libc-test-user/20261105T025041Z…dynamic`）：`337 pass/1 fail/2 known-fail`；`excluded` 27→27、`known_fail_bases` ISS-246/251/255 全同 ⇒ 无新增 known-fail/排除、无覆盖降级，仅该用例翻绿。
- `make check-components` **rc=0**、`check-source-state` **rc=0**（`libc-test: OK HEAD=fc50a4d count=1 clean`）、`check-component-changelog` **rc=0**、`check-run-artifacts` **rc=0**、`make check-night-report` **rc=0**（manifest 4 行全 0）——13:47 与 14:03 两轮均绿。
- `make check-night` 重跑：**rc=2**，输出 `FAIL — 报告目录已存在（同一天不覆盖）：…/night/2026-11-05-13`（工具自带同日不覆盖守卫，未用 `--allow-overwrite` 覆盖既有证据）⇒ 改按「核对报告现场」：`manifest.tsv` 4 行 rc=0、`meta.json` 4 成员、四份成员日志尾部依次为 `check-tset-libc-full: PASS`/`check-tset-llvm-full: PASS`/`check-tset-embench-full: PASS`/`check-arch: PASS`（05:06:34–05:32:09Z），与完成区「4/4、报告 2026-11-05-13」一致。
- 补丁正确性：源树 base+1 干净、`git diff b7ec467..HEAD` 仅 `src/regression/malloc-brk-fail.c`；把补丁施于 base 后 md5=`cbf1065` 与 HEAD 全等；`git apply --check` 正/反向均 rc=0；diff 仅新增 prime 块（断言/magic/`return t_status`/`t_vmfill`/`t_setrlim`/`munmap` 逻辑未动，失败路径沿用原 `t_error + return 1` 形态）；`series` 单行有序；锁 commit 仍 `b7ec467969a5…`；manifest 体例与其余受补丁组件一致。
- 独立反例注入（gate lock 下、`cp` 备份 + `md5sum -c` 还原、**禁 git 还原**）：备份 `cbf1065` → 删除 prime 块得 `9364751`（`git status` 非空）→ **重跑同一 `run.sh`：rc=1，`pass=12 fail=6`**，dynamic `guest exit 1 … malloc-brk-fail.c:31: malloc(10000) succeeded after memory is filled`（static 仍 PASS）→ `cp` 回填 `md5sum -c OK`、`git status` 0 行 → 复跑回到注入前基线 `pass=17 fail=1`（dynamic PASS，源 md5 仍 `cbf1065`）。
- **约束核验**：改动仅 6 文件（审前/审后 `git status --porcelain -uall` 快照逐行相同、6 个 md5 全等），无 spec/QEMU/gem5/musl/tests/`tools/**` 改动；驱动中 `malloc-brk-fail` 0 处命中 ⇒ 未动判据/排除/known-fail/judge；4K 页明写「无法现场跑（guest 页固定 64K）」并给静态推理；完成区 13 行 ≤30、任务书无运行期绝对路径；状态 `待验收`；`milestones.md` 未改（状态归 architect，其流水行现仍 `待开始`）。

**finding**
- **F1【环境阻断·非本任务】** `check-patch-tree` **rc=2**、`make check`(L1) **rc=2**，重试 13:47/13:53/13:57/14:02/14:03 共 **5 次**，输出恒为 `qemu: assertion ⑨`+`⑥` 两条、`2 problem(s)`。根因：共享 `共享 QEMU 源树` 于 13:38:52 被并发 QEMU-083t 按其**未提交**的 `components/qemu/patches/target/dadao/helper.c.patch`（md5 `41cb769`）收敛（reflog `reset c3d48b7 → commit 4d604a4`），而本树与 master 仍为 `57cadf2`；**master 无本任务改动同样红（reviewer 直跑 rc=1）**，`make apply-series` 亦在 qemu 处 `refusing to apply`；本任务 diff 不含任何 qemu 文件 ⇒ 与交付物无关。**须 architect 待 QEMU-083t 合并/共享源复原后复跑 `make check-patch-tree` + `make check` 并确认绿，再 `/complete`。** 披露：reviewer 曾误以 `--help` 触发 `apply_series.py`（该工具不支持 `--help`），其在第 2 个组件 qemu 处 `SystemExit`，已核 11 个源树 HEAD/reflog 全未变、零副作用。
- **F2【文档级】** 驱动 `run_libc_test_user_suite.py:1390` 仍打印 `(patchless, manifest-locked)`，另 `run_suite.py:39`、驱动 docstring、known-fail 文案共 4 处称 libc-test 为 patchless（纯注释/文案，不进门控与判据；ISS-246/251/255 的 basis 现场重算不依赖它）——engineer 已登记「遗留问题」，请 architect 收尾订正。
- **F3【文档级】** 完成区「static 6×32736 后余 4480 B」与补丁注释/自审「余 192 B」语境不同（4K vs 64K），建议 architect 核对措辞；不涉判据。

**判决：Accepted** —— 交付物本身达标（补丁正确、两档全量绿、无降级、范围与体例合规、反例可达 FAIL 并回绿）；F1 两项命令本轮**未观察到绿**，属并发共享工作树干扰，已按「保留现场 + 有据重试 5 次 + 记录根因」处置，终审前须由 architect 复跑确认。

#### 收尾（architect，2026-11-05）

- F1（环境阻断）：`check-patch-tree`/L1 红来自并发 `QEMU-083t` 改写共享 QEMU 源树，与本任务无关；待 QEMU-083t 合并/源树复原后由 architect 复跑 `check-patch-tree` + `make check`，绿后再置 `已验证`。
- F2（文档级）：驱动/`run_suite.py` 仍有 4 处 “libc-test patchless” 文案；列入遗留，另立小任务订正（不改判据）。
- F3（文档级）：完成区已区分 4K 推理（余 4480 B）与 DADAO 64K 实测（余 192 B）。
- 运行期路径已改为通用描述。
