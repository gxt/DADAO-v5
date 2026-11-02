# INFRA-103t: 陈旧引用/文案收口 + 两个工具缺陷

**模块**：infra
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-167t`（册名已稳定）、`SPEC-170t`（schema `opc`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源

收口以下已登记的缺陷/陈旧项（全部为"文档/工具与现状不一致"，非新功能）：

| issue | 一句话 |
|---|---|
| `ISS-160` | `contract-isa` 投影层仍列已删伪指令；`impact-matrix` 悬空；`check_spec_codeblocks` 的 `PSEUDO_INSTRUCTIONS` 陈旧 |
| `ISS-208` | `ADR-0012 D9.5` 与 `check_scope.py` 注释写 `227→228`，与现场不符 |
| `ISS-308` | `0x77000000` 字面残留（该编码已归 `OPC-MISC` 并迁 `op 0x47`） |
| `ISS-311` | `components/musl/README.md`「原子」段过期（仍称无可用原子、`__clone` 返回 `-ENOSYS`） |
| `ISS-318` | FP 异常措辞缺口：`UF` 未写"tiny 且 inexact"、tininess 检测点未声明、标志 sticky 未明示 |
| `ISS-090` | `components/qemu/changelog.md` 缺任务级记录（自 2026-09-23 起） |
| `ISS-300` | `install-host` 之外的二进制替换属例外手法，应写进纪律/文档 |
| `ISS-329` | `contract-isa.md §6.6` 仍列已删伪指令 `not.o`/`neg.o` |

**另两个工具缺陷**（本册一并修，来自 `LLVM-126t`/`SPEC-158t` 披露）：
- `tools/llvm/gen_asm_list.py --embed-spec` **非幂等**（会改 12 册）；
- `tools/llvm/gen_isa_coverage.py` 生成的 `frem_proof()` 对 `.work/source` 用 `git grep`（未跟踪目录）⇒ **死断言**。

## 目标

1. 逐条修正上表 8 项（以**现场事实**为准；每条给出"改前是什么、现在该是什么"的依据）。
2. `gen_asm_list --embed-spec` 改为幂等（二次运行零 diff）。
3. `frem_proof()` 改为对**已跟踪的补丁源**取证（或删除该死断言并说明）。
4. 顺带核实一条**待查项**（不立 issue）：QEMU `fosclb` 溢出是否置 `OF`/`UF` —— 用 2 个用例现场判定，**只出结论，不改语义**；若确认缺标志，登记新 issue 不在此修。

## 验收

1. 8 条 issue 各有"改前/改后"现场证据（grep 或门控输出），并在完成区写清每条的依据。
2. `gen_asm_list --embed-spec` 二次运行 `git status` 零变化。
3. `frem_proof` 不再是死断言（注入：把 `FREM` 错接 `forem` ⇒ 该证明必须红）。
4. `fosclb` 判定结论（置/不置 OF/UF）与依据。
5. 受影响门控：`check-spec-refs`、`check_spec_codeblocks`、`check_scope`、`check-asm-list`、`check-asm-list-drift`、`check_qemu_trans --strict`（266/266）、`check-instrinfo`、`check-contracts-dir`；`make check`(L1) 一次 rc=0。
6. **可达 FAIL ≥2**：① `contract-isa` 塞回 `not.o` ⇒ 契约门控红；② 把 `frem_proof` 改回死断言 ⇒ 注入 `FREM`→`forem` 时不再红（说明死断言）。
7. 证据 `.work/evidence/<任务ID>/run.sh`。

## 接口规范

- **输入**：`.tao/contracts/**`、`components/*/README.md`、`components/qemu/changelog.md`、`tools/llvm/gen_asm_list.py`、`tools/llvm/gen_isa_coverage.py`、`docs/**`、`spec/**`（只读，除 `ISS-318` 的措辞）。
- **输出**：文档/工具修正 + 结论。
- **约束**：不改指令语义/编码；`ISS-318` 只改措辞不改规则；不 commit/push；临时目录 `/tmp/opencode/INFRA-103t/`。

## 完成区

**测试结果**：`make check`(L1) **rc=0**（`EXIT=0`；`check_issues` 23 open/73 closed）；受影响门控 **逐项 rc=0**（18 项含 `check-spec-readonly` 21/21、`check-milestones-fresh`）+ `check_qemu_trans --strict` **266/266**；证据 `.work/evidence/INFRA-103t/run.sh` default **56/56 PASS rc=0**、`--inject` **14/14 PASS rc=0**（`run.rc`=0）。
**修改文件**：`.tao/contracts/contract-isa.md`、`tools/spec/check_spec_codeblocks.py`、`tools/llvm/gen_asm_list.py`、`tools/llvm/gen_isa_coverage.py`、`components/musl/README.md`、`spec/SimRISC-{00,07}-*.md`、`.tao/contracts/contract-fp.md`、`manifests/spec-readonly.lock.toml`、`.tao/adr/adr-{0012,0004}-*.md`、`components/qemu/changelog.md`、`docs/Process-07-门控分层规范.md`、`AGENTS.md`、`.tao/knowledge/{issues.yaml,milestones.md}`、`.work/evidence/INFRA-103t/run.sh`（+`.work/evidence/LLVM-126t/run.sh` 例外手法修复，未跟踪）。
**验收结果**：
- 8 条：`160/329` 六小节改「— 已删除」+ 替代写法，`PSEUDO_INSTRUCTIONS` 14→4 且新增契约表校验；`impact-matrix` 活引用 0；`208` **不复现/原文正确**：`6e0741bf` total=227（m1 152+fp 60+excluded 15）、`0dcaf1f3` total=228（+m3 1）⇒ 原文 227→228 无误，未改 ADR-0012（`check_scope` 已无写死计数）；`308` 代码/补丁面 `0x77000000` **0** + ADR-0004 `## 修订` 标历史快照；`311` README 改真原子 + 边界；`318` spec 补 tiny且inexact / tininess=舍入后 / sticky / UF⇒NX；`090` changelog +15 条（M2 `025t–033t`、M9 `065t/068t–072t`），`milestones`−changelog=∅；`300` Process-07 §2 MUST + AGENTS 一行。
- `gen_asm_list --embed-spec`：连续两次运行 `spec/SimRISC-*.md` 聚合 md5 不变、`git status` 行数不变（改前会改 12 册、并致 `check-legality-drift` 12 红）。
- `frem_proof`：改为读**已跟踪**补丁树，注入 `(frem)→forem` ⇒ `check-isa-coverage` 红（`DADAOCodeGen.td.patch:1062 -> forem_orrr_rf`）、`cp`+md5 还原回绿；旧 `.work/source` 半边 `git grep` 在注入下仍 0（死断言），`grep -R` 为 1（已实测）。
- `fosclb`：SC10 `1.0×2^2000` = `+Inf` + **OF|NX**、SC11 `1.0×2^-2000` = `+0` + **UF|NX**，均 PASS（probe037 **91/91**；rf0 标志比较有 selftest 可达 FAIL）⇒ **正确置 OF/UF**，`LLVM-126t` 观察③不成立，**不登记新 issue**。
- 注入 A（`not.o` 塞回 §6.6 且去「已删除」）⇒ `check-spec-codeblocks` FAIL 命中 `'not.o' 不在保留集合`；还原 md5 一致后回绿。
**新发现/坑**：① `frem_proof()` 实际在 `.work/evidence/LLVM-126t/run.sh`（非 `gen_isa_coverage.py`）；旧断言只 `.work/source` 半边死。② `--embed-spec` 非幂等根因 = 无条件追加文末（把附录 A 挪到附录 B 之后），修法 = 插到 `LEGALITY_START` 前 + 尾部归一。③ `ISS-308` 代码面早由 `SPEC-164t` 归零；ADR 剩余 3 处为历史快照。④ `spec` 只读册改动须同笔更新 `spec-readonly.lock.toml`（已含授权注记）。
**遗留问题**：L2/L3 未跑（不在本册验收面）；`.work/` 未跟踪 ⇒ LLVM-126t 证据脚本修复不入库（durable 保护在 `gen_isa_coverage.py`）；ADR 的事实订正采用 `## 修订` 形式，需用户确认是否接受（决策正文未改）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `--embed-spec` 只把 A 插到 B 前仍可能因尾部空行漂移 | ✅已修 | 插入后统一去尾部空行 + 单个 `\n` | 二次运行 spec 聚合 md5 不变（run.sh S1） |
| F2 `check_spec_codeblocks` 新校验初版正则漏 `not.o rdhb, rdhc`（要求反引号紧邻） | ✅已修 | 行正则改 `^\|\s*`([a-z][a-z0-9_.]*)[\s\`{]` | 注入即红命中；还原回绿 |
| F3 证据脚本日志名不带任务号 ⇒ `check-run-artifacts` A3 红 | ✅已修 | 日志统一 `INFRA-103t-<purpose>.log` | `make check` L1 rc=0 |
| F4 `spec/SimRISC-{00,07}` 改动未更新只读锁 ⇒ L1 红 | ✅已修 | 锁文件 2 条 sha256 + 授权注记（用户 2026-10-21「可以」/ISS-318） | `check-spec-readonly` 21/21 rc=0 |
| F5 旧 `frem_proof` 死断言无法复现（结构死而非恒假） | ✅已修（证据侧） | 注入未跟踪 `.work/source` 证明 `git grep`=0、`grep -R`=1 | run.sh `injectB` 段 PASS |
| F6 完成区最初把 `frem_proof` 归到 `gen_isa_coverage.py` | ✅已修 | 完成区「新发现/坑 ①」如实披露实际位置，并在生成器落等价证明 | 文件路径 `grep -rn frem_proof` |

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（2 阻断 + 1 对账项）。快照对账：验收前后 `git status --porcelain -uall` 均 0 行；注入文件 md5 全部还原（contract-isa `268266af`、DADAOCodeGen `b54b65b5`、SimRISC-00/07 `3e6ee082`/`554c2cc1`）。

**阻断 1｜run.sh 基线漂移，提交后不可重跑**：我重跑 `run.sh`（default）= **50 PASS / 3 FAIL，rc=1**：`[FAIL] ISS-329 … expected=5->0 actual=0->0`、`ISS-160 PSEUDO… expected=14->4 actual=4->4`、`ISS-311…expected=1->0 actual=0->0`。根因：S2 用 `git show HEAD:` 作"改前"基线，提交 `9d8e73e9` 后 HEAD 前移 ⇒ 读到"改后"值。修法：基线锚改立册提交 `a7f50322`（或预记录改前值）；交付物本身正确（我实测 `a7f50322` 时点 5/14/1 → 现状 0/4/0）。

**阻断 2｜ISS-208 事实性错误：ADR-0012 修订段把正确原文改为错值**：git 实证 D9.5 原文「227→228」**正确**——`6e0741bf`（2026-10-04 D9 定稿日）opcodes.yaml = **227** 条（文件头自述"共 227 条：M1 152+fp 60+excluded 15"）、`0dcaf1f3`（SPEC-100t 落地 sub.o）= **228** 条，同句 total=228 亦吻合；issue 登记"实测均 227"系片面时点。修订段称「笔误、正确为 226→227」及完成区「订正 226→227（与当时现场一致）」**与现场不符**。修法：撤销该事实"订正"（删除或改为"issue 不成立"说明，附上述 git 计数证据），ADR 原文保留。

**对账项 3**：实际 diff 含 `.tao/contracts/contract-fp.md`（ISS-318 措辞同步，内容正确），完成区「修改文件」漏列，须补列。

**已核通过项**（我独立重跑/注入）：① ISS-160/329 六小节「已删除+替代写法」与 `Toolchain-01 §6` 一致，替代写法（`xnor.o rd,rs,rd0`/`sub.so {rd0,rd},rd0,rs`）正确；我独立注入 `neg.b` 新伪指令小节 ⇒ `check-spec-codeblocks` rc=2 红（`'neg.b' 不在保留集合`）、还原回绿。② ISS-308：我自己 grep tests/tools/contracts/spec/两组件 patches `77000000` = **0**；ADR-0004 仅文末加修订段、决策未动。③ ISS-311：README 与 patches 一致（`lr.t.an/sc.t.ar`、`lr.o.an/sc.o.ar`、`fence 975`=0x3CF、`clone.s` 真实现 116 行、QEMU-067t/LLVM-121t 在场）。④ ISS-318 逐句核对与 IEEE 754-2019 一致（UF=tiny∧inexact；tininess=舍入后为标准允许两检测点之一且已声明；sticky；UF⇒NX、反向不成立）；引用「§7.5」经查证 = 754-2019 **underflow** 小节（754-2019 重编号：overflow 7.4 / underflow 7.5），编号正确；两册 sha256 与锁逐字节一致。⑤ ISS-090：+15 条，抽 028t/030t/071t 任务号与内容真实（archive/M2 + tasks/qemu 在场、标题吻合）。⑥ ISS-300：Process-07 §2 MUST 与 AGENTS 一行指针语义一致。⑦ `gen_asm_list --embed-spec` 我独立跑两次：rc=0×2、spec 聚合 md5 前后一致、`git status` 0 行。⑧ `frem_proof` 我独立注入（intrinsic 行改 `(frem…)->forem`，非脚本方式）⇒ `check-isa-coverage` rc=2 红（`DADAOCodeGen.td.patch:1059`）、还原回绿。⑨ fosclb：SC10 `+Inf+OF|NX`、SC11 `+0+UF|NX`，probe037 91/91 rc=0，为 ROM 内 cmp+br 真比较（expect_rf 含 rd4+rf0）⇒「正确置 OF/UF、不登记新 issue」成立。⑩ 门控：11 项 make 目标 + `check_qemu_trans --strict` **266/266**（我独立跑 rc=0）+ `make check`(L1) rc=0（我独立跑）。

### 第 2 轮 reviewer 验收

**判决：Accepted**（返工提交 `ea9290ec`；工作区快照 `git status --porcelain -uall` = 0 行，注入文件 md5 与 HEAD 逐字节一致）。逐项复验：
1. **证据可复现**：`run.sh` 锚定 `BASE=a7f50322` + `git cat-file -e` fail-closed，无 `git show HEAD:` 残留（grep 确认 3 处全改 `"$BASE"`）；我重跑 **default 56/56 rc=0**、**`--inject` 14/14 rc=0**，`run.rc`=0 一致。
2. **ADR-0012**：错误修订段已删、blob 回 `772e4594`（=立册时点原状），D9.5 原文「227→228」在场；我复算 `6e0741bf`=**227**、`0dcaf1f3`=**228** ⇒ 原文正确，撤销无误。
3. **ISS-208**：`status: closed`、`resolved_by: INFRA-103t`，notes 以【关闭…**不复现/原文正确**】收口并附两次提交计数证据。
4. **完成区**：「修改文件」已补列 `.tao/contracts/contract-fp.md`，与实际 diff 对账一致。
5. **L1**：`make check` 我本人重跑 **rc=0**（`repository checks (L1): PASS`）。

### 第 2 轮 engineer 返工（对 reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 证据脚本以 `git show HEAD:` 作基线，提交后漂移（50P/3F rc=1） | ✅已修 | 基线改为立册提交 `BASE=a7f50322`（缺失即 fail-closed），不随 HEAD 前移 | default **56/56 rc=0**、`--inject` **14/14 rc=0**（`run.rc`=0） |
| R2 ADR-0012「226→227」订正为事实错误 | ✅已修 | 删除该 `## 修订` 段，恢复原文；ISS-208 改为「不复现/原文正确」 | `6e0741bf` total=**227**、`0dcaf1f3` total=**228**（现场 `grep -c '^- id:'`）；脚本断言「无 226→227」 |
| R3 完成区修改文件漏列 `contract-fp.md` | ✅已修 | 补入「修改文件」 | 与 `git status` 对账一致 |
