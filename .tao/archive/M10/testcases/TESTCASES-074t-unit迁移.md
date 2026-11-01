# TESTCASES-074t: unit 迁移（LLVM/lld/qemu/picolibc）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：已验证

## 目标（P4）
1. `tests/llvm/lit/MC|CodeGen`、`llvm/codegen/m3/m4/m6`、`llvm/ir-lli`、picolibc 自测 → `tests/unit/{llvm,picolibc}/`。
2. 新门控 `check-unit`（lit + codegen + ir-lli + picolibc smoke）；旧 `check-lit`/`test-codegen`/`test-elf`/`test-m6`/`check-picolibc-tests` 保留别名。
3. 更新 `tests/unit.yaml`、ledger、Makefile/文档。

## 验收
- `check-unit` 绿；旧目标别名等价；`make check`/`check-modules` 绿；picolibc 仍在 unit。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**测试结果**：`.work/evidence/TESTCASES-074t/run.sh` ⇒ **PASS 21/21，RUN_EXIT=0**（约 7 min）；2 处注入（`unit.yaml` 坏条目 ⇒ `check-tests-index` rc=1；ledger 删行 ⇒ `check-case-ledger` rc=1）各经 `cp` 备份 + md5 对账还原 ⇒ 回绿。

**修改文件**（只搬家/接线/兼容，**无期望值改动**）：
- 搬迁（`git mv`；旧路径留符号链接）：`tests/llvm/{lit,codegen,ir-lli}` → `tests/unit/llvm/`；`codegen/m5` 链接重定向为 `../../../arch/umon`。
- 新增：`tests/unit/llvm/README.md`、`tests/unit/picolibc/README.md`、`tests/unit.yaml`（187 条：llvm 186 + picolibc 1）、`.work/evidence/TESTCASES-074t/run.sh`。
- 门控：`Makefile`（+`check-unit`（L2，含 ir-lli 步骤）；`check-modules` 成员收拢为 `check-unit`；lit/codegen/elf 走新路径；`GATE_LOCKED_TARGETS`/`.PHONY`/help/注释）。
- 台账/工具：`tests/case-ledger.tsv`（502 条 lit 行**仅路径重映射**，排序归一后与迁移前逐字节一致）；`tools/infra/check_case_ledger.py`（lit 真实路径）；`tools/testcases/diff_ir_lli.py`（manifest 默认新路径）+ `validate_{codegen,elf,m6,mc}_vectors.py`（路径常量）。
- 文档：`tests/{README,INVENTORY}.md`、`docs/Process-09`（§2 P4 注 + §11）、`docs/Process-05`、`spec/README.md`（路径）、`milestones.md`、本任务书。

**验收结果**：
- `make check` rc=0（`repository checks (L1): PASS`）；`check-tests-index` rc=0（`unit=187 / total=237`）；`check-case-ledger` rc=0（`现场身份 1958 条`）。
- `make check-unit` rc=0（lit 154/154；codegen 15/15；elf 5/5；ir-lli 19/19；picolibc fast 20：18 pass / 0 fail / 2 excluded / 0 blocked）。
- 旧命令等价：`check-lit` rc=0（154/154）、`test-codegen` rc=0（15/15）、`test-elf` rc=0（5/5）、`test-m6` rc=0（lit-full 12/12 + ir-lli 19/19 + embench 38/38）；`make check-modules` rc=0。
- **期望值/生成物未变**：迁移文件对 `HEAD:tests/llvm/**` 全量对账 204 文件，除 `tests/llvm→tests/unit/llvm` 路径重写外**仅 1 处**非路径改动（`validate_cfx_vectors.py` 的 REPO 定位改为向上找仓库根）；4 个独立 oracle 校验 rc=0（58 / 42 / 102 / 78 checks）。

**新发现/坑**：
① 目录符号链接**不能**替代递归 glob（`tests/llvm/lit/**/*.s` 在链接目录上 0 命中）⇒ ledger 门控必须改真路径；`os.walk`/单层 glob 可穿透顶层链接（ir-lli/codegen 驱动因此零改动）。
② 仓库根按 `__file__` 上溯**固定层数**会随搬家失效（`validate_cfx_vectors` 5→6 层，实测读到 `tests/contracts/`）⇒ 改为向上找 `manifests/install-dirs.lock.toml`。
③ `.work/log/**` 新文件名受 `check-run-artifacts` A3 约束：空格/`:`/中文即红 ⇒ 证据脚本内部日志统一 `TESTCASES-074t-evidence-<nn>-<ascii-slug>.log`。
④ `check-unit` 以门控目标为前置（`check-lit`/`test-codegen`/`test-elf`/`check-picolibc-tests`）在父锁内嵌套放行，实测 2m27s。

**遗留问题**：
① 旧路径符号链接（`tests/llvm/{lit,codegen,ir-lli}` + m5 重定向）待 `TESTCASES-076t` 删除；届时 `tools/llvm/*` 与 `tools/integ/*` 的旧路径默认值（`check_interface_alignment`、`gen_isa_coverage`、`check_lit_bytes`、`run_codegen_e2e`/`run_elf_e2e`）需一并改新路径（本任务未改，链接下均可用）。
② `tests/unit/llvm/lit/tools/DADAO/` 仍为占位（无测试），未入索引/门控（迁移前亦然）。
③ `check-unit` 为 L2 代表集；L3 全量仍由 `test-m6` 承担，`codegen/m6` 仍手工（迁移前口径未改）。
④ 未跑 `check-full`/夜跑（任务约束：只跑 smoke/定向）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`Makefile` 全部改动行；`tests/unit.yaml`（逐条 field/file 存在性由门控现场校验）；三个旧路径符号链接与 m5 目标；`check_case_ledger.py`/`diff_ir_lli.py`/4 个 validator 的路径常量；证据脚本逐检查项（含注入与还原）；`tests/README`/`INVENTORY`/`Process-09` 改动。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 递归 glob 不穿透目录符号链接 ⇒ `check-case-ledger` 现场 0 行 lit | ✅已修 | `check_case_ledger.py` lit glob 改 `tests/unit/llvm/lit`；ledger `--write` | 502 行 path-only；排序归一后 diff 空；门控 rc=0 |
| `validate_cfx_vectors.py` 固定 5 层上溯 ⇒ 读到 `tests/contracts/opcodes.yaml`（`make check` rc=2） | ✅已修 | REPO 改为向上找 `manifests/install-dirs.lock.toml` | 新/旧路径各 rc=0（16 条向量 0 错误）；`make check` PASS |
| `ir-lli/manifest.yaml` 的 `corpus_roots`/条目仍指旧路径 | ✅已修 | 全量替换为 `tests/unit/llvm/...`；driver 默认 manifest 同步 | `diff_ir_lli` 19/19 matched、PASS |
| 证据脚本 `cd ../../` 少一层（到 `.work`）⇒ 18/19 假红 | ✅已修 | 改 `../../..`；并加「备份 md5 非空」断言防恒真 | 二跑 21/21 PASS |
| 证据脚本内部日志名含空格/`:`/中文 ⇒ `check-run-artifacts` A3 红 | ✅已修 | slug 化 `TESTCASES-074t-evidence-<nn>-<slug>.log`；删除旧非法名日志 | 脚本末项 `make check` rc=0 |
| m5 符号链接按旧目录深度写 `../../arch/umon` ⇒ 迁后指向不存在路径 | ✅已修 | 改为 `../../../arch/umon` | `readlink -f` = `tests/arch/umon`；check-arch-smoke 未受影响 |
| `check-modules` 同时列旧成员与新 `check-unit` ⇒ 重复执行 | ✅已修（明示） | L2 只列 `check-unit`；旧目标名保留可单独调用 | `check-modules` rc=0（8m37） |

**判决**：改动范围内无未修 finding；遗留 ①–④ 均为**迁移前既有口径/任务约束**（旧入口待 076t 删除、占位目录、L3 口径、未跑全量），不阻断。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-27）

**重跑记录**（reviewer 亲自执行，`80a32201`，审前/审后 `git status -uall` 均 0 行）：
- `bash .work/evidence/TESTCASES-074t/run.sh` ⇒ **PASS (21/21 checks)，RUN_EXIT=0**；含 `check-unit` rc=0（lit 154/154、codegen 15/15、elf 5/5、ir-lli diff PASS、picolibc fast 20：18 pass/0 fail/2 excluded/0 blocked）、`check-lit`/`test-codegen`/`test-elf`/`test-m6` 各 rc=0、`make check` rc=0、旧路径符号链接 3 项 + 旧 manifest `diff_ir_lli` rc=0；脚本内 2 处注入（unit.yaml 坏条目、ledger 删行）各 rc=1 → cp+md5 还原 → 回绿。
- `make check-modules` rc=0（`module checks (L2): PASS`）；4 个独立 oracle 全 rc=0（58 / 42 / 102 / 78 checks + mc 78 条 0 错误）。

**独立反例**（不复用 engineer 注入）：`cp` 备份 `tests/unit/llvm/lit/MC/DADAO/basic-encoding.s`（md5 `e5fd0a99…`）→ 改第 10 行期望字节 `59 20 00 01 → 59 20 00 02` ⇒ `check-lit` **rc=2**（153/154，1 failed）、`check-unit` **rc=2**（同一 FAIL 路径）→ `cp` 还原（md5 相等）⇒ `check-lit` rc=0（154/154）、`check-unit` rc=0。

**语义不变对账**（脚本全量，非抽样）：`HEAD^:tests/llvm/**` 204 文件 → `tests/unit/llvm/` **0 缺失**；内容差异仅 20 文件，归一 `tests/llvm→tests/unit/llvm` 后非路径改动仅 2 处：`codegen/m5` 符号链接深度（`../../`→`../../../`，`readlink -f`= `tests/arch/umon`）+ `validate_cfx_vectors.py` 根定位（固定层→向上找 `manifests/install-dirs.lock.toml`）。ledger 1962 行：排序归一后与「502 行路径重映射」版本逐字节一致。索引现场 `unit=187 / total=237`。`tests/unit.yaml` 现场 187 条。

**约束核验**：① `check-unit` 在 `.PHONY`/`GATE_LOCKED_TARGETS`/L2（`check-modules` 成员收拢为 `check-unit`，无重复执行；L3 = `check-inst check-arch test-m6` 无重复）✅；② 旧门控全保留别名、`run_codegen_e2e/elf` 显式传新路径、`check-lit-full` 传 `--full-dir/--fast-file`（`check_lit_gen.py` 原生支持该参数）✅；③ 无期望值/断言弱化（对账+4 oracle 证明）✅；④ 范围外 3 处（`check_case_ledger.py` 真实路径 glob、`spec/README.md`/`docs/Process-05` 旧路径）均为必要路径重写、无语义改动 ✅；⑤ 无越界/残留（审后 `git status` 0 行）✅。m3 非搬迁遗漏（architect 已核实 `HEAD^` 无 `tests/llvm/codegen/m3`）。

**剩余风险**（不阻断，已列遗留①–④）：`tools/{llvm,integ}/*` 旧路径默认值经符号链接可达，076t 删链接时须一并改。

**判决：Accepted**

### architect 收尾（2026-10-27）
- reviewer 首次会话返回「Code Mode 无 shell 工具」，未判决、未落盘；按 §3.5 重试 **1/3** 成功（Accepted，证据 21/21）。
- 已核实 `HEAD^` 无 `tests/llvm/codegen/m3`，任务书「m3/m4/m6」为泛指，非遗漏。
