# Canon A590 IS GM1.01B — встановлення CHDK у Windows

Пакет `CHDK-A590IS-101B-1.7.0-r6346-full.zip` призначений тільки для **A590 IS,
Canon GM1.01B**, CHDK 1.7.0 r6346. Це кандидат для контрольованого фізичного тесту:
CI перевіряє файли. Користувач підтвердив базові фізичні тести r6346 із Task 002A;
нові профілі Task003 ще не перевірені (див. HARDWARE_TEST_MATRIX.md у репозиторії).
Постійна прошивка Canon не змінюється.
Жодна команда підготовки карти не запускається CI або скриптами цього репозиторію.

## 1. Що підтримує камера

A590 має DryOS R23 (`platform/a590/sub/101b/stubs_entry.S`). Для autoboot потрібен
**FAT16**, файл `DISKBOOT.BIN` у корені boot-розділу, маркер `BOOTDISK` у VBR
за зміщенням **0x40 (64)** та фізичний перемикач SD **LOCK**. Поточний одиночний
FAT32-розділ не придатний для цього способу запуску. FAT32 boot-marker 0x1E0,
що використовується новішими камерами, тут не допоможе.
[CHDK: Prepare your SD card](https://chdk.fandom.com/wiki/Prepare_your_SD_card).

Код порту має `CAM_MULTIPART=1`; `platform/a590/sub/FAT32_detect.S`, викликаний із
`101b/boot.c`, вибирає FAT32 data-розділ. Отже, підтримка двох розділів є у цьому
build. Це перевірка коду, не результат випробування конкретної карти.
`platform/generic/wrappers.c:mark_filesystem_bootable` підтверджує для старого
DryOS маркер 0x40. BOOTDISK знаходиться у boot-sector **розділу**, не в MBR диска.

| Варіант | Висновок для цієї камери |
|---|---|
| Поточні 4 GB, один FAT32 | Старий PS.FI2 може запускати старий CHDK; новий DISKBOOT сам не завантажиться |
| Один FAT16 до 2 GiB | Простий варіант першого тесту; решту місткості 4-GB карти можна залишити нерозподіленою |
| Усі 4 GB одним FAT16 | Можливий із 64-KiB кластерами, але сумісність не гарантована |
| Перший FAT16 32 MiB + решта FAT32 | Підтримується кодом A590; зберігає майже всю місткість зі звичайними кластерами; складніше підготувати/відкотити |

FAT16 понад 2 GiB потребує 64-KiB кластерів — це варіант з обмеженою сумісністю
реалізацій FAT; не вважати його гарантовано надійним для A590, ридера та всіх ОС.
[CHDK FAQ](https://chdk.fandom.com/wiki/FAQ). Windows `format.com` допускає
`/FS:FAT /A:64K`, але підтримка команди не доводить сумісності камери.
[Microsoft format](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/format).

**Рекомендація для наявної 4-GB карти:** після перевіреної резервної копії, якщо
потрібна вся місткість, використати перший **32-MiB FAT16** boot-розділ і решту
**FAT32** для фотографій та CHDK. Це усуває ризик 64-KiB кластерів, але додає ризик
помилки під час розмітки. Якщо є запасна карта до 2 GB, перший тест простіше
провести на ній, залишивши стару карту недоторканою. Форматування не потрібне,
коли вже є відповідний FAT16 boot-розділ; для описаної користувачем одиночної
FAT32 карти зміна файлової системи/розмітки необхідна саме для цього пакета без
PS.FI2. Безпечне автоматичне перетворення FAT32→FAT16 тут не пропонується.

## 2. Підготовка та резервна копія — перед будь-якою зміною

Вимкніть камеру, вийміть SD, переведіть у UNLOCK і вставте в ридер.
У PowerShell перегляньте диски; **не підставляйте букву системного диска**:

```powershell
Get-Disk | Format-Table Number,FriendlyName,SerialNumber,BusType,PartitionStyle,Size
Get-Partition | Format-Table DiskNumber,PartitionNumber,DriveLetter,Size,Type
Get-Volume | Format-Table DriveLetter,FileSystemLabel,FileSystem,Size,SizeRemaining
$sdDrive = 'E' # ЗАМІНИТИ після перевірки розміру і моделі ридера
$sdRoot = "${sdDrive}:\"
Get-Partition -DriveLetter $sdDrive | Get-Disk | Format-List *
$backupRoot = Join-Path $env:USERPROFILE ('CHDK-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -ErrorAction Stop | Out-Null
robocopy $sdRoot "$backupRoot\files" /E /COPY:DAT /DCOPY:T /R:1 /W:1 /XJ
if ($LASTEXITCODE -ge 8) { throw 'Резервне копіювання не завершене' }
Get-Disk | Format-List * | Out-File "$backupRoot\disks.txt"
Get-Partition | Format-List * | Out-File "$backupRoot\partitions.txt"
Get-Volume | Format-List * | Out-File "$backupRoot\volumes.txt"
$backupManifest = @(Get-ChildItem -LiteralPath $sdRoot -File -Recurse -Force | ForEach-Object {
    $relative = $_.FullName.Substring($sdRoot.Length)
    $sourceHash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    $copyPath = Join-Path "$backupRoot\files" $relative
    if ((Get-FileHash -LiteralPath $copyPath -Algorithm SHA256 -ErrorAction Stop).Hash -ne $sourceHash) {
        throw "Помилка копії: $relative"
    }
    [pscustomobject]@{Path=$relative; SHA256=$sourceHash; Bytes=$_.Length}
})
$backupManifest | ConvertTo-Json -Depth 3 | Set-Content "$backupRoot\files-sha256.json" -Encoding UTF8
```

Копія має включати **DCIM, усю CHDK 1.6.1, PS.FI2, DISKBOOT.BIN та інші файли**,
якщо вони є. Відкрийте кілька фотографій із копії. Зберігайте її на комп'ютері,
не на цій SD. Якщо читання/хешування повідомило помилку — зупиніться.

**Форматування знищує файли, зміна розділів може знищити весь їхній вміст.**
Звичайна файлова копія не зберігає MBR, VBR, BOOTDISK чи таблицю розділів.
Для точного повернення до початкового стану потрібен перевірений посекторний
образ усієї карти, створений окремим disk-imaging інструментом, або відновлення
початкової розмітки й файлів вручну. Див. [SD_ROLLBACK.md](SD_ROLLBACK.md).

## 3. Підготовка файлової системи — лише якщо потрібна

Це окрема **ручна, руйнівна** операція користувача після резервного копіювання.
Не виконуйте її для вже сумісної карти. Далі наведено порядок, а не автоматичний
скрипт вибору/очищення диска.

Для рекомендованих двох розділів потрібна Windows 10 1703+ або Windows 11, де
доступні кілька розділів removable USB media
([Microsoft](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/winpe--use-a-single-usb-key-for-winpe-and-a-wim-file---wim?view=windows-11)).

1. Відкрийте `diskmgmt.msc`, звірте номер, місткість і пристрій із результатом
   `Get-Disk`; від'єднання/повторне під'єднання ридера допомагає його впізнати.
2. Після backup видаліть **лише том(и) цієї SD**. Використовуйте розмітку MBR.
   Якщо карта GPT або Windows не дозволяє створити потрібні розділи, зупиніться:
   не застосовуйте навмання `clean` до диска. Для цього сценарію потрібна
   окремо контрольована підготовка MBR або проста запасна FAT16 карта.
3. На початку створіть primary simple volume **32 MB**, призначте вільну букву
   (приклад `B:`), поки не форматуйте. Потім створіть другий primary volume
   на решті простору, буква, наприклад, `F:`, FAT32. Не використовуйте exFAT,
   NTFS, GPT, logical/extended partitions.
4. Перевірте через `Get-Partition`, що FAT16 буде **першим**. Наступні команди
   форматують лише вже створені, звірені томи. Букви B/F — приклади, їх потрібно
   замінити; запуск від адміністратора може бути потрібним:

```powershell
# УВАГА: ЗНИЩУЄ ФАЙЛИ НА ВКАЗАНИХ ТОМАХ. Тільки після backup та перевірки букв!
format.com B: /FS:FAT /A:4096 /V:CHDKBOOT
format.com F: /FS:FAT32 /V:CHDKDATA
Get-Volume -DriveLetter B,F | Format-Table DriveLetter,FileSystem,Size,AllocationUnitSize
Get-Partition -DriveLetter B,F | Format-Table DiskNumber,PartitionNumber,DriveLetter,Size
```

32 MiB з кластерами 4096 bytes забезпечує FAT16, а не FAT12. Очікується FAT
на B: та FAT32 на F:. Windows зазвичай показує FAT16 як `FAT`. Обидва томи
мають належати одній SD. Якщо бачите лише один із них — не продовжуйте копіювання
на припущену букву; перевірте ридер, ОС і призначення букв.

**Альтернативи:** один FAT16 до 2 GiB із рештою нерозподіленою або вся карта
одним FAT16. Для останнього після backup можна вручну виконати
`format.com E: /FS:FAT /A:64K /V:CHDK`, але враховуйте описане обмеження сумісності.
Не підтверджуйте попередження Windows, не розуміючи його; якщо format відмовляє,
не обходьте перевірки сторонніми force-опціями. FAT16/64K не є рекомендованим
першим тестом на цій 4-GB карті.

## 4. Перевірка й розпакування пакета на ПК

Завантажте artifact **CHDK-A590IS-101B-1.7.0-r6346-full** із успішного запуску
Actions потрібного PR. GitHub може вимагати вхід. Зовнішній Actions ZIP містить
внутрішній установочний ZIP, `.sha256` і `.json`; спочатку розпакуйте оболонку.
Не копіюйте ZIP як один файл на SD. Значення checksum порівняйте також зі звітом
CI/PR; checksum поруч із файлом виявляє пошкодження, а не засвідчує автора.

```powershell
$downloadDir = Join-Path $env:USERPROFILE 'Downloads\CHDK-full-artifact'
$zipPath = Join-Path $downloadDir 'CHDK-A590IS-101B-1.7.0-r6346-full.zip'
$expectedHash = ((Get-Content ($zipPath -replace '\.zip$', '.sha256')).Trim() -split '\s+')[0]
if ((Get-FileHash $zipPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'ZIP SHA-256 mismatch' }
$stage = Join-Path $env:USERPROFILE ('CHDK-stage-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
Expand-Archive -LiteralPath $zipPath -DestinationPath $stage -ErrorAction Stop
$manifest = Get-Content "$stage\PACKAGE-MANIFEST.json" -Raw | ConvertFrom-Json
if ($manifest.identity.platform -ne 'a590' -or $manifest.identity.firmware -ne '101b' -or
    $manifest.identity.chdk -ne '1.7.0' -or $manifest.identity.svn -ne 6346) { throw 'Wrong build' }
foreach ($entry in $manifest.files) {
    $file = Join-Path $stage $entry.path
    if ((Get-Item -LiteralPath $file -ErrorAction Stop).Length -ne $entry.bytes -or
        (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.sha256) {
        throw "Package mismatch: $($entry.path)"
    }
}
$expectedModules = if ($manifest.profile -eq 'photography') { 30 } else { 38 }
if ((Get-ChildItem "$stage\CHDK\MODULES\*.flt").Count -ne $expectedModules) { throw 'Wrong module count' }
```

Вміст: DISKBOOT; 38 FLT; повне upstream дерево CHDK із SCRIPTS, LANG, FONTS,
SYMBOLS, GRIDS, DATA, CURVES, BOOKS, GAMES, HELP, LUALIB (включно з GEN);
upstream readme/changelog/camnotes/vers.req; LICENSES, ці інструкції і manifest.
`cnf_*.lua` — згенеровані описи конфігурації для скриптів. Власні `.CFG`
камера створить при роботі; старі налаштування/модулі 1.6.1 не переносити.
`main.elf`, `PS.FI2`, `PS.FIR` у пакеті відсутні.

## 5. Копіювання та BOOTDISK

Використовуйте порожнє дерево CHDK: не накладайте пакет поверх 1.6.1.
Якщо форматування не було, після backup перемістіть старі CHDK, DISKBOOT.BIN,
PS.FI2 у backup на ПК і приберіть їх із карти вручну, не видаляючи фотографії.
**Старий PS.FI2 запускає старий CHDK 1.6.1, а не новий DISKBOOT 1.7.0.**

Підставте фактичні букви. Для однороздільного FAT16 обидва значення однакові.
У двохроздільному варіанті DISKBOOT іде на перший FAT16, решта — на FAT32:

```powershell
$bootRoot = 'B:\' # FAT16 boot
$dataRoot = 'F:\' # FAT32 data; для одного FAT16: також B:\
Copy-Item -LiteralPath "$stage\DISKBOOT.BIN" -Destination $bootRoot -ErrorAction Stop
Get-ChildItem -LiteralPath $stage | Where-Object Name -ne 'DISKBOOT.BIN' | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $dataRoot -Recurse -ErrorAction Stop
}
foreach ($entry in $manifest.files) {
    $targetRoot = if ($entry.path -eq 'DISKBOOT.BIN') { $bootRoot } else { $dataRoot }
    $target = Join-Path $targetRoot $entry.path
    if ((Get-Item -LiteralPath $target -ErrorAction Stop).Length -ne $entry.bytes -or
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.sha256) {
        throw "SD verification failed: $($entry.path)"
    }
}
```

Для встановлення прапорця використайте **EOScard у режимі CHDK** за
[інструкцією CHDK EOScard](https://chdk.fandom.com/wiki/EOScard) (посилання на
інструмент/архіви є на цій сторінці; його виконуваний файл у пакет не входить).
Запустіть від адміністратора, виберіть перевірену SD і **перший FAT16 том**,
натисніть логотип CHDK/оберіть `BOOTDISK`. Не використовуйте режим Magic Lantern,
`EOS_DEVELOP` або `SCRIPT`. Для FAT16 напис `BOOTDISK` має бути за 0x040.
Натисніть **Save**, перевідкрийте том у програмі та перевірте маркер. EOScard
встановлює boot flag; він не перетворює FAT32 на FAT16. Якщо програма не дає
однозначно вибрати FAT16 том/показує іншу файлову систему, зупиніться.
Не застосовуйте необґрунтоване ручне записування raw sectors із PowerShell.

## 6. Перший запуск та фізичні перевірки

1. Безпечно витягніть обидва томи/ридер у Windows. Перемкніть SD у **LOCK**.
   Canon перевіряє LOCK для autoboot; завантажений CHDK дозволяє запис фотографій.
2. Із зарядженими акумуляторами вставте карту у вимкнену A590 GM1.01B.
   Встановіть перемикач режиму в Playback і натисніть ON/OFF
   ([інструкція Canon A590 IS](https://gdlp01.c-wss.com/gds/6/0400000016/01/PSA590IS_CUG_EN.pdf),
   Viewing Still Images). Не запускайте Firmware Update.
3. Перевірте splash CHDK, вхід в ALT кнопкою Print/Shortcut, меню CHDK →
   Miscellaneous Stuff → Show Build Info: камера a590, firmware 101b,
   version 1.7.0, revision 6346. Запишіть/сфотографуйте ці значення.
4. Спершу залиште default English/default settings. Перевірте меню, символи,
   file browser, вільний простір (у двохроздільному варіанті близький до всіх 4 GB,
   не 32 MB), вихід з ALT, звичайний JPEG, його перегляд та запис на ПК.
5. Окремо перевірте перезапуск, коректне вимкнення, простий interval script,
   RAW/DNG за потреби, вибір шрифту/мови. Український переклад upstream неповний
   (435 із 672 ID за Task 001); це не ознака іншої версії пакета.
6. Не запускайте довільні SCRIPTS/TEST: upstream містить низькорівневі діагностичні
   скрипти, що не є обов'язковою перевіркою встановлення.

Якщо немає splash, є помилка module/resource, зависання або лише 32 MB для фото —
вимкніть камеру; якщо вона не реагує, дочекайтеся припинення доступу до карти та
вийміть акумулятори. Для перевірки штатного Canon запустіть із **UNLOCK**:
автоматичний CHDK має бути обійдений. Подальший відкат описаний окремо.
Наявність правильної структури та успішного CI не доводить апаратної стабільності.
