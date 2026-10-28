# -*- Python -*-
#
# lit configuration for DADAO CodeGen (L2 structural) tests.
#
# The suite drives `llc` and checks its output with `FileCheck`; the two vector
# kinds are LLVM IR (`.ll`) and post-RA MIR (`.mir`).  Mirrors
# tests/unit/llvm/lit/MC/DADAO/lit.cfg.py.
#
# It is wired into `make check-lit` by INTEG-016t (this also resolves ISS-152).

import os
import sys
import lit.util
import lit.formats

# name: The name of this test suite.
config.name = "DADAO-CodeGen"

# test_source_root: The root path where tests are located.
config.test_source_root = os.path.dirname(__file__)

# suffixes: `.ll` (IR -> llc) and `.mir` (MIR -> llc -run-pass=...).
config.suffixes = [".ll", ".mir"]

# Use ShTest format (standard for llc/FileCheck-driven tests).
config.test_format = lit.formats.ShTest(False)

# Resolve the repo root (the dir holding the install-dirs manifest) and the
# single-source-of-truth path module (ADR-0016 D7), used both to locate the
# tools and to place lit's scratch output.
here = os.path.dirname(os.path.abspath(__file__))
root = here
while (root != os.path.dirname(root)
       and not os.path.isfile(os.path.join(root, 'manifests',
                                           'install-dirs.lock.toml'))):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, 'tools', 'infra'))
import paths as dadao_paths

# Toolchain selection (ADR-0016 D9 / ISS-300).  The install root is the single
# source of truth for the DADAO toolchain: `make install-host` refreshes it and
# the gates are meant to read it.  Precedence:
#
#   1. `config.llvm_tools_dir` -- set by a lit site config (the blessed way to
#      point at another tree, e.g. the build tree of a from-source lit run);
#   2. an explicit `LLVM_TOOLS_DIR` overlay -- a *deliberate* bypass of the
#      install root, so it needs the opt-in `DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1`
#      and is identity-checked (dadao must be a registered target of that `llc`;
#      the tools must be executable; version + sha256 are printed);
#   3. the install root's host toolchain bin.
#
# A bare `LLVM_TOOLS_DIR` is rejected loudly.  Silently preferring it is what
# lets a stale or foreign toolchain look green while `make install-host` was
# never run (LLVM-125t used the overlay for exactly that reason and had to
# remember it; ISS-300 records the class of mistake).
site_tools_dir = getattr(config, 'llvm_tools_dir', None)
env_tools_dir = os.environ.get('LLVM_TOOLS_DIR', '')
allow_override = os.environ.get('DADAO_LIT_ALLOW_TOOLS_OVERRIDE', '') == '1'
install_root = str(dadao_paths.host_toolchain_bin())

if env_tools_dir and not allow_override:
    sys.exit(
        'lit.cfg.py: LLVM_TOOLS_DIR is not a silent override any more '
        '(ADR-0016 D9 / ISS-300).\n'
        '  LLVM_TOOLS_DIR=' + env_tools_dir + '\n'
        "  Run 'make install-host' and drop the override, or set "
        'DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1 to deliberately test a different '
        'toolchain (it is then identity-checked: dadao target, version, '
        'sha256)')

if site_tools_dir and env_tools_dir:
    print('lit.cfg.py: lit site config wins over LLVM_TOOLS_DIR (site config '
          'is the blessed override)', file=sys.stderr)

tools_dir = site_tools_dir or (env_tools_dir if allow_override else '')
if not tools_dir and os.path.isdir(install_root):
    tools_dir = install_root

if not tools_dir:
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; "
             "run 'make install-host' first")

# Ensure absolute paths so lit's internal shell can find the tools.
tools_dir = os.path.abspath(tools_dir)
llc = os.path.join(tools_dir, "llc")
file_check = os.path.join(tools_dir, "FileCheck")
not_tool = os.path.join(tools_dir, "not")

# Identity check for any tree other than the install root (site config or the
# opt-in overlay): the bypass must be declared, not silent.
if tools_dir != os.path.abspath(install_root):
    import hashlib
    import subprocess

    if not os.path.isdir(tools_dir):
        sys.exit('lit.cfg.py: toolchain directory ' + tools_dir +
                 ' does not exist (the opt-in overlay must be built/installed)')
    missing = [name for name, path in (('llc', llc), ('FileCheck', file_check),
                                       ('not', not_tool))
               if not (os.path.isfile(path) and os.access(path, os.X_OK))]
    if missing:
        sys.exit('lit.cfg.py: toolchain directory ' + tools_dir +
                 ' lacks executable(s): ' + ', '.join(missing))

    try:
        version = subprocess.run([llc, '--version'], capture_output=True,
                                 text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        sys.exit('lit.cfg.py: cannot run ' + llc + ' --version: ' + str(exc))
    version_text = version.stdout + version.stderr
    if version.returncode != 0 or 'dadao' not in version_text.lower():
        sys.exit('lit.cfg.py: ' + llc + ' --version (rc=' +
                 str(version.returncode) + ') does not report a registered '
                 'dadao target; refusing to test with a foreign toolchain:\n' +
                 version_text)

    fingerprint = []
    for name, path in (('llc', llc), ('FileCheck', file_check),
                       ('not', not_tool)):
        digest = hashlib.sha256()
        with open(path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                digest.update(chunk)
        fingerprint.append(name + '=' + digest.hexdigest())
    print('lit.cfg.py: toolchain ' + tools_dir + ' (NOT the install root ' +
          install_root + ')', file=sys.stderr)
    print('lit.cfg.py: ' + ' '.join(version_text.splitlines()[:2]), file=sys.stderr)
    print('lit.cfg.py: sha256 ' + ' '.join(fingerprint), file=sys.stderr)

config.substitutions.append(("%llc", llc))
config.substitutions.append(("%FileCheck", file_check))
config.substitutions.append(("%not", not_tool))

# test_exec_root: lit's scratch output goes under the SDK test-artifacts root
# (.dadao/tests/lit-output/<name>, ADR-0016 D6), resolved through
# tools/infra/paths.py (D7), so tests never pollute the source tree.
config.test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
