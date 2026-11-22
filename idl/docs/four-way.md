# IDL 四方差分口径（`m17-idl-005`）

> **定位**：M17 四方差分（IDL / QEMU / gem5 / chipyard）的判据、平台集与用例清单
> 机制。驱动 = `idl/tools/idl_four_way.py`；门控 = `make check-idl`（L2）。
> **不做 ISA 语义**：语义仍以 `spec/SimRISC-*` + `idl/*.idl` 为准；本文只定义
> 「同一份 ELF 在四方之间比较什么、怎么比」。

## 1. 判据

一个镜像（`tests/inst/<册>/<id>.S` 编译成**同一份 ELF**）的四方判据：

1. **签名槽流逐槽全等**：每方把收尾结果缓冲按 8 字节/槽输出（`tests/shared/asm/signature.inc`），
   host 侧用 `tests/shared/signature.py`（`m16-testcases-005` 起的唯一一份；任务背景里
   的 `tools/testcases/lib/signature.py` 是迁移前旧路径）的 `parse(..., sentinel=False)`
   （inst 口径）切成「链例检查点数」个槽，四方逐槽相等；
2. **退出码全等**：IDL 的 guest `SYS_EXIT` 码（`idl_exec.py --state-out` 的
   `exit_code`）与三方进程退出码相等；
3. **每方对独立 oracle**：每方槽值再与 `tests/data/inst-signature/expected.tsv`
   （由 `.S` 内联常量 / `WDATA` 数据区派生）逐槽比对（`kind=value/table`）；
   `kind=relation` 无数值（运行期关系由 guest 断言），`kind=unwritten` 判红。
   四方一致但**全错**时仍红——**期望不从实测反推**。

逐指令 trace 不参与判据（红后归因用 `idl/tools/idl_check_trace.py`，
`idl/docs/trace-format.md`）。

## 2. 平台集

- IDL 是固定一方；`--platforms` 选另外三方：
  - **L2 / 主控机**：默认 `qemu` ⇒ **IDL + QEMU**，不依赖 gem5/Verilator 构建；
  - **节点 / 收口**：`--platforms qemu,gem5,chipyard` ⇒ 全四方。
- 任一选中平台缺可执行文件/固件 ⇒ **ERROR（rc=2）**，不静默跳过。
- 构建与三方启动**复用** `tests/ee-tiny/run_inst_tiny.py` 的既有路径（同一套
  LLVM 汇编/链接、QEMU `-bios/-kernel`、gem5 FS、chipyard `+loadmem`）；
  签名取流/解析复用 `tests/shared/signature.py`（`capture`/`parse`/`compare`），
  不新建第二套。

## 3. IDL 侧签名流：`SYS_WRITE` 不可用

`SIG_DUMP` 的收尾路径是「先 `SYS_WRITE`（handle 1）块写，未写完再 `SYS_WRITEC`
逐字节回退」（`tests/shared/asm/signature.inc`）。IDL 执行器**不提供块写通道**：

- `SYS_WRITE` 按「不可用」处理：读参数块 `{handle, buf, nbytes}`，
  `rd8 = nbytes`（`contract-semihosting §3` 的「未写字节数」= 全部未写），
  `rd8_defined = true`；
- guest 的 `SIG_DUMP` 据此走 `SYS_WRITEC` 逐字节回退，字节写进执行器既有的
  `output` 观测面（`--image-out` 落盘）；
- 因此 IDL 与 QEMU/gem5 的实测路径一致：本任务的 `tests/inst` 载体本身用
  `SIG_DUMP_CHARS`（纯逐字节），两条路径的字节流相同。

`tests/inst` 的镜像**不预填**哨兵，合法槽值本身可为 `0x00000000deadbeef`；
解析统一 `sentinel=False`，「漏跑」由 `expected.tsv` 的 `kind=unwritten` 静态判。

## 4. 用例清单机制

`idl/data/idl_exec_cases.toml`：

- `[[case]]` = **主清单**（进 `make check-idl`）：`image`（相对仓库根的 `.S`）+
  `category`；
- `[[pending]]` = 阶段一收口后**必须为空**（段缺失或空数组）——能力缺口另立任务，
  不得用 `pending` 静默降低覆盖（`m17-idl-010` 加硬断言）。

门控在 `check_four_way.py` 内**现场派生**并断言：

```
{[[case]].image} == {tests/inst/*/*.S} − {07-floating-point} − {[[pending]].image}
```

即「主清单集合 == 现场派生集合减去 pending」；`pending` 非空 ⇒ rc=2（文案「pending
必须为空」），不再接受「一致地把一条移进 pending」。集合按 glob 现场统计，不写死
镜像数；FP 册（`07-floating-point`）属阶段二，不在本口径内。

## 5. 用法与退出码

```
python3 idl/tools/idl_four_way.py                                   # IDL + QEMU（L2）
python3 idl/tools/idl_four_way.py --platforms qemu,gem5,chipyard    # 全四方
python3 idl/tools/idl_four_way.py --only ld.o_rrii_rd               # 单例诊断
make check-idl                                                         # L2 门控
```

退出码：`0` = 全部一致；`1` = 有 FAIL；`2` = setup/清单/输入错误；
`75` = 共享构建树有活跃写者（`writer-guard` 拒绝，见 `docs/Process-07 §2.1`）。
