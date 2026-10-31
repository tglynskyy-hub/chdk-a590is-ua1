# CHDK A590 IS Enhanced — актуальна дорожня карта

Цей документ уточнює A590IS_UA_PLAN.md і OPTIMIZATION_ROADMAP.md, не видаляючи
історичні плани. Ціль — фотографічна користь, доступність українською і
сумісність Canon/CHDK; економія батареї не пріоритет.

## Інтеграція і відома основа

Task003 починається від Task002A commit `398beedf0f50170fae2efd02884af11f7ea8e4fd`.
На момент початку PR2 і PR3 відкриті: merge order **PR2 → PR3 → Task003 PR**,
із перевіркою base/CI після кожного retarget. PR3 базується на Task001 branch,
Task003 — на Task002A; жодну незлиту історію не відкинуто, trunk не змінювався.
Не виконувати автоматичний merge. Якщо попередній PR squash/rebase merged,
спершу узгодити stacked history/diff, не force-reset чужу роботу.

Користувач підтвердив boot/menu/JPEG/AF/zoom/browser/RAW-DNG decode/video/restarts
на r6346, 32-MiB FAT16 + FAT32, BOOTDISK/LOCK. Деталі й межі доказу —
[HARDWARE_TEST_MATRIX](HARDWARE_TEST_MATRIX.md). Старий Full artifact/SD backup
зберігати як відкат; новим пакетам цей hardware status автоматично не присвоюється.

## Task003 — реалізована безпечна інфраструктура

- Інвентар усіх 38 FLT, conservative dependency closure, source references,
  категорії та explicit exclusion policy.
- Full (38) і Photography (30), однаковий DISKBOOT і retained resources;
  вилучення семи ігор, календаря, Sokoban levels лише при пакуванні.
- Два незалежні clean full builds із обома deterministic profiles, separate
  artifacts/manifests/inventory, baseline hashes/sections, negative integrity tests.
- Повторний locale audit: 237 missing IDs, два printf mismatches, glyph/width report.
- UI, Lua suite, photographic engine, performance та hardware acceptance plans.

Native/UI code, language bytes і Lua runtime не змінені. Нових фотографічних
режимів не заявлено. Initial Simple UI infrastructure відкладено: навіть малий
selector змінить shared runtime і вимагатиме окремого regression gate.

## Конкретний Task004: український фундамент і перший bounded script

1. Перевірити/злити за рішенням користувача попередні PR у правильному порядку;
   зберегти Task002A artifact/backup, записати хеш фізично протестованої копії.
2. Окремий commit: strict locale validator + regression fixtures для %%/types/*,
   CP1251/duplicate IDs/offset limits; виправити IDs107/109, перекласти missing
   рядки тематичними commits. Default English не змінювати до LCD QA.
3. Окремий commit: `photo_session.lua` із bounded state machine і Night Stacker
   prototype; host mocked tests timeout/cancel/no-space/restore, без focus/RAW hooks.
4. CI обидва profiles, source/manifest review; будь-яка зміна native binary
   потребує пояснення size/hash delta й нового reference, не перезапису Task001.
5. Фізично: UA glyph/width/fallback, Night 1/10 кадрів, stop/error/restore;
   JPEG/AF/zoom/DNG/video/restart matrix. Внести звіт із версіями/хешами.
6. Лише після gate — Ukrainian first-use/default proposal; Simple menu selector
   окремим наступним PR або окремою частиною Task004 за результатами scope review.

## Наступні етапи

| Етап | Результат | Gate |
|---|---|---|
| UI prototype | Existing CMenu root selector + user-menu quick access | Switch без restart/leak, усі Classic paths, UI readability |
| Fixed HDR/Motion | Bounded script sequences на чинних APIs | EXIF/trigger timing/cancel + реальні сцени |
| Adaptive exposure/Timelapse | RAW ROI controller/Auto ISO tuning | clipping/flicker/CPU/heap measurements, не лише суб'єктивна оцінка |
| Astro | Bounded long sessions і dark-frame workflow | NR/exposure/temperature/timeouts |
| Focus audit → Macro | ROM-proven address/use and MF sequence | Вирішити focus_busy/recreview_hold, repeatability й AF regression |
| Native optimization | Лише виміряні hot paths | Correctness + benchmark gain + physical regression |

Task003 acceptance: обидва ZIP з CI success, exact baseline shared binary,
dependency/resource/manifest/extraction checks, exclusions verified, logical
commits і reviewable PR. Product acceptance окреме: виміряна якість/зручність,
доступність українською, predictable recovery та user-reported physical tests.
