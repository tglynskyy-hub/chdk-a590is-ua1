# Фотографічний UI: проєкт архітектури

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
