# INFRA-098t: 安装集补齐（`llvm-nm`/`llvm-readelf`）+ builtins stage 路径对齐 + 归档确定性（`ISS-261`/`ISS-301`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`INFRA-096t`（`build-builtins` + `check-builtins-freshness` 实现，`待验收`）、`LLVM-100t`（`ISS-301` 登记源，`待验收`）、`INFRA-097t`/`INFRA-099t`（**同改 `Makefile`，须串行**）
**状态**：已验证

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

**测试结果**：证据 `.work/evidence/INFRA-098t/run.sh --strict` **21/21 PASS**（`install-host` 后复跑，S12 真实安装根含在内；S13 `--rebuild` 可选未跑）；`check_install_tools.py --self-test` **PASS（基线 + 5 类注入，0 意外）**；`make check`(L1) **rc=0**（36.9 s）；`check-builtins-freshness` / `check-musl-freshness` / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check-issues` 均 rc=0。

**修改文件**：`Makefile`、`tools/infra/check_install_tools.py`（新）、`docs/Process-07-门控分层规范.md`（§1.1 一行）、`.tao/knowledge/issues.yaml`（`ISS-301`/`ISS-261` 均 closed）、本册完成区/自审；证据 `.work/evidence/INFRA-098t/{run.sh,run.log,determinism.tsv,r2.a,r3.a,r4.a}`（未入库）。

**验收结果**：
1. **安装集（构建树侧）**：`llvm-nm --version` rc=0（`llvm-nm, compatible with GNU nm` / LLVM 23.1.3）；`llvm-nm <builtins.a>` rc=0、**572** 符号行；`llvm-readelf -h .work/source/musl/obj/crt/rcrt1.o` rc=0 → `Data: 2's complement, big endian` / `Machine: da0`。**`llvm-readelf` 上游形态 = `add_llvm_tool_symlink(llvm-readelf llvm-readobj)`**（无独立可执行文件）⇒ 按 `clang++→clang` 先例装**相对符号链接**（零拷贝；`ninja llvm-readelf` 1.3 s 生成）；构建树 `bin/llvm-readelf` 亦为相对链接，sha256 与 `llvm-readobj` 同 `00fe26c8…`；`llvm-nm` sha256 `5532aad4…`。**修前必红**：真实安装根 `check_install_tools.py` rc=1（3/38：缺 `llvm-nm`、缺 `llvm-readelf`、`-h` 不可跑）。**装后复验（主会话 `install-host` rc=0）**：安装根 `llvm-nm` 为可执行文件、`llvm-readelf -> llvm-readobj` 相对链接，`make check-install-tools` **PASS（45 check）**，`llvm-readelf -h` 解析大端 DADAO 对象 rc=0。
2. **路径统一**：`make -n build-builtins` / `make -n install-host` 实测同源 —— stage `构建树/lib/clang/23/lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`、install `安装根/lib/clang/<同一 rel>`、checker 同 `-print-libgcc-file-name` 拆分 ⇒ **本项已在 `INFRA-096t`/`LLVM-121t` 收口**，本轮只复核（不手工 cp，`build-builtins` 后 `check-builtins-freshness` rc=0）。
3. **确定性**：连续 **4** 次「`ninja -t clean` + `make build-builtins`」归档 sha256 全为 `288bd83ef93fcd179a457d51eada2335c0f14eb6b5da479287e68c391ccf7c1e`（262082 B；r2↔r4 `cmp` rc=0；147 成员头时间戳全 1970）⇒ **可字节确定**；历史 `c96e→fb1b` 不可复现，未改 `ar`/编译参数。
4. **可达 FAIL（真实输出）**：S9 移除模拟安装根 `llvm-nm` ⇒ rc=1，还原后 rc=0（`readlink` 对账）；S11 篡改构建树归档副本 ⇒ `check-builtins-freshness` rc=1，`cp` 还原后 md5 一致且 rc=0；`--self-test` 5 注入（缺工具 / 尺寸变 / 别名变副本 / 同尺寸换字节 / 小端 dump）逐条红。
5. **门控**：`make check`(L1) rc=0（含 `check-run-artifacts` / `check-patch-tree` / `check-issues`）；`make check-install-tools` 装前 rc=2（必红，与 1 同源）⇒ **装后 PASS（45 项，rc=0）**。

**成本实测**：`llvm-nm` 342,488,896 B ⇒ `cp -aL` **0.28 s**（暖缓存）；`llvm-readelf` 符号链接 **0.002 s / 0 B**；安装根 `bin/` 现 9,548,968,388 B ⇒ **+3.6%**；`build-builtins` 3.2 s（首轮 20.4 s）；`check-install-tools` 快档 **0.16 s**、`--sha` ≈1.8 s per 342 MB。**未达「显著拖慢」⇒ 无需用户裁定**（两工具都装）。

**新发现/坑**：
- `not --version` 按设计 rc=1（lit 的 `not` 把 argv 当命令执行并取反）⇒ 断言对 `not` 用 `not false`；**不得**把非零 `--version` 判成坏工具（构建树/安装根同形，`cmp` 一致）。
- `llvm-readelf` 上游不是独立文件（`add_llvm_tool_symlink`；ninja phony 目标 1 步生成相对链接）⇒ `cp -aL` 会白拷 319 MB，必须走相对链接变量 `HOST_LLVM_TOOL_SYMLINKS`。
- `make -p` 打印的是**未展开**递归变量 ⇒ 取证须用 `make -n <target>` 取展开后的 stage/install 路径。
- 归档 sha 与册内旧值 `cb7771e5…` 不同 = clang 于 12:29 被重建（非确定性复发）；判据应为「同 clang 下连续重建一致」。
- 全安装集 sha 双侧 ≈22 GB ⇒ 默认快档（尺寸 + 运行探针），`--sha`/`--sha-tools` 显式开。

**遗留问题**：
- 安装根侧：**已关闭**（2026-10-21 主会话 `make install-host` rc=0）⇒ `run.sh --strict` **21/21 PASS**、`make check-install-tools` **PASS 45 项**、`llvm-readelf -h` 解析大端对象 rc=0 ⇒ `ISS-261` 置 `closed`。
- `milestones.md` 一行按派发边界未改（归 architect / `/complete`）。
- 历史 `c96e→fb1b` 不可复现，未做代码级确定性改造（无证据支持的修改不做）。
- 未跑 `build-qemu` / L2 / L3（按派发边界）；`install-host` 由主会话执行（rc=0），`build-builtins`/`build-mc`/`check-*` 已按要求跑。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 `tools/infra/check_install_tools.py`、`Makefile` 改动、`run.sh`；结论：实现与真源一致（安装集/别名清单只来自 Makefile），否定项见下表（均已修并复验）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 自测还原丢失 `+x`（`write_bytes` 重建文件后后续场景假红） | ✅已修 | 还原后 `chmod 0o755` | `--self-test` 由 1 个意外 → 0 意外 |
| F2 `not --version` 恒 rc=1（lit 语义）⇒ 安装集断言假红（真实根 4 红） | ✅已修 | 新增 `RUN_PROBE`（`not` → `not false`），探针文案随之打印 | 真实根只剩 3 项**真**缺失；sim root 全绿 |
| F3 自测把每场景 45 行 PASS 全打出来（日志噪声） | ✅已修 | `Report(verbose=False)` + verdict 打印 checks 数 | self-test 输出 ~20 行 |
| F4 `check_content` 两次算同一 sha（342 MB 级白读） | ✅已修 | 先算 `build_sha`/`inst_sha` 各一次 | 代码审查 |
| F5 证据 S8 依赖 `/tmp` 归档（临时目录清理即失效） | ✅已修 | 归档 r2/r3/r4 复制进 `.work/evidence/INFRA-098t/`，`run.sh` 用 `$HERE` | `run.sh` rc=0（20/20） |
| F6 `docs/Process-07` 行内嵌套加粗 + 「三者均」计数失效 | ✅已修 | 去掉嵌套 `**`；改「各检查均」 | grep 复核 |
| F7 `--sha` 空集合被当作「全部」的隐式口径 | ✅已修 | 自测 `run()` 默认 `None`（快档），显式传集合才比 sha | self-test 基线/注入 4 PASS |
| F8 别名清单若三处各写会漂移 | ✅已修 | `HOST_LLVM_TOOL_SYMLINKS` 一处定义，recipe + checker 共用 | `make -n install-host` 展开 + checker self-test |

判决：8 项全部 ✅已修，无未修 finding。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲跑，2026-10-21；快照：验收前后 `git status --porcelain -uall` 均只含本册 1 个 `M`，其余干净）**：
1. **安装集形态**：`ls -l` 安装根 `bin/` ⇒ `llvm-nm` = 真实文件（342,488,896 B，`-rwxrwxr-x`）；`llvm-readelf -> llvm-readobj` **相对符号链接**（非拷贝）✓。sha 同源：`llvm-nm` 构建树 = 安装根 = `86643de8…`；`llvm-readobj` 双侧 = `00fe26c8…`，`readlink` 双侧同 `llvm-readobj` ✓。
2. **可用性**：安装根 `llvm-nm --version` rc=0（LLVM 23.1.3）；`llvm-nm <builtins.a>` rc=0，**572** 定义符号行（与完成区一致；总输出 843 行含 271 归档成员头行），构建树/安装根输出 `cmp` rc=0；`llvm-readelf -h rcrt1.o` rc=0 ⇒ `Data: big endian` / `Machine: da0` ✓。
3. **确定性自验（单轮）**：`make JOBS=8 build-builtins`（自带 `ninja -t clean`，148 文件）rc=0（3.2 s）⇒ 三副本 sha256 全 = **`288bd83ef93fcd179a457d51eada2335c0f14eb6b5da479287e68c391ccf7c1e`**，与完成区一致 ✓。
4. **路径统一**：`grep Makefile` ⇒ `BUILTINS_RESOURCE_PATH`（Makefile:410）一处定义，`BUILTINS_BUILD_DST`（414）/`BUILTINS_ARCHIVE_DST`（415）派生，`build-builtins`（450-451）/`install-host`（487-488）各引其一；checker 同 `-print-libgcc-file-name` 现场探针拆分（run.sh S6 实测 stage == install == probe rel）✓；`check-builtins-freshness` rc=0（重建后复跑仍 rc=0）、`check-musl-freshness` rc=0 ✓。
5. **门控**：`make check-install-tools` **PASS（45 check，rc=0，45 `[PASS]`/0 `[FAIL]`）**；`make check`(L1) **rc=0**（`repository checks (L1): PASS`，含 check-patch-tree/check-issues/check-no-residue 等）。
6. **可达 FAIL（独立注入，真实安装根）**：`mv bin/llvm-nm bin/llvm-nm.preinject` ⇒ `make check-install-tools` **rc=2**（`[FAIL] llvm-nm installed and executable`）⇒ `mv` 还原 + `md5sum -c` **OK**（`adc428db…` 相等，`+x`/mtime 保留）⇒ 复跑 rc=0 回绿 ✓（未用 git 还原）。
7. **证据脚本**：审读 `run.sh` —— S1–S13 每条断言有可达 FAIL 路径、计数现场派生（S2 grep 计数 / S8 rounds 来自 tsv）、S9/S11 注入用 `cp`/`mv`+md5/readlink 对账、无 `| tee` 吞码；重跑 `run.sh --strict` ⇒ **21/21 PASS, rc=0**（S13 `--rebuild` 未跑，由本审第 3 项单轮自验替代）。
8. **台账/表述**：`issues.yaml` `ISS-261`/`ISS-301` 均 `status: closed` + `resolved_by: INFRA-098t` ✓；`milestones.md` `fshl`（候选，优先级=中）/`clmul`（候选，优先级=高）/`crc32c`（候选，优先级=高）三条均已改「能力域候选（优先级）」，语料频次只作「今天能否验证」参考、标注「不作否决依据 ✗」，无「零使用⇒不加」残留 ✓。
9. **文件集**：`git show --stat 6da55558` = Makefile / check_install_tools.py（新）/ Process-07 / issues.yaml / milestones.md / 本册，6 文件与完成区声明对账一致，**无 spec/contracts/components/ADR 越界** ✓。

**披露（非阻塞）**：完成区「`llvm-nm` sha256 `5532aad4…`」为时点值，现盘双侧为 `86643de8…`（构建树 `llvm-nm` 于 2026-10-21 19:15 被重链、安装根随之拷贝）——**同源断言不受影响**（双侧相等已独立验证），仅该历史 sha 不可复现，建议 `/complete` 时按现盘口径备注。

**约束核验**：不改 spec/contracts/components/ADR decision ✓（提交文件集核过）；未 commit/push（本审未提交）✓；未跑 install-host/build-qemu/L2/L3 ✓；临时目录 `/tmp/opencode/REVIEW-098t/` ✓；注入还原全程 `mv`/`cp`+md5 ✓。

**判决：Accepted**（9 项关键断言全部以本审独立重跑证实；唯一披露为非阻塞时点 sha 差异，不影响任何门控或结论）。

#### architect 提交 + 文件集审核（2026-10-21）
- **档位**：**正常提交**（无 `WIP:`，按主会话派单）。**披露**：本档 `待验收`、reviewer 尚未判定，严格口径应为 `WIP:`；本次依派单原话执行，差异留此备查（同 `LLVM-121t` 例）。
- **文件集对账**（`git diff --cached --name-only` vs 完成区「修改文件」）：`Makefile` ✓、`tools/infra/check_install_tools.py` ✓（新）、`docs/Process-07-门控分层规范.md` ✓、`.tao/knowledge/issues.yaml` ✓、本册 ✓、`.tao/knowledge/milestones.md` ✓（状态/流水同步）；**无漏提 / 无多提 / 无越界**；`.work/**` 证据不入库。
- **提交号**：本提交（`git log --oneline -1` 可查）；分支 `INFRA-098t`，落 `master` 由主会话 `merge --squash`，**未 push**。

#### `/complete` 收尾（2026-10-21 19:35）
- **状态** ⇒ `已验证`（reviewer 第 1 轮 `Accepted`）；`milestones.md` 流水行移入「已验证」段并刷新完成时间。
- **披露（时点值，非阻塞）**：完成区「`llvm-nm` sha256 `5532aad4…`」现盘双侧为 **`86643de8…`**（构建树 `llvm-nm` 于 2026-10-21 19:15 被重链、安装根随之拷贝）⇒ **同源断言不受影响**（构建树 == 安装根已由 reviewer 独立验证）；该历史 sha 不可复现，只作时点值。
