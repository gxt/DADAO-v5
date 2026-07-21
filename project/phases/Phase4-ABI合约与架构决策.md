# Phase 4：ABI 合约与架构决策

> 对应 DADAO-0628 的 DL-002a（ABI contract）+ DL-003a（ELF ABI ADR）+ DL-004a（ELF contract）

## 目标

从 DADAO-v5/wiki 的 ABI、AEE、SBI 规范文档中提取并创建机器可读的 ABI 合约、ELF 合约和关键的架构决策记录（ADR）。这是 LLVM CodeGen 和工具链的基础。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| DADAO-v5/wiki | `SimRISC-00-指令系统设计.md` | 数据表示、寄存器模型、存储模型 |
| DADAO-v5/wiki | `DADAO-11-AEE-应用程序运行环境.md` | 不同宽度数据的运算处理、地址空间布局、汇编兼容性 |
| DADAO-v5/wiki | `DADAO-21-ABI-应用程序二进制接口.md` | 寄存器规范、传参规则、栈布局、返回值 |
| DADAO-v5/wiki | `DADAO-22-SBI-主管系统二进制接口.md` | 系统调用约定 |
| DADAO-v5/wiki | `DADAO-23-HBI-超管系统二进制接口.md` | HBI 调用约定 |
| DADAO-0628 | `contracts/abi/spec.md` | ABI 合约模板（注意是 0.1.0，需升级到 0.9.2） |
| DADAO-0628 | `contracts/abi/README.md` | ABI 说明 |
| DADAO-0628 | `contracts/elf/spec.md` | ELF 合约模板 |
| DADAO-0628 | `verif/abi.yaml` | ABI 事实模板 |
| DADAO-0628 | `docs/adr/0003-object-abi.md` | 对象 ABI ADR |

## 输出文件

```
DADAO-v5/
├── contracts/
│   ├── abi/
│   │   ├── spec.md              # ABI 规范合约（版本 0.9.2）
│   │   └── README.md            # ABI 说明
│   ├── elf/
│   │   ├── spec.md              # ELF/对象 ABI 合约（EM_DADAO=0x0DA0）
│   │   └── README.md            # ELF 说明
│   ├── sbi/
│   │   ├── spec.md              # SBI 规范合约（版本 0.7.1）
│   │   └── README.md            # SBI 说明
├── verif/
│   ├── abi.yaml                 # 机器可读 ABI 事实
│   └── sbi.yaml                 # 机器可读 SBI 函数表
├── docs/adr/
│   ├── 0003-object-abi.md       # 对象/ELF ABI 决策记录
│   └── 0004-test-machine.md     # M1 裸机测试机决策记录
```

## 子代理分解

### Agent E1：ABI 规范合约

**职责**：创建 `contracts/abi/spec.md` + `verif/abi.yaml`

**提示词**：
```
你是 DADAO-v5 的 ABI 工程师。从 wiki 的 ABI 和 AEE 规范创建 ABI 合约。

读取输入文件：
- DADAO-v5/wiki/DADAO-11-AEE-应用程序运行环境.md
- DADAO-v5/wiki/DADAO-21-ABI-应用程序二进制接口.md
- DADAO-0628/contracts/abi/spec.md（参考，注意版本差异）
- DADAO-0628/tools/abi.yaml（参考）

1. 创建 `contracts/abi/spec.md`：

基于 DADAO-v5/wiki/DADAO-21-ABI 的内容，创建结构清晰的规范合约：

§1 寄存器角色与约定
- RD bank：rd0=zero, rd1=rderrno, rd2-7=reserved, rd8-15=temp, rd16-31=参数, rd32-63=callee-saved
- RB bank：rb0=rbip, rb1=rbsp, rb2=rbfp, rb3=rbgp, rb4=rbtp, rb5-7=reserved, rb8-15=temp, rb16-31=参数, rb32-63=callee-saved
- RF bank：rf0=FCSR, rf1-7=temp, rf8-15=temp, rf16-31=参数, rf32-63=callee-saved
- RA bank：ra0=RAS控制, ra1-62=返回地址slot, ra63=RAS栈顶

§2 数据表示
- 基础类型映射（与 AEE §数据表示一致）
- 聚合体对齐规则
- 大端序说明

§3 参数传递
- 三 bank 独立计数（rd16-31  rb16-31  rf16-31）
- 标量参数提升规则
- HFA/HPA 判定流程（浮点/指针聚合）
- 聚合体参数规则（≤32B 拆分为 RD 块，>32B sret）
- 栈溢出规则
- 变参（varargs）规则

§4 返回值
- 标量：rd31/rb31/rf31（按类型）
- 多返回值：各 bank 独立逆序分配
- 聚合返回值：sret 模式

§5 栈帧布局
- SP 向下增长
- 帧布局：内存参数 → 保存的 rbfp → 保存的寄存器 → 局部变量 → red zone（128B）
- 8 字节对齐

§6 调用序列
- 调用者/被调用者职责
- 序言（prologue）/尾声（epilogue）

§7 未解决问题（标注 [OPEN]）
- Varargs 详细约定
- 动态链接 TLS
- 帧指针省略规则

版本号：0.9.2（与 wiki ABI 版本一致）

2. 创建 `verif/abi.yaml`：

```yaml
format: 1
version: "0.9.2"
abi: "DADAO-v5"
data_layout: "E-m:e-i64:64-n64-S64"
stack_alignment: 8

parameter_registers:
  rd: [16, 31]     # 16 个数据参数寄存器
  rb: [16, 31]     # 16 个地址参数寄存器
  rf: [16, 31]     # 16 个浮点参数寄存器

return_registers:
  rd: 31
  rb: 31
  rf: 31

callee_saved:
  rd: [32, 63]     # 32 个被调用者保存的 rd
  rb: [32, 63]     # 32 个被调用者保存的 rb
  rf: [32, 63]     # 32 个被调用者保存的 rf

reserved_registers:
  rd: [0, 1, 2, 3, 4, 5, 6, 7]   # rd0=zero, rd1=rderrno, rd2-7=reserved
  rb: [0, 1, 2, 3, 4, 5, 6, 7]   # rb0=rbip, rb1=rbsp, rb2=rbfp, rb3=rbgp, rb4=rbtp, rb5-7=reserved
  rf: [0]                         # rf0=FCSR
```
```

### Agent E2：ELF/SBI 合约

**职责**：创建 ELF 合约和 SBI 合约

**提示词**：
```
你是 DADAO-v5 的 ELF 和系统接口工程师。创建 ELF/对象 ABI 合约和 SBI 规范合约。

1. 创建 `contracts/elf/spec.md`：

基于 DADAO-0628/contracts/elf/spec.md 的格式，但根据 DADAO-v5 规范更新：

- EM_DADAO = 0x0DA0
- 大端序 ELF64
- ELF 文件头结构
- Section headers（.text, .data, .bss, .rodata, .comment, .debug 等）
- Relocation 类型（PC 相对 reloc、绝对 reloc、call 24-bit reloc）
- Symbol table 条目格式
- ABI 特定的 section 属性

2. 创建 `contracts/sbi/spec.md`：

基于 DADAO-v5/wiki/DADAO-22-SBI 和 DADAO-23-HBI：

§1 调用约定
- trap/escape 流程
- 参数传递（与 ABI 一致）
- 嵌套调用规则
- 错误码定义

§2 umon/jmon（用户态异常处理）
- 系统调用分发
- 版本查询

§3 smon（系统信息）
- SBI 版本查询
- cfx 探测

§4 ptw（页表）
- 页表步进功能

§5 tlb/cache（TLB/Cache 管理）
- TLB 刷新、地址范围失效

§6 pmem（物理内存管理）
- 页面分配/释放

§7 timer/uart/power
- 定时器、串口、电源管理

3. 创建 `verif/sbi.yaml`：
   机器可读的 SBI 函数表，每个条目：cfxcode、函数编号、名称、入参、出参、说明
```

### Agent E3：架构决策记录

**职责**：创建 ADR-0003 和 ADR-0004

**提示词**：
```
你是 DADAO-v5 的架构师。创建关键的架构决策记录。

1. 创建 `project/adr/0003-object-abi.md`：

基于 DADAO-0628/docs/adr/0003-object-abi.md，针对 DADAO-v5 更新：

- 决策：大端序 ELF64，EM_DADAO=0x0DA0
- ELF 文件格式定义
- 重定位类型定义（R_DADAO_NONE, R_DADAO_24, R_DADAO_PC_24 等）
- CodeModel 选择（small/medium/large）
- 与 LLVM MC 后端的接口

2. 创建 `project/adr/0004-test-machine.md`：

基于 DADAO-0628/docs/adr/0004-test-machine.md，针对 DADAO-v5 更新：

- 裸机测试机定义（命名 dadao-m1-v5）
- 内存映射：
  - ROM: 0x0010_0000（64KB）
  - RAM: 0x8000_0000（128MB）
  - Exit port MMIO: 0x1000_0000（8B）
- 复位向量：0x0010_0000（注意：DADAO-v5 wiki 中 cfx_power_hypv_excp_vector 在 0xFFFF_FFFF_0000）
- 测试入口：0x8000_0000
- 退出协议：sto 到 exit port，低 8 位为退出码
- 异常可观测性协议
```

## 阶段验证

- `contracts/abi/spec.md` 中每个 [引用] 对应 wiki 中实际存在的章节
- `verif/abi.yaml` 与 `contracts/abi/spec.md` 内容一致
- `verif/sbi.yaml` 与 `DADAO-22-SBI.md` 的函数表一致

## 依赖关系

- 依赖 Phase 0（文档目录结构）
- 是 Phase 5（组件基线）和 Phase 6（LLVM MC）的前提
