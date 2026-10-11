# TESTCASES-042t: picolibc 自带 test 接入（100% 验收）

**模块**：testcases
**项目里程碑**：M7
**依赖**：`INFRA-057t`（picolibc 移植/构建集成）、`QEMU-056t`（RAM 基址）、`LLVM-079t`（P0 后端）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #2`）：**picolibc test 验收 = 100%**（原话「**要求 100%**」）；test 重心 = **picolibc 自带 test**。
  - 组件：`.work/source/picolibc`（tag `1.8.12` @`2ae376c6`，patch 后 = base+1）；自带 test 资产（实测）：`test/` 下 `.c` 342 个 + **2 个 `.cpp`**，分 `libc-testsuite/(10)`、`semihost/(32)`、`test-ctype/(5)`、`test-libdl/(4)`、`test-math/(68)`、`test-posix/(19)`、`test-stdio/(32)`、`test-stdlib/(10)`、`test-string/(18)`、`testsuite/(109)`、top-level/(33) 等。
  - 现行 harness：`tools/testcases/**`、`tests/**`；semihosting 执行口径 `contract-semihosting.md`（`SYS_EXIT`/`SYS_WRITE`/`SYS_GET_CMDLINE` 等）。
  - 排除项（`INTEG-033k §排除项`）：动态链接（`test-libdl`）、pk/linux-user/多线程——**不适用项须显式登记为 excluded，不静默跳过**。
- **输出**：
  1. picolibc 自带 test 的**编/链/跑 harness**（落 `tools/testcases/**`，**入库**）：驱动 picolibc 构建系统（meson）或最小等价流程，把适用 test 编成 ELF/镜像、在 `qemu-system-dadao -machine dadao-m1` + semihosting 下运行。
  2. **分层门控**：快档（代表集）入 `make check` 或专项 target、全量档 opt-in（对齐 `Process-05 §2`/M6 分层；**不写死计数**，现场统计）。
  3. **100% 报告**：适用测试集**逐条结果**（pass/fail/excluded），fail=0（除显式 excluded）。
- **约束**：
  - **前置（`LLVM-080t` 整改，2026-10-12）**：**恢复 picolibc `libm`（删 `INFRA-057t` 源过滤表并重建）**——sysroot `libm.a` 现为空壳（876 B，仅 `empty.c.o`）；`nm` 复核 8 符号：`floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`/`fmin`/`fmax`（P0/P1 已由 `LLVM-079t`/`LLVM-080t` 收口）。`ISS-188`。
  - **独立 oracle**：期望值**不得**从 QEMU/`llc` 反推（`AGENTS.md`「Independent oracle」）；test 自身断言为准。
  - **不适用项 = 显式 excluded + 理由**（如动态链接）；**不得**以 skip 掩盖。
  - **依赖未就绪不降级**（同 `TESTCASES-039t` 教训）：阻塞时保留现场、登记，不伪造通过。
  - **计数不写死**；只动任务范围（`tools/testcases/**`/`tests/**`/`Makefile` 内本任务 target），越界须披露。

## 验收标准

1. **可跑**：一条命令可编/链/跑适用 picolibc test（真实输出 + 退出码）。
2. **100%**：**适用测试集 100% pass**（逐条结果表；fail=0）；excluded 项**逐条显式登记 + 理由**（现场统计：pass / fail / excluded 三个数）。
3. **语义正确**：至少 3 类（`libc-testsuite`/`semihost`/`test-math` 或 `test-string`）实跑通过（真实输出）。
4. **门控**：`make check`（+ M7 专项 target）EXIT=0；`check-no-residue` EXIT=0。
5. **反例门控**：harness **能失败**（注入错误期望值 或 改坏一条 test ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
