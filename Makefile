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
        build-qemu build-qemu-reconfig build-gem5 build-bootrom install-host docker-image docker-shell check \
        validate-vectors check-spec-refs check-spec-drift check-asm-list \
        check-legality-drift check-interface validate-encoding check-scope \
        check-rule-refs check-fp-contract check-instrinfo \
        check-dirs check-no-residue check-spec-readonly check-cfx-aliases check-asm-prose check-lit \
        check-lit-full \
        test-codegen test-elf test-semihost test-m6 \
        check-patch-tree check-index-blobs check-source-state check-asm-list-drift size-report \
        check-tasks check-spec-codeblocks check-legality-invariants

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
	@echo "  make install-host    Install needed tools: cross toolchain (clang/llc/ld.lld …) into \$$(HOST_TOOLCHAIN_BIN) + host lli into \$$(HOST_TOOLS_BIN); adr-0016 D3/D4/D5/D11"
	@echo "  make docker-image    Build the development image ($(DOCKER_TAG))"
	@echo "  make docker-shell    Open a shell in the development image"
	@echo "  make clean-work      Remove generated .work content only"
	@echo "  make validate-vectors  Validate tests/vectors schema/inventory/coverage"
	@echo "  make check           Run repository-level structural checks"
	@echo "  make check-interface  Check cross-module interface alignment"
	@echo "  make validate-encoding  Validate opcodes.yaml encoding consistency"
	@echo "  make check-scope     Check opcodes.yaml scope partition (m1/fp/excluded; SPEC-086t)"
	@echo "  make check-spec-drift  Audit contract provenance against README versions"
	@echo "  make check-spec-refs Audit spec references in contract-*.md (standalone)"
	@echo "  make check-asm-list  Check spec embedded assembly table consistency"
	@echo "  make check-asm-prose  Check prose assembly format gate (strict mode)"
	@echo "  make check-spec-codeblocks  Check spec prose \`\`\`simrisc blocks vs opcodes.yaml (ISS-077)"
	@echo "  make check-lit        Run lit MC + CodeGen + E2E tests (requires install-host)"
	@echo "  make check-lit-full   Run full generated lit MC suite from contracts/opcodes.yaml (opt-in; TESTCASES-037t)"
	@echo "  make test-codegen     Run M3 CodeGen E2E gate (llc->llvm-mc->objcopy->qemu; INTEG-012t)"
	@echo "  make test-elf         Run M4 multi-TU/multi-section ELF E2E gate (llc->ld.lld->qemu; INTEG-016t)"
	@echo "  make test-semihost    Run M5 SEE/semihosting E2E gate (bootrom+bin via -semihosting, console+SYS_EXIT, 25 svc; INTEG-020t)"
	@echo "  make test-m6          Run M6 E2E gate (lli value-level diff + Embench all benches -O0/-O2 + full lit MC suite; opt-in, INTEG-025t)"
	@echo "  make check-patch-tree  Check component patch tree (spec/Process-01, 9 assertions)"
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

LLVM_MC_FULL_TARGETS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen llc lli clang
LLVM_MC_LITE_TARGETS = llvm-mc llvm-objdump FileCheck not

build-mc: manifest-check
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
build-mc-lite: manifest-check
	@$(call component-enabled,llvm-project) || { \
	  echo "build-mc-lite: component 'llvm-project' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	@$(LLVM_CONFIGURE)
	ninja -j$(JOBS) -C $(LLVM_BUILD) $(LLVM_MC_LITE_TARGETS)
	@echo "build-mc-lite: PASS"

# build-mc-reconfig: force a cmake re-run (drops the config stamp first).
build-mc-reconfig: manifest-check
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

build-lld: manifest-check
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
build-qemu: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu: component 'qemu' is not enabled / commit pending (manifests/components.lock.toml); refusing to fake success"; \
	  exit 1; \
	}
	@if [ -f $(QEMU_BUILD)/build.ninja ]; then \
	  echo "build-qemu: build.ninja exists, skipping configure (use build-qemu-reconfig to force)"; \
	else \
	  mkdir -p $(QEMU_BUILD) && \
	  cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	    --target-list=dadao-softmmu \
	    --enable-tcg \
	    --disable-werror; \
	fi
	$(MAKE) -C $(QEMU_BUILD) -j$(JOBS)
	@echo "build-qemu: PASS"

# build-qemu-reconfig: always re-run configure (for when meson.build changes).
build-qemu-reconfig: manifest-check
	@$(call component-enabled,qemu) || { \
	  echo "build-qemu-reconfig: component 'qemu' is not enabled / commit pending; refusing to fake success"; \
	  exit 1; \
	}
	mkdir -p $(QEMU_BUILD)
	cd $(QEMU_BUILD) && $(CURDIR)/$(QEMU_SRC)/configure \
	  --target-list=dadao-softmmu \
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
# llvm-readobj/FileCheck/not (lit MC), llc (CodeGen), llvm-objcopy (test-codegen),
# lld + ld.lld (test-elf), clang (M6 cross compiler, INFRA-050t), qemu-system-dadao
# (D4), llvm-lit (lit runner).  No full `cmake --install`.
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
# NOTE (concurrency): only install-host's *writes* are made race-safe here.
# Running *gate* targets (test-elf / test-semihost / check / …) concurrently in
# one worktree remains UNSUPPORTED — they share the build trees and the SDK
# artifact dirs under $(TEST_ARTIFACTS_DIR); see AGENTS.md ("并行任务上限").
# Run them serially.
HOST_LLVM_TOOLS = llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not llc clang
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
# resource-dir `lib/` (compiler-rt builtins) has no consumer in M6 and is
# deliberately not installed.  These headers are part of the *host* compiler
# (D3), not the target sysroot (D5) — ADR-0016 D3/D5/D11 scope is unchanged.
CLANG_RESOURCE_VER := $(shell ls -1 $(LLVM_BUILD)/lib/clang 2>/dev/null | head -n1)
CLANG_HEADERS_SRC  = $(LLVM_BUILD)/lib/clang/$(CLANG_RESOURCE_VER)/include
CLANG_RESOURCE_DIR = $(HOST_TOOLCHAIN_DIR)/lib/clang/$(CLANG_RESOURCE_VER)

install-host: build-mc build-lld build-qemu
	@mkdir -p $(HOST_TOOLCHAIN_BIN) $(HOST_TOOLS_BIN)
	@for t in $(HOST_LLVM_TOOLS); do \
	  $(call atomic-install,$(LLVM_BUILD)/bin/$$t,$(HOST_TOOLCHAIN_BIN)/$$t) || exit 1; \
	done
	@$(call atomic-install,$(LLVM_BUILD)/bin/lld,$(HOST_TOOLCHAIN_BIN)/lld)
	@ln -sf lld $(HOST_TOOLCHAIN_BIN)/ld.lld
	@$(call atomic-install,$(LLVM_BUILD)/bin/lli,$(HOST_TOOLS_BIN)/lli)
	@$(call atomic-install,$(QEMU_BUILD)/qemu-system-dadao,$(HOST_TOOLCHAIN_BIN)/qemu-system-dadao)
	@rm -rf $(HOST_LIT_DIR)
	@mkdir -p $(HOST_LIT_DIR)
	@cp -a $(LLVM_SRC)/utils/lit/lit $(HOST_LIT_DIR)/lit
	@rm -rf $(HOST_LIT_DIR)/lit/__pycache__
	@printf '%s\n' '#!/usr/bin/env python3' '# DADAO install-root lit launcher (INFRA-047t): the lit package is installed in ../share/lit' 'import os' 'import sys' '' '_prefix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))' 'sys.path.insert(0, os.path.join(_prefix, "share", "lit"))' '' 'from lit.main import main' '' 'if __name__ == "__main__":' '    main()' > $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@chmod +x $(HOST_TOOLCHAIN_BIN)/llvm-lit
	@test -d $(CLANG_HEADERS_SRC) || { echo "install-host: ERROR: clang builtin headers not found at $(CLANG_HEADERS_SRC) — build tree incomplete (run 'make build-mc')"; exit 1; }
	@mkdir -p $(CLANG_RESOURCE_DIR)
	@$(call atomic-install-dir,$(CLANG_HEADERS_SRC),$(CLANG_RESOURCE_DIR)/include)
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
build-bootrom:
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

docker-image:
	docker build -t $(DOCKER_TAG) containers/dev

docker-shell:
	docker run --rm -it -v "$(PWD):/workspace" $(DOCKER_TAG) /bin/bash

clean-work:
	@$(PYTHON) tools/infra/clean_work.py

check: manifest-check validate-vectors check-spec-drift check-patch-tree check-index-blobs check-asm-list check-asm-list-drift check-asm-prose check-spec-codeblocks check-legality-drift check-legality-invariants check-interface validate-encoding check-scope check-rule-refs check-fp-contract check-instrinfo check-qemu-semantics check-cfx-aliases check-dirs check-no-residue check-spec-readonly check-lit
	@$(PYTHON) tools/infra/check_issues.py
	@$(PYTHON) -m compileall -q tools
	@echo "repository checks: PASS"

# Vector schema/inventory/coverage gate (TESTCASES-002t). Requires the M1
# encoding table (contracts/opcodes.yaml) to exist.
validate-vectors: contracts/opcodes.yaml
	@$(PYTHON) tools/testcases/validate_vectors.py

# spec drift check (INFRA-012t): fail-closed provenance audit for contract-*.md.
check-spec-drift:
	@$(PYTHON) tools/infra/check_spec_drift.py

# 组件补丁集校验 (2026-09-23): 树形补丁集断言（现 9 条），见 spec/Process-01-组件补丁组织与构建编排.md。
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
# 规则见 spec/Process-01 §11「组件源文件规模约定」。
size-report:
	@$(PYTHON) tools/infra/size_report.py

# 待收尾任务自查 (INFRA-029t): 报告型，列出「完成区已填 + 待验收」的漏 /complete 任务。
# 默认退出码 0，不并入 `make check` 阻断路径；--strict 时命中 >0 则失败。
check-tasks:
	@$(PYTHON) tools/infra/check_tasks.py

# spec 引用审计 (INFRA-011t): Check 1 引用有效性 + Check 2 无引用规范断言.
# Standalone target, not part of `make check`.
check-spec-refs:
	@$(PYTHON) tools/infra/check_spec_refs.py

# cfx alias drift gate (SPEC-075t): verify .tao/knowledge/contract-cfx-aliases.md is up-to-date.
check-cfx-aliases:
	@$(PYTHON) tools/spec/check_cfx_aliases.py

# Install/product directory path guard (INFRA-019t): validates
# manifests/install-dirs.lock.toml and scans for symlink prefix violations.
check-dirs:
	@$(PYTHON) tools/infra/check_dirs.py

# Residue gate (INFRA-025t): detect unexpected untracked temp files.
check-no-residue:
	@$(PYTHON) tools/infra/check_dirs.py --residue

# spec 目录只读锁 (SPEC-119t): 只读册 sha256 校验；失配 ⇒ FAIL（须先取用户授权并同步改锁）。
# 规则见 spec/Process-06-spec目录保护规范.md §5。
check-spec-readonly:
	@$(PYTHON) tools/infra/check_spec_readonly.py

# Spec embedded assembly list consistency (SPEC-037t).
check-asm-list:
	@$(PYTHON) tools/spec/check_asm_list_consistency.py

# Assembly-list drift gate (INFRA-027t): verify .tao/knowledge/contract-asm-list.md
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
LIT_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-lit
check-lit:
	@test -x $(LIT_BIN) || { echo "check-lit: ERROR: $(LIT_BIN) not found — run 'make install-host' first"; exit 1; }
	$(LIT_BIN) tests/llvm/lit/MC/DADAO tests/llvm/lit/CodeGen/DADAO tests/e2e/lit -v

# lit 全量档 (TESTCASES-037t): 由 contracts/opcodes.yaml 机械生成的全部 lit MC
# 编码用例（快档受控子集已随 check-lit 进 `make check`；本目标承载规模，
# **opt-in，不进 `make check`**）。先跑结构+编码检查器，再跑 lit。
# 计数不写死：由 check_lit_gen.py / llvm-lit **现场统计**；本目标不设硬编码门限。
check-lit-full:
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
test-codegen: install-host
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
test-elf: install-host
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

test-semihost: install-host build-bootrom test-elf test-codegen check
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
test-m6: install-host
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

# QEMU semantic execution gate (SPEC-069t): runs ISA semantic test vectors
# through QEMU. The QEMU binary is taken from the install root (ADR-0016 D9;
# INFRA-047t): run 'make install-host' first.
# Runs all semantic/boundary cases in reg-shift-extend + reg-compare.
# Uses symlinked temp dir + --batch for full coverage; cases run in parallel
# via --jobs $(JOBS) (JOBS defaults to 8; never nproc/full-core).
# Exit code propagates correctly (no pipe; shell rc capture per AGENTS.md).
# D6 compliance: gate dir under TEST_ARTIFACTS_DIR, log under .work/log/qemu/.
# ISS-089: the gate dir is transient, so the setup must be explicit — create it,
# then verify each vector is a symlink resolving to the expected file. ln errors
# are NOT swallowed (a silent failure would feed the gate the wrong/empty input).
QEMU_SEM_DIR = $(TEST_ARTIFACTS_DIR)/harness/gate
QEMU_SEM_LOG = .work/log/qemu/check-qemu-semantics.log
QEMU_SEM_VEC_DIR = $(CURDIR)/tests/vectors/isa
check-qemu-semantics:
	@mkdir -p .work/log/qemu || { echo "check-qemu-semantics: ERROR: cannot create .work/log/qemu"; exit 1; }; \
	  mkdir -p $(QEMU_SEM_DIR) || { echo "check-qemu-semantics: ERROR: cannot create gate dir $(QEMU_SEM_DIR) (path occupied?)"; exit 1; }; \
	  for v in reg-shift-extend.yaml reg-compare.yaml; do \
	    [ -e $(QEMU_SEM_VEC_DIR)/$$v ] || { echo "check-qemu-semantics: ERROR: vector $(QEMU_SEM_VEC_DIR)/$$v not found"; exit 1; }; \
	    ln -sf $(QEMU_SEM_VEC_DIR)/$$v $(QEMU_SEM_DIR)/$$v || { echo "check-qemu-semantics: ERROR: failed to symlink $$v into $(QEMU_SEM_DIR)"; exit 1; }; \
	    [ -L $(QEMU_SEM_DIR)/$$v ] || { echo "check-qemu-semantics: ERROR: $(QEMU_SEM_DIR)/$$v is not a symlink (stale/occupied path?)"; exit 1; }; \
	    [ "$$(readlink -f $(QEMU_SEM_DIR)/$$v)" = "$$(readlink -f $(QEMU_SEM_VEC_DIR)/$$v)" ] || { echo "check-qemu-semantics: ERROR: $(QEMU_SEM_DIR)/$$v does not point to $(QEMU_SEM_VEC_DIR)/$$v"; exit 1; }; \
	  done; \
	  echo "check-qemu-semantics: running shift+compare (all cases)..."; \
	  $(PYTHON) tests/scripts/run_qemu_test.py --batch $(QEMU_SEM_DIR) --jobs $(JOBS) --qemu $(QEMU_BIN) > $(QEMU_SEM_LOG) 2>&1; \
	  rc=$$?; \
	  tail -5 $(QEMU_SEM_LOG); \
	  if [ $$rc -ne 0 ]; then \
	    echo "check-qemu-semantics: FAIL (rc=$$rc)"; \
	    rm -rf $(QEMU_SEM_DIR); \
	    exit $$rc; \
	  fi; \
	  rm -rf $(QEMU_SEM_DIR); \
	  echo "check-qemu-semantics: PASS"

# 构建并行度（用户裁定 2026-10-01：限制 cc1plus 类进程）
JOBS ?= 8
