# GOLDEN-001t：M1 标量 golden 校正与设计说明

**状态**：已验证
**模块**：golden
**项目里程碑**：维护（M1 标量 + `scope: fp` 66 条；特权/原子/fence 在范围外；原“不扩展浮点”仅指初始范围）
**依赖**：当前 spec/、contract-isa.md、contracts/opcodes.yaml、tests/inst/schema.md

> **口径说明（2026-10-27）**：本任务书前部“43 tests / 60 FP / sub.uo 待裁定 / 浮点不实现”等为历史记录；当前最终口径见文末“文档口径与已知不足”段（49 tests、66 FP、730 回放、L2 PASS、ADR-0049；以文末“最终验收”为准）。

## 用户确认

用户原话：“按当前仓库规范，修复你原有的整数、访存、寄存器传送和控制流 golden，并重写两份文档，同时将浮点和后来新增的特权指令明确列为暂不支持”。

## 目标与范围

校正 `components/golden/dadao_interp_v5.py` 与 `validate_interp_v5.py`；重写 `README.md`、`DESIGN.md`；新增 `components/golden/test_interp_v5.py`、`test_validator_v5.py` 与可复用证据脚本（同目录）。保留原有未提交工作，只做授权范围的修改。不修改 spec/、contracts/、tests/inst/、LLVM/QEMU。

依据：contract-isa §1–8、§10–15 与对应 spec/SimRISC-00/01/02/03/04/05/06/08/09/10/12；若投影矛盾须披露而非按向量票数裁定。仅编码取自 opcodes；语义、测试期望独立来自规范，不读取 LLVM/QEMU/向量生成器。

范围 = 当前原标量指令族（整数/地址、RD/RB/RA 访存与传送、控制流、swym）；浮点/RF、特权、原子、fence 不实现。已定义而超出本模型的指令报告 Unsupported，不能冒充 ILLI。保留编码仍 UNDI；原标量家族内明确的当前地址算术变体按规范核实实现。

API 保留 decode/check_legality/build_state/run；允许新增范围查询与严格输入验证。run 单步状态、PC/rb0 含义须一致并文档化，异常保持输入状态；不承诺机器 MMU/ROM/exit-port/异常入口。验证器必须核对身份、状态、PC，缺少语义断言不能 PASS；空集/非法输入非零退出；范围外与机器层跳过独立统计。

## 分工

engineer：只改解释器与 `test_interp_v5.py`（模型的规范测试）。主会话：验证器、说明文档、证据脚本及任务完成区。reviewer：独立重跑与反例审查，不改实现。

## 下发前预检

1. 内部一致：上述范围遵用户原话，未授权浮点/特权扩展。
2. 前置可用：Python3/PyYAML、规范、编码表及仓库向量均已存在；不依赖组件构建。
3. 可执行：导入/独立规范测试/仓库向量回放/验证器反例现在可跑；L2 运行后如缺组件如实 BLOCKED，以本模型直接测试替代，不报全仓 PASS。
4. 编码与向量：当前编码 155 m1 + 60 fp + 11 excluded + 1 m3；ISA 向量 700 条（现场统计，非固定验收阈值）。历史基线无法导入（5 个废弃 ID，exit 1）。
5. 拟改文件与 spec/ 无交集；spec 只读。

## 验收

- 上述文件存在，导入/CLI 可运行；逐指令范围清单可检查，不再声称历史 178 条。
- 定宽算术/除余/比较/移位按位宽与符号逐项独立计算；边界覆盖双目的别名、0号源/目的、块重叠、内存端序/对齐、64位控制流与48位取址、RACNT/MemRAS、精确异常。
- 仓库向量逐条回放，所有 FAIL 查明；外部规范/向量冲突不隐瞒，不修改外部数据迁就实现。
- 验证器对错误身份/结果/异常/PC/空数据能失败；反例在临时树内注入，真实源码哈希不变。
- 文档写最终行为、依据、例子与已知边界，不沿用未经确认的 D-v5 决策。
- 独立 reviewer 重跑与主动证伪；所有命令捕获真实退出码；不提交或推送。

## 完成区

**修改文件**：`components/golden/{dadao_interp_v5.py,validate_interp_v5.py,README.md,DESIGN.md,test_interp_v5.py,test_validator_v5.py,check_golden.py}`；本任务书。原有4份未提交文件已备份并哈希核对于 `/tmp/opencode/GOLDEN-001t/before/`。
**测试结果**：直接测试、反例检查通过；仓库回放有10条规范/向量分歧，不能判全仓通过；当前规范借位含义待用户裁定。
**验收结果（真实输出）**：
```text
Ran 36 tests
OK
ARITH_MATRIX checked=3402
ARITH_VECTOR_INPUTS independently_recomputed=158
SHIFT_EXT_VECTOR_INPUTS independently_recomputed=85
SHIFT_MATRIX checked=360
EXIT=0
历史记录（浮点扩展前）：TOTAL 700: PASS-encoding=166 PASS-execution=476 FAIL=10 SKIP-deferred=5 SKIP-scope=0 SKIP-machine=43
EXIT=1
```
**反例留证**：`check_golden.py` 实际输出 `evidence-mutant-model: expected=1 actual=1` / `evidence-restored-model: expected=0 actual=0`；结果/身份/PC/异常四组向量注入均1、还原均0；`evidence-empty-input: expected=1 actual=1`；`REAL SOURCE SHA256 UNCHANGED`。完整日志 `.work/log/golden/GOLDEN-001t/evidence-*.log`；可复现脚本保留在 components/golden/。
**独立全量重算**：遍历全部ISA向量；158条适用定宽算术/比较、85条移位/扩展逐条从规范公式重算并比对模型和已给期望；另独立矩阵覆盖位宽/符号/除零/溢出/负数取商等。
**L2**：尝试 `make check-modules JOBS=8`，启动器 `FileNotFoundError: make`、退出1，make未启动（无make退出码）；`command -v make/gmake`均未找到。BLOCKED（工具缺失），不是PASS；替代证据为上述模型直接测试。详见 `L2.log`。
**新发现/坑**：现行`sub.uo`规范将128位高结果和0/1借位混写；以`SpecificationGap`阻止歧义输入产出假标准答案；既有向量未覆盖借位，独立测试补保护。reviewer发现异常附加断言被忽略、编码输入RA0 SBZ未查，均修复并补反例。
**遗留问题**：10条store零源旧向量（mem-rd 8 + mem-rb 2）仍期望ILLI，规范允许；不改外部向量凑绿。`sub.uo`借位且高目的非rd0须用户裁定（是否ADR也须用户确认）。浮点/特权/原子/fence/机器权限未实现是明确范围限制。未提交/未推送，工作分支GOLDEN-001t。
**边界核验**：`SHARED_SPEC_CONTRACT_VECTOR_DIFF_EMPTY=True`；7个输出文件存在；完整哈希记录 `final-files.sha256.json`。文档已重写为最终规则/例子/范围/阻断，删除历史未经确认的D-v5裁决。

## 审阅记录

### 第 1 轮 reviewer 验收

**结论：Needs Revision（验收阻断）**。本次标量修复与两份说明通过下列独立检查；未发现尚未修复的确定实现缺陷。`sub.uo` 借位含义待用户裁定、L2 缺工具，不能把整个任务置为已验证。
**审查范围**：解释器、验证器、两份测试、证据脚本、README/DESIGN；对照 SimRISC-00/04/08 与 contract-isa 的算术、合法性、RACNT、PC、访存规则。未采信 LLVM/QEMU 输出作为 oracle。
**发现并复核修复**：异常语义用例的显式错误 expected_state/expected_pc 原先可 PASS；encoding 输入 ra0 SBZ 非零原先可 PASS。两处均已修复，新增反例由 reviewer 独立重跑通过。
**独立命令与真实输出**（完整输出见 `.work/log/golden/GOLDEN-001t/reviewer-*.log`）：
```text
python3 -B -m unittest discover -s components/golden -p 'test_*v5.py' -v
Ran 36 tests in 4.378s
OK
ARITH_MATRIX checked=3402
ARITH_VECTOR_INPUTS independently_recomputed=158
SHIFT_EXT_VECTOR_INPUTS independently_recomputed=85
SHIFT_MATRIX checked=360
EXIT=0
python3 -B ./components/golden/validate_interp_v5.py
历史记录（浮点扩展前）：TOTAL 700: PASS-encoding=166 PASS-execution=476 FAIL=10 SKIP-deferred=5 SKIP-scope=0 SKIP-machine=43
EXIT=1
python3 -B ./components/golden/check_golden.py
SCALAR TESTS AND COUNTEREXAMPLE CHECKS PASS (repository replay is separate)
EXIT=0
INJECT reviewer arithmetic-right-shift->logical SHA256_CHANGED=True
INJECTED_SAME_EVIDENCE_EXIT=1
RESTORED_SHA256_IDENTICAL=True
RESTORED_SAME_EVIDENCE_EXIT=0
SOURCE_SNAPSHOT_IDENTICAL=True
CHANGES_SINCE_REVIEW=[]
SHARED_SPEC_CONTRACT_VECTOR_DIFF_EMPTY=True
STATUS_IDENTICAL=True
```
**独立注入**：只在 `/tmp/opencode/GOLDEN-001t/reviewer/` 副本改有符号右移为逻辑右移，重跑同一 `check_golden.py`；备份字节恢复、SHA256相等后重跑回绿，无组件重建需要。真实源码未改。
**10项 FAIL 逐项归因**：mem-rd 的 st.b/w/t/o、stm.b/w/t/o 与 mem-rb 的 st.o/stm.o 零号源旧向量；逐项实测为 `fault golden=None vector=ILLI`，与当前允许零号源的规范一致，未改共享向量凑绿。
**约束核验**：输出文件存在；仅任务声明范围；无 spec/contracts/vectors 修改；未提交/推送；范围外指令明确 Unsupported；精确异常、PC、数值范围检查有真实失败路径；全量适用算术/移位期望独立重算。
**L2 独立核验**：`make=None`、`gmake=None`；尝试 `make check-modules JOBS=8` 得 `FileNotFoundError`，make 未启动，无 make 退出码，BLOCKED。不得以本模型测试代称 L2 全绿。
**待解除条件**：用户裁定 sub.uo 高结果含义（是否 ADR 另确认）；提供可运行的 L2 环境；10条旧向量同步属独立数据工作。当前文档已明确上述边界，不能承诺完整 golden 或全仓回归通过。




## 用户追加：逐条指令文字说明（2026-10-13）

用户原话：“把每一条指令的golden标准的详细文字说明写成一个文档”。
交付：`components/golden/INSTRUCTION_REFERENCE.md` 与保留的生成器 `generate_instruction_guide.py`；README/DESIGN增加入口。未修改执行器、共享规范、向量或既有完成区。
逐条列出当前标量152个身份的用途、操作数、编码字段、计算/写回、异常/边界、算例及规范依据；其余75个身份列为范围外；sub.uo待裁定原样保留，未新增ADR决策。
验证输出：`IDENTITIES exact match: 152`、`ALL ENTRIES fields/source/example present; links valid`；生成器 `--check` 返回0。
临时文档注入：`FAIL: instruction reference missing or differs from generator`（exit1）；恢复后 `PASS: instruction reference reproducible (not a semantic proof)`（exit0）；`REAL_DOC_UNCHANGED=True`。
验证边界：上述计数/链接/一致性检查不证明语义；内容按当前合约/规范分族编写。纯文档追加未重跑组件构建；原L2缺make、sub.uo和10条旧向量阻断仍有效。未提交/推送。


## 用户追加：展开共同规则（2026-10-13）

用户原话：“请你把文档中的共同规则写的更详细，语言更自然一些”。
已同步修改逐条说明及其生成器：按执行输入输出、寄存器字段、零号寄存器、位宽扩展、PC、内存、结果分类、精确异常、返回栈概念及call/ret流程展开，用具体算例解释。保留原152条指令定义及已有规范阻断，不改执行器或规范。
验证：生成器`--check`退出0、`git diff --check`退出0；152条身份无重漏，来源链接和call/ret章节引用有效。纯文字修改未重跑执行测试。


## 用户追加：展开尚未裁定与验证边界（2026-10-13）

用户原话：“把尚未裁定与验证边界写的更详细一些”。
已同步扩写逐条说明及生成器末节：sub.uo两种解释与处理条件、十条旧向量的归因和修正要求、已有证据能/不能支持的结论、SKIP含义、模型能力边界、L2环境阻断、伪指令/旧编码与后续验收条件。测试数字明确为此前审查记录，不冒充本次新跑结果。
验证：生成器`--check`退出0、`git diff --check`退出0；`ENTRIES=152 LINKS=OK`。没有修改执行器、规范、向量、ADR或原验收结论；纯说明修改未重跑执行测试。


## 用户追加：逐条伪代码、浮点纳入与远端合并（2026-10-20）

用户原话：“请你在说明文档中，用伪代码的方式，把每一个指令具体执行的任务写的更清楚、唯一、明确。另外，处理当前代码和远端的合并。并扩大golden的范围，把浮点也加进来”。

交付范围：逐条参考文档与生成器覆盖当前 M1 原标量、额外确认的 `aip.si`、及 `scope: fp` 60 个身份，共 213 个受支持身份；每条独立列出编码字段、执行伪代码、写回/异常和规范来源。解释器接入 binary32/binary64 浮点、FCSR、RF 访存和传送；`fp_ref.py` 用整数位模式与精确有理数实现格式运算和四种舍入，不以宿主浮点、LLVM 或 QEMU 生成期望值。规范开放点仍报 `SpecificationGap`。不修改规范、合约、向量或 ADR。

远端处理：`origin/master` 相对本地原工作点为 327 ahead；`git merge --no-commit --no-ff origin/master` 无冲突，远端变更已进入暂存区，本地 golden 文件保持原哈希。合并提交仍待用户确认，未 commit/push。当前分支 `GOLDEN-001t`，不得把这组远端暂存变更与本任务显式 staging 混淆。

验证命令及真实结果：

```text
python3 -B -m unittest discover -s components/golden -p 'test_*v5.py' -v
43 tests ... OK
python3 -B ./components/golden/check_golden.py
MODEL TESTS AND COUNTEREXAMPLE CHECKS PASS; all injected FAIL/restore pairs matched expected exits
python3 -B ./components/golden/validate_interp_v5.py
TOTAL 711: PASS-encoding=171 PASS-execution=482 FAIL=10 SKIP-deferred=5 SKIP-scope=0 SKIP-machine=43; EXIT=1
python3 -B ./components/golden/generate_instruction_guide.py --check
PASS: instruction reference reproducible (not a semantic proof)
```

10 条回放 FAIL 均为原存数向量把规范允许的 `rd0/rb0` 源错误期望为 ILLI；`aip.si` 的 7 条执行向量已通过。标量与浮点直接测试通过；不声称全量向量或 L2 全绿。FP 的规范开放点、验证边界见 `DESIGN.md` 与 `docs/fp-oracle-design.md`。提交与 push 仍按 AGENTS 规则另行确认。

## 用户追加：同步远端合并与 FP 扩展（2026-10-26）

用户原话：“请先根据远端的内容更新golden和测试向量”。

远端处理：撤销上一轮基于 `77bd3dc1` 的未提交合并，按最新 `origin/master`（`cb3c4f1d`，相对 `d517aa43` 领先 502 个提交）重新执行 `git merge --no-commit --no-ff`；0 冲突，877 个文件进入暂存区，合并仍未提交。本地 `components/golden/` 的 4 个修改文件与 `docs/fp-oracle-design.md` 改写已按 SHA256 原样保留。

按合并后合约更新：

- `cmp` 窄宽度比较结果按 SimRISC-04/08/09/10 写满 64 位 `−1/0/1`，不再按操作宽度零扩展。
- `contracts/fp_semantics.yaml` 的 66 条 `scope: fp` 全部纳入；新增 `roundint`（`ftrnd`/`fornd`）、`minmax`（`ftmin`/`ftmax`/`fomin`/`fomax`）、`fma`（`ftfma`/`fofma`），语义分别按 contract-fp §18/§19/§20。
- `immu6` 仅对块形式表示个数；`ftrnd`/`fornd` 改为 one-hot selector 校验；`ftfma`/`fofma` 目的为 `rfha`，目的 rf0 为 ILLI。
- `generate_instruction_guide.py` 修复 `SimRISC-xx: mnemonic` 引用解析，并为三个新族生成伪代码/算例；`INSTRUCTION_REFERENCE.md` 重生成（219 条身份，scalar=153，fp=66）。

验证（真实输出）：

```text
python3 -B -m unittest discover -s components/golden -p 'test_*v5.py'
Ran 46 tests ... OK
python3 -B ./components/golden/validate_interp_v5.py
TOTAL 708: PASS-encoding=171 PASS-execution=488 FAIL=0 SKIP-deferred=5 SKIP-scope=0 SKIP-machine=44
EXIT=0
python3 -B ./components/golden/check_golden.py
MODEL TESTS AND COUNTEREXAMPLE CHECKS PASS (repository replay is separate)
EXIT=0
python3 -B ./components/golden/generate_instruction_guide.py --check
PASS: instruction reference reproducible (not a semantic proof)
EXIT=0
```

边界：回放仍无 FP 仓库向量，FP 由 46 项单测（含逐身份 66 条冒烟）覆盖；`sub.uo` 借位、f2i NX、`rootn(-0,2)`、remainder/scaleB 边界仍未裁定。合并与本次修改均未提交/推送。

## 用户追加：伪代码函数提前声明（2026-10-26）

用户原话：“golden的说明文档还需要修改：你不能在没有说明的情况下，在伪代码中使用我看不懂的函数。要提前声明”。

处理：在 `INSTRUCTION_REFERENCE.md` 的「共同规则」新增 §10，集中声明伪代码出现的全部函数、常量与记号（状态快照/提交、整数扩展、访存、RAS、FP 编解码/转换/运算），并给出输入输出、语义和实际实现位置；每条指令的伪代码标题增加“函数与记号见共同规则 §10”指针。转换类伪代码由 `tmp`/`flags(tmp)` 改为显式的 `val`/`flg` 拆分，比较类伪代码函数改名为 `has_signaling_nan`。

验证：`generate_instruction_guide.py --check` 退出0；`INSTRUCTION_REFERENCE.md` 重生成；46 项单测与向量回放不受影响。

## 用户裁定与同步：`sub.uo` 借位 = 0/1（2026-10-26）

用户原话：“选择B，并进行同步、ADR”。

- **ADR-0049** 置 `Accepted`：`sub.uo {rdHA, rdHB}, rdHC, rdHD` 的 `rdHA` = 借位（`rdHC < rdHD` 时 1，否则 0），`rdHB = (rdHC − rdHD) mod 2^64`；不写 128 位结果的全 1 高半，需要 128 位有符号高半时用 `sub.so`。
- **同步范围**：`spec/SimRISC-04 §1.1`、`spec/SimRISC-00` 附录 `0.5.6-rc`、`.tao/contracts/contract-isa.md §6.1.1`、`manifests/spec-readonly.lock.toml`（SimRISC-00/04 哈希 + 授权原话）、golden 解释器/单测/生成文档、`generate_isa_vectors.py`、`tests/inst/base/reg-arith.yaml`（新增 `0−1`、`5−7` 借位用例）。
- **不改**：QEMU 原本已按借位实现；LLVM 只用 `sub.uo {rd0, dst}`（高位丢弃）；DDLN 原本已描述借位。
- **验证（真实输出）**：

```text
python3 -B -m unittest discover -s components/golden -p 'test_*v5.py'
Ran 46 tests ... OK
python3 -B ./components/golden/validate_interp_v5.py
TOTAL 710: PASS-encoding=171 PASS-execution=490 FAIL=0 SKIP-deferred=5 SKIP-scope=0 SKIP-machine=44
EXIT=0
python3 -B ./components/golden/check_golden.py
MODEL TESTS AND COUNTEREXAMPLE CHECKS PASS (repository replay is separate)
EXIT=0
python3 -B ./tools/testcases/validate_vectors.py
validate_vectors: 156/156 M1 identities covered OK (inventory sync OK; 16 data files, 710 cases; data coverage gaps: 0)
EXIT=0
python3 -B tools/spec/check_spec_changelog.py
check-spec-changelog: PASS（变更记录集中于 SimRISC-00；01–12 无附录；逆序/册头/无表格/无任务号/互锁一致）
EXIT=0
```

- **spec 锁**：本机 `python3` 为 3.10，`check_spec_readonly.py` 因缺 `tomllib` 无法启动；用等价脚本逐册重算 21 条 `sha256`，**21/21 一致**。
- **009t 审计**：新增 `sub.uo` 借位向量无 mismatch；该工具对 `ctrl-br`、`ldm.o`、`shl.*` 仍有既存偏差（与本次 B 方案无关，未处理）。
- **剩余**：L2 环境（make/工具链/`check-{rnd,minmax,fma}-probe`）仍 BLOCKED；reviewer 第 2 轮未跑；合并、本次修改与 ADR 均未提交。reviewer 第 1 轮的“`sub.uo` 待裁定”条件已解除。

## 文档口径与已知不足（2026-10-27）

用户原话：“先把文档更新一下”。

当前口径：66 条 `scope: fp`；48 项单测；仓库向量回放 730 条（173 编码通过 / 500 执行通过 / 0 失败 / 57 跳过，退出码 0）；`validate_vectors` 156/156、718 个 base 用例、0 缺口；`sub.uo` 按 ADR-0049 返回借位 0/1；`cmp` 写满 64 位。

已知不足（如实记录，未在本次文档更新中修改实现）：

- **f2i**：finite inexact 置 NX；负 Inf/负溢出饱和已修复（3156df78），有单测。仍开放：unsigned `-Inf`/±NaN 饱和到 `0xFFFFFFFF` 还是 0，无独立向量（已记录，不阻断本任务）。
- **FP 共享向量**：`tests/inst/fp` 目前只有 scaleb；fma/rnd/minmax 仍只有单测和 C 探针，差分脚本未入库。
- **门控**：已新增 `check-golden`（单测 + `tests/inst` 回放 + `check_golden` + 生成器 `--check`），纳入 `make check`（L1）。
- **注入**：`check_golden.py` 的模型注入未覆盖 `fma/rnd/minmax`。
- **审计工具**：`009t-audit.py` 对 `ctrl-br`、`ldm.o`、`shl.*` 有既存偏差（与本次 B 方案无关）。
- **范围外**：M9 标量（rev/rol/ctlz/cttz/ctpop/clmul/lr/sc）、特权/原子/fence/trap/cfx、MMU/权限/异常入口不在模型内；48 条机器层用例为 SKIP。

## 更新至 52cbcab6 / tests/inst（2026-11-02）

用户原话：“又过了一周了，请你更新一下…还需要做哪些事情能做pr？”；“迁移是我干的…按新内容更新golden，并merge，重编号adr，更新文档，给一个门控”；“完成构建”。

- **目录**：golden 保留在 `components/golden/`（用户手动迁移）；所有活动文档/脚本路径已从 `tools/golden` 更新。
- **合并**：`dc63cc00`（旧 merge）→ `8c6eb294`（迁移/B/ADR-0049）→ `a9d1850a`（合并 `52cbcab6`，249 个提交）；`tests/vectors` 迁至 `tests/inst/`。
- **新语义**：f2i finite inexact 置 NX、不再抛 `FPGap`；`ftsclb/fosclb` 第三源改为 `rdHD` signed 64 位整数指数（`rd0=0`）；验证器支持 `sequence` 按 PC 执行；新增 `tests/inst/fp/scaleb.yaml` 回放。
- **ADR**：本地 `sub.uo` 借位决策重编号为 **ADR-0049**（上游已占用 0039/0040）。
- **门控**：新增 `make check-golden`（单测 + `tests/inst` 回放 + `check_golden` + 生成器 `--check`），纳入 `make check`（L1）。
- **验证**：48 项单测 OK；回放 730 条（173/500/0/57，退出码 0）；scaleb 2 encoding + 10 execution 全过；`validate_vectors` 156/156、718 base 用例、0 缺口；`check_golden`、生成器 `--check`、spec changelog 通过。
- **未完成**：LLVM 构建在 clang 链接阶段被 OOM 杀掉（`ld terminated with signal 9`），L2 尚未跑通；reviewer 未跑；本次改动未提交/未 push。

## 最终验收（2026-11-03）

### 第 2 轮 reviewer 验收

- 初始判决 **Needs Revision**：`fp_ref.convert_to_int` 的负饱和返回未掩码负数，解释器再 `_sext` 导致二次符号扩展；`ft2it` 的 `-Inf` / 负溢出得到 `0xFFFFFFFE80000000`，正确应为 `0xFFFFFFFF80000000`。仅 +Inf 测试覆盖，负侧漏测。
- 修复：`3156df78` 对所有 `convert_to_int` 返回值统一为宽度位型（`lo & mask`），调用方只做一次符号扩展；补 `-Inf`、`0xCF000001`、端到端 `ft2it` 与 scaleb `OF|NX`/`UF|NX` 断言。
- reviewer 复验 **Accepted**：`make check-golden` exit 0（Ran 49 tests，730 回放 FAIL=0）；真实路径 `-Inf → 0xFFFFFFFF80000000` + NV；scaleb 溢出 `(0x7F800000, OF|NX=20)`、下溢 `(0, UF|NX=24)`。
- 前一轮 probe 期望 `3` 判定为 probe 笔误（`NV|DZ`）；按 IEEE 754 / contract-fp §3/§5，正确是 `OF|NX`。

### 架构师交叉复核

**Accepted**：父版本 `3156df78^` 可复现旧值 `0xFFFFFFFE80000000`，HEAD 为 `0xFFFFFFFF80000000`；修复仅限 `fp_ref.py`、`test_fp_v5.py` 与 `docs/fp-oracle-design.md` 路径；无越界。L2 独立日志 exit 0、`module checks (L2): PASS`。L1 唯一失败 `check-knowledge-refs`（78 条历史 `.work/evidence/**` 悬空，与 golden 无关）。

### 最终证据

```text
make check-golden        Ran 49 tests ... OK
                         TOTAL 730: PASS-encoding=173 PASS-execution=500
                         FAIL=0 SKIP-deferred=5 SKIP-scope=4 SKIP-machine=48
                         EXIT=0
make check-modules       module checks (L2): PASS   EXIT=0
make -k check            EXIT=2，仅 check-knowledge-refs（78 悬空，历史/环境）
validate_vectors         156/156 identities, 718 base cases, 0 gaps
```

**提交**：`8c6eb294`（迁移/B/ADR-0049）→ `a9d1850a`（合并 52cbcab6）→ `7242e137`（tests/inst、f2i NX、scaleB、sequence、check-golden）→ `b8b3c7a9`（合并 83574646）→ `057a8620`（生成器/ledger/contract cite）→ `3156df78`（f2i 负饱和修复）→ 本文档收尾提交。

**剩余边界（不阻断本任务）**：unsigned f2i `-Inf`/±NaN 的饱和值（`0xFFFFFFFF` vs 0）待裁定/补向量；fma/rnd/minmax 仍无共享 YAML；M9 标量/特权/原子/fence/MMU 不在模型内。
