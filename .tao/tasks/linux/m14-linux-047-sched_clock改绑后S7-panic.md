# m14-linux-047: 工具链修复后 `k4_switch` S7 panic（`__mmdrop(&init_mm)`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-llvm-007`（已把同节 weak 调用改为发重定位，**共享安装根已重建为新工具链**）
**可并行分片**：否（linux 单写者）
**预估**：4–6 h
**档位**：大改（内核缺陷定位 + 修复）
**状态**：待开始

## 背景（事实，来自 `m14-llvm-007` 的实测）

- `m14-llvm-007` 修好后，内核里有 **8 个调用点**从「弱定义」改绑到强定义：`sched_clock` × 7（`kernel/sched/build_utility.o`）+ `release_thread` × 1（`kernel/exit.o`），全内核 `.text` 差 **23 B**；
- 隔离副本（同一内核源码/配置）对照：旧工具链 `k4_switch` **52/52**；新工具链 **50/51**；
- 失败点 `S7`：`Run /init.musl` 处 panic
  `kernel/fork.c:725 BUG_ON(mm == &init_mm)`（`__mmdrop` 收到 `&init_mm`）；
- 其余 K0–K3、K4 其它探针（fork 104/104、kthread 112/112、cow 86/86、stack 44/44）、K5（104/97/174）全绿；
- 判定：这是**被静默折叠长期掩盖的内核缺陷**，不是工具链回归。

## 目标

1. **定位根因**：为什么 `__mmdrop(&init_mm)` 会发生。两条线索先查：
   - `sched_clock` 强实现（`CONFIG_GENERIC_SCHED_CLOCK=y`）在 DADAO 上的行为——是否依赖尚未初始化的时钟，导致某条路径提前/延后；
   - `release_thread` 强定义（`arch/dadao` 或通用）是否对 `mm` 做了 `mmput`/引用计数操作。
2. **修复**：优先 arch 侧（`arch/dadao`）；确需动通用代码的，先报主会话转用户裁定（禁止自决）。
3. **回归**：新工具链下 K0–K5 全绿、`k4_switch` 恢复 **52/52**。

## 验收（逐条贴真实 rc）

1. **根因证据**：给出「改绑 → 哪条路径 → `__mmdrop(&init_mm)`」的链条（反汇编/调用点/引用计数变化），不是猜；
2. **修复验证**：`k4_switch` 52/52；K0 146 / K1 112 / K2 170 / K3 263 / K4 五探针 / K5 104/97/174 全 rc=0；
3. **可达 FAIL ≥2 路**（`cp`+md5）：① 撤回修复 ⇒ S7 复现 panic；② 用旧工具链对照 ⇒ 52/52（证明差异来自改绑）；
4. `check-patch-tree` linux 段 0 问题；`apply_series` 幂等；
5. 完成区写明：改了 arch 还是通用、为什么不能只在 arch 侧解决（若动通用）。

## 约束

独立 `git worktree`；不提交 git；**不得回退/重建共享工具链**（已是修复版，记录 `clang/llvm-mc/ld.lld` md5 并核对）；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
