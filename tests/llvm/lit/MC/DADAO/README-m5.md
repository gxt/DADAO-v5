# M5 L1/L3 向量对照表（`tests/llvm/lit/MC/DADAO/` + `tests/llvm/codegen/m5/`）

> 任务：`TESTCASES-033t`（SEE/HEE + semihosting 向量：L1 MC 编码/往返 + L3 执行；独立 oracle）。
> 规范：`spec/Process-05-里程碑TDD规范.md §2`（L1/L2/L3）、`§3`（一能力一向量）、
> `§4`（期望值**独立派生**）、`§5`（反例门控）、`§6`（落点）。
> 契约：`contracts/opcodes.yaml`（L1 期望编码）、`.tao/knowledge/contract-see.md`（cfx 权限）、
> `.tao/knowledge/contract-semihosting.md`（服务表/调用约定/停机）、
> `spec/Machine-01-测试机运行环境.md`。决策：`.tao/adr/adr-0020-see-semihosting.md`、
> `adr-0004`（`R1`/`R3`）。

## 1. L1 MC 向量（编码/往返）— 复用 `LLVM-060t` 产物

M5 的 L1 向量由**前置的 `LLVM-060t` 自带并已接入 `make check-lit`**（`spec/Process-05` 分阶段），
本任务**复用**，不再引入重复文件（DRY）：

| 向量文件 | 能力 | 期望值来源（独立派生） |
|---|---|---|
| `cfx2-trap-escape.s` | `trap` / `escape`（ciii）+ `cfx2rd` / `cfx2rc`（crrr）的编码与**往返**；`cfx_<name>`/`cfxHA` 等价；`cfx_<cfxname>_<regname>` 简写展开；数组寄存器单下标 | `contracts/opcodes.yaml`（`value`/`mask`/`fields`，行内 `; @enc` + `; OBJ:` 双写）+ `.tao/knowledge/contract-cfx-aliases.md`（别名） |
| `cfx2-trap-escape-err.s` | 反例：`escape` 偏移 `%4!=0`/越界/非常量、非 `excp_cause_ip` 基址、`trap` 立即数越界、`cfx2rd` 裸数字/无下标/越界下标 → **硬报错（非零退出）** | `spec/Toolchain-01 §3.2` + `contracts/opcodes.yaml` |

- 独立 oracle：`tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（从 `opcodes.yaml` + 别名表
  **独立派生** `@enc`，与行内期望比对；**不调用** `llvm-mc`）。
- 门控：`make check-lit`（62/62，含上两条；`main` 目标在 `Makefile` 中由 `INTEG-016t` 接入）。
- 编码（`contracts/opcodes.yaml`）：`trap` op `0x7F`、`escape` op `0x7E`、`cfx2rd` op `0x7A`、
  `cfx2rc` op `0x7B`，均 `mask=0xFF000000`；`crrr` 字段 `cfxha[23:18] cghb[17:12] rchc[11:6] rdhd[5:0]`，
  `ciii` 字段 `cfxha[23:18] imm18[17:0]`。

## 2. L3 执行向量（`tests/llvm/codegen/m5/`）— 向量 ↔ 能力 ↔ 期望值来源

承载形态 = **bin**（用户 2026-10-08 M5 范围简化裁定）：`llvm-mc` → `llvm-objcopy -O binary` →
`-kernel` 载入旧 RAM 基址 `0xffff_0000_0000`（`ADR-0004 D2.3` path B）→ **SEE bootrom**（`-bios`）
在**复位 PC `0xffff_ffff_0000`** 启动、配置 cfx 向量/掩码后 **hypv→user** 跳应用
（`QEMU-047t` / `Machine-01 §2`）。**不经** `ld.lld` 多 TU ELF（ELF 加载归 M6，`ISS-168`）。

| 向量文件 | 类别 | 能力 | 期望值来源（独立派生） |
|---|---|---|---|
| `m5_semi_writec.s` | semihosting | `SYS_WRITEC`(0x03)：写 rb16 处单字符到 semihosting 控制台 | `contract-semihosting §3`（服务表）+ 向量数据字节 `0x41` → 控制台 `"A"` |
| `m5_semi_write0.s` | semihosting | `SYS_WRITE0`(0x04)：写 rb16 处 NUL 结尾串 | `contract-semihosting §3` + 数据字节 `4f 4b 0a 00` → 控制台 `"OK\n"` |
| `m5_semi_write.s` | semihosting | `SYS_OPEN`(0x01, mode 4) + `SYS_WRITE`(0x05)：写宿主文件 | `contract-semihosting §3` + 缓冲字节 `57 58 59 5a` → 文件 `m5_write.txt="WXYZ"` |
| `m5_semi_exit.s` | semihosting | `SYS_EXIT`(0x18)：`{0x20026, code}` 停机、码传 host `$?` | `contract-semihosting §5`（`ADR-0020 D8`）→ `$?=0x43` |
| `m5_semi_exit_extended.s` | semihosting | `SYS_EXIT_EXTENDED`(0x20)：带显式退出码停机 | `contract-semihosting §3/§5` → `$?=0x44` |
| `m5_perm_reserved_illi.s` | permission | 一般 `trap cfx7`（reserved cfxha）⇒ `ILLI` | `contract-see §3`（reserved 7–14/19–61 ⇒ ILLI；`DADAO-12 §5`）→ cause `ILLI`(1<<8)，pass token `0x50` |
| `m5_perm_mask_illi.s` | permission | 一般 `trap cfx_jmon`（指令类型 mask 禁止）⇒ `ILLI` | `contract-see §3`（mask 禁止 ⇒ ILLI；`DADAO-12 §3`）→ `ILLI`，pass token `0x51` |
| `m5_perm_unimpl_cfxreg.s` | permission | `trap cfx_ptw`（未实现 cfx）⇒ `CFXREG` | `contract-see §3`（未实现 cfx ⇒ CFXREG；`DADAO-22 §3`）→ `CFXREG`(1<<2)，pass token `0x52` |
| `m5_perm_badcombo_cfxreg.s` | permission | `cfx2rd cfx_umon, cg6, rc63`（超数量寄存器组合）⇒ `CFXREG` | `contract-see §3`（不存在组合 ⇒ CFXREG；`DADAO-12 §3` `rc≥scratch_regs_num`）→ `CFXREG`，pass token `0x53` |
| `m5_trap_escape.s` | trap | 一般 `trap cfx_umon, 0x0123` 进向量 + bootrom handler `escape` 返回 | `contract-see §4`（cause `CFXTRAP`；`DADAO-12 §5`）→ cause `CFXTRAP`(1)、`escape_num==1`，pass token `0x60` |

**权限反例口径（`ADR-0020 D9`）**：M5 **无 PTBR 权限层** ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`
（`DADAO-12 §2.2`）**不在 M5**；本任务权限反例一律为 **cfx 级**（`ILLI`/`CFXREG`）。
`ILLI`/`CFXREG`/`CFXTRAP` 为 `DADAO-12 §4` monitor 异常原因表的一位（`CID`）。

### 2.1 L3 实际 qemu 命令行

逐例一致（`run_m5_e2e.py` 逐例打印真实命令）：

```
.dadao/cross-toolchain/bin/qemu-system-dadao \
    -M dadao-m1 \
    -bios .dadao/tests/bootrom/bootrom.bin \
    -kernel <work-dir>/<vector>.bin \
    -semihosting-config enable=on,target=native,chardev=semi \
    -chardev file,id=semi,path=<work-dir>/<vector>.console \
    -display none -nographic \
    -d cpu -D <work-dir>/<vector>.cpu.log
```

- `<bootrom.bin>` = `QEMU-047t` 产物 `.dadao/tests/bootrom/bootrom.bin`，经
  `tools/infra/paths.py::test_artifacts_dir()` 解析（**禁硬编码**）。
- `<vector>.bin` 由**自有工具链** `llvm-mc` + `llvm-objcopy -O binary --only-section=.text` 产生。
- `-chardev file,...` + `chardev=semi`：把 semihosting 控制台（`WRITEC`/`WRITE0`）落到文件供
  比对（`target=native` 无 chardev 时输出到 stderr，不可直接判定）。
- `-d cpu -D <log>`：`run_m5_e2e.py` 用它核 **复位 PC**（首块 `PC: 0000ffffffff0000`）+
  **bootrom 生效**（`CFX00 M0 ... VEC:0000ffffffff0200`）+ **应用在 user 模式**（`MODE: 0`）。
- **`-bios` 必需**：flat bin 无独立入口，复位 PC = ROM 基址；bootrom 完成模式/向量/栈初始化后
  hypv→user 跳应用（`Machine-01 §2`）⇒ 无 `-bios` 则应用不执行。

### 2.2 独立 oracle 与驱动

- 独立 oracle：`tools/testcases/validate_m5_vectors.py` —— 从 `.tao/knowledge/contract-semihosting.md §3`
  （服务表）与 `contract-see.md §3`（cfx 权限规则）**独立派生**每个向量的期望（服务号/名称、
  控制台字节、cause id、pass/fail token），并与 `expected.yaml`、向量 `; @m5` 头部、向量源文本
  **三方交叉核对**；**不调用** `llvm-mc`/`llvm-objcopy`/QEMU（无子进程导入）。
- 驱动：`tools/integ/run_m5_e2e.py`（本任务内直接 `python3` 调用；`Makefile`/`make test-semihost`
  接线归 `INTEG-020t`）。逐例输出「名字/期望/实际/退出码」；`--inject` 提供反例自检。

### 2.3 反例门控（可失败性）

`tools/testcases/validate_m5_vectors.py` 可对以下注入**失败**（见
`.work/evidence/TESTCASES-033t/run.sh`）：

1. 改一条期望退出码（`expected.yaml` 或向量 `exit=` 头）⇒ `FAIL`；
2. 改一条**服务号**（向量 `set.zw rd16, wp0, 0x00NN` 与 `@m5 service=` 不一致）⇒ `FAIL`；
3. 改一条**权限期望码**（向量 `set.zw rd12, wp0, 0x00NN` 与 `rule=` 派生的 cause 不一致）⇒ `FAIL`；
4. 改一条服务名 / 控制台数据字节 / cause 名 ⇒ `FAIL`。

`run_m5_e2e.py --inject` 另在内存中翻转一条期望退出码并跑通「FAIL ⇒ 还原 ⇒ 回绿」。
