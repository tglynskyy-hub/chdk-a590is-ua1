# Task004B — поточний hardware gate

Task004 користувач підтвердив: startup, UA, Photography/Classic + persistence,
keyboard, JPEG, AF/optical zoom, RAW/DNG, video, Lua, repeated reboot. UI суб'єктивно
повільний. Уточнення «бенчмарк просто не працював» замінює нечітке «memory failed».
Цифр і відтвореного витоку немає. Усі рядки Task004B нижче **PENDING**, CI не HW.

| Перевірка | Очікування / що записати |
|---|---|
| LOCK CHDK boot, 5 restarts | exact package SHA, no mixed modules, normal Full і Photography |
| UA, Classic↔Photo 30 switches | persisted choice, readable labels, no-op language, memory CSV |
| UI first/warm open, 30 key presses | diagnostic CSV ×3, external video для physical latency |
| Lua load/finish/ALT exit ×5 | native snapshots, no forced module unload |
| Benchmark | screen/start/last stage/options/error/REC-PLAY; окремо SD off/on |
| JPEG, AF, optical zoom | різні zoom positions, фокус до/після меню |
| DNG+JPEG | original samples + hashes, tags/decode, repeated captures |
| Video | record/playback до/після ALT, no dropped control responsiveness |
| UNLOCK stock startup | без Firmware Update, немає CHDK, JPEG + video readable |
| Stock dual partition | actual available capacity, destination partition, files readable на ПК |
| Task002A rollback | matching DISKBOOT/modules/resources + saved config; boot/capture |

Stock UNLOCK startup не доводить доступ до великого FAT32 data partition.
Якщо видно тільки маленький FAT16, потрібна окрема stock card з однією підтримуваною
Canon partition; подробиці SD_ROLLBACK. Не форматувати єдину копію фото.

---
## Історичні результати й попередні матриці

# Матриця фізичних перевірок

> **Оновлення Task 004.** Task 004 Enhanced: усі фізичні тести нового UI залишаються **не виконаними**.
> Повний перелік: [PHOTOGRAPHY_UI.md](PHOTOGRAPHY_UI.md#перевірка-на-фізичній-a590-is).
> Відомі результати Task 002A не переносяться на нову збірку.

## Відомий робочий baseline — повідомлення користувача, Task 003

Користувач повідомив про фізичне тестування CHDK **1.7.0 r6346** на Canon
**A590 IS GM1.01B**. Layout: перший 32 MiB FAT16 з DISKBOOT, другий FAT32 з
CHDK/фото, BOOTDISK і LOCK. Це ручний звіт користувача, не автоматизований suite.
Хеш фактично використаного ZIP окремо користувачем не надано; еталонний пакет
Task 002A із цього чату: SHA256
`acfe8ec4d2bd771e508dfcc529bc2d0d2e57d4d28e689dee1460646ea97bafb2`,
[CI 41196783303](https://github.com/tglynskyy-hub/chdk-a590is-ua1/actions/runs/41196783303).
Не приписуємо цьому звіту вимірювань тривалості, температури, memory headroom
або тестів функцій, не названих користувачем.

| Перевірка | Відомий baseline | Новий Full | Photography |
|---|---|---|---|
| Autoboot | Користувач: працює | Не тестовано | Не тестовано |
| Меню й навігація | Користувач: працює | Не тестовано | Не тестовано |
| Звичайний JPEG | Користувач: працює | Не тестовано | Не тестовано |
| Autofocus, optical zoom | Користувач: працює | Не тестовано | Не тестовано |
| File browser | Користувач: працює | Не тестовано | Не тестовано |
| RAW/DNG, успішне декодування | Користувач: працює | Не тестовано | Не тестовано |
| Video | Користувач: працює | Не тестовано | Не тестовано |
| Звичайні restarts | Користувач: працює | Не тестовано | Не тестовано |
| Flash/IS/довгі серії/переповнення SD | Не повідомлено | Не тестовано | Не тестовано |
| MF/focus bracketing | Не повідомлено, адреса unresolved | Не тестовано | Заблоковано до аудиту |
| UA glyphs, format strings, ширини | Не повідомлено | Не тестовано | Не тестовано |
| Порожній Games/Tools, user shortcuts | Не застосовується до Full | Не тестовано | Не тестовано |
| Шість нових Lua modes | Ще не реалізовані | Не застосовується | Не застосовується |

## Протокол наступного тесту

Зберегти робочу SD недоторканою; нові профілі тестувати на іншій підготовленій
карті або тільки після verified backup за SD_INSTALL_WINDOWS/SD_ROLLBACK.
Не форматувати вже сумісну робочу карту. Зафіксувати ZIP/DISKBOOT SHA, профіль,
параметри карти, стан CFG, акумулятор, Canon mode, результат і точний текст помилок.

1. Full і Photography окремо, чисті CFG: boot/Build Info, усі кнопки/menu/ALT,
   видимість ігор (Full є, Photography індивідуальних ігор немає), повернення Back.
2. File selector, textbox/rename, reader, user editor, Lua і .bas короткий сценарій;
   histogram/Zebra/OSD edit, DNG з незалежним desktop decode.
3. JPEG, AF, zoom, flash, video, playback, 10 restarts; зафіксувати failures,
   не переводити результат кількох проходів у «production-stable».
4. RAM/largest block до/після 10 входів у меню й скриптів; час capture-to-ready
   та тривалість write, max/p50/p95, ті самі карта/сцена/параметри.
5. Missing-module tests проводити на копії пакета, не робочій SD. Перевірити
   повідомлення про старий shortcut, відновити Full, підтвердити нормальний boot.

Окремі gates Task004: glyph chart ҐґЄєІіЇї, обрізання рядків, English fallback,
Simple↔Classic без restart (після реалізації), bounded script cancel/error/full
card, відновлення overrides/hooks і відсутність регресії відео/AF/DNG.
