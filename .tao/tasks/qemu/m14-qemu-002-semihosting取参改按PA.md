# m14-qemu-002: semihosting 取参/取串改按 PA（`ISS-450`）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`spec/Machine-v5 §5.2`（2026-11-15 已定「指针一律为 PA、不经页表翻译」）、`contract-semihosting §2`（0.7.2，同口径）；`m14-qemu-001`（Vast 最小 smon，PTW 已开）；`m14-linux-003`（内核 semihosting 早控制台，按 PA 调用）
**可并行分片**：否（qemu 组件单写者）
**预估**：2–3 h（含 QEMU 重建 + 安装根刷新 + 4 路注入）
**档位**：大改（触及上游共享 semihosting 层 + 需重建 + 门控加严；复核 ≥4 路注入 + 独立重跑）
**状态**：待开始

## 背景（`ISS-450`）

用户 2026-11-15 裁定「semihosting 参数指针 = PA」，已写入 `spec/Machine-v5 §5.2` 与 `contract-semihosting §2`：「参数块指针与 `SYS_WRITEC`/`SYS_WRITE0` 的指针**都是物理地址**，**不经页表翻译**」。

但 QEMU 现状与之一致性不足：

- `SYS_WRITEC` / `SYS_EXIT` 取参走 `translate_for_debug`（identity，仅 `[0, 2 GiB)`∪ROM∪SRAM）；
- **`SYS_WRITE0` 先 `target_strlen`、再经 `semihost_sys_write_gf` → uaccess（`probe_access_flags`）走页表**；`SYS_WRITE`/`SYS_READ` 的缓冲区同样走 uaccess；
- 开 PTW 后 identity 窗口与页表窗口不相交 ⇒ **同一指针无法同时满足两条路径**；传 PA 时 `SYS_WRITE0` 取串失败（`EFAULT`）。
- `translate_for_debug` 注释仍写「DADAO has no MMU」（Vast + PTW 下已过时）。

M14 K1 自决「传 PA + 只用 `SYS_WRITEC`」绕过了该缺陷，但规范既定 PA，实现必须跟上（否则 K2/K3 后的控制台与文件类服务都会踩）。

## 目标

1. **取参/取串/读写缓冲一律按 PA**：dadao（system 模式）下 semihosting 对 guest 内存的访问**不得经页表翻译**；覆盖 `SYS_WRITEC`、`SYS_WRITE0`、`SYS_WRITE`、`SYS_READ`、`SYS_GET_CMDLINE`、`SYS_TMPNAM` 等所有带指针的服务。
2. **不改变其它 target 行为**：共享层（`semihosting/**`）的默认路径对其它架构逐字节不变；dadao 侧改动只经**本 target 的钩子/分支**生效。
3. **注释订正**：`translate_for_debug` 的「DADAO has no MMU」改为符合 Vast + PTW 现状的表述（说明 identity 窗口用途与 PTW 关系）。
4. **加门控（先红后绿）**：在 K1 门控里新增一条 **Vast + PTW 开启**下的 semihosting 断言：字符（`SYS_WRITEC`）与字符串（`SYS_WRITE0`）都能从**未映射 VA 对应的 PA** 正确取出并输出（取串成功即可证明不经页表）。

## 验收（逐条贴真实 rc 与输出）

1. **先红后绿**：在**未修复**的基线上，新断言 **FAIL**（贴真实红色输出：`SYS_WRITE0` 取串失败/输出为空）；修复后 **PASS**。
2. `make build-qemu` rc=0（必要时 `build-qemu-reconfig`），**`make install-host`** rc=0（组件改动后必须刷新安装根，否则门控读到旧二进制）；贴 `qemu-system-dadao` 改前/改后 md5。
3. 门控全绿：`check-linux-k0`、`check-linux-k1`、`check-qemu-forms`、`make linux-semihosting-smoke`、L1 `make check` 均 rc=0；**Tiny 路径行为不变**（贴 smoke 输出与退出码）。
4. **≥4 路可达 FAIL 注入**（`cp` 备份 + md5 还原 + 重建）：① 把 PA 助手改成走页表（回到 bug 状态）⇒ 新断言红；② 只修 `SYS_WRITE0` 不修 `SYS_WRITEC`（或反之）⇒ 另一条断言红；③ 让 PA 助手用错宽度（如按 4 字节读串）⇒ 输出字节不符 ⇒ 红；④ 让 `SYS_WRITE0` 返回长度错（+1）⇒ 输出多一字节 ⇒ 红。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/qemu/**`（补丁 + `series`）与 qemu 组件源树（运行期检出）、`tools/linux/`（门控断言）；
- **不改** `spec/`、`contracts/`（口径已定，本次是实现对齐）；不改 `tests/`（除门控所需的既有探针复用）；
- 一文件一补丁（`docs/Process-01`）；`make apply-series` / `check-source-state` / `check-patch-tree` 必须 rc=0；
- **共享层最小化**：若必须改 `semihosting/**`，改动只允许是"加 target 钩子"，不得改共享层对其它 target 的语义；在完成区说明为何无法只在 `target/dadao/` 内完成；
- 构建与跑批不得同时；`JOBS=32`；不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore`）。

## 审阅记录

（待填）
