# TESTCASES-101t: libc-test `malloc-brk-fail` 改用 {cur=0,max=inf}（收口 rlimit 实现后的夜跑红）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`QEMU-084t`（已验证；guest rlimit 记账落地）、`TESTCASES-100t`（已验证；该用例 64 KiB 页修正）
**状态**：已验证

## 用户裁定（2026-11-06）

> 「2：按用例意图改语料（两侧都改）」

即：认定上游用例的限值写法在 post-4.7 内核下已过时；改语料为 `{cur=0,max=inf}`，并**在宿主上做同样改动后验证 PASS**，目标是宿主与目标**两侧都 PASS**（不是「对齐宿主现状的 FAIL」）。

## 宿主对照（architect 实测，2026-11-06）

宿主：musl 1.2.6（按锁 commit 自建静态工具链）+ Linux 6.8 + 4 KiB 页。

- 上游原样（`t_setrlim(RLIMIT_DATA, 0)`，cur/max 均为 0）⇒ **FAIL**（rc=1，`malloc(10000) failed (eventhough 64k is available to mmap): Out of memory`）
- 只降 `cur`、保留 `max=infinity` ⇒ **PASS**（rc=0）

结论：本任务改语料后，宿主（同改）与目标应**同为 PASS**；页大小 4 KiB/64 KiB 不是该用例的失败原因。

## 现状

`QEMU-084t` 实现 guest `RLIMIT_AS/DATA/STACK` 记账后，夜跑 `tset:libc-test` 的 static 与 dynamic 两档都红：

```
FAIL regression/malloc-brk-fail  exit=1
  malloc(10000) failed (eventhough 64k is available to mmap): Out of memory
```

根因：该用例用 `t_setrlim(RLIMIT_DATA, 0)`，而 `t_setrlim` 会把 **`rlim_cur` 与 `rlim_max` 都设成 0**。内核 `may_expand_vm()` 的 Valgrind workaround 要求：

```
rlimit(RLIMIT_DATA) == 0 && 请求量 <= rlimit_max(RLIMIT_DATA)
```

`max` 也是 0 时 workaround 不成立 ⇒ `munmap` 之后的新 `mmap` 仍被拒 ⇒ 用例报错。

宿主实测（Linux 6.8）：

- `RLIMIT_DATA={0,0}` + RW `mmap(64 KiB)` ⇒ `ENOMEM`
- `RLIMIT_DATA={cur=0,max=infinity}` + RW `mmap(64 KiB)` ⇒ 成功

即该用例的期望只在 `max` 保持 infinity 时成立；此前能过是因为 QEMU 把 rlimit 当 no-op。

## 目标

1. 修改 `tests/tset/libc-test/patches/src/regression/malloc-brk-fail.c.patch`：把 `T(t_setrlim(RLIMIT_DATA, 0));` 改为**只降 `rlim_cur`、保留 `rlim_max`** 的调用（等价 `{cur=0, max=infinity}`），并在补丁注释里写明依据（内核 `may_expand_vm()` 的 Valgrind workaround；`t_setrlim` 会连 `max` 一起降，使 workaround 失效）。
2. 保持用例语义与断言不变：先 `t_vmfill` 填满 VA ⇒ 首个 `malloc(10000)` 仍必须失败且 `errno=ENOMEM`；`munmap` 64 KiB 后 ⇒ 第二个 `malloc(10000)` 必须成功。不得删除断言、不得放宽退出码。
3. 组件补丁按既有流程重导出（一文件一补丁、`series`/`changelog.md` 更新），锁 commit 不变。
4. 更新 `tests/tset/libc-test/README.md` 与 `tests/tset/libc-test/changelog.md` 的说明（该用例为何用 `cur=0/max=inf`）。

## 范围 / 非范围

**在范围内**：`tests/tset/libc-test/patches/src/regression/malloc-brk-fail.c.patch`、`tests/tset/libc-test/{series,changelog.md,README.md}`（如系列不变则不动 `series`）、本任务书、`milestones.md`。

**不在范围**：QEMU/gem5 实现与补丁、其它语料用例、`spec/**`、`contracts/**`、测试判据/门控逻辑。

## 验收标准

1. 该用例在 QEMU 下 static 与 dynamic 两档均 PASS（真实 rc=0）。
2. `make check-tset-libc-smoke` rc=0；`make check-tset-libc-full`（static+dynamic）rc=0。
3. `make check-patch-tree`、`make check-source-state`（libc-test base+1 clean）、`make check-index-blobs`、`make check`（L1）rc=0。
4. 反例：把补丁改回 `t_setrlim(RLIMIT_DATA, 0)` ⇒ 该用例 FAIL；`cp`+`md5sum -c` 还原并重建后回绿（禁 git 还原）。
5. 宿主对照：用同一条改法在宿主（musl 1.2.6 + Linux 6.8）跑该用例 ⇒ PASS；目标侧同改 ⇒ PASS（两侧一致，均 rc=0）。宿主命令/输出写入完成区（不写运行期路径）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**语料假设**修正，不是 QEMU 语义回退：QEMU 行为与 Linux 6.8 实测一致，保持不动。
- `TESTCASES-100t` 的 6×32736 启动堆 prime 逻辑保留（64 KiB 页下仍需消耗 loader 捐赠堆）。
- 修好后由 architect 重跑完整夜跑（一次全绿）再收口 M11。

## 完成区

**测试结果**：目标侧 `regression/malloc-brk-fail` static/dynamic 均 PASS（rc=0）；`make check-tset-libc-full` rc=0（static 367/30/337、pass 335/fail 0/known-fail 2/blocked 0；dynamic 367/27/340、pass 338/fail 0/known-fail 2/blocked 0；两档该用例 `exit=0`，排除集与 known-fail 基线不变）；`make check-tset-libc-smoke` rc=0；`check-patch-tree`/`check-source-state`/`check-index-blobs`/`check-component-changelog` rc=0；`make check`（L1）rc=0。宿主对照（musl 1.2.6 + Linux 6.8、4 KiB 页、`musl-gcc -static`）：上游原样源 rc=1（`malloc(10000) failed (eventhough 64k is available to mmap)`），同改 `{cur=0,max=inf}` 后 rc=0。
**修改文件**：`tests/tset/libc-test/patches/src/regression/malloc-brk-fail.c.patch`、`tests/tset/libc-test/{README.md,changelog.md}`、本任务书、`.tao/knowledge/milestones.md`（仅本任务流水行状态）；`series` 不变（仍 1 条）。运行期证据已落运行期证据目录（未入库）。
**验收结果**：
1) 补丁：仍是一文件一补丁、一个 `diff --git`；新增 hunk 删除 `T(t_setrlim(RLIMIT_DATA, 0));`，改为 `getrlimit(RLIMIT_DATA,&rl)` + 只设 `rlim_cur=0` + `setrlimit`，注释写明 `may_expand_vm()` Valgrind workaround 与 `t_setrlim` 连带降 `max`；`TESTCASES-100t` 的 6×32736 prime、两条断言、`return t_status` 全保留；锁 commit `b7ec4679…` 不变。
2) 源树：base+1 干净，`git diff --name-only base HEAD` 仅 `src/regression/malloc-brk-fail.c`；`make apply-series` rc=0。
3) 宿主对照：上游原样 rc=1 且为 post-munmap ENOMEM 消息；改后 rc=0 —— 宿主与目标两侧一致 PASS。
4) 反例：补丁改回 `t_setrlim(RLIMIT_DATA, 0)` 并重建 ⇒ dynamic rc=1、报 `malloc(10000) failed (eventhough 64k is available to mmap)`；`cp` 回填补丁（md5 `a4fbcb1b…`）+ `make apply-series` 重建后源码 md5 `cca9f137…` 与注入前相等、worktree 干净、dynamic 回绿 rc=0；证据脚本 normal 36/36、`--inject` 49/49，均 rc=0。
**新发现/坑**：① 上游用例的限值写法是 post-4.7 内核下的过时假设：`{0,0}` 使 `may_expand_vm()` 的 Valgrind workaround 失效；宿主上原样同样 FAIL ⇒ 此前红是语料假设而非 QEMU 偏差。② `make check` 首跑红在 `check-run-artifacts`：共享运行目录内有两个**空**的 `llvm-ts-user` 时间戳目录（来自 09:28 被终止的 llvm-ts 夜跑；`find -mindepth 1` 计数 0），`rmdir` 清理后 L1 转绿；非本任务产物。
**遗留问题**：只改语料补丁，未动驱动注释（驱动内仍称 libc-test 为 patchless，属 `TESTCASES-100t` 遗留）；夜跑由 architect 重跑。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查补丁、源树、README/changelog、证据脚本与任务书，finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只降 `cur` 是否仍让首个 `malloc(10000)` 失败（workaround 对 `max=inf` 恒放行） | ✅已处置 | 不改断言：失败来自 `t_vmfill` 耗尽 VA（无可用 64 KiB 洞），而非 rlimit；补丁注释只称保持用例意图 | 目标侧两档 PASS；反例（`{0,0}`）dynamic rc=1 且信息为 post-munmap ENOMEM |
| F2 证据脚本三条断言写错（锁 commit 全串、把删除行当新增、把上下文当新增断言） | ✅已修 | 校正为全 40 位 commit、`^-` 删除行 + `^\+\s*(T\()?t_setrlim\(` 无新增、断言改在源文件核对 | normal 由 rc=1/fail=3 修至 36/36 rc=0 |
| F3 注入还原是否用 git 还原 | ✅已处置 | 还原仅 `cp` 补丁 + `md5sum` 比对 + `make apply-series` 重建；`reset --hard` 只用于组件检出回到锁 base（丢弃工具生成的 commit），脚本头明示 | `--inject` 49/49：补丁 md5、源 md5 均回到注入前，worktree 干净 |
| F4 宿主对照是否真实（非复用他人结论） | ✅已修 | 自建两个宿主二进制（上游原样 / 改后）并实跑 | 上游 rc=1、改后 rc=0，输出入证据目录 |
| F5 `make check` 红在共享运行目录的空残目录 | ✅已处置 | 仅删除两个空目录（`rmdir`），未动任何有内容的证据 | L1 rc=0（31s） |
| F6 新代码是否污染后续 `errno` 断言 | ✅已处置 | 保留断言前的 `errno = 0;`；`getrlimit`/`setrlimit` 失败各有独立 `t_error` + `return 1` | 源文件逐行核对；两档 PASS 且反例仍报 ENOMEM |

判决：finding 全部处置，normal/`--inject` 证据脚本 rc=0；状态置 `待验收`。

#### 第 1 轮 reviewer 验收（2026-11-06）

**重跑记录（reviewer 独立执行，rc 均取被检命令自身）**
- 证据脚本：`run.sh` rc=0（`pass=36 fail=0`）；`run.sh --inject` rc=0（`pass=49 fail=0`，补丁 md5 `a4fbcb1b…`、源 md5 `cca9f137…` 均回位、源树 clean base+1、dynamic 回绿）。
- L1：`make check` rc=0（09:44 与 09:52 各一次，`repository checks (L1): PASS`）。
- `check-tset-libc-smoke` rc=0（类别 5/代表 5、结构断言 PASS）；`check-tset-libc-full` rc=0 ×2：static `367/30/337 pass=335 fail=0 known-fail=2 blocked=0`、dynamic `367/27/340 pass=338 fail=0 known-fail=2 blocked=0`，两档 `regression/malloc-brk-fail exit=0`。
- `check-patch-tree`（7 组件/305 补丁）、`check-source-state`（libc-test `count=1 clean=True`）、`check-index-blobs`（226 new-file）、`check-component-changelog`（28 项）均 rc=0（注入前后各跑一轮）。
- 宿主对照（reviewer 自建二进制，非采信脚本产物）：musl 1.2.6 + Linux 6.8.0-147、`getconf PAGESIZE=4096`；上游原样 **rc=1**（`…malloc-brk-fail.c:41: malloc(10000) failed (eventhough 64k is available to mmap)`），同改 **rc=0**。语义探针：`getrlimit`+只设 `rlim_cur=0`+`setrlimit` 后 `max_unchanged=YES`（cur=0 / max=2^64-1）；`src/common/setrlim.c` 证实 `t_setrlim` 同时写 `rlim_max=rlim_cur=lim` ⇒ 注释所述成立。
- **reviewer 独立注入**（`cp` 备份 + `md5sum -c` 还原，禁 git 还原）：补丁改回 `T(t_setrlim(RLIMIT_DATA, 0))` 重建后 static、dynamic **均 rc=1**，报 `malloc-brk-fail.c:67: malloc(10000) failed (eventhough 64k …)`；同状态下重跑 `run.sh` 得 rc=1（`pass=24 fail=12`：补丁断言 5 条 + 两档用例 + 宿主同改）⇒ 脚本有可达 FAIL；`cp` 回填 + md5 相等 + 重建后源 md5 `cca9f137…` 相等、两档回绿 rc=0。
- 快照对账：验收前/写入前 `git status --porcelain -uall` 逐行与初始相同（5 文件），5 个改动文件 md5 前后一致；本轮写入仅新增本子区。

**约束核验**：① 补丁最小性 ✓ 单 `diff --git` 单 hunk，唯一删除行 `-	T(t_setrlim(RLIMIT_DATA, 0));`，6×32736 prime、首 malloc 必失败且 ENOMEM、munmap 后必成功、`return t_status` 全保留，无放宽退出码；② 语义等价 ✓（探针 + `setrlim.c` 源码 + 注释含 `may_expand_vm()` Valgrind workaround 与 `t_setrlim` 连带降 max）；③ 两侧一致 ✓ 宿主/目标同 PASS；④ 门控 ✓（上列全 rc=0，锁 commit `b7ec4679…` 不变）；⑤ 反例 注入→FAIL→还原→回绿 ✓（reviewer 独立 + 脚本自证各一次）；⑥ 范围/体例 ✓ 仅 5 文件（补丁/README/changelog/任务书/milestones），无 QEMU/gem5/spec/contracts；完成区 12 行、无运行期路径；完成区数字与我重跑逐条一致。

**Finding（均非阻断，交 architect 处置）**：F-a 「清空的时间戳目录」首跑红无日志留存、事后不可完全复原；可核证旁证 = 09:28 llvm-ts 夜跑 log `Terminated`、`.dadao/tests/llvm-ts-user` 父目录 mtime=09:39（与 `rmdir` 一致）、当前 A2 现场扫 919 个 run 目录 0 问题 ⇒ 披露基本属实、与本任务产物无关，唯留痕不足记档。F-b 驱动输出仍标 libc-test `patchless`（已披露，TESTCASES-100t 遗留，doc 级）。F-c 我的注入/还原使组件检出本地提交 hash 由 `2ffd765` 变为 `cd9bcaa`（内容字节相同 `cca9f137…`，E1 base+1 clean、门控绿）。

**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全部通过、硬约束无违反；architect 仍需终审。

#### 收尾（architect，2026-11-06）

- F-a：清空时间戳目录一事留痕不足（无首跑红日志），旁证一致；记遗留，不追改。
- F-b：驱动输出仍标 libc-test `patchless`（`TESTCASES-100t` 遗留，doc 级）；记遗留。
- F-c：reviewer 注入/还原使组件本地提交 hash 变化，内容字节相同、base+1 clean、门控绿；以字节与门控为准。
- 判决 Accepted，状态置 `已验证`。
