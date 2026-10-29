# Апаратний і ресурсний аудит

Рівні доказів: **S** — перевірено у вихідному коді; **D** — зовнішня документація;
**T** — потрібне вимірювання на фізичній камері. S не означає апаратну валідацію.
На 2026-10-29 камера не підключалася, RAM/CPU benchmarks не виконувалися.

## Карта ресурсів

| Властивість | Значення / джерело | Рівень |
|---|---|---|
| Модель/firmware | A590 IS, GM1.01B, PID 12662; `101b/stubs_entry.S` | S |
| ОС | DryOS 2.3 R23; той самий файл | S |
| CPU target | DIGIC III; ARM946E-S, ARMv5TE; `makefile.inc`, `arm_rules.inc` | S |
| RAM address ceiling | `0x01FFFFFF`, тобто 32 MiB адресного простору; не free heap | S |
| ROM mapping | `0xFFC00000..0xFFFFFFFF`, 4 MiB; stubs | S |
| Canon data | `[0x1900,0xDC48)`, 49992 bytes | S |
| Canon BSS | `[0xDC48,0xA5304)` | S |
| CHDK load | `0xA5304` стандартно; `MEMISOSTART` | S |
| Heap boundary used by boot | `_end .. 0x272968`; поруч `0x279C00` — kernel setup | S |
| Span before CHDK reservation | `0x272968-0xA5304 = 1889892` bytes; не runtime free memory | S, обчислено |
| EXMEM alternative | 4 MiB, load `0x1BFFFD0`; опції EXMEM стандартно вимкнені | S |
| ARAM candidate | stubs пропонує `0x2CE000`, size `0x32000`; не ввімкнено в baseline | S |
| Uncached alias bit | `0x10000000`; `include/camera.h` | S |
| RAW buffer | `0x10F63920`, один за коментарем sigfinder і lib API | S |
| RAW geometry | 3336×2480, packed 10 bit → **10341600 bytes** | S, обчислено |
| JPEG geometry | 3264×2448; `platform_camera.h` | S |
| Active area | x `[12,3300)`, y `[10,2480)` | S |
| CFA / levels | `0x01000201`, black 31, white 1023 з default macros | S |
| Bitmap | `0x10361000`, logical/storage 360×240×8 bit → 86400 bytes/plane | S |
| Live viewport | pointer table `0x2168`, index `0x1FE8`, previous of 3 slots | S |
| Record viewport | `0x10659E80`; playback pointer at `0x5258` | S |
| Palette | active at `0x3D518`; PTP getter повертає 64 bytes, type 1 | S |
| Iris/ND | реальна діафрагма; ND відсутній, `notes.txt` і camera defaults | S |
| CPU clock, bus/SD throughput | не встановлено | T |
| Free heap, largest block, stack margins | не виміряно | T |

Адреси `0x10...` — uncached aliases, не додаткова RAM. Не резервувати другий
RAW-кадр 10.34 MB на підставі «32 MB загалом»: пам'ять уже використовується Canon.
Функція viewport width у playback містить авторське припущення 720 vs 704;
воно не є перевіреним розміром апаратного буфера.

## Алокації, стеки та синхронізація

`core/memmgmt.c` використовує Canon heap і, якщо явно ввімкнено, suba heaps
ARAM/EXMEM. `platform/generic/wrappers.c:GetMemInfo` має шлях для DryOS до R39;
101b має stub GetMemInfo. Потрібні одночасно `free_size`, `free_block_max_size`,
`allocated_peak` і зміна після повторних циклів: одного числа free недостатньо.
Module loader вже повторно використовує буфер читання і звільняє модулі.

SpyTask отримує 8192 bytes; keyboard має статичний `kbd_stack[0x2000]`, заповнений
`0xDEDEDEDE`, і ручне перемикання SP; DNG RevBytes отримує 1024 bytes.
Ці величини — виділені обсяги, не виміряне використання. `-fstack-usage` може
оцінити C-функції в окремому діагностичному складанні, але не доводить межі
naked ASM, рекурсії Lua, IRQ і вкладених ROM calls. Майбутня перевірка watermark
має читати лише відомі межі власного стека, не записувати в активний стек.

RAW-save handshake і DNG `rb_state` — спільний стан між задачами. Наявні sleep,
cache barriers, буферні lifetime і порядок завершення не можна видаляти заради
теоретичного прискорення. Sleep(10/20) у коді не вимірює scheduler latency.
Апаратних SIMD/NEON/FPU API для цього порту не доведено; використовувати лише
підтверджений ARMv5TE target та наявні `lib/armutil` primitives. Наявність Canon
JPEG encoder не означає наявності безпечного інтерфейсу до його алгоритмів.

## Конкретні ризики

| Пріоритет | Свідчення | Наступна перевірка |
|---|---|---|
| Високий | `stubs_min.S` focus_busy `0x9D50` vs generated `0x7F4C`; recreview_hold `0x93EC` vs `0x5D34` | Зіставити з законно отриманим власним ROM dump, disassembly, AF/review tests; адреси не виправляти навмання |
| Високий | `kbd.c` naked C + ручний SP; boot і exp_drv ASM залежать від compiler ABI | Вивчити disassembly, реальний boot/input/capture soak test |
| Високий | `code_gen.txt` має `EXIT` до open/write/close filewrite sections, хоча вони є у `filewrite.c` | Не регенерувати автоматично; окремо перевірити поведінку generator і повноту результату |
| Високий | Один RAW buffer, DNG змінює і відновлює порядок байтів | Порівняти JPEG із RAW off/on, DNG decode, серії, помилки SD |
| Високий | DNG task creation/write completion та shared state потребують окремого аналізу failure paths | OOM/short-write testing спершу в контрольованому harness; не вводити збої на цінній SD |
| Середній | `get_flash_params_count` повертає 114, sigfinder рекомендує `0x73` (115) | ROM verification; не розширювати читання наосліп |
| Середній | kbd_pwr_on/off sigfinder match 86%/67%; power-off виклик у keyboard закоментований | Верифікація адрес і стабільності вводу |
| Середній | `FAT32_detect.S` також порівнює type 0x07 | Це не доказ підтримки exFAT; стартувати з документованої конфігурації SD |
| Середній | `CAM_EV_IN_VIDEO` вимкнено з приміткою про 101b | Не обіцяти video EV; регресія movie/zoom/mic |
| Середній | `101b/movie_rec.c:sub_FFD126CC_my` завантажує `R7=table`, потім одразу `R7=0xFFE86C24` | Змінена таблиця thresholds фактично перекривається ROM-адресою в цьому шляху; окремо перевірити bitrate control, не змінювати в baseline |
| Середній | Font/lang signed offsets і неповний переклад | Статична перевірка buffer budget, форматів і ширин |

CRC metadata 101b містить ROMCODE `0xFFC00000`, length `0x269FD2`, CRC
`0x7F90495F`, та ROM-копію RAM data `0xFFED0D74`, length `0xC348`, CRC
`0x7B0AD9E5`. Loader version/PID check і модуль `fwcrc` — різні перевірки;
не називати кожен запуск loader повною CRC-валідацією. Фізична firmware не читалася.

Безпечні методи вимірювання та release gate: [TESTING.md](TESTING.md).

## Виміряний розмір складання (не runtime memory)

Успішний baseline: text **88148**, data **42212**, BSS **14004**, загалом
**144364 bytes**; linker `_start=0xA5304`, `_end=0xC86F0`.
Арифметичний span від `_end` до `0x272968` — **1745528 bytes** перед витратами
Canon heap allocator і runtime allocations. Це не гарантований вільний запас.
DISKBOOT займає **131473 bytes** на SD; цей розмір не включає BSS і не замінює
RAM accounting. 38 FLT сумарно **266912 bytes** на диску, не одночасно resident.
