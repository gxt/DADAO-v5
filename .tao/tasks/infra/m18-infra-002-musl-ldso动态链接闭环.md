# m18-infra-002: musl ldso 动态链接运行闭环（P3）

**模块**：infra
**项目里程碑**：M18
**依赖**：`m18-infra-001`（musl 基线）、`m18-linux-003`（system Linux 可启动）；**调度约束**：与 `m18-linux-005` 串行（两者都写 `linux` 组件/共享构建树）
**可并行分片**：否
**预估**：2–3 天
**档位**：大改（组件运行期 + 装载链路）
**状态**：待开始
**执行环境**：本地（`qemu-dadao` user + QEMU system `-M kaiwu-vast`）

## 背景

- `components/musl/README.md`：阶段 A1 已能产出 `lib/libc.so`、`lib/libc_pic.a`、`ld-musl-dadao.so.1 -> libc.so` 与带 `PT_INTERP` 的动态可执行（`make build-musl-shared`），但**动态 ELF 的运行**仍属 P3；`tools/infra/build_musl.py` 目前只做 `readelf` 级断言，**不执行**。
- 动态链接 ABI 已有冻结契约：`.tao/contracts/contract-dynlink.md`（`§2` PIC/PIE、`§3` GOT/PLT、`§4` 动态重定位、`§5` 动态段、`§6` `PT_INTERP`/auxv、`§7` TLS、`§10` 越界策略）；`PT_INTERP` 路径 = `/lib/ld-musl-dadao.so.1`（`§6.1`），期望值以契约为准，不从实现反推。
- 用户 2026-11-22 裁定：**`ldso` 该加就要加**。`ADR-0052 D5` 只把 M14 初始 `/init` 定为静态，不禁动态可执行；本任务不把 `/init` 改为动态。
- 内核 `CONFIG_BINFMT_ELF=y`（`arch/dadao/configs/defconfig` 补丁），`PT_INTERP` 装载路径尚未验证。

## 目标

1. **构建**：`make build-musl-shared` 产出 `libc.so` 与 `ld-musl-dadao.so.1`；安装布局按契约（`/lib/ld-musl-dadao.so.1`）。`readelf` 断言：`ET_DYN`、大端、`EM_DADAO`、`DT_SONAME`、`DT_GNU_HASH`、无 `DT_HASH`/`DT_RELR`/版本节；动态可执行的 `PT_INTERP` 字节串与 `DT_NEEDED`。
2. **运行（system Linux，必须）**：动态可执行在 QEMU `-M kaiwu-vast` 上跑通：至少 `printf` + `malloc/free` + 一次 `write`；输出逐字匹配、退出码正确。内核 `PT_INTERP` 装载 → ldso 自举 → `libc.so` 重定位 → TLS/errno → 返回用户态，整链有可归属证据。
3. **运行（qemu-user，尽力）**：`qemu-dadao` 跑同一动态 ELF；若缺口属 qemu 组件，给出精确证据与后续任务建议，不阻塞 system 交付。
4. **能力边界**：`pthread_create/join`、`dlopen`、动态 TLS、符号版本、`RPATH/RUNPATH` 逐项判「支持 / 暂不支持（原因 + 证据 + 复评条件）」。`pthread` 失败必须定位到层（内核 / ldso / libc / qemu），不得静默跳过。
5. **不回归**：`lib/libc.a` 与改前 md5 相同（静态档不受影响）；`build-musl`、`build-busybox`、`check-linux-k6` 不回归。

## 验收（逐条贴真实 rc）

1. `make build-musl-shared` rc=0；`libc.so`/`ld-musl-dadao.so.1` 的 md5 + 上述 `readelf` 断言全部落盘。
2. **动态可执行在 system Linux 上 rc=0**，输出与期望逐字相等；证据脚本（运行期证据目录内 `run.sh`）一键完成构建 → 镜像 → 启动 → 判定，含 guest/宿主两侧退出码。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 改 `PT_INTERP` 为不存在路径 ⇒ 启动/装载失败；② 破坏 ldso 重定位（如改写 `libc.so` 的动态段或删一个必要符号）⇒ 运行失败。两路还原后回绿。
4. 静态不回归：`build-musl` rc=0 且 `libc.a` md5 等于改前；`check-linux-k6` rc=0。
5. 组件补丁按 `docs/Process-01` 重导；`check-patch-tree` 的 musl 段与基线**逐行相同**（`ISS-507` KNOWN-RED 判据），无新增 problem；`check-component-changelog` rc=0；`check-config-pins`/`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`。
2. 只动：`components/musl/**`、`tools/infra/build_musl.py`、`tools/linux/make_ldso_image.py`（**新文件**）、`tests/unit/infra/**`、`components/musl/changelog.md`、本任务书。
3. **不改** `Makefile`、`components/qemu/**`、`components/busybox/**`、既有 `tools/linux/make_initramfs.py` 与 `tools/linux/check_k6.py`、`check-linux-k6` 判据。
4. 若确需内核侧修复 `PT_INTERP`/auxv：仅限动态装载所必需的**最小** `components/linux/patches/**` 改动，逐条在完成区披露并同步 `components/linux/changelog.md`；不顺手改无关代码。若改动超出装载链路，停下写「待裁定」。
5. 期望值只来自 `contract-dynlink.md` 与 `contract-elf.md`；与实现冲突时按契约改实现，不反向改契约。
6. 不改版本号；不新增外部依赖；术语「bank = 寄存器组」；大端、64 KiB 页口径按 `MEMORY.md` 反套用清单。
7. 源码还原一律 `cp`+md5 对账；禁 `git checkout`/`restore`/`stash`；源码还原后须重建。

## 待裁定

无（若出现 qemu-user 缺口或需超出装载链路的内核改动，写「待裁定」交主会话转用户）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
