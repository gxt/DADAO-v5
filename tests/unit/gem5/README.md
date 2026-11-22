# unit/gem5 — gem5 裸机 FS 承载的 unit 用例

本目录存放**依赖 gem5 构建产物**的 unit scope 用例。`unit` 覆盖各模块自身功能；
这里的 `platforms: [system]` 指 gem5 Tiny **FS（裸机）** 运行，不是 Kaiwu-Vast 的
arch scope（`tests/arch/`），也不与 `inst`/`tset` 的 system/user 运行模式混用。

## 索引

`tests/unit.yaml`：

- `unit-gem5-hmon-001` → `unit/gem5/check_tiny_hmon.py`（`kind: driver`，
  `platforms: [system]`，`level: full`，`requires: [gem5-fs]`）。
- `.py` 驱动与 arch 的 driver 型一致：索引只静态校验 `file` 存在与字段合法，
  不执行、不解析测试语义。

## 门控层次

- **不进 L2**：`make check-unit` 的成员固定为 lit + codegen + elf + ir-lli +
  picolibc fast，不读 `tests/unit.yaml`；新增本条目不会让它多跑 gem5。
- **不进 L3**：`make check-unit-full` = `check-unit` + `check-lit-full`，同样不读
  `tests/unit.yaml`，也不会拉起 gem5。
- **静态覆盖**只有 L1 `make check-tests-index`（文件存在 / 字段 / 平台 / level /
  id 唯一）。因此本用例是**手工/按需**执行，不冒充门控绿灯。

## 运行

前置：

- gem5 DADAO 构建与 Tiny FS 配置（`make build-gem5` 产出；驱动默认在其默认构建
  落点查找，缺失时退出码 2 并提示）；
- host 工具链 `llvm-mc`、`ld.lld`、`llvm-nm`、`llvm-objcopy`（`make install-host`）；
- 用例资产：`tests/unit/gem5/tiny_hmon/`（应用、链接脚本、独立期望
  `expected.yaml`）与共享固件 `tests/ee-tiny/`。

```sh
make build-gem5
make install-host
python3 tests/unit/gem5/check_tiny_hmon.py \
    --work-dir <运行期证据目录>/tiny-hmon
```

- `--work-dir` 指向**运行期证据目录**；不显式给出时驱动默认落仓库内运行期目录，
  产物不入库。
- `--gem5` / `--config` / `--toolchain-bin` 可显式覆盖默认位置；
  `--max-ticks` 调整仿真上限（默认 2 亿 tick）。
- 驱动内部有 writer-guard：gem5 二进制或工具链在跑批期间被替换即判失败
  （不假 PASS）。

## 判据与耗时

- 退出码：`0` 全部检查通过；`1` 任一检查失败（含负例探针未按预期失败）；
  `2` 缺构建输入（gem5/config/工具链）。
- 判据来源：`tiny_hmon/expected.yaml` 独立派生自 `spec/`，对比 guest 导出的结果表、
  guest 退出码 `0x21` 与 console 的 `hmon-ok` 行。
- 耗时：一次运行含正例 + 多个负例探针（无 BootROM / BootROM 截断 / PT_LOAD 改写 /
  `e_entry` 未固定）的 gem5 启动，实际墙钟随 gem5 构建类型与主机变化；不设门控
  预算，按需执行（当前未接入 night-run 集合）。
