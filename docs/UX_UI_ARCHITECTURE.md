# UX 2.0 — рішення Task004B для реалізації Task005

**Статус: архітектура; Task004 Photography UI ще чинний.** Не показувати майбутні
режими як кнопки, поки немає працюючої дії. Використати CMenu/gui_menu.c, existing
dirty rows, CP1251 builtin font та conf.photography_ui_mode (ABI3.7), без GUI engine.

360×240: 8×16 builtin cells; фактичну доступну ширину рахувати existing menu layout
(іконка/відступ/value/scrollbar), не всі 45 колонок віддавати label. Короткі назви,
контекст 1–2 рядки в existing message box при першому підтвердженні; екран на
камері — acceptance, ASCII mockup не є доказом читабельності.

| Домівка | Перший екран/дія | Advanced / залежність |
|---|---|---|
| Фотографувати | Return to Canon shooting, зведення активних overrides | Exposure settings, quick reset лише зі зрозумілим переліком |
| RAW / DNG | Вимкнено / DNG+JPEG, пояснення місця/обробки | RAW settings і read-only metadata за RAW_DNG_ROADMAP |
| Нічна зйомка | finite series preset, frame count, interval | Task008; не показувати до реалізації |
| HDR / Експозиція | supported bracketing settings зараз; smart sequence пізніше | Task007/008; позначати offline merge |
| Макро / Фокус | existing DOF/focus information, ручні поради | Авто stack прихований до focus_busy validation |
| Автоматична зйомка | перевірені scripts як режими, parameters + Start | Task008 session registry; не довільний filename launcher |
| Налаштування | мова, UI, Classic | Diagnostics тільки diagnostic/developer path |

Сім категорій — semantic map, не сім великих плиток. Звичайний прокручуваний
список, пам'ять позиції лише якщо це безпечно в existing menu; поширені RAW/Start
за 1–2 переходи. Встановлені категорії без робочих дій не відображати.
UP/DOWN вибір, SET відкрити/підтвердити, existing LEFT/Back і MENU з незмінною
семантикою; shutter/ALT/Canon keys не перехоплювати новими global shortcuts.
Повернення до Canon зберігає явні активні overrides, показувати їх перед стартом.

Чотири рівні: simple knobs → named presets з summary → advanced actual parameters
→ developer diagnostics. Preset показує зміни shutter/ISO/RAW/NR і спосіб restore;
не приховувати storage/time/cancel. Помилка missing Lua/script — коротке повідомлення,
повернення до попереднього меню; ніякої неактивної кнопки «незабаром».
Classic завжди досяжний з Налаштувань, джерела upstream capabilities не видаляти.
Persist лише реальні зміни; нові prefs append-only з migration/default tests.

Task005 tests: 360×240 UA labels, long values, scrolling/text gaps, back from each
submenu, PLAY/REC, half/full shutter, active script guard, language/mode persistence,
missing resources, rapid key input, no-op writes, before/after p50/p95 and RAM.

---
## Історична архітектура (деталі контексту)

# Фотографічний UI: проєкт архітектури

> **Оновлення Task 004.** Task 004: Photography UI тепер реалізовано в `core/gui_photo.inc`,
> з інтеграцією в gui.c/conf.c та чинний menu engine. Classic і збереження
> вибору працюють без перезапуску на рівні коду; фізична перевірка ще потрібна.
> [Фактична ієрархія та checklist](PHOTOGRAPHY_UI.md). Нижче — попередній дизайн.

Статус Task003: **дизайн, не реалізований UI**. Shared runtime не змінюється;
обидва профілі запускають Classic як раніше. Окремий rendering engine недоцільний:
наявні `CMenu/CMenuItem`, `core/gui_menu.c`, `core/gui.c`, `gui_set_mode`, RBF
і user menu вже забезпечують потрібні операції. Ввести ще один framework
означало б дублювати input, redraw та збереження налаштувань без виміряної користі.

## Дерево для логічного екрана 360×240

| Коренева категорія | Вкладені функції / reuse |
|---|---|
| Зйомка | RAW/DNG; ISO; витримка; діафрагма/override; reset overrides |
| Експозиція | Histogram; Zebra; поточний bracketing; Auto ISO; майбутній highlight mode |
| Фокусування | Macro/Canon MF пояснення; edge overlay; focus stack недоступний до gate |
| Розумні режими | HDR, Night, Macro, Timelapse, Astro, Motion — лише реально встановлені/допущені scripts |
| Налаштування | Language/font; OSD; user menu; Simple/Classic; build info; Advanced |

Назви encoded CP1251 через numeric LANG IDs, не UTF-8 literals у C renderer.
A590 має iris, не ND; не пропонувати ND пункт. Canon mode, AE/AF і JPEG engine
не дублюються: показати, коли CHDK override не застосовний, не вдавати контроль
пропрієтарного ISP. Режим «захист світел» до реалізації/перевірки не показувати
як готову функцію. Пункт Macro Stack повинен пояснювати, чому недоступний.

Прототип: 5 категорій, заголовок і status/footer. Built-in font 8×16 дає
45 символів на всю ширину, але рамки, символ і value column зменшують бюджет.
Ціль: label ≤26 символів (~208 px), 80 px для value, 24 px для icon/margins;
перевіряти фактично через `rbf_str_width`, бо RBF має інші метрики.
Один екран не зобов'язаний показувати всі settings — використовувати scroll
існуючого меню; не зменшувати текст до нечитабельного для додаткових рядків.

## Навігація і кнопки

`platform/a590/kbd.c`: Print/Shortcut → ALT; у ALT MENU відкриває CHDK menu,
стрілки рухаються/змінюють значення, SET підтверджує/входить. MENU/Back повертає
за чинними правилами engine; Print виходить з ALT. Поза ALT Canon кнопки та
half/full-shutter залишаються штатними. Не перехоплювати zoom/shutter глобально.
В A590 для Playback є фізичний mode switch, живлення ON/OFF.

Quick access: використати `core/gui_user_menu.c` і `useredit.flt`, а не нову
панель. Стартовий набір: RAW/DNG, ISO, Tv, bracketing step/count, Zebra, script
selection. Наявні `conf.user_menu_enable`/`user_menu_as_root` і half-press+MENU
перемикають доступ до user/root menu (`core/gui.c:gui_menu` logic). Зберегти ці
правила, не конфліктувати із запуском/зупинкою scripts кнопкою спуску в ALT.

## Simple / Classic без перезавантаження

Наступна реалізація: маленький selector повертає `&photo_root_menu` або
`&root_menu` при вході, existing submenu settings/callbacks повторно
використовуються. Якщо static visibility заважає — винести вузький accessor
у тому самому translation unit, не копіювати великі таблиці settings.
Перемикати тільки коли немає активного modal/file selector/script/RAW hook;
завершити submenu navigation і `gui_menu_init(selected_root)`/redraw, скинути
стек навігації. Hardcoded повернення до `root_menu` у `core/gui_menu.c` теж
мають пройти через selector, інакше Back поверне не той інтерфейс.
Наразі технічної необхідності restart для UI switch не виявлено; це слід
підтвердити тестами, а не оголосити готовою можливістю.

Persistence: нове поле `Conf` enum {CLASSIC=0, PHOTO=1} і **вільний новий ID**
у відповідному CONF_INFO domain після повного аудиту IDs. Не використовувати
старі IDs і не змінювати on-disk layout вручну. Unknown/corrupt value → CLASSIC.
Не перезаписувати user_menu configs. Save на підтвердження зміни через existing
conf save, не кожен redraw. Відсутній ID у старому CFG → default Classic.
Оновити generated cnf Lua mappings; зміна ABI/shared code вимагатиме нового
binary baseline та повної регресії, не підміни Task001 checksum.

## Вартість і gate

Task003 code/data/BSS delta **0/0/0**. Майбутні таблиці дадуть додаткові rodata
та pointer entries; точного прогнозу без linked ELF не робимо. Бюджет рішення:
виміряти `arm-none-eabi-size/nm`, heap/largest block при 100 mode switches,
menu redraw latency і відсутність росту allocation. Не додавати frame buffer
360×240 або shadow copy всієї конфігурації без потреби.

Acceptance: усі Classic settings доступні, Simple↔Classic без restart і
memory leak, user menu збережене, строки читабельні українською, RAW/video/AF
регресій немає. Цей gate передує ввімкненню Simple за замовчуванням.
