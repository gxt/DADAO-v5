# INTEG-012t: CodeGen E2E 套件 + `make test-codegen`

**模块**：integ
**项目里程碑**：M3
**依赖**：`LLVM-041t`、`TESTCASES-026t`、`INFRA-035t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-041t` 的 llc/`.s`/obj/flat-binary 通路；`TESTCASES-026t` 的 `tests/codegen/*.ll` + `expected.yaml`；`tests/scripts/trampoline.bin`（`gen_trampoline.py`，`ADR-0004` 双镜像启动：`-bios trampoline -kernel test.bin`、RAM 基址 `0xffff_0000_0000`、退出码 = exit port 写入值）。
- **输出**：
  - `tests/scripts/codegen_crt0.s`（或等价）：最小启动桩 `_start`——建立/沿用 SP，`call main`，将返回值（`rd31`）写入 exit port（`0xffff_8000_0000`，地址用 `set.zw`/`or.w` 构造），`swym` 停机。**注意**：无链接器，故桩与 `llc` 产物必须合并为**单一 `.s`（单 TU 自包含）**再汇编。
  - `tools/integ/run_codegen_e2e.py`：fail-closed 驱动的 E2E 门（**非 lit 退出码**，直接比较 guest 退出码 vs `expected.yaml`）。
  - `Makefile`：新增 `test-codegen` 目标（复用 `LIT_BIN`/构建目录约定；前置 `build-mc`+`build-qemu`；任何用例不符即非零退出）。
  - `.work/log/integ/INTEG-012t-*.log`（完整命令输出）。
- **约束**：
  - **单 TU 自包含**（`ADR-0003 §D5`）：`llc` 产物 `.s` + `codegen_crt0.s` 拼接为一个 `.s`；段内标签就地解析，无跨 object 链接、无 LLD。
  - **链路固定**：`llc -march=dadao <prog.ll>` → `.s`；`cat crt0.s prog.s` → `.s`；`llvm-mc -triple=dadao -filetype=obj` → `.o`；`llvm-objcopy -O binary --only-section=.text`（+按需多段拼接）→ `.bin`；`timeout N qemu-system-dadao -M dadao-m1 -bios <trampoline> -kernel <bin> -display none -nographic` → **进程退出码 = guest 退出码**。
  - **判据**：每用例 guest 退出码 == `expected.yaml` 期望值 ⇒ PASS；不等/超时/负例（fault 码 `0x80|cause`）⇒ FAIL。逐用例打印「名字 + 期望 + 实际 + 退出码」。
  - **门槛**：`make test-codegen` 全绿；**≥1 算术 + ≥1 访存 + ≥1 分支 + ≥1 调用**函数端到端（与 `TESTCASES-026t` 覆盖矩阵一致）；并覆盖**大端窄访存**（C13/`ADR-0018（C13）`，显式核对字节偏移）与**指针算术**（C14/`ADR-0018（C14）`，`add.so-rb` base+offset / `cmp.uo-rb`）各 ≥1。
  - **反例门控**（强制）：驱动内置 `--inject` 或测试脚本注入反例（改一条期望值 / 把一个函数的操作数改错 → 预期 FAIL，再还原 → 回绿），完成区给出真实输出；**注入后须验证 `git diff --name-only` 非空且还原含重建**。
  - **不引入** LLD、不实现完整重定位；**不**扩 `contract-elf.md §2–§4`。
  - 不改 `components/**`；`Makefile` 改动与 `INFRA-035t` 串行（同改共享文件）。
  - 留证禁 `tee` 吞退出码（用 `cmd > log 2>&1; rc=$?`）；**不提交 git**。

## 验收标准

1. `make test-codegen` 退出 0；输出逐用例「名字/期望/实际/退出码」；四类函数各 ≥1 通过。
2. 至少一个用例的链路每一步真实执行（`llc`/`llvm-mc`/`llvm-objcopy`/`qemu` 均退出 0），完整命令与输出留存 `.work/log/integ/`。
3. 反例门控：注入 → 预期 FAIL（非零退出）→ 还原 → 回绿；给出真实输出与 `git` 还原证据（含重建）。
4. 不回归 `make check-lit`（MC+E2E 31/31）。
5. `make check-no-residue` / `git status --untracked-files=all` 干净（除本任务应有改动）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
