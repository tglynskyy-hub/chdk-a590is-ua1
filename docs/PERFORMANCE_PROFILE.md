# Task004B: вимірювання продуктивності

Ціль: A590 IS GM1.01B, r6346, GCC ARM 8.3.1. Task004 reference:
`92d7b142d14aeccc5fd10d187f577da17369182d`, manifest у evidence/task004-manifest.json.
Користувач підтвердив повільне меню, але числових вимірювань немає.
Зменшення кількості операцій нижче не є виміряним прискоренням камери.

## Результат аудиту

| Шлях | Доказ у коді | Рішення Task004B |
|---|---|---|
| SpyTask, ALT redraw | core/main.c: redraw раз на 4 ітерації, msleep(20); RAW обходить звичайний GUI цикл | Це успадкована cadence, не 80 ms гарантія. Пріоритети/затримки не змінені |
| Keyboard | platform/generic/kbd.c та camera keyboard task; upstream debounce/autorepeat | Вимірювати після dispatch; фізична затримка кнопки сюди не входить |
| Menu init | core/gui_menu.c: розміри, рядки, прокручування | Окремий таймер; холодне відкриття порівнювати з повторним |
| Навігація | gui_menu_updown повторно обходив sentinel-terminated список | Один підрахунок рядків на рух; таблиця протягом цього виклику не змінюється |
| Redraw | gui_menu_draw вже має dirty/full/partial стан | Не запроваджувати другий dirty engine без даних; таймер лише фактичного малювання |
| CP1251 | lib/font/font_8x16.c: прямий lookup | Гіпотезу дорогого пошуку Unicode відхилено; нового кешу немає |
| Мова Task004 | повторний вибір перезавантажував translation/font state | Якщо шлях, codepage і builtin font вже правильні — no-op |
| UI mode Task004 | синхронне збереження конфігурації | No-op вибір не пише SD; справжня зміна досі зберігається одразу |
| FLT | modules/module_load.c: lazy bind/load, deferred unload | Таймер load/unload, без preload і примусового unload |
| Config | core/conf.c: allocation/write failures раніше не враховувались | NULL до O_TRUNC; перевірка write/close; dirty state зберігається при помилці |
| Stack/heap | діагностика використовує статичні bounded arrays, export line 192 bytes | Це розмір локального буфера, не stack high-water; stack margin на камері ще невідомий |
| SD/Canon | sync I/O і scheduling можуть домінувати | Одна карта/стан, окремі JPEG/DNG/video регресії; поки гіпотеза |

## Збірки

CI робить normal і diagnostic (`UI_PROFILE=1` → `OPT_UI_PROFILE=1`), у кожній
Full 38 FLT і Photography 30 FLT. Normal не має таймерів, CSV writer чи статичних
масивів профайлера: host test перевіряє порожній ui_profile.o. У normal залишаються
текстові ID для сумісного комплекту мов. Розміри ELF/BSS/ZIP — у CI evidence та
profile-tests.json; diagnostic не використовувати як вимірювання normal overhead.
Жодних EXMEM/ARAM, нових task, polling file writes, compiler/scheduler tuning.

## Протокол на камері

1. Зберегти Task004/Task002A пакети та повну копію SD. Встановити **diagnostic**
   комплект одного commit; не змішувати DISKBOOT і FLT. Записати SHA пакета,
   карту, режим REC/PLAY, RAW/OSD налаштування, заряд. Перезапустити.
2. Без зйомки відкрити Photography, Classic, повернутися. Перші root checkpoints
   знімаються до init меню, тому включають стан входу, а не завершене малювання.
   Startup checkpoint — після gui_init, не після всього warm-up Canon.
3. Для latency окремий свіжий запуск: відкрити меню, зробити 30 одиночних рухів
   з паузами, закрити/відкрити ALT і меню ще 5 разів. Зовнішнє відео кнопки+LCD
   потрібне для справжнього button-to-photon. Позначити cold/warm порядок вручну.
4. Photography → Налаштування → Діагностика UI → Зберегти діагностику CSV.
   Скопіювати `CHDK/DATA/UISTAT.CSV`, `UIMEM.CSV`, `UIDELAY.CSV` у каталог запуску.
   Повторити тричі. Для memory switches/Lua — окремий запуск за MEMORY_INVESTIGATION.
5. Повторити на normal для суб'єктивної/відео перевірки overhead та Task004 для
   зовнішнього порівняння. Task004 не має цих counters: його latency CSV не існує.

UISTAT events: 0 init, 1 draw, 2 move, 3 response, 4 config-save, 5 module-load,
6 module-unload. Load включає спроби, cached і failed calls. Total/max/last у ms;
mean = total/count. UIDELAY містить **перші 64** response samples після reboot;
coalesced latest input → наступне завершене menu draw, не кожна фізична кнопка.
Немає розподілу cold/warm за назвою меню: співвіднести з журналом дій.
Тік може бути грубим: 0 ms означає нижче роздільності, не нуль роботи.
32 memory snapshots, зайві рахуються dropped. Export замінює три файли, може
бути частковим при SD error; після помилки не аналізувати комплект як повний.
Counters best-effort між tasks, export у спокої; це не атомарний trace.

## Host перевірки і наступні рішення

`test_performance.py` компілює реальний C: зіставляє навігацію з Task004 fixture
для різних рядків/text gaps/напрямків/прискорення; рахує row-count calls, не ms ARM.
Перевіряє wrap/saturation, bounds/export faults і config allocation/open/write/close
faults. `test_photo_ui.py` перевіряє реальні callbacks та no-op поведінку.
CI зберігає stdout у performance-tests.txt, обидві clean builds та hashes.

Після фізичних даних ранжувати p50/p95 response, draw, config і module load.
Не міняти task priority заради теоретичних ms. Task009: ARMv5TE disassembly,
SD write throughput, RAW hot loops, compiler flag A/B з GCC8.3.1 reference,
selected assembly тільки після bit-exact тестів і hardware gate. NEON/VFP немає
в прийнятій моделі цілі; EXMEM/ARAM потребують окремо перевіреної карти пам'яті.
