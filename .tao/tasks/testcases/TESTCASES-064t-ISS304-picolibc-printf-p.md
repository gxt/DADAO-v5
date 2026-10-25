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

### 输出（**方案 A 已定**，用户 2026-10-25「选A」）

**根因（已核，高置信）**：
- picolibc `libc/stdio/vfprintf_int.c:62` 的 `%p` 设 `FL_LONG` 后走 `arg_to_unsigned` ⇒ `va_arg(ap, unsigned long)`；
- DADAO 调用约定把**指针参数放 RB 组**（`CCIfPtr` 在 `CCIfType<[i64]>` 之前），整数放 RD 组；`va_list` 七字段按 bank 分光标（`LowerVASTART`，`DADAO-21 §3.3`）；
- 调用侧 `(void*)57` 进 RB，picolibc 侧按 `unsigned long` 读 RD ⇒ **读错 bank**（实测 0x8/0x3），其余 276 条断言走 RD 整数路径故全过；
- 这是 C 的 UB：`%p` 参数类型是 `void*`，库却按整数取。

**实施**：
1. 给 picolibc 端口打补丁：`%p` 改为 `va_arg(ap, void *)`，再转 `uintptr_t` 打印（调用侧/取参侧同为指针类 RB）；
2. 重建 picolibc，跑 `make check-picolibc-tests-full`：两例转绿、其余不回归；
3. 反例：撤补丁 ⇒ 复现 `0x8`/`0x3` ⇒ 还原 ⇒ 绿；
4. 关闭 `ISS-304`（`resolved_by = TESTCASES-064t`）。

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
