# Дорожня карта оптимізації

Пріоритет — вимірювана фотографічна користь, стабільність і сумісність.
Енергоспоживання не оптимізуємо. Нижче — гіпотези та критерії приймання,
не вже отримані покращення. Кожна функція має бути вимикана й не ламати Canon,
існуючі Lua/uBASIC scripts і FLT modules.

| Ранг | Напрям і повторне використання | Користь / здійсненність | Ресурси та ризики | Критерій |
|---|---|---|---|---|
| 1 | Завершення української локалізації: `ukrainian.lng`, Win1251, existing fonts | Висока UX / висока | Буфер рядків <32766 B, тимчасові allocations, ширина меню | Всі потрібні IDs, format specifiers сумісні, ЄІЇҐ/єіїґ і меню на LCD без обрізання |
| 2 | Highlight-aware bracket script на `rawop.meter/create_histogram`, Tv96 overrides | Висока фото / середня-висока | RAW hook затримує наступний етап; sparse ROI, bounded histogram, timeout; перший кадр уже знято | Менше clipped photosites на однакових сценах, повна серія без втрат, логи latency |
| 3 | Зручний RAW/DNG workflow та перевірка metadata | Висока / висока | Єдиний буфер, час запису, cache ordering, SD errors | Валідні DNG, правильні CFA/crop/EXIF, незмінений JPEG, прийнятний shot interval |
| 4 | User menu і shortcuts замість нового GUI engine | Висока UX / висока | Невеликий config/code budget; регресія ALT/half-shutter | Менше натискань до RAW/Tv/ISO/bracket, звичні Canon controls збережено |
| 5 | Focus bracketing на existing distance overrides і MF wrappers | Висока macro / середня | Невирішений focus_busy address, lens settling, DoF calibration | Реальні монотонні площини фокуса, повторюваність, AF після виходу працює |
| 6 | Low-light automation: fixed exposure series, dark frames, offline stacking | Висока / висока для automation | SD storage і час, рух об'єктів; не тримати кілька RAW у heap | SNR/деталі на matched сценах, відсутність clipping/ghosting у заявлених умовах |
| 7 | Live metering/Auto ISO tuning на existing `autoiso.c`, histogram/zebra | Середня-висока / середня | Viewport нелінійний; Canon AE feedback, flash/mode constraints | Порівняти зі звичайним Auto ISO на контрастних сценах; без oscillation |
| 8 | Менше redraw через existing dirty flags/OSD scheduling | Середня / середня | Canon може перемальовувати поверх CHDK; відновлення overlays | Менша CPU/latency на однаковому UI, без stale pixels у record/playback |
| 9 | Allocation/копіювання: module buffer reuse, bounded scratch, DNG chunk tuning | Потенційна / середня | Fragmentation, task lifetime, single RAW buffer; спершу profiling | Lower peak allocation або latency без зменшення largest free block margin |
| 10 | Вибіркова ARM-оптимізація packing/histograms/byte reverse | Невідома / низька до profiling | ARMv5TE, alignment, interworking, cache coherence | Bit-exact output і стабільне прискорення гарячого шляху на камері |

## Що вже реалізовано

`core/shooting.c` має Tv/Av/ISO/subject-distance bracketing; `core/autoiso.c`
враховує live highlights. `modules/rawhookops.c` має RAW meter/histogram,
`raw_merge.c` — RAW merge, `dng.c` — паралельний byte reversal/write,
`modules/module_load.c` — reuse буфера і lazy load/unload. `lib/armutil` уже
містить низькорівневі primitives. Не дублювати ці механізми.

Static inventory regex для числових рядків дає 672 English IDs і 435 Ukrainian IDs,
237 відсутніх, без duplicate/extra IDs; [повний перелік](evidence/locale-inventory.json).
Відтворення: `python3 tools/a590-baseline/audit_locale.py`.
Потрібен змістовний аудит, бо присутність ID не означає завершений переклад,
а не всі загальні рядки використовуються A590. Поточний сумарний верхній estimate
рядків Ukrainian із NUL — 8437 bytes (до escape decoding і фільтрації port).
Win1251 maps і glyphs для українських літер уже є.

RAW meter має ліміт накопичувача: не більше `0xFFFFFFFF >> bits_per_pixel`
samples за виклик. Для 10 bit це 4194303. Починати з малого ROI/кроку й
арифметики APEX96, перевіряти dimensions/step і timeout; не сканувати всі
8.27 млн photosites за один виклик. 10-bit histogram на 1024 unsigned bins
потребує приблизно 4096 bytes лише для bins, без Lua/allocator overhead.

## Вимірювані бюджети

Для кожного prototype записати code/data/BSS delta, peak heap, largest free block,
час hook, median/p95/max shot interval і частоту помилок. Числовий запас RAM
приймається лише після baseline stress matrix, включно з flash, video, playback,
Lua, DNG та великими файлами. Не вмикати EXMEM/ARAM просто через наявність define.
Не обіцяти відсотки прискорення до парного вимірювання.

Не плануємо переписування Canon demosaic/AWB/AF/JPEG ISP: доступні hooks цього
не доводять. NR hook керує наявною опцією dark-frame policy, а не довільним
алгоритмом denoise. Offline stacking є окремим шляхом з іншими ресурсами.

## Рекомендований Task 002

1. Провести фізичний baseline gate з [TESTING.md](TESTING.md) і зберегти RAW/JPEG,
   memory logs, версію SD та налаштування; розібрати address discrepancies перед
   змінами фокуса чи boot.
2. Довести українську локалізацію на наявній системі: missing IDs, placeholder
   compatibility, Win1251 glyphs, LCD widths; зробити окремий optional language build.
3. Після успішного baseline — малий highlight-aware Lua prototype з обмеженим
   ROI і максимумом кадрів, без firmware patches; порівняти з existing bracketing.

Task 002 не повинен одночасно міняти heap, loader, GUI engine і DNG pipeline.
