#!/bin/bash
set -euo pipefail
cd /src
mkdir -p baseline-output bin
exec > >(tee baseline-output/build.log) 2>&1
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
arm-none-eabi-gcc --version
arm-none-eabi-ld --version
gcc --version
make --version
dpkg-query -W > baseline-output/packages.txt
command=(make PLATFORM=a590 PLATFORMSUB=101b DEF_SVN_REF=6346)
printf 'Build command: %s\n' "${command[*]}"
"${command[@]}" clean
"${command[@]}" fir
test -s bin/DISKBOOT.BIN
cp bin/DISKBOOT.BIN baseline-output/
cp platform/a590/sub/101b/main.elf baseline-output/
arm-none-eabi-size platform/a590/sub/101b/main.elf | tee baseline-output/size.txt
arm-none-eabi-nm -n platform/a590/sub/101b/main.elf > baseline-output/symbols.txt
cp -r CHDK/MODULES baseline-output/
# A second clean build checks executable reproducibility, including every module.
"${command[@]}" clean
"${command[@]}" fir
cmp baseline-output/DISKBOOT.BIN bin/DISKBOOT.BIN
diff -r baseline-output/MODULES CHDK/MODULES
python3 tools/a590-baseline/manifest.py baseline-output
mkdir -p baseline-output/LICENSES
cp COPYING doc/6_ubasic_copyright.txt lib/lua/lua.h baseline-output/LICENSES/
printf 'PASS: two clean builds produced identical DISKBOOT.BIN and modules\n'
