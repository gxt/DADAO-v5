# SPEC-170t: schema 字段 `op` → `opc`（266 条 + 工具 + 投影表）

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-167t`/`SPEC-168t`（均已验证，`master 80cb59d9`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-23）

- 「SimRISC 的 12 个手册中，不要用单独的 `op` 字样，要么是 `opc` 表示 8 位的主编码，要么是 `opx` 表示 6 位的副编码」
- 追问「`contracts/opcodes.yaml` 的字段名 `op` 改不改？」⇒ 用户答「**改**」

## 现场盘点（2026-10-24 实测）

- `contracts/opcodes.yaml`：**266** 个 `op:` 键（唯一数据源；`tests/vectors/**` 无该字段）
- `.tao/contracts/contract-isa.md`：2 处表头 `| op |`
- 读该字段的代码（需逐个改，**不能全局替换**）：
  - `tools/spec/generate_opcodes.py`（写出字段）
  - `tools/spec/check_tables.py`
  - `tools/llvm/gen_isa_coverage.py`
  - `tools/spec/validate_encoding.py`（若读该键）
  - `tools/qemu/generate_rol_vectors.py`、`generate_atomics_vectors.py`、`generate_clmul_vectors.py`
- **陷阱**：另有约 20 处 `op` 表示"操作名"（`min`/`max`，在 `tools/testcases/oracle_minmax.py`、`run_minmax_probe.py`）——**不得改**
- `ha`（6 位字段）**不改名**（它在非操作码格式里另有含义；`opx` 只是"ha 作操作码时"的称法）

## 目标

1. `contracts/opcodes.yaml`：266 条 `op: '0x..'` → `opc: '0x..'`（**字段顺序不变**，只改键名）。
2. 上述 6 个工具：`rec["op"]` → `rec["opc"]`；写出方 `generate_opcodes.py` 同步。
3. `.tao/contracts/contract-isa.md`：2 处表头 `| op |` → `| opc |`。
4. 重生成受影响的产物（向量/矩阵/附录 A）：应**零语义变化**（仅字段名）。

## 验收

1. `grep -c '^  op:' contracts/opcodes.yaml` ⇒ **0**；`grep -c '^  opc:'` ⇒ **266**。
2. `grep -rn '\["op"\]\|\[.op.\]' tools/ | grep -v __pycache__` ⇒ 0（"操作名"的 `op` 除外，逐个判定并列出）。
3. 重生成幂等：向量/矩阵二次生成零 diff。
4. 受影响门控：`check_tables.py`、`validate_encoding`、`check-isa-coverage`、`check-scope`、`validate-vectors`、`check-asm-list`、`check-spec-cite-targets` 全 rc=0。
5. `make check`(L1) **跑一次** rc=0（schema 是中心数据，值得一次全量 L1）。
6. **可达 FAIL ≥2**：① 把一条记录改回 `op:` ⇒ `check_tables`/`validate_encoding` 红；② 把某工具读键改回 `["op"]` ⇒ 对应门控红。

## 接口规范

- **输入**：`contracts/opcodes.yaml`、`tools/{spec,llvm,qemu}/**`、`.tao/contracts/contract-isa.md`。
- **输出**：字段改名 + 工具同步 + 重生成产物。
- **约束**：不改任何**字段值**（编码/格式/scope 等一律不动）；不改 `spec/`；不 commit/push；临时目录 `/tmp/opencode/SPEC-170t/`。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
