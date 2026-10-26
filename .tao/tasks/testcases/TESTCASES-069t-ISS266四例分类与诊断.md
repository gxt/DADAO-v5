# TESTCASES-069t: ISS-266 四例分类与 SPASS/typeset 诊断（targeted，不跑全量）

**模块**：testcases
**项目里程碑**：M10
**依赖**：QEMU-075t（诊断）
**状态**：已验证

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

**状态**：已验证

**测试结果**：`bash .work/evidence/TESTCASES-069t/run.sh` ⇒ **48 PASS / 0 FAIL**（含注入→8b10b 降为 fail→`cp`+md5 还原→回绿）；`make check` rc=0。定向两档（static/dynamic）均为 `total=4 pass=1 fail=2 known-fail=1 blocked=0`；driver rc=1 因真实 `fail` 存在（判据即判定，非门控失败）。

**修改文件**：`tools/testcases/run_llvm_ts_user.py`（`rc<0` 的 `-strace` 转发探针 + ISS-266 8b10b per-case 行 + reason/`GUEST_FAULT_NOTES`）、`.tao/knowledge/issues.yaml`（ISS-266 closed）、`.tao/knowledge/milestones.md`（本行）、本任务书；证据脚本 `.work/evidence/TESTCASES-069t/run.sh`（`.work/` 不入库，日志 `.work/log/testcases/TESTCASES-069t-*`）。

**验收结果**：
- 两档逐例：`dbms PASS exit=0`（byte-exact）；`8b10b KNOWN-FAIL basis=ISS-266 exit=139`；`SPASS FAIL exit=139 (si_addr=0x8)`；`consumer-typeset FAIL exit=135 (si_addr=0x7)`；`blocked=0`。
- 三例 `qemu-strace.log` 均有 `--- SIGSEGV/SIGBUS {si_signo=…, si_code=1, si_addr=…} ---` 且无 `QEMU internal`（探针判据）。
- `make check` ⇒ `repository checks (L1): PASS`（rc=0）。

**诊断结论（SPASS/typeset）**：
- **SPASS = 语料 UB（非 qemu 语义/非后端错编）**：`cnf.c:2760` 把 `int symbol_Equal(int,int)` 强转成 `BOOL(*)(POINTER,POINTER)`；clang 按指针原型传 `rb16/rb17`，out-of-line `symbol_Equal` 读 `rd16/rd17`（`SPASS.elf` 调用点 `0x510fc` → callee `0x46758`）⇒ 自由变量过滤得错误结果，`acc=4/acc_len=2` 要删 2 个而 `newvariables` 已空 ⇒ `list_Top(NULL)` → guest SIGSEGV。同一源码 gcc/x86-64 `-O2` 跑到 exit 0；DADAO `-O0`/`-O2` 偏移一致（首调用 `nfree=3/acc=2` vs 宿主 `nfree=2/acc=1`）。**反证**：`/tmp` 副本把该强转换成匹配原型 wrapper 后，同 clang `-O2` DADAO 构建 **rc=0**、`md5(stdout+exit 0)=74365d61…` 与宿主 gcc 构建**逐字节相同**（≠上游 md5 参考 `b0b56c51…` ⇒ 另属「参考方差」面，本册不展开）。同类 = `lemon`/`ISS-277`、`TESTCASES-064t`（bank 不匹配）。
- **typeset = 语料未查 `catopen` 失败 + musl `catclose` 无 -1 守卫**：`z01.c:229/856` 无条件 `catclose(MsgCat)`；guest 无 catalog（`-strace`: `openat("lout.lib/locale/C/LC_MESSAGES/errors.C") = -1 ENOENT`）⇒ `catopen` 返回 `(nl_catd)-1`，musl `catclose` 解引用 `map+8`（addr `0x7`）→ guest SIGBUS；宿主 glibc `catclose((nl_catd)-1)` 返回 `-1/EBADF`（实测探针），故上游参考在 glibc 下不崩。
- 两者按判据记 **fail**（不伪造 known-fail）；8b10b 的 `ISS-266` 活证据 = `input.txt` 全 65536 小端词索引在界内、65409 个大端词越界（首词 `38000000` 大端 index5=117440512/index3=29360128）。

**新发现/坑**：① 本端口 `rc<0` = qemu `die_with_signal` 重发宿主信号，**不能**直接判 blocked，须 `-strace` 看 `--- SIG…` / `QEMU internal`；② bank 分离 ABI 会把「不兼容函数指针强转」类 UB 暴露成真实错误（诊断语料崩溃优先查跨 bank 原型）；③ 探针只在 `rc<0` 触发，失败用例运行时翻倍（本次每例 ~20 s）。

**遗留问题**：SPASS/typeset 属上游语料/锁定 musl 面，未改语料/qemu/LLVM；驱动保持 `fail`（全量 llvm-ts 仍红），转绿须上游修语料或改 musl 语义（另立册）。**SPASS 另有「参考方差」面**：修掉 UB 强转后 DADAO 与宿主 gcc 输出逐字节相同、却仍 ≠ 上游 md5 参考（`b0b56c51…`）⇒ 即便修语料也需重定参考，单独立册。未跑全量 llvm-ts、未夜跑（任务约束）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行复核驱动改动、探针判据、ISS-266 活证据与证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `-strace` 行解析写成 `si_signo=(\d+)`，实际 qemu 打印 `si_signo=SIGSEGV`（符号名）⇒ 探针恒不命中、四例仍 blocked | ✅已修 | 正则改 `si_signo=SIG[A-Z0-9]+`，信号号用 `getattr(signal, name)` 取得；`si_code` 保留原文（可能是名字） | 首跑四例即复现（三例 blocked）；修后两档 `fail=2/known-fail=1/blocked=0`，`qemu-strace.log` 逐例命中 |
| F2 `run_to_file`/`guest_signal_probe` 返回值形状与 docstring 不一致（3 元 vs 2 元） | ✅已修 | `run_to_file` 固定 `(rc, timed, err)`；探针固定 `(info|None, why)` | `py_compile` + 两档实跑 |
| F3 `KNOWN_FAIL_BASES` 引用未定义的 `ISS266_ID`（常量块在其后） | ✅已修 | 把 `ISS266_ID/ISS266_8B10B/ISS266_TABLE_RE` 移到表前 | 导入/运行无 `NameError` |
| F4 计入注入还原的「已还原」证据不足（仅 md5 可能自证） | ✅已修 | 证据脚本 `cp` 备份 + 前后 md5 对账 + 还原后单例重跑回绿（`I2/I3/I4`） | `run.sh` 输出 `I2.restored_md5`/`I3.restored_rc=0`/`I4=known-fail` |
| F5 探针把 guest stderr 与 `-strace` 混在同一文件，语料若打印 `QEMU internal` 会误判 blocked | ❌不修（已核） | — | 本次三例均无该串；且保守方向 = 记 blocked（宁可漏判 fail 不冒充），非假绿 |
| F6 ISS-266 活证据扫全 65536 词，而运行只用前 2000 词 | ❌不修（已核） | — | 证据是「数据文件是 LE 流」的更强断言（全量），首词即已越界；不依赖运行长度 |

自审判定：F1–F4 已修并复验，F5/F6 有据不修；无未修缺陷 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-27）

**重跑（reviewer 本人执行，非采信完成区）**：
- `bash .work/evidence/TESTCASES-069t/run.sh` ⇒ **exit=0，48 PASS / 0 FAIL**（S1–S3、D0–D15×两档、E1、I1–I4 全绿）。
- 定向两档（run.sh 内即任务书验证命令，独立产物复核 json）：static/dynamic 均 `total=4 pass=1 fail=2 known-fail=1 blocked=0`；逐例 `dbms pass exit=0`、`8b10b known-fail basis=ISS-266 exit=139`、`SPASS fail exit=139 si_addr=0x8`、`consumer-typeset fail exit=135 si_addr=0x7`；driver rc=1（真实 fail 存在）。
- `make check`（run.sh E1 + 独立日志核）⇒ `repository checks (L1): PASS`，rc=0。
- qemu-strace.log 逐例：`--- SIGSEGV/SIGBUS {…} ---` 各 1 行、`QEMU internal` 0 行（D14/D15 PASS）。

**独立反例注入（方案②，非 engineer 注入点）**：`cp` 备份驱动（md5 `b5741dc6…`）→ 在 `guest_signal_probe` 入口注入 `return None, "REVIEWER INJECTION: probe disabled"` → 定向单跑 SPASS ⇒ **`blocked=1`（`qemu killed by host signal 11; REVIEWER INJECTION…`）**，证明探针 load-bearing、blocked 路径可达 → `cp` 还原 + **md5 相等**（`b5741dc6…`）→ 重跑 SPASS ⇒ **fail / SIGSEGV**（回绿）。全程未用 `git checkout/restore/stash`。

**脚本审核**：逐条核 run.sh —— 每条 check 有可达 FAIL 路径（计数取自现场 json、grep 计数含缺文件即错）；注入非空（assert 唯一 needle）且有 `trap` + md5 对账 + 还原后单例重跑；无恒真、无双写同果。

**约束核验**：① 改动范围 = 4 文件（driver/issues.yaml/milestones.md/任务书），`git show --stat` 核过，未动 qemu/LLVM/语料/其它 driver；② 未跑全量、未夜跑（仅定向 4 例）；③ 8b10b 行精确 case（`cid != ISS266_8B10B` 即拒绝，活证据复读 input.txt + 表声明）；④ 探针仅在 `rc<0` 分支触发，timeout/无转发行/QEMU internal ⇒ 保守 blocked，其它 blocked 不误升；⑤ 无仓库残留（`git status --porcelain -uall` 前后均 0 行，注入还原 md5 相等）。

**根因证据抽查**：SPASS —— `symbol.h:112 typedef int SYMBOL` + `symbol.h:176 BOOL symbol_Equal(SYMBOL,SYMBOL)`，`cnf.c:2760` 强转属实；诊断日志含调用点 `0x510fc`（`rd2rb rb16/rb17`）与 callee `0x46768 cmp.st rd4, rd16, rd17`；wrapper 反证日志 md5 `74365d61…`（DADAO 修复构建 = 宿主 gcc 构建，≠ 上游 `b0b56c51…`）——支撑「语料 UB + 另有参考方差」。typeset —— `z01.c:229 catopen` 未查返回值、`z01.c:856` 无条件 `catclose` 属实；musl `catclose.c` 无 -1 守卫、`V(map+8)` 解引用 addr 0x7 属实；`-strace` 有 `openat(errors.C) = -1 ENOENT` 与 `--- SIGBUS si_addr=0x7`。ISS-266 closed / ISS-338、ISS-339 登记与上述一致、如实。

**遗留/风险**（不阻断）：探针把 guest stderr 与 strace 同文件（F5，保守方向=漏升 fail 不假绿，已披露）；探针使 rc<0 用例运行时翻倍；「timeout⇒blocked」为代码路径核验、未实跑注入验证。

**判决：Accepted**（验收命令块在 reviewer 重跑下全绿、约束无违反、反例注入→FAIL→还原→回绿成立）。

