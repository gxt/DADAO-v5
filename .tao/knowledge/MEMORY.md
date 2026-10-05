# MEMORY — DADAO-v5 项目记忆

## 这是什么

DADAO-v5 基于 19 份上游 spec/ 规范文档（SimRISC-00~12 + DADAO-11~23，SimRISC 0.5.4）与 v5 自定规范（`spec/Toolchain-01`、`spec/Process-0x`；索引 `spec/README.md`），从零构建 LLVM/QEMU/Chipyard/Linux 全栈。核心方法是"Agent 写代码、你写约束"——角色分工见全局 `AGENTS.md` 与 `.tao/README.md`。

## 当前进度

| 项目 | 状态 |
|------|------|
| **M1 归档**（2026-10-03） | ✅ M1 历史（testcases 模块 / M1 任务规划 / M1 实现 三行）已归档至 `.tao/archive/M1/README.md`；76 个 M1 任务书同在该目录。 |
| **M2 归档**（2026-10-04） | ✅ M2 历史（45 行 + 2 条混合行〔`spec 模块`/`integ 模块`〕的 M2 段落）已归档至 `.tao/archive/M2/README.md`；149 个 M2 任务书同在该目录。 |
| **M3 进行中**（2026-10-05 起） | M3 = **Basic CodeGen（纯整数）**。规划定稿：`ADR-0018`（取舍点 C1–C17，Accepted）+ `adr-0012 D9`（新增 `sub.o_orrr_dbb` + RB 算术三条改名，opcodes 227→**228**）。任务分解/串行链见 `SPEC-096k`。**已验证**：`SPEC-101t`（RB 三条改名+改槽）、`SPEC-100t`+`QEMU-040t`（新增 `sub.o_orrr_dbb`，原子对）、`INFRA-035t`（`llc` 入构建目标）、`LLVM-033t`（CodeGen 骨架，SelectionDAG）、`LLVM-034t`（GPRD/GPRB 双类 + 跨 bank 搬运）、`LLVM-043t`（新增指令 `sub.o` MC）、`LLVM-045t`（wyde 裸数字拒绝，关闭 `ISS-128`）、`LLVM-044t`（M1 多寄存器加固，关闭 `ISS-104`/`ISS-106`）、`LLVM-046t`（InstrInfo 生成器/校验器刷新，关闭 `ISS-103`）、`SPEC-103t`（spec 门控脚本小修，关闭 `ISS-122`/`ISS-123`/`ISS-077`/`ISS-079`）、`INFRA-037t`（infra/integ 工具与文档小修，关闭 `ISS-094`/`ISS-132`/`ISS-133`）。 |
| SimRISC 规范 | ✅ 0.5.4 |
| spec 模块 | ✅ M1 完成（`002t`~`010t` 已验证；`011m` 里程碑）。 |
| integ 模块 | ✅ M1 完成（`001k`~`003t` 已验证；`004m` 里程碑）：`002t` = E2E 冒烟（`tests/e2e/*.s` + `tests/lit/E2E/`，lit 3/3，`.test` 消费 `.s` + `timeout`，反例门控）；`003t` = 跨模块接口对齐核对（`docs/integ-interface-alignment.md` + `tools/integ/check_interface_alignment.py`，80 项 0 FAIL，4 轮 reviewer）——**发现 ELF `e_flags=0x0` 违约**（另建 `LLVM-014t` 修复） |

## 关键目录速查

| 路径 | 用途 |
|------|------|
| `spec/` | 规范：上游 19 份（SimRISC-00~12 + DADAO-11~23）+ v5 自定 `Toolchain-01`/`Process-0x`；索引 `spec/README.md`（spec 模块任务可改） |
| `manifests/` | 锁文件（规范/参考组件） |
| `.tao/tasks/<module>/` | 按模块分的任务文件（`<PREFIX>-nnn<suffix>`） |
| `.tao/knowledge/` | 知识沉淀（MEMORY/milestones/contract；ADR 已迁 `.tao/adr/`） |
| `.tao/knowledge/milestones.md` | 项目里程碑路线图（M1/M2） |
| `.tao/knowledge/issues.yaml` | Issue 注册表（M1-gate 判据 + 各模块 issue 台账；已吸收原 backlog 散文台账的 issue 部分） |
| `.tao/knowledge/lessons.md` | 经验与教训（教训/方法论/过程记录；原 backlog 散文台账拆分） |
| `.tao/adr/` | 架构决策记录（ADR，决策层） |
| `.cache/refs/<id>/` | 参考仓库只读工作树（`DADAO-0628`/`DADAO`；`make fetch-refs` 重建，不入库） |
| `contracts/` | 机器可读合约数据（编码表/ABI/合法性规则） |
| `tools/<module>/` | 各模块工具脚本（infra/spec/llvm/qemu/testcases） |
| `tests/` | 测试向量（`tests/vectors/`）、harness（`tests/scripts/`）、lit、e2e |
| `components/` | 组件补丁（llvm/qemu/gem5） |
| `sail/` | Sail 形式化规范 |
| `.cache/<原始仓库名>.git` | 上游组件持久 bare mirror（gitignored；避免重下大仓库）；目录名 = 原始仓库名（见「重要决策」） |

## 重要决策

- **数据/工具分离**：机器可读合约数据放 `contracts/`，各模块工具脚本放 `tools/<module>/`（`scripts/` 并入 `tools/infra/`）
- **模块重划（2026-09-14）**：`verif` 解散——通用 CI 检查→`infra`、领域验证依据→`spec`、组件自测→`llvm`/`qemu`、集成→新模块 `integ`
- `.tao/` 集中存放所有 agent 中间文件（对齐 t.a.o 全局约定）
- **模块清单**：`infra`/`spec`/`testcases`/`golden`/`llvm`/`qemu`/`integ`/`gem5`/`sail`（`abi` 并入 `spec`；`verif` 已解散）
- **任务编号**：`<PREFIX>-nnn<suffix>`，suffix `k`=启动/`t`=普通/`m`=里程碑；模块内递增
- **项目里程碑**：M1/M2，见 `.tao/knowledge/milestones.md`
- **去阶段化**：任务不按 Phase 组织，直接参考 DADAO-0628；已删除 `docs/phases/`
- **执行前确认**：任务分解参考 DADAO-0628 生成、未逐一审核，执行前须与用户确认任务书（见 `AGENTS.md`）
- **跨模块交互**：里程碑核验须考虑其它模块影响；需修复时里程碑后移或增加交互任务（见 `AGENTS.md`）
- **QEMU 任务重构（ADR-0010 Accepted，2026-09-19）**：D1 harness 前置（`jump-rrii`/`br.nz` → 006t，修法 a 普通模式不 emit dumper）、D2 translate.c 拆分（10 个 `.c.inc`）、D3 任务重排（006t 合并 MALIGN、007t 改为拆分、补丁 0004–0007）、D4 验收规范化（逐条标注「现在可跑/BLOCKED」）；新增 `QEMU-020t`（harness dumper 改造；**2026-09-21 已关闭**——交付物 #1 由 `015t` 落地、分段 dumper 因 `022t` 根治 TB 缺陷而不再必要）。`QEMU-014t` 依赖修正为 `004t+006t`；`QEMU-016t` 依赖修正为 `TESTCASES-004t`
- **测试机地址图（ADR-0004，2026-09-13 修订）**：采用 spec 核内地址空间模型（cfxha 63/power）——boot ROM `0xffff_ffff_0000`（= `cfx_power_hypv_excp_vector`）、RAM `0xffff_0000_0000`(16MiB)、Exit port `0xffff_8000_0000`(8B)；机器 fault 退出码 = `0x80 | spec_cause_bit`（ILLI `0x88`、UNDI `0x89`、RASOF `0x8A`、RASUF `0x8B`、MALIGN `0x8C`、IALIGN `0x8D`），unmapped `0x87`（测试机约定）
- **标识符 = 原始仓库名（2026-09-17，`INFRA-013t`）**：组件 `name` 取 GitHub 仓库名（如 `llvm-project`，非简称 `llvm`）、参考仓库 `id` 取原始仓库名含大小写（如 `DADAO-0628`）；manifest 值必须与 `ADR-0002` 的 `.cache/<name>.git`、`.cache/refs/<id>.git` 占位符一致。缓存目录因此为 `.cache/llvm-project.git`、`.cache/refs/DADAO-0628.git`；工作树为 `.work/source/llvm-project`（`LLVM_SRC=.work/source/llvm-project/llvm`）
- **DADAO target 经 `LLVM_ALL_TARGETS` 注册（2026-09-17，ADR-0007）**：DADAO 通过加入 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表注册，使 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效；否决 experimental 通道。`LLVM-003t` 补丁须包含此增项
- **LLVM 基线 = 23.1.1（2026-09-17，ADR-0006）**：lock 值 = commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（`llvmorg-23.1.1` 附注 tag 对象 `e7ce3600…` 仅溯源）；获取源 = SJTU 浅 bare 镜像 `.cache/llvm-project.git`（`--depth 1`，无完整历史，见 ADR-0006 Consequences）；`repository` 仍为 github 规范 URL；M1 期间不 bump
- **性能排查先定位主因，勿默认瓶颈在"重量级外部进程"（`INFRA-030t`，2026-10-03）**：`check-qemu-semantics` 的 46s 主因**不是**串行启动 QEMU（149 例 QEMU 合计仅 **~2.4s**），而是 `build_binary()` **每例重复 `yaml.safe_load` 整个向量 YAML**（纯 Python SafeLoader、GIL 绑定；149 次 ≈33–43s）。**GIL 下限速必须先消除重复工作（缓存）再并行**——只上线程池零提速（实测未加缓存 `thread8`≈45s，加缓存后 0.38s）。方法：先 profiling/独立计时，再决定优化手段
- 角色规则由全局 `opencode/agent/` 提供，工作仓库不含 agent 文件

## 上游 ↔ v5 偏离台账

> M2 门槛⑤交付物：登记 **6 项**上游 spec 与 v5 决策之间的**规范性偏离**。每项均已由**已 `Accepted` 的 ADR**（或 M1→M2 过渡任务 `SPEC-086t`）固化；本节只做**归一化登记 + 指针**，不新增决策。`scope`、`RACNT`、`MRPTR`、exit 码等写法与 `contracts/opcodes.yaml`、ADR 一致。

| # | 偏离点 | 上游依据 | v5 决策 | ADR / 契约指针 |
|---|--------|----------|---------|----------------|
| 1 | **exit port（程序停机）** | `SimRISC-11 §退出指令`：`escape cfxHA, [excp_cause_ip, imms20]`（**退出特权态**，非停机；编码层 `imms18`） | 自定 **exit port** MMIO（`0xffff_8000_0000`，8 B，只写）；退出码 = `0x80 \| cause_bit`；写入后 `cpu_loop_exit()` 锁定 | **ADR-0004 §D3**（Exit Port 协议）+ **ADR-0011 §D1–D4**（可靠 halt） |
| 2 | **`fence` SBZ 非零** | `SimRISC-12 §fence指令`：`immu18 bits[17:4]` 为 SBZ，**非零值行为保留** | v5 定**非零 SBZ → ILLI**（`0x88`）；且 `fence` 整体 `scope: excluded`（未实现，decode ILLI） | **ADR-0004 §D5.3**（SBZ 非零 → ILLI）+ **ADR-0014 §D1–D3**（fence 移出 M1）；`contracts/opcodes.yaml::fence_oiii_imm` |
| 3 | **测试机地址映射 / 复位值** | `spec/` **无测试机层**（`DADAO-12 §2.1` 仅给核内地址空间模型，无内存映射 / 复位值全集 / exit 协议） | 采用 spec 核内地址空间模型（cfxha 63/power）：boot ROM `0xffff_ffff_0000`、RAM `0xffff_0000_0000`(16 MiB)、Exit port `0xffff_8000_0000`；复位 PC=`rb0`=boot ROM；`rd0`/`rb1`–`rb63`/`ra0`–`ra63`/`rf1`–`rf63` 复位 `0`、`rf0` 复位 `0x7FF8_0000_7FC0_0000`（架构自定义确定性复位） | **ADR-0004 §D1/D2**（内存映射、复位向量与复位值） |
| 4 | **`ra0` 语义（MemRAS 简化）** | `SimRISC-00 §返回地址栈`（v5 修订前；对照归档 `spec/SimRISC-0.5.3/SimRISC-00`）：`ra0` 高 16 位 = **MemRAS 引用计数** | v5 `ra0` = `[63:54]` SBZ + `[53:48]` **`RACNT`** + `[47:0]` **`MRPTR`**；**取消 MemRAS 引用计数**；有效性判据 = `RACNT` | **ADR-0012 §D7**（D7.1–D7.7） |
| 5 | **`e_flags` 版本字段** | `spec/` **无 ELF/Object ABI**（`e_machine`/`e_flags` 无依据） | `e_machine = EM_DADAO (0x0DA0)`（project-custom，未注册）；`e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本 = 1；bits 8–31 保留 0） | **ADR-0003 §D1**（含 `## 修订` 的 `e_flags` 版本字段）；投影 `contract-elf.md §1.3` |
| 6 | **M1/M2 排除口径**（**订正**） | 上游把浮点（`SimRISC-07`）、特权 cfx（`SimRISC-11 §特权指令` + `DADAO-12/13`）、LR-SC（`SimRISC-12 §LR-SC指令`）、`fence`（`SimRISC-12 §fence指令`）均定义为架构指令 | v5 用 `scope ∈ {m1, fp, excluded}` 划范围：`m1` 已实现；**`fp` 60 条已实现（不再是 ILLI）**；`excluded` 15 条（cfx 6 + fence 1 + LR-SC 8）仍 decode **ILLI** | **ADR-0012 §D3.1**（0 号寄存器/范围）+ **ADR-0014**（fence excluded）+ `SPEC-086t`（scope 口径，`contracts/opcodes.yaml` + `check_scope.py`） |

> **订正说明（第 6 项）**：历史表述「浮点未实现 ⇒ decode ILLI」在 `QEMU-034t`~`037t`（执行层 60/60）后**已不成立**；现行口径为「**浮点已实现**（`scope: fp`），**仅** cfx/LR-SC/fence（`scope: excluded`）仍 ILLI」。本台账以此为准。
>
> **章节订正（实测）**：任务书/`docs/m2-spec-planning.md` 沿用 **SimRISC 0.5.3 编号**；v5 现行规范为 **0.5.4**，章节已重排——上游依据「exit port vs `escape`」现位于 `SimRISC-11 §退出指令`（0.5.3 为 `SimRISC-04`）、`fence` SBZ 位于 `SimRISC-12 §fence指令`（0.5.3 为 `SimRISC-04`）、浮点规范为 `SimRISC-07`（0.5.3 为 `SimRISC-03`）。均以 `contracts/opcodes.yaml` 的 `spec_cite` 实测为准。

## 如何参考 DADAO-0628 和 DADAO

- `DADAO-0628`：基于 SimRISC 0.4.1 的完整实现，包含补丁集和任务文件
- `DADAO`：各阶段早期的代码实现（已不再更新），包含 LLVM/QEMU/Chipyard 等组件的具体实现
- 两者 commit 锁定于 `manifests/references.lock.toml`（由 `INFRA-003t` 建立）
- 路线图与任务拆解直接参考 DADAO-0628：`docs/development-roadmap.md`（M0/M1/M2/M2.5）、`code-agent/designs/0002-detailed-roadmap.md`、`code-agent/tasks/`

## 规范版本对应

规范版本与冻结状态的**唯一来源**是 `README.md`「当前版本号」表（SimRISC 0.5.4 / AEE·ABI 0.9.2 / SEE·SBI 0.7.1 / HEE·HBI 0.1.2）。v5 不使用 `manifests/spec.lock.toml`。

## 关键差异提示（相比 DADAO-0628）

DADAO-v5 基于 SimRISC 0.5.4 规范，与 DADAO-0628（锁定在 SimRISC 0.4.1）相比有以下关键差异：

### 0.5.4 vs 0.4.1 的变化

1. **指令命名重构**：所有指令使用 `.b`/`.w`/`.t`/`.o` 位宽后缀，有符号/无符号用 `s`/`u` 区分（如 `add.uo`/`add.so`、`mul.uw`/`mul.sw`）。原 0.4.1 的 `add`/`sub`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`/`shrs`/`shru`/`shlu` 等命名已废弃。此外，LR/SC 原子指令使用 `_nn`/`_nr`/`_an`/`_ar` 后缀标记 acquire/release 语义

2. **格式体系重构**：引入 MISC-byte/wyde/tetra/octa 四个子表，通过 `orrr`/`orri` 格式覆盖各固定位宽的 and/or/xor/xnor/ext/shr/shl/add/sub/cmp/mul/div/rem 操作

3. **QFC 编码表重组**：opcode 分配完全改变（见 SimRISC-00 QFC 表），涉及所有指令的 mask/value

4. **新指令**：`add.si`（riii 格式自增自减）、`br.z-rb`/`br.nz-rb`（rb0 零/非零分支）、`cs.n-rf`/`cs.z-rf`/`cs.p-rf`/`cs.eq-rf`/`cs.ne-rf`（浮点条件赋值）

5. **寻址语义变化**：RB 算术改为全 64 位运算（原 48 位限制移除，bits[63:48] 为运算结果可用于溢出检测）

6. **立即数格式变化**：`add.si` 从 rrii（两寄存器 + 12 位 imm）改为 riii（一寄存器 + 18 位 imm）；`rela.si` 同理

7. **浮点扩展**：新增 `ft2ft`/`fo2fo`（浮点内部格式转换）

8. **命名风格统一**：`.` 作为命名分隔符（`cs.n`/`cs.z`/`cs.p`、`br.n`/`br.nn`/`br.z`、`set.zw`/`set.ow`、`or.w`/`andn.w`）

### 不变的差异（从 0.4.1 延续）

- 浮点架构完整定义（SimRISC-03），需 golden model 骨架和 LLVM 寄存器类
- 系统指令：cfx2rd/cfx2rc/cfxld/cfxst/trap/escape 指令族（SimRISC-04）
- 原子操作：lr/sc LR-SC 指令
- 命名规范：wpN（非 ww）、pmem（非 phymem）、illi（非 unimp）
- Scope 更广（含浮点/系统），实现优先级可先聚焦标量核心

## 文件映射：spec → contracts

| spec/ 文件 | 对应 contract（在 `.tao/knowledge/` 下） | 主要消费者 |
|-----------|------------------------------------------|-----------|
| SimRISC-00 ~ 04 | `contract-isa.md` | golden model, LLVM, QEMU, gem5, Sail |
| DADAO-11 AEE | `contract-abi.md` | LLVM CodeGen |
| DADAO-12 SEE | `contract-exception.md`（推迟）+ `contract-sbi.md` | QEMU, Linux |
| DADAO-13 HEE | `contract-exception.md`（推迟） | Chipyard |
| DADAO-21 ABI | `contract-abi.md` | LLVM CodeGen |
| DADAO-22 SBI | `contract-sbi.md` | QEMU, Linux |
| DADAO-23 HBI | `contract-sbi.md` | Chipyard, Linux |

## 职责边界

| 内容 | 位置 | 说明 |
|------|------|------|
| 数据表示（byte/wyde/tetra/octa） | SimRISC-00 | ISA 基础概念 |
| 寄存器模型（rd/rb/rf/ra） | SimRISC-00 | ISA 核心组成部分 |
| 浮点状态寄存器（rf0） | SimRISC-00 | 浮点指令基础 |
| 返回地址栈（RAS） | SimRISC-00 | 函数调用支持 |
| 存储模型 | SimRISC-00 | 地址空间定义 |
| 不同宽度数据的运算处理 | AEE | 运行环境相关 |
| 地址空间布局 | AEE | 应用程序运行环境 |
| 汇编兼容性 | AEE | 汇编器支持 |
| 函数调用规范 | ABI | 软件约定 |
| 系统调用规范 | ABI | 软件约定 |
