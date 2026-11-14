# m13-integ-003: 整数与访存三平台差分（inst 全量非 cfx）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-integ-001`
**可并行分片**：按套件 / 按指令族（实现标「待定」，派单前按节点实况定）
**状态**：已验证
> **派单授权（用户 2026-11-14）**：`m13-chipyard-002` 合入后由主会话**直接连派本件**，不再逐件确认。


## 背景

M13 除 FP 外还需覆盖整数与访存（用户：「含指令语义，尤其是浮点」）。

## 目标

0. **第一阶段（用户 2026-11-09）**：先**定义每条指令的完整且准确的语义**（尤其浮点：舍入方向、异常标志、NaN 传播、边界值），再**重新生成 `tests/inst` 的测试程序**，重点是各种边界。

1. **三平台差分**：`tests/inst` 中全部**非 cfx** 用例（整数/访存/控制流/位操作/原子/杂项），在 qemu / gem5 FS / chipyard 上逐例比对。
2. **差异归因**：按「spec 歧义 / 实现缺陷 / 测试资产」分类，逐条列名。
3. **不重复 FP**：FP 归 `m13-integ-002`。

## 验收标准

1. inst 全量非 cfx 用例三平台覆盖，计数现场统计
2. 差异逐条归因，无未归因项
3. 报告落 `.tao/knowledge/refs/m13-003-int-diff.{json,md}`
4. 门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

FP（`m13-integ-002`）、riscv-tests（`m13-integ-004`）

## 说明

- M13 主体任务**依赖 M12 的核实现完成**（chipyard 可用）；在此之前只做 `m13-testcases-001`–`003` 的长尾计时。
- 差分产物归属以 `m13-integ-001` 的结论为准。

## 硬约束

1. 临时目录 `/tmp/opencode/m13-integ-003/`；禁仓库内临时文件。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存运行期日志目录；命令在 worktree 根内、相对路径。
6. 单任务单机；节点操作后 `make sync-node-repo`。
7. 不要删除其它任务的临时目录。

> **用户裁定（2026-11-11）**：本任务**暂不进行**（等 M12 核完成 / 用户另行指示后再评估）。


## 审阅记录

### 第 1 轮 engineer 自审

范围：`tools/testcases/parity/int_diff.py`（新增 1 文件，逐行）+ 报告两份 + 证据脚本五段。判决：**Accepted**（finding 全修）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 节点运行树只铺 `tests/inst`，`.S` 宏链还 `.include tests/shared/asm/*.inc` ⇒ 首轮 4 节点 0/157 | ✅已修 | 铺树补 `tests/shared/` | 重跑 157+157+158+157=629/629 |
| F2 独立 oracle 点数正则 `[A-Z]` 漏 `__CHECK_*`（首字母 `_`） | ✅已修 | 改 `[A-Z_]` | oracle 194/629/629 通过 |
| F3 `TEST_FAULT_RASUF_MEM` 无故障名参数（宏体固定 RASUF）⇒ oracle 误判 1 例 | ✅已修 | 按宏体 `__FAULT_GUARD … RASUF` 取值 | `ret_riii_ra#22` 转绿 |
| F4 `--attribution` 键用带 `.S` 的文件名，与生成器 `Path.stem` 不符 ⇒ I3 红 | ✅已修 | 键改 stem | I3/I3b 均按预期 |
| F5 报告 §5 列了范围外章节（SimRISC-07/11） | ✅已修 | 只列 scope families 用到的章节 | §5 14 章 = 11 族 + 契约 |
| F6 非 id 载体靠硬编码常量 | ✅已修 | 由 `entry is None` 派生成 `coverage.non_id` | 194 = 193 + 1 |
| F7 `EXTERNAL_ATTRIBUTIONS` 跨 build 泄漏（同进程二次调用不确定） | ✅已修 | 每次 build 先 clear | 自检/I2(无表) 仍 rc=1 |
| F8 报告断言硬写 `diff==0`（不可达 FAIL） | ✅已修 | 改由 `images − agree` 派生 | I2 注入下派生值 = 1 |

判据自评：证据脚本 24 项检查（自检 10 类反例 / 报告确定性 / 独立 oracle / E2E 灵敏度 / 6 门控 / I1–I4 注入）全 PASS；注入路径均可达 FAIL（I2/I4 与 E2E 实测非零，I3 反向证明归因表逐条生效）。

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑；命令均在本任务 worktree、相对路径）

**重跑（我方真实输出 / 退出码）**
- 证据脚本全量 `bash 运行期证据目录/run.sh`：第 1 次 `22 PASS + BLOCKED E2E sensitivity (foreign writer active)`（外部 `install-host` 写者占位、E2E rc=75）、EXIT=0；**有据重试 1 次**后第 2 次 **`24 PASS / 0 FAIL / 0 BLOCKED`、EXIT=0**（E2E 实测 `rc {'chipyard':4,'qemu':4,'gem5':4}` ⇒ AGREE_FAIL at point 4，非平台分裂）；我方注入后第 3 次 **EXIT=1**；还原后第 4 次 **24 PASS、EXIT=0**。
- 分母独立重算（自写解析、不 import 其代码）：`.S` **265** / `scope:fp` **66**（07 册 52 + 01 散 8 + 02 散 5 + 03 散 1）/ 册 `11-cfx` **5** ⇒ **194 载体 = 193 opcode id + `undi_reserved`**；链例镜像 **193**、故障 **436**、合计 **629** —— 与报告逐项相等。
- `int_diff.py --check` md/json 均 **rc=0**；两次重生成 md5 相同（json `786da15b…`、md `0ffc1d8a…`）且与入库件逐字节一致；两份报告 grep `\.work/|/tmp/|/home/|/mnt/|20xx-xx-xx` **0 命中**（无运行期路径、无生成时刻）。
- 三平台抽检 **11 个链例**（册 01/02/03/04/05/06/12，`--chain-only` 本机实跑）：**11/11 PASS**、rc 全 0、三平台字节数相等；**报告 `per_image` 的 rc/md5 与我方实测逐条相同**（该次 gem5 已是 `a1dd0e4a…` 仍复现）。故障码对表 `spec/Machine-v5 §7.1`（Tiny `0xF0|idx`）⇒ `0xF1/0xF2/0xF8/0xF9/0xFA/0xFB/0xFC/0xFD` 与 oracle 表逐项一致。

**注入（判据不恒真 / 归因可达，一律 `cp`+md5）**
- 我方注入 A：翻转运行期证据中 `br.eq_rrii_rd` 链例 qemu 结果流首字节（`ca61fe38…`→`d328f120…`）⇒ 重跑 **EXIT=1**：`report json matches regeneration` FAIL + oracle 4 FAIL（`platform byte streams differ`、`agree_pass 628 != 629`、`diff 0 != 1`、`agree_fail mismatch`）；`cp` 还原 md5 相等、备份删净 ⇒ 第 4 次全绿。
- 我方注入 B（临时向量树、换受害者）：`tests/inst/06-control-flow/br.eq_rrii_rd.S` 点 1 期望 `0→1` ⇒ 三平台 **rc=1/1/1、ok=False**、runner rc=1，`fp.classify` = **AGREE_FAIL**；仓库文件 md5 `75fb396c…` 前后相同，重跑 **rc=0、0/0/0 回绿**。
- 归因路径（我方独立、用 `ics180` 分片而非其 `ics150`）：单平台 rc 0→9 ⇒ **diff=1 / unattributed=1 / rc=1**（`DIFF without an attribution entry`）；配合法表 ⇒ **rc=0、attributed=1、source=external**；`owner=nonsense` ⇒ **rc=2**（坏参数走 setup 码，判据合理）。代码侧 `ATTRIBUTIONS={}` 且 `EXTERNAL_ATTRIBUTIONS` 每次 `build` 先 `clear` ⇒ 未归因必红，路径可达。
- 报告级反例（三方同点红）：`agree_fail=1 / diff=0 / rc=0` —— 生成器不因此非零（与已验收的 `fp_diff` 同口径），但 evidence oracle 的 `images−agree == diff` 会红（注入 A 实测），且 §2 明列「三方一致非通过」，不隐藏。

**门控（我方重跑）**
- `check-inst-asm` **901/901、265 id、rc=0**；`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue` 均 **rc=0**；`check-knowledge-refs` **rc=2、红点 1**。
- 该红点 = `.tao/tasks/chipyard/m13-chipyard-002-sc保留粒度严格化.md:78`，在基线 `f4b2de26` 即存在；`git diff --name-only f4b2de26..HEAD` 仅本任务 5 文件、门控日志 grep 本任务 0 命中 ⇒ **本任务未新增红点**（master 已由 `9afbced5` 修掉，本分支基线早于它）。

**约束核验**：未改主工作树、未提交 git、未跑 `install-host`/`check-modules`/`build-*`、未动节点仓库；注入还原只用 `cp`+md5（无 checkout/restore/stash）；前后 `git status -uall` 均空、5 个已提交文件 md5 与起始快照逐一相同；完成区 **23 行 ≤30**、无运行期路径；「修改文件」5 项与 `git diff --name-only f4b2de26..HEAD` 完全一致；节点同步日志 `sync_node_artifacts: PASS / EXIT=0`。

**二进制身份表态**：报告三件 md5 与我方实测——qemu 构建树 `725c5da7…` ✓、chipyard `079ae015…` ✓、gem5 报告 `6e436d1b…`（本机已被 `build-gem5` 换成 `a1dd0e4a…`，完成区⑤已如实披露），我方抽检用 `a1dd0e4a…` 仍逐条复现同 md5 结果 ⇒ 引擎漂移未改变本轮结论；跑前 `sync_node_artifacts` 把三件同步到各节点且 verify OK，与报告 engines 一致。「用构建树而非安装根」披露属实（我方开审实测安装根 = `b34ed7f9…` ≠ 构建树，审中一次外部 `install-host` 已同步成 `725c5da7…`）。**对本任务结论无影响**：当前向量面不含保留粒度探针（`12-misc` 载体头把「保留粒度平台分歧」列为 GAP 不写用例；我方对 24 个 `lr/sc` 载体做地址流分析，「保留后同字 store 再 `sc`」= 0），`m13-qemu-015` 的差异只涉 FP（本任务范围外），且旧安装根下 `check-inst-asm` 亦 901/901。

**037 缺口与合并建议**：`m13-testcases-037` 现为 **待开始**，其 `sc` 粒度向量不在本轮载体面、报告 `known_items` 已申报「落地后需重生成」⇒ **不阻断本件**；建议 **先合本件**，037 落地后另派一件机械重生成（重跑 `int_diff.py` + `--check`），两者不互相阻塞。

**发现（不阻断）**：F1 `int_diff.py` 文档头称复用 `run_parity.STATUSES`，实际未 import（状态由 rc 硬写 PASS/FAIL）——文档级；F2 链例 `AGREE_PASS` 只读 runner 的 `bytes` 声明，字节级三方相等由 evidence oracle 把守（注入 A 实测会红）；F3 报告未记输入 commit，037 落地后只能靠重跑 `--check` 发现陈旧。

**判决：Accepted** —— 分母 194/629、三平台 629/629、差异 0 经我方独立重算 + 11 例三平台实测 + 报告逐字节复现成立；归因/注入路径可达；门控未新增红点；硬约束全守住。

## 完成区

**测试结果**：三平台差分 **629/629 镜像三方一致通过**（链例 193 + 故障例 436）；平台差异 **0**、三方一致非通过 **0**、spec 歧义 **0**、覆盖/索引缺口 **0**。分母现场统计：`.S` 载体 265 → 排除 `scope: fp` 66、册 `11-cfx` 5 ⇒ **194 载体**（193 opcode id + 非 id `undi_reserved`）/ **629 镜像**；三平台完成数 629/629/629（qemu / gem5 / chipyard），未跑 id 0。

**修改文件**：`tools/testcases/parity/int_diff.py`（新增）、`tools/testcases/parity/README.md`（+31 行）、`.tao/knowledge/refs/m13-003-int-diff.json`、`.tao/knowledge/refs/m13-003-int-diff.md`、本任务书。

**验收结果**：
1. 分片：4 节点按镜像数分片 **157/157/158/157**，`--jobs 38`（40 核 − 2）；单节点墙钟约 **2 min**（含建镜像），本次含一次 staging 修复重跑、四节点合计约 7 min；跑前登记三件二进制 md5（qemu 构建树 `725c5da7…`、gem5 `6e436d1b…`、chipyard `079ae015…`）。
2. 逐例证据：报告 JSON 的 `results.per_image` 629 条含三平台 `exit`/字节数/结果流 md5；独立 oracle（不 import 生成器）从 `.S` 与原始 `.out` 重算 194/629/629，并回读 84 个链例记录（大端）与内联期望逐点相等。
3. 报告 `--check` rc=0（md 与 json 均可从入库输入逐字节重建；无运行期路径）。
4. 证据脚本（运行期证据目录 `run.sh`，默认全量 / `--inject` 仅注入）**rc=0、24 项全 PASS**；注入 4 路 + E2E 灵敏度 1 路，全部 `cp`+md5 还原。
5. 门控：`check-inst-asm`（901/901，265 id）、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue` **均 rc=0**；`check-knowledge-refs` **rc≠0 但红点 100% 属基线他册**（`m13-chipyard-002` 审阅记录里一处具体 `.work/**`），本任务新增文件 0 处，见「遗留问题」。
6. 状态 `待验收`；未改台账（只新增 `refs/m13-003-int-diff.*`）。

**新发现/坑**：① 节点复用运行树必须同时铺 `tests/shared/asm/*.inc`（宏链二级 include），只铺 `tests/inst` 会 0/157；② **安装根 qemu 仍是 `m13-qemu-014` 之前版本**（`b34ed7f…`），差分必须显式 `--qemu` 指构建树 `725c5da7…`（否则 sc 粒度例会被旧二进制误判）；③ DADAO 记录值是大端（`DADAO-21` §端序、`Machine-v5 §7.1` semihosting 大端），校验记录内容必须按 BE 解码；④ 链例的语义 oracle 在 guest 内（`__CHECK_*` 不符即 `SYS_EXIT(pt)`），故「三平台 rc=0」等价于「三平台都满足内联期望」；⑤ 跑批后共享 gem5 被另一任务 `build-gem5` 替换（`6e436d1b…` → `a1dd0e4a…`）——报告身份是**实际执行的冻结 md5**，当前树重跑会换引擎（`ISS-373` 同类），比对前先核 md5。

**遗留问题**：① 安装根未同步 qemu（`install-host` 属禁跑动作）——`m13-testcases-037` 的 sc 粒度正式向量会撞旧安装根，需授权窗口 `install-host`；② `check-knowledge-refs` 基线红归属他册（不代改，建议主会话在 002 收尾或 follow-up 修掉那行）；③ 037 正式向量未含在本轮向量面，补入后需重生成报告（报告 §4 已标注）；④ 无实现缺陷可登记；建议 issue（流程/卫生，**非**实现缺陷）：
```yaml
- id: ISS-NNN
  scope: [infra, testcases]
  status: open
  title: "【P3】`check-knowledge-refs` 在基线红：`m13-chipyard-002` 审阅记录引用具体 `.work/evidence/**` 路径，L1 门控对所有后续任务恒红。建议：把该行改成「运行期证据目录」措辞（不改结论），或在 002 收尾时一并修正。"
```
