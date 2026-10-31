# Lua Photography Suite — специфікація, не реалізовані режими

Lua зберігається в обох профілях. Шість нижчеописаних scripts ще не додані й
не пройшли фізичні тести. Existing implementations: `modules/luascript.c`,
`rawhookops.c`, `script_shoot_hook.c`, `CHDK/LUALIB/hookutil.lua`, `rawoplib.lua`,
upstream `CHDK/SCRIPTS/hdr.lua`, `interval.lua`, `motion.lua` та .bas аналоги.
Спершу адаптувати/використати їхні APIs, не копіювати native алгоритми в Lua.

## Спільний контракт

Майбутня організація: `CHDK/SCRIPTS/PHOTO/{hdr,night,macro,timelapse,astro,motion}.lua`,
малий спільний `CHDK/LUALIB/photo_session.lua`, параметри через штатні script
headers/menu; Simple «Розумні режими» посилається на ті самі файли, Classic
script selector залишається доступним. Не додавати їх як порожні «готові» scripts.

Кожен script: finite frame count і wall-clock limit; validate params до capture;
Record/still mode check, free-space check перед кадром, configurable timeout;
state machine PRECHECK→METER→CAPTURE→WAIT_SAVE→NEXT→CLEANUP. LOG CSV:
frame/timestamp/Tv96/Sv96/Av96/free space/result; flush після capture, не в RAW hook.
Параметри обмежені консервативно, фізичні діапазони Tv/ISO беруться з port/Canon
і вимірюються; не прирівнювати сенсорний gain до маркетингового ISO.

Зберігати лише налаштування, які script змінює (`get_tv96/get_sv96/get_av96`,
RAW/NR settings); не скидати всю conf. `restore()` має бути коротким і не yield:
`modules/luascript.c:lua_run_restore` забороняє yield і обмежує час. Release
натиснуті keys, вимкнути hooks/overrides, повернути змінені settings. Мережеві
записи/очікування зйомки й sleep не виконувати в restore; normal cleanup до нього.
Обробити cancel через чинний script stop/exit key, runtime error і timeout.
При фізичній втраті живлення cleanup неможливий: журнал/backup/restart і контроль
settings перед наступним запуском є частиною тесту.

RAM: без збереження full RAW у Lua; обмежені tables/log buffers, `get_meminfo`
і `collectgarbage('count')` до/після серії. CPU: bounded loops зі sleep/yield поза
RAW hook; гістограму/метринг робить existing native rawop. Не зупиняти capture
pipeline надовго; усі `hook_raw.wait_ready` мають timeout, а `continue()` —
гарантований шлях після обробки. RAW pointers дійсні тільки у відповідному hook.

## Шість сценаріїв

| Script | APIs і фотографічна користь | Межі, ціна й recovery | Фізичні тести |
|---|---|---|---|
| Smart HDR Bracketing | get_bv96/get_tv96/get_sv96/get_av96; set_tv96_direct; shoot; для adaptive mode hook_raw + rawop.meter/create_histogram. Серія з деталями у тінях/світлах для offline HDR | Спочатку bounded 3/5 кадрів ±1/2 EV (96 APEX96 на EV), clamp допустимої витримки; метринг додає один probe кадр. ISO/Av фіксовані, не змінювати фокус. O(1) frame state, гістограма bounded bins. Немає in-camera HDR merge. При timeout зупинити серію, повернути overrides | Реальні EXIF ступені, clipping порівняння, рух/ghosting, темна/яскрава сцена, cancel між кадрами, DNG decode |
| Night Stacker | set_tv96_direct, set_sv96, set_raw, shoot, sleep. Повторювані RAW/JPEG для offline stacking | Кількість 1..100 як початковий policy, delay і exposure bounds; O(1) RAM, CPU низький, SD write домінує. Не стверджувати покращення без stacked output; не відключати NR без вибору користувача. Abort при no space/save timeout | Серії 1/10/50, фактичний cadence, гарячі пікселі/температурний дрейф, noise/SNR після однакового offline stack, відновлення settings |
| Macro Focus Stack | get_focus, get_focus_ok/get_focus_state (перевірити export перед реалізацією), set_focus тільки через supported API; get_sd_over_modes; shoot | **Blocked**: focus_busy 0x9D50 vs sigfinder 0x7F4C. Потрібні власний ROM/disassembly й MF repeatability. Не вмикати set_focus_interlock_bypass. Не планувати рівномірну DOF через рівні distance steps. O(1) state, bounded focus settle, timeout → abort | Спочатку одиночні MF команди й return-to-Canon AF, macro endpoints, repeatability/reverse sequence, достатній overlap, cancel/zoom/mode change |
| Smart Timelapse | get_tick_count, shoot, get_bv96/Tv96/Sv96; rawop metering як opt-in; set_tv96_direct/set_sv96 | Deadline-based interval, жодного catch-up burst; при overrun пропустити слот/log. EMA α=1/8 і slew ≤16 APEX96/кадр — початкова гіпотеза, не tuned результат; не feedback на saturated/invalid sample. O(1) history, bounded metering CPU | Day/night transition, step light, flicker, missed deadlines, exposure continuity, no-space, cancel; порівняти fixed exposure і controller |
| Astro Sequence | shoot, Tv/Sv setters, set_raw_nr/get_raw_nr, get_tick_count. Long-exposure lights/darks для offline обробки | Обмежені count/exposure/session duration; optional dark strategy потребує ручної кришки/підтвердження, не «електронного закриття». Canon NR Auto/On/Off тільки через відомий API, відновлення. O(1) RAM, довгі exposures+write; температура/шум важливі, економія батареї не пріоритет | Реальна довга витримка/EXIF, світлі/темні кадри, час NR, star trails, каденс, timeout довший за exposure+NR+save, recovery |
| Motion Trigger | md_detect_motion/md_get_cell_diff, existing motion.lua; shoot | Bounded ROI/grid/threshold, timeout на очікування, cooldown і max captures; не busy loop. Detector використовує viewport, не RAW; latency не гарантує lightning trigger. RAM/CPU ростуть з grid/частотою. При cancel detector/script завершити штатним шляхом | Контрольований рух, noise/flicker false positives, recording vs playback, timeout без руху, cooldown, illumination changes і trigger-to-shutter latency |

Перед кодом звіряти назви API з export у `modules/luascript.c`, а не вигадувати
bindings. `get_focus_ok`, `get_focus_state`, `get_sd_over_modes` у поточному
source експортовані; це не доказ безпечного focus automation на цьому порту.
`rawop.create_histogram` allocation залежить від bits; 10-bit bins можуть
коштувати ~4 KiB counters плюс headers, але peak визначається реалізацією та
вимірюванням. Шість одночасних VM не плануються: один script за раз.

## Порядок поставки

Task004: спільний session contract + Night Stacker prototype без RAW hooks;
спершу host-side state/timeout tests із fake camera API, потім мала фізична серія.
Далі fixed HDR → adaptive HDR, Motion → Timelapse, Astro. Macro лишається blocked
до окремого firmware-address audit. Для кожного script перед bundle: syntactic
check у сумісній Lua, bounded state tests, fault injection, physical matrix,
документація settings/return behavior. Батарея — ресурс тривалості сесії, а не
критерій відмови від корисних CPU/RAM витрат.
