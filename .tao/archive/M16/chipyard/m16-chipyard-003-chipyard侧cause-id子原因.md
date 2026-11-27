# m16-chipyard-003: chipyard 侧 `cause_id` 子原因编码（ADR-0056 D6）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m14-spec-007`（已验证：`DADAO-12 §3.6` 正文 + `contract-see §6.1.1` 表）、`m16-gem5-009`（gem5 侧同项，可并行；两件须在**同一批探针**上互校）
**可并行分片**：否（改 `components/chipyard` 单一组件树 + 需重建 sim）
**预估**：6–8 h（含 Verilator 重建）
**档位**：大改（RTL 语义 + 三方一致 + 重建；复核 ≥4 路注入 + 探针全量）
**状态**：已验证

## 背景（ADR-0056 **D6 明文要求、一直没立任务**）

`ADR-0056 D6` 原文：「QEMU（填 `cause_id` 时置子原因位）、gem5（`node_cfx`）、**chipyard（`GewuFile`）** 三处同步」。实际只立了 QEMU 侧（`m14-qemu-005`）；chipyard 侧**无任务**。

现场核查（改动前必复核）：

- `components/chipyard/patches/generators/dadao-gewu/.../GewuFile.scala.patch`：异常进入接口 `cause`/`causeIp`/`info` 三个 64 位字段（`excp_cause_id` 为硬件写、只读）；
- `components/chipyard/patches/generators/dadao-wuming/.../WumingCore.scala.patch`：`excpCause` 由 `enterHmon(ip, (1.U << CFXMEM_BIT).pad(64), info)` 一类调用点给出，**当前只有 one-hot**；`CFXMEM_BIT` 等常量已集中定义；
- 全树搜 `NONPTW`/`ADWBFAIL`/subcause **零命中** ⇒ 未实现。

后果：chipyard 的 `excp_cause_id[63:32]` 恒 0，与 `DADAO-12 §3.6` 不符；因探针已改**低 16 位掩码**，这类偏差**当前没有门控能抓到**。

## 规格（**位号一律取权威表，不在本任务书复制**）

- 权威表：`spec/DADAO-12-SEE-主管系统运行环境.md` `§3.6`（`[15:0]` cause one-hot / `[31:16]` 保留 / `[39:32]` = `CFXPERM` 8 位权限类 / `[55:48]` = `CFXMEM` 8 位缺失类 / `[63:56]` = `ADWBFAIL`/`NONPTW` + 保留）；
- 人读版：`.tao/contracts/contract-see.md` `§6.1.1`；
- 决策与用法：`.tao/adr/adr-0056-cause-id-subcause-encoding.md` D1–D7（尤其 D2 wyde 分段、D4 `cause_info` 恒为地址、D5 退出码不变）。

## 目标

1. **判定点算子原因**：在 `WumingCore` 判定 fault 类的各路径（取指/访存缺失、HSJU 与 R/W/X 不符、cfx 来源掩码拒绝、A/D 回写失败、非页表 `CFXMEM`）产生子原因位；
2. **接口扩宽**：`GewuFile` 的 `cause` 字段承载「one-hot | 子原因（按 cause 选 wyde）」，或等价地在 `enterHmon` 调用点把子原因并入 `cause`；**不改 `cause_info` 的地址语义**（D4）；
3. **非 `CFXMEM`/`CFXPERM` 的 cause 两 wyde 必须全 0**；
4. **`Vast` 路由不在本任务范围**（chipyard 只有 `WumingTinyConfig`，无 Vast 实现 —— `discussing.md` 已记）；若将来补 Vast，路由另立任务；
5. **重建 sim 并核 md5**：verilator 产物 md5 记录在完成区（仅同时段可比，`ISS-451`/`ISS-453`）。

## 验收（真实 rc + 输出）

1. **与权威表逐位对齐**：`tests/arch/ptw` 探针在 chipyard 上跑通；**每类子原因至少一例**（`NONPTW`、缺失类 ≥3、权限类 ≥3、`ADWBFAIL`）；
2. **三方一致**：同一批镜像 chipyard / QEMU 的 `cause_id` **全宽相等**（不再掩码）；与 gem5（`m16-gem5-009`）互校；
3. **反向断言**：非 cfxmem/perm 的 cause 断言 `cause_id & 0xFFFFFFFF00000000 == 0`；
4. **≥4 路注入**（`cp`+md5 还原 + 重建）：① 清掉 `NONPTW` 位 ⇒ 红；② 子原因错放在另一个 wyde ⇒ 红；③ `ADWBFAIL` 时 `cause_info` 改为访存地址（违反 D4）⇒ 红；④ 让某非 cfxmem/perm cause 置一位 ⇒ 反向断言红；
5. **不回归**：既有 chipyard 门控（`check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、sim 重建后既有探针全绿、`tests/inst` 904/904）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/chipyard/**`（补丁树）+ 必要的 `tools/**` 驱动 + 本任务书；**不动** `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,gem5}`；
- 位号**只以权威表为准**；期望值从 spec/ADR 派生，不得从 QEMU 输出反填；
- 重建属于长任务：**启动前申报预计耗时**，构建与跑批不得并行（`ISS-462`）；
- 不提交 git；注入还原 `cp`+md5（禁 `git checkout/restore`）；基线钉死 commit（`ISS-458`）。

## 待裁定

**Q1：chipyard 是否要补 TLB/PTW（以及 cfx 来源掩码判权），才能让另外 17 位子原因可达？**

- **事实**：`WumingTinyConfig` 无 MMU/TLB/PTBR（`WumingParams` 无 PTW 字段、核无 `cfx_ptw` 访问 ⇒ `ptw_enable = 0` 恒成立），核内也不做 cfx 来源掩码判权（从不发 `CFXPERM`）⇒ `contract-see §6.1.1` 的 18 位里本 profile **只有 `[57] NONPTW` 可达**；8 类页表缺失、`[56] ADWBFAIL`、8 位权限类（含 `[39] NCFXPERM`）在此 profile **结构性不存在**（M14 已裁定「chipyard/gem5 不要求 TLB 建模」，见 `discussing.md` 2026-11-16）。
- **选项**：① **接受本 profile 只有 `NONPTW`**，页表类子原因等 chipyard 将来有 TLB 时另立任务（**推荐**：表/校验器/编码器已就位，届时判定点只需传对应位号）；② 本任务内给 chipyard 补 TLB（跨里程碑、远超 6–8 h 预估，须新任务书 + `spec/` 与组件双改）；③ 只补来源掩码判权让 `[39] NCFXPERM` 可达（中等，但 Tiny 现在根本没有被掩码拒绝的 cfx 访问路径，等于新造行为）。
- **自决的临时处置**：按 ① 交付 —— 18 位表 + `encode`/`wellFormed` + 写帧点具名校验 + 8 处可达判定点（全部 `NONPTW`）已落地；验收 1 的「每类子原因至少一例」对本 profile 收敛为「`NONPTW` 全宽取证 + 其余 17 位由表/逐位互校静态保证 + 非 cfxmem/perm 两 wyde 全 0 的可达断言」。

**Q2：`tests/arch/ptw` 的 13 条探针何时能在 chipyard 上跑？**

- **事实**：那批探针（`m14-testcases-005`，**待返工、未入仓**）要求 `cfx_ptw`/PTBR/PTE 回写失败等只有 TLB 实现才有的行为；chipyard 无 TLB ⇒ 本轮改用自建载体（8 类异常、三方逐字节）取证。
- **处置**：Q1 若走 ②，把 `causeid.S` 的 8 类按 ptw 形态扩到 13 条即可（载体已与 `tests/inst` 同源：固件 `+0xF8` 返回槽、`+0xE0/0xF0` 帧槽、`SYS_WRITEC` 字节流）。

## 完成区

**测试结果**：`arch-ptw` **在 chipyard 不可跑**（无 TLB/PTW，且 `tests/arch/ptw/**` 尚未入仓）⇒ 以新载体 `tools/chipyard/excp/causeid.S`（8 类异常各一例）取证：同一 ELF 在 chipyard / QEMU / gem5 上 **128 B 字节流逐字节相同**，`cause_id` **全宽**（数据/取指 `CFXMEM` ⇒ `0x0200000000000002`；`ILLI`/`UNDI`/`MALIGN`/`CFXREG`/`CFXTRAP`/`IALIGN` 两 wyde 全 0），`cause_info` 亦逐字节相同；`check_causeid.py` 现场从 `contract-see §6.1.1` 解析位号并与 `spec §3.6` 18 行**逐位互校**，**87 项 × 3 引擎全绿**；同一载体在**改前二进制**上 4 项红（正是两条 `CFXMEM` 缺 `NONPTW`）。子原因可达面 = **只 `NONPTW`**（见「待裁定 Q1」）。
**修改文件**：`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`、`components/chipyard/changelog.md`、`components/chipyard/README.md`、本任务书；新增 `tools/chipyard/excp/causeid.S`、`tools/chipyard/excp/causeid.lds`、`tools/chipyard/excp/check_causeid.py`；证据脚本落运行期证据目录（未入仓）。
**验收结果**：**①位号表**：`check_causeid --selfcheck` rc=0，合约 18 行（wyde2 8 + wyde3 10）与 `spec §3.6` 逐位一致、逐行打印「绝对位 ⇒ 大类 ⇒ wyde」（`[32]`–`[39]`、`[48]`–`[57]`），`GewuCauseId` 常量同名同位。**②三方一致**：`cmp` chipyard↔QEMU、chipyard↔gem5 均 `same`（引擎身份现场打印：sim `2fb79602…`、qemu `0acc25bf…`、gem5.opt `4aadf06c…`、llvm-mc `342a7d00…`、bootrom `514300876e…`）。**③反向断言**：6 条非 cfxmem 用例两 wyde `(0,0)`、`[31:16]==0` 全过；`tests/inst/11-cfx` 的 `cfx2rd` 检查点 7（`CFXTRAP` 帧 = `1`）**40/40 镜像三平台逐字节**。**④注入 5 路全红**（`cp`+md5 还原+重建）：清 `NONPTW` ⇒ 具名 `Assertion failed: GewuFile: malformed excp_cause_id`（sim rc=**255**）；子原因落 wyde2 ⇒ 具名红；子原因位号错（`DGPTRAP` 当 `NONPTW`）⇒ 判据 `0x10000000000002 ≠ 0x200000000000002` 红；`CFXMEM` 的 info 改指令字 ⇒ 判据「info 恒为地址」红（`0x20484000`）；非 cfxmem cause 带一位 ⇒ 具名红，**同路关掉校验器后访客侧反向断言仍红**（`ialign … (0,1)`）。**⑤门控**：`check-patch-tree` chipyard **23 patch / 0 assertion problem**（qemu/gem5/linux 段红属他人在途）、`make_patch` 幂等（二次 0 写入）、`check-source-state` chipyard OK、`check-inst-asm` **272/272**（`m15-testcases-007` 链化后口径；合入前为 904/904）、`11-cfx` 三平台 **40/40**、`01-load-store` 三平台 **235/235**（38 id / 197 故障例，`CFXMEM`·`MALIGN` 路径覆盖）；证据脚本 A–R–G 全段 **PASS=93 FAIL=0**。**重建**：`make verilog` + `make`（`JOBS=32`，约 5 min）交付二进制 md5 **`2fb79602f30916c363ecff17eb3c33c8`**；`make clean-sim` 后重建两次曾得同一 `e7234109…`（见坑②）。
**新发现/坑**：① **`stop()` 不能当失败**：chipyard harness 把它降为 `$finish`（`STOP_COND_`）⇒ **rc=0 静默结束**，且 `printf` 只在 `+verbose` 下发出 ⇒ 校验器改用 `chisel3.assert`（Verilator `$error`：无条件、致命、rc=255），`printf` 只留作打印违规值。② **sim md5 不稳定（`ISS-453` 成因收窄）**：同一源码、同一 RTL（连续两次 re-elaborate 的 gen-collateral 聚合 md5 完全相同）、同一组链接库（`libdramsim.a`/`libfesvr.a`/`libriscv.so` 未变）下，`make clean-sim` + `make` 仍可产出两个不同 md5 的二进制（`e7234109…` vs `2fb79602…`），**行为逐字节相同** ⇒ 差异在 Verilator C++ 编译/链接段；故本任务用**行为**作身份判据、md5 只作记录。③ **`aip.si` 立即数是 4 KiB 块**、标签差进不了立即数 ⇒ 返回槽与跳转目标必须在执行点用 `rb0` 算；手写偏移一律由 `.lds` 的 `ASSERT(resume == aip + N)` 回钉（本次被 +4/+8 咬到两次，都是 ASSERT 抓出）。④ 三方探针的 `CFXREG` 例必须挑**保留寄存器**（`cg5 rc1`）：`cg8 rc1` 在 QEMU/gem5 已实现，只有 chipyard 报 CFXREG。⑤ **既有**：`tools/chipyard/excp/app.S` 在**改前基线**就红（rc=69，按旧固件「`escape` 恒回 `trap+4`」写而固件自 `m12-chipyard-028` 起读 hmon `+0xF8`、`app.S` 从不写该槽）；`GewuFile` 把 `cg3 rc0–rc3` 并成一份 mask（`DADAO-12 §3.1` 是四个独立 mask，读回互污）——两处均与本任务无关，已记入组件 README 待各自任务修。⑥ 长脚本**运行期间禁改**（两次边跑边改导致日志尾部解析错乱，已重跑收口）。
**遗留问题**：① 「每类子原因至少一例」对本 profile 只能覆盖 `NONPTW`，其余 17 位结构性不可达（待裁定 Q1，自决按「等 TLB 任务」交付）；② `tests/arch/ptw` 探针已由 `m14-testcases-005` 合入（15 例 29 检查），但 chipyard 无 TLB ⇒ 该批仍不可在本 profile 跑，本轮以自建载体替代；③ `check_causeid.py` 的用例顺序与 `.S` 仍靠注释约定（已加「用例数现场统计」交叉核，顺序本身未机械化）；④ 并行会话的 `install-host` 期间 qemu 二进制在 `0acc25bf…`/`f8b6c575…` 间跳变，最终值取自当前安装根（证据脚本每次现场打印 md5）；⑤ `app.S` 与 `cg3` 四 mask 合并两处既有缺陷不在本任务范围。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 校验器初版用 `printf`+`stop()`：`stop()` 降为 `$finish` ⇒ 静默 rc=0，消息只在 `+verbose` ⇒ 不满足「具名失败」 | ✅已修 | `GewuFile` 改 `chisel3.assert`（`$error` 无条件致命），`printf` 保留打印违规值 | inj1/inj2/inj5：`sim rc=255` + `Assertion failed: GewuFile: malformed excp_cause_id` |
| `check_causeid.check_tables` 的「绝对位 vs wyde」是恒真式（`bit-(bit-base)==base`） | ✅已修 | 改区间判据 `base <= bit < base+16` | 把合约 `NONPTW` 的 `wyde3` 改成 `wyde2` ⇒ 4 项红（含该行） |
| 判据的 8 条用例与载体顺序硬耦合 | ✅部分收口 | 证据脚本增「`.S` 的 `cN_fault:` 计数 == 判据用例数」交叉核 | D 段 `probe case count == oracle CASES | 8` PASS |
| `expect_red` 用 printf 文本判红 ⇒ 校验器关掉时误报「named fatal」 | ✅已修 | 改判 `%Error: … Assertion failed`，printf 文本不再算红 | inj5c 重跑被判为 oracle 红（`ialign … (0,1)`），与 inj5 的 named fatal 区分开 |
| `enterHmonMem` 默认 `NONPTW` 把「本 profile 无 PTW」写成默认值，将来加 TLB 时漏改站点会静默保持 `NONPTW` | ⏸延后 | 不改默认（8 处重复字面量不增加检查能力；站点写错仍只能由探针发现） | scaladoc + 组件 README + 坑②已写明「TLB 任务必须逐判定点复核」 |
| 位号表逐位互校只在 `--selfcheck` 里跑，证据脚本未断言行数 | ✅已修 | C 段断言行数（18 = 0x12）并逐行打印；D 段断言用例数 | C 段 `table rows parsed from the contract (18 = 0x12)` PASS |
| 两次在 `run.sh` 运行中编辑该脚本 ⇒ 日志尾部解析错乱 | ✅处置 | 重跑受影响段（inj5、A–G+R） | `inject5b.log` / 最终全段日志 PASS=… FAIL=0 |
| `causeid.S` 的目标/返回槽依赖手算偏移（被 +4/+8 咬过两次） | ✅已修 | 目标改在执行点算（`sub.o rb4-rb0` + `add.si -8`），偏移全部由 `causeid.lds` 的 `ASSERT(resume==aip+N)`、`ASSERT(cN_jump==cN_fault+8)` 回钉 | 链接期 ASSERT 全过；改前两次错误偏移均由断言/判据抓出 |

### 第 1 轮 reviewer 验收（deepseek-v4-pro）

**判决：Accepted**（4 条文档级 finding 交 architect 收尾改，见末尾）。

- **位号/可达性独立复推**：`spec §3.6` 与 `contract §6.1.1` 18 位逐位一致（wyde2 8 + wyde3 10）；`GewuCauseId` 同名同位；`wellFormed` 覆盖 one-class/`[31:16]`/双位/另一 wyde/保留字节全分支。`enterHmonMem` 恰 8 处（全 CFXMEM→NONPTW）；`CFXPERM_BIT` 定义但**从不 raise**、`WumingParams.nL2TLBEntries=0` 且核无 PTW ⇒ **17 位结构性不可达属实（非漏实现）**，NONPTW 唯一可达。
- **校验器**：生成 RTL `GewuFile.sv:133` = `$error("Assertion failed: GewuFile: malformed excp_cause_id…")`（无条件致命）。**我 4 路独立注入**（`cp`+md5 还原+重建，全 rc=255 具名致命）：① wyde 双位（`wyde|DGPTRAP`）② 另一 wyde 非 0（CFXMEM 置 wyde2）③ 保留位 [63:58]（bit63）④ 非页 cause 带位（MALIGN 传 `MEM_DGPTRAP`+encode else 落 wyde3）。G 段 6 mutant 全红 + 控制绿（oracle 每条断言有可达 FAIL 路径）。
- **三方全宽**：`cmp` chipyard==QEMU==gem5 逐字节相同（128B；`CFXMEM=0x0200000000000002`，6 类两 wyde 0）；`check_causeid` 87 项 rc=0。改前二进制 4 项红：pre-change `excpCause:=causeOneHot` ⇒ cause_id=0x2，full-width+one-hot 两项 ×2 CFXMEM=4 红（G 段 `clear_nonptw` mutant 复现该红）。
- **门控**：`check-patch-tree` chipyard **23 patch/0 assertion**；`make_patch` 幂等（0 written）；`check-source-state` chipyard OK clean=True；`11-cfx` 三平台 **40/40**；`check-inst-asm` **272/272**（QEMU，当前 master）。
- **越界**：仅 `components/chipyard/**` + `tools/chipyard/**` + 本任务书；无 `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,gem5}`。
- **ISS-453 意见**：增量重建（`make verilog`+`make`）实测复现 md5 `2fb79602…`；clean-sim 重建行为逐字节相同（R 段 `rebuild-cid==cid-chipyard`）。**身份判据取行为、md5 仅记录**——合理；注意非确定在 clean 链接段、增量重建是确定的。
- **环境冲突记录**：复核期发现另一会话并发跑 `run.sh --inject`（PID 986373），与我的独立注入互扰（其 inj1-restore/inj2 因我失败、我首轮因 PCH 冲突失败）；已恢复现场、待其完成后重新独立注入 4 路全绿。**最终工作树已还原交付态**：源 md5 `08fe8dad…/eaee7e57…` + sim md5 `2fb79602…` + 流全绿（87/87）。

**finding（非阻断，收尾改）**：① `changelog.md` L133 与 `README.md` L204 仍写「`printf`+`stop()`」，实际是 `chisel3.assert`（`$error` 致命）——措辞过时；② `changelog.md` sim md5 `7bcf2e2f…` 与 README/完成区 `2fb79602…` 不一致；③ 完成区「904/904」与实测 272/272 计数口径不一；④ 完成区「`m14-testcases-005` 待返工」已过时（已合入 master，但 chipyard 无 TLB ⇒ ptw 探针仍不可跑，实质正确）。
