# m14-spec-003: 内核 VA 窗口改为 `[3 TiB, 4 TiB)`（四项冻结地址 +3 TiB）

**模块**：spec
**项目里程碑**：M14
**依赖**：`m14-spec-001`（已合入，§6.3 初版）；`m14-qemu-001`、`m14-linux-002` 按本任务结论实施地址
**可并行分片**：否（单册单写者；`spec/Machine-v5` + 契约 + 投影 + 检查器 + ADR 同笔）
**预估**：3–4 h
**状态**：待开始

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 用户原话（摘要）：「用 `[3TiB, 4TiB)` 做内核空间，所有冻结的地址，增加 3TiB 的偏移」；确认理由 = 内核地址不应从 0 开始。

由此**取代** `m14-spec-001` 冻结的四个低地址；用户同时授权本任务修改 `spec/Machine-v5` 与该册只读锁（`docs/Process-06 §2` 的事先授权）。

## 背景

DADAO 内存窗口 `VA` 只有 42 位（`addr[47:42]=0`，即 `[0, 4 TiB)`），无法像 x86/RISC-V 那样使用 64 位高半区。原 `§6.3` 把内核放在 `0x10_0000` 并做全域身份映射 `VA[0,2GiB)→PA[0,2GiB)`，导致「内核与用户/物理低端混在一起」。本次改为内核独占高端 1 TiB。

## 目标值（唯一真源，逐项写死）

| 项 | 新值 | 旧值（作废） |
|---|---|---|
| 用户 VA 空间 | `[0, 3 TiB)` = `[0, 0x0000_0300_0000_0000)` | 未定义 |
| 内核 VA 窗口 | `[3 TiB, 4 TiB)` = `[0x0000_0300_0000_0000, 0x0000_0400_0000_0000)` | — |
| 首张页表页 VA | `0x0000_0300_0000_0000`（`PTBR` 仍指 PA 0） | `0x0` |
| boot info VA | `0x0000_0300_0001_0000` | `0x0001_0000` |
| 内核镜像区 VA | `[0x0000_0300_0010_0000, 0x0000_0300_0400_0000)`（63 MiB） | `[0x10_0000, 0x400_0000)` |
| `kernel_base` / `e_entry` | `0x0000_0300_0010_0000` | `0x0010_0000` |
| initramfs VA | `[0x0000_0300_0400_0000, 0x0000_0300_0600_0000)`（≤32 MiB） | `[0x400_0000, 0x600_0000)` |
| VA↔PA | `VA = PA + 3 TiB`（内核窗口内固定偏置；`PTBR`/页表项仍用 PA） | 身份映射 |

- 物理侧不变：PA RAM `[0, 2 GiB)`；内核镜像 PA `[0, 63 MiB)`、boot info PA `0x1_0000`、页表页 PA `0`。
- smon 建表改为「只映射内核窗口」：`VA[0x300_0000_0000, +64 MiB) → PA[0, 64 MiB)`（512 MiB 超页若干，最小 1 页即可覆盖前 64 MiB），**不再是全域身份映射**。
- `rb17` 仍为 boot info 的 **VA**（新值），`rb16` 为入口 VA。

## 范围

1. `spec/Machine-v5 §6.3`：替换 `§6.3.1` 分区表、`§6.3.2` 装载规则中的地址与映射表述、`§6.3.3` boot info 的 `kernel_base`/`initramfs_base` 取值、`§6.3.4` 进入态（VA/偏置）、`§6.3.5` 不定义项；版本 `0.4.6-rc` → `0.4.7-rc`，附录记录。
2. `.tao/contracts/contract-linux-boot.md`：同步地址与映射（含 `VA = PA + 3 TiB` 的表述）；版本 `0.1.0` → `0.2.0`。
3. `contracts/linux-boot.yaml`：地址常量与 `kind` 语义同步；新增/复用 `va_pa_offset` 字段（若无则加，需与契约同步）。
4. `tools/linux/check_boot_contract.py`：断言同步（三方一致 + 新增「内核窗口起点 3 TiB」「VA=PA+3TiB」两条硬断言；旧值出现即 FAIL）。
5. `manifests/spec-readonly.lock.toml`：`Machine-v5` sha 同笔重算。
6. `.tao/adr/adr-0051-linux-boot-abi.md`：**经用户授权的就地修订**——D3/D4/D5/D6 的地址与映射改为新值，`状态说明` 记 `rev. 2026-11-13`（用户原话摘要 + 渠道），不改其它 decision。

## 验收

1. `python3 tools/linux/check_boot_contract.py` rc=0；`--self-test` 各类注入仍可达 FAIL（含「旧地址回潮」一类）。
2. `git grep -n "0x0010_0000\|0x0001_0000\|0x400_0000" -- spec/Machine-v5* .tao/contracts/contract-linux-boot.md contracts/linux-boot.yaml` ⇒ **0 命中**（除「旧值作废」注记段外）。
3. spec 系列门控 + `check-contracts-dir`/`check-contracts-pending`/`check-spec-readonly` rc=0；锁 sha 现算 MATCH。
4. ADR 内 D3/D4/D5/D6 与新值一致，且修订记录含用户原话摘要；`check-knowledge-refs` rc=0。
5. ≥2 路注入可达 FAIL + `cp`+md5 还原（注入后必须能判红）。
6. 完成区 ≤30 行、无运行期路径；不改台账 / `discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree` 作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 只动「范围」列出的文件；越界须披露。
5. 需用户语义裁定写进「待裁定」段返回主会话。
6. 禁 `git checkout/restore/stash` 还原注入；用 `cp`+md5。

## 审阅记录

（待填）
