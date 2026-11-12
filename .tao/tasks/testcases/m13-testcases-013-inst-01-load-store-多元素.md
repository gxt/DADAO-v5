# m13-testcases-013: `01-load-store` 多元素（`ldm.*` + `stm.*`）改为汇编+宏

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（已合入：宏层 `inst_test.inc` + `run_asm_suite.py` 可复用）
**可并行分片**：否（共享 `tests/inst/`）
**状态**：待开始

## 背景

延续 `m13-testcases-012` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。本任务覆盖 `01-load-store` 的**多元素**部分。

## 范围（19 个 id）

`ldm.ub/uw/ut/o/sb/sw/st` 与 `stm.b/w/t/o`，各自 rd/rb/ra/rf 形式（以 `contracts/opcodes.yaml` 实际 id 为准，自己列全）。

## 与单元素任务的关键差别（必须覆盖）

1. **元素个数 `immu6`**：0/1/2/8/63 等；`immu6=0` 的合法性（按 `contracts/legality_rules.yaml` 与 spec）
2. **源/目寄存器范围**：`rdHA + immu6` 不得越过 bank 边界 ⇒ ILLI（spec 有明文）
3. **整段预检 vs 中途失败**：
   - 首地址不对齐 ⇒ `MALIGN`（**第一拍之前**，目标寄存器/内存不变）
   - 整段越出地址窗口 ⇒ `CFXMEM`（同样在预检阶段）
   - 中途 `denied` ⇒ 当前模式 `CFXMEM`（**非精确**，`info` = 当时 beat）
4. **8 字节 beat 分组**：元素按宽度自然对齐 ⇒ **元素不跨 beat**；`stm.b` 的 9 元素例应正好用 2 个 beat、第二拍 mask 只开 1 lane（`ISS-381` 的 F-b：旧向量全 count=1，多元素路径零覆盖）
5. **写后读保持**：`stm` 不能破坏相邻字节（用 24-beat pattern 验证保持区）

## 参考

- 宏层：`tests/inst/macros/inst_test.inc`（`TEST_LD` / `TEST_ST` 已有；本任务补 `TEST_LDM` / `TEST_STM`，保持「一行可读」）
- 驱动：`tools/testcases/inst/run_asm_suite.py`
- 台账：`tests/inst/MIGRATION.md`

## 验收

1. `ls tests/inst/01-load-store/ldm*.S tests/inst/01-load-store/stm*.S | wc -l` == **19**
2. 每文件检查点 ≤127、点号连续；`ldm`/`stm` 的多元素例 **count>1 占多数**（不得像旧向量那样全是 count=1）
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含 MALIGN/CFXMEM/ILLI 与中途失败
4. `make check-inst` rc=0；`check-tests-index` rc=0；273 md5 不变
5. **YAML 清理**：`base/mem-rd.yaml`、`mem-ra.yaml`、`mem-rb.yaml` 里的 `ldm`/`stm` id 迁完后，若三文件已无其它 id ⇒ `git rm` 并在 `MIGRATION.md` 勾掉
6. **可达 FAIL 注入**：改错一个多元素 boundary 期望 ⇒ 对应点号非零退出（三平台同值）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修复前必须保留），并在完成区注明仍依赖它。
- `.work` 软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

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
