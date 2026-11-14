# m13-gem5-013: `ld.t rf0` 的只读位（gem5 侧）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-qemu-007`（已合入，QEMU 侧口径已定）；与 `m16-gem5-*` 串行（组件单写者）
**可并行分片**：否
**预估**：2–3 h
**状态**：待开始

## 背景（实测）

`m13-qemu-007` 的三平台探针显示：**gem5 的 tetra 装入路径覆盖 `rf0[31:22]`（只读位）**——
`ld.t rf0 ← 0xFFFF_FFFF` 得 `0x7FF8_0000_FFFF_FFFF`（chipyard/QEMU 为 `0x7FF8_0003_7FC0_001F`）；
octa 路径（`ld.o rf0`）在 gem5 上正确 ⇒ 缺口只在 tetra。

## 范围补充（用户 2026-11-14 裁定后）

- **`ld.t`/`ldm.t` 只写低 32 位、高 32 位保持原值**（gem5 的 `writeFloatLow32` 已是此行为，**不要改成符号扩展**）；`rf0` 仍须经 FCSR 写掩码（只放行 `[33:32]`+`[4:0]`），低 32 位里只有 `[4:0]` 真正生效。
- **凡产生 ft 结果的指令只写低 32 位**：请现场核查 gem5 的 ft 算术/取余/开方/取整/缩放/最小最大/转换到 ft 路径是否都只写低 32 位（若是，给证据；若否，按裁定改并列出）。
- 复制类（`ft2ft`/`fo2fo`/`rd2rf`/`rf2rd`）按 64 位二进制搬移，不得改。
- 探针须覆盖：`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0000_7FC0_001F`；`ld.t rf5` 后 `rf2rd` 高半保持；`ftadd` 后高半保持；`ft2ft` 64 位不变。

## 范围

- `src/arch/dadao/**` 里 `ld.t`/`ldm.t` 目的为 `rf0` 的写入路径：改为经 FCSR 写掩码（只放行 `[33:32]` 与 `[4:0]`，`[63:51]`/`[31:22]` 保持、SBZ `[21:5]` 忽略），与 QEMU 的 `RF0_WRITE_MASK` 同口径。
- 不改其它 FP 写路径；不改 spec/契约。

## 验收

1. tetra 探针 9 点与 chipyard/QEMU **逐字节一致**（`ld.t rf0 ← 0xFFFF_FFFF` ⇒ `0x7FF8_0003_7FC0_001F`）；octa 3 点不变。
2. `check_b7`/`check-gem5-decode`/`check-component-changelog` rc=0；`check-patch-tree` gem5 段 0 问题。
3. ≥2 路注入可达 FAIL + `cp`+md5 还原。
4. 安装根 == 构建树（gem5 为源码构建，无 install 根则豁免，写清）。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；组件补丁 `make_patch.py gem5` 导出。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash`；用 `cp`+md5。

## 待裁定

（实现中写。）

## 审阅记录

（待填）
