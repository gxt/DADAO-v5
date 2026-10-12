> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/llvm/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# LLVM-070t — `-O2` 误编译致死循环：根因诊断报告（G6 / ISS-180）

> 判据：`-O2` 产物在 QEMU 下 `GUEST_EXIT=124`（超时）而 `-O0`/`-O1` `exit=0`。

## 1. 现象与最小复现

- 最小复现：`.work/source/embench-iot/src/matmult-int/matmult-int.c` 仅把
  `LOCAL_SCALE_FACTOR 39` 改 `3`（副本 `/tmp/opencode/TESTCASES-039t/red/mm.c`）。
- `-O2` 死循环（QEMU 输出仅 `[board:init]`，无 `[board:start]`）；`-O0`/`-O1` **exit=0**。
- 现场：`/tmp/opencode/LLVM-070t/red/`（`mm.elf` = `-O2`；`mm_O0.elf`/`mm_O1.elf`）。
- 证据：`.work/log/llvm/LLVM-070t-e2e-O2.log`（修复后 4 例 exit=0）。

## 2. 定位过程（逐层收窄）

1. **执行轨迹**（`qemu -d exec,nochain`）：死循环在 `memcpy`（ELF `0x1474`/`0x1488`）
   反复自转；`benchmark_body` 每次迭代都重新调用 `memcpy` ⇒ 是 **`benchmark_body` 的
   循环不退出**，不是 `memcpy` 本身（`memcpy` 是 `-O0` 编译，各优化级相同）。
2. **IR 隔离**：`clang -O2 -emit-llvm` 的 IR 语义正确（循环控制正确）；
   把该 IR 用 `llc -O0/-O1/-O2` 再编译**均死循环** ⇒ 与 llc 优化级无关（IR 已足够）。
3. **尺寸二分**：把 `UPPERLIMIT` 从 20 降到 18 ⇒ **exit=0**（终止）；19/20 ⇒ 死循环。
   二分发现差异是 **`Test()`→`Multiply()` 是否被内联 + 内层循环是否被完全展开**：
   - `-O2 -mllvm -unroll-threshold=0`（禁展开）⇒ **exit=0**；
   - 删除 IR 中的展开乘法块（`for.cond1.preheader.i.i`…`for.inc9.i.i`）⇒ 终止（exit=1）。
4. **反汇编对比**（`llvm-objdump -d`）：`benchmark_body` 的 gsf/lsf 循环控制指令
   （`cmp`/`br.eq`/`add.si`）在 `-O1` 与 `-O2` **逐字节相同**，且循环计数器
   （`rd32`=gsf、`rd33`=lsf、`rd35`=lsf_cnt、`rd36`=gsf_cnt）**未被内联乘法触碰**、
   所有分支目标均落在指令边界 ⇒ 循环控制本身正确。⇒ 退出测试**确实通过**。
5. **判定环在调用者**：`qemu -d exec,nochain` 的 PC 序列显示
   `benchmark_body`（epilogue `0x978`）→ **`0x4e0`（= `benchmark_body` 入口）** →
   `memcpy`。即 `benchmark_body` 返回到了**它自己的入口**，被反复重入。
6. **根因**：`warm_caches` 的 IR 是 `tail call fastcc void @benchmark_body(1, %heat)`，
   反汇编为
   ```
   warm_caches:
     ... save rbfp, set rbfp ...
     set.zw rd16, wp0, 0x1
     call [rb0, 4]        ; call benchmark_body
     <函数结束，无 ret>
   ```
   `call` 在 RegRAS（`ra63`）压入**返回地址 = `call` 的下一条指令 = benchmark_body 入口**；
   `benchmark_body` 的 `ret` 弹回该地址 ⇒ **无限自重入**（`-O2`）/ 直至参数被 clobber 后
   偶然退出（`-O1`，故 `-O1` 侥幸在 ~4.9s 终止）。
   ⇒ **根因 = DADAO 后端未处理尾调用**：`tail call` 被当作普通 `call` 发射，且调用者
   因 `IsTailCall` 为真**不再发射 `ret`**（`SelectionDAGBuilder` 在 `CLI.IsTailCall` 时
   跳过返回 lowering），二者叠加产生静默错码。DADAO 无尾调用指令（`contract-abi §2.3`：
   `call` 恒压栈），故属**后端能力边界**。

## 3. 差异证据

| 观测 | `-O0`/`-O1`（正常） | `-O2`（死循环） |
|---|---|---|
| `warm_caches` 反汇编 | 与 `-O2` **相同**（尾调用形态） | `call` + 无 `ret` |
| `benchmark_body` 循环控制 | 同 | 同（逐字节相同） |
| `benchmark_body` 返回目标 | 正常返回调用者 | 返回自身入口（`0x4e0`） |
| 去掉 IR `tail` 标记 | — | **exit=0**（`warm_caches` 变 `call`+`ret`） |

- 关键对照实验：`sed 's/tail call/call/g' mm_O2.ll; llc -O0` ⇒ `warm_caches` 出现
  `call` + `ld.o` + `ret` ⇒ **exit=0**。
- 反例最小程序（`/tmp/opencode/LLVM-070t/red/tc2.c`）：
  `void h(int x){ g(x); }`（`g` noinline）⇒ `h` 发射 `call g; <无 ret>` ⇒
  `main→h→g→main` 死循环。

## 4. 修复

`DADAOTargetLowering::LowerCall`（`DADAOISelLowering.cpp`）开头：
```cpp
if (CLI.IsTailCall) {
  if (CLI.CB && CLI.CB->isMustTailCall())
    report_fatal_error("DADAO: 'musttail' calls are not supported ...");
  CLI.IsTailCall = false;
}
```
- 依 `TargetLowering::CallLoweringInfo::IsTailCall` 文档（"should be modified by
  implementations of LowerCall"）清零 ⇒ 调用者发射普通 `call` + `ret`（**正确代码**，
  仅放弃尚不支持的尾调用优化）。
- `musttail` 不可合法降级 ⇒ `report_fatal_error`（**显式失败**，不静默错码）。

## 5. 验证（真实输出见 `.work/log/llvm/LLVM-070t-evidence.log`）

- 4 基准 `-O2`：`huffbench`/`matmult-int`/`nettle-sha256`/`statemate` **exit=0**。
- `-O0` 首验收集 10 例 **exit=0**（不下降）。
- `make check` / `make check-patch-tree` / `make check-lit`（78/77/1）/ `make build-mc` **EXIT=0**。
- 一键证据脚本 `.work/evidence/LLVM-070t/run.sh`：`fail=0 detected=1`，`EVIDENCE_EXIT=0`；
  注入（`if (CLI.IsTailCall)`→`if (false)`）⇒ `llc` 重建后尾调用复现、断言 FAIL
  （`inject-detected`）⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿。
