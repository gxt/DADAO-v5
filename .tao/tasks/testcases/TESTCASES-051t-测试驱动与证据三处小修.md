# TESTCASES-051t: 测试驱动与证据三处小修（`lencod` 缺目录 / 两个证据脚本 stale）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`LLVM-105t`（`ISS-276` 登记源：`lencod` 现场）、`QEMU-063t`（同一现场：手工补 `Output/` 后与参考逐行一致）、`TESTCASES-048t`（`lencod` 用例载体与计数面）、`LLVM-101t`（`ISS-272` 证据脚本源）、`TESTCASES-047t`（`ISS-274` 证据脚本源）、`TESTCASES-050t`（驱动最近改动，避免冲突）、`INFRA-093t`（`--json-out` / `--work-dir` 新规矩）
**状态**：待开始

> **编号（现场取号，2026-10-19）**：`testcases` 现存最大 = `TESTCASES-050t` ⇒ 取 **`051`**（`grep -rn 'TESTCASES-051' .tao/` 0 命中）。

## 执行环境
**执行环境**：本地

## 问题根源

三处均为**测试驱动 / 证据脚本**问题，不是被测程序或后端缺陷；**不改语料、不改期望值、不放宽判据**。

### ① `ISS-276`：`lencod` 缺 `Output/` ⇒ 被误判 `fail`（真 bug，本册主修）

- 现场：`llvm-test-suite` 的 `MultiSource/Applications/JM/lencod` 运行失败、产物缺失，驱动记 `fail`（`unclassified failure`）。
- 根因：程序按 `-d data/encoder_small.cfg` 读配置，配置内声明输出路径 `ReconFile = "Output/test_rec.yuv"` / `OutputFile = "Output/test.264"`（`.work/source/llvm-test-suite/MultiSource/Applications/JM/lencod/data/encoder_small.cfg:18-19`）；而 `tools/testcases/run_llvm_ts_user.py:1547-1563` 只为 **`RUN_OPTIONS` 中带 `/` 的 token** 建父目录（注释已举 `JM/ldecod` 的 `Output/test_dec.yuv`）⇒ 配置文件里的输出路径不在扫描面，run 目录无 `Output/` ⇒ 写文件失败（guest exit **244**），`fpcmp` 看到的只是截断输出。
- 依据：上游 `RunSafely` 的 `WORKDIR %S` 口径 —— 程序在**源目录副本**下运行、所需输出目录须**预先存在**；`QEMU-063t` 现场手工 `mkdir -p <run-dir>/Output` 后同一命令 **rc=0**，产物与参考**逐行一致**（`diff` 空）。
- 修法：在每例 run 目录准备阶段**按 `cid` 预建目录**（推荐最小表，如 `CASE_PREPARE_DIRS = {"MultiSource/Applications/JM/lencod": ["Output"]}`）；**禁止**用「放宽 `fpcmp`/改期望/改分类」掩盖。若实现通用配置文件解析，须限定解析面（只认该例配置文件里已声明的相对输出路径），并在完成区说明取舍。

### ② `ISS-272`：`LLVM-101t` 证据脚本 `asm-semctl-vaarg-direct` 检查方法错

- 现场：`.work/evidence/LLVM-101t/run.sh:92-108` 以汇编块内 `grep -c 'rd2rb {rb4}, {rd5}'` 判「`va_arg` 是否间接解引用」；该模式实为后端「地址 → 指针寄存器」的正常取址转换（`load` 需要 RB 寄存器），**修后仍会出现** ⇒ 把正确代码判成 `FAIL`。
- 正确判据（reviewer 已独立复核）：在 **LLVM IR** 层检查 `%vaarg.addr = phi [va.next, vaarg.in_reg], [va.stack, vaarg.on_stack]` + `load ptr, ptr %vaarg.addr`（直接从槽读取、无二次解引用）；修前形态为对槽值的间接解引用。
- 修法：断言改查 IR（保留原汇编信息仅作附注，不作判据）。

### ③ `ISS-274`：`TESTCASES-047t` 静态证据脚本 3 处 stale

- 文件：`.work/evidence/TESTCASES-047t/run.sh`。
- ① `audit.py` `NameError`：审计器由 `run.sh` 内嵌 heredoc 生成（`AUDIT=$TMP/audit.py`），其 `L129` 区域 `[c['case'] for c in iss246_rows and not (...)]` 在**生成器外**引用 `c` ⇒ `NameError: name 'c' is not defined`、`independent audit: rc=1`；改为 `[c['case'] for c in iss246_rows if not (...)]`（作用域正确）。
- ② `ADR-0030` 未认：`known-fail` 依据表（`:232-272`）只认 `ISS-246`/`ISS-251`，漏 `ADR-0030`（5 条 long-double）⇒「every row has a registered basis」FAIL；依据表补 `ADR-0030`，并保留**反向校验**（无依据行仍须 FAIL）。
- ③ `ipc_msg` 期望过时：replay 段（`:397-407`）期望 `guest exit=1` + 断言行；`ISS-249` 修复后该例已 `pass`（`exit=0`、无断言行）⇒ 2 条 FAIL；期望改为「`exit=0` 且输出含 pass 标记」。
- ④（同册、明确授权）若复跑仍出现静态 `freshness` 假红（`libc.a` mtime < 源 mtime 的 mtime 代理），按 `check-musl-freshness` 同口径改为**产物内容/戳记**判定，**不得**降级为跳过。

## 接口规范

- **输入**：
  - `tools/testcases/run_llvm_ts_user.py`（`_build_and_run` 的 run 目录准备段 `:1547-1563`；`CASE_PREPARE` 表 `:434-451`）
  - `.work/evidence/LLVM-101t/run.sh`（`asm-semctl-vaarg-direct`）、`.work/evidence/TESTCASES-047t/run.sh`（审计 heredoc / known-fail 表 / replay / freshness）
  - 语料：`.work/source/llvm-test-suite/**`、`.work/source/libc-test/**`（`patchless`，**只读**）
  - 安装根：`.dadao/cross-toolchain/`（`qemu-dadao` / musl 静态+动态产物；**本册无需 `install-host`**）
- **输出**：
  - 驱动最小改动（`lencod` 预建 `Output/`；只对该 `cid` 生效）
  - 两个证据脚本修好并复跑（default + 反例注入）
  - 本任务书完成区 + `milestones.md` 行
- **约束（硬）**：
  - **判据不得放宽**：不改 oracle / 参考输出 / `known-fail` 依据准入 / `excluded` / 逐例超时表；`lencod` 只**补目录**，期望值一字不改。
  - **新规矩 `INFRA-093t`**：本册涉及的所有驱动调用**必须显式** `--json-out` + `--work-dir`；**禁止**写 `.work/log/testcases/**` 作权威产物（`--report-out` 缺省与 `--json-out` 同目录）；日志按 `.work/log/testcases/TESTCASES-051t-<用途>.log` 命名。
  - 只改任务列出的文件（驱动 + 两个证据脚本 + 本任务书）；**不动** `spec/`、`contracts/`、`.tao/contracts/`、`components/**`、语料；不并发其它测试集（`ISS-229`）。
  - 证据脚本在 `.work/`（gitignored）：完成区须写**路径 + 改动摘要**，修改文件清单同样列出（不入 git 提交由 architect 判断）。

## 验收标准

1. **`ISS-276`（主修）**：`lencod` 在静态档、动态档各跑一次（`--link-mode both` 或两档分跑，均带 `--json-out` + `--work-dir`）⇒ 两档均 **`pass`**；run 目录内 `Output/test.264`、`Output/test_rec.yuv` 存在；对照上游参考输出**逐行一致**（贴 `diff`/`fpcmp` 真实 rc）；日志/JSON 路径落纸。
2. **`ISS-276` 无副作用**：邻例 `JM/ldecod` 复跑结论不变；`git diff tools/testcases/run_llvm_ts_user.py` 审计证明改动**仅新增目录预建**（oracle / `CASE_TIMEOUTS` / `known-fail` / `excluded` 零改动）；若跑全量，附「除 `lencod` 外逐例零 diff」，未跑全量则如实写「未跑」+ 用代码面与邻例证据支撑。
3. **`ISS-272`**：`asm-semctl-vaarg-direct` 改查 IR 后复跑 **rc=0** 且该项 PASS（贴断言行）；**可达 FAIL**：注入修前 IR/对象（临时树或 `cp` 备份）⇒ 该项转 `FAIL`（rc≠0）⇒ 还原（`cp`+md5 对账）⇒ 回绿。
4. **`ISS-274`**：三处逐一修好，脚本复跑 **rc=0**（`independent audit` rc=0、known-fail 依据全绿、`ipc_msg` 期望匹配）；**每处至少一条可达 FAIL**（分别注入：错误作用域/移除 `ADR-0030`/改回旧 `exit=1` 期望）并给出「注入→FAIL→还原→回绿」真实输出；④ 若 freshness 假红出现，同口径修后一并复跑 rc=0。
5. **`--json-out`/`--work-dir` 迁移**：上述所有驱动调用（含证据脚本内）显式带两参数；`grep` 证明无 `.work/log/testcases/` 权威写路径；缺参场景按 `INFRA-093t` 报错（rc≠0）。
6. **门控**：`make check`（L1）/ `python3 tools/infra/check_tasks.py` / `make check-knowledge-refs` / `make check-no-residue` / `make check-milestones-fresh` / `python3 tools/infra/check_issues.py` 全 **rc=0**（贴命令与 rc）。
7. **边界**：只动接口规范列出的文件；完成区与真实输出逐条对齐；不提交 git、不 push；不跑 `install-host`（若实际发现必须跑，停下报告）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
