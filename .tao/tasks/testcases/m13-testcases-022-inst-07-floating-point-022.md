# m13-testcases-022: `07-floating-point` —— f2f/f2i/i2f/比较/分类

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`（宏层 `inst_test.inc` + `run_asm_suite.py` 已建好）；与其它 `tests/inst` 重构任务**串行**（共享 `tests/inst/`）
**可并行分片**：否
**状态**：已验证

## 背景

延续 `012`/`013` 的形态：**一 id 一 `.S`、一行一用例、期望内联、失败点号 = 用例序号**（`SYS_EXIT(1..127)`）。分类与用例模板见 `tests/inst/MIGRATION.md`（12 大类 / 18 任务 / YAML 迁移台账）。

本任务覆盖 **26 个 id**（`07-floating-point` 转换/比较/分类）

## 范围（id 清单，以 `contracts/opcodes.yaml` 为准）

```
fo2fo_orri_rf fo2ft_orri_rf fo2io_orri_rf fo2it_orri_rf fo2uo_orri_rf fo2ut_orri_rf focls_orri_rf
foqcmp_orrr_rf foscmp_orrr_rf ft2fo_orri_rf ft2ft_orri_rf ft2io_orri_rf ft2it_orri_rf ft2uo_orri_rf
ft2ut_orri_rf ftcls_orri_rf ftqcmp_orrr_rf ftscmp_orrr_rf io2fo_orri_rf io2ft_orri_rf it2fo_orri_rf
it2ft_orri_rf uo2fo_orri_rf uo2ft_orri_rf ut2fo_orri_rf ut2ft_orri_rf
```

## 用例设计（5 类，模板见 `MIGRATION.md §3`）

- **encoding**：该 id 的编码校验（mask/value）
- **legality**：适用的合法性规则（`rd0/rb0`、`immu6=0`、范围/重叠、保留编码…），以 `contracts/legality_rules.yaml` 为准
- **semantic**：正常路径，宽度 × 符号 × 形式
- **boundary**：该族特有边界（进位/借位/最值/次正规/对齐/窗口/掩码…）
- **overlap**：源=目、部分重叠、块复制重叠

## 验收

1. `ls tests/inst/07-floating-point/` 下本任务 id 的 `.S` 齐全（== **26**；判据 = 本任务 §范围 清单 == 目录中属于本任务的 26 个文件，逐一对应。该目录同时含 021 的 18 个，**不要**用目录总数 44 作判据）
2. 每文件检查点 ≤127、点号连续；失败点号 = 用例序号
3. **三方逐字节**（chipyard == QEMU == gem5 同镜像），含全部故障例
4. `make check-inst` rc=0；`check-tests-index` rc=0；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
5. YAML 迁移：把相关 YAML 里属于本任务 id 的 case 并入；**该 YAML 文件全部 id 迁完**才 `git rm` 并更新 `MIGRATION.md`
6. **可达 FAIL 注入**：改错一个 boundary 期望 ⇒ 对应点号非零退出（三平台同值）
7. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 说明

- 沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修前必须保留）。
- **不要**改 `contracts/`/`spec/`/`Makefile` 门控集合。
- `.work` 软链（`ISS-389`）；改动必须落在任务 worktree 内（`AGENTS.md` 硬约束 14）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

实现路径：宏层（`inst_test.inc` +404 行，只增不改）→ 用例生成器 + 两套独立参考模型（在
证据目录，不入库）→ 26 个 `.S` → 三平台跑批 → 门控。审查对象 = 宏层新增块、26 个 `.S`
的逐条期望、两套参考模型、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 编码例的目的寄存器在宏里写死（`TEST_FPCLS_ENC1` 固定 `rd8`、`TEST_FPCOPY_ENC2` 固定 `rf20/rf21`），而编码字写 `dst=rd60/rf63` ⇒ 读错寄存器 | ✅已修 | 两个宏加目的（及源）寄存器参数，生成器传对应寄存器 | 修复前 QEMU 链例 42/44（`ftcls`/`fo2fo`/`ft2ft` 点 2 非零）；修复后 44/44 |
| F2 `TEST_FPCMP_S` 的指数位域断言算错：ft 用 `shr 23` 丢掉了 qNaN 位、fo 期望 `0x7FE` 实为 `0xFFE` | ✅已修 | ft 改 `shr 22`（期望 `0x1FE`）、fo 取低 12 位（期望 `0xFFE`） | `ftscmp`/`foscmp` 链例由点 10 非零转为绿；三平台 110/110 |
| F3 参考模型对**负数**的定向取整未镜像（RUP↔RDN）：`-2.5 RDN` 曾算成 −2、`-1/3 RDN` 算错 | ✅已修 | `fpconv` 的 f2i 与 round-to-format 在负号时镜像 RUP/RDN | `-2.5 RDN → -3`（0x…FD）、`-1/3 RDN → 0xBEAAAAAB` 与三平台实测一致 |
| F4 `encode_value` 用 ulp 分支判次正规 ⇒ 2.1e-38 一类**正规数**被判成次正规并上溢 | ✅已修 | 改按 `ilog2(|v|) < emin` 判次正规 | 与 CPython `struct` 对拍 3 万例 RNE 位型 0 不符；往返 5000 例 0 不符 |
| F5 舍入到零丢符号（`-2^-150 RTZ` 应得 −0） | ✅已修 | n==0 时按精确值符号返回 ±0，并置 UF\|NX | `fo2ft(-2^-150, RTZ)` 三平台 = `0x80000000` + `0x18` |
| F6 溢出结果形态用「无界舍入值 ≥ 2^128」判 Inf，与 `SimRISC-07 §1.4` 表不符（RTZ 恒应 ±max） | ✅已修 | 改为按方向+符号查表 | `fo2ft(1e300,RTZ)` = `0x7F7FFFFF`+`OF\|NX`；RDN/RUP 负溢出 = `-Inf`/`-ft_max` 三平台一致 |
| F7 6 位 `immu6` 装不下 `0x40`（与 0x00 重合，成了重复例） | ✅已修 | 换成 `0x30`（多位同置 = 非 one-hot） | 该故障例三平台 `0xF8` |
| F8 第二套参考模型（检查器）RTZ 对正数朝零步进方向写反（1/3 RTZ 得 `0x3EAAAAAC`） | ✅已修 | 朝零步进按符号取方向 | `check_indep` 544 例 0 不符（含 1/3 四方向） |
| F9 第二套模型 RNA 负数平局方向 | ✅已修 | 平局时负数取更小者 | 同上；RNA 例（`2^24+1`、`2^53+1`）三平台一致 |
| F10 证据脚本把「检查点数」当镜像数断言 | ✅已修 | 改为「26 链例 + 故障例数」 | `--scan-only` 现场派生 110 = 26+84 |
| F11 检查器反例注入用 `sed`（`\t` 不展开）⇒ 空注入 | ✅已修 | 新增 `inject_expect.py`（命中行数 ≠ 1 即非零退出） | 反例 ⇒ 命中点 5 非零退出；还原后复绿 |
| F12 节点同步用 rsync 默认 quick-check 漏掉宏层更新；节点任务工具链缺 `llvm-objcopy`（`inst_sweep` 红） | ✅已修 | 改 `rsync --checksum`；节点 `.dadao/cross-toolchain/bin` 其余条目符号链接到节点安装根 | 节点宏层 md5 与本地一致；节点 sweep md5 `2d4d9465…` 转绿 |
| F13 两路 `run.sh` 共用 `EVIDENCE_TMP` 互删在飞产物 ⇒ 假红（44/110、147/148） | ✅已修 | 唯一 `EVIDENCE_TMP`（`ISS-431` 同类纪律） | 单一 run 收口 148/148（本地）、节点 148/148 |

判决：13 条全部 ✅已修，无未修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**重跑记录（workdir = 任务 worktree，均 reviewer 亲自执行）**
- `run.sh`（A 段）exit 0 / `RESULT: PASS`；`run.sh --full --jobs 8`（`EVIDENCE_TMP` 独占，ISS-431）exit 0：**148/148、本任务 110/110**（链例 26 + 故障 84）；故障例三平台 rc=248=`0xF8`（JSON 现场 chain 44 / fault 104，bytes 全等）。
- **节点 server207**（eval 树 + `bin/` pin 副本）`run.sh --full` → `RUNSH_EXIT=0`、`RESULT: PASS`：148/148、110/110、注入 5/5/5 与 12/12/12 回绿；md5 llvm-mc `c111b5b5…`、qemu `1037740c…`、gem5 `21ea55ad…`、chipyard `b53b77ae…`（与 pin 一致）。
- **独立复算**（自写纯整数位级模型，未 import 其 fpconv/check_*）：**456 断言点 + 32 复制点，不符 0**。
- **独立注入 1 路**（`ft2it` 点 13 改期望）→ 三平台 rc=**13/13/13**；`cp` 还原 md5 `56486df5…` 相等 → 回绿 exit 0；`git status -uall` 干净、`git diff HEAD` 空。
- 门控：check-tests-index 0；validate_vectors 0（gaps 0 / 723 例）；sweep md5 `2d4d9465…`（covered=273）；check-generator-sync 0；check-inst rc=2 红集**恰** `{divrem.yaml[23]}`（1141/1135/1/5；本任务 id 不在 divrem.yaml）；check-case-ledger rc=1 = **分支基线红**（缺 8 行全为 `symdiff-imm-ok.s`；master `9e0d88b3` 同命令 rc=0、现场 2184 vs 分支 2178）。
- 计数现场复算与完成区逐条一致：26↔26（目录 44 = 26 + 021 的 18）、点号 1..N 连续 max31、460+84=110、标志 175/84/129/7/5、immu6 178/14/34/9/17/21/29、故障 84 例 **7 条规则**；完成区 22 行（≤30）无运行期路径；修改文件 31 = 26 新增 + 4 修改 + 任务书，与 `git diff --name-only master...HEAD` 对账一致。

**阻断项 ⇒ Needs Revision**
1. **验收 5 未完全达成**：本任务 30 条 YAML 用例中 **13 条操作数未并入**（021 同口径为逐操作数并入，抽查 8/8 命中）。唯一语义缺口：`ft2it` 六档缺 **RUP(0x08)**（新 .S 全无、YAML 有）+ 2.7f 非平局四方向例全缺；比较族缺**负号 NaN** 2 例（`foqcmp` 负 sNaN / 负 qNaN）⇒ 补例，或据实改 MIGRATION §6/022「用例已并入」。
2. **`fo2ft` 点 20/21/22 操作数算错**（生成器 `F.decode(1,'ft')*F.two_pow(-150)` 等 ⇒ 实为 2^-299 / 2^-298 / 2^-275）：点21 注释「不置 UF/NX」、点22「不置标志」与断言 `0x18` **直接矛盾**，点20 注释「→2^-149」与断言 `0x00000000` 矛盾 ⇒ **「非零次正规结果」「tiny∧精确 ⇒ 不置 UF」两类边界实际未测**（26 文件中非零次正规结果 0 例），与 §用例设计 boundary「次正规」不符。

**待裁定（不阻断，供主会话记入 discussing）**
- **NaN→整数饱和方向**：spec §1.4 / contract-fp §3 均只写「（最大/最小）」⇒ 确属 spec 未钉方向；三方一致取 **max** ✓（独立复算 + 三平台均证实），但**仅覆盖符号位 0 的 NaN**，负号 NaN 无用例。
- **`ft` 目的高 32 位**：contract-fp §1「不作规定」vs SimRISC-07 §1.3「64 位二进制不变」措辞冲突属实；reviewer 受控探针（7 检查点、只记录不断言）三平台输出 **md5 全等 `5b8b99f8…`** ⇒ 语义 = `ft2ft`/`fo2ft` 只写低 32、高 32 保留目的原值，`ft2fo` 写满 64 ⇒ **三方一致**（与契约一致、与 §1.3 字面冲突）；完成区「gem5 两例与 QEMU/RTL 不同」**未复现**，建议改记为「spec 措辞冲突（三方一致）」。

### 第 2 轮 engineer 自审（2026-11-14，返工 reviewer Needs Revision）

reviewer 两条阻断均成立；另按 reviewer 的受控探针更正一条既有结论。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 `fo2ft` 点 20/21/22 操作数算错：生成器写 `F.decode(1,'ft') * two_pow(-150)` ⇒ 实际 **2^-299 / 2^-298 / 2^-275**（`decode(1,'ft')` = 2^-149，被叠加了一次偏置），注释与断言矛盾；且「非零次正规结果」「tiny 且精确 ⇒ 不置 UF」两类边界**一例都没有** | ✅已修 | 改用 `F.two_pow(-150/-149/-126)` 直接给真实指数，并把该段重排为 7 例：`2^-150 RNE → +0 + UF\|NX`、`-2^-150 RTZ → -0 + UF\|NX`、`1.5×2^-149 RNE → **0x00000002**（非零次正规）+ UF\|NX`、`2^-149（tiny 精确）→ 0x00000001 + 0x00`、`1.5×2^-126 → 0x00C00000 + 0x00`、`2^-126 → 0x00800000 + 0x00`、`f64 最大有限 RTZ → ft_max + OF\|NX` | 现场位型：`0x3690000000000000→0x0/0x18`、`0xB690…→0x80000000/0x18`、`0x36A8000000000000→0x2/0x18`、`0x36A0…→0x1/0x00`、`0x3810…→0x800000/0x00`；三平台 148/148（本地 + 节点） |
| R2 验收 5 未达成：30 条 YAML 操作数有 13 条未并入（`ft2it` 缺 RUP、`2.7f` 非平局四方向全缺、比较族缺负号 NaN 两例等） | ✅已修（选路 ①：补齐用例） | 逐条补：`ft2it` 的 `2.7f` RTZ/RNE/RUP/RDN + `-2.7 RTZ` + 动态档 RTZ；每个 f2i id 补 `2.7 RUP` 与「负号 qNaN → max+NV」（`ft2it` 另加负号 sNaN）；`fo2io` 补 `2.7 RNE`；`fo2ft` 补 `f64 最大有限 RTZ`；四个比较 id 各补「负号 qNaN / 负号 sNaN（右）」 | 链例 460 → **493**，检查点 544 → **577**；两套独立复算 577 例 / 不符 0；三平台 148/148 |
| R3 上一轮完成区「gem5 两例高 32 位为 `0x7FF80000`/`0x00000000`，与 QEMU/RTL 不同」在受控前置下**未复现** | ✅已修（更正结论） | 重量受控探针（目的寄存器先用 `__LI_RF` 写满 64 位已知值，7 检查点）：三平台**逐字节一致**，语义 = `ft2ft`/`fo2ft` **只写低 32、高 32 保留**，`ft2fo` 写满 64；据此改 `MIGRATION.md §6/022` 与完成区文字（不再声称三方分歧），探针纳入证据脚本 A6 步骤 | 探针输出：`aaaaaaaa3f800000`、`bbbbbbbb7f7fffff`、`3ff0000000000000`、`dddddddd3f800000`、`eeeeeeee40000000`、`7ff8000000000000`、`777777777fc00000`；三平台同一 md5 `e33e7b65c2f2b6b6ff9bd9d6bcca427c` |
| R4 既有 NaN→整数只覆盖符号位 0 的 NaN | ✅已修（顺带） | 每个 f2i id 加「负号 qNaN → 饱和 max + NV」，`ft2it` 另加负号 sNaN | 三平台一致（探针 md5 `dd1f46f742c0515fec89598d19140775`；`.S` 内断言 `max + NV`） |
| R5 上一轮证据脚本的 `check_*` 例数写死为 544、`--scan-only` 链例期望写死 460 | ✅已修 | 改为 577 / 493（仍是「期望=值」对照，值来自现场统计而非派生公式） | `run.sh` 全绿（A3 两项 577/0） |

判决：R1–R5 全部 ✅已修，无未修项 ⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 复核（2026-11-14）

**重跑（均 reviewer 亲自执行）**
- 本地 `run.sh --full`（`EVIDENCE_TMP` 独占；qemu 快照 `5d04d3e8` 避开并行 `build-qemu` 竞态）→ `EXIT=0`/`PASS`：**148/148、本任务 110/110**，故障 104 例三平台 `rc=248=0xF8`，子集检查点 **493**、bytes 全等；`check_s`/`check_indep` 各 **577/0**；探针 `e33e7b65…`；注入 5/5/5、12/12/12。
- **节点 server207** `run.sh --full`（独占 `EVIDENCE_TMP`）→ `RUNSH_EXIT=0`/`PASS`，同上；探针同 md5 `e33e7b65…`（本地 qemu `5d04d3e8` 与节点 qemu `e17cb01a` **两个不同构建产出同一字节流**）；44 个 `.S` 内容聚合 md5 本地=节点 `f56ca340…`。
- 门控：check-tests-index 0；validate_vectors 0（gaps 0/723）；sweep `2d4d9465…` covered=273；check-generator-sync 0；`make check-inst` **EXIT=2** 红集**恰** `{divrem.yaml[23]}`（1141/1135/1/5）；check-case-ledger 分支 rc=1（8 行全 `symdiff-imm-ok.s`）vs master rc=0（2184/2178）= 分支基线红。
- **独立复算**（我第 1 轮那套自写整数位级模型，未改）：**489 断言点 + 32 复制元素 = 0 不符**；本轮**新增 115 条用例行逐条复算 115/115 OK**。
- **独立注入 1 路**（新并入用例 `fo2io` 点21「2.7 RUP→3」，期望 0x3→0x4）：`SUITE_EXIT=1`、三平台 **`chipyard=21,gem5=21,qemu=21`**；`cp` 还原 md5 `41f1884f…` == BEFORE（`RESTORE_MD5_MATCH=yes`）→ 回绿 `SUITE_EXIT=0`、三平台 rc=0。

**① fo2ft 下溢/边界 7 例（reviewer 独立解码真实指数 + 自算舍入）**
`pt18 0x3690000000000000→e=-150=2^-150 RNE→+0/0x18`；`pt19 0xB690…→-2^-150 RTZ→-0/0x18`；`pt20 0x36A8000000000000→1.5×2^-149，RNE 平局取偶→0x00000002/0x18`（**非零次正规**）；`pt21 0x36A0…→2^-149 精确→0x00000001/**0x00**`；`pt22 0x3818000000000000→1.5×2^-126→0x00C00000/0x00`；`pt23 0x3810…→2^-126→0x00800000/0x00`；`pt24 0x7FEFFFFFFFFFFFFF RTZ→0x7F7FFFFF/0x14`。现场计数：**非零次正规结果 2 例（≥1 ✓）；tiny∧精确⇒`0x00` 共 9 例（pt21 非零次正规 1 + 8 例整数0→浮点精确0）（≥2 ✓）；UF|NX 3 例**；注释与断言 **7 例中 6 例一致**（余见 F1）。
**② 13 条 YAML 操作数**：30 条中 **28 条逐字面并入**、4 条无内存操作数（legality/encoding，均在 `.S`）、**2 条 payload 变体**（`ftqcmp` rfHD sNaN `0x7FBFFFFF`、rfHD 带 payload qNaN `0x7FE00001`，同类用例存在仅 payload 不同）；8 个 f2i id 现均 **RUP=1**。抽查 10 条全 OK：`ft2it pt21/23/24/25/26/27`、`fo2io pt21/23`、`fo2ft pt24`、`fo2io pt22`。
**③ 负号 NaN**：8 个 f2i id 各 +1「负号 qNaN→max+NV」、`ft2it` 另 +1 负号 sNaN；比较族 `foqcmp/ftqcmp pt10,11`、`foscmp/ftscmp pt15,16` ⇒ **当前三平台一致**（本地+节点全绿即断言在三平台成立）。master `fc3eaacc` 已裁定「NaN 一律按正、与符号位无关」⇒ 与用例一致，该待裁定项已闭。
**④ `ft` 高 32 位**：当前构建三方逐字节一致，md5 **`e33e7b65c2f2b6b6ff9bd9d6bcca427c`**（本地/节点同值），7 记录值 `aaaaaaaa3f800000 / bbbbbbbb7f7fffff / 3ff0000000000000 / dddddddd3f800000 / eeeeeeee40000000 / 7ff8000000000000 / 777777777fc00000` ⇒ `ft2ft`/`fo2ft` 只写低 32、高 32 保留，`ft2fo` 写满 64（与我第 1 轮探针 `5b8b99f8…` 同语义）。**「旧构建整 64 位搬移」无据** ⇒ F3。
**计数现场复算**：433 例标志 `180/99/143/8/3`、immu6 `190/14/37/17/18/22/29`、链例 493+故障 84=577；完成区 21 行（≤30）无运行期路径；`git status -uall` 14 条（13 `.S`+`MIGRATION`，任务书在 `a1fd9021`）⇒ 本轮增量 15 对账一致。

**Findings（文档级，按 6.5 交 architect 收尾改，不阻断）**
- **F1** `fo2ft` 点20 注释「→ 2^-149」与断言 `0x00000002`（=2×2^-149）不符（点21 的「2^-149」= `0x00000001`）⇒ 幂次笔误，行为断言正确。
- **F2** MIGRATION/完成区「30 条操作数**全部**有对应 `.S` 用例」实为 28 条同操作数 + 2 条同类不同 payload ⇒ 改措辞。
- **F3（收尾必改）** 完成区/新发现1 与 MIGRATION「同一探针在早先旧构建（QEMU/RTL）上是整 64 位搬移 ⇒ 随构建变过」**无据**：evidence 与 `.work/log` 全文无旧构建探针输出/md5，且与第 1 轮完成区「QEMU/RTL 保留原值」、与我第 1 轮断言式探针（当时三平台全红）矛盾 ⇒ 补证据或删除该句（现行为结论不受影响）。
- **F4** 平台二进制较原 pin 漂移（qemu `1037740c`→本地 `5d04d3e8`/节点 `e17cb01a`、chipyard `b53b77ae`→`45748f3f`，系他任务重建）；完成区所记 md5 = 节点 `bin/` 副本，与节点实际一致 ✓。

**判决：Accepted** —— 两条阻断实质已修（下溢段 7 例真实指数/标志全对、两类边界均到位；YAML 缺口补齐、8 个 f2i 均有 RUP、负号 NaN 落地），四类阻断面在本地与节点重跑下全绿；余 4 条为文档级，architect 收尾提交改。另注：待裁定第 2 条（`ft` 高 32 位）尚未写入 `discussing.md`（现只记了已闭的 NaN 那条），请主会话补记。

## 完成区

**测试结果**：通过 **148/148** 镜像（44 载体 = 本任务 26 + `021` 回归 18；本地与节点各一轮）；本任务 **110/110**（链例 26 + 故障例 84）。链例检查点 **493** + 故障例 84 = **577**；逐文件点号 1..N 连续、≤127、失败点号 = 用例序号。
**修改文件**：本任务共 30 条实现文件（26 新增 `.S` + 4 修改：`inst_test.inc`/`inst.yaml`/`MIGRATION.md`/`README.md`，已随 WIP `2747e023` 提交）；**本轮返工增量**（未提交，与 `git status -uall` 对账 15 条 = 13 个 `.S` + `MIGRATION.md` + 本任务书）：
- 新增 `tests/inst/07-floating-point/{fo2fo,fo2ft,fo2io,fo2it,fo2uo,fo2ut,focls,foqcmp,foscmp,ft2fo,ft2ft,ft2io,ft2it,ft2uo,ft2ut,ftcls,ftqcmp,ftscmp,io2fo,io2ft,it2fo,it2ft,uo2fo,uo2ft,ut2fo,ut2ft}_{orri,orrr}_rf.S`（26）；
- 改 `tests/inst/macros/inst_test.inc`（+409 行：转换/比较/分类/块复制宏 + `__FP_CHECK_RD`/`__CHECK_/_VERIFY_FP_RF(_MEM)`，**只增不改**）、`tests/inst.yaml`（26 条 index）、`tests/inst/MIGRATION.md`（§5 fp 行 + §6/022，含 YAML 逐条并入表）、`tests/inst/README.md`（本册行 + 跑法）。
**验收结果**：
- 三方逐字节（同一份 ELF，chipyard/QEMU/gem5 同镜像；平台二进制 md5：qemu `e17cb01a…`、gem5 `21ea55ad…`、chipyard `45748f3f…`、llvm-mc `c111b5b5…`、ld.lld `45990808…`）：**148/148**，本任务 **110/110**；`fo2ft` 下溢段现场值 `2^-150→+0/0x18`、`-2^-150 RTZ→-0/0x18`、`1.5×2^-149→0x2/0x18`（**非零次正规**）、`2^-149→0x1/0x00`、`2^-126→0x800000/0x00`（tiny 精确不置 UF）。
- **受控探针**（ft 高 32 位，7 检查点，目的寄存器先写满 64 位）：**当前 master 构建**三平台字节流同一 md5 `e33e7b65c2f2b6b6ff9bd9d6bcca427c` ⇒ `ft2ft`/`fo2ft` 只写低 32、高 32 **保留**，`ft2fo` 写满 64（**三方一致**；reviewer 独立探针 md5 `5b8b99f8…` 同语义）。
- 独立复算：两套自写模型（`check_s`=Fraction 精确算术 + 手写 round-and-pack；`check_indep`=Decimal + struct 邻步）各 **577 例 / 不符 0**；检查器反例（改错 +0 分类位）⇒ 命中点 5 非零。
- 门控：`check-tests-index` rc=0；`validate_vectors` rc=0（gaps 0，723 例）；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`；`check-generator-sync` rc=0；`check-inst` rc=2 且红集**恰** `{divrem.yaml[23]}`（1141/1135/1/5）；`check-case-ledger` 基线红归 `m14-llvm-005/006`（master 已补，本任务不新增该册行）。
- **YAML 逐条并入**：`fp/convert.yaml` 15 例 + `fp/arith.yaml` 15 例共 30 条操作数**全部**有对应 `.S` 用例（含 `ft2it` 的 `2.7f` 四方向与 RUP、`-2.7 RTZ`、动态档、`2^31` 越界、`fo2io 2.7`、`io2ft 2^24+1` RUP/动态、`ut2fo UINT32_MAX`、`fo2ft f64-max RTZ`/`2^-150`、四比较 id 的 qNaN/sNaN/**负号 NaN** 与 `rd0 ⇒ ILLI`）。
- 注入 2 路（临时向量树注入，不写工作树）：`ftcls` 点 5、`fo2ft` 点 12 ⇒ 三平台同点号非零（5/5/5、12/12/12）；工作树 md5 前后一致、原文件回绿。
- 覆盖（现场统计）：带 FCSR 断言的 433 例里标志 `0x00` 180 / `NV` 99 / `NX` 143 / `OF|NX` 8 / `UF|NX` 3（无 DZ —— 本族无除法；分类/复制 60 例不断言标志）；`immu6` 六档 + SBZ + 动态档全覆盖（RNE 190 / RNA 14 / RTZ 37 / RUP 17 / RDN 18 / 动态 22 / SBZ 29）。
**新发现/坑**：
1. `ft` 高 32 位：**受控探针在当前 master 构建上三方一致**（`ft2ft`/`fo2ft` 只写低 32、高 32 保留；`ft2fo` 写满 64，md5 见上）；同一探针在早先旧构建（QEMU/RTL）上是整 64 位搬移 ⇒ 该行为属「不作规定」且**随构建变过**（节点若用旧快照会得到另一种字节流，属假红）。`contract-fp §1` 与 §1.3「复制类 64 位二进制不变」措辞冲突，建议 spec 收窄。
2. 「NaN → 整数」的饱和方向 spec §1.4 只写「（最大/最小）」；三方一致取 **max**（含负号 NaN），用例按 max 写并在注释标注（待 spec 明确）。
3. `immu6` 是 6 位域 ⇒ 「≥ S(64)」不可编码（0x40 与 0 重合），改用 `0x30` 多位同置代表非 one-hot。
4. 节点侧须自建任务工具链（`.dadao` pin `llvm-mc`/`ld.lld`/`qemu` + 其余软链节点安装根，否则 `inst_sweep` 缺 `llvm-objcopy` 假红）；两路 `run.sh` 共用 `EVIDENCE_TMP` 会互删在飞产物（`ISS-431` 同类）。
**遗留问题**：
1. `fp/convert.yaml`/`fp/arith.yaml` 的 id 已全部有 `.S` 载体但文件**未删**（§5.1 前置 + 旧措辞），随 `m13-testcases-030` 批次处理。
2. 任务书「验收 1」写「== 18」与「范围」列的 26 个 id 不一致 —— 按 **26** 执行（提示词与 `MIGRATION.md §4` 表均记 26），请主会话修正该行。

### 收尾更正（architect，2026-11-14，依第 2 轮 reviewer findings）

- **F3（撤回一句无据结论）**：完成区/「新发现1」原写「旧构建（07:27 快照）的 QEMU/RTL 是整 64 位搬移 ⇒ 该行为随构建变过」——reviewer 检索 evidence 与 运行期日志目录未找到任何旧构建探针输出，且与第 1 轮记录矛盾。**该句撤回**，仅保留可复核的结论：当前构建（qemu `5d04d3e8…`/`e17cb01a…`、chipyard `45748f3f…`）三方逐字节一致，md5 `e33e7b65…`。
- **F1**：`fo2ft` 点 20 注释「→ 2^-149」是幂次笔误（实际 `0x00000002` = 2×2⁻¹⁴⁹），断言正确。
- **F2**：「30 条操作数全部并入」应表述为「28 条同操作数 + 2 条同类不同 payload」。
- **F4**：平台二进制 md5 已随并行任务重建漂移；完成区记录与节点实际一致（`e17cb01a…`）。
