# m13-integ-005: M13 收口（差异归因 + 矩阵冻结）

> 由 `tools/testcases/parity/acceptance_report.py` 从两平台逐例生成器的同一批输入确定性重建；不写生成时刻、不写运行期路径。

## 0. 结论

- 向量面：`.S` 载体 **272**，镜像 **904**；本矩阵覆盖 864 个镜像
- 三平台逐例：整数段 **637/637**、FP 段 **227/227** `AGREE_PASS`；平台差异 **0**、三方一致非通过 **0**、未归因 **0**
- 差异分类：spec 歧义（含已登记待裁定）**2**、实现缺陷 **1**、测试资产 **10**、未归因 **0**
- 输入 commit：`b73a0cddf263c4848bd6cd417c4ef8313b6a3c93`（陈旧判定的唯一时间锚）

## 1. 输入与身份

- 机器指纹：qemu `10291d6b5b99d90f443958ed17963e33`、gem5 `093790ce03b74c7f22c50070a3e82e2b`、chipyard `4e072a711afdca8a36788f9a9958e896`；bootrom `514300876ea66ec108396334f3ef2b0f` · llvm-mc `0979c46865dcd3ba639b7f3d9292c80c`
- `.tao/contracts/contract-isa.md` sha256 `f2118f4446188169`
- `spec/SimRISC-07-浮点运算.md` sha256 `e884712ecfdf8c80`
- `tests/inst.yaml` sha256 `ed7d56b308fd724e`
- `contracts/opcodes.yaml` sha256 `f4758120b3c16129`
- run `int/book`：637 条记录 sha256 `9dcbeb102b27af10`
- run `fp/book`：227 条记录 sha256 `b37d1003394bbaaf`

## 2. 向量面（现场统计，按段）

| 段 | 载体 | opcode id | 非 id 载体 | 链例点 | 故障例 | 镜像 |
| --- | --- | --- | --- | --- | --- | --- |
| int | 202 | 193 | 9 | 3031 | 436 | 637 |
| fp | 65 | 65 | 0 | 1179 | 162 | 227 |
| cfx | 5 | 5 | 0 | 74 | 35 | 40 |
| **合计** | **272** | **263** | **9** | **4284** | **633** | **904** |

非 id 载体 **9** 条（保留编码 / 伪指令载体，以自身文件头的 spec 出处计）：`atomic_rmw`、`pseudo_set.fo_imm64`、`pseudo_set.ft_imm32`、`pseudo_set.fx_reg`、`pseudo_set.rb_imm`、`pseudo_set.rb_reg`、`pseudo_set.rd_imm`、`pseudo_set.rd_reg`、`undi_reserved`

## 3. 逐例结果（两份生成器的现场输出）

| 段 | 镜像 | AGREE_PASS | AGREE_FAIL | DIFF | spec 歧义 | 覆盖缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| 整数段 | 637 | 637 | 0 | 0 | 0 | 0 |
| FP 段 | 227 | 227 | 0 | 0 | 0 | 0 |

> 逐镜像三平台 `exit` / 字节数 / 结果流 md5 见本报告 JSON 的 `int_report.results.per_image` 与 `fp_report.results.per_image`。

## 4. 差异归因（分类）

### spec 歧义（含已登记待裁定）（2）

- `ISS-443`：`sc` 的保留清除事件「异常或中断进入」是否作为可观测要求：`spec/SimRISC-12 §1` 明列为清除事件，但三方实测分歧；不覆盖理由：载体框架下故障即终止镜像，「异常进入后再 `sc`」无法在单链例镜像内观测；需要专驱动（另立任务）
- `ISS-440`：「另一 hart 对同一精确地址+相同宽度 store ⇒ 清保留」是否在 M13 冻结判据内；不覆盖理由：单 hart 机型，多 hart 原子语义无观测载体（记 GAP，不造用例）

### 实现缺陷（1）

- `ISS-433`：`trap cfx_power` 的语义：chipyard 报 ILLI，qemu/gem5 进 power 向量——是 RTL 缺实现还是 spec 未明；不覆盖理由：cfx 面不属本差分（册 `11-cfx` 的载体归 CFX 专项）

### 测试资产（10）

- `fp_matrix`（blank_cell）：1 RTZ × NONE：该舍入档没有 flags=0 的链例点
- `fp_matrix`（blank_cell）：1 RTZ × NV：该标志位只在 0 RNE 档有点（本档无）
- `fp_matrix`（blank_cell）：1 RTZ × DZ：该标志位只在 0 RNE 档有点（本档无）
- `fp_matrix`（blank_cell）：1 RTZ × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
- `fp_matrix`（blank_cell）：2 RDN × NV：该标志位只在 0 RNE 档有点（本档无）
- `fp_matrix`（blank_cell）：2 RDN × DZ：该标志位只在 0 RNE 档有点（本档无）
- `fp_matrix`（blank_cell）：2 RDN × OF：该标志位只在 0 RNE / 1 RTZ / 3 RUP 档有点（本档无）
- `fp_matrix`（blank_cell）：2 RDN × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
- `fp_matrix`（blank_cell）：3 RUP × NV：该标志位只在 0 RNE 档有点（本档无）
- `fp_matrix`（blank_cell）：3 RUP × DZ：该标志位只在 0 RNE 档有点（本档无）

## 5. 覆盖缺口与测试资产缺口

- 生成器报告的覆盖缺口 **0** 条
- FP 矩阵空白格 **10** 个（现有向量无该组合）：
  - 1 RTZ × NONE：该舍入档没有 flags=0 的链例点
  - 1 RTZ × NV：该标志位只在 0 RNE 档有点（本档无）
  - 1 RTZ × DZ：该标志位只在 0 RNE 档有点（本档无）
  - 1 RTZ × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
  - 2 RDN × NV：该标志位只在 0 RNE 档有点（本档无）
  - 2 RDN × DZ：该标志位只在 0 RNE 档有点（本档无）
  - 2 RDN × OF：该标志位只在 0 RNE / 1 RTZ / 3 RUP 档有点（本档无）
  - 2 RDN × UF：该标志位只在 0 RNE / 3 RUP 档有点（本档无）
  - 3 RUP × NV：该标志位只在 0 RNE 档有点（本档无）
  - 3 RUP × DZ：该标志位只在 0 RNE 档有点（本档无）
- 结构 GAP `multi-hart-atomics`：多 hart 原子语义（另一 hart 同址同宽 store 清保留）：chipyard `WumingTinyConfig` 单 hart，无观测载体（不造用例、不伪造期望）
- 结构 GAP `sc-after-exception`：「异常/中断进入后再 `sc`」：故障即终止镜像，单链例镜像内不可观测（需专驱动）（不造用例、不伪造期望）

## 5.1 与旧版口径的对照（常量说明，不作判据）

| 项 | 旧版（002/003 已验收） | 冻结版（本报告现场重算） | 成因 |
| --- | --- | --- | --- |
| scope:fp 条数 | 66 | 65 | `ft2ft`/`fo2fo` 退役、`rf2rf` 新增（`m13-spec-010`） |
| FP 镜像 | 232 | 227 | 随 ↑ 的载体面变化 |
| FP 覆盖缺口（not_indexed） | 4 | 0 | 4 条 rf 访存载体现已在 `tests/inst.yaml` 登记（现场核对） |
| FP 矩阵空白格 | 11 | 10 | 新增/更新载体补了 1 个「舍入档 × 标志」组合 |
| 整数段载体 / 镜像 | 194 / 629 | 202 / 637 | 7 个伪指令载体 + `rf2rf` 等新向量进入载体面 |
| 整数段覆盖缺口 | 0 | 0 | 与旧版一致 |

> 旧版报告的「已知缺口」在此逐条交代去向；冻结版判据一律来自本报告的现场重算。

## 6. 待裁定项（spec 口径 / 实现归口）

- 载体面内 spec 歧义：**0** 条（none）
- `ISS-443`（spec）：`sc` 的保留清除事件「异常或中断进入」是否作为可观测要求：`spec/SimRISC-12 §1` 明列为清除事件，但三方实测分歧
  - 依据：`tests/inst/12-misc/sc.b.nn_orrr_rd.S` 文件头 GAP 段：chipyard 清 / qemu 仅同步异常清 / gem5 不清 ⇒ 载体只留 GAP、不把任一平台行为写成期望
  - 本矩阵不覆盖：载体框架下故障即终止镜像，「异常进入后再 `sc`」无法在单链例镜像内观测；需要专驱动（另立任务）
- `ISS-440`（spec）：「另一 hart 对同一精确地址+相同宽度 store ⇒ 清保留」是否在 M13 冻结判据内
  - 依据：`spec/SimRISC-12 §1` 列为清除事件；三方均无实现路径，且 chipyard `WumingTinyConfig` 单 hart ⇒ 无观测载体
  - 本矩阵不覆盖：单 hart 机型，多 hart 原子语义无观测载体（记 GAP，不造用例）
- `ISS-433`（implementation）：`trap cfx_power` 的语义：chipyard 报 ILLI，qemu/gem5 进 power 向量——是 RTL 缺实现还是 spec 未明
  - 依据：`m13-testcases-027` 实测；属 cfx 面（册 `11-cfx`）
  - 本矩阵不覆盖：cfx 面不属本差分（册 `11-cfx` 的载体归 CFX 专项）

## 7. 前序任务位置

- `m13-integ-002`（FP 语义）：recomputed —— FP 段由 `fp_diff.py` 在同一批输入上重算；差异数即本报告的 fp 段
- `m13-integ-003`（整数/访存）：recomputed —— 整数段由 `int_diff.py` 在同一批输入上重算；差异数即本报告的 int 段
- `m13-integ-004`（riscv-tests）：retired —— 移植语料已由 `m13-testcases-045` 退役删除（不归档、不溯源）：任务书结论 = 35/35 `AGREE_PASS`、`DIFF=0`，本轮不再重跑

## 8. 已知项（单列）

- `ISS-357`（closed (M13: m13-testcases-006)；整数段/FP 段）：SE dual-fd output capture loses fd1/fd2 order（not applicable: this differential uses a single semihosting output channel and compares bytes only）
- `ISS-373`（open；整数段）：shared install root may diverge from the build tree (m13-qemu-014: installed-root qemu is still the pre-fix build); a differential must pin the executed binary instead of assuming they agree（run identity: the engine fingerprint below is the binary actually executed (the build tree), not the installed root）
- `m13-testcases-037`（landed；整数段）：sc/sys reservation granularity (exact address + width) formal vectors; the unobservable reservation paths are not written as expectations anywhere（vector surface: the sc reservation-granularity vectors are part of the input commit (m13-testcases-037 verified); reservation paths that the carrier framework cannot observe stay GAP and are tracked in issues.yaml (ISS-440 / ISS-443)）
- `picolibc_math`（blocked (B7 closed)；FP 段）：picolibc math_test gap stays in its own matrix（not in scope: separate picolibc suite, excluded by task）

## 9. 判据

- 每个非 `AGREE_PASS` 项均已归因或登记；分母与两份逐例报告逐项对账；`AGREE_PASS` 链例三平台结果流逐字节相等（生成器内断言）

