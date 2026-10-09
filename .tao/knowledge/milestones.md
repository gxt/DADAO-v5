# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..5>/m<i>-retrospective.md`。

## 任务流水（仅当前里程碑 M6）

| 任务 | 状态 | 开始 | 结束 | 说明 |
| --- | --- | --- | --- | --- |
| `INTEG-023k` | 已验证 | — | — | M6 启动与分解（`/plan` 通过；23 份任务书已建） |
| `INFRA-050t` | 已验证 | 10-08 23:49 | 10-09 07:09 | LLVM 一次构建（`DADAO;X86`）+ 双落点；曾中断，半成品已保命续用；reviewer Accepted |
| `SPEC-122t` | 已验证 | 10-08 23:54 | 10-08 23:57 | M6 ADR 决策落地（`ADR-0018 §C7 D4` 四形态修订 + `ADR-0021`/`0022` 新建；用户逐条确认；reviewer Accepted） |
| `INTEG-024t` | 已验证 | 10-09 00:00 | 10-09 00:05 | issues 台账按性质分流（移出 15 = 规划① 7 + 阻塞/待裁定②③ 8；保留 24 真 issue）；reviewer Accepted |
| `SPEC-123t` | 已验证 | 10-09 07:21 | 10-09 07:53 | reloc 正文（`REL12`(rb0/PC 相对 `S+A−P`)/`ABS12`(rb1–rb63 `S+A`)、`NUM`=6 + `ABS48` 数据 8B）+ `Toolchain-01 §6.1` `set.fo` 口径 + 锁同步；reviewer Accepted |
| `SPEC-124t` | 已验证 | 10-09 08:17 | 10-09 08:22 | 调用约定契约收口（`contract-abi §6` 三 `[OPEN]` 消解）+ 用户授权改册（`DADAO-21 §返回值` 返回寄存器 `rd31→rd8/rb8/rf8`、声明序递增、每 bank K=8、超者 sret 经 rb16）+ 锁同步；reviewer Accepted |
| `SPEC-126t` | 已验证 | 10-09 08:37 | 10-09 08:48 | 系统调用/半托管返回寄存器 `rd31 → rd8`（`DADAO-21 §系统调用规范`/`DADAO-22` SBI 返回表/`DADAO-23`/`Machine-01 §5.2·5.4`）+ `contract-see/semihosting/abi` 同步 + 锁同步；**入参 `rd15`/参数区不动**；reviewer Accepted |
| `QEMU-052t` | 进行中 | 10-09 08:54 | — | 改走上游 `load_elf()`（钉子②），取消自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈降为验证项；RAM@0 仍 16 MiB |
| `SPEC-127t` | 待开始 | — | — | 聚合传参/HFA/HPA 约定收口（**用户 2026-10-09 裁定 B：全部聚合槽位上限 `4→8`〔64 字节〕，`>64 B ⇒ 间接指针`** + 补 `spec/DADAO-21 §传参 §聚合类型参数` + 锁同步 + `contract-abi`/`contracts/abi.yaml` 升 M6 口径）；**不含实现**（整数聚合 → `LLVM-062t`，HFA/RF → `LLVM-066t`） |

> （`INTEG-024t` 时间取自制品 mtime：开始 = `.work/INTEG-024t` 创建 00:00；结束 = reviewer Accepted 00:05。）

> （`SPEC-123t` 时间取自制品 mtime：开始 = `manifests/spec-readonly.lock.toml` 修改 **07:21**（磁盘上最早的 SPEC-123t 专属落盘）；结束 = 任务书末次写入 **07:53**（reviewer Accepted 落盘）。）

> （`SPEC-124t`/`SPEC-126t` 开始/结束取自任务书与台账落盘 mtime；`QEMU-052t` 开始 = **08:54**，取自 opencode 日志首个 `QEMU-052t` 相关进程时间戳。）

> 开始/结束由**主会话**在 `/dispatch`／`/complete` 时填写（格式 **`MM-DD hh:mm`**，不带年份）；只填**可考证**时间，**禁编造**。

## 当前进度
- **历史瑕疵登记**：提交 `815d854` 的**内容 = `SPEC-122t`**（`.tao/adr/adr-0018/0021/0022` + `SPEC-122t` 任务书），但**提交消息误写为 `INFRA-050t: …`**（squash 时 `fixup` 冲突触发 `GIT_EDITOR`，编辑脚本**无条件覆写**了合并消息）；**内容与 squash 前逐字节一致**（`git diff backup/pre-push-squash HEAD` = 0 行，已实测）。**用户 2026-10-09 已批准「修正（force-push）」**（只改消息、不动内容）；因**历史改写须独占工作树**（后台任务在写同一工作树时不可执行），**待工作树干净后执行**：`rebase -i` 停该提交 → `commit --amend`（**只对该条**设消息）→ `--continue` → 两级校验（对 `backup/pre-push-squash` 逐字节 0 行 + 对旧 `origin/master` 内容 diff 0 行）→ `push --force-with-lease`。备份分支：`backup/pre-push-squash`、`backup/before-msgfix`。
- **里程碑**：M6（`INTEG-023k`「M6 启动与分解」）
- **规划中**：
  - **M6 主题与范围（已裁定，2026-10-08；见 `INTEG-023k`）**：整数**完整调用约定** + **12 条 LLVM 欠账收口** + **ELF 加载**（改走 `load_elf()`，钉子②）+ **clang target**（仅 freestanding，钉子①）+ **Embench 接入**（钉子③）+ lit 量产 + `lli` 值级对拍；**不含** libc/OS/syscall、golden model、fuzz（后置 M7）；`ISS-003`（LR-SC）**M6 显式排除**
  - **M6 任务书已建（2026-10-08）**：**17 `t` + 6 `m` = 23 份**（`INTEG-023k` `/plan` 通过后），落 `.tao/tasks/{infra,spec,llvm,qemu,testcases,integ}/`；编号 `INFRA-050t…052m`、`SPEC-122t…125m`、`LLVM-062t…067m`、`QEMU-052t…054m`（QEMU 顺延两位以消跨模块重号）、`TESTCASES-036t…040m`、`INTEG-025t/026m`；Wave 串行见 `INTEG-023k §C/§D`
  - **M6 任务书追加（2026-10-09，用户裁定「统一为 `rd8`」；**不立 ADR**）**：新增 **3 份 `t`** ⇒ **20 `t` + 6 `m` = 26 份**——`SPEC-126t`（系统调用/半托管返回寄存器 `rd31 → rd8`，spec+contracts+锁）、`QEMU-055t`（半托管返回 `rd8` 实现 + 探针重派生）、`TESTCASES-041t`（向量/期望值重派生；**域A 函数返回**〔`SPEC-124t`〕/ **域B 半托管返回**〔`SPEC-126t`〕**分别验收**）；Wave 同步见 `INTEG-023k §C/§D`
  - **M6 任务书追加（2026-10-09，聚合槽位上限 8 立项；**不立 ADR**）**：新增 **1 份 `t`** ⇒ **21 `t` + 6 `m` = 27 份**——`SPEC-127t`（**用户裁定 B：全部聚合（通用/HFA/HPA）槽位上限 `4→8`〔64 字节〕，`>64 B ⇒ 间接指针`**；补 `spec/DADAO-21 §传参 §聚合类型参数` + 锁同步 + `contract-abi.md`（聚合传参/HFA/HPA 升 M6 口径）+ `contracts/abi.yaml` 派生投影；**不含实现**，归 `LLVM-062t`〔整数聚合〕/`LLVM-066t`〔HFA/RF〕）；Wave 同步见 `INTEG-023k §C/§D`
  - **Embench 接入（M6 待办）**：① 建 **ADR**（记录 Embench 上游选择 + 精确 commit）⇒ 翻 `manifests/components.lock.toml` 的 `enabled = true`；② 建 `components/embench-iot/{patches/**,series,changelog.md}`（board shim 3 函数、`md5sum` 大端适配、最小运行时）；③ 工作树由既有 `make fetch` 机制生成到 `.work/source/embench-iot`
  - **`lessons.md` 瘦身**：下次里程碑归档时按新口径（新增条目 ≤3 行 + 指针，细节进 `.work/log/`；**不追溯重写**）瘦身（**行数/字头数现场统计、不写死**）
  - **`issues.yaml` 移入**（规划①，2026-10-08 `INTEG-024t`；原 `scope` 原样括注）：
    - `ISS-003`（原 `[M6]`）：**LR-SC 原子**（`SimRISC-12` `lr_*`/`sc_*`，ISA 扩展整体 deferred）—— ① 未开始的能力（`SimRISC-12` 整体 deferred；M6 显式排除，待后续 ISA 里程碑重定）
    - `ISS-005`（原 `[M6]`）：**完整调用约定未交付部分**（变参 / 聚合传参返回 / 多返回值 / `sret` / 间接调用）—— ① 里程碑待办（M6 主题「完整调用约定（整数）」）
    - `ISS-006`（原 `[M6]`）：**ABI 5 项 `[OPEN]`**（rd1/rb3/rb4 callee-saved、窄返回值扩展、多返回值、red zone、帧指针省略）—— ① 里程碑待办（`contract-abi.md §6`）
    - `ISS-110`（原 `[llvm, M6]`）：**`cfxld`/`cfxst`（`SimRISC-12`）+ `crii` 格式 + `SPEC-075t` 别名表 uart2..30 覆盖缺口**（MC 未实现）—— ① 里程碑待办（`INTEG-022t` 边界拆分余项）
    - `ISS-165`（原 `[testcases, qemu, integ, M6]`）：**C1 step2（RAM@0 收口）**——旧向量/harness/crt0/e2e 迁 0 + 删旧 RAM 段 + 收紧 `check-interface` 断言 —— ① 里程碑待办（`QEMU-049t` 遗留）
    - `ISS-168`（原 `[qemu, integ, spec, M6]`）：**「`-bios` + ELF」组合加载 / ELF loader 扩 `dadao_load_regions[]` + RAM@0 / 组合加载 ADR** —— ① 里程碑待办（用户 2026-10-08 裁定，`INTEG-019k §第 8 轮`）
    - `ISS-169`（原 `[qemu, testcases, M6]`）：**6 个 M1/M2 探针（006t/008t/009t/010t/012t/013t）退出通道 `exit-port` → `SYS_EXIT`** —— ① 里程碑待办（归 `QEMU-053t`；`TESTCASES-034t` 披露例外）
- **阻塞与待裁定**：8 项归属存疑（`ISS-019/026/047/074/081/163/164/167`；其中 `ISS-163`/`ISS-167` 涉改上游只读册，**须用户授权**）；M6 主题**已裁定**（2026-10-08，见 `INTEG-023k`）
  - **`issues.yaml` 移入**（阻塞②/待裁定③，2026-10-08 `INTEG-024t`；原 `scope` 原样括注；**待用户裁定**）：
    - `ISS-019`（原 `[golden, M5]`）：结果级 / **FP 独立 oracle**（golden model）—— ③ 归属未定（M6 主题未显式覆盖 golden）—— **待用户裁定**；选项 A 归 M6「欠账收口」/ B 另立 golden 专用里程碑（`GOLDEN-*`）/ C 保留待规划
    - `ISS-026`（原 `[testcases, M5]`）：encoding `imm` **语义守卫依赖 golden** —— ③ 归属未定（同 `ISS-019`）—— **待用户裁定**；选项 A 归 M6 / B 另立 golden 里程碑 / C 保留待规划
    - `ISS-047`（原 `[llvm, M5]`）：`llvm-objdump -d` 需显式 `--triple`（`e_machine` 未映射到 dadao）—— ③ 归属存疑（④ 已实现物缺陷 抑或 ① LLVM 工具待办）—— **待用户裁定**；选项 A 归 M6「欠账收口」/ B 判为真 issue 保留 `issues.yaml` / C 保留待规划
    - `ISS-074`（原 `[testcases, M5]`）：`cs.*` 条件赋值 **overlap 语义（C-27）**未指定（aliasing 为 codegen 依赖）—— ③ 归属未定（FP/条件赋值相邻）—— **待用户裁定**；选项 A 归 M6 / B 随 FP 一并（M7+）/ C 保留待规划
    - `ISS-081`（原 `[spec, golden, testcases, llvm, qemu, integ, M5]`）：**FP 后续衔接点**（FP 独立 oracle / harness RF 寄存器类 / FP 向量 / 完整 FP E2E）—— ③ 归属未定（FP 不在 M6 显式范围）—— **待用户裁定**；选项 A 归 M6 / B 归 M7+（FP 专用）/ C 保留待规划
    - `ISS-163`（原 `[spec, M5]`）：`Toolchain-01 §5/§11/§13` **旧口径与 `contracts/opcodes.yaml` 不符** —— ②③ 须**用户授权**方可收口上游只读册（用户 2026-10-08 已裁定「暂登记遗留」）—— **待用户裁定**；选项 A 另立 spec 任务（授权 + 锁 `sha256` 同步）/ B 归 M6「欠账收口」/ C 继续暂登记
    - `ISS-164`（原 `[qemu, M5]`）：cfx mask（inner/global）与 `excp_cause_mask` **屏蔽路径当前不可观测**（monitor cause 全不可屏蔽）—— ② 须后续实现带可屏蔽 cause 的 cfx 后补验 —— **待用户裁定**；选项 A 归 M6 / B 保留跟踪（待可屏蔽 cause 的 cfx 里程碑）
    - `ISS-167`（原 `[spec, qemu, M5]`）：`DADAO-12 §5` 异常退出流程 **prose 与伪代码张力**（判据：伪代码为权威）—— ②③ 须**用户授权**方可收口上游只读册 —— **待用户裁定**；选项 A 另立 spec 任务（授权 + 锁同步）/ B 归 M6 / C 保留
