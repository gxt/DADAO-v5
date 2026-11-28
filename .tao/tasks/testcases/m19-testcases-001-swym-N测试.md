# m19-testcases-001: swym N 测试程序（12 位、1+N、SBZ/ILLI、原子）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-001`；`m19-gem5-001` / `m19-chipyard-003`（周期与中断用例）
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：已验证

## 背景

现有 `tests/inst/12-misc/swym_oiii_imm.S` 只覆盖 `swym 0` 的功能/编码，明确把 N 的时延倍数列为 GAP。用户 2026-11-27 定了 N=12 位、1+N 拍、高位 SBZ/ILLI、原子中断；需要一个测试程序把这几条固定下来。

## 目标

1. 在 `tests/inst/12-misc/`（或现有 `swym_oiii_imm.S` 扩展）增加一个测试程序，覆盖：
   - `swym 0` ⇒ 1 拍；`swym 1` ⇒ 2 拍；`swym 4095` ⇒ 4096 拍（以 trace/cycle 为准）；
   - `immu18[17:12] != 0` ⇒ `ILLI`；
   - 原子：`swym` 期间 pending 中断不进入，完成后才取（若 Tiny 无中断源，按 `m19-chipyard-003` 的披露口径处理）。
2. 签名/退出码：功能项走现有 signature；周期项允许用引擎 trace 断言，不把宿主时间当 guest 时间。
3. 跨引擎：QEMU 只验功能（NOP，不验时延）；gem5 与 chipyard 验 1+N 与原子。

## 验收（逐条贴真实 rc）

1. 新测试在 QEMU / gem5 / chipyard 上跑通；功能项退出码/签名一致。
2. 周期断言：N=0/1/4095 分别为 1/2/4096 拍；给出 trace 证据。
3. 高位非零 ⇒ ILLI，`cause`/槽位正确。
4. **可达 FAIL ≥2 路**：① 改期望周期 ⇒ 红；② 把高位非零期待成成功 ⇒ 红。
5. `check-inst-asm` / `check-tests-index` 真实 rc=0。

## 约束

独立 `git worktree`；**不提交 git**；不改 QEMU/gem5/chipyard 源码（只加测试资产）；不接板；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本（运行期证据目录内 `run.sh`）A–E **PASS 46 / FAIL 0**（rc=0）；F（`--inject`）**PASS 19 / FAIL 0**（rc=0）；整段 `run.sh` 合计 **PASS 65 / FAIL 0**（rc=0）。引擎：gem5 策略 harness 12/12（N=0/1/0x7FF/4095 ⇒ total 1/2/2048/4096、extra=N、高位被掩）；gem5 FS 探针 rc=0，guest 实测 `d0=26 d1=27 d2=4121`（Δ=1/4095）、`cause_ip=0xffffffff10b8`、`cycle=10855`、`count=1`；chipyard Verilator Tiny（sim md5 `8733c7a2…`）sim rc=0、`check_swym.py` **46/46**（`swym-done−swym+1` = 1/2/4096、三处高位 ILLI）；tests/inst 载体在 gem5 与 chipyard 完整镜像（链例 11 + 故障例 4）rc=0、88 B 签名流 `79893035…` 逐字节相同；QEMU 功能子集 rc=0 且同一 88 B。
**修改文件**：`tests/inst/12-misc/swym_oiii_imm.S`（重写：`swym 0/1/42/7/4095` 功能与单条 4 B、4 条 `immu18[17:12] != 0` ⇒ ILLI（H=0x1/0x20/0x3F/0x20+合法低位）；删除按新语义已非法的「高位非零仍成功」旧例与旧「约 N+1 倍/可设上限」GAP 表述）、`tests/inst/inventory.md`（swym 行 legality/boundary 改为 ✓）、`tests/case-ledger.tsv`（`check_case_ledger.py --write` 重生成，diff 仅 swym 行）。
**验收结果**（真实 rc）：`check-tests-index` 0；`check-inst-macro-scope` 0；`check-case-ledger` 0；`validate-vectors` 0（156/156、274 载体）；`check-index-blobs`/`check-dirs`/`check-no-residue` 0。**QEMU 腿 BLOCKED（如实记录）**：完整镜像 rc=12（0 B，停在第一个 ILLI 例；QEMU 正常启动、**无拒绝串**；旧 QEMU `trans_swym_oiii_imm` 是无条件 NOP，无 SBZ/ILLI）；`make check-inst-asm`（共享安装根）rc=2、**0/274**——安装根 bootrom 正被 Tiny 新几何迁移连续改写（两次观测 md5 `f8ef553e…`/`083710b1…`，基线 `5cee63c5…`），旧 QEMU 不接受；钉住基线产物（旧 bootrom+旧 QEMU）跑同一 runner：**273/274**，唯一 FAIL = `swym_oiii_imm.S` rc=12。
**可达 FAIL 3 路**（均 `cp`+md5 还原后回绿）：① chipyard 周期期望改 `1/1/4096` ⇒ checker rc=1（`N=1 total cycles expected=1 actual=2`）；② 载体链例里加 `.dd.t32 0x47881000`（高位非零当成功）⇒ 静态 oracle rc=1，红点 `[FAIL] carrier: no high-bit word outside the fault section (['0x47881000'])`；③ chipyard 探针把 `0x47881000` 改成合法 `0x47880000` ⇒ RTL 上 ILLI 消失，checker rc=1（`ILLI fault count expected=3 actual=0`）。
**新发现/坑**：① 共享组件树会被别的会话注入→重建（本任务实测 chipyard sim md5 由 `8733c7a2…` 变 `e10693c4…`，周期即从 1/2/4096 变 2/3/4097），安装根 bootrom 同样在迁移中被改写 ⇒ 证据必须钉二进制副本**及其共享库**（`libriscv.so`/`libdramsim.so`/`libatomic.so.1`——sim 的 RPATH 首段指向构建它的任务 worktree）、设 `LD_LIBRARY_PATH`、`ldd` 断言 0 个 `not found`，并做前后 md5 对账（`run.sh` 已内置）；② `writer_guard` 在有写者时以 rc=75 拒绝，本任务 gem5 腿等待 9 次（15 s/次）后成功，脚本内置 10×15 s 并记录次数；③ gem5 guest 侧只能测 `d(1)−d(0)`/`d(4095)−d(0)`（`d0` 含 `cfx2rd` 基线 26 拍），绝对 1 拍只能由引擎周期模型（`swymCycles = 1+N`）断言；④ Tiny 无中断源 ⇒ chipyard 原子性只作 RTL 静态检查，未写成行为已验证（行为依据 gem5 探针）；⑤ 注入 RTL 后探针自检即失败（`SYS_EXIT code=0x41` ⇒ sim rc=65），F 段按「基线/还原 sim rc=0、注入 sim rc=65」分别断言，不把注入跑写成绿。
**待裁定**：① L2 `check-inst-asm` 在共享安装根当前 rc=2/0-274（非本任务载体问题），本任务判据用钉住基线产物 273/274；274/274 待 `m19-qemu-002`（QEMU swym SBZ/ILLI，已另立）与 `m19-testcases-002/003` 几何迁移合入后由 integ 重跑。② QEMU 腿结论：阻塞点是 `trans_swym_oiii_imm` 无条件 NOP（非 entry 0x2000），完整镜像 rc=12、无拒绝串，已归 `m19-qemu-002`。

## 审阅记录

### 第 1 轮 engineer 自审

依据：`spec/SimRISC-12 §2`（N=12 位、SBZ/ILLI、1+N、原子）+ `contracts/opcodes.yaml`；逐行读 `.S`（点号 1..15 连续、故障例落点在链后）、`inventory.md` 行、证据脚本（oracle 的每个断言与三路注入路径）。判决：改动只落在任务允许的测试资产；引擎/安装根问题不掩盖、已披露。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 旧载体把「高位非零」当成功（4 例），与新 spec 冲突；chipyard-003 已登记为超时 KNOWN-RED | ✅已修 | 删除 3 条高位成功链例，新增 4 条 `TEST_FAULT_ENC … ILLI` | chipyard 完整镜像 rc=0（链例 11+故障例 4） |
| F2 QEMU 未实现 SBZ/ILLI ⇒ 完整镜像 rc=12 | 披露（BLOCKED，待 m19-qemu-001） | 不改 QEMU；功能项改用「去故障例的链例子集」并比对 88 B 签名流 | QEMU 子集 rc=0、md5 与两引擎相同；完整镜像 rc=12 已记录 |
| F3 证据会被别的会话重建的引擎/安装根移动（实测 sim md5 漂移 ⇒ 3/4097） | ✅已修 | `run.sh` 钉 chipyard sim+Scala、QEMU+基线 bootrom 副本，前后 md5 对账 | 钉住后 46/46、273/274，sim md5 运行前后相等 |
| F4 `check_cy_probe` 返回 `tail` 的 rc（注入 ①/③ 会假绿） | ✅已修 | 保存 python rc 再 `tail` | 注入 ①/③ 实测 rc=1，还原后 0 |
| F5 注入 ① 的 grep 方向写反（expected/actual 顺序） | ✅已修 | 改为 `N=1 total cycles expected=1 actual=2` | `run.sh --inject` 17/17 |
| F6 `make check-inst-asm` 在迁移中的安装根上判绿/红都失真 | ✅已修 | 拆成「记录共享环境 rc」+「钉住基线产物的同一 runner 判定」 | 273/274、唯一 FAIL=swym rc=12 |
| F7 `.S` 头「用例：semantic 5/IMmu18/位高位」等计数与错字 | ✅已修 | 头注释按实际 2/4/4/2 + 链例 11 改写 | 文件头与逐例注释一致（人工逐行核对） |
| F8 增删用例后 `tests/case-ledger.tsv` 漂移 | ✅已修 | `check_case_ledger.py --write` 重生成 | `check-case-ledger` rc=0；diff 仅 swym 行 |

**待裁定**：见完成区 2 项。

### 第 1 轮 reviewer 验收

**判决：Needs Revision** —— 证据脚本注入②的断言对其声称的条件不可失败、注入行缺前导 `.`，且完成区两处「红因/段号」与真实输出不符；除此之外本轮全部实测通过（下列每条均为 reviewer 亲自重跑，rc 取被检命令自身）。

**重跑记录**
- 仓库根执行运行期证据目录内的 `run.sh`（无参数，A–F 全段）⇒ `evidence: PASS=62 FAIL=0`、rc=0；分段实测 **A–E=45、F=17** ⇒ 完成区「A–E PASS 62」与实测不符（62 = A–F）。
- `run.sh --inject` 第 1 次（原样环境）⇒ `PASS=16 FAIL=1`、rc=1：`[FAIL] [high-bits-success RTL] restored checker rc | expected=0 actual=1`；根因＝pinned sim 的 RPATH 第 1 段指向 `m19-chipyard-003` worktree（已随收尾删除）⇒ `libriscv.so: cannot open shared object file`。
- `run.sh --inject` 第 2 次（补共享 `.conda-env/riscv-tools/lib` 到 `LD_LIBRARY_PATH`）⇒ `PASS=17 FAIL=0`、rc=0（重试 2/2，两次结果均留档，不以重试掩盖根因）。
- B：策略 harness 12/12（N=0/1/2047/4095 ⇒ 1/2/2048/4096、extra=N、高位被掩）；FS 探针 `d0=26 d1=27 d2=4121`（Δ=1/4095）、`cause_ip=0xffffffff10b8`、`cycle=10855`、`count=1` —— 与完成区逐字一致。
- C：`check_swym: PASS=46 FAIL=0`；1/2/4096；ILLI fault=3；sim md5 `8733c7a2…` 运行前后相等。
- D：gem5/chipyard 完整镜像 rc=0、QEMU 去故障例子集 rc=0，88 B `79893035…` 三方相同；QEMU 完整镜像 rc=12、0 B（qemu.log 仅 monitor 横幅、无拒绝串）。
- E：`check-tests-index`/`check-inst-macro-scope`/`check-case-ledger` rc=0；共享安装根 `make check-inst-asm` rc=2、**0/274**（bootrom `f8ef553e…` 8 KiB 新几何，274 例全红 ⇒ 环境迁移、非本载体）；钉住基线（bootrom `5cee63c5…` + QEMU `e470dc56…`，后者与当前共享 QEMU 二进制同 md5）⇒ **273/274**，唯一 FAIL＝`swym_oiii_imm.S … rc {qemu: 12}`。
- 另测 `validate-vectors` rc=0（156/156、274 载体）、`check-dirs`/`check-no-residue`/`check-index-blobs` rc=0。

**独立注入（reviewer 自做，`cp`+md5 还原后回绿）**
- 按其字面意图注入**正确格式**的高位链例词 `.dd.t32 0x47881000` ⇒ `ONLY=A` rc=1，`[FAIL] carrier: no high-bit word outside the fault section (['0x47881000'])`；还原 md5 `fa4db5d2…` ⇒ rc=0。
- 把链例检查点 9 期望 `0x14→0x10` ⇒ `ONLY=D` rc=1（gem5/chipyard/QEMU 三腿 rc=1、signature size 0）；还原 md5 相等 ⇒ rc=0。

**打回项（必修，均属脚本/完成区，不动 spec 与载体语义）**
1. `run.sh` 注入② 写成 `\tdd.t32 0x47881000`（**缺前导 `.`**）⇒ 该词从未进 `chain_words`；真实红因是删掉 H=0x1 故障例（`[FAIL] carrier: ILLI high segments … actual ['0x20','0x3f']`），完成区所写的 `no high-bit word outside the fault section` 当时是 `[PASS]`。修：注入行补 `.`。
2. 断言 `[high-bits-success] chain carried a high-bit word` 用 `grep -c 'high-bit word outside the fault section'`，**同时命中 PASS/FAIL 两支** ⇒ 对所声称条件不可失败（两支写同一结果）。修：锚定 `^\[FAIL\] carrier: no high-bit word outside`，并贴修后真实 FAIL 行。
3. `run.sh` 只钉 sim 二进制+Scala、未处理其 RPATH 依赖，且 F 段不校验 `CY_SIM_RC` ⇒ 环境一变整段跑不起来（原样 `--inject` rc=1）。修：脚本内设 `LD_LIBRARY_PATH` 或前置 `ldd` 检查，并断言 `CY_SIM_RC`；完成区「钉副本已内置」表述随之改准。
4. 完成区两处与真实输出不符须一并改正：「A–E PASS 62」（实测 A–E=45）；注入②红因（见 1）。

**约束核验**：期望独立派生 ✓（`word = 0x47880000 | (H<<12) | N` 与 spec §2 + `contracts/opcodes.yaml`（opc `0x47`/ha `0x22`/value `0x47880000`/`legality: immu18[17:12] == 0`/`encode_sbz`）手算一致；N=0/1/42/7/4095，4 条 ILLI `0x47881000/0x478A0000/0x478BFFFF/0x478A0007`，未见由 gem5/chipyard 反推）；越界 ✓（commit `9d8ae146` 仅改 4 文件、工作树与 gem5/chipyard 组件源树（git）干净、审前/审后 md5 逐行一致、未出 worktree）；原子性区分 ✓（C 段只断言 RTL 静态项并打印 NOTE，完成区/`.S` 头/`check_swym.py` docstring 均写明「Tiny 无中断源 ⇒ RTL 静态检查，行为归 gem5 探针」，未把静态写成行为）；不接板、不提交 git ✓。

**QEMU 结论（供主会话建任务）**：`target/dadao/insn_trans/trans_ctrl.c.inc:351` `trans_swym_oiii_imm` 无条件 `return true`、`insn.decode` 的 `swym_oiii_imm` 无 SBZ 约束 ⇒ 高位词不产生 ILLI；故障例 `__FAULT_BODY_END` 未触发即 `__EXIT 12` ⇒ 完整镜像 rc=12；同一 QEMU+基线 bootrom 下其余 273 例通过、去故障例子集 rc=0 且 88 B 相同 ⇒ **不是「旧 QEMU 拒绝 entry 0x2000」**。`m19-qemu-001` 只做 Tiny 几何/装载，**QEMU 侧 swym SBZ/ILLI 仍无任何任务承接 ⇒ 需另立任务**；`check-inst-asm` 返 274/274 亦须等该能力与几何迁移合入（完成区待裁定区待裁定①②由 architect 定，本轮不代决）。

### 第 1 轮返工处置（Needs Revision 后）

只改证据脚本与完成区；载体、spec、期望值未动（reviewer 已复核部分不再触碰）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 注入② 少前导 `.` ⇒ `dd.t32` 词未进链例，真实红因只是删掉 H=0x1 故障例 | ✅已修 | 注入行改 `.dd.t32 0x47881000` | 修前注入日志只有 `[FAIL] carrier: ILLI high segments … actual ['0x20','0x3f']`；修后新增 `[FAIL] carrier: no high-bit word outside the fault section (['0x47881000'])`，`--inject` 回绿 |
| R2 `chain carried a high-bit word` 的 `grep -c` 同时命中 PASS/FAIL 两支（恒真） | ✅已修 | 锚定 `^\[FAIL\] carrier: no high-bit word outside the fault section` | `--inject` 19/19，该断言 actual=1（仅失败支） |
| R3 pinned sim 的 RPATH 首段指向已删除的 chipyard-003 worktree ⇒ `libriscv.so: cannot open shared object file`（原样 `--inject` rc=1）；F 段不校验 sim rc | ✅已修 | 钉 `libriscv.so`/`libdramsim.so`/`libatomic.so.1` 进快照目录并 `export LD_LIBRARY_PATH`；C 段断言 `ldd … not found`=0；F 段按基线/还原 0、注入 65 断言 `CY_SIM_RC` | `env -u LD_LIBRARY_PATH run.sh --inject` rc=0、19/19；`ldd` 0 not found |
| R4 完成区「A–E PASS 62」与实测不符；注入② 红因写错 | ✅已修 | 改为 A–E 46 / F 19 / 合计 65；红因按真实 FAIL 行改写 | 分段 `ONLY=A,B,C,D,E` 46/0、`--inject` 19/0、整段 65/0，均 rc=0 |
| R5 注入 RTL 后探针自检即失败（`SYS_EXIT code=0x41` ⇒ sim rc=65），原断言只写 rc=0 会红 | ✅已修 | 该路断言 `CY_SIM_RC=65`；基线/还原断言 0 | `--inject` 19/19 |

**判决后状态**：`待验收`（本段只追加，未改写 reviewer 记录）。

### 第 2 轮 reviewer 验收

**判决：Accepted** —— 第 1 轮四项打回全部实测修复，其余承第 1 轮结论（本轮只读复核，未改被测产物、未提交 git）。

**重跑记录**（reviewer 亲自执行，一律 `env -u LD_LIBRARY_PATH`，rc 取被检命令自身）
- 运行期证据目录内 `run.sh`（A–F 全段）⇒ `PASS=65 FAIL=0`、rc=0；同份日志分段 **A–E=46、F=19**。
- `run.sh --inject`（工作目录预检分支被触发）⇒ `PASS=22 FAIL=0`（19 + 预检 3 条）、rc=0：`[preflight] sim rc | expected=0 actual=0`、`[preflight] baseline checker rc | expected=0 actual=0`。
- `ONLY=A,B,C,D,E run.sh` ⇒ `PASS=46 FAIL=0`、rc=0（含共享安装根 rc=2 / 0-274 记录，钉住基线 **273/274**、唯一 FAIL＝swym rc=12；`ldd` 断言 `expected=0 actual=0`）。
- 三个数字 46 / 19 / 65 与完成区逐一对上（第 1 轮「62＝A–E」的段号错已改正）。

**打回项复核**
1. 注入② 现为 `.dd.t32 0x47881000`（带前导点）。我重跑得到的真实红点＝`[FAIL] carrier: no high-bit word outside the fault section (['0x47881000'])`，同批另有 `chain immu18[17:12] == 0`、`ILLI high segments … ['0x20','0x3f']`。**修前差异真实**：第 1 轮同一文件该行是 `[PASS] … ([])`、红因只有 high segments（第 1 轮记录已留档）。
2. 断言已锚定 `^\[FAIL\]`（label 改为 `… (FAIL branch only)`）。**反证**：还原后的 oracle 日志 `grep -c '^\[FAIL\] carrier: no high-bit …'` = **0**，同文件不锚定计数 = 1（PASS 支仍打印但不再被计入）；注入后锚定计数 = 1。
3. 快照目录含 `libriscv.so`(177 MB)/`libdramsim.so`/`libatomic.so.1`（`cp -L` 实拷）；脚本内 `export LD_LIBRARY_PATH=<快照目录>` 生效 ⇒ `env -u LD_LIBRARY_PATH` 下三次运行全绿；`ldd` 断言 `expected=0 actual=0`（手工 `ldd` 同为 0 个 `not found`，libriscv/libdramsim 解析到快照目录）；`CY_SIM_RC` 四条均真实执行且可达 FAIL：C 段基线 0、F 段预检 0、注入 RTL **65**、还原 0。

**约束核验**：返工提交 `57d6cbbeb` 仅动任务书（`git show --stat` 1 file；`git diff 9d8ae146..57d6cbbeb --name-only` 只有任务书）⇒ 载体/spec/期望值/引擎源码未动；载体与两个引擎判据脚本等 5 文件 md5 与第 1 轮审后逐字节相同；状态 `待验收`；第 1 轮 reviewer 记录逐字未改（提交中无该段删除行，返工处置为追加段）；未出 worktree、未改主工作树。

**承上轮结论**：QEMU 腿 BLOCKED 已归 `m19-qemu-002`（主仓 `.tao/tasks/qemu/m19-qemu-002-swym-SBZ-ILLI.md` 已建、`milestones-m19.md` 已登行，完成区「已另立」属实）；`check-inst-asm` 返 274/274 待该能力与几何迁移合入后由 integ 重跑（待裁定①，architect 定）。
