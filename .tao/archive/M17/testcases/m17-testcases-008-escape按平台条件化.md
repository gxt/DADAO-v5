# m17-testcases-008: `escape_ciii_cfx` 按平台能力条件化（Tiny 验证 CFXREG + DIV 逐槽声明）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-chipyard-002`（根因，已验证）、`m17-idl-026`（four-way 认 DIV `slots`，已验证）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-27 裁定 1）

根因（`m17-chipyard-002`）：Tiny RTL 无 `cfx_hmon` 的 `cg4`（`commonRows` 缺项）与 `cg15 rc3`（`asyncModel` 门控），用例无条件访问 ⇒ **CFXREG**（pc `0xffffff010160` / `0xffffff010164`），未武装进 `.faultpad` 以点号 0 退出 ⇒ rc=0 + 空签名。

用户裁定：**不造假常量、不跳过**。Tiny 缺这两个寄存器是**被验证的行为**：

- 受控触发访问，断言 `cause_id = 0x4`（CFXREG）、`cause_info = 该指令编码`；
- Tiny 的期望值写进 `tests/arch/expected-divergences.yaml` 的 `DIV-18` **逐槽声明**（`slots`: `case` + 0 基 `slot` + `chipyard`）；`idl_four_way.py` 已支持（`m17-idl-026`）；
- IDL/QEMU/gem5/Vast 路径保持现有真实检查逐条不变。

已实测：Tiny 的 `escape` 指令本身可用（硬件写 `cg15 rc3` 在 Tiny 为空操作、不报错）。

## 要做

1. **能力探测**（用例开头、武装故障例之前）：受控判断 `cfx_hmon` 是否有 `cg4`/`cg15 rc3`（沿既有 hmon handler + `__PREP_ESC` 落点机制），CFXREG 不当致命错误；
2. **有能力平台**（IDL/QEMU/gem5/Vast）：现有检查逐条不变；
3. **Tiny**：对 `cg4 rc5`、`cg15 rc3` 的每处访问，在受控 handler 下真实触发并把实测 `cause_id`（`0x4`）与 `cause_info`（指令字）写入对应签名槽——期望值从 spec 独立派生（CFXREG = `1<<2`；`cause_info` = 编码），不抄其它平台输出；
4. **`DIV-18`**：补 `cg4`；加 `slots` 逐槽声明（`case: escape_ciii_cfx` / 0 基槽号 / `chipyard` 期望值）；`close_when` 与 impact 文本同步（写明「Tiny 期望 CFXREG + 槽值由本条目声明」）；
5. 订正 `.S` 头 GAP 注释（现与代码矛盾）；
6. 其它检查（落点、`cg5` 帧、rc8–rc11、返回值）在 Tiny 仍真实执行。

## 不做

- 不改 RTL/QEMU/gem5/IDL 语义；不改 `idl_four_way.py`（`m17-idl-026` 已做）；
- 不改 `expected.tsv` 槽数；不放宽 IDL/QEMU/gem5 的真实检查；
- 不写常量槽（P0/P1/P2/1 之类）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `tests/inst/11-cfx/escape_ciii_cfx.S`、`tests/arch/expected-divergences.yaml`（`DIV-18`）、必要的生成物（`tests/data/inst-signature/{expected.tsv,inputs.sha256}`，不得改槽数）、`components/chipyard/README.md`（如 GAP 说明需同步）+ 本任务书；完成区 ≤30 行；`**状态**` 改 `待验收`。

## 验证

1. `make check-idl-full` **274/274**（chipyard 签名非空；其余三方逐字节一致；`DIV-18.slots` 生效并输出标注）；
2. **可达 FAIL ①**：把 `DIV-18` 声明值改错 ⇒ 该例必红（`m17-idl-026` 的「值需更新」路径）；还原回绿；
3. **可达 FAIL ②**：Tiny 侧改错探测落点/期望 ⇒ 红；还原回绿；
4. **可达 FAIL ③**：有能力平台（QEMU/gem5）改错 `cg15 rc3` 值 ⇒ 必红（证明未放宽）；还原回绿；
5. Tiny 槽值的 **spec 推导**写明（CFXREG 位号、`cause_info` = 指令字编码）；
6. `make check-idl` 274/274；`check-knowledge-refs` rc=0；`git status -uall` 仅允许文件 + 任务书。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`.S` 的能力探测/handler/6 个检查点、DIV-18 的 8 个 `slots`、重生成的 `expected.tsv`/`inputs.sha256`、证据脚本（含三路注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 探测异常会重写 hmon 帧，点 19（`cg5 rc0`=prev mode）在 Tiny 上退化为读相邻探测帧 | ⏸延后（披露） | 不改点号/帧（整帧保存-还原超出本任务范围） | 点 19 实测 3 = prev mode 全绿；有能力平台无探测异常，语义完整；见「新发现」① |
| F2 全局 `PB_ARM` 在 5 条指令窗口内可能误吸非探测异常 | ❌不修 | 窗口内只有被测访问 | 三路注入均在访问处按预期红 |
| F3 初版 `__CHECK_RD_OR_CAUSE_BASE` 记录 `\dst`，QEMU/gem5 槽 12 由 1 变 2 | ✅已修 | 改为记录 `\rec_exp`（与原 `__CHECK_RD 12` 口径一致） | QEMU/gem5 槽流 md5 回到基线 `25f3d355…` |
| F4 `PB_15`/`PB_4` 诊断槽是死写 | ✅已修 | 删除两槽及其 PACK/store | 宏作用域门控 + 全量四方复跑绿 |
| F5 打包可能把 cause_info 上位当有效位 | ✅已修 | 打包前 mask 32/16 位；命中判据用 64 位 `==0x4`（顺带断言子原因 wyde 为 0） | 槽值 = `(enc<<32)|4` 与 DIV 对账 |
| F6 DIV 值可能从实测反填 | ✅已修（独立派生） | `derive_check.py` 由 `contracts/opcodes.yaml` + `.S` 调用点重算槽值并与 DIV 逐槽比对 | 注入① 静态 rc=1、还原 rc=0 |

**判决**：无未修 finding（F1 已披露、F2 有据不修）；状态对账「待验收」。

### 第 1 轮 reviewer 复核

- **重跑（我的执行）**：仓库根运行运行期证据目录内的 `run.sh` ⇒ **32 PASS / 0 FAIL、RUNSH_EXIT=0**；其三路自注入我逐条核过判据可达（DIV 值→静态 rc=1 + 四方「声明值不符」rc=1；`__PACK_CAUSE` 移位 32→33→rc=1；`P1` 1→2→「期望 0x…1 实际 0x…2」rc=1），均 `cp`+md5 还原回绿，产物 md5 回注入前。
- **门控（我的输出）**：`make check-idl-full` rc=0、**274/274**（parties=idl,qemu,gem5,chipyard）、日志 `DIV DIV-18` **恰 8 条**；单例四方 `[PASS] escape_ciii_cfx 槽 28 / rc {idl:0,qemu:0,gem5:0,chipyard:0}`、四方各 224 B（基线主树日志 273/274、该例 `签名字节数 0 ≠ 224` ⇒ Tiny 由 0 B 恢复）；`make check-idl` rc=0（274/274）；`check-inst-asm` rc=0（274/274）、`check-tests-index` rc=0（503 条）、`check-knowledge-refs` rc=0。
- **spec 独立派生（我自己重算）**：按 `contracts/opcodes.yaml`（opc 0x7A、`cfxha[23:18]`/`cghb[17:12]`/`rchc[11:6]`/`rdhd[5:0]`）算得 `cfx3,cg15,rc3,rd5`=0x7a0cf0c5、`cfx3,cg4,rc5,rd5`=0x7a0c4145、`cfx63,cg4,rc5,rd5`=0x7afc4145，`(enc<<32)|(1<<2)` 与 DIV-18 三组值逐位相等；`CFXREG=1<<2`、`cause_info=指令编码`（DADAO-12 §3.6/§4.1）、`cg15 rc3` 复位全 1、`cfx_hmon`=3 / `cfx_power`=63（Kaiwu 手册 cfx63）均在 spec 可定位 ⇒ 非从其它平台抄值。
- **独立注入（非脚本内，我做 2 次）**：① `.equ P1` 1→2 ⇒ 单例四方 rc=**1**，`idl/qemu/gem5 槽 11 期望 0x…1 实际 0x…2`（有能力平台真实检查未放宽）；② DIV-18 槽 11 `…04→…05` ⇒ rc=**1**「声明值不符，条目值需更新」。均 `cp` 还原后 md5 回基线、复跑 rc=0。
- **约束逐条**：`git status -uall` 仅 5 类允许文件（4 产物 + 任务书）；`DIV-18` scope 仍 `[chipyard]`、`slots` 恰 8 个 0 基槽（3/9/10/11/16/17/22/27）；IDL/QEMU/gem5 检查未删未条件化（宏内未命中走 `\exp` 原判据、`cause_id` 64 位恰等 `0x4` 否则 `__EXIT`）；`.S` 头 GAP 与代码一致；`expected.tsv` 仍 28 槽、仅来源行号变。
- **披露项（点 19）判定**：Tiny 上点 17/18 的探测异常确会重写 hmon 入口帧，点 19 读到的是最近探测帧的 prev mode（恒 hypv=3）——值仍正确、仍读真硬件、帧被清仍会判红 ⇒ **语义仍成立，仅证明力弱化**；不阻断，建议 architect 在 GAP ② / DIV-18 impact 补一句（finding **F-R1**，文档级）。
- **发现 F-R2（文档级）**：`inputs.sha256` 另有 2 行（`cfx2rc_crrr_cfx.S`/`cfx2rd_crrr_cfx.S`）修的是**基线既有漂移**（主树 HEAD 现场 `check_inst_sig --data-only` rc=1、`inputs.sha256:248`），完成区「仅来源行号变」未覆盖，建议收尾改措辞；非本任务引入、非放宽。
- **判决：Accepted**（未改 `**状态**`）。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **32 PASS / 0 FAIL、RUN_RC=0**（含三路注入自检）；`make check-idl-full` **274/274**（8 条 `DIV DIV-18` 标注）、`make check-idl` **274/274**、`check-inst-asm`/`check-inst-macro-scope`/`check-tests-index`/`check-run-artifacts`/`check-no-residue`/`check-arch-self-test`/`check-knowledge-refs` rc=0。
**修改文件**：`tests/inst/11-cfx/escape_ciii_cfx.S`、`tests/arch/expected-divergences.yaml`（`DIV-18`）、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（重生成：槽数仍 28，值不变，仅来源行号变）、本任务书。未提交。
**验收结果**：
- **真触发**：hmon 入口先装；探测 1 写 `cg15 rc3=P0`、探测 2 读 `cg4 rc5`、点 11/12/17/18/23/28 的访问都在受控 handler 下真实执行——命中即记 `cg5 rc4`（cause_id）/`cg5 rc5`（cause_info）并按 `PB_RET` 返回，未命中按规范值原判据检查。
- **槽值（Tiny，spec 独立派生）**：点 11/17/23/28 `cfx2rd cfx_hmon,cg15,rc3,rd5` = `0x7A0CF0C5` ⇒ `0x7a0cf0c500000004`；点 12 `cfx2rd cfx_hmon,cg4,rc5,rd5` = `0x7A0C4145` ⇒ `0x7a0c414500000004`；点 18 `cfx2rd cfx_power,cg4,rc5,rd5` = `0x7AFC4145` ⇒ `0x7afc414500000004`；点 4/10 快照 = `cg15 rc3` 复位值全 1 ⇒ `0xffffffffffffffff`。编码按 `contracts/opcodes.yaml` 的 `opc[31:24]|cfxha[23:18]|cg[17:12]|rc[11:6]|rd[5:0]` 现场派生，`derive_check.py` 与 DIV-18 逐槽对账（含 `1<<2`）。
- **未放宽**：IDL/QEMU/gem5 槽流逐字节相同（md5 `25f3d355…`），Tiny 仅 8 个声明槽不同；点 1-3/5-9/13-22/24-27 仍按规范值真实检查；退出码四方全 0。
- **三路注入**：① DIV 槽 10 值 `…04→…05` ⇒ 静态派生 rc=1 + 四方「声明值不符」rc=1；② `__PACK_CAUSE` 移位 `32→33` ⇒ Tiny 声明值不符 rc=1；③ `P1` `1→2`（`expected.tsv` 不重生成）⇒ QEMU/gem5「期望 0x…1 实际 0x…2」rc=1。均 `cp`+md5 还原、复跑 rc=0（注入后 `git diff --name-only` 非空已断言）。
**新发现/坑**：① Tiny 上点 11/12/17/18 的探测异常重写 hmon 帧，点 19 读到相邻探测帧（prev mode 同为 hypv=3）⇒ 该槽在 Tiny 上不再独立证明「escape 不清入口记录」，有能力平台无探测异常、语义完整；② `cfx2rd` 读未实现行与写一样触发 `CFXREG`（同 `m17-chipyard-002`）；③ Tiny 的 `cg5 rc3/rc11` 快照 = `asyncMaskByMode`（`GewuFile.scala:1984` 在 `!asyncModel` 时返回 allOnes），与 `cg15 rc3` 复位全 1 一致 ⇒ 点 4/10 期望可独立派生。
**遗留问题**：无（点 19 的 Tiny 语义弱化已按 F1 披露；未改 RTL/契约/其它用例）。
