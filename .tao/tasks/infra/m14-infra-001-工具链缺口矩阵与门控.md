# m14-infra-001: 工具链缺口矩阵与门控（`make check-linux-toolchain`）

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`（目标名与 Makefile 接线已由该任务声明；本任务不改 `Makefile`）
**可并行分片**：否（单一矩阵 + 单一门控；探针可并行执行但产出单份数据/报告）
**预估**：4–5 h
**状态**：已验证

## 背景

Linux 内核构建对工具链的要求比裸机测试更宽：归档/符号/剥符号工具（`llvm-ar`/`llvm-ranlib`/`llvm-strip`）、GNU C 扩展（`asm goto`）、栈保护、数据伪指令（`.quad/.long/.short/.byte`）、inline asm 约束、代码模型（`-mcmodel=kernel`）。当前安装根 `.dadao/cross-toolchain/bin` 只装 `HOST_LLVM_TOOLS`（`llvm-mc/llvm-objdump/llvm-objcopy/llvm-readobj/llvm-nm/llvm-dwarfdump/FileCheck/not/llc/clang` + 别名），**没有** `llvm-ar`/`llvm-ranlib`/`llvm-strip`（实测）；其余能力未系统测过。

M14 K0 的入口判据是「gaps 归零或有规避法 + 工具链就位」。本任务只**登记缺口与规避法**，**不修工具链**（安装根/构建树/LLVM 源码都不改）。

## 目标

1. 建 `tools/linux/toolchain_matrix.json`：逐项记录「探针 / 期望 / 实测 / K0 影响 / 规避法 / 归属任务」。
2. 建 `tools/linux/check_toolchain.py`：按矩阵**现场重跑探针**，断言「声明 == 实测」；提供 `--report` 从矩阵生成人读报告、`--inject` 自检（可达 FAIL）。
3. 产出 `docs/TestReports/M14-K0-toolchain-gaps.md`（四必备项：生成时间/数据来源/机器指纹/复现命令；无运行期绝对路径），并在 `docs/README.md` 索引补一行。
4. 在完成区给出 `check-linux-toolchain` 的 **L1 判据文本**（可机械判）；`docs/Process-07 §1.1` 的登记与 `Makefile` L1 成员接线**统一由 `m14-infra-003`** 完成（本任务不改 `Makefile`/`Process-07`）。
5. 给 `m14-linux-002` 输出**可直接消费**的工具选择：`CC/LD/AR/RANLIB/NM/OBJCOPY/OBJDUMP/STRIP` 各自的可执行来源与 fallback，不得只写「缺」。

## 矩阵行（至少覆盖；可增不可漏）

| 行 | 探针（必须指向 **DADAO target**，不得用 host x86 直测） | 判定 |
|---|---|---|
| `llvm-ar` | 安装根/构建树是否存在可执行 + `--version` | present/absent；内核 `AR` 选择 |
| `llvm-ranlib` | 同上 | present/absent；`.a` 索引 |
| `llvm-strip` | 同上 | present/absent；`STRIP`/`INSTALL` 行为 |
| `asm goto` | `clang --target=dadao -fsyntax-only` 编译带标签的 `asm goto`（内联 asm 跳到 C 标签） | 支持/不支持/错误码 |
| 栈保护 | `-fstack-protector-strong` +（若目标支持）`-mstack-protector-guard=…` 编译并检查生成物含 canary 访问 | 支持级别 |
| 数据伪指令 | 汇编 `.quad/.long/.short/.byte` 全组合，反汇编/读段核对字节与宽度 | 支持/错误 |
| inline asm 约束 | 内核常用约束（`"r"`, `"i"`, `"m"`, `"=&r"`, 内存 clobber）逐条编译 | 支持/错误码 |
| `-mcmodel=kernel` | 命令行接受性与实际 codegen（如 `.medlow/.small` 的替代） | 支持/需规避 |

- 每行必须给出**实测命令 + 原始输出摘要 + exit code**；禁止凭已知/文档填写。
- `missing` 行必须有**非空规避法**（如 `AR=<构建树 llvm-ar>`、`-mcmodel=medlow`、`-fno-stack-protector`）且写明对 K0 的影响（blocker / none）；`required` 行必须 present。
- 矩阵声明与探针结果**一一对应**；不允许「未知/未测」状态。

## 接口规范

**矩阵（JSON，字段名固定；值现场填写）**

```json
{
  "format": 1,
  "toolchain": {"target": "dadao-unknown-elf", "resolved_from": "tools/infra/paths.py"},
  "rows": [
    {"id": "llvm-ar", "required_for_k0": true, "declared": "absent",
     "probe": "<argv 形状，不含宿主绝对路径>", "measured": "absent",
     "workaround": "AR=<构建树>/llvm-ar（或 GNU ar）", "k0_impact": "none",
     "owner": "m14-linux-002"}
  ]
}
```

**门控判据（每条有可达 FAIL）**

1. 每一行 `declared == measured`；不一致 ⇒ FAIL（工具升级/降级后必须更新矩阵）。
2. 所有 `required_for_k0 == true` 的行 `measured == "present"`；否则 FAIL（K0 被阻塞）。
3. 所有 `declared == "absent"` 的行 `workaround` 非空；否则 FAIL。
4. 行集合覆盖上表；缺行/多未知行 ⇒ FAIL。
5. 报告与矩阵同源：报告由 `--report` 生成，正文数字与矩阵一致；改矩阵不重生成 ⇒ `--report --check` FAIL。
6. `--inject`：临时副本上翻转一行 `declared`、删一个 `workaround`、把 `required` 行标 `absent` ⇒ 三种各自 FAIL；还原（`cp`+md5）⇒ 回绿。

## 范围（改哪些文件）

- `tools/linux/toolchain_matrix.json`（新建）
- `tools/linux/check_toolchain.py`（新建）
- `docs/TestReports/M14-K0-toolchain-gaps.md`（新建，生成物）
- `docs/README.md`（索引一行）
- 本任务书

**不改**：`Makefile` 与 `docs/Process-07`（目标由 `m14-linux-001` 声明；L1 登记与成员接线由 `m14-infra-003`）、`manifests/`、LLVM/安装根/构建树内容、`components/`。

## 验收标准

1. `make check-linux-toolchain` rc=0，打印 `N/N 行一致`（N 现场统计）与 `gaps=K (blockers=0)`；`python3 tools/linux/check_toolchain.py --inject` rc=0（自检三例全 FAIL 后还原回绿）。
2. 八个矩阵行逐行有真实探针输出（完成区贴命令形状 + exit code；长输出留运行期日志目录）；**证明探针不是 host x86**（命令含 `--target=dadao` 或等价 target 选择，且失败/成功与 DADAO target 绑定）。
3. `llvm-ar`/`llvm-ranlib`/`llvm-strip` 的 present/absent 结论与安装根/构建树现场一致；若 absent，`workaround` 给出可执行来源与 `m14-linux-002` 的消费方式。
4. 报告 `docs/TestReports/M14-K0-toolchain-gaps.md`：四必备项齐全、无 `/tmp`/`/home`/具体 `.work` 路径；`make check-test-reports` rc=0；`docs/README.md` 索引有该文件。
5. 完成区给出可登记的 L1 判据文本（「声明==实测；required 全 present；absent 有规避法」）；`m14-infra-003` 负责在 `docs/Process-07 §1.1` 登记并接线（本任务不改 `Process-07`/`Makefile`）。
6. **不改工具链**：`git status` 无 `.dadao/**` 或 LLVM 源码改动；安装根二进制 mtime/sha 未变（现场核对）。
7. 回归：`make check` 其余目标 rc=0（新目标尚未接 L1，属预期；外部红逐条归属）。
8. 一键证据脚本（含注入）；完成区 ≤30 行、无运行期路径。

## 说明

- **为什么探针必须锁 target**：host clang 对 `asm goto`/`.quad`/`-mcmodel` 天然支持，用 host 测会得出「全绿」的假结论；所有探针必须经 target triple 或 `--target=…`，并在矩阵里记录 target。
- **为什么只登记不修**：安装根新增工具要走 `make install-host` + `HOST_LLVM_TOOLS`（跨任务、影响全仓），属独立决策；本任务给 `m14-linux-002` 可用的规避法即可。
- **报告文件名**按派单指定为 `docs/TestReports/M14-K0-toolchain-gaps.md`（英文主题）；`check-test-reports` 只校验 `<M>-<主题>.md` 形态与四项必备内容，不判语种。不得为「好看」改名或加日期。
- **`-mcmodel=kernel` 的语义**：DADAO 不一定有同名 code model；若 clang 拒绝，按实测选 `medlow`/`small`/默认，并把「内核链接地址 = 1 MiB」作为约束写进规避法（`m14-spec-001` 已冻结）。
- 参考实现只读：`.cache/refs/DADAO-0628` 的 K3 构建踩坑（`llvm-ar`/`strip`/`-O0`）只作**内容溯源，非执行必需**，不复制命令/补丁。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本的对照基线钉**派单前 commit 常量**或现场文件 md5，不得取 `HEAD`。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`/`Makefile`；如必须改，先停并登记「待裁定」。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：`make check-linux-toolchain` rc=0（`8/8 行一致, gaps=6 (blockers=0)`）；`python3 tools/linux/check_toolchain.py --inject` rc=0（6 例注入各自 FAIL、`cp`+md5 还原回绿）；`--report --check` rc=0；`make check-test-reports` rc=0；`make check` rc=2，唯一红 = `check-milestones-fresh` 4 项台账路由（本任务 A1 状态未移表 + 3 个在跑任务仍在「待开始」表），属主会话职责，本任务未改台账；其余全绿。
**修改文件**：`tools/linux/toolchain_matrix.json`（新）、`tools/linux/check_toolchain.py`（新）、`docs/TestReports/M14-K0-toolchain-gaps.md`（新，生成物）、`docs/README.md`（索引 1 行）、本任务书。
**验收结果**：
- 矩阵 8 行实测（现场 exit code）：`llvm-ar` absent(127)、`llvm-ranlib` absent(127)、`llvm-strip` absent(127)、`asm-goto` supported(0)、`stack-protector` unsupported(1)、`data-directives` unsupported(1)、`inline-asm-constraints` supported(0)、`mcmodel-kernel` unsupported(1)。
- required 2 行全 present：`asm-goto`、`inline-asm-constraints`；6 个缺口全 `workaround_measured=verified`（ar/ranlib、llvm-objcopy strip、`.dd.*` 字节比对、`-fno-stack-protector`、`-mcmodel=small` 现场重验）。
- target 绑定：能力探针全带 `--target=dadao-unknown-elf`（汇编 `-triple=`）；同源宿主 x86 clang 对栈保护/`-mcmodel=kernel` rc=0，target rc=1 ⇒ 结论由 target 决定。
- 报告四必备项齐、无运行期路径、首行快照标记；`--report --check` rc=0；`docs/README.md` 已索引。
- 未改工具链：安装根 bin 的 size/mtime 与 `llvm-mc` md5 前后一致；无 `.dadao/**`/LLVM 源码改动。
- 一键证据脚本（运行期证据目录）rc=0：含 2 例真实文件注入「注入→FAIL→`cp`+md5 还原→回绿」；反例（报告追加漂移行）rc=1，还原 md5 一致后回绿。
- L1 判据文本（交 `m14-infra-003` 登记）：`check-linux-toolchain` = ① 每行 `declared == measured == 现场实测`；② `required_for_k0` 行 measured 为 present/supported；③ 缺口态行 `workaround` 非空且 `workaround_measured=verified` 且现场重验通过；④ 行 id 集合 == 8 行覆盖表；⑤ 能力探针 probe 含 target；⑥ 报告 == `--report` 重渲染。
**新发现/坑**：
- DADAO ELF 大端、`e_machine=0xDA0`：GNU `strip` 无法识别（rc=1），GNU `ar/ranlib/nm` 可用 ⇒ `STRIP=<install-root>/bin/llvm-objcopy`。
- `llvm-ar/ranlib/strip` 在**构建树**也缺（非仅安装根）；补齐需改构建配置 + `HOST_LLVM_TOOLS`，属跨任务决策。
- `asm goto` 需 `%l0` + `jump [rb0, %l0]`（DADAO `jump` 要求基址寄存器）；`j`/`beq` 等 mnemonic 不存在。
- `.quad/.long/.short/.byte` 被 llvm-mc 拒绝（唯一数据指令集 `.dd.b08/w16/t32/o64`；clang codegen 亦只出 `.dd.*`）⇒ 手写汇编须翻译。
- 栈保护不是「开关不支持」而是后端 `unable to lower stackguard` + fatal error（rc=1）；日后要 SSP 须后端补齐。
- `-mcmodel` 仅接受 `default`/`small`/`large`（`kernel`/`medlow` 均拒）；K0 用 `small`（基址 1 MiB，REL26 ±32 MiB）。
- 报告机器指纹不得含 `git HEAD`（每次提交即漂移 ⇒ 同步门控假红）；改用工具版本 + 版本摘要 md5。`required_for_k0` 的 2 行与 `k0_impact=none` 判法是本任务**自决**。
**遗留问题**：`check-milestones-fresh` 外部红（本任务状态未移入「进行中」表 + 3 个在跑任务仍在「待开始」表；需主会话改台账）；`llvm-ar/ranlib/strip` 补齐属跨任务决策、L1 接线归 `m14-infra-003`。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `measure(rows)` 形参未用 | ✅已修 | 去掉形参，3 处调用同步 | `python3 -m py_compile` rc=0；gate rc=0 |
| F2 报告 detail 未 scrub，出现临时目录绝对路径 | ✅已修 | `measure` 内对 detail/规避法 detail 做 `scrub`+`_trim` | 报告 grep 无运行期路径；`make check-test-reports` rc=0 |
| F3 机器指纹含 `git HEAD` ⇒ 每次提交后报告同步假红 | ✅已修 | 指纹改 CPU+target+工具版本+版本摘要 md5 | `--report --check` rc=0；重生成后仍 rc=0 |
| F4 `--inject` 的 R2 用例只命中词表/R1，未触 R2 分支 | ✅已修 | 用例改为「声明+模拟实测同步为 unsupported」，首判据命中 R2 | `--inject` 输出首判据 `R2 required 行非 supported` |
| F5 `host_contrast` 死代码 / `_obj` 返回伪路径 | ✅已修 | 删死分支；`_obj` 失败返回 `None` | `--inject` rc=0；gate rc=0 |
| F6 `cmd_gate` 逐行 `[ok]` 恒真 | ✅已修 | 改为 declared vs live 真比较（不一致打 `!!`） | 负例中 `[FAIL]` 行出现；正常跑 8 行 `[ok]` |
| F7 证据脚本用管道接 `tee` 会吞退出码 | ✅已修 | 改「重定向到日志 + `cat`」；`git status` 同改 | 证据脚本 rc=0；反例 rc=1（9 项 FAIL） |
| F8 报告表头「类别」实为 declared | ✅已修 | 表头改「声明」 | 报告正文；`--report --check` rc=0 |


### 第 1 轮 reviewer 验收（2026-11-13，本人重跑；采信项：engineer 自审 F1–F8 的文字描述，其复验证据命令已由我重跑）

**重跑记录（命令 → 真实退出码）**：`make check-linux-toolchain` → rc=0，`toolchain matrix: 8/8 行一致, gaps=6 (blockers=0)` + `PASS`；`python3 tools/linux/check_toolchain.py --inject` → rc=0（R1/R3/R2/R4/R5/R6 六例 `expected rc=1 actual rc=1`、`cp`+md5 还原回绿、真实矩阵 md5 未变）；`bash .work/evidence/m14-infra-001/run.sh` → rc=0（31 PASS / 0 FAIL）；`make check-test-reports` → rc=0（9 report(s), 4 snapshot(s)）；`make check` → rc=2、249 PASS、唯一红 = `check-milestones-fresh`：m13 台账 1 项（`m13-testcases-016`），`--file milestones-m14.md` rc=1（4 项 = A1 `m14-infra-001` + 3×R1），而**主工作树** m13/m14 两台账 `--file` 均 rc=0 PASS ⇒ 红是任务 worktree 台账基线落后，非本任务缺陷。

**独立探针（不采信矩阵 8 行，现场 rc）**：① `llvm-ar/ranlib/strip` 在 `.dadao/cross-toolchain/bin` 与 `.work/build/llvm/bin` 六处全 ABSENT（构建树只有源码目录 `tools/llvm-ar`、无 bin 产物）；② `-fstack-protector-strong` target rc=1 `error: unable to lower stackguard`，宿主 clang rc=0；③ `.quad`/`.long` 经 `llvm-mc -triple=dadao-unknown-elf` rc=1（`unsupported directive`），`.dd.o64/.dd.b08` rc=0 且段字节 `1122334455667788aa` == 期望；④ `-mcmodel=kernel` rc=1（`unsupported code model`）、`-mcmodel=small` rc=0；⑤ `asm goto`（自写源）`-fsyntax-only` rc=0、`-O1 -S` rc=0、标签降级 1 处；另自写 inline asm 约束 r/i/m/=&r/memory 5 例 rc=0。规避法复验：`ar rcs`/`ar t`/`ranlib` rc=0、`llvm-objcopy --strip-all` rc=0（800→312，与报告同值）、GNU `strip` rc=1；ELF64 大端 `Machine da0`。

**同源核验（报告非手写）**：改矩阵 workaround 文本（不重生成）→ `--report --check` rc=1 `[FAIL] 报告与矩阵不同源`；`--report` rc=0 后再查 rc=0 且报告含改动标记；用原始矩阵重生成的报告与入库报告**除「生成时间/机器指纹」两行外 diff 为空**。

**独立注入 1 路（`cp`+md5，禁 git 还原）**：`llvm-ar declared: absent→present` → `make check-linux-toolchain` rc=2、脚本 rc=1 `[FAIL] R1 声明!=实测 …现场='absent' (rc=127)`；还原后矩阵 md5 `39ea51b02484…`、报告 md5 `888bd7e1f53b…` 均 match → gate rc=0、`--report --check` rc=0、`--inject` rc=0。

**约束核验**：`master..HEAD` 仅 5 个文件（矩阵 / 脚本 / 报告 / docs README / 任务书），无 `Makefile`、`docs/Process-07`、`manifests/`、`.dadao/**`、LLVM 源码改动；审查前后 `git status --porcelain -uall` 快照逐行一致、`git diff HEAD` 为空；安装根 clang/llvm-mc mtime 14:25–14:27（早于任务 19:58–20:02，未重建）；完成区 21 行 ≤30 且无运行期路径；报告四必备项齐、grep `/tmp|/home|\.work` 无命中；完成区数字（8/8、gaps=6、6 例注入、800→312、rc=2）与我现场值逐条一致。

**判定：Accepted**（验收命令块在本人重跑下全部通过、约束无违反、未改契约/测试/判据；本判定为「工程师达标」证据，architect 仍终审）。

**findings（文档级，不阻断，architect 收尾时改）**：F1 完成区「唯一红 = 4 项台账路由」与单次 `make check` 实际输出不完全一致（make 停在 m13 台账 1 项；「4 项」是 `--file m14` 的结果，且主工作树两台账已 PASS）；F2 缺失工具行的 `exit 127` 是脚本约定值（文件不存在即返回、未真正执行），报告宜注明；F3 报告结论行 `gaps=N (blockers=0)` 中 `blockers=0` 为字面量（gaps 为算出值；blockers>0 时 `--report` 被 validate 拦下不写，实际无假结论）；F4 已提交脚本默认临时目录写死任务 ID（可被 `DADAO_TMP` 覆盖），建议改通用名。

**未决（供 architect/用户裁定）**：`llvm-ar/llvm-ranlib/llvm-strip` 缺失——安装根与构建树均缺（我独立 `find` 确认），规避法（GNU ar/ranlib + `llvm-objcopy` strip）现场验证可用、K0 无阻塞；补齐须改 LLVM 构建配置 + `HOST_LLVM_TOOLS` + `make install-host`（动安装根、影响全仓、须重建），超出本任务「不修工具链」范围 ⇒ **建议另立任务**（独立 infra 任务或作 `m14-infra-003` 前置），由用户裁定；矩阵 `owner=m14-linux-002` 只标规避消费方，不替代该决策。
