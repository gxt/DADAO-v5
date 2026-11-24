# m16-spec-003: DMA 与 D-cache 一致性语义 + 契约笔误

**模块**：spec
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 已合入（ISS-531 实测方）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（契约语义，复核 ≤40 min；**语义方向须用户确认后开工**）
**状态**：待开始

## 背景

- `ISS-531`：`m16-chipyard-022` 的 DMA 引擎直接读写 PA，绕过 D-cache；若 CPU 先缓存目标行，DMA 写后 CPU 可能读到旧值。`DADAO-12 §4.9` 未规定 DMA 与 D-cache 的先后/失效语义，探针靠"只用 CPU 未触碰的 PA 行"回避。
- `ISS-526`：`contract-see` 的 power `start` 写成 `0x3_ffc0_0000`，与 `spec/Kaiwu §3`/`machine.yaml(vast)` 的 `0x3ff_ffc0_0000` 差一位（既有笔误）。

## 要做

> **语义方向已定（用户 2026-11-24 裁定 A）**：DMA 与 CPU 缓存**不保证硬件一致**，由**软件负责**——START 前对源/目标区间 `clean`，完成后 `invalidate`；硬件不做 snoop/自动失效。

1. **一致性语义（A）**：在 `§4.9` 写清：
   - DMA **不**与 D-cache 做硬件一致性（不 snoop、不自动失效）；
   - 软件职责：`START` 前把源区间 `clean`、完成后把目标区间 `invalidate`（顺序与时机写死）；
   - 目标为 BootROM/只读区的行为（写 ⇒ `PA_FAULT`）、`BUSY` 期间的可见性、与 `fence` 的关系；
   - 未按 A 操作时"读到旧值"属软件错误，不由硬件报异常。
2. **契约笔误**：订正 `contract-see` 的 power `start` 值；顺带核 power 段其它数值与 `machine.yaml(vast)` 一致。
3. **同步面**：`contract-see`、`contract-cfx-aliases`（若涉及）、`spec/.manifests.toml`（只重算受影响册）；版本仍 `0.8.0-rc`（内容改，不升号）。
4. **不改**实现与测试（QEMU/RTL/gem5 的 DMA 语义如与裁定不符，另立任务）。

## 不做

- 不实现 DMA 失效硬件或软件 fence；
- 不改 `cfx_pmem` 寄存器面（ISS-533 另立）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `spec/DADAO-12…`、`.tao/contracts/contract-see.md`、`spec/.manifests.toml`、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `§4.9` 有明确的一致性条款（含软件职责/硬件行为、失效粒度、与 `fence` 的关系），无"未定义"表述；
2. `grep` 全仓 `0x3_ffc0_0000` 0 命中（历史/ADR 除外），`0x3ff_ffc0_0000` 与 `machine.yaml` 一致；
3. `check-spec-refs`、`check-manifests-guard`、`check-spec-codeblocks`、`check-contracts-*`、`check-cfx-aliases` rc 记录；
4. **可达 FAIL ≥2**：注入"删一致性条款"、"回退 start 笔误" ⇒ 门控/检查红；`cp`+md5 还原回绿。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
