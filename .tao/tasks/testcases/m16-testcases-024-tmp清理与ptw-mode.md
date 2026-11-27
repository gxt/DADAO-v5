# m16-testcases-024: `tests/arch` 收尾二（临时目录清理 + `check_ptw_rtl --mode`）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-021`、`m16-testcases-022` 已合入
**可并行分片**：否（共享 `tests/arch/ptw/`、运行期证据脚本）
**预估**：1–1.5 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景

- `ISS-m16-007`：`m16-testcases-021` 证据脚本 `checks.py` 的 `a5`/`a8` 用 `tempfile.mkdtemp(dir=TMP)` 且**从不清理**；每次 `run.sh` 在运行期临时目录遗留约 300 MiB（A8 注入态 `flood.bin`），4 次全量后 952 MiB（`/tmp` 曾 82%）。
- `ISS-m16-010`：`tests/arch/ptw/check_ptw_rtl.py` **缺 `--mode`**，而 `modes.yaml` 声明 ptw 三模式 ⇒ `run_arch --cfx 4 --platforms chipyard` 15/15 报 `unrecognized arguments: --mode`（rc=1）；另外单平台 `run_arch`（只给 `--platforms chipyard`）会对未跑的 QEMU/gem5 腿报假"跨平台不一致"。

## 要做

1. **临时目录清理**：`checks.py` 的每个 `mkdtemp` 在断言完成/注入还原后 `shutil.rmtree`（异常路径也要清）；跑 4 次全量后临时目录残留应 ≈0；保留失败现场的开关（如 `KEEP_TMP=1`）并写进 README。
2. **`check_ptw_rtl --mode`**：接受 `--mode hmon|smon|umon`（与 `check_cache_rtl`/`check_hart_rtl` 同接口），按模式选择 `modes.yaml` 的 `cfx_access`；三模式均能跑（RTL 的 cfx4 若仍只 hmon，按 `DIV-09` 显式排除并给原因，不得静默）。
3. **单平台假不一致**：`run_arch.py` 在只给一个平台时，不应把未跑的腿当作"不一致"（按 `ISS-m16-010` 的记录，`ref` 空集导致 `ref_ok` 恒 false）；改为显式"单平台模式：仅本平台对照 expected"，或要求至少两平台。
4. **不回归**：`run_arch --cfx 4 --platforms qemu,gem5,chipyard` 恢复 rc=0（或按 gap 登记）；`check_ptw_rtl --selfcheck` 集合不变；`arch-cache/time/hart/pmem` 代表集不回归。

5. **证据脚本的健壮性（`m16-testcases-023` 复核 finding）**：① `run.sh` 的 `[ -x "$GEM5" ]` 只验可执行位，拦不住"可执行但截断的非 ELF"（22:57 曾出现 41.8 MB 半成品）⇒ 加 `file`/ELF magic 校验；② flake 重试计数会把"注入导致的 rc=77"也算成重试 ⇒ 重试只统计非注入轮；③ inventory 的收口注槽数（13→11）与现场核对后订正。

## 不做

- 不改 RTL/用例语义；
- 不修 `ISS-m16-011`（flake，另任务）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/**`、`tools/testcases/arch/**`、运行期证据脚本、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 4 次全量后临时目录残留 ≈0（贴 `du` 前后）；
2. `run_arch --cfx 4 --platforms chipyard --mode {hmon,smon,umon}` 不再报 `--mode` 未知；三平台 `--cfx 4` rc=0 或 gap 登记；
3. **可达 FAIL ≥2**：注入"mkdtemp 不清理"、"把 `--mode` 去掉" ⇒ 红；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **58 PASS / 0 FAIL，rc=0**，flake 重试 0。分节：A 15、B 25、C 12、D 7、E 2。A 段 4 次全量每次 18 PASS；E 段 `failures=[] cases=14 GAP=['arch-ptw-015']`。E 首次运行遇共享 gem5 被其它会话 scons 重建（41.8 MB 非 ELF，`ISS-m16-011`），记环境事件后用完整构建（md5 `24d41d4f…`）重跑，最终 flake=0。
**修改文件**：仓库 `tests/arch/ptw/check_ptw_rtl.py`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、新增 `tests/arch/common/gem5bin.py`、`tests/arch/README.md`、`tests/arch/ptw/README.md`、`tests/arch/vast-arch-inventory.md`、本任务书；运行期（gitignored）`m16-testcases-021/checks.py`+新增 `README.md`、`m16-testcases-023/run.sh`、本任务 `run.sh`。
**验收结果**：① 临时目录：修前历史遗留 **58,201,300 B / 64 目录**，修后 4 次全量 **0 B / 0 目录**；`KEEP_TMP=1` 保留 1 目录；注入「不清理」⇒ 残留 1 目录被检出，`cp`+md5（`fe46db45…`）还原回绿。② `--mode`：`--selfcheck` rc=0 且声明 DIV-09；直接 smon/umon rc=77+DIV-09；`run_arch --cfx 4 --platforms chipyard --mode {smon,umon}` rc=0、14/14 GAP；hmon 单例 002 PASS 3 槽；三平台全量 rc=0。③ 单平台：qemu/chipyard rc=0、显式「单平台模式」、无「跨平台不一致」；多平台 GAP 的 `ref` 空集不再假红。④ GEM5：真实 gem5 rc=0；4 KiB 截断 ELF（节头表越界）与非 ELF 可执行文件均 rc=1；023 `run.sh` 已接入；`retryable` 对 77/2 不重试、对 1/139 可重试。⑤ 门控 rc 全 0：`run_arch --self-test`/`check-tests-index`/`check-tasks`/`check-knowledge-refs`/`check_issues`；cache/time/hart/pmem 代表集 8 条（现场派生）rc=0。⑥ inventory 注 = 现场 11（13 → 11）。
**新发现/坑**：① argparse 长选项前缀缩写：`--mode` 是 `--mode-disabled` 的前缀 ⇒ 注入改名无效，须用不共享前缀的名字（`--rtl-mode`）。② 共享 gem5 又因并发重建变成 41.8 MB 非 ELF（可执行位仍在）⇒ `[ -x ]` 必漏；`gem5bin.py` 的 magic+节头表可拦，`GEM5=` 覆盖可绕行。③ 单平台 GAP 旧判据在 `ref` 空集时 `ref_ok` 恒 false；已改显式单平台模式 + 空 ref 兜底。④ 023 inventory 注原写「10 → 8」，现场实为 13 → 11。
**遗留问题**：ISS-m16-007/010 的 issue 状态待 architect 收尾（本任务范围不含 `issues-*.yaml`）；ISS-m16-011（flake）仍 open，按批次由 030 承接；cfx4 的 S/U 仍按 `DIV-09` 记 GAP，待 cfx4 `<mode>` 行落地后删该分支。

## 审阅记录

### 第 1 轮 engineer 自审

范围：7 个仓库文件 diff + 3 个运行期脚本；`run.sh` 实跑 4 次（2 次因自身 bug/环境重跑），最终 58/0。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 注入「去掉 --mode」改名成 `--mode-disabled` 仍被 argparse 前缀缩写接受 | ✅已修 | 注入改为不共享前缀的 `--rtl-mode`（保留 dest=mode） | B6 rc=1、B6b 日志含 `unrecognized arguments: --mode`；md5 还原相等 |
| F2 单平台 GAP 时 `ref` 空集让 `ref_ok` 恒 false | ✅已修 | `run_arch` 显式单平台分支（仅对照 expected）+ 空 ref 兜底 | B3 chipyard smon/umon rc=0、14/14 GAP、无假不一致；C1 qemu rc=0 |
| F3 selfcheck 在模式登记有问题时仍打印 PASS 行 | ✅已修 | 用 `mode_before` 判定 PASS/FAIL | `--selfcheck` rc=0；注入缺 DIV-09/模式不可达路径由同块 problems 记 FAIL |
| F4 `list_plan` 尾巴重复 `return 0` | ✅已修 | 删重复行 | `py_compile` + 最终全量 E 段跑过 `--list` 同一文件 |
| F5 E 段遇共享 gem5 被并发重建（非 ELF）时无绕行开关 | ✅已修 | 证据脚本支持 `GEM5/GEM5CFG` 覆盖；023 接入 `gem5bin.py` | C2 真实 rc=0、截断/非 ELF 均 rc=1；E 用完整构建（md5 `24d41d4f…`）rc=0 |
| F6 023 flake 计数把注入 rc=77 当重试 | ✅已修 | `retryable()` 只收 1/信号类/超时；`NO_RETRY=1` 可关 | C3/C3b rc=77/2 不重试、C3c/C3d 可重试；最终 flake=0 |
| F7 `mkdtemp` 异常路径清理只在 atexit，断言失败也不留现场说明 | ✅已修 | `scratch()` contextmanager `finally` 清理 + `KEEP_TMP` 打印路径 | A2 4 次后 0 目录；A3 KEEP_TMP 保留 1；A4 注入残留被检出、md5 还原 |
| F8 inventory 槽数注「10 → 8」与现场不符 | ✅已修 | 改「13 → 11」并由 gen 现场总槽断言 | C4 现场 11、注 13 → 11、旧值 0 命中 |
| F9 `--mode` 的 `cfx_access` 语义未说明 | ✅已修 | `ptw/README` 说明 cfx_access 只用于 QEMU/gem5 权限准备，RTL cfx4 由 DIV-09 排除 | 文档 diff；`--selfcheck` 仍 rc=0 |
| F10 单模式 RTL 承载注释过时 | ✅已修 | `platform.py` 注释改为 cfx4 收 --mode 但只出 hmon | 注释 diff；E 段 chipyard 腿全过 |

判决：F1–F10 全部已修并复验，最终 `run.sh` 58 PASS / 0 FAIL / rc=0 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收（自己重跑，以退出码为准，不采信完成区）

1. **证据脚本重跑**：运行期证据目录内的 `run.sh`（`FULL=1`）⇒ **rc=0，58 PASS / 0 FAIL，flake 0**；`FULL=0` 注入轮 ⇒ rc=1；`cp`+md5 还原后同脚本 `FULL=0` ⇒ **rc=0，56 PASS / 0 FAIL**。A 段 4 次全量各 18 PASS，`before 0 B / 0 目录 → after 0 B / 0 目录`；`KEEP_TMP=1` ⇒ 保留 1 目录。
2. **reviewer 独立注入**：`run_arch.py` 的 `single_platform = len(platforms) == 1` → `False`（md5 `3e9850ee…` → `a0e6a19e…`）⇒ 4×`[FAIL]`（B3c×2 / C1b / D6b）rc=1；`cp` 回后 md5 复等 `3e9850ee…` 且回绿（注入残留 0 命中）。脚本自带 A4（残留 1 目录被检出、还原 md5 相等）与 B6（rc=1 + `unrecognized arguments: --mode`、还原 md5 相等）各自成立。
3. **`--mode`**：`check_ptw_rtl --selfcheck` rc=0 且打印「按 DIV-09 记 GAP」；直接 `--mode smon/umon` ⇒ rc=77 + DIV-09 原因、无「unrecognized arguments」；`run_arch --cfx 4 --platforms chipyard --mode {hmon,smon,umon}` 分别 **rc=0**：hmon 13 PASS + 1 GAP(015)（`arch-ptw-002` 现场 **3** 槽）、smon/umon 各 **14 GAP**。
4. **单平台**：chipyard / qemu 全量各 rc=0，含「单平台模式」行、**0** 处「跨平台不一致」；多平台 015 的 `ref` = qemu+gem5、`ref_ok=true`（空 `ref` 分支仅兜底）。
5. **`gem5bin.py`**：真实 gem5 rc=0（ELF 737453152 B）；4 KiB 截断 rc=1（节头表越界）；1 MiB 非 ELF rc=1（magic）；`file(1)` 在场并参与；023 `run.sh` 命中 1 处接入。`retryable()` 用 023 脚本**原函数**探针实测：77 → 不重试不计数、2 → 不重试、1/139 → 重试 1 次且 FLAKES=1；`NO_RETRY=1` ⇒ rc=1 直接判红不重试（生效）。
6. **三平台**：`run_arch --cfx 4 --platforms qemu,gem5,chipyard` rc=0、`failures=[]`、`cases=14`、`GAP=['arch-ptw-015']`。
7. **门控（reviewer 独立跑）**：`run_arch --self-test` / `check-tests-index`（503 条）/ `check-tasks` / `check-knowledge-refs`（悬空 0）/ `check_issues`（54 open）**全 rc=0**；cache/time/hart/pmem 代表集 **8 条**（现场派生）rc=0。
8. **flake（ISS-m16-011）**：三轮均 `flake 重试：0`。
9. **快照对账**：验收前后 `git status --porcelain -uall` 逐行相同；改动面 8 个文件 md5 与注入前全等；`git diff --cached` 空。
10. **约束**：只动 `tests/arch/**` + 本任务书 + 运行期证据脚本 ✓；未提交 git ✓；本记录无运行期路径 ✓；术语「寄存器组」（diff 中「银行」0 命中）✓。
11. **新增文件状态**：`tests/arch/common/gem5bin.py` = **`??`（未 staged）**，合并时必须显式 staging。

**非阻断 finding（交 architect）**：① 证据脚本 `bad()` 把 `FAIL` 当标志位 ⇒ 失败时汇总打印「1 FAIL」而实为 4 条（退出码与逐条 `[FAIL]` 正确）；② 口径「hmon 2 槽」与现场 3 槽（`arch-ptw-002`；2 槽是 `007`）不符；③ inventory 注「13 → 11」是全部 signature case 总槽 3/3/2/3，主语写 `007` 略歧义（`C4` 已现场断言）；④ 021 运行期临时根仍剩 ≈230 MB / 42 项历史残留（`run_arch` 工作目录 + 一个旧版 `mkdtemp` 的 `flood.bin`），不在 `checks.py` 的 `TMP` 面内（该面 0 B / 0 目录）⇒ 不属 ISS-m16-007 覆盖面，建议另立清理；⑤ `NO_RETRY=1` 由原函数探针证实，023 `run.sh` 因分支门未整脚本实跑。

**判决：Accepted** —— 验收命令在 reviewer 自己的重跑下全绿、硬约束无违反；finding ①–⑤ 不阻断，由 architect 收尾处置。

