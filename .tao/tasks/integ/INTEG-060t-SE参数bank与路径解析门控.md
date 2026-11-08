# INTEG-060t: gem5 SE syscall 参数 bank 与路径解析门控

**模块**：integ
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实

- musl 以 `__dadao_argmask(nr)` 决定「第 i 个参数进 RD 还是 RB」：指针走 RB、标量走 RD，两 bank 各自从 16 计数；QEMU 有同表副本，`tools/qemu/check_syscall_abi.py` 断言两侧**逐项相等**
- **gem5 SE 没有这张表**：每个 syscall 在 `switch` 里手写 `rd(16)`/`rb(16)`，写错 bank 不会触发任何门控
- 真实案例：`fcntl` 的锁指针原取 `rb16`，实际 musl mask 为全 RD，`GEM5-023t` 自审才发现并改为 `rd18`
- 路径解析：`resolveGuestPath()` 对「相对路径 + dirfd」用打开时记录的 guest 名拼接，再走 redirect；`..` 未归一化，空路径/`AT_EMPTY_PATH` 分支无专门探针

## 目标

1. **参数表统一**：在 gem5 SE 侧引入与 musl 同源的 `argmask` 表（或等价的「按 mask 取第 i 个参数」封装），dispatch 统一通过它取参，删除逐处手写的 bank 选择。
2. **三方门控**：`tools/qemu/check_syscall_abi.py` 扩为 musl / QEMU / gem5 三方逐项相等；新增/修改 syscall 时三方必须同时更新，否则门控红。
3. **路径解析探针**：覆盖绝对路径 + 非 `AT_FDCWD` dirfd（应忽略 dirfd）、相对路径 + dirfd（经 redirect）、`..` 归一化、空路径/`AT_EMPTY_PATH`、`/` 与非 `/` 结尾；与宿主 Linux 逐项对照。
4. 不改测试用例与期望；不改 QEMU 语义。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh}`（取参封装与 mask 表）、`tools/qemu/check_syscall_abi.py`（三方校验）、`tools/testcases/**` 的 SE 探针（路径解析）、本任务书、`milestones.md`。

**不在范围**：新增 syscall 语义（前序任务）、QEMU 实现、测试用例与期望、`spec/contracts`。

## 验收标准

1. gem5 侧的 mask 表与 musl/QEMU **逐项相等**（含 0x00 条目）；门控 rc=0。
2. 反例：把任一 syscall 的 mask 改错（或 dispatch 改成读另一个 bank）⇒ 门控/探针 FAIL；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
3. 路径探针全绿：绝对+dirfd、相对+dirfd+redirect、`..`、空路径/`AT_EMPTY_PATH`；与宿主 Linux 结果一致。
4. 基线不退化：`GEM5-025t` 的 static 基线复跑 pass/blocked 不下降（环境缺口与 bison 例外保持登记）。
5. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是「防回归」任务，不新增能力；目的是让 rd/rb 混用与路径拼接错误**在门控里红**，而不是事后靠失败样本猜。
- 若发现某 syscall 的 mask 在 musl/QEMU 本身就分歧，先停下提交（不得自行选一边）。

## 完成区

**测试结果**：三方门控 80/80 PASS（gem5 段 11 条断言）；仅补丁（无组件源）模式 rc=0（musl/QEMU 源缺失的两项按设计 SKIP）。路径探针驱动 26/26：宿主 Linux（oracle）、gem5 SE、gem5 SE+root redirect、qemu-user 四引擎各 **22 条共享断言逐行一致**、两侧 `SUMMARY fails=0`，redirect 引擎另有 1 条根处 `..` 截断的 `local:` 断言。基线（static libc-test 双引擎 337 例）：`gem5_pass=321`、`gem5_only_fail=4`（与当前基线同集合：popen/spawn/vfork/execle-env）、`blocked=11`、`qemu_only_fail=0`、无 pass→非 pass 回归。反例：openat(56) 移出 mask 组 ⇒ 门控红并指名该行、重建后探针红；`normalizeGuestPath()` 置恒等 ⇒ 探针红（`S4-root-dotdot expected=same actual=escaped`）；两次 `cp`+`md5sum -c` 还原重建回绿（`--inject` 20/20）。
**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`、`components/gem5/{README.md,changelog.md}`（Process-01 §10 要求随组件改动登记；任务书「范围」未列，越界披露）、`tools/qemu/check_syscall_abi.py`、`tools/testcases/se/{path_resolve_probe.c,check_se_path_resolution.py}`、本任务书。
**验收结果**：`build-gem5`、`check-syscall-abi`、`check-gem5-decode`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、`check-run-artifacts`、L2 全 rc=0。L1 唯一红项是 `check-milestones-fresh` 的 A1（`INTEG-060t` 行仍在「待开始」表而册为 `待验收`，属派单时主会话应移入「进行中」的行，本任务不改台账）；L1 其余子门控逐项 rc=0（含在 A1 之后才轮到的 8 个），临时移行探针下 `check-milestones-fresh` PASS 后已 `cp`+md5 还原。一键脚本 `run.sh` 17/18（唯一红 = 上述台账 A1；`check-run-artifacts` 曾在另一任务写入非法日志名期间短暂红，其属主清理后 PASS）。`run.sh --inject` 20/20。逐 arm 等价性另用脚本核对：74 个 dispatch 块改动前后的「位置→bank」读写集合完全一致（0 差异），唯一语义变化是 `tgkill`/`time` 显式入表。
**新发现/坑**：① gem5 原有手写 bank 与 musl mask 逐 arm 一致（futex 0x19、mremap 0x11、sendto 0x12 等），缺表的 `tgkill` 恰好全标量 ⇒ 转换是纯等价重排；这类核对做成脚本比抽样读码可靠。② 路径解析真缺陷两处：`chdir("rel")` 把 `tgtCwd` 记成相对名（redirect 下后续相对 open 落到宿主 cwd）；root redirect 下 `/..` 走到宿主父目录。词法归一化修好两者，但 `link/..`（link 指向更深目录）会弹出链接本身 —— 已在代码注释与组件 README 记为已知差异。③ Linux 的 `newfstatat(fd, NULL, …, AT_EMPTY_PATH)` 是 `EFAULT`，gem5 原实现对 NULL 也操作 fd；探针 E5 抓到并已对齐。④ 证据脚本必须用任务 worktree 路径调用：`.work` 是共享符号链接，从物理路径回溯会落到主工作树并读到上一任务的补丁集（已加守卫）。
**遗留问题**：① **L1 需主会话把 `INTEG-060t` 行移入「进行中」表**（派单时间）后即全绿——探针已证移行后 `check-milestones-fresh` PASS，其余 L1 子门控本已 rc=0；② 组件 `README.md`/`changelog.md` 属 Process-01 §10 必填但不在任务书「范围」，请合并时确认；③ 路径探针未进 Makefile 门控（需已构建 gem5，L1 不可跑），由本任务证据脚本与后续任务调用；④ `link/..` 的词法归一差异未修（需 guest 符号链接解析器），已登记。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 表 245 行手工复制易错（行注释/号错配） | ✅已修 | 由 musl 表逐行生成，门控逐号比对 mask + 行注释须命名其号 | 三方门控 79/79；错一行即红（注入证据） |
| 转换可能改变某 arm 的取参 bank | ✅已修 | 独立脚本按 mask 反推「位置→bank」，逐块比对改前/改后 | 74 块 0 差异 |
| `chdir` 相对路径 + redirect 下 cwd 非绝对 | ✅已修 | `resolveGuestPath` 先 `absolutePath` 再归一化，`tgtCwd` 存绝对名 | 探针 R6/R7 与宿主一致（redirect 引擎） |
| root redirect 下 `/..` 越出 guest 根 | ✅已修 | `normalizeGuestPath` 在 guest 根截断 `..`，保留结尾 `/` 与 `.`/`..` 的目录要求 | 探针 S4/S5；注入 no-op ⇒ escaped |
| `newfstatat(fd, NULL, AT_EMPTY_PATH)` 与 Linux 不一致 | ✅已修 | NULL 路径一律 `EFAULT`，`AT_EMPTY_PATH` 只接受 `""` | 探针 E5 与宿主逐项一致 |
| 词法归一化改变 symlink+`..` 语义 | ⏸记录 | 未实现 guest 符号链接解析器；代码注释 + 组件 README 记已知差异 | 语料无此用法，基线无回归 |
| 探针驱动把 gem5 模拟器输出与 guest stdout 写进同一文件（污染断言解析、且与并发重建抢文件） | ✅已修 | 模拟器 stdout/stderr 改写到独立 `*.sim.out/*.sim.err`，guest 流仍走 `--guest-stdout`；驱动加"必须从任务 worktree 调用"守卫 | 驱动 26/26 复跑；`PermissionError` 只出现在与后台重建并发时（已避开） |
| `dadaoArgmask` 缺行时静默返回 0 | ⏸说明（门控兜底） | 保留 musl 文档化默认（未知号不进 dispatch）；门控断言「每个 case 必有表行」+「dispatch 禁止手写 bank」 | `make check-syscall-abi` 的 gem5 dispatch 两条断言 |
| 自审判决 | — | 可修项全部已修 | 门控/探针/注入/基线全绿，状态 `待验收` |

### 第 1 轮 reviewer 验收（2026-11-08，退出码均自取、未用管道吞码）

**重跑记录**
- `python3 tools/qemu/check_syscall_abi.py` → `80/80 checks passed` rc=0；仅补丁模式（临时树、无 `.work/source`）→ `77/77 + 2 SKIP` rc=0（`gem5 SE carrier: patch`）
- 独立反例（临时树，`cp`+`md5sum -c` 还原）：gem5 表 openat 移组 → rc=1 `gem5 routing mask openat (56): musl=0x02 gem5=0x00`；musl 表 openat → 4 条 FAIL；QEMU 表 openat → `guest=0x02 host=0x00`；还原后均 `77/77` rc=0、三文件 md5 OK ⇒ 门控真读三源，非硬编码
- 独立注入被测产物（`.work/source/gem5/.../se_workload.cc`，cp+md5）：`make check-syscall-abi` rc=2（79/80，指名 openat）→ 还原 md5 相等 → rc=0（80/80）；`normalizeGuestPath` 置恒等 + `make build-gem5` → 探针 rc=1 `22/26`、`gem5-se-redirect: FAIL S4-root-dotdot expected=same actual=escaped` → 还原重建 → `26/26` rc=0
- 一键证据脚本 `run.sh`（任务证据目录内）→ `SUMMARY passes=17 fails=1` rc=1（唯一红 `gate-L1`）；`run.sh --inject` → `passes=20 fails=0` rc=0
- 探针独立复跑 → `26/26` rc=0；host / gem5-se / gem5-se-redirect / qemu 各 22 条共享断言行逐字节相同，redirect 另有 `local:S5` 1 条
- 门控：`build-gem5`、`check-gem5-decode`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、`check-run-artifacts` rc=0；`check-modules`(L2) rc=0 `module checks (L2): PASS`
- `make check`(L1) rc=2，唯一 `VIOLATION: A1 …待开始… 册=待验收`；A1 之后 9 个子门控逐个 rc=0；临时移行（cp+md5）→ `check-milestones-fresh` rc=0 `结果: PASS`，还原 md5 相等 → rc=2（本记录初稿曾写入一条具体运行期证据路径致 `check-knowledge-refs` 转红，已改为文字表述并复跑 L1：该条 `具体路径 (不可复现): 0`，L1 又只剩 A1）
- 基线：落盘 JSON（16:25/16:28）早于补丁(17:09)/二进制(17:25)，故**独立全量复跑** 337 例双引擎 → `pass=321 fail=4 blocked=11 known-fail=1`、`gem5_only_fail` 同 4 例、`qemu_only_fail=0`、与 engineer 逐例 **0 差异**、对 GEM5-030t 参考 **0 例 pass→非 pass**
- 等价性：自写脚本比对改前/改后 74 个 dispatch 块的「寄存器读取序列 ↔ mask 推出的 (bank,idx) 序列」→ **0 差异**；`getReg(rd/rb 16..21)` 195→2（余 2 处在 `doFutex` 辅助函数，改前即有），`args[i]` 193 处，与「193 处」一致
- 范围：`git status` 与开工快照逐行相同、6 个交付物 md5 与开工一致；未动验收标准/期望/契约/spec；gem5 源树 clean、HEAD `d4297bd` = 锁定基线 `c8222cc`+1；完成区 5 行、无运行期绝对路径

**约束核验**：不 commit/push ✓；未改台账与验收标准 ✓；越界改 `components/gem5/{README,changelog}` 已披露且系 Process-01 §10 必填 ✓；反例还原全用 `cp`+md5（无 git 还原）✓；`link/..` 已知差异在代码注释与组件 README 如实披露 ✓。

**findings（文档级，不阻断，交 architect 收尾改）**：① 完成区「gem5 12 条」实为 **11** 条 gem5 段断言；② changelog「另 2 条 redirect 专有断言」实为 **1** 条（`local:S5`）；③ changelog「245 行含 34 行 mask 0x00」——0x00 组实为 **72** 行（34 是 0x01 组）；④ `time`(1062) 不在锁定 tbl/musl/QEMU（QEMU 无该 case、musl 无 `__NR_time`），其 `0x01` 与改前 `rb(16)` 一致，`GEM5_ONLY_MASKS` 把 131/1062 写死为常量而非从真源推导；⑤ `doFutex` 内 `getReg(rb(17))` 在 dispatch 之外，「禁手写 bank」断言覆盖不到（改前即有、与 mask `0x19` 等价）；⑥ 本环境门控读 `.work/source/gem5` 树而非补丁（已验树内容 == 补丁重建，md5 `e9cda666…` 相同）。

**三问**：① argmask 替换**语义等价**（74 块 0 差异 + 193 处一一对应 + 抽样 futex/mremap/sendto/openat/fcntl/newfstatat/tgkill/time 逐 arm 核对一致）；② 三方门控**真读三源**（musl/QEMU/gem5 均 live 解析，三处注入各自转红）；③ 路径归一化**符合 Linux**（`..` 在 guest 根截断、结尾 `/` 与 `.`/`..` 目录要求、空路径/`AT_EMPTY_PATH`/NULL 语义均与宿主真内核 22 条逐行一致）。

**判决：Accepted**（工程师达标；`make check` 当前 rc=2 仅因台账行未移，须主会话把 `INTEG-060t` 移入「进行中」后 `/complete`，移行后 L1 全绿已实测）

#### 收尾（architect，2026-11-08 19:03）

- 判决 Accepted：reviewer 自写脚本比对 74 个 dispatch 块「寄存器读取序列 ↔ mask 推出的 (bank,idx)」**0 差异**；`getReg(rd/rb 16..21)` 195→2（余 2 处在 `doFutex` 辅助函数，改前即有）；三方门控三源分别注入（gem5/musl/QEMU 各一处）均转红；路径四引擎 22 条共享断言逐字节一致。
- 基线：reviewer 独立全量复跑 337 例（因 engineer 的 JSON 早于补丁），`pass=321 fail=4 blocked=11`、`gem5_only_fail` 同 4 例、`qemu_only_fail=0`、与 030t **0 例 pass→非 pass**。
- F1–F3（数字口径）：完成区「gem5 12 条」→ 11；changelog「另 2 条 redirect 断言」→ 1（`local:S5`）；「245 行含 34 行 0x00」→ 0x00 组为 72 行（34 为 0x01 组）。
- F4：`GEM5_ONLY_MASKS`（131/1062）不可从真源推导（musl/QEMU 均无该号），**保留写死并在此记录理由**；`time`(1062) 的 `0x01` 与改前 `rb(16)` 一致。
- F5：`doFutex` 内 `getReg(rb(17))` 在 dispatch 之外，「禁手写 bank」断言覆盖不到（改前即有、与 mask `0x19` 等价）⇒ 记录为已知。
- F6：门控在本环境读 `.work/source/gem5` 树而非补丁；已验树内容 == 补丁重建（md5 `e9cda666…` 相同）。
