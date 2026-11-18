# m15-testcases-018: `run_inst_tiny.py` 的 gem5 lane 补 `--semihost on`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m16-gem5-011`（`fs.py` 的 `--semihost` 默认改 `off`）
**可并行分片**：否
**预估**：0.5–1 h
**档位**：小改
**状态**：待验收

## 背景（`m16-gem5-013` 复核发现）

`m16-gem5-011` 已把 `configs/dadao/fs.py` 的 `--semihost` 默认改为 **`off`**（显式开），但 `tests/ee-tiny/run_inst_tiny.py` 的 gem5 lane **没有同步补 `--semihost on`**：

```python
cmd = [gem5, "--outdir=…", config, "--profile", "tiny",
       "--bootrom", …, "--kernel", …, "--console-out", …]
# 缺 --semihost on
```

后果：`--platforms gem5` 时载体跑不出 semihosting 输出 ⇒ **必然超时/判红**，与实现无关。

## 目标

1. `tests/ee-tiny/run_inst_tiny.py` 的 `run_gem5()` 命令补 `--semihost on`（位置与其它参数同风格）。
2. 全仓核查同类消费者是否也漏（`grep -rn "configs/dadao/fs.py"` / 调用 `fs.py` 的脚本），逐条列出并处置（补参数或说明为何不需要）。
3. 若 `--semihost` 还有配套参数（`--semihost-argv`/`--semihost-system`）在载体链路中必需，一并确认；不需要则在完成区说明。

## 验收（逐条贴真实 rc）

1. `python3 tests/ee-tiny/run_inst_tiny.py --platforms gem5 --only <一个载体 id>`（或等价最小调用）⇒ **不再超时**，输出与 QEMU lane 一致（同一 id）。
2. **可达 FAIL**：把 `--semihost on` 临时去掉 ⇒ 该调用**超时/失败**；还原 ⇒ 通过（`cp`+md5）。
3. 全仓 grep 结论：列出所有调用 `fs.py` 的脚本，逐个标「已带/不需要/需补」。
4. `check-tests-index`、`check-dirs`、`check-no-residue` rc=0。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `tests/ee-tiny/run_inst_tiny.py`（+ 同批发现的同类消费者）+ 本任务书。
3. 不改 gem5 组件（`--semihost` 默认 `off` 是既有裁定，不动）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19）

逐行看 diff（2 文件、4 改行）：`run_gem5` 只在 `--kernel` 后插 `--semihost on`，argparse 顺序无关；docstring 同步说明默认 off 的原因。`check_tiny_hmon` 同插一处；该脚本断言的 `hmon-ok`/停止因正是 semihosting 路径，补前 rc=1（`GEM5_EXIT_CAUSE=simulate() limit reached`）、补后转 PASS。负例（缺 bootrom/非 64 KiB/PT_LOAD 越界/e_entry）走独立 gem5 调用，与 semihost 无关，补后仍全 PASS。无 finding。

### 第 1 轮 reviewer 验收（2026-11-19）

**重跑记录（我自己的命令与真实输出）**
1. worktree 自证：`git rev-parse --show-toplevel` → `/tmp/opencode/m15-testcases-018/wt`；分支 `m15-testcases-018`；`git status -uall` 干净；`git diff --name-only 92175296 c13bf77f` → **3 文件**（本任务书 / `tests/ee-tiny/run_inst_tiny.py` / `tools/gem5/check_tiny_hmon.py`）；`git diff master...HEAD -- components/` 空。
2. 修复有效性（我自己跑两侧）：`--platforms qemu` ⇒ rc=0、224 B；`--platforms gem5` ⇒ rc=0、224 B；`cmp -s` ⇒ **rc=0**，两侧 md5 同 `7e5529cea8821543d0956011fefd59c4`；gem5 日志含 `semi:ADP_Stopped`。
3. 证据脚本重跑：`bash .work/evidence/m15-testcases-018/run.sh` ⇒ **17/17，exit 0**；`--inject all` ⇒ **31/31，exit 0**（真红项在场：`inject suite: rc is timeout -2`、`inject hmon: no hmon-ok PASS line`）。
4. 独立注入（我自己删 flag，非脚本自带）：md5 `d234da65…`→`af62c268…`、`cmp` 备份 rc=1；重跑同一脚本 ⇒ **9/17，exit 1**（8 FAIL：`minimal gem5 lane rc exp=0 got=1`、`bytes exp=224 got=0`）；`cp`+md5 还原回 `d234da65…`、`cmp` rc=0 ⇒ **17/17，exit 0**。
5. 独立 fs.py 探针：同一 fs.py 命令**无** `--semihost on` ⇒ `timeout 90` **rc=124**、console 缺失；**加** ⇒ rc=0、224 B。
6. 门控（我自己直接跑）：`check-tests-index` rc=0（472 条 PASS）、`check-dirs` rc=0、`check-no-residue` rc=0。

**约束核验**：独立 worktree ✓；禁提交 git ✓（本轮只新增本审阅记录，未 commit）；只动 3 文件 ✓；`components/gem5` 零改动、`fs.py --semihost` 默认 `off` 未动 ✓；还原用 `cp`+md5，未用 checkout/restore/stash ✓；临时文件在 `/tmp/opencode/m15-testcases-018/` ✓。

**预存在红核实（属实，且与本改动无关）**：`check_tiny_hmon` 实跑 `FAIL (33/201)` rc=1 —— `cause_id` 期望 `0x2` 实测 `0x200000000000002`（record 18/19/20 + last-fault 槽）、`record count expected=43 actual=42`、record 34 起字段错位、`gem5 guest exit expected=0x21 actual=0x71`。根因 = `ADR-0056`（Accepted）+ `m16-gem5-009`（2026-11-17 合入，cause 18 位子原因）与 `tests/arch/hmon/expected.yaml`（末次改于 `e96f0f19`，仍 one-hot）漂移；本任务 diff 未碰该 oracle / hmon 源 / 组件，semihosting 面 `[FAIL] semihosting` 0 条，且 `check_tiny_hmon` 不在任何 `make` 门控。⇒ 记 finding，交 architect 立独立任务，本任务不修。

**次要 finding（不阻断）**：完成区「坑②：`--semihost on` 未提交、删掉即回 HEAD blob ⇒ `git diff` 为空」在验收时不成立 —— 该 flag 已随 WIP `c13bf77f` 入库，注入后 `git diff` 实测非空（1 insertion/1 deletion）；结论方向（改用 `cmp`+md5）仍正确，仅措辞需修正。

**判决：Needs Revision**
- 失败项 = **验收 3 / 目标 2（全仓消费者逐条处置）**：`tools/testcases/parity/run_parity.py::_run_gem5_direct`（L1621，3 处调用，`--direct-check` 下）**绕过 shim 直跑 `fs.py`，其 cmd（L1625-1629）没有 `--semihost on`**，完成区「run_parity 经该 shim 已带」不成立；按第 5 项实测该形态 rc=124 超时 ⇒ `rc != row["gem5"]["exit"]` ⇒ `direct-check: FAIL`（可达）。属 `m16-gem5-011` 预存在、非门控，但按硬约束 2「+ 同批发现的同类消费者」应补 `--semihost on` 或写明为何不需要，并修正完成区该条。
- 验收 1、2、4 全绿（见上 1–6）。其余消费者我独立复核均属实：`se.py` 全文 0 处 `semihost` ⇒ ee-user / tset / `check_se_*` / `gem5_se_engine` 确不需要；`run_embench_tiny` / `run_picolibc_tiny` / `run_suite` / `run_m5_e2e` 无 gem5 调用；`qemu_gem5_shim` L276 缺省 `on`；`compare_chipyard` L531 带 `on`。

### 第 2 轮 engineer 返工自审（2026-11-19）

| finding（reviewer 第 1 轮） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `run_parity._run_gem5_direct` 直跑 `fs.py` 缺 `--semihost on`（3 调用点，`--direct-check` 可达 FAIL） | ✅已修 | 在该唯一命令构造器的基础 cmd 里补 `--semihost on`（inst/arch/embench 三调用点全部经它） | `direct_probe.py` 调**真实** `_run_gem5_direct`（inst 形原样 extra；arch/embench 形以 tiny+显式 bootrom 代跑，非原样）：`rc=0 console=224/224/0 flag=yes semi=yes` 3/3；删 flag ⇒ 三形全 `rc=124 console=0`；`cp`+md5 还原 `a8bbc703…` ⇒ 3/3 回绿 |
| 完成区「run_parity 经该 shim 已带」不成立 | ✅已修 | 改为「shim 缺省 `on`；`--direct-check` 直跑路径已补」 | 见上条 |
| 完成区「flag 未提交 ⇒ `git diff` 为空」措辞不成立 | ✅已修 | 改为「flag 已随 WIP 入库，注入后 diff 非空；结论仍是用 `cmp`+md5」 | 本轮实测：删已入库 flag 后 `git diff --name-only` 非空 |
| `check_tiny_hmon` 预存在红（ISS-471） | ❌不修（任务书明令） | 无 | 补 flag 后 `FAIL (33/201)` 与 reviewer 实测逐条相同，`[FAIL] semihosting` 0 条 |

自审补充：`_run_logged` 不清理 `--console-out`/`--trace-cpu`，探针首轮因此把过期 console（224 B）误读成「超时仍产出」——已在探针里跑前 unlink，重跑后注入形 console=0。完整 `--direct-check` 需全量矩阵（小时级、且本 worktree 无 Vast 工件），故以「`run_parity._run_gem5_direct` + 三调用点原样实参」做函数级证据，并在完成区给出全量复跑命令。

### 第 2 轮 reviewer 验收（2026-11-19）

**阻断项复验（我自己的命令与输出）**
1. 直跑不再超时：我另写探针导入**真实** `run_parity` 模块、调真实 `_run_gem5_direct`，**inst 形 extra 原样**（`["--kernel", <elf>]`，无 `--console-out`）⇒ `rc=0 flag=yes semi=yes`；加 `--console-out` 形 ⇒ `rc=0 console=224`；日志含 `GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit` / `GEM5_EXIT_CODE=0` / `[PARITY_EXIT] rc=0`，`WALL=0.82s`。
2. 可达 FAIL（我自己注入，非脚本自带）：`run_parity.py` md5 `a8bbc703…`→`9ec67878…`、`cmp` rc=1 ⇒ 同路径 **`rc=124`**（`[PARITY] TIMEOUT after 45s`、`flag=no semi=no`）；`cp`+md5 还原回 `a8bbc703…`、`cmp` rc=0 ⇒ **`rc=0` 回绿**。
3. 只加 flag：`git diff 92175296 HEAD -- tools/testcases/parity/run_parity.py` = 仅基础 cmd 追加 `"--semihost", "on"`（1 删 2 增），无其它判据改动；三个实现文件各 1 处 flag。
4. 三调用点共用构造器：L1689/L1708/L1733 全部调 `_run_gem5_direct`；`extra` 分别为 `["--kernel", dest]` / `["--kernel",…,--console-out,…,--trace-cpu,…]` / `["--kernel", elf]`，**均不含 `--semihost`**（全文件仅 L1626 一处）⇒ 不会覆盖基础 cmd。

**其余抽样（我自己跑）**：`run.sh` **21/21 exit 0**；`--inject all` **42/42 exit 0**；`check-tests-index` rc=0（472 条）/ `check-dirs` rc=0 / `check-no-residue` rc=0；`check_tiny_hmon` = `FAIL (33/201)`（33 FAIL / 168 PASS / `[FAIL] semihosting` **0** 条）与第 1 轮实测逐条相同。`components/` 仍零改动，三实现文件 md5 `d234da65…`/`12d34753…`/`a8bbc703…`，`git status` 干净。

**完成区两条措辞**：均已改 ——「`qemu_gem5_shim` 已带（缺省 `on`）+ `run_parity --direct-check` 直跑 **需补→已补**」、「flag 已随 WIP 入库、注入后 `git diff` 非空」；`ISS-471` 实存（master `aa73ce4b`，标题即本预存在红，我分支基线早于它）。

**替代证据判定：足够关闭本轮阻断。** 探针导入真实模块、调真实 `_run_gem5_direct`，覆盖 flag 所在的唯一构造器，可达 FAIL 与还原我已独立复现。**仍缺（非阻断，记未闭合）**：① `direct_check()` 的真判据 `rc == row["gem5"]["exit"]`（直跑 vs 矩阵退出码对齐）未实测，需全量矩阵（engineer 已在完成区给出复跑命令）；② arch 形真实为 profile=vast、走 `args.bootrom_vast`、不传 `--bootrom`，本轮以 tiny+显式 bootrom 代跑，未覆盖。

**次要 finding（文档级，不阻断）**：完成区/自审表「按 3 处调用点**原样 extra 实参**」与探针 docstring `copied verbatim` 不准确 —— inst 形多加了 `--console-out`（真实调用点仅 `["--kernel", dest]`）、arch 形 profile/bootrom 非原样；实质结论不受影响（我已自证原样 inst extra rc=0），建议措辞修正。

**判决：Accepted** —— 验收 1–4 在我自己的重跑下全部通过，硬约束无违反（独立 worktree、未提交、只动 4 文件、`components/` 零改动、`cp`+md5 还原、临时文件在 `/tmp/opencode/m15-testcases-018/`）。

## 完成区

**测试结果**：证据 `.work/evidence/m15-testcases-018/run.sh` fast **21/21**、`--inject all` **42/42**（gem5.opt md5 `e88498f3…`，脚本内断言跑前=跑后；`check-source-state` rc=0）。
**验收结果**：
1. `--platforms gem5 --id ld.o_rrii_ra` ⇒ rc=0、224 B（补前 rc=-2 超时、0 B）；`--platforms qemu,gem5` ⇒ PASS，两侧 `.out` `cmp` 逐字节相同。
2. **`--direct-check` 直跑路径**：`run_parity._run_gem5_direct` 已补 `--semihost on`；用 `direct_probe.py` 调**真实** `_run_gem5_direct`（inst 原样 extra；arch 真实为 profile=vast + `args.bootrom_vast`，本轮以 tiny+显式 bootrom 代跑、**未覆盖**） ⇒ `SHAPE inst/arch/embench rc=0 console=224/224/0 flag=yes semi=yes`（3/3）。删 flag ⇒ 同一探针 `timeout 90` 三形全 `rc=124 console=0`（可达 FAIL）；`cp`+md5 还原 `a8bbc703…` ⇒ 3/3 回绿。
3. 可达 FAIL（其余两消费者）：删 flag ⇒ gem5 lane rc=-2、`check_tiny_hmon` 无 `hmon-ok`；`cp`+md5 还原 ⇒ 回绿。
4. `check-tests-index`/`check-dirs`/`check-no-residue` rc=0。
5. `fs.py` 消费者：`run_inst_tiny` **需补→已补**；`check_tiny_hmon` **需补→已补**；`run_parity --direct-check` 直跑（`_run_gem5_direct`）**需补→已补**；`qemu_gem5_shim` **已带**（缺省 `on`，另带 `--semihost-system native`）；`compare_chipyard`（`se_timing.py`）**已带**；`gem5_se_engine`/`se.py` **不需要**（SE 无 semihosting 面）；`min_rom_probe_*`、`l3_run`/`night_run`、Makefile `check-inst-asm`（只 qemu）**不需要**。
6. `--semihost-argv`/`--semihost-system` **不需要**：载体只用 `SYS_WRITEC/WRITE0/EXIT`、`SYS_WRITE0/OPEN/WRITE/EXIT`，无 `SYS_GET_CMDLINE`/`SYS_SYSTEM`；QEMU lane 也不传 `arg=`。
**修改文件**：`tests/ee-tiny/run_inst_tiny.py`、`tools/gem5/check_tiny_hmon.py`、`tools/testcases/parity/run_parity.py`（各补 `--semihost on` 一处）、本任务书。
**新发现/坑**：① `check_tiny_hmon` 预存在红 = **ISS-471**（18 位子原因 vs one-hot oracle），本任务不修；补 flag 后该脚本从「5 项可达红（semihosting 缺失）」变为「33/201 全量记录红」，**无 semihosting FAIL**、脚本不在任何 `make` 门控 ⇒ 未因本改动变绿或更红。② 完成区原「`git diff` 为空」措辞有误：该 flag 已随 WIP 入库，注入后 `git diff` 非空；结论（用 `cmp`+md5 判注入/还原）不变。③ `_run_logged` 不清理 `--console-out`/`--trace-cpu` ⇒ 探针跑前须删旧文件，否则超时形会读到过期 console 假绿。④ 读方护栏与 `m16-gem5-013` 并行重建冲突：多次 `rc=75`/源树注入期跳过，最终窗口内 gem5.opt md5 前后一致才采信。
**遗留问题**：`ISS-471`（`check_tiny_hmon` oracle 漂移，独立任务）；完整 `--direct-check` 需跑全量矩阵（inst/arch/embench/picolibc × profile，小时级）且本 worktree 无 Vast 工件 ⇒ 本轮以「三调用点原样实参」的函数级证据替代，全量复跑命令：`python3 tools/testcases/parity/run_parity.py --profiles tiny,vast --direct-check --json <运行期目录>/m.json`。
