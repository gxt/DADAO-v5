# INFRA-054t: clang 内置头（resource-dir）安装

**模块**：infra
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`，产出含 clang + `lib/clang/<ver>/include` 的 build tree）；**与 Wave 0 其它任务同改 `Makefile` ⇒ 串行**
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
