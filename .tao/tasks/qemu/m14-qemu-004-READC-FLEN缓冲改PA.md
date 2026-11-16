# m14-qemu-004: `SYS_READC`/`SYS_FLEN` 的取字缓冲改为 PA（`ISS-452`）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-qemu-002`（已验证：semihosting 指针按 PA）、`m14-qemu-003`（**已验证**，同组件已串行完毕）
**可并行分片**：否（qemu 组件单写者）
**预估**：1 h
**档位**：小改（两处缓冲地址 + 一条断言；复核 1 路注入 + 行为对账）
**状态**：待开始

## 背景（用户 2026-11-16 裁定「ISS-452：现在修，用 PA」）

`m14-qemu-002` 把 semihosting 的**指针**改成 PA 口径（`spec/Kaiwu §5.2`），但两条服务的**内部缓冲**仍用栈地址（VA）：

- `SYS_READC`：`common_semi_stack_bottom(cs) - 1`；
- `SYS_FLEN`：`common_semi_stack_bottom(cs) - 64`（同族）。

内核 SP 在 Vast 下是 **VA**；按 PA 口径应取该槽位的**物理地址**（`__pa` 化），或改用不落在内核栈的专用 PA 缓冲。K1 未用这两条服务，故当前无观测差异。

## 目标

1. 把 `SYS_READC`/`SYS_FLEN` 的内部缓冲地址改为 **PA**（推荐：复用 `m14-qemu-002` 的 PA 助手/`__pa` 换算；若取栈槽 PA 需要页表反查，则改用固定 PA 缓冲并注释理由）；
2. 补一条断言：**Vast + PTW 开**下 `SYS_READC`（或 `SYS_FLEN`）能正确取字/取长度（改前应红或行为异常）。

## 验收

1. **先红后绿**（若可复现）：改前跑新断言 ⇒ 红/异常；改后 ⇒ 绿；贴真实输出；
2. `make build-qemu` + `make install-host` rc=0（贴 md5，源树干净时取）；
3. `check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_*` 三个探针全绿、`check-qemu-forms` rc=0；
4. **1 路注入**：把改后的 PA 换算回退成 VA ⇒ 新断言红；
5. 补丁纪律同上（qemu 侧 0 problem、`make_patch` 幂等）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/qemu/**` + `tools/linux/**` + 本任务书；不改 `spec/`/`.tao/contracts/`/`tests/`；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

（待填）
