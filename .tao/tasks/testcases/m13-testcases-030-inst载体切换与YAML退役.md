# m13-testcases-030: `tests/inst` 载体切换（`.S` 入门控）+ YAML 退役

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`/`013`（`.S` 套件已建）+ `m13-spec-001`（退出码表）
**可并行分片**：否（改门控集合，需与语料任务串行）
**状态**：待开始

## 背景（`ISS-413`，P1）

`base/mem-rd/mem-ra/mem-rb` 三册里 `ld`/`st`/`ldm`/`stm` 的 id 已全部有 `.S`，但删 YAML 会让**四个门控**立刻红：`validate_vectors`（116 gap）、`check_case_ledger`（多 167 行）、`check-generator-sync`（无输入）、`check-tests-index`（file 不存在）。

根因：`.S` 套件**不在任何门控里**，而 `inventory.md`/`case-ledger`/生成器同步仍以 YAML 为真源。

## 目标

1. **载体切换**：`tests/inst/inventory.md` 的「类/载体」登记改为指向 `.S`（或由 `.S` 注释派生），`validate_vectors` 接受 `.S` 载体
2. **新门控**：`run_asm_suite.py` 进 L2（如 `check-inst-asm`），至少覆盖已迁移的 38 个 id
3. **生成器退役**：`generate_mem_vectors` 等对已迁移族的 `--check` 退役；`check-generator-sync` 改指
4. **YAML 删除**：三册清空后 `git rm`，`tests/inst.yaml` 索引条目同步，`check_case_ledger --write` 重生成
5. `MIGRATION.md` §5 台账勾掉

## 验收

1. 删除三册 YAML 后：`validate_vectors` / `check_case_ledger` / `check-tests-index` / `check-generator-sync` **全部 rc=0**
2. 新门控 `check-inst-asm` rc=0，且**能失败**（注入一个错误期望 ⇒ 红）
3. 273 例 md5 不变；`check-inst` rc=0
4. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

（待填）
