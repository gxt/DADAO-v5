<!-- 现场生成，勿手改 -->

# M17 — wuming 时序：chipyard 实测 vs gem5 模型

> 本文件由 `tools/gem5/compare_chipyard.py report` 生成，**禁手改**：表里每个数字
> 都来自同一次运行的两个引擎原始输出，改数据就重跑。

- 生成时间：2026-11-15 02:36:15（UTC）；ELF 优化级 `-O2`，同一文件双跑
- 数据来源：chipyard `+verbose` 的逐指令 `exec` 轨迹（`ip/inst/cycle`）、gem5 `stats.txt` 的 `simInsts`/`numCycles`（hooks on/off 各一次）、两者各自 `semi.out` 的板级打点
- 机器指纹：x86_64 / 64 核；chipyard `079ae01569e5fbf9fa9944bd6aee89cd`、gem5 `7c68859e48aa8a53ac96868fd2185f5c`、周期表 `08d050ea65cbf6fdecd4ec5288d94bcd`、doc `2cf2f3cb58947a64668e7af59e5fce72`
- 复现：§6 一条命令（build 复用 embench e2e 驱动，run 双引擎，report 只读原始输出）
- 机器画像 `tiny`：SRAM `0xffffff000000` + 8 MiB，SP `0xffffff7eff00`（`tests/shared/machine-profiles.yaml`）
- gem5 `se_timing`：TimingSimpleCPU + NoncoherentXBar + SimpleMemory，1 GHz；mem `0xffffff000000`+15.94 MiB（至 `StackBase`），`--max-stack 8454144`（栈预留与 SRAM 窗口由 `StackBase` 与 SP 现场推出）
- `report` 先跑 `gen_wuming_cycles.py --check`：周期表不是文档的活解析就直接停
- 规模：3 例（embench-IoT 子集，取全语料指令数最小的 3 个；选择依据由 `run.sh` 现场复算）

口径：

- chipyard 每指令拍数 = 相邻 `exec` 进入拍差（与 `docs/core-wuming-cycle-model.md`
  §5 同一方法）；只统计 `+loadmem` 装载窗内的**应用**指令，BootROM/hmon 固件单列。
- gem5 每类拍数 = 生成表逐行求和（`on − off` 实测差值对账，C4）；
  `gem5 取指/基础` = hooks off 的周期（1 拍/指令 + 指令侧内存时序）。
- 比值 = gem5 周期 / chipyard 周期（模型 / 实测）；>1.5 的例在 §3 给归因。

## 1. 总览

| 例 | 应用指令数 | 固件指令 | chipyard 周期 | gem5 周期 | gem5 模型部分 | gem5 取指/基础 | 比值 | Δ 周期 | chipyard 墙钟 |
|---|---|---|---|---|---|---|---|---|---|
| `ud` | 3666901 | 126 | 11476575 | 35628680 | 6293472 | 29335208 | 3.10 | +24152105 | 3410 s |
| `aha-mont64` | 3087737 | 126 | 6949075 | 25574829 | 872933 | 24701896 | 3.68 | +18625754 | 2057 s |
| `depthconv` | 4288001 | 126 | 10079080 | 39767332 | 5463324 | 34304008 | 3.95 | +29688252 | 2957 s |

Δ 周期 = gem5 − chipyard（正 = 模型比硬件贵）。

## 2. 逐族拍数（周期模型 §2 的类）

### `ud`

- 应用指令 3666901，chipyard 11476575 拍（含取指摊销，逐指令实测），gem5 35628680 拍 = 模型 6293472 + 取指/基础 29335208；未解析助记符 0 条、歧义行 0 条（两者为 0 时逐族归因即完整；gem5 列是**额外**拍数，execute 的 1 拍记在「取指/基础」里）

| 族（类） | 指令数 | chipyard 拍 | chipyard/指令 | gem5 模型拍（额外） | gem5/指令 | Δ 拍 |
|---|---|---|---|---|---|---|
| C | 578331 | 5392235 | 9.32 | 4626648 | 8.00 | -765587 |
| A | 1870985 | 2438885 | 1.30 | 101802 | 0.05 | -2337083 |
| A2 | 351311 | 1664258 | 4.74 | 505582 | 1.44 | -1158676 |
| D′ | 616202 | 1643219 | 2.67 | 616202 | 1.00 | -1027017 |
| B1 | 208962 | 271472 | 1.30 | 417924 | 2.00 | +146452 |
| B3 | 37506 | 37506 | 1.00 | 0 | 0.00 | -37506 |
| A3/A4 | 3594 | 28746 | 8.00 | 25158 | 7.00 | -3588 |
| D | 6 | 176 | 29.33 | 156 | 26.00 | -20 |
| F/G1/G2 | 4 | 76 | 19.00 | 0 | 0.00 | -76 |

### `aha-mont64`

- 应用指令 3087737，chipyard 6949075 拍（含取指摊销，逐指令实测），gem5 25574829 拍 = 模型 872933 + 取指/基础 24701896；未解析助记符 0 条、歧义行 0 条（两者为 0 时逐族归因即完整；gem5 列是**额外**拍数，execute 的 1 拍记在「取指/基础」里）

| 族（类） | 指令数 | chipyard 拍 | chipyard/指令 | gem5 模型拍（额外） | gem5/指令 | Δ 拍 |
|---|---|---|---|---|---|---|
| A | 2830666 | 5184237 | 1.83 | 817344 | 0.29 | -4366893 |
| A2 | 245117 | 1718748 | 7.01 | 10304 | 0.04 | -1708444 |
| C | 3868 | 35850 | 9.27 | 30944 | 8.00 | -4906 |
| B1 | 6151 | 6151 | 1.00 | 12302 | 2.00 | +6151 |
| D′ | 1913 | 3873 | 2.02 | 1913 | 1.00 | -1960 |
| A3/A4 | 18 | 138 | 7.67 | 126 | 7.00 | -12 |
| F/G1/G2 | 4 | 76 | 19.00 | 0 | 0.00 | -76 |

### `depthconv`

- 应用指令 4288001，chipyard 10079080 拍（含取指摊销，逐指令实测），gem5 39767332 拍 = 模型 5463324 + 取指/基础 34304008；未解析助记符 0 条、歧义行 0 条（两者为 0 时逐族归因即完整；gem5 列是**额外**拍数，execute 的 1 拍记在「取指/基础」里）

| 族（类） | 指令数 | chipyard 拍 | chipyard/指令 | gem5 模型拍（额外） | gem5/指令 | Δ 拍 |
|---|---|---|---|---|---|---|
| C | 580722 | 5280759 | 9.09 | 4645776 | 8.00 | -634983 |
| A | 3223206 | 3748704 | 1.16 | 104960 | 0.03 | -3643744 |
| A2 | 54348 | 422821 | 7.78 | 679 | 0.01 | -422142 |
| D′ | 164023 | 337934 | 2.06 | 164023 | 1.00 | -173911 |
| B1 | 262400 | 262400 | 1.00 | 524800 | 2.00 | +262400 |
| A3/A4 | 3298 | 26384 | 8.00 | 23086 | 7.00 | -3298 |
| F/G1/G2 | 4 | 76 | 19.00 | 0 | 0.00 | -76 |

## 3. 归因（比值 >1.5 的例：哪一族贡献多少）

`Δ = gem5 − chipyard`。每例把 Δ 拆成「逐族模型差」与「gem5 取指/基础」两部分；
后者是 TimingSimpleCPU 的指令侧时序（模型之外），硬件侧没有对应项 —— chipyard 的
取指代价已经摊销在它的逐指令拍差里（这正是 §5 的测量方法）。

### `ud`：Δ +24152105 拍，比值 3.10（>1.5，归因如下）

| 来源 | Δ 拍 | 占 Σ\|各行\| | 每指令差异 | 归因 |
|---|---|---|---|---|
| A | -2337083 | 6.7% | -1.25 | 寄存器算术 -1.25 拍/指令（模型按 1 拍，硬件含取指摊销） |
| A2 | -1158676 | 3.3% | -3.30 | 分支/跳转 -3.30 拍/指令（取指惩罚在模型里是 1 拍） |
| D′ | -1027017 | 3.0% | -1.67 | 块复制 -1.67 拍/指令（1+N 模型） |
| C | -765587 | 2.2% | -1.32 | 单次访存 -1.32 拍/指令（模型 1 元素 + 1 beat；硬件含背压/往返） |
| B1 | +146452 | 0.4% | +0.70 | 乘法 +0.70 拍/指令（模型取「可配」初值 3 拍） |
| B3 | -37506 | 0.1% | -1.00 | 除法/取余 -1.00 拍/指令（文档标「待实测」⇒ 模型计 0，provenance 规则） |
| A3/A4 | -3588 | 0.0% | -1.00 | RAS 调用/返回 -1.00 拍/指令（模型按 RegRAS/MemRAS 取固定值） |
| F/G1/G2 | -76 | 0.0% | -19.00 | `trap`（semihosting）-19.00 拍/指令：硬件 1 拍 + 宿主往返，模型只计 1 拍 |
| D | -20 | 0.0% | -3.33 | 多元素访存 -3.33 拍/指令（元素+beat 模型 vs 硬件流水） |
| gem5 取指/基础（模型外） | +29335208 | 84.3% | +8.00 | TimingSimpleCPU 每条指令的取指/内存时序；chipyard 侧无对应项 |
| chipyard 退出尾部 | -2 | 0.0% | -0.00 | 最后一条应用到 `SYS_EXIT` 的拍数（模型按 1 拍的 trap 计） |

> **反事实**（reviewer 补算）：取指若按硬件摊销 0.06 拍/指令，则本表三例的「模型/实测」比分别为 **0.57 / 0.15 / 0.57×** —— 即**模型部分本身比硬件便宜 1.8–6.6 倍**，3.1–3.9× 的差距全部来自 gem5 无 icache 的取指结构（脚本 `--engine` 暂不支持 icache 变体）。

主导项：**gem5 取指/基础**（+29335208 拍，占 Σ\|各行\| 的 84.3%）。

### `aha-mont64`：Δ +18625754 拍，比值 3.68（>1.5，归因如下）

| 来源 | Δ 拍 | 占 Σ\|各行\| | 每指令差异 | 归因 |
|---|---|---|---|---|
| A | -4366893 | 14.2% | -1.54 | 寄存器算术 -1.54 拍/指令（模型按 1 拍，硬件含取指摊销） |
| A2 | -1708444 | 5.5% | -6.97 | 分支/跳转 -6.97 拍/指令（取指惩罚在模型里是 1 拍） |
| B1 | +6151 | 0.0% | +1.00 | 乘法 +1.00 拍/指令（模型取「可配」初值 3 拍） |
| C | -4906 | 0.0% | -1.27 | 单次访存 -1.27 拍/指令（模型 1 元素 + 1 beat；硬件含背压/往返） |
| D′ | -1960 | 0.0% | -1.02 | 块复制 -1.02 拍/指令（1+N 模型） |
| F/G1/G2 | -76 | 0.0% | -19.00 | `trap`（semihosting）-19.00 拍/指令：硬件 1 拍 + 宿主往返，模型只计 1 拍 |
| A3/A4 | -12 | 0.0% | -0.67 | RAS 调用/返回 -0.67 拍/指令（模型按 RegRAS/MemRAS 取固定值） |
| gem5 取指/基础（模型外） | +24701896 | 80.2% | +8.00 | TimingSimpleCPU 每条指令的取指/内存时序；chipyard 侧无对应项 |
| chipyard 退出尾部 | -2 | 0.0% | -0.00 | 最后一条应用到 `SYS_EXIT` 的拍数（模型按 1 拍的 trap 计） |

主导项：**gem5 取指/基础**（+24701896 拍，占 Σ\|各行\| 的 80.2%）。

### `depthconv`：Δ +29688252 拍，比值 3.95（>1.5，归因如下）

| 来源 | Δ 拍 | 占 Σ\|各行\| | 每指令差异 | 归因 |
|---|---|---|---|---|
| A | -3643744 | 9.2% | -1.13 | 寄存器算术 -1.13 拍/指令（模型按 1 拍，硬件含取指摊销） |
| C | -634983 | 1.6% | -1.09 | 单次访存 -1.09 拍/指令（模型 1 元素 + 1 beat；硬件含背压/往返） |
| A2 | -422142 | 1.1% | -7.77 | 分支/跳转 -7.77 拍/指令（取指惩罚在模型里是 1 拍） |
| B1 | +262400 | 0.7% | +1.00 | 乘法 +1.00 拍/指令（模型取「可配」初值 3 拍） |
| D′ | -173911 | 0.4% | -1.06 | 块复制 -1.06 拍/指令（1+N 模型） |
| A3/A4 | -3298 | 0.0% | -1.00 | RAS 调用/返回 -1.00 拍/指令（模型按 RegRAS/MemRAS 取固定值） |
| F/G1/G2 | -76 | 0.0% | -19.00 | `trap`（semihosting）-19.00 拍/指令：硬件 1 拍 + 宿主往返，模型只计 1 拍 |
| gem5 取指/基础（模型外） | +34304008 | 87.0% | +8.00 | TimingSimpleCPU 每条指令的取指/内存时序；chipyard 侧无对应项 |
| chipyard 退出尾部 | -2 | 0.0% | -0.00 | 最后一条应用到 `SYS_EXIT` 的拍数（模型按 1 拍的 trap 计） |

主导项：**gem5 取指/基础**（+34304008 拍，占 Σ\|各行\| 的 87.0%）。

## 4. 检查（任一 FAIL 则本报告判红）

| 例 | 检查 | 结果 | 现场值 |
|---|---|---|---|
| `ud` | C1a chipyard guest exit | PASS | `expected=0 actual=0` |
| `ud` | C1b gem5 guest exit | PASS | `expected=0 actual=0` |
| `ud` | C1c chipyard board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `ud` | C1d gem5 board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `ud` | C1e chipyard sim binary stable | PASS | `md5 before == after` |
| `ud` | C2 same instruction count | PASS | `chipyard(app window)= 3666901 gem5=3666901 chipyard boot/firmware=126` |
| `ud` | C3 chipyard cycle accounting | PASS | `app cycles=11476575 sum(deltas)=11476573 tail=2` |
| `ud` | C5 instruction join (word at IP) | PASS | `mismatched=0/3667027` |
| `ud` | C4 gem5 model accounting | PASS | `table-recomputed=6293472 measured(on-off)=6293472 unobservable=0` |
| `aha-mont64` | C1a chipyard guest exit | PASS | `expected=0 actual=0` |
| `aha-mont64` | C1b gem5 guest exit | PASS | `expected=0 actual=0` |
| `aha-mont64` | C1c chipyard board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `aha-mont64` | C1d gem5 board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `aha-mont64` | C1e chipyard sim binary stable | PASS | `md5 before == after` |
| `aha-mont64` | C2 same instruction count | PASS | `chipyard(app window)= 3087737 gem5=3087737 chipyard boot/firmware=126` |
| `aha-mont64` | C3 chipyard cycle accounting | PASS | `app cycles=6949075 sum(deltas)=6949073 tail=2` |
| `aha-mont64` | C5 instruction join (word at IP) | PASS | `mismatched=0/3087863` |
| `aha-mont64` | C4 gem5 model accounting | PASS | `table-recomputed=872933 measured(on-off)=872933 unobservable=0` |
| `depthconv` | C1a chipyard guest exit | PASS | `expected=0 actual=0` |
| `depthconv` | C1b gem5 guest exit | PASS | `expected=0 actual=0` |
| `depthconv` | C1c chipyard board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `depthconv` | C1d gem5 board markers | PASS | `3/3 ['[board:init]', '[board:start]', '[board:stop]']` |
| `depthconv` | C1e chipyard sim binary stable | PASS | `md5 before == after` |
| `depthconv` | C2 same instruction count | PASS | `chipyard(app window)= 4288001 gem5=4288001 chipyard boot/firmware=126` |
| `depthconv` | C3 chipyard cycle accounting | PASS | `app cycles=10079080 sum(deltas)=10079078 tail=2` |
| `depthconv` | C5 instruction join (word at IP) | PASS | `mismatched=0/4288127` |
| `depthconv` | C4 gem5 model accounting | PASS | `table-recomputed=5463324 measured(on-off)=5463324 unobservable=0` |

**汇总结论：PASS**（27 条检查，0 条 FAIL）

## 5. 已知口径偏差（引用，属 `m16-chipyard-001` 回填项）

- `rd2rd` 类实测 `1+N`（文档 §3 02 行写的 `1+N` 与该实测一致）；
- `ra2rd`/`rd2ra` 实测 `1+N`，而文档该行仍标「未测」⇒ 模型按 provenance 规则计 0；
- `stm` 比模型多 1 拍且零方差（`stm.o` N=8 实测 73、`stm.b` 17）。

三条都不是本任务的修改项：本报告的 chipyard 列按**实测**呈现、gem5 列按**生成表**
呈现，因此它们只会以 `D′`/`D` 两行的差值形式出现，不做任何修补。

## 6. 复现

```
python3 tools/gem5/compare_chipyard.py all \
    --only ud,aha-mont64,depthconv --opt O2 \
    --work-dir <运行期目录> --jobs 3 --max-cycles 60000000 \
    --md docs/TestReports/M17-wuming-timing.md
```

`build` 复用 `tools/testcases/tset/embench/run_embench_e2e.py` 的编译行（tiny
profile + freestanding runtime），ELF 与 L2 `check-tset-embench-*` 同源；`run` 每例
跑 chipyard 一次（带 `+verbose` 轨迹）+ gem5 两次（hooks on/off）；`report` 只读
原始输出并重跑周期表门控。
