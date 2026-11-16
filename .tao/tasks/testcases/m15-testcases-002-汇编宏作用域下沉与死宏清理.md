# m15-testcases-002: 汇编宏作用域下沉（共享层 → 册/文件）+ 死宏清理 + 门控

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-001`（已验证：把 10 个 FP 宏下沉到共享层——**本任务按新口径回退其中单册部分**）；`m14-infra-004`（在跑的改名任务）**必须先合入**（两者都改 `tests/inst/**`）
**可并行分片**：否（`tests/inst/**` 单写者）
**预估**：3–4 h（机械搬运 + 字节级对账 + 新门控）
**档位**：中改（多文件搬定义 + 新增门控；复核 ≥2 路注入 + md5 对账）
**状态**：待开始

## 背景（用户 2026-11-15/16 口径）

> 「如果某个宏就只用于某个汇编测试程序，则应该把这个宏移动到该汇编测试中」

即**方向与 `m15-testcases-001` 相反**：`m15-testcases-001` 把 8 个 FP 文件里重复的宏**上抬**到共享层；按本口径，凡**只在一个册（更别说一个文件）里用**的宏都应**下沉**到册/文件，共享层只保留**跨册**宏。

## 现场统计（主会话实测，2026-11-16，`tests/inst/macros/inst_test.inc` = 132 宏 / 2,135 行）

按「反向闭包」统计真实使用者（宏被别的宏调用时继承调用者的使用者）：

- **死宏（使用者 0）**：**14 个 / 166 行** —— `TEST_FAULT_BR1`、`__CHECK_FP_RF`、`__VERIFY_FP_RF`、`__VERIFY_FP_RF_MEM`、`__CHECK_FP_RF_MEM`、`TEST_FPCOPY1..4`、`TEST_FPCOPY_ENC2`、`TEST_FPCOPY_TOP1`、`TEST_FPCOPY_TOP4`、`TEST_FPCOPY_31`、`TEST_FPCOPY_ADJ`；
- **只用 1 个 `.S`**：**18 个 / ≈170 行** —— 如 `TEST_LD_RA`→`01-load-store/ld.o_rrii_ra.S`、`TEST_LD_RB`→`ld.o_rrii_rb.S`、`TEST_LD_RF`→`ld.o_rrii_rf.S`、`TEST_LD_RF_LO32`→`ld.t_rrii_rf.S`、`TEST_ST_RA/RB`→`st.o_rrii_ra/rb.S`、`__CHECK_MEM_RB`→`st.o_rrii_rb.S`、`__VERIFY_MEM_RF`/`__CHECK_MEM_RF`→`02-reg-copy/rf2rf_orri_rf.S`、`TEST_WI_*`(4)→`03-wyde-imm/set.w_rwii_rf.S`、`TEST_AR_SI`/`TEST_FAULT_ALU_SI`→`04-arith-logic-octa/add.si_riii_rd.S`、`TEST_AR_RB_SI`→`05-arith-add/add.si_riii_rb.S`、`TEST_FAULT_RASUF_MEM`→`06-control-flow/ret_riii_ra.S`、`TEST_FPCOPY_RF0`→`00-isa-design/pseudo_set.fx_reg.S`；
- **只用 1 个册（多文件）**：**74 个 / ≈902 行** —— `01-load-store` 9、`02-reg-copy` 7、`03-wyde-imm` 5、`04-arith-logic-octa` 4、`05-arith-add` 5、`06-control-flow` 8、**`07-floating-point` 36**（含 `m15-testcases-001` 上抬的 10 个 FP 宏）；
- **跨册共享（应留共享层）**：**26 个 / 372 行**；
- 合计可下沉 **1,000 行（47%）** + 死宏 166 行。

## 目标

1. **死宏删除**：14 个死宏（166 行）确认无人使用后删除（若有注释指向已退役用例，一并清理）；
2. **单文件宏下沉**：18 个宏从共享层移到其使用文件内（定义放在该文件 `.include` 之后、首个用例之前）；
3. **单册宏下沉**：74 个宏移到**册级 include**（新建 `tests/inst/<册>/<册短名>.inc`，由该册各 `.S` 在共享层之后 `.include`）；`07-floating-point` 的 36 个按此落；
4. **共享层收窄**：`inst_test.inc` 只保留 26 个跨册宏（+ 必要的公共 helper），并在文件头写明「本层只放**跨册**宏；册专用 → 册 `.inc`；单文件 → 该文件内」；
5. **新增门控 `check-inst-macro-scope`（L1）**：机械判三条 —— ① 共享层宏的**跨册使用者数 ≥2**；② 册 `.inc` 里每个宏的使用者**只在该册**；③ `.S` 内定义的宏**只被该文件使用**；任一违反即红（含失败样例自检，证明可 FAIL）。

## 验收（真实 rc + 输出）

1. **零语义变化（核心）**：全部 272 个 `.S` 在全部形态（链例 + 各故障点，形态数从 `run_asm_suite.scan_source` 现场取）下组装，改前/改后 `.o` **md5 逐一相等**（贴 `N/N`）；`make check-inst-asm` **904/904** 且镜像数不变；
2. 静态计数：共享层宏数 132 → **26（±必要的公共 helper，逐条列出）**；死宏 0；单文件/单册宏各自归位（贴脚本现场统计，不写死）；
3. 新门控 `check-inst-macro-scope` 进 L1 且**自检可翻转**（注入一条违规宏 ⇒ 红）；
4. **≥2 路注入**（`cp`+md5 还原）：① 把某册宏挪回共享层 ⇒ 新门控红；② 删掉某册的 `.inc` include ⇒ 组装失败/门控红；
5. 其它门控：`check-tests-index`（`NON_ID_CARRIERS` 等登记不变）、`check-dirs`、`check-no-residue`、`make check` 全绿；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只搬定义、不改任何用例行/宏体语义**（宏体逐字搬运，禁顺手优化）；
- 不新增/删除用例；不改 `inst_test.inc` 之外的共享工具；
- 不提交 git；注入还原 `cp`+md5；临时文件放运行期临时目录；与本任务无关的 `tests/inst/12-misc` 结构去重归 `m15-testcases-003`（勿越界）。

## 审阅记录

（待填）
