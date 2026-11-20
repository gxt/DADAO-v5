# m16-testcases-002: 签名机制抽取（`tests/inst` 现有实现 → 共享层）+ `tests/arch` 接线

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（与 `m16-chipyard-008` 并行；本任务只改 `tests/` 与 `tools/testcases/`）
**可并行分片**：否
**预估**：6–8 h
**档位**：中改
**状态**：待验收

## 背景与判据（用户 2026-11-20 两次裁定）

> 「确实值得借鉴，tests-inst 和 tests-arch 都可以采用这个能力。」
> 「tests-inst 和 tests-arch 的底层机制我希望能尽量复用。」

**关键事实：机制已经在仓里，本任务不是"新造"，是"抽出 + 复用"。**

- `tests/inst/macros/inst_test.inc:181-186` 的 `__REC reg` 就是签名的写入口：`st.o \reg, [rb30, 0]` + `add.si rb30, 8` + 计数 `__NCHECK`；`rb30` 是结果缓冲写指针（同文件 `:54` 的保留寄存器约定）。
- 收尾 `:585` 用 `__PRINT TEST_BUF, (8 * __NCHECK)` 把整块打出（`__PRINT` 见 `:192-203`，逐字节 `SYS_WRITEC`）。
- host 侧取流与比对已在 `tests/ee-tiny/run_inst_tiny.py`：三平台各返回 `(rc, stdout_bytes, log_path)`（`:246`）、chipyard 走 `+semiout=`（`:273`）、逐平台字节数 `:332`、**字节数断言 `8×检查点数`** `:346-351`。
- 平台通道均已存在，不需要新造：chipyard `+semiout` 收 `SYS_WRITEC`/`SYS_WRITE0`/`SYS_WRITE(handle 1)` 的每个字节（`tools/testcases/lib/chipyard_engine.py:14-25`）；gem5 用 `--console-out`（`tools/gem5/compare_chipyard.py:532`）；QEMU 的 semihosting console 走 stdout 管道（`tools/testcases/lib/run_qemu_test.py:400-440`）。
- `tests/arch` 现在**只有退出码**：`tests/arch/ptw/expected.yaml` 抬头写明「guest 内自检 + `SYS_EXIT` 退出码 = 0x00 通过 / 0x01–0x7F 第 N 条断言失败」，**没有实际值**。

参考形态（`riscv-arch-test`，只借形态不借判定方式）：签名区 = `.data` 里的固定数组、预填 `0xdeadbeef`（漏跑可见）、每观测点写 8 字节并前进、末尾整块 dump、host 侧逐字节比。**该框架是"单实现合规"（gold 来自 Spike/SAIL），没有多平台差分能力**——我们的判定仍是"三方/四方互比"。

## 目标

1. **共享汇编层** `tests/shared/asm/signature.inc`（`tests/shared/README.md` 的判据：被 ≥2 个 scope 复用 ⇒ 放这里）：
   - `SIG_BEGIN count`：`.data` 里 `.p2align 4` 的 `begin_signature` + `.fill count,8,0xdeadbeef`；
   - `SIGUPD reg`：`st.o \reg, [rb30, 0]` + `add.si rb30, 8` + 计数（**与 `__REC` 同形、同寄存器约定**，`rb30` = 写指针）；
   - `SIG_DUMP`：一次 `SYS_WRITE`（`handle 1`，参数块 `{1, TEST_BUF, 8*ncheck}`）块写整段；保留 `SYS_WRITEC` 逐字节路径作为回退（不改已有镜像行为时用）。
2. **`tests/inst` 改为复用，不留第二份**：`inst_test.inc` 的 `__REC` 委托给 `SIGUPD`，收尾打印改调 `SIG_DUMP`（或保持 `__PRINT` 但由 `SIG_DUMP` 实现）——**行为必须不变**（见验收 1）。
3. **host 层** `tools/testcases/lib/signature.py`：从 `run_inst_tiny.py` 抽出
   - `parse(blob, count)`：按 8 字节切、长度断言、把 `0xdeadbeef` 槽标为"未写"；
   - `compare(got, want)`：返回首个不一致槽号 + 两侧值（16 进制），供任何 scope 直接报"槽 N 期望 X 实际 Y"；
   - `capture(platform, ...)`：三平台取流适配（qemu stdout / gem5 `--console-out` / chipyard `+semiout`）；
   - `run_inst_tiny.py` 与 `tests/arch` 都调用它，**不得留第二份解析/取流实现**。
4. **`tests/arch` 接线**：`ptw` 至少 3 条 case 的观测点（A/D 回写后的 PTE 值、`cause_info`、命中/填充计数）改用 `SIGUPD` 输出实际值，host 侧用同一 `signature.py` 判定。
5. **登记**：`tests/shared/README.md` 加一行（内容/谁用）；`tests/arch/README.md` 的「观测通道」段改为「签名流 = 唯一判据载体，退出码只作镜像级兜底」。

## 不在本任务范围

- **全量改 `tests/inst` 的期望值/载体**（那属 M17 的符合作业，且会改变指令流 → 影响已标定的周期基线）；
- 改 RTL / gem5 / QEMU 源码，改 `spec/` 与 `.tao/contracts/`；
- Vast 侧三方差分（归 `m16-chipyard-011`）。

## 验收（逐条贴真实 rc）

1. **抽取不改行为**：`make check-inst-asm` **272/272**；且抽取前后**每个镜像的签名流逐字节相同**（基线与改后各 dump 一份、逐镜像 md5 比，**非抽样**）。
2. **三平台取流一致**：同一镜像在 qemu、gem5（SE）、chipyard（**Tiny**，用现成 simulator）各取一份签名流，**逐字节相等**（≥1 条 case）。若 chipyard 侧正在被其它任务构建/占用 ⇒ 记 BLOCKED 并给替代证据（不得并发构建）。
3. **漏跑可见**：故意删一条 `SIGUPD` ⇒ 对应槽为 `0xdeadbeef`，`signature.py` 报「槽 N 未写」（不是静默当 0）。
4. **可达 FAIL ≥3 路**：① 改一个期望值 ⇒ 比对 rc=1 且报槽号 + 两侧值；② `SIG_DUMP` 长度写成 `count*4` ⇒ 长度断言红；③ 某平台流缺失 ⇒ BLOCKED 而不是 PASS。
5. **复用核验**：机制实现只有一份——`signature.inc`、`signature.py` 各 1 个文件，且 `tests/inst`、`tests/arch` 内无复制（`grep` 计数**现场派生**，不写死）。
6. **门控**：`check-inst-asm`、`check-arch`、`check-tests-index`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs` 真实 rc；`make check-inst-macro-scope` 仍绿（`SIGUPD` 加入宏体后不得触发扫描告警）。

## 约束

- 独立 `git worktree`（分支名 = 任务号）；**禁改主工作树**；临时文件在 `/tmp/opencode/<任务ID>/`。
- **不提交 git**；术语「寄存器组」；完成区不写具体 `.work/**` 路径（写「运行期证据目录内的 `run.sh`」）。
- **不得 `make install-host` / 不得重建 QEMU/gem5/chipyard**：用现成安装根与 simulator；确需重建须先说明理由并在完成区登记。
- 失败保留现场并继续推进（自行处置：派修/绕行/有据重试并记录次数/登记后跳过），只在需用户语义裁定时留问。

## 完成区

**测试结果**：通过 17/17（运行期证据目录内的 `run.sh`，rc=0）。要点：`check-inst-asm` 272/272
且 272 个镜像签名流 md5 与抽取前基线全同（差异 0/缺 0）；同一镜像 qemu/gem5/chipyard
签名流 224 B 逐字节相等；`SIG_DUMP` 冒烟镜像三平台 24 B 相等；`arch-ptw` 29/29；删一条
`SIGUPD` ⇒ `槽 2 未写` + 相邻槽错位报值；改期望 ⇒ rc=1 报「槽 1 期望 0x… 实际 0x…」；
`SIG_DUMP` 长度写 `count*4` ⇒「签名字节数 12 ≠ 24」；流缺失 ⇒ 解析 fail-closed、平台缺失
setup rc=2；`signature.inc`/`signature.py` 各 1、`tests/inst`/`tests/arch` 内复制 0。
**修改文件**：新增 `tests/shared/asm/signature.inc`、`tools/testcases/lib/signature.py`；
改 `tests/inst/macros/inst_test.inc`、`tests/ee-tiny/run_inst_tiny.py`、
`tools/testcases/arch/{min_rom_probe_tlb,node_probe_prelude}.py`、`tests/arch/ptw/expected.yaml`、
`tests/shared/README.md`、`tests/arch/README.md`、`tools/testcases/lib/README.md`。
**验收结果**：①`make check-inst-asm` rc=0（272/272），指令流不变（`.text` 同 md5，仅符号表因
局部标号改名而不同）；②三平台逐字节相等（inst 镜像 + `SIG_DUMP` 块写冒烟）；③④见上（可达
FAIL 三路均真实红后还原回绿，`cp`+md5 对账）；⑤复用核验现场派生；⑥门控真实 rc：
`check-tests-index`/`check-case-ledger`/`check-index-blobs`/`check-knowledge-refs`/
`check-inst-macro-scope`/`check-dirs`/`check-no-residue` 全 0；`make check-arch` rc=2（044t/
045t/integ046t 失败，**master 同款**：逐条在 master 复跑 rc=1；arch-smoke PASS、tlb 29/29 rc=0）。
**新发现/坑**：① QEMU/gem5 的 `SYS_WRITE` handle 1 必须先 `SYS_OPEN(":tt")` 才有效，未打开
返回「整段未写」⇒ 块写失败回退 `SYS_WRITEC`（任务给的 handle 1 块写保留为首选路径，chipyard
直接可用）；② word-builder 的 `add.si` 有 rd/rb 两个 opcode（0x59/0x5B），写指针必须用 rb 形，
用错会把 `rd16`（服务号）当指针增量 ⇒ 输出重复首字节后挂死；③ inst 合法结果本身可能等于
`0x00000000deadbeef`（`rol.t_orri_rd` 槽 13、`rol.t_orrr_rd` 槽 15）⇒ inst 侧
`parse(sentinel=False)`，预填签名的 scope 才把该值当「未写」；④ `tests/arch` 的 ptw 载体是
Python word-builder（无 `.s`），故签名发射器落在 `signature.py` 的 `Emitter`（与 `signature.inc`
同语义、同槽宽/哨兵），未新增第二份解析/取流实现；⑤ `check-arch` 的 3 个环境失败不是本任务
引入（master 逐条复现）。
**遗留问题**：无。未手工执行 `install-host`、未重建 QEMU/gem5/chipyard（`check-arch` 目标的前置
声明会进入 install 链，实测各构建步「no work to do」、安装根二进制 md5 前后一致）。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（无嵌套子代理）：签名 `SIG_DUMP` 块写/回退分支顺序、`SIG_BEGIN` 预填边界、
Emitter 分支编码（含部分写不重复写）、arch 三 case 观测点映射与 PTBR 恢复顺序、inst 侧
长度/未写哨兵的语义分离。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 word-builder 用 `add_si` 增量写指针（rd 形），把服务号 rd16 改坏 ⇒ 重复首字节后挂死 | ✅已修 | `node_probe_prelude.add_si_rb`（0x5B）+ `Emitter` 改用；回退字节循环同样用 rb 形 | 冒烟镜像三平台 24 B 相同；`arch-ptw` 29/29 |
| F2 `parse` 把 `0xdeadbeef` 一律当未写，误伤 inst 合法值 `0x00000000deadbeef` | ✅已修 | `signature.parse(..., sentinel=False)` 供 inst；预填 scope 保持默认 True | 272/272 通过且 md5 全同 |
| F3 部分写的回退会重复输出 | ✅已修 | `SIG_DUMP`：`rd8==0` 完成、`==长度`/`<0` 回退、`0<rd8<长度` 不重复写（交 host 长度断言） | 三平台签名流逐字节相等 |
| F4 arch 签名 dump 在 PTBR=ROM 时写不进 RAM | ✅已修 | `_restore_identity` 抽出，`_finish` 先恢复恒等映射再 dump；007b 观测点放在恢复之后 | `arch-ptw-007/flush_adwbfail` PASS |
| F5 注入还原可能污染工作树 | ✅已修 | 证据脚本 `cp` 备份 + md5 对账，禁 git 还原；每次注入后复跑回绿 | 证据 17/17（`可达 FAIL①/② 还原后回绿`） |

### 第 1 轮 reviewer 验收（全部本人实跑，退出码如标）

1. `make check-inst-asm` → **rc=0**，`272/272 镜像通过`（日志 272 PASS / 0 FAIL，12 s）。
2. **基线溯源**：抽取前全量 dump 的 md5 清单 272 条，我按清单重算其 dump 结果 → 272/272 相符；该次运行日志**完成时刻早于** `signature.inc`/`inst_test.inc` 的 mtime ⇒ 基线确在抽取前取（非 `HEAD~` 猜测）。
3. **抽取后全量复比（非抽样）**：现场 272 份 `.qemu.out` md5 对清单 → **相同 272 / 差异 0 / 缺 0**；另用 `llvm-objcopy --dump-section .text` 比抽取前后 272 个 ELF → **`.text` 相同 272 / 不同 0**（指令流不变，强于输出比对）。
4. **三平台逐字节**：`run_inst_tiny --id ld.o_rrii_ra --platforms qemu,gem5,chipyard` → rc=0、`1/1 镜像通过`，三侧各 **224 B**、md5 同为 `7e5529cea8821543d0956011fefd59c4`；`SIG_DUMP` 冒烟三平台 rc=0、各 **24 B**、md5 同 `1f806aedbedbee7f72a07b3b65ecc693`、解析值匹配（用现成 simulator，未重建）。
5. **漏跑可见**（我独立注入，删**第 1 条** `SIGUPD`，临时树）：`slots=[0x99aabbccddeeff00, 0x0f1e2d3c4b5a6978, None]`，报「**槽 2 未写**（期望 0x0f1e2d3c4b5a6978）」+ 相邻槽错位报值。
6. **可达 FAIL（2 路实红 + 1 路 BLOCKED，均 `cp`+md5 还原并断言 md5 相等、还原后回绿）**：① 改期望值 → `rc=1`，`槽 1 期望 0x800000006000ffe1 实际 0x800000006000ffed`；还原 → `rc=0 / 1/1 checks passed`。② `SIG_DUMP` 长度写 `count*4` → `签名字节数 12 ≠ 24（3 槽 × 8 字节）`；还原 → 24 B 解析匹配。③ 平台流缺失 → 解析 `签名字节数 0 ≠ 224` fail-closed + runner `rc=2`（`ERROR: gem5 不存在`）。
7. **回退可达且字节一致**：我构造「只保留 `SYS_WRITE` 块写、删回退」的临时变体 → QEMU 下流通道 **0 B** ⇒ 块写在 QEMU 到不了输出通道，正常镜像那 24 B 只能来自 `SYS_WRITEC` 回退；该回退输出与 chipyard 侧 md5 相同 ⇒ 回退不改字节序/长度。guest 侧全仓无 `SYS_OPEN(":tt")` 调用。
8. **复用只有一份**：`signature.inc`/`signature.py` 各 1；`tests/inst`、`tests/arch` 内 `st.o`+`[rb30` **0** 处、`def parse(`/`def capture(` **0** 处；`run_inst_tiny.py` 无 `run_qemu/run_gem5/run_chipyard/_run`、无 `int.from_bytes`/`deadbeef`/`semiout` 残留（仅 `signature.capture` 调用）。
9. **门控真实 rc**：`check-tests-index`/`check-case-ledger`/`check-index-blobs`/`check-inst-macro-scope`/`check-knowledge-refs`/`check-dirs`/`check-no-residue` 全 **0**；`git show --name-only HEAD` = **11** 文件，与完成区「修改文件」逐项一致。
10. **`check-arch` 红项归属**：15 个 CFX probe 直跑（不经过 install 链）→ 本树 `044t rc=1`（`cfxreg_badcombo`、`trap_vector_roundtrip` 两处 `RESULT: FAIL`）、`045t rc=1`、`integ046t rc=124`（超时）、其余 12 个 rc=0（`tlb 29/29`）；**主工作树 master 逐条对照：044t/045t 同 rc=1 且 FAIL 文本逐字相同**，integ046t 我两侧均超时、工程师侧 master 记录为 `6/16 passed`（红）⇒ **属预存在红，非本任务引入**。
**约束核验**：任务树 `git status -uall` 干净、`git diff --stat` 空（注入全在临时树，`cp`+md5 还原）；未 `make install-host`、未重建 QEMU/gem5/chipyard（`check-arch` 目标前置含 `install-host`，故未整跑该 make 目标，改为其 probe 体直跑；三平台用现成 simulator）；未提交 git；本记录无运行期路径。
**判决**：**Accepted**（唯一保留项：`check-arch` 的 make 级 rc=2 未由我直接复跑，理由如上；其失败项已逐条在 master 对照为预存在红）。
