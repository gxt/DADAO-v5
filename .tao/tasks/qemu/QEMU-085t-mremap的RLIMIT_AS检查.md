# QEMU-085t: `mremap` 增长的 guest `RLIMIT_AS` 检查（ISS-351）

**模块**：qemu
**项目里程碑**：M11
**依赖**：`QEMU-084t`（guest rlimit 已实现，已合入）
**状态**：待开始

## 用户授权（原话）

> 「3、补」

即：补 QEMU 侧 `mremap` 的 `RLIMIT_AS` 检查（`ISS-351`）。

## 背景与事实

- `QEMU-084t` 给 `target_mmap()` 加了 guest `RLIMIT_AS` / `RLIMIT_DATA` / `RLIMIT_STACK` 检查（对应内核 `may_expand_vm()` 口径），但 **`target_mremap()` 未检查**。
- `GEM5-030t` 实测：`mremap` 从 4 MiB 增长到 100 MiB 时，QEMU **成功**、gem5 按 Linux `may_expand_vm` 拒绝（`ENOMEM`）；该差异已写进 gem5 `README`「与 QEMU user 已知差异」第 4 条，并登记 `ISS-351`。
- 结论：gem5 侧是对的（Linux `mm/mremap.c` 两处都调 `may_expand_vm`），缺的是 QEMU 侧对齐。

## 目标

1. `components/qemu/patches/linux-user/mmap.c.patch`：`target_mremap()` 在**增长**（`new_size > old_size`，含 `MREMAP_MAYMOVE` 与固定地址两种路径）时，按 guest `RLIMIT_AS` 检查增长后的 VA 总量；超限返回 `-TARGET_ENOMEM`。口径与 `QEMU-084t` 的 `target_mmap` 一致（复用同一 `guest_rlimit_*` 基础设施，不另立状态）。
2. **不改变**不增长的 mremap、`MREMAP_DONTUNMAP` 等既有语义；不引入 RLIMIT_DATA 的新语义（除非内核确有对应，需在任务书说明）。
3. 双引擎探针：同一 ELF 在 QEMU 与 gem5 SE 上，对 `mremap` 增长对比 `ENOMEM` / 成功；`RLIMIT_AS` 设为低值时两侧一致；限值内增长两侧均成功。
4. 更新 gem5 `README`「与 QEMU 已知差异」第 4 条：改为「已对齐（QEMU-085t）」或删除该条（保留历史说明），并同步 `changelog`。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/linux-user/mmap.c.patch`（及必要的 `user-mmap.h` 注释）、`components/qemu/{README.md,changelog.md}`、gem5 `README.md` 的差异条目、任务书、`milestones.md`、`issues.yaml`（关闭 `ISS-351`）。

**不在范围**：其它 syscall、`target_mmap` 既有逻辑、gem5 实现（已正确）、测试期望值。

## 验收标准

1. 探针（双引擎）三组场景逐行一致：
   - `RLIMIT_AS` 充足 + `mremap` 增长 ⇒ 两侧成功；
   - `RLIMIT_AS` 不足 + 增长 ⇒ 两侧 `ENOMEM`；
   - 不增长的 `mremap`（收缩/原地）⇒ 两侧成功且数据完好。
2. 反例：把新增检查去掉 ⇒ 第二组探针 FAIL；`cp`+md5 还原重建回绿。
3. `build-qemu`、`install-host`（安装根与构建树 md5 一致）、`check-arch`、`check-inst`、`check-patch-tree`、`check-source-state`、L1、L2 真实 rc=0。
4. gem5 `README` 差异条目已更新，`changelog` 同笔。
5. `ISS-351` 关闭（`resolved_by: QEMU-085t`）。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- QEMU 侧改动属**跨模块**，已获用户授权（原话见上）；只动 `linux-user/mmap.c` 及文档。
- 重建 QEMU 后必须 `make install-host`（安装根只由它写入），否则门控/探针会读旧二进制。
