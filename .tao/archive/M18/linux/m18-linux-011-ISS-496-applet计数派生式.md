# m18-linux-011: ISS-496 applet 计数派生式订正

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）
**可并行分片**：否
**预估**：30 min（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单点判据订正，按 1/3 中位）
**档位**：小改（单点语义）
**状态**：已验证
**执行环境**：本地

## 背景

`ISS-496`【P3】（`m18-linux-001` 复核）：`check_k6.py` 的 applet 计数派生式 `enabled - infra` 依赖 `SH_IS_ASH` 与「`sh` 无独立符号」恰好抵消；未来新增非 applet `CONFIG_*` 会使期望虚高而假红（方向安全）。处置：随下次触碰 busybox 计数判据时改为按 applet 白名单/符号表派生。

## 目标

把期望 applet 数改为直接从 `components/busybox/config.min` 的 applet 白名单（或 `applets.txt` 符号表）派生，去掉 `enabled - infra` 的抵消假设；不放宽任何 K6 判据。

## 验收（逐条贴真实 rc）

1. 计数派生式不再依赖 `SH_IS_ASH` 或「`sh` 无独立符号」假设；改后 `check-linux-k6` 计数不变（现场打印）。
2. **可达 FAIL**：在 `config.min` 注入一个非 applet 的 `CONFIG_*`（如调试符号）⇒ 旧式会假红/新式仍绿；再注入少一个 applet ⇒ 新式判红；`cp`+md5 还原后回绿。
3. `check-linux-k6` rc=0；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
4. `ISS-496` 在 `issues.yaml` 关闭（`closed_in: M18`）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/check_k6.py`、`components/busybox/config.min`（仅注入证据时临时改，还原）、`.tao/knowledge/issues.yaml`、本任务书。不改内核/其它组件。
3. 不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据 `run.sh` **23/23、rc=0**；`check_k6.py --selfcheck` rc=0；`make check-linux-k6` items=**59**（S 10/14 C 3/16 E 2/4 R 23/25）、38/59，**21 FAILED 与改前基线逐行相同**（KNOWN-RED，见遗留）；`make check` rc=2 与基线**逐字节相同**；`check-knowledge-refs` rc=0。
**修改文件**：`tests/unit/linux/check_k6.py`（applet 期望改为 `config.min` 白名单 ∩ busybox applet 表现场派生；S 组 +1 STAT +2 断言）、`.tao/knowledge/issues.yaml`（ISS-496 closed / M18 / m18-linux-011）、本任务书。未改版本号、未提交。
**验收结果**（真实 rc）：派生 `symbols=15 old_formula=12 expected=12 actual=12`，集 `ash cat cp echo grep kill ls mkdir mv ps rm sh`；注入 `CONFIG_DEBUG=y` ⇒ `old_formula=13`（旧式假红）而 `expected=12 actual=12`（新式仍绿）；删 `CONFIG_KILL=y` ⇒ 门控 S 组判红 `期望=11 实际=12` 且集差 `kill`，`cp`+md5 还原（`05fa1062…`）后回绿；门控日志 `[STAT] busybox applets from config.min: expected=12 actual=12` + 两条 `[PASS]`。
**新发现/坑**：① 仓库内 K6 门控原先**没有** applet 计数判据（`enabled - infra` 只在 `m18-linux-001` 的运行期证据脚本里），本任务把派生落到 L2 门控；② 期望取“配置真源 vs 构建产物”两端，若两侧同随 `config.min` 变（重建后）会互相抹平，故删 applet 的证据按既有 `applets.txt` 取证；③ `include/applets.h` 由 `//applet:` 注释生成、与 config 无关，`sh` 经 `SH_IS_ASH` 的 `APPLET_ODDNAME` 行成项，无抵消假设；④ 当前 master 的 K6 启动红是 `m18-linux-022/023`（内核异步新模型/异常解码扁平位图）未合入所致，与本改动无关。
**遗留问题**：`check-linux-k6` **基线即红**（21 条，改后逐行相同）：`dadao: die mode=2 code=0xef`/`unknown(0x10000000000000)`，属 M18 内核改造任务，本任务未触碰镜像；门控 items 57→59（新增 2 条更严断言），applet 计数保持 12（验收 1 的「计数不变」按 applet 计数 12 理解，若指 items 数请主会话裁定）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `enabled - infra` 式只在 `m18-linux-001` 运行期证据里，仓库门控无该判据 | ✅已修 | 在 `check_k6.py` S 组新增白名单派生 + 计数/集合断言 | `expected=12 actual=12`；删 applet 判红 |
| 期望/实际同取自 `applets.txt` 会同源自比 | ✅已修 | 期望 = `config.min` ∩ `include/applets.h`（config 无关表），实际 = 构建产物 `applets.txt` | 注入非 applet：旧式 13 假红、新式 12 绿 |
| `APPLET_ROW_RE` 须覆盖 `APPLET_ODDNAME/NOEXEC/NOFORK/SCRIPTED`；`sh` 在 ASH/HUSH 两行会重复 | ✅已修 | 正则含四前缀，名字用 set 去重 | 派生 12 名与产物逐名相等 |
| 注释含 `enabled - infra` 会让「无该式」机械检查假红 | ✅已修 | 注释改 “offset arithmetic”，证据脚本 grep 复验 | `no-offset-formula`/`no-infra-token` PASS |
| `--selfcheck` 不应依赖 busybox source/构建 | ✅已修 | 派生函数内懒加载 `build_busybox`，仅在 manifest 非空时调用 | `--selfcheck` rc=0（5 次翻转） |
| 基线 K6 红是否本任务引入 | ✅核实 | 改前后门控 FAIL 集 `diff` 为空（21=21） | `gate-failset==baseline` PASS |

未修 finding：无；**判决**：可交付（`待验收`），K6 启动 KNOWN-RED 交主会话按 m18-linux-022/023 排期。

### 第 1 轮 reviewer 验收

1. **独立复算**（reviewer 自写 python 解析，不 import 被测函数）：`symbols=15 old_formula=12 expected=12 actual=12`；期望集 == 实际集 = `ash cat cp echo grep kill ls mkdir mv ps rm sh`（逐名相等）；`sh` 来自 `SH_IS_ASH` 的 `APPLET_ODDNAME(sh, ash, …)` 行；无 applet 表行的符号恰为 `STATIC/BUSYBOX/FEATURE_VERSION`（即旧式 infra 集）；`grep -F "enabled - infra" tests/unit/linux/check_k6.py` rc=1 ⇒ 抵消式已清除，三数自洽。
2. **注入①（非 applet，两路可达 FAIL）**：加 `CONFIG_DEBUG=y` ⇒ reviewer 复算 `symbols=16 old_formula=13`（对 actual=12 假红，证明去抵消有意义）、新式 `expected=12 actual=12`；跑 `make check-linux-k6` rc=2、applet 两条 `[PASS]`、FAIL 集 md5 `4c849e3e…` 与干净态相同 ⇒ 旧式假红 / 新式保持绿。
3. **注入②（少 applet）**：删 `CONFIG_KILL=y` ⇒ 门控 rc=2 红（构建期既有判据报 `missing required applet ['kill']`）；在「未重建」态跑门控 S 组 ⇒ `expected=11 actual=12`、2 条 FAIL 带集差 `kill`（新断言可达 FAIL，reviewer 独立复现）；`cp`+md5 还原 `05fa1062…` 后终跑 applet 两条 PASS、FAIL 集 md5 复归 `4c849e3e…`（回绿）。
4. **KNOWN-RED 证实**：`git show HEAD:tests/unit/linux/check_k6.py` 换入跑同一门控 ⇒ rc=2、`items=57`、21 FAILED、无 applet 行；与改后门控 FAIL 集逐行 `diff` 为空（两侧 md5 同 `4c849e3e…`）⇒ 基线即红、与本改动无关（21 条全为内核/启动类，归 m18-linux-022/023）。
5. **判据只增不减**：`git diff --numstat tests/unit/linux/check_k6.py` = `63 0`（纯新增、0 删除）；items 57→59 = 新增计数 + 集合 2 条断言（主会话已裁定允许）。
6. **证据脚本重跑**：运行期证据目录内的 `run.sh` 跑两轮——第 1 轮 22/23，唯一 FAIL 为 `make-check==baseline`，根因是并发会话写共享运行期 qemu 源（`target/dadao/translate.c` mtime 落在该 run 窗口）+ gate-lock WAIT 行，非本任务产物；清干净后第 2 轮 `rc=0，PASS 23/0`，与 engineer `run.out` 逐字节相同（diff rc=0）。`make check` 单跑 rc=2 且与基线 md5 同 `8d2038be…`（另有 2 次重定向运行输出为空、rc=2，疑与并发相关，如实记录）。`--selfcheck` rc=0（4 组翻转 PASS）。
7. **范围与关闭字段**：`git diff --name-only` 仅任务书、`tests/unit/linux/check_k6.py`、`.tao/knowledge/issues.yaml`；ISS-496 `status: closed / closed_in: M18 / resolved_by: m18-linux-011` 齐全；`config.min` md5 还原一致；审查前后 `git status --porcelain -uall` 逐行对账一致（同 3 行）。
8. **finding（不阻断）**：① 全门控下删 applet 会先在 initramfs 构建判据报红，新断言的集差证据取自「未重建」态的 S 组（可达性已由 reviewer 独立复现）；② 证据脚本 grep 写死 `expected=12`，计数若合法变更会红（方向安全，建议改现场派生）。
9. **判决：Accepted**
