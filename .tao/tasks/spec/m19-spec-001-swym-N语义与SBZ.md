# m19-spec-001: swym N 语义与 SBZ 合法性（12 位 N、1+N 拍、原子）

**模块**：spec
**项目里程碑**：M19
**依赖**：无
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：已验证

## 背景

用户 2026-11-27 裁定 `swym N` 的精确语义，用于 M19 及后续流水线/超标量的周期口径：

- `N = immu18[11:0]`，12 位有效；
- `immu18[17:12]` **SBZ**，非零 ⇒ `ILLI`；
- `swym 0` 为 1 拍 NOP；`swym N` 总时延 = **1 + N 拍**（N 是额外拍数，不是“执行 N 次 `swym 0`”）；
- **原子**：执行期间不取中断；完成后在下一个指令边界取中断；中断延迟上界 = 1 + N 拍；
- QEMU 不做时延建模（NOP）；gem5 / chipyard 实现时延与原子语义。

本任务只改语义与契约，不改实现。

## 目标

1. `spec/SimRISC-12 §2` 写死上述四条（N 位宽、SBZ/ILLI、1+N、原子中断语义）；同步 operation 注释。
2. `contracts/legality_rules.yaml` 增加 `swym` 高位 SBZ 规则（非零 ⇒ `ILLI`）。
3. `contracts/wuming-cycles.yaml` 的 `swym_oiii_imm` 从固定 `1` 改为 **动态 `1 + N`**（N 取 `immu18[11:0]`）。
4. 检查 `spec/SimRISC-00`/Toolchain 是否还有“约 N+1 倍”“实现可设上限”的旧表述，统一改为本口径。
5. 版本号是否升级、升到多少：**待用户确认**；未确认前只落内容，不擅自升号。

## 验收（逐条贴真实 rc）

1. `make check-legality-drift` / `check-legality-invariants` / `check-contract-relocs` 真实 rc=0（或给出基线红对照）。
2. `check-spec-refs`、`check-spec-numbering` 真实 rc=0；新条款在 `spec/SimRISC-12` 可 grep 到“12 位 / SBZ / 1 + N / 原子”。
3. **可达 FAIL ≥2 路**：① 注入“高位非零不报 ILLI”的规则，合法性门控转红；② 注入“cycles = 1”而非 `1+N`，对应契约检查/派生表转红（或给出可复现的静态断言）。
4. 不改 gem5 / chipyard / QEMU 源码；不升版本号（除非用户当轮确认）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `spec/SimRISC-12`、`spec/SimRISC-00`（若需）、`contracts/legality_rules.yaml`、`contracts/wuming-cycles.yaml`；完成区不写具体 `.work/**` 路径。

## 待裁定

1. **版本号**：未升（`spec/` 册头 0.5.8-rc、`contracts/` 头 0.5.4 均未动）——请用户确认是否升、升到多少。
2. **wuming 周期表的真源归属**：`contracts/wuming-cycles.yaml` 是 `tools/gem5/gen_wuming_cycles.py` 的生成物（真源 = `docs/core-wuming-cycle-model.md` 的实测口径）。本次按任务只改契约表，文档/生成器/gem5 C++ 表未同步 ⇒ `check-wuming-cycles` 维持基线红。把「1+N」落回该文档并重跑生成器，归 `m19-gem5-001`（「必要契约派生」）还是另立任务？

## 完成区

**测试结果**：PASS 26/26（证据脚本正向 16 + 注入自检 10，rc=0）；失败：无
**修改文件**：`spec/SimRISC-12-其它指令.md`（§2 四条 + 附录 B 工具重渲染）、`idl/SimRISC-12.idl`（swym 注释）、`idl/data/exec_anchor.toml`（`idl_check_anchor.py --update`）、`contracts/legality_rules.yaml`（`encode_sbz` 增 swym）、`tools/spec/generate_opcodes.py`（swym 增 `immu18[17:12] == 0`）、`contracts/opcodes.yaml`（重跑生成器；rule_refs 246→247）、`contracts/wuming-cycles.yaml`（swym `1+N`/null/`N`；计数现场重算 206/57）、`spec/.manifests.toml`+`idl/.manifests.toml`（sha 对账）、`.tao/contracts/contract-isa.md`（§13.1 同步）
**验收结果**（真实 rc）：`check-legality-drift`/`check-legality-invariants`/`check-contract-relocs`/`check-spec-refs`/`check-spec-numbering`/`check-opcodes-repro`/`check-rule-refs`/`validate-encoding`/`check-idl-sync`/`check-idl-parse`/`check-idl-exec-anchor`/`check-spec-cite-targets`/`check-asm-list`/`check-asm-prose`/`check-spec-codeblocks`/`check-spec-purity`/`check-spec-changelog`/`check-spec-drift`/`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-vectors` 全 rc=0；`check-isa-coverage` 显式 `--llvm-mc <主仓 llvm-mc>` 后 rc=0（worktree 无 install-host）。
- 基线红（与 HEAD `e23518a0` **错误集逐行相同**）：`check-wuming-cycles`（3 条：yaml 与现解析不一致 + gem5 C++ 两产物缺，本任务前即红）；`check-interface`（294≠309）；`check-manifests-guard`（`.tao/knowledge` 缺 m16 两文件）；`check-milestones-fresh`（他任务台账）；`check-arch-self-test`、`check-writer-guards`、`check-temp-dirs`、`check-width-sizes`（缺 install-host 工具）。
**可达 FAIL ≥3 路**（`run.sh --inject` 实测，均 cp+md5 还原后回绿）：① 去掉 swym 的 `immu18[17:12] == 0` 并重跑生成器 ⇒ `check-legality-drift` rc=2（1 violation）；② 周期写回 `{cycles: '1', value: 1, dynamic: null}` ⇒ 契约断言转红；③ §2 把「SBZ」写成「任意值」⇒ 散文断言转红。
**新发现/坑**：`contracts/wuming-cycles.yaml`、`contracts/opcodes.yaml`、`idl/data/exec_anchor.toml` 都是生成物，「只改契约」必然要连生成器/锚表一起动，否则 `check-opcodes-repro`/`check-idl-exec-anchor`/`check-manifests-guard`（sha）转红；`spec/.manifests.toml`/`idl/.manifests.toml` 的 sha256 无自动更新器，须手工对账。
**遗留问题**：① IDL 未加 SBZ raise（任务「不改实现」，加 raise 须同改 `idl_exec.py` 否则 golden↔执行器分叉），ILLI 由 `encode_sbz`+附录 B 承接，m19-gem5-001/QEMU 实现；② 待裁定 2 项见上。

## 审阅记录

### 第 1 轮 engineer 自审

自审判决：改动逐条对照任务四条目标 + 任务书约束；7 处越界均为**机械派生**（生成物/sha/镜像契约），已披露。无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只改 4 个文件无法满足「同步 operation 注释 / 附录 B 派生」 | ✅已修 | 增 `idl/SimRISC-12.idl`、`idl/data/exec_anchor.toml`、`tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml`、`spec/.manifests.toml`、`idl/.manifests.toml`、`.tao/contracts/contract-isa.md` | 各门控 rc=0（完成区） |
| F2 附录 B 不漏 swym 的 SBZ 规则 | ✅已修 | swym 记录增 legality 表达式，重跑 `gen_legality_list.py --apply` | 附录 B `encode_sbz`（13 条）含 `swym_oiii_imm` |
| F3 手工改 yaml 会导致 `check-manifests-guard` sha 不符 | ✅已修 | 更新 spec/idl 两份 `.manifests.toml` | 该门控错误集与基线逐行相同（仅 m16 两文件缺） |
| F4 yaml 头 `static_rows/dynamic_rows` 与行不一致 | ✅已修 | 现场重算写入 206/57 | `check-wuming-cycles` `ondisk-table` PASS |
| F5 IDL 只同步注释、未加 `raise(Illegal)` | ❌不修 | 未动实现 | 任务「本任务只改语义与契约，不改实现」；加 raise 须同改 `idl_exec.py`，否则 IDL 正文与执行器分叉 |
| F6 wuming 表与生成器/文档不同步 | ⏸延后 | 未动 `docs/core-wuming-cycle-model.md` | 见「待裁定」2；`check-wuming-cycles` 错误集与基线逐行相同 |
| F7 证据脚本首版 `opcodes_ok` 取 `d["instructions"]` 报 TypeError | ✅已修 | 改为顶层列表遍历 | `run.sh --check` 16/16 PASS，rc=0 |

### 第 1 轮 reviewer 验收

**我方重跑（实现 worktree 内相对路径，取被检命令自身退出码）**
1. 验收门控 `make -s check-legality-drift / check-legality-invariants / check-contract-relocs / check-spec-refs / check-spec-numbering` ⇒ 5/5 **rc=0**。
2. 追加 `check-spec-drift / check-spec-changelog / check-spec-purity / check-spec-codeblocks / check-asm-list / check-asm-prose / check-idl-parse / check-cfx-aliases / check-cfx-alias-table / check-cfx-vectors / check-knowledge-refs` ⇒ 11/11 **rc=0**；`tools/llvm/gen_isa_coverage.py --check --llvm-mc <主仓 llvm-mc>` **rc=0**（worktree 无 install-host，与完成区披露一致）。
3. 运行期证据目录内的 `run.sh` 重跑 ⇒ `PASS=26 FAIL=0`、**rc=0**，与完成区「26/26」一致。
4. 四要点 grep：`spec/SimRISC-12` §2 命中「12 位 / SBZ / 1 + N 拍 / 原子·不取中断·下一个指令边界 / 4095」；「N+1 倍」「可设上限」「时延约为」在 `spec/`、`contracts/`、`idl/`、`tools/`、`docs/`、`.tao/contracts/`、`.tao/knowledge/` 零命中（唯一含「时延上限」的是新句「无时延上限」；旧句仅存只读 `.tao/archive/`）。
5. 计数现场重算：`wuming-cycles.yaml` `dynamic=None` 206 行 / 非 None 57 行 = 头部 206/57 ✓；`opcodes.yaml` 非空 `rule_refs` = 247 ✓；附录 B `encode_sbz` 13 条含 `swym_oiii_imm` ✓。

**独立注入（reviewer 自做，非采信完成区）**
- `cp` 备份 `contracts/wuming-cycles.yaml`（md5 `114a4f78…`）→ swym 行改回 `cycles:'1', value:1, dynamic:null` → 重跑同一 `run.sh --check` ⇒ `[FAIL] wuming-cycles swym = 1+N 动态`，`PASS=15 FAIL=1`，**rc=1**；`cp` 还原 → md5 复等 → `--check` 回 `PASS=16 FAIL=0` **rc=0**。
- 脚本自带注入①（去 `immu18[17:12]==0` 并重跑生成器 ⇒ `check-legality-drift` **rc=2**、1 violation）、②③（契约/散文断言转红）三路均 cp+md5 还原回绿、逐条 PASS。脚本审核：5 条断言各有可达 FAIL，无恒真、无两支同果，计数现场派生。

**基线红（基线 `e23518a0` 独立临时 worktree 重跑 8 门控，均 rc=2）**：`check-wuming-cycles / check-interface / check-manifests-guard / check-milestones-fresh / check-arch-self-test / check-writer-guards / check-temp-dirs / check-width-sizes` 与当前输出 `diff` 仅环境差异（绝对路径、mtime 25.6↔25.5 h、worktree 计数 119↔118、ignore 计数 0↔1），**错误集逐行相同**：manifests-guard 同为 `.tao/knowledge` 缺 m16 两文件；interface 同为 `N (294) != independent count (309)`；wuming 同为 3 条 FAIL 同文。

**约束核验**
- commit `2bf528dd` 共 11 文件；`git diff --name-only e23518a0..HEAD | grep -E 'gem5|qemu|chipyard'` 空 ⇒ 未动实现 ✓。范围外 7 文件（生成器/生成物/manifests sha/镜像契约/IDL 注释）均为派生同步且完成区已披露，`check-opcodes-repro`/`check-idl-exec-anchor`/`check-spec-drift` rc=0 佐证必需。
- 版本号未升：spec 册头 `0.5.8-rc`、`legality_rules.yaml` 头 `0.5.4`，diff 无版本行 ✓（待用户确认口径守住）。
- IDL 仅同步注释、未加 raise：`idl/SimRISC-12.idl` diff 3 行全为 `#`，`idl_exec.py` 未动 ⇒ 与「不改实现」一致 ✓。
- 任务书/完成区无具体 `.work/**` 路径 ✓；注入还原后 `git status --porcelain -uall` 空、7 个目标文件 md5 与注入前快照逐一相等 ✓。

**遗留（不阻断，提请 architect 裁定）**：① `wuming-cycles.yaml` 真源 = 文档+生成器，本次按任务只改契约 ⇒ `artifact-up-to-date` 维持基线红，重跑生成器会把 `1+N` 冲回 `1`（即「待裁定 2」，需定归属任务）；② IDL 未加 SBZ raise（须同改 `idl_exec.py`，归后继任务）。

**判决：Accepted** —— 验收命令块在我方重跑下全绿、可达 FAIL ≥2 路（实为 3 路）真实且可还原回绿、基线红错误集逐行相同、无越界实现改动、版本号未升。
