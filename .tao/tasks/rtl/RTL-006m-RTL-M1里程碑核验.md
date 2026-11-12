# RTL-006m: RTL-M1 里程碑核验

**模块**：rtl
**项目里程碑**：RTL-M1
**状态**：里程碑
**目标**：核验 `RTL-001k` 到 `RTL-005t` 所建立的 DADAO Chisel generator、Tile、Config、最小 elaborator、CHIRRTL/SystemVerilog 生成和反例门控；确认版本、补丁集、产物和工作树状态一致后，决定是否将 RTL-M1 置为 `里程碑`。
**关联任务**：`RTL-001k`、`RTL-002t`、`RTL-003t`、`RTL-004t`、`RTL-005t`

## 背景

RTL-M1 的目标是证明 Chipyard 1.14.0 上的 DADAO 基础集成链路可用：

```text
rtl/dadao 权威源码
    -> Chipyard overlay/patch series
    -> DADAO generator
    -> DADAO Tile/Config
    -> DADAO elaborator
    -> DADAOTop.fir
    -> firtool 1.75.0
    -> DADAOTop.sv
    -> 结构和反例门控
```

`RTL-002t` 到 `RTL-005t` 已分别形成实现和验证证据，但 RTL-M1
尚未完成跨任务核验；正式锁文件、默认环境值、`RTL-001k` 和 ADR-0012
的当前基线说明已于 2026-10-12 统一到 Chipyard 1.14.0。ADR-0012 的
原始 1.11.0 决策仅作为历史审计文本保留。

本任务只做核验和一致性判断，不实现单周期 Core、TileLink、RAM、
BootROM、UART 或 Exit。

## 冻结输入

| 项目 | 冻结值 |
|---|---|
| 规范 | SimRISC 0.5.3 |
| Chipyard | `1.14.0` |
| Chipyard commit | `0acc1e1de2d3284bcd4d876956932a013ffe1949` |
| Chisel | `6.7.0` |
| Scala | `2.13.16` |
| sbt 构建启动版本 | `1.8.2` |
| firtool | `1.75.0` |
| Clab Chipyard 工作树 | `/home/ubuntu/user_doc/chipyard/1.14.0/.work/source/chipyard` |
| Clab DADAO-v5 工作树 | `/home/ubuntu/user_doc/dadao_doc` |
| RTL 权威源码 | `rtl/dadao` |
| Chipyard 补丁集 | `components/chipyard/series` 和 `components/chipyard/patches/` |
| 架构依据 | ADR-0012、ADR-0013、ADR-0014 |
| 补丁规则 | `docs/spec/component-patching.md` |

### 版本一致性边界

当前状态：

- `manifests/rtl.lock.toml` 已由用户授权切换到 Chipyard `1.14.0` 和
  commit `0acc1e1de2d3284bcd4d876956932a013ffe1949`；
- `tools/rtl/clab-env.sh` 默认 `CHIPYARD_VERSION` 已切换为 `1.14.0`；
- ADR-0012 的 D1/D2 原始历史文本保留 `1.11.0`，但已明确标注当前值由
  ADR-0014 取代；
- `RTL-001k` 的当前任务输入已修订为 `1.14.0`；
- ADR-0014 已 `Accepted`，本次只完成用户授权的锁文件和默认值切换，不自动
  执行 1.11.0 删除或历史 ADR 改写。

本任务必须核验锁文件、默认值和实际源码树三者一致，不得把剩余历史文档
引用误报为当前运行基线。

## 执行变量与一次性工作树

执行核验前定义以下路径：

```bash
DADAO_REPO=/home/ubuntu/user_doc/dadao_doc
FORMAL_CHIPYARD=/home/ubuntu/user_doc/chipyard/1.14.0/.work/source/chipyard
SOURCE_TREE=/home/ubuntu/user_doc/chipyard/1.14.0/.work/tmp/RTL-006m-copy-20261012
OUTPUT_DIR=/home/ubuntu/user_doc/chipyard/1.14.0/.work/build/dadao/rtl-006m
CHIPYARD_SOURCE="$SOURCE_TREE"
```

路径职责：

- `DADAO_REPO`：DADAO-v5 工作树；
- `FORMAL_CHIPYARD`：正式、干净、只作为复制来源；
- `SOURCE_TREE`：一次性补丁工作树；
- `OUTPUT_DIR`：核验产物和日志；
- `CHIPYARD_SOURCE`：RTL 脚本读取的一次性源码根。

准备步骤：

1. 检查 `FORMAL_CHIPYARD` 的 `HEAD` 精确等于冻结 commit，且
   `git status --short --untracked-files=all` 为空。
2. 检查 `SOURCE_TREE` 不存在；若已存在，不静默覆盖或删除，先报告并
   请求用户确认。
3. 使用普通本地复制创建一次性工作树，不在此时重新 clone（克隆）：

   ```bash
   cp -a "$FORMAL_CHIPYARD" "$SOURCE_TREE"
   ```

4. 在副本上应用树形补丁：

   ```bash
   cd "$DADAO_REPO"
   CHIPYARD_SOURCE="$SOURCE_TREE" \
     bash tools/rtl/chipyard_patch.sh apply "$SOURCE_TREE"
   CHIPYARD_SOURCE="$SOURCE_TREE" \
     python3 tools/rtl/check_chipyard_patch.py --source "$SOURCE_TREE"
   ```

5. 确认补丁后的 tree hash 为
   `5bbecfd3384613c4fbdcea0f2d10be8fcf3c15a5`。
6. 所有 smoke、elaboration 和 Verilog 生成只使用 `SOURCE_TREE`；不得
   在 `FORMAL_CHIPYARD` 上应用 DADAO 补丁。
7. 核验完成后，清理 `SOURCE_TREE` 是否执行必须再次获得用户确认。

普通复制不重新下载 Git 历史，不递归下载 submodule，也不改变正式工作树。

## 术语说明

- **milestone**：里程碑，满足一整组前置任务和退出条件后才能置为完成。
- **elaboration**：Chisel 展开参数化设计并生成中间表示的过程。
- **CHIRRTL**：Chisel 6 的中间 FIRRTL 方言。
- **firtool**：把 CHIRRTL/FIRRTL 编译为 SystemVerilog 的 CIRCT 工具。
- **tree hash**：把 Git 索引中的完整目录树内容压缩后的哈希指纹。
- **fail-closed**：缺少证据或检查条件不满足时必须返回非零，不能默认 PASS。
- **反例门控**：故意注入错误，证明检查器不是只会报告成功。

## 核验内容

### 1. 前置任务和文件存在性

核验以下任务状态均为 `已验证`：

```text
RTL-001k
RTL-002t
RTL-003t
RTL-004t
RTL-005t
```

核验以下文件存在且非空：

```text
rtl/dadao/build.sbt
rtl/dadao/project/build.properties
rtl/dadao/src/main/scala/dadao/DADAOParams.scala
rtl/dadao/src/main/scala/dadao/DADAOMemPort.scala
rtl/dadao/src/main/scala/dadao/DADAOCore.scala
rtl/dadao/src/main/scala/dadao/DADAOTile.scala
rtl/dadao/src/main/scala/dadao/DADAOConfig.scala
rtl/dadao/src/main/scala/dadao/DADAOElaborator.scala
components/chipyard/README.md
components/chipyard/changelog.md
components/chipyard/series
tools/rtl/build_dadao_verilog.py
tools/rtl/check_dadao_verilog.py
tools/rtl/check_dadao_verilog_negative.sh
tests/rtl/smoke/RTL-004t-elaboration-probe.sh
tests/rtl/smoke/RTL-005t-verilog-probe.sh
```

### 2. 独立 RTL 树检查

在 DADAO-v5 仓库中执行：

```bash
python3 tools/rtl/check_rtl_tree.py
bash tools/rtl/check_rtl_tree_negative.sh
```

要求：

- 正常检查退出码为 `0`；
- 注入错误后退出码为非零；
- 检查器必须读取真实源码，不得只在文件不存在时失败；
- 脚本输出和真实退出码写入正式日志。

### 3. Chipyard 补丁集检查

在 Clab 的 Chipyard `1.14.0` 工作树上执行：

```bash
python3 tools/rtl/check_chipyard_patch.py \
  --source "$CHIPYARD_SOURCE"

bash tools/rtl/check_chipyard_patch_negative.sh
```

要求：

- 补丁集只包含一文件一补丁；
- `series` 与补丁树双向一致；
- 补丁从冻结 commit 干净应用；
- 应用后的权威 Scala 文件与 `rtl/dadao` 逐字节一致；
- 反例脚本对删除、篡改、重复、错误 commit 和 submodule drift 真实失败；
- 最终 tree hash 与任务书和日志一致；
- 不修改 Chipyard submodule gitlink。

### 4. 最小 elaboration

重新从补丁集创建或验证独立工作树，不依赖已被删除的临时副本。

执行：

```bash
CHIPYARD_SOURCE="$SOURCE_TREE" \
  bash tests/rtl/smoke/RTL-004t-elaboration-probe.sh "$OUTPUT_DIR/DADAOTop.fir"
```

要求：

- `DADAOConfig attached 1 tile(s)`；
- `DADAOTop.fir` 非空；
- 包含 `circuit DADAOTop`；
- 包含 `module DADAOTile`；
- 包含 `module DADAOCore`；
- 包含 `inst dadao of DADAOTile`；
- 失败时返回非零。

### 5. Verilog 生成和反例门控

执行：

```bash
bash tests/rtl/smoke/RTL-005t-verilog-probe.sh "$SOURCE_TREE" "$OUTPUT_DIR"
bash tools/rtl/check_dadao_verilog_negative.sh
```

要求：

- firtool 实际版本精确为 `1.75.0`；
- `DADAOTop.fir` 和 `DADAOTop.sv` 非空；
- checker 按模块体检查 `module ... endmodule` 和父子实例关系；
- 23 类反例全部返回非零并命中预期原因；
- 最终恢复构建通过；
- smoke、build、negative 日志最后记录真实 `EXIT=0`；
- FIR/SV SHA-256 与任务书一致；
- 不得修改正式 Chipyard 工作树来恢复测试。

### 6. 版本和文档一致性核验

逐项比较：

```text
ADR-0012
ADR-0014
manifests/rtl.lock.toml
tools/rtl/clab-env.sh
RTL-001k ~ RTL-005t
RTL-006m
```

必须明确记录：

1. `rtl.lock.toml` 和 `clab-env.sh` 已使用 1.14.0 实际值；
2. ADR-0012 和 `RTL-001k` 的当前基线与历史文本已清晰区分；
3. 是否存在会让用户误认为正式基线已切换的表述；
4. ADR-0012、ADR-0013、ADR-0014 和 `RTL-001k` 的修订记录是否完整；
5. 1.11.0 删除是否仍按 ADR-0014 D6/D7 单独确认。

本任务只报告差异，不自行修改正式锁文件。

### 7. 工作树和临时资源清理

核验结束后必须检查：

```bash
git -C "$CHIPYARD_SOURCE" status --short --untracked-files=all
git -C "$DADAO_REPO" status --short --untracked-files=all
df -h /home/ubuntu /tmp
```

要求：

- 正式 Chipyard 工作树无未解释变更；
- DADAO 仓库无 `target/`、`test_run_dir/` 或其他构建垃圾；
- 临时工作树只存在于预定义目录；
- 清理操作必须在用户确认后执行；
- 不把临时目录当作可提交产物。

## 反例与失败处理

每个用于验收的脚本必须至少证明以下情况会使检查失败：

- 缺少 `DADAOTile` 或 `DADAOCore`；
- 缺少 `endmodule`；
- 实例位于错误模块或模块外；
- 注释伪造模块或实例；
- firtool 版本错误；
- CHIRRTL/Verilog 为空；
- 版本文件缺失或错配；
- Chipyard commit、tree hash 或补丁集错误；
- 应用后源码与 `rtl/dadao` 不一致。

不得以“脚本没有输出”或“任意非零退出码”替代预期错误原因。

## 验收标准

1. `RTL-001k` 到 `RTL-005t` 全部为 `已验证`。
2. 所有 RTL-M1 交付文件和正式验证日志存在。
3. `check_rtl_tree` 通过，且反例脚本真实失败。
4. Chipyard 补丁集通过结构、干净应用、源码一致性和 tree hash 检查。
5. CHIRRTL elaboration 通过。
6. firtool `1.75.0` 生成 SystemVerilog 通过。
7. Verilog 结构检查和 23 类反例全部通过。
8. FIR/SV 大小、SHA-256 和日志退出码与任务书一致。
9. 正式 Chipyard 工作树干净，临时资源已按用户确认处置。
10. 锁文件、默认环境和实际源码树均为 1.14.0；历史文档引用已明确分类。
11. 无未处置的跨模块影响；否则 RTL-M1 不得置为 `里程碑`。
12. 核验结论、命令和真实输出逐条写入完成区。

## 完成判定

只有同时满足以下条件，才允许将 `RTL-006m` 置为 `里程碑`：

1. 本任务全部技术核验通过；
2. 版本和锁文件差异已有明确结论；
3. 用户确认锁文件、默认环境和历史文档引用的最终处置；
4. 所有未处置项均有阻断或 deferred 记录；
5. 不依赖临时工作树或未提交的本地状态。

## 交付物

```text
.tao/tasks/rtl/
└── RTL-006m-RTL-M1里程碑核验.md

20260929report/verification-logs/
├── RTL-006m-rtl-tree-check.log
├── RTL-006m-rtl-tree-negative.log
├── RTL-006m-chipyard-patch-apply.log
├── RTL-006m-chipyard-patch-check.log
├── RTL-006m-elaboration.log
├── RTL-006m-verilog-check.log
├── RTL-006m-verilog-negative.log
├── RTL-006m-firtool-version.log
├── RTL-006m-DADAOTop.fir
├── RTL-006m-DADAOTop.sv
└── RTL-006m-summary.log
```

若实际核验使用其他日志名，必须在任务书完成区说明原因，不得静默改变。

## 下发前预检

1. **任务书内部一致性**：PASS。目标、冻结输入、核验步骤、失败处理和验收
   标准均围绕 RTL-M1，不涉及 Core 指令语义。
2. **依赖链实际可用性**：CLAB-READY。RTL-002t 到 RTL-005t 已存在；
   Chipyard 1.14.0、firtool 1.75.0 和正式证据已可用。
3. **验收可执行性**：CLAB-READY。检查、反例、elaboration、Verilog 和
   工作树审计命令均可在 Clab 执行。
4. **与 spec/vectors 一致**：PASS。本任务只核验 RTL-M1 构建链，不生成
   ISA 编码、寄存器值或语义期望值。
5. **版本边界**：必须核验 `rtl.lock.toml`、`clab-env.sh` 和实际源码树
   已统一为 1.14.0；ADR-0012 和 `RTL-001k` 的历史文本另行分类，不能把
   历史说明误报为当前基线。

## 已知风险

1. ADR-0012 的历史 1.11.0 文本仍可能与当前状态混淆，必须依赖修订说明
   区分。
2. 重新创建 Chipyard 工作树时若复用旧的已修改副本，可能掩盖补丁应用问题。
3. 正式工作树和临时工作树的路径必须分开，不能让 smoke 修改正式源码树。
4. `fence`、TileLink、RAM、UART 和完整 ISA 语义不属于 RTL-M1 核验范围。
5. 若正式工作树或日志在核验后被手工修改，必须重新核验，不能沿用旧结论。

## 完成区

### 核验结果

核验结果：PASS。

```text
chipyard=1.14.0
chipyard_commit=0acc1e1de2d3284bcd4d876956932a013ffe1949
formal_worktree=clean
patch_tree_hash=5bbecfd3384613c4fbdcea0f2d10be8fcf3c15a5
rtl_tree_check=PASS
rtl_tree_negative=EXIT=0
patch_apply=EXIT=0
patch_check=PASS
elaboration=PASS
verilog_check=PASS
verilog_negative_cases=23
verilog_negative_restore=PASS
```

产物：

```text
fir_bytes=22176
sv_bytes=25757
fir_sha256=fc1b60b52a120e5143ac86c6672e3ba1decb7d56229c3265129a6791a455f2a0
sv_sha256=59fc1e17a036c72acd4397c27a516d3ca48c0bf4fdc11da270bf0f0d23b35faf
firtool=CIRCT firtool-1.75.0
```

### 版本差异

`manifests/rtl.lock.toml`、`tools/rtl/clab-env.sh` 和实际 Chipyard
工作树已统一为 `1.14.0`。ADR-0012 的原始 `1.11.0` 决策和 ADR-0014
的升级/删除流程仍作为历史审计文本保留；`versions.txt` 明确标注为历史
安装记录，不作为当前运行基线。

### 独立复验

1. 第一轮 reviewer（独立审查者）结论为 `Needs Revision`：
   - firtool 版本日志缺少真实退出码；
   - `RTL-006m-*.log` 未获得 Git 忽略例外；
   - ADR-0014 仍有一处 1.11.0 的“当前基线”措辞。
2. 上述问题已修复并重新生成证据。
3. 第二轮 reviewer 结论为 `Accepted`，无阻塞 finding。

### 剩余事项

- 用户已于 2026-10-13 确认将 `RTL-006m` 置为 `里程碑`；
- 清理一次性副本必须先获得用户确认；
- Git 提交和推送必须另行获得用户确认。

### 最终结论

`RTL-M1` 已完成：DADAO generator、Tile、Config、最小 elaborator、
CHIRRTL、firtool `1.75.0` SystemVerilog 生成和 23 类反例门控均已通过；
正式锁文件、默认环境和实际构建源码树统一为 Chipyard `1.14.0`。

## 参考

- `.tao/tasks/rtl/RTL-001k-模块启动与任务分解.md`
- `.tao/tasks/rtl/RTL-002t-RTL源码与独立Chisel骨架.md`
- `.tao/tasks/rtl/RTL-003t-Chipyard覆盖层与树形补丁集.md`
- `.tao/tasks/rtl/RTL-004t-Tile与Config及最小elaborator.md`
- `.tao/tasks/rtl/RTL-005t-Verilog生成与反例门控.md`
- `.tao/knowledge/adr-0012-chipyard-single-cycle-soc.md`
- `.tao/knowledge/adr-0013-clab-rtl-environment.md`
- `.tao/knowledge/adr-0014-chipyard-1.14-upgrade.md`
- `manifests/rtl.lock.toml`
- `docs/spec/component-patching.md`
