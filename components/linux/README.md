# Linux 组件（linux）

DADAO 的 **Linux 内核移植目标**（M14 起；`arch/dadao/**`）+ **syscall 号表参考**（SPEC-138t 钉住的号表来源：`asm-generic/unistd.h` + `arch/riscv/include/uapi/asm/unistd.h`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "v7.2.10"`，精确 commit `7b20d05f…`）；工作树由 `make fetch` + `make apply-series` 在运行期的组件源目录建立。

M13 及以前本组件只是**参考输入**（`ADR-0025 D2`：无内核目标），故带 `patchless`、无补丁集；M14 起转为**受补丁组件**（`m14-linux-001`），基线不变。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0025`（M8 用户态栈）、`ADR-0006`（浅裸镜像）。
- **现状（首篇为空）**：`series` 零条目、`patches/` 只有 `.gitkeep` —— 这是**空补丁集首态**（`docs/Process-01 §2` 的合法形态），不是 `patchless`。首个补丁由 `m14-linux-002`（`arch/dadao/**` 骨架）落地时在 `series` 追加。
- 落地后的预期范围：`arch/dadao/**`（机器/中断/定时器/页表/启动入口）+ 少量必要上游文件修改（`arch/Kconfig`、`arch/Makefile` 等），具体以各任务书为准。

## 构建与验证

内核侧目标（目标名与脚本路径由 `Makefile` 一次声明；脚本随各任务落地）：

```
make linux-defconfig        # 生成 DADAO defconfig（写者，持 gate.lock）
make linux-vmlinux          # 构建 vmlinux（写者）
make linux-initramfs        # 构建 initramfs（写者）
make linux-semihosting-smoke  # 半主机启动冒烟（写者）
make check-linux-toolchain  # 交叉工具链可用性（只读）
make check-linux-boot-contract  # 启动 ABI 契约（只读）
make check-linux-k0         # K0 收口门控（只读，会增量构建）
```

运行期路径（源树/构建树/initramfs 目录/工具链 bin）**只**由 `tools/linux/paths.py` 从 `manifests/` 解析，脚本不得自行拼路径。

补丁集机械校验（含本组件）：

```
make check-patch-tree
python3 tools/infra/check_patch_tree.py --source-state   # 本组件应为 count=0 clean=True（空补丁集）
```
