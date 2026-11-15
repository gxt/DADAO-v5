# m15-testcases-001: `tests/inst` 载体汇编宏去重下沉（9 个宏 / 8 文件）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`tests/inst` 272 个 `.S` 已全部 `.include` 宏层；M13 载体整理已收口）
**可并行分片**：否（同一宏层单写者）
**预估**：30–45 min（机械去重 + 字节级 md5 对账）
**档位**：中改（9 文件，单点语义 = 纯去重；复核 ≥2 路注入 + md5 对账）
**状态**：待开始

## 背景（用户 2026-11-15 原话）

> 「M15：检查一下tests/inst的所有汇编文件，能改用宏的简化方式就简化一下；此外，lds文件应该统一放在一个目录下，……」

前半句 = 本任务；**后半句（lds 归位）不在本任务范围**（落点待用户裁定，见「不在范围」）。

## 现场事实（主会话实测，2026-11-15）

- `tests/inst` 共 **272 个 `.S` / 28,432 行**，**272/272 都已** `.include "tests/inst/macros/inst_test.inc"`（该宏层 2,028 行 / 122 个宏）；
- 只有 **10 个文件**自带 `.macro`，共 **35 处 / 12 个不同宏**；**每个宏的宏体在全部出现处逐字相同**（按「宏名 + 形参」分组后体哈希各只有 1 种）⇒ 是**纯重复定义**，不是"各册特化"：
  - `__FP_CHK64 pt,dst,exp,flags`：**8 处**（07-floating-point 的 8 个 FP 文件）
  - `__FP_RD1` ×2 / `__FP_RD2` ×2 / `__FP_RD3` ×4（同上 8 文件）
  - `TEST_FPRND` + `TEST_FPRND_ENC` ×2 文件；`TEST_FPSCLB` + `TEST_FPSCLB_ENC` ×2 文件；`TEST_FPSGN` + `TEST_FPSGN_ENC` ×4 文件
  - 单点专用（各 1 处，**保留原地**）：`__ESC_SETIP`/`__LAND_IP_RD`（`11-cfx/escape_ciii_cfx.S`）、`__TRAP_CHKINFO`（`11-cfx/trap_ciii_cfx.S`）
- 宏体只调用共享层已有宏（`__LI`/`__LI_RF`/`__REC`/`__EXIT`/`__VERIFY_RD`）⇒ 下沉不引入新依赖。

## 目标

1. 把**有重复的 9 个宏**（`__FP_CHK64`、`__FP_RD1/2/3`、`TEST_FPRND(_ENC)`、`TEST_FPSCLB(_ENC)`、`TEST_FPSGN(_ENC)`）各留**一份**定义，放进 `tests/inst/macros/inst_test.inc`（放在既有 FP 宏区 `__FP_ENV`/`__FP_CHECK` 附近，写一段说明为什么这 9 个是共享的）；
2. 从 8 个 FP 文件里**删掉**这 9 个宏的本地定义（共 35 − 3(单点专用) = 32 处定义删除）；
3. 3 个单点专用宏**原地不动**（单次使用造抽象无收益），在完成区写明这一判断；
4. **零语义变化**：只搬定义，不改任何宏体、不改任何用例行。

## 验收（逐条贴真实输出与 rc）

1. **宏定义唯一性**（现场派生，不写死）：扫 `tests/inst/**/*.S` + `macros/*.inc`，12 个宏名每个定义**恰好 1 处**；`07-floating-point` 8 个文件内 `.macro` 计数 = 0；
2. **字节级不变**（核心证据）：对 8 个受影响文件，用 `run_asm_suite.py` 同一条命令行（`llvm-mc --triple=dadao-unknown-elf … --defsym CASE_N=<n>`，`-defsym` 缺省 = 链例）在**全部形态**（链例 + 每个故障点）下组装，**改动前/后 `.o` md5 逐一相等**（贴 `N/N` 与形态数现场统计；形态数从 `run_asm_suite.py` 的解析结果取，禁写死）；
3. `make check-inst-asm` **PASS**，镜像/检查点计数与改动前一致（贴 `run_asm_suite:` 汇总行）；
4. **≥2 路可达 FAIL 注入**（`cp` 备份 + md5 还原）：
   ① 改共享层某宏一个立即数（如 `__FP_CHK64` 的 `ext.uo rd21, rd21, 4` → `8`）⇒ 该文件组装产物 md5 变化（或运行结果不同）⇒ 断言红；
   ② 删共享层 `__FP_RD3` ⇒ 组装直接失败（未定义宏）⇒ 断言红；
5. L1 `make check` **rc=0**（贴尾行）；`check-inst-asm` 单跑不看 host 安装根（不跑 `check-modules`、不 `install-host`、不重建任何组件）；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 不在范围（明确排除）

- **lds 归位**（`01-load-store/inst-tiny.lds`、`07-floating-point/inst-tiny-fp.lds` → 单一目录）：**落点待用户裁定**；本任务**不动** lds、不动 `run_asm_suite.py` 的 lds 解析；
- **头注释模板化**（272 文件 3,780 行重复头）：属提案，未获授权，**不做**；
- 不改 `spec/`、`contracts/`、`components/`、`tools/`；不跑三平台（QEMU 单平台足够——本任务不改语义）。

## 硬约束

- 只动 `tests/inst/macros/inst_test.inc` + 8 个 FP `.S` + 本任务书；
- 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore`）；临时文件放 `/tmp/opencode/m15-testcases-001/`。

## 审阅记录

（待填）
