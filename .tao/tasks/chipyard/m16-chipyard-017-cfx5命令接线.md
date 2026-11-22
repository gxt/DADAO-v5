# m16-chipyard-017: RTL cfx5 命令接线

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-016`（cfx5 寄存器面）
**可并行分片**：否
**预估**：3–5 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

`m16-chipyard-016` 已让 cfx5 寄存器可访问；本任务把 `cache_ctrl` 命令接到 `WumingCache` 的 D/I 阵列（现有 cmd 口在 `m16-chipyard-009/010` 中接空）。

## 要做

1. **命令解码**：按 `m16-spec-001` 的 `[1:0]` 操作、`[3:2]` 范围、`[15:14]` 选择，`cache_addr_start`/`cache_addr_size` 按 56 位 PA。
2. **D 侧**：clean（写回保留）、invalidate（丢弃脏行）、flush（写回+删除）；范围 all/单行/区间；使能位为 0 不维护；不可缓存/MMIO 无效果不报异常。
3. **I 侧**：clean no-op；invalidate/flush 使 I-Cache 行失效；I 无 dirty。
4. **per-hart**：命令只作用本 hart（单 hart 下无跨核问题）。
5. **Tiny**：Tiny 无 cfx5，行为不变。

## 不做

- 不改 `WumingCache` 的填充/替换算法（只加命令通路）；
- 不改 cfx5 寄存器位域（016）；
- 不写三方用例（`m16-testcases-009`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出（`components/chipyard/patches/**` + `series`），`make_patch.py chipyard` 幂等；
- 重建环境（JDK/conda/`RISCV`）写进证据脚本；不把环境问题当代码失败；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：D 脏行 invalidate 后内存旧值（DMA/直连读可见）、clean 后新值、flush 后行失效；I 侧改写代码后 invalidate 生效；
2. 范围/使能/异常逐条；Tiny 代表例不回归；
3. **可达 FAIL**：注入「invalidate 先写回」⇒ 红；注入「I 侧不失效」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（A–F）**PASS=60 / FAIL=0**、rc=0；`run.sh --inject` **PASS=31 / FAIL=0**、rc=0。探针 29 条记录逐条等于生成器/合约派生期望——I 侧 0x1111→0x3333（单行 invalidate）→0x5555（区间）→0x7777（flush），`I|clean` 后仍执行旧 0x1111；D 侧 invalidate 后内存 0x7777、clean 后 0xbbbb、flush 后 0xdddd 且下次 D 读缺失返回 0x4c50dddd71140000；区间 R0/R1 的 invalidate/clean/flush、all 的 invalidate/clean/flush、`enable=0` 时 invalidate 为 no-op 且 clean 仍见脏行（0xeeee）、无行 PA 见证、三处非法编码 `CFXREG`（cause_id=0x4、cause_info=0x7b148247，且 f1/f2 的非法命令未改动脏行/未丢行）。缓存日志 118 条事件逐条断言：invalidate 无 wb、I|clean 不进 I 侧且其后取指命中、I|invalidate 后重缺失、flush 后重缺失、区间只枚举两行、`enable=0` 的 invalidate 仅 1 次（未发出）、无行 PA 为 miss。判据 `--self-test`：29 条记录 mutation + 4 种日志 mutation 全部被拒。016 寄存器面探针在新 RTL 上 22 条 PASS。Tiny `11-cfx` 5/5、`01-load-store` 38/38，改前（016 二进制，md5 `6d699cc3…`）/改后逐镜像结果字节差 0。
**修改文件**：组件源 2（`generators/dadao-wuming/src/main/scala/wuming/common/{WumingCache,WumingCore}.scala`，已收敛 base+1 并导出两份补丁，`make_patch.py chipyard` 2 written / 24 unchanged）；`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/cache/{cfx5_maint.S,cfx5_maint.lds,gen_cfx5_maint_tables.py,check_cfx5_maint.py}`；`tests/arch/README.md`、`tests/arch/cache/README.md`；本任务书。未改 `WumingCache` 填充/替换、016 寄存器位域、spec/契约、QEMU/gem5。
**验收结果**：① 记录见上；D 侧「是否写回」以**取指端口**为独立观测量（经 D 改代码行 → 命令 → `I|invalidate` → 跳转执行到的立即数即内存内容），日志另断言事件序列。② 可达 FAIL：inj1「单行 invalidate 先写回」⇒ guest rc=6（第 6 检查点）、oracle rc=1，`cp`+md5 `8b6ca1b3…` 还原、重建 310 s 后 guest 0 / 流相同 / oracle 0；inj2「I 侧不维护」⇒ guest rc=3、oracle rc=1，`cp`+md5 `c6e19573…` 还原、重建 307 s 后回绿。③ 构建：强制重建（删 `generated-src/<cfg>`、仿真器、`chipyard.jar`）Vast **314 s**、Tiny **104 s**，注入重建 297/310/314/307 s，`%Error`=0；Vast sim md5 `e10ba231…`、Tiny `adbf374b…`（只作记录，ISS-453）；环境 JDK `20.0.2-internal`、conda gcc `13.2.0`、Verilator `5.020`、`RISCV` 指向组件 `.conda-env/riscv-tools`。④ 门控：`check-patch-tree` chipyard 段 **0 problem**（全局 rc=2：他人组件的 KNOWN-RED 错误集，逐行 diff 已打印；遇他人组件 `read-tree` 崩溃时脚本重试 3 次并断言「确实到达 chipyard 段」）、`make_patch.py` 幂等 `0 written`、`check-source-state`/`check-index-blobs`/`check-tasks` 均 rc=0。
**新发现/坑**：① 维护丢弃若调用 `killAge`（按动态 set/way 重排 1024 条 age），D 实例 `WumingCache.sv` 会涨到 **2.2 GB / 2176 万行**，Verilator 单进程吃满 120 GB 被 OOM 两次；改为「维护丢弃不重排 age」（无效 way 本就是下一次填充首选，`fillAge` 在分配时重置）后 **12 MB / 9.5 万行**、重建 305–314 s；填充/淘汰的 LRU 语义与 `CACHE-05` 均不受影响。② 代码行必须用 `.dd.t32` 写两条 4 B 指令（`.dd.o64` 会把 4 B 字放到 +4 ⇒ 首条取指 UNDI），首跑即红。③ 故障例的 hmon 返回槽要指向紧邻故障指令的 `f*_resume`（写 `f*_resume2` 会跳过 cause 记录）。④ Chisel `printf` 的 `=` 后带对齐空格，日志解析要 `=\s*`；self-test 的日志 mutation 正则要允许 `line=0x0…` 零填充，否则「变异未生效」。⑤ `__CHECK_RD` 的 `dst` 不能是 `rd20`（宏先写期望值），先把实测搬到 rd5。⑥ 会话/服务器重启会杀 `setsid` 子进程，长构建改 `systemd-run --user` 保活；**运行中编辑 `run.sh` 会让 bash 读到半截脚本**（本次一次 rc=2，停止后重跑即好）。⑦ 诊断时在组件源树直接跑 `git read-tree <base>` 会覆盖索引（把补丁文件暂存成删除）⇒ `apply_series` 判 worktree dirty；用 `git reset`（mixed，非 `--hard`）恢复索引即可，工作树未动。
**遗留问题**：① `cache_enable=0` 目前只门控**维护命令**，不旁路正常访存；`contract-cache` CACHE-07 的「0 = 关闭」需改访问通路（超出「只做命令接线」范围，建议另立任务/待裁定）。② 维护写回被总线拒绝时报 `CFXMEM [56] ADWBFAIL`（保留脏行）；`contract-cache` CACHE-25 未定义命令级失败、本机全部可缓存内存可写 ⇒ 不可达，记为口径待确认。③ 本探针暂未登记 `tests/arch.yaml`（chipyard 后端仍 fail-closed，与 016 同口径）。④ 全局 `check-patch-tree` KNOWN-RED（ISS-463/507），非本任务引入。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`WumingCacheCmd` 的 scope/size 与三档维护 FSM（单行/全表/区间、invalidate/clean/flush、写回失败）；`WumingCore` 的 `sXlate` `kind = 4` 子状态机、两侧顺序、使能/clean 跳过、同步完成；探针页表/代码行/观测通道；checker 的记录/日志断言与 self-test；run.sh 的 rc 捕获、注入还原与门控。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 代码行用 `.dd.o64` 存 4 B 指令 ⇒ 指令落在 +4，首取 UNDI | ✅已修 | `.l_code` 改 `.dd.t32` 两条 | 首跑 guest rc=126 → 修后 rc=0、29 记录全 OK |
| F2 故障返回槽写 `f1_resume2`，跳过 cause 记录 | ✅已修 | 三处改指 `fN_resume` | 记录 21/22 = 0x4 / 0x7b148247 |
| F3 日志解析不认 `=` 后空格，`cycle` 全为 −1，7 条时序断言假红 | ✅已修 | 正则 `(\w+)=\s*(\S+)` | 修后 118 事件全绿 |
| F4 self-test 的日志 mutation 正则不认零填充 ⇒ 变异未生效 | ✅已修 | `line=0x0*%x` | 4 种日志 mutation 均被拒 |
| F5 `__CHECK_RD dst=rd20` 会先写期望值（恒真） | ✅已修 | 先 `or.o rd5, rd20, rd0` | 反汇编逐条核对 |
| F6 `killAge` 动态重排放大 age 逻辑，Verilator OOM | ✅已修 | 维护丢弃不重排 age（只清 valid/dirty） | SV 2.2 GB→12 MB；305 s 建成；记录/日志全绿 |
| F7 run.sh 的 chipyard 段正则把 testchipip 汇总行当错误；Cmd 字段计数命中 `WumingCacheRequest.addr` | ✅已修 | `chipyard(:[^:]+)?`；按类截取后计数 | 重跑 A 段 PASS |
| F8 运行中编辑 run.sh 使 bash 读半截脚本 | ✅已修 | 停止后用修好的脚本重跑 | A–F 60 PASS、rc=0 |
| F9 「真 Verilator 构建」阈值 10 MB 对缩小后的 Vast 过严 | ✅已修 | 改 5 MB | B 段 PASS |
| F10 `cmdError` ⇒ `CFXMEM ADWBFAIL` 超出 CACHE-25「唯一失败 CFXREG」 | ⏸延后（口径） | 保留显式失败 + 注释；登记遗留② | 本机不可达（可缓存内存全可写） |
| F11 `cache_enable=0` 不旁路正常访存（CACHE-07「关闭」） | ⏸延后（超范围） | 本任务只做命令接线；登记遗留① | 探针只断言「不维护」 |
| F12 诊断时 `git read-tree <base>` 覆盖了组件源树索引（补丁文件变暂存删除） | ✅已修 | `git reset`（mixed）恢复索引，未动工作树 | `apply_series`/`check-source-state` PASS |
| F13 全局 `check-patch-tree` 在他人组件 `read-tree` 崩溃时可先于 chipyard 段退出（原断言可能空过） | ✅已修 | 重试 3 次 + 「确实到达 chipyard 段」断言 + 工具内 chipyard-only 回退 | A 段 PASS（本次 attempts 1/3 即成功） |

判决：F1–F9、F12–F13 已修并复验；F10/F11 为口径/范围外的显式登记。状态 `待验收`。

### 第 1 轮 reviewer 验收（本人重跑）

**重跑**：仓库根执行运行期证据目录内的 `run.sh`（本意 `ONLY=A,C,D,E`，脚本按环境变量读取 ⇒ 实跑完整 **A–F**、含强制重建）⇒ `summary: PASS=59 FAIL=0`、`RESULT: PASS`、**退出码 0**。与完成区 60 的唯一差是 `check-patch-tree: non-chipyard error set == baseline` 一条——并发会话正改 gem5/qemu，本轮走 `[KNOWN-RED]` 分支未计 PASS；其余 59 条同名全过（A22/B13/C4/D6/E2/F12）。
- **门控**：`apply_series base+1 matches patches`；`make_patch 0 written/26 unchanged`（幂等）；`check-patch-tree: chipyard: 26 patch(es)`、chipyard 错误行 **0**；`check-index-blobs rc=0`、`check-tasks rc=0`；2 份补丁由 patch 还原出的文件与组件源树**逐字节相同**、源树 `git status` 空。
- **构建/功能**：重建 Vast **314 s**、Tiny **102 s**，`%Error=0`，sim md5 `e10ba231…`/`adbf374b…`（与完成区一致）；探针 `PASS (29 records, 118 cache events)`；016 寄存器面 `PASS (22 records, 176 bytes)`；`--self-test` 29 条记录变异 + 4 种日志变异**全被拒**；Tiny `11-cfx` **5/5**、`01-load-store` **38/38** 改前/改后逐镜像差 **0**。
- **独立注入（探针层，无需重建）**：`cp` 备份 + md5 `e884be84…` → 改 `cfx5_maint.S` 一处（`IMM7`→`IMM6`，md5 `68746696…`）→ `ONLY=D` 跑同一 `run.sh` ⇒ **RC=1、PASS=3/FAIL=3、RESULT: FAIL**（guest rc=19、stream 0、oracle rc=1；016 两条仍 PASS）→ `cp` 还原、md5 回 `e884be84…` → `ONLY=D` 重跑 ⇒ **RC=0、PASS=6/FAIL=0**。全程未用 `checkout/restore/stash`。
- **快照对账**：审查前后 `git status --porcelain -uall` 均为同一 11 行、逐行相同；交付物 md5 与审查前一致；改动范围 = 完成区「修改文件」声明，未动 `spec/`、`.tao/contracts/`、`tests/arch.yaml`；任务书无运行期路径、无「银行」。
**语义核验（静态逐条）**：`[1:0]/[3:2]/[15:14]` 解码；`scope=1` set/tag 直查、`0/2` 全表扫描按重建 PA 过滤（区间含 wrap 钳位）；`invalidate` 只丢、`clean` 写回保留、`flush` 写回后丢；I 侧 `clean` 不发（`pendI = sel(1) && enable(0) && op=/=1`）；`enable=0` 侧跳过；`sel=00`/`op=none` 无条件 no-op；非法编码 `writeOk` ⇒ `CFXREG`（实测 cause_id=0x4、cause_info=0x7b148247 且未改动脏行）；先 I 后 D、两侧 `cmdDone` 后才 `finish`（CACHE-24）。
**遗留判定**：① `cache_enable=0` 不旁路访存 ⇒ **不阻断**：DADAO-12 §4.6 与 CACHE-07/08/23 对该位只规定「该侧不被维护」，CACHE-30 可观测量清单无旁路项，任务书第 2 条同口径 ⇒ 实现与 spec 一致；「0=关闭」是否隐含旁路属**口径**，建议登记待裁定，不改本任务。② 维护写回被拒 ⇒ `ADWBFAIL` ⇒ **登记 GAP（类比 ISS-515），不要求本任务实现**：CACHE-25 未定义该情形；脏行只在 store 成功的 PA 上产生（`sLook`/`startFill` 对 `!putOk` 直接 respond error）⇒ 本机不可达；静默完成会谎称 clean 成功，显式失败更安全；契约变更须用户认可。③ `dropLine` 不重排 age ⇒ **不阻断**：victim 优先选 invalid way、`fillAge` 分配时重置、valid 条目相对次序不变；base 的 `killAge` 只被维护路径调用，填充/淘汰的 `touchAge`/`fillAge` 逐行未改；替换策略本由 CACHE-05 实现自定。
**Findings（非阻断）**：F1 探针无「两侧同选 + 合法操作」用例（`CTRL_ID_*` 仅 none/非法）⇒ CACHE-21 先 I 后 D 只有静态核验；F2 `CACHE-22` 以「无行 PA」代替真 MMIO 区间，动态覆盖弱；F3 `check-source-state` 全局因并发 gem5 dirty 报错，仅断言 chipyard 段（并发干扰，非本任务）。
**未独立重跑**：`run.sh --inject` 的 2 路 RTL 注入（各含 2 次全量重建）——采信工程师日志（inj1 guest rc=6/oracle rc=1、inj2 rc=3/oracle rc=1，还原后均 PASS），并核到两份注入备份 md5 与当前源树**逐字节相同**、恢复重建时间线自洽；RTL 层以本人探针层注入 + `--self-test` 变异补强。
**写入本记录后重跑 `make check-knowledge-refs`**：rc=2，唯一悬空是 `.tao/knowledge/milestones-m18.md:39 ADR-0059`（目标文件不存在，该行属 `m18-linux-013`、本任务未改）；本任务书运行期路径引用数 **0**、新增行无运行期路径 ⇒ 与本任务无关，登记为并发/前置遗留。
**判决：Accepted**——验收命令在我自己的重跑下全部通过、独立注入红→还原→回绿、约束无违反（不提交 git）。
