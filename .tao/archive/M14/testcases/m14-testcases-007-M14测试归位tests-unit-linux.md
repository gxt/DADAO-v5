# m14-testcases-007: M14 测试归位 `tests/unit/linux/`

**模块**：testcases
**项目里程碑**：M14
**依赖**：无
**可并行分片**：否（一次性搬迁 + 引用同步）
**预估**：1 h
**档位**：中改（目录搬迁 + import/路径 + 门控发现逻辑）
**状态**：已验证

## 背景（用户 2026-11-21）

M14 的内核测试散在 `tools/linux/`（probe / gate）与 `tests/` 下，和 `tests/unit/llvm`、`tests/unit/picolibc` 的组织方式不一致。用户指示：在 `tests/unit/` 下建 `linux/`，把 M14 用到的测试都放进去。

## 搬迁映射

**移入 `tests/unit/linux/`**（26 个 .py + 3 个探针资产）：
- gate：`check_k0.py`、`check_k1.py`、`check_k2.py`、`check_k3.py`、`check_toolchain.py`、`check_boot_contract.py`、`check_syscall_contract.py`、`check_config_pins.py`
- probe：`k1_boot_probe.py`、`k1_pt_probe.py`、`k2_{irq,time,trap}_probe.py`、`k3_{page,pt}_probe.py`、`k4_{cow,fork,kthread,stack,switch}_probe.py`、`k5_{clocksource,clone,futex,signal,syscall}_probe.py`、`m45_entry_probe.py`
- 资产：`semihost_pa_probe.S`、`semihost_pa_probe.lds`、`semihost_readc_probe.S`

**留在 `tools/linux/`**（构建/公共工具，不是测试）：`paths.py`、`config_pins.py`、`make_defconfig.py`、`make_initramfs.py`、`make_vmlinux.py`、`build_busybox.py`、`toolchain_matrix.json`。

## 连带修改

- 搬迁文件：`parents[2]` → `parents[3]`；对已搬模块的 import 改 `tests.unit.linux.*`，对留下的工具保持 `tools.linux.*`；
- `check_config_pins.py` 的扫描目录改为 `tests/unit/linux` + `tools/linux` 两处（含 self-test 的拷贝与注入路径）；
- `Makefile` 的 11 个目标路径；`contracts/linux-boot.yaml` 的一致性注释；`docs/Process-07` 的脚本路径；`components/linux/README.md`；`tools/linux/config_pins.py` 文档串。

## 验收（真实 rc）

1. 26 个模块全部可 import（`tests.unit.linux.<module>`）⇒ 26/26；
2. `make check-config-pins` **PASS**（96 项，现场统计 21 个切片脚本 / 23 符号 / 51 镜像，脚本发现覆盖新目录）；
3. `make check-linux-toolchain` **PASS**（矩阵 8/8、gaps=2、blockers=0）；
4. `make check-tests-index` **PASS**（472 条）、`make check-dirs` **PASS**；
5. `make check-linux-k0` 的 K12 由 `apply_series` 拒绝（共享源树被在途 `m14-linux-028` 推进到 base+2）——**环境因素**，非搬迁引入；其余 K0 项通过，待 028 合入后复跑。

## 约束

不提交 git（由主会话提交）；不改组件补丁；术语「寄存器组」。
