# SPEC-007t: ELF 合约（M1：头 + 段/流水线）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-005t`、`SPEC-002t`
**状态**：已验证

## 范围（2026-09-12 变更）

- **M1 = §1 + §5 + §6**：ELF 头字段、段对齐/VA=PA、端到端 artifact pipeline。
- **§2/§3/§4（重定位类型/溢出/relaxation）标 `Deferred to M2`**：与 `SPEC-005t` 同步（M1 单 TU 自包含、不产生重定位、无 LLD）。见 `.tao/knowledge/deferred.md`。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/adr-0003-object-abi.md`（SPEC-005t，**唯一决策来源**）
  - `.tao/knowledge/contract-isa.md`（0.5.3，指令格式/字段宽度的 oracle）
- 输出：`.tao/knowledge/contract-elf.md`
- 约束：
  - ADR-0003 是唯一来源：所有值直接从 ADR 复制，不重新推导；ADR 与 ISA 冲突时暂停并报告，不自行解决
  - 与现有合约（`contract-isa.md`）风格一致；每条规则在段落内写明约束和例外
  - 不与 ISA 合约重复：指令格式/编码细节引用 `contract-isa.md §N`，不粘贴复制
  - 不引用行号：只用章节号（§N）或 ADR 决策点（§DN）
  - 合约完备：每条重定位有完整 S/A/P 公式与溢出策略，不留「见 ADR」内联空引用
  - 完成后不自行 commit

## 背景（完整）

### 目标

产出 `.tao/knowledge/contract-elf.md`，将 `.tao/knowledge/adr-0003-object-abi.md`（ADR-0003）的 **M1 ELF 决策（D1 头字段 + D5 段/流水线）**规范化为与 `contract-isa.md`、`contract-abi.md` 风格一致的合约文件（§1 + §5 + §6）。本合约成为后续 LLVM MC ELF emitter 与 QEMU loader 的 M1 oracle；**重定位（D2/D3/D4）标 `Deferred to M2`**。

### 设计理由

- ADR 是决策记录（Context/Decision/Consequences），合约是可供实现直接消费的规范化投影；
  二者分离避免实现从 ADR 叙述反推。
- 合约必须可独立阅读：字段宽度/位置、S/A/P 公式、溢出策略须完整，不能靠跳转 ADR 补全。
- 来源字段引用 ADR-0003（`spec/` 无 ELF 内容），不引用 spec commit。

### 关键概念 / 数据

**§1 ELF Header Fields**：`EI_CLASS`、`EI_DATA`、`e_machine`、`e_flags`、`EI_OSABI` 的冻结值及含义
（来源 ADR-0003 §D1）。

**§2（`Deferred to M2`）Relocation Types**：完整重定位表（编号、名称、字段宽度/位置、S/A/P 公式、适用指令、溢出策略）
+ 每类型推导说明（来源 ADR-0003 §D2）。0.5.3 下的适用指令映射：

| 重定位 | 0.5.3 适用指令 | 字段 |
|--------|---------------|------|
| `R_DADAO_64` | `.quad`/指针数据、`set.zw`/`or.w` 构造的地址（rwii） | **绝对 64-bit 数据地址**；数据节 8 字节 @ P；`set.zw`/`or.w` 每次 16 位（**不单列 wyde 地址构造场景**） |
| `R_DADAO_PCREL18` | `br.n/br.nn/br.z/br.nz/br.p/br.np`（riii） | imms18 **字偏移** `<<2` @ bits[17:0]；有效字节范围 ±2¹⁹（±512 KiB） |
| `R_DADAO_PCREL12` | `br.eq`/`br.ne`（rrii） | imms12 字偏移 `<<2` @ bits[11:0]；±2¹³（±8 KiB） |
| `R_DADAO_PCREL24` | `call imms24`/`jump imms24`（iiii） | imms24 字偏移 `<<2` @ bits[23:0]；±2²⁵（±32 MiB） |
| `R_DADAO_RELA` | `rela.si`（riii） | imms18 **直接 `<< 12`**（12 位偏移，30 位有符号）；PC 低 12 位清零得 **4KB 对齐**（**与页无关**）、无 `<<2` |

> 上表 `R_DADAO_*` 为 **legacy（0628）命名，仅作对照**；M1 **不冻结**重定位编号/公式，完整命名/编号留 `LLVM-012t`（M2），不得据本表臆造。**约定**：绝对地址（含 `set.zw`/`or.w` 构造）统一归入「绝对 64-bit 数据地址」，不单列 wyde 地址构造场景；**相对分支/call/jump** 立即数均为字偏移，重定位须 `<<2`，有效字节范围 = 立即数位宽 + 2 位；**`rela.si` 例外**——立即数直接 `<< 12`（12 位偏移），PC 低 12 位清零得 4KB 对齐，与页无关、无 `<<2`（来源 ADR-0003 §D2）。

**§3（`Deferred to M2`）Overflow Policy**：两级策略表（`R_DADAO_64`，含 `set.zw`/`or.w` 构造的绝对地址，无溢出；有界类型 link-time error）。

**§4（`Deferred to M2`）Relaxation**：M1 禁止 relaxation 的正式声明及约束。

**§5 Section Alignment**：`.text`/`.rodata`/`.data`/`.bss` 最小对齐、VA=PA 规则。

**§6 Artifact Pipeline**：M1 端到端 artifact 路径（ET_REL `.o` → `llvm-objcopy --only-section=.text -O binary` → flat binary → QEMU），**无静态链接、无 ET_EXEC、无 LLD**；**单 TU 自包含**（段内标签就地解析、不产生重定位）；若 M1 用例需要 `.rodata`/`.data`，以同一 `objcopy` 机制提取并按 8B 对齐**连续拼接**（顺序 `.text → .rodata → .data`）；与 ADR-0004（SPEC-006t）的加载模型一致。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-004a-elf-contract.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`contracts/elf/spec.md`（内容溯源：最终 Accepted 内容；合约格式见 v5 `.tao/knowledge/contract-authoring.md`）
- DADAO-0628：`contracts/elf/README.md`
- DADAO-0628：`docs/adr/0003-object-abi.md`（归一化来源）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `.tao/knowledge/contract-elf.md` | M1 ELF 合约，归一化自 ADR-0003：**§1 头字段 + §5 段对齐 + §6 流水线**；§2/§3/§4 重定位标 `Deferred to M2`。Status 先 Candidate（review 通过后 Accepted） |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **来源版本**：ADR-0003 从 0.4.1 决策改为 v5（SPEC-005t）的 0.5.3 决策；合约版本应与 v5 一致。
2. **指令助记符**：`setzw`/`orw` → `set.zw`/`or.w`；`brn/brz/…` → `br.n/br.z/…`；
   `breq/brne` → `br.eq`/`br.ne`；`rela` → `rela.si`；`call`/`jump` iiii 形式不变。
3. **重定位集**：0.4.1 初版 9 型、后补 PCREL12 为 10 型；v5 应从一开始就含 `R_DADAO_PCREL12`
   （对应 0.5.3 `br.eq`/`br.ne`）。
4. **e_flags**：0.4.1 曾出现 contract `e_flags=1` 与 ADR `e_flags=0` 的冲突，须先改 ADR 再改合约；
   v5 以 SPEC-005t 冻结值为准：`e_flags[7:0] = 1`（M1 对象/ABI 格式版本），bits 8–31 保留为 0；consumer 拒绝版本未知/不匹配或保留位非 0。
5. **e_machine 说明**：不得声称 `EM_DADAO` 已注册 upstream LLVM；应为 project-custom。
6. **LLD scope**：0.4.1 曾把 Post-M2 的 LLD 写成 M1 必需依赖；v5 须区分 object ABI 与
   test-machine load contract，明确 M1 是否使用 target linker。
7. **artifact pipeline**：`QEMU -kernel flat.bin` 不得被称为「ELF loader」；须与 ADR-0004 冻结的
   双镜像（`-bios trampoline.bin` + `-kernel flat.bin`）命令一致。

## 已知坑 / 结论

摘自 DL-004a 三轮 Architecture Review：

1. **P0 e_flags 值与 ADR 冲突**：合约不得在 ADR 之外单向改变决策；若需修订，先更新 ADR 再同步合约。
2. **P0 前置 ADR 未 Accepted**：004a 不能把 Candidate 且内部不一致的 ADR 规范化为唯一 oracle；
   须先完成 SPEC-005t/SPEC-006t review 并升级 ADR 状态。
3. **P0 §6 把 Post-M2 LLD 变成 M1 必需依赖**：须二选一——保持 roadmap（raw/section extraction）
   或扩展 M1 scope 新增 DADAO LLD backend 任务；不能只改合约。
4. **P0 §6 与 ADR-0004 启动命令不一致**：须引用唯一完整命令/镜像对，并区分 object ABI 与
   test-machine load contract。
5. **P1 PCREL12 的 §3 来源不成立**：合约 §3 自行补的 PCREL12 overflow 行须先在 ADR §D3 补齐，
   保持合约 §3 为机械规范化结果。
6. **P1 e_machine 错误声明传播**：`e_flags[7:0]=1` 只供更新的 consumer 区分 namespace，不保证旧
   consumer 检查并拒绝。
7. **最终结论**：第三轮 Accepted（ADR-0003/0004 Status 升级、e_machine 说明修正、补 PCREL12
   overflow 行、§6 补 `-bios`、PCREL12 标 ADR extension）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-004a-elf-contract.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/contracts/elf/spec.md`
- DADAO-0628：`.work/DADAO-0628/contracts/elf/README.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0003-object-abi.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）
- 本项目：`.tao/knowledge/adr-0003-object-abi.md`（SPEC-005t 产出）、`.tao/knowledge/contract-isa.md`
- DADAO-0628：`code-agent/tasks/DL-004a-elf-contract.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.tao/knowledge/contract-elf.md` 存在，Status 先 Candidate，来源指向 ADR-0003（SPEC-005t 产出）（前提：SPEC-005t/SPEC-006t review 已通过、ADR-0003/0004 Status=Accepted）
2. **§1 + §5 + §6 覆盖**（头字段、段对齐/VA=PA、artifact pipeline），无空白或「见 ADR」占位；§1 冻结 5 个 ELF 头字段
3. **§2/§3/§4（重定位类型/溢出/relaxation）明确标 `Deferred to M2`**，不与 M1 内容混排（可作登记/参考）
4. §5 给出各段最小对齐与 VA=PA
5. §6 artifact pipeline 与 ADR-0003（D5，含多段提取连续拼接与单 TU 自包含）及 ADR-0004（SPEC-006t）冻结的启动命令/镜像对一致；不把 QEMU flat loader 称为 ELF loader（前提：SPEC-005t/SPEC-006t review 已通过、ADR-0003/0004 Status=Accepted）
6. 每章节有 `[ADR-0003 §DN]` 来源标注；不引用行号
7. 合约可独立阅读：不出现「见 ADR」式的内联空引用
8. 不声明 `EM_DADAO` 已注册 upstream；命名空间/版本策略与 ADR 一致

## 完成区

**测试结果**：通过 40/40；失败原因：无。验证脚本 `/tmp/opencode/SPEC-007t/check_contract_elf.py`（结构/来源标注/格式检查），完整输出 `.tao/logs/SPEC-007t-check_contract_elf.log`（TOTAL: 40/40）。

**修改文件**：
- `.tao/knowledge/contract-elf.md`（新建，165 行）——M1 ELF 合约，归一化自 ADR-0003：§1 头字段 + §5 段对齐/VA=PA + §6 流水线；§2/§3/§4 标 `Deferred to M2`；Status=Candidate。
- `.tao/tasks/spec/SPEC-007t-ELF合约.md`（状态 `待开始`→`待验收`；填完成区 + 第 1 轮 engineer 自审）。

**验收结果**（真实输出摘要）：
- 结构检查 40/40 PASS（文件存在、Status=Candidate、§1/§5/§6 章节、§2/§3/§4 标 `Deferred to M2`、5 个头字段、e_flags 修订值、consumer 拒绝表、每章 `[ADR-0003 §DN]` 来源、无行号、无「见 ADR」占位、无 spec 版本头、§6 各要素、§5 对齐 4 段 + VA=PA、引用 contract-isa/abi §N）。
- 关键要素核对：`llvm-objcopy --only-section=.text -O binary`；`不引入 target linker（LLD）`/`不产生 ET_EXEC`；拼接顺序 `.text → .rodata → .data` + `按 8B 对齐`；`单 TU 自包含`；`不得把 QEMU 的 flat binary 加载称为「ELF loader」`；启动命令 `qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin`；`e_entry 不被 test machine 读取`。
- 前置条件已核实：`SPEC-005t`/`SPEC-006t` 状态=已验证；ADR-0003/ADR-0004 Status=Accepted。
- ADR 与 ISA 冲突核查：无冲突（大端、.text 4B、.rodata/.data 8B 均与 `contract-isa.md §1.6/§2.1/§4.1.1`、`contract-abi.md §1.7` 一致），未触发「暂停并报告」。

**新发现/坑**：
1. **任务书 §2 的 legacy `R_DADAO_*` 表不在 ADR-0003 中**：按「ADR-0003 唯一决策来源」，未把该表纳入合约（纳入将违反唯一来源、且任务书自身也标其「仅作对照、不得臆造」）；§2 改用 ADR-0003 §D2 的**场景登记表**（0.5.3 指令格式），并显式声明 M1 不定义/不冻结任何重定位编号/公式。
2. **SPEC-008t drift checker 的合约分类**：合约分 `spec-sourced`（含 `> **版本：X.Y.Z**` 头）与 `ADR-sourced`（来源标注引用 `adr-000N-*.md`）。`contract-elf.md` 为 ADR-sourced，故**不加** `> **版本：**` 头，避免被误分类为 spec-sourced 并要求 README 版本表匹配。任务书「合约版本应与 v5 一致」在本合约体现为「基线 = ADR-0003 rev. 2026-09-13」。
3. **任务书约束「每条重定位有完整 S/A/P 公式与溢出策略」与 ADR-0003 D2/D3/D4 全 Deferred 冲突**：按 ADR 唯一来源规则，§2–§4 明确声明 M1 无重定位、无公式（非占位）；不自行补 PCREL12 overflow 行（与任务书已知坑 #5「§3 须为机械规范化结果」一致）。
4. **e_flags 归一化**：用 ADR-0003 修订值 `e_flags[7:0]=1`（数值 `0x00000001`）+ bits 8–31 保留 0；未沿用旧 `e_flags=0x1`（1 位标志）表述。
5. **EM_DADAO 注册状态**：显式写「未注册 IANA/SysV/LLVM 主线、不声称已注册 upstream、project-custom」，碰撞风险由 `e_flags` 版本字段缓解。

**遗留问题**：无阻塞项。待 reviewer 确认项：§2–§4 因 ADR-0003 全 `Deferred to M2`，未含 legacy `R_DADAO_*` 编号/S-A-P 公式（见「新发现/坑」#1、#3），此为遵循「ADR-0003 唯一来源」的有意结果。**接口约束裁决**：任务书「每条重定位有完整 S/A/P 公式与溢出策略」在 M1 不适用（D2/D3/D4 全 Deferred）；M2（`LLVM-012t`）冻结重定位时再补公式。

> **注（2026-09-14，主会话）**：engineer 完成后，主会话按 ADR-0003 **rev. 2026-09-14** 更新了 `contract-elf.md` §2（绝对地址并入 `R_DADAO_64`；相对分支/call/jump `<<2`、有效范围=位宽+2；`rela.si` `<<12`、PC 低 12 位清零得 4KB 对齐、**与页无关**、无 `<<2`）及来源行（补 `rev. 2026-09-14`）。上方完成区行数留痕（165）以更新后为准。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：自主逐行审查 `contract-elf.md`（165 行），并与 ADR-0003（D1/修订/D2/D3/D4/D5/Context/Consequences）逐条对照；运行结构/来源/格式检查脚本（40/40）。

**findings 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：任务书 §2 列 legacy `R_DADAO_*` 重定位表，但 ADR-0003 §D2 无该表（仅场景登记） | ❌不修 | 不纳入 legacy 编号；§2 用 ADR §D2 场景登记表 | ADR-0003 §D2 表 6 行与合约 §2 表 6 行逐字一致；脚本 `§2 marked Deferred`/`§2 has ADR-0003 §DN source` PASS |
| F2：任务书约束「每条重定位有完整 S/A/P 公式与溢出策略」与 D2/D3/D4 全 Deferred 冲突 | ❌不修 | §2/§3 显式声明 M1 无重定位/无公式，不臆造 PCREL12 overflow 行 | §3 与 ADR §D3 逐字一致（无 PCREL12 行）；脚本 PASS |
| F3：任务书差异 #1「合约版本应与 v5 一致」，但本合约无 `版本：X.Y.Z` 头 | ❌不修 | 以「基线 = ADR-0003 rev. 2026-09-13」体现来源版本 | 脚本 `no spec version header` PASS；避免 drift checker 误分类（见完成区坑 #2） |
| F4：首轮检查脚本 7 项 FAIL（`no line-number refs`、6×`§DN source`） | ✅已修（脚本 bug） | 修正脚本：按 `## §N ` 标题切分章节；行号检查排除「不写行号」说明 | 重跑 40/40 PASS（日志已更新） |
| F5：e_flags 旧表述 `e_flags=0x1`（1 位标志） | ✅已修 | §1.1/§1.3/§2 统一为 `e_flags[7:0]=1`、数值 `0x00000001`、bits 8–31 保留 0 | 脚本 `e_flags[7:0] version field`/`bits 8-31 reserved`/`e_flags numeric 0x00000001` PASS |
| F6：EM_DADAO 注册状态可能被误述 | ✅已修 | §1.2 显式「未注册/不声称已注册 upstream/project-custom」 | 脚本 `not registered upstream`/`no false-registered claim` PASS |
| F7：§6 须完整体现 D5 的多段拼接与单 TU 自包含 | ✅已修 | §6.1 三条（步骤1 自包含定义 + 步骤2 objcopy + 多段 8B 对齐拼接 `.text → .rodata → .data`）；§6.2 与 ADR-0004 启动命令；§6.3 约束 | 脚本 `multi-section concat order`/`8B align concat`/`single TU self-contained`/`boot command frozen`/`flat binary not ELF loader` PASS |

**判决**：**Accepted（engineer 自审）**。无未修阻塞 finding；40/40 结构/来源检查通过；所有取值逐条溯源自 ADR-0003，无行号、无「见 ADR」占位、无 EM_DADAO 注册误述。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑验证脚本 + 逐条手动核对 `contract-elf.md` 与 `adr-0003-object-abi.md`（含 `## 修订`）。

##### 一、独立重跑验证脚本

```bash
python3 /tmp/opencode/SPEC-007t/check_contract_elf.py 2>&1; echo "EXIT_CODE=$?"
```

真实输出（全部 40 项 PASS，exit code 0）：

```
[PASS] file exists & non-empty
[PASS] Status Candidate
[PASS] §1 section header
[PASS] §5 section header
[PASS] §6 section header
[PASS] §2 marked Deferred
[PASS] §3 marked Deferred
[PASS] §4 marked Deferred
[PASS] header field EI_CLASS
[PASS] header field EI_DATA
[PASS] header field e_machine
[PASS] header field e_flags
[PASS] header field EI_OSABI
[PASS] e_flags numeric 0x00000001
[PASS] e_flags[7:0] version field
[PASS] bits 8-31 reserved
[PASS] consumer reject table rows
[PASS] not registered upstream
[PASS] no false-registered claim
[PASS] no line-number refs
[PASS] no 'see ADR' placeholder
[PASS] §1 has ADR-0003 §DN source
[PASS] §2 has ADR-0003 §DN source
[PASS] §3 has ADR-0003 §DN source
[PASS] §4 has ADR-0003 §DN source
[PASS] §5 has ADR-0003 §DN source
[PASS] §6 has ADR-0003 §DN source
[PASS] no spec version header
[PASS] llvm-objcopy section extraction
[PASS] no LLD
[PASS] multi-section concat order
[PASS] 8B align concat
[PASS] single TU self-contained
[PASS] flat binary not ELF loader
[PASS] boot command frozen
[PASS] e_entry not consumed
[PASS] alignment table 4 sections
[PASS] VA=PA
[PASS] references contract-isa §N
[PASS] references contract-abi §N

TOTAL: 40/40
EXIT_CODE=0
```

##### 二、逐条手动核对

**§1 五个头字段值 vs ADR-0003 D1**：

| 字段 | ADR-0003 D1 | contract-elf §1.1 | 一致 |
|------|-------------|-------------------|------|
| `EI_CLASS` | `ELFCLASS64 = 2` | `ELFCLASS64 = 2` | ✓ |
| `EI_DATA` | `ELFDATA2MSB = 2` | `ELFDATA2MSB = 2` | ✓ |
| `e_machine` | `EM_DADAO = 0x0DA0` project-custom | `EM_DADAO = 0x0DA0` project-custom，显式「未注册 upstream」 | ✓ |
| `e_flags` | `0x00000001`，bits 0–7 版本号=1，bits 8–31 保留 0 | 同 + consumer 拒绝表 4 行一致 | ✓ |
| `EI_OSABI` | `ELFOSABI_NONE = 0` | `ELFOSABI_NONE = 0` | ✓ |

**§2 修订后场景登记表 vs ADR-0003 D2 + rev. 2026-09-14**：

| 场景行 | ADR-0003 D2 表 | contract-elf §2 表 | 一致 |
|--------|---------------|-------------------|------|
| 绝对 64-bit（含 set.zw/or.w） | 64 位；不单列 wyde 地址构造 | 同 | ✓ |
| PC 相对短程分支（imms18） | `<<2`；18+2 → ±2¹⁹ | `<<2`；18+2 → ±2¹⁹ | ✓ |
| PC 相对双寄存器分支（imms12） | `<<2`；12+2 → ±2¹³ | `<<2`；12+2 → ±2¹³ | ✓ |
| PC 相对 call/jump（imms24） | `<<2`；24+2 → ±2²⁵ | `<<2`；24+2 → ±2²⁵ | ✓ |
| PC 相对地址加载（rela.si） | `<< 12`；无页概念、无 `<<2` | `<< 12`；无页概念、无 `<<2` | ✓ |

表下方约定段：「绝对地址统一归入…不单列 wyde」+「相对分支/call/jump `<<2`，有效字节范围=位宽+2」+「`rela.si` 例外 `<<12`、无页概念、无 `<<2`」——逐字与 ADR-0003 rev. 2026-09-14 一致。✓

**§5 段对齐 + VA=PA vs ADR-0003 D5**：

- `.text` 4B / `.rodata` 8B / `.data` 8B / `.bss` 8B —— 与 ADR-0003 D5 表逐行一致 ✓
- VA=PA（freestanding 无 MMU，VMA=PA）—— 一致 ✓
- 有效地址 48 位——一致 ✓

**§6 artifact pipeline vs ADR-0003 D5 + ADR-0004**：

| 要素 | ADR-0003/0004 | contract-elf §6 | 一致 |
|------|--------------|-----------------|------|
| ET_REL `.o` → `llvm-objcopy --only-section=.text -O binary` → flat | ✓ | ✓ | ✓ |
| 无 LLD / 无 ET_EXEC | ✓ | ✓ | ✓ |
| 单 TU 自包含（不产生重定位） | ✓ | ✓ | ✓ |
| 多段拼接 `.text → .rodata → .data` + 8B 对齐 | ✓ | ✓ | ✓ |
| `e_entry` 不被 test machine 读取 | ✓ | ✓ | ✓ |
| flat binary ≠ ELF loader | ✓ | ✓ | ✓ |
| 启动命令 `qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin` | ADR-0004 §D2.3 | ✓ | ✓ |

**§2/§3/§4 标 `Deferred to M2`**：三节标题均含 `` `Deferred to M2` ``，内容为 M1 不产生重定位的声明（非空白占位）。✓

**每章 `[ADR-0003 §DN]` 来源标注**：§1→§D1、§2→§D2、§3→§D3、§4→§D4、§5→§D5、§6→§D5+§Context+§Consequences；附录 A 汇总表完整。✓

**无行号**：全文无 `L123`/`第N行`/`line N` 形式引用。✓

**无「见 ADR」空引用**：全文无「见 ADR」内联占位。✓

**`EM_DADAO` 注册状态**：§1.2 显式「未注册于 IANA/SysV 公共 ELF registry」「不存在于 LLVM 主线」「不声称已注册 upstream」「project-custom」。✓

**ADR-0003 与 ISA/ABI 冲突核查**：大端、.text 4B 对齐、.rodata/.data 8B 对齐均与 `contract-isa.md §1.6/§2.1/§4.1.1`、`contract-abi.md §1.7` 一致，无冲突。✓

##### 三、约束守备清单

| 约束 | 结果 | 说明 |
|------|------|------|
| Status=Candidate | ✓ | 文件头 `**状态**：Candidate` |
| 来源指向 ADR-0003 | ✓ | 文件头 + 每章 `[ADR-0003 §DN]` |
| §1 冻结 5 个头字段 | ✓ | EI_CLASS/EI_DATA/e_machine/e_flags/EI_OSABI |
| e_flags[7:0]=1 + bits8-31=0 | ✓ | `0x00000001`，consumer 拒绝表完整 |
| e_machine project-custom | ✓ | 「未注册 upstream」「project-custom」 |
| §2/§3/§4 Deferred to M2 | ✓ | 标题含 `Deferred to M2`，非空白 |
| §5 段对齐 4 段 + VA=PA | ✓ | 与 ADR-0003 D5 逐行一致 |
| §6 pipeline 无 LLD/ET_EXEC | ✓ | 显式声明 |
| §6 多段拼接顺序+8B 对齐 | ✓ | `.text → .rodata → .data` + 8B |
| §6 单 TU 自包含 | ✓ | 含术语展开定义 |
| §6 e_entry 不参与 | ✓ | 「不被 test machine 读取」 |
| §6 flat binary ≠ ELF loader | ✓ | 显式声明 |
| §6 启动命令=ADR-0004 双镜像 | ✓ | `-bios rom.bin -kernel test.bin` |
| §2 场景表=ADR-0003 D2 | ✓ | 5 行逐字一致（含 rev. 2026-09-14） |
| §2 绝对地址并入 R_DADAO_64 | ✓ | 不单列 wyde 地址构造行 |
| §2 相对分支/call/jump `<<2` | ✓ | 有效字节范围=位宽+2 |
| §2 rela.si `<<12` 无页无 `<<2` | ✓ | 显式声明 |
| 每章 [ADR-0003 §DN] 来源 | ✓ | 六节均有 |
| 无行号 | ✓ | — |
| 无「见 ADR」空引用 | ✓ | — |
| 不声明 EM_DADAO 已注册 upstream | ✓ | — |

##### 四、判决

**Accepted**。

- 验证脚本 40/40 PASS（exit code 0），与 engineer 转述一致。
- 逐条手动核对 §1 五字段、§2 场景表（含 rev. 2026-09-14 修订）、§3/§4 Deferred、§5 段对齐/VA=PA、§6 pipeline 全部与 ADR-0003（含 `## 修订`）一致。
- 无凭空编造、无与 ADR/spec 不符之处。
- 任务书验收标准 8 条全部满足。

