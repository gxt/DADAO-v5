# -*- Python -*-
# GENERATED suite config for tests/llvm/lit/MC/DADAO-gen (TESTCASES-037t).
# Resolves llvm-mc/llvm-objdump/FileCheck from the install-root host toolchain.
import os
import sys
import lit.formats

config.name = "DADAO-MC-gen"
config.test_source_root = os.path.dirname(__file__)
config.suffixes = [".s"]
config.test_format = lit.formats.ShTest(False)

here = os.path.dirname(os.path.abspath(__file__))
root = here
while (root != os.path.dirname(root)
       and not os.path.isfile(os.path.join(root, "manifests",
                                           "install-dirs.lock.toml"))):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "tools", "infra"))
import paths as dadao_paths

tools_dir = getattr(config, "llvm_tools_dir", None) or os.environ.get(
    "LLVM_TOOLS_DIR", "") or str(dadao_paths.host_toolchain_bin())
if not os.path.isdir(tools_dir):
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; run 'make install-host' first")
tools_dir = os.path.abspath(tools_dir)
for tool in ("llvm-mc", "llvm-objdump", "llvm-readobj", "FileCheck", "not"):
    config.substitutions.append(("%" + tool.replace("-", "_"), os.path.join(tools_dir, tool)))

config.test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
