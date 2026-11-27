# m16-chipyard-016: RTL cfx5 寄存器面

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点：RTL cfx5 只有阵列、无命令面）已合入
**可并行分片**：否
**预估**：3–4 h（GewuFile 寄存器行 + 参数 + 探针）
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

用户 2026-11-22 裁定：cfx 范围含 **cfx5 cache**；三个平台都要支持，缺啥补啥；每个 cfx 一件小任务。

现状：`WumingCfxHa` 只有 `hmon`/`power`/`ptw`，RTL 的 Vast 实现掩码里没有 cfx5；`WumingCache` 已有 D/I 阵列（`m16-chipyard-009/010`），但 cfx5 的寄存器/命令口未接线。`m16-spec-001` 已定义 `cfx_cache`（cfx5）寄存器与命令语义。

本任务只做**寄存器面**：让 `cfx2rd`/`cfx2rc` 能访问 cfx5 的 `cache_exist`/`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size`，命令暂不驱动阵列（命令接线是下一件）。

## 要做

1. **参数/序列**：`generators/dadao-wuming/.../WumingParams.scala` 的 `WumingCfxHa`（Vast）加入 cfx5；Tiny 不加（Tiny 无 cache）。
2. **寄存器行**：`generators/dadao-gewu/.../GewuFile.scala` 增加 cfx5 的 cg/rc 行，位域/读写属性按 `m16-spec-001` 与 `spec/Kaiwu §3.2` 现场解析（不手写魔数）；`cache_exist` 读 `0b11`（I/D），`cache_enable` 可读写，`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可读写、保留位按契约报 `CFXREG`。
3. **核分派**：`WumingCore` 的 `cfx2rd`/`cfx2rc` 路径能到达 cfx5；未实现命令编码按契约返回确定值/异常，不 panic、不静默。
4. **探针**：新增 RTL 探针（`tests/arch/cache/` 落点，按 `m16-testcases-006` 的骨架）读回 `cache_exist=0b11`、写读四个寄存器、非法编码 ⇒ `CFXREG`；只做寄存器面，不测阵列数据。
5. **Tiny 不回归**：Tiny 无 cfx5，`WumingTinyConfig` 的 cfx 序列与行为不变。

## 不做

- 不接线 `cache_ctrl` 命令到 D/I 阵列（下件任务）；
- 不改 `WumingCache` 阵列/Cache 逻辑；
- 不改 spec/契约；不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`components/chipyard/patches/**` + `series`），`make_patch.py chipyard` 幂等；
- 术语「寄存器组」；不写运行期路径；Tiny 的 elaboration 不得改变（对比 FIRRTL/探针）。

## 验证

运行期证据目录内的 `run.sh`：

1. Vast elab + 探针：`cache_exist=0b11`，四个寄存器写读回一致；非法编码 ⇒ `CFXREG`（`contract-see §6.1`）；
2. Tiny：cfx5 不在实现序列，访问 ⇒ `CFXREG`；Tiny 既有代表例（`tests/inst` 01 册或 `semihost_smoke`）不回归；
3. **可达 FAIL**：注入「Vast 的 `WumingCfxHa` 去掉 cfx5」⇒ 探针 `CFXREG`、红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`make check-tasks` 记录 rc；
5. `--inject` ≥2 路；
6. 注明重建耗时与所用环境（JDK/conda/`RISCV`），不把环境问题当代码失败。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（A–E）**58 PASS / 0 FAIL**，rc=0；`run.sh --inject` **20 PASS / 0 FAIL**，rc=0（2 路：RTL 去 cfx5、探针语义注入）。Vast 探针 22 条记录 / 176 B 逐条等于合约派生期望；Tiny `11-cfx` 5/5（含 cfx5 ⇒ `CFXREG` 的故障例）+ `01-load-store` 38/38，改前/改后逐镜像字节差 0。
**修改文件**：`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`、`.../dadao-wuming/.../WumingParams.scala.patch`（重导，26 补丁、24 unchanged）、`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/cache/{cfx5_regs.S,cfx5_regs.lds,check_cfx5_regs.py,README.md}`；`tests/arch/README.md`；本任务书。`WumingCore` 无需改动（decoder 的 `cfxAccessible` 已含 5，`gewu` 的 cfx2 路径是通用路径）；未改 spec/契约/QEMU/gem5。
**验收结果**：① 探针记录：exist=`0x3`、enable 复位 `0x3`、enable 0/1/3/全1=`0/1/3/3`、addr_start 全1=`0x00ffffffffffffff`、addr_start pattern=`0x003456789abcdef0`、addr_size=`0x123456789abcdef0`；5 条 no-op/合法写见证；4 类 `CFXREG`（非法 ctrl 编码、读 WO ctrl、写 RO exist、保留 rc）的 cause_id=`0x4`、cause_info=`0x7b148246/0x7a148245/0x7b148006/0x7a148045`。② Tiny 不回归：`11-cfx` 5/5、`01-load-store` 38/38；改前/改后 `.chipyard.out` 逐字节相同；Tiny `GewuFile.sv` 的 cfx5 寄存器符号（`cacheRdata`/`cacheCtrlLegal`/`addrStart_1`/`addrSize_1`/`enable_1`）=0。③ 可达 FAIL：inj1「Vast 去掉 cfx5」⇒ 首条访问 `CFXREG`、guest rc=126、oracle rc=1、0 条记录；`cp`+md5 还原并重建（1736 s）后 guest rc=0、流逐字节相同、oracle rc=0。inj2「探针把 enable 写 3 改成 2」⇒ 记录 4 `0x2 != 0x3`、oracle rc=1；还原后回绿。④ `check-patch-tree` chipyard 段 **0 problem**（26 补丁）；全局 rc=2 为 KNOWN-RED（musl ISS-507 / gem5/qemu 在途源树 ISS-463，逐行 diff 已打印）；`check-index-blobs`/`check-tasks`/`check-tests-index`/`check-source-state`/`check-component-changelog`/`check-knowledge-refs`/`check-dirs`/`check-no-residue`/`check-inst-macro-scope` 均 rc=0。⑤ 构建耗时/环境：Vast 全量 elab+Verilator **1836 s**、Tiny **78 s**；inj1 重建 **1817 s**、inj1 还原重建 **1736 s**；JDK `20.0.2-internal`、conda `Python 3.10.14`、`RISCV` 指向组件的 `.conda-env/riscv-tools`（gcc 13.2.0）、Verilator `5.020`。
**新发现/坑**：① 首次 elab 因漏把 cfx5 加进 `GewuParams.cfx` 序列而报 `cache.cfxId must name an implemented cfx`；补 `GewuCfxParams(id=WumingCfxHa.cache, …)` 后通过。② Tiny FIR 里 `cache` 字样 1.6 万次来自 chipyard L2/InclusiveCache，**不能**用泛 `grep cache` 判 Tiny 零增益；须用 cfx5 专有符号（`cacheRdata`/`cacheCtrlLegal`/`addrStart_1` 等）。③ `check-patch-tree` 全局基线红：并发会话在 gem5/qemu/musl 的共享源树推进导致错误集移动（ISS-463/507）；本任务只断言 chipyard 段 0 并打印逐行 diff，记 KNOWN-RED。④ writer-guard 在 `01-load-store` 两次拦下（他人 `install-host` 改 qemu/llvm；一次 qemu 二进制在批中被替换）⇒ 用 `--allow-concurrent` + 自校验 chipyard sim md5，判据仍绑定本任务二进制。⑤ 既有 `vastptw` 探针在本任务的新 Vast 二进制上于 TL `A channel re-used source ID` 断言处 abort；reviewer 核到“旧基线二进制”那份实为 `*** FAILED *** (timeout) after 5000001 simulation cycles`，且该基线早于 009/010（无 `WumingCache`），跨两版差异不能归到本任务。`vastptw.S` 不引用 cfx5、`GewuFile.io.cache` 无消费者、本任务在 TL 路径无逻辑改动 ⇒ 仍非本任务回归，未纳入证据；TL 断言另开 issue 追根因。⑥ 契约 CACHE-03 明确 `cache_ctrl` 是 **WO**，任务书「写读四个寄存器」按「enable/start/size 写读 + ctrl 写」落地；读 ctrl ⇒ `CFXREG` 已由探针覆盖。⑦ 服务器重启中断了首个 `--inject`（inj1 红与 source 还原已完成）；用 `INJ_RESUME=1` 复用红态证据并补还原重建/回绿与 inj2，日志分 `inject-run.log` + `inject-resume.log`。
**遗留问题**：① `cache_ctrl` 命令到 D/I 阵列的接线（下一件任务，`GewuFile.io.cache` 已输出 enable/addr_start/addr_size/control，无人消费）。② 本探针暂未登记 `tests/arch.yaml`：`run_arch.py` 的 chipyard 后端仍 fail-closed，且同 scope 其它 cfx 未接 RTL。③ 全局 `check-patch-tree` KNOWN-RED（ISS-463/507），非本任务引入。④ 既有 `vastptw` 的 TL 断言失败未追根因（基线既有，超出本任务范围）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile.scala` 的 cfx5 参数/五行/读写权限/ctrl 判序/写回/输出；`WumingParams.scala` 的 Vast 序列与 Tiny `None`；decoder/核心 cfx2 通用路径；探针 22 条记录与 checker 的合约现场解析；证据脚本的 rc 捕获、注入还原与基线红处置。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 漏把 cfx5 加入 `GewuParams.cfx` ⇒ elab `require` 失败 | ✅已修 | Vast 序列追加 `GewuCfxParams(id=WumingCfxHa.cache, …)` | Vast elab rc=0、`%Error`=0 |
| F2 Tiny 零增益判据用泛 `grep cache` 会被 chipyard L2 命中（1.6 万处） | ✅已修 | 改 cfx5 专有符号（`cacheRdata`/`cacheCtrlLegal`/`addrStart_1`/`addrSize_1`/`enable_1`） | Tiny SV/FIR 对应符号均为 0 |
| F3 探针未覆盖「保留 rc ⇒ CFXREG」「读 WO/写 RO」 | ✅已修 | 增 f2/f3/f4 三个故障例（22 条记录），checker 同步 | 22 条逐条 OK、`--self-test` 22 个 mutation 全红 |
| F4 checker 的 `cfx()` 硬编码 cfxha=5、cg=8 | ✅已修 | cfxha 从 `contract-cache` 标题解析、cg 从 CACHE-03 行解析 | `--self-test`/`--expected` rc=0 |
| F5 `--inject` 未置 `DO_INJECT`、F 段 `}` 误写 | ✅已修 | 入口置 `DO_INJECT=1`；补齐 `fi` | `bash -n` rc=0、`--inject` 20 PASS |
| F6 writer-guard 把他人替换 qemu 判成本批失败 | ✅已修 | 批内 `--allow-concurrent` + 自校验 chipyard sim md5 | 两册 5/5、38/38，sim md5 前后不变 |
| F7 `check-patch-tree` 全局红按组件豁免不合基线红规则 | ✅已修 | 打印非 chipyard 错误集逐行 diff；chipyard 段单独断言 0 | A 段 PASS=20、KNOWN-RED 行注明 ISS-463/507 |
| F8 服务器重启中断首个 `--inject` | ✅已修 | 加 `INJ_RESUME` 复用 inj1 红证据，补还原重建/回绿与 inj2 | `inject-resume.log` 20 PASS / 0 FAIL |

判决：全部 finding 已修（F8 为运行中断的处置而非代码缺陷）；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（均在仓库根执行运行期证据目录内的 `run.sh`，全部为我自己的输出/退出码）**

1. `run.sh`（A–E，含 no-op 重建）⇒ `summary: PASS=58 FAIL=0`、`RESULT: PASS`、退出码 0；A 段 `check-patch-tree: chipyard assertion problems expected=0 actual=0`、`make_patch.py idempotent expected=0 actual=0`；D 段 22 条记录逐条 OK、176 B；E 段 11-cfx 5/5、01-load-store 38/38、逐镜像字节差 0。
2. `INJ_ONLY=2 run.sh --inject` ⇒ `PASS=11 FAIL=0`、退出码 0：inj2 注入 → `oracle rc=1`（`record 4 … 0x0…02 != 0x0…03`）→ `cp`+md5 还原（`088a198546983c6cef09a795add51150` 与改前同）→ 回绿、`stream == reference`。
3. 独立 RTL 反例（不重建）：把探针 ELF 跑在改动前的 Vast 二进制上 ⇒ guest rc=126、0 条记录、判据 `FAIL (records: got 0, expected 22)`。
4. `check_cfx5_regs.py --self-test/--expected` rc=0（22 条 mutation 全红）；4 条 `cause_info` 我按 `contracts/opcodes.yaml` 独立解码 = ha5/cg8/rc9·9·0·1/rd6·5·6·5，与探针指令逐字段相等；`CFXREG` = `1<<2` 与 `contract-see` §6.1 一致。
5. 门控独立重跑 rc=0：`check-index-blobs`、`check-tasks`、`check-tests-index`、`check-source-state`、`check-component-changelog`、`check-dirs`、`check-inst-macro-scope`、`check-no-residue`、`check-knowledge-refs`。`check-patch-tree` 全局 rc=2（30 problem 全在 gem5/musl/qemu；chipyard 段 0，我逐行核过日志）。`check-run-artifacts` rc=2，0 条涉本任务（全在他人 m14-linux-025 日志，本任务未声称该项）。
6. 快照对账：验收前后 `git status --porcelain -uall` 逐行相同 = 7 modified（本任务书、`components/chipyard/{README,changelog}`、两补丁、`tests/arch/README`）+ 4 untracked（`tests/arch/cache/` 四文件）；探针与两补丁 md5 未变；未提交 git。

**约束核验**

- 补丁与源树一致：`git diff HEAD^ HEAD -- <file>` 与两 `.patch` 逐字节相同；`apply_series.py --component chipyard` rc=0（base+1, matches patches）；`make_patch.py chipyard` 0 written / 26 unchanged；`check-patch-tree` chipyard 段 0 problem。✅
- 语义：CACHE-03 五行位号与 RO/WO/RW、CACHE-06/27 `0b11`、CACHE-07 复位=exist 且缺位写 1 无效、CACHE-18 `PA[55:0]`、CACHE-12/13 无条件 no-op、CACHE-14 ⇒ `CFXREG`，与 RTL（五行解码、`cacheCtrlLegal`、`addrStart := wdata(55,0)`、`enable := wdata(1,0)&exists`、`cache_ctrl` 不进读通路）逐条对上；读 WO / 写 RO / 保留 rc 由探针 f1–f4 覆盖。✅
- Tiny 不回归：`WumingTinyConfig` 走 `WumingCoreParams` 默认 `useVM=false` ⇒ `GewuParams.cache=None`、cfx 序列仅 hmon/power；Tiny `GewuFile.sv`/FIR 的 cfx5 专有符号计数 0；两册改前/改后逐镜像字节相同。✅
- 未登记 `tests/arch.yaml` 属有意：`tests/arch/cache/README.md` 与 `tests/arch/README.md` 已写明（chipyard 后端 fail-closed，`run_arch.py` 自检确认「后端 fail-closed」），同 scope 的 `arch-ptw-*` 亦未全量登记。✅
- 术语「寄存器组」、任务书自包含：本记录不出现任何具体运行期路径。✅

**未独立重跑（如实披露）**：inj1 的 RTL 源注入 + 两次全量重建（日志记 1817 s / 1736 s）只做日志与还原 md5 核验（`de6aed2eb33aef71d64d5a61a2cc0c5d` = 当前源树；guest exit status 126、0 条记录、`oracle rc=1`）；RTL 侧可达 FAIL 由上条「改动前二进制」反例独立覆盖，未再花 30 min 重建。

**finding（均不阻断）**

- F1 `run.sh` A 段「chipyard 段 0 problem」的正则只认 `assertion|problem|ERROR|MISMATCH|FAIL`，会漏 `missing series`、`patch set does not apply cleanly` 等无关键词的 chipyard 错误。本次我直接 grep 全日志确认 chipyard 段确为 0（仅两行 `N patch(es)`），非凑绿；建议改成「除 `N patch(es)` 汇总行外无任何 `check-patch-tree: chipyard*` 行」。
- F2 完成区坑⑤「新旧两版 Vast 二进制都在同一 TL `A channel re-used source ID` 断言处 abort」与日志不符：旧二进制那份是 `*** FAILED *** (timeout) after 5000001 simulation cycles`，并无该断言；且该「基线」二进制早于 009/010（无 `WumingCache` 符号），跨两版差异不能归到本任务。结论方向仍成立（`vastptw.S` 不引用 cfx5、`GewuFile.io.cache` 无消费者、本任务在 TL 路径无逻辑改动），请改措辞，TL 断言另开 issue 追根因。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、硬约束无违反；F1/F2 为不阻断 finding，由 architect 收尾处置。
