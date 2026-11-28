# m18-linux-010: ISS-486 措辞订正（libc 侧检查）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-infra-002`（musl 组件写者；避免与 ldso 任务并发改同一组件）
**可并行分片**：否
**预估**：30 min（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 3 处注释/文档措辞订正，按 1/3 中位）
**档位**：小改（注释与文档）
**状态**：已验证
**执行环境**：本地

## 背景

`ISS-486`【P3】（`m14-infra-005` 复核登记，非阻断）：两处措辞把 libc 行为归给内核。

- 任务书 `m14-infra-005` 的「新发现①」写「建议内核侧确认 `do_sigaltstack` 的 `min_ss_size`」，实际是 musl `src/signal/sigaltstack.c` 的 `sysconf(_SC_MINSIGSTKSZ)` 在用户态先拦（`MINSIGSTKSZ=2376`），内核那条轮不到；engineer 建议已撤销。
- `components/musl/patches/arch/dadao/bits/signal.h.patch` 与 `tools/infra/musl_sigframe_probe*.{py,c}` 头注释里「kernel refuses / kernel's bounds rules」同源措辞。

## 目标

把上述 3 处改为「libc 侧检查」口径；**不动判据与实现**。

## 验收（逐条贴真实 rc）

1. 3 处措辞逐条订正，`grep -rn "kernel refuses\|kernel's bounds rules"` 在允许范围内 0 命中（历史归档文件除外，逐条说明）。
2. `make build-musl` rc=0；`libc.a` 与改前 md5 相同（仅注释，产物不应变）。
3. `check-patch-tree` 的 musl 段与基线**逐行相同**（`ISS-507` KNOWN-RED 判据）；`check-component-changelog` rc=0。
4. `ISS-486` 在 `issues.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/patches/arch/dadao/bits/signal.h.patch`、`components/musl/changelog.md`（如需）、`tools/infra/musl_sigframe_probe*.{py,c}`、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改版本号；不改判据/实现；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

## 待裁定

1. **验收 2 的 md5 子句现场不可达**：musl 的 `obj/src/internal/version.h` 由 `tools/version.sh`（`git describe`）生成，补丁内容（**含注释**）一变，`apply_series` 的本地 commit hash 即变 ⇒ `version.o` 变 ⇒ `libc.a` 整档 md5 必变（实测 `175cc746`→`d332aa6c`；成员级 1346 项**仅 `version.o` 不同**；把 `version.h` 钉成同一串后两树 md5 **逐字节相同**）。建议判据改为「`crt1.o` md5 不变 + `libc.a` 成员级除 `version.o` 外逐项相同」。未擅自改判据。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 全绿（12 项，`RESULT: PASS`、rc=0）；`--inject` 两路注入红/绿闭环 rc=0；无失败项。
**修改文件**：
- `components/musl/patches/arch/dadao/bits/signal.h.patch`（libc 侧口径；同步修 hunk 计数 `+1,162`→`165`、index blob `797af17`→`e9b880c`，否则 `git apply` 静默截断）
- `tools/infra/musl_sigframe_probe.py`、`tools/infra/musl_sigframe_probe_user.c`（头注释 + Round 4 注释）
- `.tao/knowledge/issues.yaml`（ISS-486 → closed/M18/`m18-linux-010`）
- 本任务书

**验收结果**（rc 均捕被检命令自身）：
1. 3 处改完：目标 3 文件 + `issues.yaml` 的 `grep -rniE "kernel refuses|kernel's bounds rules"` **rc=1（0 命中）**。仓库级余 **4 个文件**逐条说明：历史归档 `M14/infra/m14-infra-005` 1 处（引用复核 F-b finding，历史层不改写）；本任务书 3 行（需求原文 + 本条）；`tests/unit/linux/k1_pt_probe.py:57`（PTE 缺 `SP` 是内核真拒绝）；`components/gem5/.../se_workload.cc.patch`（`RLIMIT_NPROC` 是内核真拒绝）。
2. `make build-musl JOBS=32` **rc=0**（`10/10 checks`）；`crt1.o` md5 `457aab51…` 与改前相同；`libc.a` md5 `175cc746`→`d332aa6c`，成员级 1346 项**仅 `version.o`** 不同（含 `git describe`），`version.h` 钉同串后两树 md5 相同 ⇒ 代码产物不变；见「待裁定」1 与 `control-version-o.log`。
3. `check-patch-tree` **rc=0**（11 set / 463 patches OK），musl 段与改前基线 `diff` **rc=0**；`check-component-changelog` **rc=0**（10 文件 × 4 断言）。
4. `issues.yaml` ISS-486 = `closed M18 m18-linux-010`（脚本解析核对）。
5. 本区 30 行内；状态 → `待验收`。

**新发现/坑**：① `git apply` 在 hunk 头条数小于实际 `+` 行数时**静默截断**（本次丢 `_NSIG`/`SIGUNUSED`，构建报 `_NSIG undeclared`）——改补丁注释须同步 `@@` 计数与 index blob。② musl `libc.a` 整档 md5 不是纯代码指纹（`version.o` 内嵌补丁集 commit 的 `git describe`）⇒「仅注释 ⇒ md5 不变」不成立，判产品等价须比成员。③ 任务 worktree 默认没有共享安装根/工具链（运行期目录不进版本库），需按镜像约定本地准备后再跑构建。④ 首轮注入用错 sed 大小写（`The` vs `the`）导致「注入未改文件 → g1 仍绿」，改正后红；说明注入后必须校验文件 md5 已变。

**遗留问题**：「待裁定」1（md5 子句改判）待主会话/用户裁定，其余无。


## 审阅记录

### 第 1 轮 engineer 自审

**审查方式**：自主逐行审查改动 + 现场复验（无嵌套子代理）。

**语义核对**：musl 1.2.6 源树 `src/signal/sigaltstack.c` 实测为
`size_t min = sysconf(_SC_MINSIGSTKSZ); if (!(ss_flags & SS_DISABLE) && ss_size < min) { errno = ENOMEM; return -1; }`
——3 处新措辞（用户态先拦、先于 syscall、ENOMEM）与源码一致；`get_sigframe()`
「仅当被中断 SP 已在备栈才查帧」的旧句保留（与 `m14-infra-005` 复核结论一致），未改判据/实现。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 改注释后未更新 hunk 计数，`git apply` 静默截断（丢 `_NSIG`/`SIGUNUSED`） | ✅已修 | `+1,162`→`+1,165`、index `797af17`→`e9b880c` | 截断现场：`build-after.log` `_NSIG undeclared` rc=2；修后 `run.sh` 的 `patch-hunk-line-count`=165、`patch-index-blob` 一致，`make build-musl` rc=0 |
| F2 验收 2 的「`libc.a` md5 不变」不可达（`version.o` 含补丁集 commit 的 `git describe`） | ⏸待裁定 | 未改判据；补 `control-version-o.log` 成员级 + 钉 `version.h` 对照 | 成员 diff 1346 项仅 `version.o`；钉串后两树 md5 均 `d332aa6c…` |
| F3 首轮 `--inject` 的 sed 大小写不匹配（`The`≠`the`），注入未改文件但脚本仍报「g1 绿」 | ✅已修 | sed 改用实际文本；注入后先断言文件 md5 已变 | 首轮现场 `INJECT FAIL: g1 stayed green`；修后 `--inject` rc=0，`g1` 红、`g3` 红、`restore-md5` 相等、还原回绿 |
| F4 背景 ①（`m14-infra-005` 任务书「新发现①」）未改 | ❌不修（说明） | 该文件已归档（`.tao/archive/M14/`），属历史层；验收 1 明确「历史归档文件除外」 | 归档文件保持原样；订正结论落 `issues.yaml` 关闭记录 |

**判决**：3 处目标改动完成、全部验收项有真实 rc；唯一未决是判据本身（F2，需语义裁定），不属实现缺口。


### 第 1 轮 reviewer 验收

**重跑（均本人执行，rc 取被检命令自身）**：
- 仓库根执行运行期证据目录内的 `run.sh` → **rc=0**，12 项全 PASS、`RESULT: PASS`。
- `run.sh --inject` → **rc=0**：g1 注入后 `FAIL no-phrase-in-touched-files expected=0 actual=1`、g3 注入后红、`restore-md5` 相等、还原回绿。
- **独立注入**（`cp` 备份 + 记 md5，把探针 C 头注释改回旧措辞）→ `run.sh` **rc=1**、`FAIL no-phrase-in-touched-files actual=2`、`RESULT: FAIL`；`cp` 还原 md5 相等 → 重跑 **rc=0** 回绿。
- `make build-musl JOBS=32` → **rc=0**（10/10 checks）；`libc.a` md5 `d332aa6c…`、`crt1.o` `457aab51…`（与改前同）。
- `python3 tools/infra/check_patch_tree.py` → **rc=0**；与改前基线**整档 diff rc=0**、musl 段 diff rc=0（`musl: 26 patch(es)`）；`make check-component-changelog` → **rc=0**。
- `grep -rniE "kernel refuses\|kernel's bounds rules"`（3 目标文件 + `issues.yaml`）→ **rc=1（0 命中）**；仓库级余 4 文件与完成区逐条说明一致。
- 独立 YAML 解析（全文件 181 条）→ `ISS-486 = closed / M18 / m18-linux-010`，字段齐全。

**口径核对**（逐条对照源码，非采信叙述）：
- musl `src/signal/sigaltstack.c` 实为 `size_t min = sysconf(_SC_MINSIGSTKSZ);` 不足即 `errno=ENOMEM; return -1;`，**先于** `syscall(SYS_sigaltstack,…)` ⇒ 3 处新措辞（补丁注释、探针 `.py` 头注释 + Round 4、探针 `.c` 头注释 + Round 4）与源码一致。
- 内核 `do_sigaltstack` 仅在 `ss_size < min_ss_size` 返 `-ENOMEM`，DADAO 未覆盖 `MINSIGSTKSZ`（沿用 asm-generic **2048**）⇒ 2375/2376 这条界确属 libc 侧，**内核真实行为未被写错**；`<2048` 内核仍会拒，新文案未否认。
- 补丁 hunk `+1,165`、index `e9b880c` 经 `git hash-object` 独立复算一致；探针两文件 diff **仅注释/文档字符串**，无断言值或逻辑变更。

**约束核验**：`git diff --name-only` **恰 5 文件**（与完成区声明一致）；无版本号/契约/判据改动；审前审后 `git status` 快照与 5 文件 md5 逐行相同（我的注入已 `cp`+md5 还原，未用 checkout/restore）；未提交 git。

**待裁定 1（md5 子句）— 采纳该判据订正**：独立复核成立：① 生成头确由 `tools/version.sh`（`git describe`）按补丁集 commit 生成；② 解包 `libc.a` 1346 成员，内含版本串的**只有 `version.o`**；③ 我把该生成头改为对照串重 build → `libc.a` md5 **恰等于对照树的 `b3d3b47d…`**，还原后回 `d332aa6c…`、`crt1.o` 全程 `457aab51…` ⇒ 补丁注释只经该生成头/`version.o` 影响整档 md5。故改判「`crt1.o` md5 不变 + `libc.a` 成员级除 `version.o` 外逐项相同」**成立**，记为采纳，不要求返工。

**门控 `make check-knowledge-refs`：rc=2（红，唯一失败项，与本轮审阅记录无关）**——根因是完成区「新发现/坑」③ 里的具体 `.work/**` 路径（该行写「任务 worktree 无 `<具体工作期目录>/.dadao`」），HEAD 版本 0 处、系本次完成区新增，全仓扫描仅此 1 条「具体路径不可复现」。**改法（architect 收尾直接改这一行）**：把该处改成运行期措辞（如「任务 worktree 无共享安装根/工具链软链，需本地 clone 镜像 + 软链」），改后重跑 `make check-knowledge-refs` 预期 rc=0。按「文档级小错不阻断」记 finding、不返工；其余 11 项验收与所有重跑命令均绿。

**判决：Accepted**
