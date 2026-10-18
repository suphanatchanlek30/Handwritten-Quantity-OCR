# Architecture

`qty_ocr` แยกงานเป็นโมดูลเล็กตามลำดับข้อมูล เพื่อให้เปลี่ยนวิธีหาตารางหรือวิธีอ่านตัวเลขได้โดยไม่กระทบผลลัพธ์ส่วนอื่น

```text
image -> load -> locate table -> crop qty cells -> detect ink
      -> prepare variants -> recognize -> decide/review -> export
```

| ขั้น | โมดูลหลัก | หน้าที่ |
|---|---|---|
| Load | `image_loader.py` | อ่านภาพ, ใช้ EXIF orientation และตรวจ input |
| Locate | `layout.py`, `alignment.py`, `table_detector.py` | หาตาราง, ปรับ perspective และเลือกคอลัมน์ qty |
| Crop | `roi_extractor.py`, `blank_detector.py` | ตัดแต่ละช่องและแยก blank/nonblank/uncertain |
| Recognize | `preprocessing.py`, `recognizer.py`, `digit_decoder.py` | สร้างภาพสำหรับ OCR และถอดผลเป็นตัวเลข |
| Decide | `postprocessing.py` | เลือก candidate, ตรวจรูปแบบ และกำหนด review reasons |
| Export | `exporter.py`, `visualization.py` | สร้าง JSON, CSV, summary และภาพ debug |

## จุดเริ่มต้น

- CLI: `src/qty_ocr/cli.py`
- Pipeline ภาพเดียว: `process_document()` ใน `pipeline.py`
- Pipeline batch: `process_many()` และ `process_many_parallel()`
- โครงสร้างผลลัพธ์: `schemas.py`

## ข้อตกลงสำคัญ

- ภาพภายใน pipeline เป็น BGR ของ OpenCV
- bounding box ใช้ `(x0, y0, x1, y1)` ยกเว้น OpenCV component box ที่ระบุชัดว่า `(x, y, w, h)`
- pipeline หลักใช้ config ที่ผ่าน `load_config()` และ `validate_config()`; อย่าเพิ่ม threshold ใหม่แบบ hard-code
- recognizer คืนผลตามลำดับ input เสมอ เพื่อให้จับคู่กับ cell ได้อย่างปลอดภัย
- `FieldResult.status` และ `review_reasons` เป็น contract ของผลลัพธ์ภายนอก

## การเปลี่ยนแปลงที่แนะนำ

เพิ่ม test ที่ seam ของโมดูลก่อนแก้ pipeline, รัน `python -m pytest -q`, แล้วตรวจ `results.json` และ overlay กับภาพจริง. ดูเกณฑ์การตัดสินที่ [Decision logic](DECISION_LOGIC.md)
