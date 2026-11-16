# m16-gem5-009: gem5 侧 `cause_id` 子原因编码（ADR-0056 D6）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-spec-007`（**已验证**：`DADAO-12 §3.6` 正文 + `contract-see §6.1.1` 表）、`m14-qemu-005`（**已验证**：QEMU 侧同项，作行为对照）
**可并行分片**：否（改 `components/gem5` 单一组件树）
**预估**：4–6 h
**档位**：大改（架构语义落到执行模型 + 三方一致性；复核 ≥4 路注入 + 探针全量）
**状态**：待开始

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

（待填）
