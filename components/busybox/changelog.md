# busybox 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M14

- **2026-11-18 `m14-linux-030`**
  - 摘要：**建 busybox 1.38.0 组件（静态 musl，K6 最小 applet 集）**。锁条目 `name = "busybox"`：`shallow_ref = "1_38_0"`、commit `fc71374d…`、`repository = https://git.busybox.net/busybox`（任务书原定的 github `mirror/busybox` 实测**无 1_38_0**：其 tags 最新 `1_36_1`，且直连 github clone 133 s 失败，故改官方站并记入任务书待裁定）；发布 tarball 作校验物（2695723 B，sha256 与 busybox.net `.sha256` 一致；与 git tag 树仅差 tarball 丢弃的 `.gitignore`）。补丁集 **2** 条，同一根因（`#` 不是 DADAO 汇编注释符，`spec/Toolchain-01 §2.2`）：`libbb/const_hack.c`（clang 屏障模板注释 → 空模板）、`libbb/Kbuild.src`（x86 手写汇编只在 x86 目标编译）。最小 config 真源 `components/busybox/config.min`：`allnoconfig` + 逐条打开 + `silentoldconfig` 后再断言；开 `CONFIG_BUSYBOX`/`FEATURE_VERSION`（`busybox sh` 与 `--version` 需要）、`SH_IS_ASH` + `ASH`、9 个 applet、`STATIC`；关 PAM/行编辑。构建入口 `make build-busybox`（`tools/linux/build_busybox.py`）：生成 CC wrapper（`-nostdinc` + musl 源树 include；最终链接显式 `crt1.o`+`libc.a`）、`STRIP=llvm-strip`、`ARCH=dadao`、`SOURCE_DATE_EPOCH` = 锁定 commit 时间 ⇒ clean 重建哈希逐位一致。**返工（reviewer 第 1 轮 Needs Revision）**：配置复用改**双向**（产物目录记录生成时的受管符号集，`config.min` 删/加符号都触发重生成；`build_busybox.py --check-config` 可查）；证据脚本取被检命令 `rc` 不再经管道（此前 C0/C2/C3 吞码 ⇒ 构建脚本坏死仍全绿）、C8 期望改由 `config.min` 现场派生并补 `applets.txt`↔`--list` 与任务书约定集两条断言、`--inject` 由 2 路扩到 **4 路**（新增「删真源符号」与「打坏构建脚本」）。用户 2026-11-18 裁定（原话「busybox：1、认可；2、用官方源」）：官方站 `repository` 认可，并登记 `[[component.source]]`（name=official）。**实测**：产物 `.work/build/busybox/busybox` 311408 B、sha256 `31ee37c4…`、`ELF64/MSB/0xDA0/ET_EXEC`、无 `PT_INTERP`/`PT_DYNAMIC`；`qemu-dadao` 下 `--version` = `BusyBox v1.38.0 (…)`、`--list` = `ash cat cp echo grep ls mkdir mv ps rm sh`、`echo/mkdir/ls/sh -c/grep` rc=0。
  - 执行者：engineer

## M18

- **2026-11-22 `m18-linux-001`**
  - 摘要：**`config.min` 增加 `CONFIG_KILL`**（applet 由 11 增至 12）；新增补丁 `shell/ash.c.patch`：K6 首版无作业控制，ash 的 `wait4` 同步等待即可，因此不安装 `SIGCHLD` 处理函数（设 `SIG_DFL`，不自动回收）。`ASH_JOB_CONTROL` 仍关，ash 的 `kill` 内建不可用；验收「shell 向子进程投递 `SIGTERM`/`SIGINT`」用外部 `/bin/kill`。applet 链接清单由 `applets.txt` 派生，`make_initramfs.py` 同步多建 `bin/kill -> busybox`。
  - 执行者：engineer
