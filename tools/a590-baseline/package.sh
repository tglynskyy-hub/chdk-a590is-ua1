#!/bin/bash
set -euo pipefail
cd /src
mkdir -p sd-package-output baseline-output bin
exec > >(tee baseline-output/package.log) 2>&1
stem=CHDK-A590IS-101B-1.7.0-r6346-enhanced
source_commit=$(tr -d '\r\n' < baseline-output/source-commit.txt)
command=(make PLATFORM=a590 PLATFORMSUB=101b DEF_SVN_REF=6346 "ZIPDATE=date -u -d @$SOURCE_DATE_EPOCH -R")
for pass in 1 2; do
    "${command[@]}" firzipsubcomplete
    for profile in full photography; do
        python3 tools/a590-baseline/package.py bin/a590-101b-1.7.0-6346-full.zip \
            "baseline-output/package-$pass/$stem-$profile.zip" "$source_commit" --profile "$profile"
    done
done
for profile in full photography; do
    cmp "baseline-output/package-1/$stem-$profile.zip" "baseline-output/package-2/$stem-$profile.zip"
done
python3 tools/a590-baseline/test_package.py "baseline-output/package-2/$stem-full.zip"
python3 tools/a590-baseline/test_profiles.py baseline-output/package-2 | tee baseline-output/profile-tests.txt
python3 tools/a590-baseline/audit_locale.py > baseline-output/locale-inventory.json
for profile in full photography; do
    mkdir -p "sd-package-output/$profile"
    cp "baseline-output/package-2/$stem-$profile.zip" "baseline-output/package-2/$stem-$profile.json" \
        "baseline-output/package-2/$stem-$profile.sha256" "sd-package-output/$profile/"
    cp baseline-output/profile-comparison.json baseline-output/module-inventory.json "sd-package-output/$profile/"
done
printf 'PASS: both profile ZIPs identical across two clean upstream builds\n'
