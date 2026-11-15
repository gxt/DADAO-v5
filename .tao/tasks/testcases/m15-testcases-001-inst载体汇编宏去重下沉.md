# m15-testcases-001: `tests/inst` 载体汇编宏去重下沉（9 个宏 / 8 文件）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`tests/inst` 272 个 `.S` 已全部 `.include` 宏层；M13 载体整理已收口）
**可并行分片**：否（同一宏层单写者）
**预估**：30–45 min（机械去重 + 字节级 md5 对账）
**档位**：中改（9 文件，单点语义 = 纯去重；复核 ≥2 路注入 + md5 对账）
**状态**：待验收

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
- 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore`）；临时文件放运行期临时目录。

## 审阅记录

### 第 1 轮 engineer 自审

逐行复核：`inst_test.inc` 新增区（10 个宏块 + 4 行说明）与 8 个 `.S` 的删除区；`git diff` 逐 hunk 核对（9 文件各 1 个 hunk：8 个纯删、1 个纯增，无夹带改动）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 宏体是否逐字搬运（怕手打漂移） | ✅已修 | 用脚本从原文件提取宏块原文拼装，不重打 | 10 个宏体 sha256 与改动前同位置逐一相等（如 `__FP_CHK64` 9473d635、`TEST_FPSGN` 3a288409） |
| F2 宏块间空行与既有风格不一致（2 空行 vs 1 空行） | ✅已修 | 插入区压成单空行 | 复跑四类检查全绿；`.o` md5 22/22 不变 |
| F3 宏说明文字被我改写（`符号源rf`/`符号值` 等） | ✅已修 | 4 行说明改回册文件原文（`符号源`/`符号源值`） | 同上（注释不产物，md5 不变） |
| F4 验收脚本 `resolve()` 判错仓库根 | ✅已修 | 改用不解析软链的 `absolute()` + 校验宏层存在 | 首跑 FAIL（扫到 8 处重复）→ 修后 0 重名 |
| F5 独立组装树缺 `tests/shared/asm/*.inc` | ✅已修 | 前后两树一并带 `machine-tiny.inc`/`machine.inc` | 组装成功，22/22 md5 相等 |
| F6 `--real` 注入把反例注了两次（还原前已变异） | ✅已修 | 去掉重复注入，只留公共段一次 | `--real` 全绿 + `md5sum -c` 复原 OK |

判决：无未修项 ⇒ `**状态**` → `待验收`。

### 第 1 轮 reviewer 验收

1. **宏体逐字节**（脚本现算、不归一化空白）：`git show 35339a36:<file>` 各出现处 `.macro…endm` 原始字节 vs `inst_test.inc` 新定义 ⇒ **13/13 相等**（10 个共享宏 sha 逐一相同，如 `__FP_CHK64` cc19f1a3e3c7b010；3 个单点专用仍各 1 处且字节相等）。
2. **删除干净**：全库 `.S`+`.inc`（273 文件）宏名集合 改前 == 改后（135 名；157 处 → 135 处、0 重名，13 个目标名各恰 1 处）；`07-floating-point` 50 文件 `.macro` 计数 = **0**。
3. **无夹带**：8 文件各 1 hunk、**added 行 0**；删除行逐行分类 = 宏头/endm/宏体/`@@`注释/空行，「其它」=0；「基线 − 删除行」重建 == 改后文件 8/8 True；`inst_test.inc` 1 个纯增 hunk（+106/−0）。
4. **字节级独立重跑**（命令行取自 `run_asm_suite.build()`，形态现场由 `scan_source` 派生）：8 文件 × 22 形态（fornd/ftrnd 各 5、其余各 2）⇒ 改前/改后 `.o` md5 **22/22 相等**。
5. **`make check-inst-asm`（我自跑）**：`run_asm_suite: 272 个 id / 904 个镜像 / 平台 qemu / jobs=62`、`run_asm_suite: 904/904 镜像通过（272 个 id；链例 271，故障例 633）`、`check-inst-asm: PASS`、EXIT=0（日志 904 PASS / 0 FAIL）；基线树 `scan_source` 现算同为 272/904/271 链例 id/633 故障例。
6. **L1**：`make check` ⇒ `repository checks (L1): PASS`，EXIT=0。
7. **2 路自设计注入**（`cp` 备份 + md5 还原，非 engineer 那两路）：① `__FP_RD2` 的 `__LI \ereg, \eval` → `\eval+1` ⇒ fosclb 5 形态 md5 全变（5/5），运行红 `[FAIL] fosclb_orrr_rf.S chain … rc {'qemu': 1}` rc=1；② `__FP_CHK64` `br.eq`→`br.ne` ⇒ fornd `.o` md5 变 + 运行红 `[FAIL] fornd_orri_rf.S chain … rc {'qemu': 1}` rc=1；两次还原后 md5 == `9fbc946cfa65f55f32c910519c75d0ba`、子集回绿 rc=0，`git status --porcelain -uall` 干净。
8. **证据脚本**：审 `run.sh`/`verify.py`（断言均有可达 FAIL 路径、计数现场派生、无恒真）并重跑 ⇒ `=== run.sh 汇总: ALL_PASS (rc=0)`（含其自带 check-inst-asm rc=0）。
9. **越界**：`git diff --name-only 35339a36 HEAD` = 8×`07-floating-point/*.S` + `macros/inst_test.inc` + 本任务书（10 文件）；`.lds`/`run_asm_suite.py`/`spec`/`contracts/`/`tools/`/`components/` 0 改动；完成区 14 行、无运行期路径。
10. **判决：Accepted**。非阻断 finding（文档级，architect 收尾顺手改）：「硬约束」留有 `/tmp/opencode/<任务ID>` 具体临时路径（基线文本、非本次改动），宜按「任务书不写运行期路径」改为「运行期临时目录」。

## 完成区

**测试结果**：通过 5/5 验收项（宏唯一性、字节级 md5、check-inst-asm、2 路注入、L1）；一键证据 `.work/evidence/<任务ID>/run.sh`（`--no-gate` 可跳过 L2）四段全绿。
**修改文件**：`tests/inst/macros/inst_test.inc`（+106 行：10 个宏块 + 4 行说明）；8 个 `tests/inst/07-floating-point/*.S`（fornd/ftrnd 各 −41、fosclb/ftsclb 各 −43、fosgnj/fosgnn/ftsgnj/ftsgnn 各 −47，合计 −356）；本任务书。合计 +106 / −356，无越界。
**验收结果**：
1) 宏唯一性（现场派生）：273 个 `.S`+`.inc` / 135 处定义 / 135 个（名,形参）组 ⇒ 全库 **0 重名**；**13 个名字各 1 处**（9 个逻辑宏 = 10 个名字下沉到 `inst_test.inc`：`__FP_CHK64`、`__FP_RD1/2/3`、`TEST_FPRND(_ENC)`、`TEST_FPSCLB(_ENC)`、`TEST_FPSGN(_ENC)`；3 个单点专用仍在 `11-cfx` 两文件）；`07-floating-point` 的 `.macro` 计数 = **0 个 / 0 文件**。
2) 字节级：8 文件 × 22 个形态（现场从 `run_asm_suite.scan_source` 派生：fornd/ftrnd 各 5 = 链例+4 故障点，其余 6 文件各 2 = 链例+1）⇒ 改动前（git 基线 `35339a36` 树）与改动后 `.o` md5 **22/22 逐一相等**；另 10 个宏体 sha256 与改动前逐一相等。
3) `make check-inst-asm`：**PASS**，汇总 `run_asm_suite: 272 个 id / 904 个镜像 / 平台 qemu / jobs=62` + `904/904 镜像通过（272 个 id；链例 271，故障例 633）`，与改动前基线**逐字相同**。
4) 可达 FAIL 注入（cp 备份 + md5 对账，临时树与真实共享层各跑一遍）：① `__FP_CHK64` 的 `ext.uo rd21, rd21, 4`→`8` ⇒ fornd 链例 `.o` md5 2ea7a992… → dd8a59f9…（红），还原后回绿；② 删 `__FP_RD3` ⇒ 组装 rc=1（`error: invalid operand for instruction`，宏名被当指令），还原后 md5 一致且回绿。
5) L1 `make check`：**rc=0**，尾行 `repository checks (L1): PASS`（42 个 PASS 段）。未跑 `check-modules`/`install-host`，未重建组件、未触碰节点。
**新发现/坑**：
- 工作树的 `.work` 是**指向共享运行期目录的软链**；验收脚本用 `Path(__file__).resolve()` 推仓库根会判到**别的工作树**（首跑扫到未改动树 ⇒ 误报 8 处重复定义）。改用不解析软链的 `absolute()` 并校验宏层文件存在（fail-closed）。
- `inst_test.inc` 会再 `.include` `tests/shared/asm/{machine-tiny,machine}.inc` ⇒ 独立组装树必须一并带这两个文件，否则 `Could not find include file`。
- 删掉宏定义后，残留调用点报的是 `invalid operand for instruction`（被当指令），**不是** "unknown macro"；断言要按此措辞匹配。
- 既有小噪声（**不在本任务范围**）：`11-cfx/cfx2rd_crrr_cfx.S` 留有孤立的「本文件局部宏」段头而段内无任何 `.macro`，可留作后续清理。
**遗留问题**：无。3 个单点专用宏（`__ESC_SETIP`/`__LAND_IP_RD` 在 `escape_ciii_cfx.S`、`__TRAP_CHKINFO` 在 `trap_ciii_cfx.S`）按任务书判断**原地保留**：各只 1 处使用，抽到共享层无收益、反而抬高全局命名面。
