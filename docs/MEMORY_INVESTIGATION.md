# Task004B: пам'ять та непрацюючий Benchmark

## Факти та межі

Уточнення користувача: **«бенчмарк просто не працював»**. Це збій/недоступність
Benchmark, а не доказ несправності GetMemInfo, витоку чи нестачі пам'яті.
Немає повідомлення помилки, точного етапу, чисел або відтворення.
Task004 startup/UA/switch persistence/keyboard/JPEG/AF/zoom/RAW-DNG/video/Lua/restart
працюють за звітом користувача. Task004B фізично ще не перевірений.

`modules/gui_bench.c` — benchm.flt, retained у Full і Photography. Модуль
відкриває екран, але запускає тести лише SET на Start; LEFT/RIGHT вибирають
Start/Log/SD. Під час тесту keyboard handler ігнорує ввід. Це throughput test,
не free-memory viewer. Виділяє 65536 bytes benchbuf; RAM і buffered SD тести
перевіряють NULL. Також виконує CPU, framebuffer, timer-register та SD операції.
Наявність NULL checks не доводить загальну справність; таймінги/firmware/модуль/SD
потребують реального відтворення. Змішаний комплект FLT/DISKBOOT — ще одна гіпотеза.
Не патчити MMIO/assembly або focus_busy за цим повідомленням.

## Власники й lifetime

| Ресурс | Власник / звільнення | Інтерпретація |
|---|---|---|
| translation strings | lib/lang/lang.c, lang_init free/reallocate | Повторний той самий вибір тепер пропускається |
| langbuf | language loader, retained capacity | Warm plateau може бути нормальним кешем |
| language file buffer | process_file lifecycle | Перевіряти після завершення load, не в середині |
| FLT slots | module_load.c; can_unload + deferred module_tick_unloader | Вихід з екрана не завжди моментальний unload |
| Lua VM | modules/luascript.c session; get_meminfo створює Lua table | Lua inspector сам змінює вимірюваний heap |
| config buffer | core/conf.c umalloc/ufree | Усунуто NULL-before-memcpy path; не доказ причини Benchmark |
| DNG thumbnail/header | modules/dng.c | 36864-byte thumbnail + header; fault-path audit у Task006 |
| новий profiler | статичні arrays, 32 snapshots + 64 delays | Немає heap allocation; BSS overhead вимірює linker |

GetMemInfo A590 GM1.01B має native stub 0xffc03c40. Невідомі поля ініціалізовано
-1. EXMEM/ARAM не активуються. Allocation ownership по кожному malloc не
трасується: це було б втручанням у timing/allocator. FLT disk size не є heap size;
порівнювати memory snapshots із debug module list окремого контрольного запуску.

## Повторюваний цикл

Одна карта, той самий REC/PLAY і налаштування; не запускати Benchmark/зйомку одночасно.
Diagnostic профайлер не залежить від benchm.flt або Lua.

1. Reboot: auto tag0 після gui_init. Перше Photography tag1, перше Classic tag2.
2. Перемкнути Classic↔Photography рівно 10 разів; tag10. Продовжити до 30; tag30.
   No-op вибір того самого режиму не рахується. Кожна справжня зміна зберігає config.
3. Почекати 2 s, у diagnostics «Зняти стан пам'яті» (tag100). Запустити короткий
   скрипт без зйомки (наприклад `print("memory cycle"); sleep(1000)`), дочекатися
   завершення, вийти з ALT, почекати 2 s, знову зайти в diagnostics і вибрати
   «Після вивантаження Lua» (tag101). Назва — checkpoint, не підтвердження unload:
   якщо VM лишилася resident, це записати і звірити module list окремо.
4. Повторити короткий Lua цикл 5 разів. Повернутися до того самого меню/режиму,
   почекати 2 s і «Стан спокою» (tag102). Експортувати три CSV. Повторити весь
   протокол з reboot тричі. Ліміт 32 samples; dropped має бути 0.
5. Надіслати CSV + SHA пакета + журнал дій. Free/allocated порівнювати лише між
   еквівалентними warm states. Peak зазвичай не зменшується — це не витік.

Stable plateau → імовірне retained state; free stable/largest falling → підозра
фрагментації; обидва падають по однакових циклах → підозра lifetime/leak, ще не
доказ unreachable allocation. Small largest block може зірвати 64-KiB allocation
навіть за великого total free. Потрібна повторюваність і локалізація власника.

## Окреме відтворення Benchmark

На резервній карті/копії даних записати: чи відкрився екран, чи натиснуто SET на
Start, останній рядок, реакція кнопок, зависання/вимкнення/повідомлення, REC/PLAY,
Log і SD options. Спершу SD test off, потім окремо SD on лише за стабільного
першого запуску. Не запускати під час запису JPEG/DNG/video. За зависання не
повторювати нескінченно; зберегти опис і повернути відомий пакет. BENCH.LOG,
якщо створився, додати до звіту. Task004B **не заявляє виправлення Benchmark**.

Config fix перевіряє allocation/write/close і лишає dirty state для retry.
Це не atomic save: short write/power loss може пошкодити файл; backup потрібен.
