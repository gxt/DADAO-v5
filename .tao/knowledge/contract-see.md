# SEE/HEE 运行环境合约（M5）

> **版本：0.7.1** [DADAO-12 §1. 运行模式与核芯功能扩展][DADAO-22 §1. 调用约定]
>
> **来源**：`spec/DADAO-12-SEE-主管系统运行环境.md`（0.7.1）、`spec/DADAO-13-HEE-超管系统运行环境.md`（0.1.2）、`spec/DADAO-22-SBI-主管系统二进制接口.md`（0.7.1）、`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）、`spec/SimRISC-11-其它.md`（0.5.4）；测试机运行环境正文 `spec/Machine-01-测试机运行环境.md`（v5 自定）；决策 `.tao/adr/adr-0020-see-semihosting.md`（`ADR-0020`，Accepted）与 `.tao/adr/adr-0004-test-machine.md`（`ADR-0004`，Accepted，rev. 2026-10-07 `R1`/`R3`）。
>
> **范围**：M5 SEE/HEE 运行环境——运行模式、核内地址空间与复位、cfx 与权限、`trap`/`escape` 与异常进入/退出、SBI 调用约定。semihosting 的服务表/调用约定见 `contract-semihosting.md`。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]`/`[SimRISC-XX §章节名]` 标注 spec/ 来源；测试机约定标 `[ADR-0020 DN]`/`[ADR-0004 DN]`/`[Machine-01 §N]`；不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。

---

## §1 运行模式

- DADAO 定义四种运行模式（两位编码）：`user`（`0b00`）、`jail`（`0b01`）、`supv`（`0b10`）、`hypv`（`0b11`）。[DADAO-12 §1. 运行模式与核芯功能扩展]
- `hypv`（超管模式）的 cg3 寄存器定义见 HEE（含 `hypv_switch_run_mode`/`hypv_excp_vector`）。[DADAO-13 §1. cg3 - hypv mode 寄存器]
- `trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst` 可在**任意运行模式**下执行；是否允许由 cfx mask 与指令类型 cfx mask 控制。[SimRISC-11 §特权指令]
- 异常进入时运行模式/掩码切换为 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 与 `switch_cfx_mask`（异常进入流程步骤 8）。[DADAO-12 §5. 异常进入与异常退出][DADAO-12 §3. 共有寄存器设计规范]
- v5 测试机只启用 `hypv`/`user`，**本版不启用 `supv`**、不涉及 `smon`。[ADR-0020 D12][ADR-0004 R1][Machine-01 §2]

## §2 核内地址空间与复位

- CPU 内部地址总线固定 48 位；48 位核内地址高 6 位 `bits[47:42]` 指定 cfxha。[DADAO-12 §2.1 核内地址空间]
- 硬件复位启动地址 = `cfx_power_hypv_excp_vector = 0xffff_ffff_0000`（cfxha 63 / `power`，64 KiB），可由 CPU 直接取指执行。[DADAO-12 §2.1 核内地址空间]
- v5 测试机地址划分（RAM@0 / 旧 RAM 段过渡保留 / exit port 过渡保留 / boot ROM）为**测试机约定**；RAM 基址改全 0，复位向量/ROM 与 exit port 不变。[ADR-0020 D15][ADR-0004 R3][Machine-01 §1]
- 核内地址空间非法访问触发对应 cfx 的 `CFXMEM`（`1<<1`）；测试机退出码 = `0x80 | 1 = 0x81`；`0x87`（unmapped）为测试机约定、无 spec cause。[DADAO-12 §2.1 核内地址空间][DADAO-12 §4. 专有寄存器设计规范][ADR-0004 D5.8]
- 越界**取指**与越界数据访问**同等报异常**，不得静默；fault 码表冻结不重排。[ADR-0020 D15][ADR-0004 D5.8]

## §3 cfx 与权限

- 每个 cfx 提供 cg0–cg7 共有寄存器（含 `global_cfx_mask`、指令类型 mask、`switch_run_mode`、`switch_cfx_mask`、`excp_vector`、`excp_cause_mask`）。[DADAO-12 §3. 共有寄存器设计规范]
- mask 语义：0=可触发，1=屏蔽；自身 cfxha 对应位由硬件忽略。[DADAO-12 §3. 共有寄存器设计规范]
- reserved cfxha（`7`–`14`、`19`–`61`）触发 `ILLI`；cfxha 合法但指令 cfx mask 禁止亦触发 `ILLI`。[DADAO-12 §5. 异常进入与异常退出]
- 访问**未实现**的核芯功能扩展（其 cfx 寄存器）触发 `CFXREG`。[DADAO-22 §3. 系统信息（smon）]
- `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 为 PTBR 模式权限异常（`cfx_ptw_user/jail/supv/hypv_perm` 检查）。[DADAO-12 §2.2.1 超页的地址转换][DADAO-12 §2.2.2 普通页的地址转换]
- **两层权限不可混同**：PTBR 权限（`NUPERM` 等，出自 cfx_ptw 异常原因表）与 cfx 访问权限（cfx mask 不允许 ⇒ `ILLI`）分属不同层次。[ADR-0020 D9][DADAO-12 §4. 专有寄存器设计规范]
- v5 测试机 cfx 实现范围 = `cfx0/1/2/3/63`（`umon`/`jmon`/`smon`/`hmon`/`power`），属**测试机约定**、非上游架构限制；范围外未实现 cfx 触发 `CFXREG`。[ADR-0020 D9][Machine-01 §3]

## §4 `trap`/`escape` 与异常进入/退出

- `trap cfxha, immu18`：`cfxha` 为服务提供者、`immu18` 为功能编号。[DADAO-22 §1. 调用约定]
- 一般 trap（`immu18[17:16] ≠ 2'b11`）走 `DADAO-12 §5` 异常进入流程步骤 1–10，进入目标 cfx 异常向量。[DADAO-12 §5. 异常进入与异常退出][ADR-0020 D10]
- `escape cfxha, [excp_cause_ip, imms20]` 完成异常退出；编码层 `imms18`，`Addr = excp_cause_ip + (imms18 << 2)`，`imms20` 须 `%4==0`。[DADAO-12 §异常退出流程][SimRISC-11 §退出指令]
- 被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回 trap 下一条指令。[DADAO-22 §1. 调用约定]
- **两条路分离**：semihosting（`immu18[17:16] == 2'b11`）经实现层短路、不进入向量、PC 步进返回，见 `contract-semihosting.md`；不得混入向量路径。[ADR-0020 D10][Machine-01 §4]

## §5 SBI 调用约定

- 调用方 `trap cfxha, immu18` 陷入目标 cfx；被调方经 `escape cfxha, [excp_cause_ip, 4]` 返回。[DADAO-22 §1. 调用约定]
- 参数传递与 ABI 传参规范一致（参见 `contract-abi.md`）。[DADAO-22 §1. 调用约定][DADAO-21 §传参：Parameter Passing]
- 参数寄存器：`rd16–rd31`（数据）、`rb16–rb31`（地址）、`rf16–rf31`（浮点）；三组独立计数、从 16 起递增。[DADAO-21 §参数寄存器：Parameter registers]
- 标量返回值用 `rd8`；指针返回值用 `rb8`。[DADAO-21 §标量类型返回值：Scalar type return]
- 系统调用号存于 `rd15`，与 `immu18` 为两个独立层次。[DADAO-21 §系统调用规范]
- 错误码：`0 = SBI_SUCCESS`、`−1 = SBI_ERR_FAILED`、`−2 = SBI_ERR_NOT_SUPPORTED`、`−3 = SBI_ERR_INVALID_PARAM`、`−4 = SBI_ERR_NO_DEVICE`。[DADAO-22 §1. 调用约定]

---

## 附录 A：来源对照

| 本合约 § | 内容 | spec/ 来源 |
|----------|------|-----------|
| §1 | 运行模式（四模式）、任意模式执行特权指令、switch_run_mode | `DADAO-12 §1. 运行模式与核芯功能扩展`、`§5. 异常进入与异常退出`；`DADAO-13 §1. cg3 - hypv mode 寄存器`；`SimRISC-11 §特权指令` |
| §2 | 核内地址空间 / 复位向量 / CFXMEM / 测试机划分 | `DADAO-12 §2.1 核内地址空间`、`§4. 专有寄存器设计规范`；`ADR-0020 D15`、`ADR-0004 D5.8`/`R3` |
| §3 | cfx 共有寄存器 / mask / PERM 层次 / 未实现 cfx | `DADAO-12 §3. 共有寄存器设计规范`、`§5. 异常进入与异常退出`、`§2.2.1 超页的地址转换`、`§2.2.2 普通页的地址转换`；`DADAO-22 §3. 系统信息（smon）`；`ADR-0020 D9` |
| §4 | trap/escape 路由、异常进入/退出 | `DADAO-12 §5. 异常进入与异常退出`、`§异常退出流程`；`DADAO-22 §1. 调用约定`；`SimRISC-11 §退出指令`；`ADR-0020 D10` |
| §5 | SBI 调用约定、参数/返回寄存器、错误码 | `DADAO-22 §1. 调用约定`；`DADAO-21 §参数寄存器：Parameter registers`、`§标量类型返回值：Scalar type return`、`§系统调用规范` |
