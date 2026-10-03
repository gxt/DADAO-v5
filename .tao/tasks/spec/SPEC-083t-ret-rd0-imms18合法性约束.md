# SPEC-083t: ret rd0 ⇒ imms18 必须 0 — 规范与契约落地

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-082t`、`LLVM-026t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/SimRISC-06-控制流.md`（§函数返回，当前 L133–135 无硬约束）
  - `.tao/knowledge/contract-isa.md`（§1.3.1 / §8.5，当前已有 `ret rd0, 0` 允许的说明，但缺 `rd0 ⇒ imms18==0` 的硬约束）
  - `tools/spec/generate_opcodes.py`（`ret_riii_ra` 当前 `legality: []`）
  - `contracts/legality_rules.yaml`（需新增规则条目）
  - `contracts/opcodes.yaml`（自动生成，不手改）

- **输出**：
  1. `spec/SimRISC-06-控制流.md`：§函数返回段新增约束表述
  2. `.tao/knowledge/contract-isa.md`：§1.3.1 或 §8.5 同步新增硬约束
  3. `tools/spec/generate_opcodes.py`：`ret_riii_ra` 的 `legality` 增加条件约束
  4. `contracts/legality_rules.yaml`：新增规则 ID/描述
  5. `contracts/opcodes.yaml`：由生成器重生成（含 `rule_refs`）
  6. 合法性清单：由 `tools/spec/gen_legality_list.py` 重生成
  7. 门控 `make check-legality-drift` + `make check-rule-refs` 通过

- **约束**：
  - 不改 `.tao/adr/adr-0013-assembly-syntax.md`
  - 不改 `spec/SimRISC-0.5.3/`
  - 不提交 git
  - 与 `ADR-0013 D3/D10`（汇编立即数字节化）正交，`ret` 的 `imms18` 编码名不变
  - `generate_opcodes.py` 的 `EXPR_TO_RULE` 映射需同步更新

## 验收标准

1. **规范文本**：`spec/SimRISC-06-控制流.md` §函数返回段明确写出：`ret rdHA, imms18` 中，当 `rdHA == rd0` 时，`imms18` MUST 为 0；否则**非法**：**汇编期硬报错**（LLVM，`Error` 级）+ **运行期 ILLI 0x88**（QEMU）。
2. **合约同步**：`.tao/knowledge/contract-isa.md` §1.3.1 或 §8.5 中新增相应硬约束表述，引用 `[SimRISC-06 §函数返回]`。
3. **生成器变更**：`tools/spec/generate_opcodes.py` 中 `ret_riii_ra` 的 `legality` 列表非空，包含条件约束表达式（如 `"rdha != rd0 or imms18 == 0"` 或等价形式）。
4. **规则目录**：`contracts/legality_rules.yaml` 新增一条规则，**ID = `dst_rd0_nonzero`**（与既有 `dst_rd0`/`dst_dual_same`/`dst_rb0` 的 `dst_*` 约定一致；用户确认），`kind: static`，`fault: ILLI`，`status: active`，`spec_cite: "SimRISC-06 §函数返回"`；`description` 须写清"**仅 `ret` 适用**：`rdha == rd0` 且 `imms18 != 0` ⇒ ILLI"。
5. **重生成**：运行 `python3 tools/spec/generate_opcodes.py` 后，`contracts/opcodes.yaml` 中 `ret_riii_ra` 的 `legality` 和 `rule_refs` 非空。
6. **合法性清单**：运行 `python3 tools/spec/gen_legality_list.py` 重生成清单文件，无报错。
7. **门控通过**：`make check-legality-drift` 和 `make check-rule-refs` 均 exit 0。
8. **自包含**：任务书不引用外部仓库文件作为执行依赖。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）