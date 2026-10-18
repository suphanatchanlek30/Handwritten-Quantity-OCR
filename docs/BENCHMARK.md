# Validation and benchmarks

เอกสารนี้กำหนดวิธีรายงานผล ไม่เก็บผลรันเก่าหรือ artefact ที่สร้างใหม่ได้ไว้ใน Git

## สิ่งที่ต้องยืนยันก่อนรายงานตัวเลข

- ใช้ labels ที่มนุษย์ยืนยันแล้วเท่านั้น
- ระบุจำนวนภาพ, จำนวนช่อง, รูปแบบภาพ และ configuration ที่ใช้
- แยก `ok`, `needs_review`, `invalid_text` และตรวจว่าค่าผิดหลุดเป็น `ok` กี่ช่อง
- ระบุเครื่อง, Python, engine และเวอร์ชัน dependency เมื่อรายงาน performance

ข้อมูล `annotations.draft.json` และ label ที่มีสถานะ draft ใช้สำรวจได้ แต่ห้ามใช้เป็นตัวเลขความแม่นยำ

## คำสั่งตรวจสอบ

```bash
# Unit / integration tests
python -m pytest -q

# ตรวจ OCR environment และ model cache
python scripts/check_environment.py

# วัด pipeline พร้อมบันทึกผลไว้นอก Git
python scripts/profile_pipeline.py --inputs data/samples --repeat 3 \
  --save-results outputs/validation

# ประเมินผลจาก labels ที่ verified
python -m qty_ocr.cli evaluate \
  --predictions outputs/DOCUMENT_ID/results.json \
  --ground-truth path/to/verified-ground-truth.json
```

## Baseline ใหม่

เมื่อเปลี่ยน preprocessing, OCR engine หรือ threshold ให้สร้าง reference และ candidate จาก input/config เดียวกัน แล้วเปรียบเทียบด้วย `scripts/compare_results.py`. เก็บทั้งสอง output พร้อม config, commit SHA และ checksum ของ input ใน CI artifact, release asset หรือ PR ที่เกี่ยวข้อง. `outputs/` เป็นพื้นที่ทำงานชั่วคราวเท่านั้น; repository ไม่เก็บผลรันเก่า
