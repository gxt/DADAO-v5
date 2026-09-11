# LLVM-003t: Triple 注册

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-002t`、`SPEC-009t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.work/source/llvm`（`make fetch` 后按 ADR-0005 commit 的干净 checkout）、`components/llvm/patches/series`、`.tao/knowledge/contract-elf.md`（SPEC-009t，ELF header/大端/e_machine/e_flags）
- 输出：
  - `components/llvm/patches/0001-dadao-triple-registration.patch`
  - `components/llvm/patches/0002-dadao-target-skeleton.patch`
  - 更新后的 `components/llvm/patches/series`
  - `Makefile` 的真实 `build-mc`（`LLVM-002t` 已建立，本任务确认可用）
  - 最小 lit 冒烟 `tests/lit/MC/Dadao/triple-smoke.s` + `tests/lit/MC/Dadao/lit.cfg.py`
- 约束：不实现任何指令（不写 `DADAOInstrInfo`/`DADAORegisterInfo`/`.td` 指令）；patch 必须能被 `git am` 干净应用到 `.work/source/llvm`；triple 注册名精确为 `dadao`，full triple `dadao-unknown-elf`；ELF 大端；`e_machine`/`e_flags` 用命名常量或明确取自 `contract-elf.md`，不硬编码无来源数字

## 背景（完整）

### 目标

在 ADR-0005 基线上注册 DADAO triple，构建出能通过 cmake/ninja 的最小空 target，使 `llvm-mc --triple=dadao-unknown-elf` 不报 "unknown target"，并把 `build-mc` 变为真实构建。后续任务（寄存器/指令格式/汇编器/反汇编器）均在此骨架上叠加，故本任务只做注册与 build，不越界。

### 设计理由

- 以 Lanai（`llvm/lib/Target/Lanai/`）为最简完整 target 骨架参考；大型 target（RISCV）可查 MCTargetDesc 结构。
- 先注册 triple 与最小 MCTargetDesc，保证 `llvm-mc`/`llvm-objdump` 可被调用，再逐层填充寄存器与指令。

### 关键概念 / 数据

**Triple 注册**（相对 `llvm-project` 根）：

| 文件 | 改动 |
|------|------|
| `llvm/include/llvm/TargetParser/Triple.h` | `ArchType` 枚举加 `dadao` |
| `llvm/lib/TargetParser/Triple.cpp` | `getArchTypeName`、`parseArch`、`getDefaultFormat` 等补 dadao 条目 |
| `llvm/lib/Target/CMakeLists.txt` | `LLVM_ALL_TARGETS` 加 `DADAO` |

**最小 Target 目录** `llvm/lib/Target/DADAO/`：`CMakeLists.txt`、`DADAO.h`、`DADAOTargetMachine.{h,cpp}`、`TargetInfo/DADAOTargetInfo.{h,cpp}`（`RegisterTarget`，triple `"dadao"`，desc `"DADAO SimRISC"`）、`MCTargetDesc/CMakeLists.txt`、`MCTargetDesc/DADAOMCTargetDesc.{h,cpp}`。

**AsmInfo 存根**：`MCTargetDesc/DADAOMCAsmInfo.{h,cpp}` 继承 `MCAsmInfoELF`，`CommentString = "#"`，大端 `IsLittleEndian = false`（依据 `contract-elf.md` 的 EI_DATA）。

**ELF writer 存根**：`MCTargetDesc/DADAOELFObjectWriter.cpp` 继承 `MCELFObjectTargetWriter`，`getOSABI()`、`getEMachine()`、`needsRelocateWithSymbol()`、`getRelocType()` 按 `contract-elf.md` 取值（`getRelocType()` 可为存根）。

**最小 lit 冒烟**：`triple-smoke.s` 验证 triple 注册成功（AsmParser 缺失时可退化为 `llvm-mc --version | grep dadao`）；`lit.cfg.py` 指向已 build 的 `llvm-mc`。

**构建**：`make prepare` 先 fetch+apply，再 `make build-mc`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-007a-llvm-triple.md`（完整转述：目标、patch 内容、series、Makefile、lit、约束、验收步骤、两轮 Architecture Review）。
- DADAO-0628：`components/llvm/patches/0001-dadao-triple-registration.patch`、`0002-dadao-target-skeleton.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`docs/adr/0003-object-abi.md`、`docs/adr/0005-llvm-baseline.md`。

## 交付物

- `components/llvm/patches/0001-dadao-triple-registration.patch`：Triple 注册（Triple.h/Triple.cpp/CMakeLists.txt）。
- `components/llvm/patches/0002-dadao-target-skeleton.patch`：最小 DADAO target 骨架 + AsmInfo + ELF writer 存根。
- `components/llvm/patches/series`：按序写入 0001、0002。
- `Makefile`：确认 `build-mc` 真实可用（如 `LLVM-002t` 已完成则不重复改动）。
- `tests/lit/MC/Dadao/triple-smoke.s`、`tests/lit/MC/Dadao/lit.cfg.py`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **ELF 常量来源**：`e_machine`/`e_flags`/EI_DATA 以 v5 `.tao/knowledge/contract-elf.md`（SPEC-009t，归一化自 ADR-0003）为准，不照抄 0628 的 `0x0DA0`/`e_flags=0x1` 数值表述；若 v5 沿用同一 `EM_DADAO`，须由 ADR-0003/合约明确，不得在代码里硬编码无来源数字。
- **上游路径**：v5 `.work/source/llvm/llvm`（`INFRA-004t`），构建 `.work/build/llvm`。
- **大端**：0.5.3 指令与数据均大端（`contract-isa.md` §1.5、§2.1），AsmInfo 必须 `IsLittleEndian = false`。
- **triple 名**：v5 同为 `dadao-unknown-elf`，但注册与验证须在 0.5.3 的 AsmInfo/DataLayout 下完成。
- **不复制补丁正文**：0628 的 0001/0002 patch 属 0.4.1 实现，v5 须按 0.5.3 重新生成；只参考其命名与 series 顺序。

## 已知坑 / 结论

- **AsmParser 缺失时 lit 退化为 `--version | grep dadao`**：0628 `DL-007a` 因缺 AsmParser，冒烟测试改为验证 `llvm-mc --version` 输出含 `dadao`；v5 同样处理，待 `LLVM-006t` 引入汇编解析后再补 assembly 测试。
- **MCInstPrinter 存根必需**：`llvm-mc` 运行期要求非空 printer，否则崩溃。
- **`EM_DADAO` 命名常量**：0628 第二轮 N1 指出直接硬编码 `0x0DA0`；v5 应引用命名常量或合约值，避免魔数。
- **大端 DataLayout**：若 DataLayout 写成 `e`（小端）会导致字节序错误，须确认 `E`（大端）。
- **patch 必须干净 apply**：0001→0002 顺序应用后 `ninja llvm-mc` 成功。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-007a-llvm-triple.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0003-object-abi.md`
- DADAO-0628：`.work/DADAO-0628/Makefile`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-elf.md`（SPEC-009t 产出后）、`verif/opcodes.yaml`

## 验收标准

1. 0001、0002 两个 patch 存在，且按序写入 `components/llvm/patches/series`
2. `make prepare && make build-mc` PASS（cmake configure + ninja llvm-mc）
3. `llvm-mc --version` 的 Registered Targets 含 `dadao - DADAO`（或不报 unknown target）
4. 若 AsmParser 尚未实现（本任务边界）：`llvm-mc --version` 的 Registered Targets 含 `dadao`；否则 `llvm-lit tests/lit/MC/Dadao/triple-smoke.s` PASS
5. 未定义任何指令/寄存器 `.td`（本任务边界）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
