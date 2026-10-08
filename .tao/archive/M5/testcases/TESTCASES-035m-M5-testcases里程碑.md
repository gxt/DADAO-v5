# TESTCASES-035m: M5 testcases 里程碑

**模块**：testcases
**项目里程碑**：M5
**状态**：里程碑
**目标**：测试向量支持 M5——① **SEE/HEE + semihosting 向量**（L1 MC：`trap`/`escape`/`cfx2rc`/`cfx2rd` 编码/往返，`UNSUPPORTED:` 分阶段；L3 执行：semihosting 服务/权限反例/一般 trap+escape），**独立 oracle**（禁从 LLVM/QEMU 反填）；② **exit-port → `SYS_EXIT` 迁移**（范围 = **全部**：M1–M4 所有依赖 exit-port 的向量/harness/oracle；期望值同步；迁移后全量重跑逐项不回归；`ISS-147` 随迁处置/结案）。
**关联任务**：`TESTCASES-033t`、`TESTCASES-034t`（2 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tests/llvm/lit/MC/DADAO/m5-*.s`（+ `README-m5.md`）、`tests/llvm/codegen/m5/`（+ `expected.yaml`）、oracle（`validate_*.py`）；迁移后的向量/harness/oracle
- 独立 oracle EXIT=0；oracle 无 `subprocess`/`os.system`/`Popen`（`grep` rc=1）
- L3 执行经 m5 驱动跑通（逐例「名字/期望/实际/退出码」）
- 迁移覆盖：`grep` 显示无残留依赖 exit-port 的测试侧（或仅披露例外）；期望退出码全落 `0x00–0x7F`（`ISS-147`）
- 不回归：`test-codegen` 15/15、`test-elf` 5/5、`check-lit`、`check-qemu-semantics` 逐项相等
- 反例门控：改期望字节/服务号/退出码 ⇒ 非零 ⇒ 还原回绿
- `make check`/`check-no-residue` EXIT=0

## 核验记录（主会话）

**M5 testcases 里程碑核验（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`**

证据来源：`TESTCASES-033t`/`034t` 完成区/审阅记录、`.work/log/testcases/`、`.work/log/integ/INTEG-020t-*.log`；独立只读复核（`ls`/`grep`/独立跑 oracle）。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务 2 个均 `已验证` | `TESTCASES-033t`/`034t` 头部均 `**状态**：已验证` | ✅ |
| 2 | 产出：L1 MC 向量（`tests/llvm/lit/MC/DADAO/…` + `README-m5.md`） | `tests/llvm/lit/MC/DADAO/README-m5.md` + `cfx2-trap-escape.s`(+`-err.s`)、oracle `validate_cfx_vectors.py`（**L1 复用 `LLVM-060t` 产物**，非 `m5-*.s`——见下「L1 落点偏差」） | ✅ |
| 3 | 产出：L3 执行向量 `tests/llvm/codegen/m5/` + `expected.yaml` | `ls`：10 条 `m5_*.s`（5 semihosting + 4 cfx 权限反例 + 1 trap/escape）、`expected.yaml`、`README.md` | ✅ |
| 4 | 产出：独立 oracle | `tools/testcases/validate_m5_vectors.py`（L3）、`validate_cfx_vectors.py`（L1）；**随产物入库** | ✅ |
| 5 | 独立 oracle EXIT=0；无 `subprocess`/`os.system`/`Popen`（`grep` rc=1） | 本次跑 `validate_m5_vectors.py` → `validate_m5_vectors: PASS (141 checks)`；`grep -nE 'subprocess\|os\.system\|Popen'` → **无命中**（rc=1） | ✅ |
| 6 | L3 执行经 m5 驱动跑通（逐例「名字/期望/实际/退出码」） | `INTEG-020t-test-semihost.log`：`PASS m5_semi_writec expected=64 actual=64 exit=64 (match)` … `Results: 10/10 passed, 0 failed`；`console … (byte-exact)` | ✅ |
| 7 | 迁移覆盖：无残留依赖 exit-port 的测试侧（或仅披露例外） | `grep -rl 'EXIT_PORT\|ffff_8000_0000'` 命中 **恰 6 探针**（`006t/008t/009t/010t/012t/013t`）+ `check_interface_alignment.py`——与 `ISS-169` 披露集合**逐条一致** | ✅ |
| 8 | 期望退出码全落 `0x00–0x7F`（`ISS-147`） | 独立核：`codegen/expected.yaml` max `0x79`、`m4/expected.yaml` max `0x7e`、`m5/expected.yaml` max `0x60`，**无一 > 0x7F** | ✅ |
| 9 | 不回归：`test-codegen` 15/15、`test-elf` 5/5、`check-lit`、`check-qemu-semantics` 逐项相等 | `INTEG-020t-test-semihost.log`：test-elf 5/5、test-codegen 15/15、lit 62/62、`check-qemu-semantics: PASS`（149/149）；`TESTCASES-034t` 记为「改前后逐项相等」 | ✅ |
| 10 | 反例门控（改期望字节/服务号/退出码 ⇒ 非零 ⇒ 还原回绿） | `TESTCASES-033t`/`034t` 证据脚本：各含注入（033t 4 类、034t 3 类）→ 目标断言 FAIL → `cp`+md5 还原 → 回绿；`INTEG-020t` 亦独立注入 | ✅ |
| 11 | `make check`/`check-no-residue` EXIT=0 | `INTEG-020t-test-semihost.log`：`repository checks: PASS`、`check-no-residue: PASS` | ✅ |

**L1 落点偏差（相对本 `m` 原措辞，已披露、非缺口）**：本 `m` 原写 L1 产出为 `tests/llvm/lit/MC/DADAO/m5-*.s`；实际按 `TESTCASES-033t` 的 **DRY 判定**——4 条指令的 L1 MC 向量（编码/往返）**复用 `LLVM-060t` 自带并已接入 `check-lit` 的 `cfx2-trap-escape.s`**（本任务仅补 `README-m5.md` 对照表），不重复引入 `m5-*.s`。功能等价、DRY 合规（`TESTCASES-033t` 审阅记录有「L1 复用 / 无 `UNSUPPORTED:`」的独立核验）。

**跨模块影响处置**：
- `ISS-169`（6 探针保留 exit-port，`scope[qemu,testcases,M6]`）：已披露例外，**不影响 M5 门槛**（进 `make` 门控的测试侧均已迁 `SYS_EXIT`）；建议随 M6 重写。
- `ISS-165`（RAM@0 C1 step2，`scope: M6`）：`tests/vectors/**` 的 `EA=0⇒unmapped` 用例在 R3 下将失效，**当前不在任何 `make` 门控内**，step2 随 M6；不阻断 M5。
- `ISS-147`：**closed**（由 `TESTCASES-034t` 收窄 `0x00–0x7F`）。
- `ISS-120`（探针漂移）：**未扩大**（`TESTCASES-034t` 记录「改前改后日志逐字节相同」）。

**无未处置跨模块项。**

## 审阅记录

#### M5 模块里程碑核验（architect，2026-10-08）

**判决**：**满足 ⇒ `**状态**` 置 `里程碑`**。2 关联任务全 `已验证`；11 项核验逐条通过（独立 oracle 141 checks 且无 `subprocess`、L3 逐例驱动 10/10、迁移残留恰为 `ISS-169` 披露集、期望码全 ≤ `0x7F`、不回归、反例门控、`check`/`check-no-residue` 绿）。

**L1 落点偏差**：`m5-*.s` → **复用 `LLVM-060t` 的 `cfx2-trap-escape.s`**（DRY，已披露）。

**跨模块项**：`ISS-169`（M6）/`ISS-165`（M6）/`ISS-147`（closed）/`ISS-120`（未扩大）——无未处置项。

**边界**：本次仅改本文件（`**状态**` 字段 + `## 核验记录（主会话）` + 本记录）；**`spec/` 交集为空**；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`；未新增/删除任务。
