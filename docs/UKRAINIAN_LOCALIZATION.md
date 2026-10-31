# Українська локалізація — фундамент і план

> **Оновлення Task 004.** Task 004 реалізовано: 728/728 числових ID (672 попередні + 56 нових),
> 237 пропусків заповнено, 107/109 виправлено, CP1251 збережено.
> `test_locale.py` перевіряє форматні контракти, гліфи, кодування, дублікати,
> буфери, 7-символьні enum та ширину пунктів Photography. Нижче — історичний
> аудит Task 003; актуальні правила й перевірки: [Photography UI](PHOTOGRAPHY_UI.md).

Повторний source audit r6346: **672 English IDs, 435 Ukrainian IDs, 237 відсутніх**.
`python tools/a590-baseline/audit_locale.py` генерує missing/extra/duplicates,
порожні/English-identical IDs, printf signatures, приблизні width warnings,
source glyph coverage. CI зберігає `locale-inventory.json`; tracked snapshot
Task003: [evidence/task003-locale.json](evidence/task003-locale.json).
Поточний `.lng` у цьому завданні не змінюється.

Знайдено **два існуючі format mismatches**: ID107 має 7 `%s` замість 8;
ID109 має лише `%d` замість `%d`, `%d`, `%X`. Це застарілі рядки build/memory
інформації; відсутні placeholders приховують інформацію. Не називаємо їх доказом
крашу, але виправлення потрібне до default-UA. 4 рядки мають приблизну ширину
понад 280 px при 8 px/символ; 4 значення ідентичні English (абревіатури/терміни
треба переглянути вручну, не механічно перекладати).

## Encoding, glyphs і fallback

`CHDK/LANG/ukrainian.lng` — Windows-1251. Built-in `font_8x16_uni.h` і
`codepages.h:cp_win_1251` містять **ҐґЄєІіЇї**; перевірено таблиці source, не
фотографію LCD. `include/font.h` розрізняє built-in FONT_CP_WIN_1251=1 та
RBF FONT_CP_WIN=0: не плутати ці різні enums. Обраний користувачем зовнішній RBF
може не містити всіх glyphs; потрібен тест built-in і кожного рекомендованого
RBF. Apostrophe — CP1251-compatible символ; не вводити нерепрезентовані символи.

`lib/lang/lang.c` спочатку завантажує built-in strings, потім накладає locale
лише для наявних у port IDs. Missing ID зберігає English fallback; порожній
рядок не використовувати як спосіб fallback. `rbf_font.c` рендерить байтові
рядки; UTF-8 послідовності зламають ширину/індексацію без нового decoder.
UTF-8 renderer тут не вводиться. Git/редактор можуть працювати з UTF-8 master
catalog у майбутньому, але build export має строго encode CP1251 без replacement.

## Пам'ять і layout

Поточна верхня оцінка суми Ukrainian strings із NUL до escape/port filtering:
**8437 bytes**. Це не загальна locale peak RAM. Loader також тримає file buffer,
тимчасовий масив pointers (4 bytes на ARM entry), short offset table, language
buffer; offset закодований від'ємним `short` як `-(1+offset)`. Повний переклад
має тримати offset у signed16 range, консервативно total locale bytes <32767,
і перевірити peak heap під час switch. Не вважати вільними всі 32 MB RAM.

Width audit не враховує `\n` decoding/форматовані runtime values до кінця й
не є остаточним layout test. Перевіряти готові messages з найдовшими values,
menu label/value columns, назви файлів і підтвердження. Скорочувати переклад
за значенням, не обрізати байти автоматично. `%s/%d/%X`, length modifiers,
`*` width/precision та порядок аргументів зберігати; `%%` не є аргументом.

## Послідовність реалізації Task004

1. Додати строгий locale validator (duplicate/out-of-range/encoding/escape,
   printf argument signature та signed-offset bounds). Спершу окремо зафіксувати
   існуючі defects; не вимикати перевірку всієї локалі через два відомі рядки.
2. Виправити 107/109; перекласти 237 IDs у тематичних групах: shooting/exposure,
   scripts, settings, diagnostics. Зберегти числові IDs, не перенумеровувати.
3. Терміни: «Витримка», «Діафрагма», «Експокорекція», «Брекетинг»,
   «Пересвічення», «Фокусування»; RAW/DNG/ISO лишити усталеними скороченнями.
   Незрозумілі режими супроводити коротким help, не вигаданою обіцянкою якості.
4. Виміряти bytes/peak heap, прогнати форматовані повідомлення й width warnings.
   LCD proof: glyph chart, кожне меню, діалоги, script params, English fallback,
   пошкоджений/відсутній `.lng`, restart після збереження вибору.
5. Лише після цього запропонувати Ukrainian default для нового enhanced profile.
   Full compatibility reference поки зберігає upstream defaults. Existing CFG
   language не перезаписувати; передбачити простий вибір English у Classic.

Acceptance: 0 missing active IDs, 0 incompatible formats, усі українські glyphs
читабельні, немає обрізання важливих значень, measured memory headroom і fallback
підтверджені. Факт наявності перекладу в пакеті сам по собі цього не доводить.
