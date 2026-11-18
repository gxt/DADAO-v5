# m14-linux-030: K6 busybox 构建接入（静态 musl + 最小 applet 集）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`（K1 启动）/`m14-infra-001`（工具链缺口矩阵）；**运行验收依赖 K5 收口**（syscall 闭环）
**可并行分片**：否（busybox 组件单写者）
**预估**：3–4 h
**档位**：中改（组件接入 + 最小 config；复核 ≥2 路注入）
**状态**：待验收

## 背景（用户 2026-11-17）

`ADR-0052` 已就地修订：M14 出口扩到 **K6（busybox 启动）**。**busybox 版本 = `1.38.0`（用户 2026-11-17 指定）**。K6 采用**静态 busybox**（不依赖 ldso），最小 applet 集 = `sh` + `ls/cat/echo/mkdir/rm/cp/mv/grep/ps`（`ps` 在无 `/proc` 时退化为打印自身/空表）。首版**不做 `/proc`、不做作业控制**。

**源码锁定**：`manifests/components.lock.toml` 新增 `[[component]] name = "busybox"`，`repository = "https://github.com/mirror/busybox.git"`、`shallow_ref = "1_38_0"`、`commit` 取该 tag 的 40 字符 commit（**不以 tag 作最终身份**）；下载源（镜像）由用户确认后填入 `[[component.source]]`。不得自行选定镜像并下载。

## 目标

1. **busybox 源与版本锁定**：按 `docs/Process-01` 以受补丁组件接入（源树 + 补丁集 + `manifests/` 锁 commit），版本号/commit 只认锁文件。
2. **最小 config**：只启用 `sh` 与上述 applet；关闭 `/proc`、作业控制、NFS、PAM 等无关项；输出 `.config` 与 applet 链接表。
3. **静态 musl 构建**：`-static`、无 `PT_INTERP`；工具链缺口（musl 缺函数/syscall 桩）逐条登记到完成区（区分 blocker / 可绕过）。
4. **构建可复现**：一条 `make` 目标（或脚本）产出 `busybox` ELF；build id/哈希记录。

## 验收（逐条贴真实 rc）

1. `busybox` 产出存在、`file`/`readelf` 显示静态（无 `PT_INTERP`、无 `PT_DYNAMIC`）。
2. applet 清单 = 约定集合（逐项 `readelf`/`busybox --list` 核对）；`busybox --version` 输出 `BusyBox v1.38.0`（版本断言）。
3. 工具链缺口逐条登记（blocker 0 才可继续；有 blocker 则写明解锁条件并 BLOCKED）。
4. 构建幂等：二次构建产物哈希一致（或给出非确定性归因）。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：busybox 组件目录/补丁集、`manifests/` 锁条目、构建脚本、本任务书。**不动** `spec/`、`.tao/contracts/`、内核补丁。
3. **不改版本号**（用户规则）。
4. 不提交 git；注入还原 `cp`+md5。

## 待裁定

**已裁定（用户 2026-11-18，原话：「busybox：1、认可；2、用官方源」）**：

1. **busybox 的源码 `repository`**：**认可**官方站 `https://git.busybox.net/busybox`（保持）。理由（2026-11-18 实测）：任务书原写的 `github.com/mirror/busybox.git` **没有 `1_38_0`**——其 tags 最新只到 `1_36_1`（`1_36_0` = `70f77e46…`，即 chipyard 子模块锁的 commit），且直连 github.com 的 `git clone` 133 s 后失败；官方站立即应答 `1_38_0 -> fc71374d…`，`--depth 1` 裸镜像克隆 86 s 成功。
2. **`[[component.source]]` 下载源**：**用官方源**，已登记 `name = "official"`、`url = "https://git.busybox.net/busybox"`（紧跟 `busybox` 条目之后）。发布 tarball 仍只作校验物（sha256 与 busybox.net 自带 `.sha256` 一致，与 git 树仅差 `.gitignore`）。

## 审阅记录

### 第 1 轮 engineer 自审

自审范围：`tools/linux/build_busybox.py`（新）、`components/busybox/**`（新）、`manifests` 条目、`Makefile`/`writer_guard.py` 接线、运行期证据脚本 `run.sh`。逐行核对了 config 生成/断言、CC wrapper 的编译/链接分支、ELF 解析、stamp 失效判定，以及证据脚本每条断言的「可达 FAIL」路径。实现过程中当场发现并修掉的 10 条（均已在最终产物上复验）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `SETTING_RE` 捕获组漏 `CONFIG_` 前缀，fragment 符号永远「未知」 | ✅已修 | 前缀在 `apply_fragment` 里补回 | `build-busybox: PASS`（`CONFIG_SH_IS_ASH` 不再报 unknown） |
| `-lm` 找不到（busybox 链接带 `-lm`） | ✅已修 | wrapper 加 `-L<musl>/lib` | 链接通过，最终 `Final link with: <none>` |
| 宿主 `strip` 读不了 DADAO ELF（`Unable to recognise the format`） | ✅已修 | `STRIP=<install-root>/llvm-strip` 并列为前置 | `build-busybox: PASS` |
| busybox `ARCH` 取 `uname -m`（宿主 x86_64）⇒ 编 x86 汇编，`### Generated` 头行汇编失败 | ✅已修 | 新补丁 `libbb/Kbuild.src.patch`（x86 目标才编）+ 构建传 `ARCH=dadao` | `check-patch-tree` 2 补丁 0 problem；构建通过 |
| `allnoconfig` 关掉 `CONFIG_BUSYBOX`/`FEATURE_VERSION` ⇒ `busybox --version/--list/sh` 全 `applet not found` | ✅已修 | `config.min` 显式打开两项 | `BusyBox v1.38.0 (…)`、`--list` 11 项、`sh -c` rc=0 |
| 上一棵树是 `base+2`（每补丁一 commit），patch-tree ⑧ 判红 | ✅已修 | 重建 checkout 走 `apply_series`（全序列一次提交） | `--source-state busybox: OK count=1 clean=True expected=1` |
| 证据脚本 C1/C6 期望串与实测串不同（误判 FAIL） | ✅已修 | 改按 rc + 明确期望短语判定 | `evidence 14/14 rc=0` |
| 证据脚本 C6b 正对照按大端解析宿主 `/bin/ls`（小端）⇒ `struct.error` | ✅已修 | 按 `e_ident[EI_DATA]` 选端序 | `C6b … actual=PT_INTERP present rc=0` |
| 证据脚本 C9 文件存在性判断极性写反（恒判失败） | ✅已修 | `[ -f f ] || ok=0`、`[ -d d1 ] \|\| ok=0` | `C9 … 9/9 rc=0` |
| `fail()` 返回 0 ⇒ 注入自检误判「C5 仍绿」 | ✅已修 | `fail` 返回 1；注入判定改为看日志 `[FAIL]` | `run.sh --inject` 7/7 rc=0 |
| 陈旧对象无守卫（换工具链仍链旧 `.o`） | ✅已修 | 新增 stamp（工具链 size/mtime + `crt1.o`/`libc.a`/片段/wrapper 摘要），失配自动 `make clean` | 首跑 `no build stamp => make clean`；二次 `build inputs unchanged (incremental)`；两次哈希同 |
| 死代码（`configure()`/`_fail()` 残留、`if False` 分支） | ✅已修 | 删除 | `python3 -c "ast.parse(...)"` + `--help` 正常 |

判决：以上全部 ✅已修且复验，无 ⏸/❌ finding ⇒ 任务状态置 `待验收`。

补充（同轮自审末两条，均已修）：
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书写「输出 `.config` 与 applet 链接表」，实现只产出 `busybox` | ✅已修 | 产物目录补 `.config` 快照 + `applets.txt`（解析 `include/applet_tables.h`，供 031 建链接） | `build-busybox: 11 applet(s): ash cat … sh`；证据 `C8b applets.txt == --list` PASS |
| 加 `applet_names()` 时误删一处换行致 `IndentationError` | ✅已修 | 复原函数体缩进 | `ast.parse` 通过 + 构建 PASS |

### 第 1 轮 reviewer 验收

**重跑（我自己的 rc，日志留运行期证据目录）**：`make build-busybox` **rc=0**（`build-busybox: PASS`、11 applet、产物 sha256 `31ee37c4…b0c9387e`）；证据脚本 `run.sh` 完整模式 **14/14 rc=0**（含 clean 重建哈希逐位一致）、`run.sh --inject` **7/7 rc=0**；`file`/`readelf` = ELF64/MSB/machine 0xDA0/静态，程序头 grep `INTERP|DYNAMIC` 计数 **0**；`qemu-dadao` 实跑 `--version` = `BusyBox v1.38.0 (2026-05-13 02:20:15 UTC)` rc=0、`--list` 11 项与 `config.min` 派生集（9 applet + ash + sh 别名）逐项相等。门控全 rc=0：`manifest-check`、`check-component-changelog`、`check-writer-guards`(27/27)、`check-no-residue`、`check-dirs`、`check-milestones-fresh`、`check-patch-tree`(**11 补丁集 / 423 补丁 OK**)、`check-source-state`(**busybox OK count=1 clean=True**)。
**下载源事实**：我重新下载官方 `busybox-1.38.0.tar.bz2` = 2695723 B、sha256 `34f9ea6f…c53bb2`，与 busybox.net 自带 `.sha256` 逐字一致；`git ls-remote` 实测 `1_38_0 → fc71374dfccd46448c62947269a35f1420d7ee28`，与锁条目、裸镜像、源树 base 三处一致。`[[component.source]]` 留空 = 任务书要求「镜像由用户确认后填入」，已列「待裁定」，**合理、不阻断**。
**独立注入（2 路，均任务书未列；只用 `cp` 备份 + md5 对账还原，md5 相等、`git status -uall` 干净）**：
- I-A：给 `tools/linux/build_busybox.py` 尾部注入语法错（`ast.parse` rc=1）⇒ `run.sh --no-idempotency` **13/13 绿 rc=0**、完整模式 **14/14 绿 rc=0**（构建已坏仍全绿）；还原后回绿 14/14。
- I-B：`components/busybox/config.min` 删 `CONFIG_LS=y` ⇒ `run.sh` **13/13 绿 rc=0**，产物与 `.config` 纹丝不动（`CONFIG_LS=y` 仍在、`--list` 仍含 `ls`）；还原后回绿 14/14。

**判决：Needs Revision**（两条阻断，均属本任务交付物）：
1. **C0 恒真 + 吞码**：`check_build` 写成 `out=$(build … | tail -2); rc=$?` ⇒ rc 是 `tail` 的（恒 0），且 `report` 两侧都写死 `build-busybox: PASS`，失败分支不可达 ⇒ 构建脚本整体坏死时两种模式仍全绿（I-A 实测）。违反「每条断言须有可达 FAIL 路径」「留证须捕获被检命令自身退出码」。**改法**：去掉管道取被检命令真 rc（或 `PIPESTATUS`），用 `build` 输出末行作 actual 与期望比对；`--inject` 增补「构建脚本坏死 ⇒ 报红」反例。
2. **`config.min` 收缩不生效 + C8 期望写死**：配置再生条件是单向 subset（fragment ⊆ `.config` 即跳过），删符号后不走 `allnoconfig`、产物不变；`C8` 期望串写死 11 项、`C5` 同为单向 ⇒ 「`--list` 与 config.min 一致」在**收缩方向无任何机械核验**（I-B 实测全绿，与验收要求「删 `CONFIG_LS` ⇒ 红」不符，也违背 README「`config.min` 是唯一真源」）。**改法**：`.config` 受管符号集与 fragment **双向相等**才跳过再生（或 fragment 变更即 `allnoconfig`）；`C8` 期望改从 `config.min` 派生或补一条 `config.min` ↔ `applets.txt` 一致性断言；`--inject` 增补该反例。
**非阻断 finding（交 architect 收尾一并改）**：① 完成区 sha256 后缀 `b774bf40` 与实测 `…b0c9387e` 不符（前缀同；门控不读该值，属笔误）；② `run.sh` C4 期望串写死 `files=2`（补丁数变动会假红，fail-closed，低危）。
**约束核验**：`$BASE..HEAD` = 任务书 + 11 文件，**无** `spec/`、`.tao/contracts/`、内核补丁改动、版本号未动；两处 L1 红均**外因**——`check-knowledge-refs` 的 2 条具体 `.work` 引用在 base `d7f9ce8d` 即存在、master `f03f88fd` 已修（我实测 master 两份他册任务书已无该引用），`check-temp-dirs` 5 个越龄目录全属他任务（本任务目录活动豁免）；未提交 git、未动主工作树。
**待裁定**（不阻断本判决）：`repository` 用官方站、`[[component.source]]` 镜像留空，需用户确认。

### 第 2 轮 engineer 返工（回应 reviewer 第 1 轮 Needs Revision）

**两条阻断：修复前后对照**（同一注入、只用 `cp` 备份 + md5 还原；日志留运行期证据目录）

| 注入 | 修复前（实测） | 修复后（实测） |
|---|---|---|
| **阻断 1**：`tools/linux/build_busybox.py` 末尾注入 `this is not python(`（`ast.parse` rc=1） | reviewer：`--no-idempotency` **13/13 绿 rc=0**、完整模式 **14/14 绿 rc=0**；我复现：**13/13 绿 rc=0**（`$?` 取的是 `tail`） | 同注入 → `--no-idempotency` **rc=1**：`[FAIL] C0 … actual=rc=1 last='SyntaxError: '(' was never closed'`（并连带 `C5` 红）；`cp` 还原（md5 `ae9dabd7…`）后该检查回绿 |
| **阻断 2**：`config.min` 删 `CONFIG_LS=y` | reviewer：13/13 绿 rc=0，`.config` 与产物纹丝不动；我复现：C5 「期望」被派生缩短成 13、C8 写死 11 仍绿 → **13/13 绿 rc=0** | 同注入 → `--no-idempotency` **rc=1**：`C0` 先按新真源重生成（`configuring … removed=['CONFIG_LS']`）⇒ 产物掉到 10 applet，`[FAIL] C8c 契约集`（实测集缺 `ls`）+ `[FAIL] C9 8/9`；`cp` 还原（md5 `d40f55c1…`）+ 重建后回 11 applet、sha256 不变。另在 `--inject` **I3** 里单独验 `C5`：`[FAIL] … STALE: fragment symbol set changed: added=none removed=['CONFIG_LS']` rc=1 |

**改动**：
- `run.sh`：新增 `capture()`（**命令落盘后单独取 `$?`**），清掉**全部**管道取码点（C0 与 C2/C3/C5/C8/C10 都曾是 `out=$(… | tail)` / 赋值后读 `PIPESTATUS`，后者的 rc 恒 0）；C0 的 actual 改取输出末行（期望 = 契约串 `build-busybox: PASS`，rc 独立）；C8 期望改由 `config.min` **现场派生**（`CONFIG_X=y`→`x`，`X_IS_Y`→两名字），另加 C8b（`applets.txt` ↔ `--list`）与 C8c（任务书约定集合）两条；C4 的 `files=N` 改为 `series` 现场计数；`--inject` 由 2 路扩到 **4 路**（新增 I3「删真源符号 ⇒ C5 红」、I4「打坏构建脚本 ⇒ C0 红」），每路都断言「红 → 还原 md5 相等 → 回绿」。
- `build_busybox.py`：`config_stale_reason()` 记录「生成该 `.config` 时的受管符号集」（产物目录 `.dadao-busybox-fragment`）并与当前 `config.min` **双向比对**（打印 added/removed），值漂移/禁用符号也判 stale；新增 `--check-config`（rc=0 当前 / rc=1 需重生成）供证据脚本断言。
- `manifests/components.lock.toml`：按用户裁定新增 `[[component.source]] name="official"`（官方站）。
- 非阻断两项：完成区 sha256 后缀改实测 `…b0c9387e`；C4 `files=N` 改现场派生。

**顺序修正**：主流程改为「先 C0 构建、再 C5 配置时效」——`C5` 判的是「`.config` 是否由当前真源生成」，在空产物目录（fresh tree / `clean-work`）上先跑会假红；先构建落定状态后 `C5` 才有定义（fresh-tree 实测：移走 `.work/build/busybox` 后 `--no-idempotency` 仍 **15/15 rc=0**、哈希不变）。真源收缩的红由 `C8c`（契约集）与 `--inject` I3（`C5`）双路保证。

**当前三档实测**：完整 **16/16 rc=0**、`--no-idempotency` **15/15 rc=0**、`--inject` **14 check rc=0**（4 路注入全红可复现）。判决：两条阻断 ✅已修并证明，无非阻断遗留 ⇒ 状态 `待验收`。


### 第 2 轮 reviewer 验收

**重跑（我自己的 rc，日志留运行期证据目录）**：证据脚本三档——完整 **16/16 rc=0**（12 s，C10 clean 重建哈希 `31ee37c4…b0c9387e` 逐位同）、`--no-idempotency` **15/15 rc=0**、`--inject` **14/14 rc=0**（I1–I4 每路「红 → `cp`+md5 还原 → 绿」，I3 具名 `removed=['CONFIG_LS']`、I4 具名 `rc=1 last='SyntaxError…'`）。取码点审计：`capture()` 自取被检命令 `$?`、各检查 `local rc=$?` 均落在无管道处，全脚本无 `| tee`/`| tail` 取码（仅读日志末行作 actual）。
**注入 A（打坏构建脚本，我自做）**：尾部注入语法错 ⇒ `--no-idempotency` **rc=1**（2 FAIL：C0、C5，具名 `SyntaxError`）、完整模式 **rc=1**（3 FAIL：C0、C5、C10）；`cp`+md5 还原（`ae9dabd7…` 相等、`git status` 干净）后回绿 16/16。**阻断 1 闭合**。
**注入 B（`config.min` 删 `CONFIG_LS=y`，我自做）**：收缩**真传进产物**——`--list` 与 `applets.txt` 由 11 → **10**（无 `ls`）、产物哈希变 `b29bf1e…`；`run.sh --no-idempotency` **rc=1**，**C8c**（契约集含 `ls`、实测缺 `ls`）与 **C9**（8/9，`ls` 冒烟失败）具名报红；C5 该路径为绿属**设计正确**（主流程先 `check_build` 物化 `.config` 再判 currency，脚本内有注释；C5 的 STALE 红路径由 `--inject` I3 独立证实 `removed=['CONFIG_LS']`）。还原后完整模式回绿 **16/16**、applet 回 **11**、哈希复原 `31ee37c4…b0c9387e`。**阻断 2 闭合**。
**fresh-tree**：移走构建产物目录后完整模式 **16/16 rc=0**、哈希不变（「15/15」= `--no-idempotency` 档计数，我实测该档恰 15 检查，非矛盾）。
**用户裁定落盘**：锁条目后确有 `[[component.source]] name="official" url="https://git.busybox.net/busybox"`；任务书「待裁定」已改**已裁定（用户 2026-11-18，原话：「busybox：1、认可；2、用官方源」）** ✔。完成区 sha256 已改实测全值 `…b0c9387e`、C4 `files=N` 已现场派生——上轮两条非阻断 finding 均闭合。
**门控（我自己的 rc）**：`manifest-check` 0（PASS）、`check-patch-tree` 0（**11 补丁集 / 423 补丁 OK**）、`check-source-state` 0（**busybox OK count=1 clean=True**）、`check-component-changelog` 0、`check-writer-guards` 0（27/27）、`check-no-residue` 0、`check-dirs` 0；`check-milestones-fresh` **rc=2**，唯一红 = **R1 `m15-testcases-016`「有 worktree 但未列入进行中/已验证表」**——该任务由 base 之后的 master 提交（`f3207910`/`d868457c`）建立、本任务 11 文件未碰台账 ⇒ **他任务外因**。
**越界**：`$BASE..HEAD` = 任务书 + 11 文件（`components/busybox/*` 6 件 + `build_busybox.py` + 锁条目 + `Makefile` + `writer_guard.py`），锁文件 diff **0 删除行**（纯新增 busybox 块）、无 `spec/`、`.tao/contracts/`、版本号改动；收尾 `git status -uall` 干净；未提交 git、未动主工作树。
**判决：Accepted**（两条阻断均经我独立注入复验闭合；最终接受仍由架构师终审）。

## 完成区

**测试结果**：全绿。证据脚本三档：完整 **16/16 rc=0**（含 clean 重建哈希一致）、`--no-idempotency` **15/15 rc=0**、`--inject` **14 check rc=0**（**4 路**真实注入：`.config` 漂移 / fragment 加虚构符号 / **fragment 删真源符号** / **打坏构建脚本**，每路均「检查红 → `cp`+md5 还原 → 回绿」）。门控：`manifest-check` PASS、`check-patch-tree` **11 补丁集 / 423 补丁 0 problem**、`--source-state busybox: OK count=1 clean=True expected=1`、`check-component-changelog` PASS、`check-writer-guards` 27/27、`check-no-residue`/`check-dirs` PASS。
**修改文件**（11）：`components/busybox/{README.md,changelog.md,config.min,series}`、`components/busybox/patches/libbb/{Kbuild.src.patch,const_hack.c.patch}`、`tools/linux/build_busybox.py`、`manifests/components.lock.toml`（`busybox` 条目 + `[[component.source]] official`）、`Makefile`（`build-busybox` 目标 + 写者表 + `GATE_LOCKED_TARGETS` + help）、`tools/infra/writer_guard.py`（`busybox` 组件登记）、本任务书。
**验收结果**（逐条真实输出）：
1. 静态：`ELF 64-bit MSB executable, *unknown arch 0xda0*, statically linked, stripped`；程序头 4 类、**无** `PT_INTERP`/`PT_DYNAMIC`（解析器另以宿主 `/bin/ls` 正对照 → `PT_INTERP present`）。
2. 版本/applet：`BusyBox v1.38.0 (2026-05-13 02:20:15 UTC)`（日期 = 锁定 commit 时间）；`--list` = `ash cat cp echo grep ls mkdir mv ps rm sh`，与 `config.min` 派生集（C8）、产物 `applets.txt`（C8b）、任务书约定集（C8c）三路逐项一致；`echo/mkdir/sh -c/ls/cat/cp/mv/grep/rm` 9 个 applet 冒烟全 rc=0 且文件效果逐项核对。产物目录含 `busybox` + `.config` + `applets.txt`。
3. 工具链缺口逐条登记（**blocker 0**）：见「新发现/坑」①–⑤，均有绕过或补丁，无 BLOCKED。
4. 幂等：clean 重建 sha256 `31ee37c4ba2cc0506395339f8d66b503a984ef96f69d1cc5e07238e5b0c9387e` 与首建逐位一致（`SOURCE_DATE_EPOCH` = 锁定 commit 时间；stamp 失配自动 `make clean`）。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。
**新发现/坑**：① DADAO clang 驱动 **freestanding**（不隐式链 libc、`--sysroot` 不提供 libc）⇒ 最终链接必须显式给 `musl/lib/crt1.o`+`libc.a`；② target sysroot 装的是 **picolibc/newlib 头**（无 musl `features.h`）⇒ musl 用户程序必须用 musl 源树 include（同 `run_suite.py` 口径）；**musl 头未装进 sysroot 属工具链缺口**（可绕过，建议后续补 install）；③ `#` 不是 DADAO 汇编注释符（`spec/Toolchain-01 §2.2`）⇒ 上游两处 `#` 注释编不过（clang 屏障模板注释、x86 手写汇编生成头行），已补丁；④ 宿主 `strip` 读不了 DADAO ELF ⇒ 必须 `llvm-strip`（`ar` 无碍）；⑤ busybox `ARCH` 默认 `uname -m`（宿主）⇒ 交叉构建必须显式 `ARCH=dadao`；⑥ `allnoconfig` 会关掉 `CONFIG_BUSYBOX`/`FEATURE_VERSION`（现象 `applet not found`），最小 config 必须显式打开；⑦ **配置复用必须双向判**（记录受管符号集）：单向 subset 下删真源符号不触发重生成，产物与真源脱钩（reviewer I-B）；⑧ **取被检命令 rc 禁经管道/赋值**：`out=$(cmd | tail)` 拿到的是 `tail` 的码，`$(…)` 后读 `PIPESTATUS` 恒 0——C0/C2/C3 都曾中招；⑨ `ps` 在 `qemu-dadao` 下读**宿主** `/proc`（FS 直通），进内核后才退化为自身/空表（032 收口）；⑩ `-j32` 日志错误行会交错，诊断须 `-j1` 复跑。
**遗留问题**：① 无返工遗留（reviewer 两条阻断 + 两条非阻断均已修并复验）；② busybox 尚未接入门控——K6 门控属 `m14-linux-034`、initramfs 集成属 `m14-linux-031`；③ `make check-milestones-fresh` 现红：`R1: m15-testcases-016: 有 worktree 但未列入「进行中」/「已验证」表`——属**他册/他任务**台账项（本任务行已在 `milestones-m14.md`「进行中」，未代改他册）；`check-knowledge-refs` 的 2 条具体 `.work/**` 引用、`check-temp-dirs` 的 5 个越龄目录同为外因；本任务未跑 L2（`check-linux-k*` 与之无交集）。
