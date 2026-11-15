# m13-testcases-049: 原子 RMW 合成序载体（`tests/inst/00-isa-design/`）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（`rf2rf` 已合）、`m13-testcases-037`（保留粒度向量已合）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 用户裁定（2026-11-15）

> 「我建议放00，因为01-12的文件数量正好可以和指令数对上」

⇒ **`01`–`12` 各册保持"一个 opcode id 一个文件"的对应关系，不再往册内塞非 id 载体**；原子 RMW 合成序属"非 id 载体"，放 **`tests/inst/00-isa-design/`**（与 `undi_reserved.S`、`pseudo_set.*.S` 同册）。

## 背景：现有 lr/sc 载体**不覆盖** RMW 合成序

`12-misc` 的 24 个 `lr.*`/`sc.*` 载体只测**单指令语义**（保留置位/清除、成败、失败不写内存、保留粒度）；实测 **`br.` 回跳数 = 0、`lr` 与 `sc` 之间无算术** ⇒ 完全没覆盖 C11/`__atomic_*` 编译出来的"**lr → 计算 → sc → 失败重试**"环。

## 任务：新增 `tests/inst/00-isa-design/atomic_rmw.S`（单文件，约 12–16 点）

每点"一行、期望内联、点号连续"，期望**独立推导自 `spec/SimRISC-12 §1` + `contract-isa §14.2`**（不从 qemu/llvm/gem5 反推）。覆盖：

1. **`fetch_add`（含强制失败重试）**：内存初值 `0x100`；
   `lr t0,[A]` → **插一条 `lr t1,[B]` 清除保留**（等价"被抢"）→ `sc [A], t0+8` ⇒ **失败返回 1 且 A 仍 `0x100`**（失败不写）→ 重新 `lr t0,[A]` → `sc [A], t0+8` ⇒ 成功返回 0、`A == 0x108`；并断言**第一步读到的 old == `0x100`**（返回旧值语义）；
2. **`fetch_sub`**：同构，断言 `A == old - d` 且返回 old；
3. **`fetch_and` / `fetch_or` / `fetch_xor`**：各 1 点（不需重试，断言返回值 = old、内存 = old op val）；
4. **`exchange`**：`lr` 得 old → `sc` 写新值 ⇒ 返回 old、内存 = 新值；
5. **`compare_exchange` 两路**：① 比较相等 ⇒ `sc` 成功、内存 = 期望新值；② 比较不等 ⇒ **不执行 `sc`**、内存不变、返回 old（对应"比较后决定是否尝试"这层）；
6. **重试必须重读（关键负例）**：构造"若实现复用旧值直接重试就会错"的序列 —— 在失败后**改变内存内容**（用普通 `st`，注意同 hart 同址同宽 `st` **不清**保留，所以顺序要放在清除之后、重读之前）⇒ 正确实现应读到新值并算出正确结果；把该点写成显式断言（`A` 最终 = 新值 + d）。

> 说明：**多 hart 争用**与**内存序强度**在单 hart 机型不可观测 ⇒ 继续记 GAP（与 `ISS-440`/`ISS-443` 同线），不伪造。

## 任务要求

1. 新建 `tests/inst/00-isa-design/atomic_rmw.S`（**非 id 载体**）；
2. **双注册表**逐文件登记：`tools/testcases/validate_vectors.py::NON_ID_CARRIERS` 与 `tools/testcases/check_tests_index.py::NON_ID_CARRIERS`；
3. `tests/inst.yaml` 增 1 条（`inst-00-isa-design-009`，`platforms: [system]`、`level: full`）；
4. `tests/case-ledger.tsv` 重生成；`tests/inst/README.md`（00 册说明）与 `MIGRATION.md`（§ 新增一节）同步；
5. 每点检查点 ≤127、点号连续；期望内联（优先用 `macros/inst_test.inc` 现有宏，缺宏在 `.S` 内 `.macro`）。

## 验收（真实 rc）

1. `run_asm_suite --platforms qemu --id atomic_rmw`（或按文件跑）⇒ 全过，贴检查点数与字节流；
2. **三平台可选**：chipyard/gem5 若对 RMW 序列无差异，跑一次并贴结果；若存在平台差异 ⇒ 记 GAP 并给实测值，**不把某平台行为写成期望**；
3. 门控：`validate-vectors`（非 id 载体 9 条）、`check-tests-index`（现场条数）、`check-case-ledger`、`check-inst-asm`（id 264 不变、镜像 +N）、`check-no-residue`、`check-knowledge-refs` rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把"失败不写内存"那条的期望改成"写了" ⇒ 应红；② 把"重试必须重读"那条改成复用旧值 ⇒ 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `tests/inst/00-isa-design/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅 `NON_ID_CARRIERS`）、`tests/inst/{README.md,MIGRATION.md}`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`、`tests/inst/12-misc/**`（01–12 册保持 id 一一对应）；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
