# m18-testcases-004: 异步 escape 出口帧向量与探针（任务链第 2 环）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编器支持 `escape cfxHA`）、`m18-qemu-008`（可选，用于执行侧证据）；RTL/gem5/IDL 执行证据待各自任务
**可并行分片**：否
**预估**：3–4 h（标定：同档 testcases-003 2–3 h；本任务覆盖 cg5/cg9 新布局 + escape 五类判据，取 1.2–1.5×）
**档位**：中改（独立向量 + 探针）
**状态**：已验证
**执行环境**：本地（QEMU `kaiwu-vast`；RTL/gem5 视可用性）

## 背景

`m18-spec-007` 定了出口帧：`cg5 rc0`–`rc3` 入口记录（只读）、`rc8`–`rc11` 出口意图；`cg9 rc0`–`rc4` 记录/源集合、`rc14` switch、`rc15` vector；`escape cfxHA` 按 `rc8`–`rc11` 返回并把 `rc11` 整字写目标 monitor `cg8 rc1`。目前没有任何独立向量覆盖这些判据，实现任务（QEMU/RTL/gem5/IDL/内核）各自没有共同 oracle。

## 目标（每条一向量，独立派生自 spec，**不得**从任何实现生成期望值）

1. `cg5` 布局：`rc0`–`rc3` 写入 ⇒ `CFXREG`；`rc4`/`rc5` cause id/info；`rc8`–`rc11` 读写；`rc11` 复位全 1；`excp pending`（旧 `rc5`）访问 ⇒ 按新布局语义（`rc5` 是 cause info，写入/读取行为按表）。
2. `cg9` 布局：`rc0`–`rc4` 只读、`rc5` pending 只读、`rc14`/`rc15` 读写、`rc6`–`rc13` ⇒ `CFXREG`；`rc15` 低 2 位写忽略。
3. `cg0`–`cg3`：`rc14` switch、`rc15` vector 生效；`rc8`/`rc10` ⇒ `CFXREG`。
4. 进入自动填：同步 `trap` 后目标 cfx `cg5 rc0`–`rc5`/`rc8`–`rc11` 正确；异步进入后 `cg9 rc0`–`rc4` 与 hart `cg5 rc8`–`rc11` 正确、hart `cg5 rc0`–`rc3` 不变。
5. `escape` 判据：正常返回四元组（mode/cfx/ip/mask）；`imms18 != 0` ⇒ `ILLI`；`cfxha` ≠ 当前 cfx ⇒ `CFXESC`；目标模式升权 ⇒ `CFXESC`；目标 cfx 未实现/无 monitor ⇒ `CFXESC`；`escape_num` +1；`rc11` 整字覆盖（反例：增量写 ⇒ 向量红）。
6. 与 `m18-linux-024` 的窗口场景对应：新模型下“恢复→escape”不可被异步插入（向量/探针应证明 mask 在跳转前生效）。

## 验收（逐条贴真实 rc）

1. 向量在 `tests/inst/**`（或既有向量框架）落地，`check-inst-asm`、`check-idl`、`check-tests-index`、`check-case-ledger` rc=0；生成物重算。
2. 执行侧：QEMU（`m18-qemu-008` 合入后）逐条 PASS；RTL/gem5/IDL 未就绪的条目登记 `expected-divergences` 或 KNOWN-RED（不得静默跳过）。
3. **可达 FAIL ≥2 路**：故意把某期望值写错/把 `rc11` 当增量 ⇒ 向量红；`cp`+md5 还原回绿。
4. 不回归：`check-spec-codeblocks`/`-refs`/`check-contracts-*`（向量引用 spec 的锚点有效）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/inst/**`、`tests/unit/**`（向量侧）、`tests/case-ledger.tsv`、`tests/data/inst-signature/**`、`tests/arch/**`（含 `expected-divergences.yaml`、`vast-arch-inventory.md` 中向量相关项）、`tests/ee-vast/**`、`tests/ee-tiny/**`、`tests/shared/asm/**`（qemu-008 登记的载体/legacy 探针）、`tools/testcases/generate_lit_vectors.py`（修生成器旧语法）、`tools/testcases/arch/**`（legacy 探针，如需）、本任务书。
3. 不改实现（QEMU/RTL/gem5/IDL/LLVM/内核）、spec/契约/Makefile；不改版本号。
4. 期望值必须**独立派生自 spec**，不得从 QEMU/RTL 生成；`cp`+md5 还原；临时目录 `/tmp/opencode/m18-testcases-004/`。
5. **已知待修**：`tools/testcases/generate_lit_vectors.py` 仍产旧 `escape` 语法（`m18-llvm-002` reviewer 发现）；`tests/arch/hart/cfx15.S`、`tests/ee-vast/*`、`tests/shared/asm/perm_hv.inc`、legacy 探针（`044t/045t/046t/integ040/044/048/049/050/051/async_094t`）仍是旧槽位/旧语法（`m18-qemu-008` 已登记）——本任务统一迁移到新布局，不得留着等别人。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **38/38 PASS**（含 4 路注入红→`cp`+md5 还原→回绿）；`check-inst-asm` **274/274 镜像 PASS**；`check-tests-index`/`check-case-ledger`/`check-qemu-forms`/`check-spec-refs` rc=0；`check-idl` rc=2（KNOWN-RED，见遗留）；补修轮：`check-isa-coverage` rc=0、`run_arch --self-test` PASS、`arch-pmem-001/002` QEMU PASS（48/10 槽；首次进入为真正的 `trap cfx_hmon,0`，cause=CFXTRAP 自证）；`make check` 当前树 20 gate PASS 后仅环境红 `check-syscall-abi`，基线树同工具链在 `check-isa-coverage` 即红 ⇒ 本提交不新增红。
**修改文件**：`tests/inst/11-cfx/{escape_ciii_cfx,cfx2rc_crrr_cfx,cfx2rd_crrr_cfx}.S`；`tests/arch/hart/{cfx15.S,check_cfx15.py,expected.yaml,README.md}`；`tests/arch/umon/{m5_perm_mask_cfxperm,m5_trap_escape}.S`；`tests/arch/ptw/ptw_carrier_tlb.py`；`tests/arch/vast-arch-inventory.md`；`tests/ee-tiny/cfx_hmon_tiny.S`；`tests/ee-vast/{hmon,smon,power,hmon_k0,smon_k0,probe_kernel_k0}_vast.S`；`tests/shared/asm/perm_hypv.inc`；`tools/testcases/generate_lit_vectors.py`；`tools/testcases/arch/min_rom_probe_{044t,045t,046t,integ040t,integ044t,integ048t,integ049t}.py`；`tools/llvm/llvm-isa-backend-matrix.tsv`（生成器重算）；`tests/arch/hart/check_hart.py`；`tests/arch/pmem/{pmem_dma.S,pmem_oracle.py,check_pmem_dma.py,expected.yaml,README.md}`；`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；本任务书。
**验收结果**：向量数/覆盖——`tests/inst/11-cfx` 7 载体全绿（`escape_ciii` 28 链例 + 9 故障；`cfx2rc` 14+7；`cfx2rd` 22+7；`cfxreg_deny`/`cfxtrap_deny`/`fence`/`trap` 各 3–14）；`arch-hart-001`（hmon）**124 槽**、`arch-hart-002`（smon/umon）各 **38 槽** PASS。目标映射：① cg5 布局/RO/rc8–11/rc11 复位 → `escape_ciii` 1–16 + `cfx15` 同步入口 10 槽 + cfx2rc/rd；② cg9 新布局/保留槽/rc14/15 → `cfx15` 22–47；③ cg0–cg3 rc14/15 生效 → `cfx2rc`/`cfx2rd`（cg3 rc14/15 读写）；旧 `rc8`/`rc10` ⇒ CFXREG 由既有 `min_rom_probe_m18qemu008.py` 覆盖（本任务未新增该判据；`cfx15` 30–34 是 cg9 rc14、47–49 是 cg8 rc0 写 RO ⇒ CFXREG）；④ 同步/异步进入写入集合 → `cfx15` 同步入口 10 槽 + 异步捕获 9 槽；“hart cg5 rc0–3 不变”由既有 `min_rom_probe_m18qemu008.py` 覆盖；⑤ escape 五类判据/四元组/rc11 整字/escape_num → `escape_ciii` 全链 + `cfx15` `async_ret`（rc11=0x0123456789ABCDEF 整字）与 `esc_criteria`（升权/未实现目标/cfxha 不符）；⑥ mask 在跳转前生效 → `async_ret` 首指令读回 rc11 后仍只置 pending。
**新发现/坑**：⓪a `pmem_dma.S` 曾用 reserved `cg3 rc8` 写触发**非预期 CFXREG** 进入 h_trap_entry（`rc8` 在 R3 已 reserved）；已删该行并保留真正的 `trap cfx_hmon,0`，且在 `h_trap_entry` 自证 cause=CFXTRAP（恢复旧 rc8 ⇒ cause=CFXREG ⇒ BAD00002 判红，证据注入④）。⓪b L1 回归成因：改 `generate_lit_vectors.py` 的输出形态后未重生成跨模块真源 `tools/llvm/llvm-isa-backend-matrix.tsv` ⇒ `check-isa-coverage` 红（依赖链：生成器→矩阵产物）；`check_hart.py` 自检把槽数写死 89/40，未随 `cfx15.S`/`expected.yaml` 同步 ⇒ 改为按 `expected.yaml` 现场派生。① `check_inst_sig` 的静态展开器不求值标签/寄存器表达式 ⇒ 绝对地址断言改用“入口副本相等 + 落点执行”证明（仍可达 FAIL）；② R3 禁止升权 ⇒ hypv 被打断时 supv handler 不能 `escape` 回 hypv，`cfx15` H 模式显式返回 supv/hart（S/U 仍返回被中断现场）；③ 旧 R2 异步探针把“经 smon 回 hypv”当返回路径，R3 下不可构造；④ `cfx2rc` 对 cg5 rc10 忽略低 2 位，向量改用 4 字节对齐值；⑤ `m5_trap_escape` 的向量 stub 不能用绝对 label 重定位（`set.rd`），仍用 `rb2rd+add.si`。
**遗留问题**：① **KNOWN-RED** `check-idl` rc=2：`idl_exec` 连基线 `add.si_riii_rd` 都 `step limit ... no SYS_EXIT`（IDL 未跟 R3/新 BootROM，归 `m18-idl-003`），本任务未改 IDL；② **KNOWN-RED** `min_rom_probe_{async_094t,integ050t,integ051t}.py` 仍按 R2 槽位且按“smon 回 hypv”设计，R3 需重做场景（本轮未伪装通过）；③ `integ040t` 的 `tlb_bypass_ptw_off` 在共享 master QEMU 上同样 TIMEOUT ⇒ 基线红、与本次迁移无关；④ `check-arch` 的 **full** 级其余载体（`pmem/*`、`umon/mode_entry*`、`cache/*`、`time/*`、`common/env-*`）仍含旧 rc10/rc8 或 `escape …, [off]`，smoke 代表集已全绿、full 未逐条迁移；⑤ RTL/gem5 的 cg5/cg9 R3 迁移待各自任务（`cfx15` 同源已就绪）。

## 审阅记录

### 第 1 轮 engineer 自审
**范围**：逐行审查 `escape_ciii_cfx.S`（重写 37 点：cg5 入口/出口、正常返回、rc11 整字、CFXESC 三类、RO/ILLI 故障链）、`cfx15.S`+`check_cfx15.py`（124/38 槽、facts 改 R3、esc_criteria）、生成器与 7 个 legacy 探针、bootrom/perm/umono/ptw 载体。
**判决**：下表 finding 全部处置；无未修阻断项，状态对账「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_inst_sig` 无法求值标签/寄存器 exp | ✅已修 | 绝对地址断言改“rc2==rc10 副本 + 落点执行”；rc11 改 rc11==rc3 副本；escape_num 改 runtime `__VERIFY_EQ_RD` | `check_inst_sig --write` rc=0；274/274 PASS |
| F2 cfx15 H 模式 `escape` 升权被 CFXESC | ✅已修 | H 显式 rc8=supv/rc9=hart；S/U 保持返回被中断现场；README 记录 | `run_arch` 三模式 PASS |
| F3 cfx15 期望槽数/签名长度未同步 | ✅已修 | 89/40→124/38（`.S` sig_bytes、`SIG_SLOTS`、expected.yaml、README） | `run_arch` 124/38 槽 PASS |
| F4 cg5 rc10 低 2 位被忽略导致 cfx2rc 红 | ✅已修 | 测试值改 4 字节对齐；不把“忽略低位”写成规范断言 | 11-cfx 7/7 PASS |
| F5 `m5_perm_mask_cfxperm` 仍读 cg5 rc3/rc4 | ✅已修 | 改 rc2/rc5（R3 prev ip / cause info） | `run_arch` umon-002 PASS |
| F6 `m5_trap_escape` 旧语法 + 向量偏移 | ✅已修 | stub 5 条（rc2+4→rc10→escape），`rb2rd+add -16` 定位；rc10→rc15 | `run_arch` umon-010 PASS |
| F7 legacy 探针共享常量/escape 语法 | ✅已修 | 044/045/046/040/044/048/049：rc8/10→14/15、cg5 rc2/3/4→4/2/5、`escape(ha,n)`→`ret_seq`；R3 下 trap 不再屏蔽 mask、CFXPERM info=指令地址 | 7 个探针 rc=0（integ040t 仅基线红 1 例） |
| F8 `check-idl` 红 | ⏸延后 | 不改 IDL；以基线 `add.si` 同样 `step limit` 归因 `m18-idl-003` | `run.sh` 断言 `idl_exec step limit` |
| F9 full 级 arch 载体未全部迁移 | ⏸延后 | 仅记录 KNOWN-RED（smoke 代表集已全绿）；不在本任务 6 门控内 | `run_arch --level smoke` 10/10 PASS |

残留：见完成区遗留 ①–⑤；自审确认注入均 `cp`+md5 往返、`git diff` 非空（run.sh 断言）。状态 → 待验收。

### 第 2 轮 engineer 自审
**范围**：`tools/llvm/llvm-isa-backend-matrix.tsv`（重生成）、`tests/arch/hart/check_hart.py`（want 派生）、`tests/arch/pmem/{pmem_dma.S,pmem_oracle.py,check_pmem_dma.py,expected.yaml,README.md}`（R3 迁移）、证据脚本增 3 项检查+第 3 路注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 `check-isa-coverage` 红（生成器/矩阵产物脱节） | ✅已修 | `gen_isa_coverage.py` 重算 tsv（md 无变化） | `make -s check-isa-coverage` rc=0；263 记录 accept 263 |
| G2 `check_hart` 自检写死 89/40 | ✅已修 | 改为读 `expected.yaml` 的 `_registered_slots`，docstring 124/38 | `run_arch --self-test` PASS；注入 89/40 ⇒ selfcheck rc=1，还原 md5 `6aca204b…` ⇒ rc=0 |
| G3 `pmem_dma.S` 旧 escape 语法 | ✅已修 | 4 处改 `escape cfxHA`+`cg5 rc10`；cg9/cg5/cg0–3 新槽位；R2 的 `imms18=2` 路径改正常异步返回（rc10=after_escape、rc11 整字） | `check_pmem_dma --selfcheck` PASS；`arch-pmem-001` 48 槽、`002` 10 槽三模式 QEMU PASS |
| G4 相邻产物未同步（pmem expected/oracle/README/SLOTS） | ✅已修 | 槽数 55→48、S/U 槽序按 rc4 frame/rc5 pending | 同上 + `run_arch --level smoke` 10/10 |
| G5 `make check` 新红 | ✅已修 | 仅重生成产物与测试侧；未改实现/Makefile | 当前树 20 gate PASS 后停在环境红 `check-syscall-abi`（缺 linux 源树）；基线树同工具链在 `check-isa-coverage` 即红 ⇒ 本提交不新增红、反修掉 1 条 |

残留：`check-idl` KNOWN-RED 不变（L2，单独 `make check-idl` 复现 idl_exec step-limit）；状态保持「待验收」。

### 第 3 轮 engineer 自审
**范围**：F1 入口路径（`pmem_dma.S` 删 reserved rc8 + `h_trap_entry` cause 自证）、F5 卫生（oracle 孤儿/`REC` 注释重排）、F4 R2 措辞（`cfx15.S`/`check_cfx15.py`/pmem expected/README）、F2 补迁 `smon_vast.S`、F3 完成区映射订正；证据脚本加第 4 路注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 靠 CFXREG 副作用进入 | ✅已修 | 删 `cg3 rc8` 写；`trap cfx_hmon,0` 真进入；`h_trap_entry` 断言 cause=CFXTRAP | `arch-pmem-001` PASS；注入④恢复 rc8 ⇒ rc=1（BAD00002），还原 md5 `54449d04…` ⇒ rc=0 |
| F2 完成区列了未改的 smon_vast | ✅已修（改成真迁移） | `smon_vast.S` cause id/info rc2/rc4→rc4/rc5；`probe_kernel_k0_vast.S` 注释改 `escape cfx_smon` | `build-bootrom` PASS；smoke 10/10 |
| F3 映射③④归错载体 | ✅已修 | 完成区改指 `min_rom_probe_m18qemu008.py`（旧 rc8/10、hart cg5 rc0–3 不变）；`cfx15` 30–34=cg9 rc14、47–49=cg8 rc0 RO | 文档核对 |
| F4 R2 陈旧措辞 | ✅已修 | `cfx15.S`/`check_cfx15.py` 头部与 docstring、`pmem/expected.yaml`、`pmem/README` 改 R3（非 0 ⇒ ILLI；异步返回合法） | `grep` 现行散文 0 处 `imms18=2 ⇒ CFXESC` |
| F5 孤儿/编号 | ✅已修 | 删 `cfxesc`、`f["escape_imm2"]`；`pmem_dma.S` REC 注释 27–47 顺序重排 | `py_compile` 0；selfcheck PASS |

残留：`check-idl` KNOWN-RED 与 full 级 RTL/gem5/其余载体不变；状态保持「待验收」。

### 第 1 轮 reviewer 验收

**重跑（仓库根，本人执行）**：运行期证据目录内 `run.sh` → `checks: PASS=35 FAIL=0`、`evidence: PASS`、`rc=0`（含其 3 路注入红→`cp`+md5→回绿，`check_hart` 还原 md5 `6aca204b…`）；`run_arch --self-test` rc=0；`run_arch --level smoke --platforms qemu` → `PASS（10 case × 1 平台）` rc=0（不带 `--platforms` 因缺 chipyard 仿真器 rc=2，环境）；`check_pmem_dma --selfcheck` → `48/10/10 槽（现场派生）` rc=0；`make check-isa-coverage` → `accept 263` rc=0；`check-inst-asm` 274/274、`check-tests-index`/`check-case-ledger`/`check-qemu-forms`/`check-spec-refs` 均 rc=0（均在本人重跑的 `run.sh` 内）；`make check` rc=2，首个失败 = `check-syscall-abi`（缺 linux 源树 FileNotFoundError），其前 46 处 PASS；`make check-idl` rc=2（内层 FAIL，264/274 例红，含本任务未改的 `add.si_riii_rd`）。
**基线对比**：派单基线树 `gen_isa_coverage --check` rc=1（真源重派生 `escape_ciii_cfx` accept→reject、矩阵漂移），当前树 rc=0 ⇒ 本提交不新增红、反修 1 条；`check-idl` 归因成立（两提交 `idl/**` 改动数 0、`idl/` 最后改动是基线祖先、基线 `add.si_riii_rd` 与本任务向量同为 `step limit … no SYS_EXIT`）。
**独立 oracle**：`pmem_oracle.py` 55→48 = 删 8 条旧 `imms18=2 ⇒ CFXESC`（与 `DADAO-12 §5.1/§5.3`「`imms18≠0 ⇒ ILLI`」冲突，删除正确）+ 增 1 条 `rc11 整字`（§5.3 步 3 / ADR-0061 R3-D5：`rc8=supv ⇒ smon cg8 rc1`，`rc10` 首指令读回 = 探针 `P1`，QEMU 实测 `0x0123456789abcdef`）；本人手数 hypv 期望恰 48 槽，与 `expected.yaml` 48、`SLOTS=48` 一致（S/U 10 槽）。期望由 spec 解析 + 探针常量 + ELF 符号派生，无 QEMU 反推。
**覆盖**：`tests/inst/11-cfx` 7 载体；`arch-hart-001/002` signature 长度现场解析 = 124/38；escape 五类判据（正常四元组 / `imms18≠0`⇒ILLI / cfxha 不符 / 升权 / 目标未实现）+ `rc11` 整字 + `escape_num` +1 + `excp_async_num` 1/2/3 均有向量。
**迁移 grep**：范围内 19 个文件旧 `escape …, [offset]` = 0（`ptw_carrier_tlb.py` 仅 docstring 1 处陈旧措辞）；生成器输出 `escape cfx63` 新语法，重跑两次 md5 一致且树净。
**注入（新角度）**：`pmem_oracle` rc11 槽期望 `P1 → P1^0xFF` ⇒ `arch-pmem-001` rc=1（`slot 26 … expected 0x0123456789abcd10 actual 0x0123456789abcdef`）；`cp`+md5 `4235f350…` 还原 ⇒ rc=0。
**约束**：两提交 29+8（任务书两处重叠 ⇒ 实际 36 文件），全在 `tests/**`、`tools/**`、本任务书；无 `components/ spec/ .tao/contracts/ Makefile idl/`、无内核改动；`git branch -r --contains` 两提交均空（未 push）；状态 `待验收`；`check-knowledge-refs` rc=0。**快照对账**：验收前后 `git status --porcelain -uall` 均空行、36 文件 md5 与验收前逐行相等。

**判决：Needs Revision**

- **F1（阻断·代码行为）** `tests/arch/pmem/pmem_dma.S:279` 仍写旧槽 `WCFX_IMM cfx_hmon, cg3, rc8, 3`（`DADAO-12 §3.4`：原 `rc8` 归 reserved ⇒ `CFXREG`）。本人三步实测：① 只把其后 `trap cfx_hmon, 0` 改成 `trap cfx_smon, 0` ⇒ 仍 PASS（该 trap 从未执行）；② 删掉该行、保留改后的 trap ⇒ FAIL rc=1；③ 只删该行、trap 还原 `cfx_hmon` ⇒ PASS rc=0。⇒ 载体靠**非预期 CFXREG** 跳 `h_trap_entry` 完成进入，注释「首次 trap 入口 = h_trap_entry（CFXTRAP）」与完成区「cg0–3 新槽位」不实。修法：删该行（或改 `rc14`），改后重跑 `arch-pmem-001` 与证据 `run.sh`。
- F2（文档）完成区「修改文件」列 `tests/ee-vast/smon_vast.S`，两提交均未改（实际 36 文件）。
- F3（文档）完成区映射③④把「cg0–cg3 旧 rc8/rc10 ⇒ CFXREG」「hart cg5 rc0–rc3 不变」归到 `cfx15 20–24/37–39`+`cfx2rc/rd`，实际由 `min_rom_probe_m18qemu008.py` 承接（`cfx15` 20–24 = cg9 rc14、37–39 = cg8 rc0 写 RO）。
- F4（文档）R2 陈旧措辞未清：`cfx15.S` 头部与 `check_cfx15.py` docstring 的「帧选择位 `imms18[1]` ⇒ CFXESC」、`pmem/expected.yaml` note「escape imms18=2 ⇒ CFXESC」、`pmem/README`「捕获/CFXESC」（R3：非 0 ⇒ ILLI）。
- F5（卫生）`pmem_oracle.py` 孤儿 `cfxesc`、`f["escape_imm2"]` 已无引用；`pmem_dma.S` 删块后 REC 注释编号（27–33、34 起）未重排。

### 第 2 轮 reviewer 验收
**重跑（仓库根，本人执行）**：运行期证据目录内 `run.sh` → `checks: PASS=38 FAIL=0`、`evidence: PASS`、rc=0（内含其 4 路注入红→`cp`+md5→回绿，pmem 还原 md5 `54449d04…`）；`check_pmem_dma --selfcheck` → 48/10/10 槽（现场派生）rc=0；`run_arch --self-test` rc=0；`arch-pmem-001` 48 槽 rc=0、`arch-pmem-002` smon/umon 各 10 槽 rc=0；`run_arch --level smoke --platforms qemu` → `PASS（10 case × 1 平台）` rc=0；`make -s build-bootrom` rc=0；`check-inst-asm` 274/274、`check-tests-index`/`check-case-ledger`/`check-qemu-forms`/`check-spec-refs`/`check-isa-coverage` rc=0（均在本人重跑的 `run.sh` 内）；`make check` rc=2，首个失败 = `check-syscall-abi`（缺 linux 源树 FileNotFoundError），其前 246 处 PASS、`check-knowledge-refs` PASS（0 悬空）。IDL 侧本人重跑 `idl_four_way --only add.si_riii_rd` 与 `--only escape_ciii_cfx` 均 rc=1 且日志含 `step limit`（归 `m18-idl-003`）。
**基线 diff**：派单基线提交（主仓 `aee3f24c`，与派单基线仅差台账一行）`make check` rc=2、仅 14 PASS，首个失败 = `check-patch-tree`（8 problem，qemu/musl 源树漂移；该树有组件源树故断言⑥⑨生效、任务树无源树故跳过）⇒ 基线红更早；两树环境不对称已注明，本任务只动 `tests/**`+`tools/{testcases,llvm}/**`+任务书，其可影响的门控在当前树全绿 ⇒ 不新增红。
**F1 闭环**：`pmem_dma.S` 已无 `WCFX_IMM cfx_hmon, cg3, rc8`（grep rc=1），进入 = `WCFX_LABEL cg3 rc15` → `trap cfx_hmon, 0`；`h_trap_entry` 读 `cg5 rc4` 与 `1<<0`（CFXTRAP，`contract-see` §6.1 / `DADAO-12`）比对，不等则 `REC 0xBAD00002 → fail_exit`。本人注入①恢复旧行 ⇒ rc=1、`slot 00 … actual 0x00000000bad00002`；`cp`+md5 `54449d04…` 还原 ⇒ rc=0。
**自设注入（新角度）**：② 把自证期望 `0x1` 改 `0x4` ⇒ rc=1、`slot 00 actual 0x00000000bad00002`（自证失败分支可达 FAIL）→ 还原回绿 rc=0；③ 删自证块 + 恢复旧行 ⇒ **rc=0 被旧行再次骗过**（日志 0 处 `BAD00002`）⇒ 证明自证是唯一防线 → `cp`+md5 还原、树净、rc=0。
**F2**：`smon_vast.S` cause id/info 已迁 `cg5 rc4/rc5`（diff 4 行）；`build-bootrom` rc=0（step5 bootrom 由其汇编）；`arch-pmem-002` smon/umon 各 10 槽 PASS（驱动用 step5 bootrom ⇒ 该迁移被实跑）。
**F3**：完成区映射③④载体已改指 `min_rom_probe_m18qemu008.py`（实测含 `cg0–cg3 rc8/rc10 ⇒ CFXREG`、`cg5 rc0–rc3 不变`）✓；但同句 `cfx15 20–24/37–39` 与实际槽序不符——现场 `check_cfx15 --expected`（124 条）：`30–34 = cg9 rc14`、`47–49 = CFXREG write cg8 rc0 RO`，`cfx15.S` 注释同样偏 +10 ⇒ 记 finding（判据本体成立，仅编号）。
**F4**：`cfx15.S`/`check_cfx15.py`/`pmem/{expected.yaml,README.md,pmem_oracle.py,pmem_dma.S}` grep `imms18[1]`、`imms18=2`、`不是异步返回` = 0（现存 `imms18` 措辞全为 R3「SBZ 非 0 ⇒ ILLI」）。
**F5**：`pmem_oracle.py` 无 `cfxesc`/`escape_imm2`（grep rc=1；AST 余留孤儿 `base_slot` 等与基线逐项相同、非本轮引入）；`pmem_dma.S` REC 注释 0–47 与 oracle 期望逐槽对齐（10/11、13/14 = `h_fault` 内联 cause/info，`arch-pmem-001` 日志 slot10/11/12 = ILLI cause/info/witness 佐证）。
**范围**：`git diff 3c489801..ede9371b --name-only` 恰 9 文件（任务书 + `cfx15.S`、`check_cfx15.py`、`pmem/{README.md,expected.yaml,pmem_dma.S,pmem_oracle.py}`、`ee-vast/{probe_kernel_k0,smon}_vast.S`；`check_pmem_dma.py` 未改属正常）；全程 `e458d9df..ede9371b` 39 文件全在 `tests/ tools/ .tao/`，无实现/spec/契约/Makefile/idl/内核；`git branch -r --contains ede9371b` 空（未 push）；状态 `待验收`；验收前后 `git status` 均空、9 文件 md5 逐行相等。

**判决：Accepted**（finding 一条，交 architect 收尾改：完成区与 `cfx15.S` 的 `cfx15` 槽号 `20–24/37–39` 实为 `30–34/47–49`，偏 +10；非门控读取值，不阻断）
