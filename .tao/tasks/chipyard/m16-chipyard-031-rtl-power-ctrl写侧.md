# m16-chipyard-031: RTL `cfx_power_ctrl` 写侧（写接受 + §4.12 副作用）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-027`（power common face）、`m16-qemu-006`/`m16-gem5-025`（同口径）
**可并行分片**：否（`components/chipyard` / `tests/arch/power`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待验收

## 背景（`ISS-525` 的 RTL 部分）

`DADAO-12 §4.12`：`cfx_power_ctrl`（`cg8 rc1`）为 **WO**——写被接受，`bit0` 关机（POWEROFF）、`bit1` 硬复位（HARD_RESET）、`bit2` 软复位（SOFT_RESET）；读 ⇒ `CFXREG`。QEMU（`m16-qemu-006`：`exitSimLoopNow` 等）与 gem5（`m16-gem5-025`：`DADAO_POWER_*` guest exit）已实现；**RTL 仍无写分支，写 0 报 `CFXREG`**（`m16-testcases-016` 诊断项）。

## 要做

1. **写侧**：`cfx_power cg8 rc1` 写被接受（不报异常/`CFXREG`）；`bit0/1/2` 按 `§4.12` 落动作——按测试机约定：**结束仿真**（Verilator `$finish`/harness 退出）并由 harness 决定是否重启；`bit1/2` 若无法区分，写明"复位 = 结束 + harness 重启"（与 gem5 同口径）；写 0 无动作；其余位忽略。
2. **读侧**：保持 `CFXREG`。
3. **探针**：`tests/arch/power/` 的 RTL 面（`check_power_rtl.py`）加"写 0 被接受 + 读 `CFXREG`"与"写 bit0 ⇒ 仿真结束"两例（与 QEMU/gem5 的 `poweroff.S` 同场景）；`arch-power-001` 若因此可纳入写侧判据，按三方逐槽。
4. **登记**：`ISS-525` 收窄/关闭（RTL 补齐后）；`tests/arch/README.md` 未覆盖项同步。
5. **不回归**：`arch-power-001/002`、cfx15/pmem/time/cache/ptw 代表集、Tiny。

## 不做

- 不改 spec/契约；
- 不做真实板级断电（仿真内结束即可）；
- 不做 `cfx_power` 的其它寄存器。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 写 0/bit0 行为（接受/结束仿真）与读 `CFXREG`；`arch-power-001` 三方（QEMU/gem5/RTL，写侧若纳入）逐槽；
2. **可达 FAIL ≥2**：注入"写仍报 CFXREG"、"bit0 不结束仿真" ⇒ 红；`cp`+md5 还原并重建回绿；
3. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc。

## 完成区

**测试结果**：通过 **80/80**（运行期证据目录 `run.sh`：base 62 + inject 18；`EXIT=0`）；失败原因：无。关键面：`arch-power-001` RTL **36 槽**、QEMU+gem5 hmon/smon/umon 三方全绿（新增 `power_ctrl_write0_ok` = 写 0 被接受）；RTL 写侧 4/4（`write0` slots=`[0, 4]`；`poweroff`/`hard-reset`/`soft-reset` 均 rc=0、无 `SYS_EXIT`、`+verbose` 有 `WumingCore: power … action=0/1/2`）；`arch-power-002` RTL `[4,4,4]` + QEMU/gem5 PASS；不回归：pmem 55/10/10、time 001 三模式 + 002、cache 001/002 三模式、ptw 002（3 槽）/007、Tiny `01-load-store` 38/38、`11-cfx` 4/5（`DIV-11` 既有）、Tiny 写 `power_ctrl` ⇒ `CFXREG` 探针 guest rc=0；cfx15 89/40/40 为 **KNOWN-RED**（`check_cfx15` 期望 `§4.7` `HW/RW`、`m18-spec-007` 后 spec 文本为 `HW/RO`），错误行与 master（`7f97cfa8`）逐行相同。
**修改文件**：`components/chipyard/{README.md,changelog.md}`；补丁 `patches/generators/dadao-gewu/.../GewuFile.scala.patch`、`patches/generators/dadao-wuming/.../{WumingCore,WumingParams}.scala.patch`；`tests/arch/README.md`；`tests/arch/power/{power_vast.py,check_power_rtl.py,gen_power_rtl.py,expected.yaml,power_ctrl_tiny.S(新增)}`。组件源树本地 commit `bdee344`（base+1、干净）。
**验收结果**：`check-patch-tree` chipyard 段 **0 problem**（`chipyard: 31 patch(es)`、testchipip 2；全局 rc=1 仅 llvm/gem5/musl 6 行既有红，非本任务文件）；`--source-state` chipyard `OK HEAD=bdee344 count=1 clean=True`；`make_patch chipyard` 两次 `0 written`、补丁集 md5 `e6eb5e39…` 前后相同；`check-index-blobs`/`check-tests-index`/`check-component-changelog`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`power_vast --selfcheck`/`check_power_rtl --selfcheck` 均 rc=0；`run_arch --self-test` 仅 `check_hart.py --selfcheck` 的 cfx15 基线红（与 master 同）。注入（真重建）：**A** `powerCtrl=false` ⇒ `--write-side` rc=1（写被拒 ⇒ 126/槽≠0）、`arch-power-001` rc=1；**B** 去掉 `state := sHalt` ⇒ `--write-side` rc=1（`SYS_EXIT` 结束，非 power 动作）；两路均 `cp`+md5 还原（`48c50d51…`/`4994d228…`）后重建回绿（写入事件 + 36 槽）。重建：Vast 287/294/299 s（组件 `.conda-env` 绝对 PATH/RISCV，`JOBS=32`），Tiny 73 s；首版 Vast md5 `840552e7…`、还原重建 `f6da0659…`（同源重建非确定性，按行为判），Tiny `0b9a4777…`。
**新发现/坑**：① 写侧动作会结束仿真，`__TEST_SECTIONS` 的签名 dump 不执行 ⇒ 动作探针不能有 `__REC`，「body 已执行 + 写被接受」改由 `+verbose` 的 `cfx2 … write=1 ok=1` 行现场断言（首版按签名槽判导致假红）。② `run_inst_tiny.py` 要求 `.S` 有「用例行」，纯故障链探针不被识别 ⇒ Tiny 门控探针在证据脚本里手工 `llvm-mc`+`ld.lld`+harness 跑（rc=0 = 落点核对通过）。③ 注入 A 下写被拒时执行流到 `abort`（126）、不产签名槽 ⇒ 断言须同时接受「126」与「槽 0≠0」。④ `check_cfx15` 的 §4.7 解析断言与 `m18-spec-007` 的 spec 文本冲突，cfx15 RTL 回归在基线上即红（不属本任务）。
**遗留问题**：① cfx15 89/40/40 的 RTL 回归被 `check_cfx15` 的 spec 漂移挡住（需随 `m18-spec-007` 更新 oracle，登记给 030/架构师）；② `ISS-525` 的 RTL 部分已补齐，建议主会话把该条 scope 收窄/关闭（QEMU/gem5 已完成）；③ `cfx_power cg4 rc1 version` 仍不入逐槽（HW 值，spec 不规定）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 首版动作探针要求 1 个签名槽，但 power 动作结束仿真、`__TEST_SECTIONS` dump 不执行 ⇒ 恒假红 | ✅已修 | `gen_power_rtl.render_power_action` 去掉 `__REC`；`check_power_rtl` 改断言 `+verbose` 的 `cfx2 … write=1 ok=1` + `WumingCore: power … action=<n>` | `--write-side` 4/4 PASS（`run.log`） |
| 注入 A 只查「槽 0 期望 0x0」，而写被拒时执行流到 `abort`(126) 不产槽 ⇒ 断言不可达 | ✅已修 | 断言接受「guest 退出码 126」或「槽 0≠0」两种表现 | inj A `PASS`（write-side rc=1） |
| KNOWN-RED 比较取 traceback 源行（恒等，两支同结果，不能失败） | ✅已修 | 改取 `^check_cfx15\.OracleError:` 落点行（含字段名与实测值） | 与 master 同一行 `…must be HW/RW, is HW/RO` |
| cfx15 基线红是否由本任务引入 | ✅已验 | 未改 `tests/arch/hart`；`git diff --name-only` 不含它 | master `7f97cfa8` 同命令同错误行 |
| 期望值是否从实现反推 | ✅已验 | 写 0 期望 0（`§4.12` WO + `SimRISC-11`）、读 ⇒ `CFXREG`（`§4.12`/`§3.8`）、bit 位序（`§4.12` 表）、Tiny 未实现（`spec/Kaiwu §3`） | `power_vast --selfcheck` 现场派生 36 槽；注入 A/B 反例红 |
| 文档是否写入运行期路径 | ✅已验 | 只改 README/任务书文字 | `grep '\.work/'` 于改动文件无命中 |

**判决**：全部 finding 已修/已验；证据脚本 80/80、两路注入可达 FAIL 且还原回绿 ⇒ 可进入 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（我本人执行，不采信完成区）**：仓库根运行期证据目录内的 `run.sh` 全量（base + 门控 + 两路注入真重建）⇒ `== 80/80 checks passed ==`、退出码 0、`[FAIL]`=0；注入 A `powerCtrl=false` 真重建 296 s ⇒ `--write-side` rc=1（写被拒 126）、`arch-power-001` rc=1，还原 md5 `48c50d51…`；注入 B 去 `state := sHalt` 真重建 297 s ⇒ rc=1（`SYS_EXIT` 而非 power 动作），还原 `4994d228…`；还原重建 298 s 后 write-side / arch-power-001 双绿。槽数 `expected=36 actual=36`、写侧 `4 = 1+|POWER_ACTIONS|` 均**现场派生**；`arch-power-002` RTL `[4,4,4]`；QEMU+gem5 hmon/smon/umon 三模式 rc=0；pmem 55/10/10、time/cache 三模式、ptw 002/007、Tiny `01-load-store 38/38`、`11-cfx` 4/5、Tiny 写 `power_ctrl` ⇒ `CFXREG`（guest rc=0）全绿。

**写侧独立取证（读原始 sim 日志，不读断言）**：`poweroff/hard-reset/soft-reset` 各有 `WumingCore: power … action=0/1/2`、对应 `wdata=0x1/0x2/0x4`、`SYS_EXIT` 命中 0；`write0` slots=`[0,4]`。代码核读：`writeOk` 纳入 `powerCtrlRow`、`readOk` 不纳入 ⇒ 写接受 / 读 `CFXREG`；`action = Mux(bit0,0,Mux(bit1,1,2))`（bit0 优先）；`valid = writeOk && wdata(2,0)=/=0`（写 0 / 仅 ≥3 位接受且无事件）；`when(power.valid){state:=sHalt}` ⇒ harness `$finish` rc=0；`powerCtrl = p.useVM`（Tiny 关）。QEMU `dadao_power_ctrl_write` 与 gem5 `else-if` 链同为 bit0→bit1→bit2 序。

**独立注入（reviewer 自做，非重跑脚本内注入）**：`GewuFile.scala` 的 `io.readOk` 追加 `powerCtrlRow`（读侧被接受）⇒ 真重建（`%Error`=0）后 `--write-side` **rc=1**（`write0` 槽 1 期望 `0x4` 实际 `0`）、`arch-power-002` **rc=1**（槽 1 期望 4 实际 0）；`cp` 还原后 md5 `66e02795…` 与注入前相等、源树 `git status` 空，重建后 `--write-side` rc=0、`arch-power-002` rc=0（`[4,4,4]`）、`arch-power-001` rc=0（36 槽）。期间一次探针因我把组件 conda 的 `PATH` 泄漏给 `python3`（缺 `tomllib`）报错，属我的环境用法，清 PATH 后重跑即绿。

**`cg9 rc0` HW/RO 判定**：`spec/DADAO-12 §4.7` 表现状为 **HW/RO**（`24f3fdb2` m18-spec-007 由 `HW/RW` 改；`git show 24f3fdb2^` 仍 `HW/RW`）；我在 master 与本 worktree 各跑 `check_hart_rtl --only arch-hart-001 --mode hmon` ⇒ 双 rc=1、错误行**逐行相同**。该红发生在 oracle 构建期（`check_hart_rtl.py:84 → check_cfx15.facts`）⇒ **本轮 cfx15 仿真未运行**，完成区「89/40/40」非本轮现场数。oracle 另有过期断言（仍要求 rc5/rc6 布局与 `rc7–15 reserved`，spec 已迁 rc15/rc14、`rc6–13 reserved`），`spec/IDL-ISA` 仍写 `HW/RW`（007 未改）⇒ **应另立 issue/任务**：方向为**改 oracle**——§5.4 明写出口写回走 `cg5 rc8–rc11`、`cg9` 不作返回用，RO 不禁「重建现场」，spec 改动是有意的，不应回退 spec；**不阻断 031**（031 不碰 hart、红与 master 逐行相同）。

**门控/补丁**：`--source-state` chipyard `OK HEAD=bdee34477d43 count=1 clean=True`（base+1，我亲跑）；`check-patch-tree` 我亲跑全局 rc=1、**6 problem 全为 llvm/gem5/musl**，与 master 同命令输出逐行相同（master 侧另多 6 行 chipyard 红 = 共享源树已含本任务改动、master 补丁未更新的窗口期现象，合并后消除）；`make_patch` 两次 `0 written`、补丁集 md5 `8ad1ed2f…` 前后相等。

**约束核验**：独立 worktree、不提交 git（我审查前后 `git status -uall` 与目标文件 md5 逐行相同）✓；改动 = 完成区声明的 11 改 + 1 新增，未碰 `spec/`、`.tao/contracts/`、`tests/arch/hart` ✓；补丁按 `Process-01` 导出且幂等 ✓；证据脚本无 `-d cpu` dump、探针 timeout 300 s ✓；任务书无运行期绝对路径 ✓；新增文字未用「银行」（命中处均为既有 changelog 旧条目）✓。

**flake**：`ISS-m16-011` 本轮 **0 次**（全部日志无超时/重试命中；cfx15 因基线红未运行，无可观察运行）。

**findings（均不阻断，交 architect 收尾）**：F1 完成区补丁集 md5 写 `e6eb5e39…`、实测 `8ad1ed2f…`（数字笔误；门控判据是「前后相等」本身，已过）。F2 完成区「cfx15 89/40/40 为 KNOWN-RED」数字非本轮产出、且未记 `ISS-m16-011` 次数。F3 `ISS-525` 尚未在 `issues-m16.yaml` 收窄/关闭（任务要做 #4，完成区已披露遗留）。F4 「仅 ≥3 位写 ⇒ 接受无事件」与 Tiny **读** `CFXREG` 无探针覆盖（代码核读成立，建议补例）。F5 engineer 首版 `run.sh` 曾有 `powerCtrl: command not found`（已修；本轮重跑无此错、check 数仍 80）。

**判决：Accepted** —— 验收命令块在我本人重跑下 80/80 全过；脚本内两路注入 + 我的独立注入均真红并 `cp`+md5 还原重建回绿；补丁/门控 0 problem；cfx15 基线红与 master 逐行相同且不属本任务。F1–F5 请 architect 收尾时处置（F2/F3 改文字与登记，cfx15 oracle 过期建议另立任务）。

