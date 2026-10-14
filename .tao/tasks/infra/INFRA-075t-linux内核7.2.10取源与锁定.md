# INFRA-075t: Linux 内核 7.2.10 取源与锁定

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`；`D1` = 沿用 RISC-V 编号）；消费方 `SPEC-138t`（Linux syscall 映射契约，只取号表来源指针）
**状态**：待验收

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
