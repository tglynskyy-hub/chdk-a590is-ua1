# Відтворюване складання A590 IS 1.01B

## Обсяг і середовище

Baseline — CHDK 1.7.0 r6346 із незміненим camera/core/module source.
`arm_rules.inc` дозволяє GCC major 4, 5, 8, 9, 10, 11; єдиного обов'язкового
patch-релізу upstream не задає. Для цього baseline обрано ARM GCC **8.3.1**,
як у `tools/docker/autobuild/README.TXT`, а не застарілий generic Docker recipe
на Debian stretch/GCC 5.4.1. Debian package:
[`gcc-arm-none-eabi` bullseye](https://packages.debian.org/bullseye/gcc-arm-none-eabi).

Container: Linux amd64, Debian bullseye, base digest
`sha256:e5b6442dd2e9684cf5e87d8338b5968f3b348636fc0be6d7850a381e3731a2bd`.
APT archive зафіксовано на `20251229T000000Z`; перевірка підписів пакетів лишається
ввімкненою, вимкнено лише expiry історичного Release. libc6/libc-bin усередині
ізольованого build container узгоджено з archive (`2.31-13+deb11u11`). Це legacy
build image, не контейнер для мережевого сервісу. Windows/system packages не змінено.

Dependencies: host gcc/libc development headers, binutils (через dependencies),
gcc-arm-none-eabi, GNU make, shell/coreutils/sed/awk/grep/diff, zip, Python 3.
Capstone не потрібен для складання A590 зі збереженими stubs; firmware dumps і
FI2 keys не потрібні для стандартного `DISKBOOT.BIN`. CHDK має власні libc headers,
ARM libgcc постачає compiler. `dpkg-query -W` записує точні resolved versions.

## Команди

З чистого checkout, у його корені, на машині з Docker Linux containers:

```sh
docker build --platform linux/amd64 -t a590-baseline tools/a590-baseline
docker run --rm --platform linux/amd64 -v "$PWD:/src" a590-baseline bash tools/a590-baseline/build.sh
```

PowerShell bind mount: `-v "${PWD}:/src"`. Результат у `baseline-output/`.
GitHub Actions використовує той самий recipe, а action revisions pinned за SHA.
На локальній Windows Docker/WSL/ARM GCC/make не були встановлені; реальне
складання виконується у GitHub Actions, не називається локально виконаним.

Скрипт послідовно виконує:

```sh
make PLATFORM=a590 PLATFORMSUB=101b DEF_SVN_REF=6346 clean
make PLATFORM=a590 PLATFORMSUB=101b DEF_SVN_REF=6346 fir
```

Потім повторює clean/fir, порівнює DISKBOOT і всі FLT. EXMEM/ARAM/FI2,
compat-check disabling, native Lua forcing не ввімкнено. Defaults із
`buildconf.inc` збережено: curves/debug/PTP, default English тощо.
`SOURCE_DATE_EPOCH=1766992455`, `TZ=UTC`, `LC_ALL=C` фіксують compiler timestamps
і порядок. Це не змінює boot code. Timestamp прив'язаний до r6346, не до часу
користувацького встановлення. ZIP із timestamp не оголошується bit-reproducible:
перевіряються executable binary та модулі.

## Артефакти і перевірка

`bin/DISKBOOT.BIN` — encoded SD boot image, dancingbits version 1.
`platform/a590/sub/101b/main.elf` — debug/inspection image, не файл для SD boot.
`CHDK/MODULES/*.flt` — узгоджені динамічні модулі. `PS.FIR` для VxWorks тут
не застосовується; `PS.FI2` не генерується без OPT_FI2/keys і не потрібен baseline.
Не перейменовувати ELF у DISKBOOT. CI artifact із модулями не містить усього
user resource tree; для SD потрібен повний пакет CHDK цього самого source/build.

`manifest.json` містить SHA-256 і розмір кожного binary/ELF/module;
`size.txt` — text/data/BSS, `symbols.txt` — linker symbols,
`packages.txt` — точні пакети, `source-commit.txt` — checkout SHA,
`container.json` — image metadata, `build.log` і `container-build.log` — журнали.
Перевіряти manifest повторним хешуванням завантажених файлів.

## Історія діагностики

1. Initial container: mutable base мав libc6 u14, archive — libc6-dev u11;
   apt dependency conflict, компіляція ще не почалася.
2. Security snapshot 20261028: index доступний, частина .deb повертала HTTP 404.
   Це збій отримання залежностей, не помилка A590.
3. Fixed base digest + complete older archive + explicit matching libc versions.

4. Компіляція створила main.elf, але makefile_sub.inc намагався записати
   `bin/caminfo.txt` до створення `bin/`. Git не переносить порожні каталоги.
   Мінімальна корекція — `mkdir -p bin` у wrapper до make; firmware source
   і upstream makefiles не змінено.

## Перевірений результат

**SUCCESS**, [CI run 40958015984](https://github.com/tglynskyy-hub/chdk-a590is-ua1/actions/runs/40958015984),
source `987e11b6d675d4251bac3a0668a876b68a34e35e`, 2026-10-29.
Два clean/fir дали побайтово однакові DISKBOOT.BIN та **38 FLT**.
Завантажений ZIP додатково перевірено локально: SHA-256 архіву відповідає GitHub
artifact digest; усі **40** binary/ELF/module файлів відповідають manifest.
Фізична камера не тестувалася.

| Компонент | Фактична версія |
|---|---|
| ARM compiler | arm-none-eabi-gcc 8.3.1 20190703, revision 273027 |
| Debian compiler package | 15:8-2019-q3-1+b1 |
| ARM binutils | 2.35.2, package 2.35.2-2+14+b2 |
| Host gcc | 10.2.1 20210110, Debian 10.2.1-6 |
| GNU Make | 4.3, package 4.3-4.1 |
| Python package | 3.9.2-3 |
| zip package | 3.0-12 |

| Артефакт | Bytes | SHA-256 |
|---|---:|---|
| DISKBOOT.BIN | 131473 | `e5e09ba13804d2f5b12c08f5558676ef2eb124896458595ef619313ddf5e7f86` |
| main.elf | 254352 | `5cc1d344fad87a0a01a2d38e1dceb1421e24d4fadc557dd85a637f169c5083c8` |
| Run-4 artifact ZIP (ID 12934775852) | 450145 | `349a28d197b0c5af7ec3a04a2b3529afd40e0779c8e071da072e1dbb943f3923` |

Модулі: 38 файлів, сумарно 266912 bytes. Кожен розмір і SHA-256 у
[baseline-manifest.json](evidence/baseline-manifest.json).
ELF: text 88148, data 42212, BSS 14004, total 144364 bytes.
Повний [журнал](evidence/baseline-build.log), [пакети](evidence/baseline-packages.txt),
[sections](evidence/baseline-size.txt) збережені в Git, щоб дані пережили expiry
Actions artifacts. ZIP — evidence package, не готовий SD release.

У журналі двох складань **0 compiler `warning:` diagnostics** зі стандартними
upstream flags. Це не `-Werror` і не доказ відсутності UB: upstream вимикає
частину warnings, OPT_WARNINGS не задано. По три `CAUTION` на складання означають
відсутні reference dumps/PRIMARY.BIN і використання збережених signatures/stubs.
Адреси не регенеровано й не перевірено проти фізичного ROM. Runner також повідомляє
про Node20 action deprecation (host infrastructure, не ARM compilation).

Нові запуски записують `size-changes.json` відносно baseline: additions/removals,
byte delta та hash-only changes; CI не вигадує safe RAM threshold. Після зміни
toolchain оновлення baseline вимагає явного аналізу. Перевірка незмінності source
після make додана окремим CI step. Ліцензійні повідомлення додаються до наступних
artifact packages в `LICENSES/`; джерела відповідають `source-commit.txt` у цьому repo.
