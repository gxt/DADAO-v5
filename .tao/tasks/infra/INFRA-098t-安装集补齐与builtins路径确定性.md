# INFRA-098t: 安装集补齐（`llvm-nm`/`llvm-readelf`）+ builtins stage 路径对齐 + 归档确定性（`ISS-261`/`ISS-301`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`INFRA-096t`（`build-builtins` + `check-builtins-freshness` 实现，`待验收`）、`LLVM-100t`（`ISS-301` 登记源，`待验收`）、`INFRA-097t`/`INFRA-099t`（**同改 `Makefile`，须串行**）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-096t`（本批另占 `097`/`099`）⇒ 取 **`098`**（编写前 `grep -rn 'INFRA-098' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **`ISS-261`（安装集缺工具，现场实测 2026-10-20）**：安装根 `.dadao/cross-toolchain/bin/` 现场有 `FileCheck clang clang++ ld.lld llc lld llvm-lit llvm-mc llvm-objcopy llvm-objdump llvm-readobj not qemu-dadao qemu-system-dadao`，**缺 `llvm-nm` 与 `llvm-readelf`**（`ls` 两者均 `No such file or directory`）。构建树：`.work/build/llvm/bin/llvm-nm` **存在**（342 MB，2026-10-17），`llvm-readelf` **构建树也没有**（未构建）。
  - `Makefile:323 HOST_LLVM_TOOLS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not llc clang`（不含 nm/readelf）。
  - `Makefile:188 LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen llc lli clang`（不含 nm/readelf ⇒ 需补构建 target）。
  - `ADR-0016 D11` = 「**只装所需工具集**……不做 `cmake --install` 全量安装」（**开放集合**，非封闭清单）⇒ 追加属既有 decision 范围内；**不改 `ADR-0016` 的 decision 文本**（若判必须改 ⇒ 停下报告，按「ADR decision 逐条确认」处理）。
- **`ISS-301` ①（路径不一致，确定可复现）**：`Makefile:415` 的 re-stage 目标 = `$(LLVM_BUILD)/$(BUILTINS_RESOURCE_PATH)`（实测落 `.work/build/llvm/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`）；而 `install-host` 的 `BUILTINS_ARCHIVE_DST` = `CLANG_RESOURCE_DIR`（`Makefile:364`/`384`）与 `tools/infra/check_builtins_freshness.py:342` 读的 `llvm_build/lib/clang/<ver>/<resource_rel>` **是另一路径** ⇒ 重建 clang 后跑 `build-builtins` 不刷新 clang 真正读的那份，门控「build-tree clang copy」项**必红**（必红、非假绿）；上次靠手工 `cp` 两份兜底。
- **`ISS-301` ②（跨构建非字节确定）**：同一源码两次重建归档 sha256 不同（engineer 现场记录 `c96e…` → `fb1b…`，**未留日志**；现盘三副本一致 = `cb7771e5…`）⇒ 「归档 sha 未变 ⇒ 不必重链 `libc.so`」的内容判据失效（现退化为 mtime/戳记）。`ar` 为确定性模式（成员头时间戳 = 0），故候选成因 = `.comment` / 成员顺序 / 构建路径 / 目标文件本身（均需现场证伪，**不预设**）。
- **契约/规范**：`ADR-0016 D11`（install 范围）、`ADR-0016 D9`（安装根为唯一工具来源）、`docs/Process-07 §1.1`（L1 登记表体例：目标 / 层 / 机械判据 / `--self-test` / 成本 / 来源）；`ISS-210`（旧安装根假绿）、`ISS-300`（手工 `cp` 例外手法应收编）。

## 接口规范

- **输入**：`Makefile`（`LLVM_MC_FULL_TARGETS`/`build-mc`/`HOST_LLVM_TOOLS`/`install-host`/`build-builtins`/`BUILTINS_*`/`CLANG_RESOURCE_*`）、`tools/infra/check_builtins_freshness.py`、`tools/infra/check_musl_freshness.py`、`tools/infra/build_musl.py`、`.work/build/llvm`、`.work/build/compiler-rt-builtins`、安装根。
- **输出**：
  1. `llvm-nm`/`llvm-readelf` 进 **构建目标** 与 **安装集**（`HOST_LLVM_TOOLS`）；安装根两者可执行且 `--version` rc=0；
  2. **路径对齐**：`build-builtins` 的 stage 目标与 `install-host` 的 `BUILTINS_ARCHIVE_DST`、checker 读取路径**共用同一派生变量**（一处定义、三处引用）；`Makefile:299-301` 的 D11 注释清单同步；
  3. **确定性结论**：两次 clean 重建的归档 sha256 比较 + 成员级 diff；能修则修到字节确定，不能修则给不可修证据并把重链判据改成**内容级**（成员 sha256 集合）而非「整体 sha」；
  4. 安装集可机械判的检查（`install-host` 内断言或 L1 门控，按 `Process-07 §3` 定层 + 登记表 + `--self-test`）；
  5. 证据 `.work/evidence/<任务ID>/run.sh` + 日志 `.work/log/infra/INFRA-098t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `components/**`（**本册不改补丁**）；不改 `ADR` decision；不 commit/push；**不手工 `cp`** 代替 stage（例外手法正是 `ISS-300` 要收编的）。

## 验收标准

1. **安装集**：`make install-host` 后安装根 `llvm-nm`/`llvm-readelf` 存在、可执行、`--version` rc=0；二者 sha256 == 构建树同名二进制；`llvm-readelf -h` 能正确解析大端 DADAO 对象（如 `.work/source/musl/obj/crt/rcrt1.o`：`ELFDATA2MSB`、`EM_DADAO`）；`llvm-nm` 能列 `.work/build/compiler-rt-builtins/**/libclang_rt.builtins.a` 的符号（14 符号核对场景可复现）。
2. **路径对齐**：`grep` 证明「stage 目标 / `install-host` 目标 / checker 读取路径」来自**同一变量**（不得三处各写）；`make build-builtins`（不手工 cp）后 `check-builtins-freshness` **rc=0**（三份同 sha256）；安装根那份在 `install-host` 后同样 rc=0。
3. **确定性**：连续两次「`ninja -t clean` + `build-builtins`」的归档 sha256 **相同**；或（若不同）给出成员级 diff 定位到具体字段 + 不可修证据 + 内容级判据（成员 sha256 集合）已落地且门控仍能抓住「归档内容变化」。
4. **可达 FAIL ≥ 2**（真实输出 + `cp`+md5 还原回绿）：
   - (a) **修前必红**：`make build-builtins` 后立即 `check-builtins-freshness` ⇒ 红（路径不一致，现场可复现）；
   - (b) **篡改注入**：改安装副本一字节 / 改构建树副本 ⇒ 新检查与既有门控均红（`--self-test` 亦须覆盖）；
   - (c) **安装集断言**：把安装根 `llvm-nm` 临时改名 ⇒ 安装集检查红（还原后绿）；
   - (d) **确定性反例**：若采用内容级判据，注入「成员内容变但整体 sha 未变」不可能；改注入「成员集合变」⇒ 红。若判定可字节确定，注入非确定源（临时改 `ar` 参数/加时间戳）⇒ 两次 sha 不同应被检出（记录真实输出）。
5. **门控**：`make check`(L1) rc=0（含新增检查）；`check-patch-tree`（补丁数不变）；`check-musl-freshness` rc=0（`build-builtins` 变 ⇒ 重链路径仍有效）；`check-run-artifacts` / `check-no-residue` rc=0。
6. **成本**：`build-builtins` / `install-host` 的耗时现场测并写入完成区（安装集 +2 个工具的体积/拷贝成本须如实：`llvm-nm` 342 MB 级 ⇒ 若显著拖慢，给数据交由用户裁定是否只装其一）。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml`：`ISS-301` 按实况回填；`ISS-261` 若安装集落地 ⇒ `closed` + `resolved_by: INFRA-098t`。
8. **不跑** `git commit`/`push`；`install-host` 属长构建（申报耗时，`JOBS=8`）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-098t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（改 `ADR-0016` decision / 决定只装其一 / 接受非确定性）时留问。
6. 复杂命令输出留 `.work/log/infra/`；重建按 `AGENTS.md` 申报耗时、`JOBS=8`、禁全核。
7. **不改 `components/**`**：本册不重建 LLVM 源码，只改构建编排与安装集。

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
