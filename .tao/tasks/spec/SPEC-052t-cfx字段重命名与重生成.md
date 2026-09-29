# SPEC-052t: cfx 字段重命名（cfxha/cghb/rchc/rdhd）与重生成

**模块**：spec（含跨模块 `tools/llvm/gen_asm_list.py`，因须同步才能保持 `make check` 绿灯）
**项目里程碑**：M1→M2
**依赖**：`ADR-0013 D8`（Accepted，本任务落地 D8.1–D8.5 的**机制**部分）
**状态**：待开始

## 背景

`ADR-0013 D8` 裁定：cfx 汇编记法改为 `cfxHA` / `cgHB, rcHC, rdHD`，并重命名字段。现状不一致：

- `contracts/opcodes.yaml`：`cfx2rd`/`cfx2rc` 字段为 `cfxcode`、`hb`、`hc`、`hd`；`cfxld`/`cfxst`/`trap`/`escape` 字段为 `cfxcode`
- `tools/llvm/gen_asm_list.py::operands()` **已按 `cghb`/`rchc` 判断**（当前 yaml 的 `hb`/`hc` 落到 `else` 分支 → 渲染为 `hb, hc, hd`）
- 故当前生成表为 `cfx2rd cfxcode, hb, hc, hd`（与 D8 不符）

## 修改内容

### 1. `tools/spec/generate_opcodes.py`

- `f_crrr()`：字段名 `cfxcode→cfxha`、`hb→cghb`、`hc→rchc`、`hd→rdhd`（**role/bank/bits 不变**：`cfxcode`/`cfx_cg`/`cfx_rc`；bits `[23:18]`/`[17:12]`/`[11:6]`/`[5:0]`）
- `f_crii()`/`f_ciii()`：`cfxcode→cfxha`
- 注释/文档字符串同步

### 2. 重生成 `contracts/opcodes.yaml`（用 `generate_opcodes.py`）

### 3. `tools/llvm/gen_asm_list.py`

- `operands()`：`name == "cfxcode"` → `name == "cfxha"`（kind 仍为 `"cfxcode"`；`cghb`/`rchc` 分支已存在，无需改）
- `field_name()`：`FIELD_RE` 扩展为 `^(rd|rb|ra|rf|cg|rc|cfx)([a-z]{2})$` → `cfxha→cfxHA`、`cghb→cgHB`、`rchc→rcHC`、`rdhd→rdHD`
- `new_form()` 中硬编码的 `cfxcode` → `cfxHA`（`trap`、`escape` 两处）
- 顶部注释/`field_name` 文档字符串中的 `cfxcode` 同步
- **注意**：`new_template()`（L378 起）为**死代码**（docstring 已标 deprecated），本任务**不改**

### 4. `contracts/legality_rules.yaml`（L295）

描述性文本中的 `cfxcode` → `cfxha`（若判定为字段引用；若是纯语义描述可保留并说明）

### 5. 重生成产物

- `docs/assembly-list.md`（`python3 tools/llvm/gen_asm_list.py -o docs/assembly-list.md`）
- 12 个 `spec/SimRISC-*.md` 内嵌速查表（`--embed-spec`）
- 若 `docs/self-consistency.md` 为生成物则一并重生成（请核实其生成方式；若非生成物则按字段引用同步）

### 6. 期望的 cfx 汇编形式（**逐条核对**）

```
cfxld   cfxHA, [rbHB, immu12]
cfxst   cfxHA, [rbHB, immu12]
cfx2rd  cfxHA, cgHB, rcHC, rdHD
cfx2rc  cfxHA, cgHB, rcHC, rdHD
escape  cfxHA, [excp_cause_ip, imms18i]
trap    cfxHA, immu18
```

## 约束

- **role 名不变**（`cfxcode`/`cfx_cg`/`cfx_rc`）；只改**字段名**
- 不影响 `validate_instrinfo.py` 的槽位名（`ha/hb/hc/hd` 为格式槽位，与本重命名无关）
- 不改 `docs/m1-retrospective.md`（历史记录）
- 不自行安装/下载；命令缺失 → 停下报告
- **本任务不得留半成品**：字段改名与生成器同步必须一起完成，结束时 `make check` 必须 EXIT=0

## 验收标准

1. `opcodes.yaml` 中 cfx 家族字段名为 `cfxha`/`cghb`/`rchc`/`rdhd`；bits/role/bank 未变
2. 生成表（`docs/assembly-list.md` + 12 内嵌表）cfx 行如 §6 所列
3. 生成器**幂等**（重跑无 diff）；其它 248 条渲染**不变**（给出 diff 证据）
4. `make check` EXIT=0（含 `check-asm-list-consistency`）
5. 全库（`tools/`/`contracts/`/`docs/`/`tests/`）无遗留 `cfxcode` 字段引用（历史文档除外，须列明）
6. 反例验证：注入（如 `cfxha`→`cfxcode`）→ 生成表回退旧形式可检出；复原后无残留

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
