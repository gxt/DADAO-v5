# m16-chipyard-003: chipyard 侧 `cause_id` 子原因编码（ADR-0056 D6）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m14-spec-007`（已验证：`DADAO-12 §3.6` 正文 + `contract-see §6.1.1` 表）、`m16-gem5-009`（gem5 侧同项，可并行；两件须在**同一批探针**上互校）
**可并行分片**：否（改 `components/chipyard` 单一组件树 + 需重建 sim）
**预估**：6–8 h（含 Verilator 重建）
**档位**：大改（RTL 语义 + 三方一致 + 重建；复核 ≥4 路注入 + 探针全量）
**状态**：待开始

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

## 审阅记录

（待填）
