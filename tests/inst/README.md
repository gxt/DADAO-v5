# inst scope — 指令级测试用例（`tests/inst/`）

本目录是 **inst scope**（`docs/Process-09` §3）：单指令/短序列执行语义的**源码用例**，
另含 `atomics/clmul/fma/minmax/roundint` 探针源。向量是 LLVM/QEMU/gem5 的**独立 oracle**。

> `TESTCASES-072t`（2026-10-27）从 `tests/vectors/` 与 `tests/{atomics,clmul,fma,minmax,roundint}/`
> 迁入；执行 harness 在 `tools/testcases/{lib,inst}/`。

- 向量**独立派生自锁定的规范与合约**（`spec/`、`.tao/contracts/contract-isa.md`、
  `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、
  `.tao/adr/adr-0004-test-machine.md`），**不从 LLVM 汇编输出或 QEMU 运行结果生成**。
- 每条向量记录输入状态、编码字、期望输出状态/PC/异常，期望值可回溯到 `spec_cite`。
- 覆盖率主键为 `id`（对应 `contracts/opcodes.yaml` 的 `id`，**唯一**）；`format` 为普通字段，不入主键。M1 scope 以
  `contracts/opcodes.yaml` 中 `scope == "m1"` 为唯一判据（**156 条**）。

## 文件

| 文件 | 说明 |
|------|------|
| `schema.md` | 向量 YAML 字段规范（含 `expected_pc`、class 定义、encoding 豁免、deferred 规则） |
| `inventory.md` | M1 覆盖矩阵（以 `id` 为行，含 `format`/`file` 列与 deferred reason） |
| `base/*.yaml` | 向量数据（由 `TESTCASES-003t`~`007t` 生成） |
| `MIGRATION.md` | YAML → 汇编+宏 的迁移台账（大类/小类/用例模板/任务拆分/删除规则） |
| `macros/inst_test.inc` | 汇编宏层（`TEST_LD*`/`TEST_ST*`/`TEST_FAULT`/`__CHECK_*`，期望值内联） |
| `01-load-store/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（单元素 `ld.*`/`st.*`，19 个） |
| `01-load-store/inst-tiny.lds` | 上面这册的链接布局（固定段地址 + ASSERT 钉住） |

## 汇编载体（M13 起）

用户 2026-11-12 裁定：YAML 不可读、转汇编易错 ⇒ **汇编 + 宏**，期望值内联。
一行一个用例，失败即 `SYS_EXIT(检查点号)`（`0x01`–`0x7F`）；机器异常例单独成像，
退出码 = monitor 段编码（`0xF0|异常位索引`）。格式、宏签名与两种镜像形态见
`MIGRATION.md §2`；跑法：

```
python3 tools/testcases/inst/run_asm_suite.py --id ld.o_rrii_rd   # 单个 id
python3 tools/testcases/inst/run_asm_suite.py                     # 全册
```

判据 = **同一份 ELF** 在 chipyard `WumingTinyConfig` / QEMU `dadao-tiny` / gem5 FS
`tiny` 上，链例的结果字节流逐字节一致、故障例的退出码一致。

## 校验

```
python3 tools/testcases/validate_vectors.py   # 或 make check（L1）
```

校验 schema 字段、class/fault 取值、编码 mask/value、`expected_pc`、`inventory`
同步与覆盖率；有错误时 `exit(1)` 并列出文件 + case 序号。
