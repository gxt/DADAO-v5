# INFRA-102t: 门控补强与"去写死计数"（跨模块安全网）

**模块**：infra
**项目里程碑**：M9（收尾前，先于 SPEC-164t / LLVM-126t / LLVM-127t）
**依赖**：`SPEC-165t`/`SPEC-166t`（已验证，`master df46f0f1`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户 2026-10-22）

「减少交叉链接很关键，减少各种计数和比较很关键；不然，时间都浪费在这些无谓的修订中了」

**现状痛点（实测）**：
- `tools/spec/check_fp_contract.py`：`EXPECTED_TOTAL = 64` + `FAMILY_COUNTS`（14 族写死）⇒ 每加/翻一条 FP 记录要同步改 3 处
- `tools/spec/check_scope.py`：`m1=156 / fp=64 / excluded=27 / m3=1 / m8=7 / m9=9 / total=264` 全写死
- `tools/spec/check_rule_refs.py`：`EXPECTED_ORPHAN_EXEMPTIONS` 写死
- 文档侧：`contract-isa.md` 3 处、`MEMORY.md` 1 处境写死条数

⇒ 每新增/翻转一条指令，平均要改 **4–6 个地方**（opcodes、spec 生成区、门控常量、契约计数、文档计数），这是"无谓修订"的主因。

## 目标

### 1. 计数一律现场派生（不写死）
- `check_scope.py`：删除全部期望常量；改为断言**不变量**：
  - `total == len(opcodes)`（自身）；
  - 分区集合 = `m1/fp/excluded/m3/m8/m9` 且**并集 == 全量**、**两两不交**；
  - `excluded ⇒ decode == ILLI`、非 `excluded` ⇒ 无 `decode`（既有规则保留）；
- `check_fp_contract.py`：删除 `EXPECTED_TOTAL`/`FAMILY_COUNTS`；改为
  - `fp_semantics` 的 id 集合 == `opcodes.yaml` 中 `scope == fp` 的 id 集合（**双向相等**，缺/多都红）；
  - 族集合 == 记录中出现的 `family` 值集合（现场收集）；
  - 每条记录的 `family`/`spec_cite`/`semantics_ref` 非空且格式合法；
- `check_rule_refs.py`：豁免集合从**数据文件/注释**读取（或改为"孤儿必须出现在显式 allowlist 文件"），不写在代码里。

### 2. 生成物用"幂等"代替"两处比对"
- `gen_asm_list` / `gen_legality_list` 已是单源生成：门控改为**重生成 + byte 比对**（生成结果与盘上一致即 PASS），不再维护第二份期望文本；
- 相关门控（`check_asm_list_consistency` / `check_asm_prose` / `check_tables` / `check_spec_codeblocks`）里凡是"期望字符串/期望条数"的常量，全部改为现场派生或删除。

### 3. 补 7 个覆盖缺口（原计划）
- `ISS-320`：`validate_instrinfo.py` 覆盖 FP `.td`（`DADAOInstrInfoFP.td.patch`）
- `ISS-321`：`check_qemu_trans --strict` 增加 orphan（trans 残留）方向
- `ISS-325`：`check_tables.py` 覆盖 MISC-RF（`op 0x44`）
- `ISS-327`：`gen_isa_coverage` 的 `L2_isel` 识别伪指令/同义名/`BuildMI` 三类来源
- `ISS-225`：`check-qemu-semantics` 增"`helper.c.patch` 不得出现 umon 接管分支"形态断言
- `ISS-102`+`ISS-118`（合并）：覆盖断言粒度 —— 删单条用例/删同族多 pattern 之一必须红
- `ISS-058`：`decodetree` 输出 bit-reproducible（固定 `PYTHONHASHSEED`）

## 验收

1. `grep -nE 'EXPECTED_TOTAL|FAMILY_COUNTS|== (264|156|64|31|27|60)\b' tools/**/*.py` ⇒ **0 命中**（除注释说明）。
2. 对每个改动过的门控：**注入 → FAIL → 还原 → PASS**（`cp`+md5），至少 8 条注入，逐条贴真实输出。
3. 新增 7 项缺口各有**可达 FAIL**（真实注入）。
4. `make check`(L1) + `make check-modules`(L2) 绿；`check_patch_tree` 绿。
5. 删除两条 issue 记录（`ISS-102`/`118` 合并后按合并条处理）。

## 接口规范

- **输入**：`tools/spec/**`、`tools/qemu/**`、`tools/llvm/**`、`tools/infra/**`、`contracts/**`（只读）。
- **输出**：去常量的门控 + 7 项覆盖补强 + 各自的 `--self-test`。
- **约束**：不改 `spec/**`、不改指令语义；不 commit/push；临时目录 `/tmp/opencode/INFRA-102t/`。

## 风险与纪律

- **不许为了"绿"放宽断言**：删常量不等于删校验，必须保留"集合相等/双向覆盖/不交"这类不变量；
- 每条注入都要真实红→还原→绿，禁恒真；
- 若某门控依赖的常量无法派生（如历史豁免清单），改为**显式数据文件**并加"数据文件本身被引用"断言。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
