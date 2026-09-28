# SPEC-013t: 存档 0.5.3 文档

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范
- 输入：`spec/SimRISC-00-指令系统设计.md`、`spec/SimRISC-01-数据类指令.md`、`spec/SimRISC-02-地址类指令.md`、`spec/SimRISC-03-浮点类指令.md`、`spec/SimRISC-04-系统类指令.md`
- 输出：`spec/SimRISC-0.5.3/` 目录下的 5 个文件副本
- 约束：
  1. 文件内容必须与原件完全一致，包括版本号
  2. 原件保留在原位（不删除），供后续任务参考
  3. 归档目录使用 `spec/SimRISC-0.5.3/`（与主目录平级）

## 验收标准
1. `spec/SimRISC-0.5.3/` 目录存在，包含 5 个文件
2. 每个文件内容与原件一致（用 `diff` 逐文件验证）
3. 文件版本号仍为 0.5.3
4. 原件 `spec/SimRISC-00~04` 仍在原位

## 完成区

**测试结果**：通过 5/5；diff 逐文件验证全部 identical，版本号 0.5.3 确认
**修改文件**：新建 `spec/SimRISC-0.5.3/` 目录及 5 个副本文件（无既有文件被修改）
**验收结果**：
```
=== diff verification ===
[OK] SimRISC-00-指令系统设计.md identical
[OK] SimRISC-01-数据类指令.md identical
[OK] SimRISC-02-地址类指令.md identical
[OK] SimRISC-03-浮点类指令.md identical
[OK] SimRISC-04-系统类指令.md identical

=== originals still present ===
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-01-数据类指令.md
spec/SimRISC-02-地址类指令.md
spec/SimRISC-03-浮点类指令.md
spec/SimRISC-04-系统类指令.md

=== archive contents ===
SimRISC-00-指令系统设计.md
SimRISC-01-数据类指令.md
SimRISC-02-地址类指令.md
SimRISC-03-浮点类指令.md
SimRISC-04-系统类指令.md

=== version check ===
spec/SimRISC-0.5.3/SimRISC-00-指令系统设计.md:> **版本：0.5.3**
spec/SimRISC-0.5.3/SimRISC-01-数据类指令.md:> **版本：0.5.3**（与 SimRISC-00 一致）
spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md:> **版本：0.5.3**（与 SimRISC-00 一致）
spec/SimRISC-0.5.3/SimRISC-03-浮点类指令.md:> **版本：0.5.3**（与 SimRISC-00 一致）
spec/SimRISC-0.5.3/SimRISC-04-系统类指令.md:> **版本：0.5.3**（与 SimRISC-00 一致）
```
**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审
- 任务性质：纯文件复制，无代码改动
- diff 验证：5/5 文件 identical，无差异
- 版本号：5 个归档文件头部均标注 `0.5.3`
- 原件确认：`spec/SimRISC-00~04` 5 个原件均在原位
- 判决：**PASS**，无需修复

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

#### 第 1 轮 reviewer 验收

**审查范围**：`spec/SimRISC-0.5.3/` 目录及其 5 个副本、`spec/SimRISC-00~04` 原件。

**重跑记录（reviewer 独立执行）**

1. 归档目录与文件数：
```
$ ls -1 spec/SimRISC-0.5.3/ | wc -l
5
（内容：SimRISC-00-指令系统设计.md / 01-数据类指令.md / 02-地址类指令.md / 03-浮点类指令.md / 04-系统类指令.md）
```
2. 逐文件 diff（归档 vs 原件）：
```
$ diff -q "SimRISC-0.5.3/$f" "$f"   # 对 5 个文件逐一执行
[OK] SimRISC-00-指令系统设计.md identical
[OK] SimRISC-01-数据类指令.md identical
[OK] SimRISC-02-地址类指令.md identical
[OK] SimRISC-03-浮点类指令.md identical
[OK] SimRISC-04-系统类指令.md identical
diff_total_rc=0
```
3. 原件仍在原位：
```
[OK] spec/SimRISC-00-指令系统设计.md present
[OK] spec/SimRISC-01-数据类指令.md present
[OK] spec/SimRISC-02-地址类指令.md present
[OK] spec/SimRISC-03-浮点类指令.md present
[OK] spec/SimRISC-04-系统类指令.md present
```
4. 版本号（`grep -n -m1 "版本"`）：
```
SimRISC-0.5.3/SimRISC-00-指令系统设计.md:3:> **版本：0.5.3**
SimRISC-0.5.3/SimRISC-01-数据类指令.md:3:> **版本：0.5.3**（与 SimRISC-00 一致）
SimRISC-0.5.3/SimRISC-02-地址类指令.md:3:> **版本：0.5.3**（与 SimRISC-00 一致）
SimRISC-0.5.3/SimRISC-03-浮点类指令.md:3:> **版本：0.5.3**（与 SimRISC-00 一致）
SimRISC-0.5.3/SimRISC-04-系统类指令.md:3:> **版本：0.5.3**（与 SimRISC-00 一致）
```
5. 反例注入（随机选 `SimRISC-02-地址类指令.md`，改第 5 行后 diff）：
```
$ sed -i '5s/.*/INJECTED COUNTEREXAMPLE LINE/' SimRISC-0.5.3/SimRISC-02-地址类指令.md
$ diff SimRISC-0.5.3/SimRISC-02-地址类指令.md SimRISC-02-地址类指令.md
5c5
< INJECTED COUNTEREXAMPLE LINE
---
> > **rb0 为目的寄存器约定**：rb0 = PC（只读），任何指令以 rb0 为显式目的时触发 **ILLI** 异常。
diff_rc=1
```
→ 验证方法能检测差异（`diff_rc=1`）。还原（`cp 原件 副本`）后复验：
```
$ diff -q SimRISC-0.5.3/SimRISC-02-地址类指令.md SimRISC-02-地址类指令.md; echo post_restore_diff_rc=$?
post_restore_diff_rc=0
md5：db8b00000ec29390e3dee2428670eb9c（与注入前一致）
```
6. 工作区未被污染：
```
$ git status --porcelain spec/
?? spec/SimRISC-0.5.3/
```
仅新增归档目录（未跟踪），**原件无任何修改**；反例注入已完全还原（md5 与注入前相同），无残留。

**约束核验（逐条）**

| # | 约束 | 结论 |
|---|------|------|
| 1 | 文件内容必须与原件完全一致，包括版本号 | ✅ 5/5 diff identical，版本号均 0.5.3 |
| 2 | 原件保留在原位（不删除） | ✅ 5 个原件均在，`git status` 无删除/修改 |
| 3 | 归档目录使用 `spec/SimRISC-0.5.3/`（与主目录平级） | ✅ 目录位置与命名正确，恰含 5 个文件 |

**验收标准核验**

1. 目录存在，含 5 个文件 → ✅（count=5）
2. 每文件与原件一致（diff） → ✅（全部 identical，rc=0）
3. 版本号仍为 0.5.3 → ✅（5/5）
4. 原件 SimRISC-00~04 仍在原位 → ✅

**判决**：**Accepted**

- 所有验收命令在 reviewer 独立重跑下全部通过（退出码均为 0）。
- 反例注入验证确认 diff 方法具备检测能力（注入后 `diff_rc=1`），且注入已完整还原（md5 一致、git status 无残留）。
- 三条硬约束无任何违反。工程师完成区的转述与 reviewer 真实输出逐条一致。