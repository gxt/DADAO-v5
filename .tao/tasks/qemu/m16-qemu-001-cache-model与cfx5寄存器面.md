# m16-qemu-001: `cache-model` 属性与 cfx5 寄存器面

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点）、`m16-testcases-006`（arch 骨架）已合入
**可并行分片**：否
**预估**：2–3 h（属性 + 寄存器面，不含影子数据通路）
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

用户 2026-11-22 裁定（`discussing.md`「M16 三方差分（Vast arch）批次裁定」）：

- QEMU 增加 `-machine kaiwu-vast,cache-model=off|on`，**默认 off**；off 保持现有直通（Linux/K0/inst 不变），on 只给 arch 测试。
- 完整影子写回 D-Cache 是后续任务；本任务先落**属性 + cfx5 寄存器面**，为影子通路与命令接线留稳定接口。
- **`cache-model` 只决定 cfx5 有没有效果，不决定它是否存在**（用户 2026-11-22 追加裁定；理由：Linux 内核缺省带 cache 维护逻辑，不能为「无 cache」单独编译内核）：off 下 `cache_exist` 读 0、寄存器面照常应答、命令 no-op；on 下 `cache_exist` = `0b11`。

## 要做

1. **`cache-model` 属性**：`hw/dadao/dadao-machine.c` 增加 QOM property，取值 `off|on`，默认 `off`；非法值启动报错（非零退出）。`on` 时记录到 machine 状态，供后续任务使用。
2. **cfx5 寄存器面**：
   - 两种模型下 cfx5 都**存在**（Vast；Tiny 无），只实现 cg8 寄存器面，其余 cg/rc 按 CACHE-04 报 `CFXREG`。
   - `off`（默认）：`cache_exist` 读 0；`cache_enable`/`cache_addr_start`/`cache_addr_size` 可读写（`exist=0` 的使能位无效果、读回 0）；`cache_ctrl` 合法编码**被接受但无效果**（不报 `CFXREG`），非法编码仍按契约报 `CFXREG`；不 panic。
   - `on`：`cache_exist` = `0b11`（I/D）；同样的寄存器面；命令暂不产生数据效果（留给影子 D-Cache 任务），但必须返回确定值、不 panic。
3. **契约对齐**：寄存器号/位域从 `m16-spec-001`（`spec/Kaiwu §3.2`、`.tao/contracts/contract-cache.md` 若存在）现场解析，不手写魔数；若契约缺失，先登记缺口再实现，不自行定义。
4. **不回归**：`off` 下现有 QEMU 测试（`check-arch-smoke`、K0 冒烟、`run_inst_tiny` 代表例）行为不变。

## 不做

- 不实现影子 D-Cache 数据通路（下件任务）；
- 不实现 cfx5 命令对 I/D cache 的实际维护效果（下件任务）；
- 不改 `spec/`/契约正文；不改 RTL/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`components/qemu/patches/**`）；
- 不改 `src/cpu/simple/**`；术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `off` 默认：cfx5 五个寄存器可访问——`cache_exist` 读 0、`enable`/`start`/`size` 可读写（`exist=0` 时 `enable` 读回 0）、`ctrl` 仅写（WO，读 ⇒ `CFXREG`）；`cache_ctrl` 合法编码接受且无效果、非法编码报 `CFXREG`；现有 `check-arch-smoke` 与一条 K0/inst 代表例 rc=0，与改前一致；
2. `on`：`cache_exist=0b11`；`enable`/`start`/`size` 可读写且回读一致，`ctrl` 为 WO（写合法编码不报异常、读 `ctrl` ⇒ `CFXREG`）；非法编码报 `CFXREG`；
3. `cache-model=bogus`：启动非零退出并给出可读错误；
4. **可达 FAIL**：注入「off 下 `cache_exist` 无视模型（读 `0b11`）」⇒ 判据红；注入「on 下 `cache_exist` 只置 I」⇒ 红；注入「off 下非法 `cache_ctrl` 被接受」⇒ 红；`cp`+md5 还原后回绿；
5. `check-patch-tree`（qemu 段 0 problem）、`check-index-blobs`、`make check-tasks` 记录 rc；
6. `--inject` ≥2 路。

## 完成区

**测试结果**：通过 **32/32**（`run.sh` rc=0：build 1 + 属性/启动 5 + cfx5 探针 21 + 回归 2 + 静态 3）；`run.sh --inject` rc=0 **51/51**（三路反例：off 的 `cache_exist` 无视模型 / on 的 `cache_exist` 只置 I / off 下非法 `cache_ctrl` 被接受；均判红→`cp`+md5 还原→回绿）。`integ042t` **25/25**（含 `cfx5_cache_noop`），并实测该例两路可达 FAIL（合法阶段注入非法编码 ⇒ exit 0x19；末尾非法改合法 ⇒ exit 0x7e，均判红后 md5 还原回绿）。`make check-arch` rc=2：**`integ042t` PASS**，余为改前基线已红的 `044t`/`045t`/`046t`（见遗留 ①）。
**修改文件**（8）：`components/qemu/patches/hw/dadao/dadao-machine.c.patch`、`patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/{changelog.md,README.md}`、`tools/testcases/arch/min_rom_probe_integ042t.py`（`cfx5_cache_cfxreg` → `cfx5_cache_noop`）、本任务书。
**验收结果**（真实 rc）：`make build-qemu` 0；`cache-model=bogus` rc=1（可读错误）、`kaiwu-tiny,cache-model=on` rc=1（CACHE-28）、`cache-model=on/off` 与默认均过属性解析；21 探针逐条 0（off：`exist` 读 0、`enable` 写无效、`start`/`size` 回读、27 种合法 `ctrl` 静默、非法 `ctrl` ⇒ `CFXREG`、`exist` 写/`ctrl` 读/保留 rc/cg0 ⇒ `CFXREG`；on：`exist=0b11`、`enable` 复位=exist、`start`/`size` 回读、合法 `ctrl` 静默、非法 ⇒ `CFXREG`）；`check-arch-smoke` 0；`run_inst_tiny --id ld.o_rrii_rd` 0；`check-index-blobs` 0；`make check-tasks` 0；`check-patch-tree` qemu 段 **0 problem**（69 补丁）；`check-component-changelog`/`dirs`/`no-residue`/`spec-refs`/`contracts-dir`/`knowledge-refs`/`manifests-guard` 均 0；`check-run-artifacts` rc=2（共享运行期日志目录既有命名问题，本任务命中 0）。
**新发现/坑**：① **off = cfx5 存在 + 合法 no-op / 非法 `CFXREG`**：编码校验放在 `cache_ctrl` 判序里（与模型无关），`cache_exist`/`enable` 才随模型；`off` 下 `exist=0` ⇒ `enable` 写无效（CACHE-07）。② cfx5 **只实现 cg8**，其余 cg（含共享 cg0-cg6 与 cg7）仍 `CFXREG`——否则 `044t`/`049t`/`050t` 的「cg0/cg7 ⇒ CFXREG」会变；这是只改 042t 就能保住其余探针的关键。③ `DadaoProfile.cache_cfx` 单独承载「Vast 有 cfx5 / Tiny 无」，与 `cfx_impl_mask`（同时驱动「未实现 cfx ⇒ CFXREG / 直通 ld-st 路径」）解耦。④ 042t 证据设计：合法阶段装「任何异常 ⇒ exit 0x19」的向量、非法阶段才装记 cause 的向量，否则「合法被拒」与「非法被收」共用同一 `cause_info`（同一指令编码）会互相掩盖（本轮实测到该假绿）。⑤ `check-arch` 的 `044t`/`045t`/`046t` 在**无 cfx5 的补丁基线**上逐条复现（A/B 记录在运行期证据目录）：044t 期望同步异常 6 次实为 5、045t 期望 escape 恢复 `cfxcode=0` 实为 3（`hmon_k0_vast.S` 注释即写"escape 不恢复 `inner_cfx_code`"）、046t kernel body 以 cfx0 读 cfx_pmem 触 `CFXPERM` 后 `dma_poll` 死循环 ⇒ 均与 cache 无关。
**遗留问题**：① **`check-arch` 未全绿（非本任务引入）**：`044t cfxreg_badcombo`、`045t trap_vector_roundtrip`、`046t`（6/16）在改前基线 `5d8778e` 上同样红；修它们要改 `tools/testcases/arch/*.py`（超出本任务授权文件）且 046t 涉及 kernel body 的 cfx/掩码约定，**需另立测试修复任务或由 architect/user 裁定验收面**。② `on` 的"真维护"属影子 D-Cache 任务；本任务 on/off 均无数据效果。③ 契约 CACHE-27 尚缺 `cache-model` 维度（`m16-spec-002` 负责）；`cache_addr_start` 的 56 位口径按其结论执行。④ cfx5 两轴掩码沿用通用行（默认仅 hmon）：Linux 内核若要从 supv/cfx0 做 cache 维护，需固件打开 cfx5 的 supv 行与 cg8 委托（`tests/ee-vast/hmon_k0_vast.S` 现只开已实现 cfx）——待裁/后续任务。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`cfx_idx` 运行期门控与既有「未实现 cfx ⇒ CFXREG」路径的互斥性、`cfx_reg_ptr` 未被绕过的理由、`cache_ctrl` 判序（CACHE-11）与两处无条件 no-op、`cache_enable` 复位/掩码、`addr_start` 的 `PA[55:0]` 截断、QOM 属性默认值与非法值路径、复位与 machine 初始化的先后、`-d cpu` 行数变化对既有探针的影响、证据脚本每条断言的可达 FAIL 与还原纪律。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 探针 `_cfxreg_case` 写路径把值固定成 0 ⇒ 两条 `cache_ctrl` 非法编码用例落成合法 no-op、假绿 | ✅已修 | 加 `value` 参数并按 CACHE-14 传 `sel=11 op=clean range=11` / `range=10 且 size=0` | 两例 `probe: PASS … rc=0`（此前 `exit expected 0x00 actual 0x7e`） |
| F2 探针解析 `-d cpu` 用 `^RD\[05\]` 锚行首，实际每行 4 个寄存器 ⇒ 观测恒 `None`，断言无意义 | ✅已修 | 去掉行首锚（与既有探针 `lasthex` 同法） | `off_read_exist_cfxreg` 由 FAIL（`cause_id … None`）转 PASS |
| F3 `DADAO_CACHE_*` 位域常量插在 `DADAO_CFXHA_PTW` 与 `HART` 之间，割裂 cfxha 列表 | ✅已修 | 移到 `PTW/HART/PMEM/TIME` 列表之后 | 重新编译 0 warning 相关项；`check-patch-tree` qemu 段 0 |
| F4 `run.sh` 注入备份 `cp` 目标父目录未建 ⇒ 注入第一步即失败 | ✅已修 | `mkdir -p "$BK/$(dirname "$rel")"` | `--inject` 两路 `non-empty injection` 均 PASS |
| F5 任务书「四个寄存器可读写」与 CACHE-03「`cache_ctrl` WO」冲突 | ❌不修（按契约实现，登记待裁） | 无（只记录） | `on_ctrl_read_cfxreg` 断言读 rc9 ⇒ `CFXREG`，真实 PASS；`on_ctrl_legal_no_trap` 证明写合法编码不报异常 |
| F6 `-d cpu` 新增 CFX05 行使既有探针输出变化（疑似回归） | ✅已验证（非缺陷） | 无 | `check-arch-smoke` rc=0；`integ046t` 在改前构建上同样 TIMEOUT（A/B）⇒ 与本行无关 |
| F7 `run.sh` 的 `prop_default` 用 `$?` 当 rc 显示（`if` 之后恒为 0） | ✅已修 | 固定为 1 并在 detail 打真实输出 | 重跑 `run.sh` 该行 PASS 且无 rc 误报 |
| F8 `cache-model=on` 在 Tiny 上若被静默接受，会承诺不存在的 cfx5 | ✅已修 | 属性 setter 按 `dc->profile != &dadao_profile_vast` 报错 | `-M kaiwu-tiny,cache-model=on` rc=1 且含 `CACHE-28` |

**约束核验**：worktree `git status -uall` = 6 改（4 补丁 + changelog + README）+ 本任务书；组件源码树（`.work/source/**`）干净且 `base..HEAD` 恰 1 commit；未改 `src/cpu/simple/**`、`spec/`、契约正文、RTL/gem5；未升任何版本号；未提交 git；术语「寄存器组」；本记录与完成区均无运行期具体路径。
**判决**：**待验收**（F1–F4、F7、F8 已修，F5 登记待裁，F6 已证非缺陷）。

### 第 1 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`）**：`./run.sh` rc=0 → `checks: PASS=23 FAIL=0 (cases=12, qemu_patches=69)`、`RESULT: PASS`；`./run.sh --inject` rc=0 → `checks: PASS=36 FAIL=0`、`RESULT: PASS`（两路反例 md5 变更 → 判据红 → `cp` 还原 md5 相等 → 回绿），与完成区数字逐字一致。
**逐项 rc（reviewer 自跑）**：`check-arch-smoke` 0；`run_inst_tiny --id ld.o_rrii_rd` 0（`检查点 21 / rc {'qemu': 0}`）；`check-index-blobs` 0；`make check-tasks` 0；`check-patch-tree` qemu 69 patch、0 problem（整跑 rc=1 由 gem5/chipyard/musl 在途 problem）；`check-component-changelog`/`check-dirs`/`check-no-residue`/`check-spec-refs`/`check-contracts-dir`/`check-knowledge-refs`/`check-manifests-guard` 均 0；`check-run-artifacts` rc=2（546 条全在共享日志目录，`m16-qemu-001` 命中 0）。
**启动契约手工复核**：`kaiwu-tiny,cache-model=on` rc=1 `cache-model=on is Kaiwu-Vast only … CACHE-28`；`kaiwu-vast,cache-model=bogus` rc=1 `invalid cache-model 'bogus' (expected off|on)`；`cache-model=on` 达装载期（`-kernel test.bin is required`）。

**契约口径（现场核对）**：`contract-cache` CACHE-03 写明 `cfx_cache_ctrl = cg8 rc9（WO、写即执行）`，`SimRISC-11` 的 `cfx2rd`/`cfx2rc` 规定「读写权限不匹配 ⇒ `CFXREG`」⇒ **读 rc9 ⇒ `CFXREG` 正确，实现符合契约**；probe `on_ctrl_read_cfxreg` reviewer 实跑 rc=0。**任务书验证 2「四个寄存器可读写」与契约冲突 ⇒ 任务书应订正**（architect 收尾改；engineer 按契约实现并登记待裁是正确处置，不构成返工）。
**off 口径**：任务书背景称「裁定」，但 `discussing.md` 同一条仍标 **待裁**；且既有 `integ042t cfx5_cache_cfxreg` 断言 cfx5 `cg8 rc0` 读 ⇒ `CFXREG`（reviewer 跑的 check-arch 该例 PASS）⇒「`cache_exist` 读 0」**无可观测路径、与既有门控互斥**。现实现（off 下任意 rc ⇒ `CFXREG`，`exist=0` 仅内部状态）与用户裁定的「`CFXREG` 一半」一致；**需 architect/user 明确：补可观测路径或改口径，并同步订正任务书与 `discussing.md`**。

**TIMEOUT A/B（独立重建，不采信完成区）**：改前补丁内容与 `5d8778e` 树逐文件比对一致 → 独立构建 baseline：`integ046t` 全量 **6/16 rc=1**；当前二进制全量 **6/16 rc=1**；失败集合**同名 10 条逐条相同**（仅 `va_pa_both_ways` 观测 rc `None` vs `1`，两支皆红）；`chain_basic` 单例 baseline 60 s TIMEOUT rc=1、当前 68 s TIMEOUT rc=1 ⇒ **预存成立、非本任务回归**。注：完成区「唯一失败 `chain_basic` TIMEOUT」不准确（该探针实为 6/16、10 例 TIMEOUT）。

**独立注入（`cp`+md5，未用 `git checkout/restore/stash`）**：
- 路 A `helper.c` 让 rc9 可读（违 CACHE-03 WO）：md5 `3d9b604d→d9469c0c` → `run.sh` rc=1、`[FAIL] probe on_ctrl_read_cfxreg`（21/23）→ `cp` 还原 md5 `3d9b604d` 相等 → `run.sh` rc=0（23/23）。
- 路 C `cpu.c` 复位 `cache_enable` 不取 `cache_exist`（违 CACHE-07）：md5 `33c8827d→aaf81a17` → `run.sh` rc=1、`[FAIL] probe on_exist_and_enable_reset`（21/23）→ `cp` 还原 md5 `33c8827d` 相等 → `run.sh` rc=0（23/23）。
- 附带：一次误注入「只改写侧掩码」时目标探针仍绿，但 `check-patch-tree` 判 `qemu_problems=2` 红 ⇒ 该断言非恒真、探针读侧掩码独立。

**约束核验**：`git status -uall` = 4 补丁 + `README.md` + `changelog.md` + 本任务书（7 项，与完成区一致，验收前后快照逐行相同）；源树 `git status` 空、`base..HEAD` 恒 1 commit；未改 `src/cpu/simple/**`、`spec/`、契约正文、版本号；未提交 git；本记录无运行期路径；术语「寄存器组」。

**findings（均不阻断本任务实现）**：F1 任务书验证 2 与 CACHE-03 WO 冲突 → architect 订正；F2 任务书「裁定」与 `discussing.md`「待裁」不一致且 `cache_exist=0` 不可观测 → 用户/architect 裁定；F3 完成区 TIMEOUT 描述不精确（6/16、10 例）；F4 完成区把 `check-patch-tree` 整跑 rc=1 只归因 musl/chipyard，实际还含 gem5（在途）；F5 CACHE-27 未含 `cache-model` 维度，默认 off 的 Vast 字面不符 → 需契约变更流程（用户认可）；F6 cfx5 两轴权限沿用通用行（仅 hypv 可访问），契约未规定 → 已披露。

**判决：Accepted**（重跑 23/23、`--inject` 36/36、两路独立注入红→绿、A/B 证实 TIMEOUT 预存、补丁与源树一致；F1/F2/F5 属任务书/契约层，须 architect 收尾处置）。

### 第 2 轮 engineer 返工（用户 2026-11-22 追加裁定：off = 存在但合法 no-op）

**落点**：`cfx_idx()` 不再按 `cache-model` 隐藏 cfx5（Vast 两种模型都存在，Tiny 无，由 `DadaoProfile.cache_cfx` 决定）；cfx5 只实现 cg8（其余 cg ⇒ `CFXREG`）；`cache_exist` 随模型（`off`=0 / `on`=0b11），`cache_enable` 的位效果随 `exist`；`cache_addr_start`/`cache_addr_size` 两种模型都可读写；`cache_ctrl` **判序与模型无关**——合法编码接受且无效果，`[3:2]=11` 或「PA 区间且 `size=0`」仍 `CFXREG`（CACHE-08/14）；`min_rom_probe_integ042t.py` 的 `cfx5_cache_cfxreg` 改为 `cfx5_cache_noop`（合法 no-op + 非法 `CFXREG` 两条都验，不是全删）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 042t 新例把 `addr_size` 写到 rc10（`addr_start`）⇒ `size` 恒 0、合法「PA 区间」被误判非法，且末尾非法与合法写同编码 ⇒ 假绿 | ✅已修 | 写 `rc11`；并改为两阶段向量（合法阶段任何异常 ⇒ exit 0x19） | `off_ctrl_legal_no_trap` 等 4 例加 `rd10==0` 断言后仍 PASS；042t `25/25` |
| F2 042t 单阶段处理器无法区分「合法被拒」与「非法被收」（同一 `cause_info`） | ✅已修 | 合法阶段向量 = `exit_seq(0x19)`；非法阶段才装记 cause 的处理器；断言 `rd10=CFXREG`、`rd11` = 该指令字 | 注入 A（合法循环写非法编码）⇒ `exit 0x19` 判红；注入 B（末尾非法改合法）⇒ `exit 0x7e` 判红；`cp`+md5 还原后 PASS |
| F3 证据探针的「合法 no-op / 跳过校验」用例只断言 `exit=0`，装的处理器会把异常吞成绿 | ✅已修 | 两类用例加 `rd10 == 0`（处理器只在异常时写 rd10） | `off_ctrl_legal_no_trap`/`off_ctrl_noop_skips_checks`/`on_*` 四例 PASS |
| F4 `DADAO_CACHE_ENABLE_MASK` 在改为 `dadao_cache_exist()` 掩码后无引用 | ✅已修 | 删除该死宏（`cpu.h`） | `make build-qemu` 0；`grep` 0 命中 |
| F5 `check-arch` 红（044t/045t/046t）疑似本轮引入 | ❌不修（外部预存，登记待裁） | 无（只留证据） | 用**无 cfx5** 的补丁基线 `5d8778e` 独立构建复现同三条：044t `syncn 6→5`、045t `cfxcode 0→3`、046t `6/16`；md5 `a2f0da74…` |
| F6 `off` 下 `cache_enable` 写入是否保留数值（只是读 0） | ❌不修（按 CACHE-07 实现） | `exist=0` 的位写无效、读 0 | `off_enable_ignores_writes`（写全 1 回读 0）PASS |

**约束核验**：`git status -uall` = 4 补丁 + `README.md` + `changelog.md` + `min_rom_probe_integ042t.py` + 本任务书（8 项）；组件源码树（`.work/source/**`）干净且 `base..HEAD` 恰 1 commit；未改 `src/cpu/simple/**`、`spec/`、契约正文、版本号、RTL/gem5；未提交 git；本记录无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（F1–F4 已修；F5 为外部预存、F6 为契约既定，均记录待裁）。

### 第 2 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，reviewer 亲自执行、不采信完成区）**：`./run.sh` rc=**0** → `checks: PASS=32 FAIL=0 (cases=21, qemu_patches=69)`、`RESULT: PASS`；`./run.sh --inject` rc=**0** → `checks: PASS=51 FAIL=0`、`RESULT: PASS`（三路反例 md5 变更 → 判据红 → `cp` 还原 md5 相等 → 回绿，末尾源树 `git status` 0 项）；注入收尾后再跑 `./run.sh` rc=**0** 32/32。与完成区 32/32、51/51 逐字一致。

**off/on 语义（补丁代码 + 探针双核）**：`cfx_idx()` 只按 `DadaoProfile.cache_cfx`（Vast=true / Tiny=false）放行 cfx5，与 `cache_model_on` 无关 ⇒ 两模型都存在；`dadao_cache_exist = cache_model_on ? 0b11 : 0`；`cache_enable` 读写均按 exist 掩码、复位 = exist（CACHE-07）；`addr_start/size` 两模型 RW；`dadao_cache_ctrl_exec` 判序与模型无关：`sel=00`/`op=none` 无条件 no-op → `[3:2]=11` → `PA 区间且 size=0` ⇒ `CFXREG`（CACHE-11/12/13/14）；cfx5 仅 cg8，其余 cg ⇒ `CFXREG`；读 `ctrl`、写 `exist` ⇒ `CFXREG`（WO/RO）。探针实跑：off `exist=0`、`enable` 写无效回读 0、`start/size` 回读、合法 **27 种**（clean/invalidate/flush × all/单行/区间 × I/D/双）静默、`sel=00`/`op=none` 跳过校验特例、非法 `[3:2]=11` 与 `span&size=0` ⇒ `CFXREG`；on `exist=0b11`、`enable` 复位/掩码回读、同 27 种静默、非法 ⇒ `CFXREG`。probe 27 种 ∪ 042t 36 种（3×4×3 含 `op=none`）= 全合法网格，无漏项。

**integ042t 两阶段向量（两个方向都能抓）**：合法阶段 handler = `exit_seq(0x19)`（0x980 槽），非法阶段才换记 cause 的 handler、末尾 fallthrough `0x7e`；reviewer 产品侧注入实测：合法被拒 ⇒ `exit 0x19`、非法被收 ⇒ `exit 0x7e`（正常路径 `rd10=0x4`、`rd11=指令字`）⇒ 两方向退出码互异、不共用 `cause_info` 掩盖；我方 `check-arch` 内 `integ042t` **25/25**（含 `cfx5_cache_noop`）。

**check-arch 基线判定（独立重建，不采信完成区）**：我方 `make check-arch` rc=**2**，红恰 3 条——044t `cfxreg_badcombo syncn:3 exp=0x6 got=0x5`、045t `trap_vector_roundtrip cfxcode exp=0x0 got=0x3`、046t **6/16**，其余探针全绿。独立复制源树到临时目录 checkout **`5d8778e`**（无 cfx5 改动）、`make build-qemu` rc=0（基线二进制 md5 `bce65d32…` vs 当前 `23a47052…`），同一套探针脚本打两支：044t/045t 输出**逐字节 diff 为空**、046t PASS/FAIL 集合**同名 10 条逐条相同**（均 6/16）⇒ 三条红在基线独立复现，判预存、非本任务回归。

**补丁核验**：`python3 tools/infra/make_patch.py qemu` rc=0 重写 69 份后，4 份改动补丁 md5 与跑前**相同**（`git status` 仍 8 项）⇒ 幂等且与源树一致；`check-patch-tree` qemu 段 **0 problem / 69 patch**（run.sh 内）。

**不回归**：`check-arch-smoke` rc=0、`run_inst_tiny --id ld.o_rrii_rd` rc=0（均在 run.sh 内）；Tiny 无 cfx5 = 代码层 `cache_cfx=false ⇒ cfx_idx→-1 ⇒ CFXREG` + 属性层 `-M kaiwu-tiny,cache-model=on` rc=1 `CACHE-28`（run.sh 内）+ `run_inst_tiny` 绿；`check-component-changelog`/`check-dirs`/`check-no-residue`/`check-spec-refs` 均 rc=0。

**独立注入 ≥2 路（`cp`+md5，全程未用 `git checkout/restore/stash`；逐路红→还原→回绿，合计 17/17 OK）**：路1 `cpu.h` off `exist` 无视模型 `adbde67b→d45f1fbc` ⇒ `off_exist_zero` FAIL（`rd5 expected 0x0 actual 0x3`）→ 还原 md5 相等 → 回绿；路2 `helper.c` 非法 `[3:2]=11` 被接受 `13aa50ed→eebd74f4` ⇒ `off_ctrl_reserved_range_cfxreg` FAIL（exit `0x7e`）**且** `042t cfx5_cache_noop` FAIL（exit `0x7e`）→ 还原回绿；路3 `helper.c` 合法编码被拒 `13aa50ed→3c28cc98` ⇒ `off_ctrl_legal_no_trap` FAIL（timeout）**且** `042t` FAIL（exit `0x19`）→ 还原回绿。收尾源树 `git status` 0 项、HEAD `8f974df`。

**约束核验**：验收前后 `git status -uall` 均为同一 8 项（4 补丁 + README + changelog + 042t + 本任务书）逐行相同，5 个目标文件 md5 前后相同；组件源树干净；未改 `src/cpu/simple/**`、`spec/`、契约正文、版本号、RTL/gem5；未提交 git；本记录不含运行期具体路径；术语「寄存器组」。

**findings（均不阻断）**：F1 `changelog.md` 称 042t「27 种合法编码」实为 **36**（3×4×3 含 `op=none`；27 是 run.sh 探针数）——文档数字笔误，architect 收尾改；F2 任务书验证 1「cfx5 寄存器访问不报 CFXREG」与 `ctrl` WO/`exist` RO ⇒ `CFXREG` 字面冲突（第 1 轮 F1 同源，architect 订正）；F3 `discussing.md`「M16 三方差分」cache 段仍写 off 口径「**待裁**：命令报 `CFXREG`」，与本轮「合法 no-op」裁定不一致 ⇒ architect 同步记录裁定出处；F4 无 Tiny `cfx5` 寄存器行为探针（CACHE-28 仅代码+属性层核实）⇒ 建议后续补；F5 `probe.py` 残留死函数 `case_off_read_exist`/`case_off_write_enable` 引用未定义 `_off_access`（未注册 `CASES`，不可达）。

**判决：Accepted**（`run.sh` 32/32、`--inject` 51/51、三路独立注入红→还原→回绿、042t 两阶段双向可达 FAIL、基线 A/B 证实三条红预存、补丁幂等且 qemu 段 0 problem、回归全绿；F1–F5 属文档/测试面，交 architect 收尾处置）。
