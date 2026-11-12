# m13-testcases-012: `01-load-store` 单元素（`ld.*` + `st.*`）改为汇编+宏

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-001`（退出码表 `0x01`–`0x7F` = 失败点 1–127）+ `m12-chipyard-008`（访存实现）
**可并行分片**：否（共享 `tests/inst/`）
**状态**：待开始

## 背景（用户 2026-11-12 裁定）

- **M13 的核心问题**：`tests/inst` 里每条指令到底测了什么 —— 这是三平台差分的基础
- **YAML 退出**：YAML 不可读、且需再转成汇编才能跑，转换本身可能出错 ⇒ 改为**汇编 + 宏**，期望值内联
- **分类**：大类 = SimRISC 册（`01-load-store` … `12-misc`）；小类 = `contracts/opcodes.yaml` 的 **id**（一 id 一文件）
- **目录**：`tests/inst/01-load-store/<id>.S`（id 已含 format/bank，文件名不重复 format）
- 台账：`tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移状态）

## 范围（本任务 = 18 个任务里的第 1 个）

覆盖 **19 个 id**：
- `ld.*` 11 个：`ld.ub/uw/ut/o/sb/sw/st`（`rrii` × rd/rb/ra/rf 形式）
- `st.*` 8 个：`st.b/w/t/o`（`rrii` × rd/rb/ra/rf 形式）

**不含** `ldm.*` / `stm.*`（属 `01-b`）。

## 目标

1. 建目录 `tests/inst/01-load-store/`，每 id 一个 `.S`（19 个文件）
2. 宏层放 `tests/inst/macros/`：至少
   - `TEST_LD(测试点号, 助记符, 期望值, 地址基址, 偏移, 目标 bank)`
   - `TEST_ST(测试点号, 助记符, 源值, 地址基址, 偏移)`
   - `__CHECK(期望, 实际)` / 失败即 `SYS_EXIT(测试点号)`
   - 参照 `.cache/refs/DADAO/DADAO-testset/isa/macros/scalar/test_macros.h` 的写法（**只参考结构，不复制**）
3. **每 id 按 5 类写用例**（模板见 `tests/inst/MIGRATION.md §3`）：encoding / legality / semantic / boundary / overlap
   - 访存特有边界：**自然对齐**（`ld.o` 8B、`ld.t` 4B、`ld.w` 2B、`ld.b` 1B）+ MALIGN、地址窗口外 ⇒ `CFXMEM`、`rd0` 作目的 ⇒ ILLI
4. **迁移既有 YAML**：把 30 个 YAML 里属于这 19 个 id 的 case 全部并入（含 `base/mem-rd.yaml`、`mem-rb/ra/rf.yaml`、`base/reserved.yaml` 中命中部分）；**只有当某 YAML 文件的全部 id 都迁完后**才 `git rm`，并更新 `MIGRATION.md` 台账
5. 三方对照：chipyard == QEMU == gem5 逐字节（同一镜像）

## 验收

1. 19 个 `.S` 文件齐全，`ls tests/inst/01-load-store/*.S | wc -l` == 19
2. 每个文件检查点数 ≤127，失败点号 = 用例序号（`SYS_EXIT(n)`）
3. **三方逐字节一致**（含全部 MALIGN/CFXMEM/ILLI 故障例）
4. `make check-inst` rc=0；`check-tests-index`/`check-case-ledger` rc=0（新文件需登记 `tests/inst.yaml`）
5. 273 例 md5 不变
6. `MIGRATION.md` 台账更新：本任务覆盖的 19 个 id 标「已迁」，对应 YAML 若已清空则标「已删」
7. **可达 FAIL 注入**：把某个 boundary 用例的期望改错 ⇒ 该文件对应检查点号非零退出
8. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 一个 id 一个 ELF 意味着 19 次汇编/运行；用现有 `tools/testcases/` 的驱动批量跑，不要手搓循环。
- **不要**改 `contracts/`、`spec/`、`Makefile` 的门控集合（本任务只产语料 + 宏）。
- `.work` 必须软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

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
