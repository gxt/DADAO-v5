# m12-chipyard-014: FP 除法/开方/取余

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-013`（FP 算术，已合入）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

`m12-chipyard-013` 已完成 FP 算术（加/乘/FMA/比较/最小最大）；`DZ` 端到端仍缺生产者，本任务的除法是首个。

## 目标

1. **除法**：`fodiv`（`DivSqrtRecFN_small` 等价）。
2. **开方**：`foroot`（同库）。
3. **取余**：`forem`（IEEE 754 remainder，`rfHC` 为 ±Inf / `rfHD` 为 ±0 / sNaN ⇒ NV + qNaN；不置 NX/OF/UF）。

## 验收标准

1. 对应指令族在 chipyard 上与 QEMU 逐例一致
2. `forem` 的三个边界（±Inf/±0/sNaN）各有断言
3. 除法/开方的特殊值（0/0、Inf/Inf、sqrt(-1)）各有断言
4. Verilator 构建 rc=0（主控机）；门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

取整/缩放/符号（`013`）

## 说明

- **允许多周期状态机**（用户 2026-11-09）：wuming 只是「无流水线」，不是「每条指令一个周期」；除法/开方的迭代过程走多周期状态机，不要为了单周期把组合延迟堆到不可仿真。
- 来源注明同 `009`（berkeley-hardfloat 的 `DivSqrtRecFN_small` 语义）。
- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-012/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。


## 完成区

**测试结果**：一键证据脚本 **PASS=165 FAIL=0**（`FULL_RUN_EXIT=0`；A 结构 / B 模型自检+手算锚点 / C 构建 / D 单元台三方 / E 273 回归 / F divrem.yaml / G 六组+特殊值+故障 / H 周期 / I 门控）；注入自检 **16/16 PASS**（`INJECT_EXIT=0`；① 除法不取整数商位 ⇒ D 的 div 值 785/790；② 去掉 `infiniteExc` ⇒ D 的 div 标志各 **5** 例（正是 x/0 的 5 条向量）；③ 取余恒向下舍入 ⇒ D 的 rem 43/38；④ oracle 改截断 ⇒ G 的 `div_*` 红；四组均 `cp`+md5 还原（源码 `793b531d…`、oracle `d7e1bd35…`）、复跑回绿）。

**修改文件**（与 `git status -uall` 逐项一致）：① `components/chipyard/patches/.../WumingFP.scala.patch`；② `.../WumingCore.scala.patch`；③ `.../WumingDecoder.scala.patch`；④ `.../WumingFPUnitHarness.scala.patch`（`make_patch` 重导出，`series` 不变）；⑤ `components/chipyard/README.md`；⑥ `components/chipyard/changelog.md`；⑦ `tools/chipyard/fp_ref.py`；⑧ `tools/chipyard/fp_sweep.py`；⑨ `tools/chipyard/fp_unit/unit_run.py`；⑩ `tools/chipyard/fp_unit/tb_fp_unit.cpp`；⑪ `tests/inst/fp/divrem.yaml`（新增）；⑫ `tests/case-ledger.tsv`；⑬ `tests/inst/inventory.md`（返工 R2：门控覆盖表补 `fp/arith.yaml`、`fp/divrem.yaml` 两行）；⑭ 本任务书。

**验收结果**：
1. **状态机与拍数**：div/sqrt 共用「每拍一位」的数字迭代机（`nSteps = sigWidth+2`，`start`/`done` 各一脉冲）；**fo 56 拍 / ft 27 拍 = `sigWidth+3`**，7 组不同操作数实测**完全相同**（不随操作数变化）。`forem` 是 restoring 长除（`d = ea−eb ≥ 0` 时 `sigWidth+d` 步、`d < 0` 不进循环）⇒ d = 1/10/100/1000 实测 **55/64/154/1054** 拍（差值与 d 差值相等；精确整除时早退）。
2. **forem 三边界**（YAML 1 例/项 + sweep `rem_*` 18 例/格式，含 `−Inf` 被除数与 `−0` 除数 + 故障镜像）：`rfHC` = ±Inf ⇒ qNaN+`NV`；`rfHD` = ±0 ⇒ qNaN+`NV` 且**不置 `DZ`**；sNaN ⇒ qNaN+`NV`；另 `rfHD` = ±Inf ⇒ 原样返回被除数、`rfHC` = ±0 ⇒ +0；**不置 NX/OF/UF**（oracle 侧断言 flags 恒 0）。
3. **`DZ` 端到端（指令 → `rf0` 读回）**：`fodiv 1.0/+0.0` 在本核 `rd5 = 0x7FF0000000000000`、`rd6 = 0x7FF800007FC00002`（`DZ`），`−1/+0` 与 `1/−0` 的 `±Inf` 符号正确，ft 形式同；特殊值组 **8 例** DZ（3 个除数符号 × 2 格式 + tiny/−0 × 2），7 组同镜像 QEMU 逐字节一致。
4. **特殊值**：`0/0`、`Inf/Inf`、`sqrt(−4)`/`sqrt(−Inf)` ⇒ canonical qNaN + 仅 `NV`（特殊值组 **8 例** NV，2 格式 × 4 形状）；`Inf/0`、`qNaN/0` 不置 `DZ`；`rootn(−0,2)` = −0（规范未定，不作值断言）。另：负号 qNaN 的符号本核清 0（hardfloat 同、softfloat 保留），单列 model-only。
5. **逐例三方一致**：单元台 div ft/fo **1525 例**、sqrt ft/fo **1000 例**（本核 == hardfloat `DivSqrtRecFN_small` == 精确 oracle，值 + 5 位标志全 0 差）、rem ft/fo **305 例**（== oracle）；核上 7 组 **== 独立模型逐字节**且 **== QEMU 同镜像逐字节**（`divrem_nan` 模型only）；`divrem.yaml` **65 语义**（26 本族 + 28 算术 + 11 转换）core == YAML == QEMU **65/65**、故障 **10/10**；全部故障镜像 **45/45**。
6. **273 md5** `2d4d94651346ef673c5a855e024c1489`（期望侧与核上侧相同）。
7. **门控**：elab/Verilator rc=0 且 `%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree`/`check-index-blobs` rc=0（补丁集 9 组 333 条）；L1 红为 `check-run-artifacts`/`check-temp-dirs`（他任务日志/临时目录）与 `check-knowledge-refs`（第 1 轮审阅记录里 2 处具体 `.work/**` 路径，非本轮改动，按纪律不改写审阅记录 ⇒ 移交处置）；L2 rc=0；`make check-inst`（L3）rc=0（vast 1051/1056 通过、5 条 deferred 为既有 C-27；tiny 44/44；载体 26 册）；`check-case-ledger` PASS（2085 条身份）。
8. 完成区 ≤30 行、无运行期路径；未使用节点（构建/运行均主控机）。

**新发现/坑**：
- `DZ` 与 `±Inf` 来自**两个不同来源**：`infiniteExc` 是 `DZ` 标志的唯一来源（x/0 路径 `sExp=0`，`infiniteExc || in.isInf` 已把指数定到 Inf ⇒ 该形状**不需要** `in.isInf`）；`in.isInf` 是**不置 `DZ` 的 ±Inf 结果**（无穷被除数、`sqrt(+Inf)`）的来源。「两者都必需」只在**族级**成立（各管一类形状），不是同一条路径两个都要。实测：去掉 `infiniteExc` ⇒ 除法标志红 5 例/格式；x/0 路径不置 `in.isInf` ⇒ 全绿（值也不红）；blanket 去 `in.isInf` ⇒ `sqrt(+Inf)` 值红 440/495。
- 多周期单元必须按**格式**门控 `start`：另一格式的实例被同一 `start` 点着后会长期占 `busy`，本格式下一条指令被**静默丢弃**——单元台逐例独立喂数永远发现不了，只有核上连跑才暴露。
- 取余的就近取偶判据要用**本拍更新后**的余数与**本拍**的商位（用上一拍寄存的商位会在平局处分错）。
- 除法初始余数必须先减掉 `ma ≥ mb` 的整数商位：`ma == mb` 时 R 会停在 `mb` 而非 0，整族精确商差 1 ulp。
- 开方奇偶位取自 `ea` 而不是 `sExp`（两者差一个奇数常数），且 radicand 的移位必须同步加 `p`——只改一处结果差 √2。
- sNaN 结果 payload（本核/hardfloat/gem5 canonical、softfloat/QEMU 保留 quieted payload）与 NaN 的**符号位**（本核/hardfloat 清 0、softfloat 保留）是两类已声明差异；前者**不能**在 QEMU 门控的 YAML 里钉位型（spec §2.1 只规定「返回 qNaN」，未定 payload）⇒ `forem sNaN` 的 YAML 例只钉 `NV`、canonical 值留在 sweep 的 model-only 组——否则 `check-inst` 必然红。
- `make_patch.py` 的幂等比较**剥离 `index` 行**（只比 diff 正文）⇒ 只改补丁里的注释也不会刷新新侧 blob hash，`check-index-blobs` 会红（`index` 的新侧与现场 blob 不符）；处置：删掉该补丁文件后重跑 `make_patch.py <component>` 重导出。另：手工改补丁正文时**行数必须与 `@@` 计数一致**，多一行会让 `git apply` **静默丢掉文件最后一行**（现象是远处报 `Missing closing brace`，与本行无关）。
- `qNaN rem ±0`：spec §2.1 两句交叠（「`rfHD` 为 ±0 ⇒ NV」对「qNaN 作输入不置标志」），本实现按 softfloat/hardfloat 的 NaN 优先（不置 NV）。

**遗留问题**：① `qNaN rem ±0` 的口径请 architect 裁定后是否入 spec（现与 QEMU 一致；hardfloat 无 rem 模块，不作对照）；② 未 commit（提交权归 architect）；③ 本任务书硬约束 1 的临时目录写的是他任务号（`m12-chipyard-012`），按本任务号执行并披露（`ISS-390`）。
④ 返工项处置：R1（完成区因果 + `WumingFP.scala` 类注释 + README 同款措辞）✅已修；R2（`inventory.md` 补 2 行，`check-inst` 回绿）✅已修；建议项（`rem_*` 补 `−Inf` 被除数、`−0` 除数各 1 例）✅已补 —— 复验见审阅记录第 2 轮。
⑤ `forem sNaN` 的 YAML 例改为只钉 `NV`（§2.1 未定 payload，QEMU 保留 quieted payload、本核 canonical）：若 architect 认为该例必须钉 canonical 值，则只能走 `deferred` 精确登记（QEMU 门控不可能通过），请裁定。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = `WumingFP.scala` 的 `WumingDivSqrtRecFN`/`WumingRemRecFN`/`WumingFpSlow`、`WumingDecoder` 的 6 条解码与合法性、`WumingCore` 的 `sFpSlow` 与写回/标志、`tools/chipyard/{fp_ref,fp_sweep,fp_unit}`、`tests/inst/fp/divrem.yaml`、证据脚本。缺陷都由「单元台 vs hardfloat / vs 精确 oracle」「核上字节级对比」「QEMU 同镜像」「273 回归」「门控」的真实输出暴露，逐条修复后复跑。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 除法初始余数未减整数商位（`ma == mb` 时停在 `mb`）⇒ 整族差 1 ulp | ✅已修 | `leadBit`/`leadRem` 预减 | D `div ft/fo` 1525×2 全 0 差 |
| F2 开方奇偶位取自 `sExp` 且 radicand 未加 `p` ⇒ 结果差 √2 | ✅已修 | `pBit = ea(0) ^ ((sw+2)%2)`；`xZ` 按 `pBit` 选移位 | D `sqrt ft/fo` 1000×2 全 0 差 |
| F3 取余初始 `rem = ma` 与「逐位喂 ma」重复计 ⇒ 全错 | ✅已修 | `rem := 0`（循环自己喂被除数位） | D `rem ft/fo` 305×2 全 0 差 |
| F4 取余 tie 判据用了上一拍的商位与旧余数 | ✅已修 | 改用 `remNew` / `ge` | D rem 全绿；注入③ 可达 FAIL |
| F5 取余 pass-through 仍让 rounder 报 `UF\|NX`，且 ft 结果未截到 32 位 | ✅已修 | `io.flags := Mux(passZ, 0, …)`；`passBitsZ` 取 `(ew+sw-1,0)` | `0 rem 3`、`3 rem Inf` 用例通过 |
| F6 `WumingFpSlow` 未按格式门控 `start` ⇒ 另一格式实例占 `busy`，本格式指令被静默丢弃（核上 15 拍垃圾值） | ✅已修 | 三个 for 循环加 `io.isFo === isFo.B` | G 7 组全绿；F 65/65 |
| F7 除法特殊值分支不发 `done`（`busy && lastStep` 恒假）⇒ `0/0` 永不结束 | ✅已修 | `doneReg := (busy && lastStep) \|\| (startNow && !normal)` | D/YAML 特殊值用例通过 |
| F8 `normalise` 要求 mag ≥ `sigWidth+2` 位（余数只有 `sigWidth` 位 ⇒ elaboration 报越界） | ✅已修 | `rmagZ.pad(sw + 2)` | emit rc=0 |
| F9 YAML 的 ft 用例误按 fo 位型算期望（`fo` 参数默认值） | ✅已修 | 6 例显式 `fo=False` | F 65/65 |
| F10 `divrem_special` 的 ft 用例由 fo 位型 `& 0xFFFFFFFF` 生成 ⇒ 变成 `0/0`（DZ 例只剩 5） | ✅已修 | 每形状显式给 ft/fo 位型 | dz=8 nv=8；断言改为按形状名逐条 |
| F11 负号 qNaN 的符号口径与 QEMU 不同（本核/hardfloat 清 0） | ✅已修 | 该对移入 `divrem_nan`（model-only）+ README/向量注释披露 | 7 组 `QEMU == core` 全绿 |
| F12 证据脚本的周期断言在 mark 缺失时会「空 == 空」假绿 | ✅已修 | 先断言 14 个 mark 全中 | H 段 15 条全绿 |
| F13 任务工作树缺安装根 ⇒ L1 三项 + L2 假红 | ✅已修 | 软链到主工作树（gitignore 内） | L1 仅剩他任务两项、L2 rc=0 |
| F14 「sim 比源码新」把「只改注释」误判陈旧 | ✅已修 | 改判 `sim -nt <elaborated .fir>` | C 段 PASS |

**判决**：finding 全部已修；证据脚本 165/165 全绿 + 注入 16/16（先红后绿、md5 对账）；状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（均本人在 worktree 内执行，HEAD `a339e77c`；证据归档于运行期证据目录 28 件）
1. 全量 该任务的运行期证据脚本 `run.sh` → `== summary: PASS=165 FAIL=0 ==`、`FULL_RUN_EXIT=0`；注入全部还原并 `touch` 强制重建后再跑一遍 → `PASS=165 FAIL=0`、`FINAL_EXIT=0`。分段：C elaboration/Verilator rc=0 且 `%Error`=0；D div ft/fo 1525、sqrt 1000、rem 305 三方 0 差；E 273 md5 `2d4d94651346ef673c5a855e024c1489`；F 65 语义 core==YAML==QEMU 65/65、故障 10/10、model-only 恰 1；G 7 组 core==model==QEMU、故障 45/45、special `dz=8 nv=8`；H 14 mark 全测得（fo 56 / ft 27、forem d=1/10/100/1000→55/64/154/1054）；I apply-series/check-source-state/check-patch-tree rc=0、L2 rc=0、L1 红仅 check-run-artifacts/check-temp-dirs（42+5 条 offender 全为他任务，本任务 0 条）。
2. 注入自检 `run.sh --self-test-inject` → `INJECT_EXIT=0`、16 PASS/0 非预期 FAIL：①div 785/790 ②div 标志 ft/fo 各 5 ③rem 43/38 ④div_ft/div_fo 红；4 次 `cp`+md5 还原 matched + 回绿 —— 与完成区逐条一致。
3. 独立周期探针（自建 21 mark，非脚本内 mark；源码/trace/结果见归档）：8 组 fo 除法（0.5/2、1/1、max/1、1/最小非规格、最小非规格/1、非规格/非规格、max/最小非规格、−0.5/2）**全 56**；3 组 fo 开方（0.5、max、最小非规格）**全 56**；ft 除法 2 组 27、ft 开方 27；`0/0` 与 `sqrt(−4)` 各 1 拍；`forem` d=2/7/52/402→**56/61/106/456**（=53+d+1 全中）、d=−30→1 拍（不进循环）。
4. 反例注入共 7 次（脚本内 4 + 我自选 3），全部 `cp`+md5 还原回 `099dcc33…` 且复跑回绿：
   - **injB（DZ 只置 `infiniteExc`）**：`in.isInf := infZ && !divZeroZ`（`0d298a4d`）→ C 现场重建（sbt 07:35:54）+ D 49/49 + F 65/65 + G 37/37 **全绿**、dump md5 与绿跑逐字节相同 ⇒「只置后者是垃圾指数」**不成立**；
   - injB2 `in.isInf := false.B`（`8ba8e4cb`）→ D 红：sqrt ft/fo 值+oracle 440/495（`sqrt(+Inf)` 依赖 `isInf`），div 绿（单元台无 Inf/有限对，Inf 形状由核上 sweep 覆盖）；
   - injC sqrt 提前 1 拍（`8fa4d246`）→ D 红 440/495、`op43 26→25`/`op44 55→54`；injD 去 `passZ` 标志掩码（`87abf76b`）→ D 红 rem 各 2，`[ORACLE] rem ft a=0 b=800000 want=0/0 got=0x18`（NX|UF）⇒「不置 NX/OF/UF」有可达 FAIL 路径。
5. 口径实测（自建 5 例，本核 + QEMU 各跑）：`qNaN rem ±0`、`+Inf rem qNaN` 两边均 `qNaN(0x123)+flags 0`；`sNaN rem +0` 本核 canonical / QEMU quieted payload、NV 两边同 ⇒「现与 QEMU 一致」成立。
6. `make check-inst`（L3）→ **rc=2**：`门控覆盖表未登记 L3 载体: arith.yaml`（013 遗留，014 前即红）与 `divrem.yaml`（本任务新增册未登记，`inventory.md` 本次未改）。

**约束核验**：① `git diff 7a9fc738 a339e77c --stat` 恰为完成区所列 13 文件；`git status -uall` 审前/审后均 0 行（本记录为唯一写入），13 个交付文件 md5 == HEAD，源码树无 `*.inj-bak`/`*.preinject` 残留；② 完成区 27 行 ≤30、无运行期路径（硬约束 1 的任务号笔误已按 `ISS-390` 披露）；③ 计数均脚本现场值；④ 未 commit、未 push、未改台账、未占 207/208。

**判决：Needs Revision**（仅文档/登记两处，不动 RTL 与测试）
- **R1（阻断：硬约束 3「完成区与真实输出对齐」+ `代码行为` 不一致）** 完成区「新发现/坑」第 1 条「只置 `infiniteExc` 是指数被清掉的垃圾」被 injB 端到端证伪，须按实测改正：`infiniteExc` 是 `DZ` 标志的唯一来源（inj②：div 标志 ft/fo 各红 5）、`in.isInf` 是 ±Inf 形状的来源（injB2：`sqrt(+Inf)` 红 440/495），x/0 形状上 `infiniteExc` 单独已足够（该路径 `sExp=0`，指数由 `notNaN_isSpecialInfOut = infiniteExc || isInf` 定到 Inf）。同款机制表述（`WumingFP.scala` 类注释、README「前者给无穷值、后者清指数域」）列为同轮建议、非返工条件。
- **R2（门控）** `tests/inst/inventory.md`「门控覆盖（L2/L3）」表补一行 `fp/divrem.yaml | — | ✓`（本任务新增册；返工后 `make check-inst` 应只剩 `arith.yaml` 一条）。
- **非阻断 finding**：① `forem` 三边界只隔离了 **+Inf** 被除数与 **+0** 除数（−Inf/−0 无独立向量，单元台/sweep/YAML 三处均无；sNaN ≥2 例 ✓）——验收标准 2「各有断言」已满足，建议补两例；② `qNaN rem ±0` 无既有向量，spec §2.1 两句确属交叠，且 §2.5 有「无效优先于 qNaN 传播」先例（`0×∞` 即使加数为 qNaN 仍 NV）⇒ 冲突为真，口径请 architect 裁（我只给实测证据、不代裁）；「与 hardfloat 一致」措辞不准（hardfloat 无 rem 模块）。

## 返工项（reviewer 第 1 轮 Needs Revision）

**R1（阻断，文档订正）**：完成区「新发现/坑」第 1 条的因果写反。实测（reviewer 注入 `in.isInf := infZ && !divZeroZ`）：
- `infiniteExc` 是 **DZ 标志的唯一来源**；x/0 形状上 `in.isInf` **非必需**（该路径 `sExp=0`，`notNaN_isSpecialInfOut = infiniteExc || isInf` 已把指数定到 Inf）
- `in.isInf` 是 **±Inf 形状**的来源（blanket 去掉 ⇒ `sqrt(+Inf)` 值红 440/495）
- ⇒ 「两者都必需」**只在族级**成立（各管一类形状），不是「同一条路径两个都要」
**改法**：完成区按此改写；`WumingFP.scala` 类注释与 `README` 同款措辞作为建议项，非阻断。

**R2（阻断，门控）**：`make check-inst`（L3）rc=2，两条未登记载体：
1. `fp/divrem.yaml`（本任务新增）
2. `fp/arith.yaml`（`013` 遗留，014 之前即红）
**改法**：`tests/inst/inventory.md` 的门控覆盖表补 `fp/divrem.yaml` 与 `fp/arith.yaml` 两行；返工后 `check-inst` 应 rc=0。

**建议（非阻断）**：`forem` 只隔离了 `+Inf` 被除数与 `+0` 除数，`−Inf`/`−0` 三处无独立向量；建议补两例。

### 第 2 轮 engineer 自审（返工）

返工范围 = R1/R2 + 建议项（RTL 逻辑未改，只动 `WumingFP` 类注释）。方式：自主逐行审查 + 每条现场复跑。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 完成区「新发现/坑」第 1 条因果写反 | ✅已修 | 改为「`infiniteExc` = `DZ` 唯一来源（x/0 不需 `isInf`）；`in.isInf` = 不置 `DZ` 的 ±Inf 结果；只在族级都必需」，附三条实测 | 全量脚本 + 注入自检复跑（见完成区） |
| R1 同款措辞：`WumingFP.scala` 类注释、README | ✅已修 | 类注释 4 行重写、README 特殊值段改写；补丁改后 `reset --hard <base>` + `make apply-series` 重新收敛 base+1 | `check-patch-tree` rc=0（9 组 333 条）、`check-source-state` OK |
| R2 `check-inst` rc=2：`fp/divrem.yaml`、`fp/arith.yaml` 未登记 | ✅已修 | `inventory.md` 门控覆盖表补 2 行 | `--check-only`：覆盖登记 OK（L2 3 册 / L3 26 册）；`make check-inst` rc=0 |
| S1 `forem` 只隔离 `+Inf` 被除数 / `+0` 除数 | ✅已补 | `REM_PAIRS` 补 `ninf_two`、`one_nzero`（ft/fo 各 +2 ⇒ `rem_*` 18 例/格式） | 核 == 模型 == QEMU 逐字节；oracle 期望独立算得（qNaN + `NV`） |
| N1 `divrem.yaml` 注释「两路同时置」 | ❌不修 | 只陈述两路都置（事实成立），未宣称各自角色；改它牵动向量身份/台账 | 与 `rounder.io.in.isInf := infZ`、`infiniteExc := divZeroZ` 对读 |
| N2 `make_patch` 幂等比较剥离 `index` 行 ⇒ 改注释后 `check-index-blobs` 红 | ✅已修 | 删该补丁后重导出（新侧 hash 与现场 blob 一致） | `check-index-blobs` rc=0（246 new-file） |
| N3 `check-inst` 首个非登记失败 = `divrem.yaml[22]`（sNaN rem 的 canonical qNaN vs QEMU 保留 quieted payload） | ✅已修 | spec §2.1 未定 payload ⇒ YAML 该例只钉 `NV`；canonical 值由 sweep `divrem_snan_*` 组（只对本核/模型）断言；证据脚本 model-only 精确名单 1→0 | F：core == YAML == QEMU 65/65；`make check-inst` rc=0 |
| N4 自审复读首版措辞：把 `Inf/Inf` 列入「`in.isInf` 给的 ±Inf 形状」——`Inf/Inf` 走 `invalidExc` ⇒ qNaN，不是 Inf | ✅已修 | 类注释/README/完成区统一改为「不置 `DZ` 的 ±Inf 结果（无穷被除数、`sqrt(+Inf)`）」；删补丁重导出 | `check-index-blobs`/`check-patch-tree` rc=0（246 new-file、9 组 333 条）；全量脚本复跑 |
| N5 手工把补丁注释由 4 行写成 5 行、`@@` 仍记 1869 ⇒ `git apply` **静默截断**文件最后一行（`WumingFP.scala` 少一个 `}`，构建在远处报 `Missing closing brace`） | ✅已修 | 从 HEAD 取回补丁、按 4 行重做；重放后源码 1869 行、括号 95/95；再重导出（`index ..06d391b`） | C 段 elab/Verilator rc=0 且 `%Error`=0；`check-index-blobs`/`check-patch-tree`/`check-source-state` rc=0 |

**判决**：finding 全部已修/已决（N3 属 spec §2.1 未定位型导致的必要收窄，已在完成区与遗留披露）；状态 `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录**（本人在 worktree 执行，HEAD `c6570fad`；日志 `m12-chipyard-014-review2-full / -inject / -check-inst / -injB-* / -injC / -restore-D` 等）
1. 全量证据脚本 `run.sh` → `== summary: PASS=165 FAIL=0 ==`、`REVIEW2_FULL_EXIT=0`；分段与完成区逐条对齐：C elab/Verilator rc=0 且 `%Error`=0；D div 1525×2、sqrt 1000×2、rem 305×2 三方全 0 差；E 273 md5 `2d4d94651346ef673c5a855e024c1489`；F `semantic=65 fault=10`、core/QEMU 各 65/65、model-only=0；G 8 组 core==model、7 组 QEMU==core、fault 45/45、special `dz=8 nv=8`；H 14 mark 全中（fo 56 / ft 27、forem 55/64/154/1054）；I apply-series/check-source-state/check-patch-tree rc=0、**L2 rc=0**，L1 红仅 `check-run-artifacts`/`check-temp-dirs`（offender 全为他任务）。
2. `run.sh --self-test-inject` → `REVIEW2_INJECT_EXIT=0`、**16 PASS / 0 非预期 FAIL**；4 注入全「→ FAIL as expected」（div 值 785/790、div 标志 ft/fo 各 5、rem 43/38、G `div_ft`/`div_fo` 红），`cp`+md5 还原 matched（源 `793b531d…`、oracle `d7e1bd35…`）并回绿。
3. **R1 三条实测**（本人注入，均 `cp`+md5 还原回绿）：① 去 `infiniteExc` ⇒ `div ft/fo: hf-flag-diff=5/5`、值 0 差 ⇒「DZ 唯一来源」成立；② `in.isInf := infZ && !divZeroZ`（x/0 不置 `isInf`）⇒ D `PASS=49 FAIL=0` exit=0 **全绿**（G 段同绿，但 SoC sim 未重建、不作证据）；③ `in.isInf := false.B` ⇒ D exit=1，**sqrt ft/fo 各 5 例**值+标志+oracle 红（共 30 项），div/rem 全绿 ⇒「`sqrt(+Inf)` 依赖 `isInf`、x/0 不依赖」成立。
4. **R2**：`make check-inst` → `CHECK_INST_EXIT=0`（vast **1051/1056**、5 deferred 全为 C-27；tiny **44/44**；载体 **26 册**）；`--check-only` 基线「覆盖登记 OK（L2 3 册 / L3 26 册）」；**反例注入**：删 `fp/divrem.yaml` 行 → rc=1 `门控覆盖表未登记 L3 载体: divrem.yaml`；`cp` 还原 md5 `f43c308f…` 相等 → rc=0。
5. **补丁完整性**：现场 `WumingFP.scala` **1869 行**、`{}` **95/95**、末行 `}`；空树 `git apply --check`=0 且 `git apply`=0 复现 1869 行/95-95；`git hash-object`=`06d391b98…` == 补丁 `index ..06d391b`；`make check-patch-tree` → `9 patch set(s), 333 patches OK` rc=0；`make check-index-blobs` → `246 new-file … OK` rc=0；`make check-source-state` 11 组件全 OK rc=0。截断事故已消除。
6. **sNaN 降级核**：spec/SimRISC-07 §2.1 只写「任一源为 sNaN ⇒ 置 NV 并返回 qNaN」，**未定 payload**（§1.4/§2.3 单 NaN 同为「返回 qNaN」；canonical 仅「双 NaN」条）⇒ 降级有据；该例仍钉 `rd6=0x7FF800007FC00001`（**仅 NV、无 NX/OF/UF/DZ**）+ 退出码，**非恒真**；canonical 值由 sweep `divrem_nan` 组（10 例、model-only、G 段 core==model 逐字节）承担。
7. 回归：`make check-case-ledger` → `现场身份 2085 条（vector 1576 / lit 509）… PASS` rc=0；`rem_ft/rem_fo` 各 **18 例**（建议项已补，`ninf_two`/`one_nzero` 在列）。

**约束核验**：① 返工改动 = **6 文件**（任务书 / README / WumingFP 补丁 / divrem.yaml / inventory.md / fp_sweep.py），`git diff de05832d HEAD --name-only` 逐项吻合、且全在完成区 14 文件内；审前审后 `git status -uall` 均 0 行、6 文件 md5 == HEAD；源码树无 `*.inj-bak`/`*.preinject` 残留；② 完成区 **29 行 ≤30**、无具体 `.work/**` 路径与宿主绝对路径；③ 计数均现场值；④ 未 commit（HEAD 仍 `c6570fad`）、未 push、未改台账、未占 207/208；⑤ 我方产物合规：`check-run-artifacts`/`check-temp-dirs` 中 `m12-chipyard-014` offender 均 **0**，临时树已删。

**判决：Accepted**（R1 因果、R2 门控、补丁完整性三项均由本人重跑证实；下列为收尾改文档的 finding，按 2026-10-22 裁定不阻断、不再开轮）
- **F1 数字误记（须改）**：完成区「新发现/坑」与上文「返工项 R1」写「blanket 去 `in.isInf` ⇒ `sqrt(+Inf)` 值红 **440/495**」——本人与第 1 轮原始日志 `m12-chipyard-014-r1-injB2-isinf-off.txt` 均为 **sqrt ft 5 / sqrt fo 5**（`PASS=41 FAIL=8`、total failures 30）；**440/495 出自另一注入** `m12-chipyard-014-r1-injC-sqrt-early.txt`（sqrt 提前 1 拍）。因果正确、仅数字错（该误记源自第 1 轮 reviewer 摘要，非 engineer 造数）。
- **F2 分项笔误**：完成区「65 语义（26 本族 + 28 算术 + 11 转换）」现场为 **26 + 25 + 14 = 65**（arith 28 是含 3 条 legality 的册总数），总数 65 正确、分项需改。
- **F3 措辞待定夺**：`divrem.yaml` 第 4 例注释仍「`infiniteExc` 与 `in.isInf` 同时置」——事实成立（x/0 路径 `infZ = infOut = true`），但易与「该形状不需要 `isInf`」读反；engineer N1 已声明不修，请 architect 定夺。
- **F4 门控行已过期**：完成区第 7 条写「L1 红为 `check-run-artifacts`/`check-temp-dirs` **与 `check-knowledge-refs`**」——本人全量跑 L1 时实际红项只有前两个（`actual=check-run-artifacts check-temp-dirs`），`make check-knowledge-refs` 单跑 **rc=0**（「具体路径 (不可复现): 0」，因 c6570fad 已改掉第 1 轮审阅记录的 2 处路径）；两个红项亦均非本任务（`check-run-artifacts` 54 条 illegal name 中 `m12-chipyard-014` 占 0，`check-temp-dirs` 5 项 VIOLATION 中占 0）。收尾时把该句改为「L1 红仅 `check-run-artifacts`/`check-temp-dirs`（他任务）」。
- **① R1 因果表述已准确**（三条实测全部复跑证实，仅 F1 数字需订正）；**② R2 门控真绿且登记规范**（`check-inst` rc=0 + 删行反例 rc=1 → 还原 rc=0，两行落在「门控覆盖（L2/L3）」表、格式与既有行一致）；**③ 补丁完整性可信**（1869 行 / 95-95 / `git apply --check`=0 / blob hash 对上 / 333+246 绿），静默截断已消除。

## 待裁定（handoff）

`qNaN rem ±0`：spec §2.1 两句对同一输入给出不同标志、无优先级措辞；§2.5 有反向先例（`0×∞` 即使加数为 qNaN 仍置 NV＝无效优先于 qNaN 传播）⇒ **真冲突**。实测本核 == QEMU（`qNaN(payload)+flags 0`）。等用户裁定后按裁定改 spec/实现/向量。

#### 收尾（architect，2026-11-12 11:25）

- 第 2 轮 reviewer **Accepted**：证据 165/0；`check-inst` **rc=0**（vast 1051/1056、tiny 44/44、载体 26 册）；补丁完整性独立验证 **1869 行 / 95-95 括号 / `git apply --check`=0 / blob `06d391b9` / 333+246 绿**（静默截断事故已消除）。
- R1 三条实测复核通过（`infiniteExc` = DZ 唯一来源；x/0 不置 `isInf` 全绿；blanket 去 `isInf` ⇒ `sqrt(+Inf)` 值红、div 绿）。
- **数字订正（F1/F2）**：①「440/495」应为 **sqrt ft 5 / fo 5**（440/495 是另一注入「sqrt 提前 1 拍」的数字）；② 语义分项应为 **26+25+14=65**（「arith 28」含 3 条 legality）。
- L1 红项现状（F4）：仅 `check-run-artifacts`/`check-temp-dirs`；`check-knowledge-refs` 已 rc=0。
- `divrem.yaml` 第 4 例注释「两路同时置」保留（事实成立、engineer N1 声明不修），记 `ISS-400`。

