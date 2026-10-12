# INFRA-056t: 接入 `clang++` + 核实 2 个 `.cpp` 测试需求

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-050t`（LLVM 一次构建 + 双落点，`已验证`；同改 `Makefile` ⇒ 串行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #3`）：**加 `clang++`** + 核 **2 个 `.cpp`** 测试需求。
  - 现状：`.dadao/cross-toolchain/bin/` 已有 `clang`（无 `clang++`）；`INFRA-050t` 的一次构建（`LLVM_ENABLE_PROJECTS=clang;lld`）**已含 clang 驱动**（`clang++` 通常是 `clang` 的 C++ 驱动模式，`clang -x c++` 等价），安装落点当前只装 `clang`。
  - picolibc 自带 test 中的 2 个 C++ 文件（实测）：`test/test-cdefs-cxx03.cpp`、`test/test-cplusplus.cpp`（位于 `.work/source/picolibc/test/`，随 `INFRA-055t` 浅克隆）。
  - `ADR-0016`（install 布局：`D3/D4/D5/D11`）；`Makefile` 的 `install-host` target。
- **输出**：
  1. `.dadao/cross-toolchain/bin/clang++` 落点（可执行；`clang++ --version` 与 `clang` 同源）——按 `ADR-0016` 布局；`Makefile`/`tools/infra/**` 同步。
  2. **2 个 `.cpp` 需求核实报告**：逐条说明其编译需求（是否需要 C++ 头/库、freestanding 形态、`-nostdlib` / `-ffreestanding` 下能否编），实测证据（编译/失败真实输出）。
- **约束**：
  - **不引入** C++ 标准库（freestanding 优先）；若某 `.cpp` 需 libstdc++/libc++，**显式登记**（不静默跳过）。
  - **依赖 `INFRA-050t` 的构建产物**，不重复构建 LLVM；仅补安装/落点。
  - **计数不写死**；只动任务范围，越界须披露。

## 验收标准

1. **`clang++` 可用**：`.dadao/cross-toolchain/bin/clang++ --version` EXIT=0（真实输出）；与 `clang` 同 commit。
2. **幂等**：连续两次 `make install-host` 均 EXIT=0（同 `INFRA-053t` 口径）。
3. **2 个 `.cpp` 核实**：逐条给出编译命令 + 真实结果（OK / 缺什么）；需求结论明确（是否需要 C++ 库）。
4. **门控**：`make check`、`check-no-residue` EXIT=0；`check-patch-tree` EXIT=0。
5. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`.work/evidence/<任务ID>/run.sh` rc=0（11/11 现场计）；`--inject` 自检 rc=0（删 Makefile 行→`makefile-wiring` FAIL→`cp`+md5 还原→回绿，md5 一致）。
**修改文件**：`Makefile`（install-host 增 `ln -sf clang $(HOST_TOOLCHAIN_BIN)/clang++` + 说明注释）；`.tao/knowledge/milestones.md`（INFRA-056t 行→`待验收`）；本任务书；`.work/evidence/<任务ID>/run.sh` 与 `.work/log/infra/` 日志（均 gitignored）。
**验收结果**（真实输出）：
1. `clang++ --version` rc=0：`clang version 23.1.1 (…/.cache/llvm-project.git 47eb2396a44cc5c8c2498da2215ae6b09b8b568a)`；与 `clang --version` **逐字节相同**、`stat -Lc %i` 同 inode（同一二进制）；`merge-base --is-ancestor 6dfe1677…（manifest 锁）HEAD`=真（构建基于锁定基线 +1 本地 patch 提交）。
2. 幂等：`make install-host` 连跑两次 rc1=0 rc2=0（各 ~60s）。
3. `test-cdefs-cxx03.cpp`：无 libc 时 FAIL（`'sys/cdefs.h' file not found`）；加 picolibc `-I`+探针配置后 rc=0（`-std=c++03 -ffreestanding -nostdlib -fno-exceptions -fno-rtti`）。`test-cplusplus.cpp`：无 libc FAIL；加 picolibc `-I`+探针后 rc=0。**结论：二者均需目标 C 库头（picolibc，含生成 `picolibc.h`+端序+arch `jmp_buf`，属 `INFRA-057t`），均不需 C++ 标准库**。
4. 门控：`make check` rc=0（L1 `repository checks: PASS`）、`check-no-residue` rc=0、`check-patch-tree` rc=0（4 组件/110 补丁）；追加 **L2 `make check-modules` EXIT=0**（`module checks (L2): PASS`）。
5. `git status --porcelain -uall` 仅 `M Makefile`（+ 本任务书/台账/证据脚本）；无 `*_tmp*`/`*.orig`/`*.rej`。
6. 孤儿清理：删前 `ls -la` 留证（`.work/log/infra/…-orphans-before.log`，4 个 `*.tmp.*` 共 888M），删除后 `count=0`。
**新发现/坑**：
- `clang++ --version` 报的 commit 是**工作树 HEAD**（锁定基线 `6dfe1677…` + 1 本地提交 `47eb2396a`），非 manifest 字面值；核「同 commit」应比对 `clang` 自身（同 inode 天然相等），勿直接等于 manifest `commit`。
- 目标端序为 **大端**（`__BYTE_ORDER__=__ORDER_BIG_ENDIAN__`，clang 未定义 `__FLOAT_WORD_ORDER__`）⇒ picolibc `machine/ieeefp.h` 需 `__IEEE_BIG_ENDIAN`（`INFRA-057t` 配置项）。
- picolibc `machine/setjmp.h` **无 dadao 分支** ⇒ `jmp_buf` 未定义，`test-cplusplus.cpp` 阻塞于此（arch 移植，`INFRA-057t`）。
- `atomic-install` 会遗留 `$dst.tmp.$$` 孤儿（进程中断）；本次清 4 个（非本任务引入，属落点卫生）。
**遗留问题**：2 个 `.cpp` 的**实编通过**依赖 picolibc 目标头/配置（`INFRA-057t`），本任务仅核实需求、未接 picolibc 头（范围外）。探针 `picolibc.h`/`machine/setjmp.h` 仅置 `/tmp`，未入仓。

## 审阅记录

### 第 1 轮 engineer 自审

**改动清单**：`Makefile`（install-host +1 行 `ln -sf clang …/clang++`、+6 行注释）；`.tao/knowledge/milestones.md`（1 行）；本任务书；`.work/evidence/<任务ID>/run.sh`（gitignored）。

**逐行审查**：
1. `@ln -sf clang $(HOST_TOOLCHAIN_BIN)/clang++`：相对软链、与 `clang` 同目录；`-sf` 幂等（覆盖含悬挂链）；**未**入 `HOST_LLVM_TOOLS`（避免 atomic-install 二次拷 4 GB `clang`），与既有 `ld.lld -> lld` 先例同构；位置在 `mkdir -p` + `clang` 安装之后 ⇒ 不会悬挂；未加 `|| exit 1`，与相邻 `ld.lld` 行风格一致（recipe 行失败 make 默认中止）。
2. 注释与实测相符（`bin/clang++ -> clang-23` 已验证同源）。
3. 证据脚本：计数现场统计（`TOTAL/FAILS` 不写死）；每条断言有可达 FAIL 路径（`--inject` 实测删行→`makefile-wiring` FAIL→`cp`+md5 还原→绿，md5 一致）；结尾 `[ "$FAILS" -eq 0 ]` 判 rc，无 `tee` 吞码。

**findings**：
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `stat -c %i` 取的是软链自身 inode ⇒ `clangpp-exists` 假 FAIL | ✅已修 | 改 `stat -Lc %i`（解引用） | run.sh rc=0；`inode_cpp==inode_clang` |
| `samecommit` 误把 manifest 字面 `commit` 当构建 commit（实为工作树 HEAD） | ✅已修 | 改为「clang++ == clang commit」+ `merge-base --is-ancestor <lock> HEAD` | rc=0，`based_on_lock=1` |
| 门控 record 的 actual 取到 `make: Leaving directory`（噪声） | ✅已修 | `grep -vE 'Entering\|Leaving'` | actual=`check-no-residue: PASS` |
| 脚本头注释 #3 与实现不符 | ✅已修 | 更新注释 | — |

**判决**：4 findings 全 ✅已修；证据脚本 11/11 + 注入自检 + L1/L2 门控全绿；无未修项。

### 第 1 轮 reviewer 验收（2026-10-11）

**重跑记录**（均我本机真实输出，退出码直接捕获，无 `tee` 吞码）：
- 门控：`make check` rc=0（`repository checks (L1): PASS`）；`make check-no-residue` rc=0（`check-no-residue: PASS`）；`make check-patch-tree` rc=0（`check-patch-tree: 4 component(s), 110 patches OK`）；`make check-modules` rc=0（`module checks (L2): PASS`）。
- 落点：`ls -la .dadao/cross-toolchain/bin/clang++` = `clang++ -> clang`（相对软链，与 `ld.lld -> lld` 先例同构）；`--version` rc=0（`clang version 23.1.1 (… 47eb2396a…)`）；`stat -Lc %i clang clang++` 同 inode `25559215`；`diff <(clang --version) <(clang++ --version)` rc=0（逐字节相同）。
- 同源 commit：源树 HEAD=`47eb2396a44cc…`；`git merge-base --is-ancestor 6dfe1677…(manifest 锁) HEAD` rc=0，其间仅 1 个本地 patch 提交，与自述一致（「clang++==clang」由同 inode 天然成立）。
- 「避免二次拷」判据：`grep -n 'HOST_LLVM_TOOLS *=' Makefile` → `295: … FileCheck not llc clang`（**不含** clang++）；`grep -n clang++ Makefile` 仅注释 3 行 + 第 350 行 `@ln -sf clang $(HOST_TOOLCHAIN_BIN)/clang++`。
- 幂等：独立重跑 `time make install-host` rc=0（`real 0m56.7s`）；日志 llvm/lld 两处 `ninja: no work to do`。
- `.cpp` 逐条自跑（临时树 `<tmp>/INFRA-056t-review/`）：① 无目标 C 库头 ⇒ `test-cdefs-cxx03.cpp` rc=1（`'sys/cdefs.h' file not found`）、`test-cplusplus.cpp` rc=1（`'arpa/inet.h' file not found`）；② 加 picolibc `-I <picolibc>/libc/include` + 探针配置（`<tmp>/inc/{picolibc.h,machine/setjmp.h}` + `-D__IEEE_BIG_ENDIAN`，配方取自证据脚本 `make_probe_includes`，**可复现**）⇒ 两文件均 rc=0（`.o` 产物存在，`-std=c++03 -ffreestanding -nostdlib -fno-exceptions -fno-rtti`）；③ 不需 C++ 标准库：`grep -nE '^#include *<(vector|string|iostream|…)>'` 两文件无匹配（rc=1）；`<vector>` 探针 rc=1（`'vector' file not found`）⇒ 结论有鉴别力。二者均需目标 C 库头（picolibc 配置/端序/`jmp_buf` arch 移植归 INFRA-057t，已在遗留区显式登记，非静默跳过）。
- 孤儿/工具：`ls …/bin/ | grep -c 'tmp'` = 0；`clang/llc/lld/ld.lld/llvm-mc/FileCheck/llvm-lit/llvm-objdump/llvm-objcopy/llvm-readobj/not/qemu-system-dadao` 全部在位（未误删）。
- 未触发重建：`<build>/llvm/bin/clang-23` mtime=`2026-10-11 00:32:06`，早于本任务窗口（日志/证据 18:11–18:27），且我重跑 install-host 前后 mtime 不变 + `ninja: no work to do` ⇒ 判定未重建。
- 证据脚本五项合格：一键可跑、每断言可达 FAIL、结构断言（软链/inode/配方行/错误串）、计数现场统计（`TOTAL/FAILS`、`wc -l`、`find|wc -l` 不写死）、退出码直捕。**独立注入**（与 engineer「删行」不同：`ln -sf` 源改为不存在的 `clang-NOEXIST`）：`cp`+md5 备份（`ae89d4f5…`）→ 重跑同一脚本 rc=1（`[FAIL] makefile-wiring … rc=1`，8/11）→ `cp` 还原 md5 一致 → 重跑 `install-host` 修回落点（注入态曾写入悬挂链）→ 脚本回绿 11/11 rc=0。
- 快照对账：审前/审后 `git status --porcelain -uall` 逐行相同（`M Makefile`/`M milestones.md`/M 任务书），3 文件 md5 前后一致；与完成区「修改文件」相符；无 `*_tmp*`/`*.orig`/`*.rej`。

**findings**：
- （非阻断）`no-cpp-stdlib` 的 `<vector>` 探针判据 `rc -ne 0` 会把 127（clang++ 不可执行）也算 PASS（注入态实测 `vector_rc=127` 仍 PASS）；建议收紧为「rc=1 且错误含 `'vector' file not found`」。
- （非阻断）注入态 `install-host` 会把悬挂链写进安装落点，还原须重跑 `install-host`（本轮已处置；注入流程注意项）。

**约束核验**：不引入 C++ 标准库 ✔（含鉴别力证据）；依赖 INFRA-050t 产物不重复构建 ✔（ninja no work）；只动任务范围 ✔（`git diff` 仅 Makefile +1 配方行 +6 注释行）；计数不写死 ✔；探针/临时物仅在 `<tmp>`、未入仓 ✔。

**判决：Accepted** —— 验收 1–5 在我独立重跑下全部通过，无阻断 finding；2 条非阻断建议供 INFRA-057t 顺手收紧。
