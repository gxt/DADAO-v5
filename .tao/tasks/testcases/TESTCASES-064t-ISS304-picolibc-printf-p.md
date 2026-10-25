# TESTCASES-064t: picolibc `%p` 用例判定与处置（ISS-304）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（picolibc full 档）

## 接口规范

### 背景（ISS-304，实测 2026-10-20）
- picolibc full 档：`test-printf` / `test-printf-int` 各 1 例 FAIL；失败断言仅 `test 277` / `test 278`（源 `.work/source/picolibc/test/test-stdio/test-printf-testcases.h:277-278`），两条均 `"%p"`，实参 `(void *)57ULL` / `(void *)57U`，期望 `"0x39"`；实测 `"0x8"`（3 字符）/ `"0x3"`，带宽度对照同形。
- 已排除 `hash_page.c` 过滤改动（A/B 同一 `.o` 输出逐字节相同）。

### 输出（**判定优先**）
1. **复现**：`make check-picolibc-tests-full`（或等价最小命令）取两例真实输出。
2. **判定**（给出证据链，三选一）：
   - **本项目缺陷**（picolibc 端口/`vfprintf`/指针打印路径的 DADAO 行为）⇒ 修，写明根因与改动；
   - **上游期望值/口径问题** ⇒ 留宿主对照（同版本 picolibc on x86-64）+ 上游源码/issue 依据，给出关闭理由；
   - **其它 libc/工具链问题** ⇒ 转登记对应模块，本册给复现与归因。
3. 不擅自改上游测试期望；若判上游 bug，须有上游依据。

### 约束
- 不因两例失败放松 picolibc 全量判据；不改 `spec/`。
- 判定结论与证据写完成区（命令 + 输出 + 退出码）。

## 验收标准
1. 复现命令与真实输出（含 `test 277/278` 期望/实得）。
2. 判定证据链完整（源码行 + 对照/上游）。
3. 若修：picolibc full 档转绿（贴计数）；若判非缺陷：`issues.yaml` 关闭依据充分。
4. L1 / L2 绿。
5. 完成区贴真实输出。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
