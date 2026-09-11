# TESTSUITE-007t: ISA 向量文件修复（5 文件）

**模块**：testsuite
**项目里程碑**：M1
**依赖**：`TESTSUITE-004t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/` 下 5 个向量文件（算术、立即数/块、load-store、移位扩展、misc）
  - `verif/opcodes.yaml`（mask/value 与字段位域）
  - `.tao/knowledge/contract-isa.md`（§2 编码、§3 算术/立即数/块、§4 访存、§7 系统）
- 输出：修复后的 5 个 `tests/vectors/isa/*.yaml`
- 约束：
  - 只做**单行数据纠正**，根因必须明确；无法确定的标 `[OPEN]`，不猜测
  - 每条修正给出依据（合约章节 + 手算）
  - 完成后不自行 commit

## 背景（完整）

### 目标

修复 5 个 ISA 向量文件中已确认的编码错误、期望值错误、setup 触发 ILLI 等问题，使这些向量可被 harness 正确执行与断言。

### 设计理由

0628 在 DL-024a/DL-025a review 通过后发现 5 个 ISA yaml 文件共 27 处数据问题，全部属于架构师可直修范围（单行数据纠正、根因已明确）。同类问题若不修，向量会把实现误导到错误方向。

### 关键概念 / 数据

**问题类别（0628 清单，v5 按 0.5.3 重查）**：

1. **encoding 位域错误**：`hb`/`hc` 混淆（ORRI/ORRR 的字段位置）。
   - 0628 结论：ORRI 位域 `bits[17:12]=dst, bits[11:6]=src, bits[5:0]=count`。
2. **`input_state` 出现 rd0**：harness 用 `set.zw` 预置寄存器，若 rd=rd0 → `ha=0` → ILLI。→ `input_state` 中**禁止**出现 rd0 条目（rd0 恒零，无需预置）。
3. **期望值错误**：与修正后的 encoding/语义不一致（如立即数 wyde 位置、块赋值写入宽度）。
4. **store encoding `ha=0` → ILLI**：store 类目的 rd0 非法，encoding 向量需非 0 目的或改期望为 ILLI。
5. **load encoding `addr=0` → 访问未映射 → 超时/异常**：需有效 RAM 基址或改期望（详见 TESTSUITE-009t）。
6. **deferred 状态**：实现侧 bug 未解决时，相关语义向量标 `status: deferred` 并写明 reason（0628 为 `divs`/`divu` 的 TCG label dead-code bug）。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`（完整转述：背景、5 文件逐处改动清单与根因、验收结果 92 PASS/0 FAIL、4 条新技术结论、遗留）

## 交付物

- 5 个 `tests/vectors/isa/*.yaml`（v5 组织下对应）：
  - `rd-arith.yaml`（算术）
  - `rd-imm-block.yaml`（立即数设置 + 块赋值）
  - `rd-load-store.yaml`（load/store）
  - `rd-shift-extend.yaml`（移位/扩展）
  - `misc.yaml`（系统/占位）
- 每处修正附依据；无法确定处标 `[OPEN]`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符与文件组织**：`setzw`→`set.zw`、`setow`→`set.ow`、`rd2rb`/`rb2rd`/`rb2rb` 保留但字段/命名按 0.5.3；wyde 文件在 v5 组织为 `rd-imm-block.yaml`。
2. **ORRI/ORRR 位域**：以 v5 `contract-isa.md` §2.2 与 `verif/opcodes.yaml` 的 `fields` 为准，不照抄 0628 的位域结论（结论可能一致，但须独立核对）。
3. **RB 语义（关键）**：0.5.3 RB 算术为**全 64 位**，无 48-bit 截断；0628 的「load_reg RB 3 wyde / 48-bit 截断」结论**不适用**，v5 期望值按全 64 位手算。
4. **`divs`/`divu` → `div.so`/`div.uo`**：0628 的 TCG label bug 是 0.4.1 QEMU 实现问题；v5 是否 deferred 须由 qemu 实现与 harness 独立确认，不照搬。
5. **文件集**：0628 的 5 文件为 rd-arith/rd-wyde-block/rd-load-store/rd-shift-extend/misc；v5 以 TESTSUITE-002t 实际文件组织为准。

## 已知坑 / 结论

摘自 DADAO-0628 DL-027a：

1. **rd0 禁止出现在 `input_state`**：预置 rd0 会经 `set.zw rd0` → `ha=0` → ILLI。
2. **ORRI 位域**：`bits[17:12]=dst, bits[11:6]=src, bits[5:0]=count`（hb/hc 易混淆）；v5 须用 opcodes.yaml `fields` 核对。
3. **load encoding `addr=0`**：identity map 到 host NULL → SIGSEGV/timeout；需有效 RAM 基址或改期望。
4. **store encoding `ha=0`**：触发 ILLI。
5. **deferred 必须有 reason**：实现 bug 未解时显式 deferred，不静默。
6. **0628 验收**：92 PASS / 0 FAIL（含 4 deferred）；v5 以自身 harness 为准。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/tests/vectors/isa/`（形态参考，禁止复制数据）
- 本项目：`verif/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`tests/vectors/schema.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 5 个文件中的 encoding 位域与 `verif/opcodes.yaml` 的 `(word & mask) == value` 一致
2. `input_state` 中无 rd0 条目
3. 期望值按 0.5.3 语义（含 RB 全 64 位）逐条手算且自洽
4. deferred 向量有明确 `deferred_reason`；无法确定处标 `[OPEN]` 并在完成区列出
5. `python3 verif/validate_vectors.py` 零错误；`make check` PASS
6. 每处修正可回溯到合约章节
7. 未自行 commit

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
