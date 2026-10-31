#!/bin/bash
set -euo pipefail
cd /src
mkdir -p sd-package-output baseline-output bin
exec > >(tee baseline-output/package.log) 2>&1
name=CHDK-A590IS-101B-1.7.0-r6346-full.zip
source_commit=$(tr -d '\r\n' < baseline-output/source-commit.txt)
command=(make PLATFORM=a590 PLATFORMSUB=101b DEF_SVN_REF=6346 "ZIPDATE=date -u -d @$SOURCE_DATE_EPOCH -R")
for pass in 1 2; do
    "${command[@]}" firzipsubcomplete
    python3 tools/a590-baseline/package.py bin/a590-101b-1.7.0-6346-full.zip \
        "baseline-output/package-$pass/$name" "$source_commit"
done
cmp "baseline-output/package-1/$name" "baseline-output/package-2/$name"
python3 tools/a590-baseline/test_package.py "baseline-output/package-2/$name"
cp "baseline-output/package-2/$name" "baseline-output/package-2/${name%.zip}.json" \
    "baseline-output/package-2/${name%.zip}.sha256" sd-package-output/
printf 'PASS: complete installation ZIP identical across two clean upstream builds\n'
