# QEMU-039m: M2 qemu 里程碑

**模块**：qemu
**项目里程碑**：M2
**状态**：里程碑
**目标**：QEMU 执行层随 M2 收口——trans 假绿修复与命名同步、`st` 零号寄存器/RA（RACNT/MRPTR）/D8 地址语义修正、`ret rd0` 与 `mreg_range_overlap` 运行期 ILLI、**FP 执行层 60/60**（RF 搬运/位级/softfloat 转换/算术四批）与 **`dst_rd0@FP` 运行期 ILLI**（`QEMU-038t`）；`make check` 全绿（`check-qemu-semantics` 149/149）、`check_qemu_trans` 227/227。
**关联任务**：`QEMU-024t`、`QEMU-025t`、`QEMU-026t`、`QEMU-027t`、`QEMU-028t`、`QEMU-029t`、`QEMU-030t`、`QEMU-031t`、`QEMU-032t`、`QEMU-033t`、`QEMU-034t`、`QEMU-035t`、`QEMU-036t`、`QEMU-037t`、`QEMU-038t`（15 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`components/qemu/patches/**`（现 69 = llvm 37 + qemu 32，含 `trans_fp.c.inc.patch`）、`tools/qemu/min_rom_probe_03{4,5,6,7,8}t.py`
- FP 执行层 60/60（四探针）、`dst_rd0@FP`（`_038t`）、`make check` 全绿

## 核验记录（2026-10-04，architect 核验）

**关联任务**：`QEMU-024t`~`QEMU-038t`（15/15）全部 `已验证`（`030t` 推翻 M1 已验收的 RA 行为）。

**命令核验（真实输出，2026-10-04）**：
```
$ python3 tools/qemu/min_rom_probe_034t.py   → Main: 59/59 passed ; Overall: PASS   EXIT=0   (RF 搬运族 16)
$ python3 tools/qemu/min_rom_probe_035t.py   → Main: 77/77 passed ; Overall: PASS   EXIT=0   (位级族 10)
$ python3 tools/qemu/min_rom_probe_036t.py   → Main: 113/113 passed ; Overall: PASS EXIT=0   (转换族 20)
$ python3 tools/qemu/min_rom_probe_037t.py   → Main: 91/91 passed ; Overall: PASS   EXIT=0   (算术族 14)
   ⇒ FP 执行层 16+10+20+14 = 60/60
$ python3 tools/qemu/min_rom_probe_038t.py   → Main: 42/42 passed ; Overall: PASS   EXIT=0   (dst_rd0@FP 运行期 ILLI)

$ make check   → check-qemu-semantics: Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors；EXIT=0
$ python3 tools/qemu/check_qemu_trans.py → check_qemu_trans: 227/227 insns have trans impl (M1 152/152)
```
（探针日志 `.work/log/qemu/M2-milestone-probe-03{4..8}t.log`；`trans_fp.c.inc.patch` 实测含 **60 个 `trans_`**。）

**跨模块影响**：FP 合法性合约（spec）↔ 运行期实现（qemu）双侧闭合；`check-interface` 80/80、`check-scope` PASS ⇒ 无未处置项。

**结论**：核验通过，置 `里程碑`。
