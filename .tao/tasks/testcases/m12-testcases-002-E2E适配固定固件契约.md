# m12-testcases-002: E2E 测试适配 Tiny 固定固件装载契约

**模块**：testcases
**项目里程碑**：M12
**依赖**：`m13-qemu-002`（QEMU 侧新装载契约）；任务书可在其合并后派单
**可并行分片**：否（测试资产单写者）
**状态**：待开始

## 背景

`m12-spec-004` 把 Tiny 的装载改为「**BootROM 固定固件 + 应用**」两件：

- BootROM 64 KiB 固定固件（power 8K / hmon 8K / 保留 40K / 表 8K），宿主**不得**向其下发 `PT_LOAD`
- `crt` 与测试程序一起链接、整体落 SRAM；入口固定 `0xffff_ff01_0100`
- 宿主只装 SRAM

`m12-chipyard-007` 已按新契约实现；`m13-qemu-002` 正在改 QEMU。

**现状**：`make check-modules`（L2）有 **8 个 `DADAO-E2E` 用例红**，全部沿用旧模型（`crt` 落 BootROM、`-kernel` 直接跑 ELF），例如：

```
FAIL: DADAO-E2E :: p2align_e2e.test (19 of 163)
RUN: ld.lld -T tests/shared/linker/dadao-tiny.lds crt0.o main.o -o prog.elf
RUN: timeout 30 qemu -M dadao-tiny -kernel prog.elf -semihosting-config ...
```

## 目标

1. **链接脚本**：`tests/shared/linker/dadao-tiny.lds` 改为「`crt` + 应用全部落 SRAM、入口 `0xffff_ff01_0100`」，不再把 `crt` 放 BootROM。
2. **参考启动代码**：`tests/shared/crt0/minimal_crt0.s`（及其它 E2E 使用的 crt）随新布局调整（设 SP、跳 `main`、`rd8` 返回 → semihosting `SYS_EXIT`）。
3. **E2E RUN 行**：8 个 `tests/unit/llvm/e2e/lit/*.test` 的调用改为「固件 + 应用」两件（`-bios`/`bootrom-image` 装 `bootrom.tiny.img`，`-kernel` 装应用 ELF）；固件用仓库内构建器产出的镜像，**不新增第三份固件**。
4. **零回归**：`make check-modules`（L2）/`check-lit`/`check-unit` 全绿；其它 155 个 lit 用例不受影响。

## 非范围

- 不改 QEMU/gem5/chipyard 实现
- 不改 spec
- 不改 `m13-testcases-006` 的输出判据

## 验收标准

1. 8 个 `DADAO-E2E` 用例恢复绿（`make check-modules` rc=0）
2. 这些用例的 ELF **符合新契约**：`e_entry == 0xffff_ff01_0100`、无段落 BootROM（可用 `readelf`/`llvm-readelf` 断言）
3. 固件来源单一：`bootrom.tiny.img` 由仓库构建器产出（`build_tiny_bootrom.py`），测试不内嵌手工固件
4. 反例：故意把 `crt` 放回 BootROM ⇒ 用例**必须失败**（可达 FAIL，证明契约真的生效）
5. `check-lit` 163/163（或现场总数）不回归
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 测试资产是共享文件：本任务期间不得有其它任务改 `tests/unit/llvm/e2e/**`、`tests/shared/linker/**`、`tests/shared/crt0/**`。
- 若发现 `crt0` 改动牵连多个套件，**停下登记**并返回主会话（可能需要拆任务）。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
