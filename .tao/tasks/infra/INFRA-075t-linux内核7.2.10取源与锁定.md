# INFRA-075t: Linux 内核 7.2.10 取源与锁定

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`；`D1` = 沿用 RISC-V 编号）；消费方 `SPEC-138t`（Linux syscall 映射契约，只取号表来源指针）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 问题根源 / 立项来源

- **用户裁定（2026-10-14，原话 / 选项标签）**：
  - 「**linux kernel 版本号定为：7.2.10**，安排任务：找个镜像下载该版本」；
  - 取源路线 = **「整包 7.2.10 + 验签（推荐）」**（**不走** base+patch）；
  - 源 = **TUNA 主**（实测 9.6–11.2 MB/s；阿里云 1.9–3.4、kernel.org 2.7–2.9 ⇒ 备源）。
- **动机**：M8 主线 = **无内核的 Linux 用户态栈**（`ADR-0025 D2`）；syscall **号表口径 = 沿用 RISC-V 编号**（`ADR-0025 D1`）⇒ 需 Linux 内核源码的 `asm-generic` + `riscv` 号表作**上游参照**（供 `SPEC-138t` 指针引用）。内核**不是** v5 目标、**不入** v5 组件补丁集。

## 接口规范

- **输入**：TUNA 镜像 URL（主）、`ADR-0025`（路线）、用户裁定（版本 / 路线 / 源）。
- **输出**：
  1. `.work/source/<linux>/` 下**签名 tarball + `.tar.sign` + 解包树**（**不入 git**；`.work/` 已 gitignore）；
  2. `manifests/components.lock.toml` 新增 `linux-kernel` 条目（`version` + `sha256` + 源；**参考型/无补丁集** ⇒ `patchless = true`）；
  3. **号表来源指针**（两文件路径 + sha256 + 行数）写入本任务书（**契约正文归 `SPEC-138t`**，本任务不写正文）。
- **约束**：**不**改 `spec/`、`contracts/`、组件补丁；**不**写契约正文；sha256 / 体积 / 耗时**现场取证**；正文引用 `.work/**` 一律用 `<>` 占位。

## 验收标准

1. 从 **TUNA** 取得 `linux-7.2.10.tar.xz` + `linux-7.2.10.tar.sign`（记录耗时 / 体积 / 退出码），落 `.work/source/<linux>/`。
2. `sha256sum` 现场记录，且与 **TUNA 发布的 `sha256sums.asc` 逐位一致**（独立核对）。
3. **GPG 验签完成**：`xz -dc <tarball> | gpg --verify <sign> -` ⇒ `Good signature`（记录 `gpg` 是否在、签名者/指纹）。
4. 解包 ⇒ 顶层 `Makefile` 的 `VERSION`/`PATCHLEVEL`/`SUBLEVEL` = **7 / 2 / 10**（真实输出），记录解包耗时 / 体积。
5. `manifests/components.lock.toml` 新增条目（`version`/`sha256`/源，`patchless = true`）；`make check` **rc=0**。
6. **号表来源指针**：`include/uapi/asm-generic/unistd.h` + `arch/riscv/include/uapi/asm/unistd.h` 各自 sha256 + 行数（现场）。
7. 门控：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` 各 **rc=0**。
8. `milestones.md` 加 `INFRA-075t` 流水行 + M8 规划区登记。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-075t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不**用 `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
4. **只动**：`.work/source/<linux>/**`（+ `.work/log/<模块>/` 日志）、`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`。
5. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`。
6. 大文件（tarball / 解包树）**不得**入 git（`.work/` gitignored）。

## 执行记录（2026-10-14，本地）

### 取源（TUNA）
- **申报**：≈153 MiB，按 9.6–11.2 MB/s 估 **≈20 s**。**实测**：`RC_XZ=0`、`RC_SIGN=0`、**总耗时 1 s**（`curl` 自报均值 **≈137 MB/s**）——**远快于申报**（现场值，如实记录；与预研测速差异原因未查证）。日志 `.work/log/<模块>/`。
- **体积**：`linux-7.2.10.tar.xz` = **160,425,804 B**（≈153.0 MiB，与预研 `HEAD` 的 `content-length` 逐位一致 ✓）；`linux-7.2.10.tar.sign` = **989 B**。
- **sha256（tarball，现场）**：`2feaa70453e91f541be6a5c9078d8168e081af45a3d9718054850538cff2ebf3`。
- **独立核对**：TUNA 发布 `kernel/v7.x/sha256sums.asc` 中 `linux-7.2.10.tar.xz` 的 sha256 **与本机逐位一致** ✓（非自证）。
- **`.tar.sign` sha256（现场）**：`72988fea40c5b3b6dde6d228849bc72a880d85a0ae4d896b16903d834b1ee420`。

### GPG 验签（**完成**）
- `gpg` **存在**：`gpg (GnuPG) 2.4.4`（`/usr/bin/gpg`）。
- 签名 `.sign` 的签名者密钥 = **`647F28654894E3BD457199BE38DBBDC86092693E`**（Greg KH 内核稳定版签名密钥；从 `hkps://keyserver.ubuntu.com` 导入成功）。
- **正确验签命令**：`xz -dc linux-7.2.10.tar.xz | gpg --verify linux-7.2.10.tar.sign -` ⇒ **`Good signature`**（`GPG_PIPE_RC=0`；签名日期 2026-10-11）。日志 `.work/log/<模块>/`。
  - **注**：内核 `.tar.sign` 签的是**解压后的 tar**；故 `gpg --verify <sign> <tarball.xz>` 直传压缩体会报 `BAD signature`（`GPG_LITERAL_RC=1`）——**非**验签失败，是命令形态不适用（已实测对照）。

### 解包与版本核
- `tar -xf …xz -C .work/source/<linux>/` ⇒ **`TAR_RC=0`**、**14 s**、解包树 **1.8 GB**、顶层目录 `linux-7.2.10/`。
- **版本核（真实输出）**：顶层 `Makefile` `VERSION = 7` / `PATCHLEVEL = 2` / `SUBLEVEL = 10` ⇒ **7.2.10 ✓**。

### 锁定（`manifests/components.lock.toml`）
- 新增 `[[component]] name = "linux-kernel"`：`enabled = false`、`repository`（kernel.org 规范 tarball URL）、`version = "7.2.10"`、`sha256 = "<实测>"`、`patchless = true`、`role`；`[[component.source]]` = `tuna`（主）+ `kernel-org`（备）。
- **设计决策（须披露）**：`manifest_check.py` 对**任一 `enabled` 组件**要求**完整 40 位十六进制 git commit**；签名 tarball **无** git commit（其身份 = sha256）⇒ 置 `enabled = false`（**未**为过闸伪造 commit）。`patchless = true` 如实声明「无 v5 补丁集」（与 chipyard / `ADR-0024 D1` 同类）。**待裁定**：是否为门控新增「非 git（tarball）组件」类别（`sha256` 替代 `commit`），使该条目可 `enabled = true`——**本任务未改门控**（越界）。

### 号表来源指针（供 `SPEC-138t`；**只给指针，不写契约正文**）
- `include/uapi/asm-generic/unistd.h`：**915 行**，sha256 = `9ec1faddab5c363614b166ee7eed3f7723529e3a32312aad14fc6d0df5204354`。
- `arch/riscv/include/uapi/asm/unistd.h`：**23 行**，sha256 = `0134f2d3cec62a5be0028498ae86408a513b734036afd2d845e239a2079f59e3`。
- 解包根 = `.work/source/<linux>/linux-7.2.10/`（供 `SPEC-138t` 复算 sha256 / 行数）。

### 门控（现场 rc）
- 见「完成区 · 测试结果」。

## 完成区
**测试结果**：门控现场 rc（**改动前后各一轮**）：`make check`(L1) **rc=0**、`make check-modules`(L2) **rc=0**、`check-no-residue` **rc=0**、`check-knowledge-refs` **rc=0**（0 悬空）、`check_issues.py` **rc=0**。`patchless` 机制可达性实验（**临时**改副本后 `cp`+md5 还原）：`enabled=true` 缺 commit ⇒ `manifest-check` FAIL「enabled components require a full commit」；`enabled=true` + 40 位 commit 且 `patchless=true` ⇒ `manifest-check` rc=0（放行无补丁字段）、`check-patch-tree` 跳过该组件（`0` 计数不含）；去掉 `patchless` ⇒ FAIL「missing patch series」⇒ 证明 `patchless` 为放行开关。还原后 md5 逐位复原、`make check` 回绿。
**修改文件**：`manifests/components.lock.toml`（+ `linux-kernel` 条目）；本任务书；`.tao/knowledge/milestones.md`（流水行 + M8 登记）；`.work/source/<linux>/**`（tarball + sign + 解包树，**未入 git**）、`.work/log/<模块>/*`（日志）。**未提交**（提交权归 architect）。
**验收结果**：取源 / sha256（含独立核对）/ 验签 / 解包 / 版本核 / 来源指针均由现场命令取证（见上「执行记录」）；`manifests` 条目经门控核验。
**新发现/坑**：① `manifest_check.py` 的 `enabled` 语义绑定 **git commit**（40 位十六进制）⇒ **非 git 源（签名 tarball）无法 `enabled=true`**（本任务据此置 `enabled=false`，未改门控）。② 内核 `.tar.sign` 签**解压后 tar** ⇒ 直传 `.xz` 会误报 `BAD signature`；正确形态 `xz -dc … | gpg --verify … -`。③ TUNA 实测 **≈137 MB/s**（1 s 下完 153 MiB），**远快于**预研测速 9.6–11.2 MB/s（原因未查证）。
**遗留问题**：① **待裁定**：是否为门控新增「非 git（tarball）组件」类别，使 `linux-kernel` 可 `enabled = true`（`sha256` 替代 `commit`）——**未在本任务内改门控**。② SHA-1 前的 `.sign` 密钥信任（ownertrust）未设 ⇒ gpg 报「not certified with a trusted signature」（**不影响** `Good signature`）；如需 WoT 信任须另行设置。

## 审阅记录

#### 第 1 轮 architect 执行 + 自审（2026-10-14）
- **范围**：取源（TUNA 主）、sha256（+ 独立核对 `sha256sums.asc`）、GPG 验签、解包与版本核、`manifests` 条目、号表来源指针、门控。
- **防造假**：每条结论附现场命令输出；sha256 与**外部** `sha256sums.asc` 对上（非自证）；`patchless` 用**可达 FAIL**（去 `patchless` ⇒ `missing patch series`）证明；门控改动前后各一轮均现场 rc；临时实验后 `cp`+md5 还原。
- **判决**：验收标准 1–8 均达成（`patchless` 机制**可达性**已证；本条目实际置 `enabled=false`，原因见「完成区·新发现①」）。**待 reviewer 独立验收**。

## 追加：落点订正 + 门控扩展（2026-10-14，`INFRA-075t-fix`；**不改写**上文既有完成区 / 审阅记录）

### 用户裁定（原话）
> 「不要乱建子目录，把 `linux-7.2.10.tar*` 移动到 `.cache/` 目录下，`linux-7.2.10` 目录放在 `.work/source/` 下面」

⇒ 落点订正（**此后其它子代理不得「恢复」旧布局**）：
- `.cache/linux-7.2.10.tar.xz` + `.cache/linux-7.2.10.tar.sign` = **下载原件**；
- `.work/source/<name>/` = **解包树直接放 `source/` 下，不再套 `linux/` 包装层**。

### 落点订正（现场）
- 前：`.work/source/<linux>/{linux-7.2.10.tar.xz, linux-7.2.10.tar.sign, linux-7.2.10/}`。
- 后：tarball + sign 移入 `.cache/`（`.cache/` 原有逐字节相同副本，`mv -f` 幂等）；解包树移为 `.work/source/<name>/`；空的 `.work/source/<linux>/` 已删。
- **旧路径表述已订正**：本任务书前文「输出 = 落 `.work/source/<linux>/`（tarball + sign + 解包树）」按用户指令**订正**为「下载原件归 `.cache/`、解包树归 `.work/source/<name>/`」；此后以本追加小节为准。
- 复核（现场）：tarball sha256 = `2feaa704…f2ebf3`、sign sha256 = `72988fea…`、解包树顶层 `Makefile` = **7 / 2 / 10** ⇒ **均不变**；`du -sh` = 解包树 **1.8 G**、`.cache/` **644 M**。

### 门控扩展：非-git（tarball）组件
- `manifests/components.lock.toml` 的 `linux-kernel`：新增 `source_kind = "tarball"`、`enabled = true`；保留 `version`/`sha256`/`repository`/`sources`（+ `patchless = true`，与 `source_kind` **正交**：`patchless` = 无 v5 补丁集，`source_kind` = 非-git 身份）；删除 `enabled = false` 的理由性注释。
- `tools/infra/manifest_check.py`：**当且仅当** `source_kind == "tarball"` ⇒ **允许无 40 位 commit**（**必须**有 `sha256` + `version`；**必须无** git commit；**不得**夹带 `patch_dir`/`patch_series`）；**其它组件照旧强制 commit（未放宽）**。
- **可达 FAIL 三条**（现场输出见证据脚本）：① tarball 缺 `sha256` ⇒ FAIL；② tarball 带 40 位 commit ⇒ FAIL；③ 非-tarball 组件缺 commit ⇒ 仍 FAIL；三条均 `cp`+md5 还原回绿。

### 约定改准
- `AGENTS.md`「工作区落点」：`.cache/` = 裸仓库 **+ 下载原件（tarball / 签名）**；`.work/source/<name>/` = 解包源码树（**直接放，不再套同名包装层**）；`.work/build/` = 构建产物。
- `lessons §3.19`：补「解包树直接以组件名落地、不再套包装层」的**反例**。

### 现场证据
- `.work/evidence/<任务ID>/run.sh`（可失败、可达 FAIL、结构断言、计数**现场统计**）；日志 `.work/log/<模块>/*`。

#### 第 2 轮 engineer 自审（2026-10-14，`INFRA-075t-fix`）
- **范围**：落点重摆、`source_kind="tarball"` 门控、约定/记录订正、`fetch.py` tarball 守卫。
- **逐行审查**：`manifest_check.py` tarball 分支置于 `enabled` 之后、commit/`patchless` 之前，**仅** `source_kind=="tarball"` 放行无 commit，其余分支**逐行未改**（未放宽）；该分支**主动拒绝** `commit` / 缺 `sha256` / 缺 `version` / 夹带 `patch_*`。`fetch.py` 守卫在 `component["commit"]` **之前** `continue`；`source_kind` 缺省（其余组件）行为**不变**。`check_patch_tree.py` **未改**（`linux-kernel` 经 `patchless` 跳过，`4 component(s)` 计数不含它）。
- **防造假**：三条门控 FAIL + fetch 守卫 FAIL 均**真实可达**（E2 用**临时副本**去守卫 ⇒ `KeyError: 'commit'`）；manifest 注入后 `cp`+md5 **逐位复原**（`97e4223f…`）；计数**现场统计**（`checks=29`）。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---------|------|---------|---------|
  | `enabled=true` 使 `fetch.py` 对 commitless 条目 `KeyError`（**本次新引入**） | ✅已修（**越界**，已披露） | `fetch.py` 加 `source_kind=="tarball"` 跳过 | 证据脚本 E1（rc=0）/ E2（去守卫副本 rc≠0） |
  | `apply_series.py`/`make_patch.py` 对 tarball / `patchless` 组件 `KeyError`（**既有**，`INFRA-074t` 遗留⑤） | ⏸延后 | 未改（越界；既有缺口，非本次引入） | 静态复现见「完成区·遗留①」 |
  | `milestones.md` 仍记 `linux-kernel` `enabled=false`（本任务文件集**未含**该文件） | ⏸延后 | 未改 | 任务文件集无 `milestones.md` ⇒ 建议 architect 同步 |
- **判决**：本任务（落点 + tarball 门控 + 约定）全部达成；门控全绿；**本任务范围内无未修 finding**（唯一 `fetch.py` 越界已修并披露）。**待 reviewer 独立验收**。

## 完成区（追加：`INFRA-075t-fix`，2026-10-14）

**测试结果**：证据脚本 `.work/evidence/<任务ID>/run.sh` **rc=0**（**29 项**现场计数、0 失败）：A 落点 8 项（sha256 / 版本 / 旧包装层已删）；B 门控三反例（**可达 FAIL**、`cp`+md5 还原、回绿）；C 约定文本 4 项；E `fetch.py` tarball 跳过（E2 去守卫副本 ⇒ `KeyError: 'commit'`）；D 门控 rc：L1/L2/`check-no-residue`/`check-knowledge-refs`/`check_issues.py` **各 = 0**。
**修改文件**：`.cache/linux-7.2.10.{tar.xz,tar.sign}`（下载原件，**入 `.cache/`**）、`.work/source/<name>/**`（解包树，**未入 git**）、`manifests/components.lock.toml`（`source_kind` + `enabled=true`）、`tools/infra/manifest_check.py`、**`tools/infra/fetch.py`（越界，见遗留③）**、`AGENTS.md`、`.tao/knowledge/lessons.md`、本任务书；`.work/log|evidence/**`。**未提交**（提交权归 architect）。
**验收结果**：`ls` / `sha256sum` / `Makefile` / `du -sh` 现场输出见证据脚本；门控 rc=0；`git status --porcelain -uall` 仅列本任务改动 + 并行会话（`SPEC-138t`）产物。
**新发现/坑**：① **`enabled=true`（tarball）连带影响非门控消费者**：`fetch.py`/`apply_series.py`/`make_patch.py` 直取 `component["commit"]`/`patch_*` ⇒ `KeyError`。`fetch.py` 属**本次新引入**（原 `enabled=false` 时被跳过）⇒ 已加守卫；`apply_series.py`/`make_patch.py` 属**既有** `patchless` 缺口，**未动**。② 反例注入的正则须**行内锚定**（`[^\n]`，勿用 DOTALL `.*`）——贪婪回溯会吞掉多行（本任务实测踩坑）。
**遗留问题**：① `apply_series.py`/`make_patch.py` 仍会对 tarball / `patchless` 组件 `KeyError`（既有缺口，`INFRA-074t` 遗留⑤，**非本任务**）⇒ 建议后续统一跳过 `source_kind=="tarball"`。② `milestones.md` 仍记 `linux-kernel` `enabled=false`（本任务文件集未含，**未改**）⇒ 建议 architect 同步。③ `fetch.py` 为**越界**改动（任务只列 `manifest_check.py` + `check_patch_tree.py`），已披露；回退 = 删该守卫（后果：`make fetch` 对 commitless 条目 `KeyError`）。

#### 第 1 轮 reviewer 验收（2026-10-14，分支 `INFRA-075t-fix`，全部为 reviewer 自跑真实输出/退出码）
- **落点/条目（重跑）**：`.cache/linux-7.2.10.tar.xz` sha256=`2feaa704…f2ebf3`、`.tar.sign`=`72988fea…`；解包树顶层 `Makefile` **7/2/10**；旧包装层 `ls` ⇒ `cannot access`（已删）、`.work/source` 下 `linux-7.2.10.tar*` 计数 **0**、`du` 解包树 **1.8G** ⇒ 与任务书逐位一致。`manifests` 条目：`linux-kernel` `enabled=true`+`source_kind="tarball"`+`version="7.2.10"`+`sha256`+`patchless=true` ✓。号表复算：**915/23 行**、sha256 `9ec1fadd…`/`0134f2d3…` 一致 ✓。
- **验签（重跑）**：`xz -dc … \| gpg --verify … -` ⇒ `Good signature`（`647F…693E`，Greg KH）、`GPG_PIPE_RC=0` ✓。
- **门控（重跑）**：`make check`/`check-modules`/`check-no-residue`/`check-knowledge-refs`/`check_issues.py` 各 **rc=0**（`SPEC-138t` 并发未提交改动在场，未见瞬时红，无需重跑）。
- **证据脚本（重跑）**：`.work/evidence/<任务ID>/run.sh` ⇒ **rc=0**（`checks=29 (live count) failed=0 RESULT: PASS`），与完成区声称一致。
- **独立反例注入（reviewer 自做，`cp`+md5 还原）**：①缺 `sha256` ⇒「tarball component requires a sha256」rc=1；②tarball 带 40 位 commit ⇒「must not declare a git commit」rc=1；③非-tarball（picolibc）缺 commit ⇒「enabled components require a full commit」rc=1；④tarball 夹带 `patch_series` ⇒「must not declare patch_dir/patch_series」rc=1；⑤缺 `version` ⇒「requires a version」rc=1；每次还原 md5=`97e4223f18d56a29ac4e0d87c46f1e87` 逐位复原。**同脚本反例**：注入④后重跑 run.sh ⇒ **rc=1**（`RESULT: FAIL`、failed=6，含 `B0 baseline manifest-check rc (expected=0 actual=1)`）；还原后重跑 ⇒ **rc=0** `RESULT: PASS`（注入→FAIL→还原→回绿闭环）。
- **`fetch.py` 越界核**：diff 仅 **+7 行/0 删除**，守卫位于 `component["commit"]` 之前 `continue`；守卫 harness ⇒ rc=0，5 个 git 组件照旧 `select_source`+`sync_mirror`（llvm/qemu/embench/picolibc/chipyard 均 `-> <commit>`）、linux-kernel skip ⇒ 既有 git 路径未破坏；去守卫副本 ⇒ `KeyError: 'commit'`（rc=1，可达 FAIL）。非-tarball 照旧强制 commit（注入③）⇒ **未放宽** ✓。
- **约束核验**：未动 `spec/`/`contracts/`/组件补丁 ✓；任务书 diff **48 行纯追加、0 删除**（完成区/审阅记录未改写）✓；未用 `git checkout/restore/stash` 还原 ✓；文本未写 `.work/<具体路径>` 字面 ✓；大文件未入 git ✓；`fetch.py` 越界已披露 ✓。
- **判决：Needs Revision**（唯一阻断项）
  - **B1（阻断）**：验收标准 2「与 TUNA `sha256sums.asc` 逐位一致（**独立核对**）」**无落盘留证**——`grep sha256sums .work/log/<模块>/INFRA-075t* .work/evidence/<任务ID>/` **rc=1 无匹配**，`.cache/` 无 `.asc` 副本，任务书只有结论句、无比对原始输出。按铁律「不采信叙述」无法确认 ⇒ 须**补做比对并落盘**（取 `kernel/v7.x/sha256sums.asc`〔KB 级〕⇒ `grep linux-7.2.10.tar.xz` 与本机 `sha256sum` 逐位对照 + 退出码写 `.work/log/<模块>/`，回填任务书）。**注**：内容完整性已由我重跑的 `Good signature` 独立佐证，但不替代留证；若用户裁定 GPG 已足，则应把该句改写为「未留证」而非「已核对」。
- **非阻断项（需 architect 处置）**：① **陈旧表述清单**：`milestones.md` L29/L105 仍写 `linux-kernel` `enabled=false`〔无 git commit〕（活台账，建议同步 `source_kind="tarball"`+`enabled=true`）；本任务书 L68/69/83/91（第 1 轮历史节）仍述 `enabled=false`，追加节已声明「以此为准」，改写与否请 architect 裁定。② **并发活动（非我启动、未触碰）**：另一会话 09:57 起 `git clone --bare --depth 1 --branch v7.2.10 …linux-stable.git .cache/linux.git`（`.work/log/<模块>/INFRA-075t-git-clone.log` 仍在写、`ps` 可见、TUNA 队列排队中）——不在本任务「修改文件」声明内，归属/去留请裁定。③ `.work/log/<模块>/INFRA-075t-gpg-verify.log` 未记命令形态（我重跑已证 `xz -dc \| gpg --verify -` 正确）。④ run.sh 三反例只留 rc 未捕错误文案（reviewer 注入已捕齐五条文案）。
- **其余各项**（落点、`manifests` 条目、门控三分支与反例、`fetch.py` 守卫、号表、约定固化、门控 rc）**验证通过**。

---

## 追加：源形态订正（tarball → git 基线）（2026-10-14，分支 `INFRA-075t-git`；**不改写**上文既有完成区 / 审阅记录结论）

### 用户裁定（原话）
> 「`linux-7.2.10` 目录现在**不是 git 仓库**，后续要做改动的话，就**无法产生 diff 文件**」

⇒ **源形态订正：组件源一律 git 基线**；工作树名 = `.work/source/<linux>/`（与 `qemu`/`picolibc` 命名一致）。**本追加取代**上文「tarball 整包 + 解包树」形态（上文记录作历史留存，不再代表当前落点）。

### 新落点与实测（现场值）
| 项 | 申报 | 实测 | RC |
|---|---|---|---|
| 裸仓库 `.cache/<linux>.git`（`git clone --bare --depth 1 --branch v7.2.10` ← TUNA git） | ≈200–300 MB / ≈30–120 s | **281 MB / 686 s** | `0` |
| 工作树 `.work/source/<linux>/`（`git clone --branch v7.2.10` ← 本地 mirror，无网络） | — | **2.1 G / 27 s** | `0` |

- 裸克隆慢于申报的原因（现场）：远端排队 `Position≈373` + 中段速率降至 ≈2–6 MB/s；**单次成功、未重试**（无重试必要）。
- 核验：`refs/tags/v7.2.10` 存在；工作树 `rev-parse HEAD` = 锁 `commit`、`status --porcelain` 空、`rev-parse --is-shallow-repository` = `true`。

### ★ tag ref 值 ≠ commit（体例处置，**须 architect / 用户确认**）
- 用户实测 `refs/tags/v7.2.10` = `57eee103859fa039a1f2bf343c4453ef40661be8`：经核 = **annotated tag object**（`cat-file -t` = `tag`，含 Greg KH PGP 签名），其 **peel 目标 commit** = `7b20d05fd38de8e0be168956f6fd241d750c7d69`。
- v5 体例 = 锁 `commit` 记 **commit**（实证对照：`qemu` 条目 `commit = c3d48b7d…`〔`cat-file -t` = `commit`〕，而 `refs/tags/v11.1.1` = `5e35f266…`〔tag object〕——两者不同）⇒ 本条目 `commit` 记 **peel 后 commit**，tag object sha 记入本条 + 锁注释。
- **注**：「核工作树 `rev-parse HEAD` = `57eee103…`」在 git 语义下**不可达**——annotated tag 检出后 `HEAD` 必为 **commit**；现场 `HEAD` = `7b20d05…`（= 锁 `commit`）。若须按字面记 tag object sha，**改一行**即可（后果：`fetch.py` 的 `head_of(target) == commit` 永不成立，每次 fetch 走 checkout 分支）。

### 锁条目（新原文；体例对齐 `llvm-project`/`qemu`）
```toml
[[component]]
name = "linux-kernel"
enabled = true
repository = "https://mirrors.tuna.tsinghua.edu.cn/git/linux-stable.git"
commit = "7b20d05fd38de8e0be168956f6fd241d750c7d69"
shallow = true
shallow_ref = "v7.2.10"
patchless = true
role = "Linux syscall numbering-table source (reference input; no v5 patch set)"

[[component.source]]
name = "kernel-org"
url = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
```
**删除**的 tarball 专有字段：`source_kind` / `sha256` / `version`（tarball `sha256 = 2feaa704…f2ebf3` = **校验凭据**，见下）。`make check` **rc=0**。

### 交叉校验（★ 删除旧树之前完成；独立 oracle = 已验签 tarball）
- **全量**：`diff -rq --exclude=.git <tarball 解包树> <git 工作树>` ⇒ **RC=0、差异 0 行、42 s**；文件数各 **94775**。
- **可重跑的独立 oracle**（不依赖已删旧树）：`tar -xOf .cache/linux-7.2.10.tar.xz <顶层>/<path>` sha256 vs git 工作树 sha256，**抽样 14 个**（`include/uapi/asm-generic/unistd.h`、`arch/riscv/include/uapi/asm/unistd.h`、`scripts/syscall.tbl`、`Makefile`、`kernel/{fork,sys,exit}.c`、`kernel/sched/core.c`、`arch/riscv/kernel/{syscall_table.c,entry.S}`、`arch/riscv/mm/init.c`、`include/linux/syscalls.h`、`mm/memory.c`、`fs/read_write.c`）⇒ **14/14 逐位一致**。
- 两号表 sha256（现场）：`9ec1fadd…4354`（asm-generic）/ `0134f2d3…59e3`（riscv）⇒ **与取源记录逐位一致**。
- **删除旧树**：`.work/source/<name>/`（tarball 解包树）`rm -rf` **RC=0**；**保留** `.cache/linux-7.2.10.tar.xz`（现场 sha256 `2feaa704…f2ebf3`）+ `.cache/linux-7.2.10.tar.sign` = **校验物 / 下载原件**。
- **补证（第 1 轮 reviewer B1 阻断项）**：TUNA `sha256sums.asc`（现场 sha256 `0e21f0bf…ff73`）第 123 行 `2feaa704…f2ebf3  linux-7.2.10.tar.xz` **与本机逐位一致**（`MATCH=yes`，落盘 `.work/log/<模块>/INFRA-075t-git-sha256sums.log`）。

### `git diff` 可用性证明（现场）
- 注入：向工作树号表文件追加探针行 ⇒ `git status --porcelain` 报 ` M`（1 行）、`git diff` **10 行**、落 patch 文件非空；注入态下「工作树干净」断言 **判 FAIL**（可达 FAIL ✓）。
- 还原：`cp` 备份回写 + **md5 逐位对账**（`34b4672d7491000cd8dfd4b3cff16626`）⇒ `git status` 回空、号表 sha256 回记录值。**未用** `git checkout/restore/stash` ✓

### 约定固化（治根，用户原话为据）
- `AGENTS.md` 新增一条：**组件源一律 git 基线**（`.cache/<name>.git` 裸仓库 + `.work/source/<name>/` = 可 `git diff` 的干净检出）；**tarball 只作校验物 / 下载原件，不得作组件源**。
- `lessons §3.19` 补同义条目：tarball 解包树无 git 元数据 ⇒ 改动产不出 diff（要产 patch 时才发现，返工代价高）；`patchless` 与「源码形态」**正交**。

### 现场证据
- `.work/evidence/<任务ID>/run.sh`（**计数现场统计**、可达 FAIL、结构断言、注入→FAIL→还原→回绿）；日志 `.work/log/<模块>/*`。

#### 第 3 轮 engineer 自审（2026-10-14，分支 `INFRA-075t-git`；自主逐行审查）
- **范围**：源形态订正（git 基线）、交叉校验、锁条目改造、约定固化、证据脚本。
- **逐行审查**：`components.lock.toml` 仅 `linux-kernel` 段被改（`enabled`/`shallow`/`shallow_ref`/`patchless` + 40-hex `commit` + git `repository`；tarball 专有字段 `source_kind`/`sha256`/`version` 删净），其余 6 组件**逐行未动**（`git diff` 仅该段 + 注释）。`AGENTS.md` 仅「工作区落点」行改写 + 新增 1 行，未涉其它节。`lessons.md` 仅 §3.19（标题 + 4 bullet，新增 1 条）。`run.sh`：pathspec 相对 `$WT`（本次实测教训见下）、计数**现场统计**、还原用 `cp`+md5、无 `tee`。旧树删除**不可逆**，但已「校验通过 + tarball 保留 + 可重跑 oracle」三重兜底。
- **防造假**：交叉校验用**已验签 tarball 抽取** vs git 树（独立 oracle，非自证）；门控捕**被检命令自身退出码**；注入→FAIL→还原→回绿闭环（B0–B7）；计数现场统计（46）。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---------|------|---------|---------|
  | 用户所给 `57eee103…` 实为 **annotated tag object**（非 commit）⇒ 字面填会使 `HEAD` 核对不可达、`fetch.py` 的 `head_of==commit` 永假 | ✅已修（**偏离字面，已披露 + 一行回退方案**） | 锁 `commit` = peel 后 `7b20d05…`；tag object sha 记入锁注释 + 任务书 | 证据脚本 A3/A4/A6；qemu 对照（`refs/tags/v11.1.1`=`5e35f266…`〔tag〕 vs `commit`=`c3d48b7d…`〔commit〕） |
  | 组件名 `linux-kernel` 与用户指定落点 `linux` 不一致 ⇒ `make fetch` 会另建 `.cache/linux-kernel.git` + `.work/source/linux-kernel`（重复 281 MB 下载 + 重复树） | ⏸延后（**须裁定**：改 name 超字段清单、改 `fetch.py` 超文件集） | 未改 | `.work/log/<模块>/INFRA-075t-git-fetch-naming.log`（现场打印推导；`.work/source/linux-kernel` 不存在） |
  | `manifest_check.py` tarball 分支 + `fetch.py` 守卫已成**死代码**，且门控仍放行 tarball 组件 —— 与新增约定「组件源一律 git 基线」相悖 | ⏸延后（文件集不含 `tools/`） | 未改 | 本次文件集 = lock / `AGENTS.md` / `lessons.md` / 任务书 |
  | `milestones.md` 仍记 `linux-kernel` `enabled=false`（tarball 形态） | ⏸延后（文件集未含） | 未改 | — |
  | `contract-syscall.md`（`SPEC-138t` **并行未提交**产物）引用 `source_kind="tarball"`/`version`，已被本次改锁取代 | ⏸延后（属 `SPEC-138t`，**未触碰**） | 未改 | `git status` 仍列该文件（并行会话） |
  | 第 1 轮 reviewer **B1**（`sha256sums.asc` 独立核对无留证） | ✅已修（补做 + 落盘） | 落 `.work/log/<模块>/INFRA-075t-git-sha256sums.log`（追加节记录） | `asc=2feaa704…f2ebf3` = `local=…`，`MATCH=yes` |
  | `run.sh` B 段 pathspec 取仓库根相对路径 ⇒ `git -C "$WT"` 匹配 0 项（**本次实测 FAIL**） | ✅已修 | 新增 `PROBE_REL`（相对 `$WT`） | 修前 B1/B2/B3 **rc=1 FAIL**；修后 run.sh **46/46 PASS、rc=0** |
- **判决**：未修 finding **全部为「超本次文件集 / 须裁定」的披露项**，已逐条列入完成区「遗留问题」；本任务范围内无未修缺陷。**待验收**。

## 完成区（追加：`INFRA-075t-git`，2026-10-14）

**测试结果**：`.work/evidence/<任务ID>/run.sh` **rc=0**（**46 项**现场计数、0 失败）：A 结构/事实 31 项（含自检 2 项）；B `git diff` 可用性 8 项（注入 → diff **10 行** → 还原 md5 逐位一致 → 回绿）；C 门控 5 项（`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` **各 rc=0**）。
**修改文件**：`.cache/<linux>.git`（新，裸仓库 **281 MB**）、`.work/source/<linux>/**`（新，git 检出 **2.1 G**，**未入 git**）、`.work/source/<name>/**`（tarball 解包树，**已删**）、`manifests/components.lock.toml`、`AGENTS.md`、`.tao/knowledge/lessons.md`、本任务书；`.work/log|evidence/**`。**未提交**（提交权归 architect）。
**验收结果**：见「追加：源形态订正」节现场值 + `.work/log/<模块>/INFRA-075t-git-evidence.log`（46/46 PASS）。
**新发现/坑**：① 内核 `v7.2.10` 是 **annotated tag**（`ls-remote` 报的 tag object sha ≠ commit）⇒ 锁 `commit` 须记 **peel 后 commit**（qemu 体例实证）。② TUNA 浅克隆**实测 686 s / 281 MB**（远端排队 `Position≈373` + 中段 ≈2–6 MB/s），远慢于 refs 测速 ⇒ 申报宜按最坏情况放宽。③ `git -C <wt> status/diff -- <path>` 的 pathspec **相对该仓库根**，误用外层仓库相对路径会**静默 0 匹配**（本次实测踩坑，B1 曾 FAIL）。
**遗留问题**：①【**须裁定**】组件名 `linux-kernel` 与落点 `linux` 不一致 ⇒ `make fetch` 会另建 `.cache/linux-kernel.git` + `.work/source/linux-kernel`（重复下载 281 MB）；选项 (a) name 改 `linux`（超本次字段清单）/ (b) `fetch.py` 支持目录映射（超文件集）。② `manifest_check.py` 的 tarball 分支 + `fetch.py` 守卫现为死代码且与「组件源一律 git 基线」相悖 ⇒ 建议回退（文件集不含 `tools/`，**未动**）。③ `milestones.md` 仍记 `enabled=false`（陈旧，**未改**）。④ `contract-syscall.md`（`SPEC-138t` 未提交产物）引用 tarball 字段，已被取代 ⇒ 由 `SPEC-138t` 同步。⑤ 第 1 轮 reviewer 的非阻断项 ①/③/④ 未在本轮处置（超文件集 / 历史留存）。

---

## 追加：收口订正（2026-10-14，architect；**不改写**上文既有完成区 / 审阅记录）

### 主会话裁定（**写入本任务书**，2026-10-14）
- ⓐ **组件名 `linux-kernel` → `linux`**（与用户指定落点 `.work/source/linux/` 一致）⇒ 同步 lock `name` 与**全部引用**；避免 `make fetch` 另建 `.cache/linux-kernel.git` + `.work/source/linux-kernel`（重复下载 281 MB）。
- ⓑ **回退** `tools/infra/manifest_check.py` 的 `source_kind == "tarball"` 分支 + `tools/infra/fetch.py` 的 tarball 守卫（已成**死代码**，且与「组件源一律 git 基线」相悖）⇒ **精确回退到 `INFRA-074t` 结束时的行为**；**`patchless` 机制保留**。

### 现场核验（architect，真实输出）
- **名改**：lock `name = "linux"`（`commit = 7b20d05f…`、`enabled = true`、`patchless = true`、`repository` = TUNA `linux-stable.git`、`shallow_ref = "v7.2.10"`）；tracked 文件内 `linux-kernel` 仅剩**历史归档** `.tao/archive/M1/README.md`（**不改**）与 `mirrors.md` **泛称 prose**（非组件名，**不改**）。
- **回退**：`git diff -- tools/infra/manifest_check.py tools/infra/fetch.py` **为空**、工具内 `source_kind`/`tarball` `grep` **rc=1 无匹配**（= `INFRA-074t` 结束态）；`patchless` 分支仍在（`manifest_check.py` L45 区）。
- **门控**：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` 各 **rc=0**。

### 陈旧表述订正
- `milestones.md`：任务流水行 + M8 规划区条目的 `linux-kernel` / `enabled=false` → **`linux` / `enabled=true`（git 基线）**（只改该行 / 该条）。
- 本任务书第 1 轮历史节（`enabled=false` 诸处，L68/69/83/91 一带）：**保留不重写**，以本追加节为准（订正注）。
- 第 1 轮 reviewer **B1** 阻断项：`.work/log/<模块>/…sha256sums.log` 内 TUNA `sha256sums.asc` 与本机 sha256 逐位一致（`MATCH=yes`）⇒ **已消解**。

### 收口观察（**非阻断**，留待用户/主会话裁定）
- lock 的 `[[component.source]]` 仅 `kernel-org`（canonical），`repository` = TUNA；而 `fetch.py::select_source` 优先级 = **`source[0]` 先于 `repository`** ⇒ 无 `COMPONENT_SOURCE_LINUX` 覆盖时 `make fetch` 实取 **kernel-org**（与「源 = TUNA 主」不一致；对照 `qemu`：`repository` = canonical GitHub、`source[0]` = SJTU 镜像）。本次**未改**（超收口范围），建议另行一行订正（`repository` 置 canonical + `source[0]` 置 TUNA）。
- 本任务书未含 `INFRA-075t-git` 轮次的独立 reviewer 记录（该轮为 engineer 自审 + 本轮 architect 收口核验）。

### 状态
- 第 1 轮 reviewer 判决 `Needs Revision`（唯一阻断 = B1，已补证消解）；本追加后 **状态 → `已验证`**，`milestones.md` 回填 `完成时间`。
