# SPEC-170t: schema 字段 `op` → `opc`（266 条 + 工具 + 投影表）

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-167t`/`SPEC-168t`（均已验证，`master 80cb59d9`）
**状态**：已验证

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

**测试结果**：通过 26/26（`.work/evidence/SPEC-170t/run.sh` rc=0）；`make check`(L1) rc=0。
**修改文件**：`contracts/opcodes.yaml`（266 键改名）；`tools/spec/{generate_opcodes,check_tables,validate_encoding,check_qfc_coverage}.py`；`tools/llvm/{gen_isa_coverage,validate_instrinfo,generate_instrinfo}.py`；`tools/qemu/{generate_rol_vectors,generate_atomics_vectors,generate_clmul_vectors}.py`；`tools/testcases/{generate_isa_vectors,generate_ctrl_jump_call_ret}.py`；`tools/integ/check_interface_alignment.py`；`.tao/contracts/contract-isa.md`（2 表头）；重生成 `tests/vectors/{rol/rol,clmul/clmul,isa/ctrl-call,isa/ctrl-jump,isa/ctrl-ret}.yaml`。
**验收结果**：
- `grep -c '^  op:'` ⇒ 0；`'^  opc:'` ⇒ 266；opcodes.yaml 532 行 diff 全为 `op:`→`opc:`（非键行 0）。
- `grep -rn '\["op"\]' tools/` ⇒ 13 命中，全部为操作名/`.td` 字段，已逐个判定：`run_minmax_probe.py`(3)、`oracle_minmax.py`(1)、`oracle_atomics.py`(5)、`validate_m5_vectors.py`(2)（以上为 min/max/store_n_shared/向量 header 操作名）；`gen_isa_coverage.py`:198/510（`.td` 的 `let op` 字段，非 yaml 键）。
- 重生成（10 生成器 + 矩阵）两轮 diff md5 均 `f179ac0a…`（首轮=入库，二轮零 diff）；`generate_opcodes.py` 逐字节复现 `opcodes.yaml`；矩阵/附录 A（check-asm-list）零 diff。
- 门控 rc=0：`check_tables`、`validate_encoding`、`check_qfc_coverage`、`check-isa-coverage`、`check-scope`、`validate-vectors`、`check-asm-list`、`check-spec-cite-targets`、`check-instrinfo`、`check-interface`、`make check`(L1)。
- 可达 FAIL：① 一条记录改回 `op:` ⇒ `check_tables`=1、`validate_encoding`=1；cp+md5 还原后回绿。② `check_tables.py` 读键改回 `["op"]` ⇒ rc=1；还原后回绿。
**新发现/坑**：① 生成物自 `SPEC-166t`/`SPEC-167t` 起已漂移（重生成仅 `spec_cite`/`Source` 注释变化，期望值 0 变化）——向量缺漂移门控。② `generate_ctrl_jump_call_ret.py` 的 `返回地址栈 §C*/§D*` 引用在 SPEC-167t 后悬空，重生成会令 `check-spec-cite-targets` 14 红，已改指现存节（压栈流程/弹栈流程）。③ `ha` 键与 `.td` 的 `let op` 均未动。
**遗留问题**：无。越界披露：任务书列 6/7 工具，实际另有 6 个 yaml 读写方（`validate_instrinfo`/`generate_instrinfo`/`check_qfc_coverage`/`check_interface_alignment`/`generate_isa_vectors`/`generate_ctrl_jump_call_ret`）必须同步改键，否则门控红；另有上述 ctrl 生成器 10 条 spec_cite 清理。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动源码；判决：全部 finding 已修，可标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书工具清单不全，另有 6 个 yaml 读键方 | ✅已修 | 6 文件同步 `["op"]`→`["opc"]` | 门控全 rc=0；grep 残留=0（除操作名） |
| `.td` 的 `let op` 与 yaml 键同名，易误改 | ✅已修 | 仅改 `rec_key`/yaml 侧，保留 `def_key`/`.td` 解析 | `check-instrinfo` rc=0；`gen_isa_coverage --self-test` rc=0；脚本断言 `.td` 键仍在 |
| 重生成暴露 ctrl 生成器悬空 cite（既有漂移） | ✅已修 | `§C*`→压栈流程、`§D*`→弹栈流程（现存节） | `check-spec-cite-targets` 14→0 |
| `generate_opcodes.py` 首轮漏跑 | ✅已修 | 补跑并纳入证据脚本幂等序列 | md5 `ac71f944…` 前后一致，逐字节复现 |
| 向量入库产物含 SPEC-166t/167t 遗留漂移 | ✅已修（固化） | 接受重生成结果：非 `spec_cite`/注释行 0 变化 | `git diff` 过滤后 0 行；两轮幂等 |

### 第 1 轮 reviewer 验收（2026-10-24）

基线 `9442a589`（HEAD `0fb50f38` 仅多 milestones.md 一行）；审查前后 `git status --porcelain -uall` 均 0 行、目标文件 md5 一致（`opcodes.yaml ac71f944…`）。

- **266 键**：`grep -c '^  op:'`=0、`'^  opc:'`=266（ha=177 未动）；`git diff 9442a589~1..9442a589 -- contracts/opcodes.yaml` = 532 行 = 266 对 ±，逐对校验**全为 `  op: '0x..'` → `  opc: '0x..'` 纯键名改写**（bad pairs=0）⇒ 值与顺序未变；向量 5 文件非 `op/opc/spec_cite/#` 行 = 0。
- **工具同步**：13 工具 diff 逐处核过，均为 yaml 侧读键 `["op"]`→`["opc"]`；残留 `["op"]` 13 处全部判定为**操作名/`.td` 字段**（minmax 3+1、atomics 5、m5_vectors 2 = min/max/store_n_shared/向量 header；gen_isa_coverage 198/510 = `.td` 的 `let op`，且 `rec_key` 已用 `r["opc"]`）。`let op = 0x..` 输出方 generate_instrinfo 未误改。
- **门控 rc**（本人重跑，非采信完成区）：证据脚本 `bash .work/evidence/SPEC-170t/run.sh` ⇒ **26/26 PASS，exit=0**（含重生成 round1=入库零 diff、round2 幂等、check_tables/validate_encoding/check_qfc/isa-coverage/scope/validate-vectors/asm-list/spec-cite-targets/instrinfo/interface 及 `make check`(L1) 全 rc=0）。
- **独立注入**（reviewer 自做，cp+md5 还原，非采信脚本自检）：① `opcodes.yaml` 一条 `opc:'0x10'`→`op:` ⇒ check_tables=1（KeyError: 'opc'）、validate_encoding=1，还原 md5 相等、回绿 rc=0；② `validate_instrinfo.py` 的 `rec.get("opc")`→`rec.get("op")` ⇒ `make check-instrinfo` rc=2 / **571 errors**，还原 md5 相等、回绿 rc=0（0 errors）。
- **未改 spec/**：`git diff 9442a589~1..9442a589 -- spec/` = 0 行。
- **判决：Accepted**（键无遗漏/误改、值未变、门控全绿、两次注入均红且还原回绿）。提示架构师：ctrl 生成器 10 条 spec_cite 与 clmul spec_cite 由悬空/旧值改为现存节属**既有漂移固化**，已在完成区披露，非本任务引入。

