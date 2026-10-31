# Фотографічний engine і вимірювана оптимізація

Baseline: ARM946E-S/ARMv5TE, GCC 8.3.1, без припущень про NEON/SIMD/VFP.
EXMEM/ARAM не активувати через сам факт наявності defines. Розміри ELF не є
вільною heap RAM; Canon tasks і RAW buffers мають власні вимоги. Додаткові CPU/RAM
допустимі заради перевіреної фотографічної користі; battery efficiency не ціль.

## Повторно використати наявне

| Напрям | Існуючий код | Перший рівень реалізації / gate |
|---|---|---|
| Highlight preservation | modules/rawhookops.c, raw_ev_histo.c, core/autoiso.c | Lua bounded histogram/clipping controller, desktop порівняння highlight recovery. C лише після профілювання; live YUV zebra не тотожна RAW clipping |
| Intelligent bracketing | core/shooting.c, platform/generic/shooting.c, CHDK/SCRIPTS/hdr.lua | Lua Tv96 серії, потім adaptive bounds; не замінювати working capture hooks |
| RAW metering/histogram | rawhookops.c, shot_histogram.c, histogram.c | Strided ROI sampling, existing native counters; виміряти sampling bias, RAW hook hold time |
| Auto ISO | core/autoiso.c | Спершу параметри і повторювані сцени, потім звичайний C smoothing/clamps за даними; Canon proprietary AE не переписуємо |
| DNG workflow | modules/dng.c, core/raw.c | Спершу decode/metadata/error/SD-capacity tests, write-time profiling; потім C bounds/error reporting. Один RAW buffer: не припускати безпечний asynchronous reuse |
| Focus bracketing | Lua set_focus, platform/generic wrappers, a590 stubs_min.S | Blocked address audit + MF tests; firmware hooks лише з ROM evidence, окремий PR |
| Low light | Lua exposures/NR/RAW + existing script APIs | Offline stacking, bounded session; оцінювати шум/деталі/рух, не лише ISO |
| Capture performance | core/raw.c, action_stack.c, platform/a590/sub/101b/capt_seq.c | Timestamp instrumentation і SD I/O спершу; ASM hook rewrite не входить у Task003/004 |

Arbitrary Canon JPEG engine, AF firmware, AWB та ISP tuning не є доступними
публічними APIs цього порту. Оцінюємо реально керовані exposure/RAW/script функції.

## План бенчмарків

Перед/після: та сама карта, filesystem/вільне місце, сцена, освітлення, режим,
експозиція, RAW/DNG/NR settings. Warm-up 5, потім ≥30 вимірів (довгі exposures
можуть потребувати меншої, явно вказаної вибірки). Log raw observations, p50/p95/max,
failure count; не оголошувати виграш менший за похибку/варіацію SD.

| Bottleneck | Вимір | Кандидат лише після результатів |
|---|---|---|
| Heap/fragmentation | get_meminfo free/largest block, 100 open/close/script cycles; collectgarbage count | Менші bounded temporary tables/buffers, explicit release, no stale references |
| Stack | Документований task stack instrumentation/guard у debug build; compiler stack report у відокремленій збірці | Прибрати великі stack arrays/recursion; не писати у невідомі адреси Canon stacks |
| RAW processing | hook entry/exit ticks, stride/ROI/bits sweep, clipping accuracy | Native existing ops, bounded sampling, allocation reuse; жодної другої full RAW copy без headroom |
| Histogram | process tick count, overlay/update frequency, CPU effect на capture | Інкрементальне оновлення/ROI; порівняти якість histogram |
| Dynamic modules | MODULES.LOG load/unload, heap deltas/largest block | Не preload всіх FLT; зберігати лише виправдано часто вживаний модуль |
| Menu rendering | Key-to-redraw latency, heap після repeated mode switches | Обмежити redraw regions, cache text widths з invalidation language/font |
| File I/O | DNG bytes/time, mkdir/open/write/close timing, free-space/error paths | Chunk size/buffering tuning після вимірів; не жертвувати error checks |
| Synchronization | shoot→RAW hook→file ready timeline, timeout counts | Усунути busy wait, bounded state transitions; підтвердити no missed capture |

Timer get_tick_count дає дискретний software час, не cycle-accurate counter;
не видавати невимірювані мікросекунди за результат. Інструментування теж додає
витрати; порівняти debug і без logging. Жодних measured latency/free heap цифр
поки немає. Packaging Task003 дає native size delta 0; package savings не доводять
меншої shutter latency або кращого JPEG.

GCC newer evaluation — окремі branch/container/artifacts із diff ELF, warnings,
module ABI/relocation tests і повною physical regression. Не замінювати GCC8.3.1
у validated pipeline. Assembly optimization тільки після hot-path профілю,
коректності C reference і виміряного виграшу на ARM946E-S.
