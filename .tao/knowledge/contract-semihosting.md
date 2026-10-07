# semihosting 合约（M5）

> **版本：0.7.1** [DADAO-22 §1. 调用约定][DADAO-12 §1. 运行模式与核芯功能扩展]
>
> **来源**：决策 `.tao/adr/adr-0020-see-semihosting.md`（`ADR-0020`，Accepted，`D1`–`D8`/`D14`）；规范正文 `spec/Machine-01-测试机运行环境.md §5`（v5 自定）；调用约定引用 `spec/DADAO-22-SBI-主管系统二进制接口.md`（0.7.1）、`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）；服务号值语义取自 Arm Semihosting（`Semihosting for AArch32 and AArch64`）。
>
> **范围**：v5 测试机 semihosting——入口判定（tag）、调用约定、完整 25 服务表、返回机制、停机（`SYS_EXIT`）、已知风险。SEE/HEE 运行环境见 `contract-see.md`。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` 标注 spec/ 来源；v5 架构自定义/测试机约定标 `[ADR-0020 DN]`/`[Machine-01 §N]`；不写行号。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 `ADR-0020`/`Machine-01` 冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。

---

## §1 入口判定

- `trap cfxHA, immu18` 中 **`immu18[17:16] == 2'b11`** ⇒ 该 `trap` 为 **semihosting 调用**（**与 `cfxha` 无关**）。[ADR-0020 D1][Machine-01 §5.1]
- 该 tag 判定**无上游 spec 依据、属架构自定义**：`DADAO-22` 只定义 `cfxha`=服务提供者、`immu18`=功能编号，`SimRISC-11 §陷入指令` 只定义 `immu18`=功能编号，二者均无 semihosting 语义。[ADR-0020 D1][DADAO-22 §1. 调用约定][SimRISC-11 §陷入指令]
- **两条路**：`== 2'b11` 走 semihosting 短路；`≠ 2'b11` 走一般 trap 进入 cfx 向量。不得把 semihosting 混入向量路径。[ADR-0020 D10][Machine-01 §4]

## §2 调用约定

- 寄存器映射：操作号（标量）→ `rd16`（= `rda0`）；参数块指针（地址）→ `rb16`（= `rba0`）；返回值 → `rd31`。[ADR-0020 D2][ADR-0020 D14][Machine-01 §5.2]
- **不另设 `rd15`**：`rd15` 是 `umon`/`jmon` 系统调用号，semihosting 不使用。[ADR-0020 D2][DADAO-21 §系统调用规范]
- 传参复用 ABI 约定（数据参数 `rd16–rd31`、地址参数 `rb16–rb31`，三组独立计数）。[DADAO-22 §1. 调用约定][DADAO-21 §参数寄存器：Parameter registers]
- 恒 **64 位**、**大端**（同 `ADR-0003 D1`）；参数块字段为 **64 位**。[ADR-0020 D6]
- 共享层取参位序映射：`n=0 → rd16`、`n=1 → rb16`；返回写 `rd31`。[ADR-0020 D14][Machine-01 §5.2]

## §3 服务表（完整 25 个）

服务集 = **完整 25 个**，号值采用 **Arm Semihosting 号值**；本表即为「服务号值↔入参/出参」的权威表。[ADR-0020 D3]

- 「参数块」= `rb16` 指向的 64 位字段块；「无参数」= 参数寄存器须为 0。
- 各服务的语义与字段布局遵循 Arm Semihosting（`Semihosting for AArch32 and AArch64`，`Release 2.0`）。[ADR-0020 D3]

| 号值 | 名称 | 功能 | 入参 / 返回 |
|------|------|------|-------------|
| `0x01` | `SYS_OPEN` | 打开宿主文件 | 参数块〔文件名指针, 打开模式, 文件名长度〕；返回句柄，失败 `−1` |
| `0x02` | `SYS_CLOSE` | 关闭文件 | 参数块〔句柄〕；返回 `0` 成功 / `−1` 失败 |
| `0x03` | `SYS_WRITEC` | 写单个字符 | 参数寄存器 = 字符指针；无返回 |
| `0x04` | `SYS_WRITE0` | 写以 0 结尾字符串 | 参数寄存器 = 字符串指针；无返回 |
| `0x05` | `SYS_WRITE` | 写缓冲区到文件 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未写字节数 |
| `0x06` | `SYS_READ` | 从文件读入缓冲区 | 参数块〔句柄, 缓冲区指针, 字节数〕；返回未填字节数 |
| `0x07` | `SYS_READC` | 读控制台字符 | 无参数；返回读到的字节 |
| `0x08` | `SYS_ISERROR` | 判断错误状态 | 参数块〔状态字〕；返回 `0`（非错误）/ 非 `0` |
| `0x09` | `SYS_ISTTY` | 判断交互设备 | 参数块〔句柄〕；返回 `1`/`0` |
| `0x0a` | `SYS_SEEK` | 文件定位 | 参数块〔句柄, 绝对字节位置〕；返回 `0` / 负值 |
| `0x0c` | `SYS_FLEN` | 文件长度 | 参数块〔句柄〕；返回长度 / `−1` |
| `0x0d` | `SYS_TMPNAM` | 取临时文件名 | 参数块〔缓冲区指针, 标识符, 缓冲区长度〕；返回 `0` / `−1` |
| `0x0e` | `SYS_REMOVE` | 删除文件 | 参数块〔路径名指针, 长度〕；返回 `0` / 非 `0` |
| `0x0f` | `SYS_RENAME` | 重命名文件 | 参数块〔旧名指针, 旧名长度, 新名指针, 新名长度〕；返回 `0` / 非 `0` |
| `0x10` | `SYS_CLOCK` | 自启动起百分秒 | 无参数；返回百分秒数 / `−1` |
| `0x11` | `SYS_TIME` | 自 1970-01-01 起的秒 | 无参数；返回秒数（按无符号解释） |
| `0x12` | `SYS_SYSTEM` | 执行宿主命令 | 参数块〔命令串指针, 长度〕；返回状态（见 §6） |
| `0x13` | `SYS_ERRNO` | 取宿主 errno | 无参数；返回宿主 `errno` |
| `0x15` | `SYS_GET_CMDLINE` | 取命令行 | 参数块〔缓冲区指针, 缓冲区长度〕；返回 `0` / `−1` |
| `0x16` | `SYS_HEAPINFO` | 取堆/栈参数 | 参数块〔heap_base, heap_limit, stack_base, stack_limit〕 |
| `0x18` | `SYS_EXIT` | 报告退出 | 64 位：参数块〔原因码, 子码〕；不返回（见 §5） |
| `0x19` | `SYS_SYNCCACHE` | 同步 Cache | 无参数；Cache 一致性同步 |
| `0x20` | `SYS_EXIT_EXTENDED` | 报告退出（带退出码） | 参数块〔原因码, 退出码〕；不返回（见 §5） |
| `0x30` | `SYS_ELAPSED` | 已流逝的 target ticks | 64 位：参数块〔64 位 ticks〕；返回 `0` / `−1` |
| `0x31` | `SYS_TICKFREQ` | tick 频率 | 无参数；返回 ticks/秒 / `−1` |

- `SYS_SYNCCACHE (0x19)` 在 Arm Semihosting `Release 2.0` 中列为保留号；v5 沿用共享层既有号值并纳入服务集。[ADR-0020 D3]

## §4 返回机制

- semihosting **无 `escape` 指令**：服务完成后由实现层直接**前移 PC**（`pc += 4`）并写回返回寄存器 `rd31`；guest 侧不需 `escape`。[ADR-0020 D4][Machine-01 §5.4]
- 该机制与一般 trap 的 `escape cfxha, [excp_cause_ip, 4]` 返回不同（semihosting 不进入向量）。[ADR-0020 D4][DADAO-22 §1. 调用约定]

## §5 停机（`SYS_EXIT` 取代 exit port）

- **`SYS_EXIT`（`0x18`）/`SYS_EXIT_EXTENDED`（`0x20`）取代 exit port**（`ADR-0004 D3`）作为停机协议。[ADR-0020 D8][ADR-0004 R2]
- 常规退出使用原因码 `ADP_Stopped_ApplicationExit`（`0x20026`）；退出码须忠实传播到 host `$?`（沿用 `ADR-0011` 的确定性 halt）。[ADR-0020 D8]
- **迁移范围 = 全部**（M1–M4 依赖 exit port 的向量/harness 全迁 `SYS_EXIT`）；迁移完成前 exit port 过渡保留。[ADR-0020 D8][ADR-0020 D15]

## §6 已知风险

- `SYS_SYSTEM`（`0x12`，执行宿主命令）为**已登记的已知安全风险**；v5 **不因此拒服务**（服务集 = 完整 25 个），以默认 `gdb`/沙箱、`native` 显式开启为缓解。[ADR-0020 D3][ADR-0020 D7][Machine-01 §5.6]

---

## 附录 A：来源对照

| 本合约 § | 内容 | 来源 |
|----------|------|------|
| §1 | 入口 tag 判定 / 架构自定义说明 / 两条路 | `ADR-0020 D1`/`D10`；`Machine-01 §5.1`/`§4`；`DADAO-22 §1. 调用约定`；`SimRISC-11 §陷入指令` |
| §2 | 传参/返回寄存器（rd16/rb16/rd31）、64 位大端 | `ADR-0020 D2`/`D6`/`D14`；`Machine-01 §5.2`；`DADAO-21 §参数寄存器：Parameter registers`；`DADAO-22 §1. 调用约定` |
| §3 | 完整 25 服务表（号值 = Arm 号值） | `ADR-0020 D3`；`Machine-01 §5.3`；Arm Semihosting（Release 2.0） |
| §4 | 无 `escape`、PC 步进返回 | `ADR-0020 D4`；`Machine-01 §5.4` |
| §5 | `SYS_EXIT` 取代 exit port | `ADR-0020 D8`；`ADR-0004 R2`；`Machine-01 §5.5` |
| §6 | `SYS_SYSTEM` 已知风险 | `ADR-0020 D3`/`D7`；`Machine-01 §5.6` |
