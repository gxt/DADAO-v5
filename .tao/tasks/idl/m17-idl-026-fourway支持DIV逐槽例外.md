# m17-idl-026: `idl_four_way` 支持 `expected-divergences` 的逐槽例外

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-testcases-008`（`escape_ciii_cfx` 按平台期望，同一批次）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-27 裁定 1）

Tiny 缺 `cg4`/`cg15 rc3`（`DIV-18`，用户 2026-11-26 裁定保持 M16 面）。用户 2026-11-27 裁定：**不造假常量、不跳过**，改为

- 用例在 Tiny 上验证「访问 ⇒ CFXREG」（缺失本身是被验证的行为），签名槽记录真实的 `cause_id`/`cause_info`；
- 该用例登记 `expected-divergences.yaml`，`check-idl-full` **按平台期望**判定（Tiny 用声明值，IDL/QEMU/gem5 仍按规范值并保持三方一致）。

`tests/arch/expected-divergences.yaml` 已有可选 `slots` 机制（`case` + 0 基 `slot` + `chipyard` 期望值，供 `tests/arch` 承载使用），但 `idl/tools/idl_four_way.py` **完全不读**该文件（grep `divergence` 0 命中，`m17-chipyard-002` 已核实）。

## 要做

1. `idl/tools/idl_four_way.py` 读取 `tests/arch/expected-divergences.yaml`（路径按仓库根；文件缺失/格式错 ⇒ 明确报错，不静默）：
   - 只采用与**用例镜像**匹配、且含 `slots` 的条目（`case` 取 `.S` 路径或用例 id，与现有机制一致）；
   - 对声明平台（如 `chipyard`）的对应槽：与声明值比对，**不参与**四方逐字节一致判定；
   - 对其它平台：仍按 `expected.tsv` 与该三方一致性判定（不得因例外而放宽）；
   - 例外条目**未生效**（用例未出现该差异 / 声明值不符）⇒ 判红并提示「条目应删除或值需更新」，防静默逃逸；
2. 输出与 JSON 中标注「已应用的 DIV 例外」（id + slot），便于复核；
3. 不影响未声明例外的 273 个用例（比较逻辑保持原样）；
4. 文档：`idl/docs/four-way.md` 或等价处补一段「DIV 逐槽例外如何生效/失效」。

## 不做

- 不改 HLD/QEMU/gem5/RTL/IDL 语义；不改 `expected.tsv` 槽数；
- 不改 `tests/arch` 承载（其用法不变）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/idl_four_way.py`、`idl/docs/four-way.md`、必要时 `tests/arch/expected-divergences.yaml` 的**注释**（不改条目）、本任务书；完成区 ≤30 行。

## 验证

1. 与 `m17-testcases-008` 合并后：`make check-idl-full` **274/274**（chipyard 在 `escape_ciii_cfx` 上按 DIV 声明值判，IDL/QEMU/gem5 三方仍逐字节一致）；
2. **可达 FAIL ①**：把 DIV 声明的 `chipyard` 槽值改错 ⇒ 该例必红；还原回绿；
3. **可达 FAIL ②**：把例外条目的 `case` 改错（不匹配）⇒ 该例因四方不一致仍红（且提示条目未生效）；还原回绿；
4. 回归：其余 273 例判定不变（改动前后同一批日志逐行对比，仅新增例外输出）；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
