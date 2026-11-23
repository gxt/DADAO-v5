# m18-chipyard-001: RTL escape frame selector 语义

**模块**：chipyard
**项目里程碑**：M18
**依赖**：`m18-spec-003`（escape 编码真源）、`m18-idl-001`（参考语义/向量）
**可并行分片**：否（同 `components/chipyard` 写者；须等 M16 当前 chipyard 批次收口）
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 RTL 解码/执行 + 探针，取 2–3× 中位）
**档位**：大改（RTL 指令语义）
**状态**：待开始
**执行环境**：本地（chipyard `WumingTiny/Vast` 构建与 sim）

## 背景

`m18-spec-003` 已把 `escape` 改为 `imms18` bit1 帧选择（0=cg5，1=cg9；合法 `{0,1,2}`，`3 ⇒ ILLI`；cg9 仅偏移 0；`imms20 ∈ {0,4,8}`）。chipyard RTL 仍按旧编码：只认 0/+4、`imms18[17:1]` SBZ，cg5 现场。需在 RTL 实现 bit1/cg9 路径，并保证 QEMU/RTL 逐字节一致。

## 目标

1. RTL 解码/执行：`imms18` bit1 选帧；cg5 0/+4；cg9 仅 0；`3`/`[17:2]` 非零 ⇒ ILLI；cg9 帧判据、返回 `prev_run_mode/prev_cfx_code/cause_ip`、恢复 saved mask（按 `DADAO-12 §5.3`）。
2. 探针：`tests/inst/11-cfx` 的 escape 用例（0/1/2/3）在 `WumingVastConfig`/`WumingTinyConfig`（如适用）上跑通；与 QEMU 同 ELF 逐字节签名一致。
3. 生成物/断言：受 opcodes 影响的 decode 断言重生成；`check-qemu-forms`/`check-legality-drift` 与契约一致。
4. 不回归：既有 M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem。

## 验收（逐条贴真实 rc）

1. chipyard `make verilog` + sim 构建 rc=0、`%Error`=0；sim md5 记录并注明环境。
2. escape 0/1/2/3 的 RTL 探针通过；`imms18=2` 走 cg9，`3`/`[17:2]` 非零为 ILLI；与 QEMU 同 ELF 签名逐字节一致（不一致登记 `expected-divergences.yaml` 并说明）。
3. **可达 FAIL ≥2 路**：① 仍按旧 SBZ ⇒ `imms18=2` 用例红；② cg9 不恢复 mask ⇒ 签名红；还原后重建回绿。
4. 不回归：M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/chipyard/patches/**`（escape 解码/执行/生成断言）、`components/chipyard/changelog.md`、`tests/inst/11-cfx/**`（仅如需）、`tests/arch/**`（探针）、本任务书。
3. 不改 QEMU/gem5/LLVM/内核/spec/contracts；不改版本号；术语「bank = 寄存器组」。
4. 组件补丁经 `make_patch.py chipyard` 重导；生成断言用仓库生成器；还原 `cp`+md5；还原后重建。
5. 须等 M16 当前 chipyard 批次（`m16-chipyard-020/021` 等）收口，避免同组件并发写。

## 待裁定

无。

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
