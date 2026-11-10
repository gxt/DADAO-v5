<!-- 现场生成，勿手改 -->
# M13 riscv-tests 移植与 qemu/gem5 差分

> 本册数值由 `m13-integ-004` 证据脚本现场汇总（`run_riscv_tests.py --json`）；重跑后只更新数值，不手改。

- **生成时间**：2026-11-10（本地，UTC+8）
- **数据来源**：`m13-integ-004`；上游 `riscv-software-src/riscv-tests` commit `0494f954`；逐例结果摘要 `refs/m13-004-riscv-tests.json`；原始逐例 JSON 在运行期目录，不入库
- **机器指纹**：AMD EPYC 7773X；QEMU 11.1.1；gem5 25.1.0.1；`llvm-mc` md5 `3ffcfd00…`；`gem5.opt` md5 `e2e2f9d7…`
- **复现**：`python3 tools/testcases/riscv_tests/verify_cases.py`；`python3 tools/testcases/riscv_tests/run_riscv_tests.py`；门控见 §6

## 1. 结论

- 移植了 riscv-tests 的裸机框架（启动、退出、签名区、`tohost` 等价物，见 §2），并在 DADAO 上跑通 **35 个可移植文件 / 474 条值用例**。
- **qemu 与 gem5 两平台 35/35 文件 `AGREE_PASS`**：退出码均为 0，逐例签名区逐字节一致；差异条目 **0**。
- 114 个上游 RV64 文件全部逐条归类：**移植 35 / 需改 57 / 不适用 22**（逐条名字见 §3，理由与 DADAO 映射在 `tests/riscv-tests/inventory.yaml`）。
- chipyard 列本任务记 **`N/A`**：核实现（`m12-chipyard-008/009/010/011–015`）仍待开始，本任务不伪造该列结果。

## 2. 框架映射

- **启动**：生成的 `_start` 放在 Tiny profile 的 RAM 入口；BootROM 设好 SP 后跳入。测试体不建栈、不依赖 C 运行时（对应 `RVTEST_CODE_BEGIN`）。
- **退出 / `tohost` 等价物**：semihosting `SYS_EXIT`（`trap cfx0, 0x3FF00`，参数块 `{ADP_Stopped_ApplicationExit, code}`）。`code=0` 为 PASS，`0x40 | (首个失败 testnum & 0x3F)` 为 FAIL（`spec/Machine-v5 §7.1`、`ADR-0020 D8`）。
- **签名区**：每条检查把观测值写入 `ENTRY + 0x4000 + 8*i`；结尾把整区按 16 进制逐行打印到 semihosting 控制台（等价 `begin_signature`/`end_signature`），宿主逐行与上游期望比对。
- **检查点**：只移植架构可见的值用例（`TEST_RR_OP` / `TEST_IMM_OP` / `TEST_SRL` / `TEST_SRLI`）。上游 `BYPASS`、`SRC*_EQ_DEST`、`ZERODEST` 测的是 RISC-V 微架构旁路与 `x0` 别名，不是 ISA 可见结果，未移植。

## 3. 移植清单（114 条，逐条列名）

### 3.1 移植（35）

- `rv64ui`（28）：`add addi addiw addw and andi or ori sll slli slliw sllw slt slti sltiu sltu sra srai sraiw sraw srl srli srliw srlw sub subw xor xori`
- `rv64um`（7）：`div divu mul mulh mulhu rem remu`

### 3.2 需改（57）

- `rv64ui`（24）：`auipc beq bge bgeu blt bltu bne fence_i jal jalr lb lbu ld lh lhu lui lw lwu ma_data sb sd sh simple sw`
- `rv64um`（6）：`divuw divw mulhsu mulw remuw remw`
- `rv64ua`（1）：`lrsc`
- `rv64uf`（11）：`fadd fclass fcmp fcvt fcvt_w fdiv fmadd fmin ldst move recoding`
- `rv64ud`（12）：`fadd fclass fcmp fcvt fcvt_w fdiv fmadd fmin ldst move recoding structural`
- `rv64si`（3）：`sbreak scall wfi`

归因：分支/跳转用 RB 目标与 RAS 链接模型，访存地址在 RB、数据/结果在 RD，立即数走 `set.zw`/`or.w` 的 wyde-position，无 `lui/auipc`；浮点按 `contract-fp` 的 ft/fo 寄存器与 `rf0` 标志重写；32 位乘除余需显式扩展/边界派生；LR/SC 与 trap 的观察通道与 RISC-V 不同。逐条理由见 `inventory.yaml`。

### 3.3 不适用（22）

- `rv64ua`（18）：`amoadd_d amoadd_w amoand_d amoand_w amomax_d amomax_w amomaxu_d amomaxu_w amomin_d amomin_w amominu_d amominu_w amoor_d amoor_w amoswap_d amoswap_w amoxor_d amoxor_w`
- `rv64si`（4）：`csr dirty icache-alias ma_fetch`

归因：DADAO 无 AMO 指令族（用 LR/SC 循环模拟会成为另一个测试）；无 CSR / S-mode / I-cache 别名 / 非对齐取指模型。

## 4. 两平台差分

- 口径：同一 Tiny profile、同一 raw image；QEMU system 与 gem5 FS 均启用 semihosting；比较 **host 退出码 + 签名区逐行内容**，不比较时序/日志。
- 结果：`rv64ui` 28 文件 / 414 例、`rv64um` 7 文件 / 60 例，全部 `AGREE_PASS`；`DIFF` 0、`AGREE_FAIL` 0、单平台失败 0。
- 逐例结果摘要（文件级状态、退出码、签名是否一致）见 `refs/m13-004-riscv-tests.json`；原始逐例 JSON 与引擎日志在运行期目录，不入库。

## 5. chipyard 列 `N/A` 的依据

`m12-chipyard-008`（访存）、`009`（控制流/RAS）、`010`（位操作/原子）、`011`–`015`（FP）在 `milestones-m12.md` 的「待开始」表中；核尚未具备可运行实现，chipyard 列没有可观察对象。依据任务书 §范围调整（2026-11-10）记 `N/A`，不填伪值；待核就绪后由后续任务补列。

## 6. 门控与证据

- L1：`make check` 的两个新增面（`check-test-reports`、`check-tests-index`）与 `check-no-residue`、`check-generator-sync` 均 PASS；全量 `make check` 仍红 3 项，均为 master 同红的外部项：`check-patch-tree`（共享 gem5/chipyard 源码树的未合入改动）、`check-knowledge-refs`（他任务任务书里的具体运行期路径引用）、`check-temp-dirs`（他任务超龄临时目录）。
- L2：`make check-modules` 在本 worktree 因 `check-arch-smoke → install-host` 触发全量 LLVM 构建而无法在验收时限内完成（构建树已清理，未占共享安装根），记为 BLOCKED；本任务改动不触及 L2 门控载体（`tests/inst`、`tests/unit`、`tests/tset`）。
- 功能验收：35 文件 × 2 引擎的差分（§4）+ 独立语义 oracle（§7）。
- 一键证据：运行期证据目录的 `run.sh`，含「正常→绿、guest/host 注入→红、再正常→绿」自检；任一项失败即非零退出（本次 20 项断言全 PASS）。
- 独立 oracle：`verify_cases.py` 不 import 生成器，用独立的 RISC-V 语义模型复算 474 条期望值，并 `--inject` 证明可失败。

## 7. 限制与后续

- 只移植值语义；旁路/寄存器别名类宏未移植（原因是微架构而非 ISA）。
- `rv64um` 的 32 位乘除余（`mulw/divw/divuw/remw/remuw`）与 `mulhsu` 留在「需改」：需先按 DADAO 契约补边界派生，不在本轮猜测。
- FP（`rv64uf`/`rv64ud`）与原子（`rv64ua`）需按 `contract-fp` 与 LR/SC 语义重写，建议由 M13 后续差分任务承接。
- chipyard 列待核实现完成后补齐。
