# TESTCASES-069t: ISS-266 四例分类与 SPASS/typeset 诊断（targeted，不跑全量）

**模块**：testcases
**项目里程碑**：M10
**依赖**：QEMU-075t（诊断）
**状态**：待开始

## 背景（只针对 ISS-266 的 4 个 llvm-ts 程序）
QEMU-075t 结论：
- `dbms`：已由 QEMU-063t MemRAS 初始化修好（rc=0，输出一致）⇒ 应 **pass**。
- `8b10b`：`input.txt` 是 LE、BE 目标读成 `0x38000000` ⇒ `lookupTable3B` 越界；**语料/数据问题** ⇒ **known-fail**。
- `SPASS`：guest `SIGSEGV`，`ld.o rd4,[rb39+8]`、`rb39=0`（NULL+8）。
- `consumer-typeset`：guest `SIGBUS`，`ld.ut rd4,[rb16+8]`、`rb16=-1`（NULL+7）。
- SPASS/typeset 根因**未定**（时盒到）；本次给 **≤2 h 诊断时盒**，定不了就如实归类。

## 目标
1. **`8b10b` known-fail**：用现有 known-fail 机制，精确 case + 理由（LE 输入 vs BE 目标，ISS-266）。
2. **`dbms` 断言 pass**（不得被误记 blocked/fail）。
3. **SPASS/typeset**：
   - 判据：`-strace` 有 `--- SIG…` 转发行、stderr 无 `QEMU internal` ⇒ **fail**（guest 崩溃被如实转发），**不再 blocked**；
   - 诊断时盒 ≤2 h：用 `-strace` / `-d in_asm,op` 回溯 `rb39=0` / `rb16=-1` 的来源，给出「qemu 指令语义 / 后端错编 / 语料」的判定或**明确未定**；
   - 未定 ⇒ 记 fail + reason 指本册，不伪造 known-fail。
4. **驱动**：只改 `tools/testcases/run_llvm_ts_user.py` 的 `QEMU_SIGNAL_ISSUES` / 分类 / reason；**不跑全量**。
5. issue：ISS-266 按结果**收窄或关闭**（8b10b known-fail、dbms pass、SPASS/typeset 有判定/已分类）；未定则保持 open 并写清剩余面。

## 验证（只跑这 4 例，静态+动态）
```bash
python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 1 \
  --only '8b10b$' --only 'dbms$' --only 'SPASS$' --only 'consumer-typeset$' \
  --timeout 600 --json-out /tmp/opencode/TESTCASES-069t/four.json
```
- 期望：`dbms` pass；`8b10b` known-fail；`SPASS`/`consumer-typeset` **fail**（或诊断后按结论分类）；**0 blocked**（guest 崩溃类）。
- 回归：这 4 例之外的 llvm-ts **不跑**；`make check` rc=0。
- 诊断证据落 `.work/log/testcases/TESTCASES-069t-*.log`（gdb/strace/反汇编）。

## 约束
- 只改 `run_llvm_ts_user.py` + `issues.yaml` + 任务书/`milestones.md`；不改 qemu/spec/contracts/其它 driver。
- 不跑全量 llvm-ts、不夜跑；定向 4 例。
- 反例注入还原用 `cp`+md5；临时目录 `/tmp/opencode/TESTCASES-069t/`；不提交。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 诊断结论（SPASS/typeset）
（待填）

### 遗留
（待填）
