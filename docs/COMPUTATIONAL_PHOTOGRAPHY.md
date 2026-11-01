# Обчислювальна фотографія: оцінка Task004B

Це архітектура, не реалізовані нові режими. ARM946E-S/ARMv5TE, GCC8.3.1 reference;
не припускаємо NEON/VFP чи вільні десятки MiB. Один RAW кадр = 10 341 600 bytes;
два копійовані packed frames >19.7 MiB, ще без alignment/accumulators. Це не
доводить неможливість tiled algorithms, але повнокадровий in-camera merge зараз
не має обґрунтованого RAM/time бюджету. Спочатку якісні серії для offline merge.

| Ранг / можливість | Reuse, Lua, native | Бюджет і firmware | Користь / перевірки / ризики |
|---|---|---|---|
| 1 Intelligent exposure + smart HDR | rawop.meter/histogram у modules/rawhookops.c; Lua controller, native sampled statistics | RAW hook після capture, рішення для наступного кадру; histogram 1024 counters ~4 KiB; bounded ROI/grid | Менше clipping і достатнє bracket coverage; рух/шум/насичення можуть зіпсувати оцінку |
| 2 Night Stacker | existing capture/NR/exposure API; Lua sequence | O(1) session state, N files на SD; без frame copies | Offline align/stack; рух/температура/dark mismatch, об'єктивний SNR і detail comparison |
| 3 Smart Timelapse | Lua sequencing + exposure controller | Frame/deadline bounds; native metering за потреби, не pixel loops Lua | Плавні переходи; стрибки освітлення, shutter interval overrun, ISO noise |
| 4 Astro Sequence | Lua exposure/NR/dark scheduling | Long exposure + write + dark time включати в interval budget | Придатні light/dark sets; thermal drift, hot pixels, star movement |
| 5 Motion Trigger | наявний md_detect_motion / motion.lua | Viewport ROI sampling, CPU залежить від grid; не RAW live analysis | Новий алгоритм лише якщо false positives/trigger delay кращі; lighting flicker |
| blocked Macro Focus Stack | focus API + future Lua | focus_busy 0x9D50 vs signature 0x7F4C unresolved | Спершу довести адреси/стани/MF/AF/zoom на GM1.01B; не автоматизувати зараз |

## Новий контролер експозиції (Task007)

Після captured RAW, поки hook доступний, native meter на bounded strided ROI
і histogram оцінюють black-subtracted середнє та частку near-white pixels.
Не тримати hook під час SD/log/user wait. Перевіряти API range/sample overflow,
доступність buffer та deadline, завжди release hook при error/cancel.
Lua перетворює statistics на EV96 correction: deadband, hysteresis, max step,
мінімум/максимум shutter/ISO, finite iterations, fallback на останні валідні
параметри. Початкові межі (наприклад 1/3 EV step) — tunable design, не calibration.
Aperture/shutter пріоритет користувача не змінювати непомітно. RAW analysis не є
поточним live exposure; перший кадр — probe або звичайний кадр з metering.

HDR вибирає bounded bracket offsets із clipped fraction/shadow statistics;
записує фактичні Tv/Av/Sv кожного кадру. Порівнювати з fixed -2/0/+2 EV за
highlight retention, shadow SNR, count/time, рухом і failure rate. Offline merge
explicit у UI. Люкс/сцена не визначаються з одного normalized mean універсально.

## Додаткові кандидати

- Multi-frame denoise/exposure fusion/alignment: спершу ПК; tiled native лише після
  memory/IO prototype, ghosting і detail tests. Metadata edits не знижують noise.
- Dynamic range/clipping analysis: native sampled histogram, affordable candidate;
  не вимірює абсолютний sensor DR без calibration/noise floor.
- Focus quality: bounded viewport/RAW gradient ROI з noise normalization;
  experimental; не означає безпечне керування мотором фокуса.
- Capture timing: timestamps existing hooks + external reference; deterministic
  timing не гарантується Canon tasks/SD. Не busy-wait і не підвищувати priorities.
- Automated scene exposure: bounded controller above, scene-change reset;
  не безмежний auto-optimizer.

Для кожного prototype: baseline shots, однаковий converter, scene/ISO/exposure,
original hashes, runtime/free/largest, cancel/SD-full tests, failure count. Лише
виміряна перевага виправдовує перенесення Lua logic у native C. Нові native FLT
можуть бути lazy-loaded, але не preload до вимірювання їхнього footprint.
