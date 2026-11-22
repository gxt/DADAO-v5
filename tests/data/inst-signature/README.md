# inst-signature — `tests/inst` 签名区「槽 → 期望值」表（m17-testcases-001）

本目录是 **L2 `check-idl`** 的入库期望数据：把 `tests/inst/**/*.S` 里每个
检查点的**内联期望常量**（以及 `WDATA` 数据区的独立 oracle）派生为
「镜像 × 槽 → 期望值」，供各方签名流**逐槽**比对（每方都对本表比对），失败时能报
「槽 N 期望 0x… 实际 0x…（来源 `.S:行`）」。

> 原独立门控 `make check-inst-sig` 已退役（`m17-testcases-003`，`check-idl` 是其超集）；
> **生成用 `make inst-signature-data`，执行判据见 `check-idl`**。

## 文件

| 文件 | 内容 |
|---|---|
| `expected.tsv` | 逐槽期望（`image / slot / kind / expected / expr / source` 六列；生成物，勿手改） |
| `inputs.sha256` | 派生读到的**全部输入**（`.S` + 宏层 `.inc` + 链接布局 `.lds`）的 sha256（`sha256sum -c` 格式） |

`kind` 口径：

- `value` —— `__CHECK_RD/__CHECK_MEM` 的 `exp` 是 `.S` 内联常量（符号按宏层 `.equ` 与链接布局求值）；
- `table` —— `_MEM` 变体的期望从 `.testdata` 的 `WDATA` 表装载（独立 oracle：期望来自数据区字面量，不经被测指令）；
- `relation` —— 期望是**运行期关系**（如 IP 读数「两次读回相等」、rf0 自比），没有静态常量；`check-idl` 的逐槽比对**不比对取值**（语义由 `.S` 内 `br.eq` 承担；写入口存在性由静态派生保证）；
- `unwritten` —— `__NCHECK` 记了该检查点，但源码没有 `SIGUPD` 写入口（删 `SIGUPD` 即出现）⇒ `check-idl` 报「槽 N 未写」。

## 生成命令（一行）

```sh
make inst-signature-data
```

数据漂移（`.S` 改了未重生成）由 `python3 tools/testcases/inst/check_inst_sig.py --data-only`
点名第一条漂移行；输入 sha256 不符亦 FAIL。**执行判据**不在本目录脚本，而在 L2
`check-idl`（每方槽值对本表逐槽 + 互比）。

## 输入清单

`inputs.sha256` 由生成命令现场写出（`tests/inst/*/*.S`、各册 `<册>.inc`、
`tests/inst/macros/inst_test.inc`、`tests/shared/asm/signature.inc`、
`tests/shared/asm/machine*.inc`、`tests/ee-tiny/tests_inst_tiny.lds`）。核对：

```sh
cd "$(git rev-parse --show-toplevel)" && sha256sum -c tests/data/inst-signature/inputs.sha256
```

## 为什么可以入库

- 纯文本、按镜像/槽排序、逐行带来源 `文件:行` ⇒ 变更可在 diff 里逐条审阅；
- **不含任何实测值**：期望来自 `.S` 内联常量（spec 派生、已复核）与 `WDATA` 数据区字面量，
  不从 QEMU/LLVM 输出反推；QEMU 流只用于比对（`tests/shared/signature.py`）；
- 无法静态定值的 `relation` 槽显式标 `-`（不冻结实测值当 golden）。

**数据不可入库的原因**：无 —— 本表是纯文本、可按上面的生成命令现场重算（判据 = **可复核**：
输入 sha256 + 生成命令 + `expected.tsv` 逐行来源）。若将来出现只能靠二进制/专用变换才能复现的
内容，应另存 `tests/data/` 并在本节登记原因。

## 判定细节

- `tests/inst` 的签名区**不预填** `0xdeadbeef`（不用 `SIG_BEGIN`：预填会改指令流，
  M16 周期基线不允许），且合法期望本身可为 `0x00000000deadbeef`（08 册 `rol.t` 两例）
  ⇒ 解析按 `signature.py` 的 inst 口径 `sentinel=False`；「漏跑」由上面的 `unwritten`
  **静态派生**判定，不靠哨兵猜。
- 旧 `check_inst_sig.py` 的**诊断路径**（不带参数时运行；不是门控）在正常镜像判红时另用
  `-defsym SIG_CONTINUE=1` 编译一份诊断镜像（判红点不退出）取完整流做逐槽定位；
  未定义该宏时 `.text` 与旧版逐字节相同。
