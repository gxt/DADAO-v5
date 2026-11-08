# GEM5-031t: gem5 SE 补 `chmod` / `fchmodat`（ISS-346）

**模块**：gem5
**项目里程碑**：M11
**依赖**：无（gem5 补丁串行；排在 `INTEG-060t` 之后）
**状态**：已验证

## 背景

`ISS-346`：QEMU linux-user 实现了 `chmod`/`fchmodat`（在模拟器内改宿主文件权限），gem5 SE 未实现。按「QEMU 有等价实现的 syscall，gem5 必须有」的口径应补齐，并加双引擎探针。

## 目标

1. `se_workload.cc` 实现 `chmod`（`SYS_chmod`）与 `fchmodat`（`SYS_fchmodat`，含 `AT_SYMLINK_NOFOLLOW`/`AT_EMPTY_PATH` 的处理按 Linux 口径）：
   - 目标 fd/路径经既有 `FileFDEntry` / 路径解析逻辑；
   - 返回值与 errno 与 QEMU 逐项一致（`ENOENT`/`EACCES`/`EPERM`/`ENOTDIR`/`ELOOP` 等按 Linux）。
2. 双引擎探针：mode 变更后可观察（`stat` 的 mode 位）、非法 mode、非属主、路径不存在、`fchmodat` 的 flag 组合。
3. 不改变其它 syscall 语义。

## 验收

1. 双引擎探针逐行一致（QEMU 作 oracle）。
2. 反例：去掉 mode 生效逻辑 ⇒ 探针 FAIL；`cp`+md5 还原重建回绿。
3. `build-gem5`、`check-gem5-decode`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1、L2 rc=0。
4. static libc-test 双引擎与当前基线逐例无回退。
5. 关闭 `ISS-346`；完成区 ≤30 行、无运行期路径。

## 完成区

**测试结果**：三引擎探针（宿主 Linux = oracle / gem5 SE / qemu-user，各用一棵独立树）54 条断言逐行一致、三侧 `SUMMARY fails=0`，驱动 20/20；覆盖 mode 回读（含 `S_IALLUGO` 高位掩码）、`ENOENT`/`ENOTDIR`/`EACCES`/`EPERM`/`ELOOP`/`EBADF`/`EOPNOTSUPP`/`EINVAL`、符号链接跟随、dirfd 相对与 `..`、`fchmodat2` 的 `AT_SYMLINK_NOFOLLOW`/`AT_EMPTY_PATH`/坏标志、pipe fd。反例两式：① chmod 分支只报成功不改 mode ⇒ 探针红且点名 `gem5-se-agrees-with-host`、宿主仍绿；② 去掉 `fchmodat`(53) dispatch ⇒ gem5 `fatal: syscall 53 not implemented`、探针无结果；两次 `cp`+`md5sum -c` 还原重建后均回绿。
**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`（`doFchmod`/`doFchmodat` + 三个 dispatch arm）、`components/gem5/README.md`、`components/gem5/changelog.md`（Process-01 §10 随组件改动登记）、`tools/testcases/se/chmod_probe.c`、`tools/testcases/se/check_se_chmod.py`（新探针源 + 驱动）、`.tao/knowledge/issues.yaml`（ISS-346 → closed，`resolved_by: GEM5-031t`）、本任务书；证据脚本 `run.sh`/`inject.py` 落运行期证据目录。组件源树单提交 amend（开工 HEAD `d4297bdc092c`、E1 clean；收尾 `286281a`），`make_patch.py` 重导出 97 份补丁。
**验收结果**：`build-gem5`、`check-gem5-decode`、`check-inst`、`check-arch`、`check-syscall-abi`(80/80)、`check-patch-tree`、`check-source-state`、`check-run-artifacts`、L2 全 rc=0；证据脚本默认档 20/21（唯一非绿 = 台账行）、`--inject` 18/18 rc=0（两式注入→门控/探针红→`cp`+`md5sum -c` 还原重建→回绿）。L1 唯一 `VIOLATION` 是台账行（见「遗留问题」）。static libc-test 337 例双引擎：`gem5_only_fail` 同 4 例（popen/spawn/vfork/execle-env）、`qemu_only_fail=0`、`blocked=11`，与当前基线（INTEG-060t 评审同 HEAD 全量）逐例 `qemu`/`gem5` 漂移各 0。
**新发现/坑**：① 锁定号表**没有** `chmod(2)` 号（musl `chmod()` = `fchmodat(AT_FDCWD,…)`；QEMU dadao 表亦无 `TARGET_NR_chmod`，其 `case` 被编译掉）⇒ 任务书要求的 `SYS_chmod` 在 guest ABI 里不存在；按 QEMU 等价集实现 `fchmod`(52)/`fchmodat`(53)/`fchmodat2`(452)，`chmod(2)` 经 musl 走 `fchmodat`（探针 A* 全测）。② 两个**不入跨引擎断言**的引擎差异：`fchmodat(bad_dirfd, 绝对路径)` 宿主 glibc 判 `EBADF` 而内核忽略 dirfd（gem5 按内核）；`fchmod(O_PATH fd)` 内核 `EBADF`，musl 的 `/proc/self/fd/<guest fd>` 回退在 QEMU（guest fd==宿主 fd）下成功、gem5 下仍失败——均已记组件 README。③ 探针不能在 guest 侧建符号链接（`symlinkat` 未实现 ⇒ fatal），链接改由驱动程序建；树必须每引擎独立（chmod 改态）且驱动重跑幂等（先删 `tree-*`），否则二次运行 `FileExistsError`。④ 证据脚本的 `.EXIT` 标记名违 `check-run-artifacts` A3，改名 `<任务号>-…-exit.txt`。⑤ **坑**：探索期用 `fchmodat2(AT_FDCWD, "", mode, AT_EMPTY_PATH)` 验证内核口径时，内核把**工作目录**当目标 ⇒ 把进程 cwd（当时是 worktree 根）改成 0644；已 `chmod` 复原。故探针**不测**该支（会改 cwd 模式），实现仍按 `doFaccessat` 同法取 `tgtCwd`。
**遗留问题**：① **L1 需主会话把 `GEM5-031t` 行从「待开始」移入「进行中」并填派单时间**（`check-milestones-fresh` R1 是 L1 唯一 `VIOLATION`）；L1 表中它之后的 10 个子门控（`check-archive`/`check-contracts-pending`/`check-contract-relocs`/`check-run-artifacts`/`check-width-sizes`/`check-components`/`check-interface`/`check-code-range`/`check-runner-reap`/`check-temp-dirs`）已逐个单独 rc=0，其余本已全绿；② `SYS_chmod` 无号可取 ⇒ 未实现，若要求虚构号段属 ABI 变更需用户裁定；③ pipe fd 的 inode 模式仍固定 `S_IFIFO|0600`（chmod 返回成功但不改 stat 结果），已记组件 README。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书要求 `SYS_chmod`，但锁定号表无该号（musl / QEMU 均无） | ✅按 ABI 处置 | 实现 `fchmod`/`fchmodat`/`fchmodat2`，`chmod()` 由 musl 映射到 `fchmodat` | `check-syscall-abi` 80/80；探针 A* 17 条全走 `chmod()` |
| 末级符号链接是否跟随（`::chmod` vs `fchmodat(...,0)`） | ✅验证一致 | 保持 `::chmod`，等价内核 `do_fchmodat(flags=0)` | 探针 A7：目标变 0600、链接仍 0777，三引擎一致 |
| 宿主无 `SYS_fchmodat2` 时 `AT_SYMLINK_NOFOLLOW` 走哪条路 | ✅已修 | `#ifdef SYS_fchmodat2` 缺失 ⇒ `-ENOSYS`（与 QEMU 相同） | 本机宿主 6.8 有该调用；探针 D3/D5 覆盖 `EOPNOTSUPP`/0 |
| pipe fd 无宿主描述符（`hostFdOf` 返 `EBADF`，宿主允许 chmod pipe） | ✅已修（受限） | `doFchmod` 对 `DadaoPipeFDEntry` 返 0，注释写明模式固定 0600 | 探针 B4/D11 三引擎同为 rc=0；差异记 README |
| `AT_EMPTY_PATH` + `AT_FDCWD` 语义 | ✅已修 | 与 `doFaccessat` 同法：`checkPathRedirect(tgtCwd)` 后 `::chmod` | 读码对齐既有 faccessat 实现（探针不测该支，避免改 cwd 模式） |
| flag 校验与 `EFAULT` 的先后 | ✅验证 | 先 `EINVAL` 再读路径（内核 `do_fchmodat` 顺序） | 探针 D9（坏标志 + 正常路径）= `EINVAL` |
| 探针在 guest 侧建符号链接依赖 `symlinkat`（未实现 ⇒ fatal） | ✅已修 | 链接改由驱动程序在每棵独立树里建，探针只 chmod/lstat | 探针三引擎跑通、54 行一致 |
| 驱动重跑不幂等（`tree-*` 已存在 ⇒ `FileExistsError`） | ✅已修 | `make_tree` 先 `shutil.rmtree` | `--baseline` 档二次运行全档复绿 |
| 证据 `.EXIT` 标记名违 `check-run-artifacts` A3 | ✅已修 | 改名 `<任务号>-…-exit.txt` | `check-run-artifacts` PASS（0 illegal） |
| 自审判决 | — | 可修项全部已修；`SYS_chmod` 无号属 ABI 事实，口径见完成区 | 门控/探针/注入/基线全绿（L1 仅台账行） |

### 第 1 轮 reviewer 验收（2026-11-08）

**重跑记录（全部本人执行；命令在 worktree 根、相对路径；下列为真实输出摘录）**
- 证据脚本默认档 `run.sh`：`== SUMMARY passes=20 fails=1 ==`、rc=1；唯一 FAIL=`gate-L1`，其 2 条 VIOLATION 均指本任务台账行（A1 分类、R1 有 worktree 仍在「待开始」）⇒ 与完成区「20/21、唯一非绿=台账行」逐条一致。
- 证据脚本 `run.sh --inject`：`== SUMMARY passes=18 fails=0 ==`、rc=0（chmod 只报成功不改 mode ⇒ 探针红且点名 `gem5-se-agrees-with-host`、宿主仍绿；去 `fchmodat`(53) arm ⇒ `syscall 53 not implemented`；两式均 `cp`+`md5sum -c` 还原重建回绿）。
- 门控逐条本人跑：`build-gem5`、`check-syscall-abi`（80/80，号集含 `fchmod`/`fchmodat`/`fchmodat2` 且**无** `chmod`）、`check-gem5-decode`、`check-inst`、`check-arch`、`check-patch-tree`（306 patches OK）、`check-source-state`（gem5 HEAD=286281a clean）、`check-run-artifacts`、`check-modules`(L2) 全 rc=0。`check-arch` 首轮 rc=2（既有计时敏感例 `integ047t::start_busy_returns_busy`，INFRA-146t A2 已记「8 次全量 1 败」），有据重跑 **1 次** rc=0，非本任务改动。
- L1：`make check` rc=2，`check-milestones-fresh` FAIL(2 项) 后即中断（日志含其前的 `check-musl-freshness`/`check-builtins-freshness`、不含 `check-archive`）；其后 10 项 + 收尾 2 条我逐个重跑——`check-archive`/`check-contracts-pending`/`check-contract-relocs`/`check-run-artifacts`/`check-width-sizes`/`check-components`/`check-interface`/`check-code-range`/`check-runner-reap`/`check-temp-dirs`/`check_issues.py`/`compileall` 全 rc=0 ⇒ L1 唯一红确为台账行。
- 台账行根因核证：主工作树已把本任务移入「进行中」（派单 2026-11-08 20:00），在主工作树跑 `make check-milestones-fresh` rc=0；本 worktree 自 `858490d8` 建、未含该移行，且子代理禁改共享台账 ⇒ 非交付物缺陷，合入 master 后即绿（已实测）。
- 自建探针（独立 C 源、独立 **61** 条断言：mode 生效/回读与高位掩码、`AT_SYMLINK_NOFOLLOW` 三态、`AT_EMPTY_PATH` 全支、非法 flag、`ENOENT`/`ENOTDIR`/`EACCES`/`EPERM`/`ELOOP`/`EBADF`、dirfd+`..`、`AT_FDCWD`+空路径）：宿主 Linux 作 oracle，gem5 SE 与 qemu-user 各 61 行**逐行一致**、三侧 `SUMMARY fails=0`，驱动 17/17 rc=0。
- `AT_FDCWD`+`""`+`AT_EMPTY_PATH` 实测三引擎一致地**改 cwd 模式**（0755→0701，与内核/QEMU 同）；在临时子目录内测、当场复原，树根复核仍 0755。权限抽样（临时目录、仓库根、`.tao`、`tools`、`tests`）1777/775 无异常。
- 自选反例注入（去 `doFchmodat` 未知 flag 校验，**非** engineer 两式）：`make build-gem5` rc=0（128 s）⇒ 我方探针红（`D16`/`D17` `expected=errno 22 actual=0`，宿主与 qemu 仍绿）驱动 rc=1；`cp` 备份 + `md5sum -c` 复原（md5=原值）+ 重建 rc=0（129 s）⇒ 探针 17/17 回绿，组件源树 `git status` 净、HEAD=286281a。
- 基线 337 例：engineer 落盘 JSON ↔ INTEG-060t 参照，qemu/gem5 逐例 drift=0、pass→非 pass=0；我另在**最终产物**上全量重跑 gem5 档，337 例 klass 分布 321/11/4/1 与参照 drift=0、pass→非 pass=0。
- 快照对账：验收前/后 7 个改动与新增文件 md5 逐一致、`git status` 逐行一致、组件源树与 `se_workload.cc` md5 复原。

**约束核验**：完成区 5 行（≤30）✓；任务书全文无运行期路径 ✓；`ISS-346` `status: closed` / `resolved_by: GEM5-031t` ✓；改动范围=完成区「修改文件」7 项、无越界 ✓；补丁 97 份与完成区一致 ✓；未 commit / 未 push ✓。

**发现（非阻断）**：① pipe fd 的 mode 回读与 QEMU 不一致——实测宿主/qemu `0600→0640`、gem5 仍 `0600`（三者返回值均 0），属 SE pipe 无宿主描述符的既有模型限制，已记组件 README「已知限制」与遗留③，且不改 `doFstat`（守目标 3）；② 完成区「L1 唯一 VIOLATION」实为同一台账行的 2 条（A1+R1），措辞级；③ **reviewer 侧事故已处置**：基线重跑的构建树曾把临时盘占到 97%，触发 `check-temp-dirs` 红 **1 次**，删除该树后 `check-temp-dirs` rc=0，非交付物问题。

**判决：Accepted**（`check-arch` 首轮偶发、`check-temp-dirs` 首轮红分别有据重跑 1 次并记录；L1 台账行归主会话处置，已在 master 实测 rc=0）。

#### 收尾（architect，2026-11-08 22:06）

- 判决 **Accepted**（reviewer 独立重跑：证据脚本 `--inject` 18/18、自建探针 61 条断言三侧一致、基线 337 例 drift=0、自选反例注入→红→md5 还原→回绿）。
- 遗留①（L1 台账行）由主会话在合并时移行处置；遗留②（`SYS_chmod` 无号）确认为 ABI 事实、非缺陷，不虚构号段；遗留③（pipe fd 模式）记组件 README 已知限制。
