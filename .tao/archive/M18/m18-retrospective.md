# M18 回顾（Linux 测试集 + K6）

> **达成**：2026-11-28 ｜ **册数**：73（见 `README.md` §1）｜ **关闭 issue**：21（见 `issues-closed.md`）

## 1 目标与范围

- **目标（用户 2026-11-20）**：**Linux 测试集（选择与修复）**；**K6 从 M14 移入**作为入口批次（`m14-linux-032/033/034` → `m18-linux-001/002/003`）。M14 收口判据相应收到 K5 + K3 退役，M14 不再声称「能当 Linux 用」。
- **测试集口径（用户 2026-11-22）**：**两套件都跑**——`kselftest` 先（与内核同源、粒度细、回归快）、`LTP` 子集后（系统调用/ABI 广度、对外可用性证据）；共用同一运行骨架；缺 `ldso` 就补、4 KiB 页假设的用例改成 64 KiB 页；客观无法完成的用例记录原因/证据/复评条件，**禁静默跳过**。
- **运行环境**：QEMU system `kaiwu-vast`（ADR-0052 D2）；chipyard RTL 无 MMU/TLB，节点 RTL Linux 不在本册。
- **分诊四分类**：`KERNEL_BUG` / `TEST_ADAPT` / `UNSUPPORTED` / `SUITE_ENV`；每条非 PASS 必须有在库记录。首轮目标不是通过率，而是「每个失败都有归类和证据」。

## 2 实际交付

- **入口批次 K6（`m18-linux-001`–`004` + `m18-infra-001/002`）**：busybox shell + semihosting 控制台；基础命令回归（sh 内 5 条 + mkdir/ls/rm）；K6 收口门控 `check-linux-k6`（71/71，`003`）；用户入口异步投递 + 控制台行缓冲（`004`）；musl `mallocng` 根因（`a_cas` 改 8 字节字 CAS，`infra-001`，`ISS-497/499`）与 `ldso` 动态链接闭环（`infra-002`）。终态 **K6 82/82**。
- **套件骨架（`m18-linux-005/006/018`）**：测试集运行骨架 + kselftest 试点（8 例）；LTP 子集接入 + 两轮逐例一致；套件环境补齐（TMPFS/MEMFD、iomem、非 root、PATH/passwd）；pthread create/join 闭环（`007`）。终态 kselftest 两轮一致、LTP 两轮 **14/14**。
- **内核修复主线（`m18-linux-014`–`031`）**：COW 共享文件页双重解锁（`014`）、`mlock2`/`MLOCK_ONFAULT` 复核（`015`）、`futex_waitv` 参数路由（`016`，`argmask` 449=0x09）、异常解码适配扁平位图（`023`）、内核异步新模型 R2（`022`）、内核迁 0.8.1-rc（`026`）、以及**异步返回路径关键修复链**（`025`→`028`→`029`→`030`→`031`，见 §3）。
- **平台/规范/测试同步（R3 异步 escape + 源接口）**：`spec-007/008/009`（异步 escape 语义、每源 pending/mask/ack、模式上限）+ `qemu-008/009/010` + `gem5-004/005` + `chipyard-002/003` + `idl-003/004` + `llvm-002` + `testcases-004/005`；`infra-004` issues 按里程碑分册。

## 3 关键修复链（异步返回路径）

> 一条因果链，每条修复暴露下一层的残余，最终收敛到 supv 出口意图的四字重写对称化。

1. **`025` 用户态异步投递负载自旋（`ISS-m18-001`）**：`trap.S` 先恢复 `rb1`（用户 SP）后恢复其余寄存器，而 `escape cfx_umon` 尚未执行 ⇒ 该窗口内异步入口按 supv 臂不换栈，handler 跑在用户栈，缺页/重入无限自旋。修法：两条 umon 返回路径在 `DADAO_GPR_RESTORE_AT` 前关 supv 异步门（`DADAO_CLOSE_SUPV_ASYNC`）。
2. **`028` 异步返回主因（`ISS-m18-009`）**：user 异步把捕获交接 `cfx_smon` 后不 escape，`inner_cfx_code` 停在 smon；恢复 umon 帧的 `escape cfx_umon` 即 `CFXESC`（§5.3 step 0）⇒ 静默自旋。修法：user 臂改写 hart 出口意图后 `escape cfx_hart` 到 supv finish，先恢复 `inner_cfx_code` 再跑 work loop。
3. **`029` 异步精确点残余（`ISS-m18-011`）**：根因不是 QEMU `cg15 rc2`，而是 `cfx_umon cg5` 单帧出口意图跨睡眠被覆盖——C 半睡眠期间 `dadao_enter_user()` 把 `rc8/rc9/rc11` 写成 supv 及其掩码 ⇒ 恢复的任务 `escape cfx_umon` 回 supv 执行用户代码。修法：`DADAO_UMON_USER_EXIT_INTENT` 在 skip/retry 两条路径重写四字出口意图。
4. **`030` `trap_busy` 跨睡眠误报（`ISS-m18-012`）**：hart 全局递归保护 `dadao_trap_busy` 跨 `schedule()` 误报 ⇒ 他任务 user 缺页交接即 `K2_FAIL_RECURSIVE`。修法：守卫改按任务（`thread_struct.trap_depth`）+ supv 帧按任务落内核栈；真重入仍按 `0x0e` 拒绝。
5. **`031` smon 对称（`ISS-m18-014`）**：与 `011` 同类对称缺口——`cfx_smon cg5` 的 supv 返回路径同样只重写 `rc10`。修法：`DADAO_TRAP_RESTORE_AND_ESCAPE` 在 `escape cfx_smon` 前重写四字（`rc8=supv`、`rc9=入口记录的 prev cfx`、`rc10=任务帧 ip(+4 on SKIP)`、`rc11=现场 cg15 rc3`）；`rc9` 硬编码会改变同步异常语义，须恢复入口记录值。

## 4 收尾状态（2026-11-28）

- **任务**：72 册 `已验证` + 本归档册 `里程碑`；M18 台账「待开始 / 进行中」为空。
- **issue**：`closed_in: M18` 共 **21** 条（`issues-m18.yaml` 20 + `issues-left.yaml` 的 `ISS-left-013`）；`issues-m18` open=0。
- **终局证据**：`check-linux-k6` 82/82；kselftest 两轮逐例一致；LTP 两轮 14/14；`check-syscall-abi` 86/86；`check-patch-tree` 12 patch set / 464 patches 0 problem。
- **基线红（非 M18 面）**：L1 `check-patch-tree` 52 problem（linux 51/musl 1，`ISS-left-004`）；L3 `unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类（`ISS-left-005`）。

## 5 关键裁定（最终口径）

| 主题 | 裁定 |
| --- | --- |
| 异步模型（ADR-0061 R2/R3） | mask 归 monitor、源索引统一 `cfxha`、`cg9` 七槽只读、一帧多源；escape 不异步返回；`cg9 rc6` 口径统一（复位 2、进入取 rc6，ADR-0064 D5/D9 迁 `cg15 rc14`） |
| 测试集判据 | 两套件都跑、共用骨架；失败分诊四分类、每条非 PASS 在库记录；不以通过率为首轮目标 |
| 内核出口意图 | 四字（`rc8` 模式 / `rc9` cfx / `rc10` 帧 ip / `rc11` 掩码）必须**全部重写**，不能只重写 `rc10`；`rc9` 取入口记录值、不硬编码 |

## 6 经验与坑（供后续里程碑复用）

1. **恒真断言必须上移为真判据**：`check_k6.py` C 组 11 条「rc 标记是脚本期望的…」在 `region()` 成功分支内恒真（`ISS-503` F1）；断言应并入 region 判据并注入证红，否则「验证」是空的。
2. **共享源树单写者**：非 linux 组件任务同样会写 `.work/build/linux/.config` 与内核镜像（`ISS-462`）；在途共享源树推进会让 `check-patch-tree` 假红（`ISS-463`）；构建期 ENOSPC、探针超时遗留 `gem5.opt` 写满盘（`ISS-464/465`）。单写者粒度要从组件细化到构建树。
3. **issue 原文不可信、必须复核现码**：`ISS-left-013`（原 `ISS-500`）在 M18 收口时被**误迁**到 `issues-left.yaml`——按 issue 原文「写 `~0`、无第二处写回」采信，未复核 `m18-linux-022` 已把 `dadao_enter_user()` 改为放开用户态源位。归档按 `closed_in: M18` 跨分册取集才纠正（见 `issues-closed.md`）。
4. **归档快照按 `closed_in` 跨分册取集**：本轮 `issues-m18.yaml` 20 条之外，`issues-left.yaml` 还有 `ISS-left-013`（`closed_in: M18`）⇒ 快照 21 条；只删 `issues-m18.yaml` 会漏。
5. **异步缺陷按因果链收敛、不要头痛医头**：`025`→`028`→`029`→`030`→`031` 每条修复暴露下一层残余；同类缺口（umon/smon 出口意图）要**对称**排查，未观测到签名不等于不存在。

## 7 遗留（不属 M18 收口阻断）

- **低频残余（`issues-left`，用户态异步/套件运行时）**：`ISS-left-020`（原 `ISS-m18-004`，极早停摆 1/2000）、`ISS-left-021`（原 `ISS-m18-005`，随机 case `HOST_TIMEOUT`）、`ISS-left-022`（原 `ISS-m18-006`，`handle_softirqs` `die=0xe4`/`pf-va=0x10`）、`ISS-left-009`（原 `ISS-m18-015`，`pf-va=0x0` 变体）——均登记频率区间、需抓 QEMU monitor 快照归因。
- **工具/环境缺口（`issues-left`）**：`ISS-left-006`（内核无 syscall 重启语义）、`ISS-left-008`（`check_patch_tree` 不验源树正确性）、`ISS-left-014`（`spec-005` 活文档残留）、`ISS-left-015`（`pthread_cond_wait-cancel` 回归红）、`ISS-left-023`（musl 静态产物未重建无门控）、`ISS-left-024`（`check-linux-k6` 不派生 initramfs source）、`ISS-left-027`（`mm-pfnmap` SUITE_ENV）、`ISS-left-028`（K6 无 `/proc`/mount）。
- **留给 M20 判断**：`ISS-left-007`（`fetch.py` 无 `--component`）与 `ISS-left-016`（`run_suite.py` 不取写者锁）——归属 infra 工具链，随 M20 issue 清仓批次处置。
- **跨册（m19 面）**：`ISS-left-025`（Tiny 新几何 BootROM 致 4 个 `DADAO-E2E` lit 超时）、`ISS-left-026`（`check-index-blobs` 红 4 条，chipyard 补丁 index 不符）。
