# RAW/DNG: аудит Task004B, план Task006

Task004 capture працює за повідомленням користувача. Оригінальних DNG у workspace
немає; незалежного pixel/metadata/decode підтвердження Task004B немає. RAW pipeline
у цьому PR не змінено. Джерела: platform/a590/platform_camera.h, core/raw.c,
modules/dng.c, modules/rawhookops.c, core/gui.c, include/conf.h.

## Реальні дані A590

3336×2480, packed 10-bit: 10 341 600 bytes на RAW buffer (~9.86 MiB).
Active area x12..3300, y10..2480; JPEG 3264×2448. CFA 0x01000201 (GBRG),
black=31, white=1023 у поточному коді, daylight illuminant і CAM_COLORMATRIX1.
Це перевірка source constants, не лабораторне калібрування сенсора.
Один фактичний RAW buffer: alt pointer не дає незалежного другого кадру.
DNG byte reversal/restoration та cache handling не можна просто прибрати.
Thumbnail 128×96×3 = 36864 bytes плюс header; потрібен heap reserve.

## Три рівні UX (ще не реалізовані)

| Рівень | Реальні параметри | Межі |
|---|---|---|
| Простий | conf.save_raw, conf.dng_raw; RAW+штатний JPEG; підтримуваний каталог/іменування | RAW не замінює Canon JPEG; +~10 MB/кадр, повільніше збереження |
| Профілі | Standard DNG; post-processing DNG+JPEG; low-light series з явним NR; HDR exposure sequence; macro після validation | Профілі конфігурують capture/storage, не додають bit depth/DR |
| Advanced | bad-pixel workflow, DNG version, RAW prefix/extension/directory та NR з наявного меню | Додати пояснення й перевірку сумісності, не вигадані setters |
| Read-only diagnostics | CFA, black/white, color matrix, WB/AsShotNeutral, active area, buffer dimensions/timing | Source constants/calibration не перетворювати на довільні sliders |

Відокремити доступні configuration knobs від metadata inspection. WB metadata
не застосовує denoise до сенсорних значень. Для зміни black/white/matrix потрібні
калібровані зразки, versioned profile та відкат; не Task004B.

## Пріоритети надійності

1. **Write/error paths:** core/raw.c не перевіряє всі результати write; DNG header/chunk
   writes та task creation також потребують перевірок. Аудит ownership header і
   cleanup після allocation/open/task failures. Це source risks, не відтворені
   користувацькі дефекти. Не додавати частковий fix без restore-buffer тестів.
2. Fault injection: full SD, short write, open/alloc failure, interrupted save.
   Гарантувати RAW buffer restoration, unblock capture, cleanup і зрозумілу помилку;
   не видаляти оригінал до перевірки. Power-loss atomicity — окремий дизайн.
3. DNG correctness: IFD offsets/counts, strip bounds, dimensions/crop, CFA,
   BitsPerSample, BlackLevel/WhiteLevel, ColorMatrix1/CalibrationIlluminant1,
   AsShotNeutral, bad pixels. Звіряти з фактичним decode, не лише exif listing.
4. Throughput: одна карта, ті самі експозиція/NR; серії JPEG, RAW, DNG;
   median/max save time і free/largest до/після. Оптимізувати тільки знайдений hot path.

## Зразки й критерії

Зберегти незмінені DNG+JPEG, SHA256, firmware/build, exposure/ISO/WB/NR/card.
Набір: денне світло з нейтральною мішенню, кольори, глибокі тіні, highlights,
коротка/довга витримка, dark frame з кришкою, різні ISO. Не перезаписувати masters.
Перевірити RAW mosaic bounds і clipping, metadata, відкрити двома незалежними
конвертерами (записати точні версії/settings), порівняти crop/color/highlights.
Color accuracy потребує мішені й контрольованого освітлення. Розрізняти input RAW
і render differences. Жодних заяв про якість за самими тегами.

Первинний нормативний reference: [Adobe DNG specification 1.7.1](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf).
Наявний CHDK DNG version не піднімати автоматично до версії специфікації.
