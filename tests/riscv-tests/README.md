# `tests/riscv-tests/` — riscv-tests 的 DADAO 移植语料（M13）

> 来源：`riscv-software-src/riscv-tests`，commit `0494f954a3d8d2ca9e4972da7a01e94b6a909bce`
> （chipyard 工具链锁定的检出；上游 BSD 许可）。本目录只保存**派生的分类/用例数据**，不复制上游源码。
> 任务：`m13-integ-004`；报告：`docs/TestReports/M13-riscv-tests移植与差分.md`。

## 目录

| 路径 | 内容 |
| --- | --- |
| `upstream-index.yaml` | RV64 ISA 六套件（`rv64ui/um/ua/uf/ud/si`）114 个源文件 + sha256（可追溯） |
| `inventory.yaml` | 逐文件分类：`port`（可移植）/ `rewrite`（需改）/ `na`（不适用）+ 理由 + DADAO 映射 |
| `cases/<suite>/<name>.yaml` | 35 个 `port` 文件抽取出的架构可见值用例（474 条） |
| `framework/dadao_test.inc` | 裸机框架宏（启动、签名区、退出方式见下） |

## 框架映射（riscv-tests → DADAO）

- **启动**：`_start` 位于 Tiny profile 的 RAM 入口；BootROM 设置 SP 后跳入，测试不建栈、不依赖 C 运行时（对应 `RVTEST_CODE_BEGIN`）。
- **签名区**：每条检查把观测值写到 `ENTRY + 0x4000 + 8*i`；结尾把整个签名区按 16 进制逐行打印到 semihosting 控制台（对应 `begin_signature`/`end_signature`）。
- **`tohost` 等价物**：semihosting `SYS_EXIT`（`trap cfx0, 0x3FF00`），退出码 `0` = PASS、`0x40 | (首个失败 testnum & 0x3F)` = FAIL（`spec/Machine-v5 §7.1`、`ADR-0020 D8`）。
- **检查**：每条用例把 DADAO 结果与上游期望值比较；首个失败被记录，签名区保留实际值供宿主比对。

## 用例范围

只抽取**架构可见的值用例**：`TEST_RR_OP`、`TEST_IMM_OP`、`TEST_SRL`、`TEST_SRLI`。
上游的 `BYPASS` / `SRC*_EQ_DEST` / `ZERODEST` 宏测试的是 RISC-V 微架构旁路与 `x0`
别名，不是 ISA 可见结果；DADAO 的 `rd0` 目的还触发 ILLI，故不移植（见每个
case 文件的 `note`）。

## 复现

```sh
# 结构 + 独立语义 oracle（不需要上游检出）
python3 tools/testcases/riscv_tests/verify_cases.py

# qemu 与 gem5 两平台差分（Tiny profile；35 个 port 文件）
python3 tools/testcases/riscv_tests/run_riscv_tests.py

# 刷新（需要 riscv-tests 检出；RISCV_TESTS_DIR=...）
python3 tools/testcases/riscv_tests/extract.py --upstream "$RISCV_TESTS_DIR"
python3 tools/testcases/riscv_tests/extract.py --upstream "$RISCV_TESTS_DIR" --check
```

chipyard 列在本任务记 `N/A`：核实现（`m12-chipyard-008`/`009`/`010`/`011`–`015`）
仍待开始，尚无可运行核。
