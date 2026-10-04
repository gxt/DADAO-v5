# LLVM-044t: M1 RD 多寄存器加固（不等 count 报错、{rd0:rd63} 溢出报错）

**模块**：llvm
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（需 `make build-mc` 重建 LLVM MC）

## 目标与 resolved_by

实现 2 条无依赖的 M1 MC 合法性加固 issue（**需 LLVM 重建**，一次一个长构建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-104 | M1 `rd2rd`/`rb2rb` 两 `{start:end}` 组 count 不等时静默取末组 ⇒ 须硬报错 |
| ISS-106 | M1 RD 多寄存器 `{rd0:rd63}`（count=64）静默截断为 `immu6=0` ⇒ 须按 `mreg_range_overflow` 硬报错 |

`resolved_by`：本任务 `LLVM-044t`。

## 接口规范

- **输入**（已核实，现状）：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`：
    - `mreg_range_overlap` 检查（`rd2rd`/`rb2rb`，L~1000）**只查重叠**；
    - `group counts differ` 加固（L~1023）**仅对 FP/`rd2rf`/`rf2rd`** 生效，注释明确「pre-existing M1 `rd2rd`/`rb2rb` behaviour (last group wins) is left unchanged」；
    - `mreg_range_overflow` 检查（L~961-996）**仅对 FP**（`isFPMregMnemonic` + `ldm.t/stm.t/ldm.o/stm.o` 的 RF 组），M1 RD 组不在内。
  - 规则真源：`contracts/legality_rules.yaml`（`mreg_range_overflow` / `mreg_range_overlap`）、`contract-isa.md`（`ldm.*`/`stm.*`/`rd2rd`/`rb2rb` 的 `immu6 ∈ 1..63`、`rdha+immu6>64 ⇒ ILLI`）。
- **输出**：
  - `DADAOAsmParser.cpp`（+ 必要时 `DADAOInstrInfo.td` 的 `DecoderMethod`）：M1 `rd2rd`/`rb2rb` count 不等 → Error；M1 RD `{start:end}` count=64（或起始+count>64）→ Error。
  - 新增/扩展 lit：`tests/lit/MC/Dadao/*.s`（不等 count、`{rd0:rd63}` 反例 + 合法正例）。
  - 更新 `components/llvm-project/changelog.md`（按任务一条）。
- **约束**：
  - **Spec-first**：期望行为以 `contracts/legality_rules.yaml` + `contract-isa.md` 为准；Error 级、**不得**降 warning。
  - **最小改动**：只加固 M1 侧，不顺手改 FP 侧既有逻辑。
  - 与在飞任务 **`LLVM-034t`**（其 `DADAOISelLowering/InstrInfo` 补丁当前有未提交改动）**无文件交集**（本任务主要改 AsmParser），但**构建须串行**、`make check` 不得并发。

## 验收标准

1. **ISS-104**：`llvm-mc`（`.work/build/.../llvm-mc`）对 `rd2rd {rd4:rd6}, {rd8:rd12}`、`rb2rb {rb1:rb2}, {rb3:rb5}` → **EXIT≠0**、Error 级；对 count 相等的合法组 → EXIT=0。给出真实输出。
2. **ISS-106**：`llvm-mc` 对 `ldm.o {rd0:rd63}, [rb1, rd0]`（或等价）→ **EXIT≠0**、报 `mreg_range_overflow`；对 `{rd0:rd62}`（count=63）→ EXIT=0。给出真实输出。
3. **反例门控**：把新加的 count 相等检查注释掉后重建 → 验收 1 应 FAIL（恢复旧行为）；还原并**重建**后回绿。给出注入→FAIL→还原→重建→PASS 的真实输出（还原须含重建，禁止在污染二进制上取结论）。
4. `make check-lit` 全绿；`make check` EXIT=0；`check-patch-tree` 通过（补丁导出纪律：写 `/tmp`、非空 blob、断言⑥）。
5. `components/llvm-project/changelog.md` 含本任务条目。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-044t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- **重建成本申报**：重建 LLVM MC，预计 30–90 分钟；一次只跑一个；`JOBS` 默认 8，禁 `-j$(nproc)`。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/llvm/LLVM-044t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-044t/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
