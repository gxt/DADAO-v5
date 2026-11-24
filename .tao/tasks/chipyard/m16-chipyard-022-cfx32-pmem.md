# m16-chipyard-022: RTL cfx32 pmem（DMA + 源 cfxha 32 的完成投递）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-026`（R2 捕获缓冲）合入；`m18-spec-005`（R2 规格）已合入；`m16-chipyard-024` 已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

`ADR-0061`：PMEM_DMA 以 **cfxha 32** 标识；pending/帧内位 = `1<<32`；掩码在**当前模式 monitor** 的 `cg8 rc1`（bit32）；帧内细节回 `cfx_pmem cg15 rc4`（W1C），不走 `cause_info`。`cfx_hart cg9` 七槽与仲裁由 024 提供，本任务补 cfx32 的寄存器/DMA 与完成投递。

## 要做

1. **寄存器面**：`pmem_exist`、`pmem_start[0..63]`、`pmem_size[0..63]`、`pmem_attr[0..63]`、`dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`（`DADAO-12 §4.9`；`DONE/ERROR` W1C、`ERR_CODE` one-hot、`BUSY` 期写忽略）。
2. **DMA**：单 hart 搬运；源/目标/大小校验；`dma_status` DONE/错误；与 TLB/PTW 交互按契约。
3. **完成投递（R2 捕获缓冲）**：完成（或错误）⇒ 置 `cfx_hart cg9 src_pending` 的 bit32；放行（当前模式 monitor 掩码 bit32=0）⇒ 同一指令边界投递并**整体覆盖** `cg9` 捕获；同界多源时 `src_frame` 为位图并集（与 timer 15 同一次进入）。**没有帧空/帧活动期门控**。
4. **pending 跟随源**：投递即清 bit32；`dma_status` W1C 后 pending 落（不产生遗留投递）。
5. **`escape`（R2）**：`imms18=2` **不用于异步返回**——按所选帧无效报当前 cfx 的 `CFXESC`，不改变 cfx/mode/`cg9`；`imms18=3`/`[17:2]≠0` ⇒ `ILLI`。
6. **探针**：pmem 配置/DMA/回读；完成投递（单源 + 与 timer 同帧多源）；H/S/U 三模式（各写自己 monitor 掩码）。
7. **不回归**：Tiny 无 cfx32；页表/PTW 既有探针；cfx3/4/5/15 不变。

## 不做

- 不做 cfx34（023）；
- 不改 `escape` 编码、不改 `cfx_hart cg9` 布局（024）；
- 不做 monitor-first、多核、uart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. pmem 配置/DMA 逐字节；`dma_status` DONE/ERROR/ERR_CODE；
2. 完成投递：`src_pending` bit32、`src_frame=1<<32`、mask 位 32、ack 后 pending 落；
3. **同界多源**：timer(15)+DMA(32) 同时 pending ⇒ 一次进入、`src_frame` 并集、`excp_async_num` +1；
4. H/S/U 三模式投递目标均 `cfx_hart`/supv；覆盖语义（不搬走再到期 ⇒ 整体覆盖）；
5. `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/`[17:2]≠0` ⇒ `ILLI`；
6. **可达 FAIL ≥2**：注入"DMA 不搬运"、"完成投 monitor"、"pending 记 18" ⇒ 红；`cp`+md5 还原并强制重建回绿；
7. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录 `run.sh`：A 10/10、B 2/2、C 3/3、D 6/6、E 13/13、F 4/4、G 21/21（合计 59/59，rc=0）；pmem 探针 H 85/85、S/U 各 8/8；cfx15 三模式 74/34/34；cfx5_regs 22 记录；arch-ptw 12 signature PASS + 3 登记 GAP；Tiny 11-cfx 4/5（`escape_ciii_cfx` = `DIV-11` 既有口径，rc=13）、01-load-store 38/38。

**修改文件**：`components/chipyard/patches/generators/chipyard/src/main/scala/config/DadaoConfigs.scala.patch`（地址图/`kaiwu-vast-pmem-sram`/`WumingVastParams` 新字段）；`.../dadao-gewu/.../GewuFile.scala.patch`（`GewuPmemParams`/`PmemState`、pmem 行/读写/START 校验/事件与 ack、异步位图扩到 TIMER|PMEM）；`.../dadao-wuming/.../WumingPmem.scala.patch`（新增，DMA 引擎）+ `WumingParams.scala.patch` + `WumingCore.scala.patch` + `WumingTile.scala.patch`；`components/chipyard/series`（31 条）；`components/chipyard/{README.md,changelog.md}`；`tests/arch/pmem/{pmem.S,pmem.lds,check_pmem.py,README.md}`（新增）；`tests/arch/README.md`；本任务书。未改 `spec/`、`.tao/contracts/`、`contracts/`、QEMU/gem5/工具链。

**验收结果**：① 寄存器面：`pmem_exist` 读全 1（测试机约定 64 区域）、`start/size/attr[0]/[63]` RW、`dma_size` 30 位、`dma_ctrl` START 自清 / DIR|IRQ_EN 读回、cg15 rc5/rc63 与 cg8 rc1 ⇒ `CFXREG`（cause=1<<2、info=指令字）、BUSY 期 `dma_src` 写忽略。② DMA：8 B / 32 B 往返、3 B 部分拍保留邻居、6 B 起点 0x607→0x70F 跨拍、`0xFFF8+8` 末边界合法 DONE；SIZE（0、>2^29）/CFX_RANGE（2^29、0xFFFC+8、偏移 0）/PA_RANGE/PA_FAULT（写 ROM）四类错误；ROM 读合法；DONE/ERROR W1C（ERROR 清 ERR_CODE）。③ `PMEM_DMA`：屏蔽期 pending=bit32、frame=0；放行后 prev=hypv/hmon、`cause_ip`=放行后边界、frame=bit32、pending=0、`excp_async_num`=1；同界 timer(15)+DMA(32) 一次进入、frame 并集、计数 +1；W1C ack 后 pending 落且解除掩码无遗留投递；再触发 ⇒ 第二次进入整体覆盖（num=3、新 `cause_ip`）；`escape imms18=2` ⇒ `CFXESC` 且 cg9 四槽不变；`imms18=3`/`4` ⇒ `ILLI`。④ S/U 各写自己 monitor 的 `cg8 rc1`：prev=user/umon、supv/smon，frame=bit32，num=1，投递目标仍 cfx_hart/supv。⑤ 注入 3 路：DMA 不搬运（slot 22/23/28 数据红）、完成投 monitor（红）、pending 记 18（红）；`cp`+md5 还原（GewuFile `0027b96a…`、WumingPmem `9483e575…`）并强制重建后 85/85 回绿。⑥ 构建：Vast 285 s（注入轮 284–299 s）、md5 `d9d613c3…`；Tiny 98 s、md5 `ea76f66a…`（只作记录，ISS-453）。⑦ 门控：`check-patch-tree` chipyard 31 patches/0 problem、`make_patch` 0 written、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch.py --self-test` rc=0。⑧ 不回归：cfx15 三模式、cfx5_regs、ptw 12 例；Tiny 无 `pmem` 字符串、11-cfx 与 01-load-store 同基线。

**新发现/坑**：① `pmemEvent` 若组合进 `intr.valid` 会与核的 `wEn` 形成 FIRRTL 组合环（`wEn→intr.valid→asyncTake→wEn`）⇒ 用 `RegNext` 打一拍。② `GewuCfxParams.vectorBase` 兼作 cg7 start 锚点：pmem 填 0 会让 `spaceStart=0-(32<<42)` 为负，firtool 报 "UInt literal … is negative" ⇒ 必须填 SRAM 基址。③ U/S 访问非 monitor cfx 在 020 两轴规则下 fail-closed（`DIV-09`）：pmem 必须开 `commonRows`，否则 SBI `PMEM_DMA` 无法从 smon 调用；S/U 探针因此在 hypv 启动长 DMA、在目标模式观察完成。④ QEMU/gem5 的 cfx_pmem 只实现 cg15（+cg7），cg8/12/13/14 走 `CFXREG`；RTL 按 §4.9 全实现 ⇒ 不能三方逐槽比（`DIV-06` 仍开）；`pmem_exist` 值 spec 未定（测试机约定 64 区域全 1）。⑤ DMA 绕过 D-cache：PA 侧不经 `WumingCache`，探针只用 CPU 未触碰的 PA 行，避免把一致性缺口写进判据。⑥ 误把改动写进主仓共享源树（相对路径解析到会话目录）：已用 `git diff` 核对为本次误写的 2 文件+1 新文件并恢复（该树随后 `git status` 空），此后一律绝对路径。⑦ `arch-ptw-013` 的 RTL GAP 理由（cfx_pmem SRAM 不可达）已被本任务消除，`rtl-coverage.yaml` 仍记 gap。

**遗留问题**：① `arch-ptw-013` 可提升为 signature 用例（pmem SRAM 现可达）。② QEMU/gem5 的 pmem cg8/12/13/14 寄存器面缺口与 `pmem_exist` 取值需跨平台对齐（`DIV-06` 待 023）。③ DMA 与 D-cache 的一致性未定义（单 hart 测试面外）。④ U/S 下的 pmem 寄存器面未逐项覆盖（探针只在 hypv 做寄存器面；U/S 只验投递）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile` 的 pmem 参数/行解码/读写/START 校验/事件与 pending·ack、`WumingPmem` 的 8 态搬运 FSM 与拍内字节替换、`WumingCore` 的端口/参数/`inSpecWindow`、`WumingTile` 的第三个 client 与接线、`DadaoConfigs` 地址图、`WumingParams` 的 cfx 序列/`commonRows`、`pmem.S` 全部槽序与三分支、`check_pmem.py` 的 facts/expected/self-test、`run.sh` A–G。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 组合环（`pmemEvent` 组合进 `intr.valid`） | ✅已修 | `pmemEvent` 改为 `RegNext(raw)`，事件打一拍 | Vast 构建变绿、组合环消失 |
| F2 `vectorBase=0` 使 cg7 start 为负（firtool 报错） | ✅已修 | pmem 的 `vectorBase` 填 `pmemBase` | 构建 0 error |
| F3 `cfx_pmem` 无 `<mode>` 行 ⇒ U/S 访问 fail-closed | ✅已修 | pmem 开 `commonRows`；`GewuParams` 的 require 允许 pmem | U/S 探针 + SBI 可达 |
| F4 S/U 探针在目标模式无法直接起 DMA | ✅已修（设计） | hypv 启动长 DMA、目标模式观察完成 | S/U 各 8/8 |
| F5 `pmem_exist` 取值 spec 未定 | ❌不修（约定） | 测试机约定 64 区域全 1；checker 显式声明 | README/checker 注明 |
| F6 DMA 绕过 D-cache 的一致性缺口 | ❌不修（范围外） | 探针只用冷 PA 行；登记遗留 | 探针数据全绿 |
| F7 构建脚本让 conda python 遮蔽仓库工具（`tomllib` 缺失） | ✅已修 | conda `PATH` 只在 build 子 shell 内生效 | A 段 10/10 |
| F8 Tiny 构建 md5 与旧记录不同 | ❌不修（记录口径） | 只作记录（ISS-453）；生成 SV 无 pmem、套件结果同基线 | F 段绿 |

判决：F1–F4、F7 已修并复验；F5/F6/F8 为有据的不修项；无未修 finding。状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲跑、按段；分支 `m16-chipyard-022` @ `5da8dd51`；命令均为仓库根执行运行期证据目录内的 `run.sh` + 参数）：

1. `ONLY=A`（注入前、注入后各一次）：10/10 PASS、`EXIT=0`；日志 `chipyard: 31 patch(es)` + 全树 `463 patches OK`（其余组件源树 absent，只采信 chipyard 段）；`make_patch` 两跑 `0 written, 31 unchanged`；`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch.py --self-test` 全 rc=0。
2. `--inject INJ_ONLY=1,2`：14/14 PASS（后台跑、`FAIL=0` ⇒ 按脚本逻辑 `exit 0`；同脚本失败路径我亲测 `INJ_ONLY=9` ⇒ `FAIL=1, EXIT=1`）。inj1「DMA 不搬运」⇒ `check_pmem rc=1` 红、`cp`+md5 `9483e575` 还原、强制重建 md5 `d9d613c3`、回绿 85 槽；inj2「完成投 monitor」⇒ guest rc≠0 红、md5 `0027b96a` 还原、重建 `d9d613c3`、回绿 85 槽。inj3（pending 记 18）按「任取 2 路」未跑，静态核其替换模式在源内存在且 `assert old in s` 保非空 ⇒ 可达红。
3. `ONLY=C,D`：9/9、`EXIT=0`；`check_pmem[3]: 85 slot(s) match`、`[2]`/`[0]: 8 slot(s) match`；另抽 U 流 8 槽原始值：`pending=1<<32、frame=0、prev_mode=0(user)、prev_cfx=0(umon)、cause_ip=umode_wait_begin、frame=1<<32、pending=0、num=1`。
4. `ONLY=E`：13/13、`EXIT=0`；cfx15 `74/34/34 slot(s), 0 failure(s)`；cfx5_regs `22 records`；arch-ptw 我 `grep -c` 现场计数 PASS=12、GAP=3、FAIL=0。
5. `ONLY=F`：4/4、`EXIT=0`；Tiny 生成 SV 无 `pmem`；11-cfx `total 5 ok 4 fail [escape_ciii_cfx.S]`；01-load-store `[PASS]` 38 / `[FAIL]` 0（向量目录实数 38 个 `.S`）。
6. `check_pmem.py --self-test`（mode 3/2/0）：control / 逐槽 mutation / 截断·多余槽 三问全 PASS。
7. 快照对账：`git status --porcelain -uall` 注入前后**逐行相同**；`GewuFile`/`WumingPmem`/`series`/`pmem.S`/`check_pmem.py` md5 前后一致；源树两文件 `0027b96a…`/`9483e575…`；`spec/`、`.tao/contracts/`、`contracts/` 零改动。

**约束核验**：

① 寄存器面逐项对齐 `DADAO-12 §4.9`：RO `pmem_exist` 写⇒`CFXREG`、`cg12/13/14 rc0-63` RW、`cg15 rc0-4`、`dma_size` 30 位、`dma_ctrl` START 自清+DIR/IRQ_EN 读回、`dma_status` BUSY/DONE/ERROR 粘滞 W1C+ERR_CODE one-hot、`cg15 rc5/rc63` 与 `cg8 rc1`⇒`CFXREG`、START 校验失败不置 BUSY、BootROM 写⇒`PA_FAULT`/读合法——RTL 解码与探针断言我逐条对照 `§4.9` 正文/表核过，实测绿。

② DMA：8 B/32 B 往返、3 B 部分拍保留邻居、6 B `0x607→0x70F` 跨拍双字、`0xFFF8+8` 末边界、SIZE(0/>2^29)/CFX_RANGE(2^29、`0xFFFC+8`、偏移低于基址)/PA_RANGE(>2^56)/PA_FAULT 四类均有独立断言。

③ R2 捕获：屏蔽期只置 `cg9 rc4` bit32、放行同界投递+`frame=bit32`+pending 清+`async_num`+1、timer+DMA 同界一次进入并集（计数 1→2）、W1C 后 pending 落且 `0xDEAD0006` 证明无遗留投递、再触发 `num=3` 新 `cause_ip` 整体覆盖、`escape imms18=2`⇒`CFXESC` 且 cg9 四槽等值不变、`3`/`4`⇒`ILLI`。

④ 三模式 H85/S8/U8：S/U 各写**自己** monitor 的 `cg8 rc1`（若错用 hmon 行 ⇒ pending 永不放行 ⇒ 流截断判红，可达）；`prev` 实测 user/umon、supv/smon；投递目标经 `cg9 rc5` 向量落 `cfx_hart`；入口模式 supv 仅由出口 trap 与跨 cfx 写**间接**覆盖（`cg9 rc6` 恒 supv，记录它无判别力）——记备注，不算缺陷。

⑤ `pmem_exist` 取值：spec、`contract-see`、`contract-cfx-aliases`、运行期别名表均只定 `(cfxha 32, cg8, rc0)` 不定值；「64 区域全 1」为测试机约定且 README+checker 显式声明 ⇒ **与契约一致**，非从实现反推。

⑥ 范围纪律：未改 `spec/`/`.tao/contracts/`/`contracts/`、未提交 git、术语与「运行期证据目录内的 `run.sh`」写法合规、无临时残留（`check-no-residue` rc=0）。

**遗留四项判定**：

(1) `arch-ptw-013` 的 GAP 理由（RTL 不把 pmem SRAM 窗口当 cfx 旁路）**确已被本任务消除**（`inSpecWindow` 纳入 pmem 窗口 + 探针 hmon `ld/st 0x83ff…` 全绿）；但提升 signature 须改 `tests/arch/ptw/ptw_sig.S` 的 `PTW_CASE=13`（testcases 域，且与本任务「PTW 既有探针不变」冲突）⇒ **不在本任务提升，应另立任务或登记 issue**；目前只留在本任务书遗留段，architect 收尾须落 backlog。

(2) **属实**：QEMU `helper.c` 只有 `cg==15 && cfxha==PMEM`、gem5 `node_cfx.cc` 只有 `cg==15 && CfxhaPmem`，均无 cg8/12/13/14 ⇒ 暂不能三方逐槽比。附带提示：`DIV-06` 的 `close_when`（021/022/023 全合入）在 023 后**仍不足以关闭**，须补一条 pmem 寄存器面 divergence 或改写该条件。

(3) **需要登记 issue**（P3）：DMA 旁路 D-cache 的 PA 侧一致性 spec 未定义（`§4.9` 把 cache 一致性属性推到 SMP 阶段），探针靠「只用 CPU 未触碰的 PA 行」回避 ⇒ 属能力/语义缺口，不应只留任务书遗留段。

(4) U/S 下 pmem 寄存器面未逐项覆盖：与任务书第 6 条（三模式只要求各写自己 monitor 掩码+投递）一致，README/遗留④已明示 ⇒ 接受为遗留，后续用例任务补。

**finding（均不阻断）**：F1 BUSY 期 `dma_status` 的 W1C 忽略有 RTL 实现但探针未断言（只断 `dma_src` 写忽略）；F2 `run.sh` 期望值写死（`31`/`12`/`3` 属「误报红」方向；`01-load-store (38 images)` 只断 rc 不核数，我现场数 38 属实，建议改现场断言）；F3 `check_pmem.py --self-test` 未纳入 `run.sh`（我单独跑过，三模式均 PASS）。

**判决：Accepted**——验收命令块在我自己的分段重跑下全绿、硬约束无违反、注入红→`cp`+md5 还原→强制重建回绿均亲验；遗留四项按上判处置。
