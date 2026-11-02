# TESTCASES-053t: 陈旧证据脚本族按新规重建（`ISS-270`/`ISS-273`/`ISS-282`/`ISS-288`）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`INFRA-093t`（运行产物/日志规矩 + `check-run-artifacts`，已验证）、`TESTCASES-052t`（libc-test 驱动现状，`待验收`）、`LLVM-117t`（最新工具链，`待验收`）、`INFRA-098t`（安装根 `llvm-nm`/`llvm-readelf`；本册可能需要它们取证，**按现状用构建树工具并披露**）
**状态**：已验证

> **编号（现场取号，2026-10-20）**：`testcases` 现存最大 = `TESTCASES-052t` ⇒ 取 **`053`**（编写前 `grep -rn 'TESTCASES-053' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（四条，逐条带 `file:line`）

- **`ISS-270`（驱动文案 stale）**：`tools/testcases/run_libc_test_user_suite.py:374-377` 的 `CASE_NOTES["functional/setjmp"]` 仍写「declared port gap -- sigsetjmp is not implemented」；`:1210` 在 `attribute_port_gaps()` 中**无条件** append `CASE_NOTES`（`pass` 也照打）⇒ `INFRA-089t` 已实现 `sigsetjmp` 后仍打印旧根因，与真实状态矛盾。
- **`ISS-273`（`LLVM-098t` 证据脚本过时）**：`.work/evidence/LLVM-098t/run.sh:176` 的 S9 静态基线（取自 `.work/evidence/INFRA-085t/baseline`）与 `:186-234` 的 S10「XFAIL：`libc.so` 链接必须失败（22 errors = 6 ABS48 + 16 undefined）」已被现工具链推翻（`LLVM-117t` 现场 `make build-musl-shared` rc=0）⇒ 期望与实际反向，脚本 default 5 FAIL / 注入段亦受影响。
- **`ISS-282`（`INFRA-093t` 验收三项遗留）**：① 子集跑（`--filter`）写 `authoritative/` 只有文档约束（`docs/Process-08 §1.2`「由调用者负责选择」）；② `tools/infra/check_run_artifacts.py:162-185` 的 `_meta_problems()` 只校验 `command`/`started_utc`/`toolchain.{clang,qemu,libc}`，**不校验 `finished_utc`**（文档 `§1.1` 要求）；③ `:57-60` 的 `INFLIGHT_LEGACY`（`^llvm-ts-user-.*`）过渡豁免须在 `.work/log/testcases/` 搬迁完成后删除——**搬迁未做**（`ISS-278`「另起一笔」）。
- **`ISS-288`（`LLVM-111t` 基线随 `Align(16)` 失效）**：`.work/evidence/LLVM-111t/run.sh:147` 把 `$BASE/P3.s` 列为前提、`:167-168` 断言 `P3-asm-identical`，而现 `.work/evidence/LLVM-111t/baseline/` **只有 `P3.out`**（`P3.s` 已不存在）⇒ 前提即缺；`ISS-288` 记录的差异 = `Align(16)` 后帧大小 `-24→-32` 等**合法**变化，P3 stdout 语义一致（`cmp` rc=0）。
- **共同性质**：四者均为**历史证据脚本/文案随世界变化而 stale**，**非产品缺陷**；判据口径 = `docs/Process-08`（运行产物三件套 / 命名 / 权威跑）+ `AGENTS.md`「验证脚本反例门控」（**必须能失败**；禁恒真、禁「两支写同一结果」）。

## 接口规范

- **输入**：`tools/testcases/run_libc_test_user_suite.py`（`:374-377`、`:1197-1212`）、`tools/infra/check_run_artifacts.py`（`:57-60`、`:162-185`、`:208+`）、`docs/Process-08`、`.work/evidence/{LLVM-098t,LLVM-111t}/**`（**不入 git**）、现有 `.work/log/testcases/**` 存量。
- **输出**（逐条，**修 / 按新规重建 / 有据登记** 三选一，**不得放宽**）：
  1. `ISS-270`：驱动 note 改为「已由 `INFRA-089t` 实现（`src/signal/dadao/sigsetjmp.s`）」或删除；且 `pass` 不再带 port-gap note（顺序/条件修）；
  2. `ISS-273`：S10 期望改「`libc.so` rc=0 且产物非空」+ **保留可达 FAIL**（注入 `-fno-pic`/损坏对象 ⇒ 红）；S9 基线按**当前**工具链刷新（同源同名口径）或改语义断言 + 注入；
  3. `ISS-282①`：驱动在 `--filter`/`--only`/`--limit` 与 `--work-dir` 指向 `authoritative/` 同时出现时**显式拒绝**（rc≠0 + 提示）；② `_meta_problems()` 增 `finished_utc` 非空校验 + `--self-test` 新注入；③ 搬迁未做 ⇒ **不删**豁免，给「搬迁完成后删除」的机械判据与登记（不得借此放宽其它断言）；
  4. `ISS-288`：`baseline/P3.s` 按当前工具链重生成（或明确改为语义断言）；**不得**只删 `P3-asm-identical`；`P3-stdout-identical` 保留为语义 oracle；
  5. 证据脚本（本册自证）`.work/evidence/<任务ID>/run.sh` + 日志 `.work/log/testcases/TESTCASES-053t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；不改用例分类（`pass`/`fail`/`blocked` 语义）；`.work/evidence/**` 不入 git ⇒ 可提交面 = 驱动/门控/文档 + 台账；不 commit/push。

## 验收标准

1. **四条逐条闭合**：每条给出「处置 + 依据 + 修前/修后真实输出」；`ISS-270/273/288` 的脚本 default **0 FAIL**；`ISS-282` 的 ①② 已实现（③ 有机械登记）。
2. **不许放宽（硬判据）**：每条被替换/更新的断言都必须**保留一条可达 FAIL 路径**（注入 → 红 → 还原 → 绿），并给出**真实**输出；仅删断言 / 改期望迎合现状（如把 XFAIL 改成「忽略」）⇒ 判 FAIL；`check-run-artifacts --self-test` 全绿且**新增注入各可达 FAIL**。
3. **`ISS-270` 语义**：`functional/setjmp` 单例跑（`--filter` + `--json-out` 落 `/tmp`）⇒ 报告中不含旧根因 note；把 `CASE_NOTES` 临时改回旧文案（`cp` 备份）⇒ 断言红；还原后绿。
4. **`ISS-282①` 机械判**：`--filter` + `--work-dir .work/tests/authoritative/...` ⇒ 驱动 **rc≠0** 且不创建运行目录；正常 `--filter` + `/tmp` work-dir ⇒ rc=0；去掉 guard（临时树）⇒ 组合跑 rc=0（证明断言可失败）。
5. **`ISS-282②` 机械判**：构造一个缺 `finished_utc` 的 `meta.json`（临时树）⇒ `check-run-artifacts` 红；补齐 ⇒ 绿；`--self-test` 覆盖该注入。
6. **`ISS-273`/`ISS-288` 基线口径**：刷新后的基线必须与「同源同参数重跑」逐字节一致（脚本内可重生成校验），并用一次注入证明能失败（如 `-O0`/`-fno-pic`/改源 ⇒ 红）。
7. **证据组织**：本册运行产物遵循 `docs/Process-08`（`.work/tests/**` 三件套、日志命名 `check-*.log` / `<任务号>-<用途>.log`、`--json-out` 必填）；`make check-run-artifacts` rc=0。
8. **门控**：`make check`(L1) rc=0；`check-tasks` / `check-knowledge-refs` / `check-no-residue` rc=0；不跑 L2/L3 全量（本册不改语义实现；单例跑属证据）。
9. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml`：`ISS-270`/`ISS-273`/`ISS-288` 与 `ISS-282` 的 ①② 按实况回填（`closed` 或「保留 open + 剩余项」；③ 保持 open 并注记搬迁前置）。
10. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-053t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账；`.work/evidence/**` 亦遵守）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（是否接受某证据脚本「有据登记、不修」；是否启动 `.work/log/testcases/` 搬迁）时留问。
6. 复杂命令输出留 `.work/log/testcases/`；单例跑用 `--filter` + 显式 `--json-out`。

## 完成区

**测试结果**：`./.work/evidence/TESTCASES-053t/run.sh --with-gates` rc=0（35/35 CHECK rc=0）；L1 `make check` rc=0、L2 `make check-modules` rc=0（日志 `.work/log/testcases/TESTCASES-053t-{l1,l2,evidence}.log`）；`check-run-artifacts --self-test` 6/6 PASS。
**修改文件**：`tools/testcases/run_artifacts.py`、`run_libc_test_user_suite.py`、`run_llvm_ts_user.py`、`tools/infra/check_run_artifacts.py`、`docs/Process-08-…md`、`.tao/knowledge/{issues.yaml,milestones.md}`、本册；证据目录不入 git：`.work/evidence/{LLVM-098t,LLVM-111t,TESTCASES-053t}/**`。
**验收结果**：
- `ISS-270` 修前：`--filter ^functional/setjmp$` 报告 `PASS functional/setjmp` 同时打印「sigsetjmp is not implemented」（`/tmp/opencode/TESTCASES-053t/setjmp-before.log:10-11`）；修后同命令无该 note（`setjmp-green.json` notes=[]）。两处根因：删 `CASE_NOTES` 旧条目 + `attribute_port_gaps()` 对 `pass` 早退。注入（旧条目+去早退）⇒ 断言红；`cp`+md5 还原 ⇒ 绿。
- `ISS-273` 修前：098t default 27 PASS/6 FAIL（S9 基线 size 75336 vs 79784、S10 四条 XFAIL 反向、S7「6 条 .text ABS48」）；修后 35 PASS/0 FAIL。S9 改「同源同参数当前工具链基线逐字节一致」（`--regen` 双次一致，sha256 `0d5623…a13a`）；S10 改 rc=0+产物非空+ET_DYN+无 `-fPIC` 错+确实发生链接（先删受管产物，测后 `cp` 还原）；S7 改契约不变式「0 非可写段 ABS48/≥1 可写」。
- `ISS-282①`：`--filter`+`.work/tests/authoritative` ⇒ rc=2 且目录数不变（6→6），llvm-ts `--only` 同；去掉 guard（monkeypatch）⇒ rc=0 且把运行目录写进 `authoritative/`（断言可达 FAIL）。② `_meta_problems()` 增 `finished_utc`；临时树缺字段 ⇒ rc=1 并报 `missing finished_utc`，补齐 ⇒ rc=0；`--self-test` 新增该注入。③ 搬迁未做 ⇒ 不删豁免；新增 `--legacy-status`（现 rc=1，26 个 `llvm-ts-user-*` 仍在），rc=0 即删除判据。
- `ISS-288` 修前：111t `P3-asm-identical` FAIL（其余绿）；修后 22/22 rc=0。基线按当前工具链 `--regen` 重生成（差异仅 `Align(16)` 帧大小与 `shl.uo→shl.o`），`P3.out`/`P3-stdout-identical` 保留为语义 oracle；`--inject` 1 字节翻转 ⇒ 红。
- 覆盖披露：用例分类 0 增 0 删；判定类断言改：098t S7/S9/S10 与 111t P3 基线（替换+刷新）；新增可达 FAIL 注入 10 条、gate 注入 1 条；驱动行为改动仅「拒子集写 authoritative」与「pass 不带 note」。
**新发现/坑**：① S7 同族 stale（`dlstart.lo` 现为 `REL26`+`.got` ABS48），旧「6 条 .text」只是代码生成快照，一并修；② `make lib/libc.so` 用 musl Makefile 自身 flags（无 DT_SONAME），会覆盖 `build_musl.py` 的受管产物 ⇒ S10 加 `cp` 备份/还原+EXIT trap（曾把 L1 `check-musl-freshness` 弄红，已用安装副本恢复并复验）；③ 「逐字节基线」= 编译器版本快照，跨工具链改动必须显式 `--regen` 且双次一致；④ `check-milestones-fresh` 要求 `待验收` 行保留登记时间并带 `（登记）`。
**遗留问题**：`ISS-282③` 搬迁未做（保持 open；判据 `--legacy-status`）；未 commit/push（提交归 architect）。

## 审阅记录

#### 第 1 轮 engineer 自审

**逐行审查**（两驱动 / `run_artifacts` / gate / 两份证据脚本）：guard 在任何 `makedirs` 之前 rc=2；`is_authoritative_root` 按路径组件精确匹配（不误伤 `xxx-authoritative`）；`attribute_port_gaps` 早退只影响 note、不改 klass；`legacy_status` 无 `.work/log` 时为空集=rc=0，与「可删除」语义一致；证据脚本全部 `cp`+md5 还原并带 `trap EXIT` 兜底，rc 直接捕获、无 `| tee`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 098t S10 重建覆盖受管 libc.so（L1 freshness 红） | ✅已修 | S10 `cp` 备份+测后还原+EXIT trap；注入段同 | `check-musl-freshness` PASS；再跑 098t 后两副本 sha256 均 `c69f…` |
| 098t 脚本缺 `check_eq/check_ne/md5`（inject iii 全 `command not found`） | ✅已修 | 顶部补 3 个 helper | `--inject iii` 全部 rc=0 |
| 证据脚本 green 断言方向反（`json_note` 返回 1 = 无 note） | ✅已修 | expect `0`→`1` | `no stale note ... expect=1 actual=1 rc=0` |
| 证据脚本注入计数把 work-dir 子目录算进去（4≠1） | ✅已修 | 只数运行目录 `-name '2*T*Z-*'` | `writes authoritative/ ... expect=1 actual=1 rc=0` |
| `check-milestones-fresh` 4 项（状态/长度/次序/登记注） | ✅已修 | 任务书状态→`待验收`；流水行 110 字、保留登记时间、排到表尾 | `make check` rc=0 |
| 098t S7 旧断言 stale（同族） | ✅已修 | 改契约不变式；旧期望 `--expect-nonwritable 6` 作为可达 FAIL | default 0 FAIL；旧期望 rc=1 |
| 证据脚本 grep 与 `PASS name (expected=…)` 格式不符 | ✅已修 | 改 `grep -qF` 全行前缀 | evidence final rc=0 |

**判决**：全部 finding 已修，状态置 `待验收`。


#### 第 1 轮 reviewer 验收

**重跑（本人执行；rc = 被检命令自身，未用管道取码）**：证据脚本 `./.work/evidence/TESTCASES-053t/run.sh` rc=0 / 33 CHECK / `rc=1` 计 0（另 2 条门控 CHECK ⇒ 35），末态复跑仍 rc=0。
- `ISS-270`：`--filter ^functional/setjmp$ --json-out /tmp/…` rc=0；`grep -c 'sigsetjmp is not implemented'`=0；JSON `klass=pass notes=[]`。
- `ISS-282`：① libc `--filter` / llvm-ts `--only` / `--limit` 三路指 `.work/tests/authoritative` ⇒ 均 rc=2、目录数 6→6；② 临时树缺 `finished_utc` ⇒ rc=1 + `meta.json: missing finished_utc`，空串亦红，补回 rc=0，`--self-test` rc=0（含 `A2 missing finished_utc … PASS`）；③ `--legacy-status` rc=1、26 个 `llvm-ts-user-*` 在 ⇒ 豁免保留属实，**只记录、不参与门控**。
- `ISS-273`：098t default 35 PASS/0 FAIL；`--regen` 两次构建逐字节一致且基线 md5 不变（sha256 `0d5623…a13a` = 当前工具链真值）；S10 实测 rc=0/size=1157888/DYN/link-lines=1/pic-err=0。
- `ISS-288`：111t default 22/22；`--regen` 双次一致、基线 md5 `e317ff…` 不变；`P3-asm-identical` 保留且 `P3-stdout-identical` 语义 oracle 在断言（`P3.out` 仍是 10-19 原件，未随新输出改写）。
- 门控：L1 `make check` rc=0（`check-musl-freshness`/`check-run-artifacts`/`check-no-residue` PASS）；L2 `make check-modules` rc=0。

**独立注入（`cp` + md5，红→还原→绿）**：① `static/musl_smoke.c` 加符号 ⇒ S9 现编译 cmp rc=1，还原 md5 `1e000d…` ⇒ rc=0；② `strlen.lo` 置垃圾 ⇒ `make lib/libc.so` rc=2（S10 可红），还原 md5 `1fc442…` ⇒ rc=0、受管 libc.so `9d7178…` 复原；③ 改 `P3.c` ⇒ `P3-asm-identical` cmp rc=1，还原 md5 `5377ef…` ⇒ rc=0；④ S7 新不变式对事故形状 `stale/math_atan2f.lo` 红（`|0|4`）、对现 `dlstart.lo` 绿 ⇒ 仍抓错。

**约束核验**：未触 `spec/`/`contracts/`/`tests/vectors/**`；`git status --porcelain -uall` 审前审后皆空，7 个已跟踪文件 + 3 个基线/产物 md5 与审前快照逐一相同；用例分类 0 增 0 删（驱动仅删 1 条 `CASE_NOTES` 旧条目 + `pass` 早退 + guard，早退不改 klass、notes 只入报告）；证据脚本无 `| tee` 吞码、注入全用 `cp`+md5。

**判决：Accepted**。备注（非阻断）：S9 为「同源同参数 + 持久化基线」快照口径——非自比（fresh build vs 落盘基线）、我方独立注入可红，但跨工具链变更须显式 `--regen` 才更新，脚本注释与 `baseline/README.md` 已记录；完成区「修前 27P/6F」与 `issues.yaml` 登记的「25P/8F」不一致，`.work/evidence/**` 不入 git 无从回放，仅记口径差异。
