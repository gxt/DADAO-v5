#!/bin/sh
# Extract gem5 build dependencies under .work/ without changing the host.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. /etc/os-release
if [ "$ID" != ubuntu ]; then
    echo "bootstrap-ubuntu-deps: Ubuntu is required" >&2
    exit 2
fi
pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
root="$repo_root/.work/deps/gem5/root"
pkgs="$repo_root/.work/deps/gem5/pkgs"
mkdir -p "$root" "$pkgs"
(cd "$pkgs" && apt download scons m4 zlib1g-dev python3-yaml "python${pyver}-dev" "libpython${pyver}-dev")
for deb in "$pkgs"/*.deb; do
    dpkg-deb -x "$deb" "$root"
done
arch=$(gcc -dumpmachine)
libdir="$root/usr/lib/$arch"
host_libdir="/usr/lib/$arch"
ln -sfn "$host_libdir/libpython${pyver}.so.1.0" "$libdir/libpython${pyver}.so.1"
ln -sfn "$host_libdir/libz.so.1" "$libdir/libz.so.1.3.1"
echo "bootstrap-ubuntu-deps: extracted gem5 dependencies to $root"
