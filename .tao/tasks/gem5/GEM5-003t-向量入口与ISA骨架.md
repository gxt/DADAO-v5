# GEM5-003t: 向量入口与 ISA 骨架

**模块**：gem5
**项目里程碑**：M8
**依赖**：`GEM5-002t`、`ADR-0036` D1–D4 逐条确认并 Accepted
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范
- 输入：`contracts/opcodes.yaml`、`tests/vectors/isa/`、`contract-isa.md §1–§2`、现有 LLVM MC 产物。
- 输出：`tests/gem5/` 向量映射和 `tools/gem5/` 测试驱动；可实例化单核 CPU、装入少量指令字并回读寄存器/PC/异常的最小全系统执行 fixture（仅服务 ISA 测试）；gem5 DADAO ISA 构建注册、RD/RB/RA/RF 状态、PC、复位基础、32 位大端取指与译码框架；可复现的 `make build-gem5`（`build/DADAO/gem5.opt`）。
- 约束：期望从规范/合约独立派生；脚本以可配置路径定位 `gem5.opt` 与测试产物；非法/保留编码不得静默当 NOP。先立向量和门控，再补实现。
- 启动实核（2026-10-12）：`tools/gem5/vector_inventory.py` 在现有 `tests/vectors/isa/` 中确认 150/227 个 opcode 有 active 编码向量；缺口为 FP 60、excluded 11、m1 5、m3 1。`--require-complete` 现按预期 FAIL；本任务先覆盖代表格式并建立运行期 fixture，余项按 `GEM5-004t`–`006t` 补齐，不能把静态清单视为执行验收。

## 验收标准
1. 代表性合法编码被译为正确指令，保留编码和零指令触发合约规定的异常；覆盖不同指令格式、寄存器组及立即数字段。
2. 最小执行 fixture 可独立装入指令、执行有限步并导出状态；复位值、`rd0`、`rb0` 当前 PC、RF/FCSR 初值和 4 字节 PC 对齐由独立向量核验。完整 ROM/ELF/semihosting 平台仍归 `GEM5-005t`。
3. 向量目录可列出覆盖与待实现项；至少一次篡改期望/注入错误编码令门控 FAIL，恢复后 PASS。
4. `make build-gem5` 构建出的 DADAO 二进制可打印版本/帮助，`make check` 通过；未实现语义显式失败。

## 完成区
**测试结果**：`make build-gem5` 退出 0，构建官方 25.1.0.1 的 DADAO `gem5.opt`；`make test-gem5` 16 条运行用例通过，含独立审阅要求的 FCSR 复位/别名与 IALIGN。合约生成表的 `--check`、33 个逐文件补丁的重放与 base+1 源码状态检查通过。结果见 `components/gem5/evidence/GEM5-003t.md`。
**修改文件**：`build_opts/DADAO`、`src/arch/dadao/` 与上游 `src/arch/{Kconfig,SConscript}`、`src/cpu/simple/AtomicSimpleCPU.py` 经 `components/gem5/` 一文件一补丁导出；仓库 `Makefile` 的 gem5 入口、`tools/gem5/{test_isa.py,vector_inventory.py,generate_opcode_table.py}`、`tests/gem5/`、gem5 文档与本任务书。
**验收结果**：RD/RB `add.si`、双目的 `add.uo`、32 位大端取指、PC/复位及 `ILLI`/`UNDI`/`IALIGN` 初步闭环；缺失寄存器接口和错误期望均能使门控非零退出。独立审阅发现的 FCSR 初值/别名、IALIGN、二进制路径三个缺口已修正并通过复审。
**新发现/坑**：gem5 `sim/tags.cc` 被上游强制重建，增量 SCons 每次仍链接；`m5.simulate(1)` 可精确执行一次 CPU tick 并在下一次取指前停机。gem5 把 fetch 请求地址对齐到译码块，故 IALIGN 必须检查请求保存的架构 PC。
**遗留问题**：003 只定义 ISA 骨架历史边界；标量与 Machine-01 已分别由 004/005 接续，FP、M8 新指令与全量收口仍归 006–008。仓库级知识引用阻断不在 gem5 修改范围。

## 审阅记录

2026-10-12 独立审阅先指出三项缺口：FCSR/rf0 双状态与错误复位值、取指未对齐未报 IALIGN、gem5 二进制路径硬编码。修复后复核：`rf0` 为 FCSR 唯一存储且固定 qNaN 位、写掩码双向验证；`Request::getPC()` 提供未对齐的架构 PC，16 号用例得到 `IALIGN/0x8d` 且 PC 不前进；`--gem5`/环境变量可指定二进制。复核结论为 gem5 003 范围无剩余阻断。仓库级非 gem5 门控缺失仍在完成区如实保留。

#### 2026-10-12 收尾 reviewer 独立验收

- `--profile skeleton` 退出 0，16/16；与 `ec9f281` 的历史 003 指令序列逐项一致。默认 `current` profile 退出 0，保持 50/50。
- reviewer 在 `/tmp/opencode/GEM5-003t-reviewer` 的向量副本中注入错误期望，门控退出 1；副本恢复后 SHA256 与真源一致，重跑退出 0。
- opcode 表检查、150/227 向量清单、DADAO build-info/help、33 补丁重放和源码 `base+1 clean` 均通过。
- `--require-complete` 退出 1、`check-gem5-full` 退出 2，明确保留 77 项后续缺口，未冒充全量执行验收。
- `make check`、`check-modules`、`check-full` 的非 gem5 失败分别为 60 个悬空引用、缺 `llvm-lit`、缺 `qemu-system-dadao`，按用户授权记外部阻断。
- 修改范围未命中 `spec/` 或非 gem5 模块；未修改、提交或推送。
- **判决：Accepted**。

#### 2026-10-12 architect 交叉复核与统一报告

- 新增 `skeleton` profile 只隔离 004 后追加的 scalar/control 向量；公共的 fixture、复位、异常和 FCSR 检查仍按当前实现执行，不回退修复。
- `--vector-root` 使反例在临时副本完成，避免覆盖真源；缺目录和缺二进制均显式失败。默认 profile 行为保持兼容。
- reviewer 的历史边界、运行结果、反例、完整覆盖缺口和外部阻断记录相互一致，任务四项 gem5 验收无剩余 finding。
- **统一判决：Accepted，状态置为 `已验证`**。

#### 2026-10-15 工具链恢复后复核

- `--profile skeleton` 再次退出 0，61/61；默认 current 517/517，证明后续 005 修复未回归 ISA 骨架。
- 安装后的 `llvm-lit` 107/107、接口对齐 83/83 均通过；旧“缺 llvm-lit”说明只保留为历史记录。
