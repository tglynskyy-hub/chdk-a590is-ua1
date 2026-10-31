# Перевірки і фізична валідація

Оновлення Task003: [HARDWARE_TEST_MATRIX.md](HARDWARE_TEST_MATRIX.md) містить
user-reported успішні тести baseline та окремі pending gates нових профілів.
Наведений нижче початковий план збережено як основу регресійних перевірок.

## Автоматизований gate

Workflow `A590 101b baseline` збирає два чисті результати в одному зафіксованому
контейнері, перевіряє непорожній `DISKBOOT.BIN`, порівнює його і всі FLT,
зберігає ELF sections/symbols, package inventory, SHA-256 і журнал.
Це перевірка компіляції/відтворюваності, не емуляція DIGIC і не доказ boot safety.
Точний статус/результати — у [BUILD.md](BUILD.md).

Перед PR: `git diff --check`; переконатися, що `platform/`, `loader/`, `core/`,
`modules/`, `lib/` не змінені від бази. Порівнювати `manifest.json` і
`arm-none-eabi-size` між комітами з однаковим compiler/config. Зростання BSS
також витрачає RAM, хоча не входить у file size. Не задавати довільний «безпечний»
ліміт без camera measurements; до них кожне збільшення потребує пояснення.

## Підготовка фізичного тесту

Підтвердити саме GM1.01B. Зберегти фото й копію SD, мати окрему тестову карту та
працездатні батареї. Використовувати документований SD boot для A590, з повним
узгодженим CHDK resource/module tree; не форматувати основну карту автоматично.
Завантаження лише з SD, без запису внутрішньої flash, native Lua calls вимкнені.
Не застосовувати 100e binaries, не обходити version/PID/CRC checks.

Rollback: вимкнути камеру, дочекатися завершення запису, вийняти тестову SD або
вимкнути її autoboot і повернути резервну карту/попередню копію CHDK. Перевірити
звичайний Canon startup і JPEG. Не робити power-cycle під час запису файлів.

## Матриця ручних тестів — НЕ ВИКОНАНО

| Сценарій | Що записати / приймання |
|---|---|
| Cold start record/playback, 20 циклів | Версія/CRC, час запуску, жодного crash/hang |
| Canon Auto/P/Av/Tv/M, AF, MF, zoom, IS, flash | JPEG, EXIF, правильна експозиція/фокус, штатна поведінка після ALT |
| Всі клавіші, half/full shutter, Print/Display ALT, меню | Без stuck keys, passthrough і autorepeat працюють |
| RAW off / RAW / DNG, одиночні й серії | JPEG не пошкоджений, DNG декодується, 3336×2480 CFA/crop metadata узгоджені |
| Long exposure NR Auto/On/Off | Реальний час, dark frames, hot pixels; відновлення Canon policy |
| Tv/ISO/Av brackets | Фактичні EXIF і raw brightness; жодних обіцянок крайніх витримок без перевірки |
| Focus bracket, macro/infinity, AFL/MF | Положення фокуса та settling; особлива увага focus_busy discrepancy |
| Video, optical zoom, mute, playback, IS | Запис/звук/закриття файлу, нормальна робота після виходу |
| Lua/uBASIC, modules load/unload, user menu | Existing scripts/API працюють, heap після повторів стабілізується |
| PTP remote capture, якщо підключено | JPEG/RAW chunks, завершення передачі/запису, від'єднання без зависання |
| Українська + Win1251 | ЄІЇҐ/єіїґ, рядки, діалоги, ширина, повернення до English |
| 100+ кадрів і 30+ хв змішаних режимів | Min largest block, memory trend, median/p95/max latency, error count |

Для image-quality порівнянь використовувати штатив, незмінне світло, matched
exposure/ISO, ту саму SD, scene IDs і RAW-processing settings. Оцінювати clipping
у лінійному RAW після black subtraction, шум на однаковій яскравості, деталі та
рух; яскравіший JPEG сам по собі не означає кращу якість.

## Безпечне вимірювання ресурсів

Нижче приклад для наявного CHDK Lua, не виконаний на камері. Запускається вручну
в ALT, лише читає системний heap і додає рядки на тестову SD. Не виконує зйомку,
peek/poke, native calls, ROM dump, EXMEM reserve або зміну persistent config.
Після 30 samples завершується; measurement overhead Lua/file I/O треба врахувати.

```lua
-- Save as a standalone diagnostic script on the test SD.
-- @title A590 heap sample
-- @chdk_version 1.7
local f = assert(io.open("A/CHDK/LOGS/A590HEAP.CSV", "a"))
f:write("tick,free,largest,peak,chdk_size\n")
for i=1,30 do
    local m = get_meminfo("system")
    if not m then break end
    f:write(string.format("%d,%d,%d,%d,%d\n", get_tick_count(),
        m.free_size or -1, m.free_block_max_size or -1,
        m.allocated_peak or -1, m.chdk_size or -1))
    f:flush()
    sleep(1000)
end
f:close()
```

Повторити у record/playback і після контрольованої серії; не трактувати цей
простий idle sampler як вимірювання піку всередині capture. Для capture timing
потрібен окремий bounded script з timeout, `get_tick_count`, RAW hook arrival/
release, shooting completion і збереженням файлу. RAW hook обов'язково звільняти
через `continue`; він блокує конвеєр. Логувати на SD поза критичним hook.

Stack watermark: keyboard уже заповнює власні 8192 B sentinel-значенням.
Майбутній diagnostic module може прочитати untouched range лише після верифікації
адрес/меж; це lower bound запасу за конкретний сценарій, не гарантія. Не записувати
sentinel у активні Canon/IRQ stacks і не робити довільний memory scan.

OOM/short-write/task-create failure paths спершу перевіряти host harness або
контрольованим окремим diagnostic build. Не заповнювати важливу карту й не
пошкоджувати filesystem навмисно. Release gate закритий до фізичних результатів.
