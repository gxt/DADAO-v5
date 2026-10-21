# DADAO-v5 top-level orchestration.
#
# Make is the stable user interface (ADR-0002: .tao/adr/adr-0002-build-orchestration.md); the actual manifest/fetch/patch
# logic is delegated to Python standard-library scripts under tools/infra/. All
# disposable data lives under .work/ (gitignored); persistent upstream mirrors
# live under .cache/ and are never touched by clean-work.

PYTHON ?= python3

# Install/product directory paths — single source of truth from
# manifests/install-dirs.lock.toml via tools/infra/paths.py.
# These are absolute, realpath-resolved paths.  To change them, edit the
# manifest; do NOT hardcode paths here.
REPO_ROOT          := $(shell $(PYTHON) tools/infra/paths.py repo_root)
SDK_DIR            := $(shell $(PYTHON) tools/infra/paths.py sdk_dir)
HOST_TOOLCHAIN_DIR := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_dir)
HOST_TOOLCHAIN_BIN := $(shell $(PYTHON) tools/infra/paths.py host_toolchain_bin)
HOST_TOOLS_BIN     := $(shell $(PYTHON) tools/infra/paths.py host_tools_bin)
TARGET_SYSROOT_DIR := $(shell $(PYTHON) tools/infra/paths.py target_sysroot_dir)
TEST_ARTIFACTS_DIR := $(shell $(PYTHON) tools/infra/paths.py test_artifacts_dir)

# Non-empty guard: abort if any path variable is empty (manifest missing/corrupt).
_install_dir_vars = REPO_ROOT SDK_DIR HOST_TOOLCHAIN_DIR HOST_TOOLCHAIN_BIN HOST_TOOLS_BIN TARGET_SYSROOT_DIR TEST_ARTIFACTS_DIR
$(foreach v,$(_install_dir_vars),$(if $($v),,$(error $v is empty — check manifests/install-dirs.lock.toml and tools/infra/paths.py)))

# Component source/build trees (all under the disposable .work/ root). The
# llvm source is the monorepo checkout with its `llvm/` project subdirectory.
QEMU_SRC   ?= .work/source/qemu
QEMU_BUILD ?= .work/build/qemu
LLVM_SRC   ?= .work/source/llvm-project/llvm
LLVM_BUILD ?= .work/build/llvm
GEM5_SRC   ?= .work/source/gem5
GEM5_BUILD ?= .work/build/gem5

DOCKER_TAG ?= dadao-v5-dev:local

.DEFAULT_GOAL := help

.PHONY: help manifest-check doctor status fetch fetch-refs apply-series prepare \
        clean-work build-mc build-mc-lite build-mc-reconfig build-lld \
        build-builtins build-qemu build-qemu-reconfig build-gem5 build-bootrom build-picolibc \
        build-musl build-musl-shared test-picolibc-smoke install-host docker-image docker-shell check \
        check-picolibc-tests check-picolibc-tests-full \
        check-testcases-suites check-testcases-suites-full \
        check-modules check-full check-components check-qemu-smoke check-knowledge-refs \
        validate-vectors check-spec-refs check-spec-drift check-asm-list \
        check-legality-drift check-interface validate-encoding check-scope \
        check-rule-refs check-fp-contract check-instrinfo \
        check-dirs check-no-residue check-spec-readonly check-cfx-aliases check-asm-prose check-lit \
        check-lit-full \
        check-run-artifacts \
        test-codegen test-elf test-semihost test-m6 \
        check-patch-tree check-index-blobs check-source-state check-asm-list-drift size-report \
        check-musl-freshness check-builtins-freshness check-install-tools check-milestones-fresh \
        check-tasks check-spec-codeblocks check-legality-invariants \
        check-isa-coverage check-spec-numbering check-spec-changelog check-spec-archive check-contracts-dir \
        check-component-changelog check-syscall-abi

# ── 工作树互斥锁 (INFRA-099t / ISS-229) ─────────────────────────────────────────
# 同一工作树内会写共享状态的目标 —— 构建树 `.work/build/**`、安装根 $(SDK_DIR)、
# SDK 产物目录 $(TEST_ARTIFACTS_DIR) —— 以及跑这些写者的门控，全部**串行化**：
# `GATE_LOCKED_TARGETS` 里每个名字都是**门控目标**（目标体 + 其前置在
# `_locked-<name>`），由 tools/infra/gate_lock.py 在一个 flock(2) 上运行，锁文件
# = $(GATE_LOCK)。这是 `ISS-229` 的机械化：L2 与 L3 并发曾读到瞬态不完整的安装根
# ⇒ Embench 假 FAIL（`stddef.h not found`）；手动 `build-mc` 与 L2 内
# `install-host` 并发 ⇒ 构建树写坏。规范见 docs/Process-07 §2。
#
# 语义（细节 + 自测见 tools/infra/gate_lock.py）：
#   * **嵌套放行**：同一 make 树内 `check-modules → test-semihost → install-host →
#     build-mc` 通过 DADAO_GATE_LOCK_HELD 直接通过（并由「持有者 pid 是本进程祖先」
#     校验，环境标记本身不能关掉互斥），不会自锁。
#   * **独立进程等待有上界**：GATE_LOCK_WAIT 秒（默认 3600，够一次 L3 持有）；
#     超时打印「锁文件 + 持有者 pid/开始时间/目标/命令」，rc=75。
#   * **fail-fast**：`GATE_LOCK_FAILFAST=1` ⇒ 一次非阻塞尝试失败即 rc=75 + 提示。
#   * **锁不可用**（父目录不可写 / 无 flock(2)）⇒ rc=69 且**不运行**目标（不静默跳过）。
#   * 锁文件 `.dadao/gate.lock` 在 .gitignore 的 `.dadao/` 下，不入库。
GATE_LOCK          ?= $(REPO_ROOT)/.dadao/gate.lock
GATE_LOCK_WAIT     ?= 3600
GATE_LOCK_FAILFAST ?= 0
GATE_LOCK_TOOL      = $(PYTHON) tools/infra/gate_lock.py

# 互斥面的**单一真源**（文档只指这里，不另列清单，避免漂移）。
GATE_LOCKED_TARGETS = install-host clean-work \
                      build-mc build-mc-lite build-mc-reconfig build-lld build-qemu build-qemu-reconfig \
                      build-builtins build-bootrom build-picolibc build-musl build-musl-shared \
                      test-codegen test-elf test-semihost test-m6 test-picolibc-smoke \
                      check-lit check-lit-full check-qemu-semantics check-qemu-smoke \
                      check-picolibc-tests check-picolibc-tests-full \
                      check-testcases-suites check-testcases-suites-full \
                      check check-modules check-full

# $(call gate-locked,<target>): 在锁下重入 make 跑 `_locked-<target>`。
# 必须重入而不能只锁 recipe：`install-host: build-mc build-lld ...` 的**前置**
# 才是写者，而前置在 recipe 之前执行。`-f $(firstword $(MAKEFILE_LIST))` 让重入
# 读同一个 makefile（`make -f`/探针 makefile 亦然）。一行（不用 `\` 续行，避免
# recipe 被拆行）。
gate-locked = $(GATE_LOCK_TOOL) run --lock "$(GATE_LOCK)" --wait $(GATE_LOCK_WAIT) --failfast $(GATE_LOCK_FAILFAST) --target $(1) -- $(MAKE) -f $(firstword $(MAKEFILE_LIST)) --no-print-directory _locked-$(1)

# 每个被锁目标 = 一条只做「进锁 + 重入」的门控规则；`_locked-<name>` 是原规则。
# `+` = make 的「recursive invocation」标记：把 jobserver 交给重入的 make，否则
# `make -jN` 会在子 make 里退化成 `-j1` 并打印 "jobserver unavailable"（本仓库
# `make -n` 本就不可用，见 Process-07 §1，`+` 使其在 -n 下也执行此行，同任何含
# $(MAKE) 的行）。
define gate-locked-rule
$(1):
	+@$$(call gate-locked,$(1))
endef
$(foreach t,$(GATE_LOCKED_TARGETS),$(eval $(call gate-locked-rule,$(t))))
.PHONY: $(GATE_LOCKED_TARGETS) $(addprefix _locked-,$(GATE_LOCKED_TARGETS))

# $(call component-enabled,<name>) exits 0 only when <name> is enabled in
# manifests/components.lock.toml. Build targets use it to refuse to pretend
# they built a component whose upstream commit is still pending.
component-enabled = $(PYTHON) -c "import tomllib,sys;m=tomllib.load(open('manifests/components.lock.toml','rb'));sys.exit(0 if any(c['name']=='$(1)' and c.get('enabled') for c in m.get('component',[])) else 1)"

help:
	@echo "DADAO-v5 orchestration"
	@echo ""
	@echo "  make help            Show this help"
	@echo "  make manifest-check  Validate specification/component/reference locks"
	@echo "  make doctor          Check host or container build prerequisites"
	@echo "  make status          Show locked components and references"
	@echo "  make fetch           Fetch enabled components at exact commits"
	@echo "  make fetch-refs      Fetch locked reference repositories"
	@echo "  make apply-series    Apply ordered patch series then auto-commit (E5)"
	@echo "  make prepare         Fetch enabled components and apply their patch series"
	@echo "  make check-source-state  Report each source tree's E1 state (clean + base+1)"
	@echo "  make build-mc        Build LLVM MC+CodeGen+clang+lli from one config (targets DADAO;X86, projects clang;lld)"
	@echo "  make build-mc-lite   Build LLVM MC/objdump/FileCheck/not only (no objcopy/readobj/CodeGen/clang/lli)"
	@echo "  make build-mc-reconfig  Force cmake re-run then build the full LLVM tool set"
	@echo "  make build-lld       Build LLD linker (bin/ld.lld); shares the one-shot LLVM config"
	@echo "  make build-qemu      Compile QEMU (skips configure if build.ninja exists)"
	@echo "  make build-qemu-reconfig  Force configure re-run then compile QEMU"
	@echo "  make build-gem5      Build gem5 (stub; command owned by the gem5 module)"
	@echo "  make build-bootrom   Assemble+link the SEE bootrom firmware and sample app (QEMU-047t; needs install-host)"
	@echo "  make build-picolibc  Build picolibc for dadao-unknown-elf and install it into the target sysroot (INFRA-057t; needs install-host + fetch/apply-series)"
	@echo "  make build-musl      Build the static musl libc (libc.a + crt) for dadao-unknown-elf in .work/source/musl (INFRA-082t; needs install-host + fetch/apply-series)"
	@echo "  make build-musl-shared  Build musl shared/PIC libc.so + link a dynamic smoke executable (PT_INTERP/DT_NEEDED), and install libc.so + the ld-musl-dadao.so.1 symlink into the target sysroot (INFRA-085t stage A1/B1; needs install-host + fetch/apply-series)"
	@echo "  make build-builtins  Rebuild the compiler-rt builtins with the current build-tree clang and stage the archive into that clang's resource dir (ISS-293; needs build-mc + a configured compiler-rt build tree)"
	@echo "  make test-picolibc-smoke  Compile/link/run a minimal picolibc printf program (QEMU semihosting; INFRA-057t)"
	@echo "  make check-picolibc-tests  Run the picolibc self-test representative set (L2; TESTCASES-042t)"
	@echo "  make check-picolibc-tests-full  Run the full picolibc self-test set (opt-in/L3-like; TESTCASES-042t)"
	@echo "  make check-testcases-suites  Run the two upstream reference suites (libc-test + llvm-test-suite) fast subset (opt-in, not L2; TESTCASES-045t)"
	@echo "  make check-testcases-suites-full  Run every enumerable C case with main() from both suites (opt-in/L3-like; TESTCASES-045t)"
	@echo "  make check-builtins-freshness  compiler-rt builtins archive must be the one the current clang built, in every consumer copy (L1; ISS-293)"
	@echo "  make install-host    Install needed tools: cross toolchain (clang/llc/ld.lld …) into \$$(HOST_TOOLCHAIN_BIN) + host lli into \$$(HOST_TOOLS_BIN); adr-0016 D3/D4/D5/D11"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make validate-vectors  Validate tests/vectors schema/inventory/coverage"
	@echo "  make check           Run repository-level structural checks (L1: static + component smoke)"
	@echo "  make check-modules   Run L2 module functional representative set (check-lit + check-interface + check-qemu-smoke + test-codegen/elf/semihost)"
	@echo "  make check-full      Run L3 fuller checks (check-qemu-semantics + test-m6; check-lit-full via test-m6)"
	@echo "  make check-components  Component availability smoke (llc/clang --print-targets/qemu; L1)"
	@echo "  make check-qemu-smoke  QEMU semantic smoke (representative subset; L2)"
	@echo "  make check-knowledge-refs  Dangling .work/** reference gate (L1; INFRA-058t)"
	@echo "  make check-run-artifacts  Run-directory three-piece set + .work/log new-name gate (L1; INFRA-093t)"
	@echo "  make check-contracts-dir  Whitelist gate for .tao/contracts/ + contracts/ top level (L1; INFRA-071t)"
	@echo "  make check-component-changelog  Component changelog list-form/milestone-section gate (L1; INFRA-084t)"
	@echo "  make check-syscall-abi  syscall argument-bank tables agree across musl C stub / cancellable asm / QEMU host, and cover every syscall musl can issue (L1; ISS-249)"
	@echo "  make check-contracts-pending  Contract pending markers (待定/待裁定/TODO/TBD) must carry an ADR-/ISS- pointer (L1; 2026-10-17)"
	@echo "  make check-contract-relocs  contract-elf §2.2 vs contract-dynlink §4.3 relocation type-table agreement (L1; 2026-10-17)"
	@echo "  make check-milestones-fresh  milestones.md task-flow table gate: status/coverage/length/order/format (L1; INFRA-091t)"
	@echo "  make check-milestone  Current-milestone m-book exists + its task ids exist + check-tasks --strict (milestone closure; not L1)"
	@echo "  make check-interface  Check cross-module interface alignment"
	@echo "  make validate-encoding  Validate opcodes.yaml encoding consistency"
	@echo "  make check-scope     Check opcodes.yaml scope partition (m1/fp/excluded; SPEC-086t)"
	@echo "  make check-spec-drift  Audit contract provenance against README versions"
	@echo "  make check-spec-refs Audit spec references in contract-*.md (L1; INFRA-011t/058t)"
	@echo "  make check-isa-coverage  ISA<->backend coverage matrix drift gate (L1; LLVM-081t/INFRA-069t)"
	@echo "  make check-spec-numbering  Check 21-volume heading numbering structure (L1; SPEC-133t/INFRA-069t)"
	@echo "  make check-spec-changelog  Check 21-volume appendix changelog structure (L1; SPEC-134t/INFRA-069t)"
	@echo "  make check-spec-archive  Check SimRISC per-version archives exist (L1; SPEC-154t)"
	@echo "  make check-asm-list  Check spec embedded assembly table consistency"
	@echo "  make check-asm-prose  Check prose assembly format gate (strict mode)"
	@echo "  make check-spec-codeblocks  Check spec prose \`\`\`simrisc blocks vs opcodes.yaml (ISS-077)"
	@echo "  make check-lit        Run lit MC + CodeGen + E2E tests (requires install-host)"
	@echo "  make check-lit-full   Run full generated lit MC suite from contracts/opcodes.yaml (opt-in; TESTCASES-037t)"
	@echo "  make test-codegen     Run M3 CodeGen E2E gate (llc->llvm-mc->objcopy->qemu; INTEG-012t)"
	@echo "  make test-elf         Run M4 multi-TU/multi-section ELF E2E gate (llc->ld.lld->qemu; INTEG-016t)"
	@echo "  make test-semihost    Run M5 SEE/semihosting E2E gate (bootrom+bin via -semihosting, console+SYS_EXIT, 25 svc; INTEG-020t)"
	@echo "  make test-m6          Run M6 E2E gate (lli value-level diff + Embench all benches -O0/-O2 + full lit MC suite; opt-in, INTEG-025t)"
	@echo "  make check-patch-tree  Check component patch tree (docs/Process-01, 9 assertions)"
	@echo "  make check-index-blobs  Check new-file patch index blob hashes (INFRA-038t/ISS-119)"
	@echo "  make check-legality-drift  Check LEGALITY section drift gate (SPEC-074t)"
	@echo "  make check-legality-invariants  Check ftroot/foroot n=2 + rule-rename gate (ISS-079)"
	@echo "  make check-rule-refs  Check rule_refs bidirectional gate (SPEC-071t)"
	@echo "  make check-fp-contract  Check FP semantics contract completeness (SPEC-087t)"
	@echo "  make check-instrinfo  Cross-check DADAOInstrInfo.td against opcodes.yaml (LLVM-046t)"
	@echo "  make check-cfx-aliases  Check cfx alias table drift gate (SPEC-075t)"
	@echo "  make check-asm-list-drift  Check assembly-list drift gate (INFRA-027t)"
	@echo "  make check-dirs      Validate install-dirs paths and symlink prefix guard"
	@echo "  make check-no-residue  Detect unexpected untracked temp files"
	@echo "  make check-spec-readonly  Verify read-only spec volumes against sha256 lock (SPEC-119t)"
	@echo "  make size-report  Report added-component-file sizes (advisory, not a gate)"
	@echo "  make check-tasks  Report tasks with filled 完成区 but status still 待验收 (advisory; --strict to fail)"

manifest-check:
	@$(PYTHON) tools/infra/manifest_check.py

doctor:
	@$(PYTHON) tools/infra/doctor.py

status:
	@$(PYTHON) tools/infra/status.py

fetch: manifest-check
	@$(PYTHON) tools/infra/fetch.py

fetch-refs: manifest-check
	@$(PYTHON) tools/infra/fetch_refs.py

# E5: after applying, apply_series.py commits locally (message
# "dadao: <component> patch series") so the worktree ends clean at base+1.
apply-series: manifest-check
	@$(PYTHON) tools/infra/apply_series.py

prepare: fetch apply-series

# DADAO is registered by adding it to LLVM_ALL_TARGETS in llvm/CMakeLists.txt
# (see ADR-0007).
#
# INFRA-050t: ONE cmake configuration for the whole LLVM tool set.  The tree
# .work/build/llvm is shared by build-mc / build-mc-lite / build-lld, so all of
# them must agree on the configuration; otherwise each would keep switching the
# tree back and forth.  The single configuration is:
#   - targets  DADAO + X86   (X86 is needed by lli's JIT value-level oracle)
#   - projects clang + lld   (clang compiler binary + ld.lld linker)
# and produces all four tools (clang/llc/ld.lld + lli) from one source commit.
# The config is stamped into the disposable build tree; the incremental fast
# path reconfigures only when the stamp differs, so a stale tree can never be
# silently reused (use build-mc-reconfig to force).  ADR-0016 D3/D11.
LLVM_TARGETS ?= DADAO;X86
LLVM_PROJECTS ?= clang;lld
LLVM_BUILD_CONFIG = targets=$(LLVM_TARGETS) projects=$(LLVM_PROJECTS) build_type=RelWithDebInfo assertions=ON

# Single-line shell snippet: (re)configure $(LLVM_BUILD) only when its stamped
# configuration differs.  A failing cmake aborts before the stamp is written.
LLVM_CONFIGURE = echo '$(LLVM_BUILD_CONFIG)' | cmp -s - $(LLVM_BUILD)/.dadao-llvm-config 2>/dev/null || { echo "llvm: configuring $(LLVM_BUILD) [$(LLVM_BUILD_CONFIG)]"; cmake -G Ninja -B $(LLVM_BUILD) -S $(LLVM_SRC) -DLLVM_TARGETS_TO_BUILD="$(LLVM_TARGETS)" -DLLVM_ENABLE_PROJECTS="$(LLVM_PROJECTS)" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DLLVM_ENABLE_ASSERTIONS=ON || exit 1; echo '$(LLVM_BUILD_CONFIG)' > $(LLVM_BUILD)/.dadao-llvm-config; }

LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj llvm-nm llvm-readelf FileCheck not LLVMDADAOCodeGen llc lli clang
LLVM_MC_LITE_TARGETS = llvm-mc llvm-objdump FileCheck not

_locked-build-mc: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc: PASS"

# build-mc-lite: same as build-mc but omits llvm-objcopy, llvm-readobj,
# LLVMDADAOCodeGen, lli and clang.  Sufficient for lit MC tests + encoding
# oracle + FileCheck.  Shares the one-shot configuration above.
_locked-build-mc-lite: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-lite: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_LITE_TARGETS)
	@echo "build-mc-lite: PASS"

# build-mc-reconfig: force a cmake re-run (drops the config stamp first).
_locked-build-mc-reconfig: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-reconfig: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@rm -f $(LLVM_BUILD)/.dadao-llvm-config
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_FULL_TARGETS)
	@echo "build-mc-reconfig: PASS"

# build-lld: build the LLD linker (produces .work/build/llvm/bin/ld.lld).
# See INFRA-043t / INFRA-050t.
#
# Since INFRA-050t, lld is part of the single shared configuration
# (LLVM_ENABLE_PROJECTS=clang;lld), so build-lld no longer needs its own cmake
# re-run: it reuses the stamped configuration via $(LLVM_CONFIGURE).
#
# The ninja target is `lld` (not `ld.lld`): lld/CMakeLists.txt creates the
# `ld.lld`/`lld-link`/`ld64.lld`/`wasm-ld` names as POST_BUILD copies of the
# `lld` executable (add_lld_symlink -> ALWAYS_GENERATE), so no separate ninja
# target named ld.lld exists.  Building `lld` writes bin/ld.lld.
LLD_TARGETS = lld

_locked-build-lld: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-lld: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLD_TARGETS)
	@echo "build-lld: PASS"

# build-qemu skips configure when build.ninja already exists (incremental fast
# path).  After applying patches that only touch .c/.h files (not meson.build),
# the incremental path compiles only changed objects (~3s for one file).
# Use build-qemu-reconfig to force a full configure (e.g. after changing
# meson.build or configure options).
_locked-build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@if [ -f $(QEMU_BUILD)/build.ninja ]; then \
	  echo "build-qemu: build.ninja exists, skipping configure (use build-qemu-reconfig to force)"; \
	else \
	  mkdir -p $(QEMU_BUILD) && \
	  cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	    --target-list=dadao-softmmu,dadao-linux-user \
	    --enable-tcg \
	    --disable-werror; \
	fi
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu: PASS"

# build-qemu-reconfig: always re-run configure (for when meson.build changes).
_locked-build-qemu-reconfig: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu-reconfig: component 'qemu' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	mkdir -p $(QEMU_BUILD)
	cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	  --target-list=dadao-softmmu,dadao-linux-user \
	  --enable-tcg \
	  --disable-werror
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu-reconfig: PASS"

# gem5 is a v5 addition and has no build command yet (the gem5 module owns it).
# This target is a deliberate skeleton: even once the component is enabled it
# must not claim success until a real recipe exists.
build-gem5: manifest-check
	@$(call component-enabled,gem5) || { \
	  echo "build-gem5: component 'gem5' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@echo "build-gem5: gem5 build command is not defined yet (owned by the gem5 module); refusing to fake success"
	@exit 1

# install-host (INFRA-047t, ADR-0016 D3/D4/D5/D11): stage only the needed host
# tool set from the .work/ build trees into the install root's bin/, install the
# lit runner (package + launcher) so the install root is self-contained, and lay
# down the target sysroot skeleton.  .work/ stays the single build truth (D9);
# the install root is a cache — re-run after rebuilding the components.
#
# D11 scope: just the tools the gates/executors need — llvm-mc/llvm-objdump/
# llvm-readobj/llvm-nm/llvm-readelf/FileCheck/not (lit MC + symbol/ELF inspection),
# llc (CodeGen), llvm-objcopy (test-codegen), lld + ld.lld (test-elf), clang
# (M6 cross compiler, INFRA-050t), qemu-system-dadao (D4), llvm-lit (lit runner).
# No full `cmake --install`.  (llvm-nm/llvm-readelf: INFRA-098t / ISS-261.)
#
# INFRA-050t dual destination: the cross toolchain (clang/llc/ld.lld) and the
# other target/cross tools go into $(HOST_TOOLCHAIN_BIN); the host-only lli
# value-level oracle goes into $(HOST_TOOLS_BIN) (resolved via paths.py, D7).
# The build tree's bin/clang is a symlink to a versioned clang-NN, so install
# with `cp -L` to dereference it (otherwise the installed symlink dangles).
#
# INFRA-053t: every install writes to a per-process temp name and then rename(2)s
# it over the destination ($(call atomic-install,...)).  rename(2) atomically
# replaces an existing regular file *or* a stale (e.g. previously dangling)
# symlink, so re-runs stay idempotent — and two concurrent `make install-host`
# runs can no longer hit `cp: cannot create regular file ...: File exists`.
# That error came from `cp -L --remove-destination`, which unlinks then opens
# O_CREAT|O_EXCL (a non-atomic pair): the loser's O_EXCL open fails EEXIST when
# the winner recreates the destination in between (ISS-172).
#
# NOTE (concurrency): install-host's *writes* are race-safe (INFRA-053t above),
# and concurrent runs of the writers/gates in one worktree are now *serialized*
# mechanically rather than by convention (INFRA-099t / ISS-229): every target in
# $(GATE_LOCKED_TARGETS) — install-host and the build-*/test-*/check* targets
# that share the build trees, this install root and $(TEST_ARTIFACTS_DIR) — runs
# under one flock(2) on $(GATE_LOCK) via tools/infra/gate_lock.py.  Independent
# processes wait (bounded by GATE_LOCK_WAIT, rc=75 with the holder's pid/target
# on timeout) or are refused at once with GATE_LOCK_FAILFAST=1; nested calls
# from the same make tree pass through.  See docs/Process-07 §2.
HOST_LLVM_TOOLS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj llvm-nm FileCheck not llc clang
# Zero-copy aliases, `<link>:<target>` (both live in $(HOST_TOOLCHAIN_BIN)).
# Single source of truth for the install aliases: the install recipe creates
# them and tools/infra/check_install_tools.py asserts their shape.  Relative
# symlinks resolve inside the install root and cost no bytes, unlike
# atomic-install (cp -aL) which would copy the (multi-GB) target again.
#
#   llvm-readelf -> llvm-readobj : upstream builds llvm-readelf as that same
#     binary (llvm/tools/llvm-readobj/CMakeLists.txt: `add_llvm_tool_symlink`),
#     so the GNU-style dumper is llvm-readobj in GNU output mode.  The build
#     tree's bin/llvm-readelf is a relative symlink too (ISS-261 / INFRA-098t).
#   clang++ -> clang : same binary as the C driver (INFRA-056t).
#   ld.lld -> lld    : lld's post-build copies (INFRA-043t).
HOST_LLVM_TOOL_SYMLINKS = ld.lld:lld clang++:clang llvm-readelf:llvm-readobj
HOST_LIT_DIR = $(HOST_TOOLCHAIN_DIR)/share/lit

# $(call atomic-install,<src>,<dst>): install <src> over <dst> via a per-process
# temp file + rename(2).  Idempotent and race-free (INFRA-053t / ISS-172).
# `cp -L` dereferences a source symlink (e.g. bin/clang -> clang-NN); rename(2)
# atomically replaces a regular/symlink destination, including a dangling one.
define atomic-install
cp -aL $(1) $(2).tmp.$$$$ && mv -f $(2).tmp.$$$$ $(2)
endef

# $(call atomic-install-dir,<srcdir>,<dstdir>): same temp+rename(2) convention as
# atomic-install, for a directory tree.  A rename(2) cannot overwrite a
# *non-empty* directory (ENOTEMPTY), so the previous <dstdir> is removed just
# before the final rename; the staged copy is always complete before it is
# exposed and re-runs are idempotent (INFRA-054t).
define atomic-install-dir
rm -rf $(2).tmp.$$$$ && cp -aL $(1) $(2).tmp.$$$$ && rm -rf $(2) && mv -f $(2).tmp.$$$$ $(2)
endef

# clang builtin (resource-dir) headers — INFRA-054t / ISS-174.
#
# Source: the `lib/clang/<ver>/include` tree emitted by the clang build (upstream
# `clang/lib/Headers/**` — freestanding headers such as stddef.h/stdint.h/
# stdbool.h/stdarg.h/limits.h/float.h).  A clang binary resolves its resource dir
# from its own prefix as `$(HOST_TOOLCHAIN_DIR)/lib/clang/<ver>`, so that dir must
# contain a real `include/` tree or every `#include <stddef.h>` fails with
# "file not found".
#
# <ver> is probed *live* from the build tree (never hardcoded): it is the same
# version the just-built clang reports via `-print-resource-dir`, so the staged
# dir lines up with what the installed clang looks for.
#
# The whole clang builtin `include/` tree is staged (these are the compiler's own
# freestanding headers — no target libc/OS/syscall header is introduced).  The
# resource-dir `lib/` gets exactly one entry: the DADAO compiler-rt builtins
# archive (INFRA-079t below), which the driver links itself.  These headers and
# that archive belong to the *host* compiler (D3), not to the target sysroot
# (D5) — ADR-0016 D3/D5/D11 scope is unchanged.
CLANG_RESOURCE_VER := $(shell ls -1 $(LLVM_BUILD)/lib/clang 2>/dev/null | head -n1)
CLANG_HEADERS_SRC  = $(LLVM_BUILD)/lib/clang/$(CLANG_RESOURCE_VER)/include
CLANG_RESOURCE_DIR = $(HOST_TOOLCHAIN_DIR)/lib/clang/$(CLANG_RESOURCE_VER)

# DADAO compiler-rt builtins (INFRA-079t / ADR-0027 D5): the independent
# builtins archive is produced by the compiler-rt standalone project into its
# per-target runtime dir (LLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON).  It is
# installed into the clang resource dir at exactly the path the driver reports
# for `-rtlib=compiler-rt -print-libgcc-file-name`; that relative path is
# probed live from the build-tree clang (never hardcoded), so the installed
# archive and the driver lookup cannot drift apart.
# Deliberately recursively expanded (`=`): the probe must run when the recipe
# runs, i.e. *after* build-mc has produced bin/clang, not at parse time (a clean
# checkout has neither the clang binary nor the archive yet).
COMPILER_RT_BUILD     ?= .work/build/compiler-rt-builtins
# ISS-293: the *source* of the install copy is `<build dir>/<the path the driver
# reports>`, not "the first archive matching a wildcard" -- the build tree also
# holds a retired narrow-scope archive under lib/linux/ (INFRA-079t), and a
# wildcard that picked it would install the wrong library.  Both sides of the
# copy then provably share one relative path.
#
# ISS-301: ONE probe, ONE path.  `-print-libgcc-file-name` is the only
# authoritative answer to "which archive does the build-tree clang link", and it
# names `<llvm-build>/lib/clang/<ver>/<resource-rel>`.  The previous derivation
# dropped the `clang/<ver>/` half, so `build-builtins` re-staged into
# `<llvm-build>/<resource-rel>` -- a directory no consumer reads -- while the
# copy the clang actually links stayed stale (and the freshness gate went red).
# Every consumer below (build-builtins stage target, install-host destination,
# and tools/infra/check_builtins_freshness.py, which splits the same probe) now
# derives from this one variable, so the three copies cannot drift apart again.
# The probe answers with an absolute path; it is reduced to the part below
# `lib/clang/` (`<ver>/lib/<triple>/libclang_rt.builtins.a`), which is byte-for-
# byte the same in the build tree and in the install root.
BUILTINS_RESOURCE_PATH = $(shell $(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name 2>/dev/null | sed -e 's|^.*/lib/clang/||')
BUILTINS_RESOURCE_VER  = $(firstword $(subst /, ,$(BUILTINS_RESOURCE_PATH)))
# Same file in the build tree (what bin/clang links) and in the install root
# (what install-host must refresh) -- one shape, two prefixes.
BUILTINS_BUILD_DST     = $(if $(BUILTINS_RESOURCE_PATH),$(LLVM_BUILD)/lib/clang/$(BUILTINS_RESOURCE_PATH))
BUILTINS_ARCHIVE_DST   = $(if $(BUILTINS_RESOURCE_PATH),$(HOST_TOOLCHAIN_DIR)/lib/clang/$(BUILTINS_RESOURCE_PATH))
# compiler-rt's own tree mirrors the resource dir *below* `lib/` (no `<ver>`):
# `<build dir>/lib/<triple>/libclang_rt.builtins.a`.
BUILTINS_BUILD_REL     = $(patsubst $(BUILTINS_RESOURCE_VER)/%,%,$(BUILTINS_RESOURCE_PATH))
BUILTINS_ARCHIVE_SRC   = $(if $(BUILTINS_BUILD_REL),$(COMPILER_RT_BUILD)/$(BUILTINS_BUILD_REL))

# build-builtins (ISS-293): rebuild the compiler-rt builtins with the *current*
# build-tree clang and re-stage the archive into that clang's resource dir.
#
# Why a clean rebuild: nothing in ninja tracks the compiler *binary* as an
# input of these objects, so after a codegen change (LLVM-116t moved `shl`) an
# incremental `ninja` reports "no work to do" and the archive keeps the retired
# encoding -- the new qemu then decodes it as undefined and the guest dies with
# SIGILL.  `-t clean` forces the whole target set through the current compiler
# (a few seconds; 148 tiny sources).
#
# Why the staging copy: `.work/build/llvm/bin/clang` links the archive from its
# own resource dir (`-print-libgcc-file-name`), and nothing else ever refreshed
# that copy -- it is a third consumer beside the build product and the install
# root.  `make install-host` stages the same archive into the install root.
#
# It depends on build-mc so `make -j install-host` cannot run the rebuild
# before the compiler exists (the recipe probe would fail); with the tree
# already built that prerequisite is a no-op.
_locked-build-builtins: manifest-check build-mc
	@$(call component-enabled,llvm-project) || { \
	  echo "build-builtins: component 'llvm-project' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@test -f $(LLVM_BUILD)/bin/clang || { echo "build-builtins: ERROR: $(LLVM_BUILD)/bin/clang not found -- run 'make build-mc' first"; exit 1; }
	@test -f $(COMPILER_RT_BUILD)/build.ninja || { echo "build-builtins: ERROR: no configured compiler-rt build tree at $(COMPILER_RT_BUILD) -- configure it once (INFRA-079t) first"; exit 1; }
	@test -n "$(BUILTINS_BUILD_DST)" || { echo "build-builtins: ERROR: cannot resolve the builtins path from '$(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name'"; exit 1; }
	ninja -C $(COMPILER_RT_BUILD) -t clean
	ninja -j$(JOBS) -C $(COMPILER_RT_BUILD) builtins
	@test -f $(BUILTINS_ARCHIVE_SRC) || { echo "build-builtins: ERROR: archive not produced at $(BUILTINS_ARCHIVE_SRC)"; exit 1; }
	@mkdir -p $(dir $(BUILTINS_BUILD_DST))
	@$(call atomic-install,$(BUILTINS_ARCHIVE_SRC),$(BUILTINS_BUILD_DST))
	@echo "build-builtins: PASS"

# clang++ (INFRA-056t): the C++ driver is the *same binary* as the C driver
# (upstream bin/clang++ is itself a symlink to clang-NN), so install it as a
# relative symlink to the already-installed `clang` — mirroring the ld.lld -> lld
# precedent.  Deliberately NOT added to $(HOST_LLVM_TOOLS): the clang binary
# is ~4 GB, so atomic-install would copy it a second time.  Being relative and
# resolving to the installed `clang`, it is zero-copy and same-source/same-commit.
# Same reasoning for llvm-readelf (INFRA-098t): upstream builds it as a symlink
# to llvm-readobj, so it must not be copied as a 319 MB standalone file.
# All three aliases are enumerated in $(HOST_LLVM_TOOL_SYMLINKS) (one variable,
# consumed by the recipe below and by tools/infra/check_install_tools.py).
_locked-install-host: build-mc build-lld build-qemu build-builtins
	@mkdir -p $(HOST_TOOLCHAIN_BIN) $(HOST_TOOLS_BIN)
	@for t in $(HOST_LLVM_TOOLS); do \
	  $(call atomic-install,$(LLVM_BUILD)/bin/$$t,$(HOST_TOOLCHAIN_BIN)/$$t) || exit 1; \
	done
	@$(call atomic-install,$(LLVM_BUILD)/bin/lld,$(HOST_TOOLCHAIN_BIN)/lld)
	@for s in $(HOST_LLVM_TOOL_SYMLINKS); do \
	  ln -sfn $${s#*:} $(HOST_TOOLCHAIN_BIN)/$${s%%:*} || exit 1; \
	done
	@$(call atomic-install,$(LLVM_BUILD)/bin/lli,$(HOST_TOOLS_BIN)/lli)
	@$(call atomic-install,$(QEMU_BUILD)/qemu-system-dadao,$(HOST_TOOLCHAIN_BIN)/qemu-system-dadao)
	@$(call atomic-install,$(QEMU_BUILD)/qemu-dadao,$(HOST_TOOLCHAIN_BIN)/qemu-dadao)
	@rm -rf $(HOST_LIT_DIR)
	@mkdir -p $(HOST_LIT_DIR)
	@cp -a $(LLVM_SRC)/utils/lit/lit $(HOST_LIT_DIR)/lit
	@rm -rf $(HOST_LIT_DIR)/lit/__pycache__
	@printf '%s\n' '#!/usr/bin/env python3' '# DADAO install-root lit launcher (INFRA-047t): the lit package is installed in ../share/lit' 'import os' 'import sys' '' '_prefix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))' 'sys.path.insert(0, os.path.join(_prefix, "share", "lit"))' '' 'from lit.main import main' '' 'if __name__ == "__main__":' '    main()' > $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@chmod +x $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@test -d $(CLANG_HEADERS_SRC) || { echo "install-host: ERROR: clang builtin headers not found at $(CLANG_HEADERS_SRC) — build tree incomplete (run 'make build-mc')"; exit 1; }
	@mkdir -p $(CLANG_RESOURCE_DIR)
	@$(call atomic-install-dir,$(CLANG_HEADERS_SRC),$(CLANG_RESOURCE_DIR)/include)
	@test -f $(BUILTINS_ARCHIVE_SRC) || { echo "install-host: ERROR: compiler-rt builtins archive not found under $(COMPILER_RT_BUILD)/lib/ — build the compiler-rt standalone 'builtins' target first (INFRA-079t)"; exit 1; }
	@case "$(BUILTINS_BUILD_REL)" in lib/*) ;; *) echo "install-host: ERROR: cannot resolve the builtins install path from '$(LLVM_BUILD)/bin/clang --target=dadao-unknown-elf -rtlib=compiler-rt -print-libgcc-file-name' (got '$(BUILTINS_RESOURCE_PATH)')"; exit 1 ;; esac
	@mkdir -p $(dir $(BUILTINS_ARCHIVE_DST))
	@$(call atomic-install,$(BUILTINS_ARCHIVE_SRC),$(BUILTINS_ARCHIVE_DST))
	@$(PYTHON) tools/infra/check_install_tools.py
	@mkdir -p $(TARGET_SYSROOT_DIR)/include $(TARGET_SYSROOT_DIR)/lib
	@printf '%s\n' '# DADAO target sysroot (dadao-unknown-elf)' '' 'Layout per ADR-0016 D5 (.tao/adr/adr-0016-dadao-install-layout.md):' '' '- include/ — target C headers (populated when a target libc/toolchain lands)' '- lib/     — target libraries' '' 'Placeholder only: there is no header/library consumer yet, so no content is' 'fabricated here. Consumers must resolve this path from' 'manifests/install-dirs.lock.toml via tools/infra/paths.py' '(target_sysroot_dir()), never hardcode it.' > $(TARGET_SYSROOT_DIR)/README.md
	@echo "install-host: PASS"

# build-bootrom (QEMU-047t / ADR-0020 D12): assemble and link the SEE bootrom
# firmware with the project toolchain (llvm-mc + ld.lld + tests/scripts/
# bootrom.lds; ADR-0003 / ADR-0019 / contract-elf §6.1.2) and emit the flat
# `-bios` image, plus the sample user application loaded by `-kernel`
# (ADR-0004 D2.3 path B: raw-bin dual image).  Tools come from the install root
# (ADR-0016 D9); run `make install-host` first.  Outputs live under the SDK
# test-artifacts root (ADR-0016 D6, resolved via paths.py):
#   $(BOOTROM_DIR)/{bootrom.o,bootrom.elf,bootrom.bin,bootrom_app.o,bootrom_app.bin}
BOOTROM_DIR = $(TEST_ARTIFACTS_DIR)/bootrom
_locked-build-bootrom:
	@test -x $(LLVM_MC_BIN) || { echo "build-bootrom: ERROR: $(LLVM_MC_BIN) not found — run 'make install-host' first"; exit 1; }
	@test -x $(LLD_BIN) || { echo "build-bootrom: ERROR: $(LLD_BIN) not found — run 'make install-host' first"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "build-bootrom: ERROR: $(LLVM_OBJCOPY_BIN) not found — run 'make install-host' first"; exit 1; }
	@mkdir -p $(BOOTROM_DIR)
	$(LLVM_MC_BIN) --triple=dadao-unknown-elf -filetype=obj tests/scripts/bootrom.S -o $(BOOTROM_DIR)/bootrom.o
	$(LLD_BIN) -T tests/scripts/bootrom.lds $(BOOTROM_DIR)/bootrom.o -o $(BOOTROM_DIR)/bootrom.elf
	$(LLVM_OBJCOPY_BIN) -O binary $(BOOTROM_DIR)/bootrom.elf $(BOOTROM_DIR)/bootrom.bin
	$(LLVM_MC_BIN) --triple=dadao-unknown-elf -filetype=obj tests/scripts/bootrom_app.S -o $(BOOTROM_DIR)/bootrom_app.o
	$(LLVM_OBJCOPY_BIN) -O binary --only-section=.text $(BOOTROM_DIR)/bootrom_app.o $(BOOTROM_DIR)/bootrom_app.bin
	@echo "build-bootrom: PASS (outputs under $(BOOTROM_DIR))"

# build-picolibc (INFRA-057t): build the DADAO port of picolibc with Meson and
# install it into the target sysroot (headers under $(TARGET_SYSROOT_DIR)/
# include, libraries under .../lib).  The cross file, the machine directory and
# the semihosting syscall stubs live in the component patch set
# (components/picolibc/patches/**); run 'make fetch apply-series' first.
# The target is idempotent (Meson reconfigure + incremental Ninja + install).
# Requires the install-root clang (run 'make install-host' first).
_locked-build-picolibc:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-picolibc: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_picolibc.py --jobs $(JOBS)

# test-picolibc-smoke (INFRA-057t): minimal end-to-end check — a printf("hi")
# program is compiled against the installed picolibc, linked with the project
# crt0/linker script and run under QEMU via semihosting; the guest must print
# "hi" and exit 0.  Needs 'make build-picolibc' + 'make install-host' first.
_locked-test-picolibc-smoke: build-picolibc
	@$(PYTHON) tools/infra/test_picolibc_smoke.py

# check-picolibc-tests (TESTCASES-042t, L2): the picolibc upstream self-test
# representative set — one test per Meson suite, mechanically derived by the
# harness (no hand-picked list).  The harness configures the picolibc Meson test
# build (for the authoritative test inventory), then compiles/links/runs each
# test under qemu-system-dadao -machine dadao-m1 + semihosting.  Fails if any
# representative reports a genuine test failure (fail=0); backend/library gaps
# are reported separately as `blocked`, never as silent skips.
_locked-check-picolibc-tests: build-picolibc
	@$(PYTHON) tools/testcases/picolibc_tests.py --stage fast --jobs $(JOBS)

# check-picolibc-tests-full (TESTCASES-042t): the full picolibc self-test set
# (opt-in; L3-like — hundreds of compile/link/QEMU runs, several minutes).
_locked-check-picolibc-tests-full: build-picolibc
	@$(PYTHON) tools/testcases/picolibc_tests.py --stage full --jobs $(JOBS)

# check-testcases-suites (TESTCASES-045t stage 1): drive the two upstream
# *reference* suites -- libc-test and llvm-test-suite -- through the static musl
# flow (compile -> ld.lld -T dadao.lds -> flat image -> qemu-system-dadao
# -machine dadao-m1, "path B").  Upstream's own harnesses are unusable here
# (libc-test's runtest.exe needs fork/waitpid/signals; llvm-test-suite's
# CMake/lit driver assumes a hosted OS), so tools/testcases/run_suite.py drives
# the corpora directly and classifies every case live.
#
# OPT-IN LEVEL: this target is deliberately NOT listed in L1/L2/L3.  The stage-1
# case list is a *curated* stratified subset (each entry records its tier and
# why), and docs/Process-07 §3 requires an L2 "representative set" to be
# *mechanically* derived; assigning a curated list to L2 would violate that.  It
# stays an on-demand target ("按需" level) until stage 3 replaces the curation
# with a mechanical derivation and the cost/FAIL story has been measured.
#
# Exit status follows tools/testcases/run_suite.py: non-zero on any `fail` or
# `timeout` (a genuine wrong result / hang).  `enosys`, `compile-error` and
# `unsupported` are counted and listed, never silently skipped, and do not turn
# the target red -- they are the documented state of an unfinished port.
_locked-check-testcases-suites:
	@$(PYTHON) tools/testcases/run_suite.py --stage fast \
		--json-out .work/log/testcases/runs/fast.json

# check-testcases-suites-full (TESTCASES-045t): every enumerable C case with
# main() in both suites (upstream `External/`, C++/Fortran/ObjC sources and
# helper TUs without main() are counted as `unsupported` with their reason).
# Opt-in, L3-like: hundreds of compile/link/QEMU runs; `--timeout` is raised for
# the benchmarks whose default problem size exceeds the fast-stage budget.
_locked-check-testcases-suites-full:
	@$(PYTHON) tools/testcases/run_suite.py --stage full --timeout 300 \
		--json-out .work/log/testcases/runs/full.json

# build-musl (INFRA-082t): configure and build the static musl libc for
# dadao-unknown-elf inside .work/source/musl (the DADAO port lives as a
# tree-shaped patch set, components/musl/patches/**; run 'make fetch
# apply-series' first).  P1 is the STATIC subset: --disable-shared is
# deliberate (the dynamic linker is P2, ADR-0025 D6).  Products:
# lib/libc.a + lib/crt{1,i,n}.o.  The target is idempotent (configure is
# skipped once config.mak exists and records the same mode) and, by default,
# also links and verifies a minimal static program (see
# tools/infra/build_musl.py).  Requires the install-root clang (run
# 'make install-host' first).  Stale objects are guarded: a change in the
# toolchain binaries (clang / ld.lld stamp, obj/.dadao-toolchain-stamp) or a
# tree without a stamp runs 'make clean' before building; the decision
# ("... => 'make clean'" / "... => incremental build") is printed.  Applies to
# build-musl-shared too (same script, same in-tree build directory).
_locked-build-musl:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-musl: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_musl.py --jobs $(JOBS)

# build-musl-shared (INFRA-085t stage A1): the SHARED/PIC counterpart -- same
# source tree, configured *without* --disable-shared so musl links lib/libc.so
# from -fPIC objects, with -Wl,--hash-style=gnu and -Wl,-soname,libc.so pinning
# the dynamic-section shape (contract-dynlink.md §5 rulings 6/7, §6.1).  Checks
# libc.so is ET_DYN/big-endian with DT_SONAME + DT_GNU_HASH and without
# DT_HASH/DT_RELR/version sections, then installs libc.so plus the
# ld-musl-dadao.so.1 -> libc.so symlink into the target sysroot lib dir
# (ADR-0016 D5).  The static line is checked in the same run (lib/libc.a is
# built from the same non-PIC objects), so the two modes cannot drift apart.
# Stage B1 (INFRA-085t): the same run links a dynamic EXECUTABLE with the
# interpreter passed explicitly (-dynamic-linker /lib/ld-musl-dadao.so.1,
# contract-dynlink.md §6.1 / ADR-0026 D2) and checks PT_INTERP + DT_NEEDED.
# Running/loading it is P3 (qemu-user) and is not done here.
_locked-build-musl-shared:
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "build-musl-shared: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/infra/build_musl.py --jobs $(JOBS) --shared

docker-image:
	docker build -t $(DOCKER_TAG) containers/dev

docker-shell:
	docker run --rm -it -v "$(PWD):/workspace" $(DOCKER_TAG) /bin/bash

_locked-clean-work:
	@$(PYTHON) tools/infra/clean_work.py

# ── 门控分层 (INFRA-058t；用户 2026-10-09 裁定，落 milestones「规划中」) ─────────
# L1 `make check`（默认，秒~几十秒）   = 仓库完整性（静态检查）+ 组件可用性冒烟
# L2 `make check-modules`（几十~几百秒）= 各模块功能代表集
# L3 `make check-full`（几百~几千秒）   = 较完整（全量语义 + 全量 lit + Embench）
# 「层间不重复」= 同一检查只在一层「直接」列出；触发点见 AGENTS.md「门控分层与触发点」。
# `check-qemu-semantics`(L3) 与 `check-lit`/`check-interface`(L2) 已从 L1 移出。
_locked-check: manifest-check validate-vectors check-spec-drift check-patch-tree check-index-blobs check-asm-list check-asm-list-drift check-asm-prose check-spec-codeblocks check-legality-drift check-legality-invariants validate-encoding check-scope check-rule-refs check-fp-contract check-instrinfo check-isa-coverage check-cfx-aliases check-dirs check-no-residue check-spec-readonly check-spec-refs check-knowledge-refs check-knowledge-dir check-contracts-dir check-spec-numbering check-spec-changelog check-spec-archive check-component-changelog check-syscall-abi check-musl-freshness check-builtins-freshness check-milestones-fresh check-contracts-pending check-contract-relocs check-run-artifacts check-components
	@$(PYTHON) tools/infra/check_issues.py
	@$(PYTHON) -m compileall -q tools
	@echo "repository checks (L1): PASS"

# L2 各模块功能代表集 (INFRA-058t). 注: test-semihost 自带对 `check`(L1) 的无回归前置
# （by design，见 INTEG-020t），故 `make check-modules` 会顺带跑 L1。
_locked-check-modules: check-interface check-lit check-qemu-smoke test-codegen test-elf test-semihost check-picolibc-tests
	@echo "module checks (L2): PASS"

# L3 较完整 (INFRA-058t). check-lit-full 由 test-m6 步骤 [1/3] 承载（不在本目标重复列出）。
_locked-check-full: check-qemu-semantics test-m6
	@echo "full checks (L3): PASS"

# Vector schema/inventory/coverage gate (TESTCASES-002t). Requires the M1
# encoding table (contracts/opcodes.yaml) to exist.
validate-vectors: contracts/opcodes.yaml
	@$(PYTHON) tools/testcases/validate_vectors.py

# spec drift check (INFRA-012t): fail-closed provenance audit for contract-*.md.
check-spec-drift:
	@$(PYTHON) tools/infra/check_spec_drift.py

# 21-volume heading numbering gate (SPEC-133t; INFRA-069t 并入 L1): depth <= 4,
# `N`/`N.M`/`N.M.K` shape, per-volume uniqueness + contiguity, no orphan parent.
check-spec-numbering:
	@$(PYTHON) tools/spec/check_numbering.py

# 21-volume appendix changelog gate (SPEC-134t; INFRA-069t 并入 L1): appendix
# exists and is last, version segments strictly reversed, header consistency,
# no table rows / task-ids.  Counts are recomputed live, never hardcoded.
check-spec-changelog:
	@$(PYTHON) tools/spec/check_spec_changelog.py

# SimRISC 版本归档门控 (SPEC-154t; 规则见 docs/Process-06 §8): 册头 ∪ 附录声明的
# 每个版本须有 `.tao/archive/SimRISC-<ver>/`（非空、含 SimRISC-00*、文件数与派生清单一致）。
# 只校验存在性与文件集，不校验内容（`-rc` 为时点快照）。派生失败 ⇒ 只查 A1/A2。
check-spec-archive:
	@$(PYTHON) tools/spec/check_spec_archive.py

# 组件补丁集校验 (2026-09-23): 树形补丁集断言（现 9 条），见 docs/Process-01-组件补丁组织与构建编排.md。
check-patch-tree:
	@$(PYTHON) tools/infra/check_patch_tree.py

# new-file 补丁 index blob hash 卫生 (INFRA-038t/ISS-119): 按补丁自身内容用
# `git hash-object --stdin` 重算 new-file 补丁的 index 新 hash；失配 ⇒ FAIL。
# 修改类补丁（有 old hash）不在此检查范围内，明确跳过。
check-index-blobs:
	@$(PYTHON) tools/infra/check_index_blobs.py

# E7 模块自检 (2026-10-03): 报告每个源树的 E1 状态（worktree 干净 + base+1）。
check-source-state:
	@$(PYTHON) tools/infra/check_patch_tree.py --source-state

# 组件源文件规模报告 (INFRA-028t): 仅报告（非强制），不进门控。
# 规则见 docs/Process-01 §11「组件源文件规模约定」。
size-report:
	@$(PYTHON) tools/infra/size_report.py

# 待收尾任务自查 (INFRA-029t): 报告型，列出「完成区已填 + 待验收」的漏 /complete 任务。
# 默认退出码 0，不并入 `make check` 阻断路径；--strict 时命中 >0 则失败。
check-tasks:
	@$(PYTHON) tools/infra/check_tasks.py

# 测试运行产物与日志命名门控 (INFRA-093t, L1): A1 三个 user-mode 驱动无固定
# 默认输出（`--json-out` 必填、无 DEFAULT_LOG_DIR 回落）；A2 `.work/tests/**`
# 与 test-artifacts 根下每个 `YYYYMMDDTHHMMSSZ-*` 运行目录须有
# run.json/run.log/meta.json（meta 含 command/started_utc/toolchain 摘要）；
# A3 `.work/log/**` 新增文件名须为 `check-<name>.log` 或
# `<任务号>-<用途>.(log|json|txt)`（存量按 `.run-artifacts-epoch` +
# `.run-artifacts-baseline` 豁免；标记缺失 ⇒ SKIP 并打印）。
# 规则真源 = docs/Process-08；可达 FAIL 见 `--self-test`。
check-run-artifacts:
	@$(PYTHON) tools/infra/check_run_artifacts.py

# 里程碑收尾门控 (2026-10-17, A2; 归 **L2 层 / 里程碑收尾专项**，**不入** `check-modules`):
# ① 当前里程碑（`milestones.md` 中 `项目里程碑 = M<n>` 断言的最大 n）在 `.tao/tasks/**`
#    下有对应 `m` 册（命名惯例 `<PREFIX>-<nnn>m-*.md`；自报里程碑须与当前一致）；
# ② 该 `m` 册列出的全部任务号须在 `.tao/tasks/**`（或 `.tao/archive/**`，已完成并归档）
#    有对应任务书；册内零任务号 ⇒ vacuous FAIL（防「漏立任务」）；
# ③ 接 `check_tasks.py --strict`（漏收尾 = 0）。
# 不并入 L1 的理由：`m` 册未建前本目标**必然红**（预期的收口信号），日常 L1 不应常态红。
check-milestone:
	@$(PYTHON) tools/infra/check_milestone_tasks.py
	@$(PYTHON) tools/infra/check_tasks.py --strict
	@echo "check-milestone: PASS (m 册在场 + 所列任务号存在 + 漏收尾 = 0)"

# spec 引用审计 (INFRA-011t): Check 1 引用有效性 + Check 2 无引用规范断言.
# L1 成员 (INFRA-058t): 静态引用完整性检查（改后 0 误报）。覆盖 SimRISC-/DADAO-/
# Toolchain-01/Machine-01；数值节号 (§7.2) 命中标题 `7.2 …`；模板占位 (§x/§N) 跳过。
check-spec-refs:
	@$(PYTHON) tools/infra/check_spec_refs.py

# 被引用 `.work/**` 材料悬空门控 (INFRA-058t / INTEG-037t): 扫 AGENTS.md/spec/
# .tao/knowledge/.tao/contracts/.tao/tasks 中对 `.work/**` 的引用；悬空即红。L1 成员。
# 口径 (见 AGENTS.md「文档分层与单一真源」): 占位/通配/前缀截断跳过；
# `.work/build`/`.work/source` 豁免；删除语境引用不校验；其余具体路径要求存在。
check-knowledge-refs:
	@$(PYTHON) tools/infra/check_knowledge_refs.py

# `.tao/knowledge/` 顶层白名单门控 (INFRA-070t, L1 成员): 顶层只允许既定模式
# （台账集合 / 子目录）；`contract-*.md` 已随 INFRA-071t 迁出 ⇒ 顶层再出现即白名单外 FAIL。
# 计数现场统计、不写死。规则见 AGENTS.md「文档分层与单一真源」+ docs/Process-07。
check-knowledge-dir:
	@$(PYTHON) tools/infra/check_knowledge_dir.py

# 契约目录顶层白名单门控 (INFRA-071t, L1 成员; 守两处): `.tao/contracts/` 顶层只允许
# `contract-*.md` / `README.md` / 子目录; `contracts/` 顶层只允许 `*.yaml` / `README.md` /
# 子目录（`contract-*.md` 随 Phase B 迁出作废）。白名单外文件 / 目录缺失 / vacuous 即 FAIL。
check-contracts-dir:
	@$(PYTHON) tools/infra/check_contracts_dir.py

# 组件 changelog 形态门控 (INFRA-084t, L1 成员): `components/*/` 下的组件变更记录必须为
# 「列表式（无表格）+ 按里程碑分节」形态（体例真源 docs/Process-01 §10）——① 无表格分隔行
# ② 条目 `- **<日期> …**` ③ 条目紧接 `  - 摘要：` 缩进行 ④ `## M<k>` 节序严格递增
# ⑤ 覆盖全部（glob 现场派生；空集 vacuous FAIL）。**只做形态断言**，不做内容校验；
# 计数现场统计、不写死。可达 FAIL 见 `--self-test`。
# syscall 参数银行三载体一致性 (ISS-249, L1): musl __dadao_argmask / 可取消 asm 派发 /
# QEMU dadao_argmask 逐项一致 + 完整性（musl 能发出的 syscall 名全覆盖）。
# 有 .work/source 时读工作树，否则退回 components/ 下的补丁（新克隆也能跑）。
check-syscall-abi:
	@$(PYTHON) tools/qemu/check_syscall_abi.py

# musl 产物新鲜度 (ISS-258): 安装根 libc.so 必须由当前 musl 源 + 工具链构建
# （build_musl.py 成功构建后在 obj/ 落 toolchain/source 戳记；源 digest 变即
# 强制 make clean；安装副本与构建产物逐字节一致）。无构建树 / 无共享产物 ⇒
# SKIP；有产物则缺戳记即 FAIL。成本 ~1.2 s（内容摘要），按 docs/Process-07
# §1.1 归 L1（静态溯源，不跑被测语义）。
check-musl-freshness:
	@$(PYTHON) tools/infra/check_musl_freshness.py

# compiler-rt builtins 归档新鲜度 (ISS-293, L1): 工具链消费的三份归档（构建树产物 /
# 构建树 clang 资源目录副本 / 安装根副本）必须同一内容，且不旧于构建树 clang
# （归档 mtime + 逐成员 .c.o mtime）。旧编码残留 → 新 qemu 按 ILLI 打 SIGILL。
# `--self-test` 内置「篡改安装副本 ⇒ 红」与「仅 mtime 变 ⇒ 不假红」(ISS-263)。
check-builtins-freshness:
	@$(PYTHON) tools/infra/check_builtins_freshness.py --build-dir $(COMPILER_RT_BUILD)

# 安装集断言 (ISS-261 / INFRA-098t): 安装根须带上门控/执行器要用的工具，且每个都仍是
# 构建树同一个二进制（真值源 = 本 Makefile 的 HOST_LLVM_TOOLS + HOST_LLVM_TOOL_SYMLINKS，
# 脚本解析本文件，不另写第二份清单）。挂载点 = install-host 收尾（装完即断言），
# 亦可 `make check-install-tools` 单独调。**不入 L1**：未跑过 install-host 的新克隆
# 必然红（与 check-milestone 同类理由，层归属见 docs/Process-07 §1.1）。
check-install-tools:
	@$(PYTHON) tools/infra/check_install_tools.py

# 任务流水体例门控 (INFRA-091t, L1): 状态 == 任务书 / 覆盖 / 一句改动 ≤120 字符 /
# 时间倒序 / 格式。规则 = milestones.md「体例约定（硬约束）」+ docs/Process-07 §1.1。
check-milestones-fresh:
	@$(PYTHON) tools/infra/check_milestones_fresh.py

check-component-changelog:
	@$(PYTHON) tools/infra/check_component_changelog.py

# 契约「待定」指针门控 (2026-10-17, B4; L1 成员): `.tao/contracts/**` 出现
# 「待…定 / 待裁定 / TODO / TBD」类标记时，该行须同时含 `ADR-<n>` / `ISS-<n>` 指针
# （只认带编号的落点；光写「待后继 ADR 定」不算）；行内代码跨度与「」引用不计。
# 计数现场统计、不写死；可达 FAIL 见 `--self-test`。
check-contracts-pending:
	@$(PYTHON) tools/infra/check_contracts_pending.py

# 契约重定位类型表一致门控 (2026-10-17, B5; L1 成员): `contract-elf.md §2.2` 与
# `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内的
# 表格行 ⇒ 历史注记 / 其它小节的历史表不参与（旧值可留在注记里，以现行表为准）。
# 附加自洽：表非空、号/名唯一、号 0 起密集；可达 FAIL 见 `--self-test`。
check-contract-relocs:
	@$(PYTHON) tools/infra/check_contract_relocs.py

# cfx alias drift gate (SPEC-075t): verify .tao/contracts/contract-cfx-aliases.md is up-to-date.
check-cfx-aliases:
	@$(PYTHON) tools/spec/check_cfx_aliases.py

# Install/product directory path guard (INFRA-019t): validates
# manifests/install-dirs.lock.toml and scans for symlink prefix violations.
check-dirs:
	@$(PYTHON) tools/infra/check_dirs.py

# Residue gate (INFRA-025t): detect unexpected untracked temp files.
check-no-residue:
	@$(PYTHON) tools/infra/check_dirs.py --residue

# 组件可用性冒烟 (INFRA-058t, L1): llc / clang --print-targets / qemu-system-dadao
# 可执行且确实认识 `dadao` 目标；不跑被测语义（那是 L2/L3）。
check-components:
	@$(PYTHON) tools/infra/check_components.py

# spec 目录只读锁 (SPEC-119t): 只读册 sha256 校验；失配 ⇒ FAIL（须先取用户授权并同步改锁）。
# 规则见 docs/Process-06-spec目录保护规范.md §5。
check-spec-readonly:
	@$(PYTHON) tools/infra/check_spec_readonly.py

# Spec embedded assembly list consistency (SPEC-037t).
check-asm-list:
	@$(PYTHON) tools/spec/check_asm_list_consistency.py

# Assembly-list drift gate (INFRA-027t): verify .tao/contracts/contract-asm-list.md
# is up-to-date (regenerates to a temp file, byte-diff; never overwrites).
check-asm-list-drift:
	@$(PYTHON) tools/spec/check_asm_list_drift.py

# Assembly prose format gate (SPEC-076t): detect old-format assembly
# in prose fenced-code blocks.  --strict: exit 1 if any violation (baseline=0).
check-asm-prose:
	@$(PYTHON) tools/spec/check_asm_prose.py --strict

# Spec prose ```simrisc code-block gate (SPEC-103t/ISS-077): every instruction
# line in spec/**/*.md must use a mnemonic
# from contracts/opcodes.yaml (pseudo-instructions excepted) with a valid
# operand count.
check-spec-codeblocks:
	@$(PYTHON) tools/spec/check_spec_codeblocks.py

# lit gate (INFRA-021t): run llvm-lit on MC (M1/M4) + CodeGen (L2) + E2E.
# MC needs llvm-mc/llvm-objdump/FileCheck; CodeGen needs llc + FileCheck; E2E
# needs llvm-objcopy + qemu-system-dadao + trampoline (all installed by
# `make install-host`).
# llvm-lit missing => explicit error (never silent skip).
# INFRA-047t (ADR-0016 D9): tools are taken from the install root, not .work/build.
# INFRA-058t: L2 成员（功能代表集，受控子集）——已从 L1 `make check` 移出。
LIT_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-lit
_locked-check-lit:
	@test -x $(LIT_BIN) || { echo "check-lit: ERROR: $(LIT_BIN) not found — run 'make install-host' first"; exit 1; }
	$(LIT_BIN) tests/llvm/lit/MC/DADAO tests/llvm/lit/CodeGen/DADAO tests/e2e/lit -v

# lit 全量档 (TESTCASES-037t): 由 contracts/opcodes.yaml 机械生成的全部 lit MC
# 编码用例（快档受控子集已随 check-lit 进 L2；本目标承载规模）。
# INFRA-058t: 归 **L3**（经 `check-full` → `test-m6` 步骤 [1/3] 承载；本目标亦可单独调）。
# 先跑结构+编码检查器，再跑 lit。
# 计数不写死：由 check_lit_gen.py / llvm-lit **现场统计**；本目标不设硬编码门限。
_locked-check-lit-full:
	@test -x $(LIT_BIN) || { echo "check-lit-full: ERROR: $(LIT_BIN) not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tools/testcases/check_lit_gen.py
	$(LIT_BIN) tests/llvm/lit/MC/DADAO-gen -v

# M3 CodeGen end-to-end gate (INTEG-012t).  Tools are taken from the install
# root (ADR-0016 D9); install-host keeps it in sync with the .work/ build trees.
# Pipeline (single TU, per ADR-0003 D5):
#   llc -march=dadao <prog.ll> -> .s; cat codegen_crt0.s prog.s -> .s;
#   llvm-mc --triple=dadao -filetype=obj -> .o;
#   llvm-objcopy -O binary --only-section=.text -> .bin;
#   qemu-system-dadao -M dadao-m1 -bios trampoline.bin -kernel .bin ...
# The guest process exit code is compared against tests/llvm/codegen/expected.yaml.
# Fail-closed: any mismatch / timeout / machine fault => non-zero exit.
LLC_BIN = $(HOST_TOOLCHAIN_BIN)/llc
LLVM_MC_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-mc
LLVM_OBJCOPY_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-objcopy
QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao
# Work dir under the SDK test-artifacts root (ADR-0016 D6), resolved via
# paths.py (D7) — never the source tree.
CODEGEN_E2E_WORK = $(TEST_ARTIFACTS_DIR)/codegen-e2e
CODEGEN_E2E_LOG = .work/log/integ/test-codegen.log
_locked-test-codegen: install-host
	@test -x $(LLC_BIN) || { echo "test-codegen: ERROR: $(LLC_BIN) not found"; exit 1; }
	@test -x $(LLVM_MC_BIN) || { echo "test-codegen: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "test-codegen: ERROR: $(LLVM_OBJCOPY_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-codegen: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@rm -rf $(CODEGEN_E2E_WORK); \
	  mkdir -p .work/log/integ; \
	  $(PYTHON) tools/integ/run_codegen_e2e.py \
	    --llc $(LLC_BIN) --llvm-mc $(LLVM_MC_BIN) --llvm-objcopy $(LLVM_OBJCOPY_BIN) \
	    --qemu $(QEMU_BIN) --trampoline tests/scripts/trampoline.bin \
	    --crt0 tests/scripts/codegen_crt0.s --work-dir $(CODEGEN_E2E_WORK) \
	    > $(CODEGEN_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -20 $(CODEGEN_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-codegen: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "test-codegen: PASS"

# M4 multi-TU / multi-section ELF end-to-end gate (INTEG-016t).  Tools are taken
# from the install root (ADR-0016 D9); install-host keeps it in sync with the
# build trees.  Pipeline (multi-object, per contract-elf.md §6.1.2):
#   llvm-mc --triple=dadao -filetype=obj tests/scripts/codegen_crt0.s -> crt0.o;
#   per TU llc -march=dadao -filetype=obj                            -> <tu>.o;
#   ld.lld -T tests/scripts/dadao.lds crt0.o <tu>.o ... -o <prog>.elf;
#   qemu-system-dadao -M dadao-m1 -kernel <prog>.elf ...
# The guest process exit code is compared against the independent M4 manifest
# tests/llvm/codegen/m4/expected.yaml (TESTCASES-030t/032t).
# Fail-closed: any mismatch / timeout / build-step non-zero => non-zero exit.
# Coexists with test-codegen (raw-bin / trampoline: kept as-is).
LLD_BIN = $(HOST_TOOLCHAIN_BIN)/ld.lld
# Work dir under the SDK test-artifacts root (ADR-0016 D6), resolved via
# paths.py (D7); coexists with test-codegen's dir.
CODEGEN_ELF_WORK = $(TEST_ARTIFACTS_DIR)/elf-e2e
CODEGEN_ELF_LOG = .work/log/integ/test-elf.log
_locked-test-elf: install-host
	@test -x $(LLC_BIN) || { echo "test-elf: ERROR: $(LLC_BIN) not found"; exit 1; }
	@test -x $(LLVM_MC_BIN) || { echo "test-elf: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLD_BIN) || { echo "test-elf: ERROR: $(LLD_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-elf: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@rm -rf $(CODEGEN_ELF_WORK); \
	  mkdir -p .work/log/integ; \
	  $(PYTHON) tools/integ/run_elf_e2e.py \
	    --llc $(LLC_BIN) --llvm-mc $(LLVM_MC_BIN) --ldlld $(LLD_BIN) \
	    --qemu $(QEMU_BIN) --crt0 tests/scripts/codegen_crt0.s \
	    --lds tests/scripts/dadao.lds \
	    --vectors-dir tests/llvm/codegen/m4 \
	    --expected tests/llvm/codegen/m4/expected.yaml \
	    --work-dir $(CODEGEN_ELF_WORK) \
	    > $(CODEGEN_ELF_LOG) 2>&1; \
	  rc=$$?; \
	  tail -20 $(CODEGEN_ELF_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-elf: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "test-elf: PASS"

# M5 SEE/semihosting end-to-end gate (INTEG-020t).  Five components, all
# fail-closed (any failure => non-zero exit):
#   1. forward: SEE bootrom (`-bios`, QEMU-047t) + flat bin application
#      (`-kernel`) served through `-semihosting`; the semihosting console is
#      captured with a file chardev and the host exit code is the SYS_EXIT
#      status.
#   2. cfx-level permission counter-examples (4 cases carried by the same
#      driver: reserved cfxha / masked trap => ILLI; unimplemented cfx /
#      out-of-range scratch register => CFXREG; ADR-0020 D9).
#   3. full 25-service table coverage (QEMU-046t min-ROM probe, >=1 per id).
#   4. no regression: test-elf (5/5), test-codegen (15/15) and check (which
#      includes check-lit) -- enforced as prerequisites.
#   5. INTEG open/close registration (INTEG-021m): recorded in this target's
#      logs and the task book.
# Tools come from the install root (ADR-0016 D9); the bootrom from
# `make build-bootrom`.  Coexists with (does not replace) test-elf/test-codegen.
SEMIHOST_E2E_WORK = $(TEST_ARTIFACTS_DIR)/m5-e2e
SEMIHOST_E2E_LOG = .work/log/integ/test-semihost.log
SEMIHOST_PROBE_LOG = .work/log/integ/test-semihost-probe.log
MIN_ROM_PROBE = tools/qemu/min_rom_probe_046t.py

_locked-test-semihost: install-host build-bootrom test-elf test-codegen check
	@test -x $(LLVM_MC_BIN) || { echo "test-semihost: ERROR: $(LLVM_MC_BIN) not found"; exit 1; }
	@test -x $(LLVM_OBJCOPY_BIN) || { echo "test-semihost: ERROR: $(LLVM_OBJCOPY_BIN) not found"; exit 1; }
	@test -x $(QEMU_BIN) || { echo "test-semihost: ERROR: $(QEMU_BIN) not found"; exit 1; }
	@test -f $(MIN_ROM_PROBE) || { echo "test-semihost: ERROR: $(MIN_ROM_PROBE) not found"; exit 1; }
	@test -f $(BOOTROM_DIR)/bootrom.bin || { echo "test-semihost: ERROR: $(BOOTROM_DIR)/bootrom.bin not found (run 'make build-bootrom')"; exit 1; }
	@mkdir -p .work/log/integ
	@rm -rf $(SEMIHOST_E2E_WORK)
	@echo "test-semihost: [1/2] forward semihosting + cfx-level permission counter-examples"; \
	  $(PYTHON) tools/integ/run_m5_e2e.py \
	    --llvm-mc $(LLVM_MC_BIN) --llvm-objcopy $(LLVM_OBJCOPY_BIN) \
	    --qemu $(QEMU_BIN) --bootrom $(BOOTROM_DIR)/bootrom.bin \
	    --work-dir $(SEMIHOST_E2E_WORK) > $(SEMIHOST_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 30 $(SEMIHOST_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-semihost: FAIL (forward/permission rc=$$rc)"; exit $$rc; fi
	@echo "test-semihost: [2/2] 25-service table coverage (QEMU-046t probe)"; \
	  $(PYTHON) $(MIN_ROM_PROBE) --qemu $(QEMU_BIN) > $(SEMIHOST_PROBE_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 4 $(SEMIHOST_PROBE_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-semihost: FAIL (service coverage rc=$$rc)"; exit $$rc; fi
	@echo "test-semihost: PASS (forward + permission + 25-service + no-regression + INTEG registration)"

# M6 end-to-end gate (INTEG-025t).  Three components, all fail-closed:
#   1. value-level differential: the same LLVM IR runs on the host `lli` (X86)
#      and on the DADAO target; both must expose the same value channel
#      (`@main` return low byte) -- tools/testcases/diff_ir_lli.py (038t).
#   2. Embench-IoT E2E: every benchmark under <embench-src>/src/ is compiled,
#      linked and run at -O0 and -O2; judgement = guest exit code 0
#      (support/main.c returns !correct) -- tools/integ/run_embench_e2e.py.
#   3. the full generated lit MC suite (check-lit-full, 037t), driven through a
#      sub-make so its own exit code is captured.
# opt-in: NOT part of `make check` (the fast lit subset is already in check-lit).
# Tools come from the install root (ADR-0016 D9): run 'make install-host' first.
# Landing: work dirs under the SDK test-artifacts root (ADR-0016 D6 /
# Process-05 §6), resolved via paths.py (D7) -- never hardcoded.
DIFF_IR_LLI = tools/testcases/diff_ir_lli.py
EMBENCH_E2E = tools/integ/run_embench_e2e.py
EMBENCH_SRC = .work/source/embench-iot
IR_LLI_WORK = $(TEST_ARTIFACTS_DIR)/ir-lli-diff
EMBENCH_E2E_WORK = $(TEST_ARTIFACTS_DIR)/m6-embench
IR_LLI_LOG = .work/log/integ/test-m6-ir-lli.log
EMBENCH_E2E_LOG = .work/log/integ/test-m6-embench.log
LIT_FULL_LOG = .work/log/integ/test-m6-lit-full.log
_locked-test-m6: install-host
	@test -x $(HOST_TOOLS_BIN)/lli || { echo "test-m6: ERROR: $(HOST_TOOLS_BIN)/lli not found — run 'make install-host'"; exit 1; }
	@test -x $(HOST_TOOLCHAIN_BIN)/clang || { echo "test-m6: ERROR: $(HOST_TOOLCHAIN_BIN)/clang not found — run 'make install-host'"; exit 1; }
	@test -d $(EMBENCH_SRC) || { echo "test-m6: ERROR: $(EMBENCH_SRC) not found — run 'make fetch'"; exit 1; }
	@mkdir -p .work/log/integ
	@echo "test-m6: [1/3] lit full MC suite (check-lit-full)"; \
	  $(MAKE) --no-print-directory check-lit-full > $(LIT_FULL_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 5 $(LIT_FULL_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (check-lit-full rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: [2/3] lli value-level differential (host X86 vs DADAO target)"; \
	  $(PYTHON) $(DIFF_IR_LLI) --work-dir $(IR_LLI_WORK) > $(IR_LLI_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 6 $(IR_LLI_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (diff_ir_lli rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: [3/3] Embench E2E (all benchmarks x -O0/-O2; judge guest exit 0)"; \
	  $(PYTHON) $(EMBENCH_E2E) --embench-src $(EMBENCH_SRC) --work-dir $(EMBENCH_E2E_WORK) \
	    > $(EMBENCH_E2E_LOG) 2>&1; \
	  rc=$$?; \
	  tail -n 8 $(EMBENCH_E2E_LOG); \
	  if [ $$rc -ne 0 ]; then echo "test-m6: FAIL (embench rc=$$rc)"; exit $$rc; fi
	@echo "test-m6: PASS (lit full + lli value-level diff + Embench E2E)"

# Legality drift gate (SPEC-074t): verifies LEGALITY sections in
# spec/SimRISC-01..12 exactly match content rendered from contracts/.
check-legality-drift:
	@$(PYTHON) tools/spec/check_legality_drift.py

# Legality invariants gate (SPEC-103t/ISS-079): ftroot/foroot n=2 constraint
# and rule-rename registry (new id effective, old id 0 hits) per contracts/.
check-legality-invariants:
	@$(PYTHON) tools/spec/check_legality_invariants.py

# Interface alignment gate (INTEG-003t / INTEG-007t): cross-module
# contract↔implementation consistency (LLVM/QEMU/opcodes/inventory).
check-interface:
	@$(PYTHON) tools/integ/check_interface_alignment.py

# Encoding validation gate (INTEG-008t): opcodes.yaml encoding consistency
# (value/mask, field overlap, bank, legality refs, decode conflicts).
validate-encoding: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/validate_encoding.py contracts/opcodes.yaml

# InstrInfo cross-check gate (LLVM-046t / ISS-103): the committed
# DADAOInstrInfo.td (the .td truth, read from its patch) must match
# contracts/opcodes.yaml (the encoding truth).  Hermetic: reads only repo files,
# no .work/source checkout needed.
check-instrinfo:
	@$(PYTHON) tools/llvm/validate_instrinfo.py

# ISA<->backend coverage matrix drift gate (LLVM-081t; INFRA-069t 并入 L1):
# regenerates the two-layer projection from contracts/opcodes.yaml + the DADAO
# patch tree and byte-compares it against the committed matrix; drift => FAIL
# (lessons §2.11: generated projections need a drift gate).  Needs llvm-mc
# (run 'make install-host' first); counts are recomputed live, never hardcoded.
check-isa-coverage:
	@$(PYTHON) tools/llvm/gen_isa_coverage.py --check

# Scope partition gate (SPEC-086t/089t): opcodes.yaml scope ∈ {m1,fp,excluded},
# counts 152/60/15/227, excluded <=> decode ILLI (m1/fp carry none),
# fp <=> id endswith _rf, and the old M1-exclusion boolean field has disappeared.
check-scope:
	@$(PYTHON) tools/spec/check_scope.py

# Rule references bidirectional gate (SPEC-071t): checks rule_refs in opcodes.yaml
# against legality_rules.yaml (ID existence + orphan detection with exemptions).
check-rule-refs: contracts/opcodes.yaml
	@$(PYTHON) tools/spec/check_rule_refs.py

# FP semantics contract gate (SPEC-087t): scope: fp 60 条语义投影完备性
# (id 双向覆盖/12 族计数/spec_cite/required_keys/legality 双向/锚点/版本头)。
check-fp-contract:
	@$(PYTHON) tools/spec/check_fp_contract.py

# QEMU semantic execution gate (L3; SPEC-069t, INFRA-097t): runs the **full**
# carrier set through QEMU. The QEMU binary is taken from the install root
# (ADR-0016 D9; INFRA-047t): run 'make install-host' first.
# Carrier set is derived **live** from tests/vectors: every isa/*.yaml (no
# hardcoded names/counts) + the non-isa carriers rol/*.yaml + atomics/*.yaml
# (QEMU-064t: rol.* is scope m9; QEMU-067t: fence/lr/sc are not M1 identities,
# so both live outside isa/). rev/ and bitcnt/ are out of scope (M8; see
# tests/vectors/inventory.md). ISS-235 = carrier set was 3/16 of isa/.
# Derivation + structural assertions (missing 册 / duplicate basename / bad
# symlink / zero-册 / run-total vs derived-total) + self-evidence logging
# (ISS-236: carrier list, per-册 case counts, total/passed/failed, delta vs
# ISS-235's 161) live in tools/qemu/semantics_gate.py.
# Cases run in parallel via --jobs $(JOBS) (JOBS defaults to 8; never nproc).
# Exit code propagates correctly (no pipe; shell rc capture per AGENTS.md).
# D6 compliance: gate dir under TEST_ARTIFACTS_DIR, log under .work/log/qemu/.
QEMU_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate
QEMU_SEM_LOG = .work/log/qemu/check-qemu-semantics.log
QEMU_SEM_VEC_DIR = $(CURDIR)/tests/vectors
_locked-check-qemu-semantics:
	@mkdir -p .work/log/qemu || { echo "check-qemu-semantics: ERROR: cannot create .work/log/qemu"; exit 1; }
	@$(PYTHON) tools/qemu/semantics_gate.py \
	    --vectors $(QEMU_SEM_VEC_DIR) --gate-dir $(QEMU_SEM_DIR) \
	    --qemu $(QEMU_BIN) --trampoline tests/scripts/trampoline.bin \
	    --jobs $(JOBS) > $(QEMU_SEM_LOG) 2>&1; \
	  rc=$$?; \
	  tail -40 $(QEMU_SEM_LOG); \
	  if [ $$rc -ne 0 ]; then \
	    echo "check-qemu-semantics: FAIL (rc=$$rc)"; \
	    exit $$rc; \
	  fi; \
	  echo "check-qemu-semantics: PASS"

# QEMU 语义**冒烟**门控 (INFRA-058t, L2): check-qemu-semantics 的代表子集。
# 代表集按 (class, mnemonic) **机械派生**（各组取第一条，禁手工挑），计数现场统计。
# 全量留在 L3 (`check-full` → check-qemu-semantics)。
QEMU_SMOKE_WORK = $(TEST_ARTIFACTS_DIR)/harness/smoke
QEMU_SMOKE_LOG = .work/log/qemu/check-qemu-smoke.log
_locked-check-qemu-smoke:
	@mkdir -p .work/log/qemu
	@test -x $(QEMU_BIN) || { echo "check-qemu-smoke: ERROR: $(QEMU_BIN) not found — run 'make install-host' first"; exit 1; }
	@$(PYTHON) tests/scripts/run_qemu_smoke.py --qemu $(QEMU_BIN) \
	    --trampoline tests/scripts/trampoline.bin --vector-dir tests/vectors/isa \
	    --work-dir $(QEMU_SMOKE_WORK) --jobs $(JOBS) > $(QEMU_SMOKE_LOG) 2>&1; \
	  rc=$$?; \
	  tail -8 $(QEMU_SMOKE_LOG); \
	  if [ $$rc -ne 0 ]; then echo "check-qemu-smoke: FAIL (rc=$$rc)"; exit $$rc; fi; \
	  echo "check-qemu-smoke: PASS"

# 构建并行度（用户裁定 2026-10-01：限制 cc1plus 类进程）
JOBS ?= 8
