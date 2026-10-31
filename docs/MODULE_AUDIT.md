# Аудит 38 FLT — r6346 / A590 101b

Машинний інвентар: [evidence/module-inventory.json](evidence/module-inventory.json).
Відтворення: `python tools/a590-baseline/audit_modules.py`. У CI інвентар
генерується заново й входить у кожний профіль. Для кожного модуля наведено
purpose, sources, static consumers із рядками, прямі/транзитивні залежності,
reverse module edges, category, включення, GUI/script наслідки й baseline hash/size.

Метод: правила `modules/Makefile`, wrappers `core/modules.c`, lib-pointer calls
у модулі та допоміжних sources, core/UI references, simple module metadata.
Conditional paths включені консервативно. Це не повний C call graph: виклики
через shared core callbacks, native calls і зовнішні скрипти вимагають ручного
аналізу. Саме тому дозволено вилучати лише перевірені автономні leaf modules.
Доданий статичний споживач/залежність такого leaf зупиняє генерацію інвентаря.

`mandatory` означає необхідний для збережених фотографічних/UI/script workflows,
не «кожен із цих FLT завантажується під час boot». `photography` — optional
photographic service, залишений для сумісності. `developer` — retained advanced
tool. `nonessential` — перевірений кандидат вилучення. `uncertain` — залишено,
доки немає перевірки конкретного сценарію/обладнання.

| FLT | Клас | Використання / причина рішення |
|---|---|---|
| 4wins | nonessential | Автономна гра, вилучено |
| _confmig | mandatory | Міграція старих CFG і script config IDs |
| _dng | mandatory | DNG, EXIF, bad pixels, конвертація |
| _hexbox | mandatory | Hex input Classic/debug UI |
| _osd_le | mandatory | OSD editor, викликає histo |
| _rawop | photography | RAW file merge/subtract; потрібний fselect/Lua |
| _tbox | mandatory | Textbox для fselect/Lua/Eye-Fi |
| benchm | developer | Бенчмарки; потрібні майбутні вимірювання |
| calend | nonessential | Автономний календар, вилучено |
| cpuinfo | developer | CPU діагностика |
| curves | photography | 10-bit curves, Lua/GUI; A590 має 10-bit RAW |
| edgeovr | photography | Edge overlay для композиції |
| exmemins | developer | EXMEM inspector; не вмикає allocation mode |
| eyefi | uncertain | Підтримка специфічної SD; не перевірена, залишено |
| fselect | mandatory | Браузер, вибір ресурсів, RAW operations |
| fshelter | developer | File shelter/backup; не вилучено без workflow tests |
| fwcrc | developer | Ручна CRC діагностика; не механізм boot revision guard |
| grids | photography | Композиційні сітки |
| histo | mandatory | Live histogram, Zebra, OSD editor |
| lua | mandatory | VM + shoot hooks + rawhookops |
| mastmind | nonessential | Автономна гра, вилучено |
| mdetect | photography | Lua/uBASIC motion detection |
| memview | developer | Classic memory viewer |
| modinsp | developer | Прямий core menu reference; module inspector |
| mpopup | mandatory | fselect/useredit/Eye-Fi popup |
| palette | mandatory | Вибір кольору та palette tests |
| rawevhst | photography | RAW EV histogram |
| reversi | nonessential | Автономна гра, вилучено |
| scrdump | developer | Display dump, майбутнє UI QA |
| shothist | photography | Script histogram range analysis |
| snake | nonessential | Автономна гра, вилучено |
| sokoban | nonessential | Гра і SOKOBAN.LEV, вилучено |
| sudoku | nonessential | Автономна гра, вилучено |
| tetris | nonessential | Автономна гра, вилучено |
| txtread | mandatory | Reader і відкриття тексту в fselect |
| ubasic | mandatory | Збереження .bas compatibility, motion/histogram APIs |
| useredit | mandatory | Редактор user menu та зовнішніх shortcuts |
| zebra | mandatory | Highlight warning, залежить від histo |

Ключові шляхи: `lua → fselect → {_dng,_rawop,_tbox,mpopup,txtread}`;
`lua → {curves,mdetect,shothist}`; `ubasic → {mdetect,shothist}`;
`useredit → {fselect,mpopup}`; `zebra/_osd_le → histo`;
`eyefi → {_tbox,mpopup}`. Зворотний `mdetect → lua/ubasic` — callback через
активний `libscriptapi`, не вимога одночасно тримати дві VM у RAM.
`_confmig` потрібний також API сумісності, а не лише одноразовому апгрейду CFG.
Lua `rawop.meter`/`rawop.create_histogram` реалізовано в `rawhookops.c` усередині
lua.flt; `_rawop.flt` — окремі файлові операції, їх не слід ототожнювати.

## RAM, GUI та script compatibility

`modules/module_load.c` завантажує FLT на вимогу, алокує code/data/BSS і звільняє
при unload; loader має тимчасовий 4096-byte read buffer. Видалення файла з SD
не скорочує text/data/BSS main.elf. Сума вилучених FLT — **34796 bytes** на SD
без урахування кластерів, SOKOBAN.LEV і ZIP compression. Не називати це free RAM.
Менше записів Games/Tools може зменшити heap цих меню після відкриття.

`core/gui.c:create_module_menu` читає ModuleInfo з наявних FLT: індивідуальних
пунктів вилучених модулів немає. Батьківські Games/Tools лишаються; порожній Games
слід перевірити фізично. Збережені user-menu module shortcuts не фільтруються
автоматично й дадуть load error. Чистий Photography install не містить старих
CFG. Не заявляємо сумісність довільних native-call скриптів, які прямо запускають
вилучені модулі. Full зберігає весь upstream набір як reference.

Автоматичні gates: exact 38 baseline records; 30-module dependency closure;
жодного вилученого FLT/level data в Photography; усі retained bytes тотожні Full;
Full відповідає Task001 hashes. Негативні тести перевіряють відсутню залежність,
повернуту гру, неправильний profile, відсутній/підмінений ресурс.
