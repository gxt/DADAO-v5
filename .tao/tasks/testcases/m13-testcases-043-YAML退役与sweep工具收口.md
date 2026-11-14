# m13-testcases-043: YAML 退役收口（先审计等价、再删；保留编码迁 `00-isa-design`；sweep 工具退役）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-042`（已合入后再开工：它改了 `bitcnt.yaml` 与「每 id ≤127」门控，先合避免数字漂移）
**可并行分片**：否（跨 `tests/inst` + 多个检查器）
**预估**：6–10 h（分四阶段，每阶段可单独验收）
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「最初需要独立 oracle 的情况已经不存在了，我们现在已经是多个平台差分对比，并且马上要增加 IDL；这些内容的必要性已经没有了。现在的问题是如何清理它们；有用的 case 放到对应的指令测试向量中，你不确定的，逐个告诉我，我来定」
>
> （对保留编码）「放在 `tests/inst/00-isa-design/` 下，文件名 `undi_reserved.S`」
> （对 `fp_ref.py`）「保留为生成期工具」
> （对 sweep）「首先需确认它们要生成的测试案例都已经有对应的汇编案例了，然后就可以删除了」
> （对 `.S`）「不再收敛」

## 现状（现场统计，2026-11-14）

- `.S`：**264 文件 / ~3589 条用例宏**（最大单文件 34 条，无一超 127）；故障例 **633**；ctrl 用 `__LAND_IP` 查目标 IP；FP 宏带舍入模式参数；
- YAML：**28 文件 / 1510 例 / 204 个 id**（另有 3 条**无 id** 的保留编码）；
- **204 个 YAML id 全部有 `.S` 载体**（0 缺）；
- 按「YAML 例数 vs `.S` 宏条数」粗比，**37 个 id 的 `.S` 宏数少于 YAML**（`ctpop/ctlz/cttz`、`clmul.o`、`aip.si_riii_rb`、`fence_ciii_cfx`、`sc.*` 12 形式、`ret_riii_ra` 等）——**该比较不严谨**（`.S` 用宏参数/链点/Ip 检查表达），只能当**待人工核清单**；
- 消费 YAML 的工具：`inst_sweep`（60 id/273 例）、`bit_sweep`（969 例）、`ctrl_sweep`（67）、`fp_sweep`（FP 分组）、`inst_case_run`（单例驱动）、`fetch_probe/gen_probe.py`（借 `inst_sweep` 的编码器）；`tools/testcases/generate_bitcnt_vectors.py` 生成 `bitcnt.yaml`。

## 阶段一：覆盖等价审计（**先做，作为删除的前置门控**）

对每个 YAML id 机械断言 `.S` 载体存在**对应类**：

1. `encoding` ⇒ `.S` 有编码字断言（首点/`*ENC*` 宏）；
2. `semantic` / `boundary` ⇒ 有链式检查点（`TEST_*` 参数 + `__CHECK_RD` / `__LAND_IP` / `__CHECK_MEM`）；
3. `legality`（`ILLI`/`UNDI`/`CFXMEM`）⇒ 有对应 `TEST_FAULT_*`；
4. `overlap` ⇒ 有 `TEST_FAULT_DUAL` 或等价。

**输出**：`<运行期证据目录>/coverage-audit.tsv`（id / yaml 例数 / .S 宏数 / 四类在位情况 / 结论），并对 **37 个告警 id 逐个人工核 3–5 例**并写理由。
**门控化**：把该审计做成可复跑脚本（`tools/testcases/audit_yaml_vs_s.py` 或等价），**审计不全绿 ⇒ 阶段二/三不得开工**。

## 阶段二：保留编码迁 `00-isa-design`

- 新建 `tests/inst/00-isa-design/undi_reserved.S`，承载 `reserved.yaml` 中 **3 条无 id** 的保留编码（word `0x08040001` / `0x1B040001` / `0x58040001`），断言 `UNDI`；
- `reserved.yaml` 其余 6 条 CFXMEM 本来就有 id 与 `.S` 载体，随阶段三删除；
- `check-tests-index` 的「载体↔索引」双向断言需容纳 `00-isa-design`（该目录不是 id 载体，需显式白名单或独立登记；**不得**放宽成"任意目录豁免"）。

## 阶段三：删除 YAML（除阶段二产物）

- `git rm` 28 个 YAML（`atomics/ base/ bitcnt/ clmul/ fp/ rev/ rol/`），删空目录（含 `fma/`/`minmax/`/`roundint/` 三个残留空目录）；
- 同步：`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/inst/inventory.md`、`tests/inst/MIGRATION.md`、`tests/README.md`、`tests/INVENTORY.md`、`docs/Process-09`；
- **门控替代**：`check-inst-asm`（264 id/897 镜像）成为唯一执行门控；`validate_vectors` / `generate_isa_vectors` / `check-generator-sync` / `check-case-ledger` / `check-inst` 里对 YAML 的依赖逐项改指或退役（每项写清改法）。
- 273 例 `sweep_expect.bin` md5 等历史钉：**历史任务书不改写**，但需在 `issues.yaml` 或 `MEMORY` 记「该钉随工具退役失效」。

## 阶段四：sweep 工具退役

- 删 `tools/chipyard/{bit_sweep,ctrl_sweep,fp_sweep,inst_case_run}.py`；
- `inst_sweep.py` **降为库**（去掉 YAML 扫描 CLI，只留编码器/ELF 布局/`dump_reg`/`dump_mem`），供 `fetch_probe/gen_probe.py` 使用；
- `fetch_probe/` 保留（取指探针生成器，非测试判定）；
- `tools/chipyard/mem_sweep.py` 已退役（`040`）；`fp_ref.py` **保留**（生成期工具，标注"不作判据"）；
- 删 `tools/testcases/generate_bitcnt_vectors.py`（其唯一产物是已删的 `bitcnt.yaml`）——若阶段二需要它生成 `undi_reserved.S`，则改用途并说明。

## 验收（逐条贴真实 rc / 现场值）

1. 阶段一审计脚本 rc=0；`coverage-audit.tsv` 全部 `OK`，37 个告警 id 有逐条人工核记录。
2. `git grep -c "\.yaml" tests/inst/` 只剩 `00-isa-design` 相关（预期 0，若 `undi_reserved.S` 是 `.S` 则 YAML 全 0）。
3. 门控全绿：`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-generator-sync`、`check-inst-asm`（264 id/897 镜像）、`check-inst`（Vast+Tiny）、`check-no-residue`、`check-knowledge-refs`、`check-run-artifacts`（若红，核是否全属在途任务）。
4. `grep -rn "inst_sweep\|bit_sweep\|ctrl_sweep\|fp_sweep\|inst_case_run"` 在 `Makefile`/`tools/` 只余「库/说明」；**无断链 import**（`python3 -c "import tools.chipyard.fetch_probe.gen_probe"` 或等价冒烟）。
5. 可达 FAIL 注入 ≥3 路（删 `undi_reserved.S` ⇒ 索引/审计红；把某 id 的 `.S` 改名 ⇒ 双向断言红；注入一个 YAML 依赖残留 ⇒ 门控红），`cp`+md5 还原。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**（夜跑在跑）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. **阶段顺序不可颠倒**：审计绿 → 迁保留编码 → 删 YAML → 退工具；任一步红就停，不许"先删后补"。
5. 只改 `tests/**`、`tools/testcases/**`、`tools/chipyard/**`、`Makefile`（门控接线）、`docs/Process-09*`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
6. 测试派节点、有空位就发（`--jobs` = 核数−2 减占用）；派前 `remote.py status`。

## 待裁定

（实现中写；涉及「某类断言 `.S` 无法表达」时停下写清，不要自造）

## 审阅记录

（待填）
