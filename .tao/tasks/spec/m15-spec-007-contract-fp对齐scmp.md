# m15-spec-007: `contract-fp.md` 与 spec 对齐（scmp 无序结果）

**模块**：spec
**项目里程碑**：M15
**依赖**：`a6f11e23`（spec 已改：signaling compare 无序结果 = canonical quiet NaN，版本号不变）
**可并行分片**：否（单文件）
**预估**：0.5–1 h
**档位**：小改
**状态**：待开始

## 背景

`m15-qemu-001` 执行时发现：`.tao/contracts/contract-fp.md` **第 26/88 行仍写「Signaling Compare 返回 sNaN」**，与 `a6f11e23` 之后的 `spec/SimRISC-07 §4` 冲突，且**没有任何门控覆盖这一条**。

## 要做

1. 改 `.tao/contracts/contract-fp.md` 第 26/88 行：signaling compare 的无序结果 → **canonical quiet NaN**（与 `spec/SimRISC-07 §4` 逐字一致），并补一句「quiet 与 signaling 的差别只在 `NV`」；
2. 若该文件有版本号/变更记录，按 `docs/Process-02` 处理——**但版本号升级须用户认可**：只加内容条目、版本号保持，等用户裁定；
3. 全文件搜 `sNaN`：凡「无序结果」语境的一律改；「sNaN 作输入置 NV」的语境**保留**。

## 验收

1. `grep -n "sNaN" .tao/contracts/contract-fp.md` 逐条给出处置（改/留 + 理由）；
2. `check-contract-relocs`、`check-spec-refs`、`check-knowledge-refs` rc=0；
3. 与 spec 的对应句**逐字比对**（给 diff）。

## 完成区

（待填）
