# GEM5-005t: scaleB C1 与 sc rd0 解码更新

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-004t`、`SPEC-181t`
**状态**：待开始

## 用户授权

用户 2026-11-01：scaleB C1 第三源 `rfHD → rdHD`（同 `orrr` 编码）；`sc rdHB=rd0 ⇒ ILLI`；授权 gem5 独立任务。

## 目标

1. 更新 `components/gem5` 的 decode 表/断言：
   - `ftsclb`/`fosclb` 第三字段 `rfhd → rdhd`，编码/opc/ha 不变；
   - 旧 `rf,rf,rf` 断言删除/更新；
   - `sc.*` 的 12 条 `rdHB=rd0` 新增 `dst_rd0` 合法性断言。
2. 更新 `tools/gem5/gen_decode_table.py` 从当前 `contracts/opcodes.yaml` 生成；`decode-assertions.tsv` 同步。
3. 只改 `components/gem5/**`、`tools/gem5/**`、本任务书/milestones；不改 tests/spec/contracts/LLVM/QEMU/Makefile。
4. 执行语义实现不在本任务；B6 后续处理。

## 验收

1. `make check-gem5-decode` rc=0（264 正例 + 负例；新/旧字段反例）。
2. `check-patch-tree`/`check-source-state` rc=0；`make build-gem5`（增量）rc=0。
3. 旧 `ftsclb/fosclb rf` 必须 FAIL；`sc rd0` 负例必须 FAIL。
4. 证据 `.work/evidence/<任务ID>/`；完成区 ≤30 行，状态待验收。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
