# Task004B — безпечний відкат і штатний Canon

Task004B development normal/diagnostic позначені в назвах ZIP; не змішувати їх
DISKBOOT і modules. Перед установкою зберегти всі фото, config, повне дерево SD
та відомі Task004/Task002A пакети. Нічого не пишемо у Canon flash, bootloader
assembly незмінний, фізична SD автоматично не змінюється.

1. Вимкнути камеру, UNLOCK і ввімкнути без Firmware Update. Перевірити штатне
   меню Canon, JPEG та відео, playback; на ПК перевірити читання нових файлів.
2. На поточній dual-partition карті окремо перевірити видиму місткість і розділ,
   куди Canon записав дані. UNLOCK не гарантує видимість великого FAT32 розділу.
3. Якщо stock бачить лише малий FAT16 або запис не працює, використовувати окрему
   резервну stock card з одним розділом, підтримуваним/відформатованим камерою.
   FAT32 stock card не обіцяє A590 CHDK autoboot. Окрема <=2 GB FAT16 карта може
   бути простішою для тестування CHDK+stock, але також перевірити фізично.
4. Для відкату на Task002A повернути **весь** його перевірений комплект і його
   backup config, а не один DISKBOOT. Зберегти новий config окремо, не переносити
   ABI3.7 навмання до старої версії. Не відновлювати розмітку без image backup.
5. LOCK → Task002A boot → JPEG/AF/zoom/video; UNLOCK → stock test знову.
   Записати package SHA і результати, зберегти failed package/CSV для аналізу.

Task002A source `398beedf0f50170fae2efd02884af11f7ea8e4fd`, PR3; відомі artifact
ідентифікатори та checksums збережені у попередніх installation/evidence docs.
Не виконувати format/partition commands як частину software build.

---
## Історична інструкція (не автоматичні дії)

# Відкат A590 IS до попереднього CHDK

> **Оновлення Task 004.** Для відкату Task 004 поверніть повний перевірений комплект Task 002A
> (1.7.0 r6346) разом із резервною копією конфіга. Не змішуйте новий
> DISKBOOT/модулі ABI 3.7 зі старими файлами. Наступні розділи також описують
> давніший відкат до 1.6.1 та відновлення розмітки; вони не є автоматичними діями.

Ці кроки виконує користувач вручну. Task 002A не змінює фізичну SD або ROM Canon.
Не відновлюйте лише один модуль чи PS.FI2 у дерево іншої версії.

## Швидко запустити штатний Canon

Вимкніть камеру, вийміть карту, переведіть перемикач у **UNLOCK**, вставте та
увімкніть. Без LOCK Canon не запускає DISKBOOT автоматично. Не обирайте
Firmware Update. Це обхід CHDK, а не повернення початкової розмітки карти.
У двохроздільній конфігурації штатний Canon може бачити лише малий перший том;
не продовжуйте фотографувати, доки не відновлено бажаний layout.

## Відновити попередній CHDK 1.6.1

1. Спершу збережіть на ПК нові фотографії з data-розділу та файли/повідомлення
   невдалого тесту. Не записуйте їх поверх перевіреної первісної backup-копії.
2. Якщо layout не змінювався, приберіть нове дерево CHDK, DISKBOOT.BIN,
   PACKAGE-MANIFEST.json, INSTALL, LICENSES та супровідні файли пакета після
   backup. Перевіряйте, що це саме нові файли; не видаляйте DCIM.
3. Якщо початкова карта була одним FAT32, а тепер має FAT16/два розділи,
   звичайне копіювання не поверне старий стан. Або відновіть перевірений
   **посекторний образ усієї SD** відповідним disk-imaging інструментом,
   звіривши фізичний пристрій, або вручну відновіть один MBR/FAT32 том через
   Disk Management. Останній шлях руйнівний: спочатку скопіюйте всі нові файли.
   Він відтворює придатний layout, але не початкові MBR/VBR побайтово.
4. Поверніть **всю** первісну файлову копію: старий CHDK, його PS.FI2,
   DISKBOOT.BIN (якщо був), фотографії та решту файлів. Приклад для вже
   підготовленого/перевіреного цільового тому:

```powershell
$backupRoot = 'C:\Users\YOUR_NAME\CHDK-backup-YYYYMMDD-HHMMSS' # фактична копія
$restoreRoot = 'E:\' # перевірена SD, не системний диск
Get-Partition -DriveLetter $restoreRoot.Substring(0,1) | Get-Disk | Format-List *
robocopy "$backupRoot\files" $restoreRoot /E /COPY:DAT /DCOPY:T /R:1 /W:1 /XJ
if ($LASTEXITCODE -ge 8) { throw 'Відновлення не завершено' }
$saved = Get-Content "$backupRoot\files-sha256.json" -Raw | ConvertFrom-Json
foreach ($entry in $saved) {
    $target = Join-Path $restoreRoot $entry.Path
    if ((Get-Item -LiteralPath $target -ErrorAction Stop).Length -ne $entry.Bytes -or
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.SHA256) {
        throw "Restore mismatch: $($entry.Path)"
    }
}
```

`robocopy /E` не прибирає зайвих нових файлів: тому потрібен чистий цільовий
CHDK/layout перед копіюванням. Тут навмисно немає автоматичного `/MIR`, raw-sector
write або `diskpart clean`. Повний disk-image restore знищує поточні дані карти.

5. Безпечно витягніть SD. Для попереднього способу запуску залиште **UNLOCK**,
   увімкніть камеру в Playback і скористайтеся її меню Firmware Update зі
   **старим PS.FI2 із перевіреної копії**. Він запускає старий CHDK, не є
   launcher для Task 002A. Перевірте стару версію 1.6.1 у Show Build Info.

Файлова backup-копія не містить boot flag і таблиці розділів. Якщо layout
залишається FAT16 з BOOTDISK, UNLOCK обходить autoboot, але не стирає маркер.
Для точного початкового стану потрібен образ диска; для старого ручного запуску
достатньо сумісного FAT32 layout, повного старого набору файлів і UNLOCK.
Не прошивайте сторонній Canon firmware і не перейменовуйте main.elf у PS.FI2.

## Що повідомити після невдалого тесту

Модель/Canon firmware, layout/розміри/FAT/cluster size, стан LOCK, checksum ZIP
та DISKBOOT, чи був splash, текст помилки, доступний простір, остання виконана
дія. Зберігайте ROMLOG лише якщо він доступний штатними засобами CHDK; не
запускайте низькорівневі діагностичні скрипти без окремого аналізу.
