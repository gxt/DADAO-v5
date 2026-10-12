# INFRA-068t: `setjmp`/`longjmp` 真实现（用 RA 存取/块赋值）

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-067t`（同改 `components/picolibc/patches` ⇒ **串行**）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 6 项**，原判"最难/不可为"）；依据 blocked **1**（`setjmp` 桩）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`setjmp/longjmp` 因 RegRAS 深度问题如何处理。
- 选项：A「**真实现（推荐）**」／B「记 `excluded`」／C「先做最小可行性验证」。
- **用户选择 = A「真实现（推荐）」**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## **事实修正（本任务的核心前提）**

- 现行 `setjmp.S`（`INFRA-057t`）是**显式失败桩**，其注释称「ISA 除 `ret` 外**无指令**可弹/恢复 RegRAS 条目」——**该陈述错误** ✗。
- **ISA 事实上提供**（`contract-isa §1.3.4` 明文）：
  - **`ra0`–`ra63` 可读写**（「`ra0` 作目的或源均不触发异常（**可读写**）」）；
  - 覆盖指令：**`ld.o`/`st.o`、`ldm.o`/`stm.o`**（`SimRISC-01 §存取RA寄存器`）与 **`rd2ra`/`ra2rd`**（`SimRISC-02 §寄存器组之间块赋值`）；
  - **深度与溢出状态就在 `ra0`**：`[53:48] = RACNT`（RegRAS 有效条目数 0–63）、`[47:0] = MRPTR`（MemRAS 栈顶地址，**0 = 未启用 MemRAS**）；`ra1–ra63` = 每条（递归计数 + 返回地址），**`ra63` 恒为栈顶**；有效性判据 = `RACNT`（不看条目值）。
- ⇒ **`setjmp/longjmp` 可软件完整实现**：保存/恢复 `ra0` + `ra1..ra63`（+ callee-saved GPR + `rsp`）即可恢复"深度 + 条目" ✓。
- **唯一限制**：`MRPTR != 0`（启用 **MemRAS** 溢出区）时，`longjmp` 后的新 `call` 可能覆盖 MemRAS 中"恢复所需但未弹出"的条目 ⇒ 该情形需连 **MemRAS 内容**一并保存（复杂）⇒ **本任务只做 `MRPTR == 0`（纯 RegRAS，≤63 深度）路径**，并**显式登记该限制**；**实测** M7 运行环境（`Machine-01`/bootrom）**是否启用 MemRAS**（预期未启用）。

## 接口规范

- **输出**：
  1. **真实现 `libc/machine/dadao/setjmp.S`**（`components/picolibc/patches/**`）：
     - **`setjmp`**：保存 **callee-saved 寄存器集合**（按 `contract-abi`/`ADR-0018` 的 ABI 约定，现场核**哪些 GPR/FP 寄存器跨调用保留**）+ **`rsp`** + **`ra0`**（含 `RACNT`/`MRPTR`）+ **`ra1..ra63`**（**优先用块赋值 `ldm.o`/`ra2rd`**，否则逐条 `ld.o`）；返回 0；
     - **`longjmp`**：**反向恢复**（含写回 `ra0` 的 `RACNT`/`MRPTR` 与 `ra1..ra63`）+ 按 C 语义**令 `setjmp` 返回非 0 值**（`val`，`val==0` ⇒ 1）；
     - **`sigsetjmp`/`siglongjmp`**（若 picolibc 需要）同法或按现场。
  2. **更正桩注释**：删除"ISA 无指令"错误陈述，改为**如实**写明 RA 存取依据（`contract-isa §1.3.4`）+ **`MRPTR != 0` 的限制与登记**。
  3. **重建 picolibc**（`make build-picolibc`）+ 全量 test：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ 解锁清单（预期 1 条：`test-setjmp`）。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-068t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**用 ISA 现成手段**（`ld.o`/`st.o`/`ldm.o`/`stm.o`/`rd2ra`/`ra2rd`），不自造；**不改** `spec/`、`contracts/`、`tests/vectors/`、LLVM 侧；**计数不写死**。

## 验收标准

1. **语义正确（重点，非抽样）**：自建最小用例（**调用深度 ≥3**、跨函数 `longjmp`、循环内 `setjmp`、`val=0/非0`）**真跑 rc=0**，且**证明顺序返回**（`longjmp` 后 `ret` 沿**原调用链**正确返回——用「各层返回后打印/退出码」类证据）。
2. **深度恢复可证**：构造"`setjmp` 前深度 D，`longjmp` 时深度 D+k"的用例，核恢复后**不再有多余条目**（可另用 `ra0` 的 `RACNT` 读回核对）。
3. **`test-setjmp`**：真跑 **rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
4. **桩注释已更正**：`grep` 证明错误陈述**已不存在**，新注释**引 `contract-isa`/`SimRISC-01/02`** 依据。
5. **限制已登记**：`MRPTR != 0`（MemRAS）限制写入完成区「遗留」；**实测** M7 环境 `MRPTR` 状态（读 `ra0`）。
6. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
7. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
8. **反例可失败**：注入（**去掉 RA 恢复** / 只恢复部分条目）⇒ 用例 **FAIL/错乱**（可达 FAIL）⇒ `cp`+md5 还原 ⇒ 回绿。
9. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-068t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/picolibc` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/picolibc/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
