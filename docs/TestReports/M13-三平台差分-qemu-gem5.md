<!-- 人读结论；数据来源见 §2，快照见同目录 -->
# M13 三平台差分：qemu 与 gem5（Tiny profile，2026-11-10）

- **生成时间**：2026-11-10（本地 `Asia/Shanghai`）
- **覆盖范围**：`Machine-v5-Tiny`（`hypv` 恒态）；**chipyard 列暂缺**（`m12-chipyard-007` 未开始，非 `N/A` 的伪值）
- **数据来源**：`m13-qemu-001`（QEMU Tiny hmon）、`m13-gem5-001`（gem5 Tiny hmon）、`m13-gem5-002`（Tiny 恒 `hypv` + `cg3` 限制）、`m13-testcases-001`/`002` 全量长尾（`refs/m13-001-static-3600s-full.*`、`refs/m13-002-dynamic-3600s-full.*`）
- **机器指纹**：节点 Intel Xeon E7-4820 @2.00 GHz（nproc 64）跑长尾；主控机 AMD EPYC 7773X 跑组件构建。`gem5.opt` md5 `53466b82…`（25.1.0.1）、`qemu-dadao` md5 `3c4660d2…`（11.1.1）、musl HEAD `61bd50e5…`

## 1. 结论

1. **Tiny hmon（`cfx_power` → `cfx3`）语义：qemu 与 gem5 逐条一致。**
   同一 ELF 两边 guest exit 均 `0x21`，结果表 **md5 完全相同**（`45120581…`）；`cause_id`（one-hot）、`cause_ip`、`cause_info`（指令编码 / 访存地址 / 非法 IP）、`escape` 的 0 与 +4 两路、`cg7` 四字段、`cg8 rc1` 行为全部相同。
2. **Tiny 恒 `hypv`：已对齐。** 曾经 gem5 直接取 `switch_run_mode`，guest 写 ≠3 后异常即离开 `hypv`（`ISS-363`）；现已硬置 `HYPV`，并补 `cg3` 仅 `hypv` 可访问（非 `hypv` ⇒ `CFXREG`）。
3. **长尾计时：static 不可测、dynamic 部分可测。**
   - static（72 例，3600 s 预算）：gem5 **72/72 超时**，qemu 72/72 通过（中位 44 s、最大 1103 s）。单例诊断（90 s 后 SIGINT dump）显示 `simInsts=40,847,163` 且无 guest exit ⇒ **挂死**，非「慢」（`ISS-361`）。
   - dynamic（93 例，3600 s）：gem5 **78 blocked / 14 pass / 1 fail**，qemu 93/93 通过；可比比值 **n=12**，min 172×、median 289×、p90 688×、max 1942×（enc-md5）。
4. **一处真实差异**：dynamic `FreeBench/neural` 输出长度相同（358 B）但内容不同，qemu 与 reference 一致 ⇒ gem5 侧差异（`ISS-362`），疑浮点舍入/格式化，已定为浮点差分首个定位样本。

## 2. 差异清单

| 编号 | 现象 | 归因 | 状态 |
| --- | --- | --- | --- |
| `ISS-361` | static 72 例 3600 s 全超时，最小例（qemu 0.0 s）同样吃满 | gem5 SE 挂死（非慢） | open（待定诊断方案） |
| `ISS-362` | `neural` 输出 358 B 同长但内容不同 | 疑 gem5 浮点/格式化 | open（交浮点差分） |
| `ISS-363` | guest 写 `switch_run_mode` 后可离开 `hypv` | gem5 未强制 `HYPV` + 未限制 `cg3` | **已修**（`m13-gem5-002`） |
| `ISS-364` | `check-arch` 的 `start_busy_returns_busy` 约 5% 失败 | 探针 BUSY 窗口跨 trap，既有 flaky | open（建议有界重试） |

## 3. 未覆盖

- **chipyard 列**：等 `m12-chipyard-007`（Tiny `cfx3`/`cfx63`）。同一 hmon ELF 与期望表已备，可直接复用。
- **浮点语义**：`m13-integ-002` 未开始（依赖 M12 核）。
- **Vast / smon / 中断**：不在本次范围。

## 4. 复现

```sh
make build-gem5                       # 组件构建（主控机）
python3 tools/gem5/check_tiny_hmon.py # gem5 Tiny 两件装载 + hmon 的 237 条 oracle
python3 tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py \
  --selection timeout-inventory --link-mode dynamic --jobs 48 \
  --gem5-timeout 3600 --qemu-timeout 3600 --resume
```

> hmon 用例在 qemu 侧以 `-kernel <elf>` 直跑（BootROM `PT_LOAD`），gem5 侧用 FS 模式同一 ELF；两侧结果表按同一布局 dump 后逐字节比对。
