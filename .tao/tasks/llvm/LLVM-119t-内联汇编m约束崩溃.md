# LLVM-119t: 内联汇编 `"m"` 约束后端 ISel 崩溃（`ISS-197` / `ISS-222` ②）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`LLVM-118t`（同改 `components/llvm-project/**` + 各自 `install-host`，**必须串行**：共享 `.work/build/llvm` 与安装根，并发写会互相写坏——`ISS-229`）、`LLVM-086t`（`"r"` 约束先例，已归档）、`INFRA-096t`（安装根新鲜度，`待验收`）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`llvm` 现存最大 = `LLVM-117t`（本批另占 `118`/`120`）⇒ 取 **`119`**（编写前 `grep -rn 'LLVM-119' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **最小复现（`ISS-197` 原始现场 + `ISS-222` ② 再确认）**：
  ```c
  void f(void){int x;__asm__("" : "+m"(x));}
  ```
  `clang -c` ⇒ 驱动 **rc=1** + `fatal error: error in backend: Could not match memory address.  Inline asm failure!` + crash dump；`llc` ⇒ **rc=134**（SIGABRT / core）。崩溃点 = 上游 `SelectionDAGISel::SelectInlineAsmMemoryOperands` 的 `report_fatal_error`（构建树源码 `llvm/lib/CodeGen/SelectionDAG/SelectionDAGISel.cpp`，**具体行号由现场定位，勿照抄**）。
- **对照面（优雅失败）**：`"f"` 未映射 ⇒ frontend `invalid input constraint 'f' in asm`（rc=1），**无 core**。
- **既有已解锁项**：`"r"`/`"=r"`/`"+r"`/`"=&r"` 已由 `LLVM-086t` 映射到 `GPRD`（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch:558-580`）；`"i"` 走泛型。
- **真实消费者（本册动机）**：musl 默认 `GETFUNCSYM` 用 `"+m"`（`ldso/dlstart.c` 的 `GETFUNCSYM(&dls2, __dls2, …)`）；当前 DADAO 端口以 arch 特化绕开——`components/musl/patches/arch/dadao/reloc.h.patch:85-95` 注释逐字记录了该崩溃与绕行理由。**本册不要求撤除该特化**（是否回退另议）。
- **口径依据**：用户 2026-10-12 裁定 C「**只解锁，不立约定**」（`LLVM-086t`，逐字见该册第 13-14 行）⇒ 本册**不新增** `"b"`/`"f"` 等字母、**不立** `spec/Toolchain-01` 约定；只处理内存操作数约束的**可用 / 显式不可用**。
- **`ISS-222` ①（`%0` 代入空串）不属本册**，归 `LLVM-118t`。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.*`、`DADAOISelDAGToDAG.cpp`、`DADAOAsmPrinter.*`、`DADAORegisterInfo.*` 等，按诊断结果）、`components/llvm-project/patches/series`、安装根工具链、`tests/llvm/lit/**`。
- **输出**：
  1. **诊断记录**：崩溃链（IR → SelectionDAG → `SelectInlineAsmMemoryOperands` → 哪一步无可匹配的 memory operand 形态）逐环给出 `file:line`（构建树源码 + 我方补丁位置）；
  2. **实现**：使 `"m"`/`"=m"`/`"+m"`/`"=&m"` 可用（正确寻址）**或**（仅在证实本 target 结构性不可行时）显式诊断；两条路都必须消除 core；
  3. lit 用例（`tests/llvm/lit/CodeGen/DADAO/**` 或 `MC/DADAO/**`，按实际层）+ 运行时探针（`.work/evidence/<任务ID>/`）+ 证据脚本 `run.sh` + 日志 `.work/log/llvm/LLVM-119t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `tests/vectors/**`；**不改** musl 组件（`components/musl/**`）——若判断须回退 `reloc.h` 的 `GETFUNCSYM` 特化，**停下报告**；改 `components/llvm-project/**` 后 **必须** `make install-host` 再验证（长构建，按 `AGENTS.md` 申报）；不 commit/push。

## 验收标准

1. **无崩溃（硬判据）**：对下列全部形态，`clang -c` 与 `llc` 的 rc ∈ {0, 1}，**无 SIGABRT（134）、无 core**（测试时 `ulimit -c 0`，临时目录 `/tmp/opencode/LLVM-119t/`）：`"m"`、`"=m"`、`"+m"`、`"=&m"`；空 asm 与非空 asm；操作数为局部标量 / 结构体字段 / 数组元素 / 解引用指针。
2. **语义正确（若实现支持）**——独立 oracle（手算期望，不由编译器输出反推）：
   - `int x; __asm__("set.rd %0, 7" : "=m"(x));` ⇒ `x == 7`；
   - `"+m"` 读改写（如 `__asm__("add.si %0, %0, 5" : "+m"(x));`，`x` 初值 10 ⇒ 15）；
   - 结构体字段/数组元素：写字段后其余字段不被破坏（逐字节比对）；
   - 大端语义：写入 8 字节值后按大端读回（`llvm-objdump`/运行时 memcpy + 手算字节序）。
3. **真实消费面**：把 musl 默认 `GETFUNCSYM`（`"+m"` 形态）复制到**临时文件**（`/tmp/opencode/LLVM-119t/getfuncsym.c`）⇒ `clang -c` rc=0（不要求改 musl 仓）。
4. **失败面仍可达**：不能因为「都变成 rc=1」而掩盖问题——若某形态仍不支持，诊断须**指名约束与原因**（不是 `Could not match memory address` 的 fatal），且 lit/探针断言该诊断文本；不得静默降级、不得输出错码。
5. **可达 FAIL ≥ 2**（真实输出 + `cp`+md5 还原后回绿）：
   - (a) **修前现场**：`llc` rc=134 + 同一 fatal 文案（改前复现、改后消失）；
   - (b) **注入回退**：临时树回退补丁（或改坏 memory operand 匹配）⇒ 崩溃/探针红；
   - (c) **错误值注入**：把探针期望值改错（如 7→8、字段偏移错位）⇒ 探针 rc≠0。
6. **门控**：`make check`(L1) rc=0；`check-lit`（L2 子集）/ `check-instrinfo` / `check-patch-tree` / `check-lit-full`（若改 MC 表）各留 rc；`series` 与补丁数一致（`check-patch-tree` 断言）。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-197`（及 `ISS-222` ② 注记）按实况回填。
8. **不跑** `git commit`/`push`；未 `install-host` 就跑门控属无效验证（须披露）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-119t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）；core 关闭（`ulimit -c 0`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（接受「显式不支持」边界 / 改 musl 特化 / 改 `spec/`）时留问。
6. 复杂命令输出留 `.work/log/llvm/`；重建按 `AGENTS.md` 申报耗时、`JOBS=8`。
7. **`install-host` 前置**：改组件后先装再验，否则读旧安装根 = 假绿（`ISS-210`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
