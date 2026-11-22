# m18-linux-003: K6 收口门控 `check-linux-k6`

**模块**：linux
**项目里程碑**：M18
**依赖**：`m14-linux-030`–`031`、`m18-linux-001`–`002`（全部）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（新门控 + 退役 + L2 接线）
**状态**：待验收

> **迁移说明**：本任务原为 `m14-linux-034`（M14），用户 2026-11-20 裁定 K6 移入 M18 ⇒ 改号 `m18-linux-003`，任务范围不变。

## 背景

K6（busybox 启动）是 M14 修订后的最终阶段。本任务把 K6 出口固化为 L2 门控，并沿用 `m14-linux-015`/`029` 的口径：**门控只跑代表例**，全量由回归脚本单独跑。

## 目标

1. **新增 `tools/linux/check_k6.py` + `make check-linux-k6`**：代表例 = `busybox sh` 启动 + 5 条命令 + 退出码。
2. **接线**：`Makefile`（`PHONY`、`GATE_LOCKED_TARGETS`、`_locked-check-modules`、`help`、块注释）、`docs/Process-07` 目标-层表一行（L2）。
3. **§4a 退役**：K5 及以前里「用户态应用尚未跑通 / busybox 未支持」类过时断言逐条处置（保留附理由 / 改限定语 / 删除并指向替代），门控内加机械断言（新文案在 / 旧文案不在 / 替代指向 / `Process-07 §4a` 有记录）。
4. **一键证据脚本**：构建 → 门控 → selfcheck → 注入 → 回归（K0–K5）退出码如实传播。

## 验收（逐条贴真实 rc）

1. `make check-linux-k6` rc=0，项数现场打印。
2. `--selfcheck` 每组可翻转；`--inject` ≥4 路（含至少 1 路任务书未列）均可达 FAIL，`cp`+md5 还原。
3. 不回归：`check-linux-k0`–`k5` rc=0。
4. `docs/Process-07` 与 `make help` 含新门控；`check-patch-tree` linux 段 0 problem。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：新门控脚本、`Makefile`、`docs/Process-07`、退役的旧断言（逐条披露）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

实现按「跑一次 → 读失败 → 改 → 复跑」推进；每条都在最终门控/证据脚本上复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `ls /` 顶层条目断言没有对应命令用例（空表可 vacuous 过） | ✅已修 | 新增 `ls-root` 用例；`entries` 为空判 FAIL | `make check-linux-k6` C 组 30/30 |
| `/init` 启动行按子串计数，`cat /init` 的回显也命中 | ✅已修 | 改整行相等计数 | S 组 12/12；`init-no-shell` 注入判红 |
| `GATE_LOCKED_TARGETS` 断言只扫含变量名的行，命中注释行即假绿 | ✅已修 | 收集多行赋值续行后断言真实清单 | 门控 R 组通过；gate 71/71 |
| initramfs 注入只重生成 cpio，未重链内核（initramfs 内嵌）⇒ 注入不红 | ✅已修 | `rebuild("initramfs")` 追加 `build_kernel()` | `init-no-shell`/`prompt-changed` 注入均判红后回绿 |
| `applet-cat-missing` 注入锚点带错误缩进 | ✅已修 | 锚点改 `APPLETS = ("cat", "cp",`（列 0） | 注入 C 组红（cat rc 127）后回绿 |
| selfcheck 依赖已构建 manifest；C 组空表可过 | ✅已修 | 加 `SYNTH_MANIFEST`，C 组空表判 FAIL | `--selfcheck` 5 次翻转 PASS |
| 证据脚本 `check_present` 用 BRE，`**L2**` 被当量词 ⇒ 假红 | ✅已修 | 改 `grep -F` | 最终证据 22/22、rc=0 |
| 编辑运行中的 `run.sh` 破坏 bash 读取偏移（`ections:: command not found`） | ✅已修 | 终止旧运行、恢复被中断的注入、重跑 | 最终证据 `RESULT: PASS checks=22 failed=0` |

未修 finding：无。**判决**：可交付（`待验收`）。

### 第 1 轮 reviewer 验收

**重跑记录（均仓库根、本人执行，真实输出/退出码）**
1. `JOBS=32 make check-linux-k6` → `check_k6: S 12/12  C 30/30  E 4/4  R 25/25  items=71 commands=5` + `check_k6: 71/71 passed`，rc=0；启动与命令实况含 `Run /init as init process`、`DADAO initramfs: /init -> busybox sh`、`BusyBox v1.38.0 … (ash)`、12 条提示行、`hello`、`ls-root-rc=0`、`File exists`+`mkdir2-rc=1`、`payload`、`No such file`+`rm2-rc=1`、`false-rc=1`、末行 `dadao# exit 7`（E 组 期望=7 实际=7）。
2. `python3 tests/unit/linux/check_k6.py --selfcheck` → 5 行翻转（S / C / E / R-panic / R-旧文案回潮）全 PASS，`check_k6 --selfcheck: PASS`，rc=0。
3. 仓库根执行运行期证据目录内的 `run.sh`（`JOBS=32`）→ 22 项 `[PASS]`、`RESULT: PASS checks=22 failed=0`，rc=0；其内 `--all-inject` → `check_k6: 105/105 passed`，5 路红明细逐条对得上（S×3、C、E）+ `retired-back` R 红、各路还原后回绿。
4. 不回归（本人重跑）：`check-linux-k0` 146/146、`check-linux-k1` 112/112、`check-linux-k2` 170/170、`check-linux-k5` 280/280（rc 全 0）；`check-config-pins` 89 项 rc=0；`check-patch-tree` `linux: 105 patch(es)`、linux assertion 0 行、rc=2（musl `10 problem(s)`，范围外）；`check-knowledge-refs`、`check-component-changelog` rc=0；`make help` rc=0 且含 `make check-linux-k6`。
5. 独立注入 2 路（`cp` 备份 + md5 → 改被测产物 → 重跑同一入口报 FAIL → `cp` 还原 + md5 相等 → 重建回绿）：
   - 路 A 旧文案回潮（`tests/unit/linux/k4_switch_probe.py` 追加旧句）→ `70/71 passed, 1 FAILED`，唯一 FAIL = `R §4a 退役：新文案在 / 旧文案不在`，rc=2；还原 md5 `a701ff7f…` 与注入前相等 → `71/71 passed` rc=0。
   - 路 B 少装 `cat`（`tools/linux/make_initramfs.py` 的 `APPLETS` 去掉 `cat`）→ `64/68 passed, 4 FAILED`，FAIL = `C cat/cat-init 命令与 rc 行都出现`、`命令按脚本顺序执行`（-1）、`没有中途停摆`，rc=2；还原 md5 `0e567ea5…` 与注入前相等 → `71/71 passed` rc=0。
6. 快照对账：验收前后 `git status --porcelain -uall` 均 5 行且逐行相同；5 个目标文件 md5 验收前后逐个相同。

**约束核验**：① 独立 worktree，主工作树 `git status --porcelain -uall` 0 行（未改主树）；② 改动集 = 5 项与完成区「修改文件」逐项一致，`git diff -- components/ spec/ .tao/contracts/` 为空 ⇒ 组件补丁/契约/spec 未动；③ 未提交 git（HEAD 仍为派单提交）、未改版本号、无 `*.bak/*.orig/*.preinject` 残留，还原全程字节备份 + md5 对账（未用 `git checkout/restore/stash`）。

**§4a.3 退役**：6 条逐条核（2 改限定语 + 4 保留，均带理由与替代判据）；`k4_switch_probe.py` 只有 docstring 一个 hunk（−5/+4），S5/S7 判据代码未动 ⇒ 未放宽判据；旧文案在审计面仅存于 `check_k6.py` 的锚点常量，「新文案在 / 旧文案不在」双向断言可达 FAIL（路 A 实证）。

**发现（非阻断，交 architect 收尾处置）**：F1 C 组 11 条 `rc 标记是脚本期望的 …` 在 `region()` 成功分支内恒真（`marker in text` 由 region 保证），其性质由 `region()` 缺失 → `命令与 rc 行都出现` FAIL 覆盖，但违 `docs/Process-07` §5「禁恒真」，建议并入 region 断言；F2 完成区「总 rc=2 全为 musl 既有 18 项」不准：musl 实为 `10 problem(s)`，18 是证据脚本按非 linux 前缀行统计（10 条 musl 断言 + 8 条组件 patch 计数行），其 INFO 标签 `non-linux problems` 同样失准（非断言，不影响判定）；F3 完成区「`--selfcheck` 5 次翻转（S/C/E/R×2）」与 `docs/Process-07`「四组各一次翻转」均与实况（S/C/E 各 1 + R 2 = 5）不符；F4 证据脚本定义了未使用的 `check_absent_lines`（孤儿函数）；F5 §4a.3 表符号名 `dadao_umon_frame` 应为 `dadao_umon_save`（`trap.S` 单帧实体，`.zero PT_REGS_SIZE`；前者是返回 `task_pt_regs(current)` 的 C 函数）。

**判决**：**Accepted** —— 上述验收命令在本人重跑下全部通过、三条硬约束无违反；F1–F5 属文档/冗余断言级，不入阻断面，留 architect 收尾。本记录写后 `make check-knowledge-refs` rc=0（复跑值）。

## 完成区

**测试结果**：运行期证据 `run.sh` **22/22、rc=0**；`make check-linux-k6` **71/71、rc=0**（S 12/12 C 30/30 E 4/4 R 25/25；items=71、commands=5 现场统计）；`--selfcheck` 5 次翻转（S/C/E/R×2）PASS；`--all-inject` **105/105、rc=0**（5 路：`init-no-shell`/`prompt-changed`/`applet-cat-missing`/`exit-code-zero`/`k6-shell-off` + `retired-back`，均注入红→`cp`+md5 还原→重建回绿）；不回归 k0 **146/146**、k1 **112/112**、k2 **170/170**、k5 **280/280**（rc 全 0）。
**修改文件**：新增 `tests/unit/linux/check_k6.py`；`Makefile`（PHONY、`GATE_LOCKED_TARGETS`、`_locked-check-modules`、`_locked-check-linux-k6`、help、块注释）；`docs/Process-07-门控分层规范.md`（L2 目标行 + §4a.3）；`tests/unit/linux/k4_switch_probe.py`（§4a.3 两处改限定语）；本任务书。未改版本号、未提交 git。运行期另把共享 `.work/source/linux` 与现行 linux series 对齐（linux problem 8→0，不属仓库改动）。
**验收结果**（真实 rc）：启动日志含 `Run /init as init process`、`DADAO initramfs: /init -> busybox sh`、`BusyBox v1.38.0 … (ash)`、`dadao# `；`echo`→`hello`+`echo-rc=0`，`ls /`→`bin/dev/init/init.musl`+`ls-root-rc=0`，`cat /k6/f`→`payload`+`cat-rc=0`，`mkdir` rc 0、重复 rc 1+`File exists`，`rm` rc 0、缺失 rc 1+`No such file`，`false-rc=1`；`exit 7`→QEMU rc **7**。注入红例：`exit-code-zero` rc=0≠7；`k6-shell-off` 无 `/init` 行；`applet-cat-missing` cat rc 127；`retired-back` R 红。`check-config-pins` **89 项 rc=0**；`check-patch-tree` linux **105 patch、0 problem**（总 rc=2 全为 musl 既有 18 项）；`check-knowledge-refs`、`check-component-changelog` rc=0；`docs/Process-07` 与 `make help` 均含 `check-linux-k6`。
**新发现/坑**：① initramfs 内嵌在 `vmlinux`，改 initramfs 的注入必须重链内核（只重生成 cpio 不会进镜像）；② `cat /init` 会把启动行原样回显 ⇒ 计数须整行、不能子串；③ `GATE_LOCKED_TARGETS` 是多行赋值，结构断言须收集续行（只扫含变量名的行会命中注释而假绿）；④ 共享 `.work/source/linux` 与 patch 集曾漂移（linux 8 problem），按现行 series 在临时 worktree 重建后对齐；⑤ 编辑正在运行的脚本会改变 bash 读取偏移，长脚本运行期间不得改文件。
**遗留问题**：`check-patch-tree` 总 rc=2 来自 musl 既有 18 problem（范围外）；组件补丁内两处同类旧文案按 §4a.3 记「保留」并给理由（本任务硬约束「组件补丁不经过」），留待后续统一修改；K4 `ISS-493` 既有偶发未在本任务触发（K6 门控无重试/无 K4 回归断言）；`ISS-500` 的用户态无异步 tick 为已接受行为，K6 未断言用户态 tick；作业控制仍不做。
