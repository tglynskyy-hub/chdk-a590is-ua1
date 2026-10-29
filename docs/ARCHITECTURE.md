# Архітектура A590 IS / GM1.01B

## База аудиту

Аудит Task 001, 2026-10-29. CHDK **1.7.0**, upstream SVN **r6346**:
`3dbe7f81e4472e8b15eac77336206aad76454c19`, з повідомленням
`git-svn-id: https://subversion.assembla.com/svn/chdk/trunk@6346`.
Початковий `trunk`: `3d8aa1082ed57a04efa556103e49da751ba1e44c`.
План і принципи взято з `feature/a590is-101b-foundation`,
`68a3e6557` (два коміти документації поверх trunk); їхню історію збережено.
Між r6346 і цією базою змінено лише workflow дзеркалювання та два документи.
Код камери й CHDK у Task 001 не змінюється.

`COPYING` містить GPL v2. При поширенні бінарних результатів зберігати повідомлення
про авторство, текст ліцензії та забезпечувати відповідний вихідний код зі скриптами
складання за §3. Не приписувати всьому дереву автоматично «or later»: перевіряти
заголовки конкретних файлів. Lua має окреме permissive повідомлення в
`lib/lua/lua.h`, uBASIC — BSD-подібні умови в `lib/ubasic/ubasic.c` і
`doc/6_ubasic_copyright.txt`. Архів для користувача має містити ці повідомлення;
CI-артефакт є матеріалом перевірки, не готовим релізом. Canon ROM не включається.

## Шари та складання

| Шар | Джерела | Роль |
|---|---|---|
| SD loader | `loader/a590/{entry.S,main.c}`, `loader/generic/check_compat.c` | Перевірка моделі/версії, копіювання ядра, перезапуск у RAM |
| Модель | `platform/a590/` | Клавіші, палітри, об'єктив, параметри сенсора, режими |
| Firmware ABI | `platform/a590/sub/101b/` | Абсолютні адреси, task hooks, ASM-обгортки |
| Спільна логіка | `core/`, `platform/generic/`, `lib/` | GUI, конфігурація, RAW, overrides, алокатори, скрипти |
| Модулі | `modules/`, `tools/elf2flt/` | DNG, гістограми, zebra, Lua/uBASIC, файловий менеджер тощо |

Кореневий Makefile рекурсивно збирає host tools, модулі, ресурси, платформу,
firmware-specific ядро й loader. `arm_rules.inc` задає ARMv5TE/ARM946E-S та
interworking; `platform/makefile_sub.inc` застосовує ARMv4T до відповідних
обгорток, щоб отримувати сумісні виклики firmware. Ядро змішує ARM і Thumb;
модулі мають власний формат FLT, релокації й таблицю експортів.
`modules/module_load.c:validate` перевіряє архітектуру та версії API/структур.
Модулі завантажуються за потребою; `module_tick_unloader` обслуговує відкладене
вивантаження. Не можна змішувати випадкові модулі з іншого складання.

## Запуск і задачі Canon

1. Canon завантажує закодований `DISKBOOT.BIN` із підготовленої SD.
   `entry.S` викликає `check_compat`, вимикає живлення SD через існуючий MMIO
   і переходить до `my_restart`.
2. Loader копіює blob у `MEMISOSTART`, виконує наявну cache/MPU/reset-послідовність.
   `platform/a590/main.c:startup` перевіряє межі BSS, очищує її, викликає `boot`.
3. `101b/boot.c` копіює Canon data `0xFFED0D74 → 0x1900..0xDC48`, очищує
   Canon BSS до `0xA5304`, встановлює task hooks у `0x1930/0x1934`.
4. Нижня межа Canon heap стає `_end` CHDK замість `0xA5304` у стандартному
   складанні. Створюється `SpyTask`, priority `0x19`, stack `0x2000`.
   `init_file_modules_task` сигналізує готовність файлової системи.
5. `core/main.c` чекає сигнал із межею 1000 × sleep(10), відновлює конфігурацію,
   ініціалізує GUI/алокатори/PTP, обслуговує RAW, GUI і модулі.

| Адреса оригінальної задачі (101b) | CHDK replacement |
|---|---|
| `0xFFC4F0F8` | `capt_seq_task` |
| `0xFFC973E4` | `exp_drv_task` |
| `0xFFC4BBBC` | `movie_record_task` |
| `0xFFDD6404` | `filewritetask` |
| `0xFFC657B4` | `init_file_modules_task` |

PhySw підмінюється окремо через `taskcreatePhySw_my`. Це співпраця з DryOS R23,
а не заміна ОС. Задачі capture/movie/filewrite зберігають черги повідомлень,
семафори й переходи назад у Canon ROM. Значення адрес застосовні тільки до 101b.

## Ввід, GUI і локалізація

`kbd.c` читає три MMIO-регістри `0xC0220200/204/208`; keymap і маски в
`platform_kbd.h` відокремлюють клавіші, SD lock і USB. Порядок full/half shutter
у keymap важливий. Цикл PhySw має sleep(10); ALT — Print або Display.
`core/kbd_common.c` і `kbd_process.c` передають/маскують ввід для Canon,
меню та скриптів. Не переносити важкі обчислення у keyboard task.

GUI використовує `core/gui*.c`, `gui_draw_8bit.c`, палітри record/playback.
Логічний bitmap — 360×240, стандартний шрифт — 8×16. SpyTask викликає redraw
кожну четверту ітерацію зі звичайним sleep(20), але RAW/I/O/інші задачі змінюють
фактичний інтервал: це не виміряні 12.5 FPS. Під час обробки кадру GUI/гістограма
частково пригнічуються. Існують user menu, shortcuts, modular OSD і redraw flags;
їх слід використати до створення іншої навігації.

`CHDK/LANG/ukrainian.lng` вже існує, кодування Windows-1251. `lib/font/codepages.h`
і `font_8x16_uni.h` містять Є/І/Ї/Ґ та малі варіанти. `lib/lang/lang.c` зберігає
рядки через 15-бітні signed offsets: сумарний буфер має залишатися нижче приблизно
32766 байтів. `tools/makelang.c` підтримує English fallback і
`OPT_DEFAULT_LANG=ukrainian`; baseline лишає default English.
Не зберігати `.lng` як UTF-8 без зміни й перевірки всього шляху декодування.

## Фотографічний конвеєр

`capt_seq.c` викликає `shooting_expo_param_override`, remote wait, NR hook і
`capt_seq_hook_raw_here`; `exp_drv_task` використовує CHDK `apex2us` для витримки.
Спільний RAW hook повідомляє SpyTask та чекає `RAWDATA_SAVED`, віддаючи CPU
через sleep(10). SpyTask викликає `raw_process`, потім `hook_raw_save_complete`.
Тому час RAW-обробки безпосередньо подовжує блокування capture task.

`core/raw.c` викликає Lua RAW hook. `modules/rawhookops.c` надає meter,
гістограму, pixel access і EV-перетворення; читання дозволене лише в RAW hook.
Це вимірювання вже експонованого кадру, тож корекція застосовується до наступного.
`core/autoiso.c` вже має захист світлих ділянок за live histogram;
viewport не є лінійними RAW-даними.

`modules/dng.c` формує TIFF/DNG header, thumbnail, metadata, bad-pixel handling.
RevBytes task (priority `0x1A`, stack `0x400`) переставляє байти блоками 512 KiB
паралельно із записом; при єдиному RAW-буфері відновлює початковий порядок перед
поверненням Canon. Cache cleaning тут частина коректності, не зайва операція.
`filewrite.c` перехоплює open/write/close для remote capture; структура описує
три chunks та filename offset `0x2C`, не довільний доступ до ISP.

`core/shooting.c` вже має Tv/Av/ISO/subject-distance overrides і брекетинг.
`shooting.c` платформи задає таблиці ISO, aperture, shutter і mode map;
табличні межі не доводять фізичні межі overrides. `wrappers.c` використовує
`PT_MFOn/PT_MFOff` і Canon distance getters. Movie hook має optical zoom,
compression tables і mute-on-zoom; `CAM_EV_IN_VIDEO` прямо позначено як
непрацездатне на 101b. Доказів керування алгоритмами Canon demosaic/AWB/ISP немає.

## Повнота огляду та межі

Оглянуто спільні файли моделі, loader, усі групи реалізації 101b (boot/capture/
movie/filewrite, code_gen, lib, stubs, CRC, function maps і makefiles), спільні
шаблони `sub/*_hdr.c`, `FAT32_detect.S`; 100e враховано як іншу firmware, а не
джерело взаємозамінних адрес. CSV-карти й generated stubs є вихідними свідченнями,
не незалежною перевіркою ROM. Немає PRIMARY.BIN, тому відповідність кожної
інструкції фізичній firmware та повторна генерація не перевірені.

Див. [ризики та пам'ять](HARDWARE_AUDIT.md), [складання](BUILD.md),
[план перевірок](TESTING.md) і [пріоритети](OPTIMIZATION_ROADMAP.md).
