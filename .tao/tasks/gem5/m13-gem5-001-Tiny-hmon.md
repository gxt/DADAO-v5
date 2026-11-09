# m13-gem5-001: gem5 的 Tiny `cfx_power` + `cfx3 hmon`（M13 前置）

**模块**：gem5
**项目里程碑**：M13
**依赖**：无（可与 `m12-chipyard-007` 并行；**验收要求三平台一致**）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，决策 2 = A）；**无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon
- **排期**：QEMU/gem5 侧排在 **M13 前置**；chipyard 侧在 M12（`m12-chipyard-007`）

## 目标

1. `cfx_power`（cfx63）：Tiny 启动移交 `power → hmon`（与 Vast 同构）。
2. `cfx3 hmon`：寄存器组（`excp_cause`/`excp_vector`/四类同步 mask/`cfx_intr_mask`/`switch_run_mode`）；同步异常（ILLI/UNDI/`CFXMEM`/`MALIGN`/`IALIGN`）进 hmon 向量。
3. **IALIGN 时 IP 停留在非法地址**（`DADAO-12 §5`），不写回 `nextIp`。
4. `trap` 区分：`immu18` 区间判定 semihosting vs hmon；semihosting 统一 `trap cfx_hmon`。
5. **地址图**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB）。
6. **与 chipyard 一致**：同一 ELF 在 gem5 与 chipyard 上的异常行为（`excp_cause`、IP 停留、退出码）逐条一致。

## 验收标准

1. `cfx_power → hmon` 移交可观测（运行模式与 PC）
2. 五类同步异常各至少 3 例进 hmon，`excp_cause` 正确
3. **IALIGN 时 IP 停在非法地址**（专门断言）
4. semihosting 的 `trap cfx_hmon` 与 `trap cfx63` 都能工作（`immu18` 判定不依赖 cfxha）
5. **与 chipyard 的三平台一致**（同一 ELF 逐条比对；chipyard 侧由 `m12-chipyard-007` 提供）
6. 现有 Tiny 测试零回归（`check-inst` / `check-arch` / tset 相关）
7. 构建/门控：`build-gem5` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0
8. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
9. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改 chipyard 侧（`m12-chipyard-007`）
- 不实现 smon（Tiny 不实现）
- 不改 spec（`Machine-v5` 的 Tiny hmon 由 SPEC 任务先落地；本任务按 spec 实现）

## 说明

- **前置**：spec 的 Tiny hmon 修订必须先落地（见 M13 的 SPEC 任务），否则本任务无依据。
- 组件单写者；节点操作后 `make sync-node-repo`。

## 审阅记录

### 第 1 轮 engineer 自审

逐行核对 `tiny_cfx.{hh,cc}`、`fs_tlb.*`、`fs_machine.*`、`fs_workload.*`、`inst.cc`、`isa.*`、`fs.py`、`faults.hh`；实跑 `build-gem5`、`check-gem5-decode`、`check-inst`/`-smoke`、`check-tests-index`、`check-index-blobs`、`check_tiny_hmon`、evidence `run.sh`（fast + `--inject`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| IALIGN 分支写反（`br.z` 让非 IALIGN 也走 recovery，RECOVERY=0 死循环） | ✅已修 | `tiny_hmon.S` 改 `br.nz` | checker 148 PASS；inject 15/15 |
| 手写 power cg7 start 期望值算错（0x3FFFF0000） | ✅已修 | 改 0x3FFFFFF0000；oracle 用 `bootrom_base-(63<<42)` | record 14 PASS |
| MALIGN2 用 `ld.uw`（2 字节）未触发 | ✅已修 | 改 `ld.ut`（4 字节） | record 27 MALIGN PASS |
| `rb2rd` immu6=0 返 ILLI，handler 首条自陷 | ✅已修 | handler/IALIGN 全改 immu6=1 | 全部 36 记录 PASS |
| Tiny `--trace-cpu` 误复用 Node dump | ✅已撤 | 撤回 `inst.cc` tiny trace 调用 | build rc=0 |
| 证据脚本模型注入点最初落在不可达的 `tinyTrap` reserved 分支 | ✅已修 | 改注入 `mapExecFault` fs ILLI→UNDI | `--inject` 15/15 |

### 第 1 轮 reviewer 验收（2026-11-10）

**重跑记录**（workdir 内相对路径、rc 直取；长日志留运行期日志目录 `<任务ID>-rv-*.log`；判决全部基于我自己的执行输出，未采信完成区转述）

- `make check-patch-tree`→**2**：14 problem 全 `qemu:`（⑨/⑥各 7）；gem5 断言 0 问题——同一检查器只跑 gem5 → `sets=1 errors=0 patches=99`。根因：本分支 `components/qemu/patches` 落后 master（`31258e3b` 改的正是这 7 份），共享组件源树已按 master 落地；7 份源树 HEAD diff 与 **master** 补丁逐字节相同、与本分支不同 ⇒ 合入后即绿，非本交付物。
- `make check-source-state`→**0**（12 源树全 OK；gem5 `HEAD=bcedd9d count=1 clean=True`）。
- `make install-host`→**0**（`install-host: PASS`）；`make check-modules`(L2)→**0**（`module checks (L2): PASS`）；`make check-arch`→**0**（arch-smoke + 044/045/049/039/040/042/044/046/047/048/049/050/051 全 PASS）。
- `make check-inst`→**0**：Vast 985 total / 980 passed / 0 failed / **5 deferred**（reg-cond-assign[15-19]，既有声明在 `tools/qemu/semantics_gate.py`，本任务未改该文件）+ Tiny **44/44**；`check-inst-smoke`→**0**（90/90）；`check-unit`→**0**；`check-tests-index`→**0**（**243**）；`check-index-blobs` / `check-gem5-decode` / `check-run-artifacts` / `check-tasks` / `check-no-residue`→**0**。
- `make check`(L1)→**2**、`make -k check`→**2**，3 红逐条归属：① `check-patch-tree`（同上，分支落后）；② `check-knowledge-refs` 2 条 `.work` 引用全在 `m12-spec-002` 任务书；③ `check-temp-dirs` 5 项全他任务陈旧目录——**无一来自本交付物**。
- 证据脚本：fast→**11/11**；`--inject`→**15/15**（oracle 注入 rc=1 + 还原 md5 相等；模型注入 build=0/checker=1 + 还原回绿），与完成区数字逐条一致。
- **独立注入（改被测模型源、非期望值）**：`fs_tlb.cc` 的 `FaultCFXMEM`→`FaultMALIGN`（md5 `63cc487e…`→`9a53ce71…`）⇒ `build-gem5` rc=0 ⇒ checker **rc=1、3 FAIL**：`record 17/18/19 cause CFXMEM expected=0x2 actual=0x1000`；`cp` 还原 md5 相等 ⇒ 重建 rc=0 ⇒ checker rc=0（**148 PASS**）；组件源树 porcelain 空。

**约束核验**：改动 26 文件与完成区逐一对账（16 补丁 = 14 改 + 2 新、`series`、`changelog`、`tests/arch/hmon/` 4 件、checker、`tests/arch.yaml`、`tests/arch/README.md`、任务书），无越界；完成区 7 行、无运行期路径；HEAD `150f61bc` 未变、reviewer 未 commit；工作树干净（含我重跑残留的清理，见 ①）。

- 语义逐条（我读 spec 原文核对）：cause_id one-hot（CFXTRAP `1<<0` / CFXMEM `1<<1` / CFXREG `1<<2` / CFXESC `1<<3` / CFXPERM `1<<7` / ILLI `1<<8` / UNDI `1<<9` / MALIGN `1<<12` / IALIGN `1<<13`，`DADAO-12 §5.2(二)`、`Machine-v5 §7.1`）；`info` = 指令编码（trap 0x7F / escape 0x7E / cfx2rd 0x7A / cfx2rc 0x7B，字段布局合 `SimRISC-00` ciii/crrr）或访存地址/IP（`DADAO-13 §2`）；IALIGN `cause_ip == cause_info == 非法 IP` 且不写回 nextIp；escape 仅 0/+4、SBZ→ILLI 先于任何状态切换、帧/目标错→当前 cfx 的 `CFXESC`；`trap` 两路（`immu18[17:8]==0x3FF` 短路、与 cfxha 无关）；移交流 power(cfx63)→hmon(cfx3)（handler 内 `escape cfx_hmon` 成功即证明 inner_cfx=3）；`DADAO-12 §5.2(三)` 步骤 4→5→6→7 与 `Machine-v5 §7.1` 兜底一致；cg7 的 desc/start/size/attr 与 QEMU 实现**逐值相同**。
- 测试资产：`arch-hmon-001` 已进 `tests/arch.yaml`（`level: full`、`requires: gem5-fs`），`check-index-blobs`/`check-tests-index` 绿；oracle **独立于实现**——cause id/info/cg7/几何逐条引 spec 条文，faulting IP 由 runner 现场 `llvm-nm` 解析，无一从 gem5 运行反推；checker 每条断言有可达 FAIL（注入实证，非恒真、无双写同值）。

**findings（不阻断，交 architect 收尾处置）**：

1. 证据脚本把工作目录放在与任务 worktree **同路径**的临时目录下，每次重跑会在仓库根留下 `c*-run/`、`*.bak` 共 **47 项**未跟踪残留（我重跑产生，已清理并复跑 `check-no-residue`/`check-run-artifacts`→0）；建议 TMP 改为 `<任务ID>-evidence` 兄弟目录，或改用 checker 默认的 `.dadao/tests/`（已 gitignore）。
2. 完成区④ 对 `check-patch-tree` rc=2 的归因已过时：qemu 源树现为 base+1 clean，真实原因是本分支补丁落后 master（合入即绿）。
3. **gem5 `tinyEnter` 不强制 hypv**（QEMU `cfx_enter` 对非 user profile 强制 `HYPV`）：guest 写 `switch_run_mode ≠ 3` 后异常即离开 hypv，与 `Machine-v5 §2`「运行模式恒 hypv、不能进入 user/jail/supv」不符；下游 `cg3 仅 hypv 可访问 ⇒ CFXREG`（`DADAO-13 §1`）gem5 亦未实现。属实现缺口、**不需改 spec**，建议一行对齐 QEMU（engineer 已登记为缺口，不在本任务验收项内）。

**判决：Accepted**。验收命令块在我自己的重跑下全绿（L1 / `check-patch-tree` 的 3 红已逐条归属为分支落后 + 他任务既有，非本交付物）；验收 5（三平台一致）仍 BLOCKED 于 `m12-chipyard-007`，按遗留登记；findings 1–3 由 architect 在收尾提交处置。

## 完成区

**测试结果**：`check_tiny_hmon` 148/148 断言通过（36 记录 = handover 1 + 寄存器/cg7 16 + 五类同步异常 15 + CFXTRAP/CFXESC/CFXPERM/CFXREG 4）；evidence fast 11/11、`--inject` 15/15（模型注入→FAIL→`cp`+md5 还原→回绿；源树恢复 md5 一致）。
**修改文件**：新增 `tests/arch/hmon/{tiny_hmon.S,tiny_hmon.lds,expected.yaml,README.md}`、`tools/gem5/check_tiny_hmon.py`；改 `tests/arch.yaml`、`tests/arch/README.md`、`components/gem5/changelog.md`、`components/gem5/series` 与 `patches/**`（14 改 + 2 新）；组件源一条 `dadao: gem5 patch series`（base+1，clean）。
**验收结果**：`build-gem5` rc=0；`check-gem5-decode` rc=0；`check-inst` PASS（Vast 980/985 通过 + 5 deferred；Tiny 44/44）；`check-inst-smoke` PASS（90/90）；`check-tests-index` PASS（243）；`check-index-blobs` PASS；`check-unit` PASS；gem5 `check-source-state` OK（HEAD=bcedd9d count=1 clean=True）；`check-run-artifacts` PASS。
**新发现/坑**：`rb2rd` immu6=0 ⇒ ILLI（块复制计数从 1 起）；DADAO `w`=16 位、`t`=32 位（4 字节用 `ld.ut`）；`LOAD_ADDR` 宏不能吃可重定位代码/数据标签（用 `.equ`+固定段）；escape 不恢复当前 cfx（镜像 QEMU/Node）；日志名须 `<TASK-ID>-*.log`。
**遗留问题**：① spec 缺口：`escape` 的「返回 cfx」在 §5.3 有文字但无 `prev_cfx` 保存寄存器（三平台均保持目标 cfx）；`cfx_power cg8 rc1` power ctrl 未建模（访问 ⇒ CFXREG，显式失败）。② 三平台一致（chipyard `m12-chipyard-007`）未落地 ⇒ 未逐条比对，本用例/oracle 可直接复用。③ 全局 `check-patch-tree`/`check-source-state` rc=2 仅因并行 `m13-qemu-001` 的 qemu 组件源树脏（gem5 断言失败 0）；`check-arch` 同一原因会重建 QEMU，已中止避免跨任务干扰。④ L1 另 2 红为既有：`m12-spec-002` 任务书 2 条 `.work` 引用、5 个其他任务陈旧临时目录。

#### 收尾（architect，2026-11-10 04:30）

- 第 1 轮 reviewer **Accepted**：补齐 `install-host`/L2/`check-arch` 全量（rc=0）；`check-patch-tree` 14 条全 `qemu:`（本分支落后 master，合入即绿），gem5 断言 0 问题。
- 独立注入（`fs_tlb.cc` 的 `FaultCFXMEM`→`FaultMALIGN`）⇒ checker rc=1、3 FAIL ⇒ 还原 ⇒ 重建 ⇒ 148/148 PASS。
- 期望值独立性：cause id/info/cg7/几何逐条引 `Machine-v5`/`DADAO-12`/`DADAO-13` 原文；faulting IP 由 `llvm-nm` 现场解析；无值从 gem5 反推。
- 与 QEMU 逐条一致：cause_id / cause_ip / info / escape / cg7 / `cg8 rc1` 全同。
- **一处未对齐（转 `ISS-363`）**：gem5 `tinyEnter` 直接取 `switch_run_mode`，guest 写 ≠3 后异常会**离开 hypv**（QEMU 强制 `HYPV`）；且 `cg3 仅 hypv 可访问` 未实现。不在本任务验收项内，M13 差分前修。
- 证据脚本临时目录落点建议（reviewer finding 1）：改用兄弟目录或 checker 默认 `.dadao/tests/`，避免仓库根残留。
