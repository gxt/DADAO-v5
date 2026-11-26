# m18-idl-003: IDL 执行器与 IDL-ISA 迁移到异步 escape（任务链第 3 环）

**模块**：idl
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入，F3 留下的 IDL 散文/渲染块由本任务补）、`m18-testcases-004`（向量）
**可并行分片**：否
**预估**：3–4 h（标定：同档 idl-002 2–3 h；本任务含 cg5/cg9 重排 + escape 重写 + IDL-ISA 散文与渲染，取 1.2–1.5×）
**档位**：中改（IDL 语义）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-spec-007` 已改规范与契约，但 `idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`、`spec/IDL-ISA §4.6` 散文及 `SimRISC-11` 的 IDL 渲染块仍是 R2/0.5.7 语义（seven-slot cg9、`imms18[1]` 恒 `CFXESC`、`cg5` 无出口意图）。`check-idl-sync` 之所以绿，是因为两边都旧；这会让 IDL 四方比对失去约束。

## 目标

1. **`idl/tools/idl_exec.py`**：
   - `cg5` 新布局（`rc0`–`rc3` 只读、`rc4/rc5`、`rc8`–`rc11`，`rc11` 复位全 1）；
   - `cg9` 新布局（`rc0`–`rc4`、`rc5` pending、`rc14` switch、`rc15` vector，`rc6`–`rc13` reserved）；
   - `cg0`–`cg3` switch/vector → `rc14`/`rc15`；
   - 进入自动填（同步/异步的写入集合不同，hart `cg5 rc0`–`rc3` 不写）；
   - `escape cfxHA`：`imms18=0`（非 0 `ILLI`）、`cfxha`=当前、不得升权、目标未实现/无 monitor ⇒ `CFXESC`、跳 `rc10`、`rc11` 整字写目标 monitor `cg8 rc1`、`escape_num` +1；
   - 删除旧的 cg9 七槽/`src_frame` 角色/`imms18[1]` 语义。
2. **`idl/SimRISC-11.idl` + 渲染块 + `spec/IDL-ISA §4.6` 散文**：同步新语义并重渲染（修 spec-007 的 F3）。
3. **`idl/data/exec_anchor.toml`/manifest** 重算；`check-idl-sync/-parse/-exec-anchor` rc=0。
4. 与 `m18-testcases-004` 向量交叉验证；`check-idl` 四方比对按新语义。
5. 不做：不改 QEMU/RTL/gem5/LLVM/内核。

## 验收（逐条贴真实 rc）

1. `idl_exec --self-test` 覆盖：cg5/cg9 槽位与权限、`rc11` 复位、进入写入集合、escape 五类判据、`rc11` 整字、`escape_num`；全 PASS。
2. `check-idl-sync`/`-parse`/`-exec-anchor`、`check-spec-codeblocks`、`check-manifests-guard` rc=0；`check-idl` 与 QEMU/RTL（可用者）一致，divergence 显式登记。
3. 可达 FAIL ≥2 路（旧 `imms18[1]`、`rc11` 增量），`cp`+md5 还原回绿。
4. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`、`idl/data/**`、`idl/.manifests.toml`、`spec/IDL-ISA-语义描述语言与语义库.md`、`spec/SimRISC-11-核芯功能扩展指令.md`（渲染块）、`spec/.manifests.toml`、本任务书。
3. 不改实现组件/契约（契约随 spec-007 已改）/`Makefile`；不改版本号；生成物用仓库工具重算；`cp`+md5 还原。

## 待裁定

无。

## 完成区

**测试结果**：`idl_exec --self-test` **119/119 PASS**；`check-idl` **274/274 rc=0**（含 `add.si_riii_rd`、`escape_ciii_cfx`、`cfx2rc/2rd_crrr_cfx`）；证据脚本 **14/14 PASS**（两路注入红→`cp`+md5 还原→回绿）。
**修改文件**：`idl/tools/idl_exec.py`、`idl/SimRISC-11.idl`、`idl/data/exec_anchor.toml`、`idl/data/idl_parse_fixture.json`（`--update`）、`idl/.manifests.toml`、`spec/IDL-ISA语义描述语言与语义库.md`、`spec/SimRISC-11-核芯功能扩展指令.md`（render 块）、`spec/.manifests.toml`、本任务书。
**验收结果**：`check-idl-sync`/`-parse`/`-exec-anchor`/`check-spec-codeblocks`/`check-manifests-guard` 全 **rc=0**（另 `check-spec-changelog`/`-purity`/`-refs` rc=0）；`check-idl` **rc=0** 274/274；testcases-004 交叉验证 QEMU：`arch-hart-001` 124 槽、`arch-pmem-001` 48 槽 rc=0；`add.si_riii_rd` 单例 rc=0。证据脚本：运行期证据目录内 `run.sh` → `checks: PASS=14 FAIL=0`、rc=0。
**新发现/坑**：① 基线"`add.si` step limit"的根因是**共享安装根的 BootROM 仍是 R2**（md5 `a5d788…`），R3 `hmon_tiny` 的 `cfx2rc cg5 rc10` 在 IDL R2 上反复 `CFXREG`；用当前源码 `make build-bootrom` 重建（md5 `5cee63…`，与 testcases-004 产物一致）即复现 step limit，迁移后回绿。QEMU 取 testcases-004 的 R3 构建（md5 `90b6bb…`）；两件工具链 provenance 已写进证据脚本。② `check-idl-parse` 的 AST fixture 与 `check-idl-exec-anchor` 必须分别在改 `.idl` 后 `--update`。③ IDL-ISA `0.1.1-rc` 变更记录条目按最终语义改写（版本号未动）；无调用者的 `cfx_frame_valid` 库函数删除，历史 0.1.0 条目保留同名。
**遗留问题**：① 异步进入路径仍只有自检白盒注入（Tiny 不实现 `cfx_hart`）；QEMU 侧由 `arch-hart-001`/`arch-pmem-001` 承接，IDL 四方清单无异步镜像。② `take_exception` 现按 R3 需要当前模式 monitor 的 `cg8 rc1` 快照；Tiny 仅实现 hmon，非 hypv 同步进入会显式 `ExecError`（fail-closed，当前 profile 无该载体）。③ 未跑 L2/L3 全量（`check-modules`/`check-full`）；按任务验收清单执行，且 `m18-linux-026` 长批占用门控。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`idl_exec.py`（cg5/cg9/cg3 槽位与权限、同步/异步进入写入集合、escape 五类判据、自检）、`SimRISC-11.idl`+render、IDL-ISA §4.6/0.1.1-rc、两处生成锁。逐行核对 R3 spec 与 testcases-004 向量。

**判决**：F1–F7 ✅已修/已处置；无未修阻断项，状态对账「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 共享 BootROM 为 R2，基线归因失真 | ✅已修（环境） | 用当前源码重建 BootROM 并固定 md5；QEMU 用 R3 构建 | `build-bootrom` PASS、md5 `5cee63…`；迁移前 3 例 step-limit、迁移后 274/274 |
| F2 `Machine.__init__` 给 `cfx_power cg5 rc0` 预置 3，违反"同步进入只写目标 cfx" | ✅已修 | 删除该预置；power 帧保持复位 0 | `escape_ciii` 检查点 13–16 PASS；274/274 |
| F3 `escape` 的 cfxha 不符先于目标校验，但 `cur=None` 时未在状态切换前失败 | ✅已修 | `escape` 先取 cur 并校验 cfxha/target；所有 `CFXESC` 在 mode/cfx/ip/mask/计数赋值前抛出 | 自检 `escape_*_keeps_state` 与注入 B 实证 |
| F4 cg9 rc0–rc5 写忽略但返回 0，读取语义未区分 HW/RO | ✅已修 | 写忽略、读原值；rc6–13 ⇒ CFXREG；rc14/15 写入按位宽截断 | 自检 `cg9_hw_ro_*`/`cg9_reserved_*`/`cg9_config_write` 全 PASS |
| F5 异步进入未验证"不写 hart cg5 rc0–rc3" | ✅已修 | 自检断言 `async_cg5_entry_not_written` 与 `async_exit_intent` | `async_*` 全 PASS |
| F6 旧 `imms18[1]` 语义残留 | ✅已修 | `_op_escape` 改为 `imms18 != 0 ⇒ ILLI`；删除 cg9 帧选择/偏移 | 注入 A 使自检 RED；全仓 idl/spec 现行条文 0 处 |
| F7 `rc11` 若增量写会破坏 fail-safe 策略快照 | ✅已修 | `escape` 整字赋值 + 自检 | 注入 B 使 `escape_ciii` RED；还原回绿 |


### 第 1 轮 reviewer 验收

**重跑（本人执行，仓库根）**：`idl/tools/idl_exec.py --self-test` → `self-test: 119/119 checks passed` rc=0；`make -s check-idl` → `check_four_way: 274/274 例四方一致（parties=idl,qemu）` + `check-idl: PASS` rc=0（全量日志 274 `[PASS]` / 0 `[FAIL]`，含 `add.si_riii_rd` 槽14、`escape_ciii_cfx` 槽28）；`check-idl-sync`/`-parse`/`-exec-anchor`、`check-spec-codeblocks`/`-changelog`/`-purity`/`-refs`、`check-case-ledger`、`check-tests-index` 逐条 rc=0。
**证据脚本**：仓库根执行运行期证据目录内的 `run.sh` → `INFO bootrom md5=5cee63c5b30afb8e5993f2eedc1ab962 qemu md5=90b6bba5e752b1f2262bea3e712320f4`、`checks: PASS=14 FAIL=0`、`m18-idl-003 evidence: PASS` rc=0。
**基线修复**：BootROM `5cee63c5…` / QEMU `90b6bba5…` 与 `m18-testcases-004` 同名产物 md5 逐字节一致；本人注入 R2 BootROM `a5d78816…` ⇒ `add.si_riii_rd [FAIL] 0/1` rc=1，`cp`+md5 还原后 `1/1` rc=0 —— 「R2 BootROM ⇒ add.si 红」根因实证。
**R3 语义**：cg5 rc0–rc5 HW/RO（写 ⇒ CFXREG）、rc8–rc11 RW、rc6/rc7/越界 ⇒ CFXREG、rc11 复位全 1；cg9 rc0–rc5 写忽略读原值、rc14 复位 2、rc15 48 位、rc6–13 ⇒ CFXREG；cg3 rc14/rc15 切模式/向量；同步进入写目标 cg5 rc0–rc5+rc8–rc11、异步写 cg9 rc0–rc4+hart cg5 rc8–rc11 且自检断言 hart rc0–rc3 不写；`escape` 判据齐全（imms18≠0、保留 cfx ⇒ ILLI；cfxha≠当前、升权、目标未实现、目标无 monitor ⇒ CFXESC，全部先于任何状态赋值）、rc11 整字写目标 monitor `cg8 rc1`、`escape_num`+1、跳 rc10；旧 `+0/+4` 偏移、`imms18[1]`、cg9 七槽语义已删。
**文档 F3**：`idl/SimRISC-11.idl` 与 `spec/SimRISC-11` 渲染块逐字节一致（`check-idl-sync` rc=0）；`spec/IDL-ISA §4.6` 现为 rc0–rc5/rc14/rc15 + 进入写入集合 + 出口意图，`cfx_escape_enter(cfxHA)` 单参、`cfx_frame_valid` 只存 0.1.0 历史条目；`imms18[1]`/`七槽`/`恒 CFXESC` 在 `idl/` 与两册现行正文 **0 处**（仅存「…作废」的正向表述）；`Toolchain-01` 旧语法系 spec-007 已披露遗留，不在本任务范围。
**范围**：9 文件与完成区声明逐一对齐；前后 md5 全等、`git status --porcelain -uall` 空、HEAD `0e97c880`；无 QEMU/RTL/gem5/LLVM/内核/契约/`Makefile` 改动；两 manifest 仅 `sha256` 行；远端无 `m18-idl-003`（未 push）；状态 `待验收`；完成区正文 5 行。
**注入（新角度，本人）**：C 把 `escape` 的 rc11 目标 monitor 改写为当前 cfx ⇒ `FAIL async_escape_return` rc=1；D 删 `target_mode > self.mode` 升权判据 ⇒ `FAIL escape_no_privilege_elevation` + `_keeps_state` rc=1；两次均 `cp` 备份 + md5（`bddf2fd900a27cb45a2e05708f16ec47`）对账还原 → 119/119 rc=0。
**`make check`**：rc=2，日志内唯一 `Error` = `check-syscall-abi`（缺 linux 源树，环境红）。make fail-fast 使其后 18 个目标未执行，本人补跑：6 红 —— `check-milestones-fresh`（9 项全为 m16-* 他册状态错位）、`check-width-sizes`/`check-components`/`check-linux-toolchain`（缺 clang/llc，未 `make install-host`）、`check-temp-dirs`（陈旧临时目录 + 盘 85.7%）、`check-interface`（lit 294 ≠ opcodes 309）；其输入均不在本 9 文件内 ⇒ 预存/环境红、非本改动引入；其余 12 项 rc=0。
**副作用**：本 worktree BootROM 已 R3，任务书「新发现/坑①」「F1」已记录 md5 与重建方式；合并说明尚未生成（收尾时补）。主仓与其余 worktree 的 BootROM 仍 R2 `a5d78816…` —— 门控按各自 `test_artifacts_dir` 取固件、互不影响；建议 architect 在合并说明提示「IDL 迁 R3 后 R2 BootROM 会报 step-limit」，供在跑会话（如 `m18-linux-026`）知悉（本审查不改他人文件）。
**硬约束**：① 独立 worktree、本次未提交（HEAD 仍 `0e97c880` WIP）、证据脚本在运行期证据目录内 `run.sh`；② 改动仅落在任务书允许的 9 个文件；③ 未动实现组件/契约/`Makefile`、版本号未升（`0.1.1-rc` 条目原位改写）、生成物由仓库工具 `--update` 重算、注入一律 `cp`+md5 还原（前后快照 md5 逐行相等）。

**判决：Accepted**
