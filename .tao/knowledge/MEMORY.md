# MEMORY — DADAO-v5 项目记忆

## 这是什么

DADAO-v5 基于 11 份 spec/ 规范文档（SimRISC 0.5.3），从零构建 LLVM/QEMU/Chipyard/Linux 全栈。核心方法是"Agent 写代码、你写约束"——角色分工见全局 `AGENTS.md` 与 `.tao/README.md`。

## 当前进度

| 项目 | 状态 |
|------|------|
| SimRISC 规范 | ✅ 0.5.3 |
| spec 模块 | ✅ M1 完成（`002t`~`010t` 已验证；`011m` 里程碑） |
| testcases 模块 | 🔄 `002t` 已验证（向量基础设施：schema+`expected_pc`、inventory+`format` 列+机械同步、validator 补强；覆盖率门控为**声明级**，数据级归 `009t`）；`003t` 已验证（寄存器族 6 文件：`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`，130 身份/366 条；生成器 `tools/testcases/generate_isa_vectors.py` 已入 git）；`004t` 已验证（访存 3 文件：`mem-rd`/`mem-rb`/`mem-ra`，30 身份/172 条；生成器 `tools/testcases/generate_mem_vectors.py` 已入 git；validator 追加 F10 守卫）；`005t` 已验证（`ctrl-br.yaml`，10 个 `br.*` 身份/30 条，taken+not-taken 全测；生成器 `tools/testcases/generate_ctrl_br.py` 已入 git；validator 追加 F7 `expected_pc` 存在性规则，作用域 `br.*`）；`006t` 已验证（`ctrl-jump`/`ctrl-call`/`ctrl-ret`，5 身份/16 条；F7 全 active；生成器 `tools/testcases/generate_ctrl_jump_call_ret.py` 已入 git；validator 的 F7 规则扩展至 `jump`/`call`/`ret`）；`007t` 已验证（`misc.yaml`，3 身份/6 条：`swym`/`illi`/`fence`；**F6** `illi` 恒 ILLI → encoding/semantic 豁免、覆盖率由 legality 满足；`fence` SBZ→ILLI；生成器 `tools/testcases/generate_misc.py` 已入 git）；`008t` 已验证（保留编码 → UNDI 的向量层表达（方案 A：`class: legality` + `encoding.reserved: true`）；`tests/vectors/isa/reserved.yaml` 2 条；validator 加 reserved 分支 + R8 交叉校验（word 不得匹配 opcodes 任何记录，含 `excluded_m1`）；反造假脚本 `tools/testcases/test_anti_forgery_008t.py`）；`009t` 已验证（ISA 向量全量再审计：15 文件/597 条逐族重推导，**0 残留错值**；审计记录 `.tao/knowledge/testcases-009t-audit.md`、脚本 `tools/testcases/009t-audit.py`（318/320, 0 mismatch）；`validate_vectors.py` 加数据级覆盖门控（只报不拦）；**发现 154 缺口**（141 legality+2 boundary+11 overlap））；`010m` **受阻**（154 缺口未消解，见 `deferred.md`；建议新建 `010t` 补数据 + 里程碑顺延 `011m`） |
| M1 任务规划（infra/spec/testcases/llvm/qemu/integ） | ✅ 已生成（参考 DADAO-0628；**testcases 已计划级复核**，其余未逐任务审核） |
| M1 实现 | 🔄 进行中（spec ✅ M1 完成；infra：`002t`~`009t`、`013t` 已验证（`013t` = 按原始仓库名命名；里程碑顺延为 `014m`）；`010t`~`012t` 待开始；testcases：`001k`~`009t` 已验证（15 个 `isa/*.yaml`、597 条；154 数据级缺口待补）；llvm：`002t` 已验证（组件基线：ADR-0006 Accepted + manifest `enabled=true` + commit `6dfe1677…` + `build-mc` 真实构建；DADAO target 待 `LLVM-003t` 注册，见 ADR-0007）；qemu/integ 待推进） |

## 关键目录速查

| 路径 | 用途 |
|------|------|
| `spec/` | 11 份原始规范文档（只读） |
| `manifests/` | 锁文件（规范/参考组件） |
| `.tao/tasks/<module>/` | 按模块分的任务文件（`<PREFIX>-nnn<suffix>`） |
| `.tao/knowledge/` | 知识沉淀（MEMORY/milestones/contract/adr） |
| `.tao/knowledge/milestones.md` | 项目里程碑路线图（M1/M2） |
| `.tao/knowledge/deferred.md` | 各模块暂缓/备忘（避免遗忘） |
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
- **测试机地址图（ADR-0004，2026-09-13 修订）**：采用 spec 核内地址空间模型（cfxcode 63/power）——boot ROM `0xffff_ffff_0000`（= `cfx_power_hypv_excp_vector`）、RAM `0xffff_0000_0000`(16MiB)、Exit port `0xffff_8000_0000`(8B)；机器 fault 退出码 = `0x80 | spec_cause_bit`（ILLI `0x88`、UNDI `0x89`、RASOF `0x8A`、RASUF `0x8B`、MALIGN `0x8C`、IALIGN `0x8D`），unmapped `0x87`（测试机约定）
- **标识符 = 原始仓库名（2026-09-17，`INFRA-013t`）**：组件 `name` 取 GitHub 仓库名（如 `llvm-project`，非简称 `llvm`）、参考仓库 `id` 取原始仓库名含大小写（如 `DADAO-0628`）；manifest 值必须与 `ADR-0002` 的 `.cache/<name>.git`、`.cache/refs/<id>.git` 占位符一致。缓存目录因此为 `.cache/llvm-project.git`、`.cache/refs/DADAO-0628.git`；工作树为 `.work/source/llvm-project`（`LLVM_SRC=.work/source/llvm-project/llvm`）
- **DADAO target 经 `LLVM_ALL_TARGETS` 注册（2026-09-17，ADR-0007）**：DADAO 通过加入 `llvm/CMakeLists.txt` 的 `LLVM_ALL_TARGETS` 列表注册，使 `-DLLVM_TARGETS_TO_BUILD=DADAO` 生效；否决 experimental 通道。`LLVM-003t` 补丁须包含此增项
- **LLVM 基线 = 23.1.1（2026-09-17，ADR-0006）**：lock 值 = commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（`llvmorg-23.1.1` 附注 tag 对象 `e7ce3600…` 仅溯源）；获取源 = SJTU 浅 bare 镜像 `.cache/llvm-project.git`（`--depth 1`，无完整历史，见 ADR-0006 Consequences）；`repository` 仍为 github 规范 URL；M1 期间不 bump
- 角色规则由全局 `opencode/agent/` 提供，工作仓库不含 agent 文件

## 如何参考 DADAO-0628 和 DADAO

- `DADAO-0628`：基于 SimRISC 0.4.1 的完整实现，包含补丁集和任务文件
- `DADAO`：各阶段早期的代码实现（已不再更新），包含 LLVM/QEMU/Chipyard 等组件的具体实现
- 两者 commit 锁定于 `manifests/references.lock.toml`（由 `INFRA-003t` 建立）
- 路线图与任务拆解直接参考 DADAO-0628：`docs/development-roadmap.md`（M0/M1/M2/M2.5）、`code-agent/designs/0002-detailed-roadmap.md`、`code-agent/tasks/`

## 规范版本对应

规范版本与冻结状态的**唯一来源**是 `README.md`「当前版本号」表（SimRISC 0.5.3 / AEE·ABI 0.9.2 / SEE·SBI 0.7.1 / HEE·HBI 0.1.2）。v5 不使用 `manifests/spec.lock.toml`。

## 关键差异提示（相比 DADAO-0628）

DADAO-v5 基于 SimRISC 0.5.3 规范，与 DADAO-0628（锁定在 SimRISC 0.4.1）相比有以下关键差异：

### 0.5.3 vs 0.4.1 的变化

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
