# m15-testcases-021: 测试资产伪指令收口（`LOAD_ADDR`→`set.rb`、`LD64`→`set.rd`）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m16-testcases-002`（签名机制）、`m15-testcases-006`（载体装载改用规范伪指令）
**可并行分片**：否（改 `tests/` 共享头与 100 个载体）
**预估**：6–8 h
**档位**：大改（机械替换面大，语义必须零变化）
**状态**：待验收

## 背景（用户 2026-11-20 指出）

测试资产里还留着两个**手写伪指令替代物**，规范伪指令早就能覆盖它们：

1. `tests/shared/asm/machine.inc` 的**唯一内容**是 `LOAD_ADDR rb, addr`——`set.zw` + 3×`or.w` 的固定 4 条，等价于规范伪指令 **`set.rb rb, imm64`**（常量为最少指令数；符号/可重定位地址为固定 3 片 + `R_DADAO_ABS48`）。
2. `tests/ee-tiny/common_tiny.inc` 的**唯一内容**是 `LD64 rd, w0..w3`——等价于 **`set.rd rd, imm64`**（实测：同值、同指令数，仅编码顺序不同）。

持有量（实测）：`LOAD_ADDR` **100 个文件 / 533 处**；`LD64` 2 个文件（`tests/ee-tiny/power_tiny.S` 4 处、`tools/chipyard/excp/app.S`）。

## 目标

1. **`LOAD_ADDR` → `set.rb`**：533 处逐一替换（操作数是 `.equ` 常量表达式的走常量路径；若有裸标签/跨段符号，走 `R_DADAO_ABS48`——先用 `ld.lld` 实测通过再继续）；
2. **`LD64` → `set.rd`**：`power_tiny.S` 4 处、`excp/app.S`；
3. **删除两个文件**：`tests/shared/asm/machine.inc`、`tests/ee-tiny/common_tiny.inc`，并清掉 `.include`（含 `machine-{tiny,vast}.inc` 里对 `machine.inc` 的引用与 `tests/README.md` 的登记）；
4. **重生成**：`tests/data/inst-signature/inputs.sha256`（输入 `.S` 变了）、`case-ledger` 若需要；Tiny bootrom 重建。

## 验收（逐条贴真实 rc）

1. **零残留**：全仓 `grep -rn "LOAD_ADDR\|LD64"`（排 `.tao/archive`）**0 命中**；两个文件已删、`git ls-files` 无它们；
2. **语义零变化**：`check-inst-asm` **272/272**、`check-arch`、`check-inst-sig` 全绿；**签名槽与期望值不变**（代码字节可变，执行结果不可变）；
3. **Tiny bootrom**：`make build-bootrom` 成功；bootrom 的字节会变 ⇒ 更新其 md5 基线并**在完成区写明新旧值**；
4. **符号路径**：若存在 `LOAD_ADDR <label>` 形式，必须证明 `set.rb` + `R_DADAO_ABS48` 在 `ld.lld` 下解析正确（贴链接后反汇编/符号值）；不存在则说明「全部为常量表达式」并给统计；
5. **可达 FAIL ≥2 路**（`cp`+md5）：① 把一处 `set.rb` 的常量改错 ⇒ 对应用例红；② 删 `machine-*.inc` 一条 `.equ` ⇒ 构建或 `check-tests-index` 红；
6. 门控：`check-tests-index`（含 `ASM HEADER DRIFT`）、`check-inst-macro-scope`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs`、`check-dirs`。

## 完成区必须写

**需重测周期的镜像清单**：所有指令流变化的镜像（`LOAD_ADDR` 4 条 → `set.rb` 1–4 条）；按指令类的周期表不受影响，但「实测总拍数」记录作废。

## 约束

独立 `git worktree`；不提交 git；**只做等价替换**，不顺带改语义/期望值；不改 `spec/` 与契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：`check-inst-asm` **272/272**（链例+故障链 632 例，rc=0）；`check-inst-sig` **272/272 镜像 / 4528 槽**（静态 4490 逐槽一致、relation 38，rc=0）；`expected.tsv` sha256 与改前一致（`a88af424…`，期望值与槽类型零变化）；`check-arch` = arch-smoke 10/10 + 25-service PASS + cfx 探针 12/15（044t/045t/integ046t 红，见遗留）；`build-bootrom` rc=0；一键证据脚本 20/20。
**修改文件**（107 项，`git status -uall` 全为 M/D、无未跟踪）：`tests/inst/` 60 `.S` + 5 `.inc`；`tests/arch/` 13（umon 10 + hmon 3）；`tests/ee-tiny/` 7 `.S` + 删 `common_tiny.inc`；`tests/ee-vast/` 6；`tests/shared/` 删 `asm/machine.inc` + 改 `asm/signature.inc` + `README.md`；`tools/linux/` 3（两探针 + `k1_boot_probe.py`）；`tools/chipyard/` 5；`tools/testcases/` 2；`tests/data/inst-signature/inputs.sha256`；`tests/arch/hmon/expected.yaml`；`tests/README.md`。
**验收结果**：① 零残留：代码/测试/工具/文档 0 命中（残留仅 `.tao/tasks/**` 历史任务书 21 行，含本任务书自身标题，与 `.tao/archive` 同性质，不改写历史）；两文件已删且 `git ls-files` 无。② 门控全绿 rc=0：`check-tests-index`（PASS 472）、`check-inst-macro-scope`、`check-case-ledger`（5681 条）、`check-index-blobs`、`check-knowledge-refs`、`check-dirs`。③ bootrom md5 旧 `514300876ea66ec108396334f3ef2b0f` → 新 `a5d78816a95469766639fa658b647ef3`（写入 `tests/arch/hmon/expected.yaml` 并现场核对）。④ 符号路径：不存在 `LOAD_ADDR <label>`；1232 处 `set.rb/set.rd`（改动文件）操作数 = `.equ/.set` 绝对常量（122 符号）+ `--defsym` 整数（29 符号 / 3 个 probe）+ 宏参（166 处，全部绑定 rb）⇒ **全常量表达式**，不涉及 `R_DADAO_ABS48`（该路径另有既有 lit `set-symbol.s` PASS 佐证）。⑤ 可达 FAIL（`cp`+md5 还原，禁 checkout/restore）：注入 `set.rb rb5, 0x1234→0x1235` ⇒ 用例 rc=2/`[FAIL]`，还原 md5 `6e810b2518c5ed03b8df6b3774595c6b` 回绿；删 `machine-tiny.inc` 的 `.equ RAM_BASE` ⇒ `ASM HEADER DRIFT` rc=2，还原 md5 `bbef1d358905f6c04e01ae75a27920d8` 回绿。
**需重测周期的镜像清单**：全部指令流变化的镜像 = `tests/inst` 含装载的 60 个 `.S`（528 处，旧 4 条 → `set.rb` 1–4 条）+ Tiny/Vast BootROM（`bootrom_tiny.bin`、`bootrom_step5{,_inst}.bin` 及 power/hmon/smon 段）+ arch umon/hmon 向量（13）+ K0/K1 probe（`hmon/smon/probe_kernel_k0_vast`、`tools/linux` 两探针）+ chipyard `app.S`/`vastwalk.S`/`vastptw.S`。按指令类的周期表不受影响；凡记录「实测总拍数」的结果作废（指令条数变）。
**新发现/坑**：① 任务书估数偏低：`LOAD_ADDR` 实为 **100 文件 / 528 调用**（另 5 处宏定义/注释），其中 **49 处目的是 rd** ⇒ 必须 `set.rd`（`set.rb` 会 bank 不符）；`LD64` 实为 **8 个本地宏 / 168 调用**（ee-vast 5、ee-tiny 1、tools/linux 2、`app.S` 经 `common_tiny.inc`）⇒ 逐个按寄存器组映射（rb→`set.rb`、rd→`set.rd`）。② `inst_expected.py` 是期望值派生器，必须认识 `set.rb`（否则 `ld.o` 基址退化为 unknown ⇒ 槽 kind 由 value 变 relation、`expected.tsv` 漂移）；只改一处判定分支。③ `k1_boot_probe.py` 反例串是**逐字节**匹配 `hmon_k0_vast.S` 的，替换须同步分隔符（`set.rd rd6` 空格 vs `LD64\trd6` 制表），否则 `check-linux-k1` 直接 SystemExit；已用 `count==1` 断言。④ arch 探针 `-d cpu` 日志可打满 tmpfs（实测 13 GB）。⑤ `check-cfx-aliases/-alias-table`、`check-syscall-abi`、`check-milestones-fresh`、`check-temp-dirs` 的红均与本次无关（spec 行号漂移 / 缺组件源码检出 / 他人 worktree / 陈旧临时目录），已逐条比对基线。
**遗留问题**：① `check-arch` 3 个 cfx 探针（044t/045t/integ046t）在本机安装根上**基线即红**：未改基线树重跑日志与本次**逐字节相同**（主仓 master 同日日志亦同）⇒ BLOCKED（非本任务引入），需另立任务或在匹配的 qemu 构建上复跑。② chipyard 签入 `bootrom.tiny.hex` 未重生成（属 `components/` 补丁集 + `m12-chipyard-028` 跟随项），新 md5 已入 `expected.yaml` 的 pending 项。③ gem5/chipyard 分支与 `check-linux-k0/k1`、`check-picolibc-tests` 未在本机跑（缺 kernel/gem5/chipyard/picolibc 产物），已用等价证据替代：K0 probe 36/37（唯一失败项与基线逐字节同）、两 semihost 探针与 chipyard/vastwalk/vastptw 全部装配+链接 PASS、picolibc crt0 装配 PASS。

## 审阅记录

### 第 1 轮 engineer 自审（m15-testcases-021）

**审查范围**：107 个改动文件按类抽查（.inc 宏层、rd/rb 混用文件、probe/工具链、基线文件）+ 转换规则与工具链改动逐行核对。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `inst_expected.py` 不认 `set.rb` ⇒ 期望 kind 漂移 | ✅已修 | 合并为 `set.rd/set.rb` 同一分支，删 `load_addr` 分支 | `expected.tsv` sha256 与改前一致；`check-inst-sig` 272/272 |
| F2 `k1_boot_probe.py` 反例串与 `.S` 分隔符不一致（tab vs 空格） | ✅已修 | 串改为 `"\tset.rd rd6, …"`，与转换后 `.S` 逐字节一致 | `count(HNEG_CASE3)==1`；`SMON_NEG_CASE=0..3` 与 magic 替换均装配 rc=0 |
| F3 宏参基址寄存器组未知（`\base`/`\mbase`） | ✅已核 | 统计全部调用点：`\base`→rb3/rb4…、`\mbase`→rb3/rb4，全为 rb | 转换全部用 `set.rb`；272/272 + arch 向量执行绿 |
| F4 rd 目的的 `LOAD_ADDR`（49 处）若用 `set.rb` 会 bank 错 | ✅已修 | 按寄存器前缀映射 `rd* → set.rd` | 272/272 装配+执行绿 |
| F5 `.org`/lds 偏移 ASSERT 可能因指令数变少而反向/失配 | ✅已核 | —（未改） | bootrom/step5 self-test、`power_vast.lds`(+0x2000/+0x2400)、vastwalk/vastptw lds ASSERT 全 PASS |
| F6 删宏块留下多余空行 | ✅已修 | 折叠为单空行 | 重建 bootrom md5 不变（`a5d78816…`） |
| F7 残留 token 落在历史任务书 | ❌不修 | — | 仅 `.tao/tasks/**` 历史记录 21 行（含本任务书），与 `.tao/archive` 同性质，不改写历史 |

**判决**：全部可修 finding 已修，无未修实现项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（m15-testcases-021）

**重跑记录（命令在 worktree 根、相对路径；rc 均取被检命令自身；证据 = 运行期证据目录内的 `run.sh` 与运行期日志目录）**
1. `run.sh --inject` ⇒ `RESULT: PASS (20/20)` rc=0（57 s）：零残留 0 / 两文件已删 / `expected.tsv` sha256 `a88af424c97849055f39d5a4068a4067fceb8b98f27c8ac52ac647e0b0704761`（与 `HEAD~1` 逐字节同）/ `build-bootrom` rc=0 / `check-inst-asm` 272/272 / `check-inst-sig` 272/272 / 6 门控 rc=0 / 脚本两路注入红→还原→回绿。
2. 零残留亲验：`grep -rn "LOAD_ADDR\|LD64" tests/ tools/ docs/ components/` = **0**；`git ls-files` 两文件无（rc=1）；全仓排 `.tao/`、运行期目录、`.git`、`.cache` 后仅证据脚本自述 4 行；`.include` 残留 0、`tests/README.md` 登记已清。
3. bank 全量机械配对（非抽样）：696 处（`LOAD_ADDR` 528 + `LD64` 168）逐处核「目的寄存器不变 + 伪指令 bank == 目的前缀 + `LOAD_ADDR` 表达式逐字相同 + `LD64` 四 wyde 拼值相等」⇒ **0 问题**；49 处 rd 目的全为 `set.rd`；全树 `set.rb rdN`/`set.rd rbN` = 0；配对处数与声称的 528/168 一致。
4. 槽数现场派生：`expected.tsv` 数据行 4528 = value 4482 + table 8（静态 4490）+ relation 38，与门控打印一致；`inputs.sha256` 284 条 `sha256sum -c` rc=0；`check-case-ledger` 5681 条、`check-tests-index` 472 条。
5. 我方独立注入（锚点均异于脚本，`cp`+md5 还原）：① `tests/inst/02-reg-copy/rd2rd_orri_rd.S` 改 `set.rd rd6` 常量 ⇒ rc=1/`[FAIL]`，还原 md5 `330d62b216505c032540c54ec549a1cc` 回绿 rc=0；② `tests/shared/asm/machine-vast.inc` 删 `.equ BOOTROM_BASE` ⇒ `check-tests-index` rc=2 `ASM HEADER DRIFT`，还原 md5 `45295288d7fd0344da440711466f2b47` 回绿 rc=0；③ 把 `set.rd rd5` 改成 `set.rb rd5` ⇒ llvm-mc 汇编期即判错 rc=1（bank 错必红，可达 FAIL 成立）。
6. 门控亲跑 rc=0：`check-tests-index`、`check-inst-macro-scope`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs`、`check-dirs`。
7. `check-arch`：整目标本 worktree rc=2，根因 = 该树无组件源码检出、`install-host` 前置失败（环境，非用例）；改按 Makefile 同命令直接复跑 15 个 cfx 探针 ⇒ **12/15 过**，红 = 044t/045t/integ046t；其中 **14/15 日志与主仓 master 基线（不含本改动）逐字节相同**，唯一差异 integ007t 仅运行期路径 + power 段 344→292（指令变少，双方均 PASS）⇒ **三红为基线预存**，与完成区自报一致。
8. bootrom：`make build-bootrom` rc=0，新 md5 `a5d78816a95469766639fa658b647ef3` == `tests/arch/hmon/expected.yaml` 的 `shared_bootrom_md5`；旧 `514300876ea66ec108396334f3ef2b0f` 见 `tests/data/m13-005-acceptance.json`。

**约束核验**：只动 `tests/`+`tools/`+本任务书（107 项 = 105 改 + 2 删，另任务书本身 1 改）；`spec/`、契约、`Makefile`、各门控脚本 **0 改**（`tools/testcases` 仅 `inst_expected.py` 判定分支与 `picolibc_test_crt0.s`）；新增「银行」0 处；开工/收尾快照一致（`git status -uall` 空、`git diff HEAD` 空），注入全还原；未提交 git。

**缺口判定（chipyard 签入 `bootrom.tiny.hex` 未重生成）**：确被消费（`build.sbt` 的 `resourceGenerators` 把它解码成 wuming 仿真用的 classpath 资源），但**不构成本任务阻断**——不在任务书验收面（只覆盖 `tests/`/`tools/`）、旧 hex 是等价语义的旧编码故行为不变、已入 `expected.yaml` 的 `pending_followups`，且架构师已另立 `m16-chipyard-015`（重生成签入 hex）并入台账 ⇒ 判为**可接受后续项**。

**范围扩大判定（属实且已披露）**：`LD64` = 8 个宏定义（ee-vast 5 + ee-tiny 1 + tools/linux 2）/168 处调用，`app.S` 只 include 未调用；diff 非机械行仅＝被删宏体与 `inst_expected.py` 判定分支，**无未披露改写**；`expected.tsv` 未变即证期望值/断言未被削弱。

**Finding（文档级，不阻断，交 architect 收尾改）**：① 完成区「`LOAD_ADDR` 100 文件」与实测不符（含调用行 98 文件、含 token 103 文件；**528 处本身准确**）；② `components/chipyard/README.md` 仍称签入 hex「与 QEMU/gem5 同版（`514300876e…`）」已过期，待 `m16-chipyard-015` 一并改；③ 完成区注入①写「rc=2」，实为包装脚本 rc=1（qemu 内层 rc=2）。

**判决：Accepted**（验收命令块在我方重跑下全过、约束无违反；上述三条文档级 finding 不阻断）
