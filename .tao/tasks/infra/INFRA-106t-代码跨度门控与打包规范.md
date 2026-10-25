# INFRA-106t: 代码跨度门控与打包规范

**模块**：infra
**项目里程碑**：M10
**依赖**：ADR-0036（已 Accepted）
**状态**：待开始

## 执行环境
**执行环境**：本地（纯脚本，无 LLVM 重建）

## 接口规范

### 背景事实（实测，2026-10-25）
- `call`/`jump` = REL26（`imms24` 字偏移）⇒ ±32 MiB；`br.n..` = REL20（±512 KiB）；`br.eq/ne` = REL14（±8 KiB）。
- 64 MiB 布局下 LLD 报 `R_DADAO_REL26 out of range: 16515066 is not in [-8388608, 8388607]`；16 MiB 布局正常。
- ADR-0036：硬约束「任一 REL26 边 ≤ 32 MiB」，打包预算「单 DSO 可执行区跨度 < 30 MiB」。

### 输出
1. `tools/infra/check_code_range.py`（纯 stdlib）：
   - 输入：一个或多个 DADAO ELF（可执行 / DSO；需链接时带 `--emit-relocs`，或工具自行反汇编解出目标地址——实现方式二选一并在完成区说明）；
   - 输出每个产物：`max_rel26_edge`（字节）+ `margin`（32 MiB − 最远边）、`max_rel20_edge`、`max_rel14_edge`、`exec_span`（所有 `SHF_EXECINSTR` 段 `[min,max]`）；
   - 判据：任一 REL26 边 > 32 MiB ⇒ rc=1；`exec_span ≥ 30 MiB` ⇒ rc=1；其余 rc=0。
2. `make check-code-range`（L2，接入 `check-modules`）：
   - 用**合成 fixture**（小 ELF + 构造的远距重定位）跑门控，不依赖重建；
   - 正常 fixture 绿、越界 fixture 红。
3. 打包规范：`.tao/knowledge/MEMORY.md` 增一条（≤3 行，指向 ADR-0036）。

### 约束
- 不引入第三方依赖；不修改 `components/`；
- 每条判据有**可达 FAIL** 路径；阈值不写死在多处（单一真源）。

## 验收标准
1. 对仓库现有真实产物（如 musl/qemu 测试 ELF）跑通，输出最大边与余量。
2. 合成 >32 MiB 布局 ⇒ rc=1 且指出具体产物与边；正常产物 ⇒ rc=0。
3. 反例注入（构造越界 / 改阈值）→ 红 → `cp` 还原 → 绿（禁 `git checkout` 还原）。
4. `make check` 不受影响；`make check-modules` 含新门控且绿。
5. 完成区贴真实输出、退出码、日志路径。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
