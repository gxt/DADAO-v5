# SPEC-171t: 契约悬空引用 13 条 + `rrrr` 单目的三源形态入格式表（`ISS-219`/`ISS-331`）

**模块**：spec
**项目里程碑**：M9（收尾前，用户 2026-10-24 裁定「M9 内做」）
**依赖**：`SPEC-167t`（册名/结构已稳定）
**状态**：已验证

## 立项来源

- `ISS-219`：契约正文存在 **13 条小节级悬空引用**（`INFRA-080t` 门控诊断发现）
- `ISS-331`：`Toolchain-01 §6` 格式表缺「`rrrr` 单目的 + 三源」形态；`check_asm_prose` 的 R6 假设 `rrrr` 必带 `{}` ⇒ 该形态无字面量门控（`ftfma`/`fofma` 受此影响）

## 目标

1. 逐条修正 13 条悬空引用（改指现存小节或删除）；每条给出"原指向 → 新指向 / 删除理由"。
2. `Toolchain-01 §6` 格式表补「`rrrr`：1 目的 + 3 源」（与双目的 `{rdHA, rdHB}` 区分写法）。
3. `check_asm_prose` 的 R6 改为**按实际形态判定**（单目的 rrrr 不要求 `{}`），并补 1 条正例（`ftfma rf8, rf9, rf10, rf11`）+ 1 条反例（把单目的写成 `{}` ⇒ 红）。

## 验收

1. `check_spec_refs` / `check_spec_cite_targets` / `check-contracts-dir` rc=0；13 条悬空 **0**。
2. `check-asm-prose --strict` rc=0；`ftfma` 单目的形态有门控覆盖（注入错写法 ⇒ 红）。
3. **可达 FAIL ≥2**：① 塞回一条悬空引用 ⇒ 契约门控红；② 把 `ftfma` 写成双目的 `{}` ⇒ prose 红。
4. 证据 `.work/evidence/<任务ID>/run.sh`。
5. 受影响门控 + `make check`(L1) rc=0。

## 约束

- 不改指令语义/编码；不 commit/push；开工 `git switch -c SPEC-171t`；临时目录 `/tmp/opencode/SPEC-171t/`。

---

## 完成区

**测试结果**：通过 5/5 验收项。`make check`(L1) rc=0（`/tmp/opencode/SPEC-171t/make-check-final2.log`）；证据脚本 16/16 断言 PASS（`.work/evidence/SPEC-171t/run.sh`，rc=0）。
**修改文件**：`.tao/contracts/contract-abi.md`、`.tao/contracts/contract-elf.md`、`.tao/contracts/contract-dynlink.md`、`spec/Toolchain-01-汇编语言.md`、`tools/spec/check_asm_prose.py`、`tools/infra/check_knowledge_refs.py`、`manifests/spec-readonly.lock.toml`（授权改册的同一变更内重算 sha256，见下「授权」）、本册；证据 `.work/evidence/SPEC-171t/run.sh`（`.work/` 不入库）。
**验收结果**：
1. 13 条处置（行号为改前；均为「改指现存小节」，无删除）：`contract-abi.md:147/354` `contract-isa.md §5.4–§5.6` → **§8.6**（压栈/弹栈流程）；`contract-elf.md:98` `§4.7` → **§8**（控制流：分支/call/jump）；`contract-elf.md:129/184` `§4.1.1` → **§3.1.1**（单 load/store：imms12 字段 + `ld.o`/`st.o` 8B 对齐）；`contract-dynlink.md:65/73/92/219/231/293/296/310` `ADR-0018 C6` → **`contract-abi.md §4.5`**（C6=CSR/reserved 不分配，ADR-0018 自述「C6 归 ABI」）。
2. 门控 rc：`check_spec_refs` 0 / `check_spec_cite_targets` 0 / `check-contracts-dir` 0 / `check-knowledge-refs` 0（小节级悬空 **0**，contracts 面受检 572 条、现场统计）/ `check-asm-prose --strict` 0 / `check-spec-codeblocks` 0 / `check-spec-readonly` 0 / `check-spec-drift` 0 / `check-spec-numbering`·`changelog`·`purity` 0 / L1 0。
3. 可达 FAIL 2 条（证据脚本内置）：① `ftfma {rf8, rf9}, rf10, rf11` ⇒ `R6(rrrr单目的不得带{})` rc=1；② 塞回 `contract-isa.md §5.6` ⇒「悬空小节级互指」rc=1；均 cp+md5 还原并复绿。
4. 格式表/R6：**任务书写 `Toolchain-01 §6` 有误**——§6 是「伪指令」，格式表实际在 **§5**，故落在 §5 表新增 `rrrr`（单目的）行 + §4.2 新增「单目的指令」bullet + §5 两形态对照 `simrisc` 示例。R6 改为读 `opcodes.yaml` 的 `fields[].role`：2 个 dst ⇒ 要求 `{}`；1 个 dst（`ftfma`/`fofma`，非 `cs.*`）⇒ 禁 `{}` 且须恰 4 操作数；`cs.*` 的 `{}` 归 R2b。
5. `check-knowledge-refs` 的 (B) 面由「限 `.tao/knowledge`」扩为 **knowledge + contracts 双面**（各自空转即 FAIL）——这是使验收 3① 可达的必要改动（原判据不扫契约，塞回悬空不会红）。
**授权**：`spec/` 改动授权原话（渠道 = 主会话下发，本子代理无法直问用户）= 本任务书 §目标 2「`Toolchain-01 §6` 格式表补「`rrrr`：1 目的 + 3 源」（与双目的 `{rdHA, rdHB}` 写法区分）」；册版本**不变**（先例 `ADR-0034` / `SPEC-166t`：补记既有形态、编码/语义不变，改动手续落锁注释）。
**新发现/坑**：① 任务书节号错（§6→§5）与 `INFRA-080t` 诊断行号已漂移（13 条现为 147/354/98/129/184 + 8 行；任务书/ISS 记的是旧行号）——按 token 而非行号定位；② `ISS-219` notes 里的复现命令 monkeypatch `m._SECTION_SCAN_DIR` 已失效（改为 `_SECTION_SCAN_DIRS`），收尾时须同步该 notes 并把 `ISS-219`/`ISS-331` 置 `closed`；③ `_FORMAT_OP_COUNTS["rrrr"]={3,4}` 对「双目的/单目的」共用计数集，单目的形态的「恰 4 操作数」须另判（本次补 `R6(单目的rrrr须4操作数)`）。
**遗留问题**：① 自审 F4（`ISS-219` notes 复现命令 `_SECTION_SCAN_DIR` 已改名）归主会话 `/complete` 同步台账，不涉代码；② 其余无。L1 在 R6 收紧后复跑 rc=0；证据脚本可重复执行且自带还原对账。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动；findings 与处置如下。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 R6 单目的只禁 `{}` 不够：3 操作数的 `ftfma` 仍可漏过（`rrrr` 计数集共用 3/4） | ✅已修 | `check_asm_prose.py` 单目的分支补「须恰 4 操作数」 | `check-asm-prose --strict` rc=0；注入双目的形命中 `R6(rrrr单目的不得带{})` |
| F2 注入①首版报 `R6(单目的rrrr须4操作数)`（`{…}` 计 1 个操作数），与「写成双目的」语义不符 | ✅已修 | 单目的分支先判 `{`、再判计数 | 证据 C5 hit=0（命中 `R6(rrrr单目的不得带{})`） |
| F3 契约面并入 (B) 后若某目录缺席会静默放过 | ✅已修 | `check_knowledge_refs.py` 逐面计数 + 逐面空转 FAIL（替换原合并计数判据） | `check-knowledge-refs` 打印两面校验数（47 / 572）；目录缺失即 0 ⇒ FAIL |
| F4 只扩扫描面而不改 `ISS-219` 复现命令会误导后人 | ⏸延后 | 不改台账（知识库更新归主会话 `/complete`） | 已在完成区「新发现/坑 ②」登记 |
| F5 spec 改动未同步只读锁 ⇒ `check-spec-readonly` 红 | ✅已修 | 同变更内更新 `manifests/spec-readonly.lock.toml` sha256 + 授权注释 | `check-spec-readonly`: 21 册 OK |

### 第 1 轮 reviewer 验收

**重跑（本人执行，非采信完成区）**：`check_spec_refs`/`check_spec_cite_targets`/`check_contracts_dir`/`check_knowledge_refs` rc 均=0（悬空=0；两面 47/572 条受检，非空转）；`make check-spec-readonly` rc=0（21 册 OK，锁 sha `535a538d…` = 实际文件 sha，含 SPEC-171t 授权注释）；`make check`(L1) rc=0；证据脚本 `bash .work/evidence/SPEC-171t/run.sh` 16/16 PASS、EVIDENCE_EXIT=0。

**13 条核对**：`contract-abi.md:147/354`→`contract-isa.md §8.6`（存在，压栈/弹栈流程，2 条）、`contract-elf.md:98`→`§8`（控制流指令，1 条）、`contract-elf.md:129/184`→`§3.1.1`（单 load/store，2 条）、`contract-dynlink.md:65/73/92/219/231/293/296/310`→`contract-abi.md §4.5`（8 条），2+1+2+8=13，grep 实测计数与声称一致；旧 token（§5.6/§4.7/§4.1.1/`ADR-0018 C6`）残留 0。目标小节标题语义相符。

**R6 两形态（独立注入，cp+md5 还原）**：`ftfma {rf8, rf9}, rf10, rf11` ⇒ rc=1 命中 `R6(rrrr单目的不得带{})`；`add.uo rd8, rd9, rd10, rd11`（双目的去 `{}`）⇒ rc=1 命中 `R6(rrrr缺{})`；对照 `cs.eq {rd8, rd0}?, rd9, rd10` ⇒ rc=0（cs.* 仍归 R2b，不误伤）；`cs.eq` 裸寄存器 ⇒ R2+R6 双红（可达）。opcodes.yaml 实测：ftfma/fofma 1 dst、add.uo 等 2 dst、cs.* 1 dst（由 `cs.` 前缀豁免）。

**门控增强评估**：(B) 面扩 contracts 后无假红（rc=0；抽 `contract-abi.md §1.6`、`contract-isa.md §2.3–§2.4` 等正常引用未误报）；逐面空转即 FAIL 为 fail-closed（两面 47/572 均非 0，不触发）。注入② `contract-abi.md:147` 塞回 `§5.6` ⇒ rc=1 报悬空，还原回绿。

**披露核对**：任务书写 §6、实为 §5——§6 确为「伪指令」、格式表在 §5，完成区第 4 条 + 锁注释均已如实记录；§5 表含「`rrrr`（单目的）」行 + 两形态 simrisc 对照块，§4.2 含「单目的指令」bullet。注入前后工作区快照对账一致（`git status` 空、md5 复原）。**判决：Accepted**（阻断项均未命中；`ISS-219` notes 复现命令同步遗留已登记，归 `/complete`）。

