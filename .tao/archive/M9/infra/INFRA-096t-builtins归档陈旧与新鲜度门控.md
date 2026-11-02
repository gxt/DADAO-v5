# INFRA-096t: compiler-rt builtins 归档陈旧（`ISS-293` 真根因）+ 新鲜度门控

**模块**：infra
**项目里程碑**：M9
**依赖**：`INFRA-079t`（builtins 独立库 + 安装落点，已验证）、`INFRA-088t`（driver 自动接线 `-print-libgcc-file-name`，已验证）、`LLVM-116t`（`ext`/`shl` 编码迁移，`待验收`）、`QEMU-064t`（新解码表，`待验收`）、`ISS-293`（本册关闭）、`ISS-258`/`ISS-263`（musl 新鲜度门控先例）
**状态**：已验证

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-095t` ⇒ 取 **`096`**（`grep -rn 'INFRA-096' .tao/` 0 命中）。
> **关系**：`ISS-293` 原判「旧 ELF 不兼容」**不完整** —— 旧 ELF 只是**现象**；真根因 = **compiler-rt builtins 归档从未随编码迁移重建**（`QEMU-065t` 复核时定位）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

- **现象**：新建 `qemu-dadao` 跑 047t `functional/snprintf`（静态）/`functional/strtod`（动态）⇒ 宿主 SIGILL（rc=132）；旧 qemu 跑同一 ELF 通过。
- **旧编码残留（三处归档同源）**：`extenddftf2.c.o` 内仍有 **已废止 `shl` 编码 `40 50 51 46`**（`ha=0x14`，`llvm-objdump` 显示 `<unknown>`）×3；整个构建树归档 **40** 处、构建树 clang 资源目录副本 **24** 处、安装根副本 == 旧构建树产物（sha256 `6057c89f…`，mtime 10-18 20:36）。现 clang 发 `shl` 为 `40 40 51 46`（`shl.o rd5, rd5, rd6`）。
- **三个消费点**（都真被链接）：① 构建树产物 `.work/build/compiler-rt-builtins/lib/<triple>/libclang_rt.builtins.a`；② **构建树 clang 自身资源目录**（`.work/build/llvm/lib/clang/<ver>/lib/<triple>/…`，`clang -### ` 的链接行里就是它；**没有任何规则维护它**）；③ 安装根（`make install-host` 拷贝，**无条件覆盖**，无「已最新即跳过」）。
- **第五环：`libc.so` 内嵌 builtins** —— musl 共享链接以 `LIBCC=<archive>` + `--exclude-libs=ALL` 把 builtins 成员**吃进 DSO**；`build_musl.py` 的 toolchain/source 戳记都**看不见**归档内容（归档是链接输入、非编译输入）⇒ 归档重建后若不重链，动态档继续执行旧编码（`qemu -d in_asm` 末块 `construct_dst_rep` 停在被废止的 `40 50 41 05`）。**静态档不受影响**（builtins 在程序链接行上单独出现）。
- **`ar` 是确定性模式**：成员头时间戳为 0（`ar tv` 显示 1970），故「成员级陈旧」只能按成员名回查构建树 `.c.o` 的 mtime。
- **同名陷阱**：`.work/build/compiler-rt-builtins/lib/linux/libclang_rt.builtins-dadao.a`（3.4 KB，`INFRA-079t` 的最小集遗留）会被旧 `firstword $(wildcard …)` 命中排序影响；`build_musl.py` 的 `LEGACY_COMPILER_RT_BUILTINS` 也指向它。

## 接口规范

- **输入**：`.work/build/llvm/bin/clang`（现工具链）、`.work/build/compiler-rt-builtins/`（已配置的 compiler-rt standalone 构建树）、`Makefile::install-host`、`tools/infra/{build_musl.py,check_musl_freshness.py}`、`docs/Process-07 §1.1`。
- **输出**：
  1. `make build-builtins`：`ninja -t clean` + `ninja builtins`（**强制**走当前 clang）+ 把归档 stage 进构建树 clang 资源目录；
  2. `install-host` 依赖 `build-builtins`，且 `BUILTINS_ARCHIVE_SRC` 改为 `<build dir>/<driver 报告的相对路径>`（消除 `lib/linux` 同名陷阱）；
  3. 新门控 `tools/infra/check_builtins_freshness.py`（L1）+ `--self-test`（四类注入）；
  4. `build_musl.py` 增 **builtins 戳记**（`obj/.dadao-builtins-stamp`）：归档内容变 ⇒ 删除 `lib/libc.so` 触发重链（不 `make clean`）；`check_musl_freshness.py` 增第 7 项比对；
  5. 证据 `.work/evidence/INFRA-096t/run.sh`（一键、逐项 rc、含注入与还原）+ 日志 `.work/log/infra/INFRA-096t-*.log`。
- **约束**：**不改** `spec/`/`contracts/`/`components/**`/`tests/vectors/**`；**不跑** `install-host`（主会话跑）/`build-qemu`/L2/L3；**不** commit/push。

## 验收标准

1. **重建**：`make build-builtins` rc=0；归档内 `40 50 51 46` **计数 0**；符号集不回退（成员数 / `T` 符号数 / 未定义数 / 代表性 TF+libcall 符号齐）。
2. **三份副本**：构建树产物 == 构建树 clang 资源目录副本（sha256）；安装根一份由主会话 `install-host` 覆盖（本册只证「规则会覆盖」，并给出待装状态的真值）。
3. **门控**：`check-builtins-freshness` 断言「三份同内容 + 不旧于 clang（归档 mtime + 逐成员 .c.o mtime）」；`--self-test` 双向（篡改安装副本 ⇒ 红；仅 mtime 变 ⇒ 不假红）；挂 L1 + `docs/Process-07 §1.1` 一行。
4. **动态链**：`libc.so` 以新归档重链后，047t `functional/snprintf`（静态）/`functional/strtod`（动态）**转 pass**（`--json-out` 落 `/tmp`；动态以构建树 clang + 重链副本模拟「install-host 之后」）。
5. **复发防护**：归档变而未重链 ⇒ `check-musl-freshness` 红（第 7 项）。
6. **门控**：`make check`(L1) / `check-patch-tree`(183) / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check_issues.py` 各留 rc；未过者给「真值 + 原因 + 何时转绿」。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` `ISS-293` 处置。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/builtins-freshness/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp`+md5）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。

## 完成区

**测试结果**：证据 `.work/evidence/INFRA-096t/run.sh` **rc=0（全项 PASS，42 条 `[PASS]`）**：`build-builtins` rc=0（`real 3.4 s`，含 `build-mc` 前置；纯重建 1.6 s）；归档旧编码 `40 50 51 46` 计数 **0**（构建树克隆副本同 0）、`extenddftf2.c.o` 的 `<unknown>` **0** 且 `shl.o` **5** 条；符号集**不回退**（147 成员 / 165 `T` / 357 未定义 / 780 定义，定义符号集与修复前归档 `cmp` 相等）；门控 `--self-test` 7/7（基线 + 4 注入，含「仅 mtime 变 ⇒ 不假红」）；真树注入（追加字节到构建树副本）⇒ 门控 rc=1 且 sha256 项 `[FAIL]` ⇒ `cp`+md5 还原（`925bb32e…`）⇒ 回绿；047t 10 例静态 **10/10**、动态 **10/10**（`functional/snprintf` 静态 pass、`functional/strtod` 动态 pass）。
**修改文件**：新 `tools/infra/check_builtins_freshness.py`；`Makefile`（`build-builtins` 目标 + `install-host` 依赖它 + `BUILTINS_ARCHIVE_SRC` 改按驱动相对路径 + `check-builtins-freshness` 入 L1 + 2 行 help）；`tools/infra/build_musl.py`（第 3 戳记 + 重链）；`tools/infra/check_musl_freshness.py`（第 7 项）；`docs/Process-07-门控分层规范.md` §1.1；本册（新增）；`issues.yaml`（ISS-293）；`milestones.md`（流水 + 未完成册各一行）；证据 `.work/evidence/INFRA-096t/run.sh` + 日志 `.work/log/infra/INFRA-096t-*.log`。`components/**`、`tests/vectors/**`、`spec/`、`contracts/` **0 改动**。
**验收结果**：`check-patch-tree` rc=0（5 组件 **183** patches，未变）、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`check-no-residue` rc=0、`check_issues.py` rc=0（52 open / 13 closed，`resolved_by` 约束 OK）、`check-milestones-fresh` 复跑 rc=0。`make check`(L1) **rc=2，2 红且均为真值**：① `check-builtins-freshness`（安装根副本仍旧 `6057c89f…` ≠ 新 `18c0cac1…`）——`install-host` 归主会话；② `check-musl-freshness`（builtins 戳记缺失，且现值 `6057c89f…` 证 `libc.so` 内嵌的正是旧归档）——需 `install-host` 后 `make build-musl-shared`（戳记变 ⇒ 自动重链）。二者在「`install-host` → `build-musl-shared`」后预期转绿（本册**不跑**这两步）。
**新发现/坑**：① 归档有**三个**消费点，中间那个（**构建树 clang 资源目录副本**）无任何规则维护，`clang -###` 明确链接它；② `libc.so` 以 `LIBCC`+`--exclude-libs=ALL` **内嵌** builtins ⇒ 只重建归档**不够**，动态档必须重链（副本实测：重链前 12 处旧编码 / `strtod` SIGILL，重链后 0 处 / pass，静态档全程不受影响）；③ `ar` 确定性模式（成员 mtime=0）⇒ 成员级陈旧只能**按成员名回查 `.c.o`**（`gcc_personality_v0.c.o` 非成员、mtime 旧，按目录扫描会永久假红）；④ `build_musl.py` 取归档走**安装根 clang** 探测，故顺序必须是 `install-host` → `build-musl-shared`；⑤ `/tmp/opencode/**` 之外一律未写（`make` 只动 `.work/build/**` 与本仓库日志）。
**遗留问题**：① 安装根刷新 + `libc.so` 重链**未做**（按派单禁 `install-host`）⇒ 主会话：`make install-host`（自动 `build-builtins`）→ `make build-musl-shared JOBS=8` → 两门控转绿；当前 `.work/source/musl/lib/libc.so` 仍内嵌旧 builtins（12 处），属同一件事。② 未跑 L2/L3、未 commit/push（按派单）。③ 工作树另有 `QEMU-065t` 任务书的**前序未提交改动**（非本册产生，原样保留，提交本册时勿并入）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（`subagent_depth=1`，无嵌套子代理）：核对门控每条断言的可达 FAIL、注入可达性与还原（`cp`+md5，未用 git）、`ar` 解析边界（符号表/长名）、`build_musl` 三条分支（无戳记 / 同戳记 / 戳记变）与失败路径（重链后 `make` 失败 ⇒ 产物缺失可见）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 逐 `.o` 目录扫描把**非归档成员** `gcc_personality_v0.c.o`（陈旧）判 stale ⇒ 永久假红 | ✅已修 | 解析 `ar` 成员名（GNU 长名表）后按名回查 `.c.o` | 实跑 `147/147 members live, 0 stale`；注入 4b 单成员变旧 ⇒ 1 stale |
| 自检判定把期望 `"0 failures"` 与 `"0"` 比较 ⇒ baseline/4a 假红 | ✅已修 | `expected_rc.startswith("0")` | `--self-test PASS (0 unexpected outcome(s))` |
| 只发现构建树产物，漏了**构建树 clang 自己的资源目录副本**（`clang -###` 实测链接它） | ✅已修 | `build-builtins` 增 stage；门控断言三份同 sha256 | gate `build-tree clang copy == build product` PASS |
| 只重建归档时动态档仍 SIGILL（`libc.so` 内嵌旧 builtins） | ✅已修 | `build_musl.py` builtins 戳记 + 重链；musl 门控第 7 项 | `.work/log/infra/INFRA-096t-builtins-stamp.log`：无戳记 ⇒ relink、同戳记 ⇒ 不 relink、变戳记 ⇒ 检测到 |
| 证据脚本 `fi` 与下一条语句误连成 `fiNM=…` ⇒ `bash -n` 语法错 | ✅已修 | 补回换行 | `bash -n` rc=0；脚本 rc=0 |
| `LEGACY_COMPILER_RT_BUILTINS`（`lib/linux` 3.4 KB 最小集）仅作探测失败回退，不改 | ⏸延后（`INFRA-079t` 口径；本册以顺序 + 门控兜住，另在 issue/里程碑记录顺序） | 无 | 证据脚本 8c 记录现值 |
| mtime 判据会随 clang 无关重编而红 | ❌不修（按派单「不旧于 clang」口径；重建 1.6 s、remedy 明确） | 无 | 注入 3 红 / 4a 绿 |
| `build-builtins` 每次 `-t clean` ⇒ `install-host` 每次 +2~3 s | ❌不修（ninja 不感知编译器二进制变化，确定性优先） | 无 | `real 3.4 s`（含 `build-mc`） |

判决：可修 finding 均已处置并复验；余 2 项为有据不修/延后。状态置 `待验收`。

#### 提交审核（architect）

- **档位**：正常提交（按派单；reviewer 未判决，以派单为准）。**未 push**。
- **提交**：`26d6575`（`INFRA-096t：compiler-rt builtins 陈旧修复 …`）；显式 staging **8 路径**，未用 `git add -A`。
- **对账（对完成区「修改文件」）**：`tools/infra/check_builtins_freshness.py`（新增）、`Makefile`、`tools/infra/build_musl.py`、`tools/infra/check_musl_freshness.py`、`docs/Process-07-门控分层规范.md`、本册（新增）、`issues.yaml`（ISS-293 订正 + closed）、`milestones.md`（流水 + 未完成册各一行）= 完成区声明 8 项，逐项对上 ✓；`.work/evidence/**`/`.work/log/**` 属忽略区不入 git ✓。**无漏提 / 多提 / 越界**（`QEMU-065t` 册前序改动未并入）。
- **门控复跑（提交前）**：`check-builtins-freshness` rc=0（三副本同 `18c0cac1…`、147/147 成员 live、0 stale）、`check-musl-freshness` rc=0（builtins 戳记 = 归档）、`check-patch-tree` **183** rc=0、`make check`（L1）**rc=0**（35.6 s）⇒ 完成区「验收结果」中 L1 rc=2 的两红已由主会话 `install-host` + `build-musl-shared` 转绿，本条为复跑实证。

#### 第 1 轮 reviewer 验收

**重跑**（workdir=仓库根；`master=61e7ece`、树净；自跑日志落 `/tmp/opencode/REVIEW-FIX4/`，派单限定临时物；**未**单独调用 `install-host`/`build-musl*`/`build-qemu`/L2/L3，证据脚本内部按其设计调用 `make build-builtins`（派单明示允许跑 run.sh））：
- `bash .work/evidence/INFRA-096t/run.sh` ⇒ **rc=0（0 failures，43 条 `[PASS]`）**。⚠ 完成区写「42 条 `[PASS]`」⇒ 计数差 1（写死计数漂移，非断言缺陷；建议现场派生）。
- **两层根因均落**（读 `Makefile`/`tools/infra/*`）：① `build-builtins` = `ninja -t clean`+`builtins`+stage 进构建树 clang 资源目录（`Makefile:404-415`），`install-host: … build-builtins`（`Makefile:424`）+ `BUILTINS_ARCHIVE_SRC` 按驱动报告相对路径（`:382`，`lib/*` 校验）⇒ 消除 `lib/linux` 同名陷阱；② `build_musl.py` builtins 戳记（归档变 ⇒ 删 `libc.so` 重链）+ `check_musl_freshness.py` **第 7 项**（`builtins stamp == current archive`）——「只重建归档不够」已由戳记兜住 ✓。
- **自跑关键数**：`make build-builtins` rc=0；归档旧编码 `40 50 51 46` 计数 **0**（构建树产物 + 资源目录副本两处）、`extenddftf2.c.o` `<unknown>` **0** / `shl.o` **5** ✓；符号集 **147 成员 / 165 `T` / 357 未定义**、与对照归档 `cmp` 定义符号集相等、代表性 TF+libcall 8 符号齐 ✓（与完成区逐项一致）。
- **门控**（自跑）：`--self-test` **7/7**（baseline + 4 注入 + restore；**含「仅 mtime 变 ⇒ 不假红」**（`ISS-263` 教训）与「1 stale member ⇒ 红」）rc=0；真树 `check-builtins-freshness` rc=0（三副本同 sha256 `5512be72…`、147/147 live、0 stale、install copy == build product）；`check-musl-freshness` rc=0（含第 7 项 builtins 戳记）；`check-patch-tree` **185** rc=0（完成区 183 为当时值，随后 118t/119t/120t 使总数 185，非漂移缺陷）。
- **动态链两用例转 pass**（自跑）：047t 静态 **10/10**、动态 **10/10**（脚本以「重链副本」模拟 install-host 之后）；`functional/snprintf` 静态 `pass exit=0`、`functional/strtod` 动态 `pass exit=0` ⇒ **`ISS-293` 用例面收口** ✓；`libc.so` 重链后旧编码计数 **0**。
- **戳记语义**（自跑，`build_musl` 于 `/tmp` 副本）：无戳记 ⇒ relink（`relinked: True`）、戳记记录新归档 sha256、同戳记 ⇒ 不 relink、归档 digest 变 ⇒ 检测到（`decision after digest change: (True…`）✓。
- **独立注入**（脚本 §6 之外，改**构建树产物**归档追加 1 字节，`cp`+md5 `72754394…` 备份）⇒ `check-builtins-freshness` **rc=1**，2 红（`build-tree clang copy == build product`、`installed copy == build product` 两处 sha256 FAIL，其余全绿）⇒ `cp` 还原（3 份 md5 全 `72754394…`）⇒ 复跑 **rc=0（7 PASS）**。
- 附：`make build-builtins` 重建后归档字节**未变**（`72754394…` 前后一致）⇒ 同 clang 下重建确定；`LLVM-100t`「新发现③ 归档跨构建非字节确定」今日**未复现**（其口径跨 clang 换代）。

**约束核验**：`git show 26d6575 --stat` = 8 文件，与「修改文件」逐条对上（`check_builtins_freshness.py` 新增、`Makefile`、`build_musl.py`、`check_musl_freshness.py`、`docs/Process-07` §1.1、本册、`issues.yaml`、`milestones.md`）；`components/**`/`tests/vectors/**`/`spec/`/`contracts/` **零改动** ✓；`ISS-293` `closed`+`resolved_by: INFRA-096t` ✓；未 commit/push ✓；L1 rc=0（本轮末自跑）。

**判决：Accepted** —— 验收 1–7 逐条达标（重建无旧编码 / 三副本同源 / 门控双向+`--self-test` 7/7 / 动态链两用例转 pass / 复发防护第 7 项 / 门控 rc / 完成区对齐）；「42 vs 43 条 PASS」与 patch 计数 183→185 为时点计数差异（后者有据），非交付物缺陷。

#### 勘误（收尾复核，2026-10-20）

> 收尾时按「计数现场派生」口径订正**写死时点值**；**不改写**既有完成区 / 审阅记录，以本段为准。

1. **`[PASS]` 条数**：实为 **43**（册内完成区「42 条」）——`run.sh` 现场输出计数，非断言缺陷。
2. **`check-patch-tree` 计数**：册内「183」为**时点值**（随后 `LLVM-118t`/`119t`/`120t` 增补丁使总数上升）⇒ 今日现场 **185**（收尾自跑：`check-patch-tree: 5 component(s), 185 patches OK`，rc=0）。
   - 证据：本册「第 1 轮 reviewer 验收」重跑记录（`rc=0 / 0 failures / 43 [PASS]`）+ 收尾自跑 `make check-patch-tree`。
