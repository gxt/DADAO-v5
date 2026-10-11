# INFRA-054t: clang 内置头（resource-dir）安装

**模块**：infra
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`，产出含 clang + `lib/clang/<ver>/include` 的 build tree）；**与 Wave 0 其它任务同改 `Makefile` ⇒ 串行**
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景（自包含；主会话 2026-10-10 已独立复核）

`TESTCASES-039t`（Embench 接入）engineer 停工登记了**次要（可绕过）缺口**：交付的 cross-toolchain 里 **clang 内置头缺失**——`clang -print-resource-dir` 指向 `.dadao/cross-toolchain/lib/clang/23`，而该目录**不存在**，故 `#include <stddef.h>` 直接：

```
fatal error: 'stddef.h' file not found      (clang -target dadao-unknown-elf -c，rc=1)
```

`LLVM-063t` 已在遗留问题中登记「target sysroot 的 resource-dir `include/`（`cross-toolchain/lib/clang/23/include`）不在 `install-host`（`ADR-0016 D11`）范围、实际不存在 ⇒ `stddef.h` 等内建头暂不可用（freestanding 最小程序不受影响；如需另立任务）」。本任务即补此缺口，供 Embench（`md5sum`/`ctype`/`string` 等）与真实 C 使用。

**事实核对（主会话只读实测）**：
- build tree `<LLVM_BUILD>/lib/clang/23/include` **存在**，含 clang 内置头（现场统计，非写死；源 = `clang/lib/Headers/**`）。
- cross-toolchain `.dadao/cross-toolchain/lib/clang/` **不存在**（`clang -print-resource-dir` 指向它）。
- `install-host` 现仅安装 `bin/` 工具 + lit + sysroot 骨架（`Makefile` install-host 配方），**未安装 resource-dir `include/`**。

**证据指针**：`.work/log/testcases/TESTCASES-039t-blocker.log`（§D1 resource-dir 缺、§D3 `NO (missing)`）、`-blocker_probe_result.txt`、`-progress.md`；`.tao/tasks/llvm/LLVM-063t-clang-target与driver.md`「遗留问题」末条。

## 接口规范

- **输入**：
  - `Makefile` 的 `install-host` 目标（`atomic-install` define + 工具/lit/sysroot 安装段；`INFRA-053t` 已把写操作做成 temp+`rename(2)` 原子）。
  - `tools/infra/paths.py` / `manifests/install-dirs.lock.toml`（`host_toolchain_dir` = `.dadao/cross-toolchain`；**落点唯一真源，勿硬编码**）。
  - build tree：`<LLVM_BUILD>/lib/clang/<ver>/include`（由 clang 构建生成；`<ver>` 由 build tree 现场确定，**不写死**）。
  - `ADR-0016`（安装/产物目录布局 D3/D4/D5/D11）。
- **输出**：
  1. `install-host` 随装 **clang 内置头**：把 `<LLVM_BUILD>/lib/clang/<ver>/include`（+ 同目录必要的 `lib/`？——如无消费者可**不装**，须说明）安装到 `$(HOST_TOOLCHAIN_DIR)/lib/clang/<ver>/include`，使 `clang -print-resource-dir` 指向的目录**真实存在**。
  2. **来源须交代**：内置头来源 = clang 构建产出的 `lib/clang/<ver>/include`（上游 `clang/lib/Headers/**`）；在 `Makefile`/changelog 注明来源与版本推导方式（`<ver>` 从 build tree 现场探测，**不 hardcode**）。
  3. `Makefile` 安装段遵循 `INFRA-053t` 的原子写入惯例（temp + `rename(2)`）或可证幂等的方式。
- **约束**：
  - **不引 libc**：仅装 clang **freestanding 内置头**（`stddef.h`/`stdint.h`/`stdbool.h`/`stdarg.h`/`limits.h`/`float.h` 等，来自 clang `lib/Headers`），**不**引入 target libc/OS/syscall 头（M6 明确不引 libc）。
  - **最小改动**：只动 `install-host` 相关段与必要的 `Makefile` 注释/changelog；**不改**工具集清单/落点/sysroot 骨架语义（`ADR-0016 D3/D4/D5/D11`）。
  - **落点取自 `paths.py`**（`host_toolchain_dir`），**不硬编码** `.dadao/...`。
  - **`spec/`/`contracts/`/`components/**` 交集为空**（纯 `Makefile`/`tools/infra/**`）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-054t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/INFRA-054t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须能复现回绿。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**（含头文件条数）；需要时由脚本**现场统计**，或写「**不下降 / 逐项相等**」。
- 复杂命令输出留 `.work/log/infra/INFRA-054t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **resource-dir 存在**：`install-host` 后 `.dadao/cross-toolchain/lib/clang/<ver>/include`（= `clang -print-resource-dir` 指向目录 + `/include`）**真实存在**（给真实 `ls`/`print-resource-dir` 输出）。
2. **内置头可用**：`clang -target dadao-unknown-elf -c` 能 `#include <stddef.h>` / `<stdint.h>` / `<stdbool.h>` / `<stdarg.h>` / `<limits.h>` / `<float.h>`（各一最小 TU）且 **rc=0**（给真实命令 + 输出 + rc）。
3. **与 freestanding 目标一致**：仍**不**搜索 host `/usr/include`、**不引** target libc（给 `-E -v` 搜索表证据）。
4. **幂等**：`make install-host` **连跑两次均 EXIT=0**（首次为冷态）；`clang ... #include <stddef.h>` 在两次之后均 rc=0。
5. **不回归**：`make check` 等既有门控 EXIT=0（通过数与改前**逐项相等 / 不下降**，现场统计）。
6. **一键证据脚本**：`.work/evidence/INFRA-054t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如临时移除 resource-dir `include/` ⇒ `#include <stddef.h>` FAIL ⇒ 还原 ⇒ 回绿），给真实输出与退出码。
7. **`spec/`/`contracts/`/`components/**` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts|components)/'` → 无输出。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：通过 6/6（①资源目录存在 ②六头 rc=0 ③无 host `/usr/include` ④两次 install-host EXIT=0 ⑤`make check` EXIT=0 ⑥证据脚本 RUN_EXIT=0）。失败原因：无。
**修改文件**：`Makefile`（新增 `atomic-install-dir` define + `CLANG_RESOURCE_{VER,SRC,DIR}` 变量 + install-host 段 3 行 + 注释）；`.work/evidence/INFRA-054t/run.sh`（新证据脚本，`.work/` 为 gitignored）；本任务书。**未改** `tools/infra/**`（落点由 `paths.py::host_toolchain_dir` 提供，无需新 helper）。
**验收结果**（真实输出/退出码）：
- ①`clang -print-resource-dir` = `.dadao/cross-toolchain/lib/clang/23`（rc=0），其 `include/` 存在，现场 `find -name '*.h'` = **284**；对源树 `diff -rq` **rc=0**、条目数 245=245。
- ②`stddef/stdint/stdbool/stdarg/limits/float` 各最小 TU `clang -target dadao-unknown-elf -c` **rc=0**（逐个打印）。
- ③`clang -E -v` 搜索表 = `…/lib/clang/23/include` + `…/dadao-unknown-elf/include`，`/usr/include` 出现 **0** 次。
- ④`make install-host` 冷态首跑 + 连跑 2 次均 **EXIT=0**；其后 ② 仍 rc=0；无遗留 `*.tmp.*`。
- ⑤`make check` **EXIT=0**（现场统计 234 个含 `PASS` 行；本任务仅改 `Makefile`，未触任何门控输入 ⇒ 通过数不下降）。
- ⑥`.work/evidence/INFRA-054t/run.sh` → `RUN_RESULT: ALL PASS` / `RUN_EXIT=0`；注入自检：`mv include/` ⇒ `stddef` **rc=1** ⇒ 还原（manifest md5 `0cb8edc286230fefa680f1b03762cd27` 前后相等）⇒ **rc=0**。
- ⑦`git diff --name-only | grep -E '^(spec|contracts|components)/'` 无输出；⑧`git status --porcelain -uall` 仅 ` M Makefile`，无 `_tmp/_gate/.orig/.rej`。
**新发现/坑**：`install-host` 原只装 `bin/` + lit + sysroot 骨架，resource-dir `lib/clang/<ver>/include` 缺失 ⇒ `#include <stddef.h>` file not found。`<ver>` 现场从 build tree（`ls lib/clang`，取首个）探测 = `-print-resource-dir` 基名，**勿硬编码**。目录安装**不能**单次 `rename(2)` 覆盖非空目录（ENOTEMPTY）⇒ temp staging + `rm -rf` 旧目录 + `rename`（`atomic-install-dir`，幂等）。建议 `/complete`：changelog 一条 + lessons §8 操作规范（来源 = clang `lib/Headers/**`；版本推导 = build tree 现场探测）。
**遗留问题**：resource-dir `lib/`（compiler-rt builtins）**未装**——M6 无消费者（Makefile 注释已说明），如需另立任务。**ISS-174 原话**：「现象：`.dadao/cross-toolchain/bin/clang -print-resource-dir` = `.dadao/cross-toolchain/lib/clang/23`，而该目录**不存在** ⇒ `#include <stddef.h>` 报 `fatal error: 'stddef.h' file not found`（rc=1）。根因：`install-host` 只装 `bin/` 工具 + lit + sysroot 骨架，**未安装 clang resource-dir 的 `lib/clang/<ver>/include`**……归属：新任务 `INFRA-054t`」。本任务已消除该缺口。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查新增 `atomic-install-dir` define、`CLANG_RESOURCE_*` 变量、install-host 配方 3 行与证据脚本；意见/问题/判决：

| # | 类别 | finding | 判决 |
|---|------|---------|------|
| F1 | 逻辑/鲁棒 | `CLANG_RESOURCE_VER := $(shell ls -1 $(LLVM_BUILD)/lib/clang 2>/dev/null 取首行)`：多版本目录时取首个、不确定 | ❌不修：本 build tree 仅 `23`（现场 `ls` 唯一）；任务要求「现场探测、不硬编码」；`test -d $(CLANG_HEADERS_SRC)` 守卫源缺失时 fail-loud |
| F2 | 设计/原子性 | 目录 `rename(2)` 不能覆盖非空目录（ENOTEMPTY），须先 `rm -rf` 旧目录 ⇒ 极短空窗 | ✅已修(说明+验证)：任务允许「temp+rename **或可证幂等**」；Makefile 注释已说明；幂等由两次 EXIT=0 证明 |
| F3 | 完整性 | 是否随装 resource-dir `lib/`（compiler-rt builtins） | ❌不修：M6 无消费者；Makefile 注释已声明「deliberately not installed」 |
| F4 | 防造假/证据 | 证据脚本须能失败（注入有鉴别力） | ✅已验证：`mv include/` ⇒ `stddef` rc=1；还原后 md5 前后相等、rc=0 |
| F5 | 正确性 | 安装树是否与源树逐字节一致 | ✅已验证：`diff -rq` rc=0、条目 245=245、`module.modulemap` 在 |

处置汇总：F2/F4/F5 ✅；F1/F3 ❌（均附现场证据，非静默略过）。无未修 finding。判决：可交付，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Accepted**（全部 8 项独立重跑通过，约束无违反）。证据：`.work/log/infra/INFRA-054t-review.log`（各命令原始输出）。

| # | 核验 | 真实输出 / rc |
|---|------|--------------|
| 1 | resource-dir | `clang -print-resource-dir`=`/mnt/tao/DADAO-v5/.dadao/cross-toolchain/lib/clang/23` rc=0；`include/` 在，`.h`=284；`diff -rq` 与 `.work/build/llvm/lib/clang/23/include` **rc=0**、295=295 文件 |
| 2 | 六头 | reviewer 自写最小 TU 逐个 `clang -target dadao-unknown-elf -c`：`stddef rc=0 / stdint rc=0 / stdbool rc=0 / stdarg rc=0 / limits rc=0 / float rc=0` |
| 3 | freestanding | `-E -v` rc=0，搜索表仅 `…/lib/clang/23/include` + `…/dadao-unknown-elf/include`；`grep -c '/usr/include'`=**0**；无 target libc |
| 4 | 幂等/冷态 | 移走整个 `lib/clang/`（冷态，`ls` rc=2）→ `make install-host` **EXIT=0** → 再跑 **EXIT=0**；两次后六头全 rc=0、`diff -rq` rc=0、无 `*.tmp.*` |
| 5 | 独立注入 | **删已装 `include/stddef.h`**（注入有效性：`test ! -f` rc=0）⇒ `#include <stddef.h>` **rc=1** `fatal error: 'stddef.h' file not found` ⇒ `make install-host` 重装 ⇒ 回绿 rc=0，`stddef.h` md5=`787fd4b1…` 前后相等 |
| 6 | Makefile diff | `atomic-install-dir` 的 `rm -rf $(2)` 目标精确=`$(CLANG_RESOURCE_DIR)/include`（无通配/拼接）；`CLANG_RESOURCE_VER`=`ls -1 $(LLVM_BUILD)/lib/clang \| head -n1` 现场探测、无硬编码 23；落点=`HOST_TOOLCHAIN_DIR`（`paths.py`，line 16，空值由 line 24 `$(error)` 守卫）；`HOST_LLVM_TOOLS`/sysroot 段零改（diff 纯新增，ADR-0016 D3/D4/D5/D11 语义未动） |
| 7 | 门控+证据脚本 | `make check` **EXIT=0**、`grep -c PASS`=234（与完成区一致）；`run.sh` 审查：C1–C4 各有可达 FAIL 路径、无恒真；重跑 **RUN_EXIT=0**（注入 rc=1、还原 manifest md5=`0cb8edc2…` 前后相等） |
| 8 | 无残留/边界 | `git status --porcelain -uall` 仅 ` M Makefile` + 任务书，与注入前快照 `diff` rc=0（Makefile md5 `6ebcf04d…`/run.sh md5 `ab0076e0…` 前后相等 ⇒ 未改产物）；`diff --name-only \| grep -E '^(spec\|contracts\|components)/'` 与 `origin/master...HEAD` 同查均空；无本任务 `*_tmp/_orig/_rej`（`.dadao/tests/lit-output/` 下 `*.test.tmp.*` 为 lit 既有测试产物、gitignored，非本任务残留） |

**脚本独立证伪**：另注入（删 `include/stddef.h`）后重跑**同一脚本** ⇒ `RUN_EXIT=1` `[FAIL] C2: <stddef.h> rc=1` ⇒ `cp`+md5 还原（`787fd4b1…` 相等）⇒ 重跑 `RUN_EXIT=0`，证明「能失败」非自检自证。约束逐条：落点 paths.py ✓、不引 libc ✓、`spec/contracts/components` 零交集 ✓、原子/幂等 ✓、`<ver>` 现场探测 ✓、计数未硬编码（284/234 为现场统计）✓。遗留（resource-dir `lib/` 不装）已在完成区披露、有注释说明，非阻断。无 blocking finding，供架构师终审。
