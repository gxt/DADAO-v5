# TESTCASES-054t: `llvm-test-suite` 超时预算重标（`lua`/`XSBench`/`unix-smail`）—— 分开「真慢」与「空转」

**模块**：testcases
**项目里程碑**：M9
**依赖**：`QEMU-063t`（宿主信号/卡死根因批次，已收口；本册复核其遗留注记）、`TESTCASES-053t`（同模块改 `tools/testcases/**`，**串行**）、`TESTCASES-052t`（当前全量跑口径，`待验收`）
**状态**：已验证

> **编号（现场取号，2026-10-20）**：`testcases` 现存最大 = `TESTCASES-053t` ⇒ 取 **`054`**（编写前 `find .tao -name 'TESTCASES-054t*'` = 0 命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（主会话 2026-10-20 实测，**不要重测**；本册只按此重标 + 补两档证据）

- **`lua`（`MultiSource/Applications/lua`）**：`--timeout 3600` 下实测 **1144.64 s 跑完 PASS**，`md5(stdout+stderr+exit)` = `6badfbeedd84d040f153876007407785` == `lua.reference_output` 正文（上游 `HASH_PROGRAM_OUTPUT 1`）⇒ 现有 `CASE_TIMEOUTS["MultiSource/Applications/lua"] = 840`（`tools/testcases/run_llvm_ts_user.py:308`）**偏小**。
- **`lua` 的 840 秒来历已过时**：`CASE_TIMEOUT_BASIS`（`:320-323`）写「670.52 s 时 qemu 宿主 SIGSEGV（静态档 `bench/process.lua`）+ 120 s ⇒ 840」，`QEMU_SIGNAL_ISSUES`（`:609-611`）也指 `QEMU-063t`；该崩溃属 **`QEMU-063t` 批次（已修）**，现测 1144.64 s **跑完且无宿主信号** ⇒ 注释与条目都过时。
- **`XSBench`（`MultiSource/Benchmarks/DOE-ProxyApps-C/XSBench`）**：实测 **530.13 s 跑完 PASS**（stdout byte-exact vs `XSBench.reference_output`）⇒ **不在 `CASE_TIMEOUTS`**，吃 `DEFAULT_TIMEOUT = 300`（`:291`）⇒ 每次全量跑都误判 `blocked`（历史现场：`20261019T205339Z-llvm-ts-user-static/run.json` 记 `timeout after 300s`）。
- **对照 `mafft`**：实测 1452.82 s，表值 **1620**（`:310`）——这类是「**真慢**」，预算本来就对，**不要动**。
- **`unix-smail`（`MultiSource/Benchmarks/Prolangs-C/unix-smail`）**：`CASE_NOTES`（`:538-543`）与三处 `DEFAULT_TIMEOUT` 注释（`:229-230`、`:288-290`、`:303-305`）写「打印一行后卡死、归 `QEMU-063t`」，但最新全量跑里它 **`pass` 0.11 s**（stdout 35 B byte-exact、exit 0）⇒ 疑已随 `QEMU-063t` 修复，**须两档实测确认**。
- **成本口径（写进本册，供决策）**：重标后**每档**预计增加约 **14 分钟**（`lua` 840→1320 = +480 s = 8 min；`XSBench` 300→660 = +360 s = 6 min），换回 **2 个真 PASS**；原先 840 s 属**纯空转**（实测要 1144.64 s 才跑完），而「超时即 `blocked`」会把「能跑过」误报成「跑不过」。

## 接口规范

- **输入**：`tools/testcases/run_llvm_ts_user.py`（`CASE_TIMEOUTS` `:306-313`、`CASE_TIMEOUT_BASIS` `:316-333`、`CASE_NOTES` `:536-543`、`QEMU_SIGNAL_ISSUES` `:609-611`、`DEFAULT_TIMEOUT` 注释 `:229-230`/`:288-290`/`:303-305`）、`.dadao/tests/llvm-ts-user/**/run.json`（历史实测）、`.work/source/llvm-test-suite/**`（`reference_output`）、安装根工具链 + `qemu-dadao`。
- **输出**：
  1. `CASE_TIMEOUTS` 按公式重标：`value = ceil((实测 run_seconds + 120 s) / 60) * 60`（`lua` 1144.64 → **1320**；`XSBench` 530.13 → **660**）；`CASE_TIMEOUT_BASIS` 每条写**本次实测秒数 + 公式推导**，旧叙述删净。
  2. 过时注记清理：`QEMU_SIGNAL_ISSUES` 的 `lua` 条目、`CASE_TIMEOUT_BASIS["lua"]` 的 SIGSEGV 叙述、`CASE_NOTES[unix-smail]` 的卡死文案、三处 `DEFAULT_TIMEOUT` 注释（按第 3 条判据处置）。
  3. 两档实测证据（`--json-out` + `run.json` 路径）、证据脚本 `.work/evidence/<任务ID>/run.sh`、日志 `.work/log/testcases/TESTCASES-054t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；**不改**用例分类判据（`pass`/`fail`/`blocked`/`excluded` 语义）、**不放宽**任何 oracle/断言；不 commit/push。

## 验收标准

1. **两档实测**（`--link-mode both`、`--timeout 3600`、`--only` 单例、`--json-out` 必填）：`lua` / `XSBench` / `unix-smail` **各自两档**给出 PASS（md5 或 byte-exact oracle 命中）**或**崩溃/挂死证据（rc / 宿主信号 / 日志 / `run.json`）；**单档结论不得冒充两档**。
2. **表值重标**：`CASE_TIMEOUTS` 的 `lua` / `XSBench` 值 = 按公式现场复算的结果（实测有变则以实测为准，须写明推导）；`CASE_TIMEOUT_BASIS` 的秒数能与 `run.json` 的 `run_seconds` 对账；`mafft`/`lemon`/`SimpleMOC`/`nbench` 四条**不动**（对照）。
3. **过时注记清理（逐条给判据）**：
   - `QEMU_SIGNAL_ISSUES[".../lua"]`：本次两档实测**无**宿主信号终止 ⇒ **删**；若复现 ⇒ 保留并附证据（照实写）。
   - `CASE_TIMEOUT_BASIS[".../lua"]`：改成本次实测秒数 + 公式，**删** SIGSEGV/`QEMU-063t` 叙述。
   - `unix-smail`：两档 PASS ⇒ 删 `CASE_NOTES` 卡死段 + 改三处 `DEFAULT_TIMEOUT` 注释口径（**不入表**：0.11 s ≪ 300 s）；若仍卡死 ⇒ 保留文案 + 附本次两档实测证据（不得只凭旧结论保留）。
4. **不许把真实失败改成 pass（硬判据）**：新增/保留的 `pass` 必须 oracle 命中（`pass_reference`）；`pass_exit_only` 计数**不增**；禁删断言、禁放宽阈值、禁把 `blocked` 改标 `pass`。
5. **可达 FAIL ≥ 2**（真实输出 + `cp` + md5 还原后回绿）：
   - (a) 临时把 `lua` 表值改回 **840** ⇒ 该例 `blocked`（`timeout after 840s`）——证明表值是**有效**预算而非装饰；
   - (b) 临时删掉 `XSBench` 表项 ⇒ `timeout after 300s` 红；
   - (c) 把 `CASE_NOTES[unix-smail]` 旧文案恢复 + 一条「无 stale 卡死注记」的文本断言 ⇒ 红（若本册采用该断言）。
6. **结论可判**：逐例明确回答「**给更多时间是能跑过、还是跑不过**」，附实测秒数与 oracle 结果；不得以「加超时」掩盖真实失败（若某档确实跑不过，照实给证据，**不许**靠调大预算改判）。
7. **门控**：`make check`(L1) rc=0（含 `check-run-artifacts` / `check-tasks` / `check-knowledge-refs` / `check-no-residue`）；**不跑** L2/L3 全量（本册只改驱动预算与注释）。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 按实况回填（`ISS-266` 的 `lua` 实例是否不复现、`unix-smail` 卡死面是否闭合），**不擅自**关 issue。
9. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/TESTCASES-054t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. **长跑**：单例 `lua` 约 19 min/档、`XSBench` 约 9 min/档 ⇒ 先申报耗时、`setsid nohup` 落 `XXX_EXIT=$rc`，**不在会话内空等**；一次只跑一个、`JOBS ≤ 8`。
6. 复杂命令输出留 `.work/log/testcases/`；运行产物按 `docs/Process-08`（`--json-out` 必填、命名规矩）。
7. 失败保留现场并继续推进；只在需用户语义裁定（如两档结论冲突、是否接受某例「跑不过」）时留问。

## 完成区

**测试结果**：证据脚本 `.work/evidence/TESTCASES-054t/run.sh`（full）**0 failed / RUN_EXIT=0**（13 节全绿）；`--inject`（廉价自检）rc=0。**可达 FAIL 3 处**（真实输出）：
- (a) `lua` 表值临时 1320→840 ⇒ `klass=blocked run_seconds=840.01 run_timeout=840`、`reason` 含 `timeout after 840s`、driver rc=1；`cp`+md5 还原（`c334075b…`）后该例 **PASS**。
- (b) 删 `XSBench` 表项 ⇒ `klass=blocked run_seconds=300.0 run_timeout=300`、`timeout after 300s`、rc=1；还原后 **PASS**。
- (c) `CASE_NOTES[unix-smail]` 旧卡死文案临时恢复 ⇒ 文本断言 rc=1；还原后回绿。
**收口两档真值（默认 timeout）**：`lua` 静态 **1135.37 s** / 动态 **1150.98 s**，`run_timeout=1320`，md5 命中（`6badfbeedd84d040f153876007407785`）；`XSBench` 静态 **522.61 s** / 动态 **534.52 s**，`run_timeout=720`，stdout byte-exact；`unix-smail` 两档 **0.11 s / 0.11 s**，stdout 35 B byte-exact（`run_timeout=300`，不入表）。全部 `pass`、`oracle_kind ∈ {md5,stdout}`、`pass_exit_only=0`（全量基线 = 2，未增）。

**修改文件**：`tools/testcases/run_llvm_ts_user.py`（`CASE_TIMEOUTS`/`CASE_TIMEOUT_BASIS`/`QEMU_SIGNAL_ISSUES`/`CASE_NOTES`/三处 `DEFAULT_TIMEOUT` 注释）；本册。证据（`.work/`，gitignored）：`evidence/TESTCASES-054t/run.sh` + `results/*.json|run.log`、`log/testcases/TESTCASES-054t-run.log`。

**验收结果**：`CASE_TIMEOUTS` 改后 = lua **1320**、XSBench **720**（新增），其余四条未动（lemon 480 / SimpleMOC 480 / mafft 1620 / nbench 480），`unix-smail` 不在表；`CASE_TIMEOUT_BASIS["lua"]` = 本次实测 `1141.74 s (static) / 1167.14 s (dynamic)+120 → 1287.14 → 1320`（旧 670.52/`SIGSEGV`/`QEMU-063t` 叙述删净），`XSBench` = `533.44/541.58 → 661.58 → 720`，与册内公式逐例复算一致；`QEMU_SIGNAL_ISSUES` 已空（lua 条目删）；`CASE_NOTES[unix-smail]` 条删、三处注释改为「实测 0.11 s 完成，不入表因 ≪300 s」。门控：`make check`(L1) rc=0、`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check-run-artifacts`/`check-milestones-fresh`/`check_issues` 全 rc=0（`check_issues` 无 make 目标，直接 `python3 tools/infra/check_issues.py`）。

**新发现/坑**：① `unix-smail` 实测两档 0.11 s 跑完且 byte-exact；`QEMU-063t` 归档诊断的「`/bin/sh` 缺失 ⇒ 10×`sleep(60)` 重试」现不复现（无 600 s 等待），卡死面按实测闭合——建议主会话回填 `ISS-266`（lua 宿主 SIGSEGV 本次两档均不复现）+ `unix-smail` 卡死面。② `pass_exit_only` 是**轮级计数**（`counts`），逐例记录无此字段；断言须用 `oracle_kind` 判「非 exit-only」。③ 驱动 `--link-mode both` 会给 `--json-out` 词干追加 `-static/-dynamic`，单档不追加 ⇒ 断言取路径须两支回退。④ 中途被杀的第一版证据脚本留下**空运行目录** `.dadao/tests/llvm-ts-user/<UTC>-llvm-ts-user-static`（仅目录、无三件套）⇒ `check-run-artifacts` A2 红；`rmdir` 后回绿（进程终止即清理不完整产物）。⑤ `lua` 本次实测 1135.37/1150.98 s，比主会话测量（1141.74/1167.14）快约 6–16 s（机器抖动），预算与公式结论不变。

**遗留问题**：① `**状态**` 按本笔指令**未改**（仍 `待开始`；`check-milestones-fresh` A1 要求表行与册内状态一致，单改本册会破门控）⇒ 请 architect 在 `/complete` 时把本册 `待验收`/`已验证` 与 `milestones.md` 表行**同步**改写。② `issues.yaml` 未改（下发范围限定为驱动 + 本册）⇒ `ISS-266` 回填建议见「新发现」。③ 未跑 L2/L3（本册只动预算与注释，按册约定）。④ 未 commit/push。

## 审阅记录

#### 第 1 轮 engineer 自审
审查范围：`git diff tools/testcases/run_llvm_ts_user.py` 全 46 行改动 + 证据脚本 13 节断言。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 `assert_json`/`assert_pass_official` 只认 `<tag>-<mode>.json`，单档跑写的是 `<tag>.json` ⇒ 断言必假红 | ✅已修 | 两函数加「文件存在则用 `<tag>-<mode>`，否则 `<tag>`」回退 | full 跑第 4/6/7/8/9 节全 PASS；第 3/5 节注入态亦按同一路径取到 JSON |
| F2 依据串含 3 个浮点（实测两档 + 推导值），`len(vals)!=2` 恒假红 | ✅已修 | 取前两个浮点 `[:2]` | 第 10 节：`lua … 1141.74/1167.14 → 1287.14 → 1320 [PASS]`、`xsbench … → 720 [PASS]` |
| F3 逐例记录无 `pass_exit_only` 字段，原断言 `not c.get(...)` 恒真（假绿） | ✅已修 | 改用 `oracle_kind ∈ {md5,stdout,raw}` 判「参考 oracle」 | 第 11 节逐轮打印 `pass_exit_only=0` + `oracle_counts`；第 4/6/7/8/9 节 oracle 打印 `md5/stdout` |
| F4 第一版脚本中途被杀，残留空运行目录 ⇒ `check-run-artifacts` A2 红 | ✅已修 | `rmdir` 该空目录（无三件套、非仓库跟踪区） | `make -s check-run-artifacts` 复跑 PASS；空注入检查（注入前后 md5 比对）在脚本内生效 |
| F5 自己改动是否夹带判定逻辑（把 blocked 改 pass 的风险） | ❌不修（无此改动） | 未动 `klass`/oracle/阈值 | 证据第 12 节：diff 中 0 行命中 `klass=`/`expected_hash`/`oracle_kind=`；`pass_exit_only` 全 0；注入态仍是 `blocked` 而非 pass |

判决：findings 全部 ✅已修/❌无此改动，无未修项。**状态处置**：按本笔指令未改 `**状态**`（见「遗留问题 ①」），返回主会话由 architect 与 `milestones.md` 同步。

#### 第 1 轮 reviewer 验收
（2026-10-21，reviewer 独立重跑；workdir=仓库根、相对路径；**未改代码、未提交**；按时间纪律 `lua`/`XSBench` 长跑**未重跑**，采信 engineer 日志+JSON——见下「注入证据」）
- **静态表核验**（`python3` 导入驱动亲跑，rc=0）：`CASE_TIMEOUTS` = lemon 480 / lua **1320** / SimpleMOC 480 / XSBench **720** / mafft 1620 / nbench 480（四条对照**未动**）；`unix-smail` **不在表**；`QEMU_SIGNAL_ISSUES={}`；`CASE_NOTES` 无 unix-smail；`CASE_TIMEOUT_BASIS[lua]` 不含 `SIGSEGV|QEMU-063t|670.52`；全文 `0.11 s` ≥3 处（三处 `DEFAULT_TIMEOUT` 注释）。
- **公式复算**（亲算 rc=0）：`ceil((1167.14+120)/60)*60 = 1320`、`ceil((541.58+120)/60)*60 = 720` ⇒ 与表值一致。
- **basis 对账**：`1141.74 / 1167.14 / 533.44 / 541.58` 四数在 `.dadao/tests/llvm-ts-user/20261021T*/run.json` **全部命中**，且 `klass=pass`、`oracle=md5/stdout`、`run_timeout=3600`（主会话实测现场）。
- **秒级自验**：`--link-mode both --only '^MultiSource/Benchmarks/Prolangs-C/unix-smail$'` ⇒ **DRIVER_RC=0**，两档均 `pass run=0.11 run_timeout=300 oracle=stdout pass_exit_only=0`。
- **独立注入→FAIL→还原→回绿**（`cp`+md5，禁 git 还原）：把 `lua` 表值 1320→840（md5 `c334075b…`→`40dbe29b…`）后跑**同一** `./.work/evidence/TESTCASES-054t/run.sh --inject` ⇒ 节1 `BAD: CASE_TIMEOUTS … lua: 840`、**INJECT_RUN_EXIT=1**；`cp` 回 `driver.preinject` ⇒ md5 与注入前**逐字相等** `RESTORE_MD5_MATCH=OK`，重跑 ⇒ **GREEN_RUN_EXIT=0 ALL GREEN**。
- **L1 门控**：`make -s check` ⇒ **MAKE_CHECK_EXIT=0**（`repository checks (L1): PASS`，含 `check-run-artifacts` A1–A3、`check-tasks`、`check-knowledge-refs`、`check-no-residue`、`check_issues`）。
- **注入证据（采信日志，非重跑）**：`.work/evidence/TESTCASES-054t/results/run.log` 的 driver md5 = `c334075b…` == 当前 HEAD 该文件 md5（我亲跑 `md5sum` 比对）⇒ 日志对应现行版本；(a) `klass=blocked run_seconds=840.01 run_timeout=840`、`reason` 含 `timeout after 840s`、`driver rc=1`，还原后 PASS 1135.37 s；(b) `blocked 300.0/300`、`timeout after 300s`、rc=1，还原后 PASS 522.61 s；我另逐字段读 `results/inj-*.json` 与 `final-*.json`，数值/`oracle_kind`/`counts` 与日志及完成区**逐条一致**（lua 1135.37/1150.98 md5 `6badfbee…`、XSBench 522.61/534.52 stdout、unix-smail 0.11×2）。
- **硬判据**：`git diff 53377974..HEAD -- tools/testcases/run_llvm_ts_user.py`（46 行）中命中 `klass=|oracle_kind=|pass_exit_only=|expected_hash` 的增删行 = **0**（亲跑计数 0）；权威全量 `pass_exit_only=2` 基线未动、本册各轮均 0；无 `blocked` 改标 `pass`。
- **约束核验**：改动文件集 = 3（驱动 + 本册 + `milestones.md` 流水行/未完成块），未触 `spec/`、`contracts/`、`.tao/contracts/**`、`tests/vectors/**`、`issues.yaml`；未 `commit/push`；临时目录 `/tmp/opencode/REVIEW-054t/`；未跑 L2/L3/`install-host`。
- **留痕缺口（非阻断，交 architect）**：验收标准 8 的 `issues.yaml`（`ISS-266`）回填未做、册内已披露为「下发范围限定」并附建议；`**状态**` 与 `milestones.md` 表行同步留 `/complete`（册内遗留①）。
- **判决：Accepted** —— 上列验收项在我自己的重跑下全部通过；长跑两档依日志+JSON 采信（已显式声明）。本段仅为追加，未改完成区与既有审阅记录。

#### 提交记录（architect，2026-10-20）
- 档位：`待开始`（立册，按主会话指令正常提交）
- 提交：`f261fef`（同上分支）⇒ `master` squash `84a5231`
- 文件集对账：2 文件 = 本册（新建）+ `milestones.md`（流水行 + 未完成块）；号唯一（`find .tao -name 'TESTCASES-054t*'` 立册前 0 命中）

#### 提交记录（architect，2026-10-21，实现落盘）
- 档位：`待验收`（reviewer 尚未判决；按主会话指定信息**原样**提交、未加 `WIP:` 前缀——与立册笔同一授权口径，偏差在此披露）
- 提交：`aecd9418`（`TESTCASES-054t` 分支）
- 文件集对账：`--cached` 3 文件 = 本册（`**状态**` 待开始→待验收）+ `tools/testcases/run_llvm_ts_user.py` + `.tao/knowledge/milestones.md`（流水行状态 + 未完成块同步）⇒ 完成区「修改文件」声明的 2 项全覆盖，`milestones.md` 为主会话指定的同步项；**无漏提 / 无多提 / 无越界**（`issues.yaml` 未动，`ISS-266` 回填留 `/complete`）
- 门控：`make -s check`（L1）**rc=0**（含 `check-milestones-fresh` A1/A2/A4 26 行、`check-run-artifacts`、`check-knowledge-refs` 0 悬空、`check-no-residue`）
- 落地：`master` **squash `c3353d5e`**（分支 `74f0978b` 已删；本条留痕为纯追加，故 master 上的记录补记自身父提交 hash）

#### 提交记录（architect，2026-10-21，`/complete` 收尾）
- 档位：**正常提交**（第 1 轮 reviewer 判决 `Accepted`）
- 范围：本册 `**状态**` 待验收→**已验证**（仅改该行，完成区/审阅记录未改）；`milestones.md`（流水表行同步为 `已验证` + 倒序入表、未完成块摘除本册行、`SPEC-141t` 遗留段 C3/C4 按用户 2026-10-21 裁定改写）；`issues.yaml`（`ISS-266` 按本册验收标准 8 回填，`status` 保持 `open`）；`lessons.md`（新增 §1.55 判据）
- 文件集对账：4 文件 = 本册 + `.tao/knowledge/milestones.md` + `.tao/knowledge/issues.yaml` + `.tao/knowledge/lessons.md` ⇒ 与本笔主会话指定的「该册 + `milestones.md` + `issues.yaml` + `lessons.md`」逐项一致；**无漏提 / 无多提 / 无越界**（未触 `tools/**`、`spec/`、`contracts/`、`.tao/contracts/`、`tests/vectors/`）
- 门控：`make -s check`（L1，本笔只跑一次）**rc=0**；`python3 tools/infra/check_issues.py` **rc=0**（55 open / 33 closed，`resolved_by` 约束 OK）。
- 落地：`master` **squash `0346b29b`**（分支 `054t-complete` 上首提交 `067da98f`，已删）；本条为**纯追加**（补记自身父提交 hash + 落地号），未改完成区/既有审阅记录；**未 push**。
