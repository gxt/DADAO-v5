# TESTCASES-004t: load/store 向量（RD/RB/RA 三 bank）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/rd-load-store.yaml`（`TESTCASES-002t` 产出：`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 encoding/semantic/boundary/legality）
  - `tests/vectors/isa/rb-ops.yaml` 的访存 case（`ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb`）
  - `tests/vectors/isa/ra-ops.yaml` 的访存 case（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）
  - `tests/vectors/schema.md`（`TESTCASES-002t` 返工后）
  - `contracts/opcodes.yaml`（访存指令编码字段 `fields`；`op=value>>24`、`ha=(value>>18)&0x3f`）
  - `contracts/legality_rules.yaml`（`rd_dest_rd0`/`store_src_rd0`/`rb_dest_rb0`/`rb_base_rb0_store`/`multi_immu6_zero`）
  - `.tao/knowledge/contract-isa.md` §4.1/§4.2/§4.9（load/store 合法性、对齐、RA 存取）、§2.2（格式）
  - `.tao/knowledge/adr-0004-test-machine.md`（D1 内存映射、D5.6 访问矩阵、D6.5 入口状态）
- 输出（**本任务拥有的文件**，`tests/vectors/isa/`）：
  - `mem-rd.yaml`、`mem-rb.yaml`、`mem-ra.yaml`
- 约束：
  - 期望值**手工派生自 `contract-isa.md`/`spec/`/ADR-0004**，不得从 LLVM/QEMU 反推
  - 覆盖率主键 `(insn, format)`；M1 scope 以 `excluded_m1 != true` 为准
  - **只动本任务拥有的三个目标文件与所涉源文件（`rd-load-store.yaml`/`rb-ops.yaml`/`ra-ops.yaml`）**；**不改** `contracts/`；**不改** `reg-*`/`ctrl-*`/`misc`
  - 完成后不自行 commit

## 任务范围

### 1. 文件重组（旧 → 新；只描述目标）

| 动作 | 内容 |
|---|---|
| 新建 `mem-rd.yaml` | `rd-load-store.yaml` 改名（`ld.*`/`st.*`/`ldm.*`/`stm.*` 的 RD 变体） |
| 新建 `mem-rb.yaml` | 从 `rb-ops.yaml` 拆出 `ld.o-rb`/`st.o-rb`/`ldm.o-rb`/`stm.o-rb` |
| 新建 `mem-ra.yaml` | 从 `ra-ops.yaml` 拆出 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` |
| 删除 | `rd-load-store.yaml`、`rb-ops.yaml`、`ra-ops.yaml`（后两者的非访存 case 已由 `003t` 移走） |

- **前置**：`003t` 已把 `rb-ops.yaml` 的 `add.so-rb`/`sub.so-rb`、`ra-ops.yaml` 的 `ra2rd`/`rd2ra` 移入 `reg-*`；本任务只处理剩余访存 case，移出后删除空文件。
- 三个文件合并了三种 bank（RD/RB/RA）的访存指令，但**按目标文件分组**（`mem-rd`/`mem-rb`/`mem-ra`），即「按 bank 分文件」的访存子集。

### 2. F10：访存 encoding 向量的内存语义重设计（本任务核心）

- **现状诊断**：`002t` 交付的访存 encoding 向量存在两类缺陷（以 `ld.ub-rd` word=`0x10000000` 为例）：
  1. **操作数字段全 0**：`rdha`（目的）= `rd0` → **ILLI**（`rd_dest_rd0`）；`st.*` 的 `rdha`（源）= `rd0` → **ILLI**（`store_src_rd0`）；`rbha` base = `rb0` → **ILLI**（`rb_base_rb0_store`）；multi load/store `immu6` = 0 → **ILLI**。
  2. **`input_state: {}`**：即使 base 字段非 `rb0`，未预置基址寄存器 → 地址 0 → **unmapped（`0x87`）**；而 `expected_fault: null`，自相矛盾。
- **方案 B（采用）：使用有效 RAM 基址**：
  - `input_state` 预置 `rb1 = 0x0000ffff00000000`（ADR-0004 RAM 基址 = `BINARY_BASE`，48-bit）；
  - 编码中 base 字段 = `rb1`（非 `rb0`），dest = `rd1`（非 `rd0`），store 源 = `rd1`（非 `rd0`）；
  - `expected_state: null`、`expected_fault: null`、`status: active`；加载合法 RAM 地址；
  - multi load/store 的 `immu6`（count）≥ 1（=0 → ILLI）。
- **方案 A（备选，仅登记，不采用）**：dest `rdha=rd0` → `expected_fault: ILLI`；只验证「非法目的被拒」，未验证合法路径，故不采用。
- **字段模式**（结构参考，具体 `encoding.word` 由 `contracts/opcodes.yaml` 的 `op`/`ha` 与 §2.2 公式手算）：
  - 单 load：`ha(dest)=rd1`、`hb(base)=rb1`、`imms12=0`；
  - 多 load/store：在单 load 模式上令 `immu6=1`（count=1）；
  - 所有访存 encoding 的 `input_state` 预置 `rb1 = 0x0000ffff00000000`。
- **约束**：
  - 基址必须指向 RAM 合法地址，**不得**用 addr=0 / 未映射地址；
  - 若预置基址寄存器与 harness 的 SP（`rb1 = 0x0000ffff00ff0000`，ADR-0004 D6.5）冲突，须在 notes 说明并改用不冲突的寄存器；
  - RA 存取（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）：目的为 RA 组，按 §4.9 与 `contract-isa.md` 的 RA 存取规则填字段；不得用 `ra0`/非法 count；
  - 每条 encoding case `expected_state: null`、`expected_pc: null`、`expected_fault: null`、`status: active`。
- **F10 范围**：本任务只修**访存** encoding；`reg-*`/`ctrl-*`/`misc` 的 encoding 由对应任务负责。

### 3. 语义/边界/合法性向量

- 保留并复核 `mem-*` 的 semantic/boundary/legality case：地址落在 ADR-0004 RAM 区、无 `rd0`/`rb0` 条目、对齐 fault（MALIGN/IALIGN）与 unmapped（`0x87`）期望正确。
- 期望值仍须手工派生；不采用 0628 的 `0x8000_0000`/`0x0010_0000` 地址图。

## 验收标准

1. `mem-rd.yaml`/`mem-rb.yaml`/`mem-ra.yaml` 存在，覆盖全部访存 M1 身份（含 RA 存取 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）
2. `rd-load-store.yaml`/`rb-ops.yaml`/`ra-ops.yaml` 已删除；非访存 case 不丢失（由 `003t` 承接）
3. 全部访存 encoding 向量 `status: active`、`expected_fault: null`、`expected_pc: null`
4. 每条访存 encoding 的 `input_state` 含 RAM 合法基址（如 `rb1 = 0x0000ffff00000000`），dest 非 `rd0`、base 非 `rb0`、store 源非 `rd0`
5. multi load/store 的 `immu6 ≥ 1`
6. 每条 `encoding.word` 与 `contracts/opcodes.yaml` 的 `(word & mask) == value` 一致
7. **每条访存 encoding case 经语义推演确认「可解码执行且不触发任何 fault」**（不 ILLI/unmapped）；给出字段值 + 依据章节
8. semantic/boundary 地址落在 ADR-0004 RAM 区；`input_state` 无 `rd0`/`rb0` 条目
9. 未改 `contracts/`；未动 `reg-*`/`ctrl-*`/`misc`
10. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
11. （下游）QEMU harness 就绪后，该文件全部 active 测试 PASS、0 timeout
12. 未自行 commit

## 背景（完整）

### 目标

将访存向量按 RD/RB/RA 三 bank 重组为 `mem-rd`/`mem-rb`/`mem-ra`，并把访存 encoding 从「零地址/未预置基址的 unmapped 访问」重新设计为**合法可执行的 active 测试**。

### 设计理由

- 访存是唯一跨三个 bank（RD/RB/RA）的运算族；按 bank 拆文件使 bank 语义（RD 地址、RB base、RA 目的）集中，便于逐 bank 审计。
- `encoding` 类定义为「可解码执行无 fault」，故 encoding 向量必须避开 `rd0`/`rb0`/`immu6=0` 与未映射地址。

### 关键概念 / 数据

- **编码公式**：`word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`；`op=value>>24`、`ha=(value>>18)&0x3f`。
- **内存映射（ADR-0004 D1）**：boot ROM `0xffff_ffff_0000`（64 KiB，只读）、RAM `0xffff_0000_0000`–`0xffff_00ff_ffff`（16 MiB，读写）、Exit port `0xffff_8000_0000`；`BINARY_BASE` = RAM 起始。0628 的 `dadao-virt` 布局（`0x8000_0000` 等）**不适用**。
- **addr=0 语义**：ADR-0004 D5.6 → unmapped `0x87`（确定性）；不是 hang、不是 ILLI。
- **RA 存取**：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` 属 M1（`contract-isa.md` §4.9）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`、`DL-022c`（内存地址 ROM→RAM）（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符**：`ldbs`/`ldbu`/… → `ld.sb`/`ld.ub`/…（`insn` 带 `-rd`/`-rb`/`-ra` 后缀）。
2. **内存映射**：以 ADR-0004 为准（RAM `0xffff_0000_0000`）；0628 的 `RAM 0x8000_0000`/`ROM 0x0010_0000` **不得使用**。
3. **addr=0 语义**：unmapped `0x87`（确定性）；0628 的 QEMU hang **不适用**。
4. **编码字段**：以 `contract-isa.md` §2.2 与 `contracts/opcodes.yaml` 的 `fields` 为准。
5. **RB 语义**：0.5.3 有效地址低 48 位。
6. **多寄存器**：`immu6`（count）仍须 ≥1。

## 已知坑 / 结论

1. **addr=0 未映射**：ADR-0004 D5.6 → `0x87`；不是合法 encoding 期望。
2. **方案 B 正确性**：`ha=rd1` 目标非 rd0、`hb=rb1` base 非 rb0、`immu6=1` 非 0，均避开 ILLI；`rb1` 预置 RAM 地址后 load 合法。
3. **方案 A 前提**：`rdha=rd0 → ILLI` 由合约直接规定，不依赖实现侧检查；但仅覆盖非法路径。
4. **encoding.word 必须手算**：从合约/opcodes.yaml 推导，不从 QEMU 行为反推。
5. **不改实现**：若需实现改动，另建任务。
6. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-034a-load-encoding-deferred.md`（内容溯源）
- 本项目：`.tao/knowledge/contract-isa.md` §4、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
