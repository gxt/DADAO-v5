<!-- 现场生成，勿手改 -->

# M14 K0 工具链缺口矩阵

- **生成时间**：2026-11-13 20:00:45 +0800（UTC 2026-11-13T12:00:45Z）
- **数据来源**：`tools/linux/toolchain_matrix.json`（format 1）+ 现场探针（本册由生成器按矩阵重跑探针后写出）
- **机器指纹**：CPU `AMD EPYC 7773X 64-Core Processor`；target `dadao-unknown-elf`；clang `clang version 23.1.3 (be79a1758026)`；llvm-mc `LLVM version 23.1.3`；工具版本摘要 md5 `80649bd8afe8`
- **复现**：`make check-linux-toolchain`（门控）；`python3 tools/linux/check_toolchain.py --report`（重新生成本册）；`python3 tools/linux/check_toolchain.py --inject`（自检）

## 1. 结论

- 8 行矩阵，8/8 行「声明 == 实测」。
- `gaps=6 (blockers=0)`：缺口行全部有**现场验证过**的规避法，对 K0 无阻塞。
- `required_for_k0` 共 2 行（asm-goto、inline-asm-constraints），全部 present/supported。
- 结论由 **DADAO target** 决定：能力探针一律带 `--target=dadao-unknown-elf`（汇编用 `-triple=dadao-unknown-elf`）；宿主 x86 上同类探针另见 §5 对照。

## 2. 矩阵

| 行 | 声明 | 实测 | exit | 规避法验证 | K0 影响 | 归属 |
| --- | --- | --- | --- | --- | --- | --- |
| `llvm-ar` | absent | absent | 127 | verified | none | `m14-linux-002` |
| `llvm-ranlib` | absent | absent | 127 | verified | none | `m14-linux-002` |
| `llvm-strip` | absent | absent | 127 | verified | none | `m14-linux-002` |
| `asm-goto` | supported | supported | 0 | n/a | none | `m14-linux-002` |
| `stack-protector` | unsupported | unsupported | 1 | verified | none | `m14-linux-002` |
| `data-directives` | unsupported | unsupported | 1 | verified | none | `m14-linux-002` |
| `inline-asm-constraints` | supported | supported | 0 | n/a | none | `m14-linux-002` |
| `mcmodel-kernel` | unsupported | unsupported | 1 | verified | none | `m14-linux-002` |

## 3. 逐行证据（现场输出摘要）

### `llvm-ar` — absent

- 探针：`<install-root>/bin/llvm-ar --version || <llvm-build>/bin/llvm-ar --version`
- 实测：absent（exit 127）；输出摘要：`llvm-ar 不在 install-root/bin 也不在 llvm-build/bin`
- 规避法：AR=/usr/bin/ar（GNU ar 2.42；归档格式与目标机无关，rcs/t 已在 DADAO 目标对象上验证）
- 规避法验证：verified（`ar rcs rc=0; ar t rc=0`）

### `llvm-ranlib` — absent

- 探针：`<install-root>/bin/llvm-ranlib --version || <llvm-build>/bin/llvm-ranlib --version`
- 实测：absent（exit 127）；输出摘要：`llvm-ranlib 不在 install-root/bin 也不在 llvm-build/bin`
- 规避法：RANLIB=/usr/bin/ranlib（GNU ranlib 2.42，索引已在 DADAO 目标 .a 上验证）
- 规避法验证：verified（`ar rcs rc=0; ranlib rc=0`）

### `llvm-strip` — absent

- 探针：`<install-root>/bin/llvm-strip --version || <llvm-build>/bin/llvm-strip --version`
- 实测：absent（exit 127）；输出摘要：`llvm-strip 不在 install-root/bin 也不在 llvm-build/bin`
- 规避法：STRIP=<install-root>/bin/llvm-objcopy（追加 --strip-all/--strip-debug；GNU strip 2.42 无法识别 DADAO ELF：EM 0xDA0 + 大端）
- 规避法验证：verified（`llvm-objcopy --strip-all rc=0; size 800 -> 312`）

### `asm-goto` — supported

- 探针：`clang --target=dadao-unknown-elf -fsyntax-only <src>; clang --target=dadao-unknown-elf -O1 -S <src>`
- 实测：supported（exit 0）；输出摘要：`-fsyntax-only rc=0; -O1 -S rc=0; 标签降级=yes`
- 规避法：不需要（能力已具备）

### `stack-protector` — unsupported

- 探针：`clang --target=dadao-unknown-elf -O1 -fstack-protector-strong -S <src>`
- 实测：unsupported（exit 1）；输出摘要：`-O1 -fstack-protector-strong -S rc=1; canary=no; error: unable to lower stackguard`
- 规避法：-fno-stack-protector（Kconfig 关栈保护；-mstack-protector-guard=* 同不支持）
- 规避法验证：verified（`-fno-stack-protector -S rc=0; canary=absent`）

### `data-directives` — unsupported

- 探针：`llvm-mc -triple=dadao-unknown-elf -filetype=obj <src.s>`
- 实测：unsupported（exit 1）；输出摘要：`llvm-mc -triple=dadao-unknown-elf rc=1; <tmp>/data_legacy.s:4:3: error: unsupported directive '.quad' (data directive outside the DADAO unique set: only '.dd.b08'/'.dd.w16'/'.dd.t32'/'.dd.o64' are accepted; spec/Toolcha…`
- 规避法：改写为 DADAO 唯一数据伪指令 .dd.o64/.dd.t32/.dd.w16/.dd.b08（spec/Toolchain-01 §7.1；clang codegen 亦只用该组）
- 规避法验证：verified（`.dd.* 段字节 1122334455667788aabbccddbeef5a (期望 1122334455667788aabbccddbeef5a)`）

### `inline-asm-constraints` — supported

- 探针：`clang --target=dadao-unknown-elf -O1 -S <src>（约束 r/i/m/=&r + memory clobber）`
- 实测：supported（exit 0）；输出摘要：`-O1 -S 约束 r/i/m/=&r/memory rc=0; 5 条约束全部编入`
- 规避法：不需要（能力已具备）

### `mcmodel-kernel` — unsupported

- 探针：`clang --target=dadao-unknown-elf -O1 -mcmodel=kernel -S <src>`
- 实测：unsupported（exit 1）；输出摘要：`-mcmodel=kernel rc=1; clang: error: unsupported code model 'kernel' for option '-mcmodel=' on target 'dadao-unknown-unknown-elf'; DADAO supports 'default' ('small' is an alias) and 'large'; clang: error: unsupported cod…`
- 规避法：-mcmodel=small（=default；内核基址 1 MiB 落在 REL26 ±32 MiB 内）；镜像 >32 MiB 时用 -mcmodel=large
- 规避法验证：verified（`-mcmodel=small -S rc=0`）

## 4. 可直接消费的工具选择（`m14-linux-002`）

`<install-root>` = `manifests/install-dirs.lock.toml` 的 `host_toolchain_dir`；内核 make 传变量时按下列来源：

- `CC=<install-root>/bin/clang --target=dadao-unknown-elf`（必须带 target；集成汇编器随 clang，`AS` 同源）
- `LD=<install-root>/bin/ld.lld`（现场链接 DADAO ELF 成功：Machine `0xDA0`、大端）
- `AR=/usr/bin/ar`（GNU ar；安装根/构建树均无 `llvm-ar`）
- `RANLIB=/usr/bin/ranlib`（GNU ranlib；均无 `llvm-ranlib`）
- `NM=<install-root>/bin/llvm-nm`（fallback `/usr/bin/nm`，现场可用）
- `OBJCOPY=<install-root>/bin/llvm-objcopy`
- `OBJDUMP=<install-root>/bin/llvm-objdump`
- `STRIP=<install-root>/bin/llvm-objcopy`（追加 `--strip-all` / `--strip-debug`；均无 `llvm-strip`，GNU strip 无法识别 DADAO ELF）
- 附加编译期开关：`-fno-stack-protector`、`-mcmodel=small`；手写汇编的数据伪指令用 `.dd.o64/.dd.t32/.dd.w16/.dd.b08`
- 不可用 `make LLVM=1`：该模式要求 `llvm-ar`/`llvm-strip`，二者缺失 ⇒ 逐变量覆盖上表。

## 5. 口径与反证

- 缺口头寸只有两态：`absent`（工具链二进制缺失）与 `unsupported`（target 拒绝该能力）；没有「未测」。
- `required_for_k0=true` = 必须原生具备、不允许替代的能力；`k0_impact=none` = 有现场验证过的规避法；`blocker` = 无规避法（K0 被阻塞）。
- 宿主 x86 对照：同一份源码用宿主 clang 编 `-fstack-protector-strong` rc=0、`-mcmodel=kernel` rc=0（宿主天然通过），而 DADAO target 分别 unsupported ⇒ 结论由 target 决定。
- 工具链或矩阵一旦变化，重跑 `--report` 重写本册；`--report --check` 逐字比对正文（「生成时间」「机器指纹」两行除外）⇒ 改了矩阵不重生成即 FAIL。

## 6. 复现命令

```
make check-linux-toolchain
python3 tools/linux/check_toolchain.py --report
python3 tools/linux/check_toolchain.py --report --check
python3 tools/linux/check_toolchain.py --inject
```
