# m18-qemu-002: monitor-first 异步仲裁与 pending 迁移

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m16-qemu-002`（同组件写者，须已合入/已验证）+ `ADR-0059` Accepted + `contract-see §3/§6.3/§6.4` 及 `ADR-0042 D7.4`/`ADR-0045 D3/D9` 已同步；**不得与 `m16-qemu-002` 并发写 `components/qemu`**
**可并行分片**：否
**预估**：4–6 h（标定：同档最近 5 件派单→合入实测中位数；仲裁/pending 迁移 + 探针更新，取 1.5–2× 中位）
**档位**：大改（QEMU 异步仲裁语义 + pending 迁移 + 探针/归档更新）
**状态**：待开始
**执行环境**：本地（`qemu-dadao` / `qemu-system-dadao` `-M kaiwu-vast`）

## 背景

`spec/DADAO-12 §5.2（三）（四）（五）` 已是 **monitor-first**：异步源（`TIMER`=cfx_hart、`PMEM_DMA`=cfx_pmem）先入**当前运行模式 monitor**（U/J/S/H → umon/jmon/smon/hmon），mask 两级（`<mode>_cfx_intr_mask` + `global_cfx_intr_mask`）与 delivery pending（`cg5 rc5`）都在 monitor，位索引 = **来源 cfxha**；monitor 可自行处理并 `escape`、也可 `trap` 到源 cfx，处理期间不嵌套。contract/adr 原先的 target-first 口径未及时同步（用户 2026-11-22 裁定）。

当前 QEMU `helper.c`（`dadao_async_sources`/`dadao_async_lowest`/`dadao_async_arbitrate`/`cfx_enter` 异步路径）仍是 **target-first**：投递到源 cfx（`cfx_hart`/`cfx_pmem`）、pending 记目标 cfx 的 `cg5 rc5`。须迁到 monitor-first。

## 目标

1. **仲裁改为当前 mode monitor**：`dadao_async_arbitrate()` 投递目标 = 当前运行模式 monitor（`inner_run_mode` → umon/jmon/smon/hmon），`cfx_enter(async)` 的 `target` 传 monitor、`cause` 传源 cause id。
2. **pending 迁到 monitor `cg5 rc5`**：被 mask 屏蔽时置 monitor 的 `excp_pending`（位 = 源 cause id `1<<10`/`1<<8`），不再记源 cfx；投递成功清位、软件写 0 取消（只有 monitor 这一份 delivery 记录）。
3. **两级 mask 仍按 monitor**：`<mode>_cfx_intr_mask` 与 `global_cfx_intr_mask` 都查当前 mode monitor，位索引 = 来源 cfxha（TIMER=15、PMEM_DMA=32）。
4. **同源 OR/补投/单层投递**：同源屏蔽期重复事件按单 bit OR 合并；mask 写/`escape`/新源事件后重踢补投；每次至多投递一个源（按源 cfxha 升序），不嵌套。
5. **更新探针/归档**：`min_rom_probe_integ051t`、K2/K5 异步探针、`tests/arch/vast-arch-inventory.md`、QEMU changelog 对齐 monitor-first。

## 验收（逐条贴真实 rc）

1. 修前用最小复现证明 target-first（TIMER 投递到 `cfx_hart`、pending 记 `cfx_hart`），修后同一程序投递到 monitor、pending 记 monitor `cg5 rc5`（`cfx2rd` 读回证实）。
2. **可达 FAIL ≥3 路**（`cp`+md5 还原 + 重建）：① 仲裁目标仍传源 cfx ⇒ 探针红；② pending 仍记源 cfx ⇒ 探针红；③ 两级 mask 未按 monitor（按源 cfx 行）⇒ 探针红。
3. **既有 M16 cfx5/cache 代表集不回归**：`check-qemu-*` 既有 qemu 门控 rc=0；异步 pending 迁移后 K2/K5 异步探针更新且可达 FAIL。
4. 不回归：`check-patch-tree` qemu 段与基线**逐行相同**（0 problem）；`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. `min_rom_probe_integ051t`、`tests/arch/vast-arch-inventory.md` 更新为 monitor-first 表述；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/**`（补丁 + changelog）、`tests/arch/**`（探针与归档）、`tests/unit/qemu/**`、`.tao/knowledge/issues.yaml`、本任务书。
3. **不改** `spec/`、`.tao/contracts/`（monitor-first 对齐已由架构师同笔完成，本任务不改）、`Makefile`、`components/linux/**`、`components/musl/**`；不改版本号。
4. **排队**：`m16-qemu-002 → m18-qemu-002 → m16-qemu-003 → m16-testcases-009`；本任务**必须在 `m16-qemu-003` 之前合入**，且**不得与 `m16-qemu-002` 并发写 `components/qemu`**。合入后 M16 的 003/009 基于新模型重跑（其依赖/背景已由主会话标注，本任务不改那两份 M16 任务书）。
5. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

- `ADR-0059` 待确认 2（异步投递时 monitor 帧 `excp_cause_id` = 源 cause 号，与 monitor 自身 `RASOF`/`ILLI` 同号不同义）；QEMU 侧如何记录/暴露「异步源身份」须与该裁定一致，确认后才派单。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
