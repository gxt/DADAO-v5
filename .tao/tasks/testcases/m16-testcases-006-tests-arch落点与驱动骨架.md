# m16-testcases-006: `tests/arch` 落点与驱动骨架

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（PLAN/矩阵）、`m16-testcases-005`（`tests/shared/signature.py`）已合入
**可并行分片**：否（共享 `tests/arch.yaml`、`check-tests-index`）
**预估**：中（结构与骨架，不含用例）
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`m16-testcases-004` 已产出 `tests/arch/PLAN.md`（目录/接口/字段/Process-09 草案）与 `tests/arch/vast-arch-inventory.md`（9 cfx × 3 平台）。本任务把 PLAN 的**落点与骨架**落地，让后续 cfx 用例有统一挂载点。

裁定见 `.tao/knowledge/discussing.md`「M16 三方差分（Vast arch）批次裁定」：只 Vast、三方签名一致、仿真不进常规门控、脚本/数据集中 `tests/arch/`。

## 要做

1. **目录落点**（按 PLAN）：
   - `tests/arch/run_arch.py`：唯一驱动；`--cfx <0|2|3|4|5|15|32|34|63>`、`--platforms qemu[,gem5,chipyard]`、`--cache-model on|off`（arch 默认 on）、`--self-test`；
   - `tests/arch/common/signature.py`：薄壳，只重导出 `tests/shared/signature.py` 的 `parse`/`compare`/`unwritten`/`Emitter`，不复制实现；
   - `tests/arch/common/` 的载体适配接口（qemu / gem5 / chipyard 三个后端骨架；未实现的后端必须显式失败，不静默回退）；
   - 不建空壳 cfx 子目录，按已有用例建。
2. **`tests/arch.yaml` 字段**：增加 `machine: vast`（固定）与载体类型（`asm` / `driver`）；保留 `platforms: [system]`。
3. **`check-tests-index`**：校验 `machine` 字段合法且 arch 条目只能是 `vast`；驱动型 case 的 `file` 允许指向驱动（不是 `.s`），但仍须存在。
4. **Tiny hmon 迁出**：`arch-hmon-001` 与 `tests/arch/hmon/` 迁到 `tests/unit/gem5/`（保留原测试可跑），从 `tests/arch.yaml` 删除；同步 `tests/arch/README.md`、相关门控/引用。
5. **README**：`tests/arch/README.md` 改为「Vast only；驱动型 case；脚本/数据集中本目录」。
6. **最小验证 case**：用一条现有 ptw 或 umon 用例，经 `run_arch.py --platforms qemu --cfx <n>` 跑通并产出签名流（只证明骨架可用，不新增语义用例）。

## 不做

- 不写新的 cfx 语义用例（后续任务）；
- 不实现 QEMU/gem5/RTL 的 cache 模型或 cfx5 命令；
- 不改 `docs/Process-09`（004 已改）；
- 不改组件源码。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/arch/**`、`tests/unit/gem5/**`、`tests/arch.yaml`、`tests/arch/README.md`、`tools/testcases/inst` 或 `tools/testcases/arch` 的索引校验器、本任务书；
- 不写运行期路径；术语「寄存器组」；
- 未实现的后端必须 fail-closed（非零、说明缺件），不得假 PASS。

## 验证

运行期证据目录内的 `run.sh`：

1. `run_arch.py --self-test` 通过；坏输入（未知 cfx、未实现后端）各自非零；
2. 最小 case 在 QEMU 上跑通，签名流按 `tests/shared/signature.py` 解析；
3. `make check-tests-index` 通过，现场统计条数与 `arch.yaml` 一致；注入「tiny 条目」⇒ FAIL；
4. Tiny hmon 迁出后，原 gem5 测试仍可跑（或明确记录 gem5 环境缺失，不能假 PASS）；
5. `make check-knowledge-refs`、`make check-tasks` 记录 rc；
6. `--inject` 至少 2 路（tiny 条目 / 未实现后端假绿）⇒ FAIL，`cp`+md5 还原后回绿。

## 完成区

**测试结果**：24 PASS + 1 显式 SKIP（`checks=24`，不假 PASS）。`run_arch.py --self-test` PASS；坏输入（cfx 99 / cache off / gem5 未实现）分别 rc=2/2/1；`arch-ptw-002` QEMU 跑通，签名流 3 槽逐值全等；`make check-tests-index` PASS 且 arch=11 == yaml=11（现场派生）；结构注入 2 路（arch 条目 machine=tiny / 后端假绿）均 FAIL，`cp`+md5 还原后回绿；`--inject` 12 路逐检查证明全部 `PROOF PASS`（注入红>0 / 还原绿=0）。SKIP = Tiny hmon gem5 迁移后测试：reviewer 现场日志为 `gem5.opt` 被并发 `m16-gem5-020` 重建替换（md5 `27c30421…` → 空文件 `d41d8cd9…`），writer-guard 判「跑批期间二进制被替换」；baseline 证据已被脚本 `rm -rf` 覆盖、无法复核，故首轮「同二进制失败集 33 条」的表述**订正**为替换事件，保留显式 SKIP、不假 PASS。

**修改文件**：新增 `tests/arch/run_arch.py`、`tests/arch/common/{__init__,signature,platform}.py`、`tests/arch/ptw/check_tlb.py`；`tests/arch.yaml`（+machine/kind、删 arch-hmon-001、+arch-ptw-002）、`tests/arch/README.md`、`tests/arch/vast-arch-inventory.md`（迁移注）；迁移 `tests/arch/hmon/*` → `tests/unit/gem5/tiny_hmon/*`、`tools/gem5/check_tiny_hmon.py` → `tests/unit/gem5/check_tiny_hmon.py`；`tools/testcases/check_tests_index.py`（machine/kind 校验 + 4 条注入自检）；引用同步 `tools/testcases/arch/min_rom_probe_integ007t.py`、`tools/infra/check_writer_guards.py`、`docs/Process-07-门控分层规范.md`；运行期证据目录的 `run.sh`（不入库）。越界披露：索引校验器实际在 `tools/testcases/check_tests_index.py`（任务书写「tools/testcases/inst 或 arch」）；后三个引用文件不在任务书变更集，属 item 4「相关门控/引用」同步。

**验收结果**：`run.sh` → `summary: checks=24 fails=0 skips=1` / `RESULT: PASS（含 1 项显式 SKIP）` rc=0；`run.sh --inject` → `injection: proofs=12 fails=0` + 同一 summary，rc=0。`make check-tests-index` 472 条 PASS；`make check-case-ledger` / `check-knowledge-refs` / `check-tasks` / `check-dirs` / `check-no-residue` rc=0；`check-writer-guards` 27/27 PASS；`integ007t` PASS 64 checks；`arch-ptw-002` signature.bin = `1122334455667788 1122334455667788 800000006100ffe1`。<br>**注入真实 rc（红/绿）**：ptw-qemu 1/0、signature 2/0、tests-index 1/0、hmon-tree 1/0、hmon-app 1/0、knowledge 1/0、tasks 1/0、ledger 1/0、writer-guards 1/0、gem5-skip 1/0、backend-flag 1/0、restore-md5 1/0。

**新发现/坑**：① Tiny hmon 的 SKIP 以 reviewer 现场为准：`gem5.opt` 被并发 `m16-gem5-020` 重建替换（md5 `27c30421…` → 空文件 `d41d8cd9…`），writer-guard 判「跑批期间被替换」；baseline 日志已被脚本 `rm -rf` 覆盖、无法复核，首轮「同失败集 33 条」的表述已订正。脚本先按日志文本命中替换事件，md5 比对为次级判定；两分支均只 SKIP，不再声称「同一二进制」。② `run.sh` 原 `check … "$(cmd)" "$?"` 的 `$?` 是命令替换子 shell 的 rc，已全部改为先 `rc=$?` 再传 `check`；26 处 `check` 逐行核过，无 `check … "$?"` 残留。③ `check-temp-dirs` 因其它任务的 5 个陈旧临时目录 FAIL（非本任务）。④ 新 worktree 无 `.dadao` 安装根时 `check-writer-guards` W5b rc=2；本次用运行期符号链接到主工作树工具链后 27/27。

**遗留问题**：① `tests/unit.yaml` 未增 `unit-gem5-hmon-001`（PLAN §7 要求）：`SCOPE_PLATFORMS["unit"]` 只允许 host/toolchain，加 `platforms: [system]` 需先裁定 unit 是否允许 system，未越界改 schema → 待裁。② 其余 14 条 `arch-ptw-*` 未登记 arch.yaml，随 cfx4 迁移任务。③ `tests/INVENTORY.md` 未改（历史快照、无门控）。④ 未跑 `check-arch` 全量（仿真不进常规门控；ptw-002 + integ007t 已真跑）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `run_arch.py` self-test 的 `n_sig` 生成器变量遮蔽/空 cases | ✅已修 | 拆成显式循环 | `--self-test` PASS（ptw 签名槽 10） |
| `run_arch.load_index` 未强制 arch `machine=vast` / `kind` 必填 | ✅已修 | 缺 kind/非 vast 即 ConfigError；删未用 `MACHINES` | `--self-test` 索引 PASS |
| `ARCH/rel` 拼驱动路径得到 `tests/arch/arch/...` | ✅已修 | 改用 `repo_root + tests + file`（`_carrier_path`） | driver selfcheck PASS、ptw 真跑 PASS |
| umon 的 m5-vectors-v1 被当 arch schema 误报 | ✅已修 | `validate_expected` 对 `programs` 列表跳过 | self-test 不再报 umon |
| importlib 加载 ptw 探针缺 `node_probe_prelude` 路径 | ✅已修 | 加载前补探针目录到 `sys.path` | `check_tlb.py --selfcheck` rc=0 |
| 编辑时误删「注入① ID 重复」自检体 | ✅已修 | 恢复该 case | `check_tests_index --self-test` 34/34 PASS |
| 证据脚本 `! grep` 后 `$?` 被命令替换覆盖 | ✅已修 | 先存 `hmon_rc` 再 check | `arch.yaml 已删 arch-hmon-001` PASS |
| gem5 稳定性只判 3s，遇原子替换/不可执行会假 FAIL | ✅已修 | `-x` 判据 + 原驱动同失败集比较 + 显式 SKIP | SKIP 理由「失败集相同 33 条」 |
| 注入未验证「文件已变」 | ✅已修 | 注入后 `cmp -s` 备份 | 两路「注入生效」PASS |

判决：全部 finding 已修；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑**（仓库根执行运行期证据目录内的 `run.sh`；脚本无 `ONLY=` 分段，按指示跳过 gem5 段——仅加一行 `gem5_stable=0`，差异与输出见运行期证据目录内 `reviewer-rerun1.out`）：
- 重跑①（基线）：`summary: checks=23 fails=0 skips=1` / `RESULT: PASS` / rc=0，与完成区数字一致。
- 直接复跑：`--self-test` rc=0；`--cfx 99` rc=2；`--cache-model off` rc=2；`--platforms gem5` rc=1 且日志含「载体未实现」（fail-closed 成立）。
- `make check-tests-index` rc=0（472 条，现场 `arch=11`）；`check-tasks` / `check-knowledge-refs` / `check-case-ledger` / `check-dirs` / `check-no-residue` rc=0；`check-writer-guards` 27/27 rc=0；`check_tests_index --self-test` rc=0（34 case，machine/kind 4 条注入全 PASS）。
- 独立注入：`tests/arch.yaml` 追加 `machine: tiny` 条目 ⇒ rc=1 且 VIOLATION「只能 `vast`」；`cp` 还原 md5 `e510d29615fe3bed9ded237e6ce36c80` OK ⇒ rc=0（未用 checkout/restore/stash）。

**阻断 finding（脚本不合格）**：`run.sh` 11/23 条断言恒真——`check … "$(cmd)" "$?"` 的 `$?` 取到的是**命令替换**的退出码（bash 实证：`true; echo "[$(false)] rc=$?"` ⇒ `rc=1`；`false; echo "[$(true)] rc=$?"` ⇒ `rc=0`）。恒真行：68 / 97 / 119 / 127 / 179 / 181 / 183 / 212 / 214 / 234 / 236。**实证**：把 `tools/testcases/arch/min_rom_probe_integ007t.py` 的 `APP_SRC` 改指不存在文件 ⇒ 探针 `ERROR: application source not found`，而 `run.sh` 该行仍 `PASS … rc=0`、`summary: fails=0`、`RESULT: PASS`、rc=0（运行期证据目录内 `reviewer-rerun2-integ007t-injected.out`）；`cp`+md5 还原后探针复跑 rc=0 `PASS (64 checks)`。其中 97 行是验收项 2（签名流逐值全等）的**唯一门控**，179/181/183 是三个门控的唯一门控 ⇒ 本次 `problems=[]` 属真通过，但脚本抓不住失败。要求 engineer 修脚本（rc 先存变量再传 `check`，并补「注入→该行 FAIL→还原→回绿」自证），reviewer 不代写。

**tiny-hmon SKIP 判定：如实 SKIP、非假 PASS**：末次 run 的 `tiny-hmon.log` 为 `PermissionError … gem5.opt` + `writer-guard: FAIL 二进制在跑批期间被替换（md5 27c30421… → d41d8cd9… 空文件）`，走「并发变化」分支记 SKIP；本次重跑同记 SKIP、不计 PASS。**finding（记录）**：完成区/审阅记录称「SKIP 理由 = 同二进制失败集 33 条」与现场日志（替换分支）不一致，且 baseline 失败集证据已被脚本 `rm -rf` 覆盖、无法复核 ⇒ 订正措辞或保留对应日志。**finding（门控缺口，非阻断）**：`tests/unit.yaml` 未登记该测试（`SCOPE_PLATFORMS["unit"]` 仅 host/toolchain、`Makefile` 无目标）⇒ 迁出后无 L1/L2 覆盖；已作遗留①披露、本任务书未要求登记，随 unit 是否允许 system 的裁定处理。

**结构 / 迁移 / 越界**：`common/signature.py` 无本地 `def parse/compare/unwritten/class Emitter`（grep_rc=1，仅 importlib 重导出）；`arch.yaml` 11 条（yaml=11=grep=11=门控现场 `arch=11`）；`machine=vast` 断言在 `_check_entry`。新址 `tests/unit/gem5/{check_tiny_hmon.py,tiny_hmon/*}` 6 文件齐，`tests/arch/hmon/` 与 `tools/gem5/check_tiny_hmon.py` 已删；`check_writer_guards.py`（READER_ENTRIES）、`docs/Process-07`（读方清单）、`min_rom_probe_integ007t.py`（APP_SRC）三处均为**路径同步**，必要、已在完成区披露、非越权；残留引用仅在历史/基线快照（archive、inventory 迁移注、PLAN 迁移表、TestReports）⇒ 不阻断。

**快照对账**：审查前后 `git status --porcelain -uall` 均 27 行、diff rc=0；`run.sh` md5 前后均 `d6eadf218bd416b6184496bc1289f513`；证据目录已恢复工程原 `run/`，我方输出另存 `reviewer-*.out`。

**判决：Needs Revision** —— 失败项：运行期证据目录内 `run.sh` 的恒真断言（68/97/119/127/179/181/183/212/214/234/236 行）；附带订正完成区 SKIP 理由措辞。其余验收命令在 reviewer 重跑下全部通过、硬约束无违反。

### 第 2 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `run.sh` 11 条 `check … "$(cmd)" "$?"` 恒真（68/97/119/127/179/181/183/212/214/234/236） | ✅已修 | 全部改为命令先执行并 `rc=$?`，再把 `$rc` 传 `check`；26 处 `check` 逐行核过 | `grep -n 'check .*"\$?"' run.sh` = 0 命中（仅注释）；reviewer 的 APP_SRC 注入现 `FAIL rc=2`，还原后 `PASS 64 checks` |
| 恒真断言缺「注入→FAIL→还原→绿」自证 | ✅已修 | `run.sh` 增加 `--fault <name>` 与 `--inject`；12 路逐检查注入/还原 | `injection: proofs=12 fails=0`；各路注入红/绿见完成区 |
| Tiny hmon SKIP 理由与现场日志不符 | ✅已修 | 完成区/坑改为「`gem5.opt` 被并发 `m16-gem5-020` 重建替换（`27c30421…` → `d41d8cd9…`），baseline 被 `rm -rf` 覆盖」；脚本先比 writer-guard start/finish md5，不一致即按替换 SKIP | 正常 run：`SKIP … gem5 环境：m16-gem5-020 并发重建…`；`--fault gem5-skip` 红=1/绿=0 |
| 注入恢复计数被红态污染（`restore_fails` 误计） | ✅已修 | `prove_fault` 在 restore 前 `reset_counters`，分别记 `red` / `restore_fails` / `green` | 12 路 proof 全 PASS |
| `--inject` 后 summary 被注入循环计数覆盖 | ✅已修 | `run_all` 后保存 totals，注入结束再恢复打印 | `--inject` 末行 `summary: checks=24 fails=0 skips=1` |
| 结构注入的还原断言需证明可失败 | ✅已修 | 抽出 `check_restore`；`restore-md5` 用错误 md5 触发失败 | `PROOF PASS restore-md5 注入红=1 还原绿=0` |

**注入真实 rc（红/绿）**：`ptw-qemu 1/0`、`signature 2/0`、`tests-index 1/0`、`hmon-tree 1/0`、`hmon-app 1/0`、`knowledge 1/0`、`tasks 1/0`、`ledger 1/0`、`writer-guards 1/0`、`gem5-skip 1/0`、`backend-flag 1/0`、`restore-md5 1/0`。

**最终重跑**：`run.sh` rc=0，`summary: checks=24 fails=0 skips=1`；`run.sh --inject` rc=0，`injection: proofs=12 fails=0` + 同一 summary。判决：全部 finding 已修；状态 `待验收`。

### 第 2 轮 reviewer 验收

**重跑**（仓库根执行运行期证据目录内的 `run.sh`、`run.sh --inject`；因 `m16-gem5-020` 并发在用 `gem5.opt`，按指示**不重跑真实 tiny-hmon** ⇒ 用运行期证据目录内 `reviewer-run2.sh` = 原脚本 + 1 行「`GEM5` 等于原路径 ⇒ `gem5_stable=0`」守卫；原 `run.sh` md5 前后均 `d984dda933efe3244f970235f28407e3` 未改；输出存运行期证据目录内 `reviewer-r3-*.out`）：
- 基线：`summary: checks=24 fails=0 skips=1`、`RESULT: PASS（含 1 项显式 SKIP）`、**rc=0**（现场 24 PASS + 1 SKIP）。
- `--inject`：`injection: proofs=12 fails=0` + 同一 summary、**rc=0**；12 路红/绿与完成区逐条相符（ptw-qemu 1/0、signature 2/0、其余 10 路 1/0）。
- 恒真核验：26 处 `check` 逐行核，rc 均取自紧邻 `rc=$?`、`$([ … ]; echo $?)` 或注入标记变量；`grep 'check .*"\$?"'` 仅命中脚本第 69 行注释 ⇒ 无恒真断言。`check_restore` FAIL 路径实证：`restore-md5` 注入全零 md5 ⇒ `FAIL 还原 md5 探针 rc=1`，还原后 `PASS rc=0`。
- 独立注入①（12 路未覆盖）：改写现有 `arch-ptw-002` 的 `machine: vast→tiny`（不追加）⇒ rc=1、fails=8（`check-tests-index FAIL rc=2`、`--self-test FAIL`）；`cp`+md5 `e510d296…` 还原 ⇒ rc=0、fails=0。
- 独立注入②（产物侧「签名错一槽」）：在 `tests/arch/common/platform.py::_finish` 驱动跑完后翻转 `signature.bin` 末字节 ⇒ `签名流解析/逐槽比对 FAIL rc=1`（`…ffe1→…ffe0`）+ `QEMU 跑通 FAIL`，rc=1、fails=2；`cp`+md5 `5236b311…` 还原 ⇒ rc=0、fails=0。
- 独立注入③（探计数断言）：删除 `arch-ptw-002` 条目 ⇒ 整轮 rc=1、fails=3（用例级断言变红），但 `check-tests-index PASS` 且 `arch 条数一致 PASS（yaml=10 idx=10）`。
- 还原纪律：全程 `cp`+md5、未用 `git checkout/restore/stash`；`git status --porcelain -uall` 审前/审后均 27 行、diff rc=0；`run.sh`/`arch.yaml`/`platform.py` md5 与审前一致。
- SKIP/披露核验：脚本 4 条 SKIP 分支均标「不得当作 PASS」；`grep '同二进制'` 在 `run.sh` 仅第 180 行注释、`grep '33 条'` 零命中，「33 条」只作为被订正的历史表述留在任务书；`run/` 内确无 baseline 失败集日志 ⇒「已被 `rm -rf` 覆盖、无法复核」披露如实；事件描述与第 1 轮现场记录（writer-guard 判替换）一致。
- 补核完成区数字：`check-dirs` rc=0、`check-no-residue` rc=0；`check-knowledge-refs`、`check-tasks` 在本记录写入后复跑（结果见下）。
- **采信边界**：真实 tiny-hmon 运行与 baseline 失败集日志未复跑/不可得（并发重建 + 已被 `rm -rf` 覆盖），此二项采信第 1 轮现场记录 + 本脚本分支代码；其余数字与 rc 均本轮实测。

**finding（非阻断，交 architect 收尾改）**：① 完成区「通过 23/24」是上一轮数字（本轮 24 PASS + 1 SKIP），与 `checks=24` 不符。② `arch 条数一致` 两侧同源（gate 的 `arch=N` 与直接数 `tests/arch.yaml`），只抓门控输出/解析漂移、抓不住「少一条」（注入③实证该行仍绿）⇒ 建议与独立期望对账。③ 坑①「脚本现先比对 start/finish md5」与分支顺序不符：替换事件先命中日志文本 grep，md5 比对为次级分支；两分支均只 SKIP、不影响不假 PASS。④ 坑③写了具体系统临时目录路径，建议改「其它任务的陈旧临时目录」。⑤ 第 1 轮遗留①（`tests/unit.yaml` 未登记 `unit-gem5-hmon-001`）仍未处置，随 unit 是否允许 system 裁定。

**判决：Accepted** —— 返工三项（11 条恒真断言改先 `rc=$?`、`--fault`/`--inject` 12 路注入自证、SKIP 措辞订正）在 reviewer 自己的重跑下全部成立；3 路独立注入红/绿实证；硬约束（变更集、不提交、fail-closed、不假 PASS、不写运行期路径）无违反。gem5 段按指示未重跑真实 tiny-hmon，SKIP 判定以代码分支 + 已有日志核验（守卫差异已在上披露）。5 条 finding 均不阻断。
