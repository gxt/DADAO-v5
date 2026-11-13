# m12-chipyard-028: 用新 builder 重生成 chipyard `bootrom.tiny.hex`

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m13-integ-007`（新 hmon 算法已合入）
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-410`，P1）

chipyard 签入的 BootROM hex 仍是**旧 hmon**（`escape +4`、120 B），而 QEMU/gem5 用的共享镜像已是新算法（槽 `0xF8`、48 B）。`m13-testcases-012/013` 只能靠「测试运行期自装 hmon handler」绕过，三方固件行为实际不一致。

## 目标

1. 用 `tools/testcases/arch/build_tiny_bootrom.py` 重生成 `bootrom.tiny.hex`（目标解码镜像 md5 `514300876ea66ec108396334f3ef2b0f`）
2. 改源树 hex → `tools/infra/make_patch.py chipyard` 重导出 → `check-patch-tree` rc=0
3. 回归：`make build-bootrom`、chipyard 构建/Verilator、TestDriver

## 验收

1. 签入 hex 与共享镜像一致（解码后 md5 相同；**hex 文本 md5 另行记录**，两者不是一回事）
2. `check-patch-tree` chipyard 0 问题；`check-source-state` rc=0
3. `m13-testcases-012/013` 撤掉自装 handler 的 workaround 后**仍三方一致**
4. 完成区 ≤30 行；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

**范围**：hex 重生成 → 组件树 amend → 补丁重导出；`tests/inst/macros/inst_test.inc`、`inst-tiny.lds`、`MIGRATION.md`；`components/chipyard/{README,changelog}.md`；证据脚本 `run.sh`/`verify.py`。逐行读 diff，期望值取自 `spec/Machine-v5 §6.1/§6.2` 与 `hmon.S` 头布局，不从产物反推；三平台实测 235/235。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只换 hex 资源时 `sims/verilator` 的 `.classpath_cache/chipyard.jar` 不会失效（依赖只列 Scala/Verilog 源）⇒ 首次重建后模拟器仍跑旧固件 | ✅已修 | 构建前删该 jar（主控机/节点构建脚本、证据脚本同；README+changelog 记坑） | TLROM md5 `33bfe14a…`（旧）→`514300876e…`；chipyard 故障例 rc 点号→`0xF8/0xFC/0xF1` |
| F2 保留寄存器注释仍称 `rb31`=「故障 hmon 暂存」，与 02-reg-copy 把 `rb31` 当数据寄存器冲突 | ✅已修 | 删该注释行 | `grep -rn rb31 tests/inst` 仅 02-reg-copy 两处 |
| F3 证据脚本 B 段把本任务对 `components/chipyard` 的改动误判为「导出后不干净」 | ✅已修 | 改为 patches 目录 md5 前后比对 + `0 written` 双判据 | `run.sh` B 段 6/6 PASS |
| F4 主控机 gem5 二进制正被并行任务重建（一度消失、41 MB→736 MB） | ⏸绕行（不改判据） | 脚本按二进制存在性决定本地平台集；三平台以节点段为准 | 本地在其重建完成后 `chipyard,qemu,gem5` 235/235；节点 235/235 |
| F5 节点 chipyard 组件树只同步 hex，RTL 仍是节点自身 base+1（未跑 `apply-series`：节点 llvm-project 与主控机 manifest 代次不同而被拒） | ❌不修（披露） | 无（本任务未改 RTL；029 只动 FMA 注释/表） | 节点与主控机同一 ld/st 套件判据全同（235/235、0 FAIL） |

判决：F1–F3 已修复验，F4 绕行，F5 披露（不影响本任务判据）；状态 → `待验收`。

### 第 1 轮 reviewer 验收（独立重跑，2026-11-14）

**重跑记录（命令均在本任务 worktree 仓库根，退出码为现场实测）**
- `make build-bootrom` rc=0 → `bootrom_tiny.bin` md5 **`514300876ea66ec108396334f3ef2b0f`**、`bootrom.tiny.hex` md5 **`c499803ae452d21f372acdb5cad12f4e`**；**独立解码**签入 hex（自写内联解析，不走 verify.py）md5 `5143…` 且逐字节 == bin；hmon 44 B（`20 fc 00 dc`→0xF8、`7e 0c 00 00`）、44..48 填 0、`0x20D8..0x2100` 全 0、表项 `type=1 flags=0x3 off=0x2000 size=48 boot_magic=0x30001`、无 `escape +4`。
- `python3 tools/infra/make_patch.py chipyard` rc=0 → `0 written, 21 unchanged`；补丁 md5 `6537bfbb…` 复跑不变 ⇒ 签入补丁与现场产物一致、幂等。
- **独立注入（TLROM 路，非 engineer 的 2 路）**：hex hmon 首字 `21 fc 00 d8→22…`（md5 `e98b959a…`）→ 删 `.classpath_cache/chipyard.jar` + `generated-src/<cfg>` → `make verilog CONFIG=WumingTinyConfig` **rc=0**（只读 rc 即假绿）→ 解析 `TLROM.sv` md5 `51c1b4ea35bfa34c31ad75a1413fb4fc` ≠ 目标 ⇒ **FAIL 可达**；`cp -p` 还原 md5 `c499…` → 同法重建 → TLROM md5 `514300876e…` ⇒ **回绿**，chipyard 源树 clean。
- `bash .work/evidence/m12-chipyard-028/run.sh`（默认）**rc=0** `PASS=21 FAIL=0`（本机 chipyard,qemu,gem5 **235/235**）；`--inject` **rc=0** `PASS=29 FAIL=0`（H1 翻字节→解码红/还原绿；H2 one-hot→qemu 红/还原绿，`inst_test.inc` md5 `9fc6f2d9…` 复原）；`--node server208` **rc=0** `PASS=29 FAIL=0`（跑 2 次）。
- 节点 server208：`run_asm_suite: 235/235（38 id；链例 38，故障例 197）`、0 FAIL，故障例 rc 三方同 `0xF1=241 / 0xF8=248 / 0xFC=252`（= `0xF0|one-hot 位索引`）；节点 `build-bootrom` rc=0 且镜像 md5 `5143…`、节点签入 hex md5 `c499…`、节点 TLROM md5 `5143…`。
- 门控：`check_patch_tree --source-state` rc=1（llvm/qemu/gem5 源树被并行任务弄脏），**chipyard OK HEAD=3581343 count=1 clean**、testchipip OK；`check_patch_tree` rc=1 但断言行中 chipyard **0** 条（34 条全属 llvm/qemu/gem5）；`check-component-changelog` rc=0 PASS；`make check-inst` **rc=2**，`1141 total / 1135 passed / 1 failed / 5 deferred / 0 errors`，红集恰 `{divrem.yaml[23]}`。
- `grep -rn "__INSTALL_HMON|hmon_stub|TEST_HSEC" tests/` rc=1（0 命中）；`inst_test.inc` 故障例改 `__SET_HMON_RETURN`（写 `HMON_BASE+0xF8`）、落点读 `HMON_BASE+0xE0`，one-hot/退出码/点号断言与 `TEST_FAULT` 的 `__EXIT \pt` 未删改；`inst-tiny.lds` 只删 `.hmon_stub` 段（`.text ≤0x1E00` 断言保留）；与 `hmon.S` 固定布局（0xE0 cause_id / 0xF8 返回槽）一致 ⇒ 撤的是 workaround，不是弱化断言。

**约束核验**：越界=0（`b24137d4` 仅 7 文件：任务书/README/changelog/hex 补丁/inst_test.inc/inst-tiny.lds/MIGRATION.md）；完成区 19 行、第 1 轮自审 13 行；未提交 git；开工/收尾 6 文件 md5 逐项 `OK`、`git status -uall` 空、chipyard 源树 clean、无 `*_tmp*`/`*.orig`/`.preinject` 残留。
**未采信项（披露）**：Verilator 二进制强制重建（engineer 报 rc=0/111 s）我未重跑，改以「TLROM 独立重建 + chipyard 平台 235/235 行为」为准；`--full` 的 F 段由我直接逐个跑门控替代。
**finding（文档级，不阻断）**：完成区写 `--source-state rc=0`，我方实测 rc=1——根因 llvm/qemu/gem5 工作树被并行任务弄脏（chipyard/testchipip 仍 OK、base+1 达标），属环境性差异；收尾建议注明「chipyard 段 OK，整仓受他任务影响」。

**判决：Accepted**——上述判据在我的重跑下全部通过，注入→FAIL→还原→回绿三段均有真实输出与退出码。

## 完成区

**测试结果**：一键证据脚本默认模式 `PASS=21 FAIL=0`（EXIT=0）；`--inject` `PASS=29 FAIL=0`（EXIT=0，2 路注入均可达 FAIL 且 `cp`+md5 还原回绿）；`--node server208` EXIT=0；`check-inst` 净红仅既有 `divrem.yaml[23]`。

**修改文件**（`git status -uall` = 6 modified / 0 untracked，另本任务书）：① `components/chipyard/patches/…/dadao/bootrom/bootrom.tiny.hex.patch`（**唯一**重导出的补丁，其余 20 份 `unchanged`）；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④ `tests/inst/macros/inst_test.inc`；⑤ `tests/inst/01-load-store/inst-tiny.lds`；⑥ `tests/inst/MIGRATION.md`。运行期证据：证据目录的 `run.sh`/`verify.py` 与日志（未入库）。

**验收结果**：
- hex：解码镜像 md5 **`514300876ea66ec108396334f3ef2b0f`**（65536 B）、**hex 文本 md5 `c499803ae452d21f372acdb5cad12f4e`**；`layout power@0x0000(344) hmon@0x2000(44, padded 48)`；表项 `type=1 flags=0x3 off=0x2000 size=48`、`boot_magic=0x30001`；hmon 代码 **44 B**（11 条），`0x20D8..0x2100` 全 0（数据区不入镜像）。
- hmon 槽：`0x1C ld.o rd63,[rb0,0xDC]` ⇒ 读 **0xF8** 返回槽、`0x20 cfx2rc excp_cause_ip`、`0x24 →0xD8`；power `0x130 rb2rd` / `0x134 add.si 16` / `0x138 st.o [rb7,248]`（默认返回 `trap+4`）；hmon 段无 `escape +4` 旧策略。
- 组件与门控：`check_patch_tree --source-state` rc=0（chipyard 与 testchipip OK，HEAD `3581343` = base+1）；`make_patch chipyard` = `1 written, 20 unchanged`，复跑 `0 written`；`check-patch-tree` 整仓 rc=1 但 **chipyard 段 0 条**（红 = llvm-project 5 / qemu 4 / gem5 9，均他任务在飞组件）；`check-component-changelog` rc=0。
- 回归与三平台：`make build-bootrom` rc=0；chipyard 强制重建 elab rc=0 / Verilator rc=0 / `%Error`=0（111 s，删 generated-src 与缓存 jar），elaborated `TLROM` md5 == `514300876e…`；主控机 **chipyard+qemu+gem5 235/235**（38 链例逐字节 + 197 故障例比退出码，`--inject` 轮内完整跑过）；**节点 server208 三平台 235/235、0 FAIL**（节点自建模拟器 elab/build rc=0、0 `%Error`、221 s；节点 `build-bootrom` 复现同镜像 md5）。最终版脚本在 gem5 被并行任务反复重建时本地段自动降级 chipyard+qemu（235/235，打印 NOTE），三平台判据以节点段为准。
- workaround 撤除位置（旧版行号，`ISS-410`）：`inst_test.inc` L21–25（自装理由）、L35/L84（`TEST_HSEC`/布局）、**L823–835 `__INSTALL_HMON`（真 workaround）**、L837/L839（guard 调用）、**L1102–1115 `.hmon_stub` 自带处理器**、L1119（落点读 `TEST_FAULTV+32`）；`inst-tiny.lds` L8/L37–42（`.hmon_stub` 段 + ASSERT）；`MIGRATION.md` L173。撤除后故障例改写 `0xF8` 返回槽、落点读固件 hmon 的 `0xE0` cause_id。
- 注入（可达 FAIL）：① 签入 hex 翻 1 字节 ⇒ 独立解码 md5 不符（rc=1，还原后 rc=0、组件树 clean）；② `ILLI` one-hot `0x0100→0x0200` ⇒ QEMU 故障例退出码非期望（rc=1，还原 md5 `9fc6f2d9…` 后 rc=0）。
- `check-inst`：`1141 total / 1135 passed / 1 failed / 5 deferred`，唯一红 = 既有 `divrem.yaml[23]`（红集不变；make 包装 rc=2）。

**新发现/坑**：① 只改 hex 不会让 chipyard 的缓存生成器 jar 失效 ⇒ 必须先删 `.classpath_cache/chipyard.jar` 再 `make verilog`，否则静默沿用旧固件（首轮实测故障例 rc=点号、TLROM `33bfe14a…`）；② 「新固件是否真进模拟器」的可达判据 = 独立解析 `gen-collateral/TLROM.sv`（末地址在前、字内字节序反转）求 md5，只看 `make` rc 会假绿；③ `check-inst` 的 44 个 `skipped_profile` 为 Tiny 子集口径，与 red 集无关。

**遗留问题**：① `tests/inst` 其余册任务书（020–031）仍写「沿用 012 的 hmon 自装 workaround（`ISS-410` 未修前必须保留）」——已过时，建议主会话统一改为「已撤除」；② 节点 chipyard 组件树仅同步 hex（`apply-series` 因节点 llvm-project 与主控机 manifest 不同代被拒），RTL 用节点自身 base+1——本任务未改 RTL，判据不受影响；③ 主控机 gem5 在验证期间被并行任务反复重建（二进制多次消失/重现），本地三平台依赖其空闲窗口；证据脚本已按存在性降级并打印 NOTE，三平台判据以节点段为准。

