# Linux 组件（linux）

DADAO 的 **Linux 内核移植目标**（M14 起；`arch/dadao/**`）+ **syscall 号表参考**（SPEC-138t 钉住的号表来源：`asm-generic/unistd.h` + `arch/riscv/include/uapi/asm/unistd.h`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "v7.2.10"`，精确 commit `7b20d05f…`）；工作树由 `make fetch` + `make apply-series` 在运行期的组件源目录建立。

M13 及以前本组件只是**参考输入**（`ADR-0025 D2`：无内核目标），故带 `patchless`、无补丁集；M14 起转为**受补丁组件**（`m14-linux-001`），基线不变。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0025`（M8 用户态栈）、`ADR-0006`（浅裸镜像）。
- **现状（M14 K0）**：56 份补丁，全部在 `arch/dadao/**`（`m14-linux-002` 的 K0 最小骨架）；`.gitkeep` 已随首个补丁删除。上游文件**未改动**：`ARCH=dadao` 的 target triple 走 `CLANG_TARGET_FLAGS` make 变量，导出表/符号表相关开关走 arch `Makefile` 的编译选项，因此不触碰 `scripts/Makefile.clang`、`include/linux/export.h`。
- 后续范围：机器/中断/定时器/页表/启动入口按 K1–K3 逐任务落地，具体以各任务书为准。

## 构建与验证

内核侧目标（目标名与脚本路径由 `Makefile` 一次声明；脚本随各任务落地）：

```
make linux-defconfig        # 生成 DADAO defconfig（写者，持 gate.lock）
make linux-vmlinux          # 构建 vmlinux + 产物断言 + 代码跨度护栏（写者）
make linux-initramfs        # 构建 initramfs（写者）
make linux-semihosting-smoke  # 半主机启动冒烟（写者）
make check-linux-toolchain  # 交叉工具链可用性（只读）
make check-linux-boot-contract  # 启动 ABI 契约（只读）
make check-linux-k0         # K0 收口门控（只读，会增量构建）
```

运行期路径（源树/构建树/initramfs 目录/工具链 bin）**只**由 `tools/linux/paths.py` 从 `manifests/` 解析，脚本不得自行拼路径。

K0 的 `make linux-vmlinux` 依次做：真实 `make ARCH=dadao … vmlinux` → ELF 产物断言（`contract-linux-boot §3.1`：ELF64 大端、`e_machine=0x0DA0`、`e_entry=0x0200_0010_0000`、仅 `PT_LOAD`（另允许 `PT_GNU_STACK`/`PT_NOTE`）、`p_vaddr = p_paddr + 2 TiB` 且 64 KiB 对齐、无未定义符号）→ 代码跨度护栏（带 `--emit-relocs` 重链一次，跑 `tools/infra/check_code_range.py`；exec_span ≥ 30 MiB 或 REL26 余量 < 2 MiB 即停，**不**自动切 `-mcmodel=large`）。

工具链细节：安装根的 `clang` 没有默认 target triple（`-dumpmachine` 为 `unknown`），Kbuild 的 `cc-version.sh` 会判成「unknown C compiler」；`make_defconfig.py` 因此把 `--target=dadao-unknown-elf` 的 wrapper 写进**构建树**（运行期产物）并作为 `CC`，同时把 `CLANG_TARGET_FLAGS=dadao-unknown-elf` 传给 make。

补丁集机械校验（含本组件）：

```
make check-patch-tree
python3 tools/infra/check_patch_tree.py --source-state   # 本组件应为 count=1 clean=True
```
