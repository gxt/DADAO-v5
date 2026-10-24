# INFRA-104t: musl 构建加 `-ffp-contract=off`（修 `ISS-332`：`math/yn` 3 ulp）

**模块**：infra
**项目里程碑**：M9（收尾前）
**依赖**：`LLVM-123t`（FMA 收缩启用）、`LLVM-129t`（已排除自身）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**已由 reviewer 实证，勿重复推断**）

- 现象：libc-test 静态档从 `LLVM-127t` 时的 **331 pass / 0 fail** 变为 **330 pass / 1 fail**，唯一 fail = `math/yn`（差 3 ulp）。
- 排除：`LLVM-129t` 关闭 `ldm/stm` 后仍 fail，失败 TU 零 `ldm/stm`；`jn/j0/j1` 目标码开关前后逐条一致。
- **决定性实验**（reviewer 在临时树做的）：`jn.c` 加 `-ffp-contract=off` 重编 ⇒ **exit=0 回绿**。
- 假设成立：`LLVM-123t` 启用 FMA 收缩后，musl 的 libm 多项式在 `a*b+c` 处收缩为单次舍入，结果与 libc-test 的严格期望差 1–3 ulp。上游 musl 的 `configure` 会尝试加 `-ffp-contract=off`；本仓交叉构建**没有**该 flag（`tools/infra/build_musl.py` 与 `components/musl/` 均无）。

## 目标

给 musl 交叉构建加 **`-ffp-contract=off`**（与上游意图一致），使 libm 结果与收缩无关；重建静态 + 共享 musl，验证 libc-test 恢复 **331 pass / 0 fail**。

## 实现要点（不预设落点，二选一并在完成区说明）

1. `tools/infra/build_musl.py` 的编译 flag（若它直接驱动 `make`，传 `CFLAGS_EXTRA`/`CFLAGS`）；
2. 或 `components/musl/` 的构建补丁（`config.mak` / `Makefile` 片段）。

**不要**全局关掉用户的 FMA 收缩（那只影响 libc 构建）。

## 验收

1. `make build-musl` + `make build-musl-shared` 重建成功；`check-musl-freshness` rc=0。
2. libc-test 静态档：**331 pass / 0 fail**（known-fail/blocked 保持原值）；`math/yn` 单独跑 exit=0。
3. 抽查 3 个 libm 函数目标码，确认收缩已消失（`fomul`+`foadd` 存在、`fofma` 为 0，或在 FP contraction 点看 `fofma` 消失）。
4. `make check`(L1) rc=0；`make check-modules`(L2) rc=0。
5. **可达 FAIL**：去掉该 flag 重建 ⇒ `math/yn` 复现 fail（贴两次真实输出）。
6. 证据 `.work/evidence/<任务ID>/run.sh`（rc 落盘、禁 `| tee`）。

## 接口规范

- **输入**：`tools/infra/build_musl.py`、`components/musl/**`、`Makefile`。
- **输出**：构建 flag + 重建产物 + libc-test 结果。
- **约束**：不改 `spec/`、`contracts/`、LLVM/QEMU；不 commit/push；临时目录 `/tmp/opencode/INFRA-104t/`。

## 完成区

**落点选择**：方案 1（`tools/infra/build_musl.py`）。flag 是**构建配置**，`config.mak` 本就是 `./configure` 产物；改 `components/musl/` 补丁树须重放 `fetch apply-series`，且等于手改生成物。同处把 `MUSL_CFLAGS` 混入 source digest，使「flag 变 ⇒ 必须重建」由 L1 机械保证。

**测试结果**：libc-test 静态档 **337 = pass 331 / fail 0 / known-fail 1 / blocked 5**（`functional/strptime` 与 5 例 OOM blocked 与 `LLVM-129t` 逐例相同，唯一变化 `math/yn` fail→pass）；`math/yn` 单跑 **exit=0**（注入期 exit=1）；`check-musl-freshness` rc=0；L1 rc=0；L2 rc=0；证据脚本 **43/43 PASS rc=0**。

**修改文件**：`tools/infra/build_musl.py`（唯一源码改动：新增 `MUSL_CFLAGS`、configure 传 `CFLAGS=`、`config_records` 校验其精确记录、`source_stamp` 混入 flag）；本任务书（完成区/自审）+ `.tao/knowledge/milestones.md`（仅状态列 → 待验收，L1 `check-milestones-fresh` 要求表册一致）；`.work/evidence/INFRA-104t/run.sh`（新，`.work/` 忽略区）。

**验收结果**（真实输出）：
- 收缩消失（产物 `obj/src/math/*.o`）：`fofma` **j0 50→0、j1 49→0、jn 4→0**；`fomul`/`foadd` 相应增加（j0 19+7→69+56、j1 12+5→61+52、jn 10+9→14+10）；`lib/libc.a` 全库 `fofma=0`。
- 反汇编采样（同一 TU j0）：flag off `ac: 5f 04 30 81  fofma rf1, rf3, rf2, rf1`；flag on `34: 44 68 14 10  fomul rf1, rf16, rf16` 且紧随 `foadd`。
- 可达 FAIL（两次真实输出）：flag on `PASS math/yn exit=0`；`MUSL_CFLAGS=""` 重建（`config.mak` 回 `CFLAGS = `，`libc.a` fofma>0）后 `FAIL math/yn exit=1`（`yn.h:9: RN yn(6, 0x1.8c5db097f7442p-1) want -0x1.6dbc18f9d5ddep+13 got …`）；`cp` 还原（md5 `9e1da1dc…` 对账）+ 重建 ⇒ `PASS math/yn exit=0`。
- 门控注入：仅把 `MUSL_CFLAGS` 改成 `-ffp-contract=fast`（不重建）⇒ `check-musl-freshness` **rc=1**（`[FAIL] source stamp == current musl tree`），还原后 rc=0。
- `make build-musl` rc=0（触发 `make clean` 全量 14 s）、`make build-musl-shared` rc=0（13 s）；L1/L2 日志 `.work/log/infra/INFRA-104t-check-L1.log` 与 `.work/log/infra/INFRA-104t-check-L2.log`，证据日志 `.work/log/infra/INFRA-104t-evidence.log`。

**新发现/坑**：① 只加 configure flag 不够——musl `Makefile` 不对 flag 建依赖、`config.mak` 又被 source digest 跳过 ⇒ 必须 (a) `config_records` 校验 `CFLAGS` **精确相等**、(b) 把 `MUSL_CFLAGS` 混入 `source_stamp`，否则旧树静默沿用旧 flag（注入即证）。② `libc.so` 的 2 条 `fofma` 来自 compiler-rt builtins 的 `__muldc3`（`LIBCC` 链接、不经本 flag），不能笼统断言「DSO 无 fofma」。③ libc-test runner 在 `blocked>0` 时恒 rc=1（既有 5 例 OOM），验收 oracle 是 counts 而非 rc。④ `libc.a` 被 `ar` 确定性重打会改 mtime 不改字节 ⇒ 套件结果复用须按 **libc.a sha256** 判新旧。
**遗留问题**：无。（建议 `/complete` 关闭 `ISS-332`；可选后续：`check_musl_freshness.py` docstring 补一句「source digest 含 MUSL_CFLAGS」，本册未改该文件。）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`git diff tools/infra/build_musl.py` 逐行 + `run.sh` 逐条断言（43 条，每条核对可达 FAIL 路径）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `has_musl_cflags` 曾用「含该 flag」：`MUSL_CFLAGS` 空时 `all([])==True` ⇒ 注入/陈旧 config 不重配 | ✅已修 | 改 `recorded == MUSL_CFLAGS.split()` 精确比较 | `has_musl_cflags('CFLAGS = \n')=False`、当前 config=True；`inject-config-mak-CFLAGS PASS` |
| F2 `source_stamp` 不含 flag ⇒ 改 flag 不 clean、freshness 不红 | ✅已修 | digest 先混入 `cflags {MUSL_CFLAGS}\0` | 首建日志 `sources changed => 'make clean'`；`gate-sees-flag-edit rc=1` |
| F3 断言「libc.so 无 fofma」不成立（builtins `__muldc3`） | ✅已修 | 改判「fofma owner ∉ builtins 符号表」，两侧都可 FAIL | 正常 0 命中（owner 仅 `__muldc3`）；注入期 owner=`__cos/__cosdf/__rem_pio2*` |
| F4 yn 注入断言写成字符串相等（`"rc!=0"` vs `"rc=1"`） | ✅已修 | 改 `pass_fail` + 数字判 | 注入 rc=1 → PASS |
| F5 `run_yn` stdout 与 runner 自带 report 同路径 | ✅已修 | stdout 改 `-stdout.log` | 三份日志各 1 行 `math/yn`，无交错 |
| F6 日志名 `.stdout/.EXIT` 撞 A3 门控（L1 首轮 rc=2，仅此 2 项） | ✅已修 | 改 `-stdout.log`/`-exit.txt` | L1 rc=0 |
| F7 套件 rc 在 `blocked>0` 时恒 1，按 0 断言会常红 | ✅已修 | 断言 `rc<=1` + counts 为 oracle | `PASS=43 FAIL=0` |
| F8 config.mak 另加「mode 之外」的额外约束 | ❌不修 | — | `CFLAGS` 仅由 configure 写，精确相等已覆盖，无需多余约束 |

**判决**：finding 全部已修/已证不修；证据脚本 43/43 PASS、rc=0；状态置「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录**（本人执行，日志 `.work/log/infra/INFRA-104t-reviewer-{evidence,L1,L2}.log`）：
- 证据脚本 `run.sh --rerun-suite`：**43/43 PASS，`RUN_EXIT=0`**；静态套件现场统计 `pass=331 fail=0 known-fail=1 blocked=5 total=337`（JSON 现读非写死）。
- flag 生效：`config.mak` 现读 `CFLAGS = -ffp-contract=off`；configure 传 `CFLAGS=`、`config_records` 精确比较、`source_stamp` 混 flag——代码逐行核过。
- 可察觉注入（我独立做）：`sed` 改 `MUSL_CFLAGS="-ffp-contract=fast"`（不重建）⇒ `check-musl-freshness` **rc=2**（`[FAIL] source stamp == current musl tree expected=11ad6a19… actual=e7a90ca3…`）；`cp`+md5 还原（`9e1da1dc…` 对账）后 rc=0。
- 可达 FAIL（脚本注入重建）：flag 置空重建 ⇒ `libc.a` fofma>0、`j0` 复现 `fofma`、**`math/yn` exit=1**（`yn.h:9 RN yn(6,0x1.8c5db097f7442p-1) want -0x1.6dbc18f9d5dep+13 got …1p+13, ulperr -3.219`）；还原重建 ⇒ yn rc=0、fofma 归 0、freshness rc=0。
- 反汇编（我独立数）：`j0 fofma=0 fomul=69 foadd=56`、`jn fofma=0 fomul=14 foadd=10`、`libc.a` 全库 fofma=0；`libc.so` 余 2 条 fofma owner=`__muldc3`（builtins，非 musl，成立）。
- 用户 FMA 未受影响（我独立验）：`clang -target dadao-unknown-elf -O2 -ffp-contract=fast` 编 `a*b+c` ⇒ `fofma rf8, rf16, rf17, rf18`（rc=0）。
- 门控：`make check`(L1) **rc=0**、`make check-modules`(L2) **rc=0**。

**约束核验**：改动仅 `tools/infra/build_musl.py` + 任务书 + `milestones.md` 状态列（git diff 核过，未碰 spec/contracts/LLVM/QEMU）；工作树快照前后一致（`git status` 干净、`build_musl.py` md5 `9e1da1dc…`）；临时物在 `/tmp/opencode/INFRA-104t/`；未提交。

**判决**：**Accepted**（flag 生效且机械可察觉、331/0 回绿、反例注入两向实证、用户 FMA 无损、L1/L2 绿）。

