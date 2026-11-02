# TESTCASES-084t: 测试残留清理（e2e/llvm 链接/wrapper/spec 路径）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t（已 `已验证`）
**状态**：已验证

## 背景
`076t` 收口后仍有旧口径残留：

- `tests/e2e/`（31 个工具链 E2E `.c/.s/.lds` + `lit/`）不在四 scope；当前仍被 `check-lit` 的 Makefile 引用；
- `tests/llvm/` 只剩 `lit`/`codegen`/`ir-lli` 三个兼容符号链接；`tools/llvm` 部分默认路径仍指向它；
- `tools/qemu/min_rom_probe_*`（32 个）是 `073t` 留下的薄 wrapper，真实实现在 `tools/testcases/arch/`；
- `spec/README.md` 仍有 `tests/e2e`、`tools/integ/check_interface_alignment.py` 旧路径（`spec/` 只读锁，用户 2026-10-27 已授权修改）；
- 4 个组件补丁注释仍引用旧测试路径（`tests/scripts`/`tools/integ`）；
- 5 个 `.gitkeep`、若干 `__pycache__` 为冗余/运行垃圾。

## 目标
1. **e2e 归位**：`tests/e2e/` → `tests/unit/llvm/e2e/`（工具链 E2E 属 unit/lit）；更新 Makefile `check-lit`、`tests/e2e/lit/lit.cfg.py` 相对路径、`tests/unit/llvm/lit` 引用、README/INVENTORY。
2. **删除 `tests/llvm` 符号链接**：先把 `tools/llvm/{check_lit_bytes,gen_isa_coverage,...}` 默认路径改到 `tests/unit/llvm/...`，重生成 ISA 矩阵，再删链接。
3. **删除 32 个 `tools/qemu/min_rom_probe_*` wrapper**：确认 `tools/testcases/arch/` 原件可用、引用已改；保留旧命令说明或删除。
4. **spec/README**：`tests/e2e` → `tests/unit/llvm/e2e`；`tools/integ/...` → `tools/infra/...`；更新 `manifests/spec-readonly.lock.toml` 的 sha（用户已授权）。
5. **组件补丁注释**：4 个 patch 文件里的旧路径改为语义说明（不交叉引用测试路径），重新生成补丁树并 `check-patch-tree`。
6. **清垃圾**：删 5 个 `.gitkeep`、`__pycache__`；确认无断链。
7. 不改测试期望/断言；只做路径/归属/注释清理。

## 验收
- `tests/e2e/`、`tests/llvm/` 不存在；`tools/qemu/min_rom_probe_*` 0 个；旧路径代码/配置面 grep 0；
- `make check` rc=0；`make check-modules` rc=0；`check-tests-index`/`check-case-ledger` rc=0；`check-patch-tree` rc=0；`check-spec-readonly` rc=0；
- `check-lit` 全绿（当前 158 基线，现场统计）；e2e 用例从新路径可跑；
- 证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-084t/`。

## 约束
- 只改测试/路径/文档/补丁注释；不改 spec 正文语义、不改 QEMU/LLVM 语义。
- **不跑 `check-full`/夜跑**；长构建申报。
- **不提交、不 push**；`spec/` 修改须同步锁 sha。

## 完成区

**状态**：已验证

**测试结果**：`make check` rc=0；`make check-modules` rc=0；`check-tests-index`（240 条）/`check-case-ledger`（1958）/`check-patch-tree`（205 patches）/`check-spec-readonly`（21 册）rc=0；`check-lit` 158/158、e2e 14/14（新路径）。一键证据 `.work/evidence/TESTCASES-084t/run.sh` 26/26；`--inject` 8/8（注入→FAIL→`cp`+md5 还原→回绿）。

**修改文件**：
- 移动 `tests/e2e/**`（44 个）→ `tests/unit/llvm/e2e/`（`lit.cfg.py` 夹具改由 repo-root 解析）；删 `tests/llvm/{lit,codegen,ir-lli}` 链接、`tools/qemu/min_rom_probe_*`（32 个 wrapper）、5 个 `.gitkeep`、`tests/**`+`tools/**` 的 `__pycache__`。
- 路径/注释：`Makefile`、`.gitignore`、`spec/README.md`、`docs/{Process-05,Process-09,Machine-00}`、`tests/{README,INVENTORY,arch/README,shared/README,unit/llvm/README}`、`abi-narrow-extend.ll`、`tools/llvm/{check_lit_bytes,gen_isa_coverage,gen_asm_list,validate_instrinfo}.py`+矩阵 md、`tools/infra/check_interface_alignment.py`、`tools/testcases/{check_lit_gen,generate_lit_vectors}.py`、`tools/testcases/arch/*`（README+11 处 usage）、`.tao/contracts/contract-asm.md`。
- 补丁：llvm-project 3 份 + musl 2 份（仅注释；`series` 98/25 不变）+ 两组件 changelog。
- 越界披露：`tests/unit/llvm/ir-lli/manifest.yaml`（补 M10 6 个 `.ll` 分类，解 L2 既有红，见审阅记录 F1）；`spec/README.md` 不在 sha 锁内（`check-spec-readonly` 21/21 未变，锁无需改）；`docs/Process-05`/`Process-09`/`Machine-00` 与 `.tao/contracts/contract-asm.md` 仅旧路径同步（无规则/语义变更，任务书未单列，按必要路径重写披露）。

**验收结果**：`tests/e2e`/`tests/llvm` absent；旧路径代码/配置/文档 grep 0；wrapper 0（原件 32 全在 `tools/testcases/arch/`）；`tests/**` 的 `.gitkeep` 0、`__pycache__` 0；无断链（`tests/unit/llvm/codegen/m5` 旧链接仍指向 `arch/umon`，非断链、不在本册范围）。ISA 矩阵 `--check` PASS、`check_lit_bytes` 238 patterns OK。

**新发现/坑**：① llvm-lit 对不存在路径**静默忽略**（rc=0）⇒ 反例须改 `lit.cfg.py` 的替换值，不能只改 Makefile 参数；② `check_interface_alignment.py`/`check_lit_gen.py`/`generate_lit_vectors.py` 仍用 `"tests","llvm"` 拼接默认值，被旧符号链接掩盖，删链后才暴露；③ musl 源注释一变 ⇒ `check-musl-freshness` 红，须在 install-host 重建后再跑 `build-musl{,-shared}`（顺序敏感）；④ e2e 的 `lit.cfg.py` 原按固定 `../..` 取夹具，移动后深度变，改由 repo-root 解析。

**遗留问题**：无。`ir-lli` 驱动把 host `lli` 对 `dadao-unknown-elf` triple 的拒绝（rc=1）当值记录，属既有口径缺口，本册以 `host-unsupported` 登记两例。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 L2 `ir-lli` 6 个 M10 `.ll` 未分类（既有红，LLVM-137t/138t/139t 引入） | ✅已修 | 1 include + 2 `host-unsupported`（声明 dadao triple，host lli 拒跑）+ 3 structural `no-value-entry` | `diff_ir_lli` 20/20 PASS；`make check-modules` rc=0 |
| F2 另有 3 处旧路径默认值 | ✅已修 | `tests/llvm`→`tests/unit/llvm`（interface/lit_gen/generate_lit_vectors） | `make check` rc=0；证据 C17–C20 PASS |
| F3 musl 注释改动使 freshness 红 | ✅已修 | L2 重建工具链后重跑 `build-musl{,-shared}` | `check-musl-freshness` rc=0；L1 rc=0 |
| F4 注入 I2 只改 Makefile 参数时 llvm-lit 忽略缺路径仍 rc=0 | ✅已修 | 注入改为破坏 `lit.cfg.py` 的 `%e2e_dir` | `--inject` I2 rc=1；还原后 14/14 |
| F5 `spec/README.md` 是否需同步 sha | ❌不修（无须） | 该文件不在 `spec-readonly.lock.toml`（Process-06 §5） | `check-spec-readonly` 21/21 OK |
| F6 `tests/unit/llvm/codegen/m5` 旧链接仍存 | ⏸延后 | 非 `tests/llvm` 三链接之一，指向 `tests/arch/umon` 未断 | `find -type l` 扫描 0 断链 |

**判决**：无未修 finding，状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，非采信完成区）**
- `bash .work/evidence/TESTCASES-084t/run.sh` → `checks=26 passed=26 failed=0`，`RUN_RC=0`；关键现场值：`check-lit` discovered=158/passed=158、e2e discovered=passed=14（==14 个 `.test`）、`make check` L1 PASS、`make check-modules` L2 PASS、`check-tests-index` 240、`check-case-ledger` 1958、`check-patch-tree` 205 patches、`check-spec-readonly` 21 册，均 rc=0。
- `run.sh --inject` → `checks=8 passed=8`，rc=0；I2 注入后 e2e lit rc=1、`cp`+md5 还原相等、回绿 14/14。
- **独立反例（reviewer 自做，非 engineer 自检）**：`git show c58abd87^:...min_rom_probe_005t.py` 恢复旧 wrapper + `ln -s ../unit/llvm/lit tests/llvm/lit` 恢复旧链接 → 重跑同一 `run.sh` **rc=1**（C1 FAIL hits=1、C3 FAIL present）；`rm`+md5 还原（未用 git checkout/restore/stash）→ 清门控再生成的 `__pycache__` 后重跑 **26/26 PASS rc=0**。
- 盘上事实：`tests/e2e`/`tests/llvm` absent、wrapper 0、arch 原件 32、`.gitkeep` 0、`tests/unit/llvm/codegen/m5` 链接未断；旧路径 grep（排除 `.tao`/changelog）全局 0。

**约束核验**：无测试期望/断言改动（e2e 重命名 44 文件中仅 9 个改内容，逐行核为路径文本；`abi-narrow-extend.ll` 仅注释）；补丁仅注释行（5 份 patch 改动行全为 `//`/`*` 注释 + index/hash 头；`series` 98/25 未动）；`spec/README.md` 不在锁内（lock 文件明示）⇒ 锁 sha 无须更新；`manifest.yaml` +6 条为解 137–139 引入的 L2 既有红（父提交磁盘 6 个 `.ll` 未分类，`diff_ir_lli` 闭包必红），分类正确（3 lit→`no-value-entry`、1 include、2 `host-unsupported`），越界已披露；完成区数字与我重跑逐项一致；工作区审前/审后 `git status -uall` 均 0 行。

**发现（非阻断，建议 architect 收尾修正 run.sh）**：F-R1 `run.sh` C4/C5 从 HEAD 派生 wrapper 清单，c58abd87 提交后清单为空 ⇒ 两断言恒真（注入恢复 wrapper 时仍 PASS）；同回归由 C1 实测捕获（hits=1，脚本 rc=1），建议改从 `c58abd87^` 或固化清单派生。F-R2 `run.sh` 非幂等：门控运行会再生成 `tools/**/__pycache__`（12 个，gitignored），连续第二次运行 C9 红；建议 C9 前清理或改判「是否被 git 跟踪」。剩余风险：`.tao/adr`/`.tao/archive` 历史层仍含旧路径（分层规范不改），全仓 grep 门控须排除 `.tao`。

**判决**：**Accepted**（验收命令块在 reviewer 重跑下全绿、独立反例注入→FAIL→还原→回绿成立、硬约束无违反；F-R1/F-R2 为证据脚本健壮性改进项，不影响本册交付判据）。

### architect 收尾（2026-10-28）
- reviewer Accepted；F-R1/F-R2 证据脚本已修（C4/C5 锚 `c58abd87^`、C9 改核 tracked `__pycache__`），重跑 26/26、注入 8/8。
