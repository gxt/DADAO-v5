# INFRA-086t: 收口门控三条（契约待定指针 / 重定位类型表一致 / 里程碑 m 册）

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-080t`（门控覆盖补齐，`已验证`；同属「把结论落为机械判据」）；`INFRA-084t`（`check-component-changelog` 同批体例）；`docs/Process-07`（门控分层真源）；`TESTCASES-047t`（B4 的现场红点来源之一）；`ISS-229`（串行禁令）
**状态**：已验证

> **编号说明**：本任务由主会话直接下发（无任务书），工程方已用**临时 ID `INFRA-086t`** 落证据（`.work/evidence/INFRA-086t/`）⇒ 本册按该 ID 补立。`infra` 模块现场最大号 = `INFRA-085t` ⇒ `086` 递增；全仓（含历史）`git log -S INFRA-086t` **0 命中**。

## 执行环境
**执行环境**：本地

## 目标

把 2026-10-17 收口时依赖人工判断的三件事落为**机械门控**（fail-closed + 可达 FAIL），并登记层次与触发点：

| 代号 | target | 判据（机械） | 层 |
|---|---|---|---|
| **A2** | `make check-milestone` | ① 当前里程碑（`milestones.md` 中 `项目里程碑 = M<n>` 断言的**最大 n**）在 `.tao/tasks/**` 有 `m` 册（`<PREFIX>-<nnn>m-*.md`，自报里程碑须一致）；② 该册所列任务号在 `.tao/tasks/**` **或** `.tao/archive/**` 真实存在（册内零任务号 ⇒ vacuous FAIL）；③ 接 `check_tasks.py --strict`（漏收尾 = 0） | **L2 层 / 里程碑收尾专项**（按需；**不入** `check-modules`） |
| **B4** | `make check-contracts-pending` | `.tao/contracts/**` 出现「待…定 / 待裁定 / TODO / TBD」标记的行须**同行**含 `ADR-<n>` / `ISS-<n>` 指针（只认带编号落点）；行内代码跨度与「」引用不计 | **L1** |
| **B5** | `make check-contract-relocs` | `contract-elf.md §2.2` 与 `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内表格行（历史注记/其它小节不参与）；附加自洽 = 表非空 / 号名唯一 / 号 0 起密集 | **L1** |

## 接口规范

- **输入**：`.tao/knowledge/milestones.md`、`.tao/tasks/**`、`.tao/archive/**`、`.tao/contracts/**`。
- **输出**：三个脚本 + `Makefile` target + `docs/Process-07 §1.1` 登记行；**不改**任何契约正文 / 任务状态 / `spec/`。
- **约束**：
  - **fail-closed**：扫描面为空（无里程碑断言 / 无契约文件 / 表被删空）⇒ 非零；
  - **计数现场统计、不写死**（契约数 / 行数 / 任务号数均现场派生）；
  - **禁放宽判据**换绿（如块级指针、删除标记文字）。

## 验收标准

1. 三条门控**各自可达 FAIL**：内置 `--self-test` 反例 + 真实红/绿双证（A2 的「无 m 册」、B4 的 5 处真实陈旧、B5 的单边改号）。
2. **注入 → FAIL → 还原 → 回绿**，还原用 `cp` + md5（禁 `git checkout`/`restore`/`stash`）；临时树优先。
3. 层归属与触发点写进 `docs/Process-07 §1.1`；`check-milestone` **不并入** L1 / `check-modules`（m 册未建前必然红）。
4. 一键证据脚本非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」。

## 完成区

**测试结果**：证据脚本 `.work/evidence/INFRA-086t/run.sh` 现场 **39/39 PASS（rc=0）**（含三条门控 `--self-test` 反例 + `.work/tmp/INFRA-086t/` 临时树注入 + 真实输入 md5 before/after 全等）；日志 `.work/log/infra/INFRA-086t-evidence.log`。B4 **真实红 = 5 处**：`contract-asm-list.md:6,7,309`（生成物）+ `contract-isa.md:1183,1502`；B5 当时已绿（两表 17 行、号 0..16 逐项一致）。
**修改文件**：`Makefile`（3 target + L1 接线）、`docs/Process-07-门控分层规范.md`（新增 §1.1 登记表）、`tools/infra/check_contracts_pending.py`、`tools/infra/check_contract_relocs.py`、`tools/infra/check_milestone_tasks.py`；gitignored 证据 = `.work/evidence/INFRA-086t/{run.sh,self-review.md}`、`.work/log/infra/INFRA-086t-evidence.log`、`.work/tmp/INFRA-086t/`。
**验收结果**：三条门控均**可达 FAIL**（自检 + 真实/注入双证）；层次 = **B4/B5 入 L1**、**A2 = L2 收尾专项**（不入 `check-modules`）；B4 的 5 处真实陈旧**本批已清**（先生成器 `tools/llvm/gen_asm_list.py` 再重生成；`contract-isa.md` 两处改写为定案表述 + `ADR-0012`/`ADR-0014` 指针）⇒ `check-contracts-pending` / `check-asm-list-drift` / `check-asm-list-consistency` 回绿。
**新发现/坑**：① A2 只断言「当前里程碑 **≥1** 个 m 册」，不按模块各一册（口径已披露，未扩张）；② `check-milestone` 在 m 册未建前**必然红**（设计如此，故不入日常层）；③ B4 红点含**生成物** ⇒ 须改生成器 + 重生成，**不得手改**；④ 改 `SECTION_BADGES` 会连带 `spec/` 内嵌块（只读册）⇒ 生成器用 `CONTRACT_BADGES` 覆盖，`_section_content()` 保持原样。
**遗留问题**：本册 `**状态**` 保持 `待开始`（收尾 / 独立验收由 reviewer 与主会话推进）；A2 的「每模块一册」是否升级为断言属**口径裁定**，未自扩张。

### 补记：`check-musl-freshness` 假红修复（`ISS-263`，2026-10-17 23:08–23:16）

**现场（逐字）**：用户 L2 现场 `make check-musl-freshness` ⇒ `[FAIL] toolchain stamp == current clang/ld.lld: expected=equal actual=different`，其余 7 项全 PASS（`installed libc.so == build libc.so` sha256 `d5fa2da3…`、source stamp 一致）。逐项对比 stored/current：`clang` 仅 `ctime` 不同（`1792248160137176763`→`1792249700261026265`），`size`/`mtime`/版本串全等；`ld.lld` 同形。
**根因**：`build_musl.py::toolchain_stamp()` 把 `st_ctime_ns` 计入戳记，而 `ctime` 是 **inode 元数据、不是内容属性**；`make install-host` 走 `Makefile::atomic-install`＝`cp -aL` + `rename(2)`，**同字节重装也落新 inode/新 ctime**（mtime 保留）⇒ 同内容重装被判「toolchain changed」。
**修法（判据层）**：① `toolchain_stamp()` **去掉 `ctime`**，保留 `size` + `mtime` + `--version` 版本串；未改用 sha256 的理由 = clang 4.0 GB + lld 2.0 GB（>6 GB I/O）与「无条件低成本门控」冲突，且真实换工具链必然改 mtime/版本串（已写入脚本注释）。② `check_musl_freshness.py` 就地补注释固化判据原则（**只用稳定内容属性**），未新开文档。③ **真判据未削弱**：`libc.so`/`libc.a` 内容 sha256、source stamp、安装副本 == 构建产物全部保留。
**重建戳记**：`make build-musl-shared JOBS=8` **rc=0**（20.8 s，全量 clean：`toolchain stamp changed` + `source stamp unchanged`）⇒ 新戳记无 `ctime`；`libc.a` sha256 `a65c3351…`、`libc.so` `d5fa2da3…` **与重建前逐字节相同**（mtime 23:10:41/42）。
**双向自检（同次前台闭合，`cp -a`+md5/mtime 还原）**：**真变必红** ① 安装根 `clang` ← `ld.lld`（内容/尺寸/版本不同）⇒ gate **rc=1**、恰报 `toolchain stamp` 行；② 安装 `libc.so` 追加 1 字节 ⇒ gate **rc=1**（sha256 `d5fa2da3…`→`04ffec04…`）。**假变必绿** ③ `shutil.copy2`+`os.replace` 重拷 `clang`（同字节/size/mtime，**ctime 变化**）⇒ gate **rc=0**；④ 同法重拷安装 `libc.so` ⇒ gate **rc=0**；四处均还原并复核 md5/mtime 全等，末轮 gate rc=0。
**验收结果**：`check-musl-freshness` **PASS**（7→8 项全绿）；证据 `.work/evidence/ISS-263/run.sh` default **rc=0**、`--inject` **rc=0**（2 min 07 s，含 I1–I4）；门控各 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)。
**修改文件**：`tools/infra/build_musl.py`（`toolchain_stamp` 去 `ctime` + 判据注释）、`tools/infra/check_musl_freshness.py`（判据注释/文档串）、`.tao/knowledge/issues.yaml`（`ISS-263`，`closed`/`resolved_by = INFRA-086t`）、本册；gitignored：`.work/log/infra/ISS-263-build-musl-shared.log`、`.work/evidence/ISS-263/`。
**新发现/坑**：① `ctime` 对「同字节重装」敏感（`cp -a` 保 mtime 但必然刷新 ctime）⇒ **不得**进入新鲜度判据；② 「sha 不变」不能证「未重建」——本轮重建前后两产物 sha 逐字节相同，重建证据只能是 mtime + 构建日志。
**遗留问题**：待 reviewer 独立复核；本册 `**状态**` 保持 `待开始`（未改），未 commit/push。**披露**：本次重建（23:10:41/42）晚于 `TESTCASES-046t/047t` 的 4 组复跑（22:44–23:02），但 `libc.a`/`libc.so` sha256 与复跑时**逐字节相同** ⇒ 那 4 组数字不受影响（未重跑，按派单不加跑）。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-17，临时 ID 批）

逐条记录（F1–F7 与判决）见 `.work/evidence/INFRA-086t/self-review.md`（**逐字保留**）。要点：F1/F5 = 门控照出的**既有陈旧**（B4 5 处），当时按「禁改 `.tao/contracts/**`」**如实报红、未顺手改**；F2 = A2 不按模块各一册；F3 = `check-milestone` 不入 `check-modules`（设计）；F4 = 册内自身 ID 也计入任务号（不影响幽灵号检出）；F6 = 当前里程碑取断言最大值；F7 = 临时树注入 + md5 对账。判决 = 三条门控已实现且各自可达 FAIL，无本任务交付面未修 finding；F1/F5 由 architect 另批处置（即本任务 B4 清理批）。

#### 第 1 轮 reviewer 验收（2026-10-18）

**重跑**：`run.sh` default rc=1（40 checks / 1 FAIL = A2 no-book 测试过期：INTEG-036m m-book 已存在，删 INFRA-900m 后临时树仍有 m-book ⇒ 预期红变实际绿）。**脚本 stale**，非门控缺陷。

**独立复核三条门控**：
- B4 `check_contracts_pending.py` rc=0（12 契约 / 3785 行 / 0 待定标记）✅
- B5 `check_contract_relocs.py` rc=0（两表各 17 条 / 号 0..16 一致）✅
- A2 `check_milestone_tasks.py` rc=0（M8 有 INTEG-036m m-book / 38 任务号全存在）✅

**Makefile 链路**：B4/B5 入 `make check`(L1) ✅；A2 = milestone closure 专用 target（不入 L1）✅。

**独立注入（2 次）**：
① B4 临时树注入 bare `TODO`（无编号指针）→ rc=1 + `VIOLATION: contract-abi.md:358` → 还原 → rc=0 ✅
② B5 临时树注入 name drift（`REL26→REL20`）→ rc=1 + 2 项 `VIOLATION` → 还原 → rc=0 ✅

**门控**：`make check`(L1) rc=0；`check-patch-tree` 180/0；`check-milestones-fresh` rc=0。

**判决**：**Accepted**。三条门控均可达 FAIL、层次正确、L1 链路完整。证据脚本 A2 测试因 INTEG m-book 存在而过期（脚本设计假设仅 INFRA 有 m-book），属脚本 stale，非交付缺陷。

#### 第 2 轮 engineer 自审（`ISS-263` 假红修复，2026-10-17 23:08–23:16）

逐行审查 `toolchain_stamp()` 的字段选取、`check_musl_freshness.py` 的判据注释与 `run.sh` 的四处注入/还原路径，并以 default + `--inject` 各一次真实执行对齐（非抽样）。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 改格式后旧戳记（含 `ctime`）与新戳记必然不等 ⇒ 升级后首次 gate 红 | ✅已处置 | 按要求 `make build-musl-shared JOBS=8` | `stamp changed` ⇒ `make clean` 全量（20.8 s）；重建后 8/8 PASS |
| F2 | 去 `ctime` 是否放过「同 size+同 mtime、内容不同」的真变 | ✅按证据接受 | 未改判据；理由写入脚本注释（支持路径下不可达；真换链必改 mtime/版本串） | I1（`clang`←`ld.lld`：内容/尺寸/版本不同）⇒ gate rc=1 恰报该行 |
| F3 | I1 注入 `cp -aL` 是否会写穿 `ld.lld` 符号链接（连带破坏工具链） | ✅已验证 | 未改（`cp -aL` 解引用源、目标 `clang` 是普通文件） | `bin/lld` md5 `cfd64e80…` == 构建树；`clang` 还原 md5 `854dd25e…`、mtime 1792243323 不变 |
| F4 | 还原若丢 mtime ⇒ 戳记仍红，注入无法回绿 | ✅已验证 | `cp -a` 备份/还原 | I1/I2 的 md5 与 mtime 逐项相等，还原后 gate rc=0 |
| F5 | 判据需「真变必红 × 假变必绿」双向可达 | ✅已验证 | 新增 I1–I4 | I1/I2 红（toolchain / sha256）；I3/I4（仅 ctime 变）绿；末轮 gate rc=0 |
| F6 | 新 issue 字段约束（`closed` 必填 `resolved_by`） | ✅已验证 | `ISS-263`：`closed` / `resolved_by = INFRA-086t` | `check_issues` rc=0（24 closed → 非空 / 62 open → null） |
| F7 | 重建后两产物 sha 与重建前逐字节相同 ⇒ 不能用 sha 证「已重建」，且重建晚于 4 组复跑 | ✅已披露 | 未重跑 4 组（字节相同，数字不受影响） | `libc.a` `a65c3351…`、`libc.so` `d5fa2da3…` 重建前后同值；mtime 23:10:41/42；册内「披露」行 |

判决：无未修 finding；`check-musl-freshness` 由假红转 PASS，真判据未削弱。按派单**未改**本册 `**状态**`（仍 `待开始`）、未 commit/push。
