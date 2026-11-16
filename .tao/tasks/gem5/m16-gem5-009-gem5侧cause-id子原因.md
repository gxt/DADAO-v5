# m16-gem5-009: gem5 侧 `cause_id` 子原因编码（ADR-0056 D6）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-spec-007`（**已验证**：`DADAO-12 §3.6` 正文 + `contract-see §6.1.1` 表）、`m14-qemu-005`（**已验证**：QEMU 侧同项，作行为对照）
**可并行分片**：否（改 `components/gem5` 单一组件树）
**预估**：4–6 h
**档位**：大改（架构语义落到执行模型 + 三方一致性；复核 ≥4 路注入 + 探针全量）
**状态**：待验收

## 背景（这是 ADR-0056 **D6 明文要求、一直没立任务**的一项）

`ADR-0056 §Decision D6` 原文：「QEMU（填 `cause_id` 时置子原因位）、**gem5（`node_cfx`）**、**chipyard（`GewuFile`）** 三处同步」。实际只立了 QEMU 侧（`m14-qemu-005`），gem5 侧**无任务**；现场核查 `components/gem5/` 里搜 `NONPTW`/`ADWBFAIL`/subcause **零命中** ⇒ 未实现。

后果：gem5 的 `excp_cause_id[63:32]` 恒 0，与 `DADAO-12 §3.6` 不符；因为 `tests/arch` 与 `tests/inst` 的断言已改成**低 16 位掩码**，这类偏差**当前没有门控能抓到**。

## 规格（**位号一律取权威表，不在本任务书复制**）

- 权威表：`spec/DADAO-12-SEE-主管系统运行环境.md` `§3.6`（`[15:0]` cause one-hot / `[31:16]` 留给未来 cause / `[39:32]` = `CFXPERM` 的 8 位权限类 / `[55:48]` = `CFXMEM` 的 8 位缺失类 / `[63:56]` = `ADWBFAIL`/`NONPTW` + 保留）；
- 人读版：`.tao/contracts/contract-see.md` `§6.1.1`（18 行子原因表，含 wyde 列）；
- 决策与用法：`.tao/adr/adr-0056-cause-id-subcause-encoding.md` D1–D7（**必读**；尤其 D2「一个 cause 独占一个 wyde」、D4「`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址」）。

## 目标

1. **raise 点算子原因**：在 `components/gem5/patches/src/arch/dadao/` 的异常投递链上产生子原因 —— 入口是 `tiny_cfx.cc` / `node_cfx.cc` 的 `tinyCfxRaise`/`nodeCfxRaise`（现签名以 `cause` 一个 one-hot 传入）；TLB/权限/A/D 回写/非页表 `CFXMEM` 的判定点在 `node_tlb.cc`、`inst.cc`、`fs_machine.cc` 等 raise 调用处；
2. **写入 `causeId`**：`s.cfx[ci].causeId = cause | (subcause << 32 或 << 48)`，按 cause 选 wyde（`CFXPERM` ⇒ wyde2，`CFXMEM` ⇒ wyde3）；其它 cause 下两个 wyde **必须全 0**；
3. **`cause_info` 不得改语义**（D4）：`CFXMEM` 恒为地址（`ADWBFAIL` 时为 PTE 物理地址、`NONPTW` 时为核内被访地址）；`CFXPERM` 恒为地址（`cfxtrap`/`cfx2r*` 拒绝时为触发指令地址）；
4. **退出码不受影响**（D5）：`Kaiwu §7.1` 的 monitor 段仍取低位 cause 索引；
5. **回归**：`check-gem5-decode`、时序相关门控不受影响（本任务不动周期表）。

## 验收（真实 rc + 输出）

1. **与权威表逐位对齐**：用 `tests/arch/ptw` 的现成探针（`m14-testcases-005` 已交付 13 条）与 `tools/testcases/arch/**` 的期望，在 gem5 上跑通；**每类子原因至少一例**（`NONPTW`、8 类缺失里至少 3 类、权限类至少 3 类、`ADWBFAIL`）；
2. **三方一致**：同一批镜像 gem5 / QEMU 的 `cause_id` **全宽相等**（不再掩码），差异 ⇒ 红；
3. **反向断言**：对**非** `CFXMEM`/`CFXPERM` 的 cause，断言两个 wyde **全 0**（`cause_id & 0xFFFFFFFF00000000 == 0`）；
4. **≥4 路注入**（`cp`+md5 还原）：① 把 `NONPTW` 位清掉 ⇒ 对应探针红；② 把 `CFXPERM` 的子原因错放到 wyde3 ⇒ 红；③ `ADWBFAIL` 时把 `cause_info` 改成访存地址（违反 D4）⇒ 红；④ 让某非 cfxmem/perm cause 也置一位子原因 ⇒ 反向断言红；
5. 门控：`check-gem5-decode`、`check-wuming-cycles`（不改应仍绿）、组件补丁树门控（`check-patch-tree` gem5 段 0 problem）、`make_patch` 幂等；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/gem5/**`（补丁树）+ 必要的 `tools/gem5/**` 驱动 + 本任务书；**不动** `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,chipyard}`；
- 位号**只以权威表为准**，不得自行解释或"就近取位"；
- 三方一致性的**期望值从 spec/ADR 派生**，不得从 QEMU 输出反填；
- 不提交 git；注入还原 `cp`+md5（禁 `git checkout/restore`）；基线钉死 commit（`ISS-458`）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 **Fault 重定向的 `npc` 使向量首条指令执行两次**（数据类故障 8 例红在「handler 跑了 1 次」计数；`SYNCN=1` 却 handler 跑 2 次 ⇒ 不是投递两次，而是 `setPc` 置 `npc==pc`、`BaseSimpleCPU::advancePC()` 调 `invoke()` 后不再 advance ⇒ 下条指令 `advance()` 又落回 `pc`） | ✅已修 | `nodeCfxRaise`/`tinyCfxRaise` 增 `fromFault` 形参（默认 false）；`nodeSyncEnter` 与 `MachineFault::invoke` 传 true ⇒ fault 路径 `npc = vector + 4`；in-execute 路径（trap/escape/cfx 故障/异步投递）不变 | 26/26（改前 15/26）；14 个既有 arch 探针在 gem5 上无新增红 |
| F2 证据脚本把 `$SHIM`/`$QEMU` 当相对路径，在 carrier 目录里跑 ⇒ A1/A2 得 `0 0` | ✅已修 | 在 `cd $ROOT` 之后把两个二进制改成绝对路径 | A1/A2 = 26/26 |
| F3 B 组（全宽对照）对**无故障**用例也要求「子原因集合非空」⇒ 8 例恒红 | ✅已修 | `dump_ids.py --compare` 默认只要求相等，新增 `--require-nonempty`；脚本只对 5 个故障用例（007/009/010/011/013）加该开关 | B 13/13 |
| F4 注入②的具名失败消息抓不到：驱动 `P.run` 丢弃引擎 stderr，且整例跑完后 `rom.bin` 已被最后一个 check 覆盖 | ✅已修 | 每路注入用 `--only <case>/<label>` 精确到检查点；`simerr` 不可得时用**同一镜像**经 shim 复跑一次取 stderr | ②报 `malformed excp_cause_id 0x20000000000080` |
| F5 注入④（CFXREG 带子原因）会命中 2 个检查点，脚本期望「恰好 1 次」⇒ 假红 | ✅已修 | 消息计数判据由 `==1` 改 `>=1` | ④ 8/8 检查通过 |
| F6 `code_table.py` 的非页 cause 正则 `TinyCause\w+` 把 `TinyCauseCfxPerm` 误判为违规 | ✅已修 | 改为逐名列出非页 cause（`TinyCauseIlli/…/Ialign`） | code table 34/34 |
| F7 门控段抽 gem5 problem 的 `awk '^gem5'` 与真实输出格式（`check-patch-tree: gem5: …`）不符 ⇒ E3 假红 | ✅已修 | 按 `<component>: … problem` 计数；gem5 段要求「problem 行数 0 且补丁数 > 0」 | E3 gem5 0 problem / 107 patch |
| F8 `check-wuming-cycles` 红（`tools/gem5/wuming_cycles.yaml` 与文档解析不一致） | ❌不修（外因） | 本任务未动周期表与生成器；在未改动的 master（`91a09727`）上同样 rc=1 | 主树 `gen_wuming_cycles.py --check` rc=1；gem5 侧两个 artifact 检查仍 PASS |

无未修 finding（F8 为外因，已留证）。

### 第 1 轮 reviewer 验收（大改：diff + 独立复推 + ≥4 路注入）

- **位号**：`fs_machine.hh` CauseSub 18 位逐位对 `contract-see §6.1.1`（wyde2 [32..39]/wyde3 [48..57]），`code_table.py` 独立跑 34/34 hold；helper（`missingPageSub`/`missingFragSub`/`hsjuSub`）映射正确，另一 wyde 与 `[31:16]` 由 `checkCauseId` 的 `CauseReserved16`/`sub&~own` 强制 0。
- **重跑**：`check-gem5-decode` rc=0；`check-patch-tree` gem5 段 **0 problem / 107 patch**（仓库 11 problem 全为 qemu/chipyard/linux 并发任务，非本任务）；`check-source-state` gem5 `clean=True HEAD=96db994ebc05`；`make_patch` 两次 rc=0、补丁集 md5 `f36bf630…` 幂等。arch-ptw 13 例 **gem5 26/26、QEMU 26/26**（我独立复跑，非读日志）。`make check-arch` 依赖 `install-host`（按约束禁跑），以工程师 log（14 探针+smoke PASS）+ 我独立跑 049t/integ049t 对 QEMU PASS 替代。
- **注入**：工程师 4 路日志逐条核对（每路 inject⇒具名红⇒cp+md5 还原⇒重建⇒回绿）；我另 **2 路自设计**：⑤ hsjuSub 返回两位 ⇒ `fatal …0x900000080`（one-hot）；⑥ `SubNonPtw | (1<<20)` ⇒ `fatal …0x200000000100002`（reserved[31:16]），均 cp+md5 还原（`d86c741e…` 对账）+ 重建后 nhperm/nonptw 回绿。
- **F1 独立结论**：`BaseSimpleCPU::advancePC(fault)` 调 `invoke()` 后不再 advance（base.cc:533-536），DADAO `PCState::advance()`=`pc=npc;npc+=4`（pcstate.hh:392），旧 `npc==pc` 使向量首条指令执行两次；改 `fromFault` 后 fault 路径 `npc=vec+4`、in-execute（trap/escape/cfx 故障/异步）`npc=vec` 不变。行为证据：probe `a_fault_count(c,1)` 26/26 过。**无新偏差，不拆任务**（F1 是子原因计数正确的必要前提）。
- **越界**：diff 仅 `components/gem5/**` + 本任务书；无 spec/contracts/tests/components{qemu,linux,chipyard}。
- **判决：Accepted**。小注（不阻断）：gem5 增量重建链接非逐位可复现（我重建后 md5 变，源码 md5 一致），系 gem5 既有特性（m16-gem5-010 已记录）。

## 完成区

**测试结果**：`arch-ptw` 13 例 26 检查 —— gem5 **26/26**、QEMU **26/26**；全宽对照 13/13（两引擎 rd10 里被观测到的 `excp_cause_id` 集合逐例相同：007=`0x0100000000000002`、009/013=`0x0200000000000002`、010=`0x0001000000000002`、011=`0x0000000800000080`，成功类用例两侧同为「无子原因位」）；位号表 34/34 行与 `contract-see §6.1.1` 逐位一致；反向断言 13 例 × 2 引擎 0 例外 + CFXREG 4 检查绿。4 路注入全过（`cp`+md5 还原，每路「注入⇒红⇒还原⇒重建⇒回绿」）：① 去掉 `NONPTW` ⇒ `ptw_off_bypasses_tlb` 红（校验器 `malformed excp_cause_id 0x2`）；② `NWPERM` 改投 wyde3 ⇒ `nwperm` 红（`malformed excp_cause_id 0x20000000000080`）；③ `ADWBFAIL` 的 `cause_info` 改填访存地址 ⇒ `flush_adwbfail` 红在 `cause_info == 0xfffffffffff8`；④ 非页 cause 带一位子原因（同路关校验器以证断言可达 FAIL）⇒ `range_size0_cfxreg` 红在 `wyde3 == 0`。
**修改文件**：`components/gem5/patches/src/arch/dadao/{fs_machine.hh,fs_machine.cc,fs_tlb.cc,node_cfx.hh,node_cfx.cc,node_tlb.cc,tiny_cfx.hh,tiny_cfx.cc}.patch`（8 份改，107 份补丁总数不变）、`components/gem5/changelog.md`、本任务书；gem5 源码树单 commit（`dadao: gem5 patch series`，amend 至 base+1）。
**验收结果**：`build-gem5` rc=0 → `gem5.opt` md5 **`4aadf06c70e0c3efe14e29576f577579`**（重复构建 md5 不变）；`check-gem5-decode` rc=0；`make check-arch` **PASS**（14 探针 + smoke）；`check-patch-tree` gem5 段 **0 problem**（107 patch；仓库 4 problem 全为 `linux:`，在途任务改脏）；`--source-state` gem5 `clean=True count=1`；`make_patch` 两次 rc=0 且补丁集 md5 不变。gem5 上的既有探针回归：044t/045t/049t/integ044t/integ048t/integ049t `RESULT: PASS`、integ039t 37/37、integ040t 34/34、integ047t 5/5、integ050t 16/16、integ051t 14/14，integ046t 15/16 与 integ007t 1/64 为改前既有（与 `m16-gem5-010` 记录一致）。
**新发现/坑**：① 子原因只有两个写帧点（`nodeCfxEnter`/`tinyEnter`），把「大类↔wyde 配对 + 恰一位 + 另一 wyde 与 `[31:16]` 全 0」做成 `checkCauseId()`（`fatal()` 具名失败）后，任何漏填/错位当场暴露——注入①/②就是被它抓住的；② gem5 的 `Fault::invoke` 由 `BaseSimpleCPU::advancePC()` 调用且**之后不再 advance**，所以 fault 重定向必须自带「顺序下一拍」，否则向量首条指令执行两次（`escape` 之后的子原因计数被多计）；in-execute 的 trap/escape 仍须 `npc==target`，两种语义必须分开；③ `checkCauseId` 让「漏填子原因」进不了帧，因此证明**访客侧反向断言可达 FAIL** 必须同路关掉校验器（注入④）。
**遗留问题**：① `arch-ptw` 13 条探针仍属在途的 `m14-testcases-005`（未入仓），本任务用其载体副本取证，收编后证据脚本把 `--qemu` 换成仓内驱动即可；② `check-wuming-cycles` 的外因红（`tools/gem5/wuming_cycles.yaml` 漂移，master 同红），需由周期表那边重跑生成器；③ `integ046t` 15/16、`integ007t` 1/64 为改前既有；④ `integ042t` 未在 gem5 上跑（其驱动默认逐 TB dump，实测单次约 7.8 GB，按 `ISS-465` 停跑并清理）。
