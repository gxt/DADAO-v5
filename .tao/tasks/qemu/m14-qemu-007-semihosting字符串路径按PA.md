# m14-qemu-007: semihosting 字符串路径统一按 PA（`SYS_WRITE0`/字符串类）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-qemu-002`（已验证：semihosting 指针按 PA）、`m14-qemu-004`（已验证：`SYS_READC`/`SYS_FLEN` 缓冲改 PA）
**可并行分片**：否（`components/qemu` 单树写者）
**预估**：1.5–2 h
**档位**：中改（单点语义 + 门控断言；复核 ≥2 路注入）
**状态**：待开始

## 背景（`ISS-450`，用户 2026-11-15 已裁定原则）

- **用户裁定**：「semihosting 参数指针 = **PA**」，已写进 `spec/Kaiwu §5.2` 与 `.tao/contracts/contract-semihosting.md §2`（要求**不经页表翻译**）；
- **QEMU 现状**：`SYS_WRITEC`/`SYS_EXIT` 走 `translate_for_debug`（identity，仅 `[0,2GiB)` ∪ ROM ∪ SRAM），但 **`SYS_WRITE0` 先 `target_strlen` 再 `probe_access_flags`**，**走页表** ⇒ 开 PTW 后两窗口不相交，`SYS_WRITE0` 无法按 PA 正确取串；
- 另：`translate_for_debug` 的注释仍写「DADAO has no MMU」，在 Vast + PTW 下已过时。


## 前提订正（主会话失误，2026-11-17）

本任务书的「背景」依据 `ISS-450` 的**旧描述**（`SYS_WRITE0` 走页表），但该问题**已被 `m14-qemu-002` 修掉**（`common_semi_strlen()` 钩子 + `dadao` 强定义按 PA 逐块读），`translate_for_debug` 的「no MMU」注释亦彼时订正。**立册前未核现状，属主会话失误。**

本任务实际交付（仍有价值，非重复实现）：

- **补 K14 的覆盖面缺口**：新增 640 B 长串（跨 3 个 256 B 块、起点在块内 48 B 处）的 `SYS_WRITE0` 断言 ⇒ 能把"只读首块"或"窗口上界截断"这类错误判红（3 路注入已证独立判别力）；
- **收掉最后一处过时注释**（`dadao_cpu_mmu_index()` 的 `M1: no MMU, single index`）；
- 判据：`check-linux-k1` 111→**112/112**、K14 由 3 条扩到 **7** 条。

## 目标

1. **字符串类取参统一按 PA**：`SYS_WRITE0`（及同类字符串获取路径）**不经页表翻译**；复用 `m14-qemu-004` 已建立的 PA 口径（`dadao_cpu_va_to_pa` / identity 窗口判定之一，**优先复用**，不另造第二套换算）；
2. **注释订正**：`translate_for_debug` 的「no MMU」表述改为与 Vast+PTW 一致的口径；
3. **门控**：新增一条「**Vast + `ptw_enable=1` 下 `SYS_WRITE0` 取串成功**」的断言（放进现有 K 门控或 semihosting smoke，按最小改动选）；
4. 其它 syscall 语义不动，越界须披露。

## 验收（真实 rc + 输出）

1. **先红后绿**：开 PTW 的 Vast 镜像里 `SYS_WRITE0` 断点 —— 改前取串失败/错串（贴输出），改后正确打印同长度、同内容；
2. `check-linux-k0` 119/119、`check-linux-k1` 111/111、`check-linux-k2` 104/104、`check-inst-asm` 904/904、`check-arch`（14 探针）、`check-qemu-forms`/`check-interface`/`check-component-changelog`；
3. **≥2 路自设计注入**（`cp`+md5 还原 + 重建）：① 把字符串路径改回走页表 ⇒ 红；② identity 窗口上界改小 ⇒ 长串截断/失败 ⇒ 红；
4. 补丁纪律：`check-patch-tree`（**qemu 段 0 problem**；其它段红属在途任务，逐条归因）、`make_patch` 幂等、`apply-series --component qemu` rc=0 且 HEAD 不变、`--source-state` qemu clean；
5. 完成区 ≤30 行、无运行期路径；写明**新安装根 md5**；`**状态**` → `待验收`。

## 硬约束

只动 `components/qemu/**` + 必要 `tools/linux/**` 或 `tools/qemu/**` 驱动 + 本任务书；**不动** `spec/`、`contracts/`、`tests/inst/**`、`components/{linux,gem5,chipyard}`；不提交 git；`cp`+md5 还原（禁 `git checkout/restore`）；构建用 `JOBS=32`，构建期间不跑长测试；**构建前 `df -h`**（今晚两次 ENOSPC）。

## 审阅记录

（待填）
