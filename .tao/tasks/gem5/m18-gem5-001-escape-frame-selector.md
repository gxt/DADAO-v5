# m18-gem5-001: gem5 escape frame selector 语义与断言

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-spec-003`（escape 编码真源）、`m18-idl-001`（参考语义/向量）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 b6 escape 语义 + 断言 + 生成断言，取 1.5–2× 中位）
**档位**：中改（功能模型编码语义）
**状态**：待开始
**执行环境**：本地（gem5 SE/FS 现有构建流程）

## 关联（2026-11-24，来自 M17）

- `tests/inst/11-cfx/escape_ciii_cfx.S` 的 `__c13`（`imms18=2` ⇒ 期望 `CFXESC`）在 gem5 上仍按旧编码（`imms18 >> 1 != 0 ⇒ ILLI`）返回 `rc=13`；新旧 gem5 二进制实测相同 ⇒ 既有能力缺口，非 `m17-gem5-001` 回归（证据见该任务书「新发现/坑」④）。本任务收口前须覆盖该例，否则 M17 全四方无法达到 274/274。

## 背景

`m18-spec-003` 已把 `escape` 改为 `imms18` bit1 帧选择（0=cg5，1=cg9；合法 `{0,1,2}`，`3 ⇒ ILLI`；cg9 仅偏移 0；`imms20 ∈ {0,4,8}`）。gem5 侧仍按旧编码：

- `components/gem5/patches/src/arch/dadao/exec/b6.cc` 注释/实现只认 0/+4 与 `imms18[17:1]` SBZ；
- `b6_test.cc` 的 escape SBZ/帧测试未覆盖 bit1/cg9；
- `decode/decode_assertions.inc` 由 opcodes 生成，需随 `contracts/opcodes.yaml` 重生成；
- `tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 已由 spec-003 更新，gem5 模型必须与之对齐。

## 目标

1. `b6.cc`/`b6.hh`：escape 解析 `imms18` bit1；cg5 偏移 0/+4；cg9 仅 0；`imms18=3` 或 `[17:2] != 0` ⇒ ILLI；cg9 帧判据/返回（`cfx_hart cg9 rc3 != 0`、`prev_run_mode/prev_cfx_code/cause_ip`、saved global mask）按 `DADAO-12 §5.3`。
2. `b6_test.cc`：增 `imms18=2`（cg9 路径）、`imms18=3`/`[17:2]` 非零的 ILLI；保留原 cg5 0/4 用例。
3. **重生成** `decode/decode_assertions.inc`（用仓库生成器），确保 `check-qemu-forms`/legality 相关门控与 `contracts/opcodes.yaml` 一致。
4. `tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 与新模型一致（0 error）；若 gem5 构建成本高，至少跑静态 checker + 受影响的 b6 单测。

## 验收（逐条贴真实 rc）

1. gem5 构建（既有流程）rc=0；`b6` 相关单测 `imms18=0/1/2/3` + `[17:2]` 非零用例通过；`imms18=2` 真走 cg9。
2. `tools/gem5/check_b6.py` 静态 0 error；`check-qemu-forms`/`check-legality-drift`/`check-spec-codeblocks` rc=0。
3. **可达 FAIL ≥2 路**：① 仍按旧 `[17:1]` SBZ ⇒ 新单测红；② cg9 帧不恢复 mask ⇒ 测试红；`cp`+md5 还原后回绿（源码还原后重建）。
4. 不回归：既有 gem5 代表集/`check-gem5-decode`（如适用）rc=0；`check-patch-tree` gem5 段与基线逐行相同（musl 10 基线除外）；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/gem5/patches/src/arch/dadao/exec/b6*`、`components/gem5/patches/src/arch/dadao/decode/decode_assertions.inc`（生成物）、`components/gem5/changelog.md`、`tools/gem5/check_b6.py`（仅期望）、本任务书。
3. 不改 QEMU/RTL/LLVM/内核/spec/contracts；不改版本号；术语「bank = 寄存器组」。
4. 组件补丁经 `make_patch.py gem5` 重导；生成断言用仓库生成器；还原 `cp`+md5；还原后重建。
5. 若 gem5 模型语义与 spec 冲突，按 spec 改模型并写「待裁定」，不得反向改 spec。

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
