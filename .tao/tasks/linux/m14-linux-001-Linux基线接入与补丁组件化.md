# m14-linux-001: Linux 基线接入与补丁组件化（`linux` 去 `patchless`）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（M14 K0 首个任务，先行；本批 Makefile 接线写者）
**可并行分片**：否（唯一改 `manifests/`、`docs/Process-01` 与 `Makefile` 的任务；单写者）
**预估**：4–5 h
**状态**：已验证

## 背景

`manifests/components.lock.toml` 的 `linux` 条目当前为 `patchless = true`，角色只是 syscall 号表参考（`ADR-0025 D1`），v5 既不构建也不打补丁。M14 起 Linux 是**内核移植目标**：基线不动（`7.2.10`，commit `7b20d05fd38de8e0be168956f6fd241d750c7d69`，`shallow_ref = v7.2.10`），但组件形态要转为受补丁组件，后续 `m14-linux-002` 才能把 `arch/dadao/**` 以树形补丁集落地。

**现状与目标的机械差距**（均已实测）：

- `tools/infra/check_patch_tree.py` 对**空 `series`** 直接报 `series is empty`（`check_patch_set` 首段）；`--source-state`/E1 断言⑧要求 `HEAD = base + 恰好 1 个 commit`，空补丁集没有可提交内容 ⇒ 必然 `base+0`。
- `tools/infra/apply_series.py` 已能对空补丁集打印 `has an empty series` 并幂等返回，无需改行为（只需确认不产生第二个 commit）。
- `components/<name>/patches/` 为空目录时 git 不跟踪；而 `check_patch_tree` 断言⑤要求 `patches/` 下每个文件都是 `<上游相对路径>.patch` ⇒ `.gitkeep` 目前会被判失败。

## 目标

1. **组件转正**：`linux` 去 `patchless`，声明 `patch_dir = "components/linux/patches"` / `patch_series = "components/linux/series"`；`role` 改为「Linux 内核移植目标 + syscall 号表参考」；`commit`/`repository`/`shallow`/`shallow_ref`/`source[]` 一律不变。
2. **建补丁集目录**：`components/linux/{README.md,changelog.md,series,patches/.gitkeep}`；`series` 为空（零条目，不写字面占位补丁）。
3. **空补丁集成为合法首态**（用户 2026-11-13 派单前提：空 series 合法首篇）：门控接受 `series` 零条目，但**只限该形态**，不得放行「有补丁未列」「非空 series 携带元数据文件」。
4. **E1 口径随补丁集条数**：空补丁集 ⇒ `HEAD == base` 且干净；非空 ⇒ `HEAD == base+1` 且净 diff == 补丁集。既有非空补丁集的断言一字不放宽。
5. **Makefile 单写者**：本任务一次性声明本批 Linux 目标名（脚本随后由各任务补），避免 `infra-001/002/003`、`linux-002` 并行改 `Makefile`。

## 范围（改哪些文件）

- `manifests/components.lock.toml`（linux 条目 + 相关注释；顺带修正「same class as linux」的过期引用）
- `components/linux/README.md`、`components/linux/changelog.md`、`components/linux/series`、`components/linux/patches/.gitkeep`
- `tools/infra/check_patch_tree.py`（空补丁集 + E1 期望条数 + 断言⑤的 `.gitkeep` 例外）
- `tools/linux/paths.py`（新建：从 `manifests/components.lock.toml` 的 `work_root` 与 `manifests/install-dirs.lock.toml` 解析Linux 源树/构建树/安装根，供本批其它任务复用；**不得**硬编码宿主路径）
- `docs/Process-01-组件补丁组织与构建编排.md`（§2 目录形态、§8 断言表与补丁集首态口径）
- `Makefile`（目标声明 + `GATE_LOCKED_TARGETS`；**仅本任务改**）
- 本任务书

## 接口规范

**组件条目（目标形态）**

```toml
[[component]]
name = "linux"
enabled = true
repository = "https://mirrors.tuna.tsinghua.edu.cn/git/linux-stable.git"
commit = "7b20d05fd38de8e0be168956f6fd241d750c7d69"
shallow = true
shallow_ref = "v7.2.10"
patch_dir = "components/linux/patches"
patch_series = "components/linux/series"
role = "Linux kernel port target (arch/dadao) + syscall numbering-table reference"
```

**空补丁集判据（三条同时成立才合法）**

1. `series` 存在且零个非注释条目；
2. `patches/` 下 `.patch` 文件数 = 0（允许且仅允许一个 `.gitkeep`）；
3. 组件条目**不是** `patchless`（`patchless` 与 `patch_dir`/`patch_series` 仍互斥）。

**E1 期望条数**：`expected = 1 if series 非空 else 0`；`git rev-list --count <base>..HEAD == expected` 且 `git status --porcelain` 为空。`--source-state` 的 linux 行须与断言⑧同一判据（不得两套）。

**Makefile 目标声明（本批固定名，脚本路径固定；此处只声明，不在本任务实现脚本）**

| 目标 | 脚本 | 读者/写者 | 锁 |
|---|---|---|---|
| `linux-defconfig` | `tools/linux/make_defconfig.py` | 写者 | 是 |
| `linux-vmlinux` | `tools/linux/make_vmlinux.py` | 写者 | 是 |
| `linux-initramfs` | `tools/linux/make_initramfs.py` | 写者 | 是 |
| `linux-semihosting-smoke` | `tools/linux/run_semihosting_smoke.py` | 写者 | 是 |
| `check-linux-toolchain` | `tools/linux/check_toolchain.py` | 读者 | 否 |
| `check-linux-boot-contract` | `tools/linux/check_boot_contract.py` | 读者 | 否 |
| `check-linux-k0` | `tools/linux/check_k0.py` | 读者 | 是（会增量构建） |

- 写者目标按 `docs/Process-07 §2` 加入 `GATE_LOCKED_TARGETS`，并按既有 `gate-locked` 机制提供对应 `_locked-<target>` 规则（模式规则可用，但**必须实测**：嵌套放行 + 独立进程互斥/超时）。
- **L1/L2 成员接线不在本任务**：`check-linux-toolchain`、`check-linux-boot-contract` 进 L1，`check-linux-k0` 进 L2，统一由 `m14-infra-003` 完成；本任务只保证目标可被 `make <target>` 调用。
- 目标被调用而脚本尚不存在（并行队友未落地）⇒ 明确的 make 报错即可，**不得**静默成功。
- **`tools/linux/paths.py` 最小 API（本批固定；仅本任务可改该文件）**：`linux_source_dir()`、`linux_build_dir()`、`linux_initramfs_dir()`、`linux_initramfs_manifest()`（= initramfs 目录下 `manifest.json`）、`toolchain_bin()`；均从 `manifests/` 解析，返回绝对 `Path` 但**不得**在任务书/文档中记录该绝对路径。下游任务只调用这些函数，不各自拼路径。

## 验收标准

1. `make manifest-check` rc=0；`grep -A12 '^name = "linux"' manifests/components.lock.toml` 显示**无** `patchless`、含 `patch_dir`/`patch_series`，`role` 为内核移植目标 + syscall 参考；`python3 tools/infra/manifest_check.py` 对 `patchless` 同时声明两字段的反例仍 FAIL（可达 FAIL，临时树注入后还原）。
2. `components/linux/series` 零条目、`patches/` 下 `.patch` 数 = 0；`make check-patch-tree` 对本任务补丁集 rc=0，输出包含 `linux` 补丁集（现场统计 `0 patches`），**不是** `patchless; skipped`；其它组件的既存红项逐条归属（须与本任务无关）。
3. `make apply-series` 连续两次 rc=0；两次都不新增 commit（linux 源树 `HEAD` 恒为 `7b20d05f…`、`rev-list --count <base>..HEAD == 0`、工作树干净），第二次打印「已应用/空补丁集」之一，**不得静默**。
4. `make check-source-state` rc=0，linux 行 `count=0 clean=True`。注入：在 linux 源树放一个未跟踪文件 ⇒ rc≠0 且点名 linux；`cp`+md5/删除还原 ⇒ rc=0。
5. **空 series 不是放行一切**（每例均须可达 FAIL）：
   - `series` 追加一行不存在的补丁路径 ⇒ `check-patch-tree` rc≠0 指名 missing；
   - `patches/` 放一个 `.patch` 但 `series` 不列 ⇒ rc≠0 指名 not listed；
   - `series` 非空时 `patches/.gitkeep` 仍在 ⇒ rc≠0（`.gitkeep` 仅空补丁集例外）。
   注入一律 `cp` 备份 + md5 对账还原，**禁** `git checkout/restore/stash`。
6. E1 非空口径未放宽：对任一既有非空补丁集（如 `qemu`）在**临时树**把期望条数改成 0/2 的两侧反例 ⇒ FAIL；本树既有补丁集的通过数与派单前基线一致（现场统计，不写死；外部红逐条归属）。
7. 文档同步：`docs/Process-01 §2/§8` 写明空补丁集首态的成立条件与 `.gitkeep` 唯一例外，并与 `check_patch_tree.py` 行为一致；`components/linux/README.md` 说明组件定位、基线、补丁集现状（首篇为空，`linux-002` 起落地）；`changelog.md` 有 `## M14` 节且符合 `check-component-changelog` 体例。
8. Makefile：7 个目标均可被 `make -n` 解析（或实际调用得到确定结果）；上表「锁=是」的 5 个目标均已纳入 `GATE_LOCKED_TARGETS` 并有对应 `_locked-*` 规则；`make check`（L1）rc=0（外部红逐条归属并记录）。
9. `tools/linux/paths.py` 在仓库内仅用相对路径/manifest 解析（不得出现宿主家目录、临时目录或仓库外绝对路径字面量）；`python3 -c 'import tools.linux.paths'`（或等价）可导入且返回信息与 `manifests/` 一致；本批其它任务只依赖该模块，不各自复制路径推导。
10. 一键证据脚本（`/tmp/opencode/<任务ID>/`，含注入→FAIL→还原→回绿）与完成区 ≤30 行、无运行期路径。

## 说明

- **授权提醒**：本任务改 `docs/Process-01`（工程流程规范）。按 `docs/Process-06 §2`，`docs/Process-*` 改动须用户事先允许并在任务书留存原话；**派单前**由主会话把授权原话落到本任务书「用户授权」段，未落纸 ⇒ BLOCKED，子代理不得代填或编造。
- 参考实现只读：`.cache/refs/DADAO-0628/components/linux/patches` 的「树形补丁集 + 一文件一补丁」阶段划分可对照，但**内容溯源，非执行必需**，不复制任何补丁/代码。
- **门控口径说明（对齐 `AGENTS.md`「门控白名单/判据只许收窄」）**：本任务不是「为凑绿放宽」，而是用户裁定的**新增合法首态**（空补丁集）。判定按「新增状态 + 同笔收紧」落地：`.gitkeep` **仅**在空 series 时合法（非空 series 出现即 FAIL）；非空补丁集的断言①–⑨与 E1（base+1）**一字不放宽**；两条 FAIL 路径均须实测。若 reviewer 认为该改动属「放宽判据」，**停并返回主会话裁定**，不得自行放行。
- 不改 Linux 源码、不写 `arch/dadao`（`linux-002`）；不引入新的 manifest 字段语义（只复用 `patch_dir`/`patch_series`）。
- 若发现 `check_patch_tree` 还有第三条路径依赖「必须 base+1」（例如 `check_commit_matches_patches` 或摘要计数），一并按「空 ⇒ 0」收口，并在完成区逐条列出。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；无法溯源的事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径；换目录用工具 workdir 参数。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash/reset --hard` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`），任务书只放结论 + 证据指针。

## 用户授权

**用户授权（2026-11-13，渠道 = 主会话问答；选项「授权这三处（推荐）」）**：用户同意本批任务修改 `spec/Machine-v5`（含只读锁）、`docs/Process-01`、`docs/Process-07` 三处；本任务按授权执行，其余 `spec/` 与 `docs/Process-*` 改动仍需逐次授权。

本任务范围：`docs/Process-01`（补丁集组织/空系列合法性一行登记）。

## 待裁定

无（实现中未出现需用户语义裁定的问题；外因红逐条归因见完成区）。

## 完成区

**测试结果**：一键证据脚本 **69/69 PASS，rc=0**（运行期证据目录 `run.sh`，未归档；内含注入→FAIL→`cp`+md5 还原→回绿）。现场：`manifest-check` rc=0；`check-patch-tree` 输出 `linux: 0 patch(es)` + `linux: empty patch set; assertions ④⑥ skipped`（**不再** `patchless; skipped`）；`check-source-state` → `linux: OK HEAD=7b20d05fd38d count=0 clean=True expected=0`；`apply-series`（linux 单组件探针）两次 rc=0，均打印 `linux has an empty series`，HEAD/count/clean 不变。

**修改文件**：`manifests/components.lock.toml`（linux 去 `patchless`、加 `patch_dir`/`patch_series`、改 `role`、重写注释；修 2 处「same class as linux」过期引用）· 新增 `components/linux/{README.md,changelog.md,series,patches/.gitkeep}` · `tools/infra/check_patch_tree.py` · 新增 `tools/linux/paths.py` · `docs/Process-01-组件补丁组织与构建编排.md`（§2/§6.1/§8/§13）· `Makefile` · 本任务书。

**验收结果**：①锁条目形态 PASS，`patchless`+`patch_dir` 反例在临时树 FAIL；②series 零条目、`.patch` 数 0、仅 `.gitkeep`；③linux 空补丁集 apply 两次 rc=0、无新 commit、非静默；④linux 行 `count=0 clean=True`，注入未跟踪文件 rc=2 点名 linux、删除后回绿；⑤三条非法形态均 rc=1（`missing` / `not listed` / `.gitkeep`；md5 还原一致）+ 隔离单元探针 0/1/1/0 errors；⑥qemu 临时树期望 0/2 两侧均 FAIL、原样 `1 patch set(s), 66 patches OK` 回绿；⑦docs/README/changelog 同步、`check-component-changelog` rc=0；⑧7 目标 `make -n` 解析出脚本、5 个进 `GATE_LOCKED_TARGETS`、脚本缺失 rc=2 明确报错、私有锁实测「独立进程拒绝」+「嵌套放行」；⑨`paths.py` 无宿主绝对路径字面量、返回值与 manifests 一致；⑩见测试结果。
- L1：`make check` rc=2，**5 项红全为外因**（逐条归因）：`check-patch-tree`（chipyard `WumingFP.scala` ⑥/⑨，m12-chipyard-030 在飞）、`check-knowledge-refs`（5 条具体运行期路径引用全在 m13-testcases-013 任务书）、`check-milestones-fresh`（R1：m13-testcases-015 有 worktree 仍在「待开始」）、`check-run-artifacts`（17 个运行期日志文件名非法，属 node-bootstrap/gem5 他任务）、`check-temp-dirs`（1 处非活动临时目录，他任务）；其余 46 目标 rc=0（含 `check_issues`、`compileall tools`）。
- `make apply-series` 全目标 rc=2：chipyard 拒绝（`HEAD c5d592c… is neither base (0acc1e1…) nor base+1 matching the patch set`），发生在 linux 之前、**无写入**；linux 侧幂等性用单组件探针实测（见测试结果）。

**新发现/坑**：①`git apply` 无参数读 stdin ⇒ 空补丁集若照跑断言④会假 FAIL，必须显式跳过并打印；②空 series 的 E1 只能是 `base+0`，且 `series` 一旦有 1 条，「`.gitkeep` 合法」与「`base+0`」同笔失效（注入实测）⇒ 判据必须收敛为一个函数（`expected_commit_count`），不得两套；③`Path.resolve()` 把共享的 `.work`/`.dadao` 软链解析到主仓绝对路径，`tools/linux/paths.py` 返回值即主仓路径（预期行为，非硬编码）；④证据脚本初版自身两处 bug（`source[]` 期望串写错、探针树缺 `manifests/*.toml`+`components/` 致回绿假红）——修后 69/69，探针树须镜像 manifest 与 components。

**遗留问题**：本任务范围无未完成项。非本任务（待主会话/归各任务处置）：chipyard、m13-testcases-013、m13-testcases-015、node-bootstrap/gem5 日志与一处非活动临时目录的外因红，随各自任务落地转绿。

## 审阅记录

### 第 1 轮 engineer 自审

**逐行审查**（`check_patch_tree.py` 全 diff、`Makefile` 新增块、`paths.py`、manifest 段、`Process-01 §2/§6.1/§8/§13`）：

- 判据单一真源：`expected_commit_count(entries)` 被断言⑧（`check_source_invariant(expected=)`）、断言⑨（自 `entries` 派生）、`--source-state`（`expected_series_commits` 读 manifest `patch_series`）共用，无第二套阈值；非空集恒 `1`（qemu 期望 0/2 两侧注入实测仍 FAIL）。
- 空集分支：仅 `series` 零条目时放开 ⑤ 的 `.gitkeep`，且要求 `parent == patches_dir`（嵌套 `.gitkeep` 仍 FAIL）；`patches/` 任何 `.patch` 仍由断言③（`not listed`）抓住；④⑥ 打印跳过而非静默。
- 边界：`patches/` 缺失时 `rglob` 空转（`manifest_check.py` 报缺目录，fail-closed）；HEAD 落后 base 时净 diff 断言仍 FAIL；`patchless` 组件路径未改（`llvm-test-suite`/`ansibench` 行为不变）。
- 输出契约：新增逐集 `N patch(es)` 行（stdout；汇总行 `N patch set(s), M patches OK` 保留）；⑧ 文案「expected exactly 1 commit」→「expected base+N」，仓内仅 M2 归档任务书引用旧文案（历史证据，无门控/脚本匹配）。
- 签名：仅 `check_source_invariant` 增关键字 `expected: int = 1`（验收④/⑥要求；默认可兼容旧调用），其余签名未变。
- `Makefile`：5 个写者/增量构建目标进 `GATE_LOCKED_TARGETS`（由既有 `gate-locked-rule` 生成锁门控，`_locked-*` 落同一块）；只读两门控不入锁；缺脚本 ⇒ python 报错 ⇒ make 非零（实测 rc=2）。
- `paths.py`：只读 `manifests/`，无宿主绝对路径字面量（脚本内 grep 实测 0 命中），复用 `tools/infra/paths.py` 取工具链 bin（DRY）。
- 防造假：证据脚本每条断言有可达 FAIL 分支（注入→非零→`cp`+md5 还原→回绿），计数现场生成（69 项），两轮实跑（首轮 2 FAIL 全为脚本自身 bug）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 `source[]` 期望串写错（`kernel/git/linux.git`）⇒ 假红 | ✅已修 | 改 `kernel/git/stable/linux.git` | 第 2 轮 `linux 条目形态` PASS |
| F2 临时树探针未镜像 `manifests/*.toml` 与 `components/` ⇒ 回绿假红 | ✅已修 | 探针树 `cp manifests/*.toml` + 软链 `components`/`tests` | 第 2 轮 `临时树还原后 manifest_check 回绿` PASS |
| F3 ⑧ 文案变更影响 M2 归档引用 | ❌不修 | — | 旧文案仅见于归档任务书（历史证据），无门控/脚本匹配；新文案更准确 |
| F4 全局 `check-patch-tree` rc=1（chipyard 2 红） | ⏸延后 | — | 外因（m12-chipyard-030 在飞），逐条归因见完成区；linux 段 0 红 |

**判决**：范围内 finding 全闭合（F3 判不修、F4 外因）⇒ 任务置「待验收」。

### 第 1 轮 reviewer 验收

**重跑（workdir=任务树，均本人执行；采信项 = 仅「m12-chipyard-030 在飞」的归属，其余全部实跑）**
- 证据脚本 `bash .work/evidence/m14-linux-001/run.sh` ⇒ **rc=0，PASS=69 FAIL=0**；跑后 7 目标 `md5sum -c` 全 OK、`git status -uall` 空、linux 源树 `7b20d05f…`/脏 0。
- `make manifest-check` rc=0；`python3 tools/infra/manifest_check.py` rc=0；`make check-component-changelog` rc=0（9 文件×4 断言=36 项）。
- `make check-source-state` rc=0：`linux: OK HEAD=7b20d05fd38d count=0 clean=True expected=0`，其余 10 行均 `expected=1 … OK`。
- `make check-patch-tree` rc=2（make Error 1）：仅 chipyard ⑨/⑥ 两红（`WumingFP.scala`）；`linux: 0 patch(es)` + `empty patch set; assertions ④⑥ skipped`，**非** `patchless; skipped`。
- `make -n` 7 目标 rc=0 全解析出 `tools/linux/*.py`；`make -p` 现场：5 个写者/增量目标在 `GATE_LOCKED_TARGETS`、2 个只读不在；`_locked-*` 5 条可解析。
- `make apply-series` rc=2（chipyard 拒绝，外因）；前后 `.work/source/*` 的 HEAD+脏项快照逐行 diff **完全一致（无写入）**；linux 单组件探针（本人自建）两次 rc=0、均打印 `linux has an empty series`、HEAD/count/脏不变。
- `make -k check`（L1）rc=2，失败目标恰 5 个：`check-patch-tree` / `check-knowledge-refs`（5 条全在 `m13-testcases-013` 任务书）/ `check-milestones-fresh`（`m13-testcases-015` 台账行）/ `check-run-artifacts`（17 个 `.work/log/{gem5,infra}` 日志名）/ `check-temp-dirs`（`/tmp/opencode/node-env`）——逐个复跑确认**均非本任务文件**。
- 与改动前 checker 对比（`git show 065b9829^:tools/infra/check_patch_tree.py` 于临时树实跑）：错误集**逐行相同**，唯一差异 = 少 `linux: series is empty`；`--source-state` 仅增 `expected=` 字段并 `linux FAIL→OK` ⇒ **非空集 `base+1` 一字未放宽**。

**独立注入（自设计、临时树 / `cp`+md5，未复用工程师用例）**
- 合成组件 `fakecomp` 11 例：空集+根 `.gitkeep` ⇒ 绿；空集+未列 `.patch` ⇒ `not listed`；空集+`README.txt` ⇒ `non-patch file`；嵌套 `.gitkeep` ⇒ FAIL；非空 series ⇒ `missing patch` + `.gitkeep 非法` + `expected base+1`（source-state `expected=1 FAIL`）；空集但源树多 1 commit ⇒ `expected base+0` FAIL；非空集停在 base ⇒ `expected base+1` FAIL；非空集正确形态 ⇒ rc=0；写坏补丁（2×`diff --git`）⇒ 断言①、不适用补丁 ⇒ 断言④；series 文件缺失 ⇒ `missing series` 且 source-state `expected=1`（fail-closed）；monkeypatch 期望 0/2 ⇒ 断言⑧ 必 FAIL。
- 真 gate 现场注入（`make check-patch-tree`，`cp`+md5 还原）：series 追加不存在补丁 ⇒ rc=2 且 missing/.gitkeep 非法/expected base+1 三红齐发，还原 md5 一致；`patches/` 放未列 `.patch` ⇒ `not listed`，还原树 md5 一致；回绿后 linux 0 红。
- `patchless`+`patch_dir` 同声明（临时树）⇒ `manifest_check` rc=1 `patchless component must not declare patch_dir/patch_series`，还原 md5 一致 rc=0。
- 各集 `N patch(es)` 与 `series` 现场行数逐一吻合（98/66/101/4/15/21/2/0/25/1），无写死值。

**约束核验**：改动 10 文件全在任务书范围；`docs/Process-01` 仅 §2/§6.1/§8/§13 四处 hunk（授权段已落原话）；完成区 7 行 ≤30；任务书无运行期绝对路径；工作树 `git status -uall` 空、7 目标 md5 与审查前一致、linux 源树未被改动、共享 `gate.lock` 空闲；未动 chipyard；未提交 git。

**判决：Accepted**（空补丁集为同笔收紧的新增首态，三条件均可达 FAIL，非空集判据实证未放宽；验收命令在我方重跑下达标，L1/apply-series 红全为外因并逐条归属）。**非阻断 finding（交 architect 收尾改，不返工）**：① `Makefile:186`/`Makefile:1238`/`check_patch_tree.py:554` 帮助文案仍写 `base+1`；② 自审 F3「仓内仅 M2 归档引用旧文案」与事实有出入（本任务书 16/150 行亦引用，描述性）；③ `tools/infra/remote.py:176` 另有一套 `expected = 1 if lines else 0` 且 series 缺失时恒 0（**本提交前既有、未改**），建议后续收口到 `expected_commit_count`；④ `make -n <gate-locked>` 会真实抢共享 `.dadao/gate.lock`（`build-qemu` 同样，既有行为，实测 18 s 取得并已释放）。
