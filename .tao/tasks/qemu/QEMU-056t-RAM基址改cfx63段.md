# QEMU-056t: RAM 基址改为 `0xFC00_0000_0000`（cfxha 63 段）

**模块**：qemu
**项目里程碑**：M7
**依赖**：无（M6 已验证态；`INTEG-033k` 裁定 #10）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定原话（2026-10-11；`INTEG-033k §裁定汇总 #10`）：「不想在此阶段引入其它 cfx 支持 ⇒ **有效地址空间只能在 `[47:42]` 为全 1 的情况下进行**；RAM 通常从 0 寻址 ⇒ **改为 `0xFC00_0000_0000`**；后续加 cfx 后此配置可不变」；「**16 MiB 够用 ⇒ 不改大**」。
  - `ADR-0004` rev. 2026-10-11（**就地修订**，覆盖 `R3` 的 RAM 基址口径）：RAM 基址 `0x0000_0000_0000` → **`0xFC00_0000_0000`**；复位向量/ROM（`0xffff_ffff_0000`，64 KiB）与 RAM 容量（16 MiB）不变。
  - `spec/DADAO-12 §2.1`：48 位核内地址 `bits[47:42]` = cfxha；cfxha 63 = `power` 段。`0xFC00_0000_0000` 的 `bits[47:42] = 63`。
  - 现行（M6 `QEMU-053t` 收口后）：`DADAO_RAM_BASE = 0x000000000000`（**唯一 RAM 段**，RAM@0）；`DADAO_RAM_SIZE = 16 MiB`；旧 RAM 段（`0xffff_0000_0000`）与 exit-port 设备已删。
- **输出**：
  1. QEMU 侧 RAM 唯一段基址改为 `0xFC00_0000_0000`：`components/qemu/patches/target/dadao/cpu.h.patch`（`DADAO_RAM_BASE`）、`hw/dadao/dadao-machine.c.patch`、`target/dadao/helper.c.patch`、`cpu.c.patch` 等以 `DADAO_RAM_BASE` 宏为真源的引用**随之生效**（**不写死地址**）。
  2. 测试侧跟改：`tests/scripts/dadao.lds`（`MEMORY RAM ORIGIN`）、`tests/scripts/codegen_crt0.s`、`tests/scripts/bootrom.S`/`bootrom_app.S`、`tests/e2e/*`、`tests/llvm/codegen/**`（如含地址）、`tests/vectors/isa/{ctrl-*,mem-*}.yaml`（地址类期望值，**重派生、禁反填**）。
  3. `tools/testcases/build_test_binary.py`（`BINARY_BASE`/`EXIT_BLOCK`/`DUMP_BASE`）、`tools/qemu/min_rom_probe_*.py`（`SEMI_BLOCK`/栈/数据地址）、`tools/qemu/gen_trampoline.py`（`trampoline.bin`）随地址跟改。
  4. `tools/integ/check_interface_alignment.py`：`RAM_BASE` 断言改为新基址（**从单一真源派生、不写死**）。
  5. `spec/Machine-01-测试机运行环境.md §1`（地址图正文）+ 该册 `sha256` 锁同步。
- **约束**：
  - **`ADR-0004 D5.8` fault 码表冻结不重排**（`0x81`–`0x8D`）；越界分类规则不变（`cfxha==0` 段 ⇒ `CFXMEM 0x81`、其余含 power 段 ⇒ `unmapped 0x87`），但**地址区间随新基址重算**。
  - **不改规范正文以外内容**；`ADR-0004` 正文（决策节点）不改写（`Process-03`）。
  - **计数/地址不写死**：门控计数、地址断言须**派生自单一真源**（`DADAO_RAM_BASE` 宏 / `dadao.lds`）。
  - 只动任务范围，越界须披露。

## 避坑清单（blast radius）

- **M6 `QEMU-053t` 刚把 RAM@0 收口 ⇒ 本次要再改一遍**（`INTEG-033k §避坑`）；改动面横跨 QEMU 补丁、`tests/scripts`、`tests/**`、`tools/**`、`spec/Machine-01`+锁。
- **旧「RAM@0 在 umon 段」越界断言失效**：`0xFC00_0000_0000` 与 boot ROM 同属 cfxha 63（`power`）段但偏移不同 ⇒ `umon` 段（`addr[47:42]==0`）越界 ⇒ `0x81` 的既有用例须复核（新 RAM 已不在 umon 段）。
- **补丁导出纪律**：补丁写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（`AGENTS.md`「组件补丁」）。
- **失败保留现场并继续推进**（`AGENTS.md`「最小安全设计」）。

## 验收标准

1. **地址真源**：QEMU `DADAO_RAM_BASE = 0xFC00_0000_0000`（`grep` 真实输出）；`DADAO_RAM_SIZE = 16 MiB`；**唯一 RAM 段**（无旧 RAM 段/退出端口）。
2. **测试侧一致**：`tests/scripts/dadao.lds` 的 `MEMORY RAM ORIGIN = 0xFC0000000000`；`bootrom`/`crt0`/harness 地址随改；无遗留旧基址（`grep` 现场统计，**不写死计数**）。
3. **门控全绿**：`make check`、`make check-interface`、`make check-qemu-semantics`、`make check-patch-tree` **EXIT=0**；`make test-codegen`/`test-elf`/`test-semihost` PASS。
4. **E2E**：至少一条 ELF 直载 + 一条 raw-bin 路径在新基址下正确退出码（真实输出）。
5. **反例门控**：`check_interface_alignment.py` 注入反例（把断言期望改回 `RAM_BASE=0` 或篡改 `cpu.h` 基址）⇒ **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿（有鉴别力）。
6. **规范同步**：`spec/Machine-01 §1` 地址图改为 `0xFC00_0000_0000`；`sha256` 锁同步（`check-spec-readonly` EXIT=0）。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
